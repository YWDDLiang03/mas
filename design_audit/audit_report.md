# Audit Report: Agent-Centered, Self-Improving Multi-Agent System

Coordinating agent, 12 October 2026. Prioritized findings, evidence, recommended changes, and unresolved issues from a multi-agent design audit. Design phase only; no code was written and no screening, ranking, or experiment was executed. The recommended architecture is in `optimized_design.md`; decisions in `architecture_decisions.md`; the process record in `collaboration_log.md`. Revisions made after handoff, on 13 October 2026, are summarized in [post_handoff_decisions.md](post_handoff_decisions.md).

## 1. Scope, method, limits

**Scope.** Audit the package's concept of an evidence-driven, self-improving multi-agent system for candidate prioritization; optimize it into a detailed agent-first architecture whose first acceptance case is the manuscript rebuttal (derive criteria that recover most of the historical CQAs with evidence-linked reasons; admit surufatinib onto the task-scoped leaderboard with per-criterion reasons; assess every compound individually), without hard-coding the answer.

**Method.** The coordinator read all 36 package files, extracted the manuscript's screening passage, cloned the Agentic Doping repository from GitHub and verified that the packaged excerpts match the snapshot commit `0007ad10` (tip of `cloud_deployment`, 53 commits ahead of `main`), and cloned six further open-source repositories read-only. Eight workstream subagents produced bounded reports; eight cross-review assignments were executed by the same agents on peer reports, producing nine appended cross-review sections; one inspector appended a Wave 1.5 inspection of three literature-selected repositories; an independent reviewer checks the integrated set (`agent_reports/final_integrated_review.md`). Assignments, timing, disputes, and resolutions are in `collaboration_log.md`.

**Limits.** The five Windows-path local projects named in the prompts were not on this host; per the user, Agentic Doping was inspected from GitHub and the other four were treated as outdated and replaced by newer open-source references (deepseek-harness, ARIS, DGM, hsi, ACE, HGM). The literature search cutoff is 12 October 2026; reading depth is recorded per source and several 2026 results are workshop papers or preprints. The manuscript's eleven individual CQAs are not enumerated in its main text and the 3,171-compound identity list is not in the package; both are input dependencies. No repository code was executed; UI behaviour of the reference application was read from source, not run. Biology was investigated only to the depth needed for interface contracts.

## 2. Prioritized findings

Severity: **H** blocks the acceptance target or the honesty requirements; **M** degrades quality or cost; **L** cosmetic or deferred.

