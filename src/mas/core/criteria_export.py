"""Exporting the registered criteria of one task as a reviewable snapshot (handoff §11).

WHY this module exists: the live store is `var/primary/store`, and `var/` is git-ignored, so a
checkout of this repository contains none of the 40 registered criteria, none of the 127 claims
their bounds are cited from and none of the 9 open proposer/critic disputes. The single artifact a
domain reviewer most needs is therefore the one artifact they cannot see. This writes it into the
repository: the same canonical records in JSON, one card per criterion in Markdown, a manifest
binding both to a journal position and a code commit, and a reconciliation of the counts the
project has quoted (72, 34, 40, 13, 8, 9, 26, 5), each said in terms of what it counts.

WHY the export pins a sequence: the store admits one writer and any number of readers, and a sweep
holds the write lock for roughly forty minutes while appending ~140,000 events. A fold taken while
that runs can read the registry before a collapse and the review queue after it. Every fold here
replays through `_PinnedJournal`, which clamps the task stream at one `seq`, so the snapshot is the
state at a stated position rather than whenever each query happened to land.

WHY it refuses to tidy anything: these records are the output of a generator whose merge stage
performed zero merges across every round ever run, with nine disputes unresolved. Corrected records
belong to a later version with a diff (handoff §11.1), so this reports what is there -- including
the 39 rules that carry no cutoff at all and the two bounds whose support is a transform parameter
rather than a cutoff -- and labels the whole export as the pre-repair baseline.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from . import (adjudication, assessor, collapse as collapse_mod, criteria, pool as pool_mod, review,
               task as task_mod)
from .canonical import canonical_bytes, sha256_hex
from .clock import utc_now
from .journal import Event, Journal
from .runtime import Core

EXPORT_SCHEMA_VERSION = 1

# The export's own label, not a status any record in the store carries. It is fixed text because a
# reviewer opening `derived_criteria_review.md` has no other way to know that the merge stage of the
# generator that produced these criteria never merged anything.
BASELINE_LABEL = "historical_baseline_pre_repair"
BASELINE_STATEMENT = (
    "Pre-repair historical baseline. These records are exported unchanged from the live store. They "
    "are the output of a derivation whose merge stage performed zero merges across every round, "
    "whose proposer/critic debate deferred its disagreements to the review queue rather than "
    "settling them, and whose open disputes are still open. No criterion was improved, corrected or "
    "tidied during export; corrected records belong to a later version published with a diff."
)

# Files the export writes, as the handoff §11.2 names them. The manifest is written last because it
# carries the digests of the others.
REVIEW_MARKDOWN = "derived_criteria_review.md"
REVIEW_JSON = "derived_criteria_review.json"
MANIFEST_JSON = "derived_criteria_manifest.json"
RECONCILIATION_MARKDOWN = "criteria_count_reconciliation.md"

# What a published card leaves out. Tool results and model traces are the private side of the
# derivation: `tool_result` artifacts hold whole provider responses and `trace` artifacts hold the
# prompts and completions of the proposer, critic and adjudicator roles. The quoted span, its
# locator, the document identity and the document's content hash are what an audit of a bound needs,
# and they are published; the transcript that produced them is not (handoff §11.2).
WITHHELD_ARTIFACT_KINDS = ("tool_result", "trace")

# Verdicts that mean a cell was not answered, so a criterion's measured coverage is the complement.
_UNKNOWN_VERDICTS = ("unknown_missing", "unknown_inapplicable", "unknown_conflict", "unknown_unresolved")


class ExportError(RuntimeError):
    pass


class _PinnedJournal:
    """A reader of one stream frozen at one `seq`, delegating everything else to the real journal.

    WHY a wrapper rather than a `to_seq` argument threaded through the folds: `pool.fold`,
    `review.items`, `collapse.records`, `adjudication.records` and `criteria.load` each replay the
    task stream themselves, and five call sites learning about a pin is five chances for one of them
    to read a later state than the others. Clamping the replay instead means a fold cannot see past
    the pin however it asks.
    """

    def __init__(self, journal: Journal, pins: dict[str, int]):
        self._journal = journal
        self.store = journal.store
        self.pins = dict(pins)

    def _pin(self, stream_id: str) -> int | None:
        return self.pins.get(stream_id)

    def replay(self, stream_id: str, from_seq: int = 1, to_seq: int | None = None) -> list[Event]:
        pin = self._pin(stream_id)
        if pin is not None:
            to_seq = pin if to_seq is None else min(to_seq, pin)
        return self._journal.replay(stream_id, from_seq, to_seq)

    def last_seq(self, stream_id: str) -> int:
        pin = self._pin(stream_id)
        return pin if pin is not None else self._journal.last_seq(stream_id)

    def of_type(self, event_type: str, stream_prefix: str = "") -> Iterator[Event]:
        for event in self._journal.of_type(event_type, stream_prefix):
            pin = self._pin(event.stream_id)
            if pin is None or event.seq <= pin:
                yield event

    def streams(self, prefix: str = "") -> list[str]:
        return self._journal.streams(prefix)

    def verify(self, stream_id: str) -> None:
        self._journal.verify(stream_id)

    def append(self, *args, **kwargs):
        raise ExportError("the export reads; it never appends")


def open_read_only(root: str | Path) -> Core:
    """The store a criteria export reads: open read-only, so a sweep may hold the write lock."""
    return Core.open(root, read_only=True)


def pinned(core: Core, task_id: str, at_seq: int | None = None) -> tuple[Core, int]:
    """A core whose task stream is frozen, and the sequence it is frozen at."""
    last = core.journal.last_seq(task_id)
    if last == 0:
        raise ExportError(f"no such task {task_id}")
    seq = last if at_seq is None else int(at_seq)
    if seq < 1 or seq > last:
        raise ExportError(f"--at-seq {seq} is outside {task_id} seq 1..{last}")
    return Core(core.store, _PinnedJournal(core.journal, {task_id: seq}), core.artifacts), seq


# --- reading the store ------------------------------------------------------------------------

def _artifact_hash(core: Core, artifact_id: str | None) -> str | None:
    if not artifact_id:
        return None
    row = core.store.db.execute("SELECT sha256 FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
    return row[0] if row else None


def _registry(core: Core, task_id: str) -> dict[str, dict[str, Any]]:
    """Every attribute and rule version proposed in the task, by ref, with its artifact identity."""
    out: dict[str, dict[str, Any]] = {}
    for event in core.journal.replay(task_id):
        if event.event_type != "criterion.version_proposed":
            continue
        payload = event.payload
        ref = f"{payload['id']}@v{payload['version']}"
        out[ref] = {"ref": ref, "kind": payload["kind"], "base_id": payload["id"], "version": payload["version"],
                    "artifact_id": payload["artifact_id"], "record": core.artifacts.payload(payload["artifact_id"]),
                    "seq": event.seq}
    return out


def _rule_sets(core: Core, task_id: str) -> list[dict[str, Any]]:
    out = []
    for event in core.journal.replay(task_id):
        if event.event_type == "criterion.version_approved":
            out.append(core.artifacts.payload(event.payload["artifact_id"]))
    return out


def _claim_locations(core: Core) -> dict[str, dict[str, Any]]:
    """claim_id -> where its admission was journalled and which artifact holds the record.

    WHY this is one indexed pass rather than a lookup per claim: the store holds 36,282 admission
    events, of which the 127 a criterion cites are a rounding error, and a `LIKE` scan per claim id
    would read the 1.9 GB events table once per claim. One pass over the type index costs ~3 s.
    """
    rows = core.store.db.execute(
        "SELECT stream_id, seq, event_type, json_extract(body, '$.payload.claim_id'), "
        "json_extract(body, '$.payload.artifact_id') FROM events "
        "WHERE event_type IN ('evidence.admitted', 'evidence.quarantined')"
    ).fetchall()
    return {claim_id: {"stream_id": stream, "seq": seq, "event_type": event_type, "artifact_id": artifact_id}
            for stream, seq, event_type, claim_id, artifact_id in rows if claim_id}


def _sources(core: Core, source_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not source_ids:
        return {}
    placeholders = ",".join("?" for _ in source_ids)
    rows = core.store.db.execute(
        f"SELECT artifact_id, sha256, body FROM artifacts WHERE kind = 'source' "
        f"AND json_extract(body, '$.payload.source_id') IN ({placeholders})", source_ids).fetchall()
    out: dict[str, dict[str, Any]] = {}
    for artifact_id, digest, body in rows:
        record = json.loads(body)["payload"]
        out[record["source_id"]] = {"artifact_id": artifact_id, "artifact_sha256": digest, "record": record}
    return out


def _board(core: Core, task_id: str) -> dict[str, Any] | None:
    """The latest published board for this task: its identity, its counts, and nothing per candidate.

    WHY the per-candidate rows stay out: this is the criteria package, and a board's 3,177 entries
    belong to the ranking package. What a criteria reviewer needs from it is which registered rules
    actually scored and on how many candidates each one was answered.
    """
    published = [e for e in core.journal.of_type("leaderboard.snapshot_published")
                 if e.payload.get("task_id") == task_id]
    if not published:
        return None
    event = published[-1]
    snapshot = core.artifacts.payload(event.payload["artifact_id"])
    entries = snapshot.get("candidate_entries") or []
    observed: dict[str, int] = {}
    assessed: dict[str, int] = {}
    for entry in entries:
        for ref, verdict in (entry.get("verdicts") or {}).items():
            assessed[ref] = assessed.get(ref, 0) + 1
            if verdict not in _UNKNOWN_VERDICTS and verdict is not None:
                observed[ref] = observed.get(ref, 0) + 1
    return {
        "snapshot_id": snapshot["snapshot_id"], "leaderboard_id": snapshot.get("leaderboard_id"),
        "rule_set_ref": snapshot.get("rules@v"), "run_id": snapshot.get("run_id"),
        "round_id": snapshot.get("round_id"), "result_kind": snapshot.get("result_kind"),
        "published_at": snapshot.get("published_at"), "task_context_ref": snapshot.get("task_context_id@v"),
        "evidence_snapshot_id": snapshot.get("evidence_snapshot_id"),
        "artifact_id": event.payload["artifact_id"],
        "artifact_sha256": _artifact_hash(core, event.payload["artifact_id"]),
        "candidates_assessed": len(entries),
        "candidates_ranked": sum(1 for e in entries if e.get("position") is not None),
        "ordering_method": snapshot.get("ordering_method"),
        "reporting_tuple": snapshot.get("reporting_tuple"),
        "human_review_summary": snapshot.get("human_review_summary"),
        "measured_coverage": {ref: {"observed": observed.get(ref, 0), "assessed": assessed[ref]}
                              for ref in sorted(assessed)},
    }


# --- views over one record --------------------------------------------------------------------

def _claim_view(core: Core, claim_id: str, locations: dict[str, dict[str, Any]],
                sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """One claim as an auditor needs it: the quotation, where it is, and which checks ran on it.

    WHY `quote_check` and `semantic_support` are separate keys rather than one status: the store
    records both, and they disagree on every criterion claim in this task -- 1,563 of them carry
    `location.span_checked_against_source: true` while every one carries
    `verification_status: unverified`. Collapsing them would publish either "no quote was ever
    checked" or "the passage was confirmed to support the bound", and neither is what happened
    (handoff §7.1).
    """
    located = locations.get(claim_id)
    if located is None:
        return {"claim_id": claim_id, "resolved": False,
                "note": "cited by a criterion but no admission event for it was found in this store"}
    record = core.artifacts.payload(located["artifact_id"])
    location = record.get("location") or {}
    source = sources.get(record.get("source_ref") or "")
    reasons = list(record.get("admission_reasons") or [])
    return {
        "claim_id": claim_id, "resolved": True,
        "recorded_on": {"stream_id": located["stream_id"], "seq": located["seq"], "event": located["event_type"]},
        "artifact_id": located["artifact_id"],
        "artifact_sha256": _artifact_hash(core, located["artifact_id"]),
        "claim_type": record.get("claim_type"), "question_purpose": record.get("question_purpose"),
        "polarity": record.get("polarity"),
        "statement": record.get("normalized_statement") or record.get("claim_text"),
        "statement_marker": record.get("claim_text_marker"),
        "quoted_span": location.get("quoted_span"),
        "location": {"location_kind": location.get("location_kind"), "locator_value": location.get("locator_value"),
                     "section_path": location.get("section_path"),
                     "span_checked_against_source": location.get("span_checked_against_source")},
        "value": {"value": record.get("value"), "value_low": record.get("value_low"),
                  "value_high": record.get("value_high"), "unit": record.get("unit"),
                  "unit_as_reported": record.get("unit_as_reported")},
        "scope": record.get("scope"), "scope_match": record.get("scope_match"),
        "evidence_kind": record.get("evidence_kind"), "determination_basis": record.get("determination_basis"),
        "reading_depth": record.get("reading_depth"),
        "admission": {"state": record.get("admission_state"), "reasons": reasons},
        "quote_check": {"span_checked_against_source": location.get("span_checked_against_source"),
                        "quote_verified": "quote_verified" in reasons},
        "numerical_consistency": ("value_in_quote" if "value_in_quote" in reasons else
                                  "value_not_in_quote" if "value_not_in_quote" in reasons else "not_recorded"),
        "semantic_support": {"verification_status": record.get("verification_status"),
                             "verifier": record.get("verifier") or None},
        "extracted_by": record.get("extraction_actor"),
        "recorded_at": record.get("recorded_at"),
        "source": None if source is None else {
            "source_id": source["record"].get("source_id"), "title": source["record"].get("title"),
            "container": source["record"].get("container"), "authors": source["record"].get("authors"),
            "issued_date": source["record"].get("issued_date"), "license": source["record"].get("license"),
            "identifiers": source["record"].get("identifiers"),
            "source_status": source["record"].get("source_status"),
            "access_state": source["record"].get("access_state"),
            "retraction_state": source["record"].get("retraction_state"),
            "version_label": source["record"].get("version_label"),
            "artifact_id": source["artifact_id"], "artifact_sha256": source["artifact_sha256"],
        },
        "document": {"artifact_id": record.get("document_artifact_id"),
                     "artifact_sha256": _artifact_hash(core, record.get("document_artifact_id"))},
    }


def _route_view(request: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(request.get("parameters") or {})
    subject = criteria.subject_parameters(request)
    return {"capability": request.get("capability"), "question_kind": request.get("question_kind"),
            "identifier_scheme": request.get("identifier_scheme"), "parameters": parameters,
            "subject_parameters": subject,
            "retrieval_parameters": {k: v for k, v in parameters.items() if k not in subject},
            "route_key_sha256": sha256_hex(criteria.route_key(request))}


def _parameter_support(attribute: dict[str, Any], rule: dict[str, Any]) -> list[dict[str, Any]]:
    """Every executable scientific parameter of a criterion, with the support records it names.

    WHY a cutoff's entry carries an empty `claim_refs` even where the rule cites claims: the schema
    has no per-parameter support field for a cutoff -- an attribute's `supporting_claim_refs` support
    the criterion, and only `value_transform.source_refs` names the claims behind one number. So a
    reviewer asking which quotation justifies a cutoff is told that the record does not say, rather
    than being handed the criterion's whole citation list as if it did.
    """
    out: list[dict[str, Any]] = []
    cutoff = rule.get("cutoff")
    if cutoff:
        out.append({"parameter_path": "rule.cutoff.value", "value": cutoff.get("value"),
                    "comparator": cutoff.get("comparator"), "unit": cutoff.get("unit"),
                    "basis": rule.get("cutoff_basis"), "claim_refs": [],
                    "support_field": "none; the rule schema carries no per-cutoff support record"})
    transform = attribute.get("value_transform")
    if transform:
        refs = sorted(transform.get("source_refs") or [])
        for parameter in criteria.VALUE_TRANSFORMS.get(transform.get("kind"), ()):
            out.append({"parameter_path": f"attribute.value_transform.{parameter}",
                        "value": transform.get(parameter), "comparator": None,
                        "unit": attribute.get("unit"), "basis": transform.get("basis"),
                        "claim_refs": refs, "support_field": "attribute.value_transform.source_refs"})
    return out


def _predicate_text(attribute: dict[str, Any], rule: dict[str, Any]) -> str:
    """The predicate in words, from the fields that execute it, for a reader comparing two criteria."""
    form, cutoff = rule.get("predicate_form"), rule.get("cutoff")
    unit = f" {attribute.get('unit')}" if attribute.get("unit") else ""
    if form == "ordering":
        return (f"orders candidates by the quantity, {attribute.get('direction')}; no cutoff"
                if not cutoff else
                f"orders candidates by the quantity, {attribute.get('direction')}, "
                f"with a cutoff at {cutoff.get('comparator')} {cutoff.get('value')}{unit}")
    if form == "qualitative_judgment":
        return "no executable predicate; the value is surfaced for a human judgement"
    if cutoff:
        return f"passes when the aggregated value is {cutoff.get('comparator')} {cutoff.get('value')}{unit}"
    return "no predicate: the rule declares no cutoff and no ordering"


_DECISION_ROLE = {"hard_exclusion": "hard_constraint", "preference": "preference",
                  "exploratory_consideration": "context_only"}


def _matching_facets(attribute: dict[str, Any], rule: dict[str, Any],
                     parameter_support: list[dict[str, Any]]) -> dict[str, Any]:
    """The four facets the recovery rubric compares, in a form that compares mechanically.

    WHY this block exists beside the prose card: the primary measurement classifies each sealed
    historical attribute against the derived set as exact, near-equivalent or missed on same
    operational quantity, same applicability, same decision semantics and a matching threshold
    where one exists (handoff §12.2). An evaluator reading only the 1,200-word definitions would be
    judging prose. These are the fields that execute, plus a hash over each of the two identities
    §5.2 separates, so two criteria can be called the same or different without reading either.

    `gaps` names, per facet, what this schema does not record -- for example that no field states a
    criterion's population, so applicability lives in the definition prose and nowhere a comparison
    can read it. It is a list of absences, never a reconstruction of what the absent value would be.
    """
    routes = criteria.evidence_routes(attribute)
    subjects = sorted({json.dumps(criteria.subject_parameters(r), sort_keys=True) for r in routes})
    transform = attribute.get("value_transform")
    quantity = {
        "quantity_name": attribute.get("name"),
        "subject_parameters": [json.loads(s) for s in subjects],
        "unit": attribute.get("unit"),
        "measurement_kind": attribute.get("measurement_kind"),
        "aggregation": attribute.get("aggregation"),
        "transform": transform,
        "accepted_evidence_kinds": attribute.get("acceptable_value_sources"),
        "accepted_determination_bases": attribute.get("acceptable_determination_bases"),
        # Part of the operational quantity and not a note beside it: "the measurement, and the
        # prediction only where there is none" is a different quantity from either of its halves,
        # and two criteria that differ only in this differ in what every cell of them carries.
        "determination_basis_precedence": attribute.get(criteria.PRECEDENCE_FIELD),
        "capabilities": sorted({r.get("capability") for r in routes if r.get("capability")}),
        "question_kinds": sorted({r.get("question_kind") for r in routes if r.get("question_kind")}),
    }
    semantics = {
        "decision_role": _DECISION_ROLE.get(rule.get("rule_kind"), "unlabelled"),
        "rule_kind": rule.get("rule_kind"),
        "predicate_form": rule.get("predicate_form"),
        "direction": attribute.get("direction"),
        "predicate": _predicate_text(attribute, rule),
        "on_missing": rule.get("on_missing"),
        "on_inapplicable": rule.get("on_inapplicable"),
        "on_conflict": rule.get("on_conflict"),
    }
    applicability = {
        "population": "every candidate in the task's declared universe; no narrower population is "
                      "recorded as a field",
        "applies_to_result_kind": rule.get("applies_to_result_kind"),
        "on_inapplicable": rule.get("on_inapplicable"),
        "conditions_field": attribute.get("applicability"),
        "conditions_recorded_as_a_field": attribute.get("applicability") is not None,
    }
    cutoff = rule.get("cutoff")
    bounds = [p for p in parameter_support if p["parameter_path"].startswith("attribute.value_transform")]
    threshold = {
        "state": "present" if cutoff else "explicitly_absent",
        "comparator": (cutoff or {}).get("comparator"), "value": (cutoff or {}).get("value"),
        "unit": (cutoff or {}).get("unit"), "basis": rule.get("cutoff_basis"),
        "cutoff_support_claim_refs": next((p["claim_refs"] for p in parameter_support
                                           if p["parameter_path"] == "rule.cutoff.value"), []),
        "transform_bounds": bounds,
    }
    gaps = []
    if all(not s for s in quantity["subject_parameters"]):
        gaps.append("operational_quantity.subject: no route carries a subject parameter, so the "
                    "quantity is identified by its unit, its direction and its name only")
    if not applicability["conditions_recorded_as_a_field"]:
        gaps.append("applicability: no structured population or condition field exists in this "
                    "schema; what the criterion is and is not about is stated in the definition prose")
    if semantics["predicate_form"] == "qualitative_judgment" and semantics["direction"] not in (
            None, "non_directional", "undetermined"):
        gaps.append(f"decision_semantics: direction `{semantics['direction']}` is declared while "
                    f"predicate_form is `qualitative_judgment`, so no predicate enforces it")
    if threshold["state"] == "present" and not threshold["cutoff_support_claim_refs"]:
        gaps.append("threshold: a cutoff is present and the schema records no per-cutoff support "
                    "record, so which passage justifies this number is not stated")
    return {
        "statement": "the four facets of the recovery rubric (handoff §12.2), read from executing "
                     "fields; `gaps` lists what the records do not say",
        "operational_quantity": quantity,
        "measurement_identity_sha256": sha256_hex(quantity),
        "applicability": applicability,
        "decision_semantics": semantics,
        "decision_identity_sha256": sha256_hex({"measurement": quantity, "semantics": semantics,
                                                "threshold": {k: threshold[k] for k in
                                                              ("state", "comparator", "value", "unit", "basis")}}),
        "threshold": threshold,
        "comparable_from_fields": not gaps,
        "gaps": gaps,
    }


def _origin(attribute: dict[str, Any], rule: dict[str, Any], pool_entry: dict[str, Any] | None) -> dict[str, Any]:
    """Where the criterion came from, in the four origins the handoff §2.4 asks to keep apart."""
    proposer = attribute.get("proposed_by") or {}
    derived_from = attribute.get("derived_from") or {}
    if proposer.get("role") == "adapter_template":
        kind = "task_mandated_template" if criteria.is_task_mandated(attribute) else "adapter_template"
    elif derived_from.get("pool_criterion"):
        kind = "literature_derived"
    else:
        kind = "unlabelled"
    written_by_software = {k: v for k, v in (("collapsed_by", attribute.get("collapsed_by")),
                                            ("adjudicated_by", attribute.get("adjudicated_by")),
                                            ("rule_adjudicated_by", rule.get("adjudicated_by")),
                                            ("rule_collapsed_by", rule.get("collapsed_by"))) if v}
    return {"kind": kind, "proposed_by": proposer, "rule_proposed_by": rule.get("proposed_by") or {},
            "derivation_configuration": attribute.get("derivation_configuration"),
            "derived_from": derived_from or None,
            "pool_criterion": derived_from.get("pool_criterion"),
            "derivation_run": derived_from.get("derivation_run"),
            "task_field": derived_from.get("field"),
            "dimension": (pool_entry or {}).get("dimension"),
            "written_by_software": written_by_software or None}


def _verification_summary(claims: list[dict[str, Any]]) -> dict[str, Any]:
    """The three checks §11.1 wants reported apart, counted over a criterion's resolved claims."""
    resolved = [c for c in claims if c.get("resolved")]
    return {
        "quote_check": {
            "field": "claim.location.span_checked_against_source and claim.admission_reasons",
            "claims": len(resolved),
            "span_checked_against_source": sum(1 for c in resolved if c["quote_check"]["span_checked_against_source"]),
            "quote_verified": sum(1 for c in resolved if c["quote_check"]["quote_verified"]),
        },
        "numerical_consistency": {
            "field": "claim.admission_reasons",
            "value_in_quote": sum(1 for c in resolved if c["numerical_consistency"] == "value_in_quote"),
            "value_not_in_quote": sum(1 for c in resolved if c["numerical_consistency"] == "value_not_in_quote"),
            "not_recorded": sum(1 for c in resolved if c["numerical_consistency"] == "not_recorded"),
        },
        "semantic_support": {
            "field": "claim.verification_status",
            "states": {state: sum(1 for c in resolved if c["semantic_support"]["verification_status"] == state)
                       for state in sorted({c["semantic_support"]["verification_status"] for c in resolved})},
            "note": "a separate check from quote matching; `unverified` means it was never run, "
                    "not that the quotation failed to match",
        },
        "unresolved_claim_refs": sorted(c["claim_id"] for c in claims if not c.get("resolved")),
    }


