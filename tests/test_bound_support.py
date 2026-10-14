"""Bound support and the authority it implies (core/bound_support.py): findings F2, F3 and F4.

Every number a candidate is compared against -- a rule cutoff, a bound inside a `value_transform` --
is a separately supported parameter (handoff §5.4). The three defects these tests pin were measured
on the checkout of 14 October 2026:

  F2  `derivation.validate_proposal` accepted a `source_stated_value` cutoff of 90 whose cited claim
      stated 30: it established that a cited claim carried a number, never that it carried this one.
  F3  `criteria.needs_expert` read the rule's kind and its cutoff basis, so an ordering preference
      whose transform bound carried `basis: expert_set` was registered with zero review items and
      entered a confirmed set with `auto:trigger_table` authority.
  F4  `adjudication._apply_revision` applied `>= 30` -> `>= 90` with no refusal.

The fixtures are the synthetic cases of the handoff plus the two the live registry actually holds:
the molecular-weight bound 500, whose quote states the range "approximately 380-500 Da", and the
lipophilicity band 2 to 4, whose quote states the whole window the transform uses. Scripted models;
no network; no store but the temporary one each test opens.
"""

from __future__ import annotations

import pytest

from mas.core import adjudication, assessor, bound_support, collapse as collapse_mod, criteria, derivation
from mas.core import ledger, review, task
from mas.core.journal import actor
from mas.core.runtime import Core

OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")
AGENT = actor("agent", "proposer-1", "proposer")

SPEC = {
    "objective_text": "Prioritize oral kinase inhibitors for target T1", "mode": "conditional",
    "scope_entities": [{"entity_kind": "target", "identifier": "CHEMBL_T1", "label": "T1", "role": "required"}],
    "candidate_universe": {"kind": "enumerated_set", "members": ["alpha", "beta"]},
    "constraints": [{"text": "oral administration", "kind": "route", "hardness": "hard", "provenance": "manuscript"}],
    "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True},
}
CATALOG = [{"capability": "literature_retrieval", "question_kind": "search", "identifier_scheme": "inchikey",
            "evidence_kind": "peer_reviewed"},
           {"capability": "property_estimate", "question_kind": "computed_property", "identifier_scheme": "inchikey",
            "evidence_kind": "database_entry", "determination_basis": "derived"}]

BIOAVAILABILITY = {"name": "Oral bioavailability", "definition": "Fraction of an oral dose reaching circulation",
                   "measurement_kind": "quantitative", "unit": "%", "direction": "higher_better",
                   "acceptable_value_sources": ["peer_reviewed"], "aggregation": "median",
                   "evidence_request": {"capability": "literature_retrieval", "question_kind": "search",
                                        "parameters": {"query_template": "({names}) AND bioavailability"}},
                   "rationale": "the task constrains the route to oral"}
THRESHOLD_RULE = {"rule_kind": "preference", "predicate_form": "threshold", "cutoff_basis": "source_stated_value",
                  "cutoff": {"comparator": ">=", "value": 30, "unit": "%"}}
MOLECULAR_WEIGHT = {"name": "Molecular weight in excess of the upper bound",
                    "definition": "the excess in g/mol above 500, zero at or below it",
                    "measurement_kind": "quantitative", "unit": "g/mol", "direction": "lower_better",
                    "acceptable_value_sources": ["database_entry"], "acceptable_determination_bases": ["derived"],
                    "aggregation": "median",
                    "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                                         "parameters": {"property": "MolecularWeight"}},
                    "rationale": "passive diffusion falls off with size"}
ORDERING_RULE = {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
                 "cutoff_basis": "none_evidence_insufficient"}
# The live manuscript claim, quoted as the store holds it: the number 500 is in the passage and the
# passage states a range of observed practice around it.
MW_QUOTE = ("Most clinically relevant kinase inhibitors typically fall within the range of approximately "
            "380-500 Da, which is considered close to the upper limit compatible with efficient passive diffusion")
F_QUOTE = "absolute oral bioavailability above 30% achieved adequate exposure"


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c


def _task(core) -> str:
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    return task_id


def claim(core, stream_id: str, *, claim_id: str, quote: str, value=None, unit=None, low=None, high=None,
          basis: str = "measured") -> str:
    return ledger.record_claim(core, stream_id, {
        "claim_id": claim_id, "source_ref": "src_doi_10.1-a",
        "location": {"location_kind": "paragraph", "locator_value": "sec1.p1", "section_path": ["Results"],
                     "quoted_span": quote, "span_checked_against_source": True},
        "claim_text": quote, "claim_text_marker": "paraphrase", "normalized_statement": quote,
        "claim_type": "literature_extracted", "evidence_kind": "peer_reviewed", "determination_basis": basis,
        "value": value, "value_low": low, "value_high": high, "unit": unit, "polarity": "supports",
        "scope_match": "direct", "reading_depth": "full_text"},
        by=AGENT, admission_state="admitted", admission_reasons=["quote_verified", "value_in_quote"])


def record(path: str, *, claim_id: str, number, unit, statement_kind: str, conversion=None) -> dict:
    return {"parameter_path": path, "claim_id": claim_id, "source_number": number, "source_unit": unit,
            "statement_kind": statement_kind, "conversion": conversion or {"kind": "identity"},
            "applicability_rationale": "the passage is about orally dosed small-molecule kinase inhibitors, "
                                       "which is this task's candidate population"}


def validate(proposal: dict, claims: list[dict]) -> list[str]:
    return derivation.validate_proposal(proposal, claims_by_id={c["claim_id"]: c for c in claims},
                                        reference_labels=[], catalog=CATALOG)


# --- F2: a cited claim carrying a number is not support for a particular number -------------------

def test_a_cutoff_of_ninety_citing_a_claim_that_states_thirty_is_refused_as_an_unsupported_bound(core):
    """The measured F2 defect, on the synthetic case the handoff states it with. The old validator
    asked whether any cited claim carried a value at all, so 90 passed on a claim stating 30."""
    task_id = _task(core)
    stated_thirty = claim(core, task_id, claim_id="claim_f30", quote=F_QUOTE, value=30, unit="%")
    claims = [ledger.claims(core, [task_id])[0]]
    assert claims[0]["claim_id"] == stated_thirty

    substituted = {"attribute": BIOAVAILABILITY, "supporting_claim_ids": [stated_thirty],
                   "rule": dict(THRESHOLD_RULE, cutoff={"comparator": ">=", "value": 90, "unit": "%"}),
                   "expected_change": "ranks exposed compounds higher", "falsification_test": "ranking unchanged"}
    problems = validate(substituted, claims)
    assert any("bound_support_mismatch" in p and "rule.cutoff.value" in p for p in problems), problems
    assert any("none of the 1 cited claims states that number" in p for p in problems), problems

    honest = dict(substituted, rule=THRESHOLD_RULE)
    assert validate(honest, claims) == []

    report = bound_support.validate(BIOAVAILABILITY, substituted["rule"], claims=claims)
    assert report["states"] == {"rule.cutoff.value": "unsupported"}
    assert report["unsupported_paths"] == ["rule.cutoff.value"]


