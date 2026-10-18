"""Existing-evidence registry reduction; synthetic claims and scripted models only."""

import json
from collections import Counter
from copy import deepcopy

import pytest

from mas.core import criteria, criteria_export, derivation_run, derivation_stages, ledger, pool, review, staging, task
from mas.core.journal import actor
from mas.core.models import ModelError

from test_criteria_pool import (CHEMBL_POTENCY, GTOPDB_AFFINITY, ORDERING, OPERATOR, SPEC,
                                EVIDENCE_CATALOG, merge_script, pool_of, roster_for)
from test_adjudication import ROUTE, ROUTE_RULE


def test_round_printing_accepts_saved_unchanged_registry_entries_without_a_rule_kind(capsys):
    from mas.cli.main import _print_round

    record = {"run_id": "run_synthetic_printing", "round_index": 1,
              "termination_reason": "round_limit_reached", "pool_states": {"promoted": 2},
              "promotion": {"accepted": [
                  {"rule_ref": "rule_new@v1", "rule_kind": "preference", "name": "New synthetic endpoint"},
                  {"rule_ref": "rule_existing@v1", "attribute_ref": "attr_existing@v1",
                   "retained_unchanged": True, "name": "Existing synthetic endpoint"}],
                  "deferred": [{"name": "Unresolved synthetic endpoint", "problems": ["Needs review"]}]},
              "continuation_decision": {"decision": "stop"}}
    before = deepcopy(record)
    _print_round(record)
    out = capsys.readouterr().out
    assert "accepted" in out and "preference" in out and "New synthetic endpoint" in out
    assert "retained" in out and "unchanged" in out and "Existing synthetic endpoint" in out
    assert "deferred  Unresolved synthetic endpoint: Needs review" in out
    assert "next: stop" in out and record == before


def test_model_view_preserves_scientific_semantics_and_refs_without_copying_registry_history():
    item = {"attribute": dict(CHEMBL_POTENCY, attribute_id="attr_synthetic", version=3,
                              copied_from={"history": "long immutable provenance"}, inherited_by=OPERATOR,
                              proposed_by=OPERATOR, status="proposed"),
            "rule": dict(ORDERING, rule_id="rule_synthetic", version=4, proposed_by=OPERATOR,
                         copied_from={"history": "long immutable provenance"},
                         applies_to_result_kind=["curated_measurement"],
                         dissent=[{"finding": "Keep the distinct biological endpoint", "referent": "claim_synthetic"}]),
            "supporting_claim_ids": ["claim_synthetic"], "expected_change": "same endpoint", "falsification_test": "same test"}
    original = deepcopy(item)
    view = derivation_stages._view({"item": item, "criterion_id": "cri_synthetic", "version": 2}, 0)
    assert all(view["attribute"][field] == item["attribute"][field] for field in derivation_stages.ATTRIBUTE_FIELDS
               if field in item["attribute"])
    assert view["rule"]["dissent"] == item["rule"]["dissent"]
    assert view["rule"]["applies_to_result_kind"] == item["rule"]["applies_to_result_kind"]
    assert view["refs"] == {"pool_ref": "cri_synthetic@v2", "attribute_ref": "attr_synthetic@v3", "rule_ref": "rule_synthetic@v4"}
    assert not any(key in view["attribute"] or key in view["rule"] for key in
                   ("copied_from", "inherited_by", "proposed_by", "status", "version"))
    assert item == original
    assert "rationale" not in derivation_stages._view({"item": item}, 0, blind=True)["attribute"]


