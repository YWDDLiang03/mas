# Collaboration Log

Coordinating agent, 12 October 2026 (all times UTC). This is the record of actual multi-agent work: who was assigned what, which files each agent wrote, what each agent read, where agents disagreed, and how disagreements were resolved. Harness-internal agent identifiers exist in the session transcript; per harness policy they are not reproduced here, so agents are named by their coordinator-assigned workstream ids. Every agent's own `## Contribution record` (files read, repositories and commits inspected, web queries with dates, URLs with reading depth, start and end times, access gaps) is at the end of its report under `agent_reports/`.

## 1. Setup (coordinator, 12:30–13:08)

- Read all 36 package files directly, including the eleven Agentic Doping excerpts and both manifests; extracted the manuscript's screening passage (five targets, 3,171-compound library, 140 binders, eleven CQAs in three dimensions, surufatinib as the sole all-pass) and confirmed the eleven CQAs are not enumerated in the main text.
- Resolved the user's decisions: the five Windows-path local repositories are not on this host; Agentic Doping is inspected from GitHub (`YWDDLiang/Agentic-Doping`); TASTE, iDeer, self_improving_ai, and auto_research_project_vGPT are treated as outdated and replaced by newer open-source references; installs authorized; deliverables left uncommitted.
- Environment: conda env `mas-audit` (conda-forge only after a Terms-of-Service block on the default channels; python 3.11, pypdf, pdfplumber, requests, pyyaml, jsonschema, pandas, tabulate, gh 2.102.0); `pdftotext` for PDF text extracts placed in the session scratchpad for subagents.
- Clones (read-only, outside the repository at `~/anny/reference_repos/`): `Agentic-Doping` main `7cdf6591` (2026-07-09); worktree `Agentic-Doping-snapshot` at `0007ad10` (tip of `origin/cloud_deployment`, 2026-08-12, 53 commits ahead of main); `deepseek-harness` `d7432673` (shallow, MIT); `ARIS` = `wanshuiyin/Auto-claude-code-research-in-sleep` `26b95cfa` (shallow, MIT); `dgm` `a565fd2d` (Apache-2.0). Later (Wave 1.5): `hsi` `97a022b9` (README says MIT; no license file), `ace` `82709de0` (Apache-2.0), `HGM` `013872d9` (Apache-2.0).
- Hash verification against the snapshot: 11/11 excerpt source files and 11/11 excerpt line ranges match `SOURCE_MANIFEST.json`; 7/8 progress files match `PROGRESS_SOURCE_MANIFEST.json`; `web/server.py` differs because the package hashed a working tree with uncommitted edits (the manifest warned of this).
- Wrote `agent_reports/00_coordinator_brief.md` (acceptance target, three layers, shared vocabulary, preliminary thirteen-component spine, report template, contribution-record requirement) before launching any subagent.

## 2. Wave 1: eight workstream agents (launched 13:08)

All were general-purpose subagents launched in one message with bounded scopes, a single output file each, the no-code rule, and the instruction to critique and propose rather than summarize. The soft length bound of 2,000–5,000 words was exceeded by all; the coordinator accepted the reports as complete.

| Id | Workstream | Report | Start → end | Words (final, incl. cross-review) | Notes |
|---|---|---|---|---|---|
| WS1 | Evidence and decision-policy auditor | `evidence_and_policy.md` | 13:04:53 → 13:31 | ≈8,100 | inspected `literature/`, `objective_analysis/`, `evidence_ledger/`, `schemas/` at `0007ad10` |
| WS2 | MAS architecture and reuse auditor | `mas_architecture.md` | 13:05:19 → 13:30 | ≈7,700 | inspected `dual_agent/`, `harness/`, `orchestration/`, `core/`, docs |
| WS3 | Tools and data auditor | `tools_and_data.md` | 13:06:12 → 13:52 | ≈7,500 | five web searches, 25 URLs; first attempt halted by a safety classifier before any write; restarted from scratch |
| WS4 | Human-review and UI auditor | `human_review_and_ui.md` | 13:06:17 → 13:38 | ≈6,600 | inspected `web/`, `run_dir.py`, `recommend.py`; 115 routes scanned |
| WS5 | Evaluation and self-improvement auditor | `evaluation_and_improvement.md` | 13:06:30 → 13:30 | ≈7,300 | inspected `reflection.py`, `skill_policy.py`, `memory.py`, `flywheel/`, test names |
| WS6a | Literature A: agents, orchestration, memory, tools, evaluation, agentic science | `current_agent_literature_a.md` | 13:07:30 → 13:21:51 | ≈9,100 | 33 sources, 17 full text, 17 dated queries |
| WS6b | Literature B: RSI, self-evolving agents, negative evidence | `current_agent_literature_b.md` | 13:08:06 → 17:20:32 | ≈10,400 | 35 sources, 18 full text plus DGM appendices from PDF, 25 dated queries; named the Wave 1.5 repositories |
| WS7 | Reference-harness inspector | `reference_harness_inspection.md` | 13:07 → 13:24 (+ Wave 1.5 17:14–17:26) | ≈9,400 | AD snapshot, deepseek-harness, ARIS, DGM; later hsi, ACE, HGM |

