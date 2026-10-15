import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from mas.core import assessor, identity, ledger, vocab
from mas.core.assessor import usable_claims
from mas.core.broker import Broker, ProviderResponse, ToolContract, ToolError, ToolResult
from mas.core.budget import Budget
from mas.core.evidence import BudgetBlocked, LiteratureCache, claims_from_tool_result, gather
from mas.core.journal import actor
from mas.core.models import ModelRoster, ScriptedAdapter
from mas.core.runtime import Core
from tests.fakes import AbsentProvider, FakeIdentity, FakeProperty

WHO = actor("agent", "retriever-1", "evidence_retriever")


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c


def hit(key, label):
    return {"preferred_label": label, "identifiers": [{"scheme": "ik", "value": key}], "link_basis": "name_match_single_candidate"}


def test_broker_retries_retryable_errors_then_succeeds(core):
    prop = FakeProperty({("K1", "MW"): 300.0}, failures={"K1": ["transient_network", "rate_limited"]})
    delays = []
    broker = Broker(core, sleep=delays.append)
    broker.register(prop)
    result = broker.call("run_x", "property_estimate", "computed_property", {"identifier": "K1", "property": "MW"},
                         requesting_actor=WHO)
    assert result.outcome == "ok" and result.values[0]["value"] == 300.0
    assert prop.calls == 3 and len(delays) == 2
    kinds = [e.event_type for e in core.journal.replay("run_x")]
    assert kinds == ["tool.requested", "tool.retry_scheduled", "tool.retry_scheduled", "tool.returned"]
    assert result.provenance["executed_on"]["platform"] == "linux"


def test_broker_distinguishes_failed_empty_and_not_attempted(core):
    broker = Broker(core, sleep=lambda s: None)
    broker.register(FakeProperty({}, failures={"K2": ["parse_failed"]}))
    broker.register(AbsentProvider())
    failed = broker.call("run_x", "property_estimate", "computed_property", {"identifier": "K2", "property": "MW"},
                         requesting_actor=WHO)
    empty = broker.call("run_x", "property_estimate", "computed_property", {"identifier": "K3", "property": "MW"},
                        requesting_actor=WHO)
    no_identity = broker.call("run_x", "property_estimate", "computed_property", {"identifier": "", "property": "MW"},
                              requesting_actor=WHO)
    absent = broker.call("run_x", "interaction_estimate", "estimate", {}, requesting_actor=WHO)
    unknown_capability = broker.call("run_x", "literature_retrieval", "search", {}, requesting_actor=WHO)
    assert failed.outcome == "failed" and failed.error["class"] == "parse_failed"
    assert empty.outcome == "empty"
    assert (no_identity.outcome, no_identity.absence_reason) == ("not_attempted", "identity_unresolved")
    assert (absent.outcome, absent.absence_reason) == ("not_attempted", "not_installed")
    assert (unknown_capability.outcome, unknown_capability.absence_reason) == ("not_attempted", "not_configured")


def test_broker_refuses_tools_not_supported_on_the_host_platform(core):
    broker = Broker(core, platform="windows")
    prop = FakeProperty({("K1", "MW"): 1.0})
    prop.contract = type(prop.contract)(**{**prop.contract.__dict__, "supported_platforms": (("linux", "checked"),)})
    broker.register(prop)
    result = broker.call("run_x", "property_estimate", "computed_property", {"identifier": "K1", "property": "MW"},
                         requesting_actor=WHO)
    assert (result.outcome, result.absence_reason) == ("not_attempted", "requires_other_environment")


def test_identity_resolution_records_link_basis_and_queues_ambiguity(core):
    broker = Broker(core)
    broker.register(FakeIdentity({"alpha": [hit("AAA", "Alpha")],
                                  "beta": [hit("B1", "Beta 1"), hit("B2", "Beta 2")]}))
    records = identity.resolve_universe(core, broker, "run_x", ["alpha", "beta", "gamma"], primary_scheme="ik",
                                        capability="identity_resolution")
    by_label = {r["input_label"]: r for r in records}
    assert by_label["alpha"]["candidate_id"] == "cand_ik-AAA" and identity.is_resolved(by_label["alpha"])
    assert by_label["beta"]["identity_link_basis"] == "name_match_ambiguous"
    assert by_label["gamma"]["identity_link_basis"] == "unresolved"
    queued = [e for e in core.journal.replay("run_x") if e.event_type == "human.review_requested"]
    assert len(queued) == 1 and queued[0].payload["subject"]["kind"] == "identity_merge"


