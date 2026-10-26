"""Grounded display projections. These are not model-written research syntheses."""
from __future__ import annotations

import json
import re
from typing import Any


def criterion_display_fields(attribute: dict[str, Any]) -> dict[str, str]:
    """Alias a misleading prediction prefix only for explicitly derived-only quantities."""
    name = attribute.get("name")
    if not isinstance(name, str) or attribute.get("acceptable_determination_bases") != ["derived"]:
        return {}
    match = re.fullmatch(r"Predicted\s+(.+?)\s*", name)
    return {"display_name": f"{match[1]} (calculated)"} if match else {}


def text(value: Any) -> str | None:
    if value is None or value == "" or value == [] or value == {}:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "; ".join(f"{key}: {text(item)}" for key, item in value.items() if text(item) is not None) or None
    if isinstance(value, (list, tuple)):
        return "; ".join(str(text(item)) for item in value if text(item) is not None) or None
    return str(value)


def claim_context(claim: dict[str, Any]) -> dict[str, Any]:
    scope, conditions = claim.get("scope") or {}, claim.get("conditions") or {}
    scope = scope if isinstance(scope, dict) else {"population_or_system": scope}
    conditions = conditions if isinstance(conditions, dict) else {"recorded": conditions}
    population = text(scope.get("population_or_system") or conditions.get("population") or conditions.get("species"))
    assay = text(claim.get("assay") or conditions.get("assay") or conditions.get("assay_type"))
    limitations = claim.get("limitations") or []
    limitations = list(limitations) if isinstance(limitations, list) else [str(limitations)]
    if not population:
        limitations.append("The population or experimental system was not recorded in this claim.")
    if not assay and claim.get("determination_basis") == "measured":
        limitations.append("An assay description was not recorded in this claim.")
    if claim.get("scope_match") in (None, "unknown"):
        limitations.append("Applicability to this task has not been established by this claim's scope record.")
    if claim.get("determination_basis") == "predicted":
        limitations.append("This is a model prediction, not a directly observed outcome.")
    elif claim.get("determination_basis") == "asserted":
        limitations.append("This is a source assertion; it is not itself a candidate-specific measurement.")
    return {"population": population, "assay": assay, "conditions": text(conditions),
            "units": claim.get("unit"), "limitations": list(dict.fromkeys(limitations)),
            "entities": [str(v) for v in claim.get("entities") or []],
            "evidence_kind": claim.get("evidence_kind"), "reading_depth": claim.get("reading_depth"),
            "verification_status": claim.get("verification_status")}


def fact_summary(claim: dict[str, Any]) -> dict[str, Any]:
    statement = claim.get("normalized_statement") or claim.get("claim_text")
    if not statement:
        value = claim.get("value")
        interval = (claim.get("value_low"), claim.get("value_high"))
        observed = text(value) if value is not None else f"{interval[0]} to {interval[1]}" if None not in interval else "not recorded"
        statement = f"Recorded {claim.get('attribute_hint') or 'observation'}: {observed} {claim.get('unit') or ''}.".strip()
    return {"text": statement, "method": "recorded_fact_projection", "derived": True,
            "claim_refs": [claim["claim_id"]] if claim.get("claim_id") else []}


def original_context(document: dict[str, Any], location: dict[str, Any]) -> dict[str, Any]:
    passages = [p for p in document.get("passages") or [] if isinstance(p, dict) and p.get("text")]
    locator, quote = location.get("locator_value"), location.get("quoted_span")
    matches = [i for i, passage in enumerate(passages) if passage.get("passage_id") == locator]
    basis = "locator"
    if not matches and quote:
        normalize = lambda s: re.sub(r"\s+", " ", str(s)).strip()
        matches = [i for i, passage in enumerate(passages) if normalize(quote) in normalize(passage["text"])]
        basis = "unique_verbatim_excerpt"
    if len(matches) != 1:
        return {"passage": None, "before": None, "after": None, "context_available": False,
                "context_status": "ambiguous_passage" if matches else "no_saved_matching_passage"}
    def view(index):
        if not 0 <= index < len(passages):
            return None
        p = passages[index]
        return {"passage_id": p.get("passage_id"), "section_path": p.get("section_path") or [], "text": p["text"]}
    index = matches[0]
    return {"passage": view(index), "before": view(index - 1), "after": view(index + 1),
            "context_available": True, "context_status": "saved_original", "match_basis": basis}


def criterion_explanation(attribute: dict[str, Any], rule: dict[str, Any], raw: dict[str, Any],
                          sources: list[dict[str, Any]]) -> dict[str, Any]:
    name = criterion_display_fields(attribute).get("display_name") or attribute.get("name") or "this criterion"
    transform = attribute.get("value_transform") or {}
    if transform.get("kind") == "distance_outside_band":
        calculation = f"For each usable value x, calculate max({transform.get('low')}-x, 0, x-{transform.get('high')}). "
    elif transform:
        calculation = f"Apply the recorded {transform.get('kind')} transformation to each usable value. "
    else:
        calculation = "Use the accepted source values without an added transformation. "
    calculation += f"Combine usable values using {attribute.get('aggregation', 'consensus')}. "
    cutoff = rule.get("cutoff")
    if isinstance(cutoff, dict):
        question = f"Does {name} meet the recorded comparison?"
        calculation += f"Compare the result {cutoff.get('comparator')} {text(cutoff.get('value'))} {cutoff.get('unit') or ''}."
    elif rule.get("predicate_form") == "ordering":
        direction = {"lower_better": "smaller", "higher_better": "larger"}.get(attribute.get("direction"), attribute.get("direction") or "unspecified")
        question = f"Which candidates have a more favourable {name}?"
        calculation += f"Order available values with {direction} values preferred; no cutoff is applied."
    elif rule.get("predicate_form") == "recorded_observation":
        question = f"What observation has been recorded for {name}?"
        calculation += "Record whether an observation is available, without a pass/fail judgement or a ranking score."
    else:
        question = f"What is recorded about {name}?"
        calculation += "No executable comparison is recorded for this version."
    origin = attribute.get("derived_from") or {}
    rationale = attribute.get("rationale") or raw.get("rationale")
    if not rationale and isinstance(origin, dict) and origin.get("field"):
        rationale = f"This criterion was explicitly built from task field {origin['field']}."
    limitations = []
    for finding in (raw.get("critic_findings") or []) + (rule.get("dissent") or []):
        if isinstance(finding, dict) and finding.get("finding"):
            limitations.append(str(finding["finding"]))
    limitations.extend(str(v) for v in raw.get("validator_problems") or [])
    if rule.get("on_missing"):
        limitations.append(f"Missing evidence is handled as {rule['on_missing']}.")
    scope = [attribute.get("definition") or "The definition is not recorded."]
    if attribute.get("acceptable_value_sources"):
        scope.append("Accepted evidence: " + ", ".join(attribute["acceptable_value_sources"]))
    if attribute.get("acceptable_determination_bases"):
        scope.append("Accepted determination: " + ", ".join(attribute["acceptable_determination_bases"]))
    return {"decision_question": question, "how_evaluated": calculation,
            "why_included": rationale or "An inclusion rationale was not recorded for this version.",
            "evidence_support": [f"{s['claim_id']}: {s.get('statement') or 'Saved evidence record'}" for s in sources],
            "scope": scope, "limitations": list(dict.fromkeys(limitations)),
            "method": "recorded_criterion_projection", "derived": True}