def test_smaller_refine_batches_traverse_every_item_without_truncating_the_pool(core):
    sizes, seen = [], []
    def script(request):
        notes = json.loads(request.messages[0]["content"].split("Proposals to revise or withdraw:\n", 1)[1]
                           .split("\n\nCited claims:", 1)[0])
        sizes.append(len(notes))
        seen.extend(c for note in notes for c in note["supporting_claim_ids"])
        return {"revisions": [{"index": note["index"], "action": "revise", "proposal": note,
                               "reason": "Synthetic wording already resolves the finding"} for note in notes]}
    ids = [f"claim_batch_{i}" for i in range(19)]
    ctx = pool_of(core, script, [(claim_id, CHEMBL_POTENCY) for claim_id in ids],
                  task_id="task_smaller_batches", run_id="run_smaller_batches")
    for entry in pool.fold(core, ctx.task_id).values():
        ctx.pool.set_state(entry, "needs_refine", operation="revise", reason_kind="synthetic_findings")
    result = derivation_stages.refine_stage(ctx, 1)
    assert sizes == [8, 8, 3] and result["revised"] == 19
    # Pool order follows criterion IDs; IDs created within one millisecond need
    # not follow insertion order. Every proposal must still be visited once.
    assert Counter(seen) == Counter(ids)
    assert all(entry["state"] == "candidate" for entry in pool.fold(core, ctx.task_id).values())


def test_claim_routes_use_semantic_multilabels_and_share_unclassified_evidence():
    dimensions = [{"dimension": "target_coverage"}, {"dimension": "toxicological_safety"}]
    claims = [{"claim_id": "claim_tox", "attribute_hint": "toxicological_safety"},
              {"claim_id": "claim_both", "attribute_hint": "target coverage and toxicological safety"},
              {"claim_id": "claim_structured", "assessment_dimensions": ["target_coverage"]},
              {"claim_id": "claim_unknown", "attribute_hint": "an unclassified property"}]
    log = []
    routed = derivation_run._route_claims(claims + claims[:1], dimensions, routing_log=log)
    assert [c["claim_id"] for c in routed["target_coverage"]] == [
        "claim_both", "claim_structured", "claim_unknown"]
    assert [c["claim_id"] for c in routed["toxicological_safety"]] == [
        "claim_tox", "claim_both", "claim_unknown"]
    assert len(log) == 4 and log[-1]["reason"] == "shared_unclassified"


def test_different_decision_on_one_quantity_is_retained_without_a_second_scoring_quantity(core):
    source_rule = dict(ORDERING, on_missing="unknown_blocks_recommendation")
    criteria.propose(core, "task_decision", CHEMBL_POTENCY, source_rule, by=OPERATOR)
    ctx = pool_of(core, lambda request: {"findings": []}, [("claim_synthetic", CHEMBL_POTENCY)],
                  task_id="task_decision", run_id="run_decision")
    entry = next(iter(pool.fold(core, ctx.task_id).values()))
    revised = dict(entry["item"], rule=dict(entry["item"]["rule"], on_missing="unknown_no_penalty"))
    ctx.pool.revise(entry, revised, reason_text="different missing-data decision")
    registered = criteria.registered_attributes(core, ctx.task_id)
    rules = criteria.registered_rule_records(core, ctx.task_id)
    threshold = dict(source_rule, predicate_form="threshold", cutoff_basis="source_stated_value",
                     cutoff={"comparator": ">=", "value": 8, "unit": "pChEMBL"})
    assert derivation_stages.duplicate_of_registered(CHEMBL_POTENCY, registered, rule=threshold,
                                                     registered_rules=rules) is None
    assert derivation_stages.filter_stage(ctx, 1)["filtered_out"] == 0
    outcome = derivation_stages.promote(ctx, by_proposer=OPERATOR)
    assert len(outcome["deferred"]) == 1
    assert "decision_semantics_unresolved" in outcome["deferred"][0]["problems"][0]
    assert len(criteria.registered_rule_records(core, ctx.task_id)) == 1


def test_deferred_entries_reenter_without_resetting_the_refinement_budget(core):
    ctx = pool_of(core, lambda request: {"findings": []}, [("claim_synthetic", CHEMBL_POTENCY)],
                  task_id="task_reenter", run_id="run_reenter")
    entry = next(iter(pool.fold(core, ctx.task_id).values()))
    ctx.pool.revise(entry, dict(entry["item"], refine_count=2), state="deferred_next_round",
                    reason_text="deferred before a validator repair")
    stage = derivation_run._stage_recorder(core, ctx.task_id, ctx.run_id, {})
    derivation_run._prune(ctx, stage, [], stage_names=("filter",), inner_iterations=1,
                          stall_rounds=1, merge_overlap=.35)
    after = pool.fold(core, ctx.task_id)[entry["criterion_id"]]
    assert after["state"] == "candidate" and after["item"]["refine_count"] == 2
    assert any(change["reason_kind"] == "deferred_reentered" for change in after["history"])


