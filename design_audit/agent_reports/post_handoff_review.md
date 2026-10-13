# Independent Review of the Post-Handoff Revisions (13 October 2026)

Independent reviewer, 13 October 2026. Scope: the two coordinator revisions summarized in `post_handoff_decisions.md` (ADR-30 to ADR-34, U-13) and their edits to `optimized_design.md`, `case_study_protocol.md`, `evaluation_plan.md`, `rebuttal_alignment.md`, `task.md`, `ui_ux_spec.md`, `literature_review.md`, and `audit_report.md`. Design phase only: this review reports no run, no ranking, and no recovery result, and recommends no implementation. Names follow `optimized_design.md` Section 0. This review edited no file other than itself.

## Findings

**PH-01 — Exposure is self-declared where the system holds contrary evidence, and the review queue is an authorized reader of the eleven**
Severity: **blocking**. Location: `optimized_design.md` §8.6 ("Blinding mechanics", "People and templates"); `case_study_protocol.md` §4.5 and §5.1; `architecture_decisions.md` ADR-31.
Issue: the intake record's enumerated readers are "the comparison function and the review queue". The review queue is exactly the surface on which experts confirm criteria (Stage 5, `hd_` records). So the system itself can show the eleven to a confirming expert, and nothing converts that logged access into a `historical_list_exposure` value: exposure is declared by the actor. The only automatic consequence of a logged read is §8.6's label "Any criterion version produced after a logged read by a **derivation actor** is labelled `outcome_informed_exploratory`" — confirming experts are not derivation actors, so a queue read by an expert leaves the `independent` view untouched. The `independent` view is the view that ADR-31, §17 and `rebuttal_alignment.md` C1.7 rest the "the system derived the criteria" statement on; as specified, that view can be populated by actors the access log shows to have read the list.
Evidence: §8.6 — "`visibility: evaluator_only`; readers enumerated: the comparison function and the review queue; every access logged"; and "Every template and every criterion-affecting `hd_` carries a `historical_list_exposure` declaration". §0.4 — "`undeclared` (treated as `exposed`)" covers silence, not a false `not_exposed`.
Recommended change: make exposure machine-derived wherever the log can prove it — any actor with a logged intake or `historical_stage_artifacts[]` read is `exposed` from that `seq` onward, and a conflicting `not_exposed` declaration is a consistency failure, not a value. Restrict review-queue access to the intake to comparison-adjudication items (`match_basis: expert_judged_equivalent`) and bar it from criterion-confirmation items.

**PH-02 — Exposure is declared for templates and `hd_` only; the objective text, the dimension list, the consolidation rule and the derivation strategy carry no declaration**
Severity: material. Location: `optimized_design.md` §0.4 (exposure vocabulary), §2.2 "Field visibility", §8.3; `case_study_protocol.md` §2.1, §2.2, §2.4, §4.5.
Issue: ADR-34 made every case field declare visibility, but visibility is not exposure. Four agent-visible or agent-shaping artifacts are authored by people who may know the eleven and carry no `historical_list_exposure`: (a) `objective_text`, which protocol §2.1 states is "a reconstruction ... assembled from dispersed phrases" (`reconstructed_pending_author_confirmation`); (b) the adapter's three CQA dimensions, which §2.2 of the design explicitly exempts — "The adapter's dimension list and criterion templates are adapter content visible to agents, not case fields" — while protocol §2.2 takes those dimensions from the manuscript, a case-source document; (c) the consolidation rule and `const_enumeration_saturation_k` / `const_merge_verdict_agreement`, registered "before derivation" by whoever registers them; (d) the derivation strategy promoted in E0b (prompts, enumeration procedure, retrieval rules). A derived item can therefore be steered by exposed humans through these channels and still count in the `independent` view.
Recommended change: extend the `historical_list_exposure` declaration to `objective_text`, the adapter dimension list, the consolidation rule and its constants, and the derivation strategy version; state the propagation rule (an item whose dimension, objective phrasing, or consolidation rule is exposed is `assisted`), or justify in §8.6 why these channels cannot carry criterion content.

