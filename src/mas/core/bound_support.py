"""Bound support (design §5.4, §5.6 `BOUND_SUPPORT_MISMATCH`): what stands behind a number on the board.

Every scientific cutoff and every scientific bound inside a `value_transform` is a separately
supported parameter: it is read on every cell the rule scores, so a number nothing states changes
what the board measures. Three defects measured on this checkout, 14 October 2026, each of them a
number entering a decision with nothing behind it:

  * `derivation.validate_proposal` accepted a `source_stated_value` cutoff of 90 whose cited claim
    stated 30 -- it checked that *a* cited claim carried *a* number, never that the claim carried
    this number (R4);
  * `criteria.check_value_transform` accepts `basis: expert_set` while `criteria.needs_expert` read
    only the rule's kind and its cutoff basis, so an ordering preference whose transform bound was
    expert-set scored with zero review items and `auto:trigger_table` authority (R3);
  * `adjudication._apply_revision` accepted `>= 30` -> `>= 90` with no refusal, having checked the
    schema and the rule kind but neither the support for 90 nor the direction of the change (R7).

WHAT IS MECHANICAL AND WHAT IS DECLARED. Unit normalization and explicit derivations are checked
here arithmetically: given the number a passage states, the declared conversion must produce the
executable parameter, or the record is refused. Whether the passage *states a decision threshold*,
*reports a measurement*, or *provides a heuristic*, and why it applies to this candidate population,
cannot be read out of prose by a machine without inventing the answer -- so they are declared
fields (`statement_kind`, `applicability_rationale`) and they are recorded, not guessed. A model
critic may argue about them; it cannot stand in for the arithmetic (§6 F2).

ONE PLACE WHERE THE MACHINE CAN CONTRADICT A DECLARATION, and it is the case the live registry is
in. The molecular-weight bound 500 traces to a claim whose quote reads "Most clinically relevant
kinase inhibitors typically fall within the range of approximately 380-500 Da, which is considered
close to the upper limit compatible with efficient passive diffusion". The number is in the quote,
and the passage states a *range*: 500 is one end of it. A one-sided bound taken from one end of a
stated range is the proposer drawing a line where the source drew a band, which is an interpretation
whatever the record says it is -- so `states_decision_threshold` on a range endpoint is refused and
the bound is recorded as `interpretation_added`, needing a decision before it scores. A transform
that uses the *whole* stated range (`distance_outside_band` whose low and high are the range's own
ends, as the lipophilicity attribute's 2 to 4 band is) restates it and is not an interpretation.

Nothing here writes, calls a model or reaches the network: `validate` is a function of one attribute,
one rule and the claims it cites, which is what lets every site that introduces or changes a
decision-bearing number call the same validator -- proposal validation, revision, promotion,
collapse-generated versions and rule-set confirmation.
"""

from __future__ import annotations

import re
from typing import Any

from .reading import value_in_quote

# What a passage can be doing with a number (§5.4 item 5). Only the first one makes the number a
# screening requirement the source itself proposed; the other two are a reading the criterion adds.
STATEMENT_KINDS = ("states_decision_threshold", "reports_measurement", "provides_heuristic")
# Bases that assert a source states the number, so a cited claim has to state it.
SOURCED_BASES = ("source_stated_value", "regulatory_or_standard_reference")
# Bases that assert a person's or the task's own authority instead of a source's. They are not
# traceable to a claim -- asking a claim to state an expert's judgement would report a missing
# source where none was ever claimed -- and they need that authority instead (`criteria.needs_expert`).
AUTHORITY_BASES = ("expert_set", "task_constraint")
# Bases that say in so many words that no number is executable, so there is nothing to support.
UNBOUNDED_BASES = ("none_evidence_insufficient", "measured_distribution")
# How a support record may get from the number a passage states to the executable parameter.
CONVERSION_KINDS = ("identity", "unit_conversion", "explicit_derivation")
# What the passage says about the edges of its number (§5.4 item 3). Declared, and cross-checked
# against the range the cited claim records: a record calling a stated range a point value is
# reporting the passage as more definite than it is.
CENSORING = ("none", "left_censored", "right_censored", "range")

# One state per bound, worst first. `unaudited` is not a pass: it says the store holds nothing to
# check this number against, which §9.2 requires be marked unknown rather than given a passing status.
STATES = ("invalid_support_record", "unsupported", "interpretation_added", "authority_basis",
          "interpretation_undeclared", "unaudited", "sourced_threshold")