def test_claims_need_locations_and_snapshots_freeze_admitted_claims(core):
    source = ledger.put_source(core, {"identifiers": [{"scheme": "db_fake", "value": "K1"}],
                                      "source_status": "database_entry", "access_state": "metadata_only"})
    with pytest.raises(ValueError):
        ledger.record_claim(core, "run_x", {"source_ref": source}, by=WHO, admission_state="admitted", admission_reasons=[])
    claim = {"source_ref": source, "candidate_ref": "cand_ik-K1", "attribute_ref": "attr_mw@v1",
             "location": {"location_kind": "record_field", "locator_value": "MW", "quoted_span": "300.0",
                          "span_checked_against_source": True},
             "normalized_statement": "MW of K1 is 300 g/mol", "value": 300.0, "unit": "g/mol",
             "determination_basis": "derived", "evidence_kind": "database_entry"}
    admitted = ledger.record_claim(core, "run_x", claim, by=WHO, admission_state="admitted",
                                   admission_reasons=["identifier_match", "provenance_complete"])
    ledger.record_claim(core, "run_x", dict(claim, value=999.0), by=WHO, admission_state="quarantined",
                        admission_reasons=["unit_unresolved"])
    found = ledger.claims(core, ["run_x"], candidate_ref="cand_ik-K1", attribute_ref="attr_mw@v1")
    assert [c["claim_id"] for c in found] == [admitted]
    snapshot = ledger.freeze_snapshot(core, "run_x", task_id="task_t", claim_ids=[admitted], cutoff_at="2026-10-13",
                                      tool_manifest=[], by=WHO)
    assert snapshot == "evs_task_t_1"


# --- what a tool returns is recorded with the basis the tool declares ---------------------

MECHANISM_VALUE = {"name": "target_engagement", "value": True, "unit": None, "value_kind": "curated",
                   "determination_basis": "curated", "source_record_ref": "chembl_mechanism_304",
                   "conditions": {"action_type": "INHIBITOR"}}
POTENCY_VALUE = {"name": "pchembl_value", "value": 7.5, "unit": "pChEMBL", "value_kind": "curated",
                 "source_record_ref": "chembl_activity_909963", "conditions": {"standard_type": "IC50"}}
ENGAGEMENT_ATTRIBUTE = {"attribute_id": "attr_engagement", "version": 1, "name": "ABL1 engagement on record",
                        "measurement_kind": "categorical", "unit": None,
                        "acceptable_value_sources": ["database_entry"]}


def tool_result(values, tool_id="tool_drug_chembl_mechanism"):
    return ToolResult(result_id="tres_1", invocation={"tool_id": tool_id}, outcome="ok", values=values, records=[],
                      provenance={"tool_id": tool_id, "invocation_id": "inv_1", "license_id": "CC BY-SA 3.0 (ChEMBL)",
                                  "data_version": "chembl", "upstream_ref": ["chembl:mechanism:CHEMBL941:CHEMBL1862"]})


def db_claims(core, values, tool_id="tool_drug_chembl_mechanism"):
    return claims_from_tool_result(core, "run_x", tool_result(values, tool_id), candidate={"candidate_id": "cand_ik-K1"},
                                   attribute_ref="attr_engagement@v1", evidence_kind="database_entry",
                                   link_basis="exact_identifier_match")


def test_a_tool_declared_basis_is_kept_and_an_undeclared_one_falls_back_to_the_value_kind(core):
    claims = db_claims(core, [MECHANISM_VALUE, POTENCY_VALUE])
    # the mechanism row is a curated assertion and says so; a curated potency record is a
    # measurement a curator carried over, and still maps to `measured` through DB_BASIS
    assert [c["determination_basis"] for c in claims] == ["curated", "measured"]
    assert all(c["admission_state"] == "admitted" for c in claims)


