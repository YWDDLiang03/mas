"""Projection boundaries, append/restart safety and historical snapshot fidelity."""

import hashlib
import csv
import io
import json
import sqlite3

import pytest

from mas.ui.read_api import ReadAPI
from mas.ui.read_model import ProjectionNotReady, ReadModel
from mas.core.assessor import qualification


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


def test_historical_context_method_note_preserves_raw_and_uses_only_prior_exact_admitted_claims(setup):
    journal, model = setup
    def claim(name, unit='log units'):
        value = {'claim_id': f'claim_{name}', 'source_ref': 'src_saved', 'candidate_ref': 'cand_a',
                 'attribute_ref': f'attr_{name}@v1', 'admission_state': 'admitted', 'evidence_kind': 'model_prediction',
                 'determination_basis': 'predicted', 'value': 2.5, 'unit': unit}
        ref = journal.artifact('claim', value)
        journal.event('run_a', 'evidence.admitted', dict(value, artifact_id=ref))
    for name in ('method', 'late', 'wrong_unit'):
        attr = journal.artifact('attribute', {'attribute_id': f'attr_{name}', 'version': 1, 'name': name,
            'measurement_kind': 'quantitative', 'unit': 'log units', 'aggregation': 'median',
            'acceptable_value_sources': ['model_prediction'], 'acceptable_determination_bases': ['predicted']})
        rule = journal.artifact('rule', {'rule_id': f'rule_{name}', 'version': 1, 'attribute_ref': f'attr_{name}@v1',
            'rule_kind': 'exploratory_consideration', 'predicate_form': 'qualitative_judgment', 'cutoff': None})
        journal.event('task_a', 'criterion.version_proposed', {'kind': 'attribute', 'id': f'attr_{name}', 'version': 1, 'artifact_id': attr})
        journal.event('task_a', 'criterion.version_proposed', {'kind': 'rule', 'id': f'rule_{name}', 'version': 1, 'artifact_id': rule})
        if name != 'late':
            claim(name, 'different scale' if name == 'wrong_unit' else 'log units')
        reason = journal.artifact('reason', {'reason_text': 'Historical no admitted claim message'})
        cell = journal.artifact('assessment', {'candidate_ref': 'cand_a', 'attribute_ref': f'attr_{name}@v1',
            'rule_ref': f'rule_{name}@v1', 'rule_kind': 'exploratory_consideration', 'verdict': 'unknown_missing',
            'value': None, 'unit': 'log units', 'determination_basis': 'absent', 'value_source_claim_refs': []})
        journal.event('run_a', 'candidate.assessed', {'candidate_ref': 'cand_a', 'attribute_ref': f'attr_{name}@v1',
            'rule_ref': f'rule_{name}@v1', 'artifact_id': cell, 'reason_artifact_id': reason})
    raw = {'candidate_ref': 'cand_a', 'identity_labels': ['A'], 'qualification': 'qualified',
           'position': 1, 'preference_score': .75, 'state': 'recommended'}
    journal.snapshot(entries=[raw], qualification_first=True)
    claim('late')
    model.sync()
    count = journal.db.execute('SELECT count(*) FROM events').fetchone()[0]
    result = model.candidate('task_a', 'cand_a', snapshot='snap_1')
    first, late, wrong = result['assessments']
    assert first['verdict'] == 'unknown_missing' and first['reason'] == 'Historical no admitted claim message'
    assert first['value'] is None and first['evidence'] == [] and first['basis'] == 'absent'
    assert first['interpretation']['display_verdict'] == 'unknown_unresolvable'
    assert first['interpretation']['claim_refs'] == ['claim_method']
    assert first['raw']['assessment']['verdict'] == 'unknown_missing'
    assert first['raw']['reason']['reason_text'] == first['reason']
    assert 'interpretation' not in late and 'interpretation' not in wrong
    assert [row['claim_id'] for row in result['evidence']] == ['claim_method']
    assert result['raw'] == raw and result['position'] == 1 and result['score'] == .75
    assert journal.db.execute('SELECT count(*) FROM events').fetchone()[0] == count


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


