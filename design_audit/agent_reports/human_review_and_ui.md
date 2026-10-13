# Workstream 4 — Human-Review and UI Audit, and the Proposed Progress/Review Experience

## Summary

The Agentic Doping snapshot contains both halves of a defensible progress architecture — a versioned UI-facing snapshot and an append-only event file — but they are not connected: `job_events.jsonl` is written by `run_dir.py` and read by nothing, so live truth is a mutable latest-state snapshot plus an in-memory job object.
Verified, not inferred: the run percentage is non-monotonic because each phase supplies its own denominator (75% at `propose`, ~90% at `evaluate`, then ~5% at `review`), and the client extrapolates an ETA from that number.
Progress events are emitted deliberately as watchdog heartbeats, so activity and completed work are one signal.
The trace API relabels the authoritative `exhausted` outcome as `sent_after_revision_limit`, although exhausted proposals never enter the recommendation plan.
Of 115 HTTP routes, exactly one accepts human input, and it carries no actor field; there is no review queue, no approve/edit/reject record, no pause/resume, and no staleness or rerun representation anywhere.
The only approval-looking fields in the product are machine verdicts (`llm_verdict`, `gate_verdict`, `disposition`), which is precisely the conflation the brief forbids.
**Most important recommended change:** make the append-only journal the sole source of truth for progress and history, with a gap-free per-run sequence number, a subscribe-from-sequence replay contract, and a hard rule that only completion-class events may advance a counter while heartbeats advance only "last activity". Indeterminate progress, the timeline, semantic diffs, staleness propagation, and the review queue are all projections of that journal and are otherwise unimplementable with integrity.

## 1. Implemented versus merely requested

The translated original request asks for TASTE-style progress bars, human editing of intermediate proposals "throughout", and intake of human results (`06_Agentic_Doping_Original_Prompt_English_Translation.md`). The snapshot implements less than the documentation implies.

| Requested capability | Status in snapshot `0007ad10` | Evidence |
|---|---|---|
| Current and overall task progress | Partial: one phase-local bar reused for both | `web/client/src/App.tsx:3111-3125`, `:3524-3546` |
| Durable iteration history | Written, never read by server or UI | `orchestration/run_dir.py:100-143`, `:189` |
| Human edits to intermediate proposals | **Absent**: no edit/approve/reject route | `web/server.py` route scan (115 routes) |
| Human experimental-result intake | Implemented, unattributed | `web/server.py:1585-1622` |
| Pause / resume | **Absent** (cancel only) | `web/server.py:1154` |
| Proposal/review version history | Implemented per slot | `dual_agent/loop.py:201-247`, `:294-300` |
| Report revision lineage | Implemented with `parent_version` | `analysis/report_iteration.py:270-290`; `ReportIterator.tsx:130-178` |
| Citation checking with rejected refs kept | Implemented | `dual_agent/reviewer.py:206-230`, `:382-418` |
| Semantic field-level diff | **Absent**: no producer or view | no diff code found |
| Staleness / rerun propagation | **Absent** | no record or route found |

All paths are relative to `/home/yiwei3_duke/anny/reference_repos/Agentic-Doping-snapshot/src/agentic_doping/`, commit `0007ad10`. Seven of eight manifest hashes match; `web/server.py` differs (`54f7fe4a…` on disk versus `ff70ed4a…` in `PROGRESS_SOURCE_MANIFEST.json`), so its lines were located by search and verified by reading.

## 2. Findings

### F1. The append-only journal is written but never read, so UI truth is a mutable snapshot

- **Issue** `ProgressWriter.progress()` writes `progress.json` atomically and appends the same payload to `job_events.jsonl`. The journal is the only immutable artifact, yet nothing consumes it: a repository search for `job_events` returns the writer, one `force_finish` append, and a docstring. The server streams from an in-memory job and the client polls the run list, so history is reconstructed from last-write-wins snapshots and an evicted run loses its intermediate record even though the file on disk holds it.
- **Source / location** `orchestration/run_dir.py:100-143`, `:189`; `pipelines/run_candidate.py:5` (docstring only).
- **Importance** High — the brief's component 11 requires events to be authoritative and the UI to be a projection; the reference inverts this, and replay, timeline, diffs, and staleness all depend on the inversion being fixed.
- **Recommended change** In **Event Journal + Progress Projection**, make the journal the only read authority; snapshot files become rebuildable projections written solely by the projector.
- **Tradeoff** Replaying a long run to rebuild a projection costs time, needing periodic projection snapshots keyed to a sequence number.
- **Unresolved uncertainty** Whether one journal per run suffices for a 140-candidate by 11-criterion fan-out, or whether per-candidate sub-journals with a parent index are required for read performance.

### F2. Progress delivery is latest-only, requires a live in-memory job, and has no replay contract

- **Issue** The socket handler rejects any run absent from the in-process `JOBS` map (close 4404), then sends `job.progress_event()` only when `progress_version` differs from the last sent value. The client receives the current snapshot and never the intervening ones, and cannot ask for events after a known point; a restarted or history-adopted run cannot be monitored, which the client works around with a four-second poll of the run list.
- **Source / location** `web/server.py:4179-4210` (gate `4185-4188`, loop `4194-4203`); `App.tsx:2842-2864`.
- **Importance** High — without replay there is no honest history and no safe reconnect; the fallback silently degrades to coarse phase text.
- **Recommended change** Specify `subscribe(run_id, from_seq)` on the journal: replay persisted events in order, then tail live, each frame carrying `seq`; serving a run must require only its journal on disk.
- **Tradeoff** Replay-then-tail needs server-side buffering to avoid a gap at hand-off, plus a backpressure policy for slow clients.
- **Unresolved uncertainty** Transport choice (server-sent events versus WebSocket) is left to implementation; only the contract is specified here.

### F3. There is no reconnect or stale-view behavior; a dead stream looks like a quiet run

