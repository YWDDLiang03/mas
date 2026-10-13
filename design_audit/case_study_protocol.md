# Case Study Protocol: Primary Acceptance Case

Coordinating agent, 12 October 2026. Design phase only. This document defines the protocol for the first acceptance case: the objective and target configuration, the candidate comparison scope, how criteria are derived and reviewed, the baseline and alternative configurations, the two acceptance targets, the sensitivity protocol, and the rules by which unsupported or contrary results are recorded.

**This protocol is not executed here.** No screening was run, no criterion was derived, no threshold is proposed, no candidate was assessed, and no ranking or sensitivity outcome exists. Every outcome field below is a placeholder that only an executed run may fill. Component ids (C1–C20), record kinds, state vocabularies, and the R1–R9 record index follow `optimized_design.md` Section 0 and Section 17.

## 1. Purpose and the two acceptance targets

The case exercises the whole architecture on a known-outcome reconstruction and produces the records the manuscript rebuttal needs (`rebuttal_alignment.md`). Two targets define acceptance:

- **Target A, criterion recovery.** The system derives a criterion set from the objective and the evidence, and a separate comparison component reports how that set relates to the criteria originally reported in the manuscript: recovered with an evidence-linked rationale, recovered at a different cutoff or with narrower applicability, merged, split, removed for lack of support, or not recovered. The target is that most of the originally reported criteria are recovered with evidence-linked rationales of acceptable quality. **The threshold for "most" is registered by the authors before evaluation; this protocol proposes no number.** The count is reported in two views, `independent` and `assisted` (§4.5); the authors register which view the threshold applies to.
- **Target B, reference-candidate admission.** Surufatinib is admitted onto the task-scoped leaderboard for the stated objective and target configuration, with a per-criterion reason for it and for every other assessed compound. Admission means a candidate state of `recommended`, or `provisional` where a criterion could not be evaluated, under the prespecified baseline configuration.

Both targets are **intended outcomes**, registered in the Case Acceptance Register. Neither is an expectation written into the protocol as a pass condition for the reference candidate: the register names the decisive criteria *to be reported* and the recording rule for every possible outcome, and deliberately omits any expected state (design §13.6). A configuration that does not admit the reference candidate, or a criterion that is not recovered, is a recorded finding with consequences for the rebuttal wording, never a reason to adjust the baseline.

## 2. Objective and target configuration

### 2.1 Case configuration record (filled at interface level)

| Field | Value for this case | Source |
|---|---|---|
| `mode` | `conditional` | the authors supply targets and the candidate universe |
| `objective_text` | a reconstruction of the manuscript's objective assembled from dispersed phrases in its main text (`provenance_form: reconstructed_pending_author_confirmation`; the verbatim sentence or sentences with locations are an author-confirmation input, see §2.3): a single orally administered agent that concurrently engages the stated tumour-microenvironment targets, with a pharmacological profile suitable for clinical development | manuscript; never rewritten by the system |
| `scope_entities[]` | five targets: CSF1R, VEGFR1, VEGFR2, VEGFR3, FGFR1, each `role: required`, `questioned: allowed`, provenance = manuscript | manuscript |
| `candidate_universe` | `{kind: named_library, source: "FDA-approved or Phase III clinical-stage compounds", size_if_known: 3171, access_path: INPUT DEPENDENCY, as_of: INPUT DEPENDENCY}` | manuscript states the size; the identity list is not in the package |
| `historical_stage_artifacts[]` | the 140-compound multi-target-binder stage produced by the manuscript's predictor, marked comparison-only | manuscript |
| `seed_candidates[]` | `{candidate_ref: surufatinib, reason_supplied: "manuscript-reported outcome", is_reference_outcome: true}` | manuscript |
| `constraints[]` | oral administration (`hardness: hard`, provenance manuscript); evidence cutoff date (`hardness: hard`, set by the authors) | manuscript and operator |
| `evidence_cutoff_at` | registered date; frozen into the evidence snapshot | operator |
| `tool_availability_snapshot` | the providers actually resolvable at run start; by default no interaction-prediction backend | run start |
| `historical_criteria_intake` | the authors' list of the originally reported criteria, `visibility: evaluator_only` (§5.1) | INPUT DEPENDENCY |
| `registered_constants[]` | includes the coverage floor for `recommended`, the duplicate-overlap share, the weak-exclusion universe share, breaker thresholds, the enumeration saturation count, the merge verdict-agreement share, the sweep tool-failure share; values are expert or operator decisions | experts and operator |
| `evaluation_scope` | `{comparison_basis: both, abstention_allowed: true, ordering_method_ref: registered}` with the all-pass set as the primary claim | protocol |
| `derivation_configuration` | `reference_disclosed` (see §5.2) | protocol |
| `human_review_requirements` | expert decision required for every hard exclusion entering `confirmed`, every `expert_set` cutoff, and every `recommended` publication | protocol |
| `budget_envelope` | screening rounds, review exchanges, self-correction turns, tool retries, evidence requests, tokens, tool calls, wall clock, human-review minutes | operator |

