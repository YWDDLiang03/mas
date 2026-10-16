"""Build a separate, dependency-closed research store. Never alter the input.

Keep primary task history and complete CQA/final-run streams. Other events are
retained only as exact source/context proofs in the original events table. All
retained IDs, rowids, sequence numbers, bodies and hashes are copied unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time

ART = re.compile(r'art_[0-9a-f]+\Z')
EVT = re.compile(r'evt_[A-Za-z0-9]+\Z')
TASK_REF = re.compile(r'(task_[A-Za-z0-9]+)@v(\d+)\Z')
PUBLIC = "coalesce(json_extract(body,'$.visibility'),'default') NOT IN ('evaluator_only','private','recovery')"
PRIMARY = ['task_01M51AQ0JK0MYN47806ZD5XS1B', 'task_01M52CBE5GYPK9F0MCZYBMPH84']
FINALS = ['lb_' + task + '_2' for task in PRIMARY]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source_path = (args.source / 'store.db' if args.source.is_dir() else args.source).resolve()
    output = args.output.resolve()
    if output.exists() or output == source_path.parent or output.is_relative_to(source_path.parent):
        raise SystemExit('Output must be a new directory outside the original store')
    if source_path.with_name(source_path.name + '-wal').exists() and source_path.with_name(source_path.name + '-wal').stat().st_size:
        raise SystemExit('Checkpoint/stop the source writer first; source WAL must be empty')
    output.mkdir(parents=True)
    started = time.perf_counter()
    src = sqlite3.connect(source_path.as_uri() + '?mode=ro', uri=True, cached_statements=0)
    src.row_factory = sqlite3.Row
    src.execute('PRAGMA query_only=ON')
    src.execute('BEGIN')
    before = source_path.stat()
    dst = sqlite3.connect(output / 'store.db', isolation_level=None, uri=True)
    dst.execute('PRAGMA journal_mode=OFF')
    dst.execute('PRAGMA synchronous=OFF')
    dst.execute('PRAGMA temp_store=MEMORY')
    dst.execute('PRAGMA cache_size=-65536')
    dst.execute('ATTACH DATABASE ? AS original', (source_path.as_uri() + '?mode=ro',))
    schema = list(src.execute("SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"))
    for row in schema:
        if row['type'] == 'table':
            dst.execute(row['sql'])
    dst.execute('CREATE TEMP TABLE keep_events(id INTEGER PRIMARY KEY)')
    dst.execute('CREATE TEMP TABLE keep_artifacts(id TEXT PRIMARY KEY)')
    events, artifacts, scanned_artifacts = set(), set(), set()
    stream_prefixes, queued_streams = {}, deque()
    event_queue, artifact_queue = deque(), deque()
    contexts, source_ids, claim_ids, done_sources, done_claims = set(), set(), set(), set(), set()
    support_snapshots, missing, blocked = {}, set(), set()
    opaque_artifacts = {}
    proof_runs, event_refs, event_locations = set(), set(), set()
    claim_admissions = None
    primary_runs, all_runs = [], {}
    last_log = started

    def log(message):
        nonlocal last_log
        print(json.dumps({'seconds': round(time.perf_counter()-started, 2), 'message': message,
                          'events': len(events), 'artifacts': len(artifacts)}, ensure_ascii=False), flush=True)
        last_log = time.perf_counter()

    def stream(stream_id, pin=None, reason='dependency_prefix'):
        if not isinstance(stream_id, str) or not stream_id.startswith(('task_', 'run_')):
            return
        if pin is None:
            pin = src.execute('SELECT coalesce(max(seq),0) FROM events WHERE stream_id=?', (stream_id,)).fetchone()[0]
        prior = stream_prefixes.get(stream_id, {}).get('pinned_seq', 0)
        if pin > prior:
            stream_prefixes[stream_id] = {'pinned_seq': pin, 'reason': reason}
            queued_streams.append((stream_id, prior, pin))

    def event(row):
        if row and row['rowid'] not in events:
            events.add(row['rowid'])
            event_queue.append(row['rowid'])

    def event_id(identity):
        if identity in event_refs:
            return
        event_refs.add(identity)
        row = src.execute('SELECT rowid,* FROM events WHERE event_id=? AND ' + PUBLIC, (identity,)).fetchone()
        if row:
            event(row)
        else:
            missing.add('event:' + identity)

    def event_at(stream_id, seq):
        if type(seq) is not int or seq < 1:
            return
        if seq <= stream_prefixes.get(stream_id, {}).get('pinned_seq', 0):
            return
        if (stream_id, seq) in event_locations:
            return
        event_locations.add((stream_id, seq))
        row = src.execute('SELECT rowid,* FROM events WHERE stream_id=? AND seq=? AND ' + PUBLIC, (stream_id, seq)).fetchone()
        if row:
            event(row)

    def artifact(identity):
        if isinstance(identity, str) and ART.fullmatch(identity) and identity not in artifacts:
            artifacts.add(identity)
            artifact_queue.append(identity)

    def context(task_id, version=None):
        marker = (task_id, version)
        if marker in contexts or not isinstance(task_id, str) or not task_id.startswith('task_'):
            return
        contexts.add(marker)
        sql = "SELECT seq FROM events WHERE stream_id=? AND event_type='task.version_recorded' AND " + PUBLIC
        params = [task_id]
        if version is not None:
            sql += " AND json_extract(body,'$.payload.version')=?"
            params.append(version)
        row = src.execute(sql + ' ORDER BY seq DESC LIMIT 1', params).fetchone()
        if row:
            stream(task_id, row[0], 'support_context_prefix')
        # Keep a support collection's original snapshot blob/publication and its
        # binding for cutoff metadata; do not expand its candidate assessment IDs.
        rows = src.execute("SELECT rowid,* FROM events WHERE event_type='leaderboard.snapshot_published' "
            "AND coalesce(json_extract(body,'$.payload.task_id'),json_extract(body,'$.ids.task_id'))=? "
            "AND " + PUBLIC + ' ORDER BY recorded_at DESC LIMIT 1', (task_id,)).fetchone()
        if rows and task_id not in PRIMARY:
            value = json.loads(rows['body'])
            support_snapshots[value['payload']['snapshot_id']] = {'task_id': task_id, 'run_id': rows['stream_id'],
                'artifact_id': value['payload']['artifact_id'], 'publication_rowid': rows['rowid']}
            event(rows)

    def run_proof(run_id):
        if not isinstance(run_id, str) or not run_id.startswith('run_') or run_id in proof_runs:
            return
        proof_runs.add(run_id)
        for row in src.execute("SELECT rowid,* FROM events WHERE stream_id=? AND event_type='run.created' AND " + PUBLIC, (run_id,)):
            event(row)
        row = src.execute("SELECT rowid,* FROM events WHERE stream_id=? AND event_type IN "
            "('run.completed','run.failed','run.cancelled','run.unresolved') AND " + PUBLIC + ' ORDER BY seq DESC LIMIT 1', (run_id,)).fetchone()
        event(row)

    def inspect(value, key=''):
        if isinstance(value, dict):
            # An explicitly pinned evidence/replay prefix is a hard dependency.
            if value.get('run_id') and type(value.get('pinned_seq')) is int:
                stream(value['run_id'], value['pinned_seq'], 'pinned_evidence_prefix')
            if value.get('source_task_id') and type(value.get('source_task_seq')) is int:
                stream(value['source_task_id'], value['source_task_seq'], 'pinned_source_task_prefix')
            if value.get('source_run_id') and type(value.get('source_seq')) is int:
                event_at(value['source_run_id'], value['source_seq'])
                run_proof(value['source_run_id'])
            for k, item in value.items():
                if ART.fullmatch(str(k)):
                    artifact(k)
                inspect(item, k)
        elif isinstance(value, list):
            for item in value:
                inspect(item, key)
        elif isinstance(value, str):
            if ART.fullmatch(value):
                artifact(value)
            elif EVT.fullmatch(value) and key != 'event_id':
                event_id(value)
            elif TASK_REF.fullmatch(value):
                found = TASK_REF.fullmatch(value)
                context(found[1], int(found[2]))
            elif value.startswith('task_') and key in ('source_task_id', 'derived_from_task_id', 'evidence_collection_source_task_id'):
                context(value)
            elif value.startswith('claim_') and key not in ('claim_id', 'omitted', 'omissions'):
                claim_ids.add(value)
            elif value.startswith('src_') and key in ('source_ref', 'source_id'):
                source_ids.add(value)

    # Primary streams keep all original sequence numbers, including failed CQA
    # attempts and paid usage. Only non-final screening runs must be reached by a
    # genuine saved source pin or reuse dependency.
    for task_id in PRIMARY:
        stream(task_id, reason='primary_task_complete_history')
    for row in src.execute("SELECT rowid,* FROM events WHERE event_type='run.created' AND " + PUBLIC):
        value = json.loads(row['body'])
        task_id = value.get('payload', {}).get('task_id') or value.get('ids', {}).get('task_id')
        all_runs[row['stream_id']] = row
        if task_id not in PRIMARY:
            continue
        binding_id = value['payload'].get('binding_artifact_id')
        binding = src.execute("SELECT body FROM artifacts WHERE artifact_id=? AND kind='run_binding'", (binding_id,)).fetchone()
        body = json.loads(binding[0])['payload'] if binding else {}
        if body.get('run_purpose') == 'criteria_derivation' or body.get('operation') == 'derive_existing_evidence':
            primary_runs.append(row['stream_id'])
            stream(row['stream_id'], reason='primary_complete_criteria_evolution')
    for identity in FINALS:
        row = src.execute("SELECT rowid,* FROM events WHERE event_type='leaderboard.snapshot_published' "
                          "AND json_extract(body,'$.payload.snapshot_id')=? AND " + PUBLIC, (identity,)).fetchone()
        if not row:
            raise RuntimeError('Missing requested final snapshot: ' + identity)
        primary_runs.append(row['stream_id'])
        stream(row['stream_id'], reason='primary_final_run')
    # Run-specific constants already belong to the retained primary prefixes.
    # A constant in an obsolete run must not retain that entire evaluation.
    for row in src.execute("SELECT rowid FROM events WHERE event_type='constant.registered' AND stream_id='eval'"):
        event(row)
    log('Seeded primary histories and final runs')

    while queued_streams or event_queue or artifact_queue or source_ids-done_sources or claim_ids-done_claims:
        while queued_streams:
            name, start, end = queued_streams.popleft()
            for row in src.execute('SELECT rowid FROM events WHERE stream_id=? AND seq>? AND seq<=? ORDER BY seq', (name, start, end)):
                event(row)
        while event_queue:
            row = src.execute('SELECT rowid,* FROM events WHERE rowid=?', (event_queue.popleft(),)).fetchone()
            value = json.loads(row['body'])
            if value.get('visibility', 'default') in ('evaluator_only', 'private', 'recovery'):
                blocked.add('event:' + row['event_id'])
                continue
            for name in ('parent_seq', 'cause_seq'):
                if type(value.get(name)) is int:
                    event_at(row['stream_id'], value[name])
            if row['stream_id'].startswith('run_') and row['stream_id'] not in stream_prefixes:
                run_proof(row['stream_id'])
            if row['event_type'] == 'run.created':
                binding_id = (value.get('payload') or {}).get('binding_artifact_id')
                # Metadata only: resolve the run's public context so event ownership
                # remains readable after the obsolete studies are removed.
                binding = src.execute("SELECT body FROM artifacts WHERE artifact_id=? AND kind='run_binding' AND " + PUBLIC, (binding_id,)).fetchone()
                if binding:
                    owner = json.loads(binding[0])['payload'].get('task_context_id@v')
                    if owner and TASK_REF.fullmatch(owner):
                        match = TASK_REF.fullmatch(owner)
                        context(match[1], int(match[2]))
            inspect(value)
            if time.perf_counter()-last_log > 15:
                log('Resolving retained journal references')
        while artifact_queue:
            batch = []
            while artifact_queue and len(batch) < 500:
                identity = artifact_queue.popleft()
                if identity not in scanned_artifacts:
                    batch.append(identity)
                    scanned_artifacts.add(identity)
            if not batch:
                continue
            marks = ','.join('?' for _ in batch)
            meta = {row['artifact_id']: row for row in src.execute('SELECT artifact_id,kind FROM artifacts WHERE artifact_id IN (' + marks + ')', batch)}
            allowed = []
            for identity in batch:
                if identity not in meta:
                    missing.add('artifact:' + identity)
                elif meta[identity]['kind'].startswith(('case_', 'recovery_')):
                    # Explicitly referenced legacy proof: preserve raw bytes/hash
                    # opaquely. Never decode a sealed/case payload or publish it.
                    opaque_artifacts[identity] = meta[identity]['kind']
                else:
                    allowed.append(identity)
            if not allowed:
                continue
            marks = ','.join('?' for _ in allowed)
            fetched = set()
            for row in src.execute('SELECT artifact_id,kind,body FROM artifacts WHERE artifact_id IN (' + marks + ') AND ' + PUBLIC +
                    " AND coalesce(json_extract(body,'$.payload.visibility'),'default') NOT IN ('evaluator_only','private','recovery') "
                    "AND coalesce(json_extract(body,'$.payload.evaluator_only'),0)!=1 ORDER BY rowid", allowed):
                fetched.add(row['artifact_id'])
                body = json.loads(row['body'])
                # Historical snapshot blobs are opaque lineage/context dependencies;
                # their candidate IDs do not seed another assessment population.
                if row['kind'] != 'leaderboard_snapshot':
                    inspect(body.get('payload') or {})
                else:
                    parent = (body.get('payload') or {}).get('parent_snapshot_id')
                    if parent:
                        old = src.execute("SELECT json_extract(body,'$.payload.artifact_id') FROM events WHERE event_type='leaderboard.snapshot_published' AND json_extract(body,'$.payload.snapshot_id')=? AND " + PUBLIC + ' LIMIT 1', (parent,)).fetchone()
                        if old:
                            artifact(old[0])
            for identity in set(allowed)-fetched:
                opaque_artifacts[identity] = meta[identity]['kind']
            if time.perf_counter()-last_log > 15:
                log('Resolving artifact closure')
        wanted = claim_ids-done_claims
        if wanted:
            done_claims.update(wanted)
            if claim_admissions is None:
                claim_admissions = {}
                for pointer in src.execute("SELECT rowid,json_extract(body,'$.payload.claim_id') FROM events "
                        "WHERE event_type IN ('evidence.admitted','evidence.quarantined') AND " + PUBLIC + ' ORDER BY rowid'):
                    claim_admissions.setdefault(pointer[1], pointer[0])
            # Prefer an admission already retained in the selected histories. A
            # single earliest exact admission supplies provenance for other IDs.
            for identity in wanted:
                found = claim_admissions.get(identity)
                row = src.execute('SELECT rowid FROM events WHERE rowid=?', (found,)).fetchone() if found else None
                if row:
                    event(row)
                else:
                    missing.add('claim:' + identity)
        wanted_sources = source_ids-done_sources
        if wanted_sources:
            done_sources.update(wanted_sources)
            for row in src.execute("SELECT artifact_id FROM artifacts WHERE kind='source' AND " + PUBLIC +
                " AND json_extract(body,'$.payload.source_id') IN (SELECT value FROM json_each(?))", (json.dumps(sorted(wanted_sources)),)):
                artifact(row[0])
    log('Closure resolved')
    plan = sqlite3.connect(output/'closure.sqlite')
    plan.executescript('CREATE TABLE event_ids(id INTEGER PRIMARY KEY); CREATE TABLE artifact_ids(id TEXT PRIMARY KEY); CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);')
    plan.executemany('INSERT INTO event_ids VALUES(?)', ((identity,) for identity in sorted(events)))
    plan.executemany('INSERT INTO artifact_ids VALUES(?)', ((identity,) for identity in artifacts))
    for key,value in {'retained_stream_prefixes':stream_prefixes,'support_snapshots':support_snapshots,
                      'opaque_artifacts':opaque_artifacts,'preexisting_unresolved_references':sorted(missing)}.items():
        plan.execute('INSERT INTO metadata VALUES(?,?)',(key,json.dumps(value)))
    plan.commit();plan.close()
    log('Closure ID sets checkpointed to closure.sqlite')
    # This is a candidate, never an in-place edit. Preserve evidence of every
    # unresolved/sensitive edge and refuse to silently publish an incomplete copy.
    if blocked:
        raise RuntimeError('Retained closure references nonpublic/case artifacts: ' + repr(sorted(blocked)[:12]))
    # Some free-text citations are not admitted claim IDs; keep this explicit in
    # the receipt, while hard artifact/event references must all resolve.
    # Original dangling citations remain explicit. They are not newly lost rows:
    # every referenced object actually present in the source is retained.
    dst.executemany('INSERT INTO keep_events VALUES(?)', ((identity,) for identity in sorted(events)))
    dst.executemany('INSERT INTO keep_artifacts VALUES(?)', ((identity,) for identity in artifacts))
    log('Copying exact original rows')
    dst.execute('BEGIN')
    dst.execute('INSERT INTO main.events(rowid,stream_id,seq,event_id,event_type,recorded_at,body,body_hash) '
        'SELECT e.rowid,e.stream_id,e.seq,e.event_id,e.event_type,e.recorded_at,e.body,e.body_hash '
        'FROM original.events e JOIN keep_events k ON e.rowid=k.id ORDER BY e.rowid')
    dst.execute('COMMIT')
    log('Journal copied; copying artifacts')
    dst.execute('BEGIN')
    dst.execute('INSERT INTO main.artifacts(rowid,artifact_id,kind,sha256,body,created_at) '
        'SELECT a.rowid,a.artifact_id,a.kind,a.sha256,a.body,a.created_at '
        'FROM original.artifacts a JOIN keep_artifacts k ON a.artifact_id=k.id ORDER BY a.rowid')
    dst.execute('COMMIT')
    for row in schema:
        if row['type'] in ('index', 'trigger'):
            dst.execute(row['sql'])
    log('Indexes built; checking exact identities and integrity')
    event_count = dst.execute('SELECT count(*) FROM main.events').fetchone()[0]
    artifact_count = dst.execute('SELECT count(*) FROM main.artifacts').fetchone()[0]
    bad_events = dst.execute('SELECT count(*) FROM main.events e JOIN original.events s ON s.rowid=e.rowid '
        'WHERE e.stream_id!=s.stream_id OR e.seq!=s.seq OR e.event_id!=s.event_id OR e.body!=s.body OR e.body_hash!=s.body_hash').fetchone()[0]
    bad_artifacts = dst.execute('SELECT count(*) FROM main.artifacts a JOIN original.artifacts s ON s.rowid=a.rowid '
        'WHERE a.artifact_id!=s.artifact_id OR a.sha256!=s.sha256 OR a.body!=s.body OR a.kind!=s.kind').fetchone()[0]
    integrity = dst.execute('PRAGMA main.integrity_check').fetchone()[0]
    prefix_errors = []
    for name, proof in stream_prefixes.items():
        minimum, maximum, count = dst.execute('SELECT min(seq),max(seq),count(*) FROM events WHERE stream_id=? AND seq<=?', (name, proof['pinned_seq'])).fetchone()
        if minimum != 1 or maximum != proof['pinned_seq'] or count != proof['pinned_seq']:
            prefix_errors.append(name)
    file_same = (before.st_size,before.st_mtime_ns)==(source_path.stat().st_size,source_path.stat().st_mtime_ns)
    manifest = {'created_at': datetime.now(timezone.utc).isoformat(), 'source_path': str(source_path),
        'candidate_path': str(output/'store.db'), 'primary_task_ids': PRIMARY, 'final_snapshot_ids': FINALS,
        'primary_run_ids': sorted(set(primary_runs)), 'retained_stream_prefixes': stream_prefixes,
        'support_snapshots': support_snapshots, 'event_count': event_count, 'artifact_count': artifact_count,
        'source_bytes': before.st_size, 'candidate_bytes': (output/'store.db').stat().st_size,
        'unresolved_claim_citations': sorted(item for item in missing if item.startswith('claim:')),
        'preexisting_unresolved_references':sorted(missing),'opaque_artifacts':opaque_artifacts,
        'verification': {'exact_event_rowid_body_hash': bad_events==0, 'exact_artifact_rowid_body_hash': bad_artifacts==0,
            'integrity_check': integrity, 'contiguous_required_prefixes': not prefix_errors,
            'source_size_and_mtime_unchanged': file_same, 'source_connection_total_changes': src.total_changes},
        'sparse_dependency_streams': [row[0] for row in dst.execute('SELECT DISTINCT stream_id FROM events') if row[0] not in stream_prefixes],
        'seconds': time.perf_counter()-started, 'source_records_rewritten': False,
        'note': 'Only two primary studies. Other contexts/tool events and opaque old snapshot blobs are technical dependencies, not additional research results.'}
    (output/'retention-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    dst.execute('DETACH DATABASE original')
    dst.execute('PRAGMA journal_mode=DELETE')
    dst.execute('PRAGMA synchronous=FULL')
    dst.close();src.close()
    log('Candidate completed; original store was not replaced or deleted')
    print(json.dumps({key: manifest[key] for key in ('candidate_path','event_count','artifact_count','source_bytes','candidate_bytes','verification','seconds')},indent=2),flush=True)
    if bad_events or bad_artifacts or integrity!='ok' or prefix_errors or not file_same:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
