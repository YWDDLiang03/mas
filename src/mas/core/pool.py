"""The criteria pool (design §5.6): candidate criteria as lineages that survive iterations and rounds.

A pool item is a *lineage* `cri_<ulid>`: it keeps its id while stages revise it, and each
revision is a new version. Every transition is one `criterion.change_recorded` event in
the task stream carrying the operation, the versions it consumed (`targets_in`) and
produced (`targets_out`), the reason, and the claims that justify it. A reduction -- a `merge`
of one quantity's several descriptions, or a `consolidate` of a family of distinct endpoints
into one screening criterion -- writes one record per parent (state `merged_away`, pointing at
the child) and one for the child (pointing at its parents), so lineage reads both ways.
Nothing is deleted.

`fold()` replays those events into the current pool; because the events live in the task
stream, a later round (a new run in the same chain) folds the same pool and continues
from it. This module makes no model calls.
"""

from __future__ import annotations

from typing import Any

from . import vocab
from .canonical import sha256_hex
from .ids import new_id
from .runtime import Core

ACTIVE_STATES = ("candidate", "needs_refine", "deferred_next_round")
# WHY refine_count is persisted: `refine_stage` writes it onto the item and `filter_stage` reads it to decide
# whether an item has exhausted `max_refines`, but it was not in this list, so `_record` dropped it and a fold
# read it back as 0. The repair budget therefore reset on every store reopen and every round continuation, and
# `max_refines` bounded nothing durably -- an item could be revised indefinitely as long as the run was resumed.
# The budget is per lineage and cumulative across rounds: its purpose is to stop the pool rewriting one
# proposal forever, and a round boundary is not a reason to grant a fresh allowance. Historical records predate
# this field and legitimately fold to 0; they are not backfilled with invented counts, so a run derived before
# this change keeps whatever repair history it actually recorded.
# WHY `consolidation` is persisted on the item and not only in the change record's reason text: a consolidated
# criterion replaces a family of specific endpoints with an abstraction over them, and the only thing standing
# between that and information loss is the reviewer's ability to read which endpoints were folded in and object.
# A reason string is prose; this is the list, with each subsumed lineage's id, version and name, the shared
# property claimed for the family, and the aggregation that computes it. Items that are not consolidations do not
# carry the field, and historical records legitimately fold it back as None.
ITEM_FIELDS = ("attribute", "rule", "supporting_claim_ids", "expected_change", "falsification_test", "dimension",
               "validator_problems", "critic_findings", "refine_count", "consolidation", "source_registry")

# The operations that produce a child from several parents, so `fold` reads lineage both ways for each of them.
# `consolidate` is the second one (`vocab.DOMAINS["criterion_change_operation"]`); the states it writes are the
# merge states unchanged, because `merged_away` ("merged into another") is exactly where a subsumed parent goes
# and a new registered state would say nothing `operation` does not already say.
REDUCTION_OPERATIONS = ("merge", "consolidate")


def _ref(criterion_id: str, version: int) -> str:
    return f"{criterion_id}@v{version}"


