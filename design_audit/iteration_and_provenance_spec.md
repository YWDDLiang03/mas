# Iteration and Provenance Specification

Design artifact only, 12 October 2026. This document specifies how every run, round, analysis step, and revision is recorded so that a reader can answer, from persisted records alone: what is happening now, what changed since the previous version, which evidence caused the change, who approved it, which results became stale, and why the system continued, stopped, or abstained. It contains no implementation code. All component ids (C1–C20), record names, identifier prefixes, state vocabularies, and event kinds are those defined in `optimized_design.md` Section 0; field lists repeat or extend the ones in its Sections 4, 6, 11, and 12. Nothing here reports an executed run; every example trace is an illustrative placeholder.

---

## 1. Record model: the hierarchy of work

### 1.1 Containers and their identifiers

| Level | Identifier | Created by | Parent | Versioned how |
|---|---|---|---|---|
| Task context | `task_<ulid>@v<n>` | C4 | — | every human edit of objective, scope, universe, or constraints creates `@v<n+1>` with `supersedes` |
| Case configuration | `case_<id>@v<n>` (Section 2.2 of the design) | operator | — | new version per edit; bound into runs by reference |
| Run group | `grp_<slug>` | operator | — | renamed or archived by events in its group stream; never deleted (design §6.9) |
| Run chain | `chain_<ulid>` | C15 | the root run | grows by run continuations; branches only on confirmation (design §6.8) |
| Run | `run_<ulid>` | C15 | `task_@v` through the Run Binding `bind_<run>`; `continues_run_id` within a chain | never versioned; a new cutoff, policy arm, `rules@v`, budget, or group is a new run, in the same chain when a person continues (design §6.8) |
| Attempt | `att_<run>_<n>` | C15 | run | one per execution attempt; a crash finalizes `att_n` and starts `att_n+1` |
| Stage | `stage_<run>_<slug>` | C15 from the plan | run | — |
| Round | `round_<run>_<n>` | C15 | run | one per screening round; single-pass runs have exactly `round_<run>_1` |
| Step | `step_<round>_<n>` | C5 plan | round and stage | the step record carries its brief; re-execution is a new step id with `reused_from_step_id` in the Reuse record |
| Exchange | `xchg_<step>_<n>` | C7 | step | each proposal, critique, revision, and adjudication is an artifact; the exchange is the container |
| Checkpoint | `ckpt_<run>_<seq>` | C15 | run | immutable; names the `seq` to replay from |
| Event | `evt_<stream>_<seq>` | C1 | run, task, or group stream | immutable; `seq` is contiguous per stream |

The Run Binding (`bind_<run>`) is the immutable join of a run to its task context version, case configuration version, adapter version, `rules@v` (possibly empty), `strat@v`, policy arm, evidence cutoff, tool availability snapshot, reference-outcome disclosure, derivation configuration, budget envelope, and baseline configuration reference. Every artifact and every event in the run cites `bind_<run>` through its `ids.run_id`; a bound field cannot change inside a run.

The complete field list, including the chain, group, protocol, preregistration, role-binding, host, and tool-manifest fields, is design §2.3; this specification does not repeat it.

### 1.2 What every substantive analysis record must carry

Per governing prompt §4.3, each round or analysis record needs: identifiers and relationships (task/run/round/step, parent version or checkpoint), the actor (agent, tool, or human), timestamps, the question being answered, input and evidence versions, retrieved or corrected sources, relevant tool results or errors, proposed changes, critiques, human decisions, outcomes, unresolved issues, and the reason to continue or stop. The mapping:

| Requirement | Where it lives |
|---|---|
| task/run/round/step ids | Event record `ids {group_id, task_id, chain_id, run_id, attempt_id, stage_id, step_id, round_id, exchange_id, tool_call_id, review_request_id, checkpoint_id}`; Artifact Envelope `task_context_id, run_id, round_id, exchange_id` |
| parent version or checkpoint | Artifact Envelope `parent_artifact_id`, `supersedes`; Task context `supersedes`; Reuse manifest `resumed_from_checkpoint_id`; Event `parent_seq`, `cause_seq` |
| actor | Event `actor {kind, id, role, version, model_family?, via?}`; Artifact Envelope `actor {actor_kind, actor_id, role, model_family?, policy_version?}`; Expert decision record `actor` |
| timestamps | Event `emitted_at`, `recorded_at` (UTC ms); Artifact `created_at`; Assessment `assessed_at`; Expert decision `decided_at` |
| question being answered | Event `question`; Step `question`; Open-question record `question`; Evidence request artifact `question` |
| input and evidence versions | Event `input_versions {rules@v, evs_, lb_, strat@v}`; Artifact Envelope cites `bind_`; Assessment `rules@v`, `evidence_snapshot_id` |
| retrieved or corrected sources | Source record (`src_`) with `access_state`, `supersedes_source`, `retraction_state`; Claim record `admission_state`, `supersedes`; Search coverage record |
| tool results or errors | Result record (`res_`) with `outcome`, `error`, `provenance`; Invocation record (`inv_`) with `retry_of`, `attempt_index`; events `tool.*` |
| proposed changes | proposal and revision artifacts (`changes[] {field_path, before, after, reason, finding_refs[]}`); Criterion change record (`chg_`) |
| critiques | critique artifact (`checks[]`, `findings[]`, `independence`) |
| human decisions | Expert decision record (`hd_`) and its `human.review_decided` event |
| outcomes | Exchange state and `termination_reason`; LoopOutcome; Assessment `verdict`; Candidate roll-up `state`, `state_reason`; Snapshot `result_kind` |
| unresolved issues | Open-question record (`oq_`) with `state`; Candidate roll-up `blocking_unknowns[]`; LoopOutcome `open_questions[]` |
| reason to continue or stop | Continuation decision `{decision, stop_reason, trigger_question_refs[]}` written at `round.closed`; Round Progress Record `verdict` |

