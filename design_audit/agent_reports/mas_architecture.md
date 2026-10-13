# Workstream 2 — MAS Architecture and Reuse Audit

Design only; no implementation code. Citations are read-only inspections of `/home/yiwei3_duke/anny/reference_repos/Agentic-Doping-snapshot` at commit `0007ad1` (tip of `origin/cloud_deployment`); paths are relative to `src/agentic_doping/`, line numbers as of that revision.

## Summary

The inspected system is **not** a proposer–critic–arbiter triad: it is a proposer, two heterogeneous critics (deterministic chemistry critic plus blind model reviewer), and a **deterministic combination gate** (`dual_agent/reviewer.py:601-686`). That shape is a better v1 default than an LLM arbiter and should be chosen deliberately. Independence rests on four mechanisms — withheld inputs, a deterministic offline check, citation cross-checking against an injected catalog, model-family separation — of which the last only warns (`dual_agent/reviewer_routing.py:18-30`) and human sign-off is a default pass-through (`dual_agent/harness.py:84-92`). **The single most important change: make execution state, bounded-loop termination, and state labels one core-owned registry with a declared UI mapping** — one unresolved outcome currently carries three labels in code plus a fourth, contradictory account in the project's own docs. No planner, step graph, per-step budget, or stale/rerun propagation exists in the code; these are new work, not adaptations. One provider path cannot return tool results to the model yet reports itself tool-capable (`core/llm_client.py:139-151` versus `:342-410`). Scoped memory is the most reusable subsystem, but one path auto-writes candidate-specific "avoid X" rules as prompt-injected method while bypassing the content guardrail (`harness/memory.py:422-456`) — the mechanical analogue of letting "make surufatinib win" become a method. Nothing here claims that more agents, debate, or rounds improve screening: every multiplicity is a measurable configuration parameter, and the evidence questions are deferred to the literature and evaluation workstreams.

## Units of work

| Unit | Definition | Owner | Reference precedent |
|---|---|---|---|
| Screening round | one scheduled evidence/evaluation pass yielding an auditable assessment or leaderboard snapshot; may span many tools and roles | Run Controller | none; `round_` is a revision counter (`dual_agent/loop.py:204`) |
| Review exchange | one proposal → critique (→ adjudication) cycle inside a round | Protocol engine | `loop.py:209-292` |
| Self-correction turn | proposer revises after its own deterministic self-check, before any critique | Protocol engine | `loop.py:219-224` |
| LLM turn | one model call; never a round | Model broker | `core/llm_client.py:433-487` |
| Tool retry | same call, same inputs, new `attempt_no` on one request id | Tool broker | `llm_client.py:226-246` |
| Human edit | attributed change; new version plus staleness marks | Review queue | `orchestration/recommend.py:239-246` (request field only) |
| Evidence-refresh run | later run on the same task context, new run id | Run Controller | `recommend.py:207-238` (continue/resume only) |
| Report revision | new narrative-report version | Reporting | `analysis/report_iteration.py` (package note 07) |

The reference conflates two: one counter advances both on self-check failures (`loop.py:219-224`) and on critique-driven revisions (`:277-281`), so a proposal can spend its budget without ever being critiqued.

## Core-owned state machines

| Level | States | Terminal |
|---|---|---|
| Run | `queued`, `running`, `waiting_tool`, `waiting_human`, `retrying`, `paused`, `completed`, `unresolved`, `failed`, `cancelled` | `completed`, `unresolved`, `failed`, `cancelled` |
| Stage | as Run plus `skipped` (needs reason and reuse reference) | `completed`, `unresolved`, `skipped`, `failed` |
| Step | `queued`, `running`, `waiting_tool`, `waiting_human`, `retrying`, `completed`, `rejected`, `unresolved`, `failed` | `completed`, `rejected`, `unresolved`, `failed` |
| Review exchange | `proposed`, `critiqued`, `revising`, `adjudicating`, `completed`, `rejected`, `unresolved` | `completed`, `rejected`, `unresolved` |
| Candidate decision | `unassessed`, `provisional`, `recommended`, `rejected` | all, revisable with a recorded reason |

Exchange transitions: `proposed → critiqued` on critic return; `→ completed` when every required independent check passes; `→ rejected` on an evidence-backed hard exclusion; `→ revising → proposed` when a concern is actionable and budget remains; `→ adjudicating` on persistent disagreement, ending `completed` with recorded dissent or `unresolved`; `→ unresolved` on budget exhaustion. Every terminal transition carries a `termination_reason` from one enumeration — `sufficient_support`, `no_actionable_step`, `diminishing_information_gain`, `repeated_failure`, `budget_exhausted`, `human_decision`, `dependency_unresolved`, `cancelled` — and `budget_exhausted` always maps to `unresolved`, never to acceptance.

## A. Roles, independence, artifacts

### A1. There is no arbiter; adjudication is deterministic, and that is the better default

**Issue.** Fixed precedence in a pure function: a deterministic rule-critic hard failure forces `reject` regardless of the model verdict, otherwise the model reviewer's quality threshold selects `accept` or `revise`, and the rule-only path caps the published promise value so an evidence-free score cannot claim high promise. Calling this an arbiter without saying it is deterministic invites a third LLM role that adds cost and correlated judgement, not an independent check.

**Source / location.** `reviewer.py:601-686` (veto `:604-631`, accept/revise `:651-657`, rule-only cap `:658-686`); `loop.py:230-292`.

**Importance.** High — it decides whether v1 runs three LLM roles or two plus deterministic adjudication, and whether the independence claim holds.

**Recommended change.** An **Adjudicator** with two modes: *deterministic policy adjudication* (default; declarative precedence table over typed critic findings) and *escalated adjudication* (only on persistent disagreement where no rule applies, obliged to emit a decision with recorded dissent or `unresolved` plus a named evidence request). An LLM arbiter is configuration, never default; the table is core, the findings taxonomy it ranks is adapter-supplied.

**Tradeoff.** Deterministic adjudication cannot reconcile novel conflicts, so it yields more `unresolved` outcomes and more human-review load.

**Unresolved uncertainty.** Whether escalation improves decisions at matched budget is for the evaluation and literature workstreams; both modes must be swappable and separately measurable.

### A2. Independence must be declared as enforced mechanisms; one of four is unenforced

**Issue.** The reference asserts reviewer independence in prose while relying on four mechanisms of unequal strength, one warning-only and one a default no-op; inheriting the prose would overstate verification.

**Source / location.** Withheld inputs: `loop.py:1-14` with `harness.py:1121-1124` (the reviewer step takes a dialogue argument for interface uniformity and does not pass it on, while the revision step does inject the thread, `:1265-1273`). Deterministic critic: `reviewer.py:474`, always invoked at `:697`. Citation cross-check: `reviewer.py:206-309`, downgrading over-claimed evidence classes and never upgrading (`:237-244`). Model-family separation: `reviewer_routing.py:18-30` (same family returns a warning string). Human sign-off: `harness.py:84-92` (approval returns true by default) with `:62-74` (`require_verification: bool = False`).

