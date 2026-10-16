"""Unresolved proposals stay out of prospective scoring; historical sets remain immutable."""
import pytest

from mas.core import adjudication, assessor, criteria, criteria_export, ledger, measurement, review, review_attempts, task
from mas.core.canonical import sha256_hex
from test_adjudication import OPERATOR, _roster
from test_preference_execution_guard import ORDER, QUANT, SPEC


def fixture(core):
    tid, _ = task.record_version(core, dict(SPEC, qualification_policy='qualification_first_v1'), by=OPERATOR)
    claim_id = ledger.record_claim(core, tid, {
        'source_ref': 'src_synthetic_f', 'evidence_kind': 'peer_reviewed', 'determination_basis': 'measured',
        'value': 10, 'unit': '%', 'reading_depth': 'not_read',
        'location': {'location_kind': 'table_cell', 'locator_value': 'synthetic-table-row',
                     'quoted_span': 'Synthetic F% is species dependent: mouse 10%, dog 80%.'}},
        by=OPERATOR, admission_state='admitted', admission_reasons=['synthetic fixture'])
    oral = dict(QUANT, name='Measured oral bioavailability (F%, any species)',
        definition='Maximum reported F% across species', unit='%', aggregation='max', direction='higher_better',
        acceptable_value_sources=['peer_reviewed'], supporting_claim_refs=[claim_id],
        evidence_request={'capability': 'literature_retrieval', 'question_kind': 'search',
                          'parameters': {'query_template': '({names}) AND oral bioavailability'}})
    dispute = {'open_critic_findings': [{'check': 'evidence_support', 'verdict': 'fail', 'severity': 'material',
                'referent': 'aggregation', 'finding': 'A maximum across species is not comparable.'}]}
    oral_pair = criteria.propose(core, tid, oral, ORDER, by=OPERATOR, dispute=dispute)
    resolved_pair = criteria.propose(core, tid, dict(QUANT, name='System-reviewed molecular weight'),
                                     ORDER, by=OPERATOR, dispute=dispute)
    hard_pair = criteria.propose(core, tid, dict(QUANT, name='Pending hard requirement'), {
        'rule_kind': 'hard_exclusion', 'cutoff_basis': 'expert_set',
        'cutoff': {'comparator': '<=', 'value': 500, 'unit': 'g/mol'}}, by=OPERATOR)
    queue = review.items(core, [tid])
    item = lambda ref: next(row for row in queue.values() if row['subject']['id'] == ref)
    def answer(request):
        objection = oral['name'] in request.messages[0]['content']
        return {'verdict': 'uphold_objection' if objection else 'uphold_proposal',
                'cited_claim_ids': [claim_id] if objection else [],
                'reasoning': 'Synthetic species aggregation objection' if objection else 'Synthetic system review supports the rule'}
    roster = _roster(answer)
    attempt = review_attempts.review_once(core, item(oral_pair[1]), roster=roster,
                                        qualification_policy='qualification_first_v1')
    resolved = review_attempts.review_once(core, item(resolved_pair[1]), roster=roster,
                                         qualification_policy='qualification_first_v1')
    assert attempt['outcome'] == 'unresolved' and resolved['outcome'] == 'resolved'
    return tid, oral_pair, resolved_pair, hard_pair, attempt


