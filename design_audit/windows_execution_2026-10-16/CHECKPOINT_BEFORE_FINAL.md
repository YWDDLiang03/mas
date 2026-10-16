# Current execution checkpoint — 2026-10-16

The user now treats B recovery and reduction count as soft targets. Keep meaningful criteria, improve A with authentic evidence, and complete the Windows browser workflow at mid settings. Latest steering: fix content navigation, simplify product language, use English by default with a persistent English/Chinese switch. Chinese is UI presentation only; retain research and provenance in English and preserve original source text.

## Current real workflow

- Store: `var/primary/store`; current English/Chinese UI service `http://127.0.0.1:8768` (parent PID 2768, `var/primary/workbench-8768.*`). Port 8767 still owns the running reduction process and must stay alive until it ends. Port 8765 belongs to the existing VSCode forwarding setup; leave it alone.
- Driver and checkpoints: `scripts/workbench_acceptance.py`, `var/acceptance-mid/state.json`. New operations default to 8768; `check` follows each job's recorded origin (the existing reduction is on 8767). Terminal jobs are retained across service replacement. `--base-url` can explicitly select the local service.
- Actual control channel so far: **local workbench HTTP integration**, not GUI clicks.
- Settings: standard preset, search/textbook mid, breadth 4, depth 2, 40 full documents, 4 workers, USD cap 10, autonomous, ranking coverage 0.5, mandated eligibility 1.0. Configuration hash: `e2c30f795622fa7bfbf7754d1b8a5b89282e61e1abbd98672cf425686260c31c`.
- Fresh inherited task: `task_01M50Q5EZE12GGDES5QNWR0JQX`; complete 3,177 candidate scope and 93 registered criteria, with 4 prior unresolved pool items retained.
- Registered reduction job: `job_312fd67056eb6cbd`, PID 8904; run `run_01M50Q7SWTRAM3B7E1MHV0D8V7`. It was still running at the last checkpoint. Consult `var/acceptance-mid/reduction-progress.json` and the live operation endpoint for current state.
- Input scope/configuration proof: `var/acceptance-mid/configuration_and_scope_proof.json`.
- Reduction implementation archive: `var/provenance/mid-acceptance-reduction/frozen_source.zip`. Later source fixes do not change what this running process loaded.

## Repairs completed or in progress

- Required task bindings: future reduction protects the original task anchors. `derivation_run.required_binding_audit` detects any original binding lost by an older reduction. `correct_required_bindings` restores the full affected parent set append-only after a terminal run, with source hashes and author identity preserved. Never call it while the current run is active. The five required receptor bindings were all active before promotion; verify again at completion and before freezing.
- Model accounting: subsequent processes now aggregate schema repairs, retain per-attempt trace, honor repair budget refusal, and preserve known costs on exceptions. Historic requests without full token accounting remain historic records; do not relabel them as complete totals.
- Navigation, language and three real page failures are fixed and deployed on 8768: task-less anchor links, unknown run-purpose labels breaking the home page, and eager Review route computation causing delays. Six main pages plus active progress, historical board and candidate evidence return HTTP 200. English default, Chinese persistence and switching back to English passed real HTTP checks; actual GUI clicks remain unverified. See `ui_navigation_language_verification.json`.
- Settings were saved again through 8768 at mid, and the current inherited task remains selected. The configuration hash is unchanged. New UI sees the reduction running on 8767 and blocks duplicate research operations for that task. Browser open was requested with `open_in_codex` and returned `queued`.
- All agents have stopped editing source. Current prospective source digest: `1bf12110e765777fd84ec06897f3775b2e440e3597d3204c83615faff2531bbb`; archive `var/provenance/mid-acceptance-sweep/1bf12110e765/source.zip` (archive SHA256 `39d1a089400c5a891a3dfb9673705ecbf2db1baa492b6312faf6935b9cf9d628`). No new measurement profile is registered yet; verify source identity again when freezing.
- An offline frozen-cell leaderboard reconstruction script is being prepared. Run it once after the final new snapshot, without model or network calls.

## Continue in this order

