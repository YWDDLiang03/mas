# Evaluation Plan

Coordinating agent (drafting fork), 12 October 2026. Design only; no code. Component ids, record names, identifier prefixes, and vocabularies are those of `optimized_design.md` Section 0; the evaluation records are specified in its Section 13. This plan separates process correctness (agent capability) from domain-outcome validation, defines the comparison of single-pass, fixed-round, and adaptive policies under matched budgets on fixed evidence snapshots, specifies the case-level acceptance checks for the primary case, and states the promotion criteria for strategy versions. Nothing here is a result; every numeric parameter not fixed by the design is a registered placeholder — to be set before evaluation.

## 1. Principles

1. **Process correctness is not domain validity.** Passing the process-level scenarios establishes that mechanisms behave as specified; it establishes nothing about biological effectiveness, predictive accuracy, or expert agreement. Every report carries a `claim_scope` block (Section 9) emitted by the Evaluation and Promotion Authority (C19) so that no author can omit it.
2. **No run without a protocol is evidence.** An Evaluation Protocol Manifest (`proto_`) registered and hashed before any arm runs is required for any number to be reported as an evaluation; runs without a `protocol_id` are exploratory and structurally unusable as evidence.
3. **Fixed snapshots, matched budgets, repeated runs.** Policies are compared on the same task contexts, candidate universe, evidence snapshot (`evs_`), tool set, evaluator, and budget; results are probabilities of improvement with confidence intervals across repeats, never a single difference.
4. **Evaluators are hidden, frozen per epoch, and independent.** The functions that score a strategy version are not readable by the agents being evaluated; the evaluator version is frozen for a comparison; same-family model judges are not admissible for primary domain metrics.
5. **Precision never travels alone.** Coverage and abstention accompany every precision figure (`leaderboard_spec.md` Section 7).
6. **The disclosed reference outcome is not a selection signal.** Surufatinib's admission frequency is reported descriptively and excluded from every promotion metric; the historical eleven CQAs are an evaluator-only artifact.

## 2. Process-level agent-capability evaluation

Bounded scenarios on synthetic or small fixed fixtures; no biomedical labels needed. Each scenario is a registered fixture (`proto_` with `pool_assignment: development`) and emits the records named; the pass condition is mechanically checkable from the Event Journal (C1) and the ledgers.