def test_a_bound_reached_by_a_declared_unit_conversion_passes_and_a_wrong_conversion_does_not(core):
    """The arithmetic is the machine's part: given the number a passage states, the declared
    conversion must produce the executable parameter, and the unit it converts to must be the
    parameter's own."""
    task_id = _task(core)
    grams = claim(core, task_id, claim_id="claim_sol", quote="an aqueous solubility of 0.5 g/L was required",
                  value=0.5, unit="g/L", basis="asserted")
    claims = ledger.claims(core, [task_id])
    attribute = dict(BIOAVAILABILITY, name="Aqueous solubility", unit="mg/L", definition="solubility in water",
                     acceptable_value_sources=["peer_reviewed"])
    rule = dict(THRESHOLD_RULE, cutoff={"comparator": ">=", "value": 500, "unit": "mg/L"},
                bound_support=[record("rule.cutoff.value", claim_id=grams, number=0.5, unit="g/L",
                                      statement_kind="states_decision_threshold",
                                      conversion={"kind": "unit_conversion", "factor": 1000,
                                                  "from_unit": "g/L", "to_unit": "mg/L"})])
    proposal = {"attribute": attribute, "rule": rule, "supporting_claim_ids": [grams],
                "expected_change": "ranks soluble compounds higher", "falsification_test": "ranking unchanged"}
    assert validate(proposal, claims) == []
    report = bound_support.validate(attribute, rule, claims=claims)
    (bound,) = report["bounds"]
    assert (bound["quote"], bound["arithmetic"], bound["semantic_support"]) == (
        "pass", "pass", "states_decision_threshold")
    assert bound["state"] == "sourced_threshold" and bound["authority"] == "source_stated"
    assert criteria.authority_requirements(rule, attribute, support=report) == []

    wrong_factor = dict(rule, bound_support=[dict(rule["bound_support"][0],
                                                  conversion={"kind": "unit_conversion", "factor": 100,
                                                              "from_unit": "g/L", "to_unit": "mg/L"})])
    assert any("produces 50.0, while the executable parameter is 500" in p
               for p in validate(dict(proposal, rule=wrong_factor), claims))
    wrong_unit = dict(rule, bound_support=[dict(rule["bound_support"][0],
                                                conversion={"kind": "unit_conversion", "factor": 1000,
                                                            "from_unit": "g/L", "to_unit": "ug/L"})])
    assert any("converts to 'ug/L' while the parameter is in 'mg/L'" in p
               for p in validate(dict(proposal, rule=wrong_unit), claims))


def test_a_quoted_measurement_does_not_become_a_decision_threshold_by_being_declared_one(core):
    """A record may declare what the passage is doing with its number; it may not declare away what
    the reader -- holding that passage, under `reading.CLAIM_SCHEMA` -- recorded it as doing."""
    task_id = _task(core)
    measured = claim(core, task_id, claim_id="claim_f30", quote=F_QUOTE, value=30, unit="%", basis="measured")
    claims = ledger.claims(core, [task_id])
    rule = dict(THRESHOLD_RULE, bound_support=[record("rule.cutoff.value", claim_id=measured, number=30, unit="%",
                                                      statement_kind="states_decision_threshold")])
    report = bound_support.validate(BIOAVAILABILITY, rule, claims=claims)
    (bound,) = report["bounds"]
    assert bound["quote"] == "pass" and bound["arithmetic"] == "pass"
    assert bound["semantic_support"] == "reports_measurement" and bound["state"] == "interpretation_added"
    assert bound["authority"] == "decision_required"
    assert [f["severity"] for f in report["findings"]] == ["material"]       # recorded, not a schema refusal
    assert criteria.needs_expert(rule, BIOAVAILABILITY, support=report) is True

    honest = dict(THRESHOLD_RULE, bound_support=[record("rule.cutoff.value", claim_id=measured, number=30, unit="%",
                                                        statement_kind="reports_measurement")])
    honest_report = bound_support.validate(BIOAVAILABILITY, honest, claims=claims)
    assert honest_report["states"] == {"rule.cutoff.value": "interpretation_added"}
    assert [r["reason"] for r in criteria.authority_requirements(honest, BIOAVAILABILITY, support=honest_report)] \
        == ["bound_interpretation_added"]


def test_the_live_molecular_weight_bound_of_five_hundred_is_one_end_of_a_stated_range_and_needs_a_decision(core):
    """The real case, quoted as the store holds it, and it is the calibration case for §5.4.

    500 is in the passage, so the quote check passes and the arithmetic is an identity. What the
    passage states is the range "approximately 380-500 Da" -- observed practice, with 500 described
    as close to an upper limit, not proposed as a screening cutoff. A one-sided bound at one end of
    a stated range is a line the criterion draws, so the bound is recorded as `interpretation_added`
    and cannot score on the trigger table's authority alone, whatever the record declares.
    """
    task_id = _task(core)
    ranged = claim(core, task_id, claim_id="claim_mw", quote=MW_QUOTE, low=380, high=500, unit="g/mol")
    claims = ledger.claims(core, [task_id])
    attribute = dict(MOLECULAR_WEIGHT, value_transform={"kind": "excess_above", "bound": 500,
                                                        "basis": "source_stated_value", "source_refs": [ranged]},
                     supporting_claim_refs=[ranged],
                     bound_support=[record("attribute.value_transform.bound", claim_id=ranged, number=500,
                                           unit="Da", statement_kind="states_decision_threshold")])
    report = bound_support.validate(attribute, ORDERING_RULE, claims=claims)
    (bound,) = report["bounds"]
    assert bound["parameter_path"] == "attribute.value_transform.bound"
    assert bound["quote"] == "pass" and bound["arithmetic"] == "pass"       # Da and g/mol are one unit
    assert bound["trace"] == [{"claim_id": ranged, "states_it": "claim_range_end"}]
    assert bound["range_endpoint"] == {"claim_id": ranged, "range": [380.0, 500.0], "endpoint": 500.0}
    assert bound["semantic_support"] == "reports_measurement" and bound["state"] == "interpretation_added"
    assert any("one end of it" in f["message"] for f in report["findings"])
    assert criteria.needs_expert(ORDERING_RULE, attribute, support=report) is True

    # and the honest declaration reaches the same place by the shorter road
    declared = dict(attribute, bound_support=[record("attribute.value_transform.bound", claim_id=ranged,
                                                     number=500, unit="Da", statement_kind="reports_measurement")])
    assert bound_support.validate(declared, ORDERING_RULE, claims=claims)["states"] == {
        "attribute.value_transform.bound": "interpretation_added"}


