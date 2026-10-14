"""Per-Candidate Assessor (C11; design §4.11): one assessment and one reason per candidate × rule.

The assessor executes confirmed rules it never authors. Missing evidence is
`unknown_missing`, never `fail`; values from a source kind the attribute does not
accept are not used; a hard-rule `fail` rejects; any hard-rule unknown caps the
candidate at `provisional`; `recommended` needs coverage at or above the floor.
"""

from __future__ import annotations

from typing import Any

from . import criteria, symbolic
from .canonical import sha256_hex
from .clock import utc_now

ASSESSOR_VERSION = "assessor-1"

# What an attribute accepts when it declares nothing: a measurement or a derivation, never a
# prediction. The registry owns the full list of bases (`criteria.DETERMINATION_BASES`); the
# assessor only needs the default and whether an attribute is the one that carries predictions.
DEFAULT_DETERMINATION_BASES = ("measured", "derived")

UNIT_SYNONYMS = {"percent": "%", "pct": "%", "nmol/l": "nM", "µm": "uM", "μm": "uM", "umol/l": "uM",
                 "g/mol": "g/mol", "da": "g/mol", "dalton": "g/mol", "h": "h", "hr": "h", "hours": "h"}


def canonical_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    stripped = unit.strip()
    return UNIT_SYNONYMS.get(stripped.lower(), stripped)


def _compare(value, comparator: str, cutoff) -> bool:
    if comparator in ("in", "not_in"):
        categories = cutoff if isinstance(cutoff, list) else [cutoff]
        member = _norm(value) in {_norm(c) for c in categories}
        return member if comparator == "in" else not member
    if comparator == "==":
        return _norm(value) == _norm(cutoff)
    return {">=": value >= cutoff, "<=": value <= cutoff, ">": value > cutoff, "<": value < cutoff}[comparator]


def _norm(value):
    return value.strip().lower() if isinstance(value, str) else value


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


# Which reduction over a consolidated family (`vocab.criterion_family_aggregation`) `assess_cell` below can
# actually run, given as the attribute `aggregation` that runs it.
#
# WHY the table lives beside the assessor rather than beside the vocabulary that registers the words: a
# consolidation record never reaches this function. The registered attribute carries `aggregation` and
# nothing else, and a consolidated criterion has one attribute and one pooled claim set rather than N member
# cells, so a declared family reduction is executed only if the merge gate compiles it into that field
# (`derivation_stages._consolidation`) -- and the authority on what compiles is the code that runs it.
#
# `worst_member` is direction-dependent and the inversion is silent: with `lower_better` the least
# favourable member is the largest value (`max`), with `higher_better` the smallest (`min`). Reversed, a
# candidate would be ranked on its best endpoint while its card said its worst -- the same shape as the
# ordering path that took the maximum whatever the attribute declared, which ranked sorafenib on the top of
# its 125 curated VEGFR2 measurements against surufatinib's 9.00 from two. A direction that does not order
# values (`within_range`, `target_value`, `non_directional`, `undetermined`) does not say which end is
# worse, so there is no worst member to compute and the gate refuses the consolidation instead of guessing;
# a median needs no direction, so it is executable under every one.
FAMILY_AGGREGATION_EXECUTION: dict[str, dict[str, str]] = {
    "worst_member": {"lower_better": "max", "higher_better": "min"},
    "median_of_members": dict.fromkeys(criteria.DIRECTIONS, "median"),
}


def family_aggregation_execution(family_aggregation: str, direction: str | None) -> tuple[str | None, str | None]:
    """The attribute `aggregation` that computes `family_aggregation` over a cell's pooled claims, or the
    reason nothing here computes it. Pure; exactly one of the two is None."""
    by_direction = FAMILY_AGGREGATION_EXECUTION.get(family_aggregation)
    if not by_direction:
        return None, (f"{family_aggregation!r} is not a reduction this assessor computes over a consolidated "
                      f"criterion's pooled claims")
    aggregation = by_direction.get(direction or "")
    if aggregation is None:
        return None, (f"{family_aggregation} is not computable for direction {direction!r}, which does not say "
                      f"which end of the scale is worse; it needs one of "
                      f"{', '.join(sorted(by_direction))}")
    return aggregation, None