**Importance.** High — the brief forbids inferring human scientific approval from an agent verdict or status field.

**Recommended change.** An **Independence Declaration** per decision: `decision_id`; `checks[]` with `check_kind` (`deterministic_rule`, `blind_model_critique`, `cross_family_model_critique`, `source_catalog_verification`, `tool_measurement`, `human_expert_review`), `actor_id`, `model_family?`, `inputs_withheld[]`, `result` (pass/fail/inconclusive), `finding_refs[]`; derived `independence_level` (`none`, `heterogeneous_model`, `deterministic_plus_model`, `human_reviewed`); `warnings[]`. The core must refuse to publish `recommended` when the case configuration requires an absent human-review check, and the leaderboard must render the level.

**Tradeoff.** Requiring heterogeneous critics and human checks for `recommended` lowers throughput and may empty the recommended set, which the brief accepts.

**Unresolved uncertainty.** Whether cross-family critique decorrelates errors here is unestablished; the warning-only treatment reflects single-provider availability and must stay a recorded limitation.

**Revised after cross-review:** withheld inputs is path-dependent, not enforced — on the preferred tool-calling harness the reviewer is shown the proposer's rationale (`agent_harness.py:920-925`, `proposer.py:132-136`), so `blind_model_critique` must be a computed per-critique field rather than a role property, and the H1 row "Withheld-input critic" means the file-chat path's withholding only.

### A3. Artifacts are flattened ad-hoc dictionaries; the core needs one envelope and typed payloads

**Issue.** The review result is a dictionary of over twenty keys duplicated across rule, model, combined, and flattened copies, and the web layer re-derives fields by chained fallbacks over those three sources, so consumers disagree about which copy is authoritative — the ambiguity behind Finding H2.

**Source / location.** `reviewer.py:689-729`; `web/server.py:978-1019`.

**Importance.** High — round history, version diffs, and rationale navigation must all derive from persisted truth.

**Recommended change.** One **Artifact Envelope**: `artifact_id`, `artifact_kind`, `schema_version`, `task_context_id`, `run_id`, `round_id`, `exchange_id?`, `parent_artifact_id?`, `supersedes?`, `actor` (`actor_kind` = agent/tool/human/system, `actor_id`, `role`, `model_family?`, `policy_version?`), `created_at`, `seq`, `state`, `termination_reason?`, `evidence_refs[]`, `payload`, `payload_sha256`, optional `adapter_extensions` excluded from core logic. Payloads and states:

| Kind | Key payload fields | States |
|---|---|---|
| Evidence request | `question`, `decision_relevance`, `requested_evidence_kinds[]`, `target_criterion_id?`, `target_candidate_id?`, `budget`, `acceptance_test` | `open`, `assigned`, `answered`, `unanswerable`, `withdrawn` |
| Proposal | `subject` (criterion/rule/candidate_assessment/plan), `content_ref`, `rationale`, `addressed_findings[]`, `assumptions[]` | `draft`, `submitted`, `revised`, `withdrawn` |
| Critique | `findings[]` (`finding_id`, `class`, `severity`, `target_field`, `claim`, `evidence_refs[]`, `actionable_request?`), `verdict` (support/revise/reject/inconclusive), `withheld_inputs[]` | `submitted`, `superseded` |
| Revision | `base_proposal_id`, `changes[]` (`field_path`, `before`, `after`, `reason`, `finding_refs[]`), `unaddressed_findings[]` | `submitted`, `superseded` |
| Tool request | `tool_id`, `contract_version`, `inputs`, `idempotency_key`, `budget`, `expected_output_kind` | `queued`, `dispatched`, `succeeded`, `failed`, `timed_out`, `cancelled` |
| Tool result | `tool_request_id`, `attempt_no`, `status`, `outputs`, `units`, `uncertainty?`, `error` (`code`, `class`, `retryable`), `measurement_kind` (model_prediction/simulation/curated_measurement/instrument_measurement) | `returned`, `superseded`, `stale` |
| Decision | `subject_ref`, `outcome`, `independence_declaration`, `dissent[]`, `override_reason?`, `rule_version`, `evidence_cutoff` | `provisional`, `confirmed`, `superseded`, `reverted` |
| Human decision | `queue_item_id`, `person_id`, `action` (approve/reject/edit/request_followup/defer), `scope`, `reason`, `attested_at`, `affected_refs[]` | `recorded`, `superseded` |

**Tradeoff.** A uniform envelope costs mapping work at every boundary and can block legitimate adapter fields.

**Unresolved uncertainty.** Whether tool results need a round id in single-pass mode is a modelling choice; always creating one round is safer.

### A4. Keep verification deterministic; add retrieval as a role; justify further personas by measurement

**Issue.** In the reference the counter-evidence function is a deterministic verifier, not an agent, and literature work is a budgeted tool surface with its own failure records rather than a persona; promoting either to an LLM role adds correlated judgement and cost without adding an independent check.

**Source / location.** `reviewer.py:206-309` (verification with `rejected_refs` reason codes); `harness.py:1145-1222` (research budget, cache reuse, `required_unfulfilled_reason`, outage recorded as a completed no-evidence attempt at `:1198-1206`); `orchestration/gap_discovery.py:42-61`, `:80-112`.

**Importance.** Medium — it sets roster size and cost but extends later without protocol change.

**Recommended change.** v1 roster: Planner/Delegator, Proposer, Deterministic Validator (adapter checks), Blind Critic, Evidence Retriever (own budget and provenance duties), Adjudicator, Human Reviewer. Counter-evidence is a required search obligation plus deterministic verification, not a persona. A separate Evaluator runs outside the decision path on fixed evidence snapshots so it cannot influence the run it measures. Personas are addable by configuration.

**Tradeoff.** Fewer personas means fewer viewpoints if heterogeneous critics later prove to decorrelate errors.

**Unresolved uncertainty.** Whether an adversarial persona finds disconfirming sources an obligated retriever misses is unmeasured; the literature workstream should report on devil's-advocate roles.

## B. Planning and delegation

### B1. There is no planner: the plan is a fixed nine-stage pipeline with one global round budget

**Issue.** The plan is one orchestrator function's control flow, documented as nine sequential steps; no step, owner, budget, or completion criterion exists as data, so nothing can be replanned, re-owned after failure, delegated to a person, or costed. The only loop budget is a module constant shared between self-correction and critique, applied per proposal slot rather than per objective.

**Source / location.** `AGENTS.md:19-33`; `recommend.py:231-246`, `:617-628`, `:670-680`; `harness.py:37` (`MAX_ROUNDS = 3`), `:39` (`ACCEPT_THRESHOLD = 0.7`); `loop.py:219-224`, `:277-281`.

**Importance.** High — planning and delegation are the first reusable core mechanism the brief names, and nothing here can be adapted for them.