def test_an_undeclared_bound_that_is_one_end_of_a_stated_range_says_so_on_the_rule_set_entry(core):
    """The live molecular-weight position, as a confirmed set reports it: nothing declares what the
    passage does with 500, so the state is `interpretation_undeclared` -- and the entry says the only
    trace for the number is one end of the range the claim records, which is what a reviewer needs to
    see. Marked, not refused: absent metadata is unknown, and §9.2 asks that it not be given a
    status in either direction."""
    task_id = _task(core)
    ranged = claim(core, task_id, claim_id="claim_mw", quote=MW_QUOTE, low=380, high=500, unit="g/mol")
    attribute = dict(MOLECULAR_WEIGHT, supporting_claim_refs=[ranged],
                     value_transform={"kind": "excess_above", "bound": 500, "basis": "source_stated_value",
                                      "source_refs": [ranged]})
    criteria.propose(core, task_id, attribute, ORDERING_RULE, by=AGENT)
    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    (entry,) = rules["entries"]
    assert entry["confirmed_by"] == "auto:trigger_table"            # it still scores, as it does today
    assert entry["bound_support"]["states"] == {"attribute.value_transform.bound": "interpretation_undeclared"}
    assert entry["bound_support"]["traces"] == {"attribute.value_transform.bound": "claim_range_end"}
    assert entry["bound_support"]["range_endpoints"] == ["attribute.value_transform.bound"]
    report = bound_support.validate(attribute, ORDERING_RULE, claims=ledger.claims(core, [task_id]))
    assert [f["severity"] for f in report["findings"]] == ["material"]
    assert "one end of the range 380.0 to 500.0" in report["findings"][0]["message"]
    # and the gate a sourced or frozen set confirms with holds it out
    with pytest.raises(criteria.InvariantViolation, match="held out over bound support"):
        criteria.confirm_rule_set(core, task_id, by=OPERATOR, require_bound_support=True)


def test_a_band_that_uses_the_whole_stated_range_restates_it_rather_than_drawing_a_line_in_it(core):
    """The counterpart the calibration has to get right, and it is also a live attribute: the
    lipophilicity band's low and high are the range's own ends, so the transform carries the window
    the passage states instead of one end of it."""
    task_id = _task(core)
    window = claim(core, task_id, claim_id="claim_lp", unit="log units", low=2, high=4,
                   quote="oral drugs cluster in a lipophilicity window of 2 to 4 log units", basis="asserted")
    claims = ledger.claims(core, [task_id])
    attribute = dict(MOLECULAR_WEIGHT, name="Distance outside the lipophilicity band", unit="log units",
                     definition="the distance outside the 2 to 4 band, zero inside it",
                     value_transform={"kind": "distance_outside_band", "low": 2, "high": 4,
                                      "basis": "source_stated_value", "source_refs": [window]},
                     supporting_claim_refs=[window],
                     bound_support=[record("attribute.value_transform.low", claim_id=window, number=2,
                                           unit="log units", statement_kind="states_decision_threshold"),
                                    record("attribute.value_transform.high", claim_id=window, number=4,
                                           unit="log units", statement_kind="states_decision_threshold")])
    report = bound_support.validate(attribute, ORDERING_RULE, claims=claims)
    assert report["states"] == {"attribute.value_transform.low": "sourced_threshold",
                                "attribute.value_transform.high": "sourced_threshold"}
    assert all(b["range_endpoint"] is None for b in report["bounds"])
    assert criteria.authority_requirements(ORDERING_RULE, attribute, support=report) == []


def test_a_support_record_that_names_no_parameter_or_no_claim_of_this_criterion_is_refused(core):
    task_id = _task(core)
    stated = claim(core, task_id, claim_id="claim_f30", quote=F_QUOTE, value=30, unit="%", basis="asserted")
    claims = ledger.claims(core, [task_id])
    nowhere = dict(THRESHOLD_RULE, bound_support=[record("rule.cutoff.lower", claim_id=stated, number=30,
                                                         unit="%", statement_kind="states_decision_threshold")])
    assert any("which this criterion does not hold" in p
               for p in validate({"attribute": BIOAVAILABILITY, "rule": nowhere, "supporting_claim_ids": [stated],
                                  "expected_change": "x", "falsification_test": "y"}, claims))
    elsewhere = dict(THRESHOLD_RULE, bound_support=[record("rule.cutoff.value", claim_id="claim_not_cited",
                                                           number=30, unit="%",
                                                           statement_kind="states_decision_threshold")])
    problems = validate({"attribute": BIOAVAILABILITY, "rule": elsewhere, "supporting_claim_ids": [stated],
                         "expected_change": "x", "falsification_test": "y"}, claims)
    assert any("not an admitted claim this criterion cites" in p for p in problems), problems
    thin = dict(THRESHOLD_RULE, bound_support=[{"parameter_path": "rule.cutoff.value", "claim_id": stated,
                                                "source_number": 30, "source_unit": "%",
                                                "statement_kind": "states_decision_threshold"}])
    assert any("declares no applicability_rationale" in p
               for p in validate({"attribute": BIOAVAILABILITY, "rule": thin, "supporting_claim_ids": [stated],
                                  "expected_change": "x", "falsification_test": "y"}, claims))


def test_a_record_calling_a_stated_range_a_point_value_is_contradicted_by_the_claim_it_cites(core):
    """§5.4 item 3 asks a record to carry the censoring of the number it reads, and the claim says
    whether that is true: a record declaring no censoring against a claim that records a range
    reports the passage as more definite than it is. The declared comparator and the measurement
    context travel with the outcome, so no declared field is accepted and then read by nothing."""
    task_id = _task(core)
    ranged = claim(core, task_id, claim_id="claim_mw", quote=MW_QUOTE, low=380, high=500, unit="g/mol")
    claims = ledger.claims(core, [task_id])
    attribute = dict(MOLECULAR_WEIGHT, supporting_claim_refs=[ranged],
                     value_transform={"kind": "excess_above", "bound": 500, "basis": "source_stated_value",
                                      "source_refs": [ranged]},
                     bound_support=[dict(record("attribute.value_transform.bound", claim_id=ranged, number=500,
                                                unit="Da", statement_kind="reports_measurement"),
                                         censoring="none", source_comparator="<=",
                                         measurement_context="computed descriptors of marketed kinase inhibitors")])
    report = bound_support.validate(attribute, ORDERING_RULE, claims=claims)
    (bound,) = report["bounds"]
    assert bound["censoring"] == "none" and bound["source_comparator"] == "<="
    assert bound["measurement_context"].startswith("computed descriptors")
    assert any("declares no censoring while claim" in f["message"] and f["severity"] == "material"
               for f in report["findings"])
    honest = dict(attribute, bound_support=[dict(attribute["bound_support"][0], censoring="range")])
    assert not any("censoring" in f["message"] for f in
                   bound_support.validate(honest, ORDERING_RULE, claims=claims)["findings"])
    nonsense = dict(attribute, bound_support=[dict(attribute["bound_support"][0], censoring="rounded",
                                                   source_comparator="about")])
    refused = bound_support.validate(nonsense, ORDERING_RULE, claims=claims)
    assert len(refused["blocking"]) == 2 and refused["states"] == {
        "attribute.value_transform.bound": "invalid_support_record"}


