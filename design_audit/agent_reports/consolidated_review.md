# Consolidated Consistency Review: Design Set After Four Post-Handoff Revisions

Independent design reviewer, 13 October 2026. Design only. Nothing was run or installed, and no file other than this report was edited. `v1_scope.md` was not reviewed. Severity: **blocking** means an implementer would build the wrong thing, or two documents require incompatible behaviour. **Material** means an implementer would have to guess. **Minor** means stale wording.

**Verdict: not consistent.** Two blocking, twelve material (CR-16 partly minor), and four minor findings, all fixable by text edits without a new component. Most come from revisions applied to the design but not carried into the iteration spec, UI spec, task list, or ADR log; several come from interactions no single-revision review could see (streams × memory, encryption × in-run comparison, copies × access log). Three earlier fixes did not land everywhere: N1, CG-02, and CG-12.

---

## A. Run lifecycle: chains, sweep, and rounds

**CR-01 · blocking · Where and by whom a rerun runs.**
Files: `optimized_design.md` §6.6 ¶1, §6.8 (table rows 2 and 4; "Kind and scope"), §4.16; `iteration_and_provenance_spec.md` §6 ("Human edit" and "Evidence-refresh run" rows), §8.3, §11.2 row M+6, §11.3 row 1, §12 rule 6; `ui_ux_spec.md` §5.1 wireframe, §10 ("Request targeted follow-up" row).

Problem: the documents give four answers that cannot all be true.
- **Design.** An in-run decision lets "the run go on from its checkpoint". Any round beyond the round budget is a run continuation. A rerun after the run ends is a continuation that a person starts with Continue: `operator` role, interactive confirmation, and a per-stream `basis`.
- **Iteration spec §8.3.** "The rerun executes in a new round of the same run while that run has not ended". A P0 run has a round budget of 1, so this is impossible there, and it breaks §12 rule 6: a Rerun Plan is not a referent-backed `oq_`. The §6 row says "a new round only if the Rerun Plan says so", but the Rerun Plan record has no such field.
- **Iteration spec §11.2.** The controller creates `run_R1r` right after auto-approval, with `run.created` alone: no `run.continued`, `chain_id`, `continues_run_id`, `continuation_kind`, or person. §11.3 does the same for a refresh run, binding `refresh_delta` with no parent to diff against.
- **UI §5.1.** The rerun is still `round.opened R1_2` inside the completed `run_R1`. The N1 fix reached the iteration spec only.
- **UI §10.** A follow-up goes to a "new round or refresh run".

A further gap: §6.6 counts a stale cell as attempted. A run that receives an in-run unit correction can therefore end `completed` with stale cells.

Fix:
- §6.8 row 2: "Cells made stale by an in-run `hd_` are re-assessed in the current round before the sweep counts as complete; a stale cell is not attempted; this uses no round budget."
- §4.16: "Auto-approval approves the plan; once the run has ended, the plan executes only through `run continue --kind rerun` issued by a person."
- Rewrite iteration §8.3 and the §6 "Human edit" cell to match.
- In iteration §11.2 and §11.3, add a `run.continued {parent_run_id, continuation_kind}` row in the task stream with `actor.via`, and add `chain_id` and `continues_run_id` to the binding summary.
- In UI §5.1, replace the M+6 row with `run.continued → R1·2`.
- UI §10: "new round if round budget is left, otherwise a run continuation".

**CR-02 · blocking · ADR-33 not carried into the run monitor.**
Files: `ui_ux_spec.md` §4.2 (Budget meter row), §5.1 (row N+3); versus `optimized_design.md` §0.4, §6.3, §6.7, and `architecture_decisions.md` ADR-33.

Problem: UI §4.2 says that "reaching a cap renders the run `unresolved`, never done". `screening_rounds` is a budget field (§4.6), and using it up after a complete sweep is `round_limit_reached`, which ends the run `completed`: the normal end of P0. The §4.1 wireframe itself shows "rounds 1 of 1". A monitor built to UI §4.2 would label every finished P0 run unresolved, which also breaks parity rule 1 (§15.2). UI §5.1 still closes a P0 round with `no_actionable_step`, although the precedence rule in §6.3 requires `round_limit_reached`.

