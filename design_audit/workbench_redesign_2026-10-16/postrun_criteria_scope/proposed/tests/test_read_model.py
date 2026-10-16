"""Projection boundaries, append/restart safety and historical snapshot fidelity."""

import hashlib
import json
import sqlite3

import pytest

from mas.ui.read_api import ReadAPI
from mas.ui.read_model import ProjectionNotReady, ReadModel


class Journal:
    def __init__(self, root):
        self.root = root
        root.mkdir()
        self.db = sqlite3.connect(root / "store.db")
        self.db.executescript("""
        CREATE TABLE events(stream_id TEXT,seq INTEGER,event_id TEXT UNIQUE,event_type TEXT,
          recorded_at TEXT,body TEXT,body_hash TEXT,PRIMARY KEY(stream_id,seq));
        CREATE INDEX events_type ON events(event_type);
        CREATE TABLE artifacts(artifact_id TEXT PRIMARY KEY,kind TEXT,sha256 TEXT,body TEXT,created_at TEXT);
        """)
        self.serial = 0

    def artifact(self, kind, payload):
        text = json.dumps({"kind": kind, "payload": payload}, sort_keys=True)
        digest = hashlib.sha256(text.encode()).hexdigest()
        identity = "art_" + digest[:12]
        self.db.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?,?,?)", (identity, kind, digest, text, "2026-10-16"))
        self.db.commit()
        return identity

    def event(self, stream, kind, payload=None, **fields):
        self.serial += 1
        seq = self.db.execute("SELECT coalesce(max(seq),0)+1 FROM events WHERE stream_id=?", (stream,)).fetchone()[0]
        event = dict(stream_id=stream, seq=seq, event_id=f"evt_{self.serial}", event_type=kind,
                     recorded_at=f"2026-10-16T00:00:{self.serial:02d}Z", payload=payload or {},
                     ids={"task_id": "task_a"}, visibility="default", actor=fields.pop("actor", {"id": "test"}), **fields)
        text = json.dumps(event, sort_keys=True)
        self.db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?)", (stream, seq, event["event_id"], kind, event["recorded_at"], text, hashlib.sha256(text.encode()).hexdigest()))
        self.db.commit()
        return event

    def task(self):
        ref = self.artifact("task_context", {"objective_text": "Test objective", "title": "Task A", "candidate_universe": {"members": ["a", "b"]}})
        self.event("task_a", "task.version_recorded", {"artifact_id": ref, "version": 1})
        binding = self.artifact("run_binding", {"run_purpose": "criteria_derivation"})
        self.event("run_a", "run.created", {"task_id": "task_a", "binding_artifact_id": binding}, state_to="queued")

    def change(self, operation="add", state="candidate", version=1):
        ref = self.artifact("criterion_candidate", {"attribute": {"name": "Oral evidence", "definition": "A searchable definition", "unit": "%"},
                                                  "rule": {"rule_kind": "hard_exclusion"}, "supporting_claim_ids": []})
        return self.event("task_a", "criterion.change_recorded", {"pool": True, "criterion_id": "cri_a", "version": version,
                          "artifact_id": ref, "state": state, "operation": operation, "stage": "propose" if operation == "add" else "filter",
                          "iteration": 0, "round_run_id": "run_a", "reason_text": "recorded reason", "targets_in": [], "targets_out": []})

    def snapshot(self, identity="snap_1", entries=None, **extra):
        entries = entries if entries is not None else [{"candidate_ref": f"cand_{i:03d}", "identity_labels": [f"Compound {i}"],
                     "position": i + 1, "preference_score": 1 - i / 100, "state": "provisional", "per_criterion_refs": ["asm_a"]} for i in range(60)]
        ref = self.artifact("leaderboard_snapshot", {"snapshot_id": identity, "run_id": "run_a", "candidate_entries": entries, **extra})
        self.event("run_a", "leaderboard.snapshot_published", {"task_id": "task_a", "snapshot_id": identity, "artifact_id": ref})


@pytest.fixture
def setup(tmp_path):
    journal = Journal(tmp_path / "store")
    journal.task()
    model = ReadModel(journal.root)
    yield journal, model
    journal.db.close()


