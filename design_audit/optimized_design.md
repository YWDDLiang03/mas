# Optimized Design: Agent-Centered, Self-Improving Multi-Agent System for Evidence-Driven Candidate Prioritization

Coordinating agent, 12 October 2026. Design phase only: this document specifies architecture, interfaces, states, persistence, and failure behaviour. It contains no implementation code. Field lists are declarative specifications; nothing here reports an executed screening, a ranking, or an experimental result.

This is the canonical design document. Where any other file in `design_audit/` uses a name for a component, record, state, or identifier, the name defined in Section 0 governs. The design integrates nine workstream reports and their cross-reviews (see `collaboration_log.md`); decisions and their alternatives are recorded in `architecture_decisions.md`.

---

## 0. Canonical glossary and identifier scheme

### 0.1 Layers

| Layer | Owns | Must never own |
|---|---|---|
| **Core** (reusable agent core) | planning and delegation, collaboration protocol, tool brokering, evidence ledger, criterion registry, per-candidate assessment, leaderboard lifecycle, scoped memory, run control, event journal and projections, human review queue, evaluation and strategy promotion | domain vocabulary, thresholds, entity lists, provider-specific behaviour |
| **Adapter** (domain adapter; v1 = drug prioritization) | vocabularies (compound identity schemes, target identity, assay endpoints, units, aliasing rules), evidence-source and tool adapters, criterion templates (definitions with empty cutoffs), deterministic validators, content-policy lists, expert-review requirements | orchestration, memory, provenance mechanics, leaderboard mechanics |
| **Case configuration** | the objective text, mode, scope entities, candidate universe, seed candidates with reference-outcome disclosure, constraints, evidence cutoff, historical-criteria comparison artifact, registered constants, baseline and alternative configurations, budgets | anything reusable across cases |
| **Host infrastructure** (not an agent layer) | the service host, the Operator API, sessions (`ses_`), command records (`cmd_`), role grants, request checks, the operator log (Sections 2.4, 14.1) | any C1–C20 record or any decision about one; domain vocabulary; agent context |

Import rule: Core never imports Adapter modules; it resolves adapter capabilities through registries keyed by `adapter_id` and `adapter_version`. The Case configuration is bound once at run start into an immutable **Run Binding**; changing a bound field requires a new run (a run continuation when a person continues; Section 6.8).

### 0.2 Core components (twenty, in seven groups)

| Id | Component | One-line responsibility |
|---|---|---|
| **C1** | Event Journal | Append-only, store-assigned monotonic `seq` per stream (Section 2.4); the sole source of truth; every other state is a pure projection |
| **C2** | State Registry | Closed vocabularies for execution, exchange, candidate, result, value-kind, review, and change-kind labels; `ui_label` mapping; `implies_admission` flag |
| **C3** | Artifact and Vocabulary Registry | Artifact Envelope and payload schemas; controlled vocabularies with versions; generated validators and labels |
| **C4** | Task Context Normalizer | Flexible inputs into an explicit, versioned task context; conditional and exploratory modes; unknowns; no keyword fallback |
| **C5** | Planner/Delegator | Plan record with steps, owners, budgets, completion predicates; Delegation Brief and Result Return |
| **C6** | Budget and Cost Accountant | Per-step and per-loop-class budgets; matched-budget accounting; cost per changed decision |
| **C7** | Proposer–Critic Protocol | Typed proposal, critique with external referents, revision, deterministic adjudication with escalation, Independence Declaration, dissent |
| **C8** | Open-Question Register | Continuation triggers with expected decision change; attempts and information gain; stopping criteria inputs |
| **C9** | Evidence Ledger | Source, Claim, Location, independence groups, claim type, verifier identity, visibility manifest, search coverage |
| **C10** | Criterion Registry | Attribute and Rule records; change records; registry invariants; confirmed rule-set versions; ordering method; recovery comparison against the historical artifact |
| **C11** | Per-Candidate Assessor | One assessment record per candidate, attribute version, rule version, and evidence snapshot; Reason record; candidate roll-up; coverage gate |
| **C12** | Leaderboard Service | Task-scoped versioned snapshots; result kind; four candidate states; change records with causes; tool coverage; reporting tuple |
| **C13** | Tool Broker and Capability Registries | Tool Contract, Invocation, Result, Provenance; absence and error vocabularies; retry and circuit breaker; Model Adapter Capability Record and contract tests |
| **C14** | Scoped Memory | Itemized delta entries with kind, support basis, review state, counters, scope; store-level content-policy chokepoint |
| **C15** | Run Controller | Run, stage, step, and exchange state machines; LoopOutcome; attempts, continuations, refresh runs, reopen; stopping; degradation records |
| **C16** | Reuse and Staleness Service | Input fingerprints; dependency graph; stale marks; Rerun Plan; reuse manifest |
| **C17** | Progress Projection | Three-level progress with declared denominators; freshness labels; subscribe-from-sequence replay |
| **C18** | Human Review Queue | Owns the `waiting_human` state; Expert Decision record; review-trigger table; submission intake lifecycle |
| **C19** | Evaluation and Promotion Authority | Protocol Manifest; policy arms; Round Progress Record; pools; promotion conjunction; hidden evaluators; evaluator epochs; claim scope; Case Acceptance Register; preregistration |
| **C20** | Strategy Version Archive | Strategy versions with lineage, never deleted, with rollback target, expiry, and `retired` status; owned by C19 |

Mapping from the thirteen-item preliminary spine used in the workstream reports: old 1→C4, 2→C5, 3→C7, 4→C13, 5→C9, 6→C10, 7→C11, 8→C12, 9→C14, 10→C15, 11→C1 and C17, 12→C18, 13→C19 and C20. New: C2, C3, C6, C8, C16.

### 0.3 Identifier scheme

All identifiers are opaque strings with a type prefix. `<ulid>` is a time-sortable unique id; derived ids are shown with their parent.

| Prefix | Record | Prefix | Record |
|---|---|---|---|
| `task_<ulid>@v<n>` | task context, versioned | `run_<ulid>` | one execution under a Run Binding |
| `att_<run>_<n>` | attempt within a run | `round_<run>_<n>` | screening round |
| `stage_<run>_<slug>` | stage | `step_<round>_<n>` | step |
| `xchg_<step>_<n>` | review exchange | `evt_<stream>_<seq>` | journal event; `seq` is a contiguous integer per stream (one of the stream kinds of Section 2.4) |
| `art_<sha256-12>` | content-addressed artifact | `src_<scheme>_<value>` | source (`doi`, `pmid`, `db_<name>`, `upload_<sha>`) |
| `claim_<ulid>` | ledger claim | `loc_<claim>_<n>` | passage location |
| `ig_<ulid>` | independence group | `attr_<slug>@v<n>` | attribute (CQA) version |
| `rule_<slug>@v<n>` | rule version | `rules@v<n>` | confirmed rule-set version |
| `chg_<ulid>` | change record (criterion or candidate) | `cand_<identity>` | candidate; identity supplied by the adapter scheme |
| `asm_<cand>_<attr@v>_<rule@v>_<evs>` | assessment | `rsn_<asm>` | reason record |
| `lb_<task>_<n>` | leaderboard snapshot; `<task>` without version, `n` counting every snapshot of the task in publication order | `evs_<task>_<n>` | evidence snapshot (frozen claim set and cutoff) |
| `tool_<adapter>_<slug>` | tool contract | `inv_<ulid>` / `res_<inv>` | invocation / result |
| `mem_<ulid>` | memory entry | `hd_<ulid>` | human (expert) decision |
| `q_<ulid>` | review-queue item | `oq_<ulid>` | open question |
| `plan_<run>@v<n>` | plan version | `brief_<step>` / `ret_<brief>` | delegation brief / result return |
| `ckpt_<run>_<seq>` | checkpoint | `strat@v<n>` | strategy version |
| `proto_<ulid>` | evaluation protocol manifest | `evr_<proto>_<n>` | evaluation run |
| `sub_<ulid>` | human submission | `const_<slug>` | registered numeric constant |
| `bind_<run>` | run binding | `ops_<ulid>` | operations decision (promotion, rollback) |
| `ses_<ulid>` | operator session (Section 2.4) | `cmd_<ulid>` | operator command (Section 2.4) |
| `chain_<ulid>` | run chain: a run and its continuations (Section 6.8) | `grp_<slug>` | run group: workspace and memory namespace (Section 6.9) |
| `case_<id>@v<n>` | case configuration, versioned (Section 2.2) | `lbd_<task>_<k>` | leaderboard: one per comparability key of a task (Section 4.12) |

### 0.4 State vocabularies (authoritative in C2)

**Execution states** (run, stage, step): `queued`, `running`, `waiting_tool`, `waiting_human`, `retrying`, `paused`, `failed`, `cancelled`, `completed`, `unresolved`. Terminal: `failed`, `cancelled`, `completed`, `unresolved`. Stage adds `skipped` (requires a reason and a reuse reference); step adds `rejected` (its output was rejected by adjudication). When a run ends `cancelled`, or is closed by a run continuation, its stages and steps that have not ended end `cancelled` with the run's termination reason.

**Exchange states**: `proposed`, `critiqued`, `revising`, `adjudicating`, `completed`, `rejected`, `unresolved`.

**Termination reasons**: `sufficient_support`, `round_limit_reached`, `no_actionable_step`, `diminishing_information_gain`, `repeated_failure`, `budget_exhausted`, `human_decision`, `dependency_unresolved`, `cancelled`. Rule: `budget_exhausted` always yields `unresolved`, never acceptance. `dependency_unresolved` carries a `dependency_detail`: `derivation_unavailable`, `capability_failure_share_exceeded`, or `required_input_missing`. A run ends `completed` only when its candidate sweep is complete (Section 6.6); missing values never make a run `unresolved`, they make candidates `provisional`.

**Candidate states**: `recommended`, `provisional`, `unassessed`, `rejected`.

**Result kinds** (per snapshot): `all_pass_set`, `ranked_under_score`, `both_reported` (all-pass set is the primary claim), `no_recommendation` (abstention, with reason `insufficient_coverage` | `all_candidates_excluded` | `unresolved_conflicts` | `evidence_unavailable`).

**Assessment verdicts**: `pass`, `fail`, `unknown_missing`, `unknown_conflicted`, `inapplicable`, `not_assessed`. **`not_assessed` reasons**: `identity_unresolved`, `identity_pending_review`, `budget_exhausted`, `run_cancelled`.

**Value kinds** (of a value in a record): `measured`, `curated`, `predicted`, `simulated`, `derived`, `missing`. **Determination basis** (of a claim): `measured`, `predicted`, `asserted`, `derived`, `absent`.

**Tool result outcome**: `ok`, `partial`, `empty`, `not_attempted`, `failed`, `unknown_outcome`; **record state**: `returned`, `superseded`, `stale`.

**Evidence kinds**: `peer_reviewed`, `preprint`, `database_entry`, `technical_report`, `curated_measurement`, `model_prediction`, `computational_simulation`, `biochemical_measurement`, `wet_lab_observation`, `expert_statement`.

**Claim types**: `data_derived`, `literature_extracted`, `interpretation_synthesis`, `expert_statement`.

**Approval kinds** (four disjoint fields, never interchangeable): `agent_verdict`, `software_status`, `human_scientific_approval`, `operations_decision`.

**Independence marker** (on verdicts and evaluations): `same_model`, `same_family`, `cross_family`, `deterministic`, `human`.

**Memory**: kind `evidence` | `tentative_hypothesis` | `reusable_procedure`; support basis `llm_opinion` | `deterministic_check` | `model_prediction` | `simulation` | `curated_measurement` | `instrument_measurement` | `expert_statement` | `human_curation`; review state `provisional` | `under_review` | `approved` | `rejected` | `retired`.

**Progress**: denominator kind `enumerated_fixed` | `enumerated_growing` | `budget_bounded` | `unbounded_adaptive` | `unknown`; view freshness (client-derived, never a run state) `live` | `view_stale` | `activity_unknown`.

**Derivation configuration** (on every criterion version): `reference_disclosed`, `reference_blind`, `outcome_informed_exploratory`.

**Historical-list exposure** (declared on every adapter criterion template, every `hd_` that confirms, edits, merges, splits, or removes a criterion, the `objective_text`, the adapter dimension list, the consolidation rule and its constants, every derivation strategy version, every calibration-case curation, every memory item, every `human_request` question, and every task-context version): `not_exposed`, `exposed`, `undeclared` (treated as `exposed`). Exposure is also derived: a logged read of the historical-criteria intake makes the reader `exposed` from that `seq` onward, whatever was declared. **Recovery view** (on every recovery comparison record): `independent` (no `exposed` or `undeclared` actor authored or confirmed any field of the derived item, and no artifact that shaped it has a criterion-content scan `match`; Section 8.6) or `assisted`.

**Recovery mapping kinds** (stored): `recovered_equivalent`, `recovered_with_narrower_applicability`, `recovered_with_different_cutoff`, `merged_into`, `split_into`, `not_recovered_no_evidence`, `not_recovered_out_of_scope`, `deliberately_removed`, `newly_added_not_in_history`. Reported roll-up: recovered, merged, split, removed, added, not recovered, with `recovered_with_different_cutoff` as a separate sub-count.

**Policy arms**: `P0` single-pass, `P1` fixed-round (R registered), `P2` adaptive, `P2-cap` adaptive at P0's realized budget, `P0+ retrieval-rich` and `P0+ sample-rich` single pass at P2's realized budget; `P0-noreview` P0 without the critique step (Section 13.3).

**Operator surfaces and hosts** (Sections 2.4, 14.1): surface `terminal` | `browser`; host platform `linux` | `windows`; session role `operator` | `expert` | `evaluator` | `auditor`; command entry `interactive` | `scripted`; command outcome `applied`, `duplicate` (the `command_id` was already applied with the same payload; the original result is returned), `rejected_stale_basis`, `rejected_unauthorized`, `rejected_invalid`, `rejected_not_permitted_in_state`; host start refusals `store_locked`, `store_root_unsupported`; host gap kind `stop` | `suspend`; platform support basis `checked` | `upstream_documented` | `unchecked`. Neither the surface nor the host platform enters agent context or a verdict; the host platform enters a fingerprint only through `executed_on`, for tools whose output may depend on it (Section 14.2).

**Run chains, groups, skills, and lessons** (Sections 6.8, 6.9, 10.5): continuation kind `root`, `continue`, `refresh`, `rerun`; open-question trigger class `human_request`, a sixth, non-adaptive class beside the five adaptive classes of Section 4.8; run group state `active` | `archived`; acceptance label `prespecified` | `exploratory` (Section 13.6); memory-kind display names `reusable_procedure` "skill", `tentative_hypothesis` "lesson", `evidence` "remembered evidence" (labels only; the stored kinds are unchanged).

### 0.5 Units of work

| Unit | Definition |
|---|---|
| Screening round | One scheduled evidence/evaluation pass yielding an auditable assessment or leaderboard snapshot; may span many tools and roles |
| Review exchange | One proposal → critique (→ adjudication) cycle inside a round |
| Self-correction turn | Proposer revises after its own deterministic self-check, before any critique; budgeted separately |
| LLM turn | One model call; never a round |
| Tool retry | Same call, same inputs, new attempt number on one invocation; never a round |
| Attempt | One execution attempt of a run after a crash or recovery; new `att_` id |
| Resume | Restarting an interrupted or paused run from a checkpoint; same `run_` (earlier drafts called this continuation; a round continuation adds a round inside a run, Section 6.3) |
| Evidence-refresh run | A later run on the same task context with a new evidence cutoff; new `run_` |
| Reopen | Read-only inspection of a historical run; creates no state |
| Human edit | Attributed change creating a new version and stale marks |
| Report revision | New version of a narrative report, separate from rounds and rule versions |
| Rule pass | One confirmed rule applied across every resolved candidate in the sweep scope; one step; the unit of sweep checkpointing (Section 6.6) |
| Run continuation | A new run in the same run chain, created when a person continues a run that has ended or changes a bound field; new `run_`, same `chain_`; reuses every record whose fingerprint is unchanged (Section 6.8). Not to be confused with resume, which keeps the same `run_` |

Agent count and screening-round count are independent configuration fields. A single-pass run (`screening_rounds = 1`) still fans several roles across steps within the pass.

---

## 1. Purpose and acceptance target

The system is an agent-centered method: it understands an objective, plans and delegates work, derives decision criteria from evidence, critiques them, applies them per candidate, maintains a task-scoped leaderboard, and revises its own working strategies only under measured evaluation. Biology is the first application context, supplied through a replaceable adapter and a case configuration.

The concrete v1 purpose is the manuscript rebuttal case: when implemented and run on that case configuration, the system must have a credible, evidence-backed route to (a) deriving a criterion set that recovers most of the authors' historical CQAs, each with an evidence-linked, structured rationale, and (b) admitting surufatinib onto the task-scoped leaderboard for the stated objective and five-target configuration with a per-criterion reason for every assessed compound. Every candidate receives a per-criterion record; the leaderboard position is a roll-up of those records.

The mechanism stays general. Surufatinib is a disclosed reference outcome, registered once in the case configuration; the historical eleven CQAs are a comparison artifact readable only by the comparison component; criteria are derived from objective and evidence with whatever count the evidence supports. Criterion derivation runs `reference_disclosed`: the objective and target configuration already narrow the space toward the reference candidate, so blindness is not claimed; mechanical protections (a reference-blind evidence slice, an alias scan over criterion and reason text, a leave-one-out outcome dependence report, and an evaluator-only historical artifact) stand in for it, and no acceptance claim in this design rests on a blind derivation. Any failure to recover a criterion or to admit the reference candidate under a prespecified configuration is a recorded finding with implications for the rebuttal wording (Section 17 and `case_study_protocol.md`).

---

## 2. Layer boundaries and interfaces

### 2.1 Adapter ports (implemented by the adapter, declared to the core)

| Port | Declares |
|---|---|
| Vocabulary | `entity_kinds`, `identifier_schemes` (with authority and `as_of`), `aliasing_rules`, `units`, `unit_conversions`, `scope_match_rules` |
| Criterion Templates | `template_id`, `attribute_definition`, `measurement_kind`, `direction`, `applicability_conditions`, `acceptable_value_sources`, `default_rule_form`; cutoffs are empty; templates enter the registry as `proposed`, never pre-approved |
| Evidence Sources | `source_id`, `access_mode`, `evidence_kinds_supplied`, `source_status_default`, `provenance_fields`, `cutoff_semantics`, `absence_behaviour`, `rate_limit_declaration`, `license` |
| Tool Contracts | the C13 contract (Section 7.1) |
| Deterministic Validators | `validator_id`, `finding_classes`, `severity_map`, `hard_exclusion_eligible` |
| Content Policy Lists | forbidden entity lists and numeric-claim policy consumed by the core's `check_procedure` chokepoint (Section 10.4) |
| Expert Requirements | `action_kind` → `review_required`, `qualification`, `evidence_to_present` |
| Identity Rules | identity resolution and merge rules driving the core's identity service |

### 2.2 Case configuration record

| Field | Content |
|---|---|
| `case_id`, `version`, `authored_by`, `authored_at` | identity and lineage |
| `objective_text` | verbatim; never rewritten by the system |
| `mode` | `conditional` \| `exploratory` |
| `scope_entities[]` | `{entity_kind, identifier, identifier_scheme, role: required/optional/questioned, provenance}` |
| `candidate_universe` | `{kind: enumerated_set/named_library/seeded_expansion/undetermined, source, size_if_known, access_path, as_of}` |
| `historical_stage_artifacts[]` | documented prior stages (for the primary case: the 140 predicted binders) marked comparison-only |
| `seed_candidates[]` | `{candidate_ref, reason_supplied, is_reference_outcome}` |
| `constraints[]` | `{text, kind, hardness: hard/soft/unclear, provenance}` |
| `evidence_cutoff_at`, `tool_availability_snapshot` | evidence and tool scope |
| `historical_criteria_intake` | Section 8.6; `visibility: evaluator_only` |
| `case_source_documents[]` | the manuscript, its supplement, any preprint or version of it, and documents quoting its criteria list; excluded from every derivation catalog (Section 8.6) |
| `calibration_pool_ref` | optional; external calibration cases for the derivation strategy (Section 8.3) |
| `registered_constants[]` | `const_` records (Section 8.5) including the coverage floor |
| `evaluation_scope` | `{comparison_basis: all_pass_set/ranked_score/both, abstention_allowed: true, ordering_method_ref}` |
| `baseline_configuration_ref`, `alternative_configurations[]` | registered through preregistration events (Section 13.6) |
| `human_review_requirements` | which candidate states and rule transitions require `hd_` references |
| `budget_envelope` | Section 6.5 |

