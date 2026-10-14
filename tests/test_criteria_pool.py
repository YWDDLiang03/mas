"""The criteria pool workflow (core/pool.py, derivation_stages.py, derivation_run.py):
broad proposal, filter, distill, merge, refine, promotion, stall stop, budget stop, and
continuation into a second round. Scripted models; no network."""

from __future__ import annotations

import json

import pytest

from mas.adapters.drug.registration import EVIDENCE_CATALOG
from mas.core import criteria, derivation_run, derivation_stages, pool, review, task
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


def test_a_source_basis_the_attribute_does_not_accept_is_refused_not_silently_empty():
    """A curated mechanism record is admitted evidence, but an attribute accepting only measured and
    derived values sets every one of them aside at assessment time, which looks like "no data".
    The validator refuses the pairing instead, so refinement can fix it."""
    from mas.core.derivation import validate_proposal

    entry = next(e for e in EVIDENCE_CATALOG if e["question_kind"] == "mechanism_records")
    assert entry["determination_basis"] == "curated"
    attribute = {
        "name": "Engagement of the required receptor on a curated record",
        "definition": "Whether a curated mechanism record states that the compound engages the required receptor",
        "measurement_kind": "categorical", "unit": None, "direction": "higher_better",
        "acceptable_value_sources": ["database_entry"], "aggregation": "any",
        "evidence_request": {"capability": entry["capability"], "question_kind": entry["question_kind"],
                             "parameters": {"target_chembl_id": "CHEMBL_T1"}},
        "rationale": "the objective requires engagement of the named receptor"}
    rule = {"rule_kind": "preference", "predicate_form": "threshold", "cutoff": {"comparator": "==", "value": True},
            "cutoff_basis": "task_constraint"}
    item = {"attribute": attribute, "supporting_claim_ids": ["claim_1"], "rule": rule}
    claims = {"claim_1": {"claim_id": "claim_1", "determination_basis": "curated", "value": True}}

    problems = validate_proposal(item, claims_by_id=claims, reference_labels=[], catalog=EVIDENCE_CATALOG)
    assert [p for p in problems if "acceptable_determination_bases" in p], problems

    accepted = dict(item, attribute=dict(attribute, acceptable_determination_bases=["curated"]))
    assert not [p for p in validate_proposal(accepted, claims_by_id=claims, reference_labels=[],
                                             catalog=EVIDENCE_CATALOG) if "acceptable_determination_bases" in p]

    # The pipeline normalises a reply before validating it, so the declaration has to survive that filter.
    # It did not: `acceptable_determination_bases` was absent from ATTRIBUTE_FIELDS, so a proposer that followed
    # the system prompt had its declaration stripped and got the same problem back on every revision.
    from mas.core.derivation import _normalize_proposal
    normalised = _normalize_proposal(accepted)
    assert normalised["attribute"].get("acceptable_determination_bases") == ["curated"]
    assert not [p for p in validate_proposal(normalised, claims_by_id=claims, reference_labels=[],
                                             catalog=EVIDENCE_CATALOG) if "acceptable_determination_bases" in p]


def test_an_exploratory_consideration_cannot_order_candidates_and_the_prompt_says_so():
    """`check_rule` refuses an ordering predicate on anything but a preference -- ordering is how a rule
    moves candidates up and down a board, which is what a preference is for. The schema block the proposer
    reads has to state that, and the forms it offers have to be the forms the checker accepts; it listed
    two of five, so a proposer needing a non-ranking form had to guess one."""
    from mas.core.derivation import SCHEMA_BLOCK_FORMS

    attribute = {"name": "Incidence of an on-target consequence", "definition": "share of patients reporting it",
                 "measurement_kind": "quantitative", "unit": "% of patients", "direction": "lower_better",
                 "acceptable_value_sources": ["peer_reviewed"], "aggregation": "max",
                 "evidence_request": {"capability": "literature_retrieval", "question_kind": "reported_rate"},
                 "rationale": "an anticipated consequence of engaging a required target"}
    ordering = {"rule_kind": "exploratory_consideration", "predicate_form": "ordering", "cutoff": None,
                "cutoff_basis": "none_evidence_insufficient"}
    with pytest.raises(criteria.InvariantViolation, match="ordering rule ranks candidates"):
        criteria.check_rule(ordering, attribute)
    qualitative = dict(ordering, predicate_form="qualitative_judgment")
    criteria.check_rule(qualitative, attribute)

    for form in ("threshold", "ordering", "range_membership", "categorical_membership", "qualitative_judgment"):
        assert form in SCHEMA_BLOCK_FORMS
    assert "only valid on a preference" in SCHEMA_BLOCK_FORMS


def test_merge_groups_need_the_same_route_unit_and_direction():
    from mas.core.derivation_stages import merge_groups
    def entry(i, name, unit="%", direction="higher_better"):
        return {"criterion_id": f"cri_{i}", "version": 1, "item": {"attribute": lit_attribute(name, unit, direction=direction)}}
    groups = merge_groups([entry(1, "Oral bioavailability"), entry(2, "Absolute oral bioavailability"),
                           entry(3, "Oral bioavailability", unit="h"), entry(4, "Oral bioavailability", direction="lower_better"),
                           entry(5, "Plasma protein binding")])
    assert [sorted(e["criterion_id"] for e in g) for g in groups] == [["cri_1", "cri_2"]]


