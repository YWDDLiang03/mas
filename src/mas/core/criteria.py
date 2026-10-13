"""Criterion Registry (C10): Attribute and Rule records, invariants, confirmed rule sets (design §4.10)."""

from __future__ import annotations

from typing import Any

from . import review, vocab
from .canonical import sha256_hex
from .ids import slug
from .runtime import Core

MEASUREMENT_KINDS = ("quantitative", "ordinal", "categorical", "qualitative_determination")
DIRECTIONS = ("higher_better", "lower_better", "within_range", "target_value", "non_directional", "undetermined")
RULE_KINDS = ("hard_exclusion", "preference", "exploratory_consideration")
CUTOFF_BASES = ("measured_distribution", "regulatory_or_standard_reference", "source_stated_value",
                "expert_set", "task_constraint", "none_evidence_insufficient")
COMPARATORS = (">=", "<=", ">", "<", "==", "in", "not_in")
ON_STATE_POLICIES = ("unknown_no_penalty", "unknown_blocks_recommendation", "route_to_human", "exclude")
AGGREGATIONS = ("max", "min", "median", "consensus")
# Bases a value may be determined on. `predicted` is never mixed with the others inside one
# attribute: a predicted value standing in for a measurement is a surrogate inside a verdict
# (design §4.11), so a predicted quantity needs its own attribute and its own rule.
#
# `curated` is an expert assertion a database carries with its references — ChEMBL's
# mechanism-of-action table states that a compound engages a target, which is documented
# rather than measured, and the tool declares that basis itself (`evidence.determination_basis`).
# It is registered here so that an attribute *may* ask for it; it is deliberately absent from
# `assessor.DEFAULT_DETERMINATION_BASES`, so an attribute that does not name it sees no curated
# claim at all rather than counting an assertion as a measurement.
DETERMINATION_BASES = ("measured", "derived", "predicted", "simulated", "curated")


class InvariantViolation(ValueError):
    """A typed registry finding (design §4.10); never silently corrected."""

    def __init__(self, finding_class: str, message: str):
        super().__init__(f"{finding_class}: {message}")
        self.finding_class = finding_class


def _choice(name: str, value: Any, allowed: tuple[str, ...]) -> None:
    if value not in allowed:
        raise InvariantViolation("schema", f"{name} must be one of {allowed}, got {value!r}")


def check_attribute(attr: dict[str, Any]) -> None:
    for field in ("name", "definition", "measurement_kind", "direction", "acceptable_value_sources", "evidence_request"):
        if not attr.get(field):
            raise InvariantViolation("schema", f"attribute needs {field}")
    _choice("measurement_kind", attr["measurement_kind"], MEASUREMENT_KINDS)
    _choice("direction", attr["direction"], DIRECTIONS)
    _choice("aggregation", attr.get("aggregation", "consensus"), AGGREGATIONS)
    if attr["measurement_kind"] == "quantitative" and not attr.get("unit"):
        raise InvariantViolation("units", f"quantitative attribute {attr['name']!r} has no unit")
    bases = attr.get("acceptable_determination_bases")
    if bases is not None:
        if not isinstance(bases, list) or not bases:
            raise InvariantViolation("schema", "acceptable_determination_bases is a non-empty list when given")
        for basis in bases:
            _choice("acceptable_determination_bases", basis, DETERMINATION_BASES)
        if "predicted" in bases and len(bases) > 1:
            # A predicted value standing in for a measurement is a surrogate inside a verdict
            # (design §4.11): a predicted quantity is its own attribute, with its own rule.
            raise InvariantViolation("schema", f"attribute {attr['name']!r} accepts predicted values alongside "
                                              f"{sorted(set(bases) - {'predicted'})}; give predicted values their own attribute")
    request = attr["evidence_request"]
    if not request.get("capability") or not request.get("question_kind"):
        raise InvariantViolation("schema", "evidence_request needs capability and question_kind")


