"""Public explanations must match the retained study, including unknown outcomes."""

import copy
import json
from collections import Counter
from pathlib import Path

import pytest

from mas.ui.decision_reading import criterion_disposition, eligibility_counts, eligibility_reading, selection_reading
from mas.core.assessor import qualification
from mas.ui.decision_reading import evidence_profile


RESULTS = Path(__file__).resolve().parents[1] / "examples/oral-multitarget/latest/results"


def test_profile_counts_applicable_mandatory_conditions_separately():
    profile = evidence_profile({"state": "qualified", "hard_total": 2, "applicable_hard_count": 1,
                                "hard_passed": 1, "required_direct_answered": 1, "required_total": 1})
    assert profile["state"] == "complete"
    assert profile["mandatory_met"] == profile["mandatory_total"] == 1


def test_saved_eligibility_reasons_partition_all_candidates_without_reclassifying():
    snapshot = json.loads((RESULTS / "snapshot.json").read_text(encoding="utf-8"))
    before = copy.deepcopy(snapshot)
    cqa = json.loads((RESULTS / "cqa.json").read_text(encoding="utf-8"))
    rules = {row["rule_ref"]: row for row in cqa["items"] if row.get("rule_ref")}
    readings = [eligibility_reading(entry, rules) for entry in snapshot["candidate_entries"]]
    summary = eligibility_counts(readings)
    assert summary["total"] == 3177
    assert summary["groups"] == {
        "requirements_met": 10, "mandatory_and_required_unresolved": 1899,
        "required_observations_unresolved": 1261, "mandatory_unresolved": 7,
    }
    assert sum(summary["groups"].values()) == 3177
    assert Counter(selection_reading(reading)["decision"] for reading in readings) == {"eligible": 10, "evidence_incomplete": 1305, "excluded": 1862}
    assert summary["profile_counts"] == {"complete": 10, "partial": 1305, "none": 1862, "unknown": 0, "failed": 0}
    assert eligibility_counts([reading for reading in readings if selection_reading(reading)["decision"] == "evidence_incomplete"])["profile_counts"] == {
        "complete": 0, "partial": 1305, "none": 0, "unknown": 0, "failed": 0}
    assert {selection_reading(reading)["policy"] for reading in readings} == {"selection_reporting_v3"}
    assert not any(selection_reading(reading)["confirmed_mandatory_failure"] for reading in readings)
    assert snapshot == before
    surufatinib = next(e for e in snapshot["candidate_entries"] if "Surufatinib" in e["identity_labels"])
    assert surufatinib["position"] == 1
    assert eligibility_reading(surufatinib, {})["reason_code"] == "requirements_met"


def test_saved_criteria_dispositions_explain_all_22_items_outside_evaluation():
    cqa = json.loads((RESULTS / "cqa.json").read_text(encoding="utf-8"))
    counts = Counter(criterion_disposition(row, row["evaluation"])["code"]
                     for row in cqa["items"] if row.get("current"))
    assert counts == {"mandatory_requirement": 1, "weighted_criterion": 17, "context_only": 13,
                      "comparison_incomplete": 9, "review_unresolved": 5,
                      "unit_mapping_unresolved": 1, "alternative_policy_unresolved": 5,
                      "proposal_not_finalized": 2}


def test_not_ready_conflict_and_confirmed_failure_have_distinct_explanations():
    entry = {"qualification": {"state": "not_ready", "blocking_hard_rule_refs": ["rule_size"]},
             "verdicts": {"attr_size": "unknown_conflicted"}}
    rules = {"rule_size": {"attribute_ref": "attr_size", "name": "Particle size"}}
    reading = eligibility_reading(entry, rules)
    assert reading["reason_code"] == "criteria_not_ready"
    assert reading["issues"][0]["issue"] == "conflicting_evidence"
    entry["qualification"] = {"state": "rejected", "failed_hard_rule_refs": ["rule_size"]}
    entry["verdicts"]["attr_size"] = "fail"
    assert eligibility_reading(entry, rules)["issues"][0]["issue"] == "confirmed_failure"
    assert eligibility_reading(entry, rules, legacy=True)["reason_code"] == "historical_policy"


