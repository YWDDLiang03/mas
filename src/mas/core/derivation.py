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

from . import criteria, reading
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

ATTRIBUTE_FIELDS = ("name", "definition", "measurement_kind", "unit", "direction", "acceptable_value_sources",
                    "aggregation", "evidence_request", "rationale")
RULE_FIELDS = ("rule_kind", "predicate_form", "cutoff", "cutoff_basis", "on_missing", "on_inapplicable", "on_conflict")


def _excluded(hit: dict[str, Any], case_sources: list[dict[str, Any]]) -> bool:
    return reading.is_case_source(hit, case_sources)


def enumerate_dimension(core: Core, broker, roster: ModelRoster, stream_id: str, *, task_context: dict[str, Any],
                        dimension: dict[str, str], cutoff_date: str | None, saturation_k: int = 3,
                        max_documents: int = 8, ids: dict | None = None, budget: Any = None) -> dict[str, Any]:
    """Recall-first enumeration for one dimension; returns hints, claims, and a visibility manifest."""
    objective = task_context["objective_text"]
    scope = ", ".join(e.get("label") or e.get("identifier", "") for e in task_context.get("scope_entities", []))
    focus = f"{dimension['focus']} as criteria for: {objective}" + (f" (scope: {scope})" if scope else "")
    queries = reading.plan_queries(core, roster, stream_id, objective_text=objective, focus=focus, max_queries=5,
                                   ids=ids, budget=budget)
    hits, coverage_id = reading.search(core, broker, stream_id, [q["query"] for q in queries], cutoff_date=cutoff_date,
                                       limit_per_query=10, ids=ids, budget=budget)
    case_sources = task_context.get("case_source_documents", [])
    included, excluded = [], []
    for hit in hits:
        (excluded if _excluded(hit, case_sources) else included).append(hit)
    included.sort(key=lambda h: (not h.get("is_review"), not h.get("pmcid"), -len(h.get("found_by", [])), h.get("best_rank", 0)))
    hints: dict[str, list[str]] = {}
    claims: list[dict[str, Any]] = []
    stale, read_count = 0, 0
    for hit in included:
        if read_count >= max_documents or stale >= saturation_k:
            break
        document = reading.read(core, broker, stream_id, hit, ids=ids, budget=budget)
        if document is None:
            continue
        read_count += 1
        found = reading.extract_claims(core, roster, stream_id, document, {
            "purpose": "criterion_discovery", "objective_text": objective + (f" Scope: {scope}." if scope else ""),
            "attribute": None, "candidate": None}, ids=ids, budget=budget)
        new = 0
        for claim in found:
            if claim["admission_state"] != "admitted":
                continue
            claims.append(claim)
            hint = reading.normalize_for_match(claim.get("attribute_hint") or claim["normalized_statement"])[:80]
            if hint not in hints:
                new += 1
            hints.setdefault(hint, []).append(claim["claim_id"])
        stale = 0 if new else stale + 1
    manifest = {"actor": "derivation", "subject": dimension["dimension"], "catalog_size": len(hits),
                "included_ids": [reading._key(h) for h in included],
                "excluded": [{"id": reading._key(h), "omitted_reason": "case_source_document"} for h in excluded]
                + [{"id": "historical_criteria_intake", "omitted_reason": "evaluator_only_artifact"}],
                "content_hash": None, "recorded_at": utc_now()}
    manifest_id = core.artifacts.put("visibility_manifest", manifest)
    return {"dimension": dimension["dimension"], "queries": queries, "coverage_id": coverage_id, "manifest_id": manifest_id,
            "documents_read": read_count, "saturated": stale >= saturation_k, "hints": hints, "claims": claims}


