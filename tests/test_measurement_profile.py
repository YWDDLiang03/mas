"""Regressions for the coverage-floor wiring and the frozen profile boundary."""

import pytest

from mas.core import config, constants, criteria, leaderboard, measurement, task
from tests.test_run_end_to_end import OPERATOR, SPEC, make_controller, setup_task as _setup_descriptor_task


def setup_task(core):
    # These profile-wiring fixtures measure MW/bioavailability, not the unrelated placeholder T1.
    # Required-scope binding has dedicated regressions below.
    task_id = _setup_descriptor_task(core)
    context = task.get(core, task_id)
    context["scope_entities"] = []
    task.record_version(core, context, by=OPERATOR, task_id=task_id)
    return task_id


def _register(core, task_id, **kwargs):
    return measurement.register(
        core, task_id, by=OPERATOR, primary_board="registered full-universe board",
        rationale="Report rank and complete-task eligibility separately, as registered.",
        expected_effect="Unknown mandated cells remain visible without gating the rank.", **kwargs)


def _board(require_mandated):
    cells = {"candidate": [
        {"assessment_id": f"assess_{i}", "rule_ref": f"rule_{i}@v1", "attribute_ref": f"attr_{i}@v1",
         "rule_kind": "preference", "verdict": "pass" if i < 4 else "unknown_missing",
         "value_kind": "curated" if i < 4 else "missing", "conflicting_claim_refs": []}
        for i in range(5)]}
    roll = {"candidate": {"state": "provisional", "state_reason": "no confirmed hard rule",
                          "hard_rule_coverage": None, "blocking_unknowns": [], "n_fail_hard": 0,
                          "n_unknown_hard": 0}}
    return leaderboard.build_snapshot(
        task_context=dict(SPEC, task_context_id="task_synthetic", version=1), leaderboard_id="lbd_test",
        run_id="run_test", round_id="round_test", evidence_snapshot_id=None,
        rule_set={"rule_set_ref": "rules@v1", "entries": [
            {"rule_ref": f"rule_{i}@v1", "rule_kind": "preference"} for i in range(5)]},
        roll_ups=roll, cells=cells, scores={"candidate": (0.8, 0.8)}, identities={}, parent=None,
        sweep_completeness=1.0, budget={}, mandated_rule_refs=[f"rule_{i}@v1" for i in range(5)],
        mandated_coverage_floor=1.0, rank_requires_mandated_coverage=require_mandated)


def test_rank_can_be_reported_while_complete_mandated_eligibility_stays_false():
    legacy, registered = _board(True), _board(False)
    before, after = legacy["candidate_entries"][0], registered["candidate_entries"][0]
    assert before["position"] is None and after["position"] == 1
    for row in (before, after):
        assert row["clears_mandated_criteria"] is False
        assert row["mandated_coverage"] == 4 / 5
        assert row["mandated_blocked_by"] == ["attr_4@v1"]
    assert registered["reporting_tuple"]["ranking_coverage_floor"] == 0.5
    assert registered["reporting_tuple"]["mandated_coverage_floor"] == 1.0
    assert registered["reporting_tuple"]["rank_requires_mandated_coverage"] is False


def test_profile_is_bound_and_verified_on_the_published_board(core):
    task_id = setup_task(core)
    settings = config.resolve(project_file=None, environ={})
    ref = _register(core, task_id, settings=settings)
    controller = make_controller(core)
    run_id = controller.start(task_id, by=OPERATOR, settings=settings, measurement_profile_ref=ref)
    assert controller.current_state(run_id) == "completed"
    (board,) = leaderboard.snapshots(core, task_id)
    profile = board["measurement_profile"]
    assert profile["ref"] == ref and profile["verification"]["conforms"] is True
    assert profile["digest"] == measurement.digest(measurement.load(core, task_id, ref))
    assert board["reporting_tuple"]["rank_requires_mandated_coverage"] is False
    assert board["reporting_tuple"]["mandated_coverage_floor"] == 1.0