| Id | Capability | Scenario and inputs | Observable outputs | Pass condition | Does not show |
|---|---|---|---|---|---|
| S1 | Task decomposition | an objective with one stated constraint, one unstated-but-necessary unknown, one irrelevant distractor dataset | task context (`task_`), plan (`plan_`) with steps, owners, budgets, completion predicates; `missing_info_requests[]` | the unknown surfaces as a question or `unknowns[]` entry; the distractor yields no step; every step has an owner and a completion check | whether the plan is scientifically right |
| S2 | Appropriate delegation | two task contexts differing only in whether a step needs expert judgement; the C18 trigger table | step owners; `q_` items | the judgement step routes to C18 and the other does not; no `agent_verdict` is stored in a `human_scientific_approval` field | expert agreement with the outcome |
| S3 | Tool-contract correctness | a tool fixture returning in sequence: valid, schema-invalid, timeout, permanent error, empty, pre-check failure | invocation and result records with `outcome`; retry records; per-criterion values | all six outcomes distinguished (`ok`, `failed` with class, `failed` timeout, `failed` non-retryable, `empty`, `not_attempted`); retries bounded and never a round; `empty`/`not_attempted` yield `unknown_missing`, never `fail`; the valid result enters the next step; broker exactly-once holds for a replayed idempotency key | scientific validity of outputs |
| S4 | Evidence traceability | a corpus of three sources, one a duplicate of another under a different identifier, one a preprint of a published paper | claims with locations; independence groups; visibility manifest | every material claim resolves to a `loc_`; the duplicate pair and the preprint/published pair each count as one independence group; no claim lacks a ledger entry; the manifest lists every excluded source with a reason | truth of the sources |
| S5 | Contradictions and missing data | a fixture with a planted threshold conflict and an attribute with no data | conflict records; rule with `cutoff_basis: none_evidence_insufficient`; assessments | the conflict is `unknown_conflicted` with a `q_` item, not averaged away; no cutoff is invented; `unknown_missing`, `fail`, and `inapplicable` are distinct | which side of the conflict is right |
| S6 | Memory isolation and reuse | run A authors a provisional procedure naming a candidate and a threshold; run B is another task in another group; plus twenty legitimate procedure texts | content-policy verdicts with codes; recall sets; `q_` items | the violating text is rejected on every authoring path including automatic ones; no provisional item crosses groups; the false-rejection count on the twenty is reported | whether accepted procedures help |
| S7 | Stop and resume | a run interrupted at each of three checkpoints, then resumed | journal; resumed projection; reuse manifest | resumed state equals the pre-interruption projection replayed from `seq`; steps restored `completed` only with an evaluated artifact; no silent recomputation to a different result; budget exhaustion yields `unresolved` | end-to-end reproducibility |
| S8 | Human-edit propagation | three scripted post-run edits: threshold change, criterion removal, unit correction | stale marks; Rerun Plan; reuse labels; new versions with `hd_` | exactly the dependent records are `stale_by_human_edit`; unaffected results are `reused_valid`; prior versions inspectable; the unit correction propagates to every dependent comparison | whether the edit was scientifically right |
| S9 | Useful strategy updates | one procedure evaluated with and without on a held-out task subset under a manifest | procedure trial records; metric deltas; guard values | delta computed on held-out material at matched budget with no guard violated; absent a positive lower confidence bound, the procedure stays `provisional` | generalization beyond that set |
| S10 | Cost | S1–S9 instrumented through C6 | tokens by role and family, tool calls by tool and outcome, wall clock, human-review minutes per arm per task | every metric is published with its budget; `cost_per_changed_decision` is defined on candidate state transitions only | value for money |
| S11 | Two surfaces, one record | a fixture run and its task stream observed from a terminal session and a browser session at once; scripted commands: the same review item decided from both; one surface deciding an item the other has claimed; a command resent after a dropped connection and after a host restart; the same `command_id` with a changed payload; a pause from the terminal while the browser tab is hidden; a scripted `review decide`; an evaluator-only read by a session without the evaluator role | events with `actor.via`; `cmd_` records and outcomes; labels, counters, and approval slots captured from both surfaces at sampled positions; redacted frames; operator log; access log | at every sampled position both surfaces show the same states, counters, labels, and approval slots; one decision is applied and the other is `rejected_stale_basis`; the decision under someone else's claim is `rejected_not_permitted_in_state`; the resent command returns `duplicate` and is applied once in both cases; the changed payload is `rejected_invalid`; the scripted decision and the unprivileged read are `rejected_unauthorized`; redacted frames keep `seq` contiguous; no surface shows an effect before its event; `run wait` never returns success for `unresolved` | usability of either surface |
| S12 | Portability and host interruption | one recorded journal and one fixed claim set replayed on a Linux host and on a Windows host; a host stopped abruptly mid-step and restarted; a host suspended and resumed without restart, once while `running` and once while the run is `paused` with a step `waiting_human`; a store root on a synchronized folder; a tool fixture declared Linux-only and a local tool fixture whose output differs by platform; submission paths inside the store root, outside the intake directories, and on a network share; requests with a foreign Host header, a foreign origin, `Origin: null`, and no token | `projection.hash`; record hashes; C16 fingerprints; deterministic assessment records; `attempt.finalized` with `host_gap`; tool results with `executed_on`; operator log | projection hashes, fingerprints, and deterministic records are identical on the two platforms; after a stop or a suspend no attempt stays `running`, `paused` and `waiting_human` are kept, and no budget is charged for the gap; the synchronized root is refused with `store_root_unsupported`; the Linux-only tool yields `not_attempted` with `requires_other_environment` on Windows and its cells are `unknown_missing`, never `fail`; the platform-dependent tool's results are not reused across platforms; all three paths are `rejected_invalid`; all four foreign requests are refused | that model outputs are reproducible; that the design holds on any particular Windows or Linux version |
| S13 | Edit and continue | a completed fixture run continued three ways: with a rule edit, with only a larger round budget, and into another group; a paused run continued with an edit; a second continuation of the same parent with and without branch confirmation; a `human_request` round within the round budget and one attempted in a prespecified run; a `waiting_human` parent continued; a budget-only continuation of a `budget_exhausted` baseline under the registered budget-extension rule; a continuation that changes a hard constraint | Run Bindings with `chain_id`, `continues_run_id`, `edits_since_parent[]`; reuse manifests; parents' end records; snapshots and change records; Case Acceptance Register labels | no run that has ended receives new work events; the paused parent ends `completed` or `cancelled` with `human_decision` and `continued_by`; reused cells are exactly those with unchanged fingerprints and name their run; the budget-only continuation reuses every valid cell; continuations made after results were visible are `exploratory`; the unconfirmed second continuation is `rejected_stale_basis` and the confirmed one creates a branch; the human-requested round is labelled and not counted as an adaptive trigger, and the one in the prespecified run is `rejected_not_permitted_in_state`; the waiting parent's review items are `withdrawn` and raised again; the budget-extension continuation stays prespecified and every other post-snapshot continuation is `exploratory`; the hard-constraint change opens a new leaderboard with a `supersedes` link | whether the edits were good |
| S14 | Run groups; skills and lessons during runs | two groups switched independently in a terminal and a browser session; a task with runs moved (refused) and copied; a group archived; a `warm` exploratory run and a `frozen` acceptance-bearing run that each meet a tool error with a corrected retry and a round end; a draft naming a candidate; a draft naming a case-source document; an approved lesson whose author is `exposed`; a `frozen` continuation of the `warm` run | session records; group stream; memory operations; `memory.recalled`; content-policy verdicts | switching changes no record and never affects a running run; each session shows its own group; the move is refused and the copy cites its source; the archived group accepts no new task or run; both runs draft items; only the `warm` run recalls its own provisional item in a later round, journaled; the `frozen` run recalls none; the candidate-naming draft is rejected with `candidate_identifier`; no provisional item is recalled in the other group; the case-source draft is rejected; the exposed author's lesson is not recalled in the acceptance-bearing run; records of the `warm` run that recalled provisional items are recomputed, not reused, in the `frozen` continuation | whether the skills help, which needs a procedure trial |

