"""Append two source-supported logP corrections; never rewrite the previous result.

Run once with the workbench writer stopped. No network or model calls here; new
review items must subsequently receive the ordinary workflow's actual decision.
"""
import json
from pathlib import Path

from mas.core import bound_support, criteria, ledger
from mas.core.journal import actor
from mas.core.runtime import Core
from mas.core.canonical import sha256_hex

TASK = 'task_01M51AQ0JK0MYN47806ZD5XS1B'
CORRECTIONS = (
    ('rule_lipophilicity-logp-optimal-band@v1', 'claim_01M4X8AJ48X0A1MB80GB6V5YVY',
     'Database-derived XLogP'),
    ('rule_lipophilicity-logp@v1', 'claim_01M4YGKFT8T97H08A3RS5A2H24',
     'Saved predicted logP'),
)
REASON = (
    'Correct the executable meaning of the already cited logP 2-4 preference. '
    'Use distance max(2-logP, 0, logP-4), where zero is inside the cited band and '
    'smaller is preferred. A raw lower-edge threshold cannot be applied to this '
    'distance or stand for the full band. The two endpoints remain exactly those '
    'in each criterion\'s own pinned claim. Declare the shared octanol/water logP '
    'quantity so a prediction remains supporting information when a database '
    'value is available for the same band preference. Preserve source routes, '
    'original claims, units, aggregation and all hard conditions; apply the '
    'correction to every candidate. No candidate-specific threshold, weight, '
    'imputation, new literature, prediction or lookup is introduced. Fresh '
    'evidence/applicability review is required before the corrected versions run.'
)


def main():
    destination = Path('var/workbench-v2-acceptance/logp-coordinate-revisions.json')
    if destination.exists():
        raise SystemExit('Revision record already exists; do not create duplicate versions.')
    rows = []
    with Core.open('var/primary/store') as core:
        claims = ledger.claims(core, [TASK])
        by_id = {c['claim_id']: c for c in claims}
        prepared = []
        for rule_ref, claim_id, label in CORRECTIONS:
            old_rule = criteria.load(core, rule_ref, TASK)
            old_attribute = criteria.load(core, old_rule['attribute_ref'], TASK)
            claim = by_id[claim_id]
            assert claim_id in old_attribute['supporting_claim_refs']
            assert claim['admission_state'] == 'admitted'
            assert claim['value_low'] == 2 and claim['value_high'] == 4
            support = [{
                'parameter_path': f'attribute.value_transform.{parameter}',
                'claim_id': claim_id, 'source_number': number, 'source_unit': 'logP',
                'conversion': {'kind': 'identity'}, 'statement_kind': 'provides_heuristic',
                'applicability_rationale': 'The pinned statement explicitly offers the complete logP 2-4 '
                    'heuristic for kinase inhibitors, the population of this investigation. It supplies '
                    'a relative preference only, not an oral-administration qualification test.',
                'interpretation': {
                    'measurement': 'The published logP 2-4 heuristic supplies both band endpoints; '
                        'the executed value is distance outside that complete band.',
                    'inference': 'the_heuristic_is_the_line',
                    'population_rationale': 'Use the stated kinase-inhibitor heuristic only as a '
                        'physicochemical preference for the present kinase-inhibitor library.'}}
                for parameter, number in (('low', 2), ('high', 4))]
            transform = old_attribute.get('value_transform') or {
                'kind': 'distance_outside_band', 'low': 2, 'high': 4,
                'basis': 'source_stated_value', 'source_refs': [claim_id]}
            changes = {
                'attribute': {
                    'definition': f'{label}, expressed as distance max(2-logP, 0, logP-4) '
                        'outside the source-stated logP 2-4 band for kinase inhibitors. Zero is '
                        'inside the band; smaller distances are preferred. Source values remain '
                        'available in the linked evidence.',
                    'direction': 'lower_better', 'value_transform': transform,
                    'quantity_id': 'octanol_water_log_partition_coefficient',
                    'bound_support': support},
                'rule': {'predicate_form': 'ordering', 'cutoff': None,
                         'cutoff_basis': 'none_evidence_insufficient',
                         'applies_to_result_kind': 'ranked_under_score'},
            }
            new_attribute = dict(old_attribute, **changes['attribute'])
            new_rule = dict(old_rule, **changes['rule'])
            new_rule.pop('bound_support', None)
            criteria.check_attribute(new_attribute)
            criteria.check_rule(new_rule, new_attribute)
            assert not criteria.preference_execution_problems(new_attribute, new_rule)
            checked = bound_support.validate(new_attribute, new_rule, claims=claims)
            assert not checked['unsupported_paths'], checked
            assert checked['grantable_paths'] == ['attribute.value_transform.high', 'attribute.value_transform.low']
            prepared.append((rule_ref, changes, old_rule, old_attribute, claim, checked))
        for rule_ref, changes, old_rule, old_attribute, claim, checked in prepared:
            result = criteria.revise_for_workbench(core, TASK, rule_ref, changes,
                reason=REASON, by=actor('agent', 'codex', 'operator'))
            new_rule = criteria.load(core, result['rule_ref'], TASK)
            new_attribute = criteria.load(core, result['attribute_ref'], TASK)
            assert criteria.load(core, rule_ref, TASK) == old_rule
            assert criteria.load(core, old_rule['attribute_ref'], TASK) == old_attribute
            rows.append({'result': result, 'reason': REASON, 'old_rule': old_rule,
                'old_attribute': old_attribute, 'new_rule': new_rule, 'new_attribute': new_attribute,
                'old_rule_sha256': sha256_hex(old_rule), 'new_rule_sha256': sha256_hex(new_rule),
                'bound_validation_before_review': checked, 'source_claim': claim})
    destination.write_text(json.dumps({'task_id': TASK, 'previous_snapshot_retained':
        f'lb_{TASK}_1', 'revisions': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'record': str(destination), 'results': [row['result'] for row in rows]}))


if __name__ == '__main__':
    main()