### 2.2 Three CQA dimensions

The manuscript organises its criteria into three dimensions, which the adapter supplies as the organising keys for criterion templates and for the per-dimension coverage report: **oral bioavailability**, **metabolic stability**, and **toxicological safety**. Target engagement across the five scope entities is handled as a fourth evidence dimension, **target coverage**, because it is the dimension the candidate universe was originally filtered on. The four dimensions remain separate ledgers: a value that is strong evidence under one is often irrelevant under another.

This protocol does not enumerate the individual criteria within those dimensions. They are an input dependency (§5.1) and, for derivation, they are firewalled.

### 2.3 Input dependencies

| Input | Owner | Consequence if absent |
|---|---|---|
| Identity list or access path for the 3,171-compound library | authors | The case cannot run at the stated scale; a smaller enumerated subset would have to be registered as the candidate universe and the scope stated plainly |
| The authors' list of originally reported criteria, with definitions, directions, units, any thresholds, and a `completeness_attestation` | authors | Target A cannot be scored; "most of the original criteria" cannot be quantified. If the attestation is `partial`, the recovery fraction must be restated as a fraction of a partial list |
| Assay-endpoint and unit conventions for the five targets (assay type, species, isoform, free versus total concentration) | domain experts | Target-coverage criteria cannot be made comparable across sources; affected criteria stay `proposed` with `non_evaluable_reason: unit_unresolved` |
| The 140-binder stage membership | authors | The comparison-only stage artifact cannot be reconciled with the derived assessment |
| Coverage floor and every cutoff basis | domain experts | Admission cannot reach `recommended`; candidates remain `provisional` |
| Interaction-prediction backend, if it is to be used, with training-data provenance, split, overlap check, and calibration | authors | The run records its absence and reports coverage (§4.3) |
| List of case-source documents: the manuscript, its supplement, preprints, documents quoting its criteria list | authors | The manuscript could be retrieved during derivation, and every recovered criterion would be open to the objection that it was read rather than derived |
| `historical_list_exposure` declarations from every confirming expert and every template author | authors, experts | Exposure is treated as `exposed`; all recovery is reported in the `assisted` view only |
| External calibration cases (optional): published prioritization studies on other objectives, with their criteria lists | domain experts | The derivation strategy runs uncalibrated; recovery rests on the default enumeration procedure |

**Added after independent review.** Two further items are blocking inputs, not advisory: (1) the exact `objective_text` as it appears in the manuscript, with location, confirmed by the authors (the §2.1 row is a reconstruction until then); (2) the value of the coverage floor constant `const_coverage_floor`, because until an expert registers it no candidate can reach `recommended`, so Target B is blocked on this input and not merely dependent on it.

### 2.4 Inputs at a glance and their visibility

Visibility values follow design §2.2: `agent_visible` may enter agent context; `evaluator_only` is read only by the comparison function, by the review queue on comparison-adjudication items after the criteria are confirmed, and through the evaluator-role recovery panel, each read making the reader `exposed`; `control_only` is read mechanically by core components.

| Input | Value for this case | Provided by | Visibility |
|---|---|---|---|
| Objective | reconstruction pending author confirmation (§2.1) | authors | `agent_visible` |
| Targets | the five scope entities, all required; agents may question a target but not remove it | authors | `agent_visible` |
| Candidate universe | the 3,171-compound library; identity list is an input dependency | authors | `agent_visible` |
| Reference outcome | surufatinib, `is_reference_outcome: true`, assessed under the symmetry obligation (§6.4) | authors | `agent_visible` |
| Constraints | oral administration (hard); evidence cutoff date | authors, operator | `agent_visible` |
| Tool availability | providers resolvable at run start; no interaction-prediction backend by default | system | `agent_visible` |
| CQA dimensions | the three of §2.2 plus target coverage | adapter | adapter content, agent-visible |
| Supplied evidence files (optional) | through submission intake | authors | `agent_visible` once admitted |
| Earlier 140-binder stage | comparison only | authors | `evaluator_only` |
| Original criteria list | the comparison reference for Target A | authors | `evaluator_only` |
| Case-source documents | blocked from retrieval (§4.5) | authors | `control_only` |
| Registered constants | coverage floor and the other constants of §2.1 | experts, operator | `control_only` |
| Budget envelope | rounds, tokens, tool calls, wall clock, review minutes | operator | `control_only` |
| Calibration cases (optional) | external published studies with their criteria lists | experts | `control_only`, read by C19 |
| Exposure declarations | on criterion-affecting `hd_` records and on templates | experts, authors | recorded on review records |
| Host platform and operator surface | the deployment profile chosen by the operator (design §14.1); the host is recorded on the Run Binding and the surface on each command-caused event | operator | `control_only`; never in agent context |
| Run group | the group holding the case's tasks and runs (design §6.9); calibration cases sit in other groups | operator | `control_only` |

