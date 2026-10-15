"""Machine adjudication (core/adjudication.py): resolving the review queue with nobody to ask.

The point of the module is honesty, so most of these tests are about what the records say rather
than about what the pipeline then does: that an agent still cannot make an expert decision, that an
agent-resolved rule is labelled as such everywhere it travels, and that the two routes which would
hand an agent an expert's authority -- approving an expert-set cutoff, applying a hard exclusion --
are closed. Scripted models; no network.
"""

from __future__ import annotations

import json

import pytest

from mas.core import adjudication, assessor, bound_support, criteria, ledger, leaderboard, review, task
from mas.core import config as config_mod
from mas.core.journal import actor
from mas.core.models import ModelRoster, ScriptedAdapter
from mas.core.runtime import Core
from mas.ui.server import Workbench

OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")
EXPERT = actor("human", "E1", "expert", identity_basis="recorded_attestation")
AGENT = actor("agent", "proposer-1", "proposer")

SPEC = {
    "objective_text": "Prioritize oral compounds for target T1", "mode": "conditional",
    "scope_entities": [{"entity_kind": "target", "identifier": "T1", "role": "required"}],
    "candidate_universe": {"kind": "enumerated_set", "members": ["alpha", "beta"]},
    "constraints": [{"text": "oral administration", "kind": "route", "hardness": "hard", "provenance": "manuscript"},
                    {"text": "molecular weight at most 500 g/mol", "kind": "property", "hardness": "hard",
                     "provenance": "manuscript"},
                    {"text": "prefer a once-daily schedule", "kind": "dosing", "hardness": "soft"}],
    "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True},
}

ROUTE = {"name": "Oral administration on record", "measurement_kind": "categorical", "unit": None,
         "definition": "Whether an approved product of the compound is recorded for oral administration",
         "direction": "non_directional", "acceptable_value_sources": ["database_entry"], "aggregation": "consensus",
         "evidence_request": {"capability": "record_field_lookup", "question_kind": "record_field",
                              "parameters": {"field": "oral"}}}
ROUTE_RULE = {"rule_kind": "hard_exclusion", "predicate_form": "categorical_membership",
              "cutoff": {"comparator": "==", "value": True, "unit": None}, "cutoff_basis": "task_constraint",
              "on_missing": "unknown_blocks_recommendation"}

MW = {"name": "Molecular weight", "definition": "Molecular weight of the parent compound",
      "measurement_kind": "quantitative", "unit": "g/mol", "direction": "lower_better",
      "acceptable_value_sources": ["database_entry"], "aggregation": "consensus",
      "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                           "parameters": {"property": "MolecularWeight"}}}
MW_RULE = {"rule_kind": "hard_exclusion", "cutoff": {"comparator": "<=", "value": 500, "unit": "g/mol"},
           "cutoff_basis": "task_constraint"}

HALF_LIFE = {"name": "Terminal half-life", "definition": "Terminal half-life after a single oral dose",
             "measurement_kind": "quantitative", "unit": "h", "direction": "higher_better",
             "acceptable_value_sources": ["peer_reviewed"], "aggregation": "median",
             "evidence_request": {"capability": "literature_retrieval", "question_kind": "search",
                                  "parameters": {"query_template": '({names}) AND "half-life"'}}}
RATIONALE = "I chose this because a longer half-life is what the manuscript emphasised"
QUOTE = "a terminal half-life of 12 h supported once-daily dosing"


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c


def _task(core) -> str:
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    return task_id


def _derived(attribute: dict, task_id: str, field: str) -> dict:
    """An attribute an adapter template built from one task-context field, as `objective_criteria` records it."""
    return dict(attribute, derived_from={"task_context": f"{task_id}@v1", "field": field})


def _item(core, task_id: str, rule_ref: str) -> dict:
    return next(i for i in review.items(core, [task_id]).values() if i["subject"]["id"] == rule_ref)


def _claim(core, task_id: str) -> str:
    return ledger.record_claim(core, task_id, {
        "source_ref": "src_doi_10.1-b", "attribute_ref": "attr_terminal-half-life@v1",
        "location": {"location_kind": "paragraph", "locator_value": "sec1.p1", "section_path": ["Results"],
                     "quoted_span": QUOTE, "span_checked_against_source": True},
        "claim_text": QUOTE, "claim_text_marker": "paraphrase", "normalized_statement": QUOTE,
        "claim_type": "literature_extracted", "evidence_kind": "peer_reviewed", "determination_basis": "measured",
        "value": 12, "unit": "h", "polarity": "supports", "scope_match": "direct", "reading_depth": "full_text"},
        by=AGENT, admission_state="admitted", admission_reasons=["quote_verified"])


# --- the invariant this module must not touch ----------------------------------------------------

def test_an_agent_still_cannot_create_an_expert_decision_however_much_it_can_adjudicate(core):
    """Guard test for the invariant the whole slice is built around: an `hd_` is a person's record.

    `review.decide` refuses a non-human actor and non-interactive entry, and adding a way for a run
    to proceed without a person must not open a second door to the same record. Both refusals are
    asserted here, beside the machine adjudication of the very same item, so a change that relaxed
    either one fails here and not only in a test about expert decisions.
    """
    task_id = _task(core)
    _, rule_ref = criteria.propose(core, task_id, MW, dict(MW_RULE, cutoff_basis="expert_set"), by=AGENT)
    item = _item(core, task_id, rule_ref)

    with pytest.raises(review.ReviewError) as agent_tried:
        review.decide(core, item, decision="approve", actor=AGENT, reason_text="", entry="interactive")
    assert agent_tried.value.code == "rejected_unauthorized"
    with pytest.raises(review.ReviewError) as script_tried:
        review.decide(core, item, decision="approve", actor=EXPERT, reason_text="", entry="scripted")
    assert script_tried.value.code == "rejected_unauthorized"

    record = adjudication.adjudicate(core, item)
    assert record["adjudication_id"].startswith("adj_") and "decision_id" not in record
    assert record["approval_kind"] == "agent_verdict" != "human_scientific_approval"
    assert record["authority"] == "machine_adjudication" and record["confirmed_by_a_person"] is False
    assert not core.artifacts.of_kind("expert_decision"), "no adjudication may leave an hd_ behind"
    resolved = _item(core, task_id, rule_ref)
    assert resolved["state"] == "machine_adjudicated" and "decision_id" not in resolved
    with pytest.raises(review.ReviewError) as after:
        review.decide(core, resolved, decision="approve", actor=EXPERT, reason_text="", entry="interactive")
    assert after.value.code == "rejected_not_permitted_in_state"


# --- route 1: the task's own constraint ------------------------------------------------------------

def test_a_task_constraint_cutoff_is_confirmed_only_through_the_link_that_built_it(core):
    task_id = _task(core)
    _, rule_ref = criteria.propose(core, task_id, _derived(ROUTE, task_id, "constraints[0]"), ROUTE_RULE, by=AGENT)
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref))
    assert record["route"] == "task_constraint_restated" and record["resolution"] == "approve"
    assert record["cites"] == {"task_context_ref": f"{task_id}@v1", "field": "constraints[0]",
                               "match": "derived_from_task_field", "constraint_text": "oral administration",
                               "hardness": "hard", "provenance": "manuscript"}
    # approving means the rule enters unchanged: no new version, the hard exclusion intact
    assert record["rule_ref_after"] == rule_ref == record["rule_ref_before"]
    assert record["rule_kind_after"] == "hard_exclusion"


def test_a_proposal_cannot_authorise_itself_by_quoting_the_task_into_its_own_definition(core):
    """The one route that approves must rest on something a proposer cannot write.

    `derived_from.field` is a link an adapter template wrote when it built the criterion *from* a
    constraint. An attribute's name and definition are free text the proposer chooses, so matching
    the task's wording against them would let any proposal grant itself the task's authority by
    repeating it -- and this route confirms hard exclusions, which delete candidates outright.
    """
    task_id = _task(core)
    quoted = dict(ROUTE, name="Oral administration", definition="oral administration on record")
    _, rule_ref = criteria.propose(core, task_id, quoted, ROUTE_RULE, by=AGENT)
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref))
    assert record["resolution"] != "approve"
    assert record["route"] == "irreversible_without_authority" and record["rule_kind_after"] == "preference"


def test_a_cutoff_built_from_a_named_task_field_cites_that_field_and_its_version(core):
    task_id = _task(core)
    _, rule_ref = criteria.propose(core, task_id, _derived(MW, task_id, "constraints[1]"), MW_RULE, by=AGENT)
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref))
    assert record["route"] == "task_constraint_restated" and record["resolution"] == "approve"
    assert record["cites"]["field"] == "constraints[1]" and record["cites"]["match"] == "derived_from_task_field"
    assert record["cites"]["task_context_ref"] == f"{task_id}@v1"
    assert record["cites"]["constraint_text"] == "molecular weight at most 500 g/mol"


def test_a_cutoff_the_task_text_does_not_state_is_not_approved(core):
    """Three ways the claimed authority is not in the task text, each falling through to a demotion.

    The number matters as much as the wording: a rule that cites `constraints[1]` and then draws the
    line at 600 g/mol where the task says 500 is not restating the task, it is choosing a cutoff,
    which is the judgement this route may not supply.
    """
    task_id = _task(core)
    _, wrong_number = criteria.propose(core, task_id, _derived(MW, task_id, "constraints[1]"),
                                       dict(MW_RULE, cutoff={"comparator": "<=", "value": 600, "unit": "g/mol"}),
                                       by=AGENT)
    _, unrelated = criteria.propose(core, task_id, dict(HALF_LIFE, name="Aqueous solubility", unit="ug/mL"),
                                    {"rule_kind": "hard_exclusion", "cutoff_basis": "task_constraint",
                                     "cutoff": {"comparator": ">=", "value": 50, "unit": "ug/mL"}}, by=AGENT)
    _, soft = criteria.propose(core, task_id, dict(ROUTE, name="Once-daily schedule", attribute_id="attr_once-daily",
                                                   definition="Whether the product is recorded with a prefer "
                                                              "once-daily schedule"),
                               dict(ROUTE_RULE, rule_id="rule_once-daily"), by=AGENT)

    for rule_ref in (wrong_number, unrelated, soft):
        record = adjudication.adjudicate(core, _item(core, task_id, rule_ref))
        assert record["resolution"] != "approve", rule_ref
        assert record["route"] == "irreversible_without_authority", rule_ref
        assert record["cites"] == {} and record["rule_kind_after"] == "preference"


