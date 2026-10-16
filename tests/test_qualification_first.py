"""Synthetic checks for prospective qualification, execution parity and no-new-evidence hooks."""

from copy import deepcopy

import pytest

from mas.core import adjudication, assessor, criteria, leaderboard, ledger, measurement, review, task
from mas.core.broker import Broker, ProviderResponse, ToolContract
from mas.core.budget import Budget
from mas.core.controller import RunController, _ExistingFactsBroker
from mas.core.journal import actor
from tests.test_run_end_to_end import MW, MW_RULE, OPERATOR, EXPERT, SPEC
from test_criteria_pool import CHEMBL_POTENCY, ORDERING
from test_criteria_pool import roster_for
from test_adjudication import ROUTE, ROUTE_RULE

POLICY = assessor.QUALIFICATION_POLICY
TEMPLATE = actor("system", "synthetic-task-template", "adapter_template")
MEMBERS = ["alpha", "beta", "rejected", "unknown"]


def _fixture(core):
    context = dict(SPEC, candidate_universe={"kind": "enumerated_set", "members": MEMBERS}, seed_candidates=[],
                   scope_entities=[{"entity_kind": "target", "identifier": "SYNTH_TARGET", "role": "required"}])
    task_id, _ = task.record_version(core, context, by=OPERATOR)
    criteria.propose(core, task_id, MW, MW_RULE, by=OPERATOR)
    attr = dict(CHEMBL_POTENCY, derived_from={"task_context": f"{task_id}@v1", "field": "scope_entities[0]"},
                evidence_request=dict(CHEMBL_POTENCY["evidence_request"], parameters={"target_chembl_id": "SYNTH_TARGET"}))
    criteria.propose(core, task_id, attr, ORDERING, by=TEMPLATE)
    for item in review.items(core, [task_id]).values():
        review.decide(core, item, decision="approve", actor=EXPERT, reason_text="Synthetic fixture approval",
                      entry="interactive", historical_list_exposure="not_exposed")
    criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    calls = []
    def identities(request):
        return [{"candidate_id": name, "preferred_label": name, "input_label": name,
                 "identifiers": [{"scheme": "ik", "value": name}], "identity_link_basis": "exact_identifier_match",
                 "identity_review_state": "not_required"} for name in request["members"]]
    claims = {}
    for name in MEMBERS:
        for kind, value, unit, evidence_kind in (("hard", {"alpha": 100, "beta": 200, "rejected": 900, "unknown": None}[name],
                                                  "g/mol", "database_entry"),
                                                 ("preference", {"alpha": 7, "beta": 9, "rejected": 100, "unknown": 1000}[name],
                                                  "pChEMBL", "curated_measurement")):
            if value is None:
                claims[name, kind] = []
                continue
            record = {"claim_id": f"claim_{name}_{kind}", "source_ref": f"src_{kind}", "candidate_ref": name,
                      "determination_basis": "measured", "evidence_kind": evidence_kind, "value": value, "unit": unit,
                      "location": {"location_kind": "database_record", "locator_value": f"{name}:{kind}"}}
            ledger.record_claim(core, task_id, record, by=OPERATOR, admission_state="admitted", admission_reasons=["synthetic"])
            claims[name, kind] = [dict(record, admission_state="admitted")]
    def evidence_hook(request):
        assert isinstance(request["broker"], _ExistingFactsBroker)
        name, kind = request["candidate_id"], "hard" if request["rule"]["rule_kind"] == "hard_exclusion" else "preference"
        calls.append((name, kind))
        return claims[name, kind], None, ["stored_synthetic_fact"]
    return task_id, identities, evidence_hook, calls


