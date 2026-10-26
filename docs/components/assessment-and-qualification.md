# Per-candidate assessment and qualification

[Practical walkthrough](../component-walkthrough.md#assessment-and-qualification) · [中文实操](../zh/component-walkthrough.md#assessment-and-qualification)

[Components](README.md) · [Criteria](criteria-and-review.md) · [Ranking](ranking-and-explanations.md)

The assessor computes what the available evidence means for one candidate and one criterion. Qualification determines whether the candidate satisfies all task-defined eligibility requirements: applicable condition checks and required direct observations. Eligible candidates then enter prioritization. This implements C11 and supplies the candidate-level facts consumed by C12.

## Contract

`assess_cell()` in [`assessor.py`](../../src/mas/core/assessor.py) consumes candidate identity, attribute and rule versions, frozen rule-set reference, claims, authority/review information, execution limits and the selected qualification policy. It returns an assessment and a separate reason record. A cell retains values/intervals, unit and value kind, determination basis, supporting/conflicting/set-aside claim references, verdict, missing/skip/error reasons and provenance.

`qualification()` consumes the candidate's cells plus registered hard-rule refs, required-rule refs, verified hard-rule refs and pending hard rules. It returns a structured state, failed/blocking refs, direct-coverage denominators and `qualified`. Those registered denominators remain even when cells are absent. New profiles bind `declared_eligibility_requirements_v1`: evidence-only tasks can be evaluated when their required observations are bound. An empty requirement set or an unbound evidence-only requirement remains not ready. Historical profiles retain their original readiness policy during replay and resume.

## Admission requirements and scoring uses

`qualification()` requires both the specified condition results and all required direct observations. `core.selection.requirement_roles()` describes these uses independently of the scoring role. Five target criteria in the recorded study therefore require direct evidence for admission and also contribute their values to scoring. Read-model role metadata follows the task scope captured at the selected freeze.

## Why observation, availability and eligibility differ

An observation can be available without having a justified threshold. A hard criterion can be unanswered while a preference is measurable. A prediction can suggest a promising candidate without clearing a measured-data requirement. MAS preserves these dimensions instead of collapsing them into one pass/fail flag.

The immutable `qualification_first_v1` records retain four evidence-qualification states. The shared [candidate selection policy](../reference/decision-language.md), implemented in `core/selection.py`, derives Eligible, Evidence incomplete or Excluded from task requirements and assessments. New snapshots and result readers use this same function. The underlying qualification fields are:

| State | Meaning |
|---|---|
| `rejected` | A verified hard condition has a direct-evidence failure |
| `not_ready` | Eligibility definitions are not ready under the run's bound policy; new profiles accept bound condition requirements, evidence requirements, or both |
| `pending` | Recorded evidence qualification is incomplete; partial support yields Evidence incomplete, and completed zero-support assessments yield Excluded |
| `qualified` | All applicable condition requirements pass and all required direct evidence is present |

Candidate display states such as provisional/recommended are a separate authority/result dimension. A qualified candidate can remain provisional because its rules have machine authority rather than human scientific confirmation. Insufficient ranking coverage keeps an eligible candidate unranked; it does not move the candidate into Evidence incomplete.

## Measurement mechanism

`usable_claims()` selects admitted evidence compatible with the attribute's accepted evidence kinds, determination bases, scope, units, conditions and policy. `converted_claim()` and `unit_conversion()` implement supported numerical conversions; incompatible units remain set aside. `source_document_shortfall()` enforces the configured count of distinct source documents for literature-only values; a mixed cell with record-field evidence follows the database exemption. Distinct documents are not automatically independent experiments.

Explicit basis precedence lets a measurement be used when present and a prediction fill a declared gap when permitted, without mixing the two bases in a median. The cell reports which basis it actually used. Quantitative reductions use the declared aggregation. Family aggregations are mapped by `family_aggregation_execution()` to executable reductions; conflicting scientific contexts can require a declared interpretation rather than unqualified pooling.

Threshold predicates compare the supported value with the registered bound. Ordering preferences expose an available value for later percentile scoring. Exploratory considerations remain visible but do not order candidates. Supported transforms retain their parameter provenance; unresolved interpretation produces `unknown_unresolvable`.

## Direct evidence and prediction behavior

`direct_evidence()` requires a value-bearing verdict (`pass`, `fail` or `available`), real source claim refs, no tool error, an accepted direct determination basis and a value kind outside predicted/simulated/missing. Under `qualification_first_v1`, predictions do not fail hard conditions or increase direct evidence coverage. The ranking path also avoids scoring a predicted and a direct representation of the same quantity twice for one candidate.

This policy is versioned because historical runs used legacy qualification and calibration semantics. The older `calibration_guard()` can demote overly broad exclusions for a run. Current qualification uses the diagnostic path and keeps hard-condition semantics intact. Read the run binding and snapshot policy rather than applying current defaults to historical boards.

## Scheduling and failure semantics

[`RunController._run_qualification()`](../../src/mas/core/controller.py) orders hard conditions first, prioritizes non-literature work within that group and evaluates candidates deterministically. In `staged` mode, only a direct failure of a verified hard rule triggers later skips. A missing value, unresolved identity, unverified hard rule or prediction is not such a failure. In `full` mode, later criteria remain evaluated for rejected candidates too.

| Cell state | Meaning |
|---|---|
| `pass` / `fail` | A decision-bearing predicate was evaluated |
| `available` | A value is available for ordering |
| `unknown_missing` | Required evidence is missing or the route failed/was unavailable |
| `unknown_conflicted` | Relevant evidence conflict remains unresolved |
| `unknown_unresolvable` | A required interpretation method is unresolved |
| `inapplicable` | Criterion does not apply under its declared policy |
| `not_assessed` | Identity, budget, cancellation or a verified earlier rejection prevented evaluation |

Skipped cells name `skipped_after_rejection` and the causal assessment/rule/reason refs. Budget-limited cells name `budget_exhausted`; cancelled work remains distinct. `roll_up()` combines legacy decision/authority states, while the current path adds explicit qualification. Every candidate remains represented in the published snapshot, including candidates with unknowns or skipped cells.

## Worked example: a missing hard observation

**Illustrative:** a task requires an observed particle size ≤150 nm and observed viability ≥80% under specified conditions. Candidate A has 120 nm and 92%, so its hard cells pass. Candidate B has 170 nm and no viability measurement. In staged evaluation, B's verified size failure rejects it and records the later viability cell as skipped with the size assessment as cause. Candidate C has 130 nm and only predicted viability 95%; C is Evidence incomplete, with size supported and direct viability evidence missing.

With identical fixed facts, full and staged evaluation should yield the same qualified population and qualified-candidate scores. Full mode can supply additional diagnostic cells for the rejected population; staged mode deliberately does less work.

## Existing verification

[`test_qualification_first.py`](../../tests/test_qualification_first.py) checks qualified-population equivalence, prediction limits, context methods, staged causes, direct coverage and continuation of previously skipped cells. [`test_distance_band_readiness.py`](../../tests/test_distance_band_readiness.py), [`test_raw_range_readiness.py`](../../tests/test_raw_range_readiness.py) and [`test_preference_execution_guard.py`](../../tests/test_preference_execution_guard.py) check executable measurements. [`test_calibration_guard.py`](../../tests/test_calibration_guard.py) covers the distinct legacy policy.