def _claims_block(claims: list[dict[str, Any]]) -> str:
    lines = []
    for claim in claims:
        lines.append(json.dumps({"claim_id": claim["claim_id"], "attribute_hint": claim.get("attribute_hint"),
                                 "quote": claim["location"]["quoted_span"], "value": claim.get("value"), "unit": claim.get("unit"),
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
        values = [claims_by_id[c] for c in cited if c in claims_by_id and claims_by_id[c].get("value") is not None]
        if not values:
            problems.append("arbitrary_cutoff: source_stated_value cutoff without a cited claim carrying a value")
    request = attribute.get("evidence_request") or {}
    if not any(entry["capability"] == request.get("capability") and entry["question_kind"] == request.get("question_kind")
               for entry in catalog):
        problems.append("schema: evidence_request is not bound to a catalog entry")
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


def derive(core: Core, broker, roster: ModelRoster, task_id: str, *, dimensions: list[dict[str, str]],
           catalog: list[dict[str, Any]], by: dict[str, Any], cutoff_date: str | None = None, saturation_k: int = 3,
           max_documents: int = 8, budget: Any = None, stream_id: str | None = None) -> dict[str, Any]:
    """Run derivation for a task; accepted proposals enter the registry and the review queue."""
    from . import task as task_mod
    context = task_mod.get(core, task_id)
    stream_id = stream_id or task_id
    ids = {"task_id": task_id}
    enumerations = [enumerate_dimension(core, broker, roster, stream_id, task_context=context, dimension=d,
                                        cutoff_date=cutoff_date, saturation_k=saturation_k, max_documents=max_documents,
                                        ids=ids, budget=budget) for d in dimensions]
    claims = [c for e in enumerations for c in e["claims"]]
    claims_by_id = {c["claim_id"]: c for c in claims}
    reference_labels = [label for seed in context.get("seed_candidates", []) if seed.get("is_reference_outcome")
                        for label in [seed["candidate_ref"], *seed.get("aliases", [])]]
    scope = json.dumps(context.get("scope_entities", []), ensure_ascii=False)
    prompt = (f"Objective: {context['objective_text']}\nConstraints: {json.dumps(context.get('constraints', []), ensure_ascii=False)}\n"
              f"Scope entities: {scope}\nDimensions: {', '.join(d['dimension'] for d in dimensions)}\n\n"
              f"Evidence catalog (bind each attribute's evidence_request to one entry):\n{json.dumps(catalog, ensure_ascii=False, indent=1)}\n\n"
              f"Attribute fields: name, definition, measurement_kind (quantitative|ordinal|categorical|qualitative_determination), "
              f"unit, direction (higher_better|lower_better|within_range|target_value|non_directional|undetermined), "
              f"acceptable_value_sources (evidence kinds: curated_measurement, database_entry, peer_reviewed, preprint), "
              f"aggregation (max|min|consensus), evidence_request {{capability, question_kind, identifier_scheme, parameters}}, rationale.\n"
              f"Rule fields: rule_kind (hard_exclusion|preference|exploratory_consideration), predicate_form (threshold|ordering), cutoff {{comparator (>=|<=|>|<|==), value, unit}} or null, "
              f"cutoff_basis (source_stated_value|none_evidence_insufficient), on_missing/on_inapplicable/on_conflict "
              f"(unknown_no_penalty|unknown_blocks_recommendation|route_to_human).\n\nClaims ({len(claims)}):\n{_claims_block(claims)}")
    proposer = call_role(core, roster, stream_id, ModelRequest(
        role="proposer", system=PROPOSER_SYSTEM, messages=[{"role": "user", "content": prompt}],
        response_schema=PROPOSAL_SCHEMA, max_tokens=12000, metadata={"question": "propose criteria"}), ids=ids, budget=budget)
    proposals = [_normalize_proposal(p) for p in proposer.data["proposals"]]
    accepted, rejected = [], list(proposer.data["considered_and_rejected"])
    validator = {i: validate_proposal(p, claims_by_id=claims_by_id, reference_labels=reference_labels, catalog=catalog)
                 for i, p in enumerate(proposals)}
    critique_input = [{"index": i, "attribute": p["attribute"], "rule": p["rule"], "supporting_claim_ids": p["supporting_claim_ids"],
                       "falsification_test": p["falsification_test"]} for i, p in enumerate(proposals)]
    cited = {c for p in proposals for c in p["supporting_claim_ids"] if c in claims_by_id}
    critic = call_role(core, roster, stream_id, ModelRequest(
        role="critic", system=CRITIC_SYSTEM, response_schema=CRITIQUE_SCHEMA, max_tokens=8000,
        messages=[{"role": "user", "content": f"Objective: {context['objective_text']}\n\nProposals:\n"
                   f"{json.dumps(critique_input, ensure_ascii=False, indent=1)}\n\nCited claims:\n"
                   f"{_claims_block([claims_by_id[c] for c in sorted(cited)])}"}],
        metadata={"question": "critique proposals"}), ids=ids, budget=budget)
    findings = [f for f in critic.data["findings"] if f.get("referent")]
    blocking = {f["proposal_index"] for f in findings if f["verdict"] == "fail" and f.get("severity", "material") == "blocking"}
    who = make_actor("agent", f"proposer:{proposer.model_id}", "proposer", model_family=roster.adapter("proposer").record.provider_family)
    refs = []
    for index, proposal in enumerate(proposals):
        problems = validator[index]
        if problems or index in blocking:
            rejected.append({"attribute": proposal["attribute"].get("name"), "validator": problems,
                             "critic": [f for f in findings if f["proposal_index"] == index and f["verdict"] == "fail"],
                             "rejection_reason": "validator" if problems else "critic_blocking"})
            continue
        attribute = dict(proposal["attribute"], rationale=proposal["attribute"].get("rationale", ""),
                         supporting_claim_refs=proposal["supporting_claim_ids"],
                         derived_from={"proposal_request": proposer.request_id, "critique_request": critic.request_id})
        rule = dict(proposal["rule"], expected_change=proposal["expected_change"],
                    falsification_test=proposal["falsification_test"])
        attr_ref, rule_ref = criteria.propose(core, task_id, attribute, rule, by=who)
        accepted.append({"attribute_ref": attr_ref, "rule_ref": rule_ref, "name": attribute["name"],
                         "critic_findings": [f for f in findings if f["proposal_index"] == index]})
        refs.append(rule_ref)
    record = {"task_id": task_id, "dimensions": [{k: e[k] for k in ("dimension", "documents_read", "saturated",
                                                                      "coverage_id", "manifest_id")}
                                                 | {"n_hints": len(e["hints"]), "n_claims": len(e["claims"])} for e in enumerations],
              "accepted": accepted, "considered_and_rejected": rejected, "proposer_model": proposer.model_id,
              "critic_model": critic.model_id,
              "independence": {"proposer_family": roster.adapter("proposer").record.provider_family,
                               "critic_family": roster.adapter("critic").record.provider_family,
                               "saw_proposer_rationale": False}}
    record["artifact_id"] = core.artifacts.put("derivation_record", record)
    return record
