"""Synthetic regressions for task anchors, legacy reduction output and append-only repair."""

import json

import pytest

from mas.core import assessor, criteria, criteria_export, derivation_run, derivation_stages, freeze, measurement, pool, staging, task
from mas.core.journal import actor
from mas.core.runtime import Core

from test_criteria_pool import CHEMBL_POTENCY, EVIDENCE_CATALOG, ORDERING, OPERATOR, SPEC, roster_for
from test_criteria_pool import lit_attribute

TEMPLATE = actor("system", "synthetic-required-templates", "adapter_template")
PROPOSER = actor("agent", "synthetic-reviser", "proposer")


def _required_task(core, *, research_parent=False):
    spec = dict(SPEC, scope_entities=[{"entity_kind": "target", "identifier": f"SYNTH_TARGET_{i}",
                                     "label": f"Synthetic receptor {i}", "role": "required"} for i in range(5)])
    source, _ = task.record_version(core, spec, by=OPERATOR)
    source_run = "run_synthetic_original_requirements"
    source_binding = core.artifacts.put("run_binding", {"run_purpose": "criteria_derivation",
        "task_context_id@v": f"{source}@v1", "chain_id": "chain_synthetic_requirements"})
    core.journal.append(source_run, "run.created", actor=OPERATOR, state_to="queued",
                        payload={"binding_artifact_id": source_binding})
    refs = []
    for i in range(5):
        route = dict(CHEMBL_POTENCY["evidence_request"], parameters={"target_chembl_id": f"SYNTH_TARGET_{i}"})
        attribute = dict(CHEMBL_POTENCY, name=f"Synthetic receptor {i} required potency",
                         definition=f"Median curated pChEMBL at synthetic receptor {i}", evidence_request=route,
                         derived_from={"task_context": f"{source}@v1", "field": f"scope_entities[{i}]"})
        refs.append(criteria.propose(core, source, attribute, ORDERING, by=TEMPLATE))
    research = None
    if research_parent:
        attribute = criteria.load(core, refs[-1][0], source)
        attribute = {key: value for key, value in attribute.items() if key not in
                     ("attribute_id", "version", "status", "proposed_by")}
        attribute.update(name="Synthetic research counterpart", derived_from={"derivation_run": source_run})
        research = criteria.propose(core, source, attribute, ORDERING, by=PROPOSER)
    child = staging.inherit_task(core, source, by=OPERATOR, reason="Synthetic required-binding regression")
    return child, source_run, refs, research


def _source(core, task_id, pair):
    registry = criteria_export._registry(core, task_id)
    attribute_ref, rule_ref = pair
    return {"attribute_ref": attribute_ref, "rule_ref": rule_ref,
            "attribute_artifact_id": registry[attribute_ref]["artifact_id"],
            "rule_artifact_id": registry[rule_ref]["artifact_id"],
            "attribute_sha256": criteria_export._artifact_hash(core, registry[attribute_ref]["artifact_id"]),
            "rule_sha256": criteria_export._artifact_hash(core, registry[rule_ref]["artifact_id"]),
            "task_mandated": criteria.is_task_mandated(registry[attribute_ref]["record"])}


def _legacy_run(core, task_id, pairs):
    run_id = "run_synthetic_legacy_binding_loss"
    manifest = core.artifacts.put("registered_reduction_inputs", {
        "registered_inputs": [_source(core, task_id, pair) for pair in pairs],
        "source_runs": [], "claims": [], "backlog_pool_refs": []})
    binding = core.artifacts.put("run_binding", {"run_purpose": "criteria_derivation",
        "operation": "registered_reduction", "task_context_id@v": f"{task_id}@v1",
        "source_inputs_artifact_id": manifest})
    core.journal.append(run_id, "run.created", actor=OPERATOR, state_to="queued",
                        payload={"binding_artifact_id": binding})
    core.journal.append(run_id, "run.started", actor=OPERATOR, state_to="running")
    return run_id


def _finish(core, task_id, run_id):
    report = core.artifacts.put("derivation_record", {"task_id": task_id, "run_id": run_id,
        "registry_inventory": criteria.registry_inventory(core, task_id),
        "implementation": "synthetic legacy promotion path, before protected-task-bindings fix"})
    core.journal.append(run_id, "run.completed", actor=OPERATOR, state_to="completed",
                        termination_reason="round_limit_reached", payload={"derivation_record_artifact_id": report})
    return report


