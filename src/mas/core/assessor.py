"""Per-Candidate Assessor (C11; design §4.11): one assessment and one reason per candidate × rule.

The assessor executes confirmed rules it never authors. Missing evidence is
`unknown_missing`, never `fail`; values from a source kind the attribute does not
accept are not used; a hard-rule `fail` rejects; any hard-rule unknown caps the
candidate at `provisional`; `recommended` needs coverage at or above the floor.
"""

from __future__ import annotations

import math
from functools import partial
from typing import Any

from . import criteria, symbolic
from .canonical import sha256_hex
from .clock import utc_now

ASSESSOR_VERSION = "assessor-1"

# What an attribute accepts when it declares nothing: a measurement or a derivation, never a
# prediction. The registry owns the full list of bases (`criteria.DETERMINATION_BASES`); the
# assessor only needs the default and whether an attribute is the one that carries predictions.
DEFAULT_DETERMINATION_BASES = ("measured", "derived")

# Why a claim this cell found was not counted. Enumerated here because `assess_cell` publishes these
# strings in `set_aside_claims[].reason`, which is the record of what the cell declined to use and is
# read by a person: a typo would travel into the store as a reason nobody can look up. `usable_claims`
# checks every reason it emits against this list, so an unregistered one is a loud failure here rather
# than a silent string on a published cell.
SET_ASIDE_REASONS = (
    "not_admitted",                    # the ledger did not admit the claim
    "evidence_kind_not_accepted",      # the attribute does not accept that kind of evidence
    "determination_basis_not_accepted",   # ... nor that basis at all
    "lower_precedence_basis",          # it does, and a higher-priority basis answered for this candidate
    "no_categorical_value", "no_numeric_value", "unit_unresolved",
    "duplicate_observation",           # one observation, extracted twice
    "below_min_source_documents",      # too few distinct documents to score on (`source_document_shortfall`)
    "non_positive_concentration",      # a concentration of zero or less has no logarithm (`UNIT_CONVERSIONS`)
)

# How strong a basis is, for labelling an aggregate that pooled more than one of them. Used only
# where no `determination_basis_precedence` is declared, which is the only way a cell can still pool
# two bases (an attribute accepting `measured` and `derived` genuinely may). An aggregate is no
# stronger than its weakest contributor, so the label is the weakest basis present, with ties broken
# alphabetically so the field is a function of the claim set and not of the order it arrived in.
BASIS_STRENGTH = {"asserted": 0, "predicted": 0, "simulated": 0, "curated": 1, "derived": 1, "measured": 2}

UNIT_SYNONYMS = {"percent": "%", "pct": "%", "nmol/l": "nM", "µm": "uM", "μm": "uM", "umol/l": "uM",
                 "g/mol": "g/mol", "da": "g/mol", "dalton": "g/mol", "h": "h", "hr": "h", "hours": "h"}


def canonical_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    stripped = unit.strip()
    return UNIT_SYNONYMS.get(stripped.lower(), stripped)


# --- unit conversion ----------------------------------------------------------------------------
#
# WHY this is not a `value_transform` and not a synonym. A `criteria.VALUE_TRANSFORMS` entry
# (`excess_above`, `shortfall_below`, `distance_outside_band`) states a *different quantity* computed
# from a value already in the attribute's unit -- the excess of a molecular weight over a bound is
# not a molecular weight. A synonym (`UNIT_SYNONYMS`) states that two spellings name one unit, so no
# arithmetic happens. This is the third thing: one quantity, two scales, with an exact documented
# identity between them. It therefore belongs at the seam where `usable_claims` finds a claim whose
# canonical unit differs from the attribute's, and nowhere else: before it, nothing knows the
# attribute's unit; after it, the claim has already been set aside as `unit_unresolved`.
#
# WHY it is needed, measured on the live registry of 14 October 2026: of the 26 literature-bound
# criteria not one is a potency, although a published kinase selectivity table is exactly where
# multi-target potency is reported -- because such a table prints "IC50 = 0.004 uM" and every potency
# attribute declares `pChEMBL`, so each of those claims was admitted to the ledger and then set
# aside. The curated databases cover 74 of the 3,177 candidates at the five required receptors; for
# the rest the literature is the only route, and it is unreadable without this.
#
# WHAT MAY BE CONVERTED is an explicit table and nothing else, because a conversion is legitimate
# only between commensurable quantities: a molar concentration converts to the pChEMBL scale, a
# percentage does not convert to hours. An unregistered pair keeps the existing `unit_unresolved`
# behaviour -- the claim is named on the cell with that reason, so a missing conversion is visible as
# evidence declined rather than as evidence nobody had. The table is one-directional on purpose: a
# pChEMBL value carries no concentration unit to go back to.
#
# Case matters, and that is deliberate: `nM` is nanomolar and `nm` is nanometres, `M` is molar and
# `m` is metres. `canonical_unit` folds case only through the synonym table, which maps the
# spellings that are genuinely unambiguous (`nmol/l`, `umol/l`, `µm`, `μm`); anything else reaches
# this table with its case intact and an unrecognized spelling converts nothing.
MOLAR_IN_MOL_PER_L = {"M": 1.0, "mM": 1e-3, "uM": 1e-6, "nM": 1e-9, "pM": 1e-12}