# --- route 2: an expert-set cutoff -----------------------------------------------------------------

def test_an_expert_set_cutoff_is_never_approved_autonomously_and_stops_scoring(core):
    task_id = _task(core)
    _, rule_ref = criteria.propose(core, task_id, HALF_LIFE,
                                   {"rule_kind": "preference", "cutoff_basis": "expert_set",
                                    "cutoff": {"comparator": ">=", "value": 6, "unit": "h"}}, by=AGENT)
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref))
    assert record["route"] == "no_authority_available" and record["resolution"] != "approve"
    assert record["rule_kind_before"] == "preference" and record["rule_kind_after"] == "exploratory_consideration"
    assert record["scores_candidates"] is False
    assert "expert's judgement" in record["reason_text"]
    # the demotion is a new rule version, because the assessor reads the kind off the rule record
    assert record["rule_ref_after"] == "rule_terminal-half-life@v2"
    assert criteria.load(core, record["rule_ref_after"], task_id)["adjudicated_by"] == record["adjudication_id"]
    ref = criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    (entry,) = criteria.rule_set(core, task_id, ref)["entries"]
    assert entry["rule_kind"] == "exploratory_consideration" and entry["authority"] == "machine_adjudication"


def test_an_expert_set_hard_exclusion_is_demoted_the_whole_way_rather_than_only_to_a_preference(core):
    """Where two routes could apply, the more conservative one wins: the missing authority is the
    expert's judgement about the number, which demoting to a preference would leave standing."""
    task_id = _task(core)
    _, rule_ref = criteria.propose(core, task_id, MW, dict(MW_RULE, cutoff_basis="expert_set"), by=AGENT)
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref))
    assert record["route"] == "no_authority_available"
    assert record["rule_kind_after"] == "exploratory_consideration" and record["scores_candidates"] is False


# --- route 3: a hard exclusion ----------------------------------------------------------------------

def test_a_hard_exclusion_is_demoted_rather_than_applied_so_no_candidate_is_silently_removed(core):
    """A hard exclusion deletes candidates from the result, so an agent demotes it instead of
    applying it. `roll_up` is the place that difference shows: the same failing cell rejects a
    candidate under a hard exclusion and leaves it standing under the preference it became."""
    task_id = _task(core)
    _, rule_ref = criteria.propose(core, task_id, MW, dict(MW_RULE, cutoff_basis="source_stated_value"), by=AGENT)
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref))
    assert record["route"] == "irreversible_without_authority" and record["resolution"] == "demote_to_preference"
    assert record["rule_kind_before"] == "hard_exclusion" and record["rule_kind_after"] == "preference"
    assert "deletes candidates" in record["reason_text"]

    failing = {"attribute_ref": "attr_molecular-weight@v1", "verdict": "fail"}
    before = assessor.roll_up("cand_x", [dict(failing, rule_kind="hard_exclusion")], coverage_floor=1.0,
                              recommended_requires_hd=False)
    after = assessor.roll_up("cand_x", [dict(failing, rule_kind=record["rule_kind_after"])], coverage_floor=1.0,
                             recommended_requires_hd=False)
    assert before["state"] == "rejected" and after["state"] != "rejected"


def test_a_demotion_drops_the_state_policies_only_a_hard_exclusion_may_hold(core):
    """`exclude` is an on-state policy `check_rule` allows only on a hard exclusion, and `ordering`
    a predicate form it allows only on a preference. A demotion that carried either across would
    have written a rule version the registry itself refuses."""
    task_id = _task(core)
    _, rule_ref = criteria.propose(core, task_id, MW,
                                   dict(MW_RULE, cutoff_basis="source_stated_value", on_missing="exclude"), by=AGENT)
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref))
    demoted = criteria.load(core, record["rule_ref_after"], task_id)
    assert demoted["on_missing"] == "unknown_blocks_recommendation"
    criteria.check_rule(demoted, criteria.load(core, demoted["attribute_ref"], task_id))

    _, ordering_ref = criteria.propose(core, task_id, HALF_LIFE,
                                       {"rule_kind": "preference", "predicate_form": "ordering",
                                        "cutoff": {"comparator": ">=", "value": 6, "unit": "h"},
                                        "cutoff_basis": "expert_set"}, by=AGENT)
    ordered = adjudication.adjudicate(core, _item(core, task_id, ordering_ref))
    became = criteria.load(core, ordered["rule_ref_after"], task_id)
    assert became["rule_kind"] == "exploratory_consideration" and became["predicate_form"] == "qualitative_judgment"


# --- route 4: the adjudicator -------------------------------------------------------------------------

def _disputed(core, task_id: str, rule: dict | None = None) -> tuple[str, str]:
    claim_id = _claim(core, task_id)
    attribute = dict(HALF_LIFE, rationale=RATIONALE, supporting_claim_refs=[claim_id])
    _, rule_ref = criteria.propose(
        core, task_id, attribute,
        rule or {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
                 "cutoff_basis": "none_evidence_insufficient", "expected_change": "ranks long-lived compounds higher"},
        by=AGENT, dispute={"open_critic_findings": [
            {"check": "evidence_support", "verdict": "fail", "severity": "material",
             "referent": "supporting_claim_ids", "finding": "the quote is about dosing, not about half-life itself"}],
            "pool_criterion": "cri_1", "derivation_run": None})
    return rule_ref, claim_id


def _roster(script) -> ModelRoster:
    """A roster where the adjudicator is bound to the proposer's adapter and a third family exists."""
    return ModelRoster({"p": ScriptedAdapter("p", script, model="proposer-model", provider_family="family_a"),
                        "c": ScriptedAdapter("c", script, model="critic-model", provider_family="family_b"),
                        "x": ScriptedAdapter("x", script, model="third-model", provider_family="family_c")},
                       {"proposer": "p", "critic": "c", "adjudicator": "p"})


def test_a_proposer_critic_dispute_is_resolved_by_the_adjudicator_on_a_third_model_family(core):
    task_id = _task(core)
    rule_ref, claim_id = _disputed(core, task_id)
    seen = {}

    def script(request):
        seen["content"] = request.messages[0]["content"]
        seen["role"] = request.role
        return {"verdict": "uphold_proposal", "cited_claim_ids": [claim_id, "claim_that_was_never_offered"],
                "reasoning": "the quote states the half-life value the attribute measures"}

    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref), roster=_roster(script))
    assert record["route"] == "dispute_adjudicated" and record["verdict"] == "uphold_proposal"
    assert record["resolution"] == "approve" and record["rule_kind_after"] == "preference"
    assert record["cited_claim_ids"] == [claim_id] and record["reasoning"].startswith("the quote states")

    marker = record["independence"]
    assert marker["adjudicator_family"] == "family_c" and marker["bound_adapter_id"] == "p"
    assert (marker["proposer_family"], marker["critic_family"]) == ("family_a", "family_b")
    assert marker["distinct_from_proposer"] and marker["distinct_from_critic"]
    assert marker["roster_offered_a_third_family"] is True
    assert marker["adjudicator_saw_proposer_rationale"] is False

    assert seen["role"] == "adjudicator"
    assert RATIONALE not in seen["content"], "the adjudicator sees the dispute blind, as the critic does"
    assert "expected_change" not in seen["content"] and QUOTE in seen["content"]
    view = json.loads(seen["content"].split("Criterion under dispute:\n", 1)[1].split("\n\nThe critic's")[0])
    assert "rationale" not in view["attribute"] and view["attribute"]["name"] == "Terminal half-life"


def test_a_dispute_the_adjudicator_cannot_settle_makes_the_rule_stop_scoring(core):
    task_id = _task(core)
    rule_ref, _claim_id = _disputed(core, task_id)
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref), roster=_roster(
        lambda request: {"verdict": "cannot_resolve", "cited_claim_ids": [], "reasoning": "the quote is ambiguous"}))
    assert record["verdict"] == "cannot_resolve" and record["rule_kind_after"] == "exploratory_consideration"
    assert record["scores_candidates"] is False


def test_an_adjudicated_dispute_never_hands_an_agent_the_authority_the_other_routes_withhold(core):
    """`criteria.propose` raises the dispute item *instead of* the confirmation item, so a disputed
    hard exclusion reaches route 4 with no expert gate behind it. Upholding the proposal must still
    not apply it: the routes compose, and the hard exclusion is demoted anyway."""
    task_id = _task(core)
    rule_ref, _claim_id = _disputed(core, task_id, rule={
        "rule_kind": "hard_exclusion", "cutoff": {"comparator": ">=", "value": 6, "unit": "h"},
        "cutoff_basis": "source_stated_value"})
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref), roster=_roster(
        lambda request: {"verdict": "uphold_proposal", "cited_claim_ids": [], "reasoning": "supported"}))
    assert record["verdict"] == "uphold_proposal" and record["resolution"] == "demote_to_preference"
    assert record["rule_kind_after"] == "preference" and "still a hard exclusion" in record["reason_text"]


def test_a_revision_may_weaken_a_rule_and_may_never_strengthen_one(core):
    task_id = _task(core)
    rule_ref, _claim_id = _disputed(core, task_id, rule={
        "rule_kind": "preference", "cutoff": {"comparator": ">=", "value": 6, "unit": "h"},
        "cutoff_basis": "source_stated_value"})
    weakened = adjudication.adjudicate(core, _item(core, task_id, rule_ref), roster=_roster(
        lambda request: {"verdict": "revise", "cited_claim_ids": [], "reasoning": "the claim states 12 h",
                         "revised_rule": {"cutoff": {"comparator": ">=", "value": 12, "unit": "h"}}}))
    assert weakened["resolution"] == "approve"
    assert criteria.load(core, weakened["rule_ref_after"], task_id)["cutoff"]["value"] == 12

    other_ref, _ = _disputed(core, task_id, rule={"rule_kind": "preference", "rule_id": "rule_exposure",
                                                  "cutoff": {"comparator": ">=", "value": 6, "unit": "h"},
                                                  "cutoff_basis": "source_stated_value"})
    strengthened = adjudication.adjudicate(core, _item(core, task_id, other_ref), roster=_roster(
        lambda request: {"verdict": "revise", "cited_claim_ids": [], "reasoning": "it should exclude",
                         "revised_rule": {"rule_kind": "hard_exclusion"}}))
    assert strengthened["resolution"] == "demote_to_exploratory_consideration"
    assert "may not make a rule a hard exclusion" in strengthened["reason_text"]


