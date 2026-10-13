import pytest

from mas.adapters.drug.registration import EVIDENCE_CATALOG
from mas.core import assessor, criteria, derivation, review, task
from mas.core.broker import Broker, ProviderResponse, ToolContract
from mas.core.journal import actor
from mas.core.models import ModelRoster, ScriptedAdapter
from mas.core.runtime import Core

OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")
SPEC = {
    "objective_text": "Prioritize oral multi-kinase inhibitors for targets T1 and T2", "mode": "conditional",
    "scope_entities": [{"entity_kind": "target", "identifier": "CHEMBL_T1", "label": "T1", "role": "required"}],
    "candidate_universe": {"kind": "enumerated_set", "members": ["a", "b"]},
    "constraints": [{"text": "oral administration", "kind": "route", "hardness": "hard"}],
    "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True},
    "seed_candidates": [{"candidate_ref": "refotinib", "aliases": ["RF-7"], "is_reference_outcome": True}],
    "case_source_documents": [{"identifiers": [{"scheme": "doi", "value": "10.9/case-source"}], "title": "The case manuscript"}],
}
PAPERS = {
    "10.1/review": "Oral kinase inhibitors with an absolute oral bioavailability above 30% achieved adequate exposure.",
    "10.9/case-source": "Our eleven criteria were applied to 3,171 compounds.",
}