Fix: UI §4.2: "exhausting a budget other than screening rounds before the sweep is complete renders `unresolved` (`budget_exhausted`); a used round budget after a complete sweep is `round_limit_reached` (`completed`)". UI §5.1 N+3: `stop: round_limit_reached`.

**CR-03 · material · The state machines do not cover the new ways a run ends.**
Files: `optimized_design.md` §0.4 (execution states), §6.1, §6.7, §6.8, §14.1; `ui_ux_spec.md` §13 (execution row), §15.7.

Problem:
- Steps in §6.1 have no `paused` and no `cancelled`, while §0.4 says the execution states apply to steps. §6.1 has `rejected`, which is absent from §0.4 and from the UI §13 execution labels. The step-level state is therefore undefined when an operator cancels a run, or when a continuation closes a parent that is `waiting_human` or running (§6.8).
- The Stage row lists no `cancelled` among its terminal states.
- §6.1 says `waiting_human` is "left only on an `hd_` record". §6.7 (cancel) and §6.8 (closing a parent and withdrawing its items) both leave it without one.
- UI §15.7 re-queues "only steps that were running". §14.1 re-queues `running`, `retrying`, and `waiting_tool`.

Fix:
- Give steps the §0.4 set plus `rejected`, and add `rejected` to §0.4 and UI §13.
- State that when a run ends `cancelled` or is closed by continuation, its non-terminal steps and stages end `cancelled` with the run's termination reason.
- Change §6.1 to "left on an `hd_`, a cancel, or a continuation that closes the run".
- Copy the §14.1 list into UI §15.7.

**CR-04 · material · Withdrawn review items have no event.**
Files: `optimized_design.md` §4.1 (event kinds), §6.8 ("Closing a parent"), §12.3; `iteration_and_provenance_spec.md` §2.2, §10; `ui_ux_spec.md` §16.1.

Problem: the queue is a projection over the journal (§4.1), and ADR-37 introduced the `withdrawn` state. No event kind writes it: the `human.*` events cover requested, decided, claimed, and claim_released. The `human.review_claim_released` reasons (`released | reassigned | lease_expired`) have no value for "released because the run was continued". `expired` also has no event. UI §16.1 says the items "move to the new run", which suggests mutating them.

Fix: add `human.review_withdrawn {reason: continued, replaced_by_item}` and `human.review_expired` to §4.1 and iteration §2.2 and §10. Add `withdrawn` to the claim-release reasons. In UI §16.1, change "move" to "are withdrawn and raised again in the new run".

## B. Binding and preregistration

**CR-05 · material · The Run Binding lacks fields that other sections read from it.**
Files: `optimized_design.md` §2.3; §4.8 and §6.8 ("neither bound to a `proto_` arm nor registered as prespecified"); §13.2 ("a run without a `protocol_id`"); §4.20, §13.7, `evaluation_plan.md` §10.4 and `task.md` T7.6 (`promotion_policy_version` "declared in the Run Binding"); `iteration_and_provenance_spec.md` §1.1.

Problem: §2.3 has no protocol or arm-run reference, no prespecified or registration reference, and no `promotion_policy_version`. `policy_arm: P0` appears on ordinary runs too, so C8 cannot tell whether a `human_request` round is barred. The iteration §1.1 binding paragraph also omits `screening_rounds_budget` and `sweep_scope`. This is the partly landed CG-12 item.

Fix: add `protocol_ref?` (`proto_`, `evr_`), `preregistration_ref?` (the stage-1 event a run is registered under), and `promotion_policy_version` to §2.3. Copy the full §2.3 list into iteration §1.1, or replace that paragraph with a pointer.

**CR-06 · material · Who writes preregistration, when, and against what.**
Files: `optimized_design.md` §3 (Stage 0 and Stage 5 rows), §6.9 ("Preregistration does not carry over"), §8.5, §13.6; `ui_ux_spec.md` §15.3 (`eval prereg <case> --stage <1 or 2>`, `evaluator`); `iteration_and_provenance_spec.md` §11.1 (seq 2 and 57, actor `operator`); `case_study_protocol.md` §4.1 (D0, D7).

