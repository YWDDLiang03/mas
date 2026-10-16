"""Uploaded observations exercise the real ledger/assessor without a provider call."""
from copy import deepcopy

import pytest

from mas.core import adjudication, assessor, config, derivation, existing_research, ledger, task
from mas.core.journal import actor
from mas.core.models import ModelRoster, ScriptedAdapter
from mas.core.uploaded_evidence import ADAPTER, DIMENSIONS, UploadedEvidence, UploadedRequirementsPending

BY = actor("system", "upload-fixture", "operator")


def bundle(*, library="fixture-library"):
    candidates = [{"candidate_id": key, "label": key + " carrier", "entity_kind": "carrier", "identifiers": []}
                  for key in ("sample-1", "sample-2", "sample-3")]
    measurements = [
        {"measurement_id": "m1", "candidate_id": "sample-1", "property_id": "size", "property_label": "DLS size",
         "value": 0., "unit": "nm", "conditions": {"temperature": "25 C"}, "basis": "measured"},
        {"measurement_id": "m2", "candidate_id": "sample-2", "property_id": "size", "value": 150.,
         "unit": "nm", "conditions": {"temperature": "25 C"}, "basis": "predicted"},
        {"measurement_id": "m3", "candidate_id": "sample-1", "property_id": "hazard", "value": False,
         "unit": None, "conditions": {}, "basis": "measured"},
        {"measurement_id": "m4", "candidate_id": "sample-1", "property_id": "size", "value": 99.,
         "unit": "nm", "conditions": {"temperature": "37 C"}, "basis": "measured"}]
    for index, row in enumerate(measurements, 2):
        row.update(source_id="src_upload_filehash", source_locator={"row_number": index}, row_number=index,
                   provenance={"filename": "fixture.csv", "content_sha256": "fixture-file-hash",
                               "declared_source": "User-declared laboratory record"})
    return UploadedEvidence(candidates, measurements, library_id=library, dataset_sha256="fixture-dataset")


def spec():
    return {"objective_text": "Select carriers with size at most 200 nm at 25 C", "mode": "conditional",
        "evaluation_scope": "uploaded carriers only", "candidate_universe": {"members": ["sample-1", "sample-2", "sample-3"]},
        "constraints": [{"text": "size at most 200 nm at 25 C", "kind": "property", "hardness": "hard",
            "property_id": "size", "comparator": "<=", "value": 200., "unit": "nm",
            "conditions": {"temperature": "25 C"}}]}


def test_rows_are_fixed_scoped_and_typed_without_drug_assumptions(core):
    uploaded = bundle()
    tid, _ = task.record_version(core, spec(), by=BY)
    pin = uploaded.materialize(core, tid, by=BY)
    count = core.journal.last_seq(tid)
    assert uploaded.materialize(core, tid, by=BY) == pin
    assert core.journal.last_seq(tid) == count
    assert pin["manifest"]["source_runs"] == []
    assert ADAPTER["primary_scheme"] == "uploaded_id"
    records = uploaded.identity_hook({"members": ["sample-1", "not-in-library"]})
    assert records[0]["candidate_id"] == records[0]["input_label"] == "sample-1"
    assert records[1]["identity_link_basis"] == "unresolved"
    assert "sample-1" not in str(uploaded.property_catalog())
    assert "150" not in str(uploaded.property_catalog())
    context = task.get(core, tid)
    assert uploaded.validate_task(context) == []
    template = uploaded.objective_templates(context)[0]
    assert template["rule"]["cutoff"] == {"comparator": "<=", "value": 200., "unit": "nm"}
    assert template["attribute"]["aggregation"] == "consensus"
    attr = dict(template["attribute"], attribute_id="attr_size", version=1)
    rule = dict(template["rule"], rule_id="rule_size", version=1)
    rows = uploaded.claims_for("sample-1", attribute_ref="attr_size@v1", attribute=attr)
    assert [r["value"] for r in rows] == [0.]
    assert rows[0]["source_status"] == rows[0]["evidence_kind"] == "user_supplied_document"
    cell, _ = assessor.assess_cell(candidate={"candidate_id": "sample-1"}, attribute=attr, rule=rule,
        rule_set_ref="rules_fixture@v1", claims=rows, resolved=True, qualification_policy="qualification_first_v1")
    assert cell["verdict"] == "pass"
    predicted = uploaded.claims_for("sample-2", attribute_ref="attr_size@v1", attribute=attr)
    cell, reason = assessor.assess_cell(candidate={"candidate_id": "sample-2"}, attribute=attr, rule=rule,
        rule_set_ref="rules_fixture@v1", claims=predicted, resolved=True, qualification_policy="qualification_first_v1")
    assert cell["verdict"] == "unknown_missing"
    assert cell["set_aside_claims"][0]["reason"] == "prediction_not_direct_gate"
    hazard = dict(attr, measurement_kind="categorical", unit=None, evidence_request={"capability": "uploaded_measurement_lookup",
        "question_kind": "measurement", "parameters": {"property": "hazard", "conditions": {}}})
    assert uploaded.claims_for("sample-1", attribute=hazard)[0]["value"] is False
    absent = dict(attr, evidence_request={"capability": "predicted_property_lookup", "question_kind": "admet"})
    offered, error, searched = uploaded.evidence_hook({"candidate_id": "sample-1", "attribute": absent})
    assert offered == [] and error is None and "unsupported_route" in searched[0]
    source = core.artifacts.payload(pin["manifest"]["sources"][0]["artifact_id"])
    assert source["title"] == "fixture.csv" and source["provenance"]["declared_source"]
    # Identical user IDs from another library never share a source or claim identity.
    other_tid, _ = task.record_version(core, spec(), by=BY)
    other = bundle(library="another-library").materialize(core, other_tid, by=BY)
    assert set(c["claim_id"] for c in pin["claims"]).isdisjoint(c["claim_id"] for c in other["claims"])


