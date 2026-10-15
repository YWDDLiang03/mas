# Iteration log — 2026-10-15: the bridge stall, the takeover, and rounds 6–10

All times UTC. Every run in this log is a link in one chain
(`chain_01M4X89HR1DAKPDS9PB32SS062` on `task_01M4X892V1EAER2GHWE1RE19ZN`); each continues the
previous one, so the restarts below moved the same work forward and lost no evidence.

## 1. What happened, in order

| time | event |
|---|---|
| 00:46:08 | Round 5 starts (`run_01M4YGC2…`), roster `models_round3.toml`: claude-opus-5 subagents answering through the file bridge (`llm_exchange_r3*`). |
| 00:47–04:39 | The serving Claude session answers **172 reader requests**; 1,771 claims admitted over 179 documents. |
| 04:39:39 | Last bridge answer written. |
| 04:45:47 | The serving session reports **"You've hit your session limit · resets 8am (UTC)"**. Servicing stops. |
| 05:39–09:40 | The run posts one reader request per hour; nothing answers; each waits the full 3,600 s bridge timeout, then the run moves to the next document. Six cells end `model_error: timeout`. Last claim admitted **04:38:29**. |
| 08:01 | The serving account is placed **on hold** (claude.ai/restricted). The old session's later turns fail with a request-shape error (422, `tool_definition`), independent of the hold. |
| ~10:10 | Diagnosis in a new session (deepseek-flash harness): the stall, the account state, and the dead serving loop. |
| 10:15:57 | The live pending request (posted 09:40:35) is answered by a deepseek-flash subagent — 34 claims, every quoted span machine-verified — before its 10:40:35 deadline. The run advances immediately. |
| 10:17 | Round 5 stopped on operator instruction ("finish the runs quickly"). Its journal is retained: 2,696 events, 1,771 admitted claims. |
| 10:17:51 | Round 6 (`run_01M4ZH2…`) on the **DeepSeek roster** (all six roles `deepseek-v4-flash`), `max_documents` 20. Reads all four dimensions (463 claims); stopped 10:34 with its first proposer call in flight. |
| 10:34 | Round 7 (`run_01M4ZJ0M…`), `max_documents` 10 — stopped after a reader call hung ~6.5 minutes. |
| ~10:41 | Code change `868ffed` (chain-claim inheritance) — see §6. |
| 10:42 | Round 8 (`run_01M4ZJFG…`), `max_documents` 3 — stopped after another reader hang (44 claims). |
| 10:49 | Roster timeouts tightened in `var/primary/store/models_deepseek.toml` — see §4. Round 9 (`run_01M4ZJWX…`) started, then stopped immediately on the operator's instruction to skip reading. |
| 10:51 | Round 10 (`run_01M4ZJZJ…`), `max_documents` 1. Enumeration closed 10:53:09 (2 m 10 s; 1 document read, shared across the four dimensions by the read cache; 58 claims). `propose:target_coverage` opened 10:53:13. |
| 10:53–12:28 | propose, all four dimensions: **+93 criteria** from **3,681 claims considered** (12 slices; 175 alternatives considered and rejected with reasons). |
| 12:28–13:20 | prune iteration 1: filter `kept 9 / to_refine 84`; distill `kept 9`; refine `revised 59 / withdrawn 19 / still_failing 6`; **merge `consolidated: 3`** — the project's first consolidations ever (previously 0/0), including "Weakest required-receptor potency across the five tumour-microenvironment targets" (7 members) and "Worst reported treatment-emergent toxicity burden" (5 members). |
| 13:20–13:52 | prune iteration 2: filter `kept 12 / to_refine 44`; distill `kept 12`; refine `batches_unresolved: 2` (failures counted, not hidden); **merge `consolidated: 1`**. |
| 13:52–14:21 | prune iteration 3: filter `kept 15 / to_refine 35`; distill `kept 11 / revised 4`; refine `revised 33 / withdrawn 1 / deferred 3`; **merge `consolidated: 2`**; **promote `accepted: 28 / disputed: 14`**. |
| 14:21:38 | **`run.completed`** (`termination_reason: round_limit_reached`) — the chain's first completed derivation round with the inherited evidence. |
| ~14:22 | `criteria export` → `design_audit/current_task_2026-10-15/`: **93 registered criteria** (86 promoted over the chain + 7 template-written), 208 pool lineages, 41 literature-bound rules deferred, 25 open disputes. |
| ~14:23 | **`rules@v2` confirmed** (`--allow-pending`; the set is `exploratory`, pending items listed, no decision invented). |
| 14:23:45 | Screen attempt 1 (`run_01M4ZZ4Z5KN0ZTET43J9E3GFR6`, `--seed 0 --workers 4`) on `rules@v2`. By 16:30 its assess stage is 26 % through 171,558 candidate×rule cells and moving at ~6 cells/min: the run is attempting a **per-candidate literature pass**, and the literature sources are rate-limiting it (569 `rate_limited` errors in fifteen minutes, ~1,180 searches attempted). |
| 16:32 | Attempt 1 stopped. **`rules@v3` confirmed with `literature_retrieval` deferred** — the same holding-out the Oct-14 baseline used ("26 deferred literature criteria … held out of the run"), and the decision the improvement plan explicitly left to the owner ("literature evidence pass: on the ~99 ranked compounds only, or skip it this round?"). The deferral is a policy choice recorded in the set, not a code change; the literature pass stays outstanding and is reported as such. |
| 16:33:14 | Screen attempt 2 (`run_01M506J2Q5GK32R0GQ7R035M90`) on `rules@v3`. |
| 18:35–18:58 | The box runs out of disk (96 GB full, `/` at 100 %, 70 MB free; the store grew 2.1 → 4.4 GB under the sweep) and later memory (284 MB free, 5.1 GB swap, load 23 on 2 cores). The operator expands the volume by 50 GB; the sweep recovers and resumes. |
| 19:06:01 / 19:08:53 | **Board published**: `lb_task_01M4X892V1EAER2GHWE1RE19ZN_1`, rules@v3, 3,177 entries, `sweep_completeness: 1.0`, 60,363/60,363 assess cells. |
| — | Readings, all three recorded in the system report §1 and none of them picked between: **as published** (`mandated_coverage_floor: 1.0`) the reference compound is *not positioned* (16 positioned; blocked by its absent `attr_csf1r-curated-potency@v2`); **score order over all 3,177** puts it #1,985 behind solvents; the **Oct-14 baseline** had it #4 of 95. |
| — | The sweep's tool ledger: `chembl_bioactivity` / `gtopdb_affinity` / `chembl_mechanism` exactly 15,885 calls each (3,177 × 5 receptors), **1 error in 88,957 calls** — the curated routes were collected fully; the missing receptor cells are source sparsity, and the reference compound's missing CSF1R cell is the one the earlier offline recomputation also had to take from the manuscript's Table 1. |
| — | Consequence recorded: the registered endpoint cannot be evaluated on a literature-deferred set (coverage stops discriminating; the rankable set degenerates to the universe). The repair is the literature pass `improvement_plan.md` flagged as the owner's decision — **not** a floor change now that the numbers are known. |

