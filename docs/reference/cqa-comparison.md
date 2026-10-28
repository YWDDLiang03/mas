# Comparing evaluation criteria

[中文](../zh/cqa-comparison.md) · [Component implementation](../components/evaluation-and-recovery.md) · [Synthetic fixture](../../config/examples/criterion-comparison.synthetic.json)

Compare the scientific meaning of criteria before counting matches. A name alone does not describe the measured quantity, population, experimental conditions, evidence type or decision use.

## Comparison procedure

1. Fix the two criterion sets and their versions.
2. Identify each quantity, unit, conditions, evidence basis and use in eligibility or scoring.
3. Match equivalent meanings, recording any differences in thresholds, directions or populations.
4. Keep unmatched and unresolved items visible. Count each baseline criterion once.
5. Report the comparison separately from candidate ranking and its outcome.

## Synthetic illustration

These entries demonstrate the comparison format; they are not study measurements.

| Earlier definition | Later definition | Interpretation |
|---|---|---|
| Measured particle size ≤150 nm, required | Same quantity, conditions and required cutoff | Same operational criterion |
| Measured viability ≥80%, required | Same measurement, higher values preferred for ranking | Related measurement, different decision use |
| Delivery efficiency under assay A | Uptake under assay B | Unresolved relationship; different outcomes/conditions need clarification |

The [JSON fixture](../../config/examples/criterion-comparison.synthetic.json) records this example explicitly as synthetic. Users supply their own authorized baseline and generated set for an actual comparison.

## Implementation and access

[`recovery.py`](../../src/mas/core/recovery.py) checks mappings, count partitions, origin labels and evaluator access. [`freeze.py`](../../src/mas/core/freeze.py) records the policy and selected versions. The public report can expose aggregate counts while the baseline text and detailed mappings remain private. See [public-content policy](public-content.md).
