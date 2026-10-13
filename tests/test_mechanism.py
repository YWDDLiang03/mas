"""Mechanism-of-action narrative (core/mechanism.py).

What the deterministic gate drops and what it keeps, that a curated ChEMBL mechanism record can
ground a sentence and surfaces its references, that the block is `unexplained` rather than empty
or invented, that nothing in the scoring or snapshot path can read it, that a second pass costs
nothing, and that the terminal client prints it. Scripted models; no network.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from mas.core import leaderboard, ledger, mechanism
from mas.core.broker import ToolResult
from mas.core.evidence import claims_from_tool_result
from mas.core.journal import actor
from mas.core.models import ModelRoster, ScriptedAdapter
from mas.core.runtime import Core

WHO = actor("agent", "reader-1", "reader")
OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")
RUN = "run_mech"
TASK = "task_mech"
CANDIDATE = "cand_ik-EX"
LABELS = ["Exampletinib", "EX-1"]

MECHANISM_VALUE = {
    "name": "target_engagement", "value": True, "unit": None, "value_kind": "curated",
    "determination_basis": "curated", "source_record_ref": "chembl_mechanism_304",
    "conditions": {"target_chembl_id": "CHEMBL1862", "action_type": "INHIBITOR",
                   "mechanism_of_action": "Tyrosine-protein kinase ABL inhibitor", "direct_interaction": True,
                   "references": [{"ref_type": "PubMed", "ref_id": "11290608", "ref_url": "https://pubmed/11290608"},
                                  {"ref_type": "FDA", "ref_id": "label-2001", "ref_url": None}]}}

POTENCY_QUOTE = "Exampletinib inhibited ABL1 with an IC50 of 12.5 nM in enzymatic assays"
OTHER_QUOTE = "Comparatortinib showed no activity against ABL1 in the same assays"


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c


def literature_claim(core, *, quote, admission_state="admitted", span_checked=True, candidate_ref=CANDIDATE):
    claim = {
        "source_ref": "src_doi_10.0-ex", "candidate_ref": candidate_ref, "attribute_ref": "attr_potency@v1",
        "location": {"location_kind": "paragraph", "locator_value": "sec1.p1", "section_path": ["Results"],
                     "quoted_span": quote, "span_checked_against_source": span_checked},
        "claim_text": quote, "claim_text_marker": "paraphrase", "normalized_statement": quote,
        "claim_type": "literature_extracted", "evidence_kind": "peer_reviewed", "determination_basis": "measured",
        "value": 12.5, "unit": "nM", "polarity": "supports", "scope_match": "direct", "reading_depth": "full_text",
    }
    return ledger.record_claim(core, RUN, claim, by=WHO, admission_state=admission_state,
                               admission_reasons=["quote_verified", "candidate_named_in_quote"])


def curated_mechanism_claim(core, value=None):
    """A real ChEMBL mechanism claim: basis `curated`, a categorical value, references in conditions."""
    result = ToolResult(result_id="tres_1", invocation={"tool_id": "tool_drug_chembl_mechanism"}, outcome="ok",
                        values=[value or MECHANISM_VALUE], records=[],
                        provenance={"tool_id": "tool_drug_chembl_mechanism", "invocation_id": "inv_1",
                                    "license_id": "CC BY-SA 3.0 (ChEMBL)", "data_version": "chembl",
                                    "upstream_ref": ["chembl:mechanism:CHEMBL941:CHEMBL1862"]})
    (claim,) = claims_from_tool_result(core, RUN, result, candidate={"candidate_id": CANDIDATE},
                                       attribute_ref="attr_engagement@v1", evidence_kind="database_entry",
                                       link_basis="exact_identifier_match")
    return claim["claim_id"]


def roster_saying(sentences, *, record=None):
    """A summarizer that answers with `sentences`; `claim_ids` of "*" become every offered claim id."""
    def script(request):
        offered = re.findall(r'"claim_id": "(claim_[0-9A-Z]{26})"', request.messages[0]["content"])
        if record is not None:
            record.append(request)
        return {"sentences": [dict(s, claim_ids=offered if s["claim_ids"] == ["*"] else s["claim_ids"])
                              for s in sentences]}
    adapter = ScriptedAdapter("s", script, model="scripted-summarizer")
    return ModelRoster({"s": adapter}, {"summarizer": "s"}), adapter


# --- the input is restricted before the summarizer sees anything -------------------------------------

def test_only_admitted_claims_with_a_verified_span_reach_the_summarizer(core):
    admitted = literature_claim(core, quote=POTENCY_QUOTE)
    literature_claim(core, quote=OTHER_QUOTE, admission_state="quarantined")
    unchecked = literature_claim(core, quote=POTENCY_QUOTE, span_checked=False)
    other_candidate = literature_claim(core, quote=OTHER_QUOTE, candidate_ref="cand_ik-OTHER")
    engagement = curated_mechanism_claim(core)
    eligible = [c["claim_id"] for c in mechanism.eligible_claims(core, (RUN,), candidate_ref=CANDIDATE)]
    assert sorted(eligible) == sorted([admitted, engagement])
    assert unchecked not in eligible and other_candidate not in eligible


# --- the gate ----------------------------------------------------------------------------------------

def test_a_fully_grounded_sentence_survives_with_its_claims_and_references(core):
    potency = literature_claim(core, quote=POTENCY_QUOTE)
    engagement = curated_mechanism_claim(core)
    roster, _ = roster_saying([
        {"text": "Exampletinib inhibited ABL1 in enzymatic assays.", "claim_ids": [potency]},
        {"text": "ABL1 engagement is on curated record, with the action type of an inhibitor.",
         "claim_ids": [engagement]}])
    record = mechanism.explain(core, roster, run_id=RUN, task_id=TASK, candidate_ref=CANDIDATE, labels=LABELS)
    assert record["explanation_status"] == "evidence_linked" and record["dropped_sentences"] == []
    assert [s["claim_ids"] for s in record["sentences"]] == [[potency], [engagement]]
    # a claim whose value is categorical engagement grounds a sentence, and its references travel with it
    curated = record["sentences"][1]["claims"][0]
    assert curated["determination_basis"] == "curated" and curated["value"] is True
    assert curated["conditions"]["action_type"] == "INHIBITOR"
    assert [r["ref_id"] for r in curated["references"]] == ["11290608", "label-2001"]
    assert record["sentences"][0]["claims"][0]["quote"] == POTENCY_QUOTE
    assert record["is_evidence"] is False and record["enters_scoring"] is False


def test_a_sentence_whose_citation_does_not_hold_is_dropped_not_repaired(core):
    potency = literature_claim(core, quote=POTENCY_QUOTE)
    quarantined = literature_claim(core, quote=OTHER_QUOTE, admission_state="quarantined")
    unchecked = literature_claim(core, quote=POTENCY_QUOTE, span_checked=False)
    other = literature_claim(core, quote=OTHER_QUOTE, candidate_ref="cand_ik-OTHER")
    roster, _ = roster_saying([
        {"text": "Exampletinib inhibited ABL1 in enzymatic assays.", "claim_ids": [potency]},
        {"text": "Exampletinib inhibited ABL1, as reported elsewhere.", "claim_ids": ["claim_DOESNOTEXIST"]},
        {"text": "Exampletinib inhibited ABL1 in a second report.", "claim_ids": [quarantined]},
        {"text": "Exampletinib inhibited ABL1 at a verified span.", "claim_ids": [unchecked]},
        {"text": "Exampletinib inhibited ABL1, unlike its comparator.", "claim_ids": [other]},
        {"text": "Exampletinib inhibits ABL1.", "claim_ids": []},
    ])
    record = mechanism.explain(core, roster, run_id=RUN, task_id=TASK, candidate_ref=CANDIDATE, labels=LABELS)
    assert [s["claim_ids"] for s in record["sentences"]] == [[potency]]
    assert [p["reason"] for d in record["dropped_sentences"] for p in d["problems"]] == [
        "claim_not_found", "claim_not_admitted", "span_not_verified",
        "quote_does_not_name_the_candidate", "no_claim_cited"]
    assert record["explanation_status"] == "evidence_linked"      # one sentence stood, the rest are gone


def test_a_mechanism_absent_from_a_cited_quote_and_a_scoring_term_are_both_refused(core):
    potency = literature_claim(core, quote=POTENCY_QUOTE)
    roster, _ = roster_saying([
        {"text": "Exampletinib selectively blocks CSF1R.", "claim_ids": [potency]},
        {"text": "Its inhibition of ABL1 is why it ranks first under the score.", "claim_ids": [potency]},
        {"text": "Exampletinib inhibited ABL1 in enzymatic assays.", "claim_ids": [potency]},
    ])
    record = mechanism.explain(core, roster, run_id=RUN, task_id=TASK, candidate_ref=CANDIDATE, labels=LABELS)
    assert [s["text"] for s in record["sentences"]] == ["Exampletinib inhibited ABL1 in enzymatic assays."]
    first, second = record["dropped_sentences"]
    assert first["problems"] == [{"reason": "mechanism_not_in_a_cited_quote", "detail": "block, select"}]
    assert second["problems"] == [{"reason": "describes_a_scoring_term", "detail": "ranks, score"}]
    assert mechanism.scoring_words("a percentile of the leaderboard coefficient") == [
        "coefficient", "leaderboard", "percentile"]
    assert mechanism.scoring_words("reduced VEGFR2 expression and drove tumour regression") == []


def test_nothing_surviving_the_gate_leaves_the_block_unexplained(core):
    potency = literature_claim(core, quote=POTENCY_QUOTE)
    roster, _ = roster_saying([{"text": "Exampletinib degrades the receptor.", "claim_ids": [potency]},
                               {"text": "It improves the score.", "claim_ids": [potency]}])
    record = mechanism.explain(core, roster, run_id=RUN, task_id=TASK, candidate_ref=CANDIDATE, labels=LABELS)
    assert record["sentences"] == [] and record["explanation_status"] == "unexplained"
    assert record["unexplained_reason"] == "no sentence survived the grounding gate (2 dropped)"
    assert len(record["dropped_sentences"]) == 2


def test_a_candidate_with_no_eligible_claim_is_unexplained_without_a_model_call(core):
    literature_claim(core, quote=OTHER_QUOTE, admission_state="quarantined")
    roster, adapter = roster_saying([{"text": "anything", "claim_ids": ["*"]}])
    record = mechanism.explain(core, roster, run_id=RUN, task_id=TASK, candidate_ref=CANDIDATE, labels=LABELS)
    assert record["explanation_status"] == "unexplained" and adapter.requests == []
    assert record["unexplained_reason"] == "no admitted claim with a verified span names this candidate"
    assert record["claims_offered"] == []


def test_a_candidate_named_only_in_the_passage_does_not_ground_a_sentence(core):
    """Admission accepted the passage naming the compound; a narrative sentence rests on the span itself."""
    claim = {"source_ref": "src_doi_10.0-ex", "candidate_ref": CANDIDATE, "attribute_ref": "attr_potency@v1",
             "location": {"location_kind": "paragraph", "locator_value": "sec1.p2", "section_path": ["Results"],
                          "quoted_span": "the compound inhibited ABL1 with an IC50 of 12.5 nM",
                          "span_checked_against_source": True},
             "normalized_statement": "inhibited ABL1", "evidence_kind": "peer_reviewed",
             "determination_basis": "measured", "reading_depth": "full_text"}
    claim_id = ledger.record_claim(core, RUN, claim, by=WHO, admission_state="admitted",
                                   admission_reasons=["quote_verified", "candidate_named_in_passage"])
    roster, _ = roster_saying([{"text": "Exampletinib inhibited ABL1.", "claim_ids": [claim_id]}])
    record = mechanism.explain(core, roster, run_id=RUN, task_id=TASK, candidate_ref=CANDIDATE, labels=LABELS)
    assert record["explanation_status"] == "unexplained"
    assert record["dropped_sentences"][0]["problems"] == [
        {"reason": "quote_does_not_name_the_candidate", "detail": claim_id}]


# --- separation from the decision path ---------------------------------------------------------------

def snapshot_over(core):
    context = {"task_context_id": TASK, "version": 1, "objective_text": "Rank compounds for ABL1",
               "mode": "conditional", "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True},
               "candidate_universe": {"kind": "enumerated_set", "members": [CANDIDATE], "source": "test",
                                      "as_of": "2026-10-13"},
               "scope_entities": [], "constraints": [], "seed_candidates": []}
    cell = {"assessment_id": f"asm_{CANDIDATE}", "candidate_ref": CANDIDATE, "attribute_ref": "attr_potency@v1",
            "rule_ref": "rule_potency@v1", "rule_kind": "preference", "verdict": "pass", "value": 7.5,
            "value_kind": "measured", "conflicting_claim_refs": []}
    roll = {CANDIDATE: {"state": "provisional", "state_reason": "no confirmed hard rule",
                        "hard_rule_coverage": None, "blocking_unknowns": []}}
    return context, leaderboard.build_snapshot(
        task_context=context, leaderboard_id="lbd_x_1", run_id=RUN, round_id="round_1",
        rule_set={"rule_set_ref": "rules@v1", "entries": [{"rule_kind": "preference"}],
                  "ordering_method": {"kind": "weighted_preference"}},
        evidence_snapshot_id="evs_1", roll_ups=roll, cells={CANDIDATE: [cell]},
        scores={CANDIDATE: (0.8, 1.0)}, identities={}, parent=None, sweep_completeness=1.0, budget={})


def test_the_narrative_enters_no_score_no_snapshot_and_no_comparability_key(core):
    potency = literature_claim(core, quote=POTENCY_QUOTE)
    context, before = snapshot_over(core)
    first_leaderboard = leaderboard.leaderboard_record(core, context, members=[CANDIDATE])
    roster, _ = roster_saying([{"text": "Exampletinib inhibited ABL1 in enzymatic assays.", "claim_ids": [potency]}])
    narrative = mechanism.explain(core, roster, run_id=RUN, task_id=TASK, candidate_ref=CANDIDATE, labels=LABELS)
    _context, after = snapshot_over(core)
    # the comparability key does not know the narrative exists, so no new leaderboard is opened
    assert leaderboard.leaderboard_record(core, context, members=[CANDIDATE]) == first_leaderboard
    text = json.dumps(after, sort_keys=True)
    assert narrative["artifact_id"] not in text and "mechanism_narrative" not in text
    assert narrative["sentences"][0]["text"] not in text
    assert _comparable(after) == _comparable(before)   # the snapshot is bit-for-bit what it was without one


def _comparable(snapshot):
    """A snapshot without the fields that move on every build (the publish time and change ids)."""
    changes = [{k: v for k, v in change.items() if k != "change_id"} for change in snapshot["change_records"]]
    return {**{k: v for k, v in snapshot.items() if k != "published_at"}, "change_records": changes}


def test_no_scoring_or_snapshot_module_can_read_the_narrative():
    """Separation enforced against the sources: nothing in the decision path imports this module."""
    root = Path(mechanism.__file__).parent
    for name in ("assessor.py", "symbolic.py", "sr_stage.py", "leaderboard.py", "controller.py", "criteria.py",
                 "evidence.py", "ledger.py", "staging.py", "projection.py", "derivation.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert not [line.strip() for line in text.splitlines() if "mechanism" in line and "import" in line], name
        assert not re.search(r"\bmechanism\s*\.\w", text), name
    # and the record refuses to carry a result, however it got there
    with pytest.raises(mechanism.SeparationViolation, match="preference_score"):
        mechanism.check_separate({"is_evidence": False, "sentences": [{"preference_score": 0.9}]})
    with pytest.raises(mechanism.SeparationViolation, match="not evidence"):
        mechanism.check_separate({"sentences": []})


# --- idempotence and the terminal client -------------------------------------------------------------

def test_the_narrative_is_idempotent_on_a_second_pass(core):
    potency = literature_claim(core, quote=POTENCY_QUOTE)
    roster, adapter = roster_saying([{"text": "Exampletinib inhibited ABL1 in enzymatic assays.",
                                      "claim_ids": [potency]}])
    first = mechanism.explain(core, roster, run_id=RUN, task_id=TASK, candidate_ref=CANDIDATE, labels=LABELS)
    seq = core.journal.last_seq(RUN)
    second = mechanism.explain(core, roster, run_id=RUN, task_id=TASK, candidate_ref=CANDIDATE, labels=LABELS)
    assert second["artifact_id"] == first["artifact_id"] and second["sentences"] == first["sentences"]
    assert core.journal.last_seq(RUN) == seq            # no second step, no second artifact
    assert len(adapter.requests) == 1                   # and no second model call
    assert mechanism.narrative_of(core, RUN, CANDIDATE)["artifact_id"] == first["artifact_id"]
    assert list(mechanism.narratives_of(core, RUN)) == [CANDIDATE]


def _store_with_a_finished_run(root):
    from tests.test_run_end_to_end import make_controller, setup_task
    with Core.open(root) as core:
        task_id = setup_task(core)
        make_controller(core).start(task_id, by=OPERATOR, sweep_seed=7)
    return task_id


def test_the_terminal_client_writes_the_note_on_demand_and_then_prints_it(tmp_path, capsys, monkeypatch):
    from mas.cli import main as cli
    root = tmp_path / "store"
    task_id = _store_with_a_finished_run(root)
    assert cli.main(["--store", str(root), "candidate", "show", task_id, "alpha"]) == 0
    assert "mechanism of action: not written yet" in capsys.readouterr().out
    roster, _ = roster_saying([{"text": "Alpha reached an oral bioavailability of 40% in healthy volunteers.",
                                "claim_ids": ["*"]}])
    monkeypatch.setattr(cli, "_roster", lambda args, required=True: roster)
    assert cli.main(["--store", str(root), "candidate", "explain", task_id, "alpha", "--top", "1"]) == 0
    written = capsys.readouterr().out
    assert "mechanism of action: evidence_linked" in written
    assert "Alpha reached an oral bioavailability of 40% in healthy volunteers." in written
    assert cli.main(["--store", str(root), "candidate", "show", task_id, "alpha"]) == 0
    shown = capsys.readouterr().out
    assert "Alpha reached an oral bioavailability of 40%" in shown and "claim_" in shown
    assert "oral bioavailability of 40%" in shown      # the quote the sentence rests on
    # the shortlist covers every ranked candidate, and the note already written is not rewritten
    other, _ = roster_saying([{"text": "The admitted claims report a single-dose exposure study.",
                               "claim_ids": ["*"]}])
    monkeypatch.setattr(cli, "_roster", lambda args, required=True: other)
    assert cli.main(["--store", str(root), "candidate", "explain", task_id]) == 0
    shortlist = capsys.readouterr().out
    assert "cand_ik-ALPHA" in shortlist and "cand_ik-BETA" in shortlist
    assert "Alpha reached an oral bioavailability of 40% in healthy volunteers." in shortlist
    assert "The admitted claims report a single-dose exposure study." in shortlist
    with Core.open(root) as core:
        run_id = leaderboard.snapshots(core, task_id)[-1]["run_id"]
        notes = mechanism.narratives_of(core, run_id)
        assert sorted(notes) == ["cand_ik-ALPHA", "cand_ik-BETA"]
        assert notes["cand_ik-ALPHA"]["sentences"][0]["text"].startswith("Alpha reached")