def test_full_and_staged_have_identical_qualified_population_and_qualified_only_scores(core):
    task_id, identities, hook, calls = _fixture(core)
    boards = []
    for mode in ("full", "staged"):
        ref = measurement.register(core, task_id, by=OPERATOR, primary_board=f"Synthetic {mode}", rationale="Parity",
                                   expected_effect="Same qualified set", evaluation_mode=mode)
        ctl = RunController(core, Broker(core), adapter={"adapter_id": "synthetic", "adapter_version": "1", "primary_scheme": "ik"},
                            identity_hook=identities, evidence_hook=hook)
        ctl.start(task_id, by=OPERATOR, measurement_profile_ref=ref)
        boards.append(leaderboard.snapshots(core, task_id)[-1])
    def ranked(board):
        return {row["candidate_ref"]: (row["position"], row["preference_score"], row["qualification_state"])
                for row in board["candidate_entries"]}
    assert ranked(boards[0]) == ranked(boards[1])
    assert ranked(boards[0])["alpha"] == (2, 0., "qualified")
    assert ranked(boards[0])["beta"] == (1, 1., "qualified")
    assert ranked(boards[0])["unknown"][0] is None
    assert calls.count(("rejected", "preference")) == 1
    assert calls.count(("unknown", "preference")) == 2
    assert boards[0]["reporting_tuple"]["skipped_after_rejection_n"] == 0
    assert boards[1]["reporting_tuple"]["skipped_after_rejection_n"] == 1
    assert boards[1]["reporting_tuple"]["recorded_cell_n"] == 8
    assert boards[1]["reporting_tuple"]["assessed_cell_n"] == 7


def test_prediction_cannot_fail_a_hard_gate_or_raise_direct_coverage_and_ordering_is_available():
    attr = dict(MW, attribute_id="attr_q", version=1, acceptable_value_sources=["database_entry", "model_prediction"],
                acceptable_determination_bases=["measured", "predicted"])
    rule = dict(MW_RULE, rule_id="rule_q", version=1)
    predicted = {"claim_id": "claim_p", "source_ref": "src_p", "admission_state": "admitted", "evidence_kind": "model_prediction",
                 "determination_basis": "predicted", "value": 900, "unit": "g/mol"}
    params = dict(candidate={"candidate_id": "synthetic"}, attribute=attr, rule=rule, rule_set_ref="rules@v1",
                  claims=[predicted], resolved=True, qualification_policy=POLICY)
    hard, _ = assessor.assess_cell(**params)
    assert hard["verdict"] == "unknown_missing" and not assessor.direct_evidence(hard)
    pref, _ = assessor.assess_cell(**dict(params, rule=dict(rule, **ORDERING)))
    assert pref["verdict"] == "available" and pref["value"] == 900
    scores = assessor.preference_scores({"synthetic": [pref]}, {"rule_q@v1": {"rule_kind": "preference", "predicate_form": "ordering"}},
                                        {}, qualification_policy=POLICY, qualified_candidates={"synthetic"})
    assert scores["synthetic"] == (1., 0.)
    direct = dict(predicted, claim_id="claim_direct", evidence_kind="database_entry", determination_basis="measured", value=300)
    selected, _ = assessor.assess_cell(**dict(params, rule=dict(rule, **ORDERING), claims=[predicted, direct]))
    assert selected["value"] == 300 and selected["value_source_claim_refs"] == ["claim_direct"]
    failed_tool, _ = assessor.assess_cell(**dict(params, claims=[direct], tool_error_ref="res_synthetic_failed_tool"))
    assert failed_tool["verdict"] == "unknown_missing" and not assessor.direct_evidence(failed_tool)
    assert assessor.qualification([pref], hard_rule_refs=[], required_rule_refs=[], verified_hard_rule_refs=[])["state"] == "not_ready"
    assert assessor.qualification([hard], hard_rule_refs=["rule_q@v1"], required_rule_refs=[],
                                  verified_hard_rule_refs=["rule_q@v1"])["state"] == "pending"