def test_unmapped_or_ambiguous_hard_requirement_returns_answerable_unknowns():
    uploaded, context = bundle(), spec()
    context["constraints"][0].pop("conditions")
    pending = uploaded.validate_task(context)
    assert len(pending) == 1 and pending[0]["blocking"] and pending[0]["resolution_state"] == "open"
    with pytest.raises(UploadedRequirementsPending):
        uploaded.objective_templates(context)
    context["constraints"][0]["conditions"] = {"temperature": "25 C"}
    assert uploaded.validate_task(context) == []
    context["constraints"][0]["property_id"] = "not-present"
    assert uploaded.validate_task(context)[0]["field"] == "constraints[0]"
    assert uploaded.validate_task({"constraints": []}) == []  # no invented hard gate
    assert uploaded.objective_templates({"constraints": []}) == []


def test_literal_user_requirement_enters_normal_task_review_route(core):
    uploaded = bundle()
    tid, _ = task.record_version(core, spec(), by=BY)
    added = derivation.objective_criteria(core, tid, templates=uploaded.objective_templates, by=BY)
    from mas.core import criteria
    rule = criteria.load(core, added[0]["rule_ref"], tid)
    attr = criteria.load(core, added[0]["attribute_ref"], tid)
    assert adjudication.restated_constraint(rule, attr, task.get(core, tid))["field"] == "constraints[0]"
    assert attr["proposed_by"]["role"] == "adapter_template"


def test_explicit_upload_manifest_opens_new_generation_with_no_source_runs(core):
    uploaded = bundle()
    tid, _ = task.record_version(core, spec(), by=BY)
    pin = uploaded.materialize(core, tid, by=BY)
    adapter = ScriptedAdapter("local", lambda request: {"proposals": [], "considered_and_rejected": []})
    roster = ModelRoster({"local": adapter}, {role: "local" for role in ("proposer", "critic", "adjudicator")})
    result = existing_research.derive(core, roster, tid, source_task_id=None,
        evidence_manifest_ref=pin["evidence_manifest_ref"], claims=pin["claims"],
        dimensions=DIMENSIONS, catalog=uploaded.catalog(), templates=lambda context: [], by=BY,
        settings=config.resolve(project_file=None, environ={}), implementation={"source_sha256": "fixture"}, budget=None)
    from mas.core import derivation_run
    binding = derivation_run._binding_of(core, result["run_id"])
    assert binding["source_task_id"] is None and binding["evidence_manifest_ref"] == pin["evidence_manifest_ref"]
    assert result["evidence"]["documents_read"] == result["evidence"]["new_searches"] == 0
    assert len(adapter.requests) == 1
    changed = deepcopy(pin["claims"])
    changed[0]["value"] = 999
    with pytest.raises(ValueError, match="Supplied claims differ"):
        existing_research._explicit_evidence(core, pin["evidence_manifest_ref"], changed)


def scope_spec(*, direction=None):
    result = spec()
    result["scope_entities"] = [{"entity_kind": "property", "role": "required", "label": "DLS size",
        "identifier_scheme": "uploaded_property", "identifier": "size", "property_id": "size",
        "conditions": {"temperature": "25 C"}, "unit": "nm", "direction": direction}]
    return result


