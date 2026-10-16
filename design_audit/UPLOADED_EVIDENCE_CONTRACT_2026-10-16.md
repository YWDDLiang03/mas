# Uploaded candidates and observations

Implemented in `src/mas/core/uploaded_evidence.py`. This path supplies local observations for drug, carrier or general entities. It does not import the drug adapter, retrieve literature, run predictors, invent cutoffs or modify existing measurements and leaderboards.

```python
from mas.core.uploaded_evidence import UploadedEvidence, ADAPTER, DIMENSIONS, TOOL_ID

uploaded = UploadedEvidence(
    canonical_candidates, canonical_measurements,
    library_id=library_id, dataset_sha256=fixed_dataset_hash,
    source_provenance=upload_metadata,
)
catalog = uploaded.property_catalog()  # metadata only; no candidate results
questions = uploaded.validate_task(task_context)
# The workflow saves blocking unknowns and waits for answers, then normalizes again.
# It must not mark normalization completed while these questions remain open.
pin = uploaded.materialize(core, task_id, by=import_actor)
record = existing_research.derive(
    core, roster, task_id, source_task_id=None,
    evidence_manifest_ref=pin['evidence_manifest_ref'], claims=pin['claims'],
    dimensions=DIMENSIONS, catalog=uploaded.catalog(),
    templates=uploaded.objective_templates,
    by=operator, settings=settings, implementation=implementation, budget=budget,
    observer=observer, checkpoint=checkpoint,
)
uploaded.register(broker)  # one local capability, no drug registration
controller = RunController(
    core, broker, roster, adapter=ADAPTER,
    identity_hook=uploaded.identity_hook, evidence_hook=uploaded.evidence_hook,
    evidence_manifest=uploaded.manifest(), existing_local_tool_ids=(TOOL_ID,),
    budget=budget, implementation=implementation,
)
```

`materialize` returns `claims`, `manifest`, `evidence_manifest_ref`. Materialization on the same task is idempotent. It persists admitted, structure-checked user rows with their explicit determination basis; this admission does not claim scientific review. The source kind remains `user_supplied_document`. Source title uses the uploaded filename, while the declared source, original identifiers, row locator and provenance remain inspectable. The evidence manifest pins each claim and source artifact by payload hash; `source_runs=[]` is valid. Claim/source identities include the library namespace and immutable dataset hash. An identical candidate ID in another library does not reuse these claims.

`existing_research.derive` adds optional keyword arguments `evidence_manifest_ref=None` and `claims=None`; `source_task_id=None` is permitted with an explicit manifest. The former source-task path is unchanged. An explicit manifest must contain admitted claim artifacts with matching IDs and hashes, a `source_runs` list and, when present, matching fixed source records. Supplied claims must match the pinned order and content. Reference exclusion, when requested, creates a separate proposal manifest referring to the original fact manifest. Resume keeps the binding's original manifest and batch order. This remains new proposal work, recorded as a new derivation run.

`property_catalog()` exposes property IDs, labels, units, condition profiles, bases and value types; it contains no candidate observations or derived thresholds. `validate_task(context)` returns answerable blocking unknowns for unmapped hard constraints, unspecified ambiguous conditions, unsupported units/comparisons or unbound required scope entities. `objective_templates(context)` creates mapped explicit hard requirements and required-property observations, and raises `UploadedRequirementsPending(findings)` if called before clarification. A task without a hard requirement receives no invented one; the existing qualification policy continues to report it as not ready.

The executable route is:

```json
{"capability":"uploaded_measurement_lookup","question_kind":"measurement",
 "identifier_scheme":"uploaded_id",
 "parameters":{"property":"exact trimmed property_id","conditions":{"description":"exact recorded condition"}}}
```