---

## 2. The append-only event history (C1)

### 2.1 Event record

The merged event envelope (coordinator ruling after the WS2/WS4/WS7 cross-review): `seq` (journal-assigned, contiguous per stream, design §2.4), `event_id`, `event_type`, `emitted_at`, `recorded_at`, `actor {kind: agent|tool|human|controller|scheduler|system, id, role, version, model_family?, policy_version?, via? {surface, session_id, command_id, entry}}`, `ids {group_id, task_id, chain_id, run_id, attempt_id, stage_id, step_id, round_id, exchange_id, tool_call_id, review_request_id, checkpoint_id}`, `parent_seq`, `cause_seq`, `state_from`, `state_to`, `termination_reason?`, `input_versions {rules@v, evs_, lb_, strat@v, adapter_version, bind_}`, `question`, `summary`, `progress {scope, denominator_kind, completed, planned, indeterminate}`, `budget {rounds_used, rounds_max, tool_calls, tokens_by_role, wall_clock_s, human_wait_s}`, `artifact_links[] {kind, id, version, schema_version, payload_sha256}`, `visibility` (`default` | `expert` | `auditor`), `payload_ref`, `payload_hash`.

`seq` exists once, on the event. Artifacts carry `journal_seq` (the `seq` of the event that created them) and are linked from events through `artifact_links[]`. `parent_seq` expresses continuation (the event this answers); `cause_seq` expresses causation of a state transition (the event that made the transition happen); both may be present. `actor.via` is present on every event caused by an operator command and names the surface (`terminal` | `browser`), the session, the `command_id`, and the entry mode (`interactive` | `scripted`); it is for audit only and never enters a fingerprint (design §2.4).

### 2.2 Event kinds

As listed in `optimized_design.md` Section 4.1: lifecycle (`run.*`, `stage.*`, `step.*`, `round.*`, `attempt.*`), actors (`agent.started`, `agent.heartbeat`, `agent.finished`), tools (`tool.requested`, `tool.returned`, `tool.errored`, `tool.retry_scheduled`, `tool.degraded`), protocol (`exchange.proposed`, `exchange.critiqued`, `exchange.revised`, `exchange.adjudicated`, `exchange.closed`), substance (`evidence.admitted`, `evidence.conflict_recorded`, `evidence.quarantined`, `criterion.version_proposed`, `criterion.change_recorded`, `criterion.version_approved`, `candidate.assessed`, `leaderboard.snapshot_published`, `decision.recorded`), humans (`human.review_requested`, `human.review_decided`, `human.review_claimed`, `human.review_claim_released`, `human.review_withdrawn`, `human.review_expired`, `human.input_submitted`, `trace.opened`, `evaluator_only.read`), control (`checkpoint.written`, `staleness.marked`, `rerun.scheduled`, `progress.estimate_revised`, `preregistration.recorded`, `evaluation.recorded`, `projection.hash`, `plan.recorded`).

Two kinds used throughout this specification are registered in `optimized_design.md` Section 4.1 (Memory and reports): ``memory.operation_recorded`` and ``report.revision_recorded``. Identity resolution outcomes are journaled as `candidate.assessed` with `verdict: not_assessed` and `state_reason: identity_unresolved` for unresolved identities; a dedicated kind is not required. Run chains, groups, and in-run memory add `run.continued`, `run.annotated`, `group.{created, renamed, archived, reactivated, task_added, task_removed}`, `task.group_changed`, `leaderboard.current_set`, and `memory.recalled` (design §4.1, §6.8, §6.9, §10.5).

### 2.3 Counter rule (contract)

Only completion-class events may increase any `completed` value: `stage.closed`, `step.completed`, `round.closed`, `agent.finished`, `tool.returned`, `exchange.closed`, `candidate.assessed`, `human.review_decided`. `agent.heartbeat` and `tool.requested` update `last_seen_at`, the current `question`, and elapsed time only. The watchdog consumes heartbeats; the Progress Projection (C17) consumes completions. A `progress.estimate_revised` event is the only way a `planned` value changes between stage open and stage close; it carries `before.planned`, `after.planned`, `denominator_kind`, and a reason. Conformance tests: no completion-class event with an unchanged `completed`; no heartbeat with a counter; no `planned` change outside `progress.estimate_revised`.

