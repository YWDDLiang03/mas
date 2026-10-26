"""Result-reading compatibility and criterion disposition labels."""

from typing import Any

from mas.core.selection import (
    DECISION_READING_VERSION, SELECTION_POLICY, SELECTION_DECISIONS, EVIDENCE_PROFILES,
    evidence_profile, eligibility_reading, refine_evidence_reason, eligibility_counts, selection_reading,
)


def criterion_disposition(body: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, str]:
    """Explain evaluation use separately from a proposal's lifecycle label."""
    state, reason = evaluation.get("state"), evaluation.get("reason_kind")
    if state == "enabled":
        role = body.get("role")
        if role == "exploratory_consideration":
            return {"code": "context_only", "label": "Contextual observation",
                    "description": "Assessed for interpretation; carries no eligibility or ranking weight."}
        if role == "hard_exclusion":
            return {"code": "mandatory_requirement", "label": "Mandatory requirement",
                    "description": "Direct evidence determines whether this requirement is met, failed or unresolved."}
        return {"code": "weighted_criterion", "label": "Weighted prioritization criterion",
                "description": "Contributes to the score of eligible candidates under the fixed comparison policy."}
    reason_text = str(evaluation.get("reason") or body.get("reason") or "")
    if reason == "unregistered_proposal":
        if reason_text.startswith("units:"):
            return {"code": "unit_mapping_unresolved", "label": "Unit conversion unresolved",
                    "description": "The proposed unit is incompatible with the available measurement route. This proposal is not used in the evaluation."}
        if reason_text.startswith("decision_semantics_unresolved:"):
            return {"code": "alternative_policy_unresolved", "label": "Alternative policy unresolved",
                    "description": "This quantity already has a registered criterion. The alternative decision or evidence policy is unresolved and is not counted again."}
        return {"code": "proposal_not_finalized", "label": "Proposal not finalized",
                "description": "The proposal has no validated evaluation definition and is not used in this evaluation."}
    definitions = {
        "non_executable_preference": ("comparison_incomplete", "Scoring definition incomplete",
            "The comparison threshold, range or accepted category is not defined. This criterion contributes no score."),
        "unresolved_review": ("review_unresolved", "Review unresolved",
            "A review objection remains unresolved. This criterion is withheld from the evaluation."),
        "review_pending": ("review_unresolved", "Review unresolved",
            "Review was incomplete when this evaluation was prepared. This criterion is withheld."),
        "capability_deferred": ("evidence_route_unavailable", "Evidence route unavailable",
            "The required evidence route is unavailable in this evaluation."),
        "not_prepared": ("evaluation_not_prepared", "Evaluation not prepared",
            "No evaluation framework has been prepared for this task."),
        "historical_view": ("historical_version", "Historical version",
            "This is a saved historical version. Its absence from the latest evaluation does not establish its earlier use."),
    }
    code, label, description = definitions.get(reason, ("reason_not_recorded", "Not used; reason unavailable",
        "This item is outside the evaluation set; a specific reason was not recorded."))
    return {"code": code, "label": label, "description": description}
