# Rebuttal Alignment

Coordinating agent, 12 October 2026. Design phase only. This document maps every material statement of the supplied rebuttal draft to the system capability that would realise it, the evidence that would substantiate it, the future evaluation that would test it, the records it would produce, and the condition under which the statement becomes true.

**Nothing in this document reports a completed experiment, a ranking, a sensitivity outcome, or an expert approval.** Where the draft uses completed-work wording, the wording is treated as a requirement to substantiate later, not as a fact. Component ids (C1–C20), record kinds, state vocabularies, and the R1–R9 record index follow `optimized_design.md` Section 0 and Section 17.

## 1. How to read the mapping

Each claim carries a **status**:

| Status | Meaning |
|---|---|
| **current** | The capability and record structure exist in this design and need implementation only; the claim can be made about the *design* today, not about a run. |
| **planned** | Requires implementation plus an executed run with real inputs before the claim can be made at all. |
| **unestablished** | Cannot be substantiated as worded, now or by a run, because the wording asserts something the design deliberately does not provide (for example a fixed criterion count, or a prespecified expectation about the reference candidate). A truthful alternative phrasing is given. |

Two further distinctions are used throughout, because the draft blurs them:

- **Intended outcome** versus **verified result.** The case seeks to substantiate surufatinib's high priority under the stated objective and target configuration. That is an intended outcome registered in the Case Acceptance Register (design §13.6). It is not a result and must never be written as one.
- **Unique all-pass candidate** versus **top-ranked candidate.** Under hard exclusions the primary claim is `result_kind: all_pass_set` with an `all_pass_count`; under a continuous ordering it is `result_kind: ranked_under_score`. These are different claims about different procedures, and the selection procedure actually applied determines the wording (design §0.4, §4.12).

**Record index (design §17).** R1 confirmed rule-set versions with source-linked change history and critiques · R2 per-candidate per-criterion assessment and reason records · R3 leaderboard snapshots with result kind, reporting tuple, and change records · R4 recovery-comparison summary against the historical criteria with expert reason-quality ratings · R5 preregistration events, Case Acceptance Register, and sensitivity results with prespecified versus exploratory labels · R6 tool and adapter records, including absence records · R7 expert decision records · R8 evaluation protocol manifest and `claim_scope` blocks · R9 journal exports for every round and analysis step.

## 2. Claim-by-claim mapping

The three draft paragraphs are split into nineteen material claims. Paragraph 1 is C1.1–C1.7, paragraph 2 is C2.1–C2.6, paragraph 3 is C3.1–C3.6.

### Paragraph 1 — criteria as revisable hypotheses

**C1.1 "Our original CDES analysis did not sufficiently document how the screening criteria were established, challenged, and validated, nor how sensitive the final prioritization was to the adopted rules and thresholds."**

| Field | Content |
|---|---|
| Capability | None required; this is a concession about the prior work. The design's answer to it is the Criterion Registry change history (C10), the Evidence Ledger (C9), and the registered sensitivity protocol (C19). |
| Evidence | The manuscript itself, which states a binary pass/fail funnel over criteria in three dimensions without enumerating the criteria in its main text. |
| Evaluation | Not applicable. |
| Records | R1, R5 are the remedy, not the evidence for the concession. |
| Acceptance condition | The concession is already true and may be stated now. |
| Status | **current** |

**C1.2 "To address this limitation, we implemented an iterative, tool-augmented multi-agent system."**

| Field | Content |
|---|---|
| Capability | The whole core: C1 Event Journal, C5 Planner/Delegator, C7 Proposer–Critic Protocol, C13 Tool Broker, C15 Run Controller. "Tool-augmented" is C13 with a verified Model Adapter Capability Record (design §7.6); "iterative" is C8 Open-Question Register plus the P2 arm, and is *not* required of every run (P0 single-pass is the default, design §13.3). |
| Evidence | Not a scientific claim. Substantiated by a runnable system, a versioned configuration, and execution records. |
| Evaluation | Process-level scenarios S1–S14 (`evaluation_plan.md`): decomposition, delegation, tool-contract correctness, traceability, stop/resume, human-edit propagation, cost. Contract tests for tool feedback (design §7.6) must pass, because the inspected reference had a provider that reported tool capability while discarding tool results. |
| Records | R9 (journal with run, round, step, exchange events), R6 (adapter capability records and contract-test run ids), R8 (`claim_scope`). |
| Acceptance condition | An executed run exists whose journal shows plan, delegation briefs, result returns, tool invocations with results fed into subsequent steps, and a terminal state with a `termination_reason`. |
| Status | **planned** |
| Wording not yet usable | "we implemented" (past tense, completed). |
| Truthful alternative | "We developed an iterative, tool-augmented multi-agent system and applied it to this screening question; its execution records are provided in Supplementary [R9]." Usable only after a run. |

