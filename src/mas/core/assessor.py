"""Per-Candidate Assessor (C11; design §4.11): one assessment and one reason per candidate × rule.

The assessor executes confirmed rules it never authors. Missing evidence is
`unknown_missing`, never `fail`; values from a source kind the attribute does not
accept are not used; a hard-rule `fail` rejects; any hard-rule unknown caps the
candidate at `provisional`; `recommended` needs coverage at or above the floor.
"""

from __future__ import annotations

from typing import Any

from .canonical import sha256_hex
from .clock import utc_now

ASSESSOR_VERSION = "assessor-1"

UNIT_SYNONYMS = {"percent": "%", "pct": "%", "nmol/l": "nM", "µm": "uM", "μm": "uM", "umol/l": "uM",
                 "g/mol": "g/mol", "da": "g/mol", "dalton": "g/mol", "h": "h", "hr": "h", "hours": "h"}


def canonical_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    stripped = unit.strip()
    return UNIT_SYNONYMS.get(stripped.lower(), stripped)


def _compare(value: float, comparator: str, cutoff: float) -> bool:
    return {">=": value >= cutoff, "<=": value <= cutoff, ">": value > cutoff, "<": value < cutoff,
            "==": value == cutoff}[comparator]


def usable_claims(claims: list[dict[str, Any]], attribute: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Split claims into those usable for this attribute and those set aside, with reasons."""
    accepted_kinds = set(attribute["acceptable_value_sources"])
    accepted_bases = set(attribute.get("acceptable_determination_bases", ["measured", "derived"]))
    unit = canonical_unit(attribute.get("unit"))
    usable, set_aside = [], []
    for claim in claims:
        reason = None
        if claim.get("admission_state") != "admitted":
            reason = "not_admitted"
        elif claim.get("evidence_kind") not in accepted_kinds:
            reason = "evidence_kind_not_accepted"
        elif claim.get("determination_basis") not in accepted_bases:
            reason = "determination_basis_not_accepted"
        elif attribute["measurement_kind"] == "quantitative":
            if not isinstance(claim.get("value"), (int, float)) or isinstance(claim.get("value"), bool):
                reason = "no_numeric_value"
            elif canonical_unit(claim.get("unit")) != unit:
                reason = "unit_unresolved"
        (set_aside if reason else usable).append(claim if not reason else dict(claim, set_aside_reason=reason))
    return usable, set_aside


def assess_cell(*, candidate: dict[str, Any], attribute: dict[str, Any], rule: dict[str, Any], rule_set_ref: str,
                claims: list[dict[str, Any]], resolved: bool, tool_error_ref: str | None = None,
                searched: list[str] | None = None, not_assessed_reason: str | None = None,
                evidence_snapshot_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (assessment, reason) records for one cell. Pure: no I/O."""
    attr_ref = f"{attribute['attribute_id']}@v{attribute['version']}"
    rule_ref = f"{rule['rule_id']}@v{rule['version']}"
    usable, set_aside = usable_claims(claims, attribute) if resolved and not not_assessed_reason else ([], claims)
    value, unit, value_kind, determination_basis = None, attribute.get("unit"), "missing", "absent"
    conflicting, disposition = [], "none_found"
    if not_assessed_reason or not resolved:
        verdict = "not_assessed"
        not_assessed_reason = not_assessed_reason or "identity_unresolved"
    elif not usable:
        verdict = "unknown_missing"
    else:
        cutoff = rule.get("cutoff")
        values = [float(c["value"]) for c in usable]
        aggregation = attribute.get("aggregation", "consensus")
        if cutoff is None:
            if rule.get("predicate_form") == "ordering" and rule["rule_kind"] == "preference":
                prefer_high = attribute.get("direction") != "lower_better"
                value = (max(values) if prefer_high else min(values)) if aggregation != "consensus" else values[0]
                verdict = "pass"  # value-bearing; an ordering rule ranks, it never fails
            else:
                verdict = "unknown_missing"
        else:
            sides = {_compare(v, cutoff["comparator"], cutoff["value"]) for v in values}
            if aggregation == "consensus" and len(sides) > 1:
                verdict = "unknown_conflicted"
                disposition = "found_and_unresolved"
                value = None
            else:
                value = max(values) if aggregation == "max" else min(values) if aggregation == "min" else values[0]
                verdict = "pass" if _compare(value, cutoff["comparator"], cutoff["value"]) else "fail"
            if len(sides) > 1 and aggregation != "consensus":
                disposition = "found_and_outweighed"
                conflicting = [c["claim_id"] for c in usable if _compare(float(c["value"]), cutoff["comparator"], cutoff["value"])
                               != (verdict == "pass")]
        explicit_conflicts = [c["claim_id"] for c in usable if c.get("polarity") == "conflicts"]
        conflicting = sorted(set(conflicting) | set(explicit_conflicts))
        if explicit_conflicts and disposition == "none_found":
            disposition = "found_and_outweighed"
        determination_basis = usable[0]["determination_basis"] if verdict in ("pass", "fail") else "absent"
        value_kind = {"measured": "measured", "derived": "derived", "predicted": "predicted"}.get(determination_basis, "curated")
        if any(c.get("evidence_kind") in ("database_entry", "curated_measurement") for c in usable) and value_kind == "measured":
            value_kind = "curated"
    used_refs = [c["claim_id"] for c in usable] if verdict in ("pass", "fail", "unknown_conflicted") else []
    assessment = {
        "assessment_id": f"asm_{candidate['candidate_id']}_{attr_ref}_{rule_ref}_{evidence_snapshot_id or 'live'}",
        "candidate_ref": candidate["candidate_id"], "attribute_ref": attr_ref, "rule_ref": rule_ref,
        "rules@v": rule_set_ref, "rule_kind": rule["rule_kind"], "evidence_snapshot_id": evidence_snapshot_id,
        "verdict": verdict, "not_assessed_reason": not_assessed_reason, "value": value, "unit": unit,
        "value_kind": value_kind, "determination_basis": determination_basis, "value_source_claim_refs": used_refs,
        "conflicting_claim_refs": conflicting, "set_aside_claims": [{"claim_id": c["claim_id"], "reason": c["set_aside_reason"]}
                                                                     for c in set_aside if "set_aside_reason" in c],
        "assessed_by": {"actor_kind": "tool", "actor_id": "C11", "model_or_tool_version": ASSESSOR_VERSION},
        "assessed_at": utc_now(), "tool_error_ref": tool_error_ref, "staleness": "current",
    }
    cutoff = rule.get("cutoff") or {}
    statement_value = f"{value:g} {unit}" if isinstance(value, (int, float)) else "no usable value"
    reason = {
        "reason_id": f"rsn_{sha256_hex(assessment)[:16]}", "verdict_restated": verdict,
        "attribute_ref": attr_ref, "rule_ref": rule_ref, "evidence_refs": used_refs,
        "absence_check_record": None if used_refs else {"source_kinds_searched": searched or [], "searched_at": utc_now(),
                                                        "tool_error_ref": tool_error_ref},
        "value_and_unit_as_used": statement_value, "applicability_statement": "applicable (no applicability conditions declared)",
        "counter_evidence_disposition": disposition, "cutoff_basis": rule["cutoff_basis"],
        "uncertainty_statement": f"{len(used_refs)} usable claim(s); aggregation {attribute.get('aggregation', 'consensus')}",
    }
    reason["reason_text"] = _reason_text(attribute, rule, verdict, statement_value, cutoff, used_refs, disposition,
                                         not_assessed_reason, tool_error_ref)
    assessment["reason_ref"] = reason["reason_id"]
    return assessment, reason


def _reason_text(attribute, rule, verdict, statement_value, cutoff, refs, disposition, not_assessed_reason, tool_error_ref) -> str:
    name = attribute["name"]
    if verdict == "not_assessed":
        return f"{name}: not assessed ({not_assessed_reason})."
    if verdict == "unknown_missing":
        cause = "a tool error" if tool_error_ref else "no admitted claim from an accepted source"
        return f"{name}: unknown — {cause}; this is not a failure."
    if verdict == "unknown_conflicted":
        return f"{name}: unknown — {len(refs)} admitted claims fall on both sides of the cutoff; conflict open."
    if not cutoff:
        return f"{name} = {statement_value} ({len(refs)} claim(s)); recorded for ordering ({attribute.get('direction')}), no cutoff."
    rule_text = f"{cutoff.get('comparator')} {cutoff.get('value')} {cutoff.get('unit') or ''}".strip()
    extra = "; counter-evidence found and outweighed by the declared aggregation" if disposition == "found_and_outweighed" else ""
    return f"{name} = {statement_value} ({len(refs)} claim(s)); rule {rule_text} → {verdict}{extra}."


def roll_up(candidate_id: str, assessments: list[dict[str, Any]], *, coverage_floor: float,
            recommended_requires_hd: bool, hd_refs: list[str] | None = None) -> dict[str, Any]:
    """Candidate state from its cells (design §4.11)."""
    hard = [a for a in assessments if a["rule_kind"] == "hard_exclusion" and a["verdict"] != "inapplicable"]
    prefs = [a for a in assessments if a["rule_kind"] == "preference" and a["verdict"] != "inapplicable"]
    n_fail = sum(a["verdict"] == "fail" for a in hard)
    n_unknown = sum(a["verdict"] in ("unknown_missing", "unknown_conflicted", "not_assessed") for a in hard)
    value_bearing = sum(a["verdict"] in ("pass", "fail") for a in hard)
    coverage = value_bearing / len(hard) if hard else 0.0
    blocking = [a["attribute_ref"] for a in hard if a["verdict"] in ("unknown_missing", "unknown_conflicted", "not_assessed")]
    if not assessments or all(a["verdict"] == "not_assessed" for a in assessments):
        state, reason = "unassessed", "no assessed criteria"
    elif n_fail:
        failed = [a["attribute_ref"] for a in hard if a["verdict"] == "fail"]
        state, reason = "rejected", f"hard rule failed: {', '.join(failed)}"
    elif n_unknown:
        state, reason = "provisional", f"hard rule unknown: {', '.join(blocking)}"
    elif coverage < coverage_floor:
        state, reason = "provisional", f"hard-rule coverage {coverage:.2f} below floor {coverage_floor:.2f}"
    elif recommended_requires_hd and not hd_refs:
        state, reason = "provisional", "awaiting_human_review"
    else:
        state, reason = "recommended", "every hard rule passes with coverage at or above the floor"
    evaluated = [a for a in prefs if a["verdict"] in ("pass", "fail")]
    return {"candidate_ref": candidate_id, "state": state, "state_reason": reason, "hard_rule_coverage": coverage,
            "n_fail_hard": n_fail, "n_unknown_hard": n_unknown, "n_preferences_evaluated": len(evaluated),
            "n_preferences": len(prefs), "blocking_unknowns": blocking}


def preference_scores(cells_by_candidate: dict[str, list[dict[str, Any]]], rules: dict[str, dict[str, Any]],
                      weights: dict[str, float]) -> dict[str, tuple[float | None, float]]:
    """Preference score per candidate: weighted mean desirability over evaluated preference rules.

    Threshold rules contribute 1 for pass and 0 for fail. Ordering rules contribute the
    candidate's percentile among candidates with a value, in the attribute's direction.
    Missing values are left out of both numerator and denominator (never surrogate-filled);
    the second element is the weighted share of preference rules that were evaluated.
    Returns {candidate: (score or None, preference coverage)}.
    """
    percentiles: dict[str, dict[str, float]] = {}
    for rule_ref, info in rules.items():
        if info["rule_kind"] != "preference" or info.get("predicate_form") != "ordering":
            continue
        values = {c: cell["value"] for c, cells in cells_by_candidate.items() for cell in cells
                  if cell["rule_ref"] == rule_ref and cell["verdict"] == "pass" and isinstance(cell["value"], (int, float))}
        ordered = sorted(values.items(), key=lambda kv: kv[1], reverse=info.get("direction") == "lower_better")
        n = len(ordered)
        ranks: dict[str, float] = {}
        index = 0
        while index < n:
            end = index
            while end + 1 < n and ordered[end + 1][1] == ordered[index][1]:
                end += 1
            share = ((index + end) / 2) / (n - 1) if n > 1 else 1.0
            for k in range(index, end + 1):
                ranks[ordered[k][0]] = share
            index = end + 1
        percentiles[rule_ref] = ranks
    out: dict[str, tuple[float | None, float]] = {}
    for candidate, cells in cells_by_candidate.items():
        prefs = [c for c in cells if c["rule_kind"] == "preference" and c["verdict"] != "inapplicable"]
        total = sum(weights.get(c["rule_ref"], 1.0) for c in prefs)
        numerator = denominator = 0.0
        for cell in prefs:
            weight = weights.get(cell["rule_ref"], 1.0)
            if cell["rule_ref"] in percentiles:
                if candidate in percentiles[cell["rule_ref"]]:
                    numerator += weight * percentiles[cell["rule_ref"]][candidate]
                    denominator += weight
            elif cell["verdict"] in ("pass", "fail"):
                numerator += weight * (1.0 if cell["verdict"] == "pass" else 0.0)
                denominator += weight
        out[candidate] = ((numerator / denominator) if denominator else None, (denominator / total) if total else 0.0)
    return out
