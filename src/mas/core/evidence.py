"""Evidence gathering for one candidate × attribute (design §8.1, §9 step 3).

Two paths, chosen by the capabilities of the attribute's evidence routes
(`criteria.evidence_routes`: one `evidence_request`, or several under `evidence_requests`):

* database capabilities (any tool capability other than literature): one broker call per
  declared route; each returned value becomes a claim located at the source record field,
  and the cell's claims are the union over the routes;
* `literature_retrieval`: a query built from the attribute's query template and the
  candidate's labels, then reading of the best hits and checked claim extraction.

An attribute may declare both kinds (`criteria.check_attribute` permits it for a quantitative
attribute pooled by a numeric aggregation, which is how a required receptor's potency is read
from two curations *and* from a published selectivity table). Both halves are then gathered and
the cell's claims are their union -- minus any route whose capability this run holds out
(`gather(defer_capabilities=...)`, from the rule set's entry: `criteria.DEFERRAL_SCOPES`), so a
staged sweep reads such an attribute from its databases now and from the literature later.

The literature path is per *candidate*, not per cell: `read_literature` reads the union of
every literature attribute's selection once and `gather` hands each cell the claims tagged
for its own attribute (`LiteratureReading`).
"""

from __future__ import annotations

import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

from . import criteria, ledger, reading, supplements, vocab
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


def producible_evidence_kinds(broker) -> set[str]:
    """Every evidence kind the tools registered in *this* install can stamp on a claim.

    The ground truth of what is produced, as opposed to `criteria.EVIDENCE_KINDS`, which is the
    closed registry of what any kind of tool could produce. The two answer different questions and
    both are needed: a kind in neither is a schema defect (`criteria.check_attribute` refuses it),
    while a kind in the registry and not here is a tool this machine has not got -- an install gap,
    which must not be refused as though the attribute were wrong.

    Two sources, because claims are written on two paths. A database claim carries its tool's
    `evidence_kind_produced` (`claims_from_tool_result`). A literature claim carries the source
    registry's kind for the document, except that `reading.read` stamps `preprint` on a hit the
    search returned as one -- so `preprint` is producible exactly when a reader is registered, and
    no contract declares it.
    """
    contracts = list(broker.contracts())
    kinds = {c.evidence_kind_produced for c in contracts}
    if any(c.capability_kind == "document_reading" for c in contracts):
        kinds.add("preprint")
    return kinds


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
            "title": f"{result.invocation['tool_id']} record {record_ref}",
            # A model's output is not a record anybody holds: `ledger.SOURCE_STATUSES` registers
            # `model_prediction_record` for it, and calling it a database entry would tell every
            # reader of the source table that a number somebody looked up what a model computed.
            "source_status": "model_prediction_record" if evidence_kind == "model_prediction" else "database_entry",
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
    # The *literature* route's template, not the first route's: an attribute may read one quantity
    # from two databases and from the literature, and there the first route is a database one with no
    # template at all, which fell back to the bare-name query -- a search for the compound rather
    # than for the quantity.
    route = criteria.literature_route(attribute) or {}
    template = (route.get("parameters") or {}).get("query_template", "({names})")
    return template.replace("{names}", names)


_NAME_LIKE = re.compile(r"^[A-Za-z][A-Za-z0-9\- ]{2,30}$")


def name_like(alias: str | None) -> bool:
    """A usable search label: starts with a letter, short, at most three words (drops CAS numbers, IUPAC names)."""
    return bool(alias) and bool(_NAME_LIKE.match(alias)) and len(alias.split()) <= 3 and any(c.isalpha() for c in alias[1:])


