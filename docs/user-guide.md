# Use the research workbench

[Workflow design](design.md) · [Documentation index](README.md)

[中文](zh/user-guide.md) · [Install](installation.md) · [Complete saved example](tutorial.md)

## Prepare a workspace

Start the modern workbench with `-AllowOperations` as described in the installation guide. It runs on loopback and provides task creation, uploads, settings and workflow control. Keep the terminal running while using the browser. A new workspace begins empty. To restore the published case and its inputs, use [the agent runner](agent-run.md).

Open **Settings** before your first investigation. Select the workload, worker count and budget for subsequent work. Model providers, credentials and optional predictor paths are configured separately in TOML; [configuration](configuration.md) explains both layers. A dollar budget can enforce known prices, but costs may remain unknown when the provider/configuration has no usable price. Check the cost status instead of treating unknown cost as zero.

## Create a research task

Choose **New research**. Write what a useful candidate should achieve and describe the intended experimental or use context. Set the object type, required targets/properties and constraints. For example, an oral drug study can require a documented oral route and direct observations for named targets. A carrier study needs its own property definitions and experimental conditions.

Define eligibility requirements before preferences. A condition requirement specifies a category, range or threshold that must be met; an evidence requirement specifies the usable direct observations that must be available. Both are compulsory for admission. Prioritization criteria compare eligible candidates, and a required observation can also supply a scoring value. Contextual observations support interpretation. The system preserves the original task text and its normalized scope.

Choose a candidate library and evidence input. Existing-only mode needs a saved collection or uploaded measurements. A fresh workspace has neither until data is supplied. Retrieval is a different mode that contacts configured sources. The [CSV guide](csv-input.md) explains candidate IDs, measurement rows, units, evidence basis and the preview checks. Save a draft to continue later, or start research when the inputs are ready.

## Observe the investigation

The progress strip remains across pages. It shows the current stage, recent work, elapsed time and recorded budget use. A stage can contain many batches. A batch fraction describes that stage's work, not the remaining time for the entire investigation.

The workflow connects task interpretation, evidence preparation, criterion proposals, refinement, review decisions, fixed evaluation rules, candidate assessment and result publication. Critical information that cannot be inferred can pause progress for supplementation. A budget or dependency limit leaves a specific unfinished stage rather than a fabricated completion.

**Pause**, **Continue** and **Stop** act at supported checkpoints. Check the resulting state before closing the terminal. A service restart pauses unfinished operational workflows so they can be resumed from saved work. A completed evaluation stays as a saved result; further research uses a new task or a recorded reevaluation.

## Read criterion evolution

Open **Criteria** to see the stage trajectory and final uses. The working set includes proposed items that may never become executable criteria. This is why the number of working items, registered criteria and enabled decision rules can differ.

Open a stage to inspect additions, revisions, merges, removals and unresolved proposals. Open a criterion to inspect its definition, rule, sources and history. A merge should retain the parent proposals and reasons. Check every final use: condition and evidence requirements govern admission, prioritization criteria determine scores, and contextual observations support interpretation. A criterion can serve admission and scoring. Items outside the evaluation retain a specific reason.

Before assessment, the executable rule set fixes the measurement method, unit, aggregation, allowed evidence basis and decision method. Editing a criterion creates a new version. Where the workbench offers reevaluation, inspect the proposed impact and the new saved result; old snapshots retain their original rules.

## Interpret eligibility, evidence profiles and scores

See [selection decisions and evidence states](reference/decision-language.md) for the general definitions, historical field mapping and the retained case breakdown.

| Group or state | Meaning |
|---|---|
| Eligible | All task-defined eligibility requirements are satisfied. Ranking also requires sufficient applicable direct-evidence coverage for scoring. |
| Evidence incomplete | Some admission requirements have usable support, others have evidence gaps, and no required condition has failed. |
| Excluded | A required condition is confirmed to fail, or completed required assessments provide no usable admission support. |
| Assessment incomplete | A required assessment is unfinished, failed or unavailable. |
| Criteria not ready | Eligibility requirements are missing, unbound or awaiting verification. |
| Skipped after rejection | Staged mode omitted this later cell because of a preceding hard failure. It is not a pass or missing observation. |

New tasks need at least one defined and verified eligibility requirement. A task can use condition requirements, evidence requirements, or both; an empty requirement set remains not ready. A high exclusion fraction prompts diagnosis while preserving the frozen requirements. Predictions remain separate from the direct evidence required for admission.

Use **Score** to inspect each available preference's adopted value, evidence basis, comparison points, weight and contribution. Continuous preferences compare qualified candidates with values, with ties sharing an average position. Threshold preferences use their frozen decision method. The score denominator and direct coverage denominator can differ; missing values and prediction-assisted values remain visible.

An eligible candidate with insufficient scoring coverage remains in Eligible with a visible Not ranked reason. Admission gaps belong to Evidence incomplete. Search and filters apply across the selected group, then paginate. Use the saved-evaluation selector to compare versions. Interpret scores within their declared comparison group and rule set.

## Follow a conclusion to its source

Open a candidate or criterion's **Evidence** link. The view retains the selected candidate, criterion and evaluation context. Literature is grouped by document; each group identifies research subjects and linked criteria. Expand findings to inspect values, conditions, evidence basis and original source positions. Exact duplicates can be expanded into the underlying records.

A saved evidence collection has a display name, description, topics, source count and cutoff. Editing display metadata does not modify the research evidence. A source finding can support more than one criterion, but repeated support for the same scored quantity should not become duplicate score contributions.

## Export and continue

**Export all candidates** downloads the full population for the selected saved evaluation, including candidates outside the qualified list. Keep the task, rule version, evidence scope and snapshot identity with an exported ranking. The repository's [retained example](../examples/oral-multitarget/) demonstrates a complete JSON/CSV result package.

Use **New study with this setup** to reuse a task's input setup and saved evidence while beginning a new criterion set. Supply additional evidence through supported imports, or edit the task scope with a recorded new version. A new model run can generate a different criterion trajectory; inspect its actual result before drawing conclusions.

For a complete walk-through with real numbers, screenshots and source inspection, follow the [oral multi-target tutorial](tutorial.md).
