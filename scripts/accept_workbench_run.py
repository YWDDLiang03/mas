"""Final read-only engineering acceptance for one completed workflow.

Measures 50 HTTP requests per list, then rebuilds a separate disposable query
database. Never changes backend source, the primary journal or the service cache.
No polling and no model calls. A running workflow produces no acceptance folder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import quote

sys.dont_write_bytecode = True
from export_workbench_run import API, ExportError, PROJECT_ROOT, now, payload, public

SAMPLES = 50
P95_LIMIT_MS = 300
FIRST_LIMIT_MS = 1000


def encoded(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(encoded(value).encode("utf-8")).hexdigest()


def compare(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    result = {"check": name, "match": encoded(actual) == encoded(expected),
              "actual_sha256": digest(actual), "expected_sha256": digest(expected)}
    if not result["match"]:
        if isinstance(actual, dict) and isinstance(expected, dict):
            result["different_keys"] = [key for key in sorted(set(actual) | set(expected))
                                        if encoded(actual.get(key)) != encoded(expected.get(key))]
        elif isinstance(actual, list) and isinstance(expected, list):
            result.update(actual_length=len(actual), expected_length=len(expected))
            result["first_different_indices"] = [index for index in range(min(len(actual), len(expected)))
                                                 if encoded(actual[index]) != encoded(expected[index])][:10]
    return result


def percentiles(values: list[float]) -> dict[str, Any]:
    ordered = sorted(values)
    return {"n": len(values), "p50_ms": ordered[math.ceil(.5 * len(ordered)) - 1] if ordered else None,
            "p95_ms": ordered[math.ceil(.95 * len(ordered)) - 1] if ordered else None,
            "max_ms": max(ordered) if ordered else None}


def compare_stages(name: str, actual: list[dict[str, Any]], expected: list[dict[str, Any]]) -> dict[str, Any]:
    """Allow only the proved legacy/recorded representation of mandated additions."""
    def comparable(items):
        result = []
        for item in items:
            value = dict(item)
            proof = value.get("added_event_refs")
            basis = value.get("added_count_basis")
            modern = basis == "recorded_result_and_task_binding_events" and isinstance(value.get("mandated_result_refs"), list)
            legacy = basis == "task_binding_events_between_stage_boundaries" and "mandated_result_refs" not in value
            if value.get("stage") == "mandated" and (modern or legacy) and isinstance(proof, list) and value.get("added") == len(proof):
                if all(isinstance(row, dict) and row.get("rule_ref") and row.get("attribute_ref")
                       and row.get("event_id") and isinstance(row.get("source_row"), int)
                       and row.get("rule_artifact_id") for row in proof):
                    pairs = [{"rule_ref": row["rule_ref"], "attribute_ref": row["attribute_ref"]} for row in proof]
                    unique = len({encoded(pair) for pair in pairs}) == len(pairs)
                    recorded_matches = legacy or Counter(map(encoded, value["mandated_result_refs"])) == Counter(map(encoded, pairs))
                    if unique and recorded_matches:
                        value["mandated_result_refs"] = sorted(pairs, key=encoded)
                        value["added_count_basis"] = "verified_task_binding_creation_events"
            result.append(value)
        return result

    raw = compare(name + ".raw", actual, expected)
    result = compare(name, comparable(actual), comparable(expected))
    result["raw_match"] = raw["match"]
    if not raw["match"]:
        result["raw_comparison"] = raw
        result["raw_differences"] = [{"index": index, "actual": actual[index] if index < len(actual) else None,
                                      "expected": expected[index] if index < len(expected) else None}
                                     for index in range(max(len(actual), len(expected)))
                                     if encoded(actual[index] if index < len(actual) else None)
                                     != encoded(expected[index] if index < len(expected) else None)]
        result["representation_compatibility"] = "Only mandated result refs derived from identical complete creation-event proof and its basis label are canonicalized"
    return result


def criterion_cache_view(item: dict[str, Any], evaluation_context: dict[str, Any]) -> dict[str, Any]:
    """Add the same exact-version navigation field as the criteria API boundary."""
    from mas.ui.read_model import ReadModel
    value = dict(item)
    if not value.get("detail_ref"):
        identity = value["criterion_id"]
        value["detail_ref"] = (f"{identity}@v{value['version']}" if identity.startswith("cri_") and "@v" not in identity
                               else value.get("rule_ref") or value.get("attribute_ref") or identity)
    value["evaluation"] = ReadModel._criterion_evaluation(value, evaluation_context)
    return value


def measure(api: API, task_id: str, snapshot_id: str) -> dict[str, Any]:
    prefix = "/tasks/" + quote(task_id, safe="")
    endpoints = {"overview": (prefix + "/overview", {}),
                 "criteria": (prefix + "/criteria", {"state": "working", "page": 1, "page_size": 50}),
                 "stages": (prefix + "/stages", {}),
                 "candidates": (prefix + "/candidates", {"snapshot": snapshot_id, "status": "all", "page": 1, "page_size": 50}),
                 "evidence": (prefix + "/evidence", {"page": 1, "page_size": 50})}
    results = {}
    for name, (path, query) in endpoints.items():
        samples = []
        for index in range(SAMPLES):
            started = time.perf_counter()
            try:
                raw = api.raw(path, **query)
                elapsed = round((time.perf_counter() - started) * 1000, 3)
                value = json.loads(raw.decode("utf-8-sig"))
                if not isinstance(value, dict) or value.get("error") is not None:
                    raise ExportError(f"Unusable JSON response for {name}")
                samples.append({"sample": index + 1, "ms": elapsed, "bytes": len(raw), "ok": True})
            except (ExportError, OSError, ValueError) as error:
                samples.append({"sample": index + 1, "ms": round((time.perf_counter() - started) * 1000, 3),
                                "ok": False, "error": str(error)})
        successful = [sample["ms"] for sample in samples if sample["ok"]]
        stats = percentiles(successful)
        results[name] = {"path": path, "query": query, "samples": samples, **stats,
                         "first_request_ms": samples[0]["ms"], "failed_requests": SAMPLES - len(successful),
                         "first_request_within_1000ms": samples[0]["ok"] and samples[0]["ms"] <= FIRST_LIMIT_MS,
                         "hot_p95_within_300ms": len(successful) == SAMPLES and stats["p95_ms"] <= P95_LIMIT_MS}
    return {"sample_count_per_endpoint": SAMPLES, "timing": "HTTP connection plus full response body; JSON decoding excluded",
            "first_request_scope": "First measured request after completion gate; this is not an uncached database build",
            "p95_limit_ms": P95_LIMIT_MS, "first_request_limit_ms": FIRST_LIMIT_MS,
            "endpoints": results,
            "passed": all(value["hot_p95_within_300ms"] and value["first_request_within_1000ms"] for value in results.values())}


def readonly_database(path: Path) -> sqlite3.Connection:
    database = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA query_only=ON")
    return database


def cache_records(cache_path: Path, task_id: str, snapshot_id: str, *, metadata_only: bool = False) -> dict[str, Any]:
    from mas.ui.read_model import ReadModel
    database = readonly_database(cache_path)
    try:
        metadata = {row["key"]: json.loads(row["value"]) for row in database.execute(
            "SELECT key,value FROM metadata WHERE key IN ('ready','cursor','schema_version','updated_at','source_as_of')")}
        if not metadata.get("ready"):
            raise ExportError("The service projection is not ready; rerun after it has consumed the final snapshot")
        summary_row = database.execute("SELECT body FROM task_summaries WHERE task_id=?", (task_id,)).fetchone()
        snapshot_row = database.execute("SELECT body FROM snapshots WHERE task_id=? AND snapshot_id=?", (task_id, snapshot_id)).fetchone()
        if not summary_row or not snapshot_row:
            raise ExportError("The service projection has not exposed this task/snapshot yet")
        if metadata_only:
            return {"metadata": metadata}
        evaluation_context = ReadModel._evaluation_context(database, task_id, ReadModel._meta(database).get(f"frozen:{task_id}"))
        return {"metadata": metadata, "summary": json.loads(summary_row["body"]),
                "criteria": [criterion_cache_view(json.loads(row[0]), evaluation_context) for row in database.execute(
                    "SELECT body FROM criteria_listing WHERE task_id=? ORDER BY criterion_id", (task_id,))],
                "stages": ReadModel._stages(database, task_id), "snapshot": json.loads(snapshot_row["body"]),
                "candidates": [json.loads(row[0]) for row in database.execute(
                    "SELECT body FROM candidate_rows WHERE snapshot_id=? ORDER BY ordinal", (snapshot_id,))]}
    finally:
        database.close()


def source_records(store: Path, task_id: str, snapshot_id: str) -> dict[str, Any]:
    from mas.core import criteria, pool
    from mas.core.runtime import Core

    with Core.open(store, read_only=True) as core:
        database = core.store.db
        publication = database.execute("SELECT rowid,body FROM events WHERE event_type='leaderboard.snapshot_published' "
            "AND json_extract(body,'$.payload.task_id')=? AND json_extract(body,'$.payload.snapshot_id')=?",
            (task_id, snapshot_id)).fetchall()
        if len(publication) != 1:
            raise ExportError("Expected one source publication for the requested task/snapshot")
        publication_row, raw = publication[0]
        event = json.loads(raw)
        if not public(event):
            raise ExportError("The source snapshot publication is not public")
        snapshot = payload(core, event["payload"]["artifact_id"], {"leaderboard_snapshot"})
        if snapshot.get("task_id") != task_id or snapshot.get("snapshot_id") != snapshot_id:
            raise ExportError("Source snapshot identity differs from the requested task")
        bindings = {}
        for raw, in database.execute("SELECT body FROM events WHERE event_type='run.created' AND json_extract(body,'$.payload.task_id')=?", (task_id,)):
            created = json.loads(raw)
            if public(created) and created["stream_id"].startswith("run_"):
                bindings[created["stream_id"]] = payload(core, created["payload"]["binding_artifact_id"], {"run_binding"})
        streams = [task_id, *bindings]
        marks = ",".join("?" for _ in streams)
        fingerprint = [list(row) for row in database.execute(
            f"SELECT stream_id,max(seq) FROM events WHERE stream_id IN ({marks}) GROUP BY stream_id ORDER BY stream_id", streams)]
        run_states = {}
        for run_id in bindings:
            row = database.execute("SELECT body FROM events WHERE stream_id=? AND event_type IN "
                "('run.created','run.started','run.resumed','run.paused','run.cancelled','run.failed','run.unresolved','run.completed') ORDER BY seq DESC LIMIT 1", (run_id,)).fetchone()
            run_states[run_id] = json.loads(row[0]).get("state_to") if row else None
        stage_events = []
        if bindings:
            run_marks = ",".join("?" for _ in bindings)
            for kind in ("stage.opened", "stage.closed"):
                for rowid, raw in database.execute(f"SELECT rowid,body FROM events WHERE event_type=? AND stream_id IN ({run_marks})", (kind, *bindings)):
                    stage = json.loads(raw)
                    if public(stage):
                        stage_events.append((rowid, stage))
        stages = {}
        for rowid, event in sorted(stage_events):
            data, run_id = event.get("payload") or {}, event["stream_id"]
            key = data.get("stage_key") or f"{(event.get('ids') or {}).get('round_id', '')}:{data.get('stage', 'unknown')}:{data.get('iteration')}"
            stage_id = f"{run_id}:{key}"
            stage = stages.setdefault(stage_id, {"stage_id": stage_id, "run_id": run_id, "stage": data.get("stage", "unknown"),
                                                "iteration": data.get("iteration"), "explicit_fields": []})
            if event["event_type"] == "stage.opened":
                stage.update(started_at=event["recorded_at"], closed=False)
            else:
                stage.update(finished_at=event["recorded_at"], closed=True, state=event.get("state_to") or "completed")
            for field in ("before_count", "after_count", "count_basis"):
                if field in data:
                    stage[field] = data[field]
                    if field not in stage["explicit_fields"]:
                        stage["explicit_fields"].append(field)
        for stage in stages.values():
            if not stage.get("closed"):
                stage["state"] = {"paused": "paused", "cancelled": "interrupted", "failed": "failed", "unresolved": "unresolved",
                    "completed": "unresolved", "queued": "running", "running": "running"}.get(run_states.get(stage["run_id"]), "unresolved")
                stage["after_count"], stage["finished_at"] = None, None
                if "after_count" not in stage["explicit_fields"]:
                    stage["explicit_fields"].append("after_count")
        latest_prepared = None
        for (raw,) in database.execute("SELECT body FROM events WHERE stream_id=? AND event_type='criterion.version_approved' ORDER BY seq DESC", (task_id,)):
            prepared_event = json.loads(raw)
            if public(prepared_event):
                prepared_set = payload(core, prepared_event["payload"]["artifact_id"], {"rule_set"})
                latest_prepared = {"rule_set_ref": prepared_event["payload"].get("rule_set_ref"),
                    "entries": prepared_set.get("entries") or [], "deferred": prepared_set.get("deferred") or []}
                break
        inventory = criteria.registry_inventory(core, task_id)
        rules = criteria.registered_rule_records(core, task_id)
        roles = Counter(rule.get("rule_kind") for rule in rules)
        required = sum(criteria.is_task_mandated(criteria.load(core, rule["attribute_ref"], task_id)) for rule in rules)
        claim_ids = {row[0] for row in database.execute(f"SELECT DISTINCT json_extract(body,'$.payload.claim_id') FROM events "
            f"WHERE event_type='evidence.admitted' AND stream_id IN ({marks}) "
            "AND coalesce(json_extract(body,'$.visibility'),'default') IN ('default','public')", streams) if row[0]}
        summary = {key: inventory[key] for key in ("active_registered_count", "historical_registered_count", "retired_latest_count",
                                                  "pending_review_count", "scoring_in_latest_frozen_set_count")}
        summary.update(hard_count=roles.get("hard_exclusion", 0), preference_count=roles.get("preference", 0),
                       task_required_count=required, claim_count=len(claim_ids))
        legal_criteria_ids = {row["attribute_ref"].split("@v")[0] for row in inventory["active"] + inventory["retired"]}
        legal_criteria_ids.update(pool.fold(core, task_id))
        return {"publication_rowid": publication_row, "snapshot": snapshot, "summary": summary,
                "run_implementations": {run_id: binding.get("implementation") for run_id, binding in bindings.items()},
                "active_rule_refs": sorted(row["rule_ref"] for row in inventory["active"]),
                "latest_prepared": latest_prepared,
                "stages": stages, "stream_fingerprint": fingerprint, "claim_ids": claim_ids,
                "legal_criteria_ids": legal_criteria_ids}


def local_pages(function, **query):
    page, items = 1, []
    while True:
        value = function(page=page, page_size=50, **query)
        items.extend(value["items"])
        if not value["has_more"]:
            if len(items) != value["total"]:
                raise ExportError("The isolated query database returned incomplete pagination")
            return items
        page += 1


def task_fingerprint(store: Path, task_id: str) -> list[list[Any]]:
    database = readonly_database(store / "store.db")
    try:
        runs = [row[0] for row in database.execute("SELECT stream_id FROM events WHERE event_type='run.created' AND json_extract(body,'$.payload.task_id')=?", (task_id,))]
        streams = [task_id, *runs]
        marks = ",".join("?" for _ in streams)
        return [list(row) for row in database.execute(f"SELECT stream_id,max(seq) FROM events WHERE stream_id IN ({marks}) GROUP BY stream_id ORDER BY stream_id", streams)]
    finally:
        database.close()


def parity(api: API, store: Path, service_cache: Path, task_id: str, snapshot_id: str) -> dict[str, Any]:
    from mas.ui.read_model import ReadModel

    prefix = "/tasks/" + quote(task_id, safe="")
    before = task_fingerprint(store, task_id)
    checks = []
    with tempfile.TemporaryDirectory(prefix="mas-workbench-rebuild-acceptance-") as temporary:
        isolated_path = Path(temporary) / "isolated-read.db"
        began = time.perf_counter()
        model = ReadModel(store, cache_path=isolated_path)
        status = model.sync()
        rebuild_seconds = round(time.perf_counter() - began, 3)
        cache_bytes = isolated_path.stat().st_size
        rebuilt_criteria = local_pages(lambda **query: model.criteria(task_id, **query), state="all")
        rebuilt_candidates = local_pages(lambda **query: model.candidates(task_id, **query), snapshot=snapshot_id, status="all")
        rebuilt_summary, rebuilt_stages = model.task_summary(task_id), model.stages(task_id)["items"]
        rebuilt_evidence = model.evidence(task_id, page=1, page_size=50)
        rebuilt_snapshot = next((item for item in model.snapshots(task_id)["items"] if item["snapshot_id"] == snapshot_id), None)
        if rebuilt_snapshot is None:
            raise ExportError("The isolated rebuild did not expose the completed snapshot")
        cached = cache_records(service_cache, task_id, snapshot_id)
        api_criteria, criteria_meta = api.pages(prefix + "/criteria", state="all")
        api_candidates, candidate_meta = api.pages(prefix + "/candidates", snapshot=snapshot_id, status="all")
        api_summary = api.get(prefix + "/overview")["summary"]
        api_stages = api.get(prefix + "/stages")["items"]
        api_evidence = api.get(prefix + "/evidence", page=1, page_size=50)
        source = source_records(store, task_id, snapshot_id)
        for label, actual, expected in [
            ("api_vs_service_cache.summary", api_summary, cached["summary"]),
            ("api_vs_rebuild.summary", api_summary, rebuilt_summary),
            ("api_vs_service_cache.criteria_all_items", api_criteria, cached["criteria"]),
            ("api_vs_rebuild.criteria_all_items", api_criteria, rebuilt_criteria),
            ("api_vs_service_cache.candidates_all_items", api_candidates, cached["candidates"]),
            ("api_vs_rebuild.candidates_all_items", api_candidates, rebuilt_candidates),
            ("api_vs_rebuild.evidence_first_page", api_evidence["items"], rebuilt_evidence["items"]),
            ("service_cache_vs_rebuild.snapshot_summary", cached["snapshot"], rebuilt_snapshot),
            ("api_vs_source.registry_summary", {key: api_summary.get(key) for key in source["summary"]}, source["summary"]),
            ("api_vs_source.active_rule_refs", sorted(item["rule_ref"] for item in api_criteria if item.get("registered") and item.get("current")), source["active_rule_refs"]),
            ("api_vs_source.stage_ids", sorted(item["stage_id"] for item in api_stages), sorted(source["stages"]))]:
            checks.append(compare(label, actual, expected))
        prepared = source["latest_prepared"]
        enabled = {entry["rule_ref"] for entry in (prepared or {}).get("entries") or []}
        held = {}
        for entry in (prepared or {}).get("deferred") or []:
            if entry.get("scope", "rule") == "rule":
                held.setdefault(entry["rule_ref"], entry)
        expected_evaluation, actual_evaluation = [], []
        for item in api_criteria:
            if not item.get("registered") or not item.get("current"):
                continue
            ref, evaluation = item.get("rule_ref"), item.get("evaluation") or {}
            expected_state = "enabled" if ref in enabled else "deferred" if ref in held else "pending" if prepared else "not_prepared"
            expected_evaluation.append({"rule_ref": ref, "state": expected_state,
                "rule_set_ref": prepared.get("rule_set_ref") if prepared else None,
                "reason": held[ref].get("reason") if ref in held and ref not in enabled else None})
            actual_evaluation.append({"rule_ref": ref, "state": evaluation.get("state"),
                "rule_set_ref": evaluation.get("rule_set_ref"), "reason": evaluation.get("reason")})
        checks.append(compare("api_vs_source.latest_prepared_evaluation_membership_and_reasons", actual_evaluation, expected_evaluation))
        checks.append(compare_stages("api_vs_service_cache.stages", api_stages, cached["stages"]))
        checks.append(compare_stages("api_vs_rebuild.stages", api_stages, rebuilt_stages))
        by_stage = {stage["stage_id"]: stage for stage in api_stages}
        stage_fields = []
        for stage_id, expected in source["stages"].items():
            actual = by_stage.get(stage_id) or {}
            keys = ["run_id", "stage", "iteration", "state"] + expected["explicit_fields"]
            if "finished_at" in expected:
                keys.append("finished_at")
            if "started_at" in expected:
                keys.append("started_at")
            stage_fields.append(compare(stage_id, {key: actual.get(key) for key in keys}, {key: expected.get(key) for key in keys}))
        checks.append({"check": "api_vs_source.recorded_stage_boundaries_and_states", "match": all(item["match"] for item in stage_fields),
                       "stage_count": len(stage_fields), "differences": [item for item in stage_fields if not item["match"]]})
        raw_entries = source["snapshot"].get("candidate_entries") or []
        source_candidates = [{"candidate_ref": row["candidate_ref"], "position": row.get("position"),
                              "score": row.get("preference_score", row.get("score"))} for row in raw_entries]
        checks.append(compare("api_vs_source.full_snapshot_candidate_ids_rank_and_score",
            [{key: row.get(key) for key in ("candidate_ref", "position", "score")} for row in api_candidates], source_candidates))
        checks.append(compare("api_candidate_page.total_vs_source", candidate_meta["total"], len(raw_entries)))
        source_qualifications = {}
        for row in raw_entries:
            value = row.get("qualification")
            state = (value.get("state") if isinstance(value, dict) else value if isinstance(value, str) else None) or row.get("qualification_state")
            if state in ("qualified", "pending", "rejected", "unassessed", "not_ready"):
                source_qualifications[row["candidate_ref"]] = "pending" if state == "not_ready" else state
        checks.append(compare("api_vs_source.explicit_candidate_qualifications",
            {row["candidate_ref"]: row.get("qualification") for row in api_candidates if row["candidate_ref"] in source_qualifications}, source_qualifications))
        header = source["snapshot"]
        keys = ("snapshot_id", "task_id", "run_id", "evaluation_mode", "qualification_policy", "readiness", "result_kind")
        checks.append(compare("service_cache_vs_source.snapshot_header", {key: cached["snapshot"].get(key) for key in keys},
                              {key: header.get(key) for key in keys}))
        if header.get("qualified_count") is not None:
            checks.append(compare("api_vs_source.recorded_qualified_count", candidate_meta.get("counts", {}).get("qualified"), header["qualified_count"]))
        checks.append({"check": "api_criteria_ids_exist_in_source_registry_or_pool", "match": all(item["criterion_id"] in source["legal_criteria_ids"] for item in api_criteria),
                       "unknown_ids": [item["criterion_id"] for item in api_criteria if item["criterion_id"] not in source["legal_criteria_ids"]]})
        checks.append({"check": "api_evidence_first_page_ids_are_public_source_claims", "match": all(item["claim_id"] in source["claim_ids"] for item in api_evidence["items"])})
        checks.append(compare("source_task_unchanged_during_acceptance", task_fingerprint(store, task_id), before))
        checks.append({"check": "service_cursor_consumed_snapshot_publication", "match": cached["metadata"]["cursor"] >= source["publication_rowid"]})
        checks.append({"check": "rebuild_cursor_consumed_snapshot_publication", "match": status["source_cursor"] >= source["publication_rowid"]})
        result = {"scope": "Only the requested completed task is compared; historical task checks are not rerun",
                  "rebuild": {"seconds": rebuild_seconds, "cache_bytes": cache_bytes, "schema_version": status["schema_version"],
                              "source_cursor": status["source_cursor"], "cache_location": "disposable system temporary directory", "deleted_after_checks": True},
                  "service_cache": {"path": str(service_cache), "open_mode": "ro", **cached["metadata"]},
                  "source_open_mode": "read_only", "source_publication_rowid": source["publication_rowid"],
                  "checks": checks, "passed": all(check["match"] for check in checks),
                  "source_registry_summary": source["summary"],
                  "source_run_implementations": source["run_implementations"],
                  "source_qualification_check_scope": {"explicit_rows_compared": len(source_qualifications),
                      "rows_without_explicit_qualification": len(raw_entries) - len(source_qualifications)},
                  "pagination": {"page_size": 50, "criteria_total": len(api_criteria), "candidates_total": len(api_candidates),
                      "api_criteria_ids": [item["criterion_id"] for item in api_criteria],
                      "rebuilt_criteria_ids": [item["criterion_id"] for item in rebuilt_criteria],
                      "api_candidate_ids": [item["candidate_ref"] for item in api_candidates],
                      "rebuilt_candidate_ids": [item["candidate_ref"] for item in rebuilt_candidates],
                      "source_candidate_ids": [item["candidate_ref"] for item in raw_entries]},
                  "source_stage_check_limit": "Independent source checks cover IDs, lifecycle state and explicitly recorded boundaries; all DTO stage fields also match service cache vs rebuild"}
    return result


def prior_measurements() -> list[dict[str, Any]]:
    paths = [PROJECT_ROOT / "design_audit/workbench_redesign_2026-10-16/read_model_benchmark.json",
             PROJECT_ROOT / "design_audit/workbench_redesign_2026-10-16/live_propagation_200ms.json",
             PROJECT_ROOT / "var/workbench-v2-acceptance/legacy-new-http-sample.json"]
    return [{"path": str(path), "available": path.is_file(),
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
             "scope": "Prior evidence preserved unchanged; not repeated or relabelled as the final 50-sample measurement"} for path in paths]


def run(task_id: str, workflow_id: str, base_url: str, store: Path, output: Path,
        service_cache: Path | None = None) -> dict[str, Any]:
    store, output = store.resolve(), output.resolve()
    if output.exists() or any(output == protected or output.is_relative_to(protected)
                              for protected in (store, PROJECT_ROOT / "src", PROJECT_ROOT / "var/primary")):
        raise ExportError("Choose a new acceptance folder outside backend source, the primary store and cache")
    api = API(base_url)
    workflow_path = "/workflows/" + quote(workflow_id, safe="")
    workflow = api.get(workflow_path)
    if workflow.get("workflow_id") != workflow_id or workflow.get("task_id") != task_id or workflow.get("state") != "completed" or not workflow.get("snapshot_id"):
        raise ExportError(f"Acceptance not run: task/workflow mismatch or state={workflow.get('state')}, snapshot={workflow.get('snapshot_id')}")
    snapshot_id = workflow["snapshot_id"]
    service_cache = (service_cache or Path(os.environ.get("MAS_WORKBENCH_READ_CACHE")
                                         or store.parent / "workbench-read.db")).resolve()
    # Readiness preflight is a single lookup, never a wait/poll loop.
    preflight = cache_records(service_cache, task_id, snapshot_id, metadata_only=True)
    report = {"kind": "completed_workflow_engineering_acceptance", "created_at": now(), "task_id": task_id,
              "workflow_id": workflow_id, "snapshot_id": snapshot_id, "workflow_state": "completed",
              "scientific_success_claimed": False, "models_called": 0, "primary_or_service_cache_written": False,
              "service_projection_before": preflight["metadata"], "prior_evidence": prior_measurements()}
    try:
        report["http"] = measure(api, task_id, snapshot_id)
        report["parity"] = parity(api, store, service_cache, task_id, snapshot_id)
        final_workflow = api.get(workflow_path)
        report["workflow_still_completed_same_snapshot"] = final_workflow.get("state") == "completed" and final_workflow.get("snapshot_id") == snapshot_id
        report["engineering_checks_passed"] = report["http"]["passed"] and report["parity"]["passed"] and report["workflow_still_completed_same_snapshot"]
    except Exception as error:
        report.update(engineering_checks_passed=False, error={"type": type(error).__name__, "message": str(error)})
    lines = ["# 完成工作流的最终工程验收", "", f"任务 `{task_id}`；工作流 `{workflow_id}`；快照 `{snapshot_id}`。", "",
             f"工程检查全部通过：**{report['engineering_checks_passed']}**。此字段不代表科学目标成功或参考候选获得资格。", "",
             "## 完成后的 HTTP 测量", "", "每个接口实际测量 50 次；首次值是完成门槛之后的首个测量请求，不等同于数据库冷构建。", "",
             "| 列表 | 成功样本 | 首次 ms | P95 ms | 最大 ms | 错误数 |", "|---|---:|---:|---:|---:|---:|"]
    for name, value in (report.get("http") or {}).get("endpoints", {}).items():
        lines.append(f"| {name} | {value['n']} | {value['first_request_ms']} | {value['p95_ms']} | {value['max_ms']} | {value['failed_requests']} |")
    result = report.get("parity") or {}
    lines += ["", "## 隔离重建与源记录对齐", "", f"临时库重建：{json.dumps(result.get('rebuild'), ensure_ascii=False)}。", "",
              "重建只写独立临时数据库并在结束时清理。服务 cache 与源库以只读方式打开；只对本任务进行分页、summary、stages、候选快照与源注册记录核对。", "",
              "| 核对 | 一致 |", "|---|---|"]
    lines += [f"| {check['check']} | {check['match']} |" for check in result.get("checks") or []]
    if report.get("error"):
        lines += ["", "执行错误保留：`" + json.dumps(report["error"], ensure_ascii=False) + "`。"]
    lines += ["", "先前性能证据保留原文件与 SHA-256；历史单次比较没有当作 P95，本次没有重跑旧任务基准。原始 50 样本、分页 ID、差异与重建状态见 acceptance.json。", ""]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".workbench-acceptance-", dir=output.parent) as temporary:
        staging = Path(temporary)
        (staging / "acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (staging / "report.md").write_text("\n".join(lines), encoding="utf-8")
        os.replace(staging, output)
    return {"output": str(output), "engineering_checks_passed": report["engineering_checks_passed"],
            "scientific_success_claimed": False, "snapshot_id": snapshot_id, "error": report.get("error")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8770")
    parser.add_argument("--store", type=Path, default=PROJECT_ROOT / "var/primary/store")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--service-cache", type=Path, help="Exact query database used by the running service")
    args = parser.parse_args(argv)
    try:
        result = run(args.task, args.workflow, args.base_url, args.store, args.output, args.service_cache)
    except (ExportError, OSError, ValueError) as error:
        print(f"Acceptance refused: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["engineering_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