### 2.4 Corrections by reference

The journal is never rewritten. A correction is a new event whose `cause_seq` points at the corrected event and whose `summary` names the correction; the corrected event remains and is rendered with a "superseded by seq N" marker in the timeline. Artifacts are corrected the same way: a new artifact with `supersedes` set; the old artifact's `state` becomes `superseded` through a `decision.recorded` or `human.review_decided` event. Ledger rows follow the same discipline: `admission_state` changes are new rows ordered by `(journal_seq, updated_at)`.

### 2.5 Attempts and crash recovery

An attempt begins with `attempt.started` and ends with `attempt.finalized {finalized_by: worker|controller|human}`. If a worker dies, the controller writes `attempt.finalized {finalized_by: controller}`, writes a synthetic `tool.returned {outcome: unknown_outcome}` for every `tool.requested` without a matching `tool.returned`, and starts `att_<run>_<n+1>` with `attempt.started {resumed_from_checkpoint_id}`. The recorded reference-application defect in which the progress counter restarted on resume (`progress_version` 37 → 1 in run `rec_43273c9978`, Workstream 7) cannot recur for sequence numbering, because `seq` is journal-assigned and never resets within a run; the user-visible denominator can still change mid-stage, which is why `progress.estimate_revised` exists.

---

## 3. The immutable version history

| Versioned object | Identifier | Created by | Immutability rule | Diff source |
|---|---|---|---|---|
| Attribute (CQA) | `attr_<slug>@v<n>` | C10 | new version per operation; prior versions remain `deprecated`, never deleted | Criterion change record (`chg_`) |
| Rule | `rule_<slug>@v<n>` | C10 | as above | `chg_` |
| Confirmed rule-set | `rules@v<n>` | C10 with `hd_` refs | immutable once confirmed; `evidence_admission_predicate_hash` recorded | set of `chg_` between versions |
| Evidence snapshot | `evs_<task>_<n>` | C9 | frozen claim-id set plus `cutoff_at` and `hash` | claim-id set difference |
| Leaderboard snapshot | `lb_<task>_<n>` | C12 | write-once; `change_records[]` against `parent_snapshot_id` (design §4.12, §6.8) | embedded Change records |
| Assessment | `asm_<cand>_<attr@v>_<rule@v>_<evs>` | C11 | append-only; `staleness` is a marker | Reuse record `reuse_decision` |
| Plan | `plan_<run>@v<n>` | C5 | new version on replan; `parent_plan_id` | step set difference |
| Task context | `task_@v<n>` | C4 | `supersedes` | field-level diff from `missing_info_requests` and edit records |
| Strategy version | `strat@v<n>` | C20 | never deleted; `parent_version_id`, `status`, `rollback_target` | Strategy version record `change_summary` |
| Memory item | `mem_<ulid>` | C14 | operations only; `supersedes_item_id` | ``memory.operation_recorded`` events |
| Report revision | `report_revision` artifact with `version`, `parent_version` | reporting | new artifact per revision | `change_summary` |

Versions are created only by the component that owns the object, and every version creation emits a journal event (`criterion.version_proposed`, `criterion.version_approved`, `leaderboard.snapshot_published`, `plan.recorded`, `evaluation.recorded`, or `memory.operation_recorded` and `report.revision_recorded`). A version without a creating event is invalid.

---

## 4. Evidence-to-decision links

### 4.1 Forward chain

```mermaid
flowchart LR
  S[src_ Source record] --> L[loc_ Location]
  L --> C[claim_ Claim record<br/>claim_type, verifier_id, admission_state]
  C --> IG[ig_ Independence group]
  C --> A[asm_ Assessment record<br/>verdict, value_kind]
  A --> R[rsn_ Reason record]
  A --> RU[Candidate roll-up<br/>state, state_reason]
  RU --> E[Candidate entry in lb_ snapshot]
  C -. polarity: conflicts .-> A
  CR[critique artifact] --> CHG[chg_ Change record]
  CHG --> AV[attr_@v / rule_@v]
  HD[hd_ Expert decision] --> AV
  HD --> RS[rules@v confirmed]
  RS --> A
  TR[res_ Tool result] --> C
  TR --> A
```

Every link in the chain is an explicit reference field, never an inference: `Claim.source_ref` and `Claim.location`; `Assessment.value_source_claim_refs[]` and `conflicting_claim_refs[]`; `Assessment.reason_ref`; `Candidate roll-up` is computed from the assessments of one candidate under one `rules@v` and one `evs_`; `Candidate entry.per_criterion_refs[]`; `Change record.cause {critique_id | claim_id | human_decision_id | tool_result_id | rule_change_id}`; `Rule.confirmed_by (hd_)`; `rules@v.confirmed_by[]`; `Result record.provenance.invocation_id`.

### 4.2 Backward navigation (what the UI must be able to open)

