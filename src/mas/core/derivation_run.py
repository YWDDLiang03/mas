"""Criteria derivation as a run (design §5.6, §6.8): rounds of the pool workflow, continuable.

A derivation run is a `run_` stream with `run_purpose: criteria_derivation` and no rule set.
It enumerates evidence (breadth x depth), proposes broadly into the pool, then iterates
filter -> distill -> merge -> refine up to `inner_iterations` times, stopping early when
the pool stops changing for `stall_rounds` iterations or the budget refuses a call, and
finally promotes the survivors into the registry.

A later round is a new run in the same chain (`continues_run_id`): runs are never
re-entered. Because pool transitions live in the task stream, the new round folds the
pool its predecessor left (survivors, deferred items, items needing refinement), reads
new evidence, adds to the pool, and continues; its change records point at the earlier
versions they consumed. Criteria already promoted stay as they are: changing a registered
criterion is an expert decision through the review queue, not a pool operation.

`reduce_pool` is the same round with the growth half removed: it prunes and promotes the
pool a previous round left and reads nothing new. Both entry points open a run, record a
stage, prune and close through the same four helpers, so a reader comparing two rounds of
one chain is reading one shape of record whichever grew the pool.
"""

from __future__ import annotations

import re
from typing import Any

from . import criteria, criteria_export, derivation, derivation_stages as stages, ledger, pool as pool_mod, review, task as task_mod
from .canonical import sha256_hex
from .budget import Budget
from .clock import utc_now
from .ids import new_id
from .journal import actor as make_actor
from .models import ModelError, ModelRoster
from .runtime import Core

CONTROLLER = make_actor("controller", "derivation-controller", "controller")
# WHY merge runs last: `filter` moves every item with a validator or critic finding to `needs_refine`, and
# `distill` and `merge` read only `candidate`, while `refine` is what returns a repaired item to `candidate`.
# With merge before refine the pool it reads is whatever filter happened not to flag -- on the manuscript case
# that was nothing, so across two iterations the merge stage grouped 0 items and the adjudicator role was never
# called once. Merging after refine lets the stage see the repaired pool, which is the pool promotion will use.
DEFAULT_STAGES = ("filter", "distill", "refine", "merge")


class DerivationError(RuntimeError):
    pass


def _notify_usage(observer, run_id, budget):
    if observer:
        observer("usage", {"run_id": run_id, "budget": budget.snapshot() if hasattr(budget, "snapshot") else None})


class _ActivityBudget:
    """Check before reserving a model turn, so a stop does not charge an unstarted call."""
    def __init__(self, budget, run_id, checkpoint):
        self.budget, self.run_id, self.checkpoint = budget, run_id, checkpoint

    def __getattr__(self, key):
        return getattr(self.budget, key)

    def try_charge(self, kind, amount=1):
        if kind == "llm_turns":
            self.checkpoint(self.run_id, stage_boundary=False)
        return self.budget.try_charge(kind, amount)


class _ActivityJournal:
    def __init__(self, journal, run_id, budget, observer, checkpoint):
        self.journal, self.run_id, self.budget = journal, run_id, budget
        self.observer, self.checkpoint = observer, checkpoint

    def __getattr__(self, key):
        return getattr(self.journal, key)

    def append(self, stream_id, event_type, **kwargs):
        if stream_id == self.run_id and event_type == "agent.started":
            if self.checkpoint and self.budget is None:
                self.checkpoint(self.run_id, stage_boundary=False)
            if self.observer:
                self.observer("activity", {"run_id": self.run_id, "role": kwargs.get("payload", {}).get("role", "model"),
                    "message": kwargs.get("question") or "model activity"})
        event = self.journal.append(stream_id, event_type, **kwargs)
        if stream_id == self.run_id and event_type == "agent.finished":
            _notify_usage(self.observer, self.run_id, self.budget)
        return event


class _ActivityCore:
    def __init__(self, core, run_id, budget, observer, checkpoint):
        self.core = core
        self.journal = _ActivityJournal(core.journal, run_id, budget, observer, checkpoint)

    def __getattr__(self, key):
        return getattr(self.core, key)


class _ActivityBroker:
    def __init__(self, broker, run_id, budget, observer, checkpoint):
        self.broker, self.run_id, self.budget = broker, run_id, budget
        self.observer, self.checkpoint = observer, checkpoint

    def __getattr__(self, key):
        return getattr(self.broker, key)

    def call(self, stream_id, capability, question_kind, inputs, **kwargs):
        if self.checkpoint:
            self.checkpoint(self.run_id, stage_boundary=False)
        if self.observer:
            self.observer("activity", {"run_id": self.run_id, "role": "tool",
                "message": f"{question_kind} via {capability}"})
        try:
            return self.broker.call(stream_id, capability, question_kind, inputs, **kwargs)
        finally:
            _notify_usage(self.observer, self.run_id, self.budget)


def _activity_context(core, run_id, budget, observer, checkpoint, broker=None):
    if observer is None and checkpoint is None:
        return core, budget, broker
    if checkpoint and budget is None:
        budget = Budget({})  # No caps; still check before each request, including schema repairs.
    controlled_budget = _ActivityBudget(budget, run_id, checkpoint) if budget is not None and checkpoint else budget
    wrapped = _ActivityCore(core, run_id, controlled_budget, observer, checkpoint)
    controlled_broker = _ActivityBroker(broker, run_id, budget, observer, checkpoint) if broker is not None else None
    return wrapped, controlled_budget, controlled_broker


def _interrupted(core, run_id, ids, error):
    paused = bool(getattr(error, "paused", False))
    _emit(core, run_id, "run.paused" if paused else "run.cancelled", ids=ids, state_to="paused" if paused else "cancelled",
          termination_reason=None if paused else "cancelled", payload={"cooperative": True},
          summary="Paused at an investigation checkpoint" if paused else "Stopped at an investigation checkpoint")


def _emit(core: Core, run_id: str, kind: str, **kwargs):
    return core.journal.append(run_id, kind, actor=kwargs.pop("actor", CONTROLLER), **kwargs)


def _chain_runs(core: Core, run_id: str | None) -> list[str]:
    """The derivation runs this one continues, oldest first."""
    chain = []
    while run_id:
        created = core.journal.replay(run_id, 1, 1)
        if not created or created[0].event_type != "run.created":
            raise DerivationError(f"{run_id} is not a run")
        binding = core.artifacts.payload(created[0].payload["binding_artifact_id"])
        if binding.get("run_purpose") != "criteria_derivation":
            raise DerivationError(f"{run_id} is not a criteria derivation run")
        chain.insert(0, run_id)
        run_id = binding.get("continues_run_id")
    return chain


def _binding_of(core: Core, run_id: str) -> dict[str, Any]:
    return core.artifacts.payload(core.journal.replay(run_id, 1, 1)[0].payload["binding_artifact_id"])


