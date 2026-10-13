"""Criterion derivation (design §5, §8.3; C7, C10): recall-first enumeration, proposal, critique, validation.

1. Enumerate per dimension: plan queries, search, read, and extract criterion-discovery
   claims (quotes checked) until `saturation_k` consecutive documents add no new
   attribute hint. Case-source documents are excluded from every catalog.
2. Propose: the proposer turns the discovered hints into attribute and rule proposals,
   each citing claim ids, with `expected_change` and `falsification_test`.
3. Validate deterministically: registry invariants, cited claims exist and are admitted,
   `source_stated_value` cutoffs rest on a cited value, the disclosed reference outcome is
   never named (reference-candidate scan).
4. Critique: a blind critic sees the proposals and the cited claims, never the proposer's
   rationale; its findings must reference claims or proposal fields.
5. Adjudicate deterministically: a proposal enters the registry as `proposed` (queued for
   expert confirmation) only if validation passes and the critic raised no blocking
   finding; one revision round is allowed; everything else is kept as considered-and-rejected.
"""

from __future__ import annotations

import json
from typing import Any

from . import assessor, criteria, reading
from .clock import utc_now
from .journal import actor as make_actor
from .models import ModelRequest, ModelRoster, call_role
from .runtime import Core

PROPOSAL_SCHEMA = {
    "type": "object", "required": ["proposals", "considered_and_rejected"],
    "properties": {
        "proposals": {"type": "array", "items": {"type": "object", "required": ["attribute", "rule", "supporting_claim_ids",
                                                                             "expected_change", "falsification_test"],
                                                 "properties": {"attribute": {"type": "object"}, "rule": {"type": "object"},
                                                                "supporting_claim_ids": {"type": "array", "items": {"type": "string"}},
                                                                "expected_change": {"type": "string"},
                                                                "falsification_test": {"type": "string"}}}},
        "considered_and_rejected": {"type": "array", "items": {"type": "object"}},
    },
}

CRITIQUE_SCHEMA = {
    "type": "object", "required": ["findings"],
    "properties": {"findings": {"type": "array", "items": {
        "type": "object", "required": ["proposal_index", "check", "verdict", "referent", "finding"],
        "properties": {"proposal_index": {"type": "integer"},
                       "check": {"type": "string", "enum": ["objective_conformance", "evidence_support",
                                                            "unit_applicability_consistency", "counter_evidence_considered",
                                                            "candidate_symmetric_scrutiny", "falsification_test_evaluated"]},
                       "verdict": {"type": "string", "enum": ["pass", "fail", "unknown"]},
                       "severity": {"type": "string", "enum": ["blocking", "material", "minor"]},
                       "referent": {"type": "string"}, "finding": {"type": "string"}}}}},
}

PROPOSER_SYSTEM = (
    "You propose screening criteria (attributes and rules) for an evidence-driven prioritization task. "
    "Work only from the objective, the constraints, and the claims provided (each has an id and a verbatim quote). "
    "Each proposal is one measurable attribute plus one rule. Rules are hard_exclusion (a candidate failing it is "
    "excluded) or preference (it ranks candidates). Prefer preference rules unless the objective or a constraint "
    "makes the property a requirement. A cutoff must come from a cited claim (cutoff_basis source_stated_value, "
    "and cite that claim) or be left empty with cutoff_basis none_evidence_insufficient; never invent a number. "
    "A preference rule without a cited cutoff uses predicate_form ordering: candidates are ranked by the value in "
    "the attribute's direction. "
    "Bind each attribute's evidence_request to one entry of the evidence catalog and fill its parameters. "
    "When that entry states a determination_basis, list it in the attribute's acceptable_determination_bases, "
    "or every value the source returns is set aside and the attribute carries no evidence. "
    "Never name or allude to any specific candidate compound in definitions, rationales, or rules. "
    "Merge duplicates; record what you considered and rejected, with reasons. Recall matters: cover every distinct "
    "property the claims support, across all dimensions."
)