| Id | Finding | Sev | Source | Recommended change | Where resolved |
|---|---|---|---|---|---|
| A-01 | No per-candidate per-criterion record exists in the concept or the reference code; the acceptance target has no home. | H | WS1 §5.1 (AD `models.py` 29-60) | Assessment record + structured Reason record with disqualifiers as the atomic unit; coverage-gated roll-up. | design §4.11, ADR-11 |
| A-02 | Human approval is a software field everywhere inspected (self-certified `approved`, untyped dict, default-pass gate, hard-coded `approved_by="human"`). | H | WS1 §7.1, WS4 F8, WS7 F10, WS5 STEP 1 | Four disjoint approval fields; `hd_` records written only via the review queue; UI shows "no human review yet". | §12, ADR-12 |
| A-03 | Reviewer independence is asserted, not enforced: on the default tool-harness path the reviewer sees the proposer's rationale; same-family review is correlated review. | H | WS7 F6 (AD `dual_agent/agent_harness.py` 920-955, `proposer.py` 121-145), WS2 A2 as revised, WS6b F5 | Per-critique disclosure and per-decision Independence Declaration; cross-family or human for consequential decisions; `revision_check` cannot raise the level. | §5.4, ADR-06 |
| A-04 | The historical eleven CQAs, if readable by deriving agents, make "recovery" measure copying; if the sole acceptance-eligible configuration is fully reference-blind, acceptance becomes impossible. | H | WS5 F8, WS1 §8, WS1↔WS5 cross-reviews | Evaluator-only artifact in the case configuration with mechanical exclusion records; derivation `reference_disclosed` with alias scan and leave-one-out report; `reference_blind` as a sensitivity arm. | §8.6, ADR-13 |
| A-05 | Evaluator exploitation is the default failure mode of every self-improvement loop inspected or read (hidden-detector bypass; 73.8% proxy-only gains; held-out gaps). | H | WS6b F1 (S1 App. H, S32, S33), WS7 §5 | Hidden evaluator functions, held-out composed checks, evaluator epochs, proxy-vs-held-out gap; reference-outcome frequency excluded from promotion. | §13, ADR-15 |
| A-06 | No held-out evaluation or measured strategy promotion exists in any inspected repository; the reference's only numeric signal is an acceptance-credited usage counter. | H | WS5 STEP 1, F6; WS7 F8 | Evaluation and Promotion Authority with a mandatory manifest, pools, promotion conjunction, LCB over repeats, rollback. | §13, ADR-15 |
| A-07 | Execution state is three labels remapped by presentation; `exhausted` becomes "sent after revision limit"; the version counter restarts on resume. | H | WS2 H2/C1, WS4 F6, WS7 F1, recorded run | State Registry; journal `seq` as the only sequence; UI mapping table; `unresolved` never implies advancement. | §4.2, ADR-02 |
| A-08 | The durable journal is written but never read; UI truth is a mutable snapshot; heartbeats mutate the completion record; denominators change five times in one run; ETA extrapolates across them. | H | WS4 F1–F5, WS7 §2.1 | Journal as source of truth; replay contract; counter rule as a contract; three-level progress with declared denominators; no cross-stage percentage. | §4.1, §11, ADR-01, -03, -28 |
| A-09 | One provider path cannot return tool results to the model yet reports itself tool-capable; the committed sample runs used it. | H | WS2 D1, WS7 §2.6 (AD `llm_client.py` 139-151, 342-411) | Model Adapter Capability Record with contract tests; broker-owned loop; synthetic `unknown_outcome` results; explicit degradation. | §7.6, ADR-07 |
| A-10 | Tool contracts are inline literals, provenance is three fields, four distinct absences collapse into one null; an optional backend has nowhere to plug in. | H | WS3 F1, F2, F4 | Capability-based registries; thirteen-field provenance; typed absence with required-inputs manifest; `claim_strength_ceiling`. | §7, ADR-08 |
| A-11 | A human upload becomes top-tier evidence with a perfect score because the file write succeeded. | H | WS3 F3 (AD `feedback/ingest.py`) | Submission lifecycle; provisional claims; admission by a non-submitter reviewer. | §12.4, ADR-22 |
| A-12 | The fused fixed-vocabulary target contract silently drops proposals, cannot express hard exclusions, units, or applicability, and hard-sets evidence level. | H | WS1 §2.1 (AD `analyze.py` 680-750) | Two-record criterion contract; four-state table; nothing dropped silently. | §4.10, ADR-10 |
| A-13 | Independence of support is inferred from distinct cache keys with a fixed bonus; a preprint plus its published version counts twice. | H | WS1 §4.3 (AD `quality.py` 653-657) | Independence groups; support counted over groups; preprint/published pairs collapse. | §4.9 |
| A-14 | Two filters drop sources before the prompt-inclusion catalog is built, defeating the selective-literature defence. | H | WS1 §4.4 | Catalog from the unfiltered set; visibility manifest with typed omission reasons as a publication gate. | §4.9 |
| A-15 | Precision-first admission has a degenerate optimum (admit nothing) unless coverage and abstention are reported in the same row; the coverage floor is a precision lever unless registered. | H | WS5 F7 and cross-review | Atomic reporting tuple; precision undefined at zero admissions; floor registered inside the admission-predicate hash. | §4.12, ADR-23, ADR-11 |
| A-16 | Continuation triggers are free-text gaps with no decision-relevance test or durable record; the loop budget conflates self-correction with critique. | H | WS2 C3, B1 (AD `gap_discovery.py`, `loop.py` 219-224) | Open-Question Register with referent and expected decision change; separate loop budgets; LoopOutcome on every loop. | §4.8, §6, ADR-04, -20 |
| A-17 | Candidate-specific "avoid X" skills are auto-authored from rejection counts, bypassing the content guardrail. | M | WS2 F2, WS5 F5, WS7 F7 (AD `harness/memory.py` 422-457) | Store-level content-policy chokepoint; counts never create procedures. | §10.4, ADR-16 |
| A-18 | Memory gains in the literature are conditional: context collapse on rewrite, retrieval precision collapse with pool size, negative cross-role transfer; human-curated procedures were the only uniformly positive configuration. | M | WS6a F5 (S7, S9, S10), WS6b F3 (S11, S12), WS7 F11 | Itemized delta memory with attributed counters, pool caps, human-curated promotion, rule-reversal test. | §10, ADR-16 |
| A-19 | Self-modifying harness evolution costs USD 13k–22k and one to two weeks per run and has not beaten matched-budget test-time scaling on held-out tasks. | M | WS6b F2, F7 (S9, S20, S1, S3, S6) | Excluded from v1; evaluated prompt/playbook/procedure revision only. | §13.8, ADR-17 |
| A-20 | Orchestration and verification are where multi-agent systems fail (43.7% specification/design, 24.45% verification, 67.7% orchestrator); delegation carries no output contract or boundary. | M | WS6a F1, F2 (S1, S2, S3) | Delegation brief fields in the plan step; result returns only to the planner; typed critique checks incl. candidate-symmetric scrutiny. | §4.5, §5.3 |
| A-21 | Checkpoint reuse is file-existence based; nothing is ever marked stale; a human edit cannot answer "what must rerun". | M | WS2 E2, WS4 F9 | Reuse and Staleness Service with fingerprints, dependency graph, Rerun Plan. | §4.16, ADR-19 |
| A-22 | History exists as snapshots; no semantic field-level diff links a change to its cause. | M | WS4 F7, WS7 F4 | Change records with before/after and `cause`; difference view as a projection. | §4.12 |
| A-23 | A tool failure for one candidate ends the run; an unhandled candidate exception disappears from the leaderboard. | M | WS2 D2 (AD `recommend.py` 681-689, 643-648) | Step-level isolation; every candidate leaves with a row; `run_degradation[]`. | §6.4, ADR-21 |
| A-24 | Numeric decision constants are undocumented in code and indistinguishable from scientific cutoffs. | M | WS1 §6.1 | Registered constants with scope and cutoff basis. | §8.4, ADR-25 |
| A-25 | The spine's component 13 named artifacts but no decision rule, pool discipline, or claim boundary. | M | WS5 F12, WS6a cross-review | C19 re-specified with declared interfaces; `claim_scope` on every report. | §13 |
| A-26 | Unit ambiguity is stored as a comment; the supplied dose-response table pre-loads the same failure (units and endpoint meanings undocumented; portal pages returned HTTP 410). | M | WS3 F7 | Unit gate: unknown-unit values are never consumed by the assessor; datasets stay `context_only`. | tools.md, resources.md |
| A-27 | The no-CDES route is coverage-limited and must say so numerically or it will look like a screen when it is a lookup. | M | WS3 F8 | Per-dimension `tool_coverage` on every snapshot; `interaction_estimate_provider` disclosure. | §16 |
| A-28 | The obvious optional affinity predictor is the one the manuscript names as CDES's comparator. | L | WS3 F9 | Record the collision in the case configuration; prohibit inference about relative merit. | §16 |
| A-29 | Controlled vocabularies are duplicated and have drifted (enum vs JSON schema). | L | WS1 §9.2 | Vocabulary registry generating schemas and validators. | §4.3, ADR-18 |
| A-30 | Raw model I/O is the default live view; rationale fields render as joined text with no evidence navigation. | L | WS4 F10 | Concise decisions and sources by default; traces behind a role-gated panel; claim objects link to passages. | §11.3 |