From any candidate state: the roll-up → each assessment → its reason → each cited claim → its exact location in the source, plus the visibility manifest of the decision that produced the assessment. From any criterion version: its change records → the critique, claim, tool result, or expert decision that caused each → the proposal and critique artifacts of the exchange → the exchange's events. From any snapshot change record: the `cause` → the same chain. From any expert decision: the queue item, the inspection bundle it saw, and the versions and stale sets it produced.

### 4.3 Visibility manifests

Each decision artifact references an Evidence visibility manifest (`optimized_design.md` Section 4.9) listing included and excluded sources with typed omission reasons. The manifest is what makes "which evidence was considered" answerable without raw transcripts and what records, mechanically, that the evaluator-only historical-criteria artifact was excluded from a derivation decision (`omitted_reason: evaluator_only_artifact`).

---

## 5. Change records

### 5.1 Criterion change record (`chg_`, owned by C10)

Fields as in `optimized_design.md` Section 4.10: `operation` (add | revise | merge | split | remove | reinstate), `targets[]`, `reason_kind`, `reason_text`, `source_refs[]`, `proposed_by`, `critiqued_by`, `arbitration_outcome`, `human_decision_ref`, `effective_from_version`, `affected_candidates[] {candidate_ref, restage_action}`, `removal_kind?`. The semantic difference between two rule-set versions is the ordered list of `chg_` records between them, rendered per field:

| Change kind | Rendered fields | Linked cause |
|---|---|---|
| added | new `attr_@v1` or `rule_@v1`; definition, kind, direction, unit, applicability, cutoff and `cutoff_basis` | critique or claim that motivated it; `hd_` that confirmed it |
| modified | `fields_changed[] {field, before, after}` for definition, direction, unit, applicability condition, cutoff, `cutoff_basis`, `uncertainty_range`, on-state policy, weight | the finding or claim; `hd_` if a hard exclusion or expert-set cutoff |
| merged | `targets.in[]` two or more attribute versions; `targets.out[]` one; equality basis (normalized definition, unit-normalized direction, value-source kinds) | `redundancy_detected` finding; `hd_` |
| split | `targets.in[]` one; `targets.out[]` two or more with distinct applicability sets or measurements | finding; `hd_` |
| removed | `removal_kind` unsupported or superseded; the searches that failed to support it (search coverage record refs) | `cutoff_unsupported` or `expert_instruction`; `hd_` |
| reinstated | the earlier version restored by reference | `hd_` |

Thresholds, units, and applicability changes are `modified` records whose `fields_changed[]` name the field; a unit correction that changes any verdict is additionally tagged for the review queue (`optimized_design.md` Section 12.1).

### 5.2 Candidate and leaderboard change record (shared schema, owned by C12)

`change_id`, `object_kind` (candidate_assessment | leaderboard_entry), `object_id`, `from_version` (previous `lb_`), `to_version`, `operation` (admit | exclude | demote | promote | unrank | rank_changed | status_changed | score_changed), `fields_changed[] {field, before, after}`, `cause`, `actor`, `at`, `explanation_status` (`evidence_linked` | `unexplained`). A material change with `explanation_status: unexplained` is rendered as a defect, not hidden. `unrank` means the candidate left `ranked_under_score` ordering because a hard-rule cell became `unknown_*`; it is not a failure and the record says so.

### 5.3 Rank-change explanations

Every `rank_changed` or `score_changed` record names the `chg_` or `claim_` that moved the ordering; a change caused by a preference-weight revision cites the `chg_` with `reason_kind` and the `hd_` that confirmed the new `rules@v`. More citations, repeated copies of one study, or a higher score cannot appear as a cause: the cause must be a claim admitted into a new `evs_`, a tool result, a change record, or a human decision.

---

## 6. What is, and is not, a new screening round