CRITIC_SYSTEM = (
    "You are a blind critic of proposed screening criteria. You see the proposals and the claims they cite, not the "
    "proposer's reasoning. For each proposal run the checks: objective_conformance (does it serve the objective and "
    "constraints?), evidence_support (do the cited quotes actually support the attribute and any cutoff?), "
    "unit_applicability_consistency (units, direction, measurement kind coherent?), counter_evidence_considered, "
    "candidate_symmetric_scrutiny (would it treat all candidates alike, with no hidden preference for a particular "
    "compound?), falsification_test_evaluated (is the falsification test observable?). Every finding must name its "
    "referent: a claim id or a proposal field. Mark severity blocking only for a defect that should stop the "
    "proposal; findings without a referent are not allowed."
)

REVISION_SCHEMA = {
    "type": "object", "required": ["revisions"],
    "properties": {"revisions": {"type": "array", "items": {
        "type": "object", "required": ["index", "action", "reason"],
        "properties": {"index": {"type": "integer"}, "action": {"type": "string", "enum": ["revise", "withdraw"]},
                       "proposal": {"type": "object"}, "reason": {"type": "string"}}}}},
}

REVISER_SYSTEM = PROPOSER_SYSTEM + (
    " You are now revising proposals after a blind critique and deterministic validation. For each proposal listed, "
    "either revise it so every material finding is resolved, or withdraw it with the reason. Keep supporting_claim_ids "
    "to claims that actually support the attribute. Do not add new proposals."
)

# Material failures on these checks send a proposal back for one revision; still failing afterwards, it is rejected.
REVISION_CHECKS = ("objective_conformance", "evidence_support", "unit_applicability_consistency",
                   "counter_evidence_considered", "candidate_symmetric_scrutiny")

# WHY acceptable_determination_bases is in this list: it is a validated attribute field (`check_attribute`), and the
# proposer is told to declare it when a bound source returns a basis the defaults exclude. Filtering it out here left
# that instruction impossible to satisfy -- the attribute came back with the identical validator problem after every
# revision, because the declaration was stripped before the check re-read it.
ATTRIBUTE_FIELDS = ("name", "definition", "measurement_kind", "unit", "direction", "acceptable_value_sources",
                    "acceptable_determination_bases", "aggregation", "value_transform", "evidence_request",
                    "rationale")

# WHY one shared constant: both prompt builders describe the rule schema, and when the description drifts from what
# `check_rule` accepts a proposer spends revisions discovering the real contract. This listed two of the five
# predicate forms and never said that ordering ranks candidates, so a non-ranking rule had no form to reach for.
SCHEMA_BLOCK_FORMS = (
    "Rule fields: rule_kind (hard_exclusion|preference|exploratory_consideration), predicate_form "
    "(threshold|ordering|range_membership|categorical_membership|qualitative_judgment); an ordering predicate ranks "
    "candidates, so it is only valid on a preference -- an exploratory_consideration uses qualitative_judgment "
    "instead. cutoff {comparator (>=|<=|>|<|==), value, unit} or null, cutoff_basis "
    "(source_stated_value|none_evidence_insufficient), on_missing/on_inapplicable/on_conflict "
    "(unknown_no_penalty|unknown_blocks_recommendation|route_to_human).\n")
RULE_FIELDS = ("rule_kind", "predicate_form", "cutoff", "cutoff_basis", "on_missing", "on_inapplicable", "on_conflict")


def _excluded(hit: dict[str, Any], case_sources: list[dict[str, Any]]) -> bool:
    return reading.is_case_source(hit, case_sources)


