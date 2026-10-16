# MAS research workbench

Develop evidence-based research criteria, screen candidates and inspect the evidence behind each result.

## Start the workbench

```powershell
npm --prefix web/client ci
npm --prefix web/client run build
.\start_workbench.cmd -AllowOperations -Models var\primary\store\models_deepseek.toml -Config var\primary\store\mas.toml
```

Open `http://127.0.0.1:8769/`. Start at **Settings**, choose **New research** or **Use own data**, and describe the objective, required observations, hard conditions and preferences. Choose a candidate library and saved evidence collection, or import CSVs. English / 中文 changes interface text only.

The workflow connects task input, evidence preparation, CQA generation, review and refinement, frozen criteria, candidate assessment and ranking. Progress remains visible. Criterion history preserves actual changes and sources. Only qualified candidates receive ranks; missing, conflicting, failed and skipped assessments remain distinct.

## Retained studies

| Study | Surufatinib | Qualified | Candidates |
|---|---:|---:|---:|
| Comprehensive evaluation | 4 / 10 | 10 | 3,177 |
| Latest evaluation | 1 / 10 | 10 | 3,177 |

Both use mid-level settings and four workers. Their frozen criteria differ, so scores should be interpreted within each study.

- [Comprehensive CSV](design_audit/workbench_redesign_2026-10-16/final/wf_033db93e15fa4bb289c2e03606674f6b-snapshot2/candidates.csv) · [complete result files](design_audit/workbench_redesign_2026-10-16/final/wf_033db93e15fa4bb289c2e03606674f6b-snapshot2/)
- [Latest CSV](design_audit/fresh_browser_2026-10-16/results-snapshot2/candidates.csv) · [complete result files](design_audit/fresh_browser_2026-10-16/results-snapshot2/)
- [Current presentation, speaker notes and score details](design_audit/workbench_presentation_2026-10-17/)
- [CSV input guide](design_audit/workbench_usability_2026-10-16/CSV_GUIDE.md)

The latest study developed **0 → 6 task requirements → 1,917 → 53** working records. Its evaluation uses **18 core decisions** (one hard condition and 17 preferences), plus 13 context entries. Surufatinib passes the oral condition, has direct observations for all five required targets and direct preference coverage of **10/17**. Its score is **0.7592592593**. The remaining 3,167 candidates are pending evidence. Human measured oral F% and Tmax remain missing.

Click **Score** for values, comparison points, weights and contributions. Evidence is grouped by source; exact duplicate findings can be expanded into individual records. Collection names, descriptions and topics are display metadata and do not change research results.

## Storage

Scientific records and API credentials are local and excluded from Git. Page queries use a separate rebuildable cache. The user-requested 17 October cleanup retains the two studies above, criterion evolution and the source records required for their final results. Obsolete study runs, drafts, test outputs and large backups are removed. Temporary previews and presentation build files should be removed after delivery; avoid repeated full-store backups without a concrete need.

The [storage cleanup report](design_audit/storage_cleanup_2026-10-17/REPORT.md) records the reduction from 23.49 GiB to 7.83 GiB, retained-result verification and the small read-only residue that could not be removed.

## Development

Python 3.11+ is required. Install with `pip install -e ".[dev]"`. Run relevant offline checks with `pytest`; network tests are marked `live`. Python source is in `src/mas`, the React client in `web/client/src`, and reusable test code in `tests`.

The [system design](design_audit/optimized_design.md), [architecture decisions](design_audit/architecture_decisions.md), [criterion history specification](design_audit/iteration_and_provenance_spec.md), and [ranking specification](design_audit/leaderboard_spec.md) describe the research mechanisms. These small design documents and test source code remain part of the project.