**PH-03 — Memory and lineage metrics still carry primary-case information across runs**
Severity: material. Location: `optimized_design.md` §10.2, §4.20 (`metrics.lineage`), §13.7; `evaluation_plan.md` §6, §10.4, study table E2.
Issue: two feedback paths the revision did not close. (i) §10.2: "approved items inherit across groups", and no rule bars a memory item created in a run labelled `outcome_informed_exploratory` — or by an actor with a logged intake read — from later derivation; the E2 row of the study table registers no `memory_mode`, although the manifest field exists and policy comparisons are required to be `cold`/`frozen`. A warm primary-case lineage would carry criterion content between runs of the same case. (ii) C20's `metrics.lineage` is defined as "aggregated outcomes of derived versions **and refresh runs**", and `evaluation_plan.md` §10.4 says lineage metrics "may be weighed" once a descendant exists. Refresh and rerun runs of the primary case are production runs (§6 of the evaluation plan), so primary-case outcomes — the case whose reference outcome is disclosed — can enter strategy weighing, which contradicts ADR-32's "the primary case ... is never used for selection" and the sealed `final` pool.
Recommended change: register `memory_mode: cold` (or `frozen` over an approved snapshot predating any intake access) for E2 and for every acceptance-bearing primary-case run; bar items whose provenance run carries `outcome_informed_exploratory` from derivation recall; and exclude `final`-pool runs and their refresh runs from `metrics.lineage`, not just from promotion metrics.

**PH-04 — Calibration cases are not screened against the case-source list, and their curation is unconstrained**
Severity: material. Location: `optimized_design.md` §8.3 "Calibrated derivation strategy"; `architecture_decisions.md` ADR-32; `case_study_protocol.md` §2.3, §5.4 item 5; `evaluation_plan.md` §8.1, E0b.
Issue: calibration cases are "published prioritization studies on other objectives that report their criteria lists, curated by experts". Nothing requires those cases and their criteria lists to be screened against `case_source_documents[]` or against the intake items, and nothing requires the curating experts to declare exposure. A curated calibration case that cites or quotes the manuscript's criteria list, or a set of cases chosen (even unconsciously) to resemble the eleven, imports the answer into the frozen strategy, and the strategy then enters the primary run as `agent_visible` prompt and procedure text. The C14 chokepoint codes (§10.4) catch candidate identifiers, observed thresholds and outcome references, not imported criterion content.
Recommended change: require that every calibration case be checked against `case_source_documents[]` and against the intake (mechanically, inside the comparison component, so no agent sees the comparison), that curators declare `historical_list_exposure`, and that the frozen strategy text pass an added chokepoint code for criterion-content import.

**PH-05 — Refresh and rerun runs end `completed` without a full sweep, contradicting the new definition**
Severity: material. Location: `optimized_design.md` §6.6 ("Sweep complete"), §6.7, §3 Stage 11; `iteration_and_provenance_spec.md` §11.2 (seq M+40) and §11.3 (seq 17–18); `architecture_decisions.md` ADR-33.
Issue: ADR-33 and §6.7 make run completion depend on a complete sweep of the universe on every confirmed rule, and §6.6 opens "Stage 6 assesses the whole candidate universe". But the worked examples show a partial rerun closing with "stop_reason sufficient_support **for the rerun scope**" and an evidence-refresh run assessing one candidate and then emitting `run.completed`. Under the new definition those runs are not complete sweeps, so either they must end `unresolved` (absurd) or completion must be scoped. The same gap affects P2 rounds two and above: §6.3 speaks of "the round's candidate sweep", which, read with §6.6, implies a full re-sweep each round.
Recommended change: define `sweep_scope` on the Run Binding (`full_universe` | `rerun_plan` | `refresh_delta`) and restate §6.6/§6.7 as "complete with respect to the bound sweep scope"; state that only a `full_universe` run supports the Target B coverage claim and the `evaluation_plan.md` §8.4 row "row count equals universe size".