- **Issue** The socket helper installs only `onmessage` — no `onclose`, `onerror`, backoff, or resubscribe — and the one close handler merely clears a busy flag. A dropped connection leaves the last percentage and phase on screen with no indication that the view is no longer live, which is the "implying progress that has not occurred" failure the main prompt forbids. The in-code claim that the socket "sends 'unknown job' -> our error handler" does not match the server, which closes with 4403/4404 and sends nothing.
- **Source / location** `web/client/src/api.ts:235-246`; `App.tsx:2836`, `:2872-2874`; `web/server.py:4182-4191`.
- **Importance** High — a stale view that looks live is a correctness problem for human review, not a cosmetic one.
- **Recommended change** Define three exclusive freshness labels in the **Progress Projection**: `live` (event or heartbeat within twice the heartbeat interval), `view_stale` (disconnected; show last applied sequence and its age, freeze all motion), `activity_unknown` (subscribed, state `running`, no heartbeat past the stall threshold). No animation runs in the latter two.
- **Tradeoff** Three labels are more vocabulary than a single "connected" dot, which is the ambiguity being removed.
- **Unresolved uncertainty** Stall thresholds must be declared per step type for genuinely long steps such as full-text reading; the values need measurement.

### F4. Heartbeat and completed work are the same signal, by design

- **Issue** The orchestrator emits a progress update per cross-model review explicitly so the watchdog will not kill the run — the comment states the loop "otherwise has NO heartbeat, so the server watchdog would kill the (almost-finished) run mid-review" — and the server accepts either a new `progress_version` or a merely refreshed `at` timestamp as liveness. Liveness is therefore expressed by mutating the record that reports completion, so an alive run is indistinguishable from an advancing one.
- **Source / location** `orchestration/recommend.py:744-747` (comment `745-746`); `web/server.py:409-432` (liveness `417-421`).
- **Importance** High — the main prompt requires activity and completed work to be separated; conflating them makes a stalled run look productive.
- **Recommended change** Split the vocabulary: `agent.heartbeat` and `tool.waiting` carry `last_seen_at`, current question, and elapsed time, and may not contain completion counters; only completion-class events may advance a counter (§3). The watchdog consumes heartbeats; the projection consumes completions.
- **Tradeoff** Two event families enlarge the journal; bound it by keeping heartbeats periodic and retained only in a rolling window while completions persist.
- **Unresolved uncertainty** Whether heartbeats belong in the immutable journal at all — useful for stall diagnosis, inflationary for the permanent record.

### F5. The percentage is non-monotonic, the ETA is extrapolated from it, and a budget is shown as progress

- **Issue** Within one run, `pw.progress` is called with unrelated denominators: `1/4`, `2/4`, `3/4` for goal/parents/propose; `(4+i)/(5+len(plan))` for evaluation; a recomputed `mlip_total`; `(ri+1)/n_review` with `n_review` at least 20; `(li+1)/len(lit_scope)`; then `1/1`. The display therefore reads about 75%, rises to about 90%, drops to about 5% when cross-model review starts, jumps to about 33% for literature, and ends at 100%. The client computes remaining time as `elapsed * (100 - pct) / pct` from that value in both the activity bar and the monitor, and prints `phase {current}/{total}` as if stable. Planned counts are themselves unreliable: the candidate plan may be underfilled against `n_proposals`, which is logged but not reflected in any total. Separately, the loop runs to `cfg.max_rounds` and records `exhausted`, but no UI vocabulary distinguishes "2 of 4 rounds of budget used" from "half done".
- **Source / location** `orchestration/recommend.py:232`, `:319`, `:340`, `:617-619`, `:621-628`, `:670-680`, `:742-747`, `:768-774`, `:831`; `App.tsx:3117-3123`, `:3532-3546`; `dual_agent/loop.py:219-224`, `:277-292`.
- **Importance** High — this is the concrete mechanism behind the gap named in `07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md` §2, and it produces actively misleading numbers rather than imprecise ones.
- **Recommended change** Forbid any cross-stage percentage (§4). Each scope carries `denominator_kind`, `completed`, `planned`; a percentage renders only for `enumerated_fixed`; denominator changes require a `progress.estimate_revised` event surfaced as "plan revised"; budgets render in a separate meter labelled "budget consumed — not completeness", and reaching a cap emits `run.unresolved`.
- **Tradeoff** Users lose the single number they ask for; the honest substitute is three scoped counters plus elapsed time, needing more space and explanation.
- **Unresolved uncertainty** Whether stakeholders will accept no overall percentage, or press for a blended figure that reintroduces the defect.

### F6. The trace API relabels an authoritative non-acceptance as if the proposal were sent onward

- **Issue** The loop records `status = "exhausted"` specifically to avoid admitting a low-promise proposal, and the recommendation stage consumes only `res["accepted"]`, so an exhausted slot never reaches the plan. The trace API maps `exhausted` to the disposition `sent_after_revision_limit`, which the UI prints in its `disposition` column — a label asserting a progression the code does not perform.
- **Source / location** `dual_agent/loop.py:282-292`; `orchestration/recommend.py:596`; `web/server.py:981-989`, `:1018`; `App.tsx:3785-3799`.
- **Importance** High — a status label that overstates acceptance is the exact UI failure the main prompt singles out, and it already exists in the reference.
- **Recommended change** One authoritative state enumeration in the **Run Controller** plus a declared display-mapping table; presentation may rename but never re-semanticise, and `unresolved` renders as unresolved with its unmet question.
- **Tradeoff** A strict mapping table is another artifact to maintain and review.
- **Unresolved uncertainty** Whether any consumer outside the UI table depends on the current string; the search covered this repository only.

### F7. History exists; a semantic diff does not

