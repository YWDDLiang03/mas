# UI/UX Specification: Browser Workbench and Terminal Client

Design artifact only, 12 October 2026. Non-executable wireframes and component/state descriptions for the local browser workbench (used in Chrome) and the terminal client; both are clients of one Operator API (`optimized_design.md` §2.4), and Section 15 defines how they stay equivalent. Nothing here is implemented; no event transport, component library, or visual design is chosen. All component ids (C1–C20), record names, identifier prefixes, states, and event kinds are those of `optimized_design.md` Section 0; every label shown to a user comes from the State Registry (C2) `ui_label` mapping for its `label_domain`. The reference application's progress and iteration views (Agentic Doping snapshot `0007ad10`) were inspected from source by Workstreams 4 and 7 and are credited where an idea is reused; its defects (blended percentage with extrapolated ETA, heartbeat as progress, relabelled unresolved outcomes, raw model I/O as the live default, absent review queue) are the behaviours this design replaces.

**Placeholder values.** Every number, count, position, percentage, and identifier shown in the wireframes of this document is an illustrative placeholder chosen to show field shape; none is a measurement, a prediction, or a screening result, and no run was executed.

---

## 1. Principles that every screen obeys

1. **Concise decisions and sources by default.** A decision is shown as question, actor, outcome, one-sentence reasoning, linked claims with their status, and execution state. Raw model output never appears on a default surface; it lives behind a role-gated panel (`visibility: expert | auditor`) whose opening journals `trace.opened`.
2. **Nothing implies progress, validation, or approval that has not occurred.** Percentages render only for `denominator_kind: enumerated_fixed` inside one scope; budgets render in a separate meter labelled as budget; an approval chip renders only when backed by an `hd_` record id; otherwise the slot reads "no human review yet". Agent verdicts are labelled as such and never occupy the approval slot.
3. **Every label is registered.** Execution, exchange, candidate, result-kind, value-kind, verdict, review, change-kind, termination-reason, denominator-kind, and view-freshness labels come from C2 with `ui_label` and `ui_tone`; presentation code may not remap a state. `unresolved` renders as "unresolved" with the unmet question beside it.
4. **Every number has a denominator or none.** When a denominator is unknown, the indicator is indeterminate and shows state, current question, elapsed time, and last-activity age.
5. **Every change is linked.** A row that changed shows its `cause` (claim, tool result, change record, or human decision) or is marked `unexplained` as a defect.
6. **Freshness is visible.** The view carries one of `live`, `view_stale`, `activity_unknown` (client-derived, never persisted); in the latter two all motion stops and the last applied `seq` and its age are shown.

---

## 2. Screen map

```
Task list ─┬─ Task input (new / edit → new task_@v)
           ├─ Leaderboard (lb_<task>_<n>, filters, history of snapshots)
           │     └─ Candidate detail ─── Evidence inspector
           ├─ Run monitor (live) ─┬─ Round timeline ─── Version-difference view
           │                      └─ Human-review queue
           ├─ Rules & criteria (attr_@v, rule_@v, rules@v, change history) ─── Version-difference view
           ├─ Run chain (a run and its continuations: continue · edit · branch; Section 16.1)
           ├─ Skills & lessons (memory items of the active group; Section 16.3)
           └─ Evaluation (preregistration, protocol manifests, strategy versions)
Global: activity bar (compact: active run group ▾ · run state · freshness · open blocking reviews) on every screen (reference idea: always-visible activity bar, App.tsx 3111-3125); group switcher in Section 16.2
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

Every screen on this map, and every action on those screens, has a terminal command (Section 15.3).

---

## 3. Task-input screen

### 3.1 Wireframe

```
+-- new investigation ───────────────────────────────────────────────+
| objective*  [ verbatim objective text; never rewritten          ]   |
| mode        (o) conditional   ( ) exploratory                        |
|   conditional: you supply the candidate universe and ≥1 scope        |
|   entity or constraint. exploratory: the planner proposes scope and   |
|   criteria as agent_proposed; experts confirm before any hard rule.   |
| scope entities   [+ add]  CSF1R required · VEGFR1 required · …        |
|   role: required / optional / questioned   provenance: manuscript     |
| candidate universe  [named_library ▾] [access path…] size: 3,171     |
| seed candidates  [+ add]  surufatinib  is_reference_outcome ☑        |
| constraints      [+ add]  oral administration · hard                 |
| evidence cutoff  [YYYY-MM-DD]   tool availability [snapshot ▾]        |
| supplied evidence  [upload] [local path] [paste text]                 |
| comparison artifact (evaluator_only)  [historical_criteria_intake]    |
|   comparison fn; review queue (adjudication only); evaluator panel    |
| comparison basis  (o) both (all-pass primary)  ( ) all_pass_set       |
|                   ( ) ranked_under_score      abstention allowed ☑    |
+-- needs input before the task is meaningful (blocking) ──────────────+
| (!) candidate universe access path missing            [provide]       |
+-- advisory (does not block) ─────────────────────────────────────────+
| (i) endpoint definitions for 2 of 5 targets unstated   [define later] |
| (i) no interaction_estimate provider configured → predicted cells    |
|     will render as not_attempted                                      |
+-- budget (caps on work, not a completion target) ────────────────────+
| screening_rounds [1]  review_exchanges [1]  tool_calls [200]          |
| wall_clock [2h]  human_review_minutes [60]                            |
|            [save draft]  [plan only]  [start run]                     |
+----------------------------------------------------------------------+
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

### 3.2 Components and states

| Component | Record it edits | States |
|---|---|---|
| Objective field | `task_.objective_text` | empty, filled |
| Mode selector with inline explanation | `task_.mode` | conditional, exploratory |
| Scope-entity chips | `task_.scope_entities[]` (adapter-typed) | required, optional, questioned |
| Universe picker | `task_.candidate_universe` | enumerated_set, named_library, seeded_expansion, undetermined |
| Seed list with reference-outcome toggle | `task_.seed_candidates[]` | — |
| Constraint chips | `task_.constraints[]` | hard, soft, unclear |
| Evidence intake | `sub_` submissions → provisional claims | received, parsed, parse_failed |
| Comparison-artifact slot | case configuration `historical_criteria_intake` | absent, attached (visibility evaluator_only shown) |
| Blocking-gap panel | `task_.unknowns[] {blocking: true}` and `missing_info_requests[]` | start disabled while any blocking unknown is unanswered |
| Advisory panel | `task_.unknowns[] {blocking: false}` | never blocks |
| Budget block | `budget_envelope` | — |
| Actions | `plan.recorded`, `run.created` | draft, incomplete_blocking, incomplete_advisory, ready, planning, submitted |

Editing a saved task creates `task_@v<n+1>` with `supersedes` and triggers the staleness flow (Section 10) for any run bound to the earlier version.

---

## 4. Live run monitor

### 4.1 Wireframe

