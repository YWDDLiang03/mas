"""Optional target-profile analysis after a study's evidence-based evaluation."""
from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path

from mas.core import assessor, criteria, selection
from mas.core.canonical import sha256_hex
from mas.adapters.predict.cdes import PairRequest, SavedResultScorer, install_dataset
from mas.adapters.predict.cdes_results import StructureResults


def source_target_aliases(data: dict) -> dict[str, str]:
    aliases = {}
    for label, target in data['targets'].items():
        for value in (label, target.get('uniprot')):
            if value:
                aliases[str(value).casefold()] = label
    for entity in data['manifest'].get('case_summary', {}).get('required_targets', []):
        label = aliases.get(str(entity.get('label', '')).casefold())
        if label and entity.get('identifier'):
            aliases[str(entity['identifier']).casefold()] = label
    return aliases


def selected_targets(context: dict, source: dict) -> tuple[list[str], list[str]]:
    aliases = source_target_aliases(source)
    selected, missing = [], []
    for entity in context.get('scope_entities', []):
        if entity.get('entity_kind', 'target') != 'target':
            continue
        keys = ('identifier',) if entity.get('identifier_scheme') in ('uniprot', 'uniprot_accession', 'chembl_target') else ('identifier', 'label')
        label = next((aliases[str(entity.get(key, '')).casefold()] for key in keys
                      if str(entity.get(key, '')).casefold() in aliases), None)
        conditions = entity.get('conditions') or {}
        if label:
            target = source['targets'][label]
            sequence = conditions.get('protein_sequence') or conditions.get('sequence')
            fingerprint = conditions.get('sequence_sha256')
            variant = any(conditions.get(key) for key in ('mutation', 'variant', 'isoform'))
            if ((sequence and sequence != target['sequence']) or
                    (fingerprint and fingerprint != target['sequence_sha256']) or
                    (variant and not sequence and not fingerprint)):
                label = None
        if label:
            if label not in selected:
                selected.append(label)
        else:
            missing.append(entity.get('label') or entity.get('identifier'))
    return selected, missing