def test_an_unaudited_bound_is_marked_unaudited_rather_than_passed_or_failed(core):
    """An already promoted criterion carries no support record, and §9.2 asks that absent metadata be
    marked unknown rather than given a status. It is visible on the rule-set entry, it is not a
    `sourced_threshold`, and `require_bound_support` is the gate that holds it out of a sourced set."""
    task_id = _task(core)
    stated = claim(core, task_id, claim_id="claim_f30", quote=F_QUOTE, value=30, unit="%")
    criteria.propose(core, task_id, dict(BIOAVAILABILITY, supporting_claim_refs=[stated]), THRESHOLD_RULE, by=AGENT)
    assert review.items(core, [task_id]) == {}              # the trigger table still lets a sourced preference through

    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    (entry,) = rules["entries"]
    assert entry["confirmed_by"] == "auto:trigger_table"
    assert entry["bound_support"] == {"states": {"rule.cutoff.value": "interpretation_undeclared"},
                                      "needing_a_decision": [], "claims_resolved": 1,
                                      "traces": {"rule.cutoff.value": "claim_value"}, "range_endpoints": []}
    assert rules["bounds_unsupported"] == [] and rules["bounds_withheld"] == []

    # Under the strict gate the *cutoff* is withheld, not the criterion: the number is unaudited, so
    # it may not act as a threshold, but the measurement behind it still ranks candidates in the
    # attribute's declared direction, which asserts no bound. See
    # `test_a_preference_whose_cutoff_is_withheld_still_ranks_on_the_measurement_behind_it`.
    strict = criteria.rule_set(core, task_id, criteria.confirm_rule_set(
        core, task_id, by=OPERATOR, require_bound_support=True))
    (withheld,) = strict["bounds_withheld"]
    assert withheld["fallback"] == "ranked_without_the_withheld_cutoff"
    (strict_entry,) = strict["entries"]
    assert strict_entry["rule_ref"] == entry["rule_ref"]
    assert strict["acceptance_label"] == "exploratory"


def test_a_rule_whose_cited_claims_contradict_its_cutoff_is_held_out_of_the_confirmed_set(core):
    """Missing or invalid support stays visible and non-scoring (§6 F2 acceptance). The rule keeps
    its registry record and its place in the report; what it loses is the board."""
    task_id = _task(core)
    stated = claim(core, task_id, claim_id="claim_f30", quote=F_QUOTE, value=30, unit="%")
    _, unsupported_ref = criteria.propose(
        core, task_id, dict(BIOAVAILABILITY, supporting_claim_refs=[stated]),
        dict(THRESHOLD_RULE, rule_id="rule_substituted", cutoff={"comparator": ">=", "value": 90, "unit": "%"}),
        by=AGENT)
    criteria.propose(core, task_id, dict(BIOAVAILABILITY, attribute_id="attr_half_life", name="Terminal half-life",
                                         unit="h", definition="terminal half-life after one oral dose"),
                     ORDERING_RULE, by=AGENT)

    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    assert [e["rule_ref"] for e in rules["entries"]] == ["rule_terminal-half-life@v1"]
    (held,) = rules["bounds_unsupported"]
    assert held["rule_ref"] == unsupported_ref and held["paths"] == ["rule.cutoff.value"]
    assert any("is not supported by the claims they cite" in reason for reason in rules["acceptance_reasons"])
    assert rules["acceptance_label"] == "exploratory"


# --- F3: the authority a criterion needs is a property of the whole decision-bearing object -------

def test_an_expert_set_bound_inside_a_transform_needs_the_same_decision_as_an_expert_set_cutoff(core):
    """The measured F3 defect: the number moved from the cutoff into the transform and the authority
    requirement disappeared with it -- zero review items, `auto:trigger_table` authority, and a cell
    scored against a number an expert never set."""
    task_id = _task(core)
    attribute = dict(MOLECULAR_WEIGHT, value_transform={"kind": "excess_above", "bound": 500,
                                                        "basis": "expert_set", "source_refs": []})
    _, rule_ref = criteria.propose(core, task_id, attribute, ORDERING_RULE, by=AGENT)
    criteria.propose(core, task_id, dict(BIOAVAILABILITY, attribute_id="attr_half_life",
                                         name="Terminal half-life", unit="h",
                                         definition="terminal half-life after one oral dose"),
                     ORDERING_RULE, by=AGENT)

    (item,) = [i for i in review.items(core, [task_id]).values() if i["subject"]["id"] == rule_ref]
    assert "value_transform claims basis expert_set" in item["why_expert_required"]
    assert [r["reason"] for r in criteria.authority_requirements(ORDERING_RULE, attribute)] \
        == ["transform_basis_expert_set"]
    # and it is the same requirement the number makes as a cutoff, which is the point of F3
    as_cutoff = dict(THRESHOLD_RULE, cutoff={"comparator": "<=", "value": 500, "unit": "g/mol"},
                     cutoff_basis="expert_set")
    assert [r["reason"] for r in criteria.authority_requirements(as_cutoff, MOLECULAR_WEIGHT)] \
        == ["cutoff_basis_expert_set"]

    with pytest.raises(criteria.InvariantViolation, match="await an expert decision"):
        criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR,
                                                                      allow_pending=True))
    assert [e["rule_ref"] for e in rules["entries"]] == ["rule_terminal-half-life@v1"]
    assert rules["pending"] == [rule_ref]           # the expert-set bound scores nothing without a decision

    # the machine cannot supply it either: route 2 demotes it to a non-scoring consideration
    resolved = adjudication.adjudicate(core, item)
    assert resolved["route"] == "no_authority_available" and resolved["scores_candidates"] is False


