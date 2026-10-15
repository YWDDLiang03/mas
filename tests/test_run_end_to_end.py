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
    claim = {"passage_id": "sec1.p1", "quoted_span": quote, "statement": quote, "determination_basis": "measured",
             "polarity": "supports", "value": BIOAVAILABILITY[name], "unit": "%"}
    if "attribute_name" in request.response_schema["properties"]["claims"]["items"]["properties"]:
        claim["attribute_name"] = "Oral bioavailability"     # one read serves every literature attribute
    return {"claims": [claim]}


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


def test_candidates_below_the_ranking_coverage_floor_get_no_position():
    from mas.core.leaderboard import build_snapshot
    context = dict(SPEC, task_context_id="task_x", version=1)
    rule_set = {"rule_set_ref": "rules@v1", "entries": [{"rule_kind": "preference"}, {"rule_kind": "preference"}],
                "ordering_method": {}}
    roll = {c: {"state": "provisional", "state_reason": "x", "hard_rule_coverage": 0.0, "blocking_unknowns": []} for c in "ab"}
    snapshot = build_snapshot(task_context=context, leaderboard_id="lbd_x_1", run_id="run_x", round_id="r", rule_set=rule_set,
                              evidence_snapshot_id=None, roll_ups=roll, cells={"a": [], "b": []},
                              scores={"a": (1.0, 0.5), "b": (0.6, 1.0)}, identities={}, parent=None, sweep_completeness=1.0,
                              budget={}, ranking_coverage_floor=0.75)
    entries = {e["candidate_ref"]: e for e in snapshot["candidate_entries"]}
    assert entries["b"]["position"] == 1 and entries["a"]["position"] is None
    assert "too little preference evidence" in entries["a"]["rank_note"]
    assert snapshot["reporting_tuple"]["unranked_for_coverage"] == 1


def test_shortlist_stage_copies_criteria_and_keeps_boundary_ties(core):
    from mas.core import staging
    task_id = setup_task(core)
    make_controller(core).start(task_id, by=OPERATOR, sweep_seed=7)
    (snapshot,) = leaderboard.snapshots(core, task_id)
    assert [e["candidate_ref"] for e in staging.shortlist_members(snapshot, 1)] == ["cand_ik-ALPHA"]
    new_task = staging.shortlist_task(core, task_id, top_k=1, by=OPERATOR)
    context = task.get(core, new_task)
    assert context["derived_from_task_id"] == task_id and context["candidate_universe"]["members"] == ["ALPHA"]
    assert context["candidate_universe"]["shortlist_rule"]["source_snapshot_id"] == snapshot["snapshot_id"]
    copied = criteria.load(core, "rule_molecular-weight@v1", new_task)
    assert copied["copied_from"]["rule_ref"] == "rule_molecular-weight@v1"
    open_items = [i for i in review.items(core, [new_task]).values() if i["state"] == "open"]
    assert sorted(i["subject"]["id"] for i in open_items) == [                      # expert-set cutoffs raised again
        "rule_molecular-weight@v1", "rule_oral-bioavailability@v1"]


# --- the mandated-coverage floor --------------------------------------------------------------
# Measured on the published board of 14 October 2026 (`lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4`,
# rules@v3, 9 criteria of which 6 are task-mandated): `assessor.preference_scores` averages over the
# preference rules a candidate was *evaluated* on, so a candidate assessed on few cells is scored on
# its best-covered subset -- and the top four entries each had one of the five required receptors
# measured, mebendazole (an anthelmintic) at rank 4, above candidates assessed on all five. The
# ranking coverage floor of 0.5 does not catch it, because 4 of the 9 criteria are structural
# descriptors available for every compound.

RECEPTORS = ["VEGFR1", "VEGFR2", "VEGFR3", "FGFR1", "CSF1R"]
DESCRIPTORS = ["Molecular weight", "TPSA", "Rotatable bonds", "Hydrogen bond donors"]


def _cell(candidate, name, verdict, *, mandated):
    prefix = "receptor" if mandated else "descriptor"
    return {"assessment_id": f"asm_{candidate}_{name}", "candidate_ref": candidate,
            "attribute_ref": f"attr_{prefix}-{name}@v1", "rule_ref": f"rule_{prefix}-{name}@v1",
            "rule_kind": "preference", "verdict": verdict, "value": 8.0 if verdict == "pass" else None,
            "value_kind": "curated" if verdict == "pass" else "missing", "conflicting_claim_refs": []}


