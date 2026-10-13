"""Model adapters and role resolution (design §7.6, `tools.md` §8, §14.3).

Every agent role (proposer, critic, retriever, reader, summarizer) is bound at run
start to a model adapter. Adapters are provider-agnostic:

* `anthropic`          - Anthropic Messages API
* `openai_compatible`  - any OpenAI-compatible chat-completions endpoint (a user's own provider)
* `exchange`           - file-exchange bridge: requests are written to a folder and answered
                         by an outside agent (for example Claude subagents)
* `scripted`           - deterministic responses for tests

API keys are read from the environment at call time and never enter a record (ADR-40).
"""

from __future__ import annotations

import json
import os
import re
import time
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

import requests

from .clock import utc_now
from .ids import new_id


class ModelError(RuntimeError):
    def __init__(self, error_class: str, message: str):
        super().__init__(f"{error_class}: {message}")
        self.error_class = error_class


@dataclass(frozen=True)
class CapabilityRecord:
    """Model Adapter Capability Record (design §7.6)."""
    adapter_id: str
    provider_family: str
    model_id: str
    accepts_tool_schemas: bool = False
    returns_tool_results_to_model: str = "no"
    max_tool_iterations: int = 0
    structured_output_mode: str = "json_mode"
    error_feedback_supported: bool = True
    verified_by: str | None = None
    verification_state: str = "stale"


@dataclass
class ModelRequest:
    role: str
    system: str
    messages: list[dict[str, str]]
    response_schema: dict[str, Any] | None = None
    max_tokens: int = 4000
    temperature: float = 0.0
    request_id: str = field(default_factory=lambda: new_id("brief"))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResponse:
    request_id: str
    text: str
    data: Any
    model_id: str
    provider_path: str
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: int = 0


class ModelAdapter(Protocol):
    record: CapabilityRecord

    def complete(self, request: ModelRequest) -> ModelResponse: ...


# --- structured output -------------------------------------------------------------

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(text: str) -> Any:
    """Parse the JSON object in a model reply, tolerating code fences and surrounding prose."""
    candidates = [m.group(1) for m in _FENCE.finditer(text)] + [text]
    for chunk in candidates:
        chunk = chunk.strip()
        for opener, closer in (("{", "}"), ("[", "]")):
            start, end = chunk.find(opener), chunk.rfind(closer)
            if start != -1 and end > start:
                try:
                    return json.loads(chunk[start:end + 1])
                except json.JSONDecodeError:
                    continue
    raise ModelError("parse_failed", "no JSON value found in the model reply")


_TYPES = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict}


