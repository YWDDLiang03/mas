"""Evidence gathering for one candidate × attribute (design §8.1, §9 step 3).

Two paths, chosen by the capabilities of the attribute's evidence routes
(`criteria.evidence_routes`: one `evidence_request`, or several under `evidence_requests`):

* database capabilities (any tool capability other than literature): one broker call per
  declared route; each returned value becomes a claim located at the source record field,
  and the cell's claims are the union over the routes;
* `literature_retrieval`: a query built from the attribute's query template and the
  candidate's labels, then reading of the best hits and checked claim extraction.
"""

from __future__ import annotations

import re
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from . import criteria, ledger, reading, vocab
from .journal import actor as make_actor
from .models import ModelError
from .runtime import Core


class BudgetBlocked(Exception):
    """The cell could not be attempted because its budget reservation is used up."""

# Fallback when a tool does not declare a basis: what the kind of value it returned implies.
# `curated` maps to `measured` because a curated potency record (a pChEMBL value) is an
# experimental measurement a curator carried over from the primary literature. A tool whose
# records are assertions rather than measurements must say so per value (`determination_basis`).
DB_BASIS = {"measured": "measured", "curated": "measured", "derived": "derived", "predicted": "predicted",
            "simulated": "predicted"}


def determination_basis(value: dict[str, Any]) -> str:
    """The basis the tool declared for this value, else the basis its value kind implies.

    A tool knows what its own records are: ChEMBL's mechanism table states that engagement
    is documented, which is `curated`, not a measurement of anything, so it declares that
    basis itself. A declared basis is checked against `criteria.DETERMINATION_BASES`, the
    same closed list an attribute may ask for, rather than against the value-kind domain,
    which also admits `missing` - a value kind, never a basis. The list stays where the
    attribute validator reads it instead of becoming a vocabulary domain, so that one
    registry cannot drift from the other.
    """
    declared = value.get("determination_basis")
    if declared is None:
        return DB_BASIS.get(value.get("value_kind"), "measured")
    if declared not in criteria.DETERMINATION_BASES:
        raise vocab.VocabularyViolation(f"{declared!r} is not a determination basis; "
                                        f"expected one of {criteria.DETERMINATION_BASES}")
    return declared


def claims_from_tool_result(core: Core, stream_id: str, result, *, candidate: dict[str, Any], attribute_ref: str,
                            evidence_kind: str, link_basis: str, ids: dict | None = None) -> list[dict[str, Any]]:
    """Record one claim per returned value; admitted when identity and provenance are sound."""
    who = make_actor("tool", result.invocation["tool_id"] or "broker", "evidence_source")
    out = []
    for value in result.values:
        low, high = value.get("value_low"), value.get("value_high")
        if value.get("value") is None and low is None and high is None:
            continue
        shown = value["value"] if value.get("value") is not None else f"{low}-{high}"
        record_ref = value.get("source_record_ref") or (result.provenance.get("upstream_ref") or ["unknown"])[0]
        source_id = ledger.put_source(core, {
            "source_id": f"src_db_{result.invocation['tool_id']}_{record_ref}",
            "identifiers": [{"scheme": "db_record", "value": str(record_ref)}],
            "title": f"{result.invocation['tool_id']} record {record_ref}", "source_status": "database_entry",
            "access_state": "metadata_only", "license": result.provenance.get("license_id"),
            "data_version": result.provenance.get("data_version")})
        problems = []
        if link_basis not in ("exact_identifier_match", "authority_crosswalk", "name_match_single_candidate"):
            problems.append("identity_not_grounded")
        if not result.provenance.get("tool_id") or not result.provenance.get("invocation_id"):
            problems.append("provenance_incomplete")
        claim = {
            "source_ref": source_id, "candidate_ref": candidate["candidate_id"], "attribute_ref": attribute_ref,
            "location": {"location_kind": "record_field", "locator_value": f"{record_ref}#{value.get('name')}",
                         "quoted_span": str(shown), "span_checked_against_source": True},
            "claim_text": f"{value.get('name')} = {shown} {value.get('unit') or ''}".strip(),
            "claim_text_marker": "verbatim", "normalized_statement": f"{value.get('name')} = {shown} {value.get('unit') or ''}".strip(),
            "claim_type": "data_derived", "entities": [candidate["candidate_id"]], "evidence_kind": evidence_kind,
            "determination_basis": determination_basis(value), "value": value.get("value"),
            "value_low": low, "value_high": high,
            "unit": value.get("unit"), "unit_as_reported": value.get("unit"), "polarity": "supports",
            "scope_match": "direct", "reading_depth": "not_read", "verification_status": "unverified",
            "tool_result_ref": result.result_id, "conditions": value.get("conditions"),
        }
        claim_id = ledger.record_claim(core, stream_id, claim, by=who,
                                       admission_state="quarantined" if problems else "admitted",
                                       admission_reasons=problems or ["identifier_grounded", "provenance_complete"], ids=ids)
        out.append(dict(claim, claim_id=claim_id, admission_state="quarantined" if problems else "admitted"))
    return out