def _nine_criterion_board(measured_receptors: dict[str, list[str]], scores, *, floor=1.0):
    """The shape of the live board: five required receptors as ordering preferences and four
    structural descriptors every compound answers."""
    cells = {candidate: [_cell(candidate, r, "pass" if r in mine else "unknown_missing", mandated=True)
                         for r in RECEPTORS]
                        + [_cell(candidate, d, "pass", mandated=False) for d in DESCRIPTORS]
             for candidate, mine in measured_receptors.items()}
    rule_set = {"rule_set_ref": "rules@v3", "ordering_method": {},
                "entries": [{"rule_ref": f"rule_receptor-{r}@v1", "rule_kind": "preference"} for r in RECEPTORS]
                           + [{"rule_ref": f"rule_descriptor-{d}@v1", "rule_kind": "preference"} for d in DESCRIPTORS]}
    roll = {c: {"state": "provisional", "state_reason": "no confirmed hard rule; ranked on preferences only",
                "hard_rule_coverage": None, "blocking_unknowns": [], "n_fail_hard": 0, "n_unknown_hard": 0}
            for c in measured_receptors}
    return leaderboard.build_snapshot(
        task_context=dict(SPEC, task_context_id="task_x", version=1), leaderboard_id="lbd_x_1", run_id="run_x",
        round_id="r", rule_set=rule_set, evidence_snapshot_id=None, roll_ups=roll, cells=cells,
        scores=scores, identities={}, parent=None, sweep_completeness=1.0, budget={},
        mandated_rule_refs=[f"rule_receptor-{r}@v1" for r in RECEPTORS], mandated_coverage_floor=floor)


def test_a_candidate_with_one_of_five_required_receptors_is_ineligible_and_the_four_are_named():
    """A candidate may be ranked on the task's objective only once the task's own criteria have been
    answered for it. The entry is kept, with the gate's own vocabulary extended to the task's
    criteria -- `clears_mandated_criteria`, the counts behind it, and `mandated_blocked_by` naming
    what is missing -- because "nobody has measured this compound at four of the five required
    receptors" is a finding about the evidence and the one thing a silent drop would hide."""
    snapshot = _nine_criterion_board(
        {"mebendazole": ["CSF1R"], "surufatinib": RECEPTORS},
        # the inversion the live board showed: the thinly assessed candidate scores higher
        {"mebendazole": (0.93, 5 / 9), "surufatinib": (0.71, 1.0)})
    entries = {e["candidate_ref"]: e for e in snapshot["candidate_entries"]}
    thin, full = entries["mebendazole"], entries["surufatinib"]
    assert thin["clears_mandated_criteria"] is False and thin["position"] is None
    assert (thin["n_mandated"], thin["n_mandated_answered"]) == (5, 1) and thin["mandated_coverage"] == 0.2
    assert thin["mandated_blocked_by"] == ["attr_receptor-FGFR1@v1", "attr_receptor-VEGFR1@v1",
                                           "attr_receptor-VEGFR2@v1", "attr_receptor-VEGFR3@v1"]
    assert "4 of the 5 criteria the task itself requires are unanswered" in thin["rank_note"]
    assert thin["state"] == "provisional", "its state and its cells are untouched; only the ranking is refused"
    assert full["clears_mandated_criteria"] is True and full["position"] == 1 and "rank_note" not in full
    reported = snapshot["reporting_tuple"]
    assert reported["mandated_coverage_floor"] == 1.0 and reported["ineligible_for_mandated_coverage"] == 1
    assert reported["eligible_on_mandated_criteria"] == 1
    assert reported["mandated_rule_refs"] == sorted(f"rule_receptor-{r}@v1" for r in RECEPTORS)
    # the 0.5 ranking coverage floor is the floor that cannot see this: 5 of 9 criteria answered
    assert reported["unranked_for_coverage"] == 0 and 5 / 9 > reported["ranking_coverage_floor"]