1. Use the updated 8768 UI for remaining verification and operations. Preserve the live reduction process on 8767 and its original implementation archive. On a fresh permitted browser-control turn, perform actual browser interactions; do not substitute HTTP for GUI evidence.
2. Wait for an actual terminal reduction state, recording its result and failure/unresolved status accurately. Audit original task bindings against the run input manifest; if altered, append the supported correction before a new freeze. Count active registry, pending/backlog, retired/merged and scoring separately; no numeric quota.
3. Attach the already verified supplement `art_ae77c0685a78` to the unfrozen new task, then freeze the final settings, source identity and rule set. Verify all five required receptor bindings are represented.
4. Execute the full new 3,177-candidate run and retain unknowns, eligibility, coverage, actual expense estimates and replay provenance. No imputation is currently enabled.
5. Export all 3,177 rows from one fixed snapshot; compare complete JSON/CSV identities and replay scores, coverage, eligibility and positions offline. Inspect both genuine supplement cell traces.
6. Finish real browser navigation/settings/task/run/board validation when supported. HTTP evidence and GUI evidence must stay explicitly separate. Update the final report and manifest after the true final results exist.

## Preserved reference results

- Original Windows A: task `task_01M50JQYYQAMPBQTQ0N8YNQT22`, run `run_01M50KR3WM3ZBFKF6Z83BW77EX`, snapshot `lb_task_01M50JQYYQAMPBQTQ0N8YNQT22_1`, profile `art_dc699649c378`. Surufatinib is 5/50 rankable out of 3,177, preference coverage 8/11, required receptor coverage 4/5 (CSF1R missing), provisional. All 34,947 cells completed. Keep this reading unchanged.
- Supplement: 2024 Lin et al., Communications Chemistry, DOI `10.1038/s42004-023-01084-0`. Verified WT CSF1R 5 nM and WT FGFR1 34 nM; mutant measurements excluded with reasons. Source selection is exploratory after a known evidence gap. See `supplement_source_2024.json`. One actual reading call already completed; do not repeat it.
- B: original 4/11 and inherited descriptive 1/11 are retained. Consistency audit found changing mapping interpretations; no further recovery optimization is required. Do not read evaluator-only contents.

## Browser/tool state

The browser and computer-use skills have been read. IAB bootstrap reports no discovered backend. Native Computer Use stopped this turn after it could not establish the current browser URL. A subsequent shell Chrome launch was rejected by automatic approval with only `blocked by policy`. No GUI input followed those stops. User debugging authorization is present; it does not alter these tool-enforced limits. Continue independent code/HTTP work and use a supported browser tool on a fresh permitted turn; never claim HTTP requests were GUI clicks.

## Coordination

- `windows_runtime`: UI, navigation, English/Chinese presentation, cost/status rendering.
- `inheritance_case`: protected bindings, CLI audit/correction and freeze guard; reduction performance analysis.
- `goal_policy_audit`: offline numerical leaderboard reconstruction.
- `rank_evidence`: verified supplement already complete.
- `isolated_evaluator`: B consistency/access audit complete; no further B work.

API writes require same-origin `Origin` and the `X-MAS-Operation-Token` rendered as JavaScript `const token=...`. Keep it out of logs. Secrets remain outside the repository in the user's personal configuration directory.

## Browser connection restored in the current continuation

The newly available `browser:control-in-app-browser` skill succeeded. The persistent Node browser binding is `masBrowser`, created through `setupBrowserRuntime()` from `C:/Users/admin/.codex/plugins/cache/openai-bundled/browser/26.1007.71326/scripts/browser-client.mjs`; agent handle `masBrowserAgent`. Selected browser is IAB ID `2`. `masTab` is existing tab `2`, provider tab `408d4f28-5ecb-402e-b7db-18d5cd5f72bc`, serving 8768. Reuse these bindings; do not bootstrap/select again merely because the turn changes. Complete browser documentation, its previously truncated Accessibility section, local-web-development and screenshots guidance have all been read. The old unavailable Atlas bootstrap and native Chrome stop are no longer the current browser path.

Real GUI checks now include Settings save at mid, English/Chinese switch and persistence, task selection, all six main navigation pages, current run progress and Criteria search (CSF1R -> 12 visible matching rows). `var/acceptance-mid/browser/gui_verification.json` records the actual checks and detected failures. A screenshot is saved there. UI agent is fixing the actual task-then-language selection reset, mixed-language toast, noisy field keys, active-run Prepare button and task-scoped Review. Wait for its stable notice, restart only the idle 8768 frontend, then `masTab.reload()` and recheck the affected GUI sequences. 8767 still owns the live reduction. The current prospective source archive will be superseded by these UI fixes; no final profile has been created.

At 22:33:31 UTC the reduction entered refine iteration 3. Goal-policy agent found a preliminary measured-route review shortlist: MW `q_01M50Q5G99W300W11M0RPXW5PH`, logP `q_01M50Q5G9ARXZJCRZQNBPC29D8`; TPSA already has no open item. Promotion may change these refs, so re-check after terminal state before any paid adjudication. No new review or supplement attachment has been submitted yet.