def _use(rule_ref: str, attribute_ref: str, rule_sets: list[dict[str, Any]],
         board: dict[str, Any] | None) -> dict[str, Any]:
    """Whether this criterion scored, was held out, or was merged away, on the latest rule set."""
    latest = rule_sets[-1] if rule_sets else None
    if latest is None:
        return {"status": "no_confirmed_rule_set", "rule_set_ref": None, "reason": None}
    entry = next((e for e in latest["entries"] if e["rule_ref"] == rule_ref), None)
    deferred = next((d for d in (latest.get("deferred") or []) if d["rule_ref"] == rule_ref), None)
    collapsed = next((c for c in (latest.get("collapsed_away") or []) if c["rule_ref"] == rule_ref), None)
    if entry is not None:
        # A rule may both score and carry a deferral row: the deferral is per route, so a criterion
        # reading two curations and the literature scores on the curations while the reading is held
        # out (`criteria.DEFERRAL_SCOPES`). Keyed off the entry and not off `deferred[]`, because
        # keying it off the list reported a scoring rule as deferred, which is the opposite of what
        # happened; the held-out sources are named in the reason instead.
        status = "scoring"
        reason = None
        if deferred is not None and criteria.deferral_scope(deferred) == "route":
            reason = (f"scores on {', '.join(deferred.get('scores_on') or []) or 'no route'}; "
                      f"{', '.join(deferred.get('capabilities') or [deferred['capability']])} was held out of "
                      f"this run: {deferred.get('reason') or 'no reason recorded'}")
    elif deferred is not None:
        status = "deferred"
        reason = f"{deferred['capability']} was held out of this run: {deferred.get('reason') or 'no reason recorded'}"
    elif collapsed is not None:
        status = "collapsed_away"
        reason = (f"its attribute was merged into {collapsed['merged_into']} by {collapsed['collapse_id']}; "
                  f"{collapsed['scored_by']} scores the quantity")
    elif rule_ref in (latest.get("pending") or []):
        status, reason = "not_entered_pending_decision", "awaiting a decision on an open review item"
    else:
        status, reason = "not_entered", "no version of this rule entered the confirmed set"
    measured = (board or {}).get("measured_coverage", {}).get(attribute_ref)
    return {
        "status": status, "rule_set_ref": latest["rule_set_ref"], "reason": reason,
        "entry": entry, "deferral": deferred, "collapse": collapsed,
        # Which sources this criterion's values came from this run, and which were held out, from
        # the entry that scored it: a reader can tell a database-only value from one that also used
        # a reading without resolving the attribute's routes again.
        "scoring_routes": (entry or {}).get("scoring_routes"),
        "deferred_routes": (entry or {}).get("deferred_routes"),
        "deferral_scope": None if deferred is None else criteria.deferral_scope(deferred),
        "in_pending": rule_ref in (latest.get("pending") or []),
        "scores_while_disputed": rule_ref in (latest.get("pending_but_scoring") or []),
        "machine_adjudicated": rule_ref in (latest.get("machine_adjudicated") or []),
        "reads_collapsed_attribute": rule_ref in (latest.get("machine_collapsed") or []),
        "measured_coverage": None if measured is None else dict(measured, board=(board or {}).get("snapshot_id")),
    }