# States that stop a proposal, a revision, a promotion, a collapse or an entry into a rule set.
BLOCKING_STATES = ("invalid_support_record", "unsupported")
# States where the number is traceable but its reading as a decision line is the criterion's own, so
# the parameter needs a decision before it may score (F2 acceptance, via `criteria.needs_expert`).
REVIEW_STATES = ("interpretation_added",)

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
# A stated range, written either way round: "380-500 Da" and "2 to 4 log units" are both ranges, and
# a bound that is one end of one is a different kind of support from a bound a passage states alone.
_RANGE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:[‐-―−-]|to|and)\s*(-?\d+(?:\.\d+)?)")
_TOLERANCE = 1e-9


def numbers(text: str) -> set[str]:
    """Every number in a text, as comparable strings (trailing zeros of a decimal dropped)."""
    return {n.rstrip("0").rstrip(".") if "." in n else n for n in _NUMBER.findall(text or "")}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _unit(unit: str | None) -> str | None:
    # WHY the assessor's table and not a local one: `Da` and `g/mol` are one unit there
    # (`UNIT_SYNONYMS`), and a bound judged against another table would be refused here while the
    # cells it scores were being compared against it happily.
    from .assessor import canonical_unit        # imported here: `assessor` reads `criteria`, which reads this module

    return canonical_unit(unit)


def bounds(attribute: dict[str, Any], rule: dict[str, Any]) -> list[dict[str, Any]]:
    """Every number this criterion would compare a candidate against, by parameter path.

    A rule's cutoff and a transform's bounds are the same kind of thing, which is why
    `check_value_transform` demands a basis for a transform bound in the same words the registry
    refuses an arbitrary cutoff -- and why F3's defect was possible at all: moving the number from
    the cutoff into the transform moved it out of the only field `needs_expert` was reading.
    """
    from . import criteria                      # imported here: `criteria` reads this module for its authority table

    out: list[dict[str, Any]] = []
    cutoff = rule.get("cutoff") or {}
    if _is_number(cutoff.get("value")):
        out.append({"parameter_path": "rule.cutoff.value", "kind": "cutoff", "parameter": "value",
                    "value": cutoff["value"], "unit": cutoff.get("unit") or attribute.get("unit"),
                    "comparator": cutoff.get("comparator"), "basis": rule.get("cutoff_basis"),
                    "source_refs": None})
    transform = attribute.get("value_transform") or {}
    for parameter in criteria.VALUE_TRANSFORMS.get(transform.get("kind"), ()):
        if _is_number(transform.get(parameter)):
            out.append({"parameter_path": f"attribute.value_transform.{parameter}",
                        "kind": f"value_transform.{transform['kind']}", "parameter": parameter,
                        "value": transform[parameter], "unit": attribute.get("unit"), "comparator": None,
                        "basis": transform.get("basis"), "source_refs": list(transform.get("source_refs") or [])})
    return out


def claims_stating(bound: float | int, unit: str | None, claims: list[dict[str, Any]]) -> list[dict[str, str]]:
    """The cited claims that state one bound, and how each states it.

    Either the claim's own value is the bound in the attribute's unit, or the number appears in the
    text the claim was read from -- the same two kinds of trace `adjudication.restated_constraint`
    accepts against a constraint's text. Recording which of the two it was keeps the declaration
    auditable: a number matched inside a quote is a weaker trace than a claim whose value *is* the
    bound. (This function was `adjudication._claims_stating`; it lives here so that an audit, a
    machine adjudication and a proposal validator cannot disagree about what "traceable" means.)
    """
    out = []
    for claim in claims:
        compatible = not unit or not claim.get("unit") or _unit(claim["unit"]) == _unit(unit)
        value = claim.get("value")
        ends = [claim.get("value_low"), claim.get("value_high")]
        if _is_number(value) and float(value) == float(bound) and compatible:
            out.append({"claim_id": claim["claim_id"], "states_it": "claim_value"})
        elif compatible and any(_is_number(end) and float(end) == float(bound) for end in ends):
            # A claim whose recorded range ends on this number does state it: the reader put a
            # stated range in `value_low`/`value_high` with `value` null (`reading.py` rule 2), and
            # reading only `value` reported "no claim states 500" of the very claim that states it.
            out.append({"claim_id": claim["claim_id"], "states_it": "claim_range_end"})
        elif value_in_quote(float(bound), claim_text(claim)):
            # WHY `value_in_quote` and not a set of the numbers in the text: a hyphenated range
            # reads as "380" and "-500" to a plain number scan, so the live molecular-weight quote
            # ("approximately 380-500 Da") stated no 500 at all under the old comparison.
            out.append({"claim_id": claim["claim_id"], "states_it": "claim_quote"})
    return out