def _coverage_with_last_target_missing(core, task_id):
    cells, mandated = [], []
    for rule in criteria.registered_rule_records(core, task_id):
        attribute = criteria.load(core, rule["attribute_ref"], task_id)
        ref = f"{rule['rule_id']}@v{rule['version']}"
        if criteria.is_task_mandated(attribute):
            mandated.append(ref)
        last_target = any(route.get("parameters", {}).get("target_chembl_id") == "SYNTH_TARGET_4"
                          for route in criteria.evidence_routes(attribute))
        cells.append({"rule_ref": ref, "attribute_ref": rule["attribute_ref"], "rule_kind": "preference",
                      "verdict": "unknown_missing" if last_target else "pass"})
    return assessor.mandated_coverage(cells, mandated)


def test_future_reduce_protects_all_five_task_anchors_without_model_rewriting_or_retirement(core):
    child, source_run, pairs, _ = _required_task(core)
    def no_model_calls(request):
        raise AssertionError("task requirements must not enter research reduction")
    record = derivation_run.reduce_registered(core, roster_for(no_model_calls), child,
        source_run_ids=[source_run], catalog=EVIDENCE_CATALOG, by=OPERATOR,
        reason="Keep the five task requirements independent", inner_iterations=1)
    assert record["protected_input_count"] == 5
    assert record["required_anchor_policy"] == "protected_task_bindings_v1"
    assert criteria.registry_inventory(core, child)["active_registered_count"] == 5
    assert {r["attribute_ref"] for r in criteria.registered_rule_records(core, child)} == {p[0] for p in pairs}
    audit = derivation_run.required_binding_audit(core, child, record["run_id"])
    assert audit["ok"] and audit["active_scope_binding_count"] == audit["expected_scope_binding_count"] == 5


def test_legacy_revised_template_loses_coverage_identity_and_correction_restores_source_without_relabelling_agent(core):
    child, _, pairs, _ = _required_task(core)
    run_id = _legacy_run(core, child, pairs)
    source = _source(core, child, pairs[-1])
    attribute = criteria.load(core, pairs[-1][0], child)
    rule = criteria.load(core, pairs[-1][1], child)
    writer = pool.Pool(core, child, by=PROPOSER, run_id=run_id)
    criterion_id = writer.add({"attribute": dict(attribute, rationale="Synthetic revised wording"),
        "rule": rule, "supporting_claim_ids": [], "dimension": "target_coverage", "source_registry": [source],
        "expected_change": "same required receptor quantity", "falsification_test": "task scope remains the same"})
    ctx = derivation_stages.StageContext(core=core, roster=roster_for(lambda request: {"findings": []}),
        task_id=child, run_id=run_id, task_context=task.get(core, child), catalog=EVIDENCE_CATALOG,
        claims_by_id={}, reference_labels=[], pool=writer, registry_reduce=True, pool_scope={criterion_id},
        registry_input_refs={pairs[-1][0]})
    # The synthetic version has already passed critique; isolate the real promotion/identity path.
    ctx.critiques[(criterion_id, 1)] = []
    promoted = derivation_stages.promote(ctx, by_proposer=PROPOSER)["accepted"][0]
    bad_attribute_ref = promoted["attribute_ref"]
    assert criteria.load(core, bad_attribute_ref, child)["proposed_by"] == PROPOSER
    bad_coverage = _coverage_with_last_target_missing(core, child)
    assert bad_coverage["n"] == 4 and bad_coverage["coverage"] == 1.0
    old_report = _finish(core, child, run_id)
    old_hash = criteria_export._artifact_hash(core, old_report)
    old_run_seq = core.journal.last_seq(run_id)
    audit = derivation_run.required_binding_audit(core, child, run_id)
    assert audit["missing_source_attribute_refs"] == [pairs[-1][0]]
    correction = derivation_run.correct_required_bindings(core, child, run_id=run_id, by=OPERATOR,
                                                         reason="Restore the original five task anchors")
    assert correction["audit_after"]["ok"] and correction["requires_new_freeze"]
    assert _coverage_with_last_target_missing(core, child)["n"] == 5
    assert _coverage_with_last_target_missing(core, child)["coverage"] == .8
    restored = next(row for row in correction["actions"] if row["operation"] == "restore_parent")
    restored_attribute = criteria.load(core, restored["attribute_ref"], child)
    assert restored_attribute["proposed_by"] == TEMPLATE
    assert restored_attribute["required_binding_restoration"]["source"]["attribute_ref"] == pairs[-1][0]
    assert criteria.load(core, bad_attribute_ref, child)["proposed_by"] == PROPOSER
    assert criteria_export._artifact_hash(core, old_report) == old_hash
    assert core.journal.last_seq(run_id) == old_run_seq
    assert not any(e.event_type in ("human.review_decided", "decision.recorded") for e in core.journal.replay(child))
    task_seq = core.journal.last_seq(child)
    assert not derivation_run.correct_required_bindings(core, child, run_id=run_id, by=OPERATOR,
                                                        reason="Idempotent audit")["changed"]
    assert core.journal.last_seq(child) == task_seq


