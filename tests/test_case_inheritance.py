"""Case inheritance regressions use only the explicitly synthetic recovery fixtures."""

import pytest

from mas.core import adjudication, collapse, criteria, criteria_export, pool, recovery, review, staging, task
from mas.core.journal import actor

from test_recovery import EVALUATOR, OPERATOR, POTENCY, _default_mapping, _intake, _report, _seed
from test_adjudication import _grants, _interpreted, _item, _roster, _task


def test_full_inheritance_preserves_registry_versions_origin_scope_and_software_lifecycle(core):
    source = _seed(core)
    source_id = source["task_id"]
    pool.Pool(core, source_id, by=OPERATOR, run_id="run_synthetic_pool").add(
        {"attribute": POTENCY["attribute"], "rule": POTENCY["rule"],
         "dimension": "synthetic", "supporting_claim_ids": []}, reason_text="Synthetic pool provenance")
    collapse.collapse(core, source_id, by=OPERATOR, dry_run=False)
    pin = core.journal.last_seq(source_id)
    original_registry = criteria_export._registry(core, source_id)
    # A later source revision must not leak through an explicitly pinned inheritance.
    criteria.propose(core, source_id, dict(POTENCY["attribute"], name="Later synthetic criterion"),
                     dict(POTENCY["rule"]), by=OPERATOR)
    child = staging.inherit_task(core, source_id, by=OPERATOR, reason="A descriptive synthetic reading",
                                 source_at_seq=pin)
    context = task.get(core, child)
    original = task.get(core, source_id)
    for key in ("candidate_universe", "scope_entities", "constraints", "evaluation_scope"):
        assert context[key] == original[key]
    assert recovery.case_stream(core, child) != recovery.case_stream(core, source_id)
    assert context["inheritance"]["is_independent_validation"] is False
    copied_registry = criteria_export._registry(core, child)
    assert set(copied_registry) == set(original_registry)
    for ref, entry in original_registry.items():
        copied = copied_registry[ref]["record"]
        assert copied["proposed_by"] == entry["record"]["proposed_by"]
        assert copied["copied_from"]["artifact_id"] == entry["artifact_id"]
        assert copied["copied_from"]["artifact_sha256"] == criteria_export._artifact_hash(core, entry["artifact_id"])
        if entry["kind"] == "attribute":
            assert copied["derived_from"] == entry["record"]["derived_from"]
    inheritance = context["inheritance"]
    assert inheritance["source_snapshot_sha256"] == criteria_export._artifact_hash(
        core, inheritance["source_snapshot_artifact_id"])
    snapshot = core.artifacts.payload(inheritance["source_snapshot_artifact_id"])
    assert snapshot["source_at_seq"] == pin
    assert snapshot["source_rule_sets"][0]["rule_set_ref"] == source["rule_set_ref"]
    assert set(collapse.superseded_attributes(core, child)) == set(collapse.superseded_attributes(core, source_id))
    assert pool.fold(core, child) == pool.fold(criteria_export.pinned(core, source_id, pin)[0], source_id)
    events = list(core.journal.replay(child))
    assert not any(event.event_type in ("criterion.version_approved", "human.review_decided", "decision.recorded")
                   for event in events)
    assert all(item["state"] == "open" for item in review.items(core, [child]).values())
    with pytest.raises(recovery.RecoveryError, match="criteria_not_frozen"):
        recovery.frozen_snapshots(core, child)
    criteria.confirm_rule_set(core, child, by=OPERATOR, allow_pending=True)
    cards = criteria_export.snapshot(core, child, with_board=False)["criteria"]
    oral = next(card for card in cards if card["identity"]["attribute_ref"] == source["oral"])
    assert oral["origin"]["kind"] == "task_mandated_template"
    assert any(card["use"]["status"] == "collapsed_away" for card in cards)


def test_inherited_report_retains_original_reading_and_exposure_without_local_approvals(core):
    source = _seed(core, decide_exposure="exposed")
    intake = _intake(core, source)
    original = _report(core, source, _default_mapping(core, source, intake))
    child = staging.inherit_task(core, source["task_id"], by=OPERATOR,
                                 reason="A further descriptive reading of inherited criteria")
    inherited = task.get(core, child)["inheritance"]
    assert inherited["prior_recovery_readings"][0]["comparison_id"] == original["comparison_id"]
    assert inherited["prior_recovery_readings"][0]["counts"] == original["counts"]["categories"]
    criteria.confirm_rule_set(core, child, by=OPERATOR, allow_pending=True)
    child_refs = dict(source, task_id=child)
    child_intake = _intake(core, child_refs)
    child_report = _report(core, child_refs, _default_mapping(core, child_refs, child_intake))
    exposure = child_report["exposure"]
    assert exposure["reading_kind"] == "descriptive_inherited"
    assert exposure["recovery_view"] == "assisted" and not exposure["is_independent_validation"]
    assert exposure["inherited_from"][0]["task_id"] == source["task_id"]
    assert exposure["source_confirming_decisions"][0]["historical_list_exposure"] == "exposed"
    assert exposure["declared_on_confirming_decisions"] == {}
    assert not exposure["criteria_in_the_independent_view"]
    assert exposure["reads_logged"] > len(recovery.access_log(core, child))
    assert recovery.latest_comparison(core, source["task_id"])["comparison_id"] == original["comparison_id"]
    public = recovery.public_counts(child_report)
    assert public["exposure"]["reading_kind"] == "descriptive_inherited"
    assert "descriptive assisted reading" in recovery.render_counts(public)