def claim_text(claim: dict[str, Any]) -> str:
    """The text one claim was read from: its restatement and the span quoted from the document."""
    return " ".join(str(claim.get(field) or "") for field in ("normalized_statement", "claim_text")) \
        + " " + str((claim.get("location") or {}).get("quoted_span") or "")


def stated_ranges(claim: dict[str, Any]) -> list[tuple[float, float]]:
    """Every range this claim states: its recorded low/high pair, and any range in its own text.

    The reader records a stated range in `value_low`/`value_high` with `value` null (`reading.py`
    READER_SYSTEM rule 2), so the recorded pair is the first place to look; a range the reader did
    not split out is still written as a range in the quote, which is the second.
    """
    out: list[tuple[float, float]] = []
    low, high = claim.get("value_low"), claim.get("value_high")
    if _is_number(low) and _is_number(high) and float(low) < float(high):
        out.append((float(low), float(high)))
    for first, second in _RANGE.findall(claim_text(claim)):
        pair = (float(first), float(second))
        if pair[0] < pair[1] and pair not in out:
            out.append(pair)
    return out


def range_endpoint(bound: float | int, claims: list[dict[str, Any]], *,
                   siblings: tuple[float, ...] = ()) -> dict[str, Any] | None:
    """The stated range this bound is one end of, when the criterion uses that end alone.

    Returns None when no cited claim states such a range, and None when the criterion's bounds cover
    the whole range: a band whose low and high are the range's own ends restates the range the
    passage states, while a one-sided bound at one end draws a line where the source drew a band.
    """
    for claim in claims:
        for low, high in stated_ranges(claim):
            if abs(float(bound) - low) > _TOLERANCE and abs(float(bound) - high) > _TOLERANCE:
                continue
            covered = {round(float(s), 9) for s in siblings} | {round(float(bound), 9)}
            if {round(low, 9), round(high, 9)} <= covered:
                continue
            return {"claim_id": claim["claim_id"], "range": [low, high], "endpoint": float(bound)}
    return None