def test_closed_stage_removes_stale_run_state_and_matches_a_cold_rebuild(setup, tmp_path):
    journal, model = setup
    journal.event("run_a", "stage.opened", {"stage": "propose", "iteration": 0, "before_count": 2})
    model.sync()
    journal.event("run_a", "run.started", state_to="running")
    model.sync()
    opened = model.stages("task_a")["items"][0]
    assert opened["run_state"] == opened["state"] == "running"
    journal.event("run_a", "stage.closed", {"stage": "propose", "iteration": 0,
                  "before_count": 2, "after_count": 3}, state_to="completed")
    model.sync()
    with model._cache() as db:
        row = db.execute("SELECT stage_id,body FROM stages").fetchone()
        body = json.loads(row["body"])
        assert "run_state" not in body  # New stage closures do not persist an open-stage state.
        body["run_state"] = "running"
        db.execute("UPDATE stages SET body=? WHERE stage_id=?", (json.dumps(body), row["stage_id"]))
        db.commit()
    closed = model.stages("task_a")["items"][0]
    assert "run_state" not in closed and closed["state"] == "completed"
    assert closed["before_count"] == 2 and closed["after_count"] == 3
    assert closed["started_at"] == opened["started_at"] and closed["finished_at"]
    rebuilt = ReadModel(journal.root, cache_path=tmp_path / "rebuilt-read.db")
    rebuilt.sync()
    assert rebuilt.stages("task_a") == model.stages("task_a")


def test_reference_expression_indexes_upgrade_an_existing_cache_without_rebuild(setup):
    journal, model = setup
    journal.change()
    model.sync()
    index_queries = {
        "criteria_listing_rule_ref": ("SELECT * FROM criteria_listing WHERE task_id=? AND json_extract(body,'$.rule_ref')=?", "rule_test@v1"),
        "criteria_listing_attribute_ref": ("SELECT * FROM criteria_listing WHERE task_id=? AND json_extract(body,'$.attribute_ref')=?", "attr_test@v1"),
        "changes_id": ("SELECT * FROM criterion_changes WHERE task_id=? AND json_extract(body,'$.id')=?", "evt_test"),
    }
    with model._cache() as db:
        before = model._meta(db)
        rows = list(db.execute("SELECT * FROM criteria_listing ORDER BY criterion_id"))
        for name in index_queries:
            db.execute(f"DROP INDEX {name}")
        db.commit()
    upgraded = ReadModel(journal.root, cache_path=model.cache_path)
    with upgraded._cache() as db:
        assert upgraded._meta(db) == before
        assert [tuple(row) for row in db.execute("SELECT * FROM criteria_listing ORDER BY criterion_id")] == [tuple(row) for row in rows]
        for name, (query, ref) in index_queries.items():
            plan = list(db.execute("EXPLAIN QUERY PLAN " + query, ("task_a", ref)))
            assert any(name in row[3] for row in plan), plan


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



