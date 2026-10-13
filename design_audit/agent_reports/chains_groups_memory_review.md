# Independent Review: Run Chains, Run Groups, and In-Run Skills and Lessons

Reviewer: independent design reviewer, 13 October 2026. Design-only review of the coordinator's revision for D7–D9. No file other than this report was edited.

**Verdict: not ready.** One blocking finding (a firewall gap the new channels open into acceptance-bearing runs) and nine material findings. Every fix is a text-level edit; none needs a new component.

---

## Findings

**CG-01 · blocking · design §10.2, §10.4, §10.5, §4.8, §6.8, §8.6; `case_study_protocol.md` §4.5.**
The new channels into agent context carry no historical-list exposure, and a frozen memory snapshot is never scanned. The path is: a Reflector draft or a person-written lesson, then expert approval, then an approved snapshot, then `frozen` memory in the baseline, then derivation recall. Under §8.6 the `independent` view still counts the derived item.
(a) The Reflector reads "expert corrections (`hd_` edits)". This can include `hd_` records from exposed experts, and `recovery_mapping` decisions (§8.6 does not list these as `evaluator_only` derived artifacts).
(b) §10.5 rejects drafts "derived from evaluator-only content". But `check_procedure` sees text only, so the rule cannot be enforced.
(c) §10.4 runs `historical_criterion_content` only on text "bound into a derivation strategy". It does not run on the `frozen` snapshot in the Run Binding, or on approved items inherited from other groups, such as calibration groups (protocol §2.4; UI §16.2).
(d) The recall bar in §10.2 covers only "derivation roles" and authors "with a logged read". The manuscript authors are exposed without any logged read, and the Retriever and Planner shape derivation context too.
(e) `human_request` question text and task-context edits in `edits_since_parent[]` are agent-visible but carry no exposure field.
(f) The forbidden lists are per case. A lesson drafted in a calibration-group run that names the primary manuscript therefore passes.
**Fix.**
- Every memory item carries `historical_list_exposure`, the author's declaration combined with the access log.
- A Reflector draft inherits the exposure of every `hd_` it read. The Reflector never reads `recovery_mapping` decisions, and those decisions are added to the §8.6 derived artifacts.
- Run the criterion-content scan on every memory item recallable in a case with an evaluator-only artifact. Add every registered `case_source_documents[]` identifier on the store root to the forbidden lists.
- Any memory snapshot bound to an acceptance-bearing run becomes a §8.6 global shaping artifact.
- Items whose author or approver is `exposed` or `undeclared` are not recallable by any role in acceptance-bearing runs; in other runs, every item they shape counts as `assisted`.
- Give `human_request` `oq_` records and task-context versions an `author_exposure` field that counts under "authored or confirmed".
- Add one row per channel to protocol §4.5.