def test_an_attribute_that_does_not_accept_curated_claims_gets_no_evidence(core):
    claims = db_claims(core, [MECHANISM_VALUE])
    # fails closed: an attribute that forgets acceptable_determination_bases ["curated"] sees
    # nothing, rather than counting a categorical assertion as a measurement
    usable, set_aside = usable_claims(claims, ENGAGEMENT_ATTRIBUTE)
    assert usable == [] and [c["set_aside_reason"] for c in set_aside] == ["determination_basis_not_accepted"]
    declared = dict(ENGAGEMENT_ATTRIBUTE, acceptable_determination_bases=["curated"])
    usable, set_aside = usable_claims(claims, declared)
    assert [c["claim_id"] for c in usable] == [claims[0]["claim_id"]] and set_aside == []


def test_an_unregistered_determination_basis_is_refused(core):
    # The example used to be "asserted", which is now registered: the reader had always been
    # offering it in its extraction enum while the registry had no word for it, so 60 of the
    # manuscript task's 127 criterion-support claims carried a basis no attribute could accept.
    # The invariant this test protects is unchanged -- a basis the registry does not know is refused.
    with pytest.raises(vocab.VocabularyViolation):
        db_claims(core, [dict(MECHANISM_VALUE, determination_basis="eyeballed")])


# The mechanism catalog entry instructs a proposer to write acceptable_determination_bases
# ["curated"]; the registry has to accept that attribute, or the entry is unusable end to end.
CURATED_ATTRIBUTE = dict(ENGAGEMENT_ATTRIBUTE, definition="Whether engagement with ABL1 is on curated record",
                         direction="non_directional", aggregation="consensus",
                         evidence_request={"capability": "interaction_evidence_lookup",
                                           "question_kind": "mechanism_records", "identifier_scheme": "inchikey",
                                           "parameters": {"target_chembl_id": "CHEMBL1862"}})


def test_an_attribute_may_declare_the_curated_basis_and_mechanism_claims_then_become_usable(core):
    from mas.core import assessor, criteria
    from mas.adapters.drug.registration import EVIDENCE_CATALOG
    entry = next(e for e in EVIDENCE_CATALOG if e["question_kind"] == "mechanism_records")
    assert entry["determination_basis"] in criteria.DETERMINATION_BASES    # the catalog names a registered basis
    declared = dict(CURATED_ATTRIBUTE, acceptable_determination_bases=[entry["determination_basis"]])
    criteria.check_attribute(declared)                                     # the instructed attribute is accepted
    criteria.propose(core, "task_curated", declared, {"rule_kind": "preference", "predicate_form": "categorical_membership",
                                                      "cutoff": {"comparator": "==", "value": True, "unit": None},
                                                      "cutoff_basis": "source_stated_value"}, by=WHO)
    claims = db_claims(core, [MECHANISM_VALUE])
    usable, set_aside = usable_claims(claims, declared)
    assert [c["claim_id"] for c in usable] == [claims[0]["claim_id"]] and set_aside == []
    # and the default still fails closed: an attribute that does not declare it sees no evidence
    assert "curated" not in assessor.DEFAULT_DETERMINATION_BASES
    criteria.check_attribute(CURATED_ATTRIBUTE)
    usable, set_aside = usable_claims(claims, CURATED_ATTRIBUTE)
    assert usable == [] and [c["set_aside_reason"] for c in set_aside] == ["determination_basis_not_accepted"]


# --- one quantity, two curations: an attribute may declare a route to each -----------------

CSF1R_ROUTES = [{"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values",
                 "identifier_scheme": "chembl_id", "parameters": {"target_chembl_id": "CHEMBL1844"}},
                {"capability": "interaction_evidence_lookup", "question_kind": "gtopdb_affinity",
                 "identifier_scheme": "chembl_id", "parameters": {"target_chembl_id": "CHEMBL1844"}}]
