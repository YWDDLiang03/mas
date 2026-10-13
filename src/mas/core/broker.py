"""Tool Broker and Capability Registry (C13; design §7).

Tools are resolved by capability and question kind, never by name. Every call
passes pre-checks, is retried only for retryable error classes, and returns one
of the registered outcomes with a provenance block. The broker never writes
claim status: a successful call is not a validation (design §7.7).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from . import constants, vocab
from .canonical import sha256_hex
from .clock import utc_now
from .ids import new_id
from .journal import actor as make_actor
from .runtime import Core

# Domain-neutral capability kinds owned by the core (ADR-29).
CAPABILITY_KINDS = frozenset({
    "entity_resolution", "relationship_evidence_lookup", "relationship_estimate", "attribute_estimate",
    "source_retrieval", "document_reading", "dataset_context_lookup", "rule_evaluation",
})
RETRYABLE = frozenset({"rate_limited", "transient_network", "upstream_server_error", "timeout"})
STRENGTH_ORDER = {"predicted": 0, "curated": 1, "measured": 2}
VALUE_KIND_STRENGTH = {"predicted": 0, "simulated": 0, "derived": 1, "curated": 1, "measured": 2, "missing": 0}


@dataclass(frozen=True)
class ToolContract:
    tool_id: str
    capability: str
    capability_kind: str
    question_kinds: tuple[str, ...]
    contract_version: str
    implementation_version: str
    purpose_statement: str
    evidence_kind_produced: str
    claim_strength_ceiling: str
    determinism: str = "external_state_dependent"
    cost_latency_class: str = "short"
    timeout_ms: int = 30_000
    license_id: str = "unknown"
    side_effect_class: str = "read"
    execution_location: str = "remote_endpoint"
    platform_independent_output: bool = True
    supported_platforms: tuple[tuple[str, str], ...] = (("linux", "unchecked"), ("windows", "unchecked"))
    required_inputs: tuple[str, ...] = ()
    identity_inputs: tuple[str, ...] = ()

    def __post_init__(self):
        if self.capability_kind not in CAPABILITY_KINDS:
            raise ValueError(f"unknown capability kind {self.capability_kind!r}")
        if self.claim_strength_ceiling not in STRENGTH_ORDER:
            raise ValueError(f"bad claim_strength_ceiling {self.claim_strength_ceiling!r}")


class ToolError(Exception):
    """A runtime failure after pre-checks passed (outcome `failed`)."""

    def __init__(self, error_class: str, message: str, *, retryable: bool | None = None, diagnostic: dict | None = None):
        vocab.require("error_class", error_class)
        super().__init__(f"{error_class}: {message}")
        self.error_class = error_class
        self.retryable = error_class in RETRYABLE if retryable is None else retryable
        self.diagnostic = diagnostic or {}


class ToolAbsent(Exception):
    """A pre-check failure (outcome `not_attempted`)."""

    def __init__(self, absence_reason: str, message: str = "", required_inputs_manifest: list[str] | None = None):
        vocab.require("absence_reason", absence_reason)
        super().__init__(f"{absence_reason}: {message}")
        self.absence_reason = absence_reason
        self.required_inputs_manifest = required_inputs_manifest or []


@dataclass
class ProviderResponse:
    """What a provider returns; the broker wraps it into a result record."""
    values: list[dict[str, Any]] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)
    outcome: str = "ok"
    data_version: str = "unknown"
    upstream_refs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Provider(Protocol):
    contract: ToolContract

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse: ...


@dataclass
class ToolResult:
    result_id: str
    invocation: dict[str, Any]
    outcome: str
    values: list[dict[str, Any]]
    records: list[dict[str, Any]]
    provenance: dict[str, Any]
    error: dict[str, Any] | None = None
    absence_reason: str | None = None
    required_inputs_manifest: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    artifact_id: str | None = None

    @property
    def ok(self) -> bool:
        return self.outcome in ("ok", "partial")


class Broker:
    def __init__(self, core: Core, *, sleep: Callable[[float], None] = time.sleep, platform: str = "linux"):
        self.core = core
        self.sleep = sleep
        self.platform = platform
        self._providers: list[Provider] = []
        self._cache: dict[str, ToolResult] = {}

    # --- registry -------------------------------------------------------------------
    def register(self, provider: Provider) -> None:
        self._providers.append(provider)

    def contracts(self) -> list[ToolContract]:
        return [p.contract for p in self._providers]

    def manifest(self) -> list[dict[str, Any]]:
        """The resolved tool manifest bound into a Run Binding (design §2.3, §14.2)."""
        return [{"tool_id": c.tool_id, "contract_version": c.contract_version,
                 "implementation_version": c.implementation_version, "capability": c.capability,
                 "execution_location": c.execution_location} for c in self.contracts()]

    def resolve(self, capability: str, question_kind: str) -> list[Provider]:
        """Providers able to answer, matched on adapter capability or core capability kind."""
        return [p for p in self._providers
                if (p.contract.capability == capability or p.contract.capability_kind == capability)
                and question_kind in p.contract.question_kinds]

    # --- dispatch -------------------------------------------------------------------
    def call(self, stream_id: str, capability: str, question_kind: str, inputs: dict[str, Any], *,
             requesting_actor: dict[str, Any], ids: dict[str, Any] | None = None,
             budget: Any = None, required_value_kind: str | None = None) -> ToolResult:
        providers = self.resolve(capability, question_kind)
        if required_value_kind is not None:
            needed = VALUE_KIND_STRENGTH.get(required_value_kind, 0)
            providers = [p for p in providers if STRENGTH_ORDER[p.contract.claim_strength_ceiling] >= needed]
        if not providers:
            return self._record(stream_id, None, capability, question_kind, inputs, requesting_actor, ids,
                                outcome="not_attempted", absence_reason="not_configured")
        last: ToolResult | None = None
        for provider in providers:
            last = self._call_one(stream_id, provider, capability, question_kind, inputs, requesting_actor, ids, budget)
            if last.outcome != "not_attempted":
                return last
        return last

    def _call_one(self, stream_id, provider, capability, question_kind, inputs, requesting_actor, ids, budget) -> ToolResult:
        contract = provider.contract
        cache_key = sha256_hex({"tool": contract.tool_id, "v": contract.contract_version, "q": question_kind, "in": inputs})
        if cache_key in self._cache:
            return self._cache[cache_key]
        missing = [name for name in contract.required_inputs + contract.identity_inputs
                   if inputs.get(name) in (None, "", [])]
        if missing:
            identity_gap = any(name in contract.identity_inputs for name in missing)
            return self._record(stream_id, contract, capability, question_kind, inputs, requesting_actor, ids,
                                outcome="not_attempted",
                                absence_reason="identity_unresolved" if identity_gap else "out_of_domain",
                                manifest=missing)
        if not any(platform == self.platform for platform, _ in contract.supported_platforms):
            return self._record(stream_id, contract, capability, question_kind, inputs, requesting_actor, ids,
                                outcome="not_attempted", absence_reason="requires_other_environment")
        if budget is not None and not budget.try_charge("tool_calls", 1):
            return self._record(stream_id, contract, capability, question_kind, inputs, requesting_actor, ids,
                                outcome="not_attempted", absence_reason="budget_exceeded")
        invocation_id = new_id("inv")
        requested = self.core.journal.append(
            stream_id, "tool.requested", actor=requesting_actor, ids=dict(ids or {}, tool_call_id=invocation_id),
            payload={"tool_id": contract.tool_id, "capability": capability, "question_kind": question_kind,
                     "input_hash": sha256_hex(inputs)},
            question=f"{question_kind} via {contract.tool_id}")
        limit = int(constants.value(self.core, "const_tool_retry_limit"))
        attempt = 0
        started = time.monotonic()
        while True:
            attempt += 1
            try:
                response = provider.invoke(question_kind, inputs)
            except ToolAbsent as absent:
                result = self._record(stream_id, contract, capability, question_kind, inputs, requesting_actor, ids,
                                      outcome="not_attempted", absence_reason=absent.absence_reason,
                                      manifest=absent.required_inputs_manifest, invocation_id=invocation_id,
                                      parent_seq=requested.seq)
                break
            except ToolError as error:
                if error.retryable and attempt < limit:
                    delay = min(30.0, 0.5 * (2 ** (attempt - 1))) * (0.5 + random.random())
                    self.core.journal.append(stream_id, "tool.retry_scheduled", actor=make_actor("tool", contract.tool_id),
                                             ids=dict(ids or {}, tool_call_id=invocation_id), parent_seq=requested.seq,
                                             payload={"attempt": attempt, "error_class": error.error_class, "delay_s": round(delay, 3)})
                    self.sleep(delay)
                    continue
                result = self._record(stream_id, contract, capability, question_kind, inputs, requesting_actor, ids,
                                      outcome="failed", error={"code": error.error_class, "class": error.error_class,
                                                               "retryable": error.retryable, "message": str(error),
                                                               "structured_diagnostic": error.diagnostic},
                                      invocation_id=invocation_id, parent_seq=requested.seq, attempts=attempt)
                break
            except Exception as error:  # a provider bug is an internal error, never a crash of the run
                result = self._record(stream_id, contract, capability, question_kind, inputs, requesting_actor, ids,
                                      outcome="failed", error={"code": "internal_error", "class": "internal_error",
                                                               "retryable": False, "message": repr(error)},
                                      invocation_id=invocation_id, parent_seq=requested.seq, attempts=attempt)
                break
            else:
                vocab.require("tool_outcome", response.outcome)
                for item in response.values:
                    kind = item.get("value_kind")
                    if kind and VALUE_KIND_STRENGTH.get(kind, 0) > STRENGTH_ORDER[contract.claim_strength_ceiling]:
                        raise ValueError(f"{contract.tool_id} returned {kind} above its claim_strength_ceiling")
                outcome = response.outcome if (response.values or response.records) else "empty"
                result = self._record(stream_id, contract, capability, question_kind, inputs, requesting_actor, ids,
                                      outcome=outcome, response=response, invocation_id=invocation_id,
                                      parent_seq=requested.seq, attempts=attempt,
                                      latency_ms=int((time.monotonic() - started) * 1000))
                break
        if result.outcome in ("ok", "partial", "empty"):
            self._cache[cache_key] = result
        return result

    def _record(self, stream_id, contract, capability, question_kind, inputs, requesting_actor, ids, *, outcome,
                response: ProviderResponse | None = None, error=None, absence_reason=None, manifest=None,
                invocation_id=None, parent_seq=None, attempts=0, latency_ms=None) -> ToolResult:
        invocation = {
            "invocation_id": invocation_id or new_id("inv"), "requesting_actor": requesting_actor,
            "tool_id": contract.tool_id if contract else None,
            "contract_version": contract.contract_version if contract else None,
            "capability": capability, "question_kind": question_kind, "normalized_input": inputs,
            "input_hash": sha256_hex(inputs), "requested_at": utc_now(), "attempt_index": attempts,
            "latency_ms": latency_ms, "provider_path": contract.execution_location if contract else None,
        }
        provenance = {
            "kind": "tool_result", "upstream_ref": (response.upstream_refs if response else []),
            "retrieved_at": utc_now(), "tool_id": invocation["tool_id"],
            "contract_version": invocation["contract_version"],
            "implementation_version": contract.implementation_version if contract else None,
            "data_version": response.data_version if response else "unknown",
            "parameters_hash": invocation["input_hash"], "invocation_id": invocation["invocation_id"],
            "actor": requesting_actor, "license_id": contract.license_id if contract else None,
            "executed_on": {"platform": self.platform, "execution_location": contract.execution_location if contract else None},
        }
        result = ToolResult(
            result_id=f"res_{invocation['invocation_id']}", invocation=invocation, outcome=outcome,
            values=response.values if response else [], records=response.records if response else [],
            provenance=provenance, error=error, absence_reason=absence_reason,
            required_inputs_manifest=manifest or [], warnings=response.warnings if response else [],
        )
        if absence_reason:
            vocab.require("absence_reason", absence_reason)
        payload = {
            "result_id": result.result_id, "invocation": invocation, "outcome": outcome, "values": result.values,
            "records": result.records, "provenance": provenance, "error": error, "absence_reason": absence_reason,
            "required_inputs_manifest": result.required_inputs_manifest, "warnings": result.warnings,
            "evidence_kind": contract.evidence_kind_produced if contract else None,
            "claim_strength_ceiling": contract.claim_strength_ceiling if contract else None,
            "supports_claim": None, "record_state": "returned",
        }
        result.artifact_id = self.core.artifacts.put("tool_result", payload)
        event_type = "tool.errored" if outcome == "failed" else "tool.returned"
        self.core.journal.append(
            stream_id, event_type, actor=make_actor("tool", invocation["tool_id"] or "broker"),
            ids=dict(ids or {}, tool_call_id=invocation["invocation_id"]), parent_seq=parent_seq,
            payload={"outcome": outcome, "result_id": result.result_id, "absence_reason": absence_reason,
                     "error_class": error["class"] if error else None, "n_values": len(result.values)},
            artifact_links=[{"kind": "tool_result", "id": result.artifact_id}],
            summary=f"{question_kind}: {outcome}")
        return result
