# Workstream 5 — Evaluation and Self-Improvement Audit

Agent: Workstream 5, Evaluation and Self-Improvement Auditor. Design only; no implementation code. English throughout. 12 October 2026.

## Summary

1. **No held-out evaluation or measured strategy promotion exists in the inspected code.** In `Agentic-Doping-snapshot` at commit `0007ad10`, "promotion" is a memory *scope transfer* with a trust stamp (`harness/memory.py:1073-1124`). There is no baseline arm, fixed evidence snapshot, matched-budget harness, held-out material, or regression-triggered rollback in `src/` or `tests/`.
2. **The one quantitative signal feeding strategy selection is confounded.** A skill's `uses` counter increments when the reviewer LLM accepts a proposal generated with that skill already in its prompt (`dual_agent/harness.py:1275-1283`, called at `dual_agent/loop.py:260`); provisional skills are then ranked by `uses` for future injection (`harness/memory.py:872-873`). Self-reinforcing, no control arm; it must not be reused as an improvement metric.
3. **The content guardrail is bypassed on one authoring path.** `validate_methodology_skill` guards three call sites; `_maybe_promote_skill` (`harness/memory.py:422-456`) writes candidate-specific procedures through `add_skill`, which validates no content.
4. **The reference cannot settle the round-policy question.** Its `max_rounds` bounds *review exchanges* inside one candidate slot (`dual_agent/loop.py:209-305`), not screening rounds.
5. **Spine component 13 names the right artefacts and no decision rule**, no guard against promotion by weakened admission, and no claim boundary.
6. **Most important recommended change:** make the historical eleven-CQA artefact *evaluator-only*. If the deriving agents can read it, CQA-recovery fraction measures retrieval of a supplied answer, not derivation, and the primary acceptance target becomes unfalsifiable.

## STEP 1 determination

| Question | Determination | Location (commit `0007ad10`) |
|---|---|---|
| Held-out evaluation of strategies? | None. `eval_mlip/` and `evaluation_cascade/` evaluate *candidate physics*; `runs/*/eval` are per-candidate physics outputs. | No comparison harness in `src/` or `tests/` |
| Is `E3 = "external holdout"` a policy holdout? | No — terminology trap. E3 means external-dataset or multi-MLIP agreement about a *material*. | `evidence_ledger/enums.py:18` |
| What is "promotion" in code? | A legal scope hop plus a trust stamp. Gates: valid target, two-step hop (private must pass through group public), `_memory_ready` for the super hop, de-duplication. No metric is read; the record is rewritten `review_state="approved"`. | `harness/memory.py:1073-1124` |
| Is `approved_by="human"` reliable? | No. Hard-coded regardless of caller; the HTTP route checks group ownership, not that a scientist judged. | `harness/memory.py:1020-1045`, `1113-1120`; `web/server.py:3374-3392` |
| Automatic skill creation? | Yes, by frequency: 3 repeated rejections of a `(site, single-dopant)` family, or 1 if a "non-viable" word appears. | `harness/memory.py:422-456` |
| Guardrail applied there? | No. `add_skill` performs no content check; the text written embeds an element symbol, a site and a count. | `harness/memory.py:363-391`; validator `skill_policy.py:140`, called only at `agent_harness.py:338`, `harness.py:1058`, `reflection.py:210` |
| Is skill usefulness measured? | No — only co-occurrence with an acceptance. Approved skills are injected in full every run, no decay or re-check. | `dual_agent/harness.py:1275-1283`; `harness/memory.py:755-779`, `862-863`, `872-873` |
| Retraining? | Explicitly deferred; `select_next()` returns `status="placeholder"`. | `flywheel/flywheel.py:1-77`; `workplan/PLACEHOLDERS.md` |
| Do tests exercise improvement? | No. The reflection, memory-scope, trust-flow, flywheel, dialogue-learning and knowledge-flow tests are containment and guardrail tests; none compares a policy to a baseline. | `tests/test_post_run_reflection.py` and five peers (named in the contribution record) |

The excerpts are good *containment* engineering: they stop a bad lesson spreading. They do not measure whether any lesson helps. The evaluation design below must be built, not adapted.

---

## (a) Operating policies, held-constant protocol, matched budgets, progress

### Finding 1 — The policy comparison needs a fourth and fifth arm, or "better strategy" and "more compute" stay confounded

**Issue.** Capping the adaptive policy at the baseline budget tests one direction only. Without also giving single-pass the adaptive policy's realized budget, a win for adaptivity is indistinguishable from a win for spending more.

**Source / location.** `START_HERE_Audit_and_Optimize_Prompt_EN.md` lines 68-72; `Project_Brief_EN.md` §6; no comparison harness in the reference repo (STEP 1).

**Importance.** High — it decides whether the eventual round-policy claim is defensible.

**Recommended change.** Register five frozen policy versions in the evaluation harness (spine component 13):

| Arm | Definition | Continuation triggers | Stopping criteria | Budget role |
|---|---|---|---|---|
| **P0** single-pass | One screening round; several agents may contribute; one proposer–critic exchange per criterion and candidate. | None | Stops after the round; unresolved items stay `unresolved`. | Its realized cost defines the matched cap. |
| **P1** fixed-round | Exactly *R* rounds (*R* registered in advance; 2 and 3 are separate versions). | None — rounds are scheduled. | After round *R*. | Cost reported. |
| **P2** adaptive | Continue only on a satisfied trigger. | New admissible evidence; unresolved conflict on a consequential criterion; consequential missing measurement; questionable exclusion; targeted computation with registered decision value. | Sufficient support; no actionable step; information gain below a registered threshold; repeated identical failure; budget exhausted → `unresolved`. | Cost reported. |
| **P2-cap** | P2 hard-capped at P0's realized median budget. | Same as P2 | P2's plus the cap. | Tests adaptivity at equal spend. |
| **P0+** budget-rich single pass | P0 given P2's realized median budget, spent in one pass: wider retrieval, more candidates per pass, more parallel critics, best-of-*n* adjudicated by the in-run critic. | None | After the round. | Tests the same spend without extra rounds. |

