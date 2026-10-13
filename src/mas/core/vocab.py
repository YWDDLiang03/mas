"""State Registry (C2): the closed vocabularies of design §0.4 with their UI labels.

Every stored state is validated here on write; a value outside the registered
vocabulary is refused (`VocabularyViolation`). Labels and tones come from
`ui_ux_spec.md` §13 so that no surface remaps a state.
"""

from __future__ import annotations

VOCABULARY_VERSION = "vocab-1"


class VocabularyViolation(ValueError):
    """A value outside the registered vocabulary of its label domain."""


def _domain(*values: str) -> dict[str, tuple[str, str]]:
    return {value: (value.replace("_", " "), "neutral") for value in values}


def _labelled(**items: tuple[str, str]) -> dict[str, tuple[str, str]]:
    return dict(items)


DOMAINS: dict[str, dict[str, tuple[str, str]]] = {
    "execution": _labelled(
        queued=("queued", "neutral"), running=("running", "neutral"),
        waiting_tool=("waiting for tool", "info"), waiting_human=("waiting for expert review", "attention"),
        retrying=("retrying", "warning"), paused=("paused", "neutral"), failed=("failed", "negative"),
        cancelled=("cancelled", "neutral"), completed=("completed", "positive"),
        unresolved=("unresolved", "attention"), skipped=("skipped", "muted"),
        rejected=("rejected", "negative"),
    ),
    "exchange": _domain("proposed", "critiqued", "revising", "adjudicating", "completed", "rejected", "unresolved"),
    "termination_reason": _labelled(
        sufficient_support=("sufficient support", "positive"),
        round_limit_reached=("planned rounds finished", "neutral"),
        no_actionable_step=("no actionable step", "neutral"),
        diminishing_information_gain=("diminishing information gain", "neutral"),
        repeated_failure=("repeated failure", "attention"),
        budget_exhausted=("budget exhausted (unresolved)", "attention"),
        human_decision=("human decision", "neutral"),
        dependency_unresolved=("dependency unresolved", "attention"),
        cancelled=("cancelled", "neutral"),
    ),
    "dependency_detail": _domain("derivation_unavailable", "capability_failure_share_exceeded", "required_input_missing"),
    "candidate": _labelled(
        recommended=("recommended", "positive"), provisional=("provisional", "neutral"),
        unassessed=("unassessed", "muted"), rejected=("rejected", "negative"),
    ),
    "result_kind": _labelled(
        all_pass_set=("all-pass set", "neutral"), ranked_under_score=("top-ranked under score", "neutral"),
        both_reported=("both", "neutral"), no_recommendation=("no recommendation (abstained)", "neutral"),
    ),
    "abstention_reason": _domain("insufficient_coverage", "all_candidates_excluded", "unresolved_conflicts", "evidence_unavailable"),
    "verdict": _labelled(
        pass_=("pass", "positive"), fail=("fail", "negative"),
        unknown_missing=("unknown (missing)", "muted"), unknown_conflicted=("unknown (conflict open)", "attention"),
        inapplicable=("not applicable", "muted"), not_assessed=("not assessed", "muted"),
    ),
    "not_assessed_reason": _labelled(
        identity_unresolved=("identity not resolved", "attention"),
        identity_pending_review=("identity awaiting review", "attention"),
        budget_exhausted=("not reached (budget exhausted)", "attention"),
        run_cancelled=("not reached (run cancelled)", "attention"),
    ),
    "value_kind": _domain("measured", "curated", "predicted", "simulated", "derived", "missing"),
    "tool_outcome": _domain("ok", "partial", "empty", "not_attempted", "failed", "unknown_outcome"),
    "record_state": _domain("returned", "superseded", "stale"),
    "error_class": _domain(
        "input_invalid", "identity_unresolved", "out_of_domain", "auth_missing", "auth_rejected", "rate_limited",
        "transient_network", "upstream_server_error", "timeout", "quota_exhausted", "parse_failed",
        "schema_violation", "environment_missing", "model_unavailable", "internal_error",
    ),
    "absence_reason": _domain(
        "not_configured", "not_installed", "requires_other_environment", "unreachable", "unauthorized",
        "rate_limited_exhausted", "out_of_domain", "identity_unresolved", "no_record_found", "budget_exceeded",
        "declined_by_policy",
    ),
    "approval_kind": _domain("agent_verdict", "software_status", "human_scientific_approval", "operations_decision"),
    "review": _labelled(
        none=("no human review yet", "muted"), requested=("requested", "attention"),
        human_approved=("approved by expert", "positive"), human_rejected=("rejected by expert", "negative"),
        disputed=("disputed", "attention"),
    ),
    "queue_item_state": _labelled(
        open=("open", "neutral"), in_review=("in review", "attention"), decided=("decided", "positive"),
        deferred=("deferred", "muted"), expired=("expired", "muted"), withdrawn=("withdrawn (run continued)", "muted"),
    ),
    "hd_decision": _domain(
        "approve", "approve_with_edits", "reject", "defer_more_evidence", "escalate", "abstain",
        "request_followup", "pause", "resume", "retire",
    ),
    "hd_subject_kind": _domain(
        "attribute_version", "rule_version", "rule_set_version", "claim_admission", "candidate_state",
        "identity_merge", "conflict_resolution", "unit_correction", "cutoff_setting", "submission_admission",
        "recovery_mapping", "rerun_plan", "memory_item",
    ),
    "identity_basis": _domain("authenticated_account", "recorded_attestation"),
    "actor_kind": _domain("agent", "tool", "human", "controller", "scheduler", "system"),
    "visibility": _domain("default", "expert", "auditor"),
    "denominator_kind": _domain("enumerated_fixed", "enumerated_growing", "budget_bounded", "unbounded_adaptive", "unknown"),
    "sweep_scope": _labelled(
        full_universe=("all candidates", "neutral"), rerun_plan=("rerun of stale records", "neutral"),
        refresh_delta=("records touched by new evidence", "neutral"),
    ),
    "continuation_kind": _labelled(
        root=("first run", "neutral"), **{"continue": ("continued", "neutral")},
        refresh=("refreshed with new evidence", "neutral"), rerun=("rerun of stale records", "neutral"),
    ),
    "memory_mode": _domain("cold", "frozen", "warm"),
    "policy_arm": _domain("P0", "P0-noreview", "P1", "P2", "P2-cap", "P0+retrieval-rich", "P0+sample-rich"),
    "derivation_configuration": _domain("reference_disclosed", "reference_blind", "outcome_informed_exploratory"),
    "historical_list_exposure": _labelled(
        not_exposed=("had not seen the original list", "neutral"), exposed=("had seen the original list", "attention"),
        undeclared=("not declared (treated as seen)", "attention"),
    ),
    "acceptance_label": _labelled(
        prespecified=("prespecified", "neutral"), exploratory=("exploratory (chosen after results)", "attention"),
    ),
    "surface": _domain("terminal", "browser"),
    "session_role": _domain("operator", "expert", "evaluator", "auditor"),
    "command_entry": _labelled(interactive=("confirmed by you", "neutral"), scripted=("scripted", "neutral")),
    "command_outcome": _labelled(
        applied=("applied", "positive"), duplicate=("already done (no change)", "neutral"),
        rejected_stale_basis=("changed since you looked — not applied", "attention"),
        rejected_unauthorized=("not permitted for your role", "negative"),
        rejected_invalid=("not applied — invalid input", "negative"),
        rejected_not_permitted_in_state=("not possible in the current state", "attention"),
    ),
    "task_mode": _domain("conditional", "exploratory"),
    "rule_role": _domain("hard_exclusion", "preference", "exploratory"),
    # iteration 2: the criteria pool (design §5.6)
    "criterion_pool_state": _labelled(
        candidate=("candidate", "neutral"), needs_refine=("needs refinement", "attention"),
        filtered_out=("filtered out", "muted"), merged_away=("merged into another", "muted"),
        withdrawn=("withdrawn", "muted"), promoted=("in the registry", "positive"),
        deferred_next_round=("deferred to the next round", "attention"),
    ),
    "criterion_change_operation": _domain("add", "revise", "merge", "remove", "reinstate", "promote", "defer"),
    "run_purpose": _labelled(sweep=("candidate sweep", "neutral"), criteria_derivation=("criteria derivation", "neutral")),
    "trigger_class": _domain(
        "new_external_evidence", "unresolved_conflict", "consequential_missing_measurement",
        "questionable_exclusion", "decision_relevant_computation", "human_request",
    ),
}