**C1.3 "Rather than treating the original CQA criteria as fixed inputs, the framework treats screening rules as revisable scientific hypotheses."**

| Field | Content |
|---|---|
| Capability | C10 Criterion Registry: two-record contract (Attribute + Rule), versioned, with change records carrying `operation` ∈ add/revise/merge/split/remove/reinstate, `reason_kind`, `source_refs`, and `human_decision_ref` for any transition into `confirmed`. `belief_status` ∈ proposed/supported/contested/refuted/retired makes the hypothesis status explicit. The rule-reversal test (design §4.10) checks that a rule is actually revised when a fixed snapshot contradicts it. |
| Evidence | Source-linked claims (C9) behind each criterion field, with `field_provenance` naming which actor set which field. |
| Evaluation | Scenario S5 (contradictions and missing data) and the reversal test; recovery comparison (R4) shows which historical criteria survived derivation and which did not. |
| Records | R1, R4. |
| Acceptance condition | The registry contains at least one criterion whose version history shows a revision, merge, split, or removal with a `reason_kind` and `source_refs`, and the reversal test is recorded for every promoted rule. |
| Status | **current** (design) / **planned** (as a statement about this case) |

**C1.4 "Role-specialized agents synthesize target-level, pharmacological, and counter-evidence to propose candidate CQA criteria, including their definitions, directions, thresholds, units, and applicability conditions."**

| Field | Content |
|---|---|
| Capability | C7 roster: Evidence Retriever with its own budget and provenance duties, Proposer, Deterministic Validator, Blind Critic. Counter-evidence is a *search obligation plus deterministic verification*, not a persona (design §5.1): the Retriever must produce a `search_coverage_record` and the critique must carry a `counter_evidence_considered` check with a verdict. The Attribute record carries `definition`, `direction`, `unit` and `unit_system`, `applicability_conditions`, `acceptable_value_sources`; the Rule record carries `cutoff` or `absent` with a mandatory `cutoff_basis`. |
| Evidence | Claims for each dimension: target coverage, oral bioavailability, metabolic stability, toxicological safety. Values carry `determination_basis` ∈ measured/predicted/asserted/derived/absent and `value_kind`. |
| Evaluation | Scenario S4 (evidence traceability, including a planted duplicate under a different identifier) and the `evidence_support` critique check; the visibility manifest (C9) is a publication gate against selective literature use. |
| Records | R1 (criterion fields with provenance), R2 (per-candidate values), R9. |
| Acceptance condition | Every confirmed criterion field has a `field_provenance` entry; every quantitative attribute has a unit; every cutoff has a `cutoff_basis`; `none_evidence_insufficient` is a legal and used value where evidence supports no number. |
| Status | **planned** |
| Wording not yet usable | "thresholds" as if every criterion must have one. |
| Truthful alternative | "…including their definitions, directions, units, applicability conditions, and, where the evidence supports one, a threshold or range; criteria for which the evidence supported no numerical cutoff are recorded as such." |

**C1.5 "Critic and arbiter agents then identify weakly supported, redundant, or conflicting criteria and propose additions, modifications, mergers, or removals."**

| Field | Content |
|---|---|
| Capability | C7 critique with typed `checks[]`; C10 registry invariants detect *arbitrary cutoff*, *duplicate*, *units*, and *weak exclusion* mechanically, so "weakly supported" and "redundant" are not left to model judgement. Adjudication is deterministic by default (a precedence table over typed findings); an escalated adjudicator is invoked only on persistent disagreement about an identified referent (design §5.5). Dissent is recorded on every decision, including on admissions. |
| Evidence | Independence groups (C9) decide whether support is genuinely multi-source; a preprint and its published version collapse to one group, so "weakly supported" has a computable meaning. |
| Evaluation | Scenario S5; the duplicate invariant's overlap share is a registered constant (design §8.4) and merges are only ever *proposed*, never applied automatically. |
| Records | R1 (change records with `arbitration_outcome`), R9 (exchange events), R7 where escalation reached an expert. |
| Acceptance condition | Each criterion change record names its critique or invariant finding; no unaddressed major finding lacks an override reason. |
| Status | **planned** |
| Wording not yet usable | "arbiter agents" implies an LLM arbiter in the normal path. |
| Truthful alternative | "A critic agent and deterministic validators identify weakly supported, redundant, inconsistent, or conflicting criteria; conflicts that rules cannot settle are escalated, with dissent recorded." |

