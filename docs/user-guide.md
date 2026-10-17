# Use the research workbench

[中文](zh/user-guide.md) · [Install](installation.md) · [Complete saved example](tutorial.md)

## Prepare a workspace

Start the modern workbench with `-AllowOperations` as described in the installation guide. It runs on loopback and provides task creation, uploads, settings and workflow control. Keep the terminal running while using the browser. A new workspace begins empty; published JSON/CSV results are inspection material, not an imported database.

Open **Settings** before your first investigation. Select the workload, worker count and budget for subsequent work. Model providers, credentials and optional predictor paths are configured separately in TOML; [configuration](configuration.md) explains both layers. A dollar budget can enforce known prices, but costs may remain unknown when the provider/configuration has no usable price. Check the cost status instead of treating unknown cost as zero.

## Create a research task

Choose **New research**. Write what a useful candidate should achieve and describe the intended experimental or use context. Set the object type, required targets/properties and constraints. For example, an oral drug study can require a documented oral route and direct observations for named targets. A carrier study needs its own property definitions and experimental conditions.

Keep a hard condition separate from a preference. A hard condition can exclude a candidate when it is clearly failed; a preference orders otherwise eligible candidates. Reference observations provide context without contributing ranking weight. The system preserves the original task text and its normalized scope.

Choose a candidate library and evidence input. Existing-only mode needs a saved collection or uploaded measurements. A fresh workspace has neither until data is supplied. Retrieval is a different mode that contacts configured sources. The [CSV guide](csv-input.md) explains candidate IDs, measurement rows, units, evidence basis and the preview checks. Save a draft to continue later, or start research when the inputs are ready.

## Observe the investigation

The progress strip remains across pages. It shows the current stage, recent work, elapsed time and recorded budget use. A stage can contain many batches. A batch fraction describes that stage's work, not the remaining time for the entire investigation.

The workflow connects task interpretation, evidence preparation, criterion proposals, refinement, review decisions, fixed evaluation rules, candidate assessment and result publication. Critical information that cannot be inferred can pause progress for supplementation. A budget or dependency limit leaves a specific unfinished stage rather than a fabricated completion.

**Pause**, **Continue** and **Stop** act at supported checkpoints. Check the resulting state before closing the terminal. A service restart pauses unfinished operational workflows so they can be resumed from saved work. A completed evaluation stays as a saved result; further research uses a new task or a recorded reevaluation.

## Read criterion evolution

Open **Criteria** to see the stage trajectory and final uses. The working set includes proposed items that may never become executable criteria. This is why the number of working items, registered criteria and enabled core criteria can differ.

Open a stage to inspect additions, revisions, merges, removals and unresolved proposals. Open a criterion to inspect its definition, rule, sources and history. A merge should retain the parent proposals and reasons. Check the final role: required conditions, preferences, context and not-enabled work have different effects.

Before assessment, the executable rule set fixes the measurement method, unit, aggregation, allowed evidence basis and decision method. Editing a criterion creates a new version. Where the workbench offers reevaluation, inspect the proposed impact and the new saved result; old snapshots retain their original rules.

## Interpret candidate groups and scores

| Group or state | Meaning |
|---|---|
| Qualified | Enabled hard conditions and required direct evidence are satisfied. Ranking still requires sufficient applicable direct preference coverage. |
| Pending evidence | A required determination is missing, conflicting or otherwise unresolved. |
| Rejected | An enabled hard condition has a verified failure. |
| Not assessed | Evaluation has not produced the required assessment state. |
| Skipped after rejection | Staged mode omitted this later cell because of a preceding hard failure. It is not a pass or missing observation. |

No effective hard conditions means screening is not ready. A high rejection fraction can prompt diagnosis, but does not change a hard condition into a preference. Prediction alone does not satisfy this workflow's direct-evidence gates.

Use **Score** to inspect each available preference's adopted value, evidence basis, comparison points, weight and contribution. Continuous preferences compare qualified candidates with values, with ties sharing an average position. Threshold preferences use their frozen decision method. The score denominator and direct coverage denominator can differ; missing values and prediction-assisted values remain visible.

Search and filters apply across the selected group, then paginate. Use the saved-evaluation selector to compare versions. Interpret scores within their declared comparison group and rule set.

## Follow a conclusion to its source

Open a candidate or criterion's **Evidence** link. The view retains the selected candidate, criterion and evaluation context. Literature is grouped by document; each group identifies research subjects and linked criteria. Expand findings to inspect values, conditions, evidence basis and original source positions. Exact duplicates can be expanded into the underlying records.

A saved evidence collection has a display name, description, topics, source count and cutoff. Editing display metadata does not modify the research evidence. A source finding can support more than one criterion, but repeated support for the same scored quantity should not become duplicate score contributions.

## Export and continue

**Export all candidates** downloads the full population for the selected saved evaluation, including candidates outside the qualified list. Keep the task, rule version, evidence scope and snapshot identity with an exported ranking. The repository's [retained example](../examples/oral-multitarget/) demonstrates a complete JSON/CSV result package.

Use **New study with this setup** to reuse a task's input setup and saved evidence while beginning a new criterion set. Supply additional evidence through supported imports, or edit the task scope with a recorded new version. A new model run can generate a different criterion trajectory; inspect its actual result before drawing conclusions.

For a complete walk-through with real numbers, screenshots and source inspection, follow the [oral multi-target tutorial](tutorial.md).