def test_null_proposal_is_valid_for_withdraw_and_cannot_silently_withdraw_a_revision(core):
    input_refs = {}
    def script(request):
        notes = json.loads(request.messages[0]["content"].split("Proposals to revise or withdraw:\n", 1)[1]
                           .split("\n\nCited claims:", 1)[0])
        input_refs.update({note["index"]: note["refs"]["pool_ref"] for note in notes})
        return {"revisions": [{"index": 0, "action": "withdraw", "proposal": None, "reason": "explicit withdrawal"},
                              {"index": 1, "action": "revise", "proposal": None, "reason": "incomplete revision"}]}
    ctx = pool_of(core, script, [("claim_first", CHEMBL_POTENCY), ("claim_second", GTOPDB_AFFINITY)],
                  task_id="task_null_revision", run_id="run_null_revision")
    entries = list(pool.fold(core, ctx.task_id).values())
    for entry in entries:
        ctx.pool.set_state(entry, "needs_refine", operation="revise", reason_kind="synthetic_findings")
    result = derivation_stages.refine_stage(ctx, 1)
    assert result["withdrawn"] == 1 and result["refused"] == 1
    assert set(input_refs) == {0, 1}
    folded = pool.fold(core, ctx.task_id)
    assert len(folded) == 2
    assert folded[input_refs[0].rsplit("@v", 1)[0]]["state"] == "withdrawn"
    assert folded[input_refs[1].rsplit("@v", 1)[0]]["state"] == "needs_refine"
    assert {f"{item['criterion_id']}@v{item['version']}" for item in result["not_revised"]} == {input_refs[1]}


@pytest.mark.parametrize("stage", ["filter", "promote"])
def test_unusable_critic_batch_stays_unresolved_without_keyerror_or_automatic_acceptance(core, stage):
    def failed_critic(request):
        raise ModelError("parse_failed", "synthetic unusable critic reply")
    ctx = pool_of(core, failed_critic, [("claim_synthetic", CHEMBL_POTENCY)],
                  task_id="task_failed_critic", run_id="run_failed_critic")
    if stage == "filter":
        result = derivation_stages.filter_stage(ctx, 1)
        assert result["critique_items_unresolved"] == 1
    else:
        result = derivation_stages.promote(ctx, by_proposer=OPERATOR)
        assert result["accepted"] == [] and result["deferred"][0]["problems"] == ["critique_unresolved"]
    assert result["critique_batches_unresolved"] == 1
    (entry,) = pool.fold(core, ctx.task_id).values()
    assert entry["state"] == "deferred_next_round"
    assert not criteria.registered_rule_records(core, ctx.task_id)


