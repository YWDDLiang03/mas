"""The criteria pool workflow (core/pool.py, derivation_stages.py, derivation_run.py):
broad proposal, filter, distill, merge, refine, promotion, stall stop, budget stop, and
continuation into a second round. Scripted models; no network."""

from __future__ import annotations

import json

import pytest

from mas.adapters.drug.registration import EVIDENCE_CATALOG
from mas.core import (assessor, bound_support, criteria, derivation_run, derivation_stages, models, pool,
                      review, task, vocab)
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
                merged = dict(first, attribute=child_attribute(
                    first["attribute"], name="Oral bioavailability",
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


def test_merge_offers_a_unit_and_direction_bucket_to_the_adjudicator_rather_than_pairing_on_wording():
    """A deliberate trade, and the reason the pool could not reduce.

    Grouping used to need a name+definition Jaccard of at least 0.35. Measured: the pair this stage
    exists for scores 0.14 on names and 0.10 with definitions, because one definition is terse and
    the other verbose prose -- and the clean derivation of 14 October 2026 produced 59
    literature-bound proposals of which merge grouped zero across every iteration. The design is
    "deterministic pairing, then the adjudicator decides", and a pairing that strict means the
    adjudicator is never asked, so many proposals can never become few quantities.

    Grouping is therefore coarse on purpose: a shared canonical unit, direction and dimension is a
    weak signal, which is why it is handed to a model that reads the definitions instead of merging
    anything by itself. Different units and different directions still never meet, and every merge
    the adjudicator proposes must validate, may cite only its parents' claims, and may not reach for
    a route neither parent had. The cost of this trade is that a bad merge is now the adjudicator's
    to make rather than impossible, which is why each one is recorded with its reasoning.
    """
    from mas.core.derivation_stages import merge_groups, MERGE_GROUP_MAX

    def entry(i, name, unit="%", direction="higher_better"):
        return {"criterion_id": f"cri_{i}", "version": 1,
                "item": {"attribute": lit_attribute(name, unit, direction=direction)}}

    groups = merge_groups([entry(1, "Oral bioavailability"), entry(2, "Absolute oral bioavailability"),
                           entry(3, "Oral bioavailability", unit="h"),
                           entry(4, "Oral bioavailability", direction="lower_better"),
                           entry(5, "Plasma protein binding")])
    # one bucket: same unit, same direction. The differently-united and differently-directed ones
    # are alone and so are not offered at all.
    assert [sorted(e["criterion_id"] for e in g) for g in groups] == [["cri_1", "cri_2", "cri_5"]]

    # a bucket wider than one prompt is split rather than sent whole
    wide = [entry(i, f"Reported quantity {i:02d}") for i in range(20)]
    split = merge_groups(wide)
    assert len(split) > 1 and all(len(g) <= MERGE_GROUP_MAX for g in split)
    assert sum(len(g) for g in split) == len(wide)


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


def child_attribute(attribute, *routes, **extra):
    """One attribute as a reduction states it. `MERGE_SCHEMA` requires `evidence_requests`, which is the one
    spelling `ADJUDICATOR_SYSTEM` offers, so a reply keeping a route under the singular `evidence_request`
    never reaches the gate -- `models.validate` asks for it again first."""
    return pooled(*(routes or criteria.evidence_routes(attribute)), base=attribute, **extra)


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


def test_a_literature_route_joins_database_routes_only_where_one_scale_and_one_reduction_are_declared():
    """Two routes on one attribute are two broker calls pooled under one aggregation. A literature
    route is not that: it is a search, a read and a quote-checked extraction. `evidence.gather` now
    runs both halves for one cell, so what is left to decide is pooling -- and the policy is set for
    exactly one shape of quantity: a quantitative attribute with a unit, reduced by a numeric
    aggregation, where every claim is checked against that one scale (`assessor.usable_claims`
    converts a commensurable unit and sets anything else aside). That is what a required receptor's
    potency is: one quantity, two curations and a published selectivity table, pooled by `median`.

    Everything else is still refused, because nothing about it is defined: `consensus` asks whether
    sources agree, and agreement between a curated record and a read passage is a question nobody
    has answered; an attribute with no unit has no scale to check a passage against.
    """
    literature_route = {"capability": "literature_retrieval", "question_kind": "search",
                        "parameters": {"query_template": "({names}) AND CSF1R affinity"}}
    three_routes = pooled(CHEMBL_POTENCY["evidence_request"], GTOPDB_AFFINITY["evidence_request"], literature_route)
    criteria.check_attribute(three_routes)
    assert criteria.is_literature_bound(three_routes)
    assert criteria.literature_route(three_routes) is literature_route, "by capability, never by position"
    for refused in (dict(three_routes, aggregation="consensus"),
                    dict(three_routes, measurement_kind="categorical", unit=None),
                    {k: v for k, v in three_routes.items() if k != "aggregation"}):
        with pytest.raises(criteria.InvariantViolation, match="mixes a literature route"):
            criteria.check_attribute(refused)
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


def test_propose_reuses_only_explicit_completed_slices_without_repeating_model_or_pool_writes(core):
    calls = []
    def script(request):
        calls.append(request.metadata["question"])
        return {"proposals": [proposal(CHEMBL_POTENCY, "claim_second")], "considered_and_rejected": []}

    ctx = pool_of(core, script, [("claim_first", CHEMBL_POTENCY)],
                  task_id="task_proposal_resume", run_id="run_proposal_resume")
    ctx.claims_by_id["claim_second"] = dict(ctx.claims_by_id["claim_first"], claim_id="claim_second")
    claims = list(ctx.claims_by_id.values())
    ctx.proposal_claim_batch_size = 1
    ctx.completed_proposal_slices = {"target_coverage": {1}}
    dimension = {"dimension": "target_coverage", "focus": "required target measurements"}
    outcome = derivation_stages.propose(ctx, dimension, claims)
    assert outcome["added"] == 1 and outcome["reused_slice_count"] == 1 and outcome["reused_slices"] == [1]
    assert len(calls) == 1 and "slice 2/2" in calls[0] and len(pool.fold(core, ctx.task_id)) == 2
    events = core.journal.replay(ctx.run_id)
    (completed,) = [e for e in events if e.event_type == "proposal.slice_completed"]
    assert completed.payload["slice"] == 2 and completed.payload["claim_ids"] == ["claim_second"]
    assert completed.payload["claims_sha256"] == derivation_stages.sha256_hex(claims[1:])
    assert completed.payload["ordered_claim_ids_sha256"] == derivation_stages.sha256_hex(["claim_first", "claim_second"])
    refs = {f"{e['criterion_id']}@v{e['version']}" for e in pool.fold(core, ctx.task_id).values()}
    assert set(completed.payload["added_criterion_refs"]) <= refs
    assert max(e.seq for e in events if e.event_type == "agent.finished") < completed.seq
    # An explicitly fixed complete dimension is a zero-call/zero-add continuation.
    ctx.completed_proposal_slices["target_coverage"].add(2)
    outcome = derivation_stages.propose(ctx, dimension, claims)
    assert outcome["added"] == 0 and outcome["reused_slice_count"] == 2 and len(calls) == 1
    assert core.journal.replay(ctx.run_id)[-1].seq == completed.seq


def test_proposal_slice_is_not_completed_when_only_part_of_a_successful_reply_reaches_pool(core, monkeypatch):
    def script(request):
        return {"proposals": [proposal(CHEMBL_POTENCY, "claim_one"), proposal(GTOPDB_AFFINITY, "claim_one")],
                "considered_and_rejected": []}
    ctx = pool_of(core, script, [], task_id="task_partial_slice", run_id="run_partial_slice")
    claim = {"claim_id": "claim_one", "source_ref": "src_synthetic", "value": 8, "unit": "pChEMBL",
             "determination_basis": "measured", "location": {"quoted_span": "a synthetic target measurement"}}
    ctx.claims_by_id["claim_one"] = claim
    add, added = ctx.pool.add, []
    def interrupted_add(*args, **kwargs):
        if added:
            raise InterruptedError("synthetic interruption before the second pool commit")
        value = add(*args, **kwargs)
        added.append(value)
        return value
    monkeypatch.setattr(ctx.pool, "add", interrupted_add)
    with pytest.raises(InterruptedError):
        derivation_stages.propose(ctx, {"dimension": "target_coverage", "focus": "measurements"}, [claim])
    events = core.journal.replay(ctx.run_id)
    assert any(e.event_type == "agent.finished" and e.payload["schema_ok"] for e in events)
    assert len(pool.fold(core, ctx.task_id)) == 1
    assert not any(e.event_type == "proposal.slice_completed" for e in events)


def test_a_merge_may_pool_its_parents_routes_into_one_attribute(core):
    ctx = two_curations_pool(core, merge_script())
    assert derivation_stages.merge_stage(ctx, 1) == {"groups": 1, "merged": 1, "consolidated": 0,
                                                     "kept_separate": 0, "refused": 0, "not_reduced": []}
    folded = pool.fold(core, "task_merge")
    child = next(e for e in folded.values() if e["parents"])
    assert sorted(r["question_kind"] for r in criteria.evidence_routes(child["item"]["attribute"])) == \
           ["gtopdb_affinity", "pchembl_values"]
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

# --- a family of distinct endpoints ---------------------------------------------------------
# What a dry check of `merge_groups` over the live pool of 89 proposals produced on 14 October 2026:
# ten groups, two of them eight *distinct* toxicity endpoints each (any-grade incidences; grade >=3
# incidences), sharing a unit, a direction and a dimension while measuring
# different things. `merge` is unavailable to them by its own rule -- they are not one quantity, in
# one unit and direction, for one purpose -- so duplication was never what stood between 89
# proposals and the handful of attributes a screen applies. Reducing them needs the second
# operation: a family abstracted into the criterion that decides, which is a scientific judgement
# and is therefore recorded as a consolidation and not as a merge.
TOXICITY_FAMILY = [("Grade >=3 diarrhea incidence", "toxicological_safety"),
                   ("Grade >=3 fatigue incidence", "toxicological_safety"),
                   ("Grade >=3 hyperphosphatemia incidence", "toxicological_safety")]
SHARED_PROPERTY = ("every member is a grade >=3 treatment-related adverse event that forces a dose "
                   "reduction or stops treatment, which is what disqualifies a chronic oral drug")


def burden_attribute(**extra):
    """The criterion a screen would actually apply to the family: one toxicity burden, with its own
    literature query, which is a retrieval knob rather than a reach for a source no member had."""
    return dict(lit_attribute("Grade >=3 treatment-related toxicity burden", "%", direction="lower_better"),
                definition="Share of treated patients with any grade >=3 treatment-related adverse event",
                **extra)


def family_pool(core, script, members=TOXICITY_FAMILY, *, task_id="task_family", run_id="run_family",
                spare_claim=False):
    """A pool holding one literature-bound candidate per (name, dimension), each citing its own claim.

    With `spare_claim` the ledger also holds a claim no member cites, which is how a child that cites
    evidence beyond its parents can still be a child whose every other field validates.
    """
    writer = pool.Pool(core, task_id, by=OPERATOR, run_id=run_id).at("propose", 0)
    claims_by_id = {}

    def claim(claim_id, text):
        claims_by_id[claim_id] = {"claim_id": claim_id, "source_ref": f"src_{claim_id}",
                                  "determination_basis": "measured", "value": 12.0, "unit": "%",
                                  "location": {"quoted_span": text}}

    for index, (name, dimension) in enumerate(members):
        claim_id = f"claim_tox_{index}"
        claim(claim_id, f"{name.lower()} was 12% of treated patients")
        writer.add(dict(proposal(lit_attribute(name, "%", direction="lower_better"), claim_id), dimension=dimension),
                   reason_text=f"proposed for {dimension}")
    if spare_claim:
        claim("claim_spare", "treatment was stopped for toxicity in 12% of patients")
    return derivation_stages.StageContext(
        core=core, roster=roster_for(script), task_id=task_id, run_id=run_id,
        task_context={"objective_text": SPEC["objective_text"], "constraints": [],
                      "scope_entities": SPEC["scope_entities"]},
        catalog=EVIDENCE_CATALOG, claims_by_id=claims_by_id, reference_labels=[], pool=writer)


def consolidate_script(*, members=None, shared_property=SHARED_PROPERTY, family_aggregation="worst_member",
                       attribute=None, claims=None, member_names=None):
    """An adjudicator that consolidates each group into one toxicity-burden criterion."""
    def script(request):
        question = request.metadata.get("question", "")
        assert question == "adjudicate merges", question
        groups = json.loads(request.messages[0]["content"].split("Groups:\n", 1)[1].split("\n\nCited claims:")[0])
        decisions = []
        for group in groups:
            folded = [m for m in group["members"]
                      if (members is None or m["index"] in members)
                      and (member_names is None or m["attribute"]["name"] in member_names)]
            cited = claims if claims is not None else sorted({c for m in folded for c in m["supporting_claim_ids"]})
            item = dict(proposal(child_attribute(attribute or burden_attribute()), "unused"),
                        supporting_claim_ids=cited)
            decisions.append({"group": group["group"], "action": "consolidate",
                              "consolidated": dict(item, members=[m["index"] for m in folded],
                                                   shared_property=shared_property,
                                                   family_aggregation=family_aggregation),
                              "reason": "three specific endpoints a screen applies as one toxicity burden"})
        return {"decisions": decisions}
    return script


def test_a_family_of_distinct_endpoints_sharing_a_screen_relevant_property_consolidates_into_one_criterion_that_names_what_it_subsumes(core):
    ctx = family_pool(core, consolidate_script())
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["groups"] == 1 and stats["consolidated"] == 1 and stats["merged"] == 0 and stats["refused"] == 0

    child = next(e for e in pool.fold(core, "task_family").values() if e["parents"])
    declared = child["item"]["consolidation"]
    assert declared["shared_property"] == SHARED_PROPERTY
    assert declared["family_aggregation"] in derivation_stages.FAMILY_AGGREGATIONS
    # the whole point of the field: a reviewer reads which specific endpoints this abstraction replaced,
    # by lineage id and by name, and can say that one of them did not belong in it
    assert sorted(s["name"] for s in declared["subsumes"]) == sorted(name for name, _ in TOXICITY_FAMILY)
    assert {s["criterion_id"] for s in declared["subsumes"]} == \
           {ref.split("@v")[0] for ref in child["parents"]}
    criteria.check_attribute(child["item"]["attribute"])        # and the consolidated criterion is registrable


def test_a_consolidation_whose_shared_property_merely_restates_the_unit_is_refused(core):
    """The failure mode of an abstraction is breadth, and "they are all percentages" is both true of the
    group and no reason to replace three measurements with one. The group already agrees on a unit, a
    direction and a dimension by construction, so a shared property that says only those says nothing."""
    ctx = family_pool(core, consolidate_script(shared_property="They are all percentages, lower is better"))
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["refused"] == 1 and stats["consolidated"] == 0
    (refusal,) = [d for d in stats["not_reduced"] if d["outcome"] == "refused"]
    assert "shared_property" in refusal["reason"] and "no property to screen on" in refusal["reason"]
    assert not [e for e in pool.fold(core, "task_family").values() if e["parents"]]
    # a restatement dressed up in the dimension's own words is the same empty claim
    ctx = family_pool(core, consolidate_script(shared_property="all of these toxicity endpoints are incidence rates"),
                      task_id="task_family_2")
    assert derivation_stages.merge_stage(ctx, 1)["refused"] == 1


def _family_group(direction: str = "lower_better") -> list[dict]:
    """The merge group the gate sees: one entry per endpoint, already agreeing on unit, direction and
    dimension, which is how `merge_groups` formed the two eight-member toxicity groups."""
    return [{"criterion_id": f"cri_{i}", "version": 1,
             "item": {"attribute": lit_attribute(name, "%", direction=direction), "dimension": dimension}}
            for i, (name, dimension) in enumerate(TOXICITY_FAMILY)]


# Three pooled values whose maximum, minimum and median all differ, so a cell scored under one reduction is
# distinguishable from the same cell scored under either other one.
FAMILY_VALUES = (4.0, 12.0, 31.0)
# The reductions, written out independently of `assess_cell`, so that "the assessor honours this
# aggregation" is an assertion about its output rather than a restatement of its implementation. An
# aggregation absent from this table is one no test here can confirm, which is the point: a family
# aggregation mapped to `consensus` would fail rather than quietly pass.
POOLED_REDUCTIONS = {"max": max, "min": min, "median": lambda values: sorted(values)[len(values) // 2]}


def _cell(attribute: dict, *, cutoff: dict | None = None, values=FAMILY_VALUES) -> tuple:
    """(value, verdict) `assessor.assess_cell` puts in one cell of `attribute` over claims carrying `values`.

    A consolidated criterion arrives here as one attribute over one pooled claim set -- there are no member
    cells left to reduce -- so this is the whole of what a declared family aggregation can be executed as.
    """
    rule = {"rule_id": "rule_burden", "version": 1, "rule_kind": "preference",
            "predicate_form": "threshold" if cutoff else "ordering", "cutoff": cutoff,
            "cutoff_basis": "source_stated_value" if cutoff else "none_evidence_insufficient"}
    claims = [{"claim_id": f"claim_{index}", "source_ref": f"src_{index}", "admission_state": "admitted",
               "evidence_kind": "peer_reviewed", "determination_basis": "measured", "value": value, "unit": "%",
               "location": {"quoted_span": f"the endpoint was {value}% of treated patients"}}
              for index, value in enumerate(values)]
    assessment, _ = assessor.assess_cell(candidate={"candidate_id": "cand_1"},
                                         attribute=dict(attribute, attribute_id="attr_burden", version=1),
                                         rule=rule, rule_set_ref="rules@v1", claims=claims, resolved=True)
    return assessment["value"], assessment["verdict"]


def test_a_consolidation_declaring_worst_member_computes_the_worst_value_in_the_attributes_declared_direction():
    """`worst_member` is the reduction whose execution depends on the direction, and the inversion is silent:
    with `lower_better` the least favourable member is the largest value, with `higher_better` the smallest.
    Reversed, a candidate would be ranked on its best endpoint while its card named its worst. Asserted on a
    family whose maximum and minimum differ, and against the same family's median, which is the reduction a
    consolidated criterion used to be scored under whatever it declared.
    """
    declared = {"members": [0, 1, 2], "shared_property": SHARED_PROPERTY, "family_aggregation": "worst_member"}

    members, problem, executes_as = derivation_stages._consolidation(
        _family_group("lower_better"), declared, burden_attribute(direction="lower_better"))
    assert (len(members), problem, executes_as) == (3, None, "max")
    assert _cell(burden_attribute(direction="lower_better", aggregation=executes_as)) == (31.0, "pass")
    # the worst member decides the verdict, where the median of that same family would have passed
    low_cutoff = {"comparator": "<=", "value": 20, "unit": "%"}
    assert _cell(burden_attribute(direction="lower_better", aggregation=executes_as), cutoff=low_cutoff) == \
           (31.0, "fail")
    assert _cell(burden_attribute(direction="lower_better", aggregation="median"), cutoff=low_cutoff) == \
           (12.0, "pass")

    members, problem, executes_as = derivation_stages._consolidation(
        _family_group("higher_better"), declared, burden_attribute(direction="higher_better"))
    assert (len(members), problem, executes_as) == (3, None, "min")
    assert _cell(burden_attribute(direction="higher_better", aggregation=executes_as)) == (4.0, "pass")
    high_cutoff = {"comparator": ">=", "value": 10, "unit": "%"}
    assert _cell(burden_attribute(direction="higher_better", aggregation=executes_as), cutoff=high_cutoff) == \
           (4.0, "fail")
    assert _cell(burden_attribute(direction="higher_better", aggregation="median"), cutoff=high_cutoff) == \
           (12.0, "pass")


def test_a_consolidation_whose_declared_family_aggregation_and_attribute_aggregation_disagree_cannot_score_as_if_they_agreed(core):
    """The adjudicator is asked for the attribute's own fields, `aggregation` among them, and nothing tells it
    which aggregation its family reduction implies -- `consolidate_script` declares `worst_member` over an
    attribute whose own aggregation is `median`, which is what a model actually returns. So the gate derives
    the aggregation from the family reduction instead of trusting the pair to agree: the consolidation record
    never reaches the assessor, and `aggregation` is the only half of it `assess_cell` reads."""
    ctx = family_pool(core, consolidate_script(family_aggregation="worst_member"))
    assert derivation_stages.merge_stage(ctx, 1)["consolidated"] == 1
    child = next(e for e in pool.fold(core, "task_family").values() if e["parents"])
    assert child["item"]["attribute"]["aggregation"] == "max"        # not the `median` the adjudicator wrote
    assert child["item"]["consolidation"]["executes_as_aggregation"] == "max"
    assert child["item"]["consolidation"]["replaced_declared_aggregation"] == "median"
    # and the stored attribute scores as the worst member: under the median it would have read 12.0 and passed
    assert _cell(child["item"]["attribute"], cutoff={"comparator": "<=", "value": 20, "unit": "%"}) == \
           (31.0, "fail")


def test_every_value_left_in_the_family_aggregation_vocabulary_is_executable_by_the_assessor():
    """The requirement the field was first added with was a declaration: eight reductions were registered and
    `assess_cell` computed none of them, so a consolidated criterion could say `worst_member` and be scored
    on a median. The six that nothing could execute are gone (`vocab.criterion_family_aggregation` says which
    and why); this is what keeps a seventh from being registered without being wired, in either direction --
    a value the vocabulary offers and the table does not map, or a mapping to an aggregation `assess_cell`
    does not perform."""
    registered = set(vocab.DOMAINS["criterion_family_aggregation"])
    assert registered == set(assessor.FAMILY_AGGREGATION_EXECUTION)
    for family in sorted(registered):
        executable = {}
        for direction in criteria.DIRECTIONS:
            aggregation, problem = assessor.family_aggregation_execution(family, direction)
            assert (aggregation is None) != (problem is None), (family, direction)
            if aggregation is not None:
                executable[direction] = aggregation
        assert executable, family
        for direction, aggregation in executable.items():
            assert aggregation in criteria.AGGREGATIONS and aggregation in POOLED_REDUCTIONS, (family, direction)
            assert _cell(burden_attribute(direction=direction, aggregation=aggregation)) == \
                   (POOLED_REDUCTIONS[aggregation](FAMILY_VALUES), "pass"), (family, direction)
            # and the gate compiles the declaration into exactly that aggregation, so the value is reachable
            group = _family_group(direction)
            assert derivation_stages._consolidation(
                group, {"members": [0, 1, 2], "shared_property": SHARED_PROPERTY, "family_aggregation": family},
                burden_attribute(direction=direction)) == (group, None, aggregation), (family, direction)


def test_a_consolidation_whose_declared_family_aggregation_would_not_be_computed_is_refused():
    """A consolidated criterion nobody can compute is worse than the family it replaced, and prose ("the
    overall burden of all of them") does not say what to compute, so the reduction over the family is a
    registered vocabulary (`criterion_family_aggregation`) -- and, registered or not, it is refused unless it
    maps to an aggregation `assess_cell` performs for this attribute's direction: `worst_member` over a
    `within_range` attribute names no end of the scale as the worst one.

    The gate is tested directly because the schema carries the same vocabulary as an enum and a structured
    reply never reaches the gate with an unregistered one -- the scripted adapter raises `parse_failed`
    first, as a provider enforcing the schema would. The enum is a request; this is the enforcement, and a
    provider that answers prose or a repaired reply that drops the enum still has to get past it.
    """
    group = _family_group()
    declared = {"members": [0, 1, 2], "shared_property": SHARED_PROPERTY,
                "family_aggregation": "the overall burden of all of them"}
    members, problem, executes_as = derivation_stages._consolidation(group, declared, burden_attribute())
    assert members == group and executes_as is None
    assert "family_aggregation is not computable" in problem
    for aggregation in derivation_stages.FAMILY_AGGREGATIONS:
        stands = derivation_stages._consolidation(group, dict(declared, family_aggregation=aggregation),
                                                  burden_attribute())
        assert (stands[0], stands[1]) == (group, None) and stands[2] in criteria.AGGREGATIONS, aggregation
    # the same family with no aggregation declared at all is refused for the same reason
    assert "family_aggregation" in derivation_stages._consolidation(
        group, {k: v for k, v in declared.items() if k != "family_aggregation"}, burden_attribute())[1]
    # a registered reduction a direction cannot order is refused rather than guessed at
    _, problem, executes_as = derivation_stages._consolidation(
        _family_group("within_range"), dict(declared, family_aggregation="worst_member"),
        burden_attribute(direction="within_range"))
    assert executes_as is None and "which end of the scale is worse" in problem


def test_a_consolidation_that_subsumes_one_member_or_spans_two_dimensions_is_refused(core):
    """Two different ways the declaration stops being a family. One member is no reduction at all -- the
    pool would lose a lineage and gain an abstraction of that one lineage. Two dimensions have no shared
    property one screening criterion can state: the group can span them because wording alone is enough
    to pair a literature-bound item, and the same endpoint proposed under two dimension passes is the
    ordinary way it happens."""
    ctx = family_pool(core, consolidate_script(members=[0]))
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["refused"] == 1 and stats["consolidated"] == 0
    assert "a family is two or more endpoints" in stats["not_reduced"][0]["reason"]

    spanning = TOXICITY_FAMILY[:2] + [("Grade >=3 transaminase elevation incidence", "metabolic_stability")]
    ctx = family_pool(core, consolidate_script(), members=spanning, task_id="task_family_span")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["groups"] == 1, "the three are one group, or this test proves nothing"
    assert stats["refused"] == 1 and stats["consolidated"] == 0
    assert "spans dimensions" in stats["not_reduced"][0]["reason"]
    assert not [e for e in pool.fold(core, "task_family_span").values() if e["parents"]]


def test_a_consolidation_may_not_cite_evidence_no_member_had_nor_a_route_no_member_declared(core):
    """The constraints a merge already carries, for the reason a merge carries them: a reduction combines
    what the pool already has. An abstraction is not a licence to cite a claim the family never cited or
    to read a source it never read -- and the route check measures the source and the subject, not the
    query template, so the consolidated criterion may ask the literature about the family it now stands
    for while a reach for a different capability is still refused."""
    ctx = family_pool(core, consolidate_script(claims=["claim_tox_0", "claim_spare"]), spare_claim=True)
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["refused"] == 1 and stats["consolidated"] == 0
    assert "cites claims no parent had: ['claim_spare']" in stats["not_reduced"][0]["reason"]
    # and the claim it reached for is a real, resolvable claim: the refusal is about whose it was
    assert ctx.validate(dict(proposal(burden_attribute(), "claim_spare"))) == []

    descriptor = {"capability": "property_estimate", "question_kind": "computed_property",
                  "identifier_scheme": "inchikey", "parameters": {"property": "MolecularWeight"}}
    attribute = burden_attribute(evidence_request=descriptor)
    ctx = family_pool(core, consolidate_script(attribute=attribute), task_id="task_family_route")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["refused"] == 1 and stats["consolidated"] == 0
    assert "1 evidence route(s) no parent declared" in stats["not_reduced"][0]["reason"]
    # The provenance refusal remains visible beside the now-detected incompatible unit.
    assert any(p.startswith("units:") for p in ctx.validate(dict(proposal(attribute, "claim_tox_0"))))


def test_the_parents_go_to_merged_away_pointing_at_the_child_and_the_pool_trajectory_shows_the_reduction(core):
    """Lineage is the merge's, so nothing is deleted and the reduction is readable both ways; the claim is
    not the merge's, so the records say `consolidate` and `family_consolidated` where a merge says `merge`
    and `duplicate_merged`. A reader of one lineage sees which operation retired it, and a reader of the
    trajectory sees three criteria leave and one arrive in the merge step of iteration 1."""
    ctx = family_pool(core, consolidate_script())
    derivation_stages.merge_stage(ctx, 1)
    folded = pool.fold(core, "task_family")
    child = next(e for e in folded.values() if e["parents"])
    parents = [folded[ref.split("@v")[0]] for ref in child["parents"]]
    assert len(parents) == 3
    for parent in parents:
        assert parent["state"] == "merged_away" and parent["children"] == [f"{child['criterion_id']}@v1"]
        assert parent["history"][-1]["operation"] == "consolidate"
        assert parent["history"][-1]["reason_kind"] == "family_consolidated"
    assert child["history"][-1]["operation"] == "consolidate"

    (step,) = [s for s in pool.trajectory(core, "task_family") if s["stage"] == "merge"]
    assert step["iteration"] == 1 and step["merged_away"] == 3
    assert step["reasons"] == {"family_consolidated": 4}        # three parents retired, one child written
    assert step["live_after"] == 1, "three endpoints in, one criterion out: the pool got smaller"


def test_a_merge_of_two_databases_views_of_one_quantity_is_still_a_merge_and_not_a_consolidation(core):
    """The case the merge instruction exists for keeps its own operation. Those two attributes are one
    measurement curated twice -- nothing is abstracted, nothing is subsumed, no shared property is claimed
    -- so the record must not say a judgement was made about which endpoints a screen should treat as one
    family. A consolidation is the stronger claim and the record has to be able to tell them apart."""
    ctx = two_curations_pool(core, merge_script())
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["merged"] == 1 and stats["consolidated"] == 0 and stats["not_reduced"] == []
    folded = pool.fold(core, "task_merge")
    child = next(e for e in folded.values() if e["parents"])
    assert child["item"].get("consolidation") is None
    assert {h["operation"] for e in folded.values() for h in e["history"][-1:]} == {"merge"}
    assert {h["reason_kind"] for e in folded.values() for h in e["history"][-1:]} == {"duplicate_merged"}


def test_the_adjudicator_keeping_a_group_separate_remains_a_valid_outcome_and_is_recorded(core):
    """Two operations do not make a reduction obligatory. Three distinct toxicity endpoints with no shared
    screen-relevant property are three criteria, and the gate must leave them alone -- but a count of zero
    is what made "no merges in any historical round" unreadable: a reviewer could not tell a pool of
    genuinely distinct criteria from a gate refusing everything the adjudicator proposed. So the stage
    result carries each unreduced group's reason, and `_stage_recorder` puts it in the journal."""
    def keeps_separate(request):
        assert request.metadata.get("question") == "adjudicate merges", request.metadata
        groups = json.loads(request.messages[0]["content"].split("Groups:\n", 1)[1].split("\n\nCited claims:")[0])
        return {"decisions": [{"group": g["group"], "action": "keep_separate",
                               "reason": "diarrhea, fatigue and hyperphosphatemia are different liabilities "
                                         "with different management"} for g in groups]}

    ctx = family_pool(core, keeps_separate)
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats == {"groups": 1, "merged": 0, "consolidated": 0, "kept_separate": 1, "refused": 0,
                     "not_reduced": [{"group": 0, "outcome": "kept_separate", "action": "keep_separate",
                                      "reason": "diarrhea, fatigue and hyperphosphatemia are different liabilities "
                                                "with different management"}]}
    folded = pool.fold(core, "task_family")
    assert sorted(e["state"] for e in folded.values()) == ["candidate"] * 3
    assert all(e["version"] == 1 and not e["parents"] and not e["children"] for e in folded.values())


# --- what a reduction inherits from its group ------------------------------------------------
# The four refusals of 14 October 2026, the first merge in this project's history that ever reached the
# adjudicator: 9 groups over 75 repaired candidates, 5 kept separate with specific pharmacological reasons
# ("a single worst-member or median burden would be dominated by the overall TEAE rate"), and every one of
# the 4 proposed reductions refused by the gate rather than by judgement. Three consolidations because the
# child omitted `direction`, so `worst_member` had no end of the scale to call worst, while all six or eight
# members of each group declared `lower_better`; one merge because the child omitted `name` and
# `acceptable_value_sources`, which left two `literature_retrieval/search` routes returning `peer_reviewed`
# claims that the attribute no longer admitted, while both members declared `["peer_reviewed"]`. The members
# were grouped *because* `quantity_key` found they share a unit and a direction, so the stage was demanding
# that the model restate its own grouping. Measured over the 9 groups: every member of every one of them
# agrees on the unit, the direction, the measurement kind, the value sources and the determination bases.
CLINICAL_PHARMACOLOGY_FAMILY = [("Interpatient variability in terminal half-life", "metabolic_stability"),
                                ("Clearance reduction in mild hepatic impairment", "metabolic_stability"),
                                ("Susceptibility to CYP3A4 inducer-mediated exposure reduction", "metabolic_stability")]
EXPOSURE_SHARED_PROPERTY = ("every member is a percentage change in systemic exposure driven by a patient "
                            "factor or a co-medication the prescriber cannot choose, which is what makes one "
                            "fixed oral dose unsafe across a population")


def exposure_attribute(**extra):
    """The criterion a screen would apply to the clinical-pharmacology family the live merge grouped: one
    uncontrolled-exposure-variability burden over the same percent scale its members are on."""
    return dict(lit_attribute("Uncontrolled exposure variability", "%", direction="lower_better"),
                definition="Largest percentage change in systemic exposure across patient and co-medication "
                           "factors outside the prescriber's control",
                **extra)


def merge_leaving_out(*omitted, name=None, cites=True, keep_routes="all"):
    """An adjudicator that merges each group into a child stating everything its first member states except
    `omitted` -- the shape of the live merge, whose child stated neither a name nor `acceptable_value_sources`
    and kept both members' literature routes."""
    def script(request):
        assert request.metadata.get("question") == "adjudicate merges", request.metadata
        groups = json.loads(request.messages[0]["content"].split("Groups:\n", 1)[1].split("\n\nCited claims:")[0])
        decisions = []
        for group in groups:
            members = group["members"]
            routes = [r for m in members for r in criteria.evidence_routes(m["attribute"])]
            attribute = {k: v for k, v in members[0]["attribute"].items() if k not in omitted}
            if name:
                attribute["name"] = name
            attribute = child_attribute(attribute, *(routes if keep_routes == "all" else ()))
            cited = sorted({c for m in members for c in m["supporting_claim_ids"]}) if cites else []
            decisions.append({"group": group["group"], "action": "merge",
                              "merged": dict(proposal(attribute, "unused"), supporting_claim_ids=cited),
                              "reason": "one quantity described twice"})
        return {"decisions": decisions}
    return script


def test_a_consolidation_inherits_the_direction_its_group_was_formed_on_instead_of_being_refused_for_not_restating_it(core):
    """The three live consolidations, as the gate saw them: `worst_member` over a percent-united family whose
    child declared no direction. The refusal was the compilation step's -- `worst_member` is `max` under
    `lower_better` and `min` under `higher_better`, so it needs one of the two -- and the direction it needed
    was in every member of the group, which `quantity_key` keyed on to form the group at all."""
    declared = {"members": [0, 1, 2], "shared_property": SHARED_PROPERTY, "family_aggregation": "worst_member"}
    _, problem, executes_as = derivation_stages._consolidation(_family_group(), declared,
                                                               burden_attribute(direction=None))
    assert executes_as is None and "worst_member is not computable for direction None" in problem

    for members, shared, attribute, task_id in (
            (TOXICITY_FAMILY, SHARED_PROPERTY, burden_attribute(direction=None), "task_inherit_tox"),
            (CLINICAL_PHARMACOLOGY_FAMILY, EXPOSURE_SHARED_PROPERTY, exposure_attribute(direction=None),
             "task_inherit_cp")):
        ctx = family_pool(core, consolidate_script(shared_property=shared, attribute=attribute),
                          members=members, task_id=task_id, run_id=f"run_{task_id}")
        stats = derivation_stages.merge_stage(ctx, 1)
        assert stats["consolidated"] == 1 and stats["refused"] == 0, stats["not_reduced"]
        child = next(e for e in pool.fold(core, task_id).values() if e["parents"])
        assert child["item"]["attribute"]["direction"] == "lower_better"
        # and the inherited direction is what the declared reduction is compiled against, so the burden is
        # scored on the family's least favourable endpoint rather than on nothing
        assert child["item"]["consolidation"]["executes_as_aggregation"] == "max"
        assert child["item"]["attribute"]["aggregation"] == "max"
        criteria.check_attribute(child["item"]["attribute"])


def test_a_merge_inherits_the_evidence_kinds_its_members_agreed_on_and_is_still_refused_for_citing_no_claim(core):
    """The live merge's child, reproduced: no cited claims, no `acceptable_value_sources`, both members'
    literature routes. Citing no claim is the reduction's own defect and stays -- a reduction may cite only its
    parents' claims, so citing none is a criterion resting on no evidence at all. What the members did settle
    is no longer asked for."""
    ctx = family_pool(core, merge_leaving_out("acceptable_value_sources", name="Grade >=3 toxicity incidence",
                                              cites=False, keep_routes="first"),
                      members=TOXICITY_FAMILY[:2], task_id="task_merge_live", run_id="run_merge_live")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["groups"] == 1 and stats["merged"] == 0 and stats["refused"] == 1
    (refusal,) = [d for d in stats["not_reduced"] if d["outcome"] == "refused"]
    assert "evidence_support: no supporting claims cited" in refusal["reason"]
    assert "acceptable_value_sources" not in refusal["reason"], \
        "both members declared ['peer_reviewed']; the child inherits it rather than being asked for it"

    # the same child stating only what it decides -- its name, the clearest definition, the route it keeps,
    # the claims its parents cited -- is completed from the group and applied
    ctx = family_pool(core, merge_leaving_out("unit", "direction", "measurement_kind", "acceptable_value_sources",
                                              name="Grade >=3 toxicity incidence", keep_routes="first"),
                      members=TOXICITY_FAMILY[:2], task_id="task_merge_inherit", run_id="run_merge_inherit")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["merged"] == 1 and stats["refused"] == 0, stats["not_reduced"]
    attribute = next(e for e in pool.fold(core, "task_merge_inherit").values() if e["parents"])["item"]["attribute"]
    assert (attribute["unit"], attribute["direction"], attribute["measurement_kind"]) == \
           ("%", "lower_better", "quantitative")
    assert attribute["acceptable_value_sources"] == ["peer_reviewed"]
    criteria.check_attribute(attribute)


def test_a_child_contradicting_the_direction_its_group_agreed_on_is_refused_rather_than_completed_over(core):
    """Inheritance completes what a child leaves out; it must not overwrite what the child states, because a
    reduction declaring another direction is asserting something about the quantity its group was formed on.
    Measured on this family's own values (4%, 12%, 31%): `worst_member` compiled under the asserted
    `higher_better` scores 4 -- the family's *best* endpoint -- and the criterion card would call it the
    worst. That is a claim a reviewer has to be able to object to, so it is refused and recorded."""
    ctx = family_pool(core, consolidate_script(attribute=burden_attribute(direction="higher_better")),
                      task_id="task_contradict", run_id="run_contradict")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["refused"] == 1 and stats["consolidated"] == 0
    (refusal,) = [d for d in stats["not_reduced"] if d["outcome"] == "refused"]
    assert "direction 'higher_better'" in refusal["reason"] and "'lower_better'" in refusal["reason"]
    assert not [e for e in pool.fold(core, "task_contradict").values() if e["parents"]]
    assert _cell(burden_attribute(direction="higher_better", aggregation="min")) == (4.0, "pass")


def test_a_reduction_whose_members_disagree_on_what_evidence_answers_them_is_refused_and_the_ones_that_agree_may_still_consolidate(core):
    """The one field pair the group does not settle for the gate. `acceptable_value_sources` and
    `acceptable_determination_bases` decide which claims `assessor.usable_claims` keeps, so a reduction that
    admits a kind a member refused scores that member's cell on evidence it refused, and one that drops a kind
    every member accepted empties a cell that then reads as "no data" rather than as a narrowing. Neither is
    the adjudicator's to decide for a member it is retiring, so the reduction is refused and the reason names
    the disagreement -- and because a consolidation names the subset it folds in, the members that do agree
    can still be consolidated. Measured: of the 27 groups `merge_groups` forms over every lineage this store
    holds, 2 disagree on the value sources and 1 on the effective determination bases; of the 9 groups of the
    live merge, none."""
    def endpoint(name, **extra):
        return dict(lit_attribute(name, "%", direction="lower_better"), **extra)

    items = [("claim_tox_0", endpoint("Grade >=3 diarrhea incidence")),
             ("claim_tox_1", endpoint("Grade >=3 fatigue incidence")),
             ("claim_tox_2", endpoint("Grade >=3 hyperphosphatemia incidence",
                                      acceptable_value_sources=["peer_reviewed", "preprint"]))]
    ctx = pool_of(core, consolidate_script(), items, task_id="task_disagree", run_id="run_disagree")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["groups"] == 1 and stats["refused"] == 1 and stats["consolidated"] == 0
    (refusal,) = [d for d in stats["not_reduced"] if d["outcome"] == "refused"]
    assert "do not agree on acceptable_value_sources" in refusal["reason"]
    assert "'preprint'" in refusal["reason"], "the refusal names the answers, or a reader cannot act on it"

    # Prompt indices follow generated criterion IDs, so bind this subset by endpoint identity.
    agreed_names = {item["name"] for _, item in items[:2]}
    ctx = pool_of(core, consolidate_script(member_names=agreed_names), items,
                  task_id="task_subset", run_id="run_subset")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["consolidated"] == 1 and stats["refused"] == 0, stats["not_reduced"]
    folded = pool.fold(core, "task_subset")
    child = next(e for e in folded.values() if e["parents"])
    assert len(child["item"]["consolidation"]["subsumes"]) == 2
    assert {s["name"] for s in child["item"]["consolidation"]["subsumes"]} == agreed_names
    assert child["item"]["attribute"]["acceptable_value_sources"] == ["peer_reviewed"]
    assert sorted(e["state"] for e in folded.values()) == ["candidate", "candidate", "merged_away", "merged_away"]


def test_a_reductions_cutoff_is_restated_in_the_unit_its_group_fixed_so_a_synonym_is_not_a_refusal():
    """`check_rule` compares the attribute's unit with its cutoff's literally, while `assessor.UNIT_SYNONYMS`
    maps spellings one to one and converts nothing ("percent" *is* "%"), so inheriting the members' spelling
    onto a child that wrote the cutoff in a synonym -- or left the unit off a number that can only be in the
    attribute's unit -- would refuse the reduction for the inheritance's own doing. A cutoff in a canonically
    different unit is a number compared against the wrong scale and is still refused."""
    rule = {"rule_kind": "preference", "predicate_form": "threshold", "cutoff_basis": "source_stated_value",
            "cutoff": {"comparator": "<=", "value": 20, "unit": "percent"}}
    declared = {"attribute": burden_attribute(unit=None, direction=None), "rule": rule}
    completed, problem = derivation_stages._inherited_from(_family_group(), derivation_stages._FIXED_BY_GROUPING,
                                                           declared)
    assert problem is None and completed["attribute"]["unit"] == "%"
    criteria.check_rule(completed["rule"], completed["attribute"])
    with pytest.raises(criteria.InvariantViolation, match="cutoff unit"):
        criteria.check_rule(rule, completed["attribute"])      # what the refusal would have been
    for unit in (None, "%"):
        restated, _ = derivation_stages._inherited_from(
            _family_group(), derivation_stages._FIXED_BY_GROUPING,
            {"attribute": burden_attribute(unit=None, direction=None),
             "rule": dict(rule, cutoff=dict(rule["cutoff"], unit=unit))})
        criteria.check_rule(restated["rule"], restated["attribute"])
    other_scale, _ = derivation_stages._inherited_from(
        _family_group(), derivation_stages._FIXED_BY_GROUPING,
        {"attribute": burden_attribute(unit=None, direction=None),
         "rule": dict(rule, cutoff=dict(rule["cutoff"], unit="h"))})
    with pytest.raises(criteria.InvariantViolation, match="cutoff unit"):
        criteria.check_rule(other_scale["rule"], other_scale["attribute"])


def test_the_adjudicator_is_asked_for_what_a_reduction_decides_and_told_what_its_group_fixes():
    """The prompt, the schema and the gate are one contract: every field the gate fills in has to be a field
    the prompt stops asking for, and every field the gate demands has to be one the prompt asks for and the
    schema requires -- or a model that answers the prompt exactly is refused for the difference. It used to
    say a merged criterion "has the same fields as the members", which is how a child arrived without the
    direction and the value sources its members all declared; then it listed the child's own fields flat,
    which is how three reductions arrived with the name written outside the attribute."""
    system = derivation_stages.ADJUDICATOR_SYSTEM
    assert "same fields as the members" not in system
    for field in (derivation_stages._FIXED_BY_GROUPING + derivation_stages._AGREED_BY_MEMBERS
                  + derivation_stages._AGREED_IN_A_MERGE):
        assert field in system, field
    for where in ("attribute", "rule", "decision", "consolidation"):
        for field in derivation_stages._required_of(where):
            assert f"`{field}`" in system, (where, field)
    assert "The name is required" in system
    assert "Write none of those six" in system
    # the two rules the gate enforces that the prompt used to leave it to find out: one literature route per
    # attribute, and the support record that comes with a cutoff kept unchanged
    assert "exactly one `literature_retrieval` route" in system
    assert "keeps that member's support record with it" in system
    assert "needs its own support record" in system


def test_a_merge_whose_members_pool_their_values_differently_is_not_refused_for_it(core):
    """The one inherited field whose absence no validator refuses, so completing it must not start refusing.
    `check_attribute` reads a missing `aggregation` as `consensus`; where a merge's members agree on a
    reduction the child gets it, and where they do not the question is the child's and the merge stands. The
    live merge's two members both declare `max`, and two of the three live groups split `max` with `median`,
    so both halves of this are cases the pool actually holds."""
    disagreeing = [BIOAVAILABILITY_GROUP[0],
                   dict(BIOAVAILABILITY_GROUP[1],
                        attribute=dict(BIOAVAILABILITY_GROUP[1]["attribute"], aggregation="median"))]
    ctx = live_pool(core, live_script(live_decision(LIVE_BIOAVAILABILITY_CHILD, action="merge")), disagreeing,
                    task_id="task_live_two_reductions")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["merged"] == 1 and stats["refused"] == 0, stats["not_reduced"]
    attribute = next(e for e in pool.fold(core, "task_live_two_reductions").values()
                     if e["parents"])["item"]["attribute"]
    assert attribute.get("aggregation") is None, "a disagreement is the child's to settle, not the gate's"
    criteria.check_attribute(attribute)


# --- the second live merge, and the table that says who answers what -------------------------
# The three reductions the gate refused on 14 October 2026, reproduced from the recorded reply (trace
# `art_e8c55505cab5`) replayed against the pool at that merge stage's own `input_pool_hash`: of 6 groups over
# 115 lineages the adjudicator kept 3 separate on specific pharmacological grounds and proposed 1 merge and
# 2 consolidations, and the gate refused all three -- every one on `name`, and two of them also on the
# support record for a cutoff they had kept from a parent unchanged. The lineages' real cutoffs, support
# records and claim quotes are reproduced too, because what makes the support-record refusal the gate's
# doing rather than the model's is that the number, the claim, the arithmetic and the interpretation behind
# that cutoff were already correct and already recorded, against the very bound the child kept.
LIVE_QUOTES = (
    ("claim_bioavailability_58", "The oral bioavailability is reasonable at 58%.", {"value": 58, "unit": "%"}),
    ("claim_bioavailability_1", "The principal reason is poor oral bioavailability of less than 1%",
     {"value_high": 1, "unit": "%"}),
    ("claim_half_life_120", "Cabozantinib has a half-life of 55 h and an extended terminal plasma half-life of "
                            "99-120 h and demonstrates an approximate five-fold accumulation by the 15th day of "
                            "daily administration", {"value_low": 99, "value_high": 120, "unit": "h"}),
    ("claim_half_life_51", "Single 160 mg dose geometric mean elimination half-lives of regorafenib are: 28 h "
                           "(14-58), M-2 25 h (14-32) and M5 51 h (32-70)", {"value_low": 14, "value_high": 58,
                                                                             "unit": "h"}),
    ("claim_food_20", "Following food intake, nintedanib exposure increases by roughly 20% compared to fasting "
                      "conditions, with delayed absorption.", {"value": 20, "unit": "%"}),
    ("claim_food_32", "food modestly decreases its exposure (high-fat meal AUC 22%, light-fat AUC 32%)", {}),
    ("claim_acid_46", "Omeprazole AUC 46%/Cmax 61%; ranitidine AUC 15-33%", {}),
)
LIVE_CLAIMS = {claim_id: {"claim_id": claim_id, "source_ref": f"src_{claim_id}", "evidence_kind": "peer_reviewed",
                          "determination_basis": "measured", "location": {"quoted_span": quote}, **recorded}
               for claim_id, quote, recorded in LIVE_QUOTES}


def live_support(claim_id, number, unit, *, inference, measurement, rationale):
    """One §5.4 record as the live lineages carry them: the number the passage states, the claim it was read
    from, what that passage is doing with it, why that applies here, and the step to a screening bound."""
    return {"parameter_path": "rule.cutoff.value", "claim_id": claim_id, "source_number": number,
            "source_unit": unit, "conversion": {"kind": "identity"}, "statement_kind": "reports_measurement",
            "applicability_rationale": rationale,
            "interpretation": {"measurement": measurement, "inference": inference,
                               "population_rationale": rationale}}


def live_member(name, unit, direction, dimension, *, query, aggregation, claims, cutoff=None, comparator="<=",
                support=None):
    """One lineage of a live merge group: a literature-bound criterion with its own query and, where it has a
    cutoff, the support record that cutoff was admitted on."""
    attribute = dict(lit_attribute(name, unit, direction=direction), aggregation=aggregation,
                     acceptable_determination_bases=["measured"],
                     evidence_request={"capability": "literature_retrieval", "question_kind": "search",
                                       "parameters": {"query_template": query, "search_limit": 10}})
    if cutoff is None:
        rule = {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
                "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty"}
    else:
        rule = {"rule_kind": "preference", "predicate_form": "threshold", "cutoff_basis": "source_stated_value",
                "cutoff": {"comparator": comparator, "value": cutoff, "unit": unit},
                "on_missing": "unknown_no_penalty", "bound_support": [support]}
    return {"attribute": attribute, "rule": rule, "supporting_claim_ids": list(claims), "dimension": dimension,
            "expected_change": f"candidates with a better {name.lower()} rank higher",
            "falsification_test": f"the ranking is unchanged when {name.lower()} is"}


BIOAVAILABILITY_GROUP = [
    live_member("Reported human oral bioavailability against a same-class benchmark", "%", "higher_better",
                "oral_bioavailability", query='({names}) AND "oral bioavailability"', aggregation="max",
                claims=["claim_bioavailability_58"], cutoff=58, comparator=">=",
                support=live_support("claim_bioavailability_58", 58, "%", inference="at_least_the_reported_value",
                                     measurement="the passage reports a measured oral bioavailability of 58% and "
                                                 "calls it reasonable for an orally dosed kinase inhibitor",
                                     rationale="candidates are orally administered kinase inhibitors, the "
                                               "population in which 58% was measured and judged reasonable for "
                                               "oral use")),
    live_member("Oral bioavailability relative to the band described as poor and development-limiting", "%",
                "higher_better", "oral_bioavailability", query='({names}) AND "oral absorption"',
                aggregation="max", claims=["claim_bioavailability_1"], cutoff=1, comparator=">",
                support=live_support("claim_bioavailability_1", 1, "%",
                                     inference="outside_the_reported_range_is_out_of_population",
                                     measurement="the passage reports that bioavailability below 1% was the "
                                                 "reason oral development failed",
                                     rationale="the sub-1% band is the source's own description of the "
                                               "population that cannot be developed as an oral agent")),
]
HALF_LIFE_GROUP = [
    live_member("Terminal half-life upper bound as an accumulation-risk flag", "h", "lower_better",
                "metabolic_stability", query='({names}) AND "terminal half-life"', aggregation="max",
                claims=["claim_half_life_120"], cutoff=120,
                support=live_support("claim_half_life_120", 120, "h", inference="at_most_the_reported_value",
                                     measurement="the passage reports an extended terminal plasma half-life "
                                                 "range of 99-120 h with five-fold accumulation by the "
                                                 "fifteenth day of daily dosing",
                                     rationale="candidates are oral agents intended for repeated daily dosing, "
                                               "the regimen that range was observed under, so a half-life "
                                               "beyond its upper edge accumulates further")),
    live_member("Active metabolite terminal half-life", "h", "lower_better", "metabolic_stability",
                query='({names}) AND "active metabolite"', aggregation="median", claims=["claim_half_life_51"],
                cutoff=51,
                support=live_support("claim_half_life_51", 51, "h", inference="at_most_the_reported_value",
                                     measurement="the passage reports a geometric-mean terminal half-life of "
                                                 "51 h for the long-lived active metabolite",
                                     rationale="candidates are dosed continuously in the same oncology "
                                               "population, where a longer-lived metabolite is the less "
                                               "favourable direction")),
]
CO_ADMINISTRATION_GROUP = [
    live_member("Meal-induced AUC increase", "%", "lower_better", "oral_bioavailability",
                query='({names}) AND "food effect"', aggregation="median", claims=["claim_food_20"]),
    live_member("Meal-induced AUC reduction", "%", "lower_better", "oral_bioavailability",
                query='({names}) AND "food intake"', aggregation="max", claims=["claim_food_32"]),
    live_member("Acid-reducing agent-induced AUC reduction", "%", "lower_better", "oral_bioavailability",
                query='({names}) AND "acid-reducing"', aggregation="max", claims=["claim_acid_46"]),
]
# The two live children that kept a parent's cutoff: the record as sent, with the claim, the number, the
# arithmetic and the interpretation all correct and `applicability_rationale` left out -- which is what the
# gate refused both whole reductions for, while the parent holding that identical bound states it.
LIVE_BIOAVAILABILITY_CHILD = {
    "name": "Oral bioavailability against a same-class benchmark",
    "definition": "Reported human oral bioavailability of the candidate, ranked against the 58% a cited source "
                  "reports for an orally dosed kinase inhibitor and characterises as reasonable",
    "rule": {"rule_kind": "preference", "predicate_form": "threshold", "cutoff_basis": "source_stated_value",
             "cutoff": {"comparator": ">=", "value": 58, "unit": "%"}, "on_missing": "unknown_no_penalty",
             "bound_support": [{"parameter_path": "rule.cutoff.value", "claim_id": "claim_bioavailability_58",
                                "source_number": 58, "source_unit": "%", "conversion": {"kind": "identity"},
                                "statement_kind": "reports_measurement",
                                "interpretation": {"inference": "at_least_the_reported_value",
                                                   "measurement": "the passage reports a measured oral "
                                                                  "bioavailability of 58%",
                                                   "population_rationale": "candidates are orally dosed kinase "
                                                                           "inhibitors, as the passage's subject "
                                                                           "was"}}]},
    "supporting_claim_ids": ["claim_bioavailability_58"],
    "expected_change": "candidates reported at or above 58% rank above candidates reported lower",
    "falsification_test": "candidates below the benchmark reach comparable clinical exposure",
}
LIVE_HALF_LIFE_CHILD = {
    "name": "Worst-case terminal half-life (parent or active metabolite)",
    "definition": "Terminal elimination half-life of the parent drug or of its active metabolite, whichever is "
                  "longer, against the 120 h upper edge of the range reported for an approved oral inhibitor",
    "members": [0, 1],
    "shared_property": "terminal half-life of the parent drug or its active metabolite, which governs "
                       "accumulation and delayed offset during chronic oral dosing",
    "family_aggregation": "worst_member",
    "rule": {"rule_kind": "preference", "predicate_form": "threshold", "cutoff_basis": "source_stated_value",
             "cutoff": {"comparator": "<=", "value": 120, "unit": "h"}, "on_missing": "unknown_no_penalty",
             "bound_support": [{"parameter_path": "rule.cutoff.value", "claim_id": "claim_half_life_120",
                                "source_number": 120, "source_unit": "h", "conversion": {"kind": "identity"},
                                "statement_kind": "reports_measurement",
                                "interpretation": {"inference": "at_most_the_reported_value",
                                                   "measurement": "the passage reports a terminal plasma "
                                                                  "half-life range of 99-120 h",
                                                   "population_rationale": "candidates are oral agents dosed "
                                                                           "daily, as the passage's subject was"}}]},
    "supporting_claim_ids": ["claim_half_life_120"],
    "expected_change": "candidates whose worst-case terminal half-life exceeds 120 h rank lower",
    "falsification_test": "a candidate above the bound shows no accumulation-related toxicity",
}
LIVE_CO_ADMINISTRATION_CHILD = {
    "name": "Worst-case co-administration-induced AUC change",
    "definition": "The largest percentage change in human oral AUC when the agent is given with food or with an "
                  "acid-reducing agent, relative to the reference condition",
    "members": [0, 1, 2],
    "shared_property": "magnitude of oral exposure change when the agent is co-administered with food or an "
                       "acid-reducing agent, which decides dosing consistency and administration restrictions",
    "family_aggregation": "worst_member",
    "rule": {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
             "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty"},
    "supporting_claim_ids": ["claim_food_20", "claim_food_32", "claim_acid_46"],
    "expected_change": "candidates with a smaller worst-case AUC change rank higher",
    "falsification_test": "candidates with larger changes keep consistent exposure without restrictions",
}


def live_pool(core, script, members, *, task_id, run_id=None):
    """A pool holding those lineages, and the context to run the merge stage over them."""
    writer = pool.Pool(core, task_id, by=OPERATOR, run_id=run_id or f"run_{task_id}").at("propose", 0)
    for member in members:
        writer.add(dict(member), reason_text=f"proposed for {member['dimension']}")
    return derivation_stages.StageContext(
        core=core, roster=roster_for(script), task_id=task_id, run_id=run_id or f"run_{task_id}",
        task_context={"objective_text": SPEC["objective_text"], "constraints": [],
                      "scope_entities": SPEC["scope_entities"]},
        catalog=EVIDENCE_CATALOG, claims_by_id=dict(LIVE_CLAIMS), reference_labels=[], pool=writer)


def live_decision(child, *, action, routes="one", nested=True, **override):
    """One decision in the shape the schema now requires, or in the shape the adjudicator really sent it.

    `nested=False` is half of the recorded shape -- `name` and `definition` beside `attribute` rather than
    inside it, where `derivation._normalize_proposal` drops them -- and `routes="all"` is the other half,
    every member's `literature_retrieval` query collected into one attribute.
    """
    def decide(group):
        declared = dict(child, **override)
        queries = [r for m in group["members"] for r in criteria.evidence_routes(m["attribute"])]
        attribute = {"evidence_requests": queries if routes == "all" else queries[:1]}
        if nested:
            attribute["name"], attribute["definition"] = declared.pop("name"), declared.pop("definition")
        return {"group": group["group"], "action": action,
                "merged" if action == "merge" else "consolidated": dict(declared, attribute=attribute),
                "reason": "the reason the live reply gave for this group"}
    return decide


def live_script(*decisions):
    """An adjudicator replying with one prepared decision per group, in group order."""
    def script(request):
        assert request.metadata.get("question") == "adjudicate merges", request.metadata
        groups = json.loads(request.messages[0]["content"].split("Groups:\n", 1)[1].split("\n\nCited claims:")[0])
        return {"decisions": [decisions[group["group"]](group) for group in groups]}
    return script


def test_the_schema_requires_the_name_inside_the_attribute_where_the_gate_reads_it_and_not_beside_it():
    """Why all three live reductions were refused for a `name` the model had written. The prompt listed the
    child's fields flat -- a name, a definition, the rule, the claims -- and all but three of those really are
    flat, so the model put `name` and `definition` beside `attribute` and gave `attribute` only the
    `evidence_requests` that `MERGE_SCHEMA` named. `_normalize_proposal` keeps `ATTRIBUTE_FIELDS` of the
    attribute object and nothing from outside it, so the name was dropped and `check_attribute` refused the
    child for not having one. A gate requirement the schema does not require is a requirement the model will
    keep missing, so the schema now requires it where the gate reads it and the repair round says so."""
    group = {"group": 0, "members": [derivation_stages._view({"item": m}, i)
                                     for i, m in enumerate(BIOAVAILABILITY_GROUP)]}
    as_sent = {"decisions": [live_decision(LIVE_BIOAVAILABILITY_CHILD, action="merge", nested=False)(group)]}
    assert models.validate(as_sent, derivation_stages.MERGE_SCHEMA) == \
           ["$.decisions[0].merged.attribute: missing name", "$.decisions[0].merged.attribute: missing definition"]
    nested = {"decisions": [live_decision(LIVE_BIOAVAILABILITY_CHILD, action="merge")(group)]}
    assert models.validate(nested, derivation_stages.MERGE_SCHEMA) == []
    # and every field the schema requires is a field the table says the adjudicator answers, not one the
    # group settles: a schema that asked for an inherited field would be the first defect in the mirror
    required = set(derivation_stages._required_of("attribute") + derivation_stages._required_of("rule")
                   + derivation_stages._required_of("decision")
                   + derivation_stages._required_of("consolidation"))
    inherited = set(derivation_stages._FIXED_BY_GROUPING + derivation_stages._AGREED_BY_MEMBERS
                    + derivation_stages._AGREED_IN_A_MERGE)
    assert required & inherited == set()
    assert {"name", "definition", "evidence_requests"} <= required


def test_a_reduction_keeping_a_parents_cutoff_keeps_that_parents_support_record_for_that_number(core):
    """The second blocker, on the live merge and the live consolidation that hit it. Both children kept a
    parent's cutoff exactly -- 58% oral bioavailability, 120 h terminal half-life -- restated its support
    record almost in full and left out `applicability_rationale`, and `bound_support.validate` refuses a
    declared record missing any of §5.4's four fields. The record belongs to the bound and the bound is the
    parent's, so it is inherited as the unit and the direction are, and only the fields the child left empty
    are filled: what the child does say about that number stands as its own."""
    for child, action, members, task_id in ((LIVE_BIOAVAILABILITY_CHILD, "merge", BIOAVAILABILITY_GROUP,
                                            "task_live_bioavailability"),
                                           (LIVE_HALF_LIFE_CHILD, "consolidate", HALF_LIFE_GROUP,
                                            "task_live_half_life")):
        ctx = live_pool(core, live_script(live_decision(child, action=action)), members, task_id=task_id)
        stats = derivation_stages.merge_stage(ctx, 1)
        assert stats["groups"] == 1 and stats["refused"] == 0, stats["not_reduced"]
        entry = next(e for e in pool.fold(core, task_id).values() if e["parents"])
        (record,) = entry["item"]["rule"]["bound_support"]
        parent = next(m for m in members if m["rule"]["cutoff"] == entry["item"]["rule"]["cutoff"])
        assert record["applicability_rationale"] == parent["rule"]["bound_support"][0]["applicability_rationale"]
        # what the child did write about that number is not overwritten by the parent's wording
        assert record["interpretation"]["measurement"] == \
               child["rule"]["bound_support"][0]["interpretation"]["measurement"]
        # and the completed record is support the registry accepts for the number the criterion carries
        assert bound_support.messages(bound_support.validate(
            entry["item"]["attribute"], entry["item"]["rule"],
            claims=[LIVE_CLAIMS[c] for c in entry["item"]["supporting_claim_ids"]])) == []
        assert ctx.validate(entry["item"]) == []


def test_a_reduction_stating_a_cutoff_no_member_holds_still_needs_its_own_support_record(core):
    """The guard on the inheritance, and the reason it is the bound and not the parameter path. A support
    record justifies one number: carried onto another one it would manufacture support, which is the defect
    (R4) `bound_support` exists to stop -- a cutoff of 90 citing a claim that states 30. So a child that
    states a number no member holds inherits nothing, and an incomplete record for it is refused. The live
    merge's own members disagree outright, `>= 58 %` against `> 1 %`, which needs no special handling: the
    child kept one of the two, so one parent holds that bound and the other simply does not."""
    ctx = live_pool(core, live_script(live_decision(
        LIVE_BIOAVAILABILITY_CHILD, action="merge",
        rule=dict(LIVE_BIOAVAILABILITY_CHILD["rule"], cutoff={"comparator": ">=", "value": 40, "unit": "%"}))),
        BIOAVAILABILITY_GROUP, task_id="task_live_own_number")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["refused"] == 1 and stats["merged"] == 0
    (refusal,) = [d for d in stats["not_reduced"] if d["outcome"] == "refused"]
    assert "declares no applicability_rationale" in refusal["reason"]
    assert "rule.cutoff.value reads 40 %" in refusal["reason"], "the refusal names the number nothing states"
    # the number is the only thing that changed: the same child keeping the parent's 58 is applied
    ctx = live_pool(core, live_script(live_decision(LIVE_BIOAVAILABILITY_CHILD, action="merge")),
                    BIOAVAILABILITY_GROUP, task_id="task_live_kept_number")
    assert derivation_stages.merge_stage(ctx, 1)["merged"] == 1


def test_two_members_justifying_one_kept_bound_differently_refuse_the_reduction_rather_than_the_gate_choosing(core):
    """What the gate does when the inheritance is ambiguous. A record states what a passage reports and why
    that reading applies here, so two members holding the identical bound on two different passages offer two
    readings of one number, and picking one of them would be the gate deciding which evidence the surviving
    criterion rests on. The reduction is refused and the reason names both members, so the adjudicator's next
    reply can state the record it means."""
    members = [dict(BIOAVAILABILITY_GROUP[0]),
               live_member("Oral bioavailability against the same benchmark read from a second report", "%",
                           "higher_better", "oral_bioavailability", query='({names}) AND "oral absorption"',
                           aggregation="max", claims=["claim_bioavailability_1"], cutoff=58, comparator=">=",
                           support=live_support("claim_bioavailability_1", 58, "%",
                                                inference="at_least_the_reported_value",
                                                measurement="a second report gives the same 58% for the class",
                                                rationale="the second report studied the same orally dosed "
                                                          "population, so its benchmark applies as well"))]
    ctx = live_pool(core, live_script(live_decision(LIVE_BIOAVAILABILITY_CHILD, action="merge")), members,
                    task_id="task_live_two_readings")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["refused"] == 1 and stats["merged"] == 0
    (refusal,) = [d for d in stats["not_reduced"] if d["outcome"] == "refused"]
    assert "justify that number differently" in refusal["reason"]
    assert refusal["reason"].count("@v1") == 2, "the refusal names both members, or nobody can act on it"
    assert not [e for e in pool.fold(core, "task_live_two_readings").values() if e["parents"]]


def test_the_three_reductions_the_second_live_merge_proposed_are_applied_once_the_gate_stops_asking_for_what_it_knows(core):
    """The whole second live merge, end to end: the 6 groups, the 3 the adjudicator kept separate and the 3 it
    reduced. Every refusal was the gate's -- `name`, which the model wrote outside the attribute, and the
    support record for a cutoff two of the children kept unchanged -- so with the schema requiring the name
    where the gate reads it and the record inherited with its bound, all three are applied: one merge of one
    quantity benchmarked twice, and two consolidations compiled to the reduction their declared family
    implies (`worst_member` as `max`, since the groups are `lower_better`)."""
    members = BIOAVAILABILITY_GROUP + HALF_LIFE_GROUP + CO_ADMINISTRATION_GROUP
    by_members = {frozenset(m["attribute"]["name"] for m in group): live_decision(child, action=action)
                  for group, child, action in ((BIOAVAILABILITY_GROUP, LIVE_BIOAVAILABILITY_CHILD, "merge"),
                                              (HALF_LIFE_GROUP, LIVE_HALF_LIFE_CHILD, "consolidate"),
                                              (CO_ADMINISTRATION_GROUP, LIVE_CO_ADMINISTRATION_CHILD, "consolidate"))}

    def script(request):
        groups = json.loads(request.messages[0]["content"].split("Groups:\n", 1)[1].split("\n\nCited claims:")[0])
        return {"decisions": [by_members[frozenset(m["attribute"]["name"] for m in group["members"])](group)
                              for group in groups]}

    ctx = live_pool(core, script, members, task_id="task_live_merge")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert (stats["groups"], stats["merged"], stats["consolidated"], stats["refused"]) == (3, 1, 2, 0), \
        stats["not_reduced"]
    children = {e["item"]["attribute"]["name"]: e for e in pool.fold(core, "task_live_merge").values()
                if e["parents"]}
    assert sorted(children) == ["Oral bioavailability against a same-class benchmark",
                                "Worst-case co-administration-induced AUC change",
                                "Worst-case terminal half-life (parent or active metabolite)"]
    for name, entry in children.items():
        criteria.check_attribute(entry["item"]["attribute"])
        criteria.check_rule(entry["item"]["rule"], entry["item"]["attribute"])
        assert ctx.validate(entry["item"]) == []
    for name in ("Worst-case co-administration-induced AUC change",
                 "Worst-case terminal half-life (parent or active metabolite)"):
        consolidation = children[name]["item"]["consolidation"]
        assert consolidation["executes_as_aggregation"] == "max"
        assert children[name]["item"]["attribute"]["aggregation"] == "max"
    # the merge pools its parents' values the way both of them did, rather than under the `consensus` a
    # silent child would have been given by `check_attribute`'s default
    assert children["Oral bioavailability against a same-class benchmark"]["item"]["attribute"]["aggregation"] \
        == "max"
    # 7 lineages in, 3 out and 7 retired: the reduction this pool exists to perform
    folded = pool.fold(core, "task_live_merge")
    assert len([e for e in folded.values() if e["state"] == "merged_away"]) == 7
    assert len(pool.active(folded, ("candidate",))) == 3


def test_a_literature_bound_reduction_collecting_its_members_queries_is_refused_and_that_one_is_the_adjudicators(core):
    """The refusal hiding behind the other two, which only showed once `name` was in place: all three live
    children declared every member's `literature_retrieval` route on one attribute, and `check_attribute`
    allows one, because `evidence.literature_query` builds one query per attribute and a second would never
    be asked. That is not a field the group settled -- which query stands for the family is a judgement, and
    keeping one member's silently would give a toxicity-burden criterion a diarrhea query -- so the gate is
    right to refuse it and the prompt now states the rule rather than inviting the collection."""
    ctx = live_pool(core, live_script(live_decision(LIVE_BIOAVAILABILITY_CHILD, action="merge", routes="all")),
                    BIOAVAILABILITY_GROUP, task_id="task_live_two_queries")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["refused"] == 1 and stats["merged"] == 0
    (refusal,) = [d for d in stats["not_reduced"] if d["outcome"] == "refused"]
    assert "declares 2 literature routes" in refusal["reason"]
    assert "exactly one `literature_retrieval` route" in derivation_stages.ADJUDICATOR_SYSTEM


def test_a_support_record_is_inherited_for_a_transform_bound_too_and_filed_where_the_parameter_lives():
    """Every number a candidate is compared against is one supported parameter, and a `value_transform`'s
    bounds are the other kind -- `quantity_key` keys on the transform, so a group's members carry the same
    one, and the record for its bound is the group's exactly as a kept cutoff's is. `support_records` reads
    the rule's list and the attribute's, so the completed record is filed on the object that holds the
    parameter (§5.3): filed on the other one it would travel with the wrong version through promotion."""
    transform = {"kind": "excess_above", "bound": 500, "basis": "source_stated_value",
                 "source_refs": ["claim_mass_500"]}
    record = {"parameter_path": "attribute.value_transform.bound", "claim_id": "claim_mass_500",
              "source_number": 500, "source_unit": "g/mol", "conversion": {"kind": "identity"},
              "statement_kind": "reports_measurement",
              "applicability_rationale": "the passage's 380-500 Da band is the range reported for clinically "
                                         "relevant kinase inhibitors, which is the population screened here"}
    parent_attribute = dict(lit_attribute("Molecular weight above the reported band", "g/mol",
                                          direction="lower_better"), value_transform=transform,
                            bound_support=[record])
    parents = [{"criterion_id": "cri_1", "version": 3,
                "item": {"attribute": parent_attribute,
                         "rule": {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
                                  "cutoff_basis": "none_evidence_insufficient"}}}]
    # the child keeps the transform the group is keyed on and says nothing about the bound behind it
    child = {"attribute": dict(lit_attribute("Excess molecular weight over the reported band", "g/mol",
                                             direction="lower_better"), value_transform=transform),
             "rule": {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
                      "cutoff_basis": "none_evidence_insufficient"}}
    completed, problem = derivation_stages._supported_as_its_parents(parents, child)
    assert problem is None
    assert completed["attribute"]["bound_support"] == [record], "filed on the attribute, which holds the bound"
    assert not completed["rule"].get("bound_support")
    # and a child whose transform draws its line somewhere else inherits nothing: the record justifies 500
    elsewhere = {"attribute": dict(completed["attribute"], bound_support=None,
                                   value_transform=dict(transform, bound=300)),
                 "rule": dict(child["rule"])}
    untouched, problem = derivation_stages._supported_as_its_parents(parents, elsewhere)
    assert problem is None and not untouched["attribute"].get("bound_support")


def test_a_reduction_stating_only_what_the_classification_table_leaves_to_it_is_applied(core):
    """The guard on the whole class of defect. `REDUCTION_FIELDS` says, for every requirement the four
    validators make of a reduction's child, who answers it; this builds a child out of exactly the fields the
    table leaves to the adjudicator -- nothing classified as the group's, the members', the bound's or the
    gate's -- and asserts the gate applies it. A requirement added to `check_attribute`, `check_rule`,
    `bound_support.validate` or this gate without a row in the table fails here instead of becoming the
    fourth live reduction refused for a field nobody was asked for."""
    decided = {where: derivation_stages._required_of(where)
               for where in ("attribute", "rule", "decision", "consolidation")}
    assert decided["decision"] and decided["attribute"] and decided["consolidation"]

    def only_what_is_decided(group):
        child = {"attribute": {"name": "Grade >=3 treatment-related toxicity burden",
                               "definition": "Share of treated patients with any grade >=3 treatment-related "
                                             "adverse event",
                               "evidence_requests": criteria.evidence_routes(group["members"][0]["attribute"])},
                 "rule": {"rule_kind": "preference", "cutoff_basis": "none_evidence_insufficient"},
                 "supporting_claim_ids": sorted({c for m in group["members"] for c in m["supporting_claim_ids"]}),
                 "expected_change": "a candidate with a worse grade >=3 burden ranks lower",
                 "falsification_test": "the ranking does not move when the burden does",
                 "members": [m["index"] for m in group["members"]], "shared_property": SHARED_PROPERTY,
                 "family_aggregation": "worst_member"}
        assert sorted(child) == sorted(set(decided["decision"]) | set(decided["consolidation"])), \
            "this child states the table's `decided` fields and nothing else"
        assert sorted(child["attribute"]) == sorted(decided["attribute"])
        assert sorted(child["rule"]) == sorted(decided["rule"])
        return {"group": group["group"], "action": "consolidate", "consolidated": child,
                "reason": "three endpoints a screen applies as one grade >=3 toxicity burden"}

    ctx = family_pool(core, live_script(only_what_is_decided), task_id="task_table", run_id="run_table")
    stats = derivation_stages.merge_stage(ctx, 1)
    assert stats["consolidated"] == 1 and stats["refused"] == 0, stats["not_reduced"]
    attribute = next(e for e in pool.fold(core, "task_table").values() if e["parents"])["item"]["attribute"]
    # and each field the table calls the group's or the members' reaches the child from them: what the
    # members declare is what the child carries, and what none of them declares is nothing to inherit
    members = [e["item"]["attribute"] for e in pool.active(pool.fold(core, "task_table"), ("merged_away",))]
    for field in derivation_stages._FIXED_BY_GROUPING + derivation_stages._AGREED_BY_MEMBERS:
        assert attribute.get(field) == members[0].get(field), field
    assert attribute["direction"] == "lower_better" and attribute["unit"] == "%"
    assert attribute["acceptable_value_sources"] == ["peer_reviewed"]


# --- a reduction that survives being revised --------------------------------------------------
# `item["consolidation"]` is the only protection against an abstraction destroying information: the pool is
# reported with every criteria count beside its consolidations and the endpoints each one subsumed. But
# `_item` keeps the five fields a model authors plus whatever a stage passes back, and `distill_stage` and
# `refine_stage` passed back only `dimension` and `refine_count` -- so a revised consolidated criterion kept
# the `aggregation` its consolidation had chosen and lost the list of endpoints that justified it, which is
# exactly where the published count rests. `refine_count` was dropped the same way earlier the same day, so
# the first test below asks after every field `pool.ITEM_FIELDS` persists rather than after this one.


class FamilyScript:
    """One scripted model for a family pool: queued adjudications, and one revision for every item the
    distiller or the reviser is shown.

    `adjudications` are callables taking the group view and returning a decision, one per
    `merge_stage` call; `revision` is applied to the attribute of every item offered for revision.
    """

    def __init__(self, *adjudications, revision=None, reason="sharpened for screening use"):
        self.adjudications, self.revision, self.reason = list(adjudications), revision or {}, reason
        self.asked: list[str] = []

    def __call__(self, request):
        question = request.metadata.get("question", "")
        content = request.messages[0]["content"]
        self.asked.append(question)
        if question == "adjudicate merges":
            groups = json.loads(content.split("Groups:\n", 1)[1].split("\n\nCited claims:")[0])
            decide = self.adjudications.pop(0)
            return {"decisions": [decide(group) for group in groups]}
        if question == "distill pool":
            items = json.loads(content.split("Items to distill:\n", 1)[1].split("\n\nCited claims:")[0])
            return {"items": [self._revise(item) for item in items]}
        assert question == "refine pool", question
        items = json.loads(content.split("Proposals to revise or withdraw:\n", 1)[1].split("\n\nCited claims:")[0])
        return {"revisions": [self._revise(item) for item in items]}

    def _revise(self, item):
        revised = dict(proposal(dict(item["attribute"], **self.revision), "unused"),
                       supporting_claim_ids=item["supporting_claim_ids"])
        return {"index": item["index"], "action": "revise", "reason": self.reason, "proposal": revised}


def consolidates_the_family(group):
    """The adjudication the family pool is built for: every member folded into one burden criterion."""
    return {"group": group["group"], "action": "consolidate",
            "consolidated": dict(proposal(child_attribute(burden_attribute()), "unused"),
                                 supporting_claim_ids=sorted({c for m in group["members"]
                                                              for c in m["supporting_claim_ids"]}),
                                 members=[m["index"] for m in group["members"]],
                                 shared_property=SHARED_PROPERTY, family_aggregation="worst_member"),
            "reason": "three specific endpoints a screen applies as one toxicity burden"}


def merges_onto(name: str):
    """An adjudication that merges the group into the member named `name`, keeping its attribute as it
    stands -- the merge gate's own claim, that the members were one quantity described more than once."""
    def decide(group):
        member = next(m for m in group["members"] if m["attribute"]["name"] == name)
        return {"group": group["group"], "action": "merge",
                "merged": dict(proposal(child_attribute(member["attribute"]), "unused"),
                               supporting_claim_ids=sorted({c for m in group["members"]
                                                            for c in m["supporting_claim_ids"]})),
                "reason": "one toxicity burden, described twice"}
    return decide


def consolidated_child(core, task_id="task_family"):
    """The live criterion carrying a consolidation record, and the whole fold around it. A reduction
    leaves its parents in the pool, so a merged-away consolidation is not the one under test."""
    folded = pool.fold(core, task_id)
    (entry,) = [e for e in folded.values()
                if e["item"].get("consolidation") and e["state"] != "merged_away"]
    return entry, folded


def test_a_revised_consolidation_still_names_the_endpoints_it_subsumed_and_keeps_what_the_pool_persists(core):
    """A distiller may sharpen a consolidated criterion's wording, its rationale and its literature query
    -- a retrieval knob, which is what the route check already allows a consolidation to rewrite for the
    family it stands for. What it may not do is cost the criterion the record of what it replaced."""
    script = FamilyScript(consolidates_the_family,
                          revision={"rationale": "a screen stops a chronic oral drug on dose-limiting toxicity",
                                    "evidence_requests": [dict(burden_attribute()["evidence_request"],
                                                               parameters={"query_template": "({names}) AND "
                                                                                             "grade 3 toxicity burden"})]})
    ctx = family_pool(core, script)
    assert derivation_stages.merge_stage(ctx, 1)["consolidated"] == 1
    before, _ = consolidated_child(core)
    assert derivation_stages.distill_stage(ctx, 1) == {"revised": 1, "kept": 0, "withdrawn": 0, "to_refine": 0,
                                                       "refused": 0}

    entry, _ = consolidated_child(core)
    assert entry["version"] == 2 and entry["state"] == "candidate", "the revision applied"
    assert entry["item"]["attribute"]["rationale"].startswith("a screen stops")
    # the record of what this abstraction replaced is the same record, through the fold that persists it
    assert entry["item"]["consolidation"] == before["item"]["consolidation"]
    assert sorted(s["name"] for s in entry["item"]["consolidation"]["subsumes"]) == \
        sorted(n for n, _ in TOXICITY_FAMILY)
    # and the aggregation the consolidation chose still matches the family reduction it recorded
    assert entry["item"]["attribute"]["aggregation"] == \
        entry["item"]["consolidation"]["executes_as_aggregation"] == "max"
    # every other field the pool persists survives too; `critic_findings` is the one a revision clears,
    # because those findings were raised against the version this one supersedes
    assert entry["item"]["validator_problems"] == [] and entry["item"]["dimension"] == "toxicological_safety"
    assert [f for f in pool.ITEM_FIELDS if entry["item"].get(f) is None] == ["critic_findings"], (
        "a field the pool persists and a revision drops is this defect again; keeping it is the default")


def test_a_revision_that_changes_what_a_consolidated_criterion_measures_is_refused_and_the_earlier_version_stands(core):
    """The decision this gate makes. `subsumes` is a claim about the criterion as it stands, and the gate
    that admitted it checked the family against that criterion's unit, direction, dimension and family
    reduction. A distiller sees the abstraction's own fields and neither the family nor the record, so a
    redefinition leaves nobody in a position to say whether those endpoints still share the property.
    Carrying the list onto a criterion that now measures something else would publish an unchecked claim
    as a reviewed one, and dropping it would make the reduced pool unauditable where its count rests --
    so the revision is refused, the previous version stands, and the stage result says why."""
    script = FamilyScript(consolidates_the_family,
                          revision={"definition": "Share of treated patients with any grade >=3 diarrhea"})
    ctx = family_pool(core, script)
    derivation_stages.merge_stage(ctx, 1)
    before, _ = consolidated_child(core)

    stats = derivation_stages.distill_stage(ctx, 1)
    assert stats["refused"] == 1 and stats["revised"] == 0
    (refusal,) = stats["not_revised"]
    assert refusal["criterion_id"] == before["criterion_id"] and refusal["version"] == 1
    assert "consolidates 3 endpoint(s)" in refusal["reason"] and "definition" in refusal["reason"]
    assert "may be consolidated again" in refusal["reason"], "the refusal has to name the way forward"

    entry, folded = consolidated_child(core)
    assert entry["version"] == 1 and entry["item"] == before["item"], "nothing about the lineage changed"
    assert len(entry["history"]) == 1, "and no pool record was written for a revision that did not happen"
    assert sorted(e["state"] for e in folded.values()) == ["candidate", "merged_away", "merged_away",
                                                           "merged_away"]

    # the same gate on the refine path, where the revision is a repair rather than a sharpening: a unit
    # the family was never measured in is still a change of what the criterion measures
    writer = ctx.pool.at("filter", 1)
    writer.set_state(entry, "needs_refine", operation="revise", reason_kind="validator_findings",
                     reason_text="unit", item=dict(entry["item"], validator_problems=["a validator finding"]))
    script.revision = {"unit": "events per patient-year"}
    stats = derivation_stages.refine_stage(ctx, 1)
    assert stats["refused"] == 1 and stats["revised"] == 0 and stats["still_failing"] == 0
    assert "unit" in stats["not_revised"][0]["reason"]
    entry, _ = consolidated_child(core)
    assert entry["state"] == "needs_refine" and entry["item"]["attribute"]["unit"] == "%"
    assert entry["item"]["consolidation"]["subsumes"] and entry["item"]["validator_problems"]
    assert int(entry["item"].get("refine_count") or 0) == 0, (
        "a rewrite that was never applied is not one of the rewrites the repair budget bounds")

    # and the fields the gate compares are the ones that fix the quantity, including the transform that
    # makes a burden and a burden in excess of a bound two quantities rather than one worded twice (F5)
    transformed = burden_attribute(value_transform={"kind": "excess_above", "bound": 10.0,
                                                    "basis": "source_stated_value", "source_refs": ["claim_tox_0"]})
    assert derivation_stages._measures_differently(burden_attribute(), transformed) == ["value_transform"]
    assert derivation_stages._measures_differently(
        burden_attribute(), burden_attribute(rationale="another rationale", acceptable_value_sources=["preprint"],
                                             evidence_request=dict(burden_attribute()["evidence_request"],
                                                                   parameters={"query_template": "({names}) AND tox",
                                                                               "search_limit": 25}))) == []


def test_a_merge_that_absorbs_a_consolidated_criterion_carries_its_family_forward_or_is_refused(core):
    """The same hole on the other rebuilding path, and the reason it matters more there: a merge retires
    its parents to `merged_away`, so a child that dropped a consolidated parent's record would leave the
    family named nowhere a count is read from -- the audit line would disappear at the one point the pool
    got smaller. A merge claims its members were one quantity all along, which is precisely the claim
    that passes the family on; a child measuring something else is making a different claim."""
    second = lit_attribute("Severe treatment-related toxicity rate", "%", direction="lower_better")
    script = FamilyScript(consolidates_the_family, merges_onto(burden_attribute()["name"]),
                          merges_onto(second["name"]))
    ctx = family_pool(core, script)
    assert derivation_stages.merge_stage(ctx, 1)["consolidated"] == 1
    consolidated, _ = consolidated_child(core)

    # a second description of the same burden arrives in the pool and groups with the consolidated child
    ctx.pool.at("propose", 0).add(dict(proposal(second, "claim_tox_0"), dimension="toxicological_safety"),
                                 reason_text="proposed for toxicological_safety")
    stats = derivation_stages.merge_stage(ctx, 2)
    assert stats["groups"] == 1 and stats["merged"] == 1 and stats["refused"] == 0
    child, folded = consolidated_child(core)
    assert child["criterion_id"] != consolidated["criterion_id"] and len(child["parents"]) == 2
    carried = child["item"]["consolidation"]
    assert carried["subsumes"] == consolidated["item"]["consolidation"]["subsumes"]
    assert carried["shared_property"] == SHARED_PROPERTY
    assert carried["carried_from"] == f"{consolidated['criterion_id']}@v{consolidated['version']}", (
        "a reader has to be able to see that this record came from a parent rather than from an adjudication")
    assert folded[consolidated["criterion_id"]]["state"] == "merged_away"

    # and a merge whose child measures something else than the consolidated parent is refused outright
    third = lit_attribute("Any-grade treatment-related toxicity rate", "%", direction="lower_better")
    ctx.pool.at("propose", 0).add(dict(proposal(third, "claim_tox_1"), dimension="toxicological_safety"),
                                  reason_text="proposed for toxicological_safety")
    script.adjudications = [merges_onto(third["name"])]
    stats = derivation_stages.merge_stage(ctx, 3)
    assert stats["refused"] == 1 and stats["merged"] == 0
    assert "while measuring something else" in stats["not_reduced"][0]["reason"]
    assert "(aggregation, definition, name)" in stats["not_reduced"][0]["reason"], (
        "the refusal names which fields moved: this child is a different quantity reduced a different way")
    assert consolidated_child(core)[0]["criterion_id"] == child["criterion_id"], "the child still stands"

    # two consolidated members cannot be merged either: the child would have to state both families'
    # shared properties, and a family of families is a consolidation over them rather than a merge
    def consolidated_parent(criterion_id, version):
        return {"criterion_id": criterion_id, "version": version,
                "item": {"attribute": burden_attribute(), "consolidation": dict(carried)}}

    inherited, problem = derivation_stages._merged_consolidation(
        [consolidated_parent("cri_a", 2), consolidated_parent("cri_b", 1)], {"attribute": burden_attribute()})
    assert inherited is None and "2 members are consolidations" in problem


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
    # Match the proposal's default missing-value policy too: distinct decisions on one
    # measurement now survive for reconciliation rather than being discarded as duplicates.
    attr_ref, _ = criteria.propose(core, task_id, both,
                                  dict(ORDERING, on_missing="unknown_blocks_recommendation"), by=OPERATOR)
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


def test_a_database_subset_of_a_mixed_anchor_is_covered_but_a_new_decision_is_deferred(core):
    """A literature route must not hide an existing target measurement from the subset guard."""
    task_id = "task_mixed_anchor_subset"
    literature = {"capability": "literature_retrieval", "question_kind": "search",
                  "parameters": {"query_template": "({names}) AND CSF1R potency"}}
    anchor = pooled(CHEMBL_POTENCY["evidence_request"], GTOPDB_AFFINITY["evidence_request"], literature,
                    acceptable_value_sources=["curated_measurement", "peer_reviewed"])
    source_rule = dict(ORDERING, on_missing="unknown_blocks_recommendation")
    attr_ref, _ = criteria.propose(core, task_id, anchor, source_rule, by=OPERATOR)
    registered = criteria.registered_attributes(core, task_id)
    rules = criteria.registered_rule_records(core, task_id)
    assert derivation_stages.quantity_key(CHEMBL_POTENCY) != derivation_stages.quantity_key(registered[0])
    assert derivation_stages.duplicate_of_registered(CHEMBL_POTENCY, registered, rule=source_rule,
                                                     registered_rules=rules)["attribute_ref"] == attr_ref
    for different_policy in (dict(CHEMBL_POTENCY, acceptable_value_sources=["curated_measurement", "database_entry"]),
                             dict(CHEMBL_POTENCY, determination_basis_precedence=["measured", "derived"])):
        assert derivation_stages.duplicate_of_registered(different_policy, registered) is not None
        assert derivation_stages.duplicate_of_registered(different_policy, registered, rule=source_rule,
                                                         registered_rules=rules) is None
    # Different reductions/types/quantities are not erased by the transport-independent test.
    for changed in (dict(CHEMBL_POTENCY, aggregation="max"),
                    dict(CHEMBL_POTENCY, measurement_kind="categorical", unit=None),
                    dict(CHEMBL_POTENCY, direction="lower_better"),
                    dict(CHEMBL_POTENCY, value_transform={"kind": "excess_above", "bound": 7})):
        assert derivation_stages.duplicate_of_registered(changed, registered) is None
    added_route = dict(CHEMBL_POTENCY["evidence_request"], parameters={"target_chembl_id": "CHEMBL279"})
    assert derivation_stages.duplicate_of_registered(pooled(added_route), registered) is None

    ctx = pool_of(core, lambda request: {"findings": []}, [("claim_potency", CHEMBL_POTENCY)],
                  task_id=task_id, run_id="run_mixed_anchor_subset")
    entry = next(iter(pool.fold(core, task_id).values()))
    threshold = dict(source_rule, predicate_form="threshold", cutoff_basis="source_stated_value",
                     cutoff={"comparator": ">=", "value": 8, "unit": "pChEMBL"})
    ctx.pool.revise(entry, dict(entry["item"], rule=threshold), reason_text="a supported new decision")
    assert derivation_stages.filter_stage(ctx, 1)["filtered_out"] == 0
    result = derivation_stages.promote(ctx, by_proposer=OPERATOR)
    assert len(result["deferred"]) == 1 and not result["accepted"]
    assert "decision_semantics_unresolved" in result["deferred"][0]["problems"][0]
    assert len(criteria.registered_rule_records(core, task_id)) == 1
    (retained,) = pool.fold(core, task_id).values()
    assert retained["state"] == "deferred_next_round" and retained["item"]["rule"]["cutoff"]["value"] == 8


def test_catalog_units_follow_executable_conversions_and_boolean_outputs_cannot_count():
    from mas.core.derivation import validate_proposal

    def problems(attribute, catalog=EVIDENCE_CATALOG):
        return validate_proposal(proposal(attribute, "claim_support"), claims_by_id={
            "claim_support": {"claim_id": "claim_support", "value": 8, "unit": "pChEMBL",
                              "determination_basis": "measured"}}, reference_labels=[], catalog=catalog)

    assert problems(CHEMBL_POTENCY) == []
    assert problems(dict(CHEMBL_POTENCY, unit=" pChEMBL ")) == []
    for wrong_unit in ("nM", "ng/g"):
        assert any(p.startswith("units:") and "no registered conversion" in p
                   for p in problems(dict(CHEMBL_POTENCY, unit=wrong_unit)))
    entry = next(e for e in EVIDENCE_CATALOG if e["question_kind"] == "pchembl_values")
    # This direction is genuinely implemented by the assessor; the converse above is not.
    assert problems(CHEMBL_POTENCY, [dict(entry, units={"potency": "nM"})]) == []
    assert problems(dict(CHEMBL_POTENCY, unit="nmol/l"), [dict(entry, units={"potency": "nM"})]) == []
    assert any("categorical projection" in p for p in
               problems(dict(CHEMBL_POTENCY, measurement_kind="categorical", unit=None)))
    mechanism = dict(CHEMBL_POTENCY, name="Recorded target count", unit="count",
                     acceptable_value_sources=["database_entry"], acceptable_determination_bases=["curated"],
                     evidence_request=dict(CHEMBL_POTENCY["evidence_request"], question_kind="mechanism_records"))
    assert any("no executable numeric aggregation" in p for p in problems(mechanism))
    multi = pooled(mechanism["evidence_request"],
                   dict(mechanism["evidence_request"], parameters={"target_chembl_id": "CHEMBL279"}), base=mechanism)
    assert sum("no executable numeric aggregation" in p for p in problems(multi)) == 2
    # A Boolean field's output is selected before checking units; the numeric year field in the same
    # catalog entry cannot make an oral count executable.
    record = dict(mechanism, acceptable_determination_bases=["measured"], evidence_request={
        "capability": "record_field_lookup", "question_kind": "record_field", "parameters": {"field": "oral"}})
    assert any("no executable numeric aggregation" in p for p in problems(record))
    assert problems(dict(record, unit="year", evidence_request=dict(record["evidence_request"],
                                                                    parameters={"field": "first_approval"}))) == []


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


def test_a_derived_quantity_is_not_a_duplicate_of_the_measurement_it_is_derived_from():
    """F5. `quantity_key` is supposed to say what an attribute measures, but it omitted the declared
    `value_transform` -- and a transform changes exactly that. "Molecular weight" and "the excess of
    molecular weight above 500 g/mol" share a capability, a unit, a direction and a subject while
    being different quantities, one derived from the other. So a merge or a duplicate check could
    collapse a derived criterion into its own source measurement and report it as redundant."""
    from mas.core.derivation_stages import quantity_key, duplicate_of_registered

    def mw(name, transform=None, direction="lower_better"):
        a = {"attribute_id": "attr_" + name, "version": 1, "name": name, "definition": name,
             "measurement_kind": "quantitative", "unit": "g/mol", "direction": direction,
             "acceptable_value_sources": ["database_entry"], "aggregation": "median",
             "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                                  "identifier_scheme": "inchikey", "parameters": {"property": "MolecularWeight"}}}
        if transform:
            a["value_transform"] = transform
        return a

    raw = mw("Molecular weight")
    excess = mw("Molecular weight in excess of the stated bound",
                {"kind": "excess_above", "bound": 500.0, "basis": "source_stated_value", "source_refs": ["c1"]})
    tighter = mw("Molecular weight in excess of a lower bound",
                 {"kind": "excess_above", "bound": 300.0, "basis": "source_stated_value", "source_refs": ["c1"]})

    assert quantity_key(raw) != quantity_key(excess), "a transform makes it a different quantity"
    assert quantity_key(excess) != quantity_key(tighter), "a different bound is a different quantity"
    assert quantity_key(raw) == quantity_key(mw("Molecular weight restated")), "same quantity, different wording"

    # and the duplicate check must not retire the derived criterion against the raw registration
    assert duplicate_of_registered(excess, [raw]) is None
    assert duplicate_of_registered(tighter, [excess]) is None
    assert duplicate_of_registered(mw("Molecular weight restated"), [raw]) is not None


class RoundOneBadRefineReply(RoundOne):
    """Like RoundOne, but the provider answers the refine call with prose instead of json once."""

    def __init__(self):
        super().__init__()
        self.refine_calls = 0

    def __call__(self, request):
        if request.metadata.get("question", "") == "refine pool":
            self.refine_calls += 1
            if self.refine_calls == 1:
                raise _Unparseable("no JSON value found in the model reply")
        return super().__call__(request)


class _Unparseable(Exception):
    pass


def test_one_unusable_model_reply_does_not_destroy_the_round(core):
    """Measured on the clean derivation of 14 October 2026: after 1.5 hours, 24 documents read, 597
    claims admitted and 59 proposals pruned to 38, `refine` at iteration 2 received
    `parse_failed: no JSON value found in the model reply` on one batch and the whole run died with
    nothing promoted. `call_role` repairs an unparseable reply once and then raises, and every stage
    ran its batches in a bare loop. A reasoning model that occasionally answers in prose is a
    property of the provider, not a reason to discard the work.

    This enters through `derive_iterative`, the seam a run uses, because the lesson of 64be256 is
    that a test which does not is not evidence about production.
    """
    from mas.core.models import ModelError

    task_id, broker = setup(core)
    script = RoundOneBadRefineReply()

    class Failing(ScriptedAdapter):
        def complete(self, request):
            try:
                return super().complete(request)
            except _Unparseable as bad:
                raise ModelError("parse_failed", str(bad))

    roster = ModelRoster({"p": Failing("p", script, model="proposer-model", provider_family="family_a"),
                          "c": Failing("c", script, model="critic-model", provider_family="family_b")},
                         {"retriever": "p", "reader": "p", "proposer": "p", "adjudicator": "p", "critic": "c"})
    record = derivation_run.derive_iterative(core, broker, roster, task_id, dimensions=DIMENSIONS,
                                             catalog=EVIDENCE_CATALOG, by=OPERATOR, inner_iterations=4,
                                             stall_rounds=1)
    assert script.refine_calls >= 1, "the refine stage must actually have been reached"
    assert record["termination_reason"] != "unresolved", record["termination_reason"]
    assert record["promotion"] is not None, "the round must still reach promotion"
    # the failure is counted rather than hidden
    unresolved = [it for it in record["iterations"]
                  if (it.get("refine") or {}).get("batches_unresolved")]
    assert unresolved, "an unusable batch must be recorded in the stage's own stats"


# --- reducing a pool an earlier round already built ------------------------------------------
# `reduce_pool` is the pruning half of a round with the growth half removed: no literature, no
# proposals, only the stages that consolidate and the promotion that follows them. It exists because
# re-reaching merge through `derive_iterative` costs an hour of reading and returns a *different*
# pool each time -- saturation depends on what the searches happen to return -- so a merge strategy
# could never be tried twice against the same pool.


class RoundOneStoppedAtMerge(RoundOne):
    """RoundOne with the budget refusing the adjudicator, so the round ends at the stage that reduces.

    A round has to stop before promotion for anything to be left for a later pass to consolidate:
    promotion either registers the survivors -- and a registered criterion is an expert's to change,
    not a pool stage's -- or retires them. A budget refusal is how that happens in production, and
    the merge call is the one a long round reaches last and so loses first.
    """

    def __call__(self, request):
        if request.metadata.get("question") == "adjudicate merges":
            from mas.core.models import ModelError
            raise ModelError("quota_exhausted", "llm_turns budget exhausted for adjudicator")
        return super().__call__(request)


def unmerged_pool(core):
    """A pool a first round pruned but never merged, with its survivors still candidates."""
    task_id, broker = setup(core)
    first = derivation_run.derive_iterative(core, broker, roster_for(RoundOneStoppedAtMerge()), task_id,
                                            dimensions=DIMENSIONS, catalog=EVIDENCE_CATALOG, by=OPERATOR,
                                            inner_iterations=2, stall_rounds=2)
    assert first["termination_reason"] == "budget_exhausted"
    assert not [e for e in pool.fold(core, task_id).values() if e["parents"]], "nothing was merged yet"
    assert len(pool.active(pool.fold(core, task_id), ("candidate",))) >= 2, "nothing left to reduce"
    return task_id, first


def reduce(core, task_id, parent_run_id, script, **kwargs):
    return derivation_run.reduce_pool(core, roster_for(script), task_id, catalog=EVIDENCE_CATALOG, by=OPERATOR,
                                      continues_run_id=parent_run_id, **kwargs)


def changes_by(core, task_id, run_id):
    """The pool change records one run wrote."""
    return [e.payload for e in core.journal.replay(task_id)
            if e.event_type == "criterion.change_recorded" and e.payload.get("round_run_id") == run_id]


def test_a_reduce_pass_reads_no_literature_and_proposes_nothing(core):
    task_id, first = unmerged_pool(core)
    script = RoundOne()
    record = reduce(core, task_id, first["run_id"], script)
    assert [role for role, _ in script.calls if role in ("retriever", "reader")] == []
    assert not [q for _, q in script.calls if q.startswith("propose pool")]
    stage_events = [e.payload["stage"] for e in core.journal.replay(record["run_id"]) if e.event_type == "stage.opened"]
    assert not [s for s in stage_events if s == "enumerate" or s.startswith("propose")]
    assert "merge" in stage_events and "promote" in stage_events
    # no claim was admitted into this run's stream: a reduce pass has no document to admit one from
    assert not [e for e in core.journal.replay(record["run_id"])
                if e.event_type in ("evidence.admitted", "evidence.quarantined")]
    # and every lineage it touched already existed: a pass that proposes nothing records no `add`
    assert not [c for c in changes_by(core, task_id, record["run_id"]) if c["operation"] == "add"]


def test_a_reduce_pass_merges_the_pair_an_earlier_round_left_unmerged(core):
    task_id, first = unmerged_pool(core)
    record = reduce(core, task_id, first["run_id"], RoundOne())
    folded = pool.fold(core, task_id)
    merged = [e for e in folded.values() if e["parents"]]
    assert len(merged) == 1 and len(merged[0]["parents"]) == 2, "the pair was never merged"
    assert sorted(folded[ref.split("@v")[0]]["state"] for ref in merged[0]["parents"]) == ["merged_away", "merged_away"]
    # the child is a lineage of this run, and its parents are the versions it consumed
    child = next(c for c in changes_by(core, task_id, record["run_id"])
                 if c["operation"] == "merge" and c["state"] == "candidate")
    assert sorted(child["targets_in"]) == sorted(merged[0]["parents"]) and child["stage"] == "merge"
    assert sum(it["merge"]["merged"] for it in record["iterations"]) == 1
    assert {r["name"] for r in record["promotion"]["accepted"]} == {"Oral bioavailability", "Elimination half-life"}
    assert record["continues_run_id"] == first["run_id"] and record["chain_id"] == first["chain_id"]
    assert record["round_index"] == first["round_index"] + 1


def test_the_claims_a_pool_item_cites_still_resolve_in_a_reduce_pass(core):
    """The reason a reduce pass can prune at all: `refine` quotes the evidence it is repairing against
    and a merge may cite only its parents' claims, so an item whose claim ids no longer resolve is
    one the pool can only retire. The claims were recorded in the *earlier run's* stream, not the
    task's, so they are folded from the chain rather than re-read from the documents."""
    task_id, first = unmerged_pool(core)
    folded = pool.fold(core, task_id)
    cited = {c for e in pool.active(folded) for c in e["item"]["supporting_claim_ids"]}
    offered = []

    class Capturing(RoundOne):
        def __call__(self, request):
            if request.metadata.get("question") == "adjudicate merges":
                offered.append(request.messages[0]["content"].split("\n\nCited claims:\n")[1])
            return super().__call__(request)

    record = reduce(core, task_id, first["run_id"], Capturing())
    resolvable = {c["claim_id"] for c in derivation_run.ledger.claims(core, [first["run_id"], task_id])}
    assert cited and cited <= resolvable and record["claims_resolvable"] == len(resolvable)
    # and the resolution is not vacuous: the one item citing an id no ledger holds was already retired
    assert [e["state"] for e in folded.values() if "claim_that_does_not_exist"
            in e["item"]["supporting_claim_ids"]] == ["filtered_out"]
    # the adjudicator was given the claim text behind the items it was asked to merge
    assert offered and all(any(claim in block for claim in cited) for block in offered)
    # and the merged child kept a parent's claim, which only validates while the claim resolves
    child = next(e for e in pool.fold(core, task_id).values() if e["parents"])
    assert child["item"]["supporting_claim_ids"] and set(child["item"]["supporting_claim_ids"]) <= cited


def test_a_reduce_pass_is_refused_against_a_run_that_is_not_a_criteria_derivation(core):
    task_id, broker = setup(core)
    derivation_run.derive_iterative(core, broker, roster_for(RoundOne()), task_id, dimensions=DIMENSIONS,
                                    catalog=EVIDENCE_CATALOG, by=OPERATOR, inner_iterations=4, stall_rounds=1)
    criteria.confirm_rule_set(core, task_id, by=OPERATOR, allow_pending=True)
    sweep = RunController(core, broker, roster_for(RoundOne()),
                          adapter={"adapter_id": "a", "adapter_version": "1"}).start(task_id, by=OPERATOR,
                                                                                     execute=False)
    with pytest.raises(derivation_run.DerivationError, match="not a criteria derivation run"):
        reduce(core, task_id, sweep, RoundOne())
    with pytest.raises(derivation_run.DerivationError, match="is not a run"):
        reduce(core, task_id, task_id, RoundOne())
    with pytest.raises(derivation_run.DerivationError, match="not a criteria derivation run to reduce"):
        reduce(core, task_id, None, RoundOne())
    # every refusal happened before a run was bound: the derivation round and the sweep are all there is
    assert len(core.journal.streams("run_")) == 2


def test_a_budget_refusal_ends_a_reduce_pass_as_budget_exhausted_rather_than_crashing(core):
    task_id, first = unmerged_pool(core)
    before = pool.pool_hash(pool.fold(core, task_id))
    record = reduce(core, task_id, first["run_id"], RoundOne(), budget=Budget({"llm_turns": 1}))
    assert record["termination_reason"] == "budget_exhausted"
    assert core.journal.replay(record["run_id"])[-1].event_type == "run.unresolved"
    assert record["continuation_decision"]["decision"] == "continue_next_round"
    # the pass stopped on the first stage that was refused, so the pool it was handed is still there
    assert pool.pool_hash(pool.fold(core, task_id)) == before
    assert any(e["state"] in pool.ACTIVE_STATES for e in pool.fold(core, task_id).values())


def test_running_a_reduce_pass_twice_leaves_the_second_nothing_to_do(core):
    task_id, first = unmerged_pool(core)
    once = reduce(core, task_id, first["run_id"], RoundOne())
    second_script = RoundOne()
    twice = reduce(core, task_id, once["run_id"], second_script)
    assert twice["chain_id"] == once["chain_id"] and twice["round_index"] == once["round_index"] + 1
    assert twice["termination_reason"] == "diminishing_information_gain"
    assert twice["pool_hash"] == once["pool_hash"] and twice["pool_states"] == once["pool_states"]
    assert second_script.calls == [], "an empty pool is nothing to ask a model about"
    assert twice["promotion"] == {"accepted": [], "disputed": [], "deferred": [], "duplicates": []}
    assert changes_by(core, task_id, twice["run_id"]) == []
    assert twice["continuation_decision"]["decision"] == "stop"


def test_a_round_and_a_reduce_pass_record_the_same_binding_and_stage_shapes(core):
    """A reader comparing two rounds of one chain should not have to know which function ran them:
    the fields they share carry the same names, and the run row the workbench builds is read off
    `run.created` the same way for both."""
    from mas.ui import views

    task_id, broker = setup(core)
    derived = derivation_run.derive_iterative(core, broker, roster_for(RoundOne()), task_id, dimensions=DIMENSIONS,
                                              catalog=EVIDENCE_CATALOG, by=OPERATOR, inner_iterations=4,
                                              stall_rounds=1)
    reduced = reduce(core, task_id, derived["run_id"], RoundOne())
    bindings = [views._binding(core, record["run_id"]) for record in (derived, reduced)]
    assert all(b["task_id"] == task_id and b["run_purpose"] == "criteria_derivation" for b in bindings)
    assert set(bindings[0]) - set(bindings[1]) == {"research", "dimensions", "evidence_cutoff"}
    assert set(bindings[1]) - set(bindings[0]) == set()
    assert [b["reads_new_evidence"] for b in bindings] == [True, False]
    for field in ("chain_id", "continuation_kind", "round_index", "purpose_note", "stages", "merge_overlap",
                  "inner_iterations", "stall_rounds", "max_refines", "settings", "role_bindings"):
        assert field in bindings[0] and field in bindings[1], field

    def shapes(run_id, kind):
        return {frozenset(e.payload) for e in core.journal.replay(run_id) if e.event_type == kind}

    for kind in ("run.created", "stage.opened", "stage.closed", "round.opened", "round.closed", "run.completed"):
        assert shapes(derived["run_id"], kind) == shapes(reduced["run_id"], kind), kind
    # and both rounds' records are findable again by the key the closing event names
    for record in (derived, reduced):
        assert derivation_run.record_of(core, record["run_id"])["run_id"] == record["run_id"]
    shared = set(derived) & set(reduced)
    assert set(derived) - shared == {"mandated", "enumeration", "proposed"}
    assert set(reduced) - shared == {"reduce_only", "claims_resolvable"}
    for field in ("pool_states", "pool_hash", "termination_reason", "independence", "budget",
                  "continuation_decision", "artifact_id", "iterations", "promotion"):
        assert field in shared, field