class LiteratureCache:
    """Per-run memo of searches and documents, so one paper is read once per run.

    The sweep hands one cache to candidates it may read concurrently, and `read_literature` reads
    one candidate's documents concurrently, so all three dicts are shared mutable state. `once`
    keeps the memo's whole point - a (candidate, paper) pair costs one extraction - across threads:
    the first caller produces under that key's gate while the others wait on it and then read the
    memo. Two candidates selecting the same paper still read it once: the document memo is keyed by
    the paper, and only the extraction is keyed by (candidate, paper).

    WHY a gate per key instead of one lock held across the call, which is how
    `adapters/drug/pubchem.PropertyCache` solves the same shape: producing an entry here is a
    reader tool call plus an extraction model call - the measured enumerate stage averaged 25 s
    over its 24 calls - so a single lock would serialize exactly the work the workers exist to
    overlap, while two threads reaching for the same paper must still pay for one call. A gate is kept after use rather than discarded: discarding it reopens the window in
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


@dataclass
class LiteratureReading:
    """One candidate's whole literature reading, before any of its cells is assessed.

    WHY the reading is a per-candidate unit rather than a per-cell one: one extraction tags claims
    for *every* literature attribute in the prompt, so a paper found by the hypertension query
    answers the bioavailability question too -- but a cell that harvested only the papers its own
    query selected never saw those claims. Measured on the real path, 14 October 2026, 26
    literature criteria x 2 candidates (surufatinib, sunitinib): 375 claims recorded, 253 admitted,
    70 ever offered to a cell, 6 of the 52 cells value-bearing where the ledger supported 16. The
    decisive one: surufatinib's oral bioavailability, extracted from doi:10.3389/fphar.2024.1498339
    as value 40.3 in the attribute's own unit, basis measured, quote verified, admitted -- and its
    cell came back `unknown_missing`, because that paper was read for another attribute's query.

    WHY the union is read up front instead of harvesting opportunistically from
    `cache.extractions`: a cell's claims may not depend on which other cell finished first. This
    project replays runs and compares digests (see the fold in `read_literature`), and an
    opportunistic harvest changes a cell's claim set with the scheduling of its neighbours as soon
    as `assess.workers > 1`. Reading the union first costs nothing extra -- the same documents are
    already read, the memo already pays for each one once -- and leaves every cell of a candidate
    looking at the same finished evidence.
    """

    candidate_ref: str
    claims: list[dict[str, Any]] = field(default_factory=list)
    error_ref: str | None = None
    searched: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)      # union documents reached, in reading order
    selections: list[dict[str, Any]] = field(default_factory=list)   # per attribute: query and its selection

    def claims_for(self, attribute_ref: str) -> list[dict[str, Any]]:
        """The claims this reading tagged for one attribute, in the documents' own order."""
        return [c for c in self.claims if c.get("attribute_ref") == attribute_ref]


def search_labels(candidate: dict[str, Any], identity: dict[str, Any]) -> list[str]:
    """The names a search may use for this candidate: its preferred label and name-like aliases."""
    aliases = [a.get("alias") if isinstance(a, dict) else a for a in identity.get("aliases", [])]
    labels = [identity.get("preferred_label") or candidate.get("label")] + [a for a in aliases if name_like(a)][:4]
    return [label for label in dict.fromkeys(labels) if label]


def _document_key(hit: dict[str, Any]) -> str:
    return (hit.get("doi") or hit.get("pmid") or hit.get("title") or "").lower()


def _attr_ref(attribute: dict[str, Any]) -> str:
    return f"{attribute['attribute_id']}@v{attribute['version']}"


def _select_documents(core: Core, broker, stream_id: str, *, attribute: dict[str, Any], labels: list[str],
                      cache: LiteratureCache, cutoff_date: str | None, ids: dict | None, budget: Any,
                      sources: list[str] | None, limit_per_query: int | None, max_documents: int,
                      case_sources: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """One literature attribute's query and the documents it selects, highest relevance first."""
    request = criteria.literature_route(attribute) or criteria.evidence_routes(attribute)[0]
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
            and not reading.is_case_source(h, case_sources)]
    return query, hits[:max_documents]


