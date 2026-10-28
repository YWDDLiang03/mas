# Oral multi-target research example

[Step-by-step tutorial](../../docs/tutorial.md) · [中文教程](../../docs/zh/tutorial.md) · [Criterion comparison guide](../../docs/reference/cqa-comparison.md)

This directory contains the frozen export from the latest completed study. The latest study begins with an oral multi-target objective, develops and refines criteria from saved evidence, checks the recorded compound library, and links the final ranking to its rules and source observations.

| Study | Surufatinib rank | Score | Qualified | Full candidate export |
|---|---:|---:|---:|---:|
| [Latest](latest/results/) | 1 | 0.7592592592592593 | 10 | 3,177 |


## Start with the latest saved result

1. Read [task.json](latest/results/task.json) for the exact objective, five required targets, oral constraint, disclosed reference candidate and bound inputs.
2. Read [report.md](latest/results/report.md), [workflow.json](latest/results/workflow.json) and [overview.json](latest/results/overview.json) for the run, estimated cost and saved snapshot history.
3. Inspect [cqa.json](latest/results/cqa.json), [stages.json](latest/results/stages.json) and [source-cqa-history.json](latest/results/source-cqa-history.json) for criterion definitions, revisions, merges and reasons.
4. Open [candidates.csv](latest/results/candidates.csv) or [candidates.json](latest/results/candidates.json) for all 3,177 candidates, including pending evidence.
5. Open [surufatinib.json](latest/results/surufatinib.json) for its qualification, assessed values and evidence links. Keep [snapshot.json](latest/results/snapshot.json), [manifest.json](latest/results/manifest.json) and [validation.json](latest/results/validation.json) with any copied results.

The [tutorial's inspection commands](../../docs/tutorial.md#0-inspect-the-published-result-without-starting-a-workflow) read the published files with Python's standard library, without starting a server or calling a model.

## What happened in the latest run

The researcher supplied a single-drug oral objective covering **CSF1R, VEGFR1, VEGFR2, VEGFR3 and FGFR1**. The run used **mid workload and a configured worker limit of four**, a saved **USD 5.50 cap**, and a fixed collection of **3,157 facts / 164 sources**, cutoff **15 October 2026**, over **3,177 candidates**. Criterion generation selected 3,021 of those records. The current new-task default is USD 10; it does not replace the saved cap. Recorded model cost was **USD 4.2101472 estimated**.

Criteria started empty. Six task requirements expanded to **1,917 working items**, then three refinement rounds reduced them to **147 → 68 → 53**. The final 53 comprise **18 evaluation criteria** serving six eligibility requirements and 17 scoring criteria, with five shared target criteria; **13 contextual observations**; and **22 entries outside this evaluation** (14 registered/deferred + 8 unregistered).

Surufatinib passes the oral hard condition **1/1** and has direct observations for all required targets **5/5**. The first saved result had no rank because direct preference coverage was **6/17**, below the 50% ranking floor. Correcting existing-fact reuse and four deterministic descriptor basis classifications produced a new saved snapshot with **10/17** direct coverage. Scientific thresholds, weights and coverage floors were retained; the first outcome remains in the snapshot history.

Of 17 preferences, 15 have values and equal weight: **11.38888888888889 comparison points ÷ 15 = 0.7592592592592593**. Human oral F% and Tmax remain missing. The score denominator is 15; direct coverage uses all 17 applicable preferences. Predictions can contribute to the allowed preference score but do not increase direct coverage.

The current display reports **10 Eligible, 1,305 Evidence incomplete and 1,862 Excluded**. The immutable evidence-qualification fields retain the earlier 10 qualified / 3,167 pending summary; [the mapping](../../docs/reference/system-alignment.md#classification-version) explains the relationship. Surufatinib ranks first within the qualified ten. Its FGFR1 record shows how to audit aggregation: literature IC50 **34 nM** becomes **7.468521 pChEMBL**, which joins **7.280000, 7.82 and 7.82**; the four-record median is **7.64426054148**. The records preserve source/assay context; four records do not imply four independent experiments.

## Restore, replay or generate again

A fresh clone contains the exported JSON/CSV records and screenshots. The optional [reproduction capsule](latest/reproduction/README.md) adds the original available event rows, saved assessments, fixed generation facts, candidate library and cached tool observations. It is a separate 168 MB release asset, verified against the committed manifest.

Run `python scripts/agent_run.py replay --bootstrap --workspace var/agent-replay --open` to restore and verify the latest study in a new workspace. It recalculates qualification, scores and ranking from all saved assessments, without model calls. The [agent-run guide](../../docs/agent-run.md) also shows how to prepare the same fixed facts with an empty CQA set and start a new model investigation. New research retains its own identity and outcomes. The public capsule shows the final published evaluation; the earlier unranked snapshot is retained as a historical artifact because its original publication event is unavailable.

To conduct your own research, follow [installation](../../docs/installation.md), configure the provider, initialize a new workspace and import your own [candidate](../../config/examples/candidates.csv) and [measurement](../../config/examples/measurements.csv) CSVs through **Use own data**. The supplied templates contain headers only. Preserve identities, units, conditions and measured/derived/predicted basis; report the new investigation's actual counts and result.

## Comparing criterion sets

Criterion-set comparison uses a separately supplied authorized baseline. The [English](../../docs/reference/cqa-comparison.md) and [Chinese](../../docs/zh/cqa-comparison.md) guides demonstrate the method with synthetic entries.
