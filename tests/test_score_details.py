"""Saved score explanations preserve ties, missingness, provenance and history."""
import math

from test_read_model import Journal
from mas.ui.read_model import ReadModel
from mas.ui.score_details import ScoreDetails, _normalization


def fixture(tmp_path, *, weighted=False, wrong_score=False):
    journal = Journal(tmp_path / 'source')
    journal.task()
    definitions = [
        ('potency', 'preference', 'ordering', 'higher_better', 'shared-potency'),
        ('mass', 'preference', 'threshold', 'lower_better', None),
        ('prediction', 'preference', 'ordering', 'lower_better', None),
        ('duplicate_prediction', 'preference', 'ordering', 'higher_better', 'shared-potency'),
        ('missing', 'preference', 'ordering', 'higher_better', None),
        ('hard', 'hard_exclusion', 'threshold', 'lower_better', None),
        ('context', 'exploratory_consideration', 'qualitative_judgment', 'lower_better', None),
    ]
    entries = []
    for name, kind, predicate, direction, quantity in definitions:
        attr = {'attribute_id': 'attr_' + name, 'version': 1, 'name': name, 'definition': name,
                'measurement_kind': 'quantitative', 'unit': 'pChEMBL' if quantity else 'units',
                'direction': direction, 'acceptable_value_sources': ['database_entry'],
                'evidence_request': {'capability': 'property_estimate', 'question_kind': 'computed_property',
                                     'parameters': {'property': name}}, **({'quantity_id': quantity} if quantity else {})}
        artifact = journal.artifact('attribute', attr)
        journal.event('task_a', 'criterion.version_proposed', {'kind': 'attribute', 'id': attr['attribute_id'], 'version': 1, 'artifact_id': artifact})
        rule = {'rule_id': 'rule_' + name, 'attribute_ref': attr['attribute_id'] + '@v1', 'version': 1,
                'rule_kind': kind, 'predicate_form': predicate, 'cutoff': {'comparator': '<=', 'value': 500, 'unit': 'units'} if name == 'mass' else None}
        artifact = journal.artifact('rule', rule)
        journal.event('task_a', 'criterion.version_proposed', {'kind': 'rule', 'id': rule['rule_id'], 'version': 1, 'artifact_id': artifact})
        entries.append({'rule_ref': rule['rule_id'] + '@v1', 'attribute_ref': rule['attribute_ref'], 'rule_kind': kind})
    frozen = journal.artifact('rule_set', {'task_id': 'task_a', 'rule_set_ref': 'rules@v1', 'entries': entries,
        'ordering_method': {'kind': 'weighted_preference', 'weight_vector': {'rule_potency@v1': 2} if weighted else {}}})
    journal.event('task_a', 'criterion.version_approved', {'artifact_id': frozen, 'rule_set_ref': 'rules@v1'})
    values = {'A': {'potency': 7, 'mass': 450, 'prediction': .3},
              'B': {'potency': 9, 'mass': 650, 'prediction': .8},
              'C': {'potency': 9, 'mass': 350, 'prediction': None}}
    for candidate, quantities in values.items():
        for name, kind, predicate, direction, quantity in definitions:
            value = quantities.get(name, 10 if name == 'duplicate_prediction' else 1 if name == 'hard' else None)
            predicted = name in ('prediction', 'duplicate_prediction')
            cell(journal, candidate, name, value, kind=kind, predicted=predicted)
    scores = {'A': .5 if weighted else 2 / 3, 'B': .375 if weighted else .25,
              'C': 2.5 / 3 if weighted else .875}
    snapshot(journal, 'snap_1', scores, coverage=.6 if weighted else .5, wrong_score=wrong_score)
    model = ReadModel(journal.root)
    model.sync()
    return journal, model, ScoreDetails(model)


def cell(journal, candidate, name, value, *, kind='preference', predicted=False):
    verdict = 'unknown_missing' if value is None else 'fail' if name == 'mass' and value > 500 else 'pass' if name in ('mass', 'hard') else 'available'
    body = {'assessment_id': f'asm_{candidate}_{name}_{value}', 'candidate_ref': candidate,
            'attribute_ref': 'attr_' + name + '@v1', 'rule_ref': 'rule_' + name + '@v1', 'rule_kind': kind,
            'verdict': verdict, 'value': value, 'unit': 'units',
            'determination_basis': 'absent' if value is None else 'predicted' if predicted else 'measured',
            'value_kind': 'missing' if value is None else 'predicted' if predicted else 'measured',
            'direct_evidence': value is not None and not predicted,
            'value_source_claim_refs': [] if value is None else [f'claim_{candidate}_{name}']}
    artifact = journal.artifact('assessment', body)
    journal.event('run_a', 'candidate.assessed', {'candidate_ref': candidate, 'attribute_ref': body['attribute_ref'],
                                               'rule_ref': body['rule_ref'], 'artifact_id': artifact})