def test_open_ordering_preference_is_withheld_with_receipt_but_resolved_system_review_can_score(core):
    tid, oral, resolved, hard, receipt = fixture(core)
    queue_before = review.items(core, [tid])
    originals = {ref: criteria.load(core, ref, tid) for pair in (oral, resolved, hard) for ref in pair}
    # The exact old counterexample remains available only under the legacy confirmation policy.
    legacy_ref = criteria.confirm_rule_set(core, tid, by=OPERATOR, allow_pending=True)
    legacy = criteria.rule_set(core, tid, legacy_ref)
    assert next(row for row in legacy['entries'] if row['rule_ref'] == oral[1])['disputed'] is True
    profile_ref = measurement.register(core, tid, by=OPERATOR, rule_set_ref=legacy_ref,
        qualification_policy='legacy', primary_board='Synthetic historical policy', rationale='Keep legacy behavior',
        expected_effect='Preserve the recorded old reading')
    profile_hash, legacy_hash = sha256_hex(measurement.load(core, tid, profile_ref)), sha256_hex(legacy)
    before = core.journal.last_seq(tid)
    with pytest.raises(measurement.MeasurementError, match='unresolved or disputed proposals'):
        measurement.register(core, tid, by=OPERATOR, rule_set_ref=legacy_ref,
            primary_board='Must refuse', rationale='Strict prospective policy', expected_effect='Do not bypass review')
    assert core.journal.last_seq(tid) == before
    new = measurement.prepare(core, tid, by=OPERATOR, defer_capabilities=(),
        primary_board='Synthetic strict policy', rationale='Withhold unresolved proposals',
        expected_effect='Only reviewed executable rules score')
    strict = criteria.rule_set(core, tid, new['rule_set_ref'])
    assert strict['withhold_unresolved_reviews'] is True
    assert {row['rule_ref'] for row in strict['entries']} == {resolved[1]}
    assert strict['entries'][0]['authority'] == 'machine_adjudication'
    held = next(row for row in strict['deferred'] if row['rule_ref'] == oral[1])
    assert held['reason_kind'] == 'unresolved_review' and held['attribute_ref'] == oral[0]
    assert held['reviews'][0]['attempts'][0]['attempt_ref'] == receipt['attempt_ref']
    assert receipt['reason_text'] in held['reason'] and held['review_item_refs']
    assert criteria_export._use(oral[1], oral[0], [strict], None)['reason'] == held['reason']
    assert oral[1] in strict['pending'] and hard[1] in strict['pending']
    assert review.items(core, [tid]) == queue_before
    assert criteria.registry_inventory(core, tid)['active_registered_count'] == 3
    assert not strict['pending_but_scoring']
    assert criteria.deferred_capabilities(strict) == ()
    assert not assessor.qualification([], hard_rule_refs=[], required_rule_refs=[], verified_hard_rule_refs=[],
                                     pending_hard_rules=[hard[1]])['qualified']
    assert sha256_hex(criteria.rule_set(core, tid, legacy_ref)) == legacy_hash
    assert sha256_hex(measurement.load(core, tid, profile_ref)) == profile_hash
    assert all(criteria.load(core, ref, tid) == value for ref, value in originals.items())


def test_a_frozen_disputed_entry_requires_new_confirmation_even_after_its_review_resolves(core):
    tid, oral, _, _, _ = fixture(core)
    old_ref = criteria.confirm_rule_set(core, tid, by=OPERATOR, allow_pending=True)
    item = next(row for row in review.items(core, [tid]).values() if row['subject']['id'] == oral[1])
    adjudication.adjudicate(core, item, roster=_roster(lambda request: {
        'verdict': 'uphold_proposal', 'cited_claim_ids': [], 'reasoning': 'Synthetic explicit subsequent review'}),
        qualification_policy='qualification_first_v1')
    assert not criteria.unresolved_review_findings(core, tid, rule_set=criteria.rule_set(core, tid, old_ref))
    with pytest.raises(measurement.MeasurementError, match='frozen disputed entry'):
        measurement.register(core, tid, by=OPERATOR, rule_set_ref=old_ref,
            primary_board='Stale disputed set', rationale='Require fresh confirmation', expected_effect='Refuse stale metadata')
    strict_ref = criteria.confirm_rule_set(core, tid, by=OPERATOR, allow_pending=True, withhold_unresolved_reviews=True)
    assert oral[1] in {row['rule_ref'] for row in criteria.rule_set(core, tid, strict_ref)['entries']}