```
+-- run_R1 · RUNNING · ● live (2 s ago) ──────────────────────────────+
| task_T1@v1 · plan_R1@v2 (revised 1×) · rules@v1 · evs_T1_1 · P0     |
| OVERALL  stages 3 / 7 declared          [###----]  "plan revised 1×" |
| STAGE    assess: 118 / 2,980 enumerated_fixed  [#------]  4 %        |
| ROUND    round_R1_1 · steps 4 / 6 declared                           |
| BUDGET   rounds 1 of 1 · tool calls 87 / 200 · 41 m of 2 h           |
|          (budget consumed — not completeness)                         |
| ELAPSED  00:41:18 · last activity 2 s ago                            |
+-- now running ───────────────────────────────────────────────────────+
| actor         owns            question                      state     |
| assessor-3    cand_…          metabolic stability value?    running   |
| tool_chembl   inv_…           activity records for pair?    waiting_tool |
| critic-1      xchg_…_1        unit consistent with rule?    running   |
| expert E1     rule_R7@v1      approve unit correction?      waiting_human |
+-- waiting / problems ────────────────────────────────────────────────+
| retrying  tool_pubmed  attempt 2 / 3 (rate_limited) next in 18 s      |
| not_attempted  tool_gdsc_context  absence_reason identity_unresolved → |
|                cell recorded unknown_missing (not a failure)           |
| degraded  tool_gtopdb  circuit breaker open · run_degradation recorded |
|  [pause] [cancel] [timeline] [review queue (1 blocking)] [leaderboard]|
+----------------------------------------------------------------------+
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

### 4.2 Components and states

| Component | Source | States / rules |
|---|---|---|
| Header with freshness badge | run state from C1 projection; freshness client-derived | run: queued, running, waiting_tool, waiting_human, retrying, paused, failed, cancelled, completed, unresolved; freshness: live, view_stale, activity_unknown |
| Overall row | plan stages; `progress.estimate_revised` count | "k / n declared"; never a blended percentage; indeterminate when later stages are not enumerable |
| Stage row | `progress {scope, denominator_kind, completed, planned}` | percentage only for `enumerated_fixed`; `enumerated_growing` shows "completed c · planned ≥ p"; `unbounded_adaptive` and `unknown` show state and elapsed only |
| Round row | round steps | "steps k / n declared"; steps added mid-round re-render the denominator with a "revised" tag |
| Budget meter | `budget` from events | always labelled as budget; exhausting a budget other than screening rounds before the sweep is complete renders the run `unresolved` (`budget_exhausted`), never "done"; a used round budget after a complete sweep is `round_limit_reached`, and the run is `completed` |
| Elapsed and last-activity | heartbeat age | — |
| Now-running table | `agent.started`/`agent.heartbeat`, `tool.requested`, `step.waiting_human` | one row per active actor: actor, owned object, question, execution state |
| Waiting and problems | `tool.retry_scheduled`, `tool.returned {not_attempted}`, `tool.degraded`, `run_degradation[]` | retries nest under their call; absences state their reason and that the cell is `unknown_missing`, not failed |
| Controls | `run.paused`, `run.cancelled`, navigation | pause, stop, timeline, review queue (count of blocking items), leaderboard |

In `view_stale`, the header reads "view stale · last applied seq 1,204 · 3 m ago", bars freeze, and the now-running table greys. In `activity_unknown`, the header reads "no heartbeat for 7 m (threshold 5 m for full-text reading)". Reference ideas reused: always-visible activity bar plus detailed monitor (App.tsx 3111-3125, 3524-3546); replaced: `elapsed × (100 − pct) / pct` ETA over changing denominators.

---

## 5. Round timeline

### 5.1 Wireframe

```
+-- timeline · task_T1 · run_R1 ───────────────────────────────────────+
| show ☑ rounds ☑ steps ☐ retries ☑ human edits ☑ refresh runs         |
|      ☑ report revisions ☐ heartbeats ☐ exchanges                     |
| seq   when      kind                   actor        outcome    links   |
|   1   10:02:11  run.created            controller   running    bind_R1 |
|   8   10:04:50  round.opened R1_1      controller   —          plan v1 |
|  41   10:09:02  exchange.proposed      proposer-1   proposed   art_P1  |
|  42   10:09:40  exchange.critiqued     critic-1*    4 findings art_K1  |
|  19   10:12:03  tool.errored           tool_pubmed  retry 1/3  inv_…   |
|        └ 20  10:12:21  tool.retry_scheduled → 24 tool.returned ok      |
|  47   10:15:22  exchange.closed        controller   completed  rules@v1|
|  56   10:31:04  criterion.version_approved  C10     confirmed  4 hd_   |
|  N+1  11:05:19  leaderboard.snapshot_published C12  lb_T1_1   diff ▸   |
|  N+3  11:06:00  round.closed R1_1      controller   stop: round_limit_reached |
|  M+1  13:40:10  human.review_decided   expert E2    approve_with_edits hd_H9 |
|        └ M+4 staleness.marked 44 stale · M+5 rerun.scheduled 32 required |
|  M+6  13:41:00  run.continued → R1r    operator O1  rerun      cause M+5 |
|  R2   next day  run.continued (refresh) → run_R2   operator O1       |
| * critic independence marker: cross_family                             |
| single-pass runs show one round with its steps                         |
|  [open round] [compare lb_T1_1 → lb_T1_2] [export journal]             |
+-----------------------------------------------------------------------+
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

### 5.2 Components and states