class RoundOneLateMerge(RoundOne):
    """Like RoundOne, but the critic faults the mergeable pair on first sight.

    This is the real shape of a derivation round: `filter` finds something to say about almost every
    fresh proposal, so the items a merge would group are in `needs_refine` until `refine` repairs them.
    """

    def __init__(self):
        super().__init__()
        self.seen: set[str] = set()

    def __call__(self, request):
        question = request.metadata.get("question", "")
        if question == "critique pool":
            self.calls.append((request.role, question))
            proposals = json.loads(request.messages[0]["content"].split("Proposals:\n", 1)[1]
                                   .split("\n\nCited claims:")[0])
            findings = []
            for p in proposals:
                name = p["attribute"]["name"]
                first = name not in self.seen
                self.seen.add(name)
                if first and "bioavailability" in name.lower():
                    findings.append({"proposal_index": p["index"], "check": "unit_applicability_consistency",
                                     "verdict": "fail", "severity": "material", "referent": "attribute.definition",
                                     "finding": "say whether absolute or relative bioavailability is meant"})
                else:
                    findings.append({"proposal_index": p["index"], "check": "evidence_support", "verdict": "pass",
                                     "severity": "minor", "referent": "supporting_claim_ids", "finding": "supported"})
            return {"findings": findings}
        return super().__call__(request)


def test_a_pair_the_critic_faulted_is_still_merged_in_the_iteration_that_repaired_it(core):
    """Regression: merge used to run before refine, so within an iteration it saw only unfaulted items.

    A second iteration would have caught the pair, which is why this pins `inner_iterations=1`: a round that
    stops -- on its iteration budget, a stall or a budget refusal -- leaves the merge undone. On the manuscript
    case it stopped after two iterations having grouped 0 items, the adjudicator role was never called once,
    and the registry kept both descriptions of a quantity the pool had the evidence to combine.
    """
    task_id, broker = setup(core)
    script = RoundOneLateMerge()
    derivation_run.derive_iterative(core, broker, roster_for(script), task_id, dimensions=DIMENSIONS,
                                    catalog=EVIDENCE_CATALOG, by=OPERATOR, inner_iterations=1, stall_rounds=1)
    folded = pool.fold(core, task_id)
    merged = [e for e in folded.values() if e["parents"]]
    assert len(merged) == 1 and len(merged[0]["parents"]) == 2, "the refined pair was never merged"
    parents = [folded[ref.split("@v")[0]] for ref in merged[0]["parents"]]
    # each parent was faulted, repaired, and only then merged away -- the order the stages must run in
    for parent in parents:
        operations = [h["operation"] for h in parent["history"]]
        stages_seen = [h["stage"] for h in parent["history"]]
        assert "revise" in operations and stages_seen[-1] == "merge" and parent["state"] == "merged_away"
        assert stages_seen.index("refine") < len(stages_seen) - 1
    assert ("adjudicator", "adjudicate merges") in script.calls


def test_the_trajectory_shows_the_pool_growing_then_being_pruned(core):
    task_id, broker = setup(core)
    derivation_run.derive_iterative(core, broker, roster_for(RoundOne()), task_id, dimensions=DIMENSIONS,
                                    catalog=EVIDENCE_CATALOG, by=OPERATOR, inner_iterations=4, stall_rounds=1)
    steps = pool.trajectory(core, task_id)
    assert [s["stage"] for s in steps][0] == "propose" and [s["stage"] for s in steps][-1] == "promote"
    assert steps[0]["added"] == 4 and steps[0]["live_after"] == 4          # the reference-like item never entered
    assert any(s["stage"] == "merge" and s["merged_away"] for s in steps)
    assert any(s["removed"] for s in steps) and steps[-1]["promoted"] == 2
    assert steps[-1]["live_after"] < steps[0]["live_after"], "the pool must end smaller than it started"


# --- one quantity, two curations ------------------------------------------------------------
# The two attributes the live manuscript registry held for each of the five required receptors,
# with the wording and bindings they were read out of the store with: one measurement, two
# curations, differing only in the `question_kind` that names which database answers.
CHEMBL_POTENCY = {
    "name": "CSF1R curated potency",
    "definition": "Median pChEMBL value over curated point measurements against CSF1R (CHEMBL1844)",
    "measurement_kind": "quantitative", "unit": "pChEMBL", "direction": "higher_better", "aggregation": "median",
    "acceptable_value_sources": ["curated_measurement"],
    "evidence_request": {"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values",
                         "identifier_scheme": "inchikey", "parameters": {"target_chembl_id": "CHEMBL1844"}},
    "rationale": "CSF1R is a required target of the task"}