**PH-06 — `sweep_order` and the randomization seed are assigned to a preregistration stage that cannot hold them**
Severity: material. Location: `optimized_design.md` §6.6 item 2, §13.6; `case_study_protocol.md` §4.4; `task.md` T4.4.
Issue: §6.6 says confirmed rules are applied "in a `sweep_order` registered at stage-1 preregistration", but stage 1 happens before derivation, and both §13.6 and protocol §4.4 state the reason — "criteria are an output: the policy can be fixed in advance, the criterion identities cannot". Neither stage-1 content list mentions `sweep_order` or the registered seed, so the one place they are named is the only place that cannot contain them.
Recommended change: register at stage 1 an *ordering policy* over rule classes (deterministic computation, curated lookup, literature retrieval) plus the seed, and register the concrete `sweep_order` at stage 2 with the rule-set version; add both to the §13.6 and protocol §4.4 lists and to the §8.4 checklist row on prespecification.

**PH-07 — Per-rule budget reservation is computed at a point where its inputs do not exist**
Severity: material. Location: `optimized_design.md` §6.6 item 4; §3 Stage 2 and Stage 6; `iteration_and_provenance_spec.md` §11.1 (seq 58–60).
Issue: "At plan time C6 reserves each rule's budget as a per-candidate cap times the number of resolved candidates." Planning is Stage 2; identity resolution is the first step of Stage 6, and the worked example shows the denominator moving from 3,171 to 2,980 after it. The reservation basis, and therefore the plan-time feasibility verdict, is unavailable when §6.6 requires it.
Recommended change: make the plan-time check an estimate against the universe size, with a mandatory re-reservation and a second feasibility verdict after identity resolution, emitted as `progress.estimate_revised`; keep the per-candidate cap identical across candidates so the §6.4 symmetry obligation still holds.

**PH-08 — Mid-rule budget exhaustion produces cell states the roll-up does not define**
Severity: material. Location: `optimized_design.md` §6.6 (final paragraph), §4.10 four-state table, §4.11 roll-up; `leaderboard_spec.md` §§ on coverage.
Issue: §6.6 creates per-cell `not_assessed` with reason `budget_exhausted` inside otherwise assessed candidates. The C10 four-state evaluation table covers `supported_pass`, `supported_fail`, `missing`, `inapplicable`, `conflicted`, `qualitative_only`; the C11 roll-up covers hard-rule `fail`, `unknown_*`, `inapplicable` and whole-row `not_assessed`. No rule says what a per-cell `not_assessed` does to `hard_rule_coverage` (numerator, denominator, or neither) or to the candidate state. The reasons for `not_assessed` are also an unregistered vocabulary, and the run-level "`not_attempted` manifest" reuses a name already registered in §0.4 as a tool-result outcome.
Recommended change: add a `not_assessed` row to the four-state table (excluded from the numerator, retained in the denominator, caps the candidate at `provisional`), register the `not_assessed` reason vocabulary in C2, and rename the run-level manifest (for example `unswept_cells_manifest`) to avoid the collision.

**PH-09 — Checkpoint-per-rule-pass is not supported by the checkpoint and reuse contracts**
Severity: material. Location: `optimized_design.md` §6.6 item 6, §6.5, §4.16; `iteration_and_provenance_spec.md` §8 (checkpoint record and resume rules).
Issue: §6.6 adds "A `ckpt_` is written after each rule completes across the universe, so a resume restarts at the next rule", but §6.5 and the iteration spec define checkpoints as written "at every stage boundary and before any `waiting_human`", restoring *step* states with "a step is `completed` only if an evaluated artifact exists". Nothing records within-rule progress, the seed, or the completed-cell set, so a resume cannot know where a rule pass stopped. Worse, C16 lists "per-candidate decisions" under *always re-evaluated*, which forbids exactly the reuse that "restart at the next rule" depends on (and which the worked example already exercises as `reused_valid`).
Recommended change: define the sweep's unit of work (one step per rule pass, or a cell cursor) in §0.5 and the checkpoint record; add `sweep_cursor {rule_ref, seed, completed_candidate_count}` to `ckpt_`; and correct C16 so assessment reuse under an unchanged fingerprint is explicitly legal, with "always re-evaluated" narrowed to adjudications, snapshots and model-authored rationale.

