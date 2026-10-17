"""Primary CQA recovery (handoff §12.2): the comparison against the sealed historical list.

WHY this module is the project's primary acceptance measurement: everything else the repository
measures -- how many criteria were derived, whether every threshold traces to a quoted passage,
where a reference compound lands on a board -- is a statement about the system's own output. The one
measurement that asks whether the derivation found what the domain experts found is the comparison
against the critical quality attributes the original authors used, and until this module existed
that comparison had no implementation at all.

WHY no historical item appears in this file or in `tests/test_recovery.py`: the list is sealed and
held outside the repository. It arrives once, after the criteria are frozen, through `record_intake`
-- as data an isolated evaluator supplies, never as a literal here, a default, or a test fixture.
The tests exercise this machinery with obviously synthetic items so that no test doubles as a leak,
and every refusal message in this module names items by reference rather than echoing their text,
because an error string is a surface too.

WHY the intake can only arrive second: `record_intake` refuses while no criteria snapshot is frozen
(§12.1). A list that could still shape the criteria it is compared against measures nothing, so the
refusal is the measurement's integrity condition rather than a convenience check.

WHY a model proposes and code decides: matching "median curated potency against a receptor" to a
historical item worded differently is a semantic judgement no predicate makes. That judgement is a
model call in an isolated evaluator role -- never the proposer or the critic that wrote the criteria
-- and everything checkable about its answer is checked by `check_mapping`: that every derived ref
it cites exists in the frozen set, that the three exclusive categories partition the historical
items, that no derived meaning is counted for two items without an explicit split mapping, and that
a claimed `exact` does not sit on a difference the proposal's own facet report records. A mapping
that fails any of those is refused, not repaired and not silently accepted.

WHY `extra` is not an error: a derived criterion with no historical counterpart may be a dimension
the original authors did not write down. It is counted and reported on the derived side, and the
report says in so many words that it is not a defect (§12.2).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import criteria, criteria_export, vocab
from .canonical import canonical_bytes, sha256_hex
from .derivation_stages import quantity_key
from .clock import utc_now
from .ids import new_id
from .models import ModelRequest, ModelRoster, call_role
from .runtime import Core

SCHEMA_VERSION = 1

# The artifact kind is the literal `derivation._excluded` already names in every derivation
# decision's visibility manifest under `omitted_reason: evaluator_only_artifact`. Naming the intake
# anything else would leave that mechanical record of exclusion pointing at nothing.
INTAKE_KIND = "historical_criteria_intake"
COMPARISON_KIND = "recovery_comparison"
REPORT_KIND = "recovery_report"

# The isolated evaluator. `models.ROLES` already registers this role and nothing else binds it, so
# the comparison runs on a model binding that no deriving stage shares (§12.2, design §5.1).
EVALUATOR_ROLE = "evaluator_judge"
# Roles whose exposure to the list would void the measurement: everything that writes, critiques or
# confirms a criterion, plus the coordinator driving them.
DERIVING_ROLES = frozenset({"planner", "proposer", "critic", "adjudicator", "retriever", "reader",
                            "summarizer", "reflector", "operator", "coordinator"})

# Exactly these three, exclusive and exhaustive over the historical items, so the counts sum to the
# number of items supplied (§12.2). The `recovery_category` domain also registers `extra`, which is a
# label for the derived side and never a category a historical item can take.
CATEGORIES = tuple(value for value in vocab.DOMAINS["recovery_category"] if value != "extra")
FACETS = ("operational_quantity", "applicability", "decision_semantics", "threshold")
# How a facet difference is reported in the three words §12.2 uses. A quantity or a semantics
# difference is a difference in expression; a narrower or wider population is scope; a cutoff is a
# threshold. The mapping is fixed here so a near-equivalent cannot be declared without naming which
# of the three it rests on.
_DIFFERENCE_OF_FACET = {"operational_quantity": "expression", "decision_semantics": "expression",
                        "applicability": "scope", "threshold": "threshold"}

# §2.4's four origins, as the export's `_origin` labels them plus the expert-edit route. A criterion
# that restates a requirement the task supplied was not independently discovered, so the report
# stratifies by these and never reports a restatement as a derivation (§12.2).
RESTATEMENT_STRATA = ("task_mandated", "adapter_template")
INDEPENDENT_STRATA = ("literature_derived",)
_STRATUM_OF_ORIGIN = {"task_mandated_template": "task_mandated", "adapter_template": "adapter_template",
                      "literature_derived": "literature_derived", "unlabelled": "origin_not_recorded"}

REPORT_JSON = "recovery_report.json"
REPORT_MARKDOWN = "recovery_report.md"
COUNTS_JSON = "recovery_counts.json"
COUNTS_MARKDOWN = "recovery_counts.md"
MANIFEST_JSON = "recovery_manifest.json"
# The two files that necessarily echo the historical items: the mappings and their rationales cannot
# be written without them. `write` refuses to put these where the repository publishes its reviewable
# exports, because the one directory a reviewer is told to read is the one place this content must
# not land. The former audit directory remains guarded for compatibility.
EVALUATOR_ONLY_FILES = (REPORT_JSON, REPORT_MARKDOWN)
PUBLISHED_DIRECTORIES = ("design_audit", "docs", "examples")


class RecoveryError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


class GateRefusal(RecoveryError):
    """A proposed mapping that failed the deterministic gate. It is refused, never repaired."""

    def __init__(self, problems: list[dict[str, Any]]):
        super().__init__("mapping_refused",
                         f"{len(problems)} check(s) failed: " + "; ".join(p["code"] for p in problems))
        self.problems = problems


# --- the case stream -------------------------------------------------------------------------

def case_stream(core: Core, task_id: str) -> str:
    """The stream that holds the intake, its access log and the comparison records.

    WHY not the task stream: derivation, the criteria pool, the review queue and the criteria export
    all fold the task stream, and an evaluator-only record living there would be one `event_type`
    filter away from a derivation read. The case stream is a stream kind the design already reserves
    for exactly this (design §2.4, §8.6) and that no derivation fold replays.
    """
    reference = (_task_context(core, task_id) or {}).get("case_ref")
    if reference:
        return reference if reference.startswith("case_") else f"case_{reference}"
    return "case_" + task_id.split("_", 1)[-1]


def _task_context(core: Core, task_id: str) -> dict[str, Any] | None:
    from . import task as task_mod
    try:
        return task_mod.get(core, task_id)
    except KeyError:
        return None


# --- the freeze ------------------------------------------------------------------------------

def frozen_snapshots(core: Core, task_id: str, *, rule_set_refs: list[str] | None = None) -> dict[str, Any]:
    """The criteria snapshots the comparison is made against, refusing unless they are frozen.

    Frozen means confirmed: a `criterion.version_approved` event naming a `rules@v` record. Nothing
    else in this store fixes a criteria snapshot, and §12.2's "after all intended criterion
    snapshots are frozen" is the whole reason the intake is refused before one exists.
    """
    approvals = [event for event in core.journal.replay(task_id)
                 if event.event_type == "criterion.version_approved"]
    if not approvals:
        raise RecoveryError("criteria_not_frozen",
                            f"{task_id} has no confirmed rule set, so there is no frozen criteria snapshot to "
                            f"compare against; the historical list arrives after the freeze, never before it")
    available = {event.payload["rule_set_ref"]: event for event in approvals}
    wanted = list(available) if rule_set_refs is None else list(rule_set_refs)
    unknown = [ref for ref in wanted if ref not in available]
    if unknown:
        raise RecoveryError("unknown_rule_set",
                            f"{', '.join(unknown)} is not a confirmed rule set of {task_id} "
                            f"(confirmed: {', '.join(sorted(available))})")
    records = []
    for ref in wanted:
        event = available[ref]
        record = core.artifacts.payload(event.payload["artifact_id"])
        records.append({"rule_set_ref": ref, "frozen_at_seq": event.seq, "frozen_at": event.recorded_at,
                        "artifact_id": event.payload["artifact_id"],
                        "artifact_sha256": criteria_export._artifact_hash(core, event.payload["artifact_id"]),
                        "acceptance_label": record.get("acceptance_label"),
                        "acceptance_reasons": record.get("acceptance_reasons") or [],
                        "preregistration_ref": record.get("preregistration_ref"),
                        "scoring_rules": len(record.get("entries") or [])})
    return {"rule_set_refs": [r["rule_set_ref"] for r in records], "snapshots": records,
            "frozen_at_seq": max(r["frozen_at_seq"] for r in records),
            "frozen_at": max(r["frozen_at"] for r in records),
            "task_stream_last_seq": core.journal.last_seq(task_id)}


# --- the intake ------------------------------------------------------------------------------

def _check_evaluator(by: dict[str, Any], what: str) -> None:
    # An isolated external agent records its real identity; it does not impersonate
    # a person. Deriving roles and an ordinary agent/evaluator remain unauthorized.
    if (by.get("kind"), by.get("role")) not in (("human", "evaluator"), ("agent", EVALUATOR_ROLE)):
        raise RecoveryError("rejected_unauthorized",
                            f"{what} is an evaluator command; the acting session holds "
                            f"{by.get('role')!r} as a {by.get('kind')!r}")


def record_intake(core: Core, task_id: str, intake: dict[str, Any], *, by: dict[str, Any],
                  rule_set_refs: list[str] | None = None, entry: str = "interactive") -> dict[str, Any]:
    """Record the historical list once, as an evaluator-only artifact, after the criteria froze.

    The supplied items are stored verbatim and never normalized: a comparison against a tidied copy
    of the reference is a comparison against this system's reading of it. What is recorded besides
    the items is who supplied them, when, the freeze references they are being compared against, and
    a hash over their canonical form, so a later report can prove it compared the same list.
    """
    _check_evaluator(by, "recording the historical-criteria intake")
    freeze = frozen_snapshots(core, task_id, rule_set_refs=rule_set_refs)
    existing = intake_reference(core, task_id)
    if existing is not None:
        raise RecoveryError("intake_already_recorded",
                            f"{existing['intake_id']} was recorded at {existing['recorded_at']} with "
                            f"{existing['item_count']} items; the list is opened once (§12.2), so a corrected "
                            f"list is a new case, not a second intake")
    items = list(intake.get("items") or intake.get("verbatim_items") or [])
    if not items:
        raise RecoveryError("empty_intake", "an intake with no items measures nothing")
    provenance = vocab.require("intake_provenance_form", intake.get("provenance_form") or "author_supplied_list")
    attestation = vocab.require("completeness_attestation", intake.get("completeness_attestation") or "unknown")
    intake_id = new_id("hci")
    recorded = []
    for index, item in enumerate(items):
        # Named by reference, never by content: a refusal message is a surface like any other.
        reference = f"{intake_id}#item_{index + 1:02d}"
        for field in ("label", "definition_as_given"):
            if not str(item.get(field) or "").strip():
                raise RecoveryError("item_incomplete", f"{reference} has no {field}")
        recorded.append({"item_ref": reference, "label": item["label"],
                         "definition_as_given": item["definition_as_given"],
                         "dimension_as_given": item.get("dimension_as_given"),
                         "threshold_as_given": item.get("threshold_as_given"),
                         "unit_as_given": item.get("unit_as_given"),
                         "direction_as_given": item.get("direction_as_given"),
                         "notes": item.get("notes")})
    record = {
        "schema_version": SCHEMA_VERSION, "intake_id": intake_id, "task_id": task_id,
        "visibility": vocab.require("field_visibility", "evaluator_only"),
        "readers": ["the comparison function in core/recovery.py",
                    "the review queue, on comparison-adjudication items only",
                    "the evaluator-role recovery panel"],
        "provided_by": intake.get("provided_by"), "provided_at": intake.get("provided_at"),
        "provenance_form": provenance, "completeness_attestation": attestation,
        "item_count": len(recorded), "items": recorded,
        "ambiguities": list(intake.get("ambiguities") or []),
        "content_sha256": sha256_hex(recorded),
        "freeze": freeze,
        "recorded_by": by, "recorded_at": utc_now(), "entry": entry,
    }
    artifact_id = core.artifacts.put(INTAKE_KIND, record)
    stream = case_stream(core, task_id)
    # The event itself carries no item: the header is what every non-evaluator surface may read, so
    # it must be safe to read. Counts and a hash say that a list of a given size arrived and which
    # bytes it was, and nothing about what it says.
    core.journal.append(stream, "case.version_recorded", actor=by, ids={"task_id": task_id},
                        payload={"record_kind": INTAKE_KIND, "intake_id": intake_id, "artifact_id": artifact_id,
                                 "item_count": len(recorded), "content_sha256": record["content_sha256"],
                                 "provenance_form": provenance, "completeness_attestation": attestation,
                                 "provided_by": intake.get("provided_by"), "provided_at": intake.get("provided_at"),
                                 "visibility": "evaluator_only",
                                 "freeze": {"rule_set_refs": freeze["rule_set_refs"],
                                            "frozen_at_seq": freeze["frozen_at_seq"],
                                            "frozen_at": freeze["frozen_at"]}},
                        artifact_links=[{"kind": INTAKE_KIND, "id": artifact_id}], visibility="evaluator",
                        summary=f"historical-criteria intake {intake_id}: {len(recorded)} items against "
                                f"{', '.join(freeze['rule_set_refs'])}")
    return record


def intake_reference(core: Core, task_id: str) -> dict[str, Any] | None:
    """The intake's content-free header: what it was compared against, how large it was, its hash.

    Reads the journal, not the artifact, so it is not an access to evaluator-only content and is not
    logged as one. Every surface that needs to say "a list of eleven arrived after the freeze"
    without saying what is in it reads this.
    """
    for event in core.journal.replay(case_stream(core, task_id)):
        if event.event_type == "case.version_recorded" and event.payload.get("record_kind") == INTAKE_KIND:
            return dict(event.payload, recorded_at=event.recorded_at, recorded_by=event.actor, seq=event.seq)
    return None


def read_intake(core: Core, task_id: str, *, by: dict[str, Any], purpose: str,
                via: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read the sealed items, writing the access-log event the exposure rule consults.

    Every read is logged because reading changes what is known about the reader (design §8.6): an
    actor with a logged read is `exposed` from that point on whatever it declared, and the report
    says so rather than taking a declaration's word for it.
    """
    _check_evaluator(by, "reading the historical-criteria intake")
    header = intake_reference(core, task_id)
    if header is None:
        raise RecoveryError("no_intake", f"no historical-criteria intake has been recorded for {task_id}")
    core.journal.append(case_stream(core, task_id), "evaluator_only.read", actor=by,
                        ids={"task_id": task_id},
                        payload={"person_id": by.get("id"), "subject": header["intake_id"],
                                 "subject_kind": INTAKE_KIND, "purpose": purpose, "via": via or by.get("via"),
                                 "exposure_consequence": "the reading actor is exposed from this event onward"},
                        visibility="evaluator",
                        summary=f"evaluator-only read of {header['intake_id']} for {purpose}")
    return core.artifacts.payload(header["artifact_id"])


