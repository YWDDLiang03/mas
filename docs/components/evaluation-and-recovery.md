# Prospective measurement and historical CQA recovery

[Components](README.md) · [Architecture status](../architecture.md) · [Criteria](criteria-and-review.md)

MAS includes machinery to state a measurement policy before an experiment and compare frozen derived criteria with an evaluator-supplied historical list. These are implemented parts of C19. They support a reproducible case measurement; they do not implement the full proposed strategy-promotion/evolution system.

## Purpose and rationale

A rank depends on the candidate population, enabled conditions, evidence policy and scoring rule. A recovery percentage depends on which criteria were frozen, how historical meanings were mapped and whether the deriving actors had already seen the list. Capturing those choices is necessary to interpret the reported numbers.

The implementation separates policy registration from later artifact binding because evidence that has not yet been retrieved cannot be hashed prospectively. It also separates semantic matching, which may use an isolated evaluator model, from mechanically checkable mapping constraints.

## Inputs and outputs

| Operation | Inputs | Outputs |
|---|---|---|
| Freeze policy | Task/rules refs, population, evidence/scoring/rank policy and implementation | Immutable preregistration record and later captured-artifact binding |
| Measurement profile | Exact selected rules, required anchors, scoring/qualification/evidence modes, floors and implementation | Profile reference/digest, one-run use checks |
| Historical intake | Frozen criterion snapshots, verbatim historical items, provenance/completeness and evaluator identity | One evaluator-only intake with content hash and content-free header |
| Recovery comparison | Frozen derived meanings, intake, explicit mapping or isolated evaluator roster | Checked mapping and comparison record |
| Report/export | Recorded comparison and exposure/origin information | Report, public counts and manifest with measurement limitations |

## Freeze and measurement implementation

[`freeze.register()`](../../src/mas/core/freeze.py) accepts a defined set of policy fields, requires the fields fixing the endpoint, and records the prospective policy. `verify()` compares supplied actual fields and reports drift rather than silently tolerating it. `bind_artifacts()` records captured references separately and cannot change the policy.

[`measurement.prepare()`](../../src/mas/core/measurement.py) checks required task anchors, freezes the executable rule set with the selected deferrals/authority and registers its exact profile. `check_required_anchors()` uses the original task-bound attribute/rule hashes and active bindings, refusing to shrink the required denominator by removing or silently changing an anchor. Pending review and deferred routes remain explicit.

`register()`, `load()`, `digest()`, `verify()` and `ensure_unused()` implement profile identity, validation and single-use checks. `RunController.start()` verifies the task/rule set, seed, cutoff, candidate limit, settings and implementation against the profile before execution. An old run without a profile retains its historical semantics; a new profile does not retroactively certify an earlier outcome.

## Historical intake and isolation

[`recovery.record_intake()`](../../src/mas/core/recovery.py) requires frozen snapshots and an evaluator-role actor, accepts the list once, and stores the supplied wording, provenance form, completeness attestation, ambiguities and canonical content hash. A corrected list requires a new case. Public header access reports the intake's size/hash/freeze refs without reading item contents.

`read_intake()` logs `evaluator_only.read`, including actor and purpose, before returning content. `check_isolated_evaluator()` checks that the evaluator judge uses a distinct adapter/model identity from deriving roles. `propose_mapping()` asks that evaluator for a semantic mapping; `check_mapping()` then checks that references exist in the frozen set, categories partition the historical items, repeated variants do not inflate coverage and split mappings explicitly cover the meanings they claim.

The three historical-item categories are `exact`, `near_equivalent` and `missed`. Extra derived criteria are reported on the derived side and are not automatically errors. A threshold/scope/expression difference must be disclosed as near-equivalence rather than hidden inside an exact match. `derived_set()` reconstructs the frozen criterion meanings, and `compare()` persists the checked comparison.

## Reporting and scope of inference

`exposure_declaration()` combines recorded declarations/access information. `report()` retains origin-stratified counts: task-mandated/template restatements are distinguishable from literature-derived criteria. `public_counts()` produces content-free measurement summaries; `render_markdown()`, `render_counts()`, `manifest()` and `write()` package the output.

A recovery result concerns the supplied historical list, its attested completeness, the frozen criteria and the reported exposure status. A public end-to-end rank, a fixed-evidence re-derivation and an isolated historical recovery experiment answer different scientific questions. Their records must be read with their own policy and lineage. A selected reference compound's favorable rank alone does not establish general predictive validity or an adaptive agent advantage.

Evaluator-only content uses application/process separation and access logs. Artifacts are stored as JSON in SQLite, without encryption or authenticated-principal isolation from Python/filesystem access. The `write()` export guard refuses evaluator-only report content in the repository's named published trees, including `docs` and `examples`; those full reports belong in a separate evaluator-only output directory. Public count files omit the historical item contents.

## Failure semantics

- No frozen criterion set, second intake, missing historical item fields or unauthorized evaluator role refuses intake.
- A mapping with bad refs, double counting, incomplete partitions or contradictory exact/facet claims is refused with `mapping_refused`; it is not silently repaired.
- A missing registration/profile, changed anchor, used measurement profile or policy mismatch refuses the registered path.
- Drift is a reportable result. Missing evidence, model failure, extra criteria and an incomplete reference list retain their recorded status.

## Planned C19/C20 capabilities

The release has no general matched-budget P0/P1/P2 harness, policy-promotion conjunction, held-out strategy pool service, or strategy rollback authority. C20 strategy lineage/expiry/archive operations are planned. A fixed `strat@v1` binding and registered policy-arm labels are identifiers, not evidence that these services exist. Optional symbolic-expression selection is a separate implemented scoring experiment described in [ranking](ranking-and-explanations.md).

## Worked example: a near-equivalent match

**Illustrative:** a frozen derived criterion measures the same property and population as one historical item, but uses a different cutoff. The evaluator proposes a match with a threshold facet difference. The deterministic gate permits `near_equivalent` with that declared difference and refuses a simultaneous `exact` claim. The report counts one near-equivalent historical item and separately attributes whether the derived criterion came from literature, a task requirement or a template. It does not count multiple equivalent derived variants as multiple recovered historical items.

## Existing verification

[`test_freeze.py`](../../tests/test_freeze.py) covers required fields, unsupported fields, policy drift and separate artifact binding. [`test_measurement_profile.py`](../../tests/test_measurement_profile.py) and [`test_required_bindings.py`](../../tests/test_required_bindings.py) cover bound measurement semantics. [`test_recovery.py`](../../tests/test_recovery.py) checks frozen-only intake, mapping partitions, exact/near differences, origin stratification, evaluator independence and content-free public counts. [`test_firewall.py`](../../tests/test_firewall.py) checks the recorded exposure boundary.