**PH-10 — `round_limit_reached` has no precedence rule, and the worked example and two arms were not updated**
Severity: minor. Location: `optimized_design.md` §6.3, §6.7; `evaluation_plan.md` §4.1 (P1, P2 rows); `iteration_and_provenance_spec.md` §11.1 (seq N+3).
Issue: for a P0 run with no open questions, both `sufficient_support` and `round_limit_reached` apply, and no precedence is stated, although `post_handoff_decisions.md` and `evaluation_plan.md` §4.1 call `round_limit_reached` the normal P0 end. The primary-case worked example still closes with `no_actionable_step`, and the P1 and P2 rows list stop reasons without `round_limit_reached` even though both can exhaust `screening_rounds_budget`.
Recommended change: state the precedence (round budget consumed ⇒ `round_limit_reached`, else `sufficient_support`), update the §11.1 example, and add `round_limit_reached` to the P1 and P2 stopping cells.

**PH-11 — `coverage_fraction` became ambiguous under "attempted cell"**
Severity: minor. Location: `leaderboard_spec.md` reporting tuple; `optimized_design.md` §4.12, §6.6 item 5.
Issue: the tuple defines `coverage_fraction` as "candidates with a complete per-criterion assessment ÷ candidate universe". §6.6 now defines an *attempted* cell to include `unknown_missing` with an absence check or a tool error. Read together, every `completed` run reports `coverage_fraction` near 1.0 while most cells hold no value — the opposite of the metric's purpose (precision never rendered without coverage).
Recommended change: keep two distinct fields — `sweep_completeness` (attempted ÷ required cells) and `coverage_fraction` (value-bearing applicable hard-rule cells), and say which one §8.4's "did the run cover every compound" row checks.

**PH-12 — New vocabularies are absent from the label registry and the UI**
Severity: minor. Location: `ui_ux_spec.md` label table (only the `termination_reason` row was updated); `optimized_design.md` §0.4.
Issue: `ui_ux_spec.md` requires every registered label to carry a `ui_label`, yet `historical_list_exposure`, `recovery_view`, the `case_source_document` omitted reason and the `not_assessed` reasons have no rows, and no screen renders the `independent`/`assisted` split that acceptance now depends on.
Recommended change: add label rows for the new vocabularies and one recovery-comparison screen element showing both views side by side with their denominators.

**PH-13 — `module.md` and `task.md` lag the two ADRs; `derivation_unavailable` is used as if registered**
Severity: minor. Location: `module.md` §12 (Case Configuration module), C11 and C15 entries; `task.md` T2.1; `optimized_design.md` §0.4, §4.4.
Issue: the module map's case-configuration contract still lists the §2.2 fields without `case_source_documents[]`, `calibration_pool_ref` or any visibility declaration, and the C11/C15 entries carry no sweep obligation (breadth-first, no short-circuit, per-rule reservation, per-rule checkpoint), so the implementation map understates ADR-33 and ADR-34. Separately, §4.4 calls `derivation_unavailable` a *detail* of `dependency_unresolved`, while `module.md` and `task.md` T2.1 write `unresolved {derivation_unavailable}` as though it were the registered reason; §0.4 registers no such value.
Recommended change: refresh the three `module.md` entries and register `derivation_unavailable` either as a C2 `dependency_detail` vocabulary value or consistently as prose.

**PH-14 — `post_handoff_decisions.md` cites a change-log section that does not exist and a review as recorded**
Severity: material. Location: `post_handoff_decisions.md` header and §6; `collaboration_log.md` §7.4 (the file ends with §8).
Issue: the document states "The change log entries are `collaboration_log.md` §7.4 and §7.5" and "The independent review of the combined revision **is recorded** in `collaboration_log.md` §7.5 and `agent_reports/post_handoff_review.md`". There is no §7.5, and at the time of writing neither the review nor its log entry existed; §7.4 covers only the first revision (ADR-30 to ADR-32), says explicitly "no independent review of it has been run", and mentions none of ADR-33, ADR-34, U-13, §6.3, §6.6, §6.7, the §2.2 visibility paragraph, or the `task.md`, `ui_ux_spec.md`, `evaluation_plan.md` §4.1/§8.4 and protocol §2.4/§3.1 edits. The claim "The consistency checker was rerun after each revision" is likewise unlogged for the second revision.
Recommended change: add a §7.5 covering the second revision and this review, and restate §6 in the future tense until the log entry exists. Separately, the claim in D4 that the *previous* §6.3 text contradicted §16 cannot be verified from the working tree (the package is uncommitted, so no prior version exists to compare); either keep the superseded wording in the ADR's "alternatives" cell, which ADR-33 partly does, or drop the characterization.