def reading_order(hit: dict[str, Any]) -> tuple[bool, bool, int, int]:
    """Reading order for criterion discovery: a review or a reference entry first, then a document
    whose full text is reachable, then the hits more queries found, then the source's own rank.

    WHY a reference entry counts with the reviews: the genre flags are honest, so a drug monograph
    carries `is_review=False`. With `not is_review` as the only primary key, every monograph sorted
    below every review from every source and the per-dimension document budget never reached one —
    yet the monograph is where a measured quantity is attributable to a named compound.
    """
    return (not (hit.get("is_review") or hit.get("is_reference_entry")),
            not (hit.get("pmcid") or hit.get("source") in ("bookshelf", "uploads")),
            -len(hit.get("found_by", [])), hit.get("best_rank", 0))


# Research breadth and depth when no settings are given: one round, as before settings existed.
DEFAULT_RESEARCH = {"breadth": 5, "depth": 1, "breadth_decay": 0.5, "results_per_query": 10,
                    "max_records_screened": 300, "max_documents": 8, "saturation_k": 3, "saturation_stop": 0.0,
                    "sources": None, "max_content_chars": 60_000}


def research_params(settings) -> dict[str, Any]:
    """Research breadth and depth for derivation from resolved settings (core/config.py)."""
    if settings is None:
        return dict(DEFAULT_RESEARCH)
    return {"breadth": settings["search.breadth"], "depth": settings["search.depth"],
            "breadth_decay": settings["search.breadth_decay"], "results_per_query": settings["search.results_per_query"],
            "max_records_screened": settings["search.max_records_screened"],
            "max_documents": settings["read.max_papers_full_read"], "saturation_k": DEFAULT_RESEARCH["saturation_k"],
            "saturation_stop": settings["search.saturation_stop"], "sources": list(settings["search.sources"]),
            "max_content_chars": settings["read.max_content_chars"]}


