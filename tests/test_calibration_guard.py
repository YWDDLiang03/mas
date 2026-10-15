"""The calibration guard (`assessor.calibration_guard`, applied by `controller._calibration_guard`).

A hard exclusion can be perfectly well sourced and still be the wrong line for the candidates it is
applied to, and from the inside that failure looks like selectivity: the board simply shows fewer
compounds. The guard measures each hard exclusion against the population that survives the task's
own mandated criteria and demotes the ones that remove nearly all of it -- so the criterion keeps
measuring, keeps ranking and keeps its evidence, and stops deleting.

Two things these tests are mostly about. The first is the denominator: a share over the universe
would not catch a gate that excludes every approved drug of the class the task is about, so the
reference set is the candidates that clear the *task-mandated* criteria and the guard abstains when
there are too few of them to measure a share over. The second is blindness: the guard computes a
fraction over a set and must not be able to see, branch on or report whether any particular
candidate is in it -- so relabelling the candidates, the reference outcome included, must leave its
answer bit-for-bit identical.
"""

from __future__ import annotations

import inspect
import json

import pytest

from mas.core import assessor, criteria, derivation, leaderboard, review, task
from mas.core import config as config_mod
from mas.core.broker import Broker, ProviderResponse, ToolContract
from mas.core.controller import RunController
from mas.core.journal import actor
from mas.core.runtime import Core
from tests.fakes import FakeIdentity

OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")
EXPERT = actor("human", "E1", "expert", identity_basis="recorded_attestation")
AGENT = actor("agent", "proposer-1", "proposer")
ADAPTER = {"adapter_id": "test_adapter", "adapter_version": "1", "primary_scheme": "ik"}

MANDATED_RULE = "rule_mandated@v1"
GATE_RULE = "rule_gate@v1"


def _cell(rule_ref: str, verdict: str, *, rule_kind: str = "hard_exclusion") -> dict:
    return {"rule_ref": rule_ref, "rule_kind": rule_kind, "verdict": verdict,
            "attribute_ref": rule_ref.replace("rule_", "attr_")}


def _world(gate_verdicts: dict[str, str], *, mandated: str = "pass",
           mandated_kind: str = "preference") -> dict[str, list[dict]]:
    """One cell per candidate for the mandated criterion and one for the gate under test."""
    return {candidate: [_cell(MANDATED_RULE, mandated, rule_kind=mandated_kind),
                        _cell(GATE_RULE, verdict)]
            for candidate, verdict in gate_verdicts.items()}


RULES = {MANDATED_RULE: {"rule_kind": "preference"}, GATE_RULE: {"rule_kind": "hard_exclusion"}}


# --- the reference set ---------------------------------------------------------------------------

def test_the_reference_set_is_what_survives_the_tasks_own_mandated_criteria():
    """Three decisions, each stated: a mandated `fail` is out, a mandated hard exclusion that could
    not be answered is out (the task stated it as a requirement, and an unknown is not a candidate
    meeting it), and a candidate with no value-bearing mandated cell at all is out -- without that
    last one the denominator would be every compound nobody has evidence about, which is the
    universe-wide rate the guard exists to avoid."""
    mandated = {MANDATED_RULE}
    assert assessor.clears_mandated([_cell(MANDATED_RULE, "pass", rule_kind="preference")], mandated)
    assert not assessor.clears_mandated([_cell(MANDATED_RULE, "fail", rule_kind="preference")], mandated)
    assert not assessor.clears_mandated([_cell(MANDATED_RULE, "unknown_missing", rule_kind="preference")], mandated)
    # an unknown on a mandated *hard exclusion* disqualifies; on a mandated preference it does not,
    # as long as something else the task mandates did carry a value
    both = [_cell(MANDATED_RULE, "pass", rule_kind="preference"),
            _cell("rule_mandated_gate@v1", "unknown_missing")]
    assert not assessor.clears_mandated(both, {MANDATED_RULE, "rule_mandated_gate@v1"})
    assert assessor.clears_mandated(both, {MANDATED_RULE})
    # a cell of a rule the task did not mandate is not consulted at all
    assert assessor.clears_mandated([_cell(MANDATED_RULE, "pass", rule_kind="preference"),
                                     _cell(GATE_RULE, "fail")], mandated)
    # and the clause that decides which population is measured: clearing the task's gates is not
    # membership on its own, where the task also mandates quantities of its own. Measured on the
    # published board of 14 October 2026, this is the whole difference between a guard that works and
    # one that does not -- the weaker reading admits the 1,269 compounds with an oral route on record,
    # over which the predicted DILI gate removes 54.5% (its universe-wide rate is 51.2%), while over
    # the candidates that also carry a curated potency at a required receptor it removes 100%.
    gate_only = [_cell("rule_mandated_gate@v1", "pass"),
                 _cell(MANDATED_RULE, "unknown_missing", rule_kind="preference")]
    assert not assessor.clears_mandated(gate_only, {MANDATED_RULE, "rule_mandated_gate@v1"})
    assert assessor.clears_mandated([_cell("rule_mandated_gate@v1", "pass"),
                                     _cell(MANDATED_RULE, "pass", rule_kind="preference")],
                                    {MANDATED_RULE, "rule_mandated_gate@v1"})
    # where the task mandates gates and nothing else, clearing them is the whole of its requirement
    assert assessor.clears_mandated([_cell("rule_mandated_gate@v1", "pass")], {"rule_mandated_gate@v1"})