def _source_and_child(core, *, pending=False):
    source, _ = task.record_version(core, dict(SPEC, constraints=[{
        "text": "oral administration", "kind": "route", "hardness": "hard", "provenance": "synthetic"}]), by=OPERATOR)
    run_id = "run_synthetic_existing_evidence"
    binding = core.artifacts.put("run_binding", {
        "run_purpose": "criteria_derivation", "task_context_id@v": f"{source}@v1", "chain_id": "chain_synthetic"})
    core.journal.append(run_id, "run.created", actor=OPERATOR, state_to="queued",
                        payload={"binding_artifact_id": binding})
    refs = []
    for index, attribute in enumerate((CHEMBL_POTENCY, GTOPDB_AFFINITY)):
        claim = ledger.record_claim(core, run_id, {
            "claim_id": f"claim_existing_{index}", "source_ref": f"src_synthetic_{index}",
            "location": {"location_kind": "paragraph", "locator_value": f"synthetic.{index}",
                         "quoted_span": "The synthetic receptor affinity is 8 pChEMBL."},
            "value": 8, "unit": "pChEMBL", "determination_basis": "measured",
            "evidence_kind": "curated_measurement", "polarity": "supports", "attribute_hint": "target_coverage"},
            by=OPERATOR, admission_state="admitted", admission_reasons=["quote_verified"])
        _, rule_ref = criteria.propose(core, source, dict(attribute, supporting_claim_refs=[claim],
                                                         derived_from={"derivation_run": run_id}),
                                      ORDERING, by=OPERATOR)
        refs.append(rule_ref)
    if pending:
        review.request(core, source, subject={"kind": "rule_version", "id": refs[0], "version": 1,
                                              "attribute_ref": "attr_csf1r-curated-potency@v1"},
                       why_expert_required="proposer and critic still disagree after one revision", requested_by=OPERATOR)
    core.journal.append(run_id, "run.failed", actor=OPERATOR, state_to="failed",
                        termination_reason="repeated_failure", payload={"error_class": "synthetic_provider_failure"})
    frozen_ref = criteria.confirm_rule_set(core, source, by=OPERATOR, allow_pending=True)
    source_last = core.journal.last_seq(source)
    child = staging.inherit_task(core, source, by=OPERATOR, reason="Synthetic registry reduction")
    return source, child, run_id, frozen_ref, source_last


def _reduce_script(*, combine=True, unresolved=False):
    def script(request):
        question = request.metadata.get("question")
        content = request.messages[0]["content"]
        if question in ("critique pool", "final check before promotion"):
            if unresolved:
                views = json.loads(content.split("Proposals:\n", 1)[1].split("\n\nCited claims:")[0])
                return {"findings": [{"proposal_index": view["index"], "check": "evidence_support",
                                      "verdict": "fail", "severity": "material", "referent": "attribute.definition",
                                      "finding": "Synthetic unresolved comparability question"} for view in views]}
            return {"findings": []}
        if question == "refine pool":
            views = json.loads(content.split("Proposals to revise or withdraw:\n", 1)[1].split("\n\nCited claims:")[0])
            return {"revisions": [{"index": view["index"], "action": "revise", "reason": "requires further review",
                                   "proposal": view} for view in views]}
        if question == "distill pool":
            views = json.loads(content.split("Items to distill:\n", 1)[1].split("\n\nCited claims:")[0])
            return {"items": [{"index": view["index"], "action": "keep", "reason": "preserve the quantity"}
                              for view in views]}
        if question == "adjudicate merges":
            if combine:
                return merge_script()(request)
            groups = json.loads(content.split("Groups:\n", 1)[1].split("\n\nCited claims:")[0])
            return {"decisions": [{"group": group["group"], "action": "keep_separate",
                                   "reason": "Synthetic decision remains unresolved"} for group in groups]}
        raise AssertionError(f"Unexpected stage: {question}")
    return script