def enumerate_dimension(core: Core, broker, roster: ModelRoster, stream_id: str, *, task_context: dict[str, Any],
                        dimension: dict[str, str], cutoff_date: str | None, saturation_k: int | None = None,
                        max_documents: int | None = None, ids: dict | None = None, budget: Any = None,
                        all_dimensions: list[dict[str, str]] | None = None,
                        read_cache: dict[str, list[dict[str, Any]]] | None = None,
                        research: dict[str, Any] | None = None) -> dict[str, Any]:
    """Recall-first enumeration for one dimension: breadth x depth rounds of search and reading.

    Round 0 plans `breadth` queries. Each later round plans queries from what was already
    searched and learned (gaps, alternatives, counter-evidence), with breadth multiplied by
    `breadth_decay`. Reading within a round stops after `saturation_k` consecutive documents
    add no new topic; rounds stop at the document cap, when no new records turn up, or when
    the share of documents adding a new topic falls below `saturation_stop`.
    Returns hints, claims, per-round statistics, the stop reason, and a visibility manifest.
    """
    r = dict(DEFAULT_RESEARCH, **(research or {}))
    if max_documents is not None:
        r["max_documents"] = max_documents
    if saturation_k is not None:
        r["saturation_k"] = saturation_k
    objective = task_context["objective_text"]
    scope = ", ".join(e.get("label") or e.get("identifier", "") for e in task_context.get("scope_entities", []))
    focus = f"{dimension['focus']} as criteria for: {objective}" + (f" (scope: {scope})" if scope else "")
    case_sources = task_context.get("case_source_documents", [])
    all_queries: list[dict[str, str]] = []
    coverage_ids: list[str] = []
    seen: set[str] = set()
    included_all: list[dict[str, Any]] = []
    excluded_all: list[dict[str, Any]] = []
    hints: dict[str, list[str]] = {}
    claims: list[dict[str, Any]] = []
    read_count, rounds, stop_reason = 0, [], "depth_reached"
    breadth = float(r["breadth"])
    for level in range(int(r["depth"])):
        queries = reading.plan_queries(core, roster, stream_id, objective_text=objective, focus=focus,
                                       max_queries=max(1, round(breadth)), ids=ids, budget=budget,
                                       searched=[q["query"] for q in all_queries] if level else None,
                                       learned=list(hints)[:40] if level else None)
        all_queries += queries
        hits, coverage_id = reading.search(core, broker, stream_id, [q["query"] for q in queries], cutoff_date=cutoff_date,
                                           limit_per_query=r["results_per_query"], ids=ids, budget=budget,
                                           sources=r["sources"])
        coverage_ids.append(coverage_id)
        room = max(0, int(r["max_records_screened"]) - len(seen))
        fresh = [h for h in hits if reading._key(h) not in seen][:room]
        seen.update(reading._key(h) for h in fresh)
        included = [h for h in fresh if not _excluded(h, case_sources)]
        excluded_all += [h for h in fresh if _excluded(h, case_sources)]
        included.sort(key=reading_order)
        included_all += included
        stale, documents, contributing, new_topics = 0, 0, 0, 0
        for hit in included:
            if read_count >= r["max_documents"] or stale >= r["saturation_k"]:
                break
            key = reading._key(hit)
            if read_cache is not None and key in read_cache:
                found = read_cache[key]          # read once across dimensions; its claims cover every dimension
            else:
                document = reading.read(core, broker, stream_id, hit, ids=ids, budget=budget, cutoff_date=cutoff_date)
                if document is None:
                    continue
                found = reading.extract_claims(core, roster, stream_id, document, {
                    "purpose": "criterion_discovery", "objective_text": objective + (f" Scope: {scope}." if scope else ""),
                    "dimensions": all_dimensions or [dimension], "attribute": None, "candidate": None}, ids=ids, budget=budget,
                    max_chars=r["max_content_chars"])
                if read_cache is not None:
                    read_cache[key] = found
            read_count += 1
            documents += 1
            new = 0
            for claim in found:
                if claim["admission_state"] != "admitted":
                    continue
                claims.append(claim)
                hint = reading.normalize_for_match(claim.get("attribute_hint") or claim["normalized_statement"])[:80]
                if hint not in hints:
                    new += 1
                hints.setdefault(hint, []).append(claim["claim_id"])
            contributing += 1 if new else 0
            new_topics += new
            stale = 0 if new else stale + 1
        novelty = contributing / documents if documents else 0.0
        rounds.append({"round": level, "queries": len(queries), "new_records": len(fresh), "documents_read": documents,
                       "new_topics": new_topics, "novelty": round(novelty, 3), "coverage_id": coverage_id})
        if read_count >= r["max_documents"]:
            stop_reason = "document_cap"
            break
        if not fresh:
            stop_reason = "no_new_records"
            break
        if documents and novelty < r["saturation_stop"]:
            stop_reason = "saturated"
            break
        breadth *= r["breadth_decay"]
    manifest = {"actor": "derivation", "subject": dimension["dimension"], "catalog_size": len(seen),
                "included_ids": [reading._key(h) for h in included_all],
                "excluded": [{"id": reading._key(h), "omitted_reason": "case_source_document"} for h in excluded_all]
                + [{"id": "historical_criteria_intake", "omitted_reason": "evaluator_only_artifact"}],
                "content_hash": None, "recorded_at": utc_now()}
    manifest_id = core.artifacts.put("visibility_manifest", manifest)
    return {"dimension": dimension["dimension"], "queries": all_queries, "coverage_id": coverage_ids[0] if coverage_ids else None,
            "coverage_ids": coverage_ids, "manifest_id": manifest_id, "documents_read": read_count,
            "saturated": stop_reason in ("saturated", "no_new_records"),
            "rounds": rounds, "stop_reason": stop_reason, "research": {k: v for k, v in r.items()},
            "hints": hints, "claims": claims}


def _claims_block(claims: list[dict[str, Any]]) -> str:
    lines = []
    for claim in claims:
        lines.append(json.dumps({"claim_id": claim["claim_id"], "attribute_hint": claim.get("attribute_hint"),
                                 "quote": claim["location"]["quoted_span"], "value": claim.get("value"),
                                 "range": [claim.get("value_low"), claim.get("value_high")]
                                 if claim.get("value_low") is not None or claim.get("value_high") is not None else None,
                                 "unit": claim.get("unit"),
                                 "source": claim["source_ref"], "basis": claim["determination_basis"]}, ensure_ascii=False))
    return "\n".join(lines)