def snapshot(journal, identity, scores, *, coverage=.5, wrong_score=False, policy='qualification_first_v1'):
    entries = [{'candidate_ref': candidate, 'identity_labels': [candidate], 'position': 1,
        'preference_score': .1 if wrong_score and candidate == 'A' else score, 'state': 'recommended',
        'preference_coverage': coverage, 'qualification': {'state': 'qualified', 'qualified': True}}
        for candidate, score in scores.items()]
    journal.snapshot(identity, entries=entries, qualification_policy=policy, **{'rules@v': 'rules@v1'},
                     reporting_tuple={'ranking_coverage_floor': .5, 'normalization_population': 'qualified_only'})


def test_ties_threshold_failure_missing_prediction_and_same_quantity_suppression(tmp_path):
    journal, model, service = fixture(tmp_path)
    try:
        explained = service.get('task_a', 'A', 'snap_1')
        assert explained['available'] and explained['validation']['matches']
        assert explained['score_denominator'] == 3 and explained['coverage_numerator'] == 2 and explained['coverage_denominator'] == 4
        rows = {row['name']: row for row in explained['rows']}
        assert len(rows) == 5 and explained['excluded_counts']['hard'] == explained['excluded_counts']['context'] == 1
        assert rows['missing']['comparison_score'] is None and rows['missing']['included_in_coverage']
        assert rows['duplicate_prediction']['suppressed'] and not rows['duplicate_prediction']['included_in_coverage']
        assert rows['prediction']['comparison_score'] == 1 and not rows['prediction']['direct']
        assert rows['prediction']['coverage_numerator_weight'] == 0
        assert math.isclose(sum(row['contribution'] or 0 for row in rows.values()), 2 / 3)
        other = service.get('task_a', 'B', 'snap_1')
        b = {row['name']: row for row in other['rows']}
        assert b['potency']['normalization'] | {'formula': ''} == {'kind': 'tied_empirical_percentile', 'n': 3, 'worse': 1, 'equal': 2, 'formula': ''}
        assert b['potency']['comparison_score'] == .75
        assert b['mass']['comparison_score'] == 0 and b['mass']['included_in_score'] and b['mass']['direct']
        assert other['score_denominator'] == 3 and other['validation']['matches']
    finally:
        journal.db.close()


def test_explicit_weights_change_mean_and_direct_coverage_without_filling_missing_values(tmp_path):
    journal, model, service = fixture(tmp_path, weighted=True)
    try:
        result = service.get('task_a', 'A')
        assert result['validation']['matches'] and result['score'] == .5
        assert result['score_denominator'] == 4 and result['coverage_numerator'] == 3 and result['coverage_denominator'] == 5
    finally:
        journal.db.close()


def test_exact_snapshot_publication_and_attribute_version_are_used_and_preparation_is_reused(tmp_path):
    journal, model, service = fixture(tmp_path)
    try:
        first = service.get('task_a', 'A', 'snap_1')
        prepared = next(iter(service._prepared.values()))
        cell(journal, 'A', 'potency', 100)
        updated = journal.artifact('attribute', {'attribute_id': 'attr_potency', 'version': 2, 'name': 'later edited direction',
            'unit': 'pChEMBL', 'direction': 'lower_better'})
        journal.event('task_a', 'criterion.version_proposed', {'kind': 'attribute', 'id': 'attr_potency', 'version': 2, 'artifact_id': updated})
        snapshot(journal, 'snap_2', {'A': 1, 'B': 1 / 12, 'C': .625})
        model.sync()
        assert service.get('task_a', 'A', 'snap_1')['score'] == first['score']
        assert next(iter(service._prepared.values())) is prepared
        latest = service.get('task_a', 'A')
        assert latest['snapshot_id'] == 'snap_2' and latest['validation']['matches'] and latest['score'] == 1
        row = next(row for row in latest['rows'] if row['name'] == 'potency')
        assert row['direction'] == 'higher_better' and row['attribute_ref'] == 'attr_potency@v1'
    finally:
        journal.db.close()


def test_unsupported_legacy_and_source_mismatch_are_explicit_without_rewriting_score(tmp_path):
    journal, model, service = fixture(tmp_path, wrong_score=True)
    try:
        result = service.get('task_a', 'A')
        assert result['score'] == .1 and result['recomputed_score'] == 2 / 3
        assert not result['available'] and not result['validation']['matches']
        snapshot(journal, 'legacy', {'A': .1}, policy='legacy')
        model.sync()
        result = service.get('task_a', 'A')
        assert not result['available'] and result['unavailable_reason'] == 'unsupported_qualification_policy'
        assert result['rows'] == [] and result['score'] == .1
    finally:
        journal.db.close()


def test_normalization_single_value_all_tied_and_exact_float_values():
    assert _normalization({'A': 0}, 'lower_better')['scores']['A']['score'] == 1
    tied = _normalization({'A': 0, 'B': 0, 'C': 0}, 'lower_better')
    assert all(row['score'] == .5 for row in tied['scores'].values())
    distinct = _normalization({'A': 1.0, 'B': 1.0 + 1e-15}, 'lower_better')
    assert distinct['scores']['A']['score'] == 1 and distinct['scores']['B']['score'] == 0
