"""Mechanism-of-action narrative: a separate artifact per candidate, never an input to a score (design §5.7).

The `summarizer` writes sentences about how one candidate acts, each carrying the claim ids it
rests on; a deterministic gate then re-checks every citation and drops — never repairs — any
sentence it cannot stand behind. Sentences survive only when every claim they cite exists, was
admitted, had its span verified against the source, and ties that span to this candidate. When
nothing survives, the block says `unexplained` rather than inventing a narrative or showing an
empty one that reads like silence.

Three things keep this out of the decision path, in code rather than in a prompt:

* **Input.** `explain` never accepts claims from its caller. It reads them itself through
  `ledger.claims(..., admitted_only=True)` and keeps only those whose
  `location.span_checked_against_source` is true, so a quarantined or unchecked claim cannot
  reach the summarizer at all.
* **Output.** The record is stored under its own artifact kind, carries `is_evidence: False`,
  and is checked against `FORBIDDEN_KEYS` before it is stored: a narrative that grew a score, a
  verdict, a position or a coverage figure is refused (`SeparationViolation`). Nothing in the
  scoring path imports this module — `assessor`, `symbolic`, `sr_stage`, `leaderboard` and
  `controller` never mention it, which `tests/test_mechanism.py` asserts against the sources.
* **Where it runs.** On demand for a shortlist (`mas candidate explain`), not in the sweep's
  finish step. The sweep covers thousands of candidates and one model call each would be
  indefensible for a block no score, verdict or rank reads; and because nothing downstream
  depends on it, deferring it costs the run nothing.

The gate's two prohibitions mirror the prompt's. A mechanism word in a sentence must appear in
the text of a claim it cites (`grounding_text`), and a sentence that reaches for the score at all
is dropped: no quote in an evidence ledger talks about this run's scoring terms, so such a
sentence could not be grounded, and the gate cannot tell a causal reading of one from an innocent
one. Curated ChEMBL mechanism records ground sentences alongside literature claims: their value
is the categorical statement that engagement is documented, their action type and mechanism text
travel in `conditions`, and their references are surfaced per sentence so a reader can follow them.
"""

from __future__ import annotations

import json
import re
from typing import Any

from . import evidence, ledger, reading
from .journal import actor as make_actor
from .models import ModelRequest, ModelRoster, call_role
from .runtime import Core

MECHANISM_VERSION = "mechanism-1"
STEP = "mechanism_narrative"
NARRATOR = make_actor("controller", "mechanism-narrative", "controller")
MAX_CLAIMS = 60          # claims offered to the summarizer for one candidate
MAX_SENTENCES = 8        # sentences the gate will consider from one reply

# A narrative is not a result. These keys belong to assessments, roll-ups and snapshots; if one
# appears anywhere in the record, something has started to use this block as an input.
FORBIDDEN_KEYS = ("score", "preference_score", "preference_coverage", "verdict", "verdict_restated",
                  "position", "rank", "coverage", "hard_rule_coverage", "comparability_key",
                  "selection_score", "coefficient", "coefficients")


class SeparationViolation(RuntimeError):
    """The narrative acquired a field something downstream could read as a result. It is refused."""


MECHANISM_SCHEMA = {
    "type": "object", "required": ["sentences"],
    "properties": {"sentences": {"type": "array", "items": {
        "type": "object", "required": ["text", "claim_ids"],
        "properties": {"text": {"type": "string"},
                       "claim_ids": {"type": "array", "items": {"type": "string"}}}}}},
}