Additional conformance checks, run as part of S3, S7, and S10: the counter rule (no completion-class event carries an unchanged `completed`; no heartbeat carries a counter); the State Registry mapping (no UI label implies admission when the authoritative state does not); the Model Adapter Capability Record tests (echo, error recovery, two-step dependency, iteration cap reports `budget_exhausted`, idempotency, provenance, conformance across adapters).

## 3. The Evaluation Protocol Manifest

`proto_<ulid>`, registered and hashed before any arm runs, referenced by every evaluation run (`evr_`) and every reported number:

| Field | Content |
|---|---|
| `registered_at`, `registered_by` | attribution |
| `task_set_id` | frozen `task_context_id@v` list; for process scenarios, fixture ids |
| `evidence_snapshot_id`, `snapshot_hash`, `source_access_cutoff` | identical across compared arms |
| `tool_manifest[]` | `{tool_id, contract_version, endpoint_class: local/remote/unavailable, determinism}`; identical across arms |
| `tool_outage_policy` | `abort_arm`, `record_unresolved`, or `retry_bounded` |
| `memory_mode` per arm | `cold` (recalls nothing), `frozen` (recalls only a fixed approved snapshot), `warm` (recalls current approved items and the group's provisional items); every mode may draft items (design §10.5); policy comparisons use cold or frozen; warm is reserved for labelled across-run studies |
| `evaluator_id`, `evaluator_kind`, `evaluator_blinding`, `evaluator_instructions_hash`, `evaluator_epoch` | `human_expert`, `rule_based`, or `llm_judge`; an LLM judge is inadmissible for primary domain metrics and admissible only for mechanically checkable process metrics with a cross-family judge and a recorded independence marker; the epoch is frozen for the comparison |
| `hidden_evaluator_function_refs[]` | stored outside agent-accessible memory; never readable by evolved agents |
| `metrics` | ordered primary metrics and guard metrics (Section 6) |
| `budget_caps` per arm | tokens, tool calls, wall clock, human-review items, reflection turns (Section 5; arms with and without reflection are compared only at matched caps) |
| `seeds`, `n_repeats` | `n_repeats ≥ 3` is a floor; the working `n` is derived from pilot variance (Section 10) — registered placeholder — to be set before evaluation |
| `analysis_plan` | probability of improvement with confidence intervals; lower-confidence-bound comparison with declared `z` and noise leeway |
| `stopping_rule_for_the_evaluation` | when the study itself stops |
| `pool_assignment` | `development`, `validation`, or `final` |
| `claim_scope_template` | what the study can and cannot establish |

## 4. Operating policies and comparison rules

### 4.1 Arms

| Arm | Definition | Continuation | Stopping | Budget role |
|---|---|---|---|---|
| P0 single-pass | one screening round; roles contribute within the pass; per subject one proposal, one critique with external referents, one revision | none | after the round, with `round_limit_reached` once the sweep is complete (`optimized_design.md` §6.6–§6.7); unresolved items stay `unresolved` | its realized cost defines the matched cap |
| P0-noreview | P0 without the critique step | none | after the round | ablation of the review exchange |
| P1 fixed-round (R) | exactly R scheduled rounds; R registered (R = 2 and R = 3 are separate versions) | scheduled | after round R (`round_limit_reached`) | reference configuration; cost reported |
| P2 adaptive | continue only on a C8 open question with a referent, a non-empty expected decision change, and an untried method within budget | the five adaptive trigger classes (never `human_request`, which is barred from arm runs) | `sufficient_support`, `round_limit_reached` (round budget used), `no_actionable_step`, `diminishing_information_gain` (two consecutive identical snapshots with no new ledger entries), `repeated_failure`, `budget_exhausted` → `unresolved`; two consecutive `non_progress` Round Progress verdicts | the candidate policy; the cost of each continuation decision is counted |
| P2-cap | P2 hard-capped at P0's realized median budget | as P2 | P2's plus the cap | adaptivity at equal spend |
| P0+ retrieval-rich | P0 given P2's realized median budget in one pass, spent on wider retrieval per candidate and criterion (the sweep already covers every candidate in scope) | none | after the round | same spend, no extra rounds |
| P0+ sample-rich | P0 given P2's realized median budget in one pass, spent on best-of-N proposals selected by an independent selector (cross-family, rule-based, or human; the selector's independence marker is recorded) | none | after the round | same spend, no extra rounds; surplus mode attributable |