**Interruptions.** At about 13:27 the session's usage limit terminated WS1, WS2, WS3, WS4, WS5, WS6b, and WS7 while they were trimming already-complete drafts toward the soft bound; all report files were already on disk with contribution records. The coordinator accepted the reports and did not re-run them. A second limit interruption at about 17:40 caught WS7 after it had written its Wave 1.5 sections; on resume it verified the file and corrected only an end time. WS6b's contribution record initially carried an unstamped end time, fixed during its cross-review. WS6b's scratch notes went to a mistyped scratchpad path given in its prompt; its deliverable was unaffected.

## 3. Wave 1.5: literature-selected repositories (coordinator clone 17:12; WS7 inspection 17:14–17:26)

WS6b recommended `TailinZhou/hsi` and `ace-agent/ace`, with `metauto-ai/HGM` as an alternate; the coordinator cloned all three and continued WS7 by message. WS7 appended §8.1–8.5 (seventeen mechanism rows; findings F11–F14) and reported the hsi license status exactly as found.

## 4. Wave 2: cross-review (launched ≈17:12 by resuming the same agents)

Each reviewer read one peer report in full and appended a `## Cross-review of <peer>` section to its own report (agreements, objections with evidence, interface conflicts with one resolution each, dependencies, a resolution table), without editing the peer's file. Peer files changed during some reads because peers were appending their own cross-reviews concurrently; each reviewer recorded which version it read.

| Reviewer → peer | Done | Principal objections | Coordinator ruling |
|---|---|---|---|
| WS1 → WS5 | 17:17 | evaluator-only historical list must not live in the registry the deriving agents read; an access log alone does not prove exclusion; the acceptance register must not pre-write surufatinib's expected state; recovery categories too coarse; de-duplication by source identity double-counts preprint/published pairs | all adopted: artifact in the case configuration with two enumerated readers; mechanical visibility-manifest entry per derivation decision; no expected state; nine stored mapping kinds with six-category roll-up; de-duplication by independence group |
| WS5 → WS1 | 17:23 | `reference_blind` as the sole acceptance configuration makes acceptance impossible; identical reason text is often legitimate; the coverage floor is a precision lever | all adopted: derivation `reference_disclosed` with alias scan and leave-one-out report, `reference_blind` as a sensitivity arm; disqualify identical refs+value under differing verdicts with `reason_template_id`; floor registered inside the admission-predicate hash; fourth approval field `operations_decision` |
| WS2 → WS3 and WS7 | 17:22 | WS2 conceded WS7's F6 (reviewer sees proposer rationale on the default tool-harness path; WS2 had cited the file-chat fallback); proposed merged tool-result vocabulary; two registries; retry split; `revision_check` sees structured changes not rationale; never-delete scoped to strategy versions | adopted: `outcome` {ok, partial, empty, not_attempted, failed, unknown_outcome} + `record_state`; two registries with one `verified_by` discipline; retry policy in broker, allowance in plan step; artifacts carry `journal_seq`, events carry transitions |
| WS3 → WS2 | 17:23 | WS2's tool payload lacked provenance and multi-value units; no absence/empty states; adapter capability tests are one-time attestations while providers change under a run | adopted: WS3 `values[]` and thirteen-field provenance inside the envelope; `not_attempted`/`empty` with absence reason and manifest; broker-owned provider health and breaker; stale verification → `unknown` |
| WS4 → WS2 | 17:28 | heartbeat/work separation is violated in the AD hot path; a single `human_action` kind is unprojectable; no denominator-change event; rerun approval rule left open | adopted: counter rule as a contract with a conformance test; four human event kinds; `progress.estimate_revised`; auto-approve when all items required and within budget; one `seq` on events, `journal_seq` on artifacts; `label_domain` axis in the State Registry; `waiting_human` owned by the queue |
| WS6a → WS2 | 17:35 | critique content unspecified (typed checks mandatory); plan steps lack output contract and boundaries; register-and-event for continuation; contract tests are interface-level only; memory needs lifecycle controls; C19 interfaces must be declared | adopted; WS6a revised its own F6 to defer to the register |
| WS6b → WS5 | 17:20 | P0 must not embed a free-form critique; P0+'s selector is a correlated judge; n_repeats ≥ 3 is a floor not a justification; "information-gain threshold" not computable; promotion record lacks hidden evaluators, epochs, lineage archive, replay view, reversal test; answers to WS5's six literature dependencies | adopted: `P0-noreview` ablation; P0+ split into retrieval-rich and sample-rich with an independent selector; LCB promotion from pilot variance; two-identical-snapshots stop; promotion record extended; LLM judge inadmissible for primary domain metrics |
| WS7 → WS2 | 17:25 | reviewer disclosure differs by harness path (both exist; record per exchange); progress writer: redesign the record, keep the discipline; reflection recall gated by promotion; H1 rows missing for web, report lineage, cross-run leaderboard; one `seq` space; promotion schema shared but policies separate | adopted; confirmed from the recorded run `rec_43273c9978` that `progress_version` restarts on resume |