- **Issue** Versioned proposal and review files are written per round, the UI renders successive proposer/reviewer blocks, and report iterations store `parent_version`. All of it is snapshot display: nothing computes which field changed, from what value to what, or which critique or source caused it, so a reviewer must infer deltas across eleven criteria and 140 candidates by reading two snapshots.
- **Source / location** `dual_agent/loop.py:214-218`, `:232-233`; `App.tsx:1933-1962`; `analysis/report_iteration.py:278-287`; `ReportIterator.tsx:130-178`.
- **Importance** High — "what changed and why" is the primary human-review question and the main prompt requires it to be directly inspectable.
- **Recommended change** Add a diff producer to the **Criterion Registry** and **Leaderboard Service** emitting typed change records (§5.4) with before/after values and `caused_by` links to critique, evidence, and decision.
- **Tradeoff** Typed diffs need stable identities across versions, so merges and splits require explicit lineage edges rather than name matching.
- **Unresolved uncertainty** How to diff free-text rationale; the proposal diffs structured fields and shows rationale as before/after text without claiming a semantic delta.

### F8. There is no human-review queue, no decision record, and no attribution

- **Issue** The sole human input route ingests experimental results with `run_id`, `kind`, values, and `notes` — no actor, role, reason, target artifact, or approval semantics. Nothing lets a user inspect a pending proposal, approve a version, or reject with a reason; there is no pause/resume, only cancel. The review columns the UI does show (`llm_verdict`, `gate_verdict`, `promise_score`, `disposition`) are agent outputs, so the only approval-looking fields in the product are machine verdicts.
- **Source / location** `web/server.py:1585-1593`, `:1596-1622`, `:1154`; `App.tsx:3785-3799`.
- **Importance** High — the human-in-the-loop behavior the original request wanted "throughout" is effectively unimplemented, and the brief's three approval kinds are collapsed to one.
- **Recommended change** Specify the **Human Review Queue** with first-class `human_decision` records (§6) and an `approval_kind` field (`agent_verdict` | `software_status` | `human_scientific_approval`); an approval chip may render only when backed by a `human_scientific_approval` record id, and screens without one must state "no human review yet".
- **Tradeoff** Attributed decisions add identity management and block runs that wait on review; blocking versus non-blocking queue classes bound the cost.
- **Unresolved uncertainty** Whether a local single-user deployment can carry meaningful attribution, or whether an external identity claim must be configured before expert approvals are recordable.

### F9. Staleness, rerun scope, and reuse are not representable

- **Issue** Human results are stored as records but linked to nothing they should invalidate, and no route schedules a scoped rerun. The UI cannot answer which results became stale, which were reused, and which were re-evaluated — three of the questions `07_..._EN.md` lists as mandatory.
- **Source / location** `web/server.py:1596-1622`; `orchestration/run_dir.py:100-143` (event payload carries no dependency edges); no staleness or rerun route in the scan.
- **Importance** High — without it a human edit either leaves wrong results visible or forces a full rerun.
- **Recommended change** Record dependency edges in the journal (evidence claim → per-criterion record → candidate assessment → leaderboard snapshot; criterion version → every record applying it). `staleness.marked` and `rerun.scheduled` carry the affected id set; reuse is permitted only when input hash, criterion version, and evidence-set version are unchanged and no ancestor is stale.
- **Tradeoff** Edge maintenance costs write amplification per assessment; coarser per-criterion granularity is cheaper but reruns more than necessary.
- **Unresolved uncertainty** Whether evidence-level invalidation should cascade automatically when the superseding source is itself contested.
- **Revised after cross-review:** my fingerprint-only reuse rule was insufficient; I adopt WS2 E2's always-recompute classes (rationale, applicability, per-candidate decisions, adjudications, snapshots) layered on top of the fingerprint test.

### F10. Rationales lack evidence navigation, while raw model output is the live default

- **Issue** Reviewer records retain verified refs, rejected refs, an evidence audit, and a calibration note, but the UI renders them as joined text with no link from a claim to its passage or tool result. Meanwhile the monitor's live region is labelled "live model I/O below" and the client polls model-call transcripts every four seconds, making raw responses the default live content — the inverse of the required concise-decisions-and-sources default.
- **Source / location** `dual_agent/reviewer.py:206-230`, `:382-418`; `web/server.py:995-1019`; `App.tsx:1945-1957`, `:2846`, `:3546`.
- **Importance** Medium-high — the data for evidence navigation already exists, so the defect is presentational, but the default-view inversion is a policy problem.
- **Recommended change** Represent every rationale as claim objects (`claim_text`, `evidence_ref`, `support` | `conflict`, `status`) that link into the Evidence Inspector, and move raw traces behind a role-gated, access-logged panel (§7).
- **Tradeoff** Structured claims constrain reviewer output and will sometimes truncate nuance free text carries.
- **Unresolved uncertainty** Whether every claim can bind to a passage; claims resting on absent evidence need an explicit "no source" sentinel rather than a broken link.

## 3. Event and progress interface

**Journal.** One append-only journal per run plus a task-level index of its runs. Events are immutable; a correction is a new event referencing the corrected `seq`. The projection (run state, counters, timeline, queue) is derived and rebuildable.

**Envelope fields**, on every event: `seq` (gap-free integer per run, assigned at write); `event_id`; `event_type`; `emitted_at` and `recorded_at` (UTC, millisecond, so clock skew is detectable); `actor` {`kind`: agent | tool | human | scheduler | system, `id`, `role`: planner | proposer | critic | arbiter | assessor | retriever | controller | expert, `version`}; `ids` {`task_id`, `run_id`, `stage_id`, `step_id`, `round_id`, `exchange_id`, `tool_call_id`, `review_request_id`, `checkpoint_id`}; `parent_seq` (the event this answers or continues); `input_versions` {`criterion_set_version`, `evidence_ledger_version`, `leaderboard_snapshot_id`, `strategy_version`}; `question` (one sentence, the question being answered); `summary` (concise, human-readable, never raw model output); `state_after` (`queued` | `running` | `waiting_tool` | `waiting_human` | `retrying` | `paused` | `failed` | `cancelled` | `completed` | `unresolved`); `progress` {`scope`, `denominator_kind`, `completed`, `planned`, `indeterminate`}; `budget` {`rounds_used`, `rounds_max`, `tool_calls`, `tokens`, `wall_clock_s`, `human_wait_s`}; `artifact_links` (list of {`kind`, `id`, `version`, `uri`}, `kind` in proposal, critique, decision, evidence_claim, criterion_version, candidate_assessment, leaderboard_snapshot, tool_result, trace_blob, report_revision, human_decision); `visibility` (`default` | `expert` | `auditor`); `payload_ref` (pointer; large bodies never inline).