def test_a_sourced_transform_bound_needs_claims_that_resolve_and_not_a_nonempty_source_refs_list(core):
    """`check_value_transform` is satisfied by any non-empty `source_refs`, which is a list a
    proposer writes. A bound whose references resolve to no admitted claim stating it is the
    arbitrary cutoff the registry refuses elsewhere (§6 F3)."""
    task_id = _task(core)
    stated = claim(core, task_id, claim_id="claim_f30", quote=F_QUOTE, value=30, unit="%")
    claims = ledger.claims(core, [task_id])
    invented = dict(MOLECULAR_WEIGHT, value_transform={"kind": "excess_above", "bound": 500,
                                                       "basis": "source_stated_value",
                                                       "source_refs": ["claim_f30"]},
                    supporting_claim_refs=[stated])
    criteria.check_attribute(invented)              # the registry invariant is satisfied by the list alone
    report = bound_support.validate(invented, ORDERING_RULE, claims=claims)
    assert report["states"] == {"attribute.value_transform.bound": "unsupported"}
    assert any("none of the 1 cited claims states that number" in m for m in bound_support.messages(report))
    empty = dict(invented, value_transform=dict(invented["value_transform"], source_refs=[]))
    assert bound_support.validate(empty, ORDERING_RULE, claims=claims)["states"] == {
        "attribute.value_transform.bound": "unsupported"}


def test_a_decision_on_one_version_does_not_carry_to_a_version_reading_other_parameters(core):
    """An expert approved a rule version reading one attribute version with a bound of 500. A later
    version of the same criterion reads a bound of 450: the decision was about the version it names,
    so the new one enters nothing until it is decided in its turn (§6 F3 acceptance)."""
    task_id = _task(core)
    attribute = dict(MOLECULAR_WEIGHT, value_transform={"kind": "excess_above", "bound": 500,
                                                        "basis": "expert_set", "source_refs": []})
    attr_ref, rule_ref = criteria.propose(core, task_id, attribute, ORDERING_RULE, by=AGENT)
    criteria.propose(core, task_id, dict(BIOAVAILABILITY, attribute_id="attr_half_life",
                                         name="Terminal half-life", unit="h",
                                         definition="terminal half-life after one oral dose"),
                     ORDERING_RULE, by=AGENT)
    item = next(i for i in review.items(core, [task_id]).values() if i["subject"]["id"] == rule_ref)
    review.decide(core, item, decision="approve", actor=actor("human", "E1", "expert",
                                                              identity_basis="recorded_attestation"),
                  reason_text="", entry="interactive", historical_list_exposure="not_exposed")
    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    assert {e["rule_ref"]: e["authority"] for e in rules["entries"]}[rule_ref] == "human_scientific_approval"

    tighter = dict(attribute, value_transform={"kind": "excess_above", "bound": 450,
                                               "basis": "expert_set", "source_refs": []})
    moved = criteria.record_version(core, task_id, "attribute", attr_ref, tighter, by=AGENT,
                                    summary="a tighter bound")
    second = criteria.record_version(core, task_id, "rule", rule_ref,
                                     dict(ORDERING_RULE, attribute_ref=moved), by=AGENT,
                                     summary="reads the new attribute version")
    after = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR,
                                                                      allow_pending=True))
    assert [e["rule_ref"] for e in after["entries"]] == ["rule_terminal-half-life@v1"]
    assert second not in [e["rule_ref"] for e in after["entries"]]
    assert criteria.needs_expert(criteria.load(core, second, task_id), tighter) is True


def test_a_weight_with_no_provenance_is_a_decision_about_how_much_a_criterion_counts(core):
    """§5.4: a ranking weight is a registered parameter with a rationale, not a free coefficient."""
    rule = dict(THRESHOLD_RULE, rule_id="rule_oral-bioavailability", version=1)
    weighted = {"kind": "weighted_preference", "weight_vector": {"rule_oral-bioavailability@v1": 3.0}}
    assert [r["reason"] for r in criteria.authority_requirements(rule, BIOAVAILABILITY, weighting=weighted)] \
        == ["weight_without_provenance"]
    declared = dict(weighted, weight_provenance="registered in the task's ranking policy, version 2")
    assert criteria.authority_requirements(rule, BIOAVAILABILITY, weighting=declared) == []


# --- F4: a revision is revalidated whole, and what cannot be judged is not guessed ----------------

def test_a_revision_moving_a_cutoff_from_thirty_to_ninety_is_refused_with_the_diff_of_both_versions(core):
    """The measured F4 defect, on the handoff's synthetic case: `>= 30` -> `>= 90` was applied with
    no refusal. It is a tightening, and the number it moves to is one no cited claim states."""
    task_id = _task(core)
    stated = claim(core, task_id, claim_id="claim_f30", quote=F_QUOTE, value=30, unit="%")
    claims = ledger.claims(core, [task_id])
    rule = dict(THRESHOLD_RULE)
    assert stated in {c["claim_id"] for c in claims}
    revised, refused, record_of = adjudication._apply_revision(
        rule, {"cutoff": {"comparator": ">=", "value": 90, "unit": "%"}}, BIOAVAILABILITY, claims=claims)

    assert revised == rule, "the refused revision leaves the original rule standing"
    assert "not supported by the claims the criterion cites" in refused
    assert record_of["relation"] == "stronger"
    assert record_of["diff"] == [{"field": "cutoff", "from": {"comparator": ">=", "value": 30, "unit": "%"},
                                  "to": {"comparator": ">=", "value": 90, "unit": "%"}}]
    assert record_of["bound_support"] == {"rule.cutoff.value": "unsupported"}

    # a tightening to the number a cited claim does stand behind is a change in what the rule
    # demands that does not bypass the support check, so it is applied
    claim(core, task_id, claim_id="claim_f90", quote="90% of the dose was absorbed in every subject",
          value=90, unit="%")
    supported, no_refusal, applied = adjudication._apply_revision(
        rule, {"cutoff": {"comparator": ">=", "value": 90, "unit": "%"}}, BIOAVAILABILITY,
        claims=ledger.claims(core, [task_id]))
    assert no_refusal == "" and supported["cutoff"]["value"] == 90 and applied["relation"] == "stronger"

    # and a tightening whose number no claim states is refused on that ground alone, where the basis
    # is one no claim can trace: the authority is the task's text and the number is still a change
    constrained = dict(THRESHOLD_RULE, cutoff_basis="task_constraint")
    _, tightened, pinned = adjudication._apply_revision(
        constrained, {"cutoff": {"comparator": ">=", "value": 95, "unit": "%"}}, BIOAVAILABILITY, claims=claims)
    assert "may tighten a cutoff only to a number the cited claims state" in tightened
    assert pinned["relation"] == "stronger"