# "pass" is a Python keyword, so it is spelled pass_ above; restore the registered value.
DOMAINS["verdict"]["pass"] = DOMAINS["verdict"].pop("pass_")

TERMINAL_EXECUTION_STATES = frozenset({"failed", "cancelled", "completed", "unresolved", "skipped", "rejected"})
RUN_STATES = frozenset({
    "queued", "running", "waiting_tool", "waiting_human", "retrying", "paused",
    "failed", "cancelled", "completed", "unresolved",
})
RUN_TERMINAL_STATES = frozenset({"failed", "cancelled", "completed", "unresolved"})

# Event kinds of design §4.1. Kinds marked "implementation addition" are needed by the
# build and are carried back into the design (collaboration log, slice A).
EVENT_KINDS = frozenset({
    *(f"run.{k}" for k in ("created", "started", "paused", "resumed", "cancelled", "completed",
                            "unresolved", "failed", "continued", "annotated")),
    *(f"stage.{k}" for k in ("opened", "closed", "skipped")),
    *(f"step.{k}" for k in ("queued", "started", "progressed", "waiting_tool", "waiting_human", "retrying",
                             "completed", "rejected", "unresolved", "failed")),
    "step.cancelled",  # implementation addition: steps end cancelled with their run (design §0.4)
    "round.opened", "round.closed", "attempt.started", "attempt.finalized",
    "agent.started", "agent.heartbeat", "agent.finished",
    *(f"tool.{k}" for k in ("requested", "returned", "errored", "retry_scheduled", "degraded")),
    *(f"exchange.{k}" for k in ("proposed", "critiqued", "revised", "adjudicated", "closed")),
    "evidence.admitted", "evidence.conflict_recorded", "evidence.quarantined",
    "criterion.version_proposed", "criterion.change_recorded", "criterion.version_approved",
    "candidate.assessed", "leaderboard.snapshot_published", "leaderboard.current_set", "decision.recorded",
    *(f"human.{k}" for k in ("review_requested", "review_decided", "review_claimed", "review_claim_released",
                              "review_withdrawn", "review_expired", "input_submitted")),
    "trace.opened", "evaluator_only.read",
    *(f"group.{k}" for k in ("created", "renamed", "archived", "reactivated", "task_added", "task_removed")),
    "task.group_changed",
    "checkpoint.written", "staleness.marked", "rerun.scheduled", "progress.estimate_revised",
    "preregistration.recorded", "evaluation.recorded", "projection.hash", "plan.recorded",
    "memory.operation_recorded", "memory.recalled", "report.revision_recorded",
    "task.version_recorded",     # implementation addition: every task-context version has a creating event
    "case.version_recorded",     # implementation addition: case-configuration versions (case stream)
    "constant.registered",       # implementation addition: registered constants (design §8.4)
    "identity.resolved",         # implementation addition: identity records of the identity service (design §8.2)
    "evidence.snapshot_frozen",  # implementation addition: `evs_` snapshots (design §8.5)
})

# Completion-class events: the only events that may increase a `completed` counter (design §4.1).
COMPLETION_EVENTS = frozenset({
    "stage.closed", "step.completed", "round.closed", "agent.finished", "tool.returned",
    "exchange.closed", "candidate.assessed", "human.review_decided",
})


def require(domain: str, value: str) -> str:
    """Return `value` if registered in `domain`; raise `VocabularyViolation` otherwise."""
    try:
        values = DOMAINS[domain]
    except KeyError:
        raise VocabularyViolation(f"unknown label domain {domain!r}") from None
    if value not in values:
        raise VocabularyViolation(f"{value!r} is not registered in {domain!r}")
    return value


def require_event_kind(kind: str) -> str:
    if kind not in EVENT_KINDS:
        raise VocabularyViolation(f"unregistered event kind {kind!r}")
    return kind


def label(domain: str, value: str) -> str:
    require(domain, value)
    return DOMAINS[domain][value][0]


def tone(domain: str, value: str) -> str:
    require(domain, value)
    return DOMAINS[domain][value][1]


def is_terminal(state: str) -> bool:
    require("execution", state)
    return state in TERMINAL_EXECUTION_STATES
