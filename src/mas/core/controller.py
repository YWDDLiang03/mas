"""Run Controller (C15; design §6): binding, stages, the candidate sweep, checkpoints, resume, ending.

A single-pass (P0) run: bind → normalize → plan → resolve identities → sweep every
confirmed rule across every resolved candidate (breadth-first by rule, seeded order
within a rule, no short-circuit after a fail, a budget reserved per rule, a checkpoint
after each rule pass) → freeze the evidence snapshot → publish the leaderboard
snapshot → close. A run is `completed` when its sweep is complete; budget exhaustion
before then makes it `unresolved`. A finished run is never re-entered.
"""

from __future__ import annotations

import random
import threading
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from . import (assessor, constants, criteria, evidence, identity, leaderboard, ledger, measurement, sr_stage, supplements,
               task as task_mod, vocab)
from .budget import Budget
from .broker import host_platform as current_host_platform, _cache_key, VALUE_KIND_STRENGTH, STRENGTH_ORDER
from .canonical import sha256_hex
from .clock import utc_now
from .ids import new_id
from .journal import EVAL_STREAM, Event, actor as make_actor
from .runtime import Core

CONTROLLER = make_actor("controller", "C15", "run_controller")
STRATEGY = "strat@v1"
RUN_STAGES = ("identity", "assess", "snapshot")
DATABASE_FIRST = 0
LITERATURE_LAST = 1


class _ExistingFactsBroker:
    """Permit only already cached/exact replay facts. A miss never invokes a provider."""
    def __init__(self, broker, local_tool_ids=()):
        self.broker, self.local_tool_ids = broker, set(local_tool_ids)

    def __getattr__(self, key):
        return getattr(self.broker, key)

    def call(self, stream_id, capability, question_kind, inputs, **options):
        providers = self.broker.resolve(capability, question_kind)
        requested = options.get("tool_ids")
        if requested is not None:
            providers = sorted((p for p in providers if p.contract.tool_id in requested),
                               key=lambda p: list(requested).index(p.contract.tool_id))
        for provider in providers:
            c = provider.contract
            key = _cache_key(c.tool_id, c.contract_version, c.implementation_version, question_kind, inputs)
            source = getattr(self.broker, "_replay_cache", {}).get(key)
            local_fact = c.tool_id in self.local_tool_ids and c.execution_location == "in_process"
            projected = (getattr(provider, "historical_projection_policy", None) == "pubchem_descriptor_row_projection@v1"
                         and provider._historical_rows.get(provider._row_key(inputs)) is not None)
            if local_fact or projected or key in getattr(self.broker, "_cache", {}) or (source and
                    (c.platform_independent_output or source["source_platform"] == self.broker.platform)):
                return self.broker.call(stream_id, capability, question_kind, inputs,
                                        **dict(options, tool_ids=[c.tool_id]))
            cached = getattr(provider, "existing_response", None)
            response = cached(question_kind, inputs) if callable(cached) else None
            if response is not None:
                if not response.local_derivation or not response.source_retrieved_at:
                    raise ValueError("cached-only tool facts require pinned source provenance")
                if response.outcome not in ("ok", "empty"):
                    raise ValueError("cached-only providers may return completed facts only")
                if any(VALUE_KIND_STRENGTH.get(value.get("value_kind"), 0) > STRENGTH_ORDER[c.claim_strength_ceiling]
                       for value in response.values):
                    raise ValueError("cached-only fact exceeds its tool contract's strength")
                result = self.broker._record(stream_id, c, capability, question_kind, inputs,
                    options["requesting_actor"], options.get("ids"),
                    outcome="empty" if not (response.values or response.records) else response.outcome,
                    response=response)
                self.broker._cache[key] = result
                return result
        return self.broker._record(stream_id, None, capability, question_kind, inputs,
                                  options["requesting_actor"], options.get("ids"), outcome="not_attempted",
                                  absence_reason="existing_evidence_unavailable")


def _reads_literature(item: dict[str, Any]) -> bool:
    """Whether this run reads the literature for one rule of its set.

    Not `criteria.is_literature_bound` alone: an attribute may declare a literature route beside
    its database routes, and a run that holds `literature_retrieval` out scores that rule on the
    databases (`criteria.DEFERRAL_SCOPES`). Such a cell costs no search, no document and no model
    turn, so it belongs in the database phase and must not be offered to the reader as one of the
    attributes a paper is read for.
    """
    return (criteria.is_literature_bound(item["attribute"])
            and "literature_retrieval" not in item.get("deferred_capabilities", ()))


class RunError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


class _PassBudget:
    """Charges the run budget, refusing once this rule pass has used its reservation."""

    def __init__(self, run_budget: Budget, reservation: dict[str, float]):
        self.run_budget, self.reservation, self.used = run_budget, reservation, {}
        self._lock = threading.Lock()

    def blocked(self) -> bool:
        return any(self.used.get(kind, 0) >= cap for kind, cap in self.reservation.items()) or \
            self.run_budget.exhausted("tool_calls")

    def try_charge(self, kind: str, amount: float = 1) -> bool:
        with self._lock:
            cap = self.reservation.get(kind)
            if cap is not None and self.used.get(kind, 0) + amount > cap:
                return False
            if not self.run_budget.try_charge(kind, amount):
                return False
            self.used[kind] = self.used.get(kind, 0) + amount
            return True

    # provider spend is accounted on the run budget; a rule pass does not reserve it
    @property
    def root(self) -> Budget:
        return self.run_budget

    def allows(self, kind: str) -> bool:
        return self.run_budget.allows(kind)

    def record(self, kind: str, amount: float) -> list[str]:
        return self.run_budget.record(kind, amount)

    def exhausted(self, kind: str) -> bool:
        return self.run_budget.exhausted(kind)


@dataclass
class RunState:
    run_id: str
    binding: dict[str, Any]
    task_context: dict[str, Any]
    rule_set: dict[str, Any]
    budget: Budget
    attempt_id: str
    round_id: str
    identities: dict[str, dict[str, Any]] = field(default_factory=dict)
    cells: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    rules: list[dict[str, Any]] = field(default_factory=list)
    reused: int = 0
    settings: dict[str, Any] = field(default_factory=dict)   # resolved setting values bound at start