GTOPDB_AFFINITY = {
    "name": "CSF1R affinity on the independent expert curation",
    "definition": "The median expert-curated affinity, reported on the pChEMBL scale as the negative base-ten "
                  "logarithm of a molar pIC50, pKi or pKd, that an independent pharmacological curation lists for "
                  "the compound at CSF1R",
    "measurement_kind": "quantitative", "unit": "pChEMBL", "direction": "higher_better", "aggregation": "median",
    "acceptable_value_sources": ["curated_measurement"],
    "evidence_request": {"capability": "interaction_evidence_lookup", "question_kind": "gtopdb_affinity",
                         "identifier_scheme": "inchikey", "parameters": {"target_chembl_id": "CHEMBL1844"}},
    "rationale": "an independent curation of affinity at a required target"}


def pooled(*routes, base=CHEMBL_POTENCY, **extra):
    """`base` rebound to several evidence routes and nothing else."""
    attribute = dict(base, evidence_requests=list(routes), **extra)
    attribute.pop("evidence_request", None)
    return attribute


def test_one_quantity_curated_by_two_databases_is_grouped_for_merge_though_its_wording_barely_overlaps():
    """Measured on the registry, 14 October 2026: ten promoted rules for five quantities, because each
    receptor had one attribute bound to ChEMBL and one bound to IUPHAR/BPS. Grouping keyed on
    `question_kind`, which *is* the source, so the pair could never land in one bucket; and the wording
    test cannot rescue it, as the pair's name Jaccard is 0.14 and name+definition 0.10 against the 0.35
    the test needs. Same capability, unit, direction and subject parameter is what says one quantity."""
    from mas.core.derivation_stages import _overlap, merge_groups

    assert _overlap(CHEMBL_POTENCY, GTOPDB_AFFINITY) < 0.35

    def entry(i, attribute):
        return {"criterion_id": f"cri_{i}", "version": 1, "item": {"attribute": attribute}}

    other_receptor = dict(CHEMBL_POTENCY, name="VEGFR2 curated potency",
                          evidence_request=dict(CHEMBL_POTENCY["evidence_request"],
                                                parameters={"target_chembl_id": "CHEMBL279"}))
    groups = merge_groups([entry(1, CHEMBL_POTENCY), entry(2, GTOPDB_AFFINITY), entry(3, other_receptor),
                           entry(4, dict(GTOPDB_AFFINITY, direction="lower_better"))])
    assert [sorted(e["criterion_id"] for e in g) for g in groups] == [["cri_1", "cri_2"]]
    # the two-route form of the quantity groups with either single-route form: a merge can still absorb
    # a third sibling the pool proposes later
    both = merge_groups([entry(1, pooled(CHEMBL_POTENCY["evidence_request"], GTOPDB_AFFINITY["evidence_request"])),
                         entry(2, CHEMBL_POTENCY)])
    assert [sorted(e["criterion_id"] for e in g) for g in both] == [["cri_1", "cri_2"]]


def test_an_attribute_mixing_a_literature_route_with_a_database_route_is_refused():
    """Two routes on one attribute are two broker calls pooled under one aggregation. A literature route
    is not that: it is a search, a read and a quote-checked extraction, and pooling a claim read from a
    paper with a database record under one median needs a policy nobody has set."""
    literature_route = {"capability": "literature_retrieval", "question_kind": "search",
                        "parameters": {"query_template": "({names}) AND CSF1R affinity"}}
    with pytest.raises(criteria.InvariantViolation, match="mixes a literature route"):
        criteria.check_attribute(pooled(CHEMBL_POTENCY["evidence_request"], literature_route))
    with pytest.raises(criteria.InvariantViolation, match="literature routes"):
        criteria.check_attribute(pooled(literature_route, dict(literature_route, parameters={"query_template": "({names})"})))
    with pytest.raises(criteria.InvariantViolation, match="same evidence route twice"):
        criteria.check_attribute(pooled(CHEMBL_POTENCY["evidence_request"], dict(CHEMBL_POTENCY["evidence_request"])))
    # a singular request left behind beside a route list would never be asked, so it is not accepted silently
    with pytest.raises(criteria.InvariantViolation, match="nothing would ever ask it"):
        criteria.check_attribute(dict(CHEMBL_POTENCY, evidence_requests=[GTOPDB_AFFINITY["evidence_request"]]))
    criteria.check_attribute(pooled(CHEMBL_POTENCY["evidence_request"], GTOPDB_AFFINITY["evidence_request"]))


def test_two_attributes_asking_the_same_route_set_are_duplicates_and_a_second_route_makes_them_distinct():
    """`evidence_key` is what `filter_stage` and `promote` call a duplicate of the registry. Keyed on one
    route it could not see the pair as duplicates at all (the question kinds differ); keyed on the route
    *set* it sees two attributes asking the same two databases as one, while the ChEMBL-only and the
    ChEMBL+IUPHAR form of a quantity stay distinct -- the second asks something the first never asks."""
    chembl_only = criteria.evidence_key(CHEMBL_POTENCY)
    assert criteria.evidence_key(dict(CHEMBL_POTENCY, name="Potency at the first required receptor",
                                      definition="another wording of the same question")) == chembl_only
    both = pooled(CHEMBL_POTENCY["evidence_request"], GTOPDB_AFFINITY["evidence_request"])
    assert criteria.evidence_key(both) not in (chembl_only, criteria.evidence_key(GTOPDB_AFFINITY))
    reordered = pooled(GTOPDB_AFFINITY["evidence_request"], CHEMBL_POTENCY["evidence_request"])
    assert criteria.evidence_key(reordered) == criteria.evidence_key(both)      # the set, not the order
    assert criteria.evidence_key(dict(both, name="CSF1R curated affinity")) == criteria.evidence_key(both)