def validate_proposal(proposal: dict[str, Any], *, claims_by_id: dict[str, dict[str, Any]],
                      reference_labels: list[str], catalog: list[dict[str, Any]]) -> list[str]:
    """Deterministic validator findings for one proposal (empty list = valid)."""
    problems = []
    attribute, rule = proposal.get("attribute", {}), proposal.get("rule", {})
    try:
        criteria.check_attribute(attribute)
        criteria.check_rule(rule, attribute)
    except criteria.InvariantViolation as violation:
        problems.append(f"{violation.finding_class}: {violation}")
    cited = proposal.get("supporting_claim_ids", [])
    missing = [c for c in cited if c not in claims_by_id]
    if not cited:
        problems.append("evidence_support: no supporting claims cited")
    if missing:
        problems.append(f"evidence_support: cited claims not in the ledger {missing}")
    if rule.get("cutoff_basis") == "source_stated_value":
        values = [claims_by_id[c] for c in cited if c in claims_by_id
                  and any(claims_by_id[c].get(k) is not None for k in ("value", "value_low", "value_high"))]
        if not values:
            problems.append("arbitrary_cutoff: source_stated_value cutoff without a cited claim carrying a value")
    request = attribute.get("evidence_request") or {}
    entry = next((e for e in catalog if e["capability"] == request.get("capability")
                  and e["question_kind"] == request.get("question_kind")), None)
    if entry is None:
        problems.append("schema: evidence_request is not bound to a catalog entry")
    elif entry.get("determination_basis"):
        # The source states what its records are. An attribute that does not accept that basis has
        # every value it receives set aside at assessment time, which reads as "no data" rather than
        # as a mistake, so the pairing is refused here instead.
        accepted = list(attribute.get("acceptable_determination_bases") or assessor.DEFAULT_DETERMINATION_BASES)
        if entry["determination_basis"] not in accepted:
            problems.append(f"evidence_support: the bound source returns {entry['determination_basis']} records and "
                            f"acceptable_determination_bases {accepted} excludes that basis, so every value it returns "
                            f"would be set aside and the attribute would carry no evidence")
    if request.get("capability") == "literature_retrieval" and not (attribute.get("measurement_kind") == "quantitative"
                                                                     and attribute.get("unit")):
        problems.append("schema: literature evidence yields numbers with units; a literature-bound attribute must be "
                        "quantitative with a unit")
    text = json.dumps({k: attribute.get(k) for k in ("name", "definition", "rationale")} | {"rule": rule}, ensure_ascii=False)
    if reference_labels and reading.names_entity(reference_labels, text):
        problems.append("reference_candidate_scan: a proposal names the disclosed reference outcome")
    return problems


def _normalize_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    attribute = {k: v for k, v in proposal.get("attribute", {}).items() if k in ATTRIBUTE_FIELDS}
    rule = {k: v for k, v in proposal.get("rule", {}).items() if k in RULE_FIELDS}
    if rule.get("cutoff") in ({}, None) or rule.get("cutoff_basis") == "none_evidence_insufficient":
        rule["cutoff"] = None if rule.get("cutoff_basis") == "none_evidence_insufficient" else rule.get("cutoff")
    return dict(proposal, attribute=attribute, rule=rule)


