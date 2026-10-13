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
                "expert_set", "none_evidence_insufficient")
COMPARATORS = (">=", "<=", ">", "<", "==")
ON_STATE_POLICIES = ("unknown_no_penalty", "unknown_blocks_recommendation", "route_to_human", "exclude")
AGGREGATIONS = ("max", "min", "consensus")


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
    if rule["cutoff_basis"] == "none_evidence_insufficient":
        if cutoff:
            raise InvariantViolation("arbitrary_cutoff", "none_evidence_insufficient with a cutoff value")
        return
    if not cutoff:
        raise InvariantViolation("schema", "rule needs a cutoff or cutoff_basis none_evidence_insufficient")
    _choice("comparator", cutoff.get("comparator"), COMPARATORS)
    if not isinstance(cutoff.get("value"), (int, float)) or isinstance(cutoff.get("value"), bool):
        raise InvariantViolation("schema", "cutoff value must be a number")
    if attr["measurement_kind"] == "quantitative" and cutoff.get("unit") != attr.get("unit"):
        raise InvariantViolation("units", f"cutoff unit {cutoff.get('unit')!r} differs from attribute unit {attr.get('unit')!r}")


def _versions(core: Core, task_id: str, kind: str, base_id: str) -> list[dict[str, Any]]:
    return [e.payload for e in core.journal.replay(task_id)
            if e.event_type == "criterion.version_proposed" and e.payload["kind"] == kind and e.payload["id"] == base_id]


def propose(core: Core, task_id: str, attribute: dict[str, Any], rule: dict[str, Any], *,
            by: dict[str, Any], derivation_configuration: str = "reference_disclosed") -> tuple[str, str]:
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
    why = "hard_exclusion entering confirmed" if rule_record["rule_kind"] == "hard_exclusion" else "rule confirmation"
    if rule_record["cutoff_basis"] == "expert_set":
        why += "; cutoff_basis expert_set"
    review.request(core, task_id, subject={"kind": "rule_version", "id": rule_ref, "version": rule_version,
                                           "attribute_ref": attr_ref},
                   why_expert_required=why, requested_by=by)
    return attr_ref, rule_ref


def load(core: Core, ref: str, task_id: str) -> dict[str, Any]:
    """The record of an attribute or rule version proposed in a task."""
    base_id, version = ref.rsplit("@v", 1)
    kind = "attribute" if base_id.startswith("attr_") else "rule"
    for payload in _versions(core, task_id, kind, base_id):
        if payload["version"] == int(version):
            return core.artifacts.payload(payload["artifact_id"])
    raise KeyError(ref)


def confirm_rule_set(core: Core, task_id: str, *, by: dict[str, Any], ordering_method: dict[str, Any] | None = None,
                     coverage_floor: float = 1.0, constants: list[dict[str, Any]] | None = None) -> str:
    """Assemble `rules@v<n>` from every rule version approved by an expert decision.

    A rule enters the set only with an `hd_` approving it; every proposed rule must be
    decided first. Returns the rule-set reference.
    """
    queue = review.items(core, [task_id])
    rule_items = [i for i in queue.values() if i["subject"]["kind"] == "rule_version" and i["state"] != "withdrawn"]
    open_items = [i for i in rule_items if i["state"] != "decided"]
    if open_items:
        raise InvariantViolation("unconfirmed", f"{len(open_items)} rule proposals await an expert decision")
    approved = [i for i in rule_items if i["decision"] in ("approve", "approve_with_edits")]
    if not approved:
        raise InvariantViolation("unconfirmed", "no rule version has been approved")
    entries = []
    for item in sorted(approved, key=lambda i: i["subject"]["id"]):
        rule = load(core, item["subject"]["id"], task_id)
        attr = load(core, rule["attribute_ref"], task_id)
        entries.append({"attribute_ref": rule["attribute_ref"], "rule_ref": item["subject"]["id"],
                        "rule_kind": rule["rule_kind"], "confirmed_by": item["decision_id"],
                        "acceptable_value_sources": attr["acceptable_value_sources"],
                        "on_states": [rule["on_missing"], rule["on_inapplicable"], rule["on_conflict"]],
                        "cutoff_basis": rule["cutoff_basis"]})
    existing = [e for e in core.journal.replay(task_id) if e.event_type == "criterion.version_approved"]
    version = len(existing) + 1
    admission_predicate = {"entries": [{k: e[k] for k in ("acceptable_value_sources", "on_states", "cutoff_basis")} for e in entries],
                           "coverage_floor": coverage_floor, "constants": constants or []}
    record = {"rule_set_ref": f"rules@v{version}", "task_id": task_id, "entries": entries,
              "ordering_method": ordering_method or {"kind": "all_pass_set", "tie_break": "candidate_id"},
              "coverage_floor": coverage_floor,
              "evidence_admission_predicate_hash": sha256_hex(admission_predicate),
              "confirmed_by": [e["confirmed_by"] for e in entries], "preregistration_ref": None}
    artifact_id = core.artifacts.put("rule_set", record)
    core.journal.append(task_id, "criterion.version_approved", actor=by, ids={"task_id": task_id},
                        payload={"rule_set_ref": record["rule_set_ref"], "artifact_id": artifact_id,
                                 "hash": record["evidence_admission_predicate_hash"]},
                        artifact_links=[{"kind": "rule_set", "id": artifact_id, "version": version}],
                        summary=f"confirmed {record['rule_set_ref']} ({len(entries)} rules)")
    return record["rule_set_ref"]


def rule_set(core: Core, task_id: str, ref: str | None = None) -> dict[str, Any]:
    approvals = [e for e in core.journal.replay(task_id) if e.event_type == "criterion.version_approved"]
    if not approvals:
        raise KeyError(f"{task_id} has no confirmed rule set")
    chosen = approvals[-1] if ref is None else next(e for e in approvals if e.payload["rule_set_ref"] == ref)
    return core.artifacts.payload(chosen.payload["artifact_id"])