def test_incremental_restart_pagination_and_legacy_qualification(setup):
    journal, model = setup
    with pytest.raises(ProjectionNotReady):
        model.tasks()
    journal.snapshot()
    first = model.sync()
    assert first["ready"]
    assert model.tasks()[0]["title"] == "Task A"
    result = model.candidates("task_a", status="all")
    assert len(result["items"]) == 50 and result["total"] == 60 and result["has_more"]
    assert result["legacy_rank_only"] and result["counts"]["qualified"] == 0
    assert model.candidates("task_a", status="qualified")["items"] == []
    assert len(model.candidates("task_a", status="all", page=2)["items"]) == 10
    assert model.candidates("task_a", status="all", q="Compound 59")["total"] == 1
    journal.change()
    model.sync()
    assert model.criteria("task_a", q="searchable")["total"] == 1
    restarted = ReadModel(journal.root)
    assert restarted.status()["source_cursor"] > first["source_cursor"]
    before = restarted.criteria("task_a")
    restarted.sync()
    assert restarted.criteria("task_a")["items"] == before["items"]
    assert len(restarted.snapshots("task_a")["items"]) == 1
    assert len(ReadAPI(model).export_csv("task_a").splitlines()) == 61
    assert "rank_note" in ReadAPI(model).export_csv("task_a").splitlines()[0]


def test_stage_boundaries_and_missing_open_are_honest(setup):
    journal, model = setup
    journal.event("run_a", "stage.opened", {"stage": "propose", "iteration": 0})
    journal.change()
    journal.event("run_a", "stage.closed", {"stage": "propose", "iteration": 0})
    journal.event("run_a", "stage.opened", {"stage": "filter", "iteration": 0})
    journal.change("remove", "filtered_out", 2)
    journal.event("run_a", "stage.closed", {"stage": "filter", "iteration": 0})
    journal.event("run_a", "stage.closed", {"stage": "merge", "iteration": 8})
    model.sync()
    stages = model.stages("task_a")["items"]
    assert [(row["before_count"], row["after_count"]) for row in stages[:2]] == [(0, 1), (1, 0)]
    assert stages[0]["added"] == 1 and stages[1]["removed"] == 1
    assert stages[0]["counts_known"] and not stages[-1]["counts_known"]
    assert stages[-1]["before_count"] is None
    assert model.criteria("task_a", stage=stages[0]["stage_id"])["total"] == 1
    assert model.criteria("task_a", stage=stages[0]["stage_id"])["items"][0]["state"] == "candidate"
    detail = model.criterion("task_a", "cri_a")
    assert len(detail["history"]) == 2
    assert detail["history"][1]["before"]["state"] == "candidate"
    assert detail["state"] == "retired" and detail["raw_state"] == "filtered_out"
    difference = model.criterion_diff("task_a", "cri_a", before=1, after=2)
    assert difference["known"] and difference["before"]["state"] == "candidate"
    assert difference["after"]["state"] == "filtered_out"


def test_failure_does_not_advance_cache_watermark(setup, monkeypatch):
    journal, model = setup
    model.sync()
    cursor = model.status()["source_cursor"]
    journal.change()
    project = model._project
    def fail(*args, **kwargs):
        project(*args, **kwargs)
        raise RuntimeError("interrupted")
    monkeypatch.setattr(model, "_project", fail)
    with pytest.raises(RuntimeError, match="interrupted"):
        model.sync()
    assert model.status()["source_cursor"] == cursor
    assert model.criteria("task_a")["items"] == []
    monkeypatch.setattr(model, "_project", project)
    model.sync()
    assert model.criteria("task_a")["total"] == 1


def test_changed_anchor_rebuilds_without_stale_rows(setup):
    journal, model = setup
    journal.change()
    model.sync()
    assert model.criteria("task_a")["total"] == 1
    journal.db.execute("DELETE FROM events WHERE event_type='criterion.change_recorded'")
    journal.db.commit()
    model.sync()
    assert model.criteria("task_a")["total"] == 0
    assert model.status()["source_event"]["event_id"] == "evt_2"