POOLED_POTENCY = {"attribute_id": "attr_csf1r-curated-potency", "version": 1, "name": "CSF1R curated potency",
                  "definition": "Median pChEMBL value over curated point measurements against CSF1R (CHEMBL1844), "
                                "from every curation that reports one",
                  "measurement_kind": "quantitative", "unit": "pChEMBL", "direction": "higher_better",
                  "aggregation": "median", "acceptable_value_sources": ["curated_measurement"],
                  "evidence_requests": CSF1R_ROUTES}
ORDERING = {"rule_id": "rule_csf1r-curated-potency", "version": 1, "rule_kind": "preference",
            "predicate_form": "ordering", "cutoff": None, "cutoff_basis": "none_evidence_insufficient"}
CANDIDATE = {"candidate_id": "cand_ik-K1", "label": "Alphatinib"}
RESOLVED = {"candidate_id": "cand_ik-K1", "identifiers": [{"scheme": "chembl_id", "value": "CHEMBL1"}],
            "identity_link_basis": "exact_identifier_match", "preferred_label": "Alphatinib", "aliases": []}


class Curation:
    """One curated-affinity source. The two real ones answer different question kinds under the same
    capability, which is exactly why the question kind cannot stand for the quantity."""

    def __init__(self, question_kind: str, tool_id: str, values: list[float], *, fail: bool = False):
        self.contract = ToolContract(
            tool_id=tool_id, capability="interaction_evidence_lookup", capability_kind="relationship_evidence_lookup",
            question_kinds=(question_kind,), contract_version="1", implementation_version="fake-1",
            purpose_statement="curated affinity against one target", evidence_kind_produced="curated_measurement",
            claim_strength_ceiling="measured", identity_inputs=("identifier",))
        self.values, self.fail, self.calls = values, fail, []

    def invoke(self, question_kind, inputs):
        self.calls.append(inputs["target_chembl_id"])
        if self.fail:
            raise ToolError("parse_failed", "scripted failure")
        return ProviderResponse(
            values=[{"name": "pchembl_value", "value": value, "unit": "pChEMBL", "value_kind": "curated",
                     "source_record_ref": f"{self.contract.tool_id}:{index}"} for index, value in enumerate(self.values)],
            data_version="fake", upstream_refs=[self.contract.tool_id])


def test_an_attribute_with_a_route_to_each_curation_gathers_from_both_and_is_aggregated_once(core):
    """The registry held two attributes per receptor -- the same measurement from two databases, so the
    receptor was scored twice and the coverage denominator counted a quantity that does not exist. One
    attribute with two routes gathers the union and `assess_cell` aggregates it under the declared
    median, with no change to the assessor: it already aggregates all of an attribute's claims."""
    broker = Broker(core)
    chembl, gtopdb = Curation("pchembl_values", "tool_chembl", [7.0, 7.4]), Curation("gtopdb_affinity", "tool_gtopdb", [9.0])
    broker.register(chembl)
    broker.register(gtopdb)
    claims, error_ref, searched = gather(core, broker, None, "run_x", candidate=CANDIDATE, identity=RESOLVED,
                                         attribute=POOLED_POTENCY, objective_text="rank by potency", cutoff_date=None)
    assert chembl.calls == gtopdb.calls == ["CHEMBL1844"]          # each route asked its own source
    assert error_ref is None and searched == ["interaction_evidence_lookup"]
    assert sorted(c["value"] for c in claims) == [7.0, 7.4, 9.0]   # the union, each claim on the attribute
    assert {c["attribute_ref"] for c in claims} == {"attr_csf1r-curated-potency@v1"}

    cell, reason = assessor.assess_cell(candidate=CANDIDATE, attribute=POOLED_POTENCY, rule=ORDERING,
                                        rule_set_ref="rules@v1", claims=claims, resolved=True, searched=searched)
    assert cell["verdict"] == "pass" and cell["value"] == 7.4      # one median over both curations, not two cells
    assert len(cell["value_source_claim_refs"]) == 3 and cell["set_aside_claims"] == []
    assert "3 usable claim(s); aggregation median" in reason["uncertainty_statement"]


