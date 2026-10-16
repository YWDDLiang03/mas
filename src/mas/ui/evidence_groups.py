"""Read-only, source-ID-based evidence pages. No scientific record is changed."""
from __future__ import annotations

import json
import copy
import hashlib
from typing import Any

from .evidence_read import EvidenceRead

KINDS = ('literature', 'database', 'model', 'other', 'all')
_STATUSES = {
    'model': ('model_prediction_record',),
    'database': ('database_entry', 'user_supplied_data', 'curated_measurement', 'experiment_record'),
    'literature': ('peer_reviewed', 'peer_reviewed_paper', 'reference_text', 'tertiary_reference', 'preprint', 'user_supplied_document'),
}


def finding_identity(raw_claim):
    """Compare complete saved scientific fields; never infer from a summary DTO.

    This key only folds repeated display cards. Every admission, actor and reuse
    record remains available in the group's original records.
    """
    if not isinstance(raw_claim, dict):
        return None
    location = raw_claim.get('location')
    if (not raw_claim.get('source_ref') or not isinstance(location, dict)
            or not location.get('quoted_span') or not location.get('locator_value')
            or not (raw_claim.get('normalized_statement') or raw_claim.get('claim_text'))
            or not all(key in raw_claim for key in ('scope', 'conditions', 'entities', 'value', 'determination_basis'))):
        return None
    record_fields = {'claim_id', 'task_id', 'run_id', 'version', 'recorded_at', 'created_at',
        'reuse_of_claim_id', 'reuse_of_artifact_id', 'reused_from_claim_id',
        'extraction_actor', 'admission_state', 'admission_reasons'}
    scientific = {key: value for key, value in raw_claim.items() if key not in record_fields}
    text = json.dumps(scientific, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def source_kind(metadata, claim=None):
    claim = claim or {}
    status = metadata.get('source_status')
    evidence_kind = (claim.get('context') or {}).get('evidence_kind') or claim.get('evidence_kind')
    if status == 'model_prediction_record':
        return 'model'
    if status in ('database_entry', 'user_supplied_data', 'curated_measurement', 'experiment_record'):
        return 'database'
    if status in ('peer_reviewed', 'peer_reviewed_paper', 'reference_text', 'tertiary_reference', 'preprint', 'user_supplied_document'):
        return 'literature'
    if evidence_kind == 'model_prediction':
        return 'model'
    if evidence_kind in ('database_entry', 'curated_measurement'):
        return 'database'
    if evidence_kind in (
            'peer_reviewed', 'reference_text', 'tertiary_reference', 'user_supplied_document', 'preprint'):
        return 'literature'
    return 'other'


def source_kind_sql() -> str:
    # Source metadata takes priority. The fallback uses recorded evidence kinds,
    # never words in the title/quote to infer scientific use or peer review.
    return """CASE
      WHEN json_extract(s.body,'$.source_status')='model_prediction_record' THEN 'model'
      WHEN json_extract(s.body,'$.source_status') IN ('database_entry','user_supplied_data','curated_measurement','experiment_record') THEN 'database'
      WHEN json_extract(s.body,'$.source_status') IN ('peer_reviewed','peer_reviewed_paper','reference_text','tertiary_reference','preprint','user_supplied_document') THEN 'literature'
      WHEN json_extract(c.body,'$.context.evidence_kind')='model_prediction' THEN 'model'
      WHEN json_extract(c.body,'$.context.evidence_kind') IN ('database_entry','curated_measurement') THEN 'database'
      WHEN json_extract(c.body,'$.context.evidence_kind') IN
        ('peer_reviewed','reference_text','tertiary_reference','user_supplied_document','preprint')
        THEN 'literature' ELSE 'other' END"""


def _where(model, db, task_id, selected, *, q='', criterion_ref='', attribute_ref='', rule_ref='',
           candidate_ref='', source_id='', kind='all'):
    clauses, values = ["c.task_id=?", "c.admission_state='admitted'"], [task_id]
    if selected:
        clauses.append('c.source_row<=?')
        values.append(selected['published_row'])
    if q:
        clauses.append("c.search_text LIKE ? ESCAPE '\\'")
        values.append('%' + str(q).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%')
    if source_id:
        clauses.append('c.source_id=?')
        values.append(source_id)
    links, params = ['u.task_id=?'], [task_id]
    if criterion_ref:
        if '@v' not in criterion_ref or criterion_ref.startswith('change:'):
            saved = model._resolve_criterion(db, task_id, criterion_ref)
            saved = json.loads(saved['body']) if 'body' in saved.keys() else dict(saved)
            criterion_ref = saved.get('rule_ref') or saved.get('attribute_ref') or f"{saved['criterion_id']}@v{saved['version']}"
        field = 'rule_ref' if criterion_ref.startswith('rule_') else 'attribute_ref' if criterion_ref.startswith('attr_') else 'criterion_ref'
        links.append(f'u.{field}=?')
        params.append(criterion_ref)
    for field, value in (('attribute_ref', attribute_ref), ('rule_ref', rule_ref), ('candidate_ref', candidate_ref)):
        if value:
            links.append(f'u.{field}=?')
            params.append(value)
    if criterion_ref or attribute_ref or rule_ref or candidate_ref:
        scope, scope_params = EvidenceRead._scope(selected)
        index = ('evidence_link_candidate' if candidate_ref else 'evidence_link_rule' if rule_ref or criterion_ref.startswith('rule_')
                 else 'evidence_link_attribute' if attribute_ref or criterion_ref.startswith('attr_') else 'evidence_link_criterion')
        relation = 'SELECT u.claim_id FROM evidence_links u INDEXED BY ' + index + ' WHERE ' + ' AND '.join(links) + scope
        if candidate_ref and not (criterion_ref or attribute_ref or rule_ref):
            relation = ('SELECT direct.claim_id FROM claims direct WHERE direct.task_id=? AND direct.candidate_ref=? UNION ' + relation)
            params = [task_id, candidate_ref, *params]
        clauses.append('c.claim_id IN (' + relation + ')')
        values.extend([*params, *scope_params])
    if kind != 'all':
        clauses.append('(' + source_kind_sql() + ')=?')
        values.append(kind)
    return ' AND '.join(clauses), values


def _unique(values, limit=8):
    out = []
    for value in values:
        if isinstance(value, str) and value.strip() and value not in out:
            out.append(value)
    return out[:limit]


def _evaluation_entries(model, db, source, task_id, selected):
    frozen = model._meta(db).get(f'frozen:{task_id}') or {}
    if not selected:
        return (frozen.get('entries') or [], frozen.get('rule_set_ref')) if frozen else (None, None)
    ref = (json.loads(selected['body']) or {}).get('rules@v')
    if not ref:
        return None, None
    if ref == frozen.get('rule_set_ref'):
        return frozen.get('entries') or [], ref
    from .evidence_collections import _PUBLIC_BODY
    row = source.execute("SELECT body FROM events WHERE stream_id=? AND event_type='criterion.version_approved' "
                         "AND json_extract(body,'$.payload.rule_set_ref')=? AND rowid<=? AND " + _PUBLIC_BODY +
                         " ORDER BY seq DESC LIMIT 1", (task_id, ref, selected['published_row'])).fetchone()
    artifact = (json.loads(row[0]).get('payload') or {}).get('artifact_id') if row else None
    rules = model._artifact(source, artifact, {'rule_set'})
    return (rules.get('entries') or [], ref) if rules else (None, ref)


def source_groups(model, task_id: str, *, q='', page=1, page_size=20, criterion_ref='', attribute_ref='',
                  rule_ref='', candidate_ref='', source_id='', snapshot=None, kind='literature') -> dict[str, Any]:
    if kind not in KINDS:
        raise ValueError('Choose literature, database, model, other or all sources')
    page, page_size = max(1, int(page)), max(1, min(50, int(page_size)))
    with model._cache() as db, model._source() as source:
        meta = model._ready(db)
        model._task(db, task_id)
        selected = model._snapshot_row(db, task_id, snapshot)
        mode = 'selected_snapshot' if snapshot else 'latest_snapshot' if selected else 'task_history'
        scope = {'mode': mode, 'snapshot_id': selected['snapshot_id'] if selected else None,
                 'snapshot_published_at': selected['published_at'] if selected else None}
        if candidate_ref:
            scope['candidate_ref'] = candidate_ref
            candidate = db.execute('SELECT label FROM candidate_rows WHERE snapshot_id=? AND candidate_ref=?',
                                   (scope['snapshot_id'], candidate_ref)).fetchone()
            scope['candidate_label'] = candidate[0] if candidate else None
        entries, evaluation_ref = _evaluation_entries(model, db, source, task_id, selected)
        criterion_scope = 'saved_evaluation' if selected and entries is not None else 'prepared_evaluation' if entries is not None else 'task_history'
        cache = getattr(model, '_evidence_group_pages', None)
        if cache is None:
            cache = model._evidence_group_pages = {}
        key = (task_id, meta.get('cursor'), scope['snapshot_id'], q, criterion_ref, attribute_ref, rule_ref, candidate_ref, source_id, kind, page, page_size)
        if key in cache:
            return copy.deepcopy(cache[key])
        where, values = _where(model, db, task_id, selected, q=q, criterion_ref=criterion_ref,
            attribute_ref=attribute_ref, rule_ref=rule_ref, candidate_ref=candidate_ref, source_id=source_id, kind=kind)
        relation = 'claims c LEFT JOIN evidence_sources s ON s.task_id=c.task_id AND s.source_id=c.source_id'
        grouping_relation, grouping_where, grouping_values = relation, where, values
        if criterion_ref or attribute_ref or rule_ref or candidate_ref:
            # A small explicit context must seek its claim IDs. GROUP BY would
            # otherwise tempt SQLite to scan every task row in source order.
            grouping_relation = 'claims c INDEXED BY claims_lookup LEFT JOIN evidence_sources s ON s.task_id=c.task_id AND s.source_id=c.source_id'
        elif kind in _STATUSES:
            # Filter compact source metadata before touching the much larger claim
            # rows. Unknown statuses still pass through the recorded-kind fallback.
            grouping_relation = 'evidence_sources s INDEXED BY evidence_sources_kind CROSS JOIN claims c INDEXED BY claims_source ON s.task_id=c.task_id AND s.source_id=c.source_id'
            known = tuple(value for statuses in _STATUSES.values() for value in statuses)
            grouping_where = ('s.task_id=? AND (json_extract(s.body,\'$.source_status\') IN (' +
                ','.join('?' for _ in _STATUSES[kind]) + ') OR coalesce(json_extract(s.body,\'$.source_status\'),\'\') NOT IN (' +
                ','.join('?' for _ in known) + ')) AND ' + where)
            grouping_values = [task_id, *_STATUSES[kind], *known, *values]
        grouped = f'SELECT c.source_id,count(*) AS claim_count,max(c.source_row) AS last_row FROM {grouping_relation} WHERE {grouping_where} GROUP BY c.source_id'
        aggregates = getattr(model, '_evidence_group_counts', None)
        if aggregates is None:
            aggregates = model._evidence_group_counts = {}
        aggregate_key = key[:-2]
        if aggregate_key not in aggregates:
            if len(aggregates) >= 4:
                aggregates.pop(next(iter(aggregates)))
            aggregates[aggregate_key] = [dict(row) for row in db.execute(grouped + ' ORDER BY last_row DESC,c.source_id', grouping_values)]
        all_groups = aggregates[aggregate_key]
        total = len(all_groups)
        rows = all_groups[(page - 1) * page_size:page * page_size]
        items = []
        for row in rows:
            sid = row['source_id']
            metadata_row = db.execute('SELECT body FROM evidence_sources WHERE task_id=? AND source_id=?', (task_id, sid)).fetchone()
            metadata = json.loads(metadata_row[0]) if metadata_row else {}
            samples = [json.loads(r[0]) for r in db.execute(f'SELECT c.body FROM claims c INDEXED BY claims_source LEFT JOIN evidence_sources s ON s.task_id=c.task_id AND s.source_id=c.source_id WHERE {where} AND c.source_id=? ORDER BY c.source_row DESC LIMIT 20', (*values, sid))]
            first = samples[0] if samples else {}
            reader = EvidenceRead(model)
            view = reader.source_view(db, task_id, first, source=source) if first else {}
            contexts = [sample.get('context') or {} for sample in samples]
            subjects = _unique([str(x) for c in contexts for x in c.get('entities') or []
                                if isinstance(x, str) and not x.startswith(('cand_', 'claim_', 'attr_', 'rule_', 'src_'))])
            link_scope, link_values = EvidenceRead._scope(selected)
            link_query = (f'FROM claims c INDEXED BY claims_source CROSS JOIN evidence_links u INDEXED BY evidence_claim_usage ON c.task_id=u.task_id AND c.claim_id=u.claim_id '
                f'LEFT JOIN evidence_sources s ON s.task_id=c.task_id AND s.source_id=c.source_id WHERE {where} AND c.source_id=?' + link_scope)
            link_params = [*values, sid, *link_values]
            if candidate_ref:
                # Match EvidenceRead.links' explicit candidate scope and let the
                # covering index seek that candidate plus unbound criterion use.
                link_query += " AND u.candidate_ref IN ('',?)"
                link_params.append(candidate_ref)
            if entries is not None:
                rule_refs = json.dumps([entry['rule_ref'] for entry in entries if entry.get('rule_ref')])
                attribute_refs = json.dumps([entry['attribute_ref'] for entry in entries if entry.get('attribute_ref')])
                link_query += " AND (u.rule_ref IN (SELECT value FROM json_each(?)) OR (coalesce(u.rule_ref,'')='' AND u.attribute_ref IN (SELECT value FROM json_each(?))))"
                link_params.extend([rule_refs, attribute_refs])
            identity = "coalesce(nullif(u.rule_ref,''),nullif(u.attribute_ref,''),u.criterion_ref)"
            criteria = []
            count = 0
            for link in db.execute('SELECT ' + identity + ' AS detail_ref,count(*) OVER () AS total_count,max(u.name) AS name,u.attribute_ref,u.rule_ref,'
                                  'group_concat(DISTINCT u.relationship) AS relationships ' + link_query +
                                  ' GROUP BY detail_ref ORDER BY name,detail_ref LIMIT 50', link_params):
                count = link['total_count']
                criteria.append({'detail_ref': link['detail_ref'], 'name': link['name'] or link['detail_ref'],
                    'attribute_ref': link['attribute_ref'], 'rule_ref': link['rule_ref'],
                    'relationships': (link['relationships'] or '').split(',')})
            source_type = db.execute(f'SELECT {source_kind_sql()} FROM {relation} WHERE c.task_id=? AND c.source_id=? LIMIT 1', (task_id, sid)).fetchone()
            items.append({'source_id': sid, 'title': view.get('title') or metadata.get('title'),
                'url': view.get('url') or metadata.get('url'), 'kind': source_type[0] if source_type else 'other',
                'source_status': metadata.get('source_status'), 'claim_count': row['claim_count'],
                'populations': _unique(c.get('population') for c in contexts), 'subjects': subjects,
                'assays': _unique(c.get('assay') for c in contexts), 'conditions': _unique(c.get('conditions') for c in contexts),
                'context_basis': 'recorded_claim_context', 'context_sampled': row['claim_count'] > len(samples),
                'context_sample_size': len(samples), 'criteria': criteria, 'criteria_count': count,
                'criteria_scope': criterion_scope, 'evaluation_rule_set_ref': evaluation_ref, 'scope': scope})
        result = {'items': items, 'total': total, 'page': page, 'page_size': page_size,
                  'has_more': page * page_size < total, 'kind': kind, 'scope': scope,
                  'snapshot_id': scope['snapshot_id'], 'as_of': meta.get('source_as_of')}
        if len(cache) >= 16:
            cache.pop(next(iter(cache)))
        cache[key] = copy.deepcopy(result)
        return result