Report P2 as an improvement only if it beats both P0 and P0+ and P2-cap does not fall below P0. If P2 beats P0 but loses to P0+, the honest conclusion is that budget helped and adaptivity did not.

**Tradeoff.** Roughly fivefold evaluation cost per task, and P0+'s surplus-spending rule is itself gameable; fix and version it before evaluation.

**Unresolved uncertainty.** Whether median or 90th-percentile budget is the right matching statistic, and whether human-review minutes can be matched when arms surface different numbers of review items.

### Finding 2 — The held-constant protocol must be a signed manifest, not prose

**Issue.** "Same tasks, candidate universe, cutoff, tools, evaluator" cannot be checked after the fact, and evidence drift between arms is the likeliest route to a false improvement. The reference's memory store is deliberately persistent *across* runs (`harness/memory.py:1-15`) — the opposite of a frozen comparison condition.

**Source / location.** `START_HERE_Audit_and_Optimize_Prompt_EN.md` lines 70-71; `Project_Brief_EN.md` §6 ("keep evidence snapshots fixed").

**Importance.** High — otherwise memory accumulated in arm *k* advantages arm *k+1*.

**Recommended change.** An **Evaluation Protocol Manifest**, written before any arm runs, hashed, referenced by every run and reported number. Fields: `protocol_id`; `registered_at`/`registered_by`; `task_set_id` with per-task `task_context_id` (frozen objective, intended outcome, candidate universe, constraints, unknowns, evaluation scope); `evidence_snapshot_id`; `snapshot_hash`; `source_access_cutoff`; `tool_manifest` of {tool_id, contract_version, endpoint_class ∈ local|remote|unavailable, determinism ∈ yes|no|seeded}; `tool_outage_policy` ∈ abort_arm|record_unresolved|retry_bounded; `memory_mode` per arm ∈ cold (empty) | frozen (read-only approved snapshot) | warm (writes allowed), where policy comparisons use cold or frozen and warm is labelled and reserved for across-run studies; `evaluator_id`; `evaluator_kind` ∈ human_expert|rule_based|llm_judge; `evaluator_blinding` ∈ arm_blind|unblinded; `evaluator_instructions_hash`; `metrics` (ordered primary plus guard metrics); `budget_caps` per arm (wall-clock, tokens, tool calls, human-review minutes); `seeds`; `n_repeats` ≥3 per task per arm; `analysis_plan`; `stopping_rule_for_the_evaluation_itself`.

**Tradeoff.** Cold or frozen memory removes the mechanism across-run improvement exploits, so the harness needs two study types.

**Unresolved uncertainty.** Whether an LLM evaluator is admissible for any primary metric. My position: no for domain correctness, acceptable for mechanically checkable process metrics.

### Finding 3 — "Progress" needs a mechanical definition, because the reference credits the wrong thing

**Issue.** P2 is only as good as its progress definition. The reference's nearest analogue credits *reviewer acceptance* (`dual_agent/loop.py:260`) — a model verdict about an artefact that model just saw.

**Source / location.** `dual_agent/loop.py:250-266`; `dual_agent/harness.py:1275-1283`; `START_HERE_Audit_and_Optimize_Prompt_EN.md` line 72.

**Importance.** High — a wrong definition makes P2 run indefinitely and claim gain each time.

**Recommended change.** Score each round transition in a **Round Progress Record**: `round_id`, `parent_round_id`, `trigger_claimed`, `progress_kind`, `evidence_delta_ids`, `conflict_ids_resolved`, `gap_ids_filled`, `decision_changes`, `verdict` ∈ progress|non_progress|unresolved.

| Progress | Required observable | Non-progress | Why excluded |
|---|---|---|---|
| New admissible evidence | ≥1 new ledger entry with a resolvable source location, de-duplicated by source identity not text | Rephrased rationale | No ledger delta |
| Resolved conflict | A conflict record moves `open` → `resolved` or `irreducible`, naming the deciding source or expert decision | Higher self-reported confidence | An LLM confidence statement is not a reliability estimate |
| Filled consequential gap | A `missing` per-criterion value becomes `measured`/`predicted` *and* flips a per-criterion verdict, or was pre-registered as decision-relevant | More citations for an already-supported claim | Repeated copies of one study are one source |
| Corrected a decision | A candidate state or criterion version changes, with a named cause | Longer or more elaborate reasoning | No ledger or decision delta |
| Registered negative result | A planned retrieval or tool call returned nothing admissible, recorded as such | Agreement between agent roles | Shared context, shared bias |

Two consecutive `non_progress` verdicts stop P2, independent of budget.

**Tradeoff.** "Consequential" needs a pre-round declaration of decision-relevant gaps, gameable by declaring everything consequential; the declaration is versioned and visible to the evaluator.

**Unresolved uncertainty.** Whether requiring a flipped verdict is too strict for a gap that narrows uncertainty without changing a decision; record strict and permissive counts separately.

---

## (b) Within-run refinement versus across-run improvement

### Finding 4 — The two must have different artefacts, approval paths, and evaluations

**Issue.** The package calls both "self-improvement". Conflating them lets ordinary within-run scientific revision be reported as agent self-improvement.

**Source / location.** `Project_Brief_EN.md` §6; `01_Concept_Overview_EN.md` "What self-improvement means"; `03_Provided_Rebuttal_Draft_EN.md` paragraph 1 versus paragraph 3.

**Importance.** High — the rebuttal's credibility depends on not inferring the second from the first.

**Recommended change.** Two registries, two evaluations:

| Dimension | Within-run rule refinement | Across-run strategy improvement |
|---|---|---|
| Object changed | Criterion Registry version (add/revise/merge/split/remove), per-candidate assessments, leaderboard snapshot | Retrieval procedures, review checklists, tool-selection rules, failure handling |
| Authority to confirm | Human scientific approval; agent verdicts are proposals | Measured improvement under the manifest, plus a named operator sign-off |
| Evidence standard | Source-linked evidence per criterion; conflicts retained | Matched-budget comparison on held-out material across more than one case |
| Legitimate claim | "The rules were revised under review" | "This policy performs better on this material at this budget" |
| Never licenses | Any statement about agent capability | Any statement about biological effectiveness |