# How ChEMBL computes its own `pchembl_value`, which is what the attributes this answers declare:
# the negative base-ten logarithm of the molar concentration. A documented identity, not a model.
PCHEMBL_IDENTITY = "pChEMBL = -log10(concentration in mol/L)"


def _to_pchembl(value: float, *, mol_per_l: float) -> tuple[float | None, str | None]:
    """The pChEMBL value of a concentration, or the reason it has none. Exactly one is None."""
    molar = value * mol_per_l
    if molar <= 0:
        # A zero or negative concentration has no logarithm. Refused by name rather than raising or
        # returning `inf`: a cell that scored a candidate at infinite potency would be a verdict, and
        # a crash in the assessor would end the sweep over one reader's bad number.
        return None, "non_positive_concentration"
    return -math.log10(molar), None


# The registered conversions, keyed (claim's canonical unit, attribute's canonical unit).
UNIT_CONVERSIONS: dict[tuple[str, str], dict[str, Any]] = {
    (unit, "pChEMBL"): {"identity": PCHEMBL_IDENTITY, "convert": partial(_to_pchembl, mol_per_l=factor)}
    for unit, factor in MOLAR_IN_MOL_PER_L.items()
}


def unit_conversion(from_unit: str | None, to_unit: str | None) -> dict[str, Any] | None:
    """The registered conversion from one unit to another, or None when none is registered."""
    if from_unit is None or to_unit is None:
        return None
    return UNIT_CONVERSIONS.get((canonical_unit(from_unit), canonical_unit(to_unit)))


def converted_claim(claim: dict[str, Any], unit: str | None) -> tuple[dict[str, Any] | None, str | None]:
    """This claim restated in `unit`, or the reason it cannot be. Exactly one of the two is None.

    Pure, and the stored claim is never mutated: what comes back is a copy carrying the converted
    value and a `unit_conversion` record of the original value, the original unit and the identity
    used, so a reader can check the arithmetic against the quoted span. The ledger keeps the claim as
    the source stated it; this copy is what the cell counts.

    No rounding: the identity is exact and the aggregate is computed from it, so the cell's value
    carries the full precision and a report rounds where it prints.
    """
    conversion = unit_conversion(claim.get("unit"), unit)
    if conversion is None:
        return None, "unit_unresolved"
    converted: dict[str, Any] = {}
    for field in ("value", "value_low", "value_high"):
        raw = claim.get(field)
        if raw is None:
            continue
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            return None, "no_numeric_value"
        value, refusal = conversion["convert"](float(raw))
        if refusal:
            return None, refusal
        converted[field] = value
    low, high = converted.get("value_low"), converted.get("value_high")
    if low is not None and high is not None and low > high:
        # A decreasing conversion reverses the ends of a reported range: 1-10 nM is pChEMBL 8-9, not
        # 9-8. `assess_cell` contributes both ends either way, but a record whose low exceeds its
        # high is wrong on its face and would read as one to anyone looking at the cell.
        converted["value_low"], converted["value_high"] = high, low
    record = {"from_unit": canonical_unit(claim.get("unit")), "to_unit": canonical_unit(unit),
              "identity": conversion["identity"], "unit_as_reported": claim.get("unit"),
              "value_as_reported": claim.get("value"), "value_low_as_reported": claim.get("value_low"),
              "value_high_as_reported": claim.get("value_high")}
    return dict(claim, **converted, unit=canonical_unit(unit), unit_conversion=record), None


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
    if any((claim.get("location") or {}).get("location_kind") == "record_field" for claim in usable):
        # A cell of an attribute that reads databases *and* literature: its value does not rest on
        # one extraction, because a curated record stands beside the reading, and the floor is about
        # a single mis-reading deciding a cell. Counting database records as documents would also
        # satisfy the floor with two curated rows and no reading at all, which measures nothing.
        return None
    documents = {claim.get("source_ref") for claim in usable}
    if len(documents) >= minimum:
        return None
    return (f"{len(usable)} usable claim(s) from {len(documents)} source document(s); a literature criterion "
            f"carries a value here only with claims from at least {minimum} distinct documents")