## 3. Findings by theme (short form)

**Objective → criteria → decision.** The concept lacked a task-context record between flexible input and evidence requests (WS1 §1); the criterion contract must separate attribute from rule and carry per-field provenance; missing, inapplicable, conflicted, and qualitative are four states, not "fail"; a reason is a record with disqualifiers; the historical criteria are a firewalled comparison artifact. All adopted.

**Collaboration.** The reference is a proposer, two heterogeneous critics, and a deterministic gate rather than a triad; that shape is the right default. Independence must be recorded per exchange; critiques must carry external referents; debate and extra rounds without new information are non-progress (WS6b §5). All adopted.

**Tools.** Capability-based registries, typed results with absence, thirteen-field provenance, provider-agnostic feedback with contract tests, CDES optional. Adopted; status vocabularies merged in cross-review (ADR-08).

**Memory.** Three independent trust axes, itemized delta entries, store-level policy, human-curated promotion, no count-based skills. Adopted.

**Run control and observability.** Journal as truth, State Registry, LoopOutcome, Open-Question Register, Reuse and Staleness Service, three-level progress, replay contract, counter rule. Adopted.

**Human review.** Trigger table, attributed `hd_` records, submission lifecycle, queue with precomputed consequences. Adopted.

**Leaderboard.** Task-scoped snapshots with result kind, reporting tuple, tool coverage, change records; four states; abstention valid. Adopted.