def check_rule(rule: dict[str, Any], attr: dict[str, Any]) -> None:
    _choice("rule_kind", rule.get("rule_kind"), RULE_KINDS)
    _choice("cutoff_basis", rule.get("cutoff_basis"), CUTOFF_BASES)
    for policy in ("on_missing", "on_inapplicable", "on_conflict"):
        _choice(policy, rule.get(policy, "unknown_blocks_recommendation"), ON_STATE_POLICIES)
        if rule.get(policy) == "exclude" and rule["rule_kind"] != "hard_exclusion":
            raise InvariantViolation("schema", f"{policy}: exclude is only for hard exclusions")
    cutoff = rule.get("cutoff")
    if rule.get("predicate_form", "threshold") not in ("threshold", "ordering", "range_membership", "categorical_membership",
                                                       "qualitative_judgment"):
        raise InvariantViolation("schema", f"unknown predicate_form {rule.get('predicate_form')!r}")
    if rule.get("predicate_form") == "ordering" and rule["rule_kind"] != "preference":
        raise InvariantViolation("schema", "an ordering rule ranks candidates, so it must be a preference")
    if rule["cutoff_basis"] == "none_evidence_insufficient":
        if cutoff:
            raise InvariantViolation("arbitrary_cutoff", "none_evidence_insufficient with a cutoff value")
        return
    if not cutoff:
        raise InvariantViolation("schema", "rule needs a cutoff or cutoff_basis none_evidence_insufficient")
    _choice("comparator", cutoff.get("comparator"), COMPARATORS)
    if rule.get("predicate_form") == "categorical_membership" or attr["measurement_kind"] == "categorical":
        if cutoff["comparator"] not in ("in", "not_in", "=="):
            raise InvariantViolation("schema", "a categorical rule uses in, not_in, or ==")
        values = cutoff.get("value") if isinstance(cutoff.get("value"), list) else [cutoff.get("value")]
        if not values or not all(isinstance(v, (str, bool)) for v in values):
            raise InvariantViolation("schema", "a categorical cutoff lists categories (strings or booleans)")
        return
    if cutoff["comparator"] in ("in", "not_in"):
        raise InvariantViolation("schema", "in and not_in are for categorical rules")
    if not isinstance(cutoff.get("value"), (int, float)) or isinstance(cutoff.get("value"), bool):
        raise InvariantViolation("schema", "cutoff value must be a number")
    if attr["measurement_kind"] == "quantitative" and cutoff.get("unit") != attr.get("unit"):
        raise InvariantViolation("units", f"cutoff unit {cutoff.get('unit')!r} differs from attribute unit {attr.get('unit')!r}")


def _versions(core: Core, task_id: str, kind: str, base_id: str) -> list[dict[str, Any]]:
    return [e.payload for e in core.journal.replay(task_id)
            if e.event_type == "criterion.version_proposed" and e.payload["kind"] == kind and e.payload["id"] == base_id]


def propose(core: Core, task_id: str, attribute: dict[str, Any], rule: dict[str, Any], *,
            by: dict[str, Any], derivation_configuration: str = "reference_disclosed",
            dispute: dict[str, Any] | None = None) -> tuple[str, str]:
    """Propose one attribute version and one rule version, and raise their confirmation item.

    Proposals enter as `proposed`; templates and people never pre-approve them.
    Returns (attribute_ref@v, rule_ref@v).
    """
    vocab.require("derivation_configuration", derivation_configuration)
    check_attribute(attribute)
    check_rule(rule, attribute)
    attr_id = attribute.get("attribute_id") or f"attr_{slug(attribute['name'])}"
    rule_id = rule.get("rule_id") or f"rule_{slug(attribute['name'])}"
    attr_version = len(_versions(core, task_id, "attribute", attr_id)) + 1
    rule_version = len(_versions(core, task_id, "rule", rule_id)) + 1
    attr_ref, rule_ref = f"{attr_id}@v{attr_version}", f"{rule_id}@v{rule_version}"
    attr_record = dict(attribute, attribute_id=attr_id, version=attr_version, status="proposed",
                       derivation_configuration=derivation_configuration, proposed_by=by)
    attr_record.setdefault("aggregation", "consensus")
    rule_record = dict(rule, rule_id=rule_id, version=rule_version, attribute_ref=attr_ref, status="proposed",
                       proposed_by=by)
    for policy in ("on_missing", "on_inapplicable", "on_conflict"):
        rule_record.setdefault(policy, "unknown_blocks_recommendation")
    rule_record.setdefault("predicate_form", "threshold")
    rule_record.setdefault("applies_to_result_kind", "all_pass_set")
    for kind, base_id, version, record in (("attribute", attr_id, attr_version, attr_record),
                                           ("rule", rule_id, rule_version, rule_record)):
        artifact_id = core.artifacts.put(kind, record)
        core.journal.append(task_id, "criterion.version_proposed", actor=by, ids={"task_id": task_id},
                            payload={"kind": kind, "id": base_id, "version": version, "artifact_id": artifact_id},
                            artifact_links=[{"kind": kind, "id": artifact_id, "version": version}],
                            summary=f"proposed {base_id}@v{version}")
    if dispute is not None:
        review.request(core, task_id, subject={"kind": "rule_version", "id": rule_ref, "version": rule_version,
                                               "attribute_ref": attr_ref},
                       why_expert_required="proposer and critic still disagree after one revision",
                       requested_by=by, inspection_bundle=dispute)
    elif needs_expert(rule_record):
        why = "hard_exclusion entering confirmed" if rule_record["rule_kind"] == "hard_exclusion" else "rule confirmation"
        if rule_record["cutoff_basis"] == "expert_set":
            why += "; cutoff_basis expert_set"
        review.request(core, task_id, subject={"kind": "rule_version", "id": rule_ref, "version": rule_version,
                                               "attribute_ref": attr_ref},
                       why_expert_required=why, requested_by=by)
    return attr_ref, rule_ref


