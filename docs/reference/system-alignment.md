# System terminology and recorded study alignment

[Decision rules](decision-language.md) · [Terminology catalog](terminology.md) · [Figure revision plan](../figures/revision-plan.md)

TRIAGE is an evidence-driven medical research workbench. Each task supplies its objective, candidate population, admission requirements, accepted evidence and scoring rules. The oral multi-target example supplies the drug-specific inputs used below.

## Workflow correspondence

| Study concept | System implementation and presentation |
|---|---|
| Criterion generation | Proposal, critique, revision and adjudication, followed by evidence and definition checks. |
| Eligibility requirements | Task-defined condition and evidence requirements that must all be satisfied before eligible-candidate scoring. |
| Required direct evidence | A task-defined observation obligation with explicit scope, evidence bases and requirement references. |
| Weighted prioritization | A fixed comparison method and weights applied to eligible candidates, with individual contributions available in Score. |
| Contextual observation | Assessed for interpretation, outside admission and scoring weights. |
| Enabled rules | Unique criteria used in admission or scoring; their uses may overlap. |
| Not enabled | Displayed as Not used in this evaluation, accompanied by the specific definition, review or evidence-route issue. |
| Surufatinib example | An eligible candidate with oral-administration support and observations for all five required targets. |

## Recorded quantities

| Quantity | Saved study and current system |
|---|---|
| Criterion trajectory | Empty generated set, six task requirements, expansion to 1,917 working items, then refinement to 147, 68 and 53. |
| Final working set | 18 enabled decision rules, 13 contextual observations and 22 items outside the evaluation. |
| Enabled decision rules | 18 unique rules = 6 eligibility requirements + 17 prioritization criteria − 5 shared target criteria. |
| Candidate population | 3,177. |
| Eligible population | 10. |
| Latest Surufatinib rank | 1 of 10; score 0.7592592592592593. |
| Direct preference coverage | 10/17 (58.8%), with a saved ranking floor of 50%. |
| Score contributions | 15 available equally weighted contributions: five measured/curated values, five deterministic calculations and five predictions. |
| Missing preference values | Two; retained in the coverage denominator of 17. |

## Admission and scoring uses

All six task requirements are mandatory for admission: one condition check for oral administration and five direct-evidence requirements for the targets. The same five target criteria also supply scoring values. Therefore the 18 unique decision rules implement six eligibility requirements and 17 scoring criteria, with five shared criteria. The workbench exposes these overlapping uses rather than treating them as exclusive categories.

## Classification version

The saved scientific export records `qualified: 10`, `pending: 3167` and `rejected: 0`. The earlier manuscript terminology maps these to qualified, pending/undetermined and confirmed-failure exclusion.

The current candidate-selection policy, `selection_reporting_v3`, reports:

| Display | Candidates | Decision basis |
|---|---:|---|
| Eligible | 10 | All admission requirements supported. |
| Evidence incomplete | 1,305 | Some admission requirements supported; remaining requirements have evidence gaps; no confirmed condition failure. |
| Excluded | 1,862 | Completed required assessments provide no admission support. |

The general policy also excludes a candidate when a required condition fails. In this saved example, the exclusion count is entirely attributable to absent admission support. The source qualification fields, observed values, thresholds, scores and ranks retain their saved values. The export includes the current selection decision, reason code and policy version alongside the historical fields.

The shared implementation is [core/selection.py](../../src/mas/core/selection.py). New snapshots and workbench readers use the same task-defined decisions. Requirement-specific explanations use the exact rule assessment from the selected evaluation.

## Display and figure terminology

The workbench defaults to English and offers Chinese interface labels. Main candidate groups are Eligible, Evidence incomplete and Excluded. Their indicators use green, amber and red. Unfinished assessments and framework readiness have separate status messages.

A deterministic descriptor receives a calculated display title when its recorded title still says Predicted and its current evidence definition accepts only derived values. The source title remains available in details.

The [current figures](../figures/current/README.md) use the same definitions. Their method panels describe configurable task requirements; their example panels carry the recorded quantities. Both figures are supplied as native editable PowerPoint objects, vector PDF/SVG and 600 dpi PNG.

## Verification

The [classification audit](../../examples/oral-multitarget/latest/selection/selection-audit.json) and [complete selection table](../../examples/oral-multitarget/latest/selection/candidate-selection.csv) derive from the published, frozen example. They can be regenerated with:

```powershell
python scripts/audit_selection.py --results examples/oral-multitarget/latest/results --output examples/oral-multitarget/latest/selection
```

[Release checks](../releases/2026-10-26-alignment.md) record implementation, browser/API and publication validation.