def test_only_public_artifact_bodies_are_read(setup, monkeypatch):
    journal, model = setup
    forbidden = journal.artifact("case_inheritance_snapshot", {"objective_text": "HIDDEN EVALUATOR ANSWER"})
    journal.event("case_secret", "task.version_recorded", {"artifact_id": forbidden, "version": 1})
    journal.event("task_hidden", "task.version_recorded", {"artifact_id": forbidden, "version": 1})
    journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": "attr_hidden", "version": 1, "artifact_id": forbidden})
    statements = []
    original = model._source
    from contextlib import contextmanager
    @contextmanager
    def traced():
        with original() as source:
            source.set_trace_callback(statements.append)
            yield source
    monkeypatch.setattr(model, "_source", traced)
    model.sync()
    assert len(model.tasks()) == 1 and model.criteria("task_a")["total"] == 0
    reads = [sql for sql in statements if "SELECT body FROM artifacts" in sql]
    assert not any(forbidden in sql for sql in reads)
    with model._source() as source:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            source.execute("DELETE FROM events")


def test_snapshot_detail_uses_assessments_at_publication(setup):
    journal, model = setup
    def assess(value):
        ref = journal.artifact("assessment", {"candidate_ref": "cand_a", "attribute_ref": "attr_a@v1", "rule_ref": "rule_a@v1", "value": value})
        journal.event("run_a", "candidate.assessed", {"candidate_ref": "cand_a", "attribute_ref": "attr_a@v1", "rule_ref": "rule_a@v1", "artifact_id": ref})
    assess(1)
    entries = [{"candidate_ref": "cand_a", "identity_labels": ["A"], "qualification": "qualified", "state": "recommended"}]
    journal.snapshot(entries=entries, qualification_first=True)
    assess(2)
    journal.snapshot("snap_2", entries=entries, qualification_first=True)
    model.sync()
    assert model.candidate("task_a", "cand_a", snapshot="snap_1")["assessments"][0]["value"] == 1
    assert model.candidate("task_a", "cand_a", snapshot="snap_2")["assessments"][0]["value"] == 2
    assert model.candidates("task_a", snapshot="snap_1")["counts"]["qualified"] == 1


def test_run_progress_preserves_unknown_denominator(setup):
    journal, model = setup
    journal.event("run_a", "agent.started", {"role": "reader", "request_id": "req_a"},
                  progress={"completed": 2, "planned": None, "denominator_kind": "open_ended"})
    model.sync()
    progress = model.run_progress("run_a")
    assert progress["progress"] == {"completed": 2, "planned": None, "denominator_kind": "open_ended", "scope": None}
    assert progress["active_actor"]["role"] == "reader"
    journal.event("run_a", "agent.finished", {"request_id": "req_a"})
    model.sync()
    assert model.run_progress("run_a")["active_actor"] is None


def test_new_qualification_dict_and_evidence_text_search(setup):
    journal, model = setup
    entries = [{"candidate_ref": f"cand_{state}", "qualification_state": state,
                "qualification": {"state": state, "qualified": state == "qualified", "applicable_hard_count": 2, "verified_hard_count": 2},
                "qualified": state == "qualified", "state": "provisional"}
               for state in ("qualified", "pending", "not_ready", "rejected")]
    journal.snapshot(entries=entries, qualification_policy="qualification_first_v1", evaluation_mode="staged")
    claim = journal.artifact("claim", {"source_ref": "src_doi_10.1/example", "normalized_statement": "Oral bioavailability is directly measured", "location": {"quoted_span": "Exact quote", "locator_value": "Table 2"}})
    journal.event("run_a", "evidence.admitted", {"claim_id": "claim_a", "artifact_id": claim, "source_ref": "src_doi_10.1/example"})
    model.sync()
    result = model.candidates("task_a", status="all")
    assert not result["legacy_rank_only"] and result["counts"] == {"qualified": 1, "pending": 2, "rejected": 1, "unassessed": 0, "total": 4}
    assert model.candidates("task_a")["items"][0]["hard_total"] == 2
    assert model.evidence("task_a", q="directly measured")["total"] == 1
    assert model.evidence("task_a", q="Exact quote")["items"][0]["locator"] == "Table 2"