Disputes left standing are recorded as unresolved items U-01 to U-12 in `architecture_decisions.md`.

## 5. Wave 3: integration (coordinator, from 22:15)

- Coordinator wrote `optimized_design.md` (canonical glossary with twenty components and the identifier scheme; purpose; layers; end-to-end flow; component specifications; protocol; run control; tools; evidence and criteria; assessment and leaderboard; memory; observability; human review; evaluation; persistence; failure matrix; no-CDES operation; primary-case path; scope), `architecture_decisions.md` (ADR-01 to ADR-28; U-01 to U-12), and `audit_report.md` (findings A-01 to A-30; reuse verdicts; repository lessons; literature-driven decisions; checklist self-assessment).
- Five drafting forks (which inherit the coordinator's full context) were launched in one message to write disjoint files using only the canonical vocabulary and to flag any missing term: Fork A `iteration_and_provenance_spec.md`, `ui_ux_spec.md`; Fork B `leaderboard_spec.md`, `evaluation_plan.md`; Fork C `rebuttal_alignment.md`, `case_study_protocol.md`; Fork D `tools.md`, `resources.md`, `module.md`; Fork E `literature_review.md`, `suggestions.md`, `task.md`. Their completion records are appended in Section 7 below.
- Consistency checks: a scratchpad script verifies required files, internal links, executable-code fences (none allowed), variant state spellings, and honesty markers; results are recorded in Section 7.

## 6. Wave 4: independent final review

A fresh general-purpose agent (not a fork, so it is not anchored on the coordinator's reasoning; launched 22:37, finished 22:46; it reports that it did not consult the coordinator and spawned no subagents) read the whole `design_audit/` and checks the governing prompt's pre-handoff checklist item by item, writing `agent_reports/final_integrated_review.md`. Its verdicts and the coordinator's fixes are recorded in Section 7.

## 7. Completion records (appended as work finishes)

### 7.1 Drafting forks (launched 22:31; all completed by 22:45)

| Fork | Files | Words | glossary-gap markers | Notes |
|---|---|---|---|---|
| A | `iteration_and_provenance_spec.md`, `ui_ux_spec.md` | 4,567; 4,423 | 2 → resolved by the coordinator: event kinds `memory.operation_recorded` and `report.revision_recorded` added to `optimized_design.md` §4.1; §4.2 now names `ui_ux_spec.md` §13 as the published `ui_label` table | one Mermaid diagram; three worked example traces labelled as placeholders |
| B | `leaderboard_spec.md`, `evaluation_plan.md` | 3,487; 4,507 | 0 | all numeric parameters not fixed by the design written as "registered placeholder — to be set before evaluation"; study sequence E0–E6 |
| C | `rebuttal_alignment.md`, `case_study_protocol.md` | 5,907; 4,241 | 0 | nineteen claims; three marked unestablished as worded ("final 11 CQA" twice; "surufatinib remains the top-prioritized compound"); "target coverage" used as a fourth evidence dimension, matching `tools_and_data.md` §4 |
| D | `tools.md`, `resources.md`, `module.md` | 3,805; 2,499; 3,809 | 0 | verification-gap section (GDSC HTTP 410; Europe PMC 403/404; PubChem client-rendered; NCBI reCAPTCHA; hsi license text absent; CDES absent) |
| E | `literature_review.md`, `suggestions.md`, `task.md` | 9,576; 2,310; 3,996 | 0 | 66 unique sources merged from the two investigators (33 at full text; 42 dated queries; cutoff 12 October 2026); 60 tasks across M0–M8, four blocked on author or expert inputs |

### 7.2 Consistency check (coordinator script, 22:47)

All sixteen required documents and nine agent reports present; every internal Markdown link resolves; no fenced block tagged as an executable language in any file; honesty markers present (`literature_review.md` states its cutoff; `rebuttal_alignment.md` marks current versus planned). Two variant-term flags, both accepted: a prose phrase "waiting for tool" in `ui_ux_spec.md` and the abbreviation `WAIT_TOOL` inside a wireframe in `agent_reports/human_review_and_ui.md` (an agent's own report, not edited by the coordinator). `git status` shows only the untracked `design_audit/` folder; the reference clones live outside the repository. Total words: 75,281 across the sixteen deliverable documents; about 144,000 including the nine agent reports.

### 7.3 Independent final review and fixes (reviewer 22:37–22:46; fixes applied 22:55–23:05)

**Verdict: ready with fixes.** Eleven of fifteen checklist items PASS, four PARTIAL (items 2, 3, 4, 13; item 14 was also marked PARTIAL for leftover glossary markers), none FAIL. Twelve of twelve reference-repository spot-checks confirmed the claims made about Agentic Doping and hsi; two cited ranges were listed as unendorsed rather than refuted. The full report is `agent_reports/final_integrated_review.md`.

| Reviewer finding | Fix applied by the coordinator |
|---|---|
| F1 claim count misstated (eighteen; C3.1–C3.5) | `rebuttal_alignment.md` §2 now reads nineteen claims, C3.1–C3.6; §7.1 of this log corrected |
| F2 `objective_text` labelled verbatim but composite | `case_study_protocol.md` §2.1 relabelled as a reconstruction pending author confirmation; §2.3 lists the verbatim objective as a blocking input |
| F3 domain-shaped capability names in the core list | `optimized_design.md` §7.1, §7.5, §4.13 now use domain-neutral `capability_kind` values with adapter-bound `capability` labels; ADR-29 added; notes inserted in `tools.md` §1 and `module.md` §1 |
| F4 six leftover glossary markers and a false "not yet in the list" sentence | all markers in `iteration_and_provenance_spec.md` replaced with the registered event-kind names; §2.2 sentence corrected; the consistency script now fails on any leftover marker in a deliverable |
| F5 wireframe numbers without a placeholder disclaimer | `ui_ux_spec.md` gained a header disclaimer and a disclaimer line under each of the nine wireframes containing numbers |
| F6 cross-review count understated | `audit_report.md` §1 now states eight assignments producing nine appended sections |
| F7 word total mislabelled; final-review row open | §7.2 relabelled (sixteen documents vs all files); this section closes the row |
| F8 two load-bearing defaults under-advertised | `optimized_design.md` §1 now states that derivation is reference-disclosed and blindness is not claimed; `case_study_protocol.md` §2.3 marks the coverage floor as blocking for Target B |
| Overstatements | §4.12 "impossible by construction" → detectable and rejected; §7.7 heading → "prevented from being recorded as validation"; provenance spec §2.5 scoped to sequence numbering; `audit_report.md` §8 now cites the review's PARTIALs instead of thirteen unqualified yeses |
| Citation hygiene and id collision | full paths `dual_agent/agent_harness.py`, `harness/memory.py` 422-457; placeholder id `chg_C21` renamed to `chg_7f3a21` in both specs |

**Consistency check after fixes (coordinator script).** Blocking problems: 0 (none). Non-blocking variant-term flags: 6, all accepted — they are the registered `ui_label` "waiting for tool" in prose, the abbreviation `WAIT_TOOL` inside an agent's own wireframe, and quotations of those strings in this log and in the reviewer's report. Word counts after fixes: 73,976 across the sixteen deliverable documents; 76,212 across the nine agent reports; 150,188 in total.

**Not changed.** Agent reports were not edited by the coordinator at any point; cross-review additions were made by their own authors. The reviewer's residual-risk list (author inputs gating both targets; expert throughput; pressure on the coverage floor; underpowered promotion; record volume versus projection determinism) is carried unchanged into the handoff summary and into `suggestions.md`'s v1 essentials by reference to the review.

### 7.4 Post-handoff revision (13 October 2026, coordinator)

Trigger: the user restated the final goal: the reference candidate on the leaderboard, and most of the eleven original CQAs produced, with similar items counting. Re-checking the route against that goal, the coordinator found three leakage paths the firewall did not cover (retrieval of the manuscript or its supplement; confirming experts who know the list; adapter templates written from the list) and no mechanism aimed specifically at criterion recall. Changes: ADR-30, ADR-31, ADR-32; `optimized_design.md` §0.4 (exposure and recovery-view vocabularies), §2.2 (two case-configuration rows), §4.9 (`case_source_document` omitted reason), §8.3 (recall-first enumeration, consolidation, optional calibration), §8.6 (case-source and exposure controls; `recovery_view`), §17 (inputs and route paragraph); `case_study_protocol.md` §1, §2.3, new §4.5, §5.4, §6.5; `evaluation_plan.md` §8.1 and study E0b; `rebuttal_alignment.md` C1.7; `task.md` T8.4 and T8.13–T8.15. No subagent was used for this revision, and no independent review of it has been run. The consistency checker was rerun afterwards and exited 0, with only the previously accepted VARIANT-TERM flags.

### 7.5 Second post-handoff revision, independent review, and fixes (13 October 2026)

**Revision (coordinator).** Triggered by two user questions: when a run ends and whether it covers every compound, and what the initial inputs are. Changes: ADR-33 (run completion and the candidate sweep), ADR-34 (field visibility), U-13 (sweep feasibility); `optimized_design.md` §0.4, §2.2 (field visibility paragraph), §3 Stage 6, §4.4, §4.11, §6.3, new §6.6 and §6.7; `case_study_protocol.md` §2.1, new §2.4, §3.1; `evaluation_plan.md` §4.1 and new §8.4; `ui_ux_spec.md` §13; `literature_review.md` stopping criteria; `task.md` T2.6, T2.9, T4.4, T8.6; `audit_report.md` link; new `post_handoff_decisions.md` summarizing all five follow-up discussions. The superseded wording, kept here so the contradiction is verifiable: §6.3 read "Stop reasons: `sufficient_support` (all candidates in the decision-relevant set have complete per-criterion records with independent support at the level the rule version demands and no open trigger), … Only `sufficient_support` permits `completed`", while §16 read "the run reaches `completed` with the coverage summary", and "decision-relevant set" was defined nowhere.

**Independent review.** One general-purpose subagent, launched in the background after the revision, reviewed both post-handoff revisions adversarially and wrote `agent_reports/post_handoff_review.md` (about 11 minutes, 35 tool uses; it edited no other file). Verdict: not ready, with 1 blocking finding (PH-01: the review queue could show the eleven to confirming experts, and exposure was only self-declared), 7 material (PH-02 to PH-09 and PH-14), and 6 minor.

**Fixes (coordinator).** Every finding was addressed by text edits in `optimized_design.md` (§0.4, §0.5, §2.3, §4.10, §4.11, §4.12, §4.16, §4.20, §6.3, §6.5, §6.6, §8.3, §8.6, §10.2, §10.4, §13.6), `case_study_protocol.md` (§4.4, §4.5, §5.1), `evaluation_plan.md` (§4.1, §8.4, §10.4, E2), `architecture_decisions.md` (ADR-13, ADR-31, ADR-32, ADR-33), `iteration_and_provenance_spec.md` (§7.1, §7.3, §11.1–§11.3), `leaderboard_spec.md` (reporting tuple), `module.md` (C4, C11, C15, Case Configuration), `ui_ux_spec.md` (new §11.1, label rows), `task.md` (T1.8, T2.1, T4.4, T8.14, new T8.16), and `post_handoff_decisions.md` (§2 additions, rewritten §6 with a finding-by-fix table). The agent report itself was not edited by the coordinator. The consistency checker exited 0 after these fixes.

**Re-check (same reviewer, resumed).** About 4 minutes, 28 tool uses; appended "Re-check of fixes" to its report. Verdict: ready with fixes. PH-01 (blocking) resolved; 11 of 14 findings resolved and 3 partly resolved (PH-02, PH-05, PH-11); new items N1 to N8, of which three material: N1 (`sweep_scope` bound per run but used per round; the rerun example re-entered a completed run), N2 (artifacts derived from the original list had no visibility rule; the recovery panel was an unlisted reader), N3 (the promotion replay view could include the sealed primary case).

**Second fixes (coordinator).** N1: rerun after completion is a new run with `sweep_scope: rerun_plan`, continuation rounds carry `round_scope`, and the iteration-spec example now creates `run_R1r` (design §6.6; iteration spec §11.2). N2: derived artifacts inherit `evaluator_only` and are excluded from later derivation catalogs; the evaluator-role panel is an enumerated reader (design §2.2, §8.6; protocol §2.4, §5.1; ADR-13; `rebuttal_alignment.md` C1.7; evaluation plan §8.4; UI wireframe; T1.8). N3: the replay view excludes the `final` pool (design §13.7; evaluation plan §10.1). PH-02: canonical `independent` definition and "shapes" defined (design §0.4, §8.6). PH-11: `hard_rule_coverage` aligned in `leaderboard_spec.md`. N4: `memory_mode` added to the Run Binding; protocol §4.5 citations corrected; T4.4 manifest name; `reused` replaced by `reuse.decision: reused_valid`; UI labels for `dependency_detail` and `sweep_scope`. N5: per-cell fingerprint adds `strat@v` and assessor version and forbids cross-arm reuse (design §4.16; iteration spec §7.3). N6: `const_expected_rule_count` declared `control_only` with its source and exposure. N7: the log prevails over a conflicting exposure declaration instead of blocking the summary. N8: T8.4 depends on T8.16; the P0+ retrieval-rich arm no longer adds candidates. The second fixes were checked by the coordinator with greps and the consistency checker, not by a further independent re-check; the checker exited 0.

### 7.6 Third post-handoff revision: two operator surfaces, independent review, and fixes (13 October 2026)

**Trigger.** The user: "i just realize i have to allow user to use both linux terminal&Windows local server(use chrome)".

**Revision (coordinator).** One Operator API served by a service host on Linux or Windows; a terminal client and a browser workbench used in Chrome as its two surfaces; deployment profiles L, W, and X; loopback-only listening with request checks; portable records; platform declarations on tool contracts; host stop handling; terminal command map, wireframes, and parity rules; scenarios S11 and S12; tasks T0.7, T3.7, T6.10 to T6.13; ADR-35, ADR-36, U-14, U-15. Applied by one anchored script (47 edits, 11 files); the consistency checker exited 0.

**Independent review (general-purpose agent, fresh context).** About 13 minutes measured, 39 tool uses (the report's own estimate is 50 minutes); wrote `agent_reports/surfaces_review.md` only. Verdict: not ready. Blocking: SR-01 (a sleep never triggered recovery; recovery would override `paused` and `waiting_human`; a sleep could exhaust the budget) and SR-02 (file permissions on a single Windows account would make every user `exposed`, emptying the `independent` view, and the rule wrote no record). Material: SR-03 to SR-13; minor: SR-14 to SR-17.

**Fixes (coordinator).** All seventeen findings fixed by a second anchored script (67 edits, 9 files) plus updates to `post_handoff_decisions.md` (D6 "After review" row; §5 limits; §6 fix table). The design choices were: encrypt evaluator-only content under an evaluator-held key rather than rely on file permissions; give non-run subjects task streams; record commands durably with declared preconditions and a role table; require interactive entry for `hd_` commands; keep disagreements beside the first decision. The pairing "terminal for Linux hosts, Chrome for Windows hosts" is stated as a v1 limit and left for the user to confirm (U-15). Checked by the coordinator with the consistency checker (exit 0) and a table-column check, not by a further independent re-check.

### 7.7 Fourth post-handoff revision: edit and continue, run groups, skills and lessons; independent review and fixes (13 October 2026)

**Trigger.** The user: "also, I realize that user can edit the runs and continue round and runs. also the switch of run groups shoube be added as a feature. And also i want to know can this system produce skills and lessons during the run?"

**Research (coordinator).** Read the Agentic Doping snapshot `0007ad10` for its run groups (`core/groups.py`; server-wide active group, recorded as a multi-user defect in `cloud_deploy_doc/README.md` 72-77), continue and resume modes (`orchestration/recommend.py` 209-218, 645, 734), and lesson and skill stores (`harness/memory.py` 314, 352, 443-451; `orchestration/reflection.py`).

**Revision (coordinator).** Run chains with run continuations (design §6.8), run groups switched per session (§6.9), in-run drafting of skills and lessons with a Reflector role (§5.1, §10.5), `human_request` round trigger (§4.8), UI §16 and command rows, scenarios S13 and S14, tasks T2.10, T2.11, T5.6, T6.14 to T6.16, ADR-37 to ADR-39, U-16, D7 to D9. One anchored script, 49 edits in 9 files; the consistency checker exited 0.

**Independent review (general-purpose agent, fresh context).** About 11 minutes measured, 42 tool uses (the report's own estimate is 40 minutes); wrote `agent_reports/chains_groups_memory_review.md` only. Verdict: not ready. Blocking: CG-01 (memory, Reflector drafts, person-added rounds, and task edits opened unrecorded channels for knowledge of the original list into acceptance-bearing runs). Material: CG-02 to CG-10; minor: CG-11, CG-12.

**Fixes (coordinator).** All twelve findings fixed by a second anchored script (90 edits in 12 files) plus two stale references in `audit_report.md` and `resources.md`; `post_handoff_decisions.md` gained "After review" rows in D7 to D9 and a CG fix table in §6. The script's first run stopped on three ambiguous anchors with nothing written; a repair to the script itself was needed before the successful run. Checked by the coordinator with the consistency checker (exit 0) and a table-column check, not by a further independent re-check.

### 7.8 Scope cut, consolidated review, and fixes (13 October 2026)

**Trigger.** The user asked for further suggestions ("I believe in you. Any more suggestion?") and, after six were offered, replied "sure, please give more". The coordinator took that as agreement to the two it had offered to start: an independent whole-design check, and a smaller first version.

**Scope (coordinator).** Wrote `v1_scope.md` (about 1,800 words): the in-v1 and deferred table, the build order in five slices mapped to task ids, the inputs to request now, decisions for the user, and three design gaps found while scoping (credentials, backups, exact model versions). One claim in the draft was corrected before the review: the Run Binding records no per-role adapter, not "an adapter per role".

**Consolidated review (general-purpose agent, fresh context, `v1_scope.md` excluded).** About 14 minutes measured, 72 tool uses (the report's own estimate is 80 minutes); wrote `agent_reports/consolidated_review.md` only. Verdict: not consistent. Two blocking findings: CR-01 (four incompatible answers to where a rerun runs and who starts it) and CR-02 (the run monitor would mark every finished single-pass run `unresolved`). Twelve material and four minor findings. Three earlier fixes had landed only in part: N1, CG-02, and CG-12. The reviewer confirmed that every event kind used is registered and that all 262 cross-file section references resolve.

**Fixes (coordinator).** All eighteen findings and the three scoping gaps were fixed by one anchored script (122 edits in 15 files), with ADR-40, design §14.3, tasks T0.8 and T0.9, and `post_handoff_decisions.md` §6 updated. While fixing CR-02 the coordinator found the same contradiction in the C6 failure behaviour, which the reviewer had not listed, and fixed it there too. Checked by the coordinator with the consistency checker (exit 0), a table-column check, a stale-term scan, and a task-reference check, not by a further independent re-check.

### 7.9 Iteration 2 build (13 October 2026, coordinator with subagents)

Build slices after the first exploratory manuscript run, each committed and pushed to `main`:
layered run settings with layer provenance and a bound config hash; a DeepSeek-capable
OpenAI-compatible adapter with key files, thinking control and per-call spend accounting;
a licence-gated evidence-source registry with NCBI Bookshelf (LitArch FTP), Wikipedia,
Wikibooks, user uploads and IUPHAR/BPS curated affinities, plus breadth x depth research
rounds; and the iterative criteria pool (propose, filter, distill, merge, refine, promote)
as a continuable derivation run. Division of labour on the user's instruction: code and
UI by Opus 5.5 subagents, biology by the coordinator at Opus 5.

**Evidence-source coverage probe, and a strategy decision not taken.** The coordinator
measured whether a second curated affinity source adds coverage over the case universe:
of 3,177 universe compounds, 1,988 are identifiable in the IUPHAR/BPS data, and 36 carry
an affinity row for at least one of the five required targets. That answered the
capability question (an independent curation does add coverage), and the source had
already been added to the evidence catalog on general grounds before the probe ran.

A deeper probe that would have listed *which* compounds gain coverage was started and then
deliberately stopped, and its per-compound output deleted unread. Ranking on this case is
judged by where one disclosed reference compound lands, so choosing or weighting an
evidence source after seeing which compounds it favours would make the scoring strategy
outcome-informed (design §13.6) even if no number were tuned by hand. The source stays a
catalog entry that the criteria proposer may or may not bind an attribute to; no scoring
change was made on the strength of the probe.

**Reader quality checks (coordinator, biology).** Textbook sources were checked against
the four screening dimensions before use. Per-drug monograph chapters carry attributable
quantitative pharmacokinetics (one chapter states an oral bioavailability of about 97% with
a time to peak concentration of 0.5 to 3 hours); general topic chapters, after passage
selection, carried no passage that both named a specific compound and reported a number
with a unit, so they support criterion discovery but not per-candidate values. Bookshelf
search recall was found to collapse as query length grows (six planner-style terms
returned one chapter; one term returned twenty-five), because the upstream search ANDs
every term; a bounded relaxation and a monograph preference were specified from these
measurements. ChEMBL's curated mechanism table was found to need the parent-molecule
filter (the obvious molecule filter silently returns nothing for a parent compound), and
to record target engagement with references for compounds whose activity records are
absent; it was added as a catalog entry that is explicitly not a potency surrogate.

### 7.10 Round 1 of the manuscript case: execution record (13 October 2026)

**What ran.** Criteria derivation for the manuscript case executed as three runs in one chain
(`run_01M4TX07ME8VWFJGK2PKNNGSEF`, then two continuations). The first reached enumerate, four
propose stages, filter and distill, and was interrupted mid-refine after 1 h 58 min by the
execution environment's two-hour limit on a background job - not by an error in the system. No
derived state was lost, because pool transitions live in the task stream and a continuation
re-folds them: the second run resumed the tail without re-reading a single document. The
continuations are visible as what they are; the chain is the record.

**Evidence actually gathered** (from the journal, not from a report): 1,002 admitted claims -
637 with a verified verbatim quote and 365 whose numeric value was additionally confirmed to
appear inside that quote - and 9 quarantined, every one for `value_not_in_quote`, which is the
gate catching a number asserted beside a quote that does not contain it. The claims come from 28
documents, of which 17 are NCBI Bookshelf chapters contributing 473 claims, so the licence-gated
textbook route (ADR-44) supplied nearly half the evidence of this round rather than a token
sample. The MediaWiki sources are registered and permitted and contributed nothing in this round;
that is reported rather than smoothed over.

**A defect the pre-flight check caught before promotion froze it.** Five of the fifteen
immediately promotable criteria asked ChEMBL's curated mechanism table whether a compound engages
a required receptor - CSF1R, VEGFR1, VEGFR2, VEGFR3, FGFR1, the most direct evidence this case
has - while accepting only `measured` and `derived` values. Checked against the assessor: such a
claim is admitted and then set aside as `determination_basis_not_accepted`, so the cell reads
"no data", indistinguishable from a compound with no record at all. The catalog entry does state
`determination_basis: "curated"`, so the information was in front of the proposer and was missed.
`validate_proposal` now refuses the pairing, naming both sides, and the run was stopped before
promotion - a registered criterion changes only by expert decision - so the five went back to
refinement instead of into the registry broken.

**Provider behaviour measured before round 2 spends anything** (ADR-46). `deepseek-flash` with
reasoning disabled honours `temperature=0`: two identical extraction calls returned byte-identical
JSON. With reasoning on, two calls spent 700 and 656 of a 700-token completion allowance on
reasoning and returned empty content with `finish_reason: length`; the adapter's empty-reply retry
would have repeated that three times and still had nothing to parse. Requesting `deepseek-chat`,
an id the provider no longer lists, returns a reply that echoes `deepseek-flash`. All three findings
changed code: a truncated reply is asked again with room, and the recorded model id is the echoed
one.

**An operational fault worth recording.** A `DONE` marker left in an exchange queue by an earlier
run made `bridge next --wait` return immediately, so a polling agent concluded the exchange was
over and stopped answering while the run waited for it. The marker now counts only when it is at
least as new as the newest request.

**A sizing constraint, stated before the sweep rather than discovered during it.** Fifty-six of
roughly sixty-five pool items bind to literature retrieval, and the sweep applies every rule to
every candidate. One document read serves every literature attribute for a compound, so cost
scales per compound rather than per cell, but that is still a search, up to two reads and an
extraction for each of 3,177 compounds, which no provider in reach finishes in one session. The
run is therefore staged as the design intends (U-13, ADR-33): a screen of the full universe on the
database-bound rules, then literature on a shortlist as a continuation, with the leaderboard's
member-set hash keeping the two boards distinct and the reference compound's rank reported on both.

### 7.11 Round 1: criteria frozen, and three defects the queue agents found (13 October 2026)

**The pool closed.** Four rounds in one chain, stopping at the round limit with 34 criteria in the
registry and 38 withdrawn. The last two iterations were: filter sent 46 items to refinement and
kept 1, refinement revised 31 and withdrew 24; then filter sent 25 back and kept 7, refinement
revised 27 and withdrew none. Twenty-five promoted criteria carry no open finding; nine are
disputed and wait for an expert. Withdrawals were taken where the cited evidence could not carry
the quantity - no numeric value on the declared axis, variants outside the required receptor set,
class-level or pronoun-subject quotes - or where the construction was confounded, such as a count
that rises with how thoroughly a compound has been studied.

**The fix from §7.10 was unreachable, and the queue agent found it.** `validate_proposal` now
refuses an attribute that cannot accept what its bound source returns, and the system prompt tells
the proposer to declare `acceptable_determination_bases`. But `_normalize_proposal` filters an
attribute to `ATTRIBUTE_FIELDS`, which omitted that field, so the declaration was stripped before
the validator re-read it: the five receptor attributes came back with the identical problem after
every revision. The test that covered the check passed because it called the validator directly,
skipping the normaliser the pipeline runs first. Recorded as ADR-48, because the general fault is
worse than the instance - a prompt may only ask for what the code accepts end to end. The agent
worked around it by rebinding those five to the IUPHAR/BPS curation, which returns a `measured`
basis and a distinct evidence key from the ChEMBL potency criteria; the mapping it could not verify
from its own vantage, ChEMBL target id to UniProt accession, is real and resolves.

**Five rules score the board while disputed.** Confirming the set surfaced that
`confirm_rule_set` admits a preference rule through the trigger table without re-consulting the
open review items, so a rule can sit in `entries` and in `pending[]` at once - the second list
reading, on its own, as "did not enter the set". Thirteen rules score the screen and five of them
are disputed. The entry now records `disputed`, the set records `pending_but_scoring`, and the
acceptance reasons name the rules (ADR-47). The dispute was not decided: only the user may make
that decision.

**What the data actually supports, measured before the sweep.** Of the 3,177 compounds, the
IUPHAR/BPS curation lists 1,988 as ligands but only 36 carry any interaction row against the five
required receptors, and exactly one - pazopanib - carries all five. Surufatinib carries two
(VEGFR2 7.68, FGFR1 7.28), both higher than sunitinib's and sorafenib's at the same receptors,
while pazopanib, nintedanib, linifanib, cediranib and catequentinib carry four or five. Adding an
independent curation therefore makes the case harder, which is the reason to add it. ADR-49 states
the consequence: where measurement is absent the system reports absence, and the board reports its
rankable count beside the universe size instead of presenting one as the other.

**One latent defect fixed on the way.** The per-compound ChEMBL listing asked for a single page of
1,000 rows and never read `page_meta.next`, so a compound with more measurements against a target
than that lost the remainder silently - biasing the median those criteria aggregate rather than
merely dropping records. The sweep takes the cached path, which pages correctly; the single-compound
path a `mas candidate` query uses did not.

## 8. What this log does not claim

During the design waves (§1-§6) no agent executed repository code, started a server, ran a test suite, or performed a screening, ranking, or experiment. The build records from §7.9 onward do report executed code, test runs and live runs, and each states what was measured and where. Literature reads are labelled by depth in each report; abstract-only reads are not presented as full text. Agent self-reports of their own time and reading are reproduced as given; the coordinator verified file existence, word counts, section order, hash checks, and the absence of code fences, not every claimed read.
