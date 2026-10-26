"""Task-defined candidate selection shared by execution and result readers."""

from __future__ import annotations

from collections import Counter
from typing import Any


DECISION_READING_VERSION = 7
SELECTION_POLICY = "selection_reporting_v3"
SELECTION_DECISIONS = ("eligible", "evidence_incomplete", "excluded", "incomplete", "not_ready")
EVIDENCE_PROFILES = ("complete", "partial", "none", "unknown", "failed")


def requirement_roles(entries: list[dict[str, Any]], required_evidence_refs: list[str]) -> dict[str, Any]:
    """Describe admission and scoring as independent uses of frozen criteria."""
    conditions = {row["rule_ref"] for row in entries if row.get("rule_kind") == "hard_exclusion"}
    evidence = set(required_evidence_refs)
    scoring = {row["rule_ref"] for row in entries if row.get("rule_kind") == "preference"}
    context = {row["rule_ref"] for row in entries if row.get("rule_kind") == "exploratory_consideration"}
    refs = {row["rule_ref"] for row in entries}
    roles = {ref: {"condition_requirement": ref in conditions, "evidence_requirement": ref in evidence,
                   "prioritization": ref in scoring, "contextual": ref in context} for ref in refs}
    return {"roles": roles, "summary": {
        "total": len(conditions | evidence), "condition_count": len(conditions),
        "evidence_count": len(evidence), "condition_evidence_overlap": len(conditions & evidence),
        "scoring_overlap_count": len((conditions | evidence) & scoring),
        "scoring_count": len(scoring), "unique_decision_rule_count": len(conditions | (evidence & refs) | scoring),
        "unbound_evidence_count": len(evidence - refs)}}


def evidence_profile(qualification: dict[str, Any]) -> dict[str, Any]:
    """Describe recorded support, keeping mandatory and observation counts separate."""
    fields = {"mandatory_met": "hard_passed", "mandatory_total": "hard_total",
              "required_available": "required_direct_answered", "required_total": "required_total"}
    counts = {key: qualification.get(source) for key, source in fields.items()}
    counts["mandatory_total"] = qualification.get("applicable_hard_count", counts["mandatory_total"])
    known = all(isinstance(value, int) and not isinstance(value, bool) and value >= 0
                for value in counts.values())
    failed = (qualification.get("state") == "rejected" or bool(qualification.get("failed_hard_rule_refs"))
              or (isinstance(qualification.get("hard_failed"), int) and qualification["hard_failed"] > 0))
    if failed:
        state = "failed"
    elif not known:
        state = "unknown"
    else:
        mandatory, observations = counts["mandatory_met"], counts["required_available"]
        mandatory_total, required_total = counts["mandatory_total"], counts["required_total"]
        if mandatory > mandatory_total or observations > required_total or not (mandatory_total or required_total):
            state = "unknown"
        elif mandatory == mandatory_total and observations == required_total:
            state = "complete"
        elif mandatory or observations:
            state = "partial"
        else:
            state = "none"
    return {"state": state, **counts}


