"""Rebuildable, incremental read model for the local workbench.

The scientific journal is always opened with ``mode=ro``.  Only this separate
cache is written. Readers never synchronise the journal: the host calls sync()
from its background worker, and each reader gets an independent WAL connection.
Large assessments and claims are indexed by reference and loaded on demand.
"""

from __future__ import annotations

import difflib
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from mas.core.criteria import is_task_mandated


SCHEMA_VERSION = 4
PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
PUBLIC_EVENTS = (
    "task.version_recorded", "run.created", "run.started", "run.paused", "run.resumed",
    "run.cancelled", "run.completed", "run.unresolved", "run.failed", "run.continued",
    "stage.opened", "stage.closed", "criterion.version_proposed", "criterion.change_recorded",
    "criterion.version_approved", "leaderboard.snapshot_published", "candidate.assessed",
    "evidence.admitted", "evidence.quarantined", "identity.resolved", "step.started", "step.completed",
    "agent.finished", "agent.started", "tool.requested", "human.review_requested",
    "human.review_decided", "human.review_withdrawn", "decision.recorded",
)
ARTIFACT_KINDS = frozenset({
    "task_context", "run_binding", "attribute", "rule", "rule_set", "criterion_candidate",
    "leaderboard_snapshot", "assessment", "reason", "claim", "derivation_stage", "source",
    "candidate_identity", "identity", "registered_reduction_inputs",
})
POOL_LIVE = ("candidate", "needs_refine", "deferred_next_round", "promoted")
CACHE_TABLES = ("metadata", "tasks", "runs", "stages", "criteria_current", "criterion_aliases",
                "criterion_versions", "criterion_changes", "snapshots", "candidate_rows", "assessments",
                "claims", "task_summaries", "run_progress", "registry_rules", "registry_transitions",
                "registry_collapses", "reviews", "run_pool_scope", "criteria_listing")
CRITERIA_STAGES = frozenset({"propose", "refine", "filter", "merge", "consolidate", "promote",
                             "critic", "reduce", "review", "freeze", "registry_inputs", "reenter", "distill"})

SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tasks(
 task_id TEXT PRIMARY KEY, title TEXT, objective TEXT, version INTEGER, updated_at TEXT,
 candidate_count INTEGER, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs(
 run_id TEXT PRIMARY KEY,task_id TEXT,state TEXT,started_at TEXT,updated_at TEXT,body TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS runs_task ON runs(task_id,updated_at DESC);
CREATE TABLE IF NOT EXISTS run_progress(run_id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stages(
 stage_id TEXT PRIMARY KEY,task_id TEXT,run_id TEXT,stage TEXT,iteration INTEGER,
 opened_row INTEGER,closed_row INTEGER,body TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS stages_task ON stages(task_id,opened_row,closed_row);
CREATE INDEX IF NOT EXISTS stages_run ON stages(run_id,stage,iteration,opened_row DESC);
CREATE TABLE IF NOT EXISTS criteria_current(
 task_id TEXT,criterion_id TEXT,version INTEGER,state TEXT,role TEXT,name TEXT,
 kind TEXT,updated_row INTEGER,artifact_id TEXT,body TEXT NOT NULL,
 PRIMARY KEY(task_id,criterion_id));
CREATE INDEX IF NOT EXISTS criteria_filter ON criteria_current(task_id,state,criterion_id);
CREATE TABLE IF NOT EXISTS criteria_listing(
 task_id TEXT,criterion_id TEXT,version INTEGER,state TEXT,role TEXT,name TEXT,
 kind TEXT,updated_row INTEGER,artifact_id TEXT,body TEXT NOT NULL,
 PRIMARY KEY(task_id,criterion_id));
CREATE INDEX IF NOT EXISTS criteria_listing_filter ON criteria_listing(task_id,state,criterion_id);
CREATE TABLE IF NOT EXISTS registry_rules(
 task_id TEXT,base_id TEXT,ref TEXT,attribute_ref TEXT,artifact_id TEXT,body TEXT,
 PRIMARY KEY(task_id,base_id));
CREATE TABLE IF NOT EXISTS registry_transitions(task_id TEXT,ref TEXT,state TEXT,PRIMARY KEY(task_id,ref));
CREATE TABLE IF NOT EXISTS registry_collapses(task_id TEXT,collapse_id TEXT,attribute_ref TEXT,withdrawn INTEGER,
 PRIMARY KEY(task_id,collapse_id,attribute_ref));
CREATE TABLE IF NOT EXISTS reviews(task_id TEXT,item_id TEXT,subject_ref TEXT,state TEXT,PRIMARY KEY(task_id,item_id));
CREATE TABLE IF NOT EXISTS run_pool_scope(run_id TEXT,criterion_id TEXT,PRIMARY KEY(run_id,criterion_id));
CREATE TABLE IF NOT EXISTS criterion_aliases(
 task_id TEXT,alias TEXT,criterion_id TEXT,PRIMARY KEY(task_id,alias));
CREATE TABLE IF NOT EXISTS criterion_versions(
 task_id TEXT,ref TEXT,kind TEXT,base_id TEXT,version INTEGER,artifact_id TEXT,
 source_row INTEGER,body TEXT NOT NULL,PRIMARY KEY(task_id,ref));
CREATE INDEX IF NOT EXISTS versions_base ON criterion_versions(task_id,base_id,version);
CREATE TABLE IF NOT EXISTS criterion_changes(
 source_row INTEGER PRIMARY KEY,task_id TEXT,criterion_id TEXT,version INTEGER,stage_id TEXT,
 run_id TEXT,stage TEXT,operation TEXT,at TEXT,body TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS changes_criterion ON criterion_changes(task_id,criterion_id,source_row);
CREATE INDEX IF NOT EXISTS changes_stage ON criterion_changes(task_id,stage_id,criterion_id);
CREATE TABLE IF NOT EXISTS snapshots(
 snapshot_id TEXT PRIMARY KEY,task_id TEXT,run_id TEXT,published_row INTEGER,published_at TEXT,
 artifact_id TEXT,body TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS snapshots_task ON snapshots(task_id,published_row DESC);
CREATE TABLE IF NOT EXISTS candidate_rows(
 snapshot_id TEXT,candidate_ref TEXT,qualification TEXT,position INTEGER,ordinal INTEGER,
 label TEXT,body TEXT NOT NULL,raw TEXT NOT NULL,PRIMARY KEY(snapshot_id,candidate_ref));
CREATE INDEX IF NOT EXISTS candidate_page ON candidate_rows(snapshot_id,qualification,ordinal);
CREATE INDEX IF NOT EXISTS candidate_all_page ON candidate_rows(snapshot_id,ordinal);
CREATE TABLE IF NOT EXISTS assessments(
 run_id TEXT,candidate_ref TEXT,attribute_ref TEXT,rule_ref TEXT,source_row INTEGER,
 source_seq INTEGER,artifact_id TEXT,reason_artifact_id TEXT,verdict TEXT,
 PRIMARY KEY(source_row));
CREATE INDEX IF NOT EXISTS assessments_candidate ON assessments(run_id,candidate_ref,source_row);
CREATE TABLE IF NOT EXISTS claims(
 task_id TEXT,claim_id TEXT,stream_id TEXT,candidate_ref TEXT,attribute_ref TEXT,source_id TEXT,
 artifact_id TEXT,source_row INTEGER,admission_state TEXT,body TEXT,search_text TEXT,
 PRIMARY KEY(source_row));
CREATE INDEX IF NOT EXISTS claims_task ON claims(task_id,source_row DESC);
CREATE INDEX IF NOT EXISTS claims_page ON claims(task_id,admission_state,source_row DESC);
CREATE INDEX IF NOT EXISTS claims_candidate ON claims(task_id,candidate_ref,stream_id);
CREATE INDEX IF NOT EXISTS claims_id ON claims(task_id,claim_id);
CREATE TABLE IF NOT EXISTS task_summaries(task_id TEXT PRIMARY KEY,body TEXT NOT NULL);
"""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _record(row: sqlite3.Row | None) -> dict[str, Any]:
    return json.loads(row["body"]) if row else {}


def _page(page: int, page_size: int) -> tuple[int, int, int]:
    page, page_size = max(1, int(page)), max(1, min(MAX_PAGE_SIZE, int(page_size)))
    return page, page_size, (page - 1) * page_size


def _like(value: str) -> str:
    return "%" + str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


class ProjectionNotReady(RuntimeError):
    pass


class ReadModel:
    def __init__(self, store_root: str | Path, cache_path: str | Path | None = None):
        root = Path(store_root).resolve()
        self.source_path = root if root.suffix == ".db" else root / "store.db"
        self.cache_path = Path(cache_path).resolve() if cache_path else self.source_path.parent.parent / "workbench-read.db"
        if self.source_path == self.cache_path:
            raise ValueError("the read model cache must be separate from the source journal")
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._sync_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._syncing = False
        self._error: str | None = None
        with self._cache() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(SCHEMA)
            version = self._meta(db).get("schema_version")
            if version is not None and int(version) != SCHEMA_VERSION:
                for table in CACHE_TABLES:
                    db.execute(f"DROP TABLE IF EXISTS {table}")
                db.executescript(SCHEMA)
            db.commit()

    @contextmanager
    def _cache(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.cache_path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=15000")
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def _source(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.source_path.as_uri() + "?mode=ro", uri=True, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        try:
            yield db
        finally:
            db.close()

    @staticmethod
    def _meta(db: sqlite3.Connection) -> dict[str, Any]:
        return {row[0]: json.loads(row[1]) for row in db.execute("SELECT key,value FROM metadata")}

    @staticmethod
    def _set_meta(db: sqlite3.Connection, values: dict[str, Any]) -> None:
        db.executemany("INSERT OR REPLACE INTO metadata VALUES (?,?)", [(key, _json(value)) for key, value in values.items()])

    @staticmethod
    def _reset(db: sqlite3.Connection) -> None:
        for table in CACHE_TABLES:
            db.execute(f"DELETE FROM {table}")

    def _source_identity(self) -> dict[str, Any]:
        stat = self.source_path.stat()
        return {"path": str(self.source_path), "device": stat.st_dev, "inode": stat.st_ino}

    @staticmethod
    def _event_identity(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    @staticmethod
    def _artifact(source: sqlite3.Connection, artifact_id: str | None,
                  allowed: set[str] | frozenset[str] = ARTIFACT_KINDS) -> dict[str, Any]:
        if not artifact_id:
            return {}
        # Check the kind without fetching its body. Evaluator/case/recovery bodies
        # can never cross this boundary, even through a forged public reference.
        meta = source.execute("SELECT kind FROM artifacts WHERE artifact_id=?", (artifact_id,)).fetchone()
        if not meta or meta[0] not in allowed or meta[0] not in ARTIFACT_KINDS:
            return {}
        row = source.execute("SELECT body FROM artifacts WHERE artifact_id=? AND kind=?", (artifact_id, meta[0])).fetchone()
        if not row:
            return {}
        envelope = json.loads(row[0])
        if envelope.get("kind") != meta[0] or envelope.get("visibility") == "evaluator_only":
            return {}
        payload = envelope.get("payload") or {}
        if payload.get("visibility") == "evaluator_only" or payload.get("evaluator_only"):
            return {}
        return payload

    def status(self) -> dict[str, Any]:
        with self._cache() as db:
            meta = self._meta(db)
        ready = bool(meta.get("ready"))
        with self._state_lock:
            syncing, error = self._syncing, self._error
        return {"state": "error" if error else "syncing" if syncing else "ready" if ready else "building",
                "ready": ready, "syncing": syncing, "updated_at": meta.get("updated_at"),
                "source_cursor": meta.get("cursor", 0), "source_event": meta.get("anchor"),
                "as_of": meta.get("source_as_of"), "freshness": "background_projection",
                "error": error, "schema_version": SCHEMA_VERSION}

    def sync(self) -> dict[str, Any]:
        """Atomically project committed public records and advance the durable watermark.

        rowid is used only with a checked event identity. Source replacement,
        truncation, restore or VACUUM that changes the anchor rebuilds the cache.
        The source snapshot and cache transaction cover the same complete batch.
        """
        with self._sync_lock:
            with self._state_lock:
                self._syncing, self._error = True, None
            try:
                with self._source() as source, self._cache() as db:
                    source.execute("BEGIN")
                    tail = source.execute("SELECT rowid,event_id,body_hash,stream_id,seq,recorded_at FROM events ORDER BY rowid DESC LIMIT 1").fetchone()
                    maximum = tail["rowid"] if tail else 0
                    identity = self._source_identity()
                    meta = self._meta(db)
                    cursor = int(meta.get("cursor", 0))
                    checkpoint = source.execute("SELECT rowid,event_id,body_hash,stream_id,seq,recorded_at FROM events WHERE rowid=?", (cursor,)).fetchone() if cursor else None
                    reset = (meta.get("source_identity") not in (None, identity)
                             or cursor > maximum or meta.get("anchor") != self._event_identity(checkpoint))
                    db.execute("BEGIN IMMEDIATE")
                    if reset:
                        self._reset(db)
                        cursor = 0
                    changed: set[str] = set()
                    progress: dict[str, dict[str, Any]] = {}
                    placeholders = ",".join("?" for _ in PUBLIC_EVENTS)
                    sql = (f"SELECT rowid,body FROM events WHERE rowid>? AND rowid<=? AND event_type IN ({placeholders}) "
                           "AND (substr(stream_id,1,5)='task_' OR substr(stream_id,1,4)='run_') ORDER BY rowid")
                    for row in source.execute(sql, (cursor, maximum, *PUBLIC_EVENTS)):
                        event = json.loads(row["body"])
                        if event.get("visibility") in ("evaluator_only", "private", "recovery"):
                            continue
                        task_id = self._project(db, source, row["rowid"], event)
                        if event["stream_id"].startswith("run_"):
                            self._collect_progress(db, progress, event)
                        if task_id:
                            changed.add(task_id)
                    if meta.get("ready") and meta.get("task_input_version") != 1:
                        for row in source.execute("SELECT rowid,body FROM events WHERE event_type='task.version_recorded' AND substr(stream_id,1,5)='task_' ORDER BY rowid"):
                            event = json.loads(row["body"])
                            if event.get("visibility", "default") == "default":
                                task_id = self._project(db, source, row["rowid"], event)
                                if task_id:
                                    changed.add(task_id)
                    for task_id in changed:
                        self._summarise(db, task_id)
                    db.executemany("INSERT OR REPLACE INTO run_progress VALUES (?,?)",
                                   [(run_id, _json(body)) for run_id, body in progress.items()])
                    self._set_meta(db, {"schema_version": SCHEMA_VERSION, "source_identity": identity,
                                        "cursor": maximum, "anchor": self._event_identity(tail),
                                        "source_as_of": tail["recorded_at"] if tail else None,
                                        "updated_at": _now(), "ready": True, "task_input_version": 1})
                    db.commit()
            except Exception as exc:
                with self._state_lock:
                    self._error = str(exc)
                raise
            finally:
                with self._state_lock:
                    self._syncing = False
        return self.status()

    @staticmethod
    def _collect_progress(db: sqlite3.Connection, updates: dict[str, dict[str, Any]], event: dict[str, Any]) -> None:
        run_id, kind = event["stream_id"], event["event_type"]
        if run_id not in updates:
            updates[run_id] = _record(db.execute("SELECT body FROM run_progress WHERE run_id=?", (run_id,)).fetchone())
        body = updates[run_id]
        payload = event.get("payload") or {}
        body.update(run_id=run_id, last_activity_at=event["recorded_at"])
        if kind.startswith("run.") and event.get("state_to"):
            body["state"] = event["state_to"]
        if event.get("progress"):
            raw = event["progress"]
            body["progress"] = {"completed": raw.get("completed"), "planned": raw.get("planned"),
                                "denominator_kind": raw.get("denominator_kind") or "unknown", "scope": raw.get("scope")}
        body.setdefault("progress", {"completed": None, "planned": None, "denominator_kind": "unknown"})
        if event.get("summary"):
            body["message"] = event["summary"]
        if event.get("budget"):
            body["budget"] = event["budget"]
        if kind in ("stage.opened", "step.started"):
            body["phase"] = payload.get("stage") or payload.get("step")
        if kind == "agent.started":
            body["active_actor"] = {"role": payload.get("role"), "model_id": payload.get("model_id"),
                                    "request_id": payload.get("request_id"), "started_at": event["recorded_at"]}
        elif kind == "agent.finished" and (body.get("active_actor") or {}).get("request_id") == payload.get("request_id"):
            body["active_actor"] = None
        if kind.startswith("run.") and event.get("state_to") in ("completed", "failed", "cancelled", "unresolved"):
            body["active_actor"] = None

    def _task_for(self, db: sqlite3.Connection, event: dict[str, Any]) -> str | None:
        stream, payload = event["stream_id"], event.get("payload") or {}
        if stream.startswith("task_"):
            return stream
        task_id = (event.get("ids") or {}).get("task_id") or payload.get("task_id")
        if task_id:
            return task_id
        row = db.execute("SELECT task_id FROM runs WHERE run_id=?", (stream,)).fetchone()
        return row[0] if row else None

    @staticmethod
    def _input(record: dict[str, Any], task_id: str) -> dict[str, Any]:
        original = record.get("original_user_input")
        if isinstance(original, dict) and original.get("objective"):
            fields = ("title", "objective", "targets", "constraints", "library_id", "source_task_id",
                      "evidence_mode", "evaluation_mode", "workers", "budget_usd", "reference_candidate")
            return {key: original[key] for key in fields if key in original}
        return {"title": record.get("title") or "", "objective": record.get("objective_text") or "",
                "targets": [entity.get("label") or entity.get("identifier") for entity in record.get("scope_entities") or []],
                "constraints": "\n".join(str(item.get("text") or "") for item in record.get("constraints") or []),
                "library_id": Path((record.get("candidate_universe") or {}).get("access_path") or "").name,
                "source_task_id": record.get("evidence_collection_source_task_id") or task_id,
                "evidence_mode": "existing_only", "evaluation_mode": "staged", "workers": 4, "budget_usd": 10}

    def _project(self, db: sqlite3.Connection, source: sqlite3.Connection, rowid: int,
                 event: dict[str, Any]) -> str | None:
        kind, stream, at = event["event_type"], event["stream_id"], event["recorded_at"]
        payload, task_id = event.get("payload") or {}, self._task_for(db, event)
        if not task_id:
            return None
        if kind == "task.version_recorded":
            record = self._artifact(source, payload.get("artifact_id"), {"task_context"})
            if not record:
                return task_id
            universe = record.get("candidate_universe") or {}
            count = universe.get("size_if_known")
            if count is None:
                count = len(universe.get("members") or record.get("seed_candidates") or [])
            objective = record.get("objective_text", "")
            # The compact task record excludes candidate member arrays and case inheritance.
            body = {"task_id": task_id, "title": record.get("title") or objective[:100],
                    "objective": objective, "objective_text": objective, "version": payload.get("version"),
                    "candidate_count": count, "mode": record.get("mode"), "group_id": record.get("group_id"),
                    "updated_at": at, "derived_from_task_id": record.get("derived_from_task_id")}
            body["input"] = self._input(record, task_id)
            db.execute("INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?,?,?)",
                       (task_id, body["title"], objective, payload.get("version"), at, count, _json(body)))
        elif kind == "run.created":
            binding = self._artifact(source, payload.get("binding_artifact_id"), {"run_binding"})
            fields = ("run_purpose", "chain_id", "continues_run_id", "continuation_kind", "rules@v",
                      "round_index", "operation", "evaluation_mode", "workflow_id", "budget_envelope", "source_inputs_artifact_id")
            body = {key: binding.get(key) for key in fields}
            body.update(run_id=stream, task_id=task_id, state=event.get("state_to"), started_at=at, updated_at=at)
            db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?)", (stream, task_id, body["state"], at, at, _json(body)))
            if body.get("operation") == "registered_reduction":
                manifest = self._artifact(source, body.get("source_inputs_artifact_id"), {"registered_reduction_inputs"})
                body.update(scope_known=bool(manifest), registered_input_count=len(manifest.get("registered_inputs") or []),
                            backlog_input_count=len(manifest.get("backlog_pool_refs") or []))
                db.executemany("INSERT OR IGNORE INTO run_pool_scope VALUES (?,?)",
                               [(stream, ref.split("@v")[0]) for ref in manifest.get("backlog_pool_refs") or []])
                db.execute("UPDATE runs SET body=? WHERE run_id=?", (_json(body), stream))
        elif kind.startswith("run.") and event.get("state_to"):
            row = db.execute("SELECT body FROM runs WHERE run_id=?", (stream,)).fetchone()
            body = _record(row)
            body.update(run_id=stream, task_id=task_id, state=event["state_to"], updated_at=at,
                        termination_reason=event.get("termination_reason"))
            db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?)",
                       (stream, task_id, body["state"], body.get("started_at"), at, _json(body)))
            self._refresh_open_stages(db, stream, body["state"])
        elif kind in ("stage.opened", "stage.closed"):
            self._stage(db, source, rowid, task_id, event)
        elif kind == "criterion.version_proposed":
            self._version(db, source, rowid, task_id, event)
        elif kind == "criterion.change_recorded":
            self._change(db, source, rowid, task_id, event)
        elif kind == "criterion.version_approved":
            rules = self._artifact(source, payload.get("artifact_id"), {"rule_set"})
            entries = rules.get("entries") or []
            self._set_meta(db, {f"frozen:{task_id}": {"rule_set_ref": payload.get("rule_set_ref"),
                              "pending": payload.get("pending"), "entries": entries, "at": at,
                              "deferred": rules.get("deferred") or []}})
        elif kind == "leaderboard.snapshot_published":
            self._snapshot(db, source, rowid, task_id, event)
        elif kind == "candidate.assessed" and payload.get("candidate_ref"):
            db.execute("INSERT OR REPLACE INTO assessments VALUES (?,?,?,?,?,?,?,?,?)",
                       (stream, payload["candidate_ref"], payload.get("attribute_ref"), payload.get("rule_ref"), rowid,
                        event["seq"], payload.get("artifact_id"), payload.get("reason_artifact_id"), payload.get("verdict")))
        elif kind in ("evidence.admitted", "evidence.quarantined") and payload.get("claim_id"):
            pointer = {"claim_id": payload["claim_id"], "source_id": payload.get("source_ref"),
                       "candidate_ref": payload.get("candidate_ref"), "attribute_ref": payload.get("attribute_ref"),
                       "artifact_id": payload.get("artifact_id"), "body": None,
                       "admission_state": "admitted" if kind == "evidence.admitted" else "quarantined"}
            compact = self._claim(source, pointer)
            searchable = " ".join(str(compact.get(key) or "") for key in
                                  ("claim_id", "source_id", "candidate_ref", "attribute_ref", "title", "quote", "statement", "basis"))
            db.execute("INSERT OR REPLACE INTO claims VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (task_id, payload["claim_id"], stream, payload.get("candidate_ref"), payload.get("attribute_ref"),
                        payload.get("source_ref"), payload.get("artifact_id"), rowid,
                        pointer["admission_state"], _json(compact), searchable))
        elif kind == "human.review_requested":
            subject = payload.get("subject") or {}
            if subject.get("kind") == "rule_version":
                db.execute("INSERT OR REPLACE INTO reviews VALUES (?,?,?,?)", (task_id, payload["item_id"], subject.get("id"), payload.get("state") or "open"))
        elif kind in ("human.review_decided", "human.review_withdrawn", "decision.recorded"):
            item = payload.get("queue_item_ref") or payload.get("item_id")
            state = "decided" if kind == "human.review_decided" else "withdrawn" if kind == "human.review_withdrawn" else "machine_adjudicated"
            if item and (kind != "decision.recorded" or payload.get("adjudication_id")):
                db.execute("UPDATE reviews SET state=? WHERE task_id=? AND item_id=?", (state, task_id, item))
        return task_id

    @staticmethod
    def _live_count(db: sqlite3.Connection, task_id: str, run_id: str | None = None) -> int | None:
        run = _record(db.execute("SELECT body FROM runs WHERE run_id=?", (run_id,)).fetchone()) if run_id else {}
        sql = "SELECT count(*) FROM criteria_current c WHERE c.task_id=? AND c.kind='pool' AND c.state IN ('candidate','needs_refine','deferred_next_round','promoted')"
        values: list[Any] = [task_id]
        if run.get("operation") == "registered_reduction":
            if not run.get("scope_known"):
                return None
            sql += " AND EXISTS(SELECT 1 FROM run_pool_scope scope WHERE scope.run_id=? AND scope.criterion_id=c.criterion_id)"
            values.append(run_id)
        return db.execute(sql, values).fetchone()[0]

    @staticmethod
    def _open_stage_state(run_state: str | None) -> str:
        return {"paused": "paused", "cancelled": "interrupted", "failed": "failed", "unresolved": "unresolved",
                "completed": "unresolved", "queued": "running", "running": "running"}.get(run_state, "unresolved")

    def _refresh_open_stages(self, db: sqlite3.Connection, run_id: str, run_state: str) -> None:
        for row in db.execute("SELECT stage_id,body FROM stages WHERE run_id=? AND closed_row IS NULL", (run_id,)).fetchall():
            body = _record(row)
            body.update(state=self._open_stage_state(run_state), run_state=run_state, after_count=None, counts_known=False)
            db.execute("UPDATE stages SET body=? WHERE stage_id=?", (_json(body), row["stage_id"]))

    def _stage(self, db: sqlite3.Connection, source: sqlite3.Connection, rowid: int, task_id: str, event: dict[str, Any]) -> None:
        payload, run_id = event["payload"], event["stream_id"]
        name, iteration = payload.get("stage", "unknown"), payload.get("iteration")
        round_id = (event.get("ids") or {}).get("round_id", "")
        key = payload.get("stage_key") or f"{round_id}:{name}:{iteration}"
        stage_id = f"{run_id}:{key}"
        old = db.execute("SELECT * FROM stages WHERE stage_id=?", (stage_id,)).fetchone()
        body = _record(old)
        is_criteria_stage = name.split(":")[0] in CRITERIA_STAGES
        run = _record(db.execute("SELECT body FROM runs WHERE run_id=?", (run_id,)).fetchone())
        basis = payload.get("count_basis") or body.get("count_basis") or "working_proposals"
        body.update(stage_id=stage_id, run_id=run_id, stage=name, iteration=iteration,
                    count_basis=basis, counts_basis=basis if is_criteria_stage or payload.get("count_basis") else "not_a_criteria_stage")
        opened, closed = old["opened_row"] if old else None, old["closed_row"] if old else None
        if event["event_type"] == "stage.opened":
            opened = rowid
            body.update(state="running", started_at=event["recorded_at"], finished_at=None,
                        before_count=payload.get("before_count", self._live_count(db, task_id, run_id) if is_criteria_stage else None),
                        after_count=None, added=0, modified=0, merged=0, removed=0, pending=None,
                        counts_known=False)
        else:
            closed = rowid
            result = payload.get("result")
            if result is None and payload.get("result_artifact_id"):
                result = self._artifact(source, payload["result_artifact_id"], {"derivation_stage"}).get("result")
            if name == "mandated" and isinstance(result, list):
                refs = [{"rule_ref": item["rule_ref"], "attribute_ref": item["attribute_ref"]}
                        for item in result if isinstance(item, dict) and item.get("rule_ref") and item.get("attribute_ref")]
                body["mandated_result_refs"] = refs if len(refs) == len(result) else None
            counts = {key: value for key, value in (result or {}).items() if isinstance(value, (int, float, bool))} if isinstance(result, dict) else {}
            body.update(state=event.get("state_to") or "completed", finished_at=event["recorded_at"],
                        result_counts=counts, result_artifact_id=payload.get("result_artifact_id"),
                        after_count=payload.get("after_count", self._live_count(db, task_id, run_id) if is_criteria_stage else None))
            if payload.get("before_count") is not None:
                body["before_count"] = payload["before_count"]
            body.setdefault("before_count", None)
            body["counts_known"] = body.get("before_count") is not None and body.get("after_count") is not None
            if body["counts_known"]:
                body["pending"] = db.execute("SELECT count(*) FROM criteria_current WHERE task_id=? AND kind='pool' "
                                              "AND state IN ('candidate','needs_refine','deferred_next_round')", (task_id,)).fetchone()[0]
        db.execute("INSERT OR REPLACE INTO stages VALUES (?,?,?,?,?,?,?,?)",
                   (stage_id, task_id, run_id, name, iteration, opened, closed, _json(body)))

    @staticmethod
    def _summary(criterion_id: str, version: int, attribute: dict[str, Any], rule: dict[str, Any],
                 state: str = "registered", **extra: Any) -> dict[str, Any]:
        claims = attribute.get("supporting_claim_refs") or []
        return {"criterion_id": criterion_id, "version": version, "name": attribute.get("name") or criterion_id,
                "definition": attribute.get("definition"), "state": state, "role": rule.get("rule_kind") or "unassigned",
                "unit": attribute.get("unit"), "direction": attribute.get("direction"), "cutoff": rule.get("cutoff"),
                "evidence_count": len(claims), "parents": [], "children": [], **extra}

    @staticmethod
    def _put_criterion(db: sqlite3.Connection, task_id: str, body: dict[str, Any], kind: str, rowid: int,
                       artifact_id: str | None, *, table: str = "criteria_current") -> None:
        db.execute(f"INSERT OR REPLACE INTO {table} VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (task_id, body["criterion_id"], body.get("version"), body.get("state"), body.get("role"),
                    body.get("name"), kind, rowid, artifact_id, _json(body)))

    def _version(self, db: sqlite3.Connection, source: sqlite3.Connection, rowid: int, task_id: str, event: dict[str, Any]) -> None:
        payload = event["payload"]
        kind, base, version = payload.get("kind"), payload.get("id"), payload.get("version", 1)
        if kind not in ("attribute", "rule") or not base:
            return
        ref = f"{base}@v{version}"
        record = self._artifact(source, payload.get("artifact_id"), {kind})
        if not record:
            return
        db.execute("INSERT OR REPLACE INTO criterion_versions VALUES (?,?,?,?,?,?,?,?)",
                   (task_id, ref, kind, base, version, payload.get("artifact_id"), rowid, _json(record)))
        if kind == "attribute":
            old = db.execute("SELECT * FROM criteria_current WHERE task_id=? AND criterion_id=?", (task_id, base)).fetchone()
            body = self._summary(base, version, record, {}, attribute_ref=ref, **({"rule_ref": _record(old).get("rule_ref")} if old else {}))
            self._put_criterion(db, task_id, body, "registry", rowid, payload.get("artifact_id"))
            db.execute("INSERT OR REPLACE INTO criterion_aliases VALUES (?,?,?)", (task_id, ref, base))
        else:
            db.execute("INSERT OR REPLACE INTO registry_rules VALUES (?,?,?,?,?,?)", (task_id, base, ref, record.get("attribute_ref"), payload.get("artifact_id"), _json(record)))
            attribute_ref = record.get("attribute_ref")
            alias = db.execute("SELECT criterion_id FROM criterion_aliases WHERE task_id=? AND alias=?", (task_id, attribute_ref)).fetchone()
            if alias:
                current = db.execute("SELECT * FROM criteria_current WHERE task_id=? AND criterion_id=?", (task_id, alias[0])).fetchone()
                if current:
                    body = _record(current)
                    body.update(rule_ref=ref, role=record.get("rule_kind") or "unassigned", cutoff=record.get("cutoff"))
                    self._put_criterion(db, task_id, body, current["kind"], rowid, current["artifact_id"])
                    db.execute("INSERT OR REPLACE INTO criterion_aliases VALUES (?,?,?)", (task_id, ref, alias[0]))
        alias = db.execute("SELECT criterion_id FROM criterion_aliases WHERE task_id=? AND alias=?", (task_id, ref)).fetchone()
        if alias:
            current = db.execute("SELECT body FROM criteria_current WHERE task_id=? AND criterion_id=?", (task_id, alias[0])).fetchone()
            history = {"id": event["event_id"], "version": version, "criterion_id": alias[0],
                       "stage": None, "iteration": None, "operation": "register" if version == 1 else "revise",
                       "before": _record(old) if kind == "attribute" and old else None, "after": _record(current),
                       "reason": record.get("rationale"), "actor": event.get("actor"), "at": event["recorded_at"],
                       "sources": record.get("supporting_claim_refs") or [], "artifact_id": payload.get("artifact_id"),
                       "ref": ref, "kind": kind}
            db.execute("INSERT OR REPLACE INTO criterion_changes VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (rowid, task_id, alias[0], version, None, None, None, history["operation"], event["recorded_at"], _json(history)))

    def _change(self, db: sqlite3.Connection, source: sqlite3.Connection, rowid: int, task_id: str, event: dict[str, Any]) -> None:
        change = event["payload"]
        if change.get("collapse"):
            if change.get("state") == "merged_away":
                for ref in change.get("targets_in") or []:
                    db.execute("INSERT OR REPLACE INTO registry_collapses VALUES (?,?,?,0)", (task_id, change.get("collapse_id"), ref))
            if change.get("withdrew_collapse_id"):
                db.execute("UPDATE registry_collapses SET withdrawn=1 WHERE task_id=? AND collapse_id=?", (task_id, change["withdrew_collapse_id"]))
        if change.get("registry") and change.get("rule_ref"):
            db.execute("INSERT OR REPLACE INTO registry_transitions VALUES (?,?,?)", (task_id, change["rule_ref"], change.get("registry_state")))
        if not change.get("pool") and not change.get("registry") and not change.get("collapse"):
            return
        if not change.get("pool"):
            # Registry transitions never change the task's pool fold. In
            # particular retiring a prior rule version cannot retire a newer
            # promoted lineage merely because an alias names the same attribute.
            ref = change.get("attribute_ref") or change.get("rule_ref") or change.get("criterion_id") or ""
            identity = ref.split("@v")[0]
            version = change.get("version") or (int(ref.rsplit("@v", 1)[1]) if "@v" in ref else None)
            history = {"id": change.get("change_id") or event["event_id"], "criterion_id": identity,
                       "version": version, "stage": change.get("stage"), "iteration": change.get("iteration"),
                       "operation": change.get("operation"), "before": None,
                       "after": {"criterion_id": identity, "version": version,
                                 "state": change.get("registry_state") or change.get("state"),
                                 "attribute_ref": change.get("attribute_ref"), "rule_ref": change.get("rule_ref")},
                       "reason": change.get("reason_text"), "actor": event.get("actor"), "at": event["recorded_at"],
                       "sources": change.get("source_refs") or [], "targets_in": change.get("targets_in") or [],
                       "targets_out": change.get("targets_out") or [], "collapse_id": change.get("collapse_id"),
                       "correction_id": change.get("correction_id")}
            db.execute("INSERT OR REPLACE INTO criterion_changes VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (rowid, task_id, identity, version, None, change.get("reduction_run_id") or change.get("source_reduction_run_id"),
                        change.get("stage"), change.get("operation"), event["recorded_at"], _json(history)))
            return
        criterion_id = change.get("criterion_id")
        if not criterion_id:
            ref = change.get("attribute_ref") or change.get("rule_ref")
            alias = db.execute("SELECT criterion_id FROM criterion_aliases WHERE task_id=? AND alias=?", (task_id, ref)).fetchone()
            criterion_id = alias[0] if alias else (ref or "").split("@v")[0]
        if not criterion_id:
            return
        old = db.execute("SELECT * FROM criteria_current WHERE task_id=? AND criterion_id=?", (task_id, criterion_id)).fetchone()
        before = _record(old) or None
        item = self._artifact(source, change.get("artifact_id"), {"criterion_candidate"})
        if item:
            body = self._summary(criterion_id, change.get("version", 1), item.get("attribute") or {}, item.get("rule") or {},
                                 change.get("state") or "candidate", evidence_count=len(item.get("supporting_claim_ids") or []))
            body["source_registry"] = item.get("source_registry") or []
            if before:
                for key in ("parents", "children", "attribute_ref", "rule_ref"):
                    if before.get(key):
                        body[key] = before[key]
        else:
            body = dict(before or {"criterion_id": criterion_id, "name": criterion_id, "parents": [], "children": [], "role": "unassigned"})
            body.update(version=change.get("version", body.get("version", 1)), state=change.get("state") or change.get("registry_state") or body.get("state"))
        operation = change.get("operation")
        if operation in ("merge", "consolidate"):
            key, values = ("children", change.get("targets_out") or []) if body.get("state") == "merged_away" else ("parents", change.get("targets_in") or [])
            body[key] = list(dict.fromkeys((body.get(key) or []) + values))
        run_id = change.get("round_run_id") or change.get("reduction_run_id") or (event.get("ids") or {}).get("run_id")
        if change.get("pool") and run_id:
            db.execute("INSERT OR IGNORE INTO run_pool_scope VALUES (?,?)", (run_id, criterion_id))
        stage = db.execute("SELECT * FROM stages WHERE task_id=? AND run_id=? AND (stage=? OR stage LIKE ?) AND iteration IS ? "
                           "AND opened_row IS NOT NULL AND closed_row IS NULL ORDER BY opened_row DESC LIMIT 1",
                           (task_id, run_id, change.get("stage"), str(change.get("stage")) + ":%", change.get("iteration"))).fetchone() if run_id else None
        stage_id = stage["stage_id"] if stage else None
        body.update(stage=change.get("stage"), iteration=change.get("iteration"), reason=change.get("reason_text"),
                    stage_id=stage_id, operation=operation)
        promoted = change.get("promoted_as") or {}
        body.update(promoted)
        for alias in (f"{criterion_id}@v{body.get('version', 1)}", promoted.get("attribute_ref"), promoted.get("rule_ref")):
            if alias:
                db.execute("INSERT OR REPLACE INTO criterion_aliases VALUES (?,?,?)", (task_id, alias, criterion_id))
        # Registered attributes linked to a pool lineage are represented once.
        if promoted.get("attribute_ref"):
            base = promoted["attribute_ref"].split("@v")[0]
            if base != criterion_id:
                db.execute("DELETE FROM criteria_current WHERE task_id=? AND criterion_id=? AND kind='registry'", (task_id, base))
                db.execute("UPDATE criterion_changes SET criterion_id=? WHERE task_id=? AND criterion_id=?", (criterion_id, task_id, base))
                db.execute("UPDATE criterion_aliases SET criterion_id=? WHERE task_id=? AND criterion_id=?", (criterion_id, task_id, base))
                db.execute("INSERT OR REPLACE INTO criterion_aliases VALUES (?,?,?)", (task_id, base, criterion_id))
        artifact_id = change.get("artifact_id") or (old["artifact_id"] if old else None)
        self._put_criterion(db, task_id, body, "pool" if change.get("pool") else (old["kind"] if old else "registry"), rowid, artifact_id)
        history = {"id": change.get("change_id") or event["event_id"], "version": body.get("version"), "stage": change.get("stage"),
                   "stage_id": stage_id, "iteration": change.get("iteration"), "operation": operation,
                   "before": before, "after": body, "reason": change.get("reason_text"), "actor": event.get("actor"),
                   "at": event["recorded_at"], "sources": change.get("source_refs") or [],
                   "artifact_id": artifact_id, "targets_in": change.get("targets_in") or [],
                   "targets_out": change.get("targets_out") or []}
        db.execute("INSERT OR REPLACE INTO criterion_changes VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (rowid, task_id, criterion_id, body.get("version"), stage_id, run_id, change.get("stage"),
                    operation, event["recorded_at"], _json(history)))
        if stage:
            stats = _record(stage)
            counter = "added" if operation == "add" else "merged" if operation in ("merge", "consolidate") else "removed" if body.get("state") in ("withdrawn", "filtered_out") else "modified"
            if operation in ("merge", "consolidate") and body.get("state") != "merged_away":
                counter = "added" if before is None else "modified"
            stats[counter] = stats.get(counter, 0) + 1
            db.execute("UPDATE stages SET body=? WHERE stage_id=?", (_json(stats), stage_id))

    @staticmethod
    def _qualification(entry: dict[str, Any], legacy: bool) -> str:
        explicit = entry.get("qualification")
        if explicit in ("qualified", "pending", "rejected", "unassessed") and not legacy:
            return explicit
        if not legacy:
            qualification = explicit if isinstance(explicit, dict) else {}
            state = entry.get("qualification_state") or qualification.get("state")
            if state in ("qualified", "rejected", "unassessed"):
                return state
            if state in ("not_ready", "pending", "insufficient_evidence", "unknown"):
                return "pending"
            if entry.get("qualified") is True or qualification.get("qualified") is True:
                return "qualified"
        if entry.get("state") == "rejected" or (entry.get("n_fail_hard") or 0) > 0:
            return "rejected"
        if entry.get("state") == "unassessed":
            return "unassessed"
        # A legacy ranking does not assert eligibility even when a row has a rank.
        if legacy:
            return "pending" if entry.get("per_criterion_refs") or entry.get("verdicts") else "unassessed"
        if entry.get("clears_hard_rules") is True and entry.get("clears_mandated_criteria") is not False:
            return "qualified"
        return "pending"

    def _snapshot(self, db: sqlite3.Connection, source: sqlite3.Connection, rowid: int, task_id: str, event: dict[str, Any]) -> None:
        payload = event["payload"]
        snapshot = self._artifact(source, payload.get("artifact_id"), {"leaderboard_snapshot"})
        if not snapshot:
            return
        snapshot_id = snapshot.get("snapshot_id") or payload.get("snapshot_id")
        entries = snapshot.get("candidate_entries") or []
        legacy = not (snapshot.get("qualification_policy") not in (None, "legacy") or snapshot.get("qualification_first")
                      or any("qualification" in entry for entry in entries))
        counts = dict.fromkeys(("qualified", "pending", "rejected", "unassessed"), 0)
        rows = []
        for ordinal, entry in enumerate(entries):
            qualification = self._qualification(entry, legacy)
            counts[qualification] += 1
            bases = entry.get("measured_vs_predicted_counts") or {}
            label = next((value for value in entry.get("identity_labels") or [] if value), entry["candidate_ref"])
            qualification_record = entry.get("qualification") if isinstance(entry.get("qualification"), dict) else {}
            total = entry.get("hard_total", entry.get("n_hard", qualification_record.get("hard_total", qualification_record.get("applicable_hard_count"))))
            failed, unknown = entry.get("n_fail_hard"), entry.get("n_unknown_hard")
            passed = entry.get("hard_passed", qualification_record.get("hard_passed", qualification_record.get("verified_hard_count")))
            if passed is None and total is not None and failed is not None and unknown is not None:
                passed = total - failed - unknown
            body = {"candidate_ref": entry["candidate_ref"], "label": label, "qualification": qualification,
                    "position": entry.get("position"), "score": entry.get("preference_score", entry.get("score")),
                    "hard_passed": passed, "hard_total": total, "preference_coverage": entry.get("preference_coverage"),
                    "evidence_coverage": entry.get("coverage"), "reason": entry.get("qualification_reason") or qualification_record.get("reason") or entry.get("state_reason"),
                    "state": entry.get("state"), "measured_count": bases.get("measured"), "predicted_count": bases.get("predicted"),
                    "mandated_coverage": entry.get("mandated_coverage"), "rank_note": entry.get("rank_note")}
            rows.append((snapshot_id, entry["candidate_ref"], qualification, entry.get("position"), ordinal, label, _json(body), _json(entry)))
        db.execute("DELETE FROM candidate_rows WHERE snapshot_id=?", (snapshot_id,))
        db.executemany("INSERT INTO candidate_rows VALUES (?,?,?,?,?,?,?,?)", rows)
        fields = ("snapshot_id", "task_id", "run_id", "published_at", "evaluation_mode", "qualification_policy",
                  "qualification_first", "readiness", "rules@v", "evidence_snapshot_id", "leaderboard_id",
                  "parent_snapshot_id", "result_kind", "abstention_reason", "no_recommendation", "all_pass_count")
        body = {key: snapshot.get(key) for key in fields}
        reporting = snapshot.get("reporting_tuple") or {}
        body["reporting_tuple"] = {key: reporting.get(key) for key in ("sweep_completeness", "coverage_fraction", "admitted_n", "ranking_coverage_floor", "mandated_coverage_floor",
                                  "normalization_population", "recorded_cell_n", "assessed_cell_n", "assessment_completeness",
                                  "skipped_after_rejection_n", "missing_or_conflicted_n", "error_n", "qualified_n", "direct_coverage_fraction")}
        body.update(snapshot_id=snapshot_id, task_id=task_id, run_id=snapshot.get("run_id") or event["stream_id"],
                    published_at=snapshot.get("published_at") or event["recorded_at"], candidate_count=len(rows),
                    counts={**counts, "total": len(rows)}, legacy_rank_only=legacy,
                    evaluation_mode=snapshot.get("evaluation_mode") or "historical", published_row=rowid,
                    label=snapshot.get("label") or snapshot_id)
        db.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?)",
                   (snapshot_id, task_id, body["run_id"], rowid, body["published_at"], payload.get("artifact_id"), _json(body)))

    def _summarise(self, db: sqlite3.Connection, task_id: str) -> None:
        registry = list(db.execute("SELECT * FROM registry_rules WHERE task_id=?", (task_id,)))
        transitions = dict(db.execute("SELECT ref,state FROM registry_transitions WHERE task_id=?", (task_id,)))
        collapsed = {row[0] for row in db.execute("SELECT attribute_ref FROM registry_collapses WHERE task_id=? AND withdrawn=0", (task_id,))}
        active_registry = [row for row in registry if transitions.get(row["ref"]) != "retired" and row["attribute_ref"] not in collapsed]
        active_refs = {row["ref"] for row in active_registry}
        pending_rows = [row[0] for row in db.execute("SELECT subject_ref FROM reviews WHERE task_id=? AND state IN ('open','in_review')", (task_id,))]
        pending_refs = set(pending_rows)
        reduction = next((run for row in db.execute("SELECT body FROM runs WHERE task_id=? ORDER BY started_at DESC", (task_id,))
                          if (run := _record(row)).get("operation") == "registered_reduction"), None)
        scope = {row[0] for row in db.execute("SELECT criterion_id FROM run_pool_scope WHERE run_id=?", (reduction["run_id"],))} if reduction else None
        pools = list(db.execute("SELECT * FROM criteria_current WHERE task_id=? AND kind='pool'", (task_id,)))
        unresolved = [row for row in pools if row["state"] in ("candidate", "needs_refine", "deferred_next_round")
                      and (scope is None or row["criterion_id"] in scope)]
        additional = []
        for row in unresolved:
            sources = _record(row).get("source_registry") or []
            if not (len(sources) == 1 and sources[0].get("rule_ref") in active_refs):
                additional.append(row)
        additional_ids = {row["criterion_id"] for row in additional}
        roles: dict[str, int] = {}
        task_required_count = 0
        for row in active_registry:
            role = _record(row).get("rule_kind") or "unassigned"
            roles[role] = roles.get(role, 0) + 1
        db.execute("DELETE FROM criteria_listing WHERE task_id=?", (task_id,))
        for row in registry:
            rule = _record(row)
            attribute_row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=?", (task_id, row["attribute_ref"])).fetchone()
            attribute = _record(attribute_row)
            identity = (row["attribute_ref"] or row["base_id"]).split("@v")[0]
            state = "active" if row["ref"] in active_refs else "merged" if row["attribute_ref"] in collapsed else "retired"
            body = self._summary(identity, attribute.get("version") or (attribute_row["version"] if attribute_row else 1), attribute, rule, state,
                                 attribute_ref=row["attribute_ref"], rule_ref=row["ref"], registered=True,
                                 pending_review=row["ref"] in pending_refs, current=row["ref"] in active_refs,
                                 task_required=is_task_mandated(attribute))
            if row["ref"] in active_refs and body["task_required"]:
                task_required_count += 1
            alias = db.execute("SELECT criterion_id FROM criterion_aliases WHERE task_id=? AND alias=?", (task_id, row["ref"])).fetchone()
            if alias:
                origin = _record(db.execute("SELECT body FROM criteria_current WHERE task_id=? AND criterion_id=?", (task_id, alias[0])).fetchone())
                for key in ("parents", "children", "stage", "iteration", "stage_id", "reason"):
                    if origin.get(key) is not None:
                        body[key] = origin[key]
            self._put_criterion(db, task_id, body, "registry", attribute_row["source_row"] if attribute_row else 0,
                                attribute_row["artifact_id"] if attribute_row else None, table="criteria_listing")
        for row in pools:
            raw = _record(row)
            sources = raw.get("source_registry") or []
            if row["state"] == "promoted" or (len(sources) == 1 and sources[0].get("rule_ref") in active_refs):
                continue
            body = dict(raw, raw_state=row["state"], registered=False, current=row["criterion_id"] in additional_ids)
            body["state"] = "pending" if body["current"] else "merged" if row["state"] == "merged_away" else "retired" if row["state"] in ("withdrawn", "filtered_out") else "historical"
            self._put_criterion(db, task_id, body, "pool", row["updated_row"], row["artifact_id"], table="criteria_listing")
        # A pre-registration task still exposes its actual current generated pool.
        if not registry:
            for row in additional:
                role = row["role"] or "unassigned"
                roles[role] = roles.get(role, 0) + 1
        task = db.execute("SELECT candidate_count FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        frozen = self._meta(db).get(f"frozen:{task_id}") or {}
        scoring_refs = {entry.get("rule_ref") for entry in frozen.get("entries") or []} & active_refs
        deferred_refs = {entry.get("rule_ref") for entry in frozen.get("deferred") or [] if entry.get("scope", "rule") == "rule"} & active_refs
        body = {"candidate_count": task[0] if task else None,
                "criteria_count": len(active_registry) if registry else len(additional),
                "hard_count": roles.get("hard_exclusion", 0), "preference_count": roles.get("preference", 0),
                "task_required_count": task_required_count,
                "pending_count": len(pending_refs & active_refs), "pending_review_count": len(pending_refs & active_refs),
                "historical_pending_review_count": sum(ref not in active_refs for ref in pending_rows),
                "active_registered_count": len(active_registry), "historical_registered_count": len(registry),
                "retired_latest_count": len(registry) - len(active_registry),
                "additional_unregistered_active_count": len(additional), "unresolved_pool_count": len(unresolved),
                "total_active_count": len(active_registry) + len(additional),
                "scoring_count": len(scoring_refs), "scoring_in_latest_frozen_set_count": len(scoring_refs),
                "deferred_count": len(deferred_refs), "registered_pending_count": len(active_refs - scoring_refs - deferred_refs),
                "latest_frozen_rule_set_ref": frozen.get("rule_set_ref"), "reduction_run_id": reduction.get("run_id") if reduction else None,
                "historical_criteria_count": db.execute("SELECT count(*) FROM criteria_listing WHERE task_id=?", (task_id,)).fetchone()[0],
                "run_count": db.execute("SELECT count(*) FROM runs WHERE task_id=?", (task_id,)).fetchone()[0],
                "claim_count": db.execute("SELECT count(DISTINCT claim_id) FROM claims WHERE task_id=? AND admission_state='admitted'", (task_id,)).fetchone()[0]}
        db.execute("INSERT OR REPLACE INTO task_summaries VALUES (?,?)", (task_id, _json(body)))

    def _ready(self, db: sqlite3.Connection) -> dict[str, Any]:
        meta = self._meta(db)
        if not meta.get("ready"):
            raise ProjectionNotReady("The workbench index is being prepared. Source records remain available.")
        return meta

    @staticmethod
    def _task(db: sqlite3.Connection, task_id: str) -> dict[str, Any]:
        row = db.execute("SELECT body FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            raise KeyError(f"no task {task_id}")
        return _record(row)

    def _task_row(self, db: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        body = _record(row)
        summary = _record(db.execute("SELECT body FROM task_summaries WHERE task_id=?", (body["task_id"],)).fetchone())
        latest = db.execute("SELECT snapshot_id FROM snapshots WHERE task_id=? ORDER BY published_row DESC LIMIT 1", (body["task_id"],)).fetchone()
        run = db.execute("SELECT body FROM runs WHERE task_id=? ORDER BY updated_at DESC LIMIT 1", (body["task_id"],)).fetchone()
        body.update(criteria_count=summary.get("criteria_count"), latest_snapshot_id=latest[0] if latest else None,
                    state=_record(run).get("state"), workflow_id=_record(run).get("workflow_id"), claim_count=summary.get("claim_count"))
        return body

    def tasks(self) -> list[dict[str, Any]]:
        with self._cache() as db:
            self._ready(db)
            return [self._task_row(db, row) for row in db.execute("SELECT body FROM tasks ORDER BY updated_at DESC,task_id")]

    def task_summary(self, task_id: str) -> dict[str, Any]:
        with self._cache() as db:
            self._ready(db)
            self._task(db, task_id)
            return _record(db.execute("SELECT body FROM task_summaries WHERE task_id=?", (task_id,)).fetchone())

    def task_input(self, task_id: str) -> dict[str, Any]:
        with self._cache() as db:
            self._ready(db)
            return self._task(db, task_id).get("input") or {}

    def run_progress(self, run_id: str) -> dict[str, Any]:
        with self._cache() as db:
            self._ready(db)
            row = db.execute("SELECT body FROM run_progress WHERE run_id=?", (run_id,)).fetchone()
            if not row:
                raise KeyError(f"no run {run_id}")
            return _record(row)

    def overview(self, task_id: str) -> dict[str, Any]:
        with self._cache() as db:
            meta = self._ready(db)
            row = db.execute("SELECT body FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            if not row:
                raise KeyError(f"no task {task_id}")
            task = self._task_row(db, row)
            summary = _record(db.execute("SELECT body FROM task_summaries WHERE task_id=?", (task_id,)).fetchone())
            changes = [_record(row) for row in db.execute("SELECT body FROM criterion_changes WHERE task_id=? ORDER BY source_row DESC LIMIT 20", (task_id,))]
            runs = [_record(row) for row in db.execute("SELECT body FROM runs WHERE task_id=? ORDER BY updated_at DESC", (task_id,))]
            stages = self._stages(db, task_id)
            snapshots = [_record(row) for row in db.execute("SELECT body FROM snapshots WHERE task_id=? ORDER BY published_row DESC", (task_id,))]
            return {"task": task, "input": task.get("input") or {}, "summary": summary, "stages": stages, "snapshots": snapshots,
                    "recent_changes": changes, "runs": runs, "as_of": meta.get("source_as_of"),
                    "projection": {"updated_at": meta.get("updated_at"), "source_cursor": meta.get("cursor")}}

    @staticmethod
    def _mandated_added(db: sqlite3.Connection, task_id: str, opened: int | None,
                        closed: int | None, body: dict[str, Any]) -> None:
        """Count template-created rule bindings, not attribute/rule pairs twice."""
        body.update(added=None, added_count_basis="unavailable_stage_bounds", added_event_refs=[])
        if opened is None or closed is None:
            return
        expected = body.get("mandated_result_refs")
        expected_pairs = {(item["rule_ref"], item["attribute_ref"]) for item in expected} if expected is not None else None
        if expected is not None and len(expected_pairs) != len(expected):
            body["added_count_basis"] = "ambiguous_recorded_result"
            return
        rows = db.execute("SELECT r.ref,r.source_row,r.artifact_id,r.body,a.body AS attribute_body,ch.body AS creation_body "
            "FROM criterion_versions r LEFT JOIN criterion_versions a ON a.task_id=r.task_id "
            "AND a.ref=json_extract(r.body,'$.attribute_ref') AND a.kind='attribute' "
            "LEFT JOIN criterion_changes ch ON ch.source_row=r.source_row AND ch.task_id=r.task_id "
            "WHERE r.task_id=? AND r.kind='rule' AND r.source_row>? AND r.source_row<? ORDER BY r.source_row",
            (task_id, opened, closed)).fetchall()
        verified = []
        for row in rows:
            rule = _record(row)
            pair = row["ref"], rule.get("attribute_ref")
            if expected_pairs is not None and pair not in expected_pairs:
                continue
            attribute = json.loads(row["attribute_body"]) if row["attribute_body"] else {}
            creation = json.loads(row["creation_body"]) if row["creation_body"] else {}
            origin = attribute.get("derived_from") or {}
            who = creation.get("actor") or {}
            if (not is_task_mandated(attribute) or str(origin.get("task_context", "")).split("@v")[0] != task_id
                    or who.get("kind") != "system" or who.get("id") != "objective-criteria"
                    or creation.get("kind") != "rule" or creation.get("ref") != row["ref"] or not creation.get("id")):
                body["added_count_basis"] = "unverified_task_binding_creation"
                return
            verified.append({"rule_ref": row["ref"], "attribute_ref": pair[1], "event_id": creation["id"],
                             "source_row": row["source_row"], "rule_artifact_id": row["artifact_id"],
                             "source_field": origin.get("field")})
        pairs = {(item["rule_ref"], item["attribute_ref"]) for item in verified}
        if expected_pairs is not None and pairs != expected_pairs:
            body["added_count_basis"] = "incomplete_recorded_result_creations"
            return
        if not verified and expected_pairs is None:
            body["added_count_basis"] = "no_creation_proof"
            return
        body.update(added=len(verified), added_event_refs=verified,
                    added_count_basis="recorded_result_and_task_binding_events" if expected_pairs is not None
                                      else "task_binding_events_between_stage_boundaries")

    @staticmethod
    def _stages(db: sqlite3.Connection, task_id: str) -> list[dict[str, Any]]:
        rows = db.execute("SELECT s.body,s.opened_row,s.closed_row,r.state AS run_state FROM stages s LEFT JOIN runs r ON r.run_id=s.run_id "
                          "WHERE s.task_id=? ORDER BY coalesce(s.opened_row,s.closed_row),s.stage_id", (task_id,))
        result = []
        for row in rows:
            body = _record(row)
            if row["closed_row"] is None:
                body.update(state=ReadModel._open_stage_state(row["run_state"]), run_state=row["run_state"],
                            after_count=None, counts_known=False)
            if body.get("stage") == "mandated":
                ReadModel._mandated_added(db, task_id, row["opened_row"], row["closed_row"], body)
            for key in ("before_count", "after_count", "added", "modified", "merged", "removed", "pending", "started_at", "finished_at"):
                body.setdefault(key, None)
            result.append(body)
        return result

    def stages(self, task_id: str) -> dict[str, Any]:
        with self._cache() as db:
            self._ready(db)
            self._task(db, task_id)
            return {"items": self._stages(db, task_id)}

    @staticmethod
    def _exact_criterion(db: sqlite3.Connection, task_id: str, wanted: str) -> dict[str, Any] | None:
        """Resolve saved references without following an alias to a newer version."""
        if wanted.startswith("change:"):
            change = db.execute("SELECT * FROM criterion_changes WHERE task_id=? AND json_extract(body,'$.id')=?",
                                (task_id, wanted[len("change:"):])).fetchone()
        else:
            version_row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=?", (task_id, wanted)).fetchone()
            if version_row:
                value = _record(version_row)
                is_rule = version_row["kind"] == "rule"
                attribute_ref = value.get("attribute_ref") if is_rule else wanted
                attr_row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=? AND kind='attribute'",
                                      (task_id, attribute_ref)).fetchone()
                if not attr_row:
                    return None
                attribute = _record(attr_row)
                field = "rule_ref" if is_rule else "attribute_ref"
                latest = _record(db.execute(f"SELECT body FROM criteria_listing WHERE task_id=? "
                                 f"AND json_extract(body,'$.{field}')=?", (task_id, wanted)).fetchone())
                current_row = db.execute("SELECT body FROM criteria_listing WHERE task_id=? AND json_extract(body,'$.current')=1 "
                    f"AND json_extract(body,'$.{field}') IN (SELECT ref FROM criterion_versions WHERE task_id=? AND base_id=? AND kind=?)",
                    (task_id, task_id, version_row["base_id"], version_row["kind"])).fetchone()
                current = _record(current_row)
                body = ReadModel._summary(wanted, attr_row["version"], attribute, value if is_rule else {},
                    latest.get("state") or "historical", attribute_ref=attribute_ref,
                    rule_ref=wanted if is_rule else None, registered=True,
                    current=bool(latest.get("current")), detail_ref=wanted,
                    historical_version=not is_rule or not bool(latest.get("current")),
                    current_ref=current.get("rule_ref") if current else None)
                return {"criterion_id": wanted, "version": attr_row["version"], "kind": "registry",
                        "artifact_id": attr_row["artifact_id"], "body": _json(body)}
            if "@v" not in wanted:
                return None
            base, version = wanted.rsplit("@v", 1)
            if not version.isdigit():
                return None
            change = db.execute("SELECT * FROM criterion_changes WHERE task_id=? AND criterion_id=? AND version=? "
                                "AND json_extract(body,'$.kind') IS NULL AND json_extract(body,'$.after.name') IS NOT NULL "
                                "ORDER BY source_row DESC LIMIT 1",
                                (task_id, base, int(version))).fetchone()
        if not change:
            return None
        history = _record(change)
        body = dict(history.get("after") or {})
        if not body:
            return None
        latest_row = db.execute("SELECT * FROM criteria_current WHERE task_id=? AND criterion_id=?",
                                (task_id, change["criterion_id"])).fetchone()
        earlier = not latest_row or latest_row["updated_row"] != change["source_row"]
        if not earlier:
            current = db.execute("SELECT body FROM criteria_listing WHERE task_id=? AND criterion_id=?",
                                 (task_id, change["criterion_id"])).fetchone()
            body = _record(current) or body
        current_pool = db.execute("SELECT 1 FROM criterion_changes WHERE source_row=? AND json_extract(body,'$.kind') IS NULL "
                                  "AND json_extract(body,'$.after.name') IS NOT NULL", (latest_row["updated_row"],)).fetchone() if latest_row else None
        body.update(detail_ref=wanted, historical_version=earlier,
                    current_ref=f"{change['criterion_id']}@v{latest_row['version']}" if earlier and current_pool else None)
        return {"criterion_id": change["criterion_id"], "version": body.get("version"), "kind": "pool",
                "artifact_id": history.get("artifact_id"), "body": _json(body)}

    @staticmethod
    def _frozen_criteria(db: sqlite3.Connection, task_id: str, frozen: dict[str, Any]) -> list[dict[str, Any]]:
        """Read exact enabled versions from the cache, including versions since revised."""
        rows = []
        for entry in frozen.get("entries") or []:
            ref = entry.get("rule_ref")
            rule_row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=? AND kind='rule'",
                                  (task_id, ref)).fetchone()
            rule = _record(rule_row)
            attribute_ref = entry.get("attribute_ref") or rule.get("attribute_ref")
            attr_row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=? AND kind='attribute'",
                                  (task_id, attribute_ref)).fetchone()
            if not rule_row or not attr_row:
                raise ProjectionNotReady("The prepared criterion version is not cached yet.")
            attribute = _record(attr_row)
            latest = _record(db.execute("SELECT body FROM criteria_listing WHERE task_id=? "
                                       "AND json_extract(body,'$.rule_ref')=?", (task_id, ref)).fetchone())
            body = ReadModel._summary(ref, attr_row["version"], attribute, rule, "in_evaluation",
                attribute_ref=attribute_ref, rule_ref=ref, registered=True,
                current=bool(latest.get("current")), pending_review=bool(latest.get("pending_review")),
                frozen_rule_set_ref=frozen.get("rule_set_ref"))
            version_info = ReadModel._exact_criterion(db, task_id, ref)
            detail = _record(version_info)
            body.update(detail_ref=ref, historical_version=detail.get("historical_version", False),
                        current_ref=detail.get("current_ref"))
            for key in ("parents", "children", "stage", "iteration", "stage_id", "reason"):
                if latest.get(key) is not None:
                    body[key] = latest[key]
            rows.append({"task_id": task_id, "criterion_id": ref, "version": attr_row["version"],
                         "kind": "registry", "artifact_id": attr_row["artifact_id"], "body": _json(body)})
        return rows

    def criteria(self, task_id: str, *, page: int = 1, page_size: int = PAGE_SIZE, q: str = "",
                 state: str = "", stage: str = "", cursor: str | None = None, **filters: Any) -> dict[str, Any]:
        if cursor:
            page = int(cursor)
        page, page_size, offset = _page(page, page_size)
        with self._cache() as db:
            meta = self._ready(db)
            self._task(db, task_id)
            frozen = self._meta(db).get(f"frozen:{task_id}")
            clauses, values = ["c.task_id=?"], [task_id]
            prefix, relation = "", "criteria_listing c"
            scope = "stage" if stage else "pending" if state == "pending" else "all"
            if stage:
                prefix = ("WITH selected AS (SELECT criterion_id,max(source_row) AS source_row FROM criterion_changes "
                          "WHERE task_id=? AND stage_id=? GROUP BY criterion_id), "
                          "stage_rows AS (SELECT ch.task_id,ch.criterion_id,json_set(json_extract(ch.body,'$.after'),'$.detail_ref','change:' || json_extract(ch.body,'$.id')) AS body,"
                          "json_extract(ch.body,'$.after.name') AS name,json_extract(ch.body,'$.after.state') AS state,"
                          "json_extract(ch.body,'$.after.role') AS role FROM criterion_changes ch JOIN selected s ON ch.source_row=s.source_row) ")
                relation = "stage_rows c"
                values = [task_id, stage, task_id]
            elif state == "working":
                scope = "frozen" if frozen is not None else "working"
                if frozen is not None:
                    rows = self._frozen_criteria(db, task_id, frozen)
                    prefix = ("WITH frozen_rows AS (SELECT ? AS task_id,json_extract(value,'$.criterion_id') AS criterion_id,"
                              "json_extract(value,'$.name') AS name,json_extract(value,'$.state') AS state,"
                              "json_extract(value,'$.role') AS role,value AS body FROM json_each(?)) ")
                    relation = "frozen_rows c"
                    values = [task_id, _json([_record(row) for row in rows]), task_id]
            if state and state != "all":
                if state in ("active", "working"):
                    if stage:
                        clauses.append("c.state IN ('candidate','needs_refine','deferred_next_round','promoted','active')")
                    elif state == "active" or frozen is None:
                        clauses.append("json_extract(c.body,'$.current')=1")
                elif state == "review":
                    clauses.append("json_extract(c.body,'$.current')=1 AND json_extract(c.body,'$.pending_review')=1")
                elif state == "pending":
                    if stage:
                        clauses.append("c.state IN ('candidate','needs_refine','deferred_next_round','pending')")
                    else:
                        reasons = ["coalesce(json_extract(c.body,'$.registered'),0)=0",
                                   "json_extract(c.body,'$.pending_review')=1"]
                        if frozen is not None:
                            reasons.append("NOT EXISTS (SELECT 1 FROM json_each(?) enabled WHERE enabled.value=json_extract(c.body,'$.rule_ref'))")
                            values.append(_json([entry["rule_ref"] for entry in frozen.get("entries") or [] if entry.get("rule_ref")]))
                        clauses.append("json_extract(c.body,'$.current')=1 AND (" + " OR ".join(reasons) + ")")
                elif state == "merged":
                    clauses.append("c.state IN ('merged','merged_away')")
                elif state == "retired":
                    clauses.append("c.state IN ('retired','withdrawn','filtered_out')")
                else:
                    clauses.append("c.state=?")
                    values.append(state)
            if q:
                clauses.append("(c.name LIKE ? ESCAPE '\\' OR c.criterion_id LIKE ? ESCAPE '\\' OR json_extract(c.body,'$.definition') LIKE ? ESCAPE '\\')")
                values.extend([_like(q)] * 3)
            if filters.get("role"):
                clauses.append("c.role=?")
                values.append(filters["role"])
            where = " AND ".join(clauses)
            total = db.execute(f"{prefix}SELECT count(*) FROM {relation} WHERE {where}", values).fetchone()[0]
            items = [_record(row) for row in db.execute(f"{prefix}SELECT c.body FROM {relation} WHERE {where} ORDER BY c.criterion_id LIMIT ? OFFSET ?", (*values, page_size, offset))]
            for item in items:
                if not item.get("detail_ref"):
                    identity = item["criterion_id"]
                    item["detail_ref"] = (f"{identity}@v{item['version']}" if identity.startswith("cri_") and "@v" not in identity
                                          else item.get("rule_ref") or item.get("attribute_ref") or identity)
            result = self._paged(items, total, page, page_size, meta)
            result["criteria_scope"] = scope
            if not stage and frozen is not None:
                result["rule_set_ref"] = frozen.get("rule_set_ref")
            return result

    @staticmethod
    def _paged(items: list[dict[str, Any]], total: int, page: int, page_size: int, meta: dict[str, Any]) -> dict[str, Any]:
        more = page * page_size < total
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "has_more": more, "next_cursor": str(page + 1) if more else None,
                "as_of": meta.get("source_as_of"), "updated_at": meta.get("updated_at")}

    @staticmethod
    def _resolve_criterion(db: sqlite3.Connection, task_id: str, wanted: str) -> sqlite3.Row | dict[str, Any]:
        if "@v" in wanted:
            frozen = ReadModel._meta(db).get(f"frozen:{task_id}")
            if frozen is not None and any(entry.get("rule_ref") == wanted for entry in frozen.get("entries") or []):
                return next(row for row in ReadModel._frozen_criteria(db, task_id, frozen) if row["criterion_id"] == wanted)
        if wanted.startswith("change:") or "@v" in wanted:
            exact = ReadModel._exact_criterion(db, task_id, wanted)
            if exact is None:
                raise KeyError(f"no saved criterion version {wanted} in {task_id}")
            return exact
        row = db.execute("SELECT * FROM criteria_listing WHERE task_id=? AND criterion_id=?", (task_id, wanted)).fetchone()
        if not row:
            row = db.execute("SELECT * FROM criteria_current WHERE task_id=? AND criterion_id=?", (task_id, wanted)).fetchone()
        if not row:
            row = db.execute("SELECT c.* FROM criteria_current c JOIN criterion_aliases a ON a.task_id=c.task_id "
                             "AND a.criterion_id=c.criterion_id WHERE a.task_id=? AND a.alias=?", (task_id, wanted)).fetchone()
        if not row:
            raise KeyError(f"no criterion {wanted} in {task_id}")
        return row

    @staticmethod
    def _lineage_node(db: sqlite3.Connection, task_id: str, ref: str,
                      value: dict[str, Any] | None = None) -> dict[str, Any]:
        """Read one saved version, without recursing into its lineage graph."""
        if value is None:
            try:
                value = _record(ReadModel._resolve_criterion(db, task_id, ref))
            except KeyError:
                return {"id": ref, "ref": ref, "missing": True}
        detail_ref = value.get("detail_ref") or value.get("rule_ref") or value.get("attribute_ref")
        if not detail_ref:
            identity = value.get("criterion_id") or ref
            detail_ref = (f"{identity}@v{value['version']}" if "@v" not in identity
                          and value.get("version") is not None else identity)
        return {"id": detail_ref, "ref": ref, "detail_ref": detail_ref,
                "criterion_id": value.get("criterion_id"), "name": value.get("name"),
                "version": value.get("version"), "definition": value.get("definition"),
                "state": value.get("state"), "missing": False}

    @staticmethod
    def _registered_version_history(db: sqlite3.Connection, task_id: str,
                                    refs: list[str | None]) -> list[dict[str, Any]]:
        """Follow immutable supersedes links, keeping attribute and rule records separate."""
        pending = [(ref, None) for ref in refs if ref]
        visited, history = set(), []
        while pending:
            ref, expected_kind = pending.pop()
            if ref in visited:
                continue
            visited.add(ref)
            row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=?",
                             (task_id, ref)).fetchone()
            if not row or (expected_kind is not None and row["kind"] != expected_kind):
                continue
            kind, record = row["kind"], _record(row)
            if kind not in ("attribute", "rule"):
                continue
            previous_ref = record.get("supersedes")
            previous_row = db.execute("SELECT * FROM criterion_versions WHERE task_id=? AND ref=? AND kind=?",
                                      (task_id, previous_ref, kind)).fetchone() if previous_ref else None
            previous = _record(previous_row) if previous_row else None
            metadata = _record(db.execute("SELECT body FROM criterion_changes WHERE task_id=? AND source_row=?",
                                          (task_id, row["source_row"])).fetchone())
            # Only the version's own revision metadata describes this transition. A later
            # adjudication can copy the previous version's metadata into a new artifact.
            revision = record.get("workbench_revision") or {}
            is_revision = (bool(previous_ref) and isinstance(revision, dict)
                           and revision.get(f"source_{kind}_ref") == previous_ref)
            reason = revision.get("reason") if is_revision else None
            reason_source = "workbench_revision" if isinstance(reason, str) and reason.strip() else None
            if reason_source is None:
                reason = record.get("rationale") or metadata.get("reason")
                reason_source = "rationale" if reason is not None else None
            item = dict(metadata)
            item.update(ref=ref, kind=kind, version=row["version"], source_row=row["source_row"],
                        artifact_id=row["artifact_id"], supersedes=previous_ref,
                        before_ref=previous_ref, after_ref=ref, before=previous, after=record,
                        predecessor_missing=bool(previous_ref and previous_row is None),
                        operation="revise" if previous_ref else metadata.get("operation"),
                        reason=reason, reason_source=reason_source)
            history.append(item)
            if previous_ref:
                pending.append((previous_ref, kind))
            if kind == "rule" and record.get("attribute_ref"):
                pending.append((record["attribute_ref"], "attribute"))
        return sorted(history, key=lambda item: item["source_row"])

    def criterion(self, task_id: str, wanted: str) -> dict[str, Any]:
        with self._cache() as db, self._source() as source:
            self._ready(db)
            row = self._resolve_criterion(db, task_id, wanted)
            body = _record(row)
            raw = self._artifact(source, row["artifact_id"])
            attribute = _record(db.execute("SELECT body FROM criterion_versions WHERE task_id=? AND ref=?",
                                          (task_id, body.get("attribute_ref"))).fetchone())
            if not attribute:
                attribute = raw.get("attribute") if isinstance(raw.get("attribute"), dict) else raw
            body["editable"] = not is_task_mandated(attribute)
            history_ids = {row["criterion_id"]}
            for ref in (wanted, body.get("attribute_ref"), body.get("rule_ref")):
                if ref:
                    history_ids.update(alias[0] for alias in db.execute("SELECT criterion_id FROM criterion_aliases WHERE task_id=? AND alias=?", (task_id, ref)))
            marks = ",".join("?" for _ in history_ids)
            history_rows = db.execute(f"SELECT source_row,body FROM criterion_changes WHERE task_id=? AND criterion_id IN ({marks}) ORDER BY source_row", (task_id, *history_ids)).fetchall()
            history = [_record(change) for change in history_rows]
            if row["kind"] == "registry":
                registered = self._registered_version_history(db, task_id, [body.get("rule_ref"), body.get("attribute_ref")])
                if registered:
                    by_row = {change["source_row"]: change for change in registered}
                    # Pool/stage changes keep their original before/after and reason.
                    by_row.update({change["source_row"]: _record(change) for change in history_rows
                                   if _record(change).get("kind") not in ("attribute", "rule")})
                    history = [by_row[source_row] for source_row in sorted(by_row)]
            claims = raw.get("supporting_claim_ids") or raw.get("supporting_claim_refs") or []
            sources = self._claims_by_ids(db, source, task_id, claims)
            root_node = self._lineage_node(db, task_id, wanted, body)
            nodes = [dict(root_node, relation="selected")]
            seen = {root_node["id"]}
            edges = []
            for direction, refs in (("parent", body.get("parents") or []), ("child", body.get("children") or [])):
                for ref in refs:
                    node = self._lineage_node(db, task_id, ref)
                    if node["id"] not in seen:
                        nodes.append(dict(node, relation=direction))
                        seen.add(node["id"])
                    edges.append({"source": node["id"] if direction == "parent" else root_node["id"],
                                  "target": root_node["id"] if direction == "parent" else node["id"]})
            versions = []
            for ref in (body.get("attribute_ref"), body.get("rule_ref")):
                if ref:
                    versions.extend(dict(row) for row in db.execute("SELECT ref,kind,version,artifact_id,source_row FROM criterion_versions WHERE task_id=? AND base_id=? ORDER BY version", (task_id, ref.split("@v")[0])))
            body.update(history=history, sources=sources, supporting_claims=claims, versions=versions,
                        critic_findings=raw.get("critic_findings") or [], lineage={"nodes": nodes, "edges": edges}, raw=raw)
            return body

    criterion_detail = criterion

    def criterion_history(self, task_id: str, wanted: str) -> dict[str, Any]:
        return {"items": self.criterion(task_id, wanted)["history"]}

    def criterion_diff(self, task_id: str, wanted: str, before: int | None = None, after: int | None = None) -> dict[str, Any]:
        detail = self.criterion(task_id, wanted)
        history = detail["history"]
        if not history:
            return {"before": None, "after": None, "diff": [], "known": False}
        left_records = [change for change in history if change.get("version") == before] if before is not None else []
        right_records = [change for change in history if change.get("version") == after] if after is not None else history
        left = left_records[-1].get("after") if left_records else history[-1].get("before") if before is None else None
        right = right_records[-1].get("after") if right_records else None
        lines = list(difflib.unified_diff(json.dumps(left, indent=2, ensure_ascii=False).splitlines(),
                                        json.dumps(right, indent=2, ensure_ascii=False).splitlines(), fromfile="before", tofile="after", lineterm=""))
        return {"before": left, "after": right, "diff": lines, "known": left is not None and right is not None}

    def snapshots(self, task_id: str) -> dict[str, Any]:
        with self._cache() as db:
            self._ready(db)
            self._task(db, task_id)
            return {"items": [_record(row) for row in db.execute("SELECT body FROM snapshots WHERE task_id=? ORDER BY published_row DESC", (task_id,))]}

    @staticmethod
    def _snapshot_row(db: sqlite3.Connection, task_id: str, snapshot: str | None) -> sqlite3.Row | None:
        if snapshot:
            row = db.execute("SELECT * FROM snapshots WHERE task_id=? AND snapshot_id=?", (task_id, snapshot)).fetchone()
            if not row:
                raise KeyError(f"no snapshot {snapshot} in {task_id}")
            return row
        return db.execute("SELECT * FROM snapshots WHERE task_id=? ORDER BY published_row DESC LIMIT 1", (task_id,)).fetchone()

    def candidates(self, task_id: str, *, snapshot: str | None = None, status: str = "qualified", q: str = "",
                   page: int = 1, page_size: int = PAGE_SIZE, snapshot_id: str | None = None) -> dict[str, Any]:
        if status not in ("all", "qualified", "pending", "rejected", "unassessed", ""):
            raise ValueError("unknown qualification filter")
        page, page_size, offset = _page(page, page_size)
        with self._cache() as db:
            meta = self._ready(db)
            self._task(db, task_id)
            selected = self._snapshot_row(db, task_id, snapshot or snapshot_id)
            if not selected:
                return {**self._paged([], 0, page, page_size, meta), "snapshot_id": None,
                        "counts": {"qualified": 0, "pending": 0, "rejected": 0, "unassessed": 0, "total": 0},
                        "evaluation_mode": None, "legacy_rank_only": False}
            info = _record(selected)
            clauses, values = ["snapshot_id=?"], [selected["snapshot_id"]]
            if status and status != "all":
                clauses.append("qualification=?")
                values.append(status)
            if q:
                clauses.append("(label LIKE ? ESCAPE '\\' OR candidate_ref LIKE ? ESCAPE '\\')")
                values.extend([_like(q)] * 2)
            where = " AND ".join(clauses)
            total = db.execute(f"SELECT count(*) FROM candidate_rows WHERE {where}", values).fetchone()[0]
            items = [_record(row) for row in db.execute(f"SELECT body FROM candidate_rows WHERE {where} ORDER BY ordinal LIMIT ? OFFSET ?", (*values, page_size, offset))]
            return {**self._paged(items, total, page, page_size, meta), "snapshot_id": selected["snapshot_id"],
                    "counts": info["counts"], "evaluation_mode": info["evaluation_mode"],
                    "legacy_rank_only": info["legacy_rank_only"], "progress": (info.get("reporting_tuple") or {}).get("sweep_completeness")}

    def candidate(self, task_id: str, wanted: str, *, snapshot: str | None = None, snapshot_id: str | None = None) -> dict[str, Any]:
        with self._cache() as db, self._source() as source:
            self._ready(db)
            selected = self._snapshot_row(db, task_id, snapshot or snapshot_id)
            if not selected:
                raise KeyError(f"no snapshot in {task_id}")
            row = db.execute("SELECT body,raw FROM candidate_rows WHERE snapshot_id=? AND candidate_ref=?", (selected["snapshot_id"], wanted)).fetchone()
            if not row:
                raise KeyError(f"no candidate {wanted} in {selected['snapshot_id']}")
            body, raw, info = _record(row), json.loads(row["raw"]), _record(selected)
            assessments, claim_ids = [], set()
            pointers = db.execute("SELECT * FROM assessments WHERE run_id=? AND candidate_ref=? AND source_row IN "
                                  "(SELECT max(source_row) FROM assessments WHERE run_id=? AND candidate_ref=? "
                                  "AND source_row<=? GROUP BY rule_ref) ORDER BY source_row",
                                  (selected["run_id"], wanted, selected["run_id"], wanted, selected["published_row"]))
            for pointer in pointers:
                cell = self._artifact(source, pointer["artifact_id"], {"assessment"})
                reason = self._artifact(source, pointer["reason_artifact_id"], {"reason"})
                attribute = _record(db.execute("SELECT body FROM criterion_versions WHERE task_id=? AND ref=?", (task_id, pointer["attribute_ref"])).fetchone())
                evidence = cell.get("value_source_claim_refs") or []
                claim_ids.update(evidence)
                claim_ids.update(cell.get("conflicting_claim_refs") or [])
                assessments.append({"name": attribute.get("name") or pointer["attribute_ref"], "attribute_ref": pointer["attribute_ref"],
                                    "rule_ref": pointer["rule_ref"], "role": cell.get("rule_kind"), "verdict": cell.get("verdict"),
                                    "value": cell.get("value"), "unit": cell.get("unit"), "basis": cell.get("determination_basis"),
                                    "reason": reason.get("reason_text"), "evidence": evidence,
                                    "counter_evidence": cell.get("conflicting_claim_refs") or []})
            evidence = self._claims_by_ids(db, source, task_id, sorted(claim_ids), maximum=selected["published_row"])
            body.update(snapshot_id=selected["snapshot_id"], run_id=selected["run_id"], assessments=assessments,
                        evidence=evidence, raw=raw, legacy_rank_only=info.get("legacy_rank_only"),
                        evaluation_mode=info.get("evaluation_mode"))
            return body

    candidate_detail = candidate

    @staticmethod
    def _claim(source: sqlite3.Connection, pointer: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        if pointer["body"]:
            cached = json.loads(pointer["body"])
            if "record_available" in cached:
                return cached
        claim = ReadModel._artifact(source, pointer["artifact_id"], {"claim"})
        location = claim.get("location") or {}
        source_id = claim.get("source_ref") or pointer["source_id"]
        url = claim.get("url")
        if not url and source_id:
            if source_id.startswith("src_doi_"):
                url = "https://doi.org/" + source_id[8:]
            elif source_id.startswith("src_pmid_"):
                url = "https://pubmed.ncbi.nlm.nih.gov/" + source_id[9:] + "/"
        return {"claim_id": pointer["claim_id"], "source_id": source_id, "source_ref": source_id,
                "title": claim.get("source_title") or claim.get("title"), "quote": location.get("quoted_span"),
                "locator": location.get("locator_value"), "url": url,
                "statement": claim.get("normalized_statement") or claim.get("claim_text"),
                "basis": claim.get("determination_basis"), "candidate_ref": pointer["candidate_ref"],
                "attribute_ref": claim.get("attribute_ref") or pointer["attribute_ref"],
                "value": claim.get("value"), "unit": claim.get("unit"),
                "admission_state": pointer["admission_state"], "record_available": bool(claim)}

    def _claims_by_ids(self, db: sqlite3.Connection, source: sqlite3.Connection, task_id: str,
                       claim_ids: list[str], maximum: int | None = None) -> list[dict[str, Any]]:
        result = []
        for claim_id in dict.fromkeys(claim_ids):
            sql = "SELECT * FROM claims WHERE task_id=? AND claim_id=? AND admission_state='admitted'"
            values: list[Any] = [task_id, claim_id]
            if maximum is not None:
                sql += " AND source_row<=?"
                values.append(maximum)
            row = db.execute(sql + " ORDER BY source_row DESC LIMIT 1", values).fetchone()
            if row:
                result.append(self._claim(source, row))
            else:
                result.append({"claim_id": claim_id, "record_available": False, "reason": "no admitted public record at this snapshot"})
        return result

    def evidence(self, task_id: str, *, q: str = "", page: int = 1, page_size: int = PAGE_SIZE) -> dict[str, Any]:
        page, page_size, offset = _page(page, page_size)
        clauses, values = ["task_id=?", "admission_state='admitted'"], [task_id]
        if q:
            clauses.append("search_text LIKE ? ESCAPE '\\'")
            values.append(_like(q))
        where = " AND ".join(clauses)
        with self._cache() as db, self._source() as source:
            meta = self._ready(db)
            self._task(db, task_id)
            total = db.execute(f"SELECT count(*) FROM claims WHERE {where}", values).fetchone()[0]
            items = [self._claim(source, row) for row in db.execute(f"SELECT * FROM claims WHERE {where} ORDER BY source_row DESC LIMIT ? OFFSET ?", (*values, page_size, offset))]
            return self._paged(items, total, page, page_size, meta)

    def export_rows(self, task_id: str, snapshot: str | None = None) -> Iterator[dict[str, Any]]:
        """All rows of a fixed snapshot; independent of UI filters and pagination."""
        with self._cache() as db:
            self._ready(db)
            selected = self._snapshot_row(db, task_id, snapshot)
            if not selected:
                return
            info = _record(selected)
            for row in db.execute("SELECT body,raw FROM candidate_rows WHERE snapshot_id=? ORDER BY ordinal", (selected["snapshot_id"],)):
                body, raw = _record(row), json.loads(row["raw"])
                yield {**body, "snapshot_id": selected["snapshot_id"], "evaluation_mode": info.get("evaluation_mode"),
                       "legacy_rank_only": info.get("legacy_rank_only"), "missing": raw.get("missing"),
                       "skip_reason": raw.get("skip_reason") or raw.get("not_assessed_reason")}
