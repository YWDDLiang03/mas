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
    # What kind of source a claim came from, stamped on every claim and matched against an
    # attribute's `acceptable_value_sources` (`assessor.usable_claims`, which sets a claim aside as
    # `evidence_kind_not_accepted` otherwise).
    #
    # WHY this domain exists. It did not, and `criteria.check_attribute` only checked that
    # `acceptable_value_sources` was *present*, so an attribute could name a kind nothing produces
    # and every claim it ever read was set aside. Measured on this store, 14 October 2026: the
    # oral-route literature companion declared `peer_reviewed_primary`, a kind no tool emits, and
    # the criterion could never carry a value -- the one criterion meant to answer the oral-route
    # question for the 1,262 candidates ChEMBL has no route flag for. An attribute that accepts a
    # kind nothing can produce is not a stricter attribute, it is an unanswerable one, and that has
    # to fail where it is written rather than read as "no evidence was found".
    #
    # WHY the registry is here and not in an adapter. The ground truth of what is produced is the
    # registered tools' `broker.ToolContract.evidence_kind_produced` plus `preprint`, which
    # `reading.read` stamps on a document a search returned as a preprint and which therefore no
    # contract declares (`evidence.producible_evidence_kinds` computes exactly that set for a live
    # install). But that set is install-dependent: a machine without the ADMET predictor registers
    # no tool producing `model_prediction`, and refusing an attribute against it would refuse a
    # legitimate kind for want of an optional package. So the closed list lives here, where it says
    # "no such kind anywhere" independently of what is installed, and the live set is for saying
    # "no tool for it *here*". `tests/test_predict_admet.py` pins this domain equal to what a full
    # install's contracts produce, so the two cannot drift; the core may not import an adapter to
    # compute it, and a test may.
    "evidence_kind": _labelled(
        curated_measurement=("curated measurement", "positive"),
        database_entry=("database record", "neutral"),
        model_prediction=("model prediction", "attention"),
        peer_reviewed=("peer-reviewed publication", "positive"),
        preprint=("preprint (not peer-reviewed)", "attention"),
        reference_text=("reference text", "neutral"),
        tertiary_reference=("tertiary reference", "muted"),
        user_supplied_document=("document you supplied", "neutral"),
    ),
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
    # What the literature reader decided about one extracted claim (`reading.extract_claims`), which
    # is what admits it or sets it aside. Registered because of the last value: a claim refused for
    # `attribution_ambiguous` is a number the reader found and the system is declining to use, and a
    # reviewer reading a set-aside list needs that said in words rather than inferred from a string.
    # WHY these nine and not every admission reason in the system: a database claim's reasons
    # (`evidence.claims_from_tool_result`) are about identity and provenance, not about reading a
    # span, and one domain holding both would say a reader can refuse a claim for a reason it has no
    # way to produce. `reading.extract_claims` is the only writer and validates against this list,
    # so there is one registry rather than two that can drift.
    "literature_admission_reason": _labelled(
        quote_verified=("the quoted span is in the passage it cites", "positive"),
        value_in_quote=("the number is inside the quote", "positive"),
        candidate_named_in_quote=("the quote names the candidate", "positive"),
        candidate_named_in_passage=("the passage names the candidate; the quote does not", "neutral"),
        passage_not_found=("the document has no such passage", "negative"),
        quote_not_found_in_passage=("the quote is not in the passage it cites", "negative"),
        value_not_in_quote=("the number is not inside the quote", "negative"),
        candidate_not_named_in_source=("neither the quote nor its passage names the candidate", "negative"),
        attribution_ambiguous=("the span does not tie this number to this candidate and this attribute", "negative"),
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
        # A machine adjudication resolves an item without a person, so it is its own state rather than
        # `decided`: a surface that showed the two alike would read as though an expert had answered.
        machine_adjudicated=("resolved by an agent (no person confirmed it)", "attention"),
    ),
    # Who stands behind a rule that entered a confirmed set (core/adjudication.py).
    "decision_authority": _labelled(
        human_scientific_approval=("confirmed by an expert", "positive"),
        machine_adjudication=("adjudicated by an agent; no person confirmed it", "attention"),
        trigger_table=("admitted automatically by the trigger table", "neutral"),
    ),
    "adjudication_route": _labelled(
        task_constraint_restated=("restates the task's own constraint", "neutral"),
        no_authority_available=("no authority available; demoted, stops scoring", "attention"),
        irreversible_without_authority=("too irreversible for an agent; demoted to a preference", "attention"),
        dispute_adjudicated=("proposer/critic dispute adjudicated by an agent", "attention"),
        definition_restated=("restates the attribute's own definition", "neutral"),
        bound_interpretation_granted=("an agent granted the bound's declared interpretation", "attention"),
        # Neutral, not `attention`, and deliberately: the software checked the rule's number against
        # the record the tool that produced the values wrote, exactly as `task_constraint_restated`
        # checks it against the user's own task text. Nothing was judged and nobody was asked.
        predictor_boundary_adopted=("uses the predictor's own documented decision boundary", "neutral"),
    ),
    # WHY route 6's verdicts are their own domain rather than two more `adjudication_verdict` values:
    # the question is not whose side of a dispute stands, it is whether one number may act as a
    # decision bound, and a surface that read "the proposal stands" over a granted cutoff would be
    # saying the quieter of the two things (`core/adjudication.py` route 6).
    "bound_grant_verdict": _labelled(
        grant_bound=("an agent granted the bound; it may score as a cutoff", "attention"),
        refuse_bound=("an agent refused the bound; it may not score as a cutoff", "neutral"),
    ),
    "adjudication_verdict": _labelled(
        uphold_proposal=("the proposal stands", "neutral"), uphold_objection=("the objection stands", "attention"),
        revise=("settled by a change to the rule", "neutral"),
        cannot_resolve=("not settled; the rule stops scoring", "attention"),
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
    # `evaluator` is the visibility of the sealed historical list and of everything derived from
    # it (`core/recovery.py`): an event a non-evaluator surface must not render (design §8.6).
    "visibility": _domain("default", "expert", "auditor", "evaluator"),
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
    # WHY `consolidate` is registered beside `merge` rather than reusing it: the two make different claims
    # about what happened. A merge says the members were one quantity all along, so nothing is lost. A
    # consolidation says they were distinct measurements that a screen is better off treating as one family,
    # which is a scientific judgement a reviewer may disagree with. Measured on the live pool of 89 proposals,
    # 14 October 2026: grouping formed 10 groups, two of them eight *distinct* toxicity endpoints each (any-grade
    # incidences; grade >=3 incidences), so `merge` -- "the same quantity, in the same unit and direction, for
    # the same purpose" -- correctly answers "keep separate" for all sixteen and the pool cannot reduce.
    # Recording both as `merge` would make the record unable to say which of the two happened.
    "criterion_change_operation": _domain("add", "revise", "merge", "consolidate", "remove", "reinstate", "promote",
                                          "defer"),
    # How a consolidated criterion reduces its family to one number. WHY registered rather than free text: a
    # consolidated criterion nobody can compute is worse than the family it replaced, and prose ("the overall
    # burden") does not say what to compute.
    #
    # Only the reductions that execute are registered. A consolidated criterion has one attribute and one
    # pooled claim set, not N member cells, so the reduction has to be one `assessor.assess_cell` can run
    # over those claims: `assessor.FAMILY_AGGREGATION_EXECUTION` maps each value here to the attribute
    # `aggregation` (criteria.AGGREGATIONS) that runs it, and the merge gate writes that aggregation onto
    # the consolidated attribute, which is the only field the assessor ever sees. Six values were registered
    # on 14 October 2026 and removed the same day rather than left accepted-and-unhonoured -- the defect
    # shape this repository hit twice that day (an attribute defining a derived quantity whose cell carried
    # the raw value; an ordering rule ignoring its attribute's declared aggregation) and which review
    # handoff §5.3 calls an implementation failure:
    #   * `mean_of_members`, `sum_of_members`: `criteria.AGGREGATIONS` offers no mean and no sum, so nothing
    #     computes either; substituting the median would make the card say one thing and the score another.
    #     A sum would not even be the sum over the members -- `assessor.usable_claims` pools one value per
    #     distinct (document, span, value) and a reported range contributes both of its ends, so the total
    #     would move with how much was read rather than with the family.
    #   * `count_exceeding`, `fraction_exceeding`: both name a different quantity in a different unit (a
    #     count; a share) from the attribute's own, and nothing in the consolidated cell holds the N member
    #     values to count -- the claims pooled there are observations of the family's endpoints. A count
    #     could not even be ruled on: `criteria.check_rule` requires the cutoff's unit to equal the
    #     attribute's, and the live toxicity families are in %.
    #   * `any_member_exceeds`, `all_members_within`: under a threshold rule each one *is* `worst_member`
    #     plus the cutoff ("every member stays within" is "the worst member is within"), so neither adds a
    #     computation -- and "exceeds" does not say whether it means the failing side of the cutoff or the
    #     numerically larger one, which inverts the direction mapping between the two. Three registered
    #     words for one computation make the record say something other than what runs.
    "criterion_family_aggregation": _labelled(
        worst_member=("the least favourable member", "neutral"),
        median_of_members=("the median over the members", "neutral"),
    ),
    "run_purpose": _labelled(sweep=("candidate sweep", "neutral"), criteria_derivation=("criteria derivation", "neutral")),
    "trigger_class": _domain(
        "new_external_evidence", "unresolved_conflict", "consequential_missing_measurement",
        "questionable_exclusion", "decision_relevant_computation", "human_request",
    ),
    # Primary CQA recovery (handoff §12.2, design §8.6). `field_visibility` is a record's own
    # visibility, which is not the `visibility` of the event that announced it: an event may be
    # readable while the artifact it links is not.
    "field_visibility": _domain("agent_visible", "evaluator_only", "control_only"),
    "recovery_category": _labelled(
        exact=("exact", "positive"), near_equivalent=("near-equivalent", "neutral"),
        missed=("missed", "negative"), extra=("extra: no historical counterpart", "neutral"),
    ),
    "recovery_difference_kind": _domain("expression", "threshold", "scope"),
    "recovery_mapping_shape": _domain("one_to_one", "merged", "split", "none"),
    "recovery_match_basis": _domain("definition_and_unit_match", "definition_match_unit_differs",
                                    "verdict_agreement_on_assessed_candidates", "expert_judged_equivalent"),
    "recovery_view": _labelled(independent=("independent", "positive"), assisted=("assisted", "attention")),
    "intake_provenance_form": _domain("manuscript_main_text", "manuscript_supplement", "author_supplied_list",
                                      "reconstructed_from_code", "verbal_report"),
    "completeness_attestation": _labelled(
        complete=("attested complete", "neutral"), partial=("attested partial", "attention"),
        unknown=("completeness not attested", "attention"),
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
