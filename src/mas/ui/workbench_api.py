"""Compact investigation API and the built React workbench."""
from __future__ import annotations

import json
import mimetypes
import threading
import uuid
import copy
import os
from pathlib import Path
from urllib.parse import unquote, parse_qs, urlsplit

from mas.core.clock import utc_now
from mas.core.investigation import libraries, investigation_roster
from mas.ui.read_model import ReadModel
from mas.ui.read_api import ReadAPI
from mas.ui.workflows import WorkflowManager
from mas.ui.uploads import UploadStore
from mas.ui.research_briefs import ResearchBriefService

INPUT_FIELDS = {'title', 'objective', 'targets', 'constraints', 'library_id', 'source_task_id',
                'evidence_mode', 'evaluation_mode', 'workers', 'budget_usd', 'reference_candidate',
                'additional_information', 'revision_of_task_id', 'entity_type', 'evidence_upload_id'}


def public_input(value):
    return {k: v for k, v in value.items() if k in INPUT_FIELDS}


class WorkbenchAPI:
    def __init__(self, operations):
        self.operations = operations
        self.model = ReadModel(operations.store_root, cache_path=os.environ.get('MAS_WORKBENCH_READ_CACHE') or None)
        self.briefs = ResearchBriefService(operations.working_directory / 'var/workbench-annotations', self.model,
                                           max_usd=.50)
        self.model.brief_service = self.briefs
        self.read = ReadAPI(self.model)
        self.workflows = WorkflowManager(operations, self.model)
        self.uploads = UploadStore(operations.store_root)
        self.assets = Path(os.environ.get('MAS_WORKBENCH_ASSET_DIR') or operations.working_directory / 'web/client/dist').resolve()
        self._closing = threading.Event()
        self._error = None
        self._thread = threading.Thread(target=self._project, daemon=True, name='mas-workbench-projection')
        self._thread.start()

    def _project(self):
        while not self._closing.is_set():
            try:
                self.model.sync()
                self._error = None
            except Exception as error:
                self._error = str(error)
            self._closing.wait(.5)

    def bootstrap(self):
        status = self.model.status()
        try:
            tasks = self.model.tasks() if status.get('ready') else []
        except (KeyError, ValueError, RuntimeError):
            tasks = []
        available = libraries(self.operations)
        selected = self.operations.current_task
        current = next((t for t in tasks if t['task_id'] == selected), None)
        if not current and tasks:
            selected = tasks[0]['task_id']
        sources = [{'task_id': t['task_id'], 'label': t.get('title') or t.get('objective') or t['task_id']}
                   for t in tasks if t.get('criteria_count', 0) > 0]
        return {'tasks': tasks, 'drafts': self.workflows.drafts(),
                'libraries': [{k: v for k, v in x.items() if k != 'path'} for x in available],
                'evidence_sources': sources, 'current_task_id': selected,
                'workflows': self.workflows.list(), 'operation_token': self.operations.token,
                'defaults': {'objective': '', 'targets': [], 'constraints': '',
                             'entity_type': 'drug', 'evidence_upload_id': None,
                             'library_id': available[0]['id'] if available else None,
                             'source_task_id': selected, 'evidence_mode': 'existing_only',
                             'evaluation_mode': 'staged', 'workers': self.operations.settings['assess.workers'],
                             'budget_usd': self.operations.settings['budget.usd_max']},
                'projection': status}

    def get(self, path, query):
        parts = [unquote(p) for p in path.split('/') if p][2:]
        if parts == ['bootstrap']:
            return self.bootstrap()
        if parts == ['settings']:
            settings = self.operations.configuration()
            settings['fields'] = [field for field in settings['fields']
                                  if field['key'] not in ('interaction.mode', 'rank.mandated_coverage_floor', 'budget.on_exhaust')]
            return settings
        if parts == ['workflows']:
            return {'items': self.workflows.list()}
        if len(parts) == 2 and parts[0] == 'uploads':
            record = self.uploads.read(parts[1])
            return {key: record.get(key) for key in ('upload_id', 'kind', 'filename', 'row_count', 'label', 'entity_type', 'content_sha256')}
        if len(parts) == 2 and parts[0] == 'workflows':
            return self.workflows.get(parts[1])
        if len(parts) >= 3 and parts[0] == 'tasks':
            data = self.read.get(parts[1], parts[2], query, parts[3] if len(parts) > 3 else None)
            if parts[2] == 'overview':
                data['workflow'] = next((wf for wf in self.workflows.list() if wf.get('task_id') == parts[1]), None)
                if data['workflow']:
                    data['task']['input'] = public_input(self.workflows._read(data['workflow']['workflow_id'])['input'])
                    data['input'] = data['task']['input']
                else:
                    data['input'] = self.model.task_input(parts[1])
                    data['task']['input'] = data['input']
            return data
        raise KeyError('This workbench resource is not available.')

    def post(self, path, request):
        parts = [unquote(p) for p in path.split('/') if p][2:]
        if parts == ['settings']:
            self.operations.save_settings(request.get('settings') or {})
            return self.get('/api/workbench/settings', {})
        if parts == ['uploads', 'preview']:
            return self.uploads.public_preview(self.uploads.preview(request))
        if len(parts) == 3 and parts[0] == 'uploads' and parts[2] == 'commit':
            return self.uploads.commit(parts[1], request)
        if parts == ['drafts']:
            return self.workflows.save_draft(dict(request, input=public_input(request.get('input') or {})))
        if parts == ['workflows']:
            value = public_input(request.get('input') or {})
            self.validate_input(value)
            return self.workflows.start(dict(request, input=value))
        if len(parts) == 3 and parts[0] == 'workflows':
            if parts[2] == 'commands':
                return self.workflows.command(parts[1], request.get('command'))
            if parts[2] == 'answers':
                return self.workflows.answers(parts[1], request.get('answers') or {})
        if len(parts) == 3 and parts[0] == 'tasks' and parts[2] == 'research-briefs':
            reference = request.get('criterion_ref')
            if not isinstance(reference, str) or not reference:
                raise ValueError('Choose one criterion version for a research interpretation.')
            self.briefs.roster = investigation_roster(self.operations)
            result = self.briefs.generate(parts[1], [reference])
            return {'task_id': parts[1], 'result': result, 'overview': self.briefs.overview(parts[1])}
        if len(parts) == 5 and parts[0] == 'tasks' and parts[2] == 'criteria' and parts[4] == 'revisions':
            return self.revise(parts[1], parts[3], request)
        raise ValueError('This operation is not available.')

    def validate_input(self, value):
        """Reject incompatible dataset selections before starting a paid investigation."""
        selected = value.get('library_id')
        uploaded = str(selected or '').startswith('upload:')
        if not value.get('entity_type'):
            value['entity_type'] = self.uploads.library(selected).get('entity_type', 'general') if uploaded else 'drug'
        entity_type = value['entity_type']
        if entity_type not in ('drug', 'carrier', 'general'):
            raise ValueError('Choose drugs, carriers or general candidates.')
        if entity_type != 'drug' and not uploaded:
            raise ValueError('Choose an uploaded candidate list for carriers or general candidates.')
        evidence_id = value.get('evidence_upload_id')
        if uploaded or evidence_id:
            self.uploads.library(selected)
            if not evidence_id:
                raise ValueError('Import a measurement table for this candidate list before starting. Candidate descriptions alone are not measurements.')
            if value.get('evidence_mode') == 'retrieve':
                raise ValueError('Uploaded candidate studies currently use supplied measurements and saved evidence. Select Use saved evidence.')
        if evidence_id:
            record = self.uploads.read(evidence_id)
            if record.get('kind') != 'measurements' or record.get('library_id') != selected:
                raise ValueError('Choose the measurement table imported for this exact candidate library.')

    def revise(self, task_id, criterion_id, request):
        from mas.core import criteria, task, pool
        from mas.core.runtime import Core
        from mas.core.journal import actor
        changes, reason = request.get('changes') or {}, str(request.get('reason') or '').strip()
        if not reason:
            raise ValueError('Explain why the criterion should change.')
        if set(changes) - {'name', 'definition', 'role', 'direction', 'cutoff'}:
            raise ValueError('Only the displayed criterion fields can be changed.')
        detail = self.model.criterion(task_id, criterion_id)
        if detail.get('task_required') or detail.get('editable') is False:
            raise ValueError('Edit the research objective to change a required task condition.')
        active = next((w for w in self.workflows.list() if w.get('task_id') == task_id and w['state'] not in ('completed', 'unresolved', 'failed', 'cancelled')), None)
        if active:
            # The running writer applies the request at its next checkpoint.
            data = self.workflows._read(active['workflow_id'])
            queued = data.get('_pending_revisions') or []
            queued.append({'criterion_id': criterion_id, 'changes': changes, 'reason': reason})
            self.workflows.update(active['workflow_id'], _pending_revisions=queued,
                message='The change is queued for the next saved work boundary')
            return {'task_id': task_id, 'workflow': self.workflows.get(active['workflow_id']),
                    'message': 'The revision will be applied at the next saved work boundary.'}
        with Core.open(self.operations.store_root) as core:
            result = apply_revision(core, task_id, criterion_id, changes, reason,
                                    actor(self.operations.initiator['kind'], self.operations.initiator['id'], 'operator'))
            context = task.get(core, task_id)
        prior = next((w for w in self.workflows.list() if w.get('task_id') == task_id), None)
        if prior and result.get('changed', True):
            value = copy.deepcopy(self.workflows._read(prior['workflow_id'])['input'])
            value.update(continue_task_id=task_id, reuse_from_run_id=prior.get('run_id') if prior.get('snapshot_id') else None,
                         _review_rule_refs=[result.get('rule_ref')], title=context.get('title') or prior['title'])
            if result.get('requires_review') and not result.get('rule_ref'):
                previous = self.workflows._read(prior['workflow_id'])['_checkpoints'].get('derivation') or {}
                value['_resume_pool_run_id'] = previous.get('run_id')
                value['_review_rule_refs'] = []
            result['workflow'] = self.workflows.start({'input': value, 'idempotency_key': 'revision-' + uuid.uuid4().hex})
        return result

    def asset(self, target):
        path = urlsplit(target).path
        relative = unquote(path[len('/workbench/'):]) if path.startswith('/workbench/') else ''
        wanted = (self.assets / (relative or 'index.html')).resolve()
        if not wanted.is_relative_to(self.assets.resolve()) or not wanted.is_file():
            return None
        mime = mimetypes.guess_type(wanted.name)[0] or 'application/octet-stream'
        if wanted.suffix == '.js':
            mime = 'text/javascript'
        return mime, wanted.read_bytes()

    def close(self):
        self._closing.set()
        self.workflows.close()