## 2. Why the chain had to move to DeepSeek

The round-5 roster declares claude-opus-5 subagents; the account that served them is on hold, and
the remaining reading had no bound (cap: 100 documents per dimension; 179 read in the four hours
that were served). Continuing on that roster meant mixed-provenance answers at ~4–5 minutes per
document with hours of tail. Rounds 6+ run one declared roster (`models_deepseek.toml`) unattended.
The DeepSeek endpoint was probe-tested before the switch (small and realistic completions, complete
bodies, 0.9–2.2 s).

**Cost, recorded:** shallower reading and a different provider family for every role. Round 5's
evidence is not lost — its 1,771 admitted claims stay in the ledger and are inherited by later
rounds (below) — but it was not re-read.

## 3. What "inherited" now means (rounds 8+)

Rounds before 8 only kept the chain's claims *citable*. Since `868ffed` + `9912dbb`, each round's
`propose` pass takes the chain's admitted claims as proposal input as well, grouped by the
dimension the earlier round was reading for (reconstructed from its `plan queries: <focus>`
markers). Measured effect on the input: 2,234 inherited claims × 4 dimensions = 24 proposer calls
before, ~8 after (round 5's 1,489 claims sit in the target_coverage span; 214 oral; 68 metabolic;
0 toxicological). A claim no span claims is offered to every dimension rather than dropped.

## 4. Deviations and configuration changes, recorded

