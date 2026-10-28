"""Portable, explicitly bounded research records and offline engine replay.

The capsule is a selection of immutable records, not a database backup. Event
sequence gaps and excluded document/trace references are declared in its manifest.
An imported result retains its recorded identity; live work gets a new task.
"""
from __future__ import annotations

import base64
from collections import Counter
from contextlib import ExitStack
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from . import assessor, criteria, leaderboard, task
from .canonical import canonical_text, sha256_hex
from .clock import utc_now
from .journal import actor
from .runtime import Core
from .store import _RootLock

FORMAT = "mas-portable-reproduction-v1"
DEFAULT_TASK = "task_01M52CBE5GYPK9F0MCZYBMPH84"
DEFAULT_RUN = "run_01M52Q4VRB00T5Z3QJW08SSV96"
DEFAULT_SNAPSHOT = "lb_task_01M52CBE5GYPK9F0MCZYBMPH84_2"
_ART = re.compile(r"\bart_[0-9a-f]{12}\b")
_SEMANTIC = re.compile(r"\b(?:claim_[A-Za-z0-9_-]+|src_[^\s\"<>]+)")
_FORBIDDEN = {"document", "trace", "case_inheritance_snapshot", "recovery_comparison"}
_PRIVATE = {"private", "evaluator_only", "recovery"}


class _ConcatenatedReader:
    def __init__(self, handles):
        self.handles, self.index = handles, 0

    def read(self, size=-1):
        chunks, remaining = [], size
        while self.index < len(self.handles) and remaining != 0:
            chunk = self.handles[self.index].read(remaining)
            if chunk:
                chunks.append(chunk)
                if remaining > 0:
                    remaining -= len(chunk)
            else:
                self.index += 1
        return b''.join(chunks)


def _public(record):
    payload = record.get("payload") or {}
    return (record.get("visibility", "default") not in _PRIVATE
            and payload.get("visibility", "default") not in _PRIVATE
            and not payload.get("evaluator_only") and not (record.get("ids") or {}).get("case_id"))


def public_metadata_copy(envelope):
    """Replace descriptive labels of excluded private sources in shared tasks.

    Keep source fingerprints, task meaning and the local envelope intact. The
    capsule declares the original and public digests for every projected record.
    """
    if envelope.get('kind') != 'task_context':
        return envelope, []
    sources = (envelope.get('payload') or {}).get('case_source_documents') or []
    if not sources:
        return envelope, []
    result = copy.deepcopy(envelope)
    changed = []
    for index, source in enumerate(result['payload']['case_source_documents']):
        for key, value in (('title', 'Private source document'),
                           ('note', 'Excluded source; content fingerprint retained in the public copy.')):
            if key in source and source[key] != value:
                source[key] = value
                changed.append(f'payload.case_source_documents[{index}].{key}')
    return (result, changed) if changed else (envelope, [])