Problem:
- **Who.** The design has C15, C19, and C10 write both stages automatically inside the run. The UI makes each stage an evaluator command. The worked example attributes both to the operator. If stage 2 is a command, the run must wait for an evaluator between `rules@v1` and assessment, and no wait state or queue item exists for that.
- **What it is keyed to.** The command is keyed to a case. §6.9 says a task copy, which references the same `case_id@v`, does not inherit preregistration, so registration cannot be keyed to the case.
- **When.** Stage 1 is written at Stage 0 (bind) and registers the "evidence snapshot". `evs_` is frozen only after Stage 3 retrieval (§8.5, §9 step 1). Iteration §11.1 nevertheless cites `evs_T1_1` at seq 2.

Fix: pick one actor. Recommended: both stages are evaluator commands, keyed to task and run. Stage 2 is raised as a blocking C18 item of kind `preregistration` so the run sits in `waiting_human`. Stage 1 registers the cutoff and the snapshot rule; the `evs_` id is registered at stage 2. Then update §3, UI §15.3, iteration §11.1, and the protocol §4.1 to match.

**CR-07 · material · Stage-1 content is listed six different ways.**
Files: `optimized_design.md` §13.6, §17 (first stage row), §8.3 (consolidation rule "registered before derivation"); `case_study_protocol.md` §4.4, §6.1; `task.md` T8.3; `evaluation_plan.md` §8.4.

Problem:
- `budget_extension_rule` (ADR-37) appears only in design §13.6. Without it in the protocol or T8.3, the primary baseline can never take a prespecified extension.
- The sweep ordering policy and seed (ADR-33) are missing from §17 and T8.3.
- The derivation configuration is missing from §17.
- The consolidation rule, `strat@v`, and the registered constants are missing from §13.6, although §8.3 says they are fixed before derivation (protocol §4.4 has the constants only).

Fix: make §13.6 the single list. Add `strat@v` (which carries the consolidation rule), the constants hash, the derivation configuration, the sweep ordering policy and seed, and the optional `budget_extension_rule`. Have §17, protocol §4.4 and §6.1, and T8.3 cite it instead of re-listing.

## C. Streams, records, and firewall plumbing

**CR-08 · material · Some events belong to no stream, and copies split the access log.**
Files: `optimized_design.md` §2.4 ("Streams"), §6.9 ("Copying a task"), §8.6 ("Reads and file access"), §10.5, §13.2, §13.7; `ui_ux_spec.md` §15.3 (`memory add`, `eval protocol register`, `strategy promote|rollback`).

Problem: every event must belong to a run, task, or group stream, and the group stream is limited to lifecycle events. Four kinds of event have no stream:
- `memory.operation_recorded` for a person-written skill, or for one approved after its run ended (memory items are group-scoped, not task-scoped);
- `hd_` on `memory_item`;
- `proto_` registration;
- strategy promotion and rollback (`ops_`).

Without a stream these commands also have no valid `basis`. Separately, §6.9 says a copy keeps "one access log" because it references the same `case_id@v`. The access log, however, is the `evaluator_only.read` events in each *task* stream, and case-configuration versions also go to "the task journal". After a copy, both are split across tasks, and the exposure rule must union them.

Fix: let the group stream carry memory operations and memory-item decisions. Add a case stream (`case_`) for case versions, `evaluator_only.read`, and recovery comparisons. Add a store-level evaluation stream for `proto_`, `ops_`, and strategy events. List all of them in §2.4 and §4.1.

**CR-09 · material · An evaluator-held key versus work the run does without the evaluator.**
Files: `optimized_design.md` §14.1 ("Evaluator-only store"), §8.6 ("Reads and file access"), §3 Stage 8, §10.2 ("every item recallable in the case passes the criterion-content scan"); `iteration_and_provenance_spec.md` §11.1 row N+2.

Problem: each comparison or scan needs a key the evaluator supplies and the host does not keep, through a confirmed command. Stage 8 nevertheless runs the recovery comparison inside the run, before `round.closed`, as C19, and its only human touchpoint is the expert. A `warm` exploratory run of the primary case also cannot recall its own round-1 drafts unless someone scans them during the run. No wait state or queue item covers either case.

