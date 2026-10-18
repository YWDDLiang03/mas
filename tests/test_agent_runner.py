"""Important handoff boundaries, using actual uploads and durable workflow storage."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/agent_run.py'
spec = importlib.util.spec_from_file_location('agent_runner', SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_bootstrap_reexecutes_when_venv_and_system_interpreters_share_a_binary(tmp_path, monkeypatch):
    """On POSIX, resolve(venv/bin/python) is often resolve(system/python)."""
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    target = tmp_path / '.venv' / ('Scripts/python.exe' if runner.os.name == 'nt' else 'bin/python')
    target.parent.mkdir(parents=True)
    target.touch()
    monkeypatch.setattr(runner.sys, 'executable', str(target))
    monkeypatch.setattr(runner.sys, 'prefix', str(tmp_path / 'system-prefix'))
    monkeypatch.setattr(runner.sys, 'argv', [str(SCRIPT), 'inspect', '--bootstrap', '--workspace', 'work'])
    probes, launches = [], []
    monkeypatch.setattr(runner.subprocess, 'run', lambda cmd, **kwargs: probes.append(cmd) or SimpleNamespace(returncode=0))
    monkeypatch.setattr(runner.subprocess, 'call', lambda cmd, **kwargs: launches.append(cmd) or 17)
    assert runner.bootstrap(True) == 17
    assert len(probes) == len(launches) == 1
    assert launches[0][0] == str(target) and '--bootstrap' not in launches[0]


def task_file(tmp_path, **updates):
    (tmp_path / 'candidates.csv').write_text('candidate_id,name\nC1,Carrier one\nC2,Carrier two\n', encoding='utf-8')
    (tmp_path / 'measurements.csv').write_text(
        'candidate_id,property,value,unit,basis,conditions,source\n'
        'C1,particle_size,110,nm,measured,DLS at 25 C,Provided laboratory record\n'
        'C2,particle_size,160,nm,predicted,DLS at 25 C,Provided prediction\n', encoding='utf-8')
    value = {'objective': 'Compare particle sizes under the same conditions.', 'targets': ['particle_size'],
             'constraints': 'Prefer smaller sizes.', 'entity_type': 'carrier',
             'candidates_csv': 'candidates.csv', 'measurements_csv': 'measurements.csv', **updates}
    path = tmp_path / 'task.json'
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


def arguments(tmp_path, path):
    args = runner.parser().parse_args(['plan', '--workspace', str(tmp_path / 'workspace'), '--task', str(path)])
    args.workspace = args.workspace.resolve()
    return args


def test_custom_plan_preserves_actual_observations_and_never_uses_recorded_library(tmp_path):
    from mas.ui.uploads import UploadStore
    args = arguments(tmp_path, task_file(tmp_path))
    prepared = runner.prepare_input(args, runner.load_task(args))
    value = prepared['input']
    assert value['library_id'].startswith('upload:')
    assert value['budget_usd'] == 10 and value['workers'] == 4
    assert 'source_task_id' not in value and prepared['facts']['initial_cqa_count'] == 0
    record = UploadStore(args.workspace / 'store').read(value['evidence_upload_id'])
    assert [(row['value'], row['basis']) for row in record['measurements']] == [(110, 'measured'), (160, 'predicted')]
    assert runner.prepare_input(args, runner.load_task(args)) == prepared
    ops = runner.operations_for(args, prepared)
    assert ops.settings['sources.cache_dir'] == str(args.workspace / 'cache')
    assert ops.settings['search.volume'] == ops.settings['textbook.volume'] == 'mid'
    assert '--set' in ops.cli_options and 'sources.cache_dir=' + str(args.workspace / 'cache') in ops.cli_options


def test_custom_missing_measurements_fails_before_creating_workspace(tmp_path):
    path = task_file(tmp_path)
    value = runner.read_json(path)
    del value['measurements_csv']
    runner.write_json(path, value)
    args = arguments(tmp_path, path)
    with pytest.raises(ValueError, match='requires measurements_csv'):
        runner.load_task(args)
    assert not args.workspace.exists()


def test_exact_headers_require_explicit_mapping(tmp_path):
    path = task_file(tmp_path)
    (tmp_path / 'candidates.csv').write_text('sample_id,name\nC1,Carrier one\nC2,Carrier two\n', encoding='utf-8')
    args = arguments(tmp_path, path)
    with pytest.raises(ValueError, match='exact CSV header'):
        runner.load_task(args)
    value = runner.read_json(path)
    value['candidates_mapping'] = {'candidate_id': 'sample_id'}
    runner.write_json(path, value)
    result = runner.prepare_input(args, runner.load_task(args))
    assert result['facts']['candidates_count'] == 2


def test_measurements_with_wrong_identity_or_missing_numeric_unit_cannot_commit(tmp_path):
    args = arguments(tmp_path, task_file(tmp_path))
    (tmp_path / 'measurements.csv').write_text(
        'candidate_id,property,value,unit,basis\nUNKNOWN,size,100,,measured\n', encoding='utf-8')
    with pytest.raises(ValueError, match='CSV validation failed'):
        runner.prepare_input(args, runner.load_task(args))
    committed = list(args.workspace.glob('**/upl_*.meta.json'))
    assert len(committed) == 1 and runner.read_json(committed[0])['kind'] == 'candidates'


def test_atomic_download_checks_bytes_and_reuses_only_verified_cache(tmp_path):
    source = tmp_path / 'source.bin'
    source.write_bytes(b'actual capsule bytes')
    expected = {'bytes': source.stat().st_size, 'sha256': runner.file_hash(source)}
    target = tmp_path / 'cache/bundle.gz'
    runner.download_checked(source.as_uri(), target, expected)
    assert target.read_bytes() == source.read_bytes()
    source.unlink()
    runner.download_checked(source.as_uri(), target, expected)  # no second download
    target.write_bytes(b'wrong cached content')
    source.write_bytes(b'not the declared capsule')
    with pytest.raises(ValueError, match='Capsule exceeds|checksum/size'):
        runner.download_checked(source.as_uri(), target, expected)
    assert target.read_bytes() == b'wrong cached content'
    assert not list(target.parent.glob('*.part'))


def test_durable_submission_and_workflow_retry_resume_share_one_identity(tmp_path):
    from mas.ui.workbench_api import WorkbenchAPI
    args = arguments(tmp_path, task_file(tmp_path))
    prepared = runner.prepare_input(args, runner.load_task(args))
    ops = runner.operations_for(args, prepared)
    api = WorkbenchAPI(ops)
    try:
        launched = []
        api.workflows._launch = launched.append  # stop exactly at the paid execution boundary
        state = runner.run_state(args.workspace)
        current = runner.submission(state, 'stable-request')
        runner.write_json(args.workspace / 'agent-run-state.json', state)
        request = {'input': prepared['input'], 'idempotency_key': current['idempotency_key']}
        first = api.post('/api/workbench/workflows', request)
        retry = runner.submission(runner.run_state(args.workspace), 'stable-request')
        again = api.post('/api/workbench/workflows', dict(request, idempotency_key=retry['idempotency_key']))
        assert first['workflow_id'] == again['workflow_id'] and len(launched) == 1
        api.workflows.update(first['workflow_id'], state='paused', _budget_used={'usd': 1.25},
                             _checkpoints={'normalized': {'task_id': 'task_saved'}})
        api.workflows.command(first['workflow_id'], 'resume')
        saved = api.workflows._read(first['workflow_id'])
        assert saved['_budget_used']['usd'] == 1.25
        assert saved['_checkpoints']['normalized']['task_id'] == 'task_saved'
        with pytest.raises(ValueError, match='--new-run'):
            runner.submission(state, 'changed-request')
        fresh = runner.submission(state, 'stable-request', new_run=True)
        assert fresh['idempotency_key'] != current['idempotency_key']
        question = {'id': 'condition', 'prompt': 'Which measurement condition is required?'}
        api.workflows.update(first['workflow_id'], state='waiting_input', questions=[question])
        prior = runner.inspect(args.workspace)['workflows'][0]
        assert runner.saved_submission(args.workspace, current['idempotency_key'])['workflow_id'] == first['workflow_id']
        api.close()
        api = WorkbenchAPI(ops)
        api.workflows._launch = launched.append
        count = len(launched)
        waiting = runner.recover_submission(api, prepared['input'], current, prior)
        assert waiting['state'] == 'waiting_input' and waiting['questions'] == [question]
        assert len(launched) == count  # repeating a question never starts another model request
    finally:
        api.close()
        ops.close()


def test_missing_credentials_prevents_any_paid_workflow(tmp_path, monkeypatch):
    args = arguments(tmp_path, task_file(tmp_path))
    models = tmp_path / 'models.toml'
    models.write_text('[providers.example]\nkind="openai_compatible"\nmodel="configured-model"\n'
                      'base_url="https://example.invalid"\napi_key_env="MAS_TEST_MISSING_KEY"\n'
                      '[roles]\nproposer="example"\ncritic="example"\nadjudicator="example"\n', encoding='utf-8')
    args.models = models
    monkeypatch.delenv('MAS_TEST_MISSING_KEY', raising=False)
    prepared = runner.prepare_input(args, runner.load_task(args))
    ops = runner.operations_for(args, prepared)
    with pytest.raises(RuntimeError, match='MAS_TEST_MISSING_KEY'):
        runner.execute_run(args, prepared, ops)
    assert runner.inspect(args.workspace)['workflows'] == []
    assert not (args.workspace / 'agent-run-state.json').exists()
