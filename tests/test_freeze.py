"""Registering an experiment before it runs, and detecting that it did not run as registered."""

import pytest

from mas.core import criteria, freeze, task
from mas.core.journal import actor

OPERATOR = actor("human", "operator", "operator")
SPEC = {"objective_text": "Rank candidates", "mode": "conditional",
        "scope_entities": [{"entity_kind": "target", "identifier": "CHEMBL_T1", "label": "T1",
                           "role": "required"}],
        "constraints": [{"text": "oral administration", "kind": "route", "hardness": "hard"}],
        "candidate_universe": {"kind": "enumerated_set", "members": ["a", "b"]},
        "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True}}


def policy(**over):
    base = {"task_ref": "task_x@v1", "criteria_ref": "rules@v1", "primary_board": "lb_primary",
            "rank_endpoint": "ranked_only", "scoring_policy": {"estimator": "weighted_preference",
                                                               "coverage_floor": 0.5}}
    base.update(over)
    return base


def test_a_registration_without_the_fields_that_fix_the_endpoint_is_refused(core):
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    for field in ("primary_board", "rank_endpoint", "scoring_policy", "criteria_ref"):
        incomplete = policy(); incomplete.pop(field)
        with pytest.raises(freeze.FreezeError, match="does not fix what the result is"):
            freeze.register(core, task_id, by=OPERATOR, policy=incomplete)


def test_a_registration_naming_a_field_nothing_reads_is_refused(core):
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    with pytest.raises(freeze.FreezeError, match="unknown policy fields"):
        freeze.register(core, task_id, by=OPERATOR, policy=policy(lucky_number=7))


def test_a_rule_set_may_call_itself_prespecified_on_a_registration_that_resolves(core):
    """The point of the module: `confirm_rule_set` would emit `prespecified` on any string, so the
    label rested on a caller's say-so. A reference it can resolve is what makes the claim checkable."""
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    ref = freeze.register(core, task_id, by=OPERATOR, policy=policy())
    assert core.artifacts.payload(ref)["policy"]["rank_endpoint"] == "ranked_only"
    assert [r["artifact_id"] for r in freeze.registrations(core, task_id)] == [ref]


def test_a_run_that_changed_a_registered_policy_is_reported_as_drift_not_tolerated(core):
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    ref = freeze.register(core, task_id, by=OPERATOR, policy=policy())

    conforming = freeze.verify(core, ref, actual={"rank_endpoint": "ranked_only"})
    assert conforming["conforms"] and conforming["drift"] == []

    # a coverage floor moved after the fact is exactly the change a one-shot result must not absorb
    drifted = freeze.verify(core, ref, actual={
        "scoring_policy": {"estimator": "weighted_preference", "coverage_floor": 0.3}})
    assert not drifted["conforms"]
    assert [d["field"] for d in drifted["drift"]] == ["scoring_policy"]
    assert drifted["drift"][0]["registered"]["coverage_floor"] == 0.5


def test_verifying_against_a_registration_that_does_not_resolve_is_refused(core):
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    with pytest.raises(freeze.FreezeError, match="does not resolve"):
        freeze.verify(core, "proto_imaginary", actual={"rank_endpoint": "ranked_only"})


def test_captured_artifacts_are_bound_separately_from_the_policy_they_cannot_change(core):
    """A manifest cannot hash evidence that has not been retrieved, so the binding comes second --
    and it is its own artifact pointing at the registration, never an amendment of it."""
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    ref = freeze.register(core, task_id, by=OPERATOR, policy=policy())
    before = core.artifacts.payload(ref)["policy_digest"]
    binding = freeze.bind_artifacts(core, task_id, ref, by=OPERATOR,
                                    captured={"candidate_set_hash": "abc", "evidence_snapshot": "evs_1"})
    assert core.artifacts.payload(binding)["preregistration_ref"] == ref
    assert core.artifacts.payload(ref)["policy_digest"] == before, "binding must not alter the policy"


def test_binding_before_anything_is_registered_is_refused(core):
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    with pytest.raises(freeze.FreezeError, match="no registration"):
        freeze.bind_artifacts(core, task_id, "proto_x", by=OPERATOR, captured={})