def test_required_observation_and_same_property_hard_requirement_both_freeze_and_evaluate(core):
    from mas.core import criteria, derivation_run, leaderboard, measurement, review
    from mas.core.broker import Broker
    from mas.core.controller import RunController
    uploaded, context = bundle(), scope_spec()
    assert uploaded.validate_task(context) == []
    tid, _ = task.record_version(core, context, by=BY)
    uploaded.materialize(core, tid, by=BY)
    added = derivation.objective_criteria(core, tid, templates=uploaded.objective_templates, by=BY)
    assert [item["rule_kind"] for item in added] == ["exploratory_consideration", "hard_exclusion"]
    assert derivation.objective_criteria(core, tid, templates=uploaded.objective_templates, by=BY) == []
    proof = derivation_run.required_binding_audit(core, tid)
    assert proof["preserves_original_bindings"] and proof["task_scope_fully_bound"]
    assert proof["required_scope_count"] == 1
    pending = list(review.items(core, [tid]).values())
    assert len(pending) == 1  # literal hard constraint only; no fabricated scope approval
    adjudication.adjudicate(core, pending[0], qualification_policy="qualification_first_v1")
    frozen = measurement.prepare(core, tid, by=BY, primary_board="Synthetic uploaded observation",
        rationale="Verify property scope availability", expected_effect="Only direct observations satisfy scope",
        defer_capabilities=(), rank_requires_mandated_coverage=True)
    broker = Broker(core)
    uploaded.register(broker)
    ctl = RunController(core, broker, adapter=ADAPTER, identity_hook=uploaded.identity_hook,
        evidence_hook=uploaded.evidence_hook, evidence_manifest=uploaded.manifest())
    run = ctl.start(tid, by=BY, measurement_profile_ref=frozen["measurement_profile_ref"])
    board = leaderboard.snapshots(core, tid)[-1]
    entries = {row["candidate_ref"]: row for row in board["candidate_entries"]}
    assert entries["sample-1"]["qualification_state"] == "qualified"
    assert entries["sample-2"]["qualification_state"] == "pending"  # prediction only
    assert entries["sample-3"]["qualification_state"] == "pending"  # missing
    cells = [core.artifacts.payload(event.payload["artifact_id"]) for event in core.journal.replay(run)
             if event.event_type == "candidate.assessed"]
    observed = next(cell for cell in cells if cell["candidate_ref"] == "sample-1"
                    and cell["rule_kind"] == "exploratory_consideration")
    assert observed["verdict"] == "available" and observed["value"] == 0.
    assert assessor.direct_evidence(observed)
    scores = assessor.preference_scores({"sample-1": [observed]}, {}, {},
        qualified_candidates={"sample-1"}, qualification_policy="qualification_first_v1")
    assert scores["sample-1"] == (None, 0.)


def test_recorded_observation_is_opt_in_with_conflicts_and_no_invented_hard_gate(core):
    from mas.core import criteria
    uploaded, context = bundle(), scope_spec()
    tid, _ = task.record_version(core, context, by=BY)
    uploaded.materialize(core, tid, by=BY)
    template = uploaded.objective_templates(context)[0]
    attr = dict(template["attribute"], version=1)
    rule = dict(template["rule"], version=1)
    claims = uploaded.claims_for("sample-1", attribute=attr)
    def assess(chosen_rule, rows):
        return assessor.assess_cell(candidate={"candidate_id": "sample-1"}, attribute=attr, rule=chosen_rule,
            rule_set_ref="rules_fixture@v1", claims=rows, resolved=True, qualification_policy="qualification_first_v1")[0]
    assert assess(rule, [])["verdict"] == "unknown_missing"
    old = dict(rule, predicate_form="qualitative_judgment")
    assert assess(old, claims)["verdict"] == "unknown_missing"  # existing rule semantics stay intact
    conflict = dict(claims[0], claim_id="claim_conflicting_observation", value=1.)
    cell = assess(rule, [*claims, conflict])
    assert cell["verdict"] == "unknown_conflicted" and cell["value"] is None
    assert len(cell["value_source_claim_refs"]) == 2
    single = assess(rule, claims)
    status = assessor.qualification([single], hard_rule_refs=[], required_rule_refs=[single["rule_ref"]],
        verified_hard_rule_refs=[])
    assert status["state"] == "not_ready" and status["required_direct_answered"] == 1
    category_context = scope_spec()
    category_context["scope_entities"][0].update(identifier="hazard", property_id="hazard", unit=None, conditions={})
    category = uploaded.objective_templates(category_context)[0]
    category_attr = dict(category["attribute"], version=1)
    category_cell, _ = assessor.assess_cell(candidate={"candidate_id": "sample-1"},
        attribute=category_attr, rule=dict(category["rule"], version=1), rule_set_ref="rules_fixture@v1",
        claims=uploaded.claims_for("sample-1", attribute=category_attr), resolved=True,
        qualification_policy="qualification_first_v1")
    assert category_cell["verdict"] == "available" and category_cell["value"] is False
    assert assessor.direct_evidence(category_cell)
    for invalid in (dict(rule, rule_kind="preference"), dict(rule, rule_kind="hard_exclusion"),
                    dict(rule, cutoff={"value": 1, "comparator": "<=", "unit": "nm"})):
        with pytest.raises(criteria.InvariantViolation, match="recorded_observation"):
            criteria.check_rule(invalid, attr)