| Event in the system | Container created | Journal signature | What it must not be confused with |
|---|---|---|---|
| New screening round | `round_<run>_<n+1>` | `round.opened` with `cause_seq` pointing at the `round.closed` whose Continuation decision was `continue`, and `artifact_links` to the triggering `oq_` | a tool retry or a revision inside the same round |
| Tool retry | none; same `inv_` with `attempt_index + 1` and `retry_of` | `tool.retry_scheduled` then `tool.returned` or `tool.errored`, nested under the original `tool.requested` by `parent_seq` | a new step or round |
| Review exchange revision | new revision artifact inside `xchg_` | `exchange.revised` within the same `exchange_id` | a new round; bounded by `review_exchanges` budget |
| Self-correction turn | revision artifact before any critique | `exchange.revised` with `actor.role: proposer` and no preceding `exchange.critiqued` | a review exchange; bounded separately |
| Human edit | new version of the edited object (`task_@v`, `attr_@v`, `rule_@v`, `rules@v`) | `human.review_decided` followed by `staleness.marked` and `rerun.scheduled` | a screening round; stale cells are re-assessed in the current round while the run has not ended, otherwise in a run continuation of kind `rerun` |
| Report revision | `report_revision` artifact with `parent_version` | ``report.revision_recorded`` | a rule or candidate change; it changes narrative only |
| Evidence-refresh run | new `run_<ulid>` on the same `task_@v`, new `evs_<task>_<n+1>` with a later `cutoff_at` | `run.created` whose Run Binding cites the same task context and a different cutoff; the first round's `round.opened` cites `trigger_class: new_external_evidence` | a resume of the earlier run; started from a chain, it is a run continuation of kind `refresh` (design §6.8) |
| Attempt | `att_<run>_<n+1>` | `attempt.finalized` then `attempt.started {resumed_from_checkpoint_id}` | a new run or round; the work is the same, interrupted |
| Resume | same run and round; new `att_` only if the process restarted | `checkpoint.written` earlier; `run.resumed` | an evidence-refresh run or a run continuation |
| Reopen | nothing | no event except an optional `trace.opened` if raw traces are viewed | a resume; it is read-only |
| Human-requested round | `round_<run>_<n+1>` in the same run | `round.opened` citing an `oq_` with `trigger_class: human_request` and the person's `cmd_` | an adaptive continuation; it is never counted as one when policy arms are compared |
| Run continuation | new `run_` in the same `chain_`, with `continues_run_id` | `run.continued` in the task stream and the new run's `run.created`, whose Run Binding lists `edits_since_parent[]`; reused records cite the parent run | a resume (same run) or a re-entered run; a run that has ended is never re-entered |
| Run-group switch | nothing | a session setting only; moving a task without runs is `task.group_changed` | a change of a run's group, which happens only by continuing into another group |

A longitudinal leaderboard is maintained by evidence-refresh runs; no individual run is required to be multi-round, and a single-pass run has exactly one `round.opened` and one `round.closed` whose Continuation decision records `stop_reason`.

---

## 7. Checkpoints, resume lineage, reuse

### 7.1 Checkpoint

`ckpt_<run>_<seq>` written by C15 at every stage boundary, after each rule pass of the candidate sweep, and before any `waiting_human`: `checkpoint_id`, `run_id`, `attempt_id`, `seq`, `step_states[] {step_id, state, evaluated_artifact_ref?}`, `open_questions[]`, `sweep_cursor? {rule_ref, seed, completed_candidate_count, completed_cell_refs_hash}`, `bind_` reference, `written_at`. Event: `checkpoint.written`.

### 7.2 Resume

On `run.resumed` (same attempt) or `attempt.started` (new attempt), C15 replays the journal from the checkpoint `seq`, restores step states (a step is `completed` only if an evaluated artifact exists; otherwise `queued`), and emits a Reuse manifest: `resumed_from_run_id`, `resumed_from_checkpoint_id`, `reused[] {record_ref, input_fingerprint, why_legal}`, `recomputed[]`. Candidate detail renders each assessment as `reused` (with the checkpoint) or `re_evaluated`. A run continuation (design §6.8) emits the same manifest with `resumed_from_run_id` naming the parent run and no checkpoint, and each reused record cites the run that produced it.

### 7.3 Reuse record and the two-part reuse rule

Per step: `input_fingerprint` (hash over input artifact ids and versions, `rules@v`, `strat@v`, evidence cutoff, adapter versions, tool contract versions, the `executed_on` of each tool result unless the tool declares `platform_independent_output`, and `recall_set_hash`; design §4.16), `reuse_decision` (`recomputed` | `reused_valid` | `reused_overridden_by_human` | `invalidated`), `validity`, `staleness_cause`, `human_decision_ref?`. Artifact existence is necessary; fingerprint match is sufficient — except for the always-recompute classes (criterion applicability, candidate roll-up states, adjudications, snapshots, model-authored rationale outside a reused assessment), which are re-evaluated whenever any input version changed; a per-cell assessment with its reason record is reused when its own fingerprint (candidate identity, `rule_ref@v`, `evidence_snapshot_id`, `strat@v`, assessor model or tool version, tool contract versions, `executed_on`, `recall_set_hash`; never reused across policy arms) is unchanged; a record produced with any provisional memory item recalled is never reused in a `cold` or `frozen` run or in another group. Human-approved records are never re-derived silently: an `hd_`-confirmed object that would be recomputed is instead marked `reused_overridden_by_human` with the decision reference, or routed to the queue.

---

## 8. Staleness and reruns (C16)

### 8.1 Dependency graph

Edges derived from `depends_on` and reference fields: `claim_ → asm_`; `asm_ → candidate roll-up → lb_ entry`; `attr_@v / rule_@v → every asm_ applying it`; `rules@v → every roll-up under it`; `res_ → asm_`; `evs_ → every asm_ under it`; `task_@v → plan_ → steps`.

### 8.2 Marking

A human edit, a confirmed rule change, an evidence refresh, or an adapter or tool contract version change emits `staleness.marked {cause_seq, staleness_cause, stale_set[]}` where `stale_set[]` is the transitive closure over the graph. Each stale assessment's `staleness` field becomes `stale_rule_version`, `stale_evidence`, `stale_by_human_edit`, or `superseded`. Stale records are never deleted and remain inspectable with their original versions.