**Evaluation and self-improvement.** Protocol manifest, arms P0/P0-noreview/P1/P2/P2-cap/P0+ (two variants), Round Progress Record, pools, promotion conjunction with LCB and noise leeway, hidden evaluators, claim scope. Strong RSI explicitly not claimed. Adopted.

**Rebuttal alignment risks.** Completed-work wording in the historical draft; a unique all-pass claim versus a top-ranked claim; "eleven" as a target count; CDES as a dependency; sensitivity ranges chosen after outcomes. Each is mapped to a record and an acceptance condition in `rebuttal_alignment.md`.

## 4. Agentic Doping reuse verdicts (decision of record)

| Component (AD path at `0007ad10`) | Verdict | Reason |
|---|---|---|
| Bounded proposal/review loop (`dual_agent/loop.py` 209-292) | Reuse as pattern | Correct exhaustion semantics; split the shared counter; add LoopOutcome |
| Deterministic critic plus combination gate (`reviewer.py` 474, 601-686) | Reuse as pattern | Uncorrelated check, hard veto, evidence-free score cap |
| Withheld-input critic (`harness.py` 1121-1124, file-chat path; `review_fixed_proposal`) | Reuse as pattern for those paths only | Default tool-harness path discloses the rationale |
| Citation cross-check and downgrade-only calibration (`reviewer.py` 206-422) | Adapt | Mechanism sound; classes and thresholds are domain data |
| Versioned proposal/review artifacts (`loop.py` 214-233, 294-300) | Adapt | Keep versioning; replace dictionaries with the envelope; add field-level diffs |
| Anthropic tool-feedback loop (`llm_client.py` 443-481) | Adapt behind a neutral contract | Results and typed errors return; add exhaustion reporting |
| Codex bridge one-shot path (`llm_client.py` 342-410, 139-151) | Redesign | Dispatches without returning results while reporting tool capability |
| Progress and event writer (`run_dir.py` 91-143) | Redesign the record, keep the discipline | Atomic replace, append-only journal, server-side finalization are right; vocabulary and counter are not |
| Checkpoint continue/resume (`recommend.py` 207-238) | Redesign | File-existence reuse; no fingerprint, staleness, or reuse record |
| Per-candidate ledger (`ledger.py`, `models.py`) | Adapt | Append-only and typed failures are right; add `seq`, actor, rule version, typed human review, per-criterion rows |
| Evidence ladder and candidate status (`evidence_ledger/enums.py`) | Redesign | One ordinal conflates source class, independence, measurement type; status is pipeline progress |
| Cross-run leaderboard (`leaderboard.py` 220-233) | Redesign | Prohibited universal ranking; add snapshot id, rule version, ordering method, four states |
| Scoped memory store (`memory.py` 64-66, 207-218, 299-333) | Reuse as pattern | Group and role scoping; provisional recall limits; raw verdicts non-persistent |
| Automatic skill promotion (`memory.py` 422-456) | Redesign | Candidate-specific prompt guidance bypasses the policy |
| Content policy for procedures (`skill_policy.py` 140-213) | Adapt | Keep violation-code contract; vocabulary to the adapter; add positive-form requirement |
| Post-run reflection (`reflection.py`) | Reuse the mechanism; recall governed by memory mode, review state, and the firewall rules (design §10.2, §10.5) | Honest skip becomes a counted outcome |
| Gap-directed retrieval (`gap_discovery.py`) | Adapt | Backward flow is valuable; gaps become durable register entries |
| Human verification gate (`harness.py` 84-92) | Redesign | In-process pass-through cannot represent `waiting_human` |
| Fixed-vocabulary target contract (`analyze.py` 680-750) | Adapt fields, redesign contract | Direction, rationale, computation method are useful; derivation must be open-ended |
| Wet-lab ingest (`feedback/ingest.py`) | Redesign | Perfect score on write |
| Keyword goal table and fallback (`analyze.py` 33-122, 1110-1117) | Do not transfer | Smuggles undocumented priors |
| Prompt-inclusion audit and context manifest (`visibility.py` 296-334; `analyze.py` 900-950) | Reuse as design | Best defence against selective-literature claims, once pre-catalog filters are logged |
| Scientific identity key (`quality.py` 687-695); exact-phrase normalizer (`quality.py` 173-216); transfer-scope rank (`visibility.py` 24-76) | Reuse as patterns | Become the duplicate-criterion test, name normalization, and `scope_match` |
| Invariant audit with bounded repair (`analyze.py` 215-282, 761-810) | Reuse as pattern | The critic loop the registry needs |
| Server-side finalization and reaper (`server.py` 403-446, 1255-1283) | Adopt | Disk never stays `running` |
| Disposition remap (`server.py` 980-989); ETA over changing denominators (`App.tsx` 3108-3125) | Avoid | Misrepresent state and progress |
| Report iteration with `parent_version` (`report_iteration.py` 270-290) | Adapt | Add change summary; keep distinct from rounds |