**Recommended change.** A **Plan** record: `plan_id`, `task_context_id`, `plan_version`, `parent_plan_id?`, `objective_ref`, `steps[]`, `budget_envelope`, `created_by`, `approval_state` (draft/approved/executing/superseded). Each step: `step_id`, `question`, `owner` (`owner_kind` = agent_role/tool/human, `owner_ref`), `inputs[]`, `depends_on[]`, `budget` (`llm_turns`, `tool_calls`, `wall_clock_s`, `cost_units`, `human_minutes`), `completion_criteria[]` as inspectable predicates over artifacts (for example: every admitted candidate has a per-criterion record with provenance), `on_failure` (retry/escalate_human/mark_unresolved/skip_with_reason), `produces[]`, `state`. Budgets are separate per loop class: `self_correction_turns`, `review_exchanges`, `tool_retries`, `evidence_requests`, `screening_rounds`. Agent roster and `screening_rounds` are independent run-configuration fields: a single-pass run sets `screening_rounds = 1` and still fans several roles across steps within that pass, producing the snapshot at round close.

**Tradeoff.** A declarative plan adds an interpretation layer and new failure modes such as circular plans; ship the nine stages as a default template a planner may specialize.

**Unresolved uncertainty.** How much planning autonomy helps is unmeasured, so fixed-template, template-with-insertions, and free planning should all be expressible for comparison.

## C. Orchestration state, bounded loops, continuation

### C1. Execution state is three labels and the progress counter is not a durable sequence number

**Issue.** The persisted vocabulary is `running`/`done`/`error`, extended out of band to `stopped` by a server-side finalizer, so a run blocked on a person is indistinguishable from one computing. The event stream has two event types, and the version counter is an in-process integer starting at zero, so after a resume versions restart and a consumer cannot order or replay history — while the brief requires resume by replaying from a sequence number.

**Source / location.** `orchestration/run_dir.py:96-121` (counter initialized to zero, written as `progress_version`), `:128-143` (terminal write, percent 100 or 0), `:168-192` (out-of-process finalizer adding `stopped`), `:195-217` (heartbeat refreshing a timestamp without advancing work).

**Importance.** High — honest progress, stale marking, resume lineage, and review visibility all depend on this layer.

**Recommended change.** Make the append-only **Event Journal** the single source of truth with a store-assigned monotonic `seq` per run, deriving both the UI projection and the resume position from it. Event kinds: `run_*`, `stage_*`, `step_*` (queued, started, progressed, waiting_tool, waiting_human, retrying, paused, resumed, completed, rejected, unresolved, failed, cancelled), `tool_requested`, `tool_returned`, `tool_failed`, `artifact_written`, `decision_recorded`, `human_action`, `staleness_marked`, `heartbeat`. Heartbeats are liveness only and never advance completed work — a separation the reference already observes and should keep explicitly.

**Tradeoff.** A journal-derived projection costs more writes and needs snapshots for long runs; caching it reintroduces divergence risk.

**Unresolved uncertainty.** Whether per-event durability or batched writes suffice depends on the deployment the tools workstream specifies.

### C2. Bounded loops exist, but only one records why it stopped

**Issue.** The proposal loop handles exhaustion correctly — at maximum rounds a borderline proposal becomes `exhausted` and is explicitly not admitted, with an in-code note that treating it as accepted made the reviewer gate cosmetic. The model tool loop does not: on hitting the iteration cap it exits, returning whatever final text and stop reason the last response carried, so a finished answer and an exhausted budget are indistinguishable. The literature budget, by contrast, records an explicit exhaustion reason.

**Source / location.** `loop.py:282-292`; `core/llm_client.py:433`, `:481-487`; `harness.py:1157-1161`.

**Importance.** High — a loop that cannot report exhaustion cannot honour the rule that a budget limit yields `unresolved`.

**Recommended change.** Every bounded loop returns a **LoopOutcome**: `loop_kind`, `iterations_used`, `budget`, `outcome` (completed/rejected/unresolved), `termination_reason`, `open_questions[]`, `partial_results_ref?`. No caller may read a missing terminal marker as success.

**Tradeoff.** Strict reporting surfaces more `unresolved` outcomes and queue items, reading as a throughput regression while being an honesty improvement.

**Unresolved uncertainty.** Whether partial tool-loop output is kept as evidence or discarded needs a policy; keeping it risks citing half-finished analysis.

### C3. Continuation triggers are free-text gaps with no decision-relevance test and no durable record

**Issue.** Continuation is decided by asking a model for valuable open questions as searchable phrases, then counting new papers and new knowledge per phrase. Gaps are transient strings with no state, no statement of which decision they would change, and retrieval failure reduced to one code in a return value, so nothing prevents re-asking a barren question or separates a decision-relevant gap from an interesting one.

**Source / location.** `gap_discovery.py:22-30` (prompt), `:42-61`, `:80-112` (per-gap `fetch_failed`, new-paper and new-knowledge counters), `:115-129` (light inline versus deep on-demand budgets).

**Importance.** High — this mechanism decides whether another round happens.

**Recommended change.** An **Open-Question Register**: `question_id`, `task_context_id`, `question`, `trigger_class` (`new_external_evidence`, `unresolved_conflict`, `consequential_missing_measurement`, `questionable_exclusion`, `decision_relevant_computation`), `affects[]` (criterion and candidate refs), `expected_decision_change` (which status or ordering changes, for which candidate), `acceptance_test`, `attempts[]` (`attempt_no`, `method`, `result`, `information_gain` as resolved-conflict or newly-admitted-source counts, `cost`), `state` (open/assigned/answered/unanswerable/withdrawn/deferred), `priority`. Another round is admissible only if an open question has a non-empty expected decision change and an untried method within budget. Stopping criteria at round close: `sufficient_support` (all admitted candidates have complete per-criterion records with independent support), `no_actionable_step`, `diminishing_information_gain` (last *n* attempts yielded no new admitted evidence or resolved conflict), `repeated_failure` (same method failed *k* times), `budget_exhausted`; only the first permits a `completed` run.

**Tradeoff.** Demanding an expected decision change suppresses open-ended search that sometimes pays off, and gain proxies are gameable; keep a separately budgeted exploratory mode whose results cannot promote a candidate without targeted confirmation.

**Unresolved uncertainty.** Gain thresholds cannot be set from this inspection and must be calibrated against the single-pass and fixed-round baselines.

## D. Tool-result feedback

### D1. One provider path cannot feed results back, yet is advertised as tool-capable

**Issue.** The Anthropic path is a real loop: it appends the assistant's tool-use blocks, dispatches each call, converts exceptions into an error payload rather than failing, appends results as the next user message, and iterates while the stop reason is tool use. The bridge path is one shot: it posts one request, receives an intended tool-call list plus final text, dispatches those calls locally, and returns without sending results back, so the final answer predates every tool result. The capability probe still reports that provider as tool-capable, so the harness selector believes a feedback loop exists.

**Source / location.** `core/llm_client.py:443-481` (loop; errors fed back `:467-471`; results appended `:478-480`); `:342-410` (one-shot bridge; local dispatch `:392-396`; final text from the same single response `:397`); `:139-151` (probe returning true for that provider at `:143-144`); `loop.py:168-180` (selector); `AGENTS.md:57-70` (an OpenAI-style provider has no tool loop at all).

