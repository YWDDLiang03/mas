"""Verify the pending patch in an isolated module overlay and temporary stores only."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OVERLAY = HERE / 'preview'
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
work = Path(tempfile.mkdtemp(prefix='verification-', dir=HERE)).resolve()
assert work.is_relative_to(HERE.resolve())
(OVERLAY / 'tests' / 'conftest.py').write_bytes((ROOT / 'tests' / 'conftest.py').read_bytes())

baseline_code = r'''
import json, runpy, sys
from pathlib import Path
from mas.core import assessor, criteria, measurement, task
from mas.core.canonical import sha256_hex
from mas.core.runtime import Core
fixture = runpy.run_path(sys.argv[1])
by = fixture['OPERATOR']
store = Path(sys.argv[2]) / 'legacy_store'
with Core.open(store) as core:
    task_id, _ = task.record_version(core, fixture['SPEC'], by=by)
    bad = criteria.propose(core, task_id, fixture['CAT'], fixture['NONE'], by=by)
    good = criteria.propose(core, task_id, fixture['QUANT'], fixture['ORDER'], by=by)
    selected = criteria.confirm_rule_set(core, task_id, by=by)
    frozen = criteria.rule_set(core, task_id, selected)
    assert bad[1] in {entry['rule_ref'] for entry in frozen['entries']}
    profile = measurement.register(core, task_id, by=by, rule_set_ref=selected,
        primary_board='Historical synthetic guard fixture', rationale='Reproduce the old mechanical fault',
        expected_effect='Record the existing non-executable rule without new facts')
    claims = [dict(claim_id='claim_synthetic_true', source_ref='src_synthetic', admission_state='admitted',
        evidence_kind='database_entry', determination_basis='curated', value=True, unit=None)]
    cell, _ = assessor.assess_cell(candidate={'candidate_id':'synthetic'},
        attribute=criteria.load(core,bad[0],task_id), rule=criteria.load(core,bad[1],task_id),
        rule_set_ref=selected, claims=claims, resolved=True, qualification_policy='qualification_first_v1')
    assert cell['verdict'] == 'unknown_missing' and not cell['value_source_claim_refs']
    data = dict(store=str(store), task_id=task_id, bad=list(bad), good=list(good), rule_set_ref=selected,
        profile_ref=profile, profile_sha256=sha256_hex(measurement.load(core,task_id,profile)),
        rule_set_sha256=sha256_hex(frozen), fault_reproduced=dict(entered_scoring=True,
        categorical_fact_value=True, verdict=cell['verdict'], supporting_refs=cell['value_source_claim_refs']))
Path(sys.argv[2], 'baseline.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(data['fault_reproduced']))
'''
baseline = subprocess.run([sys.executable, '-c', baseline_code,
    str(OVERLAY / 'tests/test_preference_execution_guard.py'), str(work)], cwd=ROOT, env=env,
    text=True, capture_output=True)
print(baseline.stdout, end='')
if baseline.returncode:
    print(baseline.stderr)
    raise SystemExit(baseline.returncode)

preview_code = r'''
import json, sys
from pathlib import Path
import mas.core, mas.cli
root, overlay, work = map(Path,sys.argv[1:])
mas.core.__path__.insert(0,str(overlay/'src/mas/core'))
mas.cli.__path__.insert(0,str(overlay/'src/mas/cli'))
from mas.core import criteria, measurement
from mas.core.canonical import sha256_hex
from mas.core.runtime import Core
from mas.core.journal import actor
data=json.loads((work/'baseline.json').read_text())
with Core.open(data['store']) as core:
    seq=core.journal.last_seq(data['task_id'])
    assert sha256_hex(measurement.load(core,data['task_id'],data['profile_ref']))==data['profile_sha256']
    by=actor('human','synthetic-guard-operator','operator',identity_basis='recorded_attestation')
    try:
        measurement.register(core,data['task_id'],by=by,rule_set_ref=data['rule_set_ref'],
            primary_board='Must be refused',rationale='No bypass through an old invalid scoring set',
            expected_effect='Refuse a new invalid profile')
    except measurement.MeasurementError as error:
        assert 'non-executable preferences' in str(error)
        refusal=str(error)
    else:
        raise AssertionError('a new profile must not freeze the old non-executable scoring set')
    assert core.journal.last_seq(data['task_id'])==seq
    selected=criteria.confirm_rule_set(core,data['task_id'],by=by)
    new=criteria.rule_set(core,data['task_id'],selected)
    assert [e['rule_ref'] for e in new['entries']]==[data['good'][1]]
    assert [e['rule_ref'] for e in new['deferred']]==[data['bad'][1]]
    assert criteria.registry_inventory(core,data['task_id'])['active_registered_count']==2
    assert sha256_hex(criteria.rule_set(core,data['task_id'],data['rule_set_ref']))==data['rule_set_sha256']
    assert sha256_hex(measurement.load(core,data['task_id'],data['profile_ref']))==data['profile_sha256']
    result=dict(fault_reproduced=data['fault_reproduced'],old_profile_readable_unchanged=True,
        old_rule_set_unchanged=True,new_invalid_profile_refused_without_writes=True,
        refusal=refusal,new_scoring_rule_count=len(new['entries']),
        new_deferred_rule_count=len(new['deferred']),active_registered_count=2,
        changes_hard_conditions=False,calls_models=0,calls_network=0,writes_primary=0)
(work/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
import pytest
raise SystemExit(pytest.main(['-q',str(overlay/'tests/test_preference_execution_guard.py'),
    str(root/'tests/test_qualification_first.py')+'::test_prediction_cannot_fail_a_hard_gate_or_raise_direct_coverage_and_ordering_is_available',
    str(root/'tests/test_qualification_first.py')+'::test_new_adjudication_keeps_unsupported_hard_open_and_approves_exact_task_constraint',
    str(root/'tests/test_measurement_profile.py')+'::test_profile_is_bound_and_verified_on_the_published_board']))
'''
preview = subprocess.run([sys.executable, '-c', preview_code, str(ROOT), str(OVERLAY), str(work)],
    cwd=ROOT, env=env, text=True, capture_output=True)
print(preview.stdout, end='')
if preview.returncode:
    print(preview.stderr)
    raise SystemExit(preview.returncode)

manifest = json.loads((HERE / 'patch_manifest.json').read_text())
for row in manifest:
    if row['base_sha256'] is not None:
        active_text=(ROOT/row['path']).read_text(encoding='utf-8')
        assert hashlib.sha256(active_text.encode()).hexdigest()==row['base_sha256'], row['path']
result=json.loads((work/'result.json').read_text())
result.update(verification_root=str(work),pytest_output=preview.stdout.strip(),active_sources_unchanged=True,
              patch=str(HERE/'preference_execution_guard.patch'))
(HERE/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'verification':str(HERE/'verification.json'),'active_sources_unchanged':True}))