def test_a_dispute_with_no_adjudicator_to_call_is_left_open_rather_than_resolved(core):
    task_id = _task(core)
    rule_ref, _claim_id = _disputed(core, task_id)
    (left,) = adjudication.adjudicate_open(core, task_id)
    assert left["route"] is None and "no model roster" in left["left_open_because"]
    assert _item(core, task_id, rule_ref)["state"] == "open"


# --- route 5: the attribute's own definition --------------------------------------------------------

# The two criteria as the manuscript registry holds them: a definition that names a derived quantity,
# a rule the trigger table never gated (a preference with an ordering predicate, no cutoff and
# `none_evidence_insufficient`), and no `value_transform` -- so the cell carried surufatinib's raw
# 480.6 g/mol and its raw XLogP of 3.4 under the derived quantities' names and `lower_better`.
EXCESS = {"attribute_id": "attr_molecular-weight-in-excess-of-the-stated-upper-bound",
          "name": "Molecular weight in excess of the stated upper bound",
          "definition": "the excess in g/mol above 500, zero at or below it",
          "measurement_kind": "quantitative", "unit": "g/mol", "direction": "lower_better",
          "aggregation": "median", "acceptable_value_sources": ["database_entry"],
          "acceptable_determination_bases": ["derived"],
          "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                               "parameters": {"property": "MolecularWeight"}}}
BAND = dict(EXCESS, attribute_id="attr_distance-of-computed-lipophilicity-outside-the-stated-band",
            name="Distance of computed lipophilicity outside the stated band",
            definition="the distance of the computed lipophilicity outside the stated 2-4 band, zero inside it",
            unit="log units",
            evidence_request={"capability": "property_estimate", "question_kind": "computed_property",
                              "parameters": {"property": "XLogP"}})
ORDERING = {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
            "cutoff_basis": "none_evidence_insufficient"}
QUEUE_TEXT = ("the attribute's definition describes a derived quantity but the cell carries the raw value its "
              "source returns; a registered criterion changes only by expert decision")
# The two definitions the manuscript task's own attributes carry, verbatim down to the punctuation of
# the clause that decomposes the band, because the readings these sentences yield are the whole of
# what route 5 decides on: a paraphrase that tidied "the shortfall below 2 ... and the excess above 4"
# into one clause would stop being the case that was measured. Both are quoted to the end of a
# sentence, and every form in `_QUANTITY_FORMS` matches inside one sentence, so the elided remainder
# of each definition cannot take a reading away from what is pinned here.
LIPOPHILICITY_DEFINITION = (
    "The computed octanol-water partition coefficient of the neutral species, expressed as its distance "
    "in log units outside the band of approximately 2 to 4 that the cited source states as optimal for "
    "this inhibitor class: zero inside the band, the shortfall below 2 for a more polar molecule, and "
    "the excess above 4 for a more lipophilic one. Lower is better by construction.")
MOLECULAR_WEIGHT_DEFINITION = (
    "The computed molecular weight of the molecule, expressed as its excess in g/mol above 500 g/mol, "
    "the upper end of the band that the cited source states for this inhibitor class and describes as "
    "close to the upper limit compatible with efficient passive diffusion: zero for a molecule at or "
    "below 500 g/mol, and the difference above 500 g/mol for a heavier one.")


def _bound_claim(core, task_id: str, *, claim_id: str, quote: str, value, unit: str) -> str:
    """One admitted claim stating a bound, of the kind an attribute cites for its own definition."""
    return ledger.record_claim(core, task_id, {
        "claim_id": claim_id, "source_ref": "src_doi_10.1-c", "attribute_ref": "attr_bounds@v1",
        "location": {"location_kind": "paragraph", "locator_value": "sec2.p3", "section_path": ["Methods"],
                     "quoted_span": quote, "span_checked_against_source": True},
        "claim_text": quote, "claim_text_marker": "paraphrase", "normalized_statement": quote,
        "claim_type": "literature_extracted", "evidence_kind": "peer_reviewed", "determination_basis": "measured",
        "value": value, "unit": unit, "polarity": "supports", "scope_match": "direct", "reading_depth": "full_text"},
        by=AGENT, admission_state="admitted", admission_reasons=["quote_verified"])


def _queued(core, task_id: str, attribute: dict, *, cites: list[str]) -> dict:
    """Propose one criterion and raise the item the manuscript run raised on it.

    `criteria.propose` raises nothing here: the trigger table lets a preference with no cutoff
    through, so `needs_expert` is False and none of the first four routes is about this item. It is
    on the queue because the attribute measures something other than what its definition says, which
    is what its queue text states -- verbatim, so that a change to the wording does not change the
    case this test pins.
    """
    attr_ref, rule_ref = criteria.propose(core, task_id, dict(attribute, supporting_claim_refs=cites),
                                          ORDERING, by=AGENT)
    item_id = review.request(core, task_id, subject={"kind": "rule_version", "id": rule_ref, "version": 1,
                                                     "attribute_ref": attr_ref},
                             why_expert_required=QUEUE_TEXT, requested_by=AGENT)
    return review.items(core, [task_id])[item_id]


def _but_for(attribute: dict) -> dict:
    """Everything an attribute version holds except what a new version necessarily changes."""
    return {k: v for k, v in attribute.items()
            if k not in ("version", "value_transform", "supersedes", "adjudicated_by", "approval_kind")}


def test_an_attribute_whose_definition_states_an_upper_bound_gains_the_transform_the_definition_already_describes(core):
    """The definition is the authority, so the definition is the one field the edit may not touch."""
    task_id = _task(core)
    claim_id = _bound_claim(core, task_id, claim_id="claim_mw_bound", value=500, unit="g/mol",
                            quote="an upper bound of 500 g/mol on molecular weight for oral exposure")
    record = adjudication.adjudicate(core, _queued(core, task_id, EXCESS, cites=[claim_id]))

    assert record["route"] == "definition_restated" and record["resolution"] == "declare_value_transform"
    assert record["attribute_ref_after"] == "attr_molecular-weight-in-excess-of-the-stated-upper-bound@v2"
    after = criteria.load(core, record["attribute_ref_after"], task_id)
    before = criteria.load(core, record["attribute_ref_before"], task_id)
    assert after["value_transform"] == {"kind": "excess_above", "bound": 500,
                                        "basis": "source_stated_value", "source_refs": [claim_id]}
    assert before.get("value_transform") is None
    assert after["definition"] == before["definition"] == EXCESS["definition"]
    assert _but_for(after) == _but_for(before), "only the transformation was declared"
    assert record["edits"] == [{"target": record["attribute_ref_before"], "field": "value_transform",
                                "target_after": record["attribute_ref_after"], "from": None,
                                "to": after["value_transform"]}]

    # the rule is re-versioned only to read the new attribute: the sweep loads the attribute the rule names
    assert record["rule_ref_after"] == "rule_molecular-weight-in-excess-of-the-stated-upper-bound@v2"
    rule_after = criteria.load(core, record["rule_ref_after"], task_id)
    assert rule_after["attribute_ref"] == record["attribute_ref_after"]
    assert (rule_after["rule_kind"], rule_after["predicate_form"], rule_after["cutoff"],
            rule_after["cutoff_basis"]) == ("preference", "ordering", None, "none_evidence_insufficient")
    assert record["rule_kind_before"] == record["rule_kind_after"] == "preference"
    assert record["scores_candidates"] is True

    # the measured defect, on the compound it was measured on: surufatinib's 480.6 g/mol is inside
    # the bound, so the cell is zero rather than a rank that rewards being small inside the band
    def cell_value(attribute):
        claims = [{"claim_id": "c1", "admission_state": "admitted", "evidence_kind": "database_entry",
                   "determination_basis": "derived", "value": 480.6, "unit": "g/mol"}]
        cell, _ = assessor.assess_cell(candidate={"candidate_id": "surufatinib"}, attribute=attribute,
                                       rule=rule_after, rule_set_ref="rules@v1", claims=claims, resolved=True)
        return cell["value"]

    assert cell_value(before) == 480.6 and cell_value(after) == 0.0


def test_the_transforms_bound_is_traceable_to_a_claim_the_attribute_already_cites_and_one_that_is_not_is_refused(core):
    """An untraceable bound inside a transformation is the arbitrary cutoff the registry refuses
    elsewhere: it is read on every cell the rule scores, and nothing says where the number came from."""
    task_id = _task(core)
    claim_id = _bound_claim(core, task_id, claim_id="claim_mw_bound", value=500, unit="g/mol",
                            quote="an upper bound of 500 g/mol on molecular weight for oral exposure")
    record = adjudication.adjudicate(core, _queued(core, task_id, EXCESS, cites=[claim_id]))
    assert record["cites"]["claim_ids"] == [claim_id] and record["cites"]["field"] == "definition"
    assert record["cites"]["bound_traces"] == {"bound": [{"claim_id": claim_id, "states_it": "claim_value"}]}
    assert claim_id in record["reason_text"]

    untraceable = _queued(core, task_id, dict(
        EXCESS, attribute_id="attr_molecular-weight-in-excess-of-450",
        name="Molecular weight in excess of 450 g per mol",
        definition="the excess in g/mol above 450, zero at or below it"), cites=[claim_id])
    refused = adjudication.adjudicate(core, untraceable)
    assert refused["route"] == "no_authority_available" and refused["edits"] == []
    assert refused["attribute_ref_after"] == refused["attribute_ref_before"] \
        == "attr_molecular-weight-in-excess-of-450@v1"

    uncited = _queued(core, task_id, dict(EXCESS, attribute_id="attr_molecular-weight-in-excess-uncited",
                                          name="Molecular weight in excess of the bound, citing nothing"), cites=[])
    assert adjudication.adjudicate(core, uncited)["route"] == "no_authority_available"


def test_a_definition_that_states_no_bound_is_not_given_a_transform_and_the_item_falls_through(core):
    """A definition that names the raw quantity states no transformation to restate, so the item
    reaches the route it reached before: nothing is invented to fill the gap."""
    task_id = _task(core)
    claim_id = _bound_claim(core, task_id, claim_id="claim_mw_bound", value=500, unit="g/mol",
                            quote="an upper bound of 500 g/mol on molecular weight for oral exposure")
    item = _queued(core, task_id, dict(EXCESS, attribute_id="attr_molecular-weight",
                                       name="Molecular weight of the parent compound",
                                       definition="Molecular weight of the parent compound"), cites=[claim_id])
    assert adjudication.route_preview(core, item)["route"] == "no_authority_available"
    record = adjudication.adjudicate(core, item)
    assert record["route"] == "no_authority_available" and record["cites"] == {} and record["edits"] == []
    with pytest.raises(KeyError):
        criteria.load(core, "attr_molecular-weight@v2", task_id)
    assert adjudication.stated_quantity("Molecular weight of the parent compound") is None
    # a quantity stated in words with no number is a bound nobody can check, so it is not one
    assert adjudication.stated_quantity("the excess above the stated upper bound, zero at or below it") is None


def test_a_definition_stating_a_band_yields_distance_outside_band_with_both_bounds_the_right_way_round(core):
    task_id = _task(core)
    claim_id = _bound_claim(core, task_id, claim_id="claim_lp_band", value=None, unit="log units",
                            quote="oral drugs cluster in a lipophilicity window of 2 to 4 log units")
    record = adjudication.adjudicate(core, _queued(core, task_id, BAND, cites=[claim_id]))

    assert record["route"] == "definition_restated"
    transform = criteria.load(core, record["attribute_ref_after"], task_id)["value_transform"]
    assert transform == {"kind": "distance_outside_band", "low": 2, "high": 4,
                         "basis": "source_stated_value", "source_refs": [claim_id]}
    assert record["cites"]["bound_traces"]["low"] == [{"claim_id": claim_id, "states_it": "claim_quote"}]
    assert record["cites"]["bound_traces"]["high"] == [{"claim_id": claim_id, "states_it": "claim_quote"}]
    # surufatinib's XLogP of 3.4 is inside the band: zero, not a rank
    assert criteria.apply_value_transform(3.4, transform) == 0.0
    assert criteria.apply_value_transform(1.2, transform) == pytest.approx(0.8)
    assert criteria.apply_value_transform(5.1, transform) == pytest.approx(1.1)
    # which end is the low one is the definition's to say, and a definition that says it backwards
    # is one this route cannot read rather than one to repair by swapping the bounds
    assert adjudication.stated_quantity("the distance outside the stated 4 to 2 band") is None
    assert adjudication.stated_quantity("the distance outside the stated 2 to 4 band") == {
        "kind": "distance_outside_band", "low": 2, "high": 4}


def test_the_real_lipophilicity_definition_states_one_band_although_it_spells_out_both_of_its_sides(core):
    """The measured mis-route, pinned on the definition text it was measured from.

    Three readings come out of this one sentence: `distance_outside_band {2, 4}` from the band, and
    `shortfall_below {2}` plus `excess_above {4}` from the clause that decomposes it for the reader.
    Refusing the set sent the item to `no_authority_available` -- demote the rule, stop scoring --
    over a definition whose readings agree: the band's low IS the shortfall's bound, its high IS the
    excess's, and all three readings would have written the same number into the same cells.
    """
    assert adjudication.stated_quantity(LIPOPHILICITY_DEFINITION) == {
        "kind": "distance_outside_band", "low": 2, "high": 4}

    task_id = _task(core)
    claim_id = _bound_claim(core, task_id, claim_id="claim_lp_band", value=None, unit="log units",
                            quote="oral drugs cluster in a lipophilicity window of 2 to 4 log units")
    item = _queued(core, task_id, dict(BAND, definition=LIPOPHILICITY_DEFINITION), cites=[claim_id])
    assert adjudication.route_preview(core, item)["route"] == "definition_restated"
    record = adjudication.adjudicate(core, item)
    assert record["route"] == "definition_restated" and record["resolution"] == "declare_value_transform"
    assert criteria.load(core, record["attribute_ref_after"], task_id)["value_transform"] == {
        "kind": "distance_outside_band", "low": 2, "high": 4,
        "basis": "source_stated_value", "source_refs": [claim_id]}


def test_the_real_molecular_weight_definition_still_states_its_one_excess_and_names_no_band(core):
    """The other manuscript definition, unchanged by the reconciliation: its only reading stands alone.

    It says "band" and it says "below", twice, and neither adds a reading: the forms demand a noun
    that *names* a derived quantity, so "at or below 500 g/mol" is a threshold rather than a
    shortfall, and the band it mentions is never written as "<low> to <high>". So there is nothing
    here to reconcile and nothing that needs reconciling -- the route reads it as it always did.
    """
    assert adjudication.stated_quantity(MOLECULAR_WEIGHT_DEFINITION) == {"kind": "excess_above", "bound": 500}

    task_id = _task(core)
    claim_id = _bound_claim(core, task_id, claim_id="claim_mw_bound", value=500, unit="g/mol",
                            quote="an upper bound of 500 g/mol on molecular weight for oral exposure")
    item = _queued(core, task_id, dict(EXCESS, definition=MOLECULAR_WEIGHT_DEFINITION), cites=[claim_id])
    assert adjudication.route_preview(core, item)["route"] == "definition_restated"
    record = adjudication.adjudicate(core, item)
    assert criteria.load(core, record["attribute_ref_after"], task_id)["value_transform"] == {
        "kind": "excess_above", "bound": 500, "basis": "source_stated_value", "source_refs": [claim_id]}


def test_readings_that_do_not_reconcile_to_one_band_are_refused_as_they_were_before():
    """Each way two readings can disagree, and each one still leaves the item for a person.

    The reconciliation is exact and only inward: a band the definition restates side by side is one
    quantity, and everything else here states two. A bound inside a transformation is read on every
    cell the rule scores, so a definition this cannot be sure of must not be guessed at.
    """
    # two bands: which pair of numbers every cell is measured against is exactly what is unstated
    assert adjudication.stated_quantity(
        "the distance outside the stated 2 to 4 band, and the distance outside the 1 to 5 band") is None
    # a one-sided bound that is not the band's own end on that side -- 1 is not the band's low, and a
    # cell scored against the wrong one is wrong by that whole difference
    assert adjudication.stated_quantity(
        "the distance outside the stated 2 to 4 band: the shortfall below 1 for a more polar molecule") is None
    assert adjudication.stated_quantity(
        "the distance outside the stated 2 to 4 band: the excess above 7 for a more lipophilic molecule") is None
    # two one-sided kinds and no band to reconcile them into: calling 2 and 4 the ends of one band
    # would be this module's reading of the definition rather than the definition's own statement
    assert adjudication.stated_quantity(
        "the shortfall below 2 for a more polar molecule, and the excess above 4 for a more lipophilic one") is None
    # more than one bound for the same one-sided kind: at most one of them can be the band's low
    assert adjudication.stated_quantity(
        "the distance outside the stated 2 to 4 band: the shortfall below 2, or the shortfall below 1") is None
    assert adjudication.stated_quantity("the shortfall below 2, or the shortfall below 1") is None
    # a band back to front is still unreadable once reconciled, which is where that refusal now runs
    assert adjudication.stated_quantity(
        "the distance outside the stated 4 to 2 band: the shortfall below 4, and the excess above 2") is None


def test_restating_a_definition_calls_no_model(core):
    """The authority is text already promoted into the store, so there is nothing to ask anyone.

    Asserted on the adapters rather than by withholding the roster: the route must stay deterministic
    even in a run that has models available, because a model asked what a definition means would be
    the judgement this route claims not to add.
    """
    task_id = _task(core)
    claim_id = _bound_claim(core, task_id, claim_id="claim_mw_bound", value=500, unit="g/mol",
                            quote="an upper bound of 500 g/mol on molecular weight for oral exposure")
    item = _queued(core, task_id, EXCESS, cites=[claim_id])
    roster = _roster(lambda request: pytest.fail(f"route 5 asked the {request.role} a question"))

    preview = adjudication.route_preview(core, item)
    record = adjudication.adjudicate(core, item, roster=roster)
    assert preview["route"] == record["route"] == "definition_restated"
    assert all(adapter.requests == [] for adapter in roster.adapters.values())
    assert record["actor"] == adjudication.MACHINE and record["actor"]["kind"] == "system"
    assert record["verdict"] is None and record["independence"] is None and record["cited_claim_ids"] == []
    assert record["approval_kind"] == "agent_verdict" and record["confirmed_by_a_person"] is False
    assert not core.artifacts.of_kind("expert_decision")


def test_a_route_preview_over_the_two_manuscript_rule_shapes_names_the_definition_route(core):
    """The measured mis-route, pinned on the field values it was measured from.

    `route_preview` over the twelve open items of the manuscript task returned
    `no_authority_available` for these two -- "demote the rule to an exploratory consideration, so it
    stops scoring". Neither is an expert-set cutoff: both are preferences with an ordering predicate,
    no cutoff and `cutoff_basis: none_evidence_insufficient`, so `needs_expert` is False for both and
    nothing an expert set is missing. What was missing is the transformation their own definitions
    describe, which is why demoting them answered a question nobody had asked.
    """
    task_id = _task(core)
    mw = _queued(core, task_id, EXCESS, cites=[_bound_claim(
        core, task_id, claim_id="claim_mw_bound", value=500, unit="g/mol",
        quote="an upper bound of 500 g/mol on molecular weight for oral exposure")])
    lipophilicity = _queued(core, task_id, BAND, cites=[_bound_claim(
        core, task_id, claim_id="claim_lp_band", value=None, unit="log units",
        quote="oral drugs cluster in a lipophilicity window of 2 to 4 log units")])

    assert [item["subject"]["id"] for item in (mw, lipophilicity)] == [
        "rule_molecular-weight-in-excess-of-the-stated-upper-bound@v1",
        "rule_distance-of-computed-lipophilicity-outside-the-stated-band@v1"]
    for item in (mw, lipophilicity):
        rule = criteria.load(core, item["subject"]["id"], task_id)
        assert (rule["rule_kind"], rule["predicate_form"], rule["cutoff"], rule["cutoff_basis"]) == \
               ("preference", "ordering", None, "none_evidence_insufficient")
        # the authority table reads the whole decision-bearing object now, transform bounds included
        assert criteria.needs_expert(rule, criteria.load(core, rule["attribute_ref"], task_id)) is False
        assert item["why_expert_required"] == QUEUE_TEXT
        preview = adjudication.route_preview(core, item)
        assert preview["route"] == "definition_restated", item["subject"]["id"]
        assert preview["route_label"] == "restates the attribute's own definition"
        assert "declare the transformation" in preview["would"] and preview["why_not"] is None


# --- route 6: a declared interpretation of a bound ---------------------------------------------------

# The criterion shape route 6 exists for, and it is the shape the live derivation produced 29 times
# out of 33: a cutoff whose number the cited passage states, a passage that reports a measurement
# rather than a screening threshold, and the step from the one to the other declared. Before this
# route the honest declaration was also the one that could never gate: of 35 derived criteria exactly
# one carried a cutoff, and that one restated a task constraint.
EXPOSURE_RULE = {"rule_kind": "preference", "predicate_form": "threshold",
                 "cutoff": {"comparator": ">=", "value": 12, "unit": "h"},
                 "cutoff_basis": "source_stated_value"}
INTERPRETATION = {
    "measurement": "the reported series sustained once-daily dosing at a terminal half-life of 12 h",
    "inference": "at_least_the_reported_value",
    "population_rationale": "the series reported here is orally dosed inhibitors on a once-daily schedule, which "
                            "is the schedule the objective asks for, so a shorter exposure cannot sustain the "
                            "dosing this screen is built around",
}


def _interpreted(core, task_id: str, *, rule: dict | None = None,
                 interpretation: dict | None = INTERPRETATION) -> tuple[str, str]:
    """Propose a criterion whose cutoff rests on a reported measurement, and raise its queue item.

    The support report is passed to `criteria.propose`, as the derivation stages pass it: the bound is
    `interpretation_added`, so the authority table asks for a decision and the item exists to resolve.
    """
    claim_id = _claim(core, task_id)
    attribute = dict(HALF_LIFE, rationale=RATIONALE, supporting_claim_refs=[claim_id])
    record = {"parameter_path": "rule.cutoff.value", "claim_id": claim_id, "source_number": 12,
              "source_unit": "h", "conversion": {"kind": "identity"}, "statement_kind": "reports_measurement",
              "applicability_rationale": "the passage is about orally dosed inhibitors, which is this task's "
                                         "candidate population"}
    if interpretation is not None:
        record["interpretation"] = interpretation
    rule = dict(rule or EXPOSURE_RULE, bound_support=[record])
    claims = [c for c in ledger.claims(core, [task_id]) if c["claim_id"] == claim_id]
    _, rule_ref = criteria.propose(core, task_id, attribute, rule, by=AGENT,
                                   support=bound_support.validate(attribute, rule, claims=claims))
    return rule_ref, claim_id


def _grants(verdict: str, *, requirement: bool = False, reasoning: str = "the quote states 12 h for this series"):
    def script(request):
        return {"verdict": verdict, "reasoning": reasoning, "cited_claim_ids": [],
                "property_is_a_requirement": requirement}
    return script


def test_a_cutoff_resting_on_a_reported_measurement_with_a_declared_interpretation_can_be_granted_and_then_scores(core):
    """The gap this route closes, end to end on the shape that measured it.

    The passage reports a half-life; it states no screening threshold, and the record says so. What
    the record adds is the step -- the measurement, the direction of the inference and why it holds
    for this population -- and an agent on the `adjudicator` role grants it. The rule is unchanged by
    the grant: same kind, same predicate, same cutoff, so the cell is compared against 12 h.
    """
    task_id = _task(core)
    rule_ref, claim_id = _interpreted(core, task_id)
    item = _item(core, task_id, rule_ref)
    assert "reads 12 as a decision line that its source does not state as one" in item["why_expert_required"]
    assert adjudication.route_preview(core, item)["route"] == "bound_interpretation_granted"

    record = adjudication.adjudicate(core, item, roster=_roster(_grants("grant_bound")))
    assert record["route"] == "bound_interpretation_granted" and record["resolution"] == "approve"
    assert record["verdict"] == "grant_bound" and record["scores_candidates"] is True
    assert record["grants"]["granted"] is True
    assert record["grants"]["parameter_paths"] == ["rule.cutoff.value"]
    assert record["grants"]["inferences"] == {"rule.cutoff.value": "at_least_the_reported_value"}
    assert record["rule_ref_after"] == rule_ref == record["rule_ref_before"] and record["edits"] == []

    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    (entry,) = rules["entries"]
    assert entry["rule_ref"] == rule_ref and entry["cutoff_basis"] == "source_stated_value"
    assert entry["authority"] == "machine_adjudication" and entry["confirmed_by"] == record["adjudication_id"]
    assert rules["bounds_granted"] == [{"rule_ref": rule_ref, "attribute_ref": "attr_terminal-half-life@v1",
                                        "paths": ["rule.cutoff.value"], "rule_kind": "preference",
                                        "adjudication_id": record["adjudication_id"],
                                        "excludes_candidates": False}]
    # and the cutoff is what the cell is now compared against, which is the whole point of granting it
    rule = criteria.load(core, rule_ref, task_id)
    assert rule["cutoff"] == {"comparator": ">=", "value": 12, "unit": "h"}
    short = [{"claim_id": claim_id, "admission_state": "admitted", "evidence_kind": "peer_reviewed",
              "determination_basis": "measured", "value": 4, "unit": "h"}]
    cell, _ = assessor.assess_cell(candidate={"candidate_id": "cand_x"},
                                   attribute=criteria.load(core, rule["attribute_ref"], task_id), rule=rule,
                                   rule_set_ref=rules["rule_set_ref"], claims=short, resolved=True)
    assert cell["verdict"] == "fail"


def test_the_same_cutoff_without_a_declared_interpretation_is_not_granted_and_falls_back_to_ranking(core):
    """Nobody can grant what nobody has stated, and the fallback is the one that was already there.

    The criterion is the one above with its `interpretation` left out. There is nothing for an
    adjudicator to read, so route 6 does not fire at all -- no model is asked -- and the strict gate
    does what it did before: it withholds the *cutoff* and lets the measurement go on ranking
    candidates in the attribute's declared direction, which asserts no bound.
    """
    task_id = _task(core)
    rule_ref, claim_id = _interpreted(core, task_id, interpretation=None)
    attribute = criteria.load(core, "attr_terminal-half-life@v1", task_id)
    rule = criteria.load(core, rule_ref, task_id)
    claims = ledger.claims(core, [task_id])
    report = bound_support.validate(attribute, rule, claims=claims)
    assert report["states"] == {"rule.cutoff.value": "interpretation_added"}
    assert report["grantable_paths"] == [] and report["granted_paths"] == []
    assert adjudication.grantable_interpretation(rule, attribute, claims) is None
    assert adjudication.route_preview(core, _item(core, task_id, rule_ref))["route"] == "no_authority_available"

    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(
        core, task_id, by=OPERATOR, allow_pending=True, require_bound_support=True))
    (withheld,) = rules["bounds_withheld"]
    assert withheld["rule_ref"] == rule_ref and withheld["fallback"] == "ranked_without_the_withheld_cutoff"
    (entry,) = rules["entries"]
    assert entry["rule_ref"] == rule_ref and entry["cutoff_basis"] == "none_evidence_insufficient"
    assert rules["bounds_granted"] == [] and rules["acceptance_label"] == "exploratory"