**Event types.** Lifecycle: `run.created`, `run.started`, `run.paused`, `run.resumed`, `run.cancelled`, `run.completed`, `run.unresolved`, `run.failed`; `stage.opened`/`closed`; `step.opened`/`closed`; `round.opened`/`closed`. Actors: `agent.started`, `agent.heartbeat`, `agent.finished`. Tools: `tool.requested`, `tool.result`, `tool.error`, `tool.retry_scheduled`. Protocol: `exchange.proposed`, `exchange.critiqued`, `exchange.arbitrated`, `exchange.resolved`. Substance: `evidence.admitted`, `evidence.conflict_recorded`, `criterion.version_proposed`, `criterion.version_approved`, `candidate.assessed`, `leaderboard.snapshot_published`. Humans: `human.review_requested`, `human.review_decided`, `human.input_submitted`, `trace.opened`. Control: `checkpoint.written`, `staleness.marked`, `rerun.scheduled`, `progress.estimate_revised`.

**Counter rule.** Only `stage.closed`, `step.closed`, `round.closed`, `agent.finished`, `tool.result`, `exchange.resolved`, `candidate.assessed`, and `human.review_decided` may increase a `completed` value. `agent.heartbeat` and `tool.requested` update only `last_seen_at`, `question`, and elapsed time.

**Update mechanism.** The client subscribes with `run_id` and `from_seq`; the server replays persisted events in order, then tails. Every frame carries `seq`; the client keeps `last_applied_seq` and ignores duplicates, so delivery need only be at-least-once. Reconnect resubscribes at `last_applied_seq + 1`. If the requested sequence predates compaction, the server returns a projection snapshot with `snapshot_seq` and resumes there. Serving a run requires only its journal, never a live process (contrast `web/server.py:4185-4188`).

**Mapping to persisted records.** `candidate.assessed` → per-criterion record set; `criterion.version_approved` → Criterion Registry version; `leaderboard.snapshot_published` → immutable snapshot bound to objective, rule/strategy version, evidence cutoff, ordering method; `evidence.admitted` → Evidence Ledger entry; `human.review_decided` → `human_decision` record; `checkpoint.written` → resumable checkpoint; `tool.result`/`tool.error` → tool-result store plus a `trace_blob`.

## 4. Progress semantics at three levels

| Scope | Denominator | Shown as | Indeterminate when |
|---|---|---|---|
| Overall run | stages declared by the Planner, revised only via `progress.estimate_revised` | "stages 3 / 7 completed · plan revised 2x"; never a blended percent | continuation is trigger-driven, so later stages are not enumerable |
| Stage / workstream | units enumerable at stage open (candidates, criteria, queued sources) | "118 / 140 assessed", percent only when `enumerated_fixed` | retrieval stages whose count can grow: "completed 37 · planned ≥ 40" |
| Current round | named steps in the round's completion criteria | "steps 4 / 6 declared" | steps added adaptively mid-round |

`denominator_kind` values: `enumerated_fixed`, `enumerated_growing`, `budget_bounded`, `unbounded_adaptive`, `unknown`. A percentage is permitted only for `enumerated_fixed`, only inside one scope, and never by mixing scopes — the defect at `recommend.py:232`–`:831`. A `budget_bounded` quantity renders only in the budget meter, because reaching a round cap yields `unresolved`, not completion; the maximum-round count is a spend limit and carries no information about scientific coverage, since one round may resolve the decisive conflict and four may resolve nothing. The honest indeterminate indicator shows state, current question, elapsed time, and last-activity age, with no number and no ETA. An ETA appears only when the denominator is `enumerated_fixed`, a configured minimum of units has completed, and the display names its basis ("extrapolated from 12 of 40 assessments") — conditions the reference's `elapsed * (100 - pct) / pct` cannot meet.

## 5. Screens (non-executable wireframes)

### 5.1 Task input

```
+-- new investigation ---------------------------------+
| objective* [prioritise approved drugs engaging      ]|
|            [CSF1R+VEGFR1/2/3+FGFR1 for TME/TLS      ]|
| mode  (o) conditional   ( ) exploratory              |
|       conditional = you fix universe + constraints   |
|       exploratory = planner proposes scope, you OK it|
| universe   [library_fda_ph3.csv (3,171)][+add id]    |
| properties [oral bioavail.][metab. stability][tox]   |
| constraint [evidence cutoff 2025-12-31][+add]        |
| reference  [historical_CQA_list.json] comparison only|
| evidence   [upload][local path][paste text]          |
+-- needs input before the task is meaningful ---------+
| (!) ordering unstated: [hard-rule funnel][scored]    |
| (!) 2 of 5 targets lack an assay endpoint  [define]  |
| (i) no CDES adapter: predicted -> 'unavailable'      |
| budget: rounds max[4] tool calls[200] clock[2h]      |
|   (caps work, not a completion target)               |
|        [save draft] [plan only] [start run]          |
+------------------------------------------------------+
```

Components: objective field; mode selector with inline explanation; universe picker with single-compound add; property and constraint chips; reference-artifact slot; evidence intake by upload, path, or text; blocking-gap panel generated by the Task Context Normalizer; budget block; actions. States: `draft`, `incomplete_blocking` (start disabled, each gap naming the missing decision), `incomplete_advisory` (start enabled), `ready`, `planning`, `submitted`. Advisory notices never block; only questions that make the task meaningless do.

### 5.2 Live run monitor