def test_a_revision_whose_relation_to_the_rule_is_not_decidable_requires_an_explicit_review(core):
    """Weaker has to mean something about candidates. A comparator that reverses, a unit the rule did
    not have, a relabelled basis and a changed predicate are not settings of one requirement, so the
    contract answers "not decidable" and the record asks for a person rather than guessing (§6 F4)."""
    rule = dict(THRESHOLD_RULE)
    for revision, expected in (({"cutoff": {"comparator": "<=", "value": 30, "unit": "%"}}, "comparator reverses"),
                               ({"cutoff": {"comparator": ">=", "value": 0.3, "unit": "fraction"}}, "cutoff unit changes"),
                               ({"cutoff_basis": "regulatory_or_standard_reference"}, "relabels where the number's"),
                               ({"predicate_form": "ordering"}, "changes what the rule tests")):
        revised, refused, record_of = adjudication._apply_revision(rule, revision, BIOAVAILABILITY, claims=[])
        assert revised == rule and record_of["requires_explicit_review"] is True, revision
        assert expected in refused, (revision, refused)
        assert record_of["relation"] == "not_decidable"

    # the fields a revision may not set at all: the attribute's transform is not this rule's to change
    revised, refused, record_of = adjudication._apply_revision(
        rule, {"value_transform": {"kind": "excess_above", "bound": 1, "basis": "expert_set"}},
        BIOAVAILABILITY, claims=[])
    assert revised == rule and "may not set value_transform" in refused
    assert record_of["fields_refused"] == ["value_transform"]


def test_a_revision_may_still_not_strengthen_a_rule_kind_or_an_on_state_policy(core):
    rule = dict(THRESHOLD_RULE)
    _, hard, _ = adjudication._apply_revision(rule, {"rule_kind": "hard_exclusion"}, BIOAVAILABILITY, claims=[])
    assert "may not make a rule a hard exclusion" in hard
    lenient = dict(rule, on_missing="unknown_no_penalty")
    _, harsher, record_of = adjudication._apply_revision(lenient, {"on_missing": "unknown_blocks_recommendation"},
                                                         BIOAVAILABILITY, claims=[])
    assert "may only weaken a rule" in harsher and record_of["relation"] == "stronger"
    # the registry's own default is what an unset policy is compared against, so naming it is no change
    _, unchanged, same = adjudication._apply_revision(rule, {"on_missing": "unknown_blocks_recommendation"},
                                                      BIOAVAILABILITY, claims=[])
    assert unchanged == "" and same["relation"] == "neutral" and same["diff"] == []
    weaker, no_refusal, applied = adjudication._apply_revision(rule, {"on_missing": "unknown_no_penalty"},
                                                               BIOAVAILABILITY, claims=[])
    assert no_refusal == "" and weaker["on_missing"] == "unknown_no_penalty" and applied["relation"] == "weaker"


def test_a_revision_that_drops_the_cutoff_is_a_weakening_and_keeps_its_basis_honest(core):
    rule = dict(THRESHOLD_RULE)
    weaker, no_refusal, applied = adjudication._apply_revision(
        rule, {"cutoff": None, "cutoff_basis": "none_evidence_insufficient"}, BIOAVAILABILITY, claims=[])
    assert no_refusal == "" and weaker["cutoff"] is None and applied["relation"] == "weaker"
    assert bound_support.validate(BIOAVAILABILITY, weaker, claims=[])["bounds"] == []


# --- the collapse writes versions too -------------------------------------------------------------

def test_a_collapse_refuses_to_carry_an_unsupported_bound_into_the_version_it_writes(core):
    """A collapse re-versions an attribute and its rule, so it is a site that puts decision-bearing
    numbers into the registry. It touches no bound, which is why it refuses rather than repairs."""
    task_id = _task(core)
    stated = claim(core, task_id, claim_id="claim_potency", value=7.0, unit="pChEMBL",
                   quote="a pChEMBL of 7.0 was the lowest potency considered active")
    potency = {"name": "Curated potency", "definition": "median pChEMBL at the required target",
               "measurement_kind": "quantitative", "unit": "pChEMBL", "direction": "higher_better",
               "acceptable_value_sources": ["curated_measurement"], "aggregation": "median",
               "supporting_claim_refs": [stated],
               "evidence_request": {"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values",
                                    "parameters": {"target_chembl_id": "CHEMBL_T1"}}}
    independent = dict(potency, name="Affinity on an independent curation",
                       evidence_request={"capability": "interaction_evidence_lookup",
                                         "question_kind": "gtopdb_affinity",
                                         "parameters": {"target_chembl_id": "CHEMBL_T1"}})
    rule = {"rule_kind": "preference", "predicate_form": "threshold", "cutoff_basis": "source_stated_value",
            "cutoff": {"comparator": ">=", "value": 9.0, "unit": "pChEMBL"}}
    criteria.propose(core, task_id, potency, dict(rule), by=OPERATOR)
    criteria.propose(core, task_id, independent, dict(rule), by=OPERATOR)

    (group,) = collapse_mod.plan(core, task_id)
    assert any("would carry an unsupported bound into the version this collapse writes" in why
               for why in group["refused"]), group["refused"]
    assert collapse_mod.collapse(core, task_id, by=OPERATOR, dry_run=False)["collapsed"] == []
    assert collapse_mod.records(core, task_id) == []

    # the same pair, with the cutoff its claim states, collapses as before
    other = _task(core)
    claim(core, other, claim_id="claim_potency", value=7.0, unit="pChEMBL",
          quote="a pChEMBL of 7.0 was the lowest potency considered active")
    supported = dict(rule, cutoff={"comparator": ">=", "value": 7.0, "unit": "pChEMBL"})
    criteria.propose(core, other, potency, dict(supported), by=OPERATOR)
    criteria.propose(core, other, independent, dict(supported), by=OPERATOR)
    (clean,) = collapse_mod.plan(core, other)
    assert clean["refused"] == [] and clean["bound_support"] == {"rule.cutoff.value": "interpretation_undeclared"}


# --- what the validator is, and is not --------------------------------------------------------------

def test_the_four_support_outcomes_are_recorded_separately_and_claims_that_cannot_be_resolved_are_unaudited(core):
    """§5.4 item 7: quote, arithmetic, semantic support and authority are four outcomes, not one
    verdict. And a criterion whose cited claims this store root cannot resolve is `unaudited`:
    absent evidence of support is not evidence against it, and neither is it support."""
    report = bound_support.validate(dict(BIOAVAILABILITY, supporting_claim_refs=["claim_elsewhere"]),
                                    THRESHOLD_RULE, claims=None)
    (bound,) = report["bounds"]
    assert bound["state"] == "unaudited" and bound["authority"] == "unaudited"
    assert (bound["quote"], bound["arithmetic"], bound["semantic_support"]) == (
        "not_declared", "not_declared", "undeclared")
    assert report["claims_resolved"] is None and report["findings"] == []
    assert set(bound_support.STATEMENT_KINDS) == {"states_decision_threshold", "reports_measurement",
                                                  "provides_heuristic"}
    assert bound_support.bounds(BIOAVAILABILITY, THRESHOLD_RULE)[0]["parameter_path"] == "rule.cutoff.value"