def declares_predicted(attribute: dict[str, Any]) -> bool:
    """True when the attribute may carry predicted values at all.

    True of a gap-filling attribute as well (`determination_basis_precedence`), which accepts them
    under a measurement: it says what the attribute may carry, not what a given cell used. What a
    cell used is the cell's own `determination_basis`.
    """
    return "predicted" in (attribute.get("acceptable_determination_bases") or DEFAULT_DETERMINATION_BASES)


def basis_used(usable: list[dict[str, Any]]) -> str:
    """The determination basis an aggregate over these claims rests on.

    One basis for a cell with a declared precedence, by construction: `usable_claims` has already
    kept a single basis. Without one, an attribute accepting `measured` and `derived` may pool both,
    and the label is then the weakest of them (`BASIS_STRENGTH`) rather than whichever claim
    happened to be first in the list -- which is what `usable[0]["determination_basis"]` reported,
    so the same cell could read `measured` or `derived` depending on the order the routes answered in.
    """
    bases = {claim["determination_basis"] for claim in usable}
    return min(bases, key=lambda basis: (BASIS_STRENGTH.get(basis, 0), basis))


def precedence_applied(claims: list[dict[str, Any]], precedence: list[str]) -> tuple[str | None, list[str]]:
    """The highest-priority basis these claims actually offer, and the bases outranked by it.

    Pure, and it looks at nothing but the bases present: the candidate is not an input, so a cell
    cannot be gap-filled for one compound and not for another on anything but its own evidence.
    """
    present = {claim.get("determination_basis") for claim in claims}
    chosen = next((basis for basis in precedence if basis in present), None)
    return chosen, [basis for basis in precedence if basis in present and basis != chosen]