def literature_query(attribute: dict[str, Any], labels: list[str]) -> str:
    names = " OR ".join(f'"{label}"' if " " in label or "-" in label else label for label in labels if label)
    template = (criteria.evidence_routes(attribute)[0].get("parameters") or {}).get("query_template", "({names})")
    return template.replace("{names}", names)


_NAME_LIKE = re.compile(r"^[A-Za-z][A-Za-z0-9\- ]{2,30}$")


def name_like(alias: str | None) -> bool:
    """A usable search label: starts with a letter, short, at most three words (drops CAS numbers, IUPAC names)."""
    return bool(alias) and bool(_NAME_LIKE.match(alias)) and len(alias.split()) <= 3 and any(c.isalpha() for c in alias[1:])


class LiteratureCache:
    """Per-run memo of searches and documents, so one paper is read once per run.

    The sweep hands one cache to cells it may assess concurrently, and `gather` reads one cell's
    documents concurrently, so all three dicts are shared mutable state. `once` keeps the memo's
    whole point - a (candidate, paper) pair costs one extraction - across threads: the first
    caller produces under that key's gate while the others wait on it and then read the memo.

    WHY a gate per key instead of one lock held across the call, which is how
    `adapters/drug/pubchem.PropertyCache` solves the same shape: producing an entry here is a
    reader tool call plus an extraction model call, around half a minute each on the measured
    enumerate stage, so a single lock would serialize exactly the work the workers exist to
    overlap. A gate is kept after use rather than discarded: discarding it reopens the window in
    which a late thread builds a second gate for a key whose production is still in flight, and
    one `threading.Lock` per key is nothing beside the documents the memo already holds.
    """

    def __init__(self):
        self.searches: dict[str, list[dict[str, Any]]] = {}
        self.documents: dict[str, dict[str, Any] | None] = {}
        self.extractions: dict[tuple[str, str], list[dict[str, Any]]] = {}  # (candidate, paper) → claims for every attribute
        self._lock = threading.Lock()
        self._gates: dict[tuple[str, Any], threading.Lock] = {}

    def once(self, memo_name: str, key: Any, produce: Callable[[], Any]) -> Any:
        """The memoized entry, `produce` called at most once however many threads ask for it."""
        memo = getattr(self, memo_name)
        with self._lock:
            if key in memo:
                return memo[key]
            gate = self._gates.setdefault((memo_name, key), threading.Lock())
        with gate:
            with self._lock:
                if key in memo:
                    return memo[key]
            # A refusal (a spent budget, a provider error) memoizes nothing, so the retry a resumed
            # run makes is a retry and not a replay of the failure.
            value = produce()
            with self._lock:
                memo[key] = value
            return value