def test_registry_reduction_uses_existing_failed_run_claims_retires_parents_and_freezes_only_active_rules(core):
    source, child, source_run, frozen_ref, source_last = _source_and_child(core)
    pinned_before = core.journal.last_seq(child)
    record = derivation_run.reduce_registered(core, roster_for(_reduce_script()), child,
                                               source_run_ids=[source_run], catalog=EVIDENCE_CATALOG,
                                               by=OPERATOR, reason="Remove duplicate synthetic curations", inner_iterations=1)
    inventory = record["registry_inventory"]
    assert inventory["active_registered_count"] == inventory["total_active_count"] == 1
    assert inventory["historical_registered_count"] == 3 and inventory["retired_latest_count"] == 2
    inputs = core.artifacts.payload(record["source_inputs_artifact_id"])
    assert inputs["source_runs"][0]["execution_state"] == "failed"
    assert len(inputs["claims"]) == 2 and all(claim["artifact_sha256"] for claim in inputs["claims"])
    assert record["reads_new_evidence"] is False and record["proposes_new_criteria"] is False
    frozen = criteria.confirm_rule_set(core, child, by=OPERATOR, allow_pending=True)
    assert len(criteria.rule_set(core, child, frozen)["entries"]) == 1
    summary = derivation_run.registered_reduction_summary(core, child)
    assert summary["total_active_count"] == summary["scoring_in_latest_frozen_set_count"] == 1
    assert summary["retired_by_this_run_count"] == 2 and summary["run_id"] == record["run_id"]
    current = criteria_export.snapshot(core, child, with_board=False)
    assert len(current["criteria"]) == 3  # historical cards remain reviewable
    assert current["counts"]["active_registered_criteria"]["value"] == 1
    assert current["counts"]["proposals_added_to_pool"]["value"] == 0
    assert current["counts"]["registered_reduction_inputs"]["value"] == 2
    assert current["recovery_comparison_set"]["included_count"] == 1
    assert len(current["recovery_comparison_set"]["excluded_as_retired"]) == 2
    prior = criteria_export.snapshot(core, child, at_seq=pinned_before, with_board=False)
    assert prior["registry_inventory"]["active_registered_count"] == 2
    assert prior["recovery_comparison_set"]["included_count"] == 2
    assert criteria.rule_set(core, source)["rule_set_ref"] == frozen_ref
    assert len(criteria.rule_set(core, source)["entries"]) == 2 and core.journal.last_seq(source) == source_last
    with pytest.raises(derivation_run.DerivationError, match="frozen reading"):
        derivation_run.reduce_registered(core, roster_for(_reduce_script()), child, source_run_ids=[source_run],
                                          catalog=EVIDENCE_CATALOG, by=OPERATOR, reason="Should refuse")


def test_unresolved_reduction_keeps_pending_originals_in_total_active_count(core):
    _, child, source_run, _, _ = _source_and_child(core, pending=True)
    record = derivation_run.reduce_registered(core, roster_for(_reduce_script(combine=False, unresolved=True)), child,
                                               source_run_ids=[source_run], catalog=EVIDENCE_CATALOG,
                                               by=OPERATOR, reason="Synthetic unresolved reduction", inner_iterations=1)
    summary = derivation_run.registered_reduction_summary(core, child, record["run_id"])
    assert summary["active_registered_count"] == summary["total_active_count"] == 2
    assert summary["pending_review_count"] == 1 and summary["unresolved_pool_count"] == 2
    assert summary["retired_by_this_run_count"] == 0 and summary["scoring_in_latest_frozen_set_count"] == 0


def test_automatic_sources_follow_the_inheritance_pin_and_ignore_later_source_runs(core):
    source, child, source_run, _, _ = _source_and_child(core)
    later = "run_later_uninherited"
    binding = core.artifacts.put("run_binding", {
        "run_purpose": "criteria_derivation", "task_context_id@v": f"{source}@v1", "chain_id": "chain_synthetic",
        "continues_run_id": source_run})
    core.journal.append(later, "run.created", actor=OPERATOR, payload={"binding_artifact_id": binding})
    core.journal.append(source, "run.continued", actor=OPERATOR,
                        payload={"run_id": later, "parent_run_id": source_run})
    assert derivation_run.registered_reduction_sources(core, child) == [source_run]


def test_task_mandated_input_without_literature_claims_is_retained_and_pending_is_counted(core):
    source, _, source_run, _, _ = _source_and_child(core)
    attribute = dict(ROUTE, derived_from={"task_context": f"{source}@v1", "field": "constraints[0].text"})
    _, rule_ref = criteria.propose(core, source, attribute, ROUTE_RULE,
                                   by=actor("system", "synthetic-task-template", "adapter_template"))
    child = staging.inherit_task(core, source, by=OPERATOR, reason="Synthetic task-mandated reduction")
    record = derivation_run.reduce_registered(core, roster_for(_reduce_script()), child,
                                               source_run_ids=[source_run], catalog=EVIDENCE_CATALOG,
                                               by=OPERATOR, reason="Retain task requirements", inner_iterations=1)
    summary = derivation_run.registered_reduction_summary(core, child, record["run_id"])
    assert rule_ref in {row["rule_ref"] for row in summary["active"]}
    assert summary["active_registered_count"] == summary["total_active_count"] == 2
    assert summary["pending_review_count"] == 1