def apply_revision(core, task_id, criterion_id, changes, reason, by):
    """Append a criterion version; frozen snapshots remain bound to the old refs."""
    from mas.core import criteria, pool
    rule_ref = criterion_id if criterion_id.startswith('rule_') else None
    attr_ref = criterion_id if criterion_id.startswith('attr_') else None
    if criterion_id.startswith('cri_'):
        entry = pool.fold(core, task_id).get(criterion_id.split('@v')[0])
        if not entry:
            raise ValueError('This criterion is no longer available.')
        promoted = entry.get('promoted_as') or {}
        if isinstance(promoted, dict):
            rule_ref, attr_ref = promoted.get('rule_ref'), promoted.get('attribute_ref')
        if not rule_ref:
            item = copy.deepcopy(entry['item'])
            item['attribute'].update({k: changes[k] for k in ('name', 'definition', 'direction') if k in changes})
            if 'role' in changes:
                item['rule']['rule_kind'] = changes['role']
            if 'cutoff' in changes:
                item['rule']['cutoff'] = changes['cutoff']
                item['rule'].pop('bound_support', None)
            item.update(validator_problems=[], critic_findings=[])
            writer = pool.Pool(core, task_id, by=by, run_id=(entry.get('history') or [{}])[-1].get('round_run_id') or '')
            version = writer.at('user_edit', 0).revise(entry, item, reason_text=reason, state='needs_refine', reason_kind='user_revision')
            return {'task_id': task_id, 'version': version, 'changed': True, 'requires_review': True,
                    'message': 'A new proposal version was saved for review.'}
    records = criteria.registered_rule_records(core, task_id)
    if rule_ref and '@v' not in rule_ref:
        record = next((r for r in records if r['rule_id'] == rule_ref), None)
        rule_ref = f"{record['rule_id']}@v{record['version']}" if record else None
    if not rule_ref and attr_ref:
        record = next((r for r in records if r['attribute_ref'] == attr_ref or
                       ('@v' not in attr_ref and r['attribute_ref'].split('@v')[0] == attr_ref)), None)
        rule_ref = f"{record['rule_id']}@v{record['version']}" if record else None
    if not rule_ref:
        raise ValueError('Choose a registered criterion to revise.')
    entry = next((r for r in records if f"{r['rule_id']}@v{r['version']}" == rule_ref), None)
    if entry:
        attribute = criteria.load(core, entry['attribute_ref'], task_id)
        if criteria.is_task_mandated(attribute):
            raise ValueError('Edit the research objective to change a required task condition.')
    attribute_changes = {k: changes[k] for k in ('name', 'definition', 'direction') if k in changes}
    rule_changes = {}
    if 'role' in changes:
        rule_changes['rule_kind'] = changes['role']
    if 'cutoff' in changes:
        rule_changes['cutoff'] = changes['cutoff']
    result = criteria.revise_for_workbench(core, task_id, rule_ref,
        {'attribute': attribute_changes, 'rule': rule_changes}, reason=reason, by=by)
    return dict(result, task_id=task_id, version=result['rule_ref'],
                message='A new criterion version was saved for review. Earlier results remain unchanged.')