def needs_expert(rule: dict[str, Any]) -> bool:
    """Trigger table (design §12.1): hard exclusions and expert-set cutoffs need an `hd_`;
    evidence-sourced preference rules proceed automatically, recorded and reversible."""
    return rule["rule_kind"] == "hard_exclusion" or rule["cutoff_basis"] in ("expert_set", "task_constraint")


def load(core: Core, ref: str, task_id: str) -> dict[str, Any]:
    """The record of an attribute or rule version proposed in a task."""
    base_id, version = ref.rsplit("@v", 1)
    kind = "attribute" if base_id.startswith("attr_") else "rule"
    for payload in _versions(core, task_id, kind, base_id):
        if payload["version"] == int(version):
            return core.artifacts.payload(payload["artifact_id"])
    raise KeyError(ref)


def chosen_after_results(ordering_method: dict[str, Any] | None) -> bool:
    """True for an ordering method derived from the results it will then rank (design §5.7).

    A symbolic expression is fitted on assessed cells, so the ranking rule was chosen after
    seeing the data: unless it was preregistered, the rule set is exploratory however many of
    its rules are confirmed. Without this, a fitted ordering method would inherit the
    `prespecified` label of the rules it was fitted on top of.
    """
    return (ordering_method or {}).get("kind") == "symbolic_expression"


