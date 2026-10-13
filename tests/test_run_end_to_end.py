import pytest

from mas.adapters.literature import jats
from mas.core import criteria, leaderboard, projection, review, task
from mas.core.broker import Broker, ProviderResponse, ToolContract
from mas.core.controller import RunController, RunError
from mas.core.journal import actor
from mas.core.models import ModelRoster, ScriptedAdapter
from mas.core.runtime import Core
from tests.fakes import FakeIdentity, FakeProperty

OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")
EXPERT = actor("human", "E1", "expert", identity_basis="recorded_attestation")
ADAPTER = {"adapter_id": "test_adapter", "adapter_version": "1", "primary_scheme": "ik"}

SPEC = {
    "objective_text": "Rank test compounds", "mode": "conditional",
    "scope_entities": [{"entity_kind": "target", "identifier": "T1", "role": "required"}],
    "candidate_universe": {"kind": "enumerated_set", "members": ["alpha", "beta", "gamma", "delta"]},
    "constraints": [{"text": "oral", "kind": "route", "hardness": "hard"}],
    "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True},
    "human_review_requirements": {"recommended_requires_hd": False},
}
MW = {"name": "Molecular weight", "definition": "Molecular weight of the parent compound", "measurement_kind": "quantitative",
      "unit": "g/mol", "direction": "lower_better", "acceptable_value_sources": ["database_entry"], "aggregation": "consensus",
      "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                           "identifier_scheme": "ik", "parameters": {"property": "MW"}}}
MW_RULE = {"rule_kind": "hard_exclusion", "cutoff": {"comparator": "<=", "value": 500, "unit": "g/mol"}, "cutoff_basis": "expert_set"}
BIO = {"name": "Oral bioavailability", "definition": "Fraction of an oral dose reaching circulation", "measurement_kind": "quantitative",
       "unit": "%", "direction": "higher_better", "acceptable_value_sources": ["peer_reviewed"], "aggregation": "max",
       "evidence_request": {"capability": "literature_retrieval", "question_kind": "search",
                            "parameters": {"query_template": '({names}) AND "oral bioavailability"',
                                           "relevance_terms": ["bioavailability"]}}}
BIO_RULE = {"rule_kind": "preference", "cutoff": {"comparator": ">=", "value": 30, "unit": "%"}, "cutoff_basis": "expert_set"}

IDENTITIES = {name: [{"preferred_label": name.title(), "identifiers": [{"scheme": "ik", "value": name.upper()}],
                      "link_basis": "name_match_single_candidate"}] for name in ("alpha", "beta", "gamma")}
WEIGHTS = {("ALPHA", "MW"): 300.0, ("BETA", "MW"): 450.0, ("GAMMA", "MW"): 650.0}
BIOAVAILABILITY = {"Alpha": 40, "Beta": 20, "Gamma": 70}


class FakeSearch:
    contract = ToolContract(tool_id="tool_fake_search", capability="literature_retrieval", capability_kind="source_retrieval",
                            question_kinds=("search",), contract_version="1", implementation_version="fake",
                            purpose_statement="s", evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def invoke(self, question_kind, inputs):
        name = next(n for n in BIOAVAILABILITY if n in inputs["query"])
        hit = {"pmcid": f"PMC_{name}", "doi": f"10.0/{name}", "title": f"{name} pharmacokinetics",
               "abstract_html": f"{name} oral bioavailability study", "identifiers": [{"scheme": "doi", "value": f"10.0/{name}"}]}
        return ProviderResponse(values=[{"name": "search_hit", "value": hit, "value_kind": "curated"}])


class FakeReader:
    contract = ToolContract(tool_id="tool_fake_reader", capability="document_reading", capability_kind="document_reading",
                            question_kinds=("read",), contract_version="1", implementation_version="fake",
                            purpose_statement="r", evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def invoke(self, question_kind, inputs):
        name = inputs["pmcid"].split("_")[1]
        passages = [{"passage_id": "title", "kind": "title", "section_path": [], "text": f"{name} pharmacokinetics"},
                    {"passage_id": "sec1.p1", "kind": "paragraph", "section_path": ["Results"],
                     "text": f"In healthy volunteers, {name} had an oral bioavailability of {BIOAVAILABILITY[name]}% after a single dose."}]
        doc = {"title": f"{name} pharmacokinetics", "passages": passages, "access_state": "full_text_available",
               "reading_depth": "full_text", "source_hit": {"is_preprint": False}}
        return ProviderResponse(values=[{"name": "document", "value": doc, "value_kind": "curated"}])


def reader_script(request):
    text = request.messages[0]["content"]
    name = next(n for n in BIOAVAILABILITY if f"Candidate: {n}" in text)
    quote = f"{name} had an oral bioavailability of {BIOAVAILABILITY[name]}%"
    return {"claims": [{"passage_id": "sec1.p1", "quoted_span": quote, "statement": quote, "determination_basis": "measured",
                        "polarity": "supports", "value": BIOAVAILABILITY[name], "unit": "%"}]}


class Crash(BaseException):
    pass


class CrashingProperty(FakeProperty):
    def __init__(self, table, crash_after):
        super().__init__(table)
        self.crash_after = crash_after

    def invoke(self, question_kind, inputs):
        if self.calls >= self.crash_after:
            raise Crash()
        return super().invoke(question_kind, inputs)


def setup_task(core):
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    criteria.propose(core, task_id, MW, MW_RULE, by=OPERATOR)
    criteria.propose(core, task_id, BIO, BIO_RULE, by=OPERATOR)
    for item in review.items(core, [task_id]).values():
        review.decide(core, item, decision="approve", actor=EXPERT, reason_text="", entry="interactive",
                      historical_list_exposure="not_exposed")
    criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    return task_id


def make_controller(core, property_provider=None):
    broker = Broker(core, sleep=lambda s: None)
    broker.register(FakeIdentity(IDENTITIES))
    broker.register(property_provider or FakeProperty(WEIGHTS))
    broker.register(FakeSearch())
    broker.register(FakeReader())
    roster = ModelRoster({"s": ScriptedAdapter("s", reader_script, model="scripted-reader")}, {"reader": "s"})
    return RunController(core, broker, roster, adapter=ADAPTER)


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c


def test_full_sweep_publishes_a_ranked_snapshot(core):
    task_id = setup_task(core)
    controller = make_controller(core)
    run_id = controller.start(task_id, by=OPERATOR, sweep_seed=7)
    assert controller.current_state(run_id) == "completed"
    (snapshot,) = leaderboard.snapshots(core, task_id)
    entries = {e["candidate_ref"]: e for e in snapshot["candidate_entries"]}
    assert snapshot["result_kind"] == "both_reported"
    assert entries["cand_ik-GAMMA"]["state"] == "rejected"           # MW 650 fails the hard rule
    assert entries["cand_ik-ALPHA"]["state"] == "recommended"
    assert entries["cand_ik-BETA"]["state"] == "recommended"
    assert entries["cand_ik-ALPHA"]["position"] == 1                 # 40% ≥ 30% passes the preference
    assert entries["cand_ik-BETA"]["position"] == 2
    assert entries["cand_name-delta"]["state"] == "unassessed"       # identity unresolved: not_assessed, never dropped
    assert snapshot["reporting_tuple"]["sweep_completeness"] == 1.0
    assert snapshot["reporting_tuple"]["precision_among_admitted"] is None
    ending = [e for e in core.journal.replay(run_id) if e.event_type == "run.completed"][0]
    assert ending.termination_reason == "round_limit_reached"
    view = projection.progress(core, run_id)
    assess = next(p for p in view["progress"] if p["scope"] == "stage:assess")
    assert (assess["completed"], assess["planned"], assess["percent"]) == (8, 8, 100)
    with pytest.raises(RunError):
        controller.execute(run_id)                                     # an ended run is never re-entered


def test_no_short_circuit_after_a_hard_fail(core):
    task_id = setup_task(core)
    run_id = make_controller(core).start(task_id, by=OPERATOR)
    gamma = [e for e in core.journal.replay(run_id) if e.event_type == "candidate.assessed"
             and e.payload["candidate_ref"] == "cand_ik-GAMMA"]
    assert sorted(e.payload["verdict"] for e in gamma) == ["fail", "pass"]


def test_crash_then_resume_reuses_finished_cells(core):
    task_id = setup_task(core)
    crashing = make_controller(core, CrashingProperty(WEIGHTS, crash_after=2))
    run_id = crashing.start(task_id, by=OPERATOR, execute=False)
    with pytest.raises(Crash):
        crashing.execute(run_id)
    assert crashing.current_state(run_id) == "running"
    done_before = [e for e in core.journal.replay(run_id) if e.event_type == "candidate.assessed"]
    resumed = make_controller(core)
    assert resumed.resume(run_id) == "completed"
    cells = [e for e in core.journal.replay(run_id) if e.event_type == "candidate.assessed"]
    keys = [(e.payload["rule_ref"], e.payload["candidate_ref"]) for e in cells]
    assert len(keys) == len(set(keys)) == 8                           # nothing assessed twice
    ending = [e for e in core.journal.replay(run_id) if e.event_type == "run.completed"][0]
    assert ending.payload["reused_cells"] == len(done_before)
    assert any(e.event_type == "attempt.finalized" and e.payload["finalized_by"] == "controller"
               for e in core.journal.replay(run_id))


def test_budget_exhaustion_leaves_the_run_unresolved_with_unswept_cells(core):
    task_id = setup_task(core)
    run_id = make_controller(core).start(task_id, by=OPERATOR, budget_envelope={"tool_calls": 5})
    assert RunController.current_state(make_controller(core), run_id) == "unresolved"
    closed = [e for e in core.journal.replay(run_id) if e.event_type == "round.closed"][0]
    assert closed.termination_reason == "budget_exhausted"
    assert closed.payload["unswept_cells_manifest"]
    (snapshot,) = leaderboard.snapshots(core, task_id)
    assert snapshot["reporting_tuple"]["sweep_completeness"] < 1.0