### 4.2 Comparison rules

P2 is reported as an improvement only if it beats P0 and both P0+ variants on the registered primary metrics and P2-cap does not fall below P0, with the lower confidence bound over `n` repeats exceeding the incumbent by more than the declared noise leeway. If P2 beats P0 but loses to either P0+ variant, the conclusion is that budget helped and adaptivity did not. P0-noreview versus P0 isolates the value of the review exchange; a null difference is a finding about the critique, not a license to drop verification. P1 at one registered R is the control for "more scheduled rounds". All arms run on the same `proto_`, the same `evs_`, the same tool manifest, and cold or frozen memory.

### 4.3 Round Progress Record (C19)

For every round transition: `round_id`, `parent_round_id`, `trigger_claimed`, `progress_kind` (`new_admissible_evidence`, `resolved_conflict`, `filled_consequential_gap`, `corrected_decision`, `registered_negative_result`), `evidence_delta_ids[]`, `conflict_ids_resolved[]`, `gap_ids_filled[]`, `decision_changes[]`, `verdict` (`progress`, `non_progress`, `unresolved`).

| Progress | Required observable | Non-progress | Why excluded |
|---|---|---|---|
| new admissible evidence | ≥ 1 new `claim_` with a resolvable `loc_`, de-duplicated by independence group | rephrased rationale | no ledger delta |
| resolved conflict | a conflict moves `open → resolved` or `irreducible` naming the deciding claim or `hd_` | higher self-reported confidence | an LLM confidence statement is not a reliability estimate |
| filled consequential gap | an `unknown_missing` becomes a supported verdict and flips a per-criterion verdict, or was preregistered as decision-relevant | more citations for an already-supported claim | copies of one study are one independence group |
| corrected decision | a candidate state or criterion version changes with a named cause | longer or more elaborate reasoning | no ledger or decision delta |
| registered negative result | a planned retrieval or tool call returned nothing admissible and is recorded as such | agreement between agent roles | shared context, shared bias |

A registered negative result is progress for the record but does not by itself justify continuation; continuation needs a type 1–5 trigger. "Information gain below a threshold" is not used as a stop: it is not computable without a finite answer space and ground truth.

## 5. Matched-budget checks