def test_a_granted_bound_is_recorded_as_interpreted_and_never_as_a_sourced_threshold(core):
    """`sourced_threshold` keeps meaning "the passage stated this cutoff", so a grant gets its own state.

    Everything the record said before the grant it still says: the passage reports a measurement, the
    number traces to the claim's own value, and the line is the criterion's reading. What changed is
    who stands behind that reading -- an agent -- and the gate a sourced or frozen set confirms with
    still refuses to call it sourced.
    """
    task_id = _task(core)
    rule_ref, claim_id = _interpreted(core, task_id)
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref),
                                     roster=_roster(_grants("grant_bound")))
    attribute = criteria.load(core, "attr_terminal-half-life@v1", task_id)
    rule = criteria.load(core, rule_ref, task_id)
    claims = ledger.claims(core, [task_id])

    granted = adjudication.granted_bounds(record)
    assert list(granted) == ["rule.cutoff.value"]
    assert granted["rule.cutoff.value"]["approval_kind"] == "agent_verdict"
    report = bound_support.validate(attribute, rule, claims=claims, grants=granted)
    (bound,) = report["bounds"]
    assert bound["state"] == "interpretation_granted" != "sourced_threshold"
    assert bound["semantic_support"] == "reports_measurement" and bound["trace_kind"] == "claim_value"
    assert bound["interpretation"] == "declared" and bound["authority"] == "agent_granted"
    assert bound["granted_by"]["adjudication_id"] == record["adjudication_id"]
    assert report["granted_paths"] == ["rule.cutoff.value"] and report["review_paths"] == []

    # nothing read off the rule can produce it: the grant lives in the `adj_` record, not in the
    # support record the proposer wrote, so a criterion cannot grant its own interpretation
    assert bound_support.validate(attribute, rule, claims=claims)["states"] == {
        "rule.cutoff.value": "interpretation_added"}
    forged = dict(rule, bound_support=[dict(rule["bound_support"][0], interpretation_granted=True,
                                            state="sourced_threshold")])
    assert bound_support.validate(attribute, forged, claims=claims)["states"] == {
        "rule.cutoff.value": "interpretation_added"}

    strict = criteria.rule_set(core, task_id, criteria.confirm_rule_set(
        core, task_id, by=OPERATOR, require_bound_support=True))
    assert [e["rule_ref"] for e in strict["bounds_withheld"]] == [rule_ref], \
        "the sourced gate refuses to call a granted bound a threshold its source states"


