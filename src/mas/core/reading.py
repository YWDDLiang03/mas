"""Literature finding, reading, summarizing, and claim extraction (design §8.1, §4.9; C9, C13).

The pipeline is: plan queries (retriever role) → search (finder tools) → read
(reader tools: open-access full text as located passages, else the abstract) →
summarize (summarizer role; not evidence) → extract claims (reader role).

Every extracted claim must quote one passage verbatim. The quote is checked
deterministically against the stored passage text before the claim can be
admitted; a numeric value must appear inside its quote; a candidate-specific
claim must name the candidate in its quote, or in its passage when the quote names no
other entity; a document title alone never ties a claim to a candidate; and a number
whose span does not tie it to this candidate and this attribute -- an arm comparison, a
span carrying someone else's value, a figure tagged to the wrong attribute -- is refused
(`attribution_problem`). Claims that fail a check are quarantined with the reason, never
silently dropped.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from typing import Any

from . import ledger, vocab
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


# --- attribution: does this span tie this number to this candidate and this attribute? ----
#
# A verified quote says the words are in the source. It does not say the number answers the
# question. Measured on the real literature path, 14 October 2026: the cell
# `Incidence of any-grade proteinuria x surufatinib` came back 10.8 citing the span-verified quote
# "9 [3.2%] vs. 10 [10.8%]" -- 10.8% is the comparator arm and the candidate's figure is 3.2% --
# and the same cell also cited a quote about hypertension at 38%, tagged to proteinuria. Both
# quotes passed every check there was, because every check there was is a string check.
#
# A missing value is honest and every surface already handles it; a confidently wrong value with a
# verified quote behind it is the failure this project cannot survive. So these checks refuse
# rather than guess, and they refuse into `quarantined` with a reason and a note, leaving the claim
# in the ledger as the record of what was read.

# Comparator cues, matched with boundaries that ignore hyphens so that `placebo-controlled` counts
# as naming a placebo arm (`controlled` on its own does not: the lookahead stops at its `l`).
_COMPARISON_CUE = re.compile(
    r"(?<![a-z0-9])(?:vs\.?|versus|compared (?:with|to)|relative to|than|placebo|controls?|comparator|untreated"
    r"|reference arm|standard of care|best supportive care)(?![a-z0-9])")
_ARM_WORD = re.compile(r"(?<![a-z0-9])(?:placebo|controls?|comparator|untreated|reference arm|standard of care"
                       r"|best supportive care)(?![a-z0-9])")
# Clause boundaries: a span's number belongs to the clause it sits in, and these are the words and
# marks that end one. Two tiers, because brackets cut both ways. A comparison word or a table
# cell boundary ends a clause wherever it appears, including inside a bracket -- which is where
# the measured arm comparison lives: "proteinuria (9 [3.2%] vs. 10 [10.8%], P = 0.010)". A comma or
# an `and` ends one only outside brackets, because a figure's own bracket ("proteinuria (12,
# 13.5%)") holds its count and its percentage and splitting there takes the endpoint's name away
# from its number.
_SPLIT_ANYWHERE = re.compile(r"(?<![a-z0-9])(?:vs\.?|versus|compared with|compared to|relative to|than)"
                             r"(?![a-z0-9])|[;|]")
_SPLIT_OUTSIDE_BRACKETS = re.compile(r"(?<![a-z0-9])(?:and|whereas|while)(?![a-z0-9])|[:,]")
_BRACKETED_PERCENT = re.compile(r"[\[(]\s*-?\d+(?:\.\d+)?\s*%")
# Words that measure rather than name a subject: dropping them is what lets "Incidence of
# any-grade proteinuria" and "Incidence of grade 3 or higher proteinuria" be told apart by
# `any-grade` versus `grade`, instead of both looking like "incidence".
_NOT_A_SUBJECT = frozenset({
    "incidence", "reported", "median", "mean", "average", "rate", "ratio", "time", "number", "percentage",
    "percent", "proportion", "patients", "patient", "humans", "human", "subjects", "study", "studies",
    "value", "values", "level", "levels", "dose", "doses", "dosing", "treatment", "treated", "repeated",
    "total", "overall", "observed", "higher", "lower", "greater", "maximum", "minimum", "with", "from",
    "after", "under", "over", "than", "that", "this", "which", "when", "their", "these", "those", "more",
    "less", "most", "least", "both", "each", "same", "such", "also", "into", "upon", "only", "very",
})


def _said(terms: list[str], text: str) -> list[str]:
    """Which of `terms` the text names, matched on the word's stem.

    A stem rather than the word, because a registry writes "Treatment discontinuation rate" and a
    paper writes "5 patients discontinued", "Proportion requiring a dose reduction" against "dose
    reductions have been reported", "predominant excretory route" against "fecal excretion
    predominated". Measured over the real run's 253 admitted claims, exact-word matching read all
    three of those as the attribute's subject being absent. Hyphens are boundaries, so `grade` is
    not found inside `any-grade` -- which is what tells an any-grade incidence from a grade-3 one.
    """
    haystack = normalize_for_match(text)
    said = []
    for term in terms:
        stem = term[:max(5, len(term) - 4)]
        if re.search(r"(?<![a-z0-9-])" + re.escape(stem) + r"[a-z]*(?![a-z0-9-])", haystack):
            said.append(term)
    return said


def subject_terms(attribute_name: str, sibling_names: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """The subject words that tell one attribute apart from the others read in the same extraction.

    A token two attributes share distinguishes nothing -- `oral` is in both "Reported oral
    bioavailability in humans" and "Time to steady state on repeated oral dosing" -- so only
    tokens belonging to exactly one of the names are kept. Returns this attribute's terms and, per
    other attribute, that one's, because what makes a span another attribute's is how much of that
    attribute's subject it names, not that one incidental word of it appears.
    """
    names = list(dict.fromkeys([attribute_name, *sibling_names]))
    tokens = {}
    for name in names:
        words = {t.strip("-") for t in re.findall(r"[a-z][a-z-]{3,}", normalize_for_match(name))}
        tokens[name] = {t for t in words if len(t) >= 4 and t not in _NOT_A_SUBJECT}
    counts = Counter(token for words in tokens.values() for token in words)
    distinctive = {token for token, n in counts.items() if n == 1}
    own = sorted(tokens.get(attribute_name, set()) & distinctive)
    others = {name: sorted(words & distinctive) for name, words in tokens.items() if name != attribute_name}
    return own, {name: terms for name, terms in others.items() if terms}


def value_like_numbers(span: str, unit: str | None) -> list[float]:
    """Numbers in the span that could be read as a value of this attribute.

    A number carrying a percent sign, or the attribute's own unit word, or sitting in brackets --
    the three forms a reported figure takes. Deliberately not every number: "grade 3", "study A1"
    and "9 patients" are not candidate values, and counting them would refuse almost every real
    span rather than the ambiguous ones.
    """
    text = normalize_for_match(span)
    unit_text = normalize_for_match(unit or "")
    unit_word = "%" if unit_text.startswith("%") else re.split(r"[\s/]", unit_text)[0]
    out = []
    for match in re.finditer(r"(?<![\w.])(-?\d+(?:\.\d+)?)", text):
        tail = text[match.end():match.end() + 16].lstrip()
        opener = text[match.start() - 1] if match.start() else ""
        if tail.startswith("%") or (unit_word and len(unit_word) > 1 and tail.startswith(unit_word)) \
                or opener in "([{":
            out.append(float(match.group(1)))
    return out


def _clauses(span: str) -> list[str]:
    """The span's clauses: comparison words and cell boundaries cut anywhere, commas only outside
    brackets (see `_SPLIT_ANYWHERE` / `_SPLIT_OUTSIDE_BRACKETS`)."""
    text = normalize_for_match(span)
    out, depth, start, index = [], 0, 0, 0
    while index < len(text):
        character = text[index]
        if character in "([{":
            depth += 1
        elif character in ")]}":
            depth = max(0, depth - 1)
        match = _SPLIT_ANYWHERE.match(text, index)
        if match is None and depth == 0:
            match = _SPLIT_OUTSIDE_BRACKETS.match(text, index)
        if match and match.end() > index:
            out.append(text[start:index])
            start = index = match.end()
            continue
        index += 1
    out.append(text[start:])
    return [clause.strip() for clause in out if clause.strip()]


def _clause_with(span: str, value: float) -> str:
    """The clause of the span that carries `value`, or the whole span if none does on its own."""
    for clause in _clauses(span):
        if value_in_quote(value, clause):
            return clause
    return span


def attribution_problem(item: dict[str, Any], *, labels: list[str], attribute_name: str | None,
                        sibling_names: list[str], unit: str | None) -> dict[str, Any] | None:
    """Why this numeric claim's span does not pin its number to this candidate and this attribute.

    Returns the failing check and a note a reviewer can read, or None when the span does pin it.
    Three checks, in the order they catch the measured failures:

    1. the span's subject is another attribute's (a hypertension figure tagged to proteinuria);
    2. the span compares arms -- `vs`, `versus`, `compared with`, a placebo or control arm, or two
       bracketed percentages -- and the clause carrying the number does not tie it to the candidate;
    3. the span carries a second value of this attribute's kind, so which one is meant is a guess.

    Check 1 fires on a *competing* subject, never on the absence of its own: the measured
    surufatinib bioavailability claim is "the serum level of the original drug is about 40.3%",
    which names no attribute at all and is the observation the whole repair exists to recover. It
    also asks for enough of the other attribute's subject to mean it -- every distinctive word of
    a one-word subject (`hypertension`, `bioavailability`), two of a longer one -- because over the
    measured 253 claims a single shared word ("drug", "serum") refused four true observations,
    that one among them. And it looks for the competing subject in the *clause carrying the
    number*, while its own subject counts anywhere in the span: "grade 3 or 4 TRAEs occurred in
    23.5% of patients, primarily driven by hypertension (16.2%)" is a TRAE rate with two endpoint
    names after it, not a hypertension figure.
    """
    numbers = [float(item[key]) for key in ("value", "value_low", "value_high") if item.get(key) is not None]
    if not numbers:
        return None                       # a claim with no number has no number to misattribute
    span = item.get("quoted_span") or ""
    own_terms, by_sibling = subject_terms(attribute_name, sibling_names) if attribute_name else ([], {})
    clause = _clause_with(span, numbers[0])
    said_others: list[str] = []
    for terms in by_sibling.values():
        hits = _said(terms, clause)
        if len(hits) >= min(2, len(terms)):        # enough of that attribute's subject to be about it
            said_others += [t for t in hits if t not in said_others]
    said_others.sort()
    if said_others and not _said(own_terms, span):
        return {"rule": "attribute_subject_mismatch", "numbers": numbers, "clause": clause,
                "note": f"the clause carrying {numbers[0]} ({clause!r}) is about {', '.join(said_others)}, which is "
                        f"another attribute read from the same document, and the span names none of this "
                        f"attribute's own subject words ({', '.join(own_terms) or 'it has none that are distinctive'})"}
    value_like = value_like_numbers(span, unit)
    competing = sorted({n for n in value_like if n not in numbers})
    comparison = bool(_COMPARISON_CUE.search(normalize_for_match(span)))
    crowded = bool(competing) or len(_BRACKETED_PERCENT.findall(span)) >= 2
    if not comparison and not crowded:
        return None
    if said_others or _ARM_WORD.search(clause):
        clean = False                     # the clause carrying the number names someone else's subject or arm
    elif comparison:
        # WHY a comparator cue demands the candidate's own name and not just the attribute's: the
        # other arm's figure is an attribute value too, so naming the attribute distinguishes
        # nothing. On "9 [3.2%] vs. 10 [10.8%]" both numbers are proteinuria incidences and only
        # 3.2% is the candidate's -- a span that says which is which says the candidate's name.
        clean = names_entity(labels, clause)
    else:
        # Several figures and no comparator: the usual shape is several endpoints of one arm, where
        # the endpoint's own name is what picks the number out ("proteinuria in 9 (3.2%), and
        # hypertension in 10 (10.8%)").
        clean = names_entity(labels, clause) or bool(_said(own_terms, clause))
    if clean:
        return None
    if comparison:
        return {"rule": "arm_comparison", "numbers": numbers, "clause": clause,
                "note": f"the span compares arms, and the clause carrying {numbers[0]} ({clause!r}) does not name "
                        f"{labels[0] if labels else 'this candidate'}, so which arm the number belongs to is a guess"}
    return {"rule": "competing_values", "numbers": numbers, "clause": clause,
            "note": f"the span reports {sorted(set(value_like))} and the clause carrying {numbers[0]} ({clause!r}) "
                    f"does not say that this number, rather than the others, is the one asked for"}


# --- case-source exclusion ------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", normalize_for_match(text)) if len(t) > 2}


def is_case_source(hit: dict[str, Any], case_sources: list[dict[str, Any]], *, title_similarity: float = 0.85,
                   title_containment: float = 0.90, containment_min_tokens: int = 6) -> bool:
    """True when a hit is a registered case-source document. Three paths, strongest first.

    1. Identifier. An exact match on a declared identifier — doi, pmid, pmcid, or an uploaded
       file's `sha256` content digest. A content hash is the one identity a copy of the case
       manuscript cannot shed by being renamed or retitled (an upload's title defaults to its
       filename stem, which shares no tokens with the real title), so the digest is read from
       the hit's identifier list and from a top-level `sha256` key alike.
    2. Title Jaccard at or above `title_similarity`: the same title with different casing or
       punctuation, or with a word swapped, as between a preprint and the published version.
    3. Title containment at or above `title_containment` of the *shorter* title's tokens: the
       same document with words added. Jaccard decays with every added word — the real case
       title plus ": supplementary methods" is already 10/12 = 0.83, under the threshold — so
       Jaccard alone lets the manuscript's own supplement, an "Author Correction:" of it, or a
       "Supplementary material for: ..." copy walk straight in. Containment does not decay that
       way, because the shared tokens are measured against the shorter title alone.

       Containment is deliberately symmetric: the longer side may be the hit (a supplement) or
       the declared case source (whose title may carry a subtitle the published version drops,
       or face a hit whose title a search index truncated). Either way the two titles name one
       document. The threshold is 0.90 rather than 1.00 so that, as on the Jaccard path, one
       token out of ten may differ ("... Ovarian Carcinoma: supplementary methods").

       `containment_min_tokens` guards the degenerate case. Containment of a *short* title is
       easy to hit by accident, so without a floor a two- or three-word case-source title would
       exclude every paper that happens to use those words: "TLS and Immunity" would swallow
       "TLS and immunity in colorectal cancer: a prospective cohort study". Below six content
       tokens, containment is not evidence of identity and only paths 1 and 2 apply (an exact
       short title still matches on Jaccard). At six or more, a title whose every content token
       reappears in another is not a coincidence, and a real manuscript title clears the floor
       comfortably — the deployment's case source has ten.
    """
    keys = {(i["scheme"], str(i["value"]).lower()) for i in hit.get("identifiers", [])}
    for scheme in ("doi", "pmid", "pmcid", "sha256"):
        if hit.get(scheme):
            keys.add((scheme, str(hit[scheme]).lower()))
    hit_tokens = _tokens(hit.get("title") or "")
    for doc in case_sources:
        if any((i["scheme"], str(i["value"]).lower()) in keys for i in doc.get("identifiers", [])):
            return True
        doc_tokens = _tokens(doc.get("title") or "")
        if doc_tokens and hit_tokens:
            shared = len(doc_tokens & hit_tokens)
            if shared / len(doc_tokens | hit_tokens) >= title_similarity:
                return True
            shorter = min(len(doc_tokens), len(hit_tokens))
            if shorter >= containment_min_tokens and shared / shorter >= title_containment:
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
                 budget: Any = None, searched: list[str] | None = None,
                 learned: list[str] | None = None) -> list[dict[str, str]]:
    """Plan search queries. With `searched` and `learned` (a follow-up round), the queries must reach
    evidence the earlier rounds did not: gaps, alternative mechanisms, counter-evidence."""
    prompt = (f"Objective: {objective_text}\nFocus of this search: {focus}\n"
              + (f"Entity names and aliases: {', '.join(entity_labels)}\n" if entity_labels else ""))
    if searched:
        prompt += ("This is a follow-up round. Queries already run:\n" + "\n".join(f"- {q}" for q in searched) + "\n"
                   + ("Topics already supported by evidence:\n" + "\n".join(f"- {h}" for h in (learned or [])[:40]) + "\n"
                      if learned else "")
                   + "Write queries for what is still missing: topics not yet covered, alternative explanations, "
                     "measurements behind the topics found, and counter-evidence. Do not repeat earlier queries.\n")
    prompt += f"Write up to {max_queries} queries."
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
    for identifier in hit.get("identifiers") or []:
        if identifier.get("scheme") not in ("epmc", "title"):
            return f"{identifier['scheme']}:{str(identifier['value']).lower()}"
    return f"title:{normalize_for_match(hit.get('title', ''))}"


def search(core: Core, broker, stream_id: str, queries: list[str], *, cutoff_date: str | None,
           limit_per_query: int = 25, open_access_only: bool = False, ids: dict | None = None,
           budget: Any = None, requested_minimum: int = 1,
           sources: list[str] | tuple[str, ...] | None = None) -> tuple[list[dict[str, Any]], str]:
    """Run queries, de-duplicate hits by identifier, and record a search coverage record.

    Without `sources`, each query goes to the first search tool that answers. With `sources`
    (registry ids, see adapters/literature/registry.py), each query goes to every permitted
    source in turn; a source that is not set up is recorded as unavailable, not as a failure.
    Returns (hits, coverage_record_artifact_id). Each hit lists the queries that found it. Every
    `result_counts` entry carries what the source itself recorded about the call under
    `provider_records` — for Bookshelf, the relaxation attempts actually sent to E-utilities.
    """
    from mas.adapters.literature import registry
    who = make_actor("agent", "finder", "retriever")
    merged: dict[str, dict[str, Any]] = {}
    counts, failures, unavailable = [], [], {}
    routes = [(s.source_id, [s.search_tool]) for s in registry.resolve(sources)] if sources else [(None, None)]
    for query in queries:
        for source_id, tool_ids in routes:
            if source_id in unavailable:
                continue
            result = broker.call(stream_id, "literature_retrieval", "search",
                                 {"query": query, "limit": limit_per_query, "cutoff_date": cutoff_date,
                                  "open_access_only": open_access_only},
                                 requesting_actor=who, ids=ids, budget=budget, tool_ids=tool_ids)
            if (source_id and result.outcome == "not_attempted"
                    and result.absence_reason in ("not_configured", "not_installed", "unauthorized")):
                unavailable[source_id] = result.absence_reason
                continue
            if result.outcome in ("failed", "not_attempted", "unknown_outcome"):
                failures.append({"query": query, "source": source_id, "outcome": result.outcome,
                                 "reason": (result.error or {}).get("class") or result.absence_reason})
            hits = [v["value"] for v in result.values if v.get("name") == "search_hit"]
            # `provider_records` is what the source itself recorded about the attempt — for Bookshelf,
            # the relaxation attempts: the terms actually sent, the terms dropped, the hits each got.
            # Without it the coverage artifact says only what was requested, not what was asked.
            counts.append({"query": query, "source": source_id, "returned": len(hits),
                           "tool_id": result.invocation["tool_id"],
                           "provider_records": list(result.records or [])})
            for rank, hit in enumerate(hits):
                if source_id and not hit.get("source"):
                    hit = dict(hit, source=source_id)
                key = _key(hit)
                entry = merged.setdefault(key, dict(hit, found_by=[], best_rank=rank))
                entry["found_by"].append(query)
                entry["best_rank"] = min(entry["best_rank"], rank)
    coverage = {"queries": queries, "source_families": sorted({c["tool_id"] for c in counts if c["tool_id"]}),
                "sources_requested": list(sources or []), "sources_unavailable": unavailable,
                "hits_by_source": {s: sum(1 for h in merged.values() if (h.get("source") or "unnamed") == s)
                                   for s in sorted({h.get("source") or "unnamed" for h in merged.values()})},
                "date_range": {"to": cutoff_date}, "result_counts": counts, "retrieval_failures": failures,
                "unique_hits": len(merged), "requested_minimum_met": len(merged) >= requested_minimum,
                "shortfall_note": None if len(merged) >= requested_minimum else "fewer unique hits than requested",
                "recorded_at": utc_now()}
    coverage_id = core.artifacts.put("search_coverage", coverage)
    ordered = sorted(merged.values(), key=lambda h: (-len(h["found_by"]), h["best_rank"], -(h.get("cited_by_count") or 0)))
    return ordered, coverage_id


# --- reading --------------------------------------------------------------------------

def _source_status(hit: dict[str, Any]) -> str:
    from mas.adapters.literature import registry
    if hit.get("is_preprint"):
        return "preprint"
    return registry.for_hit(hit).source_status


def read(core: Core, broker, stream_id: str, hit: dict[str, Any], *, ids: dict | None = None,
         budget: Any = None, cutoff_date: str | None = None) -> dict[str, Any] | None:
    """Read one hit with its source's reader; store the source record and the document. Returns the document or None."""
    from mas.adapters.literature import registry
    who = make_actor("agent", "reader-tool", "reader")
    tool_ids = [registry.for_hit(hit).reader_tool] if hit.get("source") else None
    result = broker.call(stream_id, "document_reading", "read",
                         {"pmcid": hit.get("pmcid"), "pmid": hit.get("pmid"), "hit": hit, "cutoff_date": cutoff_date},
                         requesting_actor=who, ids=ids, budget=budget, tool_ids=tool_ids)
    documents = [v["value"] for v in result.values if v.get("name") == "document"]
    identifiers = hit.get("identifiers") or [{"scheme": "title", "value": normalize_for_match(hit.get("title", ""))[:80]}]
    preferred = next((i for i in identifiers if i["scheme"] in ("doi", "pmid", "pmcid")), identifiers[0])
    if documents and documents[0].get("identifiers", {}).get("revid"):
        # a wiki page is cited by the revision that was read
        preferred = {"scheme": f"{preferred['scheme']}_rev", "value": documents[0]["identifiers"]["revid"]}
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
    document = dict(documents[0], source_id=source_id, tool_result_ref=result.result_id,
                    evidence_kind="preprint" if hit.get("is_preprint") else registry.for_hit(hit).evidence_kind)
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
    if question.get("attributes"):
        lines.append("Attributes (tag each claim with the attribute_name it reports on):")
        for item in question["attributes"]:
            lines.append(f"- {item['name']}: {item['definition']}" + (f" (unit: {item['unit']})" if item.get("unit") else ""))
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
        lines.append("Extract only claims about this candidate" + (" and this attribute." if attribute else
                                                                    " and these attributes." if question.get("attributes") else "."))
    return "\n".join(lines)