def test_a_route_that_errors_does_not_discard_what_the_other_route_returned(core):
    """A cell scored on nothing because one of two sources was down would be a silent downgrade of the
    evidence; a cell scored silently on one of two declared sources would be worse. The claims that
    arrived are kept and the failing call's result id rides along as the cell's tool error."""
    broker = Broker(core, sleep=lambda s: None)
    broker.register(Curation("pchembl_values", "tool_chembl", [], fail=True))
    broker.register(Curation("gtopdb_affinity", "tool_gtopdb", [9.0]))
    claims, error_ref, searched = gather(core, broker, None, "run_x", candidate=CANDIDATE, identity=RESOLVED,
                                         attribute=POOLED_POTENCY, objective_text="rank by potency", cutoff_date=None)
    assert [c["value"] for c in claims] == [9.0] and error_ref is not None and searched == ["interaction_evidence_lookup"]
    both = [e.event_type for e in core.journal.replay("run_x") if e.event_type in ("tool.errored", "tool.returned")]
    assert both == ["tool.errored", "tool.returned"]                     # both routes are on the record
    cell, _ = assessor.assess_cell(candidate=CANDIDATE, attribute=POOLED_POTENCY, rule=ORDERING, rule_set_ref="rules@v1",
                                   claims=claims, resolved=True, tool_error_ref=error_ref, searched=searched)
    assert cell["verdict"] == "pass" and cell["value"] == 9.0 and cell["tool_error_ref"] == error_ref


# --- reading one cell's documents concurrently (config `concurrency.read_workers`) ----------

PAPERS = {"Alpha": 41, "Bravo": 52, "Charlie": 63, "Delta": 74}   # paper -> the bioavailability it reports
# Extraction finishes in the reverse of the reading order, so a result assembled in completion
# order would come back 74, 63, 52, 41 and the ordering assertions below would catch it.
EXTRACTION_DELAY = {"Alpha": 0.06, "Bravo": 0.04, "Charlie": 0.02, "Delta": 0.0}

BIOAVAILABILITY = {"attribute_id": "attr_oral-bioavailability", "version": 1, "name": "Oral bioavailability",
                   "definition": "Fraction of an oral dose reaching systemic circulation",
                   "measurement_kind": "quantitative", "unit": "%", "direction": "higher_better", "aggregation": "max",
                   "acceptable_value_sources": ["peer_reviewed"],
                   "evidence_request": {"capability": "literature_retrieval", "question_kind": "search",
                                        "parameters": {"query_template": '({names}) AND "oral bioavailability"',
                                                       "relevance_terms": ["bioavailability"]}}}
HALF_LIFE = dict(BIOAVAILABILITY, attribute_id="attr_half-life", name="Elimination half-life",
                 definition="Time for the plasma concentration to halve", unit="h")
READING_ATTRIBUTES = [{"name": a["name"], "definition": a["definition"], "unit": a["unit"],
                       "ref": f"{a['attribute_id']}@v{a['version']}"} for a in (BIOAVAILABILITY, HALF_LIFE)]