MECHANISM_SYSTEM = (
    "You write the mechanism-of-action note for one compound, for a reader who will check every "
    "sentence against the claims you cite. You are given only claims that an evidence ledger admitted "
    "with their spans verified against the source. "
    "Rules: (1) Every sentence lists in claim_ids the claim ids it rests on; a sentence that cites "
    "nothing is dropped. (2) Say nothing about how the compound acts that the text of a cited claim "
    "does not state: no target, no action type, no selectivity, no pathway and no potency that is not "
    "there. A deterministic gate re-checks every citation and every mechanism word against the cited "
    "text and drops the sentence; it never repairs one, so an unsupported sentence costs you the "
    "sentence. (3) Never mention a score, a rank, a ranking, a coefficient or a percentile, and never "
    "present any scoring quantity as a cause of anything: this note is not part of any score and may "
    "not explain one. (4) A curated mechanism record states that engagement with a target is "
    "documented, with an action type and references; it says that engagement is on record, never how "
    "strong it is, so never turn one into a potency statement. (5) Prefer three or four sentences that "
    "are fully supported to a complete-sounding account, and return an empty list if the claims do not "
    "say how the compound acts."
)

# Words that state a mechanism. A sentence using one must find it in the text of a claim it cites;
# matching is on a stem, so "inhibits", "inhibitor" and "inhibition" are one word here.
MECHANISM_STEMS = ("inhibit", "antagoni", "agoni", "block", "bind", "bound", "activat", "inactivat",
                   "modulat", "suppress", "stimulat", "potentiat", "degrad", "allosteric", "covalent", "substrate",
                   "select", "downregulat", "upregulat", "phosphorylat", "dephosphorylat", "engag", "occupan",
                   "catalyt", "compet", "cleav", "transloc", "sequester", "chelat", "scaveng", "crosslink")

# Words that belong to the ranking, not to a mechanism. A sentence containing one is dropped: the
# gate cannot judge whether the mention is causal, and no quoted source can ground it either way.
# The list stays away from words a mechanism sentence needs — `expression` (gene expression) and
# `regression` (tumour regression) are not on it — and `rank` is, which costs a sentence about the
# RANK receptor; that drop is recorded with its reason rather than passed through unchecked.
SCORING_WORDS = ("score", "scores", "scored", "scoring", "rank", "ranks", "ranked", "ranking", "rankings",
                 "leaderboard", "coefficient", "coefficients", "percentile", "percentiles",
                 "ordering method", "scoring term", "preference score", "symbolic expression")

# Curated fields of a database record that carry its mechanism text. `claims_from_tool_result`
# quotes one field's *value* (`True` for an engagement record), so the curated statement itself —
# the action type, the mechanism text, the qualifiers — is in `conditions` and is read from there.
CONDITION_FIELDS = ("action_type", "mechanism_of_action", "molecular_mechanism", "binding_site_comment",
                    "selectivity_comment", "direct_interaction", "target_chembl_id")

_WORDS = re.compile(r"[a-z]+")


def _stems(text: str) -> set[str]:
    """The mechanism words a text uses, as stems."""
    words = _WORDS.findall(reading.normalize_for_match(text))
    return {stem for word in words for stem in MECHANISM_STEMS if word.startswith(stem)}