def test_a_granted_hard_exclusion_is_named_in_the_rule_set_and_keeps_the_label_exploratory(core):
    """Granting an exclusion is the loudest thing this module can do, so it is asked and recorded twice.

    Route 6 runs ahead of route 3 for a rule that declares an interpretation, because refusing the
    grant lands on route 3's own outcome anyway. A granted bound alone does not keep the exclusion:
    the adjudicator answers separately whether the evidence makes the property a requirement, and
    silence is a no.
    """
    task_id = _task(core)
    hard = dict(EXPOSURE_RULE, rule_kind="hard_exclusion", predicate_form="threshold")
    rule_ref, _claim_id = _interpreted(core, task_id, rule=hard)
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref),
                                     roster=_roster(_grants("grant_bound", requirement=True)))
    assert record["route"] == "bound_interpretation_granted" and record["resolution"] == "approve"
    assert record["rule_kind_before"] == record["rule_kind_after"] == "hard_exclusion"
    assert record["grants"]["hard_exclusion"] is True and "the exclusion stands" in record["reason_text"]

    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    (granted,) = rules["bounds_granted"]
    assert granted["rule_ref"] == rule_ref and granted["excludes_candidates"] is True
    assert rules["acceptance_label"] == "exploratory"
    assert any("score on a bound an agent granted on a declared interpretation" in reason
               for reason in rules["acceptance_reasons"]), rules["acceptance_reasons"]
    assert any("remove candidates on such a bound" in reason for reason in rules["acceptance_reasons"])
    assert rules["machine_adjudicated"] == [rule_ref]
    # the board says a machine granted it, which is what makes an exclusion nobody confirmed readable
    summary = leaderboard._review_summary(rules)
    assert summary["machine_adjudicated_n"] == 1 and "no person has confirmed them" in summary["note"]
    # and it really does exclude: that is why the grant had to be a second question
    failing = [{"attribute_ref": "attr_terminal-half-life@v1", "rule_kind": "hard_exclusion", "verdict": "fail"}]
    assert assessor.roll_up("cand_x", failing, coverage_floor=1.0,
                            recommended_requires_hd=False)["state"] == "rejected"

    # the same grant without that second answer: the bound scores, the exclusion does not stand
    other = _task(core)
    other_ref, _ = _interpreted(core, other, rule=dict(hard, rule_id="rule_exposure_hard"))
    softer = adjudication.adjudicate(core, _item(core, other, other_ref),
                                     roster=_roster(_grants("grant_bound")))
    assert softer["grants"]["granted"] is True and softer["grants"]["hard_exclusion"] is False
    assert softer["resolution"] == "demote_to_preference" and softer["rule_kind_after"] == "preference"
    assert criteria.load(core, softer["rule_ref_after"], other)["cutoff"]["value"] == 12


