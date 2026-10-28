# How TRIAGE develops an evaluation framework

[中文](zh/design.md) · [Documentation](README.md) · [Components](components/README.md)

## A reusable workflow, task-specific decisions

A study supplies a question, a candidate population and source evidence. It can also specify required conditions and observations. Those inputs determine what is examined. The workflow manages proposal, review, assessment and explanation; domain adapters supply the identities, quantities and tools appropriate to the research object.

For a new study, the criterion set starts empty. Requirements explicitly supplied by the task remain attached to it. Additional criteria are developed from the selected evidence. Saved facts can be reused without importing an earlier task's criteria or scores.

## Explore before narrowing

Early proposal generation considers relevant dimensions and alternative ways of measuring them. This exposes useful properties as well as overlapping, incomplete or poorly supported ideas. Review then determines which descriptions can support a meaningful comparison.

| Role | Responsibility | Feedback |
|---|---|---|
| Proposer | Specify a property, its conditions, evidence and intended evaluation use | Revise or withdraw proposals in response to findings |
| Critic | Check source support, relevance, measurement meaning and applicability | Return findings tied to the proposal and its evidence |
| Adjudicator | Resolve outstanding interpretations and assess compatible proposals | Combine, consolidate or retain distinctions; revised criteria return to review |

Refinement clarifies definitions, removes unsupported proposals and combines compatible descriptions. Different experimental conditions or decision meanings can remain separate. The system retains proposals and their relationships so the Criteria view can show how the final framework was obtained.

Stopping is controlled by the configured review budget and unchanged-round condition. Reaching the iteration limit records that reason. A target criterion count guides effort; the number of independent useful criteria determines the result.

Implementation: [derivation stages](../src/mas/core/derivation_stages.py), [round control](../src/mas/core/derivation_run.py), [pool history](../src/mas/core/pool.py), [adjudication](../src/mas/core/adjudication.py).

## Separate eligibility from prioritization

Eligibility requirements include conditions that must be met and direct observations that must be available. One criterion can both require an observation and use its value for scoring. Contextual observations add interpretation without scoring weight.

An applicable condition failure leads to Excluded. Otherwise, complete required support yields Eligible; partial support yields Evidence incomplete; completed assessment with no support for any requirement yields Excluded. Unfinished assessment and unavailable tools keep their own execution status. [Decision definitions](reference/decision-language.md) give the exact policy and examples.

Eligible candidates are scored using the selected comparison rules and weights. Numerical ordering is calculated within the eligible population with available values. Predictions can contribute when a criterion permits them; direct-evidence coverage separately counts accepted measurements, curated observations and allowed calculations. The saved minimum coverage decides whether an eligible candidate receives a rank.

Implementation: [assessment](components/assessment-and-qualification.md), [selection policy](../src/mas/core/selection.py), [ranking](components/ranking-and-explanations.md).

## Keep the meaning of each observation

Measurements, curated records, calculated descriptors and model predictions are distinct evidence bases. A criterion declares accepted units, conditions and aggregation. A pooled quantity should be interpreted with its endpoint types and assay metadata; two database records can describe the same underlying experiment.

Evidence pages group findings by source and link them to the criteria and candidates that use them. Candidate details distinguish eligibility findings, score contributions, predictions and missing evidence. [Evidence and reading](components/evidence-and-reading.md) and [CSV import](csv-input.md) describe those records.

## Apply the workflow to another study

Change the objective and requirements, provide the candidate library and observations, and select the appropriate tools. A synthetic carrier example can require a measured size range and viability while comparing delivery efficiency. The same eligibility function then uses those configured requirements; drug target names and case counts have no role in the generic decision function.

Follow [the agent guide](agent-run.md) for reproducible commands and [the component walkthrough](component-walkthrough.md) for inputs, rationale and implementation details. The [architecture map](architecture.md) identifies the shipped domain tools and planned extensions.