**C1.6 "Human experts review these proposed rule updates before they are incorporated into the next iteration."**

| Field | Content |
|---|---|
| Capability | C18 Human Review Queue owns the `waiting_human` state and the only writer of `human_scientific_approval`. The trigger table (design §12.1) requires an expert decision before publication for every hard exclusion entering `confirmed`, every `expert_set` cutoff, every `unknown_conflicted` on a hard rule, every attribute merge or removal, every unit normalisation that changes a verdict, and every `recommended` publication where the case configuration requires it. Four disjoint approval fields (`agent_verdict`, `software_status`, `human_scientific_approval`, `operations_decision`) make it structurally impossible for an agent verdict or a software status to be read as expert approval. |
| Evidence | `hd_` records with actor identity, `identity_basis`, declared scope of expertise, reason text, edits with before/after, and `downstream_invalidation`. |
| Evaluation | Scenario S2 (delegation: a judgement step must route to review and a non-judgement step must not) and S8 (human-edit propagation). |
| Records | R7, R1 (`confirmed_by`), R9. |
| Acceptance condition | Every `rules@v` marked confirmed references at least one `hd_`; no automated gate reads `human_scientific_approval`. |
| Status | **planned**. This is the claim most at risk: the inspected reference wrote `review_state: "approved"` from a distiller and hard-coded `approved_by="human"`, so an implementation that copies it would silently invalidate this sentence. |
| Wording not yet usable | Any phrasing implying expert review occurred. |
| Truthful alternative | "Proposed rule updates are routed to human experts, whose recorded decisions are required before a rule version is marked confirmed; the expert decision records are provided in Supplementary [R7]." |

**C1.7 "Through successive evidence–critique–human review cycles, the rule set is progressively refined toward the final 11 CQA criteria used for candidate prioritization."**

| Field | Content |
|---|---|
| Capability | C10 version history plus the recovery comparison (design §8.6). The historical criteria are an **evaluator-only comparison artifact** held in the case configuration with enumerated readers and an access log, and artifacts derived from it inherit the same visibility; each derivation decision's visibility manifest records the exclusion under `omitted_reason: evaluator_only_artifact`. Nine stored `mapping_kind` values are reported with a six-category roll-up and a separate sub-count for `recovered_with_different_cutoff`. |
| Evidence | The authors' list of the historical criteria, with a `completeness_attestation`; this list is **not enumerated in the manuscript main text** and is an input dependency. |
| Evaluation | Recovery fraction reported with its denominator and the full category breakdown, plus a separate expert rating of reason quality per criterion on a registered ordinal scale. High recovery with poor reason quality is not acceptance. The fraction is reported in the `independent` and `assisted` views (design §8.6); a statement that the framework derived the criteria rests on the `independent` view. |
| Records | R4, R1, R7. |
| Acceptance condition | The derived count is whatever the evidence supports; the comparison reports how many historical criteria were recovered, merged, split, removed for lack of support, or not recovered, each with ids and reasons. The authors register what "most" means before evaluation; this document proposes no number. |
| Status | **unestablished as worded.** "Refined toward the final 11" asserts both a target count and a convergence that the design forbids: the count follows the evidence, and the historical list is firewalled from derivation so it cannot be converged upon. |
| Truthful alternative | "Through successive evidence, critique, and expert-review cycles the rule set was refined to the N criteria that the evidence supported and the experts confirmed. A separate comparison against the originally reported criteria records which were recovered with evidence-linked rationale, which were merged or split, and which were not supported; that comparison is provided in Supplementary [R4]." |

### Paragraph 2 — application, tools, and the closed loop

**C2.1 "The resulting CQA rule set is then applied to prioritize candidate compounds."**