def test_a_transform_bound_on_a_basis_that_states_no_number_is_supported_is_refused(core):
    attribute = dict(MOLECULAR_WEIGHT, value_transform={"kind": "excess_above", "bound": 500,
                                                        "basis": "measured_distribution", "source_refs": []})
    report = bound_support.validate(attribute, ORDERING_RULE, claims=[])
    assert report["states"] == {"attribute.value_transform.bound": "unsupported"}
    assert any("which states that no number is supported" in m for m in bound_support.messages(report))


def test_a_preference_whose_cutoff_is_withheld_still_ranks_on_the_measurement_behind_it(core):
    """Withholding a cutoff and withholding a measurement are different acts, and only the first is
    what the support contract establishes.

    Measured on the clean derivation of 14 October 2026: all 33 cutoff-bearing proposals declared a
    support record, and the proposer declared 29 `reports_measurement` and 4 `provides_heuristic` --
    none `states_decision_threshold`, because the literature reports measurements and rules of thumb
    and does not state screening cutoffs. The strict gate therefore withholds every derived
    threshold, and dropping the criteria with them would discard sourced measurements the task cares
    about. Ranking by the measured value asserts no cutoff, which is the unsupported part.
    """
    task_id = _task(core)
    stated = claim(core, task_id, claim_id="claim_f58", quote=F_QUOTE, value=30, unit="%")
    _, rule_ref = criteria.propose(
        core, task_id, dict(BIOAVAILABILITY, supporting_claim_refs=[stated]),
        dict(THRESHOLD_RULE, rule_id="rule_reported_f",
             cutoff={"comparator": ">=", "value": 30, "unit": "%"},
             bound_support=[record("rule.cutoff.value", claim_id=stated, number=30, unit="%",
                                   statement_kind="reports_measurement")]),
        by=AGENT)

    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(
        core, task_id, by=OPERATOR, require_bound_support=True))
    (withheld,) = rules["bounds_withheld"]
    assert withheld["rule_ref"] == rule_ref
    assert withheld["fallback"] == "ranked_without_the_withheld_cutoff"
    # the criterion keeps the board, ranking on the measurement, asserting no threshold
    assert [e["rule_ref"] for e in rules["entries"]] == [rule_ref]
    assert rules["acceptance_label"] == "exploratory"


# --- the declared interpretation: what a machine settles before anyone is asked to grant it -------

# The step from "this passage reports X" to "X is the screening bound", declared as §5.4 asks for it.
# WHY a declaration exists at all: measured on the clean derivation of 14 October 2026, the proposer
# declared 29 of 33 cutoffs `reports_measurement` and 4 `provides_heuristic` and none
# `states_decision_threshold`, so every honest cutoff needed a decision and 34 of 35 criteria carried
# none. What a machine can check here is whether there is a declaration to judge; whether the
# inference is a good one is `adjudication`'s route 6, on the `adjudicator` role.
READS_AS_A_FLOOR = {
    "measurement": "the reported series achieved adequate exposure at an absolute oral bioavailability of 30%",
    "inference": "at_least_the_reported_value",
    "population_rationale": "the series is orally dosed small-molecule inhibitors, the population this screen "
                            "ranks, and below the reported fraction the exposure that made those compounds "
                            "usable was not reached",
}


def test_a_bound_whose_number_is_not_in_the_cited_claim_is_refused_however_well_the_interpretation_reads(core):
    """An interpretation is a step from a passage to a bound, so a passage that does not state the
    number offers no step to take. This is the measured F2 substitution -- a cutoff of 90 on a claim
    stating 30 -- with the prose that would make it sound considered: still `unsupported`, still
    blocking, and not on the table for any authority. A grant handed to the validator for that very
    path changes nothing: the state a grant can lift is the one where the number traces."""
    task_id = _task(core)
    stated = claim(core, task_id, claim_id="claim_f30", quote=F_QUOTE, value=30, unit="%")
    claims = ledger.claims(core, [task_id])
    invented = dict(THRESHOLD_RULE, cutoff={"comparator": ">=", "value": 90, "unit": "%"},
                    bound_support=[dict(record("rule.cutoff.value", claim_id=stated, number=90, unit="%",
                                               statement_kind="reports_measurement"),
                                        interpretation=dict(READS_AS_A_FLOOR, measurement="the series needed 90%"))])
    report = bound_support.validate(BIOAVAILABILITY, invented, claims=claims)
    assert report["states"] == {"rule.cutoff.value": "invalid_support_record"}
    assert report["grantable_paths"] == [] and report["blocking"]
    assert adjudication.grantable_interpretation(invented, BIOAVAILABILITY, claims) is None
    handed_a_grant = bound_support.validate(BIOAVAILABILITY, invented, claims=claims,
                                           grants={"rule.cutoff.value": {"adjudication_id": "adj_forged"}})
    assert handed_a_grant["granted_paths"] == []
    assert adjudication.route_of(invented, BIOAVAILABILITY, task.get(core, task_id), {})[0] \
        == "no_authority_available"
    assert any("not in the span quoted from the document" in m for m in bound_support.messages(report))

    # the number the passage does state, with the same declaration, is the case route 6 is for
    honest = dict(THRESHOLD_RULE, bound_support=[dict(record("rule.cutoff.value", claim_id=stated, number=30,
                                                            unit="%", statement_kind="reports_measurement"),
                                                     interpretation=READS_AS_A_FLOOR)])
    assert bound_support.validate(BIOAVAILABILITY, honest, claims=claims)["grantable_paths"] \
        == ["rule.cutoff.value"]