Memory kinds keep the coordinator brief's definitions: **evidence** becomes `approved` only with a resolvable source location and an independence marker, never by agent agreement (a tool success does not validate the claim it returned); **tentative hypothesis** stays provisional indefinitely, recallable only in its originating group/scope, cited only as a marked hypothesis; **reusable procedure** starts provisional and is approved only through the (f) protocol, with an expiry.

**Tradeoff.** Two paths invite routing procedure changes through the faster rule-approval path; make the registries structurally distinct so a procedure cannot be written to the criterion registry at all.

**Unresolved uncertainty.** Whether a recurring within-run refinement should graduate automatically into a procedure *proposal*. Proposal-only, never automatic approval — the recurrence threshold is unknown, and the reference's choice of 3 (`SKILL_PROMOTE_THRESHOLD`) has no evidential basis I could find.

### Finding 5 — The guardrail against candidate-specific lessons is bypassed on the automatic path

**Issue.** `validate_methodology_skill` rejects candidate identifiers, specific material sets, observed scores and thresholds, performance conclusions, source conclusions and non-methodological text. `_maybe_promote_skill` writes through `add_skill`, which checks only non-emptiness and name de-duplication, and the text it writes contains exactly what the policy forbids.

**Source / location.** `harness/memory.py:422-456`, `363-391`; `harness/skill_policy.py:140-206` and its three call sites.

**Importance.** High — transposed to the drug case, this is how "surufatinib was admitted *n* times, prefer it" becomes standing prompt guidance, which the package forbids (`02_Agentic_Doping_Reference_EN.md`, strategy-checks row).

**Recommended change.** Make the content policy a property of the *store*, not the caller: every write to the procedure registry passes the validator regardless of author (`agent`, `harness`, `human`). Add two checks it lacks — a **candidate-universe scan** against the case's candidate identifiers and aliases, including the known reference outcome, and an **outcome-reference scan** rejecting text naming a position, rank or admission status. Human overrides require a record naming the person.

**Tradeoff.** A store-level validator will reject some legitimate domain-flavoured procedures, since vocabulary and candidate names are hard to separate mechanically; route rejections to the human review queue with their violation codes rather than discarding them.

**Unresolved uncertainty.** False-rejection rate is unmeasured; scenario S6 exists to measure it before the validator is relied upon.

### Finding 6 — Do not reuse the acceptance-credited `uses` counter as an improvement signal

**Issue.** The skill influenced the proposal and the accepting reviewer also saw the skill. No arm exists in which it was absent, so the counter measures circulation, not benefit — and it then ranks what gets injected next.

**Source / location.** `dual_agent/loop.py:260`; `dual_agent/harness.py:1275-1283`; `harness/memory.py:755-779`, `862-863`, `872-873`.

**Importance.** High — the reference's only numeric self-improvement signal, so the most likely to be copied.

**Recommended change.** Replace it with a **procedure trial record** requiring absence as well as presence: `procedure_id`, `protocol_id`, `arm` ∈ with_procedure|without_procedure, `task_context_id`, `evidence_snapshot_id`, `outcome_metrics`, `budget_consumed`, `evaluator_id`. A procedure's standing is a measured between-arm delta on held-out tasks, never an accumulated co-occurrence count. Keep the counter only as an observability field named `circulation_count`, barred from any ranking or promotion rule, and give approved procedures an expiry.

**Tradeoff.** With/without doubles runs per procedure; in a thin task set most procedures will be unpromotable. That is the correct answer, though it will look like the mechanism is not working.

**Unresolved uncertainty.** Minimum detectable effect and required task count are unknown without pilot variance estimates; promotion is impossible until that variance is measured.

---

## (c) Process-level capability evaluation with bounded scenarios

Synthetic or small fixed fixtures; no biomedical labels needed. Passing establishes process correctness only.

| ID | Capability | Scenario and inputs | Observable outputs | Pass condition | Does not show |
|---|---|---|---|---|---|
| S1 | Decomposition quality | Objective with one stated constraint, one unstated-but-necessary unknown, one irrelevant distractor dataset | Task context; plan with steps, owners, budgets, completion criteria; questions asked | The unknown is surfaced as a question or explicit unknown; the distractor becomes no plan step; every step has an owner and completion criterion | Whether the plan is scientifically right |
| S2 | Appropriate delegation | Two task contexts differing only in whether a step needs expert judgement; role roster; review policy | Step owner assignments; review-queue entries | The judgement step routes to human review and the other does not; no agent verdict is stored as human approval | Expert agreement with the outcome |
| S3 | Tool-contract correctness | Tool fixture returning in sequence: valid, schema-invalid, timeout, permanent error, empty | Tool request/result records; retry records; downstream inputs; per-criterion values | All five classes distinguished; retries bounded and recorded as retries not rounds; empty and invalid yield `missing`/`unresolved`, never `failed`; the valid result enters the next step | Whether the output is scientifically valid |
| S4 | Evidence traceability | Corpus of three sources, one a duplicate of another under a different identifier | Rationales; ledger entries with source locations; independence markers | Every material claim resolves to a source location; the duplicate pair counts as one underlying source; no claim lacks a ledger entry | Truth of the sources |
| S5 | Contradictions and missing data | Fixture with a planted threshold conflict and a criterion with no data | Conflict records; criterion retaining uncertainty; per-candidate `missing` values | The conflict is recorded open or resolved-with-reason, not averaged away; no cutoff is invented; `missing` distinguished from `failed` and `inapplicable` | Which side of the conflict is right |
| S6 | Memory isolation and reuse | Run A authors a provisional procedure naming a candidate and a threshold; run B is a different task in another group; plus 20 legitimate procedure texts | Validator verdicts with violation codes; recall sets for A and B; review-queue entries | The violating text is rejected on every authoring path including automatic ones; no provisional record crosses groups; false-rejection count on the 20 is reported | Whether accepted procedures help |
| S7 | Stop/resume | A run interrupted at each of three checkpoints, then resumed | Event journal; resumed state; reuse-versus-recompute labels | Resumed state equals the pre-interruption projection replayed from the sequence number; no step silently recomputed to a different result; reached budget yields `unresolved` | End-to-end reproducibility |
| S8 | Human-edit propagation | Three scripted post-run edits: threshold change, criterion removal, unit correction | Stale markers; required-rerun list; reused-result list; attributed new versions | Exactly the affected records are stale; unaffected results are labelled reused; prior versions stay inspectable; the unit correction propagates to every dependent comparison | Whether the edit was scientifically right |
| S9 | Useful strategy updates | One procedure run with/without across a held-out task subset under a manifest | Procedure trial records; metric deltas; guard-metric values | Delta computed on held-out material at matched budget with guards unviolated; absent a positive delta the procedure stays provisional | Generalization beyond that set |
| S10 | Cost | S1–S9 instrumented | Wall-clock, tokens, tool calls, human-review minutes per arm per task | Costs recorded per arm and reported alongside every metric; no metric published without its budget | Value for money |