**Importance.** High — the brief requires confirming that the framework returns tool outputs into later reasoning; here declared capability and implemented behaviour differ inside one codebase.

**Recommended change.** Replace the boolean probe with a **Model Adapter Capability Record**: `adapter_id`, `provider_family`, `accepts_tool_schemas`, `returns_tool_results_to_model` (yes/no/unknown), `max_tool_iterations`, `structured_output_mode` (native_tool/json_mode/text_parse), `error_feedback_supported`, `verified_by` (contract-test run id), `verified_at`. The core refuses feedback-dependent protocols unless the record says yes, and degrades explicitly as a recorded step-level `unresolved` or a policy-approved single-shot mode. Contract tests: *echo* (report a nonce only the tool can supply); *error recovery* (a typed error is followed by a corrected second call); *two-step dependency* (tool B's input derives from tool A's output); *iteration cap* (reports `budget_exhausted`, not a plausible answer); *idempotency* (a replayed request with the same key does not double-execute a side-effecting tool); *provenance* (every cited tool result is retrievable from the journal by request id).

**Tradeoff.** Capability gating blocks otherwise usable providers until the tests run, and per-adapter tests are ongoing work.

**Unresolved uncertainty.** Whether a queue or HTTP bridge worker can carry results back is for the tools workstream; the reference states that selecting that provider does not start a worker.

### D2. Failure handling is all-or-nothing: one tool failure ends the run, one candidate exception disappears

**Issue.** A numerical-evaluation failure for a single shortlisted candidate finalizes the whole run as an error and returns, discarding every other candidate's completed assessment; conversely a candidate whose own pipeline raises is logged internally and skipped, vanishing from the leaderboard with no record, whereas a *handled* failure correctly yields an entry with a typed reason.

**Source / location.** `recommend.py:681-689`; `:643-648`; `:657-667`.

**Importance.** High — failures must be findings, missing must differ from failed, and reduced results must be reported rather than omitted.

**Recommended change.** Isolate failure at step level: a tool failure marks that step `unresolved` with the typed error and leaves the affected criterion cell `unknown` with reason `measurement_unavailable`, while the run continues and closes `unresolved` if that measurement was decision-relevant. Every candidate entering a round must leave it with a decision state and a per-criterion row; dropping a candidate from the output set is prohibited. Add `run_degradation[]` (`degradation_kind`, `component`, `reason`, `approved_by`) so fallbacks such as the heuristic-proposer substitution (`dual_agent/agent_harness.py:616-619`) are visible rather than inferred from a provenance label.

**Tradeoff.** Continuing publishes leaderboards with many `unknown` cells that readers may over-read as assessed, so evaluation completeness must sit beside status.

**Unresolved uncertainty.** Which missing measurements should block a round from closing at all needs domain-adapter judgement.

## E. Dissent, recovery, lineage, staleness

### E1. Dissent is preserved only when the decision is negative

**Issue.** A rejection writes a dedicated kill-argument artifact naming the killer and reason and appends a failure entry, while an acceptance that overrides informational critic concerns records no dissent: those concerns survive only inside the review blob, not in the decision.

**Source / location.** `loop.py:267-276`; `:262-266`; `reviewer.py:1-14` and `:604-631` (radius concerns informational by design).

**Importance.** High — one-sided dissent recording makes admissions look more consensual than they were.

**Recommended change.** Every Decision carries `dissent[]` (`finding_id`, `raised_by`, `severity`, `status` = addressed/overridden/deferred, `override_reason`, `evidence_refs[]`), and validation fails when an unaddressed major finding lacks an override reason. Persistent disagreement escalates to adjudication, then to the human queue; `unresolved` is a legitimate end state.

**Tradeoff.** More friction on admissions and more queue items for overrides that are often routine.

**Unresolved uncertainty.** Which finding classes count as major is adapter-specific, to be set with the evidence workstream.

### E2. Checkpoint reuse is file-existence based and nothing is ever marked stale

**Issue.** Continue and resume reuse a prior stage's output if its file exists, with no check that inputs, policy version, or evidence cutoff still match, and reuse is visible only as an internal log line plus a free-text source label; human-approved targets arrive as a request field. No path invalidates downstream results after an edit or refresh, so "which results must rerun" is unanswerable, and the per-candidate ledger picks the current record by timestamp comparison rather than a sequence number.

**Source / location.** `recommend.py:207-238`, `:239-246`, `:817`; `evidence_ledger/ledger.py:45-51`.

**Importance.** High — resume lineage, reuse transparency, and rerun propagation are explicit brief requirements.

**Recommended change.** A **Reuse Record** per step: `step_id`, `input_fingerprint` (hash over input artifact ids and versions, rule version, policy version, evidence cutoff, adapter versions), `reused_from_step_id?`, `reuse_decision` (recomputed/reused_valid/reused_overridden_by_human/invalidated), `validity` (fresh/stale/superseded), `staleness_cause?`. Derive a dependency graph from `depends_on` and `evidence_refs`; a human edit or evidence refresh marks all transitive dependents `stale` and emits a **Rerun Plan** (`items[]` with `reason`, `cost_estimate`, `required`/`optional`) for approval. Reusable without re-evaluation: deterministic builds and tool results whose fingerprints match, plus prior evidence records. Always re-evaluated: criterion applicability, per-candidate decisions, adjudications, leaderboard snapshots, and any model-authored rationale, since their inputs include the changed version.

**Tradeoff.** Fingerprints over-invalidate on immaterial changes and waste computation; coarser ones risk publishing results derived from superseded rules.

**Unresolved uncertainty.** Whether every rerun plan needs human approval or only those above a cost threshold is a UI decision.

## F. Scoped memory

### F1. Trust state needs separate axes; a completed computation must not label itself verified

**Issue.** Memory records resolve to `pending`, `provisional`, `approved`, or `verified`, and absent an explicit state a record whose evidence kind is a deterministic rule or a computed evaluation tier is treated as `verified`, conflating a completed computation with a validated claim; the brief's two-state model is meanwhile too coarse to separate a human-approved hypothesis from an instrument measurement.

**Source / location.** `harness/memory.py:81-98`, `:265-267`, `:378-380`.

**Importance.** High — this boundary stops tool success from becoming scientific validation.

**Recommended change.** Three independent fields: `memory_kind` (evidence/tentative_hypothesis/reusable_procedure); `support_basis` (llm_opinion, deterministic_check, model_prediction, simulation, curated_measurement, instrument_measurement, expert_statement, human_curation); `review_state` (provisional, under_review, approved, rejected, retired). Recall eligibility is a policy over the triple, `approved` is reachable only through a human action record, and no `support_basis` implies a `review_state`. Keep the reference's group and role scoping (`memory.py:64-66`, `:207-218`): approved records inherit, provisional records stay same-group and role-visible, nothing provisional crosses groups.

**Tradeoff.** Three fields mean more curation work and more mis-tagging routes than one ladder.

