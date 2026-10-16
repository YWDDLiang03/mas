"""Source grouping, exact evaluation scope and separate display metadata."""
import json
import sqlite3

import pytest

from test_workbench_evidence import evidence_fixture
from mas.ui.evidence_collections import EvidenceCollections, _public_manifest
from mas.ui.evidence_groups import finding_identity, source_groups


def test_source_pages_keep_real_source_identity_context_and_kind(tmp_path):
    journal, model = evidence_fixture(tmp_path)
    try:
        for sid, status, kind in (("src_database", "database_entry", "database_entry"),
                                  ("src_model", "model_prediction_record", "model_prediction")):
            journal.artifact("source", {"source_id": sid, "title": sid, "source_status": status})
            ref = journal.artifact("claim", {"claim_id": "claim_" + sid, "source_ref": sid,
                "claim_text": "Saved value", "evidence_kind": kind, "value": 2})
            journal.event("run_a", "evidence.admitted", {"claim_id": "claim_" + sid,
                "source_ref": sid, "artifact_id": ref})
        journal.snapshot("snap_2")
        model.sync()
        default = source_groups(model, "task_a")
        assert default["total"] == 1
        paper = default["items"][0]
        assert paper["source_id"] == "src_saved" and paper["claim_count"] == 2
        assert paper["title"] == "Recorded study title" and paper["populations"] == ["human plasma"]
        assert paper["criteria"][0]["detail_ref"] == "rule_endpoint@v1"
        pages = [source_groups(model, "task_a", kind="all", page=page, page_size=1) for page in (1, 2, 3)]
        assert all(page["total"] == 3 and len(page["items"]) == 1 for page in pages)
        assert {page["items"][0]["kind"] for page in pages} == {"literature", "database", "model"}
        assert source_groups(model, "task_a", kind="all", snapshot="snap_1")["total"] == 1
        selected = source_groups(model, "task_a", criterion_ref="rule_endpoint@v1", candidate_ref="cand_000")
        assert selected["total"] == 1 and selected["items"][0]["claim_count"] == 2
        assert selected["scope"]["candidate_label"] == "Compound 0"
        assert model.evidence_detail("task_a", "claim_original")["source"]["excerpt"] == "The measured value was 7 nM"
    finally:
        journal.db.close()


def test_source_criteria_follow_selected_frozen_versions_not_all_history(tmp_path):
    journal, model = evidence_fixture(tmp_path)
    try:
        first = journal.artifact("rule_set", {"entries": [{"rule_ref": "rule_endpoint@v1", "attribute_ref": "attr_endpoint@v1"}]})
        journal.event("task_a", "criterion.version_approved", {"artifact_id": first, "rule_set_ref": "rules@v1"})
        journal.snapshot("snap_old", **{"rules@v": "rules@v1"})
        attr = journal.artifact("attribute", {"attribute_id": "attr_endpoint", "version": 2, "name": "Binding revised",
            "definition": "Revised recorded definition", "supporting_claim_refs": ["claim_original"]})
        journal.event("task_a", "criterion.version_proposed", {"kind": "attribute", "id": "attr_endpoint", "version": 2, "artifact_id": attr})
        rule = journal.artifact("rule", {"rule_id": "rule_endpoint", "version": 2, "attribute_ref": "attr_endpoint@v2", "rule_kind": "preference"})
        journal.event("task_a", "criterion.version_proposed", {"kind": "rule", "id": "rule_endpoint", "version": 2, "artifact_id": rule})
        current = journal.artifact("rule_set", {"entries": [{"rule_ref": "rule_endpoint@v2", "attribute_ref": "attr_endpoint@v2"}]})
        journal.event("task_a", "criterion.version_approved", {"artifact_id": current, "rule_set_ref": "rules@v2"})
        journal.snapshot("snap_new", **{"rules@v": "rules@v2"})
        model.sync()
        for snapshot, expected in ((None, "rule_endpoint@v2"), ("snap_old", "rule_endpoint@v1")):
            group = source_groups(model, "task_a", snapshot=snapshot)["items"][0]
            assert group["criteria_count"] == 1
            assert [item["detail_ref"] for item in group["criteria"]] == [expected]
            assert group["criteria_scope"] == "saved_evaluation"
        # The original detail still exposes the historical links.
        assert model.evidence_detail("task_a", "claim_original")["criteria_usage"]["total"] == 2
    finally:
        journal.db.close()


