"""Validate prepared DTOs without applying the patch or synchronizing the real cache."""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import importlib.util
import json
import sqlite3
import subprocess
import sys
import types

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
manifest = json.loads((OUT / 'patch_manifest.json').read_text(encoding='utf-8'))


def check_live():
    for path, entry in manifest['files'].items():
        actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest() if (ROOT / path).exists() else None
        assert actual == entry['before_sha256'], path


check_live()
import mas.ui.read_model
module = types.ModuleType('mas.ui.read_model')
module.__file__ = str(ROOT / 'src/mas/ui/read_model.py')
sys.modules[module.__name__] = module
mas.ui.read_model = module
exec(compile((OUT / 'proposed/src/mas/ui/read_model.py').read_text(encoding='utf-8'), module.__file__, 'exec'), module.__dict__)
import pytest
target = OUT / 'proposed/tests/test_read_model.py'
code = pytest.main([str(target) + '::test_latest_evaluation_status_preserves_registry_history_and_frozen_reasons',
    str(target) + '::test_criterion_detail_refs_pin_pool_version_and_same_version_stage_state',
    str(target) + '::test_registered_history_follows_exact_supersedes_without_mixing_record_kinds',
    '-q', '-p', 'no:cacheprovider', '--basetemp', str(OUT / 'temporary-tests')])
assert code == 0


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
mw_ref = 'rule_molecular-weight-oral-absorption@v2'
anchor_ref = 'rule_csf1r-curated-potency@v1'
pending = next(item for item in model.criteria(task, state='pending', q='Molecular weight')['items'] if item.get('rule_ref') == mw_ref)
detail, anchor, old = [model.criterion(task, ref) for ref in (mw_ref, anchor_ref, mw_ref.replace('@v2', '@v1'))]
assert pending['state'] == detail['state'] == 'active'
assert pending['evaluation']['state'] == detail['evaluation']['state'] == 'deferred'
assert detail['evaluation']['reason_kind'] == 'unresolved_review'
assert anchor['evaluation']['state'] == 'enabled'
assert old['evaluation']['state'] == 'historical' and old['evaluation']['scope'] == 'saved_version'
assert model.criteria(task, state='working')['total'] == 24

with ro(model.source_path) as source, model._cache() as cache:
    event = source.execute("SELECT body FROM events WHERE stream_id=? AND event_type='criterion.version_approved' "
        "AND json_extract(body,'$.payload.rule_set_ref')='rules@v2' ORDER BY seq DESC LIMIT 1", (task,)).fetchone()
    event = json.loads(event[0])
    record = json.loads(source.execute('SELECT body FROM artifacts WHERE artifact_id=?', (event['payload']['artifact_id'],)).fetchone()[0])['payload']
    mw_record = next(item for item in record['deferred'] if item['rule_ref'] == mw_ref)
    assert detail['evaluation']['reason'] == mw_record['reason']
    assert detail['evaluation']['basis']['frozen_records'] == [mw_record]
    assert len(record['entries']) == 24 and len(record['deferred']) == 19
    assert detail['evaluation']['basis']['review_item_refs'] == mw_record['review_item_refs']
    context = module.ReadModel._evaluation_context(cache, task, module.ReadModel._meta(cache)['frozen:' + task])
    cached_rows = [json.loads(row[0]) for row in cache.execute('SELECT body FROM criteria_listing WHERE task_id=? ORDER BY criterion_id', (task,))]

# Exercise the prepared acceptance script's exact cache-to-API DTO projection;
# do not call its completion gate, HTTP, candidates, source_records or rebuild.
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('prepared_accept_workbench_run', OUT / 'proposed/scripts/accept_workbench_run.py')
acceptance = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = acceptance
spec.loader.exec_module(acceptance)
api_rows = []
for page in range(1, 100):
    result = model.criteria(task, state='all', page=page)
    api_rows.extend(result['items'])
    if not result['has_more']:
        break
cached_dtos = [acceptance.criterion_cache_view(item, context) for item in cached_rows]
assert api_rows == cached_dtos
# Independent source membership/reason oracle for current registered DTOs only.
enabled = {item['rule_ref'] for item in record['entries']}
held = {item['rule_ref']: item for item in record['deferred'] if item.get('scope', 'rule') == 'rule'}
current_rows = [item for item in api_rows if item.get('registered') and item.get('current')]
for item in current_rows:
    ref, value = item['rule_ref'], item['evaluation']
    expected_state = 'enabled' if ref in enabled else 'deferred' if ref in held else 'pending'
    assert value['state'] == expected_state and value['rule_set_ref'] == 'rules@v2'
    assert value.get('reason') == (held[ref].get('reason') if ref in held and ref not in enabled else None)

subprocess.run(['git', 'apply', '--check', '--whitespace=error-all', str(OUT / 'latest_evaluation_status.patch')], cwd=ROOT, check=True)
check_live()
proof = {'status': 'prepared_not_applied', 'temporary_regression': '3 passed',
    'real_reading': 'SQLite mode=ro; query_only=ON; no real construction/sync', 'task_id': task,
    'freeze': {'rule_set_ref': 'rules@v2', 'artifact_id': event['payload']['artifact_id'], 'event_id': event['event_id'],
               'enabled': len(record['entries']), 'deferred': len(record['deferred'])},
    'mw': {'rule_ref': mw_ref, 'recorded_state': detail['state'], 'list_evaluation': pending['evaluation'],
           'detail_evaluation': detail['evaluation'], 'reason_and_basis_match_source_freeze': True},
    'enabled_anchor': {'rule_ref': anchor_ref, 'evaluation': anchor['evaluation']},
    'historical_mw_v1': old['evaluation'],
    'acceptance_dto_parity': {'all_items_compared': len(api_rows), 'cache_to_api_exact_match': True,
        'source_membership_and_reason_rows_checked': len(current_rows), 'source_membership_and_reasons_match': True},
    'working_total_unchanged': 24, 'live_source_hashes_unchanged': True, 'git_apply_check': 'passed'}
(OUT / 'validation.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: proof[key] for key in ('status', 'temporary_regression', 'freeze', 'historical_mw_v1', 'acceptance_dto_parity', 'live_source_hashes_unchanged')}, ensure_ascii=False, indent=2))
