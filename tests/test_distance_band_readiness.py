"""Distance coordinates, using the existing sourced-band grant route; no paid calls."""
import pytest

from mas.core import adjudication, assessor, bound_support, criteria, ledger, review, task
from test_adjudication import OPERATOR, _roster
from test_preference_execution_guard import ORDER, SPEC


def records(core):
    tid, _ = task.record_version(core, dict(SPEC, objective_text='Compare kinase inhibitors using declared preferences',
                                           qualification_policy='qualification_first_v1'), by=OPERATOR)
    claim_id = ledger.record_claim(core, tid, {
        'source_ref': 'src_public_band_fixture', 'evidence_kind': 'peer_reviewed', 'determination_basis': 'asserted',
        'value_low': 2, 'value_high': 4, 'unit': 'logP', 'reading_depth': 'not_read',
        'normalized_statement': 'Moderate lipophilicity, typically logP around 2 to 4, is considered optimal for kinase inhibitors.',
        'location': {'location_kind': 'paragraph', 'locator_value': 'synthetic-copy-sec5.2.p3',
                     'quoted_span': 'Moderate lipophilicity, typically logP around 2 to 4, is considered optimal for kinase inhibitors.'}},
        by=OPERATOR, admission_state='admitted', admission_reasons=['public source shape copied for engineering regression'])
    attribute = {'name': 'Synthetic logP optimal band',
        'definition': 'XLogP within 2 to 4 is preferred and distance outside that band is penalised.',
        'measurement_kind': 'quantitative', 'unit': 'log units', 'direction': 'within_range',
        'aggregation': 'median', 'acceptable_value_sources': ['database_entry'], 'acceptable_determination_bases': ['derived'],
        'supporting_claim_refs': [claim_id], 'value_transform': {'kind': 'distance_outside_band', 'low': 2, 'high': 4,
            'basis': 'source_stated_value', 'source_refs': [claim_id]},
        'evidence_request': {'capability': 'property_estimate', 'question_kind': 'computed_property',
                             'parameters': {'property': 'XLogP'}}}
    rule = {'rule_kind': 'preference', 'predicate_form': 'range_membership', 'cutoff_basis': 'source_stated_value',
            'cutoff': {'comparator': '>=', 'value': 2, 'unit': 'log units'}}
    attr_ref, rule_ref = criteria.propose(core, tid, attribute, rule, by=OPERATOR)
    return tid, claim_id, attr_ref, rule_ref


def observation(core, tid, attr_ref, rule_ref, name, raw):
    return assessor.assess_cell(candidate={'candidate_id': name}, attribute=criteria.load(core, attr_ref, tid),
        rule=criteria.load(core, rule_ref, tid), rule_set_ref='rules@synthetic', resolved=True,
        qualification_policy='qualification_first_v1', claims=[{'claim_id': 'claim_' + name,
            'source_ref': 'src_local_fixture', 'admission_state': 'admitted', 'evidence_kind': 'database_entry',
            'determination_basis': 'derived', 'value': raw, 'unit': 'log units'}])[0]


def test_raw_band_cutoff_after_distance_transform_is_rejected_without_banning_valid_distance_tolerances(core):
    tid, _, ar, rr = records(core)
    attribute, rule = criteria.load(core, ar, tid), criteria.load(core, rr, tid)
    assert observation(core, tid, ar, rr, 'inside', 3.4)['verdict'] == 'fail'
    assert observation(core, tid, ar, rr, 'outside', 6)['verdict'] == 'pass'
    assert 'raw band endpoint' in criteria.preference_execution_problems(attribute, rule)[0]
    with pytest.raises(criteria.InvariantViolation, match='non-executable preferences'):
        criteria.confirm_rule_set(core, tid, by=OPERATOR)
    lower = dict(attribute, direction='lower_better')
    assert 'points away' in criteria.preference_execution_problems(lower, rule)[0]
    assert criteria.preference_execution_problems(lower, ORDER) == []
    for tolerance in (0, 0.5, 2):
        # A numerical coincidence with the raw low=2 is not enough to reject a distance tolerance.
        assert criteria.preference_execution_problems(lower, dict(rule, predicate_form='threshold',
            cutoff={'comparator': '<=', 'value': tolerance, 'unit': 'log units'})) == []