Fix: move the recovery comparison out of the run: an evaluator command after `lb_` publication writes `evaluation.recorded` to the case or task stream, and run completion does not depend on it. State that scans run when an item becomes recallable or an artifact is registered, as an evaluator command, and that an unscanned item is unrecallable in a case with an intake.

**CR-10 · material · Leaderboard identity is undefined.**
Files: `leaderboard_spec.md` §2.1 ("keyed by a `task_<ulid>@v<n>`"), §2.2, §11 (Longitudinal); `optimized_design.md` §0.3 (`lb_<task>_<n>`), §6.8 ("Leaderboard", "Branches"), §4.4; `iteration_and_provenance_spec.md` §1.1 (task row), §10 (`leaderboard.current_set`).

Problem:
- Every edit to constraints creates `task_@v<n+1>`, a soft-constraint edit included. If the leaderboard is keyed by version, every edit opens a new leaderboard, but §2.2 keeps non-breaking edits in the same one.
- A comparability break opens "a new leaderboard ... with a `supersedes` link", but no leaderboard record or id exists for that link to point at.
- `lb_<task>_<n>` does not say whether `<task>` includes the version, or whether `n` restarts across a new leaderboard or interleaves across branches.
- `leaderboard.current_set` targets "a task leaderboard" without naming it.
- The longitudinal view in §11 ignores branches.

Fix: add a leaderboard record `lbd_<task>_<k>` with a comparability key (the §2.2 fields), `supersedes`, and `current_snapshot`. Snapshot ids become `lb_<lbd>_<n>`, and `leaderboard.current_set` names the `lbd_`. Change leaderboard §2.1 to "keyed by the task and its comparability key", and describe branches in §11.

## D. Vocabularies and roles

**CR-11 · material · Label domains and vocabularies introduced by the revisions are not registered.**
Files: `optimized_design.md` §4.2, §0.4, §6.8, §13.3, §13.6, §16; `ui_ux_spec.md` §9.2, §13, §16.1; `evaluation_plan.md` §8.2.

Problem:
- **§4.2 label domains.** The list still lacks verdict, `not_assessed_reason`, `dependency_detail`, `sweep_scope`, `denominator_kind`, view freshness, `historical_list_exposure`, `recovery_view`, `field_visibility`, `continuation_kind`, memory kind and memory review state, `run_group_state`, and `trigger_class`. It also says `result` where UI §13 has `result_kind`. CG-12 flagged this and it is not fixed.
- **No domain or labels anywhere** for:
  - queue-item state (UI §9.2 renders `withdrawn`);
  - host start refusals (`store_locked`, `store_root_unsupported`; the launcher must "name the reason");
  - the register label `prespecified | exploratory` that §6.8 and §13.6 use and the chain view shows. Evaluation plan §8.2 uses `outcome_informed_exploratory`, which is a derivation configuration, for configurations instead.
- **Policy arms.** §0.4 omits `P0-noreview` and the two `P0+` variants that §13.3 and `run continue --policy-arm` need.
- **Exposure carriers.** §0.4's list of records carrying exposure omits memory items, `human_request` questions, and task-context versions (the CG-01 fix).
- **Absence reasons.** §16's `declared_unavailable` is not an absence reason.

Fix: make §4.2's domain list equal to UI §13's rows. Add rows for queue-item state, host start refusal, and `acceptance_label {prespecified, exploratory}`. Extend §0.4 with the arms and exposure carriers, and use `not_configured` in §16.

**CR-12 · material · Retiring a memory item: who decides?**
Files: `optimized_design.md` §2.4 role table ("authoring and retiring provisional skills and lessons": `operator`) versus §12.1 ("any approval or retirement of a memory item" needs an expert decision); `ui_ux_spec.md` §15.3 (`memory retire`: provisional by operator; approved items via the queue), §9.2 (decision control lacks `retire`).

Problem: the design contradicts itself on whether retiring a provisional item needs an `hd_`. The browser's decision control also cannot issue the `retire` decision that §12.2 defines.