## 5. Lessons from the other inspected repositories

| Repository | Adopt | Adapt | Avoid |
|---|---|---|---|
| deepseek-harness (`d7432673`) | typed event taxonomy with `{type, seq, time, data}`; durable `tool/call`–`tool/result` with synthetic results for unanswered calls; crashed turn closed not truncated; pure-fold projections; tool contract with output schema, cancellation, timeout; goal `blocked` with typed reason | — | two-value agent status and free-text job progress as user-facing vocabulary |
| ARIS (`26b95cfa`) | file-paths-only reviewer input and cross-family rule; Type-A execution gates vs Type-B quality gates ("a loop can drive, it cannot acquit"); `done` vs `accepted` requiring a verdict id and non-same-family reviewer; deterministic evidence pre-check with "verified ≠ correct"; verdicts computed by code from per-point counts | stall ladder on zero new findings → `no_actionable_step` | a single AI-score trajectory as evidence of improvement |
| DGM (`a565fd2d`) | staged evaluation budgets; explicit noise leeway; never-delete archive (scoped to strategy versions) | failure-class-directed improvement proposals | selection and reporting on the same sets; hidden-detector bypass (App. H) |
| hsi (`97a022b9`; license: README says MIT, no license text) | frozen, non-copied final selector outside the evolvable surface; LCB reward over episodes; stratified dev/val/test with fixed seeds, test touched only post-run; per-call usage log by scope; hypothesis with falsification criteria | max-of-evaluations ranking → LCB across repeats; LLM commit pool → selection by recorded metrics | in-place overwrite of past lessons |
| ACE (`82709de0`) | identified delta items with helpful/harmful counters; append-only operations, no whole-text regeneration | embedding grouping deterministic, LLM merge human-reviewed | token budget as prompt text only; label-driven branching inside a "no ground truth" mode |
| HGM (`013872d9`) | separate post-run evaluation on a different split | clade-level selection as a warning that own score predicts lineage poorly; uncertainty-based evaluation budget allocation | no token or cost accounting |

## 6. Literature-driven decisions