def merge_script(extra_route=None):
    """An adjudicator that merges each group, keeping its members' routes (plus `extra_route`, if given,
    which no member declared)."""
    def script(request):
        question = request.metadata.get("question", "")
        assert question == "adjudicate merges", question
        groups = json.loads(request.messages[0]["content"].split("Groups:\n", 1)[1].split("\n\nCited claims:")[0])
        decisions = []
        for group in groups:
            members = group["members"]
            routes = [r for m in members for r in criteria.evidence_routes(m["attribute"])]
            attribute = pooled(*(routes + ([extra_route] if extra_route else [])), base=members[0]["attribute"],
                               name="CSF1R curated affinity",
                               definition="Median curated affinity at CSF1R (CHEMBL1844) on the pChEMBL scale, over "
                                          "every curation that reports one")
            merged = dict(members[0], attribute=attribute,
                          supporting_claim_ids=sorted({c for m in members for c in m["supporting_claim_ids"]}))
            merged.pop("index")
            decisions.append({"group": group["group"], "action": "merge", "merged": merged,
                              "reason": "one measurement, two curations of it"})
        return {"decisions": decisions}
    return script


def pool_of(core, script, items, *, task_id, run_id):
    """A pool holding one item per (claim id, attribute) pair, and the context to run a stage over it."""
    writer = pool.Pool(core, task_id, by=OPERATOR, run_id=run_id).at("propose", 0)
    claims_by_id = {}
    for claim_id, attribute in items:
        claims_by_id[claim_id] = {"claim_id": claim_id, "source_ref": "src_db_1", "determination_basis": "measured",
                                  "location": {"quoted_span": f"a curated affinity at CSF1R ({claim_id})"},
                                  "value": 8.0, "unit": "pChEMBL"}
        writer.add(proposal(attribute, claim_id), reason_text="proposed for target_coverage")
    return derivation_stages.StageContext(
        core=core, roster=roster_for(script), task_id=task_id, run_id=run_id,
        task_context={"objective_text": SPEC["objective_text"], "constraints": [],
                      "scope_entities": SPEC["scope_entities"]},
        catalog=EVIDENCE_CATALOG, claims_by_id=claims_by_id, reference_labels=[], pool=writer)


def two_curations_pool(core, script, task_id="task_merge"):
    """A pool holding the receptor's two attributes, and the stage context to merge them in."""
    return pool_of(core, script, [("claim_chembl", CHEMBL_POTENCY), ("claim_gtopdb", GTOPDB_AFFINITY)],
                   task_id=task_id, run_id="run_merge")


def test_a_merge_may_pool_its_parents_routes_into_one_attribute(core):
    ctx = two_curations_pool(core, merge_script())
    assert derivation_stages.merge_stage(ctx, 1) == {"groups": 1, "merged": 1, "kept_separate": 0, "refused": 0}
    folded = pool.fold(core, "task_merge")
    child = next(e for e in folded.values() if e["parents"])
    assert [r["question_kind"] for r in criteria.evidence_routes(child["item"]["attribute"])] == \
           ["pchembl_values", "gtopdb_affinity"]
    assert sorted(e["state"] for e in folded.values() if not e["parents"]) == ["merged_away", "merged_away"]
    criteria.check_attribute(child["item"]["attribute"])          # and the pooled child is registrable


def test_a_merge_may_not_add_an_evidence_route_neither_parent_had(core):
    """The merge gate already refuses a child citing a claim its parents did not; a child asking a question
    neither parent asked is the same kind of reach, and it would make the merged criterion measure
    something the pool never proposed. The route used here reads a second receptor from a database a
    parent already uses, which is the form that would otherwise pass unnoticed: every field of the child
    validates, and only the question is new."""
    extra = {"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values",
             "identifier_scheme": "inchikey", "parameters": {"target_chembl_id": "CHEMBL279"}}
    ctx = two_curations_pool(core, merge_script(extra_route=extra))
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["refused"] == 1 and stats["merged"] == 0
    assert not [e for e in pool.fold(core, "task_merge").values() if e["parents"]]
    # and nothing else about that child was wrong: the refusal is about the route it reached for
    invented = pooled(CHEMBL_POTENCY["evidence_request"], GTOPDB_AFFINITY["evidence_request"], extra)
    assert ctx.validate(proposal(invented, "claim_chembl")) == []


# --- the registry already holds it ----------------------------------------------------------

ORDERING = {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
            "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty"}


def critic_passes_everything(request):
    """A critic that faults nothing, so a filter pass turns only on the deterministic gates."""
    assert request.metadata.get("question") == "critique pool", request.metadata
    proposals = json.loads(request.messages[0]["content"].split("Proposals:\n", 1)[1].split("\n\nCited claims:")[0])
    return {"findings": [{"proposal_index": p["index"], "check": "evidence_support", "verdict": "pass",
                          "severity": "minor", "referent": "supporting_claim_ids", "finding": "supported"}
                         for p in proposals]}