def test_carrier_task_missing_evidence_and_confirmed_failure_are_distinct():
    """The same policy must work for a different object type and requirement names."""
    size = {"rule_ref": "rule_size", "verdict": "pass", "determination_basis": "measured",
            "value_source_claim_refs": ["claim_size"], "value_kind": "point"}
    q = qualification([size], hard_rule_refs=["rule_size"], verified_hard_rule_refs=["rule_size"],
                      required_rule_refs=["rule_release"])
    entry = {"qualification": q, "verdicts": {"attr_size": "pass", "attr_release": "unknown_missing"}}
    reading = eligibility_reading(entry, {"rule_release": {"attribute_ref": "attr_release", "name": "Release at pH 6.5"}})
    decision = selection_reading(reading)
    assert decision["decision"] == "evidence_incomplete" and not decision["confirmed_mandatory_failure"]
    assert reading["evidence_profile"] == {"state": "partial", "mandatory_met": 1, "mandatory_total": 1,
                                           "required_available": 0, "required_total": 1}
    assert q["hard_failed"] == 0 and reading["issues"][0]["name"] == "Release at pH 6.5"
    reading["issues"][0]["issue"] = "tool_error"
    assert selection_reading(reading)["decision"] == "incomplete"
    no_rules = eligibility_reading({"qualification": qualification([], hard_rule_refs=[], required_rule_refs=[],
                                     verified_hard_rule_refs=[])}, {})
    assert selection_reading(no_rules)["decision"] == "not_ready"
    size["verdict"] = "fail"
    rejected = qualification([size], hard_rule_refs=["rule_size"], verified_hard_rule_refs=["rule_size"],
                             required_rule_refs=["rule_release"])
    reading = eligibility_reading({"qualification": rejected, "verdicts": {"attr_size": "fail"}},
                                   {"rule_size": {"attribute_ref": "attr_size"}})
    assert selection_reading(reading)["decision"] == "excluded"
    assert selection_reading(reading)["confirmed_mandatory_failure"]
    assert reading["evidence_profile"]["state"] == "failed"
    # A new task's own requirements drive zero-support exclusion as well.
    rules = {"rule_size": {"attribute_ref": "attr_size", "name": "Particle size"},
             "rule_release": {"attribute_ref": "attr_release", "name": "Release at pH 6.5"}}
    empty = [{"rule_ref": ref, "verdict": "unknown_missing"} for ref in rules]
    q = qualification(empty, hard_rule_refs=["rule_size"], verified_hard_rule_refs=["rule_size"],
                      required_rule_refs=["rule_release"])
    reading = eligibility_reading({"qualification": q}, rules,
                                   rule_assessments={c["rule_ref"]: c for c in empty})
    selected = selection_reading(reading)
    assert selected["decision"] == "excluded" and selected["reason_code"] == "no_required_evidence"
    assert set(selected["requirement_refs"]) == set(rules)
    assert "Particle size" in selected["reason"] and "Release at pH 6.5" in selected["reason"]
    assert not selected["confirmed_mandatory_failure"]


def test_missing_profile_counts_remain_unknown_and_preference_failure_does_not_exclude():
    reading = eligibility_reading({"qualification": {"state": "qualified", "verified_hard_count": 3}}, {})
    assert reading["evidence_profile"] == {"state": "unknown", "mandatory_met": None, "mandatory_total": None,
                                           "required_available": None, "required_total": None}
    cells = [{"rule_ref": ref, "verdict": verdict, "determination_basis": "measured",
              "value_source_claim_refs": ["claim_" + ref], "value_kind": "measured"}
             for ref, verdict in (("size", "pass"), ("release", "fail"))]
    q = qualification(cells, hard_rule_refs=["size"], verified_hard_rule_refs=["size"], required_rule_refs=["release"])
    reading = eligibility_reading({"qualification": q, "verdicts": {"attr_release": "fail"}}, {})
    assert selection_reading(reading)["decision"] == "eligible"
    assert reading["evidence_profile"]["state"] == "complete"
    assert reading["evidence_profile"]["mandatory_total"] == reading["evidence_profile"]["required_total"] == 1


@pytest.mark.parametrize(("verdict", "extra", "decision", "issue"), [
    ("unknown_missing", {}, "evidence_incomplete", "no_usable_direct_evidence"),
    ("unknown_conflicted", {}, "evidence_incomplete", "conflicting_evidence"),
    ("unknown_unresolvable", {}, "evidence_incomplete", "interpretation_unresolved"),
    ("unknown_missing", {"tool_error_ref": "error_release"}, "incomplete", "tool_error"),
    ("not_assessed", {"not_assessed_reason": "budget_exhausted"}, "incomplete", "not_assessed"),
    (None, {}, "incomplete", "assessment_record_unavailable"),
])
def test_rule_assessment_distinguishes_execution_from_evidence_gap(verdict, extra, decision, issue):
    entry = {"qualification": {"state": "pending", "hard_total": 1, "hard_passed": 1,
                               "required_total": 1, "required_direct_answered": 0,
                               "missing_direct_required_rule_refs": ["release"]},
             "verdicts": {"attr_release": "pass"}}
    reading = eligibility_reading(entry, {"release": {"attribute_ref": "attr_release"}},
                                   rule_assessments={"release": {"verdict": verdict, **extra}})
    assert reading["issues"][0]["verdict"] == verdict
    assert reading["issues"][0]["issue"] == issue
    assert selection_reading(reading)["decision"] == decision