def test_a_gate_that_removes_nearly_the_whole_reference_set_is_demoted_with_the_measured_share():
    """The case the guard is for, in the smallest world that shows it: eleven of the twelve
    candidates that clear the task's mandated criteria fail this gate, which is 0.917 of them -- past
    the registered 0.90 -- so it is demoted to a preference and the record carries the fraction."""
    verdicts = {f"cand_{i:02d}": ("pass" if i == 1 else "fail") for i in range(1, 13)}
    report = assessor.calibration_guard(_world(verdicts), RULES, mandated_rule_refs=[MANDATED_RULE])
    assert report["reference_set_n"] == 12 and report["abstained"] is None
    demotion = report["demoted"][GATE_RULE]
    assert demotion["removed_n"] == 11 and demotion["removed_share"] == pytest.approx(11 / 12)
    assert demotion["reason"] == "demoted_by_calibration_guard"
    assert (demotion["rule_kind_before"], demotion["rule_kind_after"]) == ("hard_exclusion", "preference")
    assert "0.917" in demotion["detail"] and "12" in demotion["detail"]
    checked = {c["rule_ref"]: c for c in report["hard_exclusions_checked"]}
    assert checked[GATE_RULE]["demoted"] is True
    # and the selective gate right below the limit stands: the guard is not a view about how much a
    # screen may exclude, it is a check on a gate that has stopped discriminating at all
    selective = {f"cand_{i:02d}": ("pass" if i <= 2 else "fail") for i in range(1, 13)}
    kept = assessor.calibration_guard(_world(selective), RULES, mandated_rule_refs=[MANDATED_RULE])
    assert kept["demoted"] == {} and kept["hard_exclusions_checked"][0]["removed_share"] == pytest.approx(10 / 12)


def test_the_limit_is_the_registered_one_and_the_share_is_reported_either_way():
    verdicts = {f"cand_{i:02d}": ("pass" if i == 1 else "fail") for i in range(1, 13)}
    cells = _world(verdicts)
    assert assessor.calibration_guard(cells, RULES, mandated_rule_refs=[MANDATED_RULE],
                                      max_removed_share=0.95)["demoted"] == {}
    strict = assessor.calibration_guard(cells, RULES, mandated_rule_refs=[MANDATED_RULE], max_removed_share=0.5)
    assert set(strict["demoted"]) == {GATE_RULE} and strict["limit"] == 0.5
    setting = config_mod.SETTINGS["assess.max_reference_exclusion_share"]
    assert setting.default == assessor.DEFAULT_MAX_REFERENCE_EXCLUSION == 0.90
    assert setting.const_id == "const_assess_max_reference_exclusion_share"