## Verdict

**Not ready** — one blocking finding (PH-01) and seven material ones, all fixable by text edits of a page or less; the revisions are a net improvement and no finding requires rethinking the architecture.

## Verified as correct

- **No-code and honesty rules hold.** The only fenced blocks added are `mermaid` diagrams (`post_handoff_decisions.md` §3, matching existing use in `optimized_design.md` and `module.md`); no block is tagged with an executable language, and `ui_ux_spec.md`'s eighteen fences remain untagged wireframes. No revised passage reports a run, a ranking, a recovery count or an admission; `post_handoff_decisions.md` §1 states the goal as a target, §5 lists four things the design cannot guarantee, and `evaluation_plan.md` §8.1 and protocol §1 keep the threshold for "most" a registered placeholder with no number. The Case Acceptance Register still registers no expected state for the reference candidate (design §13.6, protocol §6.1).
- **Claimed locations exist.** Every row of `post_handoff_decisions.md` §2 was checked: ADR-30 to ADR-34 and U-13 in `architecture_decisions.md`; design §0.4 (exposure, recovery view, `round_limit_reached`), §2.2 (`case_source_documents[]`, `calibration_pool_ref`, "Field visibility"), §3 Stage 6, §4.4, §4.9 (`case_source_document` omitted reason), §4.11 failure behaviour, §6.3, §6.6, §6.7, §8.3, §8.6, §17; protocol §1, §2.1 constants row, §2.3, §2.4, §3.1, §4.5, §5.4, §6.5; evaluation plan §4.1 P0 row, §8.1, §8.4 (ten rows, as claimed), E0b; `rebuttal_alignment.md` C1.7; `task.md` T2.6, T2.9, T4.4, T8.4, T8.6, T8.13 to T8.15; `ui_ux_spec.md` `termination_reason` row; `literature_review.md` stopping-criteria paragraph; `audit_report.md` top link.
- **No surviving old completion semantics.** Greps for "Only `sufficient_support`", "decision-relevant set", and run-level `unresolved` caused by missing values return nothing; the three remaining "decision-relevant" hits are about attribute enumeration and a progress-kind definition. §4.11, §6.3, §6.7 and §16 now agree that missing values cap candidates at `provisional` while the run reaches `completed`, and §16's CDES-absent paragraph is consistent with that.
- **Sweep design is coherent where it is specified.** Breadth-first by rule with no short-circuit is correctly justified by what the outcome-dependence report and sensitivity arms need; the randomized within-rule order is a sound mitigation for truncation bias and does not conflict with the §6.4 symmetry obligation, since the per-candidate cap is identical by construction; "no candidate is dropped" is consistent with C11's roll-up and C12's four-state rendering.
- **The leakage controls added are real mechanisms, not assertions.** `omitted_reason: case_source_document` on the visibility manifest is a per-decision mechanical record, `undeclared` exposure defaults to `exposed`, the `independent`/`assisted` split is carried on each comparison record and named in acceptance claims, and ADR-30's residual risk (a quotation in an unrelated document) is disclosed rather than hidden.

## Contribution record

Files read (in full or in part): `post_handoff_decisions.md`; `architecture_decisions.md`; `optimized_design.md` §§0–10, 13, 15–18; `case_study_protocol.md` §§1–6.5; `evaluation_plan.md` §§4–6, 8, 10, 12; `collaboration_log.md` §7.4, §8; `iteration_and_provenance_spec.md` §8, §11.1–11.3; `leaderboard_spec.md`; `module.md`; `ui_ux_spec.md`; `rebuttal_alignment.md` C1.7; `task.md` (nine rows); `literature_review.md`; `audit_report.md` header.