def test_uploaded_scope_mapping_accepts_explicit_direction_and_asks_for_bad_bindings():
    uploaded, context = bundle(), scope_spec(direction="lower_better")
    item = uploaded.objective_templates(context)[0]
    assert item["rule"]["rule_kind"] == "preference" and item["rule"]["predicate_form"] == "ordering"
    assert item["rule"]["cutoff"] is None and item["attribute"]["direction"] == "lower_better"
    entity = context["scope_entities"][0]
    entity["conditions"] = {"temperature": "unrecorded"}
    assert uploaded.validate_task(context)[0]["field"] == "scope_entities[0]"
    entity["conditions"] = {"temperature": "25 C"}
    entity["identifier"] = "some-other-property"
    assert "exact uploaded property_id" in uploaded.validate_task(context)[0]["question"]


def test_description_string_route_recovers_exact_recorded_conditions_without_changing_facts(core):
    from mas.core.broker import Broker
    from mas.core.uploaded_evidence import ROUTE_ENCODING_VERSION
    original = bundle()
    rows = deepcopy(original.measurements)
    description = "DLS; aqueous dispersion; 25 C"  # format observed in the completed GUI study
    rows[0]["conditions"] = {"description": description}
    uploaded = UploadedEvidence(original.candidates, rows, library_id=original.library_id,
        dataset_sha256=original.dataset_sha256, source_provenance=original.source_provenance)
    tid, _ = task.record_version(core, spec(), by=BY)
    pin = uploaded.materialize(core, tid, by=BY)
    manifest, last_seq = uploaded.manifest(), core.journal.last_seq(tid)
    attr = {"attribute_id": "attr_format", "version": 1, "name": "Recorded size", "measurement_kind": "quantitative",
        "direction": "lower_better", "unit": "nm", "aggregation": "consensus",
        "acceptable_value_sources": ["user_supplied_document"], "acceptable_determination_bases": ["measured"],
        "evidence_request": {"capability": "uploaded_measurement_lookup", "question_kind": "measurement",
                             "parameters": {"property": "size", "conditions": description}}}
    text_claims, _, _ = uploaded.evidence_hook({"candidate_id": "sample-1", "attribute": attr})
    object_attr = deepcopy(attr)
    object_attr["evidence_request"]["parameters"]["conditions"] = {"description": description}
    object_claims = uploaded.claims_for("sample-1", attribute_ref="attr_format@v1", attribute=object_attr)
    assert text_claims == object_claims and len(text_claims) == 1
    changed_text = deepcopy(attr)
    changed_text["evidence_request"]["parameters"]["conditions"] += " "
    assert uploaded.claims_for("sample-1", attribute=changed_text) == []
    cell, _ = assessor.assess_cell(candidate={"candidate_id": "sample-1"}, attribute=attr,
        rule={"rule_id": "rule_format", "version": 1, "rule_kind": "preference", "predicate_form": "ordering",
              "cutoff": None, "cutoff_basis": "none_evidence_insufficient"},
        rule_set_ref="rules_fixture@v1", claims=text_claims, resolved=True, qualification_policy="qualification_first_v1")
    assert cell["verdict"] == "available" and cell["value"] == 0.
    assert uploaded.manifest() == manifest and core.journal.last_seq(tid) == last_seq
    assert uploaded.materialize(core, tid, by=BY) == pin
    assert "route_encoding_version" not in manifest  # facts have not changed
    broker = Broker(core)
    uploaded.register(broker)
    assert uploaded.route_encoding_version == ROUTE_ENCODING_VERSION
    assert ROUTE_ENCODING_VERSION in broker.contracts()[0].implementation_version
    assert isinstance(uploaded.catalog()[0]["parameters"]["conditions"], dict)


def test_condition_shorthand_never_discards_other_experimental_fields_or_fuzzes_text(core):
    original = bundle()
    rows = deepcopy(original.measurements)
    description = "DLS; aqueous dispersion; 25 C"
    rows[0]["conditions"] = {"description": description, "pH": 7.4}
    uploaded = UploadedEvidence(original.candidates, rows, library_id=original.library_id,
        dataset_sha256=original.dataset_sha256)
    tid, _ = task.record_version(core, spec(), by=BY)
    uploaded.materialize(core, tid, by=BY)
    def lookup(condition):
        return uploaded.claims_for("sample-1", attribute={"evidence_request": {
            "capability": "uploaded_measurement_lookup", "question_kind": "measurement",
            "parameters": {"property": "size", "conditions": condition}}})
    assert not lookup(description)  # would omit pH
    assert len(lookup({"pH": 7.4, "description": description})) == 1
    assert not lookup({"pH": 7.0, "description": description})
    assert not lookup({"pH": 7.4, "description": description + " "})
    assert not lookup([description])