def test_a_proposal_whose_only_route_a_registered_attribute_already_covers_is_refused_as_a_duplicate(core):
    """`filter_stage` refused a proposal only when `evidence_key` matched, and that key hashes the whole
    route set. So once a receptor's potency is registered as one attribute reading both curations, a
    fresh single-route IUPHAR/BPS proposal did not match it and was promoted -- rebuilding the ten rules
    for five quantities the registration template was changed to remove. `merge_groups` cannot catch it
    either: it groups pool candidates, and the registered attribute is not one."""
    task_id = "task_subset"
    both = pooled(CHEMBL_POTENCY["evidence_request"], GTOPDB_AFFINITY["evidence_request"])
    attr_ref, _ = criteria.propose(core, task_id, both, ORDERING, by=OPERATOR)
    ctx = pool_of(core, critic_passes_everything, [("claim_gtopdb", GTOPDB_AFFINITY)],
                  task_id=task_id, run_id="run_subset")

    assert derivation_stages.filter_stage(ctx, 1) == {"filtered_out": 1, "to_refine": 0, "kept": 0}
    (entry,) = pool.fold(core, task_id).values()
    assert entry["state"] == "filtered_out"
    last = entry["history"][-1]
    assert last["reason_kind"] == "duplicate_of_registered"
    # the reason has to name the attribute and which of its routes already cover the proposal: with a
    # subset test, "already registered" no longer means the two attributes are identical
    assert attr_ref in last["reason_text"] and "gtopdb_affinity" in last["reason_text"]
    assert "pchembl_values" in last["reason_text"]
    found = derivation_stages.duplicate_of_registered(GTOPDB_AFFINITY, criteria.registered_attributes(core, task_id))
    assert found["attribute_ref"] == attr_ref and found["already_covered"] == ["gtopdb_affinity"]


def test_a_proposal_offering_a_route_the_registered_attribute_lacks_is_not_refused(core):
    """The mirror of the subset test, and the error that would be worse: the two-curation form of a
    quantity asks a database the one-curation form never asks. Dropping it silently would lose the
    evidence the collapse exists to pool, so it survives the filter and the registry ends up holding the
    quantity twice -- which `core/collapse.py` then collapses."""
    task_id = "task_superset"
    attr_ref, _ = criteria.propose(core, task_id, CHEMBL_POTENCY, ORDERING, by=OPERATOR)
    both = pooled(CHEMBL_POTENCY["evidence_request"], GTOPDB_AFFINITY["evidence_request"])
    ctx = pool_of(core, critic_passes_everything, [("claim_both", both)], task_id=task_id, run_id="run_superset")

    registered = criteria.registered_attributes(core, task_id)
    assert derivation_stages.quantity_key(both) == derivation_stages.quantity_key(registered[0])
    assert derivation_stages.duplicate_of_registered(both, registered) is None
    assert derivation_stages.filter_stage(ctx, 1) == {"filtered_out": 0, "to_refine": 0, "kept": 1}
    (entry,) = pool.fold(core, task_id).values()
    assert entry["state"] == "candidate"
    # and the single-route half of it, which asks nothing new, is still refused against the same registry
    assert derivation_stages.duplicate_of_registered(CHEMBL_POTENCY, registered)["attribute_ref"] == attr_ref


# --- collapsing a quantity the registry holds twice -----------------------------------------
# The registry as the manuscript left it: `{receptor}-curated-potency` promoted first by the
# task-mandated template, `{receptor}-affinity-on-the-independent-expert-curation` promoted after it
# by the pool, both measuring one receptor's affinity on the pChEMBL scale.

def promoted_pair(core, *, task_id="task_collapse", first=CHEMBL_POTENCY, second=GTOPDB_AFFINITY,
                  first_rule=None, second_rule=None):
    one = criteria.propose(core, task_id, first, first_rule or ORDERING, by=OPERATOR)
    two = criteria.propose(core, task_id, second, second_rule or ORDERING, by=OPERATOR)
    return task_id, one, two