def support_records(attribute: dict[str, Any], rule: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The declared support records, by the parameter path each one supports.

    A record is declared on whichever object holds the parameter -- the rule for its cutoff, the
    attribute for its transform bounds -- so that a record travels with the version it supports
    through normalization, promotion, revision and collapse (§5.3: a field the schema accepts and
    nothing downstream reads is an implementation failure).
    """
    out: dict[str, dict[str, Any]] = {}
    for record in list(rule.get("bound_support") or []) + list(attribute.get("bound_support") or []):
        if isinstance(record, dict) and record.get("parameter_path"):
            out[record["parameter_path"]] = record
    return out


def _finding(finding_class: str, severity: str, parameter_path: str, message: str) -> dict[str, Any]:
    return {"finding_class": finding_class, "severity": severity, "parameter_path": parameter_path,
            "message": message}


def _converted(record: dict[str, Any]) -> tuple[float | None, str]:
    """The executable number this record's declared conversion produces, and what it did.

    Deterministic and arithmetic only: a factor is applied, an explicit derivation states the result
    it computes and that result is the number checked against the parameter. Prose that would need
    reading to evaluate ("about half of the stated bound") produces nothing, which is a refusal
    rather than a guess.
    """
    source = record.get("source_number")
    conversion = record.get("conversion") or {"kind": "identity"}
    kind = conversion.get("kind")
    if not _is_number(source):
        return None, "no_source_number"
    if kind == "identity":
        return float(source), "identity"
    if kind == "unit_conversion":
        factor = conversion.get("factor")
        if not _is_number(factor) or float(factor) == 0.0:
            return None, "no_factor"
        return float(source) * float(factor), "unit_conversion"
    if kind == "explicit_derivation":
        result = conversion.get("result")
        if not _is_number(result):
            return None, "no_result"
        return float(result), "explicit_derivation"
    return None, "unknown_conversion_kind"


def _check_declared(bound: dict[str, Any], record: dict[str, Any],
                    claims_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The four outcomes of one declared support record, recorded separately (§5.4 item 7)."""
    path = bound["parameter_path"]
    findings: list[dict[str, Any]] = []
    claim = claims_by_id.get(record.get("claim_id"))
    quote, arithmetic = "unresolved", "not_checked"

    if record.get("claim_id") and claim is None and claims_by_id:
        findings.append(_finding("bound_support_mismatch", "blocking", path,
                                 f"the support record for {path} cites claim {record.get('claim_id')!r}, which is "
                                 f"not an admitted claim this criterion cites"))
    for field in ("source_number", "source_unit", "statement_kind", "applicability_rationale"):
        if record.get(field) in (None, "", []):
            findings.append(_finding("schema", "blocking", path,
                                     f"the support record for {path} declares no {field}; §5.4 asks for the number "
                                     f"and unit the passage states, what the passage is doing with it, and why it "
                                     f"applies to this population"))
    statement_kind = record.get("statement_kind")
    if statement_kind is not None and statement_kind not in STATEMENT_KINDS:
        findings.append(_finding("schema", "blocking", path,
                                 f"statement_kind {statement_kind!r} on {path} is not one of {STATEMENT_KINDS}"))
    if record.get("censoring") is not None and record["censoring"] not in CENSORING:
        findings.append(_finding("schema", "blocking", path,
                                 f"censoring {record['censoring']!r} on {path} is not one of {CENSORING}"))
    if record.get("source_comparator") is not None:
        from . import criteria                 # imported here for the same reason `bounds` imports it

        if record["source_comparator"] not in criteria.COMPARATORS:
            findings.append(_finding("schema", "blocking", path,
                                     f"source_comparator {record['source_comparator']!r} on {path} is not one of "
                                     f"{criteria.COMPARATORS}"))
    conversion = (record.get("conversion") or {"kind": "identity"}).get("kind")
    if conversion not in CONVERSION_KINDS:
        findings.append(_finding("schema", "blocking", path,
                                 f"the support record for {path} declares conversion kind {conversion!r}, "
                                 f"not one of {CONVERSION_KINDS}"))

    executable, how = _converted(record)
    if executable is None:
        arithmetic = "not_executable"
        findings.append(_finding("bound_support_mismatch", "blocking", path,
                                 f"the support record for {path} does not produce an executable number "
                                 f"({how}); a bound nobody can recompute is a bound nobody can check"))
    elif abs(executable - float(bound["value"])) > _TOLERANCE:
        arithmetic = "fail"
        findings.append(_finding("bound_support_mismatch", "blocking", path,
                                 f"the support record for {path} states {record.get('source_number')} "
                                 f"{record.get('source_unit')} and its declared {how} produces {executable}, "
                                 f"while the executable parameter is {bound['value']} "
                                 f"{bound.get('unit') or ''}".rstrip()))
    else:
        arithmetic = "pass"
        if how == "unit_conversion":
            to_unit = (record.get("conversion") or {}).get("to_unit")
            if _unit(to_unit) != _unit(bound.get("unit")):
                arithmetic = "fail"
                findings.append(_finding("units", "blocking", path,
                                         f"the support record for {path} converts to {to_unit!r} while the "
                                         f"parameter is in {bound.get('unit')!r}"))

    if claim is not None:
        source = record.get("source_number")
        if _is_number(source) and value_in_quote(float(source), (claim.get("location") or {}).get("quoted_span") or ""):
            quote = "pass"
        elif _is_number(source) and numbers(str(source)) <= numbers(claim_text(claim)):
            quote = "restatement_only"
        else:
            quote = "fail"
            findings.append(_finding("bound_support_mismatch", "blocking", path,
                                     f"the support record for {path} says claim {claim['claim_id']} states "
                                     f"{source}, and that number is not in the span quoted from the document"))
        if _unit(record.get("source_unit")) != _unit(claim.get("unit")) and claim.get("unit"):
            findings.append(_finding("units", "material", path,
                                     f"the support record for {path} reads claim {claim['claim_id']} as "
                                     f"{record.get('source_unit')!r} while the claim records {claim.get('unit')!r}"))
        if record.get("censoring") == "none" and stated_ranges(claim):
            (low, high) = stated_ranges(claim)[0]
            findings.append(_finding("bound_support_mismatch", "material", path,
                                     f"the support record for {path} declares no censoring while claim "
                                     f"{claim['claim_id']} states the range {low} to {high}"))
    return {"findings": findings, "quote": quote, "arithmetic": arithmetic, "statement_kind": statement_kind,
            "claim": claim, "conversion": how,
            # Carried so that every declared field of §5.4 item 3 reaches the report, the rule-set
            # entry and the export rather than being accepted and read by nothing (§5.3).
            "censoring": record.get("censoring"), "source_comparator": record.get("source_comparator"),
            "measurement_context": record.get("measurement_context")}


def validate(attribute: dict[str, Any], rule: dict[str, Any], *,
             claims: list[dict[str, Any]] | None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Support for every decision-bearing number of one criterion (§5.4). Pure; never raises.

    `claims` are the admitted claims this criterion cites, or None where the caller cannot resolve
    them (an old record whose derivation run is not in this store root). None is not a pass: every
    bound is then `unaudited` and says so, because a status manufactured for absent metadata is the
    thing §9.2 forbids.
    """
    claims = list(claims) if claims is not None else None
    claims_by_id = {c["claim_id"]: c for c in (claims or []) if c.get("claim_id")}
    declared = support_records(attribute, rule)
    found = bounds(attribute, rule)
    paths = {b["parameter_path"] for b in found}
    outcomes, findings = [], []

    for path, record in sorted(declared.items()):
        if path not in paths:
            findings.append(_finding("schema", "blocking", path,
                                     f"a support record names parameter {path!r}, which this criterion does not "
                                     f"hold; a record supporting nothing would read as support for everything"))

    for bound in found:
        path = bound["parameter_path"]
        record = declared.get(path)
        basis = bound.get("basis")
        siblings = tuple(b["value"] for b in found if b["kind"] == bound["kind"] and b is not bound)
        cited = claims if bound["source_refs"] is None else \
            [claims_by_id[ref] for ref in bound["source_refs"] if ref in claims_by_id]
        outcome = {**{k: bound[k] for k in ("parameter_path", "kind", "parameter", "value", "unit",
                                            "comparator", "basis")},
                   "declared": record is not None, "quote": "not_declared", "arithmetic": "not_declared",
                   "semantic_support": "undeclared", "authority": "unaudited", "trace": [], "trace_kind": "none",
                   "range_endpoint": None, "state": "unaudited"}

        if record is not None:
            checked = _check_declared(bound, record, claims_by_id)
            findings += checked["findings"]
            outcome.update(quote=checked["quote"], arithmetic=checked["arithmetic"],
                           semantic_support=checked["statement_kind"] or "undeclared",
                           conversion=checked["conversion"], censoring=checked["censoring"],
                           source_comparator=checked["source_comparator"],
                           measurement_context=checked["measurement_context"],
                           applicability_rationale=record.get("applicability_rationale"),
                           claim_id=record.get("claim_id"))

        trace = claims_stating(bound["value"], bound["unit"], cited) if cited else []
        outcome["trace"] = trace
        if trace:
            # The strongest trace the cited claims offer, in the order they establish the number:
            # the claim's own value, an end of a range it records, the text it was read from.
            outcome["trace_kind"] = next(kind for kind in ("claim_value", "claim_range_end", "claim_quote")
                                         if any(t["states_it"] == kind for t in trace))
        endpoint = range_endpoint(bound["value"], [c for c in (cited or []) if c], siblings=siblings) if cited else None
        outcome["range_endpoint"] = endpoint

        if basis in AUTHORITY_BASES:
            # The number claims a person's judgement or the task's own text, not a source's
            # statement, so there is no claim to trace and the authority is what has to be there.
            outcome.update(state="authority_basis", authority="decision_required",
                           semantic_support=outcome["semantic_support"] if record else "not_source_stated")
        elif basis in SOURCED_BASES:
            if bound["source_refs"] is not None and not bound["source_refs"]:
                outcome.update(state="unsupported", authority="none")
                findings.append(_finding("arbitrary_cutoff", "blocking", path,
                                         f"{path} claims a source-stated bound of {bound['value']} and names no "
                                         f"claim that states it"))
            elif cited is None or not cited:
                outcome.update(state="unaudited", authority="unaudited")
            elif not trace and not (record and outcome["arithmetic"] == "pass"):
                # The measured F2 defect: a cutoff of 90 citing a claim that states 30. A cited
                # claim carrying *a* number is not support for *this* number.
                outcome.update(state="unsupported", authority="none")
                findings.append(_finding("bound_support_mismatch", "blocking", path,
                                         f"{path} reads {bound['value']} {bound.get('unit') or ''}".rstrip()
                                         + f" on basis {basis}, and none of the {len(cited)} cited claims states "
                                           f"that number by its value, in the text it was read from, or through a "
                                           f"declared conversion"))
            elif record is None:
                outcome.update(state="interpretation_undeclared", authority="unaudited")
                if endpoint is not None:
                    # Recorded, not refused: what the passage does with the number is undeclared, and
                    # §9.2 asks that absent metadata be marked unknown rather than given a status --
                    # a failing one included. The deterministic half is stated here so a reviewer and
                    # a `require_bound_support` gate see it: the only trace for this number is one end
                    # of a range, which is the live molecular-weight bound's exact position.
                    findings.append(_finding("bound_support_mismatch", "material", path,
                                             f"{path} reads {bound['value']} and the only trace for it is one end "
                                             f"of the range {endpoint['range'][0]} to {endpoint['range'][1]} that "
                                             f"claim {endpoint['claim_id']} states; no support record says whether "
                                             f"that passage states a decision threshold, reports a measurement or "
                                             f"provides a heuristic"))
            elif outcome["semantic_support"] == "states_decision_threshold":
                if endpoint is not None:
                    # The live molecular-weight case: 500 is the upper end of the range
                    # "approximately 380-500 Da" the passage states. One end of a stated range,
                    # used alone, is a line the criterion draws rather than one the source states.
                    outcome.update(state="interpretation_added", authority="decision_required",
                                   semantic_support="reports_measurement")
                    findings.append(_finding("bound_support_mismatch", "material", path,
                                             f"the support record for {path} declares that the passage states "
                                             f"{bound['value']} as a decision threshold, while claim "
                                             f"{endpoint['claim_id']} states the range "
                                             f"{endpoint['range'][0]} to {endpoint['range'][1]} and this bound is "
                                             f"one end of it; the line is the criterion's, so it needs a decision"))
                elif (checked_claim := (claims_by_id.get(record.get("claim_id")) or {})).get("determination_basis") \
                        == "measured":
                    # The reader, holding the passage, recorded that it measures rather than asserts
                    # (`reading.CLAIM_SCHEMA` determination_basis). A record declaring the same
                    # passage states a requirement contradicts a field another role already wrote.
                    outcome.update(state="interpretation_added", authority="decision_required",
                                   semantic_support="reports_measurement")
                    findings.append(_finding("bound_support_mismatch", "material", path,
                                             f"the support record for {path} declares a stated decision threshold "
                                             f"while claim {checked_claim.get('claim_id')} is recorded as "
                                             f"determination_basis measured; a measurement is not a requirement"))
                else:
                    outcome.update(state="sourced_threshold", authority="source_stated")
            else:
                outcome.update(state="interpretation_added", authority="decision_required")
        elif basis in UNBOUNDED_BASES:
            # A basis that says no number is executable, holding one anyway. `check_rule` refuses
            # this for a cutoff; a transform bound reaches here.
            outcome.update(state="unsupported", authority="none")
            findings.append(_finding("arbitrary_cutoff", "blocking", path,
                                     f"{path} holds {bound['value']} on basis {basis}, which states that no "
                                     f"number is supported"))
        if record is not None and any(f["severity"] == "blocking" and f["parameter_path"] == path for f in findings):
            outcome["state"] = "invalid_support_record"
        outcomes.append(outcome)

    states = {o["parameter_path"]: o["state"] for o in outcomes}
    return {"bounds": outcomes, "findings": findings, "states": states,
            "blocking": [f for f in findings if f["severity"] == "blocking"],
            "review_paths": sorted(p for p, s in states.items() if s in REVIEW_STATES),
            "unsupported_paths": sorted(p for p, s in states.items() if s in BLOCKING_STATES),
            "claims_resolved": None if claims is None else len(claims_by_id)}


def messages(report: dict[str, Any], *, severity: str = "blocking") -> list[str]:
    """The report's findings in the `class: message` form the proposal validator returns."""
    return [f"{f['finding_class']}: {f['message']}" for f in report["findings"]
            if severity is None or f["severity"] == severity]


def resolve_claims(core, task_id: str, refs: set[str] | list[str], *,
                   run_ids: tuple[str, ...] = ()) -> list[dict[str, Any]] | None:
    """The admitted claims these ids name, read from the task stream and its derivation runs.

    Returns None when nothing was found and ids were asked for, which is the `unaudited` case: the
    criterion cites claims this store root cannot resolve, and absent evidence is not evidence of a
    valid bound. A criterion citing nothing returns an empty list, which is a different statement.

    WHY it widens to the run streams: a criterion's claims were enumerated in a derivation run's own
    stream, not in the task's, and `confirm_rule_set` is given neither. Widening reads one event per
    run stream to check the purpose on its binding, which keeps a sweep out -- a sweep records a
    claim per cell, and replaying thousands of them to resolve one citation would make confirming a
    rule set cost what the sweep cost.
    """
    from . import ledger

    wanted = {r for r in refs if r}
    if not wanted:
        return []
    found = {c["claim_id"]: c for c in ledger.claims(core, [task_id] + list(run_ids)) if c["claim_id"] in wanted}
    for stream in core.journal.streams("run_"):
        if wanted <= set(found):
            break
        if stream == task_id or stream in run_ids:
            continue
        created = core.journal.replay(stream, 1, 1)
        if not created or not created[0].payload.get("binding_artifact_id"):
            continue
        if core.artifacts.payload(created[0].payload["binding_artifact_id"]).get("run_purpose") != "criteria_derivation":
            continue
        found.update({c["claim_id"]: c for c in ledger.claims(core, [stream]) if c["claim_id"] in wanted})
    return list(found.values()) or None


# --- revision relations (F4) ---------------------------------------------------------------------

# The fields a revision may touch at all. Anything else -- the attribute, its unit, its transform,
# the rule's identity -- is not a revision of this rule but a different criterion, and an adjudicator
# that could write it would be authoring criteria rather than settling a dispute.
REVISABLE_FIELDS = ("rule_kind", "predicate_form", "cutoff", "cutoff_basis",
                    "on_missing", "on_inapplicable", "on_conflict")
# How hard each rule kind is on a candidate: a hard exclusion deletes it from the result, a
# preference moves it, an exploratory consideration does neither.
_KIND_STRENGTH = {"exploratory_consideration": 0, "preference": 1, "hard_exclusion": 2}
# How hard each on-state policy is on a candidate whose value is missing, inapplicable or disputed.
_POLICY_STRENGTH = {"unknown_no_penalty": 0, "route_to_human": 1, "unknown_blocks_recommendation": 2, "exclude": 3}
# Which way a comparator points: with `>=` a larger cutoff demands more of a candidate, with `<=` a
# smaller one does. `==` points nowhere -- any change to an equality is a different requirement.
_DIRECTION = {">=": 1, ">": 1, "<=": -1, "<": -1}
# Strictness within one direction: `>` demands more than `>=` at the same number.
_STRICTNESS = {">=": 0, ">": 1, "<=": 0, "<": 1}
RELATIONS = ("neutral", "weaker", "stronger", "not_decidable")
# What the registry applies when a rule does not set the field (`criteria.propose` fills these in),
# so that a revision naming the default explicitly is not read as a change, and dropping to a
# milder policy from an unset field is read as the weakening it is.
_DEFAULTS = {"predicate_form": "threshold", "on_missing": "unknown_blocks_recommendation",
             "on_inapplicable": "unknown_blocks_recommendation", "on_conflict": "unknown_blocks_recommendation"}


def _effective(rule: dict[str, Any], field: str) -> Any:
    value = rule.get(field)
    return _DEFAULTS[field] if value is None and field in _DEFAULTS else value


def _relation(*relations: str) -> str:
    """The relation of a whole revision, from its fields': the least decidable, then the strongest."""
    for worst in ("not_decidable", "stronger", "weaker"):
        if worst in relations:
            return worst
    return "neutral"


def field_diff(before: dict[str, Any], after: dict[str, Any], fields: tuple[str, ...] = REVISABLE_FIELDS,
               ) -> list[dict[str, Any]]:
    """A field-level diff of two versions of one rule (§6 F4: preserve both versions and a diff)."""
    return [{"field": field, "from": _effective(before, field), "to": _effective(after, field)}
            for field in fields if _effective(before, field) != _effective(after, field)]


def _cutoff_relation(before: dict[str, Any], after: dict[str, Any]) -> tuple[str, str]:
    """How the revised cutoff compares with the original one, and why.

    Not decidable, rather than weaker, wherever the two cutoffs are not two settings of one
    requirement: a comparator that points the other way, a unit the rule did not have before, a
    categorical membership test, an equality. "Weaker" has to mean something about candidates, and
    across those changes it does not (§6 F4).
    """
    old, new = before.get("cutoff") or {}, after.get("cutoff") or {}
    if not old and not new:
        return "neutral", "neither version holds a cutoff"
    if old and not new:
        return "weaker", "the revision drops the cutoff"
    if new and not old:
        return "not_decidable", "the revision introduces a cutoff where the rule had none"
    if _unit(old.get("unit")) != _unit(new.get("unit")):
        return "not_decidable", (f"the cutoff unit changes from {old.get('unit')!r} to {new.get('unit')!r}, so the "
                                 f"two numbers are not two settings of one requirement")
    one, two = old.get("comparator"), new.get("comparator")
    if one not in _DIRECTION or two not in _DIRECTION:
        return ("neutral", "the cutoff is unchanged") if old == new else \
            ("not_decidable", f"comparator {one!r} to {two!r} is not a change in how much is required")
    if _DIRECTION[one] != _DIRECTION[two]:
        return "not_decidable", f"the comparator reverses from {one!r} to {two!r}"
    if not (_is_number(old.get("value")) and _is_number(new.get("value"))):
        return "not_decidable", "one of the two cutoffs holds no number"
    demanded = (float(new["value"]) - float(old["value"])) * _DIRECTION[two]
    if abs(demanded) <= _TOLERANCE:
        tighter = _STRICTNESS[two] - _STRICTNESS[one]
        if tighter > 0:
            return "stronger", f"the comparator tightens from {one!r} to {two!r} at the same number"
        if tighter < 0:
            return "weaker", f"the comparator loosens from {one!r} to {two!r} at the same number"
        return "neutral", "the cutoff is unchanged"
    if demanded > 0:
        return "stronger", (f"{two} {new['value']} demands more of a candidate than {one} {old['value']}")
    return "weaker", f"{two} {new['value']} demands less of a candidate than {one} {old['value']}"


def revision_relation(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """How a revised rule relates to the original: per field, and over the whole object.

    `adjudication` promised in its prompt that "a revision may only weaken a rule", and a promise in
    a prompt is not a check: `_apply_revision` refused a revision to `hard_exclusion` and an
    `expert_set` cutoff basis and applied everything else, including `>= 30` -> `>= 90` (R7). This
    says per field which way a change points, and answers `not_decidable` wherever "weaker" has no
    meaning, so the caller can require a decision instead of guessing.
    """
    changes = []
    for change in field_diff(before, after):
        field, old, new = change["field"], change["from"], change["to"]
        if field == "rule_kind":
            moved = _KIND_STRENGTH.get(new, 0) - _KIND_STRENGTH.get(old, 0)
            relation, why = (("stronger", f"rule_kind {old} -> {new} bears harder on a candidate") if moved > 0
                             else ("weaker", f"rule_kind {old} -> {new} bears less hard on a candidate") if moved < 0
                             else ("neutral", "the rule kind is unchanged"))
        elif field == "cutoff":
            relation, why = _cutoff_relation(before, after)
        elif field == "cutoff_basis":
            # Relabelling the basis changes which authority the number claims, never the number, so
            # it is not a weakening of anything; dropping the cutoff with the label is.
            relation, why = (("weaker", "the rule gives up its cutoff for none_evidence_insufficient")
                             if new == "none_evidence_insufficient" and not (after.get("cutoff") or {})
                             else ("not_decidable",
                                   f"cutoff_basis {old} -> {new} relabels where the number's authority comes from"))
        elif field == "predicate_form":
            relation, why = "not_decidable", f"predicate_form {old} -> {new} changes what the rule tests"
        elif field in ("on_missing", "on_inapplicable", "on_conflict"):
            moved = _POLICY_STRENGTH.get(new, 0) - _POLICY_STRENGTH.get(old, 0)
            relation, why = (("stronger", f"{field} {old} -> {new} bears harder on a candidate") if moved > 0
                             else ("weaker", f"{field} {old} -> {new} bears less hard on a candidate") if moved < 0
                             else ("neutral", f"{field} is unchanged in effect"))
        else:
            relation, why = "not_decidable", f"{field} is not a field a revision may set"
        changes.append({**change, "relation": relation, "why": why})
    return {"changes": changes, "relation": _relation(*(c["relation"] for c in changes)),
            "diff": [{k: c[k] for k in ("field", "from", "to")} for c in changes]}
