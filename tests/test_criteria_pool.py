"""The criteria pool workflow (core/pool.py, derivation_stages.py, derivation_run.py):
broad proposal, filter, distill, merge, refine, promotion, stall stop, budget stop, and
continuation into a second round. Scripted models; no network."""

from __future__ import annotations

import json

import pytest

from mas.adapters.drug.registration import EVIDENCE_CATALOG
from mas.core import criteria, derivation_run, pool, task
from mas.core.broker import Broker, ProviderResponse, ToolContract
from mas.core.budget import Budget
from mas.core.controller import RunController, RunError
from mas.core.journal import actor
from mas.core.models import ModelRoster, ScriptedAdapter

OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")
SPEC = {
    "objective_text": "Prioritize oral multi-kinase inhibitors for target T1", "mode": "conditional",
    "scope_entities": [{"entity_kind": "target", "identifier": "CHEMBL_T1", "label": "T1", "role": "required"}],
    "candidate_universe": {"kind": "enumerated_set", "members": ["a", "b"]},
    "constraints": [], "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True},
    "seed_candidates": [{"candidate_ref": "refotinib", "aliases": ["RF-7"], "is_reference_outcome": True}],
}
PAPERS = {
    "10.1/a": "Kinase inhibitors with an absolute oral bioavailability above 30% achieved adequate exposure.",
    "10.1/b": "A terminal half-life of 12 h supported once-daily dosing of kinase inhibitors.",
    "10.1/c": "A high-fat meal increased exposure of kinase inhibitors about 2-fold.",
}
QUOTES = {"10.1/a": ("absolute oral bioavailability above 30% achieved adequate exposure", 30, "%", "oral bioavailability"),
          "10.1/b": ("terminal half-life of 12 h supported once-daily dosing", 12, "h", "half-life"),
          "10.1/c": ("high-fat meal increased exposure of kinase inhibitors about 2-fold", 2, "fold", "food effect")}
DIMENSIONS = [{"dimension": "pk", "focus": "pharmacokinetics"}]


def lit_attribute(name, unit, kind="quantitative", direction="higher_better"):
    return {"name": name, "definition": f"{name} of the compound in humans", "measurement_kind": kind, "unit": unit,
            "direction": direction, "acceptable_value_sources": ["peer_reviewed"], "aggregation": "median",
            "evidence_request": {"capability": "literature_retrieval", "question_kind": "search",
                                 "parameters": {"query_template": f"({{names}}) AND {name}"}},
            "rationale": "supports oral dosing"}


def proposal(attribute, claim, rule=None):
    return {"attribute": attribute, "supporting_claim_ids": [claim],
            "rule": rule or {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
                             "cutoff_basis": "none_evidence_insufficient"},
            "expected_change": "ranks exposed compounds higher", "falsification_test": "ranking unchanged"}


def claim_ids(content):
    """quote prefix -> claim id, from the claims block of a prompt."""
    out = {}
    for line in content.splitlines():
        if line.startswith("{") and '"claim_id"' in line:
            claim = json.loads(line)
            out[claim["quote"][:20]] = claim["claim_id"]
    return out


def cid(content, doi):
    return claim_ids(content)[QUOTES[doi][0][:20]]


