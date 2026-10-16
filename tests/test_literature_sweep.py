"""The literature cell, end to end through the candidate sweep (design §8.1, §9 step 3).

This is the path the acceptance case rests on and the one no sweep had ever taken: every run so
far was confirmed with `--defer-capability literature_retrieval`, so the task's literature-bound
criteria were listed as deferred and no candidate ever had one evaluated.

What is pinned here is the whole way through -- a query built from the candidate's identity and
the attribute's own template, documents fetched under `read.max_papers_per_candidate`, claims
extracted, quote-checked and admitted, the cell given a value, and each cited claim carrying a
quoted span and a locator inside its document -- together with the per-run `LiteratureCache` that
makes it affordable, and the filters that decide whether any of it reaches a verdict: the unit the
reader reports, the determination basis it declares, and whether the span ties its number to this
candidate and this attribute at all.

The last two sections are the two repairs of 15 October 2026, each measured on the real path
before it was made: the harvest (a cell saw only the papers its own query selected, while the
extraction it was paying for answered every literature attribute) and the attribution of a number
inside a verified quote (an arm comparison read as the candidate's own figure).

The attributes here carry the *shapes* the manuscript registry carries -- bespoke unit strings
('% of patients', '% oral bioavailability'), `aggregation: median`, no cutoff and
`predicate_form: ordering`, and no `acceptable_determination_bases` -- because those shapes are
what the admission filters act on, and a fixture using '%' everywhere would prove nothing
about them.
"""

import pytest

from mas.core import assessor, criteria, evidence, ledger, reading, review, task, vocab
from mas.core.broker import Broker, ProviderResponse, ToolContract
from mas.core.controller import RunController
from mas.core.journal import actor
from mas.core.models import ModelRoster, ScriptedAdapter
from mas.core.runtime import Core
from tests.fakes import FakeIdentity, FakeProperty

OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")
EXPERT = actor("human", "E1", "expert", identity_basis="recorded_attestation")
ADAPTER = {"adapter_id": "test_adapter", "adapter_version": "1", "primary_scheme": "ik"}

SPEC = {
    "objective_text": "Rank oral multi-kinase inhibitors by exposure and tolerability",
    "mode": "conditional",
    "scope_entities": [{"entity_kind": "target", "identifier": "CSF1R", "role": "required"}],
    "candidate_universe": {"kind": "enumerated_set", "members": ["alpha", "beta"]},
    "constraints": [{"text": "oral", "kind": "route", "hardness": "hard"}],
    "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True},
    "human_review_requirements": {"recommended_requires_hd": False},
}


def literature_attribute(name: str, unit: str, tail: str, term: str) -> dict:
    return {"name": name, "definition": f"{name}, as reported in human studies",
            "measurement_kind": "quantitative", "unit": unit, "direction": "lower_better",
            "aggregation": "median",
            "acceptable_value_sources": ["peer_reviewed", "reference_text", "curated_measurement"],
            "evidence_request": {"capability": "literature_retrieval", "question_kind": "search",
                                 "parameters": {"query_template": "({names}) AND " + tail,
                                                "relevance_terms": [term], "search_limit": 10}}}


BIOAVAILABILITY = literature_attribute(
    "Reported oral bioavailability in humans", "% oral bioavailability",
    '("oral bioavailability" OR "absolute bioavailability")', "bioavailability")
BIOAVAILABILITY["direction"] = "higher_better"
HYPERTENSION = literature_attribute(
    "Incidence of grade 3 or higher hypertension", "% of patients", "(hypertension)", "hypertension")
STEADY_STATE = literature_attribute(
    "Time to steady state on repeated oral dosing", "days", '("steady state")', "steady state")
LITERATURE_ATTRIBUTES = (BIOAVAILABILITY, HYPERTENSION, STEADY_STATE)
QUERY_TAILS = {a["name"]: a["evidence_request"]["parameters"]["query_template"].split(") AND ", 1)[1]
               for a in LITERATURE_ATTRIBUTES}
# the real literature rules: a preference with no cutoff, ranked in the attribute's direction
ORDERING = {"rule_kind": "preference", "cutoff": None, "cutoff_basis": "none_evidence_insufficient",
            "predicate_form": "ordering"}

