# Reference-Harness Inspection (Workstream 7)

Read-only inspection, 12 October 2026, of clones under `/home/yiwei3_duke/anny/reference_repos/`. Nothing was built, installed, or run; every statement comes from `cat`, `grep`, `find`, `git log`, and `git diff`. Line numbers refer to the commit named in each section. "Tested" means a test file exercising the mechanism exists at that commit, not that I executed it.

## Summary

1. Agentic Doping at `0007ad10` has a real, tested, recorded progress mechanism, but its durable journal carries only two event types (`progress`, `complete`); heartbeats mutate `progress.json` without being journaled, the denominator changes five times inside one recorded run, and that run emits three `complete` events. The journal is a progress log, not an event history.
2. Note 07's state-label defect is real and untested: `dual_agent/loop.py` records `exhausted` and refuses admission, while `web/server.py` maps it to `sent_after_revision_limit`; the only trace test covers `completed`.
3. The loop's "reviewer independence" claim is contradicted by its code: the reviewer receives the shared dialogue including the proposer's rationale (`loop.py` 230, `proposer.py` 121-145). ARIS's file-paths-only rule and DGM's benchmark evaluator are the clean counter-patterns.
4. The Codex bridge agent loop dispatches a returned call list once and never sends results back to the model, and the committed sample runs used that provider. Provider-agnostic tool feedback does not exist in this codebase; deepseek-harness's durable `tool/call` / `tool/result` pair with synthetic results for unanswered calls is the pattern to copy.
5. Memory guardrails improved between `main` and the snapshot (reviewer concerns no longer become lessons; `skill_policy.py` and `reflection.py` are new), but a legacy path (`_maybe_promote_skill`) still manufactures `avoid-<element>` skills from rejection counts.
6. No inspected repository has a held-out, fixed-snapshot promotion harness. DGM selects and reports on the same subsets and keeps every compiled child by default; ARIS cites one AI-reviewer score trajectory and disclaims it as evidence.
7. Most important change: make the Event Journal (component 11) the only source of truth for execution states, with a closed vocabulary written solely by the Run Controller, and derive every UI label, progress figure, and disposition from it by pure projection. No presentation layer may remap an authoritative state.

## 1. Verification status

All 11 excerpt source files and all 8 progress-manifest files were re-hashed; 16 of 17 match. `web/server.py` differs (`54f7fe4a…` here, `ff70ed4a…` packaged), as the coordinator stated. Note 07's `server.py` references shift slightly: the WebSocket handler is at 4179-4208 here; the disposition mapping (980-989) and trace route (959) are where cited.

## 2. Agentic Doping, snapshot `0007ad10` (tip of `cloud_deployment`, 2026-08-12)

### 2.1 Progress and event mechanism

| Observation | Location | Status |
|---|---|---|
| `ProgressWriter.progress()` writes `progress.json` atomically and appends a `progress` event with `run_id, status, phase, current, total, percent, message, progress_version, at`; `finish()` forces `current=1, total=1`, `percent` 100 or 0, appends `complete` | `orchestration/run_dir.py` 91-143 | implemented; tested (`tests/test_core.py` 16-32, `tests/web/test_server.py` 103-114) |
| `force_finish()` writes a terminal record from the server, tagged `finalized_by: server`, appending another `complete`; `heartbeat()` refreshes `at`/`message` without bumping the version or appending any event | `run_dir.py` 168-217 | implemented; tested (`tests/test_i15_features.py` 10-28); heartbeats are invisible in the journal |
| Three state vocabularies: disk `done, error, stopped, cancelled`; server `JobStatus` `queued, running, done, error, cancelling, cancelled`; history view computes `stale` after 900 s. None has `waiting_tool`, `waiting_human`, `retrying`, `paused`, `unresolved` | `run_dir.py` 200; `core/task_state.py` 18-24; `web/server.py` `_effective_status` | implemented |
| Watchdog kills after 3600 s total or 600 s without progress/heartbeat, then `force_finish("error")`; startup reaper finalizes orphaned runs | `web/server.py` 403-446, 1255-1283 | implemented |
| WebSocket polls in-memory `JobState` every 0.25 s and sends only `progress`/`complete`; versions can be skipped | `server.py` 4179-4208; `task_state.py` 115-117 | implemented; tested for no log leakage and owner-only access (`web/test_server.py` 572-589, `web/test_job_ownership.py`) |
| Client restores the active job from `localStorage`, reconnects, and polls `llm_calls` plus the run list every 4 s because "a slow provider call fires no progress event"; ETA is `elapsed × (100 − pct) / pct` | `web/client/src/App.tsx` 2839-2884, 3108-3125, 3524-3546 | implemented; no client tests |
| Denominators: `x/4` for goal/parents/propose, `5 + len(plan)` for evaluate, `4 + len(plan) + len(shortlist) + 1` for MLIP, `n_review`, `len(lit_scope)`, `1/1` for memory | `orchestration/recommend.py` 232-340, 624-680, 747, 773, 831 | implemented; confirms note 07 gap 2 |
| Recorded run `rec_43273c9978`: 105 events (102 `progress`, 3 `complete`); `(phase, total)` pairs `(goal,4) (parents,4) (propose,4) (evaluate,35) (literature,3) (mlip,65) (done,1)`; `llm_provider: codex_subagent`; `agent_max_rounds: 4`; `continue_run` equals its own id | `runs/rec_43273c9978/{job_events.jsonl, progress.json, manifest.json}` | recorded run |

Logs and model transcripts are deliberately kept out of the progress channel (`task_state.py` 1-9; `tests/test_pipeline.py` 59-66), so "what is happening now" depends on polling `llm_calls.jsonl`, which is note 07 gap 1 in practice.

### 2.2 Proposal/review versioning and authoritative outcomes

`dual_agent/loop.py` 201-307 runs one slot at a time: per round it writes `PROPOSAL_v{n}.json` plus `_latest`, runs the Type-A self-check, writes `REVIEW_v{n}.json`, and ends the slot in exactly one of `completed`, `killed`, `exhausted` (260-292), persisting `REVIEW_STATE.json` with a per-round `history` (294-297) and `KILL_ARGUMENT.json` on rejection (271-274). The comment at 282-284 states the policy: "Treating exhausted as accepted made the reviewer gate cosmetic." `tests/test_dual_agent_harness.py` 240-252 asserts a withheld verification gate yields no `completed` slot. `known_failures.json` gives within-run anti-repetition memory (37-52), which note 07 omits.

The reviewer (`dual_agent/reviewer.py`) now audits evidence: `_verify_evidence` (206-262) rejects citations outside the injected catalog with stable reason codes and only ever downgrades the evidence basis; `normalize_llm_review` (312-422) caps a reported promise of 0.80 or more at 0.79 when verified sources do not support it and records a calibration note. The trace API (`server.py` 959-1019) exposes `llm_verdict`, `gate_verdict`, `promise_score`, `evidence_*`, `raw_*`, `rejected_evidence_refs`, `evidence_audit`, `hard_failure`, `disposition`; `tests/web/test_server.py` 33-90 checks a `completed` slot only, so the `exhausted` mapping is untested.

Independence: the module docstring (7-9) says the reviewer "never sees the proposer rationale or prior reviews", yet line 230 passes `dialogue=dialogue`, and `render_dialogue(viewer="reviewer")` (`dual_agent/proposer.py` 121-145) renders each proposer turn as `PROPOSER proposed <dopants> — "<rationale[:240]>"`. `agent_harness.py` 654-657 documents this openly, while its reviewer system prompt (722) says "You review ONE doping proposal independently. You are given ONLY the ...". Shared-transcript review is the implemented behavior; blind review is a documentation claim.

### 2.3 Scoped memory and skill guardrails

`harness/memory.py`: `_recallable` (207-218) admits approved/verified rows everywhere and provisional rows only inside the same group and scope; `add_lesson`/`add_skill` set `review_state` to `approved` for human source, `verified` for evidence kinds `deterministic_rule, E2, DFT, wetlab`, else `provisional` (262-265, 380-382); `record_outcome` returns an empty dict for `dual_agent` (299-307), and the per-round `record_rejection` that existed on `main` was removed. Tests: `test_memory_scopes.py` (10), `test_memory_trust_flow.py` (5), `test_reviewer_evidence_boundaries.py` (8). Residual: `_maybe_promote_skill` (422-458) still creates `avoid-<element>-<site>` skills once rejection lessons for a single-element family reach a threshold, or at once when lesson text contains a non-viability word; it is reachable through any `add_lesson` call and is untested. `harness/skill_policy.py` (new, 213 lines) rejects model-authored skills with codes `candidate_identifier`, `specific_material_or_dopant_set`, `candidate_specific_parameters`, `observed_score_or_threshold`, `observed_performance_value`, `performance_conclusion`, `literature_or_experiment_conclusion`, `prompt_injection_language`, `not_reusable_methodology` (164-206). It is a regex content filter, not an evaluation.

### 2.4 Reflection