class Search:
    contract = ToolContract(tool_id="tool_s", capability="literature_retrieval", capability_kind="source_retrieval",
                            question_kinds=("search",), contract_version="1", implementation_version="f",
                            purpose_statement="s", evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def __init__(self, papers):
        self.papers = papers

    def invoke(self, q, inputs):
        hits = [{"doi": doi, "pmcid": f"PMC{i}", "title": f"Paper {doi}", "is_review": True,
                 "identifiers": [{"scheme": "doi", "value": doi}]} for i, doi in enumerate(self.papers)]
        return ProviderResponse(values=[{"name": "search_hit", "value": h, "value_kind": "curated"} for h in hits])


class Reader:
    contract = ToolContract(tool_id="tool_r", capability="document_reading", capability_kind="document_reading",
                            question_kinds=("read",), contract_version="1", implementation_version="f",
                            purpose_statement="r", evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def invoke(self, q, inputs):
        doi = inputs["hit"]["doi"]
        doc = {"title": inputs["hit"]["title"], "access_state": "full_text_available", "reading_depth": "full_text",
               "source_hit": {"is_preprint": False},
               "passages": [{"passage_id": "sec1.p1", "kind": "paragraph", "section_path": ["Results"], "text": PAPERS[doi]}]}
        return ProviderResponse(values=[{"name": "document", "value": doc, "value_kind": "curated"}])


def reader_reply(request):
    text = request.messages[0]["content"]
    doi = next(d for d, body in PAPERS.items() if body in text)
    quote, value, unit, hint = QUOTES[doi]
    return {"claims": [{"passage_id": "sec1.p1", "quoted_span": quote, "statement": quote, "determination_basis": "measured",
                        "polarity": "supports", "value": value, "unit": unit, "attribute_hint": hint}]}


class RoundOne:
    """Scripted models for round 1; records which stage asked what."""

    def __init__(self):
        self.calls = []

    def __call__(self, request):
        question = request.metadata.get("question", "")
        self.calls.append((request.role, question))
        content = request.messages[0]["content"]
        if request.role == "retriever":
            return {"queries": [{"query": "oral kinase inhibitor pharmacokinetics", "rationale": "recall"}]}
        if request.role == "reader":
            return reader_reply(request)
        if question.startswith("propose pool"):
            a, b = cid(content, "10.1/a"), cid(content, "10.1/b")
            return {"proposals": [
                proposal(lit_attribute("Oral bioavailability", "%"), a,
                         {"rule_kind": "preference", "predicate_form": "threshold",
                          "cutoff": {"comparator": ">=", "value": 30, "unit": "%"}, "cutoff_basis": "source_stated_value"}),
                proposal(lit_attribute("Absolute oral bioavailability", "%"), a),
                proposal(dict(lit_attribute("Bioavailability like refotinib", "%")), a),
                proposal(lit_attribute("Elimination half-life", "h", kind="qualitative_determination"), b),
                proposal(lit_attribute("Plasma protein binding", "%"), "claim_that_does_not_exist"),
            ], "considered_and_rejected": [{"name": "Colour", "reason": "not measurable"}]}
        if question in ("critique pool", "final check before promotion"):
            proposals = json.loads(content.split("Proposals:\n", 1)[1].split("\n\nCited claims:")[0])
            assert all("rationale" not in p["attribute"] and "expected_change" not in p for p in proposals)   # blind
            findings = []
            for p in proposals:
                if p["attribute"]["name"] == "Elimination half-life" and p["attribute"].get("definition", "").endswith("humans"):
                    findings.append({"proposal_index": p["index"], "check": "counter_evidence_considered", "verdict": "fail",
                                     "severity": "material", "referent": "attribute.definition",
                                     "finding": "say which half-life (terminal) is meant"})
                else:
                    findings.append({"proposal_index": p["index"], "check": "evidence_support", "verdict": "pass",
                                     "severity": "minor", "referent": "supporting_claim_ids", "finding": "supported"})
            return {"findings": findings}
        if question == "distill pool":
            items = json.loads(content.split("Items to distill:\n", 1)[1].split("\n\nCited claims:")[0])
            out = []
            for item in items:
                if item["attribute"]["name"] == "Absolute oral bioavailability" and "fraction" not in item["attribute"]["definition"]:
                    revised = dict(item, attribute=dict(item["attribute"], definition="fraction of an oral dose reaching circulation"))
                    out.append({"index": item["index"], "action": "revise", "proposal": revised, "reason": "operational"})
                else:
                    out.append({"index": item["index"], "action": "keep", "reason": "precise"})
            return {"items": out}
        if question == "adjudicate merges":
            groups = json.loads(content.split("Groups:\n", 1)[1].split("\n\nCited claims:")[0])
            decisions = []
            for group in groups:
                first = group["members"][0]
                merged = dict(first, attribute=dict(first["attribute"], name="Oral bioavailability",
                                                    definition="fraction of an oral dose reaching circulation"))
                merged.pop("index")
                decisions.append({"group": group["group"], "action": "merge", "merged": merged, "reason": "same quantity"})
            return {"decisions": decisions}
        if question == "refine pool":
            notes = json.loads(content.split("Proposals to revise or withdraw:\n", 1)[1].split("\n\nCited claims:")[0])
            revisions = []
            for note in notes:
                attribute = dict(note["attribute"], measurement_kind="quantitative",
                                 definition="terminal elimination half-life in humans after oral dosing")
                revisions.append({"index": note["index"], "action": "revise", "reason": "fixed",
                                  "proposal": dict(note, attribute=attribute)})
            return {"revisions": revisions}
        raise AssertionError((request.role, question))


def setup(core, papers=("10.1/a", "10.1/b")):
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    broker = Broker(core)
    broker.register(Search(list(papers)))
    broker.register(Reader())
    return task_id, broker


def roster_for(script):
    return ModelRoster({"p": ScriptedAdapter("p", script, model="proposer-model", provider_family="family_a"),
                        "c": ScriptedAdapter("c", script, model="critic-model", provider_family="family_b")},
                       {"retriever": "p", "reader": "p", "proposer": "p", "adjudicator": "p", "critic": "c"})


def test_round_one_filters_distills_merges_refines_and_promotes(core):
    task_id, broker = setup(core)
    script = RoundOne()
    record = derivation_run.derive_iterative(core, broker, roster_for(script), task_id, dimensions=DIMENSIONS,
                                             catalog=EVIDENCE_CATALOG, by=OPERATOR, inner_iterations=4, stall_rounds=1)
    folded = pool.fold(core, task_id)
    by_name = {}
    for entry in folded.values():
        by_name.setdefault(entry["item"]["attribute"]["name"], []).append(entry)
    # the reference outcome is refused at entry; an uncited item is filtered out
    assert record["proposed"]["pk"]["refused_at_entry"][0]["name"] == "Bioavailability like refotinib"
    assert by_name["Plasma protein binding"][0]["state"] == "filtered_out"
    # the two bioavailability items merged into one child that names its parents
    merged = [e for e in folded.values() if e["parents"]]
    assert len(merged) == 1 and len(merged[0]["parents"]) == 2 and merged[0]["state"] == "promoted"
    assert sorted(folded[p.split("@v")[0]]["state"] for p in merged[0]["parents"]) == ["merged_away", "merged_away"]
    # the half-life item was refined twice (validator, then critic) and promoted
    half = by_name["Elimination half-life"][0]
    assert half["state"] == "promoted" and half["item"]["attribute"]["measurement_kind"] == "quantitative"
    assert [h["operation"] for h in half["history"]][:2] == ["add", "revise"]
    assert {r["name"] for r in record["promotion"]["accepted"]} == {"Oral bioavailability", "Elimination half-life"}
    assert record["termination_reason"] == "diminishing_information_gain" and len(record["iterations"]) < 4
    # promoted criteria are in the registry, with ids from their names
    names = {a["name"]: a for a in criteria.registered_attributes(core, task_id)}
    assert names["Oral bioavailability"]["derived_from"]["pool_criterion"].startswith(merged[0]["criterion_id"])
    # the critic ran on its own adapter and never saw the proposer's rationale
    assert record["independence"]["same_adapter"] is False
    events = [e.event_type for e in core.journal.replay(record["run_id"])]
    assert events[0] == "run.created" and events[-1] == "run.completed"
    with pytest.raises(RunError, match="criteria_derivation"):   # a sweep controller never loads a derivation run
        RunController(core, broker, adapter={"adapter_id": "a", "adapter_version": "1"})._load(record["run_id"])


def test_round_two_continues_the_pool_in_the_same_chain(core):
    task_id, broker = setup(core)
    first = derivation_run.derive_iterative(core, broker, roster_for(RoundOne()), task_id, dimensions=DIMENSIONS,
                                            catalog=EVIDENCE_CATALOG, by=OPERATOR, inner_iterations=4, stall_rounds=1)
    promoted_before = {k: (e["version"], e["state"]) for k, e in pool.fold(core, task_id).items() if e["state"] == "promoted"}
    broker2 = Broker(core)
    broker2.register(Search(["10.1/a", "10.1/b", "10.1/c"]))
    broker2.register(Reader())
    seen_pool_names = []

    def round_two(request):
        question = request.metadata.get("question", "")
        content = request.messages[0]["content"]
        if request.role == "retriever":
            return {"queries": [{"query": "food effect kinase inhibitors", "rationale": "gap"}]}
        if request.role == "reader":
            return reader_reply(request)
        if question.startswith("propose pool"):
            seen_pool_names.append(content.split("Criteria already in the registry (do not duplicate them): ")[1].split("\n")[0])
            return {"proposals": [proposal(lit_attribute("Food effect on exposure", "fold", direction="lower_better"),
                                           cid(content, "10.1/c"))], "considered_and_rejected": []}
        if question in ("critique pool", "final check before promotion"):
            proposals = json.loads(content.split("Proposals:\n", 1)[1].split("\n\nCited claims:")[0])
            return {"findings": [{"proposal_index": p["index"], "check": "evidence_support", "verdict": "pass",
                                  "severity": "minor", "referent": "supporting_claim_ids", "finding": "ok"} for p in proposals]}
        if question == "distill pool":
            return {"items": []}
        raise AssertionError(question)

    second = derivation_run.derive_iterative(core, broker2, roster_for(round_two), task_id, dimensions=DIMENSIONS,
                                             catalog=EVIDENCE_CATALOG, by=OPERATOR, inner_iterations=3, stall_rounds=1,
                                             continues_run_id=first["run_id"])
    assert second["chain_id"] == first["chain_id"] and second["round_index"] == 2
    assert "Oral bioavailability" in seen_pool_names[0]          # round 2 sees what round 1 registered
    assert [r["name"] for r in second["promotion"]["accepted"]] == ["Food effect on exposure"]
    after = pool.fold(core, task_id)
    assert {k: (after[k]["version"], after[k]["state"]) for k in promoted_before} == promoted_before
    continued = [e.payload for e in core.journal.replay(task_id) if e.event_type == "run.continued"]
    assert continued == [{"parent_run_id": first["run_id"], "run_id": second["run_id"], "continuation_kind": "continue"}]


def test_budget_refusal_ends_the_round_unresolved_and_keeps_the_pool(core):
    task_id, broker = setup(core)
    record = derivation_run.derive_iterative(core, broker, roster_for(RoundOne()), task_id, dimensions=DIMENSIONS,
                                             catalog=EVIDENCE_CATALOG, by=OPERATOR, budget=Budget({"llm_turns": 5}))
    assert record["termination_reason"] == "budget_exhausted"
    assert record["continuation_decision"]["decision"] == "continue_next_round"
    assert core.journal.replay(record["run_id"])[-1].event_type == "run.unresolved"
    assert any(e["state"] in pool.ACTIVE_STATES for e in pool.fold(core, task_id).values())


def test_merge_groups_need_the_same_route_unit_and_direction():
    from mas.core.derivation_stages import merge_groups
    def entry(i, name, unit="%", direction="higher_better"):
        return {"criterion_id": f"cri_{i}", "version": 1, "item": {"attribute": lit_attribute(name, unit, direction=direction)}}
    groups = merge_groups([entry(1, "Oral bioavailability"), entry(2, "Absolute oral bioavailability"),
                           entry(3, "Oral bioavailability", unit="h"), entry(4, "Oral bioavailability", direction="lower_better"),
                           entry(5, "Plasma protein binding")])
    assert [sorted(e["criterion_id"] for e in g) for g in groups] == [["cri_1", "cri_2"]]