MW = {"name": "Molecular weight", "definition": "Molecular weight of the parent compound",
      "measurement_kind": "quantitative", "unit": "g/mol", "direction": "lower_better",
      "aggregation": "consensus", "acceptable_value_sources": ["database_entry"],
      "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                           "identifier_scheme": "ik", "parameters": {"property": "MW"}}}
MW_RULE = {"rule_kind": "hard_exclusion", "cutoff": {"comparator": "<=", "value": 500, "unit": "g/mol"},
           "cutoff_basis": "expert_set"}
WEIGHTS = {("ALPHA", "MW"): 300.0, ("BETA", "MW"): 450.0}

IDENTITIES = {name: [{"preferred_label": name.title(),
                      "identifiers": [{"scheme": "ik", "value": name.upper()}],
                      # one usable search label and one that is not: a CAS number is never a query term
                      "aliases": [{"alias": f"{name.title()}ib"}, {"alias": "1234-56-7"}],
                      "link_basis": "name_match_single_candidate"}]
              for name in ("alpha", "beta")}

# Per candidate: the papers a search returns in rank order. read.max_papers_per_candidate is 2,
# so the third paper of each candidate is found and never read.
PAPERS = {"Alpha": ["A1", "A2", "A3"], "Beta": ["B1", "B2", "B3"]}
VALUES = {   # paper -> {attribute name: value}, the value that paper reports
    "A1": {BIOAVAILABILITY["name"]: 78.0, HYPERTENSION["name"]: 29.0},
    "A2": {STEADY_STATE["name"]: 7.0},
    "A3": {BIOAVAILABILITY["name"]: 5.0},
    "B1": {BIOAVAILABILITY["name"]: 41.0},
    "B2": {HYPERTENSION["name"]: 12.0, STEADY_STATE["name"]: 14.0},
    "B3": {STEADY_STATE["name"]: 99.0},
}
UNITS = {a["name"]: a["unit"] for a in LITERATURE_ATTRIBUTES}


def quote_for(paper: str, label: str, attribute_name: str) -> str:
    value = VALUES[paper][attribute_name]
    shown = int(value) if float(value).is_integer() else value
    return (f"In this cohort {label} showed a {attribute_name.lower()} of "
            f"{shown} {UNITS[attribute_name]} in study {paper}")


class PaperSearch:
    """One search tool, recording every query it is asked, so the template can be checked."""

    contract = ToolContract(tool_id="tool_paper_search", capability="literature_retrieval",
                            capability_kind="source_retrieval", question_kinds=("search",), contract_version="1",
                            implementation_version="fake-1", purpose_statement="papers on one compound",
                            evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def __init__(self):
        self.queries: list[str] = []

    def invoke(self, question_kind, inputs):
        self.queries.append(inputs["query"])
        label = next((l for l in PAPERS if l in inputs["query"]), None)
        if label is None:
            return ProviderResponse(values=[])
        hits = [{"pmcid": f"PMC_{paper}", "doi": f"10.0/{paper}",
                 "title": f"{label} in advanced solid tumours, study {paper}",
                 "abstract_html": f"A phase I study of {label}.",
                 "identifiers": [{"scheme": "doi", "value": f"10.0/{paper}"}]}
                for paper in PAPERS[label]]
        return ProviderResponse(values=[{"name": "search_hit", "value": h, "value_kind": "curated"} for h in hits])


class PaperReader:
    contract = ToolContract(tool_id="tool_paper_reader", capability="document_reading",
                            capability_kind="document_reading", question_kinds=("read",), contract_version="1",
                            implementation_version="fake-1", purpose_statement="full text of one paper",
                            evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def __init__(self):
        self.reads: list[str] = []

    def invoke(self, question_kind, inputs):
        paper = inputs["pmcid"].split("_", 1)[1]
        label = next(l for l, papers in PAPERS.items() if paper in papers)
        self.reads.append(paper)
        title = f"{label} in advanced solid tumours, study {paper}"
        passages = [{"passage_id": "title", "kind": "title", "section_path": [], "text": title}]
        for index, attribute_name in enumerate(VALUES[paper], start=1):
            passages.append({"passage_id": f"sec1.p{index}", "kind": "paragraph", "section_path": ["Results"],
                             "text": quote_for(paper, label, attribute_name) + "."})
        document = {"title": title, "passages": passages, "access_state": "full_text_available",
                    "reading_depth": "full_text", "source_hit": {"is_preprint": False}}
        return ProviderResponse(values=[{"name": "document", "value": document, "value_kind": "curated"}])


class ReaderModel:
    """The reader role: one call per (candidate, document), counted so the memo can be checked.

    `unit` and `basis` rewrite what the model reports. The reader is the only thing that decides a
    literature claim's unit and its determination basis, and `assessor.usable_claims` is the only
    thing that reads them, so overriding them here is how the two admission filters get exercised.
    """

    def __init__(self, *, unit: str | None = None, basis: str = "measured"):
        self.unit_override, self.basis = unit, basis
        self.calls: list[str] = []

    def __call__(self, request):
        text = request.messages[0]["content"]
        paper = next(p for p in VALUES if f"study {p}" in text)
        label = next(l for l, papers in PAPERS.items() if paper in papers)
        assert f"Candidate: {label}" in text, "the reader is asked about one named candidate"
        self.calls.append(f"{label}:{paper}")
        offered = request.response_schema["properties"]["claims"]["items"]["properties"]
        assert "attribute_name" in offered, "one read of a paper serves every literature attribute"
        claims = []
        for index, attribute_name in enumerate(VALUES[paper], start=1):
            if attribute_name not in offered["attribute_name"]["enum"]:
                continue
            quote = quote_for(paper, label, attribute_name)
            claims.append({"passage_id": f"sec1.p{index}", "quoted_span": quote, "statement": quote,
                           "determination_basis": self.basis, "polarity": "supports",
                           "value": VALUES[paper][attribute_name],
                           "unit": self.unit_override or UNITS[attribute_name],
                           "entities": [label], "attribute_name": attribute_name})
        return {"claims": claims}


def setup_task(core, *, defer: bool = False, with_database_rule: bool = False) -> str:
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    if with_database_rule:
        criteria.propose(core, task_id, MW, MW_RULE, by=OPERATOR)
    for attribute in LITERATURE_ATTRIBUTES:
        criteria.propose(core, task_id, attribute, dict(ORDERING), by=OPERATOR)
    for item in review.items(core, [task_id]).values():
        review.decide(core, item, decision="approve", actor=EXPERT, reason_text="", entry="interactive",
                      historical_list_exposure="not_exposed")
    criteria.confirm_rule_set(core, task_id, by=OPERATOR, coverage_floor=0.5,
                              defer_capabilities=("literature_retrieval",) if defer else (),
                              defer_reason="held out of this run" if defer else "")
    return task_id


def make_controller(core, model: ReaderModel, *, workers: int = 1):
    broker = Broker(core, sleep=lambda s: None)
    search, reader = PaperSearch(), PaperReader()
    broker.register(FakeIdentity(IDENTITIES))
    broker.register(FakeProperty(WEIGHTS))
    broker.register(search)
    broker.register(reader)
    roster = ModelRoster({"s": ScriptedAdapter("s", model, model="scripted-reader")}, {"reader": "s"})
    return RunController(core, broker, roster, adapter=ADAPTER, workers=workers), search, reader


def literature_cells(core, run_id) -> dict[tuple[str, str], dict]:
    """Every assessed cell of a literature attribute, keyed by (attribute id, candidate id)."""
    out = {}
    for event in core.journal.replay(run_id):
        if event.event_type != "candidate.assessed":
            continue
        attribute_ref = event.payload["attribute_ref"]
        if attribute_ref.startswith("attr_molecular-weight"):
            continue
        out[(attribute_ref.split("@")[0], event.payload["candidate_ref"].split("-")[-1])] = \
            core.artifacts.payload(event.payload["artifact_id"])
    return out


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c


def test_a_literature_sweep_searches_reads_extracts_and_gives_every_cell_a_located_value(core):
    """The whole path, which no sweep had ever taken. Each assertion below is one link of it."""
    model = ReaderModel()
    controller, search, reader = make_controller(core, model)
    task_id = setup_task(core)
    run_id = controller.start(task_id, by=OPERATOR, sweep_seed=3)
    assert controller.current_state(run_id) == "completed"

    # 1. one query per (candidate, attribute), built from the attribute's own template and the
    #    candidate's labels: the preferred label and its name-like aliases, never the CAS number
    assert sorted(search.queries) == sorted(f"({label} OR {label}ib) AND {tail}"
                                            for label in PAPERS for tail in QUERY_TAILS.values())
    assert not any("1234-56-7" in query for query in search.queries)

    # 2. documents fetched, bounded by read.max_papers_per_candidate (default 2), each read once
    assert sorted(reader.reads) == ["A1", "A2", "B1", "B2"]

    # 3. one extraction per (candidate, paper), however many of the three attributes wanted it
    assert sorted(model.calls) == ["Alpha:A1", "Alpha:A2", "Beta:B1", "Beta:B2"]

    # 4. every cell carries the value the paper reported, aggregated as the attribute asked
    cells = literature_cells(core, run_id)
    assert {key: cell["value"] for key, cell in cells.items()} == {
        ("attr_reported-oral-bioavailability-in-humans", "ALPHA"): 78.0,
        ("attr_reported-oral-bioavailability-in-humans", "BETA"): 41.0,
        ("attr_incidence-of-grade-3-or-higher-hypertension", "ALPHA"): 29.0,
        ("attr_incidence-of-grade-3-or-higher-hypertension", "BETA"): 12.0,
        ("attr_time-to-steady-state-on-repeated-oral-dosing", "ALPHA"): 7.0,
        ("attr_time-to-steady-state-on-repeated-oral-dosing", "BETA"): 14.0}
    assert {cell["verdict"] for cell in cells.values()} == {"pass"}
    assert {cell["determination_basis"] for cell in cells.values()} == {"measured"}
    assert all(cell["unit"] == UNITS[name] for name, cell in
               ((a["name"], cells[(f"attr_{criteria.slug(a['name'])}", c)])
                for a in LITERATURE_ATTRIBUTES for c in ("ALPHA", "BETA")))
    assert not any(cell["set_aside_claims"] for cell in cells.values())

    # 5. each cited claim is admitted and carries a verified quote and a locator in its document
    claims = {c["claim_id"]: c for c in ledger.claims(core, [run_id])}
    cited = [claims[ref] for cell in cells.values() for ref in cell["value_source_claim_refs"]]
    assert len(cited) == 6
    for claim in cited:
        assert claim["admission_state"] == "admitted"
        assert claim["claim_type"] == "literature_extracted"
        assert claim["evidence_kind"] == "peer_reviewed"          # the registry's kind for the source
        assert claim["location"]["location_kind"] == "paragraph"
        assert claim["location"]["locator_value"].startswith("sec1.p")
        assert claim["location"]["section_path"] == ["Results"]
        assert claim["location"]["span_checked_against_source"] is True
        assert str(int(claim["value"])) in claim["location"]["quoted_span"]
        assert claim["source_ref"].startswith("src_doi_10.0/")
        assert claim["document_artifact_id"]
        assert set(claim["admission_reasons"]) == {"quote_verified", "value_in_quote",
                                                   "candidate_named_in_quote"}
    # and the reason record of a value-bearing cell cites the claims rather than an absence check
    reason = core.artifacts.payload(
        next(cell for cell in cells.values())["reason_artifact_id"])
    assert reason["evidence_refs"] and reason["absence_check_record"] is None


def test_one_paper_is_read_and_extracted_once_per_candidate_however_many_attributes_want_it(core):
    """The run's `LiteratureCache` is what makes a wall of literature criteria affordable: without
    it the sweep pays a reader tool call and an extraction model call per (candidate, attribute,
    paper) -- here 12 instead of 4, and on the real task 26 attributes instead of 3."""
    model = ReaderModel()
    controller, search, reader = make_controller(core, model)
    run_id = controller.start(setup_task(core), by=OPERATOR)
    assert len(literature_cells(core, run_id)) == 6           # 2 candidates x 3 attributes
    assert sorted(reader.reads) == sorted(set(reader.reads)) == ["A1", "A2", "B1", "B2"]
    assert sorted(model.calls) == sorted(set(model.calls)) and len(model.calls) == 4
    # the search memo keys on the query, and the three templates give three distinct queries
    assert len(search.queries) == len(set(search.queries)) == 6


def test_a_deferred_capability_means_no_literature_cell_is_scheduled_at_all(core):
    """What every sweep run so far did. The literature rules are listed as deferred rather than
    entered, so the search tool is never called and no candidate has a literature cell."""
    model = ReaderModel()
    controller, search, reader = make_controller(core, model)
    task_id = setup_task(core, defer=True, with_database_rule=True)
    rule_set = criteria.rule_set(core, task_id)
    assert [e["rule_ref"] for e in rule_set["entries"]] == ["rule_molecular-weight@v1"]
    assert sorted(d["rule_ref"] for d in rule_set["deferred"]) == [
        f"rule_{criteria.slug(a['name'])}@v1" for a in sorted(LITERATURE_ATTRIBUTES, key=lambda a: criteria.slug(a["name"]))]
    assert {d["capability"] for d in rule_set["deferred"]} == {"literature_retrieval"}
    run_id = controller.start(task_id, by=OPERATOR)
    assert controller.current_state(run_id) == "completed"
    assert literature_cells(core, run_id) == {}
    assert search.queries == [] and reader.reads == [] and model.calls == []


def test_a_unit_the_reader_does_not_echo_leaves_a_quantitative_literature_cell_unknown(core):
    """The filter that decides whether any of this reaches a verdict.

    `assessor.usable_claims` compares `canonical_unit(claim.unit)` against the attribute's declared
    unit, and `UNIT_SYNONYMS` knows nothing about a registry's bespoke unit strings. A reader that
    reports the plain '%' the paper prints -- which is what the passage says -- has its claim
    admitted to the ledger and then set aside as `unit_unresolved`, and the cell is
    `unknown_missing` with its evidence in hand. Every literature attribute of the manuscript task
    is quantitative and every one declares a unit of this shape.
    """
    usable, set_aside = assessor.usable_claims(
        [{"claim_id": "c1", "admission_state": "admitted", "evidence_kind": "peer_reviewed",
          "determination_basis": "measured", "value": 29.0, "unit": "%"}], HYPERTENSION)
    assert usable == [] and set_aside[0]["set_aside_reason"] == "unit_unresolved"

    model = ReaderModel(unit="%")
    controller, _, reader = make_controller(core, model)
    run_id = controller.start(setup_task(core), by=OPERATOR)
    assert sorted(reader.reads) == ["A1", "A2", "B1", "B2"], "read and extracted, then discarded"
    cells = literature_cells(core, run_id)
    assert {cell["verdict"] for cell in cells.values()} == {"unknown_missing"}
    assert {entry["reason"] for cell in cells.values() for entry in cell["set_aside_claims"]} == \
        {"unit_unresolved"}
    assert len(ledger.claims(core, [run_id])) == 6            # admitted to the ledger all the same


def test_an_asserted_literature_claim_is_evidence_for_no_attribute_that_declares_no_bases(core):
    """The other filter. A reader marks a statement without data `asserted`; an attribute that does
    not name `asserted` in `acceptable_determination_bases` falls back to
    `assessor.DEFAULT_DETERMINATION_BASES` and such a claim is set aside."""
    assert assessor.DEFAULT_DETERMINATION_BASES == ("measured", "derived")
    for attribute in LITERATURE_ATTRIBUTES:
        assert attribute.get("acceptable_determination_bases") is None
    model = ReaderModel(basis="asserted")
    controller, _, reader = make_controller(core, model)
    run_id = controller.start(setup_task(core), by=OPERATOR)
    assert reader.reads
    cells = literature_cells(core, run_id)
    assert {cell["verdict"] for cell in cells.values()} == {"unknown_missing"}
    assert {entry["reason"] for cell in cells.values() for entry in cell["set_aside_claims"]} == \
        {"determination_basis_not_accepted"}


def test_a_cell_whose_evidence_is_only_in_an_unread_paper_is_unknown_not_wrong(core):
    """`read.max_papers_per_candidate` is a ceiling on reading, and a value that lives past it is
    simply not found. A1 and A2 are read; A3's bioavailability figure of 5 never enters, so the
    cell reports 78 rather than a median over both -- which is a bound on recall, not an error."""
    model = ReaderModel()
    controller, _, reader = make_controller(core, model)
    run_id = controller.start(setup_task(core), by=OPERATOR)
    assert "A3" not in reader.reads and "B3" not in reader.reads
    cells = literature_cells(core, run_id)
    assert cells[("attr_reported-oral-bioavailability-in-humans", "ALPHA")]["value"] == 78.0
    assert cells[("attr_time-to-steady-state-on-repeated-oral-dosing", "BETA")]["value"] == 14.0


def test_the_query_is_the_attributes_own_template_filled_with_the_identitys_labels():
    """`evidence.literature_query` is the only place a candidate's identity reaches a search."""
    attribute = dict(BIOAVAILABILITY, attribute_id="attr_x", version=1)
    assert evidence.literature_query(attribute, ["Surufatinib", "HMPL-012", "sulfatinib"]) == (
        '(Surufatinib OR "HMPL-012" OR sulfatinib) AND '
        '("oral bioavailability" OR "absolute bioavailability")')
    assert evidence.name_like("Surufatinib") and evidence.name_like("HMPL-012")
    assert not evidence.name_like("1234-56-7")
    assert not evidence.name_like("(2S)-2-amino-3-phenylpropanoyl-pyrrolidine-2-carboxamide")
    # an attribute that declares no template still produces a bare name query rather than crashing
    bare = {"evidence_request": {"capability": "literature_retrieval", "question_kind": "search"}}
    assert evidence.literature_query(bare, ["Alpha", "Beta"]) == "(Alpha OR Beta)"


# --- the harvest defect, and its repair -----------------------------------------------
# Measured on the real path, 14 October 2026: 26 literature criteria x 2 candidates
# (surufatinib, sunitinib) against `task_01M4TWZXZEB1SQPS7H47C8BX01`, on a copy of the primary
# store. 70 documents were read, `reading.extract_claims` recorded 375 claims and admitted 253 of
# them -- and only 70 claims were ever offered to a cell, because `gather` harvested a cell's claims
# from the papers *its own query* selected, while the read and the extraction were shared across
# every literature attribute. Re-assessing every cell from the ledger afterwards: 16 of the 52
# cells would be value-bearing, against the 6 that were -- and the two candidates would be covered
# 9 and 7 rather than 5 and 1. The repair reads the union of a candidate's literature queries'
# selections before assessing any of its cells (`evidence.read_literature`, driven by
# `controller._literature_pass`); with the attribution guard below, the same 52 cells come to 13.
#
# The clearest single case is the one the acceptance case turns on. Surufatinib's oral
# bioavailability was extracted from doi:10.3389/fphar.2024.1498339 as
#   "After oral administration of sulfatinib, the serum level of the original drug is about 40.3%."
# value 40.3, unit "% oral bioavailability" (the attribute's own unit), basis measured, quote
# verified, candidate named in the quote, admitted. The cell
# `Reported oral bioavailability in humans x surufatinib` came back `unknown_missing` with zero
# claims, because that paper was read for another attribute's query.


class SplitSearch:
    """Two attributes whose queries select different papers: the shape the real run produced."""

    contract = PaperSearch.contract

    def __init__(self):
        self.queries: list[str] = []

    def invoke(self, question_kind, inputs):
        self.queries.append(inputs["query"])
        # the bioavailability query finds P_other (which reports nothing); every other query finds
        # P_shared (which reports the bioavailability figure as well as its own attribute's)
        paper = "P_other" if "bioavailability" in inputs["query"] else "P_shared"
        hit = {"pmcid": f"PMC_{paper}", "doi": f"10.0/{paper}", "title": f"Alpha study {paper}",
               "abstract_html": "A phase I study of Alpha.",
               "identifiers": [{"scheme": "doi", "value": f"10.0/{paper}"}]}
        return ProviderResponse(values=[{"name": "search_hit", "value": hit, "value_kind": "curated"}])


SHARED_QUOTE = "After oral administration Alpha reached a measured oral bioavailability of 40.3"
HYPERTENSION_QUOTE = "Grade 3 or higher hypertension occurred in 29 of the treated patients"


class SplitReader:
    contract = PaperReader.contract

    def __init__(self):
        self.reads: list[str] = []

    def invoke(self, question_kind, inputs):
        paper = inputs["pmcid"].split("_", 1)[1]
        self.reads.append(paper)
        passages = [{"passage_id": "title", "kind": "title", "section_path": [], "text": f"Alpha study {paper}"}]
        if paper == "P_shared":
            passages += [
                {"passage_id": "sec1.p1", "kind": "paragraph", "section_path": ["Results"],
                 "text": HYPERTENSION_QUOTE + "."},
                {"passage_id": "sec1.p2", "kind": "paragraph", "section_path": ["Introduction"],
                 "text": SHARED_QUOTE + "."}]
        else:
            passages.append({"passage_id": "sec1.p1", "kind": "paragraph", "section_path": ["Results"],
                             "text": "Alpha was well tolerated in this cohort."})
        document = {"title": f"Alpha study {paper}", "passages": passages,
                    "access_state": "full_text_available", "reading_depth": "full_text",
                    "source_hit": {"is_preprint": False}}
        return ProviderResponse(values=[{"name": "document", "value": document, "value_kind": "curated"}])


def split_reader_script(request):
    text = request.messages[0]["content"]
    if "Alpha study P_shared" not in text:
        return {"claims": []}
    return {"claims": [
        {"passage_id": "sec1.p1", "quoted_span": HYPERTENSION_QUOTE, "statement": HYPERTENSION_QUOTE,
         "determination_basis": "measured", "polarity": "supports", "value": 29.0, "unit": "% of patients",
         "entities": ["Alpha"], "attribute_name": HYPERTENSION["name"]},
        {"passage_id": "sec1.p2", "quoted_span": SHARED_QUOTE, "statement": SHARED_QUOTE,
         "determination_basis": "measured", "polarity": "supports", "value": 40.3,
         "unit": "% oral bioavailability", "entities": ["Alpha"], "attribute_name": BIOAVAILABILITY["name"]}]}


def split_controller(core):
    broker = Broker(core, sleep=lambda s: None)
    search, reader = SplitSearch(), SplitReader()
    broker.register(FakeIdentity({"alpha": IDENTITIES["alpha"]}))
    broker.register(search)
    broker.register(reader)
    roster = ModelRoster({"s": ScriptedAdapter("s", split_reader_script, model="scripted-reader")}, {"reader": "s"})
    return RunController(core, broker, roster, adapter=ADAPTER), search, reader


def split_task(core) -> str:
    spec = dict(SPEC, candidate_universe={"kind": "enumerated_set", "members": ["alpha"]})
    task_id, _ = task.record_version(core, spec, by=OPERATOR)
    for attribute in (BIOAVAILABILITY, HYPERTENSION):
        criteria.propose(core, task_id, attribute, dict(ORDERING), by=OPERATOR)
    for item in review.items(core, [task_id]).values():
        review.decide(core, item, decision="approve", actor=EXPERT, reason_text="", entry="interactive",
                      historical_list_exposure="not_exposed")
    criteria.confirm_rule_set(core, task_id, by=OPERATOR, coverage_floor=0.5)
    return task_id


def test_a_claim_for_one_attribute_read_for_another_is_admitted_to_the_ledger(core):
    """The measurement. The bioavailability figure is extracted, quote-checked and admitted under
    the bioavailability attribute, from a paper the hypertension query selected."""
    controller, search, reader = split_controller(core)
    run_id = controller.start(split_task(core), by=OPERATOR)
    assert sorted(reader.reads) == ["P_other", "P_shared"]
    admitted = [c for c in ledger.claims(core, [run_id])
                if c["attribute_ref"].startswith("attr_reported-oral-bioavailability")]
    assert len(admitted) == 1
    assert admitted[0]["value"] == 40.3 and admitted[0]["unit"] == "% oral bioavailability"
    assert admitted[0]["determination_basis"] == "measured"
    assert admitted[0]["location"]["span_checked_against_source"] is True
    assert admitted[0]["source_ref"] == "src_doi_10.0/P_shared"


def test_a_cell_uses_an_admitted_claim_for_its_attribute_that_another_cells_read_produced(core):
    """What `one read of this paper for this candidate serves every literature attribute` promises.

    The read and the extraction were already shared through `LiteratureCache`; the harvest was not,
    so this cell came back `unknown_missing` while its own evidence sat admitted in the ledger. The
    repair reads the union of the candidate's literature queries' selections (`read_literature`)
    before any of its cells is assessed, rather than harvesting opportunistically from
    `cache.extractions` -- which would have made a cell's claims depend on which other cell
    finished first, and the run unreplayable at `assess.workers > 1`.
    """
    controller, _, _ = split_controller(core)
    run_id = controller.start(split_task(core), by=OPERATOR)
    cells = literature_cells(core, run_id)
    assert cells[("attr_reported-oral-bioavailability-in-humans", "ALPHA")]["value"] == 40.3
    assert cells[("attr_reported-oral-bioavailability-in-humans", "ALPHA")]["verdict"] == "pass"
    # the claim it used is the one the hypertension query's paper produced
    cited = cells[("attr_reported-oral-bioavailability-in-humans", "ALPHA")]["value_source_claim_refs"]
    claims = {c["claim_id"]: c for c in ledger.claims(core, [run_id])}
    assert [claims[ref]["source_ref"] for ref in cited] == ["src_doi_10.0/P_shared"]


def test_one_candidates_literature_is_read_once_for_every_one_of_its_cells(core):
    """The union, and its two bounds. Three attributes with three different queries select three
    papers between them; the union is read once and every cell is assessed against all of it, so
    the reading is `read.max_papers_per_candidate` per query and the de-duplicated union across
    queries -- not one reading per cell."""
    model = ReaderModel()
    controller, search, reader = make_controller(core, model)
    run_id = controller.start(setup_task(core), by=OPERATOR)
    assert len(search.queries) == 6                       # 3 attributes x 2 candidates, each asked once
    assert sorted(reader.reads) == ["A1", "A2", "B1", "B2"]      # 2 per query, 2 distinct in the union
    assert sorted(model.calls) == ["Alpha:A1", "Alpha:A2", "Beta:B1", "Beta:B2"]
    # one step per candidate rather than one per rule, because the candidate is what is read
    steps = [e.payload for e in core.journal.replay(run_id) if e.event_type == "step.completed"]
    literature = [s for s in steps if s.get("candidate_ref")]
    assert sorted(s["candidate_ref"] for s in literature) == ["cand_ik-ALPHA", "cand_ik-BETA"]
    assert {s["union_documents"] for s in literature} == {2}
    assert all(len(s["rule_refs"]) == 3 for s in literature)


@pytest.mark.parametrize("workers", (1, 4))
def test_the_order_cells_are_assessed_in_changes_no_cells_value_or_claims(tmp_path, workers):
    """Runs are replayed and their digests compared, so no cell's value may depend on the order its
    neighbours were assessed in. The union is what makes that true: it is complete before the first
    cell of a candidate is assessed, so `assess.workers` moves nothing but the wall clock."""
    with Core.open(tmp_path / f"root{workers}") as core:
        model = ReaderModel()
        controller, _, _ = make_controller(core, model, workers=workers)
        run_id = controller.start(setup_task(core), by=OPERATOR, sweep_seed=5)
        assert controller.current_state(run_id) == "completed"
        claims = {c["claim_id"]: c for c in ledger.claims(core, [run_id])}
        seen = {key: (cell["value"], cell["unit"], cell["verdict"],
                      tuple(sorted((claims[r]["source_ref"], claims[r]["value"])
                                   for r in cell["value_source_claim_refs"])))
                for key, cell in literature_cells(core, run_id).items()}
    expected = {
        ("attr_reported-oral-bioavailability-in-humans", "ALPHA"):
            (78.0, "% oral bioavailability", "pass", (("src_doi_10.0/A1", 78.0),)),
        ("attr_reported-oral-bioavailability-in-humans", "BETA"):
            (41.0, "% oral bioavailability", "pass", (("src_doi_10.0/B1", 41.0),)),
        ("attr_incidence-of-grade-3-or-higher-hypertension", "ALPHA"):
            (29.0, "% of patients", "pass", (("src_doi_10.0/A1", 29.0),)),
        ("attr_incidence-of-grade-3-or-higher-hypertension", "BETA"):
            (12.0, "% of patients", "pass", (("src_doi_10.0/B2", 12.0),)),
        ("attr_time-to-steady-state-on-repeated-oral-dosing", "ALPHA"):
            (7.0, "days", "pass", (("src_doi_10.0/A2", 7.0),)),
        ("attr_time-to-steady-state-on-repeated-oral-dosing", "BETA"):
            (14.0, "days", "pass", (("src_doi_10.0/B2", 14.0),))}
    assert seen == expected                   # the same at one worker and at four


# --- a verified quote is not a verified answer ----------------------------------------
# Measured on the same run. The cell `Incidence of any-grade proteinuria x surufatinib` came back
# 10.8 citing a span-verified quote reading "A higher proportion of patients in the surufatinib
# treatment cohort experienced proteinuria (9 [3.2%] vs. 10 [10.8%], P = 0.010)": 10.8% is the
# comparator arm and surufatinib's figure is 3.2%. The same cell cited a quote about hypertension
# at 38%, tagged to proteinuria. Both quotes are in their sources, which is all quote verification
# ever said.
#
# `reading.attribution_problem` is the guard. Replayed over that run's ledger it refuses 39 of the
# 253 admitted claims (48% of the 82 that carry a number): 27 for competing values in one span,
# 10 for an arm comparison, 2 for a subject belonging to another attribute. Of the 70 claims the
# old per-query harvest ever offered to a cell it refuses 11. Over the 52 cells, re-assessed from
# the ledger: 6 were value-bearing as the run assessed them, 16 from the union, 13 from the union
# with this guard -- and of the reference compound's 5 value-bearing cells, 4 keep a value, the
# proteinuria cell moves off the comparator's 10.8, and `Food effect on systemic exposure` loses
# its 1.25, which was the upper edge of a bioequivalence window and never a food effect at all.

ARM_SPAN = ("A higher proportion of patients in the surufatinib treatment cohort experienced "
            "proteinuria (9 [3.2%] vs. 10 [10.8%], P = 0.010)")
PROTEINURIA = "Incidence of any-grade proteinuria"
HYPERTENSION_ATTRIBUTE = "Incidence of grade 3 or higher hypertension"
ALPHA_ARM_QUOTE = ("A higher proportion of patients in the Alpha treatment cohort experienced "
                   "hypertension (9 [3.2%] vs. 10 [10.8%], P = 0.010)")


class ArmReader:
    """One paper whose only figure for the attribute is an arm comparison, as the real one was."""

    contract = PaperReader.contract

    def __init__(self):
        self.reads: list[str] = []

    def invoke(self, question_kind, inputs):
        paper = inputs["pmcid"].split("_", 1)[1]
        self.reads.append(paper)
        text = ALPHA_ARM_QUOTE + "." if paper == "P_shared" else "Alpha was well tolerated in this cohort."
        document = {"title": f"Alpha study {paper}", "access_state": "full_text_available",
                    "reading_depth": "full_text", "source_hit": {"is_preprint": False},
                    "passages": [{"passage_id": "title", "kind": "title", "section_path": [],
                                  "text": f"Alpha study {paper}"},
                                 {"passage_id": "sec1.p1", "kind": "paragraph", "section_path": ["Results"],
                                  "text": text}]}
        return ProviderResponse(values=[{"name": "document", "value": document, "value_kind": "curated"}])


def arm_reader_script(request):
    if "Alpha study P_shared" not in request.messages[0]["content"]:
        return {"claims": []}
    return {"claims": [{"passage_id": "sec1.p1", "quoted_span": ALPHA_ARM_QUOTE, "statement": ALPHA_ARM_QUOTE,
                        "determination_basis": "measured", "polarity": "supports", "value": 10.8,
                        "unit": "% of patients", "entities": ["Alpha"], "attribute_name": HYPERTENSION["name"]}]}


def arm_controller(core):
    broker = Broker(core, sleep=lambda s: None)
    search, reader = SplitSearch(), ArmReader()
    broker.register(FakeIdentity({"alpha": IDENTITIES["alpha"]}))
    broker.register(search)
    broker.register(reader)
    roster = ModelRoster({"s": ScriptedAdapter("s", arm_reader_script, model="scripted-reader")}, {"reader": "s"})
    return RunController(core, broker, roster, adapter=ADAPTER), search, reader


def test_a_number_from_the_comparator_arm_of_a_verified_quote_is_not_this_candidates_value():
    """The measured wrong answer. Both numbers in the span are proteinuria incidences, so naming
    the attribute distinguishes nothing; only the candidate's own name does, and the clause
    carrying 10.8 has not got it."""
    problem = reading.attribution_problem(
        {"quoted_span": ARM_SPAN, "value": 10.8}, labels=["Surufatinib", "sulfatinib"],
        attribute_name=PROTEINURIA, sibling_names=[HYPERTENSION_ATTRIBUTE], unit="% of patients")
    assert problem["rule"] == "arm_comparison"
    assert "does not name Surufatinib" in problem["note"]
    assert problem["clause"] == "10 [10.8%], p = 0.010)"
    # the same span's 3.2 is kept, because the clause carrying it is the one that names the
    # candidate: the span does tie that number to this compound, which is the whole test
    assert reading.attribution_problem({"quoted_span": ARM_SPAN, "value": 3.2}, labels=["Surufatinib"],
                                       attribute_name=PROTEINURIA, sibling_names=[HYPERTENSION_ATTRIBUTE],
                                       unit="% of patients") is None
    # and a comparison whose arms are named each way round keeps the candidate's side only
    either_way = "Proteinuria occurred in 3.2% of surufatinib patients vs 10.8% on placebo"
    assert reading.attribution_problem({"quoted_span": either_way, "value": 3.2}, labels=["Surufatinib"],
                                       attribute_name=PROTEINURIA, sibling_names=[HYPERTENSION_ATTRIBUTE],
                                       unit="% of patients") is None
    assert reading.attribution_problem({"quoted_span": either_way, "value": 10.8}, labels=["Surufatinib"],
                                       attribute_name=PROTEINURIA, sibling_names=[HYPERTENSION_ATTRIBUTE],
                                       unit="% of patients")["rule"] == "arm_comparison"


def test_a_figure_whose_subject_is_another_attribute_of_the_same_read_is_mis_tagged():
    """The other half of the measured failure: a hypertension figure tagged to proteinuria. The
    check needs the competing subject in the clause that carries the number, and never fires on a
    span that simply names no attribute -- the measured surufatinib bioavailability claim is 'the
    serum level of the original drug is about 40.3%', which is a real observation.

    The toxicity siblings here are three of the task's own, because what a subject *is* depends on
    the others in the read: `grade` is in all three names, so it distinguishes nothing and the
    hypertension attribute's subject is the one word `hypertension` -- which one mention is then
    enough to decide. A two-word subject takes two.
    """
    toxicities = [HYPERTENSION_ATTRIBUTE, "Incidence of grade 3 or higher haemorrhage",
                  "Incidence of grade 3 or higher hand-foot skin reaction"]
    assert reading.subject_terms(PROTEINURIA, toxicities)[1][HYPERTENSION_ATTRIBUTE] == ["hypertension"]
    mistagged = reading.attribution_problem(
        {"quoted_span": "Hypertension occurred in 38% of the treated patients", "value": 38.0},
        labels=["Surufatinib"], attribute_name=PROTEINURIA, sibling_names=toxicities, unit="% of patients")
    assert mistagged["rule"] == "attribute_subject_mismatch" and "hypertension" in mistagged["note"]
    assert reading.attribution_problem(
        {"quoted_span": "After oral administration of sulfatinib, the serum level of the original drug is "
                        "about 40.3%.", "value": 40.3},
        labels=["Surufatinib", "sulfatinib"], attribute_name="Reported oral bioavailability in humans",
        sibling_names=["Incidence of grade 3 or higher serum phosphate elevation",
                       "Measured change in a co-administered drug's exposure"],
        unit="% oral bioavailability") is None
    # a figure named by its own endpoint inside its own bracket survives a crowded sentence, and
    # the neighbouring endpoint's figure in the same sentence does not
    crowded = ("The most common AEs were hypertension (17, 19.1%), diarrhea (14, 15.7%), "
               "proteinuria (12, 13.5%), and hypothyroidism (5, 5.6%).")
    assert reading.attribution_problem({"quoted_span": crowded, "value": 13.5}, labels=["Surufatinib"],
                                       attribute_name=PROTEINURIA, sibling_names=toxicities,
                                       unit="% of patients") is None
    hypertension_figure = reading.attribution_problem({"quoted_span": crowded, "value": 19.1},
                                                      labels=["Surufatinib"], attribute_name=PROTEINURIA,
                                                      sibling_names=toxicities, unit="% of patients")
    assert hypertension_figure["rule"] == "competing_values"
    assert hypertension_figure["clause"] == "the most common aes were hypertension (17, 19.1%)"


def test_a_table_row_of_several_columns_says_which_numbers_it_holds_and_not_which_one_is_asked_for():
    """Where most of the refusals are. A pipe row carries one endpoint's figures for several
    columns -- grades, arms, cohorts -- and nothing in the row says which column was asked for."""
    row = "Hypertension | 13 (46.4) | 1 (3.6) | 13 (46.4) | 0"
    problem = reading.attribution_problem({"quoted_span": row, "value": 3.6}, labels=["Surufatinib"],
                                          attribute_name=HYPERTENSION_ATTRIBUTE,
                                          sibling_names=[PROTEINURIA], unit="% of patients")
    assert problem["rule"] == "competing_values" and problem["clause"] == "1 (3.6)"
    # one figure and one subject in the span is not a crowd, and is kept
    assert reading.attribution_problem(
        {"quoted_span": "Grade 3 or higher hypertension occurred in 46.4% of patients", "value": 46.4},
        labels=["Surufatinib"], attribute_name=HYPERTENSION_ATTRIBUTE, sibling_names=[PROTEINURIA],
        unit="% of patients") is None


def test_a_claim_the_attribution_guard_refuses_is_set_aside_with_its_reason_and_kept_in_the_ledger(core):
    """What the refusal does to the run. The claim is recorded, quarantined with
    `attribution_ambiguous` -- a registered reason, with the failing check and a sentence on the
    claim itself -- so it reaches the cell as a set-aside claim rather than being dropped, and the
    cell is `unknown_missing` rather than confidently wrong."""
    assert vocab.label("literature_admission_reason", "attribution_ambiguous") == \
        "the span does not tie this number to this candidate and this attribute"
    controller, _, reader = arm_controller(core)
    run_id = controller.start(split_task(core), by=OPERATOR)
    cells = literature_cells(core, run_id)
    cell = cells[("attr_incidence-of-grade-3-or-higher-hypertension", "ALPHA")]
    assert cell["verdict"] == "unknown_missing" and cell["value"] is None
    assert [entry["reason"] for entry in cell["set_aside_claims"]] == ["not_admitted"]
    quarantined = [c for c in ledger.claims(core, [run_id], admitted_only=False)
                   if c["admission_state"] == "quarantined"]
    assert len(quarantined) == 1
    claim = quarantined[0]
    assert claim["value"] == 10.8 and claim["location"]["span_checked_against_source"] is True
    assert set(claim["admission_reasons"]) == {"quote_verified", "value_in_quote",
                                               "candidate_named_in_quote", "attribution_ambiguous"}
    assert claim["attribution_check"]["rule"] == "arm_comparison"
    assert "does not name Alpha" in claim["attribution_check"]["note"]


# --- how many documents a value has to rest on ------------------------------------------------
# The measured state of the path after the two repairs above, on the real two-candidate run
# (`run_smoke_lit_1792002118`, 26 literature criteria x 2 candidates, re-assessed from the claim
# union with the attribution guard applied): 13 cells carry a value, 9 of them on a single document
# and 7 on a single claim. Quote verification says the words are in the source; it does not say the
# number answers the question, and the arm-comparison claim above is what a lone unrefused
# mis-extraction looks like. `evidence.min_source_documents` is the floor that makes a scored cell
# the agreement of two readings of two texts -- off by default, because on that run it would have
# kept 4 of the 13 cells and all 4 belonged to one of the two candidates.

def floor_claims(*sources: str) -> list[dict]:
    """One admitted hypertension claim per named source document."""
    return [{"claim_id": f"c{index}", "admission_state": "admitted", "evidence_kind": "peer_reviewed",
             "determination_basis": "measured", "value": 20.0 + index, "unit": HYPERTENSION["unit"],
             "source_ref": source, "location": {"quoted_span": f"hypertension in {source}"}}
            for index, source in enumerate(sources)]


def floor_cell(claims: list[dict], minimum: int, attribute: dict = HYPERTENSION) -> tuple[dict, dict]:
    return assessor.assess_cell(candidate={"candidate_id": "cand_alpha"},
                                attribute=dict(attribute, attribute_id="attr_x", version=1),
                                rule=dict(ORDERING, rule_id="rule_x", version=1), rule_set_ref="rules@v1",
                                claims=claims, resolved=True, searched=["literature_retrieval"],
                                min_source_documents=minimum)


def test_a_literature_cell_scores_on_one_document_unless_the_floor_is_raised_above_one():
    """The default changes nothing: one admitted claim from one paper still carries a value, which is
    what every run so far has scored on."""
    cell, reason = floor_cell(floor_claims("src_doi_10.0/A1"), 1)
    assert cell["verdict"] == "pass" and cell["value"] == 20.0 and cell["set_aside_claims"] == []
    assert "1 usable claim(s)" in reason["uncertainty_statement"]
    # two claims out of one paper are two claims and still one document
    cell, _ = floor_cell(floor_claims("src_doi_10.0/A1") + floor_claims("src_doi_10.0/A1")[:1], 1)
    assert cell["verdict"] == "pass"


def test_a_literature_cell_below_the_document_floor_is_unknown_with_its_claims_set_aside_and_named():
    """Below the floor the cell does not score, and says why. The claims are not hidden: each one is
    in `set_aside_claims` under its own reason, so the evidence stays readable and only the scoring
    is refused -- and the reason text may not say "no admitted claim", because claims were found."""
    claims = floor_claims("src_doi_10.0/A1", "src_doi_10.0/A1")
    cell, reason = floor_cell(claims, 2)
    assert cell["verdict"] == "unknown_missing" and cell["value"] is None
    assert cell["value_source_claim_refs"] == []
    assert [entry["reason"] for entry in cell["set_aside_claims"]] == \
        ["below_min_source_documents", "below_min_source_documents"]
    assert "2 usable claim(s) from 1 source document(s)" in reason["reason_text"]
    assert "at least 2 distinct documents" in reason["reason_text"]
    assert "no admitted claim" not in reason["reason_text"]
    assert "not scored" in reason["uncertainty_statement"]


def test_a_literature_cell_at_the_document_floor_scores_on_the_agreement_of_two_documents():
    """At the floor the value is the attribute's own aggregation over both documents' claims -- the
    floor decides whether a cell may be scored, it does not change how it is scored."""
    claims = floor_claims("src_doi_10.0/A1", "src_doi_10.0/B1")
    cell, _ = floor_cell(claims, 2)
    assert cell["verdict"] == "pass" and cell["value"] == 20.5      # the declared median of 20 and 21
    assert len(cell["value_source_claim_refs"]) == 2 and cell["set_aside_claims"] == []
    # and a conflict is a decision about a candidate too, so the floor is applied before any verdict
    threshold = {"rule_kind": "hard_exclusion", "cutoff": {"comparator": "<=", "value": 20.5,
                                                           "unit": HYPERTENSION["unit"]},
                 "cutoff_basis": "expert_set"}
    one_document = assessor.assess_cell(
        candidate={"candidate_id": "cand_alpha"}, attribute=dict(HYPERTENSION, attribute_id="attr_x", version=1,
                                                                 aggregation="consensus"),
        rule=dict(threshold, rule_id="rule_x", version=1), rule_set_ref="rules@v1",
        claims=floor_claims("src_doi_10.0/A1", "src_doi_10.0/A1"), resolved=True, min_source_documents=2)[0]
    assert one_document["verdict"] == "unknown_missing", "a one-document conflict is not a conflict found"


def test_the_document_floor_asks_nothing_of_a_criterion_that_reads_a_database():
    """A curated measurement comes from one database record by construction, and `evidence.gather`
    already pools every route an attribute declares, so a floor applied here would refuse
    single-source curated quantities rather than ask anyone for corroboration."""
    assert not criteria.is_literature_bound(MW)
    claims = [{"claim_id": "c0", "admission_state": "admitted", "evidence_kind": "database_entry",
               "determination_basis": "derived", "value": 300.0, "unit": "g/mol", "source_ref": "src_pubchem"}]
    cell, _ = floor_cell(claims, 2, attribute=MW)
    assert cell["verdict"] == "pass" and cell["value"] == 300.0


def test_the_sweep_hands_every_literature_cell_the_configured_document_floor(core):
    """Through the seam a run goes through, not past it: the floor is read off the bound settings by
    its dotted key, and `.get(key, 1)` cannot report a key that does not match the one
    `config.SETTINGS` registers -- it can only quietly default to the old behaviour.

    Every paper in this fixture reports each attribute once, so at a floor of two no cell scores:
    the six values the default run carries are exactly the six single-document values this refuses.
    """
    from mas.core import config as config_mod

    assert config_mod.SETTINGS["evidence.min_source_documents"].default == 1
    settings = config_mod.resolve(project_file=None, environ={},
                                  # the fake search tool answers for every source, as it does when a run
                                  # binds no settings at all; only the floor is under test here
                                  overrides={"evidence.min_source_documents": 2, "search.sources": [],
                                             "evaluation.mode": "full", "qualification.policy": "legacy",
                                             "evidence.mode": "retrieve"})
    assert ("const_evidence_min_source_documents", 2, "documents") in settings.registered_constants()
    controller, _, reader = make_controller(core, ReaderModel())
    run_id = controller.start(setup_task(core), by=OPERATOR, sweep_seed=3, settings=settings)
    assert controller.current_state(run_id) == "completed"
    assert sorted(reader.reads) == ["A1", "A2", "B1", "B2"], "the reading is unchanged; the scoring is not"
    cells = literature_cells(core, run_id)
    assert {cell["verdict"] for cell in cells.values()} == {"unknown_missing"}
    assert {entry["reason"] for cell in cells.values() for entry in cell["set_aside_claims"]} == \
        {"below_min_source_documents"}
    assert len(ledger.claims(core, [run_id])) == 6, "the evidence is in the ledger, it is just not scored on"


# --- a molar concentration answering a pChEMBL attribute ------------------------------------
# The defect this closes, measured on the live registry of 14 October 2026: of the 26
# literature-bound criteria not one is a potency, although a published kinase selectivity table is
# exactly where multi-target potency is reported -- because such a table prints "IC50 = 0.004 uM"
# and every potency attribute declares `pChEMBL`, so each of those claims was admitted to the
# ledger and then set aside `unit_unresolved` (the test above pins that behaviour for a pair nothing
# converts, and it is unchanged). The curated databases cover 74 of the 3,177 candidates at the five
# required receptors; for the rest the literature is the only route.
#
# The reference values are the reference compound's own selectivity table, PMC5522050 Table 1
# (CC BY). Two of them are independent evidence that the conversion is the right one: VEGFR3 and
# FGFR1 reproduce that receptor's ChEMBL curated median (9.00, 7.82) to the decimal.
PMC5522050_TABLE_1 = {"VEGFR3": (0.001, 9.000), "FGFR1": (0.015, 7.824), "CSF1R": (0.004, 8.398),
                      "VEGFR1": (0.002, 8.699), "VEGFR2": (0.024, 7.620)}

POTENCY = {"name": "CSF1R curated potency", "definition": "Median pChEMBL value against CSF1R",
           "measurement_kind": "quantitative", "unit": "pChEMBL", "direction": "higher_better",
           "aggregation": "median", "acceptable_value_sources": ["curated_measurement", "peer_reviewed"],
           "evidence_requests": [
               {"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values",
                "identifier_scheme": "ik", "parameters": {"target_chembl_id": "CHEMBL1844"}},
               {"capability": "literature_retrieval", "question_kind": "search",
                "parameters": {"query_template": '({names}) AND "CSF1R" AND (IC50 OR Ki)',
                               "relevance_terms": ["CSF1R", "IC50"], "search_limit": 10}}]}


def potency_claim(value, unit, claim_id="c1", **extra):
    return {"claim_id": claim_id, "admission_state": "admitted", "evidence_kind": "peer_reviewed",
            "determination_basis": "measured", "value": value, "unit": unit, "unit_as_reported": unit,
            "source_ref": "src_doi_10.1038/PMC5522050",
            "location": {"location_kind": "table", "quoted_span": f"IC50 = {value} {unit}"}, **extra}


def test_a_molar_ic50_from_a_table_answers_a_pchembl_attribute_to_the_decimal():
    """`pChEMBL = -log10(concentration in mol/L)`, which is how ChEMBL computes its own
    `pchembl_value`: a documented identity, not a modelling choice. Checked against the five rows of
    the published table, and against the spellings of a micromolar and a nanomolar concentration
    that `UNIT_SYNONYMS` already folds."""
    for receptor, (micromolar, expected) in PMC5522050_TABLE_1.items():
        usable, set_aside = assessor.usable_claims([potency_claim(micromolar, "uM")], POTENCY)
        assert set_aside == [] and round(usable[0]["value"], 3) == expected, receptor
    # the same concentration, every unit and spelling the table could have printed it in
    for value, unit in ((0.004, "uM"), (0.004, "µM"), (0.004, "μM"), (0.004, "umol/L"),
                        (4.0, "nM"), (4.0, "nmol/l"), (4000.0, "pM"), (4e-6, "mM"), (4e-9, "M")):
        usable, _ = assessor.usable_claims([potency_claim(value, unit)], POTENCY)
        assert round(usable[0]["value"], 3) == 8.398, unit
    assert assessor.unit_conversion("nM", "pChEMBL")["identity"] == "pChEMBL = -log10(concentration in mol/L)"


def test_the_converted_claim_keeps_what_the_source_said_and_the_stored_claim_is_untouched():
    """The cell's value is on the attribute's scale and the record of how it got there travels with
    it, so a reader can check the arithmetic against the quote. The claim the ledger holds still says
    what the paper said: `usable_claims` returns copies and mutates nothing."""
    original = potency_claim(0.004, "uM")
    before = dict(original)
    usable, _ = assessor.usable_claims([original], POTENCY)
    converted = usable[0]["unit_conversion"]
    assert original == before, "the stored claim is not rewritten"
    assert (converted["value_as_reported"], converted["unit_as_reported"]) == (0.004, "uM")
    assert (converted["from_unit"], converted["to_unit"]) == ("uM", "pChEMBL")
    assert usable[0]["unit"] == "pChEMBL" and usable[0]["claim_id"] == original["claim_id"]
    # and the cell says so where a person reads it
    _, reason = assessor.assess_cell(candidate={"candidate_id": "ALPHA"}, attribute=dict(POTENCY, attribute_id="attr_p", version=1),
                                     rule=dict(ORDERING, rule_id="rule_p", version=1), rule_set_ref="rules@v1",
                                     claims=[potency_claim(0.004, "uM")], resolved=True)
    assert reason["unit_conversions"][0]["value_as_reported"] == 0.004
    assert "converted to pChEMBL (pChEMBL = -log10(concentration in mol/L))" in reason["uncertainty_statement"]


def test_a_concentration_of_zero_or_less_is_refused_by_name_rather_than_scored():
    """A non-positive concentration has no logarithm. Refused with a registered reason: returning
    `inf` would score the candidate at infinite potency, and raising would end a sweep over one
    reader's bad number."""
    for value in (0.0, -0.004):
        usable, set_aside = assessor.usable_claims([potency_claim(value, "uM")], POTENCY)
        assert usable == [] and set_aside[0]["set_aside_reason"] == "non_positive_concentration"
    assert "non_positive_concentration" in assessor.SET_ASIDE_REASONS


def test_only_a_commensurable_pair_converts_and_everything_else_stays_unit_unresolved():
    """The permitted conversions are an explicit table, so a pair nobody registered refuses rather
    than guesses: a percentage is not a duration, and the identity runs one way -- a pChEMBL value
    carries no concentration unit to go back to."""
    hours = dict(POTENCY, unit="h", name="Time to steady state")
    usable, set_aside = assessor.usable_claims([potency_claim(29.0, "%")], hours)
    assert usable == [] and set_aside[0]["set_aside_reason"] == "unit_unresolved"
    assert assessor.unit_conversion("%", "h") is None
    nanomolar = dict(POTENCY, unit="nM")
    usable, set_aside = assessor.usable_claims([potency_claim(8.4, "pChEMBL")], nanomolar)
    assert usable == [] and set_aside[0]["set_aside_reason"] == "unit_unresolved"
    assert assessor.unit_conversion("pChEMBL", "nM") is None
    # 'nm' is nanometres and 'm' is metres: an unrecognized spelling converts nothing
    for unit in ("nm", "m", "mol"):
        assert assessor.unit_conversion(unit, "pChEMBL") is None


def test_a_reported_range_converts_both_ends_and_keeps_low_below_high():
    """A decreasing conversion reverses the ends of a range: 1-10 nM is pChEMBL 8-9, not 9-8. Both
    ends reach the cell, which is what makes a range straddling a cutoff a conflict and not a pass."""
    usable, _ = assessor.usable_claims(
        [potency_claim(None, "nM", value_low=1.0, value_high=10.0)], POTENCY)
    assert (round(usable[0]["value_low"], 3), round(usable[0]["value_high"], 3)) == (8.0, 9.0)


def test_a_curated_record_and_a_read_table_pool_into_one_median_on_the_attributes_scale():
    """What the conversion is for: one quantity, two curations and a published selectivity table,
    reduced by the `median` the attribute already declared. The curated record arrives on the
    pChEMBL scale and the paper's row arrives in micromolar, and the cell is one number."""
    attribute = dict(POTENCY, attribute_id="attr_csf1r", version=1)
    curated = {"claim_id": "c_db", "admission_state": "admitted", "evidence_kind": "curated_measurement",
               "determination_basis": "measured", "value": 9.0, "unit": "pChEMBL", "source_ref": "src_db_chembl",
               "location": {"location_kind": "record_field", "quoted_span": "9.0"}}
    cell, _ = assessor.assess_cell(candidate={"candidate_id": "ALPHA"}, attribute=attribute,
                                   rule=dict(ORDERING, rule_id="rule_csf1r", version=1), rule_set_ref="rules@v1",
                                   claims=[curated, potency_claim(0.004, "uM", claim_id="c_lit")], resolved=True)
    assert cell["verdict"] == "pass" and round(cell["value"], 3) == round((9.0 + 8.398) / 2, 3)
    assert cell["unit"] == "pChEMBL" and sorted(cell["value_source_claim_refs"]) == ["c_db", "c_lit"]


# --- deferral is per route, not per rule --------------------------------------------------------
#
# The mandated receptor potency is one quantity read from three routes: ChEMBL, IUPHAR/BPS and a
# published selectivity table. Until 15 October 2026 `confirm_rule_set` held the whole rule out of
# the set if *any* of its routes named a deferred capability, so a sweep confirmed with
# `--defer-capability literature_retrieval` -- which is every full-universe run, because one
# document read per compound is out of reach at 3,177 -- scored the task's own quantity nowhere,
# not even on the two curations that need no reading. Everything computed from those cells went
# with it: the mandated-coverage floor and the calibration guard's reference population.

POTENCY_THREE_ROUTES = dict(
    POTENCY, name="CSF1R potency, curated and reported",
    evidence_requests=[
        {"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values",
         "identifier_scheme": "ik", "parameters": {"target_chembl_id": "CHEMBL1844"}},
        {"capability": "interaction_evidence_lookup", "question_kind": "gtopdb_affinity",
         "identifier_scheme": "ik", "parameters": {"target_chembl_id": "CHEMBL1844"}},
        {"capability": "literature_retrieval", "question_kind": "search",
         "parameters": {"query_template": '({names}) AND "CSF1R" AND (IC50 OR Ki)',
                        "relevance_terms": ["CSF1R", "IC50"], "search_limit": 10}}])

CURATED_POTENCY = {("ALPHA", "pchembl_values"): 9.0, ("ALPHA", "gtopdb_affinity"): 8.6,
                   ("BETA", "pchembl_values"): 7.0}


class FakeCuration:
    """Two independent curations of one quantity, behind one capability, as the real pair is."""

    contract = ToolContract(
        tool_id="tool_fake_curation", capability="interaction_evidence_lookup",
        capability_kind="relationship_evidence_lookup",
        question_kinds=("pchembl_values", "gtopdb_affinity"), contract_version="1",
        implementation_version="fake-1", purpose_statement="test curated potency",
        evidence_kind_produced="curated_measurement", claim_strength_ceiling="measured",
        identity_inputs=("identifier",))

    def __init__(self):
        self.asked: list[tuple[str, str]] = []

    def invoke(self, question_kind, inputs):
        self.asked.append((inputs["identifier"], question_kind))
        value = CURATED_POTENCY.get((inputs["identifier"], question_kind))
        if value is None:
            return ProviderResponse(values=[], data_version="fake")
        return ProviderResponse(
            values=[{"name": question_kind, "value": value, "unit": "pChEMBL", "value_kind": "measured",
                     "source_record_ref": f"fake:{inputs['identifier']}:{question_kind}"}],
            data_version="fake", upstream_refs=[f"fake:{inputs['identifier']}"])


def three_route_task(core) -> str:
    """One three-route potency rule, one literature-only rule and one database-only rule, with
    `literature_retrieval` held out of the run."""
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    criteria.propose(core, task_id, MW, MW_RULE, by=OPERATOR)
    criteria.propose(core, task_id, POTENCY_THREE_ROUTES, dict(ORDERING), by=OPERATOR)
    criteria.propose(core, task_id, BIOAVAILABILITY, dict(ORDERING), by=OPERATOR)
    for item in review.items(core, [task_id]).values():
        review.decide(core, item, decision="approve", actor=EXPERT, reason_text="", entry="interactive",
                      historical_list_exposure="not_exposed")
    criteria.confirm_rule_set(core, task_id, by=OPERATOR, coverage_floor=0.5,
                              defer_capabilities=("literature_retrieval",),
                              defer_reason="full-universe screen; the literature runs on a shortlist")
    return task_id


POTENCY_RULE_REF = "rule_csf1r-potency-curated-and-reported@v1"
LITERATURE_ONLY_RULE_REF = "rule_reported-oral-bioavailability-in-humans@v1"


def test_a_three_route_rule_enters_the_set_with_only_its_literature_route_held_out(core):
    """The repair. The rule scores on the two curations and its entry says so: `scoring_routes` are
    what the values may come from and `deferred_routes` are what this run did not ask, so a reader
    of a cell can tell a database-only value from one that also used a reading."""
    rule_set = criteria.rule_set(core, three_route_task(core))
    entry = next(e for e in rule_set["entries"] if e["rule_ref"] == POTENCY_RULE_REF)
    assert [(r["capability"], r["question_kind"]) for r in entry["scoring_routes"]] == [
        ("interaction_evidence_lookup", "pchembl_values"),
        ("interaction_evidence_lookup", "gtopdb_affinity")]
    assert entry["deferred_routes"] == [{"capability": "literature_retrieval", "question_kind": "search"}]
    assert criteria.entry_deferred_capabilities(entry) == ("literature_retrieval",)
    # and a row still appears in `deferred[]`, marked as route-level: that list is what `sr_stage`
    # and the export read the deferral off, and a rule missing from it would be silently un-deferred
    row = next(d for d in rule_set["deferred"] if d["rule_ref"] == POTENCY_RULE_REF)
    assert criteria.deferral_scope(row) == "route" and row["capabilities"] == ["literature_retrieval"]
    assert row["scores_on"] == ["interaction_evidence_lookup", "interaction_evidence_lookup"]
    # the rule whose *only* route is deferred still leaves the set whole, which is the unchanged half
    whole = next(d for d in rule_set["deferred"] if d["rule_ref"] == LITERATURE_ONLY_RULE_REF)
    assert criteria.deferral_scope(whole) == "rule" and whole["scores_on"] == []
    assert LITERATURE_ONLY_RULE_REF not in [e["rule_ref"] for e in rule_set["entries"]]
    # an entry with nothing held out says so with an empty list rather than with a missing field
    database_only = next(e for e in rule_set["entries"] if e["rule_ref"] == "rule_molecular-weight@v1")
    assert database_only["deferred_routes"] == [] and len(database_only["scoring_routes"]) == 1


def test_a_re_confirmation_does_not_un_defer_a_route_level_deferral(core):
    """`sr_stage._install` re-confirms the set when it installs a fitted ordering method, with the
    deferral read back off the record. The capability has to survive that round trip: a set that
    re-confirmed without it would ask, in the set that now decides the ranking, for reading the run
    had decided not to buy. Read through `criteria.deferred_capabilities`, which prefers the
    recorded policy to the rows -- the rows of a route-level deferral belong to rules that entered,
    so a rule held out for some other reason would drop its capability from the rebuilt set."""
    task_id = three_route_task(core)
    first = criteria.rule_set(core, task_id)
    assert criteria.deferred_capabilities(first) == ("literature_retrieval",)
    again = criteria.rule_set(core, task_id, criteria.confirm_rule_set(
        core, task_id, by=OPERATOR, coverage_floor=0.5,
        defer_capabilities=criteria.deferred_capabilities(first),
        defer_reason=criteria.deferral_reason(first)))
    entry = next(e for e in again["entries"] if e["rule_ref"] == POTENCY_RULE_REF)
    assert criteria.entry_deferred_capabilities(entry) == ("literature_retrieval",)
    assert LITERATURE_ONLY_RULE_REF not in [e["rule_ref"] for e in again["entries"]]
    # an older record carries no policy field at all, and the rows are all it has; a rule-level row
    # must still rebuild the capability from them
    legacy = {"deferred": [{"rule_ref": LITERATURE_ONLY_RULE_REF, "capability": "literature_retrieval",
                            "reason": "held out"}]}
    assert criteria.deferred_capabilities(legacy) == ("literature_retrieval",)
    assert criteria.deferral_scope(legacy["deferred"][0]) == "rule"


def test_the_sweep_asks_the_curated_routes_of_a_rule_whose_reading_is_held_out(core):
    """What the deferral is for, through the controller: the curated routes are called for every
    candidate and the cell carries their median, while the search tool, the reader and the model are
    never touched. Before this, the rule was not in the set at all and the quantity the task is
    about was measured on nobody."""
    model = ReaderModel()
    controller, search, reader = make_controller(core, model)
    curation = FakeCuration()
    controller.broker.register(curation)
    run_id = controller.start(three_route_task(core), by=OPERATOR, sweep_seed=3)
    assert controller.current_state(run_id) == "completed"
    assert sorted(curation.asked) == [("ALPHA", "gtopdb_affinity"), ("ALPHA", "pchembl_values"),
                                      ("BETA", "gtopdb_affinity"), ("BETA", "pchembl_values")]
    assert search.queries == [] and reader.reads == [] and model.calls == []
    cells = {event.payload["candidate_ref"].split("-")[-1]: core.artifacts.payload(event.payload["artifact_id"])
             for event in core.journal.replay(run_id)
             if event.event_type == "candidate.assessed"
             and event.payload["attribute_ref"].startswith("attr_csf1r")}
    assert cells["ALPHA"]["value"] == pytest.approx((9.0 + 8.6) / 2) and cells["ALPHA"]["verdict"] == "pass"
    assert cells["BETA"]["value"] == pytest.approx(7.0), "one curation answering is still an answer"
    assert {c["determination_basis"] for c in cells.values()} == {"measured"}
    assert [len(cells[c]["value_source_claim_refs"]) for c in ("ALPHA", "BETA")] == [2, 1]
