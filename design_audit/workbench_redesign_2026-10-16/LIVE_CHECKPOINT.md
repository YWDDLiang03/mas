# Live implementation checkpoint — 2026-10-16

Work remains active. **No final scientific success or production replacement yet.**

## Current execution

- Repo: `C:/Users/admin/Desktop/ai4med/mas-final-goal`.
- Preview port **8770**, parent PID **19484** (verify child before stopping), logs
  `var/primary/workbench-8770-v10.log/.err`.
- Loaded backend **1cd1f401bf2d21f9a0a2d54f2fce33da30e49ad4bb1f5cb3c066e46c7f7b1927**;
  immutable archive `var/provenance/workbench-v2/1cd1f401bf2d21f9`.
- Current UI **index-CJ7O9ore.js** (one later frontend SSE enrichment fix; backend unchanged).
- Workflow **wf_033db93e15fa4bb289c2e03606674f6b**, task
  **task_01M51AQ0JK0MYN47806ZD5XS1B**, title **Oral TME evidence study**.
- Current screening run **run_01M51NWNGBK6EY7AAC4GZEQBVC**, rules **rules@v2**:
  **24 enabled = 1 hard + 22 preferences + 1 context item**. Registered 43;
  deferred 19; unregistered unresolved pool 11. No disputed rule may score.
- Reused **28,246** complete unchanged cells from the stopped first evaluation.
  Current total planned cells **76,248 = 3,177 × 24**. Let this finish.
- Workflow estimated model spend **3.8478801 / 9.67 USD**; previous two stopped
  debugging workflows **0.3239793 USD** excluded from that number. Session ceiling USD10.
  Re-evaluation preserves accumulated budget, original CQA and fixed fact manifest.

## Important completed corrections

- CQA completed: 0 → 6 task bindings → 1,807 (1,801 raw proposals + 6 bindings)
  → 54 current entries (43 registered + 11 unresolved pool proposals). First filter
  removed735, first refine reached185, first merge106; three rounds completed.
  Derivation `run_01M51DNTG28TNJ16JBMNBBZWFB`, record `art_2dafe5ea2f92`, retains
  original backend210c6fe3. No new literature/full-text reading or old59-rule inheritance.
- Scoring execution guard defers7 preferences without executable comparison/order,
  plus2 multi-target composites whose definitions require grouped medians/spread
  while executor only pooled raw observations. Independent5target anchors retained.
- LD50 log reciprocal direction corrected via actual GUI to lower_better v2, with
  old version and reason preserved. It remains pending under current strict review.
- Finished unresolved reviews are reusable receipts; original duplicate paid review
  requests/fees remain. DeepSeek thinking adjudications now start with24k output room
  (same prompt/model/schema/totalbudget); old4k traces still recover exactly.
- Criteria/ledger/cited-claim SQL filtering preserves actual records and order,
  approximately4–9× faster on measured real-task reads.135 related tests passed.
- Registered history now displays real supersedes Before/After and revision reason;
  actual GUI verified LD50v1→v2. Pool exact versions/parent links/Added6 already verified.
- First evaluation **run_01M51MS4KW71HX2FEMTPJ01JHA** was stopped before publication:
  legacy trigger-table admission let4 explicitly unresolved prefs score. It retained
  **34,131 cells** (1,176 complete29cell members +1 member27cells), no snapshot.
  Diagnostic `var/workbench-v2-acceptance/disputed-freeze-diagnosis.json`.
- New qualification-first measurements strictly defer open/disputed reviews; legacy
  profile reads unchanged. Source/threshold/weight values never adjusted to get A.
- MWv1 mistakenly used ADMET molecular_weight/predicted although definition is a
  computed physical descriptor. Fixed PubChem projection contains3,084MW rows and
  matches original binding digest;1,136/1,177 partial members had exact saved rows.
  Root recorded MWv2 property_estimate/MolecularWeight/database_entry/derived with
  original<=500,unit,direction,bound_support unchanged. Its threshold review remains
  unresolved, therefore MWv2 is deferred rather than automatically scored. Evidence:
  `var/workbench-v2-acceptance/molecular-weight-route-revision.json` and
  `mw_existing_only_diagnostic/REPORT.md`.