def test_two_promoted_attributes_for_one_quantity_collapse_to_one_declaring_both_routes(core):
    """The registry is append-only and the pool's merge stage only groups pool candidates, so a
    duplicate that has already been promoted was past the one stage that could have combined it.
    Measured on the manuscript registry, 14 October 2026: ten promoted rules for five quantities, every
    receptor scored twice and five quantities that do not exist in the coverage denominator."""
    from mas.core import collapse

    task_id, (attr_chembl, rule_chembl), (attr_gtopdb, rule_gtopdb) = promoted_pair(core)
    before = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    assert sorted(e["rule_ref"] for e in before["entries"]) == sorted([rule_chembl, rule_gtopdb])

    result = collapse.collapse(core, task_id, by=OPERATOR, dry_run=False)
    (group,) = result["collapsed"]
    assert result["refused"] == [] and group["collapse_id"].startswith("clp_")
    (record,) = collapse.records(core, task_id)
    assert record["surviving"]["attribute_ref_before"] == attr_chembl        # the earliest-promoted survives
    assert [m["attribute_ref"] for m in record["superseded"]] == [attr_gtopdb]
    surviving = criteria.load(core, record["surviving"]["attribute_ref_after"], task_id)
    assert [r["question_kind"] for r in criteria.evidence_routes(surviving)] == ["pchembl_values", "gtopdb_affinity"]
    assert surviving["definition"] == CHEMBL_POTENCY["definition"]           # the definition is left alone
    assert "evidence_request" not in surviving                               # nothing names one route as *the* one
    criteria.check_attribute(surviving)

    after = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    assert [e["rule_ref"] for e in after["entries"]] == [record["surviving"]["rule_ref_after"]]
    assert after["entries"][0]["attribute_ref"] == record["surviving"]["attribute_ref_after"]
    assert [e["rule_ref"] for e in after["collapsed_away"]] == [rule_gtopdb]
    assert after["collapsed_away"][0]["merged_into"] == record["surviving"]["attribute_ref_after"]
    assert after["machine_collapsed"] == [record["surviving"]["rule_ref_after"]]
    # the superseded lineage reads both ways, in the pool's own change-record vocabulary
    changes = [e.payload for e in core.journal.replay(task_id)
               if e.event_type == "criterion.change_recorded" and e.payload.get("collapse")]
    assert {(c["criterion_id"], c["operation"], c["state"]) for c in changes} == {
        (attr_gtopdb.split("@v")[0], "merge", "merged_away"),
        (attr_chembl.split("@v")[0], "merge", "promoted")}
    assert all(c["targets_out"] == [record["surviving"]["attribute_ref_after"]] for c in changes)
    assert not any(c.get("pool") for c in changes)       # these are registry refs, not `cri_` lineages
    # and a second run has nothing left to do, so the command is safe to repeat
    assert collapse.collapse(core, task_id, by=OPERATOR, dry_run=False)["collapsed"] == []


def test_the_surviving_attributes_rule_is_unchanged_by_the_collapse(core):
    """A collapse is about the attribute: it pools the routes one quantity is read from and re-decides
    nothing. The new rule version exists only because the sweep loads the attribute the *rule* names
    (`controller` reads `entries[].attribute_ref`), so a new attribute version nothing points at would
    leave every cell reading one database while the registry said the quantity read two."""
    from mas.core import collapse

    task_id, (_, rule_chembl), _ = promoted_pair(core)
    collapse.collapse(core, task_id, by=OPERATOR, dry_run=False)
    (record,) = collapse.records(core, task_id)
    before = criteria.load(core, rule_chembl, task_id)
    after = criteria.load(core, record["surviving"]["rule_ref_after"], task_id)

    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    assert changed == {"attribute_ref", "version", "supersedes", "collapsed_by"}
    assert (after["rule_kind"], after["predicate_form"], after["cutoff"], after["cutoff_basis"]) == \
           (before["rule_kind"], before["predicate_form"], before["cutoff"], before["cutoff_basis"])
    assert after["supersedes"] == rule_chembl and after["collapsed_by"] == record["collapse_id"]
    assert review.items(core, [task_id]) == {}       # an ordering preference needs no expert, before or after


def test_a_group_whose_rules_disagree_on_cutoff_or_kind_is_refused_and_says_why(core):
    """Two rules that score one quantity differently are a disagreement about how to score it, not a
    duplicate registration of it, and the one authority this collapse has -- that the routes ask the
    same question -- says nothing about which rule is right. So the group is refused whole, and both
    rules keep scoring until a person settles it."""
    from mas.core import collapse

    threshold = {"rule_kind": "preference", "predicate_form": "threshold", "cutoff_basis": "source_stated_value",
                 "cutoff": {"comparator": ">=", "value": 7.0, "unit": "pChEMBL"}}
    task_id, (_, rule_chembl), (_, rule_gtopdb) = promoted_pair(
        core, first_rule=threshold,
        second_rule=dict(threshold, cutoff={"comparator": ">=", "value": 8.0, "unit": "pChEMBL"}))
    result = collapse.collapse(core, task_id, by=OPERATOR, dry_run=False)

    assert result["collapsed"] == [] and len(result["refused"]) == 1
    (why,) = result["refused"][0]["refused"]
    assert rule_gtopdb in why and rule_chembl in why and "cutoff" in why and "8.0" in why
    assert collapse.records(core, task_id) == []            # a real disagreement writes nothing at all
    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    assert sorted(e["rule_ref"] for e in rules["entries"]) == sorted([rule_chembl, rule_gtopdb])
    assert rules["machine_collapsed"] == [] and rules["collapsed_away"] == []

    kinds_task, _, (_, demoted) = promoted_pair(
        core, task_id="task_collapse_kinds", first_rule=ORDERING,
        second_rule={"rule_kind": "exploratory_consideration", "predicate_form": "qualitative_judgment",
                     "cutoff": None, "cutoff_basis": "none_evidence_insufficient"})
    refusals = collapse.collapse(core, kinds_task, by=OPERATOR, dry_run=False)["refused"][0]["refused"]
    assert any("rule_kind" in r and demoted in r for r in refusals)
    assert any("predicate_form" in r for r in refusals)