**Unresolved uncertainty.** Whether deterministic checks should ever be injected as prompt context rather than simply executed is open; executing them is safer.

### F2. One path writes candidate-specific avoidance rules as reusable method, bypassing the guardrail

**Issue.** Adding a lesson triggers automatic skill promotion that, after a repeat threshold or at once for a non-viability flag, writes a prompt-injected procedure naming the specific candidate entity and site. The content policy that exists to stop a candidate result becoming future method is not applied there; it runs only in post-run reflection and the two harness-authored skill paths. This is the structural analogue, inverted in sign, of letting "make surufatinib win" become a method.

**Source / location.** `harness/memory.py:247-279` (lesson write triggering promotion at `:278`), `:422-456` (auto-authored text embedding entity and site), `:363-390` (skill write with no policy call); policy invoked only at `orchestration/reflection.py:210-212`, `harness.py:1058-1060`, `agent_harness.py:338-340`; policy vocabulary is materials-specific at `harness/skill_policy.py:16-60`, checks at `:140-213`.

**Importance.** High — both a guardrail bypass and a route by which an unreviewed exclusion propagates across runs.

**Recommended change.** One chokepoint: every procedural-memory write, automatic ones included, passes the policy check and returns stable violation codes. Candidate-specific conclusions belong in the **Criterion Registry** as a reviewable sourced rule, or in an exclusion record attached to that candidate — never in prompt-injected procedure. Move the vocabulary into the adapter behind a core contract `check_procedure(text_fields, forbidden_entity_lists, numeric_claim_policy) -> {ok, violation_codes[]}`, core owning codes and adapter owning lists and patterns, and add a positive requirement that a procedure state when it applies, what to do, and what evidence would retire it.

**Tradeoff.** A single chokepoint can block legitimate automatic learning and reject wording a human would accept, so rejected candidates should queue for review rather than be discarded.

**Unresolved uncertainty.** Denylists are evadable by paraphrase; whether a classifier or a structured procedure form is the better long-term guard is unresolved, and the structured form is the safer v1.

### F3. Credit and recall asymmetries can entrench over-acceptance and over-exclusion

**Issue.** Procedure credit increments when a proposal is accepted — on a model verdict, not a verified outcome — so a procedure that persuades the reviewer accrues credit; recall is asymmetric the other way, withholding positive loop outcomes unless curated while recalling rejection and kill lessons freely, which can entrench incorrect exclusions.

**Source / location.** `harness.py:1276-1284`; `harness/memory.py:817-830`, `:299-307`, `:323-333` (raw verdicts deliberately non-persistent — the right default).

**Importance.** Medium — it governs cross-run behaviour rather than a single-pass v1 case.

**Recommended change.** Credit procedures only on outcomes confirmed by a deterministic check, a measurement, or a human decision, recording `credit_basis` beside the count, and never let usage counts gate recall alone. Apply the same review requirement to exclusion lessons as to admission lessons, and require any recalled exclusion that blocks a candidate to be cited in that candidate's rejection record so it is visible and appealable.

**Tradeoff.** Symmetry slows accumulation of useful negative knowledge and adds review load.

**Unresolved uncertainty.** Whether recalled exclusions change later proposals enough to matter needs the ablation the evaluation workstream designs.

## G. Enforcing the three-layer separation

### G1. Separation needs import direction, a capability registry, and a start-of-run binding

**Issue.** The orchestrator imports domain modules directly, the reviewer imports a domain knowledge package, the domain intermediate representation sits in the shared schemas package, and the guardrail vocabulary is domain-specific, so nothing structural keeps domain concepts out of core logic.

**Source / location.** `recommend.py:202-205`; `reviewer.py:22`; `schemas/doping_ir.py:35-215`; `harness/skill_policy.py:16-60`.

**Importance.** High — this separation is a hard brief requirement and the main source of reuse beyond this case.

**Recommended change.** The adapter implements declarative ports: **Vocabulary** (`entity_kinds`, `identifier_schemes`, `aliasing_rules`, `units`, `unit_conversions`); **Criterion Templates** (`template_id`, `attribute_definition`, `direction`, `applicability_conditions`, `evidence_requirements`, `default_rule_form`); **Evidence Sources** (`source_id`, `access_mode`, `evidence_kinds_supplied`, `provenance_fields`, `cutoff_semantics`, `absence_behaviour`); **Tool Contracts** (`tool_id`, `inputs`, `outputs`, `units`, `uncertainty_semantics`, `measurement_kind`, `failure_modes`, `cost_model`, `absence_behaviour`); **Deterministic Validators** (`validator_id`, `finding_classes`, `severity_map`, `hard_exclusion_eligible`); **Content Policy Lists**; **Expert Requirements** (`action_kind` → `review_required`, `qualification`, `evidence_to_present`). The core never imports adapter modules, resolving them through a registry keyed by `adapter_id` and `adapter_version`, with a static import-direction check in the later build. The case configuration binds once at run start into an immutable **Run Binding**: `run_id`, `task_context_id`, `objective_ref`, `candidate_universe_ref`, `constraints`, `evidence_cutoff`, `adapter_id`/`adapter_version`, `rule_version`, `policy_version`, `known_reference_outcome_disclosure`, `budget_envelope`, `baseline_configuration_ref`, `bound_at`, `bound_by`. Every artifact cites the binding; changing a bound field requires a new run, not a mutation.

**Tradeoff.** Port indirection adds boilerplate and invites an escape hatch for one urgent domain need, so declined capabilities must be recorded explicitly.

**Unresolved uncertainty.** Candidate identity resolution is genuinely ambiguous — identity is core for ledger joins while alias tables are domain data; the proposal is a core identity service driven entirely by adapter-supplied schemes.

## H. Reuse verdicts and defects to avoid

### H1. Component-by-component reuse verdict

**Issue.** The package lists patterns without saying which are reusable as implemented, so an implementation phase could copy mechanisms whose source-level behaviour does not meet this brief.

**Source / location.** Each row cites its inspected location.

**Importance.** High — it sets what may be copied versus designed anew.