Commands: listings and word counts; `awk` extraction of §7.4; heading inventories; ADR id ordering check; greps for `decision-relevant`, "Only `sufficient_support`", `derivation_unavailable`, `round_limit_reached`, `run.completed`/`run.unresolved`/"ends `completed`", `not_attempted`, `coverage_fraction`, `hard_rule_coverage`, `checkpoint`, `memory_mode`, `lineage`, `sweep_order`, `historical_list_exposure`, `recovery_view`, `agent_visible`/`control_only`, `case_source_document`, the three new `const_` names, `assisted`, and a fenced-block census. No git command was run; no file but this report was touched.

Approximate time: 30 minutes.

## Re-check of fixes (13 October 2026)

Scope: the fixes listed in `post_handoff_decisions.md` §6 and `collaboration_log.md` §7.5. The findings above are left unchanged so they can still be traced.

### Status per finding

| Finding | Status | Reason | Evidence |
|---|---|---|---|
| PH-01 | resolved | Queue reads limited to post-confirmation adjudication; exposure derived from the access log; conflicting `not_exposed` is a consistency failure | design §0.4, §8.6; protocol §4.5, §5.1; ADR-13; UI §11.1 |
| PH-02 | partially resolved | Scan-or-verbatim rule added, but canonical §0.4 still defines `independent` only by who "authored or confirmed any field"; the scan-`match` rule lives only in §8.6, and "shaped" is undefined | design §0.4 vs §8.6 |
| PH-03 | resolved | Cold or frozen memory for acceptance-bearing runs; no recall of `outcome_informed_exploratory` items; `final` pool excluded from lineage | design §10.2, §4.20; evaluation plan §10.4, E2 |
| PH-04 | resolved | Inclusion rule, screening, curator exposure, strategy scan | design §8.3, §10.4; ADR-32; T8.16 |
| PH-05 | partially resolved | `sweep_scope` is added and the examples are relabelled, but the fix introduces the contradiction described in N1 | design §2.3, §6.6; iteration spec §11.2 |
| PH-06 | resolved | Ordering policy and seed are registered at stage 1; the concrete order at stage 2 | design §6.6 item 2, §13.6; protocol §4.4 |
| PH-07 | resolved | Two feasibility verdicts, the second after identity resolution | design §6.6 item 4; T4.4 |
| PH-08 | resolved | `not_assessed` row, registered reasons, roll-up cap, `unswept_cells_manifest`; one stale name (N4) | design §0.4, §4.10, §4.11, §6.6 |
| PH-09 | resolved | Rule-pass unit, `sweep_cursor`, per-cell reuse; C16 corrected | design §0.5, §4.16, §6.5; iteration spec §7.1, §7.3 |
| PH-10 | resolved | Precedence stated; examples and P1/P2 rows updated | design §6.3; evaluation plan §4.1; iteration spec §11.1 |
| PH-11 | partially resolved | `coverage_fraction` now counts only value-bearing cells and `sweep_completeness` is added. However, `leaderboard_spec.md` still defines "`hard_rule_coverage = assessed applicable hard rules ÷ applicable hard rules`", which contradicts design §4.11 ("value-bearing verdict, `pass` or `fail`") | leaderboard spec coverage paragraph |
| PH-12 | resolved | Label rows and two-view panel added; labels for vocabularies the fixes introduced are missing (N4) | UI §11.1, §13 |
| PH-13 | resolved | Entries refreshed; `dependency_detail` registered | design §0.4; `module.md` C4, C11, C15, Case Configuration; T2.1 |
| PH-14 | resolved | §7.5 exists and quotes the superseded §6.3 wording; two forward claims recur (N4) | `collaboration_log.md` §7.5 |

### New problems introduced or still open

**N1 (material): `sweep_scope` is bound per run but used per round, and the rerun example re-enters a terminal run.** §2.3 places `sweep_scope` on the immutable Run Binding, while §6.6 assigns `rerun_plan` to "a rerun round" and `refresh_delta` to "a continuation round". Iteration spec §11.2 opens `round_R1_2` inside `run_R1` after `run.completed` at N+4. That example contradicts itself in three ways: it re-enters a terminal state, it runs a second round in a P0 run whose round budget is 1, and it closes with `sufficient_support` even though the new precedence rule requires `round_limit_reached` once the round budget is used. Fix: make a post-completion rerun a new run bound with `sweep_scope: rerun_plan`, as refresh runs already are, or move the scope onto the round record.