def test_the_guard_abstains_rather_than_demoting_on_a_population_it_cannot_measure():
    """No mandated criterion means no population to calibrate against, and a handful of candidates
    cannot tell "excludes nearly all of them" from "excluded the three it saw". Both abstentions say
    so in the record: a guard that silently did nothing would read as a gate that passed the check."""
    verdicts = {f"cand_{i:02d}": "fail" for i in range(1, 13)}
    nothing_mandated = assessor.calibration_guard(_world(verdicts), RULES, mandated_rule_refs=[])
    assert nothing_mandated["demoted"] == {} and "no criterion was built from the task context" \
        in nothing_mandated["abstained"]
    tiny = assessor.calibration_guard(_world({"cand_01": "fail", "cand_02": "fail"}), RULES,
                                      mandated_rule_refs=[MANDATED_RULE])
    assert tiny["demoted"] == {} and tiny["reference_set_n"] == 2
    assert f"below the {assessor.MIN_CALIBRATION_REFERENCE}" in tiny["abstained"]
    # the same twelve candidates, none of which clears the mandated criteria: nothing to measure over
    unmeasured = assessor.calibration_guard(_world(verdicts, mandated="unknown_missing"), RULES,
                                            mandated_rule_refs=[MANDATED_RULE])
    assert unmeasured["reference_set_n"] == 0 and unmeasured["demoted"] == {}


# --- blindness ----------------------------------------------------------------------------------

def test_the_guard_cannot_see_which_candidate_it_is_measuring():
    """The guard's whole input is cells and rule kinds: no task context, no identities, no seed list,
    so there is no `is_reference_outcome` to consult and no label to branch on. This pins the
    consequence -- relabelling every candidate, the disclosed reference compound included, leaves the
    answer identical -- and that no candidate reference appears in the record at all, so neither the
    demotion nor the report can be read back to a compound.

    `is_reference_outcome` lives on the task context's seed candidates and is read by
    `controller.start`, `derivation.derive` and `sr_stage`; the guard is the place a leak would be
    worst, because a gate kept or demoted according to who it removes is the outcome being written
    into the screen.
    """
    verdicts = {"cand_ik-REFOTINIB": "pass", **{f"cand_ik-C{i:03d}": "fail" for i in range(11)}}
    first = assessor.calibration_guard(_world(verdicts), RULES, mandated_rule_refs=[MANDATED_RULE])
    # the reference compound is now one of the excluded ones, and every other label changes too
    relabelled = {("cand_ik-C999" if candidate == "cand_ik-REFOTINIB" else f"x_{candidate}"): verdict
                  for candidate, verdict in verdicts.items()}
    relabelled["cand_ik-C999"] = "fail"
    relabelled["x_cand_ik-C000"] = "pass"
    second = assessor.calibration_guard(_world(relabelled), RULES, mandated_rule_refs=[MANDATED_RULE])
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["demoted"][GATE_RULE]["removed_n"] == 11
    text = json.dumps(first)
    assert "REFOTINIB" not in text and "cand_" not in text
    # and it is blind structurally, not by discipline: nothing it is handed carries the disclosure.
    # `is_reference_outcome` is a field of the task context's seed candidates, and neither the guard
    # nor its reference-set predicate is given a task context, an identity record or a seed list.
    assert set(inspect.signature(assessor.calibration_guard).parameters) == {
        "cells_by_candidate", "rules", "mandated_rule_refs", "max_removed_share"}
    assert set(inspect.signature(assessor.clears_mandated).parameters) == {"cells", "mandated_rule_refs"}
    guard_code = inspect.getsource(assessor.calibration_guard).split('"""')[2]
    assert "is_reference_outcome" not in guard_code and "task_context" not in guard_code


# --- through the controller ----------------------------------------------------------------------

