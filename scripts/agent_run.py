#!/usr/bin/env python3
"""One-command, resumable MAS handoff. Run --help; no model is called by plan/replay."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from urllib.request import urlopen
import uuid
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'examples/oral-multitarget/latest/reproduction/manifest.json'
ASSET_URL = 'https://github.com/YWDDLiang03/mas/releases/download/v1.1.0/'
TERMINAL = {'completed', 'unresolved', 'failed', 'cancelled'}
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'src'))


def progress(message):
    print(message, file=sys.stderr, flush=True)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def bootstrap(enabled):
    """Keep the entry point stdlib-only until the optional environment is ready."""
    if sys.version_info < (3, 11):
        raise ValueError('Python 3.11 or newer is required.')
    if enabled:
        target = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not target.is_file():
            progress('Creating .venv (first use only)')
            subprocess.run([sys.executable, '-m', 'venv', str(ROOT / '.venv')], check=True, stdout=sys.stderr)
        probe = subprocess.run([str(target), '-c', 'import requests; import importlib.metadata; importlib.metadata.version("mas")'],
                               cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if probe.returncode:
            progress('Installing MAS and its Python dependencies into .venv')
            subprocess.run([str(target), '-m', 'pip', 'install', '-e', str(ROOT)], check=True, stdout=sys.stderr)
        # POSIX virtual environments commonly symlink their executable to the
        # base interpreter. Compare environment prefixes, not symlink targets.
        if Path(sys.prefix).resolve() != (ROOT / '.venv').resolve():
            return subprocess.call([str(target), str(Path(__file__).resolve()),
                                    *[arg for arg in sys.argv[1:] if arg != '--bootstrap']], cwd=Path.cwd())
    if importlib.util.find_spec('requests') is None:
        raise ValueError('Python dependencies are missing. Repeat this command with --bootstrap.')
    return None


@contextmanager
def workspace_lock(workspace):
    """OS locks release on crashes; the file lives outside an empty import target."""
    directory = ROOT / 'var/agent-run-locks'
    if directory.is_relative_to(workspace):
        raise ValueError('The repository root cannot be used as a research workspace.')
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (signature(os.path.normcase(str(workspace))) + '.lock')
    with path.open('a+b') as handle:
        handle.seek(0, 2)
        if not handle.tell():
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError('This workspace is already owned by another agent-run command. Use inspect to read its status.') from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def download_checked(url, destination, expected):
    """Atomic cache publication: interrupted or wrong bytes never become a bundle."""
    destination = Path(destination)
    if destination.is_file() and destination.stat().st_size == expected['bytes'] and file_hash(destination) == expected['sha256']:
        progress(f'Using verified cached capsule: {destination}')
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix='.' + destination.name + '.', suffix='.part', dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        total, digest, last = 0, hashlib.sha256(), time.monotonic()
        progress(f'Downloading optional recorded-input capsule ({expected["bytes"]:,} bytes)')
        with os.fdopen(descriptor, 'wb') as output, urlopen(url, timeout=60) as response:
            for block in iter(lambda: response.read(1024 * 1024), b''):
                output.write(block)
                total += len(block)
                digest.update(block)
                if total > expected['bytes']:
                    raise ValueError('Capsule exceeds the manifest byte count.')
                if time.monotonic() - last > 10:
                    progress(f'Downloaded {total:,}/{expected["bytes"]:,} bytes')
                    last = time.monotonic()
            output.flush()
            os.fsync(output.fileno())
        if total != expected['bytes'] or digest.hexdigest() != expected['sha256']:
            raise ValueError('Downloaded capsule checksum/size differs from the repository manifest.')
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def ensure_recorded(args):
    from mas.core.reproduction import import_bundle
    if args.bundle:
        bundle = args.bundle.resolve()
    else:
        manifest = read_json(MANIFEST)
        cache = args.download_cache.resolve() / manifest['capsule']['sha256']
        if cache == args.workspace or cache.is_relative_to(args.workspace):
            raise ValueError('The download cache must be outside the target workspace.')
        cache.mkdir(parents=True, exist_ok=True)
        parts = manifest['capsule'].get('parts') or [manifest['capsule']]
        for part in parts:
            if Path(part['path']).name != part['path']:
                raise ValueError('Invalid capsule asset filename in manifest.')
            download_checked(ASSET_URL + part['path'], cache / part['path'], part)
        write_json(cache / 'manifest.json', manifest)
        bundle = cache
    progress('Importing recorded inputs (an identical completed import is reused)')
    return import_bundle(bundle, args.workspace, progress=progress)


def load_task(args):
    spec = read_json(args.task) if args.task else {'input_mode': 'original'}
    if not isinstance(spec, dict):
        raise ValueError('Task JSON must be an object.')
    known = {'input_mode', 'candidates_csv', 'measurements_csv', 'candidates_mapping', 'measurements_mapping',
             'objective', 'targets', 'constraints', 'entity_type', 'title', 'reference_candidate',
             'additional_information', 'workers', 'budget_usd', 'evaluation_mode'}
    unknown = set(spec) - known
    if unknown:
        raise ValueError('Unknown task JSON field(s): ' + ', '.join(sorted(unknown)))
    mode = spec.get('input_mode', 'custom')
    if mode not in ('original', 'custom'):
        raise ValueError('input_mode must be original or custom.')
    spec['input_mode'] = mode
    for key in ('objective', 'targets', 'constraints', 'entity_type', 'title', 'reference_candidate',
                'workers', 'budget_usd', 'evaluation_mode'):
        override = getattr(args, key, None)
        if override is not None:
            spec[key] = override
    spec.setdefault('workers', 4)
    spec.setdefault('budget_usd', 10.0)
    spec.setdefault('evaluation_mode', 'staged')
    if type(spec['workers']) is not int or not 1 <= spec['workers'] <= 32:
        raise ValueError('workers must be an integer from 1 to 32.')
    if isinstance(spec['budget_usd'], bool) or not isinstance(spec['budget_usd'], (int, float)) or not math.isfinite(spec['budget_usd']) or spec['budget_usd'] <= 0:
        raise ValueError('budget_usd must be a finite positive number.')
    if spec['evaluation_mode'] not in ('staged', 'full'):
        raise ValueError('evaluation_mode must be staged or full.')
    if 'targets' in spec and (not isinstance(spec['targets'], list) or any(not isinstance(t, str) or not t.strip() for t in spec['targets'])):
        raise ValueError('targets must be an array of nonempty strings.')
    if 'constraints' in spec and not isinstance(spec['constraints'], str):
        raise ValueError('constraints must be text.')
    if 'entity_type' in spec and spec['entity_type'] not in ('drug', 'carrier', 'general'):
        raise ValueError('entity_type must be drug, carrier or general.')
    if 'objective' in spec and (not isinstance(spec['objective'], str) or not spec['objective'].strip()):
        raise ValueError('objective must be nonempty text.')
    if mode == 'custom':
        for field in ('objective', 'targets', 'constraints', 'entity_type', 'candidates_csv', 'measurements_csv'):
            if field not in spec or (field not in ('targets', 'constraints') and not spec[field]):
                raise ValueError(f'Custom task requires {field}; recorded inputs are never used as a fallback.')
        base = args.task.resolve().parent if args.task else Path.cwd()
        for kind in ('candidates', 'measurements'):
            path = (base / spec[kind + '_csv']).resolve()
            if not path.is_file():
                raise ValueError(f'Missing {kind} CSV: {path}')
            spec[kind + '_csv'] = str(path)
            # Pass an explicit mapping for every canonical field: aliases are opt-in.
            exact_mapping(kind, path.read_text(encoding='utf-8-sig'), spec.get(kind + '_mapping'))
    elif any(key in spec for key in ('candidates_csv', 'measurements_csv')):
        raise ValueError('CSV inputs require input_mode=custom.')
    return spec


def exact_mapping(kind, content, supplied=None):
    from mas.ui.uploads import FIELDS
    headers = next(csv.reader(io.StringIO(content)), [])
    if supplied is not None and not isinstance(supplied, dict):
        raise ValueError(f'{kind}_mapping must map canonical field names to exact CSV headers.')
    known = {row[0] for row in FIELDS[kind]}
    if supplied and set(supplied) - known:
        raise ValueError(f'Unknown canonical field in {kind}_mapping.')
    mapping = {key: key if key in headers else None for key in known}
    mapping.update(supplied or {})
    for key, _, required in FIELDS[kind]:
        column = mapping[key]
        if column is not None and column not in headers:
            raise ValueError(f'{kind}: mapped CSV header {column!r} is absent.')
        if required and not column:
            raise ValueError(f'{kind}: exact CSV header {key!r} is required; alternatively supply {kind}_mapping.')
    return mapping


def initialize_custom(workspace):
    marker = workspace / 'agent-workspace.json'
    if workspace.exists() and any(workspace.iterdir()) and not (marker.is_file() or (workspace / 'reproduction-import.json').is_file()):
        raise ValueError('Choose a new empty workspace or a workspace already prepared by agent_run.py.')
    workspace.mkdir(parents=True, exist_ok=True)
    if not marker.exists():
        write_json(marker, {'format': 'mas-agent-workspace-v1', 'input_mode': 'custom'})
    from mas.core.runtime import Core
    with Core.open(workspace / 'store'):
        pass


def prepare_input(args, spec):
    if spec['input_mode'] == 'original':
        ensure_recorded(args)
        from mas.core.reproduction import prepare_live
        prepared = prepare_live(args.workspace)
        value = dict(prepared['input'])
        facts = {k: v for k, v in prepared.items() if k not in ('input', 'created_at')}
    else:
        initialize_custom(args.workspace)
        from mas.ui.uploads import UploadStore
        uploads = UploadStore(args.workspace / 'store')
        value, counts = {}, {}
        for kind in ('candidates', 'measurements'):
            path = Path(spec[kind + '_csv'])
            content = path.read_text(encoding='utf-8-sig')
            request = {'kind': kind, 'filename': path.name, 'content': content,
                       'mapping': exact_mapping(kind, content, spec.get(kind + '_mapping')),
                       'entity_type': spec['entity_type']}
            if kind == 'measurements':
                request['library_id'] = value['library_id']
            preview = uploads.preview(request)
            if not preview['can_commit']:
                errors = '; '.join(f'row {e.get("row", "header")}: {e["message"]}' for e in preview['errors'][:12])
                raise ValueError(f'{kind} CSV validation failed: {errors}')
            committed = uploads.commit(preview['upload_id'], request)
            value['library_id'] = committed['library_id']
            if kind == 'measurements':
                value['evidence_upload_id'] = committed['evidence_upload_id']
            counts[kind + '_count'] = committed['row_count']
        facts = dict(counts, initial_cqa_count=0, new_observations_created=0)
    for key in ('objective', 'targets', 'constraints', 'entity_type', 'title', 'reference_candidate',
                'additional_information', 'workers', 'budget_usd', 'evaluation_mode'):
        if key in spec:
            value[key] = spec[key]
    value['evidence_mode'] = 'existing_only'
    return {'input': value, 'input_mode': spec['input_mode'], 'facts': facts,
            'workspace': str(args.workspace), 'model_calls': 0, 'retrieval_calls': 0}


def operations_for(args, prepared):
    from mas.core import config
    from mas.ui.operations import OperationManager
    if args.config and not args.config.is_file():
        raise ValueError(f'MAS config file does not exist: {args.config}')
    value = prepared['input']
    updates = {'search.volume': 'mid', 'textbook.volume': 'mid', 'assess.workers': value['workers'],
               'budget.usd_max': value['budget_usd'], 'sources.cache_dir': str(args.workspace / 'cache')}
    cli = []
    if args.models:
        cli += ['--models', str(args.models.resolve())]
    if args.config:
        cli += ['--config', str(args.config.resolve())]
    for key, val in updates.items():
        cli += ['--set', f'{key}={val}']
    settings = config.resolve(preset='standard', project_file=args.config, overrides=updates)
    ops = OperationManager(args.workspace / 'store', cli_options=cli, settings=settings,
                           config_hash=settings.hash(), working_directory=ROOT,
                           initiator_kind='agent', initiator_name='agent-run')
    ops.save_settings({key: val for key, val in updates.items() if key != 'sources.cache_dir'})
    return ops


def check_credentials(ops):
    """Validate only; never send a network request or print key material."""
    from mas.core.investigation import investigation_roster
    from mas.core.models import _secret
    try:
        roster = investigation_roster(ops)
        for role in ('proposer', 'critic', 'adjudicator'):
            adapter = roster.adapter(role)
            if not hasattr(adapter, 'api_key_env'):
                raise ValueError(f'{role}: agent-run requires an actual configured API model adapter.')
            _secret(adapter.api_key_env, adapter.api_key_file)
    except FileNotFoundError:
        raise ValueError('No model TOML was found. Supply --models <models.toml> and set its api_key_env or api_key_file before run.') from None
    return roster.role_bindings()


def run_state(workspace):
    path = workspace / 'agent-run-state.json'
    return read_json(path) if path.is_file() else {'format': 'mas-agent-runs-v1', 'runs': []}


def submission(state, request_hash, *, new_run=False):
    """Persist this value before workflow creation; retries reuse the exact idem key."""
    current = state['runs'][-1] if state['runs'] else None
    if current and not new_run:
        if current['request_hash'] != request_hash:
            raise ValueError('The prepared task/settings differ from the saved submission. Use --new-run for another paid investigation or restore the original parameters.')
        return current
    current = {'request_hash': request_hash, 'idempotency_key': 'agent-run:' + uuid.uuid4().hex,
               'workflow_id': None}
    state['runs'].append(current)
    return current


def inspect(workspace):
    path = workspace / 'workbench-workflows.db'
    rows = []
    if path.is_file():
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
            for body, in db.execute('SELECT body FROM workflows ORDER BY rowid DESC'):
                data = json.loads(body)
                rows.append({k: data.get(k) for k in ('workflow_id', 'title', 'state', 'phase', 'message', 'task_id', 'run_id',
                                                      'snapshot_id', 'budget', 'questions', 'error', 'finished_at')})
    return {'command': 'inspect', 'workspace': str(workspace), 'workflows': rows,
            'agent_runs': run_state(workspace)['runs']}


def saved_submission(workspace, idempotency_key):
    path = workspace / 'workbench-workflows.db'
    if path.is_file():
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
            row = db.execute('SELECT body FROM workflows WHERE idem=?', (idempotency_key,)).fetchone()
            if row:
                return json.loads(row[0])
    return None


def ensure_client():
    assets = Path(os.environ.get('MAS_WORKBENCH_ASSET_DIR') or ROOT / 'web/client/dist').resolve()
    if (assets / 'index.html').is_file():
        return
    if os.environ.get('MAS_WORKBENCH_ASSET_DIR'):
        raise ValueError('MAS_WORKBENCH_ASSET_DIR has no index.html; build the client or correct the directory.')
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not npm:
        raise ValueError('Node.js/npm is required to build the UI. Install it, then repeat serve.')
    client = ROOT / 'web/client'
    if not (client / 'node_modules/.package-lock.json').is_file():
        progress('Installing UI dependencies (first use only)')
        subprocess.run([npm, 'ci'], cwd=client, check=True, stdout=sys.stderr)
    progress('Building workbench UI')
    subprocess.run([npm, 'run', 'build'], cwd=client, check=True, stdout=sys.stderr)


def make_api_server(args, ops, api, *, port):
    from mas.ui.server import make_server
    server = make_server(args.workspace / 'store', port=port, settings=ops.settings)
    # Reuse the existing manager: constructing a second one would pause active work.
    server.workbench.operations = ops
    server.workbench.modern = api
    return server


def portable_source(workspace):
    """A model-free evidence source also makes imported records usable in the UI."""
    if (workspace / 'reproduction-import.json').is_file():
        from mas.core.reproduction import prepare_live
        prepared = prepare_live(workspace)
        return {key: value for key, value in prepared.items() if key != 'input'}
    return None


def export_completed(args, ops, api, workflow):
    output = args.output.resolve() if args.output else args.workspace / 'exports' / workflow['workflow_id']
    if (output / 'manifest.json').is_file():
        manifest = read_json(output / 'manifest.json')
        if manifest.get('workflow_id') == workflow['workflow_id'] and manifest.get('snapshot_id') == workflow['snapshot_id']:
            for name, record in manifest.get('files', {}).items():
                path = (output / name).resolve()
                if not path.is_relative_to(output) or not path.is_file() or path.stat().st_size != record['bytes'] or file_hash(path) != record['sha256']:
                    raise ValueError('An existing export file differs from its manifest. Choose --output <new directory>.')
            return {'output': str(output), 'reused': True}
        raise ValueError('The export destination contains another result. Choose --output <new directory>.')
    progress('Exporting the complete actual snapshot, criterion history and cost records')
    api.model.sync()
    server = make_api_server(args, ops, api, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        spec = importlib.util.spec_from_file_location('mas_agent_export', ROOT / 'scripts/export_workbench_run.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from mas.ui.server import address
        return module.export(workflow['workflow_id'], address(server), args.workspace / 'store', output)
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def scientific_outcome(workspace, workflow, input_value):
    if not workflow.get('snapshot_id'):
        return {'status': 'unresolved', 'reason': 'No published snapshot is available.'}
    from mas.core.runtime import Core
    from mas.core import leaderboard
    with Core.open(workspace / 'store', read_only=True) as core:
        snapshot = next(s for s in leaderboard.snapshots(core, workflow['task_id']) if s['snapshot_id'] == workflow['snapshot_id'])
    result = {'status': 'requires_scientific_review', 'result_kind': snapshot.get('result_kind'),
              'all_pass_count': snapshot.get('all_pass_count'), 'no_recommendation': snapshot.get('no_recommendation')}
    reference = str(input_value.get('reference_candidate') or '').casefold()
    if reference:
        matches = [e for e in snapshot['candidate_entries'] if reference == e['candidate_ref'].casefold()
                   or reference in [str(label).casefold() for label in e.get('identity_labels') or []]]
        if len(matches) == 1:
            row = matches[0]
            result['reference'] = {k: row.get(k) for k in ('candidate_ref', 'qualified', 'position', 'preference_score')}
            result['reference_qualified_top_five'] = row.get('qualified') is True and isinstance(row.get('position'), int) and row['position'] <= 5
        else:
            result['reference_match_count'] = len(matches)
    return result


def serve_ui(args, ops, api):
    ensure_client()
    from mas.ui.server import address, serve
    server = make_api_server(args, ops, api, port=args.port)
    url = address(server)
    progress(f'Workbench listening: {url} (Ctrl+C to stop). First opening may need a few minutes to index the saved records.')
    if args.open:
        webbrowser.open(url)
    serve(server)


def recover_submission(api, value, current, prior):
    workflow = api.post('/api/workbench/workflows', {'input': value, 'idempotency_key': current['idempotency_key']})
    if prior and prior['state'] == 'waiting_input':
        # Manager startup pauses nonterminal work. An unanswered question still
        # needs an answer; repeating the command must not pay to ask it again.
        workflow = api.workflows.update(workflow['workflow_id'], state='waiting_input', command=None,
                                        questions=prior.get('questions') or [], message=prior.get('message'))
    elif workflow['state'] == 'paused':
        workflow = api.workflows.command(workflow['workflow_id'], 'resume')
    return workflow


def execute_run(args, prepared, ops):
    state = run_state(args.workspace)
    if not args.models and state.get('models_path'):
        args.models = Path(state['models_path'])
        ops.cli_options += ['--models', str(args.models)]
    # Bind semantic model settings without reading or serializing any credentials.
    from mas.core.investigation import investigation_roster
    try:
        bindings = investigation_roster(ops).role_bindings()
    except FileNotFoundError:
        check_credentials(ops)  # actionable error before any workflow starts
        raise
    request_hash = signature({'input': prepared['input'], 'settings': ops.settings.values, 'models': bindings})
    current = submission(state, request_hash, new_run=args.new_run)
    prior = saved_submission(args.workspace, current['idempotency_key'])
    if not prior or prior['state'] not in TERMINAL:
        check_credentials(ops)
    state['models_path'] = str(args.models.resolve()) if args.models else None
    write_json(args.workspace / 'agent-run-state.json', state)
    from mas.ui.workbench_api import WorkbenchAPI
    api = WorkbenchAPI(ops)
    try:
        value = prepared['input']
        api.validate_input(value)
        workflow = recover_submission(api, value, current, prior)
        current['workflow_id'] = workflow['workflow_id']
        write_json(args.workspace / 'agent-run-state.json', state)
        previous = None
        interrupted = False
        try:
            while workflow['state'] not in TERMINAL | {'waiting_input', 'paused'}:
                status = (workflow['state'], workflow.get('phase'), workflow.get('message'), workflow.get('progress'), workflow.get('budget'))
                if status != previous:
                    progress(f"[{workflow['state']}/{workflow.get('phase')}] {workflow.get('message', '')} | budget={json.dumps(workflow.get('budget'), ensure_ascii=False)}")
                    previous = status
                time.sleep(.5)
                workflow = api.workflows.get(workflow['workflow_id'])
        except KeyboardInterrupt:
            interrupted = True
            api.close()
            worker = api.workflows._threads.get(workflow['workflow_id'])
            progress('Saving the current work boundary; repeat the same run command to continue.')
            while worker and worker.is_alive():
                worker.join(timeout=.5)
            workflow = api.workflows.get(workflow['workflow_id'])
        receipt = {'command': 'run', 'workspace': str(args.workspace), 'workflow': workflow,
                   'workflow_completed': workflow['state'] == 'completed',
                   'scientific_outcome': scientific_outcome(args.workspace, workflow, value),
                   'resubmit_behavior': 'same submission; --new-run creates a separate paid investigation'}
        if workflow['state'] == 'completed':
            receipt['export'] = export_completed(args, ops, api, workflow)
        else:
            write_json(args.workspace / 'agent-run-incomplete.json', receipt)
        write_json(args.workspace / 'agent-run-receipt.json', receipt)
        print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
        if not interrupted and (args.serve or args.open):
            serve_ui(args, ops, api)
        return 0 if workflow['state'] == 'completed' else 3
    finally:
        api.close()
        ops.close()


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('command', choices=('replay', 'plan', 'run', 'serve', 'inspect', 'status'))
    result.add_argument('--workspace', type=Path, required=True, help='Independent workspace directory (never the private source store)')
    result.add_argument('--bootstrap', action='store_true', help='Create/reuse .venv and install Python package only when needed')
    result.add_argument('--bundle', type=Path, help='Local capsule directory containing manifest.json and its asset')
    result.add_argument('--download-cache', type=Path, default=ROOT / 'var/downloads/reproduction')
    result.add_argument('--task', type=Path, help='Task JSON; CSV paths are relative to this file')
    result.add_argument('--models', type=Path, help='Provider/role TOML; keys stay in environment/key files')
    result.add_argument('--config', type=Path, help='Optional MAS settings TOML')
    result.add_argument('--objective')
    result.add_argument('--targets', nargs='+', help='Space-separated target names (quote names containing spaces)')
    result.add_argument('--constraints')
    result.add_argument('--entity-type', choices=('drug', 'carrier', 'general'))
    result.add_argument('--title')
    result.add_argument('--reference-candidate')
    result.add_argument('--workers', type=int)
    result.add_argument('--budget-usd', type=float)
    result.add_argument('--evaluation-mode', choices=('staged', 'full'))
    result.add_argument('--new-run', action='store_true', help='Explicitly submit another live investigation')
    result.add_argument('--output', type=Path, help='New directory for the complete final export')
    result.add_argument('--serve', action='store_true', help='Keep the workbench UI open after replay/run')
    result.add_argument('--open', action='store_true', help='Serve UI and open it in the default browser')
    result.add_argument('--port', type=int, default=8782)
    return result


def main(argv=None):
    # Receipts are UTF-8 JSON even when a Windows launcher inherits a legacy
    # console code page. The original research text must survive redirection.
    for stream in (sys.stdout, sys.stderr):
        configure = getattr(stream, 'reconfigure', None)
        if configure:
            configure(encoding='utf-8')
    args = parser().parse_args(argv)
    for name in ('workspace', 'task', 'models', 'config', 'bundle', 'output', 'download_cache'):
        value = getattr(args, name)
        if value is not None:
            setattr(args, name, value.expanduser().resolve())
    if not 1 <= args.port <= 65535:
        progress('Error: port must be between 1 and 65535.')
        return 2
    try:
        child_code = bootstrap(args.bootstrap)
        if child_code is not None:
            return child_code
        if args.command in ('inspect', 'status'):
            print(json.dumps(inspect(args.workspace), ensure_ascii=False, indent=2))
            return 0
        with workspace_lock(args.workspace):
            if args.command == 'replay':
                imported = ensure_recorded(args)
                from mas.core.reproduction import verify_replay
                progress('Recomputing qualification, scores and ranking with the production engine')
                verified = verify_replay(args.workspace / 'store')
                receipt = {'command': 'replay', 'import': imported, 'verification': verified,
                           'evidence_source': portable_source(args.workspace)}
                write_json(args.workspace / 'agent-replay-receipt.json', receipt)
                print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
                if verified['status'] != 'pass':
                    return 4
                if not (args.serve or args.open):
                    return 0
                prepared = {'input': {'workers': 4, 'budget_usd': 10.0}}
            elif args.command == 'serve':
                if not (args.workspace / 'store/store.db').is_file():
                    raise ValueError('No store/store.db in this workspace. Run replay or plan first.')
                portable_source(args.workspace)
                prepared = {'input': {'workers': args.workers or 4, 'budget_usd': args.budget_usd or 10.0}}
            else:
                prepared = prepare_input(args, load_task(args))
                if args.command == 'plan':
                    prepared.update(command='plan', workload='mid', sources_cache_dir=str(args.workspace / 'cache'),
                                    next_step='Repeat with run and --models <models.toml> to call the configured models.')
                    write_json(args.workspace / 'agent-plan.json', prepared)
                    print(json.dumps(prepared, ensure_ascii=False, indent=2))
                    return 0
            ops = operations_for(args, prepared)
            if args.command == 'run':
                return execute_run(args, prepared, ops)
            from mas.ui.workbench_api import WorkbenchAPI
            api = WorkbenchAPI(ops)
            try:
                serve_ui(args, ops, api)
                return 0
            finally:
                api.close()
                ops.close()
    except (OSError, ValueError, RuntimeError, KeyError, StopIteration, sqlite3.Error, subprocess.SubprocessError) as error:
        progress(f'Error: {error}')
        print(json.dumps({'command': args.command, 'status': 'error', 'workspace': str(args.workspace),
                          'error': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