**N2 (material, leakage still open): artifacts derived from the intake carry no visibility rule.** Recovery comparison records, the R4 summary, `evaluation.recorded` payloads and the new UI §11.1 panel all hold content from the original list, but none inherits `evaluator_only`. The panel is a third reader alongside the "exactly two enumerated readers" (protocol §5.1; T1.8). A later refresh or rerun run on the same case, where agents can propose criterion changes, has no rule keeping these artifacts out of its derivation catalog. Fix: state that every artifact derived from the intake inherits `evaluator_only` and is excluded under `evaluator_only_artifact`, and list the panel as a reader.

**N3 (material, leakage still open; I missed this in the original review): the replay gate can let the primary case influence selection.** Promotion condition (6), "a replay/retention view on earlier cases shows no regression" (design §13.7; evaluation plan §10.1), does not exclude the `final` pool. The primary case could therefore veto a promotion, which contradicts the new lineage rule "so the primary case never feeds selection". Fix: exclude `final`-pool cases from the replay view.

**N4 (minor): stale or broken references.**
- Unrestricted review-queue reads of `evaluator_only` fields are still stated in design §2.2 "Field visibility", protocol §2.4 and `ui_ux_spec.md` line 54. The §8.6 restriction covers the intake only, so the 140-binder stage is still readable on confirmation items.
- T4.4 still says "random `not_attempted` …".
- Protocol §4.5 cites "memory mode in the Run Binding", but §2.3 has no such field, and cites §13.7 for the lineage exclusion, which is actually in §4.20.
- §6.6 uses the value "`reused`", which is not registered.
- `dependency_detail` and `sweep_scope` have no UI label rows.
- `post_handoff_decisions.md` §6 says this re-check is "noted in `collaboration_log.md` §7.5" and that the checker was rerun after the fixes; §7.5 records neither yet.

**N5 (minor): the per-cell reuse fingerprint is too narrow.** It covers candidate identity, `rule_ref@v`, `evidence_snapshot_id` and tool contract versions. It omits `strat@v` and the assessor's model version, both of which the step-level fingerprint includes, so a cell could be reused across strategy versions or across policy arms on the same `evs_`. Fix: add both, or forbid cross-arm reuse.

**N6 (minor): new pre-derivation count.** The first feasibility verdict uses a "registered expected rule count per dimension", a number fixed before derivation. ADR-32 says the count is an output. This count has no stated visibility and no exposure declaration. Fix: declare it `control_only` and state where it comes from.

**N7 (minor): a single false declaration can block the whole summary.** "Blocks publication of the recovery summary" lets one false declaration withhold both views, which conflicts with "both views are always reported". Fix: let the log win (the item moves to `assisted`) and report the conflict.

**N8 (minor): task dependency and arm wording.** T8.4 does not depend on T8.16, although the scan must run before stage-1 preregistration. The P0+ retrieval-rich arm still spends budget on "more candidates per pass", which contradicts §6.6's "never samples within its scope" (also missed in my original review).

### Updated verdict

**Ready with fixes.** The blocking finding is resolved, and ten of fourteen findings are fully resolved. Three material items remain (N1, N2, N3), and each needs a sentence or a table row. Until N2 and N3 are fixed, an acceptance claim resting on the `independent` view should not be described as fully firewalled across later runs.

### Contribution record (re-check)

- Read: every section cited in `post_handoff_decisions.md` §6 and `collaboration_log.md` §7.5, plus design §2.2 and §13.7, and T8.4.
- Greps: `sweep_scope`, `not_attempted`, `hard_rule_coverage`, `lineage`, `memory_mode`, `replay/retention`, reader enumeration, new labels.
- No git commands were run, and no other file was touched.
- Time: about 15 minutes. The original record's "30 minutes" was a rough self-estimate; `collaboration_log.md` §7.5 gives a measured figure of about 11 minutes.