# WHY a literature cell may be asked for more than one document before it scores: quote verification
# establishes that the words exist in the source, not that the number answers the question. Measured on the
# two-candidate run of 14 October 2026 (`run_smoke_lit_1792002118`, 26 literature criteria x 2 candidates),
# re-assessed from the claim union with the attribution guard applied: the guard refuses 48% of the numeric
# literature claims it reads, and of the 13 cells that still carry a value 9 rest on a single document and 7
# on a single claim -- among them a value that was the comparator arm of a two-arm comparison inside a
# span-verified quote. One unrefused mis-extraction therefore still decides a cell. A second document cannot
# detect a mis-reading on its own, but it makes the cell's value the agreement of two readings of two texts,
# which is the cheapest check this path does not already perform.
#
# Off by default (`minimum` of 1), because it buys that check by discarding evidence: at 2 that same run keeps
# 4 of its 13 value-bearing cells, and all 4 belong to one of the two candidates -- every value the comparator
# had rested on one document, so the floor would leave it unrankable rather than less certain. Raising it is a
# deliberate trade of coverage for support, so it is an operator setting and a registered constant
# (`config.evidence.min_source_documents`), not a decision taken here.
#
# Database routes are exempt because the floor would mean something else there: a curated measurement comes
# from one database record by construction, and `evidence.gather` already pools every declared route, so a
# floor of 2 would refuse single-source curated quantities rather than ask for corroboration.
def source_document_shortfall(usable: list[dict[str, Any]], attribute: dict[str, Any], minimum: int) -> str | None:
    """Why this cell's usable claims are too thin a base to score on, or None when they are enough."""
    if minimum <= 1 or not usable or not criteria.is_literature_bound(attribute):
        return None
    documents = {claim.get("source_ref") for claim in usable}
    if len(documents) >= minimum:
        return None
    return (f"{len(usable)} usable claim(s) from {len(documents)} source document(s); a literature criterion "
            f"carries a value here only with claims from at least {minimum} distinct documents")


def declares_predicted(attribute: dict[str, Any]) -> bool:
    """True when the attribute is the one that carries predicted values, rather than measurements."""
    return "predicted" in (attribute.get("acceptable_determination_bases") or DEFAULT_DETERMINATION_BASES)