def validate(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """A small JSON-schema subset: type, required, properties, items, enum."""
    problems = []
    expected = schema.get("type")
    if expected:
        types = expected if isinstance(expected, list) else [expected]
        if not any(t == "null" and value is None or (t in _TYPES and isinstance(value, _TYPES[t])
                   and not (t in ("number", "integer") and isinstance(value, bool))) for t in types):
            return [f"{path}: expected {expected}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                problems.append(f"{path}: missing {key}")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                problems.extend(validate(value[key], sub, f"{path}.{key}"))
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            problems.extend(validate(item, schema["items"], f"{path}[{index}]"))
    return problems


def schema_instruction(schema: dict[str, Any]) -> str:
    return ("Reply with one JSON value only, no prose, matching this schema "
            "(JSON-schema subset):\n" + json.dumps(schema, indent=1))


# --- adapters ------------------------------------------------------------------------

def _secret(env_name: str) -> str:
    value = os.environ.get(env_name)
    if not value:
        raise ModelError("auth_missing", f"environment variable {env_name} is not set")
    return value


def redact(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text


class AnthropicAdapter:
    def __init__(self, adapter_id: str, model: str, *, api_key_env: str = "ANTHROPIC_API_KEY",
                 base_url: str = "https://api.anthropic.com", timeout_s: int = 300):
        self.record = CapabilityRecord(adapter_id, "anthropic", model)
        self.api_key_env, self.base_url, self.timeout_s = api_key_env, base_url.rstrip("/"), timeout_s

    def complete(self, request: ModelRequest) -> ModelResponse:
        key = _secret(self.api_key_env)
        system = request.system + ("\n\n" + schema_instruction(request.response_schema) if request.response_schema else "")
        started = time.monotonic()
        try:
            reply = requests.post(f"{self.base_url}/v1/messages", timeout=self.timeout_s, headers={
                "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": self.record.model_id, "system": system, "messages": request.messages,
                      "max_tokens": request.max_tokens, "temperature": request.temperature})
        except requests.RequestException as error:
            raise ModelError("transient_network", redact(str(error), [key])) from None
        if reply.status_code >= 400:
            raise ModelError("auth_rejected" if reply.status_code in (401, 403) else "upstream_server_error",
                             redact(reply.text[:500], [key]))
        body = reply.json()
        text = "".join(part.get("text", "") for part in body.get("content", []) if part.get("type") == "text")
        usage = body.get("usage", {})
        return ModelResponse(request.request_id, text, None, body.get("model", self.record.model_id), "anthropic_api",
                             {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0)},
                             int((time.monotonic() - started) * 1000))


class OpenAICompatibleAdapter:
    def __init__(self, adapter_id: str, model: str, *, base_url: str, api_key_env: str,
                 provider_family: str = "openai_compatible", json_response_format: bool = True, timeout_s: int = 300):
        self.record = CapabilityRecord(adapter_id, provider_family, model)
        self.base_url, self.api_key_env = base_url.rstrip("/"), api_key_env
        self.json_response_format, self.timeout_s = json_response_format, timeout_s

    def complete(self, request: ModelRequest) -> ModelResponse:
        key = _secret(self.api_key_env)
        system = request.system + ("\n\n" + schema_instruction(request.response_schema) if request.response_schema else "")
        payload = {"model": self.record.model_id, "messages": [{"role": "system", "content": system}, *request.messages],
                   "max_tokens": request.max_tokens, "temperature": request.temperature}
        if request.response_schema and self.json_response_format:
            payload["response_format"] = {"type": "json_object"}
        started = time.monotonic()
        try:
            reply = requests.post(f"{self.base_url}/chat/completions", timeout=self.timeout_s,
                                  headers={"authorization": f"Bearer {key}", "content-type": "application/json"},
                                  json=payload)
        except requests.RequestException as error:
            raise ModelError("transient_network", redact(str(error), [key])) from None
        if reply.status_code >= 400:
            raise ModelError("auth_rejected" if reply.status_code in (401, 403) else "upstream_server_error",
                             redact(reply.text[:500], [key]))
        body = reply.json()
        text = body["choices"][0]["message"].get("content") or ""
        usage = body.get("usage", {})
        return ModelResponse(request.request_id, text, None, body.get("model", self.record.model_id), "openai_compatible_api",
                             {"input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)},
                             int((time.monotonic() - started) * 1000))


class ExchangeAdapter:
    """File-exchange bridge: `<dir>/requests/<id>.json` in, `<dir>/responses/<id>.json` out.

    A response file holds {"request_id", "text"} or {"request_id", "data"}, plus
    "model_id" and "answered_by". Requests are written atomically; the adapter waits
    up to `timeout_s` for the response.
    """

    def __init__(self, adapter_id: str, exchange_dir: str | os.PathLike, *, model: str = "external-agent",
                 provider_family: str = "anthropic", poll_s: float = 1.0, timeout_s: float = 3600):
        self.record = CapabilityRecord(adapter_id, provider_family, model, returns_tool_results_to_model="no")
        self.root = Path(exchange_dir)
        (self.root / "requests").mkdir(parents=True, exist_ok=True)
        (self.root / "responses").mkdir(parents=True, exist_ok=True)
        self.poll_s, self.timeout_s = poll_s, timeout_s

    def post(self, request: ModelRequest) -> Path:
        body = {"request_id": request.request_id, "role": request.role, "system": request.system,
                "messages": request.messages, "response_schema": request.response_schema,
                "max_tokens": request.max_tokens, "metadata": request.metadata, "created_at": utc_now()}
        target = self.root / "requests" / f"{request.request_id}.json"
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(body, indent=1, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, target)
        return target

    def wait(self, request: ModelRequest) -> ModelResponse:
        response_path = self.root / "responses" / f"{request.request_id}.json"
        started, deadline = time.monotonic(), time.monotonic() + self.timeout_s
        while not response_path.exists():
            if time.monotonic() > deadline:
                raise ModelError("timeout", f"no response for {request.request_id} within {self.timeout_s}s")
            time.sleep(self.poll_s)
        body = json.loads(response_path.read_text(encoding="utf-8"))
        text = body.get("text") if body.get("text") is not None else json.dumps(body.get("data"))
        return ModelResponse(request.request_id, text, body.get("data"), body.get("model_id", self.record.model_id),
                             "exchange_bridge", body.get("usage", {}), int((time.monotonic() - started) * 1000))

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.post(request)
        return self.wait(request)


class ScriptedAdapter:
    """Deterministic adapter for tests: `script(request) -> str | dict`."""

    def __init__(self, adapter_id: str, script: Callable[[ModelRequest], Any], *, model: str = "scripted",
                 provider_family: str = "scripted"):
        self.record = CapabilityRecord(adapter_id, provider_family, model, verification_state="current")
        self.script = script
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        out = self.script(request)
        text = out if isinstance(out, str) else json.dumps(out)
        return ModelResponse(request.request_id, text, None if isinstance(out, str) else out, self.record.model_id, "scripted")


# --- configuration and role resolution ---------------------------------------------

ROLES = ("planner", "proposer", "critic", "adjudicator", "retriever", "reader", "summarizer", "reflector", "evaluator_judge")


def adapter_from_config(adapter_id: str, spec: dict[str, Any], base_dir: Path) -> ModelAdapter:
    kind = spec.get("kind")
    if kind == "anthropic":
        return AnthropicAdapter(adapter_id, spec["model"], api_key_env=spec.get("api_key_env", "ANTHROPIC_API_KEY"),
                                base_url=spec.get("base_url", "https://api.anthropic.com"))
    if kind == "openai_compatible":
        return OpenAICompatibleAdapter(adapter_id, spec["model"], base_url=spec["base_url"],
                                       api_key_env=spec["api_key_env"], provider_family=spec.get("provider_family", "openai_compatible"),
                                       json_response_format=spec.get("json_response_format", True))
    if kind == "exchange":
        directory = Path(spec.get("exchange_dir", "llm_exchange"))
        return ExchangeAdapter(adapter_id, directory if directory.is_absolute() else base_dir / directory,
                               model=spec.get("model", "external-agent"),
                               provider_family=spec.get("provider_family", "anthropic"),
                               poll_s=spec.get("poll_s", 1.0), timeout_s=spec.get("timeout_s", 3600))
    raise ValueError(f"unknown model adapter kind {kind!r} for {adapter_id}")


class ModelRoster:
    """Role → adapter bindings for one run; `role_bindings` go into the Run Binding."""

    def __init__(self, adapters: dict[str, ModelAdapter], roles: dict[str, str]):
        unknown = [r for r in roles if r not in ROLES]
        if unknown:
            raise ValueError(f"unknown roles {unknown}")
        missing = [a for a in roles.values() if a not in adapters]
        if missing:
            raise ValueError(f"roles bound to undefined adapters {missing}")
        self.adapters, self.roles = adapters, roles

    @classmethod
    def from_toml(cls, path: str | os.PathLike) -> "ModelRoster":
        path = Path(path)
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        adapters = {name: adapter_from_config(name, spec, path.parent) for name, spec in config.get("providers", {}).items()}
        return cls(adapters, dict(config.get("roles", {})))

    def adapter(self, role: str) -> ModelAdapter:
        if role not in self.roles:
            raise ModelError("model_unavailable", f"no adapter bound to role {role!r}")
        return self.adapters[self.roles[role]]

    def role_bindings(self) -> list[dict[str, Any]]:
        return [{"role": role, "adapter_id": name, "provider_family": self.adapters[name].record.provider_family,
                 "model_id": self.adapters[name].record.model_id, "model_version": self.adapters[name].record.model_id,
                 "decoding_parameters": {"temperature": 0.0}} for role, name in sorted(self.roles.items())]


def call_role(core, roster: ModelRoster, stream_id: str, request: ModelRequest, *,
              ids: dict[str, Any] | None = None, budget: Any = None, max_repairs: int = 1) -> ModelResponse:
    """Call the adapter bound to `request.role`, journal it, and enforce the response schema.

    Raw input and output go to a trace artifact (visibility expert/auditor), never into
    the default event summary. A reply that fails the schema is fed back once with the
    problems listed (error-recovery contract); a second failure raises `parse_failed`.
    """
    from .journal import actor as make_actor

    adapter = roster.adapter(request.role)
    who = make_actor("agent", f"{request.role}:{adapter.record.adapter_id}", request.role,
                     model_family=adapter.record.provider_family, version=adapter.record.model_id)
    if budget is not None and not budget.try_charge("llm_turns", 1):
        raise ModelError("quota_exhausted", f"llm_turns budget exhausted for {request.role}")
    core.journal.append(stream_id, "agent.started", actor=who, ids=ids or {},
                        payload={"request_id": request.request_id, "role": request.role}, question=request.metadata.get("question"))
    attempt_request, response, problems = request, None, []
    for attempt in range(max_repairs + 1):
        response = adapter.complete(attempt_request)
        if request.response_schema is None:
            break
        try:
            data = response.data if response.data is not None else extract_json(response.text)
            problems = validate(data, request.response_schema)
        except ModelError as error:
            data, problems = None, [str(error)]
        if not problems:
            response.data = data
            break
        if attempt < max_repairs:
            if budget is not None:
                budget.try_charge("llm_turns", 1)
            attempt_request = ModelRequest(
                role=request.role, system=request.system, response_schema=request.response_schema,
                max_tokens=request.max_tokens, temperature=request.temperature, metadata=request.metadata,
                request_id=new_id("brief"),
                messages=request.messages + [{"role": "assistant", "content": response.text},
                                             {"role": "user", "content": "Your reply did not match the schema: "
                                              + "; ".join(problems[:10]) + ". Reply again with corrected JSON only."}])
    trace_id = core.artifacts.put("trace", {"request": asdict(request), "final_text": response.text,
                                            "model_id": response.model_id, "provider_path": response.provider_path,
                                            "schema_problems": problems})
    core.journal.append(stream_id, "agent.finished", actor=who, ids=ids or {}, visibility="default",
                        payload={"request_id": request.request_id, "role": request.role, "usage": response.usage,
                                 "provider_path": response.provider_path, "model_id": response.model_id,
                                 "trace_blob": trace_id, "schema_ok": not problems},
                        summary=f"{request.role} replied" + ("" if not problems else " (schema problems)"))
    if problems:
        raise ModelError("parse_failed", "; ".join(problems[:5]))
    return response