def test_a_refused_bound_leaves_the_criterion_ranking_on_the_measurement_and_asserting_no_cutoff(core):
    """Refusing is a normal answer, and it falls where the support contract already put it.

    Withholding a cutoff and withholding a measurement are different acts: the rule gives up the
    cutoff and the support record that backed it, keeps its direction, and goes on ranking. The
    refused version and the reason stay in the journal.
    """
    task_id = _task(core)
    rule_ref, _claim_id = _interpreted(core, task_id)
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref), roster=_roster(
        _grants("refuse_bound", reasoning="the series was dosed once daily at a higher dose than this screen "
                                          "assumes, so 12 h is not the line for this population")))
    assert record["verdict"] == "refuse_bound" and record["resolution"] == "withdraw_the_cutoff"
    assert record["grants"]["granted"] is False
    assert record["grants"]["parameter_paths_refused"] == ["rule.cutoff.value"]
    assert "ranking candidates on the measurement" in record["reason_text"]
    assert record["rule_ref_after"] == "rule_terminal-half-life@v2"
    assert record["edits"] == [{"target": rule_ref, "target_after": record["rule_ref_after"], "field": "cutoff",
                               "from": {"comparator": ">=", "value": 12, "unit": "h"}, "to": None}]

    after = criteria.load(core, record["rule_ref_after"], task_id)
    assert (after["rule_kind"], after["predicate_form"], after["cutoff"], after["cutoff_basis"]) == (
        "preference", "ordering", None, "none_evidence_insufficient")
    assert after["bound_support"] == [], "the support record goes with the cutoff it supported"
    assert record["scores_candidates"] is True
    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    assert rules["bounds_granted"] == [] and rules["machine_adjudicated"] == [record["rule_ref_after"]]
    assert criteria.load(core, rule_ref, task_id)["cutoff"]["value"] == 12, \
        "the refused version is still in the journal"


def test_the_grant_is_recorded_as_an_agents_and_creates_no_expert_decision(core):
    """The invariant the whole module is built around, on the one route that lets a rule gate.

    A grant is an agent's verdict and the record says so in the same field an `hd_` uses to say the
    opposite. The adjudicator is blind to the proposer's rationale, exactly as the critic is, and the
    declared interpretation is shown because it is the thing under judgement.
    """
    task_id = _task(core)
    rule_ref, claim_id = _interpreted(core, task_id)
    seen = {}

    def script(request):
        seen["content"] = request.messages[0]["content"]
        seen["role"] = request.role
        return {"verdict": "grant_bound", "reasoning": "the quote states 12 h for the series it reports",
                "cited_claim_ids": [claim_id, "claim_that_was_never_offered"]}

    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref), roster=_roster(script))
    assert record["adjudication_id"].startswith("adj_") and "decision_id" not in record
    assert record["actor"]["kind"] == "agent" and record["actor"]["role"] == "adjudicator"
    assert record["approval_kind"] == "agent_verdict" != "human_scientific_approval"
    assert record["authority"] == "machine_adjudication" and record["confirmed_by_a_person"] is False
    assert not core.artifacts.of_kind("expert_decision"), "no grant may leave an hd_ behind"
    assert record["cited_claim_ids"] == [claim_id]
    assert record["independence"]["adjudicator_saw_proposer_rationale"] is False
    assert record["independence"]["adjudicator_family"] == "family_c"

    assert seen["role"] == "adjudicator"
    assert RATIONALE not in seen["content"], "the grant is judged blind, as the critic judges"
    assert "expected_change" not in seen["content"]
    assert INTERPRETATION["population_rationale"] in seen["content"], "the declaration is what is being judged"
    assert QUOTE in seen["content"]

    resolved = _item(core, task_id, rule_ref)
    assert resolved["state"] == "machine_adjudicated" and "decision_id" not in resolved
    with pytest.raises(review.ReviewError) as after:
        review.decide(core, resolved, decision="approve", actor=EXPERT, reason_text="", entry="interactive")
    assert after.value.code == "rejected_not_permitted_in_state"


def test_a_grant_with_no_adjudicator_to_call_is_left_open_rather_than_resolved(core):
    """A judgement needs somebody to make it: with no roster the item stays on the queue for a person,
    exactly as a proposer/critic dispute does."""
    task_id = _task(core)
    rule_ref, _claim_id = _interpreted(core, task_id)
    (left,) = adjudication.adjudicate_open(core, task_id)
    assert left["route"] is None and "no model roster" in left["left_open_because"]
    assert "declared interpretation of rule.cutoff.value" in left["left_open_because"]
    assert _item(core, task_id, rule_ref)["state"] == "open"


# --- what the rule set, the board and the pages then say ------------------------------------------------

def test_a_rule_set_containing_any_machine_adjudication_is_exploratory_and_says_so(core):
    task_id = _task(core)
    _, adjudicated_ref = criteria.propose(core, task_id, MW, dict(MW_RULE, cutoff_basis="expert_set"), by=AGENT)
    criteria.propose(core, task_id, HALF_LIFE, {"rule_kind": "preference", "predicate_form": "ordering",
                                                "cutoff": None, "cutoff_basis": "none_evidence_insufficient"},
                     by=AGENT)
    record = adjudication.adjudicate(core, _item(core, task_id, adjudicated_ref))
    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))

    assert rules["machine_adjudicated"] == [record["rule_ref_after"]]
    assert rules["acceptance_label"] == "exploratory"
    assert any("1 rules were adjudicated by an agent; no person has confirmed them" in reason
               for reason in rules["acceptance_reasons"]), rules["acceptance_reasons"]
    by_ref = {e["rule_ref"]: e for e in rules["entries"]}
    assert by_ref[record["rule_ref_after"]]["authority"] == "machine_adjudication"
    assert by_ref[record["rule_ref_after"]]["confirmed_by"] == record["adjudication_id"]
    assert by_ref["rule_terminal-half-life@v1"]["authority"] == "trigger_table"

    summary = leaderboard._review_summary(rules)
    assert summary["machine_adjudicated_n"] == 1 and summary["expert_confirmed_rules"] == []
    assert "no person has confirmed them" in summary["note"]


def test_a_later_version_of_an_adjudicated_rule_does_not_inherit_the_earlier_adjudication(core):
    """A later derivation round promotes the same criterion again, proposing a new version and
    raising a fresh item. Keyed by the rule's base id rather than by the version it left standing,
    the adjudication of @v1 confirmed @v3 as well -- a rule nothing had looked at entering a set on
    another rule's authority."""
    task_id = _task(core)
    criteria.propose(core, task_id, HALF_LIFE, {"rule_kind": "preference", "predicate_form": "ordering",
                                                "cutoff": None, "cutoff_basis": "none_evidence_insufficient"},
                     by=AGENT)
    _, first = criteria.propose(core, task_id, MW, dict(MW_RULE, cutoff_basis="expert_set"), by=AGENT)
    record = adjudication.adjudicate(core, _item(core, task_id, first))
    assert record["rule_ref_after"] == "rule_molecular-weight@v2"

    criteria.propose(core, task_id, MW, dict(MW_RULE, cutoff_basis="expert_set"), by=AGENT)   # a later round
    with pytest.raises(criteria.InvariantViolation, match="await an expert decision"):
        criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR,
                                                                      allow_pending=True))
    assert rules["pending"] == ["rule_molecular-weight@v3"] and rules["machine_adjudicated"] == []
    assert [e["rule_ref"] for e in rules["entries"]] == ["rule_terminal-half-life@v1"]


def test_an_expert_confirmed_rule_set_still_reads_as_prespecified_and_names_the_person(core):
    """The counterpart: nothing about the new path may change what a set an expert confirmed says."""
    task_id = _task(core)
    _, rule_ref = criteria.propose(core, task_id, MW, dict(MW_RULE, cutoff_basis="expert_set"), by=AGENT)
    review.decide(core, _item(core, task_id, rule_ref), decision="approve", actor=EXPERT, reason_text="",
                  entry="interactive", historical_list_exposure="not_exposed")
    rules = criteria.rule_set(core, task_id, criteria.confirm_rule_set(core, task_id, by=OPERATOR))
    assert rules["acceptance_label"] == "prespecified" and rules["machine_adjudicated"] == []
    assert rules["entries"][0]["authority"] == "human_scientific_approval"
    assert leaderboard._review_summary(rules)["note"] is None