def test_legacy_shortlist_follows_transitive_source_case_reads(core):
    source = _seed(core)
    _intake(core, source)
    child = staging.inherit_task(core, source["task_id"], by=OPERATOR, reason="Synthetic inheritance")
    board = {"snapshot_id": "lb_synthetic", "published_at": "2026-10-14T00:00:00Z", "rules@v": "rules@v1",
             "candidate_entries": [{"candidate_ref": "cand_ik-alpha", "position": 1, "preference_score": 1.0}]}
    artifact = core.artifacts.put("leaderboard_snapshot", board)
    core.journal.append("run_synthetic_board", "leaderboard.snapshot_published", actor=OPERATOR,
                        payload={"task_id": child, "snapshot_id": board["snapshot_id"], "artifact_id": artifact})
    grandchild = staging.shortlist_task(core, child, top_k=1, by=OPERATOR)
    # This access happens after inheritance; it must still taint the descendant's later freeze.
    core.journal.append(recovery.case_stream(core, source["task_id"]), "evaluator_only.read",
                        actor=actor("agent", "synthetic-coordinator", "coordinator"),
                        payload={"subject": "hci_synthetic", "purpose": "synthetic exposure regression"},
                        visibility="evaluator")
    derived = recovery.derived_set(core, grandchild)
    exposure = recovery.exposure_declaration(
        core, grandchild, derived=derived,
        intake={"freeze": {"frozen_at": "9999-01-01T00:00:00Z", "frozen_at_seq": derived["pinned_seq"]},
                "recorded_at": "9999-01-01T00:00:01Z"})
    assert [source_entry["task_id"] for source_entry in exposure["inherited_from"]] == [child, source["task_id"]]
    assert exposure["coordinator_or_deriving_agent_saw_the_list_before_the_freeze"] is True
    assert exposure["reads_by_a_deriving_role"][0]["source_task_id"] == source["task_id"]
    assert exposure["recovery_view"] == "assisted"


def test_compare_itself_refuses_remeasurement_and_a_different_pin_before_opening_the_intake(core):
    source = _seed(core)
    intake = _intake(core, source)
    task_id = source["task_id"]
    before = len(recovery.access_log(core, task_id))
    mapping = _default_mapping(core, source, intake)
    with pytest.raises(recovery.RecoveryError, match="comparison_pin_mismatch"):
        recovery.compare(core, task_id, by=EVALUATOR, mapping=mapping,
                         at_seq=intake["freeze"]["frozen_at_seq"] + 1)
    assert len(recovery.access_log(core, task_id)) == before
    first = recovery.compare(core, task_id, by=EVALUATOR, mapping=mapping)
    before = len(recovery.access_log(core, task_id))
    with pytest.raises(recovery.RecoveryError, match="comparison_already_recorded"):
        recovery.compare(core, task_id, by=EVALUATOR, mapping=mapping)
    assert len(recovery.access_log(core, task_id)) == before
    assert recovery.report(core, task_id, by=EVALUATOR)["comparison_id"] == first["comparison_id"]


@pytest.mark.parametrize("verdict,needs_review", [("grant_bound", True), ("refuse_bound", False)])
def test_resolved_source_authority_is_requeued_only_for_the_current_inherited_rule(core, verdict, needs_review):
    source_id = _task(core)
    rule_ref, _ = _interpreted(core, source_id)
    source_item = _item(core, source_id, rule_ref)
    decision = adjudication.adjudicate(core, source_item, roster=_roster(_grants(verdict)))
    assert review.items(core, [source_id])[source_item["item_id"]]["state"] == "machine_adjudicated"
    child = staging.inherit_task(core, source_id, by=OPERATOR, reason="Synthetic resolved-authority inheritance")
    queue = list(review.items(core, [child]).values())
    assert bool(queue) is needs_review
    if needs_review:
        (pending,) = queue
        assert pending["subject"]["id"] == rule_ref == decision["rule_ref_after"]
        assert pending["state"] == "open"
        assert pending["inspection_bundle"]["source_adjudication_id"] == decision["adjudication_id"]
        assert pending["inspection_bundle"]["source_authority_carried"] is False
        assert adjudication.records(core, child) == []
        # Reproduce a previously created case with copied records but no inherited review item.
        spec = {key: value for key, value in task.get(core, child).items()
                if key not in ("task_context_id", "version", "supersedes", "created_by")}
        spec["case_ref"] = "case_synthetic_legacy_repair"
        legacy, _ = task.record_version(core, spec, by=OPERATOR)
        source_rule = criteria.load(core, rule_ref, source_id)
        source_attribute = criteria.load(core, source_rule["attribute_ref"], source_id)
        criteria.propose(core, legacy, source_attribute, source_rule, by=OPERATOR)
        assert not review.items(core, [legacy])  # the support-dependent grant has no intrinsic trigger
        assert len(staging.restore_inherited_reviews(core, legacy, rule_refs=[rule_ref])) == 1
        assert next(iter(review.items(core, [legacy]).values()))["subject"]["id"] == rule_ref
        assert staging.restore_inherited_reviews(core, legacy, rule_refs=[rule_ref]) == []
    else:
        current = criteria.load(core, decision["rule_ref_after"], child)
        assert current["cutoff"] is None and current["version"] == 2
        assert staging.restore_inherited_reviews(core, child) == []