def test_context_with_numeric_evidence_requires_a_method_and_missing_evidence_stays_missing():
    attr = dict(MW, attribute_id='attr_method', version=1, acceptable_value_sources=['model_prediction'],
                acceptable_determination_bases=['predicted'])
    rule = dict(MW_RULE, rule_id='rule_method', version=1, rule_kind='exploratory_consideration',
                predicate_form='qualitative_judgment', cutoff=None)
    claim = {'claim_id': 'claim_method', 'source_ref': 'src_method', 'admission_state': 'admitted',
             'evidence_kind': 'model_prediction', 'determination_basis': 'predicted', 'value': 12, 'unit': attr['unit']}
    args = dict(candidate={'candidate_id': 'method_example'}, attribute=attr, rule=rule,
                rule_set_ref='rules@v1', resolved=True, qualification_policy=POLICY)
    cell, reason = assessor.assess_cell(**args, claims=[claim])
    assert cell['verdict'] == 'unknown_unresolvable' and cell['value'] is None
    assert cell['value_source_claim_refs'] == [] and not cell['direct_evidence']
    assert cell['availability'] == 'unavailable' and cell['interpretation_claim_refs'] == ['claim_method']
    assert reason['evidence_refs'] == ['claim_method'] and reason['absence_check_record'] is None
    assert 'interpretation method' in reason['reason_text'] and 'no admitted claim' not in reason['reason_text']
    for claims in ([], [dict(claim, unit='wrong_scale')]):
        missing, _ = assessor.assess_cell(**args, claims=claims)
        assert missing['verdict'] == 'unknown_missing' and 'interpretation_claim_refs' not in missing
    literature = dict(attr, evidence_request={'capability': 'literature_retrieval', 'question_kind': 'search', 'parameters': {}})
    literature.pop('evidence_requests', None)
    shortfall, _ = assessor.assess_cell(**dict(args, attribute=literature), claims=[claim], min_source_documents=2)
    assert shortfall['verdict'] == 'unknown_missing'
    observation, _ = assessor.assess_cell(**dict(args, rule=dict(rule, predicate_form='recorded_observation')), claims=[claim])
    assert observation['verdict'] == 'available' and observation['value'] == 12
    for kind in ('hard_exclusion', 'preference'):
        unchanged, _ = assessor.assess_cell(**dict(args, rule=dict(rule, rule_kind=kind)), claims=[claim])
        assert unchanged['verdict'] == 'unknown_missing'


def test_explicit_same_property_transform_ignores_provenance_and_prediction_does_not_score_twice():
    direct = {'quantity_id': 'synthetic.logp.property', 'unit': 'log units',
        'value_transform': {'kind': 'distance_outside_band', 'low': 2, 'high': 4,
                            'basis': 'source_stated_value', 'source_refs': ['claim_first_band']},
        'evidence_request': {'capability': 'property_estimate', 'question_kind': 'computed_property',
                             'parameters': {'property': 'XLogP'}}}
    predicted = dict(direct, value_transform=dict(direct['value_transform'], source_refs=['claim_other_band']),
        evidence_request={'capability': 'predicted_property_lookup', 'question_kind': 'admet_prediction',
                          'parameters': {'endpoint': 'logP'}})
    key = criteria.quantity_identity(direct)
    assert criteria.quantity_identity(predicted) == key
    assert criteria.quantity_identity(dict(predicted, value_transform=dict(predicted['value_transform'], basis='expert_set'))) == key
    assert criteria.quantity_identity(dict(predicted, value_transform=dict(predicted['value_transform'], high=5))) != key
    assert criteria.quantity_identity(dict(predicted, unit='different scale')) != key
    assert criteria.quantity_identity(dict(predicted, quantity_id='synthetic.logp.different_condition')) != key
    assert criteria.quantity_identity({k: v for k, v in direct.items() if k != 'quantity_id'}) != \
        criteria.quantity_identity({k: v for k, v in predicted.items() if k != 'quantity_id'})
    def cell(ref, value, basis):
        return {'rule_ref': ref, 'rule_kind': 'preference', 'verdict': 'available', 'value': value,
                'determination_basis': basis, 'value_kind': 'derived' if basis == 'derived' else 'predicted',
                'value_source_claim_refs': ['claim_' + ref]}
    rules = {ref: {'rule_kind': 'preference', 'predicate_form': 'ordering', 'direction': 'lower_better', 'quantity_key': key}
             for ref in ('rule_direct@v1', 'rule_auxiliary@v1')}
    observed = {'alpha': [cell('rule_direct@v1', 0, 'derived')], 'beta': [cell('rule_direct@v1', 2, 'derived')]}
    baseline = assessor.preference_scores(observed, rules, {}, qualified_candidates=set(observed), qualification_policy=POLICY)
    both = {name: [*cells, cell('rule_auxiliary@v1', 2 if name == 'alpha' else 0, 'predicted')]
            for name, cells in observed.items()}
    assert assessor.preference_scores(both, rules, {}, qualified_candidates=set(both), qualification_policy=POLICY) == baseline
    assert baseline == {'alpha': (1.0, 1.0), 'beta': (0.0, 1.0)}