def _file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_bundle(store_root, output, *, task_id=DEFAULT_TASK, run_id=DEFAULT_RUN,
                 snapshot_id=DEFAULT_SNAPSHOT, workflow_id=None, progress=None):
    """Export selected public records from a read-only source into a new directory.

    The allowlist excludes full texts, model traces, private cases, recovery
    artifacts, operator logs and provider configuration. Excluded private-source
    labels are projected with declared original/public digests. Scientific
    values and source identities retain their historical meaning.
    """
    root, output = Path(store_root).resolve(), Path(output).resolve()
    if output == root or output.is_relative_to(root) or (output.exists() and any(output.iterdir())):
        raise ValueError("Use a new empty output directory outside the source store.")
    output.mkdir(parents=True, exist_ok=True)
    report = progress or (lambda message: None)
    with Core.open(root, read_only=True) as core:
        db = core.store.db
        context = task.get(core, task_id)
        created = next(e for e in core.journal.replay(run_id, 1, 1) if e.event_type == "run.created")
        binding = core.artifacts.payload(created.payload["binding_artifact_id"])
        tool_sources = binding.get("tool_replay") or {}
        selected, pending, excluded, event_keys = set(), set(), {}, set()
        public_metadata_changes = []
        event_counts, artifact_counts, file_counts = Counter(), Counter(), Counter()
        closure_index = {}
        report("Indexing source identities")
        for aid, kind, identity in db.execute("SELECT artifact_id,kind,CASE kind "
                "WHEN 'claim' THEN json_extract(body,'$.payload.claim_id') "
                "WHEN 'source' THEN json_extract(body,'$.payload.source_id') END "
                "FROM artifacts WHERE kind IN ('claim','source') ORDER BY rowid"):
            if identity:
                closure_index[identity] = aid

        def refs(record):
            text = canonical_text(record)
            pending.update(_ART.findall(text))
            # Only semantic identifiers of included claims/assessments need content.
            if record.get("kind") in {"assessment", "claim", "reason", "evidence_snapshot", "verified_supplement"}:
                pending.update(closure_index[r] for r in _SEMANTIC.findall(text) if r in closure_index)

        capsule = output / "oral-multitarget-latest-v1.jsonl.gz"
        with capsule.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            def write(record):
                compressed.write((canonical_text(record) + "\n").encode("utf-8"))

            def add_event(raw_event):
                e = json.loads(raw_event) if isinstance(raw_event, str) else raw_event
                key = (e["stream_id"], e["seq"])
                if key in event_keys or not _public(e):
                    return
                event_keys.add(key)
                refs(e)
                source_rowid, digest = db.execute('SELECT rowid,body_hash FROM events WHERE event_id=?', (e['event_id'],)).fetchone()
                if digest != sha256_hex(e):
                    raise ValueError(f"Source event hash differs: {e['event_id']}")
                write({"record_type": "event", "source_rowid": source_rowid, "body": e, "sha256": digest})
                event_counts[e["event_type"]] += 1

            report("Selecting task and criterion history")
            # Preserve the latest task's full public science history; traces are
            # explicitly excluded below even where a historical event names them.
            for body, in db.execute("SELECT body FROM events WHERE stream_id=? ORDER BY seq", (task_id,)):
                add_event(body)
            task_runs = []
            for body, in db.execute("SELECT body FROM events WHERE event_type='run.created' "
                    "AND json_extract(body,'$.payload.task_id')=? ORDER BY recorded_at", (task_id,)):
                e = json.loads(body)
                b = core.artifacts.payload(e["payload"]["binding_artifact_id"])
                if b.get("run_purpose") == "criteria_derivation":
                    task_runs.append(e["stream_id"])
            for stream in task_runs:
                for body, in db.execute("SELECT body FROM events WHERE stream_id=? ORDER BY seq", (stream,)):
                    add_event(body)

            # All frozen boards for this task retain the original failed outcome.
            snapshots = []
            for body, in db.execute("SELECT body FROM events WHERE event_type='leaderboard.snapshot_published' "
                    "AND coalesce(json_extract(body,'$.payload.task_id'),json_extract(body,'$.ids.task_id'))=? "
                    "ORDER BY recorded_at", (task_id,)):
                e = json.loads(body)
                s = core.artifacts.payload(e["payload"]["artifact_id"])
                snapshots.append(s)
                add_event(e)
            history_snapshots = []
            published_ids = {s['snapshot_id'] for s in snapshots}
            for aid, body in db.execute("SELECT artifact_id,body FROM artifacts WHERE kind='leaderboard_snapshot'"):
                board = json.loads(body)['payload']
                if board.get('task_id') == task_id and board['snapshot_id'] not in published_ids:
                    pending.add(aid)
                    history = {'artifact_id': aid, 'snapshot_id': board['snapshot_id'], 'original_run_id': board['run_id'],
                               'original_publication_event_available': False,
                               'basis': 'retained immutable snapshot artifact; original run journal was cleaned previously'}
                    write({'record_type': 'history_snapshot', 'body': history})
                    history_snapshots.append(history)
            if snapshot_id not in {s["snapshot_id"] for s in snapshots}:
                raise ValueError("The requested snapshot is not published by this task.")
            wanted_cells = {ref for s in snapshots for row in s["candidate_entries"] for ref in row["per_criterion_refs"]}
            wanted_claims = {row['claim_id'] for row in core.artifacts.payload(context['evidence_fact_manifest_ref'])['claims']}
            board_runs = {s["run_id"] for s in snapshots}
            report("Selecting frozen identities, assessments and claims")
            for stream in sorted(board_runs):
                for body, in db.execute("SELECT body FROM events WHERE stream_id=? AND event_type NOT IN "
                        "('tool.requested','tool.returned','tool.errored','checkpoint.written','candidate.assessed','evidence.admitted') ORDER BY seq", (stream,)):
                    add_event(body)
                for body, in db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='candidate.assessed' ORDER BY seq", (stream,)):
                    e = json.loads(body)
                    aid = e["payload"]["artifact_id"]
                    cell = core.artifacts.payload(aid)
                    if cell["assessment_id"] in wanted_cells:
                        wanted_claims.update(cell.get('value_source_claim_refs') or [])
                        add_event(e)
                for body, in db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='evidence.admitted' ORDER BY seq", (stream,)):
                    e = json.loads(body)
                    claim = core.artifacts.payload(e['payload']['artifact_id'])
                    if claim['claim_id'] in wanted_claims:
                        add_event(e)

            # Pin the source contexts but do not import their CQA decisions.
            source_tasks = {context.get("evidence_collection_source_task_id")}
            fact_manifest = core.artifacts.payload(context["evidence_fact_manifest_ref"])
            source_tasks.add(fact_manifest.get("source_task_id"))
            for stream in sorted(source_tasks - {None, task_id}):
                for body, in db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='task.version_recorded' ORDER BY seq", (stream,)):
                    add_event(body)

            report("Selecting pinned historical tool facts")
            replay_keys = set()
            replay_events = 0
            for stream in tool_sources.get("source_run_ids") or []:
                pin = tool_sources.get("source_pins", {}).get(stream, core.journal.last_seq(stream))
                for body, in db.execute("SELECT body FROM events WHERE stream_id=? AND seq<=? "
                        "AND event_type IN ('run.created','run.started','run.resumed','run.paused','run.cancelled',"
                        "'run.completed','run.unresolved','run.failed','tool.returned') ORDER BY seq", (stream, pin)):
                    e = json.loads(body)
                    if e["event_type"] == "tool.returned":
                        p = e["payload"]
                        if not _public(e) or p.get("outcome") not in ("ok", "empty"):
                            continue
                        links = [v["id"] for v in e.get("artifact_links") or [] if v.get("kind") == "tool_result"]
                        if len(links) != 1:
                            continue
                        result = core.artifacts.payload(links[0])
                        from .broker import _cache_key
                        inv, prov = result.get("invocation") or {}, result.get("provenance") or {}
                        key = _cache_key(inv.get("tool_id"), inv.get("contract_version"), prov.get("implementation_version"),
                                         inv.get("question_kind"), inv.get("normalized_input"))
                        if key in replay_keys:
                            continue
                        replay_keys.add(key)
                        replay_events += 1
                    add_event(e)
                # Candidate literature is a small separate subset of historical
                # facts. Preserve its original measurement definition for the
                # existing exact-quantity rebinding hook, never an old verdict.
                source_owner = core.artifacts.payload(next(json.loads(raw)['payload']['binding_artifact_id']
                    for raw, in db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='run.created'", (stream,))))['task_context_id@v'].split('@v')[0]
                for body, in db.execute("SELECT e.body FROM events e JOIN artifacts a "
                        "ON a.artifact_id=json_extract(e.body,'$.payload.artifact_id') "
                        "WHERE e.stream_id=? AND e.seq<=? AND e.event_type='evidence.admitted' "
                        "AND json_extract(a.body,'$.payload.evidence_kind') IN "
                        "('peer_reviewed','reference_text','user_supplied_document') ORDER BY e.seq", (stream, pin)):
                    e = json.loads(body)
                    claim = core.artifacts.payload(e['payload']['artifact_id'])
                    ref = claim.get('attribute_ref')
                    if not claim.get('candidate_ref') or not ref or '@v' not in ref:
                        continue
                    base, version = ref.rsplit('@v', 1)
                    for attribute_event, in db.execute("SELECT body FROM events WHERE stream_id=? "
                            "AND event_type='criterion.version_proposed' AND json_extract(body,'$.payload.kind')='attribute' "
                            "AND json_extract(body,'$.payload.id')=? AND json_extract(body,'$.payload.version')=? ORDER BY seq", (source_owner, base, int(version))):
                        add_event(attribute_event)
                    add_event(e)
            if replay_events != tool_sources.get("cache_entries", replay_events):
                raise ValueError(f"Pinned tool facts differ: {replay_events} versus {tool_sources.get('cache_entries')}.")

            # Explicit claim manifest rows are sufficient for a fresh generation;
            # original derivation source streams are provenance, not dependencies.
            pending.add(context["evidence_fact_manifest_ref"])
            report("Resolving public artifact closure")
            missing = set()
            while pending:
                aid = pending.pop()
                if aid in selected or aid in excluded or aid in missing:
                    continue
                row = db.execute("SELECT kind,sha256,body,created_at FROM artifacts WHERE artifact_id=?", (aid,)).fetchone()
                if not row:
                    missing.add(aid)
                    continue
                kind, digest, body, created = row
                envelope = json.loads(body)
                if kind in _FORBIDDEN or not _public(envelope) or kind.startswith(("case_", "recovery_")):
                    excluded[aid] = {"kind": kind, "sha256": digest,
                                     "reason": "full_text_or_model_trace" if kind in {"document", "trace"} else "private_or_recovery"}
                    continue
                if sha256_hex(envelope) != digest:
                    raise ValueError(f"Source artifact hash differs: {aid}")
                selected.add(aid)
                published, changed_fields = public_metadata_copy(envelope)
                refs(published)
                published_digest = sha256_hex(published) if changed_fields else digest
                record = {"record_type": "artifact", "artifact_id": aid, "body": published,
                          "sha256": published_digest, "created_at": created}
                if changed_fields:
                    record['source_sha256'] = digest
                    public_metadata_changes.append({'artifact_id': aid, 'fields': changed_fields,
                        'source_sha256': digest, 'public_sha256': published_digest})
                write(record)
                artifact_counts[kind] += 1

            report("Packing library and pinned cached prediction rows")
            files = [root.parent / "universe_chembl.json", root.parent / "universe_smiles.json"]
            cache_proofs = []
            for entry in binding.get("evidence_manifest", {}).get("cached_tool_projections", []):
                if entry.get("manifest", {}).get("policy") == "admet_existing_panel_projection_v1":
                    cache_proofs.extend(entry["manifest"]["entries"])
            for proof in cache_proofs:
                files.append(root.parent / "cache/admet/admet-ai-2-panel-1" / proof["cache_relative_path"])
            files = list(dict.fromkeys(files))
            proofs = {p["cache_relative_path"]: p for p in cache_proofs}
            file_manifest = []
            for path in files:
                data = path.read_bytes()
                relative = path.relative_to(root.parent).as_posix()
                proof = proofs.get(path.relative_to(root.parent / "cache/admet/admet-ai-2-panel-1").as_posix()) if relative.startswith("cache/") else None
                if proof and hashlib.sha256(data).hexdigest() != proof["cache_file_sha256"]:
                    raise ValueError(f"Pinned prediction cache changed: {relative}")
                timestamp = proof.get("source_retrieved_at") if proof else None
                write({"record_type": "file", "path": relative, "content_base64": base64.b64encode(data).decode("ascii"),
                       "sha256": hashlib.sha256(data).hexdigest(), "mtime": timestamp})
                file_manifest.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
                file_counts["prediction_panel" if proof else "candidate_library"] += 1

            workflow_path = root.parent / "workbench-workflows.db"
            if workflow_path.is_file():
                with sqlite3.connect(workflow_path.as_uri() + "?mode=ro", uri=True) as workflows:
                    query, args = ("SELECT body FROM workflows WHERE id=?", (workflow_id,)) if workflow_id else (
                        "SELECT body FROM workflows WHERE json_extract(body,'$.task_id')=?", (task_id,))
                    for raw_workflow, in workflows.execute(query, args):
                        workflow = json.loads(raw_workflow)
                        # Only user-visible state and inputs; no resume commands,
                        # provider config or private checkpoints cross the boundary.
                        workflow = {k: v for k, v in workflow.items() if not k.startswith("_") and k not in {"config", "source_manifest"}}
                        workflow.update(command=None, _checkpoints={}, config={})
                        write({"record_type": "workflow", "body": workflow})

        manifest = {"format": FORMAT, "created_at": utc_now(), "task_id": task_id, "run_id": run_id,
                    "snapshot_id": snapshot_id, "rules_ref": binding["rules@v"],
                    "capsule": {"path": capsule.name, "sha256": _file_hash(capsule), "bytes": capsule.stat().st_size},
                    "public_metadata_projection": {"policy": "excluded_source_labels_v1", "records": public_metadata_changes},
                    "counts": {"events": sum(event_counts.values()), "artifacts": len(selected),
                               "event_types": dict(event_counts), "artifact_kinds": dict(artifact_counts),
                               "pinned_claims": len(fact_manifest["claims"]), "pinned_sources": len(fact_manifest["source_records"]),
                               "historical_tool_facts": replay_events, "files": dict(file_counts)},
                    "files": file_manifest, "excluded_artifacts": excluded, "unavailable_historical_refs": sorted(missing),
                    "dependency_policy": {"event_sequences": "selected immutable rows; original seq and source rowid gaps retained",
                        "source_rowids_required": True,
                        "runtime_closure": "frozen cells, identities, rules, claims and metadata; explicit fact manifests; pinned tool results; library; saved prediction panel",
                        "historical_refs": "excluded full texts, model traces and ancestor decision history are audit pointers, not runnable dependencies",
                        "not_included": ["credentials", "provider configuration", "operator logs", "private/evaluator records", "recovery artifacts", "original manuscript PDF", "full article documents", "predictor environment"]},
                    "claim_scope": {"recorded_replay": "recompute qualification, scores and ranking from recorded assessments with the real engine",
                                    "new_live_run": "new task and empty CQA set using pinned factual inputs; requires configured model; trajectory and winner may differ"},
                    "recorded_implementation": binding.get("implementation")}
        manifest['historical_snapshots'] = history_snapshots
        manifest['distribution'] = {'kind': 'optional_release_asset', 'asset_name': capsule.name, 'bundled_in_git': False}
        _write_json(output / "manifest.json", manifest)
    return manifest


def import_bundle(bundle, workspace, *, progress=None):
    """Restore a capsule, resuming only an owned import of these exact bytes.

    The ownership marker precedes all store/files; the final marker publishes a
    completed workspace. Retries reuse matching committed rows and atomic files,
    while unrelated populated directories and changed records remain untouched.
    """
    bundle, workspace = Path(bundle).resolve(), Path(workspace).resolve()
    report = progress or (lambda message: None)
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT:
        raise ValueError("Unsupported reproduction capsule format.")
    parts = manifest['capsule'].get('parts') or [manifest['capsule']]
    digest = hashlib.sha256()
    for part in parts:
        path = (bundle / part['path']).resolve()
        if path.parent != bundle or _file_hash(path) != part['sha256']:
            raise ValueError('The reproduction capsule part hash differs.')
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
    if digest.hexdigest() != manifest['capsule']['sha256']:
        raise ValueError('The concatenated reproduction capsule hash differs.')
    owner_path = workspace / '.mas-import'
    ownership = {'format': 'mas-capsule-import-owner-v1', 'workspace': str(workspace),
                 'capsule_sha256': manifest['capsule']['sha256']}
    if workspace.exists() and any(workspace.iterdir()):
        marker = workspace / "reproduction-import.json"
        if marker.is_file():
            saved = json.loads(marker.read_text(encoding="utf-8"))
            if saved.get("capsule_sha256") == manifest["capsule"]["sha256"]:
                return saved
        owned = False
        if owner_path.is_dir():
            owner_file = owner_path / 'owner.json'
            if owner_file.is_file():
                try:
                    owned = json.loads(owner_file.read_text(encoding='utf-8')) == ownership
                except (OSError, ValueError):
                    pass
            else:
                # An exit during ownership publication precedes every store or
                # input file. Only our marker/lock and unfinished metadata exist.
                owned = ({p.name for p in workspace.iterdir()} <= {owner_path.name, 'store.lock'}
                         and {p.name for p in owner_path.iterdir()} <= {'.mas-import.tmp'})
        if not owned:
            raise ValueError("Import into a new empty workspace; existing work is preserved.")
        report('Resuming the owned capsule import')
    workspace.mkdir(parents=True, exist_ok=True)
    # Directory creation is atomic. Publish the full capsule ownership below
    # before opening any database or input file.
    owner_path.mkdir(exist_ok=True)
    lock = _RootLock(workspace)
    lock.acquire()
    try:
        _write_import_json(owner_path / 'owner.json', ownership)
        return _restore_owned_bundle(bundle, workspace, manifest, report)
    finally:
        lock.release()


def _write_import_file(path, data):
    """Publish one owned file atomically; a conflicting final file is preserved."""
    if path.exists():
        if not path.is_file() or path.read_bytes() != data:
            raise ValueError(f'An existing workspace file differs from the capsule: {path.name}')
        return
    temporary = path.with_name('.mas-import.tmp')
    temporary.write_bytes(data)
    if path.exists():
        if not path.is_file() or path.read_bytes() != data:
            raise ValueError(f'An existing workspace file differs from the capsule: {path.name}')
        return
    temporary.replace(path)


def _write_import_json(path, value):
    _write_import_file(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def _restore_owned_bundle(bundle, workspace, manifest, report):
    parts = manifest['capsule'].get('parts') or [manifest['capsule']]
    workflows, histories, counts = [], [], Counter()
    with Core.open(workspace / "store") as core, ExitStack() as stack:
        import io
        handles = [stack.enter_context((bundle / p['path']).open('rb')) for p in parts]
        stream = stack.enter_context(gzip.GzipFile(fileobj=_ConcatenatedReader(handles), mode='rb'))
        handle = stack.enter_context(io.TextIOWrapper(stream, encoding='utf-8'))
        core.store.db.execute("BEGIN IMMEDIATE")
        try:
            for record_number, line in enumerate(handle, 1):
                record = json.loads(line)
                kind = record["record_type"]
                if kind in {"event", "artifact"}:
                    body = record["body"]
                    if not _public(body) or sha256_hex(body) != record["sha256"]:
                        raise ValueError("The capsule contains a changed or non-public record.")
                    if kind == "event":
                        source_rowid = record.get('source_rowid')
                        if manifest.get('dependency_policy', {}).get('source_rowids_required') and (type(source_rowid) is not int or source_rowid < 1):
                            raise ValueError('An original event is missing its positive source rowid.')
                        saved = core.store.db.execute('SELECT rowid,body,body_hash FROM events WHERE event_id=?', (body['event_id'],)).fetchone()
                        encoded = canonical_text(body)
                        if saved:
                            if (saved[1:] != (encoded, record['sha256'])
                                    or (source_rowid is not None and saved[0] != source_rowid)):
                                raise ValueError('An existing imported event differs from the capsule.')
                        else:
                            core.store.db.execute("INSERT INTO events (rowid,stream_id,seq,event_id,event_type,recorded_at,body,body_hash) VALUES (?,?,?,?,?,?,?,?)", (source_rowid, body["stream_id"], body["seq"],
                                body["event_id"], body["event_type"], body["recorded_at"], encoded, record["sha256"]))
                    else:
                        if body["kind"] in _FORBIDDEN or body["kind"].startswith(("case_", "recovery_")):
                            raise ValueError("The capsule contains an excluded artifact kind.")
                        saved = core.store.db.execute('SELECT kind,sha256,body,created_at FROM artifacts WHERE artifact_id=?', (record['artifact_id'],)).fetchone()
                        values = (body['kind'], record['sha256'], canonical_text(body), record['created_at'])
                        if saved:
                            if saved != values:
                                raise ValueError('An existing imported artifact differs from the capsule.')
                        else:
                            core.store.db.execute("INSERT INTO artifacts VALUES (?,?,?,?,?)", (record["artifact_id"], *values))
                elif kind == "file":
                    path = (workspace / record["path"]).resolve()
                    allowed = record['path'] in {'universe_chembl.json', 'universe_smiles.json'} or bool(
                        re.fullmatch(r'cache/admet/admet-ai-2-panel-1/[0-9a-f]{2}/[0-9a-f]{64}\.json', record['path']))
                    if not path.is_relative_to(workspace) or not allowed:
                        raise ValueError("Capsule file path escapes its declared workspace.")
                    data = base64.b64decode(record["content_base64"], validate=True)
                    if hashlib.sha256(data).hexdigest() != record["sha256"]:
                        raise ValueError("A capsule file hash differs.")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    _write_import_file(path, data)
                    if record.get("mtime"):
                        from datetime import datetime
                        import os
                        stamp = datetime.fromisoformat(record["mtime"].replace("Z", "+00:00")).timestamp()
                        os.utime(path, (stamp, stamp))
                elif kind == "workflow":
                    workflows.append(record["body"])
                elif kind == 'history_snapshot':
                    histories.append(record['body'])
                else:
                    raise ValueError(f"Unknown capsule record type: {kind}")
                counts[kind] += 1
                if record_number % 20000 == 0:
                    report(f"Restored {record_number:,} capsule records")
            core.store.db.execute("COMMIT")
        except BaseException:
            core.store.db.execute("ROLLBACK")
            raise
    if counts["event"] != manifest["counts"]["events"] or counts["artifact"] != manifest["counts"]["artifacts"]:
        raise ValueError("Imported record counts differ from the capsule manifest.")
    with sqlite3.connect(workspace / "workbench-workflows.db") as db:
        db.executescript("CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY,body TEXT NOT NULL);"
                        "CREATE TABLE IF NOT EXISTS workflows (id TEXT PRIMARY KEY,idem TEXT UNIQUE NOT NULL,body TEXT NOT NULL);"
                        "CREATE TABLE IF NOT EXISTS events (cursor INTEGER PRIMARY KEY AUTOINCREMENT,recorded_at TEXT NOT NULL,body TEXT NOT NULL);")
        for workflow in workflows:
            expected = ("reproduction:" + workflow["workflow_id"], json.dumps(workflow))
            saved = db.execute('SELECT idem,body FROM workflows WHERE id=?', (workflow['workflow_id'],)).fetchone()
            if saved:
                if saved != expected:
                    raise ValueError('An existing imported workflow differs from the capsule.')
            else:
                db.execute("INSERT INTO workflows VALUES (?,?,?)", (workflow["workflow_id"], *expected))
    _write_import_json(workspace / "workbench-state.json", {"current_task": manifest["task_id"], "settings": {}})
    with Core.open(workspace / "store", read_only=True) as core:
        support_tasks = [tid for tid in core.journal.streams("task_") if tid != manifest["task_id"]]
    _write_import_json(workspace / "workbench-display.json", {
        "version": 1, "archived_task_ids": support_tasks,
        "task_labels": {manifest["task_id"]: "Recorded oral multi-target study"},
        "snapshot_labels": {manifest["snapshot_id"]: "Recorded final evaluation"}})
    result = {"format": FORMAT, "workspace": str(workspace), "store": str(workspace / "store"),
              "task_id": manifest["task_id"], "run_id": manifest["run_id"], "snapshot_id": manifest["snapshot_id"],
              "available_historical_snapshot_artifacts": histories,
              "capsule_sha256": manifest["capsule"]["sha256"], "counts": dict(counts), "imported_at": utc_now()}
    _write_import_json(workspace / "reproduction-import.json", result)
    return result


def _same(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def verify_replay(store_root, *, task_id=DEFAULT_TASK, snapshot_id=DEFAULT_SNAPSHOT):
    """Use production qualification/scoring/ranking functions on frozen cells."""
    with Core.open(store_root, read_only=True) as core:
        saved = next(s for s in leaderboard.snapshots(core, task_id) if s["snapshot_id"] == snapshot_id)
        run_id = saved["run_id"]
        binding = core.artifacts.payload(core.journal.replay(run_id, 1, 1)[0].payload["binding_artifact_id"])
        owner, version = binding["task_context_id@v"].rsplit("@v", 1)
        context = task.get(core, owner, int(version))
        frozen = criteria.rule_set(core, task_id, saved["rules@v"])
        loaded = [{"entry": entry, "rule": criteria.load(core, entry["rule_ref"], task_id),
                   "attribute": criteria.load(core, entry["attribute_ref"], task_id)} for entry in frozen["entries"]]
        refs = {r for e in saved["candidate_entries"] for r in e["per_criterion_refs"]}
        cells, identities = {}, {}
        for body, in core.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='candidate.assessed' ORDER BY seq", (run_id,)):
            e = json.loads(body)
            cell = core.artifacts.payload(e["payload"]["artifact_id"])
            if cell["assessment_id"] in refs:
                cells[cell["assessment_id"]] = cell
        if cells.keys() != refs:
            raise ValueError("Frozen assessment dependency closure is incomplete.")
        for body, in core.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='identity.resolved' ORDER BY seq", (run_id,)):
            identity = core.artifacts.payload(json.loads(body)["payload"]["artifact_id"])
            identities[identity["candidate_id"]] = identity
        candidates = sorted(e["candidate_ref"] for e in saved["candidate_entries"])
        by_candidate = {c: [] for c in candidates}
        for entry in saved["candidate_entries"]:
            by_candidate[entry["candidate_ref"]] = [cells[r] for r in entry["per_criterion_refs"]]
        expected_cells = len(candidates) * len(loaded)
        if len(cells) != expected_cells or any(c not in identities for c in candidates):
            raise ValueError("Frozen candidate-by-rule scope is incomplete.")
        info = {r["entry"]["rule_ref"]: {"rule_kind": r["rule"]["rule_kind"],
                "predicate_form": r["rule"].get("predicate_form", "threshold"), "direction": r["attribute"].get("direction"),
                "quantity_key": criteria.quantity_identity(r["attribute"])} for r in loaded}
        mandated = [r["entry"]["rule_ref"] for r in loaded if criteria.is_task_mandated(r["attribute"])]
        pending = [r for r in frozen.get("pending", []) if criteria.load(core, r, task_id)["rule_kind"] == "hard_exclusion"]
        policy = binding.get("qualification_policy", "legacy")
        if policy != assessor.QUALIFICATION_POLICY:
            raise ValueError("This portable engine replay currently supports qualification_first_v1.")
        proof = saved.get("measurement_profile", {}).get("policy", {}).get("scoring_policy", {}).get("required_binding_check", {})
        required = [r["rule_ref"] for r in proof.get("scope_bindings", [])] if proof else criteria.required_scope_rule_refs(context, loaded)
        hard = [r["entry"]["rule_ref"] for r in loaded if r["rule"]["rule_kind"] == "hard_exclusion"]
        verified = [r["entry"]["rule_ref"] for r in loaded if r["rule"]["rule_kind"] == "hard_exclusion"
                    and not r["entry"].get("disputed") and r["entry"].get("authority") in ("machine_adjudication", "human_scientific_approval")]
        qualifications = {c: assessor.qualification(by_candidate[c], hard_rule_refs=hard, required_rule_refs=required,
                           verified_hard_rule_refs=verified, pending_hard_rules=pending,
                           admission_policy=binding.get("admission_requirement_policy", assessor.LEGACY_ADMISSION_POLICY)) for c in candidates}
        diagnostic = {c: [dict(cell, verdict="pass" if cell["verdict"] == "available" and assessor.direct_evidence(cell)
                           else "unknown_missing" if not assessor.direct_evidence(cell) and cell["verdict"] in ("pass", "fail", "available")
                           else cell["verdict"]) for cell in mine] for c, mine in by_candidate.items()}
        settings = {}
        settings_id = (binding.get("settings") or {}).get("layers_artifact_id")
        if settings_id:
            settings = {v["key"]: v["value"] for v in core.artifacts.payload(settings_id)["settings"]}
        guard = assessor.calibration_guard(diagnostic, info, mandated_rule_refs=mandated,
                    max_removed_share=settings.get("assess.max_reference_exclusion_share", assessor.DEFAULT_MAX_REFERENCE_EXCLUSION))
        guard = dict(guard, policy="diagnostic_only", demoted={}, flagged=guard.get("demoted") or {}, changes_scientific_rules=False)
        rolls = {}
        for c, mine in by_candidate.items():
            roll = assessor.roll_up(c, mine, coverage_floor=frozen.get("coverage_floor", 1.0),
                    recommended_requires_hd=context.get("human_review_requirements", {}).get("recommended_requires_hd", True),
                    pending_hard_rules=pending, machine_authority=bool(frozen.get("machine_adjudicated")))
            q = qualifications[c]
            roll.update(qualification=q, state="recommended" if q["qualified"] else "rejected" if q["state"] == "rejected" else "provisional",
                        state_reason=f"qualification: {q['state']}", hard_rule_coverage=q["hard_direct_coverage"],
                        n_preferences_evaluated=sum(x["rule_kind"] == "preference" and x["verdict"] in ("pass", "fail", "available") for x in mine))
            rolls[c] = roll
        scores = assessor.preference_scores(by_candidate, info, (frozen.get("ordering_method") or {}).get("weight_vector") or {},
                    qualified_candidates={c for c, q in qualifications.items() if q["qualified"]}, qualification_policy=policy)
        reporting = saved["reporting_tuple"]
        completeness = sum(c.get("not_assessed_reason") != "budget_exhausted" for c in cells.values()) / expected_cells
        rebuilt = leaderboard.build_snapshot(task_context=context, leaderboard_id=saved["leaderboard_id"], run_id=run_id,
                    round_id=saved["round_id"], rule_set=frozen, evidence_snapshot_id=saved["evidence_snapshot_id"],
                    roll_ups=rolls, cells=by_candidate, scores=scores, identities=identities, parent=None,
                    sweep_completeness=completeness, budget=reporting.get('budget') or {}, ranking_coverage_floor=reporting["ranking_coverage_floor"],
                    mandated_rule_refs=mandated, mandated_coverage_floor=reporting["mandated_coverage_floor"],
                    calibration_guard=guard, rank_requires_mandated_coverage=reporting["rank_requires_mandated_coverage"],
                    qualification_policy=policy, qualifications=qualifications, evaluation_mode=saved["evaluation_mode"])
        before = {e["candidate_ref"]: e for e in saved["candidate_entries"]}
        after = {e["candidate_ref"]: e for e in rebuilt["candidate_entries"]}
        differences = []
        for c in candidates:
            for field in before[c].keys() | after[c].keys():
                value = before[c].get(field)
                if not _same(value, after[c].get(field)):
                    differences.append({"candidate_ref": c, "field": field, "saved": value, "replayed": after[c].get(field)})
        for field in ("reporting_tuple", "result_kind", "no_recommendation", "abstention_reason", "all_pass_count", "calibration_guard"):
            if not _same(saved.get(field), rebuilt.get(field)):
                differences.append({"field": field, "saved": saved.get(field), "replayed": rebuilt.get(field)})
        reference = next((e for e in after.values() if "surufatinib" in " ".join(e["identity_labels"]).lower()), {})
        import mas
        source_digest = hashlib.sha256()
        package_root = Path(mas.__file__).resolve().parent
        for source in sorted(package_root.rglob('*.py')):
            source_digest.update(source.relative_to(package_root).as_posix().encode('utf-8') + b'\0')
            source_digest.update(source.read_bytes() + b'\0')
        return {"status": "pass" if not differences else "fail", "method": "production qualification -> production preference_scores -> production leaderboard.build_snapshot",
                "task_id": task_id, "run_id": run_id, "snapshot_id": snapshot_id, "candidate_count": len(candidates),
                "scoring_rule_count": len(loaded), "assessment_count": len(cells), "difference_count": len(differences),
                "differences": differences[:100], "saved_entries_sha256": sha256_hex(before), "replayed_entries_sha256": sha256_hex(after),
                "surufatinib": {k: reference.get(k) for k in ("candidate_ref", "position", "preference_score", "qualified", "preference_coverage")},
                "new_model_calls": 0, "new_retrieval_calls": 0, "new_cqa_generation": False,
                "new_cost_usd": 0, "budget_reporting_basis": "original recorded budget carried through unchanged",
                "current_implementation": {'package_version': mas.__version__, 'source_sha256': source_digest.hexdigest()},
                "source_digest_matches_recorded": source_digest.hexdigest() == binding.get('implementation', {}).get('source_sha256'),
                "recorded_implementation": binding.get("implementation"), "verified_at": utc_now()}


def prepare_live(workspace, *, task_id=DEFAULT_TASK):
    """Create an evidence-only source task for an independent zero-CQA workflow."""
    workspace = Path(workspace).resolve()
    marker = workspace / "reproduction-live-input.json"
    if marker.is_file():
        return json.loads(marker.read_text(encoding="utf-8"))
    with Core.open(workspace / "store") as core:
        original = task.get(core, task_id)
        facts_ref = original["evidence_fact_manifest_ref"]
        facts = core.artifacts.payload(facts_ref)
        created = core.journal.replay(DEFAULT_RUN, 1, 1)[0]
        binding = core.artifacts.payload(created.payload["binding_artifact_id"])
        replay = binding["tool_replay"]
        source_manifest = {"policy": "portable_pinned_terminal_tool_facts_v1", "source_task_id": task_id,
                           "source_runs": [{"run_id": r["run_id"], "pinned_seq": r["pinned_seq"],
                                            "terminal_event_id": r["terminal_event_id"], "terminal_seq": r["terminal_seq"],
                                            "execution_state": r["execution_state"]} for r in replay["sources"]],
                           "selection": "first_source_then_first_event", "reuses_decisions": False, "reads_new_evidence": False}
        source_manifest["sha256"] = sha256_hex(source_manifest)
        tools_ref = core.artifacts.put("existing_tool_fact_manifest", source_manifest)
        spec = copy.deepcopy(original)
        for key in ("task_context_id", "version", "supersedes", "created_by", "evidence_collection_source_task_id", "inheritance", "derived_from_task_id"):
            spec.pop(key, None)
        spec.update(title="Portable oral multi-target evidence", purpose="evidence_collection",
                    evidence_cutoff=binding.get("evidence_cutoff"), evidence_tool_fact_manifest_ref=tools_ref,
                    evidence_fact_manifest_ref=facts_ref, candidate_universe=dict(original["candidate_universe"],
                    access_path=str(workspace / "universe_chembl.json")))
        source_id, _ = task.record_version(core, spec, by=actor("tool", "portable-evidence-import"))
        value = copy.deepcopy(original["original_user_input"])
        value.update(source_task_id=source_id, library_id="universe_chembl.json", evidence_mode="existing_only",
                     title="Independent oral multi-target research")
        value.pop("reuse_from_run_id", None)
        result = {"source_task_id": source_id, "input": value, "pinned_claim_count": len(facts["claims"]),
                  "pinned_source_count": len(facts["source_records"]), "initial_cqa_count": 0,
                  "historical_tool_fact_count": replay["cache_entries"], "created_at": utc_now()}
    _write_json(marker, result)
    return result


def prepared_input(workspace, *, task_id=None):
    """Return a new-study setup only for this workspace's imported recorded case."""
    workspace = Path(workspace)
    imported, prepared = workspace / "reproduction-import.json", workspace / "reproduction-live-input.json"
    if not imported.is_file() or not prepared.is_file():
        return None
    origin = json.loads(imported.read_text(encoding="utf-8"))
    if task_id is not None and task_id != origin.get("task_id"):
        return None
    result = json.loads(prepared.read_text(encoding="utf-8"))
    return copy.deepcopy(result.get("input"))