Not inputs: the criteria, their cutoffs, and any ranking; the system produces them. The minimum to start any case is an objective, a mode, an evaluation scope, and either a candidate universe or a seed set (design §4.4); every other field may be `undetermined`, which allows the run but blocks `recommended`.

## 3. Candidate comparison scope

### 3.1 Universe and stages

The candidate universe is the full library. The manuscript's prior filtering stage (140 compounds predicted to bind all five targets above a stated probability) is recorded as a `historical_stage_artifact` and used for **comparison only**: it is not the universe, and it is not an admission criterion. Reporting both the full-universe assessment and the overlap with that historical stage is informative; treating the 140 as the candidate set would import the prior model's decisions as premises.

Every compound in the universe is assessed on every confirmed criterion in a full sweep (design §6.6). A run ends `completed` when the sweep is complete, with missing values recorded as `unknown_missing`, and ends `unresolved` only if the sweep could not finish (design §6.7).

### 3.2 Identity resolution

Before any evidence is attached, every candidate passes the core identity service driven by adapter schemes (design §8.2): identifiers with scheme authority and `as_of`, aliases typed as code, brand, synonym, salt form, or transliteration, and an `identity_link_basis`. Rules:

- A claim may ground an assessment only on `exact_identifier_match` or `authority_crosswalk`.
- `name_match_ambiguous` routes to the human review queue and the claim stays `pending`.
- `unresolved` yields a `not_assessed` row, visible in the universe count.
- Salt and formulation differences are aliases, not separate candidates, unless an attribute's applicability depends on them.
- Merging two rows is human-confirmed with a change record.

This step is not optional bookkeeping: the package's own inventory records that a supplied response table contained no match for the reference candidate's aliases, which is exactly an identity failure rather than an absence of effect.

### 3.3 Expected coverage limits

Without an interaction-prediction backend, target-coverage values come from curated bioactivity records and expert-curated interaction tables, which exist for well-studied compound–target pairs and not for most of a large library. The property dimensions draw on computed descriptors, published measurements retrieved through literature tools, and pinned-version property predictors whose outputs are `model_prediction` with `claim_strength_ceiling: predicted`.

The protocol therefore expects:

- `unknown_missing` to be the most common per-criterion verdict across the universe;
- a large `provisional` and `unassessed` tier;
- a small, possibly empty, `recommended` set.

This is a correct outcome under precision-first admission, not a failure. Every snapshot carries a per-dimension `tool_coverage` block (candidates with a measured value, with a prediction only, with nothing, and the provider behind each) and the disclosure `interaction_estimate_provider: none` where applicable, so no later narrative can imply a backend ran.

## 4. Criteria derivation and review protocol

### 4.1 Stages and roles

| Stage | Owner | Output | Review |
|---|---|---|---|
| D0 Bind and preregister policy | C15, C19 | Run Binding; stage-1 preregistration event with hash | evaluator records stage 1 |
| D1 Normalize | C4 | task context with unknowns and missing-information requests | blocking unknowns queue to C18 |
| D2 Plan | C5, C6 | plan with per-dimension retrieval steps, owners, budgets, completion predicates | plan inspectable, not gated |
| D3 Retrieve | Evidence Retriever via C13, C9 | sources, claims with exact locations, independence groups, search coverage records, visibility manifests | none; shortfalls reported |
| D4 Propose | Proposer (C7) | Attribute and Rule proposals with `considered_and_rejected[]`, `expected_change`, `falsification_test` | — |
| D5 Validate and critique | Deterministic Validator, Blind Critic (C7), C10 invariants | typed findings; critique with mandatory checks | — |
| D6 Adjudicate | Deterministic Adjudicator; escalation only on persistent disagreement about an identified referent | adjudication artifact with dissent | — |
| D7 Confirm | C18, C10 | `hd_` decisions; `rules@v1` confirmed with its admission-predicate hash; stage-2 preregistration | expert decisions required per the trigger table; evaluator records stage 2 |

