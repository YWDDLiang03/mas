"""Review resumption, with real temporary journals and scripted models only."""
import pytest

from mas.core import adjudication, criteria, review, review_attempts, task
from mas.core.runtime import Core
from test_adjudication import OPERATOR, _disputed, _item, _roster, _task


def scenario(core):
    tid = _task(core)
    context = task.get(core, tid)
    task.record_version(core, dict(context, qualification_policy='qualification_first_v1'), by=OPERATOR, task_id=tid)
    rule_ref, _ = _disputed(core, tid)
    return tid, rule_ref


@pytest.mark.parametrize('verdict,outcome', [('uphold_proposal', 'resolved'), ('uphold_objection', 'unresolved')])
def test_completed_workflow_attempt_survives_reopen_without_a_second_model_call(core, verdict, outcome):
    tid, rule_ref = scenario(core)
    calls = []
    def script(request):
        calls.append(request.request_id)
        return {'verdict': verdict, 'cited_claim_ids': [], 'reasoning': 'Synthetic original review reasoning'}
    roster = _roster(script)
    item = _item(core, tid, rule_ref)
    first = review_attempts.review_once(core, item, roster=roster, qualification_policy='qualification_first_v1')
    assert first['outcome'] == outcome and not first['reused'] and len(calls) == 1
    with Core.open(core.store.root, read_only=True) as reopened:
        row = reopened.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='decision.recorded' "
            "AND json_extract(body,'$.payload.record_kind')='review_attempt'", (tid,)).fetchone()
        assert row is not None
    second = review_attempts.review_once(core, item, roster=roster, qualification_policy='qualification_first_v1')
    assert second['reused'] and second['attempt_ref'] == first['attempt_ref'] and len(calls) == 1
    state = _item(core, tid, rule_ref)['state']
    assert state == ('machine_adjudicated' if outcome == 'resolved' else 'open')
    if outcome == 'resolved':
        assert first['decision_ref'] == adjudication.records(core, tid)[0]['adjudication_id']
    else:
        assert not adjudication.records(core, tid)
    # A new task context invalidates the attempt cache even if the criterion text is unchanged.
    if outcome == 'unresolved':
        task.record_version(core, task.get(core, tid), by=OPERATOR, task_id=tid)
        third = review_attempts.review_once(core, _item(core, tid, rule_ref), roster=roster,
                                          qualification_policy='qualification_first_v1')
        assert not third['reused'] and len(calls) == 2


@pytest.mark.parametrize('answer', [
    {'verdict': 'uphold_objection', 'cited_claim_ids': [], 'reasoning': 'Original legacy objection'},
    {'verdict': 'revise', 'cited_claim_ids': [], 'reasoning': 'Original refused legacy revision',
     'revised_rule': {'acceptable_value_sources': ['peer_reviewed']}},
])
def test_exact_completed_legacy_unresolved_trace_is_recovered_without_new_approval(core, answer):
    tid, rule_ref = scenario(core)
    calls = []
    def script(request):
        calls.append(request.request_id)
        return answer
    roster = _roster(script)
    item = _item(core, tid, rule_ref)
    with pytest.raises(adjudication.AdjudicationError) as original:
        adjudication.adjudicate(core, item, roster=roster, qualification_policy='qualification_first_v1')
    result = review_attempts.review_once(core, item, roster=roster, qualification_policy='qualification_first_v1')
    assert result['reused'] and result['source_kind'] == 'legacy_completed_trace' and len(calls) == 1
    assert result['outcome'] == 'unresolved' and result['reason_text'] == str(original.value)
    assert result['model_reasoning'] == answer['reasoning'] and result['source_agent_records'][0]['trace_ref']
    assert _item(core, tid, rule_ref)['state'] == 'open' and not adjudication.records(core, tid)
    # A new CQA rule/attribute version is new review work, never an old cached answer.
    new_ref, _ = _disputed(core, tid)
    assert new_ref != rule_ref
    new = review_attempts.review_once(core, _item(core, tid, new_ref), roster=roster,
                                    qualification_policy='qualification_first_v1')
    assert not new['reused'] and len(calls) == 2


def test_interrupted_review_has_no_completed_attempt_and_no_reused_incomplete_reply(core, monkeypatch):
    tid, rule_ref = scenario(core)
    item = _item(core, tid, rule_ref)
    roster = _roster(lambda request: {'verdict': 'uphold_objection', 'cited_claim_ids': [], 'reasoning': 'new full reply'})
    core.journal.append(tid, 'agent.started', actor={'kind': 'agent', 'id': 'synthetic-unfinished', 'role': 'adjudicator'},
                        payload={'request_id': 'brief_synthetic_unfinished', 'role': 'adjudicator'})
    original = adjudication.adjudicate
    def interrupted(*args, **kwargs):
        raise InterruptedError('Synthetic stop before a complete reply')
    monkeypatch.setattr(adjudication, 'adjudicate', interrupted)
    with pytest.raises(InterruptedError):
        review_attempts.review_once(core, item, roster=roster, qualification_policy='qualification_first_v1')
    assert not any(e.event_type == 'decision.recorded' for e in core.journal.replay(tid))
    monkeypatch.setattr(adjudication, 'adjudicate', original)
    result = review_attempts.review_once(core, item, roster=roster, qualification_policy='qualification_first_v1')
    assert not result['reused'] and result['outcome'] == 'unresolved'
    assert all(row['request_id'] != 'brief_synthetic_unfinished' for row in result['source_agent_records'])