`orchestration/reflection.py` (new) runs after ranking, gives the reviewer model only counts and reason codes (24-114), asks for `save_skill` or `skip`, validates with `skill_policy`, and saves at most one `provisional` skill (158-264); `recommend.py` 827-847 writes the decision to `memory_reflection.json`. Five tests (`tests/test_post_run_reflection.py`). Nothing measures whether a saved skill helps a later run.

### 2.5 Evidence ledger and leaderboard

`evidence_ledger/models.py` `LedgerRecord`: `candidate_id, status, evidence_level E0-E4, scores (decomposed), artifacts, failure_reason (typed), provenance [kind, ref, at], human_review_state (untyped dict), next_action, updated_at`, with `extra="forbid"`. `ledger.py` 22-51 is append-only JSONL, current = latest `updated_at`. `leaderboard.py` 81-90 sorts failed last, then evidence tier, `goal_score`, ratio error; `leaderboard_all` (220-233) aggregates across run directories. It is a read-only projection with no snapshot id, rule-version binding, or rank-change explanation. JSON schemas exist and are tested (`tests/test_schemas.py`).

### 2.6 Tool loop and the Codex bridge

`core/llm_client.py` `run_agent_loop` (413-488) loops on Anthropic `tool_use`, dispatching and appending `tool_result` blocks. For `codex_subagent` it calls `_codex_agent_loop` (342-411): one `bridge.request(payload)` asking the outer runner for `{"final_text", "tool_calls", "stop_reason": "end_turn", "iters": 1}`; returned calls are dispatched locally and their results logged but never returned to the model. `openai_compatible` cannot use tools (`AGENTS.md` 54-55). Note 02's warning is confirmed and extended: the committed sample runs used this one-shot path.

### 2.7 Coverage and note reconciliation

| Note claim | Verdict at `0007ad10` |
|---|---|
| 02: bounded loop preserving `completed/killed/exhausted`; append-only ledger; reflection with guardrails; scoped memory; no held-out evaluator | all confirmed; leaderboard additionally unversioned; `_maybe_promote_skill` residual added |
| 02: Codex bridge does not loop | confirmed; sample runs used it |
| 07: activity bar, monitor, ETA; `progress.json` + `job_events.jsonl`; WS may skip updates; history/restore/polling; versioned proposal/review; report lineage; review dimensions; evidence checking | all confirmed; evidence checking is stronger than described (calibration cap, reason codes); ETA extrapolates over a changing denominator; heartbeats unjournaled |
| 07 gaps 1-4 | real, none addressed; gap 4 untested |
| 07 gap 5 | real; trace now carries `evidence_refs`/`rejected_evidence_refs`, but the UI renders strings, not links |

Test gaps beyond those: no test of denominator semantics or multiple `complete` events; no reconnect/replay test; no Codex agent-loop round trip; no snapshot/version test for the leaderboard.

### 2.8 What changed from `main` (`7cdf6591`, 2026-07-09)

53 commits, 235 files, +35,240/−2,632. `run_dir.py` is byte-identical, so the progress mechanism is unchanged. New: `skill_policy.py`, `reflection.py`, `ReportIterator.tsx`. `reviewer.py` (+607) gained the evidence audit and calibration (`f96dd11`, `7755cec`); `loop.py` (+120) gained `review_fixed_proposal` (71-130, so user-authored proposals cannot bypass review) and dropped the per-round auto-lesson; `memory.py` (+606) gained review states and trust scoping; `server.py` (+2007) added multi-user auth, job ownership, the reaper, and the richer trace; tests grew by roughly 7,500 lines. The direction is toward the behaviors the brief asks for; the state-label and event-completeness gaps were not touched.

## 3. deepseek-harness (`d7432673`, 2026-10-09, v0.2.1-alpha.2, MIT, developer preview)

Kernel boundary: Agent Note `2026-06-11-microkernel-event-taxonomy.md` (status implemented) makes every extension point a typed Cordis event with four dispatch modes (waterfall, serial, parallel, emit); `agent/*` events live in the `dsh-agent` contract package, and `dsh-agent-loop` is the only concrete loop and is swappable (`docs/architecture.md`; `packages/core/agent/src/runtime-types.ts`).

Event model (`docs/architecture.md`, "Turn flow"): durable session events `turn/start|end`, `step/start|end`, `system/message`, `user/message`, `developer/message`, `assistant/message`, `assistant/attempt`, `tool/call`, `tool/result`; live waterfalls `agent/pre-step`, `agent/request`, `llm/stream`, `tools/pre-execute|execute|post-execute`; serial `agent/turn-stopping`. A step is one model request plus its tools; a turn is zero or more steps. `SessionEvent` is `{type, seq, time, data}` with contiguous `seq`; `deriveMessages()` projects history (`docs/subsystems/session.md`).

Persistence (`2026-06-14-session-persistence.md`; `packages/core/agent-loop/README.md` 116, 198): append-only JSONL per session, header out of log, versioned formats with explicit migrations; a crashed turn is closed, never truncated, and resume appends `interruptedTurnClosers` plus synthetic results for unanswered tool calls ("Its outcome is unknown", retry only if idempotent). Projections are pure synchronous folds over committed events (`session-projection.md`), which is spine component 11's "UI state is a projection" made concrete.

Tool results: `tool-calls.ts` appends `tool/call` (264) and `tool/result` (282); aborts record synthetic error results so replay stays valid (8-9, 240). `ToolResultMessage` is `{toolCallId, content, isError}` (`llm-streaming.md` 34). `ToolDefinition` has a mandatory `output.schema`, pure `render`, `execute(args, exec)` with a cancellation signal, and `timeoutMs` enforced by a policy plugin (`tools.md`).

Progress surfacing is thin: `AgentStatus` is `'idle' | 'running'` (`runtime-types.ts` 109); `JobStatus` is `running | stopping | completed | killed | failed` with a free-text `progress` line cleared at settlement (`jobs.md` 21, 238-239); goals have `GoalPhase` `active | paused | blocked | complete` with typed `GoalBlockReason {code, message}` (`goal.md`). Human feedback events are log-only and never reach the model (`feedback.md`).

Evaluation: `BENCHMARK.md` is three lines of SDK pointers; `benchmarks/` are wall-clock and memory gates (session open, reconnect, conversation fold, long sessions, terminal I/O) with a rule never to use recorded sessions (`benchmarks/AGENTS.md`). There is no agent-capability evaluation. Tests: 1,671 `.ts` files under `packages/*/tests` (71 in `packages/core`); `snapshots/session` has 136 recorded-session replay fixtures. Documentation is generated from source (`type-equiv` blocks) and Agent Notes carry explicit status labels, so implemented versus intended is unusually legible.

## 4. ARIS (`26b95cfa`, 2026-10-07; arXiv 2605.03042 not in repo, not read)

ARIS is 84 Markdown skills plus Python helpers and MCP bridges; there is no runtime loop in code. `skills/auto-review-loop/SKILL.md`: `MAX_ROUNDS = 4` (25); stop when `score >= 6/10` and `verdict ∈ {ready, almost}` (26); phases review → fix → re-evaluate; `review-stage/REVIEW_STATE.json` overwritten each round with `run_id, round, threadId, reviewer_backend, executor/reviewer model and family, identity_assurance, independence_verified, requires_external_acquittal, status, last_score, last_verdict, pending_experiments` (138-185); append-only `ACQUITTAL_LOG.jsonl` binding verdicts to trace ids (187-216); append-only reviewer memory hashed before each call (587-590). Stop/continue/escalate is executable in `tools/review_gate.py` (same-family verdicts fail closed; 27 tests).

Artifacts: file paths only. `shared-references/reviewer-independence.md` forbids summaries, interpretations, previous-round feedback, and change descriptions; `review-tracing.md` stores every request/response under `.aris/traces/<skill>/<date>_run<NN>/`. Audit skills open a fresh thread per round; `auto-review-loop` is the documented exception.

Verify versus opine: `acceptance-gate.md` splits Type-A execution gates (exit codes, files exist, "reviewer was invoked") that the executor may self-judge from Type-B quality gates ("score >= 6 when Claude assigned the score") that must be cross-family: "A goal/loop can DRIVE; it cannot ACQUIT." `tools/evidence_check.py` proves cited evidence exists and states `verified ≠ correct`. `tools/run_state.py` separates `done` (self-report) from `accepted` (requires `verdict_id` and a non-same-family `reviewer`); resume walks to the first phase not in `{accepted, skipped}` (22 tests). `iteration_log.py` turns zero-finding rounds into a stall ladder (2 → structural pivot, 4 → human). `kill-argument` computes its verdict from per-point counts in skill code so the defending reviewer cannot self-grade (377-379).

Evidence of improvement: README 1061-1096 shows one paper moving 4/10 → 8.5/10 by an AI reviewer over three rounds; line 650 states the scores "are AI-review signals, not venue acceptances" and are "an expected byproduct, not proof of acceptance". One community PDF is archived (under review). No ablation, baseline, or held-out comparison exists in the repository. `meta-optimize` proposes harness changes only; landing requires human `/meta-apply`, and its SKILL.md admits the provenance verifier is "NOT yet built".

## 5. Darwin Gödel Machine (`a565fd2d`, 2025-08-13, Apache-2.0, arXiv 2505.22954)