def access_log(core: Core, task_id: str) -> list[dict[str, Any]]:
    """Every logged read of evaluator-only content for this case, in order."""
    return [{"seq": event.seq, "read_at": event.payload.get("read_at") or event.recorded_at,
             "logged_at": event.recorded_at, "actor": event.actor,
             "role": (event.actor or {}).get("role"), "subject": event.payload.get("subject"),
             "purpose": event.payload.get("purpose")}
            for event in core.journal.replay(case_stream(core, task_id))
            if event.event_type == "evaluator_only.read"]


# --- the frozen derived set ------------------------------------------------------------------

def _confirming_decisions(core: Core, task_id: str, at_seq: int) -> dict[str, dict[str, Any]]:
    """Every expert decision recorded on this task up to the pin, by decision id.

    WHY folded here rather than read from the export: `review.items` carries a decision's id and its
    verdict onto the queue item but not the `historical_list_exposure` the decision declared, so the
    export's per-criterion exposure field has no declaration to report. The declaration lives on the
    decision event, which is what this reads -- and the exposure rule needs it per criterion, because
    it is the confirming person, not the deriving agent, who may have seen the list.
    """
    out: dict[str, dict[str, Any]] = {}
    for event in core.journal.replay(task_id, to_seq=at_seq):
        if event.event_type == "human.review_decided":
            out[event.payload["decision_id"]] = {
                "decision": event.payload.get("decision"),
                "historical_list_exposure": event.payload.get("historical_list_exposure"),
                "decided_by": (event.payload.get("actor") or {}).get("id"),
                "decided_at": event.payload.get("decided_at")}
    return out