**Field visibility.** Every case-configuration field declares `visibility`. `agent_visible` fields may enter agent context: `objective_text`, `mode`, `scope_entities[]`, `candidate_universe`, `seed_candidates[]` (with the reference-outcome flag), `constraints[]`, `evidence_cutoff_at`, `tool_availability_snapshot`, `evaluation_scope`. `evaluator_only` fields are read only by the comparison function, by the review queue on comparison-adjudication items after `rules@v` is confirmed, and through the evaluator-role recovery panel, each read logged with the exposure consequence of Section 8.6: `historical_criteria_intake`, `historical_stage_artifacts[]`. `control_only` fields are read mechanically by core components and never placed in agent context: `registered_constants[]`, `budget_envelope`, `human_review_requirements`, `case_source_documents[]`, `calibration_pool_ref`, and the baseline and alternative configuration refs. Agent context is assembled from `agent_visible` fields only, and each derivation decision's visibility manifest lists the others. The adapter's dimension list and criterion templates are adapter content visible to agents, not case fields. Supplied evidence files enter through the submission intake (Section 12.4) and become agent-visible only once admitted.

### 2.3 Run Binding (immutable, written at run start by C15)

`bind_<run>`: `run_id`, `task_context_id@v`, `case_id@v`, `adapter_id`, `adapter_version`, `rules@v` (may be empty), `strat@v`, `policy_arm`, `group_id`, `chain_id`, `continues_run_id?`, `continuation_kind`, `branch_label?`, `edits_since_parent[]`, `budget_extension_ref?` (Section 6.8), `protocol_ref?` (`proto_` and `evr_` when the run is an evaluation-arm run), `preregistration_ref?` (the stage-1 `preregistration.recorded` the run is registered under; a run with one is prespecified), `promotion_policy_version`, `role_bindings[] {role, adapter_id, provider_family, model_id, model_version, decoding_parameters}` (Section 14.3), `screening_rounds_budget`, `sweep_scope` (`full_universe` \| `rerun_plan` \| `refresh_delta`), `memory_mode` (`cold` \| `frozen` with snapshot ref \| `warm`), `evidence_cutoff`, `host {platform: linux/windows, os_version, service_host_version}`, `tool_availability_snapshot` (resolved on that host, with each tool's `execution_location`; Section 14.2), `known_reference_outcome_disclosure`, `derivation_configuration`, `budget_envelope`, `baseline_configuration_ref`, `bound_at`, `bound_by`. Every artifact cites its binding.

### 2.4 Operator API (the one interface both operator surfaces use)

People operate the system through one Operator API served by the service host (Section 14.1). Two surfaces implement it in v1: a **terminal client** and a **browser workbench** served by the local service host and used in Chrome (`ui_ux_spec.md` §15). In v1 the terminal client operates Linux hosts (profiles L and X) and Chrome operates a Windows host (profile W) or a Linux host (L, X); a Linux terminal operating a Windows host is not supported (Section 18, U-15). Neither surface reads store files or keeps state of its own, so a run started from one can be watched, paused, or reviewed from the other. The API and the service host are host infrastructure (Section 0.1), not core components: they own sessions, command records, role grants, request checks, and the operator log, and they decide nothing about any C1–C20 record. Subscriptions and queries are served from C17 projections and the stores' read paths; each command is validated by the component that owns its subject (C4, C8, C12, C14, C15, C16, C18, C19).

**Streams.** Every event belongs to one stream with its own contiguous `seq`. There are five kinds, all C1 journals under the same rules:

- a run journal (`run_`) for everything that happens inside a run;
- a task journal (`task_`) for task-context versions, submissions, preregistration, `run.continued`, `leaderboard.current_set`, and review items raised or decided after their run ended, Rerun Plan approvals included;
- a group journal (`grp_`) for run-group lifecycle events, memory operations, and decisions on memory items (Sections 6.9, 10);
- a case journal (`case_`) for case-configuration versions, `evaluator_only.read` events, criterion-content scans, and recovery comparisons, so a case has one access log however many tasks reference it (Section 8.6);
- one store-level evaluation journal for protocol manifests, strategy versions, and `ops_` decisions (Section 13).

| Part | Contract |
|---|---|
| Subscribe | `subscribe(stream_id, from_seq)` with the replay contract of Section 11.2, for any stream; any number of subscribers, each with its own `last_applied_seq`. Frames are filtered by session role and field visibility: a withheld event is sent as a redacted frame that keeps its `seq`, so no subscriber sees a gap |
| Query | read-only views over projections and stores (tasks, runs, leaderboard snapshots, candidate records, claims, rules, review items, change records); every response names the `{stream, seq}` or snapshot id it reflects and is filtered as above |
| Command | every state-changing request and every logged read (the role table below; `ui_ux_spec.md` §15.3). A command carries `command_id`, `session_id`, `basis` (the last `{stream, seq}` its issuer had applied on the subject's stream, or one per stream when the command reads several, as a run continuation does), the expected version of its subject, and `entry` (`interactive` \| `scripted`), and receives exactly one command outcome (Section 0.4) |
| Command record | `cmd_` record, written durably before the acknowledgement: `command_id`, `session_id`, `kind`, `subject`, `basis`, `entry`, `payload_hash`, `outcome`, `result_ref` (the `{stream, seq}` of the resulting event, if any), `received_at` |
| Session | `ses_` record: `person_id`, `roles[]` (from role grants), `identity_basis` (`authenticated_account` \| `recorded_attestation`, as in Section 12.2), `os_account`, `surface`, `active_group_id` (Section 6.9), `opened_at`, `closed_at`; one person may hold sessions on both surfaces at once |

**Roles.** Roles come from `role_grant` records in the operator log, written by the person who controls the host's operating-system account; a session does not choose its own roles.

| Command group | Required role |
|---|---|
| task and case-configuration authoring, plan only, run start, pause, resume, cancel, continue and branch, human-requested rounds, run annotations, follow-up questions, universe additions, scope-based exclusions, run-group creation, renaming, archiving, and task moves or copies, authoring and retiring provisional skills and lessons, exports of non-evaluator records, setting a leaderboard's current snapshot, reassigning review items and assigning claims to experts, issuing a browser address for another person | `operator` (human-requested rounds and skill or lesson authoring also `expert`) |
| every command that writes an `hd_` record: review decisions with or without edits, disputes, evidence-based exclusions, submission admission, Rerun Plan approval, identity merges | `expert` |
| reads of `evaluator_only` content (recovery panel, comparison-adjudication items), attaching the historical-criteria intake, recording preregistration stages, registering evaluation protocols, running criterion-content scans and recovery comparisons, requesting procedure trials | `evaluator` |
| strategy promotion and rollback (`ops_`) | `operator` with the evaluation-lead grant |
| opening raw traces | `expert` or `auditor` |

A command from a session lacking the role is `rejected_unauthorized`. Switching the active run group is a session setting open to every role (Section 6.9). A comparison-adjudication decision needs both roles: `evaluator` for the read and `expert` for the `hd_`. Under `recorded_attestation` roles and identities rest on attestation, not enforcement. Sessions that share one `os_account` under different person ids are linked, and every separation-of-duties check (a submission admitted by someone other than its submitter; exposure per person) treats linked identities as one person and flags the case.

**Command rules.**

- **Effects come from the journal.** A surface shows the effect of a command only when the event recording it arrives through its subscription; the acknowledgement carries `command_id` and `result_ref`, never a predicted state. Both surfaces therefore show the same state at the same position.
- **At most once.** A repeated `command_id` with the same `payload_hash` returns `duplicate` with the original result from the `cmd_` record, also across host restarts; the same `command_id` with a different `payload_hash` is `rejected_invalid`.
- **Preconditions, and no last writer wins.** Each command kind declares a precondition on its subject. If the precondition fails against the state at `basis`, the outcome is `rejected_not_permitted_in_state`. If the stream advanced past `basis.seq` and the precondition no longer holds (the item was decided or claimed by someone else, the run was cancelled, the rule version was superseded since the issuer looked), the outcome is `rejected_stale_basis` with the current state, and the surface asks the person to look again.
- **Disagreement is not replacement.** An expert who disagrees with an applied decision records a new `hd_` with `disputes_decision_id`; both records are kept, and the subject becomes `unresolved`, labelled disputed, until escalation (Section 12.2). `supersedes_decision_id` is reserved for revising one's own decision and for deciding an escalation item.
- **Human decisions are entered by a person.** A command that writes an `hd_` needs `entry: interactive`: a confirmation answered by the person at the surface after the consequences are shown. A scripted command that would write an `hd_` is `rejected_unauthorized`.
- **Attribution.** Every event a command causes carries `actor.via {surface, session_id, command_id, entry}`. Rejected commands are written to the operator log (Section 14).
- **Logged reads are commands.** Reading `evaluator_only` content or a raw trace changes what is known about the reader, so it is a command: it carries the session token, needs the role above, and asks for confirmation on both surfaces with the exposure warning of Section 8.6. In v1, evaluator-only records are shown on screen only; they are never exported, downloaded, or written as line-delimited output, because a copy outside the store would have readers nobody logs. Store files read outside the API are protected as Section 14.1 states.

---

## 3. End-to-end flow (single-pass default)

The default operating policy is `P0`: one screening round in which several roles contribute. Numbered stages below name the components, the artifacts written, the journal events, and the human touchpoints. Section 17 instantiates this flow for the primary case.

```mermaid
flowchart TD
  A[Case configuration + Run Binding<br/>C15, C19 preregistration] --> B[Task context normalization<br/>C4]
  B --> C[Plan with steps, owners, budgets<br/>C5, C6]
  C --> D[Evidence retrieval and ledger<br/>C13 tools, C9]
  D --> E[Criterion derivation: propose, critique, adjudicate<br/>C7, C10 invariants]
  E --> F{Expert confirmation<br/>C18}
  F -->|rules@v confirmed| G[Identity resolution + per-candidate assessment<br/>C13, C11]
  G --> H[Leaderboard snapshot<br/>C12]
  H --> I[Recovery comparison + case acceptance records<br/>C10 comparison fn, C19]
  I --> J{Round close<br/>C15, C8}
  J -->|no actionable trigger or P0| K[run completed / unresolved]
  J -->|referent-backed trigger and budget, P2| D
  K --> L[Human edits → stale marks → Rerun Plan<br/>C18, C16]
  K --> M[Evidence-refresh run → new snapshot<br/>new run_, same task_]
```

| Stage | Components | Writes | Journal events | Human touchpoint |
|---|---|---|---|---|
| 0 Bind | C15, C19 | `bind_`; for a prespecified run, a blocking preregistration item until the evaluator records stage 1 (Section 13.6) | `run.created`, `human.review_requested`, `preregistration.recorded` | operator authors the case configuration; evaluator records stage 1 |
| 1 Normalize | C4 | `task_@v1`, unknowns, `missing_info_requests` | `stage.*`, `human.review_requested` if a blocking unknown exists | answers blocking questions only |
| 2 Plan | C5, C6 | `plan_@v1`, `brief_` per step, budgets | `plan.recorded`, `step.queued` | none by default; plan inspectable |
| 3 Retrieve | C13, C9 | `src_`, `claim_`, `loc_`, `ig_`, search coverage records, visibility manifest | `tool.*`, `evidence.admitted`, `evidence.conflict_recorded` | none |
| 4 Derive criteria | C7, C10 | proposal, critique, revision, adjudication artifacts; `attr_@v`, `rule_@v`, `chg_`; considered-and-rejected list | `exchange.*`, `criterion.version_proposed`, `criterion.change_recorded` | none inside the exchange |
| 5 Confirm | C18, C10 | `q_` items, `hd_` decisions, `rules@v1`; preregistration (criterion stage) | `human.review_requested/decided`, `criterion.version_approved`, `preregistration.recorded` | expert approves, edits, or rejects each hard exclusion and expert-set cutoff; for a prespecified run, the evaluator records stage 2 before assessment |
| 6 Assess | C13, C11 | identity records, `asm_` and `rsn_` per candidate × criterion (full sweep, breadth-first by rule; Section 6.6), roll-ups | `candidate.assessed`, `tool.*` | ambiguous identities queued |
| 7 Snapshot | C12 | `lb_<task>_1` with result kind, reporting tuple, tool coverage, Independence level | `leaderboard.snapshot_published`, `decision.recorded`, `projection.hash` | `recommended` publication requires `hd_` reference if the case requires it |
| 8 Outcome report | C19, C11 | outcome dependence report; the run's own acceptance records | `evaluation.recorded` | none; the recovery comparison and the full acceptance check run after the snapshot, outside the run, as evaluator commands in the case stream (Section 8.6), with experts judging `expert_judged_equivalent` mappings; run completion never waits for them |
| 9 Close | C15, C8 | `oq_` entries, LoopOutcome, termination reason | `round.closed`, `run.completed` or `run.unresolved` | none |
| 10 Edit | C18, C16 | new versions, stale marks, Rerun Plan, reuse manifest | `human.*`, `staleness.marked`, `rerun.scheduled` | expert edits; approves reruns above budget |
| 11 Refresh | C15, C12 | new `run_`, `evs_<n+1>`, `lb_<task>_<n+1>` with change records | all of the above | as needed |

The same records are produced for a single-pass run and for an adaptive multi-round run; the only difference is whether Stage 9 schedules another round. Updating a leaderboard over time (Stage 11) never requires any individual run to be multi-round. Editing and continuing a run (Section 6.8) enters this flow again at Stage 1 as a new run in the same chain, binding the edited versions and reusing unchanged records.

---

## 4. Core components: responsibilities, records, states, failure behaviour

Each subsection gives the component's responsibility, the records it owns (field lists), its states, its failure behaviour, and its human touchpoints. Records are persisted through the Artifact Envelope (C3) unless stated otherwise; every record carries `vocabulary_version` and the `journal_seq` of the event that created it.

### 4.1 C1 Event Journal

**Responsibility.** Append-only journals of immutable events, one per stream (Section 2.4: run, task, run group, case, and the store-level evaluation stream); the only source of truth. Progress, run state, timeline, review queue, leaderboard views, and resume positions are pure folds over committed events. A correction is a new event that references the corrected `seq`; nothing is rewritten.

**Event record.** `seq` (contiguous integer per stream, assigned at write), `event_id`, `event_type`, `emitted_at`, `recorded_at` (both UTC ms, so clock skew is detectable), `actor {kind: agent|tool|human|controller|scheduler|system, id, role, version, model_family?, via? {surface, session_id, command_id, entry}}` (`via` on events caused by an operator command; Section 2.4), `ids {group_id, task_id, chain_id, run_id, attempt_id, stage_id, step_id, round_id, exchange_id, tool_call_id, review_request_id, checkpoint_id}`, `parent_seq` (causal link: the event this answers or continues), `cause_seq` (the event that caused a state transition), `state_from`, `state_to` (for transition events), `input_versions {rules@v, evs_, lb_, strat@v}`, `question` (one sentence), `summary` (concise, never raw model output), `progress {scope, denominator_kind, completed, planned, indeterminate}`, `budget {rounds_used, rounds_max, tool_calls, tokens_by_role, wall_clock_s, human_wait_s}`, `artifact_links[] {kind, id, version}`, `visibility` (`default` | `expert` | `auditor`), `payload_ref` (pointer; large bodies never inline), `payload_hash`.

**Event kinds.** Lifecycle: `run.{created, started, paused, resumed, cancelled, completed, unresolved, failed, continued, annotated}`, `stage.{opened, closed, skipped}`, `step.{queued, started, progressed, waiting_tool, waiting_human, retrying, completed, rejected, unresolved, failed}`, `round.{opened, closed}`, `attempt.{started, finalized}` with `finalized_by {worker, controller, human}`. Actors: `agent.{started, heartbeat, finished}`. Tools: `tool.{requested, returned, errored, retry_scheduled, degraded}`. Protocol: `exchange.{proposed, critiqued, revised, adjudicated, closed}`. Substance: `evidence.{admitted, conflict_recorded, quarantined}`, `criterion.{version_proposed, change_recorded, version_approved}`, `candidate.assessed`, `leaderboard.snapshot_published`, `leaderboard.current_set`, `decision.recorded`. Humans: `human.{review_requested, review_decided, review_claimed, review_claim_released, review_withdrawn, review_expired, input_submitted}`, `trace.opened`, `evaluator_only.read` (case stream; Section 8.6). Groups: `group.{created, renamed, archived, reactivated, task_added, task_removed}` (group stream) and `task.group_changed` (task stream; Section 6.9). Control: `checkpoint.written`, `staleness.marked`, `rerun.scheduled`, `progress.estimate_revised` (carries before/after `planned` and `denominator_kind`), `preregistration.recorded`, `evaluation.recorded`, `projection.hash`, `plan.recorded`. Memory and reports: `memory.operation_recorded` (one per C14 operation: add, retire, supersede, retag), `memory.recalled` (the memory items placed in one step's context, with their review states; Section 10.5), `report.revision_recorded` (one per `report_revision` artifact).

**Counter rule (contract).** Only completion-class events (`stage.closed`, `step.completed`, `round.closed`, `agent.finished`, `tool.returned`, `exchange.closed`, `candidate.assessed`, `human.review_decided`) may increase a `completed` value. `agent.heartbeat` and `tool.requested` update only `last_seen_at`, the current question, and elapsed time. The watchdog subscribes to heartbeats only. A conformance test asserts that no completion-class event carries an unchanged `completed` count and that no heartbeat carries a counter.

**Failure behaviour.** A crashed attempt is closed by the controller with `attempt.finalized {finalized_by: controller}`, never truncated; unanswered tool calls receive synthetic `unknown_outcome` results so replay stays valid; recovery starts a new `att_`. Writes are durable per event; projections are rebuilt from `seq` after any inconsistency. Heartbeats are journaled as an activity class with a retention window; completion events are retained indefinitely.

### 4.2 C2 State Registry

**Responsibility.** The closed vocabularies of Section 0.4, each with `label_domain` (execution, exchange, candidate, result, value_kind, review, change_kind, termination_reason, surface, host_platform, session_role, command_entry, command_outcome, host_gap_kind, platform_support_basis), `state_id`, `semantics`, `is_terminal`, `implies_admission`, `ui_label`, `ui_tone`, `maps_to_candidate_state?`. The Run Controller is the only writer of execution and exchange states; presentation code reads `ui_label` and may never remap a state. `unresolved` never maps to a word implying advancement. A contract test asserts that no transport or UI label maps to admission when the authoritative state does not.

**Authoritative labels.** The `ui_label` string for every registered state, by `label_domain`, is tabulated in `ui_ux_spec.md` Section 13; that table is the registry's published mapping and is the only place labels are defined.

**Failure behaviour.** A value absent from the registered vocabulary version fails validation at write; the write is rejected and journaled as `step.failed` with `reason: vocabulary_violation`.

### 4.3 C3 Artifact and Vocabulary Registry

**Artifact Envelope.** `artifact_id` (content hash), `artifact_kind`, `schema_version`, `vocabulary_version`, `task_context_id`, `run_id`, `round_id`, `exchange_id?`, `parent_artifact_id?`, `supersedes?`, `actor {actor_kind, actor_id, role, model_family?, policy_version?}`, `created_at`, `journal_seq`, `state`, `termination_reason?`, `evidence_refs[]`, `payload`, `payload_sha256`, `adapter_extensions` (opaque to core logic).

**Artifact kinds and key payloads.**

| Kind | Key payload fields | States |
|---|---|---|
| evidence_request | `question`, `decision_relevance`, `requested_evidence_kinds[]`, `target_criterion_id?`, `target_candidate_id?`, `budget`, `acceptance_test` | open, assigned, answered, unanswerable, withdrawn |
| proposal | `subject` (criterion \| rule \| candidate_assessment \| plan), `content_ref`, `rationale`, `addressed_findings[]`, `assumptions[]`, `considered_and_rejected[]` | draft, submitted, revised, withdrawn |
| critique | `checks[]` (Section 5.3), `findings[]` (`finding_id`, `class`, `severity`, `target_field`, `claim`, `evidence_refs[]`, `external_referent`, `actionable_request?`), `verdict` (support \| revise \| reject \| inconclusive), `independence` (Section 5.4) | submitted, superseded |
| revision | `base_proposal_id`, `changes[]` (`field_path`, `before`, `after`, `reason`, `finding_refs[]`), `unaddressed_findings[]` | submitted, superseded |
| adjudication | `inputs[]`, `precedence_table_version`, `outcome`, `dissent[]`, `escalated: bool` | recorded |
| tool_request | `tool_id`, `contract_version`, `inputs`, `idempotency_key`, `budget`, `expected_output_kind`, `question_id` | queued, dispatched, succeeded, failed, timed_out, cancelled |
| tool_result | Section 7.3 | returned, superseded, stale |
| result_return | `brief_step_id`, `status` (completed \| rejected \| unresolved), `structured_summary` (bounded), `ledger_refs[]`, `artifact_refs[]`, `budget_consumed`, `open_issues[]` | returned |
| decision | `subject_ref`, `outcome`, `independence_declaration`, `dissent[]`, `override_reason?`, `rules@v`, `evidence_cutoff` | provisional, confirmed, superseded, reverted |
| human_decision | Section 12.2 | recorded, superseded |
| report_revision | `report_id`, `version`, `parent_version`, `user_request`, `intent`, `content_ref`, `change_summary` | current, superseded |

**Vocabulary registry.** `vocabulary_id`, `version`, `values[] {value, definition, introduced_in_version}`, `deprecations[]`. Schemas, validators, and UI labels are generated from it; a persisted value absent from the version it was written against fails a consistency check.

### 4.4 C4 Task Context Normalizer

**Responsibility.** Turn any combination of objective text, desired properties, supplied evidence or data, candidate set, seeds, and constraints into an explicit, versioned task context. Ask only for information that makes the task meaningful. No keyword fallback: if derivation cannot run, the run ends `unresolved` with termination reason `dependency_unresolved` and `dependency_detail: derivation_unavailable`.

**Task context record.** `task_context_id`, `version`, `created_by`, `created_at`, `supersedes`; `group_id` (Section 6.9); `derived_from_task_id?` (a copy into another group); `author_exposure` (the `historical_list_exposure` of the version's author; Section 8.6); `mode` (conditional \| exploratory); `objective_text` (verbatim); `intended_outcome {statement, origin: user/agent_proposed, status: given/proposed/confirmed}`; `scope_entities[]` (adapter-typed, with `role` required/optional/questioned and provenance); `candidate_universe {kind, source, size_if_known, access_path, as_of}`; `seed_candidates[] {candidate_ref, reason_supplied, is_reference_outcome}`; `constraints[] {text, kind, hardness, provenance}`; `supplied_evidence[] {artifact_ref, kind, submitted_by, submitted_at, admitted: pending/admitted/rejected, limitation_note}`; `unknowns[] {question, blocking, owner: agent/tool/human, resolution_state}`; `evaluation_scope {comparison_basis, abstention_allowed, evidence_cutoff_at, tool_availability_snapshot}`; `missing_info_requests[] {field, why_needed_for_meaning, asked_at, answer, answered_by}`.

Mandatory: `objective_text`, `mode`, `evaluation_scope`, and either a candidate universe or a seed set. Everything else is explicitly `undetermined`, which blocks admission (not execution). Conditional mode means a user-supplied candidate universe plus at least one constraint or scope entity. Exploratory mode means scope entities and criteria arrive as `agent_proposed` and need human confirmation before any hard rule depends on them; in v1 the system may flag but not remove a user-supplied scope entity.

**Human touchpoint.** Blocking unknowns create `waiting_human` queue items; advisory unknowns are shown on the task-input screen and never block.

### 4.5 C5 Planner/Delegator

**Plan record.** `plan_id`, `task_context_id`, `plan_version`, `parent_plan_id?`, `objective_ref`, `steps[]`, `budget_envelope`, `created_by`, `approval_state` (draft \| approved \| executing \| superseded).

**Step record** (the delegation brief is the step). `step_id`, `question`, `objective` (one sentence), `owner {owner_kind: agent_role/tool/human, owner_ref}`, `output_contract {artifact_kind, required_fields[]}`, `allowed_tools_and_sources[]`, `scope_boundaries[]`, `inputs[]`, `depends_on[]`, `budget {llm_turns, tool_calls, tool_retries, wall_clock_s, cost_units, human_minutes}`, `completion_check` (inspectable predicates over artifacts, e.g. "every admitted candidate has a per-criterion record with provenance"), `on_failure` (retry \| escalate_human \| mark_unresolved \| skip_with_reason), `produces[]`, `evidence_cutoff_ref`, `state`.

**Policy.** The planner's context receives only `result_return` artifacts and ledger references, never raw transcripts; a bounded excerpt can be requested by event sequence number. Effort scales with the task through a declarative complexity table in the case configuration (lookup: one worker, few calls; comparison: several workers; full derivation: many), never through a default round count. Loop budgets are separate per class: `self_correction_turns`, `review_exchanges`, `tool_retries`, `evidence_requests`, `screening_rounds`, `reflection_turns`. The default plan is a template of the Section 3 stages that the planner may specialize; fixed-template, template-with-insertions, and free planning are all expressible for comparison.

**Failure behaviour.** A step whose owner fails follows `on_failure`; a circular or unexecutable plan is rejected at `approval_state: draft` with a journaled reason.

### 4.6 C6 Budget and Cost Accountant

**Responsibility.** Per-step, per-loop-class (including `reflection_turns`; Section 10.5), and per-run budgets, and the cumulative `chain_cost` of a run chain (Section 6.8); matched-budget accounting for evaluation arms; cost reporting beside every metric.

**Records.** `budget_envelope {screening_rounds, review_exchanges, self_correction_turns, tool_retries, evidence_requests, reflection_turns, tokens_by_role, tool_calls_by_tool, wall_clock_s, human_review_minutes, money_class}`; per-round and per-strategy-version `cost_record {tokens_by_role_and_family, tool_calls_by_tool_and_outcome, wall_clock_s, human_review_minutes, decisions_changed}`; derived `cost_per_changed_decision` where "changed decision" is defined on candidate state transitions only.

**Failure behaviour.** Exhausting a budget other than the round budget before the sweep is complete yields a `LoopOutcome` with `termination_reason: budget_exhausted` and state `unresolved`; using up the round budget after a complete sweep is `round_limit_reached`, and the run ends `completed` (Section 6.3). Nothing is truncated silently.

### 4.7 C7 Proposer–Critic Protocol

Specified in Section 5. Summary: roles are Planner/Delegator, Proposer, Deterministic Validator (adapter checks), Blind Critic, Evidence Retriever (own budget and provenance duties), Deterministic Adjudicator (escalated adjudication only on persistent disagreement about an identified referent), Human Reviewer; a separate Evaluator runs outside the decision path on fixed snapshots. Counter-evidence is a required search obligation plus deterministic verification, not a persona. Default bound: one proposal, one critique with external referents, one revision; outcomes `completed` | `rejected` | `unresolved`.

### 4.8 C8 Open-Question Register

**Responsibility.** The durable home of continuation triggers; the only legitimate reason for another screening round.

**Open-question record.** `question_id`, `task_context_id`, `question`, `trigger_class` (`new_external_evidence` | `unresolved_conflict` | `consequential_missing_measurement` | `questionable_exclusion` | `decision_relevant_computation` | `human_request`), `referent {artifact_kind, id, version}` (mandatory: a ledger entry, tool result, criterion, or candidate exclusion), `affects[]` (criterion and candidate refs), `expected_decision_change` (which state or ordering changes for which candidate), `acceptance_test`, `attempts[] {attempt_no, method, result, realized_information_gain {new_admitted_claims, conflicts_resolved, gaps_filled, decisions_changed}, cost}`, `state` (open \| assigned \| answered \| unanswerable \| withdrawn \| deferred), `priority`.

**Admissibility rule.** Another round is admissible only if an open question has a non-empty `expected_decision_change`, a referent, and an untried method within budget. An agent's self-reported low confidence and agent disagreement without a referent are not triggers. Cross-family reviewer disagreement about a specific ledger entry is admissible as `unresolved_conflict`. A `human_request` question is written by a person (operator or expert) through the Operator API. Its referent is the record the person names (a criterion, candidate, claim, tool result, or exclusion) and is required; it also carries a stated reason, `expected_decision_change`, and `author_exposure` (Section 8.6); the command itself appears only in `actor.via`. It is admissible within the round budget of a run that is neither bound to a `proto_` arm nor registered as prespecified; otherwise it is `rejected_not_permitted_in_state`, and the person continues the run instead (Section 6.8). The round it opens is labelled human-requested, and `human_request` is never one of the five adaptive trigger classes.

**Round-level event.** `round.closed` carries the register delta and `realized_information_gain`, so the diminishing-gain stop (two consecutive rounds producing identical leaderboard snapshots with no new ledger entries) is computable from the journal.

### 4.9 C9 Evidence Ledger

**Responsibility.** Two ledgers: the **Claim Ledger** (claims linked to exact source locations) and the **Assessment Ledger** (Section 4.11), the second referencing the first. Append-only; ordering by `(journal_seq, updated_at)`; crash-truncated lines tolerated and reported.

**Source record.** `source_id`, `identifiers[] {scheme: doi/pmid/accession/url/internal, value}`, `title`, `authors`, `issued_date`, `container`, `source_status` (`peer_reviewed_paper` \| `preprint` \| `database_entry` \| `technical_report` \| `curated_measurement` \| `model_prediction_record` \| `experiment_record` \| `expert_statement`), `version_label`, `supersedes_source` / `superseded_by_source`, `retraction_state` (none \| corrected \| retracted \| expression_of_concern \| unknown), `access_state` (`full_text_available` \| `abstract_only` \| `metadata_only` \| `paywalled` \| `fetch_failed`), `access_checked_at`, `duplicate_of`, `license`.

**Claim record.** `claim_id`, `source_ref`, `location {location_kind: page/section/table/figure/paragraph/record_field/line_range, locator_value, quoted_span, span_checked_against_source}`, `claim_text` with `verbatim` | `paraphrase` marker, `normalized_statement`, `claim_type`, `entities[]` (adapter-typed with identifier scheme), `scope {population_or_system, conditions, measurement_context}` each marked stated | inferred, `evidence_kind`, `determination_basis`, `value`, `unit`, `unit_as_reported`, `normalization_applied`, `direction_or_verdict`, `uncertainty {form: interval/sd/qualitative/absent, value}`, `polarity` (supports \| conflicts \| inconclusive) relative to a named attribute, `independence_group`, `scope_match` (direct \| conditional \| analogous \| out_of_scope \| unknown), `reading_depth` (title_only \| title_abstract \| full_text \| supplementary \| not_read), `extraction_actor`, `extraction_confidence` (labelled a model self-report), `verifier_id`, `verifier_operating_point`, `verification_status` (supported \| unsupported \| contested \| unverified), `admission_state` (pending \| admitted \| quarantined \| rejected \| superseded), `admission_reasons[]`, `supersedes`.

**Independence group.** `group_id`, `basis` (`same_underlying_experiment` \| `same_dataset` \| `same_cohort_or_sample` \| `same_model_run` \| `shared_authorship_only` \| `assumed_distinct`), `member_claim_refs[]`, `determined_by`, `evidence_for_grouping`. Support counts are computed over groups, never over claims or sources; `assumed_distinct` is a visible default; preprint/published pairs collapse to one group via `supersedes_source`; `independent_support_count` replaces any replication bonus.

**Evidence visibility manifest** (per decision). `actor`, `role`, `task_context_id`, `subject` (criterion or candidate under assessment), `catalog_size`, `included_ids[]`, `excluded[] {id, omitted_reason}` with reasons `acl_denied_for_role` \| `extraction_not_prompt_safe` \| `no_structured_claims` \| `budget_exceeded` \| `superseded_by_newer_version` \| `duplicate_of_included_source` \| `evaluator_only_artifact` \| `case_source_document`, `conflicting_sources_excluded[]`, `conflicting_to_supporting_ratio`, `content_hash`. The catalog is built from the unfiltered source set before any filter runs. Publication gate: a decision publishes only if its manifest exists and every `conflicts`-polarity claim for the attributes involved is included or individually excluded with a reason.

**Search coverage record** (per evidence request). `queries[]`, `source_families[]`, `date_range`, `result_counts`, `retrieval_failures[]`, `requested_minimum_met: bool`, `shortfall_note`.

**Rules.** A claim used by a `hard_exclusion` or quoted in a published rationale requires a location record with `span_checked_against_source`. When `access_state` is not `full_text_available`, `reading_depth` cannot be `full_text` and the dependent assessment carries `limitation_kind: full_text_unavailable`. An `interpretation_synthesis` claim may not be the sole support of a Criterion Registry entry without a human decision. A successful tool call never changes `verification_status`.

**Failure behaviour.** Fetch failures are source records with `access_state: fetch_failed`; retrieval shortfalls are reported, never padded.

### 4.10 C10 Criterion Registry

**Attribute record (CQA).** `attribute_id`, `version`, `name`, `definition` (one measurable quantity or one qualitative determination), `rationale`, `measurement_kind` (quantitative \| ordinal \| categorical \| qualitative_determination), `unit`, `unit_system` (required when quantitative, else `not_applicable`), `direction` (higher_better \| lower_better \| within_range \| target_value \| non_directional \| undetermined), `applicability_conditions[] {condition_text, scope_kind, evaluable_by: rule_engine/human, if_unmet: inapplicable/unknown}`, `acceptable_value_sources[]` (ordered evidence kinds), `supporting_claim_refs[]`, `conflicting_claim_refs[]`, `belief_status` (proposed \| supported \| contested \| refuted \| retired), `status` (proposed \| under_review \| confirmed \| deprecated \| rejected), `derived_from` (template or proposal ref), `derivation_configuration`, `non_evaluable_reason?` (`no_measurement_available` \| `no_tool_adapter` \| `unit_unresolved` \| `requires_expert_determination`), `field_provenance[] {field_name, actor_kind, actor_id, at, source_refs, supersedes}`.

**Rule record.** `rule_id`, `version`, `attribute_ref@v`, `rule_kind` (`hard_exclusion` \| `preference` \| `exploratory_consideration`), `predicate_form` (threshold \| range_membership \| ordering \| categorical_membership \| qualitative_judgment), `cutoff {comparator, value, unit}` \| `absent`, `cutoff_basis` (`measured_distribution` \| `regulatory_or_standard_reference` \| `source_stated_value` \| `expert_set` \| `none_evidence_insufficient`), `uncertainty_range {low, high, basis}` \| `absent`, `on_missing`, `on_inapplicable`, `on_conflict` (each `unknown_no_penalty` \| `unknown_blocks_recommendation` \| `route_to_human` \| `exclude`; `exclude` only for hard exclusions and only with a human decision reference), `weight` (preferences only), `applies_to_result_kind` (all_pass_set \| ranked_score \| both), `status`, `confirmed_by` (`hd_` ref), `field_provenance[]`.

**Four-state evaluation table** (binding on C11). `supported_pass`; `supported_fail` (hard exclusion → `rejected` with this rule as cause); `missing` (hard rule → `unknown`, candidate capped at `provisional`; preference → excluded from the sum, lowers reported coverage); `inapplicable` (not evaluated, denominator reduced, never a penalty); `conflicted` (hard rule → `unknown` plus mandatory queue item; preference excluded until resolved); `qualitative_only` (`unknown` unless `predicate_form = qualitative_judgment`; preference only via a declared ordinal mapping with its own `cutoff_basis`). `not_assessed` (cell never attempted: identity unresolved or pending, budget exhausted mid-rule, run cancelled; counted in the denominator and not the numerator of `hard_rule_coverage`; on a hard rule, caps the candidate at `provisional`). No surrogate may stand in for a missing value inside a verdict; a surrogate is a separate attribute with its own rule.

**Criterion change record.** `change_id`, `operation` (add \| revise \| merge \| split \| remove \| reinstate), `targets[]` (ids and versions in/out), `reason_kind` (`new_evidence` \| `conflict_resolved` \| `redundancy_detected` \| `unit_or_direction_error` \| `applicability_narrowed` \| `cutoff_unsupported` \| `expert_instruction` \| `scope_change`), `reason_text`, `source_refs[]` (required except `expert_instruction`), `proposed_by`, `critiqued_by`, `arbitration_outcome` (accepted \| rejected \| unresolved), `human_decision_ref` (required for any transition into `confirmed`), `effective_from_version`, `affected_candidates[] {candidate_ref, restage_action: reassess_required/reusable_unchanged/newly_applicable/newly_inapplicable}`, `removal_kind?` (`unsupported` \| `superseded`). Merge requires equal normalized definition, unit-normalized direction, and value-source kinds; split requires distinct applicability sets or measurements. No `reason_kind` can carry a retrieval, review, or tool-selection change: those are strategy changes (C20), not criterion changes.

**Registry invariants** (each failure is a typed critique, never a silent correction; bounded repair of N revisions, then `unresolved`): *arbitrary cutoff* (cutoff present with `expert_set` and no `hd_`, or `none_evidence_insufficient` with a value; two rules on one attribute differing by less than their uncertainty); *duplicate* (matching `(definition_normalized, unit_normalized, direction, acceptable_value_sources)` tuple, or verdict agreement above a configured share on assessed candidates — merges are only ever proposed); *units* (unitless cutoff on a quantitative attribute is a hard failure); *weak exclusion* (hard exclusion resting on `source_stated_value` from one independence group, or on `analogous` scope, or rejecting more than a configured share of the universe on predicted values); *reference-candidate scan* (identifiers and aliases of the disclosed reference outcome found in any definition, rationale, cutoff, or reason text outside an explicit comparison artifact); *reversal test* (before promotion, the rule is presented with a fixed evidence snapshot that contradicts it and the revision behaviour is recorded).

**Confirmed rule-set version.** `rules@v<n>`: ordered attribute and rule versions, `ordering_method {kind, weight_vector, tie_break}`, `evidence_admission_predicate_hash` (computed over `acceptable_value_sources`, the three on-state policies, the permitted `cutoff_basis` set, the coverage-floor constant, and registered constants), `confirmed_by[]` (`hd_` refs), `preregistration_ref`. A rule-version change marks every assessment under the prior version `stale` and re-derives candidate state; a changed hard exclusion can only move candidates between `recommended`/`provisional` and `rejected`; a changed preference weight can only reorder within one result kind and must emit a rank-change explanation naming the change record.

**Comparison function and historical artifact.** Section 8.6.

**Failure behaviour.** Attributes the adapter cannot evaluate stay `proposed` with `non_evaluable_reason` and are reported as known limitations; nothing is silently dropped. A rejected proposal is retained with `rejection_reason` (`no_evidence` \| `single_non_independent_source` \| `unit_unresolved` \| `duplicate_of` \| `out_of_scope_for_objective` \| `not_measurable_with_available_sources` \| `expert_rejected` \| `conflicting_evidence_unresolved` \| `superseded_by`).

### 4.11 C11 Per-Candidate Assessor

**Responsibility.** Apply a confirmed rule-set version to each candidate, producing one assessment record per (candidate, attribute version, rule version, evidence snapshot). The assessor executes rules it never authors; merge, split, and removal stay in C10.

**Assessment record.** `assessment_id`, `candidate_ref`, `attribute_ref@v`, `rule_ref@v`, `rules@v`, `evidence_snapshot_id`, `verdict` (Section 0.4), `value`, `unit`, `value_kind`, `determination_basis`, `value_source_claim_refs[]` (required unless `determination_basis = absent`), `conflicting_claim_refs[]`, `uncertainty`, `applicability_evaluation {condition_refs[], outcome}`, `reason_ref` (`rsn_`), `assessed_by {actor_kind, actor_id, model_or_tool_version}`, `assessed_at`, `tool_result_ref` \| `tool_error_ref`, `staleness` (`current` \| `stale_rule_version` \| `stale_evidence` \| `stale_by_human_edit` \| `superseded`), `human_override_ref?`, `reuse {decision: recomputed/reused_valid/reused_overridden_by_human, reused_from_assessment_id?}`.

**Reason record.** `reason_id`, `verdict_restated` (enum, so text cannot disagree with the verdict), `attribute_ref@v`, `rule_ref@v`, `evidence_refs[]` (at least one admitted claim, or `determination_basis: absent` plus an `absence_check_record {source_kinds_searched[], searched_at, coverage_record_ref}`), `value_and_unit_as_used`, `unit_normalization_note?`, `applicability_statement`, `counter_evidence_disposition` (`none_found` \| `found_and_outweighed` with basis \| `found_and_unresolved` \| `not_searched`), `cutoff_basis` (inherited), `uncertainty_statement`, `reason_template_id?` (for legitimately shared reasons such as a library-wide hard exclusion), `reason_text` (generated last, constrained to restate the fields above).

**Disqualifiers** (an assessment with an invalid reason is unpublishable): no `evidence_refs` and no absence check; sole reference is a model self-report, an LLM confidence statement, another agent's verdict, or a `provisional` memory entry; a cited claim with `scope_match: out_of_scope` or `admission_state ≠ admitted`; a unit differing from the rule's without a normalization note; a hard exclusion resting on a `title_only` read or on `not_searched` counter-evidence; text asserting a measurement where `determination_basis = predicted`; naming the disclosed reference outcome as justification; identical `evidence_refs` and `value` under differing verdicts across candidates.

**Candidate roll-up.** `hard_rule_coverage` (applicable hard rules holding a value-bearing verdict, `pass` or `fail` ÷ applicable hard rules), `n_fail_hard`, `n_unknown_hard`, `n_inapplicable`, `preference_score?` (with ordering method ref), `state`, `state_reason`, `blocking_unknowns[]`. Rules: any hard-rule `fail` ⇒ `rejected`; any hard-rule `unknown_*` or `not_assessed` cell caps the state at `provisional`; `recommended` additionally requires `hard_rule_coverage ≥ const_coverage_floor` (a registered case constant inside the admission-predicate hash), no `unknown_conflicted` on any hard rule, at least one admitted claim per hard rule whose `determination_basis` is in the attribute's `acceptable_value_sources`, and the Independence level the case configuration requires; no assessed criteria ⇒ `unassessed`. Every candidate entering a round leaves it with a state and a row; dropping a candidate is prohibited.

**Failure behaviour.** A tool failure for one candidate marks that cell `unknown_missing` with `tool_error_ref` and reason `measurement_unavailable`; the run continues, and the cell counts as attempted for the sweep (Section 6.6). If failed cells for one capability exceed `const_sweep_tool_failure_share` of that capability's cells, the run ends `unresolved` with `dependency_unresolved` and `dependency_detail: capability_failure_share_exceeded`. Rows for candidates that never reach assessment (unresolved identity, or budget exhausted mid-sweep) are materialized against an explicit `not_assessed` default with the reason.

### 4.12 C12 Leaderboard Service

**Responsibility.** Render candidate decisions it does not compute: task-scoped, versioned, evidence-backed snapshots with explanations; never a universal ranking across task contexts.

**Snapshot record.** `snapshot_id`, `task_context_id@v`, `run_id`, `round_id`, `rules@v`, `strat@v`, `evidence_snapshot_id`, `evidence_cutoff`, `result_kind`, `ordering_method` (recorded here although owned by C10), `all_pass_count?`, `candidate_entries[]`, `leaderboard_id` (`lbd_`), `parent_snapshot_id`, `change_records[]` (vs. `parent_snapshot_id`: the parent run's last snapshot within a run chain, otherwise the previous snapshot of the same task; Section 6.8), `tool_coverage {per dimension: n_measured, n_predicted_only, n_nothing, providers[]}`, `reporting_tuple {admitted_n, precision_among_admitted (undefined when admitted_n = 0), coverage_fraction, sweep_completeness, abstention_n_by_reason, incorrect_exclusion_rate?, unsupported_claim_rate?, budget}`, `interaction_estimate_provider` (e.g. `none`), `independence_level_summary`, `human_review_summary`, `outcome_dependence_report_ref?`, `published_at`, `projection_hash`.

**Leaderboard record** (`lbd_<task>_<k>`). `leaderboard_id`, `task_id`, `comparability_key` (hash over the fields of `leaderboard_spec.md` §2.2), `supersedes?`, `current_snapshot_id`, `opened_at`, `closed_at?`. A task has one open leaderboard per comparability key; an edit that changes the key closes the old record and opens a new one with `supersedes`. `leaderboard.current_set` names the `lbd_` and the snapshot it now shows; without one, the most recently published snapshot of that leaderboard is current.

**Candidate entry.** `candidate_ref`, `identity_labels`, `state`, `state_reason`, `position?` (only for `ranked_under_score`), `relevance_to_objective`, `per_criterion_refs[]`, `coverage`, `missing[]`, `counter_evidence_refs[]`, `uncertainty_summary`, `measured_vs_predicted_counts`, `provenance_summary {independent_support_count, shared_experiment_groups}`, `evaluation_completeness`, `review_status` (`none` \| `requested` \| `human_approved` \| `human_rejected` \| `disputed`), `reason_for_position_or_state`, `reused_vs_re_evaluated_counts`.

**Change record** (shared with C10 for criteria). `change_id`, `object_kind` (criterion \| rule \| candidate_assessment \| leaderboard_entry), `object_id`, `from_version`, `to_version`, `operation` (criteria: add \| revise \| merge \| split \| remove; candidates: admit \| exclude \| demote \| promote \| unrank \| rank_changed \| status_changed \| score_changed), `fields_changed[] {field, before, after}`, `cause {critique_id \| claim_id \| human_decision_id \| tool_result_id \| rule_change_id}`, `actor`, `at`, `explanation_status` (`evidence_linked` \| `unexplained`; an unexplained material change renders as a defect).

**Rules.** `task_context_id` is mandatory on every row and no view may sum entries across task contexts, so cross-context aggregation is detectable and rejected rather than merely discouraged. More citations, repeated copies of one study, a higher score, or a stable winner never change a state without a change record whose cause is a claim, tool result, or decision. New evidence may raise, lower, remove, or leave a candidate unranked. Four states are always shown separately; `unassessed` and exploratory candidates appear in a separate view labelled "not evidence-qualified". Precision is never rendered without coverage and abstention from the same tuple.

### 4.13 C13 Tool Broker and Capability Registries

Specified in Section 7. Summary: the core owns the shape of a tool interaction; the adapter owns the vocabulary that fills it; the case configuration owns provider preference and required value kinds. Two registries (tool capability, keyed by domain-neutral `capability_kind` with adapter-bound `capability` labels; model adapter capability) share one `verified_by` contract-test discipline. Every result carries unit, value kind, uncertainty, data version, and a thirteen-field provenance block; `not_attempted` with a typed absence reason and a required-inputs manifest is a first-class outcome; the broker never writes a claim's verification status.

### 4.14 C14 Scoped Memory

Specified in Section 10. Summary: itemized entries with kind, support basis, review state, attributed counters, scope, and provenance; mutations are operations (`add`, `retire`, `supersede`, `retag`), never rewrites; a store-level content-policy chokepoint applies to every write regardless of author; `approved` is reachable only through a human decision or an evaluation record; counts never create procedures; exclusion lessons face the same review as admission lessons.

### 4.15 C15 Run Controller

Specified in Section 6. Summary: the only writer of execution and exchange states; state machines for run, stage, step, and exchange; every bounded loop returns a `LoopOutcome`; attempts, resumes, round continuations, run continuations, evidence-refresh runs, and reopen are distinct; step-level failure isolation with `run_degradation[]`; round continuation only through C8.

### 4.16 C16 Reuse and Staleness Service

**Reuse record** (per step). `step_id`, `input_fingerprint` (hash over input artifact ids and versions, `rules@v`, `strat@v`, evidence cutoff, adapter versions, tool contract versions, the `executed_on` of each tool result unless the tool declares `platform_independent_output`, and `recall_set_hash` over the memory items in the step's `memory.recalled`), `reused_from_step_id?`, `reuse_decision` (`recomputed` \| `reused_valid` \| `reused_overridden_by_human` \| `invalidated`), `validity` (`fresh` \| `stale` \| `superseded`), `staleness_cause?` (`rule_version` \| `evidence` \| `human_edit` \| `adapter_version` \| `tool_version`), `human_decision_ref?`.

**Dependency graph.** Edges derived from `depends_on` and `evidence_refs`: claim → assessment → candidate roll-up → snapshot; criterion version → every assessment applying it; tool result → assessment. A human edit or evidence refresh marks all transitive dependents `stale` and emits a **Rerun Plan**: `items[] {object_ref, reason, cost_estimate, required: bool}`, `approval_rule` (auto-approve when every item is `required` and within step budget; otherwise a non-blocking queue item). Approval approves the plan only: while the run has not ended, approved items are re-assessed in its current round; once it has ended, the plan executes only through a run continuation of kind `rerun` that a person starts (Section 6.8). Reusable without re-evaluation: deterministic builds and tool results whose fingerprints match, prior evidence records. Always re-evaluated whenever any of their input versions changed: criterion applicability, candidate roll-up states, adjudications, snapshots, and model-authored rationale outside a reused assessment. A per-cell assessment record, with its reason record, is reusable when its own fingerprint (candidate identity, `rule_ref@v`, `evidence_snapshot_id`, `strat@v`, assessor model or tool version, tool contract versions, `executed_on` and `recall_set_hash` as for the step fingerprint; never reused across policy arms; a record produced with any provisional item recalled is never reused in a `cold` or `frozen` run or in another group) is unchanged. Artifact existence is necessary and fingerprint match sufficient for reuse; human-approved records are never re-derived silently.

**Reuse manifest** (on resume). `resumed_from_run_id`, `resumed_from_checkpoint_id`, `reused[] {record_ref, input_fingerprint, why_legal}`, `recomputed[]`.

### 4.17 C17 Progress Projection

Specified in Section 11. Summary: a pure fold over C1 producing three-level progress with declared `denominator_kind`, no cross-stage percentage, a separate budget meter, elapsed and last-activity times, freshness labels computed client-side, and a `subscribe(stream_id, from_seq)` replay-then-tail contract with compaction snapshots.

### 4.18 C18 Human Review Queue

Specified in Section 12. Summary: owns the durable `waiting_human` state and the `blocked_on_review[]` projection; every human action creates an immutable, attributed `hd_` record; a trigger table states which actions require expert review and which proceed automatically; human submissions enter as provisional claims and are admitted only by a reviewer other than the submitter.

### 4.19 C19 Evaluation and Promotion Authority

Specified in Section 13. Summary: owns the Evaluation Protocol Manifest (no run without a `proto_` is admissible as evidence), the policy arms, the Round Progress Record, the three pools with a sealed final pool, the promotion conjunction, hidden evaluator functions and evaluator epochs, the `claim_scope` block on every report, the Case Acceptance Register, and preregistration events. It never approves criteria; that belongs to C18 and C10. Its interfaces to C6 (budgets), C1 (events), C13 (tool set identity), and the Run Binding are declared fields of the manifest.

### 4.20 C20 Strategy Version Archive

**Strategy version record.** `strategy_version_id`, `parent_version_id`, `change_class` (`prompt_text` \| `procedure_memory` \| `tool_selection_rule` \| `retrieval_rule` \| `failure_handling` \| `model_weights`), `change_summary`, `authored_by`, `authored_at`, `components {role_prompts, delegation_policy_table, tool_selection_policy, memory_retrieval_policy, approved_memory_snapshot_ref}`, `evaluations[] (evr_ refs)`, `metrics {own: mean, lower_confidence_bound, n_repeats, z; lineage: aggregated outcomes of derived versions and refresh runs, excluding every `final`-pool run and its refresh and rerun runs}`, `proxy_vs_held_out_gap`, `held_out_touches`, `status` (`candidate` \| `promoted` \| `keep_candidate` \| `rejected` \| `rolled_back` \| `retired`), `promotion_decision_ref` (`ops_`), `rollback_target`, `expiry_at`, `promotion_policy_version` (immutable per run, declared in the Run Binding, outside any evolvable surface). Versions are never deleted. Rollback to any archived version is a one-step operation journaled as an event.

---

## 5. Collaboration protocol (C7)

### 5.1 Roles

| Role | Kind | Receives | Produces | Independence contribution |
|---|---|---|---|---|
| Planner/Delegator | agent | task context, result returns, ledger refs | plan, steps | none (orchestration) |
| Evidence Retriever | agent with tool budget | step brief, open questions | sources, claims, search coverage records | provenance duties; counter-evidence search obligation |
| Proposer | agent | step brief, evidence slice, criterion templates | proposal (with `considered_and_rejected[]`, `expected_change`, `falsification_test`) | none |
| Deterministic Validator | code (adapter checks + registry invariants) | proposal | typed findings with stable codes | deterministic |
| Blind Critic | agent, preferably different model family | artifact refs and the ledger slice only; never the proposer's rationale or prior rounds in `critique` mode | critique with `checks[]` and `findings[]`, each with an external referent | blind, possibly cross-family |
| Deterministic Adjudicator | code (precedence table) | validator findings, critique, proposal | adjudication artifact; escalation only on persistent disagreement about a referent | deterministic |
| Escalated Adjudicator | agent, cross-family where available | the disputed referent and both positions | decision with recorded dissent or `unresolved` plus a named evidence request | cross-family or none (recorded) |
| Human Reviewer | person | queue item with proposal, critique, evidence, consequences | `hd_` decision | human |
| Evaluator | code plus hidden evaluator functions; runs outside the decision path | fixed snapshots | evaluation records | separate |
| Reflector | agent with a small fixed budget | at a round end, at the run end, and when an expert correction is recorded: the round's typed critique findings, tool error-and-recovery records, expert corrections (`hd_` edits), and termination reasons; never raw rationale, candidate verdicts, evaluator-only content, or `recovery_mapping` decisions | at most `const_reflection_item_cap` provisional skill or lesson drafts, each through the content-policy chokepoint, or an explicit `nothing_reusable` record | none (drafts only; Section 10.5) |

Counter-evidence is an obligation of the Retriever plus deterministic verification, not a persona. Multiple LLM proposers are not used for diversity (hivemind similarity evidence). Personas are addable by configuration and must be justified by measurement.

### 5.2 Exchange flow and bounds

`proposed → critiqued` on critic return; `→ completed` when every required check has a verdict and no unaddressed major finding lacks an override reason; `→ rejected` on an evidence-backed hard exclusion; `→ revising → proposed` when a finding is actionable and `review_exchanges` budget remains; `→ adjudicating` on persistent disagreement about an identified referent; `→ unresolved` on budget exhaustion. Default bound per subject: one proposal, one critique, one revision. Self-correction turns (proposer vs. deterministic validator) are a separate budget so a proposal cannot exhaust its exchanges without ever being critiqued.

A critique whose findings carry no external referent (a ledger entry it disputes, a tool result it cites, a criterion it claims missing, a candidate exclusion it questions) is recorded as `restatement`, does not count as a review exchange, and triggers no revision.

### 5.3 Critique checks (mandatory, typed)

`checks[]` entries: `check_id`, `target_artifact_version`, `check_type` ∈ {`objective_conformance`, `evidence_support` (ledger refs present and `verification_status = supported`), `unit_applicability_consistency`, `counter_evidence_considered`, `candidate_symmetric_scrutiny` (same test applied to the reference candidate and competitors), `falsification_test_evaluated`, `termination_condition_met`}, `verdict` (pass \| fail \| unknown), `severity`, `evidence_refs[]`, `actionable_next_step` (evidence request \| tool request \| human review). A proposal cannot move to `completed` unless `objective_conformance`, `counter_evidence_considered`, and `candidate_symmetric_scrutiny` have verdicts.

### 5.4 Independence Declaration (per decision) and per-critique disclosure

Per critique: `independence {inputs_disclosed[], inputs_withheld[], saw_prior_critique, saw_proposer_rationale, critic_model_family, proposer_model_family, marker}` where `marker` is the Section 0.4 independence marker; `saw_proposer_rationale = true` or same-model ⇒ the critique cannot raise the decision's independence level. A `revision_check` (critic receives its own prior critique plus the structured `changes[]`, never the rationale) is a distinct `check_kind` that cannot raise the level either.

Per decision: `independence_declaration {checks[] {check_kind: deterministic_rule/blind_model_critique/cross_family_model_critique/source_catalog_verification/tool_measurement/human_expert_review, actor_id, model_family?, result, finding_refs[]}, independence_level: none/heterogeneous_model/deterministic_plus_model/human_reviewed, warnings[]}`. The core refuses to publish `recommended` when the case configuration requires an absent check. The leaderboard renders the level. If cross-family critics are unavailable, the record says `false`; independence is never claimed.

### 5.5 Adjudication precedence (deterministic)

Ordered table over typed findings: (1) deterministic validator hard failure ⇒ `rejected`; (2) `evidence_support` fail on a hard-exclusion claim ⇒ `revising` or `rejected`; (3) unresolved `candidate_symmetric_scrutiny` fail ⇒ `revising`; (4) open `counter_evidence_considered` fail ⇒ evidence request via C8; (5) all required checks pass ⇒ `completed`; precedence is keyed to `claim_type` and `verifier_operating_point` so an `interpretation_synthesis` support never outranks `data_derived` counter-evidence. Any evidence-free promise value is capped (the inspected reference's rule-only cap is adopted as a pattern). Dissent record on every decision: `dissent[] {finding_id, raised_by, severity, status: addressed/overridden/deferred, override_reason, evidence_refs[]}`; validation fails when an unaddressed major finding lacks an override reason.

### 5.6 What role separation is for

Fresh, scoped contexts per role (context hygiene) and recorded independence, not accuracy by discussion. The Planner splits work to keep contexts short, never to multiply opinions. The journal distinguishes role-separated single-pass work from debate by the absence of `exchange.revised` events beyond the default bound and by the `restatement` label.

---

## 6. Run control (C15, C8, C6, C16)

### 6.1 State machines

| Level | States | Terminal | Writer |
|---|---|---|---|
| Run | queued, running, waiting_tool, waiting_human, retrying, paused, completed, unresolved, failed, cancelled | completed, unresolved, failed, cancelled | C15 |
| Stage | Run states plus skipped | completed, unresolved, skipped, failed, cancelled | C15 |
| Step | the run states plus rejected | completed, rejected, unresolved, failed, cancelled | C15 |
| Exchange | proposed, critiqued, revising, adjudicating, completed, rejected, unresolved | completed, rejected, unresolved | C15 on behalf of C7 |
| Candidate decision | unassessed, provisional, recommended, rejected | all revisable with a change record | C11 → C12 |

`waiting_human` is entered by C15 on a C18 queue item and left on an `hd_` record, on a `preregistration.recorded` for a preregistration item, on a cancel, or on a run continuation that closes the run; C18 projects `blocked_on_review[]`. Every terminal transition carries a `termination_reason`. A recovered attempt gets a new `att_` and a `finalized_by` on the old one.

### 6.2 LoopOutcome (every bounded loop)

`loop_kind` (self_correction \| review_exchange \| tool_retry \| evidence_request \| screening_round \| model_tool_iteration \| reflection), `iterations_used`, `budget`, `outcome` (completed \| rejected \| unresolved), `termination_reason`, `open_questions[]` (`oq_` refs), `partial_results_ref?`, `partial_results_policy` (`retained_as_unverified` \| `discarded`). No caller may read a missing terminal marker as success; a model tool loop hitting its iteration cap reports `budget_exhausted`, not a plausible answer.

### 6.3 Continuation decision

`continuation_decision {round_id, trigger_question_refs[], trigger_kind, expected_gain_statement, budget_class, decision: continue/stop, stop_reason}`. Continue only when a C8 question has a referent, a non-empty `expected_decision_change`, and an untried method within budget. Stop reasons once the round's candidate sweep is complete (Section 6.6), each yielding `completed`: `sufficient_support` (no open question carries a non-empty `expected_decision_change`), `round_limit_reached` (the binding's `screening_rounds_budget` is used; open questions carry forward to the next run and are not dropped; the normal end of a `P0` run), `no_actionable_step` (every open critique lacks an external referent), `diminishing_information_gain` (two consecutive rounds yield identical snapshots with no new ledger entries). Stop reasons before the sweep is complete, each yielding `unresolved` with a `unswept_cells_manifest`: `repeated_failure` (same method failed k times → queue item), `budget_exhausted`, `dependency_unresolved`. Candidates with incomplete records remain `unassessed` or `provisional`, never silently resolved. Precedence when several reasons apply: `round_limit_reached` when the round budget is consumed, otherwise `sufficient_support`, then `diminishing_information_gain`, then `no_actionable_step`; open questions are recorded on the round either way. The run state says whether the work finished; how well the evidence supports each candidate is carried by candidate states and the reporting tuple, never by the run state.

### 6.4 Failure isolation and degradation

A tool failure marks the step `unresolved` with the typed error and the affected cell `unknown_missing`; the run continues. `run_degradation[] {degradation_kind: provider_absent/provider_degraded/fallback_substituted/budget_reduced, component, reason, call_scoped_absence_refs[], approved_by?}` makes fallbacks visible rather than inferred from provenance labels. Call-scoped `not_attempted` results are the evidence beneath run-scoped degradation records, so no one approves every missing lookup.

### 6.5 Budgets and checkpoints

Budget envelope per Section 4.6; per-loop-class limits are separate fields. Checkpoints (`ckpt_`) are written at stage boundaries, after each rule pass of the candidate sweep, and before any `waiting_human`; a sweep checkpoint carries `sweep_cursor {rule_ref, seed, completed_candidate_count, completed_cell_refs_hash}`; a checkpoint names the `seq` to replay from and the step states to restore (`completed` only when an evaluated artifact exists, else `queued`). Resume produces a reuse manifest (Section 4.16).

### 6.6 Candidate sweep

Stage 6 assesses every candidate and rule inside the run's bound `sweep_scope`: `full_universe` for a baseline run; the items of an approved Rerun Plan for a rerun run (`rerun_plan`); the candidates and rules touched by new evidence for an evidence-refresh run (`refresh_delta`). `sweep_scope` is bound per run and governs its first round. A continuation round inside an adaptive run sweeps the candidates and rules named in its triggering questions' `affects[]`, recorded on the round as `round_scope`. A rerun after a human edit to a completed run is a run continuation (Section 6.8), of kind `rerun` with `sweep_scope: rerun_plan` or of kind `continue` with the parent's scope; a completed run is never re-entered. It never stops at the first admissible candidate and never samples within its scope.

1. **Identity first.** Identity resolution runs for every candidate before any rule is applied. Unresolved identities become `not_assessed` rows with a queue item; ambiguous ones wait in the queue without blocking the sweep.
2. **Breadth-first by rule.** Confirmed rules are applied one at a time across all resolved candidates, in a `sweep_order` built from an ordering policy over rule classes (deterministic computation, then curated lookup, then literature retrieval) and a randomization seed, both registered at stage-1 preregistration; the concrete `sweep_order` over rule ids is registered at stage 2 with the rule-set version. Within a rule, candidates are processed in an order randomized with the registered seed.
3. **No short-circuit.** A candidate that fails a hard rule is still assessed on every remaining rule; rejection is computed at roll-up after the sweep. Complete per-candidate records are what the candidate pages, the outcome dependence report, and the sensitivity configurations need, and a short-circuited candidate could not be re-evaluated under an alternative cutoff without a rerun.
4. **Budget reserved per rule.** At plan time, before criteria exist, C6 issues a first feasibility verdict from the universe size and `const_expected_rule_count` per dimension, a `control_only` budgeting constant set by the operator from the calibration cases when they exist, otherwise from the adapter's template count, never from the original list; its author declares `historical_list_exposure`, it never enters agent context, and it does not constrain the derived count. After stage-2 registration and identity resolution, it reserves each rule's budget as a per-candidate cap times the number of resolved candidates and issues a second verdict, emitted with `progress.estimate_revised`. The cap is identical for every candidate (symmetry obligation, `case_study_protocol.md` §6.4). If either verdict shows that the envelope cannot cover the sweep, the run says so before any rule is applied, and the operator raises the budget, registers a smaller universe under a stated rule, or accepts that the run will end `unresolved`; nothing is trimmed silently.
5. **Attempted cells.** A cell is attempted when it is not marked stale and holds a verdict from an admitted value, `inapplicable`, `unknown_conflicted`, `unknown_missing` with an absence check record, or `unknown_missing` with a tool error after bounded retries.
6. **Checkpoint per rule pass.** Each rule pass is one step; a `ckpt_` with a `sweep_cursor` is written after each rule pass (Section 6.5). On resume inside a rule pass, cells already written with an unchanged fingerprint are reused (Section 4.16), and the remaining cells continue in the same seeded order.

**Sweep complete** means, for the bound scope (or a continuation round's `round_scope`), every candidate in scope has a row with a state, and every resolved candidate in scope has an attempted cell for every rule in scope; records outside a partial scope are carried forward with `reuse.decision: reused_valid`. Only a `full_universe` run supports the Target B coverage claim and the row-count check of `evaluation_plan.md` §8.4. Volume is the universe size times the number of confirmed rules; for the primary case, 3,171 rows and one per-criterion record for each confirmed rule on each resolved compound. If a rule's reservation runs out mid-pass, the remaining cells of that rule become `not_assessed` with reason `budget_exhausted`; because the within-rule order is randomized, that remainder is a random subset, and its size and members are listed in the run's `unswept_cells_manifest`.

### 6.7 When a run ends

| Run state | When | Termination reasons |
|---|---|---|
| `completed` | the sweep is complete and the round loop has stopped | `sufficient_support`, `round_limit_reached` (normal end of `P0`), `no_actionable_step`, `diminishing_information_gain`; `human_decision` when the sweep is complete |
| `unresolved` | the sweep could not complete | `budget_exhausted`, `repeated_failure`, `dependency_unresolved` (including derivation unavailable and a capability failure share above `const_sweep_tool_failure_share`) |
| `failed` | an unrecoverable system fault | the fault record |
| `cancelled` | an operator stops the run before the sweep is complete | `cancelled`, or `human_decision` |

`waiting_human` and `waiting_tool` are pauses, never ends: a run waiting for expert confirmation of `rules@v1` holds at Stage 5 until an `hd_` record arrives or an operator cancels. New evidence after a run ends starts a refresh run with a new snapshot (Section 3, Stage 11); it never reopens a completed run's sweep.

### 6.8 Editing and continuing runs

People can edit what a run works with and continue its rounds and the run itself, from either surface. Records stay immutable: an edit creates a new version of its subject, and continuing either stays in the same run or starts a new run in the same **run chain** (`chain_`), which the surfaces show as one continued run with rounds numbered across it. Three terms are kept apart: **resume** restarts an interrupted run (same `run_`); a **round continuation** adds a round inside a run (Section 6.3); a **run continuation** starts a new run in the chain.

| Person wants to | Run state | What happens | Same run? |
|---|---|---|---|
| resume after a pause or a host stop | not ended | resume from the last checkpoint (Section 6.5) | yes |
| decide pending review items; approve, edit, or reject proposals, attributes, and rules the run derived | not ended (waiting or paused) | `hd_` records and stale marks; the run goes on from its checkpoint with the decisions applied. A rule set confirmed inside the run is a run output, so editing it needs no new run. Cells made stale by such a decision are re-assessed in the current round before the sweep counts as complete; this uses no round budget | yes |
| add a round | not ended, round budget left, and neither bound to a `proto_` arm nor registered as prespecified | a `human_request` open question naming its subject (Section 4.8); the next round opens on it | yes |
| add a round beyond the round budget, add a round to an evaluation-arm or prespecified run, raise any budget, or continue after the run ended (`completed`, `unresolved`, `cancelled`, `failed`) | any | run continuation | no: new run, same chain |
| change a bound field: task context (objective wording, constraints, scope entities, candidate universe), the starting rule set named in the binding, policy arm, strategy version, memory mode, evidence cutoff, tool availability, run group | any | new versions, then a run continuation that binds them | no: new run, same chain |
| rename a run or add notes and tags | any | `run.annotated`; presentation only, never a fingerprint input | yes (no new work) |

**Run continuation.** The person chooses Continue and sets, in one dialog or command, the continuation kind, rounds, budgets, memory mode, policy arm, strategy version, evidence cutoff, tool availability, group, and any task-context edits. The dialog lists `edits_since_parent[]`, each a reference to a new version or decision record; rule changes appear only as the `hd_` records that made them and are never created by the continuation. It also shows the estimated reuse, the chain's cumulative cost (`chain_cost`), whether a new leaderboard will open, and what happens to the parent. The command carries one `basis` per stream it read (the parent's run stream and the task stream) and the expected version of every listed edit; any change since is `rejected_stale_basis` (Section 2.4).

- **Kind and scope.** A new evidence cutoff makes the continuation `refresh` (`sweep_scope: refresh_delta`). Otherwise it is `continue`, bound to the parent's `sweep_scope`, unless the person chooses to execute only an approved Rerun Plan, which makes it `rerun` (`sweep_scope: rerun_plan`). The first run of a chain is `root`. Only a run bound to `full_universe` supports the coverage claim (Section 6.6).
- **Reuse.** C16 reuses every record whose fingerprint is unchanged, the recall set included (Section 4.16), so only stale, unswept, and newly added cells are computed, and every reused record names the run it came from. From a `failed` parent, only records committed before the fault's `cause_seq` are reusable.
- **Closing a parent that has not ended.** It is closed with termination reason `human_decision`, as `completed` when its sweep is complete and `cancelled` otherwise, and its end record names `continued_by`; the dialog says so before confirmation. Its open review items are withdrawn (`human.review_withdrawn {reason: continued, replaced_by_item}`), their claims are released (`human.review_claim_released {reason: withdrawn}`), and they are raised again in the continuation with a link to the withdrawn item; a later decision on a withdrawn item is `rejected_not_permitted_in_state`. Closing a registered run before its sweep completes needs the `evaluator` role and interactive entry, and writes a protocol-deviation entry in the Case Acceptance Register.
- **Carried forward.** The parent's open questions carry into the continuation. Its rounds are new `round_` records, numbered on the surfaces after the parent's. The event `run.continued {parent_run_id, continuation_kind, edits_since_parent}` is written in the task stream.
- **Leaderboard.** The continuation publishes the next snapshot of the task leaderboard with `parent_snapshot_id` set to the parent run's last snapshot; change records are computed against that snapshot and name the edit or decision behind each change. If the edits break comparability (objective wording, mode, required scope entities, universe identity, hard constraints, or comparison basis; `leaderboard_spec.md` §2.2), the dialog says so, and the continuation opens a new leaderboard record (`lbd_`; Section 4.12) with a `supersedes` link to the old one.
- **Branches.** A second continuation from the same parent is a branch, created only when the person confirms it as one (`branch_label`). Without that confirmation the command is `rejected_stale_basis` if the issuer had not seen the existing continuation and `rejected_not_permitted_in_state` if they had, so a chain never forks by accident. Each branch's snapshots chain through `parent_snapshot_id`. Each leaderboard (`lbd_`) shows the snapshot set by `leaderboard.current_set` (`board set-current`), otherwise its most recently published one.
- **What a continuation may claim.** Each run of a chain keeps its own binding, termination reason, and sweep completeness. A chain is never reported as one run, and every report citing a run other than the root states `chain_cost`. A continuation is **outcome-informed** when any run of its chain had published a leaderboard snapshot or a recovery comparison before the continuation was created, unless it matches a rule registered at stage-1 preregistration (Section 13.6): a registered sensitivity configuration, or the registered `budget_extension_rule` (a continuation that changes only budgets, after `budget_exhausted`, within the registered maximum). Outcome-informed continuations are `exploratory` in the Case Acceptance Register. The baseline acceptance claim cites the prespecified run, or its registered budget extension, never another run of its chain. Reuse never crosses policy arms (Section 4.16).

### 6.9 Run groups

A **run group** (`grp_<slug>`) bundles tasks with their runs and is the namespace of their memory (C14 `scope.group_id`). C15 owns group records and their lifecycle; C14 uses `group_id` as the memory scope. Record: `group_id` (stable), `name` (renamable without touching any run or memory item), `description`, `created_by`, `created_at`, `state` (`active` | `archived`). Every store root has a default group; every task context names its group, and every Run Binding binds the group of its task.

- **Switching.** The active group is a session setting (`ses_.active_group_id`), never a server-wide one, so two sessions, including one person's terminal and browser sessions, can show different groups. Switching filters what is listed (tasks, runs, chains, leaderboards, review items, skills and lessons) and sets the default group for new tasks; it changes no record and never affects a running run, whose group is bound. Every surface always shows the group it is in, a command can name another group explicitly, and a new session starts in the person's last active group.
- **Creating, renaming, archiving.** `group.created`, `group.renamed`, `group.archived`, and `group.reactivated` events go in the group's stream. Archiving is refused while any run in the group has not ended. An archived group accepts no new task or run; its records stay readable, review decisions on items of its runs remain possible, and its runs can be continued into another group. An archived group can be reactivated. Groups are never deleted, so no run or memory item is ever orphaned.
- **Moving work.** A task with no runs can move to another group: `task.group_changed` (a new task-context version) in the task stream, with `group.task_removed` and `group.task_added` in the two groups' streams. A task with runs cannot move, because its runs recalled memory from their group; the person copies it instead.
- **Copying a task.** A copy is a new task with `derived_from_task_id` in the target group. It references the same `case_id@v`, so the case-source documents and the encrypted historical-criteria intake remain single artifacts with one access log, and no `evaluator_only` field is duplicated. Preregistration does not carry over: a copy's runs are `exploratory` until their own preregistration is recorded.
- **Continuing into another group** is a copy followed by a run continuation of the copied task. The chain link is kept (`continues_run_id`), the run's group equals its task's group, and the copy opens its own leaderboard. From then on, memory recall comes from the new group, provisional items of the old group are not carried (Section 10.2), and the chain view marks the switch.
- **Memory across groups.** Provisional skills and lessons stay in their group; approved items are recallable in every group, subject to the firewall rules of Section 10.2. Acceptance-bearing runs use `cold` or `frozen` memory whatever their group.

---

## 7. Tool layer (C13)

### 7.1 Tool contract (declared once per tool, versioned)

`tool_id`; `capability_kind` from the core's domain-neutral list (`entity_resolution`, `relationship_evidence_lookup`, `relationship_estimate`, `attribute_estimate`, `source_retrieval`, `document_reading`, `dataset_context_lookup`, `rule_evaluation`) and `capability` as the adapter-declared binding of that kind (the drug adapter binds `identity_resolution` → `entity_resolution`, `interaction_evidence_lookup` → `relationship_evidence_lookup`, `interaction_estimate` → `relationship_estimate`, `property_estimate` → `attribute_estimate`, `literature_retrieval` → `source_retrieval`; the core resolves on `capability_kind`, so no pharmacology term lives in the core); `contract_version`, `implementation_version`, `upstream_version_source`; `purpose_statement`; `evidence_kind_produced`; `claim_strength_ceiling` (`predicted` \| `curated` \| `measured`; the broker rejects payloads exceeding it); `input_schema` (per field: type, unit, required, allowed values, identity precondition); `output_schema` (per field: type, mandatory unit, `value_kind`, uncertainty block, source-record reference); `uncertainty_model` (`none` \| `interval` \| `stated_sd` \| `class_probability` \| `rank_only` \| `qualitative`); `error_schema`, `absence_schema`; `determinism` (`deterministic` \| `seeded_stochastic` \| `nondeterministic` \| `external_state_dependent`) with reproducibility-key fields; `cost_latency_class` (`interactive` \| `short` \| `batch` \| `offline_human`), `quota_cost`, `money_cost_class`; `rate_limit_declaration`; `prerequisites`; `supported_platforms[] {platform: linux/windows, platform_support_basis: checked/upstream_documented/unchecked}`, `execution_location` (`in_process` \| `local_subprocess` \| `remote_endpoint` \| `compatibility_environment`), and `platform_independent_output` (Section 14.2); `license_and_redistribution`; `side_effect_class` (`read` \| `idempotent_write` \| `non_idempotent_write`; every v1 evidence tool is `read`), `idempotency_key_required`; `timeout_ms`; `human_review_required` with conditions; `deprecation` (`active` \| `degraded` \| `deprecated` \| `withdrawn`, replacement id).

### 7.2 Invocation record

`invocation_id`, `run_id`, `round_id`, `step_id`, `requesting_actor`, `question_id`, resolved `tool_id` + versions, `normalized_input`, `input_hash`, `idempotency_key`, `requested_at`, `started_at`, `finished_at`, `latency_ms`, `attempt_index`, `retry_of`, `budget_charged`, `cache_hit`, `cache_key`, `cache_written_at`, `provider_path` (which model or transport adapter carried the exchange).

### 7.3 Result record (payload of the `tool_result` artifact)

`outcome` (`ok` \| `partial` \| `empty` — the source answered and held no record \| `not_attempted` — a dispatch pre-check failed, with `absence_reason` and `required_inputs_manifest` \| `failed` — a runtime error, with `error {code, class, retryable, operator_action, structured_diagnostic {path, expected, found, allowed_values}}` \| `unknown_outcome` — synthetic result for a call whose step aborted, with an idempotency hint); `record_state` (`returned` \| `superseded` \| `stale`); `values[] {name, value, unit, value_kind, uncertainty, n, conditions_ref, source_record_ref}`; `data_version`; `determinism_record`; `executed_on {platform, execution_location}` (Section 14.2); `evidence_kind`, `claim_strength_ceiling` (echoed); `supports_claim` (always null from the broker); `warnings[]`; `truncation_record`; `provenance` (7.4).

Error classes: `input_invalid`, `identity_unresolved`, `out_of_domain`, `auth_missing`, `auth_rejected`, `rate_limited`, `transient_network`, `upstream_server_error`, `timeout`, `quota_exhausted`, `parse_failed`, `schema_violation`, `environment_missing`, `model_unavailable`, `internal_error`. Absence reasons: `not_configured`, `not_installed`, `requires_other_environment`, `unreachable`, `unauthorized`, `rate_limited_exhausted`, `out_of_domain`, `identity_unresolved`, `no_record_found`, `budget_exceeded`, `declined_by_policy`. The discriminator between an absence and an error with the same name is whether dispatch pre-checks passed.

### 7.4 Provenance block (mandatory on every ledger write from a tool)

`kind`, `upstream_ref` (DOI, accession, URL, or file hash), `retrieved_at`, `tool_id`, `contract_version`, `implementation_version`, `data_version`, `parameters_hash`, `invocation_id`, `run_id`, `actor`, `license_id`, `independence_key`. The broker refuses results with incomplete provenance; services without version information produce `unknown` values, visibly.

### 7.5 Registries, dispatch, retry, feedback

Resolution by `(capability_kind, question_kind, required_value_kind)`, never by tool name (adapter-declared `capability` names are labels bound to a core kind); a criterion requiring a measured value cannot be matched to a prediction-only provider — the assessor records `unknown`. Pre-checks in order: input validation, identity precondition, license gate, prerequisite probe, budget and rate-limit token; a failed pre-check yields `not_attempted`. Retry policy lives in the broker (retryable classes only, bounded attempts, exponential backoff with jitter, idempotency by `input_hash`, `retry_of` lineage); retry allowance lives in the plan step budget. A per-provider circuit breaker marks a provider `degraded` after N consecutive failures, journals `tool.degraded`, writes `run_degradation[]`, and falls through to the next provider or records absence. Broker-level exactly-once for non-idempotent writes (ledger, leaderboard, registry) is enforced by keys independent of model instructions.

Feedback: every result, error, and absence becomes a typed `tool_observation` entering the next agent turn (question asked, outcome, values with units and kinds, uncertainty, absence reason, `decision_relevance`, `unverified_flag`), after output-schema validation and with a truncation record; a rejected malformed payload is itself fed back as an error observation.

### 7.6 Model Adapter Capability Record and contract tests

`adapter_id`, `provider_family`, `accepts_tool_schemas`, `returns_tool_results_to_model` (yes \| no \| unknown), `max_tool_iterations`, `structured_output_mode` (`native_tool` \| `json_mode` \| `text_parse`), `error_feedback_supported`, `verified_by` (contract-test run id), `verified_at`, `verification_state` (`current` \| `stale` → treated as `unknown`). The core refuses feedback-dependent protocols unless the record says yes and degrades explicitly to a recorded step-level `unresolved` or a policy-approved single-shot mode. Contract tests (interface-level only; they do not establish outcome quality): *echo* (a nonce only the tool can supply is reported), *error recovery* (a typed error is followed by a corrected call), *two-step dependency*, *iteration cap* (reports `budget_exhausted`), *idempotency* (replayed key does not double-execute), *provenance* (every cited result retrievable by invocation id), *conformance* (the same exchange through each adapter, recording `provider_path`).

### 7.7 How a successful call is prevented from being recorded as validation

Five structural mechanisms: `outcome` and `verification_status` live in different records and the broker cannot write the second; `claim_strength_ceiling` forbids storing a predictor's output as a measurement; the assessor compares the criterion's required value kind with the record's `value_kind` and a mismatch yields `unknown`; every leaderboard cell renders its value kind and provenance; `human_scientific_approval` is writable only by C18.

---

## 8. Evidence and criteria workflow (C9, C10)

### 8.1 Source-agnostic evidence workflow

Stages: title screening → title-and-abstract screening → full-text reading when `access_state = full_text_available` → claim extraction with locations → verification (`verifier_id`, operating point) → admission. Every screened item keeps its decision; shortfalls are reported, never padded. Duplicates and revised versions collapse through `duplicate_of` and `supersedes_source`; ambiguous entity names route to identity resolution and, when `name_match_ambiguous`, to the review queue with the claim held `pending`. The drug adapter extends claims with compounds, targets, assay endpoints, units, and conditions through adapter-typed `entities[]` and `scope`.

### 8.2 Identity service

Core identity record driven by adapter schemes: `candidate_id`, `preferred_label`, `identifiers[] {scheme, value, scheme_authority, as_of}`, `aliases[] {alias, alias_source, alias_kind: code/brand/synonym/salt_form/transliteration}`, `identity_link_basis` (`exact_identifier_match` \| `authority_crosswalk` \| `name_match_single_candidate` \| `name_match_ambiguous` \| `unresolved`), `merge_history[]`, `identity_review_state`. A claim grounds an assessment only on an identifier match or authority crosswalk; merging rows is human-confirmed with a change record; salt and formulation differences are aliases unless an attribute's applicability depends on them.

### 8.3 Criterion derivation and lifecycle

Templates from the adapter enter as `proposed`. The Proposer derives attributes and rules from objective and admitted evidence (reference-blind evidence slice: claims whose only subject is the reference candidate are excluded from derivation context and counted in the visibility manifest; the derivation nonetheless runs `reference_disclosed` because the objective and target configuration already narrow the space, and full blindness is not claimed). Critique, validator invariants, and adjudication follow Section 5. Each operation produces a change record; confirmation of any hard exclusion, expert-set cutoff, conflicted attribute, merge, or removal requires an `hd_` record; `rules@v<n>` is confirmed with its admission-predicate hash and preregistered.

**Recall-first enumeration, then consolidation.** Derivation runs in two passes so that pruning never hides what was never proposed. (1) *Enumeration*: for each dimension in the case configuration, the Proposer lists every attribute that admitted evidence treats as decision-relevant, drawing on three source classes kept separate in the search coverage record: standards and guidance documents of the field, published prioritization or screening studies other than the case-source documents (Section 8.6), and evidence about the candidates themselves. Enumeration for a dimension stops on saturation, when the last `const_enumeration_saturation_k` screened sources added no new attribute, or on budget, in which case the dimension's search coverage record carries `enumeration_saturated: false` and the snapshot reports it. (2) *Consolidation*: attributes are merged into decision-level criteria by a rule registered before derivation that references no historical count: attributes measuring the same property by different methods merge with a unit-normalization note, and rules whose verdicts agree on more than `const_merge_verdict_agreement` of assessed candidates are proposed for merging. Every merge, split, and drop is a change record with its reason; the resulting count is an output. The enumeration list, with each attribute's fate, is published in R1, so a reader can see where every historical item would have entered and why it survived or not.

**Calibrated derivation strategy (optional, recommended).** How well criteria are recovered depends on the derivation strategy (enumeration procedure, retrieval rules, consolidation rule, prompts), and that strategy can be improved without touching the primary case. External calibration cases (published prioritization studies on other objectives that report their criteria lists, curated by experts) are registered as `development` and `validation` pools under C19; criterion recall and expert-rated reason quality are measured on them, and strategy versions are promoted under Section 13.7. The primary case sits in the sealed `final` pool, is never used for selection, and is opened once with the frozen strategy. Transfer from calibration cases is not assumed: the gap between calibration recall and primary-case recall is reported. Calibration cases are selected by an inclusion rule registered before curation (a stated search and stated criteria), not hand-picked. The comparison component checks every calibration case and its criteria list against `case_source_documents[]` and against the intake items, without showing the comparison to any agent; a case that cites or quotes the manuscript's criteria, or matches an intake item beyond generic dimension names, is excluded with a recorded reason. Curators declare `historical_list_exposure`, and the frozen strategy text passes the criterion-content scan (Section 8.6) before it is bound.

### 8.4 Registered constants

`const_id`, `scope` (`core_policy` \| `adapter_policy` \| `case_configuration`), `value`, `unit`, `cutoff_basis`, `set_by`, `set_at`, `sensitivity_tested {yes/no, protocol_ref}`. Every numeric constant affecting a published verdict is registered, including engineering constants (extraction-confidence floors, duplicate-overlap shares, breaker thresholds) and the coverage floor; none is hidden in code. Host infrastructure registers its engineering constants the same way with `scope: core_policy`: `const_review_claim_lease`, `const_host_suspend_threshold`, and `const_store_write_retry_limit`. The Reflector's cap, `const_reflection_item_cap`, is registered the same way.

### 8.5 Evidence snapshot

`evs_<task>_<n>`: frozen set of admitted claim ids with source versions, `cutoff_at`, `tool_availability_snapshot`, `hash`. Policy comparisons and sensitivity analyses run on fixed snapshots so new data is never mistaken for agent improvement.

### 8.6 Historical-criteria comparison artifact and recovery comparison

**Intake record** (case configuration; `visibility: evaluator_only`; readers enumerated: the comparison function; the review queue for comparison-adjudication items only (`match_basis: expert_judged_equivalent`, after `rules@v` is confirmed), never for criterion-confirmation items; and the evaluator-role recovery comparison panel (`ui_ux_spec.md` §11.1); every access logged with the reading actor). `intake_id`, `provided_by`, `provided_at`, `provenance_form` (`manuscript_main_text` \| `manuscript_supplement` \| `author_supplied_list` \| `reconstructed_from_code` \| `verbal_report`), `verbatim_items[] {label, definition_as_given, dimension_as_given, threshold_as_given, unit_as_given, direction_as_given, notes}`, `completeness_attestation` (`complete` \| `partial` \| `unknown`), `ambiguities[] {item_ref, question, resolved_by, resolution}`. For the primary case the eleven CQAs are not enumerated in the manuscript main text, so this record is an input dependency on the authors.

**Blinding mechanics.** The artifact is excluded by construction from every derivation agent's evidence catalog; each derivation decision's visibility manifest lists it under `omitted_reason: evaluator_only_artifact`, which is the mechanical record of exclusion (a component's self-assertion is not evidence); the access log corroborates. Any criterion version produced after a logged read by a derivation actor is labelled `outcome_informed_exploratory`. Two further leakage paths are closed the same way. *Case-source documents*: the manuscript, its supplement, any preprint or version of it, and any document quoting its criteria list are registered as `case_source_documents[]` and excluded from every derivation catalog under `omitted_reason: case_source_document`; matching uses identifiers, title, and author list, retrieval hits are logged, and residual misses found later are reported. *People and templates*: firewalling agents does not firewall the humans who confirm criteria or the authors of adapter templates. Every template and every criterion-affecting `hd_` carries a `historical_list_exposure` declaration, checked against the access log: an actor with a logged read is `exposed` from that `seq`, and where a `not_exposed` declaration conflicts with the log, the log prevails: the actor is treated as `exposed`, the affected items move to `assisted`, and the conflict is reported in the recovery summary. A derived item any of whose fields was authored or confirmed by an `exposed` or `undeclared` actor counts in the `assisted` recovery view, and the `independent` view counts only the rest. Because comparison adjudication happens only after `rules@v` is confirmed, an expert who adjudicates equivalences afterwards does not change the view of items confirmed before the read, but any later confirmation by that expert is `assisted`. The same access-log rule applies to `historical_stage_artifacts[]` for derivation actors. *Global shaping artifacts*: the objective text, the adapter dimension list, the consolidation rule and its constants, the derivation strategy, and any memory snapshot bound to an acceptance-bearing run (Section 10.2) are usually authored by people who know the list, so a declaration alone would move every item to `assisted`. Instead, each such artifact must be verbatim public text cited by location (the manuscript main text, which does not enumerate the eleven) or pass a **criterion-content scan**: before stage-1 preregistration the comparison component checks the artifact against the intake's labels and definitions (not its dimension names) and returns only `clean` or `match {item_ref}`, so no agent sees the comparison. An artifact *shapes* a derived item when it was in that item's derivation context: a template shapes the items `derived_from` it, and the objective text, dimension list, consolidation rule, and derivation strategy shape every item derived in the run. A `match` moves every item the artifact shaped to `assisted`. This channel carries a weaker guarantee than templates and confirmations, and the recovery summary says so. Both views are always reported, and an acceptance claim names the view it rests on.

**Recovery comparison record** (one per historical item plus one per unmatched derived attribute). `comparison_id`, `historical_item_ref`, `derived_attribute_refs[]`, `mapping_kind` (Section 0.4 nine values), `rule_role_match` (hard_exclusion \| preference \| exploratory \| none), `match_basis` (`definition_and_unit_match` \| `definition_match_unit_differs` \| `verdict_agreement_on_assessed_candidates` \| `expert_judged_equivalent`), `agreement_evidence {agree[], disagree[], not_comparable[]}`, `rationale_refs[]`, `reason_text`, `judged_by` (comparison component id plus `hd_` when expert-judged), `derivation_configuration` of the derived version, `recovery_view` (`independent` \| `assisted`, from the exposure declarations above). Per-snapshot summary: `n_historical`, `n_recovered`, `n_recovered_different_cutoff`, `n_merged`, `n_split`, `n_removed_unsupported`, `n_removed_superseded`, `n_not_recovered`, `n_newly_added`, each with ids, reported by item count and by decision impact (how many candidate states each item changes), in both the `independent` and `assisted` views. A `not_recovered_no_evidence` item is a statement about the historical criterion's documentation, not a system failure, and is worded that way. Expert reason-quality ratings per criterion use a registered ordinal scale; high recovery with poor reason quality is not acceptance.

**Derived artifacts.** Every artifact derived from the intake (recovery comparison records, the `hd_` records deciding recovery mappings, the R4 summary, `evaluation.recorded` payloads that contain them, and the recovery comparison panel's projection) inherits `visibility: evaluator_only`, is excluded from the derivation catalog of every later run of the same case under `evaluator_only_artifact`, and has every read logged with the same exposure consequence as a read of the intake. Task-context versions and `human_request` questions carry `author_exposure` and count as authored fields of every item they shape; memory items carry `historical_list_exposure` (Section 10.5).

**Reads and file access.** Every read of the intake or of an artifact derived from it goes through a confirmed command and writes an `evaluator_only.read {person_id, subject, purpose, via}` event in the case stream; that event is the access log the exposure rule consults. Store files read outside the API are not logged, so evaluator-only content is encrypted at rest under a key the evaluator supplies for each scan, comparison, or panel read and the host does not keep (Section 14.1). File access without the key is not a read. Because the key is the evaluator's, every operation that needs the intake is an evaluator command outside any run: the recovery comparison runs after a snapshot is published and writes `evaluation.recorded` to the case stream, and run completion never waits for it; criterion-content scans run when an item becomes recallable or a shaping artifact is registered. An item not yet scanned is unrecallable in a case with an intake, and an artifact not yet scanned is treated as a scan `match`.

---

## 9. Per-candidate assessment and leaderboard lifecycle (C11, C12)

Records are specified in Sections 4.11 and 4.12; `leaderboard_spec.md` elaborates admission policy and user-facing views. The lifecycle:

1. A confirmed `rules@v` and a frozen `evs_` are bound to the round.
2. Identity resolution runs for the candidate universe; unresolved or ambiguous identities become `not_assessed` rows and queue items.
3. For each candidate and each applicable rule, the assessor requests evidence through the broker by `(capability, question_kind, required_value_kind)`, writes an assessment and a reason record, and marks `staleness: current`.
4. Roll-up computes state and `state_reason`; the four-state table and coverage floor decide `recommended` / `provisional` / `unassessed` / `rejected`.
5. The Leaderboard Service publishes a snapshot with change records against its parent snapshot (Section 4.12), the reporting tuple, tool coverage, and the independence summary; `recommended` entries without the required `hd_` reference are published as `provisional` with `state_reason: awaiting_human_review`.
6. Any later rule change, evidence refresh, or human edit marks dependent assessments stale through C16 and produces a new snapshot with explained changes; prior snapshots remain inspectable.

Publication rules: no snapshot without a visibility manifest for every decision it contains; no `recommended` entry whose reason record fails a disqualifier; no precision figure without coverage and abstention; result kind stated on every snapshot; a unique all-pass candidate under hard rules and a top-ranked candidate under a score are reported as different results.

---

## 10. Scoped memory (C14)

### 10.1 Memory item

`item_id`, `kind` (`evidence` \| `tentative_hypothesis` \| `reusable_procedure`), `section`, `content` (structured: for procedures `when`, `procedure`, `why_useful`, `retire_when`), `scope {group_id, role, layer: task_context/adapter/core}`, `support_basis`, `review_state`, `provenance {run_id, journal_seq, ledger_refs[], derived_from_item_id}`, `counters {helpful, harmful, neutral}`, `counter_events[] {run_id, exchange_id, tag, tagged_by {actor_kind, model_family}, signal_provenance: outcome_label/evaluated_metric/model_judgment/human_judgment}`, `circulation_count` (observability only; barred from ranking and promotion), `promotion_eval_ref?`, `expiry_at`, `supersedes_item_id`, `historical_list_exposure` (of the author, and of the approver once approved; Section 10.5).

### 10.2 Operations and lifecycle

Mutations are journaled operations only: `add`, `retire`, `supersede`, `retag`. No code path rewrites the store; corrections supersede. Active pool capped per scope with small retrieval top-k; pruning is a policy over counters and age that queues items for human review rather than deleting. Recall eligibility is a policy over `(kind, support_basis, review_state, scope)`: approved items inherit across groups; provisional items are recallable only in their originating group and role; nothing provisional crosses groups. For a case with an evaluator-only artifact: no role recalls an item whose provenance run carries `outcome_informed_exploratory`; in acceptance-bearing runs, no role recalls an item whose author or approver is `exposed` or `undeclared` (a logged read of the intake makes an actor `exposed`, and so does having supplied the list); every item recallable in the case passes the criterion-content scan of Section 8.6, and a `match` makes it unrecallable there; and every acceptance-bearing run uses `memory_mode: cold`, or `frozen` over an approved snapshot taken before any intake access, which is itself a global shaping artifact (Section 8.6). In runs that are not acceptance-bearing, an item from an exposed or undeclared author or approver may be recalled, and every item it shapes counts in the `assisted` view. `memory_mode` governs recall only: `cold` recalls nothing, `frozen` recalls only a fixed approved snapshot, and `warm` recalls current approved items plus the group's provisional items; every mode may draft new items (Section 10.5). Agent verdicts and reviewer concerns never become items automatically; a completed computation does not label itself verified (no `support_basis` implies a `review_state`).

### 10.3 Promotion

`approved` is reachable only through an `hd_` (human curation) or a C19 evaluation record on held-out material; procedures evolved in one adapter are never auto-promoted to core; a procedure trial record (`with_procedure` vs `without_procedure` arms on a fixed snapshot) is the only admissible usefulness evidence; counters incremented by a model judgment never count as outcome labels and are displayed as self-judged. A rule-reversal test precedes any promotion of a procedure that influences criteria. Exclusion lessons face the same review as admission lessons, and a recalled exclusion that blocks a candidate must be cited in that candidate's rejection record.

### 10.4 Content-policy chokepoint

Every procedural-memory write, automatic or human, passes `check_procedure(text_fields, forbidden_entity_lists, numeric_claim_policy) → {ok, violation_codes[]}` with core-owned codes (`candidate_identifier`, `specific_entity_set`, `candidate_specific_parameters`, `observed_score_or_threshold`, `observed_performance_value`, `performance_conclusion`, `literature_or_experiment_conclusion`, `outcome_reference`, `prompt_injection_language`, `not_reusable_methodology`, and, for any memory item recallable in, or procedure text bound into a derivation strategy of, a case with an evaluator-only artifact, `historical_criterion_content` from the criterion-content scan of Section 8.6) and adapter-owned lists (including the case's candidate identifiers and aliases, the disclosed reference outcome, and the identifiers and titles of every case-source document registered on the store root). Rejected items queue for human review with their codes rather than being discarded. Candidate-specific conclusions belong in the Criterion Registry as sourced rules or in an exclusion record, never in prompt-injected procedure.

### 10.5 Producing skills and lessons during a run

The surfaces call a `reusable_procedure` item a **skill** and a `tentative_hypothesis` item a **lesson**. Both are about method (how to search, resolve, check, or recover from a failure), never a conclusion about a candidate. A run can produce them while it works:

| Source during a run | When | Drafted by | Support basis of the draft | Exposure of the draft |
|---|---|---|---|---|
| a tool error followed by a successful corrected call | as it happens | C13, from the typed error and the changed input, without a model | `deterministic_check` | `not_exposed` |
| reflection | at a round end and at the run end | the Reflector role (Section 5.1), at most `const_reflection_item_cap` drafts, or `nothing_reusable` | `llm_opinion` | the most exposed of the records it read |
| an expert's correction (unit, applicability, identity, cutoff) | when the `hd_` is recorded | the Reflector, linked to that `hd_` | `llm_opinion` until the expert approves the wording | the exposure of that `hd_` |
| a person writes one | any time, from either surface, with interactive entry | the person | `human_curation` | the person's declaration, checked against the access log |

- **Checked and provisional.** Every draft passes the content-policy chokepoint (Section 10.4) and is stored `provisional`, scoped to the run's group and to the role it concerns, with provenance to the run, round, and records it came from, and with its `historical_list_exposure`. Candidate identifiers, observed scores and thresholds, outcome statements, and the identifiers and titles of registered case-source documents are rejected with codes. The Reflector never reads evaluator-only content, `recovery_mapping` decisions, raw rationale, or candidate verdicts. Agent verdicts and reviewer concerns never become items automatically, and repetition counts never create a skill.
- **Use within the same run.** `memory_mode` governs recall only, and every mode drafts. Only in `warm` mode can a provisional item drafted in round 1 be recalled in round 2, by its role, in its group. Every recall is journaled as `memory.recalled` and enters the step's fingerprint (Section 4.16). Acceptance-bearing runs use `cold` or `frozen` memory: they still draft items for later review, but nothing drafted in the run changes its own behaviour, and the firewall rules of Section 10.2 decide which earlier items they may recall.
- **Becoming reusable.** An item becomes `approved` only through an `hd_` on subject `memory_item` in the review queue, with the approver's exposure recorded, or through a C19 procedure trial on held-out material (Section 10.3). Only approved items are recalled outside their group. Self-judged helpful counts are shown as self-judged and never promote.
- **Cost.** Reflector turns are charged to a separate `reflection_turns` budget class in C6, so policy arms can be matched with and without reflection.
- **Strategy-level improvement** (prompts, playbooks, procedure bundles; Section 13.1) happens between runs, offline, under the C19 promotion gate; a run never rewrites its own strategy.
- **Expectation.** The evidence that within-run reflection improves results is weak (ADR-04), so drafting is capped and cheap, and a skill is relied on only after review or a procedure trial (U-16).

---

## 11. Observability (C1, C17)

### 11.1 Progress semantics

| Scope | Denominator | Rendered as | Indeterminate when |
|---|---|---|---|
| Overall run | stages declared by the plan; revised only through `progress.estimate_revised` | "stages k / n completed · plan revised m×"; never a blended percentage | continuation is trigger-driven, so later stages are not enumerable |
| Stage | units enumerable at stage open (candidates, criteria, queued sources) | "118 / 140 assessed"; percentage only for `enumerated_fixed` | retrieval stages whose count can grow: "completed 37 · planned ≥ 40" |
| Current round / exchange | named steps in the round's completion criteria | "steps 4 / 6 declared" | steps added adaptively mid-round |
| Budget (separate meter) | `rounds_used / rounds_max`, tool calls, tokens, wall clock, human minutes | labelled "budget consumed — not completeness" | never shown as progress |

A percentage is permitted only for `enumerated_fixed`, only inside one scope. An ETA appears only when the denominator is fixed, a configured minimum of units has completed, and the display names its basis. The honest indeterminate indicator shows state, current question, elapsed time, and last-activity age, with no number.

### 11.2 Freshness and replay

Client freshness labels: `live` (event or heartbeat within twice the heartbeat interval), `view_stale` (disconnected; show last applied `seq` and its age; freeze all motion), `activity_unknown` (subscribed, state running, no heartbeat past the step-type stall threshold). Replay contract: `subscribe(stream_id, from_seq)` replays persisted events in order, then tails; every frame carries `seq`; the client keeps `last_applied_seq` and ignores duplicates (at-least-once delivery); reconnect resubscribes at `last_applied_seq + 1`; if the requested sequence predates compaction the server returns a projection snapshot with `snapshot_seq` and resumes there. Serving a run requires only its journal, never a live process. Both operator surfaces use this contract (Section 11.4). Transport (server-sent events or WebSocket for the browser; loopback HTTP or a local socket for the terminal) is an implementation choice; only the contract is specified.

### 11.3 Default view and raw traces

The default surface shows per decision: question, actor, outcome, one-sentence reasoning, linked claims with evidence status, execution state — never raw model output. Raw traces persist behind `trace_blob` links with `visibility: expert | auditor`, opened only by an explicit action that journals `trace.opened` with its actor. A decision record is invalid without at least one evidence link or an explicit "no evidence available" reason.

### 11.4 Operator surfaces

The terminal client and the browser workbench render the same projections with the same C2 labels, the same denominator and percentage rules, the same freshness labels, and the same approval-slot rule ("no human review yet" unless an `hd_` record exists). The terminal shows each tone as a word or glyph as well as a colour, so meaning survives a terminal without colour. A scripted terminal session receives the same records as line-delimited output, one record per line with its stream and `seq` (evaluator-only records excepted; Section 2.4); a wait-until-finished command returns an exit status by terminal state, and only `completed` is success (`unresolved`, `failed`, and `cancelled` each have their own non-success status; ADR-02). The browser resubscribes from `last_applied_seq + 1` whenever a hidden or throttled tab becomes visible and never serves a record from a browser cache. Screens, terminal commands, the parity rules, and the behaviour when both surfaces act at once are in `ui_ux_spec.md` §15.

---

## 12. Human review (C18)

### 12.1 Trigger table

| Requires an expert decision before publication | Proceeds automatically (recorded, reversible) |
|---|---|
| any `hard_exclusion` entering `confirmed`; any cutoff with `cutoff_basis: expert_set`; any `unknown_conflicted` on a hard rule; any `name_match_ambiguous` identity; any attribute merge or removal; any unit normalization that changes a verdict; any `expert_statement` or unreviewed-preprint claim used by a hard rule; any `recommended` publication where the case configuration requires it; any `outcome_informed_exploratory` criterion version; admission of a human submission that would change a candidate state; any `expert_judged_equivalent` recovery mapping; any Rerun Plan above step budget; any approval of a memory item (skill or lesson), or retirement of an approved one | retrieval, screening, extraction, duplicate detection, inapplicability evaluation, preference-weight proposals, exploratory-consideration additions, assessment recomputation after a confirmed rule change, intake and identity resolution, scope-based exclusion, rerun scheduling within budget, run control (pause, resume, cancel) |

### 12.2 Expert decision record (`hd_`)

`decision_id`, `queue_item_ref`, `subject {kind: attribute_version/rule_version/rule_set_version/claim_admission/candidate_state/identity_merge/conflict_resolution/unit_correction/cutoff_setting/submission_admission/recovery_mapping/rerun_plan/memory_item, id, version}`, `decision` (`approve` \| `approve_with_edits` \| `reject` \| `defer_more_evidence` \| `escalate` \| `abstain` \| `request_followup` \| `pause` \| `resume` \| `retire`), `edits[] {field, before, after}`, `reason_text` (required except for approving an unedited proposal), `actor {person_id, role, affiliation_claim, identity_basis: authenticated_account/recorded_attestation}`, `declared_scope_of_expertise`, `decided_at`, `sources_consulted[]`, `confidence_qualifier` (`stated_certain` \| `stated_tentative` \| `not_stated`), `approval_kind` (always `human_scientific_approval` for scientific subjects; the only carrier of that value), `supersedes_decision_id` (revising one's own decision, or deciding an escalation item), `disputes_decision_id` (a disagreement with another person's applied decision: both records are kept and the subject becomes `unresolved`), `historical_list_exposure` (required when the subject is criterion-affecting; Section 8.6), `entry` (`interactive`; Section 2.4), `downstream_invalidation {stale_set[], rerun_set[], reuse_set[]}`, `journal_seq`. Expert-versus-expert disagreement retains both records and leaves the subject `unresolved`.

### 12.3 Queue item

`item_id`, `priority`, `created_at`, `age`, `subject`, `why_expert_required` (trigger-table row), `blocking: bool`, `requested_by`, `inspection_bundle {proposal_ref, critique_ref, evidence_refs[], precomputed_consequences: stale/rerun/reuse counts}`, `state` (`open` \| `in_review` \| `decided` \| `deferred` \| `expired` \| `withdrawn`), `assigned_to?`. **Claims.** A claim writes `human.review_claimed {person_id, lease_until}` and moves the item to `in_review`; release, reassignment, and lease expiry write `human.review_claim_released {reason: released | reassigned | lease_expired | withdrawn}`, the expiry written by the `scheduler` actor, also when it is detected after a host gap. A live claim reserves the item: a decision by anyone else is `rejected_not_permitted_in_state`. The lease is `const_review_claim_lease`. Withdrawal and expiry of an item are journaled as `human.review_withdrawn {reason, replaced_by_item?}` and `human.review_expired`.

### 12.4 Submission intake (text, local path, upload)

`submission_id`, `submitted_by`, `submitted_at`, `intake_mode` (`pasted_text` \| `host_path`, a path inside a registered intake directory on the service host, Section 14.1 \| `browser_upload` \| `terminal_stdin`), `path_as_given`, `path_platform`, `original_filename`, `content_hash` (raw bytes), `text_hash` (text files only; Section 14.2), `stored_uri`, `parser_used`, `parser_version`, `asserted_subject {candidate, criterion, target}`, `identity_resolution_status`, `claimed_value_kind`, `provenance {performed_by, performed_at, laboratory, protocol_ref, instrument_or_model, data_version_or_batch, prior_publication}`, `experimental_context {assay, system, species, n, replicates, controls, concentration_or_dose_range, incubation, temperature, matrix, readout, normalization, statistics}`, `values[]` with mandatory units, `direction` (`effect_observed` \| `no_effect_observed` \| `below_limit_of_detection` \| `assay_failed` \| `inconclusive`), detection limits. Lifecycle: `received → parsed | parse_failed (retained, needs_confirmation) → identity_resolved → review_pending → accepted_as_evidence | accepted_with_reservations | rejected | withdrawn`. No evidence level is assigned on write; admission requires an `hd_` by a reviewer other than the submitter; acceptance marks affected assessments stale and schedules reassessment; earlier snapshots are never rewritten. Negative results are first-class and visible in conflict sets.

---

## 13. Evaluation and strategy improvement (C19, C20)

### 13.1 Two kinds of improvement, two registries

| Dimension | Within-run rule refinement | Across-run strategy improvement |
|---|---|---|
| Object changed | attributes, rules, assessments, snapshots (C10–C12) | role prompts, delegation policy, retrieval rules, review checklists, tool selection, failure handling (C20) |
| Authority to confirm | human scientific approval (`hd_`) | measured improvement under a manifest plus an `ops_` decision by a named operator |
| Evidence standard | source-linked evidence per criterion; conflicts retained | matched-budget comparison on held-out material across more than one case |
| Legitimate claim | "the rules were revised under review" | "this policy performs better on this material at this budget" |
| Never licenses | any statement about agent capability | any statement about biological effectiveness |

The registries are structurally distinct: a criterion change record cannot carry a strategy change and a strategy version cannot alter the admission predicate (its hash must be unchanged for promotion).

### 13.2 Evaluation Protocol Manifest (`proto_`, hashed, registered before any arm runs)

`protocol_id`, `registered_at/by`, `task_set_id` with frozen `task_context_id`s, `evidence_snapshot_id` and hash, `source_access_cutoff`, `tool_manifest[] {tool_id, contract_version, endpoint_class, determinism}` identical across compared arms, `tool_outage_policy` (`abort_arm` \| `record_unresolved` \| `retry_bounded`), `memory_mode` per arm (`cold` \| `frozen` \| `warm`; policy comparisons use cold or frozen), `evaluator_id`, `evaluator_kind` (`human_expert` \| `rule_based` \| `llm_judge`; an LLM judge is inadmissible for primary domain metrics and admissible only for mechanically checkable process metrics with a cross-family judge), `evaluator_blinding`, `evaluator_instructions_hash`, `evaluator_epoch` (frozen for the comparison), `hidden_evaluator_function_refs[]` (never readable by evolved agents), `metrics` (primary and guards), `budget_caps` per arm, `seeds`, `n_repeats` (≥ 3 as a floor; promotion uses lower confidence bounds from pilot variance), `analysis_plan`, `stopping_rule_for_the_evaluation`, `pool_assignment` (development \| validation \| final), `claim_scope_template`. A run without a `protocol_id` is exploratory and structurally unusable as evidence.

### 13.3 Policy arms

| Arm | Definition | Role |
|---|---|---|
| P0 single-pass | one screening round; proposal + critique with external referent + one revision per subject | baseline; its realized cost defines the matched cap |
| P0-noreview | P0 without the critique step | ablation of the review exchange |
| P1 fixed-round (R) | exactly R scheduled rounds; R registered | reference configuration |
| P2 adaptive | continuation only on C8 triggers with stopping criteria | the candidate policy |
| P2-cap | P2 hard-capped at P0's realized median budget | adaptivity at equal spend |
| P0+ retrieval-rich / P0+ sample-rich | P0 given P2's realized budget in one pass (wider retrieval; or best-of-N proposals with an independent, cross-family or deterministic selector) | same spend without extra rounds |

P2 is an improvement only if it beats P0 and both P0+ variants and P2-cap does not fall below P0. Results are reported as probability of improvement with confidence intervals across repeats, never as a single difference; the cost of deciding whether to continue is counted.

### 13.4 Round Progress Record

`round_id`, `parent_round_id`, `trigger_claimed`, `progress_kind` (`new_admissible_evidence` \| `resolved_conflict` \| `filled_consequential_gap` \| `corrected_decision` \| `registered_negative_result`), `evidence_delta_ids[]`, `conflict_ids_resolved[]`, `gap_ids_filled[]`, `decision_changes[]`, `verdict` (`progress` \| `non_progress` \| `unresolved`). Non-progress: rephrased rationale, higher self-reported confidence, more citations for an already-supported claim, longer reasoning, agreement between agent roles. Two consecutive `non_progress` verdicts stop P2 independent of budget.

### 13.5 Metrics and reporting

Process-level (bounded scenarios S1–S14 in `evaluation_plan.md`): decomposition quality, delegation appropriateness, tool-contract correctness, evidence traceability, contradiction and missing-data handling, memory isolation and reuse, stop/resume fidelity, human-edit propagation, useful strategy updates, cost. Domain-level, reported separately and only with expert review or labels: precision among admitted, evidence correctness, independent support, unsupported-claim rate (guard), incorrect-exclusion rate (guard), coverage (mandatory beside precision), abstention by reason, calibration where a band exists, reproducibility across seeds, operating cost. Every report carries a `claim_scope {establishes[], does_not_establish[], label_dependency}` block emitted by C19, so passing process checks is never described as biological effectiveness.

### 13.6 Case Acceptance Register and preregistration

Two-stage preregistration as journal events with hashes, recorded by the evaluator in the task stream for a named task and run; a prespecified run waits in `waiting_human` on a blocking preregistration item until each stage is recorded. This is the one list of their contents, and other documents cite it. **Stage 1** (before derivation): rule semantics (`rule_kind`, `predicate_form`, the permitted `cutoff_basis` set, the on-state policies, `applies_to_result_kind`); hard-exclusion semantics; the ordering method; evidence-tier requirements; the evidence cutoff and the snapshot rule (the `evs_` id itself is registered at stage 2, once retrieval has frozen it); the candidate universe id; the tool manifest; the derivation configuration; the strategy version `strat@v`, which carries the consolidation rule; the hash of the registered constants, the coverage floor included; the sweep ordering policy and randomization seed; the threshold for "most" of the historical criteria and which similar matches count; and an optional `budget_extension_rule` (the most budget a continuation may add after `budget_exhausted` and still count as prespecified; Section 6.8). **Stage 2** (on expert approval, before any candidate assessment): `rules@v` with its `evidence_admission_predicate_hash`, the `evs_` id, and the concrete sweep order over the rule ids. Every run and configuration in the register carries an acceptance label, `prespecified` or `exploratory`; `outcome_informed_exploratory` is a derivation configuration of criterion versions, not this label. The register names the decisive criteria to be reported and the recording rules for every outcome; it does not pre-write an expected state for the reference candidate. Sensitivity ranges with justification and sources are registered before evaluation; configurations chosen after seeing outcomes are labelled `exploratory` everywhere they appear. The outcome recording rule: observed state; the criteria that failed or were `unknown`; cause (absent evidence, tool gap, excluding criterion); never adjust the baseline to fix it. An `outcome_dependence_report` (leave-one-out over hard rules: how many would change the reference candidate's verdict if removed, without tuning) accompanies every snapshot of the primary case.

### 13.7 Promotion conjunction and pools

Promotion of a strategy version requires all of: positive delta on registered primary metrics against the fixed baseline, on held-out tasks spanning more than the current case, at matched budget, with the lower confidence bound over `n` repeats exceeding the incumbent by more than the declared noise leeway; `evidence_admission_predicate_hash` identical to the baseline's; no guard metric degraded beyond registered tolerance (guards are gates, never weighted terms); reference-outcome selection frequency excluded from promotion metrics and reported only descriptively; `proxy_vs_held_out_gap` reported; a replay/retention view on earlier cases outside the `final` pool; the rule-reversal test passed where applicable; an `ops_` record by a named operator. Pools: `development` (free use, re-sampling allowed), `validation` (fixed; candidate selection; registered maximum looks per lineage), `final` (sealed; opened at most once per lineage; the opening recorded; a second look invalidates that lineage's claim). The promotion selector and policy are declared in the Run Binding (`promotion_policy_version`) and sit outside any evolvable surface. Rollback and expiry are journal events; the parent stays executable.

### 13.8 What v1 does and does not claim

v1 is evaluated strategy revision with held-out checks and human promotion, limited to prompt, playbook, and procedure-memory revision (offline, GEPA/ACE-style under the gate above). Not in v1: self-modifying agent code, automatic topology or workflow-graph search, co-evolving evaluators, fully automatic skill evolution without curation, and model-weight training. Three properties are explicitly "not claimed": sustained acceleration across recursive rounds under independent evaluation, meta-improvement of the mechanism that selects what to improve, and persistent gains on genuinely novel tasks. Any future claim to one of them is tied to a predefined measurement in C19.

---

## 14. Persistence model

| Store | Content | Write discipline | Reads |
|---|---|---|---|
| Journal (per stream: run, task, group, case, evaluation) | events (Section 4.1) | append-only, durable per event, store-assigned `seq`; a correction is a new event | replay by `seq`; projections are pure folds; compaction writes projection snapshots with `snapshot_seq` |
| Artifact store | envelopes (Section 4.3), content-addressed | write-once by content hash; `supersedes` links; never mutated | by id; by kind and task |
| Claim Ledger | sources, claims, locations, independence groups, visibility manifests, search coverage | append-only; `admission_state` changes are new rows ordered by `(journal_seq, updated_at)` | by claim, source, attribute, candidate |
| Criterion Registry | attribute and rule versions, change records, confirmed rule sets | append-only versions; `confirmed` only with `hd_` refs | by version; diff between versions is a projection over change records |
| Assessment Ledger | assessments, reasons, roll-ups | append-only; staleness is a marker, never a deletion | by candidate, criterion, rules@v, snapshot |
| Leaderboard snapshots | immutable snapshots with change records | write-once per snapshot | by task; by snapshot id; longitudinal by task |
| Memory store | items and operations | operations only (`add`, `retire`, `supersede`, `retag`) | by scope and recall policy |
| Review queue and decisions | items, `hd_` records | items transition; decisions are immutable | by state, subject, actor |
| Evaluation store | manifests, evaluation runs, strategy versions, `ops_` decisions | registered before use; hashed | by protocol, version, lineage |
| Submission store | uploaded or pasted inputs | write-once by content hash | by submission id |
| Trace store | raw model I/O | write-once; `visibility: expert \| auditor`; access journaled | by `trace_blob` link only |
| Operator log (per store root) | sessions, role grants, command records (`cmd_`), rejected commands, exports, service start and stop records | append-only; a `cmd_` record is durable before its acknowledgement | by session, person, time, `command_id` |
| Access log | `evaluator_only.read` events in case streams, one per read of the historical-criteria intake or an artifact derived from it | append-only, as part of the journal | by person and subject; consumed by the exposure rule of Section 8.6 |
| Cache | tool responses | each entry carries `retrieved_at` and a staleness policy | by cache key; a cached answer is a claim about a past release |

Retention: completion events, artifacts, ledgers, snapshots, decisions, and evaluation records are retained indefinitely; heartbeats roll in a bounded window; caches expire by policy. All stores are local-first (single-node file or embedded-database class); no store depends on a specific model provider. Every record carries `vocabulary_version`, `journal_seq`, and the Run Binding reference needed to reproduce it.

### 14.1 Service host and deployment profiles

The core runs inside one **service host** process on a Linux or a Windows machine. One service host owns one store root. The root must be on a local disk that is not synchronized elsewhere: a root inside a cloud-synchronized folder or on a network file system would carry evaluator-only content off the machine and would let a second host elsewhere bypass the lock, so the host refuses to start there (`store_root_unsupported`). Detection covers known synchronization folders and network file systems and is backed by the operator's declaration at setup, which is recorded; it is not proof. The host holds an operating-system lock on the root, which the operating system releases when the process ends, so a crash never leaves a stale lock; a second host on the same root refuses to start (`store_locked`). No surface or tool opens store files directly.

| Profile | Service host runs on | Surfaces | Network exposure |
|---|---|---|---|
| L | Linux | terminal client on the same host; optionally the browser workbench in Chrome on the same host | loopback only |
| W | Windows, started by the person from a launcher | Chrome on the same machine at the loopback address | loopback only |
| X | Linux (for example a remote compute node) | terminal on the host; Chrome on a Windows machine through an SSH local port forward, bound to the Windows machine's loopback, to the host's loopback port | loopback only on both ends; the forward is the person's own SSH session |

Rules for every profile:

- **Loopback only.** The service host listens on the loopback interface only. Listening on other interfaces, and serving several people over a network, is out of scope for v1 (Section 18, U-15). On a Linux machine shared by several accounts every local account can reach the loopback port, so the session token, not the port, is the access boundary.
- **Local request checks.** Any web page open in the same browser can address a loopback port. On every request, including the handshake of the event stream, the host therefore accepts only a Host header and an origin of `127.0.0.1`, `[::1]`, or `localhost` with the host's port or a registered forwarded port, and refuses `Origin: null`; there is no cross-origin access. Every command, including every logged read, carries the session token in a request header; the browser's session cookie is `HttpOnly` and `SameSite=Strict` and is never sufficient alone.
- **Session start.** `session open --browser`, run in the host's operating-system account, prints a single-use, short-lived address that Chrome exchanges for a session; on profile W the launcher does the same and opens Chrome. The operator can issue such an address for another person, who then opens a session under their own person id. Because the address is single-use and expires, a copy left in browser history or visible in a process list cannot be reused. The terminal client authenticates with a token file readable only by the host's operating-system account.
- **Same-account processes.** Any process running under the host's operating-system account can read that account's files, including the token file. Tool subprocesses are started without the token in their environment, which reduces but does not remove this exposure; it is the boundary of a single-account local deployment.
- **Self-contained workbench.** The workbench's pages and assets are served by the host; only tools and model providers need internet access.
- **Evaluator-only store.** Evaluator-only content (the historical-criteria intake and every artifact derived from it) is encrypted at rest under a key the evaluator supplies for each scan, comparison, or panel read and the host does not keep. File access without the key is not a read; a read with the key happens only through a confirmed command (Section 2.4) and writes an `evaluator_only.read` event (Section 8.6). Without this protection everyone who can read the store's files under the host's account would have to be treated as `exposed`, which on profile W would leave the `independent` recovery view empty; acceptance-bearing runs therefore require it.
- **Host intake directories.** A submission by path (`intake_mode: host_path`) is resolved with links and junctions followed and accepted only inside directories the operator registered for intake. A path inside the store root or the token location, a network path, or a device path is `rejected_invalid`.
- **File-system interference.** On Windows, antivirus and indexing services can hold a newly written file open. A sharing violation is retried up to `const_store_write_retry_limit` times and is then a C1 write failure (Section 15).
- **Stop, sleep, and crash.** An abrupt stop of the current attempt is either a stop of the host (window closed, log-off, crash) or a suspend, detected when the wall clock moves ahead of a suspend-excluding monotonic clock by more than `const_host_suspend_threshold`. In both cases the controller finalizes the attempt (`finalized_by: controller`), closes unanswered tool calls with synthetic `unknown_outcome` results, and starts a new attempt from the last checkpoint. The new attempt restores the execution state recorded at the checkpoint and in the journal: a `paused` run stays `paused`, a `waiting_human` step keeps waiting until an `hd_` arrives (Section 6.1), and only steps that were `running`, `retrying`, or `waiting_tool` are re-queued. The attempt record carries `host_gap {kind: stop | suspend, last_heartbeat_at, detected_at}`. The gap is charged to no budget. The operator log records `service.stopping` on an orderly stop and `service.started {prior_stop: orderly | abrupt}` on every start.

### 14.2 Portable records

A journal, store, or checkpoint written on one platform must replay to the same projections on the other. This is a design requirement, checked by scenario S12 (`evaluation_plan.md` §2); it has not been tested.

- **Canonical bytes.** Every hashed record is serialized in one canonical form defined and versioned by C3: UTF-8 without a byte-order mark, Unicode NFC, LF line endings, fixed field order, fixed number formatting. Record hashes, `payload_hash`, C16 fingerprints, and `projection.hash` are computed on that form, never on platform-native text. Files people supply are different: they are stored and hashed on their raw bytes (`content_hash`) so that evidence is never altered, and a text file also gets a `text_hash` over its canonical text (UTF-8, NFC, LF), used only to detect duplicates.
- **Paths and file names.** Stored paths are relative to the store root with `/` separators. File names inside stores are content hashes or a lowercase hash of an identifier, never an identifier or a name a person supplied, so case-sensitive identifiers, characters Windows rejects, reserved device names, and path-length limits cannot collide with them. A path a person types is kept verbatim as `path_as_given` with `path_platform`. On profile X a path on the person's Windows machine is not readable by the Linux host, so the browser offers upload instead (Section 12.4).
- **Time.** Timestamps are UTC. Durations come from a suspend-excluding monotonic clock and are never computed across a host gap from wall-clock differences.
- **Tools per platform.** Every tool contract declares `supported_platforms[]` with a `platform_support_basis`, an `execution_location`, and whether its output is `platform_independent_output` (Section 7.1). A tool that cannot run on the host fails the prerequisite probe and yields `not_attempted` with `absence_reason: requires_other_environment`; the affected cells are `unknown_missing`, never `fail`. Every tool result records `executed_on {platform, execution_location}`, which enters the C16 fingerprint unless the tool declares `platform_independent_output` (a remote web service can; a locally installed numerical tool cannot until checked), so by default a result computed on one platform is never reused as valid on the other.
- **Comparison and continuation across platforms.** The resolved tool manifest is part of the Run Binding, so runs on different platforms are comparable only when their manifests match, which C19 already requires across compared arms. A store root moved to the other platform can be reopened read-only anywhere. Resuming a run on the new host re-resolves the tool manifest and is refused on any mismatch; the work then goes on in a run continuation (Section 6.8).
- **What is not portable.** Language-model outputs are not reproducible on either platform. Portability is claimed for replaying a recorded journal, which recomputes projections from recorded values and never re-executes tools, and for deterministic records (rule evaluation over a fixed claim set, fingerprints, projections).

### 14.3 Credentials, backups, and model versions

- **Credentials.** Keys for model providers and data sources live in the host account's operating-system credential store. They never enter the journal, traces, exports, agent context, provenance blocks, the operator log, or line-delimited output; the Tool Broker and model adapters receive them at dispatch, and trace capture redacts any that appear in model input or output. Rotating a key changes no record. A missing key fails the dispatch pre-check (`not_attempted`, `absence_reason: not_configured`); a rejected key is `failed` with error class `auth_rejected` (Section 7.3).
- **Backups.** The store root is local and not synchronized (Section 14.1), so a backup is the only copy elsewhere. Scheduled snapshots of the whole store root are encrypted and kept off the host; the append-only journals and content-addressed stores make them incremental. Before the primary case runs, a restore drill replays a restored journal to the same `projection.hash`. The evaluator's key is not in the backup; it has a recorded escrow arrangement, because losing it makes the recovery comparison impossible.
- **Exact model versions.** The Run Binding records `role_bindings[] {role, adapter_id, provider_family, model_id, model_version, decoding_parameters}`, so the independence marker, cost, and reproducibility refer to an exact model. A run whose bound model a provider has retired cannot be resumed; the work continues in a run continuation that binds a new strategy version, labelled as such.

---

## 15. Failure handling matrix

| Component | Failure | Behaviour | Record | UI state |
|---|---|---|---|---|
| C1 | process crash mid-attempt | controller closes the attempt (`finalized_by: controller`); synthetic `unknown_outcome` tool results; new attempt replays from checkpoint `seq` | `attempt.finalized`, `checkpoint.written` | run `retrying`, then the execution state recorded at the checkpoint (`paused` and `waiting_human` kept; Section 14.1); reuse manifest shown |
| C2/C3 | value outside registered vocabulary | write rejected | `step.failed {vocabulary_violation}` | step `failed` with reason |
| C4 | blocking unknown unanswered | run waits; advisory unknowns never block | `human.review_requested` | `waiting_human` with the missing decision named |
| C5 | step owner fails | `on_failure` policy (retry \| escalate_human \| mark_unresolved \| skip_with_reason) | `step.*` | per policy |
| C6 | budget exhausted | LoopOutcome `budget_exhausted`; state `unresolved`; never acceptance | `round.closed {termination_reason}` | budget meter full; `unresolved` with open questions listed |
| C7 | critique without external referent | labelled `restatement`; no exchange consumed | `exchange.critiqued {restatement: true}` | shown as restatement |
| C7 | persistent disagreement | deterministic adjudication, then escalation, then queue; `unresolved` is legitimate | `exchange.adjudicated`, `human.review_requested` | `adjudicating` → `waiting_human` |
| C8 | no admissible trigger | round closes with `no_actionable_step` | `round.closed` | `completed` or `unresolved` with reason |
| C9 | fetch failure | source `access_state: fetch_failed`; shortfall reported | search coverage record | evidence inspector shows the gap |
| C9 | full text unavailable | `reading_depth ≤ title_abstract`; dependent assessment carries `limitation_kind` | claim record | limitation badge |
| C10 | invariant violation | typed critique; bounded repair; then `unresolved` | `criterion.change_recorded {arbitration_outcome: unresolved}` | rule history shows the failed proposal |
| C11 | tool failure for one candidate | cell `unknown_missing` with error ref; run continues | `tool.errored`, `candidate.assessed` | candidate detail shows unknown with cause |
| C12 | `recommended` without required `hd_` | published as `provisional {awaiting_human_review}` | snapshot | "no human review yet" |
| C13 | provider pre-check fails | `not_attempted` with absence reason and manifest; fall through to next provider | `tool.returned {outcome: not_attempted}` | tool coverage block |
| C13 | repeated runtime failures | circuit breaker `degraded`; `run_degradation[]` | `tool.degraded` | problems list; coverage reduced |
| C13 | adapter cannot return tool results | feedback-dependent protocol refused or policy-approved single-shot with `unresolved` steps | capability record, `run_degradation[]` | degradation shown |
| C14 | content-policy violation | item rejected to review queue with codes | memory operation refused | queue item |
| C15 | stale checkpoint | steps restored `queued` unless an evaluated artifact exists | reuse manifest | reused vs re-evaluated labels |
| C16 | human edit | transitive stale marks; Rerun Plan; auto-approve only when all items required and within budget | `staleness.marked`, `rerun.scheduled` | stale badges; rerun counts |
| C17 | disconnected client | `view_stale`; motion frozen; last `seq` and age shown | none (client-side) | stale banner |
| C18 | expert disagreement | both records retained; subject `unresolved` | two `hd_` records | disputed badge |
| C19 | run without manifest | treated as exploratory; inadmissible as evidence | evaluation record absent | labelled exploratory |
| C19 | guard metric breached after promotion | rollback event to `rollback_target` | `ops_` decision | strategy version `rolled_back` |
| Host infrastructure | host stopped (window closed, log-off, crash) or suspended (sleep) | attempt recovery of Section 14.1: a new attempt from the checkpoint with the recorded execution state restored (`paused` and `waiting_human` kept); the gap is charged to no budget | `attempt.finalized {finalized_by: controller}` with `host_gap {kind}`; operator log `service.started {prior_stop}` | both surfaces `view_stale`; then "host stopped" or "host was asleep" for the gap, with the resumed checkpoint |
| Host infrastructure | second host started on the same store root | refuses to start (`store_locked`) | operator log | surfaces stay attached to the running host |
| Host infrastructure | store root on a synchronized folder or a network file system | refuses to start (`store_root_unsupported`) | operator log | the launcher or terminal names the reason |
| Host infrastructure | command based on a stale view | `rejected_stale_basis` with the current state; nothing applied | `cmd_` record; operator log | "changed since you looked", with the newer state |
| Host infrastructure | command whose precondition fails, including a decision on an item someone else has claimed | `rejected_not_permitted_in_state` | `cmd_` record; operator log | the reason and the current state |
| Host infrastructure | command resent after a dropped connection | `duplicate`; original result returned from the `cmd_` record | none new | the original outcome |
| Host infrastructure | scripted command that would write an `hd_`, or a command without the required role | `rejected_unauthorized` | `cmd_` record; operator log | "needs interactive confirmation" or "not permitted for your role" |
| Host infrastructure | submission path outside the registered intake directories, inside the store root or token location, or a network or device path | `rejected_invalid`; nothing read | operator log | "path not allowed for intake" |
| Host infrastructure | request with a foreign Host header, a foreign origin, `Origin: null`, or no session token | refused before any component sees it | operator log | none |
| C1 | file held open by another process on Windows (sharing violation) | bounded retry (`const_store_write_retry_limit`), then handled as a C1 write failure | step or command failure record | problems list |
| C13 | tool cannot run on this host platform | prerequisite probe fails; `not_attempted` with `requires_other_environment`; fall through to another provider | `tool.returned {outcome: not_attempted}`; tool manifest on the Run Binding | tool coverage block names the platform |
| C15 | resume on another platform with a different resolved tool manifest | resume refused; the work goes on in a run continuation | operator log | "tool manifest differs; continue in the chain" |
| C15 | continuation requested for a parent another person has just continued | `rejected_stale_basis`, unless confirmed as a branch | `cmd_` record | the other continuation, with a branch option |
| C15 | task or run requested in an archived group, or a move of a task that has runs | `rejected_not_permitted_in_state` | `cmd_` record | "group archived" or "task has runs: continue or copy into the group" |
| C14 | skill or lesson draft violates the content policy | rejected to the review queue with codes; nothing stored as provisional | memory operation refused | queue item |
| Host infrastructure | credential missing or rejected | `not_attempted` (`not_configured`) at pre-check, or `failed` (`auth_rejected`); no key is taken from anywhere else | tool result | tool coverage block |
| C15 | resume of a run whose bound model was retired | resume refused; the work continues in a run continuation with a new strategy version | operator log | "model retired; continue in the chain" |

---

## 16. Operation without CDES, and the optional CDES adapter

**No-CDES route (default).** Target-coverage evidence comes from curated bioactivity records and expert-curated interaction tables (interface-level sources in `tools.md`); property dimensions come from computed descriptors, published measurements retrieved through literature tools, and pinned-version property predictors whose outputs are `model_prediction` with `claim_strength_ceiling: predicted`. Coverage is the limit, not quality: retrieval yields values for well-studied pairs and nothing for most of a large library, so `unknown_missing` will be the most common verdict for many candidates and must stay a first-class, non-penalising state. Every snapshot carries a per-dimension `tool_coverage` block and `interaction_estimate_provider: none`, so no later narrative can imply a model ran. An empty or small recommended set with a large provisional tier is a correct outcome and a finding.

**CDES as an optional adapter.** Capability `interaction_estimate`; inputs: resolved compound identity (structure key plus canonical structure string) and resolved target identity (protein accession, sequence version, isoform); outputs: one interaction probability per compound–target pair with `model_version`, `checkpoint_id`, `training_data_version`, `calibration_metadata`, and an `applicability` flag; evidence kind `model_prediction`; `uncertainty_model: class_probability`; `determinism: seeded_stochastic`; `cost_latency_class: batch`; prerequisites: code, checkpoint, GPU environment. What it adds: uniform coverage of the whole candidate universe, which no retrieval route can replace. What it requires before any criterion may depend on it: the training set with provenance and license, the train/test split, an overlap check against the reference candidate and the five targets (the case outcome is disclosed, so leakage is a live risk), calibration data giving the decision threshold a meaning, and a stated threshold rationale. Absence or failure: the provider is not registered, and calls resolve to `not_attempted` with `absence_reason: not_configured`; capability resolution falls through; affected cells `unknown_missing` with absence reason and manifest; candidates `provisional` or `unassessed`, never `rejected` for want of a prediction; the run reaches `completed` with the coverage summary. If CDES arrives later it enters as an evidence-refresh run against preserved snapshots, with an agreement check against curated measurements recorded before any criterion depends on it alone. An optional structure-based affinity predictor may occupy the same capability slot; the case configuration records that the manuscript cites it as CDES's comparator and prohibits any inference about CDES's relative merit from its use.

---

## 17. End-to-end path for the primary case

This instantiates Section 3 for the manuscript case and names the records the rebuttal needs. It specifies; it does not report results. The full protocol, inputs, and recording rules are in `case_study_protocol.md`; the claim-by-claim mapping is in `rebuttal_alignment.md`.

**Inputs the package does not contain (dependencies on the authors).** The identity list of the 3,171-compound library (or its access path); the authors' list of the eleven historical CQAs with definitions, thresholds, units, directions, and a completeness attestation; assay-endpoint and unit conventions for the five targets; the historical 140-binder stage as a comparison artifact. The list of case-source documents; exposure declarations from confirming experts and template authors; optionally, expert-curated external calibration cases.

**Case configuration (abbreviated).** Mode conditional; objective text verbatim from the manuscript context; scope entities CSF1R, VEGFR1, VEGFR2, VEGFR3, FGFR1 (`role: required`, `questioned: allowed`); candidate universe the 3,171-compound library; seed surufatinib with `is_reference_outcome: true`; constraints oral administration and an evidence cutoff; historical-criteria intake with `visibility: evaluator_only`; registered constants including the coverage floor (value an expert dependency); comparison basis `both` with all-pass primary; `derivation_configuration: reference_disclosed`; human-review requirements: every hard exclusion and every `recommended` publication.

**Route to the two targets.** Criterion recovery rests on recall-first enumeration per dimension with saturation stopping, a registered consolidation rule, matching that credits similar items (different cutoff, narrower applicability, merge, split) separately from exact ones, and, when calibration cases exist, a derivation strategy frozen after calibration on other published cases (Section 8.3). The eleven, the manuscript, and its supplement stay outside derivation, and exposure declarations decide whether a recovered item counts in the `independent` or `assisted` view (Section 8.6). Admission rests on three conditions the design controls without steering the outcome: identity resolution of the reference candidate through authority crosswalks; no hard exclusion confirmed on weak evidence (weak-exclusion invariant and expert confirmation); and missing values capping a candidate at `provisional` rather than rejecting it. What the design cannot control is a confirmed hard rule that the candidate fails on admitted evidence; that outcome is recorded under `case_study_protocol.md` §6.2, and the protocol's §5.4 and §6.5 give the full route.

**Where it runs.** The case may be run on any deployment profile of Section 14.1 and operated from either surface; the route and the records do not depend on the surface. The Run Binding names the host platform and the resolved tool manifest; a tool that cannot run on the chosen host is recorded as absent, lowers coverage, and is reported in R6.

**Edits and continuations.** The prespecified baseline run is the root of its chain. A continuation created after any snapshot or recovery comparison of the chain was published is outcome-informed and `exploratory`, unless it matches a stage-1 rule: a registered sensitivity configuration, or the registered budget-extension rule for a baseline that ended `budget_exhausted` (U-13). Exploratory continuations are reported beside the baseline, never in its place (Section 6.8).

**Stages and records.**

| Stage | What happens | Records produced for the rebuttal |
|---|---|---|
| Bind and preregister policy | Run Binding; stage-1 preregistration recorded by the evaluator (contents: Section 13.6) | R5 preregistration events (policy) |
| Normalize and plan | task context with unknowns (endpoint definitions, unit conventions, universe access); plan with per-dimension retrieval steps | R9 journal |
| Retrieve | sources and claims for target coverage, oral bioavailability, metabolic stability, toxicological safety; reference-blind evidence slice; search coverage records | R1 evidence basis |
| Derive and critique | attributes and rules with change records; considered-and-rejected list; typed critique checks incl. candidate-symmetric scrutiny; deterministic adjudication; invariants incl. reference-candidate scan | R1 rule-evolution history |
| Confirm | expert decisions on every hard exclusion and expert-set cutoff; `rules@v1` confirmed; stage-2 preregistration of the criterion version | R7 expert decisions; R5 preregistration (criteria) |
| Assess | identity resolution; one assessment and reason record per candidate × criterion; coverage expected low without CDES; roll-ups | R2 per-candidate per-criterion records |
| Snapshot | `lb_<task>_1` with result kind, reporting tuple, tool coverage, independence summary, `interaction_estimate_provider: none` | R3 leaderboard snapshot |
| Compare and accept | recovery comparison against the eleven (nine mapping kinds, expert-judged equivalences); Case Acceptance Register check; outcome dependence report | R4 recovery summary; R5 acceptance records |
| Sensitivity (registered before evaluation) | justified alternative configurations and threshold ranges run on the same snapshot; all configurations retained with equal prominence; outcome-informed ones labelled exploratory | R5 sensitivity results |
| Close and continue | open questions registered (conflicts, consequential missing measurements, questionable exclusions, targeted computations such as an optional affinity predictor for consequential gaps); P0 stops here by default | R9 termination reasons |
| Edits and refresh | expert edits create new versions with stale marks and rerun plans; new evidence triggers refresh runs and new snapshots with explained changes | R3 longitudinal snapshots; R7 |

**Records index.** R1 confirmed rule-set versions with source-linked change history and critiques; R2 per-candidate per-criterion assessment and reason records for every candidate reached; R3 leaderboard snapshots with result kind, reporting tuple, and change records; R4 recovery-comparison summary against the historical eleven with expert reason-quality ratings; R5 preregistration events, Case Acceptance Register, and sensitivity results for all configurations with prespecified versus exploratory labels; R6 tool and adapter records, including the absence record for CDES; R7 expert decision records; R8 evaluation protocol manifest and `claim_scope` blocks; R9 journal exports for every round and analysis step.

**Honest outcome statements (templates, to be filled only by a run).** "Under the prespecified baseline `rules@vN` and evidence snapshot `evs_K`, surufatinib was [recommended | provisional | unassessed | rejected]; decisive criteria: …; criteria with unknown verdicts: … (cause: …)." "Of the N historical CQAs (completeness attested: …), k were recovered with evidence-linked rationale (of which j at a different cutoff), m merged, s split, r removed for lack of support (searches: …), a newly added; expert reason-quality ratings: …." "No interaction-prediction backend ran; target-coverage verdicts rest on curated measurements covering X of Y candidate–target pairs." "The result kind is [unique all-pass under hard rules | top-ranked under the registered ordering method]." If the reference candidate is not admitted under the prespecified baseline, the rebuttal cannot claim that the framework recovered the original prioritization; it reports the derived criteria, the specific failures or missing measurements, and the evidence that would resolve them.

---

## 18. Out of scope for v1 and extension points

Out of scope: de novo molecule generation; virtual-cell or perturbation modelling as a required step; target discovery from scratch (the system may question supplied targets and route doubts to experts); self-modifying agent code, topology search, co-evolving evaluators, and weight training; any universal cross-objective ranking; a second domain adapter; listening on interfaces other than loopback and serving several people over a network from one service host; a Linux terminal operating a Windows host (Section 14.1, U-15). Extension points: a terminal client on Windows using the same Operator API; additional adapters implementing the Section 2.1 ports; additional `interaction_estimate` or `property_estimate` providers through the capability registry; additional policy arms and evaluators through the Protocol Manifest; perturbation or cell-state tools as optional `dataset_context_lookup` providers whose outputs are `computational_simulation` evidence with their own applicability conditions.