```
+-- run r-1012-003  RUNNING ------- live (2s ago) -----+
| task t-ovca-01 | plan v3 (rev 2x) | rules v7 | cutoff|
| OVERALL stages 3/7 planned   [###----] plan revised  |
| STAGE   assessment 118/140 enumerated [#####-]       |
| ROUND   round 2 | steps 4/6 declared                 |
| BUDGET  exchange 2 of max 4 | 41m of 2h (not done-ness)
| ELAPSED 00:41:18 | last activity 2s ago              |
+-- now running ---------------------------------------+
| actor        owns          question          state   |
| assessor-3   surufatinib   metab. stability? RUNNING |
| tool:chembl  query 118     CYP3A4 substrate? WAIT_TOOL
| critic-1     crit c-009    threshold ok?     RUNNING |
| expert       crit v8       approve unit fix? WAIT_HUMAN
+-- waiting / problems --------------------------------+
| RETRYING tool:pubmed 2/3 (429) next 18s              |
| FAILED   tool:gdsc no alias -> recorded as missing   |
|  [pause][stop][timeline][review queue (1)]           |
+------------------------------------------------------+
```

Components: run header with freshness badge; three scoped progress rows; a separate budget meter; elapsed and last-activity pair; now-running table of actor, owned object, question, state; waiting/problems list; controls. States: view freshness `live` | `view_stale` | `activity_unknown`, plus the ten execution states per row. `waiting_human` rows link to the queue; an indeterminate scope renders a label and elapsed time with no bar; `view_stale` freezes all motion and shows the last applied sequence and its age.

### 5.3 Round timeline

```
+-- timeline t-ovca-01 --------------------------------+
| show [x]rounds [x]steps [ ]retries [x]human edits    |
|      [x]refresh runs [ ]heartbeats                   |
| seq when     kind          actor     outcome   link  |
|   1 10:02:11 run.started   scheduler running   plan1 |
|   7 10:04:50 round1 opened planner   -         rules5|
|  12 10:09:02 criterion prop proposer1 proposed  v5>v6|
|  14 10:09:40 critique      critic1   revise    2 pts |
|  19 10:12:03 tool.error    pubmed    retry 1/3 error |
|  23 10:15:22 decision      arbiter   completed rules6|
|  31 10:22:40 round1 closed controller snapshot L-3   |
|  33 10:23:05 human edit    j.doe     unit fixed rules7
|      -> 44 stale | 12 reusable | 32 to rerun         |
|  34 10:23:06 rerun sched.  controller queued   32    |
|  51 11:05:19 round2 opened planner   trigger   e-221 |
|  62 11:41:18 assessment    assessor3 running   (now) |
| single-pass runs show as one round with its steps    |
|  [open 31][compare v6>v7][export journal]            |
+------------------------------------------------------+
```

Components: kind filters; sequence-ordered rows; nested consequence lines; per-row artifact links; compare and export. Row states: `completed`, `unresolved`, `failed`, `cancelled`, `superseded_by` (correction link), `current`. Retries nest under their tool call and never create a round row; human edits, report revisions, and evidence-refresh runs carry distinct kind labels so none is read as a screening round.

### 5.4 Version-difference view

```
+-- difference rules v6 -> v7 -------------------------+
| cause human edit by j.doe (expert) 10:23:05          |
| reason "source reports mg/kg, not mg" | ev e-118     |
| approval HUMAN SCIENTIFIC (j.doe, d-19)              |
+-- criteria ------------------------------------------+
| ADDED    c-012 CYP3A4 TDI | preference | e-204 e-209 |
| MODIFIED c-003 thresh >=20% -> >=30% | e-118 | q-77  |
|          applicability all -> oral dosing only       |
| MODIFIED c-007 units mg -> mg/kg (human correction)  |
| MERGED   c-004 + c-005 -> c-013 hepatic safety       |
| SPLIT    c-008 -> c-014 hERG + c-015 DILI            |
| REMOVED  c-011 no source supported the threshold     |
+-- leaderboard L-3 -> L-4 ----------------------------+
| ADMITTED surufatinib unassessed -> recommended c-007 |
| DEMOTED  cmpd-A recommended -> provisional c-003 unk |
| EXCLUDED cmpd-B provisional -> rejected c-012 e-204  |
| UNRANKED cmpd-C metabolic data missing (not a fail)  |
| RANK     cmpd-D #4 -> #6 | 0.71 -> 0.58 | c-003      |
| each row: [evidence][decision][critique][rerun]      |
+------------------------------------------------------+
```

Components: cause header naming actor, reason, and approval kind; criterion change list with before/after values; candidate and ranking change list; per-row links. Change types: criteria `added`, `modified`, `merged`, `split`, `removed`; candidates `admitted`, `excluded`, `demoted`, `promoted`, `unranked`, `rank_changed`, `status_changed`, `score_changed`. Each row is `evidence_linked` or `unexplained`; an unexplained material change renders as a defect rather than being hidden.

### 5.5 Candidate detail

```
+-- surufatinib (CHEMBL..., InChIKey ...) -------------+
| task t-ovca-01 | L-4 | RECOMMENDED | rules v7        |
| position #1 of 140 assessed | hard-rule funnel       |
| reason: only candidate with no FAIL across 11 hard   |
|   criteria; 1 unknown, 1 inapplicable, 0 open fails  |
| review HUMAN APPROVED j.doe 10:31 (d-19)             |
| agent verdicts proposer favourable | critic no objn. |
|   (an agent verdict is not approval)                 |
| provenance 2 independent sources | 1 shared-author   |
+-- per-criterion -------------------------------------+
| crit  value    kind      result  reason     ev  rev  |
| c-001 34%      measured  PASS    >=30%     e118 ok   |
| c-003 12uL/min measured  PASS    mg/kg     e118 human|
| c-007 none     missing   UNKNOWN no assay   -   open |
| c-012 6.1uM    predicted PASS    model m3  e204 ok   |
|   counter-evidence e-233 1.8uM -> CONFLICT open      |
| c-013 n/a      inapplic. N/A     no oral    -   n/a  |
| completeness 9/11 with evidence | 7 reused, 4 new    |
| [evidence][history][exclude w/ reason][request rerun]|
+------------------------------------------------------+
```