A suite passing S1–S10 is easy to mis-describe as "the system was validated", and prohibition in the prompt (`START_HERE_Audit_and_Optimize_Prompt_EN.md` lines 108-110) does not prevent it in the write-up. Have the harness emit a fixed `claim_scope` block with every process report — `establishes` (behaviours observed), `does_not_establish` (biological effectiveness, predictive accuracy, expert agreement, generalization beyond the task set), `label_dependency` — owned by spine component 13 so no author can omit it.

---

## (d) Domain-outcome validation, reported separately

| Metric | Definition | Labels / expert review? | Reporting rule | Unestablished without labels |
|---|---|---|---|---|
| Precision among admitted | Fraction of `recommended` candidates expert review judges correctly admitted *under the stated criteria and evidence* | Qualified expert review; no outcome labels | Always with denominator and coverage; never alone | Whether admitted candidates are pharmacologically effective |
| Evidence correctness | Fraction of sampled material claims whose source location supports the claim as stated | Expert or trained-annotator review of a registered sample | Report sampling frame, sample size, inter-rater agreement | Whether the sources are themselves right |
| Independent support | Fraction of admitted candidates whose decisive criteria rest on ≥2 sources that are not the same underlying experiment | De-duplication plus expert adjudication of borderline cases | Report the de-duplication rule; copies of one study count once | Whether independent sources are jointly correct |
| Unsupported-claim rate | Material claims with no resolvable source location, or a source that does not support them | Expert review on a sample | Registered **guard metric**; must not rise | — |
| Incorrect-exclusion rate | Fraction of sampled excluded/`rejected` candidates expert review judges wrongly excluded | Expert review of a stratified sample including borderline exclusions | Report beside precision; a precision gain with a rise here is not an improvement | True negatives in any biological sense |
| Coverage | Fraction of the candidate universe reaching a complete per-criterion assessment | No | Mandatory beside precision, so an empty shortlist cannot win | — |
| Abstention | Candidates left `unassessed`/`unresolved`, grouped by reason | No | Mandatory; an empty `recommended` set is abstention, not precision 1.0 | — |
| Uncertainty calibration | Agreement between stated uncertainty bands and expert-adjudicated correctness, where a band exists | Expert review; computable only on that subset | Report with the subset size; LLM confidence statements excluded by definition | Calibration where no quantitative band exists |
| Reproducibility | Agreement of candidate states and criterion versions across repeats at fixed snapshot and policy | No | Per arm across ≥3 seeds; disagreements itemized | Nothing about correctness |
| Operating cost | Wall-clock, tokens, tool calls, human-review minutes per task per arm | No | Attached to every metric above | — |

### Finding 7 — Precision must never be reported without coverage and abstention in the same row

**Issue.** Precision-first admission plus a legitimate empty recommended set creates a degenerate optimum: admit nothing, and precision is vacuous or undefined. The package anticipates this without specifying the reporting shape that prevents it.

**Source / location.** `START_HERE_Audit_and_Optimize_Prompt_EN.md` lines 58, 82-84, 110; `Project_Brief_EN.md` §6.

**Importance.** High — the likeliest way a "better" strategy would be manufactured.

**Recommended change.** One mandatory reporting tuple per arm per task, emitted atomically by the Leaderboard Service: `{admitted_n, precision_among_admitted, coverage_fraction, abstention_n_by_reason, incorrect_exclusion_rate, unsupported_claim_rate, budget}`. The harness refuses to render precision when `admitted_n = 0`, printing `undefined (admitted_n = 0)`. Promotion rules read the tuple, never precision alone.

**Tradeoff.** Richer tuples are harder to compress into a manuscript sentence; the text will need a careful one-line summary rather than one number.

**Unresolved uncertainty.** Whether a composite admission-quality score should exist. My recommendation is no — keep the tuple and let reviewers see the tradeoff.

---

## (e) Case-level acceptance checks for the primary case

No result is asserted here. These are checks to run later, with recording rules fixed in advance.

### Finding 8 — CQA-recovery fraction is meaningless unless the historical list is withheld from the deriving agents

*Revised after cross-review:* my six recovery categories should be a reporting roll-up over WS1's nine-value `mapping_kind` enum, not the stored vocabulary, and the asserted exclusion boolean should be replaced by an access log.

**Issue.** The acceptance target is that derived criteria recover most of the historical CQAs with evidence-linked rationales. The eleven are not in the manuscript main text, so an intake step supplies them. If that intake reaches the deriving agents, recovery measures copying.

**Source / location.** Coordinator brief §2 and §6; `START_HERE_Audit_and_Optimize_Prompt_EN.md` lines 25, 31; `Project_Brief_EN.md` §2 ("Do not start from a mandatory checklist of eleven items").

**Importance.** High — this is the acceptance target for the whole v1 purpose.