Counter-evidence is an obligation of the Retriever plus deterministic verification, not a separate persona: the critique must carry a `counter_evidence_considered` check with a verdict, and `not_searched` disqualifies any reason that depends on it for a hard exclusion.

### 4.2 Reference-disclosed derivation with an alias scan

The reference candidate's identity is disclosed once, in the case configuration. Derivation runs `reference_disclosed` rather than `reference_blind`, because the objective text and the five-target configuration already narrow the space toward the known compound, so a claim of blindness would be false. The protections are mechanical instead:

1. **Alias scan.** Every criterion definition, rationale, cutoff, and reason text is scanned for the reference candidate's identifiers and aliases. A hit outside an explicit comparison artifact fails the entry.
2. **Candidate-symmetric scrutiny.** A mandatory critique check requires the same test to be applied to the reference candidate and its competitors; a proposal cannot reach `completed` without a verdict on it.
3. **Outcome dependence report.** A leave-one-out report accompanies every snapshot: how many hard rules would change the reference candidate's verdict if each were removed, computed without tuning.
4. **`reference_blind` as a sensitivity arm.** A registered configuration in which claims whose only subject is the reference candidate are excluded from the derivation context is run as one sensitivity arm and reported alongside the baseline. It is not the acceptance gate.

### 4.3 Visibility manifest and invariants

Every derivation decision publishes a visibility manifest built from the **unfiltered** source catalog, listing included claim ids and excluded ones with typed reasons (including `evaluator_only_artifact` for the historical criteria). A decision publishes only if its manifest exists and every conflicting-polarity claim for the attributes involved is either included or individually excluded with a reason. The conflicting-to-supporting ratio is reported.

The registry invariants run on every proposal and produce typed critiques, never silent corrections: arbitrary cutoff, duplicate criteria, unit consistency, weak exclusion, reference-candidate scan, and the rule-reversal test before promotion. Bounded repair applies: a fixed number of revisions, then `unresolved`.

### 4.4 Two-stage preregistration

| Stage | When | Registers |
|---|---|---|
| Stage 1, policy | before any derivation | the stage-1 list of design §13.6: rule semantics, constants hash with the coverage floor, ordering method, evidence tiers, cutoff and snapshot rule, universe id, tool manifest, derivation configuration, `strat@v` with the consolidation rule, sweep ordering policy and seed, the threshold for "most", and the optional budget-extension rule |
| Stage 2, criterion version | on expert confirmation, before any candidate assessment | `rules@v` with its `evidence_admission_predicate_hash`, the `evs_` id, and the concrete sweep order (design §13.6) |

Both stages are journal events carrying hashes and timestamps, recorded by the evaluator; a prespecified run waits in `waiting_human` until each is recorded (design §13.6). The two-stage split exists because criteria are an output: the policy can be fixed in advance, the criterion identities cannot.

### 4.5 Leakage paths outside the agents

The firewall in §5.1 keeps the historical list away from derivation agents. Eight other paths could carry it in; each is closed and recorded:

| Path | Control | Record |
|---|---|---|
| Retrieval finds the manuscript, its supplement, a preprint, or a document quoting its criteria list | registered `case_source_documents[]`, matched on identifiers, title, and author list; excluded from every derivation catalog | `omitted_reason: case_source_document` in each visibility manifest; retrieval hits logged |
| A confirming expert knows the historical list | `historical_list_exposure` declared on every criterion-affecting `hd_` and checked against the intake access log (a logged read makes the reader `exposed`); the review queue shows the list only for comparison-adjudication items after `rules@v` is confirmed; where available, criteria are confirmed by an expert who has not seen the list, and exposed authors answer specific review-queue questions instead | items authored or confirmed by an exposed or undeclared actor count in the `assisted` view |
| An adapter criterion template was written from the historical list | `historical_list_exposure` declared on every template; templates enter as `proposed` with empty cutoffs | any derived item whose `derived_from` is an exposed template counts in the `assisted` view |
| Global shaping artifacts (objective text, dimension list, consolidation rule and its constants, derivation strategy) written by people who know the list | exposure declared; each artifact is verbatim public text cited by location or passes the criterion-content scan run by the comparison component (design §8.6) | a scan `match` moves every item the artifact shaped to the `assisted` view; the summary states that this channel carries a weaker guarantee |
| Feedback from the primary case into memory or strategy selection | acceptance-bearing runs use `memory_mode: cold`, or `frozen` over a snapshot taken before any intake access; `final`-pool runs never feed lineage metrics; calibration cases are screened; the replay view excludes the `final` pool (design §4.20, §8.3, §10.2, §13.7) | memory mode in the Run Binding; lineage exclusion on the strategy version; calibration screening record |
| Skills and lessons recalled from memory (approved items from any group, a frozen snapshot, Reflector drafts) | every memory item carries `historical_list_exposure`; the Reflector never reads evaluator-only content or recovery-mapping decisions and inherits the exposure of what it read; items recallable in the case pass the criterion-content scan; acceptance-bearing runs never recall items whose author or approver is exposed or undeclared; a bound snapshot is a global shaping artifact (design §8.6, §10.2, §10.5) | exposure and scan result on each item; `memory.recalled` per step |
| Lessons drafted in other groups (calibration cases among them) that name the manuscript | the identifiers and titles of every registered case-source document are on the content-policy lists of every group (design §10.4) | rejection codes on refused drafts |
| A person's added round or task edit in a run continuation | `author_exposure` on `human_request` questions and task-context versions; they count as authored fields of what they shape (design §4.4, §4.8, §8.6) | exposure on the question and the task version; `assisted` counts |