Components: identity block; status, position, and the reason for that position; approval block keeping human decisions visually separate from agent verdicts; per-criterion table of value, value kind, result, reason, evidence, review state; completeness and reuse summary; actions. States: candidate `recommended` | `provisional` | `unassessed` | `rejected`; result `pass` | `fail` | `unknown` | `inapplicable`; value kind `measured` | `predicted` | `missing`; review `none` | `requested` | `human_approved` | `human_rejected` | `disputed`; each record tagged `reused` (with its checkpoint) or `re_evaluated`.

### 5.6 Evidence inspector

```
+-- evidence e-118 ------------------------------------+
| peer-reviewed paper | DOI 10.xxxx/yyyy | got 10:08   |
| status ADMITTED (ledger v12) | independence group-A  |
| used by c-003, c-007 | 44 assessments | L-4          |
+-- exact passage -------------------------------------+
| p.7 Table 2 "oral bioavailability 34% (rat, 5 mg/kg)"|
| [open source][page image][extraction: table parse]   |
+-- support / conflict --------------------------------+
| SUPPORTS  c-003 PASS | asserted assessor-3, ref ok   |
| CONFLICTS e-233 1.8uM vs e-204 6.1uM -> OPEN         |
|           [assign to expert][request measurement]    |
| REJECTED refs kept: e-901 not in retrieved set       |
| note: the identifier check passed; this does not     |
|   establish that the scientific claim is correct     |
| [dispute][submit better source][raw trace*]          |
|  *expert/auditor only; logged as trace.opened        |
+------------------------------------------------------+
```

Components: source header with evidence kind and independence marker; exact passage with extraction method; support and conflict list; retained rejected references; standing caution line; actions. States: evidence `admitted` | `provisional` | `rejected` | `superseded` | `disputed`; relation `supports` | `conflicts` | `independent_confirmation`; conflict `open` | `expert_assigned` | `resolved`.

### 5.7 Human-review queue

```
+-- review queue t-ovca-01 -- 3 open | 1 blocking -----+
| pri  age what                   why expert   state   |
| HIGH 4m  criterion v8 unit fix  threshold    BLOCKING|
|          requested by critic-1 | run paused r2s4     |
| MED  22m admit cmpd-E           identity     OPEN    |
| MED  31m conflict e-233/e-204   judgement    OPEN    |
| LOW  2h  report revision r-4    optional     OPEN    |
+-- inspect criterion v8 (pending) --------------------+
| proposal raise c-003 20% -> 30% (proposer-1)         |
| critique "source is rat, not human" (critic-1)       |
| evidence e-118 adm. | e-204 adm. | e-901 rejected    |
| if approved: 44 stale | 32 rerun | 12 reusable       |
| decision ( )approve ( )approve with edit ( )reject   |
| reason* [                                          ] |
| j.doe (expert) -> creates human_decision d-19        |
|              [submit][defer][reassign]               |
+------------------------------------------------------+
```

Components: prioritised queue with age, blocking indicator, and the reason expert judgement is required; inspection pane showing proposal, critique, evidence, and the pre-computed staleness consequence; decision control with a mandatory reason; attribution line naming the record that will be created. States: item `open`, `in_review`, `decided`, `deferred`, `expired`, `withdrawn`, each blocking or non-blocking; decision `approved`, `approved_with_edit`, `rejected`, `escalated`.

## 6. Human interventions

Each action creates an immutable `human_decision` record: `decision_id`, `actor` (identity, role, affiliation claim), `action`, `target` (artifact id and version), `reason` (mandatory), `decided_at`, `approval_kind`, `resulting_version`, `stale_set`, `rerun_set`, `reuse_set`, `journal_seq`. Prior versions are never overwritten; corrections supersede by reference.

| Action | Creates | Versioning | Stale | Rerun | Reuse | Expert |
|---|---|---|---|---|---|---|
| Inspect pending proposal | view / `trace.opened` | none | none | none | all | no |
| Edit proposal | `approved_with_edit` | new proposal version, parent linked | records citing it | the open exchange | earlier rounds | yes |
| Reject with reason | `rejected` | proposal closed, not deleted | none | none; round may close `unresolved` | all | yes |
| Approve rule version | `approved` + `human_scientific_approval` | registry version promoted | records on the prior version | assessments whose criteria changed | assessments on unchanged criteria | yes |
| Add compound | `human.input_submitted` | universe version | leaderboard snapshot | that compound only | all others | no; identity check automatic |
| Exclude compound | decision + status `rejected` | leaderboard snapshot | that candidate's rank context | ranking | its per-criterion records | yes if evidence-based, no if scope-based |
| Correct units / thresholds / applicability | decision + criterion version | registry version | every record using it | affected assessments and ranking | records where it is inapplicable | yes |
| Correct an interpretation | decision + claim revision | ledger version | assessments citing the claim | those assessments | others | yes |
| Submit references or results | `human.input_submitted`, `provisional` | ledger version on admission | none until admitted | none automatically | all | yes to admit; intake automatic |
| Request targeted follow-up | `rerun.scheduled` with scope | new round or refresh run | none | the named scope only | everything outside it | no |
| Pause / resume / stop | `run.paused` / `resumed` / `cancelled` | checkpoint id | none | in-flight step on resume | completed steps | no |

Submission is not acceptance: supplied references and results enter as `provisional` with `submitted_by`, and only an admission decision makes them usable. A resumed run carries `resumed_from_run_id`, `resumed_from_checkpoint_id`, and a `reuse_manifest` naming each reused record with its input hash and why reuse was legal; candidate detail shows `reused` or `re_evaluated` per record. Automatic actions are limited to intake, identity resolution, scope-based exclusion, rerun scheduling, and run control; every change to scientific meaning — thresholds, units, applicability, interpretation, evidence admission, rule promotion — requires an expert decision. Absent one, the UI states "no human review yet", and an agent verdict never renders in the approval slot.

## 7. Default view and raw traces