### 8.3 Rerun Plan

`rerun.scheduled {items[] {object_ref, reason, cost_estimate, required}, approval_rule, approved_by?}`. Approval rule (coordinator ruling): auto-approve when every item is `required` and within the step budget; otherwise a non-blocking queue item that shows the stale, rerun, and reusable counts. Approval approves the plan only. While the run has not ended, its items are re-assessed in the current round before its sweep counts as complete, using no round budget; once the run has ended, or when the cutoff or binding changed, the plan executes only in a run continuation of kind `rerun` that a person starts (design §6.8), and each recomputed assessment gets a Reuse record with `reuse_decision: recomputed`; unaffected results carry `reused_valid`.

### 8.4 What the UI must show

For any object: whether it is current or stale, the cause, whether a rerun is scheduled, approved, running, or done, and whether the displayed value was reused or re-evaluated and from which checkpoint.

---

## 9. Replay contract (C17 over C1)

`subscribe(stream_id, from_seq)` replays persisted events in order, then tails live. Each frame carries `seq`; the client keeps `last_applied_seq` and ignores duplicates (delivery is at-least-once). Reconnect resubscribes at `last_applied_seq + 1`. If `from_seq` predates compaction, the server returns the projection snapshot with `snapshot_seq` and resumes from it. Serving a run requires only its journal on disk, never a live process. Client freshness (`live` | `view_stale` | `activity_unknown`) is derived from heartbeat age and connection state and is never persisted as run state. Both operator surfaces use this contract, for every stream kind alike. A journal written on a Linux host must replay to the same projections on a Windows host and the reverse, because hashes and projections are computed on the canonical form of design §14.2; this is checked by scenario S12 and has not been tested. The transport is an implementation choice.

---

## 10. Mapping events to persisted records

| Event kind | Record written or changed | Store (design Section 14) |
|---|---|---|
| `run.created` | Run Binding `bind_`; task context reference | journal, artifact store |
| `plan.recorded` | `plan_@v` with steps | artifact store |
| `preregistration.recorded` | hashed preregistration artifact (policy stage or criterion stage) | evaluation store |
| `tool.requested` / `tool.returned` / `tool.errored` | Invocation `inv_`, Result `res_` with provenance | artifact store; cache |
| `evidence.admitted` / `evidence.conflict_recorded` / `evidence.quarantined` | Claim rows with `admission_state`; Independence group; Search coverage record | Claim Ledger |
| `exchange.*` | proposal, critique, revision, adjudication artifacts; exchange state | artifact store |
| `criterion.version_proposed` / `criterion.change_recorded` / `criterion.version_approved` | `attr_@v`, `rule_@v`, `chg_`, `rules@v` | Criterion Registry |
| `candidate.assessed` | `asm_`, `rsn_`, roll-up | Assessment Ledger |
| `leaderboard.snapshot_published` | `lb_<task>_<n>` with change records and reporting tuple | leaderboard snapshots |
| `decision.recorded` | decision artifact with Independence Declaration and dissent | artifact store |
| `human.review_requested` / `human.review_decided` | Queue item `q_`; Expert decision `hd_` | review queue and decisions |
| `human.input_submitted` | Submission `sub_`; provisional claim | submission store; Claim Ledger |
| `trace.opened` | access record | trace store (access log) |
| `checkpoint.written` | `ckpt_` | journal, artifact store |
| `staleness.marked` / `rerun.scheduled` | Reuse records; Rerun Plan | Assessment Ledger; artifact store |
| `progress.estimate_revised` | projection input only | journal |
| `evaluation.recorded` | Evaluation run `evr_`, Round Progress Record, Recovery comparison records | evaluation store |
| `projection.hash` | hash of the event range summarized by a projection | journal |
| `attempt.started` / `attempt.finalized` | attempt rows; synthetic `res_` with `unknown_outcome` | journal; artifact store |
| `run.continued` / `run.annotated` | continuation link with `edits_since_parent[]` (task stream); run annotation | journal |
| `group.*` / `task.group_changed` | group record; task-context version | journal, artifact store |
| `leaderboard.current_set` | current-snapshot pointer of a leaderboard record (`lbd_`) | journal |
| `memory.recalled` | recall set of a step, which enters its fingerprint | journal; memory store usage log |
| `human.review_withdrawn` / `human.review_expired` | queue item state | review queue and decisions |
| ``memory.operation_recorded`` | Memory item operations | memory store |
| ``report.revision_recorded`` | `report_revision` artifact | artifact store |

---

## 11. Worked example traces (illustrative placeholders only)

All ids, counts, and names below are placeholders to show record shapes. They are not results and must not be read as a run that occurred.

### 11.1 Single-pass run