def test_the_mandated_floor_is_a_registered_number_and_a_looser_one_ranks_the_thin_candidate_again():
    """The floor is a setting with a constant id, like the ranking coverage floor beside it, so the
    number a board was built with is recorded on the board and reproducible from it."""
    from mas.core import config, constants

    assert config.SETTINGS["rank.mandated_coverage_floor"].default == 1.0
    assert constants.CORE_DEFAULTS["const_mandated_coverage_floor"] == (1.0, "fraction")
    settings = config.resolve(project_file=None, environ={}, overrides={"rank.mandated_coverage_floor": 0.2})
    assert ("const_mandated_coverage_floor", 0.2, "fraction") in settings.registered_constants()
    snapshot = _nine_criterion_board({"mebendazole": ["CSF1R"], "surufatinib": RECEPTORS},
                                     {"mebendazole": (0.93, 5 / 9), "surufatinib": (0.71, 1.0)}, floor=0.2)
    entries = {e["candidate_ref"]: e for e in snapshot["candidate_entries"]}
    assert entries["mebendazole"]["position"] == 1 and entries["surufatinib"]["position"] == 2
    assert snapshot["reporting_tuple"]["ineligible_for_mandated_coverage"] == 0


def test_a_board_whose_task_mandates_nothing_is_unchanged_by_the_floor():
    """None, not False: a task with no criterion built from its own context has no mandated
    population, and an absent number reads as unknown rather than as a candidate that failed."""
    snapshot = _nine_criterion_board({"alpha": RECEPTORS, "beta": ["CSF1R"]},
                                     {"alpha": (0.4, 1.0), "beta": (0.9, 5 / 9)})
    bare = leaderboard.build_snapshot(
        task_context=dict(SPEC, task_context_id="task_x", version=1), leaderboard_id="lbd_x_1", run_id="run_x",
        round_id="r", rule_set={"rule_set_ref": "rules@v1", "ordering_method": {},
                                "entries": [{"rule_ref": "rule_a@v1", "rule_kind": "preference"}]},
        evidence_snapshot_id=None,
        roll_ups={"alpha": {"state": "provisional", "state_reason": "x", "hard_rule_coverage": None,
                            "blocking_unknowns": []}},
        cells={"alpha": [_cell("alpha", "CSF1R", "pass", mandated=True)]}, scores={"alpha": (0.5, 1.0)},
        identities={}, parent=None, sweep_completeness=1.0, budget={})
    (entry,) = bare["candidate_entries"]
    assert entry["clears_mandated_criteria"] is None and entry["position"] == 1 and "rank_note" not in entry
    assert bare["reporting_tuple"]["ineligible_for_mandated_coverage"] == 0
    assert snapshot["candidate_entries"][0]["candidate_ref"] == "alpha", "and with mandated refs the floor applies"


# --- the floor measures what ranks, not what gates ---------------------------------------------
# Measured on the same published board: of the 16 candidates answering all five required receptors,
# only 9 also have a value for the sixth mandated criterion, the oral-route hard exclusion. ChEMBL
# derives its route flags from approved-product records and has no `oral` value for 1,262 of the
# 3,177 candidates -- most of the Phase-III population the task explicitly admits -- so the strict
# reading of the floor withheld a position from 7 candidates because a register does not cover them.

GATE_RULE_REF = "rule_gate-oral-route@v1"
GATE_ATTR_REF = "attr_gate-oral-route@v1"