def derived_set(core: Core, task_id: str, *, at_seq: int | None = None) -> dict[str, Any]:
    """The derived criteria a mapping may cite, read from the criteria export's own facets.

    WHY it is built on `criteria_export.snapshot` rather than on the registry: the export already
    computes the four facets §12.2 compares on, already excludes the criteria whose quantity another
    criterion carries, and already labels each criterion's origin. A second, slightly different
    reading of the same records would be a second answer to "what was derived", and the comparison
    would then be against neither of them.

    `meaning_key` is `derivation_stages.quantity_key`, the registry's own measurement identity:
    capability set, canonical unit, direction, subject parameters and declared transform. The gate
    counts meanings rather than criteria, which is what stops repeated variants from inflating
    recovery (§12.2).

    WHY not `criteria.evidence_key`, which is the other hash on the card: that one is a *retrieval*
    identity -- capability, question kind and parameters -- and `question_kind` names which database
    answers. A receptor's curated potency from ChEMBL and the same affinity from IUPHAR are one
    quantity with two retrieval identities, so keying on retrieval would let one meaning be spent on
    two historical items unchallenged; and a quantity derived from a measurement by a declared
    transform shares its source's retrieval identity while measuring something else, so keying on
    retrieval would also refuse a mapping that correctly matched both. That is F5's separation
    applied here: retrieval identity for caching, measurement identity for whether two criteria
    estimate the same thing.
    """
    payload = criteria_export.snapshot(core, task_id, at_seq=at_seq, with_board=False)
    cards = {card["identity"]["attribute_ref"]: card for card in payload["criteria"]}
    decisions = _confirming_decisions(core, task_id, payload["journal_position"]["pinned_seq"])
    # One replay for every attribute record, because `quantity_key` reads fields the card does not
    # carry and loading them one at a time would replay a 140,000-event stream once per criterion.
    pinned_core, _ = criteria_export.pinned(core, task_id, at_seq)
    records = {entry["ref"]: entry["record"] for entry in criteria_export._registry(pinned_core, task_id).values()
               if entry["kind"] == "attribute"}
    entries = []
    for included in payload["recovery_comparison_set"]["included"]:
        card = cards[included["attribute_ref"]]
        confirming = [d for d in card["authority"]["expert_decisions"] if d in decisions]
        edited = [d for d in confirming if decisions[d]["decision"] == "approve_with_edits"]
        declared = sorted({decisions[d]["historical_list_exposure"] for d in confirming
                           if decisions[d]["historical_list_exposure"]})
        origin = card["origin"]["kind"]
        entries.append({
            "attribute_ref": card["identity"]["attribute_ref"], "rule_ref": card["identity"]["rule_ref"],
            "name": card["name"],
            "origin_kind": origin,
            "stratum": "expert_modified" if edited else _STRATUM_OF_ORIGIN.get(origin, "origin_not_recorded"),
            "expert_edits": edited, "confirming_decisions": confirming,
            "status": card["use"]["status"],
            "meaning_key": sha256_hex(list(quantity_key(records[card["identity"]["attribute_ref"]]))),
            "retrieval_identity_sha256": card["computation"]["evidence_key_sha256"],
            "measurement_identity_sha256": card["matching_facets"]["measurement_identity_sha256"],
            "decision_identity_sha256": card["matching_facets"]["decision_identity_sha256"],
            "facets": {facet: card["matching_facets"][facet] for facet in FACETS},
            "comparable_from_fields": card["matching_facets"]["comparable_from_fields"],
            "gaps": card["matching_facets"]["gaps"],
            "declared_exposure": declared, "confirmed_by_a_person": bool(confirming),
            "derivation_configuration": card["origin"]["derivation_configuration"],
        })
    meanings: dict[str, list[str]] = {}
    for entry in entries:
        meanings.setdefault(entry["meaning_key"], []).append(entry["attribute_ref"])
    for entry in entries:
        entry["same_meaning_as"] = sorted(set(meanings[entry["meaning_key"]]) - {entry["attribute_ref"]})
    strata: dict[str, list[str]] = {}
    for entry in entries:
        strata.setdefault(entry["stratum"], []).append(entry["attribute_ref"])
    return {
        "statement": payload["recovery_comparison_set"]["statement"],
        "task_context_ref": payload["task"]["task_context_ref"],
        "pinned_seq": payload["journal_position"]["pinned_seq"],
        "rule_set_refs": [record["rule_set_ref"] for record in payload["rule_sets"]],
        "criteria": entries,
        "criteria_count": len(entries),
        "meanings": {key: sorted(refs) for key, refs in sorted(meanings.items())},
        "repeated_variants": {key: sorted(refs) for key, refs in sorted(meanings.items()) if len(refs) > 1},
        "by_stratum": {stratum: sorted(refs) for stratum, refs in sorted(strata.items())},
        "excluded_as_a_repeated_variant": payload["recovery_comparison_set"]["excluded_as_a_repeated_variant"],
        "excluded_as_pruned_pool_items": payload["recovery_comparison_set"]["excluded_as_pruned_pool_items"],
        "payload_digest": sha256_hex(payload),
    }


# --- the deterministic gate ------------------------------------------------------------------

