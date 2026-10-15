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

from typing import Any

from . import criteria, derivation, derivation_stages as stages, ledger, pool as pool_mod, task as task_mod
from .canonical import sha256_hex
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


def _inherited_claims_by_dimension(core: Core, parent_runs: list[str],
                                   dimensions: list[dict[str, str]]) -> dict[str, list[dict[str, Any]]]:
    """The chain's admitted claims, grouped by the dimension each was read for.

    A round reads one dimension at a time and opens each dimension's reading with its
    `plan queries: <focus>` calls, so a claim's `recorded_at` places it in the span the round was
    reading for one dimension; the grouping is the one the round itself would have built had it
    reached its proposal pass.

    WHY grouped rather than handed to every dimension whole -- operator instruction to finish
    quickly, 15 October 2026: the inherited set measured 2,234 claims (round 5's 1,771 and round
    6's 463), and offering all of it to all four dimensions cost 24 proposer calls where the
    grouping costs 8, most of the difference being round 5's 1,489 target-coverage claims. A claim
    whose time falls in no span is offered to every dimension: dropping it would be the worse
    error, and a round that never opened a dimension has no span to place its claims in.
    """
    by_focus = {d["focus"]: d["dimension"] for d in dimensions}
    grouped: dict[str, list[dict[str, Any]]] = {d["dimension"]: [] for d in dimensions}
    unplaced: list[dict[str, Any]] = []
    for run_id in parent_runs:
        marks: list[tuple[str, str]] = []
        for event in core.journal.replay(run_id):
            question = event.question or ""
            if not question.startswith("plan queries: "):
                continue
            rest = question[len("plan queries: "):]
            dimension = next((name for focus, name in by_focus.items() if rest.startswith(focus)), None)
            if dimension and (not marks or marks[-1][0] != dimension):
                marks.append((dimension, event.recorded_at))
        spans = [(dimension, start, marks[index + 1][1] if index + 1 < len(marks) else None)
                 for index, (dimension, start) in enumerate(marks)]
        for claim in ledger.claims(core, [run_id]):
            at = claim.get("recorded_at") or ""
            placed = next((dimension for dimension, start, end in spans
                           if start <= at and (end is None or at < end)), None)
            (grouped[placed] if placed else unplaced).append(claim)
    for claims in grouped.values():
        claims.extend(unplaced)
    return grouped


def _stage_recorder(core: Core, task_id: str, run_id: str, ids: dict[str, Any]):
    """A `stage(name, iteration, fn)` that records the pool hash either side of a stage.

    Shared by `derive_iterative` and `reduce_pool` so a stage looks the same in the journal whichever
    entered it -- a reader comparing two rounds should not have to know which function ran them.
    """
    def stage(name: str, iteration: int, fn):
        before = pool_mod.pool_hash(pool_mod.fold(core, task_id))
        key = sha256_hex({"stage": name, "iteration": iteration, "run_id": run_id, "input_pool_hash": before})
        _emit(core, run_id, "stage.opened", ids=ids, payload={"stage": name, "iteration": iteration, "stage_key": key})
        result = fn()
        after = pool_mod.pool_hash(pool_mod.fold(core, task_id))
        result_id = core.artifacts.put("derivation_stage", {"stage": name, "iteration": iteration, "result": result,
                                                            "input_pool_hash": before, "output_pool_hash": after})
        _emit(core, run_id, "stage.closed", ids=ids, state_to="completed",
              payload={"stage": name, "iteration": iteration, "stage_key": key, "result_artifact_id": result_id,
                       "pool_changed": before != after, "result": result}, summary=f"{name} {iteration}: {result}")
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
                implementation: dict[str, Any] | None = None) -> dict[str, Any]:
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
    claims = {c["claim_id"]: c for c in ledger.claims(core, parents + [task_id])}
    ctx = _stage_context(core, roster, task_id, run_id, context=context, catalog=catalog, claims=claims,
                         budget=budget, max_refines=max_refines)
    record: dict[str, Any] = {"task_id": task_id, "run_id": run_id, "chain_id": binding["chain_id"],
                              "round_index": binding["round_index"], "continues_run_id": continues_run_id,
                              "reduce_only": True, "claims_resolvable": len(claims)}
    termination = "round_limit_reached"
    stage = _stage_recorder(core, task_id, run_id, ids)
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
    except Exception as error:
        _fail(core, run_id, ids, error)
        raise
    return _close_run(core, task_id, run_id, ids, record, roster=roster, budget=budget, termination=termination)


def derive_iterative(core: Core, broker, roster: ModelRoster, task_id: str, *, dimensions: list[dict[str, str]],
                     catalog: list[dict[str, Any]], by: dict[str, Any], research: dict[str, Any] | None = None,
                     inner_iterations: int = 3, stall_rounds: int = 2, stage_names: tuple[str, ...] = DEFAULT_STAGES,
                     max_refines: int = 2, merge_overlap: float = 0.35, cutoff_date: str | None = None,
                     budget: Any = None, templates=None, continues_run_id: str | None = None,
                     settings: Any = None, implementation: dict[str, Any] | None = None) -> dict[str, Any]:
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
    record: dict[str, Any] = {"task_id": task_id, "run_id": run_id, "chain_id": binding["chain_id"],
                              "round_index": binding["round_index"], "continues_run_id": continues_run_id}
    termination = "round_limit_reached"
    stage = _stage_recorder(core, task_id, run_id, ids)
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
        inherited = _inherited_claims_by_dimension(core, parents, dimensions)
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