def test_a_collapsed_rule_set_cannot_read_as_prespecified(core):
    """Nobody confirmed the collapse, and the acceptance label is what a reader has to go on. A rule set
    whose attribute a machine rewrote must not read like one a person settled, for the same reason a
    machine-adjudicated rule makes a set exploratory."""
    from mas.core import collapse

    task_id, _, _ = promoted_pair(core)
    before = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    assert before["acceptance_label"] == "prespecified" and before["acceptance_reasons"] == []

    collapse.collapse(core, task_id, by=OPERATOR, dry_run=False)
    after = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    assert after["acceptance_label"] == "exploratory"
    assert any("no person confirmed that" in reason for reason in after["acceptance_reasons"])
    assert any("held out of this set because the software merged" in r for r in after["acceptance_reasons"])
    (record,) = collapse.records(core, task_id)
    assert record["approval_kind"] == "software_status" and record["confirmed_by_a_person"] is False
    assert record["actor"] == {"kind": "system", "id": "criterion-collapse", "role": "registry"}
    assert not [e for e in core.journal.replay(task_id) if e.event_type == "human.review_decided"]


def test_a_dry_run_writes_nothing_to_the_journal(core):
    """`collapse` defaults to the dry path, so the real run is the explicit absence of `--dry-run`: this
    rewrites an append-only registry, and a caller that has not decided must not change it."""
    from mas.core import collapse

    task_id, (attr_chembl, _), (attr_gtopdb, _) = promoted_pair(core)
    before = [(e.seq, e.event_id) for e in core.journal.replay(task_id)]

    planned = collapse.collapse(core, task_id, by=OPERATOR)
    assert planned["dry_run"] is True
    assert [(e.seq, e.event_id) for e in core.journal.replay(task_id)] == before
    assert collapse.records(core, task_id) == []
    (group,) = planned["collapsed"]
    assert group["collapse_id"] is None
    assert group["surviving"]["attribute_ref"] == attr_chembl
    assert [m["attribute_ref"] for m in group["superseded"]] == [attr_gtopdb]
    assert group["routes_before"] == ["pchembl_values"] and group["routes_after"] == ["pchembl_values",
                                                                                     "gtopdb_affinity"]
    # the plan is the same whether or not it is applied, so the printed plan is what the real run does
    applied = collapse.collapse(core, task_id, by=OPERATOR, dry_run=False)["collapsed"][0]
    assert {k: v for k, v in applied.items() if k != "collapse_id"} == {k: v for k, v in group.items()
                                                                       if k != "collapse_id"}


def test_a_person_can_withdraw_a_collapse_and_the_merged_away_rule_scores_again(core):
    """`adjudication.reopen` cannot serve: it needs a queue item folded to `machine_adjudicated`, which
    only a `machine_adjudication` record produces, and it reverses nothing in the registry -- it
    withdraws an agent's verdict and carries the subject back to a terminal. A collapse resolves no
    queue item and is no verdict, and what has to come back is the supersession `confirm_rule_set`
    reads. So the reversal is recorded in `reopen`'s shape: the collapse stays in the journal as what
    the software did, and withdrawing is not deciding -- it leaves the duplication unresolved."""
    from mas.core import adjudication, collapse

    task_id, (_, rule_chembl), (_, rule_gtopdb) = promoted_pair(core)
    collapse.collapse(core, task_id, by=OPERATOR, dry_run=False)
    (record,) = collapse.records(core, task_id)
    assert review.items(core, [task_id]) == {}       # there is no queue item for `reopen` to reopen
    with pytest.raises(adjudication.AdjudicationError, match="not machine-adjudicated"):
        adjudication.reopen(core, {"item_id": "q_absent", "state": None, "stream_id": task_id,
                                   "subject": {"kind": "rule_version", "id": rule_chembl}},
                            by=OPERATOR, reason_text="a pharmacologist is available now")

    with pytest.raises(collapse.CollapseError, match="say why"):
        collapse.withdraw(core, task_id, record["collapse_id"], by=OPERATOR, reason_text="   ")
    assert collapse.withdraw(core, task_id, record["collapse_id"], by=OPERATOR,
                             reason_text="the two curations disagree on this receptor") == [rule_gtopdb]
    assert [r["withdrawn"] for r in collapse.records(core, task_id)] == [True]
    with pytest.raises(collapse.CollapseError, match="already withdrawn"):
        collapse.withdraw(core, task_id, record["collapse_id"], by=OPERATOR, reason_text="again")

    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    assert rule_gtopdb in [e["rule_ref"] for e in rules["entries"]] and rules["collapsed_away"] == []
    # the withdrawal un-does the supersession, which is a fold; it cannot un-write the pooled attribute
    # version the surviving rule reads, so the set still says a machine wrote it
    assert rules["machine_collapsed"] == [record["surviving"]["rule_ref_after"]]
    assert rules["acceptance_label"] == "exploratory"
    assert any("the software wrote" in reason for reason in rules["acceptance_reasons"])
    # the collapse is still on the record, and the pooled attribute version is not deleted: the quantity
    # is registered twice again, which is the state the person is being asked about
    assert record["collapse_id"] in {e.payload.get("collapse_id") for e in core.journal.replay(task_id)}
    assert criteria.load(core, record["surviving"]["attribute_ref_after"], task_id)["collapsed_by"] \
           == record["collapse_id"]
    # and the next run of the command refuses the group rather than collapsing it again: a reversal a
    # re-run quietly overturns is not a reversal
    again = collapse.collapse(core, task_id, by=OPERATOR, dry_run=False)
    assert again["collapsed"] == [] and record["collapse_id"] in again["refused"][0]["refused"][0]
    assert "would overrule them" in again["refused"][0]["refused"][0]