def _record(core: Core, task_id: str, *, criterion_id: str, version: int, operation: str, state: str, by: dict[str, Any],
            context: dict[str, Any], reason_kind: str, reason_text: str = "", item: dict[str, Any] | None = None,
            targets_in: list[str] | None = None, targets_out: list[str] | None = None,
            source_refs: list[str] | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    vocab.require("criterion_change_operation", operation)
    vocab.require("criterion_pool_state", state)
    artifact_id = None
    if item is not None:
        artifact_id = core.artifacts.put("criterion_candidate", {"criterion_id": criterion_id, "version": version,
                                                                 **{k: (item.get(k) or []) if k == "source_registry"
                                                                    else item.get(k) for k in ITEM_FIELDS}})
    payload = {"pool": True, "change_id": new_id("chg"), "criterion_id": criterion_id, "version": version,
               "operation": operation, "state": state, "targets_in": targets_in or [], "targets_out": targets_out or [],
               "reason_kind": reason_kind, "reason_text": reason_text[:2000], "source_refs": source_refs or [],
               "artifact_id": artifact_id, **context, **(extra or {})}
    core.journal.append(task_id, "criterion.change_recorded", actor=by, ids={"task_id": task_id}, payload=payload,
                        artifact_links=[{"kind": "criterion_candidate", "id": artifact_id}] if artifact_id else [],
                        summary=f"{operation} {_ref(criterion_id, version)} -> {state}")
    return payload


def fold(core: Core, task_id: str) -> dict[str, dict[str, Any]]:
    """Current pool: criterion_id -> {version, state, item, parents, children, history, promoted_as}."""
    pool: dict[str, dict[str, Any]] = {}
    for event in core.journal.replay(task_id):
        if event.event_type != "criterion.change_recorded" or not event.payload.get("pool"):
            continue
        change = event.payload
        entry = pool.setdefault(change["criterion_id"], {"criterion_id": change["criterion_id"], "version": 0,
                                                         "state": None, "item": None, "parents": [], "children": [],
                                                         "history": [], "promoted_as": None})
        entry["version"] = max(entry["version"], change["version"])
        entry["state"] = change["state"]
        if change.get("artifact_id"):
            entry["item"] = core.artifacts.payload(change["artifact_id"])
        if change["operation"] in REDUCTION_OPERATIONS and change["state"] == "merged_away":
            entry["children"] += change["targets_out"]
        elif change["operation"] in REDUCTION_OPERATIONS:
            entry["parents"] += change["targets_in"]
        if change.get("promoted_as"):
            entry["promoted_as"] = change["promoted_as"]
        entry["history"].append({k: change.get(k) for k in ("change_id", "version", "operation", "state", "reason_kind",
                                                           "reason_text", "stage", "iteration", "round_run_id")})
    return pool


def active(pool: dict[str, dict[str, Any]], states: tuple[str, ...] = ACTIVE_STATES) -> list[dict[str, Any]]:
    return sorted((e for e in pool.values() if e["state"] in states), key=lambda e: e["criterion_id"])


def pool_hash(pool: dict[str, dict[str, Any]]) -> str:
    return sha256_hex(sorted([e["criterion_id"], e["version"], e["state"]] for e in pool.values()))


class Pool:
    """Writes pool transitions for one stage context (run, round, stage, iteration)."""

    def __init__(self, core: Core, task_id: str, *, by: dict[str, Any], run_id: str):
        self.core, self.task_id, self.by, self.run_id = core, task_id, by, run_id
        self.context: dict[str, Any] = {"round_run_id": run_id, "stage": None, "iteration": 0}

    def at(self, stage: str, iteration: int) -> "Pool":
        self.context = {"round_run_id": self.run_id, "stage": stage, "iteration": iteration}
        return self

    def fold(self) -> dict[str, dict[str, Any]]:
        return fold(self.core, self.task_id)

    def add(self, item: dict[str, Any], *, reason_text: str = "", state: str = "candidate",
            reason_kind: str = "new_evidence") -> str:
        criterion_id = new_id("cri")
        _record(self.core, self.task_id, criterion_id=criterion_id, version=1, operation="add", state=state, by=self.by,
                context=self.context, reason_kind=reason_kind, reason_text=reason_text, item=item,
                targets_out=[_ref(criterion_id, 1)], source_refs=list(item.get("supporting_claim_ids") or []))
        return criterion_id

    def revise(self, entry: dict[str, Any], item: dict[str, Any], *, reason_text: str, state: str = "candidate",
               reason_kind: str = "refinement") -> int:
        version = entry["version"] + 1
        _record(self.core, self.task_id, criterion_id=entry["criterion_id"], version=version, operation="revise", state=state,
                by=self.by, context=self.context, reason_kind=reason_kind, reason_text=reason_text, item=item,
                targets_in=[_ref(entry["criterion_id"], entry["version"])],
                targets_out=[_ref(entry["criterion_id"], version)], source_refs=list(item.get("supporting_claim_ids") or []))
        entry["version"], entry["state"], entry["item"] = version, state, item
        return version

    def set_state(self, entry: dict[str, Any], state: str, *, operation: str, reason_kind: str, reason_text: str = "",
                  item: dict[str, Any] | None = None, extra: dict[str, Any] | None = None) -> None:
        """A state change. With `item` (e.g. findings attached) it is recorded as a new version."""
        version = entry["version"] + (1 if item is not None else 0)
        _record(self.core, self.task_id, criterion_id=entry["criterion_id"], version=version, operation=operation,
                state=state, by=self.by, context=self.context, reason_kind=reason_kind, reason_text=reason_text, item=item,
                targets_in=[_ref(entry["criterion_id"], entry["version"])],
                targets_out=[_ref(entry["criterion_id"], version)], extra=extra)
        entry["version"], entry["state"] = version, state
        if item is not None:
            entry["item"] = item

    def merge(self, parents: list[dict[str, Any]], item: dict[str, Any], *, reason_text: str,
              operation: str = "merge", reason_kind: str = "duplicate_merged") -> str:
        """Several parents into one child: one record per parent (`merged_away`, pointing at the child) and
        one for the child (pointing at its parents).

        `operation` and `reason_kind` are what distinguish the two reductions in the record. A reader of the
        trajectory sees `duplicate_merged` or `family_consolidated` in the per-stage reason counts, and a
        reader of one lineage's history sees `merge` or `consolidate` as the operation that retired it.
        """
        child = new_id("cri")
        parent_refs = [_ref(p["criterion_id"], p["version"]) for p in parents]
        for parent in parents:
            _record(self.core, self.task_id, criterion_id=parent["criterion_id"], version=parent["version"],
                    operation=operation, state="merged_away", by=self.by, context=self.context, reason_kind=reason_kind,
                    reason_text=reason_text, targets_in=[_ref(parent["criterion_id"], parent["version"])],
                    targets_out=[_ref(child, 1)])
            parent["state"] = "merged_away"
        _record(self.core, self.task_id, criterion_id=child, version=1, operation=operation, state="candidate",
                by=self.by, context=self.context, reason_kind=reason_kind, reason_text=reason_text, item=item,
                targets_in=parent_refs, targets_out=[_ref(child, 1)],
                source_refs=list(item.get("supporting_claim_ids") or []))
        return child

    def consolidate(self, members: list[dict[str, Any]], item: dict[str, Any], *, reason_text: str) -> str:
        """A family of distinct criteria into one that subsumes them. Lineage is the merge's, the claim is not:
        these members were never one quantity, so the record says `consolidate`, and `item["consolidation"]`
        carries the family it stands for."""
        return self.merge(members, item, reason_text=reason_text, operation="consolidate",
                          reason_kind="family_consolidated")


# WHY a trajectory report: the pool's whole point is that it grows, is pruned and is merged, and `fold` only
# shows where every lineage ended up. Reading the end state, a reviewer cannot tell whether 34 criteria are the
# survivors of 72 proposals or the only 34 ever written -- which is the difference between a pool and a list.
# This replays the same change records per (stage, iteration) so the sequence is on the record, not inferred.
STAGE_ORDER = ("propose", "filter", "distill", "refine", "merge", "promote")


def trajectory(core: Core, task_id: str) -> list[dict[str, Any]]:
    """Per (round, iteration, stage): what entered the pool, what left it, and the live count after."""
    steps: dict[tuple[str, int, str], dict[str, Any]] = {}
    live: set[str] = set()
    order: list[tuple[str, int, str]] = []
    for event in core.journal.replay(task_id):
        if event.event_type != "criterion.change_recorded" or not event.payload.get("pool"):
            continue
        change = event.payload
        stage = (change.get("stage") or "?").split(":")[0]
        key = (change.get("round_run_id") or "?", int(change.get("iteration") or 0), stage)
        if key not in steps:
            steps[key] = {"round_run_id": key[0], "iteration": key[1], "stage": stage, "added": 0, "revised": 0,
                          "merged_away": 0, "removed": 0, "reinstated": 0, "promoted": 0, "reasons": {}}
            order.append(key)
        step = steps[key]
        operation, state = change["operation"], change["state"]
        step["added" if operation == "add" else
             "merged_away" if state == "merged_away" else
             "removed" if state in ("withdrawn", "filtered_out") else
             "promoted" if state == "promoted" else
             "reinstated" if operation == "reinstate" else "revised"] += 1
        if change.get("reason_kind"):
            step["reasons"][change["reason_kind"]] = step["reasons"].get(change["reason_kind"], 0) + 1
        if state in ("withdrawn", "filtered_out", "merged_away"):
            live.discard(change["criterion_id"])
        else:
            live.add(change["criterion_id"])
        step["live_after"] = len(live)
    # `propose` and `promote` both carry iteration 0 but bracket the iterations, so they sort by phase first.
    phase = {"propose": -1, "promote": 1}
    return [steps[k] for k in sorted(order, key=lambda k: (k[0], phase.get(k[2], 0), k[1],
                                                           STAGE_ORDER.index(k[2]) if k[2] in STAGE_ORDER
                                                           else len(STAGE_ORDER)))]