**CG-02 · material · design §4.16, §6.8, §6.9; iteration spec §7.3.**
Fingerprints omit memory. A step or cell computed in a `warm` run with provisional items recalled matches one computed cold. A continuation that changes to `frozen`, or moves into another group, therefore reuses those records. This defeats "nothing provisional crosses groups".
**Fix.**
- Add `recall_set_hash` (the item ids in the step's `memory.recalled`) to the step and per-cell fingerprints.
- Add: "records produced with any provisional recall are never reused in a `cold` or `frozen` run, or in another group."

**CG-03 · material · design §4.8, §2.4, §0.4; ADR-04; UI §10, §15.3; evaluation plan §4.1.**
(a) The `human_request` referent is a `cmd_`. That is a host-infrastructure record in the operator log (§0.1), not in the journal (ADR-01), and it is not among the referent kinds §4.8 lists.
(b) Nothing bars human-requested rounds from runs under a `proto_` arm, or from prespecified configurations. "Not counted as adaptive" does not undo the round's effect on outcomes and realized budget, which feed P2-cap and P0+ matching.
(c) `run followup` ("Expert required: no") overlaps with `run add-round`, and its trigger class is unstated.
(d) `run add-round` has no flag for the subject the person names.
(e) ADR-04 and the evaluation plan still say "five" trigger classes. §0.4 says "added to the five of Section 4.8", but §4.8 already lists six.
**Fix.**
- The referent is the named C1–C20 subject, and it is required. The `cmd_` appears only in `actor.via`.
- `human_request` is `rejected_not_permitted_in_state` in any `proto_`-bound or registered run.
- `run followup` writes `human_request`, and both commands take `--subject <ref>`.
- Reword to "five adaptive classes; `human_request` is not adaptive".

**CG-04 · material · design §0.5, §6.6, §6.8, §4.15, §14.2, §15; iteration spec §6, §8.3.**
The boundary between same-run and new-run work contradicts itself.
(a) §6.8 row 2 allows rule edits in the same run, but row 5 makes a "rule set" edit a new run.
(b) §6.6 binds a post-completion rerun to `rerun_plan`, but §6.8 binds "the parent's `sweep_scope`". This choice decides Target B support, and S13's "rule edit" case is ambiguous because of it.
(c) Terminology:
- §0.5 "Continuation" means the same run, while "Run continuation" means a new run.
- Iteration spec §6 says a refresh run is not "a continuation", but `refresh` is now a continuation kind.
- Iteration spec §8.3 calls a same-run rerun a "continuation".
- §14.2 and §15 say "start a new run" where §6.8 now prescribes a run continuation.
(d) No precedence among the kinds is given.
**Fix.**
- Rename the §0.5 row to "Resume" and propagate the name.
- State that a `rules@v` confirmed inside a run is a run output and may be edited in-run; only the binding's starting `rules@v` is a bound field.
- Bind by kind: `continue` keeps the parent's scope, `rerun` uses `rerun_plan`, and `refresh` uses `refresh_delta`. Precedence: refresh, then rerun, then continue.

**CG-05 · material · design §6.8, §6.9; `leaderboard_spec.md` §2.2, §6.1.**
(a) A continuation that edits objective wording, hard constraints, or the universe "publishes the next snapshot of the task leaderboard". Leaderboard spec §2.2 instead closes that leaderboard, because the task contexts are not comparable.
(b) `lb_<task>_<n>` interleaves across branches, so change records against "the previous snapshot of the same task" can compare across branches. Nothing names the branch the task's leaderboard shows.
(c) Continuing into another group leaves `bind.group_id` ≠ `task.group_id`, so group listing and the task leaderboard disagree.
**Fix.**
- The dialog warns, and a new leaderboard opens, when comparability breaks.
- Add `parent_snapshot_id` to the snapshot record and compute change records against it.
- Add a journaled `board set-current` command.
- Define "continue into another group" as copy plus continue (`derived_from_task_id`, with the chain link kept).

**CG-06 · material · design §6.8, §12.3; UI §16.1.**
Closing a non-terminal parent leaves loose ends.
(a) Open `q_` items on a `waiting_human` parent are not handled, so an expert could confirm `rules@v1` on the closed parent while the continuation raises it again.
(b) Review claims are not released.
(c) A continuation can close the prespecified baseline `cancelled` mid-sweep, which silently destroys the baseline claim.
(d) For a `failed` parent, which records may be reused is not stated.
(e) The dialog never warns that a running parent will be closed.
**Fix.**
- Parent items become `withdrawn` (reason `continued`) and are re-raised with a link; later decisions on them are `rejected_not_permitted_in_state`. Claims are released.
- Closing a registered run before its sweep completes needs the `evaluator` role and interactive entry, and writes a protocol-deviation entry in the Case Acceptance Register.
- A `failed` parent's records are reusable only if committed before the fault's `cause_seq`.
- Add the dialog line "R1·2 is running and will end `cancelled`".

**CG-07 · material · design §6.8, §4.6, §17; U-13.**
No cumulative budget exists across a chain, so spend is unbounded and unreported. §17 marks continuations "with edits or extra rounds" as exploratory but says nothing about a budget-only continuation. U-13 expects the baseline may end `budget_exhausted`, and the design does not say whether it can then ever complete under its prespecified label. "Results visible" has no mechanical definition.
**Fix.**
- Report `chain_cost` in the chain view, the dialog, and every report citing a non-root run.
- Allow a stage-1 preregistered budget-extension rule. Only a continuation that matches it stays prespecified.
- Define: "outcome-informed = any continuation whose parent published a snapshot or recovery comparison, unless preregistered".

**CG-08 · material · design §2.4, §6.8.**
`basis` is a single `{stream, seq}`, but `edits_since_parent[]` spans the run stream and the task stream. An edit confirmed while another person's Continue dialog is open is silently left out of the continuation.
**Fix.**
- The continue command carries `basis[]` per stream read, plus the expected version of every listed edit. Any change gives `rejected_stale_basis`.
- A continuation without a branch label, issued after the issuer has seen the existing continuation, is `rejected_not_permitted_in_state`.

**CG-09 · material · UI §15.3, §16.1–16.3.**
The surfaces do not deliver "edit runs" for every bound field.
- The Continue dialog and `run continue` lack memory mode, policy arm, strategy, evidence cutoff, tool manifest, and continuation kind.
- What `--edits-from` may contain is undefined. If it can carry rule edits, an `operator` could create rule versions without an expert's interactive `hd_`.
- The chain view has no "edit" control, although the screen map promises one.
- The terminal has no "send for review" command.
- The browser has no reactivate control.
- There is no `chain list` command.
- The §15.4 terminal header omits the group, which §16.2 requires.
**Fix.**
- Add the flags and the dialog fields.
- Restrict `--edits-from` to task-context and binding fields. Rule edits exist only as `review decide` `hd_` records, which a continuation lists but never creates.
- Add `memory send-for-review`, `chain list`, an "edit…" control, a reactivate control, and the group in the terminal header.

**CG-10 · material · design §6.9, §2.4.**
(a) Archiving a group with running runs or open review items is unspecified, and "read-only" would block decisions those runs wait on.
(b) No component owns group records.
(c) `task.group_changed` sits in the group stream, although task-context versions belong to the task stream.
(d) `task copy` does not say what happens to the case configuration, the encrypted intake, preregistration, or the case-source list.
**Fix.**
- Archiving is refused while any run in the group is not terminal. Review decisions and continuing out of the group remain allowed.
- Name the owner.
- Write `task.group_changed` in the task stream, with link events in both groups' streams.
- A copy references the same `case_id@v` and never duplicates `evaluator_only` fields. Preregistration does not carry, so a copy's runs are `exploratory` until preregistered.

**CG-11 · minor · design §10.5, §12.1–12.2, §5.1, §4.6; evaluation plan §3; `module.md` C14.**
- The evaluation plan calls `frozen` "read-only" and `warm` "writes allowed", yet §10.5 has every mode draft items. State that `memory_mode` governs recall only.
- `hd_` subject kinds lack `memory_item`, decisions lack `retire`, and §12.1 has no memory-approval row.
- The Reflector's trigger differs between §5.1 (round or run end) and §10.5 (every `hd_`).
- C6 has no `reflection_turns` budget class for arm matching.
- C14 "gate recall by the promotion record" contradicts `warm` recall.
- A scripted `memory add` gets `support_basis: human_curation`; require interactive entry.

**CG-12 · minor · stale references.**
- Streams: design §2.4 "Both are C1 journals" and "run or a task stream"; §0.3 `evt_`; §4.1; iteration spec §2.1 and §12 rule 1; `module.md` C1. All omit group streams.
- Missing event kinds: iteration spec §2.2 and §10 lack `run.continued`, `run.annotated`, `group.*`, `task.group_changed`, and `memory.recalled`.
- Label domains: the design §4.2 list is incomplete.
- Scenario counts: `rebuttal_alignment.md` line 47 and `suggestions.md` line 61 say "S1–S10". The T7.4 description covers only the S1–S10 topics.
- `post_handoff_decisions.md` cites `collaboration_log.md` §7.7, which does not exist (the PH-14 precedent rated this material).
- Records and diagrams: the iteration spec §1.1 binding paragraph lacks the new fields; the Run Binding has no `branch_label`; event `ids` lack `chain_id`; the §3 flowchart has no chains.
- Wireframe: UI §16.1 labels a two-round continuation "single pass finished".

---

## Checked and found sound

- The Agentic Doping citations hold at 0007ad10: `recommend.py` 207–221, 645, 734–738; `groups.py` `delete_group` at 195 and global `set_active`; `cloud_deploy_doc/README.md` 72–77; `memory.py` 314, 352, 443–451.
- No ended run is re-entered (ADR-33).
- Branching needs confirmation.
- The active group is per session, and groups are never deleted.
- No reuse crosses policy arms.
- The Reflector excludes rationale and verdicts.
- Approval happens only through `hd_` or a trial, and strategy changes stay offline (ADR-16, ADR-17).
- Acceptance-bearing runs do not use their own drafts.
- Honesty holds: §10.5 "Expectation", U-16, post-handoff §5, and the "does not show" columns of S13 and S14; nothing claims the features exist or were tested.
- S1–S14 are updated in the design, E1, and T7.4; the UI label rows and §15 rejection rows are added.

## Contribution record

- **Files read:**
  - `optimized_design.md` (all);
  - `architecture_decisions.md` (ADR-01–04, 13–19, 30–39, U-13–16);
  - `ui_ux_spec.md` §1–2, §10, §12–16;
  - `iteration_and_provenance_spec.md` §1–3, §6–12;
  - `evaluation_plan.md` §2–6 and §12;
  - `module.md` (affected entries);
  - `task.md` (new rows);
  - `case_study_protocol.md` §2.4 and §4.5;
  - `post_handoff_decisions.md`;
  - `leaderboard_spec.md` §2 and §6.1;
  - `collaboration_log.md` headings;
  - the five cited Agentic Doping files.
- **Searches run:** scenario ranges, discussion and ADR counts, `human_request`, `subscribe(`, trigger counts, `hd_` subject kinds, group, chain, and warm terms across the deliverables, honesty terms, and AD recall functions.
- **Approximate time:** 40 minutes.
