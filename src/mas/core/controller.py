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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from . import (assessor, constants, criteria, evidence, identity, leaderboard, ledger, sr_stage,
               task as task_mod, vocab)
from .budget import Budget
from .canonical import sha256_hex
from .clock import utc_now
from .ids import new_id
from .journal import EVAL_STREAM, actor as make_actor
from .runtime import Core

CONTROLLER = make_actor("controller", "C15", "run_controller")
STRATEGY = "strat@v1"
RUN_STAGES = ("identity", "assess", "snapshot")
DATABASE_FIRST = 0
LITERATURE_LAST = 1


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
    def __init__(self, core: Core, broker, roster=None, *, adapter: dict[str, Any], host_platform: str = "linux",
                 implementation: dict[str, Any] | None = None, workers: int = 1):
        self.core, self.broker, self.roster = core, broker, roster
        self.implementation = implementation or {}
        self.workers = max(1, workers)  # concurrent cells for literature rules (model calls dominate)
        self.adapter = adapter  # {"adapter_id", "adapter_version", "primary_scheme"}
        self.host_platform = host_platform

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
              screening_rounds: int = 1, budget_envelope: dict[str, Any] | None = None, sweep_seed: int = 0,
              memory_mode: str = "cold", evidence_cutoff: str | None = None, chain_id: str | None = None,
              continues_run_id: str | None = None, continuation_kind: str = "root", candidate_limit: int | None = None,
              execute: bool = True, settings: Any = None) -> str:
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
            "memory_mode": memory_mode, "evidence_cutoff": evidence_cutoff or utc_now()[:10],
            "host": {"platform": self.host_platform, "service_host_version": "mas-0.1.0"},
            "tool_availability_snapshot": self.broker.manifest(),
            "known_reference_outcome_disclosure": [s for s in context.get("seed_candidates", []) if s.get("is_reference_outcome")],
            "derivation_configuration": "reference_disclosed", "budget_envelope": budget_envelope or {},
            "candidate_limit": candidate_limit, "implementation": self.implementation,
            "settings": settings_ref, "budget_policy": budget_policy,
            "bound_at": utc_now(), "bound_by": by,
        }
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
        if binding.get("run_purpose", "sweep") != "sweep":
            raise RunError("rejected_invalid", f"{run_id} is a {binding['run_purpose']} run, not a candidate sweep")
        task_id = events[0].payload["task_id"]
        context = task_mod.get(self.core, task_id, int(binding["task_context_id@v"].rsplit("@v", 1)[1]))
        rule_set = criteria.rule_set(self.core, task_id, binding["rules@v"])
        policy = binding.get("budget_policy") or {}
        budget = Budget(binding["budget_envelope"], soft_kinds=tuple(policy.get("soft_kinds", ())),
                        warn_at=policy.get("warn_at"))
        settings_values = {}
        if (binding.get("settings") or {}).get("layers_artifact_id"):
            layers = self.core.artifacts.payload(binding["settings"]["layers_artifact_id"])
            settings_values = {row["key"]: row["value"] for row in layers["settings"]}
        state = RunState(run_id, binding, context, rule_set, budget,
                         attempt_id=f"att_{run_id}_1", round_id=f"round_{run_id}_1", settings=settings_values)
        for entry in rule_set["entries"]:
            rule = criteria.load(self.core, entry["rule_ref"], task_id)
            attr = criteria.load(self.core, entry["attribute_ref"], task_id)
            state.rules.append({"entry": entry, "rule": rule, "attribute": attr})
        state.rules.sort(key=lambda r: (LITERATURE_LAST if criteria.is_literature_bound(r["attribute"])
                                        else DATABASE_FIRST, r["entry"]["rule_ref"]))
        return state

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
        return self._run(st, ids)

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
        # identity first (design §6.6 step 1)
        if not st.identities:
            self._emit(run_id, "stage.opened", ids=ids, payload={"stage": "identity"},
                       progress={"scope": "stage:identity", "denominator_kind": "enumerated_fixed", "completed": 0,
                                 "planned": len(members)})
            records = identity.resolve_universe(self.core, self.broker, run_id, members,
                                                primary_scheme=self.adapter["primary_scheme"],
                                                capability="identity_resolution", ids=ids, budget=st.budget)
            st.identities = {r["candidate_id"]: r for r in records}
            self._emit(run_id, "stage.closed", ids=ids, payload={"stage": "identity",
                                                                "resolved": sum(identity.is_resolved(r) for r in records)},
                       state_to="completed", progress={"scope": "stage:identity", "denominator_kind": "enumerated_fixed",
                                                       "completed": len(records), "planned": len(members)})
        candidates = sorted(st.identities)
        planned_cells = len(candidates) * len(st.rules)
        self._emit(run_id, "stage.opened", ids=ids, payload={"stage": "assess", "planned_cells": planned_cells},
                   progress={"scope": "stage:assess", "denominator_kind": "enumerated_fixed",
                             "completed": len(st.cells), "planned": planned_cells})
        budget_cut = False
        cache = evidence.LiteratureCache()
        for index, item in enumerate(st.rules):
            rule_ref = item["entry"]["rule_ref"]
            remaining_rules = len(st.rules) - index
            reservation = {k: (st.budget.remaining(k) or 0) / remaining_rules
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
            literature = criteria.is_literature_bound(item["attribute"])

            def work(candidate_id: str) -> bool:
                cell, reason = self._assess(st, item, candidate_id, pass_budget, step_ids, cache)
                self._record_cell(st, cell, reason, step_ids, planned_cells)
                return cell["verdict"] == "not_assessed" and cell["not_assessed_reason"] == "budget_exhausted"

            if literature and self.workers > 1:
                with ThreadPoolExecutor(max_workers=self.workers) as pool:
                    budget_cut = any(list(pool.map(work, todo))) or budget_cut
            else:
                for candidate_id in todo:
                    budget_cut = work(candidate_id) or budget_cut
            self._emit(run_id, "step.completed", ids=step_ids, state_to="completed",
                       payload={"rule_ref": rule_ref, "budget_used": pass_budget.used})
            self._emit(run_id, "checkpoint.written", ids=dict(step_ids, checkpoint_id=f"ckpt_{run_id}_{index + 1}"),
                       payload={"sweep_cursor": {"rule_ref": rule_ref, "seed": st.binding["sweep_seed"],
                                                 "completed_candidate_count": len(order),
                                                 "completed_cell_refs_hash": sha256_hex(sorted(f"{r}|{c}" for r, c in st.cells))},
                                "next_rule_index": index + 1})
        self._emit(run_id, "stage.closed", ids=ids, state_to="completed", payload={"stage": "assess"},
                   progress={"scope": "stage:assess", "denominator_kind": "enumerated_fixed",
                             "completed": len(st.cells), "planned": planned_cells})
        return self._finish(st, ids, budget_cut)

    def _assess(self, st: RunState, item: dict[str, Any], candidate_id: str, pass_budget: _PassBudget,
                ids: dict[str, Any], cache) -> tuple[dict, dict]:
        record = st.identities[candidate_id]
        attribute, rule = item["attribute"], item["rule"]
        candidate = {"candidate_id": candidate_id, "label": record.get("preferred_label")}
        if not identity.is_resolved(record):
            reason = "identity_pending_review" if record["identity_review_state"] == "pending" else "identity_unresolved"
            return assessor.assess_cell(candidate=candidate, attribute=attribute, rule=rule,
                                        rule_set_ref=st.rule_set["rule_set_ref"], claims=[], resolved=False,
                                        not_assessed_reason=reason)
        needs_llm = criteria.is_literature_bound(attribute)
        out_of_budget = assessor.assess_cell(candidate=candidate, attribute=attribute, rule=rule,
                                             rule_set_ref=st.rule_set["rule_set_ref"], claims=[], resolved=True,
                                             not_assessed_reason="budget_exhausted")
        if pass_budget.blocked() or (needs_llm and st.budget.exhausted("llm_turns")):
            return out_of_budget
        try:
            claims, error_ref, searched = evidence.gather(
                self.core, self.broker, self.roster, st.run_id, candidate=candidate, identity=record, attribute=attribute,
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
                                    for r in st.rules if criteria.is_literature_bound(r["attribute"])])
        except evidence.BudgetBlocked:
            return out_of_budget
        return assessor.assess_cell(candidate=candidate, attribute=attribute, rule=rule,
                                    rule_set_ref=st.rule_set["rule_set_ref"], claims=claims, resolved=True,
                                    tool_error_ref=error_ref, searched=searched)

    def _record_cell(self, st: RunState, cell: dict, reason: dict, ids: dict[str, Any], planned_cells: int) -> None:
        cell = dict(cell, fingerprint=sha256_hex({
            "candidate": cell["candidate_ref"], "rule": cell["rule_ref"], "attribute": cell["attribute_ref"],
            "strategy": STRATEGY, "assessor": assessor.ASSESSOR_VERSION, "claims": cell["value_source_claim_refs"],
            "tools": [(t["tool_id"], t["contract_version"]) for t in st.binding["tool_availability_snapshot"]],
            "executed_on": self.host_platform, "recall_set_hash": ""}),
            reuse={"decision": "recomputed"})
        reason_artifact = self.core.artifacts.put("reason", reason)
        cell_artifact = self.core.artifacts.put("assessment", dict(cell, reason_artifact_id=reason_artifact))
        st.cells[(cell["rule_ref"], cell["candidate_ref"])] = dict(cell, reason_artifact_id=reason_artifact)
        self._emit(st.run_id, "candidate.assessed", ids=ids,
                   payload={"candidate_ref": cell["candidate_ref"], "rule_ref": cell["rule_ref"],
                            "attribute_ref": cell["attribute_ref"], "verdict": cell["verdict"],
                            "artifact_id": cell_artifact, "reason_artifact_id": reason_artifact},
                   artifact_links=[{"kind": "assessment", "id": cell_artifact}, {"kind": "reason", "id": reason_artifact}],
                   summary=f"{cell['candidate_ref']} · {cell['attribute_ref']}: {cell['verdict']}",
                   progress={"scope": "stage:assess", "denominator_kind": "enumerated_fixed",
                             "completed": len(st.cells), "planned": planned_cells},
                   budget=st.budget.snapshot())

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
        roll_ups = {c: assessor.roll_up(c, by_candidate[c], coverage_floor=st.rule_set.get("coverage_floor", 1.0),
                                        recommended_requires_hd=requires_hd, pending_hard_rules=pending_hard,
                                        machine_authority=machine_authority) for c in candidates}
        rules_info = {r["entry"]["rule_ref"]: {"rule_kind": r["rule"]["rule_kind"],
                                               "predicate_form": r["rule"].get("predicate_form", "threshold"),
                                               "direction": r["attribute"].get("direction")} for r in st.rules}
        scores = assessor.preference_scores(by_candidate, rules_info, weights)
        if sr_stage.enabled(st.settings):
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
        if ordering_method.get("kind") == "symbolic_expression":
            # The registered ordering method decides the score; a resumed run reads it from the rule set.
            scores = assessor.expression_scores(by_candidate, rules_info, ordering_method)
        claim_ids = sorted({r for cell in st.cells.values() for r in cell["value_source_claim_refs"]})
        snapshot_id = ledger.freeze_snapshot(self.core, run_id, task_id=task_id, claim_ids=claim_ids,
                                             cutoff_at=st.binding["evidence_cutoff"],
                                             tool_manifest=st.binding["tool_availability_snapshot"], by=CONTROLLER)
        lbd = leaderboard.leaderboard_record(self.core, st.task_context, members=candidates)
        previous = [s for s in leaderboard.snapshots(self.core, task_id) if s["leaderboard_id"] == lbd]
        parent = previous[-1] if previous else None
        planned = len(candidates) * len(st.rules)
        attempted = sum(c["verdict"] != "not_assessed" or c.get("not_assessed_reason") in ("identity_unresolved",
                                                                                            "identity_pending_review")
                        for c in st.cells.values())
        sweep_completeness = attempted / planned if planned else 1.0
        snapshot = leaderboard.build_snapshot(
            task_context=st.task_context, leaderboard_id=lbd, run_id=run_id, round_id=st.round_id, rule_set=st.rule_set,
            evidence_snapshot_id=snapshot_id, roll_ups=roll_ups, cells=by_candidate, scores=scores,
            identities=st.identities, parent=parent, sweep_completeness=sweep_completeness, budget=st.budget.snapshot(),
            ranking_coverage_floor=float(constants.value(self.core, "const_ranking_coverage_floor",
                                                         (EVAL_STREAM, st.run_id))))
        all_snapshots = leaderboard.snapshots(self.core, task_id)
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