def _facet_differences(entry: dict[str, Any], item: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    """Which facets the proposal itself reports as differing, and the problems in how it reports."""
    problems: list[dict[str, Any]] = []
    facets = entry.get("facets") or {}
    reference = entry["historical_item_ref"]
    differing = []
    has_threshold = bool(str(item.get("threshold_as_given") or "").strip())
    for facet in FACETS:
        judgement = facets.get(facet)
        if facet == "threshold" and not has_threshold:
            # §12.2 asks for a matching threshold only where the historical item has one. With no
            # historical threshold there is nothing to match, so an unjudged facet is correct here.
            continue
        if not isinstance(judgement, dict) or judgement.get("agrees") not in (True, False):
            problems.append({"code": "facet_not_judged", "historical_item_ref": reference, "facet": facet,
                             "detail": f"{reference} cites derived criteria without saying whether {facet} agrees; "
                                       f"a category cannot rest on a facet nobody judged"})
            continue
        if judgement["agrees"] is False:
            differing.append(facet)
            if facet == "threshold" and not (str(judgement.get("historical") or "").strip()
                                             and str(judgement.get("derived") or "").strip()):
                # The difference §12.2 insists is preserved: both numbers, not the word "differs".
                problems.append({"code": "threshold_difference_not_preserved", "historical_item_ref": reference,
                                 "detail": f"{reference} reports a threshold difference without both the "
                                           f"historical and the derived value, so the difference is hidden"})
            if not str(judgement.get("note") or "").strip():
                problems.append({"code": "difference_not_reported", "historical_item_ref": reference,
                                 "facet": facet,
                                 "detail": f"{reference} reports {facet} as differing with no note saying how; "
                                           f"a near-equivalent difference must be reported explicitly"})
    return differing, problems


def check_mapping(mapping: list[dict[str, Any]], *, intake: dict[str, Any],
                  derived: dict[str, Any]) -> dict[str, Any]:
    """Refuse a proposed mapping that any mechanical check contradicts; otherwise normalize it.

    The gate never changes a category to make a mapping pass: it derives the category from the
    proposal's own per-facet judgements and refuses when the declared category disagrees. That is
    what makes "a matching threshold where the historical item has one" executable -- a proposal
    cannot claim `exact` over a difference it has itself recorded.
    """
    problems: list[dict[str, Any]] = []
    items = {item["item_ref"]: item for item in intake["items"]}
    known = {entry["attribute_ref"]: entry for entry in derived["criteria"]}
    by_item: dict[str, dict[str, Any]] = {}
    for entry in mapping:
        reference = entry.get("historical_item_ref")
        if reference not in items:
            problems.append({"code": "unknown_historical_item", "historical_item_ref": reference,
                             "detail": f"{reference!r} is not an item of {intake['intake_id']}"})
            continue
        if reference in by_item:
            problems.append({"code": "duplicate_item_proposal", "historical_item_ref": reference,
                             "detail": f"{reference} has more than one proposed mapping; the three categories are "
                                       f"exclusive, so each item takes exactly one"})
            continue
        by_item[reference] = entry
    for reference in items:
        if reference not in by_item:
            problems.append({"code": "partition_incomplete", "historical_item_ref": reference,
                             "detail": f"{reference} has no proposed mapping; the categories must partition every "
                                       f"historical item so the counts sum to {intake['item_count']}"})

    normalized: list[dict[str, Any]] = []
    meaning_claims: dict[str, list[str]] = {}
    for reference, entry in by_item.items():
        item = items[reference]
        refs = list(entry.get("derived_attribute_refs") or [])
        unknown = [ref for ref in refs if ref not in known]
        if unknown:
            problems.append({"code": "unknown_derived_ref", "historical_item_ref": reference,
                             "detail": f"{reference} cites {', '.join(unknown)}, which is not in the frozen derived "
                                       f"set of {derived['criteria_count']} criteria pinned at seq "
                                       f"{derived['pinned_seq']}"})
        shape = entry.get("mapping_shape") or ("none" if not refs else
                                               "one_to_one" if len(refs) == 1 else "merged")
        try:
            vocab.require("recovery_mapping_shape", shape)
        except vocab.VocabularyViolation as error:
            problems.append({"code": "unknown_mapping_shape", "historical_item_ref": reference, "detail": str(error)})
            shape = "none" if not refs else "one_to_one"
        declared = entry.get("category")
        if declared is not None and declared not in CATEGORIES:
            problems.append({"code": "unknown_category", "historical_item_ref": reference,
                             "detail": f"{reference} declares category {declared!r}; the exclusive categories are "
                                       f"{', '.join(CATEGORIES)}"})
        basis = entry.get("match_basis")
        if basis is not None:
            try:
                vocab.require("recovery_match_basis", basis)
            except vocab.VocabularyViolation as error:
                problems.append({"code": "unknown_match_basis", "historical_item_ref": reference,
                                 "detail": str(error)})
        for kind in entry.get("difference_kinds") or []:
            try:
                vocab.require("recovery_difference_kind", kind)
            except vocab.VocabularyViolation as error:
                problems.append({"code": "unknown_difference_kind", "historical_item_ref": reference,
                                 "detail": str(error)})
        if not str(entry.get("rationale") or "").strip():
            problems.append({"code": "rationale_missing", "historical_item_ref": reference,
                             "detail": f"{reference} carries no mapping rationale; §12.2 reports one per item"})

        if not refs:
            category, differences, facet_problems = "missed", [], []
            if shape != "none":
                problems.append({"code": "missed_with_a_mapping_shape", "historical_item_ref": reference,
                                 "detail": f"{reference} cites no derived criterion but declares shape {shape!r}"})
        else:
            differences, facet_problems = _facet_differences(entry, item)
            category = vocab.require("recovery_category", "exact" if not differences else "near_equivalent")
        problems.extend(facet_problems)
        if declared is not None and declared in CATEGORIES and declared != category:
            code = ("exact_claimed_over_a_reported_difference" if declared == "exact"
                    else "category_contradicts_its_own_facets")
            problems.append({"code": code, "historical_item_ref": reference, "declared": declared,
                             "derived_from_facets": category, "differing_facets": differences,
                             "detail": f"{reference} is declared {declared} while its own facet report makes "
                                       f"it {category}"
                                       + (f" (differing: {', '.join(differences)})" if differences else "")})
        if refs and shape in ("merged", "split") and not str(entry.get("covers_historical_meaning") or "").strip():
            problems.append({"code": "coverage_not_explicit", "historical_item_ref": reference, "mapping_shape": shape,
                             "detail": f"{reference} declares a {shape} mapping without stating which historical "
                                       f"meaning each cited criterion covers; §12.2 requires explicit coverage"})
        difference_kinds = sorted({_DIFFERENCE_OF_FACET[facet] for facet in differences})
        stated = entry.get("difference_kinds")
        if stated is not None and sorted(set(stated)) != difference_kinds:
            problems.append({"code": "difference_kinds_do_not_match_the_facets", "historical_item_ref": reference,
                             "stated": sorted(set(stated)), "from_facets": difference_kinds,
                             "detail": f"{reference} states difference kinds {sorted(set(stated))} while its facet "
                                       f"report shows {difference_kinds}"})
        for ref in refs:
            meaning_claims.setdefault(known[ref]["meaning_key"] if ref in known else f"unknown:{ref}",
                                      []).append(reference)
        normalized.append({
            "comparison_ref": f"{reference}->{'+'.join(refs) or 'none'}",
            "historical_item_ref": reference, "category": category, "declared_category": declared,
            "derived_attribute_refs": refs, "mapping_shape": shape,
            "covers_historical_meaning": entry.get("covers_historical_meaning"),
            "difference_kinds": difference_kinds,
            "differing_facets": differences,
            "facets": entry.get("facets") or {},
            "match_basis": entry.get("match_basis"),
            "rationale": entry.get("rationale"),
            "derived_meaning_keys": sorted({known[ref]["meaning_key"] for ref in refs if ref in known}),
            "historical_threshold_as_given": item.get("threshold_as_given"),
        })

    # One derived meaning answering two historical items is either a split the mapping declares and
    # explains, or recovery counted twice. Keyed on the meaning rather than the ref so that two
    # registered readings of one quantity cannot be spent on two items (§12.2).
    for key, references in sorted(meaning_claims.items()):
        if len(set(references)) < 2:
            continue
        refs_of_meaning = derived["meanings"].get(key, [])
        undeclared = [r for r in sorted(set(references))
                      if (by_item.get(r) or {}).get("mapping_shape") != "split"]
        if undeclared:
            problems.append({"code": "derived_meaning_double_counted", "historical_item_refs": sorted(set(references)),
                             "derived_attribute_refs": refs_of_meaning,
                             "detail": f"one derived meaning ({', '.join(refs_of_meaning) or key}) is counted for "
                                       f"{len(set(references))} historical items, and "
                                       f"{', '.join(undeclared)} does not declare a split mapping"})
        else:
            missing = [r for r in sorted(set(references))
                       if not str((by_item.get(r) or {}).get("covers_historical_meaning") or "").strip()]
            if missing:
                problems.append({"code": "split_coverage_not_explicit", "historical_item_refs": sorted(set(references)),
                                 "detail": f"a split mapping over {', '.join(refs_of_meaning) or key} must state the "
                                           f"meaning each side covers; {', '.join(missing)} does not"})

    if problems:
        raise GateRefusal(problems)
    normalized.sort(key=lambda entry: entry["historical_item_ref"])
    return {"ok": True, "checked_at": utc_now(), "mapping": normalized,
            "checks": ["every cited derived ref is in the frozen set",
                       "the three exclusive categories partition the historical items",
                       "each category follows from the proposal's own per-facet judgement",
                       "a threshold is judged wherever the historical item states one",
                       "no derived meaning answers two historical items without an explicit split mapping",
                       "merged and split mappings state the coverage of each historical meaning"]}


def check_isolated_evaluator(roster: ModelRoster) -> dict[str, Any]:
    """Refuse a roster whose evaluator is the model that proposed or critiqued the criteria.

    The semantic judgement needs a model; it must not be the model under measurement. A roster that
    binds one adapter to both would have the proposer grading its own output, which is not an
    independent comparison however the prompt is worded (§12.2, design §5.1).
    """
    bound = roster.roles.get(EVALUATOR_ROLE)
    if not bound:
        raise RecoveryError("evaluator_unbound",
                            f"no adapter is bound to the {EVALUATOR_ROLE!r} role; the comparison is made by an "
                            f"isolated evaluator, never by a deriving role")
    clashes = sorted(role for role in ("proposer", "critic", "adjudicator")
                     if roster.roles.get(role) == bound)
    if clashes:
        raise RecoveryError("evaluator_not_isolated",
                            f"the {EVALUATOR_ROLE!r} role is bound to adapter {bound!r}, which also serves "
                            f"{', '.join(clashes)}; the evaluator may not be the model whose criteria are measured")
    adapter = roster.adapter(EVALUATOR_ROLE)
    return {"role": EVALUATOR_ROLE, "adapter_id": bound, "model_id": adapter.record.model_id,
            "provider_family": adapter.record.provider_family,
            "distinct_from": {role: roster.roles.get(role) for role in ("proposer", "critic", "adjudicator")}}


# --- the evaluator's proposal ----------------------------------------------------------------

_SYSTEM = (
    "You are an isolated evaluator measuring whether a set of derived screening criteria recovers a "
    "list of historical quality attributes that the derivation never saw. You did not write the "
    "criteria and you may not change them.\n"
    "For each historical item, decide whether the derived set contains a qualifying match, and "
    "judge each of the four facets separately:\n"
    "  operational_quantity -- the same property, measured the same way, in the same unit;\n"
    "  applicability -- the same population and the same behaviour where it does not apply;\n"
    "  decision_semantics -- the same role in the decision (hard constraint, preference, context) "
    "and the same direction;\n"
    "  threshold -- judge it only when the historical item states one; then say whether the derived "
    "cutoff matches, and give both values.\n"
    "Set `agrees` true or false per facet and write a `note` for every facet you set false. Cite "
    "derived criteria only by the `attribute_ref` given to you. Cite none when nothing qualifies.\n"
    "Do not label the category: the facets you report decide it. Report every difference you see; a "
    "difference you leave out is a refused mapping, not a closer match.\n"
    "If one derived criterion covers two historical items, declare `mapping_shape: \"split\"` on "
    "both and state in `covers_historical_meaning` which meaning each side covers. If several "
    "derived criteria together cover one item, declare `mapping_shape: \"merged\"` and state the "
    "same."
)

_FACET_SCHEMA = {"type": "object", "required": ["agrees"],
                 "properties": {"agrees": {"type": ["boolean", "null"]}, "note": {"type": "string"},
                                "historical": {"type": "string"}, "derived": {"type": "string"}}}
RESPONSE_SCHEMA = {
    "type": "object", "required": ["mapping"],
    "properties": {"mapping": {"type": "array", "items": {
        "type": "object", "required": ["historical_item_ref", "derived_attribute_refs", "facets", "rationale"],
        "properties": {
            "historical_item_ref": {"type": "string"},
            "derived_attribute_refs": {"type": "array", "items": {"type": "string"}},
            "mapping_shape": {"type": "string", "enum": ["one_to_one", "merged", "split", "none"]},
            "covers_historical_meaning": {"type": "string"},
            "match_basis": {"type": "string", "enum": ["definition_and_unit_match", "definition_match_unit_differs",
                                                       "verdict_agreement_on_assessed_candidates",
                                                       "expert_judged_equivalent"]},
            "rationale": {"type": "string"},
            "facets": {"type": "object", "required": list(FACETS),
                       "properties": {facet: _FACET_SCHEMA for facet in FACETS}},
        }}}},
}


def propose_mapping(core: Core, roster: ModelRoster, task_id: str, *, intake: dict[str, Any],
                    derived: dict[str, Any], budget: Any = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """One evaluator call over the whole comparison, returning the proposed mapping and who judged.

    WHY one call and not one per item: a split mapping is a statement about two historical items at
    once, and a merge is a statement about several derived criteria. An evaluator shown one item at a
    time cannot declare either, and the gate would then refuse every mapping that needed one.
    """
    judged_by = check_isolated_evaluator(roster)
    payload = {
        "historical_items": [{k: item[k] for k in ("item_ref", "label", "definition_as_given", "dimension_as_given",
                                                   "threshold_as_given", "unit_as_given", "direction_as_given",
                                                   "notes")}
                             for item in intake["items"]],
        "derived_criteria": [{"attribute_ref": entry["attribute_ref"], "name": entry["name"],
                              "facets": entry["facets"], "unreadable_from_fields": entry["gaps"]}
                             for entry in derived["criteria"]],
    }
    request = ModelRequest(
        role=EVALUATOR_ROLE, system=_SYSTEM, response_schema=RESPONSE_SCHEMA, max_tokens=16000,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)}],
        metadata={"task_id": task_id, "intake_id": intake["intake_id"], "purpose": "primary_cqa_recovery"})
    response = call_role(core, roster, case_stream(core, task_id), request,
                         ids={"task_id": task_id}, budget=budget)
    data = response.data if isinstance(response.data, dict) else {}
    return list(data.get("mapping") or []), dict(judged_by, request_id=request.request_id,
                                                 model_id=response.model_id,
                                                 provider_path=response.provider_path)