Fix: §12.1: "any approval of a memory item, or retirement of an approved one". Add `retire` (for subject `memory_item`) to UI §9.2.

**CR-13 · minor · Command ownership and the role table are incomplete.**
Files: `optimized_design.md` §2.4 ("validated by ... C4, C8, C15, C16, C18, C19"); `module.md` §13 (header "Writes (through C18 or C15 only)"; the UI table has no chain, group, or skills screens), C12 and C15 "Emits"; `ui_ux_spec.md` §15.3.

Problem:
- Memory commands are owned by C14 and `board set-current` by C12, but neither component is in the validator list, and no module emits `leaderboard.current_set` or `group.*`.
- The role table omits several commands that §15.3 assigns roles to: set-current, `review reassign`, `claim assign`, `memory trial`, and issuing a browser address for another person.
- Comparison-adjudication items need both `expert` (for the `hd_`) and `evaluator` (for the read), and no document says so.

Fix: add C12 and C14 to the validator list. Name C12 as the writer of `leaderboard.current_set` and C15 as the writer of `group.*` in `module.md`. Extend the role table, and state the dual role.

## E. Fingerprints and budgets

**CR-14 · material · The CG-02 fix landed only in part.**
Files: `iteration_and_provenance_spec.md` §7.3 versus `optimized_design.md` §4.16.

Problem: the per-step `input_fingerprint` in iteration §7.3 omits `executed_on` and `recall_set_hash`; only the per-cell list has them. Steps that recalled provisional items, or ran on another platform, would match.

Fix: copy the design §4.16 step fingerprint into iteration §7.3.

**CR-15 · minor · `reflection_turns` is named but has no field.**
Files: `optimized_design.md` §4.6 (`budget_envelope`), §4.5 (loop classes), §6.2 (`loop_kind`); `evaluation_plan.md` §3 (`budget_caps`).

Fix: add `reflection_turns` to the envelope, the loop classes, `loop_kind` (`reflection`), and arm caps, so arms can be matched with and without reflection as §10.5 promises.

## F. Stale terminology and references

**CR-16 · material for ADR-36; minor for the rest · Pre-revision meanings of "continuation" and "per-run seq".**
Files: `architecture_decisions.md` ADR-36 ("continuation refused on a manifest mismatch"), ADR-20, ADR-01, ADR-03; `optimized_design.md` §4.15 ("continuation only through C8"), §0.2 C1, §4.17, §11.2; `iteration_and_provenance_spec.md` §9; `ui_ux_spec.md` §12; `module.md` C17; `task.md` T0.1, T6.1.

Problem:
- **ADR-36.** It refuses the very thing §14.2 prescribes as the remedy: "resume refused; continue in the chain".
- **"Continuation".** §4.15 and ADR-20 use the word without a qualifier.
- **Per-run journals.** C1, ADR-01, and T0.1 describe a "seq per run" or "per-run journal".
- **`subscribe(run_id, …)`.** Seven places still use it, against `subscribe(stream_id, …)` in §2.4.

Fix:
- ADR-36: "resume refused on a manifest mismatch; the work continues in a run continuation".
- §4.15: "round continuation only through C8".
- ADR-20: name resume, round continuation, and run continuation.
- Replace "per run" with "per stream", and `run_id` with `stream_id`, at each listed location.

**CR-17 · minor · Stale counts and ranges.**
Problem and fix, by location:
- `rebuttal_alignment.md` C2.5: "Five trigger classes only". Use "five adaptive classes; a person's `human_request` round is a sixth, non-adaptive class excluded from arm comparisons".
- `suggestions.md` line 3: "ADR-01 to ADR-28, U-01 to U-12". Use ADR-39 and U-16. Line 55 (E12): "five triggers". Use "five adaptive triggers".
- `audit_report.md` §7: "U-01 to U-12 ... None blocks". Use U-16, and note that U-15 awaits the user.
- `ui_ux_spec.md` §10: "`hd_` or operations record" for Rerun Plan approval. Use `hd_` only (the SR-08 fix).
- `optimized_design.md` §0.3: no `case_` prefix, though iteration §1.1 and T8.1 use `case_<id>@v<n>`. Add it.

