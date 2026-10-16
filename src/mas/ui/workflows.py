"""Durable local investigation commands, drafts and progress.

Scientific records remain in the core journal. This small operational database
keeps browser commands and their outcomes across workbench restarts.
"""
from __future__ import annotations

import copy
import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from mas.core.clock import utc_now

PHASES = [('task', 'Understand the task'), ('evidence', 'Prepare evidence'),
          ('propose', 'Discover criteria'), ('refine', 'Review and refine'),
          ('review', 'Resolve decisions'), ('freeze', 'Save evaluation rules'),
          ('screen', 'Screen candidates'), ('results', 'Publish results')]
TERMINAL = {'completed', 'unresolved', 'failed', 'cancelled'}


class WorkflowStopped(InterruptedError):
    def __init__(self, *, paused=False):
        super().__init__('Paused for service restart' if paused else 'Stopped by the operator')
        self.paused = paused


class WorkflowRevised(Exception):
    """The previous evaluation was closed and a new rule version is ready."""


class WorkflowManager:
    def __init__(self, operations, read_model):
        self.operations, self.read_model = operations, read_model
        self.root = operations.store_root.parent
        self.path = self.root / 'workbench-workflows.db'
        self._lock = threading.RLock()
        self._writer = threading.Lock()
        self._threads = {}
        self._closing = threading.Event()
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS workflows (id TEXT PRIMARY KEY, idem TEXT UNIQUE NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (cursor INTEGER PRIMARY KEY AUTOINCREMENT, recorded_at TEXT NOT NULL, body TEXT NOT NULL);
            ''')
            for row in db.execute('SELECT id,body FROM workflows').fetchall():
                data = json.loads(row[1])
                if data['state'] not in TERMINAL:
                    data.update(state='paused', command='pause', message='Workbench restarted. Continue from the saved checkpoint.', updated_at=utc_now())
                    db.execute('UPDATE workflows SET body=? WHERE id=?', (json.dumps(data), row[0]))

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.execute('PRAGMA journal_mode=WAL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def _read(self, workflow_id):
        with self.db() as db:
            row = db.execute('SELECT body FROM workflows WHERE id=?', (workflow_id,)).fetchone()
        if not row:
            raise ValueError('This investigation is not available.')
        return json.loads(row[0])

    def update(self, workflow_id, **fields):
        with self._lock, self.db() as db:
            row = db.execute('SELECT body FROM workflows WHERE id=?', (workflow_id,)).fetchone()
            data = json.loads(row[0])
            data.update(fields, updated_at=utc_now())
            db.execute('UPDATE workflows SET body=? WHERE id=?', (json.dumps(data, ensure_ascii=False), workflow_id))
            public = self._public(data)
            db.execute('INSERT INTO events(recorded_at,body) VALUES (?,?)',
                       (utc_now(), json.dumps({'kind': 'workflow', 'workflow': public, 'task_id': data.get('task_id')}, ensure_ascii=False)))
        return public

    def _public(self, data):
        out = {k: copy.deepcopy(v) for k, v in data.items() if not k.startswith('_') and k not in ('command', 'input', 'config', 'source_manifest')}
        state = out['state']
        out.update(can_pause=state in ('running', 'queued'), can_resume=state == 'paused',
                   can_stop=state not in TERMINAL,
                   can_reevaluate=state in TERMINAL and bool(data.get('_checkpoints', {}).get('derivation'))
                   and float(data.get('_budget_used', {}).get('usd') or 0) < float(data['input'].get('budget_usd') or 10))
        return out

    def get(self, workflow_id):
        data = self._read(workflow_id)
        out = self._public(data)
        if (data.get('run_id') and data['state'] == 'running' and data.get('phase') == 'screen'
                and not data.get('command') and hasattr(self.read_model, 'run_progress')):
            try:
                current = self.read_model.run_progress(data['run_id']) or {}
            except (KeyError, ValueError, RuntimeError):
                current = {}
            if current.get('progress') and current.get('state') in ('running', 'paused'):
                out['progress'] = current['progress']
            if current.get('message') and current.get('state') in ('running', 'paused'):
                out['message'] = current['message']
            if current.get('last_activity_at'):
                out['last_activity_at'] = current['last_activity_at']
        return out

    def list(self):
        with self.db() as db:
            ids = [row[0] for row in db.execute('SELECT id FROM workflows ORDER BY rowid DESC')]
        return [self.get(i) for i in ids]

    def drafts(self):
        with self.db() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT body FROM drafts ORDER BY rowid DESC')]

    def save_draft(self, request):
        value = request.get('input')
        if not isinstance(value, dict):
            raise ValueError('Enter a research objective first.')
        draft = {'draft_id': request.get('draft_id') or 'draft_' + uuid.uuid4().hex,
                 'input': value, 'updated_at': utc_now()}
        with self._lock, self.db() as db:
            db.execute('INSERT INTO drafts(id,body) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',
                       (draft['draft_id'], json.dumps(draft, ensure_ascii=False)))
        return draft

    def start(self, request):
        idem = str(request.get('idempotency_key') or '')
        if not idem:
            raise ValueError('A submission identity is required. Please submit the form again.')
        with self._lock, self.db() as db:
            old = db.execute('SELECT id FROM workflows WHERE idem=?', (idem,)).fetchone()
            if old:
                return self.get(old[0])
            value = request.get('input')
            if not isinstance(value, dict) or not str(value.get('objective') or '').strip():
                raise ValueError('Describe the research objective before starting.')
            if value.get('evidence_mode', 'existing_only') not in ('existing_only', 'retrieve'):
                raise ValueError('Choose an evidence mode.')
            if value.get('evaluation_mode', 'staged') not in ('staged', 'full'):
                raise ValueError('Choose staged screening or full evaluation.')
            continued = value.get('continue_task_id')
            data = {'workflow_id': 'wf_' + uuid.uuid4().hex, 'task_id': continued, 'draft_id': request.get('draft_id'),
                    'title': value.get('title') or str(value['objective']).strip()[:90], 'input': value,
                    'state': 'queued', 'phase': 'task', 'message': 'Waiting to start', 'started_at': utc_now(),
                    'updated_at': utc_now(), 'finished_at': None, 'command': None,
                    'progress': {'completed': 0, 'planned': None, 'denominator_kind': 'unknown'},
                    'budget': {'used_usd': 0, 'limit_usd': float(value.get('budget_usd') or 10), 'cost_status': 'not_started'},
                    'phases': [{'id': i, 'label': label, 'state': 'queued'} for i, label in PHASES],
                    'questions': [], 'run_id': None, 'snapshot_id': None,
                    'config': self.operations.saved_overrides,
                    '_checkpoints': ({'normalized': {'task_id': continued}, **({} if value.get('_resume_pool_run_id') else
                                     {'derivation': {'continued_from_task': continued}})}
                                     if continued else {}), '_budget_used': {}}
            db.execute('INSERT INTO workflows(id,idem,body) VALUES (?,?,?)',
                       (data['workflow_id'], idem, json.dumps(data, ensure_ascii=False)))
        self._launch(data['workflow_id'])
        return self.get(data['workflow_id'])

    def _launch(self, workflow_id):
        old = self._threads.get(workflow_id)
        if old and old.is_alive():
            return
        thread = threading.Thread(target=self._work, args=(workflow_id,), name='mas-investigation', daemon=True)
        self._threads[workflow_id] = thread
        thread.start()

    def command(self, workflow_id, command):
        if command not in ('pause', 'resume', 'stop', 'reevaluate'):
            raise ValueError('Choose pause, resume, stop or reevaluate.')
        data = self._read(workflow_id)
        if command == 'reevaluate':
            thread = self._threads.get(workflow_id)
            if data['state'] not in TERMINAL or (thread and thread.is_alive()):
                raise ValueError('Stop the current evaluation and wait for its saved boundary first.')
            if not data.get('_checkpoints', {}).get('derivation'):
                raise ValueError('Complete criterion development before evaluating saved criteria.')
            if not self._public(data)['can_reevaluate']:
                raise ValueError('The saved research budget is exhausted.')
            checkpoints = dict(data['_checkpoints'])
            previous_run = (checkpoints.get('screen_started') or {}).get('run_id')
            history = [*(data.get('_evaluation_history') or []), {
                'recorded_at': utc_now(), 'state': data['state'], 'phase': data['phase'],
                'run_id': previous_run, 'snapshot_id': data.get('snapshot_id'),
                'finished_at': data.get('finished_at'), 'budget': data.get('budget'),
                'phases': copy.deepcopy(data['phases']),
                'checkpoints': {key: checkpoints.get(key) for key in ('review', 'freeze', 'screen_started', 'screen')},
                'reason': 'Evaluate the current reviewed criteria in a new frozen version; preserve prior results.'}]
            for key in ('review', 'freeze', 'screen_started', 'screen'):
                checkpoints.pop(key, None)
            value = dict(data['input'])
            value.pop('_review_rule_refs', None)
            value.pop('reuse_from_run_id', None)
            if previous_run:
                value['reuse_from_run_id'] = previous_run
            phases = copy.deepcopy(data['phases'])
            for phase in phases:
                if phase['id'] in ('review', 'freeze', 'screen', 'results'):
                    phase['state'] = 'queued'
                    phase.pop('finished_at', None)
                    phase.pop('started_at', None)
            runs = list(dict.fromkeys([*(data.get('_run_history') or []), *([previous_run] if previous_run else [])]))
            self.update(workflow_id, input=value, _checkpoints=checkpoints, _evaluation_history=history,
                _run_history=runs, phases=phases, state='queued', command=None, phase='review',
                questions=[],
                phase_label=dict(PHASES)['review'], run_id=None, snapshot_id=None, finished_at=None,
                error=None, progress={'completed': 0, 'planned': None, 'denominator_kind': 'unknown'},
                message='Preparing a new evaluation from the saved criteria and evidence')
            self._launch(workflow_id)
            return self.get(workflow_id)
        if data['state'] in TERMINAL:
            raise ValueError('This investigation has ended. Start a new investigation to change its results.')
        if command == 'pause':
            self.update(workflow_id, command='pause', message='Pausing after the current activity')
        elif command == 'stop':
            self.update(workflow_id, command='stop', message='Stopping after the current activity')
            if not self._threads.get(workflow_id) or not self._threads[workflow_id].is_alive():
                self.update(workflow_id, state='cancelled', finished_at=utc_now(), message='Stopped')
        else:
            self.update(workflow_id, command=None, state='queued', message='Continuing from the saved checkpoint')
            self._launch(workflow_id)
        return self.get(workflow_id)

    def answers(self, workflow_id, answers):
        data = self._read(workflow_id)
        if data['state'] != 'waiting_input':
            raise ValueError('This investigation is not waiting for an answer.')
        value = dict(data['input'])
        for key, answer in answers.items():
            if key == 'objective':
                value['objective'] = answer
            elif key in ('source_task_id', 'library_id', 'library', 'evidence_upload_id', 'entity_type'):
                value['library_id' if key == 'library' else key] = answer
            else:
                value['additional_information'] = str(value.get('additional_information') or '') + '\n' + str(answer)
        self.update(workflow_id, input=value, questions=[], state='queued', command=None)
        self._launch(workflow_id)
        return self.get(workflow_id)

    def checkpoint(self, workflow_id, run_id=None):
        while True:
            data = self._read(workflow_id)
            if data.get('command') == 'stop' or self._closing.is_set():
                raise WorkflowStopped(paused=self._closing.is_set())
            if data.get('command') != 'pause':
                if data['state'] in ('paused', 'queued'):
                    self.update(workflow_id, state='running', message='Continuing the investigation')
                return
            if data['state'] != 'paused':
                self.update(workflow_id, state='paused', message='Paused at a saved work boundary')
            self._closing.wait(.3)

    def phase(self, workflow_id, phase, message, **fields):
        data = self._read(workflow_id)
        phases = data['phases']
        order = [i for i, _ in PHASES]
        for row in phases:
            if order.index(row['id']) < order.index(phase) and row['state'] == 'running':
                row.update(state='completed', finished_at=utc_now())
            if row['id'] == phase:
                row.update(state='running', started_at=row.get('started_at') or utc_now())
        if data.get('phase') != phase:
            fields = {'active_stage': None, 'iteration': None, 'batch': None, **fields}
        self.update(workflow_id, phase=phase, phase_label=dict(PHASES)[phase], phases=phases,
                    state='running', message=message,
                    **({'progress': {'completed': 0, 'planned': None, 'denominator_kind': 'unknown'}} if 'progress' not in fields else {}), **fields)

    def record_checkpoint(self, workflow_id, key, result):
        data = self._read(workflow_id)
        checkpoints = dict(data['_checkpoints'], **{key: result})
        self.update(workflow_id, _checkpoints=checkpoints)

    def _work(self, workflow_id):
        from mas.core.investigation import execute
        try:
            with self._writer:
                while True:
                    self.checkpoint(workflow_id)
                    try:
                        execute(self, workflow_id)
                        break
                    except WorkflowRevised:
                        self.update(workflow_id, state='running', command=None,
                                    message='Re-evaluating the affected criteria with the new version')
        except WorkflowStopped as stopped:
            paused = stopped.paused or self._closing.is_set()
            self.update(workflow_id, state='paused' if paused else 'cancelled',
                        message='Saved for continuation' if paused else 'Stopped', finished_at=None if paused else utc_now())
        except Exception as error:
            self.update(workflow_id, state='failed', message='The investigation needs attention',
                        error={'code': type(error).__name__, 'message': str(error)[:1000]}, finished_at=utc_now())

    def events(self, after=0):
        with self.db() as db:
            return [{'cursor': row[0], **json.loads(row[1])} for row in db.execute(
                'SELECT cursor,body FROM events WHERE cursor>? ORDER BY cursor LIMIT 100', (after,))]

    def close(self):
        self._closing.set()