# --- exposure --------------------------------------------------------------------------------

def _inheritance_sources(core: Core, task_id: str, at_seq: int | None = None) -> list[dict[str, Any]]:
    """The pinned ancestry of a derived case, without reading an evaluator-only artifact."""
    from . import task as task_mod

    context_core = criteria_export.pinned(core, task_id, at_seq)[0] if at_seq is not None else core
    context = _task_context(context_core, task_id) or {}
    seen = {task_id}
    sources = []
    while True:
        inheritance = context.get("inheritance") or {}
        source_id = context.get("derived_from_task_id") or inheritance.get("source_task_id")
        if not source_id:
            return sources
        # Older shortlist copies may retain their parent's inheritance block. The task's direct
        # derivation edge is authoritative; an ancestor's pin cannot pin a different task stream.
        if inheritance.get("source_task_id") not in (None, source_id):
            inheritance = {}
        if source_id in seen:
            raise RecoveryError("inheritance_cycle", f"the inherited case lineage repeats {source_id}")
        seen.add(source_id)
        source_seq = inheritance.get("source_at_seq")
        source_core, source_seq = criteria_export.pinned(core, source_id, source_seq)
        context = task_mod.get(source_core, source_id)
        sources.append({"task_id": source_id, "source_at_seq": source_seq,
                        "task_context_ref": f"{source_id}@v{context['version']}",
                        "case_ref": inheritance.get("source_case_ref") or case_stream(source_core, source_id),
                        "source_snapshot_artifact_id": inheritance.get("source_snapshot_artifact_id"),
                        "source_snapshot_sha256": inheritance.get("source_snapshot_sha256")})


def exposure_declaration(core: Core, task_id: str, *, intake: dict[str, Any],
                         derived: dict[str, Any]) -> dict[str, Any]:
    """Whether the coordinator or any deriving agent had seen the list before the criteria froze.

    Two sources, and the log outranks the declaration (design §8.6): declarations live on the expert
    decisions that confirmed each criterion, and the access log records who actually opened the
    intake. A read timestamped before the freeze by a deriving role or the coordinator is the one
    finding that voids an independent recovery claim, so it is computed rather than asserted.
    """
    sources = _inheritance_sources(core, task_id, derived.get("pinned_seq"))
    log = access_log(core, task_id)
    seen_reads = {(case_stream(core, task_id), read["seq"]) for read in log}
    source_decisions = []
    for source in sources:
        # A source read after inheritance but before the child freeze is still exposure. Only the
        # source criteria/context are pinned; access logs deliberately remain live across cases.
        for event in core.journal.replay(source["case_ref"]):
            identity = (source["case_ref"], event.seq)
            if event.event_type != "evaluator_only.read" or identity in seen_reads:
                continue
            seen_reads.add(identity)
            log.append({"seq": event.seq, "read_at": event.recorded_at, "actor": event.actor,
                        "role": (event.actor or {}).get("role"), "subject": event.payload.get("subject"),
                        "purpose": event.payload.get("purpose"), "source_task_id": source["task_id"],
                        "source_case_ref": source["case_ref"]})
        for event in core.journal.replay(source["task_id"], to_seq=source["source_at_seq"]):
            if event.event_type == "human.review_decided" and (event.payload.get("subject") or {}).get("kind") in (
                    "attribute_version", "rule_version", "rule_set_version", "cutoff_setting"):
                source_decisions.append({"source_task_id": source["task_id"], "seq": event.seq,
                                         "decision_id": event.payload["decision_id"],
                                         "subject": event.payload.get("subject"),
                                         "decision": event.payload.get("decision"),
                                         "historical_list_exposure": event.payload.get("historical_list_exposure"),
                                         "decided_by": (event.payload.get("actor") or event.actor).get("id")})
    frozen_at = intake["freeze"]["frozen_at"]
    before_freeze = [read for read in log if read["read_at"] < frozen_at]
    by_deriving = [read for read in log if (read["role"] or "") in DERIVING_ROLES]
    declared: dict[str, list[str]] = {}
    unconfirmed = []
    for entry in derived["criteria"]:
        if not entry["declared_exposure"]:
            unconfirmed.append(entry["attribute_ref"])
        for value in entry["declared_exposure"]:
            declared.setdefault(value, []).append(entry["attribute_ref"])
    # `undeclared` is treated as exposed by design §8.6, so a criterion whose confirmation declared
    # nothing cannot be counted in the independent view. This is why both views are always reported:
    # on a store where the terminal's default was `undeclared`, the independent view may be empty,
    # and that is a finding about the declarations rather than about the derivation.
    assisted_refs = sorted({ref for value, refs in declared.items() for ref in refs
                            if value in ("exposed", "undeclared")})
    # Copying work carries its lineage, while source decisions confer no authority on a new case.
    if sources:
        assisted_refs = sorted(entry["attribute_ref"] for entry in derived["criteria"])
    tainted = [read for read in before_freeze if (read["role"] or "") in DERIVING_ROLES]
    return {
        "statement": "Whether the list was seen before the criteria froze, from the access log and the "
                     "exposure declarations on the decisions that confirmed each criterion. Where a "
                     "declaration and the log disagree, the log prevails. Inherited cases carry "
                     "their source-case reads and source confirming declarations and are reported "
                     "as descriptive assisted readings, not new independent validation.",
        "reading_kind": "descriptive_inherited" if sources else "original_case",
        "is_independent_validation": not bool(sources or tainted or assisted_refs),
        "inherited_from": sources,
        "source_confirming_decisions": source_decisions,
        "criteria_frozen_at": frozen_at, "criteria_frozen_at_seq": intake["freeze"]["frozen_at_seq"],
        "intake_recorded_at": intake["recorded_at"],
        "intake_arrived_after_the_freeze": intake["recorded_at"] >= frozen_at,
        "coordinator_or_deriving_agent_saw_the_list_before_the_freeze": bool(tainted),
        "reads_before_the_freeze": before_freeze,
        "reads_by_a_deriving_role": by_deriving,
        "reads_logged": len(log),
        "declared_on_confirming_decisions": {value: sorted(refs) for value, refs in sorted(declared.items())},
        "criteria_with_no_confirming_decision": sorted(unconfirmed),
        "criteria_with_no_confirming_decision_note":
            "no person declared an exposure for these because no person confirmed them: they entered on "
            "the trigger table, a machine adjudication or a collapse, so there is no human exposure "
            "path to declare. That is not the same statement as a declaration of `not_exposed`.",
        "criteria_in_the_assisted_view": assisted_refs,
        "criteria_in_the_independent_view": sorted({entry["attribute_ref"] for entry in derived["criteria"]}
                                                   - set(assisted_refs)),
        "recovery_view": vocab.require("recovery_view", "assisted" if (sources or tainted or assisted_refs)
                                       else "independent"),
    }


# --- the comparison record and the report ----------------------------------------------------

def compare(core: Core, task_id: str, *, by: dict[str, Any], roster: ModelRoster | None = None,
            mapping: list[dict[str, Any]] | None = None, at_seq: int | None = None,
            budget: Any = None) -> dict[str, Any]:
    """Run the comparison once and record it, or refuse the mapping that fails the gate.

    A supplied `mapping` is for an evaluator whose model runs outside this process; it passes the
    same gate as one this module requested, and the record says which route produced it.
    """
    _check_evaluator(by, "comparing the historical-criteria intake")
    for event in core.journal.replay(case_stream(core, task_id)):
        if event.event_type == "evaluation.recorded" and event.payload.get("record_kind") == COMPARISON_KIND:
            raise RecoveryError("comparison_already_recorded",
                                f"{event.payload['comparison_id']} already compared this case; "
                                "read the recorded report, or register a new descriptive inherited case")
    header = intake_reference(core, task_id)
    if header is None:
        raise RecoveryError("no_intake", f"no historical-criteria intake has been recorded for {task_id}")
    pinned_at = header["freeze"]["frozen_at_seq"]
    if at_seq is not None and at_seq != pinned_at:
        raise RecoveryError("comparison_pin_mismatch",
                            f"the intake fixes the criteria at seq {pinned_at}; "
                            f"seq {at_seq} would compare a different set after opening the list")
    intake = read_intake(core, task_id, by=by, purpose="primary_cqa_recovery")
    derived = derived_set(core, task_id, at_seq=pinned_at)
    if mapping is None:
        if roster is None:
            raise RecoveryError("no_evaluator",
                                f"no comparison is recorded for {task_id} and nothing can make one: bind an "
                                f"adapter to the {EVALUATOR_ROLE!r} role (`mas init`, or --models), or supply a "
                                f"mapping an outside evaluator proposed (--mapping)")
        mapping, judged_by = propose_mapping(core, roster, task_id, intake=intake, derived=derived, budget=budget)
        route = "model_proposed"
    else:
        route = "supplied_by_the_evaluator"
        judged_by = {"role": EVALUATOR_ROLE, "adapter_id": None, "model_id": by.get("model_id"),
                     "supplied_by": by, "distinct_from": by.get("isolated_from_roles"),
                     "note": "proposed outside this process by the evaluator named in `supplied_by`; it "
                             "passed the same gate as a mapping this module requested"}
    gate = check_mapping(mapping, intake=intake, derived=derived)
    record = {
        "schema_version": SCHEMA_VERSION, "comparison_id": new_id("evr"), "task_id": task_id,
        "visibility": vocab.require("field_visibility", "evaluator_only"),
        "intake_id": intake["intake_id"], "intake_content_sha256": intake["content_sha256"],
        "freeze": intake["freeze"], "derived_set_digest": derived["payload_digest"],
        "derived_set_pinned_seq": derived["pinned_seq"],
        "judged_by": judged_by, "route": route, "gate": gate,
        "comparisons": gate["mapping"], "compared_by": by, "compared_at": utc_now(),
    }
    counts = _counts(record["comparisons"], intake, derived)
    artifact_id = core.artifacts.put(COMPARISON_KIND, record)
    core.journal.append(case_stream(core, task_id), "evaluation.recorded", actor=by, ids={"task_id": task_id},
                        payload={"record_kind": COMPARISON_KIND, "comparison_id": record["comparison_id"],
                                 "artifact_id": artifact_id, "visibility": "evaluator_only",
                                 "intake_id": intake["intake_id"], "route": route,
                                 "counts": counts["categories"], "rates": counts["rates"]},
                        artifact_links=[{"kind": COMPARISON_KIND, "id": artifact_id}], visibility="evaluator",
                        summary=f"recovery comparison {record['comparison_id']}: "
                                f"{counts['categories']['exact']} exact, "
                                f"{counts['categories']['near_equivalent']} near-equivalent, "
                                f"{counts['categories']['missed']} missed of {counts['n_historical']}")
    return record