| Component | Source | Verdict | Reason |
|---|---|---|---|
| Bounded proposal/review loop | `loop.py:209-292` | Reuse as pattern | Correct exhaustion semantics, preserved kill/exhausted outcomes; split the shared counter, add `LoopOutcome` |
| Deterministic critic plus gate | `reviewer.py:474`, `:601-686` | Reuse as pattern | Uncorrelated check, hard veto, evidence-free score cap |
| Withheld-input critic | `harness.py:1121-1124` | Reuse as pattern | Independence enforced by inputs, not naming |
| Citation cross-check | `reviewer.py:206-309` | Adapt | Catalogue membership and class downgrade are sound; classes and thresholds are domain data |
| Versioned proposal/review artifacts | `loop.py:214-218`, `:232-233`, `:294-300` | Adapt | Keep versioning and latest pointers; replace dictionaries with the A3 envelope, add field-level diffs |
| Anthropic tool-feedback loop | `llm_client.py:443-481` | Reuse as pattern | Results and typed errors return into the next turn; add exhaustion reporting |
| Bridge tool path | `llm_client.py:342-410`, `:139-151` | Redesign | Dispatches without returning results while reporting itself tool-capable |
| Progress and event writer | `run_dir.py:91-143` | Redesign | Three statuses, two event kinds, per-process counter; no waiting, retrying, unresolved, or replay |
| Checkpoint continue/resume | `recommend.py:207-238` | Redesign | File-existence reuse, no fingerprint, staleness, or reuse record |
| Per-candidate ledger | `ledger.py:1-51`, `models.py:23-60` | Adapt | Append-only provenance and typed failures are right; add `seq`, round and actor ids, rule version, typed human review, per-criterion rows |
| Evidence ladder and candidate status | `evidence_ledger/enums.py` | Redesign | One ordinal ladder conflates source class, independence, measurement type; status is pipeline progress, not decision state |
| Scoped memory store | `memory.py:64-66`, `:207-218`, `:299-333` | Reuse as pattern | Group and role scoping, provisional recall limits, non-persistence of raw verdicts |
| Automatic skill promotion | `memory.py:422-456` | Redesign | Writes candidate-specific prompt guidance, bypasses the content policy |
| Content policy for procedures | `skill_policy.py:140-213` | Adapt | Keep the violation-code contract; move vocabulary to the adapter, add a positive-form requirement |
| Post-run reflection | `reflection.py:66-175` | Reuse as pattern | Mechanical process signals, hashed inputs, one provisional procedure, finished run unchanged |
| Gap-directed retrieval | `gap_discovery.py:42-129` | Adapt | Backward flow from held knowledge to targeted search is valuable; gaps must become durable register entries |
| Human verification gate | `harness.py:84-92` | Redesign | In-process pass-through callback cannot represent a durable `waiting_human` state |
| Fixed-vocabulary target contract | `schemas/doping_ir.py`; package excerpt 10 | Adapt | Useful fields (direction, rationale, computation method); criterion derivation must be open-ended and registry-owned |

**Recommended change.** Treat this table as the reuse decision of record; later deviations should be justified against the cited line ranges.

**Tradeoff.** Redesigning five subsystems costs more v1 effort than adapting them, and some of that work delivers no user-visible feature.

**Unresolved uncertainty.** The web and UI layers were inspected only where Finding H2 required; the UI workstream may find further reusable behaviour.

### H2. One unresolved outcome carries three labels in code and a fourth, contradictory account in the docs

**Issue.** When a proposal exhausts its revision budget the loop records `exhausted` and deliberately does not admit it; the trace API maps that state to `sent_after_revision_limit`, asserting it *was* sent onward although the orchestrator builds its plan only from accepted sets; the memory helper renders the same state as `marginal`; and the architecture doc says a borderline set is accepted as `exhausted` and left to downstream evaluation, contradicting the code comment that treating `exhausted` as accepted made the reviewer gate cosmetic. That doc's line references point to an earlier revision, so it is not evidence of current behaviour.

**Source / location.** `loop.py:282-292`; `web/server.py:978-989`; `harness/memory.py:309-310`; `docs/architecture/04-dialogue-loop.md` (design-philosophy bullet and code-location table with stale line numbers); plan construction from accepted sets at `recommend.py:593-610`.

**Importance.** High — a UI label implying acceptance of an unresolved result is exactly the misrepresentation the acceptance target forbids.

**Recommended change.** A core **State Registry**: `state_id`, `level`, `label_authoritative`, `semantics`, `is_terminal`, `implies_admission`, `ui_label`, `ui_tone`, `maps_to_candidate_state?`. No component may introduce a label outside the registry, and the UI reads `ui_label` rather than deriving meaning from a status string. Name this state `unresolved_budget_exhausted` with `implies_admission = false`. Add a contract test asserting that no transport label maps to admission when the authoritative state does not, and require documentation examples to cite a commit.

**Tradeoff.** A registry adds a release step for every new state, and stricter labels read as less reassuring.

**Unresolved uncertainty.** Whether the reference intended eventually to admit exhausted proposals cannot be settled from the snapshot; both readings exist and the code is authoritative here.

## I. Critique of the preliminary spine

### I1. The spine is broadly right but misses six components and misplaces three boundaries

**Issue.** Items 1–13 of the coordinator brief cover most of the needed surface, but several mechanisms this audit found indispensable have no owner, and three responsibilities sit where they will be implemented twice or not at all.

**Source / location.** `design_audit/agent_reports/00_coordinator_brief.md` §5 items 2, 3, 6–13; supported by Findings B1, C1, C3, D1, E2, G1, H2.

**Importance.** High — the spine becomes the module map, so a missing component becomes a missing interface.

**Recommended change.** Add: (i) **Open-Question / Evidence-Request Register** — the continuation trigger has no home (C3); (ii) **Artifact Contract Registry** — envelope and payload schemas with versions, so the protocol does not own serialization (A3); (iii) **Reuse and Staleness Service** — fingerprints, dependency graph, rerun plans, currently folded into the Run Controller where they will be lost (E2); (iv) **Budget and Cost Accountant** — per-step budgets and matched-budget accounting the evaluation plan needs and nothing owns (B1); (v) **Adapter and Model Capability Registry** (D1, G1); (vi) **State Registry** (H2). Move: the Event Journal from position 11 to the foundation on which Run Controller, Evidence Ledger, Criterion Registry, and Leaderboard are projections, since `seq` must be assigned once; give the Human Review Queue ownership of the durable `waiting_human` state and the attestation record instead of making it a consumer of Run Controller state; move ordering-method ownership from the Leaderboard Service to the Criterion Registry, leaving the leaderboard to render decisions it does not compute. Resolve redundancy: Scoped Memory's promotion workflow and Strategy Versioning's promotion criteria are one mechanism at two scopes and should share a promotion record, while the Per-Candidate Assessor must execute rules it never authors, keeping criterion merge, split, and removal solely in the registry. Finally, state what the core must never own — domain vocabulary, thresholds, entity lists, provider specifics — as an enforceable import rule, not a convention.

**Tradeoff.** Nineteen components instead of thirteen is a larger v1 surface, and the two smallest will look like overhead until the first disagreement about a label or a budget.

**Unresolved uncertainty.** Whether the Reuse and Staleness Service can stay adapter-independent is untested; fingerprinting may need domain knowledge of which inputs are semantically material.

## Cross-review of tools_and_data.md

Read in full, 12 October 2026. WS3 and I overlap on tool contracts, result feedback, and core/adapter ownership; its report is stronger than mine wherever provenance is concerned.