def eligibility_reading(entry: dict[str, Any], rules: dict[str, dict[str, Any]], *,
                        legacy: bool = False,
                        rule_assessments: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    q = entry.get("qualification")
    q = q if isinstance(q, dict) else {}
    state = q.get("state") or entry.get("qualification_state") or entry.get("qualification")
    if not isinstance(state, str):
        state = None
    failed = q.get("failed_hard_rule_refs") or []
    blocked = q.get("blocking_hard_rule_refs") or []
    missing = q.get("missing_direct_required_rule_refs") or []
    if legacy or not q:
        code = "historical_policy" if legacy else "reason_not_recorded"
        description = ("Eligibility was not established under the current policy in this saved evaluation."
                       if legacy else "A detailed eligibility reason was not recorded.")
    elif state == "rejected":
        code, description = "mandatory_failure", "Direct evidence confirms that a required condition is not met."
    elif state == "not_ready":
        code, description = "criteria_not_ready", "Define and verify the task's eligibility requirements before assessment."
    elif state == "qualified":
        code, description = "requirements_met", "All eligibility requirements are satisfied: required conditions are met and required direct evidence is available."
    elif blocked and missing:
        code, description = "mandatory_and_required_unresolved", "Eligibility requirements have gaps in both condition checks and required direct evidence."
    elif blocked:
        code, description = "mandatory_unresolved", "A required condition needs supporting evidence."
    elif missing:
        code, description = "required_observations_unresolved", "Required conditions are met; the required direct evidence is incomplete."
    elif state == "unassessed":
        code, description = "not_assessed", "Eligibility has not been assessed."
    else:
        code, description = "reason_not_recorded", "A detailed eligibility reason was not recorded."
    issues = []
    for role, refs in (("mandatory_failure", failed), ("mandatory", blocked), ("required_observation", missing)):
        for ref in refs:
            rule = rules.get(ref, {})
            attribute = rule.get("attribute_ref")
            cell = (rule_assessments or {}).get(ref)
            # A saved attribute summary can contain another rule's verdict. Use
            # the exact assessment when available; retain snapshot-only reading.
            verdict = cell.get("verdict") if cell is not None else (entry.get("verdicts") or {}).get(attribute)
            issue = {"unknown_missing": "no_usable_direct_evidence", "unknown_conflicted": "conflicting_evidence",
                     "unknown_unresolvable": "interpretation_unresolved", "not_assessed": "not_assessed",
                     "inapplicable": "not_applicable", None: "assessment_record_unavailable"}.get(verdict, "direct_evidence_unresolved")
            if role == "mandatory_failure":
                issue = "confirmed_failure"
            elif cell is not None and cell.get("tool_error_ref"):
                issue = "tool_error"
            elif cell is not None and cell.get("not_assessed_reason"):
                issue = "not_assessed"
            issues.append({"rule_ref": ref, "attribute_ref": attribute, "name": rule.get("name") or ref,
                           "role": role, "issue": issue, "verdict": verdict})
    names = "; ".join(dict.fromkeys(issue["name"] for issue in issues))
    reading = {"state": state, "reason_code": code, "description": description,
            "reason": description + (" " + names + "." if names else ""), "issues": issues,
            "mandatory_passed": q.get("hard_passed"), "mandatory_total": q.get("hard_total"),
            "required_supported": q.get("required_direct_answered"), "required_total": q.get("required_total"),
            "evidence_profile": evidence_profile(q),
            "scope": "saved_evaluation"}
    return refine_evidence_reason(reading)


def refine_evidence_reason(reading: dict[str, Any]) -> dict[str, Any]:
    """Choose a primary reason from recorded evidence states, retaining every issue."""
    if reading["state"] != "pending" or reading["reason_code"] == "historical_policy":
        return reading
    issues = {item["issue"] for item in reading["issues"]}
    primary = None
    if issues & {"tool_error", "not_assessed", "assessment_record_unavailable"}:
        primary = ("assessment_incomplete", "A required assessment is incomplete, failed or unavailable in the saved record.")
    elif "conflicting_evidence" in issues:
        primary = ("required_evidence_conflicted", "Conflicting evidence prevents a required determination.")
    elif "interpretation_unresolved" in issues:
        primary = ("required_interpretation_unresolved", "A required observation lacks a resolved interpretation method.")
    elif "direct_evidence_unresolved" in issues:
        primary = ("direct_evidence_requirement_not_met", "An available value does not establish the required direct-evidence determination.")
    if primary:
        reading["reason_code"], reading["description"] = primary
        names = "; ".join(dict.fromkeys(item["name"] for item in reading["issues"]))
        reading["reason"] = reading["description"] + (" " + names + "." if names else "")
    return reading


def eligibility_counts(readings: list[dict[str, Any]]) -> dict[str, Any]:
    """Mutually exclusive reason groups; per-rule counts may overlap."""
    groups = Counter(reading["reason_code"] for reading in readings)
    profiles = Counter((reading.get("evidence_profile") or {}).get("state", "unknown") for reading in readings)
    issues: dict[tuple[str, str], dict[str, Any]] = {}
    for reading in readings:
        for issue in reading["issues"]:
            key = issue["rule_ref"], issue["role"]
            item = issues.setdefault(key, {"rule_ref": issue["rule_ref"], "name": issue["name"],
                                           "role": issue["role"], "count": 0})
            item["count"] += 1
    return {"total": len(readings), "groups": dict(groups), "requirements": list(issues.values()),
            "profile_counts": {state: profiles[state] for state in EVIDENCE_PROFILES},
            "group_counting": "mutually_exclusive", "requirement_counting": "overlapping"}


def selection_reading(reading: dict[str, Any]) -> dict[str, Any]:
    """Classify completed assessments by their task-specific admission support."""
    code = reading["reason_code"]
    if code == "requirements_met":
        decision = "eligible"
    elif code == "criteria_not_ready":
        decision = "not_ready"
    elif code in ("historical_policy", "reason_not_recorded", "not_assessed", "assessment_incomplete"):
        decision = "incomplete"
    elif code == "mandatory_failure":
        decision = "excluded"
    elif any(issue["issue"] in ("not_assessed", "tool_error", "assessment_record_unavailable") for issue in reading["issues"]):
        decision = "incomplete"
    elif reading.get("evidence_profile", {}).get("state") == "none":
        decision, code = "excluded", "no_required_evidence"
    elif reading.get("evidence_profile", {}).get("state") != "partial":
        decision = "incomplete"
    else:
        decision = "evidence_incomplete"
    description = {
        "eligible": "All task admission requirements are supported.",
        "evidence_incomplete": "Some task admission requirements are supported; the remaining requirements need evidence.",
        "excluded": ("A required condition is not met." if code == "mandatory_failure"
                     else "No task admission requirement has usable support."),
        "incomplete": "A required assessment is incomplete or its record is unavailable.",
        "not_ready": "The task admission framework is not ready.",
    }[decision]
    refs = list(dict.fromkeys(issue["rule_ref"] for issue in reading["issues"]))
    names = "; ".join(dict.fromkeys(issue["name"] for issue in reading["issues"]))
    return {"decision": decision, "reason_code": code, "scope": "current_evaluation_prioritization",
            "description": description, "reason": description + (" " + names + "." if names else ""),
            "requirement_refs": refs,
            "policy": SELECTION_POLICY, "confirmed_mandatory_failure": code == "mandatory_failure"}