| seq | event kind | actor | ids (abbrev.) | summary |
|---|---|---|---|---|
| 1 | `run.created` | controller | run_R1, bind_R1 | bound task_T1@v1, case_C1@v1, rules@v0 (empty), strat@v1, arm P0, cutoff D |
| 2 | `preregistration.recorded` | human:evaluator V1 | task_T1 stream; run_R1 | policy stage (design §13.6): rule semantics, constants hash, ordering method, evidence tiers, cutoff D and snapshot rule, universe id, tool manifest, strat@v1, sweep seed, threshold for "most" |
| 3 | `attempt.started` | controller | att_R1_1 | — |
| 4 | `stage.opened` | controller | stage_R1_normalize | — |
| 5 | `step.completed` | agent:C4 | step_…_1 | task_T1@v1 written; 2 advisory unknowns, 0 blocking |
| 6 | `stage.closed` | controller | stage_R1_normalize | completed |
| 7 | `plan.recorded` | agent:planner | plan_R1@v1 | 10 steps, screening_rounds budget 1 |
| 8 | `round.opened` | controller | round_R1_1 | single pass |
| 9–40 | `tool.requested` / `tool.returned` / `evidence.admitted` / `evidence.conflict_recorded` | tool:*, agent:retriever | step_…_2..5 | per-dimension retrieval; search coverage records; one conflict recorded on attr_A3 |
| 41 | `exchange.proposed` | agent:proposer | xchg_…_1 | proposal art_P1: 9 attributes, 11 rules, 3 considered-and-rejected |
| 42 | `exchange.critiqued` | agent:critic (cross_family) | xchg_…_1 | critique art_K1: 7 checks, 4 findings with external referents |
| 43 | `exchange.revised` | agent:proposer | xchg_…_1 | revision art_V1: changes[] on 3 fields |
| 44 | `exchange.adjudicated` | controller (deterministic) | xchg_…_1 | precedence table v1; dissent[] 1 deferred |
| 45 | `criterion.change_recorded` ×12 | C10 | chg_… | add ×9 attributes, add ×11 rules (collapsed here) |
| 46 | `criterion.version_proposed` | C10 | rules@v1-proposed | — |
| 47 | `exchange.closed` | controller | xchg_…_1 | completed; termination_reason sufficient_support |
| 48 | `human.review_requested` ×4 | C18 | q_… | each hard exclusion and one expert-set cutoff |
| 49 | `checkpoint.written` | controller | ckpt_R1_49 | before waiting_human |
| 50 | `step.waiting_human` | controller | step_…_6 | blocked_on_review: 4 |
| 51–54 | `human.review_decided` | human:expert E1 | hd_… | approve ×3, approve_with_edits ×1 (unit correction on rule_R7) |
| 55 | `criterion.change_recorded` | C10 | chg_… | revise rule_R7 unit; cause hd_… |
| 56 | `criterion.version_approved` | C10 | rules@v1 | confirmed_by 4 hd_; admission-predicate hash H1 |
| 57 | `preregistration.recorded` | human:evaluator V1 | task_T1 stream; run_R1 | criterion stage: rules@v1, evs_T1_1, sweep order |
| 58–60 | `progress.estimate_revised` | controller | stage_R1_assess | planned 3,171 → 2,980 after identity resolution (191 unresolved) |
| 61–N | `candidate.assessed` | agent:assessor, tool:* | asm_… | one per candidate × criterion; many `unknown_missing` |
| N+1 | `leaderboard.snapshot_published` | C12 | lb_T1_1 | result_kind both_reported; reporting tuple; tool_coverage; interaction_estimate_provider none |
| N+2 | `evaluation.recorded` | C19 | evr_… | outcome dependence report; the recovery comparison follows after the run as an evaluator command in the case stream |
| N+3 | `round.closed` | controller | round_R1_1 | Continuation decision: stop; stop_reason round_limit_reached (P0, round budget 1 used); 2 open questions carried forward |
| N+4 | `run.completed` | controller | run_R1 | — |
| N+5 | `attempt.finalized` | controller | att_R1_1 | finalized_by worker |

### 11.2 Human unit correction causing stale marks and a partial rerun