def latest_comparison(core: Core, task_id: str) -> dict[str, Any] | None:
    """The last recorded comparison, read from the artifact the case stream names."""
    found = None
    for event in core.journal.replay(case_stream(core, task_id)):
        if event.event_type == "evaluation.recorded" and event.payload.get("record_kind") == COMPARISON_KIND:
            found = event.payload["artifact_id"]
    return None if found is None else core.artifacts.payload(found)


def _counts(comparisons: list[dict[str, Any]], intake: dict[str, Any],
            derived: dict[str, Any]) -> dict[str, Any]:
    """`exact / N` and `(exact + near_equivalent) / N` with the raw counts behind both."""
    n = intake["item_count"]
    categories = {category: sum(1 for c in comparisons if c["category"] == category) for category in CATEGORIES}
    cited_meanings = {key for c in comparisons for key in c["derived_meaning_keys"]}
    extra = [entry for entry in derived["criteria"] if entry["meaning_key"] not in cited_meanings]
    extra_meanings: dict[str, list[str]] = {}
    for entry in extra:
        extra_meanings.setdefault(entry["meaning_key"], []).append(entry["attribute_ref"])
    return {
        "n_historical": n,
        "categories": categories,
        "partitions": sum(categories.values()) == n,
        "rates": {
            "exact": {"numerator": categories["exact"], "denominator": n,
                      "as_text": f"{categories['exact']} / {n}",
                      "value": round(categories["exact"] / n, 4) if n else None},
            "exact_or_near_equivalent": {
                "numerator": categories["exact"] + categories["near_equivalent"], "denominator": n,
                "as_text": f"{categories['exact'] + categories['near_equivalent']} / {n}",
                "value": round((categories["exact"] + categories["near_equivalent"]) / n, 4) if n else None},
        },
        "derived_meanings_matched": len(cited_meanings),
        "extra": {
            "statement": "Derived criteria with no qualifying historical counterpart. Counted by meaning, so "
                         "two registered readings of one quantity are one extra. An extra is not "
                         "automatically a scientific error (§12.2).",
            "count_by_meaning": len(extra_meanings),
            "count_by_criterion": len(extra),
            "meanings": {key: sorted(refs) for key, refs in sorted(extra_meanings.items())},
            "by_stratum": {stratum: sorted(entry["attribute_ref"] for entry in extra
                                           if entry["stratum"] == stratum)
                           for stratum in sorted({entry["stratum"] for entry in extra})},
        },
        "repeated_variants_in_the_derived_set": derived["repeated_variants"],
    }


def _origin_view(comparisons: list[dict[str, Any]], derived: dict[str, Any],
                 counts: dict[str, Any]) -> dict[str, Any]:
    """Recovery split by where each matching criterion came from (§12.2, §2.4).

    WHY: a criterion that restates a requirement the task statement supplied was not discovered by
    the derivation, and a single recovery figure that mixes the two describes supplied requirements
    as independent findings. The second accounting here counts an item as independently recovered
    only when at least one criterion matching it came from the literature rather than from a task
    restatement or an adapter template.
    """
    stratum_of = {entry["attribute_ref"]: entry["stratum"] for entry in derived["criteria"]}
    per_stratum: dict[str, dict[str, Any]] = {}
    independent: dict[str, int] = {category: 0 for category in CATEGORIES}
    restated_only: list[str] = []
    for comparison in comparisons:
        strata = {stratum_of.get(ref, "origin_not_recorded") for ref in comparison["derived_attribute_refs"]}
        for stratum in sorted(strata):
            row = per_stratum.setdefault(stratum, {category: 0 for category in CATEGORIES})
            row[comparison["category"]] += 1
            row.setdefault("historical_item_refs", []).append(comparison["historical_item_ref"])
        if comparison["category"] == "missed":
            independent["missed"] += 1
        elif strata & set(INDEPENDENT_STRATA):
            independent[comparison["category"]] += 1
        else:
            restated_only.append(comparison["historical_item_ref"])
    n = counts["n_historical"]
    independently_recovered = independent["exact"] + independent["near_equivalent"]
    return {
        "statement": "Recovery by the origin of the criteria that matched. Items recovered only by a "
                     "criterion restating a task requirement or an adapter template are reported "
                     "separately and are not described as independently derived.",
        "derived_criteria_by_stratum": {stratum: len(refs) for stratum, refs in derived["by_stratum"].items()},
        "restatement_strata": list(RESTATEMENT_STRATA),
        "independent_strata": list(INDEPENDENT_STRATA),
        "recovered_by_stratum": per_stratum,
        "independently_derived_only": {
            "exact": independent["exact"], "near_equivalent": independent["near_equivalent"],
            "recovered": independently_recovered,
            "exact_as_text": f"{independent['exact']} / {n}",
            "recovered_as_text": f"{independently_recovered} / {n}",
            "items_recovered_only_by_a_restatement": sorted(restated_only),
            "note": "an item matched only by a task-mandated or template criterion is counted here as "
                    "supplied rather than derived; it keeps its category in the primary counts",
        },
    }