**Recommended change.** Register the historical list as an **evaluator-only comparison reference**: stored in the Criterion Registry with `visibility = evaluator_only`, excluded from every agent prompt and retrieval index, access logged, so the event journal can prove no deriving run read it. Score recovery by expert-adjudicated per-criterion mapping:

| Category | Meaning | Required fields |
|---|---|---|
| `recovered` | A derived criterion covers the same property and decision role | derived_criterion_id; property-match rationale; rule-role match (hard exclusion / preference / exploratory); evidence links; reviewer identity |
| `merged` | One derived criterion covers two or more historical ones | derived_criterion_id; historical ids; justification |
| `split` | Several derived criteria cover one historical one | derived_criterion_ids; justification |
| `removed` | Derivation found no evidential support | reason; the searches and sources that failed to support it; retrieval failure versus genuine absence |
| `added` | A derived criterion with no historical counterpart | derived_criterion_id; evidence links; whether it changed any candidate decision |
| `not_recovered` | Not covered, and no justified removal reason | reason; whether supporting evidence existed in the snapshot |

Report recovery as a fraction *with its denominator and the full category breakdown*, plus a separate expert rating of reason quality per criterion on a registered ordinal scale. High recovery with poor reason quality is not an acceptance.

**Tradeoff.** Evaluator-only visibility means the agents may miss a criterion an expert finds obvious, lowering measured recovery relative to an unblinded run — the honest cost of a meaningful measurement.

**Unresolved uncertainty.** Where "most" lies. The threshold should be registered by the authors and experts before evaluation; this report states no number.

### Finding 9 — Surufatinib admission needs a prespecified baseline, pre-registered ranges, and a fixed non-admission recording rule

**Issue.** The rebuttal draft states surufatinib remains top-prioritized under the original configuration while large changes reorder competitors; the package records this as an intended question, not a result. Without pre-registration, any configuration that admits it can later be relabelled "the baseline".

**Source / location.** `03_Provided_Rebuttal_Draft_EN.md` paragraph 3 and claims table ("Sensitivity ranges were prespecified and tested — Not performed here"); `START_HERE_Audit_and_Optimize_Prompt_EN.md` line 114; coordinator brief §2, §6.

**Importance.** High — the claim a reviewer will scrutinize hardest.

**Recommended change.** A **Case Acceptance Register** fixed before any evaluation run; anything added later is exploratory.

| Check | Prespecified content | Observable output | If not met |
|---|---|---|---|
| Baseline configuration | criterion version id; hard exclusions versus preferences; ordering method; evidence snapshot id; candidate universe id; tool manifest | Leaderboard snapshot with per-candidate, per-criterion records | — |
| Surufatinib admission under baseline | Expected state ∈ `recommended`\|`provisional`; decisive criteria named in advance | Candidate state with per-criterion evidence, value provenance, verdict, reason | Record the observed state, the criteria that failed or were `missing`, and whether the cause was absent evidence, a tool gap, or an excluding criterion. Do not adjust the baseline to fix it. |
| Result-type naming | Whether the claim is "unique all-pass under hard rules" or "top-ranked under a score" | The selection procedure actually applied | If the procedure yields top-ranked rather than unique all-pass, the rebuttal must say so; they are different claims |
| Sensitivity ranges | Per-criterion ranges with biological justification and sources, timestamped | Candidate states and orderings under each configuration, all retained | Configurations not admitting surufatinib are reported with equal prominence |
| Alternative configurations | Named justified alternatives (different applicability condition, unit convention, stricter evidence tier) | Comparative snapshots with rank-change explanations | Reported as-is |
| Exploratory tuning | Any range or configuration chosen after seeing outcomes | Labelled `exploratory` in the registry and every report | Never described as prespecified |

**Implications for rebuttal wording.** Admitted under the baseline and across the registered ranges → state a conditional prioritization, naming the ranges. Admitted under the baseline but not across parts of the range → state it as conditional on the specific assumptions that sustain it, naming those that do not. Not admitted under the prespecified baseline → report the derived criteria, the specific failures or missing measurements, and what evidence would resolve them; the manuscript cannot claim the framework recovered the original prioritization. `unresolved` from budget or tool unavailability is neither admission nor non-admission. Low CQA recovery → the wording cannot claim the framework reconstructs the original screening rationale, only that it derives an evidence-linked set differing in stated ways.

**Tradeoff.** Pre-registration removes the freedom to improve the configuration after a disappointing result, so a weaker but checkable case may be published instead of a tuned one.

**Unresolved uncertainty.** Whether a baseline can be specified before the criteria exist, since criteria are an output. Recommendation: register in two stages — the *policy* (hard-exclusion semantics, ordering method, evidence-tier requirements, snapshot) before derivation, and the *criterion version* on expert approval and before any candidate assessment — both timestamped in the event journal. WS1 should confirm compatibility with its criterion contract.

---

## (f) Strategy promotion protocol

### Finding 10 — Promotion must be unsatisfiable by weakening admission, and must survive a fixed snapshot

*Revised after cross-review:* the hashed `evidence_admission_predicate` must also cover the hard-rule coverage floor and WS1's registered numeric constants, and the promotion decision needs a fourth, disjoint `operations_decision` field rather than reuse of any approval field.

**Issue.** Any single-metric rule based on precision, or on how often the known reference outcome is selected, can be satisfied by admitting less, loosening evidence requirements, or new data arriving between arms. The package names all three risks without specifying the mechanism; the reference has no promotion criterion at all.

**Source / location.** `START_HERE_Audit_and_Optimize_Prompt_EN.md` lines 110-116; `Project_Brief_EN.md` §6; STEP 1 table.

**Importance.** High — the difference between evaluated self-improvement and a tuned demo.

**Recommended change.** Promotion is a conjunction of a measured gain and invariants, all read from the manifest. Record fields: `strategy_version_id`; `parent_version_id`; `change_class` ∈ prompt_text|procedure_memory|tool_selection_rule|retrieval_rule|failure_handling|model_weights; `change_summary`; `authored_by`/`authored_at`; `protocol_id`; `evidence_snapshot_id` (identical across arms); `memory_mode` ∈ cold|frozen; `held_out_task_ids`; `budget_caps`; `n_repeats`; `primary_result` (the Finding 7 tuples for candidate and baseline); `guard_metrics` (unsupported-claim rate, incorrect-exclusion rate, coverage, abstention, `evidence_admission_predicate_hash`, reproducibility agreement); `decision` ∈ promote|reject|inconclusive; `decided_by`/`decided_at`; `rollback_target`; `expiry_at`.