The default surface shows per decision: question, actor, outcome, one-sentence reasoning, linked claims with evidence status, and execution state — never raw model output, which the reference makes the live default (`App.tsx:2846`, `:3546`). Raw traces persist in a separate store behind `trace_blob` links with `visibility: expert | auditor`, opened only by an explicit action that journals `trace.opened` with its actor. A decision record is invalid without at least one evidence link or an explicit "no evidence available" reason; that rule is what makes the default view sufficient alone.

## 8. Agentic Doping: reuse, and gaps to add

| Reuse | Add |
|---|---|
| Activity bar plus detailed monitor (`App.tsx:3111-3125`, `:3524-3546`) | Three scoped progress rows, separate budget meter (F5) |
| Snapshot/journal split (`run_dir.py:104-143`) | Journal authoritative and replayable by sequence (F1, F2) |
| Internal log kept out of the progress channel (`run_dir.py:123-126`) | Same discipline for raw traces, role-gated (§7) |
| Per-round proposer/reviewer blocks, per-version files (`App.tsx:1933-1962`; `loop.py:201-247`) | Typed field-level diffs with `caused_by` links (F7) |
| Report lineage via `parent_version` (`report_iteration.py:270-290`; `ReportIterator.tsx:130-178`) | Keep revisions distinct from rounds and rule versions |
| Separated review dimensions (`App.tsx:3785-3799`; `server.py:995-1019`) | The missing dimension: attributed human approval (F8) |
| Citation checks retaining rejected refs (`reviewer.py:206-230`, `:382-418`) | Claim-to-passage navigation and the caution that an identifier check is not validation (F10) |
| Run history, restore, polling fallback (`App.tsx:2490-2508`, `:2797-2805`, `:2842-2884`) | Activity events, reconnect with stale labels, resuming distinguished from reopening (F3, F4) |

## Cross-review of mas_architecture.md

### Agreements

- C1's journal-as-single-source-of-truth with a store-assigned monotonic `seq` is my F1/F2, and its counter-initialised-to-zero citation (`run_dir.py:96-121`) is the mechanism behind my "no replay" finding.
- H2's `unresolved_budget_exhausted` with `implies_admission = false` is stronger than my F6, which asked only for a mapping table; I accept the stronger form.
- H1's redesign verdict on the human verification gate (`harness.py:84-92`, approval true by default, `require_verification: bool = False`) upgrades my F8 from "no approval route" to "a default-pass approval gate exists".
- E2's fingerprints, dependency graph and Rerun Plan are the same mechanism as my F9 staleness edges; D2's no-dropped-candidate rule is what my `UNRANKED` diff row renders.
- I1's relocation of the Event Journal to the foundation is the structural form of my "UI is a projection" claim, and A2's derived `independence_level` should render in candidate detail (§5.5) beside provenance.

### Objections

**O1 — C1 says heartbeat/work separation is "a separation the reference already observes".** It is observed in one helper and violated in the hot path: `recommend.py:744-747` emits a work-progress event explicitly to satisfy the watchdog ("this slow per-candidate LLM loop otherwise has NO heartbeat"), and `web/server.py:417-421` accepts a merely refreshed `at` on that record as liveness, bypassing the helper WS2 cites (`run_dir.py:195-217`). Alternative: my counter rule as a contract — the watchdog subscribes only to `heartbeat`, liveness-motivated progress events are a violation, and a conformance test asserts no completion-class event carries an unchanged `completed` value.

**O2 — C1 collapses human activity into one `human_action` kind.** Open review items are requested-minus-decided, so one kind makes the queue unprojectable and trace access unauditable. Alternative: `human_review_requested`, `human_review_decided`, `human_input_submitted`, `trace_opened`.

**O3 — C1 has no denominator-change event.** With `step_progressed` alone, a changed planned count is indistinguishable from progress — my F5 defect (`recommend.py:232`, `:623`, `:677`, `:742`, `:773`). Alternative: `progress_estimate_revised` carrying before/after `planned` and `denominator_kind`, surfaced as "plan revised".

**O4 — E2 over-reaches on reuse yet leaves approval open.** I accept its always-recompute classes (rationale, applicability, per-candidate decisions, adjudications, snapshots) and now treat my fingerprint-only rule as insufficient. The open approval question is mine: rerun plans auto-approve when every item is `required` and within the step budget, else they queue as a non-blocking item showing stale/rerun/reusable counts.

### Interface conflicts and resolutions

**Event envelope versus A3 Artifact Envelope.** Both carry `seq`; it must exist once. Merged event fields: `seq` (journal-assigned, gap-free per run), `event_id`, `event_type`, `emitted_at`, `recorded_at`, `actor` {kind, id, role, model_family?, policy_version?}, `ids` {task, run, stage, step, round, exchange, tool_call, review_request, checkpoint}, `parent_seq`, `input_versions` {criterion_set, evidence_ledger, leaderboard_snapshot, strategy, adapter, run_binding}, `question`, `summary`, `state_after`, `termination_reason?`, `progress` {scope, denominator_kind, completed, planned, indeterminate}, `budget`, `artifact_links[]` {artifact_kind, artifact_id, schema_version, version, payload_sha256}, `visibility`, `payload_ref`. Artifacts keep `artifact_id`, `artifact_kind`, `schema_version`, `parent_artifact_id?`, `supersedes?`, `created_at`, `state`, `evidence_refs[]`, `payload`, `payload_sha256`, `adapter_extensions`, and replace A3's `seq` with `journal_seq`.

**Counter rule and freshness labels versus H2's State Registry.** None of my non-execution labels are in H2 today. Resolution: add `label_domain` to the registry (execution, candidate, criterion_result, value_provenance, evidence, review, change_kind, view_freshness, denominator_kind) and require registration in every domain, marking `view_freshness` client-derived and never persisted as run state — so `live` / `view_stale` / `activity_unknown` are registered labels but not run states, while the result, value-kind, review and change-kind vocabularies gain `ui_label` and `ui_tone`.