def test_a_circular_or_empty_interpretation_is_refused_and_leaves_the_bound_where_it_was(core):
    """A justification that states its conclusion as its premise is the one shape no adjudicator
    should be asked to see through, so it is refused here. Refused means not grantable: the bound
    stays `interpretation_added`, needing a decision, exactly where an undeclared one sits -- the
    sourced measurement behind it is not what is in doubt, so it is not held out of the registry."""
    task_id = _task(core)
    stated = claim(core, task_id, claim_id="claim_f30", quote=F_QUOTE, value=30, unit="%")
    claims = ledger.claims(core, [task_id])

    def read(interpretation) -> tuple[dict, dict]:
        rule = dict(THRESHOLD_RULE, bound_support=[
            dict(record("rule.cutoff.value", claim_id=stated, number=30, unit="%",
                        statement_kind="reports_measurement"), interpretation=interpretation)])
        report = bound_support.validate(BIOAVAILABILITY, rule, claims=claims)
        (bound,) = report["bounds"]
        return bound, report

    for interpretation, expected in (
            ({}, "not_declared"),
            ({"measurement": "", "inference": "", "population_rationale": ""}, "not_declared"),
            (dict(READS_AS_A_FLOOR, population_rationale=""), "incomplete"),
            (dict(READS_AS_A_FLOOR, inference="it_seemed_about_right"), "unreadable"),
            (dict(READS_AS_A_FLOOR, measurement="the bound is 30",
                  population_rationale="30 is the appropriate cutoff because 30 is the value to screen on"),
             "circular")):
        bound, report = read(interpretation)
        assert bound["interpretation"] == expected, interpretation
        assert bound["state"] == "interpretation_added" and report["grantable_paths"] == []
        assert criteria.needs_expert(THRESHOLD_RULE, BIOAVAILABILITY, support=report) is True
        if expected != "not_declared":
            assert any("cannot be granted" in f["message"] and f["severity"] == "material"
                       for f in report["findings"]), interpretation
        assert report["blocking"] == [], "a declaration nobody can check does not unsupport the number"

    declared, report = read(READS_AS_A_FLOOR)
    assert declared["interpretation"] == "declared" and report["grantable_paths"] == ["rule.cutoff.value"]
    assert declared["interpretation_inference"] == "at_least_the_reported_value"


def test_an_interpretation_whose_direction_contradicts_the_bound_it_reads_is_refused(core):
    """The direction of the inference is declared, and what it is checked against is mechanical: the
    comparator the rule applies, the kind of transform the bound sits in, and -- for a bound read as
    the edge of a reported range -- the range the cited claim actually states. Two declarations that
    contradict each other are not a reading of the passage, and that is checkable without reading
    either one."""
    task_id = _task(core)
    stated = claim(core, task_id, claim_id="claim_f30", quote=F_QUOTE, value=30, unit="%")
    ranged = claim(core, task_id, claim_id="claim_mw", quote=MW_QUOTE, low=380, high=500, unit="g/mol")
    claims = ledger.claims(core, [task_id])

    def cutoff_with(interpretation, statement_kind="reports_measurement") -> dict:
        rule = dict(THRESHOLD_RULE, bound_support=[
            dict(record("rule.cutoff.value", claim_id=stated, number=30, unit="%",
                        statement_kind=statement_kind), interpretation=interpretation)])
        (bound,) = bound_support.validate(BIOAVAILABILITY, rule, claims=claims)["bounds"]
        return bound

    backwards = cutoff_with(dict(READS_AS_A_FLOOR, inference="at_most_the_reported_value"))
    assert backwards["interpretation"] == "contradicts_the_rule"
    assert "demands the opposite of a candidate" in backwards["interpretation_detail"]
    not_a_heuristic = cutoff_with(dict(READS_AS_A_FLOOR, inference="the_heuristic_is_the_line"))
    assert not_a_heuristic["interpretation"] == "contradicts_the_rule"
    no_range = cutoff_with(dict(READS_AS_A_FLOOR, inference="outside_the_reported_range_is_out_of_population"))
    assert no_range["interpretation"] == "contradicts_the_rule"
    assert "states no range ending there" in no_range["interpretation_detail"]
    heuristic = cutoff_with(dict(READS_AS_A_FLOOR, inference="the_heuristic_is_the_line"),
                            statement_kind="provides_heuristic")
    assert heuristic["interpretation"] == "declared"

    # the live molecular-weight bound, which is the case the range reading exists for: 500 is the
    # upper end of the range the passage states, and `excess_above` applies it as a ceiling, so the
    # declared edge and the direction the transform imposes agree
    edge = dict(READS_AS_A_FLOOR, inference="outside_the_reported_range_is_out_of_population",
                measurement="clinically relevant kinase inhibitors fall in a range of about 380 to 500 Da",
                population_rationale="the compounds this screen ranks are oral kinase inhibitors of that same "
                                     "class, and a heavier molecule is outside the mass range in which the "
                                     "cited series showed efficient passive diffusion")
    attribute = dict(MOLECULAR_WEIGHT, supporting_claim_refs=[ranged],
                     value_transform={"kind": "excess_above", "bound": 500, "basis": "source_stated_value",
                                      "source_refs": [ranged]},
                     bound_support=[dict(record("attribute.value_transform.bound", claim_id=ranged, number=500,
                                                unit="Da", statement_kind="reports_measurement"),
                                         censoring="range", interpretation=edge)])
    report = bound_support.validate(attribute, ORDERING_RULE, claims=claims)
    (bound,) = report["bounds"]
    assert bound["interpretation"] == "declared" and bound["state"] == "interpretation_added"
    assert report["grantable_paths"] == ["attribute.value_transform.bound"]
    assert adjudication.route_of(ORDERING_RULE, attribute, task.get(core, task_id), {},
                                 claims)[0] == "bound_interpretation_granted"
    # and read as a floor instead, the same bound contradicts the transform that applies it
    as_a_floor = dict(attribute, bound_support=[
        dict(attribute["bound_support"][0], interpretation=dict(edge, inference="at_least_the_reported_value"))])
    (refused,) = bound_support.validate(as_a_floor, ORDERING_RULE, claims=claims)["bounds"]
    assert refused["interpretation"] == "contradicts_the_rule"


def test_a_hard_exclusion_whose_cutoff_is_withheld_does_not_fall_back_to_a_nudge(core):
    """An exclusion with no defensible cutoff has nothing left to do, and demoting it to a ranking
    would quietly turn a requirement into a preference -- the one direction a repair must not go."""
    task_id = _task(core)
    stated = claim(core, task_id, claim_id="claim_f_hard", quote=F_QUOTE, value=30, unit="%")
    _, rule_ref = criteria.propose(
        core, task_id, dict(BIOAVAILABILITY, supporting_claim_refs=[stated]),
        dict(THRESHOLD_RULE, rule_id="rule_hard_f", rule_kind="hard_exclusion",
             cutoff={"comparator": ">=", "value": 30, "unit": "%"},
             bound_support=[record("rule.cutoff.value", claim_id=stated, number=30, unit="%",
                                   statement_kind="provides_heuristic")]),
        by=AGENT)
    criteria.propose(core, task_id, dict(BIOAVAILABILITY, attribute_id="attr_half_life",
                                         name="Terminal half-life", unit="h",
                                         definition="terminal half-life after one oral dose"),
                     ORDERING_RULE, by=AGENT)
    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(
        core, task_id, by=OPERATOR, allow_pending=True, require_bound_support=True))
    (withheld,) = rules["bounds_withheld"]
    assert withheld["rule_ref"] == rule_ref and withheld["fallback"] is None
    assert not [e for e in rules["entries"] if e["rule_ref"] == rule_ref]