def objective_criteria(core: Core, task_id: str, *, templates, by: dict[str, Any]) -> list[dict[str, Any]]:
    """Criteria the task itself mandates (required scope entities, hard constraints), built by adapter templates.

    `templates(task_context)` returns [{"attribute", "rule", "source_field"}]. Each is proposed with
    `derived_from: task_context` and its source field, skipping any whose evidence key is already registered.
    Hard exclusions among them still need an expert decision (trigger table).
    """
    from . import task as task_mod
    context = task_mod.get(core, task_id)
    existing = {criteria.evidence_key(a) for a in criteria.registered_attributes(core, task_id)}
    who = make_actor("system", "objective-criteria", "adapter_template")
    added = []
    for item in templates(context):
        if criteria.evidence_key(item["attribute"]) in existing:
            continue
        attribute = dict(item["attribute"], derived_from={"task_context": f"{task_id}@v{context['version']}",
                                                           "field": item["source_field"]})
        attr_ref, rule_ref = criteria.propose(core, task_id, attribute, item["rule"], by=who)
        existing.add(criteria.evidence_key(item["attribute"]))
        added.append({"attribute_ref": attr_ref, "rule_ref": rule_ref, "name": attribute["name"],
                      "rule_kind": item["rule"]["rule_kind"], "source_field": item["source_field"]})
    return added


