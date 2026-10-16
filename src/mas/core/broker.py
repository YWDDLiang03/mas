"""Tool Broker and Capability Registry (C13; design §7).

Tools are resolved by capability and question kind, never by name. Every call
passes pre-checks, is retried only for retryable error classes, and returns one
of the registered outcomes with a provenance block. The broker never writes
claim status: a successful call is not a validation (design §7.7).
"""

from __future__ import annotations

import copy
import json
import random
import sys
import time
from dataclasses import dataclass, field, fields
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


def host_platform() -> str:
    """Use the platform names tool contracts already declare; keep unknown hosts distinct."""
    if sys.platform.startswith("win") or sys.platform in ("cygwin", "msys"):
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    return sys.platform


def _cache_key(tool_id, contract_version, implementation_version, question_kind, inputs) -> str:
    return sha256_hex({"tool": tool_id, "v": contract_version, "implementation": implementation_version,
                       "q": question_kind, "in": inputs})


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
    source_retrieved_at: str | None = None
    local_derivation: dict[str, Any] | None = None


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
    def __init__(self, core: Core, *, sleep: Callable[[float], None] = time.sleep, platform: str | None = None):
        self.core = core
        self.sleep = sleep
        self.platform = platform if platform is not None else host_platform()
        self._providers: list[Provider] = []
        self._cache: dict[str, ToolResult] = {}
        self._replay_cache: dict[str, dict[str, Any]] = {}
        self._replay_manifest: dict[str, Any] | None = None
        self._replay_logged: set[tuple[str, str]] = set()
        self._has_called = False

    def seed_cache_from_runs(self, source_run_ids: list[str] | tuple[str, ...], *,
                             pubchem_record_projection: bool = False,
                             allow_terminal_sources: bool = False,
                             source_pins: dict[str, int] | None = None) -> dict[str, Any]:
        """Index exact successful/empty historical results from explicitly named completed runs.

        Opting into terminal sources reuses completed tool facts from interrupted
        sweeps, never a run verdict. Active/paused runs and failed/partial tool
        attempts remain ineligible. ``source_pins`` fixes each journal prefix.
        First listed run wins, then first event within that run. Results stay in their
        original artifacts and are loaded on demand; failed and partial calls are not
        converted to empty results or sampled anew by this operation.
        """
        if self._has_called or self._replay_manifest is not None:
            raise ValueError("historical tool replay must be configured once, before any tool call")
        source_run_ids = list(dict.fromkeys(source_run_ids))
        if not source_run_ids or any(not isinstance(ref, str) or not ref.startswith("run_") for ref in source_run_ids):
            raise ValueError("historical tool replay needs explicit run_ ids")
        if source_pins is not None and (set(source_pins) != set(source_run_ids) or
                any(type(pin) is not int or pin < 1 for pin in source_pins.values())):
            raise ValueError("historical tool replay needs one positive pinned sequence per source run")
        indexed: dict[str, dict[str, Any]] = {}
        sources = []
        projection_providers = [p for p in self._providers if pubchem_record_projection
                                and getattr(p, "historical_projection_policy", None) == "pubchem_descriptor_row_projection@v1"]
        if pubchem_record_projection and not projection_providers:
            raise ValueError("PubChem record projection was requested but its provider is not registered")
        projection_rows = []
        for run_id in source_run_ids:
            pin = source_pins[run_id] if source_pins is not None else self.core.journal.last_seq(run_id)
            row = self.core.store.db.execute(
                "SELECT body FROM events WHERE stream_id = ? AND event_type IN "
                "('run.created','run.started','run.resumed','run.paused','run.cancelled','run.completed',"
                "'run.unresolved','run.failed') AND seq<=? ORDER BY seq DESC LIMIT 1", (run_id, pin)).fetchone()
            terminal = json.loads(row[0]) if row else None
            accepted = {"run.completed", "run.cancelled", "run.failed", "run.unresolved"} if allow_terminal_sources else {"run.completed"}
            if terminal is None or terminal["event_type"] not in accepted or terminal.get("visibility", "default") not in ("default", "public"):
                required = "terminated public run" if allow_terminal_sources else "completed run"
                raise ValueError(f"tool replay source {run_id} is not a {required}")
            if source_pins is not None:
                last_state = self.core.store.db.execute(
                    "SELECT event_type FROM events WHERE stream_id=? AND event_type IN "
                    "('run.created','run.started','run.resumed','run.paused','run.cancelled','run.completed',"
                    "'run.unresolved','run.failed') ORDER BY seq DESC LIMIT 1", (run_id,)).fetchone()
                if not last_state or last_state[0] not in accepted or pin > self.core.journal.last_seq(run_id):
                    raise ValueError(f"tool replay source {run_id} is no longer a terminated pinned source")
            entries, skipped = [], {"unsuccessful": 0, "malformed": 0, "duplicate": 0}
            rows = self.core.store.db.execute(
                "SELECT body FROM events WHERE stream_id = ? AND seq<=? AND event_type IN ('tool.returned','tool.errored') "
                "ORDER BY seq", (run_id, pin))
            for (body,) in rows:
                event = json.loads(body)
                if (event.get("visibility", "default") not in ("default", "public") or
                        event["event_type"] != "tool.returned" or event["payload"].get("outcome") not in ("ok", "empty")):
                    skipped["unsuccessful"] += 1
                    continue
                refs = [link["id"] for link in event.get("artifact_links", []) if link.get("kind") == "tool_result"]
                if len(refs) != 1:
                    skipped["malformed"] += 1
                    continue
                artifact_id = refs[0]
                artifact = self.core.store.db.execute(
                    "SELECT body, sha256 FROM artifacts WHERE artifact_id = ? AND kind = 'tool_result'", (artifact_id,)).fetchone()
                if artifact is None:
                    skipped["malformed"] += 1
                    continue
                result = json.loads(artifact[0])["payload"]
                invocation, provenance = result.get("invocation") or {}, result.get("provenance") or {}
                required = ("result_id", "invocation", "outcome", "values", "records", "provenance")
                inputs = invocation.get("normalized_input")
                if (any(key not in result for key in required) or result["outcome"] not in ("ok", "empty")
                        or result.get("error") or result.get("absence_reason") or not isinstance(inputs, dict)
                        or not all(invocation.get(key) for key in ("tool_id", "contract_version", "question_kind"))
                        or not provenance.get("implementation_version") or not provenance.get("retrieved_at")
                        or provenance.get("tool_id") != invocation["tool_id"]
                        or provenance.get("contract_version") != invocation["contract_version"]
                        or invocation.get("input_hash") != sha256_hex(inputs)
                        or provenance.get("parameters_hash") != sha256_hex(inputs)):
                    skipped["malformed"] += 1
                    continue
                key = _cache_key(invocation["tool_id"], invocation["contract_version"], provenance["implementation_version"],
                                 invocation["question_kind"], inputs)
                if key in indexed:
                    skipped["duplicate"] += 1
                    continue
                source = {"source_run_id": run_id, "source_event_id": event["event_id"],
                          "source_seq": event["seq"], "source_request_seq": event.get("parent_seq"),
                          "source_artifact_id": artifact_id, "result_id": result["result_id"],
                          "retrieved_at": provenance["retrieved_at"], "cache_key": key,
                          "source_platform": (provenance.get("executed_on") or {}).get("platform")}
                if allow_terminal_sources or source_pins is not None:
                    source["source_artifact_sha256"] = artifact[1]
                indexed[key] = source
                entries.append(source)
                for provider in projection_providers:
                    contract = provider.contract
                    if (invocation["tool_id"] == contract.tool_id and invocation["contract_version"] == contract.contract_version
                            and provenance["implementation_version"] == contract.implementation_version):
                        projection_rows.append((provider, result, dict(source, source_artifact_sha256=artifact[1])))
            sources.append({"run_id": run_id, "completed_event_id": terminal["event_id"],
                            "completed_seq": terminal["seq"], "entries": len(entries),
                            "entries_digest": sha256_hex(entries), "skipped": skipped})
            if allow_terminal_sources or source_pins is not None:
                sources[-1].update(pinned_seq=pin, execution_state=terminal.get("state_to"),
                                   terminal_event_id=terminal["event_id"], terminal_seq=terminal["seq"])
                if terminal["event_type"] != "run.completed":
                    sources[-1].pop("completed_event_id")
                    sources[-1].pop("completed_seq")
        manifest = {"policy_version": 1, "mode": "exact_historical_tool_results", "source_run_ids": source_run_ids,
                    "selection": "first_source_then_first_event", "outcomes": ["ok", "empty"],
                    "matching_fields": ["tool_id", "contract_version", "implementation_version", "question_kind",
                                        "normalized_input"], "sources": sources, "cache_entries": len(indexed)}
        if pubchem_record_projection:
            for provider, result, source in projection_rows:
                provider.seed_historical_result(result, source)
            manifest.update({"policy_version": 2, "parameter_projections": [
                provider.historical_projection_manifest() for provider in projection_providers]})
        if allow_terminal_sources or source_pins is not None:
            manifest.update(policy_version=3, allow_terminal_sources=allow_terminal_sources,
                            source_pins={row["run_id"]: row["pinned_seq"] for row in sources},
                            source_unit="completed_tool_result", reuses_decisions=False)
        manifest["manifest_digest"] = sha256_hex(manifest)
        self._replay_cache, self._replay_manifest = indexed, manifest
        return copy.deepcopy(manifest)

    def replay_manifest(self) -> dict[str, Any] | None:
        return copy.deepcopy(self._replay_manifest)

    def _replay(self, stream_id, key, capability, question_kind, inputs, requesting_actor, ids) -> ToolResult:
        source = self._replay_cache[key]
        payload = self.core.artifacts.payload(source["source_artifact_id"])
        result = ToolResult(**{item.name: payload[item.name] for item in fields(ToolResult) if item.name in payload})
        result.artifact_id = source["source_artifact_id"]
        if (stream_id, key) not in self._replay_logged:
            self.core.journal.append(
                stream_id, "tool.returned", actor=make_actor("tool", result.invocation["tool_id"]),
                ids=dict(ids or {}, tool_call_id=result.invocation["invocation_id"]),
                payload={"outcome": result.outcome, "result_id": result.result_id,
                         "absence_reason": None, "error_class": None, "n_values": len(result.values),
                         "historical_replay": True, "fresh_tool_call": False, "charged_tool_calls": 0,
                         "replay_manifest_digest": self._replay_manifest["manifest_digest"], **source,
                         "current_request": {"capability": capability, "question_kind": question_kind,
                                             "input_hash": sha256_hex(inputs), "requesting_actor": requesting_actor}},
                artifact_links=[{"kind": "tool_result", "id": result.artifact_id}],
                summary=f"{question_kind}: historical {result.outcome} from {source['source_run_id']}")
            self._replay_logged.add((stream_id, key))
        return result

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
             budget: Any = None, required_value_kind: str | None = None,
             tool_ids: tuple[str, ...] | list[str] | None = None) -> ToolResult:
        """Dispatch to the first provider that attempts the question; `tool_ids` restricts and orders
        the providers (used to query one named evidence source at a time)."""
        self._has_called = True
        providers = self.resolve(capability, question_kind)
        if tool_ids is not None:
            by_id = {p.contract.tool_id: p for p in providers}
            providers = [by_id[t] for t in tool_ids if t in by_id]
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
        cache_key = _cache_key(contract.tool_id, contract.contract_version, contract.implementation_version,
                               question_kind, inputs)
        if cache_key in self._cache:
            return self._cache[cache_key]
        if cache_key in self._replay_cache and (contract.platform_independent_output
                                               or self._replay_cache[cache_key]["source_platform"] == self.platform):
            return self._replay(stream_id, cache_key, capability, question_kind, inputs, requesting_actor, ids)
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
                outcome = "empty" if response.outcome == "ok" and not (response.values or response.records) else response.outcome
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
        if response is not None and response.local_derivation is not None:
            if not response.source_retrieved_at:
                raise ValueError("a local historical projection must preserve its source retrieval date")
            invocation["provider_path"] = "in_process"
            provenance.update({"operation_kind": "local_historical_projection",
                               "derived_from": response.local_derivation,
                               "retrieved_at": response.source_retrieved_at, "processed_at": utc_now(),
                               "executed_on": {"platform": self.platform, "execution_location": "in_process"}})
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
                     "error_class": error["class"] if error else None, "n_values": len(result.values),
                     **({"operation_kind": "local_historical_projection", "fresh_retrieval": False,
                         "fresh_tool_call": False, "charged_tool_calls": 0,
                         **{key: response.local_derivation[key] for key in
                            ("source_artifact_id", "cache_file_sha256", "manifest_digest")
                            if key in response.local_derivation}}
                        if response is not None and response.local_derivation is not None else {})},
            artifact_links=[{"kind": "tool_result", "id": result.artifact_id}],
            summary=f"{question_kind}: {outcome}")
        return result