def test_cache_rebuild_and_schema_upgrade_match_live_projection(setup):
    journal, model = setup
    journal.change()
    journal.snapshot()
    model.sync()
    expected = {"tasks": model.tasks(), "criteria": model.criteria("task_a")["items"], "candidates": model.candidates("task_a", status="all")["items"]}
    rebuilt = ReadModel(journal.root, journal.root.parent / "rebuilt.db")
    rebuilt.sync()
    assert rebuilt.tasks() == expected["tasks"]
    assert rebuilt.criteria("task_a")["items"] == expected["criteria"]
    assert rebuilt.candidates("task_a", status="all")["items"] == expected["candidates"]
    with model._cache() as cache:
        model._set_meta(cache, {"schema_version": -1})
        cache.commit()
    upgraded = ReadModel(journal.root)
    assert not upgraded.status()["ready"]
    upgraded.sync()
    assert upgraded.criteria("task_a")["items"] == expected["criteria"]


def test_registry_latest_refs_and_reduction_scope_exclude_old_pool(setup):
    journal, model = setup
    attr = journal.artifact("attribute", {"attribute_id": "attr_a", "name": "Registered endpoint", "version": 1})
    journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": "attr_a", "version": 1, "artifact_id": attr})
    for version in (1, 2):
        rule = journal.artifact("rule", {"rule_id": "rule_a", "attribute_ref": "attr_a@v1", "version": version, "rule_kind": "preference"})
        journal.event("task_a", "criterion.version_proposed", {"kind": "rule", "id": "rule_a", "version": version, "artifact_id": rule})
    journal.event("task_a", "criterion.change_recorded", {"registry": True, "registry_state": "retired", "rule_ref": "rule_a@v1", "attribute_ref": "attr_a@v1", "operation": "remove"})
    for identity, state in (("cri_older", "promoted"), ("cri_backlog", "candidate")):
        item = journal.artifact("criterion_candidate", {"attribute": {"name": identity}, "rule": {"rule_kind": "preference"}})
        promoted = {"attribute_ref": "attr_a@v1", "rule_ref": "rule_a@v1"} if state == "promoted" else {}
        journal.event("task_a", "criterion.change_recorded", {"pool": True, "criterion_id": identity, "version": 1, "artifact_id": item, "operation": "add", "state": state, "promoted_as": promoted})
    manifest = journal.artifact("registered_reduction_inputs", {"registered_inputs": [{"rule_ref": "rule_a@v2"}], "backlog_pool_refs": ["cri_backlog@v1"]})
    binding = journal.artifact("run_binding", {"operation": "registered_reduction", "source_inputs_artifact_id": manifest})
    journal.event("run_reduce", "run.created", {"task_id": "task_a", "binding_artifact_id": binding}, state_to="queued")
    item = journal.artifact("criterion_candidate", {"attribute": {"name": "Registered input"}, "rule": {"rule_kind": "preference"}, "source_registry": [{"rule_ref": "rule_a@v2"}]})
    journal.event("task_a", "criterion.change_recorded", {"pool": True, "criterion_id": "cri_input", "version": 1, "artifact_id": item, "operation": "add", "state": "candidate", "round_run_id": "run_reduce"})
    journal.event("run_reduce", "stage.opened", {"stage": "filter", "iteration": 1})
    journal.event("run_reduce", "stage.closed", {"stage": "filter", "iteration": 1})
    for version in (1, 2):
        journal.event("task_a", "human.review_requested", {"item_id": f"q{version}", "subject": {"kind": "rule_version", "id": f"rule_a@v{version}"}})
    model.sync()
    summary = model.task_summary("task_a")
    assert summary["active_registered_count"] == summary["criteria_count"] == 1
    assert summary["additional_unregistered_active_count"] == 1
    assert summary["pending_review_count"] == summary["historical_pending_review_count"] == 1
    assert model.criteria("task_a", state="active")["total"] == 2
    assert model.criteria("task_a", state="pending")["total"] == 2
    assert model.criteria("task_a", state="review")["total"] == 1
    stage = model.stages("task_a")["items"][0]
    assert stage["before_count"] == stage["after_count"] == 2
    assert stage["count_basis"] == "working_proposals"
    journal.event("task_a", "criterion.change_recorded", {"registry": True, "registry_state": "retired", "rule_ref": "rule_a@v2", "attribute_ref": "attr_a@v1", "operation": "remove"})
    model.sync()
    assert model.task_summary("task_a")["active_registered_count"] == 0
    with model._cache() as cache:
        assert cache.execute("SELECT state FROM criteria_current WHERE criterion_id='cri_older'").fetchone()[0] == "promoted"
    journal.event("task_a", "criterion.change_recorded", {"registry": True, "registry_state": "active", "rule_ref": "rule_a@v2", "attribute_ref": "attr_a@v1", "operation": "reinstate"})
    model.sync()
    assert model.task_summary("task_a")["active_registered_count"] == 1