def derive(core: Core, broker, roster: ModelRoster, task_id: str, *, dimensions: list[dict[str, str]],
           catalog: list[dict[str, Any]], by: dict[str, Any], cutoff_date: str | None = None, saturation_k: int = 3,
           max_documents: int | None = None, budget: Any = None, stream_id: str | None = None, templates=None,
           research: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run derivation for a task; accepted proposals enter the registry and the review queue.

    Objective-mandated criteria (adapter `templates`) are registered first; literature-derived proposals
    that duplicate a registered attribute are recorded as duplicates. Proposals still disputed after one
    revision enter the registry with a review item showing the open findings; the expert decides.
    """
    from . import task as task_mod
    mandated = objective_criteria(core, task_id, templates=templates, by=by) if templates else []
    context = task_mod.get(core, task_id)
    stream_id = stream_id or task_id
    ids = {"task_id": task_id}
    read_cache: dict[str, list[dict[str, Any]]] = {}
    enumerations = [enumerate_dimension(core, broker, roster, stream_id, task_context=context, dimension=d,
                                        cutoff_date=cutoff_date, saturation_k=saturation_k, max_documents=max_documents,
                                        ids=ids, budget=budget, all_dimensions=dimensions, read_cache=read_cache,
                                        research=research)
                    for d in dimensions]
    claims = list({c["claim_id"]: c for e in enumerations for c in e["claims"]}.values())
    claims_by_id = {c["claim_id"]: c for c in claims}
    reference_labels = [label for seed in context.get("seed_candidates", []) if seed.get("is_reference_outcome")
                        for label in [seed["candidate_ref"], *seed.get("aliases", [])]]
    scope = json.dumps(context.get("scope_entities", []), ensure_ascii=False)
    prompt = (f"Objective: {context['objective_text']}\nConstraints: {json.dumps(context.get('constraints', []), ensure_ascii=False)}\n"
              f"Scope entities: {scope}\nDimensions: {', '.join(d['dimension'] for d in dimensions)}\n"
              f"Criteria already registered from the task itself (do not duplicate them): "
              f"{json.dumps([a['name'] for a in criteria.registered_attributes(core, task_id)], ensure_ascii=False)}\n\n"
              f"Evidence catalog (bind each attribute's evidence_request to one entry):\n{json.dumps(catalog, ensure_ascii=False, indent=1)}\n\n"
              f"Attribute fields: name, definition, measurement_kind (quantitative|ordinal|categorical|qualitative_determination), "
              f"unit, direction (higher_better|lower_better|within_range|target_value|non_directional|undetermined), "
              f"acceptable_value_sources (evidence kinds: curated_measurement, database_entry, peer_reviewed, preprint, "
              f"reference_text, tertiary_reference, user_supplied_document), "
              f"acceptable_determination_bases (defaults to measured and derived), "
              f"value_transform when the attribute is about a derived quantity rather than the value the source "
              f"returns -- {{kind: excess_above|shortfall_below|distance_outside_band, bound or low and high, "
              f"basis, source_refs}}; without it the raw value is what gets ranked, however the definition "
              f"describes the quantity, "
              f"aggregation (max|min|consensus), evidence_request {{capability, question_kind, identifier_scheme, parameters}}, rationale.\n"
              + SCHEMA_BLOCK_FORMS
              + f"\nClaims ({len(claims)}):\n{_claims_block(claims)}")
    proposer = call_role(core, roster, stream_id, ModelRequest(
        role="proposer", system=PROPOSER_SYSTEM, messages=[{"role": "user", "content": prompt}],
        response_schema=PROPOSAL_SCHEMA, max_tokens=12000, metadata={"question": "propose criteria"}), ids=ids, budget=budget)
    proposals = [_normalize_proposal(p) for p in proposer.data["proposals"]]
    rejected = list(proposer.data["considered_and_rejected"])

    def run_validator(items: dict[int, dict[str, Any]]) -> dict[int, list[str]]:
        return {i: validate_proposal(p, claims_by_id=claims_by_id, reference_labels=reference_labels, catalog=catalog)
                for i, p in items.items()}

    def run_critic(items: dict[int, dict[str, Any]], prior: list[dict[str, Any]] | None = None):
        critique_input = [{"index": i, "attribute": p["attribute"], "rule": p["rule"],
                           "supporting_claim_ids": p["supporting_claim_ids"], "falsification_test": p["falsification_test"]}
                          for i, p in items.items()]
        cited = {c for p in items.values() for c in p["supporting_claim_ids"] if c in claims_by_id}
        revision_note = ("\n\nThis is a revision check. Your earlier findings on these proposals were:\n"
                         + json.dumps(prior, ensure_ascii=False, indent=1)) if prior else ""
        response = call_role(core, roster, stream_id, ModelRequest(
            role="critic", system=CRITIC_SYSTEM, response_schema=CRITIQUE_SCHEMA, max_tokens=8000,
            messages=[{"role": "user", "content": f"Objective: {context['objective_text']}\n\nProposals:\n"
                       f"{json.dumps(critique_input, ensure_ascii=False, indent=1)}\n\nCited claims:\n"
                       f"{_claims_block([claims_by_id[c] for c in sorted(cited)])}{revision_note}"}],
            metadata={"question": "revision check" if prior else "critique proposals"}), ids=ids, budget=budget)
        return response, [f for f in response.data["findings"] if f.get("referent")]

    def classify(index: int, problems: list[str], findings: list[dict[str, Any]]) -> str:
        mine = [f for f in findings if f["proposal_index"] == index and f["verdict"] == "fail"]
        if problems or any(f.get("severity") == "blocking" for f in mine):
            return "blocked"
        if any(f["check"] in REVISION_CHECKS and f.get("severity", "material") == "material" for f in mine):
            return "revise"
        return "accept"

    items = dict(enumerate(proposals))
    validator = run_validator(items)
    critic, findings = run_critic(items)
    status = {i: classify(i, validator[i], findings) for i in items}
    to_revise = {i: p for i, p in items.items() if status[i] in ("revise", "blocked")}
    revision_record: list[dict[str, Any]] = []
    if to_revise:
        notes = [{"index": i, "attribute": p["attribute"], "rule": p["rule"],
                  "supporting_claim_ids": p["supporting_claim_ids"], "expected_change": p["expected_change"],
                  "falsification_test": p["falsification_test"], "validator_problems": validator[i],
                  "critic_findings": [f for f in findings if f["proposal_index"] == i and f["verdict"] == "fail"]}
                 for i, p in to_revise.items()]
        reviser = call_role(core, roster, stream_id, ModelRequest(
            role="proposer", system=REVISER_SYSTEM, response_schema=REVISION_SCHEMA, max_tokens=12000,
            messages=[{"role": "user", "content": prompt + "\n\nProposals to revise or withdraw:\n"
                       + json.dumps(notes, ensure_ascii=False, indent=1)}],
            metadata={"question": "revise proposals"}), ids=ids, budget=budget)
        revised: dict[int, dict[str, Any]] = {}
        for revision in reviser.data["revisions"]:
            index = revision["index"]
            if index not in to_revise:
                continue
            revision_record.append({"index": index, "action": revision["action"], "reason": revision["reason"]})
            if revision["action"] == "revise" and revision.get("proposal"):
                merged = dict(to_revise[index], **revision["proposal"])
                revised[index] = _normalize_proposal(merged)
        for index in to_revise:
            if index not in revised:
                status[index] = "withdrawn"
        if revised:
            validator.update(run_validator(revised))
            prior = [f for f in findings if f["proposal_index"] in revised and f["verdict"] == "fail"]
            critic, recheck = run_critic(revised, prior)
            findings = [f for f in findings if f["proposal_index"] not in revised] + recheck
            for index, proposal in revised.items():
                items[index] = proposal
                after = classify(index, validator[index], findings)
                status[index] = "accept" if after == "accept" else "unresolved_after_revision"
    accepted = []
    who = make_actor("agent", f"proposer:{proposer.model_id}", "proposer", model_family=roster.adapter("proposer").record.provider_family)
    registered_keys = {criteria.evidence_key(a) for a in criteria.registered_attributes(core, task_id)}
    disputed = []
    for index, proposal in items.items():
        mine = [f for f in findings if f["proposal_index"] == index]
        if status[index] == "accept" and criteria.evidence_key(proposal["attribute"]) in registered_keys:
            status[index] = "duplicate_of_registered"
        if status[index] not in ("accept", "unresolved_after_revision") or (status[index] == "unresolved_after_revision"
                                                                              and validator[index]):
            rejected.append({"attribute": proposal["attribute"].get("name"), "validator": validator[index],
                             "critic": [f for f in mine if f["verdict"] == "fail"], "rejection_reason": status[index]})
            continue
        attribute = dict(proposal["attribute"], rationale=proposal["attribute"].get("rationale", ""),
                         supporting_claim_refs=proposal["supporting_claim_ids"],
                         derived_from={"proposal_request": proposer.request_id, "critique_request": critic.request_id})
        rule = dict(proposal["rule"], expected_change=proposal["expected_change"],
                    falsification_test=proposal["falsification_test"],
                    dissent=[f for f in mine if f["verdict"] == "fail"])
        if criteria.evidence_key(attribute) in registered_keys:
            rejected.append({"attribute": attribute["name"], "validator": [], "critic": [], "rejection_reason": "duplicate_of_registered"})
            continue
        dispute = None
        if status[index] == "unresolved_after_revision":
            dispute = {"open_critic_findings": [f for f in mine if f["verdict"] == "fail"],
                       "proposal_request": proposer.request_id, "critique_request": critic.request_id}
        attr_ref, rule_ref = criteria.propose(core, task_id, attribute, rule, by=who, dispute=dispute)
        registered_keys.add(criteria.evidence_key(attribute))
        entry = {"attribute_ref": attr_ref, "rule_ref": rule_ref, "name": attribute["name"],
                 "rule_kind": rule["rule_kind"], "critic_findings": mine}
        (disputed if dispute else accepted).append(entry)
    record = {"task_id": task_id, "dimensions": [{k: e[k] for k in ("dimension", "documents_read", "saturated",
                                                                      "coverage_id", "manifest_id")}
                                                 | {"n_hints": len(e["hints"]), "n_claims": len(e["claims"])} for e in enumerations],
              "mandated": mandated, "accepted": accepted, "disputed": disputed,
              "considered_and_rejected": rejected, "revisions": revision_record,
              "proposer_model": proposer.model_id,
              "critic_model": critic.model_id,
              "independence": {"proposer_family": roster.adapter("proposer").record.provider_family,
                               "critic_family": roster.adapter("critic").record.provider_family,
                               "same_adapter": roster.roles.get("proposer") == roster.roles.get("critic"),
                               "saw_proposer_rationale": False}}
    record["artifact_id"] = core.artifacts.put("derivation_record", record)
    return record