**CR-18 · minor · Task list.**
Problem and fix, by task (`task.md`):
- T1.3 depends on "T2.x queue stub". The queue is T5.1.
- T1.6 depends on T8.1 (blocked on the authors), and T2.11 depends on T6.10. Both contradict the milestone table (M1 needs M0 only; M2 needs M0 and M1).
- No task builds the §8.4 `const_` registry, which holds the core-policy host constants and `const_reflection_item_cap`. Add T0.8.
- T8.2's acceptance limits readers to "the comparison function and queue". Add the evaluator panel, as in N2.
- T8.3: see CR-07.
- A blank line before the T8.13 row splits the M8 table, so T8.13 to T8.16 render outside it.

---

## Checked and consistent

- **Event kinds.** Every dotted event kind used in the fifteen files is in design §4.1, and iteration §2.2 matches §4.1. The only gaps are the missing kinds in CR-04.
- **Identifier prefixes.** Every prefix used is in §0.3, except `case_`.
- **Cross-references.** All 262 explicit cross-file section references resolve to existing headings. ADR-01 to ADR-39 and U-01 to U-16 all exist; ADR-28 sits after ADR-39 but exists. S1 to S14 are cited consistently in design §13.5, evaluation E1, T7.4, suggestions E18, and the rebuttal.
- **Shared field and value lists.** These are identical across their files:
  - `actor.via` (design §4.1, iteration §2.1);
  - the command outcomes (§0.4, §2.4, UI §13, §15);
  - the nine recovery mapping kinds (§0.4, §8.6, protocol §5.2, evaluation §8.1).
- **Continuations.** Continuation kind maps to `sweep_scope` the same way in design §6.6 and §6.8 and UI §13, §15.3, and §16.1.
- **Closing a parent.** A closed parent ends with `human_decision`, `completed` or `cancelled`, and `continued_by` in design §6.7 and §6.8 and S13.
- **Memory rules.** `memory_mode` governs recall only, and every mode drafts (§10.2, §10.5, evaluation §3, S14, UI §16.3). The exposure and recall bars for memory are the same in §10.2, ADR-39, and protocol §4.5.
- **Groups.** Archiving is refused while runs have not ended; moving a task means copying it; groups are never deleted (§6.9, ADR-38, UI §16.2, S14).
- **Host recovery.** Stop or suspend keeps `paused` and `waiting_human` and is charged to no budget in §14.1, §15, ADR-36, and S12. UI §15.7 differs as noted in CR-03.
- **Expert decisions.** An `hd_` requires the `expert` role and interactive entry, and disagreement uses `disputes_decision_id`, in §2.4, §12.2, UI §15.2 and §15.3, and S11.

## Contribution record

- **Files read in full:**
  - `optimized_design.md`
  - `architecture_decisions.md`
  - `iteration_and_provenance_spec.md`
  - `ui_ux_spec.md`
  - `leaderboard_spec.md`
  - `evaluation_plan.md`
  - `case_study_protocol.md`
  - `module.md`
  - `task.md`
  - `post_handoff_decisions.md`
  - `collaboration_log.md` §7.6–§7.7
  - `agent_reports/chains_groups_memory_review.md`
  - `agent_reports/surfaces_review.md`
- **Files read in part:**
  - `rebuttal_alignment.md` (§1, C2.5–C2.6, §3–§5)
  - `agent_reports/post_handoff_review.md` (findings and re-check)
- **Files scanned for revision terms:** `tools.md`, `resources.md`, `suggestions.md`, `audit_report.md`; `literature_review.md` not reviewed.
- **Searches run:**
  - extraction of every dotted event token, compared with §4.1;
  - extraction of every identifier prefix, compared with §0.3;
  - a script resolving 262 section cross-references against heading lists;
  - range checks for ADR, U, and S numbers;
  - targeted greps for `withdraw`, `mismatch`, "reaching a cap", `prereg`, consolidation rule, `budget_extension`, `proto_` arm, `protocol_id`, `promotion_policy_version`, `const_`, `subscribe(`, and task ids.
- **Approximate time:** 80 minutes.
