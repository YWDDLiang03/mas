"""Run the local workbench's real HTTP workflow, recording its control channel.

This is API integration verification, not a claim of GUI interaction. Steps are
explicit and checkpointed so a timeout cannot silently start another experiment.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "var/acceptance-mid/state.json"
BASE = "http://127.0.0.1:8768"


def save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(STATE)


def get(path, *, endpoint=None, **params):
    response = requests.get((endpoint or BASE) + path, params=params, timeout=40)
    response.raise_for_status()
    return response


def post(payload):
    page = get("/operations")
    token = re.search(r'const token=("[^"\r\n]*");', page.text)
    if not token:
        raise RuntimeError("the operation page did not provide its local operation token; nothing was submitted")
    response = requests.post(BASE + "/api/operations", json=payload,
                             headers={"Origin": BASE, "X-MAS-Operation-Token": json.loads(token.group(1))},
                             timeout=40)
    if not response.ok:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
    return response.json()


def main():
    global BASE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("configure", "inherit", "reduce", "supplement", "freeze", "run", "check", "export"))
    parser.add_argument("--base-url", default=BASE, help="local workbench used for new operations")
    args = parser.parse_args()
    BASE = args.base_url.rstrip("/")
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {
        "control_channel": "local_workbench_http_integration", "gui_click_performed": False,
        "base_url": BASE, "source_task": "task_01M50JQYYQAMPBQTQ0N8YNQT22", "jobs": {}, "steps": []}
    if args.step == "configure":
        updates = {"search.volume": "mid", "textbook.volume": "mid", "assess.workers": 4,
                   "search.breadth": 4, "search.depth": 2, "read.max_papers_full_read": 40,
                   "budget.usd_max": 10.0, "budget.on_exhaust": "finalize_partial", "interaction.mode": "autonomous",
                   "rank.coverage_floor": 0.5, "rank.mandated_coverage_floor": 1.0}
        result = post({"action": "save_settings", "settings": updates})
        assert result["preset"] == "standard"
        actual = {field["key"]: field["value"] for field in result["fields"]}
        assert all(actual[key] == value for key, value in updates.items())
        state["configuration"] = result
        post({"action": "select_task", "task_id": state.get("task_id", state["source_task"])})
        state["steps"].append({"step": "configure", "base_url": BASE, "preset": result["preset"], "config_hash": result["config_hash"]})
        save(state)
        print(json.dumps(state["steps"][-1]))
        return
    if args.step == "check":
        snapshots = {}
        for step, recorded in state["jobs"].items():
            endpoint = recorded.get("operation_base_url", state["base_url"])
            if recorded.get("status") in ("completed", "failed", "cancelled"):
                current = recorded
            else:
                if endpoint not in snapshots:
                    snapshots[endpoint] = {job["job_id"]: job for job in get("/api/operations", endpoint=endpoint).json()["jobs"]}
                if recorded["job_id"] not in snapshots[endpoint]:
                    print(json.dumps({"step": step, "job_id": recorded["job_id"], "status": "not_in_recorded_service"}))
                    continue
                current = dict(snapshots[endpoint][recorded["job_id"]], operation_base_url=endpoint)
            state["jobs"][step] = current
            if step == "inherit" and current["status"] == "completed":
                match = re.search(r"\btask_[0-9A-Z]{26}\b", current.get("log_tail", ""))
                if match:
                    state["task_id"] = match.group()
                    if not state.get("inherited_task_selected"):
                        post({"action": "select_task", "task_id": state["task_id"]})
                        state["inherited_task_selected"] = True
            if step == "freeze" and current["status"] == "completed":
                frozen = json.loads(current["log_tail"])
                state["frozen"] = frozen
            if step == "run" and current.get("run_id"):
                state["run_id"] = current["run_id"]
            print(json.dumps({"step": step, **{key: current.get(key) for key in
                              ("job_id", "status", "exit_code", "run_id", "pid", "log_tail")}}, ensure_ascii=False))
        save(state)
        return
    if args.step == "export":
        task_id = state["task_id"]
        board = get("/api/leaderboard", task=task_id, top=1000000).json()
        snapshot_id = board["snapshot_id"]
        expected = board["members_compared"]
        identities = [row["candidate_ref"] for row in board["rows"]]
        if len(identities) != expected or len(set(identities)) != expected:
            raise RuntimeError("the JSON leaderboard does not contain every candidate exactly once")
        STATE.with_name("leaderboard.json").write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")
        response = get("/export/leaderboard.csv", task=task_id, snapshot=snapshot_id)
        STATE.with_name("leaderboard.csv").write_bytes(response.content)
        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        if ([row["candidate_ref"] for row in rows] != identities
                or any(row["snapshot_id"] != snapshot_id or row["rules_ref"] != board["rules@v"] for row in rows)):
            raise RuntimeError("CSV rows differ from the pinned JSON leaderboard")
        state["exported_rows"] = len(rows)
        state["export_verification"] = {
            "snapshot_id": snapshot_id, "rules_ref": board["rules@v"], "run_id": board["run_id"],
            "expected_candidates": expected, "unique_candidates": len(set(identities)),
            "json_csv_order_matches": True, "csv_sha256": hashlib.sha256(response.content).hexdigest(),
        }
        save(state)
        print(json.dumps({"task_id": task_id, "exported_rows": len(rows), **state["export_verification"]}))
        return
    if args.step in state["jobs"]:
        raise RuntimeError(f"{args.step} was already submitted; inspect its recorded job instead of repeating it")
    if state.get("pending_request"):
        raise RuntimeError("an earlier submission has no recorded outcome; inspect its actual operation before submitting again")
    if args.step == "inherit":
        payload = {"action": "task_inherit", "task_id": state["source_task"], "reason":
                   "Mid-level workbench acceptance: reduce inherited registered criteria, retain all provenance, attach verified measurements, and run the complete 3177-candidate universe. Prior A and B snapshots remain unchanged; no CQA remapping or numeric reduction quota."}
    else:
        payload = {"task_id": state["task_id"]}
        if args.step == "reduce":
            payload.update(action="reduce_registered", reason=
                           "Systematically reduce the complete inherited registry on its existing evidence at standard/mid settings. Merge genuine redundancy and retire unsupported or redundant items with reasons; preserve distinct endpoints and unresolved items. Quantity is a soft preference, never a forced cutoff.")
        elif args.step == "supplement":
            payload.update(action="supplement_attach", supplement_ref="art_ae77c0685a78")
        elif args.step == "freeze":
            payload.update(action="freeze_profile", primary_board="windows-mid-reduced-with-verified-evidence-2026-10-16",
                           rationale="Prospective workflow acceptance after evidence-preserving registered reduction and verified source attachment; all candidates retain the same identity scope and lookup rules.",
                           expected_effect="Use the active reduced criteria, measured/curated/derived values and bound verified supplements. Keep missing values unknown, rank coverage at 0.5, and report mandated eligibility separately at 1.0. The targeted supplement selection is exploratory and recorded.",
                           defer_capabilities=["predicted_property_lookup", "literature_retrieval"],
                           defer_reason="Reuse inherited data plus already span-verified measurements; defer new literature crawling and predictions for this full-universe mid-level acceptance run.")
        elif args.step == "run":
            payload.update(action="run_start", rule_set_ref=state["frozen"]["rule_set_ref"],
                           measurement_profile=state["frozen"]["measurement_profile_ref"], workers=4)
    state["pending_request"] = {"step": args.step, "payload": payload}
    save(state)
    job = post(payload)
    job["operation_base_url"] = BASE
    state["jobs"][args.step] = job
    state.pop("pending_request", None)
    save(state)
    print(json.dumps({"step": args.step, "job_id": job["job_id"], "status": job["status"], "pid": job["pid"]}))


if __name__ == "__main__":
    main()