def test_registered_history_follows_exact_supersedes_without_mixing_record_kinds(setup):
    journal, model = setup

    def record(kind, base, version, **values):
        payload = {f"{kind}_id": base, "version": version, **values}
        ref = journal.artifact(kind, payload)
        journal.event("task_a", "criterion.version_proposed", {"kind": kind, "id": base,
                      "version": version, "artifact_id": ref})

    record("attribute", "attr_endpoint", 1, name="Endpoint", definition="Original definition",
           direction="higher_better", unit="log reciprocal", rationale="Original rationale")
    record("rule", "rule_endpoint", 1, attribute_ref="attr_endpoint@v1", rule_kind="preference",
           predicate_form="ordering")
    revision = {"source_attribute_ref": "attr_endpoint@v1", "source_rule_ref": "rule_endpoint@v1",
                "reason": "Correct the direction before evaluation", "changes": {"attribute": {"direction": "lower_better"}}}
    record("attribute", "attr_endpoint", 2, name="Endpoint", definition="Corrected definition", unit="log reciprocal",
           direction="lower_better", supersedes="attr_endpoint@v1", rationale="Original rationale",
           workbench_revision=revision)
    record("rule", "rule_endpoint", 2, attribute_ref="attr_endpoint@v2", rule_kind="preference",
           predicate_form="ordering", supersedes="rule_endpoint@v1", workbench_revision=revision)
    # A subsequent version exists, but opening v2 must not silently include its future.
    record("attribute", "attr_endpoint", 3, name="Endpoint", definition="Later definition", unit="log reciprocal",
           direction="lower_better", supersedes="attr_endpoint@v2", rationale="Later rationale", workbench_revision=revision)
    record("rule", "rule_endpoint", 3, attribute_ref="attr_endpoint@v3", rule_kind="preference",
           predicate_form="ordering", supersedes="rule_endpoint@v2", workbench_revision=revision)
    model.sync()
    first = model.criterion("task_a", "rule_endpoint@v1")
    revised = model.criterion("task_a", "rule_endpoint@v2")
    history = {change["ref"]: change for change in revised["history"]}
    assert set(history) == {"attr_endpoint@v1", "rule_endpoint@v1", "attr_endpoint@v2", "rule_endpoint@v2"}
    assert {change["ref"] for change in first["history"]} == {"attr_endpoint@v1", "rule_endpoint@v1"}
    attr, rule = history["attr_endpoint@v2"], history["rule_endpoint@v2"]
    assert attr["before"]["direction"] == "higher_better" and attr["after"]["direction"] == "lower_better"
    assert attr["before"]["definition"] == "Original definition" and attr["after"]["definition"] == "Corrected definition"
    assert "rule_kind" not in attr["before"] and "rule_kind" not in attr["after"]
    assert rule["before"]["attribute_ref"] == "attr_endpoint@v1" and rule["after"]["attribute_ref"] == "attr_endpoint@v2"
    assert "direction" not in rule["before"] and "direction" not in rule["after"]
    assert attr["reason"] == rule["reason"] == revision["reason"]
    assert attr["reason_source"] == rule["reason_source"] == "workbench_revision"
    assert not attr["predecessor_missing"] and not rule["predecessor_missing"]
    latest = {change["ref"]: change for change in model.criterion("task_a", "rule_endpoint@v3")["history"]}
    assert latest["attr_endpoint@v3"]["reason"] == "Later rationale"  # Copied v2 metadata is not a new reason.
    assert latest["rule_endpoint@v3"]["reason"] is None


def test_registered_history_keeps_missing_predecessor_unknown(setup):
    journal, model = setup
    attr = journal.artifact("attribute", {"attribute_id": "attr_orphan", "version": 2,
        "name": "Orphan endpoint", "direction": "lower_better", "supersedes": "attr_orphan@v1"})
    journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": "attr_orphan", "version": 2, "artifact_id": attr})
    rule = journal.artifact("rule", {"rule_id": "rule_orphan", "version": 2, "attribute_ref": "attr_orphan@v2",
        "rule_kind": "preference", "supersedes": "rule_orphan@v1"})
    journal.event("task_a", "criterion.version_proposed", {"kind": "rule", "id": "rule_orphan", "version": 2, "artifact_id": rule})
    model.sync()
    history = model.criterion("task_a", "rule_orphan@v2")["history"]
    assert len(history) == 2
    assert all(change["before"] is None and change["predecessor_missing"] and change["reason"] is None for change in history)
    assert {change["before_ref"] for change in history} == {"attr_orphan@v1", "rule_orphan@v1"}



