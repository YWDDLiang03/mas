"""The primary acceptance measurement: recovery of the sealed historical criteria (handoff §12.2).

Every historical item in this file is obviously synthetic and says so in its own label. The real
list is sealed and held outside the repository, arrives once through `recovery.record_intake` after
the criteria are frozen, and appears in no fixture, default or literal here -- a test that carried a
real item would be a leak with a test's permissions.
"""

import json

import pytest

from mas.core import criteria, recovery, review, task
from mas.core.journal import actor
from mas.core.models import ModelRoster, ScriptedAdapter
from mas.core.runtime import Core

EVALUATOR = actor("human", "V1", "evaluator", identity_basis="recorded_attestation",
                  via={"surface": "terminal"})
OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")
PROPOSER = actor("agent", "proposer-1", "proposer", model_family="family_a")
TEMPLATE = actor("agent", "drug-adapter-template", "adapter_template")

TASK_SPEC = {
    "objective_text": "Prioritize oral compounds engaging the synthetic receptor S1",
    "mode": "conditional",
    "scope_entities": [{"entity_kind": "target", "identifier": "S1", "identifier_scheme": "test",
                        "role": "required", "label": "S1"}],
    "candidate_universe": {"kind": "enumerated_set", "members": ["alpha", "beta"], "size_if_known": 2},
    "constraints": [{"text": "oral administration", "kind": "route", "hardness": "hard", "provenance": "test"}],
    "evaluation_scope": {"comparison_basis": "all_pass_set", "abstention_allowed": True},
}