The `independent` view supports the statement that the system derived the criteria. The `assisted` view supports only the statement that the system produced and evidence-checked the criteria with input from people who knew the original list. Both are reported; neither is hidden when it is small.

## 5. The criterion-recovery target (Target A)

### 5.1 Intake record and firewall

The authors' list of originally reported criteria enters as an intake record in the **case configuration**, not in the Criterion Registry: `intake_id`, `provided_by`, `provided_at`, `provenance_form` ∈ `manuscript_main_text` / `manuscript_supplement` / `author_supplied_list` / `reconstructed_from_code` / `verbal_report`, `verbatim_items[]` (label, definition as given, dimension as given, threshold as given, unit as given, direction as given, notes), `completeness_attestation` ∈ `complete` / `partial` / `unknown`, `ambiguities[]`.

The firewall has three parts: `visibility: evaluator_only` with enumerated readers (the comparison component; the review queue for comparison-adjudication items only, never for criterion-confirmation items; and the evaluator-role recovery comparison panel, `ui_ux_spec.md` §11.1), and every artifact derived from it inherits the same visibility (design §8.6); an access log, so a read by any actor is visible and makes that actor `exposed` from that point (§4.5); and a visibility-manifest entry on every derivation decision recording the exclusion under `omitted_reason: evaluator_only_artifact`. The manifest entry is the mechanical record; the access log corroborates it. Any criterion version produced after a logged read by a derivation actor is labelled `outcome_informed_exploratory` and cannot support an acceptance claim.

### 5.2 Scoring

One recovery comparison record per historical item, plus one per unmatched derived attribute. Nine stored `mapping_kind` values:

`recovered_equivalent` · `recovered_with_narrower_applicability` · `recovered_with_different_cutoff` · `merged_into` · `split_into` · `not_recovered_no_evidence` · `not_recovered_out_of_scope` · `deliberately_removed` · `newly_added_not_in_history`

Each record also carries `rule_role_match` (hard exclusion, preference, exploratory, none), `match_basis` ∈ `definition_and_unit_match` / `definition_match_unit_differs` / `verdict_agreement_on_assessed_candidates` / `expert_judged_equivalent`, agreement evidence (candidates where the historical and derived rules agree, disagree, or cannot be compared), rationale refs, reason text, judged-by (plus an `hd_` reference whenever the basis is `expert_judged_equivalent`), and the derived version's `derivation_configuration`.

Reporting uses a six-category roll-up (recovered, merged, split, removed, added, not recovered) with `recovered_with_different_cutoff` broken out as a separate sub-count, so a cutoff mismatch is never banked as a clean recovery. Removals are split into *unsupported* and *superseded*, because only the first is a finding about the historical criterion's documentation.

### 5.3 Reason quality and two views

Recovery count alone is insufficient. Each derived criterion's rationale is rated by an expert on a registered ordinal scale, and the summary reports both:

- **count view:** how many historical items fall in each mapping kind;
- **decision-impact view:** how many candidate states each historical item's presence or absence changes.

High recovery with poor reason quality is not acceptance. A `not_recovered_no_evidence` item is reported as a statement about the historical criterion's documentation and the searches that failed to support it, not as a system failure.

### 5.4 Route to high recovery without steering

The design raises the chance that most of the original criteria are produced by making derivation thorough and matching fair, not by pointing derivation at the answer:

1. **Same starting point as the authors.** The agents receive the objective, the target configuration, and the three dimensions (§2.2), which the manuscript states publicly. They do not receive the list or its count.
2. **Recall-first enumeration** (design §8.3). Per dimension, every decision-relevant attribute found in standards and guidance documents, in other published prioritization studies, and in candidate evidence is listed before any pruning, until new sources stop adding attributes. Original criteria grounded in the field's standard practice should appear in this list; one that never appears is evidence that it was not grounded in retrievable sources.
3. **Registered consolidation.** Attributes are merged into decision-level criteria by a rule fixed before derivation (same property by different methods; verdict agreement above a registered share), so the derived set reaches a granularity comparable to a curated list without any count target.
4. **Fair matching of similar items.** A derived criterion that matches an original one in definition but differs in cutoff, applicability, or granularity is credited as `recovered_with_different_cutoff`, `recovered_with_narrower_applicability`, `merged_into`, or `split_into`, each counted separately from `recovered_equivalent`; every equivalence judged by an expert carries an `hd_`.
5. **Calibration on other cases** (optional, recommended; design §8.3). The derivation strategy is improved on external calibration cases whose published criteria lists are known, then frozen; the primary case is opened once. This is the only route by which recovery is tuned, and it never touches the eleven.

What the route cannot do is produce an original criterion for which no retrievable source supports a decision-relevant attribute. Such an item is reported as `not_recovered_no_evidence` with the searches that failed, which is a finding about how the criterion was documented.

## 6. The reference-candidate admission target (Target B)

### 6.1 What the register fixes in advance

| Registered before evaluation | Deliberately not registered |
|---|---|
| The baseline configuration: everything registered in the two preregistration stages (design §13.6), the optional budget-extension rule included | Any expected state for the reference candidate |
| The decisive criteria whose verdicts will be reported for the reference candidate and for named comparators | Any threshold chosen to produce a particular outcome |
| The result-type naming rule (§6.3) | — |
| The recording rule for every outcome (§6.2) | — |
| The sensitivity ranges with justifications and sources (§7) | — |

### 6.2 Recording rule for every outcome

Whatever the run produces, the record states: the observed candidate state; the decisive criteria and their verdicts; every criterion whose verdict was `unknown_missing`, `unknown_conflicted`, or `inapplicable`, with the cause (absent evidence, tool gap, unresolved identity, or an excluding criterion); the coverage and abstention figures for the snapshot; and the outcome dependence report. The baseline is never adjusted after seeing the result. A state of `unresolved` arising from budget exhaustion or tool unavailability is neither admission nor non-admission and is reported as unresolved.

### 6.3 Result-type naming

The applied procedure determines the wording, fixed in advance:

- If the procedure is a hard-rule funnel, the claim is about the **all-pass set**: `result_kind: all_pass_set` with `all_pass_count`, and the number of candidates left `provisional` or `unassessed` reported alongside, because "the only compound passing all criteria" means little if most of the universe was never assessed.
- If the procedure is a continuous ordering, the claim is about **rank** under the registered ordering method, reported with coverage and abstention.
- If both are reported (`both_reported`), the all-pass set is the primary claim and the ranking a secondary ordering of it.

### 6.4 Symmetry obligation

The reference candidate receives no additional search effort, no additional tool calls, and no relaxed reason requirements relative to comparators. The `candidate_symmetric_scrutiny` check is the mechanical expression of this, and the per-candidate budget is recorded so asymmetric effort is visible in the cost record.

### 6.5 Route to admission without steering

Admission (§1) means `recommended`, or `provisional` where a criterion could not be evaluated. Only two outcomes remove the reference candidate from admission: a `fail` on a confirmed hard rule backed by admitted evidence (`rejected`), or an identity or tool gap that leaves it `unassessed`. The design addresses each risk with a control that applies equally to every candidate:

| Risk | Control |
|---|---|
| Identity not resolved (code names, brand names, salt forms) | identity service with authority crosswalks; ambiguous matches routed to the review queue, never dropped |
| Missing measurements | `on_missing` is `unknown_no_penalty` or `unknown_blocks_recommendation`; a missing value caps a candidate at `provisional` and never rejects it |
| A hard exclusion resting on weak evidence | weak-exclusion invariant (single independence group, analogous scope, mass rejection on predicted values); expert confirmation of every hard exclusion; `not_searched` counter-evidence disqualifies the reason |
| An arbitrary cutoff | `cutoff_basis` required; `expert_set` requires an `hd_`; registered sensitivity ranges show where each verdict flips |
| A preference treated as an exclusion | `rule_kind` separates `hard_exclusion` from `preference`; preferences change rank, never admission |

