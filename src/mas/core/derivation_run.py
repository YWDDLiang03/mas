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
    parent_binding = None
    if parents:
        created = core.journal.replay(parents[-1], 1, 1)[0]
        parent_binding = core.artifacts.payload(created.payload["binding_artifact_id"])
    run_id = new_id("run")
    ids = {"task_id": task_id, "run_id": run_id}
    binding = {
        "bind_id": f"bind_{run_id}", "run_id": run_id, "run_purpose": "criteria_derivation",
        "task_context_id@v": f"{task_id}@v{context['version']}", "rules@v": None,
        "chain_id": parent_binding["chain_id"] if parent_binding else new_id("chain"),
        "continues_run_id": continues_run_id, "continuation_kind": "continue" if continues_run_id else "root",
        "round_index": len(parents) + 1, "role_bindings": roster.role_bindings(),
        "research": research or dict(derivation.DEFAULT_RESEARCH), "inner_iterations": inner_iterations,
        "stall_rounds": stall_rounds, "stages": list(stage_names), "max_refines": max_refines,
        "merge_overlap": merge_overlap, "evidence_cutoff": cutoff_date,
        "dimensions": [d["dimension"] for d in dimensions],
        "settings": ({"config_hash": settings.hash(), "preset": settings.preset, "profile": settings.profile,
                      "layers_artifact_id": core.artifacts.put("config_layers", settings.layer_record())}
                     if settings is not None else None),
        "derivation_configuration": "reference_disclosed",
        "known_reference_outcome_disclosure": [s for s in context.get("seed_candidates", []) if s.get("is_reference_outcome")],
        "implementation": implementation, "bound_at": utc_now(), "bound_by": by,
    }
    binding_id = core.artifacts.put("run_binding", binding)
    _emit(core, run_id, "run.created", actor=by, ids=ids, state_to="queued",
          payload={"binding_artifact_id": binding_id, "task_id": task_id, "chain_id": binding["chain_id"],
                   "run_purpose": "criteria_derivation"},
          artifact_links=[{"kind": "run_binding", "id": binding_id}],
          summary=f"criteria derivation round {binding['round_index']}")
    if settings is not None:
        from .config import register_constants
        register_constants(core, settings, by=by, stream_id=run_id)
    if continues_run_id:
        core.journal.append(task_id, "run.continued", actor=by, payload={
            "parent_run_id": continues_run_id, "run_id": run_id, "continuation_kind": "continue"})
    _emit(core, run_id, "run.started", ids=ids, state_from="queued", state_to="running")
    _emit(core, run_id, "round.opened", ids=ids, payload={"round_id": f"round_{run_id}_1",
                                                         "trigger": "continuation" if parents else "first_round"})

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

    record: dict[str, Any] = {"task_id": task_id, "run_id": run_id, "chain_id": binding["chain_id"],
                              "round_index": binding["round_index"], "continues_run_id": continues_run_id}
    termination = "round_limit_reached"
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
        ctx = stages.StageContext(
            core=core, roster=roster, task_id=task_id, run_id=run_id, task_context=context, catalog=catalog,
            claims_by_id=claims, budget=budget, max_refines=max_refines,
            reference_labels=[label for s in context.get("seed_candidates", []) if s.get("is_reference_outcome")
                              for label in [s["candidate_ref"], *s.get("aliases", [])]],
            pool=pool_mod.Pool(core, task_id, by=stages.proposer_actor_for(roster), run_id=run_id))
        record["proposed"] = {}
        for enumeration, dimension in zip(enumerations, dimensions):
            dim_claims = [c for c in enumeration["claims"] if c.get("admission_state") == "admitted"]
            ctx.pool.at("propose", 0)
            record["proposed"][dimension["dimension"]] = stage(
                f"propose:{dimension['dimension']}", 0, lambda d=dimension, cl=dim_claims: stages.propose(ctx, d, cl))
        record["iterations"] = []
        stalled = 0
        for iteration in range(1, inner_iterations + 1):
            before = pool_mod.pool_hash(pool_mod.fold(core, task_id))
            results = {}
            for name in stage_names:
                fn = stages.STAGES[name]
                if name == "merge":
                    results[name] = stage(name, iteration, lambda: stages.merge_stage(ctx, iteration, overlap=merge_overlap))
                else:
                    results[name] = stage(name, iteration, lambda fn=fn: fn(ctx, iteration))
            changed = pool_mod.pool_hash(pool_mod.fold(core, task_id)) != before
            record["iterations"].append({"iteration": iteration, "pool_changed": changed, **results})
            stalled = 0 if changed else stalled + 1
            if stalled >= stall_rounds:
                termination = "diminishing_information_gain"
                break
        record["promotion"] = stage("promote", 0, lambda: stages.promote(ctx, by_proposer=stages.proposer_actor(ctx)))
    except ModelError as error:
        if error.error_class != "quota_exhausted":
            _fail(core, run_id, ids, error)
            raise
        termination = "budget_exhausted"
    except Exception as error:
        _fail(core, run_id, ids, error)
        raise
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
    end_state, end_event = ("unresolved", "run.unresolved") if termination == "budget_exhausted" else ("completed", "run.completed")
    _emit(core, run_id, "round.closed", ids=ids, termination_reason=termination,
          payload={"round_id": f"round_{run_id}_1", "continuation_decision": decision,
                   "derivation_record_artifact_id": record["artifact_id"]})
    _emit(core, run_id, end_event, ids=ids, state_from="running", state_to=end_state, termination_reason=termination,
          payload={"derivation_record_artifact_id": record["artifact_id"]})
    return record


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