# --- the snapshot ----------------------------------------------------------------------------

def snapshot(core: Core, task_id: str, *, at_seq: int | None = None, with_board: bool = True) -> dict[str, Any]:
    """The canonical export payload: the registry, its support, its lifecycle and its counts.

    Deterministic for a fixed `at_seq`: it carries no export timestamp and no wall-clock value of
    its own, so two exports of one sequence hash identically.
    """
    pinned_core, seq = pinned(core, task_id, at_seq)
    context = task_mod.get(pinned_core, task_id)
    task_context_ref = f"{task_id}@v{context['version']}"
    registry = _registry(pinned_core, task_id)
    rule_sets = _rule_sets(pinned_core, task_id)
    folded = pool_mod.fold(pinned_core, task_id)
    trajectory = pool_mod.trajectory(pinned_core, task_id)
    collapses = collapse_mod.records(pinned_core, task_id)
    queue = review.items(pinned_core, [task_id])
    adjudications = adjudication.records(pinned_core, task_id)
    board = _board(pinned_core, task_id) if with_board else None

    latest_attributes = {r["base_id"]: r for r in registry.values() if r["kind"] == "attribute"}
    # Keyed by the attribute the rule *reads*, not by the rule's own base id: `attr_<slug>` and
    # `rule_<slug>` happen to share a slug today, but the link a rule actually declares is its
    # `attribute_ref`, and a rule whose attribute was revised points at the newer version.
    latest_rules = {r["record"]["attribute_ref"].split("@v")[0]: r for r in registry.values()
                    if r["kind"] == "rule" and r["record"].get("attribute_ref")}
    by_pool_criterion = {}
    for entry in folded.values():
        if entry.get("promoted_as"):
            by_pool_criterion[entry["promoted_as"]["attribute_ref"].split("@v")[0]] = entry

    locations = _claim_locations(pinned_core)
    wanted_claims = sorted({ref for record in latest_attributes.values()
                            for ref in _cited_refs(record["record"])})
    source_ids = sorted({pinned_core.artifacts.payload(locations[ref]["artifact_id"]).get("source_ref")
                         for ref in wanted_claims if ref in locations} - {None, ""})
    sources = _sources(pinned_core, source_ids)
    claim_cache = {ref: _claim_view(pinned_core, ref, locations, sources) for ref in wanted_claims}

    adjudication_by_rule = {}
    for record in adjudications:
        adjudication_by_rule.setdefault(record["rule_ref_after"], []).append(record)
        if record["rule_ref_before"] != record["rule_ref_after"]:
            adjudication_by_rule.setdefault(record["rule_ref_before"], []).append(record)

    cards = [_card(pinned_core, task_id, base_id, latest_attributes[base_id], latest_rules.get(base_id), registry,
                   by_pool_criterion.get(base_id), rule_sets, queue, adjudication_by_rule, collapses, board,
                   claim_cache, task_context_ref)
             for base_id in sorted(latest_attributes)]

    lifecycle = _lifecycle(folded, collapses, registry, rule_sets)
    counts = _counts(cards, folded, trajectory, registry, rule_sets, collapses, queue, adjudications, lifecycle)
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "export_kind": "historical_baseline",
        "baseline_label": BASELINE_LABEL,
        "baseline_statement": BASELINE_STATEMENT,
        "journal_position": {"task_stream": task_id, "pinned_seq": seq},
        "task": {
            "task_context_ref": task_context_ref, "objective_text": context["objective_text"],
            "mode": context.get("mode"), "group_id": context.get("group_id"),
            "objective_provenance": context.get("objective_provenance"),
            "constraints": context.get("constraints"), "scope_entities": context.get("scope_entities"),
            "evaluation_scope": context.get("evaluation_scope"),
            "human_review_requirements": context.get("human_review_requirements"),
            "candidate_universe": {k: v for k, v in (context.get("candidate_universe") or {}).items()
                                   if k != "members"},
            "case_source_documents": context.get("case_source_documents"),
            "seed_candidates": context.get("seed_candidates"),
        },
        "rule_sets": [_rule_set_view(record) for record in rule_sets],
        "latest_rule_set_ref": rule_sets[-1]["rule_set_ref"] if rule_sets else None,
        "board": board,
        "criteria": cards,
        "recovery_comparison_set": _recovery_comparison_set(cards, lifecycle),
        "lifecycle": lifecycle,
        "derivation_trajectory": trajectory,
        "collapses": collapses,
        "adjudications": adjudications,
        "review_queue": [queue[item_id] for item_id in sorted(queue)],
        "counts": counts,
        "withheld": {"artifact_kinds": list(WITHHELD_ARTIFACT_KINDS),
                     "reason": "private model traces and whole provider responses are not published; "
                               "quoted spans, locators, source identities and document hashes are"},
    }


def _cited_refs(attribute: dict[str, Any]) -> list[str]:
    """Every claim a registered attribute cites, from both fields that can name one.

    WHY both: a pool item cites in `supporting_claim_ids` and the attribute the promotion writes
    cites in `supporting_claim_refs`, and a transform bound names its own claims in
    `value_transform.source_refs`. Reading one field alone drops the support of the two bounds that
    are the only source-stated numbers in this registry.
    """
    refs = set(attribute.get("supporting_claim_refs") or []) | set(attribute.get("supporting_claim_ids") or [])
    refs |= set((attribute.get("value_transform") or {}).get("source_refs") or [])
    return sorted(refs)