class PaperSearch:
    """One query, four hits: the shape a literature cell reads."""

    contract = ToolContract(tool_id="tool_paper_search", capability="literature_retrieval",
                            capability_kind="source_retrieval", question_kinds=("search",), contract_version="1",
                            implementation_version="fake-1", purpose_statement="papers on one compound",
                            evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def invoke(self, question_kind, inputs):
        hits = [{"pmcid": f"PMC_{name}", "doi": f"10.0/{name}", "title": f"{name}: Alphatinib pharmacokinetics",
                 "abstract_html": "Alphatinib oral bioavailability in healthy volunteers",
                 "identifiers": [{"scheme": "doi", "value": f"10.0/{name}"}]} for name in PAPERS]
        return ProviderResponse(values=[{"name": "search_hit", "value": h, "value_kind": "curated"} for h in hits])


class PaperReader:
    contract = ToolContract(tool_id="tool_paper_reader", capability="document_reading",
                            capability_kind="document_reading", question_kinds=("read",), contract_version="1",
                            implementation_version="fake-1", purpose_statement="full text of one paper",
                            evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def __init__(self):
        self.reads: list[str] = []

    def invoke(self, question_kind, inputs):
        name = inputs["pmcid"].split("_")[1]
        self.reads.append(name)
        quote = f"Alphatinib had an oral bioavailability of {PAPERS[name]}% in this cohort"
        passages = [{"passage_id": "title", "kind": "title", "section_path": [],
                     "text": f"{name}: Alphatinib pharmacokinetics"},
                    {"passage_id": "sec1.p1", "kind": "paragraph", "section_path": ["Results"], "text": f"{quote}."}]
        document = {"title": f"{name}: Alphatinib pharmacokinetics", "passages": passages,
                    "access_state": "full_text_available", "reading_depth": "full_text",
                    "source_hit": {"is_preprint": False}}
        return ProviderResponse(values=[{"name": "document", "value": document, "value_kind": "curated"}])


class ExtractionModel:
    """The reader model, counting its calls and the calls that overlapped one another.

    A `barrier` is how a test proves concurrency without a timing threshold: every call waits for
    the others, so sequential reading times the wait out and fails the test instead of passing by
    luck, and `highest_overlap` is then the number of parties rather than whatever the host's load
    allowed. `delay` runs after the wait, so completion order can be set against reading order.
    """

    def __init__(self, delay: dict[str, float] | None = None, barrier: threading.Barrier | None = None):
        self.delay, self.barrier = delay or {}, barrier
        self.calls: list[str] = []
        self.highest_overlap = 0
        self._running = 0
        self._lock = threading.Lock()

    def __call__(self, request):
        text = request.messages[0]["content"]
        name = next(n for n in PAPERS if f"{n}: Alphatinib pharmacokinetics" in text)
        with self._lock:
            self.calls.append(name)
            self._running += 1
            self.highest_overlap = max(self.highest_overlap, self._running)
        try:
            if self.barrier is not None:
                self.barrier.wait(timeout=20)
            time.sleep(self.delay.get(name, 0.0))
        finally:
            with self._lock:
                self._running -= 1
        quote = f"Alphatinib had an oral bioavailability of {PAPERS[name]}% in this cohort"
        claim = {"passage_id": "sec1.p1", "quoted_span": quote, "statement": quote, "determination_basis": "measured",
                 "polarity": "supports", "value": PAPERS[name], "unit": "%"}
        if "attribute_name" in request.response_schema["properties"]["claims"]["items"]["properties"]:
            # one read of this paper serves every literature attribute the prompt lists
            return {"claims": [dict(claim, attribute_name=a["name"]) for a in READING_ATTRIBUTES
                               if f"- {a['name']}:" in text]}
        return {"claims": [claim]}


def literature_cell(core, *, delay=None, barrier=None):
    broker = Broker(core, sleep=lambda s: None)
    reader_tool = PaperReader()
    broker.register(PaperSearch())
    broker.register(reader_tool)
    model = ExtractionModel(delay, barrier)
    roster = ModelRoster({"s": ScriptedAdapter("s", model, model="scripted-reader")}, {"reader": "s"})
    return broker, roster, model, reader_tool


def read_cell(core, broker, roster, *, attribute=BIOAVAILABILITY, **kw):
    return gather(core, broker, roster, "run_x", candidate=CANDIDATE, identity=RESOLVED, attribute=attribute,
                  objective_text="rank by oral bioavailability", cutoff_date=None, max_documents=4, **kw)


def test_reading_several_documents_concurrently_yields_exactly_the_claims_the_sequential_path_yields(tmp_path):
    """Runs are replayed and their digests compared, so a cell's claims may not be ordered by which
    worker finished first. The extraction delays here invert completion order against reading order."""
    seen = []
    for workers in (1, len(PAPERS)):
        barrier = threading.Barrier(workers) if workers > 1 else None
        with Core.open(tmp_path / f"root{workers}") as core:
            broker, roster, model, reader_tool = literature_cell(core, delay=EXTRACTION_DELAY, barrier=barrier)
            claims, error_ref, searched = read_cell(core, broker, roster, document_workers=workers)
            assert error_ref is None and searched == ["literature_retrieval", "document_reading"]
            seen.append([(c["source_ref"], c["value"], c["location"]["quoted_span"]) for c in claims])
            # the tool and model calls are made in whatever order the workers get to them; only the
            # claims the cell returns are ordered, and they are ordered by the documents, not by them
            assert sorted(reader_tool.reads) == sorted(model.calls) == sorted(PAPERS)
            assert model.highest_overlap == workers
    assert [value for _, value, _ in seen[0]] == list(PAPERS.values())     # the documents' own order
    assert seen[0] == seen[1]


def test_a_document_already_in_the_cache_is_not_read_twice_when_two_workers_want_it_at_once(core):
    """Two cells of the same candidate, gathered at the same time over one cache: the memo exists so
    that a (candidate, paper) pair costs one extraction, and a thread that arrives while the first
    is still in the model call has to wait for it rather than pay for a second."""
    broker, roster, model, reader_tool = literature_cell(core, delay=dict.fromkeys(PAPERS, 0.05))
    cache = LiteratureCache()
    together = threading.Barrier(2)

    def cell(attribute):
        together.wait(timeout=20)      # both cells enter the shared cache at once, not one after the other
        return read_cell(core, broker, roster, attribute=attribute, cache=cache, document_workers=len(PAPERS),
                         reading_attributes=READING_ATTRIBUTES)

    with ThreadPoolExecutor(max_workers=2) as pool:
        both = [f.result() for f in [pool.submit(cell, BIOAVAILABILITY), pool.submit(cell, HALF_LIFE)]]

    assert sorted(model.calls) == sorted(PAPERS)              # four papers, four extractions, not eight
    assert sorted(reader_tool.reads) == sorted(PAPERS)
    for claims, _, _ in both:
        assert [c["value"] for c in claims] == list(PAPERS.values())
    assert {c["attribute_ref"] for c in both[0][0]} == {"attr_oral-bioavailability@v1"}
    assert {c["attribute_ref"] for c in both[1][0]} == {"attr_half-life@v1"}


@pytest.mark.parametrize("workers", (1, 4))
def test_a_budget_refusal_during_concurrent_reading_still_stops_the_run(core, workers):
    """A refusal mid-flight must leave the cell unassessed. Returning the two documents that were
    read before the cap, with no error reference, would be a cell scored on a third of its evidence
    and indistinguishable from a complete one."""
    broker, roster, model, _ = literature_cell(core)
    with pytest.raises(BudgetBlocked):
        read_cell(core, broker, roster, document_workers=workers, budget=Budget({"llm_turns": 2}))
    assert len(model.calls) == 2                               # the refusal came mid-flight, not before the cell


def test_the_journals_hash_chain_verifies_after_concurrent_appends(core):
    """Claims and tool events are appended from the workers; `Journal.append` serializes them under
    the store write lock, so `seq` stays contiguous and every record hashes to what it was stored as."""
    broker, roster, model, _ = literature_cell(core, delay=dict.fromkeys(PAPERS, 0.02))
    claims, _, _ = read_cell(core, broker, roster, document_workers=4)
    core.journal.verify("run_x")
    admitted = [e for e in core.journal.replay("run_x") if e.event_type == "evidence.admitted"]
    assert {e.payload["claim_id"] for e in admitted} == {c["claim_id"] for c in claims}
    assert [e.seq for e in core.journal.replay("run_x")] == list(range(1, core.journal.last_seq("run_x") + 1))


def test_the_default_worker_count_is_one_so_behaviour_is_unchanged_unless_the_setting_is_raised(core):
    import inspect

    from mas.core import config as config_mod

    settings = config_mod.resolve(project_file=None, environ={})
    assert settings["concurrency.read_workers"] == 1 and config_mod.SETTINGS["concurrency.read_workers"].minimum == 1
    assert inspect.signature(gather).parameters["document_workers"].default == 1
    broker, roster, model, reader_tool = literature_cell(core, delay=dict.fromkeys(PAPERS, 0.02))
    claims, error_ref, _ = read_cell(core, broker, roster)        # no document_workers: the default path
    assert model.highest_overlap == 1 and reader_tool.reads == list(PAPERS)
    assert [c["value"] for c in claims] == list(PAPERS.values()) and error_ref is None


def test_a_document_whose_claims_cannot_be_extracted_is_skipped_rather_than_ending_the_round(core):
    """Measured on 14 October 2026 against DeepSeek: `reading.extract_claims` under
    `derivation.enumerate_dimension` raised `parse_failed: no JSON value found in the model reply`
    and killed a derivation after 1.5 hours and 312 admitted claims. The same class of failure in
    `refine_stage` had killed the run before it. A reasoning provider that occasionally answers in
    prose is a property of the provider, and a document whose claims cannot be extracted contributes
    nothing -- which is exactly what an unreadable document already does. It is skipped and counted,
    and the dimension reports it so a reader can tell "little evidence" from "evidence lost"."""
    import inspect
    from mas.core import derivation
    from mas.core.models import ModelError

    source = inspect.getsource(derivation.enumerate_dimension)
    assert "except ModelError" in source, "the extraction call must be guarded"
    assert "unreadable.append" in source
    assert 'error.error_class == "quota_exhausted"' in source, (
        "a budget refusal is the run being told to stop and must still propagate")
    assert '"documents_unreadable": unreadable' in inspect.getsource(derivation), (
        "a dimension must report the documents whose evidence was lost")

    # and the repair budget that let a single prose reply through is now two, not one
    from mas.core import models
    assert inspect.signature(models.call_role).parameters["max_repairs"].default == 2


def test_an_attribute_declaring_databases_and_literature_is_gathered_on_both_paths(core):
    """One quantity, two curations and a published report of it (`criteria.check_attribute` permits
    the mixture for a quantitative attribute pooled by a numeric aggregation). `gather` dispatched on
    `is_literature_bound` and returned at the first branch, so such a cell's databases were never
    called at all and it read as though no record existed. Both halves are asked; the cell's claims
    are their union; and the scale still decides what counts -- the extracted figures here are
    percentages, which this attribute has no conversion for and does not score on."""
    from mas.core import criteria

    literature_route = {"capability": "literature_retrieval", "question_kind": "search",
                        "parameters": {"query_template": '({names}) AND "CSF1R" AND (IC50 OR Ki)',
                                       "relevance_terms": ["CSF1R", "IC50"], "search_limit": 4}}
    mixed = dict(POOLED_POTENCY, acceptable_value_sources=["curated_measurement", "peer_reviewed"],
                 evidence_requests=CSF1R_ROUTES + [literature_route])
    criteria.check_attribute(mixed)
    broker, roster, model, reader_tool = literature_cell(core)
    chembl, gtopdb = Curation("pchembl_values", "tool_chembl", [7.0, 7.4]), Curation("gtopdb_affinity", "tool_gtopdb", [9.0])
    broker.register(chembl)
    broker.register(gtopdb)
    claims, error_ref, searched = read_cell(core, broker, roster, attribute=mixed)
    assert chembl.calls == gtopdb.calls == ["CHEMBL1844"], "the curated routes are asked"
    assert sorted(reader_tool.reads) == sorted(PAPERS), "and so is the literature route"
    assert error_ref is None
    assert searched == ["interaction_evidence_lookup", "literature_retrieval", "document_reading"]
    assert sorted(c["value"] for c in claims if c["unit"] == "pChEMBL") == [7.0, 7.4, 9.0]
    assert sorted(c["value"] for c in claims if c["unit"] == "%") == sorted(PAPERS.values())

    cell, _ = assessor.assess_cell(candidate=CANDIDATE, attribute=mixed, rule=ORDERING, rule_set_ref="rules@v1",
                                   claims=claims, resolved=True, searched=searched)
    assert cell["verdict"] == "pass" and cell["value"] == 7.4 and len(cell["value_source_claim_refs"]) == 3
    assert {entry["reason"] for entry in cell["set_aside_claims"]} == {"unit_unresolved"}