def test_latest_evaluation_status_preserves_registry_history_and_frozen_reasons(setup):
    journal, model = setup

    def register(name, version=1):
        attribute = journal.artifact("attribute", {"attribute_id": f"attr_{name}", "version": version, "name": name})
        journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": f"attr_{name}", "version": version, "artifact_id": attribute})
        rule = journal.artifact("rule", {"rule_id": f"rule_{name}", "version": version, "attribute_ref": f"attr_{name}@v{version}", "rule_kind": "preference"})
        journal.event("task_a", "criterion.version_proposed", {"kind": "rule", "id": f"rule_{name}", "version": version, "artifact_id": rule})

    register("mw")
    register("anchor")
    model.sync()
    assert model.criterion("task_a", "rule_mw@v1")["evaluation"]["state"] == "not_prepared"
    first = journal.artifact("rule_set", {"entries": [{"rule_ref": "rule_mw@v1", "attribute_ref": "attr_mw@v1"}]})
    journal.event("task_a", "criterion.version_approved", {"rule_set_ref": "rules@v1", "artifact_id": first})
    journal.snapshot(identity="before_revision", entries=[], **{"rules@v": "rules@v1"})
    register("mw", 2)
    record = {"rule_ref": "rule_mw@v2", "attribute_ref": "attr_mw@v2", "scope": "rule", "reason_kind": "unresolved_review",
        "reason": "Review is unresolved for the recorded cutoff", "review_item_refs": ["q_mw"],
        "reviews": [{"item_ref": "q_mw", "state": "open", "attempts": [{"attempt_ref": "art_attempt", "outcome": "unresolved", "reason_text": "Actual machine reason"}]}]}
    frozen = journal.artifact("rule_set", {"entries": [{"rule_ref": "rule_anchor@v1", "attribute_ref": "attr_anchor@v1"}], "deferred": [record]})
    journal.event("task_a", "human.review_requested", {"item_id": "q_mw", "subject": {"kind": "rule_version", "id": "rule_mw@v2"}})
    journal.event("task_a", "criterion.version_approved", {"rule_set_ref": "rules@v2", "artifact_id": frozen, "pending": ["rule_mw@v2"]})
    journal.event("run_a", "stage.opened", {"stage": "propose", "iteration": 0})
    change = journal.change()
    journal.event("run_a", "stage.closed", {"stage": "propose", "iteration": 0})
    model.sync()
    pending = model.criteria("task_a", state="pending", q="mw")["items"][0]
    assert pending["state"] == "active"  # Registry status is not rewritten.
    assert pending["evaluation"]["state"] == "deferred" and pending["evaluation"]["reason"] == record["reason"]
    assert pending["evaluation"]["basis"]["review_item_refs"] == ["q_mw"]
    detail = model.criterion("task_a", "rule_mw@v2")
    assert detail["evaluation"]["basis"]["frozen_records"] == [record]
    assert detail["evaluation"]["basis"]["attempt_refs"] == ["art_attempt"]
    assert model.criterion("task_a", "rule_anchor@v1")["evaluation"]["state"] == "enabled"
    historical = model.criterion("task_a", "rule_mw@v1")["evaluation"]
    assert historical == {"state": "historical", "scope": "saved_version", "reason_kind": "historical_view"}
    pinned = model.criterion("task_a", "rule_mw@v1", snapshot="before_revision")["evaluation"]
    assert pinned["state"] == "enabled" and pinned["rule_set_ref"] == "rules@v1"
    assert pinned["scope"] == "selected_evaluation"
    stage = model.criterion("task_a", "change:" + change["event_id"])["evaluation"]
    assert stage["state"] == "historical" and stage["scope"] == "stage_snapshot"
    assert model.criteria("task_a", state="working")["total"] == 1

def test_frozen_role_summary_separates_core_context_and_pending(setup):
    journal, model = setup
    entries = []
    for index, role in enumerate(('hard_exclusion', 'preference', 'exploratory_consideration', 'preference')):
        aid, rid = f'attr_role_{index}', f'rule_role_{index}'
        attr = journal.artifact('attribute', {'attribute_id': aid, 'name': aid, 'version': 1})
        rule = journal.artifact('rule', {'rule_id': rid, 'attribute_ref': aid + '@v1', 'version': 1, 'rule_kind': role})
        journal.event('task_a', 'criterion.version_proposed', {'kind': 'attribute', 'id': aid, 'version': 1, 'artifact_id': attr})
        journal.event('task_a', 'criterion.version_proposed', {'kind': 'rule', 'id': rid, 'version': 1, 'artifact_id': rule})
        entries.append({'rule_ref': rid + '@v1', 'attribute_ref': aid + '@v1', 'rule_kind': role})
    frozen = journal.artifact('rule_set', {'entries': entries[:3], 'deferred': [entries[3]]})
    journal.event('task_a', 'criterion.version_approved', {'rule_set_ref': 'rules@v1', 'artifact_id': frozen})
    journal.change()
    model.sync()
    summary = model.task_summary('task_a')
    assert summary['scoring_count'] == 3
    assert summary['enabled_core_count'] == 2
    assert summary['enabled_hard_count'] == summary['enabled_preference_count'] == summary['enabled_context_count'] == 1
    assert summary['not_enabled_count'] == 2  # one deferred registry entry, one unregistered proposal
    with model._cache() as cache:
        model._set_meta(cache, {'criterion_role_summary_version': 0})
        cache.execute("UPDATE task_summaries SET body=json_remove(body,'$.enabled_core_count')")
        cache.commit()
    model.sync()  # refresh these summaries even without a new scientific event
    assert model.task_summary('task_a')['enabled_core_count'] == 2


