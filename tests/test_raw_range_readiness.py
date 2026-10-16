"""A raw window cannot become a scalar threshold through approval or prose."""
from mas.core import assessor, criteria, review, task
from test_preference_execution_guard import OPERATOR, QUANT, ORDER, SPEC


def test_raw_nonmonotonic_preference_is_deferred_even_after_explicit_approval(core):
    tid, _ = task.record_version(core, SPEC, by=OPERATOR)
    attribute = dict(QUANT, name="Synthetic raw window", unit="log units", direction="within_range",
        definition="Prefer the declared window; a one-sided scalar test does not implement it.",
        acceptable_determination_bases=["derived"])
    rule = {"rule_kind":"preference", "predicate_form":"range_membership", "cutoff_basis":"expert_set",
            "cutoff":{"comparator":">=", "value":2, "unit":"log units"}}
    ar, rr = criteria.propose(core, tid, attribute, rule, by=OPERATOR)
    for item in review.items(core, [tid]).values():
        review.decide(core, item, decision="approve", actor=OPERATOR,
            reason_text="Synthetic authority cannot add an undeclared range operation", entry="interactive")
    _, control = criteria.propose(core, tid, dict(QUANT, name="Synthetic monotonic control"), ORDER, by=OPERATOR)
    attr, predicate = criteria.load(core, ar, tid), criteria.load(core, rr, tid)
    cells = {}
    for label, raw in (("synthetic_below",1), ("synthetic_inside",3), ("synthetic_above",6)):
        cell, _ = assessor.assess_cell(candidate={"candidate_id":label}, attribute=attr, rule=predicate,
            rule_set_ref="rules@synthetic", resolved=True, qualification_policy="qualification_first_v1",
            claims=[{"claim_id":"claim_"+label, "source_ref":"src_synthetic", "admission_state":"admitted",
                     "evidence_kind":"database_entry", "determination_basis":"derived", "value":raw,"unit":"log units"}])
        cells[label] = [cell]
    scores = assessor.preference_scores(cells, {rr:{"rule_kind":"preference", "predicate_form":"range_membership",
        "direction":"within_range"}}, {}, qualified_candidates=set(cells), qualification_policy="qualification_first_v1")
    assert scores["synthetic_inside"] == scores["synthetic_above"] == (1.0,1.0)
    assert scores["synthetic_below"] == (0.0,1.0)
    assert "raw values" in criteria.preference_execution_problems(attr, predicate)[0]
    selected = criteria.rule_set(core, tid, criteria.confirm_rule_set(core, tid, by=OPERATOR, allow_pending=True))
    assert {row["rule_ref"] for row in selected["entries"]} == {control}
    deferred = next(row for row in selected["deferred"] if row["rule_ref"] == rr)
    assert deferred["reason_kind"] == "non_executable_preference"
    assert criteria.load(core, ar, tid) == attr and criteria.load(core, rr, tid) == predicate
    assert criteria.preference_execution_problems(dict(attr,direction="higher_better"),predicate) == []
    assert criteria.preference_execution_problems(attr,dict(predicate,rule_kind="hard_exclusion")) == []
    point = dict(predicate,predicate_form="threshold",cutoff={"comparator":"==","value":2,"unit":"log units"})
    assert criteria.preference_execution_problems(dict(attr,direction="target_value"),point) == []
    distance = dict(attr,direction="lower_better",value_transform={"kind":"distance_outside_band","low":2,"high":4,
        "basis":"source_stated_value","source_refs":["claim_bounds"]})
    assert criteria.preference_execution_problems(distance,ORDER) == []