def _route_claims(claims: list[dict[str, Any]], dimensions: list[dict[str, str]], *,
                  routing_log: list[dict[str, Any]] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Route semantic labels to every matching dimension; unclassified evidence stays shared.

    Readers extract every dimension from a document. Its retrieval time cannot identify a claim's
    dimension. Free-text hints match declared dimension names/aliases; no model guesses a label.
    """
    def normalize(value):
        return " ".join(str(value).lower().replace("_", " ").replace("-", " ").split())

    aliases = {d["dimension"]: [normalize(d["dimension"])] +
               [normalize(alias) for alias in d.get("hint_aliases", [])] for d in dimensions}
    grouped = {name: [] for name in aliases}
    seen = set()
    for claim in claims:
        if claim["claim_id"] in seen:
            continue
        seen.add(claim["claim_id"])
        structured = []
        for key in ("dimension", "assessment_dimensions", "dimensions"):
            value = claim.get(key)
            structured.extend(value if isinstance(value, list) else [value] if value else [])
        explicit = {name for name, terms in aliases.items()
                    if any(normalize(value) in terms for value in structured)}
        hint = " " + normalize(claim.get("attribute_hint") or "") + " "
        hinted = {name for name, terms in aliases.items() if any(" " + term + " " in hint for term in terms)}
        selected = explicit | hinted
        reason = "structured_dimensions_and_hint" if explicit and hinted else (
            "structured_dimensions" if explicit else "attribute_hint" if hinted else "shared_unclassified")
        selected = selected or set(grouped)
        for name in selected:
            grouped[name].append(claim)
        if routing_log is not None:
            routing_log.append({"claim_id": claim["claim_id"], "dimensions": sorted(selected), "reason": reason})
    return grouped


def _inherited_claims_by_dimension(core: Core, parent_runs: list[str], dimensions: list[dict[str, str]], *,
                                   routing_log: list[dict[str, Any]] | None = None) -> dict[str, list[dict[str, Any]]]:
    return _route_claims(ledger.claims(core, parent_runs), dimensions, routing_log=routing_log)


def _stage_recorder(core: Core, task_id: str, run_id: str, ids: dict[str, Any], *, observer=None, checkpoint=None):
    """A `stage(name, iteration, fn)` that records the pool hash either side of a stage.

    Shared by `derive_iterative` and `reduce_pool` so a stage looks the same in the journal whichever
    entered it -- a reader comparing two rounds should not have to know which function ran them.
    """
    def stage(name: str, iteration: int, fn):
        if checkpoint:
            checkpoint(run_id, stage_boundary=True)
        phase = "evidence" if name == "enumerate" else "propose" if name.startswith(("propose", "mandated")) else "refine"
        before_count = (len(criteria.registered_rule_records(core, task_id)) + len(pool_mod.active(pool_mod.fold(core, task_id)))) if observer else None
        if observer:
            observer("stage", {"phase": phase, "stage": name, "iteration": iteration, "run_id": run_id,
                                "before_count": before_count, "message": f"{name} · iteration {iteration}"})
        before = pool_mod.pool_hash(pool_mod.fold(core, task_id))
        key = sha256_hex({"stage": name, "iteration": iteration, "run_id": run_id, "input_pool_hash": before})
        count_fields = {"before_count": before_count, "count_basis": "active_registered_plus_unregistered_proposals"} if observer else {}
        _emit(core, run_id, "stage.opened", ids=ids, payload={"stage": name, "iteration": iteration, "stage_key": key, **count_fields})
        result = fn()
        after = pool_mod.pool_hash(pool_mod.fold(core, task_id))
        if observer:
            count_fields["after_count"] = len(criteria.registered_rule_records(core, task_id)) + len(pool_mod.active(pool_mod.fold(core, task_id)))
        result_id = core.artifacts.put("derivation_stage", {"stage": name, "iteration": iteration, "result": result,
                                                            "input_pool_hash": before, "output_pool_hash": after, **count_fields})
        _emit(core, run_id, "stage.closed", ids=ids, state_to="completed",
              payload={"stage": name, "iteration": iteration, "stage_key": key, "result_artifact_id": result_id,
                       "pool_changed": before != after, "result": result, **count_fields}, summary=f"{name} {iteration}: {result}")
        if observer:
            observer("stage_finished", {"phase": phase, "stage": name, "iteration": iteration, "run_id": run_id,
                "before_count": before_count, "after_count": count_fields["after_count"],
                "result": result})
        return result
    return stage


def _open_run(core: Core, task_id: str, *, by: dict[str, Any], roster: ModelRoster, parents: list[str],
              continues_run_id: str | None, implementation: dict[str, Any] | None,
              purpose_note: str, settings: Any = None, binding_extra: dict[str, Any] | None = None):
    """Bind the run, register its constants and open its first round; returns (run_id, ids, binding).

    Every event a reader uses to place a run in its chain is written here -- `run.created` carries the
    task and chain ids that `ui/views._binding` indexes a run row by, and the task stream's
    `run.continued` is what makes the chain readable from the task rather than only backwards from the
    run. A second entry point that wrote its own copy of this would be one field away from a run the
    workbench cannot list, so there is one copy and the differences arrive as `binding_extra`.
    """
    context = task_mod.get(core, task_id)
    parent_binding = _binding_of(core, parents[-1]) if parents else None
    run_id = new_id("run")
    ids = {"task_id": task_id, "run_id": run_id}
    binding = {
        "bind_id": f"bind_{run_id}", "run_id": run_id, "run_purpose": "criteria_derivation",
        "task_context_id@v": f"{task_id}@v{context['version']}", "rules@v": None,
        "chain_id": parent_binding["chain_id"] if parent_binding else new_id("chain"),
        "continues_run_id": continues_run_id, "continuation_kind": "continue" if continues_run_id else "root",
        "round_index": len(parents) + 1, "role_bindings": roster.role_bindings(),
        "purpose_note": purpose_note,
        "settings": ({"config_hash": settings.hash(), "preset": settings.preset, "profile": settings.profile,
                      "layers_artifact_id": core.artifacts.put("config_layers", settings.layer_record())}
                     if settings is not None else None),
        "derivation_configuration": "reference_disclosed",
        "known_reference_outcome_disclosure": [sd for sd in context.get("seed_candidates", [])
                                               if sd.get("is_reference_outcome")],
        "implementation": implementation, "bound_at": utc_now(), "bound_by": by,
        **(binding_extra or {}),
    }
    binding_id = core.artifacts.put("run_binding", binding)
    _emit(core, run_id, "run.created", actor=by, ids=ids, state_to="queued",
          payload={"binding_artifact_id": binding_id, "task_id": task_id, "chain_id": binding["chain_id"],
                   "run_purpose": "criteria_derivation"},
          artifact_links=[{"kind": "run_binding", "id": binding_id}],
          summary=f"criteria derivation round {binding['round_index']}: {purpose_note}")
    if settings is not None:
        from .config import register_constants
        register_constants(core, settings, by=by, stream_id=run_id)
    if continues_run_id:
        core.journal.append(task_id, "run.continued", actor=by, payload={
            "parent_run_id": continues_run_id, "run_id": run_id, "continuation_kind": "continue"})
    _emit(core, run_id, "run.started", ids=ids, state_from="queued", state_to="running")
    _emit(core, run_id, "round.opened", ids=ids, payload={"round_id": f"round_{run_id}_1",
                                                          "trigger": "continuation" if parents else "first_round"})
    return run_id, ids, binding


def _stage_context(core: Core, roster: ModelRoster, task_id: str, run_id: str, *, context: dict[str, Any],
                   catalog: list[dict[str, Any]], claims: dict[str, dict[str, Any]], budget: Any,
                   max_refines: int) -> stages.StageContext:
    return stages.StageContext(
        core=core, roster=roster, task_id=task_id, run_id=run_id, task_context=context, catalog=catalog,
        claims_by_id=claims, budget=budget, max_refines=max_refines,
        reference_labels=[label for sd in context.get("seed_candidates", []) if sd.get("is_reference_outcome")
                          for label in [sd["candidate_ref"], *sd.get("aliases", [])]],
        pool=pool_mod.Pool(core, task_id, by=stages.proposer_actor_for(roster), run_id=run_id))


def _prune(ctx: stages.StageContext, stage, iterations: list[dict[str, Any]], *, stage_names: tuple[str, ...],
           inner_iterations: int, stall_rounds: int, merge_overlap: float) -> str:
    """Iterate the pruning stages until the pool stops changing; returns the termination reason.

    Each finished iteration is appended to `iterations` as it finishes rather than returned at the end,
    so a budget refusal or a crash mid-iteration still leaves the ones that did run on the record.
    """
    stalled = 0
    deferred = ctx.active(("deferred_next_round",))
    if deferred:
        def reenter():
            for entry in deferred:
                ctx.pool.at("reenter", 0).set_state(
                    entry, "needs_refine", operation="reinstate", reason_kind="deferred_reentered",
                    reason_text="rechecked on the next run; cumulative refinement count is preserved")
            return {"reentered": len(deferred)}
        stage("reenter", 0, reenter)
    for iteration in range(1, inner_iterations + 1):
        before = pool_mod.pool_hash(pool_mod.fold(ctx.core, ctx.task_id))
        results = {}
        for name in stage_names:
            fn = stages.STAGES[name]
            if name == "merge":
                results[name] = stage(name, iteration,
                                      lambda: stages.merge_stage(ctx, iteration, overlap=merge_overlap))
            else:
                results[name] = stage(name, iteration, lambda fn=fn: fn(ctx, iteration))
        changed = pool_mod.pool_hash(pool_mod.fold(ctx.core, ctx.task_id)) != before
        iterations.append({"iteration": iteration, "pool_changed": changed, **results})
        stalled = 0 if changed else stalled + 1
        if stalled >= stall_rounds:
            return "diminishing_information_gain"
    return "round_limit_reached"


def _close_run(core: Core, task_id: str, run_id: str, ids: dict[str, Any], record: dict[str, Any], *,
               roster: ModelRoster, budget: Any, termination: str) -> dict[str, Any]:
    """The end of a round: what the pool now holds, whether another round has work, and the last events.

    The record artifact id is named `derivation_record_artifact_id` on both closing events because that
    is the key `record_of` reads a round's record back by; a round that spelled it differently was a
    round whose own result could not be found again.
    """
    final = pool_mod.fold(core, task_id)
    counts: dict[str, int] = {}
    for entry in final.values():
        counts[entry["state"]] = counts.get(entry["state"], 0) + 1
    record["pool_states"] = counts
    record["pool_hash"] = pool_mod.pool_hash(final)
    record["termination_reason"] = termination
    record["independence"] = {"proposer_family": roster.adapter("proposer").record.provider_family,
                              "critic_family": roster.adapter("critic").record.provider_family,
                              "same_adapter": roster.roles.get("proposer") == roster.roles.get("critic"),
                              "critic_saw_proposer_rationale": False}
    record["budget"] = budget.snapshot() if hasattr(budget, "snapshot") else None
    waiting = counts.get("deferred_next_round", 0) + counts.get("needs_refine", 0) + counts.get("candidate", 0)
    decision = {"decision": "continue_next_round" if waiting else "stop", "stop_reason": termination,
                "items_waiting": waiting}
    record["continuation_decision"] = decision
    record["artifact_id"] = core.artifacts.put("derivation_record", record)
    end_state, end_event = (("unresolved", "run.unresolved") if termination == "budget_exhausted"
                            else ("completed", "run.completed"))
    _emit(core, run_id, "round.closed", ids=ids, termination_reason=termination,
          payload={"round_id": f"round_{run_id}_1", "continuation_decision": decision,
                   "derivation_record_artifact_id": record["artifact_id"]})
    _emit(core, run_id, end_event, ids=ids, state_from="running", state_to=end_state, termination_reason=termination,
          payload={"derivation_record_artifact_id": record["artifact_id"]})
    return record


def reduce_pool(core: Core, roster: ModelRoster, task_id: str, *, catalog: list[dict[str, Any]],
                by: dict[str, Any], continues_run_id: str, inner_iterations: int = 2, stall_rounds: int = 2,
                stage_names: tuple[str, ...] = DEFAULT_STAGES, max_refines: int = 2,
                merge_overlap: float = 0.35, budget: Any = None, settings: Any = None,
                implementation: dict[str, Any] | None = None, observer=None, checkpoint=None) -> dict[str, Any]:
    """Run the pruning stages and promotion over the pool a previous round already built.

    WHY this exists separately from `derive_iterative`: the reduction from many proposals to few
    quantities is the part of the design that had never run, and re-reaching it meant re-running
    enumerate -- an hour of literature the store already holds, with a different set of documents
    each time because saturation depends on what the searches happen to return. Growing the pool and
    pruning it are different operations on it, and only the second one needed repeating. This reads
    no new literature, proposes nothing, and touches only the stages that consolidate: so a merge
    strategy can be changed and tried against the pool it failed on, rather than against whatever a
    fresh enumerate produces.

    The claims the pool cites stay resolvable because `ledger.claims` folds them from the chain's own
    run streams, which is where the round that read the literature recorded them; a refine or a merge
    that must quote the evidence behind an item therefore has it, without a document being fetched.
    """
    unknown = [s for s in stage_names if s not in stages.STAGES]
    if unknown:
        raise DerivationError(f"unknown stages {unknown}; known stages are {sorted(stages.STAGES)}")
    parents = _chain_runs(core, continues_run_id) if continues_run_id else []
    if not parents:
        raise DerivationError(f"{continues_run_id} is not a criteria derivation run to reduce")
    # WHY the task is checked against the chain and not assumed: the pool is folded from the task
    # stream while the claims come from the run streams, so a run id belonging to another task would
    # prune one task's pool against another task's evidence and promote the result into this registry.
    reduced = _binding_of(core, parents[-1])["task_context_id@v"].split("@v")[0]
    if reduced != task_id:
        raise DerivationError(f"{continues_run_id} derives criteria for {reduced}, not {task_id}")
    context = task_mod.get(core, task_id)
    run_id, ids, binding = _open_run(
        core, task_id, by=by, roster=roster, parents=parents, continues_run_id=continues_run_id,
        implementation=implementation, purpose_note="reduce the pool an earlier round built", settings=settings,
        binding_extra={"inner_iterations": inner_iterations, "stall_rounds": stall_rounds,
                       "stages": list(stage_names), "max_refines": max_refines, "merge_overlap": merge_overlap,
                       # WHY stated rather than left to be inferred from the absent `research` block: this is
                       # the one claim a reader of the chain cannot check from the pool, and it is the whole
                       # difference between the two entry points. Both bindings carry it, so the question is
                       # answered by reading one field instead of by noticing which fields are missing.
                       "reads_new_evidence": False})
    if observer:
        observer("created", {"run_id": run_id})
    core, budget, _ = _activity_context(core, run_id, budget, observer, checkpoint)
    claims = {c["claim_id"]: c for c in ledger.claims(core, parents + [task_id])}
    ctx = _stage_context(core, roster, task_id, run_id, context=context, catalog=catalog, claims=claims,
                         budget=budget, max_refines=max_refines)
    record: dict[str, Any] = {"task_id": task_id, "run_id": run_id, "chain_id": binding["chain_id"],
                              "round_index": binding["round_index"], "continues_run_id": continues_run_id,
                              "reduce_only": True, "claims_resolvable": len(claims),
                              "inherited_claim_routing_artifact_id": None}
    termination = "round_limit_reached"
    stage = _stage_recorder(core, task_id, run_id, ids, observer=observer, checkpoint=checkpoint)
    try:
        record["iterations"] = []
        termination = _prune(ctx, stage, record["iterations"], stage_names=stage_names,
                             inner_iterations=inner_iterations, stall_rounds=stall_rounds,
                             merge_overlap=merge_overlap)
        record["promotion"] = stage("promote", 0, lambda: stages.promote(ctx, by_proposer=stages.proposer_actor(ctx)))
    except ModelError as error:
        if error.error_class != "quota_exhausted":
            _fail(core, run_id, ids, error)
            raise
        termination = "budget_exhausted"
    except InterruptedError as error:
        _interrupted(core, run_id, ids, error)
        raise
    except Exception as error:
        _fail(core, run_id, ids, error)
        raise
    return _close_run(core, task_id, run_id, ids, record, roster=roster, budget=budget, termination=termination)


def registered_reduction_sources(core: Core, task_id: str) -> list[str]:
    """Resolve the original chain from pinned inherited task events, never later/new runs."""
    cursor = task_mod.get(core, task_id)
    seen = {task_id}
    while cursor.get("derived_from_task_id"):
        source_task = cursor["derived_from_task_id"]
        if source_task in seen:
            raise DerivationError("cyclic task inheritance")
        seen.add(source_task)
        pin = (cursor.get("inheritance") or {}).get("source_at_seq")
        if pin is None:
            raise DerivationError("automatic evidence sources need a pinned inheritance snapshot")
        source_core, _ = criteria_export.pinned(core, source_task, pin)
        events = list(source_core.journal.replay(source_task))
        candidates = [e.payload["run_id"] for e in reversed(events) if e.event_type == "run.continued"]
        for event in reversed(events):
            if event.event_type == "criterion.change_recorded" and event.payload.get("pool"):
                if event.payload.get("round_run_id"):
                    candidates.append(event.payload["round_run_id"])
            elif event.event_type == "criterion.version_proposed" and event.payload["kind"] == "attribute":
                attribute = core.artifacts.payload(event.payload["artifact_id"])
                derived_run = (attribute.get("derived_from") or {}).get("derivation_run")
                if derived_run:
                    candidates.append(derived_run)
        for run_id in dict.fromkeys(candidates):
            binding = _binding_of(core, run_id)
            if binding.get("run_purpose") != "criteria_derivation" or \
                    binding["task_context_id@v"].split("@v")[0] != source_task:
                continue
            if binding.get("operation") == "registered_reduction":
                manifest = core.artifacts.payload(binding["source_inputs_artifact_id"])
                return [source["run_id"] for source in manifest["source_runs"]]
            return _chain_runs(core, run_id)
        cursor = task_mod.get(source_core, source_task)
    raise DerivationError("no original derivation chain is referenced by the pinned inherited tasks")


def _task_field(context: dict[str, Any], path: str) -> Any:
    value: Any = context
    for part in path.split("."):
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?", part)
        if not match or not isinstance(value, dict) or match[1] not in value:
            raise KeyError(path)
        value = value[match[1]]
        if match[2] is not None:
            value = value[int(match[2])]
    return value


def _same_required_content(attribute: dict[str, Any], rule: dict[str, Any],
                           original_attribute: dict[str, Any], original_rule: dict[str, Any]) -> bool:
    return (all(attribute.get(key) == original_attribute.get(key) for key in stages.ATTRIBUTE_FIELDS)
            and stages.decision_key(rule) == stages.decision_key(original_rule)
            and criteria.is_task_mandated(attribute) == criteria.is_task_mandated(original_attribute)
            and (attribute.get("derived_from") or {}).get("field") ==
            (original_attribute.get("derived_from") or {}).get("field"))


def required_binding_audit(core: Core, task_id: str, run_id: str | None = None) -> dict[str, Any]:
    """Read original task anchors and their current/frozen bindings without changing any result."""
    context = task_mod.get(core, task_id)
    registry = criteria_export._registry(core, task_id)
    expected = {}
    input_sources = None
    run_state = None
    if run_id:
        binding = _binding_of(core, run_id)
        if binding.get("operation") != "registered_reduction" or binding["task_context_id@v"].split("@v")[0] != task_id:
            raise DerivationError(f"{run_id} is not a registered reduction of {task_id}")
        manifest = core.artifacts.payload(binding["source_inputs_artifact_id"])
        input_sources = [source for source in manifest["registered_inputs"] if source.get("task_mandated")]
        lifecycle = [e for e in core.journal.replay(run_id) if e.event_type.startswith("run.") and e.state_to]
        run_state = lifecycle[-1].state_to if lifecycle else "unknown"
    if input_sources is None:
        for entry in registry.values():
            if entry["kind"] == "attribute" and criteria.is_task_mandated(entry["record"]):
                expected[entry["base_id"]] = entry
        input_sources = []
        for entry in expected.values():
            linked = [record for record in registry.values() if record["kind"] == "rule"
                      and record["record"].get("attribute_ref") == entry["ref"]]
            if linked:
                input_sources.append({"attribute_ref": entry["ref"], "rule_ref": linked[-1]["ref"],
                                      "attribute_sha256": criteria_export._artifact_hash(core, entry["artifact_id"]),
                                      "rule_sha256": criteria_export._artifact_hash(core, linked[-1]["artifact_id"])})
    active_rules = criteria.registered_rule_records(core, task_id)
    try:
        frozen = criteria.rule_set(core, task_id)
        frozen_refs = {entry["rule_ref"] for entry in frozen["entries"]}
        frozen_ref = frozen["rule_set_ref"]
    except KeyError:
        frozen_refs, frozen_ref = set(), None
    bindings, invalid, missing = [], [], []
    bound_scope = set()
    for source in input_sources:
        original_attribute = registry[source["attribute_ref"]]["record"]
        original_rule = registry[source["rule_ref"]]["record"]
        field = (original_attribute.get("derived_from") or {}).get("field")
        valid = criteria.is_task_mandated(original_attribute)
        for kind in ("attribute", "rule"):
            ref = source[f"{kind}_ref"]
            valid = valid and source.get(f"{kind}_sha256") == criteria_export._artifact_hash(core, registry[ref]["artifact_id"])
        try:
            task_value = _task_field(context, field or "")
            source_context_ref = (original_attribute.get("derived_from") or {}).get("task_context")
            if source_context_ref:
                source_task, version = source_context_ref.rsplit("@v", 1)
                source_value = _task_field(task_mod.get(core, source_task, int(version)), field or "")
                valid = valid and sha256_hex(task_value) == sha256_hex(source_value)
        except (KeyError, IndexError, TypeError, ValueError):
            task_value, valid = None, False
        if not valid:
            invalid.append(source["attribute_ref"])
        matches = [record for record in active_rules
                   if record["attribute_ref"].split("@v")[0] == original_attribute["attribute_id"]
                   and _same_required_content(criteria.load(core, record["attribute_ref"], task_id), record,
                                              original_attribute, original_rule)]
        match = matches[-1] if matches else None
        active_ref = f"{match['rule_id']}@v{match['version']}" if match else None
        scope_id = task_value.get("identifier") if isinstance(task_value, dict) and task_value.get("role") == "required" else None
        if scope_id:
            subjects = {str(value) for route in criteria.evidence_routes(original_attribute)
                        for value in criteria.subject_parameters(route).values()}
            valid = valid and scope_id in subjects
            if not valid and source["attribute_ref"] not in invalid:
                invalid.append(source["attribute_ref"])
        if scope_id and match and valid:
            bound_scope.add(scope_id)
        row = {"source_attribute_ref": source["attribute_ref"], "source_rule_ref": source["rule_ref"],
               "source_attribute_sha256": source.get("attribute_sha256"),
               "source_rule_sha256": source.get("rule_sha256"), "task_field": field,
               "task_field_value_sha256": sha256_hex(task_value), "required_scope_identifier": scope_id,
               "source_rule_kind": original_rule["rule_kind"], "source_integrity_verified": bool(valid),
               "active_attribute_ref": match["attribute_ref"] if match else None, "active_rule_ref": active_ref,
               "present_in_latest_frozen_set": bool(valid and active_ref and active_ref in frozen_refs)}
        bindings.append(row)
        if not match:
            missing.append(source["attribute_ref"])
    required_scope = {entity["identifier"] for entity in context.get("scope_entities") or []
                      if entity.get("role") == "required"}
    return {"task_id": task_id, "task_context_ref": f"{task_id}@v{context['version']}",
            "task_pinned_seq": core.journal.last_seq(task_id), "run_id": run_id, "run_state": run_state,
            "bindings": bindings, "expected_binding_count": len(bindings),
            "expected_scope_binding_count": sum(bool(row["required_scope_identifier"]) for row in bindings),
            "active_binding_count": sum(bool(row["active_rule_ref"] and row["source_integrity_verified"]) for row in bindings),
            "active_scope_binding_count": len(bound_scope), "required_scope_count": len(required_scope),
            "missing_source_attribute_refs": missing, "invalid_source_attribute_refs": invalid,
            "unbound_required_scope_identifiers": sorted(required_scope - bound_scope),
            "preserves_original_bindings": not missing and not invalid,
            "task_scope_fully_bound": required_scope <= bound_scope,
            "latest_frozen_rule_set_ref": frozen_ref,
            "frozen_scope_binding_count": sum(bool(row["required_scope_identifier"] and
                                                     row["present_in_latest_frozen_set"]) for row in bindings),
            "ok": not missing and not invalid and required_scope <= bound_scope}


def correct_required_bindings(core: Core, task_id: str, *, run_id: str, by: dict[str, Any],
                              reason: str) -> dict[str, Any]:
    """Append an auditable correction after a reduction, restoring every affected parent.

    This does not rewrite the reduction report or a frozen rule set. Restored content keeps its
    actual original author; the journal actor is restoration software, never a disguised proposer.
    No review decision or machine authority is copied onto a new rule version.
    """
    if not reason.strip():
        raise DerivationError("a required-binding correction needs a reason")
    before = required_binding_audit(core, task_id, run_id)
    if before["run_state"] not in ("completed", "failed", "unresolved", "cancelled"):
        raise DerivationError("wait for the registered reduction to end before correcting its output")
    if before["invalid_source_attribute_refs"]:
        raise DerivationError("original required-binding integrity failed; do not infer a replacement")
    registry = criteria_export._registry(core, task_id)
    source_refs = {row["source_rule_ref"] for row in before["bindings"]}
    parents = {row["source_rule_ref"]: {"attribute_ref": row["source_attribute_ref"],
                "rule_ref": row["source_rule_ref"], "attribute_sha256": row["source_attribute_sha256"],
                "rule_sha256": row["source_rule_sha256"]} for row in before["bindings"]}
    affected = []
    for entry in registry.values():
        reduction = entry["record"].get("registry_reduction") or {}
        sources = reduction.get("source_registry") or []
        if entry["kind"] == "rule" and reduction.get("run_id") == run_id and \
                any(source["rule_ref"] in source_refs for source in sources):
            affected.append(entry["ref"])
            for source in sources:
                parents[source["rule_ref"]] = source
    for source in parents.values():
        for kind in ("attribute", "rule"):
            ref = source[f"{kind}_ref"]
            if ref not in registry or source.get(f"{kind}_sha256") != criteria_export._artifact_hash(core, registry[ref]["artifact_id"]):
                raise DerivationError("an affected parent's immutable source hash does not match")
    active = criteria.registered_rule_records(core, task_id)
    active_refs = {f"{record['rule_id']}@v{record['version']}" for record in active}
    to_restore = []
    for source in parents.values():
        original_attribute = registry[source["attribute_ref"]]["record"]
        original_rule = registry[source["rule_ref"]]["record"]
        if not any(record["attribute_ref"].split("@v")[0] == original_attribute["attribute_id"] and
                   _same_required_content(criteria.load(core, record["attribute_ref"], task_id), record,
                                          original_attribute, original_rule) for record in active):
            to_restore.append(source)
    to_retire = [ref for ref in affected if ref in active_refs]
    if not to_restore and not to_retire:
        return {"status": "unchanged", "changed": False, "audit": before,
                "requires_new_freeze": False, "correction_id": None}
    correction_id = new_id("chg")
    software = make_actor("system", "required-binding-restoration", "registry", requested_by=by)
    original_events = list(core.journal.replay(run_id))
    original_result_id = next((event.payload["derivation_record_artifact_id"] for event in reversed(original_events)
                               if event.payload.get("derivation_record_artifact_id")), None)
    original_run = {"run_id": run_id, "terminal_seq": original_events[-1].seq,
                    "result_artifact_id": original_result_id,
                    "result_sha256": criteria_export._artifact_hash(core, original_result_id)}
    actions = []
    for ref in to_retire:
        criteria.retire_rule(core, task_id, ref, by=software,
                             reason=f"{correction_id}: research reduction cannot replace task requirement anchors; {reason}")
        actions.append({"operation": "retire_replacement", "rule_ref": ref})
    latest_rules = {record["rule_id"]: record for record in criteria.registered_rule_records(core, task_id, include_retired=True)}
    latest_attributes = {entry["base_id"]: entry for entry in registry.values() if entry["kind"] == "attribute"}
    prior_queue = review.items(core, [task_id])
    for source in to_restore:
        attribute = registry[source["attribute_ref"]]["record"]
        rule = registry[source["rule_ref"]]["record"]
        latest_rule = latest_rules[rule["rule_id"]]
        same_version = (latest_rule["version"] == rule["version"] and
                        latest_attributes[attribute["attribute_id"]]["ref"] == source["attribute_ref"])
        if same_version:
            restored_rule_ref, restored_attribute_ref = source["rule_ref"], source["attribute_ref"]
            core.journal.append(task_id, "criterion.change_recorded", actor=software, ids={"task_id": task_id},
                                payload={"registry": True, "registry_state": "active", "operation": "reinstate",
                                         "rule_ref": restored_rule_ref, "attribute_ref": restored_attribute_ref,
                                         "reason_text": reason, "correction_id": correction_id,
                                         "source_reduction_run_id": run_id})
        else:
            provenance = {"correction_id": correction_id, "source_reduction_run_id": run_id,
                          "source": source, "authority_carried": False,
                          "restored_by": software,
                          "authorship": "content restored from the immutable original; journal actor is restoration software"}
            restored_attribute_ref = criteria.record_version(
                core, task_id, "attribute", latest_attributes[attribute["attribute_id"]]["ref"], attribute, by=software,
                summary=f"{correction_id}: restore original task/research parent {source['attribute_ref']}",
                extra={"required_binding_restoration": provenance})
            restored_rule_ref = criteria.record_version(
                core, task_id, "rule", f"{latest_rule['rule_id']}@v{latest_rule['version']}",
                dict(rule, attribute_ref=restored_attribute_ref), by=software,
                summary=f"{correction_id}: restore original parent {source['rule_ref']}",
                extra={"required_binding_restoration": provenance})
            old_requests = [item for item in prior_queue.values() if item["subject"].get("id") == source["rule_ref"]]
            owed = criteria.authority_requirements(rule, attribute)
            if old_requests or owed:
                review.request(core, task_id, subject={"kind": "rule_version", "id": restored_rule_ref,
                                                       "version": int(restored_rule_ref.rsplit("@v", 1)[1]),
                                                       "attribute_ref": restored_attribute_ref},
                               why_expert_required="original parent restored as a new version; prior authority is not copied: "
                               + (old_requests[0]["why_expert_required"] if old_requests else
                                  "; ".join(item["detail"] for item in owed)), requested_by=software,
                               inspection_bundle={"required_binding_restoration": provenance})
        actions.append({"operation": "restore_parent", "source_rule_ref": source["rule_ref"],
                        "attribute_ref": restored_attribute_ref, "rule_ref": restored_rule_ref,
                        "new_version": not same_version})
    after = required_binding_audit(core, task_id, run_id)
    record = {"kind": "required_binding_correction", "correction_id": correction_id, "task_id": task_id,
              "source_reduction_run_id": run_id, "reason": reason, "requested_by": by, "actions": actions,
              "original_run": original_run,
              "audit_before": before, "audit_after": after, "requires_new_freeze": True,
              "original_run_report_unchanged": True}
    artifact_id = core.artifacts.put("required_binding_correction", record)
    core.journal.append(task_id, "criterion.change_recorded", actor=software, ids={"task_id": task_id},
                        payload={"required_binding_correction": True, "correction_id": correction_id,
                                 "source_reduction_run_id": run_id, "artifact_id": artifact_id},
                        artifact_links=[{"kind": "required_binding_correction", "id": artifact_id}],
                        summary=f"{correction_id}: restored original bindings and all affected parents; new freeze required")
    return dict(record, status="applied", changed=True, artifact_id=artifact_id)


def registered_reduction_summary(core: Core, task_id: str, run_id: str | None = None) -> dict[str, Any]:
    """Read registry/reduction counts without historical items, evaluator artifacts or a board."""
    inventory = criteria.registry_inventory(core, task_id)
    folded = pool_mod.fold(core, task_id)
    if run_id is None:
        seed_events = [event for event in core.journal.replay(task_id)
                       if event.event_type == "criterion.change_recorded" and event.payload.get("pool")
                       and event.payload.get("reason_kind") == "registered_input"]
        run_id = seed_events[-1].payload.get("round_run_id") if seed_events else None
    scope, manifest_id, manifest = [], None, None
    if run_id:
        binding = _binding_of(core, run_id)
        if binding.get("operation") != "registered_reduction" or binding["task_context_id@v"].split("@v")[0] != task_id:
            raise DerivationError(f"{run_id} is not a registry reduction of {task_id}")
        manifest_id = binding["source_inputs_artifact_id"]
        manifest = core.artifacts.payload(manifest_id)
        backlog_ids = {ref.split("@v")[0] for ref in manifest["backlog_pool_refs"]}
        scope = [entry for entry in folded.values() if entry["criterion_id"] in backlog_ids or
                 any(change.get("round_run_id") == run_id for change in entry["history"])]
    active_refs = {row["rule_ref"] for row in inventory["active"]}
    unresolved = [entry for entry in scope if entry["state"] in pool_mod.ACTIVE_STATES]
    additional = [entry for entry in unresolved if not (
        len(entry["item"].get("source_registry") or []) == 1 and
        entry["item"]["source_registry"][0]["rule_ref"] in active_refs)]
    counts = {}
    for entry in scope:
        counts[entry["state"]] = counts.get(entry["state"], 0) + 1
    retired_here = [event.payload["rule_ref"] for event in core.journal.replay(task_id)
                    if event.event_type == "criterion.change_recorded" and event.payload.get("registry")
                    and event.payload.get("registry_state") == "retired"
                    and run_id and event.payload.get("reduction_run_id") == run_id]
    corrections = [dict(event.payload, seq=event.seq) for event in core.journal.replay(task_id)
                   if event.event_type == "criterion.change_recorded" and event.payload.get("required_binding_correction")
                   and (not run_id or event.payload.get("source_reduction_run_id") == run_id)]
    try:
        frozen = criteria.rule_set(core, task_id)["rule_set_ref"]
    except KeyError:
        frozen = None
    return dict(inventory, task_context_ref=f"{task_id}@v{task_mod.latest_version(core, task_id)}",
                run_id=run_id, latest_frozen_rule_set_ref=frozen, scope_pool_states=counts,
                unresolved_pool_count=len(unresolved), additional_unregistered_active_count=len(additional),
                total_active_count=inventory["active_registered_count"] + len(additional),
                retired_by_this_run_count=len(set(retired_here)), source_inputs_artifact_id=manifest_id,
                source_inputs_sha256=criteria_export._artifact_hash(core, manifest_id),
                source_runs=(manifest or {}).get("source_runs") or [],
                inherited_claim_count=len((manifest or {}).get("claims") or []),
                historical_pool_lineage_count_before_reduction=(manifest or {}).get("historical_pool_lineage_count"),
                pool_lineage_count_now=len(folded), required_binding_corrections=corrections)


def reduce_registered(core: Core, roster: ModelRoster, task_id: str, *, source_run_ids: list[str],
                      catalog: list[dict[str, Any]], by: dict[str, Any], reason: str,
                      inner_iterations: int = 3, stall_rounds: int = 2, max_refines: int = 2,
                      merge_overlap: float = 0.35, budget: Any = None, settings: Any = None,
                      implementation: dict[str, Any] | None = None) -> dict[str, Any]:
    """Reduce a fresh inherited registry using explicitly selected existing evidence only.

    No broker, enumeration or proposal pass is involved. Each source run is pinned with its real
    execution state, including failed/incomplete runs whose admitted claims remain usable. Registry
    replacements are append-only, while unresolved reductions keep their original parents active.
    """
    if not reason.strip() or not source_run_ids:
        raise DerivationError("registry reduction needs a reason and an explicit source_run_ids list")
    context = task_mod.get(core, task_id)
    if any(e.event_type == "criterion.version_approved" for e in core.journal.replay(task_id)):
        raise DerivationError("reduce a fresh inherited task; an existing frozen reading stays unchanged")
    required_audit = required_binding_audit(core, task_id)
    if required_audit["missing_source_attribute_refs"] or required_audit["invalid_source_attribute_refs"]:
        raise DerivationError("restore original task requirement anchors before another research reduction")
    ancestry = {}
    cursor = context
    while cursor.get("derived_from_task_id"):
        source_task = cursor["derived_from_task_id"]
        if source_task in ancestry:
            raise DerivationError("cyclic task inheritance")
        pin = (cursor.get("inheritance") or {}).get("source_at_seq")
        source_core, pin = criteria_export.pinned(core, source_task, pin)
        ancestry[source_task] = pin
        cursor = task_mod.get(source_core, source_task)
    if not ancestry:
        raise DerivationError("registry reduction requires an inherited task with pinned provenance")

    source_records, claim_records, claims = [], {}, {}
    chain_ids, owners = set(), set()
    for source_run in dict.fromkeys(source_run_ids):
        if not source_run.startswith("run_"):
            raise DerivationError(f"{source_run} is not a derivation run")
        events = list(core.journal.replay(source_run))
        if not events or events[0].event_type != "run.created":
            raise DerivationError(f"{source_run} is not a run")
        binding = core.artifacts.payload(events[0].payload["binding_artifact_id"])
        if binding.get("run_purpose") != "criteria_derivation":
            raise DerivationError(f"{source_run} is not criteria-derivation evidence")
        owner = binding["task_context_id@v"].split("@v")[0]
        if owner not in ancestry:
            raise DerivationError(f"{source_run} is outside this task's inherited provenance")
        chain_ids.add(binding["chain_id"])
        owners.add(owner)
        lifecycle = [e for e in events if e.event_type.startswith("run.") and e.state_to]
        last = lifecycle[-1] if lifecycle else None
        source_records.append({"run_id": source_run, "task_id": owner, "pinned_seq": events[-1].seq,
                               "chain_id": binding["chain_id"],
                               "execution_state": last.state_to if last else "unknown",
                               "termination_reason": last.termination_reason if last else None,
                               "binding_artifact_id": events[0].payload["binding_artifact_id"],
                               "binding_sha256": criteria_export._artifact_hash(
                                   core, events[0].payload["binding_artifact_id"])})
        for event in events:
            if event.event_type != "evidence.admitted":
                continue
            artifact_id = event.payload["artifact_id"]
            claim = core.artifacts.payload(artifact_id)
            if claim.get("admission_state") != "admitted":
                continue
            identity = {"claim_id": claim["claim_id"], "artifact_id": artifact_id,
                        "artifact_sha256": criteria_export._artifact_hash(core, artifact_id),
                        "source_run_id": source_run, "source_seq": event.seq}
            previous = claim_records.get(claim["claim_id"])
            if previous and previous["artifact_sha256"] != identity["artifact_sha256"]:
                raise DerivationError(f"conflicting inherited claim identity {claim['claim_id']}")
            claims[claim["claim_id"]], claim_records[claim["claim_id"]] = claim, identity
    if len(chain_ids) != 1 or len(owners) != 1:
        raise DerivationError("select explicit runs from one inherited source task and derivation chain")
    source_owner = next(iter(owners))
    source_core, source_pin = criteria_export.pinned(core, source_owner, ancestry[source_owner])
    for event in source_core.journal.replay(source_owner):
        if event.event_type == "evidence.admitted":
            artifact_id = event.payload["artifact_id"]
            claim = core.artifacts.payload(artifact_id)
            if claim.get("admission_state") == "admitted":
                claims.setdefault(claim["claim_id"], claim)
                claim_records.setdefault(claim["claim_id"], {
                    "claim_id": claim["claim_id"], "artifact_id": artifact_id,
                    "artifact_sha256": criteria_export._artifact_hash(core, artifact_id),
                    "source_task_id": source_owner, "source_seq": event.seq})

    registry = criteria_export._registry(core, task_id)
    rules = criteria.registered_rule_records(core, task_id)
    prior_pool = pool_mod.fold(core, task_id)
    by_attribute = {entry["promoted_as"]["attribute_ref"].split("@v")[0]: entry
                    for entry in prior_pool.values() if entry.get("promoted_as")}
    inputs = []
    for rule in rules:
        rule_ref = f"{rule['rule_id']}@v{rule['version']}"
        attribute = registry[rule["attribute_ref"]]["record"]
        origin = (by_attribute.get(attribute["attribute_id"]) or {}).get("item") or {}
        source = {"attribute_ref": rule["attribute_ref"], "rule_ref": rule_ref,
                  "attribute_artifact_id": registry[rule["attribute_ref"]]["artifact_id"],
                  "rule_artifact_id": registry[rule_ref]["artifact_id"],
                  "task_mandated": criteria.is_task_mandated(attribute)}
        for kind in ("attribute", "rule"):
            source[f"{kind}_sha256"] = criteria_export._artifact_hash(core, source[f"{kind}_artifact_id"])
        inputs.append({"attribute": attribute, "rule": rule,
                       "supporting_claim_ids": list(attribute.get("supporting_claim_refs") or []),
                       "dimension": origin.get("dimension") or "task_mandated",
                       "expected_change": rule.get("expected_change") or "retain useful distinctions while reducing redundancy",
                       "falsification_test": rule.get("falsification_test") or "a reduction must preserve supported distinctions",
                       "refine_count": 0, "consolidation": origin.get("consolidation"), "source_registry": [source]})
    backlog = [entry for entry in prior_pool.values() if entry["state"] in
               ("candidate", "needs_refine", "deferred_next_round")]
    protected = {item["source_registry"][0]["attribute_ref"] for item in inputs
                 if item["source_registry"][0]["task_mandated"]}
    protected_bases = {ref.split("@v")[0] for ref in protected}
    protected_backlog = {entry["criterion_id"] for entry in backlog
                         if any(source["attribute_ref"].split("@v")[0] in protected_bases
                                for source in entry["item"].get("source_registry") or [])}
    cited = {ref for item in inputs + [entry["item"] for entry in backlog]
             for ref in item.get("supporting_claim_ids") or []}
    if cited - claims.keys():
        raise DerivationError(f"explicit source runs omit {len(cited - claims.keys())} cited claims; "
                              "supply their original derivation runs before reducing the registry")
    manifest = {"kind": "registered_reduction_inputs", "source_task_id": source_owner,
                "source_task_pinned_seq": source_pin, "source_runs": source_records,
                "claims": [claim_records[key] for key in sorted(claim_records)],
                "registered_inputs": [item["source_registry"][0] for item in inputs],
                "backlog_pool_refs": [f"{e['criterion_id']}@v{e['version']}" for e in backlog],
                "historical_pool_lineage_count": len(prior_pool),
                "required_anchor_policy": "protected_task_bindings_v1",
                "protected_input_attribute_refs": sorted(protected),
                "protected_backlog_pool_refs": sorted(protected_backlog),
                "reads_new_evidence": False, "proposes_new_criteria": False, "reason": reason}
    manifest_id = core.artifacts.put("registered_reduction_inputs", manifest)
    run_id, ids, binding = _open_run(
        core, task_id, by=by, roster=roster, parents=[], continues_run_id=None, settings=settings,
        implementation=implementation, purpose_note="reduce existing registered criteria without new literature or proposals",
        binding_extra={"reads_new_evidence": False, "proposes_new_criteria": False,
                       "operation": "registered_reduction", "source_inputs_artifact_id": manifest_id,
                       "required_anchor_policy": "protected_task_bindings_v1",
                       "source_inputs_sha256": criteria_export._artifact_hash(core, manifest_id),
                       "inner_iterations": inner_iterations, "stages": list(DEFAULT_STAGES),
                       "max_refines": max_refines, "merge_overlap": merge_overlap})
    ctx = _stage_context(core, roster, task_id, run_id, context=context, catalog=catalog, claims=claims,
                         budget=budget, max_refines=max_refines)
    ctx.registry_reduce, ctx.pool_scope = True, {entry["criterion_id"] for entry in backlog
                                              if entry["criterion_id"] not in protected_backlog}
    ctx.registry_input_refs = {item["source_registry"][0]["attribute_ref"] for item in inputs} - protected
    input_ids = []
    for item in inputs:
        criterion_id = ctx.pool.at("registry_inputs", 0).add(item, reason_kind="registered_input",
                                                           reason_text="existing registered criterion in reduction scope")
        if item["source_registry"][0]["attribute_ref"] in protected:
            source = item["source_registry"][0]
            entry = ctx.pool.fold()[criterion_id]
            ctx.pool.set_state(entry, "promoted", operation="promote", reason_kind="protected_task_requirement",
                               reason_text="task-defined anchor retained unchanged outside research reduction",
                               extra={"promoted_as": {"attribute_ref": source["attribute_ref"],
                                                       "rule_ref": source["rule_ref"]}})
            continue
        ctx.pool_scope.add(criterion_id)
        input_ids.append(criterion_id)
    record = {"task_id": task_id, "run_id": run_id, "chain_id": binding["chain_id"],
              "round_index": binding["round_index"], "operation": "registered_reduction",
              "source_inputs_artifact_id": manifest_id, "registered_input_count": len(inputs),
              "backlog_input_count": len(backlog), "reads_new_evidence": False, "proposes_new_criteria": False,
              "required_anchor_policy": "protected_task_bindings_v1", "protected_input_count": len(protected),
              "iterations": []}
    stage = _stage_recorder(core, task_id, run_id, ids)
    termination = "round_limit_reached"
    try:
        termination = _prune(ctx, stage, record["iterations"], stage_names=DEFAULT_STAGES,
                             inner_iterations=inner_iterations, stall_rounds=stall_rounds, merge_overlap=merge_overlap)
        record["promotion"] = stage("promote", 0, lambda: stages.promote(ctx, by_proposer=stages.proposer_actor(ctx)))
        final_pool = pool_mod.fold(core, task_id)
        for criterion_id in input_ids:
            entry = final_pool[criterion_id]
            if entry["state"] not in ("withdrawn", "filtered_out"):
                continue
            for source in entry["item"].get("source_registry") or []:
                last = entry["history"][-1]
                criteria.retire_rule(core, task_id, source["rule_ref"], by=CONTROLLER,
                                     reason=last.get("reason_text") or last["reason_kind"],
                                     reduction_run_id=run_id,
                                     source_pool_ref=f"{criterion_id}@v{entry['version']}")
    except ModelError as error:
        if error.error_class != "quota_exhausted":
            _fail(core, run_id, ids, error)
            raise
        termination = "budget_exhausted"
    except Exception as error:
        _fail(core, run_id, ids, error)
        raise
    record["registry_inventory"] = registered_reduction_summary(core, task_id, run_id)
    record["unresolved_pool_refs"] = [f"{e['criterion_id']}@v{e['version']}" for e in ctx.active()]
    return _close_run(core, task_id, run_id, ids, record, roster=roster, budget=budget, termination=termination)


def derive_iterative(core: Core, broker, roster: ModelRoster, task_id: str, *, dimensions: list[dict[str, str]],
                     catalog: list[dict[str, Any]], by: dict[str, Any], research: dict[str, Any] | None = None,
                     inner_iterations: int = 3, stall_rounds: int = 2, stage_names: tuple[str, ...] = DEFAULT_STAGES,
                     max_refines: int = 2, merge_overlap: float = 0.35, cutoff_date: str | None = None,
                     budget: Any = None, templates=None, continues_run_id: str | None = None,
                     settings: Any = None, implementation: dict[str, Any] | None = None,
                     observer=None, checkpoint=None) -> dict[str, Any]:
    """One round of the criteria pool workflow as a run; returns the derivation record."""
    unknown = [s for s in stage_names if s not in stages.STAGES]
    if unknown:
        raise DerivationError(f"unknown stages {unknown}; known stages are {sorted(stages.STAGES)}")
    context = task_mod.get(core, task_id)
    parents = _chain_runs(core, continues_run_id) if continues_run_id else []
    run_id, ids, binding = _open_run(
        core, task_id, by=by, roster=roster, parents=parents, continues_run_id=continues_run_id,
        implementation=implementation, purpose_note="derive criteria from new literature", settings=settings,
        binding_extra={"research": research or dict(derivation.DEFAULT_RESEARCH),
                       "inner_iterations": inner_iterations, "stall_rounds": stall_rounds,
                       "stages": list(stage_names), "max_refines": max_refines, "merge_overlap": merge_overlap,
                       "evidence_cutoff": cutoff_date, "dimensions": [d["dimension"] for d in dimensions],
                       "reads_new_evidence": True})
    if observer:
        observer("created", {"run_id": run_id})
    core, budget, broker = _activity_context(core, run_id, budget, observer, checkpoint, broker)
    record: dict[str, Any] = {"task_id": task_id, "run_id": run_id, "chain_id": binding["chain_id"],
                              "round_index": binding["round_index"], "continues_run_id": continues_run_id,
                              "inherited_claim_routing_artifact_id": None}
    termination = "round_limit_reached"
    stage = _stage_recorder(core, task_id, run_id, ids, observer=observer, checkpoint=checkpoint)
    try:
        record["mandated"] = (stage("mandated", 0, lambda: derivation.objective_criteria(core, task_id, templates=templates, by=by))
                              if templates else [])
        read_cache: dict[str, list[dict[str, Any]]] = {}
        enumerations = []

        def enumerate_all():
            for d in dimensions:
                enumerations.append(derivation.enumerate_dimension(
                    core, broker, roster, run_id, task_context=context, dimension=d, cutoff_date=cutoff_date, ids=ids,
                    budget=budget, all_dimensions=dimensions, read_cache=read_cache, research=research))
            return [{k: e[k] for k in ("dimension", "documents_read", "stop_reason", "rounds")}
                    | {"n_claims": len(e["claims"]), "n_topics": len(e["hints"])} for e in enumerations]

        record["enumeration"] = stage("enumerate", 0, enumerate_all)
        claims = {c["claim_id"]: c for e in enumerations for c in e["claims"]}
        # claims cited by pool items from earlier rounds stay resolvable
        for claim in ledger.claims(core, parents + [task_id]):
            claims.setdefault(claim["claim_id"], claim)
        # The chain's admitted claims are also proposed *from*, not only cited: a round may follow one
        # that read a hundred and seventy-nine documents and never reached its own proposal pass
        # (round 5 died waiting on an unavailable provider, 15 October 2026), and the operator
        # instructed that the new round carry that reading rather than re-buy it. The inherited set is
        # grouped by the dimension the earlier round was reading for, not handed to every dimension
        # whole; `_inherited_claims_by_dimension` says why and how. The stage record keeps the counts,
        # so what was inherited is readable from the run, not inferred.
        routing_log = []
        inherited = _inherited_claims_by_dimension(core, parents, dimensions, routing_log=routing_log)
        record["inherited_claim_routing_artifact_id"] = core.artifacts.put(
            "inherited_claim_routing", {"policy": "semantic_multilabel_v1", "source_runs": parents,
                                         "routes": routing_log})
        ctx = _stage_context(core, roster, task_id, run_id, context=context, catalog=catalog, claims=claims,
                             budget=budget, max_refines=max_refines)
        record["proposed"] = {}
        for enumeration, dimension in zip(enumerations, dimensions):
            own = [c for c in enumeration["claims"] if c.get("admission_state") == "admitted"]
            dim_claims = own + inherited[dimension["dimension"]]
            ctx.pool.at("propose", 0)
            record["proposed"][dimension["dimension"]] = stage(
                f"propose:{dimension['dimension']}", 0, lambda d=dimension, cl=dim_claims: stages.propose(ctx, d, cl))
        record["iterations"] = []
        termination = _prune(ctx, stage, record["iterations"], stage_names=stage_names,
                             inner_iterations=inner_iterations, stall_rounds=stall_rounds,
                             merge_overlap=merge_overlap)
        record["promotion"] = stage("promote", 0, lambda: stages.promote(ctx, by_proposer=stages.proposer_actor(ctx)))
    except ModelError as error:
        if error.error_class != "quota_exhausted":
            _fail(core, run_id, ids, error)
            raise
        termination = "budget_exhausted"
    except InterruptedError as error:
        _interrupted(core, run_id, ids, error)
        raise
    except Exception as error:
        _fail(core, run_id, ids, error)
        raise
    return _close_run(core, task_id, run_id, ids, record, roster=roster, budget=budget, termination=termination)


def _fail(core: Core, run_id: str, ids: dict[str, Any], error: Exception) -> None:
    """A crashed round ends `failed` with the error class; its pool changes so far remain recorded."""
    _emit(core, run_id, "run.failed", ids=ids, state_from="running", state_to="failed",
          termination_reason="repeated_failure",
          payload={"error_class": getattr(error, "error_class", type(error).__name__), "message": str(error)[:500]})


def record_of(core: Core, run_id: str) -> dict[str, Any] | None:
    for event in reversed(core.journal.replay(run_id)):
        if event.event_type in ("run.completed", "run.unresolved") and event.payload.get("derivation_record_artifact_id"):
            return core.artifacts.payload(event.payload["derivation_record_artifact_id"])
    return None
