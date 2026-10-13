# v1 Scope and Build Order

Coordinating agent, 13 October 2026. Design phase only; this is a recommendation for the user to accept or change. It removes nothing from the other documents: every deferred item stays specified and can be built later. Component ids, records, and task ids follow `optimized_design.md` Section 0 and `task.md`.

## 1. Why cut, and the rule used

The goal is the manuscript case: surufatinib on the task-scoped leaderboard and most of the eleven original CQAs produced, with every result honestly recorded (`case_study_protocol.md` §1). Since the handoff the design has gained ten decisions (ADR-30 to ADR-39), and each new feature drew between twelve and seventeen review findings. Every feature that is not on the route to the goal adds build time and risk before the first real result.

**Rule.** An item is in v1 when at least one of these holds:

1. the route to the two acceptance targets needs it;
2. a rebuttal claim the authors intend to make needs it;
3. without it a result would be untrustworthy (the historical-list firewall, provenance, replay).

Everything else waits.

## 2. What is in v1 and what waits

| Area | In v1 | Waits for v1.1 or later | Reason |
|---|---|---|---|
| Journal, State Registry, Artifact Registry, identifiers, Run Binding (C1–C3; T0.1–T0.6) | yes, with the canonical serialization of design §14.2 from day one | — | everything rests on them; retrofitting canonical bytes would change every hash |
| Task context, planner, budgets (C4–C6) | yes | per-loop-class matching for arm comparisons | |
| Proposer, Blind Critic, deterministic validator and adjudicator (C7) | yes; one cross-family critic if a second provider is available (U-05) | escalated model adjudicator (disputes go to the review queue) | fewer moving parts; the queue exists anyway |
| Open-Question Register (C8) | records open questions; `human_request` rounds | adaptive continuation (P2) | P0 single pass is the baseline (ADR-04) |
| Evidence Ledger, identity service (C9) | yes | — | every cell needs evidence and identity |
| Criterion Registry with recall-first enumeration and consolidation (C10, design §8.3) | yes | — | route to the CQA-recovery target |
| Historical-list firewall: evaluator-only intake, case-source exclusion, exposure declarations, access log, encryption of evaluator-only content (design §8.6, §14.1) | yes | — | without it a recovery number means nothing |
| Per-candidate assessor, full sweep, leaderboard (C11, C12; T4.1–T4.4) | yes | — | route to the leaderboard target |
| Tool Broker with the no-CDES providers (C13; `tools.md` §2.1–2.9) | yes | Boltz-2; CDES adapter | both optional by design |
| Scoped memory (C14) | store, content-policy chokepoint, `cold` and `frozen` modes, person-written and tool-recovery drafts, approval through the review queue | `warm` recall, the Reflector role, procedure trials | acceptance-bearing runs are `cold` or `frozen` anyway (ADR-39); the Reflector's value is open (U-16) |
| Run control, checkpoints, resume (C15) | yes | — | |
| Run chains (design §6.8) | linear chains: continue, rerun, refresh | branches; continuing into another group | branches multiply records and review cases |
| Reuse and staleness (C16) | yes | — | continuation and resume depend on it |
| Progress and replay (C17) | yes | — | |
| Human review queue (C18) | yes, with claims and exposure declarations | — | expert confirmation gates the rule set |
| Evaluation (C19, C20) | Protocol Manifest, two-stage preregistration, Case Acceptance Register, recovery comparison, sealed `final` pool, pilot E0 | policy-arm comparisons (E2 to E4), promotion conjunction, strategy archive operations, lineage metrics | the case needs the first group; claims about agent policy or self-improvement need the second |
| Run groups (design §6.9) | create, switch per session, archive | moving and copying tasks between groups | |
| Operator surfaces (design §2.4, §14.1) | profile X: a Linux service host, the terminal client, and Chrome on Windows through an SSH port forward; profile L for development | profile W (native Windows host) and its launcher | profile X already gives a Linux terminal and Chrome on Windows; profile W adds Windows sleep, file-locking, antivirus, and tool-availability work |
| Sessions and roles | one host account; expert decisions with interactive entry and `recorded_attestation` | authenticated accounts; network serving (U-15) | |
| Process scenarios | S1–S8, S10, S11 on one Linux host, S13 for linear chains | S9 (strategy updates), the Windows half of S12, the Reflector and branch parts of S13 and S14 | |

**What v1 can and cannot support in the rebuttal.**
- **Can support:** both case targets; the process-level claims of `rebuttal_alignment.md` Paragraphs 1 and 2; the sensitivity claims of Paragraph 3.
- **Cannot support:** a claim that extra rounds or evolved strategies improve results. The evaluation row of C2.5 (policy arms at matched budget) stays **planned**, and wording such as "self-improving" must stay conditional.

## 3. Build order: one thin end-to-end slice first

`task.md` builds layer by layer (M0, then M1, and so on). The first working run would then arrive only after most of the system exists, and the two biggest unknowns would surface last: whether derivation recovers criteria at all, and what one compound × criterion cell costs. The slices below each end in something that runs.