| Mechanism | Verdict | Basis |
|---|---|---|
| Typed delegation briefs and structured result returns | adopt | S1 43.7% specification failures; S2 67.7% orchestrator; S3 |
| Objective-level verification with typed checks | adopt | S1 +15.6%; S23 verification 13–87% more success |
| Itemized delta memory with counters and promotion gate | adopt | S7; S8; S9; S10; S11; S12 |
| Schema-based tool contracts with structured diagnostics; idempotency keys | adopt (interface-level) | S16; S17 |
| Append-only journal with intent/effect separation and hash-verified projections | adopt | S19; S1/S2/S20 need traces |
| Cost-controlled, tool-standardized, log-inspected evaluation with trivial baselines and pass^k | adopt as requirement | ABC, HAL, AstaBench, τ²-bench |
| Claim-type-aware ledger with verifier identity | adopt | S28 (57.9% vs 85.5%); S29 (3–18% verifier-relative) |
| Offline GEPA-style prompt optimization under a held-out gate | adopt as candidate; evaluate first | S15; S6 prompts before topology |
| Persistent epistemic state and preregistration | adopt | S30 |
| Hidden evaluators, evaluator epochs, proxy-vs-held-out gap | adopt | S1 App. H; S32; S33; S19 |
| Independence markers on verdicts; cross-family for consequential decisions | adopt | S29; S30; S31 |
| LCB promotion with noise leeway; lineage archive | adopt | DGM, HGM, AIDE², hsi |
| Learned RL orchestration or routing | unsupported complexity | S4, S5 need trajectory sets that do not exist |
| Automatic topology or workflow evolution; self-modifying code | defer | S9 +0.0 held-out; S20; USD 13k–22k per run |
| Large skill libraries; multiple LLM proposers for diversity | avoid | S9 precision collapse; S30 hivemind |
| Co-evolving evaluators; weight training | defer | S19 work in progress; governing prompt |

## 7. Unresolved issues and expert dependencies

See `architecture_decisions.md` U-01 to U-16. In summary: the held-out check for criterion derivation without labels; affordable repeats and variance; the coverage floor and every cutoff basis; whether exploratory mode may remove a supplied scope entity; the 3,171-compound list and the authors' eleven CQAs as inputs; cross-family critic availability; transport and durability details; heartbeat journaling; approval granularity; lineage-based selection; unit-conversion ownership; the full-sweep budget (U-13); tools that run only on Linux on a Windows host (U-14); several people on one host and a Linux terminal for a Windows host (U-15, awaiting the user); whether the Reflector is worth its cost (U-16). None blocks the architecture; each is recorded as a review-queue item, a registered constant, or an implementation choice with a stated default.

## 8. Pre-handoff checklist self-assessment

| Item (governing prompt, final paragraph) | Self-assessment | Where |
|---|---|---|
| Method agent-centered; v1 purpose is the rebuttal and surufatinib's priority | yes; acceptance target stated and threaded through every document | design §1, §17 |
| Rebuttal-to-design mapping complete | yes, claim by claim with current vs planned marking | `rebuttal_alignment.md` |
| End-to-end case protocol complete | yes; inputs, stages, records, recording rules, no invented result | `case_study_protocol.md`, design §17 |
| Core, adapter, case configuration separated | yes; ports, binding, import rule | design §0, §2 |
| No implementation code | yes; declarative schemas, tables, diagrams, wireframes only (checked by grep) | all |
| Architecture sufficiently detailed | yes; twenty components with field lists, states, failure behaviour | design §4–§16 |
| Live progress and evidence-linked histories specified | yes | design §11, `ui_ux_spec.md`, `iteration_and_provenance_spec.md` |
| Core works without CDES | yes; CDES optional adapter with absence behaviour | design §16, `tools.md` |
| Actual multi-agent work and current literature documented | yes; eight agents, six cross-reviews, two literature reports with cutoff and depth | `collaboration_log.md`, `literature_review.md` |
| Flexible inputs and task-scoped leaderboards | yes | design §4.4, §4.12 |
| Surufatinib not a fixed answer; CQAs not forced to eleven; target discovery optional | yes | design §1, §8.6, §18 |
| Additional rounds have triggers and stopping criteria | yes | design §4.8, §6.3 |
| Intended rankings or experiments not reported as completed | yes; templates only | design §17 |

The independent reviewer's verdict on these items is in `agent_reports/final_integrated_review.md`: eleven items PASS, four PARTIAL (rebuttal mapping claim count; objective text labelled verbatim; a domain-shaped capability list in the core; wireframe numbers without placeholder disclaimers), none FAIL; all four were fixed in the texts after the review, and the fixes are recorded in `collaboration_log.md` §7.3. The self-assessment above is the coordinator's and should be read with that review, not instead of it.
