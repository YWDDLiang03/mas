"""Export one completed workbench workflow without writing its source or cache.

Example, after the workflow has completed::

    .venv/Scripts/python.exe -B scripts/export_workbench_run.py \
      --workflow wf_example --base-url http://127.0.0.1:8770 \
      --store var/workspace/store --output var/exports/wf_example

No polling and no model calls. A non-completed workflow produces no final folder.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

TASK_EVENTS = ("task.version_recorded", "criterion.version_proposed", "criterion.version_approved",
               "criterion.change_recorded", "human.review_requested", "human.review_decided",
               "human.review_withdrawn", "decision.recorded", "run.continued")
MODEL_EVENTS = ("stage.opened", "stage.closed", "step.started", "step.completed", "agent.started", "agent.finished")
PUBLIC_KINDS = frozenset({"task_context", "run_binding", "attribute", "rule", "rule_set",
                          "criterion_candidate", "leaderboard_snapshot", "derivation_stage", "derivation_record"})


class ExportError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class API:
    def __init__(self, base_url: str):
        base_url = base_url.rstrip("/")
        self.base = base_url if base_url.endswith("/api/workbench") else base_url + "/api/workbench"

    def raw(self, path: str, **query: Any) -> bytes:
        url = self.base + path + ("?" + urlencode({k: v for k, v in query.items() if v is not None}) if query else "")
        try:
            with urlopen(url, timeout=30) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as error:
            raise ExportError(f"GET {path} failed: {error}") from error

    def get(self, path: str, **query: Any) -> dict[str, Any]:
        value = json.loads(self.raw(path, **query).decode("utf-8-sig"))
        if not isinstance(value, dict) or value.get("error") is not None:
            raise ExportError(f"Unexpected API response for {path}: {value}")
        return value

    def pages(self, path: str, **query: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        items, first, page = [], None, 1
        while True:
            value = self.get(path, page=page, page_size=50, **query)
            if first is None:
                first = value
            if value.get("page_size") != 50 or value.get("page") != page:
                raise ExportError(f"Unexpected pagination for {path}")
            if value.get("total") != first.get("total"):
                raise ExportError(f"The projected list changed during export: {path}")
            batch = value.get("items") or []
            items.extend(batch)
            if not value.get("has_more"):
                if len(items) != value.get("total"):
                    raise ExportError(f"Incomplete page collection for {path}: {len(items)} / {value.get('total')}")
                return items, {k: v for k, v in first.items() if k != "items"}
            if not batch:
                raise ExportError(f"Empty page claims more rows: {path}")
            page += 1


def public(event: dict[str, Any]) -> bool:
    return event.get("visibility", "default") in ("default", "public")


def payload(core, artifact_id: str, allowed: set[str] | frozenset[str] = PUBLIC_KINDS) -> dict[str, Any]:
    # Check the kind before fetching a body. Never traverse case, evaluator,
    # recovery, prompt trace, or arbitrary artifact links from public records.
    row = core.store.db.execute("SELECT kind FROM artifacts WHERE artifact_id=?", (artifact_id,)).fetchone()
    if row is None or row[0] not in allowed or row[0] not in PUBLIC_KINDS:
        raise ExportError(f"Missing or non-public artifact kind for {artifact_id}")
    return core.artifacts.payload(artifact_id)


def selected_source(store: Path, workflow: dict[str, Any]) -> dict[str, Any]:
    from mas.core.runtime import Core

    task_id, snapshot_id = workflow["task_id"], workflow["snapshot_id"]
    with Core.open(store, read_only=True) as core:
        db = core.store.db
        found = db.execute("SELECT rowid,body FROM events WHERE event_type='leaderboard.snapshot_published' "
                           "AND json_extract(body,'$.payload.task_id')=? AND json_extract(body,'$.payload.snapshot_id')=?",
                           (task_id, snapshot_id)).fetchall()
        if len(found) != 1:
            raise ExportError(f"Expected one publication for this task/snapshot, got {len(found)}")
        publication_row, publication_raw = found[0]
        publication = json.loads(publication_raw)
        if not public(publication) or not publication["stream_id"].startswith("run_"):
            raise ExportError("The selected snapshot does not have a public run publication")
        snapshot = payload(core, publication["payload"]["artifact_id"], {"leaderboard_snapshot"})
        if snapshot.get("task_id") != task_id or snapshot.get("snapshot_id") != snapshot_id:
            raise ExportError("Snapshot identity differs from the requested workflow")
        if snapshot.get("run_id") != workflow.get("run_id"):
            raise ExportError("Workflow run and published snapshot run differ")
        events = []
        for kind in TASK_EVENTS:
            for rowid, raw in db.execute("SELECT rowid,body FROM events WHERE event_type=? AND stream_id=? AND rowid<=?",
                                         (kind, task_id, publication_row)):
                event = json.loads(raw)
                if public(event):
                    events.append({"source_rowid": rowid, **event})
        events.sort(key=lambda event: event["seq"])
        contexts = [event for event in events if event["event_type"] == "task.version_recorded"]
        bound_context = snapshot.get("task_context_id@v")
        version = int(bound_context.rsplit("@v", 1)[1]) if bound_context and "@v" in bound_context else None
        context_event = next((event for event in reversed(contexts) if version is None or event["payload"].get("version") == version), None)
        if context_event is None:
            raise ExportError("No public task context matches the frozen snapshot")
        context = payload(core, context_event["payload"]["artifact_id"], {"task_context"})
        records, excluded = {}, []
        for event in events:
            if event["event_type"] not in ("criterion.version_proposed", "criterion.version_approved", "criterion.change_recorded"):
                continue
            reference = event["payload"].get("artifact_id")
            if not reference or reference in records:
                continue
            meta = db.execute("SELECT kind FROM artifacts WHERE artifact_id=?", (reference,)).fetchone()
            if not meta or meta[0] not in PUBLIC_KINDS:
                excluded.append({"artifact_id": reference, "event_id": event["event_id"], "reason": "outside public CQA artifact allowlist"})
                continue
            records[reference] = {"kind": meta[0], "payload": payload(core, reference)}
        # Scope cost records to runs created for this task in this workflow's
        # time window, plus the task stream used by normalization and review.
        started, finished = workflow["started_at"], workflow.get("finished_at") or now()
        bindings = {}
        for raw, in db.execute("SELECT body FROM events WHERE event_type='run.created' "
                               "AND json_extract(body,'$.payload.task_id')=? AND recorded_at>=? AND recorded_at<=?",
                               (task_id, started, finished)):
            event = json.loads(raw)
            if public(event) and event["stream_id"].startswith("run_"):
                bindings[event["stream_id"]] = payload(core, event["payload"]["binding_artifact_id"], {"run_binding"})
        if snapshot["run_id"] not in bindings:
            raise ExportError("The snapshot's screening run is outside this workflow's task/time scope")
        streams = [task_id, *bindings]
        markers, values = ",".join("?" for _ in streams), []
        for kind in MODEL_EVENTS:
            for raw, in db.execute(f"SELECT body FROM events WHERE event_type=? AND stream_id IN ({markers}) "
                                   "AND recorded_at>=? AND recorded_at<=?", (kind, *streams, started, finished)):
                event = json.loads(raw)
                if public(event):
                    values.append(event)
        values.sort(key=lambda event: (event["recorded_at"], event["stream_id"], event["seq"]))
        return {"snapshot": snapshot, "task": context, "publication": publication,
                "publication_rowid": publication_row, "cqa_events": events, "cqa_records": records,
                "excluded_cqa_artifacts": excluded, "run_bindings": bindings, "model_events": values}


def phase_of(workflow: dict[str, Any], event: dict[str, Any], stage: str | None) -> str:
    # Resumed phases can overlap in wall-clock time. The recorded work/stream
    # identity is stronger than a cumulative phase's time window.
    if event["stream_id"].startswith("task_"):
        return "review" if (event.get("payload") or {}).get("role") == "adjudicator" else "task"
    name = (stage or "").split(":", 1)[0]
    if name == "evidence":
        return "evidence"
    if name in ("mandated", "propose"):
        return "propose"
    if name in ("filter", "distill", "refine", "merge", "promote", "reenter"):
        return "refine"
    if name in ("identity", "assess", "snapshot"):
        return "screen"
    stamp = event["recorded_at"]
    windows = [phase for phase in workflow.get("phases") or [] if phase.get("started_at")
               and phase["started_at"] <= stamp and (not phase.get("finished_at") or stamp <= phase["finished_at"])]
    if windows:
        return max(windows, key=lambda phase: phase["started_at"])["id"]
    return "unknown"


def accounting(workflow: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    stages, requests, finished, rows, groups = {}, {}, set(), [], defaultdict(list)
    for event in events:
        kind, stream, item = event["event_type"], event["stream_id"], event.get("payload") or {}
        if kind in ("stage.opened", "step.started"):
            stages[stream] = {"stage": item.get("stage") or item.get("step"), "iteration": item.get("iteration")}
        elif kind in ("stage.closed", "step.completed"):
            stages.pop(stream, None)
        elif kind == "agent.started":
            requests[item["request_id"]] = {"event": event, **stages.get(stream, {})}
        elif kind == "agent.finished":
            identity = item.get("request_id")
            if identity in finished:
                continue
            finished.add(identity)
            begin = requests.get(identity) or {"event": event, **stages.get(stream, {})}
            phase = phase_of(workflow, begin["event"], begin.get("stage"))
            cost = item.get("known_cost_usd", item.get("cost_usd"))
            known = isinstance(cost, (int, float)) and not isinstance(cost, bool) and math.isfinite(cost)
            row = {"request_id": identity, "run_or_task_id": stream, "phase": phase,
                   "stage": begin.get("stage"), "iteration": begin.get("iteration"), "role": item.get("role"),
                   "started_at": begin["event"]["recorded_at"], "finished_at": event["recorded_at"],
                   "usage": item.get("usage") or {}, "usage_status": item.get("usage_status") or "unknown",
                   "known_cost_usd": cost if known else None, "cost_status": item.get("cost_status") or "unknown",
                   "outcome": item.get("outcome"), "error_class": item.get("error_class"),
                   "attempt_count": item.get("attempt_count"), "provider_attempt_count": item.get("provider_attempt_count")}
            rows.append(row)
            groups[(phase, begin.get("stage"), begin.get("iteration"), item.get("role"))].append(row)

    def aggregate(values):
        known = [row["known_cost_usd"] for row in values if row["known_cost_usd"] is not None]
        tokens = {}
        for key in ("input_tokens", "output_tokens"):
            present = [row["usage"][key] for row in values if isinstance(row["usage"].get(key), int)]
            tokens[key] = sum(present) if present else None
        return {"requests": len(values), "known_cost_usd": round(sum(known), 10) if known else None,
                "cost_status": "not_started" if not values else "unknown" if not known else
                    "estimated" if len(known) == len(values) and all(row["cost_status"] in ("estimated", "recorded") for row in values) else "partial",
                "unknown_or_partial_cost_requests": sum(row["known_cost_usd"] is None or row["cost_status"] in ("unknown", "partial") for row in values),
                "usage": tokens, "usage_status": "complete" if values and all(row["usage_status"] == "complete" for row in values) else "partial" if any(value is not None for value in tokens.values()) else "unknown"}

    outstanding = [{"request_id": identity, "started_at": value["event"]["recorded_at"], "stream_id": value["event"]["stream_id"]}
                   for identity, value in requests.items() if identity not in finished]
    total = aggregate(rows)
    if outstanding and total["cost_status"] == "estimated":
        total["cost_status"] = "partial"
    return {"scope": "This workflow's task/runs and started_at..finished_at only; previous stopped workflows excluded.",
            "basis": "agent.finished aggregates only; provider_attempt annotations are not added again",
            "total": total, "workflow_budget_record": workflow.get("budget"), "unfinished_model_requests": outstanding,
            "by_stage_and_role": [{"phase": key[0], "stage": key[1], "iteration": key[2], "role": key[3], **aggregate(value)}
                                  for key, value in sorted(groups.items(), key=lambda item: tuple(str(part or "") for part in item[0]))],
            "requests": rows, "previous_stopped_workflows_cost_included": False}


def qualification(entry: dict[str, Any], snapshot: dict[str, Any]) -> str:
    value = entry.get("qualification")
    if isinstance(value, dict) and value.get("state"):
        return value["state"]
    if isinstance(value, str):
        return value
    if entry.get("qualification_state"):
        return entry["qualification_state"]
    if snapshot.get("qualification_policy") == "qualification_first_v1" and entry.get("qualified") is True:
        return "qualified"
    return "unknown_legacy" if snapshot.get("qualification_policy") != "qualification_first_v1" else "unknown"


def surufatinib_rows(snapshot: dict[str, Any]) -> dict[str, Any]:
    matches = []
    for entry in snapshot.get("candidate_entries") or []:
        labels = " ".join(str(value or "") for value in entry.get("identity_labels") or [])
        if re.search(r"\b(?:surufatinib|sulfatinib|hmpl[- ]?012)\b", labels, re.I) or entry.get("candidate_ref") == "cand_inchikey-TTZSNFLLYPYKIL-UHFFFAOYSA-N":
            matches.append({"candidate_ref": entry["candidate_ref"], "labels": entry.get("identity_labels"),
                            "qualification": qualification(entry, snapshot), "rank": entry.get("position"),
                            "rank_status": "not_recorded" if "position" not in entry else "unranked" if entry["position"] is None else "ranked",
                            "score": entry.get("preference_score"), "qualification_record": entry.get("qualification"),
                            "state": entry.get("state"), "reason": entry.get("state_reason"),
                            "preference_coverage": entry.get("preference_coverage"), "hard_evidence_coverage": entry.get("coverage"),
                            "mandated_coverage": entry.get("mandated_coverage"), "missing": entry.get("missing"),
                            "rank_note": entry.get("rank_note"), "gap_filled_criteria": entry.get("gap_filled_criteria")})
    return {"status": "found" if len(matches) == 1 else "not_found" if not matches else "ambiguous", "matches": matches}


def _cell(value: Any) -> str:
    if value is None:
        return "未知／未记录"
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def markdown(bundle: dict[str, Any]) -> str:
    workflow, snapshot, costs = bundle["workflow"], bundle["source"]["snapshot"], bundle["accounting"]
    summary, reporting = bundle["overview"].get("summary") or {}, snapshot.get("reporting_tuple") or {}
    entries = snapshot.get("candidate_entries") or []
    counts = Counter(qualification(entry, snapshot) for entry in entries)
    lines = ["# 工作流最终记录与验收报告", "", "这是已完成工作流发布快照的记录导出。工作流完成表示处理结束；科学结论按以下真实资格、覆盖与未知状态陈述。", "",
             f"- 工作流：`{workflow['workflow_id']}`", f"- 任务：`{workflow['task_id']}`", f"- 快照：`{workflow['snapshot_id']}`",
             f"- 模式：{_cell(snapshot.get('evaluation_mode'))}；资格政策：{_cell(snapshot.get('qualification_policy'))}",
             f"- Readiness：{_cell(snapshot.get('readiness'))}；结果类型：{_cell(snapshot.get('result_kind'))}",
             f"- 弃权／无推荐原因：{_cell(snapshot.get('abstention_reason'))}", "", "## 数量与覆盖", "",
             f"候选总数 **{len(entries)}**；qualified **{counts.get('qualified', 0)}**；其余状态：{_cell(dict(counts))}。",
             f"CSV 实际行数 **{bundle['validation']['csv_rows']}**，已与原始 snapshot 及完整 API 候选集合核对。", "",
             "| 指标 | 原记录 |", "|---|---|",
             *[f"| {key} | {_cell(reporting.get(key))} |" for key in ("sweep_completeness", "assessment_completeness", "direct_coverage_fraction", "coverage_fraction", "recorded_cell_n", "assessed_cell_n", "skipped_after_rejection_n", "missing_or_conflicted_n", "error_n")],
             "", "缺失、冲突、未评估和拒绝后跳过分别保留；缺失指标表示未知，不补成零。", "", "## Surufatinib 的实际结果", ""]
    suruf = bundle["surufatinib"]
    if suruf["status"] != "found":
        lines.append(f"匹配状态：**{suruf['status']}**。未自动挑选一个候选或补造资格／排名；详见 surufatinib.json。")
    for row in suruf["matches"]:
        rank = "未排名（原记录 position=null）" if row["rank_status"] == "unranked" else _cell(row["rank"])
        lines += [f"- 候选：`{row['candidate_ref']}`（{_cell(row['labels'])}）", f"- 资格：**{_cell(row['qualification'])}**；排名：**{rank}**；得分：{_cell(row['score'])}",
                  f"- 偏好覆盖：{_cell(row['preference_coverage'])}；硬条件证据覆盖：{_cell(row['hard_evidence_coverage'])}；任务要求覆盖：{_cell(row['mandated_coverage'])}",
                  f"- 原资格记录：{_cell(row['qualification_record'])}", f"- 原因：{_cell(row['reason'])}；缺失：{_cell(row['missing'])}；排名说明：{_cell(row['rank_note'])}"]
    lines += ["", "## CQA 演化", "", f"当前 API 摘要：{_cell(summary)}。", "",
              "阶段数量严格保留 count_basis；工作提案数量与当前注册数量按各自口径显示。下面的未知边界保留为空缺，完整版本、变更与 lineage 见 cqa.json 和 source-cqa-history.json。", "",
              "| 阶段 | 迭代 | 计数口径 | 前 → 后 | 新增 | 修改 | 合并 | 移除 |", "|---|---:|---|---|---:|---:|---:|---:|"]
    for stage in bundle["stages"]:
        lines.append("| " + " | ".join(_cell(value) for value in (stage.get("stage"), stage.get("iteration"), stage.get("count_basis") or stage.get("counts_basis"),
                     f"{_cell(stage.get('before_count'))} → {_cell(stage.get('after_count'))}", stage.get("added"), stage.get("modified"), stage.get("merged"), stage.get("removed"))) + " |")
    lines += ["", "## 模型用量与费用估算", "", "仅累计本工作流时间窗内的 agent.finished 聚合；内部 provider_attempt 不重复相加。前两次停止运行费用由操作者另行合并，本脚本没有将其加到本次费用。", "",
              f"已知费用小计：**{_cell(costs['total']['known_cost_usd'])} USD**；状态：**{costs['total']['cost_status']}**。",
              f"工作流预算原记录：{_cell(costs.get('workflow_budget_record'))}。未结束的模型逻辑请求：{len(costs['unfinished_model_requests'])}。", "",
              "| 阶段／操作 | 角色 | 请求 | 输入 token | 输出 token | 已知 USD | 费用状态 |", "|---|---|---:|---:|---:|---:|---|"]
    for group in costs["by_stage_and_role"]:
        lines.append("| " + " | ".join(_cell(value) for value in (f"{group['phase']} / {group['stage'] or '—'}", group["role"], group["requests"], group["usage"]["input_tokens"], group["usage"]["output_tokens"], group["known_cost_usd"], group["cost_status"])) + " |")
    lines += ["", "## 核对与保留项", "", f"核对原记录：{_cell(bundle['validation'])}。", "",
              "本报告不自动声称研究成功、找到了合格候选或达到了参考药物目标。资格为 pending/not_ready、排名为空、覆盖不足和费用未知均按原记录保留。", "",
              "完整候选：[candidates.csv](candidates.csv)、[candidates.json](candidates.json)、[snapshot.json](snapshot.json)；模型记录：[model-accounting.json](model-accounting.json)；导出范围与文件校验和见 manifest.json。", ""]
    return "\n".join(lines)


def export(workflow_id: str, base_url: str, store: Path, output: Path) -> dict[str, Any]:
    store, output = store.resolve(), output.resolve()
    if any(output == protected or output.is_relative_to(protected) for protected in (store, PROJECT_ROOT / "src", PROJECT_ROOT / "var" / "primary")):
        raise ExportError("Choose an output directory outside backend source, the primary store and its cache directory")
    if output.exists():
        raise ExportError(f"Output already exists; choose a new export directory: {output}")
    api = API(base_url)
    workflow_path = "/workflows/" + quote(workflow_id, safe="")
    workflow = api.get(workflow_path)
    if workflow.get("workflow_id") != workflow_id or workflow.get("state") != "completed" or not workflow.get("snapshot_id") or not workflow.get("task_id"):
        raise ExportError(f"No final export: workflow state={workflow.get('state')}, snapshot={workflow.get('snapshot_id')}. Nothing was exported.")
    task_id, snapshot_id = workflow["task_id"], workflow["snapshot_id"]
    prefix = "/tasks/" + quote(task_id, safe="")
    overview = api.get(prefix + "/overview")
    stages = api.get(prefix + "/stages").get("items") or []
    criteria_items, cqa_page = api.pages(prefix + "/criteria", state="all")
    details = [api.get(prefix + "/criteria/" + quote(item.get("detail_ref") or item["criterion_id"], safe="")) for item in criteria_items]
    candidates, candidate_page = api.pages(prefix + "/candidates", snapshot=snapshot_id, status="all")
    if candidate_page.get("snapshot_id") != snapshot_id:
        raise ExportError("Projected candidate list is not the workflow's published snapshot")
    csv_bytes = api.raw(prefix + "/export.csv", snapshot=snapshot_id)
    csv_rows = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig"))))
    source = selected_source(store, workflow)
    entries = source["snapshot"].get("candidate_entries") or []
    expected = [entry["candidate_ref"] for entry in entries]
    csv_ids, api_ids = [row.get("candidate_ref") for row in csv_rows], [row.get("candidate_ref") for row in candidates]
    if len(csv_rows) != len(entries) or len(candidates) != len(entries) or Counter(csv_ids) != Counter(expected) or Counter(api_ids) != Counter(expected):
        raise ExportError(f"Final row verification failed: source={len(entries)}, CSV={len(csv_rows)}, API={len(candidates)}. Nothing was exported.")
    if any(row.get("snapshot_id") != snapshot_id for row in csv_rows):
        raise ExportError("CSV contains rows for a different snapshot")
    final_workflow = api.get(workflow_path)
    if final_workflow.get("state") != "completed" or final_workflow.get("snapshot_id") != snapshot_id:
        raise ExportError("The workflow changed while exporting; no final folder was written")
    suruf = surufatinib_rows(source["snapshot"])
    for row in suruf["matches"]:
        row["detail"] = api.get(prefix + "/candidates/" + quote(row["candidate_ref"], safe=""), snapshot=snapshot_id)
    cqa = {"items": criteria_items, "page_collection": cqa_page, "details": details,
           "active_registered": [item for item in criteria_items if item.get("current") and item.get("registered")],
           "pending": [item for item in criteria_items if item.get("current") and (item.get("pending_review") or item.get("state") == "pending")],
           "inactive_history": [item for item in criteria_items if not item.get("current")],
           "sets_note": "Pending review overlaps active registered; these are not disjoint scientific populations.",
           "lineage": {"nodes": [node for detail in details for node in (detail.get("lineage") or {}).get("nodes") or []],
                       "edges": [edge for detail in details for edge in (detail.get("lineage") or {}).get("edges") or []]}}
    validation = {"workflow_completed": True, "snapshot_present": True, "snapshot_run_matches_workflow": True,
                  "snapshot_candidates": len(entries), "csv_rows": len(csv_rows), "api_candidate_rows": len(candidates),
                  "csv_and_api_candidate_id_multisets_match_snapshot": True,
                  "source_publication_rowid": source["publication_rowid"], "surufatinib_match_status": suruf["status"],
                  "snapshot_readiness": source["snapshot"].get("readiness"), "scientific_success_claimed": False,
                  "cqa_api_as_of": cqa_page.get("as_of"), "cqa_source_history_scope": "selected task through this snapshot publication",
                  "excluded_cqa_artifacts": source["excluded_cqa_artifacts"]}
    bundle = {"workflow": final_workflow, "overview": overview, "stages": stages, "source": source,
              "surufatinib": suruf, "validation": validation, "accounting": accounting(workflow, source["model_events"])}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".workbench-final-export-", dir=output.parent) as temporary:
        staging = Path(temporary)
        documents = {"workflow.json": final_workflow, "task.json": source["task"], "overview.json": overview,
                     "snapshot.json": source["snapshot"], "stages.json": {"items": stages}, "cqa.json": cqa,
                     "source-cqa-history.json": {"events": source["cqa_events"], "records": source["cqa_records"],
                                                 "snapshot_publication": source["publication"]},
                     "run-bindings.json": source["run_bindings"], "candidates.json": {"items": candidates, "total": len(candidates),
                         "collection_complete": True, "snapshot_id": snapshot_id, "api_first_page_metadata": candidate_page},
                     "surufatinib.json": suruf, "model-accounting.json": bundle["accounting"], "validation.json": validation}
        for name, value in documents.items():
            (staging / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        (staging / "candidates.csv").write_bytes(csv_bytes)
        (staging / "report.md").write_text(markdown(bundle), encoding="utf-8")
        files = {path.name: {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                 for path in sorted(staging.iterdir())}
        manifest = {"export_kind": "recorded_final_snapshot", "created_at": now(), "workflow_id": workflow_id,
                    "task_id": task_id, "snapshot_id": snapshot_id, "workflow_state": "completed",
                    "source_store": str(store), "source_open_mode": "read_only", "source_or_cache_modified": False,
                    "model_calls_made_by_exporter": 0, "scientific_success_claimed": False, "files": files,
                    "previous_stopped_workflows_cost_included": False}
        (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(staging, output)
    return {"output": str(output), "workflow_id": workflow_id, "snapshot_id": snapshot_id,
            "csv_rows": len(csv_rows), "snapshot_rows": len(entries), "surufatinib_status": suruf["status"],
            "workflow_known_cost_usd": bundle["accounting"]["total"]["known_cost_usd"], "scientific_success_claimed": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workflow", required=True, help="Exact completed workflow id")
    parser.add_argument("--base-url", default="http://127.0.0.1:8770", help="Workbench origin or /api/workbench URL")
    parser.add_argument("--store", type=Path, default=PROJECT_ROOT / "var" / "primary" / "store")
    parser.add_argument("--output", type=Path, required=True, help="New directory for the verified final export")
    args = parser.parse_args(argv)
    try:
        result = export(args.workflow, args.base_url, args.store, args.output)
    except (ExportError, OSError, ValueError, KeyError) as error:
        print(f"Export refused: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