def test_explicit_stage_counts_override_inferred_pool_and_need_no_open_record(setup):
    journal, model = setup
    journal.event("run_a", "stage.closed", {"stage": "mandated", "iteration": 0,
                  "before_count": 0, "after_count": 7, "count_basis": "active_registered_plus_unregistered_proposals"})
    model.sync()
    stage = model.stages("task_a")["items"][0]
    assert stage["before_count"] == 0 and stage["after_count"] == 7 and stage["counts_known"]
    assert stage["count_basis"] == stage["counts_basis"] == "active_registered_plus_unregistered_proposals"


@pytest.mark.parametrize("run_state,stage_state", [("paused", "paused"), ("cancelled", "interrupted"),
    ("failed", "failed"), ("unresolved", "unresolved"), ("completed", "unresolved")])
def test_open_stage_tracks_run_state_without_inventing_a_close_or_after_count(setup, run_state, stage_state):
    journal, model = setup
    journal.event("run_a", "stage.opened", {"stage": "propose", "iteration": 0})
    model.sync()
    journal.event("run_a", "run." + run_state, state_to=run_state)
    model.sync()
    row = model.stages("task_a")["items"][0]
    assert row["state"] == stage_state and row["run_state"] == run_state
    assert row["after_count"] is None and row["finished_at"] is None and not row["counts_known"]
    with model._cache() as cache:
        persisted = json.loads(cache.execute("SELECT body FROM stages").fetchone()[0])
        assert persisted["state"] == stage_state
    if run_state == "paused":
        journal.event("run_a", "run.resumed", state_to="running")
        model.sync()
        assert model.stages("task_a")["items"][0]["state"] == "running"


def test_working_scope_pins_frozen_versions_and_pending_filters_before_paging(setup):
    journal, model = setup

    def propose(name, version=1, title=None):
        attr = journal.artifact("attribute", {"attribute_id": f"attr_{name}", "version": version,
                                 "name": title or f"Endpoint {name.upper()}", "definition": "Test endpoint"})
        journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": f"attr_{name}",
                      "version": version, "artifact_id": attr})
        rule = journal.artifact("rule", {"rule_id": f"rule_{name}", "version": version,
                                 "attribute_ref": f"attr_{name}@v{version}", "rule_kind": "preference"})
        journal.event("task_a", "criterion.version_proposed", {"kind": "rule", "id": f"rule_{name}",
                      "version": version, "artifact_id": rule})

    for name in "abc":
        propose(name)
    journal.event("run_a", "stage.opened", {"stage": "propose", "iteration": 0})
    journal.change()
    journal.event("run_a", "stage.closed", {"stage": "propose", "iteration": 0})
    model.sync()
    assert model.criteria("task_a", state="working")["total"] == 4
    frozen = journal.artifact("rule_set", {"entries": [
        {"rule_ref": "rule_a@v1", "attribute_ref": "attr_a@v1"},
        {"rule_ref": "rule_b@v1", "attribute_ref": "attr_b@v1"}]})
    journal.event("task_a", "criterion.version_approved", {"artifact_id": frozen, "rule_set_ref": "rules@v1"})
    journal.event("task_a", "human.review_requested", {"item_id": "q_b", "subject": {"kind": "rule_version", "id": "rule_b@v1"}})
    propose("a", 2, "Revised endpoint A")
    model.sync()
    working = model.criteria("task_a", state="working", page_size=1)
    assert working["criteria_scope"] == "frozen" and working["rule_set_ref"] == "rules@v1"
    assert working["total"] == 2 and len(working["items"]) == 1 and working["has_more"]
    assert model.criteria("task_a", state="working", page=2, page_size=1)["total"] == 2
    assert model.criteria("task_a", state="working", q="Revised")["total"] == 0
    frozen_a = model.criteria("task_a", state="working", q="Endpoint A")["items"][0]
    assert frozen_a["criterion_id"] == "rule_a@v1" and frozen_a["version"] == 1
    assert frozen_a["detail_ref"] == "rule_a@v1"
    assert model.criterion("task_a", frozen_a["detail_ref"])["name"] == "Endpoint A"
    assert model.criterion("task_a", frozen_a["detail_ref"])["historical_version"]
    assert model.criterion("task_a", "attr_a@v1")["name"] == "Endpoint A"
    assert model.criterion("task_a", "rule_a@v2")["name"] == "Revised endpoint A"
    pending = model.criteria("task_a", state="pending", page_size=1)
    assert pending["total"] == 4 and len(pending["items"]) == 1 and pending["has_more"]
    assert model.criteria("task_a", state="pending", q="Endpoint C")["total"] == 1
    assert model.criteria("task_a", state="active")["total"] == 4  # Compatibility API still exposes the working universe.
    stage = model.stages("task_a")["items"][0]["stage_id"]
    assert model.criteria("task_a", stage=stage)["total"] == 1
    assert model.criteria("task_a", state="working", stage=stage)["total"] == 1