def usable_claims(claims: list[dict[str, Any]], attribute: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Split claims into those usable for this attribute and those set aside, with reasons."""
    accepted_kinds = set(attribute["acceptable_value_sources"])
    accepted_bases = set(attribute.get("acceptable_determination_bases") or DEFAULT_DETERMINATION_BASES)
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
        elif attribute["measurement_kind"] == "categorical":
            if claim.get("value") is None or isinstance(claim.get("value"), (dict, list)):
                reason = "no_categorical_value"
        elif attribute["measurement_kind"] == "quantitative":
            if (not isinstance(claim.get("value"), (int, float)) or isinstance(claim.get("value"), bool)) and \
                    not (isinstance(claim.get("value_low"), (int, float)) and isinstance(claim.get("value_high"), (int, float))):
                reason = "no_numeric_value"
            elif canonical_unit(claim.get("unit")) != unit:
                reason = "unit_unresolved"
        (set_aside if reason else usable).append(claim if not reason else dict(claim, set_aside_reason=reason))
    # WHY one observation is counted once: nothing collapsed identical extractions, so a value the
    # reader emitted twice entered an aggregate twice and weighted it twice. Measured on the clean
    # derivation of 14 October 2026: 388 claims came from 15 distinct documents and 18 (document,
    # quoted span) pairs were extracted more than once -- one table row about a marketed inhibitor
    # seven times from a single paper. A median over seven copies of one number is that number, so
    # this is a bias in the aggregate, not only wasted reading. Two extractions of one span are one
    # observation; the duplicates stay in the ledger, which is the record of what was read, and are
    # set aside here, which is the record of what was counted. Deliberately narrow: same document,
    # same span and same value, so a table and a sentence reporting the same figure separately are
    # still two reports, and the cross-source experiment deduplication that §7.2 asks for is a
    # wider question this does not pretend to answer.
    seen, unique = {}, []
    for claim in usable:
        fingerprint = (claim.get("source_ref"),
                       ((claim.get("location") or {}).get("quoted_span") or "").strip(),
                       _norm(claim.get("value")), _norm(claim.get("value_low")),
                       _norm(claim.get("value_high")), canonical_unit(claim.get("unit")))
        first = seen.get(fingerprint)
        if first is None:
            seen[fingerprint] = claim
            unique.append(claim)
        else:
            set_aside.append(dict(claim, set_aside_reason="duplicate_observation",
                                  duplicate_of=first.get("claim_id")))
    return unique, set_aside


def assess_cell(*, candidate: dict[str, Any], attribute: dict[str, Any], rule: dict[str, Any], rule_set_ref: str,
                claims: list[dict[str, Any]], resolved: bool, tool_error_ref: str | None = None,
                searched: list[str] | None = None, not_assessed_reason: str | None = None,
                evidence_snapshot_id: str | None = None, min_source_documents: int = 1,
                ) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (assessment, reason) records for one cell. Pure: no I/O."""
    attr_ref = f"{attribute['attribute_id']}@v{attribute['version']}"
    rule_ref = f"{rule['rule_id']}@v{rule['version']}"
    usable, set_aside = usable_claims(claims, attribute) if resolved and not not_assessed_reason else ([], claims)
    # Applied before any verdict is computed, so the floor decides whether this cell may be scored at all --
    # including whether it may declare a conflict, which is as much a decision about a candidate as a value
    # is. The claims are set aside rather than dropped: they stay in the ledger, and `set_aside_claims` names
    # every one of them with this reason, so the evidence is visible and only the scoring is refused.
    shortfall = source_document_shortfall(usable, attribute, min_source_documents)
    if shortfall:
        set_aside = set_aside + [dict(c, set_aside_reason="below_min_source_documents") for c in usable]
        usable = []
    value, unit, value_kind, determination_basis = None, attribute.get("unit"), "missing", "absent"
    conflicting, disposition = [], "none_found"
    if not_assessed_reason or not resolved:
        verdict = "not_assessed"
        not_assessed_reason = not_assessed_reason or "identity_unresolved"
    elif not usable:
        verdict = "unknown_missing"
    else:
        cutoff = rule.get("cutoff")
        categorical = attribute["measurement_kind"] == "categorical"
        # The attribute may be about a derived quantity -- an excess over a stated bound, a distance
        # outside a stated band -- while its source returns the raw value. Applied per claim, before
        # aggregation and before any comparison, so the cell carries the quantity the attribute names.
        declared = attribute.get("value_transform")
        transform = (lambda v: criteria.apply_value_transform(v, declared)) if declared else (lambda v: v)
        # WHY one evaluation per claim, kept and reused: the verdict and its explanation have to be computed
        # from the same numbers. Conflict attribution used to re-derive sides from the raw `value` against a
        # cutoff that lives on the transformed scale, and skipped range claims entirely because their `value`
        # is None -- so with raw observations 20 and 50, an excess-above-30 transform, assessed values 0 and
        # 20, median 10 and a `>= 10` predicate, the cell passed while the claim that transformed to 0 was
        # reported as no conflict at all. The score was right and its audit trail denied the counter-evidence.
        evaluated = []
        for c in usable:
            if categorical:
                claim_values = [c["value"]]
            elif c.get("value") is not None:
                claim_values = [transform(float(c["value"]))]
            else:   # a reported range contributes both ends: a range straddling a cutoff is a conflict, not a pass
                claim_values = [transform(float(c["value_low"])), transform(float(c["value_high"]))]
            evaluated.append({"claim_id": c["claim_id"], "values": claim_values})
        values = [v for e in evaluated for v in e["values"]]
        aggregation = "consensus" if categorical else attribute.get("aggregation", "consensus")
        if cutoff is None:
            if rule.get("predicate_form") == "ordering" and rule["rule_kind"] == "preference":
                # WHY the declared aggregation governs here too: this path took the best of the usable values
                # regardless of what the attribute asked for, and a maximum rises with the number of assays.
                # Measured on the manuscript case: sorafenib carried 125 curated VEGFR2 measurements and was
                # ranked on their maximum, 10.68, against surufatinib's 9.00 from two -- so the board rewarded
                # having been studied often. The evidence catalog warns of exactly this and every one of the ten
                # target attributes declared `median`; honouring it is what the attribute already said.
                prefer_high = attribute.get("direction") != "lower_better"
                value = (_median(values) if aggregation == "median"
                         else max(values) if aggregation == "max" else min(values) if aggregation == "min"
                         else (max(values) if prefer_high else min(values)) if aggregation != "consensus"
                         else values[0])
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
                value = (max(values) if aggregation == "max" else min(values) if aggregation == "min"
                         else _median(values) if aggregation == "median" else values[0])
                verdict = "pass" if _compare(value, cutoff["comparator"], cutoff["value"]) else "fail"
            if len(sides) > 1 and aggregation != "consensus":
                disposition = "found_and_outweighed"
                # A claim counts as counter-evidence when any value it contributed -- either end of a
                # reported range included -- lands on the side the aggregate did not take.
                conflicting = [e["claim_id"] for e in evaluated
                               if any(_compare(v, cutoff["comparator"], cutoff["value"]) != (verdict == "pass")
                                      for v in e["values"])]
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
    statement_value = (f"{value:g} {unit}" if isinstance(value, (int, float)) and not isinstance(value, bool)
                       else str(value) if value is not None else "no usable value")
    reason = {
        "reason_id": f"rsn_{sha256_hex(assessment)[:16]}", "verdict_restated": verdict,
        "attribute_ref": attr_ref, "rule_ref": rule_ref, "evidence_refs": used_refs,
        "absence_check_record": None if used_refs else {"source_kinds_searched": searched or [], "searched_at": utc_now(),
                                                        "tool_error_ref": tool_error_ref},
        "value_and_unit_as_used": statement_value, "applicability_statement": "applicable (no applicability conditions declared)",
        "counter_evidence_disposition": disposition, "cutoff_basis": rule["cutoff_basis"],
        "uncertainty_statement": f"{len(used_refs)} usable claim(s); aggregation {attribute.get('aggregation', 'consensus')}"
                                 + (f"; not scored: {shortfall}" if shortfall else ""),
    }
    reason["reason_text"] = _reason_text(attribute, rule, verdict, statement_value, cutoff, used_refs, disposition,
                                         not_assessed_reason, tool_error_ref, shortfall)
    assessment["reason_ref"] = reason["reason_id"]
    return assessment, reason


def _reason_text(attribute, rule, verdict, statement_value, cutoff, refs, disposition, not_assessed_reason,
                 tool_error_ref, shortfall=None) -> str:
    name = attribute["name"]
    if verdict == "not_assessed":
        return f"{name}: not assessed ({not_assessed_reason})."
    if verdict == "unknown_missing":
        # The shortfall is named here rather than left as "no admitted claim": the cell did find admitted
        # claims, and a reason that said it found none would be false about the evidence it set aside.
        cause = ("a tool error" if tool_error_ref else shortfall if shortfall
                 else "no admitted claim from an accepted source")
        return f"{name}: unknown — {cause}; this is not a failure."
    if verdict == "unknown_conflicted":
        return f"{name}: unknown — {len(refs)} admitted claims fall on both sides of the cutoff; conflict open."
    if not cutoff:
        return f"{name} = {statement_value} ({len(refs)} claim(s)); recorded for ordering ({attribute.get('direction')}), no cutoff."
    rule_text = f"{cutoff.get('comparator')} {cutoff.get('value')} {cutoff.get('unit') or ''}".strip()
    extra = "; counter-evidence found and outweighed by the declared aggregation" if disposition == "found_and_outweighed" else ""
    return f"{name} = {statement_value} ({len(refs)} claim(s)); rule {rule_text} → {verdict}{extra}."


def roll_up(candidate_id: str, assessments: list[dict[str, Any]], *, coverage_floor: float,
            recommended_requires_hd: bool, hd_refs: list[str] | None = None,
            pending_hard_rules: list[str] | None = None,
            machine_authority: bool = False) -> dict[str, Any]:
    """Candidate state from its cells (design §4.11).

    Hard rules still awaiting an expert decision keep every candidate `provisional`
    (the rule set is exploratory); a rule set with no hard rule never recommends.
    """
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
    elif pending_hard_rules:
        state, reason = "provisional", f"hard rules await an expert decision: {', '.join(pending_hard_rules)}"
    elif not hard:
        state, reason = "provisional", "no confirmed hard rule; ranked on preferences only"
    elif coverage < coverage_floor:
        state, reason = "provisional", f"hard-rule coverage {coverage:.2f} below floor {coverage_floor:.2f}"
    elif recommended_requires_hd and not hd_refs and not machine_authority:
        state, reason = "provisional", "awaiting_human_review"
    elif recommended_requires_hd and not hd_refs:
        # WHY a machine-adjudicated set may still clear the gate: the selection is two steps -- hard
        # rules decide who is eligible, preferences rank the eligible -- and with
        # `recommended_requires_hd` and no `hd_` in existence, step one could never complete for any
        # candidate, so the eligible set was empty by construction and the second step had nothing to
        # rank. Measured on the 14 October board: 9 candidates cleared every hard rule and all 9 read
        # `provisional / awaiting_human_review`, indistinguishable from the 1,262 blocked on an absent
        # record. An autonomous run is a legitimate configuration here, so it reaches a decision --
        # and the reason says who took it, because the one thing this must not do is let an agent's
        # verdict read as a person's. The rule set is `exploratory` and names every machine
        # adjudication regardless.
        state = "recommended"
        reason = ("every hard rule passes with coverage at or above the floor; the hard rules were "
                  "adjudicated by an agent and no person has confirmed them")
    else:
        state, reason = "recommended", "every hard rule passes with coverage at or above the floor"
    evaluated = [a for a in prefs if a["verdict"] in ("pass", "fail")]
    return {"candidate_ref": candidate_id, "state": state, "state_reason": reason,
            "hard_rule_coverage": coverage if hard else None,
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


def feature_values(cells: list[dict[str, Any]], rules: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Numeric values a candidate's cells offer as scoring features, keyed by attribute reference.

    Only a value-bearing cell of a rule still in the confirmed set counts: a cell left over from a
    rule that is no longer confirmed is missing evidence for the score, not a usable number.
    """
    out: dict[str, float] = {}
    for cell in cells:
        if cell["rule_ref"] not in rules or cell["verdict"] not in ("pass", "fail"):
            continue
        value = cell.get("value")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out[cell["attribute_ref"]] = float(value)
    return out


def expression_scores(cells_by_candidate: dict[str, list[dict[str, Any]]], rules: dict[str, dict[str, Any]],
                      expression: Any) -> dict[str, tuple[float | None, float]]:
    """Score per candidate under a registered scoring expression (design §5.7).

    Same contract as `preference_scores`: {candidate: (score or None, coverage)}, where coverage is
    the weighted share of the expression's features that had a usable value — so the ranking
    coverage floor, the change notes and the snapshot's reporting tuple need no change. The
    expression is applied exactly as registered; this function never refits anything.
    """
    expr = symbolic.as_expression(expression)
    return {candidate: symbolic.evaluate(expr, feature_values(cells, rules))
            for candidate, cells in cells_by_candidate.items()}
