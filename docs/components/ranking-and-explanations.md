# Ranking, symbolic scoring and explanations

[Components](README.md) · [Assessment](assessment-and-qualification.md) · [Evaluation](evaluation-and-recovery.md)

Ranking orders candidates after eligibility has been established and publishes the evidence coverage needed to interpret that order. Explanations help readers inspect the result, with different authority for a score decomposition and a literature-grounded mechanism note. This page covers C12 and the optional scoring/explanation modules.

## Inputs and outputs

| Input | Output |
|---|---|
| Candidate cells, rule definitions, weights, qualification | Preference score and coverage per candidate |
| Task context, member set, rule set, roll-ups, evidence snapshot and scores | Immutable leaderboard snapshot and change records |
| Assessed features, model proposals, fixed train/select/holdout splits | Recorded symbolic scoring attempt; expression adopted only if it passes |
| Admitted candidate claims with verified spans | Separately stored mechanism narrative with sentence-level citations or `unexplained` |

[`leaderboard.py`](../../src/mas/core/leaderboard.py) implements `member_set_hash`, `leaderboard_record`, `snapshots` and `build_snapshot`. The comparability key includes objective, mode, evaluation scope, required scope, hard constraints, universe description and the actual member-set hash. Set-dependent percentile scores over different populations therefore open different leaderboards.

## Weighted preference mechanism

[`assessor.preference_scores()`](../../src/mas/core/assessor.py) returns `(score, coverage)`. A threshold preference contributes 1 for pass or 0 for fail. An ordering preference contributes a direction-aware percentile among candidates with a usable value; ties share their mean percentile and a singleton receives 1. Under current qualification, the comparison population can be restricted to qualified candidates.

Weights combine available contributions into a weighted mean. Missing contributions are absent from the score numerator/observed denominator, while coverage reports how much of the registered applicable preference set has been answered. Under current qualification that coverage uses direct evidence. A candidate with a high score and weak coverage is therefore distinguishable from one with a similar score measured comprehensively. The configured floor determines whether it receives a position.

The snapshot records each candidate's qualification, score, preference/direct coverage, mandated coverage, hard failures/unknowns, measurement versus prediction counts, determination bases, missing evidence and assessment refs. Current qualification assigns scores only to qualified candidates. Stable tie breaks use score, state, coverage and candidate ID. `result_kind` states whether the snapshot reports an all-pass set, ranking, both or no recommendation, and abstention reasons explain an empty usable result.

`_changes()` compares parent/current candidate state and position and attaches assessment causes. Snapshots are immutable; selecting a current snapshot or editing its display title does not alter previous ranks. Machine authority remains visible through the rule review summary and provisional states.

## Optional symbolic scoring

[`symbolic.py`](../../src/mas/core/symbolic.py) implements a restricted term grammar, expression evaluation, ridge fitting toward declared priors, sign checks, conditioning checks, deterministic candidate splits and scoring metrics. It does not execute model-generated Python.

[`sr_stage.py`](../../src/mas/core/sr_stage.py) builds features from already assessed cells, proposes/criticizes expression structures and runs the experiment. The proposer sees feature definitions, units, directions, coverage and training quartiles; candidate identities, target values and the disclosed reference outcome are withheld. Target-derived features and reserved score/rank fields are refused. Terms need allowed forms; hinge constants must come from shown quartiles or cited claim values. Too few fitting rows can use declared priors, recorded as that route.

Generations are selected using the select split and a complexity penalty. `adoption_check()` uses a held-out comparison against the weighted-preference baseline, recomputed for that holdout member set. Insufficient gain retains the baseline and records the failed attempt. An adopted expression is installed through a new confirmed rule-set ordering method before publication, with exploratory authority and review requirements.

The current controller refuses symbolic ordering combined with `qualification_first_v1`. Symbolic scoring is an optional legacy-compatible path; the standard qualification workflow uses weighted preferences. A scoring fit is also distinct from the proposed C20 strategy archive.

## Explanation boundaries

Symbolic `term_contributions()` and score-detail functions explain the arithmetic that generated a score. [`ui/score_details.py`](../../src/mas/ui/score_details.py) exposes values, directions, weights and contributions for inspection.

[`mechanism.py`](../../src/mas/core/mechanism.py) instead builds a narrative from admitted claims with checked spans. `eligible_claims()`, `gate()` and `check_separate()` enforce citation/candidate support and reject scoring claims in the narrative. Unsupported sentences are dropped. No eligible/surviving sentence yields `unexplained`. `explain()` and `explain_shortlist()` persist the separate narrative; `narrative_of()` retrieves it. Scoring, comparability and snapshot modules do not read this narrative.

Workbench research briefs are another presentation aid. They use a separate annotation store and bounded spend, and cannot replace scientific criterion or assessment records.

## Failure semantics

No usable preference contribution yields no score. Insufficient direct coverage prevents a rank. No qualified/rankable candidates produces an explicit abstention. Invalid symbolic grammar, singular/ill-conditioned fit, sign violation, unsupported hinge, blocking critique or insufficient held-out improvement retains a recorded rejection/baseline. Narrative citation failures drop the affected sentences instead of manufacturing support.

## Worked example: score and coverage together

**Illustrative:** two equally weighted threshold preferences apply to two qualified candidates. A passes one and fails one: score 0.5 with full direct coverage. B passes one and has no observation for the other: its observed score is 1.0 with direct coverage 0.5. If the configured ranking floor is 0.75, B remains visible but has no position. Lowering the floor for a new registered run would change that ranking policy, while the old snapshot remains intact.

## Existing verification

[`test_symbolic.py`](../../tests/test_symbolic.py) covers grammar, fit refusal, priors, split exclusion, blind prompts, held-out adoption and member-set comparability. [`test_score_details.py`](../../tests/test_score_details.py) checks score inspection. [`test_mechanism.py`](../../tests/test_mechanism.py) checks citations, idempotence and separation from scores/snapshots; [`test_qualification_first.py`](../../tests/test_qualification_first.py) checks qualified-only ranking and direct coverage.