SPEC = {
    "objective_text": "Rank test compounds for target T1", "mode": "conditional",
    "scope_entities": [{"entity_kind": "target", "identifier": "T1", "role": "required",
                        "identifier_scheme": "test_target", "label": "T1"}],
    "candidate_universe": {"kind": "enumerated_set", "members": [f"c{i:02d}" for i in range(1, 13)]},
    "seed_candidates": [{"candidate_ref": "c01", "reason_supplied": "known outcome", "is_reference_outcome": True}],
    "constraints": [],
    "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True},
    "human_review_requirements": {"recommended_requires_hd": False},
}
POTENCY = {"name": "T1 potency", "definition": "Potency against T1, as curated",
           "measurement_kind": "quantitative", "unit": "pChEMBL", "direction": "higher_better",
           "acceptable_value_sources": ["database_entry"], "aggregation": "median",
           "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                                "identifier_scheme": "ik", "parameters": {"property": "potency"}}}
TOX = {"name": "Predicted toxicity", "definition": "Probability the compound is toxic",
       "measurement_kind": "quantitative", "unit": "probability", "direction": "lower_better",
       "acceptable_value_sources": ["database_entry"], "aggregation": "max",
       "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                            "identifier_scheme": "ik", "parameters": {"property": "tox"}}}
TOX_RULE = {"rule_kind": "hard_exclusion", "cutoff": {"comparator": "<=", "value": 0.5, "unit": "probability"},
            "cutoff_basis": "expert_set", "on_missing": "unknown_blocks_recommendation"}
IDENTITIES = {f"c{i:02d}": [{"preferred_label": f"C{i:02d}", "identifiers": [{"scheme": "ik", "value": f"C{i:02d}"}],
                             "link_basis": "name_match_single_candidate"}] for i in range(1, 13)}


class Panel:
    """Both quantities for every candidate: a potency the task mandates a criterion for, and a
    toxicity probability that is 0.9 for everyone but the first compound."""

    contract = ToolContract(
        tool_id="tool_panel", capability="property_estimate", capability_kind="attribute_estimate",
        question_kinds=("computed_property",), contract_version="1", implementation_version="fake-1",
        purpose_statement="test panel", evidence_kind_produced="database_entry",
        claim_strength_ceiling="curated", identity_inputs=("identifier",))
    UNITS = {"potency": "pChEMBL", "tox": "probability"}

    def invoke(self, question_kind, inputs):
        name = inputs["property"]
        index = int(inputs["identifier"][1:])
        value = 6.0 + index / 10 if name == "potency" else (0.2 if index == 1 else 0.9)
        return ProviderResponse(
            values=[{"name": name, "value": value, "unit": self.UNITS[name], "value_kind": "curated",
                     "source_record_ref": f"panel:{inputs['identifier']}:{name}"}],
            data_version="fake", upstream_refs=[f"panel:{inputs['identifier']}"])


def _mandated_templates(task_context):
    """What an adapter template does: one criterion per required scope entity, carrying the
    task-context field it was built from (`criteria.is_task_mandated`)."""
    return [{"source_field": "scope_entities[0]", "attribute": POTENCY,
             "rule": {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
                      "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty"}}]


def _setup(core, *, limit: float | None = None) -> tuple[str, RunController, object]:
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    mandated = derivation.objective_criteria(core, task_id, templates=_mandated_templates, by=OPERATOR)
    attribute = criteria.load(core, mandated[0]["attribute_ref"], task_id)
    assert criteria.is_task_mandated(attribute), "the template's criterion is the task's own"
    criteria.propose(core, task_id, TOX, TOX_RULE, by=AGENT)
    for item in review.items(core, [task_id]).values():
        review.decide(core, item, decision="approve", actor=EXPERT, reason_text="", entry="interactive",
                      historical_list_exposure="not_exposed")
    criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    broker = Broker(core, sleep=lambda s: None)
    broker.register(FakeIdentity(IDENTITIES))
    broker.register(Panel())
    overrides = {} if limit is None else {"assess.max_reference_exclusion_share": str(limit)}
    settings = config_mod.resolve(project_file=None, environ={}, overrides=overrides)
    return task_id, RunController(core, broker, None, adapter=ADAPTER), settings


def test_a_demoted_gate_still_ranks_and_the_board_says_what_was_measured(core):
    """End to end: the expert-approved toxicity gate removes eleven of the twelve candidates that
    clear the task's mandated criterion, so the run demotes it. What that has to mean downstream is
    the point of this test -- the eleven are ranked rather than rejected, the gate still contributes
    its pass/fail to the score, and the board carries the measured share and the reason."""
    task_id, controller, settings = _setup(core)
    run_id = controller.start(task_id, by=OPERATOR, sweep_seed=3, settings=settings)
    assert controller.current_state(run_id) == "completed"
    (snapshot,) = leaderboard.snapshots(core, task_id)
    guard = snapshot["calibration_guard"]
    assert guard["reference_set_n"] == 12 and guard["abstained"] is None
    (demoted_ref,) = list(guard["demoted"])
    assert demoted_ref.startswith("rule_predicted-toxicity")
    assert guard["demoted"][demoted_ref]["removed_share"] == pytest.approx(11 / 12)
    assert guard["demoted"][demoted_ref]["reason"] == "demoted_by_calibration_guard"
    entries = {e["candidate_ref"]: e for e in snapshot["candidate_entries"]}
    assert not [e for e in entries.values() if e["state"] == "rejected"], "a demoted gate deletes nobody"
    assert all(e["position"] is not None for e in entries.values()), "every candidate is still ranked"
    # the gate's evidence survives the demotion: it is a preference now, so failing it costs score
    assert entries["cand_ik-C01"]["preference_score"] > entries["cand_ik-C02"]["preference_score"]
    assert snapshot["result_kind"] == "ranked_under_score"   # no hard rule is left standing on this board
    recorded = [e for e in core.journal.replay(run_id) if e.event_type == "decision.recorded"]
    assert len(recorded) == 1 and recorded[0].payload["approval_kind"] == "software_status"
    assert recorded[0].payload["confirmed_by_a_person"] is False
    artifact = core.artifacts.payload(recorded[0].payload["artifact_id"])
    assert artifact["guard_id"].startswith("cal_") and artifact["reference_set_n"] == 12
    assert "cand_" not in json.dumps(artifact), "the record names no candidate"
    gate_cells = [payload for _, payload in core.artifacts.of_kind("assessment")
                  if payload["rule_ref"] == demoted_ref]
    assert len(gate_cells) == 12 and all(c["rule_kind"] == "hard_exclusion" for c in gate_cells), \
        "the cells as assessed are untouched; the demotion is this run's decision, recorded on the run"
    assert criteria.load(core, demoted_ref, task_id)["rule_kind"] == "hard_exclusion", \
        "and the registry's rule is untouched too: the guard decided what this run did with it"


def test_the_same_gate_excludes_when_the_operator_raises_the_limit(core):
    """The setting is the decision, and this is the proof it is read: at 0.95 the identical gate
    clears the guard and does what a hard exclusion does. Which is also the honest reading of the
    default -- it is a registered judgement about how much a gate may remove, not a law."""
    task_id, controller, settings = _setup(core, limit=0.95)
    run_id = controller.start(task_id, by=OPERATOR, sweep_seed=3, settings=settings)
    (snapshot,) = leaderboard.snapshots(core, task_id)
    assert snapshot["calibration_guard"]["demoted"] == {}
    assert snapshot["calibration_guard"]["hard_exclusions_checked"][0]["removed_share"] == pytest.approx(11 / 12)
    entries = {e["candidate_ref"]: e for e in snapshot["candidate_entries"]}
    assert sum(e["state"] == "rejected" for e in entries.values()) == 11
    assert snapshot["result_kind"] == "both_reported"
    assert not [e for e in core.journal.replay(run_id) if e.event_type == "decision.recorded"], \
        "nothing was demoted, so there is no demotion to record; the share is on the board either way"


# --- the mandated-coverage floor, through the same seam ------------------------------------------
# The guard measures hard exclusions against the candidates that clear the task's mandated criteria.
# The floor below is the other half of that notion: a candidate may be *ranked* on the task's
# objective only once the task's own criteria have been answered for it. Both read one list of
# mandated rule refs (`criteria.is_task_mandated`, assembled in `controller._finish`), so there is
# one definition of what the task requires.


DESCRIPTOR = {"name": "Molecular weight", "definition": "Molecular weight of the parent compound",
              "measurement_kind": "quantitative", "unit": "g/mol", "direction": "lower_better",
              "acceptable_value_sources": ["database_entry"], "aggregation": "consensus",
              "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                                   "identifier_scheme": "ik", "parameters": {"property": "mw"}}}
DESCRIPTOR_RULE = {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
                   "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty"}


class SparsePanel(Panel):
    """Curated potency as it really is -- measured for a few compounds and absent for the rest; 74
    of the 3,177 candidates of the manuscript universe carry one at a required receptor -- beside a
    structural descriptor every compound answers, which is the shape that defeats the ranking
    coverage floor: half the preferences evaluated is above the 0.5 that floor asks for.

    The toxicity probability is low for everybody, so nothing is excluded and nothing is demoted and
    the mandated floor is the only thing deciding who may hold a position.
    """

    MEASURED = 4
    UNITS = dict(Panel.UNITS, mw="g/mol")

    def _one(self, name, identifier, value):
        return ProviderResponse(values=[{"name": name, "value": value, "unit": self.UNITS[name],
                                         "value_kind": "curated",
                                         "source_record_ref": f"panel:{identifier}:{name}"}],
                                data_version="fake", upstream_refs=[f"panel:{identifier}"])

    def invoke(self, question_kind, inputs):
        index, name = int(inputs["identifier"][1:]), inputs["property"]
        if name == "tox":
            return self._one(name, inputs["identifier"], 0.2)
        if name == "mw":
            return self._one(name, inputs["identifier"], 300.0 + index)
        if index > self.MEASURED:
            return ProviderResponse(values=[], data_version="fake", upstream_refs=[f"panel:{inputs['identifier']}"])
        return super().invoke(question_kind, inputs)


def _sparse_run(core, root=None):
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    derivation.objective_criteria(core, task_id, templates=_mandated_templates, by=OPERATOR)
    criteria.propose(core, task_id, DESCRIPTOR, DESCRIPTOR_RULE, by=AGENT)
    criteria.propose(core, task_id, TOX, TOX_RULE, by=AGENT)
    for item in review.items(core, [task_id]).values():
        review.decide(core, item, decision="approve", actor=EXPERT, reason_text="", entry="interactive",
                      historical_list_exposure="not_exposed")
    criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    broker = Broker(core, sleep=lambda s: None)
    broker.register(FakeIdentity(IDENTITIES))
    broker.register(SparsePanel())
    settings = config_mod.resolve(project_file=None, environ={}, overrides={})
    controller = RunController(core, broker, None, adapter=ADAPTER)
    run_id = controller.start(task_id, by=OPERATOR, sweep_seed=3, settings=settings)
    assert controller.current_state(run_id) == "completed"
    return task_id, run_id


def test_a_candidate_the_tasks_own_criterion_is_unanswered_for_is_not_ranked_on_it(core):
    """Through the controller, so the floor is read off the registered constant the run bound and
    applied where the board is built. Eight of the twelve candidates have no curated potency at the
    task's required target; they keep their entries, their states and their cells, and they are
    reported as ineligible for a position with the criterion they are missing named."""
    task_id, run_id = _sparse_run(core)
    (snapshot,) = leaderboard.snapshots(core, task_id)
    entries = {e["candidate_ref"]: e for e in snapshot["candidate_entries"]}
    measured = [f"cand_ik-C{i:02d}" for i in range(1, SparsePanel.MEASURED + 1)]
    unmeasured = [f"cand_ik-C{i:02d}" for i in range(SparsePanel.MEASURED + 1, 13)]
    assert all(entries[c]["clears_mandated_criteria"] is True for c in measured)
    assert sorted(e["candidate_ref"] for e in snapshot["candidate_entries"] if e["position"]) == measured
    for candidate in unmeasured:
        entry = entries[candidate]
        assert entry["clears_mandated_criteria"] is False and entry["position"] is None
        assert (entry["n_mandated"], entry["n_mandated_answered"]) == (1, 0)
        assert entry["mandated_blocked_by"] == ["attr_t1-potency@v1"]
        assert "1 of the 1 criteria the task itself requires are unanswered" in entry["rank_note"]
        assert entry["state"] == "recommended", "the gate it does clear is not taken away from it"
        assert entry["preference_score"] is not None, "it has a score; what it has not is the task's quantity"
        assert entry["preference_coverage"] == 0.5, "which is exactly what the ranking floor lets through"
    reported = snapshot["reporting_tuple"]
    assert reported["mandated_coverage_floor"] == 1.0
    assert reported["eligible_on_mandated_criteria"] == 4 and reported["ineligible_for_mandated_coverage"] == 8
    assert reported["mandated_rule_refs"] == ["rule_t1-potency@v1"]
    assert reported["unranked_for_coverage"] == 0, "the ranking coverage floor sees nothing wrong here"
    assert reported["ranking_coverage_floor"] == 0.5


def test_the_board_command_names_the_floor_and_what_each_ineligible_candidate_is_missing(tmp_path, capsys):
    """A board that ranked a thinly assessed candidate above a fully assessed one read as a ranking
    of potency. These are the lines that tell a reader which candidates the task's own criteria were
    answered for at all."""
    from mas.cli import main as cli

    root = tmp_path / "store"
    with Core.open(root) as core:
        task_id, _ = _sparse_run(core)
    assert cli.main(["--store", str(root), "board", "show", task_id, "--all"]) == 0
    shown = capsys.readouterr().out
    assert ("mandated-criteria floor 1.00 over 1 criteria the task requires: 4 candidate(s) answer it, "
            "8 are not ranked") in shown
    assert "ineligible for a position: 1 of 1 criteria the task requires are unanswered (attr_t1-potency@v1)" in shown