| seq | event kind | actor | ids | summary |
|---|---|---|---|---|
| M | `human.review_requested` | C18 | q_Q9 | critic flagged unit mismatch on attr_A5 (as-reported vs normalized) |
| M+1 | `human.review_decided` | human:expert E2 | hd_H9 | approve_with_edits: unit of attr_A5 corrected; reason recorded; approval_kind human_scientific_approval |
| M+2 | `criterion.change_recorded` | C10 | chg_7f3a21 | modified attr_A5 unit; fields_changed before/after; cause hd_H9 |
| M+3 | `criterion.version_approved` | C10 | rules@v2 | hash H2 (unit change alters a verdict → review-queue trigger satisfied by hd_H9) |
| M+4 | `staleness.marked` | C16 | — | staleness_cause rule_version; stale_set: 44 asm_ under attr_A5, 44 roll-ups, lb_T1_1 entries |
| M+5 | `rerun.scheduled` | C16 | — | items 32 required (verdict may flip), 12 reusable (inapplicable to those candidates); auto-approved (all required within budget) |
| M+6 | `run.continued`, then `run.created` | human:operator O1 (terminal, interactive) | task_T1 stream; run_R1r, bind_R1r | `run continue --kind rerun`: continuation_kind rerun, sweep_scope rerun_plan, chain_id chain_C1, continues_run_id run_R1, edits_since_parent [rules@v2 by hd_H9]; executes the plan approved at M+5; run_R1 stays completed and is not re-entered (seq numbering continues here for readability; run_R1r's own journal starts at seq 1) |
| M+7 | `round.opened` | controller | round_R1r_1 | scope: the 44 stale cells |
| M+8..M+39 | `candidate.assessed` | assessor | asm_… | 32 recomputed with reuse_decision recomputed; 12 reused_valid |
| M+40 | `leaderboard.snapshot_published` | C12 | lb_T1_2 | change_records: 3 status_changed, 1 unrank; each cause chg_7f3a21 |
| M+41 | `round.closed` | controller | round_R1r_1 | stop; stop_reason round_limit_reached; sweep complete for sweep_scope rerun_plan |
| M+42 | `run.completed` | controller | run_R1r | — |

### 11.3 Evidence-refresh run changing one candidate's state

| seq | event kind | actor | ids | summary |
|---|---|---|---|---|
| 1 | `run.continued`, then `run.created` | human:operator O1 | task_T1 stream; run_R2, bind_R2 | `run continue --kind refresh` from run_R1r: same task_T1@v1; rules@v2; new cutoff D+90; sweep_scope refresh_delta against the parent snapshot lb_T1_2; chain_id chain_C1 |
| 2–9 | `tool.*`, `evidence.admitted` | retriever | step_… | 6 new claims admitted; evs_T1_2 frozen |
| 10 | `round.opened` | controller | round_R2_1 | trigger_class new_external_evidence; referent claim_K44 |
| 11 | `evidence.conflict_recorded` | C9 | — | claim_K44 conflicts with claim_K12 on attr_A2 for cand_X |
| 12 | `candidate.assessed` | assessor | asm_X_A2 | verdict unknown_conflicted; counter_evidence_disposition found_and_unresolved |
| 13 | `human.review_requested` | C18 | q_Q12 | hard rule conflict → expert judgement required |
| 14 | `human.review_decided` | human:expert E1 | hd_H12 | conflict_resolution: claim_K44 preferred (independence group distinct, full text read); reason recorded |
| 15 | `candidate.assessed` | assessor | asm_X_A2 | re-evaluated: verdict fail |
| 16 | `leaderboard.snapshot_published` | C12 | lb_T1_3 | change_record: cand_X exclude (provisional → rejected); cause hd_H12 and claim_K44; explanation_status evidence_linked |
| 17 | `round.closed` | controller | round_R2_1 | stop; stop_reason round_limit_reached; sweep complete for sweep_scope refresh_delta |
| 18 | `run.completed` | controller | run_R2 | — |

---

## 12. Integrity rules (summary)

1. One `seq` space per stream (design §2.4); artifacts carry `journal_seq`; nothing resets on resume.
2. Every version has a creating event; every change has a `cause`; every decision has a visibility manifest and an Independence Declaration.
3. Corrections supersede; nothing is rewritten or deleted.
4. Heartbeats never advance counters; `planned` changes only through `progress.estimate_revised`.
5. `budget_exhausted` → `unresolved`; no label maps an unresolved state to advancement (C2).
6. A new round requires a Continuation decision with a referent-backed open question; retries, revisions, human edits, report revisions, and refresh runs are distinct signatures.
7. Reuse requires artifact existence and fingerprint match, except the always-recompute classes; human-approved records are never silently re-derived.
8. Agent verdicts, software statuses, human scientific approvals, and operations decisions are four disjoint fields; only `hd_` records carry the third.
9. Every command has a `command_id` and is applied at most once; a command whose `basis` predates a change that breaks its precondition is rejected, never merged; a disagreement between experts is recorded with `disputes_decision_id`, never by replacing the earlier decision (design §2.4).
10. No surface shows an effect before the event that records it; neither the surface nor the host platform changes a record's content, fingerprint, or verdict.
11. A run continuation is a new run; a run that has ended is never re-entered, and each run of a chain is reported with its own binding, termination reason, and completeness.
12. A provisional skill or lesson influences a step only through a journaled `memory.recalled`, in a `warm` run of its own group; nothing provisional crosses groups.

Sources: `optimized_design.md` Sections 0, 4.1–4.3, 4.9–4.12, 4.16, 6, 11, 12, 14; `agent_reports/human_review_and_ui.md` (F1–F9, §3, §6, cross-review); `agent_reports/reference_harness_inspection.md` (§2.1, §3, F1–F4, F9, cross-review); `agent_reports/mas_architecture.md` (A3, C1, C2, E2, H2 and cross-reviews); `agent_reports/evidence_and_policy.md` (§3.1, §4, §5).