`identity_hook` keeps the user's `candidate_id` and exact input label for continuation. `claims_for(candidate_id, *, attribute_ref=None, attribute=...)` uses exact property and full condition equality, and leaves unit validation/conversion to the assessor. Missing conditions are not a wildcard. `evidence_hook(request)` always returns `(claims, None, searched)` including unsupported or absent routes, so generic candidates never fall through to drug tools. The local provider advertises the same capability in the tool manifest; assessment uses the hook to keep original claim provenance rather than restamping tool output as a database source.

The route codec accepts a plain condition string as the lossless shorthand `{"description": original_string}`. It performs no trimming, approximate match or deletion of experimental fields. A description-only shorthand cannot match a record that additionally specifies pH, temperature or other keys. This corrects the format mismatch observed when the paid GUI study generated a string condition for an otherwise identical description-object row. Source rows, factual manifests and claim IDs remain unchanged. Execution is versioned separately by `ROUTE_ENCODING_VERSION='uploaded_condition_encoding_v2'`, exposed as `uploaded.route_encoding_version` and included in the broker implementation version. The controller evidence manifest must also record this execution version so corrected screening cannot reuse old unknown cells. The prior failed snapshot remains historical; a new measurement/result binds the corrected implementation. Two format regressions plus the previous uploaded checks pass (9 tests); no paid validation was used.

Hard constraints use consensus across repeated observations; different outcomes remain conflicts. Predictions and simulations keep their declared basis and cannot alone satisfy a hard condition under `qualification_first_v1`. Numeric zero and Boolean false remain real values. No observed distribution establishes a task cutoff.

## Required property scope

An uploaded scope entity uses `entity_kind=property`, `identifier_scheme=uploaded_property`, and `identifier` equal to the exact `property_id`. It carries an exact condition object and compatible unit. A single recorded condition profile or unit can be bound without changing it; ambiguous or incompatible profiles require clarification. The normalizer supplies a direction only when the user expresses it. The helper checks that higher/lower ordering has a numeric encoding.

Each scope template derives from `scope_entities[i]`, and `evidence_request.parameters.property` equals the entity identifier. Existing required-binding audit and qualification therefore recognize this anchor without drug-specific identifiers. With an explicit numeric higher/lower direction it is an ordering preference. Without a direction it is an `exploratory_consideration` using the new opt-in `predicate_form=recorded_observation`, `cutoff=null`, `cutoff_basis=none_evidence_insufficient`. Other combinations are rejected by the registry.

`recorded_observation` returns `available` and retains the value and claim references when usable observations exist. It never returns Pass or contributes a preference score. Missing observations stay unknown; disagreeing observations under consensus or explicit counter-evidence stay conflicted. Boolean False is an available observation, not an asserted pass. Predictions cannot satisfy direct required scope. Existing cutoff-free rules without this explicit predicate retain their prior behavior.

The uploaded templates opt into `preserve_task_binding`: objective registration deduplicates these templates by measurement plus task field. This prevents a scope observation from silently absorbing a literal hard constraint reading the same property. Old templates retain their previous measurement-only deduplication. Neither duplicate observation anchors nor hard constraints add preference votes.

Scope validation: 31 passed using `tests/test_uploaded_evidence.py`, `tests/test_qualification_first.py`, `tests/test_existing_research_resume.py`, and `tests/test_workbench_normalization.py`. The temporary-store integration covers task anchors, deterministic literal-hard review, frozen measurement, controller hooks and a complete synthetic snapshot. It preserves no-hard not-ready, missing/predicted direct-scope blocking, existing qualification/scoring behavior, and the prior non-ordering cutoff-free unknown behavior. No primary store, paid model or network was used.

Validation: `python -B -m pytest tests/test_uploaded_evidence.py tests/test_existing_research_resume.py tests/test_workbench_uploads.py tests/test_workbench_normalization.py -q` — 14 passed. This uses temporary stores and a local ScriptedAdapter, with no network or paid model. It verifies typed row assessment, prediction-only hard unknown, condition isolation, stable user identity, cross-library claim separation, idempotent import, literal task review routing, explicit-manifest generation and prior continuation compatibility. It does not claim a new scientific ranking or replace the accepted snapshot2 result.
