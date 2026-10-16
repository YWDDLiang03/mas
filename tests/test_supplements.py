"""The supplement boundary: exact matching, mutant isolation and immutable bindings."""

import pytest

from mas.core import assessor, evidence, ledger, measurement, supplements, task
from mas.core.broker import Broker
from tests.test_run_end_to_end import OPERATOR, setup_task
from tests.test_measurement_profile import setup_task as setup_profile_task


def _source(core, *, include_mutant=False):
    quote = "CompoundX inhibited CSF1R with an IC50 of 5 nM."
    mutant_quote = "CompoundX inhibited the CSF1R T663I mutant with an IC50 of 4 nM."
    document = {"source_id": "src_test", "year": "2024", "source_hit": {"first_publication_date": "2024-01-03"},
                "passages": [{"passage_id": "p1", "text": quote}, {"passage_id": "p2", "text": mutant_quote}]}
    doc_ref = core.artifacts.put("document", document)
    reviews = []
    for index, text in enumerate((quote, mutant_quote), 1):
        claim = {"source_ref": "src_test", "document_artifact_id": doc_ref, "candidate_ref": "original_candidate",
                 "attribute_ref": "original_attribute@v1", "evidence_kind": "peer_reviewed",
                 "determination_basis": "measured", "value": 5 if index == 1 else 4, "unit": "nM",
                 "scope": {"population_or_system": "wild-type CSF1R" if index == 1 else "CSF1R T663I mutant"},
                 "location": {"location_kind": "paragraph", "locator_value": f"p{index}", "quoted_span": text,
                              "span_checked_against_source": True}, "reading_depth": "full_text"}
        claim_id = ledger.record_claim(core, "run_source", claim, by=OPERATOR, admission_state="admitted",
                                       admission_reasons=["quote_verified", "value_in_quote"])
        reviews.append({"claim_id": claim_id, "target_chembl_id": "CHEMBL1844",
                        "decision": "include" if index == 1 or include_mutant else "exclude",
                        "reason": "scope reviewed", "conditions": {"target_variant": "wild_type",
                                                                       "assay": "biochemical assay", "unknown_conditions": ["ATP"]}})
    return supplements.create_verified(core, source_run_id="run_source", document_ref=doc_ref,
                                       candidate_identifiers=[{"scheme": "inchikey", "value": "EXACT-ID"}],
                                       reviews=reviews, selection_rationale="Known-gap exploratory source selection", by=OPERATOR)


def _attribute(target="CHEMBL1844"):
    return {"attribute_id": "new_attribute", "version": 2, "name": "CSF1R potency", "measurement_kind": "quantitative", "unit": "pChEMBL",
            "acceptable_value_sources": ["peer_reviewed"], "aggregation": "median", "direction": "higher_better",
            "evidence_requests": [{"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values",
                                   "identifier_scheme": "inchikey", "parameters": {"target_chembl_id": target}}]}


def test_uniform_lookup_matches_exact_compound_target_and_preserves_source(core):
    ref = _source(core)
    identity = {"identifiers": [{"scheme": "inchikey", "value": "EXACT-ID"}],
                "identity_link_basis": "exact_identifier_match"}
    claims, _, _ = evidence.gather(core, Broker(core), None, "run_lookup", candidate={"candidate_id": "new_candidate"},
                                   identity=identity, attribute=_attribute(), objective_text="test", cutoff_date="2026-10-16",
                                   verified_supplement_refs=[ref], defer_capabilities=("literature_retrieval",))
    assert len(claims) == 1
    assert claims[0]["candidate_ref"] == "new_candidate" and claims[0]["attribute_ref"] == "new_attribute@v2"
    assert claims[0]["value"] == 5 and claims[0]["unit"] == "nM"
    assert claims[0]["reused_from_claim_id"] != claims[0]["claim_id"]
    reused = ledger.claims(core, ["run_lookup"])
    assert reused[0]["verified_supplement_ref"] == ref and reused[0]["candidate_ref"] == "new_candidate"
    rule = {"rule_id": "new_rule", "version": 2, "rule_kind": "preference", "predicate_form": "ordering",
            "cutoff": None, "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty"}
    cell, _ = assessor.assess_cell(candidate={"candidate_id": "new_candidate"}, attribute=_attribute(), rule=rule,
                                  rule_set_ref="rules@v1", claims=claims, resolved=True)
    assert cell["value"] == pytest.approx(8.3010299957) and cell["determination_basis"] == "measured"
    record = supplements.load(core, ref)
    assert len(record["excluded_claims"]) == 1
    args = dict(candidate={"candidate_id": "other"}, attribute=_attribute(), cutoff_date="2026-10-16")
    assert supplements.lookup(core, [ref], identity={"identifiers": [{"scheme": "inchikey", "value": "OTHER"}]}, **args) == []
    assert supplements.lookup(core, [ref], identity=identity, candidate={"candidate_id": "new_candidate"},
                              attribute=_attribute("CHEMBL3650")) == []
    assert supplements.lookup(core, [ref], identity=identity, candidate={"candidate_id": "new_candidate"},
                              attribute=_attribute(), cutoff_date="2023-12-31") == []


