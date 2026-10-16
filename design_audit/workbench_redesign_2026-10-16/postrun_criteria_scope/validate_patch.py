"""Validate the prepared patch in memory and against read-only historical cache rows."""
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
code = pytest.main([str(target) + '::test_working_scope_pins_frozen_versions_and_pending_filters_before_paging',
                    str(target) + '::test_criterion_detail_refs_pin_pool_version_and_same_version_stage_state',
                    str(target) + '::test_mandated_added_uses_created_bindings_and_repairs_legacy_cache_on_read',
                    str(target) + '::test_lineage_nodes_resolve_saved_versions_and_preserve_new_child_history',
                    '-q', '-p', 'no:cacheprovider', '--basetemp', str(OUT / 'temporary-tests')])
assert code == 0

cache = ROOT / 'var/primary/workbench-read.db'
@contextmanager
def readonly_cache():
    db = sqlite3.connect(cache.as_uri() + '?mode=ro', uri=True, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    try:
        yield db
    finally:
        db.close()

model = module.ReadModel.__new__(module.ReadModel)
model._cache = readonly_cache
model.source_path = ROOT / 'var/primary/store/store.db'
rows = []
for task_id in ('task_01M50JQYYQAMPBQTQ0N8YNQT22', 'task_01M50Q5EZE12GGDES5QNWR0JQX'):
    working = model.criteria(task_id, state='working', page_size=200)
    pending = model.criteria(task_id, state='pending')
    broad = model.criteria(task_id, state='active')
    with readonly_cache() as db:
        frozen = module.ReadModel._meta(db)['frozen:' + task_id]
        assert {item['rule_ref'] for item in working['items']} == {item['rule_ref'] for item in frozen['entries']}
    assert working['total'] == len(working['items'])
    assert all(item['state'] == 'in_evaluation' for item in working['items'])
    rows.append({'task_id': task_id, 'rule_set_ref': working['rule_set_ref'],
                 'working_total': working['total'], 'pending_total': pending['total'],
                 'legacy_active_total': broad['total'], 'frozen_refs_match': True})
print(json.dumps(rows, indent=2))

with readonly_cache() as db:
    past = db.execute("SELECT ch.* FROM criterion_changes ch JOIN criteria_current c "
        "ON c.task_id=ch.task_id AND c.criterion_id=ch.criterion_id WHERE ch.task_id=? "
        "AND ch.stage_id IS NOT NULL AND ch.version<c.version AND ch.criterion_id LIKE 'cri_%' "
        "AND ch.source_row=(SELECT max(x.source_row) FROM criterion_changes x WHERE x.task_id=ch.task_id "
        "AND x.criterion_id=ch.criterion_id AND x.stage_id=ch.stage_id) LIMIT 1",
        ('task_01M50Q5EZE12GGDES5QNWR0JQX',)).fetchone()
    assert past
    latest = json.loads(module.ReadModel._resolve_criterion(db, past['task_id'], past['criterion_id'])['body'])
    selected = model.criteria(past['task_id'], stage=past['stage_id'], q=past['criterion_id'], page_size=1)['items'][0]
    pinned = json.loads(module.ReadModel._resolve_criterion(db, past['task_id'], selected['detail_ref'])['body'])
    assert pinned['version'] == selected['version'] == past['version'] < latest['version']
    exact_detail = {'task_id': past['task_id'], 'criterion_id': past['criterion_id'],
                    'table_version': selected['version'], 'base_id_version': latest['version'],
                    'pinned_detail_version': pinned['version'], 'historical_read_only': pinned['historical_version'],
                    'detail_ref': selected['detail_ref']}
print(json.dumps(exact_detail, indent=2))

task_id, run_id = 'task_01M51AQ0JK0MYN47806ZD5XS1B', 'run_01M51AQ43WQQPDQZVD9GADSVTB'
with sqlite3.connect(model.source_path.as_uri() + '?mode=ro', uri=True) as source:
    source.row_factory = sqlite3.Row
    source.execute('PRAGMA query_only=ON')
    boundaries = source.execute("SELECT rowid,body FROM events WHERE stream_id=? "
        "AND event_type IN ('stage.opened','stage.closed') AND json_extract(body,'$.payload.stage')='mandated' ORDER BY seq", (run_id,)).fetchall()
    opened, closed = boundaries
    closing = json.loads(closed['body'])
    expected = {row['rule_ref']: row['attribute_ref'] for row in closing['payload']['result']}
    creations = []
    for row in source.execute("SELECT rowid,body FROM events WHERE stream_id=? AND event_type='criterion.version_proposed' "
        "AND json_extract(body,'$.payload.kind')='rule' AND rowid>? AND rowid<? ORDER BY rowid", (task_id, opened['rowid'], closed['rowid'])):
        event = json.loads(row['body'])
        payload = event['payload']
        ref = f"{payload['id']}@v{payload['version']}"
        rule_row = source.execute("SELECT body FROM artifacts WHERE artifact_id=? AND kind='rule'", (payload['artifact_id'],)).fetchone()
        rule = json.loads(rule_row['body'])['payload']
        assert expected[ref] == rule['attribute_ref']
        creations.append({'rule_ref': ref, 'attribute_ref': rule['attribute_ref'], 'event_id': event['event_id']})
projected = next(stage for stage in model.stages(task_id)['items'] if stage['run_id'] == run_id and stage['stage'] == 'mandated')
assert projected['before_count'] == 0 and projected['after_count'] == projected['added'] == len(expected) == len(creations) == 6
assert {(row['rule_ref'], row['event_id']) for row in projected['added_event_refs']} == {(row['rule_ref'], row['event_id']) for row in creations}
with readonly_cache() as db:
    raw_added = json.loads(db.execute('SELECT body FROM stages WHERE stage_id=?', (projected['stage_id'],)).fetchone()[0])['added']
mandated = {'task_id': task_id, 'run_id': run_id, 'result_artifact_id': closing['payload']['result_artifact_id'],
    'before_count': projected['before_count'], 'after_count': projected['after_count'],
    'raw_cached_added': raw_added, 'projected_added': projected['added'],
    'added_count_basis': projected['added_count_basis'], 'verified_creation_events': creations}
print(json.dumps(mandated, indent=2))

child_ref = 'cri_01M51GW2QDP58C6CYM8PA889PT@v1'
child = model.criterion(task_id, child_ref)
parents = [node for node in child['lineage']['nodes'] if node.get('relation') == 'parent']
expected_parents = {'cri_01M51ASBG7FE3ZQ9VTA8PTJJH5@v1', 'cri_01M51BGY30T4YP2D2BEF8YAMH8@v1'}
assert {node['ref'] for node in parents} == expected_parents
assert all(node['name'] == 'CSF1R engagement on record' and node['definition'] and node['version'] == 1
           and not node['missing'] for node in parents)
for node in parents:
    original = model.criterion(task_id, node['detail_ref'])
    assert original['version'] == node['version'] and original['definition'] == node['definition']
creation = next(change for change in child['history'] if change.get('operation') == 'merge' and change.get('before') is None)
lineage = {'task_id': task_id, 'child_ref': child_ref, 'child_name': child['name'],
           'parent_nodes': parents, 'edges': child['lineage']['edges'],
           'merge_creation_before': creation['before'], 'merge_creation_after_version': creation['after']['version'],
           'exact_parent_detail_matches': True}
print(json.dumps(lineage, indent=2))

subprocess.run(['git', 'apply', '--check', str(OUT / 'working_criteria.patch')], cwd=ROOT, check=True)
for path, hashes in manifest['files'].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == hashes['before_sha256'], path
(OUT / 'validation.json').write_text(json.dumps({'status': 'prepared_not_applied', 'temporary_regression': '4 passed',
    'historical_cache_mode': 'sqlite mode=ro; query_only=ON', 'historical_rows': rows,
    'historical_exact_detail': exact_detail,
    'mandated_added_projection': mandated,
    'exact_lineage': lineage,
    'live_source_hashes_unchanged': True, 'git_apply_check': 'passed'}, indent=2) + '\n', encoding='utf-8')