| Field | Content |
|---|---|
| Capability | C11 Per-Candidate Assessor applies a confirmed `rules@v` to each candidate against a frozen evidence snapshot, producing one assessment record per candidate × attribute version × rule version, each with a structured Reason record. C12 Leaderboard Service publishes the task-scoped snapshot. The assessor executes rules it never authors. |
| Evidence | Admitted claims per criterion, with `value_kind` and provenance; `missing` and `inapplicable` are distinct from `fail` by the four-state table (design §4.10). |
| Evaluation | Scenario S3 (tool-contract correctness across valid, invalid, timeout, permanent-error, empty results) and the reporting tuple (admitted count, precision, coverage, abstention by reason, guard rates, budget). |
| Records | R2, R3. |
| Acceptance condition | Every candidate entering a round leaves it with a state and a per-criterion row; no candidate is dropped; precision is never reported without coverage and abstention. |
| Status | **planned** |

**C2.2 "…after which the agents can invoke the original CDES pipeline, as well as other task-specific computational tools where appropriate, for further quantitative screening and verification."**

| Field | Content |
|---|---|
| Capability | C13 capability-based resolution by `(capability, question_kind, required_value_kind)`. CDES is one optional `interaction_estimate` provider (design §16). Absence is first-class: provider not registered (`not_configured`), affected cells `unknown_missing` with an `absence_reason` and a `required_inputs_manifest`, snapshot disclosure `interaction_estimate_provider: none`, and candidates `provisional` or `unassessed` — never `rejected` for want of a prediction. |
| Evidence | Tool results with the thirteen-field provenance block (tool and implementation version, data version, parameters hash, invocation id). Prerequisites before any criterion may depend on CDES: training-set provenance and licence, the train/test split, an overlap check against the reference candidate and the five targets, calibration data, and a stated threshold rationale. |
| Evaluation | Contract tests (echo, error recovery, two-step dependency, iteration cap, idempotency, provenance); an agreement check against curated measurements recorded before any criterion depends on CDES alone. |
| Records | R6, R2, R9. |
| Acceptance condition | If CDES ran: actual requests, versions, outputs, failures, and their use in subsequent decisions are retained. If it did not run: the absence record and the per-dimension `tool_coverage` block are published. |
| Status | **planned**, and conditional. The package contains no CDES code, checkpoint, or screening output, so a run today would record its absence. |
| Wording not yet usable | "the agents can invoke the original CDES pipeline" in a context implying it was invoked. |
| Truthful alternative | "Where a compatible numerical backend was available the agents invoked it and received its outputs as structured feedback; for this analysis no interaction-prediction backend was available, and the affected criteria are recorded as unknown rather than failed (Supplementary [R6])." |

**C2.3 "Importantly, the LLM agents do not replace the underlying computational models: they determine which evidence, rules, candidates, and alternative configurations should be examined, whereas CDES and the corresponding computational tools execute the numerical evaluation."**

| Field | Content |
|---|---|
| Capability | Structurally enforced by five mechanisms (design §7.7): `outcome` and `verification_status` live in different records and the broker cannot write the second; `claim_strength_ceiling` forbids storing a prediction as a measurement; the assessor compares the criterion's required value kind against the record's `value_kind` and a mismatch yields `unknown`; every leaderboard cell renders its value kind and provenance; `human_scientific_approval` is writable only by C18. |
| Evidence | `evidence_kind` and `determination_basis` on every value; an LLM confidence statement is never a reliability estimate. |
| Evaluation | Scenario S3; the unsupported-claim rate as a registered guard metric. |
| Records | R2 (value kinds per cell), R6, R3 (coverage of measured versus predicted). |
| Acceptance condition | No criterion verdict rests on a model self-report; every numerical value carries its producing tool and version. |
| Status | **current** (design) |

**C2.4 "Their outputs — including target/CQA scores, rule violations, candidate exclusions, and ranking changes — are returned to the agents as structured feedback."**

| Field | Content |
|---|---|
| Capability | C13 returns a typed `tool_observation` into the next reasoning step after output-schema validation, with a truncation record; a rejected malformed payload is itself fed back as an error observation. Rule violations and exclusions are assessment verdicts (C11); ranking changes are change records with a `cause` (C12). |
| Evidence | The `provider_path` recorded on each exchange, because the inspected reference had one provider path that dispatched tool calls without returning results to the model. |
| Evaluation | The two-step dependency and error-recovery contract tests; a conformance run through each adapter. |
| Records | R6, R2, R3 (change records), R9. |
| Acceptance condition | For each cited tool result there is a journal event showing it entering a later step, and the capability record for the adapter used says `returns_tool_results_to_model: yes`. |
| Status | **planned** |

**C2.5 "The agents use these results to identify unsupported exclusions, boundary cases, failed rules, and evidence conflicts, which can trigger another round of rule revision and human review."**