# Four registered criteria: one literature-derived ordering preference, a second reading of the same
# quantity (the same tools asked the same questions, which is what makes the two one meaning), one
# literature-derived criterion carrying a cutoff, and one restating a requirement the task supplied.
POTENCY = {
    "attribute": {"name": "Potency at S1", "definition": "Median curated potency at S1, as a pChEMBL value",
                  "measurement_kind": "quantitative", "unit": "pChEMBL", "direction": "higher_better",
                  "acceptable_value_sources": ["curated_measurement"], "aggregation": "median",
                  "derived_from": {"pool_criterion": "cri_synthetic_1@v1", "derivation_run": "run_synthetic"},
                  "evidence_request": {"capability": "interaction_evidence_lookup",
                                       "question_kind": "pchembl_values", "parameters": {"target": "S1"}}},
    "rule": {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
             "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty",
             "on_inapplicable": "unknown_no_penalty", "on_conflict": "unknown_no_penalty"},
}
# The live defect's shape: one quantity registered once per curating database. The two differ in
# `question_kind`, which names which database answers, so their *retrieval* identities differ while
# `derivation_stages.quantity_key` reads them as one quantity -- the distinction the gate rests on.
POTENCY_VARIANT = {
    "attribute": dict(POTENCY["attribute"], name="Affinity at S1 (second curation)",
                      definition="Median curated affinity at S1, from an independent curation",
                      evidence_request={"capability": "interaction_evidence_lookup",
                                        "question_kind": "gtopdb_affinity", "parameters": {"target": "S1"}}),
    "rule": dict(POTENCY["rule"]),
}
SOLUBILITY = {
    "attribute": {"name": "Aqueous solubility", "definition": "Aqueous solubility of the candidate",
                  "measurement_kind": "quantitative", "unit": "ug/mL", "direction": "higher_better",
                  "acceptable_value_sources": ["curated_measurement"], "aggregation": "median",
                  "derived_from": {"pool_criterion": "cri_synthetic_2@v1", "derivation_run": "run_synthetic"},
                  "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                                       "parameters": {"property": "solubility"}}},
    "rule": {"rule_kind": "preference", "predicate_form": "threshold",
             "cutoff": {"comparator": ">=", "value": 50, "unit": "ug/mL"},
             "cutoff_basis": "measured_distribution", "on_missing": "unknown_no_penalty",
             "on_inapplicable": "unknown_no_penalty", "on_conflict": "unknown_no_penalty"},
}
# A quantity derived from the one above by a declared transform: the same tool and field, so the
# same retrieval identity, while measuring something else. F5's lesson in the other direction.
SOLUBILITY_SHORTFALL = {
    "attribute": {"name": "Solubility shortfall below the bound",
                  "definition": "How far the candidate's aqueous solubility falls below 50 ug/mL, zero above it",
                  "measurement_kind": "quantitative", "unit": "ug/mL", "direction": "lower_better",
                  "acceptable_value_sources": ["curated_measurement"], "aggregation": "median",
                  "value_transform": {"kind": "shortfall_below", "bound": 50, "basis": "measured_distribution"},
                  "derived_from": {"pool_criterion": "cri_synthetic_4@v1", "derivation_run": "run_synthetic"},
                  "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                                       "parameters": {"property": "solubility"}}},
    "rule": {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
             "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty",
             "on_inapplicable": "unknown_no_penalty", "on_conflict": "unknown_no_penalty"},
}
ORAL_ROUTE = {
    "attribute": {"name": "Oral route on record", "definition": "Whether an oral route is on record",
                  "measurement_kind": "categorical", "direction": "non_directional",
                  "acceptable_value_sources": ["curated_measurement"], "aggregation": "consensus",
                  "derived_from": {"field": "constraints[0].text"},
                  "evidence_request": {"capability": "regulatory_status_lookup",
                                       "question_kind": "route_of_administration", "parameters": {}}},
    "rule": {"rule_kind": "preference", "predicate_form": "categorical_membership",
             "cutoff": {"comparator": "in", "value": ["oral"]}, "cutoff_basis": "task_constraint",
             "on_missing": "unknown_no_penalty", "on_inapplicable": "unknown_no_penalty",
             "on_conflict": "unknown_no_penalty"},
}

# Synthetic stand-ins for the sealed items. Three, so the arithmetic of the partition is readable.
HISTORICAL_ITEMS = [
    {"label": "Historical item A: aqueous solubility above a stated bound",
     "definition_as_given": "A synthetic stand-in. The candidate's aqueous solubility must be above the "
                            "bound this item states.",
     "dimension_as_given": "synthetic_dimension_one", "threshold_as_given": ">= 100 ug/mL",
     "unit_as_given": "ug/mL", "direction_as_given": "higher_better"},
    {"label": "Historical item B: potency at the synthetic receptor",
     "definition_as_given": "A synthetic stand-in. The candidate must be potent at the synthetic "
                            "receptor S1; this item states no threshold.",
     "dimension_as_given": "synthetic_dimension_two", "threshold_as_given": None,
     "unit_as_given": "pChEMBL", "direction_as_given": "higher_better"},
    {"label": "Historical item C: a requirement the task statement already supplied",
     "definition_as_given": "A synthetic stand-in for an item that the task statement states itself, so "
                            "that a criterion restating it is not an independent discovery.",
     "dimension_as_given": "synthetic_dimension_three", "threshold_as_given": None,
     "unit_as_given": None, "direction_as_given": "non_directional"},
]

INTAKE = {"provided_by": {"kind": "human", "id": "author-A", "role": "original_author"},
          "provided_at": "2026-10-14T00:00:00.000Z", "provenance_form": "author_supplied_list",
          "completeness_attestation": "complete", "items": HISTORICAL_ITEMS}


# --- fixtures ---------------------------------------------------------------------------------

def _propose(core, task_id, pair, by):
    return criteria.propose(core, task_id, dict(pair["attribute"]), dict(pair["rule"]), by=by)


def _seed(core, *, freeze: bool = True, decide_exposure: str | None = None) -> dict[str, str]:
    """A task with four registered criteria and, unless asked otherwise, a confirmed rule set."""
    task_id, _ = task.record_version(core, TASK_SPEC, by=OPERATOR)
    refs = {"task_id": task_id}
    for key, pair, by in (("potency", POTENCY, PROPOSER), ("variant", POTENCY_VARIANT, PROPOSER),
                          ("solubility", SOLUBILITY, PROPOSER), ("oral", ORAL_ROUTE, TEMPLATE)):
        attribute_ref, rule_ref = _propose(core, task_id, pair, by)
        refs[key], refs[f"{key}_rule"] = attribute_ref, rule_ref
    if decide_exposure is not None:
        # The oral-route criterion claims `cutoff_basis: task_constraint`, so the authority table
        # owes it a person's decision; deciding it is what puts an exposure declaration on a
        # confirming decision at all.
        item = next(i for i in review.items(core, [task_id]).values()
                    if i["subject"]["id"] == refs["oral_rule"])
        review.decide(core, item, decision="approve", actor=OPERATOR, reason_text="restates the task",
                      entry="interactive", historical_list_exposure=decide_exposure)
    if freeze:
        refs["rule_set_ref"] = criteria.confirm_rule_set(core, task_id, by=OPERATOR, coverage_floor=0.5,
                                                         allow_pending=True)
    return refs


@pytest.fixture
def frozen(core):
    return _seed(core)


def _intake(core, refs, *, items=None):
    return recovery.record_intake(core, refs["task_id"], dict(INTAKE, items=items or HISTORICAL_ITEMS),
                                  by=EVALUATOR)


def _facets(*, differs=(), threshold=None, notes="the two differ in how they are expressed"):
    """A per-facet judgement block of the shape the evaluator returns."""
    out = {}
    for facet in recovery.FACETS:
        if facet == "threshold":
            out[facet] = dict(threshold) if threshold else {"agrees": None}
            continue
        out[facet] = {"agrees": facet not in differs, "note": notes if facet in differs else ""}
    return out


def _entry(item_ref, refs, *, facets=None, shape=None, coverage=None, category=None,
           rationale="the derived criterion measures the same property the item asks for",
           basis="definition_and_unit_match", difference_kinds=None):
    entry = {"historical_item_ref": item_ref, "derived_attribute_refs": list(refs),
             "facets": facets if facets is not None else _facets(), "rationale": rationale,
             "match_basis": basis}
    for key, value in (("mapping_shape", shape), ("covers_historical_meaning", coverage),
                       ("category", category), ("difference_kinds", difference_kinds)):
        if value is not None:
            entry[key] = value
    return entry


def _roster(mapping, *, evaluator_adapter="isolated"):
    """A roster whose evaluator replies with `mapping`, bound apart from the proposer and critic."""
    evaluator = ScriptedAdapter("isolated", lambda request: {"mapping": mapping},
                                model="evaluator-model", provider_family="family_z")
    deriving = ScriptedAdapter("deriving", lambda request: {}, model="proposer-model",
                              provider_family="family_a")
    return ModelRoster({"isolated": evaluator, "deriving": deriving},
                       {"evaluator_judge": evaluator_adapter, "proposer": "deriving", "critic": "deriving"})


def _report(core, refs, mapping):
    return recovery.report(core, refs["task_id"], by=EVALUATOR, roster=_roster(mapping))


def _default_mapping(core, refs, intake):
    """A mapping that passes the gate: one exact, one near-equivalent on a threshold, one restatement."""
    items = [item["item_ref"] for item in intake["items"]]
    return [
        _entry(items[0], [refs["solubility"]],
               facets=_facets(differs=("threshold",),
                              threshold={"agrees": False, "historical": ">= 100 ug/mL",
                                         "derived": ">= 50 ug/mL",
                                         "note": "the derived cutoff sits below the one the item states"})),
        _entry(items[1], [refs["potency"]]),
        _entry(items[2], [refs["oral"]]),
    ]


# --- the intake -------------------------------------------------------------------------------

def test_the_intake_is_refused_while_the_criteria_are_not_frozen(core):
    refs = _seed(core, freeze=False)
    with pytest.raises(recovery.RecoveryError) as refusal:
        _intake(core, refs)
    assert refusal.value.code == "criteria_not_frozen"
    # And nothing was written: a refused intake must not leave the list in the store.
    assert recovery.intake_reference(core, refs["task_id"]) is None
    assert not core.artifacts.of_kind(recovery.INTAKE_KIND)

    # The same intake, once a rule set is confirmed, lands as evaluator-only content whose journal
    # event carries a hash and a count and no item.
    criteria.confirm_rule_set(core, refs["task_id"], by=OPERATOR, coverage_floor=0.5, allow_pending=True)
    record = _intake(core, refs)
    assert record["visibility"] == "evaluator_only"
    assert record["item_count"] == len(HISTORICAL_ITEMS)
    assert record["freeze"]["rule_set_refs"] == ["rules@v1"]
    header = recovery.intake_reference(core, refs["task_id"])
    assert header["content_sha256"] == record["content_sha256"]
    assert "items" not in header and HISTORICAL_ITEMS[0]["label"] not in json.dumps(header)
    # A second intake is refused: the list is opened once.
    with pytest.raises(recovery.RecoveryError) as second:
        _intake(core, refs)
    assert second.value.code == "intake_already_recorded"


def test_the_intake_is_refused_against_a_rule_set_the_task_never_confirmed(frozen, core):
    with pytest.raises(recovery.RecoveryError) as refusal:
        recovery.record_intake(core, frozen["task_id"], INTAKE, by=EVALUATOR, rule_set_refs=["rules@v9"])
    assert refusal.value.code == "unknown_rule_set"


# --- the gate ---------------------------------------------------------------------------------

def test_the_three_exclusive_categories_partition_the_historical_items_and_a_mapping_that_double_counts_one_is_refused(
        frozen, core):
    intake = _intake(core, frozen)
    report = _report(core, frozen, _default_mapping(core, frozen, intake))
    counts = report["counts"]
    assert counts["n_historical"] == 3
    assert counts["categories"] == {"exact": 2, "near_equivalent": 1, "missed": 0}
    assert sum(counts["categories"].values()) == counts["n_historical"] and counts["partitions"]
    assert counts["rates"]["exact"]["as_text"] == "2 / 3"
    assert counts["rates"]["exact_or_near_equivalent"]["as_text"] == "3 / 3"
    assert {m["category"] for m in report["mappings"]} <= set(recovery.CATEGORIES)
    # Each item appears exactly once across the three categories.
    assert sorted(m["historical_item_ref"] for m in report["mappings"]) == \
        sorted(item["item_ref"] for item in intake["items"])

    items = [item["item_ref"] for item in intake["items"]]
    doubled = [_entry(items[0], [frozen["solubility"]], facets=_facets(threshold={"agrees": True})),
               _entry(items[0], [frozen["potency"]]),
               _entry(items[1], [frozen["potency"]])]
    with pytest.raises(recovery.GateRefusal) as refusal:
        recovery.check_mapping(doubled, intake=intake,
                               derived=recovery.derived_set(core, frozen["task_id"]))
    codes = {problem["code"] for problem in refusal.value.problems}
    assert "duplicate_item_proposal" in codes and "partition_incomplete" in codes


def test_a_derived_criterion_cited_by_a_mapping_that_is_not_in_the_frozen_set_is_refused(frozen, core):
    intake = _intake(core, frozen)
    mapping = _default_mapping(core, frozen, intake)
    mapping[1] = _entry(intake["items"][1]["item_ref"], ["attr_never-registered@v1"])
    with pytest.raises(recovery.GateRefusal) as refusal:
        _report(core, frozen, mapping)
    problem = next(p for p in refusal.value.problems if p["code"] == "unknown_derived_ref")
    assert "attr_never-registered@v1" in problem["detail"]
    # Refused, not recorded: no comparison and no recovery figure exists for a mapping like this.
    assert recovery.latest_comparison(core, frozen["task_id"]) is None


def test_two_derived_variants_of_one_meaning_do_not_inflate_recovery(frozen, core):
    intake = _intake(core, frozen)
    derived = recovery.derived_set(core, frozen["task_id"])
    # One quantity read from two curations: the two criteria carry different retrieval identities and
    # one measurement identity, so the registry reads them as one quantity however they are named.
    assert derived["repeated_variants"] == {
        next(iter(derived["repeated_variants"])): sorted([frozen["potency"], frozen["variant"]])}
    potency, variant = (next(e for e in derived["criteria"] if e["attribute_ref"] == frozen[key])
                        for key in ("potency", "variant"))
    assert potency["meaning_key"] == variant["meaning_key"]
    assert potency["retrieval_identity_sha256"] != variant["retrieval_identity_sha256"]
    assert potency["same_meaning_as"] == [frozen["variant"]]
    items = [item["item_ref"] for item in intake["items"]]

    spent_twice = [_entry(items[0], [frozen["potency"]], facets=_facets(threshold={"agrees": True})),
                   _entry(items[1], [frozen["variant"]]),
                   _entry(items[2], [frozen["oral"]])]
    with pytest.raises(recovery.GateRefusal) as refusal:
        recovery.check_mapping(spent_twice, intake=intake, derived=derived)
    problem = next(p for p in refusal.value.problems if p["code"] == "derived_meaning_double_counted")
    assert problem["derived_attribute_refs"] == sorted([frozen["potency"], frozen["variant"]])

    # Cited together for one item, the two variants are one meaning and recover one item, not two.
    merged = [_entry(items[0], [frozen["solubility"]], facets=_facets(threshold={"agrees": True})),
              _entry(items[1], [frozen["potency"], frozen["variant"]], shape="merged",
                     coverage="both readings cover the one potency meaning the item states"),
              _entry(items[2], [frozen["oral"]])]
    report = _report(core, frozen, merged)
    assert report["counts"]["categories"]["exact"] == 3
    assert report["counts"]["derived_meanings_matched"] == 3
    # Neither reading is an extra: extras are counted by meaning, and this meaning was matched, so a
    # second registration of it is neither a second recovery nor a second derived dimension.
    assert report["counts"]["extra"]["count_by_meaning"] == 0
    assert report["counts"]["extra"]["count_by_criterion"] == 0


def test_a_quantity_derived_from_another_by_a_transform_is_not_a_repeated_variant_of_it(core):
    """The gate must not refuse a mapping because two criteria read one database field.

    A shared retrieval identity is not a shared meaning: "aqueous solubility" and "how far
    solubility falls below the bound" read the same field and measure different things, so matching
    them to two historical items is a legitimate mapping, not one meaning spent twice.
    """
    refs = _seed(core)
    attribute_ref, _ = _propose(core, refs["task_id"], SOLUBILITY_SHORTFALL, PROPOSER)
    criteria.confirm_rule_set(core, refs["task_id"], by=OPERATOR, coverage_floor=0.5, allow_pending=True)
    derived = recovery.derived_set(core, refs["task_id"])
    source, shortfall = (next(e for e in derived["criteria"] if e["attribute_ref"] == ref)
                         for ref in (refs["solubility"], attribute_ref))
    assert source["retrieval_identity_sha256"] == shortfall["retrieval_identity_sha256"]
    assert source["meaning_key"] != shortfall["meaning_key"]

    intake = _intake(core, refs)
    items = [item["item_ref"] for item in intake["items"]]
    checked = recovery.check_mapping(
        [_entry(items[0], [refs["solubility"]], facets=_facets(threshold={"agrees": True})),
         _entry(items[1], [attribute_ref]),
         _entry(items[2], [refs["oral"]])],
        intake=intake, derived=derived)
    assert [m["category"] for m in checked["mapping"]] == ["exact", "exact", "exact"]


def test_a_split_mapping_must_cover_each_historical_meaning_explicitly(frozen, core):
    intake = _intake(core, frozen)
    derived = recovery.derived_set(core, frozen["task_id"])
    items = [item["item_ref"] for item in intake["items"]]
    half_declared = [
        _entry(items[0], [frozen["potency"]], shape="split",
               facets=_facets(threshold={"agrees": True}),
               coverage="this side covers the solubility meaning"),
        _entry(items[1], [frozen["variant"]], shape="split"),
        _entry(items[2], [frozen["oral"]]),
    ]
    with pytest.raises(recovery.GateRefusal) as refusal:
        recovery.check_mapping(half_declared, intake=intake, derived=derived)
    codes = {problem["code"] for problem in refusal.value.problems}
    assert "split_coverage_not_explicit" in codes and "coverage_not_explicit" in codes

    both_declared = [dict(half_declared[0]),
                     dict(half_declared[1], covers_historical_meaning="this side covers the potency meaning"),
                     half_declared[2]]
    checked = recovery.check_mapping(both_declared, intake=intake, derived=derived)
    assert [m["mapping_shape"] for m in checked["mapping"][:2]] == ["split", "split"]
    assert all(m["covers_historical_meaning"] for m in checked["mapping"][:2])


def test_a_threshold_difference_makes_a_match_near_equivalent_and_is_reported_not_hidden(frozen, core):
    intake = _intake(core, frozen)
    derived = recovery.derived_set(core, frozen["task_id"])
    items = [item["item_ref"] for item in intake["items"]]
    difference = {"agrees": False, "historical": ">= 100 ug/mL", "derived": ">= 50 ug/mL",
                  "note": "the derived cutoff sits below the one the item states"}

    # Declaring it exact over a difference the proposal itself records is refused, not accepted.
    with pytest.raises(recovery.GateRefusal) as refusal:
        recovery.check_mapping([_entry(items[0], [frozen["solubility"]], category="exact",
                                       facets=_facets(threshold=difference)),
                                _entry(items[1], [frozen["potency"]]),
                                _entry(items[2], [frozen["oral"]])],
                               intake=intake, derived=derived)
    problem = next(p for p in refusal.value.problems
                   if p["code"] == "exact_claimed_over_a_reported_difference")
    assert problem["differing_facets"] == ["threshold"]

    # Stating the difference without both numbers hides it, which is also refused.
    with pytest.raises(recovery.GateRefusal) as hidden:
        recovery.check_mapping([_entry(items[0], [frozen["solubility"]],
                                       facets=_facets(threshold={"agrees": False, "note": "the cutoffs differ"})),
                                _entry(items[1], [frozen["potency"]]),
                                _entry(items[2], [frozen["oral"]])],
                               intake=intake, derived=derived)
    assert "threshold_difference_not_preserved" in {p["code"] for p in hidden.value.problems}

    # Reported properly, it is a near-equivalent and both numbers survive into the report.
    report = _report(core, frozen, _default_mapping(core, frozen, intake))
    mapped = next(m for m in report["mappings"] if m["historical_item_ref"] == items[0])
    assert mapped["category"] == "near_equivalent" and mapped["difference_kinds"] == ["threshold"]
    assert mapped["facets"]["threshold"]["historical"] == ">= 100 ug/mL"
    assert mapped["facets"]["threshold"]["derived"] == ">= 50 ug/mL"
    assert report["counts"]["categories"]["exact"] == 2
    rendered = recovery.render_markdown(report)
    assert ">= 100 ug/mL" in rendered and ">= 50 ug/mL" in rendered

    # The threshold facet is judged wherever the item states one; leaving it out is refused.
    with pytest.raises(recovery.GateRefusal) as unjudged:
        recovery.check_mapping([_entry(items[0], [frozen["solubility"]], facets=_facets()),
                                _entry(items[1], [frozen["potency"]]),
                                _entry(items[2], [frozen["oral"]])],
                               intake=intake, derived=derived)
    assert next(p for p in unjudged.value.problems if p["code"] == "facet_not_judged")["facet"] == "threshold"


# --- the report -------------------------------------------------------------------------------

def test_the_origin_stratified_view_separates_task_mandated_restatements_from_literature_derived_criteria(
        frozen, core):
    intake = _intake(core, frozen)
    report = _report(core, frozen, _default_mapping(core, frozen, intake))
    view = report["origin_stratified"]
    assert view["derived_criteria_by_stratum"]["task_mandated"] == 1
    assert view["derived_criteria_by_stratum"]["literature_derived"] == 3
    assert set(view["recovered_by_stratum"]) == {"task_mandated", "literature_derived"}
    assert view["recovered_by_stratum"]["task_mandated"]["exact"] == 1
    # Two of the three items were recovered by criteria derived from the literature; the third was
    # recovered only by a criterion restating the task, so it is not an independent derivation.
    independent = view["independently_derived_only"]
    assert independent["recovered_as_text"] == "2 / 3" and independent["exact_as_text"] == "1 / 3"
    assert independent["items_recovered_only_by_a_restatement"] == [intake["items"][2]["item_ref"]]
    assert report["counts"]["rates"]["exact_or_near_equivalent"]["as_text"] == "3 / 3"


def test_the_exposure_declaration_is_carried_into_the_report(core):
    refs = _seed(core, decide_exposure="undeclared")
    intake = _intake(core, refs)
    report = _report(core, refs, _default_mapping(core, refs, intake))
    exposure = report["exposure"]
    # Nobody could have read the list before the freeze: the intake is refused until the criteria are
    # frozen, so the ordering is a mechanical guarantee rather than an assurance.
    assert exposure["coordinator_or_deriving_agent_saw_the_list_before_the_freeze"] is False
    assert exposure["intake_arrived_after_the_freeze"] is True
    assert exposure["reads_before_the_freeze"] == [] and exposure["reads_logged"] >= 1
    # The one criterion a person confirmed declared nothing, and an undeclared declaration counts as
    # exposed (design §8.6), so the whole comparison reports the assisted view.
    assert exposure["declared_on_confirming_decisions"]["undeclared"] == [refs["oral"]]
    assert exposure["criteria_in_the_assisted_view"] == [refs["oral"]]
    assert exposure["recovery_view"] == "assisted"
    assert recovery.public_counts(report)["exposure"]["recovery_view"] == "assisted"
    assert "assisted" in recovery.render_markdown(report)

    # With no person's declaration anywhere, the same machinery reports the independent view.
    with Core.open(core.store.root.parent / "second") as other:
        clean = _seed(other)
        clean_intake = _intake(other, clean)
        clean_report = _report(other, clean, _default_mapping(other, clean, clean_intake))
        assert clean_report["exposure"]["recovery_view"] == "independent"


def test_the_evaluator_role_is_not_the_proposer_or_critic_adapter(frozen, core):
    shared = ScriptedAdapter("deriving", lambda request: {"mapping": []}, model="proposer-model")
    not_isolated = ModelRoster({"deriving": shared},
                               {"evaluator_judge": "deriving", "proposer": "deriving", "critic": "deriving"})
    with pytest.raises(recovery.RecoveryError) as refusal:
        recovery.check_isolated_evaluator(not_isolated)
    assert refusal.value.code == "evaluator_not_isolated"

    unbound = ModelRoster({"deriving": shared}, {"proposer": "deriving", "critic": "deriving"})
    with pytest.raises(recovery.RecoveryError) as missing:
        recovery.check_isolated_evaluator(unbound)
    assert missing.value.code == "evaluator_unbound"

    # The refusal comes before any call, so the proposer never sees the sealed list.
    intake = _intake(core, frozen)
    with pytest.raises(recovery.RecoveryError):
        recovery.propose_mapping(core, not_isolated, frozen["task_id"], intake=intake,
                                 derived=recovery.derived_set(core, frozen["task_id"]))
    assert shared.requests == []

    judged_by = recovery.check_isolated_evaluator(_roster([]))
    assert judged_by["role"] == "evaluator_judge" and judged_by["adapter_id"] == "isolated"
    assert judged_by["distinct_from"] == {"proposer": "deriving", "critic": "deriving", "adjudicator": None}


def test_the_published_counts_carry_the_measurement_and_none_of_the_historical_items(frozen, core, tmp_path):
    intake = _intake(core, frozen)
    report = _report(core, frozen, _default_mapping(core, frozen, intake))
    summary = recovery.public_counts(report)
    published = json.dumps(summary) + recovery.render_counts(summary)
    for item in intake["items"]:
        assert item["label"] not in published
        assert item["definition_as_given"] not in published
        assert item["item_ref"] not in published
    assert ">= 100 ug/mL" not in published      # the historical threshold is a historical item too
    assert summary["rates"]["exact"]["as_text"] == "2 / 3"
    assert summary["visibility"] == "agent_visible" and report["visibility"] == "evaluator_only"

    record = recovery.write(report, tmp_path / "out", store_root=str(core.store.root))
    assert record["file_visibility"] == {
        recovery.REPORT_JSON: "evaluator_only", recovery.REPORT_MARKDOWN: "evaluator_only",
        recovery.COUNTS_JSON: "agent_visible", recovery.COUNTS_MARKDOWN: "agent_visible",
        recovery.MANIFEST_JSON: "agent_visible"}
    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == sorted(
        [recovery.REPORT_JSON, recovery.REPORT_MARKDOWN, recovery.COUNTS_JSON, recovery.COUNTS_MARKDOWN,
         recovery.MANIFEST_JSON])
    on_disk = (tmp_path / "out" / recovery.COUNTS_MARKDOWN).read_text(encoding="utf-8")
    assert HISTORICAL_ITEMS[0]["label"] not in on_disk

    # The mappings restate the sealed items, so they may not be written where reviewers are sent.
    for published_directory in ("design_audit", "docs", "examples"):
        with pytest.raises(recovery.RecoveryError) as refusal:
            recovery.write(report, tmp_path / published_directory / "recovery")
        assert refusal.value.code == "evaluator_only_destination"


def test_a_recorded_comparison_is_reported_again_without_a_second_model_call(frozen, core):
    intake = _intake(core, frozen)
    mapping = _default_mapping(core, frozen, intake)
    roster = _roster(mapping)
    first = recovery.report(core, frozen["task_id"], by=EVALUATOR, roster=roster)
    adapter = roster.adapter("evaluator_judge")
    assert len(adapter.requests) == 1
    again = recovery.report(core, frozen["task_id"], by=EVALUATOR, roster=roster)
    assert len(adapter.requests) == 1
    assert again["comparison_id"] == first["comparison_id"]
    assert again["counts"] == first["counts"]
    assert again["derived_set"]["unchanged_since_the_comparison"] is True
    assert again["derived_set"]["digest_when_compared"] == again["derived_set"]["payload_digest"]
    # A second mapping over a list already opened is refused, not quietly ignored: it would not be
    # another independent recovery (§12.4).
    with pytest.raises(recovery.RecoveryError) as refusal:
        recovery.report(core, frozen["task_id"], by=EVALUATOR, mapping=mapping)
    assert refusal.value.code == "comparison_already_recorded"
    # Every read of the sealed list is logged, including the ones a report makes.
    log = recovery.access_log(core, frozen["task_id"])
    assert [read["purpose"] for read in log].count("primary_cqa_recovery") == 1
    assert [read["purpose"] for read in log].count("recovery_report") == 2
    assert {read["role"] for read in log} == {"evaluator"}