def test_collection_metadata_preserves_source_store_and_public_manifest_boundary(tmp_path):
    journal, model = evidence_fixture(tmp_path)
    try:
        source = journal.artifact("source", {"source_id": "src_saved", "source_status": "peer_reviewed_paper"})
        manifest = journal.artifact("existing_fact_manifest", {"claims": ["claim_original"],
            "source_records": {"src_saved": {"artifact_id": source}}, "created_at": "2026-10-15"})
        context = journal.artifact("task_context", {"objective_text": "Original objective", "title": "Original task",
            "evidence_fact_manifest_ref": manifest, "original_user_input": {"objective": "Original objective", "targets": ["binding"], "source_task_id": "task_hidden"}})
        journal.event("task_a", "task.version_recorded", {"version": 2, "artifact_id": context})
        model.sync()
        display = tmp_path / "display.json"
        service = EvidenceCollections(model, display)
        before = journal.db.execute("SELECT count(*) FROM events").fetchone()[0]
        data = service.get("task_a")
        assert data["source_count"] == 1 and data["claim_count"] == 1
        assert data["source_counts"]["literature"] == 1 and data["bound_source_task_id"] == "task_hidden"
        renamed = service.update("task_a", {"label": "Binding evidence", "description": "Saved assay findings", "topics": ["binding"]})
        assert renamed["label"] == "Binding evidence" and renamed["original_title"] == "Original task"
        assert EvidenceCollections(model, display).get("task_a")["label"] == "Binding evidence"
        assert journal.db.execute("SELECT count(*) FROM events").fetchone()[0] == before
        assert model.task_input("task_a")["objective"] == "Original objective"
        with pytest.raises(ValueError):
            service.update("task_a", {"objective": "must not change"})
        with pytest.raises(ValueError):
            EvidenceCollections(model, journal.root / "display.json")
    finally:
        journal.db.close()
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE artifacts(artifact_id TEXT,kind TEXT,body TEXT)")
    public = {"kind": "existing_fact_manifest", "payload": {"claims": ["public"]}}
    protected = [dict(public, visibility=level) for level in ("private", "evaluator_only", "recovery")]
    protected += [{"kind": "existing_fact_manifest", "payload": {"visibility": level}} for level in ("private", "evaluator_only", "recovery")]
    protected += [{"kind": "existing_fact_manifest", "payload": {"evaluator_only": True}}]
    for index, body in enumerate([public, *protected]):
        db.execute("INSERT INTO artifacts VALUES(?,?,?)", (str(index), "existing_fact_manifest", json.dumps(body)))
        result = _public_manifest(db, str(index))
        assert result == public["payload"] if index == 0 else result == {}
    db.close()


def test_finding_identity_requires_complete_fields_and_keeps_scientific_differences():
    raw = {"claim_id": "one", "source_ref": "source", "location": {"locator_value": "p1", "quoted_span": "Value 7 nM"},
           "scope": {"population": "human"}, "conditions": {"temperature": "37 C"}, "entities": ["compound"],
           "value": 7, "unit": "nM", "determination_basis": "measured", "claim_text": "Measured value 7 nM",
           "subject": "compound", "object": "target", "predicate": "inhibits"}
    copied = dict(raw, claim_id="two", recorded_at="later", reuse_of_claim_id="one", admission_reasons=["reused"])
    assert finding_identity(raw) == finding_identity(copied)
    for update in ({"conditions": {"temperature": "25 C"}}, {"claim_text": "Different conclusion"},
                   {"object": "other target"}, {"value": 8}, {"unit": "uM"}):
        assert finding_identity(raw) != finding_identity(dict(raw, **update))
    incomplete = dict(raw); incomplete.pop("conditions")
    assert finding_identity(incomplete) is None