What is matched: tokens by role and model family, tool calls by tool, wall-clock time, and the number of human-review items, as recorded by C6 per round and per arm. The cost of deciding whether to continue (planner turns, register maintenance) is charged to the adaptive arm. Human-review minutes are not scalarized into machine cost: machine budget is matched, human-review items per arm are capped with overflow recorded as `unresolved`, and human minutes are reported as a separate axis. The cost of producing a strategy revision is included in that version's budget when promotion is assessed. `cost_per_changed_decision` (changed decision = candidate state transition) is reported beside every metric so a policy that spends more to change nothing is visibly worse. Budget matching uses the median realized budget of the reference arm; whether the ninetieth percentile is the better statistic is a registered placeholder — to be set before evaluation.

## 6. Separated evidence snapshots and memory modes

Every policy comparison runs on one frozen `evs_` (admitted claim ids with source versions, cutoff, tool availability, hash), so a gain cannot come from new data. Across-run improvement studies that need memory accumulation use `memory_mode: warm` and are labelled as such; they never share a manifest with a policy comparison. Evidence-refresh runs for the longitudinal leaderboard are production runs, not evaluation arms, and are reported separately.

## 7. Metrics

| Metric | Definition | Labels or expert review | Reporting rule | Unestablished without labels |
|---|---|---|---|---|
| precision among admitted | fraction of `recommended` entries an expert panel judges correctly admitted under the stated criteria and evidence | qualified expert review on the admitted set | always with `admitted_n`, coverage, abstention; undefined at zero admissions | pharmacological effectiveness |
| evidence correctness | fraction of sampled material claims whose `loc_` supports the claim as stated | expert or trained-annotator review of a registered sample; inter-rater agreement reported | sampling frame and size reported | whether the sources are right |
| independent support | fraction of admitted entries whose decisive hard rules rest on ≥ 2 independence groups not `assumed_distinct` | de-duplication plus expert adjudication of borderline groups | grouping rule reported | joint correctness of sources |
| unsupported-claim rate (guard) | material claims with no resolvable `loc_` or a `loc_` that does not support them | expert sample | must not rise | — |
| incorrect-exclusion rate (guard) | fraction of sampled `rejected` entries judged wrongly excluded | stratified expert sample including borderline exclusions | beside precision; a precision gain with a rise here is not an improvement | true negatives in any biological sense |
| coverage (guard) | fraction of the candidate universe with a complete per-criterion assessment | none | mandatory beside precision; must not fall | — |
| abstention | `unknown_missing`, `unknown_conflicted`, `not_assessed` counts by reason | none | mandatory; an empty shortlist is abstention, not precision 1.0 | — |
| uncertainty calibration | agreement between stated bands and expert-adjudicated correctness where a band exists | expert review on that subset | subset size reported; LLM confidence excluded by definition | calibration where no band exists |
| reproducibility | agreement of candidate states and criterion versions across repeats at fixed snapshot and policy | none | per arm over `n` seeds; disagreements itemized | correctness |
| operating cost | tokens, tool calls, wall clock, human-review minutes per task per arm | none | attached to every metric | — |
| proxy-vs-held-out gap | difference between a strategy version's metric on its selection material and on held-out material | none | reported per version; growth across optimization steps is a guard breach | — |

Visibility-manifest statistics (catalog size, excluded-reason distribution, conflicting-to-supporting ratio) are additional guard metrics, so a retrieval- or prompt-rule change that shifts which claims are admitted is detectable even though it touches no criterion.

## 8. Case-level acceptance checks for the primary case

No result is asserted. These are checks to run later with recording rules fixed in advance in the Case Acceptance Register (C19) and two-stage preregistration (`preregistration.recorded` events: policy before derivation; criterion version on expert approval).

### 8.1 CQA recovery

The historical eleven CQAs enter as the evaluator-only intake record (`optimized_design.md` Section 8.6), excluded by construction from derivation context and listed in each derivation decision's visibility manifest. The comparison function produces one recovery comparison record per historical item and per unmatched derived attribute with `mapping_kind` from the nine stored values (`recovered_equivalent`, `recovered_with_narrower_applicability`, `recovered_with_different_cutoff`, `merged_into`, `split_into`, `not_recovered_no_evidence`, `not_recovered_out_of_scope`, `deliberately_removed`, `newly_added_not_in_history`), `rule_role_match`, `match_basis`, and `agreement_evidence`; `expert_judged_equivalent` mappings require an `hd_`. Reporting: the fraction with its denominator (and the completeness attestation of the intake), the six-category roll-up (recovered, merged, split, removed, added, not recovered) with `recovered_with_different_cutoff` as a separate sub-count, both by item count and by decision impact, plus an expert reason-quality rating per criterion on a registered ordinal scale. High recovery with poor reason quality is not acceptance. The threshold for "most" is a registered placeholder — to be set by the authors and experts before evaluation. Recovery is reported in the `independent` and `assisted` views (`optimized_design.md` §8.6), and the threshold names the view it applies to. When external calibration cases exist, the derivation strategy is frozen on them before E2 (study E0b) and the calibration-to-case recall gap is reported.