def test_multi_parent_correction_restores_the_nonprotected_branch_too(core):
    child, _, pairs, research = _required_task(core, research_parent=True)
    run_id = _legacy_run(core, child, pairs + [research])
    sources = [_source(core, child, pair) for pair in (pairs[-1], research)]
    attribute = criteria.load(core, pairs[-1][0], child)
    attribute = {key: value for key, value in attribute.items() if key not in
                 ("attribute_id", "version", "status", "proposed_by")}
    attribute.update(name="Synthetic mixed reduction", derived_from={"pool_criterion": "cri_synthetic_family",
                                                                    "derivation_run": run_id})
    _, bad_rule = criteria.propose(core, child, attribute,
        dict(ORDERING, registry_reduction={"run_id": run_id, "source_registry": sources}), by=PROPOSER)
    for source in sources:
        criteria.retire_rule(core, child, source["rule_ref"], by=PROPOSER,
                             reason="Synthetic legacy merge", superseded_by=bad_rule, reduction_run_id=run_id)
    _finish(core, child, run_id)
    result = derivation_run.correct_required_bindings(core, child, run_id=run_id, by=OPERATOR,
                                                     reason="Restore all affected parent branches")
    active_refs = {row["rule_ref"] for row in criteria.registry_inventory(core, child)["active"]}
    assert bad_rule not in active_refs
    assert pairs[-1][1] in active_refs and research[1] in active_refs
    assert len(active_refs) == 6 and result["audit_after"]["active_scope_binding_count"] == 5
    assert {row["source_rule_ref"] for row in result["actions"] if row["operation"] == "restore_parent"} == {
        pairs[-1][1], research[1]}


def test_corrector_refuses_to_touch_a_running_reduction(core):
    child, _, pairs, _ = _required_task(core)
    run_id = _legacy_run(core, child, pairs)
    task_seq = core.journal.last_seq(child)
    with pytest.raises(derivation_run.DerivationError, match="wait for"):
        derivation_run.correct_required_bindings(core, child, run_id=run_id, by=OPERATOR, reason="Must wait")
    assert core.journal.last_seq(child) == task_seq


def test_audit_checks_task_field_identity_instead_of_trusting_a_template_flag(core):
    child, _, pairs, _ = _required_task(core)
    run_id = _legacy_run(core, child, pairs)
    _finish(core, child, run_id)
    context = task.get(core, child)
    context["scope_entities"][0]["identifier"] = "DIFFERENT_SYNTHETIC_TARGET"
    task.record_version(core, context, by=OPERATOR, task_id=child)
    audit = derivation_run.required_binding_audit(core, child, run_id)
    assert audit["invalid_source_attribute_refs"] == [pairs[0][0]]
    assert audit["active_scope_binding_count"] == 4 and not audit["ok"]
    with pytest.raises(derivation_run.DerivationError, match="integrity failed"):
        derivation_run.correct_required_bindings(core, child, run_id=run_id, by=OPERATOR,
                                                 reason="Cannot invent an updated task binding")


@pytest.mark.parametrize("action", ["register", "prepare"])
def test_new_measurement_refuses_lost_required_identity_before_recording_a_profile(core, action):
    child, _, pairs, _ = _required_task(core)
    attribute = criteria.load(core, pairs[-1][0], child)
    rule = criteria.load(core, pairs[-1][1], child)
    criteria.propose(core, child, dict(attribute, derived_from={"pool_criterion": "cri_synthetic_lost_binding"}),
                     rule, by=PROPOSER)
    if action == "register":
        criteria.confirm_rule_set(core, child, by=OPERATOR, allow_pending=True)
    before = core.journal.last_seq(child)
    with pytest.raises(measurement.MeasurementError, match="required anchors"):
        getattr(measurement, action)(core, child, by=OPERATOR, primary_board="synthetic new policy",
                                    rationale="Keep task requirements", expected_effect="Preserve the denominator")
    assert core.journal.last_seq(child) == before


