# logP distance coordinates and shared-property scoring

The mathematical failure was confirmed from the exact public registry records, without reading other candidate rankings. Original `rule_lipophilicity-logp-optimal-band@v1` compared `distance_outside_band(XLogP;2,4)` against `>=2`, even though its definition preferred the band and penalised increasing distance. Its direction field was `within_range`, not `lower_better`. Therefore a raw value3.4 became distance0 and failed, while raw6 became distance2 and passed.

## Bounded impact check

[rules@v2 structural scan](transform_scope_rules_v2_2026-10-16.json) records all24 enabled rule/attribute refs, transforms, directions, predicates and cutoffs. Exactly one declared a transform: the faulty optimal-band criterion. No entry override fields were present; the controller loads the referenced rule/attribute records.

The same bounded inspection also confirmed a second mathematical mismatch: predicted `rule_lipophilicity-logp@v1` claimed preference for the complete2–4 band but used only raw `>=2`, so values above4 remained passing. Its own cited claim `claim_01M4YGKFT8T97H08A3RS5A2H24` explicitly calls logP≈2–4 optimal for kinase inhibitors, with `value_low=2`, `value_high=4`, DOI10.3390/ijms27156590, locator sec5.2.p3. Its other claim describes the typical range and is not independently labelled an optimal threshold. Evidence is retained in [the exact source lookup](raw_logp_band_support_2026-10-16.json).

The optimal-band criterion's original claim `claim_01M4X8AJ48X0A1MB80GB6V5YVY`, from that same DOI/locator, also explicitly provides2–4 as a heuristic. None of these statements was relabelled as a hard suitability threshold.

## Correct revision/review contract

Root owns the actual append-only scientific revisions. Both corrected contracts use `d(x)=max(2-x,0,x-4)`, `direction=lower_better`, `predicate_form=ordering`, `cutoff=None`, `cutoff_basis=none_evidence_insufficient`. Units, raw values, routes, bases, each criterion's own claims, and bounds2/4 remain preserved. Old cutoff support does not travel as support for a parameter that no longer exists.

The two attribute bounds have explicit **list-shaped** support records at `attribute.value_transform.low` and `.high`, each using the corresponding original claim, source number2/4, source unit from its quoted logP statement, `provides_heuristic`, identity conversion, and a declared interpretation/application to the kinase-inhibitor population. The existing `bound_interpretation_granted` route can review these records; no new generic approval route was needed. Grant is a real agent verdict, not automatic authority; refusal keeps the item pending. This route and both outcomes were verified in a temporary Core store.

## Implemented mechanical guard

`criteria.preference_execution_problems` now withholds:

- A `distance_outside_band` preference still using `within_range` and a nonzero raw band endpoint as its cutoff.
- A `lower_better` distance preference using `>`/`>=` a positive distance, which rewards movement away from the band.

It does not reject every transformed cutoff. Lower-better ordering with no cutoff, distance<=0, or a properly supported distance tolerance remains possible. A numeric tolerance coinciding with a raw endpoint is not rejected merely because the numbers match. Existing source/bound review remains in force.

## Shared quantity identity

The PubChem XLogP and RDKit logP routes both target molecular logP in log units from the candidate structure, with no differing experimental-condition parameters in these route contracts. They are different numerical estimators; the implementation does not pool or interchange their values or change their provenance.

Root explicitly assigned both revised contracts `quantity_id=octanol_water_log_partition_coefficient`. Only under an explicit ID, `criteria.quantity_identity` now hashes known-transform mathematical kind/parameters rather than `source_refs` or `basis`. Units and different boundaries still distinguish quantities. Without an explicit ID, the original route identity remains. Different experimental conditions or different scientific quantities require different IDs.

The read-only check of actual v2 records confirms both have no readiness findings and share key:

`4fb8aec22936ff5a349a4e9c9214575977c7162a61ca8baf1bb6686277a9221e`

[Actual v2 contract check](logp_v2_math_readonly_2026-10-16.json) retains each route and its own support. This lets the existing direct-first policy suppress a second predictive contribution when a direct value is available, without changing weights or coverage policy.

## Verification

- Distance/readiness/bound-support/unresolved-review combination: **37 passed in1.59s**.
- Final quantity-identity/qualification/distance combination after the identity change: **25 passed in2.70s**.
- Tests reproduce the inverted original arithmetic, verify corrected distance ordering, preserve valid distance tolerances, exercise real temporary-store grant/refuse review, and show that an opposite predictive estimate cannot add a second score when the explicit quantity has direct evidence. Different units, bounds and condition IDs remain distinct.

Changed source is limited to `core/criteria.py`; regression changes are `tests/test_distance_band_readiness.py` and an extension to `tests/test_qualification_first.py`. No adjudication module change, primary scientific write, paid call, weight change or qualification-threshold change was made by this agent. Root controls versioned data revisions, real review, new freeze and re-evaluation; previous snapshots remain preserved.