def test_criterion_detail_refs_pin_pool_version_and_same_version_stage_state(setup):
    journal, model = setup
    journal.event("run_a", "stage.opened", {"stage": "propose", "iteration": 0})
    journal.change()
    journal.event("run_a", "stage.closed", {"stage": "propose", "iteration": 0})
    journal.event("run_a", "stage.opened", {"stage": "filter", "iteration": 0})
    journal.change("revise", "needs_refine", 2)
    journal.event("run_a", "stage.closed", {"stage": "filter", "iteration": 0})
    model.sync()
    stages = model.stages("task_a")["items"]
    proposal = model.criteria("task_a", stage=stages[0]["stage_id"])["items"][0]
    filtered = model.criteria("task_a", stage=stages[1]["stage_id"])["items"][0]
    assert proposal["detail_ref"].startswith("change:")
    assert model.criterion("task_a", proposal["detail_ref"])["version"] == 1
    assert model.criterion("task_a", "cri_a")["version"] == 2  # Base ID keeps existing latest semantics.
    assert model.criterion("task_a", "cri_a@v1")["version"] == 1
    journal.change("remove", "filtered_out", 2)  # State can change without changing item version.
    model.sync()
    current = model.criterion("task_a", "cri_a@v2")
    assert current["state"] == "retired" and current["raw_state"] == "filtered_out"
    old = model.criterion("task_a", filtered["detail_ref"])
    assert old["version"] == 2 and old["state"] == "needs_refine" and old["historical_version"]
    assert old["current_ref"] == "cri_a@v2"
    with pytest.raises(KeyError):
        model.criterion("task_a", "cri_a@v999")