def test_prepare_and_register_keep_the_full_scope_population_and_legacy_profile_loading(core):
    child, _, _, _ = _required_task(core)
    result = measurement.prepare(core, child, by=OPERATOR, primary_board="synthetic full scope",
                                 rationale="Freeze all required receptors", expected_effect="Preserve five bindings")
    assert result["required_binding_check"]["required_scope_count"] == 5
    assert result["required_binding_check"]["scope_preference_count"] == 5
    record = measurement.load(core, child, result["measurement_profile_ref"])
    legacy_policy = dict(record["policy"])
    legacy_policy["scoring_policy"].pop("required_binding_check")
    legacy = freeze.register(core, child, by=OPERATOR, policy=legacy_policy)
    assert "required_binding_check" not in measurement.load(core, child, legacy)["policy"]["scoring_policy"]


def test_register_refuses_a_frozen_set_missing_an_active_required_anchor(core):
    child, _, _, _ = _required_task(core)
    ref = criteria.confirm_rule_set(core, child, by=OPERATOR, allow_pending=True)
    original = criteria.rule_set(core, child, ref)
    incomplete = dict(original, rule_set_ref="rules@v2", entries=original["entries"][:-1])
    artifact_id = core.artifacts.put("rule_set", incomplete)
    core.journal.append(child, "criterion.version_approved", actor=OPERATOR,
                        payload={"rule_set_ref": "rules@v2", "artifact_id": artifact_id})
    before = core.journal.last_seq(child)
    with pytest.raises(measurement.MeasurementError, match="denominator would shrink"):
        measurement.register(core, child, by=OPERATOR, primary_board="synthetic incomplete scope",
                             rationale="Must refuse", expected_effect="Do not shrink the task population")
    assert core.journal.last_seq(child) == before


def test_prepare_refuses_deferring_all_required_routes_before_confirming_rules(core):
    child, _, _, _ = _required_task(core)
    before = core.journal.last_seq(child)
    with pytest.raises(measurement.MeasurementError, match="every route"):
        measurement.prepare(core, child, by=OPERATOR, primary_board="synthetic deferred scope",
                            rationale="Must refuse", expected_effect="Keep the task requirements",
                            defer_capabilities=("interaction_evidence_lookup",))
    assert core.journal.last_seq(child) == before


def test_prepare_preserves_active_non_scope_anchor_while_explicitly_deferring_its_literature_route(core):
    child, _, _, _ = _required_task(core)
    context = task.get(core, child)
    context["constraints"] = [{"kind": "route", "text": "oral administration", "hardness": "hard"}]
    task.record_version(core, context, by=OPERATOR, task_id=child)
    attribute = dict(lit_attribute("Synthetic oral literature measurement", "%"),
                     derived_from={"task_context": f"{child}@v2", "field": "constraints[0]"})
    _, gate_ref = criteria.propose(core, child, attribute,
                                  dict(ORDERING, rule_kind="exploratory_consideration",
                                       predicate_form="qualitative_judgment"), by=TEMPLATE)
    result = measurement.prepare(core, child, by=OPERATOR, primary_board="synthetic scope and deferred literature",
                                 rationale="Preserve anchors while deferring literature", expected_effect="Five receptor denominator")
    proof = result["required_binding_check"]
    assert proof["required_scope_count"] == proof["scope_preference_count"] == 5
    gate = next(row for row in proof["non_scope_required_anchors"] if row["rule_ref"] == gate_ref)
    assert gate["freeze_state"] == "deferred"
    assert gate["deferred"][0]["scope"] == "rule" and gate["deferred"][0]["scores_on"] == []
    assert criteria.registry_inventory(core, child)["active_registered_count"] == 6
    frozen = criteria.rule_set(core, child, result["rule_set_ref"])
    assert len(frozen["entries"]) == 5 and gate_ref in {row["rule_ref"] for row in frozen["deferred"]}


def test_bindings_cli_audits_read_only_and_restores_idempotently(tmp_path, capsys):
    from mas.cli.main import main

    root = tmp_path / "cli-bindings"
    with Core.open(root) as core:
        child, _, pairs, _ = _required_task(core)
        run_id = _legacy_run(core, child, pairs)
        _finish(core, child, run_id)
        before = core.journal.last_seq(child)
        # A live writer may hold the lock while the audit opens a read-only connection.
        main(["--store", str(root), "criteria", "audit-bindings", child, "--source-run", run_id])
        assert json.loads(capsys.readouterr().out)["ok"]
        assert core.journal.last_seq(child) == before
    main(["--store", str(root), "criteria", "restore-bindings", child, "--source-run", run_id,
          "--reason", "Synthetic terminal audit requires no correction"])
    assert not json.loads(capsys.readouterr().out)["changed"]
    with Core.open(root, read_only=True) as core:
        assert core.journal.last_seq(child) == before