The outcome dependence report (§4.2) shows how many hard rules the admission depends on. If the reference candidate fails a confirmed hard rule on admitted evidence, that is the result, recorded under §6.2; the baseline is not adjusted.

## 7. Baseline and alternative configurations; sensitivity protocol

### 7.1 Registration

Each sensitivity configuration is registered before its run with: the criteria and constants varied, the range and its biological justification with sources, the configuration id, and the snapshot it runs against. The evidence snapshot is **frozen and identical** across configurations, so an ordering change is attributable to the configuration and not to new data. The design proposes no ranges and no thresholds; those are expert inputs.

### 7.2 Classes of alternative

| Class | Example of what varies | Justification required |
|---|---|---|
| Threshold variation | a cutoff moved within a registered range | sources supporting the range |
| Applicability variation | a condition narrowed or widened | evidence that the condition is or is not met in the intended setting |
| Unit or endpoint convention | an alternative normalisation | the upstream data dictionary or an expert statement |
| Evidence-tier strictness | requiring a measured rather than a predicted value for a hard rule | the admission-predicate change, which is a policy change requiring expert approval |
| Rule-kind variation | a criterion treated as a preference rather than a hard exclusion | expert judgement on whether the attribute can exclude |
| `reference_blind` derivation | the derivation context excludes claims whose only subject is the reference candidate | §4.2 |

### 7.3 Reporting

All configurations are retained and reported with equal prominence, including those that do not admit the reference candidate and those that reorder competitors. Ranges or configurations chosen after inspecting outcomes are labelled `exploratory` everywhere they appear and may never be described as prespecified. Changes in ordering are reported with the named criteria and the magnitude of change, not as "sufficiently large changes to several key criteria".

## 8. How unsupported or contrary results are recorded

The following templates are the registered recording forms. Bracketed fields are filled only by an executed run; none is filled here.

**Admission outcome.** "Under the prespecified baseline (rule set version [N], evidence snapshot [K], ordering method [M]), surufatinib was [recommended | provisional | unassessed | rejected | unresolved]. Decisive criteria and verdicts: [list]. Criteria with unknown verdicts: [list] (cause: [absent evidence | tool gap | unresolved identity | conflict]). Coverage [c] of applicable hard criteria; [n] candidates remained provisional and [m] unassessed."

**Non-admission.** "Under the prespecified baseline surufatinib was [state]; the criteria it failed or for which evidence was unavailable are [list], and the evidence that would resolve them is [list]. We therefore do not claim that the framework recovered the original prioritization under this configuration."

**Recovery outcome.** "Of the [N] originally reported criteria (completeness attested: [complete | partial | unknown]), [k] were recovered with evidence-linked rationale, of which [j] at a different cutoff and [i] with narrower applicability; [m] were merged, [s] split, [r] removed for lack of support (searches recorded in [R1]), and [u] not recovered. [a] criteria were newly added with no historical counterpart. Expert reason-quality ratings: [distribution]."

**Low recovery.** "The derived criterion set differs from the originally reported set in the ways tabulated in [R4]; we therefore do not claim that the framework reconstructs the original screening rationale, only that it derives an evidence-linked set whose differences are stated."

**Coverage disclosure.** "No interaction-prediction backend was available for this analysis; target-coverage verdicts rest on curated measurements covering [X] of [Y] candidate–target pairs, and the remaining pairs are recorded as unknown rather than failed."

**Sensitivity outcome.** "Across the [p] registered configurations, surufatinib was admitted in [q]; the configurations in which it was not admitted are [list] and the criteria responsible are [list]. Changes of magnitude [range] to criteria [ids] altered the ordering of competing candidates."

**Unresolved run.** "The run terminated `unresolved` with reason [termination_reason]; [n] open questions remain, with their referents and expected decision changes recorded in [R9]. No prioritization is claimed from this run."

Three prohibitions accompany the templates. A result may not be reported without its coverage and abstention figures. An intended outcome may not be written in the past tense. A configuration examined after seeing results may not be relabelled as prespecified.

## 9. Required tools, at interface level

The provider-by-provider research, with primary links, licences, inputs and outputs, and limitations, is in `tools.md`. Per dimension, this protocol requires at least:

| Dimension | Capability required | Value kinds expected | Notes |
|---|---|---|---|
| Identity (precondition for all) | `identity_resolution` | `derived` | Structure normalisation and identifier crosswalk; failure yields `not_assessed`, never `fail` |
| Target coverage | `interaction_evidence_lookup`; optionally `interaction_estimate` | `curated_measurement`, `measured`; `predicted` where only a model is available | Curated and predicted values never merge into one cell; the optional backend is disclosed per snapshot |
| Oral bioavailability | `property_estimate`, `literature_retrieval`, `document_reading` | `derived` descriptors, `predicted` endpoints, `measured` published values | Descriptors are computed properties, not measurements |
| Metabolic stability | `property_estimate`, `literature_retrieval` | `predicted`, `measured` | Units and assay conditions must be carried, not normalised away |
| Toxicological safety | `property_estimate`, `literature_retrieval`, `document_reading` | `predicted`, `measured`, `wet_lab_observation` where published | Severity and reversibility weighting is an expert judgement, not a tool output |
| Optional context | `dataset_context_lookup` | `context_only` | The supplied datasets are `role: context_only`; no criterion value may derive from them while units and endpoint meanings are undocumented |

Two machine-enforced gates apply throughout: a value whose unit is `unknown` may be stored and displayed but never consumed by the assessor; and a criterion requiring a measured value cannot be satisfied by a prediction-only provider, which yields `unknown_missing`.

## 10. Expert dependencies

Each becomes a review-queue item with an `hd_` record:

1. Which attributes may carry hard exclusions at all.
2. Every cutoff and its `cutoff_basis`, including whether the evidence supports a number, only a range, or neither; and whether a qualitative determination may exclude.
3. Applicability conditions per attribute, and what `inapplicable` means for this objective.
4. Relative standing of source statuses, and what makes two conflicting claims "comparable".
5. Independence grouping where a shared experiment, dataset, or cohort is suspected.
6. Candidate identity equivalence across salt forms, formulations, codes, and ambiguous names.
7. Unit and endpoint normalisation across heterogeneous measurement contexts, including species extrapolation.
8. The coverage floor for `recommended`, and whether predicted values may ever satisfy a hard rule.
9. Equivalence judgements in the recovery comparison (`expert_judged_equivalent`).
10. Whether the five-target configuration is a fixed constraint or a questioned hypothesis for this case.
11. The registered sensitivity ranges and their biological justification.
12. The threshold for "most" in Target A.

## 11. Records produced and the handoff

| Record | Produced by | Handed to the rebuttal as |
|---|---|---|
| R1 | C10 | rule-evolution history with sources, critiques, and confirmations |
| R2 | C11 | per-compound per-criterion decisions with reasons |
| R3 | C12 | leaderboard snapshots with result kind, reporting tuple, tool coverage, change records |
| R4 | C10 comparison component, C19 | recovery comparison with mapping kinds and reason-quality ratings |
| R5 | C19 | preregistration events, Case Acceptance Register, sensitivity results, outcome dependence report |
| R6 | C13 | tool and adapter records, including absence records |
| R7 | C18 | expert decision records |
| R8 | C19 | evaluation protocol manifest and `claim_scope` blocks |
| R9 | C1 | journal exports with open questions and termination reasons |

The mapping from each record to the rebuttal statement it supports is in `rebuttal_alignment.md` §4.

## 12. What this protocol does not do

- It does not execute any stage. No criterion, assessment, snapshot, recovery comparison, or sensitivity result exists.
- It does not propose thresholds, ranges, or a coverage floor, and it does not enumerate the originally reported criteria.
- It does not claim that the reference candidate will be admitted, nor pre-register an expectation that it will be.
- It does not treat the historical 140-compound stage as a candidate set or as an admission criterion.
- It does not require an interaction-prediction backend; where none is available the run records absence and reports coverage.
- It does not establish biological effectiveness. Passing the process-level checks in `evaluation_plan.md` demonstrates that the system behaves as specified, not that any candidate is therapeutically effective.
- It does not treat this case as blind discovery. Surufatinib is a disclosed reference outcome, and the case is a known-outcome reconstruction whose purpose is to document how criteria and candidate decisions were established.

**Sources:** `optimized_design.md` §0, §8.6, §13.6, §16, §17; `03_Provided_Rebuttal_Draft_EN.md`; `01_Concept_Overview_EN.md` ("Testing the nomination"); `agent_reports/evidence_and_policy.md` §3.2, §6.3, §8 and cross-review; `agent_reports/evaluation_and_improvement.md` Findings 8–9 and cross-review; `agent_reports/tools_and_data.md` §2, §4, Finding 8; manuscript text extract (screening passage) for the universe size, the 140-binder stage, the five targets, and the three dimensions.
