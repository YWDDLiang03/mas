# Task-defined admission and prioritization

[中文](../zh/decision-language.md) · [Terminology](terminology.md) · [User guide](../user-guide.md)

TRIAGE evaluates candidates against a framework defined for each research task. The task supplies the candidate type, eligibility requirements, accepted evidence, applicability and prioritization criteria. Eligibility requirements include both condition requirements and evidence requirements; every one is required for admission. These definitions are fixed before candidate comparison.

## Three layers

1. **Task requirements:** what the candidate must satisfy, what evidence must be available, and how eligible candidates will be compared.
2. **Requirement assessment:** the observed value, applicable condition, evidence source and determination for each candidate–requirement pair.
3. **Candidate decision:** an outcome computed from those assessments, with links to the requirements responsible for it.

A **condition requirement** specifies a value, range or category that must be met. An **evidence requirement** specifies the usable direct observation that must be available. These are two kinds of eligibility requirement. A criterion can also use that observation for scoring.

In the recorded case, six eligibility requirements and 17 scoring criteria share five target criteria:

| Criterion group | Eligibility use | Scoring use | Unique criteria |
|---|---|---|---:|
| Oral administration | Condition must be met | None | 1 |
| Five required targets | Direct observations must be available | Potency values contribute to ranking | 5 |
| Other prioritization criteria | None | Values contribute to ranking | 12 |

Thus, **6 eligibility requirements + 17 scoring criteria − 5 shared criteria = 18 unique decision rules**. The target admission test in this saved framework is direct-evidence availability; its potency values are compared during ranking. Condition and evidence uses come from the frozen task bindings, so another task can assign different requirements and comparisons.

## Candidate decisions

| Outcome | Decision rule | Next step |
|---|---|---|
| **Eligible** | All applicable required conditions are met and all required observations are available. | Calculate the prioritization score and apply the ranking coverage policy. |
| **Evidence incomplete** | Some admission requirements have usable support, others remain unresolved, and no required condition has failed. | Show the supported requirements and the specific evidence gaps. |
| **Excluded** | An applicable required condition fails, or a completed assessment provides no usable support for any admission requirement. | Show the exclusion reason and the affected requirements. |

A required-condition failure takes priority over support for other requirements. Exclusion reasons distinguish **Required condition not met** and **No admission support**. Detailed evidence records retain measured values, missing evidence, conflicts and interpretation issues.

**Assessment incomplete** reports unfinished required work, tool errors or unavailable assessment records. **Criteria not ready** reports missing or unverified eligibility definitions. New evaluations require at least one explicitly defined eligibility requirement; a task may have condition requirements, evidence requirements, or both. A task with neither remains not ready. These operational states are displayed beside the outcome groups.

In staged evaluation, an established condition failure can stop later work. Zero-support exclusion is determined once the required assessments are complete. New evidence creates a new evaluation with the updated decision and its cause.

## Examples across task types

| Task | Task-defined requirements | Example outcomes |
|---|---|---|
| Drug prioritization | A permitted administration route and observations for the selected targets | Complete required support → Eligible; route support with missing target observations → Evidence incomplete; no admission support → Excluded. |
| Carrier selection | Measured size ≤150 nm and viability ≥80% under the specified assay conditions | 120 nm and 92% → Eligible; 120 nm with viability missing → Evidence incomplete; 170 nm → Excluded, with size as the reason. |
| Assay selection | A required sample type and documented detection limit | Complete support → Eligible; one requirement supported → Evidence incomplete; incompatible sample type or no admission support → Excluded. |

The same decision function consumes each task's requirement references and assessments. Candidate names, targets, assay names and sample counts enter through task data.

## Scores and evidence

A **prioritization score** compares eligible candidates under the fixed scoring definitions and weights. A threshold preference reports **Scoring threshold met / not met**; an ordering preference reports its value and score contribution.

**Direct-evidence coverage** is the directly supported share of applicable prioritization weight. The framework declares the accepted bases: measurements, curated observations, supported source statements and permitted deterministic calculations. Predictions are listed separately. An eligible candidate receives a rank when it satisfies the saved ranking coverage policy. Insufficient scoring coverage leaves the candidate in Eligible with a Not ranked reason; it does not change the admission decision.

## Criterion use

| Term | Meaning |
|---|---|
| Criterion proposal | A measurement and decision definition under development. |
| Evaluation criterion | What is assessed, under which conditions, with which evidence and comparison. |
| Eligibility requirement | A condition or evidence obligation that must be satisfied for admission. |
| Condition requirement | An applicable value, range or category that must be met. |
| Required direct observation | A task-defined evidence obligation for a property or entity. |
| Weighted prioritization criterion | A comparison contributing to the eligible candidates' scores. |
| Contextual observation | Evidence used to interpret results. |
| Not used in this evaluation | A retained item outside the active framework, accompanied by a specific reason. |

Items outside the evaluation identify their obstacle: incomplete scoring definition, unresolved review, unresolved unit conversion, unresolved alternative policy or an unfinished proposal. The framework records the responsible review and version.

## Shared implementation

[`core/selection.py`](../../src/mas/core/selection.py) implements the decision policy. New result snapshots, historical result readers, candidate details and exports use this function. Each decision carries a policy version, reason code and affected requirement references. Names and supporting evidence are resolved from the selected task and evaluation.

`selection_reporting_v3` uses `eligible`, `evidence_incomplete` and `excluded` as compatible API values; `evidence_incomplete` is displayed as **Evidence incomplete**. Execution uses `incomplete` and framework readiness uses `not_ready`. New measurement profiles record `declared_eligibility_requirements_v1`, which supports evidence-only admission requirements. Historical profiles without this field retain `verified_condition_required_v1` for replay and resume. Historical source records retain their saved qualification fields. Legacy hard/mandatory fields refer to condition checks; required-observation fields refer to evidence requirements. CSV exports include both selection and evidence reason codes.

## Recorded oral multi-target example

The task has six eligibility requirements: one oral-administration condition and five direct-evidence requirements. The five target criteria also participate in scoring. Its current classification is **10 Eligible, 1,305 Evidence incomplete and 1,862 Excluded**. The exclusion reason for those 1,862 candidates is no admission support. The five target observations contribute numerical values to subsequent prioritization.

Surufatinib ranks **1 of 10**, with score **0.7592592592592593**. Direct coverage is **10/17 (58.8%)**: five measured/curated target values and five permitted calculations. Five additional criteria use predictions and two lack values. Fifteen equally weighted contributions enter the score.

The final working set contains 18 enabled decision rules, 13 contextual observations and 22 items outside the evaluation. [Source snapshot](../../examples/oral-multitarget/latest/results/snapshot.json) · [Current classification audit](../../examples/oral-multitarget/latest/selection/selection-audit.json)