@pytest.mark.parametrize("action", ["pause", "cancel"])
def test_cooperative_control_preserves_cells_and_shared_workflow_budget(core, action):
    task_id, identities, hook, calls = _fixture(core)
    shared = Budget({"usd": 10, "llm_turns": 20})
    shared.record("usd", 2.5)
    seen = []
    def control(run_id):
        seen.append(run_id)
        return action if len(seen) == 3 else None
    ref = measurement.register(core, task_id, by=OPERATOR, primary_board="Synthetic control", rationale="Control", expected_effect="Keep facts")
    ctl = RunController(core, Broker(core), adapter={"adapter_id": "synthetic", "adapter_version": "1", "primary_scheme": "ik"},
                        identity_hook=identities, evidence_hook=hook, control_hook=control, budget=shared)
    run = ctl.start(task_id, by=OPERATOR, measurement_profile_ref=ref)
    assert ctl.current_state(run) == ("paused" if action == "pause" else "cancelled")
    assert len(calls) == 1 and shared.used["usd"] == 2.5
    if action == "pause":
        ctl.control_hook = None
        assert ctl.resume(run) == "completed"
        assert calls.count(("alpha", "hard")) == 1
    assert shared.used["usd"] == 2.5


def test_existing_only_broker_never_invokes_a_remote_or_prediction_provider(core):
    class Forbidden:
        contract = ToolContract(tool_id="synthetic_remote", capability="attribute_estimate", capability_kind="attribute_estimate",
            question_kinds=("quantity",), contract_version="1", implementation_version="1", purpose_statement="synthetic",
            evidence_kind_produced="model_prediction", claim_strength_ceiling="predicted")
        def invoke(self, *args):
            raise AssertionError("existing_only must not recompute")
    broker = Broker(core)
    broker.register(Forbidden())
    result = _ExistingFactsBroker(broker).call("run_synthetic_readonly", "attribute_estimate", "quantity", {}, requesting_actor=OPERATOR)
    assert result.outcome == "not_attempted" and result.absence_reason == "existing_evidence_unavailable"
    assert not any(e.event_type == "tool.requested" for e in core.journal.replay("run_synthetic_readonly"))


def test_new_adjudication_keeps_unsupported_hard_open_and_approves_exact_task_constraint(core):
    context = dict(SPEC, scope_entities=[])
    task_id, _ = task.record_version(core, context, by=OPERATOR)
    _, hard = criteria.propose(core, task_id, MW, MW_RULE, by=OPERATOR)
    oral = dict(ROUTE, derived_from={"task_context": f"{task_id}@v1", "field": "constraints[0]"})
    _, oral_ref = criteria.propose(core, task_id, oral, ROUTE_RULE, by=TEMPLATE)
    result = adjudication.adjudicate_open(core, task_id, qualification_policy=POLICY)
    assert any(row.get("left_open_because") for row in result)
    assert criteria.load(core, hard, task_id)["rule_kind"] == "hard_exclusion"
    assert any(row.get("rule_ref_after") == oral_ref and row["resolution"] == "approve" for row in result)
    pending = review.items(core, [task_id])
    assert next(row for row in pending.values() if row["subject"]["id"] == hard)["state"] == "open"


def test_workbench_revision_is_append_only_and_requires_new_authority(core):
    task_id, _, _, _ = _fixture(core)
    before = criteria.rule_set(core, task_id)
    hard = next(row for row in before["entries"] if row["rule_kind"] == "hard_exclusion")
    old = deepcopy(criteria.load(core, hard["rule_ref"], task_id))
    result = criteria.revise_for_workbench(core, task_id, hard["rule_ref"],
        {"rule": {"cutoff": {"comparator": "<=", "value": 450, "unit": "g/mol"}}}, by=OPERATOR,
        reason="Synthetic revised policy, no inherited approval")
    assert result["changed"] and result["requires_new_freeze"] and not result["previous_authority_carried"]
    assert criteria.load(core, hard["rule_ref"], task_id) == old
    assert criteria.rule_set(core, task_id, before["rule_set_ref"]) == before
    assert "bound_support" not in criteria.load(core, result["rule_ref"], task_id)
    new = criteria.confirm_rule_set(core, task_id, by=OPERATOR, allow_pending=True)
    assert result["rule_ref"] not in {row["rule_ref"] for row in criteria.rule_set(core, task_id, new)["entries"]}
    assert review.items(core, [task_id])[result["review_item_id"]]["state"] == "open"


