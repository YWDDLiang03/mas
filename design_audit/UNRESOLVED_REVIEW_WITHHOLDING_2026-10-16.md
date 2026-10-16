# Strict prospective withholding of unresolved proposals

Implemented for new `qualification_first_v1` measurements. Legacy confirmation behavior and stored profiles remain readable without reinterpretation. No actual candidate results, sealed data, primary writes or model calls were used in this implementation verification.

## Confirmed failure and resulting behavior

The root task identified four `disputed=true` preferences in the first frozen set. In particular, the complete review receipt for `measured-oral-bioavailability-f-any-species@v1` upheld the objection and left the item unresolved, yet the old trigger-table path admitted this cutoff-free ordering preference to scoring. Completion of an unresolved review attempt did not mean approval.

New strict confirmation keeps each unresolved proposal active in the registry and retains the original queue state, rule, attribute, cutoff and evidence. It records the proposal in `deferred[]` with `scope=rule` and `reason_kind=unresolved_review`, including the exact rule/attribute and queue refs, queue reason, matching receipt refs, original receipt reason and source model request/trace refs. It does not include the proposal in scoring or its coverage denominator.

Resolved system review can still enter the scoring set with its actual machine adjudication authority. No human approval or passing verdict is fabricated. Original `pending[]` refs remain, so the existing controller path continues to block qualification on pending hard requirements or report not-ready when no verified applicable hard condition is available.

## API and compatibility

- `criteria.confirm_rule_set(..., withhold_unresolved_reviews=False)` adds an explicit opt-in flag. The default preserves legacy confirmation behavior.
- `criteria.unresolved_review_findings(core, task_id, *, rule_set=None)` is read-only: by default it reports active proposals with open/in-review rule items; a selected frozen set restricts findings to its exact entries.
- `measurement.prepare` automatically opts in when its effective policy is `qualification_first_v1`.
- `measurement.register` under that new policy rejects a selected scoring set that still has open/in-review entries or entries already marked disputed in the frozen set. Even if the queue later resolves, a stale frozen `disputed=true` entry needs fresh confirmation. The refusal writes no new profile.
- Strict rule sets and prospective scoring policies record `withhold_unresolved_reviews=True`.
- Criterion export renders these rule-level deferral reasons without treating them as deferred tool capabilities.

Changed files: `core/criteria.py`, `core/measurement.py`, `core/criteria_export.py`, and `tests/test_unresolved_review_freeze.py`. Workflow, investigation, controller, browser and store implementations were not edited.

## Verification

Two new tests use real temporary Core journals and scripted adjudicators. A cutoff-free quantitative F% ordering preference with an upheld species-aggregation objection reproduces the old auto-scoring behavior under explicit legacy confirmation, is withheld by strict confirmation, and retains its original records and unresolved receipt. A separate system-approved preference still scores. Pending hard review, active registry counts, original proposal data, legacy rule-set hash and old profile hash remain unchanged. A stale disputed frozen entry cannot bypass new-profile validation after its queue resolves.

Affected existing checks were reused:

```powershell
.venv\Scripts\python.exe -B -m pytest tests/test_unresolved_review_freeze.py tests/test_preference_execution_guard.py tests/test_qualification_first.py tests/test_measurement_profile.py tests/test_review_attempt_resume.py -q
```

Result: **42 passed in 3.57 s**. This verifies engineering behavior on synthetic temporary stores, not a new scientific ranking. Root owns preserving the partial old run, creating the next implementation/profile binding, and reusing only valid unchanged assessments under the new frozen scoring set.