def _card(core: Core, task_id: str, base_id: str, attribute_entry: dict[str, Any],
          rule_entry: dict[str, Any] | None, registry: dict[str, dict[str, Any]],
          pool_entry: dict[str, Any] | None, rule_sets: list[dict[str, Any]],
          queue: dict[str, dict[str, Any]], adjudication_by_rule: dict[str, list[dict[str, Any]]],
          collapses: list[dict[str, Any]], board: dict[str, Any] | None,
          claim_cache: dict[str, dict[str, Any]], task_context_ref: str) -> dict[str, Any]:
    attribute = attribute_entry["record"]
    rule = (rule_entry or {}).get("record") or {}
    attribute_ref, rule_ref = attribute_entry["ref"], (rule_entry or {}).get("ref")
    item = (pool_entry or {}).get("item") or {}
    claims = [claim_cache[ref] for ref in _cited_refs(attribute)]
    by_polarity: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        by_polarity.setdefault(claim.get("polarity") or "unresolved", []).append(claim)
    related_items = [queue[k] for k in sorted(queue)
                     if queue[k]["subject"].get("id") in {rule_ref, attribute_ref}
                     or queue[k]["subject"].get("attribute_ref") == attribute_ref]
    merged = next((c for c in collapses for m in c["superseded"] if m["attribute_ref"] == attribute_ref), None)
    survived = next((c for c in collapses if c["surviving"]["attribute_ref_after"] == attribute_ref), None)
    parameter_support = _parameter_support(attribute, rule)
    return {
        "criterion_key": base_id,
        "name": attribute.get("name"),
        "matching_facets": _matching_facets(attribute, rule, parameter_support),
        "identity": {
            "task_context_ref": task_context_ref,
            "attribute_ref": attribute_ref, "attribute_id": attribute.get("attribute_id"),
            "attribute_version": attribute.get("version"),
            "rule_ref": rule_ref, "rule_id": rule.get("rule_id"), "rule_version": rule.get("version"),
            "attribute_versions": sorted(r["ref"] for r in registry.values()
                                         if r["kind"] == "attribute" and r["base_id"] == base_id),
            "rule_versions": sorted(r["ref"] for r in registry.values()
                                    if r["kind"] == "rule" and r["base_id"] == rule.get("rule_id")),
            "supersedes": attribute.get("supersedes"),
            "attribute_artifact": {"artifact_id": attribute_entry["artifact_id"],
                                   "artifact_sha256": _artifact_hash(core, attribute_entry["artifact_id"])},
            "rule_artifact": None if rule_entry is None else {
                "artifact_id": rule_entry["artifact_id"],
                "artifact_sha256": _artifact_hash(core, rule_entry["artifact_id"])},
        },
        "origin": _origin(attribute, rule, item),
        "meaning": {
            "definition": attribute.get("definition"), "rationale": attribute.get("rationale"),
            "measurement_kind": attribute.get("measurement_kind"), "unit": attribute.get("unit"),
            "direction": attribute.get("direction"), "aggregation": attribute.get("aggregation"),
            "acceptable_value_sources": attribute.get("acceptable_value_sources"),
            "acceptable_determination_bases": attribute.get("acceptable_determination_bases"),
            "determination_basis_precedence": attribute.get(criteria.PRECEDENCE_FIELD),
            "applicability": {"applies_to_result_kind": rule.get("applies_to_result_kind"),
                              "on_inapplicable": rule.get("on_inapplicable"),
                              "stated_in_definition_only": attribute.get("applicability") is None},
            "expected_change": item.get("expected_change") or rule.get("expected_change"),
            "falsification_test": item.get("falsification_test") or rule.get("falsification_test"),
        },
        "computation": {
            "value_transform": attribute.get("value_transform"),
            "transform_declared": attribute.get("value_transform") is not None,
            "family_reduction": _family_reduction(attribute, item.get("consolidation")),
            "evidence_routes": [_route_view(r) for r in criteria.evidence_routes(attribute)],
            "route_count": len(criteria.evidence_routes(attribute)),
            "literature_bound": criteria.is_literature_bound(attribute),
            "evidence_key_sha256": criteria.evidence_key(attribute),
        },
        "rule": {
            "rule_kind": rule.get("rule_kind"), "predicate_form": rule.get("predicate_form"),
            "cutoff": rule.get("cutoff"),
            "cutoff_state": "present" if rule.get("cutoff") else "explicitly_absent",
            "cutoff_basis": rule.get("cutoff_basis"),
            "on_missing": rule.get("on_missing"), "on_inapplicable": rule.get("on_inapplicable"),
            "on_conflict": rule.get("on_conflict"),
            "weight": {"weight_vector_entry": ((rule_sets[-1]["ordering_method"].get("weight_vector") or {}).get(rule_ref)
                                               if rule_sets else None),
                       "weighting": "unweighted mean over observed contributions; the confirmed "
                                    "ordering method declares an empty weight vector"},
            "decision_group": None,
        },
        "support": {
            "supporting_claim_refs": _cited_refs(attribute),
            "parameter_support": parameter_support,
            "claims_by_polarity": {polarity: by_polarity.get(polarity, []) for polarity in sorted(by_polarity)},
            "counts": {polarity: len(found) for polarity, found in sorted(by_polarity.items())},
            "experiment_groups": "not_recorded; these are literature-extracted claims and the store "
                                 "holds no underlying-experiment identity for them",
        },
        "verification": _verification_summary(claims),
        "authority": {
            # The authority table reads the rule, the attribute and the bounds inside its transform
            # (`criteria.authority_requirements`), so a number moved out of a cutoff keeps the
            # decision it owes. What it returns is published rather than a yes/no, because a card
            # saying only "needs an expert" does not say which parameter is why.
            "authority_required": criteria.authority_requirements(rule, attribute) if rule else None,
            "expert_decisions": [i["decision_id"] for i in related_items if i.get("decision_id")],
            "machine_adjudications": [
                {"adjudication_id": a["adjudication_id"], "route": a["route"], "resolution": a["resolution"],
                 "basis": a["basis"], "reason_text": a["reason_text"], "approval_kind": a["approval_kind"],
                 "confirmed_by_a_person": a["confirmed_by_a_person"], "independence": a.get("independence"),
                 "cites": a.get("cites"), "cited_claim_ids": a.get("cited_claim_ids")}
                for a in adjudication_by_rule.get(rule_ref, [])],
            "open_review_items": [
                {"item_id": i["item_id"], "state": i["state"], "why_expert_required": i["why_expert_required"],
                 "blocking": i.get("blocking"), "created_at": i.get("created_at"),
                 "inspection_bundle": i.get("inspection_bundle")}
                for i in related_items if i["state"] in ("open", "in_review")],
            "unresolved_disputes": [
                {"item_id": i["item_id"], "why_expert_required": i["why_expert_required"],
                 "inspection_bundle": i.get("inspection_bundle")}
                for i in related_items if i["state"] in ("open", "in_review")
                and "disagree" in (i["why_expert_required"] or "")],
            "exposure": {
                "derivation_configuration": attribute.get("derivation_configuration"),
                "historical_list_exposure": sorted({i.get("historical_list_exposure") for i in related_items
                                                    if i.get("historical_list_exposure")}) or
                                            ["no expert decision exists for this criterion"],
                "note": "the sealed eleven-CQA list was not in the derivation agents' context; "
                        "the known reference compound was disclosed, which is a separate exposure",
            },
        },
        "lifecycle": {
            "pool_state": (pool_entry or {}).get("state"),
            "pool_criterion_id": (pool_entry or {}).get("criterion_id"),
            "pool_version": (pool_entry or {}).get("version"),
            "parents": (pool_entry or {}).get("parents") or [],
            "children": (pool_entry or {}).get("children") or [],
            "refinement_history": (pool_entry or {}).get("history") or [],
            "critic_findings": item.get("critic_findings") or [],
            "validator_problems": item.get("validator_problems") or [],
            "dissent_recorded_on_rule": rule.get("dissent") or [],
            # What a consolidated criterion stands for: the specific endpoints it subsumed, the property
            # claimed to be shared across them, and the aggregation that reduces them to one number. A
            # reviewer who cannot read that list cannot object to the abstraction, which is the whole
            # difference between a consolidation and information loss, so it travels with the card rather
            # than only in the pool's change records.
            "consolidation": item.get("consolidation"),
            "merged_away": None if merged is None else {
                "collapse_id": merged["collapse_id"], "into": merged["surviving"]["attribute_ref_after"],
                "reason_text": merged["reason_text"], "withdrawn": merged["withdrawn"]},
            "survived_collapse": None if survived is None else {
                "collapse_id": survived["collapse_id"],
                "absorbed": [m["attribute_ref"] for m in survived["superseded"]],
                "routes_before": survived["surviving"]["routes_before"],
                "routes_after": survived["surviving"]["routes_after"],
                "reason_text": survived["reason_text"], "withdrawn": survived["withdrawn"]},
        },
        "use": _use(rule_ref, attribute_ref, rule_sets, board),
    }


def _recovery_comparison_set(cards: list[dict[str, Any]], lifecycle: dict[str, Any]) -> dict[str, Any]:
    """Which of the registered criteria form the derived set a recovery mapping compares against.

    WHY the set is not simply the 40 cards: five of them measure a quantity another card already
    measures -- a collapse merged their attributes away because each required receptor had been
    registered twice, once per curating database -- and a mapping that counted both would report two
    derived criteria recovering one historical meaning. Repeated variants must not inflate recovery
    (handoff §12.2), so they are named here as excluded, with the survivor that carries the quantity.

    The split by origin is here for the same reason in the other direction: six of these criteria
    restate a requirement the task supplied, and a recovery figure that does not separate them would
    describe a supplied requirement as an independently derived one (§12.2, §2.4).
    """
    included = [c for c in cards if c["use"]["status"] not in ("collapsed_away",)]
    excluded = [{"attribute_ref": c["identity"]["attribute_ref"], "rule_ref": c["identity"]["rule_ref"],
                 "name": c["name"], "reason": c["use"]["reason"],
                 "same_quantity_as": (c["lifecycle"]["merged_away"] or {}).get("into")}
                for c in cards if c["use"]["status"] == "collapsed_away"]
    origins: dict[str, list[str]] = {}
    for card in included:
        origins.setdefault(card["origin"]["kind"], []).append(card["identity"]["attribute_ref"])
    return {
        "statement": "The derived set for a recovery mapping: every registered criterion whose "
                     "quantity is not already carried by another registered criterion. Pruned pool "
                     "items are in the lifecycle section and are not derived criteria. Nothing here "
                     "is shaped by any knowledge of the sealed historical list.",
        "included": [{"attribute_ref": c["identity"]["attribute_ref"], "rule_ref": c["identity"]["rule_ref"],
                      "name": c["name"], "origin": c["origin"]["kind"], "status": c["use"]["status"],
                      "measurement_identity_sha256": c["matching_facets"]["measurement_identity_sha256"]}
                     for c in included],
        "included_count": len(included),
        "excluded_as_a_repeated_variant": excluded,
        "excluded_as_pruned_pool_items": lifecycle["pool_items_not_promoted_count"],
        "by_origin": {kind: {"count": len(refs), "attribute_refs": sorted(refs)}
                      for kind, refs in sorted(origins.items())},
        "duplicate_measurement_identities": sorted(
            identity for identity in {c["matching_facets"]["measurement_identity_sha256"] for c in included}
            if sum(1 for c in included
                   if c["matching_facets"]["measurement_identity_sha256"] == identity) > 1),
    }


def _held_out_whole(record: dict[str, Any]) -> list[dict[str, Any]]:
    """The `deferred[]` rows that kept a rule out of the set entirely.

    WHY counted apart from the route-level rows: every count of "deferred" in this export means
    "registered rules that did not enter the latest set", and the reconciliation adds it to the
    scoring rules to reach the registered total. A route-level row is a rule that *did* enter, so
    counting it there would both overstate what was held out and double-count that rule.
    """
    return [row for row in (record.get("deferred") or []) if criteria.deferral_scope(row) == "rule"]


def _scoring_with_a_route_held_out(record: dict[str, Any]) -> list[dict[str, Any]]:
    """The `deferred[]` rows of rules that entered the set with some of their routes held out."""
    return [row for row in (record.get("deferred") or []) if criteria.deferral_scope(row) == "route"]


def _rule_set_view(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_set_ref": record["rule_set_ref"], "acceptance_label": record["acceptance_label"],
        "acceptance_reasons": record.get("acceptance_reasons") or [],
        "preregistration_ref": record.get("preregistration_ref"),
        "coverage_floor": record.get("coverage_floor"), "ordering_method": record.get("ordering_method"),
        "evidence_admission_predicate_hash": record.get("evidence_admission_predicate_hash"),
        "entries": record["entries"],
        "pending": record.get("pending") or [], "pending_but_scoring": record.get("pending_but_scoring") or [],
        "machine_adjudicated": record.get("machine_adjudicated") or [],
        "machine_collapsed": record.get("machine_collapsed") or [],
        "collapsed_away": record.get("collapsed_away") or [], "deferred": record.get("deferred") or [],
        "deferred_capabilities": record.get("deferred_capabilities") or [],
        "counts": {"scoring": len(record["entries"]), "pending": len(record.get("pending") or []),
                   "deferred": len(_held_out_whole(record)),
                   "scoring_with_a_route_held_out": len(_scoring_with_a_route_held_out(record)),
                   "collapsed_away": len(record.get("collapsed_away") or [])},
    }


