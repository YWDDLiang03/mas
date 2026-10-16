"""Model adapters and role resolution (design §7.6, `tools.md` §8, §14.3).

Every agent role (proposer, critic, retriever, reader, summarizer) is bound at run
start to a model adapter. Adapters are provider-agnostic:

* `anthropic`          - Anthropic Messages API
* `openai_compatible`  - any OpenAI-compatible chat-completions endpoint (a user's own provider)
* `exchange`           - file-exchange bridge: requests are written to a folder and answered
                         by an outside agent (for example Claude subagents)
* `scripted`           - deterministic responses for tests

API keys are read at call time from an environment variable or a key file and never
enter a record, a trace, or an error message (ADR-40).
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
    def __init__(self, error_class: str, message: str, *, accounting: dict[str, Any] | None = None):
        super().__init__(f"{error_class}: {message}")
        self.error_class = error_class
        self.accounting = accounting or {}


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
    cost_usd: float | None = None
    reasoning: str = ""   # provider reasoning text, kept in the trace only
    truncated: bool = False   # the provider stopped at the token limit, so the reply is incomplete
    usage_status: str | None = None
    cost_status: str | None = None
    provider_attempts: list[dict[str, Any]] = field(default_factory=list)


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

def _secret(env_name: str | None, key_file: str | None = None) -> str:
    """The API key from the environment variable, else from the key file; never logged."""
    value = os.environ.get(env_name) if env_name else None
    if not value and key_file:
        try:
            value = Path(key_file).expanduser().read_text(encoding="utf-8").strip()
        except OSError:
            raise ModelError("auth_missing", f"key file {key_file} cannot be read") from None
    if not value:
        where = f"environment variable {env_name}" if env_name else "no key source"
        raise ModelError("auth_missing", f"{where} is not set" + (f" and {key_file} is empty" if key_file else ""))
    return value


def _cost(usage: dict[str, int], price_in: float | None, price_out: float | None) -> float | None:
    """Known tariff subtotal; absent usage or prices remain unknown, rather than zero."""
    terms = [usage[key] * price / 1_000_000
             for key, price in (("input_tokens", price_in), ("output_tokens", price_out))
             if key in usage and price is not None]
    return sum(terms) if terms else None


def _usage_status(usage: dict[str, int]) -> str:
    return "complete" if all(key in usage for key in ("input_tokens", "output_tokens")) else "partial" if usage else "unknown"


def _cost_status(usage: dict[str, int], price_in: float | None, price_out: float | None) -> str:
    if _cost(usage, price_in, price_out) is None:
        return "unknown"
    complete = _usage_status(usage) == "complete" and all(
        price is not None or usage[key] == 0
        for key, price in (("input_tokens", price_in), ("output_tokens", price_out)))
    return "estimated" if complete else "partial"


def _aggregate_accounting(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    actual = [attempt for attempt in attempts if attempt.get("status") != "not_attempted"]
    usage: dict[str, int] = {}
    for attempt in actual:
        for key, value in (attempt.get("usage") or {}).items():
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                usage[key] = usage.get(key, 0) + value
    known = [attempt["cost_usd"] for attempt in actual if attempt.get("cost_usd") is not None]
    cost = sum(known) if known else None
    return {"usage": usage,
            "usage_status": "complete" if actual and all(a.get("usage_status") == "complete" for a in actual)
                            else "partial" if usage else "unknown",
            "cost_usd": cost, "known_cost_usd": cost,
            "cost_status": "estimated" if actual and all(a.get("cost_status") == "estimated" for a in actual)
                           else "partial" if known else "unknown",
            "cost_is_estimate": True,
            "attempt_count": len(actual)}


def redact(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text


class AnthropicAdapter:
    def __init__(self, adapter_id: str, model: str, *, api_key_env: str = "ANTHROPIC_API_KEY",
                 api_key_file: str | None = None, base_url: str = "https://api.anthropic.com", timeout_s: int = 300,
                 price_input_per_mtok: float | None = None, price_output_per_mtok: float | None = None):
        self.record = CapabilityRecord(adapter_id, "anthropic", model)
        self.api_key_env, self.api_key_file = api_key_env, api_key_file
        self.base_url, self.timeout_s = base_url.rstrip("/"), timeout_s
        self.price_in, self.price_out = price_input_per_mtok, price_output_per_mtok

    def decoding(self, temperature: float) -> dict[str, Any]:
        return {"temperature": temperature}

    def complete(self, request: ModelRequest) -> ModelResponse:
        key = _secret(self.api_key_env, self.api_key_file)
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
        tokens = {key: usage[key] for key in ("input_tokens", "output_tokens") if key in usage}
        return ModelResponse(request.request_id, text, None, body.get("model", self.record.model_id), "anthropic_api",
                             tokens, int((time.monotonic() - started) * 1000),
                             cost_usd=_cost(tokens, self.price_in, self.price_out), usage_status=_usage_status(tokens),
                             cost_status=_cost_status(tokens, self.price_in, self.price_out))


class OpenAICompatibleAdapter:
    """Any OpenAI-compatible chat-completions endpoint (DeepSeek, vLLM, a user's own provider).

    `thinking` switches a provider's reasoning mode where it has one: None sends nothing,
    False sends {"thinking": {"type": "disabled"}}, True leaves it on. While thinking is on,
    providers such as DeepSeek ignore `temperature`, so it is not sent and the binding says so.
    """

    def __init__(self, adapter_id: str, model: str, *, base_url: str, api_key_env: str | None = None,
                 api_key_file: str | None = None, provider_family: str = "openai_compatible",
                 json_response_format: bool = True, timeout_s: int = 300, thinking: bool | None = None,
                 reasoning_effort: str | None = None, price_input_per_mtok: float | None = None,
                 price_output_per_mtok: float | None = None, empty_reply_retries: int = 2,
                 max_token_ceiling: int = 32000):
        self.record = CapabilityRecord(adapter_id, provider_family, model)
        self.base_url, self.api_key_env, self.api_key_file = base_url.rstrip("/"), api_key_env, api_key_file
        self.json_response_format, self.timeout_s = json_response_format, timeout_s
        self.thinking, self.reasoning_effort = thinking, reasoning_effort
        self.price_in, self.price_out = price_input_per_mtok, price_output_per_mtok
        self.empty_reply_retries, self.max_token_ceiling = empty_reply_retries, max_token_ceiling

    def decoding(self, temperature: float) -> dict[str, Any]:
        """The decoding parameters actually sent, for the run binding."""
        out: dict[str, Any] = {}
        if self.thinking is not None:
            out["thinking"] = self.thinking
        if self.reasoning_effort:
            out["reasoning_effort"] = self.reasoning_effort
        if self.thinking is not True:
            out["temperature"] = temperature
        return out

    def payload(self, request: ModelRequest) -> dict[str, Any]:
        system = request.system
        if request.response_schema:
            system += "\n\n" + schema_instruction(request.response_schema)
            if self.json_response_format:
                # JSON mode requires the word "json" in the prompt on some providers (DeepSeek).
                system += "\nOutput format: json."
        payload: dict[str, Any] = {"model": self.record.model_id,
                                   "messages": [{"role": "system", "content": system}, *request.messages],
                                   "max_tokens": request.max_tokens}
        if self.thinking is not True:
            payload["temperature"] = request.temperature
        if self.thinking is False:
            payload["thinking"] = {"type": "disabled"}
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        if request.response_schema and self.json_response_format:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def complete(self, request: ModelRequest) -> ModelResponse:
        return self.complete_controlled(request)

    def complete_controlled(self, request: ModelRequest, *,
                            before_attempt: Callable[[dict[str, Any]], None] | None = None,
                            on_attempt: Callable[[dict[str, Any]], None] | None = None) -> ModelResponse:
        """Report and control each actual HTTP attempt, including internal retries.

        Callbacks receive metadata and accounting, never credentials or raw replies.
        A cooperative exception keeps its identity and completed-attempt accounting.
        The ordinary complete(request) entry point retains its previous behaviour.
        """
        key = _secret(self.api_key_env, self.api_key_file)
        payload = self.payload(request)
        started = time.monotonic()
        provider_attempts = []

        def attach_accounting(error: Exception) -> None:
            error.accounting = dict(_aggregate_accounting(provider_attempts), provider_attempts=provider_attempts)

        def publish_attempt(record: dict[str, Any]) -> None:
            provider_attempts.append(record)
            if on_attempt is not None:
                fields = ("request_id", "provider_attempt_index", "max_tokens", "status", "usage_status",
                          "cost_usd", "cost_status", "response_id", "finish_reason", "error_class")
                summary = {key: record.get(key) for key in fields}
                summary["usage"] = dict(record.get("usage") or {})
                summary["known_cost_usd"] = record.get("cost_usd")
                try:
                    on_attempt(summary)
                except Exception as error:
                    attach_accounting(error)
                    raise

        max_tokens = request.max_tokens
        ceiling = max(request.max_tokens, min(4 * request.max_tokens, self.max_token_ceiling))
        finish_reason = None
        for attempt in range(self.empty_reply_retries + 1):
            payload["max_tokens"] = max_tokens
            attempt_record = {"request_id": request.request_id, "provider_attempt_index": attempt + 1,
                              "max_tokens": max_tokens, "status": "failed", "usage": {}, "usage_status": "unknown",
                              "cost_usd": None, "cost_status": "unknown"}
            if before_attempt is not None:
                try:
                    before_attempt({"request_id": request.request_id, "provider_attempt_index": attempt + 1,
                                    "max_tokens": max_tokens})
                except Exception as error:
                    provider_attempts.append(dict(attempt_record, status="not_attempted",
                                                  error_class=error.error_class if isinstance(error, ModelError) else type(error).__name__))
                    attach_accounting(error)
                    raise
            try:
                reply = requests.post(f"{self.base_url}/chat/completions", timeout=self.timeout_s,
                                      headers={"authorization": f"Bearer {key}", "content-type": "application/json"},
                                      json=payload)
                attempt_record["raw_response"] = redact(reply.text, [key])
                if reply.status_code == 429:
                    raise ModelError("rate_limited", redact(reply.text[:300], [key]))
                if reply.status_code >= 400:
                    raise ModelError("auth_rejected" if reply.status_code in (401, 403) else "upstream_server_error",
                                     redact(reply.text[:500], [key]))
                body = reply.json()
                usage = body.get("usage") or {}
                tokens = {target: usage[source] for source, target in
                          (("prompt_tokens", "input_tokens"), ("completion_tokens", "output_tokens")) if source in usage}
                attempt_record.update(usage=tokens, usage_status=_usage_status(tokens),
                                      cost_usd=_cost(tokens, self.price_in, self.price_out),
                                      cost_status=_cost_status(tokens, self.price_in, self.price_out),
                                      response_id=body.get("id"))
                choice = body["choices"][0]
                message = choice["message"]
                finish_reason = choice.get("finish_reason")
                text = message.get("content") or ""
                attempt_record.update(status="returned", text=text, reasoning=message.get("reasoning_content") or "",
                                      finish_reason=finish_reason)
            except InterruptedError as error:
                attempt_record["error_class"] = type(error).__name__
                publish_attempt(attempt_record)
                attach_accounting(error)
                raise
            except Exception as error:
                error_class = (error.error_class if isinstance(error, ModelError) else
                               "transient_network" if isinstance(error, requests.RequestException) else "parse_failed")
                attempt_record["error_class"] = error_class
                publish_attempt(attempt_record)
                accounting = _aggregate_accounting(provider_attempts)
                accounting["provider_attempts"] = provider_attempts
                raise ModelError(error_class, redact(str(error), [key]), accounting=accounting) from None
            publish_attempt(attempt_record)
            if finish_reason == "length" and max_tokens < ceiling:
                # A reply cut off at the limit is never a complete JSON value, and a reasoning
                # model can spend the whole allowance before the answer starts (measured on
                # deepseek-flash: 700 of 700 completion tokens were reasoning, content empty).
                max_tokens = min(2 * max_tokens, ceiling)
                continue
            if text.strip() or attempt == self.empty_reply_retries:
                break   # providers in JSON mode may occasionally return empty content; ask again
        accounting = _aggregate_accounting(provider_attempts)
        return ModelResponse(request.request_id, text, None, body.get("model", self.record.model_id),
                             "openai_compatible_api", accounting["usage"], int((time.monotonic() - started) * 1000),
                             cost_usd=accounting["cost_usd"], usage_status=accounting["usage_status"],
                             cost_status=accounting["cost_status"], provider_attempts=provider_attempts,
                             reasoning=message.get("reasoning_content") or "",
                             truncated=finish_reason == "length")


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
        while True:
            try:
                raw = response_path.read_text(encoding="utf-8")
                break
            except (FileNotFoundError, PermissionError):
                # Atomic publication does not prevent a short Windows sharing lock.
                # Keep polling under the original deadline, without treating it as a reply.
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ModelError("timeout", f"no readable response for {request.request_id} within {self.timeout_s}s") from None
                time.sleep(min(self.poll_s, remaining))
        body = json.loads(raw)
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
                                api_key_file=spec.get("api_key_file"),
                                base_url=spec.get("base_url", "https://api.anthropic.com"),
                                price_input_per_mtok=spec.get("price_input_per_mtok"),
                                price_output_per_mtok=spec.get("price_output_per_mtok"))
    if kind == "openai_compatible":
        if not spec.get("api_key_env") and not spec.get("api_key_file"):
            raise ValueError(f"{adapter_id}: set api_key_env or api_key_file")
        return OpenAICompatibleAdapter(adapter_id, spec["model"], base_url=spec["base_url"],
                                       api_key_env=spec.get("api_key_env"), api_key_file=spec.get("api_key_file"),
                                       provider_family=spec.get("provider_family", "openai_compatible"),
                                       json_response_format=spec.get("json_response_format", True),
                                       thinking=spec.get("thinking"), reasoning_effort=spec.get("reasoning_effort"),
                                       price_input_per_mtok=spec.get("price_input_per_mtok"),
                                       price_output_per_mtok=spec.get("price_output_per_mtok"),
                                       timeout_s=spec.get("timeout_s", 300))
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
        return cls.from_tables(config.get("providers", {}), config.get("roles", {}), path.parent)

    @classmethod
    def from_tables(cls, providers: dict[str, Any], roles: dict[str, str], base_dir: str | os.PathLike) -> "ModelRoster":
        """Providers and roles from a resolved configuration (see core/config.py)."""
        adapters = {name: adapter_from_config(name, spec, Path(base_dir)) for name, spec in providers.items()}
        return cls(adapters, dict(roles))

    def adapter(self, role: str) -> ModelAdapter:
        if role not in self.roles:
            raise ModelError("model_unavailable", f"no adapter bound to role {role!r}")
        return self.adapters[self.roles[role]]

    def role_bindings(self) -> list[dict[str, Any]]:
        return [{"role": role, "adapter_id": name, "provider_family": self.adapters[name].record.provider_family,
                 "model_id": self.adapters[name].record.model_id, "model_version": self.adapters[name].record.model_id,
                 "decoding_parameters": (self.adapters[name].decoding(0.0) if hasattr(self.adapters[name], "decoding")
                                         else {"temperature": 0.0})}
                for role, name in sorted(self.roles.items())]


def call_role(core, roster: ModelRoster, stream_id: str, request: ModelRequest, *,
              ids: dict[str, Any] | None = None, budget: Any = None, max_repairs: int = 2) -> ModelResponse:
    """Call the adapter bound to `request.role`, journal it, and enforce the response schema.

    Raw input and output go to a trace artifact (visibility expert/auditor), never into
    the default event summary. A reply that fails the schema is fed back with the problems
    listed (error-recovery contract); exhausting `max_repairs` raises `parse_failed`.

    WHY the default is two repairs rather than one: a reasoning provider occasionally answers in
    prose instead of json, and one repair was not enough to absorb it. Measured on 14 October 2026
    against DeepSeek `deepseek-v4-flash`, which cost three derivation runs: twice in
    `derivation_stages.refine_stage` and once in `reading.extract_claims` under
    `derivation.enumerate_dimension`, each time `parse_failed: no JSON value found in the model
    reply` after 1.5 hours of reading. A repair is one cheap call against the loss of a whole round,
    and the reply that fails is already in the trace artifact either way.
    """
    from .journal import actor as make_actor

    adapter = roster.adapter(request.role)
    controlled_complete = getattr(adapter, "complete_controlled", None)
    controlled = callable(controlled_complete)
    who = make_actor("agent", f"{request.role}:{adapter.record.adapter_id}", request.role,
                     model_family=adapter.record.provider_family, version=adapter.record.model_id)
    def reserve_turn() -> ModelError | None:
        if budget is not None and hasattr(budget, "allows") and not budget.allows("usd"):
            return ModelError("quota_exhausted", f"spend cap reached before {request.role}")
        if budget is not None and not budget.try_charge("llm_turns", 1):
            return ModelError("quota_exhausted", f"llm_turns budget exhausted for {request.role}")
        return None

    def record_spend(cost: float | None) -> None:
        total = getattr(budget, "root", budget)
        accountant = budget if hasattr(budget, "record") else total
        if cost is None or accountant is None or not hasattr(accountant, "record"):
            return
        for level in accountant.record("usd", cost):
            used = total.used.get("usd", 0.0)
            core.journal.append(stream_id, "run.annotated", actor=make_actor("controller", "budget", "controller"),
                                payload={"annotation": "budget_threshold", "kind": "usd", "level": level,
                                         "used": round(used, 4), "cap": total.caps.get("usd"),
                                         "continues": budget.allows("usd")},
                                summary=f"provider spend crossed the {level} threshold "
                                        f"({used:.2f} of {total.caps.get('usd')} USD)")

    if not controlled:
        refusal = reserve_turn()
        if refusal is not None:
            raise refusal
    core.journal.append(stream_id, "agent.started", actor=who, ids=ids or {},
                        payload={"request_id": request.request_id, "role": request.role}, question=request.metadata.get("question"))
    attempt_request, response, problems = request, None, []
    attempts, reasoning, failure = [], [], None
    for attempt in range(max_repairs + 1):
        entry = {"attempt_index": attempt + 1, "request_id": attempt_request.request_id,
                 "request": asdict(attempt_request), "schema_problems": []}
        if attempt and not controlled:
            try:
                refusal = reserve_turn()
            except InterruptedError as error:
                # Preserve the paid response and its accounting before propagating a
                # cooperative pause/stop that arrives between schema-repair attempts.
                failure = error
                attempts.append(dict(entry, status="not_attempted", error_class=type(error).__name__))
                break
            if refusal is not None:
                failure = refusal
                attempts.append(dict(entry, status="not_attempted", error_class=refusal.error_class))
                break
        def before_provider_attempt(metadata: dict[str, Any]) -> None:
            refusal = reserve_turn()
            if refusal is not None:
                raise refusal

        def provider_attempt_finished(summary: dict[str, Any]) -> None:
            # Provider attempts are charged here, once, before a retry may start.
            # The logical agent.finished event later replaces this subtotal in
            # readers; it is never another debit to the shared budget.
            record_spend(summary.get("cost_usd"))
            payload = {**summary, "annotation": "model_provider_attempt", "request_id": request.request_id,
                       "attempt_request_id": summary.get("request_id"), "logical_attempt_index": attempt + 1,
                       "role": request.role}
            core.journal.append(stream_id, "run.annotated", actor=who, ids=ids or {}, payload=payload,
                                budget=budget.snapshot() if budget is not None and hasattr(budget, "snapshot") else None,
                                summary=f"{request.role} provider attempt {summary.get('provider_attempt_index')} finished")
            observer = getattr(budget, "on_model_attempt", None)
            if callable(observer):
                observer(payload)

        try:
            response = controlled_complete(attempt_request, before_attempt=before_provider_attempt,
                                           on_attempt=provider_attempt_finished) if controlled else adapter.complete(attempt_request)
        except Exception as error:
            failure = error
            partial = getattr(error, "accounting", {}) or {}
            entry.update(status="not_attempted" if controlled and not partial.get("attempt_count") else "failed",
                         usage=partial.get("usage") or {},
                         usage_status=partial.get("usage_status", "unknown"),
                         cost_usd=partial.get("cost_usd"), cost_status=partial.get("cost_status", "unknown"),
                         provider_attempts=partial.get("provider_attempts") or [],
                         error_class=error.error_class if isinstance(error, ModelError) else type(error).__name__)
            if not controlled:
                record_spend(entry["cost_usd"])
            attempts.append(entry)
            break
        entry.update(status="returned", response=asdict(response), usage=dict(response.usage or {}),
                     usage_status=response.usage_status or _usage_status(response.usage or {}),
                     cost_usd=response.cost_usd,
                     cost_status=response.cost_status or ("estimated" if response.cost_usd is not None else "unknown"))
        if not controlled:
            record_spend(response.cost_usd)
        attempts.append(entry)
        if response.reasoning:
            reasoning.append(response.reasoning)
        if request.response_schema is None:
            break
        try:
            data = response.data if response.data is not None else extract_json(response.text)
            problems = validate(data, request.response_schema)
        except ModelError as error:
            data, problems = None, [str(error)]
        entry["schema_problems"] = list(problems)
        if not problems:
            response.data = data
            break
        entry["status"] = "schema_invalid"
        if attempt < max_repairs:
            attempt_request = ModelRequest(
                role=request.role, system=request.system, response_schema=request.response_schema,
                max_tokens=2 * attempt_request.max_tokens if response.truncated else request.max_tokens,
                temperature=request.temperature, metadata=request.metadata,
                request_id=new_id("brief"),
                messages=request.messages + [{"role": "assistant", "content": response.text},
                                             {"role": "user", "content": "Your reply did not match the schema: "
                                              + "; ".join(problems[:10]) + ". Reply again with corrected JSON only."}])
    if failure is None and problems:
        failure = ModelError("parse_failed", "; ".join(problems[:5]))
    accounting = _aggregate_accounting(attempts)
    if controlled:
        accounting["provider_attempt_count"] = sum(
            len([provider for provider in entry.get("provider_attempts", (entry.get("response") or {}).get("provider_attempts", []))
                 if provider.get("status") != "not_attempted"]) for entry in attempts)
    model_id = response.model_id if response is not None else adapter.record.model_id
    provider_path = response.provider_path if response is not None else "unknown"
    schema_ok = failure is None and not problems
    outcome = ("ok" if schema_ok else "interrupted" if isinstance(failure, InterruptedError) else
               "budget_exhausted" if isinstance(failure, ModelError) and failure.error_class == "quota_exhausted" else "failed")
    trace_id = core.artifacts.put("trace", {"request": asdict(request), "final_text": response.text if response else "",
                                            "model_id": model_id, "provider_path": provider_path,
                                            "schema_problems": problems, "reasoning": reasoning,
                                            "truncated": response.truncated if response else False,
                                            "max_tokens_final": attempt_request.max_tokens,
                                            "attempts": attempts, "accounting": accounting, "outcome": outcome,
                                            "error_class": (failure.error_class if isinstance(failure, ModelError)
                                                            else type(failure).__name__ if failure else None)})
    core.journal.append(stream_id, "agent.finished", actor=who, ids=ids or {}, visibility="default",
                        payload={"request_id": request.request_id, "role": request.role, **accounting,
                                 "provider_path": provider_path, "model_id": model_id, "trace_blob": trace_id,
                                 "schema_ok": schema_ok, "reply_truncated": response.truncated if response else False,
                                 "outcome": outcome,
                                 "error_class": (failure.error_class if isinstance(failure, ModelError)
                                                 else type(failure).__name__ if failure else None)},
                        summary=f"{request.role} finished ({outcome})")
    if failure is not None:
        if isinstance(failure, (ModelError, InterruptedError)):
            failure.accounting = dict(accounting, trace_blob=trace_id,
                                      provider_attempts=[provider for entry in attempts for provider in
                                          entry.get("provider_attempts", (entry.get("response") or {}).get("provider_attempts", []))])
        raise failure
    response.usage = accounting["usage"]
    response.usage_status = accounting["usage_status"]
    response.cost_usd = accounting["cost_usd"]
    response.cost_status = accounting["cost_status"]
    return response
