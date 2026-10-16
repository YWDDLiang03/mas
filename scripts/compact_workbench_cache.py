"""Build a smaller disposable workbench cache without changing either source DB.

Build into a new path, inspect the JSON report, then move files externally. Before
starting the workbench at its final source path, run ``rebind`` against the new
cache with the build report. A byte/hash/pointer check is required before rebinding.
No model, broker, scientific event or artifact writer is used.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import math
import sqlite3
import sys
import time
import uuid
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mas.ui.read_model import CACHE_TABLES, ReadModel, SCHEMA_VERSION

PRIMARY_TASKS = ["task_01M51AQ0JK0MYN47806ZD5XS1B", "task_01M52CBE5GYPK9F0MCZYBMPH84"]
FINAL_SNAPSHOTS = [f"lb_{task}_2" for task in PRIMARY_TASKS]
POINTERS = {
    "stages": ("opened_row", "closed_row"),
    "criteria_current": ("updated_row",), "criteria_listing": ("updated_row",),
    "criterion_versions": ("source_row",), "criterion_changes": ("source_row",),
    "snapshots": ("published_row",), "assessments": ("source_row",), "claims": ("source_row",),
    "evidence_links": ("source_row", "assessment_row", "superseded_row"),
}
CQA_TABLES = {"criteria_current", "criteria_listing", "criterion_aliases", "criterion_versions",
              "criterion_changes", "registry_rules", "registry_transitions", "registry_collapses", "reviews"}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_file(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def connect_ro(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    db.execute("PRAGMA cache_size=-131072")
    db.execute("PRAGMA mmap_size=2147483648")
    return db


def attach_ro(db, name, path):
    db.execute(f"ATTACH DATABASE ? AS {name}", (Path(path).resolve().as_uri() + "?mode=ro",))


def event_digest(db, schema="main"):
    digest = hashlib.sha256()
    count = 0
    for row in db.execute(f"SELECT rowid,event_id,body_hash,stream_id,seq,recorded_at FROM {schema}.events ORDER BY rowid"):
        digest.update((encoded(list(row)) + "\n").encode())
        count += 1
    return {"events": count, "sha256": digest.hexdigest()}


def meta(db, schema="main"):
    return {row[0]: json.loads(row[1]) for row in db.execute(f"SELECT key,value FROM {schema}.metadata")}


def source_identity(path):
    path = Path(path).resolve()
    stat = path.stat()
    return {"path": str(path), "device": stat.st_dev, "inode": stat.st_ino}


def source_tail(db, schema="kept"):
    row = db.execute(f"SELECT rowid,event_id,body_hash,stream_id,seq,recorded_at FROM {schema}.events ORDER BY rowid DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stats(db, schema="main"):
    return {table: db.execute(f'SELECT count(*) FROM {schema}."{table}"').fetchone()[0] for table in CACHE_TABLES}


def check_pointers(db, schema="main", source="kept"):
    result = {}
    for table, columns in POINTERS.items():
        for column in columns:
            missing = db.execute(f'SELECT count(*) FROM {schema}."{table}" p WHERE p."{column}">0 '
                f'AND NOT EXISTS (SELECT 1 FROM {source}.events e WHERE e.rowid=p."{column}")').fetchone()[0]
            result[f"{table}.{column}"] = missing
            require(missing == 0, f"{table}.{column} has {missing} references outside the compact source")
    mismatch = db.execute(f"SELECT count(*) FROM {schema}.assessments p JOIN {source}.events e ON e.rowid=p.source_row "
                          "WHERE p.run_id<>e.stream_id OR p.source_seq<>e.seq OR e.event_type<>'candidate.assessed'").fetchone()[0]
    require(mismatch == 0, "Assessment source stream/sequence/type changed")
    result["assessment_event_mismatches"] = mismatch
    return result


def check_artifacts(db):
    result = {}
    for table in ("criteria_current", "criteria_listing", "criterion_versions", "snapshots", "assessments", "claims"):
        columns = ("artifact_id", "reason_artifact_id") if table == "assessments" else ("artifact_id",)
        for column in columns:
            missing = db.execute(f'SELECT count(*) FROM "{table}" p WHERE p."{column}" IS NOT NULL AND length(p."{column}")>0 '
                f'AND NOT EXISTS (SELECT 1 FROM kept.artifacts a WHERE a.artifact_id=p."{column}")').fetchone()[0]
            result[f"{table}.{column}"] = missing
            require(missing == 0, f"Missing source artifact for {table}.{column}: {missing}")
    for table, column in (("evidence_documents", "artifact_id"),):
        missing = db.execute(f'SELECT count(*) FROM "{table}" p WHERE NOT EXISTS '
                             f'(SELECT 1 FROM kept.artifacts a WHERE a.artifact_id=p."{column}")').fetchone()[0]
        result[f"{table}.{column}"] = missing
        require(missing == 0, f"Missing saved document artifact: {missing}")
    return result


def parity(db, task_ids, snapshots):
    result = {}
    for task in task_ids:
        per_task = {}
        for table in sorted(CQA_TABLES | {"stages"}):
            common = "task_id=?"
            if table == "stages":
                common += " AND run_id IN (SELECT run_id FROM keep_runs)"
            before = db.execute(f'SELECT count(*) FROM prior."{table}" WHERE {common}', (task,)).fetchone()[0]
            after = db.execute(f'SELECT count(*) FROM main."{table}" WHERE task_id=?', (task,)).fetchone()[0]
            require(before == after, f"Primary criterion history count changed: {task} {table}")
            difference = db.execute(f'SELECT * FROM prior."{table}" WHERE {common} EXCEPT '
                                    f'SELECT * FROM main."{table}" WHERE task_id=? LIMIT 1', (task, task)).fetchone()
            require(difference is None, f"Primary criterion history content changed: {task} {table}")
            per_task[table] = after
        result[task] = per_task
    for snapshot in snapshots:
        count = db.execute("SELECT count(*) FROM candidate_rows WHERE snapshot_id=?", (snapshot,)).fetchone()[0]
        difference = db.execute("SELECT * FROM prior.candidate_rows WHERE snapshot_id=? EXCEPT "
                                "SELECT * FROM main.candidate_rows WHERE snapshot_id=? LIMIT 1", (snapshot, snapshot)).fetchone()
        require(count == db.execute("SELECT count(*) FROM prior.candidate_rows WHERE snapshot_id=?", (snapshot,)).fetchone()[0]
                and difference is None, f"Final candidate rows changed: {snapshot}")
        result[snapshot] = {"candidate_rows": count, "exact_prior_rows": True}
    return result


def build(args):
    started = time.perf_counter()
    cache, original, compact, output, report = [Path(value).resolve() for value in
        (args.cache, args.original_source, args.compact_source, args.output, args.report)]
    for path in (cache, original, compact):
        require(path.is_file(), f"Input is not a file: {path}")
    require(len({cache, original, compact, output}) == 4, "Inputs and output must be separate files")
    require(not output.exists() and not report.exists(), "Output/report already exists; use new paths")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = output.with_name(output.stem + ".working-" + uuid.uuid4().hex[:8] + ".db")
    db = sqlite3.connect(work, timeout=30, uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=DELETE")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA temp_store=MEMORY")
    db.execute("PRAGMA cache_size=-131072")
    db.execute("PRAGMA mmap_size=2147483648")
    attach_ro(db, "prior", cache)
    attach_ro(db, "original", original)
    attach_ro(db, "kept", compact)
    payload = {"version": 1, "original_cache": str(cache), "original_source": str(original),
               "compact_source": str(compact), "output_cache": str(output), "original_cache_identity": source_identity(cache), "primary_task_ids": args.task or PRIMARY_TASKS,
               "final_snapshot_ids": args.snapshot or FINAL_SNAPSHOTS, "scientific_writes": 0,
               "models_called": 0, "status": "building"}
    try:
        prior_meta = meta(db, "prior")
        require(prior_meta.get("ready") and prior_meta.get("schema_version") == SCHEMA_VERSION,
                "Existing cache must be ready and use the current projection schema")
        prior_anchor = db.execute("SELECT rowid,event_id,body_hash,stream_id,seq,recorded_at FROM original.events WHERE rowid=?",
                                  (prior_meta.get("cursor"),)).fetchone()
        require(prior_anchor is not None and dict(prior_anchor) == prior_meta.get("anchor"),
                "Existing cache anchor does not match the original source")
        payload["prior_cache_anchor_validated"] = True
        tail = source_tail(db)
        require(tail is not None and int(prior_meta.get("cursor", 0)) >= tail["rowid"], "Cache has not projected the retained source tail")
        # Compare only retained public/source-dependency events; no unrelated or
        # evaluator artifacts are opened. SQLite compares the preserved body bytes.
        print("Checking retained source event rows and original body bytes", flush=True)
        mismatch = db.execute("SELECT count(*) FROM kept.events k LEFT JOIN original.events o ON o.rowid=k.rowid "
            "WHERE o.rowid IS NULL OR k.event_id<>o.event_id OR k.stream_id<>o.stream_id OR k.seq<>o.seq "
            "OR k.event_type<>o.event_type OR k.body_hash<>o.body_hash OR k.body<>o.body").fetchone()[0]
        require(mismatch == 0, f"Compact source does not preserve retained event bytes/rowids: {mismatch}")
        payload["source_event_parity"] = {"mismatches": mismatch, **event_digest(db, "kept")}
        payload["before"] = stats(db, "prior")
        db.execute("CREATE TEMP TABLE keep_events(row_id INTEGER PRIMARY KEY)")
        db.execute("INSERT INTO keep_events SELECT rowid FROM kept.events")
        db.execute("CREATE TEMP TABLE primary_tasks(task_id TEXT PRIMARY KEY)")
        db.executemany("INSERT INTO primary_tasks VALUES(?)", [(task,) for task in payload["primary_task_ids"]])
        db.execute("CREATE TEMP TABLE keep_tasks(task_id TEXT PRIMARY KEY)")
        db.execute("INSERT INTO keep_tasks SELECT task_id FROM primary_tasks")
        pending = list(payload["primary_task_ids"])
        support = set(args.support_task or [])
        while pending:
            task = pending.pop()
            row = db.execute("SELECT body FROM prior.tasks WHERE task_id=?", (task,)).fetchone()
            require(row is not None, f"Task not present in old cache: {task}")
            parent = (json.loads(row[0]).get("input") or {}).get("source_task_id")
            if parent and parent != task and not db.execute("SELECT 1 FROM keep_tasks WHERE task_id=?", (parent,)).fetchone():
                support.add(parent)
                db.execute("INSERT INTO keep_tasks VALUES(?)", (parent,))
                pending.append(parent)
        db.executemany("INSERT OR IGNORE INTO keep_tasks VALUES(?)", [(task,) for task in support])
        for row in db.execute("SELECT task_id FROM keep_tasks"):
            require(db.execute("SELECT 1 FROM kept.events WHERE stream_id=? AND event_type='task.version_recorded' LIMIT 1", (row[0],)).fetchone(),
                    f"Required source task context absent: {row[0]}")
        payload["support_task_ids"] = sorted(support)
        db.execute("CREATE TEMP TABLE final_snapshots(snapshot_id TEXT PRIMARY KEY)")
        db.executemany("INSERT INTO final_snapshots VALUES(?)", [(snapshot,) for snapshot in payload["final_snapshot_ids"]])
        db.execute("CREATE TEMP TABLE support_snapshots(snapshot_id TEXT PRIMARY KEY)")
        # Only each bound support collection's latest snapshot summary is retained.
        # Candidate entries inside its immutable source artifact stay source-only.
        for task in support:
            row = db.execute("SELECT s.snapshot_id FROM prior.snapshots s JOIN kept.events e ON e.rowid=s.published_row "
                             "WHERE s.task_id=? ORDER BY s.published_row DESC LIMIT 1", (task,)).fetchone()
            if row:
                db.execute("INSERT OR IGNORE INTO support_snapshots VALUES(?)", (row[0],))
        payload["support_snapshot_ids"] = [row[0] for row in db.execute("SELECT snapshot_id FROM support_snapshots")]
        db.execute("CREATE TEMP TABLE final_runs(run_id TEXT PRIMARY KEY)")
        db.execute("INSERT INTO final_runs SELECT run_id FROM prior.snapshots WHERE snapshot_id IN (SELECT snapshot_id FROM final_snapshots)")
        require(db.execute("SELECT count(*) FROM final_runs").fetchone()[0] == len(payload["final_snapshot_ids"]), "A final snapshot/run is absent")
        db.execute("CREATE TEMP TABLE keep_runs(run_id TEXT PRIMARY KEY)")
        db.execute("INSERT INTO keep_runs SELECT run_id FROM final_runs")
        db.execute("INSERT OR IGNORE INTO keep_runs SELECT run_id FROM prior.runs r WHERE r.task_id IN (SELECT task_id FROM primary_tasks) "
            "AND json_extract(r.body,'$.run_purpose')='criteria_derivation' "
            "AND EXISTS (SELECT 1 FROM kept.events e WHERE e.stream_id=r.run_id AND e.event_type='run.created')")
        db.execute("INSERT OR IGNORE INTO keep_runs SELECT run_id FROM prior.snapshots WHERE snapshot_id IN (SELECT snapshot_id FROM support_snapshots)")
        payload["kept_run_ids"] = [row[0] for row in db.execute("SELECT run_id FROM keep_runs")]
        for row in db.execute("SELECT sql FROM prior.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            db.execute(row[0])
        conditions = {
            "metadata": "key NOT LIKE 'frozen:%' OR substr(key,8) IN (SELECT task_id FROM primary_tasks)",
            "tasks": "task_id IN (SELECT task_id FROM keep_tasks)",
            "runs": "run_id IN (SELECT run_id FROM keep_runs)",
            "run_progress": "run_id IN (SELECT run_id FROM keep_runs) AND run_id NOT IN (SELECT run_id FROM prior.snapshots WHERE snapshot_id IN (SELECT snapshot_id FROM support_snapshots))",
            "stages": "task_id IN (SELECT task_id FROM primary_tasks) AND run_id IN (SELECT run_id FROM keep_runs)",
            "snapshots": "snapshot_id IN (SELECT snapshot_id FROM final_snapshots UNION SELECT snapshot_id FROM support_snapshots)",
            "candidate_rows": "snapshot_id IN (SELECT snapshot_id FROM final_snapshots)",
            "assessments": "run_id IN (SELECT run_id FROM final_runs)",
            "claims": "task_id IN (SELECT task_id FROM keep_tasks) AND source_row IN (SELECT row_id FROM keep_events)",
            "task_summaries": "task_id IN (SELECT task_id FROM keep_tasks)",
            "run_pool_scope": "run_id IN (SELECT run_id FROM keep_runs)",
            "evidence_links": "task_id IN (SELECT task_id FROM primary_tasks) AND source_row IN (SELECT row_id FROM keep_events) AND (assessment_row=0 OR run_id IN (SELECT run_id FROM final_runs))",
        }
        for table in CQA_TABLES:
            conditions[table] = "task_id IN (SELECT task_id FROM primary_tasks)"
        order = [table for table in CACHE_TABLES if table not in ("claim_origins", "evidence_documents", "evidence_sources")]
        for table in order:
            db.execute(f'INSERT INTO main."{table}" SELECT * FROM prior."{table}" WHERE {conditions[table]}')
            count = db.execute(f'SELECT count(*) FROM main."{table}"').fetchone()[0]
            print(f"Copied {table}: {count}", flush=True)
        db.execute("CREATE TEMP TABLE relevant_claims(task_id TEXT,claim_id TEXT,PRIMARY KEY(task_id,claim_id))")
        db.execute("INSERT OR IGNORE INTO relevant_claims SELECT task_id,claim_id FROM claims")
        while True:
            cursor = db.execute("INSERT OR IGNORE INTO relevant_claims SELECT o.task_id,o.parent_id FROM prior.claim_origins o "
                                "JOIN relevant_claims c ON c.task_id=o.task_id AND c.claim_id=o.claim_id")
            if cursor.rowcount == 0:
                break
        db.execute("INSERT INTO claim_origins SELECT o.* FROM prior.claim_origins o JOIN relevant_claims c "
                   "ON c.task_id=o.task_id AND c.claim_id=o.claim_id")
        db.execute("CREATE TEMP TABLE relevant_sources(task_id TEXT,source_id TEXT,PRIMARY KEY(task_id,source_id))")
        db.execute("INSERT OR IGNORE INTO relevant_sources SELECT task_id,source_id FROM claims")
        db.execute("INSERT INTO evidence_sources SELECT s.* FROM prior.evidence_sources s JOIN relevant_sources r "
                   "ON r.task_id=s.task_id AND r.source_id=s.source_id")
        db.execute("CREATE TEMP TABLE relevant_documents(task_id TEXT,artifact_id TEXT,PRIMARY KEY(task_id,artifact_id))")
        db.execute("INSERT OR IGNORE INTO relevant_documents SELECT task_id,json_extract(body,'$.document_artifact_id') "
                   "FROM claims WHERE json_extract(body,'$.document_artifact_id') IS NOT NULL")
        db.execute("INSERT INTO evidence_documents SELECT d.* FROM prior.evidence_documents d JOIN relevant_documents r "
                   "ON r.task_id=d.task_id AND r.artifact_id=d.artifact_id "
                   "WHERE EXISTS (SELECT 1 FROM kept.artifacts a WHERE a.artifact_id=d.artifact_id AND a.kind='document')")
        print("Creating indexes on the new cache", flush=True)
        for row in db.execute("SELECT sql FROM prior.sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY name").fetchall():
            db.execute(row[0])
        # Support contexts have intentionally lost their research outputs. Rebuild
        # their compact task/run metadata from the retained records, never future state.
        projector = ReadModel.__new__(ReadModel)
        with closing(connect_ro(compact)) as source:
            for task in support:
                db.execute("DELETE FROM tasks WHERE task_id=?", (task,))
                for row in source.execute("SELECT rowid,body FROM events WHERE stream_id=? AND event_type='task.version_recorded' ORDER BY rowid", (task,)):
                    event = json.loads(row["body"])
                    if event.get("visibility", "default") == "default":
                        projector._project(db, source, row["rowid"], event)
                for row in db.execute("SELECT run_id FROM runs WHERE task_id=?", (task,)).fetchall():
                    db.execute("DELETE FROM runs WHERE run_id=?", (row[0],))
                    for e in source.execute("SELECT rowid,body FROM events WHERE stream_id=? ORDER BY rowid", (row[0],)):
                        event = json.loads(e["body"])
                        if event.get("visibility", "default") == "default" and (event.get("event_type") == "run.created" or
                                (str(event.get("event_type", "")).startswith("run.") and event.get("state_to"))):
                            projector._project(db, source, e["rowid"], event)
        print("Validating source-row pointers and artifact references", flush=True)
        payload["pointer_validation"] = check_pointers(db)
        payload["artifact_validation"] = check_artifacts(db)
        print("Comparing complete primary criterion history and final candidate rows", flush=True)
        payload["exact_primary_parity"] = parity(db, payload["primary_task_ids"], payload["final_snapshot_ids"])
        for task in db.execute("SELECT task_id FROM keep_tasks").fetchall():
            projector._summarise(db, task[0])
        payload["primary_summary_changes"] = {}
        for task in payload["primary_task_ids"]:
            old = json.loads(db.execute("SELECT body FROM prior.task_summaries WHERE task_id=?", (task,)).fetchone()[0])
            new = json.loads(db.execute("SELECT body FROM task_summaries WHERE task_id=?", (task,)).fetchone()[0])
            difference = {key: {"before": old.get(key), "after": new.get(key)} for key in old.keys() | new.keys() if old.get(key) != new.get(key)}
            require(set(difference) <= {"run_count", "claim_count"}, f"Scientific criterion summary changed: {task}: {difference}")
            payload["primary_summary_changes"][task] = difference
        parity(db, payload["primary_task_ids"], payload["final_snapshot_ids"])
        identity = source_identity(compact)
        ReadModel._set_meta(db, {"source_identity": identity, "cursor": tail["rowid"], "anchor": tail,
            "source_as_of": tail["recorded_at"], "ready": True, "schema_version": SCHEMA_VERSION})
        payload["after"] = stats(db)
        payload["anchor"] = tail
        payload["source_identity_before_final_move"] = identity
        db.commit()
        print("Checking cache integrity", flush=True)
        require(db.execute("PRAGMA main.quick_check").fetchone()[0] == "ok", "Working cache quick check failed")
        print("Writing compact cache with VACUUM INTO", flush=True)
        vacuum_start = time.perf_counter()
        db.execute("VACUUM main INTO ?", (str(output),))
        payload["vacuum_seconds"] = time.perf_counter() - vacuum_start
        db.close()
        with closing(connect_ro(output)) as final:
            require(final.execute("PRAGMA main.integrity_check").fetchone()[0] == "ok", "Output integrity check failed")
        payload.update(status="validated", original_cache_bytes=cache.stat().st_size, cache_bytes=output.stat().st_size,
                       cache_sha256=sha_file(output), compact_source_sha256=sha_file(compact),
                       elapsed_seconds=time.perf_counter()-started,
                       rebuild_assessment={"performed": False, "reason": "Full replay would re-project every assessment and evidence relation. Exact-row reuse avoids rerunning already-valid projection work.",
                           "events": payload["source_event_parity"]["events"], "event_budget_seconds_at_100_to_500_per_second":
                           [math.ceil(payload["source_event_parity"]["events"]/500), math.ceil(payload["source_event_parity"]["events"]/100)],
                           "estimate_only": True})
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        work.unlink()
        print(json.dumps({"status": payload["status"], "cache": str(output), "bytes": payload["cache_bytes"], "report": str(report)}), flush=True)
    except Exception as error:
        db.close()
        payload.update(status="failed", error=str(error), scratch_cache=str(work), elapsed_seconds=time.perf_counter()-started)
        if not report.exists():
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise



def resume(args):
    """Finish an already committed scratch cache; no original rows are recopied."""
    started = time.perf_counter()
    cache, compact, work, output, report, manifest_path = [Path(value).resolve() for value in
        (args.cache, args.compact_source, args.work, args.output, args.report, args.source_proof)]
    require(all(path.is_file() for path in (cache, compact, work, manifest_path)), "Resume inputs are incomplete")
    require(len({cache, compact, work, output}) == 4 and '.working-' in work.name,
            "Resume only a separate generated working cache")
    require(not output.exists() and not report.exists(), "Resume output/report already exists")
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    verification = manifest.get('verification') or {}
    require(Path(manifest['candidate_path']).resolve() == compact and
            verification.get('exact_event_rowid_body_hash') is True and
            verification.get('exact_artifact_rowid_body_hash') is True and
            verification.get('integrity_check') == 'ok', "A validated source retention proof is required")
    tasks, snapshots = manifest['primary_task_ids'], manifest['final_snapshot_ids']
    db = sqlite3.connect(work, uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA cache_size=-131072')
    db.execute('PRAGMA mmap_size=2147483648')
    db.execute('PRAGMA temp_store=MEMORY')
    attach_ro(db, 'prior', cache)
    attach_ro(db, 'kept', compact)
    tail = source_tail(db)
    require(meta(db).get('ready') and meta(db).get('anchor') == tail and
            meta(db).get('source_identity') == source_identity(compact),
            'Working cache has not committed a validated compact-source anchor')
    db.execute('CREATE TEMP TABLE keep_runs(run_id TEXT PRIMARY KEY)')
    db.execute('INSERT INTO keep_runs SELECT run_id FROM main.runs')
    print('Resume: verifying committed primary rows and source pointers', flush=True)
    proof = {'version': 1, 'status': 'validating', 'original_cache': str(cache),
             'original_cache_identity': source_identity(cache), 'compact_source': str(compact),
             'output_cache': str(output), 'resumed_committed_workfile': str(work),
             'primary_task_ids': tasks, 'final_snapshot_ids': snapshots,
             'support_task_ids': [row[0] for row in db.execute('SELECT task_id FROM tasks') if row[0] not in tasks],
             'support_snapshot_ids': [row[0] for row in db.execute('SELECT snapshot_id FROM snapshots') if row[0] not in snapshots],
             'kept_run_ids': [row[0] for row in db.execute('SELECT run_id FROM runs')],
             'source_retention_proof': str(manifest_path), 'source_integrity_check_reused': True,
             'scientific_writes': 0, 'models_called': 0}
    proof['pointer_validation'] = check_pointers(db)
    proof['artifact_validation'] = check_artifacts(db)
    proof['exact_primary_parity'] = parity(db, tasks, snapshots)
    proof['primary_summary_changes'] = {}
    for task in tasks:
        old = json.loads(db.execute('SELECT body FROM prior.task_summaries WHERE task_id=?', (task,)).fetchone()[0])
        current = json.loads(db.execute('SELECT body FROM task_summaries WHERE task_id=?', (task,)).fetchone()[0])
        difference = {key: {'before': old.get(key), 'after': current.get(key)} for key in old.keys() | current.keys() if old.get(key) != current.get(key)}
        require(set(difference) <= {'run_count', 'claim_count'}, f'Primary criterion summary changed: {task}')
        proof['primary_summary_changes'][task] = difference
    proof['source_event_parity'] = {'mismatches': 0, **event_digest(db, 'kept')}
    require(proof['source_event_parity']['events'] == manifest['event_count'], 'Source event count changed after retention proof')
    proof['before'], proof['after'] = stats(db, 'prior'), stats(db)
    proof['anchor'] = tail
    proof['source_identity_before_final_move'] = source_identity(compact)
    print('Resume: main.quick_check on working cache only', flush=True)
    require(db.execute('PRAGMA main.quick_check').fetchone()[0] == 'ok', 'Working quick check failed')
    db.commit()
    print('Resume: VACUUM main INTO new output', flush=True)
    began = time.perf_counter()
    db.execute('VACUUM main INTO ?', (str(output),))
    proof['vacuum_seconds'] = time.perf_counter() - began
    db.close()
    print('Resume: one main.integrity_check on final output only', flush=True)
    began = time.perf_counter()
    with closing(connect_ro(output)) as final:
        require(final.execute('PRAGMA main.integrity_check').fetchone()[0] == 'ok', 'Final integrity check failed')
    proof['final_integrity_seconds'] = time.perf_counter() - began
    print('Resume: sealing source/cache hashes', flush=True)
    proof.update(status='validated', original_cache_bytes=cache.stat().st_size,
                 cache_bytes=output.stat().st_size, cache_sha256=sha_file(output),
                 compact_source_sha256=sha_file(compact), elapsed_seconds=time.perf_counter()-started,
                 rebuild_assessment={'performed': False, 'estimate_only': True,
                    'events': manifest['event_count'], 'illustrative_seconds_at_100_to_500_events_per_second':
                    [math.ceil(manifest['event_count']/500), math.ceil(manifest['event_count']/100)],
                    'note': 'Throughput is an explicit planning assumption, not a measured replay ETA. Source and final cache have each had one scoped full integrity check.'})
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    work.unlink()
    print(json.dumps({'status': 'validated', 'cache': str(output), 'bytes': proof['cache_bytes'], 'report': str(report)}), flush=True)


def rebind(args):
    cache, source, proof_path, report = [Path(value).resolve() for value in (args.cache, args.source, args.proof, args.report)]
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    require(proof.get("status") == "validated", "Build proof is not validated")
    require(not report.exists(), "Rebind report already exists")
    identity = source_identity(cache)
    original_identity = proof["original_cache_identity"]
    require(cache != source and (identity["device"], identity["inode"]) !=
            (original_identity["device"], original_identity["inode"]),
            "Refuse original cache/source mutation; rebind only the proof-matched compact cache")
    require(sha_file(cache) == proof["cache_sha256"], "Cache differs from the validated staged output")
    require(sha_file(source) == proof["compact_source_sha256"], "Final source differs from the validated compact source")
    with closing(connect_ro(source)) as scientific:
        expected = {key: proof["source_event_parity"][key] for key in ("events", "sha256")}
        require(event_digest(scientific) == expected, "Source event digest changed")
    db = sqlite3.connect(cache, uri=True)
    db.row_factory = sqlite3.Row
    attach_ro(db, "kept", source)
    require(source_tail(db) == proof["anchor"], "Final source anchor changed")
    require(meta(db).get("anchor") == proof["anchor"], "Cache anchor changed")
    pointers = check_pointers(db)
    old = meta(db).get("source_identity")
    identity = source_identity(source)
    ReadModel._set_meta(db, {"source_identity": identity})
    db.commit()
    db.close()
    result = {"status": "rebound", "cache": str(cache), "source": str(source), "previous_source_identity": old,
              "source_identity": identity, "pointer_validation": pointers, "cache_sha256": sha_file(cache),
              "scientific_writes": 0, "models_called": 0}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "rebound", "report": str(report)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("build", help="Create and validate a new cache; never replaces originals")
    for flag in ("cache", "original-source", "compact-source", "output", "report"):
        p.add_argument("--" + flag, required=True)
    for flag in ("task", "snapshot", "support-task"):
        p.add_argument("--" + flag, action="append")
    p.set_defaults(func=build)
    p = sub.add_parser("resume", help="Finish a committed scratch cache with source retention proof")
    for flag in ("cache", "compact-source", "work", "output", "report", "source-proof"):
        p.add_argument("--" + flag, required=True)
    p.set_defaults(func=resume)
    p = sub.add_parser("rebind", help="After the source move, bind only a proof-matched staged cache")
    for flag in ("cache", "source", "proof", "report"):
        p.add_argument("--" + flag, required=True)
    p.set_defaults(func=rebind)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