def test_a_collapse_will_not_stop_a_rule_an_expert_approved_from_scoring(core):
    """The collapse holds the merged-away rules out of the confirmed set, and where a person approved
    one of them that is the software overruling an expert decision. "The routes ask one question"
    authorises pooling the routes; it authorises nothing about an `hd_`."""
    from mas.core import collapse

    hard = {"rule_kind": "hard_exclusion", "predicate_form": "threshold", "cutoff_basis": "source_stated_value",
            "cutoff": {"comparator": ">=", "value": 7.0, "unit": "pChEMBL"}}
    task_id, _, (_, rule_gtopdb) = promoted_pair(core, first_rule=hard, second_rule=hard)
    item = next(i for i in review.items(core, [task_id]).values() if i["subject"]["id"] == rule_gtopdb)
    review.decide(core, item, decision="approve", actor=OPERATOR, reason_text="", entry="interactive")

    (group,) = collapse.collapse(core, task_id, by=OPERATOR, dry_run=False)["refused"]
    assert any(rule_gtopdb in why and "a person has to collapse what a person confirmed" in why
               for why in group["refused"])
    assert collapse.records(core, task_id) == []


def test_a_collapse_group_that_states_no_subject_is_refused_because_its_quantity_key_names_nothing(core):
    """A quantity key is (capability set, unit, direction, subject parameters), and only the subject
    identifies a measurement: `interaction_evidence_lookup` answers `pchembl_values`, `gtopdb_affinity`
    and `mechanism_records` alike, so the capability is a transport. Measured on the fixtures in this
    file: "Oral bioavailability" (%, higher_better) and "Plasma protein binding" (%, higher_better) have
    the same key exactly. Collapsing on it would merge two different quantities and call it a duplicate.
    """
    from mas.core import collapse
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    bioavailability = lit_attribute("Oral bioavailability", "%")
    binding = lit_attribute("Plasma protein binding", "%")
    assert collapse.quantity_key(bioavailability) == collapse.quantity_key(binding)
    assert not criteria.subject_parameters(bioavailability["evidence_request"])
    rule = {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
            "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty"}
    for attribute in (bioavailability, binding):
        criteria.propose(core, task_id, dict(attribute, supporting_claim_refs=[]), dict(rule), by=OPERATOR)
    groups = collapse.plan(core, task_id)
    assert groups, "the two attributes do share a quantity key, so a group must be formed and then refused"
    assert all(g["refused"] for g in groups)
    assert any("no subject parameters" in reason for g in groups for reason in g["refused"])
    before = len(core.journal.replay(task_id))
    collapse.collapse(core, task_id, by=OPERATOR, dry_run=False)
    assert len(core.journal.replay(task_id)) == before, "a refused group must write nothing"


def test_the_repair_budget_survives_a_store_reopen_and_a_merge_does_not_reset_it(core):
    """F1. `refine_stage` wrote `refine_count` onto the item and `filter_stage` read it to enforce
    `max_refines`, but it was absent from `pool.ITEM_FIELDS`, so `_record` dropped it and a fold read
    0. The budget reset on every reopen and round continuation, so the limit bounded nothing durably.
    A merged child must inherit its group's largest count too, or merging would be the cheapest way
    past the limit."""
    from mas.core import pool as pool_mod
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    writer = pool_mod.Pool(core, task_id, by=OPERATOR, run_id="run_x").at("refine", 1)
    item = {"attribute": lit_attribute("Oral bioavailability", "%"), "rule": {}, "supporting_claim_ids": ["c1"],
            "refine_count": 2}
    criterion_id = writer.add(item, reason_text="first")

    # the counter must come back from a fresh fold, which is what a reopened store or a later round does
    entry = pool_mod.fold(core, task_id)[criterion_id]
    assert entry["item"]["refine_count"] == 2, "the repair budget was dropped on persistence"

    revised = pool_mod.Pool(core, task_id, by=OPERATOR, run_id="run_x").at("refine", 2)
    revised.revise(entry, dict(entry["item"], refine_count=3), reason_text="again", reason_kind="refined")
    assert pool_mod.fold(core, task_id)[criterion_id]["item"]["refine_count"] == 3

    # a merged child inherits the largest count in its group rather than starting over
    from mas.core.derivation_stages import _item
    group = [{"item": {"refine_count": 3}}, {"item": {"refine_count": 1}}, {"item": {}}]
    child = _item({"attribute": {}, "rule": {}, "supporting_claim_ids": []},
                  refine_count=max(int(e["item"].get("refine_count") or 0) for e in group))
    assert child["refine_count"] == 3
