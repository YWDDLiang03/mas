"""Evidence collection display metadata, kept separately from all scientific records."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import threading

from .evidence_groups import source_kind


_PUBLIC_BODY = (
    "coalesce(json_extract(body,'$.visibility'),'default') NOT IN ('evaluator_only','private','recovery') "
    "AND coalesce(json_extract(body,'$.payload.visibility'),'default') NOT IN ('evaluator_only','private','recovery') "
    "AND coalesce(json_extract(body,'$.payload.evaluator_only'),0)!=1"
)


def _public_manifest(source, artifact_id):
    if not artifact_id:
        return {}
    row = source.execute("SELECT body FROM artifacts WHERE artifact_id=? AND kind='existing_fact_manifest' AND " + _PUBLIC_BODY,
                         (artifact_id,)).fetchone()
    envelope = json.loads(row[0]) if row else {}
    payload = envelope.get('payload') or {}
    if (envelope.get('kind') != 'existing_fact_manifest'
            or envelope.get('visibility') in ('evaluator_only', 'private', 'recovery')
            or payload.get('visibility') in ('evaluator_only', 'private', 'recovery')
            or payload.get('evaluator_only')):
        return {}
    return payload


class EvidenceCollections:
    def __init__(self, model, display_path):
        self.model, self.path = model, Path(display_path).resolve()
        if self.path == model.source_path or self.path.is_relative_to(model.source_path.parent):
            raise ValueError('Collection display metadata must be outside the scientific source store')
        self._lock, self._base_cache = threading.RLock(), {}

    def _display(self):
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if data.get('version') != 1 or not isinstance(data.get('collections'), dict):
            raise ValueError('The collection display metadata is invalid')
        return data['collections']

    def get(self, task_id):
        with self._lock, self.model._cache() as db, self.model._source() as source:
            self.model._ready(db)
            task = self.model._task(db, task_id)
            latest = self.model._snapshot_row(db, task_id, None)
            watermark = db.execute('SELECT source_row FROM claims WHERE task_id=? ORDER BY source_row DESC LIMIT 1', (task_id,)).fetchone()
            key = (task.get('version'), watermark[0] if watermark else 0, latest['snapshot_id'] if latest else None)
            cached = self._base_cache.get(task_id)
            if cached is None or cached[0] != key:
                raw = source.execute("SELECT body FROM events WHERE stream_id=? AND event_type='task.version_recorded' AND " + _PUBLIC_BODY + " ORDER BY seq DESC LIMIT 1", (task_id,)).fetchone()
                event = json.loads(raw[0]) if raw else {}
                context = self.model._artifact(source, (event.get('payload') or {}).get('artifact_id'), {'task_context'})
                manifest_ref = context.get('evidence_fact_manifest_ref')
                manifest = _public_manifest(source, manifest_ref)
                records = manifest.get('source_records') or {}
                kinds = dict.fromkeys(('literature', 'database', 'model', 'other'), 0)
                if manifest and isinstance(manifest.get('claims'), list) and records:
                    count, total = len(manifest['claims']), len(records)
                    for sid, pointer in records.items():
                        metadata = self.model._artifact(source, pointer.get('artifact_id'), {'source'})
                        first = db.execute('SELECT body FROM claims WHERE task_id=? AND source_id=? LIMIT 1', (task_id, sid)).fetchone()
                        kinds[source_kind(metadata, json.loads(first[0]) if first else None)] += 1
                    basis = 'pinned_fact_manifest'
                else:
                    count, total = db.execute("SELECT count(*),count(DISTINCT source_id) FROM claims WHERE task_id=? AND admission_state='admitted'", (task_id,)).fetchone()
                    for row in db.execute("SELECT c.source_id,c.body,s.body AS metadata FROM claims c LEFT JOIN evidence_sources s ON s.task_id=c.task_id AND s.source_id=c.source_id WHERE c.task_id=? AND c.admission_state='admitted' GROUP BY c.source_id", (task_id,)):
                        kinds[source_kind(json.loads(row['metadata']) if row['metadata'] else {}, json.loads(row['body']))] += 1
                    basis = 'admitted_task_evidence'
                cutoff = context.get('evidence_cutoff')
                if latest:
                    created = source.execute("SELECT body FROM events WHERE stream_id=? AND event_type='run.created' AND " + _PUBLIC_BODY + " ORDER BY seq LIMIT 1", (latest['run_id'],)).fetchone()
                    binding_id = (json.loads(created[0]).get('payload') or {}).get('binding_artifact_id') if created else None
                    binding = self.model._artifact(source, binding_id, {'run_binding'})
                    cutoff = binding.get('evidence_cutoff')
                saved_input = task.get('input') or {}
                topics = [str(value) for value in saved_input.get('targets') or [] if value]
                title = task.get('title') or ''
                if len(title) > 64:
                    title = ' / '.join(topics[:3]) + ' evidence' if topics else title[:61].rstrip() + '…'
                description = task.get('objective') or ''
                if len(description) > 300:
                    description = description[:297].rstrip() + '…'
                base = {'task_id': task_id, 'label': title or 'Saved evidence collection', 'description': description,
                        'topics': topics, 'topics_basis': 'task_targets', 'claim_count': count, 'source_count': total,
                        'source_counts': kinds, 'counts_basis': basis, 'cutoff': cutoff,
                        'pinned_at': manifest.get('created_at'), 'manifest_ref': manifest_ref,
                        'bound_source_task_id': saved_input.get('source_task_id'),
                        'original_title': task.get('title'), 'original_objective': task.get('objective'),
                        'display_origin': 'recorded_task_fields'}
                self._base_cache[task_id] = (key, base)
            result = copy.deepcopy(self._base_cache[task_id][1])
            display = self._display().get(task_id)
            if display:
                result.update(display, display_origin='ui_metadata')
            return result

    def list(self, task_ids):
        return [self.get(task_id) for task_id in dict.fromkeys(task_ids)]

    def update(self, task_id, display):
        if not isinstance(display, dict) or set(display) - {'label', 'description', 'topics'}:
            raise ValueError('Edit only the collection name, description and topics')
        current = self.get(task_id)
        label = display.get('label', current['label'])
        description = display.get('description', current['description'])
        topics = display.get('topics', current['topics'])
        if not isinstance(label, str) or not label.strip() or len(label) > 80:
            raise ValueError('Use a collection name of 1–80 characters')
        if not isinstance(description, str) or len(description) > 600:
            raise ValueError('Keep the collection description within 600 characters')
        if not isinstance(topics, list) or len(topics) > 20 or any(not isinstance(value, str) or len(value) > 80 for value in topics):
            raise ValueError('Use at most 20 topics, each within 80 characters')
        cleaned = {'label': label.strip(), 'description': description.strip(),
                   'topics': list(dict.fromkeys(value.strip() for value in topics if value.strip()))}
        with self._lock:
            all_display = self._display()
            all_display[task_id] = cleaned
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + '.tmp')
            temporary.write_text(json.dumps({'version': 1, 'collections': all_display}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            temporary.replace(self.path)
        return self.get(task_id)