def test_changed_config_is_refused_before_creating_a_run(core):
    task_id = setup_task(core)
    settings = config.resolve(project_file=None, environ={})
    ref = _register(core, task_id, settings=settings)
    changed = config.resolve(project_file=None, environ={}, overrides={"rank.coverage_floor": 0.6})
    with pytest.raises(measurement.MeasurementError, match="profile drift"):
        make_controller(core).start(task_id, by=OPERATOR, settings=changed, measurement_profile_ref=ref)
    assert core.journal.streams("run_") == []


def test_bound_constant_drift_is_refused_before_execute(core):
    task_id = setup_task(core)
    ref = _register(core, task_id)
    controller = make_controller(core)
    run_id = controller.start(task_id, by=OPERATOR, execute=False, measurement_profile_ref=ref)
    constants.register(core, "const_mandated_coverage_floor", 0.0, unit="fraction", scope="case_configuration",
                       cutoff_basis="expert_set", set_by=OPERATOR, stream_id=run_id)
    with pytest.raises(measurement.MeasurementError, match="profile drift"):
        controller.execute(run_id)
    assert controller.current_state(run_id) == "queued"
    assert leaderboard.snapshots(core, task_id) == []


def test_reconfirming_rules_or_limiting_candidates_changes_the_frozen_instrument(core):
    task_id = setup_task(core)
    ref = _register(core, task_id)
    controller = make_controller(core)
    with pytest.raises(measurement.MeasurementError, match="candidate_scope"):
        controller.start(task_id, by=OPERATOR, execute=False, measurement_profile_ref=ref, candidate_limit=1)
    criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    with pytest.raises(measurement.MeasurementError, match="criteria_ref"):
        controller.start(task_id, by=OPERATOR, execute=False, measurement_profile_ref=ref)


def test_new_profile_never_rewrites_the_previous_policy(core):
    task_id = setup_task(core)
    first = _register(core, task_id)
    digest = measurement.digest(measurement.load(core, task_id, first))
    second = _register(core, task_id, ranking_coverage_floor=0.6)
    assert first != second
    assert measurement.digest(measurement.load(core, task_id, first)) == digest
    assert measurement.load(core, task_id, first)["policy"]["scoring_policy"]["ranking_coverage_floor"] == 0.5


def test_a_profile_names_one_run_and_an_interrupted_run_can_be_resumed(core):
    task_id = setup_task(core)
    ref = _register(core, task_id)
    controller = make_controller(core)
    run_id = controller.start(task_id, by=OPERATOR, execute=False, measurement_profile_ref=ref)
    with pytest.raises(measurement.MeasurementError, match=f"already bound to {run_id}"):
        controller.start(task_id, by=OPERATOR, execute=False, measurement_profile_ref=ref)
    assert controller.resume(run_id) == "completed"


def test_explicit_seed_and_cutoff_overrides_cannot_bypass_the_frozen_settings(core):
    task_id = setup_task(core)
    settings = config.resolve(project_file=None, environ={}, overrides={"run.seed": 3, "search.date_to": "2026-10-15"})
    ref = _register(core, task_id, settings=settings)
    controller = make_controller(core)
    with pytest.raises(measurement.MeasurementError, match="sweep_seed"):
        controller.start(task_id, by=OPERATOR, execute=False, settings=settings,
                         measurement_profile_ref=ref, sweep_seed=4)
    with pytest.raises(measurement.MeasurementError, match="evidence_cutoff"):
        controller.start(task_id, by=OPERATOR, execute=False, settings=settings,
                         measurement_profile_ref=ref, evidence_cutoff="2026-10-16")
    run_id = controller.start(task_id, by=OPERATOR, execute=False, settings=settings, measurement_profile_ref=ref)
    state = controller._load(run_id)
    assert state.binding["sweep_seed"] == 3 and state.binding["evidence_cutoff"] == "2026-10-15"
    state.binding["sweep_seed"] = 4
    with pytest.raises(measurement.MeasurementError, match="sweep_seed"):
        controller._measurement_profile(state)
    state.binding["sweep_seed"], state.binding["evidence_cutoff"] = 3, "2026-10-16"
    with pytest.raises(measurement.MeasurementError, match="evidence_cutoff"):
        controller._measurement_profile(state)