def scoring_words(text: str) -> list[str]:
    """Ranking vocabulary a sentence uses; a sentence that uses any is not a mechanism statement."""
    haystack = reading.normalize_for_match(text)
    return sorted(word for word in SCORING_WORDS
                  if re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", haystack))


def grounding_text(claim: dict[str, Any]) -> str:
    """The text a sentence's mechanism words must be found in.

    For a literature claim this is the verified quote and nothing else. For a database record
    field it is the quote plus the record's own curated fields, because the tool quotes the field
    value while the curated statement travels in `conditions` — a mechanism record's quote is
    `True`, and its mechanism is the action type and mechanism text beside it.
    """
    location = claim.get("location") or {}
    parts = [str(location.get("quoted_span") or "")]
    if location.get("location_kind") == "record_field":
        parts.append(str(claim.get("normalized_statement") or ""))
        conditions = claim.get("conditions") or {}
        parts += [str(conditions.get(field)) for field in CONDITION_FIELDS
                  if conditions.get(field) not in (None, "", [])]
    return " ".join(parts)


def references(claim: dict[str, Any]) -> list[dict[str, Any]]:
    """The references a curated record carries (PubMed ids, label sections), surfaced for the reader."""
    conditions = claim.get("conditions") or {}
    return [ref for ref in (conditions.get("references") or []) if isinstance(ref, dict)]


def names_candidate(claim: dict[str, Any], labels: list[str], candidate_ref: str) -> bool:
    """Whether a claim's span ties it to this candidate.

    A literature claim is tied by its quote naming the compound (`reading.names_entity`) — the
    passage is not enough here, although it was enough to admit the claim: a narrative sentence
    rests on the span a reader will be shown. A database record field is tied by the identifier
    the record was located with, recorded in the claim's admission reasons, because the quoted
    span of a record field is the field's value and names nothing at all.
    """
    quote = (claim.get("location") or {}).get("quoted_span") or ""
    if reading.names_entity(labels, quote):
        return True
    return ((claim.get("location") or {}).get("location_kind") == "record_field"
            and claim.get("candidate_ref") == candidate_ref
            and "identifier_grounded" in (claim.get("admission_reasons") or []))


def eligible_claims(core: Core, streams: tuple[str, ...], *, candidate_ref: str) -> list[dict[str, Any]]:
    """The only input: this candidate's admitted claims whose span was checked against the source."""
    return [claim for claim in ledger.claims(core, list(streams), candidate_ref=candidate_ref, admitted_only=True)
            if (claim.get("location") or {}).get("span_checked_against_source")]


def citation(claim: dict[str, Any]) -> dict[str, Any]:
    """What a surviving sentence shows for one claim it rests on."""
    location = claim.get("location") or {}
    conditions = claim.get("conditions") or {}
    return {"claim_id": claim["claim_id"], "source_ref": claim.get("source_ref"),
            "locator": location.get("locator_value"), "quote": location.get("quoted_span"),
            "statement": claim.get("normalized_statement"), "value": claim.get("value"), "unit": claim.get("unit"),
            "determination_basis": claim.get("determination_basis"), "evidence_kind": claim.get("evidence_kind"),
            "conditions": {field: conditions[field] for field in CONDITION_FIELDS if conditions.get(field) is not None},
            "references": references(claim)}


def claims_block(claims: list[dict[str, Any]]) -> str:
    """The claims as the summarizer sees them: id, verified quote, what it says, and its references."""
    return "\n".join(json.dumps({k: v for k, v in citation(claim).items() if v not in (None, "", [], {})},
                                ensure_ascii=False) for claim in claims)


def gate(sentences: list[dict[str, Any]], *, claims_by_id: dict[str, dict[str, Any]], labels: list[str],
         candidate_ref: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Re-check every sentence deterministically. Returns (kept, dropped); a failing sentence is dropped.

    Each cited claim must exist, be admitted, have a verified span, and name the candidate. Every
    mechanism word the sentence uses must appear in the text of a claim it cites, and a sentence
    that reaches for the ranking vocabulary is dropped whatever it cites.
    """
    kept, dropped = [], []
    for index, sentence in enumerate(sentences):
        text = str(sentence.get("text") or "").strip()
        cited_ids = list(dict.fromkeys(sentence.get("claim_ids") or []))
        problems: list[dict[str, str]] = []
        if index >= MAX_SENTENCES:
            problems.append({"reason": "beyond_the_sentence_limit", "detail": str(MAX_SENTENCES)})
        if not text:
            problems.append({"reason": "empty_sentence", "detail": ""})
        if not cited_ids:
            problems.append({"reason": "no_claim_cited", "detail": ""})
        cited = []
        for claim_id in cited_ids:
            claim = claims_by_id.get(claim_id)
            if claim is None:
                problems.append({"reason": "claim_not_found", "detail": claim_id})
            elif claim.get("admission_state") != "admitted":
                problems.append({"reason": "claim_not_admitted", "detail": claim_id})
            elif not (claim.get("location") or {}).get("span_checked_against_source"):
                problems.append({"reason": "span_not_verified", "detail": claim_id})
            elif not names_candidate(claim, labels, candidate_ref):
                problems.append({"reason": "quote_does_not_name_the_candidate", "detail": claim_id})
            else:
                cited.append(claim)
        if cited:
            unsupported = sorted(_stems(text) - {stem for claim in cited for stem in _stems(grounding_text(claim))})
            if unsupported:
                problems.append({"reason": "mechanism_not_in_a_cited_quote", "detail": ", ".join(unsupported)})
        used = scoring_words(text)
        if used:
            problems.append({"reason": "describes_a_scoring_term", "detail": ", ".join(used)})
        if problems:
            dropped.append({"index": index, "text": text, "cited_claim_ids": cited_ids, "problems": problems})
        else:
            kept.append({"text": text, "claim_ids": [claim["claim_id"] for claim in cited],
                         "claims": [citation(claim) for claim in cited]})
    return kept, dropped


def _keys(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _keys(item)


def check_separate(record: dict[str, Any]) -> dict[str, Any]:
    """Refuse a narrative that carries a result. Called before the artifact is written."""
    found = sorted({key for key in _keys(record) if key in FORBIDDEN_KEYS})
    if found:
        raise SeparationViolation(f"a mechanism narrative may not carry {found}: it is not an input to a score, "
                                  f"a verdict, a rank or a coverage figure")
    if record.get("is_evidence") is not False:
        raise SeparationViolation("a mechanism narrative is not evidence and must say so")
    return record


def labels_for(core: Core, run_id: str, candidate_ref: str) -> list[str]:
    """The candidate's names from the identity record the run resolved — the same label set the
    reader used when it admitted a literature claim, so the gate re-checks the same question."""
    for event in reversed(core.journal.replay(run_id)):
        if event.event_type == "identity.resolved" and event.payload.get("candidate_id") == candidate_ref:
            record = core.artifacts.payload(event.payload["artifact_id"])
            aliases = [a.get("alias") if isinstance(a, dict) else a for a in record.get("aliases") or []]
            labels = [record.get("preferred_label") or record.get("input_label")]
            labels += [alias for alias in aliases if evidence.name_like(alias)][:4]
            return [label for label in dict.fromkeys(labels) if label]
    return []


def narrative_of(core: Core, run_id: str, candidate_ref: str) -> dict[str, Any] | None:
    """The narrative already recorded for this candidate in this run, if there is one."""
    for event in reversed(core.journal.replay(run_id)):
        if (event.event_type == "step.completed" and event.payload.get("step") == STEP
                and event.payload.get("candidate_ref") == candidate_ref):
            return dict(core.artifacts.payload(event.payload["artifact_id"]),
                        artifact_id=event.payload["artifact_id"])
    return None


def narratives_of(core: Core, run_id: str) -> dict[str, dict[str, Any]]:
    """Every narrative recorded in this run, by candidate."""
    out: dict[str, dict[str, Any]] = {}
    for event in core.journal.replay(run_id):
        if event.event_type == "step.completed" and event.payload.get("step") == STEP:
            out[event.payload["candidate_ref"]] = dict(core.artifacts.payload(event.payload["artifact_id"]),
                                                       artifact_id=event.payload["artifact_id"])
    return out


def explain(core: Core, roster: ModelRoster | None, *, run_id: str, candidate_ref: str,
            task_id: str | None = None, labels: list[str] | None = None, by: dict[str, Any] | None = None,
            budget: Any = None, ids: dict[str, Any] | None = None,
            max_claims: int = MAX_CLAIMS) -> dict[str, Any]:
    """Write (once) the mechanism narrative for one candidate of one run.

    Idempotent: a narrative already recorded for this candidate is returned unchanged, with no
    model call and no new event, so a resumed or repeated shortlist costs nothing. The claims are
    read here, never passed in: only admitted claims with a verified span can reach the summarizer.
    """
    recorded = narrative_of(core, run_id, candidate_ref)
    if recorded is not None:
        return recorded
    by = by or NARRATOR
    ids = dict(ids or {}, step_id=f"step_{run_id}_{STEP}_{candidate_ref}")
    streams = (run_id,) if task_id is None else (run_id, task_id)
    labels = labels if labels is not None else labels_for(core, run_id, candidate_ref)
    eligible = eligible_claims(core, streams, candidate_ref=candidate_ref)[:max_claims]
    core.journal.append(run_id, "step.started", actor=by, ids=ids,
                        payload={"step": STEP, "candidate_ref": candidate_ref, "eligible_claims": len(eligible)},
                        question=f"what do the admitted, span-verified claims say about how {candidate_ref} acts?")
    record: dict[str, Any] = {
        "mechanism_version": MECHANISM_VERSION, "run_id": run_id, "task_id": task_id,
        "candidate_ref": candidate_ref, "candidate_labels": list(labels),
        "claims_offered": [claim["claim_id"] for claim in eligible], "sentences": [], "dropped_sentences": [],
        "explanation_status": "unexplained", "unexplained_reason": None, "model_id": None,
        "is_evidence": False, "enters_scoring": False,
        "note": "a separate artifact: no score, verdict, ranking or coverage figure reads it",
    }
    if not eligible:
        record["unexplained_reason"] = "no admitted claim with a verified span names this candidate"
    elif roster is None or "summarizer" not in roster.roles:
        record["unexplained_reason"] = "no model is bound to the summarizer role"
    else:
        response = call_role(core, roster, run_id, ModelRequest(
            role="summarizer", system=MECHANISM_SYSTEM, response_schema=MECHANISM_SCHEMA, max_tokens=2500,
            messages=[{"role": "user", "content":
                       f"Compound: {labels[0] if labels else candidate_ref}"
                       + (f" (also known as: {', '.join(labels[1:])})" if len(labels) > 1 else "")
                       + f"\n\nAdmitted claims, spans already verified ({len(eligible)}):\n{claims_block(eligible)}"
                       + "\n\nWrite the mechanism-of-action note."}],
            metadata={"question": f"mechanism of action of {candidate_ref}"}), ids=ids, budget=budget)
        claims_by_id = {claim["claim_id"]: claim
                        for claim in ledger.claims(core, list(streams), admitted_only=False)}
        kept, dropped = gate(response.data["sentences"], claims_by_id=claims_by_id, labels=labels,
                             candidate_ref=candidate_ref)
        record.update({"sentences": kept, "dropped_sentences": dropped, "model_id": response.model_id,
                       "explanation_status": "evidence_linked" if kept else "unexplained",
                       "unexplained_reason": None if kept else
                       f"no sentence survived the grounding gate ({len(dropped)} dropped)"})
    artifact_id = core.artifacts.put("mechanism_narrative", check_separate(record))
    core.journal.append(run_id, "step.completed", actor=by, ids=ids, state_to="completed",
                        payload={"step": STEP, "candidate_ref": candidate_ref, "artifact_id": artifact_id,
                                 "explanation_status": record["explanation_status"],
                                 "sentences_kept": len(record["sentences"]),
                                 "sentences_dropped": len(record["dropped_sentences"]),
                                 "is_evidence": False},
                        artifact_links=[{"kind": "mechanism_narrative", "id": artifact_id}],
                        summary=f"mechanism of {candidate_ref}: {record['explanation_status']} "
                                f"({len(record['sentences'])} sentence(s), "
                                f"{len(record['dropped_sentences'])} dropped)")
    return dict(record, artifact_id=artifact_id)


def explain_shortlist(core: Core, roster: ModelRoster | None, *, run_id: str, candidate_refs: list[str],
                      task_id: str | None = None, by: dict[str, Any] | None = None, budget: Any = None,
                      ids: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Narratives for a shortlist, in the order given; already-explained candidates cost nothing."""
    return [explain(core, roster, run_id=run_id, candidate_ref=ref, task_id=task_id, by=by, budget=budget, ids=ids)
            for ref in candidate_refs]