def extract_claims(core: Core, roster: ModelRoster, stream_id: str, document: dict[str, Any], question: dict[str, Any], *,
                   ids: dict | None = None, budget: Any = None, admit: bool = True,
                   max_chars: int | None = None) -> list[dict[str, Any]]:
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
    attribute_refs: dict[str, str] = {}
    schema = CLAIM_SCHEMA
    if question.get("attributes"):
        attribute_refs = {a["name"]: a["ref"] for a in question["attributes"]}
        terms += [t for a in question["attributes"] for t in (a["name"], a.get("definition", ""))]
        schema = json.loads(json.dumps(CLAIM_SCHEMA))
        item_schema = schema["properties"]["claims"]["items"]
        item_schema["required"] = item_schema["required"] + ["attribute_name"]
        item_schema["properties"]["attribute_name"] = {"type": "string", "enum": sorted(attribute_refs)}
    passages = select_passages(document, terms, max_chars=max_chars or 60_000)
    response = call_role(core, roster, stream_id, ModelRequest(
        role="reader", system=READER_SYSTEM, response_schema=schema, max_tokens=6000,
        messages=[{"role": "user", "content": f"{_question_text(question)}\n\nDocument: {document.get('title')}\n\n{_render(passages)}"}],
        metadata={"question": f"extract claims from {document.get('source_id')}"}), ids=ids, budget=budget)
    by_id = {p["passage_id"]: p for p in document["passages"]}
    reader = make_actor("agent", f"reader:{response.model_id}", "reader")
    candidate = question.get("candidate")
    attribute = question.get("attribute")
    # The attributes this extraction was asked about, by name: what an extracted number may be
    # checked against, and what the *other* attributes of the same read are called -- which is how
    # a hypertension figure tagged to proteinuria is recognized as mis-tagged.
    offered = {a["name"]: a for a in (question.get("attributes") or ([attribute] if attribute else []))}
    source_status = ("preprint" if document.get("source_hit", {}).get("is_preprint")
                     else document.get("evidence_kind", "peer_reviewed"))
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
        attribution = None
        if candidate:
            labels = candidate["labels"]
            others = [e for e in item.get("entities", []) if e and not names_entity(labels, e)]
            if names_entity(labels, item["quoted_span"]):
                reasons.append("candidate_named_in_quote")
            elif passage is not None and names_entity(labels, passage["text"]) and not names_entity(others, item["quoted_span"]):
                reasons.append("candidate_named_in_passage")
            else:
                problems.append("candidate_not_named_in_source")
            name = item.get("attribute_name") if attribute_refs else (attribute or {}).get("name")
            attribution = attribution_problem(item, labels=labels, attribute_name=name,
                                              sibling_names=[n for n in offered if n != name],
                                              unit=(offered.get(name) or {}).get("unit"))
            if attribution:
                problems.append("attribution_ambiguous")
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
            "attribute_ref": attribute_refs.get(item.get("attribute_name")) if attribute_refs
            else attribute.get("ref") if attribute else None,
            "question_purpose": question.get("purpose"),
            # Which attribution check refused the number, and why in words: `attribution_ambiguous`
            # says a claim was set aside, this says what a reviewer would have to disagree with.
            "attribution_check": attribution,
        }
        state = "admitted" if admit and not problems else "quarantined"
        admission_reasons = [vocab.require("literature_admission_reason", r) for r in reasons + problems]
        claim_id = ledger.record_claim(core, stream_id, claim, by=reader, admission_state=state,
                                       admission_reasons=admission_reasons, ids=ids)
        recorded.append(dict(claim, claim_id=claim_id, admission_state=state, admission_reasons=admission_reasons))
    return recorded