### 8.2 Surufatinib admission

| Check | Prespecified content | Observable output | If not met |
|---|---|---|---|
| baseline configuration | `rules@v` id; hard exclusions versus preferences; ordering method; `evs_` id; universe id; tool manifest; `derivation_configuration: reference_disclosed` | `lb_` snapshot with per-candidate per-criterion records | — |
| decisive criteria to report | the hard rules whose verdicts determine the candidate's state, named in advance; no expected state is registered | the candidate's state with per-criterion evidence, value provenance, verdict, and reason | record the observed state, the criteria that failed or were `unknown_*`, and the cause (absent evidence, tool gap, excluding criterion); do not adjust the baseline |
| result-type naming | whether the claim will be unique all-pass or top-ranked follows from the actual selection procedure | `result_kind` on the snapshot | the rebuttal uses the produced kind; they are different claims |
| sensitivity ranges | per-criterion ranges with justification and sources, timestamped before evaluation | candidate states and orderings under each configuration, all retained | configurations not admitting the candidate reported with equal prominence |
| alternative configurations | named justified alternatives (applicability condition, unit convention, stricter evidence tier, `reference_blind` derivation as a sensitivity arm) | comparative snapshots with rank-change explanations | reported as-is |
| outcome dependence | leave-one-out over hard rules: how many would change the candidate's verdict if removed, without tuning | `outcome_dependence_report` per snapshot | — |
| exploratory tuning | any range or configuration chosen after seeing outcomes | labelled `exploratory` (the acceptance label of design §13.6) everywhere | never described as prespecified |

### 8.3 Rebuttal-wording implications

| Outcome | What may be stated |
|---|---|
| admitted under the baseline and across the registered ranges | a conditional prioritization, naming the ranges and the result kind |
| admitted under the baseline but not across parts of the ranges | conditional on the specific assumptions that sustain it, naming those that do not |
| not admitted under the prespecified baseline | the derived criteria, the specific failures or missing measurements, and what evidence would resolve them; the framework cannot be said to have recovered the original prioritization |
| `unresolved` from budget or tool unavailability | neither admission nor non-admission; the open questions and required inputs |
| low CQA recovery | the framework derives an evidence-linked criterion set differing from the historical one in stated ways; it does not reconstruct the original rationale |

### 8.4 Run verification checklist

A reader of an executed run checks the following, each against the named records (`optimized_design.md` §17).

| Question | Check | Records |
|---|---|---|
| Were rules and targets fixed before results? | stage-1 and stage-2 preregistration events precede the first derivation event and the first `candidate.assessed` event; the sweep ordering policy and seed are in stage 1 and the concrete sweep order in stage 2; the threshold for "most" is registered before evaluation | R5, R9 |
| Did any agent see the original list or the manuscript? | the intake access log shows only its enumerated readers (the review queue only on comparison-adjudication items), and artifacts derived from it are excluded from every later derivation catalog of the case; every derivation visibility manifest lists the `evaluator_only_artifact` and `case_source_document` exclusions; the case-source retrieval-hit log is reviewed | R1, R9 |
| Who knew the list? | exposure declarations on every criterion-affecting `hd_`, template, and global shaping artifact agree with the access log; criterion-content scan results present; recovery reported in both views |  R4, R7 |
| Did the run cover every compound? | for a `full_universe` run: row count equals universe size; `sweep_completeness` = 1; the `unswept_cells_manifest` is empty for a `completed` run; `coverage_fraction` is reported separately and is expected to be far below 1 without an interaction-prediction backend | R2, R3 |
| Is each verdict traceable? | a random sample of compound × criterion cells traced from verdict to claim to source location; disqualifier check passes | R1, R2 |
| Is the leaderboard reproducible? | rebuild from the journal; `projection_hash` matches | R3, R9 |
| Are the reasons good? | expert ordinal ratings per criterion | R4 |
| Does admission depend on one rule? | outcome dependence report | R5 |
| Does it hold under alternatives? | registered sensitivity configurations and the `reference_blind` arm, reported with equal prominence | R5 |
| Was the reference candidate treated specially? | identical per-candidate caps in the cost records; alias scan clean; candidate-symmetric scrutiny verdicts present | R1, R9 |
| Did the host or the surface change anything? | the Run Binding names the host platform and the resolved tool manifest; every tool absent with `requires_other_environment` is listed with its cells; decisions carry `actor.via`; a run compared with a run on another platform has an identical tool manifest | R6, R9 |