def test_snapshot_lookup_filters_metadata_without_replaying_unrelated_runs(core, monkeypatch):
    for i, target in enumerate(("task_other", "task_selected", "task_selected")):
        aid = core.artifacts.put("leaderboard_snapshot", {"task_id": target, "published_at": f"2026-01-0{3-i}",
                                                        "snapshot_id": f"lb_{i}"})
        core.journal.append(f"run_synthetic_snapshot_{i}", "leaderboard.snapshot_published", actor=OPERATOR,
                            payload={"task_id": target, "artifact_id": aid})
    def no_replay(*args, **kwargs):
        raise AssertionError("snapshot lookup must not replay every run")
    monkeypatch.setattr(core.journal, "replay", no_replay)
    assert [row["snapshot_id"] for row in leaderboard.snapshots(core, "task_selected")] == ["lb_2", "lb_1"]


def test_continuation_reuses_only_unchanged_facts_and_reassesses_parent_skips(core):
    task_id, identities, hook, calls = _fixture(core)
    manifest = {"policy": "synthetic_exact_facts_v1", "claim_source": "task fixture", "hash": "fixed"}
    opts = dict(adapter={"adapter_id": "synthetic", "adapter_version": "1", "primary_scheme": "ik"},
                identity_hook=identities, evidence_hook=hook, evidence_manifest=manifest)
    ctl = RunController(core, Broker(core), **opts)
    first_profile = measurement.register(core, task_id, by=OPERATOR, primary_board="First synthetic", rationale="First", expected_effect="First")
    first = ctl.start(task_id, by=OPERATOR, measurement_profile_ref=first_profile)
    first_seq = core.journal.last_seq(first)
    frozen = criteria.rule_set(core, task_id)
    hard = next(row for row in frozen["entries"] if row["rule_kind"] == "hard_exclusion")
    edited = criteria.revise_for_workbench(core, task_id, hard["rule_ref"],
        {"rule": {"cutoff": {"comparator": "<=", "value": 1000, "unit": "g/mol"}}},
        reason="Synthetic changed threshold, independent new policy", by=OPERATOR)
    review.decide(core, review.items(core, [task_id])[edited["review_item_id"]], decision="approve", actor=EXPERT,
                  reason_text="Synthetic new review", entry="interactive", historical_list_exposure="not_exposed")
    criteria.confirm_rule_set(core, task_id, by=OPERATOR, allow_pending=True)
    second_profile = measurement.register(core, task_id, by=OPERATOR, primary_board="Second synthetic", rationale="Second", expected_effect="Second")
    calls.clear()
    second = ctl.start(task_id, by=OPERATOR, measurement_profile_ref=second_profile, reuse_from_run_id=first)
    assert calls == [("alpha", "hard"), ("beta", "hard"), ("rejected", "hard"), ("rejected", "preference"), ("unknown", "hard")]
    assert core.journal.last_seq(first) == first_seq
    reused = [core.artifacts.payload(e.payload["artifact_id"]) for e in core.journal.replay(second) if e.event_type == "candidate.assessed"]
    carried = [c for c in reused if c["reuse"]["decision"] == "reused"]
    assert len(carried) == 3 and all(c["reuse"]["source_run_id"] == first for c in carried)
    assert leaderboard.snapshots(core, task_id)[-1]["qualified_count"] == 3
    before = len(core.journal.streams("run_"))
    wrong_mode = measurement.register(core, task_id, by=OPERATOR, primary_board="Wrong mode", rationale="Mode", expected_effect="Refuse", evaluation_mode="full")
    with pytest.raises(Exception, match="reuse policy drift: evaluation_mode"):
        ctl.start(task_id, by=OPERATOR, measurement_profile_ref=wrong_mode, reuse_from_run_id=first)
    assert len(core.journal.streams("run_")) == before