Promotion requires **all** of: (1) a positive delta on registered primary metrics against the fixed baseline, on **held-out tasks spanning more than the current case**, at **matched budget**, across the registered repeats; (2) `evidence_admission_predicate_hash` identical to the baseline's, since a strategy that changes what counts as admissible evidence is a policy change requiring separate expert approval, not a strategy improvement; (3) no guard metric degraded beyond registered tolerance — coverage must not fall, unsupported-claim and incorrect-exclusion rates must not rise, and guards are gates rather than weighted terms, because a composite can always be traded off; (4) reference-outcome selection frequency **excluded** from promotion metrics and reported only descriptively, since more frequent selection of surufatinib is not evidence of improvement; (5) a named operator records the decision, stored as an operations record — a different record kind from human scientific approval.

Also required. **Rollback:** the parent version stays executable and selectable; expiry forces re-evaluation or reversion; a guard breach on later material triggers rollback as a journal event, never a silent edit. **Pool discipline:** three disjoint pools registered once — `development` (free use), `validation` (candidate selection, with a registered maximum number of looks per lineage), `final` (sealed, opened at most once per lineage, the opening recorded); a second look at `final` invalidates that lineage's claim. **Prompt/memory versus weight training:** `change_class` separates them; weight training additionally requires a stated task and label source, a held-out set disjoint from training, a no-additional-training baseline under the same protocol, cost accounting, and a gain over the prompt/memory baseline rather than over an untuned control, and reflection-authored prompt text is a memory update, never training. **No-additional-training baseline:** v1 runs on prompts, procedures, retrieval rules and tool contracts only, and is the reference every optional trained model must beat (`START_HERE_Audit_and_Optimize_Prompt_EN.md` line 116).

**Tradeoff.** These criteria make most proposed strategies unpromotable early, when the task pool is small and variance unmeasured, so the system will look static. A permissive rule instead produces promotions that cannot be defended in a manuscript.

**Unresolved uncertainty.** Pool size, guard tolerances, and per-task versus pooled analysis all depend on variance that does not yet exist; where the design must state numbers, it should mark them unregistered placeholders.

---

## (g) Critique of the inspected mechanism and of spine component 13

### Finding 11 — The reflection/skill mechanism is containment, not self-improvement, and should be cited as such

**Issue.** The concept documents present the reference as a basis for provisional methodology reflection in a self-improving platform, inviting the reading that the improvement loop exists and merely needs transferring. The loop is open: reflection proposes, guardrails filter, memory stores, prompts consume — nothing measures.

**Source / location.** `orchestration/reflection.py:158-264`, with its docstring at lines 1-4 stating it never alters the current run; `harness/skill_policy.py:140-206`; `harness/memory.py:1073-1124`; `flywheel/flywheel.py:1-77`; `02_Agentic_Doping_Reference_EN.md` "Limits that matter"; `01_Concept_Overview_EN.md` "What self-improvement means".

**Importance.** High — it sets what the architecture documents and rebuttal may claim about prior art.

**Recommended change.** State the contribution precisely: the reference supplies a forward-only reflection boundary that cannot retroactively change a completed run; a content policy with stable violation codes; scope-partitioned provisional memory with a two-step human trust boundary; and an explicit deferral of acquisition and retraining. It supplies nothing for policy comparison, held-out evaluation, promotion or rollback. Three defects must not transfer: the acceptance-credited `uses` ranking (Finding 6), the unvalidated automatic authoring path (Finding 5), and unconditional full injection of approved procedures with no expiry (`harness/memory.py:862-863`). One strength should transfer and be strengthened: the honest-skip outcome should become a first-class counted result, so "no reusable improvement was demonstrated this run" is a normal reportable outcome.

**Tradeoff.** Describing prior art this narrowly reduces apparent platform maturity; it also removes the risk that a reviewer finds the gap first.

**Unresolved uncertainty.** I read source and test names but executed no tests and did not audit recorded `runs/` history, so the determination rests on code and test inspection.

### Finding 12 — Spine component 13 lists artefacts but omits the decision rule, pool discipline, and claim boundary

**Issue.** Component 13 is "policy versions, fixed evidence snapshots, held-out material, matched-budget comparisons, promotion and rollback". Every noun is right and no verb is specified; as written it is satisfied by a version table and a spreadsheet, which is how most self-improvement claims fail.

**Source / location.** Coordinator brief §5 item 13; `START_HERE_Audit_and_Optimize_Prompt_EN.md` §5.

**Importance.** High — it carries the self-improvement claim.

**Recommended change.** Re-specify it as the **Evaluation and Promotion Authority**, owning five things the current wording omits: the Evaluation Protocol Manifest, which no component may bypass (a run with no `protocol_id` is not admissible as evidence); pool discipline with sealed final material and recorded looks; the promotion conjunction including the admission-predicate invariant and the exclusion of reference-outcome frequency; the `claim_scope` block on every report; and rollback and expiry as journal events. It should also own the P0/P1/P2/P2-cap/P0+ arm registry, so the round question is answered by measurement rather than architectural preference. It must **not** own criterion approval — that belongs to the Human Review Queue and Criterion Registry — because an authority that both approves criteria and judges policies can satisfy its own promotion criteria by changing what counts as admissible.

**Tradeoff.** An authority over what counts as evidence becomes a bottleneck, and a strict manifest blocks early exploratory runs; exploratory runs are permitted and simply carry no `protocol_id`, making them structurally unusable as evidence rather than merely discouraged.

**Unresolved uncertainty.** Whether the authority should also gate within-run rule refinement. I recommend not, keeping scientific approval with experts — but that creates a seam where a strategy change could be disguised as a criterion change; cross-review with WS1 should test it.