def confirm_rule_set(core: Core, task_id: str, *, by: dict[str, Any], ordering_method: dict[str, Any] | None = None,
                     coverage_floor: float = 1.0, constants: list[dict[str, Any]] | None = None,
                     allow_pending: bool = False, defer_capabilities: tuple[str, ...] = (),
                     defer_reason: str = "", preregistration_ref: str | None = None) -> str:
    """Assemble `rules@v<n>` from the rule proposals that may enter it.

    A rule needing an expert enters only with an `hd_` approving it; a preference rule the
    trigger table lets proceed automatically enters with `confirmed_by: auto:trigger_table`.
    Proposals still awaiting a decision block the set unless `allow_pending` is given (for
    exploratory runs); they are then listed in `pending[]`, never silently dropped.
    """
    queue = review.items(core, [task_id])
    decided = {i["subject"]["id"]: i for i in queue.values()
               if i["subject"]["kind"] == "rule_version" and i["state"] == "decided"}
    open_refs = sorted(i["subject"]["id"] for i in queue.values()
                       if i["subject"]["kind"] == "rule_version" and i["state"] in ("open", "in_review"))
    if open_refs and not allow_pending:
        raise InvariantViolation("unconfirmed", f"{len(open_refs)} rule proposals await an expert decision")
    proposed = {}
    for event in core.journal.replay(task_id):
        if event.event_type == "criterion.version_proposed" and event.payload["kind"] == "rule":
            proposed[event.payload["id"]] = f"{event.payload['id']}@v{event.payload['version']}"   # latest version wins
    entries, deferred = [], []
    for rule_ref in sorted(proposed.values()):
        rule = load(core, rule_ref, task_id)
        capability = load(core, rule["attribute_ref"], task_id)["evidence_request"]["capability"]
        if capability in defer_capabilities:
            deferred.append({"rule_ref": rule_ref, "capability": capability, "reason": defer_reason})
            continue
        item = decided.get(rule_ref)
        if item is not None:
            if item["decision"] not in ("approve", "approve_with_edits"):
                continue
            confirmed_by = item["decision_id"]
        elif not needs_expert(rule):
            confirmed_by = "auto:trigger_table"
        else:
            continue
        attr = load(core, rule["attribute_ref"], task_id)
        entries.append({"attribute_ref": rule["attribute_ref"], "rule_ref": rule_ref, "rule_kind": rule["rule_kind"],
                        "confirmed_by": confirmed_by, "acceptable_value_sources": attr["acceptable_value_sources"],
                        "on_states": [rule["on_missing"], rule["on_inapplicable"], rule["on_conflict"]],
                        "cutoff_basis": rule["cutoff_basis"]})
    if not entries:
        raise InvariantViolation("unconfirmed", "no rule version may enter the set yet")
    existing = [e for e in core.journal.replay(task_id) if e.event_type == "criterion.version_approved"]
    version = len(existing) + 1
    admission_predicate = {"entries": [{k: e[k] for k in ("acceptable_value_sources", "on_states", "cutoff_basis")} for e in entries],
                           "coverage_floor": coverage_floor, "constants": constants or []}
    fitted_ordering = chosen_after_results(ordering_method) and not preregistration_ref
    acceptance_reasons = ([f"{len(open_refs)} rule proposals await an expert decision"] if open_refs else []) + \
                         (["the ordering method was fitted on the results it ranks"] if fitted_ordering else [])
    record = {"rule_set_ref": f"rules@v{version}", "task_id": task_id, "entries": entries,
              "ordering_method": ordering_method or {"kind": "weighted_preference", "weight_vector": {}, "tie_break": "candidate_id"},
              "coverage_floor": coverage_floor,
              "evidence_admission_predicate_hash": sha256_hex(admission_predicate),
              "confirmed_by": [e["confirmed_by"] for e in entries], "pending": open_refs, "deferred": deferred,
              "acceptance_label": vocab.require("acceptance_label", "exploratory" if acceptance_reasons else "prespecified"),
              "acceptance_reasons": acceptance_reasons, "preregistration_ref": preregistration_ref}
    artifact_id = core.artifacts.put("rule_set", record)
    core.journal.append(task_id, "criterion.version_approved", actor=by, ids={"task_id": task_id},
                        payload={"rule_set_ref": record["rule_set_ref"], "artifact_id": artifact_id,
                                 "hash": record["evidence_admission_predicate_hash"], "pending": open_refs},
                        artifact_links=[{"kind": "rule_set", "id": artifact_id, "version": version}],
                        summary=f"confirmed {record['rule_set_ref']} ({len(entries)} rules, {len(open_refs)} pending, "
                                f"{len(deferred)} deferred)")
    return record["rule_set_ref"]


def rule_set(core: Core, task_id: str, ref: str | None = None) -> dict[str, Any]:
    approvals = [e for e in core.journal.replay(task_id) if e.event_type == "criterion.version_approved"]
    if not approvals:
        raise KeyError(f"{task_id} has no confirmed rule set")
    chosen = approvals[-1] if ref is None else next(e for e in approvals if e.payload["rule_set_ref"] == ref)
    return core.artifacts.payload(chosen.payload["artifact_id"])


def registered_attributes(core: Core, task_id: str) -> list[dict[str, Any]]:
    """Latest version of every attribute proposed in a task."""
    latest: dict[str, dict[str, Any]] = {}
    for event in core.journal.replay(task_id):
        if event.event_type == "criterion.version_proposed" and event.payload["kind"] == "attribute":
            latest[event.payload["id"]] = core.artifacts.payload(event.payload["artifact_id"])
    return list(latest.values())


def evidence_key(attribute: dict[str, Any]) -> str:
    """Two attributes asking the same tool the same question are duplicates (registry invariant)."""
    request = attribute.get("evidence_request") or {}
    return sha256_hex({k: request.get(k) for k in ("capability", "question_kind", "parameters")}
                      if request.get("capability") != "literature_retrieval"
                      else {"name": (attribute.get("name") or "").strip().lower(), "unit": attribute.get("unit")})