def _board_with_a_mandated_gate(gate_verdicts: dict[str, str], *, floor=1.0):
    """The live shape: five mandated receptor preferences, four descriptors and one mandated hard
    exclusion whose value a register may simply not carry."""
    cells, roll = {}, {}
    for candidate, gate in gate_verdicts.items():
        cells[candidate] = ([_cell(candidate, r, "pass", mandated=True) for r in RECEPTORS]
                            + [_cell(candidate, d, "pass", mandated=False) for d in DESCRIPTORS]
                            + [dict(_cell(candidate, "oral-route", gate, mandated=True),
                                    attribute_ref=GATE_ATTR_REF, rule_ref=GATE_RULE_REF,
                                    rule_kind="hard_exclusion")])
        unknown_hard = 1 if gate not in ("pass", "fail") else 0
        roll[candidate] = {
            # the states `assessor.roll_up` gives these three cases
            "state": "rejected" if gate == "fail" else "recommended" if gate == "pass" else "provisional",
            "state_reason": (f"hard rule unknown: {GATE_ATTR_REF}" if unknown_hard
                             else f"hard rule failed: {GATE_ATTR_REF}" if gate == "fail"
                             else "every hard rule passed"),
            "hard_rule_coverage": 0.0 if unknown_hard else 1.0,
            "blocking_unknowns": [GATE_ATTR_REF] if unknown_hard else [],
            "n_fail_hard": 1 if gate == "fail" else 0, "n_unknown_hard": unknown_hard}
    rule_set = {"rule_set_ref": "rules@v3", "ordering_method": {},
                "entries": [{"rule_ref": f"rule_receptor-{r}@v1", "rule_kind": "preference"} for r in RECEPTORS]
                           + [{"rule_ref": f"rule_descriptor-{d}@v1", "rule_kind": "preference"} for d in DESCRIPTORS]
                           + [{"rule_ref": GATE_RULE_REF, "rule_kind": "hard_exclusion"}]}
    return leaderboard.build_snapshot(
        task_context=dict(SPEC, task_context_id="task_x", version=1), leaderboard_id="lbd_x_1", run_id="run_x",
        round_id="r", rule_set=rule_set, evidence_snapshot_id=None, roll_ups=roll, cells=cells,
        scores={c: (0.7, 1.0) for c in gate_verdicts}, identities={}, parent=None, sweep_completeness=1.0,
        budget={}, mandated_rule_refs=[f"rule_receptor-{r}@v1" for r in RECEPTORS] + [GATE_RULE_REF],
        mandated_coverage_floor=floor)


def test_the_mandated_floor_ignores_a_hard_exclusion_a_register_cannot_answer():
    """The floor exists so that a comparable *score* can be computed, which is a question about
    value-bearing quantities and not about gates. A mandated hard exclusion already carries its own
    missingness policy, and applying the floor on top conflates "cannot be recommended" with
    "cannot be ranked" -- while an unknown produced by a register's coverage is a fact about the
    register, not evidence about the compound."""
    snapshot = _board_with_a_mandated_gate({"cediranib": "unknown_missing", "pazopanib": "pass"})
    entries = {e["candidate_ref"]: e for e in snapshot["candidate_entries"]}
    unknown_gate, clean = entries["cediranib"], entries["pazopanib"]
    # the gate is not in the population the floor measures, so answering all five receptors is enough
    assert (unknown_gate["n_mandated"], unknown_gate["n_mandated_answered"]) == (5, 5)
    assert unknown_gate["mandated_coverage"] == 1.0 and unknown_gate["clears_mandated_criteria"] is True
    assert unknown_gate["mandated_blocked_by"] == [] and "rank_note" not in unknown_gate
    assert unknown_gate["position"] is not None and clean["position"] is not None
    # the gate is named rather than dropped, so a reader can see what the floor did not measure
    assert unknown_gate["mandated_gates"] == [GATE_ATTR_REF]
    assert unknown_gate["mandated_gates_unanswered"] == [GATE_ATTR_REF]
    assert clean["mandated_gates"] == [GATE_ATTR_REF] and clean["mandated_gates_unanswered"] == []
    # and the gate's own effect is untouched: it is ranked, and it cannot be recommended
    assert unknown_gate["state"] == "provisional" and unknown_gate["clears_hard_rules"] is False
    assert unknown_gate["gate_blocked_by"] == [GATE_ATTR_REF] and unknown_gate["n_unknown_hard"] == 1
    assert clean["state"] == "recommended" and clean["clears_hard_rules"] is True
    reported = snapshot["reporting_tuple"]
    assert reported["eligible_on_mandated_criteria"] == 2 and reported["ineligible_for_mandated_coverage"] == 0
    # what the decision costs, stated on the board rather than left to be recomputed
    assert reported["ranked_with_a_mandated_gate_unanswered"] == 1


def test_a_candidate_failing_a_mandated_gate_is_still_rejected_by_it():
    """The narrowing is about an *unknown* gate. A gate with a value still does what it does: a
    `fail` is a rejection, and the floor neither saves nor withholds anything there."""
    snapshot = _board_with_a_mandated_gate({"failing": "fail"})
    (entry,) = snapshot["candidate_entries"]
    assert entry["clears_mandated_criteria"] is True, "the floor measures the five receptors"
    assert entry["mandated_gates_unanswered"] == [], "the gate was answered -- in the negative"
    assert entry["state"] == "rejected" and entry["n_fail_hard"] == 1
    assert entry["clears_hard_rules"] is False and entry["position"] is None, "a failed gate is not ranked"
