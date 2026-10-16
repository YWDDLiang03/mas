"""Prospective preference execution guard. Synthetic temporary stores; no model/network."""
import json
import pytest

from mas.adapters.drug.registration import EVIDENCE_CATALOG
from mas.adapters.drug.universe import UniverseRecordField
from mas.core import assessor, criteria, criteria_export, ledger, measurement, review, task
from mas.core.journal import actor

OPERATOR = actor("human", "synthetic-guard-operator", "operator", identity_basis="recorded_attestation")
SPEC = {"objective_text": "Synthetic preference execution check", "mode": "exploratory", "scope_entities": [],
        "candidate_universe": {"kind": "enumerated_set", "members": ["synthetic"]}, "constraints": [],
        "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True}}
CAT = {"name": "Synthetic engagement on record", "definition": "A curated statement of target engagement",
       "measurement_kind": "categorical", "unit": None, "direction": "non_directional",
       "acceptable_value_sources": ["database_entry"], "acceptable_determination_bases": ["curated"],
       "aggregation": "consensus", "evidence_request": {"capability": "interaction_evidence_lookup",
       "question_kind": "mechanism_records", "parameters": {"target_chembl_id": "SYNTH_TARGET"}}}
QUANT = {"name": "Synthetic molecular weight", "definition": "Molecular weight of the candidate",
         "measurement_kind": "quantitative", "unit": "g/mol", "direction": "lower_better",
         "acceptable_value_sources": ["database_entry"], "aggregation": "median",
         "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                              "parameters": {"property": "MolecularWeight"}}}
NONE = {"rule_kind": "preference", "cutoff": None, "cutoff_basis": "none_evidence_insufficient"}
ORDER = dict(NONE, predicate_form="ordering")


def test_non_executable_preferences_remain_active_and_deferred_without_changing_hard_pending(core):
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    pairs = []
    for attribute, rule in ((CAT, NONE),
                            (dict(QUANT, name="Unordered numeric preference", direction="non_directional"), ORDER),
                            (dict(CAT, name="Categorical ordering without a direction"), ORDER),
                            (QUANT, ORDER),
                            (dict(QUANT, name="Unresolved hard condition"), {"rule_kind": "hard_exclusion",
                             "cutoff": {"comparator": "<=", "value": 500, "unit": "g/mol"}, "cutoff_basis": "expert_set"})):
        pairs.append(criteria.propose(core, task_id, attribute, rule, by=OPERATOR))
    before = {ref: criteria.load(core, ref, task_id) for pair in pairs for ref in pair}
    queue = review.items(core, [task_id])
    with pytest.raises(criteria.InvariantViolation, match="await an expert decision"):
        criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    selected_ref = criteria.confirm_rule_set(core, task_id, by=OPERATOR, allow_pending=True)
    selected = criteria.rule_set(core, task_id, selected_ref)
    assert {row["rule_ref"] for row in selected["entries"]} == {pairs[3][1]}
    assert {row["rule_ref"] for row in selected["deferred"]} == {pair[1] for pair in pairs[:3]}
    assert all(row["reason_kind"] == "non_executable_preference" and row["scope"] == "rule" and row["problems"]
               for row in selected["deferred"])
    assert pairs[-1][1] in selected["pending"] and review.items(core, [task_id]) == queue
    assert criteria.registry_inventory(core, task_id)["active_registered_count"] == 5
    assert criteria.registry_inventory(core, task_id)["scoring_in_latest_frozen_set_count"] == 1
    assert criteria.deferred_capabilities(selected) == ()
    assert criteria.preference_execution_findings(core, task_id, rule_set=selected) == []
    for pair in pairs:
        for ref in pair:
            assert criteria.load(core, ref, task_id) == before[ref]
    for attr_ref, rule_ref in pairs[:3]:
        exported = criteria_export._use(rule_ref, attr_ref, [selected], None)
        assert exported["status"] == "deferred" and exported["reason"]
    profile = measurement.register(core, task_id, by=OPERATOR, rule_set_ref=selected_ref,
        primary_board="Synthetic execution guard", rationale="Mechanical scoring readiness",
        expected_effect="Do not count non-executable preferences")
    assert measurement.load(core, task_id, profile)["policy"]["scoring_policy"]["scoring_rule_refs"] == sorted(
        [pairs[3][1]])
    # allow_pending did not remove the unresolved hard constraint from the record.
    with pytest.raises(criteria.InvariantViolation, match="await an expert decision"):
        criteria.confirm_rule_set(core, task_id, by=OPERATOR)


def test_valid_numeric_ordering_and_declared_boolean_comparison_remain_executable():
    assert criteria.preference_execution_problems(QUANT, ORDER) == []
    boolean = dict(NONE, predicate_form="categorical_membership", cutoff_basis="task_constraint",
                   cutoff={"comparator": "==", "value": True})
    assert criteria.preference_execution_problems(CAT, boolean) == []
    assert criteria.preference_execution_problems(CAT, dict(NONE, rule_kind="hard_exclusion")) == []
    attribute = dict(QUANT, attribute_id="attr_synthetic", version=1)
    rule = dict(ORDER, rule_id="rule_synthetic", version=1)
    observed = {"claim_id": "claim_synthetic", "source_ref": "src_synthetic", "admission_state": "admitted",
                "evidence_kind": "database_entry", "determination_basis": "derived", "value": 300, "unit": "g/mol"}
    cell, _ = assessor.assess_cell(candidate={"candidate_id": "synthetic"}, attribute=attribute, rule=rule,
        rule_set_ref="rules@v1", claims=[observed], resolved=True, qualification_policy="qualification_first_v1")
    assert cell["verdict"] == "available" and cell["value"] == 300


@pytest.mark.parametrize("kind,unit", [("categorical", "phase"), ("ordinal", None)])
def test_existing_numeric_phase_and_unitless_ordinal_ordering_are_preserved(core, tmp_path, kind, unit):
    entry = next(row for row in EVIDENCE_CATALOG if row["question_kind"] == "record_field")
    assert entry["units"]["max_phase"] == "phase"
    path = tmp_path / "synthetic_universe.json"
    path.write_text(json.dumps({"source": "synthetic phase fixture", "universe": [
        {"inchikey": "SYNTH_A", "chembl_id": "SYNTH_CHEMBL_A", "max_phase": 2},
        {"inchikey": "SYNTH_B", "chembl_id": "SYNTH_CHEMBL_B", "max_phase": 4}]}))
    provider = UniverseRecordField(path)
    attribute = dict(CAT, name=f"Synthetic phase encoded as {kind}", measurement_kind=kind,
        unit=unit, direction="higher_better", acceptable_determination_bases=["measured"],
        evidence_request={"capability": "record_field_lookup", "question_kind": "record_field",
                          "parameters": {"field": "max_phase"}})
    assert criteria.preference_execution_problems(attribute, ORDER) == []
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    attr_ref, rule_ref = criteria.propose(core, task_id, attribute, ORDER, by=OPERATOR)
    selected_ref = criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    selected = criteria.rule_set(core, task_id, selected_ref)
    assert [row["rule_ref"] for row in selected["entries"]] == [rule_ref] and selected["deferred"] == []
    cells = {}
    for key in ("SYNTH_A", "SYNTH_B"):
        response = provider.invoke("record_field", {"identifier": key, "field": "max_phase"})
        observed = response.values[0]
        claim = dict(claim_id=f"claim_{key}", source_ref="src_synthetic_phase", candidate_ref=key,
                     evidence_kind="database_entry", determination_basis="measured", value=observed["value"],
                     unit=observed["unit"], reading_depth="not_read",
                     location={"location_kind": "database_record", "locator_value": f"{key}:max_phase"})
        ledger.record_claim(core, task_id, claim, by=OPERATOR, admission_state="admitted",
                            admission_reasons=["synthetic local fixture"])
        cell, _ = assessor.assess_cell(candidate={"candidate_id": key},
            attribute=criteria.load(core, attr_ref, task_id), rule=criteria.load(core, rule_ref, task_id),
            rule_set_ref=selected_ref, claims=[dict(claim, admission_state="admitted")], resolved=True,
            qualification_policy="qualification_first_v1")
        assert cell["verdict"] == "available" and cell["value"] == observed["value"]
        cells[key] = [cell]
    scores = assessor.preference_scores(cells, {rule_ref: {"rule_kind": "preference", "predicate_form": "ordering",
        "direction": "higher_better"}}, {}, qualified_candidates=set(cells), qualification_policy="qualification_first_v1")
    assert scores == {"SYNTH_A": (0.0, 1.0), "SYNTH_B": (1.0, 1.0)}
