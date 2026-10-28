# Current interface and results

[中文](zh/current-status.md) · [Tutorial](tutorial.md) · [Presentation](presentation/README.md) · [Screenshot manifest](assets/current/manifest.json) · [Verification data](reference/current-ui-validation.json)

The screenshots on this page were captured on **28 October 2026** in the Windows browser workbench using application version 1.1.0, source commit `c614ac4`. They show the retained public study through the current interface. The documentation refresh inspected the saved results and exported all candidates; it started no new research run.

## Current study results

| Item | Current value |
|---|---:|
| Candidate library | 3,177 |
| Eligible | 10 |
| Evidence incomplete | 1,305 |
| Excluded | 1,862 |
| Eligibility requirements | 6 |
| Scoring criteria | 17 |
| Criteria shared by eligibility and scoring | 5 |
| Unique evaluation criteria | 18 |
| Contextual observations | 13 |
| Retained items outside this evaluation | 22 |

The six eligibility requirements comprise oral administration and direct quantitative observations for five required targets. These five target criteria also contribute to scoring: **6 + 17 − 5 = 18 unique criteria**. The retained set contains 53 items; 31 are assessed, including 13 contextual observations.

Surufatinib ranks first among the ten eligible candidates. Its score is 0.7592592593, averaged over 15 available scoring values. Direct evidence coverage is calculated separately as 10/17 (58.8%). Five ADMET predictions contribute to the score; the ten direct values comprise five target observations and five structure-derived values.

In this case, the 1,305 Evidence incomplete candidates have partial support for the required evidence. The 1,862 Excluded candidates have no usable admission support after the required assessments are complete. [Decision definitions](reference/decision-language.md) explain the task-defined rules, including exclusion after a confirmed condition failure.

![Current candidate groups and leaderboard](assets/current/candidates.jpg)

The [full browser export](../examples/oral-multitarget/latest/selection/workbench-export.csv) contains all 3,177 candidates. Its `selection_decision` field matches these groups. Earlier raw fields remain in the export for tracing the recorded snapshot; use the current selection field for reporting.

## Task, progress and evidence

The overview shows the selected question, completed work and result. **Research options → New study with this setup** opens an editable task with the saved library and evidence collection. The new study starts from an empty criterion set.

![Current overview](assets/current/overview.jpg)

![New-study form before submission](assets/current/new-study.jpg)

Expand **Workflow & run details** to see the saved stage record. The displayed study has completed 8/8 stages. Its recorded elapsed time is about 3 hours 32 minutes and estimated model cost is USD 4.2101472 against a USD 5.50 cap. These are saved study measurements. The current Settings screenshot configures subsequent work at Medium, four workers and a USD 10 cap.

![Completed workflow stages](assets/current/progress.jpg)

![Settings for subsequent work](assets/current/settings.jpg)

The Criteria page shows expansion and refinement alongside the final roles. A criterion opens its definition, changes, lineage and sources.

![Criteria, shared roles and evolution](assets/current/criteria.jpg)

The score panel separates eligibility, scoring contributions and evidence coverage. Evidence details connect findings to the candidate and criterion that use them. The library groups findings by source; preserved excerpts and conditions accompany the source links.

![Current score breakdown](assets/current/score-details.jpg)

![Finding linked to the candidate, criterion and source](assets/current/evidence-fgfr1.jpg)

![Literature grouped by source](assets/current/evidence-library.jpg)

Further views: [Evidence selection](assets/current/evidence-selection.jpg), [expanded findings](assets/current/evidence-findings.jpg), [criterion lineage](assets/current/criterion-lineage.jpg), [criterion changes](assets/current/criterion-changes.jpg), [candidate evidence](assets/current/candidate-details.jpg), [coverage calculation](assets/current/score-coverage.jpg), [Evidence incomplete](assets/current/candidates-incomplete.jpg), [Excluded](assets/current/candidates-excluded.jpg), [Chinese interface](assets/current/candidates-zh.jpg) and [CSV preview](assets/current/csv-import.jpg). The CSV preview uses two explicitly synthetic carrier records and was checked before import.

## Current response measurements

Measured on Windows with Python 3.14.2, using the restored public study after the query index was ready. Each resource received 20 serial local HTTP requests. Times include the response and JSON decoding; cold indexing, browser painting and research/model execution have separate durations.

| Read request | Median | P95 |
|---|---:|---:|
| Overview | 43.11 ms | 48.39 ms |
| Criteria, page size 50 | 176.41 ms | 198.53 ms |
| Eligible candidates, page size 50 | 4.24 ms | 4.86 ms |
| Literature sources, page size 20 | 5.49 ms | 6.41 ms |
| Candidate score details | 5.32 ms | 6.36 ms |

The [verification record](reference/current-ui-validation.json) contains the routes, sample counts, candidate totals and CSV hash. The [screenshot manifest](assets/current/manifest.json) records each image's source URL, capture time, dimensions and checksum. Dated release notes retain their original validation history and link here for the current display.