def _lifecycle(folded: dict[str, dict[str, Any]], collapses: list[dict[str, Any]],
               registry: dict[str, dict[str, Any]], rule_sets: list[dict[str, Any]]) -> dict[str, Any]:
    """What was pruned, so the survivors can be read against it (handoff §11.1).

    Kept apart from the cards on purpose: a reviewer asking whether 34 survivors are a pool's
    output or its entire content cannot answer that from the survivors.
    """
    pruned: dict[str, list[dict[str, Any]]] = {}
    for criterion_id in sorted(folded):
        entry = folded[criterion_id]
        if entry["state"] == "promoted" or entry.get("promoted_as"):
            continue
        item = entry.get("item") or {}
        attribute = item.get("attribute") or {}
        last = (entry.get("history") or [{}])[-1]
        pruned.setdefault(entry["state"] or "unknown", []).append({
            "criterion_id": criterion_id, "final_version": entry["version"], "state": entry["state"],
            "dimension": item.get("dimension"), "name": attribute.get("name"),
            "definition": attribute.get("definition"), "unit": attribute.get("unit"),
            "direction": attribute.get("direction"), "rule": item.get("rule"),
            "left_at": {k: last.get(k) for k in ("stage", "iteration", "round_run_id", "operation")},
            "reason_kind": last.get("reason_kind"), "reason_text": last.get("reason_text"),
            "critic_findings": item.get("critic_findings") or [],
            "validator_problems": item.get("validator_problems") or [],
            "supporting_claim_ids": item.get("supporting_claim_ids") or [],
            "parents": entry.get("parents") or [], "children": entry.get("children") or [],
            "history": entry.get("history") or [],
        })
    latest = rule_sets[-1] if rule_sets else {}
    merged_away = []
    for record in collapses:
        for member in record["superseded"]:
            held_out = next((c for c in (latest.get("collapsed_away") or [])
                             if c["attribute_ref"] == member["attribute_ref"]), None)
            merged_away.append({
                "attribute_ref": member["attribute_ref"], "rule_ref": member["rule_ref"],
                "name": member.get("name"), "routes": member.get("routes"),
                "merged_into": record["surviving"]["attribute_ref_after"],
                "scored_by": record["surviving"]["rule_ref_after"],
                "collapse_id": record["collapse_id"], "collapse_withdrawn": record["withdrawn"],
                "reason_text": record["reason_text"], "approval_kind": record["approval_kind"],
                "confirmed_by_a_person": record["confirmed_by_a_person"],
                "held_out_of_latest_rule_set": held_out is not None,
                "definition_text": record.get("definition_text"),
                "definition_shares_words_with_one_route": record.get("definition_shares_words_with_one_route"),
            })
    superseded_versions = sorted(
        {r["record"].get("supersedes") for r in registry.values() if r["record"].get("supersedes")})
    return {
        "statement": "Items that did not reach the registry, or reached it and were merged away. "
                     "None of them scores on any confirmed rule set.",
        "pool_items_not_promoted": pruned,
        "pool_items_not_promoted_count": sum(len(found) for found in pruned.values()),
        "merged_away_attributes": merged_away,
        "superseded_registry_versions": superseded_versions,
    }


def _counts(cards: list[dict[str, Any]], folded: dict[str, dict[str, Any]], trajectory: list[dict[str, Any]],
            registry: dict[str, dict[str, Any]], rule_sets: list[dict[str, Any]],
            collapses: list[dict[str, Any]], queue: dict[str, dict[str, Any]],
            adjudications: list[dict[str, Any]], lifecycle: dict[str, Any]) -> dict[str, Any]:
    """Each quoted number with the population it counts, measured from the pinned snapshot."""
    proposals = sum(step["added"] for step in trajectory)
    promoted = [c for c in cards if (c["lifecycle"]["pool_state"] == "promoted")]
    templates = [c for c in cards if c["origin"]["kind"] in ("adapter_template", "task_mandated_template")]
    latest = rule_sets[-1] if rule_sets else {}
    bound = [c for c in cards if any(p["basis"] == "source_stated_value" and p["claim_refs"]
                                     for p in c["support"]["parameter_support"])]
    task_cutoff = [c for c in cards if c["rule"]["cutoff"] and c["rule"]["cutoff_basis"] == "task_constraint"]
    no_cutoff = [c for c in cards if c["rule"]["cutoff_state"] == "explicitly_absent"]
    return {
        "proposals_added_to_pool": {
            "value": proposals,
            "counts": "pool lineages created by the propose stage, over every round in this task"},
        "pool_lineages": {"value": len(folded), "counts": "distinct `cri_` lineages the pool ever held"},
        "promoted_pool_items": {
            "value": sum(1 for e in folded.values() if e["state"] == "promoted"),
            "counts": "pool lineages whose final state is `promoted`; each wrote one attribute and "
                      "one rule into the registry"},
        "pruned_pool_items": {"value": lifecycle["pool_items_not_promoted_count"],
                              "counts": "pool lineages that never reached the registry, by final state: "
                                        + ", ".join(f"{state} {len(found)}" for state, found
                                                    in sorted(lifecycle["pool_items_not_promoted"].items()))},
        "registered_criteria": {
            "value": len(cards),
            "counts": "distinct attribute ids in the registry, each paired with one rule id; this is "
                      "the promoted pool items plus the criteria the adapter templates registered "
                      "without entering the pool"},
        "registered_from_pool": {"value": len(promoted),
                                 "counts": "registered criteria whose attribute a pool promotion wrote"},
        "registered_from_templates": {
            "value": len(templates),
            "counts": "registered criteria an adapter template wrote directly, bypassing the pool"},
        "registry_versions": {
            "value": {"attribute": sum(1 for r in registry.values() if r["kind"] == "attribute"),
                      "rule": sum(1 for r in registry.values() if r["kind"] == "rule")},
            "counts": "attribute and rule *versions*, not criteria; a second version is a revision "
                      "of one criterion, not another criterion"},
        "rule_sets": [{"rule_set_ref": r["rule_set_ref"], "scoring": len(r["entries"]),
                       "pending": len(r.get("pending") or []), "deferred": len(_held_out_whole(r)),
                       "scoring_with_a_route_held_out": len(_scoring_with_a_route_held_out(r)),
                       "collapsed_away": len(r.get("collapsed_away") or []),
                       "acceptance_label": r["acceptance_label"]} for r in rule_sets],
        "scoring_now": {"value": len(latest.get("entries") or []),
                        "counts": f"rules in {latest.get('rule_set_ref')}, the latest confirmed set"},
        "deferred_now": {"value": len(_held_out_whole(latest)),
                         "counts": "registered rules held out of the latest set entirely, because "
                                   "every evidence route they declare needs a capability that was "
                                   "not run"},
        "scoring_with_a_route_held_out_now": {
            "value": len(_scoring_with_a_route_held_out(latest)),
            "counts": "rules in the latest set that score on some of their evidence routes while "
                      "others are held out of this run; they are counted in `scoring_now`, never "
                      "in `deferred_now`"},
        "collapsed_away_now": {"value": len(latest.get("collapsed_away") or []),
                               "counts": "registered rules whose attribute a collapse merged away"},
        "collapses": {"value": {"applied": len(collapses),
                                "withdrawn": sum(1 for c in collapses if c["withdrawn"])},
                      "counts": "collapse records; each merged several registrations of one quantity "
                                "into one attribute reading every route"},
        "review_queue": {"value": {state: sum(1 for i in queue.values() if i["state"] == state)
                                   for state in sorted({i["state"] for i in queue.values()})},
                         "counts": "review items raised against this task, by state"},
        "unresolved_disputes": {
            "value": sum(1 for i in queue.values() if i["state"] in ("open", "in_review")
                         and "disagree" in (i["why_expert_required"] or "")),
            "counts": "open review items raised because a proposer and a critic still disagreed "
                      "after one revision"},
        "machine_adjudications": {"value": len(adjudications),
                                  "counts": "items resolved by software with no person; recorded as "
                                            "`agent_verdict`, never as an expert approval"},
        "expert_decisions": {"value": sum(1 for i in queue.values() if i.get("decision_id")),
                             "counts": "`hd_` records; an expert decision needs a person at a terminal"},
        "bounds": {
            "value": {"source_stated_with_claims": len(bound), "task_constraint_cutoff": len(task_cutoff),
                      "no_cutoff_evidence_insufficient": len(no_cutoff)},
            "counts": "registered criteria carrying a numeric bound whose basis is a cited claim, a "
                      "bound restating a task constraint, and no bound at all"},
        "matching_facet_gaps": {
            "value": {facet: sum(1 for c in cards if any(g.startswith(facet) for g in c["matching_facets"]["gaps"]))
                      for facet in ("operational_quantity", "applicability", "decision_semantics", "threshold")},
            "counts": "registered criteria whose records do not answer one of the four recovery-rubric "
                      "facets from fields alone; the cards name the absence per criterion"},
        "comparable_from_fields": {
            "value": sum(1 for c in cards if c["matching_facets"]["comparable_from_fields"]),
            "counts": "registered criteria all four rubric facets can be read off without reading "
                      "prose; the applicability gap is schema-wide, so this is zero while no "
                      "attribute records applicability as a field"},
    }


# --- rendering -------------------------------------------------------------------------------

def _fence(text: Any) -> str:
    return "—" if text in (None, "", [], {}) else str(text)


def _inline(value: Any) -> str:
    if value in (None, "", [], {}):
        return "—"
    if isinstance(value, (dict, list)):
        return f"`{json.dumps(value, sort_keys=True, ensure_ascii=False)}`"
    return f"`{value}`"


def _claim_lines(claim: dict[str, Any]) -> list[str]:
    """One claim in five lines: the quotation, where it is, what checked it, and how it was admitted.

    WHY five and not fourteen: a criterion citing nine claims renders nine of these, and the same
    claim is cited by several criteria, so a line per field put 250 KB of repeated labels into a
    document whose purpose is that a person reads it. Every field §11.1 asks for is still here; the
    publication metadata of each source is tabulated once in the sources appendix instead of being
    reprinted under every criterion that cites it.
    """
    if not claim.get("resolved"):
        return [f"- **{claim['claim_id']}** — {claim['note']}"]
    source = claim.get("source") or {}
    location, checks = claim["location"], claim["quote_check"]
    section = " / ".join(location.get("section_path") or []) or "—"
    return [
        f"- **{claim['claim_id']}** · `{claim.get('polarity')}` · evidence `{claim.get('evidence_kind')}` · "
        f"determination `{claim.get('determination_basis')}` · value {_inline(claim['value'])}",
        f"  > {(claim.get('quoted_span') or '— no span recorded').strip()}",
        f"  - as recorded ({_fence(claim.get('statement_marker'))}): {_fence(claim.get('statement'))}",
        f"  - in `{source.get('source_id')}` at `{location.get('location_kind')}` "
        f"`{location.get('locator_value')}`, section {section}; document `"
        f"{(claim.get('document') or {}).get('artifact_id')}` "
        f"sha256 `{(claim.get('document') or {}).get('artifact_sha256')}`; claim `{claim['artifact_id']}` "
        f"sha256 `{claim['artifact_sha256']}` on `{claim['recorded_on']['stream_id']}` "
        f"seq {claim['recorded_on']['seq']}",
        f"  - checks — quote: span_checked_against_source "
        f"`{checks['span_checked_against_source']}`, quote_verified `{checks['quote_verified']}` · "
        f"numerical: `{claim['numerical_consistency']}` · semantic: "
        f"`{claim['semantic_support']['verification_status']}`",
        f"  - scope ({_fence((claim.get('scope') or {}).get('marker'))}) "
        f"{_fence((claim.get('scope') or {}).get('population_or_system'))} · scope_match "
        f"`{claim.get('scope_match')}` · read `{claim.get('reading_depth')}` · admitted "
        f"`{claim['admission']['state']}` {_inline(claim['admission']['reasons'])} · by "
        f"`{(claim.get('extracted_by') or {}).get('id')}`",
    ]