### Dependencies on the literature workstreams

Six choices above are commitments made under uncertainty and are deferred to the two literature workstreams, per `START_HERE_Audit_and_Optimize_Prompt_EN.md` lines 130-136, which require an evidence-based answer on when single-pass screening suffices: (1) whether extra rounds or debate help after cost adjustment, deciding whether P1 and P2 are worth running beyond one reference configuration; (2) held-out pool sizing and minimum detectable effects; (3) whether an LLM judge is admissible for any primary metric, with reported agreement rates; (4) known evaluator-exploitation patterns the guard list should cover; (5) any published convention for budget matching across arms with differing human-review loads; (6) reported variance for agent-policy comparisons. The manifest, pool discipline, admission-predicate invariant, progress definition and the blind on the historical CQA list follow from the package's own constraints and do not wait on the literature. If the literature supports none of the six, the first studies are variance-estimation pilots and cannot support promotion; the integrated plan must say so rather than filling the gaps with plausible numbers.

---

## Cross-review of evidence_and_policy.md

Read in full on 12 October 2026 (7,108 words). We overlap on three artefacts: the historical-CQA
intake, the per-criterion assessment record, and the admission policy.

**1. Agreements.** §1.1 — without a task-context identity no two arms are comparable, and
`derivation_unavailable` is the right `unresolved` reason once the keyword fallback goes. §2.1 — my
admission-predicate invariant is undefinable while `rule_kind` does not exist. §2.2 — the four-state
table is what scenario S5 tests, and its two prohibitions remove the mechanism most likely to inflate
precision. §2.3 — `independence_group` and `determination_basis` make my independent-support metric
computable. §4.4 — cataloguing before filtering, and gating publication on a visibility manifest, is a
stronger form of my Finding 2. §5.1 — the assessment record is the substrate my Finding 7 tuple
aggregates. §6.1 — the constant registry is the missing half of my hashed admission predicate. §6.2 —
coverage-gated admission with typed empty-set reasons is my Finding 7 reached independently. §6.3(v) —
the leave-one-out report is better than anything in my Finding 9. §7.1 — three disjoint approval
fields confirm my STEP 1 finding on `approved_by="human"`. §9.2 — one vocabulary registry is a
precondition for my manifest hashes meaning anything.

**2. Objections.**

*§6.3(ii)-(iv): `reference_blind` as the only acceptance-eligible configuration.* The exclusion
predicate — claims "whose only subject is the reference candidate" — decides nothing consistently,
since most claims about a compound also concern a target or endpoint; and WS1's own §6.3 uncertainty
concedes blinding is probably unachievable, because the objective text and five-target configuration
already narrow toward the known compound. A gate that cannot be met turns the acceptance target into
automatic non-acceptance. Alternative: make the *historical criterion list* the hard blind, which is
mechanical and verifiable; record the candidate as `reference_disclosed` with the alias scan applied
to criterion definitions, rationales, cutoffs and reasons, plus the leave-one-out report; keep
`reference_blind` as one registered sensitivity arm.

*§5.2 disqualifier "identical across candidates whose cited claims differ".* For a library-wide hard
exclusion, identical reason text is often correct — many candidates fail one rule for the same
missing measurement class — so disqualifying it rewards paraphrase, which my Finding 3 calls
non-progress and no guard metric catches. Alternative: disqualify identical `evidence_refs` and
`value` under differing verdicts, dedupe structurally identical reasons by hash, and expose a
`reason_template_id`.

*§6.2 coverage floor left to case configuration.* No number should be invented, but a tunable floor
is a precision lever: raising it shifts candidates to `provisional`, raising precision and lowering
coverage without touching any admission predicate. Alternative: register it as a §6.1 constant inside
my `evidence_admission_predicate_hash`, so changing it needs `expert_decision`.

**3. Interface conflicts and resolutions.**

*Intake visibility.* WS1 uses `access_restriction: visible_to_comparison_agent_only` plus a
self-asserted `historical_criteria_excluded: true`; mine is `visibility = evaluator_only` with access
logging. The conflict is real: a comparison agent runs inside the run, my evaluator may be outside it
or human, and a boolean the deriving component writes about itself is not evidence. Resolution: keep
WS1's record, rename the value `evaluator_only` with two enumerated readers (comparison component,
review queue), replace the boolean with my access log so non-reading is provable, and attach
`protocol_id` to each criterion version so `derivation_configuration` ties to a manifest.

*`mapping_kind` versus my six categories.* WS1's nine values are strictly finer. Resolution: store
WS1's enum and publish my six as a fixed roll-up (three `recovered_*` → `recovered`;
`deliberately_removed` → `removed`; both `not_recovered_*` → `not_recovered`), reporting
`recovered_with_different_cutoff` as a separate sub-count so a cutoff mismatch is not banked as a
clean recovery. Keep my reason-quality rating, which WS1 lacks.

*Assessment `verdict` versus my Finding 7 tuple.* Not substantively conflicting — theirs is
per-criterion, mine a per-arm aggregate — but coverage must not be computed twice. Resolution: define
my tuple as aggregations over their enum, binding `coverage_fraction` to their `hard_rule_coverage`
denominator (applicable, excluding `inapplicable`) and `abstention_n_by_reason` to `unknown_missing` /
`unknown_conflicted` / `not_assessed`.

*Three approval fields versus my promotion record.* WS1's `expert_decision.subject` has no
strategy-version value, and their gate requires publication to reference `expert_decision` "and
nothing else"; a promotion must never read as scientific approval. Resolution: a fourth disjoint
field `operations_decision` ∈ promote|reject|inconclusive|rollback, writable only by the Evaluation
and Promotion Authority and outside their publication gate.

*The Finding 12 seam.* WS1's invariants close it partly: a strategy change moving a cutoff or
registered constant must surface as a criterion change record needing `expert_decision`. The residue
is retrieval-rule and prompt-text changes, which shift which claims are admitted without touching any
criterion. Resolution: carry the visibility manifest's catalog size and excluded-reason distribution
as promotion guard metrics.