class Search:
    contract = ToolContract(tool_id="tool_s", capability="literature_retrieval", capability_kind="source_retrieval",
                            question_kinds=("search",), contract_version="1", implementation_version="f", purpose_statement="s",
                            evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def invoke(self, q, inputs):
        hits = [{"doi": doi, "pmcid": f"PMC{i}", "title": f"Paper {i}", "is_review": True,
                 "identifiers": [{"scheme": "doi", "value": doi}]} for i, doi in enumerate(PAPERS)]
        return ProviderResponse(values=[{"name": "search_hit", "value": h, "value_kind": "curated"} for h in hits])


class Reader:
    contract = ToolContract(tool_id="tool_r", capability="document_reading", capability_kind="document_reading",
                            question_kinds=("read",), contract_version="1", implementation_version="f", purpose_statement="r",
                            evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def invoke(self, q, inputs):
        doi = inputs["hit"]["doi"]
        doc = {"title": inputs["hit"]["title"], "access_state": "full_text_available", "reading_depth": "full_text",
               "source_hit": {"is_preprint": False},
               "passages": [{"passage_id": "sec1.p1", "kind": "paragraph", "section_path": ["Results"], "text": PAPERS[doi]}]}
        return ProviderResponse(values=[{"name": "document", "value": doc, "value_kind": "curated"}])


GOOD = {"attribute": {"name": "Oral bioavailability", "definition": "Fraction of an oral dose reaching circulation",
                      "measurement_kind": "quantitative", "unit": "%", "direction": "higher_better",
                      "acceptable_value_sources": ["peer_reviewed"], "aggregation": "max",
                      "evidence_request": {"capability": "literature_retrieval", "question_kind": "search",
                                           "parameters": {"query_template": "({names}) AND bioavailability"}},
                      "rationale": "oral route constraint"},
        "rule": {"rule_kind": "preference", "predicate_form": "threshold", "cutoff": {"comparator": ">=", "value": 30, "unit": "%"},
                 "cutoff_basis": "source_stated_value"},
        "expected_change": "ranks orally exposed compounds higher", "falsification_test": "no difference in ranking"}


def script(request):
    if request.role == "retriever":
        return {"queries": [{"query": "oral kinase inhibitor criteria", "rationale": "recall"}]}
    if request.role == "reader":
        if "eleven criteria" in request.messages[0]["content"]:
            raise AssertionError("the case-source document reached the reader")
        return {"claims": [{"passage_id": "sec1.p1", "quoted_span": "absolute oral bioavailability above 30% achieved adequate exposure",
                            "statement": "F above 30% gave adequate exposure", "determination_basis": "measured",
                            "polarity": "supports", "value": 30, "unit": "%", "attribute_hint": "oral bioavailability"}]}
    if request.role == "proposer" and "revising proposals" in request.system:
        claim_id = request.messages[0]["content"].split('"claim_id": "')[1].split('"')[0]
        revised = dict(GOOD, supporting_claim_ids=[claim_id],
                       attribute=dict(GOOD["attribute"], name="Exposure margin", definition="Oral bioavailability as exposure"))
        return {"revisions": [{"index": 1, "action": "withdraw", "reason": "named a compound"},
                              {"index": 2, "action": "withdraw", "reason": "citation did not exist"},
                              {"index": 3, "action": "revise", "proposal": revised, "reason": "claim now matches"}]}
    if request.role == "proposer":
        claim_id = request.messages[0]["content"].split('"claim_id": "')[1].split('"')[0]
        good = dict(GOOD, supporting_claim_ids=[claim_id])
        names_reference = dict(GOOD, supporting_claim_ids=[claim_id],
                               attribute=dict(GOOD["attribute"], name="Similarity to refotinib", rationale="like refotinib"))
        invented = dict(GOOD, supporting_claim_ids=["claim_nonexistent"])
        blocked = dict(GOOD, supporting_claim_ids=[claim_id], attribute=dict(GOOD["attribute"], name="Exposure margin"))
        return {"proposals": [good, names_reference, invented, blocked], "considered_and_rejected": [
            {"name": "Color", "reason": "not measurable from sources"}]}
    if request.role == "critic" and "revision check" in request.messages[0]["content"]:
        assert "quote is about bioavailability" in request.messages[0]["content"]   # the critic sees its earlier findings
        return {"findings": [{"proposal_index": 3, "check": "evidence_support", "verdict": "pass", "severity": "minor",
                              "referent": "supporting_claim_ids", "finding": "now supported"}]}
    if request.role == "critic":
        return {"findings": [{"proposal_index": 3, "check": "evidence_support", "verdict": "fail", "severity": "blocking",
                              "referent": "supporting_claim_ids", "finding": "quote is about bioavailability, not exposure margin"},
                             {"proposal_index": 0, "check": "objective_conformance", "verdict": "pass", "severity": "minor",
                              "referent": "rule.cutoff", "finding": "serves the oral constraint"},
                             {"proposal_index": 0, "check": "evidence_support", "verdict": "fail", "severity": "blocking",
                              "referent": "", "finding": "no referent, must be ignored"}]}
    raise AssertionError(request.role)


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c


def test_derivation_screens_proposals_and_queues_the_rest(core):
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    broker = Broker(core)
    broker.register(Search())
    broker.register(Reader())
    adapter = ScriptedAdapter("s", script, model="scripted-opus")
    roster = ModelRoster({"s": adapter}, {r: "s" for r in ("retriever", "reader", "proposer", "critic")})
    record = derivation.derive(core, broker, roster, task_id, dimensions=[{"dimension": "oral", "focus": "bioavailability"}],
                               catalog=EVIDENCE_CATALOG, by=OPERATOR)
    assert sorted(a["name"] for a in record["accepted"]) == ["Exposure margin", "Oral bioavailability"]
    reasons = {r.get("attribute"): r for r in record["considered_and_rejected"] if "rejection_reason" in r}
    assert any("reference_candidate_scan" in p for p in reasons["Similarity to refotinib"]["validator"])
    assert reasons["Similarity to refotinib"]["rejection_reason"] == "withdrawn"
    assert reasons["Oral bioavailability"]["rejection_reason"] == "withdrawn"          # the invented-citation copy
    assert [r["action"] for r in record["revisions"]] == ["withdraw", "withdraw", "revise"]
    manifest = core.artifacts.payload(record["dimensions"][0]["manifest_id"])
    omitted = {e["omitted_reason"] for e in manifest["excluded"]}
    assert omitted == {"case_source_document", "evaluator_only_artifact"}
    assert review.items(core, [task_id]) == {}          # an evidence-sourced preference needs no expert (trigger table)
    criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    rules = criteria.rule_set(core, task_id)
    assert [(e["rule_ref"], e["confirmed_by"]) for e in rules["entries"]] == [
        ("rule_exposure-margin@v1", "auto:trigger_table"), ("rule_oral-bioavailability@v1", "auto:trigger_table")]
    assert rules["acceptance_label"] == "prespecified" and rules["pending"] == []
    proposer_request = next(r for r in adapter.requests if r.role == "proposer")
    critic_request = next(r for r in adapter.requests if r.role == "critic")
    assert "expected_change" not in critic_request.messages[0]["content"]       # blind critic: no proposer rationale
    assert "Evidence catalog" in proposer_request.messages[0]["content"]


def test_ordering_preferences_score_by_percentile_and_skip_missing():
    def cell(candidate, value, verdict="pass"):
        return {"candidate_ref": candidate, "rule_ref": "rule_f@v1", "rule_kind": "preference", "verdict": verdict, "value": value}
    cells = {"a": [cell("a", 10.0)], "b": [cell("b", 50.0)], "c": [cell("c", 90.0)], "d": [cell("d", None, "unknown_missing")]}
    rules = {"rule_f@v1": {"rule_kind": "preference", "predicate_form": "ordering", "direction": "higher_better"}}
    scores = assessor.preference_scores(cells, rules, {})
    assert scores["c"] == (1.0, 1.0) and scores["a"] == (0.0, 1.0) and scores["b"] == (0.5, 1.0)
    assert scores["d"] == (None, 0.0)
    rules["rule_f@v1"]["direction"] = "lower_better"
    assert assessor.preference_scores(cells, rules, {})["a"] == (1.0, 1.0)


def test_task_mandated_criteria_come_from_scope_and_constraints_without_duplicates(core):
    from mas.adapters.drug.registration import objective_templates
    spec = dict(SPEC, scope_entities=[
        {"entity_kind": "target", "identifier": "CHEMBL1", "identifier_scheme": "chembl_target", "label": "T1", "role": "required"},
        {"entity_kind": "target", "identifier": "CHEMBL2", "identifier_scheme": "chembl_target", "label": "T2", "role": "optional"}])
    task_id, _ = task.record_version(core, spec, by=OPERATOR)
    added = derivation.objective_criteria(core, task_id, templates=objective_templates, by=OPERATOR)
    assert [a["name"] for a in added] == ["T1 curated potency", "Approved oral route on record"]
    assert derivation.objective_criteria(core, task_id, templates=objective_templates, by=OPERATOR) == []
    (item,) = review.items(core, [task_id]).values()                    # the hard route constraint needs an expert
    assert item["subject"]["id"].startswith("rule_approved-oral-route-on-record")
    ref = criteria.confirm_rule_set(core, task_id, by=OPERATOR, allow_pending=True)
    assert [e["rule_ref"] for e in criteria.rule_set(core, task_id, ref)["entries"]] == ["rule_t1-curated-potency@v1"]


def test_range_claims_straddling_a_cutoff_are_conflicts_not_passes():
    attribute = {"attribute_id": "attr_f", "version": 1, "name": "F", "definition": "d", "measurement_kind": "quantitative",
                 "unit": "%", "direction": "higher_better", "acceptable_value_sources": ["peer_reviewed"], "aggregation": "consensus",
                 "evidence_request": {"capability": "literature_retrieval", "question_kind": "search"}}
    rule = {"rule_id": "rule_f", "version": 1, "rule_kind": "preference", "cutoff": {"comparator": ">=", "value": 30, "unit": "%"},
            "cutoff_basis": "source_stated_value"}
    def claim(low, high):
        return {"claim_id": f"c{low}", "admission_state": "admitted", "evidence_kind": "peer_reviewed",
                "determination_basis": "measured", "value": None, "value_low": low, "value_high": high, "unit": "%"}
    straddling, _ = assessor.assess_cell(candidate={"candidate_id": "x"}, attribute=attribute, rule=rule, rule_set_ref="rules@v1",
                                         claims=[claim(20, 40)], resolved=True)
    above, _ = assessor.assess_cell(candidate={"candidate_id": "x"}, attribute=attribute, rule=rule, rule_set_ref="rules@v1",
                                    claims=[claim(35, 45)], resolved=True)
    assert straddling["verdict"] == "unknown_conflicted" and above["verdict"] == "pass"