@pytest.mark.parametrize("source_state", ["cancelled", "failed", "unresolved"])
@pytest.mark.parametrize("change_rule", [False, True])
def test_terminal_partial_sweep_reuses_only_completed_unchanged_cells(core, source_state, change_rule):
    task_id, identities, hook, calls = _fixture(core)
    manifest = {"policy": "synthetic_partial_facts_v1", "hash": "fixed"}
    def source_evidence(request):
        result = hook(request)
        if calls[-1] == ("beta", "preference"):
            return [], "res_synthetic_tool_failure", ["synthetic_failed_tool"]
        return result
    def stop_after_partial(run_id):
        count = core.store.db.execute("SELECT count(*) FROM events WHERE stream_id=? "
                                     "AND event_type='candidate.assessed'", (run_id,)).fetchone()[0]
        if count >= 6:
            if source_state == "cancelled":
                return "cancel"
            raise InterruptedError("synthetic worker termination")
    opts = dict(adapter={"adapter_id": "synthetic", "adapter_version": "1", "primary_scheme": "ik"},
                identity_hook=identities, evidence_manifest=manifest)
    ctl = RunController(core, Broker(core), evidence_hook=source_evidence, control_hook=stop_after_partial, **opts)
    first_profile = measurement.register(core, task_id, by=OPERATOR, primary_board="Partial source",
                                        rationale="Partial reuse", expected_effect="Keep completed facts")
    first = ctl.start(task_id, by=OPERATOR, measurement_profile_ref=first_profile, execute=False)
    if source_state == "cancelled":
        assert ctl.execute(first) == "cancelled"
    else:
        with pytest.raises(InterruptedError, match="synthetic worker termination"):
            ctl.execute(first)
        core.journal.append(first, f"run.{source_state}", actor=OPERATOR,
                            state_from="running", state_to=source_state)
    first_seq = core.journal.last_seq(first)
    source_cells = [core.artifacts.payload(e.payload["artifact_id"]) for e in core.journal.replay(first)
                    if e.event_type == "candidate.assessed"]
    assert len(source_cells) == 6 and not leaderboard.snapshots(core, task_id)
    assert any(c.get("tool_error_ref") for c in source_cells)
    assert any(c.get("not_assessed_reason") == "skipped_after_rejection" for c in source_cells)
    if change_rule:
        hard = next(row for row in criteria.rule_set(core, task_id)["entries"] if row["rule_kind"] == "hard_exclusion")
        edited = criteria.revise_for_workbench(core, task_id, hard["rule_ref"],
            {"rule": {"cutoff": {"comparator": "<=", "value": 1000, "unit": "g/mol"}}},
            reason="Synthetic new threshold", by=OPERATOR)
        review.decide(core, review.items(core, [task_id])[edited["review_item_id"]], decision="approve", actor=EXPERT,
                      reason_text="Synthetic new authority", entry="interactive", historical_list_exposure="not_exposed")
        criteria.confirm_rule_set(core, task_id, by=OPERATOR, allow_pending=True)
    ctl.control_hook, ctl.evidence_hook = None, hook
    second_profile = measurement.register(core, task_id, by=OPERATOR, primary_board="Partial continuation",
                                         rationale="New run", expected_effect="Recompute unfinished or changed cells")
    calls.clear()
    second = ctl.start(task_id, by=OPERATOR, measurement_profile_ref=second_profile, reuse_from_run_id=first, execute=False)
    assert ctl.current_state(second) == "queued" and not leaderboard.snapshots(core, task_id)
    assert ctl.execute(second) == "completed"
    cells = [core.artifacts.payload(e.payload["artifact_id"]) for e in core.journal.replay(second)
             if e.event_type == "candidate.assessed"]
    carried = [c for c in cells if c["reuse"]["decision"] == "reused"]
    assert len(cells) == 8 and len(carried) == (1 if change_rule else 4)
    assert all(c["reuse"]["source_run_id"] == first and c["verdict"] != "not_assessed"
               and not c.get("tool_error_ref") for c in carried)
    assert ("beta", "preference") in calls and ("unknown", "hard") in calls
    if change_rule:
        assert len(calls) == 7 and all(c["rule_kind"] == "preference" for c in carried)
        assert ("rejected", "preference") in calls
    else:
        assert calls == [("beta", "preference"), ("unknown", "hard"), ("unknown", "preference")]
        skipped = next(c for c in cells if c.get("not_assessed_reason") == "skipped_after_rejection")
        assert skipped["reuse"]["decision"] == "recomputed"
    assert ctl.current_state(first) == source_state and core.journal.last_seq(first) == first_seq