def test_selection_v3_profiles_filters_csv_and_cache_backfill(setup):
    journal, model = setup
    for name, role in (("size", "hard_exclusion"), ("release", "preference")):
        attr = journal.artifact("attribute", {"attribute_id": "attr_" + name, "version": 1, "name": name})
        rule = journal.artifact("rule", {"rule_id": "rule_" + name, "version": 1,
                                          "attribute_ref": f"attr_{name}@v1", "rule_kind": role})
        journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": "attr_" + name, "version": 1, "artifact_id": attr})
        journal.event("task_a", "criterion.version_proposed", {"kind": "rule", "id": "rule_" + name, "version": 1, "artifact_id": rule})
    entries = []
    cases = (("partial", "pass", "unknown_missing"), ("none", "unknown_missing", "unknown_missing"),
             ("failed", "fail", "not_assessed"), ("tool", "pass", "unknown_missing"),
             ("complete", "pass", "available"))
    for name, size_verdict, release_verdict in cases:
        cells = []
        for field, verdict in (("size", size_verdict), ("release", release_verdict)):
            cell = {"candidate_ref": "cand_" + name, "attribute_ref": f"attr_{field}@v1",
                    "rule_ref": f"rule_{field}@v1", "verdict": verdict,
                    "determination_basis": "measured", "value_kind": "measured",
                    "value_source_claim_refs": ["claim_" + name + field] if verdict in ("pass", "fail", "available") else []}
            if name == "tool" and field == "release":
                cell["tool_error_ref"] = "error_release"
            if verdict == "not_assessed":
                cell["not_assessed_reason"] = "skipped_after_rejection"
            artifact = journal.artifact("assessment", cell)
            journal.event("run_a", "candidate.assessed", {**cell, "artifact_id": artifact})
            cells.append(cell)
        q = qualification(cells, hard_rule_refs=["rule_size@v1"], verified_hard_rule_refs=["rule_size@v1"],
                          required_rule_refs=["rule_release@v1"])
        entries.append({"candidate_ref": "cand_" + name, "identity_labels": [name], "qualification": q,
                        "verdicts": {**{cell["attribute_ref"]: cell["verdict"] for cell in cells},
                                     "attr_optional_preference@v1": "fail"}, "state": "provisional"})
    entries.append({"candidate_ref": "cand_unknown", "qualification": {"state": "pending"}, "state": "provisional"})
    journal.snapshot(entries=entries, qualification_policy="qualification_first_v1")
    source_events = journal.db.execute("SELECT count(*) FROM events").fetchone()[0]
    model.sync()
    api = ReadAPI(model)
    result = api.get("task_a", "candidates", {"selection": "all"})
    assert result["selection_counts"] == {"eligible": 1, "evidence_incomplete": 1, "excluded": 2,
                                           "incomplete": 2, "not_ready": 0, "total": 6}
    assert result["evidence_incomplete_summary"]["profile_counts"] == {
        "complete": 0, "partial": 1, "none": 0, "unknown": 0, "failed": 0}
    assert result["exclusion_summary"]["total"] == 2
    partial = api.get("task_a", "candidates", {"selection": "evidence_incomplete", "evidence_profile": ["partial"]})
    assert [row["candidate_ref"] for row in partial["items"]] == ["cand_partial"]
    assert api.get("task_a", "candidates", {"selection": "all", "evidence_profile": "partial"})["total"] == 2
    assert api.get("task_a", "candidates", {"evidence_profile": "partial"})["total"] == 2
    assert api.get("task_a", "candidates", {"selection": "all", "evidence_profile": "none"})["total"] == 1
    assert api.get("task_a", "candidates", {"selection": "all", "evidence_profile": "failed"})["total"] == 1
    with pytest.raises(ValueError, match="evidence profile"):
        api.get("task_a", "candidates", {"evidence_profile": "invented"})
    exported = {row["candidate_ref"]: row for row in csv.DictReader(io.StringIO(api.export_csv("task_a")))}
    assert exported["cand_partial"]["selection_decision"] == "evidence_incomplete"
    assert exported["cand_partial"]["evidence_profile"] == "partial"
    assert exported["cand_partial"]["selection_policy"] == "selection_reporting_v3"
    assert exported["cand_none"]["selection_decision"] == "excluded"
    assert exported["cand_none"]["selection_reason_code"] == "no_required_evidence"
    assert exported["cand_none"]["confirmed_mandatory_failure"] == "False"
    assert exported["cand_complete"]["selection_decision"] == "eligible"  # optional preference failure does not exclude
    assert exported["cand_tool"]["selection_decision"] == "incomplete"
    assert exported["cand_unknown"]["evidence_profile"] == "unknown"
    assert all(row["raw"] == entry for row, entry in zip(
        [model.candidate("task_a", entry["candidate_ref"]) for entry in entries], entries))
    with model._cache() as cache:
        cache.execute("UPDATE snapshots SET body=json_set(body,'$.decision_reading_version',5)")
        cache.execute("UPDATE candidate_rows SET body=json_remove(body,'$.eligibility','$.selection')")
        cache.commit()
    cursor = model.status()["source_cursor"]
    restarted = ReadModel(journal.root)
    assert restarted.status()["ready"] and restarted.status()["source_cursor"] == cursor
    assert restarted.candidates("task_a", status="all")["total"] == 6
    restarted.sync()  # reading v5 -> v6 backfill; retain the schema-v4 cache and event cursor
    assert model.candidates("task_a", selection="all")["selection_counts"] == result["selection_counts"]
    assert model.snapshots("task_a")["items"][0]["decision_reading_version"] == 6
    assert journal.db.execute("SELECT count(*) FROM events").fetchone()[0] == source_events