**`human_decision` versus A2's Human decision payload.** Merged: `decision_id`, `queue_item_id`, `person_id`, `actor` {role, qualification, affiliation_claim}, `action` (union: approve, approve_with_edit, reject, edit, add_candidate, exclude_candidate, correct_value, correct_interpretation, submit_evidence, request_followup, defer, pause, resume, stop), `scope`, `target` {artifact_kind, id, version}, `reason` (mandatory), `attested_at`, `decided_at`, `approval_kind` (`agent_verdict` | `software_status` | `human_scientific_approval`, and only this record may carry the third), `resulting_version`, `affected_refs` split into `stale_set` / `rerun_set` / `reuse_set`, `independence_declaration_ref`, `journal_seq`, record state (`recorded` | `superseded`).

**`waiting_human` ownership (I1).** Accepted: the queue owns the item and attestation, the Run Controller holds a derived `blocked_on_review[]`, a run with an open blocking item cannot project `running`, and my monitor renders the join.

**Ordering method.** I1 moves ownership to the Criterion Registry; the snapshot must still record `ordering_method` and `rule_version`, or candidate detail cannot say why a compound ranks first.

### Dependencies

From WS2: the Plan record (B1), my only honest overall-run denominator; the Open-Question Register (C3) behind my question column and the queue's expert-need reasons; the State Registry with `label_domain`; the Artifact Contract Registry for link kinds; the Budget Accountant for meter fields; A2 for candidate detail. To WS2: rerun-approval policy, label inventory, freshness semantics, raw-trace visibility.

### Resolution summary

| Topic | My position | WS2 position | Proposed resolution | Confidence |
|---|---|---|---|---|
| Heartbeat separation | Violated in the hot path (F4) | Already observed | Counter rule as contract plus conformance test | High |
| Event kinds | Fine-grained | Coarser, `human_action` | Merged list; split human and trace kinds | High |
| Denominator changes | Explicit revision event (F5) | Not represented | Add `progress_estimate_revised` | High |
| `seq` ownership | On the journal event | On the artifact (A3) | One `seq` on events; artifacts carry `journal_seq` | High |
| Reuse rule | Fingerprint-based (F9) | Class-based recompute | Both; class rule layered on fingerprints | Medium-high |
| Rerun approval | Auto below threshold | Open "UI decision" | Auto when all items required and in budget | Medium |
| Label governance | Many label domains | Execution/candidate states | Registry plus `label_domain`; freshness non-authoritative | Medium-high |
| `waiting_human` | Run-state driven | Queue-owned (I1) | Queue-owned, derived run projection | High |

## Contribution record

- **Agent identity**: Workstream 4, Human-Review and UI Auditor — a Claude Code subagent on model Fable 5.1 (`claude-fable-5-1`), invoked by the coordinating agent.
- **Start / end (UTC)**: main report 2026-10-12T13:06:17Z to 13:38Z; cross-review wave 2026-10-12T17:14:10Z to 17:34Z (same session, resumed after a usage-limit interruption).
- **Package files read**: `design_audit/agent_reports/00_coordinator_brief.md` (full); `START_HERE_Audit_and_Optimize_Prompt_EN.md` lines 60-104 (section 4 and 4.1-4.3) plus full heading outline; `Project_Brief_EN.md` lines 50-82 (sections 4-5) plus outline; `06_Agentic_Doping_Original_Prompt_English_Translation.md` (full, 47 lines); `07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md` (full, 36 lines); `agentic_doping_reference/PROGRESS_SOURCE_MANIFEST.json` (full).
- **Repository inspected read-only, nothing modified**: `/home/yiwei3_duke/anny/reference_repos/Agentic-Doping-snapshot`, commit `0007ad104755aec56cbc2479db6cf68c0e05b237`. Under `src/agentic_doping/`: `web/client/src/App.tsx` 1933-1962, 2490-2508, 2797-2805, 2842-2884, 3111-3125, 3524-3546, 3785-3799 plus socket-handler and clarification greps; `web/client/src/api.ts` 235-253; `web/client/src/ReportIterator.tsx` 130-178; `orchestration/run_dir.py` 100-150 plus a grep for event-file consumers; `orchestration/recommend.py` 610-635, 660-690, 740-780 and every `pw.progress` site (232, 319, 340, 626, 679, 747, 773, 831) plus `exhausted`/`accepted` greps; `web/server.py` 400-435, 965-1025, 1154, 1585-1640, 4179-4212 and a scan of all 115 route decorators; `dual_agent/loop.py` 200-250, 275-305; `dual_agent/reviewer.py` 206-230, 382-418; `analysis/report_iteration.py` 265-295.
- **Hash verification**: seven of eight manifest files match their SHA-256; `web/server.py` is `54f7fe4a…` on disk against the manifest's `ff70ed4a…`, so its lines were located by search and confirmed by reading. The trace-API ranges still align; the socket handler is at 4179-4210, not the manifest's 4190-4208.
- **Tools used**: Bash (`cat`, `sed`, `awk`, `grep`, `wc`, `sha256sum`, `git rev-parse`, `date`) and Read. No repository code was executed, no server started, no browser used; nothing was written outside this report and the scratch files under `scratchpad/ws4/`.
- **Cross-review wave**: read `design_audit/agent_reports/mas_architecture.md` (Workstream 2) in full, 365 lines, and appended the `## Cross-review of mas_architecture.md` section above. The peer file was not modified. No new code inspection was performed for the cross-review; every repository citation in that section is from my own earlier reading, except `harness.py:84-92`, `harness.py:62-74` and `run_dir.py:195-217`, which I take from WS2 on its authority and did not re-verify. My earlier findings are unchanged apart from one `Revised after cross-review:` note on F9. Finding ids referenced are my on-disk F1-F10.
- **Not accessed**: the Agentic Doping UI at runtime, so all UI behavior reported here is read from source and not runtime-verified; the `main`-branch clone and the DeepSeek Harness, ARIS, and DGM repositories (other workstreams); the five original Windows-path projects, absent from this host; the manuscript PDF and its extract, `04_Source_Inventory_EN.md`, and `agentic_doping_reference/excerpts/*.py.txt` — case facts and excerpt patterns were taken as established in the coordinator brief §6 rather than re-derived. No web searches were run.