def report(core: Core, task_id: str, *, by: dict[str, Any], comparison: dict[str, Any] | None = None,
           roster: ModelRoster | None = None, mapping: list[dict[str, Any]] | None = None,
           at_seq: int | None = None, budget: Any = None) -> dict[str, Any]:
    """The full, evaluator-only recovery report: counts, rates, mappings, origins and exposure."""
    if comparison is None:
        comparison = latest_comparison(core, task_id)
        if comparison is not None and mapping is not None:
            # Refused rather than quietly ignored: a second mapping over the same sealed list is not
            # another independent recovery (§12.4), and a caller who supplied one is asking for a
            # measurement this command cannot honestly produce.
            raise RecoveryError("comparison_already_recorded",
                                f"{comparison['comparison_id']} already compared this frozen set against "
                                f"{comparison['intake_id']}; a second mapping over a list that has been opened "
                                f"cannot be reported as another independent recovery")
    if comparison is None:
        comparison = compare(core, task_id, by=by, roster=roster, mapping=mapping, at_seq=at_seq, budget=budget)
    intake = read_intake(core, task_id, by=by, purpose="recovery_report")
    if intake["content_sha256"] != comparison["intake_content_sha256"]:
        raise RecoveryError("intake_changed",
                            f"comparison {comparison['comparison_id']} was made against a different intake "
                            f"content hash; a report may not restate counts over a list it did not compare")
    derived = derived_set(core, task_id, at_seq=comparison["derived_set_pinned_seq"])
    # Reported rather than refused: the criteria are pinned at a task sequence, so no later criterion
    # version can move them, but the export also folds the claim records their bounds cite, and those
    # live in run streams the pin does not clamp. A later admission therefore moves the digest without
    # changing a single criterion, and refusing the report over that would block the measurement for a
    # reason that is not about the criteria.
    drift = derived["payload_digest"] != comparison["derived_set_digest"]
    counts = _counts(comparison["comparisons"], intake, derived)
    items = {item["item_ref"]: item for item in intake["items"]}
    mappings = [dict(record,
                     historical_label=items[record["historical_item_ref"]]["label"],
                     historical_definition_as_given=items[record["historical_item_ref"]]["definition_as_given"],
                     historical_dimension_as_given=items[record["historical_item_ref"]]["dimension_as_given"],
                     derived_names=[next((e["name"] for e in derived["criteria"]
                                          if e["attribute_ref"] == ref), None)
                                    for ref in record["derived_attribute_refs"]],
                     derived_strata=[next((e["stratum"] for e in derived["criteria"]
                                           if e["attribute_ref"] == ref), None)
                                     for ref in record["derived_attribute_refs"]])
                for record in comparison["comparisons"]]
    exposure = exposure_declaration(core, task_id, intake=intake, derived=derived)
    return {
        "schema_version": SCHEMA_VERSION, "report_kind": REPORT_KIND,
        "visibility": vocab.require("field_visibility", "evaluator_only"),
        "visibility_statement": (
            "**Evaluator-only.** The mappings and rationales below restate the historical items, so this "
            "surface is sealed with the list itself. The counts, rates, origin strata and exposure "
            "declaration carry no historical content and are published separately in "
            f"`{COUNTS_JSON}` and `{COUNTS_MARKDOWN}`."),
        "task_id": task_id, "task_context_ref": derived["task_context_ref"],
        "comparison_id": comparison["comparison_id"], "route": comparison["route"],
        "judged_by": comparison["judged_by"], "gate": comparison["gate"],
        "intake": {k: intake[k] for k in ("intake_id", "provided_by", "provided_at", "provenance_form",
                                          "completeness_attestation", "item_count", "content_sha256",
                                          "recorded_at", "recorded_by", "ambiguities")},
        "freeze": intake["freeze"],
        "derived_set": dict(
            {k: derived[k] for k in ("statement", "criteria_count", "pinned_seq", "rule_set_refs",
                                     "by_stratum", "repeated_variants", "excluded_as_a_repeated_variant",
                                     "excluded_as_pruned_pool_items", "payload_digest")},
            digest_when_compared=comparison["derived_set_digest"],
            unchanged_since_the_comparison=not drift,
            drift_note=None if not drift else
            "the export payload folds differently than when the comparison was judged; the criteria "
            "themselves are pinned at the task sequence above, so a difference here comes from records "
            "outside that pin, such as a claim admitted after the comparison"),
        "counts": counts,
        "mappings": mappings,
        "origin_stratified": _origin_view(comparison["comparisons"], derived, counts),
        "exposure": exposure,
        "limits": [
            "The historical comparison does not replace an independent assessment of criterion quality "
            "and source support (§12.2).",
            "A `missed` item may be a statement about the historical item's documentation rather than a "
            "failure of the derivation; the rationale per item says which.",
            "No binary success claim is made here: §12.2 asks for a minimum recovery requirement "
            "registered before unsealing, and this report does not register one after the fact.",
        ] + (["This case inherits an existing registry and its exposure lineage. Its recovery is a "
              "descriptive assisted reading; the original case's comparison remains the original result."]
             if exposure["inherited_from"] else []),
        "reported_at": utc_now(),
    }


def public_counts(report_record: dict[str, Any]) -> dict[str, Any]:
    """The part of the report that carries no historical content, for a non-evaluator reader.

    WHY no per-item row survives here, not even a category: "item 3 is recovered by the molecular
    weight criterion" states what item 3 is about, and the derived criteria are public. Aggregates
    do not, so this surface is counts, rates, strata, exposure and digests -- the measurement
    without the list.
    """
    counts, origins = report_record["counts"], report_record["origin_stratified"]
    return {
        "schema_version": SCHEMA_VERSION, "report_kind": "recovery_counts",
        "visibility": vocab.require("field_visibility", "agent_visible"),
        "visibility_statement": (
            "Published surface. It carries no historical item, no per-item mapping and no rationale: "
            "only aggregate counts over the sealed list, which is the measurement itself."),
        "task_id": report_record["task_id"], "task_context_ref": report_record["task_context_ref"],
        "comparison_id": report_record["comparison_id"], "route": report_record["route"],
        "judged_by": {k: report_record["judged_by"].get(k) for k in ("role", "adapter_id", "model_id",
                                                                     "provider_family", "distinct_from",
                                                                     "supplied_by", "note")},
        "gate": {"ok": report_record["gate"]["ok"], "checks": report_record["gate"]["checks"]},
        "intake": {k: report_record["intake"][k] for k in ("intake_id", "item_count", "content_sha256",
                                                           "provenance_form", "completeness_attestation",
                                                           "provided_by", "provided_at", "recorded_at")},
        "freeze": {k: report_record["freeze"][k] for k in ("rule_set_refs", "frozen_at", "frozen_at_seq")},
        "freeze_acceptance": [{k: snapshot[k] for k in ("rule_set_ref", "acceptance_label", "acceptance_reasons",
                                                        "preregistration_ref")}
                              for snapshot in report_record["freeze"]["snapshots"]],
        "derived_set": report_record["derived_set"],
        "n_historical": counts["n_historical"],
        "categories": counts["categories"],
        "categories_partition_the_historical_items": counts["partitions"],
        "rates": counts["rates"],
        "extra": {k: counts["extra"][k] for k in ("statement", "count_by_meaning", "count_by_criterion",
                                                  "by_stratum")},
        "derived_meanings_matched": counts["derived_meanings_matched"],
        "repeated_variants_in_the_derived_set": counts["repeated_variants_in_the_derived_set"],
        "origin_stratified": {
            "statement": origins["statement"],
            "derived_criteria_by_stratum": origins["derived_criteria_by_stratum"],
            "restatement_strata": origins["restatement_strata"],
            "independent_strata": origins["independent_strata"],
            "recovered_by_stratum": {stratum: {category: row[category] for category in CATEGORIES}
                                     for stratum, row in origins["recovered_by_stratum"].items()},
            "independently_derived_only": {k: v for k, v in origins["independently_derived_only"].items()
                                           if k != "items_recovered_only_by_a_restatement"},
            "items_recovered_only_by_a_restatement": len(
                origins["independently_derived_only"]["items_recovered_only_by_a_restatement"]),
        },
        "exposure": {k: v for k, v in report_record["exposure"].items()
                     if k not in ("reads_before_the_freeze", "reads_by_a_deriving_role")},
        "exposure_reads": {"before_the_freeze": len(report_record["exposure"]["reads_before_the_freeze"]),
                           "by_a_deriving_role": len(report_record["exposure"]["reads_by_a_deriving_role"]),
                           "logged": report_record["exposure"]["reads_logged"]},
        "limits": report_record["limits"],
    }


# --- rendering and writing -------------------------------------------------------------------

def _judged(judged_by: dict[str, Any], route: str) -> str:
    if route == "supplied_by_the_evaluator":
        return f"proposed outside this process by {_inline((judged_by.get('supplied_by') or {}).get('id'))}"
    return (f"{_inline(judged_by.get('model_id'))} in role `{judged_by.get('role')}`"
            f" (adapter {_inline(judged_by.get('adapter_id'))})")