**1. Agreements.**
- The thirteen-field provenance block (§1.4) beats the bare `evidence_refs[]` pointer in my A3 envelope; I adopt it as required Tool result content.
- `independence_key` fills a gap my A2 declaration left open: three "sources" repeating one experiment, which role-level independence cannot see.
- Absence as a first-class result with typed `absence_reason` and a `required_inputs_manifest` is the enforceable form of `missing ≠ failed`, which my D2 only asserted.
- `supports_claim` always null from the broker is the structural version of my F1 rule that a completed computation never labels itself verified.
- WS3 Finding 3 (wet-lab intake writing top-tier evidence with a perfect sub-score on successful write) is a sharper instance of my F1 defect class; I had not inspected that file and accept it.
- Finding 5 adds `core/property_semantics.py` to my G1 list of import-direction violations.
- Finding 10 and my C2/B1 agree that retry is never a round and provider health needs its own state.
- The per-dimension `tool_coverage` block (Finding 8) specifies the disclosure my D2 requested.

**2. Objections.**
- *Status conflates two axes.* §1.3 `status` {`ok`, `partial`, `empty`, `absent`, `failed`} classifies outcomes; my A3 {`returned`, `superseded`, `stale`} is a record lifecycle. Theirs cannot mark a stored result stale after an evidence refresh, which my E2 propagation needs, and `absent` reads as the brief's `missing`. Alternative: `outcome` {`ok`, `partial`, `empty`, `not_attempted`, `failed`} plus `record_state` {`returned`, `superseded`, `stale`}.
- *Overlapping vocabularies.* `out_of_domain` and `identity_unresolved` appear in both the error classes and the absence reasons (§1.5), so one event is classifiable either way. Alternative: the dispatch pre-check list discriminates — failure before dispatch is `not_attempted` with an absence reason; a provider judgment is `failed` or `empty`.
- *Retry ownership.* Retry mechanics and the breaker belong in the broker, but the budget must stay a plan-step field (`tool_retries`, my B1) or matched-budget evaluation cannot account for spend, and a tripped breaker changes coverage so it must write my D2 `run_degradation[]`. Alternative: broker owns mechanism and provider health, Run Controller owns budget and authorises fallback, both journal events.
- *The registry omits model adapters.* Resolution by (`capability`, `question_kind`, `required_value_kind`) correctly replaces name-based dispatch for evidence and compute tools but says nothing about whether the language-model adapter returns results into later reasoning — my D1 defect; a perfect tool registry still breaks on a one-shot provider. Alternative: two registries, one verification discipline, each carrying `verified_by` = contract-test run id.
- *Double-encoded absence.* `value_kind: missing` inside `values[]` repeats what `status` says; reserve per-value `unknown` for a record returned with a null field.

**3. Interface conflicts and resolutions.**
- *Identity ownership.* Finding 5 puts identity rules in the adapter; my G1 proposed a core service. Resolution: core owns the identity record, join key and `identity_resolution_status` enum; adapter owns resolution rules and alias tables.
- *Record nesting.* The §1.2 invocation record has `run_id`/`round_id`/`step_id` but no `seq` or `exchange_id`. Resolution: invocation and result records are payloads inside my A3 envelope, which supplies `seq`, `exchange_id` and actor; no duplication.
- *Verdict authority.* No real conflict. Resolution: the Decision artifact is the sole writer of criterion verdicts and the broker's null is enforced by schema, not convention.

**4. Dependencies.** My C3 register consumes their `absence_reason` as its actionability test (`not_configured` → operator task, `no_record_found` → evidence gap, `out_of_domain` → route closed); my E2 fingerprint needs their `data_version`, `parameters_hash` and `determinism_record`; their §6 submission lifecycle supplies my A3 Human decision payload; their coverage block feeds the completeness column my D2 requires.

**5. Resolution summary.**

| Topic | My position | WS3 position | Resolution | Confidence |
|---|---|---|---|---|
| Registry shape | Tool Contracts port | Capability resolution by three keys | WS3 resolution inside my port; core imports no tool module | High |
| Model adapter capability | Capability Record plus contract tests | Not addressed | Two registries, shared `verified_by` | High |
| Result status | Lifecycle states | Outcome statuses | Split `outcome` and `record_state`; rename `absent` | Medium-high |
| Error/absence overlap | Not addressed | Two shared codes | Pre-dispatch is absence; provider judgment is failure | Medium |
| Retry and breaker | Controller budgets | Broker-owned | Broker mechanism, controller budget, breaker writes degradation | High |
| Units, identity, value kind | Core identity service | Core shape, adapter vocabulary | Agreed; identity record core, rules adapter | High |
| Verdict authority | Decision record | Null `supports_claim` | Both, schema-enforced | High |

## Cross-review of reference_harness_inspection.md

Read in full, 12 October 2026. WS7 inspected the same snapshot plus three further repositories and corrects one of my findings at source level.

**1. Agreements.**
- F1 reaches my H2 conclusion independently and improves it with `finalized_by` {worker, controller, human} and one terminal event per attempt.
- F2's record (`state_from`, `state_to`, `cause_seq`, `attempt_id`, `inputs_ref`, `outputs_ref`) is better than my C1 event-kind list; adopted as the journal record.
- F3's three progress levels with an explicit `denominator_known` flag specify the honest-indeterminate rule my C1 only asserted.
- F7's memory record matches my F1 three axes and adds `evaluation_ref`.
- F10's rule that any `approved` status must reference a `decision_id` is the enforcement my A2 lacked.
- F8 confirms across four repositories that no held-out promotion harness exists, supporting my I1 shared promotion record.
- Their finding that the committed sample runs used the one-shot bridge upgrades my D1 from "a provider path cannot feed results back" to "the exercised path cannot".

**2. Objections.**
- *F6 versus my A2 — they are right on the default path.* Source check: `agent_harness.py:920-925` prepends `render_dialogue(dialogue, viewer="reviewer")` to the reviewer's message; `proposer.py:132-136` renders each proposer turn with its rationale truncated to 240 characters; `agent_harness.py:654-657` documents that the reviewer sees how the proposer responded. My A2 cited `harness.py:1121-1124`, the file-chat fallback, where the argument is accepted and unused — true only there, while `loop.py:168-180` prefers the tool harness whenever the provider reports tool support. Withheld inputs is therefore path-dependent and the `loop.py:7-9` docstring is false for the preferred path; A2 now carries a revision note. My narrower objection: their `independence` record must be **computed by the harness from what it actually rendered**, never declared by a role, and my `independence_level` must derive to `none` when `saw_proposer_rationale` is true.
- *Revision check needs a structured diff.* F6's `revision_check` critic sees only its own prior critique plus the new artifact, which cannot establish that a concern was addressed. Alternative: give it the Revision payload's `changes[]` (`field_path`, `before`, `after`, `reason`, `finding_refs[]`) from my A3 — a diff, not persuasive text — preserving blindness to argumentation while allowing convergence.
- *Resume rule too weak.* F9 marks a step `completed` whenever an evaluated artifact exists. Existence is necessary, not sufficient: my E2 requires a fingerprint match over inputs, rule version, policy version, evidence cutoff and adapter versions. Alternative: three outcomes — `reused_valid`, `stale` (rerun), `invalidated`.
- *Never-delete needs scoping.* I accept DGM's staged budgets, noise leeway, and a compile-filter analogue (a strategy failing process-level contract tests never becomes a promotion candidate). But never-delete should cover strategy versions, not every leaderboard snapshot at full fidelity, and must not become never-retire: retired strategies need a status or the archive keeps superseded policies selectable.