@pytest.mark.parametrize("source_state", ["queued", "running", "paused"])
def test_continuation_rejects_nonterminal_sweep_sources(core, source_state):
    task_id, identities, hook, _ = _fixture(core)
    ctl = RunController(core, Broker(core), adapter={"adapter_id": "synthetic", "adapter_version": "1", "primary_scheme": "ik"},
                        identity_hook=identities, evidence_hook=hook, evidence_manifest={"policy": "synthetic_fixed"})
    profile = measurement.register(core, task_id, by=OPERATOR, primary_board="Live source",
                                   rationale="Reject live reuse", expected_effect="No concurrent source")
    source = ctl.start(task_id, by=OPERATOR, measurement_profile_ref=profile, execute=False)
    if source_state in ("running", "paused"):
        core.journal.append(source, "run.started", actor=OPERATOR, state_from="queued", state_to="running")
    if source_state == "paused":
        core.journal.append(source, "run.paused", actor=OPERATOR, state_from="running", state_to="paused")
    profile = measurement.register(core, task_id, by=OPERATOR, primary_board="Rejected continuation",
                                   rationale="Reject live reuse", expected_effect="No new run")
    before = core.journal.streams("run_")
    with pytest.raises(Exception, match="reuse source must be a terminated screening run"):
        ctl.start(task_id, by=OPERATOR, measurement_profile_ref=profile, reuse_from_run_id=source)
    assert core.journal.streams("run_") == before and ctl.current_state(source) == source_state


def test_pause_after_all_cells_resumes_without_duplicate_stage_completion(core):
    task_id, identities, hook, _ = _fixture(core)
    issued = []
    def control(run):
        assessed = core.store.db.execute("SELECT 1 FROM events WHERE stream_id=? AND event_type='stage.closed' "
            "AND json_extract(body, '$.payload.stage')='assess'", (run,)).fetchone()
        if assessed and not issued:
            issued.append(True)
            return "pause"
    ctl = RunController(core, Broker(core), adapter={"adapter_id": "synthetic", "adapter_version": "1", "primary_scheme": "ik"},
                        identity_hook=identities, evidence_hook=hook, control_hook=control)
    ref = measurement.register(core, task_id, by=OPERATOR, primary_board="Synthetic late pause", rationale="Pause", expected_effect="Resume finalization")
    run = ctl.start(task_id, by=OPERATOR, measurement_profile_ref=ref)
    assert ctl.current_state(run) == "paused"
    assert ctl.resume(run) == "completed"
    stages = [e.payload["stage"] for e in core.journal.replay(run) if e.event_type == "stage.closed"]
    assert stages == ["identity", "assess", "snapshot"]


@pytest.mark.parametrize("supported", [True, False])
def test_machine_hard_review_requires_explicit_evidence_and_applicability(core, supported):
    task_id, _ = task.record_version(core, dict(SPEC, scope_entities=[]), by=OPERATOR)
    claim = {"claim_id": "claim_synthetic_decision", "source_ref": "src_synthetic_rule", "value": 500, "unit": "g/mol",
             "determination_basis": "asserted", "evidence_kind": "peer_reviewed",
             "location": {"location_kind": "passage", "locator_value": "synthetic:p1",
                          "quoted_span": "An upper limit of 500 g/mol is required for this synthetic population."}}
    ledger.record_claim(core, task_id, claim, by=OPERATOR, admission_state="admitted", admission_reasons=["synthetic"])
    rule = dict(MW_RULE, cutoff_basis="source_stated_value", bound_support=[{
        "parameter_path": "rule.cutoff.value", "claim_id": claim["claim_id"], "source_number": 500, "source_unit": "g/mol",
        "conversion": {"kind": "identity"}, "statement_kind": "states_decision_threshold",
        "applicability_rationale": "The task uses the same synthetic population and measurement scale."}])
    _, ref = criteria.propose(core, task_id, dict(MW, supporting_claim_refs=[claim["claim_id"]]), rule, by=OPERATOR)
    roster = roster_for(lambda request: {"supported": supported, "applicable_to_task": supported,
        "property_is_a_requirement": supported, "reasoning": "Synthetic applicability review", "cited_claim_ids": [claim["claim_id"]]})
    result = adjudication.adjudicate_open(core, task_id, roster=roster, qualification_policy=POLICY)
    assert criteria.load(core, ref, task_id)["rule_kind"] == "hard_exclusion"
    if supported:
        assert result[0]["resolution"] == "approve", result[0].get("left_open_because")
        assert result[0]["requirement_review"]["applicable_to_task"]
        assert result[0]["cited_claim_ids"] == [claim["claim_id"]]
    else:
        assert result[0]["left_open_because"] and next(iter(review.items(core, [task_id]).values()))["state"] == "open"
