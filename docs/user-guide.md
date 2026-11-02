# Use the research workbench

[中文](zh/user-guide.md) · [Target-driven workflow](target-workflow.md) · [Install](installation.md) · [Recorded case tutorial](tutorial.md)

## Prepare a workspace

Start the workbench with local operations enabled, following the installation guide. Open **Settings** and choose workload, concurrency and the cost cap for new studies. The CDES default is also set here. Provider credentials and model bindings are configured in TOML; see [configuration](configuration.md).

The saved public study can be restored with [the agent runner](agent-run.md). Its original settings and costs remain available in the run record. New studies record their own configuration and model use.

## Enter targets and requirements

Choose **New research**. Enter the target profile and the conditions or preferences that matter to the study. Add an indication or other research context when useful. If targets are supplied without additional objective text, the form shows a generated task summary before launch.

State required conditions clearly, such as a documented administration route or a measured value under specified conditions. Preferences describe how to compare eligible candidates. The agents use these inputs to develop the evaluation framework and retain each requirement's task origin.

Choose the object type. Drug studies use their selected compound library and drug data providers. Carrier and other candidate studies use uploaded properties and observations. The [CSV guide](csv-input.md) explains identities, values, units, conditions and sources.

## Choose the library and evidence strategy

Select **Candidate database / library**, or import the candidate and observation files for an uploaded-data study.

| Evidence strategy | Use |
|---|---|
| Search and read new evidence | Start a drug study with a new target profile; optionally add a saved collection. |
| Use saved or uploaded evidence | Develop criteria from the selected collection or supplied observations. |

A new retrieval study can begin with its own task and library. Saved-evidence mode uses an explicitly selected collection. Review the collection's name, topics, source count and cutoff when choosing it.

## Choose optional CDES analysis

The **CDES target profiles** switch belongs to the current task. When enabled, select a saved prediction collection and check its available targets. The workflow preview adds a CDES step after screening and ranking.

CDES provides structure-based interaction profiles beside the recorded activity and overall evaluation. The current module reads supplied results. Its source collection is fixed for the study, and the output identifies covered and missing targets or compound matches. [The module guide](components/structure-predictions.md) covers import and the later deployment connection.

For a completed study, **CDES analysis** can switch its analysis view off and on while retaining the attached records. Settings changes apply to new drug studies; each task can override the default.

## Start and follow progress

Use **Save draft** to keep an unfinished setup, or **Start research** when ready. The progress strip remains visible across pages and shows the current activity, elapsed time, recent work and cost status.

The workflow connects task interpretation, evidence preparation, criterion development, refinement, review, evaluation preparation, candidate assessment and result delivery. CDES adds a step when selected. Essential missing task information appears as a specific question. Budget or source limits identify the stage that needs attention.

**Pause**, **Continue** and **Stop** act at saved work boundaries. After a service restart, unfinished work can continue from its checkpoint. Read the cost value together with its recorded, estimated, partial or unknown status.

## Explore criterion development

Open **Criteria → How these criteria developed**. The trajectory shows the starting set, task requirements, expansion and refinement. Stage changes show additions, revisions, combinations, withdrawals and unresolved work.

Open a criterion to inspect its definition, accepted evidence, decision use, sources and history. Eligibility requirements govern admission; prioritization criteria contribute to scores; contextual observations support interpretation. A criterion can supply both required evidence and a scoring value.

The evaluation fixes measurement definitions, units, aggregation, comparison methods and weights before candidate assessment. Editing a criterion creates a new version. Saved evaluations retain the definitions used to produce them.

## Read candidate results

| Group | Meaning |
|---|---|
| Eligible | All task-defined admission requirements are supported. |
| Evidence incomplete | Some admission support is available and further required evidence is needed. |
| Excluded | A required condition fails, or completed required assessments provide no admission support. |

Execution status also identifies unfinished assessments and requirements awaiting definition or review. [Decision definitions](reference/decision-language.md) give the full policy.

A candidate opens three views: **Score breakdown**, **Assessments & evidence** and **Target profile**. The score view lists adopted values, evidence bases, criterion points, weights and contributions. It also shows the coverage used for ranking. An eligible candidate below the configured coverage threshold retains its eligibility and a specific unranked reason.

Continuous scores compare eligible candidates with available values. The total averages the available weighted contributions; coverage uses the applicable scoring framework. The CDES target profile presents interaction scores and recorded activities with their own units and source links.

Search and filters operate across the selected candidate group before pagination. The saved-evaluation selector opens the result version to inspect.

## Follow a result to its source

Candidate and criterion links retain their research context in **Evidence**. Findings are grouped by document or source record. Expand a group to inspect values, study conditions, source positions and the criteria that use them.

In **CDES analysis**, select a prediction to inspect its original result row and protein input. **View observations** opens the recorded activity sources for that candidate and target criterion. The prediction library and the study's candidate library have separate counts and a visible correspondence.

## Export and continue

**Export all candidates** downloads the full saved evaluation. **Download complete data** on the CDES page exports its linked result collection and source files. Both exports retain the evaluation identity needed to interpret the values.

Use **New study with this setup** to reuse inputs and start a new criterion set. Change the targets, requirements, library, evidence strategy and optional module choice for the next study. The [case tutorial](tutorial.md) demonstrates the full inspection path using the public saved result.