class RunController:
    def __init__(self, core: Core, broker, roster=None, *, adapter: dict[str, Any], host_platform: str | None = None,
                 implementation: dict[str, Any] | None = None, workers: int = 1,
                 evidence_hook=None, identity_hook=None, control_hook=None, budget: Budget | None = None,
                 existing_local_tool_ids: tuple[str, ...] = (), evidence_manifest: dict[str, Any] | None = None):
        self.core, self.broker, self.roster = core, broker, roster
        self.implementation = implementation or {}
        self.workers = max(1, workers)  # concurrent candidates in the literature phase (model calls dominate)
        self._cells_lock = threading.Lock()
        self.adapter = adapter  # {"adapter_id", "adapter_version", "primary_scheme"}
        self.evidence_hook, self.identity_hook, self.control_hook = evidence_hook, identity_hook, control_hook
        self.shared_budget, self.existing_local_tool_ids = budget, tuple(existing_local_tool_ids)
        self.evidence_manifest = copy.deepcopy(evidence_manifest)
        self.host_platform = host_platform if host_platform is not None else getattr(broker, "platform", current_host_platform())

    # --- journal helpers ----------------------------------------------------------
    def _emit(self, run_id: str, kind: str, **kwargs):
        event = self.core.journal.append(run_id, kind, actor=kwargs.pop("actor", CONTROLLER), **kwargs)
        if kind == "stage.closed":
            closed = sum(1 for e in self.core.journal.replay(run_id) if e.event_type == "stage.closed")
            self.core.journal.append(run_id, "progress.estimate_revised", actor=CONTROLLER, payload={"reason": "stage closed"},
                                     progress={"scope": "run", "denominator_kind": "enumerated_fixed",
                                               "completed": closed, "planned": len(RUN_STAGES)})
        return event

    # --- start ----------------------------------------------------------------------
    def start(self, task_id: str, *, by: dict[str, Any], rule_set_ref: str | None = None, policy_arm: str = "P0",
              screening_rounds: int = 1, budget_envelope: dict[str, Any] | None = None, sweep_seed: int | None = None,
              memory_mode: str = "cold", evidence_cutoff: str | None = None, chain_id: str | None = None,
              continues_run_id: str | None = None, continuation_kind: str = "root", candidate_limit: int | None = None,
              execute: bool = True, settings: Any = None, measurement_profile_ref: str | None = None,
              evaluation_mode: str | None = None, qualification_policy: str | None = None,
              evidence_mode: str | None = None, reuse_from_run_id: str | None = None) -> str:
        """Bind and (by default) execute a run. `settings` is a resolved core.config.Config: its hash and
        layer record are bound, its verdict-affecting values are registered as run-scoped constants,
        and its budget policy decides whether reaching the spend cap stops the run."""
        vocab.require("policy_arm", policy_arm)
        vocab.require("memory_mode", memory_mode)
        vocab.require("continuation_kind", continuation_kind)
        context = task_mod.get(self.core, task_id)
        blocking = task_mod.blocking_unknowns(context)
        if blocking:
            raise RunError("rejected_not_permitted_in_state", f"{len(blocking)} blocking unknowns are open")
        rule_set = criteria.rule_set(self.core, task_id, rule_set_ref)
        sweep_seed = sweep_seed if sweep_seed is not None else (settings["run.seed"] if settings is not None else 0)
        cutoff = evidence_cutoff or (settings["search.date_to"] if settings is not None else "") or None
        profile = None
        if measurement_profile_ref:
            cutoff = cutoff or measurement.load(self.core, task_id, measurement_profile_ref)["policy"]["evidence_cutoff"]
            effective = settings.values if settings is not None else {
                "rank.coverage_floor": constants.value(self.core, "const_ranking_coverage_floor"),
                "rank.mandated_coverage_floor": constants.value(self.core, "const_mandated_coverage_floor")}
            profile = measurement.verify(
                self.core, task_id, measurement_profile_ref, context=context, rule_set=rule_set,
                sweep_seed=sweep_seed, evidence_cutoff=cutoff,
                candidate_limit=candidate_limit, settings=effective,
                config_hash=settings.hash() if settings is not None else None, implementation=self.implementation)
            measurement.ensure_unused(self.core, task_id, measurement_profile_ref)
        scoring = profile["policy"]["scoring_policy"] if profile else {}
        modes = {}
        for key, explicit, fallback in (("evaluation_mode", evaluation_mode, "full"),
                                        ("qualification_policy", qualification_policy, "legacy"),
                                        ("evidence_mode", evidence_mode, "retrieve")):
            config_key = {"evaluation_mode": "evaluation.mode", "qualification_policy": "qualification.policy",
                          "evidence_mode": "evidence.mode"}[key]
            # A historical profile with no versioned mode keeps its historical behavior.
            value = scoring.get(key, fallback) if profile else explicit or (settings[config_key] if settings else fallback)
            if explicit is not None and profile and explicit != value:
                raise RunError("rejected_invalid", f"{key} differs from the registered profile")
            modes[key] = value
        if modes["evaluation_mode"] not in ("staged", "full") or modes["qualification_policy"] not in ("legacy", assessor.QUALIFICATION_POLICY) \
                or modes["evidence_mode"] not in ("existing_only", "retrieve"):
            raise RunError("rejected_invalid", "invalid evaluation, qualification or evidence mode")
        if modes["qualification_policy"] == assessor.QUALIFICATION_POLICY and (rule_set.get("ordering_method") or {}).get("kind") == "symbolic_expression":
            raise RunError("rejected_invalid", "qualification_first_v1 currently requires weighted preference scoring")
        run_id = new_id("run")
        settings_ref, budget_policy = None, {}
        if settings is not None:
            settings_ref = {"config_hash": settings.hash(), "preset": settings.preset, "profile": settings.profile,
                            "layers_artifact_id": self.core.artifacts.put("config_layers", settings.layer_record())}
            budget_envelope = {"usd": settings["budget.usd_max"], **({k: v for k, v in (
                ("llm_turns", settings["budget.llm_turns"]), ("tool_calls", settings["budget.tool_calls"])) if v}),
                **(budget_envelope or {})}
            budget_policy = {"on_exhaust": settings["budget.on_exhaust"], "warn_at": settings["budget.warn_at"],
                             "soft_kinds": ["usd"] if settings["budget.on_exhaust"] == "warn_continue" else []}
        binding = {
            "bind_id": f"bind_{run_id}", "run_id": run_id,
            "task_context_id@v": f"{task_id}@v{context['version']}", "case_id@v": context.get("case_ref"),
            "adapter_id": self.adapter["adapter_id"], "adapter_version": self.adapter["adapter_version"],
            "rules@v": rule_set["rule_set_ref"], "strat@v": STRATEGY, "policy_arm": policy_arm,
            "group_id": context.get("group_id", task_mod.DEFAULT_GROUP), "chain_id": chain_id or new_id("chain"),
            "continues_run_id": continues_run_id, "continuation_kind": continuation_kind, "branch_label": None,
            "edits_since_parent": [], "budget_extension_ref": None, "protocol_ref": None, "preregistration_ref": None,
            "promotion_policy_version": "promotion-1",
            "role_bindings": self.roster.role_bindings() if self.roster else [],
            "screening_rounds_budget": screening_rounds, "sweep_scope": "full_universe", "sweep_seed": sweep_seed,
            "memory_mode": memory_mode, "evidence_cutoff": cutoff or utc_now()[:10],
            "host": {"platform": self.host_platform, "service_host_version": "mas-0.1.0"},
            "tool_availability_snapshot": self.broker.manifest(),
            "known_reference_outcome_disclosure": [s for s in context.get("seed_candidates", []) if s.get("is_reference_outcome")],
            "derivation_configuration": "reference_disclosed", "budget_envelope": budget_envelope or {},
            "candidate_limit": candidate_limit, "implementation": self.implementation,
            "settings": settings_ref, "budget_policy": budget_policy,
            "shared_budget_initial": self.shared_budget.snapshot() if self.shared_budget else None,
            "existing_local_tool_ids": list(self.existing_local_tool_ids),
            "evidence_manifest": self.evidence_manifest,
            "assessor_version": "assessor-qualification-1" if modes["qualification_policy"] == assessor.QUALIFICATION_POLICY else assessor.ASSESSOR_VERSION,
            "reuse_from_run_id": reuse_from_run_id,
            "measurement_profile_ref": measurement_profile_ref,
            "measurement_profile_digest": profile["digest"] if profile else None,
            **modes,
            "tool_replay": getattr(self.broker, "replay_manifest", lambda: None)(),
            "verified_supplements": supplements.binding(self.core, context),
            "bound_at": utc_now(), "bound_by": by,
        }
        if self.shared_budget:
            binding["budget_envelope"] = dict(self.shared_budget.caps)
        if reuse_from_run_id:
            self._reuse_source(binding, reuse_from_run_id)
        artifact_id = self.core.artifacts.put("run_binding", binding)
        self._emit(run_id, "run.created", actor=by, ids={"task_id": task_id, "run_id": run_id}, state_to="queued",
                   payload={"binding_artifact_id": artifact_id, "task_id": task_id, "chain_id": binding["chain_id"]},
                   artifact_links=[{"kind": "run_binding", "id": artifact_id}], summary=f"run bound to {rule_set['rule_set_ref']}")
        if settings is not None:
            from .config import register_constants
            register_constants(self.core, settings, by=by, stream_id=run_id)
        if continues_run_id:
            self.core.journal.append(task_id, "run.continued", actor=by, payload={
                "parent_run_id": continues_run_id, "run_id": run_id, "continuation_kind": continuation_kind})
        if execute:
            self.execute(run_id)
        return run_id

    # --- execution -------------------------------------------------------------------
    def _load(self, run_id: str) -> RunState:
        events = self.core.journal.replay(run_id)
        if not events or events[0].event_type != "run.created":
            raise RunError("rejected_invalid", f"{run_id} is not a run")
        binding = self.core.artifacts.payload(events[0].payload["binding_artifact_id"])
        if binding.get("evidence_manifest") != self.evidence_manifest:
            raise RunError("rejected_invalid", "the bound evidence hook manifest changed")
        if binding.get("tool_replay") != getattr(self.broker, "replay_manifest", lambda: None)():
            raise RunError("tool_replay_policy_drift", "the bound historical tool replay sources changed")
        if binding.get("run_purpose", "sweep") != "sweep":
            raise RunError("rejected_invalid", f"{run_id} is a {binding['run_purpose']} run, not a candidate sweep")
        task_id = events[0].payload["task_id"]
        context = task_mod.get(self.core, task_id, int(binding["task_context_id@v"].rsplit("@v", 1)[1]))
        if (binding.get("verified_supplements") or supplements.binding(self.core, {})) != supplements.binding(self.core, context):
            raise RunError("rejected_invalid", "the bound verified supplement refs or digests changed")
        rule_set = criteria.rule_set(self.core, task_id, binding["rules@v"])
        policy = binding.get("budget_policy") or {}
        budget = Budget(binding["budget_envelope"], soft_kinds=tuple(policy.get("soft_kinds", ())),
                        warn_at=policy.get("warn_at"))
        if self.shared_budget is not None:
            if self.shared_budget.caps != binding["budget_envelope"]:
                raise RunError("rejected_invalid", "shared budget caps differ from the bound workflow budget")
            budget = self.shared_budget
        elif binding.get("shared_budget_initial"):
            budget.used.update(binding["shared_budget_initial"].get("used") or {})
            for event in events:
                if event.budget:
                    budget.used.update(event.budget.get("used") or {})
        settings_values = {}
        if (binding.get("settings") or {}).get("layers_artifact_id"):
            layers = self.core.artifacts.payload(binding["settings"]["layers_artifact_id"])
            settings_values = {row["key"]: row["value"] for row in layers["settings"]}
        state = RunState(run_id, binding, context, rule_set, budget,
                         attempt_id=f"att_{run_id}_1", round_id=f"round_{run_id}_1", settings=settings_values)
        for entry in rule_set["entries"]:
            rule = criteria.load(self.core, entry["rule_ref"], task_id)
            attr = criteria.load(self.core, entry["attribute_ref"], task_id)
            # The capabilities this run holds out for this rule, from the entry the confirmation
            # wrote (`criteria.DEFERRAL_SCOPES`): the rule scores on its other routes, and this is
            # what makes the run ask those and not the deferred one.
            state.rules.append({"entry": entry, "rule": rule, "attribute": attr,
                                "deferred_capabilities": criteria.entry_deferred_capabilities(entry)})
        state.rules.sort(key=lambda r: (LITERATURE_LAST if _reads_literature(r) else DATABASE_FIRST,
                                        r["entry"]["rule_ref"]))
        self._measurement_profile(state)
        return state

    def _measurement_profile(self, st: RunState) -> dict[str, Any] | None:
        ref = st.binding.get("measurement_profile_ref")
        if not ref:
            return None
        effective = dict(st.settings)
        effective.update({
            "rank.coverage_floor": constants.value(self.core, "const_ranking_coverage_floor", (EVAL_STREAM, st.run_id)),
            "rank.mandated_coverage_floor": constants.value(self.core, "const_mandated_coverage_floor",
                                                           (EVAL_STREAM, st.run_id))})
        return measurement.verify(
            self.core, st.task_context["task_context_id"], ref, context=st.task_context, rule_set=st.rule_set,
            sweep_seed=st.binding["sweep_seed"], evidence_cutoff=st.binding["evidence_cutoff"],
            candidate_limit=st.binding.get("candidate_limit"), settings=effective,
            config_hash=(st.binding.get("settings") or {}).get("config_hash"), implementation=self.implementation,
            bound_digest=st.binding.get("measurement_profile_digest"))

    def current_state(self, run_id: str) -> str | None:
        state = None
        for event in self.core.journal.replay(run_id):
            if event.event_type.startswith("run.") and event.state_to:
                state = event.state_to
        return state

    def execute(self, run_id: str, *, resuming: bool = False) -> str:
        run_state = self.current_state(run_id)
        if run_state in vocab.RUN_TERMINAL_STATES:
            raise RunError("rejected_not_permitted_in_state", f"{run_id} has ended ({run_state}); continue it instead")
        st = self._load(run_id)
        attempts = [e for e in self.core.journal.replay(run_id) if e.event_type == "attempt.started"]
        st.attempt_id = f"att_{run_id}_{len(attempts) + 1}"
        ids = {"task_id": st.task_context["task_context_id"], "run_id": run_id, "attempt_id": st.attempt_id,
               "round_id": st.round_id}
        if resuming:
            self._emit(run_id, "attempt.finalized", ids=ids, payload={"finalized_by": "controller",
                                                                     "attempt_id": f"att_{run_id}_{len(attempts)}"})
            self._emit(run_id, "run.resumed", ids=ids, state_from=run_state, state_to="running")
        else:
            self._emit(run_id, "run.started", ids=ids, state_from="queued", state_to="running")
        self._emit(run_id, "attempt.started", ids=ids, payload={"attempt_id": st.attempt_id, "resuming": resuming})
        if not resuming:
            plan = {"plan_id": f"plan_{run_id}@v1", "stages": list(RUN_STAGES),
                    "steps": [{"step": f"rule pass {r['entry']['rule_ref']}", "owner": "C11"} for r in st.rules],
                    "budget_envelope": st.binding["budget_envelope"]}
            plan_artifact = self.core.artifacts.put("plan", plan)
            self._emit(run_id, "plan.recorded", ids=ids, payload={"plan_artifact_id": plan_artifact,
                                                                 "stages_declared": len(plan["stages"])},
                       progress={"scope": "run", "denominator_kind": "enumerated_fixed", "completed": 0,
                                 "planned": len(plan["stages"])})
            self._emit(run_id, "round.opened", ids=ids, payload={"round_id": st.round_id, "trigger": "first_round"})
        self._restore(st)
        if st.binding.get("reuse_from_run_id"):
            self._reuse_cells(st, ids)
        return self._run(st, ids)

    def _reuse_source(self, binding, source_run_id):
        first = self.core.journal.replay(source_run_id, 1, 1)
        if not first or first[0].event_type != "run.created":
            raise RunError("rejected_invalid", "reuse source must be a terminated screening run")
        source = self.core.artifacts.payload(first[0].payload["binding_artifact_id"])
        last = self.core.store.db.execute("SELECT body FROM events WHERE stream_id = ? AND event_type IN "
            "('run.created','run.started','run.resumed','run.paused','run.cancelled','run.completed','run.unresolved','run.failed') "
            "ORDER BY seq DESC LIMIT 1", (source_run_id,)).fetchone()
        source_state = json.loads(last[0]).get("state_to") if last else None
        if source.get("run_purpose", "sweep") != "sweep" or source_state not in vocab.RUN_TERMINAL_STATES:
            raise RunError("rejected_invalid", "reuse source must be a terminated screening run")
        if (self.evidence_hook or self.identity_hook) and not self.evidence_manifest:
            raise RunError("rejected_invalid", "hook-based continuation reuse requires a fixed evidence_manifest")
        keys = ("task_context_id@v", "evidence_cutoff", "tool_availability_snapshot", "tool_replay",
                "verified_supplements", "existing_local_tool_ids", "evidence_manifest")
        for key in keys:
            default = [] if key == "existing_local_tool_ids" else None
            if source.get(key, default) != binding.get(key, default):
                raise RunError("rejected_invalid", f"reuse policy drift: {key}")
        for key, default in (("qualification_policy", "legacy"), ("evaluation_mode", "full"),
                             ("evidence_mode", "retrieve"), ("assessor_version", assessor.ASSESSOR_VERSION)):
            if source.get(key, default) != binding.get(key, default):
                raise RunError("rejected_invalid", f"reuse policy drift: {key}")
        def retrieval_settings(record):
            ref = (record.get("settings") or {}).get("layers_artifact_id")
            rows = self.core.artifacts.payload(ref)["settings"] if ref else []
            return {row["key"]: row["value"] for row in rows if row["key"].split(".", 1)[0]
                    in ("search", "read", "sources", "predict", "evidence")}
        if retrieval_settings(source) != retrieval_settings(binding):
            raise RunError("rejected_invalid", "reuse policy drift: retrieval settings")
        return source

    def _reuse_cells(self, st, ids):
        source_run = st.binding["reuse_from_run_id"]
        source_binding = self._reuse_source(st.binding, source_run)
        source_rules = criteria.rule_set(self.core, st.task_context["task_context_id"], source_binding["rules@v"])
        source_entries = {entry["rule_ref"]: entry for entry in source_rules["entries"]}
        allowed = {(r["entry"]["rule_ref"], r["entry"]["attribute_ref"]) for r in st.rules}
        current_entries = {r["entry"]["rule_ref"]: r["entry"] for r in st.rules}
        planned = len(st.task_context["candidate_universe"].get("members") or []) * len(st.rules)
        rows = self.core.store.db.execute("SELECT body FROM events WHERE stream_id = ? AND event_type IN "
                                         "('identity.resolved','candidate.assessed') ORDER BY seq", (source_run,))
        for (body,) in rows:
            event = Event.from_record(json.loads(body))
            if event.event_type == "identity.resolved":
                record = self.core.artifacts.payload(event.payload["artifact_id"])
                if record["candidate_id"] not in st.identities:
                    st.identities[record["candidate_id"]] = record
                    self._emit(st.run_id, "identity.resolved", ids=ids, payload={**event.payload,
                        "source_run_id": source_run, "source_event_id": event.event_id})
            elif event.event_type == "candidate.assessed":
                cell = self.core.artifacts.payload(event.payload["artifact_id"])
                key = (cell["rule_ref"], cell["candidate_ref"])
                if key in st.cells or (cell["rule_ref"], cell["attribute_ref"]) not in allowed \
                        or cell["verdict"] == "not_assessed" or cell.get("tool_error_ref"):
                    continue
                before = source_entries.get(cell["rule_ref"], {})
                after = current_entries[cell["rule_ref"]]
                if any(before.get(key) != after.get(key) for key in ("scoring_routes", "deferred_routes")):
                    continue
                if cell["assessed_by"]["model_or_tool_version"] != st.binding["assessor_version"]:
                    continue
                reason = self.core.artifacts.payload(event.payload["reason_artifact_id"])
                reused = dict(cell, **{"rules@v": st.rule_set["rule_set_ref"]})
                self._record_cell(st, reused, reason, ids, planned, reuse={"decision": "reused",
                    "source_run_id": source_run, "source_event_id": event.event_id,
                    "source_assessment_artifact_id": event.payload["artifact_id"],
                    "source_reason_artifact_id": event.payload["reason_artifact_id"],
                    "source_rules@v": cell["rules@v"]})

    def _restore(self, st: RunState) -> None:
        """Reload identities and assessed cells already in the journal (resume reuse, design §7.2)."""
        for event in self.core.journal.replay(st.run_id):
            if event.event_type == "identity.resolved":
                record = self.core.artifacts.payload(event.payload["artifact_id"])
                st.identities[record["candidate_id"]] = record
            elif event.event_type == "candidate.assessed":
                cell = self.core.artifacts.payload(event.payload["artifact_id"])
                st.cells[(cell["rule_ref"], cell["candidate_ref"])] = cell

    def _run(self, st: RunState, ids: dict[str, Any]) -> str:
        run_id = st.run_id
        members = list(st.task_context["candidate_universe"].get("members") or [])
        members += [s["candidate_ref"] for s in st.task_context.get("seed_candidates", []) if s["candidate_ref"] not in members]
        if st.binding.get("candidate_limit"):
            members = members[: st.binding["candidate_limit"]]
        stopped = self._cooperate(st, ids)
        if stopped:
            return stopped
        # identity first (design §6.6 step 1)
        new_policy = st.binding.get("qualification_policy") == assessor.QUALIFICATION_POLICY
        known_labels = {record.get("input_label") for record in st.identities.values()}
        remaining_members = [member for member in members if member not in known_labels] if new_policy else members
        if not st.identities or (new_policy and remaining_members):
            self._emit(run_id, "stage.opened", ids=ids, payload={"stage": "identity"},
                       progress={"scope": "stage:identity", "denominator_kind": "enumerated_fixed", "completed": 0,
                                 "planned": len(members)})
            request = {"run_id": run_id, "task_id": st.task_context["task_context_id"], "task_context": st.task_context,
                       "members": remaining_members, "primary_scheme": self.adapter["primary_scheme"],
                       "evidence_mode": st.binding.get("evidence_mode", "retrieve"), "ids": ids, "budget": st.budget,
                       "broker": self._facts_broker(st)}
            records = self.identity_hook(request) if self.identity_hook else None
            if records is None:
                records = []
                for member in remaining_members:
                    stopped = self._cooperate(st, ids)
                    if stopped:
                        return stopped
                    records.extend(identity.resolve_universe(self.core, self._facts_broker(st), run_id, [member],
                                                primary_scheme=self.adapter["primary_scheme"],
                                                capability="identity_resolution", ids=ids, budget=st.budget))
            elif self.identity_hook:
                for record in records:
                    artifact_id = self.core.artifacts.put("identity_record", record)
                    self._emit(run_id, "identity.resolved", ids=ids,
                               payload={"artifact_id": artifact_id, "candidate_id": record["candidate_id"]})
            st.identities.update({r["candidate_id"]: r for r in records})
            self._emit(run_id, "stage.closed", ids=ids, payload={"stage": "identity",
                                                                "resolved": sum(identity.is_resolved(r) for r in st.identities.values())},
                       state_to="completed", progress={"scope": "stage:identity", "denominator_kind": "enumerated_fixed",
                                                       "completed": len(st.identities), "planned": len(members)})
        elif new_policy and not self._stage_closed(st, "identity"):
            self._emit(run_id, "stage.closed", ids=ids, state_to="completed", payload={"stage": "identity", "reused": True},
                       progress={"scope": "stage:identity", "denominator_kind": "enumerated_fixed", "completed": len(members), "planned": len(members)})
        candidates = sorted(st.identities)
        if st.binding.get("qualification_policy") == assessor.QUALIFICATION_POLICY:
            return self._run_qualification(st, ids, candidates)
        planned_cells = len(candidates) * len(st.rules)
        self._emit(run_id, "stage.opened", ids=ids, payload={"stage": "assess", "planned_cells": planned_cells},
                   progress={"scope": "stage:assess", "denominator_kind": "enumerated_fixed",
                             "completed": len(st.cells), "planned": planned_cells})
        budget_cut = False
        cache = evidence.LiteratureCache()
        # The sweep is breadth-first by rule for database rules and breadth-first by *candidate* for
        # literature rules, because that is the unit the reading is bought in: one read of one paper
        # for one candidate is extracted for every literature attribute at once, so every literature
        # cell of a candidate is assessed against that candidate's whole reading (`_literature_pass`).
        database_rules = [r for r in st.rules if not _reads_literature(r)]
        literature_rules = [r for r in st.rules if _reads_literature(r)]
        for index, item in enumerate(database_rules):
            rule_ref = item["entry"]["rule_ref"]
            # The literature phase is one more reservation holder, not one per literature rule: its
            # rules share a single reading, so reserving per rule would hold back budget for passes
            # that cost nothing of their own.
            remaining_passes = len(database_rules) - index + (1 if literature_rules else 0)
            reservation = {k: (st.budget.remaining(k) or 0) / remaining_passes
                           for k in ("tool_calls", "llm_turns") if st.budget.remaining(k) is not None}
            pass_budget = _PassBudget(st.budget, reservation)
            order = list(candidates)
            random.Random(f"{st.binding['sweep_seed']}:{rule_ref}").shuffle(order)
            step_id = f"step_{st.round_id}_{index + 1}"
            step_ids = dict(ids, step_id=step_id)
            self._emit(run_id, "step.started", ids=step_ids, payload={"rule_ref": rule_ref, "candidates": len(order)},
                       question=f"apply {rule_ref} to every resolved candidate")
            todo = [c for c in order if (rule_ref, c) not in st.cells]
            st.reused += len(order) - len(todo)

            # WHY this pass runs its candidates through the same pool the literature pass uses
            # (measured 15 October 2026 the hard way): a measured-cell sweep of 3,177 candidates x 11
            # rules is one tool round trip per cell, and serially that is ~120 cells/min — about five
            # hours for one screen, with the process four-fifths idle on network waits. The cells of
            # one rule pass are independent of one another (each gathers its own evidence and the
            # journal is append-only), which is the same argument `_literature_pass` already relies
            # on; `assess.workers` is the operator's bound on how many may be in flight at once.
            def work(candidate_id: str) -> bool:
                cell, reason = self._assess(st, item, candidate_id, pass_budget, step_ids, cache)
                self._record_cell(st, cell, reason, step_ids, planned_cells)
                return (cell["verdict"] == "not_assessed"
                        and cell["not_assessed_reason"] == "budget_exhausted")

            if self.workers > 1 and len(todo) > 1:
                with ThreadPoolExecutor(max_workers=self.workers) as pool:
                    cut_here = any(list(pool.map(work, todo)))
            else:
                cut_here = any([work(candidate_id) for candidate_id in todo])
            budget_cut = cut_here or budget_cut
            self._emit(run_id, "step.completed", ids=step_ids, state_to="completed",
                       payload={"rule_ref": rule_ref, "budget_used": pass_budget.used})
            self._emit(run_id, "checkpoint.written", ids=dict(step_ids, checkpoint_id=f"ckpt_{run_id}_{index + 1}"),
                       payload={"sweep_cursor": {"rule_ref": rule_ref, "seed": st.binding["sweep_seed"],
                                                 "completed_candidate_count": len(order),
                                                 "completed_cell_refs_hash": self._cell_refs_hash(st)},
                                "next_rule_index": index + 1})
        if literature_rules:
            budget_cut = self._literature_pass(st, ids, literature_rules, candidates, planned_cells,
                                               steps_done=len(database_rules), cache=cache) or budget_cut
        self._emit(run_id, "stage.closed", ids=ids, state_to="completed", payload={"stage": "assess"},
                   progress={"scope": "stage:assess", "denominator_kind": "enumerated_fixed",
                             "completed": len(st.cells), "planned": planned_cells})
        return self._finish(st, ids, budget_cut)

    def _facts_broker(self, st):
        return _ExistingFactsBroker(self.broker, st.binding.get("existing_local_tool_ids", ())) \
            if st.binding.get("evidence_mode") == "existing_only" else self.broker

    def _stage_closed(self, st, stage):
        return self.core.store.db.execute("SELECT 1 FROM events WHERE stream_id = ? AND event_type = 'stage.closed' "
            "AND json_extract(body, '$.payload.stage') = ? LIMIT 1", (st.run_id, stage)).fetchone() is not None

    def _cooperate(self, st, ids):
        action = self.control_hook(st.run_id) if self.control_hook else None
        if action not in (None, "pause", "cancel"):
            raise RunError("rejected_invalid", "control_hook must return None, pause or cancel")
        if action is None:
            return None
        state = "paused" if action == "pause" else "cancelled"
        self._emit(st.run_id, "checkpoint.written", ids=ids,
                   payload={"control_action": action, "completed_cell_refs_hash": self._cell_refs_hash(st)})
        self._emit(st.run_id, f"run.{state}", ids=ids, state_from="running", state_to=state,
                   termination_reason=None if action == "pause" else "cancelled",
                   payload={"control_action": action, "cooperative": True})
        return state

    def _run_qualification(self, st, ids, candidates):
        """Hard conditions first; unknowns continue, only a verified direct failure can skip."""
        planned = len(candidates) * len(st.rules)
        if len(st.cells) == planned and self._stage_closed(st, "assess"):
            st.reused += len(st.cells)
            cut = any(c.get("not_assessed_reason") == "budget_exhausted" for c in st.cells.values())
            return self._cooperate(st, ids) or self._finish(st, ids, cut)
        self._emit(st.run_id, "stage.opened", ids=ids, payload={"stage": "assess", "planned_cells": planned},
                   progress={"scope": "stage:assess", "denominator_kind": "enumerated_fixed", "completed": len(st.cells), "planned": planned})
        ordered = sorted(st.rules, key=lambda r: (r["rule"]["rule_kind"] != "hard_exclusion", _reads_literature(r), r["entry"]["rule_ref"]))
        cache, cut = evidence.LiteratureCache(), False
        reservation = {k: st.budget.remaining(k) for k in ("tool_calls", "llm_turns") if st.budget.remaining(k) is not None}
        budget = _PassBudget(st.budget, reservation)
        for candidate in candidates:
            cause = None
            for item in ordered:
                stopped = self._cooperate(st, ids)
                if stopped:
                    return stopped
                ref = item["entry"]["rule_ref"]
                prior = st.cells.get((ref, candidate))
                if prior is not None:
                    st.reused += 1
                    cell = prior
                elif cause and st.binding["evaluation_mode"] == "staged":
                    cell, reason = assessor.assess_cell(candidate={"candidate_id": candidate}, attribute=item["attribute"],
                        rule=item["rule"], rule_set_ref=st.rule_set["rule_set_ref"], claims=[], resolved=True,
                        not_assessed_reason="skipped_after_rejection", qualification_policy=assessor.QUALIFICATION_POLICY)
                    cell["skip_cause"] = reason["skip_cause"] = cause
                    self._record_cell(st, cell, reason, ids, planned)
                else:
                    cell, reason = self._assess(st, item, candidate, budget, ids, cache)
                    self._record_cell(st, cell, reason, ids, planned)
                if item["rule"]["rule_kind"] == "hard_exclusion" and cell["verdict"] == "fail" \
                        and assessor.direct_evidence(cell) and self._verified_hard(item):
                    cause = {"rule_ref": ref, "assessment_id": cell["assessment_id"], "reason_ref": cell.get("reason_ref")}
                cut = cut or cell.get("not_assessed_reason") == "budget_exhausted"
            self._emit(st.run_id, "checkpoint.written", ids=ids, payload={"candidate_ref": candidate,
                        "completed_cell_refs_hash": self._cell_refs_hash(st)})
        self._emit(st.run_id, "stage.closed", ids=ids, state_to="completed", payload={"stage": "assess"},
                   progress={"scope": "stage:assess", "denominator_kind": "enumerated_fixed", "completed": len(st.cells), "planned": planned})
        return self._cooperate(st, ids) or self._finish(st, ids, cut)

    @staticmethod
    def _verified_hard(item):
        return (item["rule"]["rule_kind"] == "hard_exclusion" and not item["entry"].get("disputed")
                and item["entry"].get("authority") in ("machine_adjudication", "human_scientific_approval"))

    def _literature_pass(self, st: RunState, ids: dict[str, Any], rules: list[dict[str, Any]],
                         candidates: list[str], planned_cells: int, *, steps_done: int, cache) -> bool:
        """One candidate at a time: read its literature once, then rule on it with every literature rule.

        WHY the candidate and not the rule is the unit here: one extraction of one paper tags claims
        for every literature attribute in the prompt, so a paper the hypertension query found also
        answers the bioavailability question -- but while each cell harvested only the papers its own
        query selected, those claims were paid for, admitted to the ledger, and never offered to a
        cell. Measured on the real path, 14 October 2026, 26 literature criteria x 2 candidates:
        375 claims recorded, 253 admitted, 70 offered to a cell, 6 of 52 cells value-bearing where
        the ledger supported 16. Reading the union first costs no extra call -- it is the same set of
        documents the per-cell reads already fetched through the memo -- and it keeps a cell's claims
        independent of which other cell finished first, which `assess.workers > 1` would otherwise
        decide.

        A step and a checkpoint per candidate rather than per rule, for the same reason: the
        candidate is what the work and the spend are organized by.
        """
        run_id = st.run_id
        reservation = {k: (st.budget.remaining(k) or 0)
                       for k in ("tool_calls", "llm_turns") if st.budget.remaining(k) is not None}
        pass_budget = _PassBudget(st.budget, reservation)
        order = list(candidates)
        random.Random(f"{st.binding['sweep_seed']}:literature").shuffle(order)
        rule_refs = [r["entry"]["rule_ref"] for r in rules]
        attributes = [r["attribute"] for r in rules]
        todo = []
        for candidate_id in order:
            missing = [r for r in rules if (r["entry"]["rule_ref"], candidate_id) not in st.cells]
            st.reused += len(rules) - len(missing)
            if missing:
                todo.append(candidate_id)

        def work(job: tuple[int, str]) -> bool:
            position, candidate_id = job
            step_ids = dict(ids, step_id=f"step_{st.round_id}_{steps_done + position + 1}")
            self._emit(run_id, "step.started", ids=step_ids,
                       payload={"candidate_ref": candidate_id, "rule_refs": rule_refs},
                       question=f"read {candidate_id}'s literature once and apply {len(rule_refs)} literature rule(s)")
            record = st.identities[candidate_id]
            reading, refused = None, False
            if identity.is_resolved(record) and not pass_budget.blocked() and not st.budget.exhausted("llm_turns"):
                try:
                    reading = evidence.read_literature(
                        self.core, self.broker, self.roster, run_id,
                        candidate={"candidate_id": candidate_id, "label": record.get("preferred_label")},
                        identity=record, attributes=attributes, objective_text=st.task_context["objective_text"],
                        cutoff_date=st.binding["evidence_cutoff"], budget=pass_budget, ids=step_ids, cache=cache,
                        case_sources=st.task_context.get("case_source_documents", []),
                        sources=st.settings.get("search.sources"),
                        max_documents=st.settings.get("read.max_papers_per_candidate", 2),
                        limit_per_query=st.settings.get("search.results_per_query", 10),
                        max_chars=st.settings.get("read.max_content_chars"),
                        document_workers=st.settings.get("concurrency.read_workers", 1))
                except evidence.BudgetBlocked:
                    # Every literature cell of this candidate is left `not_assessed` rather than scored
                    # on the part of the union that was read before the cap: the cells share one
                    # reading, and a truncated one would make each of them look complete.
                    refused = True
            cut = False
            for item in rules:
                if (item["entry"]["rule_ref"], candidate_id) in st.cells:
                    continue
                cell, reason = self._assess(st, item, candidate_id, pass_budget, step_ids, cache,
                                            candidate_reading=reading, read_refused=refused)
                self._record_cell(st, cell, reason, step_ids, planned_cells)
                cut = cut or (cell["verdict"] == "not_assessed"
                              and cell["not_assessed_reason"] == "budget_exhausted")
            self._emit(run_id, "step.completed", ids=step_ids, state_to="completed",
                       payload={"candidate_ref": candidate_id, "rule_refs": rule_refs,
                                "union_documents": len(reading.documents) if reading else 0,
                                "claims_extracted": len(reading.claims) if reading else 0,
                                "budget_used": dict(pass_budget.used)})
            self._emit(run_id, "checkpoint.written",
                       ids=dict(step_ids, checkpoint_id=f"ckpt_{run_id}_{steps_done + position + 1}"),
                       payload={"sweep_cursor": {"candidate_ref": candidate_id, "seed": st.binding["sweep_seed"],
                                                 "literature_rules": len(rule_refs),
                                                 "completed_cell_refs_hash": self._cell_refs_hash(st)},
                                "next_candidate_index": position + 1})
            return cut

        jobs = list(enumerate(todo))
        if self.workers > 1 and len(jobs) > 1:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                return any(list(pool.map(work, jobs)))
        return any([work(job) for job in jobs])     # every candidate is swept; `any` may not short-circuit

    def _assess(self, st: RunState, item: dict[str, Any], candidate_id: str, pass_budget: _PassBudget,
                ids: dict[str, Any], cache, *, candidate_reading: evidence.LiteratureReading | None = None,
                read_refused: bool = False) -> tuple[dict, dict]:
        record = st.identities[candidate_id]
        attribute, rule = item["attribute"], item["rule"]
        policy = st.binding.get("qualification_policy", "legacy")
        existing = st.binding.get("evidence_mode") == "existing_only"
        candidate = {"candidate_id": candidate_id, "label": record.get("preferred_label")}
        if not identity.is_resolved(record):
            reason = "identity_pending_review" if record["identity_review_state"] == "pending" else "identity_unresolved"
            return assessor.assess_cell(candidate=candidate, attribute=attribute, rule=rule,
                                        rule_set_ref=st.rule_set["rule_set_ref"], claims=[], resolved=False,
                                        not_assessed_reason=reason, qualification_policy=policy)
        needs_llm = _reads_literature(item)
        out_of_budget = assessor.assess_cell(candidate=candidate, attribute=attribute, rule=rule,
                                             rule_set_ref=st.rule_set["rule_set_ref"], claims=[], resolved=True,
                                             not_assessed_reason="budget_exhausted", qualification_policy=policy)
        # `read_refused` is the candidate's shared literature reading having been cut off by the
        # budget: it is not visible in `pass_budget.blocked()`, which answers whether the next call
        # may be made, not whether one was already refused.
        if not existing and (read_refused or pass_budget.blocked() or (needs_llm and st.budget.exhausted("llm_turns"))):
            return out_of_budget
        request = {"run_id": st.run_id, "task_id": st.task_context["task_context_id"], "task_context": st.task_context,
                   "candidate_id": candidate_id, "candidate": candidate, "identity": record, "attribute": attribute,
                   "rule": rule, "rule_entry": item["entry"], "rule_set_ref": st.rule_set["rule_set_ref"],
                   "evidence_cutoff": st.binding["evidence_cutoff"], "deferred_capabilities": item.get("deferred_capabilities", ()),
                   "evidence_mode": st.binding.get("evidence_mode", "retrieve"), "qualification_policy": policy,
                   "ids": ids, "budget": pass_budget, "broker": self._facts_broker(st)}
        offered = self.evidence_hook(request) if self.evidence_hook else None
        if offered is not None or (existing and needs_llm):
            claims, error_ref, searched = offered if offered is not None else ([], None, ["existing_only:no_stored_claims"])
            return assessor.assess_cell(candidate=candidate, attribute=attribute, rule=rule,
                rule_set_ref=st.rule_set["rule_set_ref"], claims=claims, resolved=True,
                tool_error_ref=error_ref, searched=searched, qualification_policy=policy,
                min_source_documents=st.settings.get("evidence.min_source_documents", 1))
        try:
            claims, error_ref, searched = evidence.gather(
                self.core, self._facts_broker(st), self.roster, st.run_id, candidate=candidate, identity=record, attribute=attribute,
                objective_text=st.task_context["objective_text"], cutoff_date=st.binding["evidence_cutoff"],
                budget=pass_budget, ids=ids, cache=cache,
                case_sources=st.task_context.get("case_source_documents", []),
                sources=st.settings.get("search.sources"),
                max_documents=st.settings.get("read.max_papers_per_candidate", 2),
                limit_per_query=st.settings.get("search.results_per_query", 10),
                max_chars=st.settings.get("read.max_content_chars"),
                document_workers=st.settings.get("concurrency.read_workers", 1),
                reading_attributes=[{"name": r["attribute"]["name"], "definition": r["attribute"]["definition"],
                                     "unit": r["attribute"].get("unit"),
                                     "ref": f"{r['attribute']['attribute_id']}@v{r['attribute']['version']}"}
                                    for r in st.rules if _reads_literature(r)],
                candidate_reading=candidate_reading,
                defer_capabilities=item.get("deferred_capabilities", ()),
                verified_supplement_refs=[e["ref"] for e in st.binding.get("verified_supplements", {}).get("entries", [])])
        except evidence.BudgetBlocked:
            return out_of_budget
        return assessor.assess_cell(candidate=candidate, attribute=attribute, rule=rule,
                                    rule_set_ref=st.rule_set["rule_set_ref"], claims=claims, resolved=True,
                                    tool_error_ref=error_ref, searched=searched,
                                    # The only one of the three `assess_cell` calls in this method that
                                    # scores claims; the other two carry none and are refusals already.
                                    min_source_documents=st.settings.get("evidence.min_source_documents", 1),
                                    qualification_policy=policy)

    def _cell_refs_hash(self, st: RunState) -> str:
        """The checkpoint's digest of what is assessed so far, read without a writer mid-insert.

        The literature phase assesses candidates concurrently and writes its checkpoint from inside
        a worker, so this iterates a dict another worker may be inserting into -- which raises
        `RuntimeError: dictionary changed size during iteration` rather than returning a wrong hash.
        """
        with self._cells_lock:
            return sha256_hex(sorted(f"{rule}|{candidate}" for rule, candidate in st.cells))

    def _record_cell(self, st: RunState, cell: dict, reason: dict, ids: dict[str, Any], planned_cells: int,
                     *, reuse: dict[str, Any] | None = None) -> None:
        cell = dict(cell, fingerprint=sha256_hex({
            "candidate": cell["candidate_ref"], "rule": cell["rule_ref"], "attribute": cell["attribute_ref"],
            "strategy": STRATEGY, "assessor": cell["assessed_by"]["model_or_tool_version"], "claims": cell["value_source_claim_refs"],
            "tools": [(t["tool_id"], t["contract_version"]) for t in st.binding["tool_availability_snapshot"]],
            "executed_on": self.host_platform, "recall_set_hash": ""}),
            reuse=reuse or {"decision": "recomputed"})
        reason_artifact = self.core.artifacts.put("reason", reason)
        cell_artifact = self.core.artifacts.put("assessment", dict(cell, reason_artifact_id=reason_artifact))
        with self._cells_lock:
            st.cells[(cell["rule_ref"], cell["candidate_ref"])] = dict(cell, reason_artifact_id=reason_artifact)
            completed = len(st.cells)
        self._emit(st.run_id, "candidate.assessed", ids=ids,
                   payload={"candidate_ref": cell["candidate_ref"], "rule_ref": cell["rule_ref"],
                            "attribute_ref": cell["attribute_ref"], "verdict": cell["verdict"],
                            "artifact_id": cell_artifact, "reason_artifact_id": reason_artifact},
                   artifact_links=[{"kind": "assessment", "id": cell_artifact}, {"kind": "reason", "id": reason_artifact}],
                   summary=f"{cell['candidate_ref']} · {cell['attribute_ref']}: {cell['verdict']}",
                   progress={"scope": "stage:assess", "denominator_kind": "enumerated_fixed",
                             "completed": completed, "planned": planned_cells},
                   budget=st.budget.snapshot())

    def _calibration_guard(self, st: RunState, by_candidate: dict[str, list[dict]],
                           rules_info: dict[str, dict[str, Any]], mandated: list[str],
                           ids: dict[str, Any]) -> tuple[dict[str, list[dict]], dict[str, dict[str, Any]], dict]:
        """Demote every hard exclusion that removes too much of the task's mandated population.

        `assessor.calibration_guard` decides; this applies the decision and records it. Applying it
        means rewriting `rule_kind` on the run's own cell records and on `rules_info`, which is what
        the roll-up, the preference score and the snapshot all read -- a demotion recorded only
        beside them would leave the exclusion excluding while every surface said it had been demoted,
        which is the defect `adjudication`'s module docstring describes.

        WHY it is not a new rule version, where a machine adjudication writes one: the guard's input
        is this run's assessed cells, so it cannot run before the sweep, and by then the rule set is
        confirmed and the cells are written. The rule in the registry is unchanged and still a hard
        exclusion; what this run did with it is recorded on the run and on the board it published.
        A reader who wants the registry's answer gets the hard exclusion; a reader of this board is
        told, with the measured share, that it ranked here instead of excluding.
        """
        new_policy = st.binding.get("qualification_policy") == assessor.QUALIFICATION_POLICY
        diagnostic_cells = {c: [dict(cell, verdict="pass" if cell["verdict"] == "available" and assessor.direct_evidence(cell)
                                     else "unknown_missing" if not assessor.direct_evidence(cell) and cell["verdict"] in ("pass", "fail", "available")
                                     else cell["verdict"]) for cell in cells] for c, cells in by_candidate.items()} if new_policy else by_candidate
        guard = assessor.calibration_guard(
            diagnostic_cells, rules_info, mandated_rule_refs=mandated,
            max_removed_share=st.settings.get("assess.max_reference_exclusion_share",
                                              assessor.DEFAULT_MAX_REFERENCE_EXCLUSION))
        if new_policy:
            return by_candidate, rules_info, dict(guard, policy="diagnostic_only", demoted={},
                flagged=guard.get("demoted") or {}, changes_scientific_rules=False)
        if not guard["demoted"]:
            return by_candidate, rules_info, guard
        demoted = guard["demoted"]
        rules_info = {ref: (dict(info, rule_kind="preference") if ref in demoted else info)
                      for ref, info in rules_info.items()}
        # The loaded rule records too, because the scoring stage reads the kind off them when it
        # decides which quantities it may offer as features (`sr_stage.build_dataset`): left alone,
        # the demoted criterion would rank under the weighted-preference score and be invisible to
        # the expression fitted against that very score. The registry's own record is untouched --
        # `confirm_rule_set` reads the store, not this list -- so a rule set written after this run
        # still carries the hard exclusion.
        for item in st.rules:
            if item["entry"]["rule_ref"] in demoted:
                item["rule"] = dict(item["rule"], rule_kind="preference")
        by_candidate = {candidate: [dict(cell, rule_kind="preference",
                                         demoted_by_calibration_guard=demoted[cell["rule_ref"]])
                                    if cell["rule_ref"] in demoted else cell for cell in cells]
                        for candidate, cells in by_candidate.items()}
        record = {"guard_id": new_id("cal"), "run_id": st.run_id, "task_id": st.task_context["task_context_id"],
                  "rules@v": st.rule_set["rule_set_ref"], **guard,
                  # Never `agent_verdict` and never a person's: no model was called and nobody was
                  # asked. It is a share the software measured over records already in the store, the
                  # same standing `collapse` records for itself.
                  "approval_kind": vocab.require("approval_kind", "software_status"),
                  "confirmed_by_a_person": False, "actor": CONTROLLER, "measured_at": utc_now()}
        artifact_id = self.core.artifacts.put("calibration_guard", record)
        self._emit(st.run_id, "decision.recorded", ids=ids, payload=dict(record, artifact_id=artifact_id),
                   artifact_links=[{"kind": "calibration_guard", "id": artifact_id}],
                   summary=f"{len(demoted)} hard exclusion(s) demoted to preferences on this run: each removes "
                           f"more than {guard['limit']:.2f} of the {guard['reference_set_n']} candidates that "
                           f"clear the task's mandated criteria (no person confirmed it)")
        return by_candidate, rules_info, guard

    def _finish(self, st: RunState, ids: dict[str, Any], budget_cut: bool) -> str:
        run_id, task_id = st.run_id, st.task_context["task_context_id"]
        candidates = sorted(st.identities)
        by_candidate: dict[str, list[dict]] = {c: [] for c in candidates}
        for (rule_ref, candidate_id), cell in st.cells.items():
            by_candidate.setdefault(candidate_id, []).append(cell)
        requires_hd = st.task_context.get("human_review_requirements", {}).get("recommended_requires_hd", True)
        weights = (st.rule_set.get("ordering_method") or {}).get("weight_vector") or {}
        pending_hard = [ref for ref in st.rule_set.get("pending", [])
                        if criteria.load(self.core, ref, task_id)["rule_kind"] == "hard_exclusion"]
        # A hard rule resolved by machine adjudication carries authority the run can act on, labelled
        # as an agent's and never as a person's. Without this the eligible set is empty whenever no
        # `hd_` exists, which is every autonomous run.
        machine_authority = bool(st.rule_set.get("machine_adjudicated"))
        rules_info = {r["entry"]["rule_ref"]: {"rule_kind": r["rule"]["rule_kind"],
                                               "predicate_form": r["rule"].get("predicate_form", "threshold"),
                                               "direction": r["attribute"].get("direction"),
                                               "quantity_key": criteria.quantity_identity(r["attribute"])} for r in st.rules}
        # The criteria the task itself mandates (`criteria.is_task_mandated`): one list, read by the
        # calibration guard for its reference population and by the board for its coverage floor, so
        # the two cannot drift into two definitions of "what the task requires".
        mandated = [r["entry"]["rule_ref"] for r in st.rules if criteria.is_task_mandated(r["attribute"])]
        new_policy = st.binding.get("qualification_policy") == assessor.QUALIFICATION_POLICY
        qualifications = None
        if new_policy:
            profile_proof = (self._measurement_profile(st) or {}).get("policy", {}).get("scoring_policy", {}).get("required_binding_check", {})
            required = [row["rule_ref"] for row in profile_proof.get("scope_bindings", [])]
            if not profile_proof:
                required = criteria.required_scope_rule_refs(st.task_context, st.rules)
            hard = [r["entry"]["rule_ref"] for r in st.rules if r["rule"]["rule_kind"] == "hard_exclusion"]
            verified = [r["entry"]["rule_ref"] for r in st.rules if self._verified_hard(r)]
            qualifications = {c: assessor.qualification(by_candidate[c], hard_rule_refs=hard, required_rule_refs=required,
                verified_hard_rule_refs=verified, pending_hard_rules=pending_hard) for c in candidates}
        by_candidate, rules_info, guard = self._calibration_guard(st, by_candidate, rules_info, mandated, ids)
        roll_ups = {c: assessor.roll_up(c, by_candidate[c], coverage_floor=st.rule_set.get("coverage_floor", 1.0),
                                        recommended_requires_hd=requires_hd, pending_hard_rules=pending_hard,
                                        machine_authority=machine_authority) for c in candidates}
        if new_policy:
            for c, roll in roll_ups.items():
                q = qualifications[c]
                roll.update(qualification=q, state="recommended" if q["qualified"] else "rejected" if q["state"] == "rejected" else "provisional",
                            state_reason=f"qualification: {q['state']}", hard_rule_coverage=q["hard_direct_coverage"],
                            n_preferences_evaluated=sum(c["rule_kind"] == "preference" and c["verdict"] in
                                                       ("pass", "fail", "available") for c in by_candidate[c]))
        scores = assessor.preference_scores(by_candidate, rules_info, weights,
            qualified_candidates={c for c, q in qualifications.items() if q["qualified"]} if new_policy else None,
            qualification_policy=st.binding.get("qualification_policy", "legacy"))
        if not new_policy and sr_stage.enabled(st.settings):
            # Symbolic regression is strictly additive: it fits on cells already assessed, installs an
            # ordering method only if it wins on its holdout, and records the attempt either way.
            sr = sr_stage.fit_and_install(self.core, self.roster, run_id=run_id, task_id=task_id,
                                          task_context=st.task_context, rule_set=st.rule_set, rules=st.rules,
                                          cells_by_candidate=by_candidate, rules_info=rules_info, weights=weights,
                                          baseline_scores=scores, identities=st.identities, settings=st.settings,
                                          by=CONTROLLER, budget=st.budget, ids=ids)
            if sr.get("installed_rule_set_ref"):
                st.rule_set = criteria.rule_set(self.core, task_id, sr["installed_rule_set_ref"])
        ordering_method = st.rule_set.get("ordering_method") or {}
        if not new_policy and ordering_method.get("kind") == "symbolic_expression":
            # The registered ordering method decides the score; a resumed run reads it from the rule set.
            scores = assessor.expression_scores(by_candidate, rules_info, ordering_method)
        claim_ids = sorted({r for cell in st.cells.values() for r in cell["value_source_claim_refs"]})
        snapshot_id = ledger.freeze_snapshot(self.core, run_id, task_id=task_id, claim_ids=claim_ids,
                                             cutoff_at=st.binding["evidence_cutoff"],
                                             tool_manifest=st.binding["tool_availability_snapshot"], by=CONTROLLER)
        lbd = leaderboard.leaderboard_record(self.core, st.task_context, members=candidates)
        all_snapshots = leaderboard.snapshots(self.core, task_id)
        previous = [s for s in all_snapshots if s["leaderboard_id"] == lbd]
        parent = previous[-1] if previous else None
        planned = len(candidates) * len(st.rules)
        attempted = sum(c["verdict"] != "not_assessed" or c.get("not_assessed_reason") in ("identity_unresolved",
                                                                                            "identity_pending_review")
                        for c in st.cells.values())
        if new_policy:
            attempted = sum(c.get("not_assessed_reason") != "budget_exhausted" for c in st.cells.values())
        sweep_completeness = attempted / planned if planned else 1.0
        profile = self._measurement_profile(st)
        snapshot = leaderboard.build_snapshot(
            task_context=st.task_context, leaderboard_id=lbd, run_id=run_id, round_id=st.round_id, rule_set=st.rule_set,
            evidence_snapshot_id=snapshot_id, roll_ups=roll_ups, cells=by_candidate, scores=scores,
            identities=st.identities, parent=parent, sweep_completeness=sweep_completeness, budget=st.budget.snapshot(),
            ranking_coverage_floor=float(constants.value(self.core, "const_ranking_coverage_floor",
                                                         (EVAL_STREAM, st.run_id))),
            mandated_rule_refs=mandated,
            mandated_coverage_floor=float(constants.value(self.core, "const_mandated_coverage_floor",
                                                         (EVAL_STREAM, st.run_id))),
            calibration_guard=guard,
            rank_requires_mandated_coverage=(profile["policy"]["scoring_policy"]["rank_requires_mandated_coverage"]
                                             if profile else True),
            qualification_policy=st.binding.get("qualification_policy", "legacy"), qualifications=qualifications,
            evaluation_mode=st.binding.get("evaluation_mode", "full"))
        if profile:
            snapshot["measurement_profile"] = profile
        snapshot["verified_supplements"] = st.binding.get("verified_supplements") or supplements.binding(self.core, {})
        snapshot["snapshot_id"] = f"lb_{task_id}_{len(all_snapshots) + 1}"
        snapshot_artifact = self.core.artifacts.put("leaderboard_snapshot", snapshot)
        self._emit(run_id, "stage.closed", ids=ids, state_to="completed", payload={"stage": "snapshot"})
        self._emit(run_id, "leaderboard.snapshot_published", ids=ids,
                   payload={"snapshot_id": snapshot["snapshot_id"], "task_id": task_id, "artifact_id": snapshot_artifact,
                            "leaderboard_id": lbd, "result_kind": snapshot["result_kind"]},
                   artifact_links=[{"kind": "leaderboard_snapshot", "id": snapshot_artifact}],
                   summary=f"{snapshot['snapshot_id']}: {snapshot['result_kind']}")
        last = self.core.journal.last_seq(run_id)
        self._emit(run_id, "projection.hash", ids=ids, payload={"to_seq": last, "hash": sha256_hex(
            [e.to_record() for e in self.core.journal.replay(run_id, 1, last)])})
        if budget_cut:
            reason, end_state, end_event = "budget_exhausted", "unresolved", "run.unresolved"
        else:
            reason, end_state, end_event = "round_limit_reached", "completed", "run.completed"
        unswept = [{"rule_ref": c["rule_ref"], "candidate_ref": c["candidate_ref"]} for c in st.cells.values()
                   if c.get("not_assessed_reason") == "budget_exhausted"]
        self._emit(run_id, "round.closed", ids=ids, termination_reason=reason,
                   payload={"round_id": st.round_id, "continuation_decision": {"decision": "stop", "stop_reason": reason},
                            "unswept_cells_manifest": unswept, "open_questions": []})
        self._emit(run_id, "attempt.finalized", ids=ids, payload={"finalized_by": "worker", "attempt_id": st.attempt_id})
        self._emit(run_id, end_event, ids=ids, state_from="running", state_to=end_state, termination_reason=reason,
                   payload={"snapshot_id": snapshot["snapshot_id"], "sweep_completeness": sweep_completeness,
                            "reused_cells": st.reused})
        return end_state

    def resume(self, run_id: str) -> str:
        return self.execute(run_id, resuming=True)