def test_the_review_page_shows_the_route_for_an_open_item_and_who_resolved_a_closed_one(tmp_path):
    root = tmp_path / "store"
    with Core.open(root) as core:
        task_id = _task(core)
        _, resolved_ref = criteria.propose(core, task_id, MW, dict(MW_RULE, cutoff_basis="expert_set"), by=AGENT)
        criteria.propose(core, task_id, _derived(ROUTE, task_id, "constraints[0]"), ROUTE_RULE, by=AGENT)
        adjudication.adjudicate(core, _item(core, task_id, resolved_ref))
    data = json.loads(Workbench(root).handle("GET", "/api/review").body)

    (pending,) = data["pending"]
    assert pending["subject_id"] == "rule_oral-administration-on-record@v1"
    assert pending["route"] == "task_constraint_restated"
    assert pending["route_label"] == "restates the task's own constraint"
    assert "citing the task-context field" in pending["would"]

    assert data["machine_adjudicated_n"] == 1 and data["decided"] == []
    (done,) = data["machine_adjudicated"]
    assert done["route"] == "no_authority_available" and done["confirmed_by_a_person"] is False
    assert done["authority"] == "adjudicated by an agent; no person confirmed it"
    assert done["adjudication_id"].startswith("adj_")
    assert "no person confirmed them" in data["machine_adjudication_note"]
    shown = Workbench(root).handle("GET", "/review").body.decode("utf-8")
    assert "adjudicated by an agent; no person confirmed it" in shown and "task_constraint_restated" in shown


def test_the_board_names_the_rules_an_agent_adjudicated_beside_its_exploratory_label(tmp_path):
    """The whole chain in one run: a queue nobody answered, a board that still says so."""
    from mas.ui import views
    from tests.test_run_end_to_end import BIO, BIO_RULE, MW as E2E_MW, MW_RULE as E2E_MW_RULE, SPEC as E2E_SPEC
    from tests.test_run_end_to_end import OPERATOR as E2E_OPERATOR, make_controller

    root = tmp_path / "store"
    with Core.open(root) as core:
        task_id, _ = task.record_version(core, E2E_SPEC, by=E2E_OPERATOR)
        criteria.propose(core, task_id, E2E_MW, E2E_MW_RULE, by=AGENT)            # hard exclusion, expert_set
        criteria.propose(core, task_id, BIO, dict(BIO_RULE, cutoff_basis="source_stated_value"), by=AGENT)
        (record,) = adjudication.adjudicate_open(core, task_id)
        criteria.confirm_rule_set(core, task_id, by=E2E_OPERATOR)
        make_controller(core).start(task_id, by=E2E_OPERATOR, sweep_seed=7)
        board = views.board(core, task_id)

    assert board["acceptance_label"] == "exploratory"
    assert any("adjudicated by an agent" in reason for reason in board["acceptance_reasons"])
    assert board["human_review_summary"]["machine_adjudicated_n"] == 1
    assert board["human_review_summary"]["machine_adjudicated_rules"] == [record["rule_ref_after"]]
    assert board["machine_adjudicated_rules"] == [
        {"rule_ref": record["rule_ref_after"], "rule_kind": "exploratory_consideration",
         "authority": "adjudicated by an agent; no person confirmed it"}]
    # the demoted exclusion excluded nobody: every candidate is still on the board
    assert not any(row["state"] == "rejected" for row in board["rows"])


# --- the setting -----------------------------------------------------------------------------------------

def test_adjudicating_without_a_person_is_off_until_the_run_says_there_is_nobody_to_ask():
    off = config_mod.resolve(project_file=None, environ={})
    assert off["interaction.autonomous_adjudication"] is False
    assert off.sources["interaction.autonomous_adjudication"] == "default"

    autonomous = config_mod.resolve(project_file=None, environ={}, overrides={"interaction.mode": "autonomous",
                                                                             "interaction.checkpoints": ""})
    assert autonomous["interaction.autonomous_adjudication"] is True
    assert autonomous.sources["interaction.autonomous_adjudication"] == "override"
    assert config_mod.resolve(preset="quick", project_file=None, environ={})["interaction.autonomous_adjudication"]

    kept = config_mod.resolve(project_file=None, environ={},
                              overrides={"interaction.mode": "autonomous", "interaction.checkpoints": "",
                                         "interaction.autonomous_adjudication": "false"})
    assert kept["interaction.autonomous_adjudication"] is False, "an explicit value outranks the implication"


def test_a_run_that_stops_for_a_person_may_not_also_resolve_the_queue_without_one():
    with pytest.raises(config_mod.ConfigError) as error:
        config_mod.resolve(project_file=None, environ={}, overrides={"interaction.autonomous_adjudication": "true"})
    assert "interaction.checkpoints" in str(error.value) and "formality" in str(error.value)
    config_mod.resolve(project_file=None, environ={},
                       overrides={"interaction.autonomous_adjudication": "true", "interaction.checkpoints": ""})


def test_an_expert_arriving_later_can_withdraw_the_agents_verdict_and_decide_it_themselves(core):
    """Running with nobody to ask must not be a one-way door.

    `review.decide` refuses an item whose state is not open, which is what stops an adjudication
    being re-badged as an expert decision -- but it also left an expert arriving later unable to
    overrule the agent on anything already resolved. Withdrawing is not deciding: it raises a fresh
    item and leaves the subject unresolved, with the adjudication still in the journal as what the
    system did while no person was available.
    """
    task_id = _task(core)
    _, rule_ref = criteria.propose(core, task_id, MW, dict(MW_RULE, cutoff_basis="expert_set"), by=AGENT)
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref))
    resolved = _item(core, task_id, rule_ref)
    assert resolved["state"] == "machine_adjudicated"

    fresh_id = adjudication.reopen(core, resolved, by=OPERATOR, reason_text="a pharmacologist is available now")
    items = review.items(core, [task_id])
    assert items[resolved["item_id"]]["state"] == "withdrawn"
    fresh = items[fresh_id]
    assert fresh["state"] == "open" and fresh["subject"] == resolved["subject"]
    assert record["adjudication_id"] in fresh["why_expert_required"] or \
        record["route"] in fresh["why_expert_required"]

    decision = review.decide(core, fresh, decision="reject", actor=EXPERT, reason_text="the cutoff is not supportable",
                             entry="interactive", historical_list_exposure="not_exposed")
    assert decision["decision_id"].startswith("hd_") and decision["actor"]["kind"] == "human"
    # the agent's record survives the override: the journal keeps both
    assert [r["adjudication_id"] for r in adjudication.records(core, task_id)] == [record["adjudication_id"]]


def test_an_item_a_person_already_decided_cannot_be_reopened_as_if_an_agent_had_done_it(core):
    task_id = _task(core)
    _, rule_ref = criteria.propose(core, task_id, MW, dict(MW_RULE, cutoff_basis="expert_set"), by=AGENT)
    item = _item(core, task_id, rule_ref)
    review.decide(core, item, decision="approve", actor=EXPERT, reason_text="", entry="interactive",
                  historical_list_exposure="not_exposed")
    with pytest.raises(adjudication.AdjudicationError, match="not machine-adjudicated"):
        adjudication.reopen(core, _item(core, task_id, rule_ref), by=OPERATOR, reason_text="second thoughts")


def test_withdrawing_an_agents_verdict_needs_a_reason(core):
    task_id = _task(core)
    _, rule_ref = criteria.propose(core, task_id, MW, dict(MW_RULE, cutoff_basis="expert_set"), by=AGENT)
    adjudication.adjudicate(core, _item(core, task_id, rule_ref))
    with pytest.raises(adjudication.AdjudicationError, match="say why"):
        adjudication.reopen(core, _item(core, task_id, rule_ref), by=OPERATOR, reason_text="  ")


def test_the_expert_decision_guard_is_a_process_boundary_and_not_a_security_boundary(core):
    """F7, pinned as a known limitation rather than left as an unexamined claim.

    The project repeatedly asserted that no agent can create an expert decision. The guard in
    `review.decide` does reject a non-human actor and non-interactive entry, and that is what stops
    a model's structured output becoming an approval. But both fields are caller-supplied strings,
    so anything able to call this function can satisfy them. This test asserts BOTH halves, so the
    day someone enforces an authenticated principal it fails and has to be rewritten -- which is
    the point of writing it down.
    """
    from mas.core import review
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    item = {"item_id": "q_f7", "state": "open", "stream_id": task_id,
            "subject": {"kind": "rule_version", "id": "rule_anything@v1"}}

    # the half that holds: an agent actor, and a human actor without interactive entry
    with pytest.raises(review.ReviewError, match="never by agents"):
        review.decide(core, item, decision="approve", actor=actor("agent", "proposer", "proposer"),
                      reason_text="", entry="interactive")
    with pytest.raises(review.ReviewError, match="interactive confirmation"):
        review.decide(core, item, decision="approve", actor=OPERATOR, reason_text="", entry="scripted")

    # the half that does not hold: the fields are unauthenticated, so a direct call satisfies them
    forged = review.decide(core, item, decision="approve",
                           actor={"id": "not-a-person", "kind": "human", "role": "expert"},
                           reason_text="", entry="interactive")
    assert forged["approval_kind"] == "human_scientific_approval"
    assert forged["decision_id"].startswith("hd_"), (
        "a direct caller can still mint an expert decision; the guard is a process boundary, and "
        "the public claim must stay narrow until an authenticated principal replaces it")


# --- route 7: the predictor's own decision boundary ---------------------------------------------

HERG = {"name": "Predicted hERG block", "measurement_kind": "quantitative", "unit": "probability",
        "definition": "The panel's predicted probability that the compound blocks the hERG channel",
        "direction": "lower_better", "acceptable_value_sources": ["model_prediction"], "aggregation": "median",
        "acceptable_determination_bases": ["predicted"],
        "evidence_request": {"capability": "predicted_property_lookup", "question_kind": "admet_prediction",
                             "identifier_scheme": "inchikey", "parameters": {"endpoint": "hERG"}}}
HERG_RULE = {"rule_kind": "preference", "predicate_form": "threshold",
             "cutoff": {"comparator": "<", "value": 0.5, "unit": "probability"},
             "cutoff_basis": "model_decision_boundary", "on_missing": "unknown_no_penalty"}
HALF_LIFE_PREDICTED = {
    "name": "Predicted half-life", "measurement_kind": "quantitative", "unit": "h",
    "definition": "The panel's predicted terminal half-life", "direction": "higher_better",
    "acceptable_value_sources": ["model_prediction"], "aggregation": "median",
    "acceptable_determination_bases": ["predicted"],
    "evidence_request": {"capability": "predicted_property_lookup", "question_kind": "admet_prediction",
                         "identifier_scheme": "inchikey", "parameters": {"endpoint": "Half_Life_Obach"}}}


