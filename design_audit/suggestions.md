# Suggestions: Gaps, Weaknesses, and Prioritized Improvements

Coordinating agent, 12 October 2026. This file answers the Project Brief's request for gaps, ambiguities, scientific and engineering weaknesses of the original concept, and prioritized improvements separated into v1 essentials and later extensions. It draws on the prioritized findings in `audit_report.md` §2 (A-01 to A-30), the decisions in `architecture_decisions.md` (ADR-01 to ADR-40, U-01 to U-16), and the literature in `literature_review.md`. Design only; nothing here reports a result.

## 1. Gaps and ambiguities in the original concept

**No atomic decision record.** The concept described criteria, critique, and a leaderboard, but no record existed for the per-candidate, per-criterion decision that the rebuttal promises (candidate-level decisions with rule violations and exclusions). The reference code stores numeric score breakdowns with no verdict, evidence link, or reason (A-01). Everything in the acceptance target — "most CQAs with reasonable reasons", "surufatinib on the leaderboard with per-CQA reasons" — depends on this record existing.

**"Reasonable reason" was undefined.** Without an operational definition a fluent paragraph satisfies it. The design makes a reason a record with required fields (evidence references or an absence check, value and unit as used, applicability statement, counter-evidence disposition, cutoff basis, uncertainty) and disqualifiers (sole reliance on a model self-report or another agent's verdict; out-of-scope claims; hard exclusions on title-only reads; naming the reference outcome as justification).

**Attribute and rule were fused.** The historical eleven CQAs were pass/fail criteria with thresholds; the concept kept the fusion, which makes a hard exclusion indistinguishable from a preference and leaves no room for `missing` and `inapplicable` as states distinct from `fail` (A-12). The reference code's fixed property vocabulary silently drops any proposal outside its menu.

**Human approval was a software field.** In every inspected codebase an `approved` status is written by software or an agent, the human-review state is an untyped dictionary, and the verification gate passes by default (A-02). The rebuttal's claim that experts reviewed rule updates cannot be substantiated by such fields.

**Independence was asserted, not enforced.** The reference's docstrings say the reviewer never sees the proposer's rationale; on the default tool-harness path it does (A-03). Same-family review is correlated review (`literature_review.md` §5). Role names create no independence.

**The historical CQA list had no safe home.** If deriving agents can read it, "recovery" measures copying; if the sole acceptance-eligible configuration is fully blind to the reference candidate, acceptance becomes impossible because the objective and five-target configuration already narrow toward it (A-04). The concept had not confronted this.

**Self-improvement was named, not evaluated.** No inspected repository holds out material or promotes a strategy by measurement; the reference's only numeric signal is a usage counter incremented when a reviewer accepts a proposal that already contained the skill (A-06). The literature shows evaluator exploitation is the default outcome of every loop that selects on a visible proxy (A-05).

**Execution state and progress were unreliable.** Three state vocabularies, an `exhausted` outcome relabelled as "sent after revision limit", a journal written but never read, heartbeats mutating the completion record, denominators changing five times in one recorded run, and an ETA extrapolated across them (A-07, A-08). The concept's promise of honest live progress could not be met by the reference mechanisms.

**Tool feedback was provider-specific and, for one provider, one-shot.** The committed sample runs used a path that dispatches tool calls without returning results to the model while reporting itself tool-capable (A-09). Tool contracts were inline literals with three-field provenance; four distinct absences collapsed into one null (A-10).

**Evidence handling inflated support.** Independence was inferred from distinct cache keys with a fixed bonus (a preprint plus its published version counted twice); two filters dropped sources before the inclusion catalog was built, defeating the selective-literature defence; claims had no passage locator (A-13, A-14).

**Rounds had no reason.** Continuation triggers were free-text gaps with no decision-relevance test; one counter advanced on both self-check failures and critiques (A-16). The concept implied that more rounds mean more rigour.

**Ambiguous terms.** "Round" (screening round vs LLM turn vs review exchange), "approved", "verified", "self-improvement", "promotion", "held-out" (the reference uses E3 "external holdout" to mean an external dataset about a material, not a policy holdout) each carried several meanings. The canonical glossary (`optimized_design.md` §0) fixes them.

## 2. Scientific and engineering weaknesses to address

- **Scientific.** The result kind must be stated: a unique all-pass compound under hard rules and a top-ranked compound under a score are different claims (ADR-11). Sensitivity ranges chosen after seeing outcomes cannot be called prespecified (ADR-14). Precision reported without coverage and abstention has a degenerate optimum (ADR-23). A successful tool call, a model prediction, and a measurement are different evidence kinds and must never be merged into one cell (ADR-08). Interpretive syntheses are the least reliable claim type and must not be the sole support of a criterion (design §4.9).
- **Engineering.** One sequence space for events; projections as pure folds; closed vocabularies generated from one registry; content-addressed artifacts; capability-based tool resolution; idempotency at the broker; fingerprint-based reuse; step-level failure isolation. Each is listed with its reference-code counter-example in `audit_report.md` §4.

## 3. Prioritized improvements

### 3.1 v1 essentials

These are needed to complete the rebuttal workflow and the surufatinib case honestly. Order is by dependency, not by effort.

| # | Improvement | Why essential | Component / decision |
|---|---|---|---|
| E1 | **Event Journal as the only source of truth**, closed State Registry, and Artifact and Vocabulary Registry | Every later record, diff, and progress figure is a projection; without this the rebuttal's "auditable closed loop" is unauditable | C1, C2, C3; ADR-01, ADR-02, ADR-18 |
| E2 | **Two-record criterion contract** (attribute + rule) with per-field provenance, `cutoff_basis`, four-state evaluation table, change records, registry invariants | The rebuttal promises rule definitions, directions, thresholds, units, applicability, and a recorded evolution; this is the record that holds them | C10; ADR-10 |
| E3 | **Per-candidate per-criterion Assessment and Reason records** with disqualifiers and coverage-gated roll-up | The acceptance target: every compound, every criterion, a reason | C11; ADR-11 |
| E4 | **Human Review Queue with attributed `hd_` records** and a trigger table; four disjoint approval fields | The rebuttal's "human experts review these proposed rule updates" is substantiated only by these records | C18; ADR-12 |
| E5 | **Evaluator-only historical-criteria artifact in the case configuration**, mechanical exclusion records, `reference_disclosed` derivation with alias scan and leave-one-out report, nine recovery mapping kinds | The CQA-recovery claim is falsifiable only if the list is firewalled; the surufatinib claim is honest only if the reference is disclosed and its influence measured | C10 comparison function, C19; ADR-13 |
| E6 | **Case Acceptance Register with two-stage preregistration**; no expected state pre-written; sensitivity ranges registered before evaluation | Prevents relabelling a tuned configuration as prespecified | C19; ADR-14 |
| E7 | **Capability-based tool registries**, typed result outcomes with absence and required-inputs manifests, thirteen-field provenance, broker-owned feedback with capability records and contract tests | Makes CDES genuinely optional and makes "the agents invoked tools and received structured feedback" true for every provider | C13; ADR-07, ADR-08 |
| E8 | **No-CDES coverage disclosure**: per-dimension `tool_coverage` and `interaction_estimate_provider` on every snapshot | Without it a lookup over a well-studied subset looks like a screen of 3,171 compounds | C12; design §16 |
| E9 | **Reporting tuple** (admitted n, precision undefined at zero, coverage, abstention by reason, guard rates, budget) emitted atomically | Prevents the empty-shortlist optimum and the "higher score means better" fallacy | C12; ADR-23 |
| E10 | **Claim Ledger with locations, claim type, verifier identity, independence groups, visibility manifests, search coverage** | Source-linked rationales that a reviewer can check; defence against selective-literature accusations | C9 |
| E11 | **Proposer–critic protocol with typed checks, external referents, deterministic adjudication, Independence Declaration, dissent records** | Replaces role-name independence with recorded independence; makes critique checkable | C7; ADR-05, ADR-06 |
| E12 | **Open-Question Register and LoopOutcome**; single-pass default; five adaptive triggers; stopping criteria | Every round has a reason; budget exhaustion yields `unresolved` | C8, C15; ADR-04, ADR-20 |
| E13 | **Reuse and Staleness Service** with fingerprints, dependency graph, Rerun Plan | Human edits must answer "what became stale and what must rerun" | C16; ADR-19 |
| E14 | **Progress Projection** with declared denominators, no cross-stage percentage, replay contract, freshness labels, heartbeat counter rule | The UI must never imply progress or approval that has not occurred | C17; ADR-03, ADR-28 |
| E15 | **Submission intake lifecycle** for human-supplied results | Uploads must not become top-tier evidence because the write succeeded | C18; ADR-22 |
| E16 | **Registered constants** for every number that affects a verdict | The criticism being rebutted is undocumented thresholds | design §8.4; ADR-25 |
| E17 | **Scoped Memory with delta operations and a store-level content-policy chokepoint**; no count-based procedures | Prevents "surufatinib was admitted n times, prefer it" from becoming standing guidance | C14; ADR-16 |
| E18 | **Evaluation Protocol Manifest and `claim_scope` block**, process-level scenarios S1–S14, policy arms P0/P0-noreview/P1/P2/P2-cap/P0+ | Distinguishes a working demonstration from evidence; answers the round question by measurement | C19; ADR-15 |
| E19 | **Case-configuration intake records** for the authors' inputs (3,171-compound identity list, eleven CQAs with completeness attestation, endpoint and unit conventions) | The primary case cannot run without them; they are input dependencies, not design gaps | case layer; U-07 |

### 3.2 Later extensions

| # | Extension | Precondition | Component / decision |
|---|---|---|---|
| X1 | Adaptive continuation (P2) evaluated at scale with matched budgets across more than one case | Pilot variance estimates; a second case; the P0/P0+ baselines run first | C19; U-01, U-02 |
| X2 | Offline GEPA/ACE-style strategy revision of role prompts, retrieval rules, and review checklists under the promotion conjunction | Protocol Manifest, pools, hidden evaluator functions, and a metric that does not leak the historical list | C19, C20; ADR-17 |
| X3 | A second domain adapter to exercise the port boundary | v1 core complete; a case with a different vocabulary | C3 ports |
| X4 | Optional predictors: an interaction-estimate provider (CDES or a structure-based predictor) and additional property predictors | Prerequisite list in design §16 met, including the leakage check against the reference candidate and recorded collision with the manuscript's comparator | C13; ADR-09 |
| X5 | A trained evidence-extraction model (endpoint, value, unit, conditions, direction from full text) | A stated minimum of reviewer-verified extractions; evaluation against the untrained baseline at matched budget on reviewer-minutes per accepted record | `resources.md`; ADR-17 |
| X6 | Lineage metrics and clade-style evaluation-budget allocation across strategy versions | At least one evaluated descendant per version; more than one case | C20; U-11 |
| X7 | Claim-level conformal citation guard as a hard gate | Domain-calibrated gold set (about 200 pairs) | C9 |
| X8 | Perturbation or cell-state tools as `dataset_context_lookup` providers | Matched pre-treatment samples and a data dictionary the package lacks | C13; `tools.md` |
| X9 | Cross-family critic as a standing requirement for all hard exclusions | Provider availability; recorded `independence_marker` until then | C7; U-05 |
| X10 | Automated per-role evidence hiding beyond evaluator-only artifacts | Evidence that it helps; logged omission paths | U-04 |

## 4. What must be added to support the intended manuscript claims

The historical rebuttal draft (`03_Provided_Rebuttal_Draft_EN.md`) makes seven claims in completed-work language. Each needs a record that does not yet exist; `rebuttal_alignment.md` maps them in full. In summary:

1. "We implemented an iterative, tool-augmented multi-agent system" requires the implemented core with a runnable Run Binding, journal exports (R9), and tool records (R6).
2. "Rules were refined through successive evidence–critique–human review cycles" requires confirmed rule-set versions with source-linked change records, critiques with typed checks, and `hd_` records (R1, R7). The word "successive" should be dropped unless more than one round actually ran; a single-pass run with several roles is the default.
3. "Refined toward the final 11 CQA criteria" must become "derived N criteria; recovery comparison against the historical eleven: k recovered, …" (R4). Eleven is a comparison reference, not a target.
4. "Agents invoked CDES and received numerical feedback" must become either an actual adapter record or the disclosure that no interaction-prediction backend ran and verdicts rest on curated measurements covering X of Y pairs (R6, coverage block).
5. "Sensitivity ranges were prespecified and tested" requires stage-1 and stage-2 preregistration events with hashes dated before the runs, and results for every configuration with equal prominence (R5).
6. "Surufatinib remains top-prioritized under the original configuration" must state the result kind (unique all-pass under hard rules vs top-ranked under a score), the decisive criteria, the unknown criteria and their causes, and the leave-one-out outcome dependence report (R2, R3). If it is not admitted under the prespecified baseline, the manuscript cannot claim the framework recovered the original prioritization.
7. "The revised manuscript provides the records" requires the records index R1–R9 to exist and be cited.

## 5. Claims that should be reworded regardless of outcome

- Replace "self-improving system" with "evaluated strategy revision with held-out checks and human promotion"; do not use "recursive self-improvement" (design §13.8).
- Replace "the agents validated" with "the agents assessed; experts approved" wherever an `hd_` record exists, and "no human review yet" wherever it does not.
- Replace "predicted binding" or "high affinity" with the value kind actually present (`measured`, `curated`, `predicted`) and its provenance.
- State the disclosed reference outcome: the case is a known-outcome reconstruction under a `reference_disclosed` derivation configuration, not a blind discovery.
- Replace any percentage of "progress" or "completion" in run descriptions with completed-versus-planned counts and the budget consumed.
- Where the result is an empty or single-entry recommended set with a large provisional tier, say so; it is the designed conservative outcome, not a failure.

Sources: `audit_report.md` §2–§7, `architecture_decisions.md`, `optimized_design.md` §0–§18, `literature_review.md` §4–§8, `agent_reports/evidence_and_policy.md`, `agent_reports/evaluation_and_improvement.md`, `agent_reports/tools_and_data.md`, `agent_reports/human_review_and_ui.md`, and `03_Provided_Rebuttal_Draft_EN.md`.
