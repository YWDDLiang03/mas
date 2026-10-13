"""Literature finding, reading, summarizing, and claim extraction (design §8.1, §4.9; C9, C13).

The pipeline is: plan queries (retriever role) → search (finder tools) → read
(reader tools: open-access full text as located passages, else the abstract) →
summarize (summarizer role; not evidence) → extract claims (reader role).

Every extracted claim must quote one passage verbatim. The quote is checked
deterministically against the stored passage text before the claim can be
admitted; a numeric value must appear inside its quote; a candidate-specific
claim must name the candidate in its quote, or in its passage when the quote names no
other entity; a document title alone never ties a claim to a candidate. Claims that
fail a check are quarantined with the reason, never silently dropped.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from . import ledger
from .clock import utc_now
from .journal import actor as make_actor
from .models import ModelRequest, ModelRoster, call_role
from .runtime import Core

# --- text normalization for quote checking ---------------------------------------

_QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"', "′": "'", "″": '"'}
_DASHES = {"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-"}
_SPACES = re.compile(r"\s+")


def normalize_for_match(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for table in (_QUOTES, _DASHES):
        for old, new in table.items():
            text = text.replace(old, new)
    text = text.replace("·", ".")  # mid-dot decimal separator used by some journals
    return _SPACES.sub(" ", text).strip().lower()


def quote_found(quote: str, passage_text: str) -> bool:
    q = normalize_for_match(quote).strip(" .;,")
    return len(q) >= 15 and q in normalize_for_match(passage_text)


def _number_forms(value: float) -> set[str]:
    forms = {repr(value)}
    if float(value).is_integer():
        forms.add(str(int(value)))
    else:
        forms.add(f"{value:g}")
        forms.add(("%f" % value).rstrip("0").rstrip("."))
    return {f.lower() for f in forms}


def value_in_quote(value: float, quote: str) -> bool:
    text = normalize_for_match(quote).replace(",", "")
    numbers = re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?", text)
    wanted = _number_forms(value)
    for number in numbers:
        try:
            if number in wanted or float(number) == float(value):
                return True
        except ValueError:
            continue
    return False


def names_entity(labels: list[str], *texts: str) -> bool:
    haystack = " ".join(normalize_for_match(t) for t in texts if t)
    return any(len(label) >= 3 and re.search(r"(?<![a-z0-9])" + re.escape(normalize_for_match(label)) + r"(?![a-z0-9])", haystack)
               for label in labels if label)


# --- case-source exclusion ------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", normalize_for_match(text)) if len(t) > 2}


def is_case_source(hit: dict[str, Any], case_sources: list[dict[str, Any]], *, title_similarity: float = 0.85) -> bool:
    """True when a hit is a registered case-source document: same identifier, or a near-identical title
    (token overlap at or above `title_similarity`, which catches preprint and published versions)."""
    keys = {(i["scheme"], str(i["value"]).lower()) for i in hit.get("identifiers", [])}
    for scheme in ("doi", "pmid", "pmcid"):
        if hit.get(scheme):
            keys.add((scheme, str(hit[scheme]).lower()))
    hit_tokens = _tokens(hit.get("title") or "")
    for doc in case_sources:
        if any((i["scheme"], str(i["value"]).lower()) in keys for i in doc.get("identifiers", [])):
            return True
        doc_tokens = _tokens(doc.get("title") or "")
        if doc_tokens and hit_tokens:
            overlap = len(doc_tokens & hit_tokens) / len(doc_tokens | hit_tokens)
            if overlap >= title_similarity:
                return True
    return False


# --- finding -------------------------------------------------------------------------

QUERY_PLAN_SCHEMA = {
    "type": "object", "required": ["queries"],
    "properties": {"queries": {"type": "array", "items": {
        "type": "object", "required": ["query", "rationale"],
        "properties": {"query": {"type": "string"}, "rationale": {"type": "string"}}}}},
}

RETRIEVER_SYSTEM = (
    "You plan literature searches for an evidence-gathering agent. You write search queries for "
    "Europe PMC (boolean AND/OR, quoted phrases, parentheses). Aim for recall first: cover synonyms, "
    "abbreviations, and the specific entity names given. Include at least one query aimed at "
    "counter-evidence or negative results. Never include information that was not given to you."
)


def plan_queries(core: Core, roster: ModelRoster, stream_id: str, *, objective_text: str, focus: str,
                 entity_labels: list[str] | None = None, max_queries: int = 6, ids: dict | None = None,
                 budget: Any = None) -> list[dict[str, str]]:
    prompt = (f"Objective: {objective_text}\nFocus of this search: {focus}\n"
              + (f"Entity names and aliases: {', '.join(entity_labels)}\n" if entity_labels else "")
              + f"Write up to {max_queries} queries.")
    response = call_role(core, roster, stream_id, ModelRequest(
        role="retriever", system=RETRIEVER_SYSTEM, messages=[{"role": "user", "content": prompt}],
        response_schema=QUERY_PLAN_SCHEMA, max_tokens=1500, metadata={"question": f"plan queries: {focus}"}),
        ids=ids, budget=budget)
    queries = [q for q in response.data["queries"] if q.get("query", "").strip()][:max_queries]
    return queries


def _key(hit: dict[str, Any]) -> str:
    for scheme in ("doi", "pmid", "pmcid"):
        if hit.get(scheme):
            return f"{scheme}:{str(hit[scheme]).lower()}"
    return f"title:{normalize_for_match(hit.get('title', ''))}"


def search(core: Core, broker, stream_id: str, queries: list[str], *, cutoff_date: str | None,
           limit_per_query: int = 25, open_access_only: bool = False, ids: dict | None = None,
           budget: Any = None, requested_minimum: int = 1) -> tuple[list[dict[str, Any]], str]:
    """Run queries, de-duplicate hits by identifier, and record a search coverage record.

    Returns (hits, coverage_record_artifact_id). Each hit lists the queries that found it.
    """
    who = make_actor("agent", "finder", "retriever")
    merged: dict[str, dict[str, Any]] = {}
    counts, failures = [], []
    for query in queries:
        result = broker.call(stream_id, "literature_retrieval", "search",
                             {"query": query, "limit": limit_per_query, "cutoff_date": cutoff_date,
                              "open_access_only": open_access_only},
                             requesting_actor=who, ids=ids, budget=budget)
        if result.outcome in ("failed", "not_attempted", "unknown_outcome"):
            failures.append({"query": query, "outcome": result.outcome,
                             "reason": (result.error or {}).get("class") or result.absence_reason})
        hits = [v["value"] for v in result.values if v.get("name") == "search_hit"]
        counts.append({"query": query, "returned": len(hits), "tool_id": result.invocation["tool_id"]})
        for rank, hit in enumerate(hits):
            key = _key(hit)
            entry = merged.setdefault(key, dict(hit, found_by=[], best_rank=rank))
            entry["found_by"].append(query)
            entry["best_rank"] = min(entry["best_rank"], rank)
    coverage = {"queries": queries, "source_families": sorted({c["tool_id"] for c in counts if c["tool_id"]}),
                "date_range": {"to": cutoff_date}, "result_counts": counts, "retrieval_failures": failures,
                "unique_hits": len(merged), "requested_minimum_met": len(merged) >= requested_minimum,
                "shortfall_note": None if len(merged) >= requested_minimum else "fewer unique hits than requested",
                "recorded_at": utc_now()}
    coverage_id = core.artifacts.put("search_coverage", coverage)
    ordered = sorted(merged.values(), key=lambda h: (-len(h["found_by"]), h["best_rank"], -(h.get("cited_by_count") or 0)))
    return ordered, coverage_id


# --- reading --------------------------------------------------------------------------

def _source_status(hit: dict[str, Any]) -> str:
    return "preprint" if hit.get("is_preprint") else "peer_reviewed_paper"


def read(core: Core, broker, stream_id: str, hit: dict[str, Any], *, ids: dict | None = None,
         budget: Any = None) -> dict[str, Any] | None:
    """Read one hit; store the source record and the document. Returns the document or None."""
    who = make_actor("agent", "reader-tool", "reader")
    result = broker.call(stream_id, "document_reading", "read", {"pmcid": hit.get("pmcid"), "pmid": hit.get("pmid"), "hit": hit},
                         requesting_actor=who, ids=ids, budget=budget)
    documents = [v["value"] for v in result.values if v.get("name") == "document"]
    identifiers = hit.get("identifiers") or [{"scheme": "title", "value": normalize_for_match(hit.get("title", ""))[:80]}]
    preferred = next((i for i in identifiers if i["scheme"] in ("doi", "pmid", "pmcid")), identifiers[0])
    source_id = f"src_{preferred['scheme']}_{preferred['value']}"
    access_state = documents[0]["access_state"] if documents else "fetch_failed"
    ledger.put_source(core, {
        "source_id": source_id, "identifiers": identifiers, "title": hit.get("title"), "authors": hit.get("authors"),
        "issued_date": hit.get("first_publication_date") or hit.get("year"), "container": hit.get("journal"),
        "source_status": _source_status(hit), "version_label": None, "retraction_state": "unknown",
        "access_state": access_state, "access_checked_at": utc_now(), "license": hit.get("license"),
        "pub_types": hit.get("pub_types", [])})
    if not documents:
        return None
    document = dict(documents[0], source_id=source_id, tool_result_ref=result.result_id)
    document["document_artifact_id"] = core.artifacts.put("document", document)
    return document


def select_passages(document: dict[str, Any], terms: list[str], *, max_chars: int = 60_000) -> list[dict[str, Any]]:
    """Passages most relevant to `terms`, always keeping title and abstract, within `max_chars`."""
    passages = document["passages"]
    total = sum(len(p["text"]) for p in passages)
    if total <= max_chars:
        return passages
    wanted = [normalize_for_match(t) for t in terms if t and len(t) >= 3]

    def score(p: dict[str, Any]) -> float:
        text = normalize_for_match(p["text"])
        hits = sum(text.count(t) for t in wanted)
        bonus = 5 if p["kind"] in ("title", "abstract") else (1 if p["kind"] == "table" else 0)
        return hits * 3 + bonus

    keep, used = [], 0
    for passage in sorted(passages, key=score, reverse=True):
        if used + len(passage["text"]) > max_chars and passage["kind"] not in ("title", "abstract"):
            continue
        keep.append(passage)
        used += len(passage["text"])
    order = {p["passage_id"]: i for i, p in enumerate(passages)}
    return sorted(keep, key=lambda p: order[p["passage_id"]])


def _render(passages: list[dict[str, Any]]) -> str:
    """One header line per passage: `=== passage <id> | <kind> | <section path>` (ids never contain spaces or bars)."""
    return "\n\n".join(f"=== passage {p['passage_id']} | {p['kind']} | {' > '.join(p['section_path'])}\n{p['text']}"
                         for p in passages)


# --- summarizing ----------------------------------------------------------------------

SUMMARY_SCHEMA = {
    "type": "object", "required": ["study_kind", "key_points", "limitations", "relevance"],
    "properties": {
        "study_kind": {"type": "string", "enum": ["review", "primary_research", "clinical_trial", "real_world_study",
                                                  "preclinical", "computational", "other"]},
        "key_points": {"type": "array", "items": {"type": "object", "required": ["point", "passage_ids"],
                                                  "properties": {"point": {"type": "string"},
                                                                 "passage_ids": {"type": "array", "items": {"type": "string"}}}}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "relevance": {"type": "string"},
    },
}

SUMMARIZER_SYSTEM = (
    "You summarize one scientific document for a research team. Use only the passages provided. "
    "Every key point must cite the passage ids it rests on. State limitations the document itself "
    "states, plus obvious ones (sample size, study design, preclinical only). Say how relevant the "
    "document is to the focus, plainly. Do not add knowledge from outside the passages."
)


def summarize(core: Core, roster: ModelRoster, stream_id: str, document: dict[str, Any], *, focus: str,
              terms: list[str] | None = None, ids: dict | None = None, budget: Any = None) -> dict[str, Any]:
    """A cited summary of one document. Summaries orient people and agents; they are never evidence."""
    passages = select_passages(document, terms or [focus])
    response = call_role(core, roster, stream_id, ModelRequest(
        role="summarizer", system=SUMMARIZER_SYSTEM,
        messages=[{"role": "user", "content": f"Focus: {focus}\n\nDocument: {document.get('title')}\n\n{_render(passages)}"}],
        response_schema=SUMMARY_SCHEMA, max_tokens=2500, metadata={"question": f"summarize {document.get('source_id')}"}),
        ids=ids, budget=budget)
    known = {p["passage_id"] for p in document["passages"]}
    points, dropped = [], []
    for point in response.data["key_points"]:
        cited = [pid for pid in point["passage_ids"] if pid in known]
        (points if cited else dropped).append(dict(point, passage_ids=cited))
    summary = {"source_id": document["source_id"], "document_artifact_id": document["document_artifact_id"],
               "focus": focus, "study_kind": response.data["study_kind"], "key_points": points,
               "uncited_points_dropped": len(dropped), "limitations": response.data["limitations"],
               "relevance": response.data["relevance"], "reading_depth": document["reading_depth"],
               "is_evidence": False, "model_id": response.model_id}
    summary["summary_artifact_id"] = core.artifacts.put("summary", summary)
    return summary


# --- claim extraction -----------------------------------------------------------------

CLAIM_SCHEMA = {
    "type": "object", "required": ["claims"],
    "properties": {"claims": {"type": "array", "items": {
        "type": "object", "required": ["passage_id", "quoted_span", "statement", "determination_basis", "polarity"],
        "properties": {
            "passage_id": {"type": "string"}, "quoted_span": {"type": "string"}, "statement": {"type": "string"},
            "determination_basis": {"type": "string", "enum": ["measured", "predicted", "asserted", "derived"]},
            "polarity": {"type": "string", "enum": ["supports", "conflicts", "inconclusive"]},
            "value": {"type": ["number", "null"]}, "value_low": {"type": ["number", "null"]},
            "value_high": {"type": ["number", "null"]}, "unit": {"type": ["string", "null"]},
            "entities": {"type": "array", "items": {"type": "string"}},
            "system_or_population": {"type": ["string", "null"]},
            "attribute_hint": {"type": ["string", "null"]},
        }}}},
}

READER_SYSTEM = (
    "You extract claims from the passages of one scientific document for an evidence ledger. "
    "Rules: (1) Use only the passages given. (2) Every claim quotes exactly one passage: quoted_span "
    "must be copied character for character from that passage, at least one full clause, and must "
    "contain the claim's number if the claim has one; a stated range goes in value_low and value_high (both inside the "
    "quote) with value null. (3) statement restates the quote plainly, "
    "without adding anything. (4) determination_basis: measured for experimental or clinical "
    "measurements, predicted for model or computational predictions, asserted for statements without "
    "data, derived for values computed from others. (5) polarity is relative to the question asked: "
    "supports, conflicts (counter-evidence), or inconclusive. (6) Include counter-evidence and "
    "negative results. (7) If nothing in the passages answers the question, return an empty list."
)


def _question_text(question: dict[str, Any]) -> str:
    lines = [f"Objective: {question.get('objective_text', '')}"]
    attribute = question.get("attribute")
    candidate = question.get("candidate")
    if question.get("purpose") == "criterion_discovery":
        lines.append("Question: which measurable properties or criteria does this document indicate matter for the "
                     "objective, and what values or thresholds does it report for them? Put the property name in "
                     "attribute_hint.")
        if question.get("dimensions"):
            lines.append("Cover every one of these assessment dimensions: "
                         + "; ".join(f"{d['dimension']} ({d['focus']})" for d in question["dimensions"]) + ".")
    if attribute:
        lines.append(f"Attribute: {attribute['name']} — {attribute['definition']}"
                     + (f" (unit: {attribute['unit']})" if attribute.get("unit") else ""))
    if candidate:
        lines.append(f"Candidate: {candidate['labels'][0]} (also known as: {', '.join(candidate['labels'][1:]) or 'no aliases'})")
        lines.append("Extract only claims about this candidate" + (" and this attribute." if attribute else "."))
    return "\n".join(lines)


def extract_claims(core: Core, roster: ModelRoster, stream_id: str, document: dict[str, Any], question: dict[str, Any], *,
                   ids: dict | None = None, budget: Any = None, admit: bool = True) -> list[dict[str, Any]]:
    """Extract, check, and record claims from one document for one question.

    `question`: {"purpose": "candidate_attribute" | "criterion_discovery", "objective_text",
    "attribute": {...} | None, "candidate": {"candidate_id", "labels": [...]} | None}.
    Returns the recorded claims (admitted and quarantined).
    """
    terms = [question.get("objective_text", "")]
    if question.get("attribute"):
        terms += [question["attribute"]["name"], question["attribute"].get("definition", "")]
    if question.get("candidate"):
        terms += question["candidate"]["labels"]
    passages = select_passages(document, terms)
    response = call_role(core, roster, stream_id, ModelRequest(
        role="reader", system=READER_SYSTEM, response_schema=CLAIM_SCHEMA, max_tokens=4000,
        messages=[{"role": "user", "content": f"{_question_text(question)}\n\nDocument: {document.get('title')}\n\n{_render(passages)}"}],
        metadata={"question": f"extract claims from {document.get('source_id')}"}), ids=ids, budget=budget)
    by_id = {p["passage_id"]: p for p in document["passages"]}
    reader = make_actor("agent", f"reader:{response.model_id}", "reader")
    candidate = question.get("candidate")
    attribute = question.get("attribute")
    source_status = "preprint" if document.get("source_hit", {}).get("is_preprint") else "peer_reviewed"
    recorded = []
    for item in response.data["claims"]:
        reasons, problems = [], []
        passage = by_id.get(item["passage_id"])
        if passage is None:
            problems.append("passage_not_found")
        elif not quote_found(item["quoted_span"], passage["text"]):
            problems.append("quote_not_found_in_passage")
        else:
            reasons.append("quote_verified")
        numbers = [item.get(k) for k in ("value", "value_low", "value_high") if item.get(k) is not None]
        if numbers:
            if all(value_in_quote(float(n), item["quoted_span"]) for n in numbers):
                reasons.append("value_in_quote")
            else:
                problems.append("value_not_in_quote")
        if candidate:
            labels = candidate["labels"]
            others = [e for e in item.get("entities", []) if e and not names_entity(labels, e)]
            if names_entity(labels, item["quoted_span"]):
                reasons.append("candidate_named_in_quote")
            elif passage is not None and names_entity(labels, passage["text"]) and not names_entity(others, item["quoted_span"]):
                reasons.append("candidate_named_in_passage")
            else:
                problems.append("candidate_not_named_in_source")
        claim = {
            "source_ref": document["source_id"], "document_artifact_id": document["document_artifact_id"],
            "location": {"location_kind": passage["kind"] if passage else "paragraph", "locator_value": item["passage_id"],
                         "section_path": passage["section_path"] if passage else [], "quoted_span": item["quoted_span"],
                         "span_checked_against_source": "quote_verified" in reasons},
            "claim_text": item["statement"], "claim_text_marker": "paraphrase", "normalized_statement": item["statement"],
            "claim_type": "literature_extracted", "entities": item.get("entities", []),
            "scope": {"population_or_system": item.get("system_or_population"), "marker": "stated"},
            "evidence_kind": source_status, "determination_basis": item["determination_basis"],
            "value": item.get("value"), "value_low": item.get("value_low"), "value_high": item.get("value_high"),
            "unit": item.get("unit"), "unit_as_reported": item.get("unit"),
            "polarity": item["polarity"], "attribute_hint": item.get("attribute_hint"),
            "scope_match": "direct" if candidate else "unknown", "reading_depth": document["reading_depth"],
            "verification_status": "unverified", "extraction_confidence": None,
            "candidate_ref": candidate["candidate_id"] if candidate else None,
            "attribute_ref": attribute.get("ref") if attribute else None,
            "question_purpose": question.get("purpose"),
        }
        state = "admitted" if admit and not problems else "quarantined"
        claim_id = ledger.record_claim(core, stream_id, claim, by=reader, admission_state=state,
                                       admission_reasons=reasons + problems, ids=ids)
        recorded.append(dict(claim, claim_id=claim_id, admission_state=state, admission_reasons=reasons + problems))
    return recorded