def read_literature(core: Core, broker, roster, stream_id: str, *, candidate: dict[str, Any],
                    identity: dict[str, Any], attributes: list[dict[str, Any]], objective_text: str,
                    cutoff_date: str | None, budget: Any = None, ids: dict | None = None,
                    cache: LiteratureCache | None = None, max_documents: int = 2,
                    max_union_documents: int | None = None, case_sources: list[dict[str, Any]] | None = None,
                    reading_attributes: list[dict[str, Any]] | None = None, sources: list[str] | None = None,
                    limit_per_query: int | None = None, max_chars: int | None = None,
                    document_workers: int = 1) -> LiteratureReading:
    """Read one candidate's literature once: every attribute's selection, extracted for all of them.

    The union is bounded twice. Per query, by `max_documents` (`read.max_papers_per_candidate`),
    exactly as a single cell was bounded. Across queries, by `max_union_documents`, which defaults
    to the sum of those per-query bounds -- the union is a set of documents, so two queries that
    choose the same paper pay for it once, and the measured run's 26 queries x 2 documents came to
    38 documents per candidate rather than the 52 the ceiling allows.
    """
    cache = cache or LiteratureCache()
    labels = search_labels(candidate, identity)
    ordered = sorted(attributes, key=_attr_ref)
    if reading_attributes is None and len(ordered) > 1:
        reading_attributes = [{"name": a["name"], "definition": a["definition"], "unit": a.get("unit"),
                               "ref": _attr_ref(a)} for a in ordered]
    out = LiteratureReading(candidate_ref=candidate["candidate_id"],
                            searched=["literature_retrieval", "document_reading"])
    union: dict[str, dict[str, Any]] = {}
    for attribute in ordered:
        query, selected = _select_documents(core, broker, stream_id, attribute=attribute, labels=labels, cache=cache,
                                            cutoff_date=cutoff_date, ids=ids, budget=budget, sources=sources,
                                            limit_per_query=limit_per_query, max_documents=max_documents,
                                            case_sources=case_sources or [])
        out.selections.append({"attribute_ref": _attr_ref(attribute), "query": query,
                               "documents": [_document_key(h) for h in selected]})
        for hit in selected:
            union.setdefault(_document_key(hit), hit)
    cap = max_union_documents if max_union_documents is not None else max_documents * max(1, len(ordered))
    selected_hits = list(union.values())[:cap]

    def read_one(hit: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None, bool]:
        """One document's claims, the model error that ended it, and whether the budget refused it."""
        key = _document_key(hit)
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
            one = ordered[0]
            question = {"purpose": "candidate_attribute", "objective_text": objective_text,
                        "attribute": {"name": one["name"], "definition": one["definition"],
                                      "unit": one.get("unit"), "ref": _attr_ref(one)},
                        "candidate": candidate_spec}
        try:
            if reading_attributes:
                extracted = cache.once("extractions", (candidate["candidate_id"], key),
                                       lambda: reading.extract_claims(core, roster, stream_id, document, question,
                                                                      ids=ids, budget=budget, max_chars=max_chars))
                return list(extracted), None, False
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
    # past the document that ended the reading is read at all; at N the later documents are already in
    # flight when it fails, and their claims are dropped rather than appended out of sequence.
    outcomes: list[tuple[list[dict[str, Any]], str | None, bool]] = []
    if document_workers > 1 and len(selected_hits) > 1:
        with ThreadPoolExecutor(max_workers=min(document_workers, len(selected_hits))) as pool:
            pending = [pool.submit(read_one, hit) for hit in selected_hits]
        outcomes = [future.result() for future in pending]   # the pool has joined: every read finished
    else:
        for hit in selected_hits:
            outcome = read_one(hit)
            outcomes.append(outcome)
            if outcome[1] or outcome[2]:
                break
    for hit, (extracted, model_error, blocked) in zip(selected_hits, outcomes):
        if blocked:
            # A refusal mid-flight must leave the candidate's literature cells `not_assessed`, never a
            # short set of claims that reads like a complete one: what was gathered so far is discarded
            # with the exception, and the reading is re-done in full when the run resumes.
            raise BudgetBlocked()
        if model_error:
            out.error_ref = model_error
            return out
        out.claims += extracted
        out.documents.append(_document_key(hit))
    return out