@pytest.mark.parametrize('verdict', ['grant_bound', 'refuse_bound'])
def test_corrected_ordering_with_explicit_heuristic_transform_support_has_a_fresh_review_route(core, verdict):
    tid, claim_id, ar, rr = records(core)
    original_attribute, original_rule = criteria.load(core, ar, tid), criteria.load(core, rr, tid)
    support = [{'parameter_path': f'attribute.value_transform.{parameter}', 'claim_id': claim_id,
        'source_number': number, 'source_unit': 'logP', 'conversion': {'kind': 'identity'},
        'statement_kind': 'provides_heuristic',
        'applicability_rationale': 'The source concerns the same kinase inhibitor population and supplies the complete stated band.',
        'interpretation': {'measurement': 'The published logP 2 to 4 heuristic supplies the lower and upper band endpoints.',
            'inference': 'the_heuristic_is_the_line',
            'population_rationale': 'This task compares kinase inhibitors, so the cited optimal physicochemical window '
                                    'is used only as a relative preference, not as a mandatory suitability test.'}}
        for parameter, number in (('low', 2), ('high', 4))]
    changed = criteria.revise_for_workbench(core, tid, rr, {'attribute': {'direction': 'lower_better',
        'definition': 'Distance max(2-XLogP, 0, XLogP-4); zero inside the stated band, larger distances are less preferred.',
        'bound_support': support}, 'rule': dict(ORDER)}, reason='Correct raw-versus-distance coordinates', by=OPERATOR)
    new_attr = criteria.load(core, changed['attribute_ref'], tid)
    new_rule = criteria.load(core, changed['rule_ref'], tid)
    assert new_attr['value_transform'] == original_attribute['value_transform']
    assert new_rule['cutoff'] is None and not new_rule.get('bound_support')
    claims = ledger.claims(core, [tid])
    checked = bound_support.validate(new_attr, new_rule, claims=claims)
    assert not checked['unsupported_paths']
    assert checked['grantable_paths'] == ['attribute.value_transform.high', 'attribute.value_transform.low']
    item = review.items(core, [tid])[changed['review_item_id']]
    assert adjudication.route_preview(core, item)['route'] == 'bound_interpretation_granted'
    roster = _roster(lambda request: {'verdict': verdict, 'reasoning': 'Synthetic reviewer evaluates the explicitly declared heuristic.',
                                      'cited_claim_ids': [claim_id]})
    if verdict == 'refuse_bound':
        with pytest.raises(adjudication.AdjudicationError, match='remains pending'):
            adjudication.adjudicate(core, item, roster=roster, qualification_policy='qualification_first_v1')
        assert review.items(core, [tid])[item['item_id']]['state'] == 'open'
    else:
        decision = adjudication.adjudicate(core, item, roster=roster, qualification_policy='qualification_first_v1')
        assert decision['route'] == 'bound_interpretation_granted' and decision['resolution'] == 'approve'
        selected = criteria.rule_set(core, tid, criteria.confirm_rule_set(core, tid, by=OPERATOR,
            allow_pending=True, withhold_unresolved_reviews=True))
        assert selected['entries'][0]['authority'] == 'machine_adjudication'
        inside = observation(core, tid, changed['attribute_ref'], changed['rule_ref'], 'inside', 3.4)
        outside = observation(core, tid, changed['attribute_ref'], changed['rule_ref'], 'outside', 6)
        assert (inside['value'], outside['value']) == (0, 2)
        assert inside['verdict'] == outside['verdict'] == 'available'
        scores = assessor.preference_scores({'inside': [inside], 'outside': [outside]}, {
            changed['rule_ref']: {'rule_kind': 'preference', 'predicate_form': 'ordering', 'direction': 'lower_better'}},
            {}, qualified_candidates={'inside', 'outside'}, qualification_policy='qualification_first_v1')
        assert scores == {'inside': (1.0, 1.0), 'outside': (0.0, 1.0)}
    assert criteria.load(core, ar, tid) == original_attribute and criteria.load(core, rr, tid) == original_rule