**4. Dependencies.** My hashed admission predicate needs `rule_kind`, `cutoff_basis` and
`on_missing`/`on_conflict`; my guard metrics need their reason disqualifiers and `independence_group`;
recovery scoring needs their intake and `mapping_kind`; S3 and S5 need the four-state table. If their
contract is adopted I would rename my tuple fields to their enums, demote my six categories to a
roll-up, pull the coverage floor and §6.1 constants inside the hashed predicate, add the operations
field, and replace my visibility wording with their record plus access logging.

**5. Resolution summary.**

| Topic | My position | WS1 position | Resolution | Confidence |
|---|---|---|---|---|
| Historical-list visibility | `evaluator_only` + access log | Comparison-agent-only + asserted boolean | WS1's record, renamed value; access log replaces the boolean | High |
| Reference-candidate blinding | Disclose; alias-scan criterion text | `reference_blind` required for acceptance | Blind the historical list only; blinding becomes a sensitivity arm | Medium |
| Recovery categories | Six | Nine (`mapping_kind`) | Store nine; publish six as a roll-up plus a cutoff-mismatch sub-count | High |
| Verdict versus tuple | Per-arm aggregate | Per-criterion enum | Aggregate mine from their enum; one coverage definition | High |
| Promotion record | Operations record, not approval | Three approval fields | Add a fourth `operations_decision`, outside their gate | High |
| Coverage floor | Guard that must not fall | Case-configured, no number | Register inside the hashed admission predicate | Medium |
| Identical reason text | Often correct | A disqualifier | Disqualify identical refs under differing verdicts | Medium |
| Retrieval/prompt seam | Unclosed | Partly closed | Visibility-manifest statistics become guard metrics | Medium |

## Contribution record

**Agent identity.** Workstream 5 — Evaluation and Self-Improvement Auditor; a Claude Code subagent (model Fable 5.1, `claude-fable-5-1`) launched by the coordinating agent. No other identifier was given to me; I delegated nothing and spawned no further agents.

**Times.** Main report: start 2026-10-12 13:06:30 UTC, end 2026-10-12 13:30 UTC (the trimming pass was interrupted by a usage limit; the coordinator then accepted the report at 6,034 words and instructed no further trimming). Cross-review wave: start 2026-10-12 17:13 UTC, end 2026-10-12 17:34 UTC, about 20 minutes, of which the peer read was roughly half.

**Cross-review.** Read `/home/yiwei3_duke/anny/mas/design_audit/agent_reports/evidence_and_policy.md` (Workstream 1, Evidence and Decision-Policy, 7,108 words) in full, once, at its state on 12 October 2026. I did not edit it. The resulting section is `## Cross-review of evidence_and_policy.md` above, plus two `Revised after cross-review:` notes on Findings 8 and 10; no earlier finding was otherwise altered. I did not read the other peer reports (`mas_architecture.md`, `human_review_and_ui.md`), so the interface conflicts I name are with WS1 and the coordinator brief only, and a conflict between my records and the architecture or UI workstreams may remain undetected.

**Files read (full).** `design_audit/agent_reports/00_coordinator_brief.md`; and under `/home/yiwei3_duke/anny/mas/MAS_MultiAgent_Design_Audit_EN_20261012/`: `START_HERE_Audit_and_Optimize_Prompt_EN.md` (including §4.1, §4.2, §5), `Project_Brief_EN.md` (including §6), `01_Concept_Overview_EN.md`, `02_Agentic_Doping_Reference_EN.md`, `03_Provided_Rebuttal_Draft_EN.md`, `agentic_doping_reference/SOURCE_MANIFEST.json`, and excerpts 05, 06, 07, 08, 11.

**Repository inspected (read-only; nothing modified).** `/home/yiwei3_duke/anny/reference_repos/Agentic-Doping-snapshot`, commit `0007ad104755aec56cbc2479db6cf68c0e05b237` (2026-08-12), confirmed via `git log`. Read in whole or in the cited ranges: `orchestration/reflection.py` (1-158 directly; 158-264 via the packaged excerpt), `harness/skill_policy.py` (1-60, 120-213), `harness/memory.py` (1-30, 75-115, 355-470, 750-790, 855-895, 1012-1135), `flywheel/flywheel.py` (full), `dual_agent/loop.py` (209-305), `dual_agent/harness.py` (1275-1290 plus `applied_skills` sites), `evidence_ledger/enums.py` (1-40), `evaluation_cascade/base.py` and `cascade.py` (headers), `web/server.py` (3366-3400, 3470-3500), `workplan/PLACEHOLDERS.md` (grepped). Tests inspected by listing, line counts and `def test_*` names: `test_post_run_reflection.py`, `test_memory_scopes.py`, `test_memory_trust_flow.py`, `test_flywheel.py`, `test_dialogue_learning.py`, `test_forward_knowledge_flow.py`; bodies not read in full and **no test executed**.

**Tools used.** Bash (read-only `cat`, `sed -n`, `grep`, `find`, `ls`, `wc`, `git log`, plus one `mkdir` and heredoc in the session scratchpad), Read, Write (one file: this report). Scratch note: `scratchpad/ws5/code_findings.md`. No web searches: current-literature investigation is the literature workstream's assignment.

**Could not access / did not do.** I did not read the manuscript PDF or its text extract, relying on the case facts the coordinator brief establishes in §6 without re-deriving them. I did not read excerpts 01, 02, 03, 04, 09, 10, nor `04_Source_Inventory_EN.md`, `05_Delivery_Checks_EN.md`, `06_Agentic_Doping_Original_Prompt_English_Translation.md`, `07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md`; excerpt 03's content I verified against the live source instead. I did not inspect the `Agentic-Doping` `main` clone, `deepseek-harness`, `ARIS`, or `dgm`. I did not audit the snapshot's `runs/` artefacts beyond confirming the nature of `runs/*/eval`, so the "no held-out policy evaluation" determination rests on source and test inspection rather than an exhaustive run-history audit. No scientific result, ranking, threshold, score, or experimental outcome is asserted anywhere in this report.