def _inline(value: Any) -> str:
    if value is None or value == [] or value == {}:
        return "_none_"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return ", ".join(_inline(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{key}: {_inline(item)}" for key, item in value.items())
    return str(value)


def render_markdown(report_record: dict[str, Any]) -> str:
    """The evaluator-only report: every mapping with its rationale and its reported differences."""
    counts, exposure = report_record["counts"], report_record["exposure"]
    lines = [f"# Primary CQA recovery — {report_record['task_context_ref']}", "",
             f"> {report_record['visibility_statement']}", "",
             f"- comparison `{report_record['comparison_id']}`: "
             f"{_judged(report_record['judged_by'], report_record['route'])}",
             f"- intake `{report_record['intake']['intake_id']}`: {report_record['intake']['item_count']} items, "
             f"{report_record['intake']['provenance_form']}, completeness "
             f"{report_record['intake']['completeness_attestation']}, sha256 "
             f"`{report_record['intake']['content_sha256'][:16]}…`",
             f"- frozen criteria: {_inline(report_record['freeze']['rule_set_refs'])} at seq "
             f"{report_record['freeze']['frozen_at_seq']}; derived set "
             f"{report_record['derived_set']['criteria_count']} criteria pinned at seq "
             f"{report_record['derived_set']['pinned_seq']}", "",
             "## Recovery", "",
             f"- **exact**: {counts['rates']['exact']['as_text']}",
             f"- **exact or near-equivalent**: {counts['rates']['exact_or_near_equivalent']['as_text']}",
             f"- raw counts: " + _inline(counts["categories"]),
             f"- the three categories partition the {counts['n_historical']} historical items: "
             f"{_inline(counts['partitions'])}",
             f"- extra on the derived side: {counts['extra']['count_by_meaning']} meanings "
             f"({counts['extra']['count_by_criterion']} criteria). {counts['extra']['statement']}", "",
             "## Mapping per historical item", ""]
    for record in report_record["mappings"]:
        lines += [f"### {record['historical_item_ref']} — {record['category']}", "",
                  f"- historical item as given: {_inline(record['historical_label'])}",
                  f"- definition as given: {_inline(record['historical_definition_as_given'])}",
                  f"- threshold as given: {_inline(record['historical_threshold_as_given'])}",
                  f"- derived criteria cited: {_inline(record['derived_attribute_refs'])} "
                  f"({_inline(record['derived_names'])})",
                  f"- mapping shape: {record['mapping_shape']}"
                  + (f"; coverage: {record['covers_historical_meaning']}"
                     if record.get("covers_historical_meaning") else ""),
                  f"- origin of the matching criteria: {_inline(record['derived_strata'])}",
                  f"- match basis: {_inline(record['match_basis'])}",
                  f"- differences reported: {_inline(record['difference_kinds']) }"
                  f" (facets: {_inline(record['differing_facets'])})",
                  f"- rationale: {record['rationale']}", ""]
        for facet in FACETS:
            judgement = (record["facets"] or {}).get(facet)
            if isinstance(judgement, dict) and judgement.get("agrees") is False:
                detail = f"historical {_inline(judgement.get('historical'))} vs derived " \
                         f"{_inline(judgement.get('derived'))}; " if facet == "threshold" else ""
                lines.append(f"  - **{facet} differs**: {detail}{_inline(judgement.get('note'))}")
        lines.append("")
    origins = report_record["origin_stratified"]
    lines += ["## Origin-stratified view", "", origins["statement"], "",
              f"- derived criteria by origin: {_inline(origins['derived_criteria_by_stratum'])}",
              f"- recovered by origin: "
              + _inline({stratum: {category: row[category] for category in CATEGORIES}
                         for stratum, row in origins["recovered_by_stratum"].items()}),
              f"- independently derived only: exact "
              f"{origins['independently_derived_only']['exact_as_text']}, recovered "
              f"{origins['independently_derived_only']['recovered_as_text']}",
              f"- items recovered only by a restatement: "
              f"{_inline(origins['independently_derived_only']['items_recovered_only_by_a_restatement'])}", "",
              "## Exposure declaration", "", exposure["statement"], "",
              f"- the coordinator or a deriving agent saw the list before the freeze: "
              f"{_inline(exposure['coordinator_or_deriving_agent_saw_the_list_before_the_freeze'])}",
              f"- recovery view: **{exposure['recovery_view']}**",
              f"- reading kind: {_inline(exposure.get('reading_kind'))}; "
              f"inherited source cases: {_inline(exposure.get('inherited_from'))}",
              f"- logged reads: {exposure['reads_logged']} "
              f"({len(exposure['reads_before_the_freeze'])} before the freeze, "
              f"{len(exposure['reads_by_a_deriving_role'])} by a deriving role)",
              f"- declared on the confirming decisions: {_inline(exposure['declared_on_confirming_decisions'])}",
              f"- no person confirmed, so no declaration exists: "
              f"{_inline(exposure['criteria_with_no_confirming_decision'])}", "",
              "## Limits", ""] + [f"- {limit}" for limit in report_record["limits"]] + [""]
    return "\n".join(lines)


def render_counts(summary: dict[str, Any]) -> str:
    """The published counterpart: the measurement without the list."""
    origins = summary["origin_stratified"]
    return "\n".join([
        f"# Primary CQA recovery — counts ({summary['task_context_ref']})", "",
        f"> {summary['visibility_statement']}", "",
        f"- comparison `{summary['comparison_id']}`: {_judged(summary['judged_by'], summary['route'])}; "
        f"deriving roles bound to {_inline(summary['judged_by']['distinct_from'])}",
        f"- intake `{summary['intake']['intake_id']}`: {summary['intake']['item_count']} items, sha256 "
        f"`{summary['intake']['content_sha256'][:16]}…`, recorded {summary['intake']['recorded_at']}",
        f"- frozen criteria {_inline(summary['freeze']['rule_set_refs'])} at seq "
        f"{summary['freeze']['frozen_at_seq']}; acceptance "
        f"{_inline([s['acceptance_label'] for s in summary['freeze_acceptance']])}",
        f"- derived set: {summary['derived_set']['criteria_count']} criteria by origin "
        f"{_inline({k: len(v) for k, v in summary['derived_set']['by_stratum'].items()})}",
        "", "## Recovery", "",
        f"- **exact**: {summary['rates']['exact']['as_text']}",
        f"- **exact or near-equivalent**: {summary['rates']['exact_or_near_equivalent']['as_text']}",
        f"- raw counts over {summary['n_historical']} historical items: {_inline(summary['categories'])} "
        f"(partition: {_inline(summary['categories_partition_the_historical_items'])})",
        f"- extra on the derived side: {summary['extra']['count_by_meaning']} meanings, "
        f"{summary['extra']['count_by_criterion']} criteria; {summary['extra']['statement']}",
        f"- derived meanings matched: {summary['derived_meanings_matched']}; registered more than once "
        f"as one quantity: {_inline(list(summary['repeated_variants_in_the_derived_set'].values()))}",
        "", "## Origin-stratified view", "", origins["statement"], "",
        f"- derived criteria by origin: {_inline(origins['derived_criteria_by_stratum'])}",
        f"- recovered by origin: {_inline(origins['recovered_by_stratum'])}",
        f"- independently derived only: {_inline(origins['independently_derived_only'])}",
        f"- items recovered only by a restatement: {origins['items_recovered_only_by_a_restatement']}",
        "", "## Exposure", "",
        f"- the coordinator or a deriving agent saw the list before the freeze: "
        f"{_inline(summary['exposure']['coordinator_or_deriving_agent_saw_the_list_before_the_freeze'])}",
        f"- recovery view: **{summary['exposure']['recovery_view']}**",
        f"- reading kind: {_inline(summary['exposure'].get('reading_kind'))}; "
        f"inherited source cases: {_inline(summary['exposure'].get('inherited_from'))}",
        f"- logged reads: {_inline(summary['exposure_reads'])}",
        f"- declared on the confirming decisions: "
        f"{_inline(summary['exposure']['declared_on_confirming_decisions'])}",
        f"- no person confirmed, so no declaration exists: "
        f"{_inline(summary['exposure']['criteria_with_no_confirming_decision'])}",
        "", "## Limits", ""] + [f"- {limit}" for limit in summary["limits"]] + [""])


def manifest(report_record: dict[str, Any], summary: dict[str, Any], *, store_root: str,
             digests: dict[str, dict[str, Any]], implementation: dict[str, Any],
             written_at: str | None = None) -> dict[str, Any]:
    """Refs, digests and the visibility of each written file, in the shape §11.2 uses."""
    return {
        "schema_version": SCHEMA_VERSION, "report_kind": "recovery_manifest",
        "task": {"task_id": report_record["task_id"], "task_context_ref": report_record["task_context_ref"]},
        "comparison_id": report_record["comparison_id"], "route": report_record["route"],
        "intake": {"intake_id": report_record["intake"]["intake_id"],
                   "item_count": report_record["intake"]["item_count"],
                   "content_sha256": report_record["intake"]["content_sha256"]},
        "freeze": summary["freeze"], "freeze_acceptance": summary["freeze_acceptance"],
        "derived_set_digest": report_record["derived_set"]["payload_digest"],
        "derived_set_pinned_seq": report_record["derived_set"]["pinned_seq"],
        "counts": summary["categories"], "rates": summary["rates"],
        "recovery_view": summary["exposure"]["recovery_view"],
        "gate": {"ok": report_record["gate"]["ok"], "checks": report_record["gate"]["checks"]},
        "file_visibility": {**{name: ("evaluator_only" if name in EVALUATOR_ONLY_FILES else "agent_visible")
                               for name in digests}, MANIFEST_JSON: "agent_visible"},
        "file_digests": digests,
        "payload_digest": {"sha256": sha256_hex(summary),
                           "over": "the published counts payload, which carries no historical item"},
        "store": {"root": store_root},
        "implementation": implementation,
        "export_metadata": {"tool": "mas recovery report", "written_at": written_at or utc_now(),
                            "note": "written_at is excluded from payload_digest on purpose"},
    }


def write(report_record: dict[str, Any], out_dir: str | Path, *, store_root: str = "",
          implementation: dict[str, Any] | None = None) -> dict[str, Any]:
    """Write the evaluator-only report, its published counts, and the manifest binding both.

    Refuses a destination inside a published directory: the evaluator-only files restate the sealed
    items, and the repository's reviewable export is the one place a reviewer is told to read.
    """
    directory = Path(out_dir)
    if any(part in PUBLISHED_DIRECTORIES for part in directory.resolve().parts):
        raise RecoveryError("evaluator_only_destination",
                            f"{directory} is inside a published directory "
                            f"({', '.join(PUBLISHED_DIRECTORIES)}); the mappings restate the sealed items and "
                            f"may not be written where reviewers read")
    summary = public_counts(report_record)
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        REPORT_JSON: canonical_bytes(report_record) + b"\n",
        REPORT_MARKDOWN: render_markdown(report_record).encode("utf-8"),
        COUNTS_JSON: canonical_bytes(summary) + b"\n",
        COUNTS_MARKDOWN: render_counts(summary).encode("utf-8"),
    }
    digests = {}
    for name, data in files.items():
        (directory / name).write_bytes(data)
        digests[name] = {"sha256": criteria_export.sha256_hex_bytes(data), "bytes": len(data)}
    record = manifest(report_record, summary, store_root=store_root, digests=digests,
                      implementation=implementation or {})
    manifest_bytes = json.dumps(record, indent=1, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    (directory / MANIFEST_JSON).write_bytes(manifest_bytes)
    record["paths"] = {name: str(directory / name) for name in list(files) + [MANIFEST_JSON]}
    return record