def test_mutant_cannot_be_relabelled_as_wild_type(core):
    with pytest.raises(supplements.SupplementError, match="original extraction identifies a mutant"):
        _source(core, include_mutant=True)


def test_task_version_and_profile_freeze_supplement_refs_and_digests(core):
    # Only profile tests remove the unrelated T1; version-guard fixtures below intentionally start at v1.
    task_id = setup_profile_task(core)
    original = task.get(core, task_id)
    ref = _source(core)
    _, version = supplements.attach(core, task_id, ref, by=OPERATOR)
    context = task.get(core, task_id)
    assert version == original["version"] + 1
    assert task.get(core, task_id, original["version"]) == original
    profile = measurement.register(core, task_id, by=OPERATOR, primary_board="supplemented exploration",
                                   rationale="Reuse verified measured claims", expected_effect="Answer known gaps")
    policy = measurement.load(core, task_id, profile)["policy"]
    assert policy["retrieval_policy"]["verified_supplements"] == supplements.binding(core, context)
    assert policy["retrieval_policy"]["verified_supplements"]["entries"][0]["ref"] == ref
    changed = dict(context, verified_supplement_refs=[])
    from mas.core import criteria
    with pytest.raises(measurement.MeasurementError, match="verified_supplements"):
        measurement.verify(core, task_id, profile, context=changed, rule_set=criteria.rule_set(core, task_id),
                           sweep_seed=0, evidence_cutoff=policy["evidence_cutoff"])


def test_attach_refuses_a_frozen_task_version(core):
    task_id = setup_profile_task(core)
    measurement.register(core, task_id, by=OPERATOR, primary_board="original", rationale="Original evidence policy",
                         expected_effect="Preserve the existing result")
    before = task.get(core, task_id)
    with pytest.raises(supplements.SupplementError, match="frozen profile"):
        supplements.attach(core, task_id, _source(core), by=OPERATOR)
    assert task.get(core, task_id) == before


def _bound_run(core, task_id, *, purpose="criteria_derivation", operation="registered_reduction", state="completed"):
    binding = {"task_context_id@v": f"{task_id}@v1", "run_purpose": purpose, "operation": operation}
    ref = core.artifacts.put("run_binding", binding)
    core.journal.append("run_bound", "run.created", actor=OPERATOR, state_to="queued",
                        payload={"task_id": task_id, "binding_artifact_id": ref})
    if state != "queued":
        event = {"running": "run.started", "completed": "run.completed", "failed": "run.failed",
                 "unresolved": "run.unresolved"}[state]
        core.journal.append("run_bound", event, actor=OPERATOR, state_to=state)
    return ref, binding


def test_attach_after_completed_registered_reduction_creates_v2_without_editing_v1(core):
    task_id = setup_task(core)
    original = task.get(core, task_id)
    binding_ref, original_binding = _bound_run(core, task_id)
    ref = _source(core)
    assert supplements.attach(core, task_id, ref, by=OPERATOR) == (task_id, 2)
    assert task.get(core, task_id)["verified_supplement_refs"] == [ref]
    assert task.get(core, task_id, 1) == original
    assert core.artifacts.payload(binding_ref) == original_binding


@pytest.mark.parametrize("purpose,operation,state", [
    ("criteria_derivation", "registered_reduction", "queued"),
    ("criteria_derivation", "registered_reduction", "running"),
    ("criteria_derivation", "registered_reduction", "failed"),
    ("criteria_derivation", "registered_reduction", "unresolved"),
    ("criteria_derivation", "other_research", "completed"),
    ("sweep", "registered_reduction", "completed"),
    (None, None, "completed"),
])
def test_attach_still_refuses_active_failed_or_sweep_bindings(core, purpose, operation, state):
    task_id = setup_task(core)
    before = task.get(core, task_id)
    _bound_run(core, task_id, purpose=purpose, operation=operation, state=state)
    with pytest.raises(supplements.SupplementError, match="already bound to a run"):
        supplements.attach(core, task_id, _source(core), by=OPERATOR)
    assert task.get(core, task_id) == before