- Workflow **Evaluate saved criteria** command retains derivation/factbank/spend and
  creates new freeze/run, saving prior evaluation metadata. Completed cells from
  terminal partial sweeps may be reused only with identical evidence/policy/ref
  contracts; skips/errors/changed refs are recomputed.32 integrated tests passed.
- Default rank policy remains **direct support / total applicable preference weight**,
  including prediction-only preferences in denominator; floor0.5 unchanged.

## Browser handles and actual checks

- Existing browser runtime **masBrowser**; use **masStableTab** (tab4) now.
  Old **masPreviewTab** (tab3) landed on a native data-URL error page during restart;
  its controls were blocked by browser URL policy. Do not use it. New tab4 opened
  the same healthy authorized localhost UI. Do not rebootstrap/read browser docs.
- `masEvidenceFs` is fs/promises. `masViewport` belonged to oldtab3; acquire tab4's
  viewport capability for new narrow tests. `.goto`, `.reload`, `.screenshot`,
  `.ax.get('state',{disableDiffing:true})`, supported semantic Playwright all work.
- EN/中文 uses getByText exact, not checkbox role. Native details uses getByText
  exact summary including count. Close detail drawer before interacting behind it.
- New GUI Evaluate saved criteria initially vanished because SSE replay at equal
  updated_at erased bootstrap-derived fields; upsert now merges old+event. Reload
  and actual click succeeded; this is the current run. No source backend changed.
- Completed: Settings(mid/mid/4), custominput/draft/Start, zero-CQA entry, pause/
  resume/stop/restart, CQA stages/search/page persistence/parentv1 links, true v1-v2
  diff/reason, source quote English while UIChinese,390/760px earlierlayouts.
- Candidate verdict buttons now filter/focus actual supporting and counter-evidence
  cards; completed progress rail is compact. Both need real final-result GUI checks.
- Screenshots and evidence in `var/workbench-v2-acceptance/browser/`.

## Remaining required delivery

1. Let current actual run finish; inspect real Surufatinib qualification/rank,
   eligible/rankable counts, hard/required-target/direct-preference coverage and gaps.
   Goal: genuine hard pass + qualified top5. Never loosen rules/floor or fake data.
2. Final GUI: full candidate groups/search/page/snapshot/criterion source click,
   CSV button, narrow layout, English/Chinese; inspect Pending reasons and final24
   evolution count. Report any true data gaps; no new papers this run, no B retest.
3. Run `scripts/accept_workbench_run.py` first on completed workflow (50requests/type
   and isolated query-cache rebuild/source/API parity); then `export_workbench_run.py`
   for complete CSV/JSON/CQAhistory/snapshot/Suruf/costs. Exact CLI args in scripts;
   defaultbase8770, storevar/primary/store. Output under final/ and var acceptance.
   Exporter now uses detail_ref and semantic phase attribution before overlapping
   resumed wall-clock windows. Add previous0.3239793 separately to session fee report.
4. Save latest frontend-only archive separately (do not overwrite backend archive),
   complete final report and README link. Tests already passed remain valid.
5. Replace **8769** only after preview acceptance; verify owned oldprocess and idle
   legacy operations; stop8770 to avoid two cachewriters. **Never stop8765** (VSCode).
   Open production result in actualbrowser, verify oldlinks preserved, keep archives.
6. Final Chinese response with actual scientific result, validation, cost and
   clickable report/CSV/JSON/UI. Do not claim this checkpoint itself is complete.

All agents currently completed. No source edits should be made while this run is
active unless preparing an unapplied patch. No commit/push requested. Secret is
outside Git; never print it. Initial5.5GB backup remains in
`var/backups/workbench-redesign-20261016/`.