Outer loop (`DGM_outer.py` 270-332): up to 80 generations; choose `selfimprove_size` (2) parents; run `self_improve` in threads with a 1.5 h timeout; drop children that did not compile; update the archive; append one line per generation to `dgm_metadata.jsonl`.

Archive and selection (`choose_selfimproves` 50-150): candidates are archive entries with readable `metadata.json`; methods `random`, `score_prop` (sigmoid of accuracy), `score_child_prop` (default; × 1/(1+children)), `best`; the argparse `choices` at 227-228 is missing a comma, so `best` is not selectable from the CLI. Targets are failure classes `solve_empty_patches`, `solve_stochasticity`, `solve_contextlength` (0.25 each) or a random unresolved task. `update_archive` (174-190) defaults to `keep_all`; `keep_better` compares against the initial agent minus `noise_leeway` 0.1, not the parent.

Evaluator (`self_improve_step.py` 125-221; `swe_bench/harness.py`): deterministic benchmark tests in Docker; accuracy is `resolved / submitted` (`utils/evo_utils.py` 43-95). Staged cost: small subset (10) first, medium (50) if resolved ≥ 0.4 of small; `get_full_eval_threshold` (second-highest archive score, min 0.4) gates the big subset (140), although `full_eval_threshold` and `test_task_list_big` are accepted (234, 258) and not referenced in the function body at this commit. The problem statement is diagnosed by an LLM (`o1-2024-12-17`, 28) from the parent's failure logs; a post-hoc LLM "improvement diagnosis" is recorded but does not affect selection.

Safeguards and cost: Docker isolation, 30-minute agent timeout, compile filter, README warning about untrusted model-generated code. No token or dollar accounting; the committed initial agent reports accuracy 0.2 (12/60). Tests cover only the bash and edit tools. Nothing is held out: selection, admission, and reported score use the same subsets. For component 13 this gives three adoptable mechanics (never-delete archive, staged budgets, explicit noise leeway) and one hard warning (optimizing on the selection set); it also shows an outer loop needs a deterministic or human-labelled evaluator, which our domain does not have ready-made.

## 6. Mechanisms table

| Mechanism | Repository, path | Status | Spine | Verdict and reason |
|---|---|---|---|---|
| Versioned progress snapshot plus append-only journal | AD `run_dir.py` 91-143 | implemented, tested, recorded | 11 | adapt: keep dual write; widen vocabulary; journal heartbeats as activity |
| Server-side terminal finalization and reaper | AD `server.py` 403-446, 1255-1283 | implemented, tested | 10 | adopt: disk never stays `running`; emit `failed`/`cancelled` with `finalized_by` |
| Progress-only WebSocket with version skipping | AD `server.py` 4179-4208 | implemented, tested | 11 | adapt: live latest state, but replay history by `seq` |
| Restore from local storage plus transcript polling | AD `App.tsx` 2839-2884 | implemented | 11 | adapt: resume by sequence number |
| Linear ETA over changing denominators | AD `App.tsx` 3108-3125; `recommend.py` 624-680 | implemented, recorded | 11 | avoid |
| Slot state machine with versioned artifacts and kill arguments | AD `loop.py` 201-307 | implemented, tested | 3 | adopt, renamed `completed/rejected/unresolved` |
| Disposition remap of `exhausted` | AD `server.py` 980-989 | implemented, untested | 3, 11 | avoid |
| Shared-transcript reviewer | AD `loop.py` 230; `proposer.py` 121-145 | implemented | 3 | avoid for critique; allow an explicit revision-check exchange |
| Citation verification against injected catalog; downgrade-only calibration | AD `reviewer.py` 206-422 | implemented, tested | 5, 3 | adopt |
| Scoped provisional memory with review states | AD `memory.py` 207-218, 262-265 | implemented, tested | 9 | adopt |
| Count-based auto skill promotion | AD `memory.py` 422-458 | implemented, untested | 9 | avoid |
| Methodology content policy | AD `skill_policy.py` | implemented, tested | 9, 13 | adapt: necessary, not sufficient |
| Post-run reflection with honest skip | AD `reflection.py` | implemented, tested | 13 | adapt: route output into evaluation |
| Append-only ledger, latest-by-timestamp projection | AD `evidence_ledger/ledger.py` | implemented, tested | 5, 7 | adopt |
| Read-only evidence-first leaderboard | AD `leaderboard.py` | implemented, tested | 8 | adapt: add snapshot id, rule version, ordering method, four states |
| Anthropic tool loop | AD `llm_client.py` 413-488 | implemented, tested | 4 | adapt behind a neutral contract |
| Codex bridge one-shot loop | AD `llm_client.py` 342-411 | implemented, recorded | 4 | avoid as-is |
| Report iteration with `parent_version` | AD `report_iteration.py` 270-290 | implemented | 11 | adapt: add change summary |
| Typed event taxonomy with dispatch modes | dsh Agent Note 2026-06-11 | implemented, tested | 11, 4 | adopt |
| Durable `tool/call`/`tool/result`; synthetic results for unanswered calls | dsh `tool-calls.ts` 264-282; README 198 | implemented, tested | 4, 10 | adopt |
| Append-only log; crashed turn closed not truncated; replay resume | dsh persistence note | implemented, tested, replay fixtures | 10, 11 | adopt |
| Pure-fold projections | dsh `session-projection.md` | implemented | 11 | adopt |
| Tool contract with output schema, cancellation, timeout | dsh `tools.md` | implemented | 4 | adopt |
| Two-value agent status; free-text job progress | dsh `runtime-types.ts` 109; `jobs.md` | implemented | 10 | avoid as user-facing vocabulary |
| Goal `blocked` with typed reason code | dsh `goal.md` | implemented | 10 | adopt for `unresolved`/`waiting_human` reasons |
| File-paths-only reviewer input; cross-family rule | ARIS `reviewer-independence.md` | documented, traced | 3 | adopt |
| Type-A/Type-B gate split | ARIS `acceptance-gate.md` | documented | 3, 10, 12 | adopt |
| `done` vs `accepted`; accept needs verdict id and reviewer | ARIS `tools/run_state.py` | implemented, tested | 10, 12 | adopt |
| Deterministic evidence pre-check, `verified ≠ correct` | ARIS `tools/evidence_check.py` | implemented, tested | 5 | adopt |
| Stall ladder on zero new findings | ARIS `tools/iteration_log.py` | implemented, tested | 10 | adapt as "no actionable step" |
| Verdict computed by code from per-point counts | ARIS `kill-argument` 377-379 | documented | 3 | adopt |
| Single AI-score trajectory as evidence | ARIS README 1061-1096 | documented | 13 | avoid as evidence |
| Never-delete archive; score-and-novelty parent selection | DGM `DGM_outer.py` 50-190 | implemented | 13 | adapt |
| Staged evaluation budgets; explicit noise leeway | DGM `self_improve_step.py` 152-178; `DGM_outer.py` 174-190 | implemented | 13 | adopt |
| Selection and reporting on the same sets | DGM outer loop | implemented | 13 | avoid |
| Failure-class-directed improvement proposals | DGM `choose_selfimproves` 117-148 | implemented | 13 | adapt |

## 7. Findings

### F1. Execution-state labels are rewritten by presentation code
- **Issue**: `exhausted` is authoritative and non-admitting in `REVIEW_STATE.json`, yet the trace API labels it `sent_after_revision_limit`; three state vocabularies coexist; `force_finish` can append further `complete` events to a completed run.
- **Source / location**: AD `0007ad10` `loop.py` 282-292; `server.py` 980-989; `task_state.py` 18-24; `runs/rec_43273c9978/job_events.jsonl`.
- **Importance**: high; "sent after revision limit" implies progress that did not occur.
- **Recommended change**: component 11 defines one closed execution vocabulary (`queued, running, waiting_tool, waiting_human, retrying, paused, failed, cancelled, completed, unresolved`) and one exchange vocabulary (`completed, rejected, unresolved`); the Run Controller is the only writer; UI labels come from a published mapping table in which `unresolved` never maps to a word implying advancement; one terminal event per attempt, carrying `finalized_by {worker, controller, human}`; a recovery is a new attempt id.
- **Tradeoff**: less freedom for friendly per-view labels.
- **Unresolved uncertainty**: whether the recorded triple `complete` came from continue mode or watchdog recovery.
- Revised after cross-review: the `progress_version` reset (37 to 1 at event 37) shows the first `complete` closed an earlier attempt and continue mode restarted the counter; the second and third `complete` events (versions 67 and 68) belong to one attempt, the last following an MLIP recovery, so this is an attempt boundary, not a watchdog kill.