def usable_claims(claims: list[dict[str, Any]], attribute: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Split claims into those usable for this attribute and those set aside, with reasons.

    Three filters, in order: what the attribute accepts at all (kind, basis, and a value on its
    scale -- in its unit, or in one an exact registered conversion restates in its unit, which is
    how a literature claim reporting "IC50 = 4 nM" answers a `pChEMBL` attribute);
    then, where the attribute declares a `determination_basis_precedence`, the single
    highest-priority basis this candidate actually has evidence on -- so a measurement is used where
    there is one and a prediction only where there is none, and **no aggregate ever spans two
    bases**; then one observation per (document, span, value), so a figure extracted twice weighs once.
    """
    accepted_kinds = set(attribute["acceptable_value_sources"])
    accepted_bases = set(attribute.get("acceptable_determination_bases") or DEFAULT_DETERMINATION_BASES)
    unit = canonical_unit(attribute.get("unit"))
    usable, set_aside = [], []
    for claim in claims:
        reason, prepared = None, claim
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
                # A different unit is not yet a refusal: where an exact documented conversion between
                # the two is registered (`UNIT_CONVERSIONS`), the claim is restated in the attribute's
                # unit and counted, keeping what the source said. Where none is, or where the
                # arithmetic has no answer, the claim is set aside with the reason -- `unit_unresolved`
                # exactly as before for a pair nothing converts.
                prepared, reason = converted_claim(claim, unit)
        (set_aside if reason else usable).append(prepared if not reason else dict(claim, set_aside_reason=reason))
    # The gap-fill, and the one place the never-pool invariant is enforced: of the bases this
    # candidate actually has evidence on, only the highest-priority one is kept. A candidate with a
    # curated measurement and a prediction is scored on the measurement alone; one with only a
    # prediction is scored on the prediction alone; neither is scored on both. The prediction stays
    # in the ledger and is named here with the reason it was not counted, so a reader can see that a
    # measured cell had a prediction available and declined it.
    precedence = criteria.basis_precedence(attribute)
    if precedence and usable:
        chosen, outranked = precedence_applied(usable, precedence)
        if outranked:
            kept = [c for c in usable if c["determination_basis"] == chosen]
            set_aside += [dict(c, set_aside_reason="lower_precedence_basis", outranked_by=chosen)
                          for c in usable if c["determination_basis"] != chosen]
            usable = kept
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
    unregistered = {c["set_aside_reason"] for c in set_aside} - set(SET_ASIDE_REASONS)
    if unregistered:
        raise ValueError(f"unregistered set-aside reason(s) {sorted(unregistered)}; add them to "
                         f"assessor.SET_ASIDE_REASONS, which is what a reader of a cell looks them up in")
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
    # Every claim this cell counted on a scale other than the one its source stated it on, with the
    # original value, the original unit and the identity used (`converted_claim`). Published on the
    # reason record because a reader checking a pChEMBL value against a quote that says "0.004 uM"
    # needs the arithmetic named; the ledger's claim is untouched and still says uM.
    unit_conversions = [dict(claim["unit_conversion"], claim_id=claim["claim_id"], value=claim.get("value"))
                        for claim in usable if claim.get("unit_conversion")]
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
        # The basis the value this cell reports actually rests on. Not `usable[0]`: with a declared
        # precedence every usable claim shares one basis and the first is that basis, but without one
        # a pooled cell's label depended on which route answered first, so a measured/derived
        # aggregate could read either way on two runs of the same evidence (`basis_used`).
        determination_basis = basis_used(usable) if verdict in ("pass", "fail") else "absent"
        value_kind = {"measured": "measured", "derived": "derived", "predicted": "predicted"}.get(determination_basis, "curated")
        if any(c.get("evidence_kind") in ("database_entry", "curated_measurement") for c in usable) and value_kind == "measured":
            value_kind = "curated"
    used_refs = [c["claim_id"] for c in usable] if verdict in ("pass", "fail", "unknown_conflicted") else []
    # The provenance block of a gap-filling attribute: which bases it ranks, which one this candidate
    # was scored on, whether that was a fall-back from a basis with nothing to say here, and which
    # claims it therefore declined. `None` for every attribute that declares no precedence, so a
    # reader never has to tell "no precedence" from "the top basis answered".
    precedence = criteria.basis_precedence(attribute)
    basis_precedence_record = None
    if precedence:
        outranked = [{"claim_id": c["claim_id"], "basis": c["determination_basis"]} for c in set_aside
                     if c.get("set_aside_reason") == "lower_precedence_basis"]
        basis_precedence_record = {
            "order": list(precedence), "basis_used": determination_basis if used_refs else None,
            # True where the basis used is not the highest-ranked one: the cell is standing in for a
            # measurement this candidate does not have. False on a cell the top basis answered, and
            # None where nothing answered at all.
            "gap_filled": (None if not used_refs or determination_basis not in precedence
                           else precedence.index(determination_basis) > 0),
            "outranked_claims": outranked,
        }
    assessment = {
        "assessment_id": f"asm_{candidate['candidate_id']}_{attr_ref}_{rule_ref}_{evidence_snapshot_id or 'live'}",
        "candidate_ref": candidate["candidate_id"], "attribute_ref": attr_ref, "rule_ref": rule_ref,
        "rules@v": rule_set_ref, "rule_kind": rule["rule_kind"], "evidence_snapshot_id": evidence_snapshot_id,
        "verdict": verdict, "not_assessed_reason": not_assessed_reason, "value": value, "unit": unit,
        "value_kind": value_kind, "determination_basis": determination_basis, "value_source_claim_refs": used_refs,
        "determination_basis_precedence": basis_precedence_record,
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
        # The same block the assessment carries: a reason record is what a person reads about one
        # cell, and "this value is a prediction standing in for a measurement nobody has made" is
        # the most consequential thing this cell can say about itself.
        "determination_basis_precedence": basis_precedence_record,
        "unit_conversions": unit_conversions,
        "uncertainty_statement": f"{len(used_refs)} usable claim(s); aggregation {attribute.get('aggregation', 'consensus')}"
                                 + (f"; not scored: {shortfall}" if shortfall else "")
                                 + _precedence_statement(basis_precedence_record)
                                 + (f"; {len(unit_conversions)} claim(s) converted to {canonical_unit(unit)} "
                                    f"({unit_conversions[0]['identity']})" if unit_conversions else ""),
    }
    reason["reason_text"] = _reason_text(attribute, rule, verdict, statement_value, cutoff, used_refs, disposition,
                                         not_assessed_reason, tool_error_ref, shortfall, basis_precedence_record)
    assessment["reason_ref"] = reason["reason_id"]
    return assessment, reason


def _precedence_statement(record: dict[str, Any] | None) -> str:
    """What the basis precedence did to this cell, in words, or nothing when it declares none."""
    if not record or record["basis_used"] is None:
        return ""
    order = " > ".join(record["order"])
    if record["gap_filled"]:
        return (f"; the value is {record['basis_used']}, standing in for {record['order'][0]} evidence this "
                f"candidate has none of (basis precedence {order})")
    declined = len(record["outranked_claims"])
    return (f"; the value is {record['basis_used']} under basis precedence {order}"
            + (f", and {declined} lower-precedence claim(s) were not counted" if declined else ""))


def _reason_text(attribute, rule, verdict, statement_value, cutoff, refs, disposition, not_assessed_reason,
                 tool_error_ref, shortfall=None, precedence=None) -> str:
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
    # The basis clause rides on the value-bearing sentences, where there is a value whose provenance
    # it describes; the two unknown verdicts above have none.
    basis = _precedence_statement(precedence)
    if not cutoff:
        return (f"{name} = {statement_value} ({len(refs)} claim(s)); recorded for ordering "
                f"({attribute.get('direction')}), no cutoff{basis}.")
    rule_text = f"{cutoff.get('comparator')} {cutoff.get('value')} {cutoff.get('unit') or ''}".strip()
    extra = "; counter-evidence found and outweighed by the declared aggregation" if disposition == "found_and_outweighed" else ""
    return f"{name} = {statement_value} ({len(refs)} claim(s)); rule {rule_text} → {verdict}{extra}{basis}."


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
    scored = [a for a in assessments if a["verdict"] in ("pass", "fail")]
    return {"candidate_ref": candidate_id, "state": state, "state_reason": reason,
            "hard_rule_coverage": coverage if hard else None,
            "n_fail_hard": n_fail, "n_unknown_hard": n_unknown, "n_preferences_evaluated": len(evaluated),
            "n_preferences": len(prefs), "blocking_unknowns": blocking,
            # What this candidate's values rest on, and which of them stand in for a measurement it
            # has none of. Carried here because the roll-up is what the board entry is built from: a
            # candidate ranked largely on gap-filled cells is a different claim from one ranked on
            # measurements, and `measured_vs_predicted_counts` alone cannot say which cells those
            # were or that an attribute offering both bases fell back to the weaker one.
            # `.get`, because a caller may roll up a reduced cell record (several tests, and the
            # recovery measurement, build one out of the fields they are about) and a summary field
            # must not decide whether a candidate can be rolled up at all.
            "determination_bases": {basis: sum(a.get("determination_basis") == basis for a in scored)
                                    for basis in sorted({a.get("determination_basis") for a in scored}
                                                         - {None})},
            "gap_filled_criteria": sorted(a.get("attribute_ref") or "" for a in scored
                                          if (a.get("determination_basis_precedence") or {}).get("gap_filled")),
            }


# --- the calibration guard ----------------------------------------------------------------------
#
# WHY a hard exclusion is checked against a population at all. A gate's cutoff can be impeccably
# sourced and still be wrong for the candidates it is applied to, and the failure looks like
# selectivity from the inside: the board simply shows fewer candidates. Measured on the manuscript
# universe, 14 October 2026, with the predicted-toxicity panel: a general-toxicity gate taken at the
# model's own 0.5 line excludes 100% of the 116 approved or phase-3 kinase inhibitors in the
# candidate set -- DILI alone 99.1%, hERG 88.8%. A screen that removes every already-approved drug
# of the class the task is about has not discriminated between candidates; it has stated that the
# class is unacceptable, which is a fact about the gate's calibration on this population and not
# about any candidate.
#
# WHY a universe-wide rate would not catch it: the same DILI gate excludes 51% of all 3,177
# compounds, which is an unremarkable number. The population the rate has to be measured over is the
# one that survives the task's own primary requirement, which is why the reference set is the
# candidates that clear the *task-mandated* criteria (`criteria.is_task_mandated`) and not the
# universe.
#
# WHY the guard demotes rather than deletes: demoting to a preference keeps the measurement, keeps
# the evidence and keeps the ranking, and removes only the deletion -- the same remedy, for the same
# reason, as `adjudication`'s `irreversible_without_authority`. And it is applied to *every* hard
# exclusion, not only to predicted ones: a curated gate can be as miscalibrated for a population as
# a modelled one, and a guard that only looked at model outputs would be saying otherwise.
#
# A reference set too small to measure a share over is not evidence about a gate. Ten is the
# smallest set on which a share can distinguish "excludes nearly all of them" from "excluded the
# three it saw": below that the guard abstains and says so, rather than demoting a gate on one
# candidate's worth of evidence.
MIN_CALIBRATION_REFERENCE = 10
# The share of the reference set a hard exclusion may remove before it is demoted, when no setting
# is supplied (`config.assess.max_reference_exclusion_share`).
DEFAULT_MAX_REFERENCE_EXCLUSION = 0.90


def clears_mandated(cells: list[dict[str, Any]], mandated_rule_refs: set[str]) -> bool:
    """Whether this candidate survives the task's own mandated criteria.

    The task mandates two kinds of criterion and they are cleared differently (`objective_templates`
    in the drug adapter builds both): a constraint becomes a gate, and a required target becomes a
    quantity to measure. So:
      * no `fail` on any mandated criterion -- the task's own criterion said no;
      * every mandated *gate* passes, value-bearing. The task stated it as a requirement, so a
        candidate no record can answer it for has not met it (and `unknown_blocks_recommendation`
        keeps such a candidate off the board anyway);
      * where the task mandates quantities of its own -- the potency at each required target -- at
        least one of them carries a value. A candidate nobody has measured against any required
        target is not a member of the population the screen is about; it is a compound with no
        evidence, and counting it would put the whole universe in the denominator, which is the
        universe-wide rate the guard exists to avoid. Where the task mandates only gates, clearing
        them is the whole of its requirement and one value-bearing mandated cell is enough.

    WHY the third condition is this and not merely "one mandated cell carries a value", measured on
    the published board of 14 October 2026 (`lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4`, rules@v3, 9
    entries of which 6 are task-mandated: the five required receptors' curated potency as ordering
    preferences, and the oral-route gate): the weaker reading admits every compound with an oral
    route on record, 1,269 of 3,177, over which the predicted DILI gate at the model's own line
    removes 54.5% and hERG 47.9% -- indistinguishable from their universe-wide rates (51.2%, 44.2%),
    so the guard would have measured the wrong population and demoted nothing. Over the candidates
    that also carry a curated potency at a required receptor, the same two gates remove 100%. That
    narrower population is the one the task is about, and it is the one a gate has to be calibrated
    against.
    """
    mine = [c for c in cells if c["rule_ref"] in mandated_rule_refs and c["verdict"] != "inapplicable"]
    if any(c["verdict"] == "fail" for c in mine):
        return False
    if any(c["rule_kind"] == "hard_exclusion" and c["verdict"] != "pass" for c in mine):
        return False
    measured = [c for c in mine if c["rule_kind"] != "hard_exclusion"] or mine
    return any(c["verdict"] in ("pass", "fail") for c in measured)


# --- the mandated-coverage floor ----------------------------------------------------------------
#
# The default: every criterion the task itself mandates and that *ranks* must be answered before a
# candidate is ranked on the task's objective. 1.0 and not a share, because the task stated each of
# them as a requirement, and 0.8 of five required receptors is "four of the five, and which one is
# missing depends on who has been studied". A mandated hard exclusion is not in the population --
# see `mandated_coverage`: it gates rather than ranks, and it has its own missingness policy.
DEFAULT_MANDATED_COVERAGE_FLOOR = 1.0


def mandated_coverage(cells: list[dict[str, Any]], mandated_rule_refs: set[str] | list[str] | tuple[str, ...]
                      ) -> dict[str, Any]:
    """How much of the task's own mandated criteria this candidate's cells answer, and what is left.

    The same population as `clears_mandated` above -- the criteria an adapter template built out of
    the task context, `criteria.is_task_mandated` -- measured rather than thresholded, so one
    definition of "mandated" serves the calibration guard's reference set and the board's floor.

    WHY a floor over this population is needed beside the two floors that already exist, measured on
    the published board of 14 October 2026 (`lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4`, rules@v3, 9
    criteria): `preference_scores` averages over the preference rules a candidate was *evaluated*
    on, so a candidate assessed on few cells is scored on its best-covered subset, and the top four
    entries each had one of the five required receptors measured -- mebendazole, an anthelmintic, at
    rank 4 -- ahead of candidates assessed on all five. The ranking coverage floor of 0.5 does not
    catch it because 4 of the 9 criteria are structural descriptors available for every compound, so
    a candidate with four descriptors and one receptor clears it comfortably.
    WHY not `on_missing`: an unknown on a *preference* is absence of information, not failure, and
    these receptor criteria are ordering preferences precisely because no potency threshold is
    evidence-supported. A preference ranks, it does not require (`clears_mandated`). What the task
    requires is that its own quantities be *answered* before a candidate is placed on the board at
    all, which is a property of the board and is applied where the board is built.

    WHY a mandated *hard exclusion* is not in the population, measured on the published board
    `lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4` (rules@v3, 14 October 2026): 16 candidates answer all
    five required receptors and only 9 of them answer the sixth mandated criterion, the oral-route
    hard exclusion. The 7 that do not are not unmeasured compounds -- ChEMBL derives its route flags
    from approved-product records and has no `oral` value for 1,262 of the 3,177 candidates, which is
    most of the Phase-III population the task explicitly admits -- and all 7 are already held at
    `provisional` by that gate's own `unknown_blocks_recommendation` policy. Three reasons they
    belong on the board anyway:
      * this floor exists so that a *comparable score* can be computed, which is a question about
        value-bearing quantities, not about gates: a gate contributes nothing to the score it would
        be withholding a position from;
      * the gate already carries its own missingness policy, and applying the floor on top conflates
        "cannot be recommended" with "cannot be ranked". `design_audit/registered_endpoint_decision.md`
        records that eligibility is reported separately from position and is not claimed as task
        satisfaction, so the two have to be able to come apart;
      * an unknown produced by a register's coverage is a fact about the register, not evidence about
        the compound, and nothing is learnt by declining to rank a compound because a database does
        not cover it.
    The gate's own effect is untouched: such a candidate still cannot be recommended, its
    `clears_hard_rules` is still false and the criterion is still named in `gate_blocked_by`. Only
    its rankability changes. A mandated gate the calibration guard demoted for this run arrives here
    as a `preference` -- the kind the cells were computed with -- and is counted, which is the same
    rule: what ranks is what the floor is about.

    `coverage` is None where the task mandates no criterion, or where this candidate has no mandated
    cell, or where every mandated criterion is a hard exclusion: an absent number reads as unknown
    and never as a pass (§9.2), and the floor treats it as "nothing to apply" rather than as a
    failure.
    """
    mandated = set(mandated_rule_refs)
    mine = [c for c in cells if c.get("rule_ref") in mandated and c.get("verdict") != "inapplicable"]
    ranked_on = [c for c in mine if c.get("rule_kind") != "hard_exclusion"]
    answered = [c for c in ranked_on if c.get("verdict") in ("pass", "fail")]
    return {"n": len(ranked_on), "answered_n": len(answered),
            "coverage": (len(answered) / len(ranked_on)) if ranked_on else None,
            "unanswered": sorted({c.get("attribute_ref") or c.get("rule_ref") for c in ranked_on
                                  if c.get("verdict") not in ("pass", "fail")}),
            # The mandated gates this floor does not measure, named rather than dropped: without
            # them a reader cannot tell a task that mandates five criteria from one that mandates
            # six of which one is a gate, and the second is what this task is.
            "gates": sorted({c.get("attribute_ref") or c.get("rule_ref") for c in mine
                             if c.get("rule_kind") == "hard_exclusion"}),
            "gates_unanswered": sorted({c.get("attribute_ref") or c.get("rule_ref") for c in mine
                                        if c.get("rule_kind") == "hard_exclusion"
                                        and c.get("verdict") not in ("pass", "fail")})}


def calibration_guard(cells_by_candidate: dict[str, list[dict[str, Any]]], rules: dict[str, dict[str, Any]], *,
                      mandated_rule_refs: list[str] | tuple[str, ...],
                      max_removed_share: float = DEFAULT_MAX_REFERENCE_EXCLUSION) -> dict[str, Any]:
    """Which hard exclusions remove too much of the mandated reference set to be gates, and by how much.

    Pure and deterministic: one pass over the cells, a count per hard exclusion, a comparison with
    one registered share. `rules` is {rule_ref: {"rule_kind", ...}} as the controller builds it.

    BLIND TO CANDIDATE IDENTITY, structurally and not by discipline. The function is handed cells
    and rule kinds and nothing else -- no task context, no identities, no seed list -- so there is no
    `is_reference_outcome` to consult, no label to branch on and no way to ask whether any particular
    compound is in the reference set or removed from it. What it returns is counts and shares: no
    candidate reference appears anywhere in the record, so neither the demotion nor the report can be
    read back to a candidate. Relabelling every candidate leaves the output identical, which
    `tests/test_calibration_guard.py` pins.
    """
    mandated = set(mandated_rule_refs)
    reference = sorted(candidate for candidate, cells in cells_by_candidate.items()
                       if clears_mandated(cells, mandated))
    hard = sorted(ref for ref, info in rules.items() if info["rule_kind"] == "hard_exclusion")
    report: dict[str, Any] = {
        "limit": max_removed_share, "minimum_reference_set": MIN_CALIBRATION_REFERENCE,
        "mandated_rule_refs": sorted(mandated), "reference_set_n": len(reference),
        "hard_exclusions_checked": [], "demoted": {}, "abstained": None,
    }
    if not mandated:
        report["abstained"] = ("no criterion was built from the task context itself, so there is no mandated "
                               "population to calibrate a gate against")
        return report
    if len(reference) < MIN_CALIBRATION_REFERENCE:
        report["abstained"] = (f"{len(reference)} candidate(s) clear the task's mandated criteria, below the "
                               f"{MIN_CALIBRATION_REFERENCE} a share can be measured over; no gate is demoted "
                               f"on this run")
        return report
    for rule_ref in hard:
        removed = sum(1 for candidate in reference
                      if any(c["rule_ref"] == rule_ref and c["verdict"] == "fail"
                             for c in cells_by_candidate[candidate]))
        share = removed / len(reference)
        over = share > max_removed_share
        report["hard_exclusions_checked"].append({"rule_ref": rule_ref, "removed_n": removed,
                                                  "removed_share": share, "demoted": over})
        if over:
            report["demoted"][rule_ref] = {
                "reason": "demoted_by_calibration_guard", "removed_share": share, "removed_n": removed,
                "reference_set_n": len(reference), "limit": max_removed_share,
                "rule_kind_before": "hard_exclusion", "rule_kind_after": "preference",
                "detail": (f"this hard exclusion removes {removed} of the {len(reference)} candidates that clear "
                           f"the task's mandated criteria ({share:.3f} of them), above the registered "
                           f"{max_removed_share:.2f}: a gate that removes almost everything the task's own "
                           f"requirement leaves is not discriminating between candidates, so it is demoted to a "
                           f"preference and goes on ranking them instead of deleting them"),
            }
    return report


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
