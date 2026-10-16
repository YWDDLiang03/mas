"""Saved context, exact provenance links and annotation-only accounting."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_read_model import Journal
from mas.ui.read_model import ReadModel
from mas.ui.read_api import ReadAPI
from mas.ui.research_briefs import ResearchBriefService
from mas.core.models import ModelResponse, ModelRoster, ScriptedAdapter


def evidence_fixture(tmp_path):
    journal=Journal(tmp_path/"source")
    journal.task()
    doc=journal.artifact("document",{"source_id":"src_saved","title":"Recorded study title","passages":[
        {"passage_id":"p1","text":"The assay used human plasma.","section_path":["Methods"]},
        {"passage_id":"p2","text":"The measured value was 7 nM in the assay.","section_path":["Results"]},
        {"passage_id":"p3","text":"The source records one assay condition only.","section_path":["Limitations"]}]})
    original={"claim_id":"claim_original","source_ref":"src_saved","document_artifact_id":doc,
        "claim_text":"The measured value was 7 nM.","determination_basis":"measured","evidence_kind":"peer_reviewed",
        "scope":{"population_or_system":"human plasma"},"conditions":{"assay":"binding","temperature":"37 C"},
        "value":7,"unit":"nM","location":{"locator_value":"p2","quoted_span":"The measured value was 7 nM"}}
    for identity,candidate,parent in (("claim_original",None,None),("claim_reused","cand_000","claim_original")):
        claim=dict(original,claim_id=identity,candidate_ref=candidate,reuse_of_claim_id=parent)
        artifact=journal.artifact("claim",claim)
        journal.event("task_a","evidence.admitted",{"claim_id":identity,"artifact_id":artifact,"source_ref":"src_saved","candidate_ref":candidate})
    attr=journal.artifact("attribute",{"attribute_id":"attr_endpoint","version":1,"name":"Binding endpoint","definition":"An observed binding quantity",
        "unit":"nM","direction":"lower_better","aggregation":"median","supporting_claim_refs":["claim_original"],"rationale":"A recorded task-relevant binding measurement."})
    journal.event("task_a","criterion.version_proposed",{"kind":"attribute","id":"attr_endpoint","version":1,"artifact_id":attr})
    rule=journal.artifact("rule",{"rule_id":"rule_endpoint","version":1,"attribute_ref":"attr_endpoint@v1","rule_kind":"preference","predicate_form":"ordering","cutoff":None})
    journal.event("task_a","criterion.version_proposed",{"kind":"rule","id":"rule_endpoint","version":1,"artifact_id":rule})
    assessment=journal.artifact("assessment",{"value_source_claim_refs":["claim_reused"],"verdict":"available","value":7})
    journal.event("run_a","candidate.assessed",{"candidate_ref":"cand_000","attribute_ref":"attr_endpoint@v1","rule_ref":"rule_endpoint@v1","artifact_id":assessment})
    journal.snapshot()
    model=ReadModel(journal.root)
    model.sync()
    return journal,model


def test_saved_context_and_bidirectional_exact_links_paginate_and_keep_snapshot(tmp_path):
    journal,model=evidence_fixture(tmp_path)
    try:
        api=ReadAPI(model)
        detail=api.get("task_a","evidence",{"snapshot":["snap_1"],"link_page_size":["1"]},"claim_original")
        assert detail["source"]["title"]=="Recorded study title"
        assert detail["source"]["passage"]["passage_id"]=="p2"
        assert detail["source"]["before"]["passage_id"]=="p1" and detail["source"]["after"]["passage_id"]=="p3"
        assert detail["context"]["population"]=="human plasma" and "37 C" in detail["context"]["conditions"]
        assert detail["summary"]["method"]=="recorded_fact_projection" and detail["source"]["excerpt"]!=detail["summary"]["text"]
        assert detail["criteria_usage"]["items"][0]["detail_ref"]=="rule_endpoint@v1"
        candidate=detail["candidate_usage"]["items"][0]
        assert candidate["label"]=="Compound 0" and candidate["snapshot_id"]=="snap_1"
        assert "claim_reused" in candidate["via_claim_refs"]
        assert "derived_used_in_assessment" in candidate["relationships"]
        page=api.get("task_a","evidence",{"criterion_ref":["rule_endpoint@v1"],"candidate_ref":["cand_000"],"source_id":["src_saved"],"page_size":["1"],"snapshot":["snap_1"]})
        assert page["total"]==2 and page["has_more"] and page["relationships_ready"]
        assert model.evidence("task_a",criterion_ref="rule_endpoint@v2")["total"]==0
        criterion=model.criterion("task_a","rule_endpoint@v1")
        assert criterion["explanation"]["why_included"]=="A recorded task-relevant binding measurement."
        assert criterion["evidence_query"]["criterion_ref"]=="rule_endpoint@v1"
        assert criterion["sources"][0]["links"]["counts"]["candidates"]==1
    finally:journal.db.close()


def test_relationship_backfill_does_not_reset_cursor_and_missing_or_private_context_stays_missing(tmp_path):
    journal,model=evidence_fixture(tmp_path)
    try:
        with model._cache() as db:
            cursor=model._meta(db)["cursor"]
            db.execute("DELETE FROM evidence_links")
            db.execute("DELETE FROM metadata WHERE key='evidence_links_version'")
            db.commit()
        model.sync()
        assert model.status()["source_cursor"]==cursor
        assert model.evidence_detail("task_a","claim_original")["links"]["counts"]["candidates"]==1
        doc=journal.artifact("document",{"source_id":"src_private","visibility":"evaluator_only","passages":[{"passage_id":"p1","text":"HIDDEN"}]})
        claim=journal.artifact("claim",{"claim_id":"claim_private_context","source_ref":"src_private","document_artifact_id":doc,
                                       "location":{"locator_value":"p1"},"claim_text":"Public fact without accessible context"})
        journal.event("task_a","evidence.admitted",{"claim_id":"claim_private_context","artifact_id":claim,"source_ref":"src_private"})
        model.sync()
        detail=model.evidence_detail("task_a","claim_private_context")
        assert not detail["source"]["context_available"] and "HIDDEN" not in json.dumps(detail)
    finally:journal.db.close()


def test_assessment_intervals_preserve_old_snapshot_and_withdraw_old_claim_use(tmp_path):
    journal,model=evidence_fixture(tmp_path)
    try:
        replacement=journal.artifact("assessment",{"value_source_claim_refs":[],"verdict":"unknown"})
        journal.event("run_a","candidate.assessed",{"candidate_ref":"cand_000","attribute_ref":"attr_endpoint@v1",
            "rule_ref":"rule_endpoint@v1","artifact_id":replacement})
        journal.snapshot("snap_2")
        model.sync()
        def counts(snapshot):
            return model.evidence_detail("task_a","claim_reused",snapshot=snapshot)["links"]["counts"]
        assert counts("snap_1")=={"criteria":1,"candidates":1}
        assert counts("snap_2")=={"criteria":0,"candidates":0}
        # Existing caches migrate using only their assessment pointers.
        with model._cache() as db:
            db.execute("UPDATE evidence_links SET superseded_row=NULL")
            db.execute("DELETE FROM metadata WHERE key='evidence_intervals_version'")
            db.commit()
        ReadModel(journal.root).sync()
        assert counts("snap_1")=={"criteria":1,"candidates":1}
        assert counts("snap_2")=={"criteria":0,"candidates":0}
    finally:journal.db.close()


def test_default_connections_use_latest_snapshot_and_history_counts_have_explicit_units(tmp_path):
    journal,model=evidence_fixture(tmp_path)
    try:
        artifact=journal.artifact("assessment",{"value_source_claim_refs":["claim_reused"],"verdict":"available"})
        for run_id in ("run_cancelled","run_new"):
            journal.event(run_id,"run.created",{"task_id":"task_a"},state_to="queued")
            journal.event(run_id,"candidate.assessed",{"candidate_ref":"cand_000","attribute_ref":"attr_endpoint@v1",
                "rule_ref":"rule_endpoint@v1","artifact_id":artifact})
        journal.event("run_cancelled","run.cancelled",state_to="cancelled")
        snapshot=journal.artifact("leaderboard_snapshot",{"snapshot_id":"snap_2","run_id":"run_new",
            "candidate_entries":[{"candidate_ref":"cand_000","identity_labels":["Compound 0"]}]})
        journal.event("run_new","leaderboard.snapshot_published",{"snapshot_id":"snap_2","artifact_id":snapshot})
        model.sync()
        default=model.evidence_detail("task_a","claim_original",link_page_size=1)
        assert default["candidate_usage"]["total"]==1 and default["candidate_usage"]["unit"]=="unique_candidates"
        assert default["links"]["scope"]["mode"]=="latest_snapshot"
        assert default["links"]["scope"]["snapshot_id"]=="snap_2"
        assert default["links"]["scope"]["snapshot_published_at"]
        assert default["candidate_usage"]["items"][0]["run_id"]=="run_new"
        old=model.evidence_detail("task_a","claim_original",snapshot="snap_1",link_page_size=1)
        assert old["candidate_usage"]["total"]==1 and old["candidate_usage"]["items"][0]["run_id"]=="run_a"
        assert old["links"]["scope"]["mode"]=="selected_snapshot" and old["source"]["excerpt"]==default["source"]["excerpt"]
        assert model.criterion("task_a","rule_endpoint@v1")["evidence_query"]["snapshot"]=="snap_2"
        with model._cache() as db:
            db.execute("DELETE FROM snapshots")
            db.commit()
        history=model.evidence_detail("task_a","claim_original",link_page_size=1)
        assert history["candidate_usage"]["total"]==3 and history["candidate_usage"]["has_more"]
        assert history["candidate_usage"]["unit"]=="candidate_run_records"
        assert history["links"]["scope"]["mode"]=="task_history"
        assert history["criteria_usage"]["unit"]=="criterion_versions"
    finally:journal.db.close()


class BriefModel:
    def __init__(self,tmp_path):
        self.source_path=tmp_path/"scientific"/"store.db"
        self.hash="old"
    def task_input(self,task_id):return {"objective":"Understand the saved assay","targets":[],"constraints":"Recorded facts only"}
    def frozen_criterion_refs(self,task_id):return ["cri_a@v1"]
    def criterion(self,task_id,ref,**kwargs):
        return {"criterion_id":ref,"detail_ref":ref,"attribute_record":{"name":"Assay"},"rule_record":{"predicate_form":"ordering"},
            "supporting_claims":["claim_a"],"sources":[{"claim_id":"claim_a","claim_artifact_id":"art_a","source_context_hash":self.hash,"record_available":True}],
            "explanation":{"why_included":"Saved assay relevance"}}
    def evidence_detail(self,*args,**kwargs):
        return {"statement":"The recorded assay value is 7 nM","basis":"measured","value":7,"context":{"population":"human plasma"},
                "source":{"title":"Saved paper","locator":"p2","excerpt":"Value 7 nM","passage":{"text":"Value 7 nM in human plasma."}}}


class PricedAdapter(ScriptedAdapter):
    price_in=0.
    price_out=1.
    thinking=False
    def complete(self,request):
        self.requests.append(request)
        inputs=json.loads(request.messages[0]["content"])["inputs"]
        sections=("conclusion","task_implication","conditions","limitations")
        data={"briefs":[{"criterion_ref":item["criterion_ref"],**{key:[{"text":"Interpretation restricted to the recorded assay and population.","claim_refs":item["allowed_claim_refs"]}] for key in sections}} for item in inputs]}
        return ModelResponse(request.request_id,json.dumps(data),data,self.record.model_id,"scripted",{"input_tokens":1,"output_tokens":6000},1,
                             cost_usd=.006,usage_status="complete",cost_status="estimated")


def test_annotation_cache_is_exact_and_cap_restores_across_restart_without_double_charge(tmp_path):
    model=BriefModel(tmp_path);adapter=PricedAdapter("priced",lambda _:None)
    roster=ModelRoster({"priced":adapter},{"proposer":"priced"})
    root=tmp_path/"annotations"
    service=ResearchBriefService(root,model,roster,max_usd=.01)
    assert service.generate("task_a")["state"]=="completed"
    assert service.get("task_a","cri_a@v1")["status"]=="ready"
    assert service.usage()["known_cost_usd"]==.006 and len(adapter.requests)==1
    model.hash="changed_context"
    restarted=ResearchBriefService(root,model,roster,max_usd=.01)
    assert restarted.get("task_a","cri_a@v1")["status"]=="stale"
    assert restarted.generate("task_a")["state"]=="partial"
    assert len(adapter.requests)==1 and restarted.usage()["known_cost_usd"]==.006
    assert not model.source_path.exists()


def test_brief_citations_cannot_cross_criterion_inputs():
    reply={"briefs":[{"criterion_ref":"a",**{section:[{"text":"A recorded interpretation","claim_refs":["claim_b"]}]
                                             for section in ("conclusion","task_implication","conditions","limitations")}}]}
    with pytest.raises(ValueError,match="cross-criterion"):
        ResearchBriefService._validate(reply,[{"criterion_ref":"a","allowed_claim_refs":["claim_a"]}])


def test_research_brief_store_is_separate_from_the_real_scientific_journal(tmp_path):
    from mas.core.runtime import Core

    journal, model = evidence_fixture(tmp_path)
    try:
        before = list(journal.db.iterdump())
        # Equal roots and ancestors would place annotation writes into the source tree.
        for forbidden in (journal.root, journal.root.parent):
            with pytest.raises(ValueError, match="separate"):
                ResearchBriefService(forbidden, model)
        adapter = PricedAdapter("annotation-fixture", lambda _: None)
        roster = ModelRoster({"annotation-fixture": adapter}, {"proposer": "annotation-fixture"})
        annotation_root = tmp_path / "annotations"
        service = ResearchBriefService(annotation_root, model, roster, max_usd=.01)
        result = service.generate("task_a", criterion_refs=["rule_endpoint@v1"])
        assert result["state"] == "completed" and len(adapter.requests) == 1
        assert service.get("task_a", "rule_endpoint@v1")["status"] == "ready"
        with Core.open(annotation_root, read_only=True) as annotations:
            assert len(annotations.artifacts.of_kind("workbench_research_brief")) == 1
        assert list(journal.db.iterdump()) == before
        assert journal.db.execute("SELECT COUNT(*) FROM artifacts WHERE kind='workbench_research_brief'").fetchone()[0] == 0
    finally:
        journal.db.close()