def run_saved_analysis(core, workspace: Path, context: dict, snapshot: dict, pin: dict,
                       checkpoint=lambda: None) -> dict:
    """Bind predictions to this task's targets and this snapshot's actual values."""
    service = StructureResults(workspace)
    source, source_root = service.load_pinned(pin)
    tid = context['task_context_id']
    service.set_enabled(tid, True)
    targets, missing = selected_targets(context, source)
    if not targets:
        return {'status': 'not_covered', 'message': 'The saved CDES collection does not cover the requested targets.',
                'missing_targets': missing, 'predicted_pairs': 0, 'source': pin}
    existing, _ = service.load(tid)
    uses_source = existing and (existing['manifest'].get('source_collection') == pin or
        existing['manifest']['integration_id'] == pin['integration_id'])
    if uses_source and existing['manifest']['snapshot_id'] == snapshot['snapshot_id'] and targets == existing['manifest']['targets']:
        service.set_enabled(tid, True)
        return {'status': 'completed', 'source': pin,
                'predicted_pairs': existing['manifest']['matched_candidates'] * len(targets),
                'integration_id': existing['manifest']['integration_id'], 'missing_targets': missing}
    frozen = criteria.rule_set(core, tid, snapshot['rules@v'])
    attribute_targets, units, rules = {}, {}, {}
    aliases = source_target_aliases(source)
    for entry in frozen['entries']:
        attribute = criteria.load(core, entry['attribute_ref'], tid)
        rules[entry['rule_ref']] = {'attribute_ref': entry['attribute_ref'], 'name': attribute.get('name')}
        found = set()
        for route in criteria.evidence_routes(attribute):
            parameters = route.get('parameters') or {}
            for key in ('target_chembl_id', 'target_uniprot', 'target_id'):
                label = aliases.get(str(parameters.get(key, '')).casefold())
                if label in targets:
                    found.add(label)
        if len(found) == 1:
            attribute_targets[entry['attribute_ref']] = found.pop()
            units[entry['attribute_ref']] = attribute.get('unit')
    entries = {entry['candidate_ref']: entry for entry in snapshot['candidate_entries']}
    if not any(row['candidate_ref'] in entries for row in source['candidates']):
        return {'status': 'not_covered', 'message': 'The saved collection has no confirmed compound matches in this library.',
                'missing_targets': missing, 'predicted_pairs': 0, 'source': pin}
    observations: dict[tuple[str, str], dict[str, dict]] = {}
    if attribute_targets:
        placeholders = ','.join('?' for _ in attribute_targets)
        rows = core.store.db.execute(
            "SELECT json_extract(body,'$.payload') FROM events WHERE stream_id=? AND event_type='candidate.assessed' "
            f"AND json_extract(body,'$.payload.attribute_ref') IN ({placeholders}) ORDER BY seq",
            (snapshot['run_id'], *attribute_targets))
        for index, row in enumerate(rows):
            if index % 500 == 0:
                checkpoint()
            pointer = json.loads(row[0])
            cell = core.artifacts.payload(pointer['artifact_id'])
            entry = entries.get(pointer['candidate_ref'])
            if not entry or cell.get('assessment_id') not in entry['per_criterion_refs'] or not assessor.direct_evidence(cell):
                continue
            if not isinstance(cell.get('value'), (float, int)) or isinstance(cell['value'], bool):
                continue
            refs = cell.get('value_source_claim_refs') or []
            target = attribute_targets[pointer['attribute_ref']]
            observations.setdefault((pointer['candidate_ref'], target), {})[pointer['rule_ref']] = {
                'value': cell['value'], 'unit': cell.get('unit') or units[pointer['attribute_ref']],
                'basis': cell['determination_basis'], 'observation_count': len(refs), 'endpoint_types': [],
                'claim_refs': refs, 'rule_ref': pointer['rule_ref']}
    data = copy.deepcopy(source)
    data['targets'] = {target: source['targets'][target] for target in targets}
    scorer = SavedResultScorer(source)
    matched_refs = set()
    classification_counts = Counter()
    for index, item in enumerate(data['candidates']):
        if index % 100 == 0:
            checkpoint()
        item['predictions'] = {target: item['predictions'][target] for target in targets}
        item['measurements'], item['measurement_variants'], item['evaluation'] = {}, {}, None
        entry = entries.get(item['candidate_ref'])
        if not entry:
            item['candidate_ref'] = None
            item['match_status'] = 'outside_study_library'
            continue
        matched_refs.add(item['candidate_ref'])
        checked = scorer.predict_pairs([PairRequest(item['candidate_ref'], item['smiles'],
            source['targets'][target]['uniprot'], source['targets'][target]['sequence']) for target in targets])
        if checked['errors']:
            raise ValueError('A saved prediction no longer matches its compound or target input')
        decision = entry.get('selection') or selection.selection_reading(selection.eligibility_reading(entry, rules))
        label = {'eligible': 'Eligible', 'evidence_incomplete': 'Evidence incomplete', 'excluded': 'Excluded',
                 'incomplete': 'Assessment incomplete', 'not_ready': 'Requirements not ready'}[decision['decision']]
        classification_counts[label] += 1
        item['evaluation'] = {'label': (entry.get('identity_labels') or [item['name']])[0], 'classification': label,
            'rank': entry.get('position'), 'score': entry.get('preference_score'),
            'requirements_supported': (entry.get('qualification', {}).get('hard_passed') or 0)
                                     + (entry.get('qualification', {}).get('required_direct_answered') or 0)}
        for target in targets:
            values = list(observations.get((item['candidate_ref'], target), {}).values())
            if len(values) == 1:
                item['measurements'][target] = values[0]
            elif values:
                item['measurement_variants'][target] = values
    eligible = [row for row in data['candidates'] if (row['evaluation'] or {}).get('classification') == 'Eligible']
    data['candidates'].sort(key=lambda row: ((row['evaluation'] or {}).get('rank') or 10**9, row['name']))
    data['original_candidates_without_prediction'] = [
        {'candidate_ref': ref, 'name': (entry.get('identity_labels') or [ref])[0], 'chembl_id': ''}
        for ref, entry in entries.items() if ref not in matched_refs]
    identity = sha256_hex({'source': pin, 'task_context': context, 'snapshot_id': snapshot['snapshot_id'],
                          'targets': targets, 'module_version': 1})
    data['manifest'].update(integration_id='cdes_' + identity, origin='optional_module', task_id=tid,
        run_id=snapshot['run_id'], snapshot_id=snapshot['snapshot_id'], source_collection=pin,
        targets=targets, requested_targets=context.get('scope_entities', []), missing_targets=missing,
        original_candidate_count=len(entries), matched_candidates=len(matched_refs),
        prediction_count=len(data['candidates']) * len(targets),
        original_candidates_without_prediction=len(entries) - len(matched_refs),
        eligible_matched=len(eligible), eligible_target_observations=sum(len(row['measurements']) + len(row['measurement_variants']) for row in eligible),
        eligible_target_gaps=sum(len(targets) - len(row['measurements']) - len(row['measurement_variants']) for row in eligible),
        match_counts=dict(Counter(row['match_status'] for row in data['candidates'])), case_sources=[],
        case_summary={'objective': context['objective_text'], 'candidate_count': len(entries),
                      'required_targets': context.get('scope_entities', []), 'snapshot_id': snapshot['snapshot_id']})
    sources = {row['file']: (source_root / 'sources' / row['file']).read_bytes() for row in data['manifest']['source_files']}
    install_dataset(data, sources, workspace)
    service.set_enabled(tid, True)
    return {'status': 'partial' if missing else 'completed', 'source': pin, 'missing_targets': missing,
            'matched_candidates': len(matched_refs), 'predicted_pairs': len(matched_refs) * len(targets),
            'integration_id': data['manifest']['integration_id']}