**3. Interface conflicts and resolutions.**
- *Event record versus Artifact Envelope.* Resolution: the envelope describes durable content and carries the `seq` of the event that created it; events describe transitions and reference `artifact_id`. `state_from`/`state_to` live only in events.
- *Two exchange vocabularies.* F1 gives outcomes {`completed`, `rejected`, `unresolved`}; mine adds lifecycle states. Resolution: publish both in the State Registry with `is_terminal`; only outcomes appear in user-facing dispositions.
- *Three tool-result vocabularies.* F5 {`ok`, `error`, `timeout`, `cancelled`, `unknown_outcome`}, WS3 {`ok`, `partial`, `empty`, `absent`, `failed`}, mine lifecycle. Resolution for the coordinator: `outcome` {`ok`, `partial`, `empty`, `not_attempted`, `failed`, `unknown_outcome`} plus `record_state`, keeping WS7's rule that every dispatched call gets a result even when its step aborts.
- *Independence records.* Resolution: one record, WS7's fields being the evidence from which my `independence_level` is computed.

**4. Dependencies.** My H2 registry needs F1's mapping table and `finalized_by`; my C1 journal takes F2's record; my units of work gain F9's `attempt` level; my E2 record consumes F9's `continuation` / `evidence_refresh_run` / `reopen` split; my I1 promotion record adopts F8's field list.

**5. Resolution summary.**

| Topic | My position | WS7 position | Resolution | Confidence |
|---|---|---|---|---|
| Reviewer independence | Withheld inputs enforced | Shared transcript implemented | WS7 correct for the preferred path; independence computed per critique | High |
| Revision convergence | Blind critic, bounded rounds | `critique` / `revision_check` split | Adopt split; feed it `changes[]`, not rationale | High |
| Event model | Event kinds | Transition record with `cause_seq` | Adopt WS7 record; envelope keeps content | High |
| State labels | State Registry | Closed vocabulary, sole writer | Same mechanism plus `finalized_by` | High |
| Resume semantics | Fingerprint reuse | Artifact existence | Existence necessary, fingerprint sufficient | High |
| Tool result status | Lifecycle only | `unknown_outcome` for aborts | Combined scheme above | Medium-high |
| Strategy archive | Shared promotion record | Never-delete, staged budgets | Adopt budgets and leeway; scope never-delete; add retired status | Medium-high |

## Contribution record

**Agent identity.** Workstream 2 subagent, "MAS Architecture and Reuse Auditor", launched by this audit's coordinating agent; model Claude Fable 5.1 (`claude-fable-5-1`). No persistent subagent identifier beyond this assignment.

**Times.** Main report: start 2026-10-12T13:05:19Z, end 13:30Z. Cross-review wave: start 2026-10-12T14:05Z, end 14:28Z (UTC).

**Package files read.** `design_audit/agent_reports/00_coordinator_brief.md`; in `MAS_MultiAgent_Design_Audit_EN_20261012/`: `START_HERE_Audit_and_Optimize_Prompt_EN.md` (full), `Project_Brief_EN.md` (sections 1–6 full, 7–9 headings only), `01_Concept_Overview_EN.md`, `02_Agentic_Doping_Reference_EN.md`, `07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md`, excerpts 03–08, and `agentic_doping_reference/SOURCE_MANIFEST.json` (through its sixth excerpt entry; remainder truncated by output limit).

**Repository inspected (read-only, unmodified).** `Agentic-Doping-snapshot`, commit `0007ad1` ("fix: restore distinct energy metrics in screening"), tip of `origin/cloud_deployment`. Read whole or in substantial part: `AGENTS.md`; `dual_agent/loop.py` (whole), `dual_agent/reviewer.py` (`:1-40`, `:189-312`, `:601-729` plus outline), `dual_agent/reviewer_routing.py` (whole), `dual_agent/harness.py` (`:37-100`, `:1084-1291`), `dual_agent/agent_harness.py` (outline, `:572-619`), `harness/memory.py` (`:1-101`, `:247-460`, `:810-840` plus outline), `harness/skill_policy.py` (`:1-60`, `:100-213`), `orchestration/reflection.py` (`:1-175`), `orchestration/run_dir.py` (whole), `orchestration/gap_discovery.py` (whole), `orchestration/recommend.py` (`:200-250`, `:612-690`, plus targeted greps), `core/llm_client.py` (`:139-155`, `:342-496` plus outline), `evidence_ledger/ledger.py` (whole), `evidence_ledger/models.py` and `schemas/doping_ir.py` (field outlines), `evidence_ledger/enums.py` (whole), `evidence_ledger/leaderboard.py` (`:1-70`), `schemas/ledger_record_v1.json` (partial), `pipelines/run_candidate.py` (header), `web/server.py` (`:975-1025`), `docs/architecture/04-dialogue-loop.md` (`:1-45`), `docs/architecture/subsystem-dual-agent.md` (`:1-30`), and the `docs/architecture/` index.

**Tools used.** Bash (git, find, grep, sed, cat -n, python for JSON formatting and word counts) and Read. One scratch file written: `scratchpad/ws2/findings_notes.md`. No repository, package file, or peer report was modified; this report is the only project file written.

**Cross-review wave (appended sections).** Read in full: `agent_reports/tools_and_data.md` (Workstream 3, 6,500 words) and `agent_reports/reference_harness_inspection.md` (Workstream 7, 5,086 words). Neither peer file was modified. To settle the independence dispute I re-opened the snapshot and read `dual_agent/agent_harness.py:648-677` and `:915-944` and `dual_agent/proposer.py:118-162`, which confirm that the tool-calling reviewer path renders the proposer's rationale into the reviewer prompt; Workstream 7's F6 is correct for the preferred path and my A2 cited only the file-chat fallback. That is the one earlier finding I now partly disagree with, and A2 carries a one-line revision note; no other finding was altered. Three-way conflict referred to the coordinator: tool-result status vocabularies differ across Workstream 3, Workstream 7 and this report, with a combined `outcome` plus `record_state` scheme proposed in both cross-review sections.

**Not accessed / limits.** No code was executed; no tests or experiments were run. Not inspected: `web/client/` (left to the UI workstream), `objective_analysis/`, `literature/`, `evaluation_cascade/`, `flywheel/`, `analysis/report_iteration.py`, and `pipelines/run_candidate.py` beyond its header. Excerpts 01, 02, and 09–11 were read only as summarized in the package notes. The manuscript PDF, the other reference repositories (`deepseek-harness`, `ARIS`, `dgm`, `Agentic-Doping` on `main`), and the supplied datasets were out of scope here. No web searches were run. One early tool call was interrupted by a safety classifier before returning output; the affected file was subsequently read in full by another means. No empirical claim about multi-agent, multi-round, or debate effectiveness is made; those questions belong to the literature and evaluation workstreams.
