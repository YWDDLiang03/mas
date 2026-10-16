"""Run prepared code in memory; real store/cache connections are read-only."""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import sqlite3
import subprocess
import sys
import types

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
manifest = json.loads((OUT / 'patch_manifest.json').read_text(encoding='utf-8'))
for path, hashes in manifest['files'].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == hashes['before_sha256'], path
    assert hashlib.sha256((OUT / 'proposed' / path).read_bytes()).hexdigest() == hashes['after_sha256'], path

import mas.ui.read_model
module = types.ModuleType('mas.ui.read_model')
module.__file__ = str(ROOT / 'src/mas/ui/read_model.py')
sys.modules[module.__name__] = module
mas.ui.read_model = module
exec(compile((OUT / 'proposed/src/mas/ui/read_model.py').read_text(encoding='utf-8'), module.__file__, 'exec'), module.__dict__)

import pytest
target = OUT / 'proposed/tests/test_read_model.py'
result = pytest.main([str(target) + '::test_registered_history_follows_exact_supersedes_without_mixing_record_kinds',
    str(target) + '::test_registered_history_keeps_missing_predecessor_unknown',
    str(target) + '::test_criterion_detail_refs_pin_pool_version_and_same_version_stage_state',
    '-q', '-p', 'no:cacheprovider', '--basetemp', str(OUT / 'temporary-tests')])
assert result == 0


@contextmanager
def ro(path):
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    try:
        yield db
    finally:
        db.close()


model = module.ReadModel.__new__(module.ReadModel)
model._cache = lambda: ro(ROOT / 'var/primary/workbench-read.db')
model.source_path = ROOT / 'var/primary/store/store.db'
task = 'task_01M51AQ0JK0MYN47806ZD5XS1B'
refs = ['rule_predicted-acute-toxicity-ld50@v1', 'rule_predicted-acute-toxicity-ld50@v2']
first, revised = [model.criterion(task, ref) for ref in refs]
version_changes = {item['ref']: item for item in revised['history'] if item.get('kind') in ('attribute', 'rule')}
attr_ref = 'attr_predicted-acute-toxicity-ld50@v2'
attr, rule = version_changes[attr_ref], version_changes[refs[1]]
assert attr['before']['direction'] == first['direction'] == 'higher_better'
assert attr['after']['direction'] == revised['direction'] == 'lower_better'
assert attr['before']['definition'] == first['definition']
assert attr['after']['definition'] == revised['definition']
assert attr['reason'] == rule['reason'] and attr['reason_source'] == rule['reason_source'] == 'workbench_revision'
assert 'rule_kind' not in attr['before'] and 'rule_kind' not in attr['after']
assert 'direction' not in rule['before'] and 'direction' not in rule['after']
assert rule['before']['attribute_ref'] == 'attr_predicted-acute-toxicity-ld50@v1'
assert rule['after']['attribute_ref'] == attr_ref
assert {change['ref'] for change in first['history'] if change.get('kind') in ('attribute', 'rule')} == {
    refs[0], 'attr_predicted-acute-toxicity-ld50@v1'}

proof = []
with model._cache() as cache, ro(model.source_path) as source:
    for ref in ('attr_predicted-acute-toxicity-ld50@v1', refs[0], attr_ref, refs[1]):
        row = cache.execute('SELECT * FROM criterion_versions WHERE task_id=? AND ref=?', (task, ref)).fetchone()
        value = json.loads(row['body'])
        source_value = json.loads(source.execute('SELECT body FROM artifacts WHERE artifact_id=?', (row['artifact_id'],)).fetchone()[0])['payload']
        assert value == source_value
        event = json.loads(source.execute('SELECT body FROM events WHERE rowid=?', (row['source_row'],)).fetchone()[0])
        assert event['event_type'] == 'criterion.version_proposed' and event['payload']['artifact_id'] == row['artifact_id']
        cached_history = json.loads(cache.execute('SELECT body FROM criterion_changes WHERE source_row=?', (row['source_row'],)).fetchone()[0])
        change = version_changes[ref]
        proof.append({'ref': ref, 'artifact_id': row['artifact_id'], 'source_event_id': event['event_id'],
            'source_row': row['source_row'], 'supersedes': value.get('supersedes'),
            'cached_before_was_null': cached_history.get('before') is None,
            'projected_before_ref': change.get('before_ref'),
            'projected_before_version': (change.get('before') or {}).get('version'),
            'projected_after_version': change['after']['version'], 'kind': change['kind'],
            'reason_source': change['reason_source'], 'reason': change['reason']})

subprocess.run(['git', 'apply', '--check', '--whitespace=error-all', str(OUT / 'registered_revision_history.patch')], cwd=ROOT, check=True)
for path, hashes in manifest['files'].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == hashes['before_sha256'], path
validation = {'status': 'prepared_not_applied', 'temporary_regression': '3 passed',
    'real_connections': 'SQLite mode=ro; query_only=ON; no ReadModel construction/sync',
    'task_id': task, 'detail_refs_checked': refs,
    'v1_preserved': {'direction': first['direction'], 'definition': first['definition']},
    'v2_revision': {'before_direction': attr['before']['direction'], 'after_direction': attr['after']['direction'],
        'workbench_reason': attr['reason'], 'record_kinds_kept_separate': True},
    'source_and_cache_records_match': proof, 'live_source_hashes_unchanged': True, 'git_apply_check': 'passed'}
(OUT / 'validation.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(validation, ensure_ascii=False, indent=2))