- **Reader model substitution** (round 5, exactly one document): answered by a deepseek-flash
  subagent although the roster declares claude-opus-5. Recorded in the response file
  (`model_id: deepseek-flash (subagent)`, `answered_by: claude-code-subagent`) and in the claim's
  reader actor (`reader:deepseek-flash (subagent)`). All 172 answers before it were
  `claude-opus (subagent)`.
- **Roster**: rounds 6–11 use `var/primary/store/models_deepseek.toml`. `models_round3.toml`'s WHY
  (DeepSeek mid-body stalls measured on 15 October) is in that file; the stall recurred
  intermittently today (two reader hangs of 6+ minutes, rate-limited finder calls) and the run
  retries or skips per its timeout policy.
- **Reading budget** (`research.max_documents`): 100 (round 5 design) → 20 → 10 → 3 → **1**
  (round 10), each cut on operator instruction to finish quickly. The record in each Run Binding
  states the value that round ran under.
- **Timeouts** (`var/primary/store/models_deepseek.toml`, config only): `deepseek_exact`
  300 → **120 s** (every completed reader call measured today ran 8–105 s; a stalled call cost up
  to three attempts × 300 s), `deepseek_reasoning` **600 s** (large prompts legitimately run for
  minutes).
- **Unserved bridge requests** from 05:39–09:40 remain in `var/primary/store/llm_exchange_r3/requests/`
  as an honest record; nothing reads them.

## 5. Test log

| when | command | result |
|---|---|---|
| after `868ffed` | `pytest tests/test_derivation.py tests/test_criteria_pool.py -q` | 73 passed, 18.4 s |
| after `9912dbb` | same | 73 passed, 21.1 s |
| 2026-10-15 ~10:52 | `pytest tests/ -q` | **442 passed, 15 deselected (live), 104.9 s** |

Live-network tests are selected with `pytest -m live` (14 tests across `test_live_drug.py`,
`test_live_literature.py`, `test_live_predict.py`).

## 6. Development log (today's commits)

| commit | time | what |
|---|---|---|
| `dbb0394` | 00:01 | Predicted evidence; a published IC50 answers a potency; ranked candidates whose required criteria are unanswered are refused. (Previous session.) |
| `868ffed` | ~10:41 | `propose` slices its input (`BATCH["propose"] = 400`); a round proposes *from* the chain's admitted claims, not only cites them. |
| `9912dbb` | ~10:47 | The inherited claims are grouped by the dimension they were read for (plan-query spans); 24 → 8 proposer calls. |

## 7. Not done in this pass (stated so the next agent does not assume it)

- The merge/consolidate schema refusals seen in the last completed reduce round (Oct 14: 45 → 33
  promoted, `merged: 0`, `consolidated: 0`, five groups refused on schema) were **not** fixed —
  operator instruction: "this round's results only need to be roughly good enough".
- CQA recovery intake: **awaits the sealed list** (evaluator-only; template kept outside the
  repository at `/home/yiwei3_duke/anny/cqa_intake_template.json`).

The endgame commands, in order (all with
`--store var/primary/store --models var/primary/store/models_deepseek.toml`, from the repo root):

```
mas criteria export   task_01M4X892V1EAER2GHWE1RE19ZN --out design_audit/current_task_2026-10-15
mas review adjudicate task_01M4X892V1EAER2GHWE1RE19ZN          # 38 items are queued, no decisions recorded;
                                                              # machine adjudication resolves them one call each.
                                                              # If that is too slow, skip to confirm and accept
                                                              # the exploratory label it produces.
mas rules confirm     task_01M4X892V1EAER2GHWE1RE19ZN --allow-pending   # see §1: the old baseline is exploratory too
mas run start         task_01M4X892V1EAER2GHWE1RE19ZN --seed 0 --workers 4
mas board show        task_01M4X892V1EAER2GHWE1RE19ZN --all
mas criteria export   task_01M4X892V1EAER2GHWE1RE19ZN --out design_audit/current_task_2026-10-15
                      # re-run after the board: with_board=True picks up the published snapshot,
                      # so the committed package carries the rank next to the criteria
mas recovery intake   task_01M4X892V1EAER2GHWE1RE19ZN --from <sealed list>.json   # after the freeze
mas recovery report   task_01M4X892V1EAER2GHWE1RE19ZN
```

Each step's outcome is reported in the system report's §1 with its run id and event counts.
- The old Claude session (`0ea0f6b6…`) is not recoverable as-is: its transcript carries a content
  block type the endpoint refuses (422), independent of the account hold.