def gather(core: Core, broker, roster, stream_id: str, *, candidate: dict[str, Any], identity: dict[str, Any],
           attribute: dict[str, Any], objective_text: str, cutoff_date: str | None, budget: Any = None,
           ids: dict | None = None, cache: LiteratureCache | None = None, max_documents: int = 2,
           case_sources: list[dict[str, Any]] | None = None,
           reading_attributes: list[dict[str, Any]] | None = None,
           sources: list[str] | None = None, limit_per_query: int | None = None,
           max_chars: int | None = None, document_workers: int = 1,
           candidate_reading: LiteratureReading | None = None,
           defer_capabilities: tuple[str, ...] = (),
           verified_supplement_refs: list[str] | tuple[str, ...] = ()) -> tuple[list[dict], str | None, list[str]]:
    """Gather claims for one cell. Returns (claims, tool_error_ref, source kinds searched).

    `defer_capabilities` are the capabilities this run holds out (`criteria.DEFERRAL_SCOPES`,
    `criteria.entry_deferred_capabilities`): those routes are not asked and the others are. The
    cell is then gathered on part of its attribute's declared evidence, which is a thing the run
    decided and the rule set's entry records -- not a thing this function may decide, so an empty
    tuple asks every route, as before.
    """
    routes = criteria.evidence_routes(attribute)
    attr_ref = f"{attribute['attribute_id']}@v{attribute['version']}"
    who = make_actor("agent", "evidence-retriever", "retriever")
    # Every route of one attribute is asked, and the cell's claims are the union: the attribute
    # names one quantity, and `assessor.assess_cell` already aggregates all of an attribute's
    # claims under its declared aggregation, so two databases answering become one median rather
    # than two cells. A route that fails does not discard what another route returned -- the
    # error reference is kept so the cell says a source errored, with the claims it did get.
    #
    # The two kinds of route are both asked where an attribute declares both (`criteria.check_attribute`
    # permits that for a quantitative attribute pooled by a numeric aggregation). The database part
    # runs here per route; the literature part is a per-candidate reading handed in below. Dispatching
    # on `is_literature_bound` alone returned at the first branch, so a mixed attribute's databases
    # were never called at all and its cell read as though no record existed.
    claims = supplements.lookup(core, verified_supplement_refs, candidate=candidate, identity=identity,
                                attribute=attribute, cutoff_date=cutoff_date)
    claims = supplements.record_reuse(core, stream_id, claims, ids=ids)
    error_ref, searched = None, (["verified_supplement_lookup"] if verified_supplement_refs else [])
    for request in [r for r in routes if r.get("capability") != "literature_retrieval"
                    and r.get("capability") not in defer_capabilities]:
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
    if not criteria.is_literature_bound(attribute) or "literature_retrieval" in defer_capabilities:
        # No literature route, or the run holds that capability out: the cell is the union of the
        # database routes that were asked. A mixed attribute's databases are still asked, which is
        # the whole point of deferring per route -- the quantity is read from the curations now and
        # the reading is bought over a shortlist later.
        return claims, error_ref, searched
    # The literature half of the cell. The reading is a per-candidate unit (`read_literature`),
    # so the sweep reads it once and hands it to every literature cell of that candidate; a caller
    # that assesses a single cell on its own gets a reading of that one attribute's selection, which
    # is what the cell used to read for itself.
    if candidate_reading is None:
        candidate_reading = read_literature(
            core, broker, roster, stream_id, candidate=candidate, identity=identity, attributes=[attribute],
            objective_text=objective_text, cutoff_date=cutoff_date, budget=budget, ids=ids, cache=cache,
            max_documents=max_documents, case_sources=case_sources, reading_attributes=reading_attributes,
            sources=sources, limit_per_query=limit_per_query, max_chars=max_chars,
            document_workers=document_workers)
    return (claims + candidate_reading.claims_for(attr_ref), error_ref or candidate_reading.error_ref,
            searched + [kind for kind in candidate_reading.searched if kind not in searched])
