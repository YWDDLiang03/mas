"""Temporary-store integration probe. Uses scripted models and forbids network.

Run from the project root with PYTHONPATH=src;tests. No primary store is opened.
"""
from __future__ import annotations

import json
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mas.core import config, criteria, derivation_run, existing_research, ledger, task
from mas.core.journal import actor
from mas.core.runtime import Core
from mas.ui.read_model import ReadModel
from mas.ui.workflows import WorkflowManager
from test_criteria_pool import lit_attribute, proposal, roster_for


def run_audit(scenario="complete"):
    calls = []
    source_claim = None
    manager = workflow = None

    def script(request):
        required = set((request.response_schema or {}).get("required") or [])
        calls.append({"role": request.role, "question": request.metadata.get("question"), "required": sorted(required)})
        if scenario == "stop" and str(request.metadata.get("question") or "").startswith("propose pool"):
            manager.command(workflow["workflow_id"], "stop")
        if "title" in required:
            return {"title": "Offline audit", "objective": "Find orally administered compounds", "mode": "conditional",
                    "targets": [], "constraints": [{"text": "oral administration", "kind": "route", "hardness": "hard"}], "questions": []}
        if "proposals" in required:
            return {"proposals": [proposal(lit_attribute("Oral bioavailability", "%"), source_claim)], "considered_and_rejected": []}
        if "findings" in required:
            return {"findings": []}
        if "items" in required:
            return {"items": [{"index": 0, "action": "keep", "reason": "One distinct measured endpoint"}]}
        if "revisions" in required:
            return {"revisions": []}
        if "decisions" in required:
            return {"decisions": []}
        raise AssertionError("Unexpected offline model schema " + str(required))

    with tempfile.TemporaryDirectory(prefix="mas-wiring-audit-") as temporary:
        root = Path(temporary)
        library = root / "universe_audit.json"
        library.write_text(json.dumps({"source": "synthetic audit", "retrieved_at": "2026-10-16", "universe": [
            {"inchikey": "KEY_A", "name": "Compound A", "chembl_id": "CHEMBL_A", "smiles": "C",
             "fields": {"oral": True, "first_approval": 2020}}]}), encoding="utf-8")
        roster = roster_for(script)
        if scenario == "budget":
            for adapter in roster.adapters.values():
                original = adapter.complete
                def charged(request, complete=original):
                    response = complete(request)
                    response.cost_usd, response.cost_status = .6, "estimated"
                    response.usage, response.usage_status = {"input_tokens": 10, "output_tokens": 10}, "recorded"
                    return response
                adapter.complete = charged
        overrides = {"criteria.inner_iterations": 1, "criteria.stall_rounds": 1, "sources.cache_dir": str(root / "cache")}
        settings = config.resolve(preset="standard", overrides=overrides, environ={})
        with Core.open(root / "store") as core:
            source_task, _ = task.record_version(core, {"objective_text": "Source oral pharmacology", "mode": "exploratory",
                "candidate_universe": {"members": ["KEY_A"]},
                "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True}},
                by=actor("agent", "offline-audit", "operator"))
            source_run, ids, _ = derivation_run._open_run(core, source_task, by=actor("agent", "offline-audit", "operator"),
                roster=roster, parents=[], continues_run_id=None, implementation={"audit": "offline"},
                purpose_note="synthetic source", settings=settings)
            text = "Oral bioavailability of 40 percent supports adequate exposure"
            source_claim = ledger.record_claim(core, source_run, {"source_ref": "src_doi_10.1/synthetic",
                "normalized_statement": text, "claim_text": text, "attribute_hint": "oral bioavailability",
                "location": {"location_kind": "paragraph", "locator_value": "p1", "quoted_span": text,
                             "span_checked_against_source": True},
                "reading_depth": "full_text", "determination_basis": "measured", "evidence_kind": "peer_reviewed",
                "value": 40, "unit": "%"}, by=actor("agent", "offline-audit", "reader"),
                admission_state="admitted", admission_reasons=["synthetic audit"], ids=ids)
            derivation_run._emit(core, source_run, "run.completed", ids=ids, state_to="completed")
            pin_count = len(existing_research.pin_evidence(core, source_task)[1])
        operations = SimpleNamespace(store_root=root / "store", working_directory=Path.cwd(), cli_options=[],
            saved_overrides=overrides, settings=settings, initiator={"kind": "agent", "id": "offline-audit"},
            current_task=None, _save_state=lambda: None)
        model = ReadModel(operations.store_root)
        manager = WorkflowManager(operations, model)
        manager._launch = lambda workflow_id: None
        workflow = manager.start({"input": {"objective": "Find oral compounds", "source_task_id": source_task,
            "library_id": library.name, "evidence_mode": "existing_only", "evaluation_mode": "staged",
            "workers": 1, "budget_usd": 1}, "idempotency_key": "offline-audit"})
        manager._threads[workflow["workflow_id"]] = threading.current_thread()
        with patch("mas.core.investigation.roster_for", return_value=roster), \
             patch("mas.cli.main._implementation", return_value={"audit": "offline"}), \
             patch("requests.sessions.Session.request", side_effect=AssertionError("Offline audit forbids network")):
            manager._work(workflow["workflow_id"])
        result = manager.get(workflow["workflow_id"])
        report = {"scenario": scenario, "state": result["state"], "workflow": result, "pin_claim_count": pin_count,
                  "scripted_model_calls": calls, "network_allowed": False, "primary_store_opened": False}
        with Core.open(root / "store", read_only=True) as core:
            if result.get("task_id"):
                inventory = criteria.registry_inventory(core, result["task_id"])
                report["registry_counts"] = {key: value for key, value in inventory.items() if not isinstance(value, list)}
                report["public_event_counts"] = dict(core.store.db.execute("SELECT event_type,count(*) FROM events GROUP BY event_type"))
                if result.get("snapshot_id"):
                    from mas.core import leaderboard
                    snapshot = leaderboard.snapshots(core, result["task_id"])[-1]
                    report["snapshot"] = {key: snapshot.get(key) for key in ("qualification_policy", "readiness", "evaluation_mode", "result_kind")}
                    report["candidate_qualifications"] = [{key: entry.get(key) for key in ("candidate_ref", "qualification", "position", "preference_score")} for entry in snapshot["candidate_entries"]]
        return report


if __name__ == "__main__":
    report = {"scenarios": [run_audit(scenario) for scenario in ("complete", "stop", "budget")]}
    expected = {"complete": "completed", "stop": "cancelled", "budget": "unresolved"}
    report["all_expected_states"] = all(scenario["state"] == expected[scenario["scenario"]] for scenario in report["scenarios"])
    output = Path("design_audit/workbench_redesign_2026-10-16/offline_wiring_audit.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"all_expected_states": report["all_expected_states"], "scenarios": [
        {"scenario": row["scenario"], "state": row["state"], "error": row["workflow"].get("error"),
         "model_calls": len(row["scripted_model_calls"]), "budget": row["workflow"]["budget"],
         "events": row.get("public_event_counts")} for row in report["scenarios"]]}, ensure_ascii=False, indent=2))