| Field | Content |
|---|---|
| Capability | C8 Open-Question Register. A continuation trigger must carry a `referent` (a ledger claim, tool result, criterion, or candidate exclusion), a non-empty `expected_decision_change`, and an untried method within budget. Five adaptive trigger classes only: new external evidence, unresolved conflict, consequential missing measurement, questionable exclusion, decision-relevant computation; a person's `human_request` round is a sixth, non-adaptive class, barred from evaluation-arm and prespecified runs. Self-reported low confidence and agent disagreement without a referent are **not** triggers. |
| Evidence | The `questionable_exclusion` trigger is defined against the weak-exclusion invariant: a hard-rule failure resting on a single low-independence source or on `analogous` scope. |
| Evaluation | The Round Progress Record (design §13.4) scores each round transition `progress` / `non_progress` / `unresolved`; two consecutive `non_progress` verdicts stop the adaptive arm regardless of budget. Policy arms P0, P0-noreview, P1, P2, P2-cap, and two P0+ variants test whether continuation buys anything at matched budget. |
| Records | R9 (open questions, round records, termination reasons), R1, R7. |
| Acceptance condition | Every additional round names the open question that justified it and the decision it expected to change; rounds that produced no new admitted evidence, resolved conflict, or changed decision are recorded as non-progress. |
| Status | **planned** |
| Wording not yet usable | Nothing in this sentence overclaims, provided "can trigger" is kept conditional and rounds are not presented as evidence of thoroughness. |

**C2.6 "This creates an auditable closed loop of evidence synthesis, rule evolution, candidate prioritization, computational validation, and expert confirmation."**

| Field | Content |
|---|---|
| Capability | C1 Event Journal as the sole source of truth, with projections for progress, timeline, and difference views; C16 Reuse and Staleness Service for what must rerun after an edit; C2 State Registry so no presentation layer can relabel a state (the inspected reference mapped an unresolved outcome to a label implying it had been sent onward). |
| Evidence | Append-only events with `seq`, `parent_seq`, `cause_seq`; content-addressed artifacts; change records linking each material change to its cause. |
| Evaluation | Scenario S7 (stop/resume fidelity: resumed state equals the pre-interruption projection replayed from the sequence number) and S8. |
| Records | R9, R3, R1, R7. |
| Acceptance condition | A reader can open any round and follow evidence → criterion version → candidate verdict → leaderboard position, and can answer: what changed, which evidence caused it, who approved it, which results became stale, why the run continued or stopped. |
| Status | **current** (design) / **planned** (as a claim about records) |
| Wording not yet usable | "computational validation" as a synonym for a successful tool call. |
| Truthful alternative | "…an auditable loop of evidence synthesis, rule evolution, candidate prioritization, numerical evaluation where a backend was available, and expert confirmation. A successful tool call is recorded as a computed result, not as validation of the underlying claim." |

### Paragraph 3 — sensitivity and the prioritization claim

**C3.1 "We further used this framework to evaluate the sensitivity of the resulting screening procedure."**

| Field | Content |
|---|---|
| Capability | C19 Evaluation and Promotion Authority: the Evaluation Protocol Manifest is registered and hashed before any arm runs, and a run without a `protocol_id` is exploratory and structurally unusable as evidence. |
| Evidence | A frozen evidence snapshot (`evs_`) so configuration effects are not confounded with new data. |
| Evaluation | This claim *is* the evaluation; what it needs is the manifest and the registered ranges. |
| Records | R5, R8. |
| Acceptance condition | A manifest exists, registered before the sensitivity runs, naming the configurations, the snapshot, the tool manifest, the metrics, and the analysis plan. |
| Status | **planned** |

**C3.2 "Selected target and CQA thresholds were systematically varied within prespecified biologically plausible ranges, and the computational screening was rerun under each configuration."**

| Field | Content |
|---|---|
| Capability | C19 preregistration events (two stages: policy before derivation, criterion version on expert approval); C10 registered constants with `cutoff_basis` and a `sensitivity_tested` field; C16 rerun machinery so each configuration is a recorded run against the same snapshot. |
| Evidence | Each range needs a biological justification and sources, supplied by experts; the design proposes no ranges and no thresholds. |
| Evaluation | All configurations retained with equal prominence, including those that do not favour the reference candidate. Ranges chosen after inspecting outcomes are labelled `exploratory` everywhere they appear. |
| Records | R5 (preregistration with hashes; per-configuration results), R3 (one snapshot per configuration), R9. |
| Acceptance condition | Every range has a timestamped registration *preceding* the corresponding run, with its justification and sources; no configuration added later is described as prespecified. |
| Status | **planned**; the claims table records that this was not performed. |
| Wording not yet usable | "prespecified" unless the registration timestamp precedes the run. |
| Truthful alternative | "Selected target and criterion thresholds were varied within ranges registered in advance (Supplementary [R5], with registration timestamps), and the screening was rerun under each configuration; configurations examined after inspecting results are labelled exploratory." |