def gather(core: Core, broker, roster, stream_id: str, *, candidate: dict[str, Any], identity: dict[str, Any],
           attribute: dict[str, Any], objective_text: str, cutoff_date: str | None, budget: Any = None,
           ids: dict | None = None, cache: LiteratureCache | None = None, max_documents: int = 2,
           case_sources: list[dict[str, Any]] | None = None,
           reading_attributes: list[dict[str, Any]] | None = None,
           sources: list[str] | None = None, limit_per_query: int | None = None,
           max_chars: int | None = None, document_workers: int = 1) -> tuple[list[dict], str | None, list[str]]:
    """Gather claims for one cell. Returns (claims, tool_error_ref, source kinds searched)."""
    routes = criteria.evidence_routes(attribute)
    attr_ref = f"{attribute['attribute_id']}@v{attribute['version']}"
    who = make_actor("agent", "evidence-retriever", "retriever")
    if not criteria.is_literature_bound(attribute):
        # Every route of one attribute is asked, and the cell's claims are the union: the attribute
        # names one quantity, and `assessor.assess_cell` already aggregates all of an attribute's
        # claims under its declared aggregation, so two databases answering become one median rather
        # than two cells. A route that fails does not discard what another route returned -- the
        # error reference is kept so the cell says a source errored, with the claims it did get.
        claims, error_ref, searched = [], None, []
        for request in routes:
            inputs = dict(request.get("parameters", {}))
            inputs.update({"identifier": next((i["value"] for i in identity["identifiers"] if i["scheme"] == request.get("identifier_scheme")), None)
                           if request.get("identifier_scheme") else identity.get("candidate_id"),
                           "identifiers": identity["identifiers"]})
            result = broker.call(stream_id, request["capability"], request["question_kind"], inputs, requesting_actor=who,
                                 ids=ids, budget=budget)
            if result.absence_reason == "budget_exceeded":
                # The cell is not assessed rather than assessed on the routes that fit in the budget:
                # a quantity scored from one of its two declared sources is not that quantity, and
                # the cell is re-gathered in full when the run resumes.
                raise BudgetBlocked()
            if request["capability"] not in searched:
                searched.append(request["capability"])
            error_ref = error_ref or (result.result_id if result.outcome in ("failed", "unknown_outcome") else None)
            if result.ok:
                contract = next((c for c in broker.contracts() if c.tool_id == result.invocation["tool_id"]), None)
                claims += claims_from_tool_result(core, stream_id, result, candidate=candidate, attribute_ref=attr_ref,
                                                  evidence_kind=contract.evidence_kind_produced if contract else "database_entry",
                                                  link_basis=identity["identity_link_basis"], ids=ids)
        return claims, error_ref, searched
    request = routes[0]
    cache = cache or LiteratureCache()
    aliases = [a.get("alias") if isinstance(a, dict) else a for a in identity.get("aliases", [])]
    labels = [identity.get("preferred_label") or candidate.get("label")] + [a for a in aliases if name_like(a)][:4]
    labels = [l for l in dict.fromkeys(labels) if l]
    query = literature_query(attribute, labels)

    def run_search() -> list[dict[str, Any]]:
        hits, coverage_id = reading.search(core, broker, stream_id, [query], cutoff_date=cutoff_date,
                                           limit_per_query=limit_per_query or request.get("parameters", {}).get("search_limit", 10),
                                           ids=ids, budget=budget, sources=sources)
        if any(f["reason"] == "budget_exceeded" for f in core.artifacts.payload(coverage_id)["retrieval_failures"]):
            raise BudgetBlocked()
        return hits

    searched_hits = cache.once("searches", query, run_search)
    terms = (request.get("parameters") or {}).get("relevance_terms") or [attribute["name"]]

    def relevance(hit: dict[str, Any]) -> tuple:
        text = f"{hit.get('title', '')} {hit.get('abstract_html', '')}"
        names_candidate = reading.names_entity(labels, text)
        term_hits = sum(reading.normalize_for_match(t) in reading.normalize_for_match(text) for t in terms)
        return (not names_candidate, -term_hits, not hit.get("pmcid"), hit.get("best_rank", 0))

    hits = [h for h in sorted(searched_hits, key=relevance)
            if reading.names_entity(labels, f"{h.get('title', '')} {h.get('abstract_html', '')}")
            and not reading.is_case_source(h, case_sources or [])]
    selected = hits[:max_documents]

    def read_one(hit: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None, bool]:
        """One document's claims, the model error that ended it, and whether the budget refused it."""
        key = (hit.get("doi") or hit.get("pmid") or hit.get("title") or "").lower()
        document = cache.once("documents", key, lambda: reading.read(core, broker, stream_id, hit, ids=ids,
                                                                     budget=budget, cutoff_date=cutoff_date))
        if document is None:
            return [], None, False
        candidate_spec = {"candidate_id": candidate["candidate_id"], "labels": labels}
        if reading_attributes:
            # one read of this paper for this candidate serves every literature attribute of the rule set
            question = {"purpose": "candidate_attribute", "objective_text": objective_text, "attribute": None,
                        "attributes": reading_attributes, "candidate": candidate_spec}
        else:
            question = {"purpose": "candidate_attribute", "objective_text": objective_text,
                        "attribute": {"name": attribute["name"], "definition": attribute["definition"],
                                      "unit": attribute.get("unit"), "ref": attr_ref},
                        "candidate": candidate_spec}
        try:
            if reading_attributes:
                extracted = cache.once("extractions", (candidate["candidate_id"], key),
                                       lambda: reading.extract_claims(core, roster, stream_id, document, question,
                                                                      ids=ids, budget=budget, max_chars=max_chars))
                return [c for c in extracted if c.get("attribute_ref") == attr_ref], None, False
            return list(reading.extract_claims(core, roster, stream_id, document, question, ids=ids, budget=budget,
                                               max_chars=max_chars)), None, False
        except ModelError as error:
            if error.error_class == "quota_exhausted":
                return [], None, True
            return [], f"model_error:{error.error_class}", False

    # Positional collection, not completion order: the project replays runs and compares digests, so
    # a cell's claim order may not depend on which worker finished first. The fold below then reads
    # the outcomes in the documents' own order, which is what makes the result at N workers the same
    # result the one-worker path produces -- including when reading ends early. At one worker nothing
    # past the document that ended the cell is read at all; at N the later documents are already in
    # flight when it fails, and their claims are dropped rather than appended out of sequence.
    outcomes: list[tuple[list[dict[str, Any]], str | None, bool]] = []
    if document_workers > 1 and len(selected) > 1:
        with ThreadPoolExecutor(max_workers=min(document_workers, len(selected))) as pool:
            pending = [pool.submit(read_one, hit) for hit in selected]
        outcomes = [future.result() for future in pending]   # the pool has joined: every read finished
    else:
        for hit in selected:
            outcome = read_one(hit)
            outcomes.append(outcome)
            if outcome[1] or outcome[2]:
                break
    claims: list[dict[str, Any]] = []
    for extracted, model_error, blocked in outcomes:
        if blocked:
            # A refusal mid-flight must leave the cell `not_assessed`, never a short set of claims
            # that reads like a complete one: the claims gathered so far are discarded with the
            # exception, and the cell is re-gathered in full when the run resumes.
            raise BudgetBlocked()
        if model_error:
            return claims, model_error, ["literature_retrieval", "document_reading"]
        claims += extracted
    return claims, None, ["literature_retrieval", "document_reading"]