def test_mandated_added_uses_created_bindings_and_repairs_legacy_cache_on_read(setup):
    journal, model = setup
    journal.event("run_a", "stage.opened", {"stage": "mandated", "iteration": 0,
                  "before_count": 0, "count_basis": "active_registered_plus_unregistered_proposals"})
    refs = []
    for index in range(6):
        attr_ref, rule_ref = f"attr_required_{index}@v1", f"rule_required_{index}@v1"
        attr = journal.artifact("attribute", {"attribute_id": attr_ref.split("@v")[0], "version": 1,
            "name": f"Task requirement {index}", "proposed_by": {"role": "adapter_template"},
            "derived_from": {"task_context": "task_a@v1", "field": f"scope_entities[{index}]"}})
        journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": attr_ref.split("@v")[0],
            "version": 1, "artifact_id": attr}, actor={"kind": "system", "id": "objective-criteria"})
        rule = journal.artifact("rule", {"rule_id": rule_ref.split("@v")[0], "version": 1,
            "attribute_ref": attr_ref, "rule_kind": "preference"})
        journal.event("task_a", "criterion.version_proposed", {"kind": "rule", "id": rule_ref.split("@v")[0],
            "version": 1, "artifact_id": rule}, actor={"kind": "system", "id": "objective-criteria"})
        refs.append({"attribute_ref": attr_ref, "rule_ref": rule_ref})
    journal.event("run_a", "stage.closed", {"stage": "mandated", "iteration": 0, "result": refs,
                  "before_count": 0, "after_count": 6, "count_basis": "active_registered_plus_unregistered_proposals"})
    model.sync()
    stage = model.stages("task_a")["items"][0]
    assert stage["before_count"] == 0 and stage["after_count"] == stage["added"] == 6
    assert stage["added_count_basis"] == "recorded_result_and_task_binding_events"
    assert len(stage["added_event_refs"]) == 6  # Six conditions, not twelve attribute/rule events.
    with model._cache() as db:
        saved = json.loads(db.execute("SELECT body FROM stages WHERE stage_id=?", (stage["stage_id"],)).fetchone()[0])
        saved.pop("mandated_result_refs")
        saved["added"] = 0
        db.execute("UPDATE stages SET body=? WHERE stage_id=?", (json.dumps(saved), stage["stage_id"]))
        db.commit()
    legacy = model.stages("task_a")["items"][0]
    assert legacy["added"] == 6 and legacy["added_count_basis"] == "task_binding_events_between_stage_boundaries"
    journal.event("run_a", "stage.closed", {"stage": "mandated", "iteration": 9, "result": refs})
    model.sync()
    unknown = model.stages("task_a")["items"][-1]
    assert unknown["added"] is None and unknown["added_count_basis"] == "unavailable_stage_bounds"


def test_lineage_nodes_resolve_saved_versions_and_preserve_new_child_history(setup):
    journal, model = setup

    def proposal(identity, name, definition, version=1, operation="add", state="candidate", parents=(), children=()):
        ref = journal.artifact("criterion_candidate", {"attribute": {"name": name, "definition": definition},
            "rule": {"rule_kind": "preference"}, "supporting_claim_ids": []})
        journal.event("task_a", "criterion.change_recorded", {"pool": True, "criterion_id": identity,
            "version": version, "artifact_id": ref, "state": state, "operation": operation, "stage": "merge",
            "iteration": 0, "round_run_id": "run_a", "targets_in": list(parents), "targets_out": list(children)})

    proposal("cri_left", "First original", "First original definition")
    proposal("cri_right", "Second original", "Second original definition")
    proposal("cri_child", "Merged criterion", "Combined definition", operation="merge",
             parents=("cri_left@v1", "cri_right@v1", "cri_missing@v1"))
    proposal("cri_left", "First original", "First original definition", operation="merge", state="merged_away",
             children=("cri_child@v1",))
    proposal("cri_left", "Later revision", "Must not replace original", version=2, operation="revise")
    model.sync()
    detail = model.criterion("task_a", "cri_child")
    nodes = {node["id"]: node for node in detail["lineage"]["nodes"]}
    first, second = nodes["cri_left@v1"], nodes["cri_right@v1"]
    assert first["name"] == "First original" and first["definition"] == "First original definition"
    assert first["version"] == 1 and first["state"] == "merged_away"
    assert second["name"] == "Second original" and second["definition"] == "Second original definition"
    assert nodes["cri_missing@v1"]["missing"] and "name" not in nodes["cri_missing@v1"]
    assert {edge["source"] for edge in detail["lineage"]["edges"]} == {"cri_left@v1", "cri_right@v1", "cri_missing@v1"}
    assert all(edge["target"] == "cri_child@v1" for edge in detail["lineage"]["edges"])
    assert len(detail["history"]) == 1 and detail["history"][0]["before"] is None
    parent_detail = model.criterion("task_a", first["detail_ref"])
    assert parent_detail["version"] == 1 and parent_detail["definition"] == first["definition"]
    child_node = next(node for node in parent_detail["lineage"]["nodes"] if node.get("relation") == "child")
    assert child_node["name"] == "Merged criterion" and child_node["detail_ref"] == "cri_child@v1"