| Component | Source | Rules |
|---|---|---|
| Kind filters | event kinds | retries and heartbeats hidden by default; exchanges collapsible under their round |
| Rows | C1 events in `seq` order | each row: seq, time, kind (`ui_label`), actor, outcome (`ui_label` of `state_to` or `termination_reason`), artifact links |
| Nesting | `parent_seq` | tool retries nest under the original `tool.requested` and never create a round row; staleness and rerun events nest under the human decision that caused them |
| Distinct kind labels | Section 6 of the provenance spec | screening round, human edit, report revision, evidence-refresh run, attempt, reopen each render with a different label so none reads as a round |
| Row states | registry | completed, unresolved, failed, cancelled, superseded_by (correction link), current |
| Actions | — | open round (shows the round's evidence considered, proposal vs critique, decision and rationale, resulting changes), compare two snapshots, export journal range |

Opening a round shows: input versions (`rules@v`, `evs_`, `strat@v`), the Evidence visibility manifest of each decision, the proposal and critique side by side with the typed `checks[]` and `findings[]`, the adjudication with dissent, the human decisions, the per-candidate changes, the Continuation decision with its `stop_reason` or triggering `oq_`, and the Round Progress Record verdict. Raw transcripts are not needed to read a round.

---

## 6. Version-difference view

### 6.1 Wireframe

```
+-- difference · rules@v1 → rules@v2 · lb_T1_1 → lb_T1_2 ───────────────+
| cause   human edit by expert E2 · 13:40:10 · hd_H9                     |
| reason  "as-reported unit differs from rule unit; normalization note"   |
| approval  HUMAN SCIENTIFIC APPROVAL (hd_H9) · admission hash H1 → H2    |
+-- criteria ───────────────────────────────────────────────────────────+
| modified  attr_A5@v1 → @v2  unit  mg → mg/kg          cause hd_H9      |
| modified  rule_R7@v1 → @v2  cutoff_basis unchanged; applicability      |
|           all → oral dosing only                      cause chg_7f3a21    |
| added     attr_A12@v1  preference  (claims claim_K31, claim_K33)        |
| merged    attr_A4 + attr_A6 → attr_A13  basis definition_and_unit_match |
| split     attr_A8 → attr_A14 + attr_A15  distinct applicability sets   |
| removed   attr_A11  removal_kind unsupported  (coverage record cov_…)   |
+-- candidates and ranking ──────────────────────────────────────────────+
| status_changed  cand_X  provisional → recommended   cause chg_7f3a21 ✓ linked |
| status_changed  cand_Y  recommended → provisional   unknown_missing on attr_A5 |
| exclude         cand_Z  provisional → rejected      cause claim_K44 ✓ linked |
| unrank          cand_W  hard-rule cell became unknown (not a failure)   |
| rank_changed    cand_V  #4 → #6 · score 0.71 → 0.58  cause chg_7f3a21     |
| !! unexplained  cand_U  score changed with no cause → rendered as defect|
|   each row: [evidence] [decision] [critique] [rerun status]            |
+------------------------------------------------------------------------+
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

### 6.2 Components and states

| Component | Source | Rules |
|---|---|---|
| Cause header | the `chg_`/`hd_`/`claim_`/`res_` that caused the version | shows actor, reason text, `approval_kind` (only `human_scientific_approval` renders as approval), admission-predicate hash before/after |
| Criterion change list | `chg_` records between the two `rules@v` | operation label from registry (added, modified, merged, split, removed, reinstated); `fields_changed[]` as before → after; each with `cause` |
| Candidate change list | `change_records[]` of the later snapshot | operation label (admit, exclude, demote, promote, unrank, rank_changed, status_changed, score_changed) |
| Explanation status | `explanation_status` | `evidence_linked` shows a check; `unexplained` renders as a defect banner |
| Row actions | links | evidence inspector, decision artifact, critique artifact, rerun status |

A result-kind change (for example `both_reported` → `ranked_under_score`) is shown in the header because it changes what the snapshot claims.

---

## 7. Candidate detail

### 7.1 Wireframe

```
+-- cand_…  [adapter identity widget: structure · identifiers · aliases] +
| task_T1 · lb_T1_2 · state RECOMMENDED · rules@v2 · evs_T1_1            |
| result kind: all_pass_set (primary) · ranked position #1 of 112 assessed |
| state reason: all applicable hard rules pass · hard_rule_coverage 9/11  |
|   ≥ const_coverage_floor · 1 unknown (preference) · 1 inapplicable      |
| HUMAN REVIEW   approved by expert E1 · 10:31 · hd_H3                    |
| agent verdicts  proposer: support · critic: no unaddressed finding      |
|                 (an agent verdict is not approval)                      |
| independence level  deterministic_plus_model · critic cross_family      |
| provenance  independent_support_count 2 · 1 shared-experiment group     |
+-- per-criterion ───────────────────────────────────────────────────────+
| criterion    value      value_kind  verdict           reason   evidence  review |
| attr_A1@v2   34 %       measured    pass              rsn_…    claim_K7  none   |
| attr_A3@v2   12 µL/min  measured    pass              rsn_…    claim_K9  human_approved |
| attr_A5@v2   —          missing     unknown_missing   rsn_…    absence check  none |
| attr_A7@v2   6.1 µM     predicted   pass              rsn_…    claim_K12 none   |
|   counter-evidence claim_K44 1.8 µM → conflict open → queued            |
| attr_A9@v2   n/a        —           inapplicable      rsn_…    —         n/a    |
| completeness 9 / 11 with evidence · 7 reused (ckpt_R1_49) · 4 re-evaluated |
| [evidence inspector] [history] [exclude with reason] [request targeted follow-up] |
+--------------------------------------------------------------------------+
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

### 7.2 Components and states

| Component | Source | States / rules |
|---|---|---|
| Identity block | adapter identity record and widget | the structure and identifier display is an adapter-provided widget (compound structure, identifiers, aliases, `identity_link_basis`); the core renders only what the adapter supplies |
| State and reason | Candidate roll-up | state: recommended, provisional, unassessed, rejected; `state_reason`; result kind and position only when applicable |
| Human review block | `hd_` records | `none`, `requested`, `human_approved`, `human_rejected`, `disputed`; renders "no human review yet" when none; visually separate from agent verdicts |
| Agent verdicts line | decision artifact | labelled as agent verdicts; never in the approval slot |
| Independence line | Independence Declaration | level and markers |
| Provenance line | roll-up and independence groups | counts over groups, never over claims |
| Per-criterion table | Assessment records | value, unit, `value_kind` (measured, curated, predicted, simulated, derived, missing), verdict (pass, fail, unknown_missing, unknown_conflicted, inapplicable, not_assessed), reason link, evidence links, review state; counter-evidence shown under the row with conflict state |
| Completeness and reuse | roll-up; Reuse records | "k / n with evidence"; `reused` with checkpoint vs `re_evaluated` |
| Actions | C18 | exclude with reason (creates `hd_` and a change record), request targeted follow-up (creates `oq_`), history (all assessments across snapshots) |

Reference idea reused: separated review dimensions (App.tsx 3785-3799); added: the attributed human-approval dimension that the reference lacked.

---

## 8. Evidence inspector

### 8.1 Wireframe

```
+-- claim_K7 · src_doi_… ─────────────────────────────────────────────────+
| source status  peer_reviewed_paper · issued 2023 · access full_text_available |
| retraction_state none · version_label v2 · supersedes src_… (preprint)   |
| admission ADMITTED · independence group ig_… (basis assumed_distinct)    |
| claim type literature_extracted · verifier V1 · verification supported   |
| used by attr_A1@v2, attr_A3@v2 · 44 assessments · lb_T1_2                |
+-- exact passage ────────────────────────────────────────────────────────+
| p. 7, Table 2 — "…34 % (rat, 5 mg/kg)…"  span_checked_against_source ✓  |
| reading_depth full_text · extraction_actor assessor-3 · [open source]    |
+-- support / conflict ───────────────────────────────────────────────────+
| SUPPORTS   attr_A1 pass for cand_…  (scope_match direct)                 |
| CONFLICTS  claim_K44 (1.8 µM) vs claim_K12 (6.1 µM) on attr_A7 → OPEN     |
|            [assign to expert] [request measurement]                      |
| rejected references retained: claim_K901 (not in retrieved set)          |
| note: the identifier check passed; this does not establish that the      |
|   scientific claim is correct                                            |
| [dispute] [submit better source] [raw trace — expert/auditor only]       |
+--------------------------------------------------------------------------+
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

### 8.2 Components and states

| Component | Source | States |
|---|---|---|
| Source header | Source record | source_status values; access_state; retraction_state; supersedes links |
| Admission and independence | Claim record; Independence group | admission_state: pending, admitted, quarantined, rejected, superseded; group basis |
| Verification line | Claim record | claim_type; verifier_id; verification_status: supported, unsupported, contested, unverified |
| Exact passage | Location record | locator, quoted span, `span_checked_against_source`, reading_depth |
| Support and conflict | Claim polarity relative to attributes; conflict records | relation: supports, conflicts, inconclusive; conflict: open, expert_assigned, resolved |
| Retained rejected references | critique verification | shown, never deleted |
| Standing caution | fixed text | identifier check is not correctness |
| Raw trace button | trace store | visible only to expert or auditor roles; opening journals `trace.opened` |

Reference idea reused: citation checks that retain rejected references (reviewer.py 206-230, 382-418); added: navigation from a claim to its passage and the explicit caution line.

---

## 9. Human-review queue

### 9.1 Wireframe

```
+-- review queue · task_T1 · 3 open · 1 blocking ───────────────────────────+
| pri   age   subject                    why expert           state         |
| HIGH  4 m   rule_R7@v1 unit correction  hard_exclusion→confirmed BLOCKING |
|             requested by critic-1 · run paused at step_…_6                |
| MED   22 m  admit cand_E (identity)     name_match_ambiguous   open       |
| MED   31 m  conflict claim_K44/K12      unknown_conflicted hard rule open |
| LOW   2 h   report revision r-4         optional               open       |
+-- inspect q_… · rule_R7@v1 (pending) ─────────────────────────────────────+
| proposal  raise cutoff 20 % → 30 % (proposer-1) · falsification_test …     |
| critique  "source is rat, not human" (critic-1, cross_family)              |
| evidence  claim_K7 admitted · claim_K12 admitted · claim_K901 rejected     |
| if approved: 44 stale · 32 rerun (required) · 12 reusable · within budget  |
| decision  ( ) approve  ( ) approve_with_edits  ( ) reject  ( ) defer       |
|           ( ) escalate ( ) abstain                                         |
| edits     [field ▾] before → after                                          |
| reason*   [                                                            ]   |
| exposure* original list: ( ) had not seen it  ( ) had seen it              |
| this creates hd_… by expert E2 (authenticated_account) · scope of expertise |
|  [claim] [release] [submit] [defer] [reassign] [record disagreement]        |
+----------------------------------------------------------------------------+
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

### 9.2 Components and states

| Component | Source | States / rules |
|---|---|---|
| Queue list | Queue items (`q_`) | priority, age, subject, `why_expert_required` (trigger-table row), blocking flag, state: open, in_review, decided, deferred, expired, withdrawn |
| Inspection pane | `inspection_bundle` | proposal, critique, evidence with admission states, precomputed consequences (stale, rerun, reusable counts; budget check) |
| Decision control | Expert decision record | approve, approve_with_edits, reject, defer_more_evidence, escalate, abstain, request_followup, pause, resume, retire (memory items); `edits[]` field-level before → after; mandatory `reason_text` except for approving an unedited proposal |
| Attribution line | actor fields | person, role, `identity_basis`, `declared_scope_of_expertise`; names the `hd_` that will be created |
| Claim control | `human.review_claimed`, `human.review_claim_released` | claim, release, reassign; a live claim reserves the item until released, reassigned, or expired after `const_review_claim_lease` (design §12.3) |
| Exposure declaration | `hd_.historical_list_exposure` | required on criterion-affecting decisions: had not seen the original list / had seen it; checked against the access log (design §8.6) |
| Record disagreement | `hd_.disputes_decision_id` | for an item another person has decided; both records kept; subject becomes `unresolved` and labelled disputed (design §12.2) |
| Blocking semantics | C18 ownership of `waiting_human` | a run with an open blocking item cannot project `running`; the monitor shows `blocked_on_review[]` |

Reference finding this replaces: the inspected application had one unattributed human-input route and no approve/edit/reject record (Workstream 4 F8).

---

## 10. Human interventions and their consequences

| Action | Record created | Versioning | Stale | Rerun | Reuse | Expert required |
|---|---|---|---|---|---|---|
| Inspect pending proposal | none (view); `trace.opened` only if raw trace viewed | none | none | none | all | no |
| Edit proposal | `hd_` approve_with_edits; revision artifact | new proposal version, `parent_artifact_id` | records citing it | the open exchange | earlier rounds | yes |
| Reject with reason | `hd_` reject | proposal closed, retained | none | none; round may close `unresolved` | all | yes |
| Approve rule-set version | `hd_` approve → `rules@v` | registry version confirmed | assessments on the prior version | assessments whose criteria changed | assessments on unchanged criteria | yes |
| Add compound | `human.input_submitted`; identity resolution | universe version | snapshot | that compound only | all others | no (identity check automatic) |
| Exclude compound | `hd_` + change record exclude | snapshot | that candidate's rank context | ranking | its assessments | yes if evidence-based, no if scope-based |
| Correct units, thresholds, applicability | `hd_` + `chg_` modified | registry version | every assessment using it | affected assessments and ranking | records where inapplicable | yes |
| Correct an interpretation | `hd_` conflict_resolution or claim revision | ledger row | assessments citing the claim | those assessments | others | yes |
| Submit references or results | `sub_` → provisional claims | ledger row on admission | none until admitted | none automatically | all | yes to admit (non-submitter reviewer); intake automatic |
| Request targeted follow-up | `oq_` open question (`human_request`, subject named); `rerun.scheduled` with scope | new round if round budget is left; otherwise a run continuation | none | the named scope only | everything outside it | no |
| Pause / resume / cancel | `run.paused` / `run.resumed` / `run.cancelled` | `ckpt_` | none | in-flight step on resume | completed steps | no |
| Approve Rerun Plan above budget | `hd_` | — | — | the plan | — | yes (non-blocking item) |

Submission is not acceptance: supplied references and results enter `provisional` with `submitted_by`, and only an admission decision makes them usable. A resumed run shows its Reuse manifest and labels every assessment `reused` or `re_evaluated`.

---

## 11. Leaderboard view and filters

```
+-- leaderboard · task_T1 · lb_T1_2 (published 13:41) · rules@v2 · evs_T1_1 +
| result kind both_reported (all-pass primary) · ordering method OM-1       |
| reporting tuple  admitted 1 · precision undefined? no → 1/1 · coverage 0.38 |
|   abstention 1,868 by reason {insufficient_coverage 1,650, identity 191, …} |
| tool coverage  target: measured 212 · predicted 0 · nothing 2,768 ·        |
|   interaction_estimate_provider none                                        |
| filters [objective ▾] [target coverage ▾] [candidate source ▾] [rules@v ▾] |
|         [evidence status ▾] [evaluation completeness ▾] [properties ▾]      |
| RECOMMENDED (1)   PROVISIONAL (37)   UNASSESSED (2,942)   REJECTED (191)   |
| cand_…  recommended  coverage 9/11  independence deterministic_plus_model   |
|         human_approved · reason: all applicable hard rules pass …   [open] |
| cand_…  provisional  coverage 6/11  1 unknown_missing hard rule     [open] |
| unassessed and exploratory candidates: separate tab labelled                |
|   "not evidence-qualified"                                                   |
| [snapshot history lb_T1_1 → lb_T1_2 → …] [compare] [export]                 |
+------------------------------------------------------------------------------+
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

Filters operate on fields of the Candidate entry and the snapshot: objective (task context), target coverage (per-dimension measured/predicted/nothing), candidate source (universe segment, seed, human-added), `rules@v`, evidence status (admitted, provisional, disputed), evaluation completeness (coverage band), properties (adapter-declared attributes). Each snapshot in the history is immutable and opens the version-difference view against its predecessor. Different task contexts are never merged into one list.

---

### 11.1 Recovery comparison panel (primary case)

Reached from the Leaderboard view by users with an evaluator role. Opening it is a logged read of the historical-criteria intake and makes the viewer `exposed` (design §8.6), so the panel warns before opening and is never offered on a criterion-confirmation item.

```
+----------------------------------------------------------------------+
| Recovery comparison   rules@v1 · lb_T1_1 · completeness: complete      |
|  view       | recovered | diff. cutoff | merged | split | removed | not rec. | added |
|  independent|    k1     |      j1      |   m1   |  s1   |   r1    |    u1    |  a1   |
|  assisted   |    k2     |      j2      |   m2   |  s2   |   r2    |    u2    |  a2   |
|  denominator: N original criteria (attestation shown)                 |
|----------------------------------------------------------------------|
| original item | mapping kind | match basis | derived refs | view | reason quality |
| H1            | recovered_.. | definition_ | attr_..      | ind. | rating          |
+----------------------------------------------------------------------+
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

Each row links to its recovery comparison record, its rationale references, and, for `expert_judged_equivalent`, the `hd_` record. The two views are always shown together with their denominators.

## 12. Progress and event interface summary

The UI subscribes with `subscribe(stream_id, from_seq)` and applies events in `seq` order; it keeps `last_applied_seq`, ignores duplicates, resubscribes at `last_applied_seq + 1` after a disconnect, and accepts a projection snapshot with `snapshot_seq` when its position predates compaction. Freshness is computed from heartbeat age against per-step-type stall thresholds. Progress rows read `progress {scope, denominator_kind, completed, planned, indeterminate}` and the budget meter reads `budget`; counters change only on completion-class events; `progress.estimate_revised` renders as "plan revised". Record shapes, event kinds, and the mapping to persisted stores are in `iteration_and_provenance_spec.md`; the transport is an implementation choice.

---

## 13. Registered labels (what every state renders as)

| label_domain | Values and `ui_label` | `ui_tone` |
|---|---|---|
| execution | queued "queued"; running "running"; waiting_tool "waiting for tool"; waiting_human "waiting for expert review"; retrying "retrying"; paused "paused"; failed "failed"; cancelled "cancelled"; completed "completed"; unresolved "unresolved"; rejected "rejected" (steps only) | neutral; neutral; info; attention; warning; neutral; negative; neutral; positive; attention; negative |
| exchange | proposed, critiqued, revising, adjudicating, completed, rejected, unresolved | as above by outcome |
| candidate | recommended "recommended"; provisional "provisional"; unassessed "unassessed"; rejected "rejected" | positive; neutral; muted; negative |
| result_kind | all_pass_set "unique all-pass under hard rules" / "all-pass set"; ranked_under_score "top-ranked under score"; both_reported "both"; no_recommendation "no recommendation (abstained)" | — |
| verdict | pass; fail; unknown_missing "unknown (missing)"; unknown_conflicted "unknown (conflict open)"; inapplicable "not applicable"; not_assessed "not assessed" | positive; negative; muted; attention; muted; muted |
| value_kind | measured; curated; predicted; simulated; derived; missing | distinct glyphs; predicted never styled as measured |
| review | none "no human review yet"; requested; human_approved "approved by expert"; human_rejected; disputed | muted; attention; positive; negative; attention |
| change_kind | added, modified, merged, split, removed, reinstated; admit, exclude, demote, promote, unrank "left unranked (not a failure)", rank_changed, status_changed, score_changed | — |
| termination_reason | sufficient_support; round_limit_reached "planned rounds finished"; no_actionable_step; diminishing_information_gain; repeated_failure; budget_exhausted "budget exhausted (unresolved)"; human_decision; dependency_unresolved; cancelled | budget_exhausted always attention, never positive |
| historical_list_exposure | not_exposed "had not seen the original list"; exposed "had seen the original list"; undeclared "not declared (treated as seen)" | neutral; attention; attention |
| recovery_view | independent "derived without the original list"; assisted "derived with input from people who knew the original list" | neutral; neutral |
| omitted_reason (additions) | evaluator_only_artifact "evaluator-only"; case_source_document "case-source document (blocked)" | muted |
| not_assessed_reason | identity_unresolved "identity not resolved"; identity_pending_review "identity awaiting review"; budget_exhausted "not reached (budget exhausted)"; run_cancelled "not reached (run cancelled)" | attention |
| field_visibility | agent_visible "seen by agents"; evaluator_only "evaluator only"; control_only "system control only" | — |
| dependency_detail | derivation_unavailable "criteria could not be derived"; capability_failure_share_exceeded "too many tool failures for one capability"; required_input_missing "required input missing" | attention |
| sweep_scope | full_universe "all candidates"; rerun_plan "rerun of stale records"; refresh_delta "records touched by new evidence" | neutral |
| denominator_kind | enumerated_fixed (percent allowed); enumerated_growing ("≥"); budget_bounded (budget meter only); unbounded_adaptive, unknown (indeterminate) | — |
| view_freshness (client-derived) | live; view_stale "view stale — last seq N, age"; activity_unknown "no heartbeat for …" | positive; warning; attention |
| surface | terminal "terminal"; browser "browser" | — |
| host_platform | linux "Linux host"; windows "Windows host" | — |
| session_role | operator "operator"; expert "expert"; evaluator "evaluator"; auditor "auditor" | — |
| command_entry | interactive "confirmed by you"; scripted "scripted" | — |
| host_gap_kind | stop "host stopped"; suspend "host was asleep" | attention |
| platform_support_basis | checked "checked"; upstream_documented "documented upstream, not checked here"; unchecked "not checked" | neutral; muted; attention |
| continuation_kind | root "first run"; continue "continued"; refresh "refreshed with new evidence"; rerun "rerun of stale records" | neutral |
| memory kind (display) | reusable_procedure "skill"; tentative_hypothesis "lesson"; evidence "remembered evidence" | — |
| memory review state | provisional "provisional — not yet reviewed"; under_review "under review"; approved "approved"; rejected "rejected"; retired "retired" | muted; attention; positive; negative; muted |
| run_group_state | active "active"; archived "archived (read-only)" | neutral; muted |
| queue_item_state | open "open"; in_review "in review"; decided "decided"; deferred "deferred"; expired "expired"; withdrawn "withdrawn (run continued)"; machine_adjudicated "resolved by an agent (no person confirmed it)" | neutral; attention; positive; muted; muted; muted; attention |
| host_start_refusal | store_locked "another host is using this store"; store_root_unsupported "store folder is synchronized or on a network drive" | negative |
| acceptance_label | prespecified "prespecified"; exploratory "exploratory (chosen after results)" | neutral; attention |
| decision_authority (addition) | human_scientific_approval "confirmed by an expert"; machine_adjudication "adjudicated by an agent; no person confirmed it"; trigger_table "admitted automatically by the trigger table" | positive; attention; neutral |
| adjudication_route (addition) | task_constraint_restated "restates the task's own constraint"; no_authority_available "no authority available; demoted, stops scoring"; irreversible_without_authority "too irreversible for an agent; demoted to a preference"; dispute_adjudicated "proposer/critic dispute adjudicated by an agent" | neutral; attention; attention; attention |
| adjudication_verdict (addition) | uphold_proposal "the proposal stands"; uphold_objection "the objection stands"; revise "settled by a change to the rule"; cannot_resolve "not settled; the rule stops scoring" | neutral; attention; neutral; attention |
| trigger_class (addition) | human_request "requested by a person" | neutral |
| command_outcome | applied "applied"; duplicate "already done (no change)"; rejected_stale_basis "changed since you looked — not applied"; rejected_unauthorized "not permitted for your role"; rejected_invalid "not applied — invalid input"; rejected_not_permitted_in_state "not possible in the current state" | positive; neutral; attention; negative; negative; attention |
| terminal exit status (`run wait`) | completed → success; unresolved, failed, cancelled, connection lost → four distinct non-success statuses | `unresolved` never maps to success |

No label may map an `unresolved` or `budget_exhausted` state to a word implying advancement (the inspected reference's "sent after revision limit" is the prohibited pattern).

---

## 14. What this specification does not decide

Component library, visual theme, terminal text-interface toolkit, transports (SSE or WebSocket for the browser; loopback HTTP or a local socket for the terminal), packaging of the Windows launcher, identity provider for expert attribution, stall thresholds per step type (to be measured), and whether a local single-user deployment can carry meaningful attribution without an external identity claim (recorded as an open question). These are design artifacts only; the UI and the event transport are not implemented in this phase.

---

## 15. Two operator surfaces: terminal client and browser workbench

A person may operate the system from a Linux terminal or from Chrome, including Chrome on Windows talking to a service host on the same Windows machine. Both surfaces are clients of the Operator API (`optimized_design.md` §2.4) served by one service host (§14.1 of the design); neither holds state, so one run can be followed and acted on from both at once.

### 15.1 Deployment profiles as the person sees them

| Profile | How the person starts | What they open |
|---|---|---|
| L (Linux host) | starts the service host in a terminal or as a user service | the terminal client; optionally Chrome on the same host, at a single-use address printed by `session open --browser` |
| W (Windows host) | starts the service host from a launcher | the launcher opens Chrome at a single-use, short-lived loopback address, which is exchanged for a session |
| X (Linux host, Windows browser) | starts the service host on the Linux machine; opens an SSH local port forward from Windows, bound to the Windows loopback | the terminal on the Linux host; Chrome on Windows at the address printed by `session open --browser`, through the forwarded port |

In v1 the terminal client operates Linux hosts; a Windows host is operated from Chrome. A Linux terminal operating a Windows host is not supported (design §18, U-15). The activity bar on every browser screen and the header of every terminal view name the host (`host_platform`), the store root, and the session's person and roles.

### 15.2 Parity rules

1. **Same records, same labels.** Both surfaces read the same projections and render every state through the C2 `ui_label`; no surface has a label, state, or count of its own.
2. **Same honesty rules.** Percentages only for `enumerated_fixed`; the budget meter is labelled as budget; the approval slot reads "no human review yet" without an `hd_` record; `unresolved` is shown with its open question; freshness is shown and motion stops when the view is stale (Section 1).
3. **Tone without colour.** The terminal shows each `ui_tone` as a word or glyph as well as a colour (for example `[attention]`) and drops colour when output is not a terminal or the person has asked for no colour.
4. **Nothing silently cut.** A table wider or longer than the terminal is truncated with an explicit "… n more (show all)" line, never silently.
5. **Effects only from events.** After a command, a surface shows "sent" until the event recording the effect arrives; it never shows the predicted result first.
6. **Same visibility.** A role sees the same fields on both surfaces. Evaluator-only content needs the evaluator role on either, is read only through a confirmed command that shows the exposure warning, and is shown on screen only: never exported, downloaded, or written as line-delimited output.
7. **Same confirmations, entered by a person.** A review decision shows its precomputed consequences (stale, rerun, and reuse counts) and the exposure declaration, and requires a reason, on both surfaces. The confirmation is answered by the person at the surface; in the terminal it is read from the terminal itself, not from standard input or a flag, so a script cannot supply it.
8. **Machine-readable output is the same data.** The terminal's line-delimited output carries the same record fields, stream, and `seq` as the API, evaluator-only records excepted; it is not a second format to keep in step.
9. **Same words for the same action.** Both surfaces say "cancel" for `run.cancelled` and "applied" for an applied command.

### 15.3 Screen-to-command map

Commands are shown without the program name, which is an implementation choice. Every command offers a human-readable and a line-delimited output mode, except that evaluator-only content is shown on screen only. The role column follows the role table of design §2.4.

| Browser screen or action | Terminal command | Record written | Role |
|---|---|---|---|
| Sign in; who am I | `session open`, `session show`, `session close`; `session open --browser` prints a single-use browser address, also for another person | `ses_` | any; an address for another person: `operator` |
| Task list | `task list` | none | any |
| Case configuration (new, edit, attach the comparison artifact) | `case new --from <file>`, `case edit <case>`, `case attach-intake <case> --from <file>` | case version; the intake stored encrypted (design §14.1) | `operator`; attaching the intake: `evaluator` |
| Task input (new, edit) | `task new --from <file>`, `task edit <task>`: the task context opens as a structured text file in the person's editor and is validated on save; blocking unknowns are listed | `task_@v` through C4 | `operator` |
| Plan only | `run plan <task>` | `plan.recorded` | `operator` |
| Start a run | `run start <task>`; refused while a blocking unknown is open | `run.created` through C15 | `operator` |
| Live run monitor | `run watch <run>`: a full-screen view in a terminal, appended lines otherwise | none | any |
| Pause, resume, cancel | `run pause <run>`, `run resume <run>`, `run cancel <run>`, each with confirmation | `run.paused`, `run.resumed`, `run.cancelled` | `operator` |
| Wait for a run to end (scripted) | `run wait <run>`: exit status by terminal state (Section 13) | none | any |
| Round timeline; open a round; export a journal range | `run timeline <run> [--kind …]`, `run round <round>`, `export --journal <run> --from-seq <n> --to-seq <m> --to <file>` | export: operator log | any; export: `operator` |
| Rules & criteria | `rules show <rules@v> [--history]`, `rule show <rule@v>`, `attr show <attr@v>` | none | any |
| Version-difference view | `rules diff <rules@v> <rules@v>`, `board diff <lb> <lb>` | none | any |
| Leaderboard and filters; current snapshot | `board show <task> [--state …] [--snapshot <lb>]`, `board set-current <lb>` | none; `leaderboard.current_set` | any; setting the current snapshot: `operator` |
| Candidate detail | `candidate show <cand> [--snapshot <lb>]` | none | any |
| Exclude with reason | `candidate exclude <cand> --basis <scope or evidence> --reason-file <file>` | change record; `hd_` when the basis is evidence | `operator` for scope; `expert` for evidence |
| Add compound | `universe add <task> --from <file>` | `human.input_submitted`; identity resolution | `operator` |
| Request a targeted follow-up (the same as Add a round) | `run followup <run> --subject <ref> --question …` | `oq_` with `human_request` | `operator` or `expert` |
| Evidence inspector | `claim show <claim>`, `source show <src>` | none | any |
| Dispute a claim; submit a better source; assign to an expert; request a measurement | `claim dispute <claim> --reason-file <file>`, `submit --for <claim> …`, `claim assign <claim> --to <person>`, `claim request-measurement <claim> --note …` | queue item; `sub_` | dispute: `expert`; others: `operator` |
| Raw trace (role-gated) | `trace open <trace ref>`, with confirmation | `trace.opened` | `expert` or `auditor` |
| Human-review queue | `review list`, `review show <q>`, `review claim <q>`, `review release <q>`, `review reassign <q> --to <person>`, `review decide <q> --decision … --reason-file <file> [--edits-file <file>] --exposure <declaration>`, `review dispute <hd> --reason-file <file>` | `human.review_claimed`, `human.review_claim_released`, `hd_` through C18 | `expert`; reassign: `operator` |
| Submit references or results | `submit --text-file <file>`, `submit --path <path in an intake directory>`, or standard input | `sub_` | `operator` or `expert` |
| Approve a Rerun Plan above budget | `rerun approve <plan>` | `hd_` | `expert` |
| Recovery comparison panel | `recovery show <task>`, with the exposure warning and confirmation; on screen only | `evaluator_only.read` | `evaluator` |
| Evaluation | `eval prereg <task> --run <run> --stage <1 or 2>`, `eval compare <task> --snapshot <lb>`, `eval scan <subject>`, `eval protocol register --from <file>`, `strategy promote <strat@v>`, `strategy rollback <strat@v>` | `preregistration.recorded`; `evaluation.recorded` (case stream); `proto_`; `ops_` | `evaluator`; promotion and rollback: `operator` with the evaluation-lead grant |
| Export | `export <record> --to <file>`, filtered by role and visibility; never evaluator-only content | operator log | `operator` |
| Run-group switcher | `group list`, `group show`, `group switch <grp>`; `--group <grp>` on any command | session setting (operator log) | any |
| Create, rename, archive, or reactivate a group; move or copy a task | `group new <name>`, `group rename <grp> <name>`, `group archive <grp>`, `group reactivate <grp>`, `task move <task> --to <grp>` (tasks without runs), `task copy <task> --to <grp>` | `group.*`, `task.group_changed`, new task | `operator` |
| Run chains; continue; branch | `chain list [--task <task>]`, `chain show <chain>`; `run continue <run> [--kind <continue, rerun, or refresh>] [--rounds <n>] [--budget-file <file>] [--memory-mode <mode>] [--policy-arm <arm>] [--strategy <strat@v>] [--cutoff <date>] [--tools-file <file>] [--group <grp>] [--task-edits-from <file>] [--branch <label>]`. `--task-edits-from` holds task-context and binding fields only; rule changes exist only as `hd_` records from `review decide`, which the continuation lists. The command shows the edits, reuse estimate, `chain_cost`, leaderboard effect, and what happens to the parent, and asks for interactive confirmation | `run.continued`; a new `run_` in the chain | `operator`; closing a registered run early: `evaluator` |
| Add a round | `run add-round <run> --subject <ref> --reason-file <file> --expected-change …`; refused in evaluation-arm and prespecified runs, which are continued instead | `oq_` with `human_request` | `operator` or `expert` |
| Rename a run; notes and tags | `run annotate <run> [--name …] [--note …] [--tag …]` | `run.annotated` | `operator` |
| Skills & lessons | `memory list [--kind <skill or lesson>] [--state …]`, `memory show <mem>`, `memory add --kind <skill or lesson> --from <file>` (interactive confirmation), `memory send-for-review <mem>`, `memory retire <mem> --reason-file <file>` (provisional items; an approved item is retired through the review queue), `memory trial <mem>` | `memory.operation_recorded`; approval through `review decide`; a trial request to C19 | any to read; `operator` or `expert` to add or retire; `evaluator` to request a trial |

Memory items awaiting approval reach people as review-queue items (design §10.3) and are decided with `review decide`. The Evaluation screen added to the map of Section 2 lists preregistration events, protocol manifests, and strategy versions with the commands above; its wireframe is left to implementation.

### 15.4 Terminal wireframes

Run watch, which fits 80 columns and carries the same rows as the browser monitor of Section 4, with registered labels:

```
run_R1 · running · live (2 s ago) · Linux host · grp_case-a · E1 (operator)
task_T1@v1 · plan_R1@v2 (revised 1x) · rules@v1 · evs_T1_1 · P0
OVERALL  stages 3 / 7 declared · plan revised 1x
STAGE    assess: 118 / 2,980 enumerated_fixed · 4 %
ROUND    round_R1_1 · steps 4 / 6 declared
BUDGET   rounds 1 of 1 · tool calls 87 / 200 · 41 m of 2 h
         (budget consumed - not completeness)
ELAPSED  00:41:18 · last activity 2 s ago
NOW      state                      actor        owns        question
         running                    assessor-3   cand_...    stability value?
         waiting for tool           tool_chembl  inv_...     activity records?
         running                    critic-1     xchg_..._1  unit matches rule?
         waiting for expert review  expert E1    rule_R7@v1  approve unit fix?
PROBLEMS [warning] tool_pubmed retrying 2 / 3 (rate_limited), next in 18 s
         [muted] tool_gdsc_context not attempted (identity not resolved):
                 cell recorded unknown (missing), not a failure
         [attention] tool_gtopdb degraded; run_degradation recorded
keys: p pause · c cancel · t timeline · r review queue (1 blocking) · q quit
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

A review decision at its confirmation step:

```
review decide q_7 --decision approve_with_edits
              --edits-file edits.txt --reason-file reason.txt
subject   rule_R7@v1 unit correction (hard rule)          [blocking]
claim     held by you until 14:32
edit      unit: as reported -> normalized                 (1 field)
reason    read from reason.txt (212 characters)
effect    stale 31 assessments · rerun 31 · reuse 2,949
reviewer  E1 (expert) · identity: recorded attestation · via terminal
exposure  had not seen the original list (declared; access log agrees)
confirm by typing the item id (q_7):
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

The same decision when another person decided the item first:

```
not applied: changed since you looked
q_7 was decided at seq 4,412 by E2 (browser): approve
your decision was based on seq 4,398 and was not applied
show that decision; you may record a disagreement or leave it
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

### 15.5 Browser workbench in Chrome on Windows

- **Supported browser.** Current stable Chrome; other browsers are best-effort. The workbench needs no browser extension and no internet access of its own.
- **Tabs.** Each tab is its own subscriber with its own `last_applied_seq`; a tab hidden or throttled by the browser shows `view_stale` on return until it has resubscribed from `last_applied_seq + 1`.
- **No cached records.** Pages and assets may be cached; records never are. After a host restart, an open page shows `view_stale` until its subscription is live again.
- **Files.** Upload sends a file to the service host, where it is stored by content hash (design §12.4). A local path is offered only when the browser and the host share a machine (profiles L and W), and only inside a directory the operator registered for intake (design §14.1); on profile X a path on the Windows machine is not readable by the Linux host, so only upload is offered.
- **Downloads and exports.** Filtered by role and visibility and logged, exactly as the terminal's `export`; evaluator-only content is never downloadable.
- **Closing Chrome.** Closing the browser does not stop a run, which continues in the service host. Closing the service host's window does stop it, and that is handled as an abrupt stop (Section 15.7).

### 15.6 Using both surfaces at once

| Situation | What happens | What each surface shows |
|---|---|---|
| The same run watched from the terminal and from Chrome | two subscribers, one journal | the same states, counters, and labels at each `seq` |
| Pause sent from the terminal while Chrome is open | one `run.paused` event | both show "paused" once the event arrives; Chrome shows who paused it and from which surface |
| Two people decide the same review item | the first decision is applied; the second is `rejected_stale_basis` | the second person sees the applied decision and may record a disagreement (`disputes_decision_id`; the subject becomes `unresolved`, labelled disputed) or leave it |
| A review item claimed on one surface | `human.review_claimed` reserves it; a decision by anyone else is `rejected_not_permitted_in_state`; release, reassignment, or expiry after `const_review_claim_lease` writes `human.review_claim_released`, written by the scheduler on expiry, also after a host gap | the claim and its holder on both; the item returns to `open` on both when released |
| A command resent after a dropped connection | `duplicate`, with the original result | the original outcome, applied once |

### 15.7 When the service host stops or sleeps

Both surfaces go `view_stale` with the last applied `seq` and its age; nothing moves. After the host restarts or wakes, the surfaces show "host stopped" or "host was asleep" for the gap, the finalized attempt, and the checkpoint the new attempt resumed from. A paused run stays paused, a step waiting for expert review keeps waiting, and only steps that were running, retrying, or waiting for a tool are re-queued; each restored step is labelled reused or re-evaluated as for any resume. The gap is charged to no budget, and the timeline shows it as a gap with no step running during it.

---

## 16. Editing and continuing runs, run groups, and skills and lessons

All three features work the same on both surfaces; the commands are in Section 15.3 and the rules in `optimized_design.md` §6.8, §6.9, and §10.5.

### 16.1 Run chain view and the Continue dialog

A run that has been continued is shown as one entry, its chain. Rounds are numbered across the chain; each run of the chain keeps its own state, termination reason, and completeness; reused records name the run they came from; and the chain's cumulative cost is always shown.

```
+-- run chain chain_C1 · task_T1 · group grp_case-a ─────────────────────────+
| cost so far  tool calls 612 · tokens 3.1 M · 3 h 05 m · review 40 m         |
| R1    completed  planned rounds finished  round 1     lb_T1_1  first run   |
| R1·2  completed  planned rounds finished  rounds 2-3  lb_T1_2  continued   |
|       edits: rule_R7@v2 (hd_H31) · tool calls 200 -> 400                   |
|       reused 2,941 cells from R1 · computed 39 · exploratory               |
| R1·3  running    round 4                                     continued     |
|  [continue…] [edit…] [branch…] [add round…] [annotate] [set current]      |
+----------------------------------------------------------------------------+
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

```
+-- continue R1·2 ───────────────────────────────────────────────────────────+
| kind               (o) continue  ( ) rerun plan only  ( ) refresh evidence  |
| edits since R1·2   rule_R7@v2 (hd_H31) · constraint added (task_T1@v2)      |
| rounds · budget    [1] more · tool calls [400] · time [2 h]                 |
| memory · arm       [frozen ▾] · [P0 ▾]   strategy [strat@v3]  cutoff [same] |
| tools · group      [same] · grp_case-a (same) [change…]                     |
| expected work      reuse about 2,941 cells · compute about 39               |
| chain cost so far  tool calls 612 · 3 h 05 m                                |
| leaderboard        same leaderboard (the edits keep comparability)          |
| claim              exploratory: snapshots of this chain were published      |
| parent             R1·2 has ended and stays as it is; this creates R1·3     |
|                                           [cancel]  [continue as R1·3]      |
+-----------------------------------------------------------------------------+
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

"Edit…" opens the same dialog with the task-context editor. Rule changes are made in the review queue and appear here only as the `hd_` records that made them. When the parent has not ended, the parent line reads, for example, "R1·3 is running and will end cancelled; its 2 open review items are withdrawn and raised again in the new run".

| Component | Source | States / rules |
|---|---|---|
| Chain list | Run Bindings with `chain_id`, `continues_run_id`, `branch_label` | linear or branched; each run with its state, termination reason, and snapshot; chain cost |
| Continue dialog | `edits_since_parent[]`, C16 reuse estimate, C6 `chain_cost`, comparability check | every bound field editable; shows the exploratory label, the leaderboard effect, and what happens to a parent that has not ended; refused with "already continued by …" unless confirmed as a branch |
| Add-round control | C8 `human_request` with a named subject | enabled only in a run that has not ended, has round budget left, and is neither an evaluation-arm nor a prespecified run; otherwise offers Continue |
| Set current | `leaderboard.current_set` | chooses which branch's snapshot the task leaderboard shows |
| Annotation | `run.annotated` | name, notes, tags; never changes results |

### 16.2 Run-group switcher

The browser activity bar carries the active group with a switcher; the terminal shows the group in every view header and switches with `group switch`.

```
| group ▾  grp_case-a "Manuscript case" · 3 tasks · 7 runs  | running R1·3 |
|   grp_default  "Default"                                                |
|   grp_calib-1  "Calibration case 1"                                     |
|   grp_pilot-2  "Pilot" archived (read-only)                              |
|   [+ new group]  [rename]  [archive]  [reactivate]                      |
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

- Switching changes what is listed and the default group for new tasks. A run in another group keeps running, and the activity bar still shows it with its group.
- Each session has its own active group: the terminal and the browser can show different groups at once, and each always names the one it shows.
- Archived groups are muted and read-only; groups cannot be deleted.
- Moving a task that has runs is not offered; "copy to group" and "continue into group" are (continuing into a group copies the task first; design §6.9).
- Archiving is refused while a run in the group has not ended.

### 16.3 Skills & lessons screen

For the active group: memory items with their kind shown as skill or lesson, review state, origin (run, round, and whether a tool recovery, a reflection, an expert correction, or a person), use (from `memory.recalled`), and counters labelled self-judged where a model produced them.

```
+-- skills & lessons · grp_case-a · 12 provisional · 3 approved ──────────+
| kind    state          from                          used   summary     |
| skill   provisional    R1·2 tool recovery (inv_…)    0      …           |
| lesson  provisional    R1·2 reflection, round 3      2      …           |
| skill   approved       hd_H40 (expert E2)            5      …           |
| drafts rejected by the content policy: 1 (candidate_identifier)         |
|  [filter ▾] [add skill or lesson] [send for review] [request trial]     |
+-------------------------------------------------------------------------+
```
_All values in this wireframe are illustrative placeholders showing field shape; no screening was run and no number is a result._

- A provisional item reads "provisional — not yet reviewed" and is never styled as approved.
- An item drafted in a run whose memory was `cold` or `frozen` reads "drafted; not used in this run".
- "Used" counts journaled recalls; a model's own helpfulness tags are shown as self-judged.

Sources: `optimized_design.md` Sections 0, 2.4, 4.1, 4.2, 4.4, 4.11, 4.12, 4.16–4.18, 6, 11, 12, 14.1, 14.2; `agent_reports/human_review_and_ui.md` (F1–F10, §3–§8 and cross-review); `agent_reports/reference_harness_inspection.md` (§2.1, §3, F1–F3, F9); `agent_reports/mas_architecture.md` (H2 and cross-reviews); `iteration_and_provenance_spec.md`.