def test_eligibility_reason_uses_exact_rule_assessment_before_attribute_summary(setup):
    journal, model = setup
    attr = journal.artifact("attribute", {"attribute_id": "attr_size", "version": 1, "name": "Particle size"})
    journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": "attr_size", "version": 1, "artifact_id": attr})
    for name, role in (("hard_size", "hard_exclusion"), ("preferred_size", "preference")):
        rule = journal.artifact("rule", {"rule_id": "rule_" + name, "version": 1,
                                          "attribute_ref": "attr_size@v1", "rule_kind": role})
        journal.event("task_a", "criterion.version_proposed", {"kind": "rule", "id": "rule_" + name, "version": 1, "artifact_id": rule})
    def assess(name, verdict):
        cell = {"candidate_ref": "cand_a", "attribute_ref": "attr_size@v1", "rule_ref": f"rule_{name}@v1", "verdict": verdict}
        artifact = journal.artifact("assessment", cell)
        reason = journal.artifact("reason", {"reason_text": "Exact " + name + " " + verdict})
        journal.event("run_a", "candidate.assessed", {**cell, "artifact_id": artifact, "reason_artifact_id": reason})
    assess("hard_size", "unknown_conflicted")
    assess("preferred_size", "pass")
    entry = {"candidate_ref": "cand_a", "state": "provisional", "verdicts": {"attr_size@v1": "pass"},
             "qualification": {"state": "pending", "hard_total": 1, "hard_passed": 0,
                               "required_total": 0, "required_direct_answered": 0,
                               "blocking_hard_rule_refs": ["rule_hard_size@v1"]}}
    journal.snapshot(entries=[entry], qualification_policy="qualification_first_v1")
    assess("hard_size", "pass")  # a later assessment must not change this saved reading
    model.sync()
    reading = model.candidates("task_a", selection="excluded")["items"][0]["eligibility"]
    assert reading["reason_code"] == "required_evidence_conflicted"
    assert reading["issues"][0]["verdict"] == "unknown_conflicted"
    detail = model.candidate("task_a", "cand_a")
    assert detail["eligibility"]["issues"][0]["recorded_reason"] == "Exact hard_size unknown_conflicted"
    assert detail["selection"]["decision"] == "excluded"
    assert detail["raw"] == entry
