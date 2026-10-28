"""Verify the public saved-case tables and optionally assemble their standalone ZIP.

Uses the Python standard library. Reads recorded observations; makes no model or
network calls and does not update the scientific workspace.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import median
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT if (ROOT / 'run-summary.json').is_file() else ROOT / 'examples/oral-multitarget/latest/source-data'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def csv_rows(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def close(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12), (a, b)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(data):
    case = data / 'study_exports' if (data / 'study_exports').is_dir() else data.parent
    for name, record in read_json(data / 'source-index.json')['files'].items():
        path = case / name
        assert path.stat().st_size == record['bytes'] and digest(path) == record['sha256'], name
    tables = {n: csv_rows(next(data.glob(f'AI_Data_{n}_*.csv*'))) for n in range(1, 11)}
    expected = {1: 53, 2: 3177, 3: 98487, 4: 170, 5: 25, 6: 17, 7: 1348, 8: 10, 9: 10, 10: 18}
    assert {n: len(rows) for n, rows in tables.items()} == expected
    snapshot = read_json(case / 'results/snapshot.json')
    entries = {e['candidate_ref']: e for e in snapshot['candidate_entries']}
    names = {e['identity_labels'][0]: ref for ref, e in entries.items()}
    assert len(names) == len(entries) == 3177
    defs = read_json(data / 'source_records/final_criterion_definitions.json')
    definitions = {d['entry']['rule_ref']: d for d in defs}
    bindings = snapshot['measurement_profile']['policy']['scoring_policy']['required_binding_check']
    targets = {b['rule_ref'] for b in bindings['scope_bindings']}
    conditions = {r for r, d in definitions.items() if d['rule']['rule_kind'] == 'hard_exclusion'}
    scoring = {r for r, d in definitions.items() if d['rule']['rule_kind'] == 'preference'}
    assert (len(conditions | targets), len(scoring), len(targets & scoring), len(conditions | targets | scoring)) == (6, 17, 5, 18)
    uses = Counter(r['Use'] for r in tables[1])
    assert uses == {'Eligibility': 1, 'Eligibility and scoring': 5, 'Scoring': 12,
                    'Context': 13, 'Awaiting definition or review': 22}
    current = [x for x in read_json(case / 'results/cqa.json')['items'] if x.get('current')]
    assert {(r['Criterion identifier'], r['Rule reference']) for r in tables[1]} == \
        {(r['criterion_id'], r.get('rule_ref') or '') for r in current}

    cells, assessment_ids, per_candidate = {}, set(), defaultdict(set)
    for row in tables[3]:
        key = row['Candidate identifier'], row['Rule reference']
        assert key not in cells and row['Assessment identifier'] not in assessment_ids
        assert names[row['Candidate']] == key[0] and key[1] in definitions
        cells[key] = row
        assessment_ids.add(row['Assessment identifier'])
        per_candidate[key[0]].add(row['Assessment identifier'])
    assert all(per_candidate[ref] == set(e['per_criterion_refs']) for ref, e in entries.items())

    outcomes = {r['candidate']: r for r in csv_rows(case / 'selection/candidate-selection.csv')}
    classes = {'eligible': 'Eligible', 'evidence_incomplete': 'Evidence incomplete', 'excluded': 'Excluded'}
    for row in tables[2]:
        original = outcomes[row['Candidate']]
        assert row['Classification'] == classes[original['selection']]
        ref = names[row['Candidate']]
        supported = sum(cells[ref, r]['Assessment'] == 'pass' for r in conditions)
        supported += sum(cells[ref, r]['Supports direct coverage'] == 'True' for r in targets)
        failed = any(cells[ref, r]['Assessment'] == 'fail' for r in conditions)
        derived = 'Excluded' if failed or not supported else 'Eligible' if supported == 6 else 'Evidence incomplete'
        assert derived == row['Classification'] and int(row['Requirements supported']) == supported
        if row['Score']: close(row['Score'], original['score'])
    groups = dict(Counter(r['Classification'] for r in tables[2]))
    assert groups == {'Eligible': 10, 'Evidence incomplete': 1305, 'Excluded': 1862}
    eligible = {ref for ref, e in entries.items() if e['qualified']}
    scores_by_name = defaultdict(list)
    for row in tables[4]:
        ref, rule = names[row['Candidate']], row['Rule reference']
        assert ref in eligible and rule in scoring
        cell = cells[ref, rule]
        assert row['Observed value'] == cell['Value'] and row['Evidence basis'] == cell['Evidence basis']
        available = cell['Assessment'] in ('available', 'pass', 'fail') and bool(cell['Value'])
        if row['Included in total score'] == 'True':
            assert available
            if row['Comparison method'] == 'ordering':
                vals = [float(cells[c, rule]['Value']) for c in eligible
                        if cells[c, rule]['Value'] and cells[c, rule]['Assessment'] in ('available', 'pass')]
                value = float(cell['Value'])
                worse = sum(v > value if row['Direction'] == 'lower_better' else v < value for v in vals)
                ties = sum(v == value for v in vals)
                point = (worse + (ties - 1) / 2) / (len(vals) - 1) if len(vals) > 1 else 1.0
            else:
                point = 1.0 if cell['Assessment'] == 'pass' else 0.0
            close(point, row['Criterion score'])
        else:
            assert not row['Criterion score']
        scores_by_name[row['Candidate']].append(row)
    for name, rows in scores_by_name.items():
        assert len(rows) == 17
        usable = [r for r in rows if r['Included in total score'] == 'True']
        denom = sum(float(r['Weight']) for r in usable)
        value = sum(float(r['Weight']) * float(r['Criterion score']) for r in usable) / denom
        coverage = sum(float(r['Direct coverage weight']) for r in rows) / sum(float(r['Applicable coverage weight']) for r in rows)
        close(value, entries[names[name]]['preference_score'])
        close(coverage, entries[names[name]]['direct_preference_coverage'])
        for row in usable:
            close(float(row['Weight']) * float(row['Criterion score']) / denom, row['Contribution to total score'])
            close(value, row['Total score'])
    for row in csv_rows(data / 'eligible-leaderboard.csv'):
        entry = entries[row['Candidate identifier']]
        close(row['Score'], entry['preference_score'])
        close(row['Direct scoring evidence coverage'], entry['direct_preference_coverage'])
        assert int(row['Rank']) == entry['position']

    obs = tables[7]
    raw = read_json(data / 'source_records/target_observation_records.json')
    by_target = defaultdict(list)
    target_by_name = {definitions[r]['attribute']['name']: r for r in targets}
    for row in obs:
        claim = raw['claims'][row['Claim reference']]
        value = claim['value']; unit = claim['unit']
        if unit not in ('pChEMBL', 'pIC50', 'pKi', 'pKd', 'pEC50'):
            value = -math.log10(value * {'nM': 1e-9, 'uM': 1e-6, 'µM': 1e-6, 'μM': 1e-6, 'mM': 1e-3, 'M': 1}[unit])
        close(value, row['Value used (pChEMBL)'])
        assert row['Source reference'] == claim['source_ref']
        by_target[row['Candidate'], row['Target criterion']].append(row)
    assert len(by_target) == 238 and len(raw['claims']) == len(obs) == 1348
    for (name, target), rows in by_target.items():
        cell = cells[names[name], target_by_name[target]]
        assert {r['Claim reference'] for r in rows} == set(json.loads(cell['Source observation references']))
        close(median(float(r['Value used (pChEMBL)']) for r in rows), cell['Value'])

    duplicates = defaultdict(list)
    for row in obs:
        if row['Assay identifier']:
            key = tuple(row[k] for k in ['Candidate', 'Target criterion', 'Assay identifier', 'Measurement type', 'Reported value', 'Reported unit'])
            duplicates[key].append(row)
    duplicate_sets = {frozenset(r['Claim reference'] for r in rows) for rows in duplicates.values() if len(rows) > 1}
    review = read_json(data / 'source_records/review_summary.json')
    assert duplicate_sets == {frozenset(g['claims']) for g in review['same_assay_endpoint_value_groups']}
    for result in review['duplicate_record_sensitivity']:
        key = result['candidate'], result['criterion']
        rows = by_target[key]
        remove = {r['Claim reference'] for group in duplicates.values() if len(group) > 1
                  and len({r['Document identifier'] for r in group}) == 1 for r in group[1:]}
        remaining = [r for r in rows if r['Claim reference'] not in remove]
        close(median(float(r['Value used (pChEMBL)']) for r in rows), result['before'])
        close(median(float(r['Value used (pChEMBL)']) for r in remaining), result['after'])
        assert result['candidate'] not in scores_by_name and remaining

    nonprediction = {}
    for name, rows in scores_by_name.items():
        parts = [r for r in rows if r['Included in total score'] == 'True' and r['Evidence basis'] != 'predicted']
        nonprediction[name] = sum(float(r['Weight']) * float(r['Criterion score']) for r in parts) / sum(float(r['Weight']) for r in parts)
    no_pred_rank = {n: i + 1 for i, n in enumerate(sorted(nonprediction, key=lambda n: (-nonprediction[n], entries[names[n]]['position'])))}
    for row in tables[8]:
        close(row['Without ADMET predictions score'], nonprediction[row['Candidate']])
        assert int(row['Without ADMET predictions rank']) == no_pred_rank[row['Candidate']]

    ic50 = {(n, t): median(float(r['Value used (pChEMBL)']) for r in rows if r['Measurement type'] == 'IC50')
            for (n, t), rows in by_target.items() if n in scores_by_name and any(r['Measurement type'] == 'IC50' for r in rows)}
    comparison = {}
    for name, rows in scores_by_name.items():
        points, direct = [], 0
        for row in rows:
            target = row['Criterion']
            if target in target_by_name:
                if (name, target) not in ic50: continue
                v = ic50[name, target]; population = [x for (n, t), x in ic50.items() if t == target]
                points.append((sum(x < v for x in population) + (sum(x == v for x in population) - 1) / 2) / (len(population) - 1) if len(population) > 1 else 1.0)
                direct += 1
            elif row['Included in total score'] == 'True':
                points.append(float(row['Criterion score'])); direct += float(row['Direct coverage weight'])
        comparison[name] = (sum(points) / len(points), direct / 17)
    ordered = sorted((n for n, (_, coverage) in comparison.items() if coverage >= .5),
                     key=lambda n: (-comparison[n][0], entries[names[n]]['position']))
    assert len(ordered) == 7
    for row in tables[9]:
        name = row['Candidate']; value, coverage = comparison[name]
        close(value, row['IC50-only target summaries score']); close(coverage, row['Direct coverage'])
        assert row['Rank in IC50-only comparison'] == (str(ordered.index(name) + 1) if name in ordered else '')
    account = read_json(case / 'results/model-accounting.json')['total']
    assert sum(int(r['Model requests']) for r in tables[10]) == account['requests'] == 325
    assert sum(int(r['Input tokens']) for r in tables[10]) == account['usage']['input_tokens']
    assert sum(int(r['Output tokens']) for r in tables[10]) == account['usage']['output_tokens']
    close(sum(float(r['Estimated cost USD']) for r in tables[10]), account['known_cost_usd'])
    stages = read_json(case / 'results/stages.json')['items']
    assert len(stages) == len(tables[5])
    for saved, row in zip(stages, tables[5]):
        assert row['Stage'] == saved['stage'] and row['Entries after'] == (str(saved['after_count']) if saved.get('after_count') is not None else '')
    return {'status': 'pass', 'row_counts': {str(k): v for k, v in expected.items()}, 'candidate_groups': groups, 'assessment_links_checked': len(assessment_ids),
            'eligible_scores_recomputed': len(scores_by_name), 'target_medians_recomputed': len(by_target),
            'without_predictions_surufatinib_rank': no_pred_rank['Surufatinib'],
            'ic50_fixed_cohort_surufatinib_rank': ordered.index('Surufatinib') + 1, 'ic50_coverage_rankable_candidates': len(ordered),
            'duplicate_record_groups_checked': len(duplicate_sets),
            'model_requests': account['requests'], 'estimated_model_cost_usd': account['known_cost_usd']}


def bundle_files(data):
    files = {p.relative_to(data).as_posix(): p.read_bytes() for p in data.rglob('*') if p.is_file() and p != data / 'manifest.json'}
    gz = 'AI_Data_3_candidate_assessments.csv.gz'
    files[gz[:-3]] = gzip.decompress(files.pop(gz))
    for name in list(files):
        if name.endswith('.md'):
            text = files[name].decode('utf-8')
            text = text.replace('(AI_Data_3_candidate_assessments.csv.gz)', '(AI_Data_3_candidate_assessments.csv)')
            text = text.replace('(../../../../docs/', '(https://github.com/YWDDLiang03/mas/blob/main/docs/')
            text = text.replace('(../results/', '(study_exports/results/')
            text = text.replace('(../source-data-download.json)', '(https://github.com/YWDDLiang03/mas/blob/main/examples/oral-multitarget/latest/source-data-download.json)')
            files[name] = text.encode('utf-8')
    index = read_json(data / 'source-index.json')
    for name, record in index['files'].items():
        case = data / 'study_exports' if (data / 'study_exports').is_dir() else data.parent
        path = case / name
        assert digest(path) == record['sha256'] and path.stat().st_size == record['bytes'], name
        files['study_exports/' + name] = path.read_bytes()
    files['tools/build_case_source_data.py'] = Path(__file__).read_text(encoding='utf-8').encode('utf-8')
    return files


def make_manifest(data, report):
    return {'format': 'triage-case-source-data-v1', 'release_date': '2026-10-28',
            'task_id': read_json(data / 'run-summary.json')['task_id'],
            'snapshot_id': read_json(data / 'run-summary.json')['snapshot_id'],
            'verification': report,
            'files': {p.relative_to(data).as_posix(): {'bytes': p.stat().st_size, 'sha256': digest(p)}
                      for p in sorted(data.rglob('*')) if p.is_file() and p != data / 'manifest.json'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DEFAULT)
    parser.add_argument('--write-manifest', action='store_true', help='Record checksums after preparing a new data release')
    parser.add_argument('--output', type=Path, help='Write a standalone ZIP after verification')
    args = parser.parse_args()
    report = verify(args.data)
    manifest = make_manifest(args.data, report)
    if args.write_manifest:
        (args.data / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    else:
        assert read_json(args.data / 'manifest.json') == manifest, 'Source-data manifest differs'
    if args.output:
        files = bundle_files(args.data)
        archive_manifest = dict(manifest, files={name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for name, raw in sorted(files.items())})
        files['manifest.json'] = (json.dumps(archive_manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for name, raw in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 10, 28, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3; info.external_attr = 0o644 << 16
                z.writestr(info, raw, compresslevel=9)
        report['archive'] = {'path': str(args.output), 'bytes': args.output.stat().st_size, 'sha256': digest(args.output), 'files': len(files)}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