def _provenance(endpoint: str, metric: dict, *, task_type: str = "classification", boundary=0.5,
                unit: str = "probability") -> dict:
    """The provenance a predictor attaches to each value it returns (`adapters/predict/admet.py`'s
    `provenance`), reduced to the keys this route reads (`adjudication.PROVENANCE_KEYS`)."""
    return {"predictor_package": "admet-ai", "predictor_version": "1.3.0", "endpoint": endpoint,
            "endpoint_name": endpoint, "task_type": task_type, "holdout_metric": metric,
            "decision_boundary": boundary, "unit": unit, "training_dataset": endpoint, "training_rows": 648,
            "model": "Chemprop-RDKit ensemble over the TDC dataset of the same id"}


def _prediction(core, task_id: str, attr_ref: str, *, value, unit: str, conditions: dict,
                basis: str = "predicted", stream: str = "run_predict") -> str:
    """One predicted value for one candidate, recorded as the sweep records it: in the run's own
    stream, with the tool's provenance in `conditions` (`evidence.claims_from_tool_result`)."""
    if not core.journal.replay(stream):
        core.journal.append(stream, "run.created", actor=OPERATOR, payload={"for": "predicted values"})
    return ledger.record_claim(core, stream, {
        "source_ref": f"src_db_tool_predict_admet_panel_{conditions['endpoint']}",
        "candidate_ref": "cand_1", "attribute_ref": attr_ref,
        "location": {"location_kind": "record_field", "locator_value": f"{conditions['endpoint']}#value",
                     "quoted_span": str(value), "span_checked_against_source": True},
        "claim_text": f"{conditions['endpoint']} = {value} {unit}", "claim_text_marker": "verbatim",
        "normalized_statement": f"{conditions['endpoint']} = {value} {unit}", "claim_type": "data_derived",
        "evidence_kind": "model_prediction", "determination_basis": basis, "value": value, "unit": unit,
        "polarity": "supports", "scope_match": "direct", "reading_depth": "not_read",
        "conditions": conditions}, by=AGENT, admission_state="admitted", admission_reasons=["identifier_grounded"])


def test_a_well_measured_classifier_may_gate_on_the_boundary_its_own_record_documents(core):
    """The route the basis needed. `model_decision_boundary` reaches `authority_basis /
    decision_required` and no claim in the ledger states 0.5, so with expert review switched off the
    item used to fall through to route 2 and the criterion stopped scoring altogether. The authority
    it was missing is a record: the provenance the predictor stamps on every value says where its
    boundary is, what the endpoint is and how well it held out, so the route checks the rule against
    that and adds no judgement of its own -- which is what it has in common with route 1.
    """
    task_id = _task(core)
    attr_ref, rule_ref = criteria.propose(core, task_id, HERG, HERG_RULE, by=AGENT)
    claim_id = _prediction(core, task_id, attr_ref, value=0.21, unit="probability",
                           conditions=_provenance("hERG", {"auprc": 0.9062, "auroc": 0.8388}))
    assert adjudication.route_preview(core, _item(core, task_id, rule_ref))["route"] == "predictor_boundary_adopted"

    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref))
    assert record["route"] == "predictor_boundary_adopted" and record["resolution"] == "approve"
    assert record["rule_ref_after"] == rule_ref, "approving changes nothing: same kind, same cutoff, same basis"
    assert record["rule_kind_after"] == "preference" and record["scores_candidates"] is True
    # the record carries every condition it checked, and what it checked them against
    boundary = record["predictor_boundary"]
    assert (boundary["endpoint"], boundary["decision_boundary"], boundary["cutoff_value"]) == ("hERG", 0.5, 0.5)
    assert (boundary["metric_name"], boundary["metric_value"], boundary["metric_floor"]) == ("auroc", 0.8388, 0.70)
    assert boundary["claim_ids"] == [claim_id] and boundary["refusals"] == []
    assert "0.8388" in record["reason_text"] and "hERG" in record["reason_text"]
    # and it is an agent's verdict labelled as one, with no `hd_` anywhere
    assert record["approval_kind"] == "agent_verdict" and record["confirmed_by_a_person"] is False
    assert record["authority"] == "machine_adjudication"
    assert not core.artifacts.of_kind("expert_decision")
    assert not record["cited_claim_ids"], "no model was called, so there is no agent citation to make"

    ref = criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    rule_set = criteria.rule_set(core, task_id, ref)
    (entry,) = rule_set["entries"]
    assert entry["rule_kind"] == "preference" and entry["authority"] == "machine_adjudication"
    assert entry["cutoff_basis"] == "model_decision_boundary"
    assert entry["bound_support"]["states"]["rule.cutoff.value"] == "authority_basis"
    assert rule_set["acceptance_label"] == "exploratory" and rule_set["machine_adjudicated"] == [rule_ref]


def test_an_endpoint_with_a_negative_r2_can_never_carry_a_gate(core):
    """`Half_Life_Obach` holds out at R^2 -2.39 and `VDss_Lombardo` at -1.21: both are worse than
    predicting the training mean, so their output carries no information about a particular compound.
    A bound on such an endpoint is refused however exactly it matches the documented boundary, and
    the record says which condition failed -- the rule's author can act on that, where "no expert has
    given one" would have been false as well as useless."""
    task_id = _task(core)
    attr_ref, rule_ref = criteria.propose(
        core, task_id, HALF_LIFE_PREDICTED,
        {"rule_kind": "preference", "predicate_form": "threshold",
         "cutoff": {"comparator": ">=", "value": 6.0, "unit": "h"},
         "cutoff_basis": "model_decision_boundary", "on_missing": "unknown_no_penalty"}, by=AGENT)
    _prediction(core, task_id, attr_ref, value=14.2, unit="h",
                conditions=_provenance("Half_Life_Obach", {"r2": -2.3857, "mae": 31.8474},
                                       task_type="regression", boundary=6.0, unit="h"))
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref))
    assert record["route"] == "no_authority_available" and record["resolution"] != "approve"
    assert record["rule_kind_after"] == "exploratory_consideration" and record["scores_candidates"] is False
    assert record["predictor_boundary"]["adoptable"] is False
    (refusal,) = record["predictor_boundary"]["refusals"]
    assert "-2.3857" in refusal and "0.5" in refusal and "training mean" in refusal
    assert "model_decision_boundary" in record["reason_text"] and "expert" not in record["reason_text"]
    floors = adjudication.GATING_METRICS
    assert floors["regression"] == ("r2", adjudication.MIN_GATING_R2) and adjudication.MIN_GATING_R2 > 0


def test_a_boundary_the_model_does_not_draw_and_a_metric_it_does_not_record_are_both_refused(core):
    """Each condition on its own. A rule thresholding a classifier at 0.8 has drawn its own line,
    which is somebody's judgement and not the model's; an endpoint with no held-out metric
    establishes no skill at all; and a value kind the attribute does not accept means the claims this
    bound would be applied to are claims the cell would set aside."""
    task_id = _task(core)
    attr_ref, _ = criteria.propose(core, task_id, HERG, HERG_RULE, by=AGENT)
    good = _provenance("hERG", {"auprc": 0.9062, "auroc": 0.8388})
    claims = [{"claim_id": "claim_a", "determination_basis": "predicted", "conditions": good}]
    attribute = dict(HERG, attribute_id="attr_x", version=1)

    own_line = adjudication.predictor_boundary(
        dict(HERG_RULE, cutoff={"comparator": "<", "value": 0.8, "unit": "probability"}), attribute, claims)
    assert own_line["adoptable"] is False and "0.8" in own_line["refusals"][0]
    assert "does not state" in own_line["refusals"][0]

    unmeasured = adjudication.predictor_boundary(HERG_RULE, attribute,
                                                 [dict(claims[0], conditions=_provenance("Lipinski", {}))])
    assert unmeasured["adoptable"] is False and "no held-out auroc" in unmeasured["refusals"][0]

    unaccepted = adjudication.predictor_boundary(HERG_RULE, dict(attribute, acceptable_determination_bases=["measured"]),
                                                 claims)
    assert unaccepted["adoptable"] is False and "a basis the attribute accepts" in unaccepted["refusals"][0]

    nothing_stated = adjudication.predictor_boundary(HERG_RULE, attribute, [])
    assert nothing_stated["adoptable"] is False and "0 claim(s)" in nothing_stated["refusals"][0]

    two_endpoints = adjudication.predictor_boundary(
        HERG_RULE, attribute, claims + [{"claim_id": "claim_b", "determination_basis": "predicted",
                                         "conditions": _provenance("DILI", {"auroc": 0.8815})}])
    assert two_endpoints["adoptable"] is False and "different" in two_endpoints["refusals"][0]

    # the floors are the run's, not the module's, where a run states them
    strict = adjudication.predictor_boundary(HERG_RULE, attribute, claims,
                                             settings={"predict.min_gate_auroc": 0.95})
    assert strict["adoptable"] is False and "below the 0.95" in strict["refusals"][0]
    assert adjudication.predictor_boundary(HERG_RULE, attribute, claims)["adoptable"] is True


def test_adopting_the_boundary_does_not_hand_an_agent_the_authority_to_delete_candidates(core):
    """The route adopts a number, and the number is all it adopts. A model's decision boundary says
    where its two classes divide; it does not say that candidates on one side are unsuitable, which
    is the judgement route 3 withholds from an agent. So a hard exclusion on a documented boundary
    is still demoted to a preference -- it scores at the model's own line and deletes nobody -- and
    the record says both halves of what happened.
    """
    task_id = _task(core)
    attr_ref, rule_ref = criteria.propose(core, task_id, HERG,
                                          dict(HERG_RULE, rule_kind="hard_exclusion",
                                               on_missing="unknown_blocks_recommendation"), by=AGENT)
    _prediction(core, task_id, attr_ref, value=0.93, unit="probability",
                conditions=_provenance("hERG", {"auprc": 0.9062, "auroc": 0.8388}))
    record = adjudication.adjudicate(core, _item(core, task_id, rule_ref))
    assert record["route"] == "predictor_boundary_adopted" and record["resolution"] == "demote_to_preference"
    assert record["rule_kind_before"] == "hard_exclusion" and record["rule_kind_after"] == "preference"
    assert "stops excluding" in record["reason_text"] and "0.8388" in record["reason_text"]
    demoted = criteria.load(core, record["rule_ref_after"], task_id)
    assert demoted["cutoff"] == {"comparator": "<", "value": 0.5, "unit": "probability"}, \
        "the boundary survives the demotion; what the demotion removes is the deletion"
    assert demoted["cutoff_basis"] == "model_decision_boundary"