### F2. The journal records progress, not activity
- **Issue**: two event types; agent starts, tool dispatches, waits, retries, and heartbeats are absent; the client polls raw model I/O as the only live signal.
- **Source / location**: `run_dir.py` 107-143, 195-217; `App.tsx` 2839-2866, 3546; contrast dsh turn flow and `tool-calls.ts` 264-282.
- **Importance**: high; the brief requires separating activity from completed work.
- **Recommended change**: event record `seq, run_id, attempt_id, stage_id, step_id, exchange_id, actor {kind: agent|tool|human|controller, id}, event_type, state_from, state_to, question, inputs_ref, outputs_ref, error, at, cause_seq`; event types `run.*`, `stage.*`, `step.{started, waiting_tool, waiting_human, retrying, completed, failed}`, `tool.{called, returned, errored}`, `exchange.{proposed, critiqued, arbitrated, closed}`, `human.*`, and `heartbeat` as an activity class that never counts as work. Progress is a fold over these.
- **Tradeoff**: more events; projections must stay pure and cheap (dsh's unchanged-reference rule).
- **Unresolved uncertainty**: how much transcript to keep reachable from the timeline for audit.

### F3. Denominators are stage-local and change mid-run
- **Issue**: one `percent` field means `3/4 phases`, `k/35 candidates`, `j/65 MLIP steps`, `1/1 done` within a single recorded run; the ETA extrapolates across them.
- **Source / location**: `recommend.py` 232-340, 624-680; `App.tsx` 3118-3122; recorded run phase/total pairs.
- **Importance**: medium; misleading, not corrupting.
- **Recommended change**: three progress levels (run, stage, current exchange), each `denominator_known, completed, planned, elapsed_s, last_activity_at`; no cross-stage percentage; no ETA without a declared denominator and calibrated per-unit duration; round budgets shown as `rounds_used / round_budget` labelled "budget".
- **Tradeoff**: no single reassuring number.
- **Unresolved uncertainty**: none material.

### F4. History exists; semantic difference does not
- **Issue**: proposal/review and report versions are whole snapshots with lineage, not field-level changes linked to their cause.
- **Source / location**: `loop.py` 294-297; `report_iteration.py` 270-290; `ReportIterator.tsx` 130-178.
- **Importance**: high for the Criterion Registry and Leaderboard.
- **Recommended change**: components 6 and 8 write change records `change_id, object_kind {criterion, rule, candidate_assessment, leaderboard_entry}, object_id, from_version, to_version, operation {add, revise, merge, split, remove, admit, exclude, demote, unrank}, fields_changed [{field, before, after}], cause {critique_id | evidence_id | human_decision_id | tool_result_id}, actor, at`; the difference view is a projection over them.
- **Tradeoff**: disciplined write paths; free-text edits must be diffed or declared.
- **Unresolved uncertainty**: granularity for derived thresholds and units.

### F5. Tool feedback is provider-specific and, for one provider, one-shot
- **Issue**: only the Anthropic path loops; the Codex bridge discards results from the model's view; OpenAI-compatible endpoints have no tools; sample runs used the one-shot path.
- **Source / location**: `llm_client.py` 342-426; `AGENTS.md` 54-61; `runs/rec_43273c9978/manifest.json`.
- **Importance**: high.
- **Recommended change**: component 4 owns `ToolCall {call_id, name, args, step_id}` and `ToolResult {call_id, status {ok, error, timeout, cancelled, unknown_outcome}, value | error, schema_version, duration_ms}`; the broker, not the adapter, decides whether another model request is owed; every call gets a result even when the step aborts (dsh's synthetic "outcome unknown" with an idempotency hint); a conformance script runs the same exchange through each adapter and records the provider path as provenance on each exchange.
- **Tradeoff**: message-encoded loops for non-native providers are slower and less reliable, and must be visible as such.
- **Unresolved uncertainty**: whether domain tools such as CDES need background-job states (`waiting_tool`).

### F6. Review independence is asserted, not enforced
- **Issue**: the reviewer sees the proposer's rationale and prior rounds while prompts and docstrings claim the opposite.
- **Source / location**: `loop.py` 7-9 versus 230; `proposer.py` 121-145; `agent_harness.py` 654-657, 722; contrast ARIS `reviewer-independence.md`, `acceptance-gate.md`.
- **Importance**: high; note 02 already warns that role names do not create independence.
- **Recommended change**: component 3 defines `critique` (critic receives artifact references and the ledger slice only) and `revision_check` (critic receives its own prior critique plus the new artifact); each critique records `independence {inputs_disclosed, saw_prior_critique, saw_proposer_rationale, model_family_differs: true|false|unknown}`; verdict aggregation is code, as in ARIS `kill-argument`.
- **Tradeoff**: blind critics repeat answered objections; `revision_check` absorbs that.
- **Unresolved uncertainty**: availability of cross-family critics under the project's provider constraints; if absent, record `false`, do not claim independence.

### F7. Agent verdicts can still leak into durable memory
- **Issue**: `_maybe_promote_skill` turns rejection counts into `avoid-<element>` skills without evaluation, the category `skill_policy.py` forbids for model-authored text.
- **Source / location**: `memory.py` 299-307 versus 247-279, 422-458.
- **Importance**: medium; dormant on the main path, but a pattern to avoid copying.
- **Recommended change**: component 9 record `kind {evidence, hypothesis, procedure}, status {provisional, evaluated, approved, retired}, scope {group, role}, source {human, tool, model, literature}, derived_from, evaluation_ref`; only a component 12 decision or a component 13 evaluation may set `approved`; counts never create procedures.
- **Tradeoff**: slower memory.
- **Unresolved uncertainty**: whether deterministic-rule outcomes belong in memory or only in the registry.

### F8. No inspected repository evaluates strategy versions on held-out material
- **Issue**: AD saves provisional skills without later measurement; DGM selects and reports on the same subsets; ARIS offers one AI-scored trajectory and disclaims it.
- **Source / location**: `reflection.py` 158-264; `DGM_outer.py` 50-219; `self_improve_step.py` 152-178; ARIS README 650, 1061-1096.
- **Importance**: high; component 13 is the credibility of "self-improving".
- **Recommended change**: record `strategy_version, parent_version, change_summary, evidence_snapshot_id (frozen), evaluation_set {development, held_out}, budget {tool_calls, model_calls, wall_time}, metrics {precision_admitted, coverage, abstention, unsupported_claim_rate, incorrect_exclusion_rate, reproducibility, cost}, noise_leeway, baseline_version, decision {promote, keep_candidate, reject}, decided_by {harness, human}, rollback_to`; adopt DGM's staged budgets and never-delete archive; the promotion gate is a Type-B judgment the strategy's author cannot acquit; held-out use is counted.
- **Tradeoff**: with one case study the held-out set is tiny; the design must state which claims stay unestablished.
- **Unresolved uncertainty**: the evaluator for CQA derivation without biological labels (process-level checks only).

### F9. Resume, continue, and reopen are conflated or under-specified
- **Issue**: AD separates `continue_run` from `resume_run` and offsets child indices, but the UI's restore only re-attaches to a running job and history is reopened by re-polling; dsh replays the log and closes a crashed turn; ARIS resumes to the first phase not `accepted`.
- **Source / location**: `recommend.py` 209-238; `App.tsx` 2872-2884; dsh `agent-loop/README.md` 116; ARIS `resumable-runs.md`.
- **Importance**: medium-high; stale/rerun propagation depends on it.
- **Recommended change**: component 10 defines `attempt`, `continuation`, `evidence_refresh_run` (new run id, same context, new cutoff), and `reopen` (read-only); resume replays from the last checkpoint `seq`, marks steps `completed` only when an evaluated artifact exists, else `queued`; human-approved records are never re-derived silently.
- **Tradeoff**: more states to learn.
- **Unresolved uncertainty**: checkpoint granularity for long tool runs.

### F10. Human approval is a software field everywhere inspected
- **Issue**: AD's `human_review_state` is an untyped dict, its verification gate is a boolean callable, and `approved` follows from `source == "human"` without an attributed record; dsh feedback never affects the model; ARIS `manual-review` routes to a human-chosen model, not a scientist.
- **Source / location**: `evidence_ledger/models.py` 57; `dual_agent/harness.py` `VerificationGate`; `memory.py` 262-265; dsh `feedback.md`; ARIS `mcp-servers/manual-review`.
- **Importance**: high; the brief separates agent verdict, software status, and human scientific approval.
- **Recommended change**: component 12 record `decision_id, actor {person_id, role}, object {kind, id, version}, decision {approve, reject, edit, request_followup, pause, resume}, reason, evidence_refs, at, supersedes_decision_id, stale_marks`; any `approved` status must reference a `decision_id`; projections render "approved by <role> on <date>" or nothing.
- **Tradeoff**: friction for small edits, mitigated by batching in the queue.
- **Unresolved uncertainty**: whether approving a criterion also approves the rule that uses it.

## 8. Appended repositories

Three repositories added on the coordinator's Wave 1.5 assignment, inspected 12 October 2026, 17:14-17:35 UTC, read-only, same methods as above. None of the three papers (arXiv 2608.08466, 2510.04618, 2510.21614) was read; claims attributed to them are reported as the repositories state them.

### 8.1 hsi (`97a022b9`, 2026-08-23) — Hierarchical Self-Improvement

License status, exactly as found: there is no `LICENSE`, `LICENSE.*`, or `COPYING` file; `README.md` lines 199-201 read "## License" followed by the single word "MIT"; no `.py`, `.md`, `.toml`, or `.yaml` file carries an SPDX, copyright, or "licensed under" line; `requirements.txt` says nothing about licensing. The MIT claim therefore rests on one README word with no license text. A committed `.env` holds `LLM_PROVIDER`, `OPENAI_API_KEY`, and `OPENAI_API_BASE`; the key value is seven characters long, not a plausible credential (values were not printed).

Boundary (three scopes). One frozen model acts in three scopes with disjoint editable surfaces (`README.md` 1-8): the task harness (`repo/harness.py` and siblings), the evolver (rewrites the harness through seed selection, main evolution, commit selection), and the meta-evolver (rewrites `evolution/select_seed.py` and `select_commit.py`). The anchor is `godel_evolution_init/`: it is copied into `repo/evolution/` at run start except `select_best.py`, which is never copied and is loaded from the init template, so meta-evolution "physically cannot edit it" (`src/react_loop/agent.py` 1457-1466; `archive_manager.py` 1-11, 33-41). Enforcement is a path sandbox in the tool executor: the evolve scope may not touch `evolution/` (`agent.py` 1122-1127); meta-evolve `edit_file`/`write_file` are limited to `evolution/` and the repo root (1143-1151) and `read_file` to `evolution/`, `src/react_loop/`, and root harness files (1152-1169); bash edits that escape to harness files during meta-evolution are reverted from the pre-meta commit (`meta_evolve.py` 727-740); the probe sub-agent is read-only (`probe_agent.py` 4, 19). The "frozen" selector is fixed code and fixed prompts around an LLM react loop (`select_best.py` 1-60, 130-200), so frozen means non-editable procedure, not deterministic selection. `select_seed.py` and `select_commit.py` split FIXED interface blocks from EVOLVABLE prompt blocks (`select_seed.py` 1-50; `select_commit.py` 1-15).

What a harness is. Per environment, `godel_harness_init/<env>/` holds `harness.py` with the fixed entry `using_harness(agent, obs)` (`balrog_babyai/harness.py` 31-51) and an evolvable `HarnessPolicy` step lifecycle (54-80), `prompts.py` (a 12-line system prompt), `hooks.py` (no-op request/response/complete hooks), `context.py` (message-history management), `utils.py`, optional `tools_harness.py` (agentdojo and terminal_bench templates), and `BOOTSTRAP.md`. `src/react_loop/framework_contract.md` fixes the file roles and states that `using_harness()` is never modified. Memory: `plan.md` is iteration-scoped and rolled back with the code; `BOOTSTRAP.md` is permanent, and a `lesson(iteration=N, ...)` call replaces that iteration's earlier line in place (framework contract, "Keep lessons honest").

Loop and ranking. Per iteration: LLM seed selection with a hypothesis carrying falsification criteria (`strategies/greedy.py` 20-45 shows the template), main evolution with `evaluate(eval_mode="dev")`, LLM commit selection of two to five diverse versions with "Val > Dev" and "diversity over max reward" rules (`select_commit.py` 20-60), optional meta-evolution, and a terminal best-version selection whose fusion results must be evaluated before submission (`select_best.py` 130-175). Reward is the lower confidence bound mean − z·stdev(ddof=1)/√n over episodes within one task evaluation, mean for n < 2 (`state.py` 66-96), z from `lcb_zscore` (0.5 in the suite configs, `balrog_babyai/config.yaml` 12; code default 1.0, `main.py` 127); it applies to dev and val only, while test reports the raw mean to match the benchmark (`src/benchmark/balrog/adapter.py` 124-131, 176-186). Version ranking takes the maximum single-evaluation reward per code hash, prefers the val layer whenever any val evaluation exists, and never mixes layers (`state.py` 97-177), so the conservatism is within an evaluation, not across repeated evaluations of one version. Unit test `test_lcb` checks the jittery-versus-stable ordering (`run_tests.py` 184-221).

Splits. `src/benchmark/adapter.py` 185-275 splits tasks per category: dev versus test by `dev_ratio` with `split_seed`; val out of dev by `val_ratio` with `split_seed + 1000` (162-184); `dynamic_sample` re-samples dev per evaluation while val and test stay fixed. Setup A uses `dev_ratio 1.0`, `val_ratio 0.0` (no held-out; `balrog_babyai/config.yaml` 74-76); Setup B uses `dev_ratio 0.8`, `val_ratio 0.2`, `split_seed 66`, `test_repeats 1` (`balrog_babaisai_breakstop/config.yaml` 73-80). Test evaluation runs after evolution in `main.py` (484) or `main_final.py` 198-241 with a rotating repeat seed.

Persistence and recording. A git repository of harness versions; `evolution_metadata.json` written by `EvolutionTracker` with `EvolutionRecord {iteration, parent_commit, new_commit[], reward[], timestamp[], state_summary, action_count, metadata}` where the lists are a commit pool (`git_version/controller.py` 29-70); `usage_summary.json` from per-call token logging with scope `harness | meta | evolve`, model, and thinking flag (`agent.py` 514-538); `test_repeat_results.json` and `final_results.json` (`main_final.py` 289, 311); `context.json` and `.evolution/` for resume (`agent.py` 1232-1300); `evolution_graph.html` from a knowledge graph with LLM-analyzed correlation edges (`knowledge_graph.py`). Progress surfacing is log lines and `fmt_iteration_status` (`state.py` 37); there is no event journal.

Implemented versus documented. Code, configs, and 65 test functions across `run_tests.py` and `src/react_loop/tests/` are present; the README result tables (BALROG leaderboard comparison, Setup B held-out rewards) are paper results reproducible only with BALROG data and a DeepSeek endpoint; the README's "What HSI is not" (175-177) is an honest limits statement. Nothing was executed.

### 8.2 ace (`82709de0`, 2026-08-24; Apache-2.0 `LICENSE.txt`; `pyproject.toml` version 0.1.0) — Agentic Context Engineering

Loop. `ace/ace.py` `_train_single_sample` (456-632): the Generator answers with the playbook; `answer_is_correct(final_answer, target)` decides correctness (477); if incorrect, up to `max_num_rounds` (3) Reflector rounds each tag the bullets used and regenerate (499-545); if correct, one Reflector pass tags helpful bullets (548-576); every `curator_frequency` steps the Curator emits operations (579-600); optional `BulletpointAnalyzer` (602-608); a post-curation generation records the post-train result (611-626). Offline mode validates every `eval_steps` and keeps `best_playbook` by validation accuracy (632-836, 781-784); online mode trains and tests in windows (877-1141). `ace_batch.py` (1,552 lines) is a parallel variant in which groups propose operations from one playbook snapshot and an LLM reducer deduplicates them (`core/curator.py` 169-326).

Delta item format and counters. A bullet is one text line `[section_slug-00000] helpful=X harmful=Y :: content` parsed by regex (`playbook_utils.py` 13-27, 46-48); counters are incremented from Reflector tags `helpful | harmful | neutral` (`update_bullet_counts` 50-93; tag extraction `core/reflector.py` 100-149; prompt `prompts/reflector.py` 1-30). `get_playbook_stats` (218-255) derives `high_performing` (helpful > 5, harmful < 2), `problematic` (harmful ≥ helpful), and `unused` counts for the Curator prompt.

Deterministic merge, de-duplication, pruning. `apply_curator_operations` (96-217) implements only ADD: fresh id, counters 0/0, appended to the named section or OTHERS. UPDATE, MERGE, CREATE_META, and DELETE are TODO comments (100-104, 131-141), and the reducer prompt states "The current ACE implementation only supports ADD operations" (`prompts/curator.py` 139). De-duplication is therefore (a) prompt instruction ("Avoid redundancy", 17, 80; "Drop proposals that are already covered", 145-146) and (b) the optional analyzer, off by default (README argument table), which groups bullets by sentence-transformer cosine similarity at threshold 0.9 and either keeps the first or merges each group with an LLM (`core/bulletpoint_analyzer.py` 150-191, 193-272, 273-371). Nothing prunes by counters; `playbook_token_budget` (80,000) is only interpolated into prompts and `count_tokens` is used for logging (grep over `ace/`, `utils.py`, `playbook_utils.py`). Context collapse is prevented structurally: the Curator may output operations only ("Do NOT regenerate the entire playbook", `prompts/curator.py` 20) and the merge code can only append, so the playbook grows monotonically unless the analyzer runs.

Signals. Correctness comes from the DataProcessor's label (`target`). In `no_ground_truth` mode the Reflector receives no target and a fixed feedback string (514-517, 557-560), but the loop's branching still computes `is_correct` from `target` at 477 and 542, so labels steer the loop even when the prompt is told there are none. The AppWorld execution-feedback path lives in the `ace-appworld` submodule, which is an empty directory in this clone and could not be inspected.

Persistence and recording. The playbook text file is the state; a line without the standard prefix but containing "::" is parsed with an `unknown-` id (`bulletpoint_analyzer.py` 53-60). Logs: `bullet_usage_log.jsonl` with `timestamp, epoch, step, sample_id, sample_question, sample_context, bullet_ids_used, bullet_count, bullets_with_content, reflection_summary, is_correct` (`logger.py` 32-82); `curator_operations_diff.jsonl` (83-); `detailed_llm_logs/`; intermediate playbooks every `save_steps` (`ace.py` 728-731); `best_playbook.txt`; `initial_test_results.json` versus `final_test_results.json` as a built-in before/after. No progress API; no event journal.

Evaluated versus asserted. The README's gains (+10.6% AppWorld, +8.6% finance, latency and cost reductions) are paper results; the repository ships finance train/val/test subsets (`eval/finance/data/`) and run scripts with the empty-playbook baseline, so the finance before/after is reproducible in principle. No unit tests exist in the file listing.

### 8.3 HGM (`013872d9`, 2026-02-08; Apache-2.0) — Huxley-Gödel Machine

Relation to dgm. `diff -rq` against the dgm clone: 36 shared files differ and `hgm.py`, `hgm_utils.py`, `tree.py`, `config.py`, `config.yaml`, `evaluate_agent.py`, `run.sh`, `best_agent/`, and `utils/test_generator.py` are new; `DGM_outer.py` is gone. `initial_swe/` and `initial_polyglot/`, which `initialize_run` expects (`hgm.py` 84-95), are absent from the clone.

Loop. `hgm.py` 122-489 replaces DGM's generations with an asynchronous pool (`max_workers` 20) of two operations. `expand()` (383-404) picks a parent by Thompson sampling over clade descendant evaluations and runs one self-improvement (`hgm_utils.sample_child`, 279-). `sample()` (406-459) picks a node by Thompson sampling over its own measurements and evaluates one more task on it. The rule at 412-420 expands when `n_task_evals ** alpha >= nodes − 1 + pending_expands` (alpha 0.6, `config.yaml`), so the tree grows as a power of total evaluations, up to `max_task_evals` 800.

Clade metaproductivity versus `score_child_prop`. `tree.py` 45-54: a node's descendant evaluations are its own binary utility measures (or its mean repeated `n_pseudo_descendant_evals` = 10,000 times once it has at least that many) plus every descendant's measures; `TS_sample` (`hgm.py` 360-377) draws Beta(1 + successes, 1 + failures) per candidate and takes the argmax, with optional cool-down scaling (`cool_down: false`). Only nodes with finite `mean_utility` > 0 may be expanded (385-389), so an unevaluated or zero-score node is never a parent. DGM's `score_child_prop` used sigmoid(own score) × 1/(1 + children); HGM selects on the aggregate outcome of the whole subtree, so a mediocre parent with productive children is preferred, and a strong parent with failing children is demoted. Utility is binary per task: 1 if resolved (`utils/eval_utils.py` 13-22; `initialize_run` 100-118).

Evaluator and held-out. Within a run, tasks are SWE-bench Verified `small` + `medium` (60) shuffled with seed 42, or all Verified if `full_eval` (`hgm.py` 327-335); polyglot uses medium + small; each `sample()` evaluates one not-yet-submitted task on the chosen node (`hgm_utils.eval_agent` 154-278). Nothing is held out inside the run. `evaluate_agent.py` (1-26) evaluates an exported agent on a different split (`SWE-bench_Lite` default, `gpt-5`) with `hours_per_task`; `best_agent/README.md` points to external results. So the held-out evaluation is a separate post-run script on a different split, and the clone records the exported best agent and its `self_evo.md` transcript but no in-repo result numbers.

Archive policy, cost, safeguards. All nodes persist in `hgm_metadata.jsonl` (append per update; `hgm.py` 30-49) with `commit_id, id, parent_id, mean_utility, num_evals`; failed children are not added (401-403); `continue_from` rebuilds the tree (52-99). No deletion. Cost accounting: none in `hgm.py`, `hgm_utils.py`, `llm.py`, `config.py` (no usage, token, or cost fields); budget is `max_task_evals` plus 3600 s timeouts; models `gpt-5-mini` for self-improve, downstream, and diagnosis (`config.yaml`). Safeguards as DGM: Docker, timeouts, README warning; `diagnose_problem` retries twice (`self_improve_step.py` 29). Tests remain the two tool tests. Progress surfacing is the metadata file and `hgm_outer.log`.

### 8.4 Added mechanism rows (same columns as section 6)

| Mechanism | Repository, path | Status | Spine | Verdict and reason |
|---|---|---|---|---|
| Frozen, non-copied final selector; path-sandboxed edit scopes; bash-escape revert | hsi `agent.py` 1122-1169, 1457-1466; `meta_evolve.py` 727-740 | implemented, tested | 13 | adopt: the promotion/export decision procedure sits outside the evolvable surface |
| LCB reward over episodes, z configurable; raw mean on test | hsi `state.py` 66-96; `balrog/adapter.py` 176-186 | implemented, tested | 13 | adopt, extended to repeated evaluations of one version |
| Max-of-evaluations ranking, val preferred, layers never mixed | hsi `state.py` 97-177 | implemented | 13 | adapt: rank by LCB across repeats, not max |
| Stratified dev/val/test with fixed seeds; test touched only post-run with repeats | hsi `adapter.py` 162-275; `main_final.py` 198-241 | implemented | 13 | adopt |
| Hypothesis with falsification criteria per iteration; `plan.md` rolled back with code | hsi `framework_contract.md`; `strategies/greedy.py` 20-45 | implemented (prompt contract) | 3, 13 | adopt as proposal fields |
| In-place overwrite of past lessons by iteration number | hsi framework contract, "Keep lessons honest" | documented | 9 | avoid; supersede, do not rewrite |
| LLM commit pool of 2-5 diverse versions | hsi `select_commit.py` 20-60 | implemented (prompt) | 13 | adapt: keep candidates, but selection by recorded metrics |
| Per-call usage log by scope | hsi `agent.py` 514-538 | implemented | 13 | adopt |
| Identified delta items with helpful/harmful counters | ace `playbook_utils.py` 13-93 | implemented | 9 | adopt with attribution and provenance fields |
| Append-only ADD merge; no whole-text regeneration | ace `playbook_utils.py` 96-217; `prompts/curator.py` 20, 139 | implemented | 9 | adopt the operation discipline |
| Embedding-threshold grouping plus LLM merge | ace `bulletpoint_analyzer.py` 150-371 | implemented, off by default | 9 | adapt: grouping deterministic, merge human-reviewed |
| Token budget as prompt text only | ace `ace.py` 127, 454 | implemented | 9 | avoid; budgets must be enforced |
| Label-driven branching inside a "no ground truth" mode | ace `ace.py` 477, 514-517 | implemented | 9, 13 | avoid: declare signal provenance per counter |
| Clade-level Thompson selection over binary outcomes | HGM `tree.py` 45-54; `hgm.py` 360-404 | implemented, recorded (best agent) | 13 | adapt as a warning and as an optional selector |
| Incremental one-task measurement with expand/measure balance | HGM `hgm.py` 406-459 | implemented | 13 | adapt: evaluation budget allocation by uncertainty |
| Separate post-run evaluation on a different split | HGM `evaluate_agent.py` | implemented | 13 | adopt |
| No token or cost accounting | HGM | absent | 13 | avoid |

### 8.5 Findings added by Wave 1.5

### F11. Procedural memory should be delta items with attributed counters, never regenerated text
- **Issue**: ACE prevents context collapse by construction: memory is a set of identified items, the Curator may only emit operations, and the merge code only appends. Agentic Doping's `_maybe_promote_skill` and reflection write free text; hsi overwrites lessons in place. ACE's counters, however, are Reflector judgments that are label-informed in one mode and label-free in another, and nothing prunes.
- **Source / location**: ace `playbook_utils.py` 13-93, 96-217; `prompts/curator.py` 20, 139; `ace.py` 477, 514-517; hsi `framework_contract.md` "Keep lessons honest"; AD `memory.py` 422-458.
- **Importance**: high for component 9; it is the difference between an auditable memory and a drifting prompt.
- **Recommended change**: Component 9 memory item: `item_id, kind {evidence, hypothesis, procedure}, section, content, status, scope, support_basis, counters {helpful, harmful, neutral}, counter_events [{run_id, exchange_id, tag, tagged_by {model_family | human}, signal_provenance {outcome_label, evaluated_metric, model_judgment}}], supersedes_item_id`. Mutations are operations (`add, retire, supersede, retag`) recorded in the journal; no code path rewrites the store; corrections supersede rather than overwrite; pruning is a policy over counters and age that queues items for human review rather than deleting them; a counter incremented by a model judgment never counts as an outcome label.
- **Tradeoff**: more fields per item and a growing store; the analyzer-style grouping is useful for review queues but its LLM merge should produce a proposal, not a write.
- **Unresolved uncertainty**: whether counters from different model families should be pooled or kept separate.

### F12. Promotion needs a lower confidence bound, a split that is touched once, and a selector outside the evolvable surface
- **Issue**: hsi is the only inspected repository that combines uncertainty-aware reward, stratified dev/val/test with fixed seeds, test evaluated only after evolution with repeats, and a final selector that the evolving system cannot edit; but it ranks versions by the maximum of their evaluations and lets an LLM make the export choice.
- **Source / location**: hsi `state.py` 66-177; `adapter.py` 162-275; `agent.py` 1457-1466; `select_best.py` 130-175; `balrog_babyai/config.yaml` 74-76 versus `balrog_babaisai_breakstop/config.yaml` 73-80.
- **Importance**: high; this sharpens F8 into testable rules.
- **Recommended change**: Component 13 promotion rule: compare strategy versions by the lower confidence bound of each metric over repeated evaluations on the fixed evidence snapshot with a declared `z` and `n`, never by the best single run; development material may be re-sampled, validation is fixed, and held-out material is evaluated only when a version is nominated for promotion, with the touch counted in the version record; the promotion decision is a deterministic rule over recorded metrics plus a human decision record, and the code or policy that implements it is not part of any evolvable surface (declared in the Run Binding as `promotion_policy_version`, immutable per run).
- **Tradeoff**: LCB with small `n` is harsh and will leave many versions `keep_candidate`; held-out use counting slows iteration.
- **Unresolved uncertainty**: how to form repeats for a run that costs hours of tool time; stratification keys for a candidate universe of 3,171 compounds.

### F13. A version's own score is a poor predictor of its lineage; count-based selection needs binary outcomes we do not have
- **Issue**: HGM replaces DGM's own-score selection with clade metaproductivity because descendants' outcomes predict a parent's value better than its score. Its machinery assumes binary per-task outcomes and dense re-measurement; our per-criterion records carry `unknown`, and strategy versions rarely have descendants.
- **Source / location**: HGM `tree.py` 45-54; `hgm.py` 360-420; dgm `DGM_outer.py` 83-100.
- **Importance**: medium for component 13; it changes what "evaluated improvement" should measure.
- **Recommended change**: Component 13 records, for each strategy version, `lineage_metrics` aggregating the evaluated outcomes of versions derived from it and of evidence-refresh runs that reused it, alongside its own metrics; promotion may weigh lineage metrics only when the record shows at least one evaluated descendant. If a count model is used to allocate evaluation budget, `unknown` outcomes are excluded from both success and failure counts and reported as coverage, never folded into failure.
- **Tradeoff**: lineage metrics arrive late and may never exist for a one-case project.
- **Unresolved uncertainty**: whether any selection model is worth its complexity before more than one case study exists.

### F14. Proposals should carry a falsification test
- **Issue**: hsi requires each iteration's hypothesis to state the failure mode targeted, the mechanism, and falsification criteria, with a confidence that is lowered when trace evidence is absent; our proposal artifact has rationale but no test of its own claim.
- **Source / location**: hsi `framework_contract.md` ("plan", "lesson", confidence scale); `strategies/greedy.py` 20-45.
- **Importance**: medium for component 3; it makes critiques checkable.
- **Recommended change**: Proposal payload gains `expected_change {object_ref, field, direction}` and `falsification_test {observable, threshold_or_condition, evidence_kind_required}`; the critic's first obligation is to evaluate the test, and a `revision_check` reports whether the stated observable moved.
- **Tradeoff**: proposals become longer and some scientific proposals have no cheap observable.
- **Unresolved uncertainty**: how to phrase falsification for criterion-derivation proposals where the observable is expert agreement.

## Cross-review of mas_architecture.md

Workstream 2's report (6,028 words) was read in full on 12 October 2026, 17:10-17:25 UTC; every line reference below was re-checked at `0007ad10`.

### Agreements
- A1: adjudication is a deterministic combination gate (`reviewer.py` 601-686); no default LLM arbiter. Matches my F6.
- A3: the review result is a flattened multi-copy dictionary and the trace re-derives fields by fallback chains (`server.py` 978-1019); the mechanism behind my F1.
- B1: no plan as data; one constant bounds self-check and critique rounds (`loop.py` 219-224, 277-281).
- C1: the version counter restarts on continue/resume. Confirmed in the recorded run: `progress_version` falls from 37 to 1 at event 37 of `runs/rec_43273c9978/job_events.jsonl` (105 events, maximum version 68).
- C2: the tool loop reports no exhaustion at its iteration cap (`llm_client.py` 481-487).
- D1: `supports_tools` returns `True` for `codex_subagent` (`llm_client.py` 143-144) although the bridge cannot return results; my 2.6 adds that the sample runs used it.
- D2, E1, E2, F1-F3, G1, H2: not contradicted; the `marginal` label is at `memory.py` 309-310, reachable only for non-dual-agent sources.

### Objections
1. A2 and H1 "withheld-input critic" (`harness.py` 1121-1124). Both readings hold for different paths; WS2's generalization fails for the path that ran. `DualAgentHarness.step_review` never references `dialogue` after its signature (checked 1121-1264), so the file-chat reviewer is blind. `AnthropicAgentHarness.step_review` (`agent_harness.py` 952-955) passes it to `_agent_review`, rendered for the reviewer at 920 through `proposer.py` 121-145 with proposer rationale. `run_loop` selects that harness whenever `supports_tools(proposer)` holds (`loop.py` 171-174), covering every Anthropic-style and Codex configuration, so the sample runs used the shared-transcript reviewer. Only `review_fixed_proposal` (`loop.py` 125) is blind in both harnesses. Resolution: H1 must say "withheld inputs enforced in the file-chat harness and fixed-proposal review only"; disclosure is recorded per exchange (my F6), not assumed per harness.
2. H1 "Progress and event writer: Redesign" versus my "adapt". The record (three statuses, two event kinds, per-process counter) must be redesigned; the write discipline (atomic replace, append-only journal, server-side finalization, heartbeat separated from work; `run_dir.py` 43-60, 168-217; `tests/test_i15_features.py` 10-28) should be kept. Resolution: redesign the record, keep the discipline.
3. H1 "Citation cross-check" and "Per-candidate ledger": WS2 "Adapt", mine "adopt". Terminological; evidence classes, thresholds, and ledger fields are domain or schema work. Resolution: WS2's wording.
4. H1 "Post-run reflection: Reuse as pattern" versus my "adapt". Reuse as-is leaves the saved procedure recallable before evaluation, which WS2's own F1 and F3 forbid. Resolution: reuse the mechanism, gate recall behind the promotion record.
5. Rows missing from H1 because `web/client`, `report_iteration.py`, and the leaderboard beyond line 70 were outside WS2's scope: disposition remap (avoid; H2 agrees), ETA over changing denominators (avoid), WebSocket version skipping and client polling (adapt), cross-run leaderboard (adapt: snapshot id, rule version, ordering method), report lineage (adapt). No conflict; add them to the reuse decision of record.

### Interface conflicts
- Event record (F1/F2) versus C1 kinds and the A3 envelope. WS2 adds `artifact_written`, `decision_recorded`, `staleness_marked`, and step `progressed/paused/resumed/rejected/unresolved/cancelled`; I add `exchange.{proposed, critiqued, arbitrated, closed}` and `cause_seq`. Resolution: one journal with store-assigned `seq`, union of kinds; exchange transitions stay explicit because the round timeline is built from them; an artifact's `seq` is that of its `artifact_written` event, so there is one sequence space; `cause_seq` links events, `parent_artifact_id`/`supersedes` link artifacts.
- Units of work (F9) versus WS2's table and E2. I accept `self-correction turn`; I add `attempt` (one execution of a run; the counter reset is two attempts of one run) and keep `reopen` as a read-only view. Reuse is decided per step by the Reuse Record; "approved records are never re-derived silently" becomes `reuse_decision = reused_valid` with a human decision reference, as in ARIS `accepted`.
- Critique/revision_check (F6) versus the Independence Declaration (A2). Nested: my per-exchange block is one `checks[]` entry; `independence_level` is the per-decision aggregate. A `revision_check` sees its own prior critique, so it is a distinct `check_kind` that cannot raise the level; record `inputs_disclosed` beside `inputs_withheld`.
- Strategy-version record (F8) versus I1's merged promotion. Memory items are judged by recall effect and may be human-approved; strategy versions bundle policy parameters with approved memory and are judged by matched-budget comparison on frozen snapshots. Merging risks promoting strategies by the cheaper route. Resolution: shared promotion record schema, separate policies and evaluators; memory promotion feeds strategy versioning, it is not the same act.

### Mechanisms WS2 should have cited
WS2 scoped itself to Agentic Doping, so these are borrowings: C1 reinvents deepseek-harness's `SessionEvent {type, seq, time, data}`, closed-not-truncated crashed turns, and pure-fold projections; D1's contract tests and D2's isolation match dsh's synthetic "outcome unknown" tool results (`agent-loop/README.md` 198); A2 and E2 match ARIS `run_state.py` (`done` versus `accepted`, mandatory `verdict_id` and `reviewer`) and the `REVIEW_STATE.json` identity fields; A1 matches ARIS `kill-argument` computing verdicts from per-point counts; C3 matches ARIS `iteration_log.py`'s findings-count stall ladder; F1 matches `evidence_check.py`'s `verified` is not `correct`; I1 should weigh ARIS's `meta-optimize`/`meta-apply` split and DGM's never-delete archive, noise leeway, and same-set selection hazard.

### Resolution summary
| Topic | WS7 | WS2 | Resolution | Confidence |
|---|---|---|---|---|
| Reviewer sees dialogue | yes (tool path) | no (file-chat path) | both exist; record disclosure per exchange | high |
| Progress writer | adapt | redesign | redesign record, keep discipline | high |
| Citation check, ledger | adopt | adapt | adapt | high |
| Reflection | adapt | reuse | reuse; gate recall by promotion record | medium |
| Journal kinds | exchange events | artifact/decision/staleness events | union; one `seq` space | high |
| Units of work | `attempt`, `reopen` | self-correction turn, Reuse Record | union; `reopen` is a view | high |
| Independence | per-exchange block | per-decision declaration | nest; `revision_check` cannot raise level | high |
| Promotion | separate | merged | shared schema, separate policies | medium |
| Counter restart | not stated | restarts | confirmed from recorded run | high |

## Contribution record

- Identity: Workstream 7, Reference-Harness Inspector (Claude agent, model `claude-fable-5-1`), spawned by the coordinating agent. Start 2026-10-12 13:07 UTC; end 13:24 UTC.
- Package files read in full: `design_audit/agent_reports/00_coordinator_brief.md`; `START_HERE_Audit_and_Optimize_Prompt_EN.md` lines 88-141 (sections 4.3, 6); `02_Agentic_Doping_Reference_EN.md`; `07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md`; `agentic_doping_reference/SOURCE_MANIFEST.json` and `PROGRESS_SOURCE_MANIFEST.json`.
- `Agentic-Doping-snapshot` `0007ad104755aec56cbc2479db6cf68c0e05b237`: `AGENTS.md` 1-120; full reads of `orchestration/run_dir.py`, `dual_agent/loop.py`, `harness/skill_policy.py`, `core/task_state.py` 1-120, `evidence_ledger/{enums,models,ledger,leaderboard}.py`; partial reads of `dual_agent/reviewer.py` (190-240, 370-430), `dual_agent/harness.py` (1121-1140), `dual_agent/agent_harness.py` (650-672, 912-930), `dual_agent/proposer.py` (121-161), `web/server.py` (395-450, 955-1025, 1252-1290, 4179-4210), `web/client/src/App.tsx` (1930-1965, 2836-2890, 3106-3127, 3522-3548, 3783-3800), `web/client/src/ReportIterator.tsx` (120-180), `analysis/report_iteration.py` (262-297), `harness/memory.py` (1-60, 195-330, 360-460, 782-810), `orchestration/reflection.py` (1-157), `orchestration/recommend.py` (209-238, 615-632, 666-684, 736-760, 822-858), `core/llm_client.py` (342-440, 481-626), `schemas/ledger_record_v1.json` (1-60); greps across those files; `runs/rec_43273c9978/` manifest, progress head, and event-type tally; tests `test_dual_agent_harness.py` 240-275, `web/test_server.py` 33-90 and 572-600, `test_pipeline.py` 50-75, `test_i15_features.py` 1-45, and def lists of the memory, reflection, reviewer-boundary, and web tests; `sha256sum` of 17 files.
- `Agentic-Doping` `7cdf6591`: used only through `git log origin/main..HEAD`, `git diff --stat`, and `git diff -- dual_agent/loop.py` inside the snapshot clone.
- `deepseek-harness` `d7432673`: `README.md` 1-140; `AGENTS.md` 1-120; `BENCHMARK.md`; `benchmarks/AGENTS.md` and listing; Agent Notes `2026-06-11-microkernel-event-taxonomy.md`, `2026-06-14-session-persistence.md`; `docs/architecture.md` 1-120; `docs/subsystems/{core 1-90, session 1-80, session-projection 1-60, tools 1-70, jobs 1-50, subagent 1-50, goal 1-40, feedback 1-40, persistence 1-40}.md`; `packages/core/agent-loop/src/tool-calls.ts` 1-60 and grep; `packages/core/agent-loop/README.md` grep (116, 192, 198); `packages/core/agent/src/runtime-types.ts` 109-121; `packages/feedback/README.md` 1-25; listings of packages, tests, `snapshots/session`.
- `ARIS` `26b95cfa`: `AGENT_GUIDE.md` full; `skills/auto-review-loop/SKILL.md` 138-300, 940-960, 1116-1137 plus headings and grep; `skills/kill-argument/SKILL.md` 1-60 and grep; `skills/research-review/SKILL.md` headings and grep; `skills/meta-optimize/SKILL.md` 1-60; `skills/shared-references/{acceptance-gate 1-120, reviewer-independence full, evidence-precheck full, review-tracing 1-60, resumable-runs 1-60}.md`; `tools/{review_gate, evidence_check, iteration_log}.py` headers; `docs/{CODEX_CLAUDE_REVIEW_GUIDE 1-80, WATCHDOG_GUIDE 1-60, SESSION_RECOVERY_GUIDE 1-50}.md`; `README.md` 1055-1110 and grep; `docs/ARIS_INTRO.md` grep; tests `test_iteration_log.py` 1-60, `test_http_reviewer_review_gate.py` 1-50, def lists of `test_review_gate.py`, `test_evidence_check.py`, `test_run_state.py`, `test_auto_proceed_contract.py`; `mcp-servers/claude-review/server.py` def list; listings.
- `dgm` `a565fd2d`: `README.md`, `DGM_outer.py`, `self_improve_step.py` in full; `utils/evo_utils.py` 43-136; `swe_bench/harness.py` 1-60; `prompts/self_improvement_prompt.py` 1-80 and grep; greps of `coding_agent.py`, `llm_withtools.py`; `initial/metadata.json` summary; subset JSON element counts; listings.
- Tools: Bash with `cat`, `sed -n`, `grep`, `find`, `ls`, `wc`, `sha256sum`, `git log`, `git diff`, `git branch`, and short Python one-liners to count JSON records. No repository code executed, no servers started, no web access.
- Cross-review (17:10-17:25 UTC): read `design_audit/agent_reports/mas_architecture.md` in full (6,028 words); re-verified `core/llm_client.py` 139-152, `dual_agent/harness.py` 60-95 and 1121-1264, `dual_agent/agent_harness.py` 952-956, `dual_agent/loop.py` 101-110 and 166-174, `harness/memory.py` 308-311; recomputed the `progress_version` sequence of `runs/rec_43273c9978/job_events.jsonl` with a Python one-liner. The peer file was not modified.
- Wave 1.5 (17:14-17:26 UTC; verified intact 22:12 UTC after a session interruption), read-only under `/home/yiwei3_duke/anny/reference_repos/`: `hsi` `97a022b9a9c260c0498806fc9826ebf22e753ed9` — `README.md` full; `config.yaml`; `benchmark_config_goal/{balrog_babyai, balrog_babaisai_breakstop}/config.yaml` grep; `requirements.txt`; `.env` key names and value lengths only; `godel_harness_init/balrog_babyai/{harness.py 1-80, hooks.py, prompts.py, BOOTSTRAP.md}`; `godel_evolution_init/{select_seed.py 1-80, select_commit.py 1-80, select_best.py full, strategies/greedy.py 1-60}`; `src/react_loop/{state.py 60-177, archive_manager.py 1-60, agent.py 514-560 and 1120-1178 and 1419-1480, meta_evolve.py 716-740, framework_contract.md 1-60, git_version/controller.py 29-70 and EvolutionTracker head}`; `src/benchmark/balrog/adapter.py` 118-200; `src/benchmark/adapter.py` 162-275 and grep; `run_tests.py` 1-40 and 184-221; `main_final.py` grep; `paper/readme.md`; test-function counts; license search with `ls` and `grep` over all text files. `ace` `82709de050e1db6e6ef2f07bcb0393560b94992a` — `README.md` full; `LICENSE.txt` head; `pyproject.toml`; `.gitmodules`; `EXTENDING_ACE.md` headings; `ace/ace.py` 456-632 and grep; `ace/core/{curator.py 1-120 and 169-326, reflector.py 1-60 and 100-149, bulletpoint_analyzer.py 1-100 and 150-371}`; `ace/prompts/{curator.py 1-90 and grep, reflector.py 1-70}`; `playbook_utils.py` 96-175 and grep; `logger.py` grep; `eval/finance/run.py` grep. `HGM` `013872d95da978483f5b540e531db063d23890da` — `README.md` full; `LICENSE` head; `config.yaml`; `run.sh`; `hgm.py` 30-122 and 300-489; `hgm_utils.py` 36-153, 154-278, 279-330; `tree.py` full; `self_improve_step.py` full; `evaluate_agent.py` full; `utils/eval_utils.py` 13-22; `best_agent/README.md` and `self_evo.md` 1-30; `diff -rq` against the `dgm` clone and `diff` of `swe_bench/harness.py`; subset JSON element counts. Tools: `cat`, `sed -n`, `grep`, `find`, `ls`, `wc`, `diff`, `awk`, Python one-liners for JSON counts; no code executed; no web access; the three papers were not read.
- Not accessed: the ARIS technical report (arXiv 2605.03042) and the DGM paper (arXiv 2505.22954); their claims are not evaluated here. The Agentic Doping UI was not run; browser behavior is inferred from `App.tsx`. No test suite was executed.