**C3.3 "Surufatinib remains the top-prioritized compound under the original prespecified configuration."**

| Field | Content |
|---|---|
| Capability | C11, C12, and the Case Acceptance Register (design §13.6). The register names the decisive criteria to be reported and the recording rule for every outcome; it deliberately does **not** pre-write an expected state for the reference candidate, because registering the expected answer would write the conclusion into the protocol. Surufatinib is recorded once as `is_reference_outcome: true` in the case configuration, and criterion text is scanned for its identifiers and aliases so the disclosure cannot leak into criterion definitions or reasons. |
| Evidence | Per-criterion evidence for this compound as for every other, with the same scrutiny (the `candidate_symmetric_scrutiny` critique check is mandatory). An `outcome_dependence_report` (leave-one-out over hard rules: how many would change this candidate's verdict if removed, without tuning) accompanies every snapshot. |
| Evaluation | The admission check under the prespecified baseline, then the registered sensitivity configurations. Reference-outcome selection frequency is excluded from any strategy-promotion metric and reported descriptively only. |
| Records | R3, R2, R5, and the outcome dependence report. |
| Acceptance condition | The observed state is reported with its decisive criteria and with any criteria whose verdicts were `unknown`, naming the cause (absent evidence, tool gap, or an excluding criterion). The baseline is never adjusted to produce admission. |
| Status | **planned** as a question; **unestablished** as a result. This is the intended outcome of the case, not an observation. |
| Wording not yet usable | "remains the top-prioritized compound"; also "top-prioritized" if the procedure applied was a hard-rule funnel. |
| Truthful alternative, hard-rule procedure | "Under the prespecified configuration (rule set version N, evidence snapshot K) surufatinib was the only compound passing all applicable hard criteria; N′ compounds remained provisional because one or more criteria could not be evaluated (Supplementary [R2], [R3])." |
| Truthful alternative, scored procedure | "Under the prespecified configuration and the registered ordering method, surufatinib ranked first among the assessed compounds; coverage and abstention are reported alongside the ranking." |
| If not admitted | "Under the prespecified configuration surufatinib was [state]; the criteria it failed or for which evidence was unavailable are listed in Supplementary [R2], and the evidence that would resolve them is identified. We therefore do not claim that the framework reconstructs the original prioritization." |

**C3.4 "…whereas sufficiently large changes to several key criteria alter the ordering of competing candidates."**

| Field | Content |
|---|---|
| Capability | C12 change records with before/after values and a `cause`; rank-change explanations naming the criterion change record; snapshots preserved per configuration. |
| Evidence | The same frozen snapshot across configurations, so ordering changes are attributable to the configuration and not to new data. |
| Evaluation | Comparative snapshots across the registered ranges; configurations that reorder candidates are reported with the same prominence as those that do not. |
| Records | R3, R5. |
| Acceptance condition | For each configuration, the snapshot and its change records exist; "several key criteria" is replaced by the named criteria and the observed magnitude of change. |
| Status | **planned** |
| Truthful alternative | "Changes of magnitude [range] to criteria [ids] altered the ordering of competing candidates; the affected configurations and their snapshots are provided in Supplementary [R5]." |

**C3.5 "We therefore now explicitly characterize the final CDES-based prioritization as conditional on the adopted rule set and parameter configuration, rather than as a parameter-invariant ranking."**

| Field | Content |
|---|---|
| Capability | Every snapshot is bound to `task_context_id`, `rules@v`, `strat@v`, evidence snapshot, cutoff, ordering method, and result kind (C12), so conditionality is a property of the record rather than a caveat in prose. `task_context_id` is mandatory on every row, which makes a cross-objective universal ranking impossible by construction. |
| Evidence | The sensitivity results themselves. |
| Evaluation | Not applicable; this is a wording commitment. |
| Records | R3, R5. |
| Acceptance condition | The manuscript states the rule-set version, evidence cutoff, ordering method, and result kind alongside the prioritization. |
| Status | **current** as an intention; the specific conditionality statement is **planned** because it must name the configurations actually examined. Note that "CDES-based" is inaccurate under the current design unless that backend ran. |
| Truthful alternative | "We characterize this prioritization as conditional on the adopted rule set (version N), evidence cutoff, and ordering method, and we report the configurations under which the ordering changes." |

**C3.6 "The revised manuscript additionally provides the evidence and rule-evolution records for the five TME targets and the final 11 CQA criteria, together with the corresponding candidate-level decisions and computational outputs."**

| Field | Content |
|---|---|
| Capability | R1–R9 are designed to be exportable: C1 journal exports, C9 claim ledger with exact source locations, C10 version history and change records, C11 assessment and reason records, C12 snapshots, C18 expert decisions, C19 manifest and `claim_scope`. |
| Evidence | The five targets (CSF1R, VEGFR1, VEGFR2, VEGFR3, FGFR1) are case-configuration scope entities with `role: required` and provenance recorded; assay-endpoint and unit conventions for them are an input dependency. |
| Evaluation | The independent completeness check that every published decision has a visibility manifest and every material claim resolves to a source location. |
| Records | All of R1–R9. |
| Acceptance condition | The supplements exist and are linked; the criterion count stated is the count actually produced and confirmed. |
| Status | **planned**; "the final 11 CQA criteria" is **unestablished as worded** for the reason given at C1.7. |
| Truthful alternative | "The revised manuscript provides the evidence and rule-evolution records for the five TME targets and for the N criteria confirmed by expert review, together with the per-compound per-criterion decisions, the numerical outputs obtained, and a comparison against the originally reported criteria." |

## 3. Wording that cannot yet be substantiated

Collected for the authors' convenience. Each item is either a tense problem (the work is designed, not done), a count problem, a procedure-naming problem, or a validation-category problem.

| Draft wording | Problem | Minimum requirement before use |
|---|---|---|
| "we implemented an iterative, tool-augmented multi-agent system" | Completed-work tense; also "iterative" implies multi-round is intrinsic, whereas single-pass is the default mode | An executed run with journal exports (R9) and passing tool-feedback contract tests (R6) |
| "Human experts review these proposed rule updates" | Asserts expert review occurred | `hd_` records referenced by the confirmed rule-set version (R7, R1) |
| "progressively refined toward the final 11 CQA criteria" | Asserts a target count and convergence on a firewalled artifact | Report the count produced and confirmed; attach the recovery comparison (R4) |
| "the agents can invoke the original CDES pipeline" (in a completed context) | Implies the backend ran | Tool records showing invocation, version, outputs, and their use — or the absence record (R6) |
| "computational validation" | Conflates a successful computation with validation of the claim | Rephrase as numerical evaluation; validation requires experimental evidence |
| "prespecified biologically plausible ranges" | "Prespecified" requires a registration preceding the run | Preregistration events with timestamps and hashes (R5) |
| "Surufatinib remains the top-prioritized compound" | Reports an intended outcome as a verified result; also mis-names the procedure if a hard-rule funnel was used | An executed baseline run; the result-kind-appropriate sentence from C3.3 |
| "sufficiently large changes to several key criteria" | Unquantified and unnamed | Named criteria, magnitudes, and per-configuration snapshots (R5, R3) |
| "the final CDES-based prioritization" | Attributes the prioritization to a backend that may not have run | Name the actual procedure and backends used |
| "The revised manuscript additionally provides…" | Depends on supplements that do not exist yet | The supplements, linked and complete |

Two standing cautions, from the package and reaffirmed here. First, surufatinib is an **already-known reference outcome** in the manuscript; the response should state that context rather than presenting the case as blind discovery. Second, a **unique all-pass candidate** under hard rules and the **highest-ranked candidate** under a continuous score are different results; the selection procedure actually applied must determine the wording, and if both are reported the all-pass set is the primary claim with the ranking a secondary ordering of it.

## 4. Records the revised manuscript would attach

| Record | Content | Field it supplies to the rebuttal |
|---|---|---|
| **R1** Confirmed rule-set versions with change history | Attribute and Rule versions; change records with `operation`, `reason_kind`, `source_refs`, `arbitration_outcome`, `human_decision_ref`; registry-invariant findings; rejected proposals retained with `rejection_reason` | C1.3, C1.4, C1.5, C1.7, C3.6 — that rules were treated as revisable hypotheses, challenged, and confirmed |
| **R2** Per-candidate per-criterion assessment and reason records | Verdict, value, `value_kind`, `determination_basis`, claim refs, conflicting claims, uncertainty, applicability evaluation, structured reason, staleness, reuse decision | C2.1, C2.3, C3.3, C3.6 — the per-compound evidence behind every decision |
| **R3** Leaderboard snapshots | Result kind, `all_pass_count`, ordering method, reporting tuple (admitted, precision, coverage, abstention by reason, guard rates, budget), tool coverage per dimension, `interaction_estimate_provider`, change records with causes, independence summary | C2.1, C3.3, C3.4, C3.5 — the prioritization, its conditionality, and what changed |
| **R4** Recovery-comparison summary | Per historical item: `mapping_kind` (nine values), `rule_role_match`, `match_basis`, agreement evidence, rationale refs, reason text, judged-by; per-snapshot counts by item and by decision impact; expert reason-quality ratings | C1.7, C3.6 — how the derived criteria relate to those originally reported |
| **R5** Preregistration, Case Acceptance Register, sensitivity results | Two-stage preregistration events with hashes and timestamps; decisive criteria to report; recording rules; registered ranges with justifications; per-configuration results; prespecified versus exploratory labels; outcome dependence report | C3.1, C3.2, C3.3, C3.4 — that the sensitivity protocol preceded the results |
| **R6** Tool and adapter records | Tool contracts and versions, invocations with provenance, results with `outcome` and `record_state`, absence records with `absence_reason` and `required_inputs_manifest`, model adapter capability records, contract-test run ids, `run_degradation[]` | C1.2, C2.2, C2.4 — what computed what, and what did not run |
| **R7** Expert decision records | Actor identity and `identity_basis`, declared scope of expertise, subject and version, decision, edits with before/after, reason, sources consulted, confidence qualifier, downstream invalidation | C1.6, C1.5 (escalations), C3.6 — that human scientific approval occurred and by whom |
| **R8** Evaluation protocol manifest and claim scope | Protocol id, task set, evidence snapshot and hash, cutoff, tool manifest, evaluator kind and blinding, metrics, budget caps, seeds, repeats, analysis plan, pools; `claim_scope {establishes, does_not_establish, label_dependency}` per report | C3.1, and the honesty boundary on every quantitative statement |
| **R9** Journal exports | Events with `seq`, actor, ids, `parent_seq`, `cause_seq`, state transitions, input versions, question, summary, budget, artifact links; open questions with referents and expected decision changes; termination reasons | C1.2, C2.5, C2.6 — the auditable loop and the reason each round continued or stopped |

## 5. Residual risks to the rebuttal

1. **Input dependencies.** The authors' list of the originally reported criteria (with a completeness attestation) and the identity list of the 3,171-compound library are not in the package. Without the first, the recovery comparison cannot be scored and "most of the original criteria" cannot be quantified; without the second, the case cannot run at the stated scale.
2. **Coverage, not quality, limits the no-backend route.** Retrieval yields values for well-studied compound–target pairs and nothing for most of a large library, so `unknown_missing` is expected to be the most common verdict and the recommended set may be small or empty. That is a correct outcome under precision-first admission and must be reported as coverage, not hidden.
3. **Expert availability.** The trigger table makes expert decisions a precondition for every hard exclusion and for publishing a recommended candidate. Throughput depends on expert time, and the claim at C1.6 fails without recorded decisions.
4. **Procedure naming.** If the applied procedure is a hard-rule funnel, the sentence must claim uniqueness among all-pass candidates and report how many candidates were unassessed; if it is a scored ordering, it must claim rank and report coverage. Choosing the stronger-sounding phrasing after seeing the result would be the same error the rebuttal is answering.
5. **Disclosure.** The case is a known-outcome reconstruction. Presenting it as independent discovery, or omitting that surufatinib was the manuscript's reported outcome, would misstate the design.

**Sources:** `03_Provided_Rebuttal_Draft_EN.md` (original paragraphs and claims table); `01_Concept_Overview_EN.md` ("Testing the nomination"); `optimized_design.md` §0, §8.6, §13.6, §16, §17; `agent_reports/evidence_and_policy.md` §3.2, §6.3, §8 and cross-review; `agent_reports/evaluation_and_improvement.md` Findings 8–9 and cross-review; `agent_reports/tools_and_data.md` §2, §4, Finding 8.
