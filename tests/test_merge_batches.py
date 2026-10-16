"""Bound merge requests without changing groups or losing paid batch outcomes."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from mas.core import derivation_stages as stages, pool
from mas.core.models import ModelError
from test_criteria_pool import CHEMBL_POTENCY, GTOPDB_AFFINITY, merge_script, pool_of


def group_pool(core, script, count=9):
    items = []
    for group in range(count):
        for member in range(2):
            attribute = deepcopy(CHEMBL_POTENCY if member == 0 else GTOPDB_AFFINITY)
            attribute["evidence_request"]["parameters"]["target_chembl_id"] = f"CHEMBL_SYNTHETIC_{group}"
            items.append((f"claim_{group}_{member}", deepcopy(attribute)))
    return pool_of(core, script, items, task_id="task_merge_batches", run_id="run_merge_batches")


def offered(request):
    return json.loads(request.messages[0]["content"].split("Groups:\n", 1)[1].split("\n\nCited claims:", 1)[0])


def test_merge_batches_preserve_groups_and_global_ids(core):
    seen = []
    def script(request):
        groups = offered(request)
        seen.append(groups)
        return {"decisions": [{"group": group["group"], "action": "keep_separate", "reason": "Distinct decision semantics"}
                              for group in groups]}
    ctx = group_pool(core, script)
    original = [[entry["criterion_id"] for entry in group] for group in stages.merge_groups(ctx.active())]
    result = stages.merge_stage(ctx, 1)
    assert [len(batch) for batch in seen] == [4, 4, 1]
    assert [request.metadata["question"] for request in ctx.roster.adapter("adjudicator").requests] == [
        "adjudicate merges (batch 1/3)", "adjudicate merges (batch 2/3)", "adjudicate merges (batch 3/3)"]
    assert [group["group"] for batch in seen for group in batch] == list(range(9))
    assert [[member["refs"]["pool_ref"].split("@v")[0] for member in group["members"]] for batch in seen for group in batch] == original
    assert result["groups"] == result["kept_separate"] == 9 and result["batches"] == 3
    assert len(ctx.adjudicated) == 9 and len(pool.active(pool.fold(core, ctx.task_id))) == 18


@pytest.mark.parametrize("reply", [{"decisions": []}, {"decisions": [
    {"group": 0, "action": "keep_separate", "reason": "One"},
    {"group": 0, "action": "keep_separate", "reason": "Two"}]}])
def test_missing_or_ambiguous_decisions_remain_unresolved_and_can_be_retried(core, reply):
    ctx = group_pool(core, lambda request: reply, count=1)
    result = stages.merge_stage(ctx, 1)
    assert result["unresolved"] == 1 and not ctx.adjudicated
    assert result["merged"] == result["kept_separate"] == 0
    assert result["not_reduced"][0]["outcome"] == "unresolved"


def test_a_later_budget_boundary_keeps_already_applied_merges(core):
    calls = []
    merge = merge_script()
    def script(request):
        calls.append(offered(request))
        if len(calls) == 2:
            raise ModelError("quota_exhausted", "Synthetic later batch cap")
        return merge(replace(request, metadata={**request.metadata, "question": "adjudicate merges"}))
    ctx = group_pool(core, script, count=5)
    with pytest.raises(ModelError, match="quota_exhausted"):
        stages.merge_stage(ctx, 1)
    states = [entry["state"] for entry in pool.fold(core, ctx.task_id).values()]
    assert states.count("merged_away") == 8  # Four complete two-parent groups, already persisted.
    assert states.count("candidate") == 6  # Four children and the untouched final two parents.
    assert len(ctx.adjudicated) == 4


def test_failed_batch_is_unresolved_and_other_complete_batches_are_retained(core):
    calls = []
    def script(request):
        groups = offered(request)
        calls.append(groups)
        if len(calls) == 1:
            raise ModelError("transient_network", "Synthetic first batch failure")
        return {"decisions": [{"group": group["group"], "action": "keep_separate", "reason": "Independent endpoints"}
                              for group in groups]}
    ctx = group_pool(core, script, count=5)
    result = stages.merge_stage(ctx, 1)
    assert result["unresolved"] == 4 and result["batches_unresolved"] == 1
    assert result["kept_separate"] == 1 and len(ctx.adjudicated) == 1
    assert len(pool.active(pool.fold(core, ctx.task_id))) == 10