def _finding_lines(label: str, found: list[dict[str, Any]]) -> list[str]:
    """Critic, validator and dissent findings as sentences rather than JSON.

    WHY not `_inline`: these are the longest records on a card -- 36 KB of them across the registry
    -- and a reviewer deciding whether a criticism was answered has to read the finding, which a
    one-line JSON dump of five keys makes the hardest thing on the page to read.

    A validator problem is recorded as a sentence and a critic finding as a record, so both shapes
    are rendered rather than one being coerced into the other.
    """
    if not found:
        return [f"- {label}: —"]
    lines = [f"- {label} ({len(found)}):"]
    for finding in found:
        if not isinstance(finding, dict):
            lines.append(f"  - {finding}")
            continue
        lines.append(f"  - `{finding.get('check')}` on {_fence(finding.get('referent'))} · "
                     f"severity `{finding.get('severity')}` · verdict `{finding.get('verdict')}`: "
                     f"{_fence(finding.get('finding'))}")
    return lines


def _sources_markdown(payload: dict[str, Any]) -> list[str]:
    """Every source behind a quotation, once, with the identity and licence an audit needs."""
    seen: dict[str, dict[str, Any]] = {}
    for card in payload["criteria"]:
        for claims in card["support"]["claims_by_polarity"].values():
            for claim in claims:
                source = claim.get("source")
                if source and source["source_id"] not in seen:
                    seen[source["source_id"]] = source
    lines = ["", "## Sources behind the quotations", "",
             f"{len(seen)} sources, each cited by one or more claims above.", "",
             "| source id | title | container | issued | status | access | licence | identifiers | artifact sha256 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for source_id in sorted(seen):
        source = seen[source_id]
        identifiers = ", ".join(f"{i['scheme']}:{i['value']}" for i in (source.get("identifiers") or [])) or "—"
        lines.append(
            f"| `{source_id}` | {_fence(source.get('title'))} | {_fence(source.get('container'))} | "
            f"{_fence(source.get('issued_date'))} | `{source.get('source_status')}` | "
            f"`{source.get('access_state')}` | {_fence(source.get('license'))} | {identifiers} | "
            f"`{source.get('artifact_sha256')}` |")
    return lines + [""]


def _family_reduction(attribute: dict[str, Any], consolidation: dict[str, Any] | None) -> dict[str, Any] | None:
    """What a consolidated criterion computes, re-derived from the attribute that will be executed.

    WHY it is re-derived here rather than copied from the pool's consolidation record: the record is what the
    adjudicator declared, the attribute's `aggregation` is what `assess_cell` runs, and only the second one
    reaches the assessor. The merge gate writes the first into the second so they cannot part, but a later
    attribute version can be registered by any other route, so the card states the aggregation that will run
    and, when it is not the one the declared family reduction asks for, says so in the same sentence. A card
    that printed only the declaration would be reproducing the defect this field had when it was added: a
    reduction recorded and never executed.
    """
    if not consolidation:
        return None
    family = str(consolidation.get("family_aggregation") or "")
    direction = attribute.get("direction")
    executes_as, problem = assessor.family_aggregation_execution(family, direction)
    runs = attribute.get("aggregation") or "consensus"
    agrees = problem is None and executes_as == runs
    if agrees:
        statement = (f"the family reduction `{family}` over a `{direction}` attribute is the `{runs}` of the "
                     f"cell's pooled claims, which is the aggregation the attribute declares: that is what "
                     f"will be computed")
    elif problem:
        statement = (f"the family reduction `{family}` is not executable here ({problem}); the attribute's "
                     f"`{runs}` of the cell's pooled claims is what will be computed")
    else:
        statement = (f"the family reduction `{family}` over a `{direction}` attribute would be the "
                     f"`{executes_as}` of the cell's pooled claims, but the attribute declares `{runs}`, "
                     f"which is what will be computed: the declaration and the execution disagree")
    return {"family_aggregation": family, "executes_as_aggregation": executes_as,
            "attribute_aggregation": runs, "direction": direction, "agrees_with_attribute": agrees,
            "statement": statement}


def _consolidation_lines(consolidation: dict[str, Any] | None) -> list[str]:
    """The family a consolidated criterion replaced, named endpoint by endpoint so that a reviewer can say
    one of them did not belong in it."""
    if not consolidation:
        return []
    subsumes = consolidation.get("subsumes") or []
    return [f"- consolidates {len(subsumes)} specific endpoints, reduced by "
            f"`{consolidation.get('family_aggregation')}`, on the shared property "
            f"{_fence(consolidation.get('shared_property'))}:"] + \
           [f"  - `{s.get('criterion_id')}@v{s.get('version')}` {s.get('name')}" for s in subsumes]


def _card_markdown(card: dict[str, Any], index: int) -> list[str]:
    identity, meaning, rule = card["identity"], card["meaning"], card["rule"]
    origin, support, use = card["origin"], card["support"], card["use"]
    verification, lifecycle, authority = card["verification"], card["lifecycle"], card["authority"]
    computation = card["computation"]
    lines = [
        f"### {index}. {card['name']}",
        "",
        f"- **attribute** `{identity['attribute_ref']}` · **rule** `{identity['rule_ref']}` · "
        f"**task** `{identity['task_context_ref']}`",
        f"- **all versions**: attribute {_inline(identity['attribute_versions'])}, "
        f"rule {_inline(identity['rule_versions'])}; supersedes {_inline(identity['supersedes'])}",
        f"- **record hashes**: attribute `{identity['attribute_artifact']['artifact_sha256']}`, "
        f"rule `{(identity['rule_artifact'] or {}).get('artifact_sha256')}`",
        f"- **origin**: `{origin['kind']}` · proposed by {_inline(origin['proposed_by'])} · "
        f"derivation configuration `{origin['derivation_configuration']}`",
        f"- **derived from**: {_inline(origin['derived_from'])} · dimension {_inline(origin['dimension'])}",
        f"- **written by software**: {_inline(origin['written_by_software'])}",
        "",
        "**Recovery-comparison facets** (same operational quantity · applicability · decision "
        "semantics · threshold)",
        "",
    ]
    facets = card["matching_facets"]
    quantity, semantics, applicability, threshold = (facets["operational_quantity"],
                                                     facets["decision_semantics"],
                                                     facets["applicability"], facets["threshold"])
    lines += [
        f"- **quantity**: {_fence(quantity['quantity_name'])} · subject "
        f"{_inline(quantity['subject_parameters'])} · unit {_inline(quantity['unit'])} · "
        f"`{quantity['measurement_kind']}` · aggregated by `{quantity['aggregation']}` · transform "
        f"{_inline(quantity['transform'])}",
        f"  - read from {_inline(quantity['capabilities'])} asking {_inline(quantity['question_kinds'])}; "
        f"evidence kinds {_inline(quantity['accepted_evidence_kinds'])}; determination bases "
        f"{_inline(quantity['accepted_determination_bases'])}",
        f"  - measurement identity `{facets['measurement_identity_sha256']}`",
        f"- **applicability**: {applicability['population']} · result kind "
        f"`{applicability['applies_to_result_kind']}` · on inapplicable "
        f"`{applicability['on_inapplicable']}` · condition field "
        f"{_inline(applicability['conditions_field'])}",
        f"- **decision semantics**: role `{semantics['decision_role']}` (`{semantics['rule_kind']}`) · "
        f"predicate form `{semantics['predicate_form']}` · direction `{semantics['direction']}`",
        f"  - predicate: {semantics['predicate']}",
        f"  - on missing `{semantics['on_missing']}` · on conflict `{semantics['on_conflict']}` · "
        f"decision identity `{facets['decision_identity_sha256']}`",
        f"- **threshold**: `{threshold['state']}`"
        + (f" — `{threshold['comparator']} {threshold['value']}"
           + (f" {threshold['unit']}`" if threshold["unit"] else "`")
           if threshold["state"] == "present" else "")
        + f" · basis `{threshold['basis']}` · cutoff support "
          f"{_inline(threshold['cutoff_support_claim_refs'])}",
        f"- **comparable from fields alone**: {_inline(facets['comparable_from_fields'])}",
    ]
    for gap in facets["gaps"]:
        lines.append(f"  - gap: {gap}")
    lines += [
        "",
        "**Operational definition**",
        "",
        f"> {_fence(meaning['definition'])}",
        "",
        f"- **unit** {_inline(meaning['unit'])} · **measurement kind** `{meaning['measurement_kind']}` · "
        f"**direction** `{meaning['direction']}` · **aggregation** `{meaning['aggregation']}`",
        f"- **accepted evidence kinds** {_inline(meaning['acceptable_value_sources'])} · "
        f"**accepted determination bases** {_inline(meaning['acceptable_determination_bases'])}"
        + (f" · **basis precedence** {' > '.join(meaning['determination_basis_precedence'])}"
           f" (a lower-priority basis is used only where every higher one is silent, and the cell "
           f"reports the basis it used)" if meaning.get("determination_basis_precedence") else ""),
        f"- **applicability**: {_inline(meaning['applicability'])}",
        f"- **expected change**: {_fence(meaning['expected_change'])}",
        f"- **falsification test**: {_fence(meaning['falsification_test'])}",
        f"- **rationale**: {_fence(meaning['rationale'])}",
        "",
        "**Rule**",
        "",
        f"- **kind** `{rule['rule_kind']}` · **predicate form** `{rule['predicate_form']}` · "
        f"**cutoff** {_inline(rule['cutoff'])} (`{rule['cutoff_state']}`) · "
        f"**cutoff basis** `{rule['cutoff_basis']}`",
        f"- **on missing** `{rule['on_missing']}` · **on inapplicable** `{rule['on_inapplicable']}` · "
        f"**on conflict** `{rule['on_conflict']}`",
        f"- **weight**: {_inline(rule['weight']['weight_vector_entry'])} — {rule['weight']['weighting']}",
        "",
        "**Transform and computation**",
        "",
        f"- **value transform**: {_inline(computation['value_transform'])}",
        f"- **evidence key** `{computation['evidence_key_sha256']}` · "
        f"{computation['route_count']} route(s) · literature-bound {_inline(computation['literature_bound'])}",
    ]
    if computation["family_reduction"]:
        lines.append(f"- **family reduction**: {computation['family_reduction']['statement']}")
    for route in computation["evidence_routes"]:
        lines.append(f"  - route `{route['capability']}` / `{route['question_kind']}` · "
                     f"subject {_inline(route['subject_parameters'])} · "
                     f"retrieval {_inline(route['retrieval_parameters'])} · "
                     f"identifier scheme {_inline(route['identifier_scheme'])}")
    lines += ["", "**Parameter support**", ""]
    if not support["parameter_support"]:
        lines.append("- no executable scientific parameter: the rule carries no cutoff and the "
                     "attribute declares no transform")
    for parameter in support["parameter_support"]:
        lines.append(f"- `{parameter['parameter_path']}` = {_inline(parameter['value'])} "
                     f"{_inline(parameter.get('comparator'))} unit {_inline(parameter['unit'])} · "
                     f"basis `{parameter['basis']}` · claims {_inline(parameter['claim_refs'])} · "
                     f"support field: {parameter['support_field']}")
    quote, numeric, semantic = (verification["quote_check"], verification["numerical_consistency"],
                               verification["semantic_support"])
    lines += ["", "**Verification, reported as three separate checks**", "",
              f"- quote check — of {quote['claims']} cited claim(s), "
              f"{quote['span_checked_against_source']} carry "
              f"`location.span_checked_against_source: true` and {quote['quote_verified']} carry "
              f"`quote_verified` among their admission reasons",
              f"- numerical consistency — `value_in_quote` {numeric['value_in_quote']}, "
              f"`value_not_in_quote` {numeric['value_not_in_quote']}, not recorded "
              f"{numeric['not_recorded']} (field: `{numeric['field']}`)",
              f"- semantic support — `verification_status` "
              f"{_inline(semantic['states'])} (field: `{semantic['field']}`). "
              f"{semantic['note'].replace('`unverified`', 'unverified')}",
              f"- unresolved claim refs — {_inline(verification['unresolved_claim_refs'])}",
              "", "**Supporting and conflicting claims**", "",
              f"- counts by polarity: {_inline(support['counts'])}",
              f"- underlying experiment groups: {support['experiment_groups']}"]
    for polarity in sorted(support["claims_by_polarity"]):
        lines += ["", f"*polarity `{polarity}`*", ""]
        for claim in support["claims_by_polarity"][polarity]:
            lines += _claim_lines(claim)
    exposure = authority["exposure"]
    lines += ["", "**Critique, adjudication and authority**", ""]
    owed = authority["authority_required"] or []
    lines.append("- authority this criterion owes before it may score: "
                 + ("; ".join(f"`{r['reason']}` ({r['detail']})" for r in owed) if owed
                    else "none by the trigger table"))
    lines.append(f"- expert decisions: {_inline(authority['expert_decisions'])}")
    if not authority["machine_adjudications"]:
        lines.append("- machine adjudications: —")
    for record in authority["machine_adjudications"]:
        lines += [f"- machine adjudication `{record['adjudication_id']}` · route `{record['route']}` · "
                  f"resolution `{record['resolution']}` · approval kind `{record['approval_kind']}` · "
                  f"confirmed by a person {_inline(record['confirmed_by_a_person'])}",
                  f"  - reason: {_fence(record['reason_text'])}",
                  f"  - cites: {_inline(record.get('cites'))} · claims "
                  f"{_inline(record.get('cited_claim_ids'))} · independence "
                  f"{_inline(record.get('independence'))}"]
    if not authority["open_review_items"]:
        lines.append("- open review items: —")
    for item in authority["open_review_items"]:
        lines += [f"- open review item `{item['item_id']}` (`{item['state']}`, blocking "
                  f"{_inline(item['blocking'])}, raised {item['created_at']}): "
                  f"{_fence(item['why_expert_required'])}",
                  f"  - inspection bundle: {_inline(item['inspection_bundle'])}"]
    lines.append(f"- unresolved proposer/critic disputes: "
                 + (", ".join(f"`{d['item_id']}`" for d in authority["unresolved_disputes"])
                    if authority["unresolved_disputes"] else "—"))
    lines += [f"- exposure: derivation configuration `{exposure['derivation_configuration']}` · "
              f"historical-list exposure {_inline(exposure['historical_list_exposure'])}",
              f"  - {exposure['note']}"]
    lines += _finding_lines("critic findings", lifecycle["critic_findings"])
    lines += _finding_lines("validator problems", lifecycle["validator_problems"])
    lines += _finding_lines("dissent recorded on the rule", lifecycle["dissent_recorded_on_rule"])
    lines += ["", "**Lineage and lifecycle**", "",
              f"- pool lineage {_inline(lifecycle['pool_criterion_id'])} at version "
              f"{_inline(lifecycle['pool_version'])}, state {_inline(lifecycle['pool_state'])}",
              f"- parents {_inline(lifecycle['parents'])} · children {_inline(lifecycle['children'])}",
              f"- merged away: {_inline(lifecycle['merged_away'])}",
              f"- survived a collapse: {_inline(lifecycle['survived_collapse'])}",
              *_consolidation_lines(lifecycle.get("consolidation")),
              "- refinement history:" if lifecycle["refinement_history"]
              else "- refinement history: — (this criterion never entered the pool)"]
    for step in lifecycle["refinement_history"]:
        lines.append(f"  - round `{step.get('round_run_id')}` iteration {step.get('iteration')} "
                     f"stage `{step.get('stage')}` · `{step.get('operation')}` → `{step.get('state')}` · "
                     f"`{step.get('reason_kind')}` · {_fence(step.get('reason_text'))}")
    lines += ["", "**Use**", "",
              f"- status `{use['status']}` on `{use['rule_set_ref']}`"
              + (f" — {use['reason']}" if use.get("reason") else ""),
              f"- rule-set entry: {_inline(use['entry'])}",
              f"- scores while disputed: {_inline(use['scores_while_disputed'])} · "
              f"machine adjudicated: {_inline(use['machine_adjudicated'])} · "
              f"reads a collapsed attribute: {_inline(use['reads_collapsed_attribute'])}",
              f"- measured coverage: {_inline(use['measured_coverage'])}",
              "", "---", ""]
    return lines


def render_markdown(payload: dict[str, Any]) -> str:
    counts, task_block = payload["counts"], payload["task"]
    board = payload.get("board") or {}
    lines = [
        "# Derived criteria — review snapshot (historical baseline)",
        "",
        f"**Label:** `{payload['baseline_label']}`",
        "",
        payload["baseline_statement"],
        "",
        f"**Snapshot:** task stream `{payload['journal_position']['task_stream']}` pinned at journal "
        f"sequence {payload['journal_position']['pinned_seq']}. The exact records behind every card "
        f"are in `{REVIEW_JSON}`; the refs, hashes and code commit are in `{MANIFEST_JSON}`. "
        f"The counts below are reconciled in `{RECONCILIATION_MARKDOWN}`.",
        "",
        "## The task these criteria were derived for",
        "",
        f"- **task context** `{task_block['task_context_ref']}` · mode `{task_block['mode']}` · "
        f"group `{task_block['group_id']}`",
        f"- **objective**: {task_block['objective_text']}",
        f"- **objective provenance**: {_fence(task_block['objective_provenance'])}",
        f"- **required scope entities**: "
        + ", ".join(f"{e.get('label')} (`{e.get('identifier')}`, {e.get('role')})"
                    for e in (task_block["scope_entities"] or [])),
        f"- **constraints**: {_inline(task_block['constraints'])}",
        f"- **candidate universe**: {_inline(task_block['candidate_universe'])}",
        f"- **case source documents held out of derivation evidence**: "
        f"{_inline(task_block['case_source_documents'])}",
        f"- **declared reference outcome**: {_inline(task_block['seed_candidates'])}",
        "",
        "## How to read a card",
        "",
        "Three things are reported separately and must not be read as one status.",
        "",
        "1. **Quote check** — did the recorded span match the source text "
        "(`claim.location.span_checked_against_source`, and `quote_verified` among the admission reasons)?",
        "2. **Numerical consistency** — was the number the criterion uses present in that span "
        "(`value_in_quote` / `value_not_in_quote` among the admission reasons)?",
        "3. **Semantic support** — did anything judge that the passage *justifies* this bound for this "
        "task (`claim.verification_status`)? `unverified` means the check was never run, not that the "
        "quotation failed.",
        "",
        "Each card also opens with **recovery-comparison facets**: the operational quantity, the "
        "applicability, the decision semantics and the threshold, read from the fields that execute "
        "rather than from the definition prose, with a hash over the measurement identity and over "
        "the decision identity so two criteria can be called the same or different mechanically. "
        "Where this schema records no field for a facet, the card says so under `gap:` instead of "
        "supplying a value.",
        "",
        "## Counts at this snapshot",
        "",
        "| quantity | value | what it counts |",
        "|---|---|---|",
    ]
    for key in ("proposals_added_to_pool", "pool_lineages", "promoted_pool_items", "pruned_pool_items",
                "registered_criteria", "registered_from_pool", "registered_from_templates",
                "registry_versions", "scoring_now", "deferred_now", "scoring_with_a_route_held_out_now",
                "collapsed_away_now", "collapses",
                "review_queue", "unresolved_disputes", "machine_adjudications", "expert_decisions",
                "bounds", "comparable_from_fields", "matching_facet_gaps"):
        entry = counts[key]
        lines.append(f"| `{key}` | {_inline(entry['value'])} | {entry['counts']} |")
    lines += ["", "## Confirmed rule sets", "",
              "| rule set | scoring | pending | deferred | scoring with a route held out | "
              "collapsed away | label |", "|---|---|---|---|---|---|---|"]
    for record in payload["rule_sets"]:
        c = record["counts"]
        lines.append(f"| `{record['rule_set_ref']}` | {c['scoring']} | {c['pending']} | {c['deferred']} | "
                     f"{c['scoring_with_a_route_held_out']} | "
                     f"{c['collapsed_away']} | `{record['acceptance_label']}` |")
    for record in payload["rule_sets"]:
        if record["acceptance_reasons"]:
            lines += ["", f"`{record['rule_set_ref']}` is labelled `{record['acceptance_label']}` because:"]
            lines += [f"- {reason}" for reason in record["acceptance_reasons"]]
    if board:
        lines += ["", "## The board these criteria were last applied on", "",
                  f"- **snapshot** `{board['snapshot_id']}` on `{board['rule_set_ref']}`, "
                  f"run `{board['run_id']}`, published {board['published_at']}",
                  f"- **candidates assessed** {board['candidates_assessed']} · "
                  f"**ranked** {board['candidates_ranked']} · result kind `{board['result_kind']}`",
                  f"- **reporting tuple**: {_inline(board['reporting_tuple'])}",
                  f"- **human review summary**: {_inline(board['human_review_summary'])}",
                  f"- snapshot artifact `{board['artifact_id']}` sha256 `{board['artifact_sha256']}`"]
    lines += ["", "## Derivation trajectory", "",
              "| round | iteration | stage | added | revised | merged away | removed | promoted | live after | reasons |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for step in payload["derivation_trajectory"]:
        lines.append(f"| `{step['round_run_id']}` | {step['iteration']} | `{step['stage']}` | {step['added']} | "
                     f"{step['revised']} | {step['merged_away']} | {step['removed']} | {step['promoted']} | "
                     f"{step.get('live_after')} | {_inline(step['reasons'])} |")
    recovery = payload["recovery_comparison_set"]
    lines += ["", "## The derived set, for a later recovery comparison", "", recovery["statement"], "",
              f"- **{recovery['included_count']} registered criteria** form the derived set: "
              + " · ".join(f"{kind} {entry['count']}" for kind, entry in recovery["by_origin"].items()),
              f"- **{len(recovery['excluded_as_a_repeated_variant'])} excluded as a repeated "
              f"variant** of a quantity another criterion already carries:"]
    for item in recovery["excluded_as_a_repeated_variant"]:
        lines.append(f"  - `{item['attribute_ref']}` ({item['name']}) — same quantity as "
                     f"`{item['same_quantity_as']}`; {_fence(item['reason'])}")
    lines += [f"- **{recovery['excluded_as_pruned_pool_items']} pruned pool items** are in the "
              f"lifecycle section below and are not derived criteria",
              f"- duplicate measurement identities remaining inside the derived set: "
              f"{_inline(recovery['duplicate_measurement_identities'])}"]
    lines += ["", "## Index of registered criteria", "",
              "| # | criterion | attribute | rule kind | cutoff | status |", "|---|---|---|---|---|---|"]
    for index, card in enumerate(payload["criteria"], start=1):
        lines.append(f"| {index} | {card['name']} | `{card['identity']['attribute_ref']}` | "
                     f"`{card['rule']['rule_kind']}` | {_inline(card['rule']['cutoff'])} | "
                     f"`{card['use']['status']}` |")
    lines += ["", "## Cards", ""]
    for index, card in enumerate(payload["criteria"], start=1):
        lines += _card_markdown(card, index)
    lines += _sources_markdown(payload)
    lines += _lifecycle_markdown(payload)
    lines += ["", "## Withheld from this export", "",
              f"- artifact kinds: {_inline(payload['withheld']['artifact_kinds'])}",
              f"- {payload['withheld']['reason']}", ""]
    return "\n".join(lines) + "\n"


def _lifecycle_markdown(payload: dict[str, Any]) -> list[str]:
    lifecycle = payload["lifecycle"]
    lines = ["", "## Lifecycle: what was pruned, deferred and merged away", "",
             lifecycle["statement"], ""]
    for state in sorted(lifecycle["pool_items_not_promoted"]):
        found = lifecycle["pool_items_not_promoted"][state]
        lines += [f"### Pool items in final state `{state}` ({len(found)})", ""]
        for item in found:
            left = item["left_at"]
            lines += [
                f"- **{_fence(item['name'])}** · `{item['criterion_id']}@v{item['final_version']}` · "
                f"dimension {_inline(item['dimension'])} · unit {_inline(item['unit'])} · "
                f"direction {_inline(item['direction'])}",
                f"  - left the pool at stage `{left.get('stage')}` iteration {left.get('iteration')} "
                f"of round `{left.get('round_run_id')}` by `{left.get('operation')}`",
                f"  - reason `{item['reason_kind']}`: {_fence(item['reason_text'])}",
                f"  - definition: {_fence(item['definition'])}",
                f"  - rule: {_inline(item['rule'])}",
            ]
            lines += [f"  {line}" for line in _finding_lines("critic findings", item["critic_findings"])]
            lines += [f"  {line}" for line in _finding_lines("validator problems", item["validator_problems"])]
            lines.append(f"  - cited claims: {_inline(item['supporting_claim_ids'])}")
        lines.append("")
    merged = lifecycle["merged_away_attributes"]
    lines += [f"### Registry versions merged away by a collapse ({len(merged)})", ""]
    for item in merged:
        lines += [
            f"- **{_fence(item['name'])}** · `{item['attribute_ref']}` with `{item['rule_ref']}` → "
            f"merged into `{item['merged_into']}`, scored by `{item['scored_by']}`",
            f"  - collapse `{item['collapse_id']}` · approval kind `{item['approval_kind']}` · "
            f"confirmed by a person {_inline(item['confirmed_by_a_person'])} · "
            f"withdrawn {_inline(item['collapse_withdrawn'])}",
            f"  - routes it contributed: {_inline(item['routes'])}",
            f"  - held out of the latest confirmed rule set: {_inline(item['held_out_of_latest_rule_set'])}",
            f"  - reason: {_fence(item['reason_text'])}",
        ]
    lines += ["", f"### Superseded registry versions ({len(lifecycle['superseded_registry_versions'])})", "",
              _inline(lifecycle["superseded_registry_versions"]), ""]
    return lines


def render_reconciliation(payload: dict[str, Any]) -> str:
    counts = payload["counts"]
    rule_sets = {r["rule_set_ref"]: r for r in payload["rule_sets"]}
    latest = payload["rule_sets"][-1] if payload["rule_sets"] else {"rule_set_ref": None, "counts": {}}
    first = payload["rule_sets"][0] if payload["rule_sets"] else {"rule_set_ref": None, "counts": {}}
    registered = counts["registered_criteria"]["value"]
    scoring = latest["counts"].get("scoring")
    deferred = latest["counts"].get("deferred")
    collapsed = latest["counts"].get("collapsed_away")
    published = first["counts"].get("scoring")
    lines = [
        "# Criteria count reconciliation",
        "",
        f"Measured from `{payload['journal_position']['task_stream']}` at journal sequence "
        f"{payload['journal_position']['pinned_seq']}; the same snapshot as `{REVIEW_JSON}`. "
        "The project has quoted several different criteria counts. They differ because they count "
        "different populations at different versions, not because any of them is wrong.",
        "",
        "## The numbers, each with its population",
        "",
        "| quoted number | value here | what it counts | version and scope |",
        "|---|---|---|---|",
        f"| 72 proposals | {counts['proposals_added_to_pool']['value']} | pool lineages the `propose` "
        "stage created | the whole task, summed over every round |",
        f"| 34 promoted | {counts['promoted_pool_items']['value']} | pool lineages whose final state is "
        "`promoted` | end state of the pool at this sequence |",
        f"| 40 registered criteria | {registered} | distinct attribute ids in the registry, each with "
        "one rule id | the registry, all origins |",
        f"| 13 scoring rules on the published board | {published} | entries in "
        f"`{first['rule_set_ref']}` | the first confirmed rule set |",
        "| 8 scoring rules in an offline experiment | not a rule set in this store | the 13 minus the "
        "five duplicate IUPHAR rules | an offline recomputation; it was never confirmed, so no "
        "`rules@v` holds it |",
        f"| 9 scoring rules in `{latest['rule_set_ref']}` | {scoring} | entries in the latest confirmed "
        "set | after the collapse and one machine adjudication |",
        f"| 26 deferred literature criteria | {deferred} | registered rules whose capability "
        "`literature_retrieval` was held out of the run | every confirmed set so far |",
        f"| 5 collapsed away | {collapsed} | registered rules whose attribute a collapse merged away | "
        f"`{latest['rule_set_ref']}` |",
        "",
        "## Why 34 and 40 differ",
        "",
        f"{counts['registered_from_pool']['value']} of the {registered} registered criteria were "
        f"written by a pool promotion. The other {counts['registered_from_templates']['value']} were "
        "written directly by the drug adapter's objective templates, which restate task-supplied "
        "requirements (the five required receptors and the oral-route constraint) and never enter the "
        "pool. So 34 counts the derivation's output and 40 counts the registry, which also holds the "
        "task's own mandated criteria.",
        "",
        f"The registry additionally holds {counts['registry_versions']['value']['attribute']} attribute "
        f"versions and {counts['registry_versions']['value']['rule']} rule versions for those "
        f"{registered} criteria. A second version is a revision of one criterion, not another "
        "criterion: five receptor attributes were revised to `@v2` to declare both curations as routes "
        "of one quantity, and the molecular-weight and lipophilicity attributes were revised to `@v2` "
        "to declare the transform their definitions already described.",
        "",
        "## Why the scoring counts differ",
        "",
        f"Every confirmed set draws on the same {registered} registered rules and differs only in how "
        "many of them may enter:",
        "",
        "| rule set | scoring | pending | deferred | collapsed away | adds up to |",
        "|---|---|---|---|---|---|",
    ]
    for record in payload["rule_sets"]:
        c = record["counts"]
        lines.append(f"| `{record['rule_set_ref']}` | {c['scoring']} | {c['pending']} | {c['deferred']} | "
                     f"{c['collapsed_away']} | {c['scoring'] + c['deferred'] + c['collapsed_away']} "
                     f"of {registered} |")
    route_held = latest["counts"].get("scoring_with_a_route_held_out") or 0
    if route_held:
        # Stated here because the arithmetic above would otherwise look wrong to a reader who had
        # counted the `deferred[]` rows: a deferral is per route, so a rule may appear in that list
        # and still score. It is counted once, under `scoring`, where it belongs.
        lines += ["",
                  f"{route_held} of the {scoring} scoring rules of `{latest['rule_set_ref']}` score on part of "
                  f"their declared evidence: a capability this run held out "
                  f"({', '.join(latest.get('deferred_capabilities') or []) or 'unrecorded'}) removes one or more "
                  f"of their routes and the rest are asked. They appear in `deferred[]` with `scope: route` and "
                  f"are counted once above, under scoring, never under deferred."]
    lines += [
        "",
        f"`{first['rule_set_ref']}`: {published} scoring plus {first['counts'].get('deferred')} deferred "
        f"accounts for {published + (first['counts'].get('deferred') or 0)} of {registered}. The "
        "remainder is the oral-route hard exclusion, which the trigger table gates and which had no "
        "decision at that point, so it entered neither list.",
        "",
        f"`{latest['rule_set_ref']}`: {scoring} scoring plus {deferred} deferred plus {collapsed} "
        f"collapsed away accounts for all {registered}. Relative to "
        f"`{first['rule_set_ref']}` it loses the five IUPHAR duplicates, whose attributes a collapse "
        "merged into the receptor attributes they duplicated, and gains the oral-route hard exclusion, "
        "which a machine adjudication resolved by restating the task's own constraint.",
        "",
        "The offline 8 sits between the two: it is the 13 with the five duplicates deleted rather than "
        "merged, and without the oral-route rule. Deleting an independent curation is not the path the "
        "store took; merging it into the quantity it duplicates is.",
        "",
        "## What the 9 open disputes are",
        "",
        f"{counts['unresolved_disputes']['value']} review items are open because a proposer and a "
        "critic still disagreed after one revision. They are not counted anywhere above as a criteria "
        "count: a disputed rule can still be registered, and five of the nine concern rules whose "
        "attributes the collapse later merged away.",
        "",
        "## Bounds",
        "",
        f"Of the {registered} registered criteria, "
        f"{counts['bounds']['value']['source_stated_with_claims']} carry a numeric bound whose basis is "
        f"a cited claim, {counts['bounds']['value']['task_constraint_cutoff']} carries a cutoff "
        "restating a task constraint, and "
        f"{counts['bounds']['value']['no_cutoff_evidence_insufficient']} carry "
        "`cutoff_basis: none_evidence_insufficient` and no cutoff at all. The two source-stated bounds "
        "are transform parameters, not rule cutoffs, so a reviewer looking only at `rule.cutoff` sees "
        "a registry with one bound in it.",
        "",
    ]
    return "\n".join(lines) + "\n"


def sha256_hex_bytes(data: bytes) -> str:
    """Digest of exact written bytes, so a reader can check a file without re-canonicalizing it."""
    return hashlib.sha256(data).hexdigest()


def manifest(payload: dict[str, Any], *, store_root: str, digests: dict[str, dict[str, Any]],
             implementation: dict[str, Any], exported_by: dict[str, Any] | None = None,
             exported_at: str | None = None) -> dict[str, Any]:
    """Refs, journal position, code commit and payload digests for one export.

    `payload_digest` is taken over the snapshot payload, which carries no export timestamp, so the
    digest of an unchanged snapshot does not move when it is exported again (handoff §11.2).
    """
    board = payload.get("board") or {}
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "export_kind": payload["export_kind"],
        "baseline_label": payload["baseline_label"],
        "baseline_statement": payload["baseline_statement"],
        "task": {"task_context_ref": payload["task"]["task_context_ref"],
                 "objective_text": payload["task"]["objective_text"]},
        "journal_position": payload["journal_position"],
        "rule_set_refs": [record["rule_set_ref"] for record in payload["rule_sets"]],
        "latest_rule_set_ref": payload["latest_rule_set_ref"],
        "recovery_comparison_set": {k: payload["recovery_comparison_set"][k] for k in
                                    ("statement", "included_count", "by_origin",
                                     "excluded_as_a_repeated_variant", "excluded_as_pruned_pool_items",
                                     "duplicate_measurement_identities")},
        "board": {k: board.get(k) for k in ("snapshot_id", "leaderboard_id", "rule_set_ref", "run_id",
                                            "round_id", "published_at", "evidence_snapshot_id",
                                            "candidates_assessed", "candidates_ranked", "artifact_sha256")}
                 if board else None,
        "store": {"root": store_root, "opened": "read_only"},
        "implementation": implementation,
        "payload_digest": {"sha256": sha256_hex(payload),
                           "over": "the canonical snapshot payload, which carries no export timestamp"},
        "file_digests": digests,
        "counts": payload["counts"],
        "withheld": payload["withheld"],
        "export_metadata": {"tool": "mas criteria export", "exported_at": exported_at or utc_now(),
                            "exported_by": exported_by,
                            "note": "exported_at is excluded from payload_digest on purpose"},
    }


def write(core: Core, task_id: str, out_dir: str | Path, *, at_seq: int | None = None,
          with_board: bool = True, implementation: dict[str, Any] | None = None,
          exported_by: dict[str, Any] | None = None, store_root: str | None = None) -> dict[str, Any]:
    """Write the four artifacts of §11.2 and return the manifest."""
    payload = snapshot(core, task_id, at_seq=at_seq, with_board=with_board)
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        REVIEW_JSON: canonical_bytes(payload) + b"\n",
        REVIEW_MARKDOWN: render_markdown(payload).encode("utf-8"),
        RECONCILIATION_MARKDOWN: render_reconciliation(payload).encode("utf-8"),
    }
    digests = {}
    for name, data in files.items():
        (directory / name).write_bytes(data)
        digests[name] = {"sha256": sha256_hex_bytes(data), "bytes": len(data)}
    record = manifest(payload, store_root=store_root or str(core.store.root), digests=digests,
                      implementation=implementation or {}, exported_by=exported_by)
    manifest_bytes = json.dumps(record, indent=1, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    (directory / MANIFEST_JSON).write_bytes(manifest_bytes)
    record["paths"] = {name: str(directory / name) for name in list(files) + [MANIFEST_JSON]}
    return record