## 9. Claim scope

Every process report and every evaluation run carries `claim_scope {establishes[], does_not_establish[], label_dependency}`. For the process scenarios: establishes the observed mechanism behaviours; does not establish biological effectiveness, predictive accuracy, expert agreement, or generalization beyond the fixtures. For the policy comparison: establishes relative performance on the registered metrics at matched budget on the registered snapshot; does not establish domain correctness without the expert-reviewed metrics. For the case checks: establishes the observed states and recovery mapping under the registered configurations; does not establish that any candidate is pharmacologically effective. For strategy promotion: establishes a measured, held-out improvement on the registered metrics; does not establish sustained acceleration, meta-improvement, or cross-domain transfer.

## 10. Strategy promotion

### 10.1 Promotion conjunction

A strategy version (`strat@v<n>`, C20) is promoted only if all hold: (1) positive delta on the registered primary metrics against the fixed baseline on held-out tasks spanning more than the current case, at matched budget, with the lower confidence bound over `n` repeats exceeding the incumbent by more than the declared noise leeway; (2) `evidence_admission_predicate_hash` identical to the baseline's (a change to what counts as admissible evidence, including the coverage floor and registered constants, is a criterion change needing an `hd_`, never a strategy improvement); (3) no guard metric degraded beyond registered tolerance; guards are gates, not weighted terms; (4) reference-outcome selection frequency excluded from promotion metrics and reported descriptively; (5) `proxy_vs_held_out_gap` reported and not growing across optimization steps; (6) a replay/retention view on earlier cases outside the `final` pool shows no regression; (7) the rule-reversal test passed for any procedure that influences criteria (the procedure, presented with a fixed snapshot contradicting it, is revised); (8) an `operations_decision` (`ops_`) by a named operator, a record kind disjoint from `human_scientific_approval`.

### 10.2 Hidden evaluators and epochs

The evaluator functions that score versions are stored outside agent-accessible memory and are never readable by the agents being evaluated; the evaluator version is frozen for an epoch and changes only between epochs with a recorded reason. Held-out composed checks (cases or criteria never used for selection) are evaluated only when a version is nominated, and each touch is counted in the version record.

### 10.3 Pools