| Slice | Contents (task ids) | Exit check |
|---|---|---|
| A. Walking skeleton | about 20 public compounds, two criteria proposed and confirmed through the queue, one identity provider and one curated bioactivity source: T0.1–T0.6, T0.8, T1.1, T1.3–T1.5, T2.1–T2.3, T2.6, T2.8, T3.1–T3.3, T3.5 (two providers), T4.1, T4.2, T4.4, T5.1 (minimal), T6.1, T6.10 (minimal), T6.11 (watch, board, candidate, review) | a run completes; every cell traces from verdict to claim to source location; replay reproduces `projection.hash`; a stop mid-sweep resumes with correct reuse |
| B. Derivation pilot on external cases (E0) | recall-first enumeration and consolidation, proposer–critic, literature retrieval, property estimation: T1.6, T1.7, T1.9, T2.4, T2.5, T3.4, T3.5 (remaining providers), T7.1 (pilot manifest), T8.15 | on two or three published external cases: recovery against their published criteria lists and per-cell cost per rule are measured; the full-universe budget is estimated (U-13); the derivation strategy is frozen before the primary case |
| C. Firewall, preregistration, review | T1.2, T1.8, T2.9, T5.1 (full), T5.2–T5.4, T8.3, T8.13, T8.14, T8.16, T0.9, plus the encryption and access-log parts of T0.7 | S2, S4, S5, S6 pass; a rehearsal with a dummy list shows only the enumerated readers in the access log |
| D. Scale and surfaces | T2.7, T2.10 (linear), T2.11 (create, switch, archive), T4.3, T6.2–T6.9 served on Linux, T6.13 (one host), T6.14, T6.15 | S7, S8, S11, and the linear S13 cases pass; a full-universe rehearsal on a public library of similar size finishes inside its registered budget |
| E. The primary case, once | T7.5, T8.1–T8.12 | records R1–R9 exist; recovery reported in both views; the acceptance register check is complete |

Slice B is the main decision point. If recovery on the external cases is poor, improve the derivation strategy on further external cases. Never adjust it on the primary case, which is touched once.

## 4. Inputs to request now

Nothing about the case can be checked without these. The list can be sent as it stands.

**From the authors**
1. The eleven CQAs: name, definition, dimension, threshold or cutoff with unit, direction, the data source used, and whether the list is complete. Delivered to the evaluator only, never to anyone who will confirm criteria.
2. The identity list of the 3,171 compounds (identifiers, source, and version or date), and how the 140-binder subset was produced.
3. The exact objective wording and where it appears in the manuscript.
4. Every document that states or quotes the criteria list: manuscript versions, supplement, preprints, theses, slides, code repositories.
5. Who has seen the list, among everyone who might confirm criteria.
6. The threshold for "most" of the eleven, and which kinds of similar match count, agreed before any run.
7. The rebuttal deadline.

**From experts**
8. At least one expert who has not seen the list and can confirm criteria. Without one, the `independent` recovery view is empty and the strongest statement ("the system derived the criteria") is unavailable.
9. The coverage-floor value and the unit conventions for the five targets.

**From the operator**
10. Model providers with quotas, ideally two model families so the critic can be independent, and an overall budget.
11. Two or three published external cases with explicit criteria lists for slice B.

## 5. Decisions this scope asks for

| Decision | Recommended | Consequence if not taken |
|---|---|---|
| v1 surfaces | profile X (Linux host, terminal, Chrome on Windows over SSH) | profile W adds the Windows-host work of ADR-36 before the first result |
| Agent-policy and self-improvement evaluation | after the primary case | adds E2–E4 and C20 operations to the critical path; needed only for claims about agent policy |
| Run chains | linear only | branches add tree navigation, review cases, and snapshot bookkeeping |
| Reflector | after a procedure trial shows value | cost without evidence of benefit (U-16) |
| Build order | slices A–E | layer-by-layer order delays the first result and the two biggest unknowns |

## 6. Design gaps found while scoping

These were missing from the design when this scope was written; after the consolidated review they were added (design §2.3 `role_bindings[]`, §14.3; ADR-40; task T0.9).

| Gap | Why it matters | Proposed rule |
|---|---|---|
| G1 Credentials | model-provider and data-source keys are mentioned only in passing (`tools.md`, `resources.md`); traces store raw model input and output, and exports leave the store | keys live in the host account's operating-system credential store; they never enter the journal, traces, exports, agent context, provenance blocks, or the operator log; the broker injects them at dispatch; trace capture redacts them; rotating a key changes no record |
| G2 Backup and restore | the store root must be local and unsynchronized (design §14.1), so nothing copies it unless a backup does; losing the evaluator's key makes the recovery comparison impossible | scheduled encrypted snapshots of the store root (the append-only journal makes this incremental); a restore drill before slice E; the evaluator's key held by the evaluator with a recorded escrow arrangement |
| G3 Exact model versions | roles are bound to model adapters at run start (`tools.md` §8), but the Run Binding (design §2.3) records neither the adapter per role nor the exact model version or decoding settings; providers retire models | the Run Binding records `role_bindings[] {role, adapter_id, provider_family, model_id, model_version, decoding_parameters}`; a run with a retired model cannot be resumed and continues in a run continuation that binds a new strategy version, labelled as such |

Sources: `optimized_design.md` §0–§18; `architecture_decisions.md` ADR-04, ADR-24, ADR-33, ADR-35 to ADR-39, U-05, U-13 to U-16; `task.md`; `evaluation_plan.md` §2, §12; `rebuttal_alignment.md` §2; `post_handoff_decisions.md` §4.