`development` (free use, re-sampling allowed), `validation` (fixed; candidate selection; a registered maximum number of looks per lineage), `final` (sealed; opened at most once per lineage; the opening recorded; a second look invalidates that lineage's claim). Pool sizes and the maximum looks are registered placeholders — to be set before evaluation; the literature's indicative requirement is on the order of several hundred effective items for stable selection, which for a single case means repeated runs and multiple cases.

### 10.4 Archive, rollback, expiry

Versions are archived with lineage and never deleted; the parent remains executable; rollback to any archived version is a one-step journaled event; approved versions carry an `expiry_at` that forces re-evaluation or reversion; a guard breach on later material triggers rollback as an event. `lineage_metrics` (outcomes of derived versions and refresh runs that reused a version, excluding every `final`-pool run and its refresh and rerun runs, so the primary case never feeds selection) are recorded and may be weighed only when at least one evaluated descendant exists; `unknown` outcomes are excluded from both success and failure counts and reported as coverage. The promotion selector and policy are declared in the Run Binding (`promotion_policy_version`) and sit outside any evolvable surface.

### 10.5 No-additional-training baseline and optional training

v1 runs on prompts, procedures, retrieval rules, and tool contracts with pinned external model versions; nothing is trained, fine-tuned, or calibrated. This is the comparison arm for every later model. An optional trained model must specify: task; training data and its provenance; labels or reward source and how labels enter through the ledger gate (reviewer-accepted records only); method; compute; a held-out set disjoint from training; evaluation against the no-training baseline under the same manifest at matched budget; cost; and the value it must demonstrate (for the one candidate identified by the tools workstream, an evidence-extraction model, reviewer minutes per accepted evidence record at equal or better exact agreement of value and unit, plus conflict-detection recall). Reflection-authored prompt text is a memory update, never training; `change_class` separates `prompt_text`, `procedure_memory`, `tool_selection_rule`, `retrieval_rule`, `failure_handling`, and `model_weights`.

### 10.6 Evaluator-exploitation guard list

The guard list that every promotion review and every log inspection checks, from the literature workstream: (1) removal or alteration of detector tokens or logging that an evaluator relies on; (2) edits to scoring or evaluation scripts; (3) proxy-only gains that grow with optimization steps; (4) memorization of test inputs or held-out items; (5) seed cherry-picking and extraction of test labels; (6) selection by noise on small validation sets; (7) consensus inflation among same-context agents; (8) same-family judge inflation and self-preference; (9) regressions hidden by endpoint metrics (checked by the replay/retention view). Each is a registered inspection item with a pass/fail record on the evaluation run.

## 11. What the literature does and does not settle

Settled: extra rounds or homogeneous debate do not help after cost except on an external trigger (hence P1 at one R as a control and P2 only with trigger logging). Not settled: pool sizing and minimum detectable effect; variance of agent-policy comparisons (indicative swings in the literature are large); any convention for matching budgets with uneven human-review loads (hence the separate-axis rule); whether an LLM judge reaches adequate agreement with experts on domain correctness (hence inadmissible for primary domain metrics); whether memory or strategy gains observed in coding and games transfer to a domain whose feedback is expert judgement (no evidence found; hence the pilot-first sequence below).

## 12. Sequence of evaluation studies

| Order | Study | Inputs | Outputs | Gate to next |
|---|---|---|---|---|
| E0 | pilot variance estimation | P0 on the development pool, `n` seeds, fixed `evs_` | reproducibility across seeds; variance per metric; realized P0 budget | working `n_repeats` and noise leeway registered |
| E0b | derivation-strategy calibration (optional) | external calibration cases in `development` and `validation` pools; criterion recall and expert-rated reason quality | promoted derivation strategy; recall per calibration case | strategy frozen and recorded in the Run Binding before E2 |
| E1 | process scenarios S1–S14 | fixtures | pass/fail per scenario with `claim_scope` | all pass, or failures recorded as blocking implementation defects |
| E2 | P0 baseline on the primary case | case configuration; `rules@v1` confirmed by experts; `evs_1`; stage-1 and stage-2 preregistration; `memory_mode: cold`, or `frozen` over an approved snapshot taken before any intake access | `lb_<task>_1`; recovery comparison summary; Case Acceptance Register check; outcome dependence report; reporting tuple; expert ratings | records R1–R9 of `optimized_design.md` Section 17 exist |
| E3 | arm comparison | P0, P0-noreview, P1(R), P2, P2-cap, P0+ (two variants) on the same `proto_` | probability of improvement with intervals; Round Progress Records; cost per changed decision | the single-pass-versus-adaptive answer for this task class, with its uncertainty |
| E4 | sensitivity and alternative configurations | registered ranges and alternatives, including `reference_blind` derivation | states and orderings under each; exploratory configurations labelled | the conditional statement the rebuttal may make |
| E5 | promotion attempts | candidate strategy versions; validation pool; held-out material touched at nomination | promotion records with LCB, guards, gap, replay view, `ops_` decisions | promoted, kept as candidate, or rejected; rollback targets retained |
| E6 | across-run improvement study (labelled) | `memory_mode: warm`; separate manifest | retention and transfer measurements | informs later versions; never merged with E3 |

Each study emits its own `claim_scope`. If E0 shows variance that makes E3 or E5 underpowered at affordable `n`, the plan says so and reports E3 as descriptive rather than as a promotion basis.

Sources: `optimized_design.md` Sections 0, 4.8, 4.11, 4.12, 6.3, 8.6, 13; `agent_reports/evaluation_and_improvement.md` (Findings 1–12, STEP 1 table, scenarios, cross-review and revision notes); `agent_reports/current_agent_literature_b.md` §4–§6 and cross-review (six dependency answers; exploitation patterns); `agent_reports/current_agent_literature_a.md` F8, F9; `agent_reports/evidence_and_policy.md` §5, §6, §8 and cross-review; `agent_reports/tools_and_data.md` §7 and Finding 8; `agent_reports/reference_harness_inspection.md` F8, F12, F13; governing prompt §4.1 and §5.
