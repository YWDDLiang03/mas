# Derived criteria — review snapshot (historical baseline)

**Label:** `historical_baseline_pre_repair`

Pre-repair historical baseline. These records are exported unchanged from the live store. They are the output of a derivation whose merge stage performed zero merges across every round, whose proposer/critic debate deferred its disagreements to the review queue rather than settling them, and whose open disputes are still open. No criterion was improved, corrected or tidied during export; corrected records belong to a later version published with a diff.

**Snapshot:** task stream `task_01M4TWZXZEB1SQPS7H47C8BX01` pinned at journal sequence 516. The exact records behind every card are in `derived_criteria_review.json`; the refs, hashes and code commit are in `derived_criteria_manifest.json`. The counts below are reconciled in `criteria_count_reconciliation.md`.

## The task these criteria were derived for

- **task context** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1` · mode `conditional` · group `grp_primary-case`
- **objective**: Identify a single orally administered agent that concurrently engages the stated tumour-microenvironment targets (CSF1R, VEGFR1, VEGFR2, VEGFR3, FGFR1), with a pharmacological profile suitable for clinical development
- **objective provenance**: reconstructed_pending_author_confirmation (case_study_protocol.md §2.1)
- **required scope entities**: CSF1R (`CHEMBL1844`, required), VEGFR1 (`CHEMBL1868`, required), VEGFR2 (`CHEMBL279`, required), VEGFR3 (`CHEMBL1955`, required), FGFR1 (`CHEMBL3650`, required)
- **constraints**: `[{"hardness": "hard", "kind": "route", "provenance": "manuscript", "text": "oral administration"}]`
- **candidate universe**: `{"access_path": "var/primary/universe_chembl.json", "as_of": "2026-10-13", "kind": "named_library", "size_if_known": 3177, "source": "ChEMBL small molecules with max_phase >= 3, salts collapsed to parents (reconstruction; the authors' 3,171-compound list was not available)"}`
- **case source documents held out of derivation evidence**: `[{"identifiers": [{"scheme": "sha256", "value": "4332685173c953ddaf7adb855965378da580958fa904fd97ca9017acb34153d2"}], "note": "the case manuscript; declared by content hash as well as title so an uploaded copy or its supplement cannot enter derivation evidence", "title": "Multi-target TME Reprogramming Awakens TLS-driven Immunity in Ovarian Cancer"}]`
- **declared reference outcome**: `[{"aliases": ["sulfatinib", "HMPL-012"], "candidate_ref": "surufatinib", "is_reference_outcome": true, "reason_supplied": "manuscript-reported outcome"}]`

## How to read a card

Three things are reported separately and must not be read as one status.

1. **Quote check** — did the recorded span match the source text (`claim.location.span_checked_against_source`, and `quote_verified` among the admission reasons)?
2. **Numerical consistency** — was the number the criterion uses present in that span (`value_in_quote` / `value_not_in_quote` among the admission reasons)?
3. **Semantic support** — did anything judge that the passage *justifies* this bound for this task (`claim.verification_status`)? `unverified` means the check was never run, not that the quotation failed.

Each card also opens with **recovery-comparison facets**: the operational quantity, the applicability, the decision semantics and the threshold, read from the fields that execute rather than from the definition prose, with a hash over the measurement identity and over the decision identity so two criteria can be called the same or different mechanically. Where this schema records no field for a facet, the card says so under `gap:` instead of supplying a value.

## Counts at this snapshot

| quantity | value | what it counts |
|---|---|---|
| `proposals_added_to_pool` | `72` | pool lineages created by the propose stage, over every round in this task |
| `pool_lineages` | `72` | distinct `cri_` lineages the pool ever held |
| `promoted_pool_items` | `34` | pool lineages whose final state is `promoted`; each wrote one attribute and one rule into the registry |
| `pruned_pool_items` | `38` | pool lineages that never reached the registry, by final state: withdrawn 38 |
| `registered_criteria` | `40` | distinct attribute ids in the registry, each paired with one rule id; this is the promoted pool items plus the criteria the adapter templates registered without entering the pool |
| `registered_from_pool` | `34` | registered criteria whose attribute a pool promotion wrote |
| `registered_from_templates` | `6` | registered criteria an adapter template wrote directly, bypassing the pool |
| `registry_versions` | `{"attribute": 47, "rule": 47}` | attribute and rule *versions*, not criteria; a second version is a revision of one criterion, not another criterion |
| `scoring_now` | `9` | rules in rules@v3, the latest confirmed set |
| `deferred_now` | `26` | registered rules held out of the latest set because a capability they need was not run |
| `collapsed_away_now` | `5` | registered rules whose attribute a collapse merged away |
| `collapses` | `{"applied": 5, "withdrawn": 0}` | collapse records; each merged several registrations of one quantity into one attribute reading every route |
| `review_queue` | `{"machine_adjudicated": 3, "open": 9}` | review items raised against this task, by state |
| `unresolved_disputes` | `9` | open review items raised because a proposer and a critic still disagreed after one revision |
| `machine_adjudications` | `3` | items resolved by software with no person; recorded as `agent_verdict`, never as an expert approval |
| `expert_decisions` | `0` | `hd_` records; an expert decision needs a person at a terminal |
| `bounds` | `{"no_cutoff_evidence_insufficient": 39, "source_stated_with_claims": 2, "task_constraint_cutoff": 1}` | registered criteria carrying a numeric bound whose basis is a cited claim, a bound restating a task constraint, and no bound at all |
| `comparable_from_fields` | `0` | registered criteria all four rubric facets can be read off without reading prose; the applicability gap is schema-wide, so this is zero while no attribute records applicability as a field |
| `matching_facet_gaps` | `{"applicability": 40, "decision_semantics": 3, "operational_quantity": 26, "threshold": 1}` | registered criteria whose records do not answer one of the four recovery-rubric facets from fields alone; the cards name the absence per criterion |

## Confirmed rule sets

| rule set | scoring | pending | deferred | collapsed away | label |
|---|---|---|---|---|---|
| `rules@v1` | 13 | 10 | 26 | 0 | `exploratory` |
| `rules@v2` | 13 | 10 | 26 | 0 | `exploratory` |
| `rules@v3` | 9 | 9 | 26 | 5 | `exploratory` |

`rules@v1` is labelled `exploratory` because:
- 10 rule proposals await an expert decision

`rules@v2` is labelled `exploratory` because:
- 10 rule proposals await an expert decision
- 5 of them score candidates while disputed: rule_csf1r-affinity-on-the-independent-expert-curation@v1, rule_fgfr1-affinity-on-the-independent-expert-curation@v1, rule_vegfr1-affinity-on-the-independent-expert-curation@v1, rule_vegfr2-affinity-on-the-independent-expert-curation@v1, rule_vegfr3-affinity-on-the-independent-expert-curation@v1

`rules@v3` is labelled `exploratory` because:
- 9 rule proposals await an expert decision
- 3 rules were adjudicated by an agent; no person has confirmed them: rule_approved-oral-route-on-record@v1, rule_distance-of-computed-lipophilicity-outside-the-stated-band@v2, rule_molecular-weight-in-excess-of-the-stated-upper-bound@v2
- 5 rules read an attribute version the software wrote when it collapsed several registrations of one quantity; no person confirmed that: rule_csf1r-curated-potency@v2, rule_fgfr1-curated-potency@v2, rule_vegfr1-curated-potency@v2, rule_vegfr2-curated-potency@v2, rule_vegfr3-curated-potency@v2
- 5 rules are held out of this set because the software merged their attributes away: rule_csf1r-affinity-on-the-independent-expert-curation@v1, rule_fgfr1-affinity-on-the-independent-expert-curation@v1, rule_vegfr1-affinity-on-the-independent-expert-curation@v1, rule_vegfr2-affinity-on-the-independent-expert-curation@v1, rule_vegfr3-affinity-on-the-independent-expert-curation@v1

## The board these criteria were last applied on

- **snapshot** `lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4` on `rules@v3`, run `run_01M4WYBBYWD518XGX2CYP74FK1`, published 2026-10-14T11:06:34.347Z
- **candidates assessed** 3177 · **ranked** 95 · result kind `both_reported`
- **reporting tuple**: `{"abstention_n_by_reason": {"awaiting_human_review": 1269, "hard rule unknown": 1262}, "admitted_n": 0, "budget": {"caps": {"usd": 20.0}, "soft_kinds": ["usd"], "used": {"tool_calls": 47656}, "warn_at": 0.8}, "coverage_fraction": 0.39436225649634526, "precision_among_admitted": null, "ranking_coverage_floor": 0.5, "sweep_completeness": 1.0, "unranked_for_coverage": 2989}`
- **human review summary**: `{"expert_confirmed_n": 0, "expert_confirmed_rules": [], "machine_adjudicated_n": 3, "machine_adjudicated_rules": ["rule_approved-oral-route-on-record@v1", "rule_distance-of-computed-lipophilicity-outside-the-stated-band@v2", "rule_molecular-weight-in-excess-of-the-stated-upper-bound@v2"], "note": "3 of this board's rules were adjudicated by an agent; no person has confirmed them", "recommended_requires_hd": true}`
- snapshot artifact `art_32fcc3c536c8` sha256 `32fcc3c536c85a21ba2cc1f7feaf4425eb66de15bf04a05a0635b7fdab2bf0fb`

## Derivation trajectory

| round | iteration | stage | added | revised | merged away | removed | promoted | live after | reasons |
|---|---|---|---|---|---|---|---|---|---|
| `run_01M4TX07ME8VWFJGK2PKNNGSEF` | 0 | `propose` | 72 | 0 | 0 | 0 | 0 | 72 | `{"new_evidence": 72}` |
| `run_01M4TX07ME8VWFJGK2PKNNGSEF` | 1 | `filter` | 0 | 71 | 0 | 0 | 0 | 72 | `{"critic_findings": 47, "validator_findings": 24}` |
| `run_01M4TX07ME8VWFJGK2PKNNGSEF` | 1 | `distill` | 0 | 1 | 0 | 0 | 0 | 72 | `{"distilled": 1}` |
| `run_01M4TX07ME8VWFJGK2PKNNGSEF` | 1 | `refine` | 0 | 14 | 0 | 6 | 0 | 66 | `{"refined": 14, "withdrawn_by_reviser": 6}` |
| `run_01M4V43E8GDH8GF8M633VTWDQJ` | 1 | `refine` | 0 | 17 | 0 | 3 | 0 | 63 | `{"refined": 17, "withdrawn_by_reviser": 3}` |
| `run_01M4V52W85KZMCC0X2A7BN1YR3` | 1 | `filter` | 0 | 5 | 0 | 0 | 0 | 63 | `{"validator_findings": 5}` |
| `run_01M4VABCW4TS9P3FJC0K7M8JC9` | 1 | `filter` | 0 | 46 | 0 | 0 | 0 | 63 | `{"critic_findings": 46}` |
| `run_01M4VABCW4TS9P3FJC0K7M8JC9` | 1 | `refine` | 0 | 38 | 0 | 24 | 0 | 39 | `{"refined": 31, "refined_still_failing": 7, "withdrawn_by_reviser": 24}` |
| `run_01M4VABCW4TS9P3FJC0K7M8JC9` | 2 | `filter` | 0 | 25 | 0 | 0 | 0 | 39 | `{"critic_findings": 25}` |
| `run_01M4VABCW4TS9P3FJC0K7M8JC9` | 2 | `refine` | 0 | 27 | 0 | 5 | 0 | 34 | `{"refined": 27, "withdrawn_by_reviser": 5}` |
| `run_01M4VABCW4TS9P3FJC0K7M8JC9` | 0 | `promote` | 0 | 0 | 0 | 0 | 34 | 34 | `{"accepted": 25, "disputed": 9}` |

## The derived set, for a later recovery comparison

The derived set for a recovery mapping: every registered criterion whose quantity is not already carried by another registered criterion. Pruned pool items are in the lifecycle section and are not derived criteria. Nothing here is shaped by any knowledge of the sealed historical list.

- **35 registered criteria** form the derived set: literature_derived 29 · task_mandated_template 6
- **5 excluded as a repeated variant** of a quantity another criterion already carries:
  - `attr_csf1r-affinity-on-the-independent-expert-curation@v1` (CSF1R affinity on the independent expert curation) — same quantity as `attr_csf1r-curated-potency@v2`; its attribute was merged into attr_csf1r-curated-potency@v2 by clp_01M4WXKPA3MBD055HSNCBV43AA; rule_csf1r-curated-potency@v2 scores the quantity
  - `attr_fgfr1-affinity-on-the-independent-expert-curation@v1` (FGFR1 affinity on the independent expert curation) — same quantity as `attr_fgfr1-curated-potency@v2`; its attribute was merged into attr_fgfr1-curated-potency@v2 by clp_01M4WXKPEB4X4X3ZSBETYZ9EXX; rule_fgfr1-curated-potency@v2 scores the quantity
  - `attr_vegfr1-affinity-on-the-independent-expert-curation@v1` (VEGFR1 affinity on the independent expert curation) — same quantity as `attr_vegfr1-curated-potency@v2`; its attribute was merged into attr_vegfr1-curated-potency@v2 by clp_01M4WXKPKBRKYT0M0QJ6FP1BJ4; rule_vegfr1-curated-potency@v2 scores the quantity
  - `attr_vegfr2-affinity-on-the-independent-expert-curation@v1` (VEGFR2 affinity on the independent expert curation) — same quantity as `attr_vegfr2-curated-potency@v2`; its attribute was merged into attr_vegfr2-curated-potency@v2 by clp_01M4WXKPQ837MK8GF71Y7F5YVH; rule_vegfr2-curated-potency@v2 scores the quantity
  - `attr_vegfr3-affinity-on-the-independent-expert-curation@v1` (VEGFR3 affinity on the independent expert curation) — same quantity as `attr_vegfr3-curated-potency@v2`; its attribute was merged into attr_vegfr3-curated-potency@v2 by clp_01M4WXKPVCG360VDRWPCXAM2EN; rule_vegfr3-curated-potency@v2 scores the quantity
- **38 pruned pool items** are in the lifecycle section below and are not derived criteria
- duplicate measurement identities remaining inside the derived set: —

## Index of registered criteria

| # | criterion | attribute | rule kind | cutoff | status |
|---|---|---|---|---|---|
| 1 | Approved oral route on record | `attr_approved-oral-route-on-record@v1` | `hard_exclusion` | `{"comparator": "==", "unit": null, "value": true}` | `scoring` |
| 2 | Change in exposure with gastric acid suppression | `attr_change-in-exposure-with-gastric-acid-suppression@v1` | `preference` | — | `deferred` |
| 3 | Concentration of elimination in the predominant excretory route | `attr_concentration-of-elimination-in-the-predominant-excretory-ro@v1` | `preference` | — | `deferred` |
| 4 | Concentration-QTc upper bound at the highest modelled exposure | `attr_concentration-qtc-upper-bound-at-the-highest-modelled-exposu@v1` | `preference` | — | `deferred` |
| 5 | CSF1R affinity on the independent expert curation | `attr_csf1r-affinity-on-the-independent-expert-curation@v1` | `preference` | — | `collapsed_away` |
| 6 | CSF1R curated potency | `attr_csf1r-curated-potency@v2` | `preference` | — | `scoring` |
| 7 | Distance of computed lipophilicity outside the stated band | `attr_distance-of-computed-lipophilicity-outside-the-stated-band@v2` | `preference` | — | `scoring` |
| 8 | Exposure loss with a strong CYP3A inducer | `attr_exposure-loss-with-a-strong-cyp3a-inducer@v1` | `preference` | — | `deferred` |
| 9 | Exposure ratio with a strong CYP3A inhibitor | `attr_exposure-ratio-with-a-strong-cyp3a-inhibitor@v1` | `preference` | — | `deferred` |
| 10 | FGFR1 affinity on the independent expert curation | `attr_fgfr1-affinity-on-the-independent-expert-curation@v1` | `preference` | — | `collapsed_away` |
| 11 | FGFR1 curated potency | `attr_fgfr1-curated-potency@v2` | `preference` | — | `scoring` |
| 12 | Food effect on systemic exposure as a fold deviation | `attr_food-effect-on-systemic-exposure-as-a-fold-deviation@v1` | `preference` | — | `deferred` |
| 13 | Fraction of a profiling panel inhibited outside the required target set | `attr_fraction-of-a-profiling-panel-inhibited-outside-the-required@v1` | `preference` | — | `deferred` |
| 14 | Hydrogen-bond donor count | `attr_hydrogen-bond-donor-count@v1` | `preference` | — | `scoring` |
| 15 | Incidence of any-grade proteinuria | `attr_incidence-of-any-grade-proteinuria@v1` | `preference` | — | `deferred` |
| 16 | Incidence of central serous retinopathy | `attr_incidence-of-central-serous-retinopathy@v1` | `preference` | — | `deferred` |
| 17 | Incidence of grade 3 or higher haemorrhage | `attr_incidence-of-grade-3-or-higher-haemorrhage@v1` | `exploratory_consideration` | — | `deferred` |
| 18 | Incidence of grade 3 or higher hand-foot skin reaction | `attr_incidence-of-grade-3-or-higher-hand-foot-skin-reaction@v1` | `preference` | — | `deferred` |
| 19 | Incidence of grade 3 or higher hypertension | `attr_incidence-of-grade-3-or-higher-hypertension@v1` | `exploratory_consideration` | — | `deferred` |
| 20 | Incidence of grade 3 or higher serum phosphate elevation | `attr_incidence-of-grade-3-or-higher-serum-phosphate-elevation@v1` | `exploratory_consideration` | — | `deferred` |
| 21 | Measured change in a co-administered drug's exposure | `attr_measured-change-in-a-co-administered-drug-s-exposure@v1` | `preference` | — | `deferred` |
| 22 | Molecular weight in excess of the stated upper bound | `attr_molecular-weight-in-excess-of-the-stated-upper-bound@v2` | `preference` | — | `scoring` |
| 23 | Number of hepatic impairment grades at which dosing is restricted | `attr_number-of-hepatic-impairment-grades-at-which-dosing-is-restr@v1` | `preference` | — | `deferred` |
| 24 | Number of molecules required to achieve the reported coverage | `attr_number-of-molecules-required-to-achieve-the-reported-coverag@v1` | `preference` | — | `deferred` |
| 25 | Number of renal function strata at which dosing is restricted | `attr_number-of-renal-function-strata-at-which-dosing-is-restricte@v1` | `preference` | — | `deferred` |
| 26 | Number of required receptors named as covered in the literature | `attr_number-of-required-receptors-named-as-covered-in-the-literat@v1` | `preference` | — | `deferred` |
| 27 | Number of required receptors with measured rather than predicted engagement | `attr_number-of-required-receptors-with-measured-rather-than-predi@v1` | `preference` | — | `deferred` |
| 28 | Oral doses required per day | `attr_oral-doses-required-per-day@v1` | `preference` | — | `deferred` |
| 29 | Proportion of patients requiring a dose reduction | `attr_proportion-of-patients-requiring-a-dose-reduction@v1` | `preference` | — | `deferred` |
| 30 | Rate of grade 3 or higher treatment-related adverse events | `attr_rate-of-grade-3-or-higher-treatment-related-adverse-events@v1` | `preference` | — | `deferred` |
| 31 | Reported oral bioavailability in humans | `attr_reported-oral-bioavailability-in-humans@v1` | `preference` | — | `deferred` |
| 32 | Time to steady state on repeated oral dosing | `attr_time-to-steady-state-on-repeated-oral-dosing@v1` | `preference` | — | `deferred` |
| 33 | Transporter-mediated change in systemic exposure | `attr_transporter-mediated-change-in-systemic-exposure@v1` | `preference` | — | `deferred` |
| 34 | Treatment discontinuation rate due to adverse events | `attr_treatment-discontinuation-rate-due-to-adverse-events@v1` | `preference` | — | `deferred` |
| 35 | VEGFR1 affinity on the independent expert curation | `attr_vegfr1-affinity-on-the-independent-expert-curation@v1` | `preference` | — | `collapsed_away` |
| 36 | VEGFR1 curated potency | `attr_vegfr1-curated-potency@v2` | `preference` | — | `scoring` |
| 37 | VEGFR2 affinity on the independent expert curation | `attr_vegfr2-affinity-on-the-independent-expert-curation@v1` | `preference` | — | `collapsed_away` |
| 38 | VEGFR2 curated potency | `attr_vegfr2-curated-potency@v2` | `preference` | — | `scoring` |
| 39 | VEGFR3 affinity on the independent expert curation | `attr_vegfr3-affinity-on-the-independent-expert-curation@v1` | `preference` | — | `collapsed_away` |
| 40 | VEGFR3 curated potency | `attr_vegfr3-curated-potency@v2` | `preference` | — | `scoring` |

## Cards

### 1. Approved oral route on record

- **attribute** `attr_approved-oral-route-on-record@v1` · **rule** `rule_approved-oral-route-on-record@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_approved-oral-route-on-record@v1"]`, rule `["rule_approved-oral-route-on-record@v1"]`; supersedes —
- **record hashes**: attribute `3a873a8a97ceebb8da900e5c13815c2cddb3f6a8a812882cf832c1a0a002db2d`, rule `07d39a8017ffb7316a54ee0fe2e51996aebf2d285e0fdd62d6ff9f30d7684704`
- **origin**: `task_mandated_template` · proposed by `{"id": "objective-criteria", "kind": "system", "role": "adapter_template"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"field": "constraints[0]", "task_context": "task_01M4TWZXZEB1SQPS7H47C8BX01@v1"}` · dimension —
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Approved oral route on record · subject `[{"field": "oral"}]` · unit — · `categorical` · aggregated by `consensus` · transform —
  - read from `["record_field_lookup"]` asking `["record_field"]`; evidence kinds `["database_entry"]`; determination bases `["measured", "derived"]`
  - measurement identity `7a464cf427b91b924d9ed73f3a76bb4d4c63ae1d463b018061e0350809ecf269`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_blocks_recommendation` · condition field —
- **decision semantics**: role `hard_constraint` (`hard_exclusion`) · predicate form `categorical_membership` · direction `non_directional`
  - predicate: passes when the aggregated value is == True
  - on missing `unknown_blocks_recommendation` · on conflict `unknown_blocks_recommendation` · decision identity `b2854588438105d74469a137d82449515907d7bfa67b97cf8069ac0c4e9c0d04`
- **threshold**: `present` — `== True` · basis `task_constraint` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose
  - gap: threshold: a cutoff is present and the schema records no per-cutoff support record, so which passage justifies this number is not stated

**Operational definition**

> Whether an approved product of the compound is recorded with an oral route

- **unit** — · **measurement kind** `categorical` · **direction** `non_directional` · **aggregation** `consensus`
- **accepted evidence kinds** `["database_entry"]` · **accepted determination bases** `["measured", "derived"]`
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_blocks_recommendation", "stated_in_definition_only": true}`
- **expected change**: —
- **falsification test**: —
- **rationale**: the task's hard constraint: oral administration

**Rule**

- **kind** `hard_exclusion` · **predicate form** `categorical_membership` · **cutoff** `{"comparator": "==", "unit": null, "value": true}` (`present`) · **cutoff basis** `task_constraint`
- **on missing** `unknown_blocks_recommendation` · **on inapplicable** `unknown_blocks_recommendation` · **on conflict** `unknown_blocks_recommendation`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `a6a8aa760f90ed342be38cc0984c81b4087f862acde756b8d9ac2075f214b14c` · 1 route(s) · literature-bound `False`
  - route `record_field_lookup` / `record_field` · subject `{"field": "oral"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- `rule.cutoff.value` = `True` `==` unit — · basis `task_constraint` · claims — · support field: none; the rule schema carries no per-cutoff support record

**Verification, reported as three separate checks**

- quote check — of 0 cited claim(s), 0 carry `location.span_checked_against_source: true` and 0 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` — (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: —
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

**Critique, adjudication and authority**

- authority this criterion owes before it may score: `hard_exclusion` (a hard exclusion deletes candidates from the result); `cutoff_basis_task_constraint` (the cutoff claims cutoff_basis task_constraint)
- expert decisions: —
- machine adjudication `adj_01M4WY583JYPE9SJSG68C6KB8A` · route `task_constraint_restated` · resolution `approve` · approval kind `agent_verdict` · confirmed by a person `False`
  - reason: the cutoff restates constraints[0] of task_01M4TWZXZEB1SQPS7H47C8BX01@v1 ('oral administration'), which the task context states itself
  - cites: `{"constraint_text": "oral administration", "field": "constraints[0]", "hardness": "hard", "match": "derived_from_task_field", "provenance": "manuscript", "task_context_ref": "task_01M4TWZXZEB1SQPS7H47C8BX01@v1"}` · claims — · independence —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage — at version —, state —
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history: — (this criterion never entered the pool)

**Use**

- status `scoring` on `rules@v3`
- rule-set entry: `{"acceptable_value_sources": ["database_entry"], "attribute_ref": "attr_approved-oral-route-on-record@v1", "authority": "machine_adjudication", "confirmed_by": "adj_01M4WY583JYPE9SJSG68C6KB8A", "cutoff_basis": "task_constraint", "disputed": false, "on_states": ["unknown_blocks_recommendation", "unknown_blocks_recommendation", "unknown_blocks_recommendation"], "rule_kind": "hard_exclusion", "rule_ref": "rule_approved-oral-route-on-record@v1"}`
- scores while disputed: `False` · machine adjudicated: `True` · reads a collapsed attribute: `False`
- measured coverage: `{"assessed": 3177, "board": "lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4", "observed": 1915}`

---

### 2. Change in exposure with gastric acid suppression

- **attribute** `attr_change-in-exposure-with-gastric-acid-suppression@v1` · **rule** `rule_change-in-exposure-with-gastric-acid-suppression@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_change-in-exposure-with-gastric-acid-suppression@v1"]`, rule `["rule_change-in-exposure-with-gastric-acid-suppression@v1"]`; supersedes —
- **record hashes**: attribute `f3650aa4f952badf3a61bfd83047e6cb736e3fb97bfb3bba78182578d4e4bf3f`, rule `5043908c87ae49022410a82dd7f4c5b92e5478a2fdc0367bbf3d7edf7b1c8592`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1FPHDRCKC2XYZKA0ER1ED@v5"}` · dimension `oral_bioavailability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Change in exposure with gastric acid suppression · subject `[{}]` · unit `% change in AUC (magnitude)` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `9fd40ac1f5cdd676f60a0b62d0fb30312bc5330521c375d586aa2ed590284a40`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `b2105ff9fac4ebdd14a33fc4e16858c196a4d191674580f4361dba3ebc8fd01d`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The magnitude of the percentage change in systemic exposure (AUC) when the compound is co-administered with an acid-reducing agent, taken from a dedicated interaction study and entered as a non-negative number: a 53 percent fall enters as 53 and a 13 percent fall as 13, and a rise of the same size enters identically. The sign of the change, the class of acid-reducing agent and the formulation studied are recorded alongside the value but are not scored, so the predicate orders candidates by how far exposure moves and never ranks a larger loss as better than a smaller one. Smaller magnitude is better. Where no dedicated study exists the attribute returns unknown, which carries no penalty and leaves the candidate unranked on this attribute rather than scored as insensitive; where the source describes the compound as a weak base with pH-dependent solubility that liability is recorded as an annotation for a later stage to read, not converted into a score, because this evidence supports no number for it. Because the magnitude depends on the salt form, solid-state form and excipients of the product studied, a value may not be transferred between formulations.

- **unit** `% change in AUC (magnitude)` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates with a dedicated study showing little change rank above candidates with a large measured reduction, in either direction of effect, while candidates with no study are unranked on this attribute and carry a recorded pH-dependence annotation for a later stage rather than a score.
- **falsification test**: List which candidates have a dedicated acid-suppression study. If most candidates are unranked the attribute discriminates little and the recorded annotations, not the score, carry the dimension; if the recorded pH-dependence annotations turn out to predict the measured magnitudes well, a later iteration can propose a scored quantity for them on evidence this request does not contain.
- **rationale**: The cited quotes establish both the mechanism and the spread of measured magnitudes. A majority of orally administered molecularly targeted agents are weak bases with pH-dependent solubility whose absorption is impaired by acid suppression, described as a potential Achilles heel of targeted therapy, and acid-reducing agents are among the most commonly used medicines in the oncology population. For weakly basic compounds solubility is highest in the acidic fasted stomach, so loss of gastric acidity reduces the fraction dissolved. Measured effects run from no clinically meaningful change, through a 41 percent fall in peak concentration with only 13 percent in AUC, to AUC reductions of 43 and 53 percent, and one quote records that the same agent is judged differently by two regulators. Because every measured value is a reduction while the mechanism admits either direction, the quantity is the unsigned magnitude and the sign is recorded, so the ordering cannot invert. A further quote ties the magnitude to the formulation studied, which is why the definition forbids transferring values between products. Nothing in the cited evidence states an acceptable magnitude, so the rule is an ordering with no cutoff, and nothing in it supports a numeric penalty for an untested compound, which is why the pH-dependence liability is recorded rather than scored.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `8aa66c8f668a0325a4b972a3e79dbd0a715f3a204668b3eb4eab53407a4ca6c9` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"proton pump inhibitor\" OR omeprazole OR esomeprazole OR rabeprazole OR famotidine OR antacid OR \"acid-reducing\" OR \"gastric pH\") AND (AUC OR Cmax OR exposure OR solubility)", "relevance_terms": ["proton pump inhibitor", "gastric pH", "antacid", "AUC", "solubility"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 6 cited claim(s), 6 carry `location.span_checked_against_source: true` and 6 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 2, `value_not_in_quote` 0, not recorded 4 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 6}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 4, "inconclusive": 1, "supports": 1}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TYZ65SAGNN580844FW8ZR6** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > For weakly basic compounds, solubility is pH-dependent and highest in the acidic environment of the fasted stomach, so loss of gastric acidity can reduce the fraction dissolved and available for absorption
  - as recorded (paraphrase): For weakly basic compounds solubility is pH-dependent and highest in the acidic fasted stomach, so loss of gastric acidity reduces the fraction dissolved and available for absorption.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec4.1.p1`, section 4. Pharmacokinetic Determinants of Oral Anticancer Drug Exposure / 4.1. Solubility and Dissolution; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_3e5c4570c28e` sha256 `3e5c4570c28eb6e75c5179e1c166a1485ef2db1b01878b7ebb7c2922571bf14e` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 663
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`
- **claim_01M4TYZ6D2XAE62ZP5K53JNCAG** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > A majority of orally administered, molecularly targeted anticancer agents are weak bases that exhibit pH-dependent solubility, such that suppression of gastric acidity can impair their absorption—a vulnerability that has been described as a potential “Achilles heel” of targeted therapy [17,18]. The clinical relevance of this mechanism is amplified by epidemiology: acid-reducing agents—proton pump inhibitors (PPIs), histamine H2-receptor antagonists (H2RAs), and antacids—are among the most commonly used medications in the oncology population, and they are frequently taken without the prescriber’s or patient’s awareness of an interaction with cancer therapy
  - as recorded (paraphrase): A majority of oral molecularly targeted anticancer agents are weak bases with pH-dependent solubility whose absorption is impaired by gastric acid suppression, and acid-reducing agents are among the most commonly used medications in the oncology population.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec6.p1`, section 6. Gastric pH, Acid-Suppressive Therapy, and Absorption; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_a299ce595b53` sha256 `a299ce595b53275a7a69258e832842c457ecc0ae403a70f21692c9a6c5252a76` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 685
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`
- **claim_01M4TYZ6EQ6GKNF22ZX6FQYDJT** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% reduction in AUC with antacid", "unit_as_reported": "% reduction in AUC with antacid", "value": 53, "value_high": null, "value_low": null}`
  > Acalabrutinib—a structurally distinct second-generation BTK inhibitor approved for similar indications—has solubility that decreases with rising pH, with the result that the PPI omeprazole reduces acalabrutinib AUC by 43%, calcium-carbonate antacid reduces AUC by 53%, and the label recommends avoiding concomitant PPIs entirely while staggering H2RAs and antacids by at least two hours [55]. Two drugs against the same target, in the same diseases, with categorically different acid-suppression instructions—an instructive lesson in why class membership does not predict pharmacokinetic behavior and why agent-level review is necessary at every initiation
  - as recorded (paraphrase): One agent whose solubility decreases with rising pH loses 43% of AUC with a proton pump inhibitor and 53% with a calcium-carbonate antacid while a same-target agent has no such interaction, showing that class membership does not predict pharmacokinetic behaviour.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec6.p4`, section 6. Gastric pH, Acid-Suppressive Therapy, and Absorption; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_59ba9a03d210` sha256 `59ba9a03d210c1ad031f724529685fa42de70ad1aa4e84e25a287c1955fc81ec` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 690
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TYZ6F30J0KEF9W5FQ4K941** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Cytochrome P450 and transporter interactions are largely properties of the active molecule, whereas the magnitude of an acid-suppression interaction depends on dissolution behavior and therefore on the salt form, the solid-state form and the excipients of the particular product studied, so each value applies to the formulation examined in the cited source and should not be transferred without qualification to a different product of the same molecule
  - as recorded (paraphrase): Cytochrome P450 and transporter interactions are properties of the active molecule whereas the magnitude of an acid-suppression interaction depends on dissolution behaviour and therefore on salt form, solid-state form and excipients of the particular product studied.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec6.p5`, section 6. Gastric pH, Acid-Suppressive Therapy, and Absorption; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_8638fcc0f4ff` sha256 `8638fcc0f4ff0665364233e411010d7571af39ece083b2772d9def4d4445841e` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 691
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`

*polarity `inconclusive`*

- **claim_01M4TYZ6EDF3VDKSFTB1B58KKV** · `inconclusive` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% reduction in AUC", "unit_as_reported": "% reduction in AUC", "value": 13, "value_high": null, "value_low": null}`
  > an agent may be pH-dependent in vitro yet show little clinically meaningful interaction in vivo: the palbociclib label reports that rabeprazole, under fed conditions, reduced Cmax by 41% but AUC by only 13%
  - as recorded (paraphrase): An agent can be pH-dependent in vitro yet show little clinically meaningful interaction in vivo, with one example showing a 41% Cmax reduction but only a 13% AUC reduction.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec6.p3`, section 6. Gastric pH, Acid-Suppressive Therapy, and Absorption; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_2e20a29b4075` sha256 `2e20a29b4075fdb6e0955ed0b3931341c40a3d7847b25bf5d0feb1c3156ae3df` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 689
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

*polarity `supports`*

- **claim_01M4TX98YYX1FVXEK7AB58N46T** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > When administering specific TKIs, many factors can contribute to reduced potency and the development of acquired resistance. These factors include such as whether or not food intake affects bioavailability, the mechanism of drug metabolism and elimination, liver and kidney function, drug-drug interactions, the presence of other medications that alter stomach pH, and patient demographics.
  - as recorded (paraphrase): Factors that can reduce the potency of an administered tyrosine kinase inhibitor and promote acquired resistance include whether food intake affects bioavailability, the mechanism of metabolism and elimination, liver and kidney function, drug-drug interactions, co-medications that alter stomach pH, and patient demographics.
  - in `src_nbk_NBK563322` at `paragraph` `article-109800.s4.p1`, section Administration; document `art_f39aa2170bbb` sha256 `f39aa2170bbb6e797aa143c217673d26d91bf5238802cedbd23bc4621ce110fc`; claim `art_8ac93bcead73` sha256 `8ac93bcead7359264c2af601730dc289ab1204d3a4bfa7502bc5211836552915` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 67
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) patients receiving oral tyrosine kinase inhibitors · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage `cri_01M4V1FPHDRCKC2XYZKA0ER1ED` at version `5`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for oral_bioavailability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · aggregation max with on_missing unknown_no_penalty scores a candidate that has a dedicated acid-suppression study at its worst value while a candidate with no study is unpenalised, rewarding absent data.
  - round `run_01M4V43E8GDH8GF8M633VTWDQJ` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The material finding is accepted: taking the maximum reported effect while leaving an absent study unpenalised scored the best-characterised candidate at its worst value and the least-studied candidate at no value, which rewards absent data. Two changes follow. Aggregation is changed from max to median, so a single worst-case study no longer defines a candidate that has several. And the definition now states that an unknown here means untested rather than insensitive, requires the absence of a dedicated acid-suppression study to be recorded explicitly as untested alongside the score, and directs that a candidate known to be a weak base with pH-dependent solubility but never studied must be reported as an untested liability rather than as a clean one. The quoted formulation caveat is retained, since the magnitude of such an interaction depends on the salt and solid-state form of the product examined.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · 'Smaller change is better' with direction lower_better does not say whether the signed change or its magnitude is entered. The cited values are reductions, so a signed entry would rank a 53 percent loss (claim_01M4TYZ6EQ6GKNF22ZX6FQYDJT) as better than a 13 percent loss (claim_01M4TYZ6EDF3VDKSFTB1B58KKV). Unlike proposal 16, which states its sign convention, this definition leaves the predicate direction undetermined.; The definition insists 'silence is never scored as safety', but rule.on_missi
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The sign convention is now stated: the value is the unsigned magnitude of the percentage change, so a 53 percent loss can never rank better than a 13 percent loss, and the sign is recorded without being scored. The definition no longer promises a penalty the rule does not implement: an untested candidate returns unknown with no penalty and the weak-base pH-dependence liability is recorded as an annotation for a later stage, since no cited quote supports a number for it.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 3. Concentration of elimination in the predominant excretory route

- **attribute** `attr_concentration-of-elimination-in-the-predominant-excretory-ro@v1` · **rule** `rule_concentration-of-elimination-in-the-predominant-excretory-ro@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_concentration-of-elimination-in-the-predominant-excretory-ro@v1"]`, rule `["rule_concentration-of-elimination-in-the-predominant-excretory-ro@v1"]`; supersedes —
- **record hashes**: attribute `f09eab1f141aa0aa72013566d21abfc369c7a379048c354475d7ade698db255c`, rule `6569c81b67e9a98cfc2660a88c6fc284ec1a095e6e223708360ada48a4b8720d`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1RENP8NXHKN07H2HQNX50@v6"}` · dimension `metabolic_stability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Concentration of elimination in the predominant excretory route · subject `[{}]` · unit `% of dose recovered by the predominant route` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `78524f1708b221e52815ce26a9e0fbeca59d4e3ef4a6a1235ffb576532cf5883`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `559d10055d59e9ec9d8f92aca04e3362d5dc4bef1d7b2fc6353255d7bbb3cdc7`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The percentage of the administered dose recovered by the single predominant excretory route in a mass-balance study, with the recovery by the other route recorded alongside: a compound recovering 65 percent of the dose in faeces and 25 percent in urine scores 65, and one recovering 42 percent in faeces and 22 percent in urine scores 42. A high value means elimination is concentrated in one route and the compound's clearance therefore depends on one organ's function; a lower value means the routes share it. Lower is better. Only a stated recovery percentage is entered. A source stating only that elimination is mainly by one route, without a percentage for it, yields unknown with that statement and any percentage it does give for the minor route recorded, because the share carried by the predominant route cannot be inferred from the minor route's share when recovery is incomplete. A route-of-clearance fraction, such as a statement of what percentage of the drug undergoes renal clearance, is a different quantity and is recorded with its own description rather than entered, because recovery of the administered dose and apportionment of clearance are not interchangeable. The quantity is one number rather than a split, so the predicate has a monotone order; the full split remains in the record for a later stage to read.

- **unit** `% of dose recovered by the predominant route` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose elimination is shared between routes rank above candidates that funnel almost the whole dose through one, so a candidate whose single clearance route is removed by impairment of one organ is visibly disfavoured, and the recorded split explains the organ-impairment dose rules scored separately.
- **falsification test**: If mass-balance recoveries are unavailable for most candidates this attribute is inert and the organ-impairment dose-adjustment attributes carry the same information in a coarser form. If a candidate's predominant-route share is low only because its mass-balance recovery was incomplete, the value is an artefact of recovery and must be routed to a human rather than scored as redundancy.
- **rationale**: The cited quotes give elimination balances for agents of this class and show that concentration in one route creates a dependency on one organ: one agent recovers 65 percent of the dose in faeces and 25 percent in urine, another 42 percent in faeces and 22 percent in urine, and a third is reported as mainly excreted in faeces with less than 1 percent eliminated in urine, which states the minor route's share but not the predominant route's and therefore yields unknown on this axis with the statement recorded. Those splits are what make organ function a determinant of exposure for some agents of this class and not others, which is the consequence the organ-impairment attributes score directly. Scoring the share carried by the predominant route, rather than a two-number split or a window with no stated bounds, gives a single monotone axis that the evidence supports, and only percentages the sources state are entered, so the worked examples are exactly the two quotes that report both routes numerically. No cited quote states an acceptable renal or faecal percentage, so there is no cutoff and no range. A quote stating a renal function threshold for dosing, and one apportioning clearance rather than reporting recovery, are not cited here, because neither reports a mass-balance recovery.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `59542e7ddb9d152f849049f6b75a36bbdbccd190a3c5d8905d6143ec81a4b35e` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"mass balance\" OR excretion OR \"recovered in urine\" OR \"recovered in feces\" OR \"renal clearance\" OR \"biliary excretion\")", "relevance_terms": ["mass balance", "excretion", "urine", "feces", "renal clearance"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 3 cited claim(s), 3 carry `location.span_checked_against_source: true` and 3 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 3, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 3}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"inconclusive": 2, "supports": 1}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `inconclusive`*

- **claim_01M4TZRMNPXWPF5ZXG06WXM13D** · `inconclusive` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% eliminated in faeces", "unit_as_reported": "% eliminated in faeces", "value": 65, "value_high": null, "value_low": null}`
  > Approximately 65% and 25% of brigatinib’s systemic concentrations are eliminated via feces and urine, respectively
  - as recorded (paraphrase): For one agent approximately 65% of systemic drug is eliminated in faeces and 25% in urine.
  - in `src_doi_10.3389/or.2025.1612249` at `paragraph` `sec2.1.3.p1`, section 2 Results / 2.1 Lung cancer / 2.1.3 Brigatinib; document `art_25fa3c4c8de6` sha256 `25fa3c4c8de6f66f5a12b8a0bd0f4d3835f97671a144fda008226feb06d42e6d`; claim `art_c913717003b4` sha256 `c913717003b48c417adbf7de554b32123197eb7c41074e721bc045ab6b2d3262` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 951
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TZRMQ1242DD9D4QPQGBGT2** · `inconclusive` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% faecal excretion", "unit_as_reported": "% faecal excretion", "value": 42, "value_high": null, "value_low": null}`
  > Capmatinib undergoes biotransformation mainly through CYP3A4 and aldehyde oxidase, with excretion primarily in healthy subjects via feces (42%) and secondarily via urine (22%)
  - as recorded (paraphrase): One agent is biotransformed mainly by CYP3A4 and aldehyde oxidase with 42% faecal and 22% urinary excretion in healthy subjects.
  - in `src_doi_10.3389/or.2025.1612249` at `paragraph` `sec2.1.4.p1`, section 2 Results / 2.1 Lung cancer / 2.1.4 Capmatinib; document `art_25fa3c4c8de6` sha256 `25fa3c4c8de6f66f5a12b8a0bd0f4d3835f97671a144fda008226feb06d42e6d`; claim `art_1d4908f45bc1` sha256 `1d4908f45bc1726b623fe7be1cfe5c5151ae82f14a7ff715e81ce0d8e0e663cf` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 954
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

*polarity `supports`*

- **claim_01M4TY1REDXK0D6FTZ8BTSC3W1** · `supports` · evidence `reference_text` · determination `measured` · value `{"unit": "% eliminated in urine", "unit_as_reported": "% eliminated in urine", "value": 1, "value_high": null, "value_low": null}`
  > The drug is mainly excreted via feces, with less than 1% eliminated in urine.
  - as recorded (paraphrase): The agent is mainly excreted in faeces with less than 1% eliminated in urine.
  - in `src_nbk_NBK585049` at `paragraph` `article-143222.s3.p5`, section Mechanism of Action; document `art_d6f5f137dcb6` sha256 `d6f5f137dcb662288deb6e65d17790449f04dce1f0a228cee80848efe41da003`; claim `art_11a56582b4fb` sha256 `11a56582b4fb4de6babbdc46d553c2c0b16afbf324ee64923f09fc110f109d3b` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 354
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage `cri_01M4V1RENP8NXHKN07H2HQNX50` at version `6`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for metabolic_stability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Structured value 65 carries unit '% eliminated in FAECES', but the attribute's unit is '% of dose eliminated renally' (the renal figure in this quote is 25%). Same inversion in claim_01M4TZRMQ1242DD9D4QPQGBGT2 (42 is faecal; renal is 22%).; direction within_range with predicate_form ordering and cutoff null gives no defined sort, and the definition states the split is 'recorded as a balance rather than a preference for either route' while rule_kind is 'preference'. The rule contradicts its own d
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · direction is 'within_range' but rule.cutoff is null with cutoff_basis 'none_evidence_insufficient', so neither bound exists; a within_range direction needs both. predicate_form is also 'ordering', and a within-range quantity has no monotone order, so the predicate cannot enforce the direction it declares and the attribute cannot be scored as written.; The definition scores 'The split of the administered dose between renal and faecal or biliary elimination, as percentages', two numbers, while the
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The blocking defect is removed: the direction is now lower_better on a single monotone axis, the share of the dose recovered by the predominant excretory route, instead of within_range with no bounds under an ordering predicate. One number is entered rather than a two-number split, with the full split recorded, and route-of-clearance fractions are no longer pooled with mass-balance recoveries, so the quote reporting a renal clearance fraction is dropped from the support.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Two of the three worked examples are traceable, 65 percent in faeces from claim_01M4TZRMNPXWPF5ZXG06WXM13D and 42 percent from claim_01M4TZRMQ1242DD9D4QPQGBGT2, but the first, 'a compound recovering 93 percent of the dose in faeces scores 93', appears in no cited claim. claim_01M4TY1REDXK0D6FTZ8BTSC3W1 gives only 'mainly excreted via feces, with less than 1% eliminated in urine' and states no faecal percentage, so 93 is a number without a source.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The untraceable worked example is removed: the definition now illustrates the axis only with the two cited quotes that report both routes numerically, 65 with 25 percent and 42 with 22 percent, and the 93 percent figure that appeared in no cited quote is gone. A source stating only that elimination is mainly by one route, without a percentage for that route, now yields unknown with the statement recorded rather than being read as a high value, and the renal-threshold quote, which reports no recovery, is dropped from the support.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 4. Concentration-QTc upper bound at the highest modelled exposure

- **attribute** `attr_concentration-qtc-upper-bound-at-the-highest-modelled-exposu@v1` · **rule** `rule_concentration-qtc-upper-bound-at-the-highest-modelled-exposu@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_concentration-qtc-upper-bound-at-the-highest-modelled-exposu@v1"]`, rule `["rule_concentration-qtc-upper-bound-at-the-highest-modelled-exposu@v1"]`; supersedes —
- **record hashes**: attribute `d33504a0894830962f2bf5760f994028d8d9f460a6dbf3e361a5fb0788e2a2a4`, rule `044a1c441c59c789e0e717642760e1a5dc0bef678a5767641996e9967189765f`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V2225HYEE0AJ7A0NHSTMXN@v6"}` · dimension `toxicological_safety`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Concentration-QTc upper bound at the highest modelled exposure · subject `[{}]` · unit `msec change in QTc` · `quantitative` · aggregated by `max` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `cd8f5c57acfd66e052aba26d3e68e834d440db6810d5b43876800b1d2ea10a87`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `6504c974d50aee23ba63441d930de43733bd463d2b7539434e7380c0a7a48f1c`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The upper bound of the 90 percent confidence interval of the estimated mean QTc change, in milliseconds, at the highest exposure the source models, with that exposure recorded alongside: where a source reports bounds at the steady-state clinical peak concentration and at a multiple of it, the bound at the multiple is the admitted value and the clinical-exposure bound is recorded. The axis is defined at the highest modelled exposure, rather than at the clinical exposure alone, for two reasons: it is the conservative figure, since a candidate's exposure can rise with an interacting co-medication, and it is the figure these sources report as the headline estimate, so the admitted value is the one the source itself carries and no reader has to reconstruct a different one. A value estimated from a concentration-QTc model is recorded as model-derived. A candidate for which the evidence offers only event counts, a symptom list or a monitoring instruction returns unknown rather than a value, and reported rates of cardiac failure, left ventricular dysfunction and ischaemic events are percentages, a different quantity that is recorded rather than entered and is scored, where quantified, by the severe-adverse-event attribute. Where candidates' bounds come from different exposure multiples the multiple is recorded with each value, and because a bound estimated at a higher multiple is the more conservative figure, an ordering that prefers the candidate whose bound was estimated at the higher multiple errs on the side of caution rather than against the candidate. Smaller QT effect is better.

- **unit** `msec change in QTc` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `max`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates with a documented negligible modelled QT effect rank above candidates with a larger estimated effect, the admitted number is the one the source reports with its exposure recorded, and candidates with only event or monitoring content return unknown rather than a fabricated value.
- **falsification test**: A negligible QT effect measured at the approved dose does not exclude an effect at higher exposure or with an interacting co-medication; if the only data are at a single dose level the attribute must be read together with the interaction attributes.
- **rationale**: One cited quote gives this quantity directly: a concentration-QTc model estimated the upper bounds of the 90 percent confidence interval of the mean QTc change as 0.0537 milliseconds at the steady-state peak concentration and 4.00 milliseconds at twice that concentration, and 4.00 is the figure the claim itself carries as its value with the unit in milliseconds. Defining the axis at the highest modelled exposure therefore makes the admitted number the one the source and the claim both report, instead of a figure that has to be read back out of the quote, and it is also the conservative choice for a compound whose exposure can be raised by an interacting co-medication. The quote also makes plain that the figure is model-derived, which the definition records rather than conceals. No cited quote states an acceptable QT effect, so the rule is an ordering with no cutoff, and a negligible modelled effect does not exclude an effect at exposures beyond those modelled, which is why the recorded exposure multiple and the interaction attributes must be read with it.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `ffef55c588b4394d4c0c8f0a227dfdc5341f15fefc8e7b9c8c7386409fabceb2` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"QT\" OR QTc OR \"cardiac failure\" OR \"left ventricular\" OR cardiomyopathy OR \"ejection fraction\") AND (msec OR milliseconds OR incidence OR \"concentration-QTc\" OR grade)", "relevance_terms": ["QTc", "cardiac failure", "left ventricular", "ejection fraction"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 1 cited claim(s), 1 carry `location.span_checked_against_source: true` and 1 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 1, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 1}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"supports": 1}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `supports`*

- **claim_01M4V0JWPT4EGBYNDFA652RSEJ** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "msec upper bound of mean QTc change", "unit_as_reported": "msec upper bound of mean QTc change", "value": 4.0, "value_high": null, "value_low": null}`
  > The final C‐QTc model, which was selected based on the model performance, estimated that the upper bounds of the 90% confidence interval (CI) of the mean ΔΔQTcP at steady‐state GM M11 C max, and twice the GM M11 C max, were 0.0537 and 4.00 msec, respectively. Predictions generated using a C‐QTc model that included only fruquintinib were similar, with the estimated upper bounds of the 90% CI of the predicted mean ΔΔQTcP at twice the GM steady‐state fruquintinib C max (580 ng/mL) being 3.96 msec. These data indicated that fruquintinib administered at the approved clinical dose is not anticipated to cause clinically meaningful QT prolongation
  - as recorded (paraphrase): Concentration-QTc modelling in 205 patients estimated upper 90% confidence bounds of the mean QTc change of about 4 msec at twice the geometric mean steady-state peak concentration, indicating no clinically meaningful QT prolongation at the approved dose.
  - in `src_doi_10.1111/cts.70713` at `paragraph` `sec4.p5`, section Pharmacokinetic Characteristics; document `art_c39cbfdcc31e` sha256 `c39cbfdcc31ef3ea6814fce214c161303b6e692683ea6d22ad085239bd8d08b3`; claim `art_4e4ed9b61ca0` sha256 `4e4ed9b61ca0eb39aa0ed624730526f7a2d266da63f6c45139313e23b796ee87` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1224
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review item `q_01M4VEGX9EGD8RJ4YHR0DPX1TK` (`open`, blocking `True`, raised 2026-10-13T20:16:06.446Z): proposer and critic still disagree after one revision
  - inspection bundle: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "open_critic_findings": [{"check": "unit_applicability_consistency", "finding": "The admitted value is whatever exposure a given source happens to model highest, so a bound computed at twice the clinical peak and a bound computed at the clinical peak alone can sit on one millisecond axis. The definition records the multiple and argues the error direction is safe, but the values are not estimates at a common exposure, and with aggregation max the candidate whose source modelled a higher multiple is ordered on a different quantity.", "proposal_index": 24, "referent": "attribute.definition", "severity": "material", "verdict": "fail"}], "pool_criterion": "cri_01M4V2225HYEE0AJ7A0NHSTMXN"}`
- unresolved proposer/critic disputes: `q_01M4VEGX9EGD8RJ4YHR0DPX1TK`
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `unit_applicability_consistency` on attribute.definition · severity `material` · verdict `fail`: The admitted value is whatever exposure a given source happens to model highest, so a bound computed at twice the clinical peak and a bound computed at the clinical peak alone can sit on one millisecond axis. The definition records the multiple and argues the error direction is safe, but the values are not estimates at a common exposure, and with aggregation max the candidate whose source modelled a higher multiple is ordered on a different quantity.

**Lineage and lifecycle**

- pool lineage `cri_01M4V2225HYEE0AJ7A0NHSTMXN` at version `6`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for toxicological_safety
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The definition bundles a QTc change in milliseconds with 'reported rates of cardiac failure, left ventricular dysfunction and ischaemic events' as percentages, under the single unit 'msec change in QTc'. An event rate entering this scale is not commensurable with a millisecond value.; Structured value 4.0 is the upper bound at TWICE the geometric-mean Cmax; the figure at the clinical exposure, which the definition specifies, is 0.0537 msec. With agg max the supratherapeutic value governs, contra
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The unit is 'msec change in QTc', but the definition also scores 'reported rates of cardiac failure, left ventricular dysfunction and ischaemic events', which are percentages. With aggregation max over a single axis, a rate and a millisecond value cannot both be entered, and every cited claim except claim_01M4V0JWPT4EGBYNDFA652RSEJ offers only event or monitoring content, so the value is undefined for candidates with event data alone.; The definition asks for the upper bound 'at the clinical exp
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The blocking unit conflict is resolved: the axis carries milliseconds only, and cardiac event rates are recorded rather than entered, with a candidate that has only event or monitoring content returning unknown. The definition now fixes which exposure is admitted, the bound at the steady-state clinical peak rather than the bound at twice that concentration, so the cited quote is read at the right exposure, and the value is recorded as model-derived. The four quotes that are symptom lists or monitoring notes are dropped from the support.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The claim's own value field records 4.0 with unit 'msec upper bound of mean QTc change', which is the figure at twice the clinical exposure, not the 0.0537 the definition admits. A pipeline reading claim values rather than quote text would still enter the wrong number, so the correction lives only in the prose.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The axis is redefined at the highest exposure the source models, which is the figure the cited claim carries as its value, so the admitted number no longer depends on a prose correction that a pipeline reading claim values would miss. The exposure at which each bound was estimated is recorded, and the definition notes that this choice is the conservative one because exposure can rise with an interacting co-medication.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `disputed` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 5. CSF1R affinity on the independent expert curation

- **attribute** `attr_csf1r-affinity-on-the-independent-expert-curation@v1` · **rule** `rule_csf1r-affinity-on-the-independent-expert-curation@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_csf1r-affinity-on-the-independent-expert-curation@v1"]`, rule `["rule_csf1r-affinity-on-the-independent-expert-curation@v1"]`; supersedes —
- **record hashes**: attribute `5e6977e6f0676f8316cd742568079da649ae15e5fae4e5930a8a3874571ebbdb`, rule `9573d69e02159ab8c128508ccfed735a985a41f5ab6b46aa10a6dc22436da7a2`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V183B9DMFBV9A0WVHM5XFY@v6"}` · dimension `target_coverage`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: CSF1R affinity on the independent expert curation · subject `[{"target_chembl_id": "CHEMBL1844"}]` · unit `pChEMBL` · `quantitative` · aggregated by `median` · transform —
  - read from `["interaction_evidence_lookup"]` asking `["gtopdb_affinity"]`; evidence kinds `["curated_measurement"]`; determination bases —
  - measurement identity `09239afcec8ceea87f739657198c84bd736737638e88ff666c43317be210defc`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `unknown_no_penalty` · decision identity `1b3fc79520d305321c8ec8db210f44a8dc3cb559f6204c08baef538e9586e1ca`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The median expert-curated affinity of the compound at the colony-stimulating-factor-1 receptor, on the pChEMBL scale, that is the negative base-ten logarithm of the molar half-maximal inhibitory concentration, inhibition constant or dissociation constant as the curation reports it. Higher is better. The source bound here is an expert curation independent of the activity table that the registry's potency criterion for this receptor reads, and it can cover compound-target pairs that table lacks, which is the gap this attribute is for: a candidate whose engagement of this receptor is absent from one curation may be quantified in the other. It is therefore not a restatement of the registry criterion and does not replace it. The two read different sources, the median is taken over the records this source returns rather than a maximum, because a maximum rises with the number of records, and the action type and any selectivity comment travel with each record for a narrative to cite. Where the two curations disagree materially about the same compound the conflict is routed to a human rather than averaged. Absence of a record gives unknown and never a failure, because this curation is sparse outside developed and late-stage drugs.

- **unit** `pChEMBL` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `median`
- **accepted evidence kinds** `["curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose affinity at this receptor is quantified by a curation independent of the activity table are ranked on that measurement, which recovers coverage evidence for candidates the activity table does not cover, while candidates with no record in either curation are not penalised.
- **falsification test**: Compare this curation's values with the registry potency criterion for the same receptor across the pool. If the two agree everywhere and cover the same candidates, this attribute adds nothing and should be merged into that criterion; if they disagree materially for a candidate, the conflict is routed to a human rather than averaged. If the curation returns no record for any candidate the attribute yields only unknowns.
- **rationale**: The objective requires that one molecule engage this microenvironmental receptor, and the cited quotes establish that it is a clinically drugged target with an approved oral inhibitor, that it belongs to the receptor protein-tyrosine kinase families alongside the other required receptors, that single agents documented to cover it together with the vascular receptors exist, that co-inhibiting it with the vascular receptors is rationalised as relieving receptor-driven immune suppression, and that a compound should be regarded as a pathway modulator rather than a confirmed inhibitor where direct biochemical inhibition was never reported. The mechanism-of-action record source this attribute previously read stamps every claim it returns with determination basis curated, a basis excluded by the bases an attribute here accepts, so every record it returned would be set aside at assessment time and the attribute would carry no evidence at all; that is the finding this revision answers. The attribute is therefore bound instead to the independent expert curation of affinity at this receptor, which returns measured values on the pChEMBL scale and, being independent of the activity table, reaches compound-target pairs that table lacks, the same gap the record-based form was meant to close, while stating how strongly rather than only that engagement is documented. No cited quote states a required affinity at this receptor, so the rule is an ordering with no cutoff, and an absent record is unknown rather than a failure.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `unknown_no_penalty`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `619dfa6620134da00266feb8886b982be61eac401b1ded1e4a4ce86bc88ca23d` · 1 route(s) · literature-bound `False`
  - route `interaction_evidence_lookup` / `gtopdb_affinity` · subject `{"target_chembl_id": "CHEMBL1844"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 5 cited claim(s), 5 carry `location.span_checked_against_source: true` and 5 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 5 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 5}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"supports": 5}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `supports`*

- **claim_01M4TX99MCZ572N3DGP2J10J8R** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Pexidartinib | CSF1R | Tenosynovial giant cell tumors
  - as recorded (paraphrase): An approved oral tyrosine kinase inhibitor targeting CSF1R exists, indicated for tenosynovial giant cell tumours.
  - in `src_nbk_NBK563322` at `table` `article-109800.table1`, section Tables; document `art_f39aa2170bbb` sha256 `f39aa2170bbb6e797aa143c217673d26d91bf5238802cedbd23bc4621ce110fc`; claim `art_b6a05399858a` sha256 `b6a05399858ae08c55bcab3e6347af6bd66f34e7d056c88ae2a04376838a2415` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 103
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXQQ2QWTWJM3HWNWMHJ27Z** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Multi-target FGFR1/2/3 inhibition (with additional CSF1R/VEGFR activity) combined with PD-L1 blockade to couple direct FGFR-addicted tumour killing with relief of FGFR-driven immune suppression
  - as recorded (paraphrase): Multi-target FGFR1/2/3 inhibition with additional CSF1R and VEGFR activity is rationalised as coupling direct tumour killing with relief of FGFR-driven immune suppression.
  - in `src_doi_10.2147/dddt.s559328` at `table` `table4`, section Tables; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_ac0a931075fb` sha256 `ac0a931075fbc23d3bfcb94870b219dbfff7463088f9ff6a14588b990cf7167c` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 201
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYG03CFH1TYT47BR0G5S93** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > In biochemical and cellular studies, sunitinib, an RTKI, potently inhibits VEGFR1/2, FLT3, KIT, PDGFRα/β, RET and CSF1R
  - as recorded (paraphrase): In biochemical and cellular studies an approved oral agent potently inhibits VEGFR1, VEGFR2, FLT3, KIT, PDGFR alpha and beta, RET and CSF1R.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec3.1.1.4.p1`, section Review / Receptor Tyrosine Kinase Inhibitors / Moderate Clinical Evidence / Sunitinib; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_0276dab99bc0` sha256 `0276dab99bc0a3eb37f9f1cc4818266438fa80e1a684bfeb6c5cbaba72baf928` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 497
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYG0AE0MKPGQKYXXBKHWXJ** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > The receptor protein‐tyrosine kinases are subdivided into the following: anaplastic lymphoma kinase (ALK), colony‐stimulating factor 1 receptor (CSF1R), cholecystokinin receptor (CCKR), discoidin domain‐containing receptor (DDR), epidermal growth factor receptor (EGFR), erythropoietin‐producing hepatocellular carcinoma receptor (EPHR), fibroblast growth factor receptor (FGFR), Feline McDonough Sarcoma (c‐FMS)‐like tyrosine kinase 3 (FLT3), KIT protein (KIT), mesenchymal‐epithelial transition factor (MET), platelet‐derived growth factor (PDGFR), vascular endothelial growth factor receptor (VEGFR)
  - as recorded (paraphrase): The receptor protein-tyrosine kinase families include colony-stimulating factor 1 receptor, fibroblast growth factor receptor and vascular endothelial growth factor receptor among others.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec1.p2`, section Introduction; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_ca1b1e355d8c` sha256 `ca1b1e355d8c1b50d2366d5cec4a86fef8f6bfb83081e43b4ef30267637f3c19` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 508
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYRS56BYQ5JA6Q413SSDTS** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > However, direct biochemical inhibition of c-Met was not reported, so the compound should be regarded as a c-Met-pathway modulator rather than a confirmed c-Met kinase inhibitor.
  - as recorded (paraphrase): Without reported direct biochemical inhibition a compound should be regarded as a pathway modulator rather than a confirmed kinase inhibitor.
  - in `src_doi_10.3390/ijms27188007` at `paragraph` `sec3.p8`, section 3. Natural Products as Lead Scaffolds for c-Met Inhibitor Discovery; document `art_480b68481ece` sha256 `480b68481ecefe2a1fdafb89f03b786362ce39c7543050d4150c5567f2a10d23`; claim `art_c34a7f656824` sha256 `c34a7f656824754547db567cdb83ef2ceb1a1d754f64e7c79ca73a4f8bcccad3` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 621
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review item `q_01M4VEGR3F1V6ADPRMW0P2HD4G` (`open`, blocking `True`, raised 2026-10-13T20:16:01.135Z): proposer and critic still disagree after one revision
  - inspection bundle: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "open_critic_findings": [{"check": "evidence_support", "finding": "No cited claim contains a pChEMBL value or any numeric affinity at this receptor. claim_01M4TX99MCZ572N3DGP2J10J8R is a table row, 'Pexidartinib | CSF1R | Tenosynovial giant cell tumors'; claim_01M4TYG0AE0MKPGQKYXXBKHWXJ is a list of receptor kinase family names; claim_01M4TYG03CFH1TYT47BR0G5S93 says sunitinib 'potently inhibits VEGFR1/2, FLT3, KIT, PDGFR alpha/beta, RET and CSF1R' with no number. The claims establish that the receptor is drugged, not that the bound curation returns a value.", "proposal_index": 0, "referent": "supporting_claim_ids", "severity": "material", "verdict": "fail"}, {"check": "unit_applicability_consistency", "finding": "The definition states 'Where the two curations disagree materially about the same compound the conflict is routed to a human rather than averaged', but rule.on_conflict is 'unknown_no_penalty', which drops the candidate to unknown instead of routing it. The rule contradicts the definition, and the same mismatch is present in proposals 1 to 4.", "proposal_index": 0, "referent": "rule.on_conflict", "severity": "material", "verdict": "fail"}, {"check": "objective_conformance", "finding": "Five separate per-receptor affinity attributes each return unknown_no_penalty when the curation has no record, so a candidate that does not engage a required receptor is indistinguishable from one not yet curated at it, and none of the five enforces the objective's 'concurrently engages' requirement. The definition concedes the curation 'is sparse outside developed and late-stage drugs', which makes the unknown the common case.", "proposal_index": 0, "referent": "rule.on_missing", "severity": "material", "verdict": "fail"}], "pool_criterion": "cri_01M4V183B9DMFBV9A0WVHM5XFY"}`
- unresolved proposer/critic disputes: `q_01M4VEGR3F1V6ADPRMW0P2HD4G`
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (3):
  - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: No cited claim contains a pChEMBL value or any numeric affinity at this receptor. claim_01M4TX99MCZ572N3DGP2J10J8R is a table row, 'Pexidartinib | CSF1R | Tenosynovial giant cell tumors'; claim_01M4TYG0AE0MKPGQKYXXBKHWXJ is a list of receptor kinase family names; claim_01M4TYG03CFH1TYT47BR0G5S93 says sunitinib 'potently inhibits VEGFR1/2, FLT3, KIT, PDGFR alpha/beta, RET and CSF1R' with no number. The claims establish that the receptor is drugged, not that the bound curation returns a value.
  - `unit_applicability_consistency` on rule.on_conflict · severity `material` · verdict `fail`: The definition states 'Where the two curations disagree materially about the same compound the conflict is routed to a human rather than averaged', but rule.on_conflict is 'unknown_no_penalty', which drops the candidate to unknown instead of routing it. The rule contradicts the definition, and the same mismatch is present in proposals 1 to 4.
  - `objective_conformance` on rule.on_missing · severity `material` · verdict `fail`: Five separate per-receptor affinity attributes each return unknown_no_penalty when the curation has no record, so a candidate that does not engage a required receptor is indistinguishable from one not yet curated at it, and none of the five enforces the objective's 'concurrently engages' requirement. The definition concedes the curation 'is sparse outside developed and late-stage drugs', which makes the unknown the common case.

**Lineage and lifecycle**

- pool lineage `cri_01M4V183B9DMFBV9A0WVHM5XFY` at version `6`, state `promoted`
- parents — · children —
- merged away: `{"collapse_id": "clp_01M4WXKPA3MBD055HSNCBV43AA", "into": "attr_csf1r-curated-potency@v2", "reason_text": "2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL1844. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_csf1r-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.", "withdrawn": false}`
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for target_coverage
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · arbitrary_cutoff: source_stated_value cutoff without a cited claim carrying a value
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The validator was right: a cutoff of 'equals true' carries no value taken from any cited quote, so declaring cutoff_basis source_stated_value invented a standard the claims do not state. The rule is therefore rebuilt as a preference with predicate_form ordering, cutoff null and cutoff_basis none_evidence_insufficient, and the direction is set to higher_better so documented engagement ranks above undocumented engagement without any threshold being asserted. Two further corrections follow from the evidence catalog's own instruction for this entry: acceptable_determination_bases is now declared as ['curated'], without which every record-derived claim would be set aside and the attribute would see no evidence at all, and the definition now states in terms that a record is an expert assertion rather than a measurement and must never stand in for a potency value. The cited claims are unchanged, since each of them bears on whether documented engagement of this receptor is the right thing to look for.
  - round `run_01M4V52W85KZMCC0X2A7BN1YR3` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · evidence_support: the bound source returns curated records and acceptable_determination_bases ['measured', 'derived'] excludes that basis, so every value it returns would be set aside and the attribute would carry no evidence
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `needs_refine` · `refined_still_failing` · evidence_support: the bound source returns curated records and acceptable_determination_bases ['measured', 'derived'] excludes that basis, so every value it returns would be set aside and the attribute would carry no evidence
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The bound mechanism-of-action record source returns claims stamped determination basis curated, which the accepted bases exclude, so every record would have been set aside and the criterion would have measured nothing; declaring the basis on the attribute did not survive the previous revision, so the finding is resolved the other way, by binding the attribute to the independent expert affinity curation for the same receptor, whose records are measured values on the pChEMBL scale. The definition states that this curation is independent of the activity table the registry's potency criterion reads, which is the coverage gap the record-based form was meant to close, that it does not replace that criterion, and that a material disagreement between the two is routed to a human.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `disputed` · —

**Use**

- status `collapsed_away` on `rules@v3` — its attribute was merged into attr_csf1r-curated-potency@v2 by clp_01M4WXKPA3MBD055HSNCBV43AA; rule_csf1r-curated-potency@v2 scores the quantity
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 6. CSF1R curated potency

- **attribute** `attr_csf1r-curated-potency@v2` · **rule** `rule_csf1r-curated-potency@v2` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_csf1r-curated-potency@v1", "attr_csf1r-curated-potency@v2"]`, rule `["rule_csf1r-curated-potency@v1", "rule_csf1r-curated-potency@v2"]`; supersedes `attr_csf1r-curated-potency@v1`
- **record hashes**: attribute `4b70612b03ff505467d9b278bf6456352830ff33e83bacfb03290b549c9db8af`, rule `65d1055ba916f11b5babf7801b49375e2515ed9cfa004517a6c6b18bd3162c65`
- **origin**: `task_mandated_template` · proposed by `{"id": "objective-criteria", "kind": "system", "role": "adapter_template"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"field": "scope_entities[0]", "task_context": "task_01M4TWZXZEB1SQPS7H47C8BX01@v1"}` · dimension —
- **written by software**: `{"collapsed_by": "clp_01M4WXKPA3MBD055HSNCBV43AA", "rule_collapsed_by": "clp_01M4WXKPA3MBD055HSNCBV43AA"}`

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: CSF1R curated potency · subject `[{"target_chembl_id": "CHEMBL1844"}]` · unit `pChEMBL` · `quantitative` · aggregated by `median` · transform —
  - read from `["interaction_evidence_lookup"]` asking `["gtopdb_affinity", "pchembl_values"]`; evidence kinds `["curated_measurement"]`; determination bases —
  - measurement identity `408ac135ffbc9afafbae86b3d9be0932228ce31dd8530ee08c9eaf00f949e129`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_blocks_recommendation` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `unknown_blocks_recommendation` · decision identity `ccd2a4bc32097a7f60ee901cccfbdf7c410ee1074eae1097004718d596b03326`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> Median pChEMBL value over curated point measurements against CSF1R (CHEMBL1844)

- **unit** `pChEMBL` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `median`
- **accepted evidence kinds** `["curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_blocks_recommendation", "stated_in_definition_only": true}`
- **expected change**: —
- **falsification test**: —
- **rationale**: CSF1R is a required target of the task

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_blocks_recommendation` · **on conflict** `unknown_blocks_recommendation`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `c1d7e7adad5246706ab0f95e7ff5e2a14ff5f292466b2f5bb65127502835f956` · 2 route(s) · literature-bound `False`
  - route `interaction_evidence_lookup` / `pchembl_values` · subject `{"target_chembl_id": "CHEMBL1844"}` · retrieval — · identifier scheme `inchikey`
  - route `interaction_evidence_lookup` / `gtopdb_affinity` · subject `{"target_chembl_id": "CHEMBL1844"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 0 cited claim(s), 0 carry `location.span_checked_against_source: true` and 0 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` — (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: —
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage — at version —, state —
- parents — · children —
- merged away: —
- survived a collapse: `{"absorbed": ["attr_csf1r-affinity-on-the-independent-expert-curation@v1"], "collapse_id": "clp_01M4WXKPA3MBD055HSNCBV43AA", "reason_text": "2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL1844. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_csf1r-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.", "routes_after": ["pchembl_values", "gtopdb_affinity"], "routes_before": ["pchembl_values"], "withdrawn": false}`
- refinement history: — (this criterion never entered the pool)

**Use**

- status `scoring` on `rules@v3`
- rule-set entry: `{"acceptable_value_sources": ["curated_measurement"], "attribute_ref": "attr_csf1r-curated-potency@v2", "authority": "trigger_table", "confirmed_by": "auto:trigger_table", "cutoff_basis": "none_evidence_insufficient", "disputed": false, "on_states": ["unknown_no_penalty", "unknown_blocks_recommendation", "unknown_blocks_recommendation"], "rule_kind": "preference", "rule_ref": "rule_csf1r-curated-potency@v2"}`
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `True`
- measured coverage: `{"assessed": 3177, "board": "lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4", "observed": 37}`

---

### 7. Distance of computed lipophilicity outside the stated band

- **attribute** `attr_distance-of-computed-lipophilicity-outside-the-stated-band@v2` · **rule** `rule_distance-of-computed-lipophilicity-outside-the-stated-band@v2` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_distance-of-computed-lipophilicity-outside-the-stated-band@v1", "attr_distance-of-computed-lipophilicity-outside-the-stated-band@v2"]`, rule `["rule_distance-of-computed-lipophilicity-outside-the-stated-band@v1", "rule_distance-of-computed-lipophilicity-outside-the-stated-band@v2"]`; supersedes `attr_distance-of-computed-lipophilicity-outside-the-stated-band@v1`
- **record hashes**: attribute `bcb06a394f6a8c8758fa132b235e523b73f8edacc622ed20cbe834e29b86c18e`, rule `adc1e94c80721531a77ca2aa19c5d7abbf1d511246c6f48294839d5fdf657dfd`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1FPCHCHCPQF09A5DR9BYN@v3"}` · dimension `oral_bioavailability`
- **written by software**: `{"adjudicated_by": "adj_01M4WY7SQ2RASTG0CF7VV562NA", "rule_adjudicated_by": "adj_01M4WY7SQ2RASTG0CF7VV562NA"}`

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Distance of computed lipophilicity outside the stated band · subject `[{"property": "XLogP"}]` · unit `log units` · `quantitative` · aggregated by `median` · transform `{"basis": "source_stated_value", "high": 4, "kind": "distance_outside_band", "low": 2, "source_refs": ["claim_01M4TXF4NN19J6JG3M3Y6T17V1"]}`
  - read from `["property_estimate"]` asking `["computed_property"]`; evidence kinds `["database_entry"]`; determination bases —
  - measurement identity `fe1f4592005e5fa96254eb6e3be6a99f54662f1caaca23c1cc8c39ff85471337`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `unknown_no_penalty` · decision identity `7221a2a424c4f0c96934b8e6c3ec006398ead52259f3ce9ac765ddf6817e326f`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The computed octanol-water partition coefficient of the neutral species, expressed as its distance in log units outside the band of approximately 2 to 4 that the cited source states as optimal for this inhibitor class: zero inside the band, the shortfall below 2 for a more polar molecule, and the excess above 4 for a more lipophilic one. Lower is better by construction. The quantity is explicitly a proxy: the same cited source states that logD, which incorporates ionisation at physiological pH, reflects in vivo behaviour more accurately, and logD is not obtainable from the evidence catalog, so ionisable candidates will be scored less faithfully than neutral ones and this attribute must never outweigh a measured absorption endpoint.

- **unit** `log units` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["database_entry"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates inside the stated lipophilicity band score zero and are not separated on this attribute, while both excessively lipophilic and excessively polar candidates are demoted in proportion to their distance outside it.
- **falsification test**: If the ranking by this computed proxy inverts the ranking by measured oral bioavailability, the neutral-species descriptor is the wrong quantity for these molecules, as the cited source itself implies, and the attribute must be withdrawn in favour of the measured value.
- **rationale**: The cited quote states that moderate lipophilicity, typically a logP of about 2 to 4, is considered optimal for this class because it permits passive membrane diffusion without excessively compromising aqueous solubility. The two failure modes are quoted separately and are now both encoded by the two-sided quantity: compounds of excessively high lipophilicity show poor aqueous solubility, increased metabolic clearance and higher affinity for efflux transporters, while highly polar low-logP molecules show limited membrane permeability. Two further cited quotes show the same parameter driving transporter behaviour, with efflux activity particularly sensitive to lipophilicity and halogen substitution raising lipophilicity at the cost of greater efflux susceptibility, which is why the band and not a direction is the right form. The deprecation of the neutral-species descriptor in favour of logD is recorded above as a declared limitation rather than left implicit.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `unknown_no_penalty`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: `{"basis": "source_stated_value", "high": 4, "kind": "distance_outside_band", "low": 2, "source_refs": ["claim_01M4TXF4NN19J6JG3M3Y6T17V1"]}`
- **evidence key** `dcb7ebc0dfacef0005504d778afd0d76748ba84c51cb7951b2ce3d1bfcc074a7` · 1 route(s) · literature-bound `False`
  - route `property_estimate` / `computed_property` · subject `{"property": "XLogP"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- `attribute.value_transform.low` = `2` — unit `log units` · basis `source_stated_value` · claims `["claim_01M4TXF4NN19J6JG3M3Y6T17V1"]` · support field: attribute.value_transform.source_refs
- `attribute.value_transform.high` = `4` — unit `log units` · basis `source_stated_value` · claims `["claim_01M4TXF4NN19J6JG3M3Y6T17V1"]` · support field: attribute.value_transform.source_refs

**Verification, reported as three separate checks**

- quote check — of 6 cited claim(s), 6 carry `location.span_checked_against_source: true` and 6 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 1, `value_not_in_quote` 0, not recorded 5 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 6}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 2, "inconclusive": 1, "supports": 3}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TXF4PGYBH8PGC6E4PX2YGE** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Indeed, compounds displaying excessively high lipophilicity often exhibit poor aqueous solubility, increased metabolic clearance, and higher affinity for efflux transporters
  - as recorded (paraphrase): Compounds with excessively high lipophilicity often show poor aqueous solubility, increased metabolic clearance and higher affinity for efflux transporters.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.2.p3`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.2. Critical Physicochemical Properties for Oral Bioavailability of KIs and Central Nervous System Penetration; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_b27b5ec303cf` sha256 `b27b5ec303cf6b154c861b0908a36694c5be8cb503932c48a5de8acfc276d7ef` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 131
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXF51FCCKMFXB693PTF19T** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > For instance, the introduction of halogen atoms (e.g., Cl, F) typically increases lipophilicity and enhances hydrophobic interactions within the kinase binding pocket, although this may simultaneously increase susceptibility to P-gp-mediated efflux
  - as recorded (paraphrase): Introducing halogen atoms typically increases lipophilicity and hydrophobic binding-pocket interactions but may simultaneously increase susceptibility to P-gp-mediated efflux.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.4.p5`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.4. Influence of Molecular Structure on Efflux Transporter Interaction (P-gp, BCRP); document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_955cd8d62f83` sha256 `955cd8d62f8364413d49ac17fcf4052103b041e6e34ce8c20360c90a58ca565e` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 149
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

*polarity `inconclusive`*

- **claim_01M4TXF4QYFGNTQ6ZAFT5A947E** · `inconclusive` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > while logP describes the partition coefficient of the neutral species between octanol and water, logD more accurately reflects in vivo behavior by incorporating ionization at physiological pH
  - as recorded (paraphrase): logP describes the octanol-water partition coefficient of the neutral species, whereas logD better reflects in vivo behaviour because it incorporates ionisation at physiological pH.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.2.p3`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.2. Critical Physicochemical Properties for Oral Bioavailability of KIs and Central Nervous System Penetration; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_40f784adfece` sha256 `40f784adfece0e91770229c2e8f13d8473e40e6104cd3f58109d16ca26f482c6` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 133
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

*polarity `supports`*

- **claim_01M4TXF4NN19J6JG3M3Y6T17V1** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": "logP", "unit_as_reported": "logP", "value": null, "value_high": 4, "value_low": 2}`
  > In general, moderate lipophilicity (typically logP ≈ 2–4) is considered optimal for kinase inhibitors, as it facilitates passive membrane diffusion without excessively compromising aqueous solubility
  - as recorded (paraphrase): Moderate lipophilicity, typically a logP of about 2 to 4, is considered optimal for kinase inhibitors because it permits passive membrane diffusion without excessively compromising aqueous solubility.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.2.p3`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.2. Critical Physicochemical Properties for Oral Bioavailability of KIs and Central Nervous System Penetration; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_83432e6710cf` sha256 `83432e6710cf42858daa0dfa510ec2e15dd68b27705b84896b00828c1265f398` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 130
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) kinase inhibitors · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXF4Q30DYF9581W0RNTTG1** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Conversely, highly polar molecules (low logP) tend to display limited membrane permeability.
  - as recorded (paraphrase): Highly polar, low-logP molecules tend to show limited membrane permeability.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.2.p3`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.2. Critical Physicochemical Properties for Oral Bioavailability of KIs and Central Nervous System Penetration; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_2842d67cd0bc` sha256 `2842d67cd0bcc89c43b73f7d1ffd585353300afad9ae2a213cea7ddab4e71f69` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 132
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXF54AB5M65KFKHTW5S7C2** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Similarly, studies on propafenone analogues have highlighted that nitrogen basicity, substituent flexibility, and lipophilicity (logP) are key determinants of transporter selectivity, with P-gp activity being particularly sensitive to changes in lipophilicity compared with BCRP
  - as recorded (paraphrase): Nitrogen basicity, substituent flexibility and lipophilicity are key determinants of transporter selectivity, with P-gp activity particularly sensitive to lipophilicity changes compared with BCRP.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.4.p6`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.4. Influence of Molecular Structure on Efflux Transporter Interaction (P-gp, BCRP); document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_62f446c01539` sha256 `62f446c015397c26c25b7a204159ff4c9301ebed2150fd1174addec2906611a0` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 154
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) propafenone analogues · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudication `adj_01M4WY7SQ2RASTG0CF7VV562NA` · route `definition_restated` · resolution `declare_value_transform` · approval kind `agent_verdict` · confirmed by a person `False`
  - reason: the attribute's definition states the distance outside the band 2 to 4 and the attribute declared no transformation, so every cell carried the raw value its source returns; the transformation is declared as the definition already describes it, on a bound claims claim_01M4TXF4NN19J6JG3M3Y6T17V1 state, and the definition itself is unchanged
  - cites: `{"bound_traces": {"high": [{"claim_id": "claim_01M4TXF4NN19J6JG3M3Y6T17V1", "states_it": "claim_quote"}], "low": [{"claim_id": "claim_01M4TXF4NN19J6JG3M3Y6T17V1", "states_it": "claim_quote"}]}, "claim_ids": ["claim_01M4TXF4NN19J6JG3M3Y6T17V1"], "definition_text": "The computed octanol-water partition coefficient of the neutral species, expressed as its distance in log units outside the band of approximately 2 to 4 that the cited source states as optimal for this inhibitor class: zero inside the band, the shortfall below 2 for a more polar molecule, and the excess above 4 for a more lipophilic one. Lower is better by construction. The quantity is explicitly a proxy: the same cited source states that logD, which incorporates ionisation at physiological pH, reflects in vivo behaviour more accurately, and logD is not obtainable from the evidence catalog, so ionisable candidates will be scored less faithfully than neutral ones and this attribute must never outweigh a measured absorption endpoint.", "field": "definition", "match": "definition_states_a_derived_quantity", "quantity_text": "the distance outside the band 2 to 4", "value_transform": {"basis": "source_stated_value", "high": 4, "kind": "distance_outside_band", "low": 2, "source_refs": ["claim_01M4TXF4NN19J6JG3M3Y6T17V1"]}}` · claims — · independence —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (2):
  - `unit_applicability_consistency` on attribute.evidence_request.parameters.property · severity `minor` · verdict `fail`: The band's numeric bounds come from a quote about logP generally, but the bound property is 'XLogP', one particular computed estimator. Applying 2 and 4 to an estimator's output without any calibration statement treats two different quantities as one scale; the definition's own logD caveat (claim_01M4TXF4QYFGNTQ6ZAFT5A947E) is the honest part of this.
  - `evidence_support` on claim_01M4TXF54AB5M65KFKHTW5S7C2 · severity `minor` · verdict `fail`: The propafenone-analogue quote concerns 'transporter selectivity, with P-gp activity being particularly sensitive to changes in lipophilicity compared with BCRP'. That is a transporter-selectivity finding in an unrelated chemotype, not evidence for an optimal logP band for this inhibitor class.

**Lineage and lifecycle**

- pool lineage `cri_01M4V1FPCHCHCPQF09A5DR9BYN` at version `3`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for oral_bioavailability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · direction within_range with predicate threshold <=4 drops the lower bound of 2 in the window stated by claim_01M4TXF4NN19J6JG3M3Y6T17V1, so a logP of 0 scores as well as a logP of 3.; This quote (low logP limits permeability) is cited and is precisely the counter-evidence the one-sided cutoff ignores; it is carried in the definition but not in the rule.; The attribute measures XLogP of the neutral species, while its own claim_01M4TXF4QYFGNTQ6ZAFT5A947E states logD reflects in vivo behaviour more
  - round `run_01M4V43E8GDH8GF8M633VTWDQJ` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · Three findings, all accepted. First, the one-sided <= 4 cutoff dropped the lower bound of the stated 2 to 4 window, so a logP of 0 scored as well as a logP of 3; as with molecular weight the quantity is changed rather than the rule patched, and the attribute now measures the distance in log units outside the stated band, zero inside it, with a plain ordering and no cutoff. Second, the counter-evidence quote that highly polar low-logP molecules show limited membrane permeability was carried in the prose but not in the rule; it is now encoded, because falling below the lower bound costs score exactly as exceeding the upper bound does. Third, the deprecation finding is accepted and stated openly instead of being glossed: the cited source does say that logD, which incorporates ionisation at physiological pH, reflects in vivo behaviour more faithfully than the neutral-species logP, and logD is not available from the evidence catalog. The definition and rationale now declare the computed value a proxy for a quantity the cited evidence prefers, name the consequence, that basic or acidic candidates will be mis-scored relative to neutral ones, and subordinate the attribute to any measured absorption endpoint.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `scoring` on `rules@v3`
- rule-set entry: `{"acceptable_value_sources": ["database_entry"], "attribute_ref": "attr_distance-of-computed-lipophilicity-outside-the-stated-band@v2", "authority": "machine_adjudication", "confirmed_by": "adj_01M4WY7SQ2RASTG0CF7VV562NA", "cutoff_basis": "none_evidence_insufficient", "disputed": false, "on_states": ["unknown_no_penalty", "unknown_no_penalty", "unknown_no_penalty"], "rule_kind": "preference", "rule_ref": "rule_distance-of-computed-lipophilicity-outside-the-stated-band@v2"}`
- scores while disputed: `False` · machine adjudicated: `True` · reads a collapsed attribute: `False`
- measured coverage: `{"assessed": 3177, "board": "lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4", "observed": 2956}`

---

### 8. Exposure loss with a strong CYP3A inducer

- **attribute** `attr_exposure-loss-with-a-strong-cyp3a-inducer@v1` · **rule** `rule_exposure-loss-with-a-strong-cyp3a-inducer@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_exposure-loss-with-a-strong-cyp3a-inducer@v1"]`, rule `["rule_exposure-loss-with-a-strong-cyp3a-inducer@v1"]`; supersedes —
- **record hashes**: attribute `a2a417671d71dd869ed49104bd3ea61ff40ea68c256396853cb29f17b90b0bd8`, rule `6f10e8275e02e79ecaca79eeafae81bf651ec0b4fb093cd22c531ce9e5315733`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1REGCQQPA9HWCGY6H2KK1@v6"}` · dimension `metabolic_stability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Exposure loss with a strong CYP3A inducer · subject `[{}]` · unit `% reduction in AUC` · `quantitative` · aggregated by `max` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `cdde241298444dc499b595cf12ce7b97a2943e84b6d54d5d8c8e7db49eb9a7b6`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `c09e82d669c44180a4ecc70a981b9773c129c6ce08587069a2a70074f8439b74`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The percentage reduction in systemic exposure (AUC) when the compound is co-administered with a strong CYP3A inducer, entered as a non-negative percentage of the exposure without the inducer. A loss reported as a fold is converted before entry: a reduction of F-fold enters as (1 minus 1 divided by F) times 100 percent, so a roughly 10-fold loss of exposure enters as approximately 90 percent, and no value may be entered as a bare fold. A reported change in apparent oral clearance, and a peak-concentration change, are different endpoints and are recorded rather than entered on this axis. Only an administered interaction study yields a value; a model-based projection is recorded as a prediction. Smaller losses are better, because loss of exposure is loss of target coverage.

- **unit** `% reduction in AUC` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `max`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates robust to enzyme induction rank above candidates that lose most of their exposure to a common anticonvulsant, antimicrobial or herbal product, which is the interaction least amenable to dose adjustment.
- **falsification test**: If induction effects are reported only as model predictions rather than administered studies the determination basis is predicted and must be recorded as such; the claims flag one such projection explicitly.
- **rationale**: The cited quotes give measured losses of 50, 72, 77, 80, 85 and 87 percent for agents of this class, and a roughly ten-fold loss for one agent, which is why the definition states the fold-to-percentage conversion rather than letting a fold and a percentage share one axis. They also state that the ability to compensate by dose escalation is agent-dependent and not always supported, so avoidance is generally recommended, and that strong inducers of this enzyme should be avoided with some agents of the class while another tolerates them, which shows the quantity is agent-specific rather than generic. The axis carries induction losses only: a quote about dietary or herbal inhibition of the same enzyme describes the opposite perturbation, supports no value here, and is no longer cited. Loss of exposure is the failure mode that silently removes the target coverage this screen selects for, and no cited quote states an acceptable loss, so the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `971cf61df275c600ed9ab95a125fbcc8ae4f1e039e817ffb928b8de4a1fcc049` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (rifampin OR rifampicin OR carbamazepine OR phenytoin OR \"St John\" OR \"strong CYP3A inducer\" OR \"enzyme-inducing\") AND (AUC OR exposure OR Cmax OR reduc*)", "relevance_terms": ["CYP3A inducer", "rifampin", "carbamazepine", "AUC", "reduction"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 5 cited claim(s), 5 carry `location.span_checked_against_source: true` and 5 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 4, `value_not_in_quote` 0, not recorded 1 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 5}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 4, "supports": 1}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TYZ6GYVQ0X24MFKYHWRR78** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% increase in metabolite exposure", "unit_as_reported": "% increase in metabolite exposure", "value": 264, "value_high": null, "value_low": null}`
  > Regorafenib | CYP3A4 + UGT1A9 | Ketoconazole/rifampin | Ketoconazole ↑ AUC 33%; rifampin ↓ AUC 50% (M-5 ↑ 264%) | Avoid strong inhibitors/inducers; striking metabolite shift
  - as recorded (paraphrase): One multikinase agent is metabolised by CYP3A4 and UGT1A9, with a strong inhibitor raising AUC 33% and a strong inducer lowering parent AUC 50% while raising one metabolite by 264%, a striking metabolite shift.
  - in `src_doi_10.3390/pharmaceutics18091082` at `table` `table3`, section Tables; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_e5f7c6487df7` sha256 `e5f7c6487df756b9cfbe25bf08a4f6bc8a19a1cc529e070a2c5b6a65919ef7c8` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 697
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TYZ6HAZGY1DQKD1TVGZYT7** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% reduction in AUC with strong inducer", "unit_as_reported": "% reduction in AUC with strong inducer", "value": 77, "value_high": null, "value_low": null}`
  > Cabozantinib | CYP3A4 substrate; P-gp inhibitor | Ketoconazole/rifampin | Ketoconazole ↑ AUC 38%; rifampin ↓ AUC 77% | Avoid strong inhibitors/inducers; if unavoidable, reduce by 20 mg
  - as recorded (paraphrase): One multikinase agent is a CYP3A4 substrate and P-glycoprotein inhibitor whose AUC rises 38% with a strong inhibitor and falls 77% with a strong inducer.
  - in `src_doi_10.3390/pharmaceutics18091082` at `table` `table3`, section Tables; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_3ebfe19eb321` sha256 `3ebfe19eb321b058722291d0b8e50677e3cba16d9285f56f911e69d060267036` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 698
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TYZ6HNVY0TRFMZFQH98P84** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% reduction in exposure", "unit_as_reported": "% reduction in exposure", "value": null, "value_high": 87, "value_low": 80}`
  > Strong inducers such as rifampin, carbamazepine, phenytoin and St. John’s wort accelerate clearance and reduce exposure, and the effect is frequently large: rifampin reduced exposure by approximately 80% for nilotinib, 85% for palbociclib, 87% for olaparib, and roughly 10-fold for ibrutinib; carbamazepine reduced lapatinib AUC by approximately 72% [40,43,44,52]. Because the ability to compensate by dose escalation is agent-dependent and not always supported, avoidance is generally recommended
  - as recorded (paraphrase): Strong inducers accelerate clearance and reduce exposure by approximately 80 to 87% for several agents and about 10-fold for one, and because compensation by dose escalation is not always supported, avoidance is generally recommended.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec7.2.p1`, section 7. CYP-Mediated and Transporter-Mediated Drug–Drug Interactions / 7.2. CYP3A4 Induction; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_79231bf8025e` sha256 `79231bf8025e198e6651215076c0463f93cfb61e45ee4e0f5f97aedf9a52df9f` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 699
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TZRMSEZG0XEHKSZCVPMAZZ** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% decrease in AUC", "unit_as_reported": "% decrease in AUC", "value": 85, "value_high": null, "value_low": null}`
  > co-administration with rifampicin, a strong CYP3A4/5 inducer, led to a decrease in lorlatinib AUC and Cmax by 85% and 76%, respectively, with an increased risk of hepatotoxicity (elevated level of AST/ALT with no modification of other hepatic indices of any grade according to CTCAE) within 3 days from administration
  - as recorded (paraphrase): A strong CYP3A4/5 inducer reduced one agent's AUC by 85% and Cmax by 76% and increased the risk of transaminase elevation within 3 days of administration.
  - in `src_doi_10.3389/or.2025.1612249` at `paragraph` `sec2.1.6.p1`, section 2 Results / 2.1 Lung cancer / 2.1.6 Lorlatinib; document `art_25fa3c4c8de6` sha256 `25fa3c4c8de6f66f5a12b8a0bd0f4d3835f97671a144fda008226feb06d42e6d`; claim `art_f243dd0f8089` sha256 `f243dd0f8089eaa478f43afc4fe3a86c509282765ef7e558e8c0f461fdbc5c9f` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 961
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

*polarity `supports`*

- **claim_01M4TZM5CZCJ3FNWMDT8WWRRNH** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > VEGF TKIs used in hepatocellular carcinoma (HCC) treatment, lenvatinib, sorafenib, regorafenib, and cabozantinib are metabolized by CYP3A4, but not all strong inducers/inhibitors have a clinical impact upon them. Strong CYP3A4 inducers should be avoided during sorafenib, regorafenib, and cabozantinib treatment, but can be used during lenvatinib treatment, while strong CYP3A4 inhibitors may be used during treatment with sorafenib and lenvatinib, but should be avoided when regorafenib and cabozantinib are administered
  - as recorded (paraphrase): Four VEGF-targeting oral agents are all metabolised by CYP3A4 yet differ in whether strong inducers or inhibitors must be avoided, so the interaction consequence is agent-specific rather than class-wide.
  - in `src_doi_10.3390/ph18070959` at `paragraph` `sec3.3.3.p1`, section 3. Pharmacokinetic Drug–Drug Interactions / 3.3. DDIs Affecting TKI Metabolization / 3.3.3. DDIs Affecting VEGF TKIs; document `art_e9c956a4dc7b` sha256 `e9c956a4dc7b2e7da4ec02d0d8ec260cd2ffb32e2749b82fcd654a8b87d3462a`; claim `art_d3168ec45894` sha256 `d3168ec45894306968a242af593b1d362f9a47a1456928040321d0e89ac4dc59` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 889
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `falsification_test_evaluated` on falsification_test · severity `material` · verdict `fail`: The test still asserts 'the claims flag one such projection explicitly'. None of this proposal's cited claims flags a model projection; the only predicted value in the request is the abemaciclib 16-fold figure inside claim_01M4TYZ6HZBETVC92XEY94VRYR, which concerns an inhibitor and is cited by proposal 12.

**Lineage and lifecycle**

- pool lineage `cri_01M4V1REGCQQPA9HWCGY6H2KK1` at version `6`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for metabolic_stability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Structured value 264 with unit '% increase in METABOLITE exposure'. On an attribute measuring percentage REDUCTION in parent AUC with direction lower_better and aggregation max, this wrong-analyte, wrong-sign figure would dominate the score.; Quote concerns CYP3A4 INHIBITION by foods and herbals - the opposite perturbation from the inducer this attribute measures.; Quote reports 80%, 85%, 87% and 72% alongside 'roughly 10-fold for ibrutinib', but is carried as a range of 80-87 '% reduction in ex
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The unit is '% reduction in AUC', but claim_01M4TYZ6HNVY0TRFMZFQH98P84 reports losses on two scales in one sentence, 'approximately 80% for nilotinib, 85% for palbociclib, 87% for olaparib, and roughly 10-fold for ibrutinib'. Unlike proposals 16 and 26 this definition states no conversion rule, so a fold reduction and a percentage reduction would be entered on the same axis.; The attribute is exposure loss with a strong CYP3A inducer, but this quote concerns dietary and herbal CYP3A4 inhibition,
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The fold-to-percentage conversion is now stated, so a roughly 10-fold loss enters as approximately 90 percent instead of sharing the axis with percentages unconverted, and clearance or peak-concentration changes are recorded rather than entered. The quote about dietary and herbal inhibition, the opposite perturbation, is dropped.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · This claim remains cited and still concerns the opposite perturbation: foods and herbs that 'may increase toxicity due to CYP3A4 inhibition or affect the efficacy because of the lower absorption'. An inhibition statement supports no value on an induction-loss axis.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The quote about dietary and herbal inhibition of the enzyme is now removed from supporting_claim_ids; the previous revision described the removal in the rationale without actually dropping the identifier. The axis is stated to carry induction losses only, so an inhibition statement cannot supply a value.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 9. Exposure ratio with a strong CYP3A inhibitor

- **attribute** `attr_exposure-ratio-with-a-strong-cyp3a-inhibitor@v1` · **rule** `rule_exposure-ratio-with-a-strong-cyp3a-inhibitor@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_exposure-ratio-with-a-strong-cyp3a-inhibitor@v1"]`, rule `["rule_exposure-ratio-with-a-strong-cyp3a-inhibitor@v1"]`; supersedes —
- **record hashes**: attribute `d09674ee3aa3a5caf19ca0ce12f1a62f96985e318e38db25779c3e17c5808cf7`, rule `96c6a24ff04f00bd44c9bd29ce8c3f18ff38681e7c78fafd0815d2a7f6954887`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1REFM5CHVJB09Z123N73V@v7"}` · dimension `metabolic_stability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Exposure ratio with a strong CYP3A inhibitor · subject `[{}]` · unit `fold increase in AUC` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `256345decedfe775c3585a09618abba91290b3f49951f3fc5bdf01ad0a1ef7af`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `51eb6a6688215e82ae6be4c3beac7a04dd73877326113ee936215150f6f8518c`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The ratio of the compound's systemic exposure (AUC) with a strong CYP3A inhibitor to its exposure without one, always expressed as a value of at least 1, taken from an administered clinical interaction study and recorded with the index inhibitor, its dose and duration, the victim dosing design, the population studied and the endpoint reported. Percentage increases are converted before entry: a 51 percent increase enters as 1.51 and a 141.79 percent increase enters as 2.42, and no value may be entered as a bare percentage. Where a source reports both a model-based prediction and an administered study, only the measured ratio is entered and the prediction is recorded as a prediction; a source offering a prediction alone yields unknown. A peak-concentration ratio is a different endpoint and is recorded rather than entered. Because the cited evidence states that interaction studies differ in index perpetrator, dose and duration, in whether the victim drug was given as a single dose or at steady state, in the population studied and in the endpoint reported, so that a larger reported fold change does not by itself establish that one agent is more interaction-prone than another and the values are best used as an indication of the order of magnitude, the comparison this attribute supports is coarse by construction: candidates whose ratios fall within the same order of magnitude are not separated by this attribute, and a ranking that would turn on a within-order difference is routed to a human rather than scored. A ratio near 1 is best. Where no administered study exists the attribute returns unknown, which carries no penalty and leaves the candidate unranked here rather than scored as insensitive; that a compound is a known substrate of the enzyme is recorded as an annotation, because no cited quote supports a number for the untested case.

- **unit** `fold increase in AUC` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose exposure barely moves with a strong inhibitor rank above candidates whose exposure multiplies by an order of magnitude, the ranking no longer depends on whether a source wrote a fold or a percentage, candidates separated only within an order of magnitude are not ordered by this attribute, and candidates with no administered study are unranked here with their substrate status recorded.
- **falsification test**: Re-derive every value from the source's own numbers and confirm the conversion. If the index inhibitors, doses and designs differ too widely the ratios are comparable only as orders of magnitude; and if the top-ranked candidates prove to be those with no dedicated study, the untested flag is not working and the attribute must be restricted to studied candidates.
- **rationale**: The cited quotes supply a graded series of measured results for this exact experiment, which after conversion to one scale runs from no clinically meaningful change through roughly 1.5-, 1.7-, 1.8-, 2.4- and 3.4-fold to 5.2- and 24-fold, together with the clinical consequence at the top of that range: co-administration of a strong inhibitor of this enzyme with one multi-kinase agent led to hepatic failure and death in a reported patient, and labels mandate defined dose reductions where co-administration is unavoidable. One cited quote states a model-based prediction of up to 16-fold alongside an administered study measuring 24-fold on exposure, which is why only the administered value is entered and the prediction is recorded as such. A further cited quote is the counter-evidence that sets the resolution of this attribute: interaction studies differ in index perpetrator, dose, duration, victim dosing design, population and endpoint, a larger reported fold change does not by itself establish that one agent is more interaction-prone than another, and such values are best used as an indication of the order of magnitude. That is why every value carries those design qualifiers, why the quantity is not treated as finely comparable between candidates, and why a ranking turning on a within-order difference goes to a human. Because the sources express the same measurement sometimes as a fold and sometimes as a percentage the conversion is specified, and because no quote states an acceptable ratio the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `5759ac8dc4bfdd4cef4f2193ffe0f3b215d571fddf3e9a2ed443d61e284c9b8c` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (ketoconazole OR itraconazole OR clarithromycin OR \"strong CYP3A4 inhibitor\" OR \"strong CYP3A inhibitor\") AND (AUC OR exposure OR Cmax OR fold OR percent)", "relevance_terms": ["CYP3A4 inhibitor", "ketoconazole", "itraconazole", "AUC", "fold"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 9 cited claim(s), 9 carry `location.span_checked_against_source: true` and 9 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 7, `value_not_in_quote` 0, not recorded 2 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 9}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 8, "inconclusive": 1}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TYZ6GBX3103NGN9T07NEGW** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "fold increase in AUC", "unit_as_reported": "fold increase in AUC", "value": 1.7, "value_high": null, "value_low": null}`
  > Pazopanib | CYP3A4 substrate; P-gp/BCRP substrate; UGT1A1/OATP1B1 inhibitor | Ketoconazole/rifampin | Ketoconazole ↑ AUC 1.7× | Avoid strong inhibitors; if unavoidable, reduce to 400 mg
  - as recorded (paraphrase): The VEGFR multikinase agent is a CYP3A4 and P-gp/BCRP substrate and a UGT1A1 and OATP1B1 inhibitor, a strong CYP3A4 inhibitor raises its AUC 1.7-fold, and the dose must be reduced to 400 mg if co-administration is unavoidable.
  - in `src_doi_10.3390/pharmaceutics18091082` at `table` `table3`, section Tables; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_060ccdd76d17` sha256 `060ccdd76d17686627c2f9e22a7b39241df517b3b6b172b7e1211b2c2082766f` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 695
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TYZ6GNYEDHER8S67EY8JQ7** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% increase in AUC with strong inhibitor", "unit_as_reported": "% increase in AUC with strong inhibitor", "value": 51, "value_high": null, "value_low": null}`
  > Sunitinib | CYP3A4 substrate | Ketoconazole/rifampin | Ketoconazole ↑ AUC 51%; rifampin ↓ AUC 46% | Reduce dose with a strong inhibitor (37.5 mg GIST/RCC; 25 mg pNET)
  - as recorded (paraphrase): One multikinase agent is a CYP3A4 substrate whose AUC rises 51% with a strong inhibitor and falls 46% with a strong inducer, requiring dose reduction with a strong inhibitor.
  - in `src_doi_10.3390/pharmaceutics18091082` at `table` `table3`, section Tables; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_3c59a591a855` sha256 `3c59a591a8557c93848453df5e46f9106bfdc60bdecc1a78ceeecddb09ffec6c` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 696
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TYZ6HZBETVC92XEY94VRYR** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "fold increase in AUC", "unit_as_reported": "fold increase in AUC", "value": 24, "value_high": null, "value_low": null}`
  > Strong CYP3A4 inhibitors, which include the azole antifungals ketoconazole and itraconazole, macrolides such as clarithromycin, and several protease inhibitors, reduce clearance and increase the exposure of substrate agents, sometimes dramatically. The abemaciclib label notes that ketoconazole is predicted to increase abemaciclib AUC up to 16-fold [33,60]. A dedicated study of ibrutinib found that ketoconazole increased ibrutinib Cmax and AUC by approximately 29-fold and 24-fold, respectively
  - as recorded (paraphrase): Strong CYP3A4 inhibitors reduce clearance and increase substrate exposure, in one dedicated study by approximately 29-fold for Cmax and 24-fold for AUC.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec7.1.p1`, section 7. CYP-Mediated and Transporter-Mediated Drug–Drug Interactions / 7.1. CYP3A4 Inhibition; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_5a5c75fbbab8` sha256 `5a5c75fbbab8117b79104278a7a90cadbdfa43faa0e980869c349d8c0e1f9c09` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 700
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TZM5G7W90RYH1N7D2BYAP5** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Pazopanib is metabolized by CYP3A4 mainly, followed by CYP1A2 and CYP2C8, but it is also a substrate for P-glycoprotein and BRCP, contributing to elimination into the gastrointestinal tract through biliary secretion [53]. Concomitant administration with clarithromycin, an antibiotic prescribed for acute bronchitis and a strong CYP3A4 inhibitor, led to hepatic failure and death in a 44-year-old renal cancer patient
  - as recorded (paraphrase): The oral agent covering VEGFR1-3 is metabolised mainly by CYP3A4 with contributions from CYP1A2 and CYP2C8 and is a P-glycoprotein and BCRP substrate eliminated by biliary secretion, and co-administration with a strong CYP3A4 inhibitor led to hepatic failure and death in a reported patient.
  - in `src_doi_10.3390/ph18070959` at `paragraph` `sec3.3.4.p1`, section 3. Pharmacokinetic Drug–Drug Interactions / 3.3. DDIs Affecting TKI Metabolization / 3.3.4. DDIs Affecting Multiple Target TKIs; document `art_e9c956a4dc7b` sha256 `e9c956a4dc7b2e7da4ec02d0d8ec260cd2ffb32e2749b82fcd654a8b87d3462a`; claim `art_6663823f306d` sha256 `6663823f306d95cde7384a4fe10184dbe701beafdcc205791a76a845c27ce344` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 894
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`
- **claim_01M4TZM5M405VH8NBN5YTW8YZW** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "fold increase in exposure", "unit_as_reported": "fold increase in exposure", "value": 3.4, "value_high": null, "value_low": null}`
  > Co-administration of rifampicin, a potent CYP3A4 inducer, significantly decreased bioavailability, while co-administration of ketoconazole, a potent CYP3A4 inhibitor, increased crizotinib exposure by 3.4-fold
  - as recorded (paraphrase): For one agent a potent CYP3A4 inducer significantly decreased bioavailability while a potent inhibitor increased exposure 3.4-fold.
  - in `src_doi_10.3390/ph18070959` at `paragraph` `sec3.3.1.p1`, section 3. Pharmacokinetic Drug–Drug Interactions / 3.3. DDIs Affecting TKI Metabolization / 3.3.1. DDIs Affecting ALK TKIs; document `art_e9c956a4dc7b` sha256 `e9c956a4dc7b2e7da4ec02d0d8ec260cd2ffb32e2749b82fcd654a8b87d3462a`; claim `art_f84897d26966` sha256 `f84897d26966382770ef69368e5d98121db42aa8673d90cf40a8f7725e820c5e` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 900
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TZRMP7FDP332025ZZJHKMR** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% increase in AUC", "unit_as_reported": "% increase in AUC", "value": 82, "value_high": null, "value_low": null}`
  > Itraconazole significantly increased brigatinib exposure (AUC + 82%), while rifampicin led to an important decrease in brigatinib’s plasma levels (AUC − 80%). These findings suggest a significant impact on brigatinib systemic exposure. This may result in decreased brigatinib efficacy, even though further clinical investigations are needed. Hence, co-administration of strong CYP3A inhibitors and inducers should be avoided, but if unavoidable, a 50% dose reduction in brigatinib is recommended
  - as recorded (paraphrase): A strong CYP3A inhibitor raised one agent's AUC by 82% and a strong inducer lowered it by 80%, so both should be avoided and a 50% dose reduction is recommended if unavoidable.
  - in `src_doi_10.3389/or.2025.1612249` at `paragraph` `sec2.1.3.p1`, section 2 Results / 2.1 Lung cancer / 2.1.3 Brigatinib; document `art_25fa3c4c8de6` sha256 `25fa3c4c8de6f66f5a12b8a0bd0f4d3835f97671a144fda008226feb06d42e6d`; claim `art_98d090db9a97` sha256 `98d090db9a9767970b8fc0921446e692245c0aa06021a87c6928ac3394515a4b` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 952
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TZRMQQHEA6VMW1TMG88FQ9** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "fold increase in AUC", "unit_as_reported": "fold increase in AUC", "value": 5.2, "value_high": null, "value_low": null}`
  > Xiu et al. (26), in a phase 1 trial in healthy volunteers, demonstrated that concomitant administration with a strong CYP3A inhibitor led to 5.2- and 1.6-fold increases in AUC and Cmax, respectively, while a CYP3A inducer caused a marked reduction in crizotinib systemic exposure (AUC by 94% and Cmax by 89%)
  - as recorded (paraphrase): In a phase 1 trial a strong CYP3A inhibitor raised one agent's AUC 5.2-fold and Cmax 1.6-fold while an inducer reduced AUC by 94% and Cmax by 89%.
  - in `src_doi_10.3389/or.2025.1612249` at `paragraph` `sec2.1.5.p1`, section 2 Results / 2.1 Lung cancer / 2.1.5 Crizotinib; document `art_25fa3c4c8de6` sha256 `25fa3c4c8de6f66f5a12b8a0bd0f4d3835f97671a144fda008226feb06d42e6d`; claim `art_da37dfae5d95` sha256 `da37dfae5d9546e653cecaaeecb4042a498efcf3c2f2522d1e466daae3531767` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 956
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) phase 1 trial in healthy volunteers · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TZRMSVD3ZYECRQQB17TJSQ** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% increase in AUC", "unit_as_reported": "% increase in AUC", "value": 141.79, "value_high": null, "value_low": null}`
  > Patel et al. demonstrated in healthy volunteers that the strong CYP3A4 inhibitor itraconazole elevated lorlatinib AUC and Cmax by 141.79% (90% CI, 128.71%, and 156.21%) and 124.39% (90% CI, 110.20%, and 140.41%), respectively, although this was not associated with an increased risk of AEs. Hence, lorlatinib co-administration with strong CYP3A4 inhibitors may lead to a relevant DDI and should be avoided; therefore, if this combination is unavoidable, the starting dose of lorlatinib should be reduced from 100 mg to 75 mg
  - as recorded (paraphrase): A strong CYP3A4 inhibitor raised one agent's AUC by 141.79% and Cmax by 124.39% without increased adverse events, but the combination should be avoided and the starting dose reduced from 100 mg to 75 mg if unavoidable.
  - in `src_doi_10.3389/or.2025.1612249` at `paragraph` `sec2.1.6.p1`, section 2 Results / 2.1 Lung cancer / 2.1.6 Lorlatinib; document `art_25fa3c4c8de6` sha256 `25fa3c4c8de6f66f5a12b8a0bd0f4d3835f97671a144fda008226feb06d42e6d`; claim `art_a69dd0af58a1` sha256 `a69dd0af58a1ef4be24eba7b9ebc4f7165e5db3b2576d30e1f67f6428fe09394` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 962
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) healthy volunteers · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

*polarity `inconclusive`*

- **claim_01M4TYZ6N61H4K84ZQ795M2T9E** · `inconclusive` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Interaction studies differ in the index perpetrator used and in its dose and duration, in whether the victim drug was given as a single dose or at steady state, in the population studied, and in the endpoint reported, so a larger reported fold-change does not by itself establish that one agent is more interaction-prone than another. The values are best used as an indication of the order of magnitude of the effect for the agent concerned, and of the management response that it requires
  - as recorded (paraphrase): Interaction studies differ in perpetrator, dose, duration, single-dose versus steady-state design, population and endpoint, so a larger reported fold change does not establish that one agent is more interaction-prone, and values indicate order of magnitude only.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec7.4.p2`, section 7. CYP-Mediated and Transporter-Mediated Drug–Drug Interactions / 7.4. Transporter-Mediated Interactions; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_7b8e7d9c42de` sha256 `7b8e7d9c42debeae6a9c2d5587d986c317fa4ddd90eac523247f1db514c8f5cf` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 708
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `evidence_support` on claim_01M4TZM5G7W90RYH1N7D2BYAP5 · severity `minor` · verdict `fail`: This claim remains cited and still reports an outcome rather than a ratio, concomitant clarithromycin having 'led to hepatic failure and death in a 44-year-old renal cancer patient'; it supports the severity of the liability but supplies no value on the fold axis.

**Lineage and lifecycle**

- pool lineage `cri_01M4V1REFM5CHVJB09Z123N73V` at version `7`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for metabolic_stability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · unit 'fold increase in AUC' with agg max pools fold values (claim_01M4TYZ6HZBETVC92XEY94VRYR=24, claim_01M4TYZ6GBX3103NGN9T07NEGW=1.7) with percentages (claim_01M4TZRMSVD3ZYECRQQB17TJSQ=141.79, claim_01M4TZRMP7FDP332025ZZJHKMR=82, claim_01M4TYZ6GNYEDHER8S67EY8JQ7=51). A +141.79% effect (~2.4-fold) then outscores a genuine 24-fold interaction.; Quote sets a bioavailability threshold (<50%) marking interaction sensitivity; it is not an exposure fold change and cannot supply a value for this attrib
  - round `run_01M4V43E8GDH8GF8M633VTWDQJ` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The blocking finding is accepted and fixed at the scale: fold values and percentage increases were pooled on one axis, so a 141.79 percent increase, which is about 2.4-fold, outranked a 24-fold increase as the worse result. The definition now specifies a single quantity, the ratio of exposure with a strong CYP3A inhibitor to exposure without it, always at least 1, and requires percentage increases to be converted before entry, a 51 percent increase entering as 1.51 and a 141.79 percent increase as 2.42. The first material finding is accepted and the offending citation dropped: the quote setting a bioavailability threshold below which agents are interaction-sensitive is not an exposure fold change and cannot supply a value here. The second material finding is accepted too: aggregation by maximum together with an unpenalised unknown scored the best-characterised candidate at its worst study and the unstudied candidate at nothing, so aggregation becomes median and the definition now requires an absent dedicated study to be recorded as untested rather than treated as favourable.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The definition admits values only 'from a dedicated clinical interaction study', but this quote mixes a prediction with a study: 'ketoconazole is predicted to increase abemaciclib AUC up to 16-fold' alongside a dedicated ibrutinib study at 29-fold Cmax and 24-fold AUC. The predicted 16-fold is inadmissible under the attribute's own rule, and the claim's single value field records 24.; The definition says an unstudied candidate is 'recorded as untested, not as favourable', but rule.on_missing is 
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The definition now says what to do with a source that mixes a prediction and an administered study: only the measured ratio is entered, the prediction is recorded as a prediction, and a prediction alone yields unknown, which keeps the cited claim's measured 24-fold value admissible and its predicted 16-fold out. The definition also no longer promises to disfavour an unstudied substrate when the rule gives unknown no penalty; substrate status is recorded as an annotation instead.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · claim_01M4TYZ6N61H4K84ZQ795M2T9E is in this request and states that interaction studies differ in index perpetrator, dose, duration, population and endpoint, so 'a larger reported fold-change does not by itself establish that one agent is more interaction-prone than another' and the values are 'best used as an indication of the order of magnitude'. It is not cited here, and the attribute ranks candidates on a median of such ratios, which is the comparison that claim denies. Proposal 8 made exact
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The counter-evidence is now cited and implemented: because the cited quote states that interaction studies differ in index perpetrator, dose, duration, victim dosing design, population and endpoint, so that a larger fold change does not by itself make one agent more interaction-prone and the values are best read as orders of magnitude, every value now carries those design qualifiers, candidates within the same order of magnitude are not separated by this attribute, and a ranking that would turn on a within-order difference is routed to a human.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 10. FGFR1 affinity on the independent expert curation

- **attribute** `attr_fgfr1-affinity-on-the-independent-expert-curation@v1` · **rule** `rule_fgfr1-affinity-on-the-independent-expert-curation@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_fgfr1-affinity-on-the-independent-expert-curation@v1"]`, rule `["rule_fgfr1-affinity-on-the-independent-expert-curation@v1"]`; supersedes —
- **record hashes**: attribute `978cef15a0df3e0860788e518666e1d130c2ee468cd84535e79669ab272bf8d1`, rule `77d1d66a7fd677a90b5de86f72c9e1b2c434c0ddc0527cbe03c4de7fbd5b9185`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V183E5YCPRK4PS73H751KS@v6"}` · dimension `target_coverage`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: FGFR1 affinity on the independent expert curation · subject `[{"target_chembl_id": "CHEMBL3650"}]` · unit `pChEMBL` · `quantitative` · aggregated by `median` · transform —
  - read from `["interaction_evidence_lookup"]` asking `["gtopdb_affinity"]`; evidence kinds `["curated_measurement"]`; determination bases —
  - measurement identity `7154d3cf8887a33fdc1a7e4b4d38e5bb5c4475c4e5e3bfdd99346507f146f860`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `unknown_no_penalty` · decision identity `e75e0d2a6f608ee53eeb7853fb6e72557fd22a6da04a469e89969bbf2c50f915`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The median expert-curated affinity of the compound at fibroblast growth factor receptor 1, on the pChEMBL scale, that is the negative base-ten logarithm of the molar half-maximal inhibitory concentration, inhibition constant or dissociation constant as the curation reports it. Higher is better. The source bound here is an expert curation independent of the activity table that the registry's potency criterion for this receptor reads, and it can cover compound-target pairs that table lacks, which is the gap this attribute is for: a candidate whose engagement of this receptor is absent from one curation may be quantified in the other. It is therefore not a restatement of the registry criterion and does not replace it. The two read different sources, the median is taken over the records this source returns rather than a maximum, because a maximum rises with the number of records, and the action type and any selectivity comment travel with each record for a narrative to cite. Where the two curations disagree materially about the same compound the conflict is routed to a human rather than averaged. Absence of a record gives unknown and never a failure, because this curation is sparse outside developed and late-stage drugs.

- **unit** `pChEMBL` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `median`
- **accepted evidence kinds** `["curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose affinity at this receptor is quantified by a curation independent of the activity table are ranked on that measurement, which recovers coverage evidence for candidates the activity table does not cover, while candidates with no record in either curation are not penalised.
- **falsification test**: Compare this curation's values with the registry potency criterion for the same receptor across the pool. If the two agree everywhere and cover the same candidates, this attribute adds nothing and should be merged into that criterion; if they disagree materially for a candidate, the conflict is routed to a human rather than averaged. If the curation returns no record for any candidate the attribute yields only unknowns.
- **rationale**: This is a required receptor, and the cited quotes show that nominal and real coverage of it differ: an approved oral inhibitor of the family exists, overexpression of this receptor is tied to disease biology, adding coverage of it to a vascular-receptor backbone is described as supplying an additional antiangiogenic mechanism, one agent potent at the vascular receptors is stated to inhibit it only weakly, and another is reported to inhibit it with low nanomolar potency. A quantified affinity separates documented engagement from an unquantified family-level mention, which is exactly the distinction the weak-inhibition quote shows matters. The mechanism-of-action record source this attribute previously read stamps every claim it returns with determination basis curated, a basis excluded by the bases an attribute here accepts, so every record it returned would be set aside at assessment time and the attribute would carry no evidence at all; that is the finding this revision answers. The attribute is therefore bound instead to the independent expert curation of affinity at this receptor, which returns measured values on the pChEMBL scale and, being independent of the activity table, reaches compound-target pairs that table lacks, the same gap the record-based form was meant to close, while stating how strongly rather than only that engagement is documented. No cited quote states a required affinity at this receptor, so the rule is an ordering with no cutoff, and an absent record is unknown rather than a failure.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `unknown_no_penalty`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `afe89945e9a38656bd401dd4a65d65881cad121a5516eb2d2d7bca7740a70bf2` · 1 route(s) · literature-bound `False`
  - route `interaction_evidence_lookup` / `gtopdb_affinity` · subject `{"target_chembl_id": "CHEMBL3650"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 5 cited claim(s), 5 carry `location.span_checked_against_source: true` and 5 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 5 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 5}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 1, "supports": 4}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TYG06JXTGFNNYMFCFYXM4Z** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Fruquintinib, a second‐generation RTKI, is a highly selective and potent small‐molecule inhibitor targeting VEGFR1/2/3 [87, 213, 214] with weak inhibition of RET, FGFR‐1 and KIT
  - as recorded (paraphrase): A second-generation agent is a highly selective and potent inhibitor of VEGFR1, VEGFR2 and VEGFR3 with only weak inhibition of RET, FGFR1 and KIT.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec3.1.3.2.p1`, section Review / Receptor Tyrosine Kinase Inhibitors / Theoretical Risk / Fruquintinib; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_147b8939b346` sha256 `147b8939b346676ffd5462fc1717195839d0269b6109b3dd1ddaf652f4c7ac86` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 502
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

*polarity `supports`*

- **claim_01M4TX99MPPTCDR7AZQFCBN9ZY** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Pemigatinib | FGFR | Cholangiocarcinoma with FGFR2 fusions or rearrangements
  - as recorded (paraphrase): An approved oral tyrosine kinase inhibitor targeting FGFR exists, indicated for cholangiocarcinoma with FGFR2 fusions or rearrangements.
  - in `src_nbk_NBK563322` at `table` `article-109800.table1`, section Tables; document `art_f39aa2170bbb` sha256 `f39aa2170bbb6e797aa143c217673d26d91bf5238802cedbd23bc4621ce110fc`; claim `art_d8692b9510f5` sha256 `d8692b9510f5a67187fdda85164f3b85427e7e52dc22a139d9f1a47e3429b632` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 104
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXF4F1YW5CXVC4K1KKQ43T** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > FGFR1 | FGFR1 overexpression | Variable | Associated with glioma stem-cell maintenance, invasion, recurrence and radioresistance. | MAPK; PI3K/AKT
  - as recorded (paraphrase): FGFR1 overexpression is of variable frequency and is associated with glioma stem-cell maintenance, invasion, recurrence and radioresistance through MAPK and PI3K/AKT signalling.
  - in `src_doi_10.3390/ijms27156590` at `table` `table1`, section Tables; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_92a465b75d9b` sha256 `92a465b75d9baac5fc5ac0abc40a32126ea6135898c4c6ba29ff44e4d29aa14b` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 120
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXXAAFWX2DY726ZA49AZ65** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > FGFR inhibition, unique to lenvatinib (compared to sunitinib and sorafenib), provides an additional mechanism of inhibition of angiogenesis.
  - as recorded (paraphrase): FGFR inhibition, which distinguishes one multi-targeted agent from two other approved VEGFR multi-kinase agents, provides an additional mechanism of angiogenesis inhibition.
  - in `src_nbk_NBK563230` at `paragraph` `article-28341.s9.p37`, section Treatment / Management; document `art_55e79771f56d` sha256 `55e79771f56d1e6d548de79bb180e4c496477cca454dd8e3a79d1718f5793133`; claim `art_900325c148aa` sha256 `900325c148aa3a6606b72844c8ee79dc457fecf6e5f4eb3e9544b03ca0810fd8` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 279
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYG095KQSAJK11CPP0R5ER** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "nM (low nanomolar IC50)", "unit_as_reported": "nM (low nanomolar IC50)", "value": null, "value_high": null, "value_low": null}`
  > Infigratinib, an RTKI, inhibits FGFR1, FGFR2 and FGFR3 with low nanomolar IC50 values, showing reduced FGFR4 activity.
  - as recorded (paraphrase): An agent inhibits FGFR1, FGFR2 and FGFR3 with low nanomolar IC50 values and reduced activity on FGFR4.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec3.1.3.3.p1`, section Review / Receptor Tyrosine Kinase Inhibitors / Theoretical Risk / Infigratinib; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_93b36bf7841a` sha256 `93b36bf7841a9fabdc751493b3a1f3a8c3db2c314c5dc8b19c6590acab98e6a8` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 506
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review item `q_01M4VEGRH173PAZ8PYESTZ9SPJ` (`open`, blocking `True`, raised 2026-10-13T20:16:01.569Z): proposer and critic still disagree after one revision
  - inspection bundle: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "open_critic_findings": [{"check": "evidence_support", "finding": "This is the nearest to on-endpoint of the five cited claims, 'Infigratinib ... inhibits FGFR1, FGFR2 and FGFR3 with low nanomolar IC50 values', but it states a range in words and its value field is null, so no pChEMBL can be derived; claim_01M4TYG06JXTGFNNYMFCFYXM4Z reports FGFR1 engagement as weak and the remaining three are target-relevance rows.", "proposal_index": 4, "referent": "claim_01M4TYG095KQSAJK11CPP0R5ER", "severity": "material", "verdict": "fail"}], "pool_criterion": "cri_01M4V183E5YCPRK4PS73H751KS"}`
- unresolved proposer/critic disputes: `q_01M4VEGRH173PAZ8PYESTZ9SPJ`
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `evidence_support` on claim_01M4TYG095KQSAJK11CPP0R5ER · severity `material` · verdict `fail`: This is the nearest to on-endpoint of the five cited claims, 'Infigratinib ... inhibits FGFR1, FGFR2 and FGFR3 with low nanomolar IC50 values', but it states a range in words and its value field is null, so no pChEMBL can be derived; claim_01M4TYG06JXTGFNNYMFCFYXM4Z reports FGFR1 engagement as weak and the remaining three are target-relevance rows.

**Lineage and lifecycle**

- pool lineage `cri_01M4V183E5YCPRK4PS73H751KS` at version `6`, state `promoted`
- parents — · children —
- merged away: `{"collapse_id": "clp_01M4WXKPEB4X4X3ZSBETYZ9EXX", "into": "attr_fgfr1-curated-potency@v2", "reason_text": "2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL3650. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_fgfr1-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.", "withdrawn": false}`
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for target_coverage
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · arbitrary_cutoff: source_stated_value cutoff without a cited claim carrying a value
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The validator was right: a cutoff of 'equals true' carries no value taken from any cited quote, so declaring cutoff_basis source_stated_value invented a standard the claims do not state. The rule is therefore rebuilt as a preference with predicate_form ordering, cutoff null and cutoff_basis none_evidence_insufficient, and the direction is set to higher_better so documented engagement ranks above undocumented engagement without any threshold being asserted. Two further corrections follow from the evidence catalog's own instruction for this entry: acceptable_determination_bases is now declared as ['curated'], without which every record-derived claim would be set aside and the attribute would see no evidence at all, and the definition now states in terms that a record is an expert assertion rather than a measurement and must never stand in for a potency value. The cited claims are unchanged.
  - round `run_01M4V52W85KZMCC0X2A7BN1YR3` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · evidence_support: the bound source returns curated records and acceptable_determination_bases ['measured', 'derived'] excludes that basis, so every value it returns would be set aside and the attribute would carry no evidence
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `needs_refine` · `refined_still_failing` · evidence_support: the bound source returns curated records and acceptable_determination_bases ['measured', 'derived'] excludes that basis, so every value it returns would be set aside and the attribute would carry no evidence
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The bound mechanism-of-action record source returns claims stamped determination basis curated, which the accepted bases exclude, so every record would have been set aside and the criterion would have measured nothing; declaring the basis on the attribute did not survive the previous revision, so the finding is resolved the other way, by binding the attribute to the independent expert affinity curation for the same receptor, whose records are measured values on the pChEMBL scale. The definition states that this curation is independent of the activity table the registry's potency criterion reads, which is the coverage gap the record-based form was meant to close, that it does not replace that criterion, and that a material disagreement between the two is routed to a human.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `disputed` · —

**Use**

- status `collapsed_away` on `rules@v3` — its attribute was merged into attr_fgfr1-curated-potency@v2 by clp_01M4WXKPEB4X4X3ZSBETYZ9EXX; rule_fgfr1-curated-potency@v2 scores the quantity
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 11. FGFR1 curated potency

- **attribute** `attr_fgfr1-curated-potency@v2` · **rule** `rule_fgfr1-curated-potency@v2` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_fgfr1-curated-potency@v1", "attr_fgfr1-curated-potency@v2"]`, rule `["rule_fgfr1-curated-potency@v1", "rule_fgfr1-curated-potency@v2"]`; supersedes `attr_fgfr1-curated-potency@v1`
- **record hashes**: attribute `6ffaf8a49a76a4f878c4ce11fe59e107b3b60d53c783e517f95e4136556e62e9`, rule `05f20a5fae727ef54118eafee2c84c807a926014e40a5fd2754b7d5d29c6cb37`
- **origin**: `task_mandated_template` · proposed by `{"id": "objective-criteria", "kind": "system", "role": "adapter_template"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"field": "scope_entities[4]", "task_context": "task_01M4TWZXZEB1SQPS7H47C8BX01@v1"}` · dimension —
- **written by software**: `{"collapsed_by": "clp_01M4WXKPEB4X4X3ZSBETYZ9EXX", "rule_collapsed_by": "clp_01M4WXKPEB4X4X3ZSBETYZ9EXX"}`

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: FGFR1 curated potency · subject `[{"target_chembl_id": "CHEMBL3650"}]` · unit `pChEMBL` · `quantitative` · aggregated by `median` · transform —
  - read from `["interaction_evidence_lookup"]` asking `["gtopdb_affinity", "pchembl_values"]`; evidence kinds `["curated_measurement"]`; determination bases —
  - measurement identity `a384009269ddae7cb0ad67e991ec2644f154bf8db16181e0b9d3004a56e886ef`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_blocks_recommendation` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `unknown_blocks_recommendation` · decision identity `ae5f3b84f28f6ccb642a79a745d7784804b4335ad54b733b9596e0b22fb5c470`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> Median pChEMBL value over curated point measurements against FGFR1 (CHEMBL3650)

- **unit** `pChEMBL` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `median`
- **accepted evidence kinds** `["curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_blocks_recommendation", "stated_in_definition_only": true}`
- **expected change**: —
- **falsification test**: —
- **rationale**: FGFR1 is a required target of the task

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_blocks_recommendation` · **on conflict** `unknown_blocks_recommendation`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `cf5506329f53a41bac7f4ae2d446e0fa76e73890b5293d57d157750e56b7df74` · 2 route(s) · literature-bound `False`
  - route `interaction_evidence_lookup` / `pchembl_values` · subject `{"target_chembl_id": "CHEMBL3650"}` · retrieval — · identifier scheme `inchikey`
  - route `interaction_evidence_lookup` / `gtopdb_affinity` · subject `{"target_chembl_id": "CHEMBL3650"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 0 cited claim(s), 0 carry `location.span_checked_against_source: true` and 0 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` — (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: —
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage — at version —, state —
- parents — · children —
- merged away: —
- survived a collapse: `{"absorbed": ["attr_fgfr1-affinity-on-the-independent-expert-curation@v1"], "collapse_id": "clp_01M4WXKPEB4X4X3ZSBETYZ9EXX", "reason_text": "2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL3650. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_fgfr1-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.", "routes_after": ["pchembl_values", "gtopdb_affinity"], "routes_before": ["pchembl_values"], "withdrawn": false}`
- refinement history: — (this criterion never entered the pool)

**Use**

- status `scoring` on `rules@v3`
- rule-set entry: `{"acceptable_value_sources": ["curated_measurement"], "attribute_ref": "attr_fgfr1-curated-potency@v2", "authority": "trigger_table", "confirmed_by": "auto:trigger_table", "cutoff_basis": "none_evidence_insufficient", "disputed": false, "on_states": ["unknown_no_penalty", "unknown_blocks_recommendation", "unknown_blocks_recommendation"], "rule_kind": "preference", "rule_ref": "rule_fgfr1-curated-potency@v2"}`
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `True`
- measured coverage: `{"assessed": 3177, "board": "lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4", "observed": 40}`

---

### 12. Food effect on systemic exposure as a fold deviation

- **attribute** `attr_food-effect-on-systemic-exposure-as-a-fold-deviation@v1` · **rule** `rule_food-effect-on-systemic-exposure-as-a-fold-deviation@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_food-effect-on-systemic-exposure-as-a-fold-deviation@v1"]`, rule `["rule_food-effect-on-systemic-exposure-as-a-fold-deviation@v1"]`; supersedes —
- **record hashes**: attribute `92dec85744eab2d4e74d667bd791e393cd556d53a70be3877e1a224847188e97`, rule `a9b8b3febdc623a1c4049d0cc20eaadbdc2bdc4cc388b3cdd1da6c22eabbe5c2`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1FPGN9YZDQHG93BJGSQZY@v7"}` · dimension `oral_bioavailability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Food effect on systemic exposure as a fold deviation · subject `[{}]` · unit `fold deviation from unity` · `quantitative` · aggregated by `max` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `7929105da3e00b690e8ecd546b3b143508e1d78f8a1fe68dab87909ce95d27fa`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `5cb341a74692e80eca9085520282aeb536fdcf8069f7c35e7ed74f7309c91c77`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The fold change in systemic exposure (AUC) between the fed and fasted states, expressed as a ratio of at least 1 in whichever direction the effect runs: the fed-to-fasted ratio where food increases exposure and the fasted-to-fed ratio where food decreases it, so the quantity measures the size of the prandial effect and not its sign. Percentage changes in exposure are converted before entry, a 20 percent increase entering as 1.20 and a doubling as 2.00, and no value may be entered as a bare percentage. A ratio of fed to fasted absolute bioavailability is a different quantity on a different endpoint and is not admitted here, and no conversion between the two is attempted; such a figure is recorded with the oral bioavailability attribute instead. Each value is recorded with the study population, the dose and whether dosing was single or at steady state, the caloric and fat content of the test meal, the analyte measured and the exposure endpoint reported, because the cited evidence states that values drawn from studies differing in those respects are not the output of a common experiment and should not be read as strictly comparable measurements. Values from studies differing in those respects are therefore not pooled: a label-derived value measured against a standard meal is preferred where one exists, and an unresolved disagreement between designs is routed to a human rather than averaged. A value of 1.00 means exposure is unaffected by food and is the best score; larger values are worse whether the effect is an increase or a decrease.

- **unit** `fold deviation from unity` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `max`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose exposure is insensitive to the prandial state score near 1.00 and rank above candidates requiring strict fasting or a specified meal composition; a candidate whose exposure falls with food is penalised as much as one whose exposure rises; and candidates whose only values come from incomparable study designs are routed to a human rather than ranked against each other.
- **falsification test**: Re-derive every value from the source's own numbers and check the conversion. If food-effect studies for the candidates used different meal compositions, analytes or dosing designs, the ratios are not strictly comparable between candidates and the attribute must be restricted to label-derived values measured against a standard high-fat meal.
- **rationale**: The cited quotes span the whole range of this property and show it dictates the dosing instruction in both directions. A meal approximately doubles exposure for one multi-kinase agent, which must be dosed fasting; another must be taken with a specifically low-fat meal because both high-fat meals and fasting lower active-metabolite exposure; food increases exposure by roughly 20 percent for another with delayed absorption; one agent has 98 percent bioavailability regardless of food; and several show no effect and may be taken either way. Because effects run in both directions the quantity is unsigned, and because the same quotes report some effects as folds and others as percentages the conversion is specified rather than left to the reader. A further cited quote states that the food-effect studies these values come from differ in population, dose, single-dose versus steady-state design, meal composition, analyte and endpoint, and that descriptions of relative size should not be read as strictly comparable measurements; that quote is what the recorded qualifiers and the refusal to pool across designs implement. The axis carries exposure ratios only. A fed-versus-fasted change in absolute bioavailability is a different endpoint, no quote reporting one is cited here, and any such figure belongs to the oral bioavailability attribute, which records the prandial state with each value.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `f6b2a970cdb16af91a046dbeb2002c7bfb99a3a63fdbef94ba99fd00046fbb2d` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"food effect\" OR \"high-fat meal\" OR \"fed state\" OR \"fasted state\" OR \"with food\" OR \"empty stomach\") AND (AUC OR Cmax OR exposure OR bioavailability)", "relevance_terms": ["food effect", "high-fat meal", "fasted", "AUC", "Cmax"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 7 cited claim(s), 7 carry `location.span_checked_against_source: true` and 7 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 3, `value_not_in_quote` 0, not recorded 4 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 7}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 4, "inconclusive": 1, "supports": 2}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TY1R97AG7D77VHD3S4GYJR** · `conflicts` · evidence `reference_text` · determination `measured` · value `{"unit": "% increase in exposure with food", "unit_as_reported": "% increase in exposure with food", "value": 20, "value_high": null, "value_low": null}`
  > Following food intake, nintedanib exposure increases by roughly 20% compared to fasting conditions, with delayed absorption.
  - as recorded (paraphrase): Food increases exposure by roughly 20% relative to fasting and delays absorption.
  - in `src_nbk_NBK585049` at `paragraph` `article-143222.s3.p3`, section Mechanism of Action; document `art_d6f5f137dcb6` sha256 `d6f5f137dcb662288deb6e65d17790449f04dce1f0a228cee80848efe41da003`; claim `art_9d775c4041b5` sha256 `9d775c4041b5f8483a1e0da5f934945c3b9a6566f35e503fe6098284fa5b2ed0` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 345
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYZ6926W2AJ5MSPENYN33P** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Food can alter the bioavailability of an oral anticancer agent substantially, and the direction and magnitude of the effect are agent-specific [1,9]. A meal changes the gastrointestinal environment in several ways that bear on drug absorption: it delays gastric emptying, stimulates biliary and pancreatic secretion, raises gastric pH transiently, increases splanchnic blood flow, and—particularly for a high-fat meal—provides lipid that can solubilize poorly water-soluble compounds and recruit them into mixed micelles. The net effect on a given drug depends on which of these mechanisms predominate
  - as recorded (paraphrase): Food can substantially alter oral bioavailability in an agent-specific direction and magnitude because a meal delays gastric emptying, stimulates biliary and pancreatic secretion, transiently raises gastric pH, increases splanchnic blood flow and provides lipid that solubilises poorly soluble compounds into mixed micelles.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec5.p1`, section 5. Food Effects on Oral Anticancer Agents; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_9d7ccd4e8d44` sha256 `9d7ccd4e8d443819ed00fca521de2afc8eb97110107ee247eba3247d1f1ba680` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 673
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`
- **claim_01M4TYZ69P208EDHPQQVAAAKYF** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "fold increase in AUC and Cmax", "unit_as_reported": "fold increase in AUC and Cmax", "value": 2, "value_high": null, "value_low": null}`
  > Pazopanib | VEGFR/multikinase TKI | Meal ~doubles AUC and Cmax | Empty stomach: ≥1 h before/2 h after | Fasting avoids food-driven over-exposure; do not crush
  - as recorded (paraphrase): For the VEGFR multikinase agent a meal approximately doubles AUC and Cmax, so it must be taken on an empty stomach at least one hour before or two hours after food to avoid food-driven over-exposure.
  - in `src_doi_10.3390/pharmaceutics18091082` at `table` `table1`, section Tables; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_64c3162c78ff` sha256 `64c3162c78ff8248b4ddb814cfc8da5afef054668de428c3a5e16d89342eb328` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 675
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TYZ6B42DA4F3FDKYFB64B4** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Cabozantinib | Multikinase TKI | Food raises exposure | Empty stomach: ≥1 h before/2 h after | Strict fasting; tablets and capsules not interchangeable
  - as recorded (paraphrase): For one multikinase agent food raises exposure so strict fasting is required, and its tablet and capsule formulations are not interchangeable.
  - in `src_doi_10.3390/pharmaceutics18091082` at `table` `table1`, section Tables; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_8a1cd77e142f` sha256 `8a1cd77e142f59897c3b533015d14fc7246f7a3fbdca287358649ad7704ac30e` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 679
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`

*polarity `inconclusive`*

- **claim_01M4TYZ6CQD712197RSTQ470ZM** · `inconclusive` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > The food-effect studies from which these values derive differ in design—in study population (healthy volunteers or patients), dose, single-dose versus multiple-dose or steady-state conditions, the caloric and fat content of the test meal, the analyte measured (parent drug alone or parent plus active metabolite), and the pharmacokinetic endpoint reported. Descriptions such as “largest” or “most striking” in this review therefore rank magnitudes as they were reported in the respective studies and labels; they are not the output of a common experiment and should not be read as strictly comparable measurements
  - as recorded (paraphrase): Food-effect studies differ in population, dose, single-dose versus steady-state design, meal composition, analyte measured and endpoint reported, so the reported magnitudes are not strictly comparable across agents.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec5.p5`, section 5. Food Effects on Oral Anticancer Agents; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_4e5401f1e7d2` sha256 `4e5401f1e7d2a96380490e4b16e4768a0a9ebb59eed9d5089e948bba548f5753` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 684
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`

*polarity `supports`*

- **claim_01M4TYZ6A3VQZWM7VZKSQH0GQA** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Sunitinib | Multikinase TKI | No effect | With or without food | Flexible timing
  - as recorded (paraphrase): For one multikinase agent food has no effect on exposure and it may be taken with or without food.
  - in `src_doi_10.3390/pharmaceutics18091082` at `table` `table1`, section Tables; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_e042213bf0cd` sha256 `e042213bf0cd6f021c544b1e7bda06c8120bf0be2ccefa045d23d922825672ae` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 676
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`
- **claim_01M4TYZ6BQ0Y6RKJ767XG0921F** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% bioavailability", "unit_as_reported": "% bioavailability", "value": 98, "value_high": null, "value_low": null}`
  > Imatinib is conventionally taken with food and water to reduce gastrointestinal upset rather than to alter exposure (its bioavailability is 98% regardless of food)
  - as recorded (paraphrase): One oral agent has 98% bioavailability regardless of food and is taken with food only to reduce gastrointestinal upset.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec5.p3`, section 5. Food Effects on Oral Anticancer Agents; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_c13cf3533ff1` sha256 `c13cf3533ff1b7f15f43c81c99c53d42afd9bb655f00c41db0a5fc9c85515e8c` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 681
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review item `q_01M4VEGV60H22GEJRPPVSBWTRH` (`open`, blocking `True`, raised 2026-10-13T20:16:04.288Z): proposer and critic still disagree after one revision
  - inspection bundle: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "open_critic_findings": [{"check": "evidence_support", "finding": "The definition excludes a bioavailability-based figure, 'A ratio of fed to fasted absolute bioavailability is a different quantity on a different endpoint and is not admitted here', and the erlotinib claim has duly been dropped. This claim is the same kind of statement, 'its bioavailability is 98% regardless of food', and is retained; read as a 1.00 it would enter a bioavailability observation on the AUC axis the definition reserves.", "proposal_index": 9, "referent": "claim_01M4TYZ6BQ0Y6RKJ767XG0921F", "severity": "material", "verdict": "fail"}], "pool_criterion": "cri_01M4V1FPGN9YZDQHG93BJGSQZY"}`
- unresolved proposer/critic disputes: `q_01M4VEGV60H22GEJRPPVSBWTRH`
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `evidence_support` on claim_01M4TYZ6BQ0Y6RKJ767XG0921F · severity `material` · verdict `fail`: The definition excludes a bioavailability-based figure, 'A ratio of fed to fasted absolute bioavailability is a different quantity on a different endpoint and is not admitted here', and the erlotinib claim has duly been dropped. This claim is the same kind of statement, 'its bioavailability is 98% regardless of food', and is retained; read as a 1.00 it would enter a bioavailability observation on the AUC axis the definition reserves.

**Lineage and lifecycle**

- pool lineage `cri_01M4V1FPGN9YZDQHG93BJGSQZY` at version `7`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for oral_bioavailability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · unit 'fold change in AUC' with aggregation max pools claim_01M4TYZ69P208EDHPQQVAAAKYF (value 2, a doubling) with claim_01M4TY1R97AG7D77VHD3S4GYJR (value 20, a 20% increase). On one scale the 20% effect scores ten times worse than the doubling, inverting the ranking mechanically.; The definition scores 'absolute size ... in either direction', but lower_better on a signed fold change rewards food-driven UNDER-exposure. Nothing in the rule takes an absolute value.; The falsification test invokes a 
  - round `run_01M4V43E8GDH8GF8M633VTWDQJ` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The blocking finding is accepted and fixed at the scale. Pooling a doubling recorded as the number 2 with a 20 percent increase recorded as the number 20 made the smaller effect score ten times worse, inverting the ranking mechanically. The attribute now defines a single quantity, the fed-to-fasted exposure ratio expressed so that it is always at least 1, with percentage changes converted explicitly before entry: a 20 percent increase enters as 1.20 and a doubling as 2.0. The second material finding is fixed by the same construction, since taking the larger of the two ratios means a food-driven reduction in exposure is scored as a deviation of the same size as an equivalent increase, so under-exposure is no longer rewarded by a signed lower_better scale. The third finding is accepted and resolved by deleting the appeal to a non-cited warning from the falsification test rather than by adding a claim the item never cited; the test now states the comparability problem in its own terms.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The attribute is defined on 'fold change in systemic exposure (AUC)', but this cited claim reports absolute bioavailability rising 'from roughly 60% fasted toward 100% with food'. A bioavailability ratio and an AUC ratio are different quantities; entering the former on the AUC axis mixes endpoints, and no conversion rule for it is given.; claim_01M4TYZ6CQD712197RSTQ470ZM states directly that food-effect values 'are not the output of a common experiment and should not be read as strictly comparab
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The fed-versus-fasted absolute-bioavailability quote is dropped as a different endpoint that the exposure-ratio axis cannot carry, with no conversion invented for it. The non-comparability quote is now cited and implemented: each value carries its population, dose, dosing design, meal composition, analyte and endpoint, values from differing designs are not pooled, label-derived standard-meal values are preferred, and an unresolved disagreement is routed to a human.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The definition now states that 'A ratio of fed to fasted absolute bioavailability is a different quantity on a different endpoint and is not admitted here', yet this claim, which reports exactly that ('absolute bioavailability rises from roughly 60% fasted toward 100% with food'), remains in supporting_claim_ids. A claim the attribute excludes is still listed as supporting it.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The quote reporting a fed-versus-fasted change in absolute bioavailability is already absent from supporting_claim_ids, where the previous revision removed it; the finding rests on the rationale sentence that mentioned the removal, which read as though the quote were still in play. That sentence is replaced by a positive statement of the exclusion rule and of where such a figure belongs, so nothing in the proposal refers to a claim it does not cite.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `disputed` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 13. Fraction of a profiling panel inhibited outside the required target set

- **attribute** `attr_fraction-of-a-profiling-panel-inhibited-outside-the-required@v1` · **rule** `rule_fraction-of-a-profiling-panel-inhibited-outside-the-required@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_fraction-of-a-profiling-panel-inhibited-outside-the-required@v1"]`, rule `["rule_fraction-of-a-profiling-panel-inhibited-outside-the-required@v1"]`; supersedes —
- **record hashes**: attribute `0a9e390573f0b713ca221d0780949f18520938f3f2d81771926e9771400e2043`, rule `96d8c181e35e4c0deff006a3bc42c220103797ad0f5cd4b1dd063edf47e5dc08`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V183H4QEGQ349CT82KN1H0@v7"}` · dimension `target_coverage`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Fraction of a profiling panel inhibited outside the required target set · subject `[{}]` · unit `% of screened kinases` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "curated_measurement"]`; determination bases —
  - measurement identity `a5a5d54add6aeb8c897ee3d3ac76cb5a634bf759c1c32fc0053563f65ad3d865`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `a7dc958a5ac0d27124058b4a8d7988b0300a89dfff42c20e6ed4e449d78909fa`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> Of the kinases screened in a profiling panel, excluding the five required receptors, the percentage inhibited at or above the panel's own stated threshold (for example 50 percent inhibition at the screening concentration). A value is admitted where the source states the panel size and the inhibition threshold, both of which are recorded with it, since without a denominator and a threshold no percentage exists. The screening concentration and the composition of the panel are recorded whenever the source states them and their absence is recorded as a gap, because a fraction is weaker evidence without them. Expressing the result as a fraction of the panel rather than as a raw count makes panels of different size commensurable; it does not make panels of different composition or screening concentration commensurable, because a panel enriched for the compound's own kinase family inflates the fraction for that compound. Fractions from panels that differ in composition or concentration, or whose composition or concentration is unstated, are therefore not pooled, and a comparison between them that would decide the ranking is routed to a human rather than averaged. Lower is better.

- **unit** `% of screened kinases` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates that leave most of a large screened panel untouched rank above candidates with broad residual activity, and the ranking no longer depends on how many kinases each source happened to screen.
- **falsification test**: If the admitted panels differ in inhibition threshold, screening concentration or composition, the fractions are not comparable and the attribute must be restricted to a single panel convention or withdrawn. If only one candidate in the pool has a panel reported with all four qualifiers, the attribute ranks nothing and should be withdrawn at the merge stage.
- **rationale**: One cited quote both demonstrates the quantity and fixes its convention: an agent is reported as sparing most of the kinome, with only three kinases showing at least 50 percent inhibition in a 371-kinase screen. That example is why the quantity must be a fraction rather than a count: three hits in a 371-kinase screen would otherwise be indistinguishable from three hits in a twenty-kinase panel. It states a panel size and an inhibition threshold, which is what a percentage needs and what the definition requires of every admitted value; it does not state the screening concentration or the panel's composition, which is why those are recorded when given and recorded as a gap when not, rather than being made conditions of admission that this evidence cannot meet. The qualitative off-target descriptions previously cited can yield no percentage, since a phrase such as a limited number of undesired targets, or a list of inhibited kinases with per-kinase percentages but no denominator and no threshold, has no denominator at all. Nothing in the cited evidence states a permissible fraction, so the rule is an ordering with no cutoff, and because composition and concentration are often unstated the attribute cannot settle a close comparison on its own.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `86b753080381870d32d210c4f9f2e87adad388d7e7c85570c6ee5fd070ddcf58` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"kinase panel\" OR kinome OR \"profiled against\" OR \"screened against\") AND (\"percent inhibition\" OR \"% inhibition\" OR \"off-target\" OR selectivity)", "relevance_terms": ["kinase panel", "kinome", "percent inhibition", "off-target"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 1 cited claim(s), 1 carry `location.span_checked_against_source: true` and 1 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 1, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 1}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"supports": 1}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `supports`*

- **claim_01M4TXQQ0TQNSH090AG6QEDW7Z** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "fold selectivity (FGFR2/3 over FGFR1)", "unit_as_reported": "fold selectivity (FGFR2/3 over FGFR1)", "value": 140, "value_high": null, "value_low": null}`
  > CGT4859, another reversible FGFR2-focused agent, demonstrates roughly 140-fold selectivity for FGFR2/3 over FGFR1 and retains activity against a wide panel of FGFR2 resistance mutations while sparing most of the kinome (only FGFR2, FGFR3 and ROS showing ≥50% inhibition in a 371-kinase screen
  - as recorded (paraphrase): A reversible FGFR2-focused agent shows roughly 140-fold selectivity for FGFR2/3 over FGFR1 and spares most of the kinome, with only FGFR2, FGFR3 and ROS showing at least 50% inhibition in a 371-kinase screen.
  - in `src_doi_10.2147/dddt.s559328` at `paragraph` `sec3.5.p5`, section Clinical Efficacy & Safety / Other Novel Drugs; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_1290101d51e0` sha256 `1290101d51e0bd80f6408389cc61801398a43082c80eef9d1ff5bc669ac032e1` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 198
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) 371-kinase screen · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `falsification_test_evaluated` on falsification_test · severity `material` · verdict `fail`: The test still reads 'If only one candidate in the pool has a panel reported with all four qualifiers, the attribute ranks nothing', which belongs to the superseded four-qualifier admission rule. Under the new rule a value is admitted on two qualifiers, so the test's trigger no longer matches the attribute it tests.

**Lineage and lifecycle**

- pool lineage `cri_01M4V183H4QEGQ349CT82KN1H0` at version `7`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for target_coverage
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · 'count of kinases' aggregated by median across panels whose size the definition itself requires recording: a count from the 371-kinase screen in claim_01M4TXQQ0TQNSH090AG6QEDW7Z is not commensurable with one from a small panel.
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The material finding is accepted: a bare count of inhibited kinases cannot be pooled by median across panels of different size, since three hits in a 371-kinase screen and three in a small panel are not the same observation. The measured quantity is therefore changed from a count to the fraction of the screened panel that is inhibited at or above the panel's own stated threshold, expressed as a percentage, which is commensurable across panels and keeps the attribute's meaning exactly. The definition now requires the panel size and the inhibition threshold to be recorded with each value and admits only panels that report both, and the rationale states that values from panels using different inhibition thresholds remain only loosely comparable. Citations are unchanged, and the 371-kinase quote now serves as the worked example of a value this attribute can actually compute.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The quote gives per-kinase percentages ('CLK1 (61.85%), LCK (44.62%), MAP3K19 (43.35%), and Aurora B (42.71%)') but states neither the panel size nor the screening threshold, both of which the definition requires before a value is admitted; it therefore yields no admissible value.; Of the six cited claims only claim_01M4TXQQ0TQNSH090AG6QEDW7Z can produce a value. claim_01M4TY6CMDHEX119N8WY36JMGF ('only a limited number of undesired targets'), claim_01M4TY6CPYRG6P7ZZ33EWG5CK6 ('a limited number o
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · Citation narrowed to the one quote that can yield a value, a 371-kinase screen with three kinases at or above 50 percent inhibition; the qualitative target lists, including the per-kinase percentages with no panel denominator or threshold, are removed. The definition now requires the panel's composition to be stated and recorded alongside size, screening concentration and threshold, and forbids pooling fractions from panels of different composition, routing such a disagreement to a human instead.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The admission rule now requires four qualifiers, but the single supporting quote supplies only two: 'only FGFR2, FGFR3 and ROS showing >=50% inhibition in a 371-kinase screen' states the panel size and the threshold and states neither the screening concentration nor the panel composition. On the tightened rule the attribute's own and only cited value is inadmissible.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The admission rule is brought back to what the evidence can state: a value needs the panel size and the inhibition threshold, which the cited 371-kinase screen gives, while the screening concentration and panel composition are recorded when stated and recorded as a gap when not, instead of being conditions that made the attribute's only cited value inadmissible. Non-comparability is handled where it belongs: fractions from panels differing in composition or concentration, or with those unstated, are not pooled and a comparison that would decide the ranking is routed to a human.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 14. Hydrogen-bond donor count

- **attribute** `attr_hydrogen-bond-donor-count@v1` · **rule** `rule_hydrogen-bond-donor-count@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_hydrogen-bond-donor-count@v1"]`, rule `["rule_hydrogen-bond-donor-count@v1"]`; supersedes —
- **record hashes**: attribute `51d5a9acd0630375e356d4201840dee10f0a4d20cefa3651fb939bc7e1b2fd19`, rule `a3b9e381da6383a6877c896f3721069ad74ad5e54777a229e84b82f122f9a575`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1FPDRK9QKAFWRD1D4KZE2@v4"}` · dimension `oral_bioavailability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Hydrogen-bond donor count · subject `[{"property": "HBondDonorCount"}]` · unit `count` · `quantitative` · aggregated by `median` · transform —
  - read from `["property_estimate"]` asking `["computed_property"]`; evidence kinds `["database_entry"]`; determination bases —
  - measurement identity `70c89de71e30801dbe29cef2a857f66574d2ac49b69ed6ce8cbcc7815388938f`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `54eb080c82e147e21c6c6404801ef870e1598cfac186814e4351de55c112e055`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The number of hydrogen-bond donor groups in the molecule, taken as the computed descriptor for the neutral parent structure (the hydroxyl and amine hydrogens that the cited source names as the polar functional groups which increase solvation). Reported as an integer count. Fewer donors is scored as better, monotonically and with no threshold, because the cited claims support a direction of effect on membrane permeability but state no permissible number of donors. Two limits are part of the definition. The cited evidence describes a trade-off rather than a one-way preference: incorporating polar or ionisable groups improves aqueous solubility while raising polar surface area and reducing passive diffusion, so a monotone preference for fewer donors captures only one side of it, and this attribute is subordinate to the measured oral bioavailability attribute and must not outweigh it. And the value is a computed descriptor, a derived quantity rather than a measurement, so where a measured oral bioavailability exists for the same candidate the measurement governs and this attribute serves only to separate candidates that have none.

- **unit** `count` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["database_entry"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Among candidates of comparable size and lipophilicity, those carrying fewer hydroxyl and amine donors rank higher on expected passive absorption, which separates scaffolds whose polarity sits in acceptors from those carrying many donors. Because the rule is an ordering with no cutoff, no candidate is excluded on this attribute and a candidate with a high donor count but a measured high oral bioavailability is not demoted below one with a favourable descriptor and no measurement.
- **falsification test**: Compute donor count and topological polar surface area for every candidate in the pool and correlate them. If the two rank the pool identically, they are one measurement and this attribute should be merged into the polar-surface-area attribute at the merge stage. Independently, if candidate ordering by donor count inverts the ordering by measured absolute oral bioavailability, the descriptor is not tracking absorption for these molecules and the attribute should be withdrawn in favour of the measured value.
- **rationale**: The cited claims make donor count a determinant of absorption in its own right rather than a restatement of polar surface area: one states that lower polarity is associated with enhanced passive diffusion, evidenced by polar surface area below approximately 90 square angstroms together with a limited number of hydrogen-bonding interactions; a second states that an excess of polar functional groups, particularly hydroxyl and amine moieties, increases solvation and reduces membrane permeability; a third gives the design response, lowering polar surface area by bioisosteric capping; and a fourth lists hydrogen-bonding capacity alongside molecular weight and lipophilicity as the parameters whose modulation promotes oral bioavailability. Two limits follow from those same quotes and are recorded here rather than left implicit. The quoted threshold language is reported for central-nervous-system penetration, not for intestinal absorption, so it supports the direction of the effect but cannot license a numeric cutoff for this objective, which names no central-nervous-system compartment. And the value is a computed descriptor, a derived quantity rather than a measurement, so where a measured oral bioavailability exists for the same candidate the measurement governs and this attribute serves only to separate candidates that have none. A third consideration is now admitted here on the same terms as in the polar-surface-area attribute, since donor count and polar surface area express one polarity mechanism: the cited evidence states that incorporating polar or ionisable groups improves aqueous solubility while raising polar surface area and reducing passive diffusion, so fewer donors is not uniformly better, and the preference is weak and subordinate to measured absorption.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `0d6151ab7bff5bd8c679840e399b3de6e7dbd9bd1764be130a2d962ecceb6941` · 1 route(s) · literature-bound `False`
  - route `property_estimate` / `computed_property` · subject `{"property": "HBondDonorCount"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 5 cited claim(s), 5 carry `location.span_checked_against_source: true` and 5 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 1, `value_not_in_quote` 0, not recorded 4 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 5}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 1, "supports": 4}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TXF51XDDHCAZG3WWD6VE4T** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Conversely, the incorporation of polar or ionizable groups, including morpholine moieties or protonable amines, can improve aqueous solubility while increasing topological polar surface area, ultimately reducing passive diffusion across the BBB
  - as recorded (paraphrase): Adding polar or ionisable groups such as morpholine or protonable amines can improve aqueous solubility while increasing topological polar surface area and reducing passive diffusion.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.4.p5`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.4. Influence of Molecular Structure on Efflux Transporter Interaction (P-gp, BCRP); document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_6496739af194` sha256 `6496739af194ed4fb06f6c3d018d73c2a4226f93a02b07e21ce5fc9e25a016ad` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 150
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

*polarity `supports`*

- **claim_01M4TXF4RG4P3S9CV0926P5XV9** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "Å2 (TPSA)", "unit_as_reported": "Å2 (TPSA)", "value": 90, "value_high": null, "value_low": null}`
  > Lower polarity is generally associated with enhanced passive diffusion, as evidenced by TPSA values below approximately 90 Å2 and a limited number of hydrogen bonding interactions correlating with improved CNS penetration
  - as recorded (paraphrase): Lower polarity favours passive diffusion, with topological polar surface area values below roughly 90 square angstroms and a limited number of hydrogen-bonding interactions correlating with improved CNS penetration.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.2.p4`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.2. Critical Physicochemical Properties for Oral Bioavailability of KIs and Central Nervous System Penetration; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_af2faace3572` sha256 `af2faace3572b7f1c3bffd07e0df23babea745f460aafe017f3516bcd4a8f9ba` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 134
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXF4S4XVHCR3R6M8T3CTYJ** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Conversely, an excess of polar functional groups, particularly hydroxyl and amine moieties (OH, NH), increases solvation and reduces membrane permeability
  - as recorded (paraphrase): An excess of polar functional groups, especially hydroxyl and amine moieties, increases solvation and reduces membrane permeability.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.2.p4`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.2. Critical Physicochemical Properties for Oral Bioavailability of KIs and Central Nervous System Penetration; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_f633047e77b2` sha256 `f633047e77b24c1d409130db2bd23beee3323c978b7f4e8cabf1d705ed043277` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 135
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXF4YN56TQ7412JCAN5AZN** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > next-generation design must prioritize macrocyclization, structural rigidification, and bioisosteric capping to lower polar surface area and evade P-glycoprotein and BCRP efflux
  - as recorded (paraphrase): Next-generation design should prioritise macrocyclisation, structural rigidification and bioisosteric capping in order to lower polar surface area and evade P-glycoprotein and BCRP efflux.
  - in `src_doi_10.3390/ijms27156590` at `abstract` `abstract.p1`, section Abstract; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_834d3711fff3` sha256 `834d3711fff3df4841180bfc97fa810c1cf853c3e8d30713d5e3700cee1c42c9` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 144
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXF50Y236KPK5VTCY742X0** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > These hybrid designs also facilitate the modulation of key parameters such as molecular weight, lipophilicity, and hydrogen-bonding capacity, thereby promoting oral bioavailability while maintaining the potential for CNS exposure
  - as recorded (paraphrase): Hybrid fused-heterocycle designs allow modulation of molecular weight, lipophilicity and hydrogen-bonding capacity, promoting oral bioavailability while retaining potential CNS exposure.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.3.p6`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.3. Chemical Design of Oral Kinase Inhibitors; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_b903f85b4f99` sha256 `b903f85b4f99937958b8c32265525a8722dfa07e167371a2e34fb2a6f99d1cae` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 148
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `unit_applicability_consistency` on attribute.evidence_request.parameters.property · severity `minor` · verdict `fail`: The definition still equates the computed descriptor with 'the hydroxyl and amine hydrogens that the cited source names', while HBondDonorCount counts donors beyond OH and NH; the computed value remains broader than the groups the quote implicates.

**Lineage and lifecycle**

- pool lineage `cri_01M4V1FPDRK9QKAFWRD1D4KZE2` at version `4`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for oral_bioavailability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `distill` · `revise` → `candidate` · `distilled` · Kept in meaning but sharpened in three ways. First, the definition is made operational: the quantity is now named as the PubChem-computed count of hydrogen-bond donor groups, that is the hydroxyl and amine hydrogens the cited claim names, counted on the neutral parent structure, so two readers would compute the same number. Second, the direction and rule kind are justified rather than asserted: the cited claims support only a monotone 'fewer is better' association with permeability, not any numeric limit, so the rule stays a preference with predicate_form ordering and cutoff_basis none_evidence_insufficient; the one number among the cited claims, approximately 90 square angstroms, is a polar-surface-area figure and belongs to the separate polar-surface-area attribute, so it is not borrowed as a donor cutoff and no number is invented. Third, two honest limits that were implicit are now written into the rationale: the cited threshold language is reported for central-nervous-system penetration rather than for intestinal absorption, and the quantity is a derived computed descriptor rather than a measurement, so it must not outweigh a measured bioavailability value. The claim citations are unchanged.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Donor count and polar surface area are the same polarity mechanism, yet the solubility trade-off that proposal 11 cites to temper its preference (claim_01M4TXF51XDDHCAZG3WWD6VE4T) is neither cited nor acknowledged here, and no subordination to measured absorption is stated. The same evidence is admitted as a caveat in one proposal and omitted in the other.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The solubility-versus-permeability trade-off quote is now cited and acknowledged here on the same terms as in the polar-surface-area attribute, since the two attributes express one polarity mechanism, and the definition states the subordination to measured oral bioavailability explicitly rather than leaving it in the rationale.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `scoring` on `rules@v3`
- rule-set entry: `{"acceptable_value_sources": ["database_entry"], "attribute_ref": "attr_hydrogen-bond-donor-count@v1", "authority": "trigger_table", "confirmed_by": "auto:trigger_table", "cutoff_basis": "none_evidence_insufficient", "disputed": false, "on_states": ["unknown_no_penalty", "unknown_no_penalty", "route_to_human"], "rule_kind": "preference", "rule_ref": "rule_hydrogen-bond-donor-count@v1"}`
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: `{"assessed": 3177, "board": "lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4", "observed": 3084}`

---

### 15. Incidence of any-grade proteinuria

- **attribute** `attr_incidence-of-any-grade-proteinuria@v1` · **rule** `rule_incidence-of-any-grade-proteinuria@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_incidence-of-any-grade-proteinuria@v1"]`, rule `["rule_incidence-of-any-grade-proteinuria@v1"]`; supersedes —
- **record hashes**: attribute `65d848204ab74867553f94c4e90dc7acff82b56163d072e38160025a1bf25af9`, rule `2ce8c588b9fd66f7066a584a586311a192730316251cfa5a8e5467cc697e148a`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V222336CJA33WRFBG0195S@v6"}` · dimension `toxicological_safety`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Incidence of any-grade proteinuria · subject `[{}]` · unit `% of patients` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `b7a2e308dcf75633f4525f5c7fb229c197882ba03406357a4b7886fe48d357f7`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `34895313fec5d3df560212ea072d1b86bf0e743075dc427b382421ef4e9c0080`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The proportion of treated patients developing proteinuria of any grade, as a percentage, with the control-arm rate recorded where a randomised comparison reports one. The any-grade rate is the scored severity because it is the one the cited evidence resolves: the pooled any-grade difference is reported with a risk ratio and a confidence interval excluding unity, whereas the grade 3 or higher rate is reported as uncommon, not significantly different between groups, and with wide confidence intervals because of the low number of events. The grade 3 or higher rate is therefore recorded alongside every value, never entered, and never used to separate candidates. Reported renal pathology such as podocytopathy or thrombotic microangiopathy is a narrative finding rather than a percentage and is recorded rather than entered. Lower is better. Because the cited evidence associates renal dysfunction with inhibition of the required vascular receptor pathway, the rate counts against a candidate only where coverage of those receptors is comparable, and a low rate in a candidate whose coverage is weaker is routed to a human rather than credited.

- **unit** `% of patients` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates with lower any-grade proteinuria rates at comparable coverage of the required receptors rank above candidates in whom it is common, the severe-grade rate and the control-arm rate stay in the record, and no candidate is separated from another on severe-grade differences the cited evidence calls imprecise.
- **falsification test**: The claims record physiological proteinuria as a confounder of renal safety monitoring in some settings; if reported rates do not distinguish drug-induced from background proteinuria the attribute is biased and must be restricted to controlled comparisons.
- **rationale**: The cited quotes quantify this across the class and against controls: any-grade proteinuria in 27.30 percent of treated patients compared with 16.19 percent of control patients, a pooled risk ratio of 1.89 with a confidence interval of 1.30 to 2.74, and 18.7 percent proteinuria with 2.4 percent high-grade across trials of this inhibitor class. The second cited quote is why the scored severity is the any-grade rate rather than the severe one: it states that grade 3 or higher proteinuria was uncommon, did not differ significantly between treatment groups, and carries wide confidence intervals because of the low number of events, so an ordering built on those severe-grade differences would rank candidates on an effect the evidence does not resolve. The severe rate is kept in the record because it is what prompts dose modification in practice. The substantial control-arm rate is why the control value is recorded with each measurement, and no cited quote states an acceptable rate, so the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `d4becd72a7a891331218588807c342adbb371fd38edd8959a07c839e23dc0fe9` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (proteinuria OR \"renal toxicity\" OR nephrotic OR \"kidney injury\" OR creatinine) AND (incidence OR percent OR % OR grade)", "relevance_terms": ["proteinuria", "renal", "kidney", "incidence"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 2 cited claim(s), 2 carry `location.span_checked_against_source: true` and 2 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 1, `value_not_in_quote` 0, not recorded 1 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 2}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 1, "supports": 1}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4V09QHD46WZ4M5YPXT50GQN** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% any-grade proteinuria", "unit_as_reported": "% any-grade proteinuria", "value": 27.3, "value_high": null, "value_low": null}`
  > Any-grade proteinuria was also increased with fruquintinib. In the overall pooled cohort, any-grade proteinuria in GI cancers occurred in 27.30% of patients receiving fruquintinib compared with 16.19% of control patients, corresponding to a pooled risk ratio of 1.89 (95% CI 1.30–2.74; p = 0.0008). In GI cancer group, high-grade proteinuria occurred 1.85% vs. 0.53% (RR, 2.49; 95% CI: 0.86–7.16; p = 0.09).
  - as recorded (paraphrase): Any-grade proteinuria occurred in 27.30% of patients on the VEGFR1-3 inhibitor versus 16.19% of controls with a risk ratio of 1.89, while grade 3 or higher proteinuria occurred in 1.85% versus 0.53% without reaching significance.
  - in `src_doi_10.32604/or.2026.078524` at `paragraph` `sec3.5.p1`, section Results / Proteinuria; document `art_24d34d336ae8` sha256 `24d34d336ae8f45bdd1335abc021c757a77b737cd7c5efcbe87506e9a1b1338f`; claim `art_2dbcdd69ad23` sha256 `2dbcdd69ad233e98f53f3e4aa7569ec980d4687ca35095ec7e6d426430964d42` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1146
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

*polarity `supports`*

- **claim_01M4V09QHQ1MCSHX6KVNVGY6CG** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Grade ≥3 proteinuria was uncommon across trials and did not differ significantly between treatment groups. Confidence intervals were wide because of the low number of events, reflecting the limited precision of pooled estimates for this endpoint
  - as recorded (paraphrase): Grade 3 or higher proteinuria was uncommon and did not differ significantly between groups, with wide confidence intervals from low event numbers.
  - in `src_doi_10.32604/or.2026.078524` at `paragraph` `sec3.5.p3`, section Results / Proteinuria; document `art_24d34d336ae8` sha256 `24d34d336ae8f45bdd1335abc021c757a77b737cd7c5efcbe87506e9a1b1338f`; claim `art_7481c05246e1` sha256 `7481c05246e112b474773da52331eef429e707a9ff482ce0d91ad42636548bfd` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1147
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `falsification_test_evaluated` on falsification_test · severity `material` · verdict `fail`: The test still asserts 'The claims record physiological proteinuria as a confounder of renal safety monitoring in some settings'. Neither cited claim mentions physiological proteinuria; the nearest content is the 16.19 percent control-arm rate in claim_01M4V09QHD46WZ4M5YPXT50GQN, which is a trial comparator rather than a statement about physiological proteinuria.

**Lineage and lifecycle**

- pool lineage `cri_01M4V222336CJA33WRFBG0195S` at version `6`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for toxicological_safety
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The definition bundles any-grade proteinuria, grade >=3 proteinuria and 'any reported renal pathology' under a single '% of patients' unit and one ordering; claim_01M4V09QHD46WZ4M5YPXT50GQN alone carries 27.30 any-grade against 1.85 high-grade.; This cited quote states grade >=3 proteinuria 'did not differ significantly between treatment groups' with wide confidence intervals, so the endpoint does not separate drug from background. The rule nonetheless ranks candidates on it.; The quoted span is
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The definition puts three things on one '% of patients' axis: 'proteinuria, at any grade and at grade 3 or higher, together with any reported renal pathology'. In the cited source the two severity rates differ more than tenfold, 'any-grade proteinuria ... 27.30%' against 'high-grade proteinuria ... 1.85%' (claim_01M4V09QHD46WZ4M5YPXT50GQN), and renal pathology is not a percentage at all.; Only claim_01M4V09QHD46WZ4M5YPXT50GQN carries rates. claim_01M4TX995V8QY6XQ4R9BQWZSM6 is the two-word list '
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The axis now carries one quantity, the grade 3 or higher proteinuria rate, with the any-grade rate, the control-arm rate and any reported renal pathology recorded rather than entered. The four cited quotes that yield no percentage are dropped from the support, leaving the two that report rates, and the definition states that the rate is compared only between candidates of comparable coverage of the required receptors.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The only grade 3 or higher figures available are 'high-grade proteinuria occurred 1.85% vs. 0.53%' (claim_01M4V09QHD46WZ4M5YPXT50GQN), and this claim states that such rates were 'uncommon across trials and did not differ significantly between treatment groups' with wide confidence intervals 'because of the low number of events'. The scored axis is therefore an ordering over differences the cited evidence calls imprecise.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The scored severity moves to the any-grade rate, which is the one the cited evidence resolves with a risk ratio and a confidence interval excluding unity, while the grade 3 or higher rate, which the same evidence calls uncommon, not significantly different and imprecise because of few events, is recorded alongside and never used to separate candidates. Both cited quotes now support the scored axis.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 16. Incidence of central serous retinopathy

- **attribute** `attr_incidence-of-central-serous-retinopathy@v1` · **rule** `rule_incidence-of-central-serous-retinopathy@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_incidence-of-central-serous-retinopathy@v1"]`, rule `["rule_incidence-of-central-serous-retinopathy@v1"]`; supersedes —
- **record hashes**: attribute `b0cfec676a014c1573afb84adf6c3a6f9acfae5fdc700129739cfe89f43a286c`, rule `4df80908dcd2cf3bbcf14240bf5f89bf5d31d56c4cf2d3490053f46bd39faecf`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V222D146MVN9ZR3JCSF720@v6"}` · dimension `toxicological_safety`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Incidence of central serous retinopathy · subject `[{}]` · unit `% of patients` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `f8cfd4ed6ae5e960b676a285eaf8c7f8052b3fbd2a462888a307ad75c54da347`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `18538dde2a4b13fdf5992a1269ddc09f65d9a68653938aa899b72808d1e92c7d`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The proportion of treated patients developing central serous retinopathy, at any grade, as a percentage, reported for the compound itself. Two admission rules follow from the cited evidence. A rate is admitted only where the source reports it for a named molecule; a rate given for a drug class as a whole, such as a class table row of ocular event rates with no molecule named, is recorded as class context and is never entered as a candidate's value, which is why the two figures in the evidence, about 21 percent for a named agent in one indication and about 9 percent in a class table, are not two values for one axis. And every admitted value is recorded with the indication and the trial population it comes from; values from different indications are not pooled into one median, and where a candidate has values from more than one indication each is kept with its own label for a later stage to read. The grade 3 or higher rate is recorded alongside where a source reports one, and the severity entered is always the any-grade rate so that two severities never share the axis. The other ocular events in the evidence, retinal pigment epithelial detachment, retinal detachment, dry eye and cataract, are separate endpoints with their own rates and are recorded rather than entered. Whether baseline and periodic ophthalmological examination is mandated is a categorical requirement with no scale; it is recorded with the value as a monitoring burden for a human to weigh, and is not scored. Lower is better.

- **unit** `% of patients` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates with a lower central serous retinopathy incidence rank above candidates in whom it is common, with the other ocular event rates, the grade 3 figure and the ophthalmological monitoring mandate visible in the record rather than mixed into one percentage.
- **falsification test**: If ocular rates are drawn from a different indication or dose than the candidates would use they do not transfer; and because the claims describe this toxicity as reversible on discontinuation, severity should be weighted by reversibility rather than incidence alone.
- **rationale**: The cited quotes identify this as a distinctive toxicity of the fibroblast growth factor receptor arm of the required coverage and quantify it in two different forms. One reports central serous retinopathy in 21 percent of patients, 3 percent at grade 3, for a named agent in trials of one indication; the other is a class table row giving about 9 percent for central serous retinopathy alongside about 20 percent dry eye, 4 percent retinal detachment and 6 percent cataract, with no molecule named. Those two figures differ more than twofold, and the definition now explains why that is not a conflict on one axis: the first is a candidate value from a stated indication, the second is class context, and only the first kind is entered. Recording the indication with every admitted value keeps the remaining population difference visible instead of averaging it away. The class table is retained in the support because it is the evidence that the other ocular endpoints exist and carry their own rates, and because it states the baseline eye examination and the interruption rule that the monitoring annotation records. No cited quote states an acceptable rate, so the rule is an ordering with no cutoff, and because the cited evidence describes this toxicity as reversible on discontinuation, the recorded reversibility must be read with the incidence.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `648bb91dfd07b278b6ee46d825bc56e0c8001bce0ebc6afe94511ac4704f8374` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"central serous retinopathy\" OR \"retinal detachment\" OR \"retinal pigment\" OR \"ocular toxicity\" OR \"dry eye\" OR cataract OR ophthalmolog*)", "relevance_terms": ["central serous retinopathy", "retinal detachment", "ocular toxicity", "ophthalmological"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 2 cited claim(s), 2 carry `location.span_checked_against_source: true` and 2 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 2, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 2}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 2}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TXQQJM138ZGV1X2D1QW6NH** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% of patients", "unit_as_reported": "% of patients", "value": 21, "value_high": null, "value_low": null}`
  > In trials of urothelial carcinoma treated with erdafitinib, CSR was seen in 21% of patients (3% grade 3).
  - as recorded (paraphrase): In urothelial carcinoma trials of a pan-FGFR inhibitor, central serous retinopathy occurred in 21% of patients with 3% grade 3.
  - in `src_doi_10.2147/dddt.s559328` at `paragraph` `sec3.6.p5`, section Clinical Efficacy & Safety / Common Side Effects and Management; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_f06227c691ed` sha256 `f06227c691ed6aebcdedf664486ee6af8e4bbd669ea10ad730afd43509c87dc0` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 228
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) urothelial carcinoma trials · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXQQN8ZFQN9DB8RZ17CRHE** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% central serous retinopathy", "unit_as_reported": "% central serous retinopathy", "value": 9, "value_high": null, "value_low": null}`
  > Ocular AEs (dry eye, CSR, retinal detachment, cataract) | Dry eye ≈20; CSR ≈9; retinal detachment ≈4; cataract ≈6 | On-target retinal/ocular effects | Variable; may be insidious | Baseline eye examination for all patients; prompt ophthalmology review for visual symptoms; treatment interruption for ≥grade 3; restart at reduced dose only under specialist supervision
  - as recorded (paraphrase): Reported ocular adverse-event rates are about 20% dry eye, 9% central serous retinopathy, 4% retinal detachment and 6% cataract, treated as on-target retinal effects requiring baseline eye examination for all patients and interruption at grade 3 or above.
  - in `src_doi_10.2147/dddt.s559328` at `table` `table3`, section Tables; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_8727becabb0a` sha256 `8727becabb0a3a812db9f80bfd593b8348f929dd8fe6476a8100aac22f12d65a` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 233
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `falsification_test_evaluated` on falsification_test · severity `material` · verdict `fail`: The test still asserts that 'the claims describe this toxicity as reversible on discontinuation'. Neither cited claim says so; claim_01M4TXQQN8ZFQN9DB8RZ17CRHE states only 'treatment interruption for >= grade 3; restart at reduced dose only under specialist supervision', so the reversibility weighting the test proposes rests on a statement the evidence does not make.

**Lineage and lifecycle**

- pool lineage `cri_01M4V222D146MVN9ZR3JCSF720` at version `6`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for toxicological_safety
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Structured value 10 carries unit '% grade >=3' and refers to grade >=3 HYPERPHOSPHATAEMIA; this quote's ocular content is entirely qualitative. A phosphate rate would enter the ocular attribute as an ocular rate.; Five different endpoints are pooled on one '% of patients' scale - claim_01M4TXQQN8ZFQN9DB8RZ17CRHE gives dry eye ~20, CSR ~9, retinal detachment ~4 and cataract ~6 - and the definition adds a boolean ('whether baseline and periodic ophthalmological examination is mandated'). A median 
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Five separate event rates plus a monitoring mandate share one '% of patients' axis with direction lower_better, and 'lighter monitoring' has no scale at all: claim_01M4TXQQK4P73MY29GPGTRA1XW states only that 'Baseline ophthalmological evaluation is mandatory', which is a categorical requirement, not a quantity.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The axis now carries one event at one severity, the any-grade central serous retinopathy incidence, which is the severity both admissible quotes report. The four other ocular endpoints are recorded as separate rates, and the ophthalmological monitoring mandate, which has no scale, is recorded as a burden for a human rather than scored; the quote stating only that mandate is dropped from the support.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The two cited any-grade figures conflict by more than twofold, 'CSR was seen in 21% of patients (3% grade 3)' here against 'CSR approximately 9' in claim_01M4TXQQN8ZFQN9DB8RZ17CRHE, and they are not the same population: the 21% is specific to 'trials of urothelial carcinoma treated with erdafitinib' while the other is a class table. The indication qualifier appears only in the falsification test, not as an admission rule.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The two cited figures are no longer treated as two values on one axis: a rate is admitted only where the source reports it for a named molecule, so the class table row with no molecule named becomes class context, and the indication and trial population are now recorded with every admitted value as an admission rule rather than appearing only in the falsification test. Values from different indications are not pooled.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 17. Incidence of grade 3 or higher haemorrhage

- **attribute** `attr_incidence-of-grade-3-or-higher-haemorrhage@v1` · **rule** `rule_incidence-of-grade-3-or-higher-haemorrhage@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_incidence-of-grade-3-or-higher-haemorrhage@v1"]`, rule `["rule_incidence-of-grade-3-or-higher-haemorrhage@v1"]`; supersedes —
- **record hashes**: attribute `7866b73c579bb374c4e4f3bde2f995667f99bc3885770c83cbf9f2b6bbd753bd`, rule `a38d620470ae87718afe8456c992888ad1983bba89cc01739c095299f9cf820f`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V2224A3VFJ6ZZH0G36F859@v6"}` · dimension `toxicological_safety`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Incidence of grade 3 or higher haemorrhage · subject `[{}]` · unit `% of patients` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `e816b01b7efc4c0529f6c7e18bc8792217300fea8cf3688d4ed31a33cfd4a12b`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `context_only` (`exploratory_consideration`) · predicate form `qualitative_judgment` · direction `lower_better`
  - predicate: no executable predicate; the value is surfaced for a human judgement
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `68cbd1e1929135bdaa03e9d70eb71828fe3069adf264f00a603ce256949f368d`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose
  - gap: decision_semantics: direction `lower_better` is declared while predicate_form is `qualitative_judgment`, so no predicate enforces it

**Operational definition**

> The proportion of treated patients with a grade 3 or higher haemorrhagic event, as a percentage, recorded with the control-arm rate where a randomised comparison reports one and with the enrolment criteria of the trial that reported it. Only that endpoint at that severity is entered. Venous and arterial thromboembolic rates are a different endpoint at a different severity and are recorded alongside, because a median across bleeding and clotting rates has no interpretation even though the cited evidence treats them as competing consequences of one mechanism. The cited evidence states that absolute rates were low and that the pooled estimate did not demonstrate a statistically significant increase, so the measured rate is recorded and weighed as a judgement rather than used to order the pool: a difference of a point or two between candidates on this endpoint is not a resolved difference in liability, and the rule therefore carries no monotone ordering and no cutoff. What the human sees is the rate, the control-arm rate, the enrolment criteria and the thromboembolic rates beside them, with a candidate reporting a clearly elevated rate surfaced for the recommendation decision.

- **unit** `% of patients` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: The measured severe bleeding rate is surfaced for every candidate with its control-arm rate, enrolment criteria and the thromboembolic rates beside it, so a clearly elevated bleeding signal reaches the recommendation decision while candidates separated by a percentage point on an estimate the evidence calls non-significant are not ordered against each other.
- **falsification test**: The claims state that thromboembolism estimates are imprecise because of sparse events and wide confidence intervals; if the retrieved event counts are in single figures the attribute must not be allowed to drive exclusion.
- **rationale**: The cited quotes quantify this endpoint and are explicit about its uncertainty: grade 3 or higher haemorrhage in 2.30 percent of treated patients, 26 of 1131, against 1.35 percent of controls, 10 of 741, and a pooled estimate that did not demonstrate a statistically significant increase. An ordering over that difference would rank candidates on an effect the evidence does not resolve, which is why the rule is a consideration weighed by a human rather than a preference ordering the pool. Mechanistically the quotes state that long-term weakening of vessel walls can lead to thrombosis and haemorrhage and that post-marketing experience includes severe and fatal bleeding events, so the endpoint follows from the required coverage and is worth surfacing even where the pooled estimate is imprecise. The thromboembolic rates in the same evidence are recorded rather than scored, and no cited quote states an acceptable rate, so there is no cutoff.

**Rule**

- **kind** `exploratory_consideration` · **predicate form** `qualitative_judgment` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `518bd62caf95067d5a5fc3ad4b6762d0922c6a3afc16952ce72ce7ce64154705` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (h?emorrhage OR bleeding OR \"venous thromboembolism\" OR thrombosis OR \"arterial thromboembolic\") AND (grade OR incidence OR percent OR % OR \"risk ratio\")", "relevance_terms": ["hemorrhage", "bleeding", "thromboembolism", "thrombosis", "grade 3"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 4 cited claim(s), 4 carry `location.span_checked_against_source: true` and 4 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 1, `value_not_in_quote` 0, not recorded 3 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 4}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 2, "supports": 2}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TX9941P0HK8NQZWV2G9D49** · `conflicts` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Because VEGF is vital to endothelial cell survival, anti-VEGF therapy can diminish the integrity and regenerative capacity of endothelial cells, causing pro-coagulant changes. The long-term weakening and diminished integrity of blood vessel walls can eventually lead to thrombosis and hemorrhage.
  - as recorded (paraphrase): Anti-VEGF therapy can reduce endothelial cell integrity and regenerative capacity, producing pro-coagulant changes, and long-term weakening of vessel walls can lead to thrombosis and haemorrhage.
  - in `src_nbk_NBK563322` at `paragraph` `article-109800.s5.p3`, section Adverse Effects; document `art_f39aa2170bbb` sha256 `f39aa2170bbb6e797aa143c217673d26d91bf5238802cedbd23bc4621ce110fc`; claim `art_1f5dfdef4d49` sha256 `1f5dfdef4d492378b7f34c9041d0f733777675a33d5aa40c86d7dde5d8567415` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 80
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) patients on long-term anti-VEGF therapy · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TY1RSARR5MJT5F4AV9JZJC** · `conflicts` · evidence `reference_text` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > In several clinical trials, nintedanib was also found to be associated with an increased risk of bleeding, likely secondary to VEGFR inhibition. Although severe bleeding and arterial thromboembolic events such as myocardial infarction (MI) and stroke were rare, bleeding events with severe and fatal outcomes have been reported in the post-marketing surveillance of the drug
  - as recorded (paraphrase): The agent was associated with increased bleeding risk in several clinical trials, likely secondary to VEGFR inhibition, and although severe bleeding and arterial thromboembolic events were rare, severe and fatal bleeding events have been reported post-marketing.
  - in `src_nbk_NBK585049` at `paragraph` `article-143222.s5.p4`, section Adverse Effects; document `art_d6f5f137dcb6` sha256 `d6f5f137dcb662288deb6e65d17790449f04dce1f0a228cee80848efe41da003`; claim `art_60f3784638b2` sha256 `60f3784638b22a98a96d9cc282316fb0c8091ec1cdfe097acdb17f0baa1abdc4` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 374
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

*polarity `supports`*

- **claim_01M4V09QJ1DDEMMY607KC6RJN5** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% grade >=3 haemorrhage", "unit_as_reported": "% grade >=3 haemorrhage", "value": 2.3, "value_high": null, "value_low": null}`
  > Grade ≥3 hemorrhage occurred in 2.30% (26/1131) of patients receiving fruquintinib compared with 1.35% (10/741) of control patients. The pooled risk ratio for grade ≥3 hemorrhage was 1.82 (95% CI 0.92–3.61; p = 0.09), indicating a numerical increase that did not reach statistical significance.
  - as recorded (paraphrase): Grade 3 or higher haemorrhage occurred in 2.30% of patients on the VEGFR1-3 inhibitor versus 1.35% of controls, a risk ratio of 1.82 that did not reach statistical significance.
  - in `src_doi_10.32604/or.2026.078524` at `paragraph` `sec3.4.1.p1`, section Results / Clinically Actionable Grade 3 or Higher Toxicities / Hemorrhage; document `art_24d34d336ae8` sha256 `24d34d336ae8f45bdd1335abc021c757a77b737cd7c5efcbe87506e9a1b1338f`; claim `art_8a7623d5e4c6` sha256 `8a7623d5e4c6c97e44277fbc8c7bb10d035f2575b2cfb1ee276f1ebfd2ce0b0d` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1148
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4V09QJAWQ938PF0PETJJ889** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > These findings indicate that although hemorrhagic events occurred during VEGFR inhibition, absolute rates were low and the pooled estimate did not demonstrate a statistically significant increase in grade ≥3 hemorrhage across the randomized trials.
  - as recorded (paraphrase): Haemorrhagic events occurred during VEGFR inhibition but absolute rates were low and the pooled estimate showed no statistically significant increase in severe haemorrhage.
  - in `src_doi_10.32604/or.2026.078524` at `paragraph` `sec3.4.1.p2`, section Results / Clinically Actionable Grade 3 or Higher Toxicities / Hemorrhage; document `art_24d34d336ae8` sha256 `24d34d336ae8f45bdd1335abc021c757a77b737cd7c5efcbe87506e9a1b1338f`; claim `art_b620e07246c4` sha256 `b620e07246c45f4cb1dd27ed0a6a3c125e3b2cf36a2060b54bc1967f43213e10` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1149
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage `cri_01M4V2224A3VFJ6ZZH0G36F859` at version `6`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for toxicological_safety
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Two distinct endpoints share one '% of patients' unit and one median: claim_01M4V09QJ1DDEMMY607KC6RJN5 gives 2.30 for grade >=3 haemorrhage while claim_01M4V09QJVJYEDZKWF82AV0GX4 gives 2.74 for ANY-GRADE venous thromboembolism. A median across them is a rate of nothing.; claim_01M4V09QJAWQ938PF0PETJJ889 and the non-significant ratios in claim_01M4V09QJ1DDEMMY607KC6RJN5 (p=0.09) and claim_01M4V09QJVJYEDZKWF82AV0GX4 (p=0.63) show neither endpoint separates drug from control. The test only bars thi
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Two endpoints at two severity grades share one '% of patients' axis: 'Grade >= 3 hemorrhage occurred in 2.30%' (claim_01M4V09QJ1DDEMMY607KC6RJN5) and 'any-grade VTE occurred in 2.74% ... Grade >= 3 VTE ... 1.67%' (claim_01M4V09QJVJYEDZKWF82AV0GX4). A median across bleeding and clotting rates has no interpretation, even though the shared mechanism is supported by claim_01M4TX9941P0HK8NQZWV2G9D49.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The axis now carries one endpoint at one severity, the grade 3 or higher haemorrhage rate. The thromboembolic rates, which sit at a different endpoint and severity, are recorded alongside with their cited non-significance rather than pooled into the same median, and the two quotes that report only those rates are dropped from the support.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The single admissible value is 'Grade >= 3 hemorrhage occurred in 2.30% (26/1131) ... compared with 1.35% (10/741)', and claim_01M4V09QJAWQ938PF0PETJJ889 states the pooled estimate 'did not demonstrate a statistically significant increase'. An ordering built on that difference ranks candidates on an effect the cited evidence does not resolve, and the population qualifier formerly supplied by the active-bleeding exclusion criterion is no longer carried in the claim list.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · Because the cited evidence states that absolute rates were low and the pooled estimate did not demonstrate a statistically significant increase, the attribute no longer orders the pool on that difference: it becomes an exploratory consideration with predicate_form qualitative_judgment and no cutoff, surfacing the rate with its control-arm rate, the trial's enrolment criteria and the thromboembolic rates for a human. The enrolment-criteria qualifier is now carried in the definition rather than only in the earlier rationale.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 18. Incidence of grade 3 or higher hand-foot skin reaction

- **attribute** `attr_incidence-of-grade-3-or-higher-hand-foot-skin-reaction@v1` · **rule** `rule_incidence-of-grade-3-or-higher-hand-foot-skin-reaction@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_incidence-of-grade-3-or-higher-hand-foot-skin-reaction@v1"]`, rule `["rule_incidence-of-grade-3-or-higher-hand-foot-skin-reaction@v1"]`; supersedes —
- **record hashes**: attribute `6b16806e16660b59c6a1047bb6efef717d32514aeeb7946ee80c393d9543eb05`, rule `e8e423be31b4906c7f22144c59d092d42fb8a0bc365f78cd78d6848af01c1388`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V2223QHZ4VFTKRHXG0W8W1@v4"}` · dimension `toxicological_safety`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Incidence of grade 3 or higher hand-foot skin reaction · subject `[{}]` · unit `% of patients` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `2e8b1799df60c68702c804945e8976469a41b0467e8420695c35776db666d936`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `6372b8d7a88b10a65755ec80c3f4dc0b0d0c7ba7dfdc8556b4aca9934a0d05f6`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The proportion of treated patients developing grade 3 or higher hand-foot skin reaction or palmar-plantar erythrodysaesthesia, as a percentage. Only that single-event, single-severity rate is entered. An any-grade rate, a rate combining this event with another such as oral mucositis, and a dose-modification fraction are each a different quantity and are recorded alongside rather than entered, because incidence, severity grade and modification rate are not interchangeable on one axis. The control-arm rate is recorded where a randomised comparison reports one, and the cited evidence notes that control-arm rates are sometimes zero, which makes relative risks unstable, so the absolute incidence governs. Lower is better.

- **unit** `% of patients` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates with low severe hand-foot skin reaction incidence rank above candidates in whom it is common, with any-grade rates, combined-event rates and dose-modification fractions visible in the record rather than averaged into the score.
- **falsification test**: If any-grade and grade 3 rates are conflated across sources the ordering is unsafe; and because control-arm rates are sometimes zero, relative risks here are unstable and the absolute incidence must govern.
- **rationale**: The cited quotes make this a principal signal of the class and quantify it at one severity: grade 3 or higher hand-foot skin reaction or palmar-plantar erythrodysaesthesia in 8.50 percent of treated patients against zero percent of controls, with a pooled risk ratio of 26.00, any-grade 27.93 against 3.64 percent and zero between-study heterogeneity, and about 10 percent grade 3 or higher for a second-line agent. Because the control arm is zero in that pooled analysis the relative risk is unstable, which is why the absolute grade 3 or higher incidence is the scored quantity and the any-grade rate is recorded. Two quotes previously cited have been removed from the support: one reports an any-grade rate of approximately 20 to 35 percent for this event combined with oral mucositis, and one a 2 to 3 percent dose-modification fraction for nail toxicity; neither is this event's severe-grade incidence and neither can share the axis with it. No cited quote states an acceptable rate, so the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `7b03001d83ef106c00c122c305f81a27b65e3fb9f18b0c2fc7c01aa923258560` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"hand-foot\" OR \"palmar-plantar\" OR \"hand foot skin reaction\" OR rash OR \"nail changes\" OR paronychia) AND (grade OR incidence OR percent OR %)", "relevance_terms": ["hand-foot", "palmar-plantar", "rash", "nail", "grade 3"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 3 cited claim(s), 3 carry `location.span_checked_against_source: true` and 3 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 3, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 3}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 3}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4V09QGJZ7EBB4XT0Z4T4YYN** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% grade >=3 HFSR/PPE", "unit_as_reported": "% grade >=3 HFSR/PPE", "value": 8.5, "value_high": null, "value_low": null}`
  > The incidence of any-grade HFSR or PPE in GI cancers was higher in the fruquintinib group compared to the placebo group, 27.93% (316/1131) vs. 3.64% (27/741) (RR, 7.64; 95% CI: 4.08–14.33; p < 0.00001). In the overall pooled cohort, grade ≥3 hand–foot skin reaction or palmar–plantar erythrodysesthesia (HFSR/PPE) occurred in 8.50% (97/1131) of patients receiving fruquintinib and 0% (0/741) of control patients, corresponding to a pooled risk ratio of 26.00 (95% CI 6.42–105.29; p < 0.00001)
  - as recorded (paraphrase): Any-grade hand-foot skin reaction or palmar-plantar erythrodysesthesia occurred in 27.93% versus 3.64% of controls, and grade 3 or higher in 8.50% versus 0%, a pooled risk ratio of 26.00.
  - in `src_doi_10.32604/or.2026.078524` at `paragraph` `sec3.4.3.p1`, section Results / Clinically Actionable Grade 3 or Higher Toxicities / Hand-Foot Skin Reaction and Palmar Plantar Erythrodysesthesia; document `art_24d34d336ae8` sha256 `24d34d336ae8f45bdd1335abc021c757a77b737cd7c5efcbe87506e9a1b1338f`; claim `art_3cabc1ac9807` sha256 `3cabc1ac9807fe3c90754814bfa5859f056941abee7f4865766131db9364b282` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1143
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4V09QH4VGKGEJEP3NBQEACM** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% grade >=3 HFSR/PPE", "unit_as_reported": "% grade >=3 HFSR/PPE", "value": 8.45, "value_high": null, "value_low": null}`
  > Grade ≥3 HFSR/PPE occurred in 8.45% of patients receiving fruquintinib and 0% of control patients, corresponding to a pooled risk ratio of 19.34 (95% CI 3.84–97.36; p = 0.0003). Between-study heterogeneity was minimal across analyses (I2 = 0%), indicating consistent dermatologic toxicity signals across trials
  - as recorded (paraphrase): In the colorectal subgroup grade 3 or higher dermatologic toxicity occurred in 8.45% versus 0% of controls with minimal between-study heterogeneity, indicating a consistent signal.
  - in `src_doi_10.32604/or.2026.078524` at `paragraph` `sec3.4.3.p2`, section Results / Clinically Actionable Grade 3 or Higher Toxicities / Hand-Foot Skin Reaction and Palmar Plantar Erythrodysesthesia; document `art_24d34d336ae8` sha256 `24d34d336ae8f45bdd1335abc021c757a77b737cd7c5efcbe87506e9a1b1338f`; claim `art_597307316e12` sha256 `597307316e12257770d4417e9954c91058ff5255d23a3cc513b3088054fe4e3d` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1145
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4V0DJ5P94K5SJS1BJ5TTVZ1** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% treatment-related grade >=3 events", "unit_as_reported": "% treatment-related grade >=3 events", "value": 57, "value_high": null, "value_low": null}`
  > Hand–foot skin reaction (Grade ≥ 3 in approximately 10%); diarrhea (most common any grade AE); hypertension (Grade ≥ 3 in 12%); fatigue (Grade ≥ 3 in 9%); decreased appetite, overlap with residual toxicities carried over from previous VEGFR‐TKI compounds, and having an impact on day‐to‐day life | Continuous oral daily dosing; vigilant surveillance for carry‐over and cumulative class toxicities; dose modifications common; treatment‐related Grade ≥ 3 events approximately 57% in updated COSMIC‐311 analysis
  - as recorded (paraphrase): For the second-line multitarget agent, grade 3 or higher hand-foot skin reaction occurred in about 10%, hypertension in 12% and fatigue in 9%, with treatment-related grade 3 or higher events in approximately 57% overall and common dose modification.
  - in `src_doi_10.1002/cai2.70078` at `table` `table3`, section Tables; document `art_e6a50d504115` sha256 `e6a50d50411565dcb2beef0b6cd9f260fa01b5e5e7bdb0087cd27cb8c4a85b97`; claim `art_daf9b289c54d` sha256 `daf9b289c54da2bd8670a7ae3709d18fc93342f72bf060d60709ac1bb3fe8132` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1179
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `candidate_symmetric_scrutiny` on attribute.aggregation · severity `minor` · verdict `fail`: claim_01M4V09QGJZ7EBB4XT0Z4T4YYN (8.50%) and claim_01M4V09QH4VGKGEJEP3NBQEACM (8.45%) report the same pooled analysis with different risk ratios, 26.00 and 19.34; a median over both weights one dataset twice.

**Lineage and lifecycle**

- pool lineage `cri_01M4V2223QHZ4VFTKRHXG0W8W1` at version `4`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for toxicological_safety
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Structured value 57 carries unit '% treatment-related grade >=3 events' - the composite all-toxicity rate. The quote's dermatologic figure is 'Grade >= 3 in approximately 10%', so the composite enters a dermatologic attribute at roughly six times the right value.; Value 64.3 is a dose-reduction rate, not a dermatologic incidence. This same claim is cited as a value by proposal[6], proposal[7] and proposal[10], each time standing for a different quantity.; The 2-3% range is the proportion requiri
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Three different quantities would enter one median: grade 3 or higher incidence (8.50%), an any-grade combined rate for two events ('Stomatitis/oral mucositis and palmar-plantar erythrodysaesthesia are also common (approximately 20-35%)', claim_01M4TXQQDXS79CKRMZRWZJ87K8), and a dose-modification fraction ('Hardly 2-3% of patients require dose reduction or interruption because of nail toxicities', claim_01M4TXQQM8A7E3MBAJKG2ZPVDX). Incidence, severity grade and modification rate are not interchan
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The axis now carries one event at one severity, the grade 3 or higher hand-foot skin reaction incidence; any-grade rates, rates combining this event with another, and dose-modification fractions are recorded rather than entered, and the two quotes carrying only those other quantities are dropped from the support. The absolute incidence governs because one cited control-arm rate is zero, which makes the relative risk unstable.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 19. Incidence of grade 3 or higher hypertension

- **attribute** `attr_incidence-of-grade-3-or-higher-hypertension@v1` · **rule** `rule_incidence-of-grade-3-or-higher-hypertension@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_incidence-of-grade-3-or-higher-hypertension@v1"]`, rule `["rule_incidence-of-grade-3-or-higher-hypertension@v1"]`; supersedes —
- **record hashes**: attribute `c87c26255559c500dbbcc1ef9337f5d85c78eb72438d7474a2e433d3c999cbd7`, rule `8b86c6164e5ed3750706a1c4e0d7f34baf327563cfc209ae0a114e0fc4c7372d`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V2222DE6V3RQZT3P0DY3W6@v5"}` · dimension `toxicological_safety`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Incidence of grade 3 or higher hypertension · subject `[{}]` · unit `% of patients` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `d2ce2accce0d829ddd6624a0b0fde35f79bf5adcf4b27d0f4163ba4b93739be4`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `context_only` (`exploratory_consideration`) · predicate form `qualitative_judgment` · direction `lower_better`
  - predicate: no executable predicate; the value is surfaced for a human judgement
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `c2149c73aebd57fbc5c901b11f0dbcca9011d3f261ce491c719995fb617dff2b`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose
  - gap: decision_semantics: direction `lower_better` is declared while predicate_form is `qualitative_judgment`, so no predicate enforces it

**Operational definition**

> The proportion of treated patients developing grade 3 or higher hypertension, as a percentage. Only the grade 3 or higher rate is entered; an any-grade rate is a different quantity, differing from it by around a factor of three in the same source, and is recorded alongside rather than entered, as is the control-arm rate where a randomised comparison reports one. This is the index on-target vascular toxicity of inhibiting the required vascular receptors, and the cited evidence states that their pharmacologic inhibition predictably produces a characteristic spectrum of toxicities. The measured rate is therefore recorded and weighed as a judgement against the candidate's coverage of those receptors rather than ordering the pool: a lower rate counts in a candidate's favour only where its coverage of the required vascular receptors is comparable, a low rate in a candidate whose coverage is weaker is routed to a human, and the attribute never ranks a candidate downward for an anticipated consequence of the coverage the objective requires. Because the judgement is on the rate together with the coverage, the rule carries no monotone ordering over the pool and no cutoff; the percentage, its severity grade, the control-arm rate and the candidate's coverage are what the human sees.

- **unit** `% of patients` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: The measured severe hypertension rate is surfaced for every candidate alongside its coverage of the required vascular receptors, so a human can see where a low rate reflects tolerability and where it reflects weaker engagement, and no candidate is ranked downward for an anticipated consequence of the coverage the objective requires.
- **falsification test**: Because hypertension is on-target, a candidate with no hypertension signal may simply not be engaging the vascular receptors; a zero rate must be cross-checked against the coverage criteria rather than rewarded on its own.
- **rationale**: This is the most consistently quantified toxicity in the claim set and the one most tightly bound to the required targets. A meta-analysis of randomised trials of a selective inhibitor of the three required vascular receptors found any-grade hypertension in 34.92 percent versus 7.55 percent of controls and grade 3 or higher in 13.96 percent versus 1.21 percent, a risk ratio of 9.01, with zero between-study heterogeneity; in one disease subgroup the figures rose to 43.02 and 17.28 percent. Other agents of the class show 24.8 percent grade 3 to 4, 13.6 percent, 12 percent and 12.9 percent. The mechanism is stated too: the receptor pathway is required for adequate nitric oxide production, so its inhibition raises systemic vascular resistance, which makes this toxicity inseparable from the required coverage rather than an avoidable off-target effect. Because the cited evidence ties this toxicity mechanistically to inhibition of the required receptor pathway and calls the resulting toxicity spectrum predictable, a monotone preference on it would reward weaker engagement of a required target. The rule is therefore an exploratory consideration: the measured rate is surfaced for a human to weigh against the coverage criteria, and the definition states that it discriminates only between candidates of comparable coverage. Only the grade 3 or higher rate is entered, because the same source reports an any-grade rate three times larger and the median would otherwise be taken over two severities.

**Rule**

- **kind** `exploratory_consideration` · **predicate form** `qualitative_judgment` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `2e21bcc4505b6b5639b46f9316e85a09b4ee79c0e7be0912c917d010fbd79d7d` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (hypertension OR \"blood pressure\") AND (\"grade 3\" OR \"grade ≥3\" OR incidence OR percent OR %)", "relevance_terms": ["hypertension", "grade 3", "incidence", "blood pressure"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 7 cited claim(s), 7 carry `location.span_checked_against_source: true` and 7 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 4, `value_not_in_quote` 0, not recorded 3 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 7}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 6, "supports": 1}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TX9937CKPPPM3WZGXCM35C** · `conflicts` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Due to VEGF’s role in blood vessel survival and plasticity, TKIs that inhibit VEGFR carry associations with several cardiovascular toxicities, particularly hypertension.
  - as recorded (paraphrase): Tyrosine kinase inhibitors that inhibit VEGFR are associated with several cardiovascular toxicities, hypertension in particular, because of the role of VEGF in blood-vessel survival and plasticity.
  - in `src_nbk_NBK563322` at `paragraph` `article-109800.s5.p3`, section Adverse Effects; document `art_f39aa2170bbb` sha256 `f39aa2170bbb6e797aa143c217673d26d91bf5238802cedbd23bc4621ce110fc`; claim `art_fef6c7337b4f` sha256 `fef6c7337b4f1ab7ce67fd5149d733def0f27e39cf783b86f51873c142c8b769` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 78
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) patients treated with VEGFR-inhibiting TKIs · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TX993KPQ0C6WAYA349FH79** · `conflicts` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > This toxicity is likely because VEGF is necessary for adequate nitric oxide production. Inhibition of VEGF, therefore, results in elevated systemic vascular resistance.
  - as recorded (paraphrase): Hypertension on VEGF inhibition is attributed to VEGF being required for adequate nitric oxide production, so inhibition raises systemic vascular resistance.
  - in `src_nbk_NBK563322` at `paragraph` `article-109800.s5.p3`, section Adverse Effects; document `art_f39aa2170bbb` sha256 `f39aa2170bbb6e797aa143c217673d26d91bf5238802cedbd23bc4621ce110fc`; claim `art_a540e08e56cc` sha256 `a540e08e56cce83a3d468d6044a79a43bf182481f92c79d343c0c29f6736e45f` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 79
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXQQRNXEWJEGS3GDDC1CNP** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% grade 3-4 hypertension", "unit_as_reported": "% grade 3-4 hypertension", "value": 24.8, "value_high": null, "value_low": null}`
  > The most frequent grade 3–4 events occurring in ≥5% of patients were hypertension (24.8%), stomatitis (7.3%), palmar–plantar erythrodysaesthesia (7.3%) and diarrhoea (5.5%)
  - as recorded (paraphrase): The most frequent grade 3-4 events in at least 5% of patients given the multikinase FGFR/VEGFR/CSF1R inhibitor were hypertension at 24.8%, stomatitis 7.3%, palmar-plantar erythrodysaesthesia 7.3% and diarrhoea 5.5%.
  - in `src_doi_10.2147/dddt.s559328` at `paragraph` `sec3.5.p4`, section Clinical Efficacy & Safety / Other Novel Drugs; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_e8bbd7380075` sha256 `e8bbd7380075cf6747fd823cfbaff987a640426de5fe263f3c9502b536c98bb7` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 240
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) pooled cohort of 109 CCA patients · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4V09QEKMZED9SNCXRRKXK89** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > VEGFR signaling also plays key roles in normal vascular, renal, and epithelial homeostasis, pharmacologic inhibition predictably results in a characteristic spectrum of treatment-related toxicities.
  - as recorded (paraphrase): Because VEGFR signalling also serves normal vascular, renal and epithelial homeostasis, pharmacological inhibition predictably produces a characteristic spectrum of treatment-related toxicities.
  - in `src_doi_10.32604/or.2026.078524` at `paragraph` `sec1.p2`, section Introduction; document `art_24d34d336ae8` sha256 `24d34d336ae8f45bdd1335abc021c757a77b737cd7c5efcbe87506e9a1b1338f`; claim `art_2c0aab043d01` sha256 `2c0aab043d0158e812531d4e4ea41121df85a3f4998708a3892ade985d546e48` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1137
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`
- **claim_01M4V09QFMZ820S46XHCGDWHTF** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% grade >=3 hypertension", "unit_as_reported": "% grade >=3 hypertension", "value": 13.96, "value_high": null, "value_low": null}`
  > The incidence of any-grade HTN was higher in the fruquintinib group, 34.92% vs. 7.55% (RR 3.96; 95% CI: 3.05–5.13; p < 0.00001). The rate of high-grade HTN was 13.96% vs. 1.21% (RR 9.01; 95% CI: 4.67–17.40; p < 0.00001).
  - as recorded (paraphrase): Any-grade hypertension occurred in 34.92% of patients on the VEGFR1-3 inhibitor versus 7.55% of controls with a risk ratio of 3.96, and grade 3 or higher hypertension in 13.96% versus 1.21% with a risk ratio of 9.01.
  - in `src_doi_10.32604/or.2026.078524` at `paragraph` `sec3.4.2.p1`, section Results / Clinically Actionable Grade 3 or Higher Toxicities / Hypertension; document `art_24d34d336ae8` sha256 `24d34d336ae8f45bdd1335abc021c757a77b737cd7c5efcbe87506e9a1b1338f`; claim `art_1ca9ecd661b9` sha256 `1ca9ecd661b9726d256d31255b06dd0eae8c3a0670dd8616bd822b98188421e5` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1140
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) pooled randomised trials in gastrointestinal malignancies, n = 1872 · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4V09QFY04X5EZ3SCHCZ068N** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% any-grade hypertension", "unit_as_reported": "% any-grade hypertension", "value": 43.02, "value_high": null, "value_low": null}`
  > In the metastatic colorectal cancer subgroup, incidence of any-grade HTN was 43.02% vs. 10.45% (RR 3.97; 95% CI: 2.95–5.33; p < 0.00001). The incidence of high-grade HTN in colorectal patients was 17.28% vs. 1.27% (RR 12.06; 95% CI: 5.19–28.01; p < 0.00001).
  - as recorded (paraphrase): In the colorectal subgroup any-grade hypertension reached 43.02% versus 10.45% and grade 3 or higher hypertension 17.28% versus 1.27%, a risk ratio of 12.06.
  - in `src_doi_10.32604/or.2026.078524` at `paragraph` `sec3.4.2.p2`, section Results / Clinically Actionable Grade 3 or Higher Toxicities / Hypertension; document `art_24d34d336ae8` sha256 `24d34d336ae8f45bdd1335abc021c757a77b737cd7c5efcbe87506e9a1b1338f`; claim `art_e1cb5baf8429` sha256 `e1cb5baf8429b036ba5daebc41201f7301a79c1c4b219d75099183d9393e6b7a` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1141
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

*polarity `supports`*

- **claim_01M4V09QG70AJZF5D613M2P3AB** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% I-squared heterogeneity", "unit_as_reported": "% I-squared heterogeneity", "value": 0, "value_high": null, "value_low": null}`
  > Between-study heterogeneity was low across hypertension analyses (I2 = 0%), indicating consistent treatment effects across trials
  - as recorded (paraphrase): Between-study heterogeneity for hypertension was zero, indicating consistent treatment effects across trials.
  - in `src_doi_10.32604/or.2026.078524` at `paragraph` `sec3.4.2.p3`, section Results / Clinically Actionable Grade 3 or Higher Toxicities / Hypertension; document `art_24d34d336ae8` sha256 `24d34d336ae8f45bdd1335abc021c757a77b737cd7c5efcbe87506e9a1b1338f`; claim `art_b8a5ddfdbdeb` sha256 `b8a5ddfdbdeb5d4931dba9ad5e65e92390cadd46a310a809f6cdbf50c998fcf0` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1142
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review item `q_01M4VEGWV20CJP101H5T4N0GYK` (`open`, blocking `True`, raised 2026-10-13T20:16:05.986Z): proposer and critic still disagree after one revision
  - inspection bundle: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "open_critic_findings": [{"check": "unit_applicability_consistency", "finding": "direction remains 'lower_better' while the definition states that 'the rule carries no monotone ordering over the pool and no cutoff' and predicate_form is qualitative_judgment. The declared direction is not enforced by any predicate, so a consumer reading the direction field would order the pool on a quantity the rule deliberately refuses to order; proposals 23 and 25 carry the same mismatch.", "proposal_index": 21, "referent": "attribute.direction", "severity": "material", "verdict": "fail"}], "pool_criterion": "cri_01M4V2222DE6V3RQZT3P0DY3W6"}`
- unresolved proposer/critic disputes: `q_01M4VEGWV20CJP101H5T4N0GYK`
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `unit_applicability_consistency` on attribute.direction · severity `material` · verdict `fail`: direction remains 'lower_better' while the definition states that 'the rule carries no monotone ordering over the pool and no cutoff' and predicate_form is qualitative_judgment. The declared direction is not enforced by any predicate, so a consumer reading the direction field would order the pool on a quantity the rule deliberately refuses to order; proposals 23 and 25 carry the same mismatch.

**Lineage and lifecycle**

- pool lineage `cri_01M4V2222DE6V3RQZT3P0DY3W6` at version `5`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for toxicological_safety
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Structured value 0 carries unit '% I-squared heterogeneity' - a meta-analytic consistency statistic. On a patient-incidence scale with lower_better it reads as a 0% hypertension rate, the best attainable score.; Structured value 43.02 is an ANY-GRADE hypertension rate (the high-grade figure in the quote is 17.28%), pooled by median with the grade >=3 values in claim_01M4V09QFMZ820S46XHCGDWHTF (13.96) and claim_01M4TXQQRNXEWJEGS3GDDC1CNP (24.8). Two severity strata on one scale.; claim_01M4V09QEK
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Hypertension is an on-target consequence of the coverage the objective requires: claim_01M4TX9937CKPPPM3WZGXCM35C ties it to VEGFR inhibition and claim_01M4V09QEKMZED9SNCXRRKXK89 states that 'pharmacologic inhibition predictably results in a characteristic spectrum of treatment-related toxicities'. A monotone lower_better therefore rewards weaker engagement of the required vascular receptors; the falsification test flags this, but the scored direction still pulls against the objective.; The scor
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `needs_refine` · `refined_still_failing` · schema: schema: an ordering rule ranks candidates, so it must be a preference
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The rule form is corrected: an ordering rule must be a preference, so this consideration now uses predicate_form qualitative_judgment with rule_kind exploratory_consideration and no cutoff, which is the valid way to surface a measured rate for a human judgement. The substance is unchanged and the definition states it: the grade 3 or higher rate is recorded and weighed against the candidate's coverage of the required vascular receptors rather than ordering the pool, because a monotone preference on an anticipated on-target effect would reward weaker engagement of a required receptor.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `disputed` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 20. Incidence of grade 3 or higher serum phosphate elevation

- **attribute** `attr_incidence-of-grade-3-or-higher-serum-phosphate-elevation@v1` · **rule** `rule_incidence-of-grade-3-or-higher-serum-phosphate-elevation@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_incidence-of-grade-3-or-higher-serum-phosphate-elevation@v1"]`, rule `["rule_incidence-of-grade-3-or-higher-serum-phosphate-elevation@v1"]`; supersedes —
- **record hashes**: attribute `40432128ee6a7e2289c19852960901e55be86161063e0ba5159dd8743b6547eb`, rule `b91a07846a75bf348dedb010ab7e77a1619ff6a8c3b5e4a4c5cbb36b05d38824`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V222634HXNASHZY4AJJ6XH@v5"}` · dimension `toxicological_safety`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Incidence of grade 3 or higher serum phosphate elevation · subject `[{}]` · unit `% of patients` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `b99f5e7b2a3570517363788f2f21458d51225f7f0581458d3434611ffee6cece`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `context_only` (`exploratory_consideration`) · predicate form `qualitative_judgment` · direction `lower_better`
  - predicate: no executable predicate; the value is surfaced for a human judgement
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `72a8e44bbf1cc9f79a41166c8ef4e203ca332da6628784f4193afa52acb55ac6`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose
  - gap: decision_semantics: direction `lower_better` is declared while predicate_form is `qualitative_judgment`, so no predicate enforces it

**Operational definition**

> The proportion of treated patients developing grade 3 or higher serum phosphate elevation, as a percentage. Only that severity is entered: the any-grade rate, which the cited evidence puts an order of magnitude higher, is recorded alongside rather than entered. The management thresholds in the evidence are serum concentrations in milligrams per decilitre and cannot enter a percentage axis; they are recorded with the value, as are reported hypothyroidism and lipid changes, which are separate endpoints. Serum phosphate disturbance is an anticipated pharmacodynamic consequence of inhibiting one of the required receptors, which the cited evidence names as a key regulator of phosphate homeostasis. The measured rate is therefore recorded and weighed as a judgement against the candidate's coverage of that receptor rather than ordering the pool: a lower rate counts in a candidate's favour only where coverage of that receptor is comparable, a low rate in a candidate whose coverage is weaker is routed to a human, and the attribute never ranks a candidate downward for an anticipated consequence of a required target. Because the judgement is on the rate together with the coverage, the rule carries no monotone ordering over the pool and no cutoff; the percentage, its severity grade, the management thresholds and the candidate's coverage are what the human sees.

- **unit** `% of patients` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: The measured severe phosphate-elevation rate is surfaced for every candidate alongside its coverage of the required fibroblast growth factor receptor, with any-grade rates and the milligram-per-decilitre management thresholds visible in the record, so no candidate is ranked downward for an anticipated consequence of a required target.
- **falsification test**: Because phosphate disturbance is on-target for a required receptor, a candidate with no such signal may be failing to engage that receptor; a clean phosphate profile must be checked against the fibroblast growth factor receptor coverage criteria before it is credited.
- **rationale**: The cited quotes make this the clearest case of a toxicity locked to a required target: the fibroblast growth factor receptor the objective requires is named as a key regulator of phosphate homeostasis, so serum phosphate disturbance is an anticipated pharmacodynamic effect of inhibiting it. They also quantify it at both severities, any-grade running at roughly 60 to 80 percent with 15 to 20 percent grade 3 or higher, and individual trials reporting 58, 74.2 and 75 percent any-grade with about 10 percent and 2.3 percent grade 3 or higher; because the two severities differ by an order of magnitude, only the grade 3 or higher rate is entered. Management is defined by numeric thresholds in milligrams per decilitre, binders started around 5 to 6, 7 as grade 3 requiring dose reduction, rechallenge below 5.5 and permanent discontinuation above 10; those are concentrations and are recorded rather than entered. Hypothyroidism appears among the commonest events for a vascular-receptor-selective agent and 80 percent of patients on one agent needed a lipid-lowering drug, but those are separate endpoints, and the quote naming hypothyroidism carries only a reporting cutoff of 20 percent rather than an incidence, so it has been removed from the support. Because the effect is anticipated for a required target, the rule is an exploratory consideration rather than a preference, and the rate discriminates only between candidates of comparable coverage.

**Rule**

- **kind** `exploratory_consideration` · **predicate form** `qualitative_judgment` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `be1ea46d7e21dbbdb63802532abe49510f4b345c771fd5a6fb99123e643a1a9f` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (hyperphosphat?emia OR phosphate OR hypothyroidism OR hyperlipid?emia OR \"thyroid function\") AND (incidence OR percent OR % OR grade OR threshold)", "relevance_terms": ["hyperphosphatemia", "phosphate", "hypothyroidism", "hyperlipidemia"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 6 cited claim(s), 6 carry `location.span_checked_against_source: true` and 6 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 5, `value_not_in_quote` 0, not recorded 1 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 6}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 6}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TXQPTBW9MEN037003ZG1W8** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > FGFR1 is a key regulator of phosphate homeostasis; therefore, on-target disturbances of serum phosphate are an anticipated pharmacodynamic effect of pemigatinib and other FGFR inhibitors
  - as recorded (paraphrase): FGFR1 is a key regulator of phosphate homeostasis, so on-target disturbance of serum phosphate is an anticipated pharmacodynamic effect of FGFR inhibitors.
  - in `src_doi_10.2147/dddt.s559328` at `paragraph` `sec3.2.p1`, section Clinical Efficacy & Safety / Pemigatinib; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_fd53f31c66c7` sha256 `fd53f31c66c750f1487987e3a6bc13b2a2c887e5b5a1a62b32bd3e13d0a8e9e8` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 189
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXQQDCBWYE20MQ2JQD1A2D** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% of patients (any-grade hyperphosphataemia)", "unit_as_reported": "% of patients (any-grade hyperphosphataemia)", "value": null, "value_high": 80, "value_low": 60}`
  > Across pivotal trials, any-grade hyperphosphataemia is reported in roughly 60–80% of patients (grade ≥ 3 in about 15–20%), while alopecia, diarrhoea, dry mouth and fatigue each occur in ~40–70% of cases, and nail changes or other dermatologic events in about one-third
  - as recorded (paraphrase): Across pivotal trials any-grade hyperphosphataemia occurs in roughly 60 to 80% of patients with grade 3 or above in about 15 to 20%, while alopecia, diarrhoea, dry mouth and fatigue each occur in about 40 to 70% and nail changes or other dermatologic events in about one third.
  - in `src_doi_10.2147/dddt.s559328` at `paragraph` `sec3.6.p1`, section Clinical Efficacy & Safety / Common Side Effects and Management; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_4c7b24c487bd` sha256 `4c7b24c487bdd0578439df23e9208f31a78f5408b3a58a24f4ec23187bd3ad15` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 218
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) pivotal FGFR inhibitor trials · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXQQEZAHRH5HDFY12WQYF3** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": "mg/dl", "unit_as_reported": "mg/dl", "value": 7, "value_high": null, "value_low": null}`
  > Along with these measures, phosphate lowering agents should be administered when serum levels exceed ≥7 mg/dl.
  - as recorded (paraphrase): Phosphate-lowering agents should be given when serum phosphate exceeds 7 mg/dl.
  - in `src_doi_10.2147/dddt.s559328` at `paragraph` `sec3.6.p2`, section Clinical Efficacy & Safety / Common Side Effects and Management; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_37d9a9dc9bbc` sha256 `37d9a9dc9bbc7227af2701c01cbe94fd4813496ae3262c144aeaf7135da263b4` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 221
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXQQFK4S696WRX5YEF1NS2** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": "mg/dl (permanent discontinuation threshold)", "unit_as_reported": "mg/dl (permanent discontinuation threshold)", "value": 10, "value_high": null, "value_low": null}`
  > Any serum phosphate ≥7 mg/dl is grade 3 hyperphosphatemia and warrants dose reduction. Serum phosphate levels are to be monitored weekly. If levels decrease to <5.5mg/dl, rechallenge can be tried. Repeat elevation above 7mg/dl should prompt a switch to an alternate FGFR inhibitor. Repeat values above 10mg/dl are an indication for permanent discontinuation.
  - as recorded (paraphrase): Serum phosphate of 7 mg/dl or above is grade 3 hyperphosphataemia warranting dose reduction, phosphate is monitored weekly, rechallenge can be tried below 5.5 mg/dl, repeat elevation above 7 mg/dl prompts a switch of agent and repeat values above 10 mg/dl indicate permanent discontinuation.
  - in `src_doi_10.2147/dddt.s559328` at `paragraph` `sec3.6.p2`, section Clinical Efficacy & Safety / Common Side Effects and Management; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_9dae539d13c2` sha256 `9dae539d13c2630c17f28608ac5d40de3265e5ad6ea58b407dfe3ee372e1ab4c` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 222
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXQQMTZCKZPVKRJBZ26M6N** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% grade >=3", "unit_as_reported": "% grade >=3", "value": null, "value_high": 20, "value_low": 15}`
  > Hyperphosphataemia | ≈60–80/15–20 | On-target (renal FGFR inhibition) | Early, often within first 1–2 cycles | Dietary restriction, start phosphate binders around 5–6 mg/dL in asymptomatic patients; dose hold/reduction for higher or symptomatic levels; avoid over-correction to hypophosphataemia
  - as recorded (paraphrase): Hyperphosphataemia occurs in about 60 to 80% of patients with 15 to 20% grade 3 or above, is an on-target effect of renal FGFR inhibition, appears early within the first one to two cycles, and is managed with dietary restriction, phosphate binders started around 5 to 6 mg/dL, and dose hold or reduction at higher or symptomatic levels.
  - in `src_doi_10.2147/dddt.s559328` at `table` `table3`, section Tables; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_8f9afba6672a` sha256 `8f9afba6672a8dfc0476818c70f1a5e18c4261112c21895d36d9d95384d05225` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 232
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXQQNPFXC3G23TAK7D47ZX** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% of patients", "unit_as_reported": "% of patients", "value": 75, "value_high": null, "value_low": null}`
  > Hyperphosphatemia was the most common treatment-emergent adverse event (TEAE) (75%, grade ≥ 3, 2.3%).
  - as recorded (paraphrase): In a dose-finding study, hyperphosphataemia was the most common treatment-emergent adverse event at 75% with 2.3% grade 3 or above.
  - in `src_doi_10.2147/dddt.s559328` at `paragraph` `sec3.2.p2`, section Clinical Efficacy & Safety / Pemigatinib; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_84dacdd76457` sha256 `84dacdd764571e1e399f92e36cf617388f159e8b4915555c36fe7e7dbdd949e6` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 234
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage `cri_01M4V222634HXNASHZY4AJJ6XH` at version `5`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for toxicological_safety
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Structured value 7 is a serum phosphate concentration in mg/dl at which binders are started, not a percentage of patients; claim_01M4TXQQFK4S696WRX5YEF1NS2 (value 10, mg/dl) is the same category error. Both would enter a '% of patients' scale as rates.; Structured value 20 is the REPORTING cutoff used to decide which adverse events the source listed ('incidence >= 20%'), not the incidence of any endocrine or metabolic event.; Any-grade and grade >=3 strata are pooled under one unit: claim_01M4TX
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The definition includes 'the intervention thresholds that apply' on a '% of patients' axis, but those thresholds are concentrations: 'phosphate lowering agents should be administered when serum levels exceed >= 7 mg/dl' (claim_01M4TXQQEZAHRH5HDFY12WQYF3) and 'Repeat values above 10mg/dl are an indication for permanent discontinuation' (claim_01M4TXQQFK4S696WRX5YEF1NS2). A mg/dl threshold cannot enter a percentage median.; Any-grade and grade 3 or higher rates for the same toxicity are both avail
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `needs_refine` · `refined_still_failing` · schema: schema: an ordering rule ranks candidates, so it must be a preference
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The rule form is corrected: an ordering rule must be a preference, so this consideration now uses predicate_form qualitative_judgment with rule_kind exploratory_consideration and no cutoff. The substance is unchanged: the grade 3 or higher phosphate-elevation rate is recorded with the any-grade rate and the milligram-per-decilitre management thresholds and weighed against the candidate's coverage of the required fibroblast growth factor receptor, because a monotone preference on an anticipated on-target effect would reward weaker engagement of it.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 21. Measured change in a co-administered drug's exposure

- **attribute** `attr_measured-change-in-a-co-administered-drug-s-exposure@v1` · **rule** `rule_measured-change-in-a-co-administered-drug-s-exposure@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_measured-change-in-a-co-administered-drug-s-exposure@v1"]`, rule `["rule_measured-change-in-a-co-administered-drug-s-exposure@v1"]`; supersedes —
- **record hashes**: attribute `bbc8a00c0a198e8d521195b0890c5306ff930c6ddf381e583835b94f225b0feb`, rule `d7e862aabbf54fbdf2a95f24f8a9a6acb24c41ed8f114b21052a79bbe230bd86`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1REHNKFS87VCDBEGNCB72@v6"}` · dimension `metabolic_stability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Measured change in a co-administered drug's exposure · subject `[{}]` · unit `% change in co-medication AUC (magnitude)` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `e1c279e61cfc6744d7614a82b01c8ad6cfcbf14d5c5cadff95b71c55a99091da`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `f03470689e66454feaff41c59ecec2b0cc0e062bab1b78e3db4b94871bb894a3`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The change the compound produces in the systemic exposure (AUC) of a co-administered probe or victim drug in an administered clinical interaction study, entered as a non-negative percentage of that drug's exposure without the compound, so that a 92 percent fall and a 92 percent rise score alike; the direction of the change, the victim drug and the study design are recorded but are not scored. Fold changes are converted before entry: a 2.8-fold increase enters as 180 percent, and a fall to one third of exposure enters as 67 percent. A value is entered only where the quote reporting it shows the result came from an administered study. Where a quote presents its numbers inside an in-vitro, preclinical or predicted finding, the figures are recorded as a flag and never entered, whatever their size, because whether they were ever observed in people cannot be read from the quote; a peak-concentration change without an exposure change and a single case report are recorded as flags on the same ground. Where several victim drugs have been studied the value is the median across them, not the largest change, because a largest-change rule can only worsen as more victim drugs are examined and would penalise a compound for the depth of its interaction programme, whereas a median moves in both directions as null results are added; the number of victim drugs studied is recorded with the value. Smaller magnitude is better.

- **unit** `% change in co-medication AUC (magnitude)` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates that leave the exposure of co-administered drugs largely unchanged rank above candidates that move it substantially in either direction, the ranking no longer turns on whether a source wrote a fold or a percentage, and a compound examined against many victim drugs is no longer scored worse than one never tested as a perpetrator.
- **falsification test**: Check that every entered value is an exposure change from an administered study and that fold values were converted. If most candidates have only in-vitro or case-report findings, the attribute ranks almost nothing and the recorded flags, not the score, carry the dimension; if the median across victim drugs hides a single severe interaction with a narrow-therapeutic-index drug, that interaction must be surfaced as a flag for a human rather than averaged away.
- **rationale**: The cited quotes give measured magnitudes for this experiment in people: one agent, at steady state in patients, behaved as a strong inducer in a phenotypic cocktail study and reduced probe-substrate exposures by 92, 85 and 46 percent, and another raised the exposure of an oral transporter substrate approximately 2.8-fold. Because those sources report increases and decreases, folds and percentages, and several victim drugs per compound, the definition states one axis, one sign convention, the fold conversion and the exclusion of endpoints that are not exposure, and takes the median across victim drugs so that a compound studied against many probes is not scored worse for having been studied. Two quotes previously cited have been removed because they present their numbers inside findings introduced as in-vitro evidence and as a preclinical study, so whether the reductions they report were observed in people cannot be read from the quote; they belong in the recorded flags, as do peak-concentration-only reports and the single bleeding case report with a narrow-index anticoagulant. The claims also record that interaction-screening tools focused on the cancer drug's own clearance easily miss this direction of interaction, which is why the dimension is scored at all, and no cited quote states an acceptable magnitude, so the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `f7e33bbe834d315958ab70afe9dcd07dcb6707b54d234892ff170ceee950a160` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (midazolam OR digoxin OR rosuvastatin OR warfarin OR \"probe substrate\" OR \"inhibitor of CYP\" OR \"inducer of CYP\" OR \"P-glycoprotein inhibitor\" OR \"BCRP inhibitor\") AND (AUC OR exposure OR interaction)", "relevance_terms": ["probe substrate", "midazolam", "digoxin", "AUC", "inhibitor"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 2 cited claim(s), 2 carry `location.span_checked_against_source: true` and 2 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 1, `value_not_in_quote` 0, not recorded 1 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 2}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 2}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TYZ6JGW5GDYWGXP625KPJW** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Beyond metabolism, the efflux transporters P-gp and BCRP and the uptake transporter family OATP mediate interactions for agents that are their substrates or inhibitors [19,63]. Several agents reviewed here are not only substrates but inhibitors: lapatinib increased the AUC of oral digoxin approximately 2.8-fold; ibrutinib inhibits P-gp and BCRP; venetoclax is both a substrate and an inhibitor of P-gp and BCRP, with the label advising separation of narrow-index P-gp substrates by at least six hours; and pazopanib inhibits UGT1A1 and OATP1B1
  - as recorded (paraphrase): Beyond metabolism the efflux transporters P-glycoprotein and BCRP and the uptake transporter family OATP mediate interactions for substrates and inhibitors, and several agents are themselves transporter inhibitors, with one VEGFR multikinase agent inhibiting UGT1A1 and OATP1B1.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec7.4.p1`, section 7. CYP-Mediated and Transporter-Mediated Drug–Drug Interactions / 7.4. Transporter-Mediated Interactions; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_2c60b28e9c0c` sha256 `2c60b28e9c0cba9703f09cfbd2ba3cf98b04c65f71f400aa717211d4ba22a9b2` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 702
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`
- **claim_01M4TYZ6KANW13ZKFYPZP82B4Y** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% reduction in co-medication AUC", "unit_as_reported": "% reduction in co-medication AUC", "value": 92, "value_high": null, "value_low": null}`
  > Two of the agents reviewed here are themselves strong CYP3A4 inducers, and this perpetrator role is at least as clinically important as their victim profile. Enzalutamide, at steady state in patients, behaved as a strong CYP3A4 inducer in a phenotypic cocktail study, reducing midazolam exposure substantially [11], and apalutamide produced even more dramatic effects in a dedicated drug-interaction study: midazolam AUC fell by 92%, omeprazole AUC by 85%, and S-warfarin AUC by 46%
  - as recorded (paraphrase): Two reviewed agents are themselves strong CYP3A4 inducers, with one reducing the exposure of co-administered probe drugs by 92%, 85% and 46%, a perpetrator role at least as clinically important as their victim profile.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec7.3.p1`, section 7. CYP-Mediated and Transporter-Mediated Drug–Drug Interactions / 7.3. Perpetrator Role of Androgen-Axis Antagonists; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_996dbc91892e` sha256 `996dbc91892eb26de46837b028f0f16af315807434d908260d6cc3a16faad592` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 705
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage `cri_01M4V1REHNKFS87VCDBEGNCB72` at version `6`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for metabolic_stability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · lower_better pools reductions (claim_01M4TYZ6KANW13ZKFYPZP82B4Y=92, claim_01M4TZRMT8VX9JM9QMQWD86SCD=61) with increases (claim_01M4TZRMQEFB39VYKA01DQZYAY=134). The definition asks how STRONGLY co-medications are perturbed, but nothing takes an absolute value, so a 92% suppression and a 134% elevation are ordered against each other, not by magnitude.; Quote reports Cmax increases of 72% and 23%, not AUC changes, so it is not a value on this attribute's declared scale.; claim_01M4TZRMT8VX9JM9QMQWD
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · A single axis of '% change in co-medication AUC' cannot carry the cited evidence. The claims mix scales ('increased the AUC of oral digoxin approximately 2.8-fold', claim_01M4TYZ6JGW5GDYWGXP625KPJW), endpoints (Cmax only in claim_01M4TZRMV16FFAA79YHRQ4YD4G, 'Cmax showed significant increases of 72% and 23%'), signs (increases in claim_01M4TZRMQEFB39VYKA01DQZYAY against 'midazolam AUC fell by 92%' in claim_01M4TYZ6KANW13ZKFYPZP82B4Y) and multiple probe substrates per compound. With no conversion 
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The axis is now single and well defined: a non-negative percentage change in a victim drug's exposure from an administered study, with folds converted, the sign recorded but not scored, and peak-concentration, in-vitro and case-report findings excluded as flags rather than entered, which also removes the boolean-plus-magnitude wording and the three claims that have no entry on the scale. Aggregation moves from max to the median across victim drugs, with the number studied recorded, so depth of study no longer monotonically worsens the score.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The admission rule requires an administered interaction study, but this quote presents its numbers inside an in-vitro finding: 'in vitro evidence suggests that lorlatinib has moderate CYP3A4/5 inductor activity, with a reduction of 50% in midazolam Cmax and a 61% reduction in AUC'. Whether the 61 percent is an administered result cannot be read from the quote, and claim_01M4TZRMQEFB39VYKA01DQZYAY is likewise introduced as 'A preclinical study'.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The admission rule is enforced on the evidence as well as in the definition: the two quotes that present their numbers inside an in-vitro finding and a preclinical study are dropped from the support, and the definition now states that figures presented inside an in-vitro, preclinical or predicted finding are recorded as flags and never entered, whatever their size. The remaining cited values are a phenotypic cocktail study at steady state in patients and a co-administration result in people.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 22. Molecular weight in excess of the stated upper bound

- **attribute** `attr_molecular-weight-in-excess-of-the-stated-upper-bound@v2` · **rule** `rule_molecular-weight-in-excess-of-the-stated-upper-bound@v2` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_molecular-weight-in-excess-of-the-stated-upper-bound@v1", "attr_molecular-weight-in-excess-of-the-stated-upper-bound@v2"]`, rule `["rule_molecular-weight-in-excess-of-the-stated-upper-bound@v1", "rule_molecular-weight-in-excess-of-the-stated-upper-bound@v2"]`; supersedes `attr_molecular-weight-in-excess-of-the-stated-upper-bound@v1`
- **record hashes**: attribute `80be32835f08588a3ddc8172ed9b6888c3be016fc78ad6b076fd9302f45eb47a`, rule `9448a6e390422821a627c4d2a858bfea67927b2f6123b702e3074e4699c1f190`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1FPBYWEPR40J6510X14Z0@v5"}` · dimension `oral_bioavailability`
- **written by software**: `{"adjudicated_by": "adj_01M4WYA3P9EW16MP2V3GVQEAHY", "rule_adjudicated_by": "adj_01M4WYA3P9EW16MP2V3GVQEAHY"}`

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Molecular weight in excess of the stated upper bound · subject `[{"property": "MolecularWeight"}]` · unit `g/mol` · `quantitative` · aggregated by `median` · transform `{"basis": "source_stated_value", "bound": 500, "kind": "excess_above", "source_refs": ["claim_01M4TXF4M4X0E0TMMW8R9FX4SV"]}`
  - read from `["property_estimate"]` asking `["computed_property"]`; evidence kinds `["database_entry"]`; determination bases —
  - measurement identity `2016a4858cccd2c403b560b27d6b1ea98930e7785277b47b1c3eb782c21e527d`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `unknown_no_penalty` · decision identity `9c4dc7946e3841606f5b9be7f330f0a7351d4197ad2d59c4f9c584b28d62adc8`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The computed molecular weight of the molecule, expressed as its excess in g/mol above 500 g/mol, the upper end of the band that the cited source states for this inhibitor class and describes as close to the upper limit compatible with efficient passive diffusion: zero for a molecule at or below 500 g/mol, and the difference above 500 g/mol for a heavier one. The quantity is one-sided because the cited evidence is one-sided: it penalises excessive weight through reduced intestinal absorption and greater recognition by efflux transporters, and it describes agents of this class as typically low-molecular-weight, so no cited quote states that a lighter molecule is absorbed worse and no shortfall below the lower end of the band is scored here. Lower is better by construction. A computed weight is a derived descriptor, so where a measured oral bioavailability exists for the same candidate the measurement governs.

- **unit** `g/mol` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["database_entry"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates at or below the stated upper bound all score zero and are not separated from one another on size, while heavier candidates are demoted in proportion to their excess, and no candidate is demoted for being light.
- **falsification test**: Compute the quantity for the pool. If every candidate scores zero the bound does not discriminate and the attribute should be withdrawn; if candidates ranked well here rank poorly on measured oral bioavailability, the descriptor is not tracking absorption for these molecules and the measurement must govern.
- **rationale**: The cited quote states that most clinically relevant inhibitors of this class fall within approximately 380 to 500 Da, which is considered close to the upper limit compatible with efficient passive diffusion, and a second states that excessive increases in molecular weight are associated with reduced intestinal absorption and enhanced recognition by efflux transporters. A third names molecular weight among the determinants of passive transcellular diffusion and of susceptibility to active efflux transporters such as P-glycoprotein. A fourth, describing these agents as typically low-molecular-weight lipophilic compounds, is cited as counter-evidence against any penalty at the low end, and is why only the excess above the upper bound is scored: the quoted band describes where inhibitors fall, not that a lighter molecule absorbs worse. The two quotes previously cited as a far-end anchor concerned a 115 kDa injected protein and its diffusion into ocular tissue; a kilodalton protein given by injection is three orders of magnitude off this attribute's g/mol axis and belongs to a different route and endpoint, so both have been removed. Two limits remain recorded: the band is quoted in the context of central-nervous-system-directed design, which this objective does not require, and the value is computed rather than measured.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `unknown_no_penalty`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: `{"basis": "source_stated_value", "bound": 500, "kind": "excess_above", "source_refs": ["claim_01M4TXF4M4X0E0TMMW8R9FX4SV"]}`
- **evidence key** `614145c201671074ec738674194dcb2f107287e9208a461785f72cf4a5882931` · 1 route(s) · literature-bound `False`
  - route `property_estimate` / `computed_property` · subject `{"property": "MolecularWeight"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- `attribute.value_transform.bound` = `500` — unit `g/mol` · basis `source_stated_value` · claims `["claim_01M4TXF4M4X0E0TMMW8R9FX4SV"]` · support field: attribute.value_transform.source_refs

**Verification, reported as three separate checks**

- quote check — of 4 cited claim(s), 4 carry `location.span_checked_against_source: true` and 4 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 1, `value_not_in_quote` 0, not recorded 3 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 4}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"supports": 4}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `supports`*

- **claim_01M4TXF4KFBDJF1ASFM4NTQM19** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Among the most critical determinant factors are molecular weight, lipophilicity, polarity, and ionization state, all of which influence passive transcellular diffusion and susceptibility to active efflux transporters, such as P-gp
  - as recorded (paraphrase): Molecular weight, lipophilicity, polarity and ionisation state are the most critical determinants influencing passive transcellular diffusion and susceptibility to active efflux transporters such as P-gp.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.2.p1`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.2. Critical Physicochemical Properties for Oral Bioavailability of KIs and Central Nervous System Penetration; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_1893b08dcdd0` sha256 `1893b08dcdd0e6cefb44a52dcf0cbe263cf2ef087df87eca857c704ab2b9be02` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 127
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXF4M4X0E0TMMW8R9FX4SV** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "Da", "unit_as_reported": "Da", "value": null, "value_high": 500, "value_low": 380}`
  > Most clinically relevant kinase inhibitors typically fall within the range of approximately 380–500 Da, which is considered close to the upper limit compatible with efficient passive diffusion
  - as recorded (paraphrase): Most clinically relevant kinase inhibitors have molecular weights of roughly 380 to 500 Da, close to the upper limit compatible with efficient passive diffusion.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.2.p2`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.2. Critical Physicochemical Properties for Oral Bioavailability of KIs and Central Nervous System Penetration; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_da695a92926d` sha256 `da695a92926d8708f99eb44d3356d4b6de419db89f43120cb2187fe32c3a4402` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 128
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) clinically relevant kinase inhibitors · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXF4N0M24H5RQVF51DH6W4** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Excessive increases in MW are generally associated with reduced intestinal absorption, reduced BBB permeability and enhanced recognition by efflux transporters, ultimately limiting CNS exposure
  - as recorded (paraphrase): Excessive molecular weight is associated with reduced intestinal absorption, reduced blood-brain barrier permeability and greater recognition by efflux transporters.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.2.p2`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.2. Critical Physicochemical Properties for Oral Bioavailability of KIs and Central Nervous System Penetration; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_1e167c5385f8` sha256 `1e167c5385f8811b7ee622be83c6c37c256400ef0debb43b448903d65af1d14c` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 129
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXF4WPE3JHKCBGQ5WWPPAM** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > These agents are typically low-molecular-weight organic compounds and lipophilic, penetrating cells and directly targeting the catalytic activity of intracellular kinases
  - as recorded (paraphrase): Small-molecule kinase inhibitors are typically low-molecular-weight, lipophilic organic compounds that penetrate cells and target the catalytic activity of intracellular kinases.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.1.p1`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.1. Types of Kinase Inhibitors; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_8f805617ec3b` sha256 `8f805617ec3b17f74b8acc4ce873ea9ea87346e29eaea3ae88385fe20e1ef8d5` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 140
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudication `adj_01M4WYA3P9EW16MP2V3GVQEAHY` · route `definition_restated` · resolution `declare_value_transform` · approval kind `agent_verdict` · confirmed by a person `False`
  - reason: the attribute's definition states the excess above 500 and the attribute declared no transformation, so every cell carried the raw value its source returns; the transformation is declared as the definition already describes it, on a bound claims claim_01M4TXF4M4X0E0TMMW8R9FX4SV state, and the definition itself is unchanged
  - cites: `{"bound_traces": {"bound": [{"claim_id": "claim_01M4TXF4M4X0E0TMMW8R9FX4SV", "states_it": "claim_quote"}]}, "claim_ids": ["claim_01M4TXF4M4X0E0TMMW8R9FX4SV"], "definition_text": "The computed molecular weight of the molecule, expressed as its excess in g/mol above 500 g/mol, the upper end of the band that the cited source states for this inhibitor class and describes as close to the upper limit compatible with efficient passive diffusion: zero for a molecule at or below 500 g/mol, and the difference above 500 g/mol for a heavier one. The quantity is one-sided because the cited evidence is one-sided: it penalises excessive weight through reduced intestinal absorption and greater recognition by efflux transporters, and it describes agents of this class as typically low-molecular-weight, so no cited quote states that a lighter molecule is absorbed worse and no shortfall below the lower end of the band is scored here. Lower is better by construction. A computed weight is a derived descriptor, so where a measured oral bioavailability exists for the same candidate the measurement governs.", "field": "definition", "match": "definition_states_a_derived_quantity", "quantity_text": "the excess above 500", "value_transform": {"basis": "source_stated_value", "bound": 500, "kind": "excess_above", "source_refs": ["claim_01M4TXF4M4X0E0TMMW8R9FX4SV"]}}` · claims — · independence —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `unit_applicability_consistency` on attribute.definition · severity `minor` · verdict `fail`: The source states the band as 'approximately 380-500 Da'; using 500 as an exact zero point converts an approximate bound into a precise one, so candidates a few g/mol either side of it are separated by a precision the quote does not carry.

**Lineage and lifecycle**

- pool lineage `cri_01M4V1FPBYWEPR40J6510X14Z0` at version `5`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for oral_bioavailability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · direction within_range but predicate_form threshold with the single comparator <=500, so the 380 g/mol lower bound in claim_01M4TXF4M4X0E0TMMW8R9FX4SV is not encoded and a 250 g/mol candidate scores as well as a 450 g/mol one - which the definition explicitly disclaims.
  - round `run_01M4V43E8GDH8GF8M633VTWDQJ` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The material finding is accepted: a single <= comparator could not encode the two-sided band the definition claimed, so a very light molecule scored as well as one in the stated band, which the definition itself disclaimed. The fix is to change the measured quantity rather than patch the rule. The attribute now measures the distance in g/mol by which the molecule falls outside the band of roughly 380 to 500 g/mol that the cited quote states, scored as zero inside the band and as the shortfall or excess outside it, with direction lower_better and a plain ordering. Both bounds are now encoded, both come from the cited quote, and no threshold is invented: the rule has no cutoff and cutoff_basis none_evidence_insufficient.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Both bounds do come from this one quote, but the quote supports only the upper one as a liability: 'Most clinically relevant kinase inhibitors typically fall within the range of approximately 380-500 Da, which is considered close to the upper limit compatible with efficient passive diffusion.' It describes where inhibitors fall, not that a lighter molecule absorbs worse, so the penalty for a shortfall below 380 is not stated by the evidence. claim_01M4TXF4N0M24H5RQVF51DH6W4 penalises only 'Exces
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The low-end penalty is removed: the quoted band describes where inhibitors of this class fall and the cited quotes penalise only excessive weight, while another calls these agents typically low-molecular-weight, so only the excess above the stated upper bound is now scored. The 115 kDa injected-protein quotes and the ocular-diffusion quote are dropped as a different route, endpoint and scale from this attribute's g/mol axis.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `scoring` on `rules@v3`
- rule-set entry: `{"acceptable_value_sources": ["database_entry"], "attribute_ref": "attr_molecular-weight-in-excess-of-the-stated-upper-bound@v2", "authority": "machine_adjudication", "confirmed_by": "adj_01M4WYA3P9EW16MP2V3GVQEAHY", "cutoff_basis": "none_evidence_insufficient", "disputed": false, "on_states": ["unknown_no_penalty", "unknown_no_penalty", "unknown_no_penalty"], "rule_kind": "preference", "rule_ref": "rule_molecular-weight-in-excess-of-the-stated-upper-bound@v2"}`
- scores while disputed: `False` · machine adjudicated: `True` · reads a collapsed attribute: `False`
- measured coverage: `{"assessed": 3177, "board": "lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4", "observed": 3084}`

---

### 23. Number of hepatic impairment grades at which dosing is restricted

- **attribute** `attr_number-of-hepatic-impairment-grades-at-which-dosing-is-restr@v1` · **rule** `rule_number-of-hepatic-impairment-grades-at-which-dosing-is-restr@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_number-of-hepatic-impairment-grades-at-which-dosing-is-restr@v1"]`, rule `["rule_number-of-hepatic-impairment-grades-at-which-dosing-is-restr@v1"]`; supersedes —
- **record hashes**: attribute `3820151ca66e1b4bc48b75bd6525414bb2d35027cfff3c4fa63cb706c926b7db`, rule `56478e240930d1e60482887f0fa8d01b07ff0c18a781e7b3a5a6cd0491d25c39`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1REPN4PXP5CYZDKQB3YAA@v5"}` · dimension `metabolic_stability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Number of hepatic impairment grades at which dosing is restricted · subject `[{}]` · unit `count of impairment grades restricted` · `quantitative` · aggregated by `consensus` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `816239abe13316e045114cd3f888d1e72dc5ddd9e06039cf9df08a71a56583c2`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `fa2c13bda89bb85b52ffc99d4b4eee1581df21a40defb05a77eea37647126f19`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The number of the three graded severities of hepatic impairment, mild, moderate and severe, at which the label or clinical pharmacology data for the compound state that a dose reduction is required or that use is not advised or contraindicated: an integer from 0 to 3. A grade counts as unrestricted only where the source reports pharmacokinetic or clinical data at that grade showing that no adjustment is needed. A label that simply contains no dosage adjustment for hepatic impairment is the absence of a labelled finding rather than a demonstrated absence of restriction, so every grade it does not address is recorded as untested and counted neither as restricted nor as unrestricted; a candidate whose only statement is of that kind therefore returns unknown rather than a count of zero. Where a source both restricts a grade and reports that grade as not well studied, the grade counts as restricted and is additionally flagged as restricted on untested grounds, because the restriction is the operative statement for dosing while the flag records that it rests on absent data rather than on measured exposure. The grade or grades restricted, the nature of each restriction, reduction or prohibition, and the number of grades actually covered are recorded with the count, so a partial count is never read as a complete one. Only data for an orally administered small molecule of the kind this objective concerns are used; a statement about a parenterally administered biological agent is outside the comparison and is not entered. Fewer restricted grades is better.

- **unit** `count of impairment grades restricted` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `consensus`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates with data at the graded severities showing no adjustment is needed rank above candidates restricted at several of them, a candidate whose label is merely silent returns unknown rather than a favourable count, and a grade restricted because it is unstudied is visible as such in the record.
- **falsification test**: If a candidate's hepatic-impairment data are absent, that is an untested restriction rather than an absent one, and the attribute must return unknown instead of a favourable score.
- **rationale**: The cited quotes show that hepatic metabolism dominates clearance for most agents of this class, which makes hepatic impairment a frequent determinant of altered exposure and a common basis for dose adjustment, and they give the consequences in the form this count reads: one agent needs a halved dose in mild impairment and is not advised in moderate or severe impairment, with moderate to severe impairment also described as a relative contraindication and severe impairment described as not well studied. That pair of statements is why the definition now has a rule for a grade that is restricted precisely because it is unstudied: the grade counts as restricted, since that is what governs dosing, and carries a flag recording that the restriction rests on absent data. The quote whose only content is that a product label contains no dosage adjustment for hepatic impairment is no longer cited, on two grounds: the absence of a labelled finding is not a demonstrated absence of restriction, which is why such a grade is now recorded as untested rather than counted as unrestricted, and the agent it concerns is a parenterally administered biological rather than an orally administered small molecule, so it cannot calibrate the unrestricted end of this axis. No cited quote states an acceptable number of restricted grades, so the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `3b0168819fab3279a12230e7ad7f6780acaa7a3a8a43ea61e11e524630d21286` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"hepatic impairment\" OR \"Child-Pugh\" OR \"liver impairment\" OR cirrhosis) AND (dose OR adjustment OR contraindicat* OR pharmacokinetic*)", "relevance_terms": ["hepatic impairment", "Child-Pugh", "dose adjustment", "contraindicated"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 5 cited claim(s), 5 carry `location.span_checked_against_source: true` and 5 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 2, `value_not_in_quote` 0, not recorded 3 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 5}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 4, "supports": 1}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TY1RJWJRQP9RWT8WQ2SQ0D** · `conflicts` · evidence `reference_text` · determination `asserted` · value `{"unit": "mg twice daily", "unit_as_reported": "mg twice daily", "value": 100, "value_high": null, "value_low": null}`
  > Hepatic impairment: In cases of mild hepatic impairment (Child-Pugh class A), low body mass index (BMI), or persistent gastrointestinal adverse effects, a dose reduction to 100 mg twice daily is recommended.[16] Nintedanib is not advised for patients with moderate or severe hepatic impairment.
  - as recorded (paraphrase): In mild hepatic impairment, low body mass index or persistent gastrointestinal adverse effects a dose reduction to 100 mg twice daily is recommended, and the agent is not advised in moderate or severe hepatic impairment.
  - in `src_nbk_NBK585049` at `paragraph` `article-143222.s4.p6`, section Administration; document `art_d6f5f137dcb6` sha256 `d6f5f137dcb662288deb6e65d17790449f04dce1f0a228cee80848efe41da003`; claim `art_575a9468a2d5` sha256 `575a9468a2d56eed6695a3b33fcd73e7c0c34697e36f9eb5cf836fd095ecf8bb` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 362
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TY1RWC07WD1Q6SPGFNCV4B** · `conflicts` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Moderate to severe hepatic impairment (Child-pugh class B and C) is also a relative contraindication to nintedanib therapy.[17] Nintedanib is not well-studied in patients with severe hepatic impairment.
  - as recorded (paraphrase): Moderate to severe hepatic impairment is a relative contraindication and the agent is not well studied in severe hepatic impairment.
  - in `src_nbk_NBK585049` at `paragraph` `article-143222.s6.p3`, section Contraindications; document `art_d6f5f137dcb6` sha256 `d6f5f137dcb662288deb6e65d17790449f04dce1f0a228cee80848efe41da003`; claim `art_7407da47f61e` sha256 `7407da47f61eef7f011261a361467281e115c32202e5af5523b743f93acdb907` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 380
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TZM5C3RMHZ9QZEGATZ1XXG** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > In oncology patients, who frequently exhibit an altered hepatic functionality, this first-pass effect can further complicate TKI dosing. Variability in hepatic transporter proteins, such as OATPs (organic anion transporting polypeptides), may modulate drug absorption and elimination, resulting in altered pharmacokinetic profiles that require careful dose adjustments based on individual metabolic status
  - as recorded (paraphrase): Altered hepatic function in oncology patients complicates dosing, and variability in hepatic uptake transporters modulates absorption and elimination so that dose adjustment by individual metabolic status is required.
  - in `src_doi_10.3390/ph18070959` at `paragraph` `sec3.3.p1`, section 3. Pharmacokinetic Drug–Drug Interactions / 3.3. DDIs Affecting TKI Metabolization; document `art_e9c956a4dc7b` sha256 `e9c956a4dc7b2e7da4ec02d0d8ec260cd2ffb32e2749b82fcd654a8b87d3462a`; claim `art_ed31b4456714` sha256 `ed31b4456714032f9cbeee693e7240f4e89bbe588514fd2009af1fc2b17ceb82` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 888
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`
- **claim_01M4V00PF94HP0WXW68SB7NS6F** · `conflicts` · evidence `reference_text` · determination `asserted` · value `{"unit": "mL/min/1.73 m2 eGFR threshold", "unit_as_reported": "mL/min/1.73 m2 eGFR threshold", "value": 30, "value_high": null, "value_low": null}`
  > Baricitinib is contraindicated in patients with chronic kidney disease with an eGFR <30 mL/min/1.73 m². However, for COVID-19 patients, baricitinib is not recommended for patients with end-stage renal disease with an eGFR <15 mL/min/1.73 m². Furthermore, baricitinib is not recommended for patients with severe hepatic impairment.
  - as recorded (paraphrase): The agent is contraindicated in chronic kidney disease with estimated glomerular filtration rate below 30 mL/min/1.73 m2, not recommended below 15 in one indication, and not recommended in severe hepatic impairment.
  - in `src_nbk_NBK572064` at `paragraph` `article-132927.s6.p2`, section Contraindications; document `art_f09893a5f2a3` sha256 `f09893a5f2a38c249a46c0d73fe003e5e19bc338cb246c20f56f53cda70dc87b`; claim `art_fb7ca329dccb` sha256 `fb7ca329dccb67cd54a0c7ef967129260083f3f04b5829947f4333bd2ebd3fbe` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1046
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

*polarity `supports`*

- **claim_01M4TYZ67EZVH1PQV6BX6E0SC1** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Most oral anticancer agents are highly protein-bound, and only the unbound fraction is pharmacologically active and available for distribution, metabolism, and elimination. Because hepatic metabolism dominates the clearance of most of these agents, hepatic impairment is a frequent determinant of altered exposure and a common basis for dose adjustment. Renal elimination of unchanged drug is comparatively minor for many oral targeted agents, though renal contribution and the disposition of active metabolites are agent-specific.
  - as recorded (paraphrase): Most oral anticancer agents are highly protein-bound with only the unbound fraction pharmacologically active, hepatic metabolism dominates clearance so hepatic impairment commonly requires dose adjustment, and renal elimination of unchanged drug is comparatively minor though agent-specific.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec4.5.p1`, section 4. Pharmacokinetic Determinants of Oral Anticancer Drug Exposure / 4.5. Protein Binding, Hepatic Function, and Renal Contribution; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_6ae400f8e0e8` sha256 `6ae400f8e0e852a1ed5428f5a030f19403453ef828a393c1e769cbc7718df601` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 668
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage `cri_01M4V1REPN4PXP5CYZDKQB3YAA` at version `5`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for metabolic_stability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · Restated as a quantity with a unit, as the schema requires of a literature-bound attribute: the count of graded hepatic impairment severities, from 0 to 3, at which the source states a dose reduction or a prohibition, with the grade and the nature of each restriction recorded. A grade with no data is recorded as untested and counted neither way, and the count is reported with the number of grades covered so a partial count is not read as a complete one.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The quote states only that 'The product label does not include specific dosage adjustments for patients with hepatic impairment', which is the absence of a labelled finding. claim_01M4TYZ6MVMRJHNEA0V8AJR2SE, in this same request, says such an entry 'should be read as an untested rather than an excluded' one; scoring it 0 across three grades therefore reads silence as unrestricted, which the attribute's own untested rule forbids.; This claim and claim_01M4TZXZ5FDPFT2PRPTV3KSM7C are about golimuma
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · Silence is no longer scored as unrestricted: a grade counts as unrestricted only where the source reports data at that grade showing no adjustment is needed, a label containing no hepatic adjustment is recorded as untested for every grade it does not address, and a candidate with only such a statement returns unknown. A grade that is restricted precisely because it is unstudied now counts as restricted with a flag recording that basis, and the quote about a parenterally administered biological agent is dropped, so the axis is not calibrated from outside the objective's scope.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 24. Number of molecules required to achieve the reported coverage

- **attribute** `attr_number-of-molecules-required-to-achieve-the-reported-coverag@v1` · **rule** `rule_number-of-molecules-required-to-achieve-the-reported-coverag@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_number-of-molecules-required-to-achieve-the-reported-coverag@v1"]`, rule `["rule_number-of-molecules-required-to-achieve-the-reported-coverag@v1"]`; supersedes —
- **record hashes**: attribute `3076b3ab06cf67257af14be41144f0221aece3322868232d0113d386efcd4414`, rule `8a38ad1f60d17a41e37a1ebc722ca2437bff80d47c4bc3c70386287ccd826eba`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V183S5DPZ4NBTSN24PZ5HA@v5"}` · dimension `target_coverage`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Number of molecules required to achieve the reported coverage · subject `[{}]` · unit `count of molecules` · `quantitative` · aggregated by `consensus` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `c41e1f6ddaff1745495a5d22af9908f53f99bde0aa865648f4a97aa39d307fe0`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `5059804be413a65f3bd528104a190552e703fb681961b6edb9180a6d7291a720`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The number of distinct molecules that the source credits with achieving the reported coverage of the required receptor set: 1 where one molecule is described as covering the receptors itself, 2 or more where the coverage is attributed to a combination or a regimen. Only the molecules said to supply the receptor coverage are counted; co-administered agents with unrelated mechanisms, such as a cytotoxic backbone, are not. Lower is better, with 1 as the value the objective asks for. Values are taken by consensus across the retrieved sources rather than from the most favourable one: a single source describing the molecule as covering the receptors by itself does not set the count to 1 when other sources attribute that coverage to a combination or a regimen, and an unresolved disagreement between sources is routed to a human.

- **unit** `count of molecules` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `consensus`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose five-receptor coverage is attributed to the molecule itself rank above candidates whose coverage is attributed to a regimen, enforcing the single-molecule requirement as a ranking rather than as a rejection on bibliographic wording.
- **falsification test**: If every retrieved source describes every candidate as a single agent the count is 1 throughout and the attribute discriminates nothing; if a candidate scores 2 only because it is usually studied alongside chemotherapy, the counting rule has been misapplied and must be tightened.
- **rationale**: The objective asks for a single orally administered agent, and the cited quotes show that the same pharmacology is routinely reached the other way: single-node monotherapies are described as failing through compensatory pathway hyperactivation and clonal heterogeneity whereas multi-targeted agents or rational dual-node combinations prevent rapid adaptation, co-inhibition of two receptor nodes restores sensitivity in model systems, scaffold adaptability is said to permit either selective or multi-target inhibitors, combinations and degraders are positioned explicitly as the alternatives when single-molecule polypharmacology is constrained, and multi-target agents are credited with overcoming pathway redundancy. Coverage credited to a regimen is therefore not evidence about the candidate molecule, which is what this count makes explicit. It is a ranking rather than an exclusion because the value reflects how a source attributed the pharmacology, and a candidate described only in combination may still be a single-molecule multi-target agent. Aggregation is consensus rather than a minimum, because a minimum takes the most favourable source and would score the count as 1 however many other sources attributed the coverage to a regimen, inverting the attribute's stated purpose of detecting combination-dependent coverage.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `220124cfe594c34fa5198951debc4842f23c9250e8cd759ab2ef001cd4866552` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (monotherapy OR \"single agent\" OR \"multitargeted\" OR \"multikinase\" OR \"multi-kinase\" OR combination) AND (CSF1R OR VEGFR OR FGFR)", "relevance_terms": ["single agent", "monotherapy", "multikinase", "combination"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 5 cited claim(s), 5 carry `location.span_checked_against_source: true` and 5 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 5 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 5}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 1, "supports": 4}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TY6CW8TF1NAVBN4MXYMZBT** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > We also summarize combination therapy that augments selective FLT3 blockade and outline PROTAC approaches that induce FLT3 degradation, positioning these modalities as alternatives when single-molecule polypharmacology is constrained.
  - as recorded (paraphrase): Combination therapy and degrader approaches are positioned as alternatives when single-molecule polypharmacology is constrained.
  - in `src_doi_10.1039/d6ra01319h` at `abstract` `abstract.p1`, section Abstract; document `art_dd6c9b208f11` sha256 `dd6c9b208f110ca3d6d1dca45d3a009b8b51440cc04c37911c49684151e98ddf`; claim `art_6e057cb99bc0` sha256 `6e057cb99bc04bf97286c8b183d25155ef093f368585faf0e501116ca7776118` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 434
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

*polarity `supports`*

- **claim_01M4TXF44J2PCMZNB4X82BK66F** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Reviewing recent clinical failures, such as paxalisib and osimertinib, underscores that single-node monotherapies fail due to compensatory pathway hyperactivation and clonal heterogeneity, whereas multi-targeted agents or rational dual-node combinations prevent rapid tumor adaptation.
  - as recorded (paraphrase): Single-node monotherapies fail because of compensatory pathway hyperactivation and clonal heterogeneity, whereas multi-targeted agents or rational dual-node combinations prevent rapid tumour adaptation.
  - in `src_doi_10.3390/ijms27156590` at `abstract` `abstract.p1`, section Abstract; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_c6e57d5cd942` sha256 `c6e57d5cd9420fd147ee686dde0af1fd494c742d60388ec26a588eaa21004bb5` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 110
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXF495C5NRV9MRKJ1GK0MQ** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > This structural adaptability facilitates the design of both selective and multi-target inhibitors, a feature particularly relevant in GB, where pathway redundancy often necessitates broader kinase inhibition
  - as recorded (paraphrase): Scaffold adaptability allows design of both selective and multi-target inhibitors, which is relevant where pathway redundancy necessitates broader kinase inhibition.
  - in `src_doi_10.3390/ijms27156590` at `paragraph` `sec5.3.p4`, section 5. Targeted Therapies: Kinase Inhibitors (KIs) / 5.3. Chemical Design of Oral Kinase Inhibitors; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_b3756e154a63` sha256 `b3756e154a63c467dbf017bdd730ad069b96bc40ac5956c43acf185034311e3c` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 113
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXQR2XR0XMW0QDAXG8G629** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Co-inhibition (eg, EGFR + FGFR) restores sensitivity in FGFR2-fusion models and early translational settings.
  - as recorded (paraphrase): Co-inhibition of two receptor nodes restores sensitivity in fusion models and early translational settings.
  - in `src_doi_10.2147/dddt.s559328` at `paragraph` `sec4.p6`, section Resistance Mechanisms; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_9dfd5600e92f` sha256 `9dfd5600e92f1f4941ac0d5daa8342682272dee4eb91863a9ba8a5a5062fc285` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 258
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYRRC54N7CM8M6JVYNEKTK** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > In addition, recent advances in dual- and multitarget agents that simultaneously modulate c-Met and complementary therapeutic targets, including VEGFR-2, EGFR, AXL, MER, PARP1, CDK2, and tubulin, are highlighted as promising strategies for overcoming pathway redundancy and acquired resistance.
  - as recorded (paraphrase): Dual- and multitarget agents that simultaneously modulate a primary receptor kinase and complementary targets including VEGFR-2 are promising strategies for overcoming pathway redundancy and acquired resistance.
  - in `src_doi_10.3390/ijms27188007` at `abstract` `abstract.p1`, section Abstract; document `art_480b68481ece` sha256 `480b68481ecefe2a1fdafb89f03b786362ce39c7543050d4150c5567f2a10d23`; claim `art_e8b8d712dd57` sha256 `e8b8d712dd57c539cdfa118d4f9340e93c5ea6627fdff2a32884f4a4cb86c975` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 579
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `evidence_support` on claim_01M4TXF495C5NRV9MRKJ1GK0MQ · severity `minor` · verdict `fail`: This quote is about design feasibility, 'facilitates the design of both selective and multi-target inhibitors', and claim_01M4TYRRC54N7CM8M6JVYNEKTK about dual- and multitarget agents in general. Neither credits coverage to a counted number of molecules for any candidate.

**Lineage and lifecycle**

- pool lineage `cri_01M4V183S5DPZ4NBTSN24PZ5HA` at version `5`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for target_coverage
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The validator finding is accepted and the quantity is made numeric with a unit: instead of a qualitative determination of whether coverage is achieved by one molecule, the attribute now counts the number of distinct molecules that the source credits with achieving the reported coverage of the required receptor set, an integer with the unit 'count of molecules', direction lower_better, so a single molecule covering the set scores 1 and a two-drug regimen scores 2. The rule is changed from a hard exclusion with a null cutoff, which could not have been executed, to a preference with predicate_form ordering and cutoff_basis none_evidence_insufficient; the single-molecule requirement in the objective is thereby expressed as a strong ranking signal without rejecting a candidate on how a source happened to attribute its coverage. Citations are unchanged and all five bear on single-molecule versus combination pharmacology.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Aggregation 'min' with direction lower_better takes the most favourable source: if any one source describes the molecule as covering the receptors alone, the score is 1 however many other sources attribute the coverage to a combination. That inverts the attribute's stated purpose of detecting combination-dependent coverage.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · Aggregation moves from min to consensus, so one favourable source can no longer set the count to 1 against other sources that attribute the coverage to a combination; the definition states the consensus rule and routes an unresolved disagreement to a human, which restores the attribute's stated purpose.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 25. Number of renal function strata at which dosing is restricted

- **attribute** `attr_number-of-renal-function-strata-at-which-dosing-is-restricte@v1` · **rule** `rule_number-of-renal-function-strata-at-which-dosing-is-restricte@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_number-of-renal-function-strata-at-which-dosing-is-restricte@v1"]`, rule `["rule_number-of-renal-function-strata-at-which-dosing-is-restricte@v1"]`; supersedes —
- **record hashes**: attribute `1f265d6d9ccec67c0dc708df6169eda27fc1aabbe8d12f3b400a309e4e8b3660`, rule `631ba692610711d5f8672ebefd730c916fbc818a7d300c03d068e66490599b21`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1REQAWH6XKJZC4DXSY8XB@v5"}` · dimension `metabolic_stability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Number of renal function strata at which dosing is restricted · subject `[{}]` · unit `count of renal function strata restricted` · `quantitative` · aggregated by `consensus` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `b5e9b4d1a1337f5cbda01c780de9a769fef39dc03cf4f4298a8ed7d68a6610cb`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `f91f7d6c5739aedfdb1874f7721117fdb619121a4de7836617d4b58847ffe488`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The number of the four renal function strata, mild, moderate and severe impairment and end-stage disease including dialysis, at which the source states for this compound that a dose reduction is required or that use is contraindicated or not recommended: an integer from 0 to 4. A stratum counts only where the source itself names it. A restriction stated purely as a measured cut, such as a creatinine clearance or filtration-rate figure with no stratum named, is recorded with its threshold and is not assigned to a stratum, because no cited quote supplies the correspondence between a numeric cut and the named strata; the strata such a restriction might cover are left untested in the count and the threshold travels with the value for a later stage to read. Where the source names a stratum and also gives its cut, for example end-stage disease with a stated filtration-rate figure, the restriction counts for that named stratum and the figure is recorded. A stratum for which the source reports no data is recorded as untested and counted neither as restricted nor as unrestricted, and a stratum counts as unrestricted only where the source states that no adjustment is needed for it. The count is reported with the number of strata actually covered, so a partial count is never read as a complete one. Only data for an orally administered small molecule of the kind this objective concerns are used, and an adherence or persistence measure is not a dosing restriction and is never counted. Fewer restricted strata is better.

- **unit** `count of renal function strata restricted` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `consensus`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates usable across the renal function strata rank above candidates restricted at several of them, with each stated threshold visible in the record, which matters because the cited evidence describes renal effects as an on-target consequence of inhibiting the required vascular receptors, so renal function may deteriorate on treatment.
- **falsification test**: Check that every counted restriction is stated for a named stratum and that strata with no data are recorded as untested. If most candidates have data for only one or two strata the counts are not comparable and must be reported with their coverage rather than ranked; if a candidate scores 0 only because no stratum has been studied, the attribute must return unknown instead of a favourable count.
- **rationale**: The cited quotes give restrictions in the two forms this definition distinguishes. One names the strata directly: adjustment is not needed for mild to moderate impairment, while no data are available for severe impairment, stated with a creatinine clearance of 30 mL/min, or for end-stage renal disease, so two strata are unrestricted on reported data and two are untested. Another names a stratum and a cut together, use not recommended in end-stage renal disease at a stated filtration rate, alongside a contraindication stated only as a filtration-rate cut; the first counts for the named stratum and the second is recorded with its threshold rather than assigned to mild, moderate or severe, because nothing cited maps a numeric cut onto those names. The quotes also state that renal elimination of unchanged drug is comparatively minor for many agents of this class while the renal contribution is agent-specific, which is why this must be looked up for each candidate rather than assumed. A quote reporting consistent persistence rates across filtration-rate groups for a parenterally administered antibody has been removed from the support: persistence is an adherence measure rather than a dosing restriction, and the agent is outside the oral small-molecule comparison this objective concerns. No cited quote states an acceptable number of restricted strata, so the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `7ef456c3a5278dfc5ab57faa2f04b43e121c8b8d338d79e39c3848c1922de687` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"renal impairment\" OR \"creatinine clearance\" OR \"glomerular filtration\" OR \"end-stage renal\" OR dialysis) AND (dose OR adjustment OR contraindicat* OR pharmacokinetic*)", "relevance_terms": ["renal impairment", "creatinine clearance", "glomerular filtration", "dose adjustment"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 4 cited claim(s), 4 carry `location.span_checked_against_source: true` and 4 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 2, `value_not_in_quote` 0, not recorded 2 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 4}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 2, "supports": 2}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TZM5C3RMHZ9QZEGATZ1XXG** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > In oncology patients, who frequently exhibit an altered hepatic functionality, this first-pass effect can further complicate TKI dosing. Variability in hepatic transporter proteins, such as OATPs (organic anion transporting polypeptides), may modulate drug absorption and elimination, resulting in altered pharmacokinetic profiles that require careful dose adjustments based on individual metabolic status
  - as recorded (paraphrase): Altered hepatic function in oncology patients complicates dosing, and variability in hepatic uptake transporters modulates absorption and elimination so that dose adjustment by individual metabolic status is required.
  - in `src_doi_10.3390/ph18070959` at `paragraph` `sec3.3.p1`, section 3. Pharmacokinetic Drug–Drug Interactions / 3.3. DDIs Affecting TKI Metabolization; document `art_e9c956a4dc7b` sha256 `e9c956a4dc7b2e7da4ec02d0d8ec260cd2ffb32e2749b82fcd654a8b87d3462a`; claim `art_ed31b4456714` sha256 `ed31b4456714032f9cbeee693e7240f4e89bbe588514fd2009af1fc2b17ceb82` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 888
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`
- **claim_01M4V00PF94HP0WXW68SB7NS6F** · `conflicts` · evidence `reference_text` · determination `asserted` · value `{"unit": "mL/min/1.73 m2 eGFR threshold", "unit_as_reported": "mL/min/1.73 m2 eGFR threshold", "value": 30, "value_high": null, "value_low": null}`
  > Baricitinib is contraindicated in patients with chronic kidney disease with an eGFR <30 mL/min/1.73 m². However, for COVID-19 patients, baricitinib is not recommended for patients with end-stage renal disease with an eGFR <15 mL/min/1.73 m². Furthermore, baricitinib is not recommended for patients with severe hepatic impairment.
  - as recorded (paraphrase): The agent is contraindicated in chronic kidney disease with estimated glomerular filtration rate below 30 mL/min/1.73 m2, not recommended below 15 in one indication, and not recommended in severe hepatic impairment.
  - in `src_nbk_NBK572064` at `paragraph` `article-132927.s6.p2`, section Contraindications; document `art_f09893a5f2a3` sha256 `f09893a5f2a38c249a46c0d73fe003e5e19bc338cb246c20f56f53cda70dc87b`; claim `art_fb7ca329dccb` sha256 `fb7ca329dccb67cd54a0c7ef967129260083f3f04b5829947f4333bd2ebd3fbe` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1046
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

*polarity `supports`*

- **claim_01M4TY1RKFEC4TH490MSH42QPM** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": "mL/min creatinine clearance", "unit_as_reported": "mL/min creatinine clearance", "value": 30, "value_high": null, "value_low": null}`
  > Renal impairment: Adjustment of the nintedanib dosage for mild to moderate renal impairment is not needed. There is no available data regarding nintedanib administration for patients with severe renal impairment (CrCl <30 mL/min) and end-stage renal disease.
  - as recorded (paraphrase): No dose adjustment is needed for mild to moderate renal impairment and there are no data for severe renal impairment below 30 mL/min creatinine clearance or end-stage renal disease.
  - in `src_nbk_NBK585049` at `paragraph` `article-143222.s4.p7`, section Administration; document `art_d6f5f137dcb6` sha256 `d6f5f137dcb662288deb6e65d17790449f04dce1f0a228cee80848efe41da003`; claim `art_efa0f959f408` sha256 `efa0f959f408f39a6af348b70073c32b8484b3d1b67bd4b38f1e2e41b903d04d` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 363
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYZ67EZVH1PQV6BX6E0SC1** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Most oral anticancer agents are highly protein-bound, and only the unbound fraction is pharmacologically active and available for distribution, metabolism, and elimination. Because hepatic metabolism dominates the clearance of most of these agents, hepatic impairment is a frequent determinant of altered exposure and a common basis for dose adjustment. Renal elimination of unchanged drug is comparatively minor for many oral targeted agents, though renal contribution and the disposition of active metabolites are agent-specific.
  - as recorded (paraphrase): Most oral anticancer agents are highly protein-bound with only the unbound fraction pharmacologically active, hepatic metabolism dominates clearance so hepatic impairment commonly requires dose adjustment, and renal elimination of unchanged drug is comparatively minor though agent-specific.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec4.5.p1`, section 4. Pharmacokinetic Determinants of Oral Anticancer Drug Exposure / 4.5. Protein Binding, Hepatic Function, and Renal Contribution; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_6ae400f8e0e8` sha256 `6ae400f8e0e852a1ed5428f5a030f19403453ef828a393c1e769cbc7718df601` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 668
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage `cri_01M4V1REQAWH6XKJZC4DXSY8XB` at version `5`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for metabolic_stability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · Restated as a quantity with a unit, as the schema requires of a literature-bound attribute: the count of renal function strata, from 0 to 4, at which the source states a reduction or a prohibition. The stated creatinine-clearance or filtration-rate thresholds are recorded rather than entered, so measures expressed differently never need to be ordered against each other, and a stratum with no data is counted neither way and reported as untested.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The falsification test requires that 'every counted restriction is stated for a named stratum', but this quote states its restrictions by measured cut alone, 'contraindicated in patients with chronic kidney disease with an eGFR <30 mL/min/1.73 m2 ... not recommended for patients with end-stage renal disease with an eGFR <15'. Assigning an eGFR cut to the mild, moderate or severe stratum needs a correspondence no cited quote supplies.; The quote reports 'consistent persistence rates across variou
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · A stratum now counts only where the source names it, so a restriction stated purely as a measured cut is recorded with its threshold rather than assigned to a stratum the evidence does not name, while a restriction that names a stratum and gives a cut counts for that stratum. The persistence quote for a parenterally administered antibody is dropped: persistence is an adherence measure, not a dosing restriction, and the agent is outside the oral small-molecule comparison.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 26. Number of required receptors named as covered in the literature

- **attribute** `attr_number-of-required-receptors-named-as-covered-in-the-literat@v1` · **rule** `rule_number-of-required-receptors-named-as-covered-in-the-literat@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_number-of-required-receptors-named-as-covered-in-the-literat@v1"]`, rule `["rule_number-of-required-receptors-named-as-covered-in-the-literat@v1"]`; supersedes —
- **record hashes**: attribute `cd1c8accab7bd23235341b19ff5ac9b5146f583993c6be2be3272f5164e9f5b7`, rule `5faa22c99121a58b8f535857a1c6247fd63e3e34f164f458b5ac36cc55867937`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V183FY1P79KRKXTNJ80TWY@v7"}` · dimension `target_coverage`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Number of required receptors named as covered in the literature · subject `[{}]` · unit `count of required receptors` · `quantitative` · aggregated by `consensus` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement", "database_entry"]`; determination bases —
  - measurement identity `9fe9d0165670cd275b16254451d1a4d01860bd3de21efc5842b76f11b0228b12`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `57f736cbb577ceee7cef2eb4adee5ac3a141b320e29314ee8d01bbbc39fd3589`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The number of the five required receptors for which a retrieved peer-reviewed or reference source states that this single molecule inhibits or binds the receptor. A receptor counts when the source names it either by its protein name or by an unambiguous gene symbol or long-standing synonym, namely CSF1R, c-FMS or FMS for the colony-stimulating-factor-1 receptor; VEGFR1 or FLT1; VEGFR2 or KDR; VEGFR3 or FLT4; and FGFR1. A statement that an agent covers a receptor family without naming the isoform counts for no isoform of that family, and a statement that qualifies the engagement at a receptor as weak, minimal, negligible or absent does not count that receptor as covered. Silence is not denial and not agreement: a retrieved source that does not mention a receptor neither adds it nor removes it, so a receptor counts where at least one retrieved source names it as engaged without qualification and no retrieved source denies or qualifies engagement at that receptor. A target list that omits a receptor therefore leaves a receptor counted from another source standing, while an explicit statement of weak, minimal or absent engagement removes it. Determination basis decides a conflict: where one source names a receptor and another reports engagement at it as weak or absent, a statement whose basis is measured governs over an asserted review target list. A receptor counted only from asserted target lists, with no measured statement either way, still counts, and the number of counted receptors resting on asserted lists alone is recorded with the value so that a count assembled from review strings is visible as such. An unresolved disagreement between sources of the same basis is routed to a human. The quantity is therefore an integer from 0 to 5 measuring how completely the retrieved sources name this molecule's coverage of the required set, not how potently it engages them.

- **unit** `count of required receptors` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `consensus`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement", "database_entry"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose published target list names more of the five required receptors rank higher, and no candidate is excluded, so an agent described only at family level can still be recommended on the strength of the registry's measured potency criteria.
- **falsification test**: Score the pool and compare the ranking with the per-receptor potency criteria in the registry. If the two disagree systematically, this attribute is measuring publication practice rather than coverage and should be withdrawn. If every candidate scores the same, it discriminates nothing.
- **rationale**: The objective is a single molecule engaging five named receptors at once, and the cited quotes show that agents in this class routinely cover only part of that set: some cover the three vascular receptors without the fibroblast growth factor receptor, one covers that receptor family alone without the vascular or macrophage receptors, one is potent at the vascular receptors but inhibits the required fibroblast growth factor receptor only weakly, and one is selective for that family with minimal activity at one of the vascular receptors. Counting the receptors a source actually names, and refusing to count the ones it names only to call the engagement weak or minimal, turns that partial-coverage pattern into a quantity without equating a weak mention with potent engagement. The two quotes that reach five receptors are asserted review target strings while the restrictive quotes are measured, which is why the definition now makes determination basis decide a conflict and records how much of a count rests on asserted lists alone: an asserted list can supply a receptor, but a measured statement of weak or absent engagement at that receptor overrides it. The same asymmetry is why silence is treated as neither agreement nor denial: a target list that happens not to mention a receptor is not evidence against it, and a count must not swing on which receptors a review chose to enumerate. It measures the completeness of reporting, so a source asserting family-level coverage without isoforms scores low and that low score is a statement about the source, not about the molecule; such a candidate is not excluded and its pharmacology is carried by the five per-receptor potency criteria already in the registry, which this attribute complements and never replaces.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `43e1067f88789a4d263ed2e39ea373e1850b554a32f509100c76a7248b353954` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (CSF1R OR \"CSF-1R\" OR \"colony stimulating factor 1 receptor\" OR FMS OR VEGFR OR KDR OR FLT1 OR FLT4 OR FGFR1) AND (inhibit* OR \"target\" OR selectivity OR IC50)", "relevance_terms": ["CSF1R", "VEGFR", "FGFR1", "inhibitor", "selectivity"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 8 cited claim(s), 8 carry `location.span_checked_against_source: true` and 8 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 8 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 8}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 4, "supports": 4}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TXQQ3GXQNNE9DG8QK6E6NM** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Debio-1347 (CH5183284, zoligratinib) | Oral, highly selective, ATP-competitive FGFR1–3 inhibitor; minimal activity on KDR/VEGFR2 and most other kinases.
  - as recorded (paraphrase): An oral highly selective ATP-competitive FGFR1-3 inhibitor has minimal activity on KDR/VEGFR2 and most other kinases.
  - in `src_doi_10.2147/dddt.s559328` at `table` `table2`, section Tables; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_46bea276c6cb` sha256 `46bea276c6cbd970afcd7119e3ec640bada788d2bf6770bc860b5ab6bd4b37c8` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 202
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYG06JXTGFNNYMFCFYXM4Z** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Fruquintinib, a second‐generation RTKI, is a highly selective and potent small‐molecule inhibitor targeting VEGFR1/2/3 [87, 213, 214] with weak inhibition of RET, FGFR‐1 and KIT
  - as recorded (paraphrase): A second-generation agent is a highly selective and potent inhibitor of VEGFR1, VEGFR2 and VEGFR3 with only weak inhibition of RET, FGFR1 and KIT.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec3.1.3.2.p1`, section Review / Receptor Tyrosine Kinase Inhibitors / Theoretical Risk / Fruquintinib; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_147b8939b346` sha256 `147b8939b346676ffd5462fc1717195839d0269b6109b3dd1ddaf652f4c7ac86` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 502
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYG07WBNDBQ3R2GZ9JRE94** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Sorafenib, a multikinase RTKI, targets VEGFR2/3, PDGFR, RAF kinases (CRAF, BRAF), MEK, extracellular signal‐regulated kinase (ERK), KIT, FLT3 and RET.
  - as recorded (paraphrase): A multikinase agent targets VEGFR2 and VEGFR3, PDGFR, RAF kinases, MEK, ERK, KIT, FLT3 and RET.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec3.1.1.3.p1`, section Review / Receptor Tyrosine Kinase Inhibitors / Moderate Clinical Evidence / Sorafenib; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_d3ef920c0238` sha256 `d3ef920c023813ee3833dc3c5396ffa9c98fd0919008fad4cf695bca1de16b5b` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 504
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYG08K0MSYCE7J5XSNXGQC** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Pemigatinib, an RTKI, targets FGFR1, FGFR2 and FGFR3
  - as recorded (paraphrase): An approved agent targets FGFR1, FGFR2 and FGFR3 only.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec3.1.2.3.p1`, section Review / Receptor Tyrosine Kinase Inhibitors / Limited Clinical Evidence / Pemigatinib; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_e070d744de18` sha256 `e070d744de184ab7b09937029d7f2c8f102dfe6bd9ce00fff3dd4be3495ce86b` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 505
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

*polarity `supports`*

- **claim_01M4TXF44J2PCMZNB4X82BK66F** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Reviewing recent clinical failures, such as paxalisib and osimertinib, underscores that single-node monotherapies fail due to compensatory pathway hyperactivation and clonal heterogeneity, whereas multi-targeted agents or rational dual-node combinations prevent rapid tumor adaptation.
  - as recorded (paraphrase): Single-node monotherapies fail because of compensatory pathway hyperactivation and clonal heterogeneity, whereas multi-targeted agents or rational dual-node combinations prevent rapid tumour adaptation.
  - in `src_doi_10.3390/ijms27156590` at `abstract` `abstract.p1`, section Abstract; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_c6e57d5cd942` sha256 `c6e57d5cd9420fd147ee686dde0af1fd494c742d60388ec26a588eaa21004bb5` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 110
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYG00Q4K55KEJ4HD7YREWX** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Pazopanib, an RTKI targeting VEGFR1/2/3, PDGFR, FGFR1/3, KIT, ITK, LCK and c‐FMS, is approved for RCC and soft‐tissue sarcomas
  - as recorded (paraphrase): An approved oral receptor tyrosine kinase inhibitor targets VEGFR1, VEGFR2, VEGFR3, PDGFR, FGFR1, FGFR3, KIT, ITK, LCK and c-FMS.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec3.1.1.2.p1`, section Review / Receptor Tyrosine Kinase Inhibitors / Moderate Clinical Evidence / Pazopanib; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_4b03185b1f52` sha256 `4b03185b1f520e785ded43670a27e62dc078e4394e90f91f0c6b83ec2265fa5d` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 493
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYG021F5G6RW5MBZBT8C67** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Regorafenib, an oral multikinase RTKI, targets diverse oncogenic kinases and the angiogenic tumour microenvironment, including VEGFR1/2/3, PDGFR, FGFR1/2, TIE2, DDR2, TrkA, Eph2A, RAF1, KIT, RET, BRAF, BRAFV600E, osmotic stress/ABA‐activated protein kinase 2 (SAPK2), FRK, ABL and CSF1R
  - as recorded (paraphrase): An approved oral multikinase inhibitor targets the angiogenic tumour microenvironment including VEGFR1, VEGFR2, VEGFR3, PDGFR, FGFR1, FGFR2, TIE2 and CSF1R among other kinases.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec3.1.3.5.p1`, section Review / Receptor Tyrosine Kinase Inhibitors / Theoretical Risk / Regorafenib; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_ae9eb2fd8e2f` sha256 `ae9eb2fd8e2fdf44d49bbe6469a48aebc3b9887be7eaea48d3355d5acca468e7` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 495
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYG05YW55A4ZAPN55DY6NX** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Axitinib, an RTKI that potently inhibits VEGFR1/2/3, PDGFRβ and KIT
  - as recorded (paraphrase): An approved agent potently inhibits VEGFR1, VEGFR2, VEGFR3, PDGFR beta and KIT.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec3.1.2.1.p1`, section Review / Receptor Tyrosine Kinase Inhibitors / Limited Clinical Evidence / Axitinib; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_6219a1e249b2` sha256 `6219a1e249b2993f67eb15b16d18f7dca61128f84aa75f1b7e219312230574ac` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 501
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `unit_applicability_consistency` on attribute.acceptable_value_sources · severity `minor` · verdict `fail`: 'database_entry' remains in the source list while evidence_request binds only capability 'literature_retrieval' with question_kind 'search', which cannot return a database entry.

**Lineage and lifecycle**

- pool lineage `cri_01M4V183FY1P79KRKXTNJ80TWY` at version `7`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for target_coverage
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · rule_kind hard_exclusion with predicate_form threshold but cutoff null and cutoff_basis none_evidence_insufficient. An exclusion with no threshold cannot be executed, and this is the pool's only hard_exclusion.; This is the one quote naming all five required receptors for a single molecule. A 5-of-5 'named receptor' exclusion therefore encodes one review sentence as the pass condition, selecting a compound rather than measuring a property.; The definition counts only receptors 'named explicitly'
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · Three findings, two of them blocking, and all three are accepted. First, a hard exclusion with a null cutoff cannot be executed; combined with the second finding, that a five-of-five pass condition built on the single review sentence naming all five receptors would select a compound rather than measure a property, the correct fix is to stop excluding altogether. The rule becomes a preference with predicate_form ordering, so coverage breadth ranks candidates and nothing is rejected on how a review happened to be worded. Third, retrieval and counting disagreed: the query searched gene-symbol synonyms while the definition counted only receptors named in full, which made the c-FMS quote retrievable but uncountable. The definition now states the accepted synonyms explicitly and counts a receptor when the source names it by either its protein name or an unambiguous gene symbol. The fourth finding, that this measures completeness of reporting rather than pharmacology, is answered by renaming the attribute to say so, by recording in the rationale that a family-level statement naming no isoform counts for no isoform and that such a candidate is therefore scored low on reporting and not judged pharmacologically, and by stating that this attribute must be read alongside the registry's five per-receptor potency criteria, which carry the pharmacology. Citations are unchanged: every one is a statement of receptor coverage, which is what the attribute counts, including the partial-coverage counter-examples.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Cited as coverage evidence, but the quote names only families: 'Tinengotinib (TT-00420) is a multikinase inhibitor (FGFR, VEGFR, CSF1R)'. Under this proposal's own rule ('A statement that an agent covers a receptor family without naming the isoform counts for no isoform of that family') the quote supports a count of 1, not 5.; The quote is the fragment '(only weak inhibition of VEGFR and c-KIT has been described)'. It names no molecule and no VEGFR isoform, so it cannot raise or lower the count 
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · Dropped the family-level quote and the subject-less quote, which under this attribute's own counting rule supported no isoform. The definition now refuses to count a receptor whose engagement the source qualifies as weak, minimal, negligible or absent, so a qualified mention is not scored as equal to potent engagement. Aggregation moves from max to consensus so that the longest asserted review target list can no longer outrank narrower measured statements, with an unresolved disagreement routed to a human.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The consensus rule says 'a receptor counts only where the retrieved sources agree' but does not distinguish a source that denies a receptor from one that is silent about it. claim_01M4TYG07WBNDBQ3R2GZ9JRE94 lists 'VEGFR2/3, PDGFR, RAF kinases ... KIT, FLT3 and RET' and is simply silent on VEGFR1 and FGFR1; whether that silence blocks agreement is undetermined, and it decides whether such a candidate scores 2 or 4.; The only two claims that can reach five receptors, claim_01M4TYG00Q4K55KEJ4HD7YRE
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The consensus rule is made determinate: silence about a receptor is neither agreement nor denial, so a receptor counts where one source names it unqualified and none denies or qualifies it, which fixes the case of a target list that simply omits a receptor. Determination basis now decides a conflict, with a measured statement of weak or absent engagement overriding an asserted review target list, and the number of counted receptors resting on asserted lists alone is recorded so a count assembled from review strings is visible as such.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 27. Number of required receptors with measured rather than predicted engagement

- **attribute** `attr_number-of-required-receptors-with-measured-rather-than-predi@v1` · **rule** `rule_number-of-required-receptors-with-measured-rather-than-predi@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_number-of-required-receptors-with-measured-rather-than-predi@v1"]`, rule `["rule_number-of-required-receptors-with-measured-rather-than-predi@v1"]`; supersedes —
- **record hashes**: attribute `7a9161b17fe0fc570d1b5f25bbec57255e50543dbe506c9f81b4197a8e3d0385`, rule `3ed27df5c379d74b2ee3289458e8012903a7476fbb95344bfc561a0f8ffa10a9`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V183SH6VQ5CB7CDVW555B5@v7"}` · dimension `target_coverage`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Number of required receptors with measured rather than predicted engagement · subject `[{}]` · unit `count of required receptors` · `quantitative` · aggregated by `consensus` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "curated_measurement"]`; determination bases —
  - measurement identity `5c7dc254bcb8d4b49a47642737024ab18297877c73fe5c94bbe92c46bacda724`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `cf700352226cccb88f0e6d6c5b956dc8a2422095975e08d2df87a575a78b3ecc`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The number of the five required receptors for which engagement by this compound is supported by a direct measured readout, namely a biochemical or biophysical binding or inhibition assay, or a cellular target-engagement readout such as inhibition of receptor phosphorylation, reported for that receptor by name. Molecular docking, model-based predictions and unquantified narrative assertions do not count, and a receptor whose engagement a source reports as weak, minimal or absent does not count as measured engagement even where the statement is itself a measurement, because the count is of receptors shown to be engaged. Values are taken by consensus across the retrieved sources rather than from the most generous one: a receptor counts where a retrieved source reports a measured readout at it and no retrieved source of the same basis contradicts that, so one source asserting measurement at all five cannot set the count where other sources report only docking or prediction for some of them, and an unresolved disagreement is routed to a human. An integer from 0 to 5; higher is better.

- **unit** `count of required receptors` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `consensus`
- **accepted evidence kinds** `["peer_reviewed", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose coverage of the required receptors is backed by measurement at more of those receptors rank above candidates whose target list is asserted or modelled, which guards the coverage counts against inflation by narrative review statements.
- **falsification test**: If determination basis cannot be read reliably from the retrieved text the count is guesswork and the attribute must be withdrawn rather than estimated; if every candidate scores 5 it discriminates nothing.
- **rationale**: Two cited quotes state the rule this attribute enforces: docking-guided target assignment generates testable hypotheses about pocket accommodation but should not be presented as proof of direct inhibition without biochemical, biophysical or cellular target-engagement evidence, and where direct biochemical inhibition was not reported a compound should be regarded as a pathway modulator rather than a confirmed kinase inhibitor. Two further cited quotes are worked instances of what does count, both at required receptors and both on a measured basis: one agent is reported to inhibit the required fibroblast growth factor receptor together with two others of its family at low nanomolar inhibitory concentrations, and another is reported as a potent and selective inhibitor of all three required vascular receptors while inhibiting the fibroblast growth factor receptor only weakly. That pair also shows why the count must be per receptor and why a weak statement cannot count: the same source credits three receptors with measured potent engagement and one with weak engagement. Aggregation is consensus rather than a maximum, because a maximum would let one source asserting measurement at all five set the count while other retrieved sources report only docking for some of them, which is the same gap the coverage count closes. No cited quote states a required number of measured receptors, so the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `0749c49ecb23e52401ee4a9a44f7d2287896b078dc53bedc0f5cfa89f11b8961` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"target engagement\" OR \"biochemical assay\" OR \"enzyme inhibition\" OR \"binding assay\" OR phosphorylation) AND (CSF1R OR VEGFR OR FGFR1)", "relevance_terms": ["target engagement", "biochemical", "binding assay", "phosphorylation"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 4 cited claim(s), 4 carry `location.span_checked_against_source: true` and 4 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 4 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 4}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 1, "supports": 3}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TYG06JXTGFNNYMFCFYXM4Z** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Fruquintinib, a second‐generation RTKI, is a highly selective and potent small‐molecule inhibitor targeting VEGFR1/2/3 [87, 213, 214] with weak inhibition of RET, FGFR‐1 and KIT
  - as recorded (paraphrase): A second-generation agent is a highly selective and potent inhibitor of VEGFR1, VEGFR2 and VEGFR3 with only weak inhibition of RET, FGFR1 and KIT.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec3.1.3.2.p1`, section Review / Receptor Tyrosine Kinase Inhibitors / Theoretical Risk / Fruquintinib; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_147b8939b346` sha256 `147b8939b346676ffd5462fc1717195839d0269b6109b3dd1ddaf652f4c7ac86` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 502
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

*polarity `supports`*

- **claim_01M4TYG095KQSAJK11CPP0R5ER** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "nM (low nanomolar IC50)", "unit_as_reported": "nM (low nanomolar IC50)", "value": null, "value_high": null, "value_low": null}`
  > Infigratinib, an RTKI, inhibits FGFR1, FGFR2 and FGFR3 with low nanomolar IC50 values, showing reduced FGFR4 activity.
  - as recorded (paraphrase): An agent inhibits FGFR1, FGFR2 and FGFR3 with low nanomolar IC50 values and reduced activity on FGFR4.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec3.1.3.3.p1`, section Review / Receptor Tyrosine Kinase Inhibitors / Theoretical Risk / Infigratinib; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_93b36bf7841a` sha256 `93b36bf7841a9fabdc751493b3a1f3a8c3db2c314c5dc8b19c6590acab98e6a8` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 506
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYRS2Q0R5839WKYNVMD2DR** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Docking-guided target assignment | Thienopyridines 169, triazinones 177, and selected indolinone, quinazolinone, and pyrazole derivatives | Generates testable hypotheses regarding ATP-pocket accommodation and possible residue interactions | Should not be presented as proof of direct c-Met inhibition without biochemical, biophysical, or cellular target-engagement evidence
  - as recorded (paraphrase): Docking-based target assignment generates testable hypotheses but should not be treated as proof of direct target inhibition without biochemical, biophysical or cellular target-engagement evidence.
  - in `src_doi_10.3390/ijms27188007` at `table` `table3`, section Tables; document `art_480b68481ece` sha256 `480b68481ecefe2a1fdafb89f03b786362ce39c7543050d4150c5567f2a10d23`; claim `art_b62134f13ae2` sha256 `b62134f13ae2430c9454f39db98133b8f0664af61cc6cb75f081c78742a91106` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 617
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYRS56BYQ5JA6Q413SSDTS** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > However, direct biochemical inhibition of c-Met was not reported, so the compound should be regarded as a c-Met-pathway modulator rather than a confirmed c-Met kinase inhibitor.
  - as recorded (paraphrase): Without reported direct biochemical inhibition a compound should be regarded as a pathway modulator rather than a confirmed kinase inhibitor.
  - in `src_doi_10.3390/ijms27188007` at `paragraph` `sec3.p8`, section 3. Natural Products as Lead Scaffolds for c-Met Inhibitor Discovery; document `art_480b68481ece` sha256 `480b68481ecefe2a1fdafb89f03b786362ce39c7543050d4150c5567f2a10d23`; claim `art_c34a7f656824` sha256 `c34a7f656824754547db567cdb83ef2ceb1a1d754f64e7c79ca73a4f8bcccad3` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 621
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage `cri_01M4V183SH6VQ5CB7CDVW555B5` at version `7`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for target_coverage
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The validator finding is accepted and the quantity is made numeric with a unit while keeping the item's meaning. Instead of a qualitative determination of whether engagement rests on measurement rather than prediction, the attribute now counts how many of the five required receptors have engagement supported by a direct measured assay, an integer from 0 to 5 with the unit 'count of required receptors', direction higher_better, ranked by ordering with no cutoff. The definition states which readouts count as measured, a biochemical or biophysical assay or a cellular target-engagement readout, and which do not, docking, model predictions and unquantified narrative assertions, so the count is reproducible. Citations are unchanged: both of the central quotes state the measurement-over-prediction rule explicitly.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · This fold-selectivity quote about 'wild-type FLT3 and FLT3-D835Y' concerns neither a required receptor nor the determination basis of engagement, which is what this attribute counts; it does not support the attribute.; The quote opens 'At high clinical concentrations in purified enzyme assays, it demonstrates broad-spectrum kinase inhibition, including DDR1, FGFR1 ... VEGFR2'. The subject is a pronoun with no molecule named in the quote, so the two required receptors it would credit cannot be bo
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · Removed the fold-selectivity quote, whose endpoint is a kinase outside the required set and which speaks to selectivity rather than to determination basis, and the quote whose subject is a pronoun, whose receptors cannot be attributed to a candidate from the quote alone. The remaining two quotes are exactly the rule the attribute counts: docking is not proof of inhibition, and unreported direct inhibition means pathway modulator rather than confirmed inhibitor.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Both cited quotes concern c-Met and state only what does not count. No cited claim records a measured engagement at CSF1R, VEGFR1, VEGFR2, VEGFR3 or FGFR1, so the attribute's numerator has no worked instance in the evidence supplied and I cannot judge whether a count above zero is obtainable.; Aggregation remains 'max' with direction higher_better, so one source asserting measured engagement at all five receptors sets the count to 5 even where other retrieved sources report only docking. Proposa
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The numerator now has worked instances in the cited evidence: two measured quotes at required receptors are added, one reporting low nanomolar inhibition of the required fibroblast growth factor receptor and one reporting potent selective inhibition of all three required vascular receptors with weak inhibition of the fibroblast growth factor receptor, and the definition states that a weak, minimal or absent reading does not count as measured engagement. Aggregation moves from max to consensus, so one source asserting measurement at all five can no longer set the count against sources reporting only docking.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 28. Oral doses required per day

- **attribute** `attr_oral-doses-required-per-day@v1` · **rule** `rule_oral-doses-required-per-day@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_oral-doses-required-per-day@v1"]`, rule `["rule_oral-doses-required-per-day@v1"]`; supersedes —
- **record hashes**: attribute `0128c74e87bedaf161a7310f631117625b54e4da14f89b9277c8d8d2a72a6bea`, rule `98202a2750f800d12812d41cccfacc0594d3f8b2c455a8c24e38bd78c871addc`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1FPNS49CC25EG1F3KEK2X@v7"}` · dimension `oral_bioavailability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Oral doses required per day · subject `[{}]` · unit `doses per day` · `quantitative` · aggregated by `max` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `7d58a63b4a2e7bb579dfcc6246009c9446033e1ccbd948593661482cfa153717`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `f5e930b160a0891342da2bb884cce500731e9a6f9b5c22c9ad0d2afecb812eb3`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The number of oral doses of the compound required per day at the recommended regimen, as an integer, recorded together with two qualifiers that are not scored here: whether the regimen requires intermittent on-off cycling rather than continuous dosing, and whether a timed food-free window must be observed around each dose. A value is admitted only where the quote reporting the regimen names the molecule it belongs to; a dose statement in a quote whose subject is a pronoun cannot be attributed to a candidate and is discarded, which is the same admission rule the measured bioavailability attribute applies. Fewer doses per day is better. The qualifiers are recorded so that a later stage can see the whole burden without the scored quantity losing its ordering.

- **unit** `doses per day` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `max`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates dosed once daily rank above candidates dosed twice daily, with intermittent cycling and food-free windows visible as qualifiers rather than silently folded into the score.
- **falsification test**: If dose frequency is set by toxicity management rather than by pharmacokinetics the attribute belongs to the safety dimension and should be moved there; if every candidate is dosed once daily it discriminates nothing.
- **rationale**: The cited quotes give regimens actually used in this class, with the molecule named in the quote, which is what makes the quantity measurable and attributable: one agent's typical recommended dosage is 150 mg twice daily, and one requires strict fasting with no food for a defined window either side of the dose, with its capsule and tablet instructions differing. The objective is a chronically administered oral agent, so the number of doses a day is a property of the regimen the candidate would carry. Quotes whose subject is a pronoun, such as a daily oral dose stated for an unnamed molecule, are now inadmissible and have been removed from the support, which applies here the same evidence standard as the measured bioavailability attribute; a quote reporting the monthly cost of therapy and one stating only that these agents are effective taken orally were removed earlier as off-endpoint. No cited quote states an acceptable dose frequency, so the rule is an ordering with no cutoff, and the cycling and food-window qualifiers are recorded rather than folded into the score.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `573c15ec510d16b09f2adc3bd02dd9d4194d98236cc06cdf43c3383e3265f78d` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"once daily\" OR \"twice daily\" OR \"weeks on\" OR \"drug holiday\" OR \"dosing schedule\" OR \"recommended dose\") AND (oral OR regimen)", "relevance_terms": ["once daily", "twice daily", "dosing schedule", "oral dose"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 2 cited claim(s), 2 carry `location.span_checked_against_source: true` and 2 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 1, `value_not_in_quote` 0, not recorded 1 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 2}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 1, "supports": 1}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TYZ6B42DA4F3FDKYFB64B4** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Cabozantinib | Multikinase TKI | Food raises exposure | Empty stomach: ≥1 h before/2 h after | Strict fasting; tablets and capsules not interchangeable
  - as recorded (paraphrase): For one multikinase agent food raises exposure so strict fasting is required, and its tablet and capsule formulations are not interchangeable.
  - in `src_doi_10.3390/pharmaceutics18091082` at `table` `table1`, section Tables; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_8a1cd77e142f` sha256 `8a1cd77e142f59897c3b533015d14fc7246f7a3fbdca287358649ad7704ac30e` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 679
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`

*polarity `supports`*

- **claim_01M4TY1RASMQG6HVYS7ES2WCPG** · `supports` · evidence `reference_text` · determination `measured` · value `{"unit": "mg twice daily", "unit_as_reported": "mg twice daily", "value": 150, "value_high": null, "value_low": null}`
  > The typical recommended dosage is 150 mg twice daily.
  - as recorded (paraphrase): The typical recommended oral dosage is 150 mg twice daily.
  - in `src_nbk_NBK585049` at `paragraph` `article-143222.s4.p4`, section Administration; document `art_d6f5f137dcb6` sha256 `d6f5f137dcb662288deb6e65d17790449f04dce1f0a228cee80848efe41da003`; claim `art_7d8deab6f130` sha256 `7d8deab6f1306e4f3d2e71b52fda874673e31dee72fffd4547c12677f8a9d3e8` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 348
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `evidence_support` on supporting_claim_ids · severity `minor` · verdict `fail`: After the removals only claim_01M4TY1RASMQG6HVYS7ES2WCPG ('The typical recommended dosage is 150 mg twice daily') yields a frequency; claim_01M4TYZ6B42DA4F3FDKYFB64B4 supplies only the food-free window qualifier, so no once-daily instance remains in the cited set and the axis has one value.

**Lineage and lifecycle**

- pool lineage `cri_01M4V1FPNS49CC25EG1F3KEK2X` at version `7`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for oral_bioavailability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - round `run_01M4V43E8GDH8GF8M633VTWDQJ` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The validator finding is accepted and the quantity is made numeric with a unit: the attribute is now the number of oral doses required per day, an integer with the unit 'doses per day', which the cited evidence reports directly for every agent it describes. The schedule constraints that the original item bundled into an ordinal judgement, intermittent on-off cycling and timed food-free windows, are retained as recorded qualifiers beside the value rather than mixed into the scored quantity, so the ordering is well defined and the information is not lost. Fewer doses per day is better, with the adherence argument from the cited evidence given as the justification.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Cited for doses per day, the quote is about cost: 'Kinase inhibitor therapy ranges from $5000 to $10,000 per month or more in the United States.' It carries no dose frequency and belongs to a different endpoint entirely; claim_01M4TX98YJ9MMHF68978W0DDBW states only that TKIs work orally.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · Dropped the monthly-cost quote, which carries no dose frequency and belongs to a different endpoint, and the quote stating only that these agents work orally. The rationale now rests on the four quotes that actually report regimens, and the attribute is otherwise unchanged.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · claim_01M4TXXAGMJ3MB3W09X5J9N5ST and claim_01M4TXXAKE2M7CD5P2HH91XNNS have pronoun subjects ('It is administered in a daily oral dose of 140 mg'), and unlike proposal 7, which now discards a value 'in a quote whose subject is a pronoun', this definition adds no named-subject rule. The same evidence standard is applied in one attribute and not the other.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The named-subject admission rule is added, matching the measured bioavailability attribute: a regimen stated in a quote whose subject is a pronoun cannot be attributed to a candidate and is discarded, and the two pronoun-subject quotes are dropped from the support, leaving the quote that names its molecule with a twice-daily dosage and the quote recording a fasting window with differing capsule and tablet instructions.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 29. Proportion of patients requiring a dose reduction

- **attribute** `attr_proportion-of-patients-requiring-a-dose-reduction@v1` · **rule** `rule_proportion-of-patients-requiring-a-dose-reduction@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_proportion-of-patients-requiring-a-dose-reduction@v1"]`, rule `["rule_proportion-of-patients-requiring-a-dose-reduction@v1"]`; supersedes —
- **record hashes**: attribute `7d714c2c8cdde236d5c7e09b56748717ae313ac0c0900d75a9d2c37c22c5717b`, rule `68d20b2a7f23cbb767d012317ea60338f190d12f2b604f8c7200543c0adeec53`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V2221RQK6JQTYPA8X2BC36@v6"}` · dimension `toxicological_safety`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Proportion of patients requiring a dose reduction · subject `[{}]` · unit `% of patients with a dose reduction` · `quantitative` · aggregated by `consensus` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `4dc423fe77f280894cb7a806d20aa76a2690b32f271c6d797fc63ed632d595d1`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `3b2a46a4db7d6b6348ca1f44a3668ab5bac31facbf6c74f77b5dcd776e6675b0`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The proportion of patients requiring at least one dose reduction, as a percentage. Only the dose-reduction proportion is entered, because sources report reductions, interruptions and discontinuations as separate overlapping proportions and combining them double counts patients; the interruption and discontinuation proportions are recorded alongside the value and are not entered. The relative dose intensity actually achieved is a different quantity whose better direction is the opposite of this one, so it is recorded with the value and never placed on this axis. Values are taken by consensus across sources that define the modification identically; the cited evidence states that reporting of dose intensity, reductions and discontinuation is inconsistent across trials and precludes quantitative pooling, so incomparably defined values are not pooled into one number and an unresolved disagreement is routed to a human. Lower is better.

- **unit** `% of patients with a dose reduction` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `consensus`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose effective dose can be sustained rank above candidates that most patients must step down from, linking this dimension back to delivered target coverage, with interruption, discontinuation and achieved dose intensity visible in the record rather than mixed into the score.
- **falsification test**: The claims note that reporting of dose intensity and modification is inconsistent across trials and often precludes pooling; if the retrieved values are not comparably defined the attribute must be reduced to a qualitative determination.
- **rationale**: One cited quote supplies the quantity for an agent of this class and shows why only one of the three proportions can be scored: dose reductions, interruptions and discontinuations are reported separately, in 64.3, 66.2 and 18.8 percent of patients, and those proportions overlap, so combining them would double count patients while scoring the reduction proportion alone is well defined. The other cited quote is the counter-evidence that sets this attribute's aggregation: reporting of dose intensity, dose reductions and treatment discontinuation was inconsistent across trials, precluding quantitative pooling, which is why values are taken by consensus across sources that define the modification identically rather than pooled into a median, and why an unresolved disagreement is routed to a human. Quotes previously cited have been removed because they yield no dose-reduction proportion: one reports efficacy endpoints with only qualitative toxicity content, one recommends that reduction or interruption be considered for persistent gastrointestinal symptoms without giving a rate, and two state in general terms that toxicity limits dose intensity. The objective is an agent that must be held at an effective dose to deliver the coverage this screen selects for, which is what makes the proportion needing a reduction a criterion rather than a convenience, and no cited quote states an acceptable rate, so the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `1c6200e96ba60586d097d4e1172e74bb9e6c363386664a89193cf028ff71853d` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"dose reduction\" OR \"dose interruption\" OR \"dose modification\" OR \"relative dose intensity\") AND (percent OR % OR patients OR rate)", "relevance_terms": ["dose reduction", "dose interruption", "relative dose intensity"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 2 cited claim(s), 2 carry `location.span_checked_against_source: true` and 2 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 1, `value_not_in_quote` 0, not recorded 1 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 2}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 2}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4V09QK4VJB736ZMANTZ45WQ** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Reporting of dose intensity, dose reductions, and treatment discontinuation due to adverse events was inconsistent across trials, precluding quantitative pooling. Available trial-level data suggest that hypertension, proteinuria, and dermatologic toxicity were among the most frequent reasons for treatment modification.
  - as recorded (paraphrase): Reporting of dose intensity, dose reduction and discontinuation was inconsistent across trials, but hypertension, proteinuria and dermatologic toxicity were among the most frequent reasons for treatment modification.
  - in `src_doi_10.32604/or.2026.078524` at `paragraph` `sec3.3.p1`, section Results / Dose Intensity and Treatment Modifications; document `art_24d34d336ae8` sha256 `24d34d336ae8f45bdd1335abc021c757a77b737cd7c5efcbe87506e9a1b1338f`; claim `art_f8d2e80d0d97` sha256 `f8d2e80d0d9793f4dc28d35716ae5999c8b86762226ebb53a403294ab37bfe0c` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1152
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`
- **claim_01M4V0DJ45DJXF0FWWCRT2M30M** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% dose reductions", "unit_as_reported": "% dose reductions", "value": 64.3, "value_high": null, "value_low": null}`
  > Adverse events, most commonly hand–foot skin reaction (the principal driver of dose modification), diarrhea, alopecia, rash, fatigue, weight loss, and hypertension, occurred in 98.6% of treated patients, with dose reductions, interruptions, and discontinuations in 64.3%, 66.2%, and 18.8%, respectively.
  - as recorded (paraphrase): For the agent without FGFR coverage, adverse events occurred in 98.6% of patients with dose reductions in 64.3%, interruptions in 66.2% and discontinuations in 18.8%, hand-foot skin reaction being the principal driver of dose modification.
  - in `src_doi_10.1002/cai2.70078` at `paragraph` `sec5.1.p3`, section Systemic Therapy: Evidence‐Based Approaches and Sequential Strategies / Multitargeted VEGFR‐TKIs; document `art_e6a50d504115` sha256 `e6a50d50411565dcb2beef0b6cd9f260fa01b5e5e7bdb0087cd27cb8c4a85b97`; claim `art_4d177b7a62bf` sha256 `4d177b7a62bf1a5ca572f2bad91cbf08947c392ad4055e53d1f0b208ac3735bf` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1175
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage `cri_01M4V2221RQK6JQTYPA8X2BC36` at version `6`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for toxicological_safety
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Structured value 64.8 carries unit '% objective response rate' - an efficacy endpoint. On an attribute measuring the percentage requiring dose modification, with lower_better, a high response rate would be scored as a high toxicity burden.; The definition bundles two quantities with OPPOSITE polarity - 'Lower modification rates and higher achieved dose intensity are better' - under one unit and one lower_better ordering. A relative-dose-intensity value entering this scale is ranked backwards.; T
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Two quantities with opposite directions are bundled: 'Lower modification rates and higher achieved dose intensity are better', under one direction lower_better and one unit '% of patients requiring dose modification'. Relative dose intensity has no place on that axis and its preferred direction is the reverse of the declared one.; The cited claim states 'Reporting of dose intensity, dose reductions, and treatment discontinuation due to adverse events was inconsistent across trials, precluding qu
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The axis now carries one quantity, the proportion with at least one dose reduction; the overlapping interruption and discontinuation proportions and the oppositely directed relative dose intensity are recorded rather than entered, so no two quantities share the axis and nothing is double counted. Aggregation moves from median to consensus because the attribute's own cited evidence says reporting of these measures is inconsistent across trials and precludes quantitative pooling.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · This claim remains cited and its only numbers are efficacy endpoints, 'PFS gain ... (HR: 0.21)' and 'ORR ... (64.8% vs. 12.2%)', with its toxicity content qualitative. It yields no dose-reduction proportion, leaving claim_01M4V0DJ45DJXF0FWWCRT2M30M ('dose reductions, interruptions, and discontinuations in 64.3%, 66.2%, and 18.8%') as the single admissible value for a consensus aggregation.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The support is narrowed to the two quotes that do the work: the one reporting dose reductions, interruptions and discontinuations as separate overlapping proportions, which is the admissible value and the reason only reductions are scored, and the one stating that reporting of these measures is inconsistent across trials and precludes pooling, which is why aggregation is consensus. The efficacy-endpoint quote, the qualitative recommendation to consider a reduction, and the two general statements about toxicity limiting dose intensity yield no proportion and are dropped.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 30. Rate of grade 3 or higher treatment-related adverse events

- **attribute** `attr_rate-of-grade-3-or-higher-treatment-related-adverse-events@v1` · **rule** `rule_rate-of-grade-3-or-higher-treatment-related-adverse-events@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_rate-of-grade-3-or-higher-treatment-related-adverse-events@v1"]`, rule `["rule_rate-of-grade-3-or-higher-treatment-related-adverse-events@v1"]`; supersedes —
- **record hashes**: attribute `d15216f10d496d3fd2a73e62266acc13cc00ceb8fb458aa6863cb7f11811ec41`, rule `e5e02e104d53baf958069207ec7006e5deb7be6cd1948684fd30d4b01cb9e45f`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V2220CFDSQ8W8B1JV4P88Z@v6"}` · dimension `toxicological_safety`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Rate of grade 3 or higher treatment-related adverse events · subject `[{}]` · unit `% of patients` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `67aac26480cbf2fe600f548af1570fa38991604b3abc0a0ef26c697b209f9abd`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `21cdfb493cc476b07f5821449c06ba6cd2a6e84bd79b08b586821d1acb16dd52`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The proportion of treated patients experiencing at least one grade 3 or higher adverse event, as a percentage, from clinical trials graded by standard criteria. The attribution is recorded with every value and fixes which quantity it is: a treatment-related rate and an all-cause rate are the same kind of proportion but not the same quantity, so they are never pooled into one median; the median is taken within an attribution, and where both exist for a candidate the treatment-related rate governs because it is the one attributable to the agent. Only a rate for events of any kind is admitted: the incidence of one named event, such as a single organ toxicity, is a different quantity and belongs to the organ-specific attributes. The predicate is a plain ordering on the absolute rate as reported, and it is always defined. What travels with every value, rather than suspending the ordering, is the context needed to discount it: the line of therapy, the trial population, and, for a randomised trial, the control-arm rate, because the cited evidence shows control-arm rates differing by about thirty points between these trials. A ranking that turns on values from different lines of therapy is therefore ordered as reported and flagged in the record as resting on different populations, so the human decision at recommendation time can see it; conflicting values for the same candidate under the same attribution are routed to a human. Lower is better.

- **unit** `% of patients` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates with lower severe-toxicity rates rank above candidates where three quarters of patients experience a grade 3 or higher event, which is the broadest single comparator the claims make available.
- **falsification test**: Severe-event rates depend on the line of therapy and the frailty of the enrolled population, which the claims show differ markedly between these trials; if the retrieved rates come from non-comparable populations they must be read as orders of magnitude only.
- **rationale**: The cited quotes give values across agents of this class and show they span a wide range: 75.9 percent of patients with treatment-related grade 3 or higher events, all-cause rates of 61.1 and 62.7 percent against control-arm rates of 19.7 and 50.4 percent in the same trials, and 13 to 21 percent for a more selective agent. Those control arms are why the line of therapy, the population and the control-arm rate travel with every value: the same drug toxicity would otherwise look different according to the population enrolled. They are recorded as qualifiers rather than as a bar on comparison, because an attribute that refused to order most candidate pairs would rank nothing at all, and the rate as reported is still the best available summary of severe toxicity. The two attributions present in the quotes, treatment-related and all-cause, are why the definition fixes which is entered and forbids pooling them. The quotes also establish why this single number matters operationally, since grade 2 or greater events generally lead to dose interruption or reduction, and the standard grading system exists precisely to let consistent thresholds for dose adjustment and discontinuation be applied across trials. No cited quote states an acceptable rate, so the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `1ccdd1040a7b7a25014b6bd9fe860ebefa5add4fa34fafb2408003a54e8540ab` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"grade 3\" OR \"grade 3 or higher\" OR \"grade ≥3\" OR CTCAE OR \"treatment-related adverse events\") AND (percent OR % OR incidence OR patients)", "relevance_terms": ["grade 3", "CTCAE", "treatment-related adverse events", "incidence"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 5 cited claim(s), 5 carry `location.span_checked_against_source: true` and 5 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 5, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 5}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 5}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TXQQR4Q6H8X3ZPN4NG9B17** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% grade >=3 TRAEs", "unit_as_reported": "% grade >=3 TRAEs", "value": 54.1, "value_high": null, "value_low": null}`
  > TRAEs were reported in 105 patients (96.3%), and 59 (54.1%) experienced grade ≥ 3 TRAEs. The most frequent grade 3–4 events occurring in ≥5% of patients were hypertension (24.8%), stomatitis (7.3%), palmar–plantar erythrodysaesthesia (7.3%) and diarrhoea (5.5%), a pattern that was broadly comparable to that seen in other advanced solid tumour settings
  - as recorded (paraphrase): In a pooled cohort of 109 cholangiocarcinoma patients given a multikinase FGFR/VEGFR/CSF1R inhibitor, treatment-related adverse events occurred in 96.3% and grade 3 or above in 54.1%, the most frequent grade 3-4 events being hypertension in 24.8%, stomatitis 7.3%, palmar-plantar erythrodysaesthesia 7.3% and diarrhoea 5.5%.
  - in `src_doi_10.2147/dddt.s559328` at `paragraph` `sec3.5.p4`, section Clinical Efficacy & Safety / Other Novel Drugs; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_18c3ed88eb4c` sha256 `18c3ed88eb4c52b71ae01569ad346239d857ec734dc1a72638b72605a0e1771c` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 239
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) pooled cohort of 109 CCA patients · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4V0DJ3TH48MB4DJX096M03C** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% grade >=3 treatment-related adverse events", "unit_as_reported": "% grade >=3 treatment-related adverse events", "value": 75.9, "value_high": null, "value_low": null}`
  > Treatment‐related adverse events occurred in 97.3% of patients (Grade ≥ 3 in 75.9%), with hypertension and proteinuria being the most common, and 14.2% discontinued because of adverse effects
  - as recorded (paraphrase): For the agent covering VEGFR1-3 and FGFR1-4, treatment-related adverse events occurred in 97.3% of patients with grade 3 or higher in 75.9%, most commonly hypertension and proteinuria, and 14.2% discontinued because of adverse effects.
  - in `src_doi_10.1002/cai2.70078` at `paragraph` `sec5.1.p2`, section Systemic Therapy: Evidence‐Based Approaches and Sequential Strategies / Multitargeted VEGFR‐TKIs; document `art_e6a50d504115` sha256 `e6a50d50411565dcb2beef0b6cd9f260fa01b5e5e7bdb0087cd27cb8c4a85b97`; claim `art_89434e5f2819` sha256 `89434e5f2819a869912b46ab486e5069e14a7675ce9cfc5eab8131a3ad8295e0` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1174
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4V0DJ5P94K5SJS1BJ5TTVZ1** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% treatment-related grade >=3 events", "unit_as_reported": "% treatment-related grade >=3 events", "value": 57, "value_high": null, "value_low": null}`
  > Hand–foot skin reaction (Grade ≥ 3 in approximately 10%); diarrhea (most common any grade AE); hypertension (Grade ≥ 3 in 12%); fatigue (Grade ≥ 3 in 9%); decreased appetite, overlap with residual toxicities carried over from previous VEGFR‐TKI compounds, and having an impact on day‐to‐day life | Continuous oral daily dosing; vigilant surveillance for carry‐over and cumulative class toxicities; dose modifications common; treatment‐related Grade ≥ 3 events approximately 57% in updated COSMIC‐311 analysis
  - as recorded (paraphrase): For the second-line multitarget agent, grade 3 or higher hand-foot skin reaction occurred in about 10%, hypertension in 12% and fatigue in 9%, with treatment-related grade 3 or higher events in approximately 57% overall and common dose modification.
  - in `src_doi_10.1002/cai2.70078` at `table` `table3`, section Tables; document `art_e6a50d504115` sha256 `e6a50d50411565dcb2beef0b6cd9f260fa01b5e5e7bdb0087cd27cb8c4a85b97`; claim `art_daf9b289c54d` sha256 `daf9b289c54da2bd8670a7ae3709d18fc93342f72bf060d60709ac1bb3fe8132` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1179
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4V0JWTG86NZZ4E1SRM2Y6DR** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% grade >=3 adverse events", "unit_as_reported": "% grade >=3 adverse events", "value": 61.1, "value_high": null, "value_low": null}`
  > grade ≥ 3 AEs occurred in 61.1% versus 19.7% of patients with fruquintinib versus placebo; common AEs grade ≥ 3 AEs in the fruquintinib arm included hypertension (21.2%), hand‐foot syndrome (10.8%), and proteinuria (3.2%). Treatment discontinuation due to AEs occurred in 15.2% versus 5.8% of patients who received fruquintinib versus placebo; nine patients who received fruquintinib (3.2%) and two patients who received placebo (1.5%) had treatment‐emergent AEs leading to death
  - as recorded (paraphrase): Grade 3 or higher adverse events occurred in 61.1% versus 19.7% of controls, with grade 3 or higher hypertension in 21.2%, hand-foot syndrome in 10.8% and proteinuria in 3.2%, discontinuation for adverse events in 15.2% versus 5.8%, and fatal treatment-emergent events in 3.2% versus 1.5%.
  - in `src_doi_10.1111/cts.70713` at `paragraph` `sec5.1.p1`, section Key Clinical Trials / Summary of Clinical Efficacy and Safety; document `art_c39cbfdcc31e` sha256 `c39cbfdcc31ef3ea6814fce214c161303b6e692683ea6d22ad085239bd8d08b3`; claim `art_eefc08b79ccd` sha256 `eefc08b79ccd7e86496ebf4ae8d227089af91fedbba0b08adc36558b8de5cad3` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1230
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4V0JWVR3H8QGFBPKCBEZP8Z** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% grade >=3 adverse events", "unit_as_reported": "% grade >=3 adverse events", "value": 62.7, "value_high": null, "value_low": null}`
  > Grade ≥ 3 AEs were experienced by 62.7% of patients with fruquintinib versus 50.4% with placebo; common grade ≥ 3 AEs in the fruquintinib arm included hypertension (13.6%), asthenia (7.7%), and
  - as recorded (paraphrase): In the global trial grade 3 or higher adverse events occurred in 62.7% versus 50.4% of controls, with grade 3 or higher hypertension in 13.6% and asthenia in 7.7%.
  - in `src_doi_10.1111/cts.70713` at `paragraph` `sec5.1.p2`, section Key Clinical Trials / Summary of Clinical Efficacy and Safety; document `art_c39cbfdcc31e` sha256 `c39cbfdcc31ef3ea6814fce214c161303b6e692683ea6d22ad085239bd8d08b3`; claim `art_696873f4f6bb` sha256 `696873f4f6bba69750194060ecb47b36b928392c5639a3611dadf5c3f8bd49f5` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1232
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review item `q_01M4VEGWDBK98B0R5R6GD2APZ0` (`open`, blocking `True`, raised 2026-10-13T20:16:05.547Z): proposer and critic still disagree after one revision
  - inspection bundle: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "open_critic_findings": [{"check": "candidate_symmetric_scrutiny", "finding": "The formal inconsistency is resolved by keeping 'a plain ordering on the absolute rate as reported' and flagging the confound in the record. That accepts the confound into the score: the pool is still ordered on absolute rates from trials whose control arms differ 'by about thirty points', and a flag the human reads later does not remove the population difference from the ranking the attribute produces.", "proposal_index": 19, "referent": "attribute.definition", "severity": "material", "verdict": "fail"}], "pool_criterion": "cri_01M4V2220CFDSQ8W8B1JV4P88Z"}`
- unresolved proposer/critic disputes: `q_01M4VEGWDBK98B0R5R6GD2APZ0`
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `candidate_symmetric_scrutiny` on attribute.definition · severity `material` · verdict `fail`: The formal inconsistency is resolved by keeping 'a plain ordering on the absolute rate as reported' and flagging the confound in the record. That accepts the confound into the score: the pool is still ordered on absolute rates from trials whose control arms differ 'by about thirty points', and a flag the human reads later does not remove the population difference from the ranking the attribute produces.

**Lineage and lifecycle**

- pool lineage `cri_01M4V2220CFDSQ8W8B1JV4P88Z` at version `6`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for toxicological_safety
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Structured value 4 is a grade >=3 PNEUMONITIS rate for one agent, an organ-specific event. The attribute measures the composite 'at least one grade >=3 treatment-related adverse event', so this single-event rate enters as an overall severe-toxicity rate and is the lowest value in the set, making its compound look safest by an order of magnitude.; Value 61.1 is an ALL-CAUSE grade >=3 AE rate, but the definition requires treatment-related events; same for claim_01M4V0JWVR3H8QGFBPKCBEZP8Z (62.7). A
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The definition scores 'treatment-related' grade 3 or higher events, but two cited values are all-cause: 'grade >= 3 AEs occurred in 61.1% versus 19.7%' (claim_01M4V0JWTG86NZZ4E1SRM2Y6DR) and 'Grade >= 3 AEs were experienced by 62.7%' (claim_01M4V0JWVR3H8QGFBPKCBEZP8Z), against treatment-related 75.9% in claim_01M4V0DJ3TH48MB4DJX096M03C. A median pools two different attributions.; The only number here is a single-event rate, 'pneumonitis/interstitial lung disease (Grade >= 3 in approximately 4% o
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · One attribution per value: treatment-related and all-cause rates are recorded as what they are and never pooled into one median, with the treatment-related rate governing where both exist. Single-event incidences are excluded from the axis and the quote carrying only one has been dropped. The population confounding is now handled in the definition rather than only in the falsification test: line of therapy and control-arm rate are recorded, comparison is within a line, and a cross-line comparison is routed to a human.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The definition now says absolute rates are compared only within a line of therapy and that 'a comparison across lines is routed to a human', citing control-arm rates that differ by thirty points. But predicate_form is 'ordering' over one '% of patients' axis, and a comparison that must be routed to a human for most candidate pairs is not an ordering of the pool; what the attribute ranks when lines differ is left undetermined.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The predicate is now determinate: the ordering is always on the absolute rate as reported, and the line of therapy, the population and the control-arm rate travel with every value as recorded qualifiers that flag a cross-line comparison instead of suspending the ordering for most candidate pairs. Only conflicting values for the same candidate under the same attribution are routed to a human.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `disputed` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 31. Reported oral bioavailability in humans

- **attribute** `attr_reported-oral-bioavailability-in-humans@v1` · **rule** `rule_reported-oral-bioavailability-in-humans@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_reported-oral-bioavailability-in-humans@v1"]`, rule `["rule_reported-oral-bioavailability-in-humans@v1"]`; supersedes —
- **record hashes**: attribute `35151305eef3c123bd78b2c7c7b852ebc8b3c8def4f3de670153b793ac2d265e`, rule `26a152b91116929eeba306720fa2546fcbf25618ce8956a44f672ed5b335e6da`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1FPFH613S0HQAMRCSMX3Z@v7"}` · dimension `oral_bioavailability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Reported oral bioavailability in humans · subject `[{}]` · unit `% oral bioavailability` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `bda34429bb8d224f80d7244619488e4f016db0213ece84544133d9f8a3c575be`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `3899cd78657096f90f30b4fac35b95cbcf7b12a3e6b42fc65aeb59539f6b0b59`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The oral bioavailability percentage of the compound in humans as the source reports it, from clinical pharmacology sources or product labelling. The derivation is recorded with every value and the attribute makes no assumption about it: a figure stated as absolute bioavailability against an intravenous reference states its reference, while an unqualified reported bioavailability does not, and no cited quote says what reference an unqualified figure was derived against, so the two are not asserted to be the same quantity. Values are compared within a derivation. Where both exist for one candidate the absolute figure governs and the unqualified one is recorded, and where the ranking between two candidates would turn on comparing an absolute figure against an unqualified one, that comparison is recorded as resting on an unstated reference and is routed to a human rather than scored. Each value is also recorded with its prandial state and formulation, and the median is taken only across values sharing the same derivation, prandial state and formulation; values obtained under different conditions are never merged into one median, and where a candidate's labelled administration condition is known only values measured under that condition enter it, because the cited evidence contains a molecule whose absolute bioavailability runs from roughly 60 percent fasted toward 100 percent with food, so a value without its prandial state is not a property of the molecule. A value is admitted only where the quote reporting it names the molecule it belongs to; a percentage in a quote whose subject is a pronoun cannot be attributed to a candidate and is discarded, whatever its size. Higher is better.

- **unit** `% oral bioavailability` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates with high measured oral bioavailability under their own labelled administration condition rank above candidates known to be poorly absorbed, and no candidate gains rank from a fed-state value when it must be dosed fasting.
- **falsification test**: Check every retrieved value for its derivation, prandial state and formulation, and check that the quote reporting it names the molecule. If those qualifiers are unavailable for most candidates the values are not comparable and the attribute must be restricted to label-derived figures; if two values for one compound under the same qualifiers differ by more than about twofold, the conflict is routed to a human rather than averaged.
- **rationale**: This is the dimension's defining measurement and the cited quotes show it discriminates within one mechanistic class: 92 percent for one approved multi-kinase agent, 98 percent for another regardless of food, and for a third an absolute bioavailability rising from roughly 60 percent fasted toward 100 percent with food, which is dosed fasting to standardise exposure. Two of those are unqualified figures and one states its intravenous reference. Nothing in the quotes says what reference the unqualified figures used, so the attribute records the derivation, compares within it, lets the absolute figure govern where a candidate has both, and routes a cross-derivation comparison that would decide the ranking to a human instead of asserting that the two measure the same thing. The third quote is also what the prandial qualifier is for, since the swing within that one molecule is wider than the gap between the other two, which is why values measured under different prandial states are conditioned rather than pooled. A spread of this size within one class cannot be inferred from any computed descriptor, which is why this attribute governs where it and the descriptors disagree. Percentages in quotes whose subject is a pronoun are inadmissible whatever their size, which removes a low figure on the same ground as high ones, and no cited quote states a minimum acceptable bioavailability, so the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `71fee9f13f19f91c8636f0997be07c33e69ee8b00997efb4e43f26d7a83b4d2b` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"absolute bioavailability\" OR \"oral bioavailability\" OR \"bioavailability of\") AND (human* OR patients OR \"healthy volunteers\" OR percent OR %)", "relevance_terms": ["absolute bioavailability", "oral bioavailability", "human", "%"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 3 cited claim(s), 3 carry `location.span_checked_against_source: true` and 3 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 3, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 3}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 1, "supports": 2}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TYZ6BD1VREV74HX42XV9B6** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% absolute bioavailability", "unit_as_reported": "% absolute bioavailability", "value": null, "value_high": 100, "value_low": 60}`
  > erlotinib’s absolute bioavailability rises from roughly 60% fasted toward 100% with food, and it is taken fasting to standardize exposure
  - as recorded (paraphrase): One oral agent's absolute bioavailability rises from roughly 60% fasted to about 100% with food, and it is taken fasting to standardise exposure.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec5.p2`, section 5. Food Effects on Oral Anticancer Agents; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_418e4487b568` sha256 `418e4487b5680cb2c692d0012444463ff9e3b55a7ab44545bbcc900028e1a14c` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 680
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

*polarity `supports`*

- **claim_01M4TXXAH43N15Q7BMDBRQQJCQ** · `supports` · evidence `reference_text` · determination `measured` · value `{"unit": "% oral bioavailability", "unit_as_reported": "% oral bioavailability", "value": 92, "value_high": null, "value_low": null}`
  > Sorafenib is administered orally at 400 mg twice daily, with an oral bioavailability of 92 percent.
  - as recorded (paraphrase): A VEGFR1-3 multi-kinase agent is given orally at 400 mg twice daily with oral bioavailability of 92 percent.
  - in `src_nbk_NBK563230` at `paragraph` `article-28341.s9.p35`, section Treatment / Management; document `art_55e79771f56d` sha256 `55e79771f56d1e6d548de79bb180e4c496477cca454dd8e3a79d1718f5793133`; claim `art_4c8eda585bce` sha256 `4c8eda585bce3392806550f8a271ae71761be33ae0abb48f17a7dffc99a9585a` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 291
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYZ6BQ0Y6RKJ767XG0921F** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% bioavailability", "unit_as_reported": "% bioavailability", "value": 98, "value_high": null, "value_low": null}`
  > Imatinib is conventionally taken with food and water to reduce gastrointestinal upset rather than to alter exposure (its bioavailability is 98% regardless of food)
  - as recorded (paraphrase): One oral agent has 98% bioavailability regardless of food and is taken with food only to reduce gastrointestinal upset.
  - in `src_doi_10.3390/pharmaceutics18091082` at `paragraph` `sec5.p3`, section 5. Food Effects on Oral Anticancer Agents; document `art_9d479cc30be6` sha256 `9d479cc30be617a29731ae916fe10a81cea94cd4e0386e360af557a0f68074bc`; claim `art_c13cf3533ff1` sha256 `c13cf3533ff1b7f15f43c81c99c53d42afd9bb655f00c41db0a5fc9c85515e8c` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 681
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `unit_applicability_consistency` on rule.predicate_form · severity `minor` · verdict `fail`: predicate_form remains 'ordering' while cross-derivation comparisons are routed to a human, so the ordering over the pool is partial by construction. The definition is explicit about this, but what the attribute returns when the pool mixes derivations is a set of within-derivation orders rather than one ranking.

**Lineage and lifecycle**

- pool lineage `cri_01M4V1FPFH613S0HQAMRCSMX3Z` at version `7`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for oral_bioavailability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The definition requires absolute bioavailability against an IV reference, but claim_01M4TXXAG37Q6PCR1C7VED6HNG, claim_01M4TXXAH43N15Q7BMDBRQQJCQ, claim_01M4TXXAHQYTWM319EGG2ZYEH6 and claim_01M4TXXAJ8KXFRN0AW01WM4TXZ report plain 'bioavailability'; only claim_01M4TY1R88ZVK1PM3YP17YHPKD states 'absolute'. Two measurement kinds pooled under one unit.; claim_01M4TYZ6BD1VREV74HX42XV9B6 shows one molecule's absolute bioavailability moving from ~60% fasted to ~100% fed, so a single median per compound 
  - round `run_01M4V43E8GDH8GF8M633VTWDQJ` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · Both material findings are accepted. The definition demanded absolute bioavailability against an intravenous reference, but only one cited quote uses the word absolute while four report a plain bioavailability percentage whose derivation is unstated; the definition now admits reported oral bioavailability and requires each value to be recorded with whether the source called it absolute, so the two are never silently equated. The second finding is the more important: one cited quote shows a single molecule moving from roughly 60 percent fasted to about 100 percent fed, so a single median per compound conflates prandial state. The attribute now takes the value measured under the compound's own labelled administration condition, records the prandial state with every value, and forbids pooling across prandial states; where only an unconditioned value exists it is recorded as such. The falsification test, which previously mentioned formulation only, now covers prandial state and derivation as well.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The definition requires that values differing in derivation, prandial state or formulation 'are not pooled', but aggregation is 'median', which pools. As written the attribute both forbids and performs pooling; which operation applies when qualifiers differ is undetermined.; The cited values sit on two different scales that the definition distinguishes but the median would merge: 'absolute bioavailability is 4.7%' (claim_01M4TY1R88ZVK1PM3YP17YHPKD) against unqualified figures such as 'an oral bi
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The attribute now defines one quantity on one axis, percent of the administered oral dose reaching systemic circulation, states how an absolute figure against an intravenous reference and an unqualified figure relate on it, and gives the absolute figure precedence where both exist rather than averaging them. The median is defined as operating only within a matched derivation, prandial state and formulation, so the definition no longer both forbids and performs pooling. Values whose quote names no molecule are inadmissible, and the four subject-less quotes are dropped, including the 4.7 percent absolute figure, so the rule removes a low value on the same ground as high ones.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The definition asserts that an absolute figure and an unqualified reported bioavailability 'are both percentages of the administered oral dose, so they enter the same percent-of-dose axis'. The cited unqualified quotes do not state a reference, so that they measure the same quantity is an assumption rather than something any quote says; the rule that the absolute figure governs where both exist mitigates but does not establish it.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The definition no longer asserts that an absolute figure and an unqualified reported bioavailability are the same percent-of-dose quantity, which no cited quote states. The derivation is recorded, values are compared within a derivation, the absolute figure governs where a candidate has both, and a comparison across derivations that would decide the ranking is recorded as resting on an unstated reference and routed to a human.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 32. Time to steady state on repeated oral dosing

- **attribute** `attr_time-to-steady-state-on-repeated-oral-dosing@v1` · **rule** `rule_time-to-steady-state-on-repeated-oral-dosing@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_time-to-steady-state-on-repeated-oral-dosing@v1"]`, rule `["rule_time-to-steady-state-on-repeated-oral-dosing@v1"]`; supersedes —
- **record hashes**: attribute `3668c80736b1b46c454627dc47ed5f9e47a2f8f645f0916ead13851692f6e7d4`, rule `df5891d7fd380a902211d8d17a0d56882d83a67eb207d6c07b8eb6e81e9a232a`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1FPKQKVVX7QZX6223WPFY@v7"}` · dimension `oral_bioavailability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Time to steady state on repeated oral dosing · subject `[{}]` · unit `days` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `e128914b5e84c0eb5c3601657a7ba507fd10be6e277e6d7c2d0531672385fe3a`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `33549606cb7019435a7b0c1b5c110adfc551574af68716220ecae6c334cd8e03`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The time in days for systemic exposure to reach steady state on repeated oral dosing, recorded together with three qualifiers: whether the figure is a point estimate or an upper bound, whether exposure was reported to increase proportionally with dose over the clinically relevant range, and the accumulation ratio at steady state where stated. A time stated in weeks is converted before entry at seven days to the week and is flagged as the bound the source states rather than as a measurement, so a statement that steady state is attained within one week enters as 7 days flagged as an upper bound; bound-flagged values and point estimates are compared, but a tie between a bound and a point estimate within the conversion's precision is routed to a human rather than resolved by the number. Only a statement about the time to steady state is entered: a statement about dose proportionality, accumulation or the prandial state is recorded as a qualifier and never converted into a time. Shorter is better. Where only a qualitative statement of linearity exists the value is unknown with that statement noted.

- **unit** `days` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose exposure reaches steady state within days rank above candidates that accumulate over weeks, and the recorded qualifiers let a later stage see whether exposure is also dose-proportional.
- **falsification test**: If time to steady state is reported for few candidates the attribute returns unknown; and if it tracks the half-life attribute exactly it is a restatement of it and should be merged.
- **rationale**: One cited quote reports this quantity for an agent of this class: pharmacokinetics described as linear with steady-state plasma levels attained within one week. Because that figure is stated in weeks and as a bound, the definition states the conversion at seven days to the week and keeps the bound visible rather than presenting 7 days as a measured value. A second cited quote states that the interplay of the multiple processes governing pharmacokinetics and pharmacodynamics merits consideration when administering an agent of this class to titrate the optimal dosage, which is the extent of what the evidence says about why the quantity matters: it makes time to steady state relevant to dose titration, and no cited quote calls rapid stabilisation of exposure the central requirement of chronic oral dosing. Two quotes previously cited have been removed because they are on other endpoints, one describing how a meal alters the gastrointestinal environment and one stating only that these agents are effective taken orally; neither speaks to steady state, dose proportionality or accumulation. No cited quote states an acceptable time to steady state, so the rule is an ordering with no cutoff, and the linearity and accumulation qualifiers are recorded rather than scored.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `5592cc6f886eaf76bd260a80f7ea1ae530901c9f307baff2734f78d885e4475d` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"steady state\" OR \"dose proportional\" OR \"dose-proportional\" OR accumulation OR linearity) AND (pharmacokinetic* OR exposure OR AUC)", "relevance_terms": ["steady state", "dose proportional", "accumulation", "pharmacokinetics"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 2 cited claim(s), 2 carry `location.span_checked_against_source: true` and 2 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 1, `value_not_in_quote` 0, not recorded 1 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 2}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"supports": 2}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `supports`*

- **claim_01M4TX99CD37E1GDDWKR0CV75Y** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > The interplay of multiple processes regulating the pharmacokinetics and pharmacodynamics of TKIs merits consideration when administering a TKI to titrate the optimal dosage.
  - as recorded (paraphrase): The interplay of the multiple processes governing tyrosine kinase inhibitor pharmacokinetics and pharmacodynamics must be considered when titrating the optimal dose.
  - in `src_nbk_NBK563322` at `paragraph` `article-109800.s8.p3`, section Toxicity; document `art_f39aa2170bbb` sha256 `f39aa2170bbb6e797aa143c217673d26d91bf5238802cedbd23bc4621ce110fc`; claim `art_e961f691506b` sha256 `e961f691506be7781669aff577b8378b15e0ca028ef6ff985bb6196ab8385f2f` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 90
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TY1R9SWZMM96CT0BRYF2JB** · `supports` · evidence `reference_text` · determination `measured` · value `{"unit": "week to steady state", "unit_as_reported": "week to steady state", "value": 1, "value_high": null, "value_low": null}`
  > The pharmacokinetics of nintedanib are linear, with steady-state plasma levels attained within 1 week.
  - as recorded (paraphrase): The pharmacokinetics are linear and steady-state plasma levels are reached within one week.
  - in `src_nbk_NBK585049` at `paragraph` `article-143222.s3.p3`, section Mechanism of Action; document `art_d6f5f137dcb6` sha256 `d6f5f137dcb662288deb6e65d17790449f04dce1f0a228cee80848efe41da003`; claim `art_ff6c609fa062` sha256 `ff6c609fa062be3247cd3bb98111a66b96c191b4c7c1933ba4e449f05c0a7091` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 346
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `evidence_support` on claim_01M4TX99CD37E1GDDWKR0CV75Y · severity `minor` · verdict `fail`: This quote says only that the interplay of processes 'merits consideration when administering a TKI to titrate the optimal dosage'; it yields no time and leaves claim_01M4TY1R9SWZMM96CT0BRYF2JB as the sole value-bearing claim.

**Lineage and lifecycle**

- pool lineage `cri_01M4V1FPKQKVVX7QZX6223WPFY` at version `7`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for oral_bioavailability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - round `run_01M4V43E8GDH8GF8M633VTWDQJ` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The validator finding is accepted and the quantity is made numeric with a unit while keeping the item's meaning. The attribute is now the time in days to reach steady state on repeated oral dosing, which the cited evidence reports directly, with the dose-proportionality finding and the accumulation ratio recorded as qualifiers alongside the value rather than as the scored quantity. A shorter time to steady state is preferred because it is the measurable face of the predictability the item was after: exposure settles quickly, so a dose adjustment takes effect within days. The rule remains an ordering with no cutoff, since no quote states a required time.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The attribute's unit is days, but the only cited numeric statement is 'steady-state plasma levels attained within 1 week' with unit 'week to steady state'. That is an upper bound in weeks, not a measured number of days, and the definition supplies no conversion rule (contrast proposals 16 and 26, which state theirs), so entering 7 would add precision the quote does not carry.; The definition claims the cited evidence 'identifies as the central practical requirement of chronic oral dosing in this
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The weeks-to-days conversion is now stated explicitly and the converted value is flagged as the upper bound the source gives rather than presented as a measured number of days, with a tie between a bound and a point estimate routed to a human. The definition's claim that the cited evidence identifies rapid stabilisation as the central practical requirement of chronic oral dosing is removed, because no cited quote says it; the rationale now states only what the quotes support, relevance to dose titration.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · This food-effect mechanism quote says nothing about steady state, dose proportionality or accumulation, and claim_01M4TX98YJ9MMHF68978W0DDBW ('Nearly all TKIs are effective when taken orally') is equally off this endpoint. Both remain cited after the revision.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The two off-endpoint quotes are dropped, the food-effect mechanism quote and the quote stating only that these agents work orally, neither of which speaks to steady state, dose proportionality or accumulation. The definition now also states that a dose-proportionality, accumulation or prandial statement is recorded as a qualifier and never converted into a time, so nothing off the endpoint can enter the axis.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 33. Transporter-mediated change in systemic exposure

- **attribute** `attr_transporter-mediated-change-in-systemic-exposure@v1` · **rule** `rule_transporter-mediated-change-in-systemic-exposure@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_transporter-mediated-change-in-systemic-exposure@v1"]`, rule `["rule_transporter-mediated-change-in-systemic-exposure@v1"]`; supersedes —
- **record hashes**: attribute `2ad799429c828b55cc8d8ecb53d0d3fc55ff5acb19eafe45704366d20919daa0`, rule `57f02d41214eee0b94135edb6d337021181acfd7b8819d96b94b6e15b3846e97`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V1REJWG0PT878H02298YCV@v6"}` · dimension `metabolic_stability`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Transporter-mediated change in systemic exposure · subject `[{}]` · unit `fold deviation from unity` · `quantitative` · aggregated by `max` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `db4ca3c7f76a782180372806f0d9397f4c2c828c9646ec9d77f6e9edd486b804`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `c409e5d719eada920eab8bc9e002847a6f1830f4764a2d81711e8b4fa1c18e22`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The change in the compound's own systemic exposure (AUC) when a transporter inhibitor or inducer is co-administered, expressed as a ratio of at least 1 in whichever direction the change runs, so that the same factor of change scores alike whether exposure rises or falls: a doubling and a halving both enter as 2.00. The conversion is stated because the sources report percentages: a percentage increase of X enters as 1 plus X divided by 100, so a 160.5 percent increase enters as 2.61, and a percentage decrease of Y enters as 1 divided by (1 minus Y divided by 100), so a 50.1 percent decrease enters as 2.00. A percentage is never entered as a bare number, and the direction of the change and the perturbing agent are recorded with every value. A statement about blood or plasma concentrations rather than exposure, and a peak-concentration change without an exposure change, are recorded rather than entered, because they are different endpoints. Where a source reports both an inhibitor arm and an inducer arm, both are converted and retained in the record; the scored value is the larger ratio, the worst perturbation in either direction, so an exposure loss is never discarded for being a loss but only for being the smaller movement on a scale that treats the two symmetrically. A value of 1.00 means exposure is unaffected and is the best score; larger values are worse.

- **unit** `fold deviation from unity` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `max`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates insensitive to transporter modulation score near 1.00 and rank above candidates whose exposure moves substantially with a transporter inhibitor or inducer, a rise and a fall of the same factor score alike, and a low cytochrome dependence is no longer mistaken for a low overall interaction liability.
- **falsification test**: If a candidate has a low cytochrome fraction and no transporter interaction study, its interaction liability is untested rather than low, and the attribute must return unknown rather than a favourable score.
- **rationale**: The cited quotes show that for agents whose clearance avoids the cytochromes the interaction liability moves to transporters rather than disappearing: one agent metabolised mainly by a conjugating enzyme is nonetheless a transporter substrate whose exposure rose by 160.5 percent with a strong transporter inhibitor and fell by about 50 percent with an inducer, and one agent must have its dose halved with a potent transporter inhibitor. That single study is also why the scale is a fold deviation from unity rather than a percentage magnitude: on a percentage axis a doubling would enter as 100 and a halving as 50, so the same factor of change would score twice as badly as a rise as it does as a fall, and the two arms of that study are closer in factor than their percentages suggest. Converting both arms to a ratio of at least 1 makes a rise and a fall of the same factor score alike, which is the convention the food-effect attribute already uses. The quotes also record the converse case, an agent not substantially susceptible to either transporter or cytochrome interactions and therefore of minimal interaction potential, and none states an acceptable magnitude, so the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `aa19c15ec684dafe617ac44d43d3bb0c25defba2b1f8affa75b9651ddb2846ac` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (\"P-glycoprotein\" OR \"P-gp\" OR BCRP OR OAT3 OR OATP OR \"transporter inhibitor\" OR \"transporter inducer\") AND (AUC OR Cmax OR exposure)", "relevance_terms": ["P-glycoprotein", "transporter inhibitor", "OAT3", "AUC", "exposure"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 5 cited claim(s), 5 carry `location.span_checked_against_source: true` and 5 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 1, `value_not_in_quote` 0, not recorded 4 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 5}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 4, "supports": 1}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TY1REX3SM4ND6KESQHPZAD** · `conflicts` · evidence `reference_text` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Additionally, nintedanib is a substrate and weak inhibitor of P-glycoprotein and a minor substrate of CYP3A4. Patients receiving concomitant P-gp and CYP3A4 inhibitors should be closely monitored.
  - as recorded (paraphrase): The agent is a substrate and weak inhibitor of P-glycoprotein and a minor CYP3A4 substrate, so patients on concomitant P-gp and CYP3A4 inhibitors need close monitoring.
  - in `src_nbk_NBK585049` at `paragraph` `article-143222.s3.p5`, section Mechanism of Action; document `art_d6f5f137dcb6` sha256 `d6f5f137dcb662288deb6e65d17790449f04dce1f0a228cee80848efe41da003`; claim `art_c678aa13a219` sha256 `c678aa13a2193788cd57fc35a9c0454a8507680e63594f75d6db6a6386185d80` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 355
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TZRMB1MJFHHM23N5128K89** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% increase in Cmax and AUC", "unit_as_reported": "% increase in Cmax and AUC", "value": 160.5, "value_high": null, "value_low": null}`
  > Nintedanib is a substrate of P-gp, and according to a phase I study in healthy subjects (38), co-administration of ketoconazole (a strong P-gp inhibitor) led to an increase in nintedanib Cmax and AUC by 160.5% and 160.5%, respectively; conversely, rifampicin (a strong P-gp inducer) decreased its Cmax and AUC by 59.8% and 50.1%, respectively
  - as recorded (paraphrase): That agent is a P-glycoprotein substrate whose Cmax and AUC rose by 160.5% with a strong P-glycoprotein inhibitor and fell by 59.8% and 50.1% with a strong inducer in a phase I study in healthy subjects.
  - in `src_doi_10.3389/or.2025.1612249` at `paragraph` `sec2.1.7.p1`, section 2 Results / 2.1 Lung cancer / 2.1.7 Nintedanib; document `art_25fa3c4c8de6` sha256 `25fa3c4c8de6f66f5a12b8a0bd0f4d3835f97671a144fda008226feb06d42e6d`; claim `art_c969f14dc44a` sha256 `c969f14dc44ad64f98eafd42bf36f8bf128794aad0b1c1f20a10c276d5fc8c21` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 938
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) phase I study in healthy subjects · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4TZRMBQY9MD4E9WEFG7T7AB** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > As a result, careful monitoring for side effects is advised when nintedanib is administered with a strong P-gp inhibitor, although dose adjustment is not typically required (37). On the other hand, given that potent P-gp inducers (e.g., rifampicin, carbamazepine, phenytoin, and St. John’s Wort) significantly lower nintedanib exposure, their concurrent use should be carefully considered
  - as recorded (paraphrase): Careful monitoring is advised with a strong P-glycoprotein inhibitor although dose adjustment is not typically required, while potent inducers that significantly lower exposure need careful consideration.
  - in `src_doi_10.3389/or.2025.1612249` at `paragraph` `sec2.1.7.p1`, section 2 Results / 2.1 Lung cancer / 2.1.7 Nintedanib; document `art_25fa3c4c8de6` sha256 `25fa3c4c8de6f66f5a12b8a0bd0f4d3835f97671a144fda008226feb06d42e6d`; claim `art_6362fa45bf0d` sha256 `6362fa45bf0df13675437670ca414d92780096b045921f1f86c0f140e99d59a3` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 939
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`
- **claim_01M4V00PEQMW3JCZTA66X81QZW** · `conflicts` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Baricitinib should not be used concomitantly with biologic DMARDs, other JAK inhibitors, or potent immunosuppressants such as azathioprine and cyclosporine. The coadministration of OAT3 inhibitors can elevate baricitinib exposure. Consequently, it is recommended to reduce the baricitinib dosage by half when used in conjunction with strong OAT3 inhibitors.
  - as recorded (paraphrase): The agent must not be used with biologic disease-modifying drugs, other inhibitors of the same kinase family or potent immunosuppressants, and the dose must be halved with a strong transporter inhibitor.
  - in `src_nbk_NBK572064` at `paragraph` `article-132927.s5.p6`, section Adverse Effects; document `art_f09893a5f2a3` sha256 `f09893a5f2a38c249a46c0d73fe003e5e19bc338cb246c20f56f53cda70dc87b`; claim `art_98e85eb8315d` sha256 `98e85eb8315d007378d914f063a485ee609fa6a92ef143239041e2c6addf0371` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1045
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`

*polarity `supports`*

- **claim_01M4TZM5N79K45R9T9TKBSBC2R** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Given that afatinib does not exhibit substantial susceptibility to efflux transporter interactions or CYP450-mediated metabolism, its potential for DDIs is considered minimal, supporting its use in combination therapy
  - as recorded (paraphrase): An agent not substantially susceptible to efflux transporter interactions or CYP450 metabolism has minimal interaction potential, supporting its use in combination therapy.
  - in `src_doi_10.3390/ph18070959` at `paragraph` `sec3.2.p3`, section 3. Pharmacokinetic Drug–Drug Interactions / 3.2. DDIs Affecting TKI Distribution; document `art_e9c956a4dc7b` sha256 `e9c956a4dc7b2e7da4ec02d0d8ec260cd2ffb32e2749b82fcd654a8b87d3462a`; claim `art_0e7407c41f01` sha256 `0e7407c41f017d2e98aadb40bb0f8aa5b0e261deed512bd54523e30ae88e631c` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 902
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `evidence_support` on claim_01M4V00PEQMW3JCZTA66X81QZW · severity `minor` · verdict `fail`: This claim is prescribing advice, 'it is recommended to reduce the baricitinib dosage by half when used in conjunction with strong OAT3 inhibitors', with no exposure change; it and claim_01M4TZRMBQY9MD4E9WEFG7T7AB and claim_01M4TZM5N79K45R9T9TKBSBC2R yield nothing on the fold axis, leaving one value-bearing claim.

**Lineage and lifecycle**

- pool lineage `cri_01M4V1REJWG0PT878H02298YCV` at version `6`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for metabolic_stability
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · unit '% change in AUC' with agg max pools claim_01M4TZRMB1MJFHHM23N5128K89 (value 160.5, a percentage) with claim_01M4V00PE48YPB3R5Z8KJCWMRW (value 2, a FOLD increase). A doubling enters the scale as '2% change' and scores best in the pool.; Quote measures 'blood levels', not AUC, and reports a fold change; the attribute's declared parameter is percentage change in AUC.; agg max with on_missing unknown_no_penalty scores a candidate that has transporter interaction studies at its worst value whil
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The declared unit is '% change in AUC', but the cited values are on mixed scales and endpoints with no stated conversion: 'increase in nintedanib Cmax and AUC by 160.5% and 160.5%' (claim_01M4TZRMB1MJFHHM23N5128K89) against 'a 2-fold increase in baricitinib blood levels' (claim_01M4V00PE48YPB3R5Z8KJCWMRW), the latter a concentration statement rather than an AUC.; Aggregation max with direction lower_better on an unsigned 'change' selects the largest increase and so discards the inducer arm of th
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · One axis with a stated sign convention and conversion: a non-negative percentage change in exposure, folds converted, and concentration-only or peak-only statements recorded rather than entered, which is why the doubling-of-blood-levels quote is dropped from the support. Both arms of a study are retained and the scored value is the larger magnitude in either direction, so an exposure loss with an inducer is treated as the same liability as a rise with an inhibitor rather than discarded as a decrease.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The definition claims 'a 50 percent loss with an inducer and a 50 percent rise with an inhibitor score alike', but the stated conversion is not scale-symmetric: a doubling enters as 100 and a halving as 50, so the same factor of two scores twice as badly as a rise than as a fall. On the cited study that is decisive, since 'increase in nintedanib Cmax and AUC by 160.5%' and 'decreased its Cmax and AUC by 59.8% and 50.1%' (claim_01M4TZRMB1MJFHHM23N5128K89) are closer in factor than the percentages
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The axis becomes scale-symmetric: the change is entered as a fold deviation from unity, with the conversion stated for both directions, so a doubling and a halving both enter as 2.00 instead of 100 and 50 and the same factor of change no longer scores worse as a rise than as a fall. This is also the convention the food-effect attribute uses, and both arms of a study are still converted and retained with the larger ratio scored.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 34. Treatment discontinuation rate due to adverse events

- **attribute** `attr_treatment-discontinuation-rate-due-to-adverse-events@v1` · **rule** `rule_treatment-discontinuation-rate-due-to-adverse-events@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_treatment-discontinuation-rate-due-to-adverse-events@v1"]`, rule `["rule_treatment-discontinuation-rate-due-to-adverse-events@v1"]`; supersedes —
- **record hashes**: attribute `d1e2e675096f99a2fa065a89e5d6c57eaf8e9d2fe0aeb9475c8ee85a45381f7e`, rule `4a634916c43787354829242ddb732a569d8a12626cfb7c5e7abd949a6c53c4ec`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V22210J1SV3PK3W8HTZ29Z@v4"}` · dimension `toxicological_safety`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: Treatment discontinuation rate due to adverse events · subject `[{}]` · unit `% of patients` · `quantitative` · aggregated by `median` · transform —
  - read from `["literature_retrieval"]` asking `["search"]`; evidence kinds `["peer_reviewed", "reference_text", "curated_measurement"]`; determination bases —
  - measurement identity `a932751661c09145542be35b84a8637b8368f2db42f11fd99c16c64ec7382bbb`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `lower_better`
  - predicate: orders candidates by the quantity, lower_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `route_to_human` · decision identity `725cb48f05f9bd7faeecded7545fba20e7818c7d53d389bc6010e973ad1ddde3`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: operational_quantity.subject: no route carries a subject parameter, so the quantity is identified by its unit, its direction and its name only
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The proportion of patients who permanently stopped treatment because of adverse events, as a percentage. A cessation rate that the source does not attribute to adverse events is a different quantity and is not admitted, and neither is a rate reported for a drug class other than the one under consideration. This measures whether the toxicity can be lived with, as distinct from how severe it is on paper. Each value is recorded with the line of therapy, because the cited evidence shows these trials differ in line and in the alternatives available to patients. Lower is better.

- **unit** `% of patients` · **measurement kind** `quantitative` · **direction** `lower_better` · **aggregation** `median`
- **accepted evidence kinds** `["peer_reviewed", "reference_text", "curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates patients can stay on rank above candidates abandoned by a third of their recipients, which is the practical meaning of tolerability for an agent meant to be taken continuously.
- **falsification test**: Discontinuation rates confound toxicity with the availability of alternatives: in a last-line setting patients persist with worse toxicity. If the retrieved rates come from different lines of therapy the comparison is unsafe.
- **rationale**: The cited quotes supply a graded series of adverse-event discontinuation rates for agents of this class: about 10 percent, 14, 15.2 and 18.8 percent, and they record that one agent required dose reduction in 37 percent and discontinuation in 6 percent while another required reductions in 64.3 percent, interruptions in 66.2 percent and discontinuations in 18.8 percent. Since the objective is chronic oral dosing, the rate at which patients stop is a more faithful summary of tolerability than the graded event count. One quote previously cited has been dropped: it reports treatment cessation in approximately 5 percent of patients with operable and 36 percent with advanced disease for an unrelated inhibitor class, attributes the cessation to no cause, and reading it as an adverse-event discontinuation rate would add an attribution the quote does not make. No cited quote states an acceptable rate, so the rule is an ordering with no cutoff.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `route_to_human`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `b54962facff0e4fedbdd1f55e3fc275311559334f9c623f432fd228d23b06fca` · 1 route(s) · literature-bound `True`
  - route `literature_retrieval` / `search` · subject — · retrieval `{"query_template": "({names}) AND (discontinu* OR \"treatment cessation\" OR withdraw*) AND (\"adverse event\" OR toxicity) AND (percent OR % OR rate)", "relevance_terms": ["discontinuation", "adverse event", "rate", "percent"], "search_limit": 10}` · identifier scheme —

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 4 cited claim(s), 4 carry `location.span_checked_against_source: true` and 4 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 4, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 4}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 4}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TXQQP6MGMJQ6CG95GTZ8DX** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% of patients discontinuing", "unit_as_reported": "% of patients discontinuing", "value": 10.2, "value_high": null, "value_low": null}`
  > Hyperphosphatemia was the most common TEAE (58%). Pemigatinib was discontinued in 15 (10.2%) patients due to TEAEs.
  - as recorded (paraphrase): In the updated pivotal trial, hyperphosphataemia was the most common treatment-emergent adverse event at 58% and 10.2% of patients discontinued because of treatment-emergent adverse events.
  - in `src_doi_10.2147/dddt.s559328` at `paragraph` `sec3.2.p2`, section Clinical Efficacy & Safety / Pemigatinib; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_4e422a653f31` sha256 `4e422a653f3190ffd26245dee13e866e064ad05e5c787b40adce329d64f243f0` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 235
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus (subagent)`
- **claim_01M4V0DJ3TH48MB4DJX096M03C** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% grade >=3 treatment-related adverse events", "unit_as_reported": "% grade >=3 treatment-related adverse events", "value": 75.9, "value_high": null, "value_low": null}`
  > Treatment‐related adverse events occurred in 97.3% of patients (Grade ≥ 3 in 75.9%), with hypertension and proteinuria being the most common, and 14.2% discontinued because of adverse effects
  - as recorded (paraphrase): For the agent covering VEGFR1-3 and FGFR1-4, treatment-related adverse events occurred in 97.3% of patients with grade 3 or higher in 75.9%, most commonly hypertension and proteinuria, and 14.2% discontinued because of adverse effects.
  - in `src_doi_10.1002/cai2.70078` at `paragraph` `sec5.1.p2`, section Systemic Therapy: Evidence‐Based Approaches and Sequential Strategies / Multitargeted VEGFR‐TKIs; document `art_e6a50d504115` sha256 `e6a50d50411565dcb2beef0b6cd9f260fa01b5e5e7bdb0087cd27cb8c4a85b97`; claim `art_89434e5f2819` sha256 `89434e5f2819a869912b46ab486e5069e14a7675ce9cfc5eab8131a3ad8295e0` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1174
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4V0DJ45DJXF0FWWCRT2M30M** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% dose reductions", "unit_as_reported": "% dose reductions", "value": 64.3, "value_high": null, "value_low": null}`
  > Adverse events, most commonly hand–foot skin reaction (the principal driver of dose modification), diarrhea, alopecia, rash, fatigue, weight loss, and hypertension, occurred in 98.6% of treated patients, with dose reductions, interruptions, and discontinuations in 64.3%, 66.2%, and 18.8%, respectively.
  - as recorded (paraphrase): For the agent without FGFR coverage, adverse events occurred in 98.6% of patients with dose reductions in 64.3%, interruptions in 66.2% and discontinuations in 18.8%, hand-foot skin reaction being the principal driver of dose modification.
  - in `src_doi_10.1002/cai2.70078` at `paragraph` `sec5.1.p3`, section Systemic Therapy: Evidence‐Based Approaches and Sequential Strategies / Multitargeted VEGFR‐TKIs; document `art_e6a50d504115` sha256 `e6a50d50411565dcb2beef0b6cd9f260fa01b5e5e7bdb0087cd27cb8c4a85b97`; claim `art_4d177b7a62bf` sha256 `4d177b7a62bf1a5ca572f2bad91cbf08947c392ad4055e53d1f0b208ac3735bf` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1175
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`
- **claim_01M4V0JWTG86NZZ4E1SRM2Y6DR** · `conflicts` · evidence `peer_reviewed` · determination `measured` · value `{"unit": "% grade >=3 adverse events", "unit_as_reported": "% grade >=3 adverse events", "value": 61.1, "value_high": null, "value_low": null}`
  > grade ≥ 3 AEs occurred in 61.1% versus 19.7% of patients with fruquintinib versus placebo; common AEs grade ≥ 3 AEs in the fruquintinib arm included hypertension (21.2%), hand‐foot syndrome (10.8%), and proteinuria (3.2%). Treatment discontinuation due to AEs occurred in 15.2% versus 5.8% of patients who received fruquintinib versus placebo; nine patients who received fruquintinib (3.2%) and two patients who received placebo (1.5%) had treatment‐emergent AEs leading to death
  - as recorded (paraphrase): Grade 3 or higher adverse events occurred in 61.1% versus 19.7% of controls, with grade 3 or higher hypertension in 21.2%, hand-foot syndrome in 10.8% and proteinuria in 3.2%, discontinuation for adverse events in 15.2% versus 5.8%, and fatal treatment-emergent events in 3.2% versus 1.5%.
  - in `src_doi_10.1111/cts.70713` at `paragraph` `sec5.1.p1`, section Key Clinical Trials / Summary of Clinical Efficacy and Safety; document `art_c39cbfdcc31e` sha256 `c39cbfdcc31ef3ea6814fce214c161303b6e692683ea6d22ad085239bd8d08b3`; claim `art_eefc08b79ccd` sha256 `eefc08b79ccd7e86496ebf4ae8d227089af91fedbba0b08adc36558b8de5cad3` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 1230
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `value_in_quote` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified", "value_in_quote"]` · by `reader:claude-opus-5`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage `cri_01M4V22210J1SV3PK3W8HTZ29Z` at version `4`, state `promoted`
- parents — · children —
- merged away: —
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for toxicological_safety
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Structured value 64.3 carries unit '% dose reductions'; the discontinuation figure in this quote is 18.8%. On a discontinuation-rate attribute this overstates by more than threefold.; Structured value 61.1 is a grade >=3 AE rate; the quote's discontinuation figure is 15.2%. The same pattern in claim_01M4V0DJ3TH48MB4DJX096M03C (value 75.9 is grade >=3; discontinuation is 14.2%). Three of five claims carry a value that is not a discontinuation rate while the correct figure sits only in the prose.;
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · The quote reads 'treatment cessation occurs in approximately 5% of patients with operable BCC and 36% of patients with locally advanced or metastatic BCC' and concerns Shh inhibitors. It neither attributes cessation to adverse events nor concerns an agent of this class, so reading it as an adverse-event discontinuation rate adds an attribution the quote does not make.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · Dropped the cessation quote that neither attributes stopping to adverse events nor concerns this class, and the definition now excludes unattributed cessation rates and rates reported for another drug class. The line of therapy is recorded with each value, since the quotes differ in line and in the alternatives patients have.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `accepted` · —

**Use**

- status `deferred` on `rules@v3` — literature_retrieval was held out of this run: screened on database rules first (staged sweep, ADR-33)
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 35. VEGFR1 affinity on the independent expert curation

- **attribute** `attr_vegfr1-affinity-on-the-independent-expert-curation@v1` · **rule** `rule_vegfr1-affinity-on-the-independent-expert-curation@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_vegfr1-affinity-on-the-independent-expert-curation@v1"]`, rule `["rule_vegfr1-affinity-on-the-independent-expert-curation@v1"]`; supersedes —
- **record hashes**: attribute `cb44a80ead53742a36d34a6f0817780b3721b3e452b0a0fd0aab0aeb8b8f0428`, rule `311a2866a7080d001a1339b2530b11a47d71cf493e6f6ae55c2e13e74a907cb4`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V183C7BDENSATE61MA535A@v6"}` · dimension `target_coverage`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: VEGFR1 affinity on the independent expert curation · subject `[{"target_chembl_id": "CHEMBL1868"}]` · unit `pChEMBL` · `quantitative` · aggregated by `median` · transform —
  - read from `["interaction_evidence_lookup"]` asking `["gtopdb_affinity"]`; evidence kinds `["curated_measurement"]`; determination bases —
  - measurement identity `0f0f7e3f3b2c16e28a9eaf6c7a3e297fb4b4f77a52a9e096f87500a36b766732`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `unknown_no_penalty` · decision identity `1dc08baee1cac8e45f5e584f1de68cb26a7611fa05e59249d48bbc69303ded44`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The median expert-curated affinity of the compound at vascular endothelial growth factor receptor 1, on the pChEMBL scale, that is the negative base-ten logarithm of the molar half-maximal inhibitory concentration, inhibition constant or dissociation constant as the curation reports it. Higher is better. The source bound here is an expert curation independent of the activity table that the registry's potency criterion for this receptor reads, and it can cover compound-target pairs that table lacks, which is the gap this attribute is for: a candidate whose engagement of this receptor is absent from one curation may be quantified in the other. It is therefore not a restatement of the registry criterion and does not replace it. The two read different sources, the median is taken over the records this source returns rather than a maximum, because a maximum rises with the number of records, and the action type and any selectivity comment travel with each record for a narrative to cite. Where the two curations disagree materially about the same compound the conflict is routed to a human rather than averaged. Absence of a record gives unknown and never a failure, because this curation is sparse outside developed and late-stage drugs.

- **unit** `pChEMBL` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `median`
- **accepted evidence kinds** `["curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose affinity at this receptor is quantified by a curation independent of the activity table are ranked on that measurement, which recovers coverage evidence for candidates the activity table does not cover, while candidates with no record in either curation are not penalised.
- **falsification test**: Compare this curation's values with the registry potency criterion for the same receptor across the pool. If the two agree everywhere and cover the same candidates, this attribute adds nothing and should be merged into that criterion; if they disagree materially for a candidate, the conflict is routed to a human rather than averaged. If the curation returns no record for any candidate the attribute yields only unknowns.
- **rationale**: This is one of the required receptors and the cited quotes show it is covered as part of a set rather than alone: one approved oral agent inhibits it together with the other two vascular receptors and further kinases, a phase I agent covers it alongside two further kinases as an ATP-competitive inhibitor, the anti-angiogenic effect of the class is attributed to it and the second vascular receptor for angiogenesis and to the third for lymphangiogenesis, dual blockade of the first two suppressed angiogenesis and tumour growth in vitro, and one multikinase agent is recorded as lacking coverage of it altogether, so coverage here cannot be inferred from activity at the principal angiogenic receptor. The mechanism-of-action record source this attribute previously read stamps every claim it returns with determination basis curated, a basis excluded by the bases an attribute here accepts, so every record it returned would be set aside at assessment time and the attribute would carry no evidence at all; that is the finding this revision answers. The attribute is therefore bound instead to the independent expert curation of affinity at this receptor, which returns measured values on the pChEMBL scale and, being independent of the activity table, reaches compound-target pairs that table lacks, the same gap the record-based form was meant to close, while stating how strongly rather than only that engagement is documented. No cited quote states a required affinity at this receptor, so the rule is an ordering with no cutoff, and an absent record is unknown rather than a failure.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `unknown_no_penalty`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `7b63f3a54252dffb26e2aab0e4113fcb575fcd9fe1be8e03d6bcf9ce687dd4ef` · 1 route(s) · literature-bound `False`
  - route `interaction_evidence_lookup` / `gtopdb_affinity` · subject `{"target_chembl_id": "CHEMBL1868"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 5 cited claim(s), 5 carry `location.span_checked_against_source: true` and 5 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 5 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 5}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 1, "supports": 4}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TYG07WBNDBQ3R2GZ9JRE94** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Sorafenib, a multikinase RTKI, targets VEGFR2/3, PDGFR, RAF kinases (CRAF, BRAF), MEK, extracellular signal‐regulated kinase (ERK), KIT, FLT3 and RET.
  - as recorded (paraphrase): A multikinase agent targets VEGFR2 and VEGFR3, PDGFR, RAF kinases, MEK, ERK, KIT, FLT3 and RET.
  - in `src_doi_10.1111/iwj.70513` at `paragraph` `sec3.1.1.3.p1`, section Review / Receptor Tyrosine Kinase Inhibitors / Moderate Clinical Evidence / Sorafenib; document `art_499b086f52f6` sha256 `499b086f52f6419f8d88affbe0dbf50286a0c8ac557c5b669c0eaec26426e98e`; claim `art_d3ef920c0238` sha256 `d3ef920c023813ee3833dc3c5396ffa9c98fd0919008fad4cf695bca1de16b5b` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 504
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

*polarity `supports`*

- **claim_01M4TXF5QC8TYJSBFBSHEKMY1D** · `supports` · evidence `peer_reviewed` · determination `measured` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > VGB peptide | VEGFR1, VEGFR2 | - In vitro: human umbilical vascular endothelial cells (HUVECs), 4T1 mammary carcinoma tumor cells and U87 glioblastoma cells. | VEGFR1/VEGFR2 inhibition, VEGF-induced endothelial proliferation, migration, tube formation, angiogenesis, tumor growth, metastasis, PI3K/AKT and MAPK/ERK signaling. | Dual blockade of VEGFR1 and VEGFR2 inhibited VEGF-driven angiogenesis, tumor growth, and metastasis by suppressing PI3K/AKT and MAPK/ERK1/2 signaling pathways
  - as recorded (paraphrase): Dual blockade of VEGFR1 and VEGFR2 inhibited VEGF-driven angiogenesis, tumour growth and metastasis by suppressing PI3K/AKT and MAPK/ERK1/2 signalling.
  - in `src_doi_10.3390/ijms27156590` at `table` `table3`, section Tables; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_1fb9320ec633` sha256 `1fb9320ec6332f17ca71647caf5fe9b7882c23c867357263005e3e84fdd29fd2` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 173
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) HUVECs, 4T1 and U87 cells in vitro · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXXA7GJ9ZR3WRGDN5N5ZDW** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > It inhibits multiple receptor tyrosine kinases, including VEGFR 1, 2, 3, PDGRF alpha, beta, c-kit, FLT-3, and RET.
  - as recorded (paraphrase): An approved oral multi-kinase agent inhibits VEGFR1, VEGFR2 and VEGFR3 together with PDGFR alpha and beta, c-kit, FLT-3 and RET.
  - in `src_nbk_NBK563230` at `paragraph` `article-28341.s9.p33`, section Treatment / Management; document `art_55e79771f56d` sha256 `55e79771f56d1e6d548de79bb180e4c496477cca454dd8e3a79d1718f5793133`; claim `art_20436d8fc1ef` sha256 `20436d8fc1ef3550b9b886861f51e99a0184f2d1abe7ab905bc8103bb5b7c27d` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 274
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXXA8SKD5CQJSCYVNT1BJD** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > The anti-angiogenic effect of sorafenib is attributed to its effect on angiogenesis and lymphangiogenesis, which is mediated via the VEGFR 1,2 (angiogenesis) and 3 (lymphangiogenesis), respectively.
  - as recorded (paraphrase): The anti-angiogenic effect of a multi-kinase inhibitor is mediated through VEGFR1 and VEGFR2 for angiogenesis and VEGFR3 for lymphangiogenesis.
  - in `src_nbk_NBK563230` at `paragraph` `article-28341.s9.p35`, section Treatment / Management; document `art_55e79771f56d` sha256 `55e79771f56d1e6d548de79bb180e4c496477cca454dd8e3a79d1718f5793133`; claim `art_f47d496f74ba` sha256 `f47d496f74ba41b05eadd68142fb9293a088f206bb39355affb99f8cfc53f5e9` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 276
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TYRRJB6JG6JKRS1N8VSTC1** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > MK-24613 | Ia (non-classical) | c-Met, RON, VEGFR1 | Phase I | Solid tumors | Active-state selective ATP-competitive inhibitor
  - as recorded (paraphrase): A phase I non-classical Type Ia agent covers VEGFR1 alongside two other kinases as an active-state selective ATP-competitive inhibitor.
  - in `src_doi_10.3390/ijms27188007` at `table` `table1`, section Tables; document `art_480b68481ece` sha256 `480b68481ecefe2a1fdafb89f03b786362ce39c7543050d4150c5567f2a10d23`; claim `art_12c2b27a0821` sha256 `12c2b27a082123b8ceef2713534ae08bddcf674af8e03158f793a3f9f01057a5` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 590
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review item `q_01M4VEGR6NEJM5DCWK0FRPAMD4` (`open`, blocking `True`, raised 2026-10-13T20:16:01.237Z): proposer and critic still disagree after one revision
  - inspection bundle: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "open_critic_findings": [{"check": "evidence_support", "finding": "The subject is 'VGB peptide', a peptide evaluated in vitro in HUVECs and tumour cell lines, while the attribute binds by inchikey to a small-molecule curation and the objective is an orally administered agent. claim_01M4TYRRJB6JG6JKRS1N8VSTC1 is a phase I pipeline row, and claim_01M4TXXA7GJ9ZR3WRGDN5N5ZDW has a pronoun subject ('It inhibits multiple receptor tyrosine kinases, including VEGFR 1, 2, 3'). None supplies a numeric affinity.", "proposal_index": 1, "referent": "claim_01M4TXF5QC8TYJSBFBSHEKMY1D", "severity": "material", "verdict": "fail"}], "pool_criterion": "cri_01M4V183C7BDENSATE61MA535A"}`
- unresolved proposer/critic disputes: `q_01M4VEGR6NEJM5DCWK0FRPAMD4`
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (2):
  - `evidence_support` on claim_01M4TXF5QC8TYJSBFBSHEKMY1D · severity `material` · verdict `fail`: The subject is 'VGB peptide', a peptide evaluated in vitro in HUVECs and tumour cell lines, while the attribute binds by inchikey to a small-molecule curation and the objective is an orally administered agent. claim_01M4TYRRJB6JG6JKRS1N8VSTC1 is a phase I pipeline row, and claim_01M4TXXA7GJ9ZR3WRGDN5N5ZDW has a pronoun subject ('It inhibits multiple receptor tyrosine kinases, including VEGFR 1, 2, 3'). None supplies a numeric affinity.
  - `evidence_support` on claim_01M4TYG07WBNDBQ3R2GZ9JRE94 · severity `minor` · verdict `fail`: This quote lists 'VEGFR2/3, PDGFR, RAF kinases ... KIT, FLT3 and RET' and is silent on VEGFR1. Silence about a receptor is evidence of nothing on an affinity axis and cannot support a value for this attribute.

**Lineage and lifecycle**

- pool lineage `cri_01M4V183C7BDENSATE61MA535A` at version `6`, state `promoted`
- parents — · children —
- merged away: `{"collapse_id": "clp_01M4WXKPKBRKYT0M0QJ6FP1BJ4", "into": "attr_vegfr1-curated-potency@v2", "reason_text": "2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL1868. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_vegfr1-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.", "withdrawn": false}`
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for target_coverage
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · arbitrary_cutoff: source_stated_value cutoff without a cited claim carrying a value
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The validator was right: a cutoff of 'equals true' carries no value taken from any cited quote, so declaring cutoff_basis source_stated_value invented a standard the claims do not state. The rule is therefore rebuilt as a preference with predicate_form ordering, cutoff null and cutoff_basis none_evidence_insufficient, and the direction is set to higher_better so documented engagement ranks above undocumented engagement without any threshold being asserted. Two further corrections follow from the evidence catalog's own instruction for this entry: acceptable_determination_bases is now declared as ['curated'], without which every record-derived claim would be set aside and the attribute would see no evidence at all, and the definition now states in terms that a record is an expert assertion rather than a measurement and must never stand in for a potency value. The cited claims are retained: each one speaks to VEGFR1 coverage specifically, including the counter-example of an agent recorded as lacking it.
  - round `run_01M4V52W85KZMCC0X2A7BN1YR3` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · evidence_support: the bound source returns curated records and acceptable_determination_bases ['measured', 'derived'] excludes that basis, so every value it returns would be set aside and the attribute would carry no evidence
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `needs_refine` · `refined_still_failing` · evidence_support: the bound source returns curated records and acceptable_determination_bases ['measured', 'derived'] excludes that basis, so every value it returns would be set aside and the attribute would carry no evidence
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The bound mechanism-of-action record source returns claims stamped determination basis curated, which the accepted bases exclude, so every record would have been set aside and the criterion would have measured nothing; declaring the basis on the attribute did not survive the previous revision, so the finding is resolved the other way, by binding the attribute to the independent expert affinity curation for the same receptor, whose records are measured values on the pChEMBL scale. The definition states that this curation is independent of the activity table the registry's potency criterion reads, which is the coverage gap the record-based form was meant to close, that it does not replace that criterion, and that a material disagreement between the two is routed to a human.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `disputed` · —

**Use**

- status `collapsed_away` on `rules@v3` — its attribute was merged into attr_vegfr1-curated-potency@v2 by clp_01M4WXKPKBRKYT0M0QJ6FP1BJ4; rule_vegfr1-curated-potency@v2 scores the quantity
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 36. VEGFR1 curated potency

- **attribute** `attr_vegfr1-curated-potency@v2` · **rule** `rule_vegfr1-curated-potency@v2` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_vegfr1-curated-potency@v1", "attr_vegfr1-curated-potency@v2"]`, rule `["rule_vegfr1-curated-potency@v1", "rule_vegfr1-curated-potency@v2"]`; supersedes `attr_vegfr1-curated-potency@v1`
- **record hashes**: attribute `5895f9eb20eb55d2db2365fe46ad0a8941132151d36aa995ec4e1050add1c2e8`, rule `2af4335a32ab6c4a7d282462dcb48e6298967fbc7e46b760a48eec4000cdb39b`
- **origin**: `task_mandated_template` · proposed by `{"id": "objective-criteria", "kind": "system", "role": "adapter_template"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"field": "scope_entities[1]", "task_context": "task_01M4TWZXZEB1SQPS7H47C8BX01@v1"}` · dimension —
- **written by software**: `{"collapsed_by": "clp_01M4WXKPKBRKYT0M0QJ6FP1BJ4", "rule_collapsed_by": "clp_01M4WXKPKBRKYT0M0QJ6FP1BJ4"}`

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: VEGFR1 curated potency · subject `[{"target_chembl_id": "CHEMBL1868"}]` · unit `pChEMBL` · `quantitative` · aggregated by `median` · transform —
  - read from `["interaction_evidence_lookup"]` asking `["gtopdb_affinity", "pchembl_values"]`; evidence kinds `["curated_measurement"]`; determination bases —
  - measurement identity `f5ec63a39fd1252c3d47afbda02cfb271afd316f410465e00f54c60144e91321`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_blocks_recommendation` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `unknown_blocks_recommendation` · decision identity `bedd2b96e516da2036f38a46b04a61f2e57a1858042d60f285862fd1b9bc0dda`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> Median pChEMBL value over curated point measurements against VEGFR1 (CHEMBL1868)

- **unit** `pChEMBL` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `median`
- **accepted evidence kinds** `["curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_blocks_recommendation", "stated_in_definition_only": true}`
- **expected change**: —
- **falsification test**: —
- **rationale**: VEGFR1 is a required target of the task

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_blocks_recommendation` · **on conflict** `unknown_blocks_recommendation`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `5fdb988fd31f59141fc8469b461732699269e2175504fdc02f2f3538ed9bee9b` · 2 route(s) · literature-bound `False`
  - route `interaction_evidence_lookup` / `pchembl_values` · subject `{"target_chembl_id": "CHEMBL1868"}` · retrieval — · identifier scheme `inchikey`
  - route `interaction_evidence_lookup` / `gtopdb_affinity` · subject `{"target_chembl_id": "CHEMBL1868"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 0 cited claim(s), 0 carry `location.span_checked_against_source: true` and 0 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` — (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: —
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage — at version —, state —
- parents — · children —
- merged away: —
- survived a collapse: `{"absorbed": ["attr_vegfr1-affinity-on-the-independent-expert-curation@v1"], "collapse_id": "clp_01M4WXKPKBRKYT0M0QJ6FP1BJ4", "reason_text": "2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL1868. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_vegfr1-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.", "routes_after": ["pchembl_values", "gtopdb_affinity"], "routes_before": ["pchembl_values"], "withdrawn": false}`
- refinement history: — (this criterion never entered the pool)

**Use**

- status `scoring` on `rules@v3`
- rule-set entry: `{"acceptable_value_sources": ["curated_measurement"], "attribute_ref": "attr_vegfr1-curated-potency@v2", "authority": "trigger_table", "confirmed_by": "auto:trigger_table", "cutoff_basis": "none_evidence_insufficient", "disputed": false, "on_states": ["unknown_no_penalty", "unknown_blocks_recommendation", "unknown_blocks_recommendation"], "rule_kind": "preference", "rule_ref": "rule_vegfr1-curated-potency@v2"}`
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `True`
- measured coverage: `{"assessed": 3177, "board": "lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4", "observed": 42}`

---

### 37. VEGFR2 affinity on the independent expert curation

- **attribute** `attr_vegfr2-affinity-on-the-independent-expert-curation@v1` · **rule** `rule_vegfr2-affinity-on-the-independent-expert-curation@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_vegfr2-affinity-on-the-independent-expert-curation@v1"]`, rule `["rule_vegfr2-affinity-on-the-independent-expert-curation@v1"]`; supersedes —
- **record hashes**: attribute `28752f00f436f42ccd36d99968964d3bf55b9458cfe64419e05fe0655c340a68`, rule `d176818719fd9d74815eb86526714529c7322c60b2cbde9ddf722926073352e4`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V183CVHMGPNPDT5HKCD2GB@v6"}` · dimension `target_coverage`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: VEGFR2 affinity on the independent expert curation · subject `[{"target_chembl_id": "CHEMBL279"}]` · unit `pChEMBL` · `quantitative` · aggregated by `median` · transform —
  - read from `["interaction_evidence_lookup"]` asking `["gtopdb_affinity"]`; evidence kinds `["curated_measurement"]`; determination bases —
  - measurement identity `43d4296440e59c01c79c7335a0b77c3e696bdb5cdb41c57834cddb6027c80a4c`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `unknown_no_penalty` · decision identity `8d6475411bc04079e08064f14b3e098618353653e2f2467113fc6279b4252983`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The median expert-curated affinity of the compound at vascular endothelial growth factor receptor 2, on the pChEMBL scale, that is the negative base-ten logarithm of the molar half-maximal inhibitory concentration, inhibition constant or dissociation constant as the curation reports it. Higher is better. The source bound here is an expert curation independent of the activity table that the registry's potency criterion for this receptor reads, and it can cover compound-target pairs that table lacks, which is the gap this attribute is for: a candidate whose engagement of this receptor is absent from one curation may be quantified in the other. It is therefore not a restatement of the registry criterion and does not replace it. The two read different sources, the median is taken over the records this source returns rather than a maximum, because a maximum rises with the number of records, and the action type and any selectivity comment travel with each record for a narrative to cite. Where the two curations disagree materially about the same compound the conflict is routed to a human rather than averaged. Absence of a record gives unknown and never a failure, because this curation is sparse outside developed and late-stage drugs.

- **unit** `pChEMBL` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `median`
- **accepted evidence kinds** `["curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose affinity at this receptor is quantified by a curation independent of the activity table are ranked on that measurement, which recovers coverage evidence for candidates the activity table does not cover, while candidates with no record in either curation are not penalised.
- **falsification test**: Compare this curation's values with the registry potency criterion for the same receptor across the pool. If the two agree everywhere and cover the same candidates, this attribute adds nothing and should be merged into that criterion; if they disagree materially for a candidate, the conflict is routed to a human rather than averaged. If the curation returns no record for any candidate the attribute yields only unknowns.
- **rationale**: The cited quotes identify this receptor as the principal mediator of growth-factor-driven angiogenesis and the one whose upregulation marks tumour vasculature, name an approved oral inhibitor of it, describe a single oral agent covering it together with the required fibroblast growth factor receptor, describe another covering it together with that receptor family and the macrophage receptor, and record a counter-example in which a highly selective agent of the fibroblast growth factor receptor class has minimal activity at it, so coverage is not safely assumed from class membership. The mechanism-of-action record source this attribute previously read stamps every claim it returns with determination basis curated, a basis excluded by the bases an attribute here accepts, so every record it returned would be set aside at assessment time and the attribute would carry no evidence at all; that is the finding this revision answers. The attribute is therefore bound instead to the independent expert curation of affinity at this receptor, which returns measured values on the pChEMBL scale and, being independent of the activity table, reaches compound-target pairs that table lacks, the same gap the record-based form was meant to close, while stating how strongly rather than only that engagement is documented. No cited quote states a required affinity at this receptor, so the rule is an ordering with no cutoff, and an absent record is unknown rather than a failure.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `unknown_no_penalty`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `dc3682e71e3341df14ff939221ec48c4e841aca97c2b131f295702966108254c` · 1 route(s) · literature-bound `False`
  - route `interaction_evidence_lookup` / `gtopdb_affinity` · subject `{"target_chembl_id": "CHEMBL279"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 5 cited claim(s), 5 carry `location.span_checked_against_source: true` and 5 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 5 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 5}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"conflicts": 1, "supports": 4}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `conflicts`*

- **claim_01M4TXQQ3GXQNNE9DG8QK6E6NM** · `conflicts` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Debio-1347 (CH5183284, zoligratinib) | Oral, highly selective, ATP-competitive FGFR1–3 inhibitor; minimal activity on KDR/VEGFR2 and most other kinases.
  - as recorded (paraphrase): An oral highly selective ATP-competitive FGFR1-3 inhibitor has minimal activity on KDR/VEGFR2 and most other kinases.
  - in `src_doi_10.2147/dddt.s559328` at `table` `table2`, section Tables; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_46bea276c6cb` sha256 `46bea276c6cbd970afcd7119e3ec640bada788d2bf6770bc860b5ab6bd4b37c8` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 202
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

*polarity `supports`*

- **claim_01M4TX99N08S8JSHY0B6TYSH4C** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Vandetanib | VEGFR2 | Medullary thyroid cancer
  - as recorded (paraphrase): An approved oral tyrosine kinase inhibitor targeting VEGFR2 exists, indicated for medullary thyroid cancer.
  - in `src_nbk_NBK563322` at `table` `article-109800.table1`, section Tables; document `art_f39aa2170bbb` sha256 `f39aa2170bbb6e797aa143c217673d26d91bf5238802cedbd23bc4621ce110fc`; claim `art_595f357273a4` sha256 `595f357273a48a346144ad62f52a1355739c7a2621b6f4cc3919c0bc60bc7b9e` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 105
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXF4FQF24CPE4ZHR2NAJF9** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > VEGFR2 | VEGFR2 upregulation in tumor endothelium | Highly expressed in GB vasculature | Principal mediator of tumor angiogenesis and endothelial proliferation. Major therapeutic target for antiangiogenic therapies. | VEGF/VEGFR2 signaling
  - as recorded (paraphrase): VEGFR2 is upregulated in tumour endothelium and highly expressed in GB vasculature, where it is the principal mediator of tumour angiogenesis and endothelial proliferation and a major antiangiogenic target.
  - in `src_doi_10.3390/ijms27156590` at `table` `table1`, section Tables; document `art_89edbb6e2bd5` sha256 `89edbb6e2bd50f354c4e745c213f100f4c25afa86d2ffd74113c029d99781d04`; claim `art_f692e75b5bf4` sha256 `f692e75b5bf49b89327ea02285a394b0ea782d97a6c8472efe648c9b0a66f75c` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 121
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXQQ259SAS711B2STZ8NB2** · `supports` · evidence `peer_reviewed` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Derazantinib (ARQ-087) | Oral, reversible, spectrum-selective FGFR1–3 inhibitor with additional CSF1R and VEGFR2 inhibition (multi-kinase) | ATP-competitive pan-FGFR1–3 blockade; concurrent CSF1R and VEGFR2 inhibition may modulate the tumour micro-environment and angiogenesis; active against a range of FGFR2 alterations (fusions, mutations, amplifications).
  - as recorded (paraphrase): An oral reversible spectrum-selective FGFR1-3 inhibitor with additional CSF1R and VEGFR2 inhibition provides ATP-competitive pan-FGFR1-3 blockade, and concurrent CSF1R and VEGFR2 inhibition may modulate the tumour microenvironment and angiogenesis, with activity across FGFR2 fusions, mutations and amplifications.
  - in `src_doi_10.2147/dddt.s559328` at `table` `table2`, section Tables; document `art_762c8d10f115` sha256 `762c8d10f115f4f6b6ae1009f09e6ce851a2de43cd5606238f0078ce2ddf6cec`; claim `art_26ec13cce203` sha256 `26ec13cce2039652faad612048c3a8a0a9e05e439cce107ce65c1dd9179a908e` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 200
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXXA9SKM4H1AGH6EW4773R** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > Multitargeted receptor tyrosine kinase inhibitor inhibits VEGFR 2, fibroblast growth factor receptor 1, 2, 3, 4, PDGFR alpha, c kit, and RET.
  - as recorded (paraphrase): An approved oral multi-targeted receptor tyrosine kinase inhibitor inhibits VEGFR2, FGFR1, FGFR2, FGFR3, FGFR4, PDGFR alpha, c-kit and RET.
  - in `src_nbk_NBK563230` at `paragraph` `article-28341.s9.p37`, section Treatment / Management; document `art_55e79771f56d` sha256 `55e79771f56d1e6d548de79bb180e4c496477cca454dd8e3a79d1718f5793133`; claim `art_f0373d3cd414` sha256 `f0373d3cd414eb4f1f2540ed50aa80d43748796434e285451b058dda787b7f54` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 278
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review item `q_01M4VEGRA2FYK8WVZ7HSFRCCGZ` (`open`, blocking `True`, raised 2026-10-13T20:16:01.346Z): proposer and critic still disagree after one revision
  - inspection bundle: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "open_critic_findings": [{"check": "evidence_support", "finding": "None of the five cited claims carries an affinity number. claim_01M4TXF4FQF24CPE4ZHR2NAJF9 and claim_01M4TX99N08S8JSHY0B6TYSH4C establish target relevance; claim_01M4TXXA9SKM4H1AGH6EW4773R and claim_01M4TXQQ259SAS711B2STZ8NB2 are target lists; claim_01M4TXQQ3GXQNNE9DG8QK6E6NM reports 'minimal activity on KDR/VEGFR2', a near-absence that yields no pChEMBL value and under direction higher_better would need quantifying to count against a candidate.", "proposal_index": 2, "referent": "supporting_claim_ids", "severity": "material", "verdict": "fail"}], "pool_criterion": "cri_01M4V183CVHMGPNPDT5HKCD2GB"}`
- unresolved proposer/critic disputes: `q_01M4VEGRA2FYK8WVZ7HSFRCCGZ`
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: None of the five cited claims carries an affinity number. claim_01M4TXF4FQF24CPE4ZHR2NAJF9 and claim_01M4TX99N08S8JSHY0B6TYSH4C establish target relevance; claim_01M4TXXA9SKM4H1AGH6EW4773R and claim_01M4TXQQ259SAS711B2STZ8NB2 are target lists; claim_01M4TXQQ3GXQNNE9DG8QK6E6NM reports 'minimal activity on KDR/VEGFR2', a near-absence that yields no pChEMBL value and under direction higher_better would need quantifying to count against a candidate.

**Lineage and lifecycle**

- pool lineage `cri_01M4V183CVHMGPNPDT5HKCD2GB` at version `6`, state `promoted`
- parents — · children —
- merged away: `{"collapse_id": "clp_01M4WXKPQ837MK8GF71Y7F5YVH", "into": "attr_vegfr2-curated-potency@v2", "reason_text": "2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL279. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_vegfr2-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.", "withdrawn": false}`
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for target_coverage
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · arbitrary_cutoff: source_stated_value cutoff without a cited claim carrying a value
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · The validator was right: a cutoff of 'equals true' carries no value taken from any cited quote, so declaring cutoff_basis source_stated_value invented a standard the claims do not state. The rule is therefore rebuilt as a preference with predicate_form ordering, cutoff null and cutoff_basis none_evidence_insufficient, and the direction is set to higher_better so documented engagement ranks above undocumented engagement without any threshold being asserted. Two further corrections follow from the evidence catalog's own instruction for this entry: acceptable_determination_bases is now declared as ['curated'], without which every record-derived claim would be set aside and the attribute would see no evidence at all, and the definition now states in terms that a record is an expert assertion rather than a measurement and must never stand in for a potency value. The cited claims are unchanged.
  - round `run_01M4V52W85KZMCC0X2A7BN1YR3` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · evidence_support: the bound source returns curated records and acceptable_determination_bases ['measured', 'derived'] excludes that basis, so every value it returns would be set aside and the attribute would carry no evidence
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `needs_refine` · `refined_still_failing` · evidence_support: the bound source returns curated records and acceptable_determination_bases ['measured', 'derived'] excludes that basis, so every value it returns would be set aside and the attribute would carry no evidence
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The bound mechanism-of-action record source returns claims stamped determination basis curated, which the accepted bases exclude, so every record would have been set aside and the criterion would have measured nothing; declaring the basis on the attribute did not survive the previous revision, so the finding is resolved the other way, by binding the attribute to the independent expert affinity curation for the same receptor, whose records are measured values on the pChEMBL scale. The definition states that this curation is independent of the activity table the registry's potency criterion reads, which is the coverage gap the record-based form was meant to close, that it does not replace that criterion, and that a material disagreement between the two is routed to a human.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `disputed` · —

**Use**

- status `collapsed_away` on `rules@v3` — its attribute was merged into attr_vegfr2-curated-potency@v2 by clp_01M4WXKPQ837MK8GF71Y7F5YVH; rule_vegfr2-curated-potency@v2 scores the quantity
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 38. VEGFR2 curated potency

- **attribute** `attr_vegfr2-curated-potency@v2` · **rule** `rule_vegfr2-curated-potency@v2` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_vegfr2-curated-potency@v1", "attr_vegfr2-curated-potency@v2"]`, rule `["rule_vegfr2-curated-potency@v1", "rule_vegfr2-curated-potency@v2"]`; supersedes `attr_vegfr2-curated-potency@v1`
- **record hashes**: attribute `9fc04359a74f7b08e751970cb5e707fdb92113cee409e41a65c48f5c77f6b5f2`, rule `c73846a251f81f67fb22415e0b6442d41ad4ae8c71f409e7aba0050f3a3f2d63`
- **origin**: `task_mandated_template` · proposed by `{"id": "objective-criteria", "kind": "system", "role": "adapter_template"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"field": "scope_entities[2]", "task_context": "task_01M4TWZXZEB1SQPS7H47C8BX01@v1"}` · dimension —
- **written by software**: `{"collapsed_by": "clp_01M4WXKPQ837MK8GF71Y7F5YVH", "rule_collapsed_by": "clp_01M4WXKPQ837MK8GF71Y7F5YVH"}`

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: VEGFR2 curated potency · subject `[{"target_chembl_id": "CHEMBL279"}]` · unit `pChEMBL` · `quantitative` · aggregated by `median` · transform —
  - read from `["interaction_evidence_lookup"]` asking `["gtopdb_affinity", "pchembl_values"]`; evidence kinds `["curated_measurement"]`; determination bases —
  - measurement identity `e242eb37c495da10b1201e69f0dd366ca4f53d5b4add83c50a2a3a0519cce7c1`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_blocks_recommendation` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `unknown_blocks_recommendation` · decision identity `9f80a813ffdb82268bf6fb0e23be629fefa0e083a325359f676e012f90fc836d`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> Median pChEMBL value over curated point measurements against VEGFR2 (CHEMBL279)

- **unit** `pChEMBL` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `median`
- **accepted evidence kinds** `["curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_blocks_recommendation", "stated_in_definition_only": true}`
- **expected change**: —
- **falsification test**: —
- **rationale**: VEGFR2 is a required target of the task

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_blocks_recommendation` · **on conflict** `unknown_blocks_recommendation`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `6b0048c1439b759cf96ee5f2a6a3b28b144fa6dd9292d79b71843040d58fea38` · 2 route(s) · literature-bound `False`
  - route `interaction_evidence_lookup` / `pchembl_values` · subject `{"target_chembl_id": "CHEMBL279"}` · retrieval — · identifier scheme `inchikey`
  - route `interaction_evidence_lookup` / `gtopdb_affinity` · subject `{"target_chembl_id": "CHEMBL279"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 0 cited claim(s), 0 carry `location.span_checked_against_source: true` and 0 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` — (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: —
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage — at version —, state —
- parents — · children —
- merged away: —
- survived a collapse: `{"absorbed": ["attr_vegfr2-affinity-on-the-independent-expert-curation@v1"], "collapse_id": "clp_01M4WXKPQ837MK8GF71Y7F5YVH", "reason_text": "2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL279. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_vegfr2-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.", "routes_after": ["pchembl_values", "gtopdb_affinity"], "routes_before": ["pchembl_values"], "withdrawn": false}`
- refinement history: — (this criterion never entered the pool)

**Use**

- status `scoring` on `rules@v3`
- rule-set entry: `{"acceptable_value_sources": ["curated_measurement"], "attribute_ref": "attr_vegfr2-curated-potency@v2", "authority": "trigger_table", "confirmed_by": "auto:trigger_table", "cutoff_basis": "none_evidence_insufficient", "disputed": false, "on_states": ["unknown_no_penalty", "unknown_blocks_recommendation", "unknown_blocks_recommendation"], "rule_kind": "preference", "rule_ref": "rule_vegfr2-curated-potency@v2"}`
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `True`
- measured coverage: `{"assessed": 3177, "board": "lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4", "observed": 84}`

---

### 39. VEGFR3 affinity on the independent expert curation

- **attribute** `attr_vegfr3-affinity-on-the-independent-expert-curation@v1` · **rule** `rule_vegfr3-affinity-on-the-independent-expert-curation@v1` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_vegfr3-affinity-on-the-independent-expert-curation@v1"]`, rule `["rule_vegfr3-affinity-on-the-independent-expert-curation@v1"]`; supersedes —
- **record hashes**: attribute `8afb74157d0811505c5e35eb08473976983a1a1e8d0ba07c614fd65d078dbdc4`, rule `70ca181bf58873d97b4092cf0f918020ba40328a2b3156263393f1082191c227`
- **origin**: `literature_derived` · proposed by `{"id": "proposer:claude-opus-5 (subagent)", "kind": "agent", "model_family": "anthropic", "role": "proposer"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "pool_criterion": "cri_01M4V183DCPYS6DXM2GSSJDBGC@v6"}` · dimension `target_coverage`
- **written by software**: —

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: VEGFR3 affinity on the independent expert curation · subject `[{"target_chembl_id": "CHEMBL1955"}]` · unit `pChEMBL` · `quantitative` · aggregated by `median` · transform —
  - read from `["interaction_evidence_lookup"]` asking `["gtopdb_affinity"]`; evidence kinds `["curated_measurement"]`; determination bases —
  - measurement identity `2a921affbc2597fffb95afc091e811f74d7ff9bdccea3fac675f65cded81f42a`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_no_penalty` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `unknown_no_penalty` · decision identity `10545d886d53ab9f9da7205b6a1a1dc8224877daafe27f12e51a6f5bcee1f037`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> The median expert-curated affinity of the compound at vascular endothelial growth factor receptor 3, on the pChEMBL scale, that is the negative base-ten logarithm of the molar half-maximal inhibitory concentration, inhibition constant or dissociation constant as the curation reports it. Higher is better. The source bound here is an expert curation independent of the activity table that the registry's potency criterion for this receptor reads, and it can cover compound-target pairs that table lacks, which is the gap this attribute is for: a candidate whose engagement of this receptor is absent from one curation may be quantified in the other. It is therefore not a restatement of the registry criterion and does not replace it. The two read different sources, the median is taken over the records this source returns rather than a maximum, because a maximum rises with the number of records, and the action type and any selectivity comment travel with each record for a narrative to cite. Where the two curations disagree materially about the same compound the conflict is routed to a human rather than averaged. Absence of a record gives unknown and never a failure, because this curation is sparse outside developed and late-stage drugs.

- **unit** `pChEMBL` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `median`
- **accepted evidence kinds** `["curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_no_penalty", "stated_in_definition_only": true}`
- **expected change**: Candidates whose affinity at this receptor is quantified by a curation independent of the activity table are ranked on that measurement, which recovers coverage evidence for candidates the activity table does not cover, while candidates with no record in either curation are not penalised.
- **falsification test**: Compare this curation's values with the registry potency criterion for the same receptor across the pool. If the two agree everywhere and cover the same candidates, this attribute adds nothing and should be merged into that criterion; if they disagree materially for a candidate, the conflict is routed to a human rather than averaged. If the curation returns no record for any candidate the attribute yields only unknowns.
- **rationale**: This required receptor has a mechanistically distinct role: the cited quotes attribute angiogenesis to the first two receptors of the family and lymphangiogenesis to this one, so coverage of it cannot be inferred from activity at the principal angiogenic receptor, and the other cited quotes record single oral agents whose target list includes it explicitly alongside the other two. It is also the required receptor least likely to have been assayed in a routine screening cascade, which is why a second, independent curation is worth binding here. The mechanism-of-action record source this attribute previously read stamps every claim it returns with determination basis curated, a basis excluded by the bases an attribute here accepts, so every record it returned would be set aside at assessment time and the attribute would carry no evidence at all; that is the finding this revision answers. The attribute is therefore bound instead to the independent expert curation of affinity at this receptor, which returns measured values on the pChEMBL scale and, being independent of the activity table, reaches compound-target pairs that table lacks, the same gap the record-based form was meant to close, while stating how strongly rather than only that engagement is documented. No cited quote states a required affinity at this receptor, so the rule is an ordering with no cutoff, and an absent record is unknown rather than a failure.

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_no_penalty` · **on conflict** `unknown_no_penalty`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `7063f5e4dfdb215d634572f4a90bad55394c31f6d8c36e1b4a46655ce511d0de` · 1 route(s) · literature-bound `False`
  - route `interaction_evidence_lookup` / `gtopdb_affinity` · subject `{"target_chembl_id": "CHEMBL1955"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 3 cited claim(s), 3 carry `location.span_checked_against_source: true` and 3 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 3 (field: `claim.admission_reasons`)
- semantic support — `verification_status` `{"unverified": 3}` (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: `{"supports": 3}`
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

*polarity `supports`*

- **claim_01M4TXXA7GJ9ZR3WRGDN5N5ZDW** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > It inhibits multiple receptor tyrosine kinases, including VEGFR 1, 2, 3, PDGRF alpha, beta, c-kit, FLT-3, and RET.
  - as recorded (paraphrase): An approved oral multi-kinase agent inhibits VEGFR1, VEGFR2 and VEGFR3 together with PDGFR alpha and beta, c-kit, FLT-3 and RET.
  - in `src_nbk_NBK563230` at `paragraph` `article-28341.s9.p33`, section Treatment / Management; document `art_55e79771f56d` sha256 `55e79771f56d1e6d548de79bb180e4c496477cca454dd8e3a79d1718f5793133`; claim `art_20436d8fc1ef` sha256 `20436d8fc1ef3550b9b886861f51e99a0184f2d1abe7ab905bc8103bb5b7c27d` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 274
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXXA8SKD5CQJSCYVNT1BJD** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > The anti-angiogenic effect of sorafenib is attributed to its effect on angiogenesis and lymphangiogenesis, which is mediated via the VEGFR 1,2 (angiogenesis) and 3 (lymphangiogenesis), respectively.
  - as recorded (paraphrase): The anti-angiogenic effect of a multi-kinase inhibitor is mediated through VEGFR1 and VEGFR2 for angiogenesis and VEGFR3 for lymphangiogenesis.
  - in `src_nbk_NBK563230` at `paragraph` `article-28341.s9.p35`, section Treatment / Management; document `art_55e79771f56d` sha256 `55e79771f56d1e6d548de79bb180e4c496477cca454dd8e3a79d1718f5793133`; claim `art_f47d496f74ba` sha256 `f47d496f74ba41b05eadd68142fb9293a088f206bb39355affb99f8cfc53f5e9` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 276
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`
- **claim_01M4TXXAAZT417JZE2XG2YHH23** · `supports` · evidence `reference_text` · determination `asserted` · value `{"unit": null, "unit_as_reported": null, "value": null, "value_high": null, "value_low": null}`
  > It is a multitargeted receptor tyrosine kinase inhibitor, which inhibits VEGFR 1, 2, 3, PDGFR alpha and beta, and c-kit
  - as recorded (paraphrase): A third approved oral multi-targeted receptor tyrosine kinase inhibitor inhibits VEGFR1, VEGFR2, VEGFR3, PDGFR alpha and beta and c-kit.
  - in `src_nbk_NBK563230` at `paragraph` `article-28341.s9.p39`, section Treatment / Management; document `art_55e79771f56d` sha256 `55e79771f56d1e6d548de79bb180e4c496477cca454dd8e3a79d1718f5793133`; claim `art_93bd341e3413` sha256 `93bd341e3413e379f8e919181c1ae7da5428b8e59837aa49632614bc517517f6` on `run_01M4TX07ME8VWFJGK2PKNNGSEF` seq 280
  - checks — quote: span_checked_against_source `True`, quote_verified `True` · numerical: `not_recorded` · semantic: `unverified`
  - scope (stated) — · scope_match `unknown` · read `full_text` · admitted `admitted` `["quote_verified"]` · by `reader:claude-opus (subagent)`

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review item `q_01M4VEGRDJ9HW40J9AFPBHPM1S` (`open`, blocking `True`, raised 2026-10-13T20:16:01.458Z): proposer and critic still disagree after one revision
  - inspection bundle: `{"derivation_run": "run_01M4VABCW4TS9P3FJC0K7M8JC9", "open_critic_findings": [{"check": "evidence_support", "finding": "All three cited claims are mechanism or target-list statements with no number: claim_01M4TXXA8SKD5CQJSCYVNT1BJD assigns VEGFR3 to lymphangiogenesis, claim_01M4TXXAAZT417JZE2XG2YHH23 and claim_01M4TXXA7GJ9ZR3WRGDN5N5ZDW are pronoun-subject target lists. VEGFR3 is the receptor least likely to be curated, so this is the attribute whose unknown_no_penalty default will bind hardest.", "proposal_index": 3, "referent": "supporting_claim_ids", "severity": "material", "verdict": "fail"}], "pool_criterion": "cri_01M4V183DCPYS6DXM2GSSJDBGC"}`
- unresolved proposer/critic disputes: `q_01M4VEGRDJ9HW40J9AFPBHPM1S`
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule (1):
  - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: All three cited claims are mechanism or target-list statements with no number: claim_01M4TXXA8SKD5CQJSCYVNT1BJD assigns VEGFR3 to lymphangiogenesis, claim_01M4TXXAAZT417JZE2XG2YHH23 and claim_01M4TXXA7GJ9ZR3WRGDN5N5ZDW are pronoun-subject target lists. VEGFR3 is the receptor least likely to be curated, so this is the attribute whose unknown_no_penalty default will bind hardest.

**Lineage and lifecycle**

- pool lineage `cri_01M4V183DCPYS6DXM2GSSJDBGC` at version `6`, state `promoted`
- parents — · children —
- merged away: `{"collapse_id": "clp_01M4WXKPVCG360VDRWPCXAM2EN", "into": "attr_vegfr3-curated-potency@v2", "reason_text": "2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL1955. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_vegfr3-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.", "withdrawn": false}`
- survived a collapse: —
- refinement history:
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 0 stage `propose` · `add` → `candidate` · `new_evidence` · proposed for target_coverage
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `filter` · `revise` → `needs_refine` · `critic_findings` · Quote reports pan-FGFR1-4 coverage and says nothing about VEGFR3; it cannot support a VEGFR3 engagement flag.; claim_01M4TY6CKGF5YW7VD6P967ZDZX is a >=99% inhibition potency readout, but the attribute declares 'a documented-engagement flag, not a potency value' and accepts only database_entry. Wrong measurement kind for the only quantitative quote cited.
  - round `run_01M4TX07ME8VWFJGK2PKNNGSEF` iteration 1 stage `refine` · `revise` → `candidate` · `refined` · Two material evidence-support findings are accepted in full and resolved by removing the offending citations. claim_01M4TXQPYBE46FJ6XNSSCXGP0N reports coverage of all four FGFR isoforms and says nothing whatever about VEGFR3, so it cannot support a VEGFR3 engagement flag and is dropped. claim_01M4TY6CKGF5YW7VD6P967ZDZX is a percent-inhibition potency readout, which is the wrong measurement kind for an attribute that declares itself a documented-engagement flag accepting only database records, and it is dropped for that reason rather than reinterpreted. Three citations remain, each naming VEGFR3 or the three vascular receptors as a set. The cutoff defect shared with the sibling attributes is fixed the same way: ordering rather than an invented 'equals true' threshold, direction higher_better, cutoff_basis none_evidence_insufficient, acceptable_determination_bases declared as ['curated'], and the definition now states that a record is not a potency value.
  - round `run_01M4V52W85KZMCC0X2A7BN1YR3` iteration 1 stage `filter` · `revise` → `needs_refine` · `validator_findings` · evidence_support: the bound source returns curated records and acceptable_determination_bases ['measured', 'derived'] excludes that basis, so every value it returns would be set aside and the attribute would carry no evidence
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 1 stage `refine` · `revise` → `needs_refine` · `refined_still_failing` · evidence_support: the bound source returns curated records and acceptable_determination_bases ['measured', 'derived'] excludes that basis, so every value it returns would be set aside and the attribute would carry no evidence
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 2 stage `refine` · `revise` → `candidate` · `refined` · The bound mechanism-of-action record source returns claims stamped determination basis curated, which the accepted bases exclude, so every record would have been set aside and the criterion would have measured nothing; declaring the basis on the attribute did not survive the previous revision, so the finding is resolved the other way, by binding the attribute to the independent expert affinity curation for the same receptor, whose records are measured values on the pChEMBL scale. The definition states that this curation is independent of the activity table the registry's potency criterion reads, which is the coverage gap the record-based form was meant to close, that it does not replace that criterion, and that a material disagreement between the two is routed to a human.
  - round `run_01M4VABCW4TS9P3FJC0K7M8JC9` iteration 0 stage `promote` · `promote` → `promoted` · `disputed` · —

**Use**

- status `collapsed_away` on `rules@v3` — its attribute was merged into attr_vegfr3-curated-potency@v2 by clp_01M4WXKPVCG360VDRWPCXAM2EN; rule_vegfr3-curated-potency@v2 scores the quantity
- rule-set entry: —
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `False`
- measured coverage: —

---

### 40. VEGFR3 curated potency

- **attribute** `attr_vegfr3-curated-potency@v2` · **rule** `rule_vegfr3-curated-potency@v2` · **task** `task_01M4TWZXZEB1SQPS7H47C8BX01@v1`
- **all versions**: attribute `["attr_vegfr3-curated-potency@v1", "attr_vegfr3-curated-potency@v2"]`, rule `["rule_vegfr3-curated-potency@v1", "rule_vegfr3-curated-potency@v2"]`; supersedes `attr_vegfr3-curated-potency@v1`
- **record hashes**: attribute `e9d24be6d6afc7183fa6c29e38cc5343b83673d91dbc903701aa7325bfe93e3b`, rule `3755a0e654cb13742053fd86404bd80edd937b0490ae22012fd0df6755cc6113`
- **origin**: `task_mandated_template` · proposed by `{"id": "objective-criteria", "kind": "system", "role": "adapter_template"}` · derivation configuration `reference_disclosed`
- **derived from**: `{"field": "scope_entities[3]", "task_context": "task_01M4TWZXZEB1SQPS7H47C8BX01@v1"}` · dimension —
- **written by software**: `{"collapsed_by": "clp_01M4WXKPVCG360VDRWPCXAM2EN", "rule_collapsed_by": "clp_01M4WXKPVCG360VDRWPCXAM2EN"}`

**Recovery-comparison facets** (same operational quantity · applicability · decision semantics · threshold)

- **quantity**: VEGFR3 curated potency · subject `[{"target_chembl_id": "CHEMBL1955"}]` · unit `pChEMBL` · `quantitative` · aggregated by `median` · transform —
  - read from `["interaction_evidence_lookup"]` asking `["gtopdb_affinity", "pchembl_values"]`; evidence kinds `["curated_measurement"]`; determination bases —
  - measurement identity `b53b8d9fd631b4c0a3de8312a42006ce27923c412a946750dad904005fde6cd2`
- **applicability**: every candidate in the task's declared universe; no narrower population is recorded as a field · result kind `all_pass_set` · on inapplicable `unknown_blocks_recommendation` · condition field —
- **decision semantics**: role `preference` (`preference`) · predicate form `ordering` · direction `higher_better`
  - predicate: orders candidates by the quantity, higher_better; no cutoff
  - on missing `unknown_no_penalty` · on conflict `unknown_blocks_recommendation` · decision identity `679cfa67d0692965f56a8e87a014048519208763d17cce8b1d49c5ac8740ad75`
- **threshold**: `explicitly_absent` · basis `none_evidence_insufficient` · cutoff support —
- **comparable from fields alone**: `False`
  - gap: applicability: no structured population or condition field exists in this schema; what the criterion is and is not about is stated in the definition prose

**Operational definition**

> Median pChEMBL value over curated point measurements against VEGFR3 (CHEMBL1955)

- **unit** `pChEMBL` · **measurement kind** `quantitative` · **direction** `higher_better` · **aggregation** `median`
- **accepted evidence kinds** `["curated_measurement"]` · **accepted determination bases** —
- **applicability**: `{"applies_to_result_kind": "all_pass_set", "on_inapplicable": "unknown_blocks_recommendation", "stated_in_definition_only": true}`
- **expected change**: —
- **falsification test**: —
- **rationale**: VEGFR3 is a required target of the task

**Rule**

- **kind** `preference` · **predicate form** `ordering` · **cutoff** — (`explicitly_absent`) · **cutoff basis** `none_evidence_insufficient`
- **on missing** `unknown_no_penalty` · **on inapplicable** `unknown_blocks_recommendation` · **on conflict** `unknown_blocks_recommendation`
- **weight**: — — unweighted mean over observed contributions; the confirmed ordering method declares an empty weight vector

**Transform and computation**

- **value transform**: —
- **evidence key** `6dd02d0de11911e8575f648c78448f68fea4ba22b02c0737fc7a5448338fa08c` · 2 route(s) · literature-bound `False`
  - route `interaction_evidence_lookup` / `pchembl_values` · subject `{"target_chembl_id": "CHEMBL1955"}` · retrieval — · identifier scheme `inchikey`
  - route `interaction_evidence_lookup` / `gtopdb_affinity` · subject `{"target_chembl_id": "CHEMBL1955"}` · retrieval — · identifier scheme `inchikey`

**Parameter support**

- no executable scientific parameter: the rule carries no cutoff and the attribute declares no transform

**Verification, reported as three separate checks**

- quote check — of 0 cited claim(s), 0 carry `location.span_checked_against_source: true` and 0 carry `quote_verified` among their admission reasons
- numerical consistency — `value_in_quote` 0, `value_not_in_quote` 0, not recorded 0 (field: `claim.admission_reasons`)
- semantic support — `verification_status` — (field: `claim.verification_status`). a separate check from quote matching; unverified means it was never run, not that the quotation failed to match
- unresolved claim refs — —

**Supporting and conflicting claims**

- counts by polarity: —
- underlying experiment groups: not_recorded; these are literature-extracted claims and the store holds no underlying-experiment identity for them

**Critique, adjudication and authority**

- authority this criterion owes before it may score: none by the trigger table
- expert decisions: —
- machine adjudications: —
- open review items: —
- unresolved proposer/critic disputes: —
- exposure: derivation configuration `reference_disclosed` · historical-list exposure `["no expert decision exists for this criterion"]`
  - the sealed eleven-CQA list was not in the derivation agents' context; the known reference compound was disclosed, which is a separate exposure
- critic findings: —
- validator problems: —
- dissent recorded on the rule: —

**Lineage and lifecycle**

- pool lineage — at version —, state —
- parents — · children —
- merged away: —
- survived a collapse: `{"absorbed": ["attr_vegfr3-affinity-on-the-independent-expert-curation@v1"], "collapse_id": "clp_01M4WXKPVCG360VDRWPCXAM2EN", "reason_text": "2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL1955. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_vegfr3-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.", "routes_after": ["pchembl_values", "gtopdb_affinity"], "routes_before": ["pchembl_values"], "withdrawn": false}`
- refinement history: — (this criterion never entered the pool)

**Use**

- status `scoring` on `rules@v3`
- rule-set entry: `{"acceptable_value_sources": ["curated_measurement"], "attribute_ref": "attr_vegfr3-curated-potency@v2", "authority": "trigger_table", "confirmed_by": "auto:trigger_table", "cutoff_basis": "none_evidence_insufficient", "disputed": false, "on_states": ["unknown_no_penalty", "unknown_blocks_recommendation", "unknown_blocks_recommendation"], "rule_kind": "preference", "rule_ref": "rule_vegfr3-curated-potency@v2"}`
- scores while disputed: `False` · machine adjudicated: `False` · reads a collapsed attribute: `True`
- measured coverage: `{"assessed": 3177, "board": "lb_task_01M4TWZXZEB1SQPS7H47C8BX01_4", "observed": 34}`

---


## Sources behind the quotations

15 sources, each cited by one or more claims above.

| source id | title | container | issued | status | access | licence | identifiers | artifact sha256 |
|---|---|---|---|---|---|---|---|---|
| `src_doi_10.1002/cai2.70078` | Radioiodine-Refractory Differentiated Thyroid Cancer: Definition, Molecular Mechanisms, and Advances in Precision Therapy. | Cancer innovation | 2026-08-26 | `peer_reviewed_paper` | `full_text_available` | cc by-nc-nd | doi:10.1002/cai2.70078, pmid:42661840, pmcid:PMC13519041, epmc:42661840 | `197e20834112966397f5a270002163eaac57a9ee2a67dbe35bb7244a01ff22f2` |
| `src_doi_10.1039/d6ra01319h` | FLT3 inhibitors in AML: from classic scaffolds to next-generation approaches. | RSC advances | 2026-07-16 | `peer_reviewed_paper` | `full_text_available` | cc by-nc | doi:10.1039/d6ra01319h, pmid:42466468, pmcid:PMC13373645, epmc:42466468 | `6ce745bcc4710bd26c28e7555a64e6a3f338be0029c28cf44adca4f11ab633a0` |
| `src_doi_10.1111/cts.70713` | Fruquintinib: Mechanism of Action, Clinical, and Translational Science. | Clinical and translational science | 2026-10-01 | `peer_reviewed_paper` | `full_text_available` | cc by-nc | doi:10.1111/cts.70713, pmid:42765734, pmcid:PMC13592224, epmc:42765734 | `6c67635aef76e8d5f5f053c5117227a65e591e4b5ccea0528481b04f1efce8a0` |
| `src_doi_10.1111/iwj.70513` | The Adverse Impact of Tyrosine Kinase Inhibitors on Wound Healing and Repair. | International wound journal | 2025-04-01 | `peer_reviewed_paper` | `full_text_available` | cc by-nc-nd | doi:10.1111/iwj.70513, pmid:40251464, pmcid:PMC12008022, epmc:40251464 | `f7b5f6c2d0270a95d5b2a7ce7414718eb5f03fb164aae7725499a506502c600d` |
| `src_doi_10.2147/dddt.s559328` | Fibroblast Growth Factor Receptor (FGFR) Inhibitors for the Treatment of Cholangiocarcinoma: Key Therapeutic Developments and Knowledge Gaps. | Drug design, development and therapy | 2026-02-24 | `peer_reviewed_paper` | `full_text_available` | cc by-nc | doi:10.2147/dddt.s559328, pmid:41773262, pmcid:PMC12949802, epmc:41773262 | `e77ff607d769812e127ae2876641b5a2d27e434150747df51a9f5dc3d20d0e27` |
| `src_doi_10.32604/or.2026.078524` | Toxicities of Fruquintinib in Gastrointestinal Malignancies: A Systematic Review and Meta-Analysis. | Oncology research | 2026-09-14 | `peer_reviewed_paper` | `full_text_available` | cc by | doi:10.32604/or.2026.078524, pmid:42769859, pmcid:PMC13591366, epmc:42769859 | `10783acfe8fc070df85f9bcb1d9544d785a316660b212955cdc7c095bb205b83` |
| `src_doi_10.3389/or.2025.1612249` | Tyrosine-kinase inhibitors for lung or breast cancer and drug-drug interactions: a clinical guide. | Oncology reviews | 2025-09-22 | `peer_reviewed_paper` | `full_text_available` | cc by | doi:10.3389/or.2025.1612249, pmid:41059172, pmcid:PMC12497703, epmc:41059172 | `2ac4269877533210376afcb29c447a4fea3395ef3991f413dc13b114e2bb4505` |
| `src_doi_10.3390/ijms27156590` | Targeting Kinase Signaling in Glioblastoma: Structural Optimization, Blood-Brain Barrier Dynamics and Combinatorial Translational Strategies. | International journal of molecular sciences | 2026-07-24 | `peer_reviewed_paper` | `full_text_available` | cc by | doi:10.3390/ijms27156590, pmid:42589248, pmcid:PMC13466966, epmc:42589248 | `960f7ed62a3f333e3ef8f309304c39c37966e4f3b67b4d4aabfa38bbbc0100c4` |
| `src_doi_10.3390/ijms27188007` | Medicinal Chemistry of Small-Molecule c-Met Inhibitors: From Approved Therapies to Emerging Multitarget Anticancer Agents. | International journal of molecular sciences | 2026-09-09 | `peer_reviewed_paper` | `full_text_available` | cc by | doi:10.3390/ijms27188007, pmid:42794437, pmcid:PMC13606796, epmc:42794437 | `365408eeee90c88af9434426cf4c718a2fccdba9220a1ce2fd1d647ac8edc14d` |
| `src_doi_10.3390/ph18070959` | Beyond the Basics: Exploring Pharmacokinetic Interactions and Safety in Tyrosine-Kinase Inhibitor Oral Therapy for Solid Tumors. | Pharmaceuticals (Basel, Switzerland) | 2025-06-26 | `peer_reviewed_paper` | `full_text_available` | cc by | doi:10.3390/ph18070959, pmid:40732249, pmcid:PMC12299390, epmc:40732249 | `d2453d787bdd3e01a92d8e1f3d60d219076ffcbd0538f95e62aba9e2835a1912` |
| `src_doi_10.3390/pharmaceutics18091082` | Food Effects, Pharmacokinetic Drug-Drug Interactions, and Clinical Optimization of Oral Anticancer Agents. | Pharmaceutics | 2026-08-28 | `peer_reviewed_paper` | `full_text_available` | cc by | doi:10.3390/pharmaceutics18091082, pmid:42797257, pmcid:PMC13610770, epmc:42797257 | `3d9ca378e97bc211dfea76da0ce3cdf040e1023aeb8e6c2ee56174492b5ffc36` |
| `src_nbk_NBK563230` | Renal Clear Cell Cancer | StatPearls | 2023-01-01 | `reference_text` | `full_text_available` | https://creativecommons.org/licenses/by-nc-nd/4.0/ | nbk:NBK563230 | `20e2e92c0b08e783e5d79e9643268d1625d793fd3627e36c10f4ac190d7c78ab` |
| `src_nbk_NBK563322` | Tyrosine Kinase Inhibitors | StatPearls | 2023-01-01 | `reference_text` | `full_text_available` | https://creativecommons.org/licenses/by-nc-nd/4.0/ | nbk:NBK563322 | `d727c2fff92a115088da17964c0df1892c665398cd5504bb1fdce2d79d095d23` |
| `src_nbk_NBK572064` | Baricitinib | StatPearls | 2024-01-01 | `reference_text` | `full_text_available` | https://creativecommons.org/licenses/by-nc-nd/4.0/ | nbk:NBK572064 | `f6a173b76fc611b0ffeb58478604e0a259c7fe780d6f7142dc5cf02d11791861` |
| `src_nbk_NBK585049` | Nintedanib | StatPearls | 2024-01-01 | `reference_text` | `full_text_available` | https://creativecommons.org/licenses/by-nc-nd/4.0/ | nbk:NBK585049 | `f4f25af1e368ac84d05fc6297d0a06c967c61985a88fd8778d4b3ee50cde724c` |


## Lifecycle: what was pruned, deferred and merged away

Items that did not reach the registry, or reached it and were merged away. None of them scores on any confirmed rule set.

### Pool items in final state `withdrawn` (38)

- **CSF1R affinity from independent expert curation** · `cri_01M4V183ER0ZQ7XBX2FDDW7SPM@v2` · dimension `target_coverage` · unit `pChEMBL` · direction `higher_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4TX07ME8VWFJGK2PKNNGSEF` by `remove`
  - reason `withdrawn_by_reviser`: The material finding is correct and cannot be resolved by revision. Not one of the five cited quotes reports an affinity for this receptor on any concentration scale: the strongest of them is a row from a drug-target-indication table, and the rest establish only that the receptor matters and that agents covering it exist. An attribute whose measured quantity is a curated affinity in pChEMBL units therefore has no cited claim carrying that quantity, and under the rule that citations must actually support the attribute I cannot repair it by re-pointing it at claims that were never cited. Rewriting it into something the quotes do support, documented engagement, would duplicate the engagement attribute at index 0, which the instruction not to merge at this stage forbids. The intended contribution of this item, a second independent curation for a receptor that may be missing from the main activity table, is not lost: it survives as the engagement record attribute at index 0, and per-receptor curated potency is already in the registry.
  - definition: Median expert-curated affinity (pIC50, pKi or pKd on the pChEMBL scale) against the colony-stimulating-factor-1 receptor as recorded in the IUPHAR/BPS Guide to Pharmacology, used as a second, independently curated read of potency at this receptor.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (1):
    - `evidence_support` on proposal[1].attribute.definition · severity `material` · verdict `fail`: No cited quote reports any CSF1R affinity or any pChEMBL-scale value. All five quotes establish only that CSF1R is a target of interest; claim_01M4TX99MCZ572N3DGP2J10J8R is a target-indication table row.
  - validator problems: —
  - cited claims: `["claim_01M4TXQQ1HVWSC6J59BT8G7V5X", "claim_01M4TYG021F5G6RW5MBZBT8C67", "claim_01M4TY1R3PQYK1M6KYH9F9V093", "claim_01M4TYRS56BYQ5JA6Q413SSDTS", "claim_01M4TX99MCZ572N3DGP2J10J8R"]`
- **VEGFR3 affinity from independent expert curation** · `cri_01M4V183FBZ67QCVB3M4Q7WNCB@v2` · dimension `target_coverage` · unit `pChEMBL` · direction `higher_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4TX07ME8VWFJGK2PKNNGSEF` by `remove`
  - reason `withdrawn_by_reviser`: Both material findings are accepted. One cited quote concerns a peptide acting at VEGFR1 and VEGFR2, so it bears neither on VEGFR3 nor on an orally administered agent, and the only quantitative quote reports percent inhibition in a panel rather than an affinity on the pChEMBL scale. After removing those two, no remaining citation carries a VEGFR3 affinity value, so the attribute's declared quantity has no evidential support in its own claim set. As at index 5 I cannot import claims that were not already cited, and recasting the item as a documented-engagement flag would duplicate index 3. Withdrawn rather than left standing on quotes that do not measure what it claims to measure; the VEGFR3 coverage question is carried by index 3 and by the registry's VEGFR3 potency criterion.
  - definition: Median expert-curated affinity (pIC50, pKi or pKd on the pChEMBL scale) against vascular endothelial growth factor receptor 3 as recorded in the IUPHAR/BPS Guide to Pharmacology, used as a second, independently curated read of potency at the lymphangiogenic receptor.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (2):
    - `evidence_support` on claim_01M4TXF5QC8TYJSBFBSHEKMY1D · severity `material` · verdict `fail`: Quote concerns a VGB peptide acting on VEGFR1 and VEGFR2, not VEGFR3, and a peptide is outside an orally administered objective. It cannot support a VEGFR3 affinity attribute.
    - `evidence_support` on proposal[2].attribute.unit · severity `material` · verdict `fail`: No cited quote gives a VEGFR3/FLT4 affinity on any concentration scale; claim_01M4TY6CKGF5YW7VD6P967ZDZX gives percent inhibition, not an affinity on the pChEMBL scale.
  - validator problems: —
  - cited claims: `["claim_01M4TXXA8SKD5CQJSCYVNT1BJD", "claim_01M4TY6CKGF5YW7VD6P967ZDZX", "claim_01M4TXXAAZT417JZE2XG2YHH23", "claim_01M4TXXA85XZ422QZR26RBS3KQ", "claim_01M4TXF5QC8TYJSBFBSHEKMY1D"]`
- **Selectivity margin over kinases outside the required target set** · `cri_01M4V183GJVDM9G12BH5585GSP@v4` · dimension `target_coverage` · unit `fold` · direction `higher_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: No cited quote reports a fold margin measured at any of the five required receptors. The only two fold values in the evidence are a 30-fold margin whose endpoint is a kinase outside the required set, and a roughly 140-fold ratio between two members of one required receptor family, which this attribute's own definition excludes as a coverage failure rather than selectivity; the remaining cited quotes concern on-target and off-target toxicity limiting dose intensity and carry no ratio at all, so the unit fold rests on no cited value. The construction is also biased: as the smallest ratio over however many kinases were tested, it penalises a candidate screened against hundreds of kinases relative to one tested against a handful, and the evidence records no panel-size normalisation that would cure that. The off-target-breadth concern is carried by the panel-fraction attribute, which expresses the same evidence as a fraction of a stated panel and is retained.
  - definition: The smallest reported fold ratio between the compound's potency at any kinase outside the five required receptors and its potency at the required receptors, taken from a kinase-panel or kinome-wide profiling report. Only kinases outside the required set count: a margin obtained by sparing one of the five required receptors is not selectivity for this objective but a coverage failure, and is scored by the coverage and per-receptor potency criteria instead. Higher values mean the required receptors are engaged at concentrations well below those that touch unintended kinases.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (3):
    - `evidence_support` on claim_01M4TY6CMWT3R5CD88DX61AGMC · severity `material` · verdict `fail`: The only fold value cited is 'High selectivity and inhibitory activity to wild-type FLT3 and FLT3-D835Y with at least a 30-fold higher activity than other tested kinases'. The endpoint is FLT3, which is not one of the five required receptors, so the quote does not evidence a margin measured at the required receptors.
    - `evidence_support` on claim_01M4TX99745ECCBHTQVPHYATZ3 · severity `material` · verdict `fail`: The quote speaks of 'the combined detrimental effects of both on-target and off-target toxicities' limiting dose intensity. It carries no fold ratio and no kinase potencies, so it cannot support a quantity with unit 'fold'; the same applies to claim_01M4TX99086ZNX1P5HJ5SPN2PW and claim_01M4TYRRGK40JWMED9NZ7ZVY1A.
    - `candidate_symmetric_scrutiny` on attribute.definition · severity `material` · verdict `fail`: The value is 'the smallest reported fold ratio' over kinases outside the required set, with no normalisation for how many kinases were tested. A compound profiled against a 371-kinase screen (claim_01M4TXQQ0TQNSH090AG6QEDW7Z) has far more chances to produce a small minimum than one tested against a handful, so broadly profiled candidates are systematically penalised.
  - validator problems: —
  - cited claims: `["claim_01M4TY6CMWT3R5CD88DX61AGMC", "claim_01M4TY6CMDHEX119N8WY36JMGF", "claim_01M4TX99745ECCBHTQVPHYATZ3", "claim_01M4TYRRGK40JWMED9NZ7ZVY1A", "claim_01M4TX99086ZNX1P5HJ5SPN2PW"]`
- **Potency at the weakest-covered required receptor** · `cri_01M4V183HQE0DEHR20JKSR46YQ@v4` · dimension `target_coverage` · unit `nM` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: The attribute is a molar concentration in nanomolar, but no cited claim carries a numeric concentration at any of the five required receptors: the two quotes relied on state only that enzymatic inhibitory concentrations remain in the low-nanomolar range, with null value fields, and both concern one receptor family rather than the required set, so the weakest of the five cannot be established from the evidence. The construction also cannot be made symmetric on this evidence: as the worst value over however many of the five a source happens to report, it rewards a candidate reported at one receptor over an equally potent candidate reported at all five, and no cited quote supplies the per-receptor values that would let the count be normalised. Per-receptor potency is already measured by the five curated potency criteria in the registry, on a single logarithmic scale.
  - definition: The inhibitory concentration reported for the compound at whichever of the five required receptors it engages least potently, expressed as a molar concentration in nanomolar. Only values on a concentration scale are admitted; a pChEMBL value is an inverse logarithm and must not be entered here, because mixing the two scales reverses the ranking, and per-receptor pChEMBL potency is already covered by the registry criteria. Where the source reports potency for only some of the required receptors, the value is the weakest of those reported and the definition records how many receptors it covered. Lower concentration is better.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (3):
    - `evidence_support` on claim_01M4TXQQ072P05S5A0EN99KXXK · severity `material` · verdict `fail`: The attribute is a molar concentration in nM, but the quote states only that 'in-vitro enzymatic IC50 values remain in the low-nanomolar range' and the claim's value field is null. No number is available, so no nM value is traceable to this claim; claim_01M4TYG095KQSAJK11CPP0R5ER ('low nanomolar IC50 values') is numberless in the same way.
    - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: Both cited claims concern FGFR1-3 only (TYRA-200 and infigratinib). Neither reports potency at CSF1R, VEGFR1, VEGFR2 or VEGFR3, so the cited evidence cannot establish the 'weakest of the five required receptors' that the attribute names.
    - `candidate_symmetric_scrutiny` on attribute.definition · severity `material` · verdict `fail`: 'Where the source reports potency for only some of the required receptors, the value is the weakest of those reported.' Because the score is a minimum over however many receptors happen to be reported and is not normalised by that number, a candidate with potency reported at one receptor scores better than an equally potent candidate reported at all five. Coverage of the data, not of the receptors, drives the ranking.
  - validator problems: —
  - cited claims: `["claim_01M4TXQQ072P05S5A0EN99KXXK", "claim_01M4TYG095KQSAJK11CPP0R5ER"]`
- **Measured enzymatic potency at the required receptors** · `cri_01M4V183JABBDZR6NWP9FXQ3B8@v4` · dimension `target_coverage` · unit `nM` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: No cited claim reports a numeric enzymatic inhibitory concentration at any required receptor: one quote has a null value, one spans the low-nanomolar to subnanomolar range for agents directed at a receptor outside the required set, and one says only that docking is not proof of inhibition, so the nanomolar axis is traceable to no cited value. The definition also pools the required receptors into one median, which hides a weakly engaged receptor behind strongly engaged ones and contradicts the limiting-receptor logic defined on the same numbers. Measured per-receptor potency is already carried by the registry's five curated potency criteria.
  - definition: The inhibitory concentration of the compound against the required receptors measured in a cell-free enzymatic or biochemical assay, in nanomolar. Cellular potency values, growth-inhibition values and docking or model predictions are excluded, since mixing assay formats on one scale makes the values incomparable. Where several enzymatic values exist the median is taken. Lower is better, with no threshold: the cited quotes report what has been achieved and do not state a required potency.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (2):
    - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: No cited claim reports a numeric enzymatic IC50 at any of the five required receptors. claim_01M4TXQQ072P05S5A0EN99KXXK has value null; claim_01M4TYRRWQVKDGTYQ971FNFHTB spans 'the low-nanomolar to subnanomolar range' for c-Met-directed and multitarget agents; claim_01M4TYRS2Q0R5839WKYNVMD2DR is about docking not being proof of inhibition. The nM scale is therefore not traceable to a cited value.
    - `unit_applicability_consistency` on attribute.aggregation · severity `material` · verdict `fail`: The definition pools 'the inhibitory concentration of the compound against the required receptors' and takes a median, without saying which receptor the value belongs to. A median over CSF1R, VEGFR1/2/3 and FGFR1 values hides a weak receptor behind strong ones and contradicts the weakest-receptor logic of proposal 3, which is defined on the same numbers.
  - validator problems: —
  - cited claims: `["claim_01M4TXQQ072P05S5A0EN99KXXK", "claim_01M4TYRRWQVKDGTYQ971FNFHTB", "claim_01M4TYRS2Q0R5839WKYNVMD2DR"]`
- **Free-concentration margin over the inhibitory concentration at the required receptors** · `cri_01M4V183QEBEB5AFND950Y571R@v4` · dimension `target_coverage` · unit `fold` · direction `higher_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: Neither cited quote pairs a free concentration with an inhibitory concentration: one speaks qualitatively of limited systemic exposure and small rightward shifts in inhibitory concentration, and the other reports a 2.40 nM inhibitory concentration at a receptor outside the required set with no unbound concentration beside it. The declared unit fold therefore rests on no cited value, and the proposal itself expects the attribute to return unknown for every candidate, so it cannot rank anything.
  - definition: The ratio of the free (unbound) plasma concentration achieved at a tolerated oral dose to the inhibitory concentration at the required receptors, expressed as a fold margin. Only reported pairs of values measured in the same source are admitted, so that the numerator and denominator are commensurable. Higher margin is better. Where no source reports both quantities the attribute returns unknown with no penalty.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (1):
    - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: Neither cited claim contains a paired free concentration and inhibitory concentration. claim_01M4TXQQCAN1HENYN157FH1G8X speaks qualitatively of 'conditions of limited systemic exposure' and 'small rightward shifts in IC50'; claim_01M4TYRRN7KH6S7BK555AQ0Y74 gives an IC50 of 2.40 nM for c-Met, which is not a required receptor and is not paired with an unbound concentration. The declared unit 'fold' rests on no cited value.
  - validator problems: —
  - cited claims: `["claim_01M4TXQQCAN1HENYN157FH1G8X", "claim_01M4TYRRN7KH6S7BK555AQ0Y74"]`
- **Binding mode at the required receptors** · `cri_01M4V183R013R1JXS04K8NM3Z5@v2` · dimension `target_coverage` · unit — · direction `non_directional`
  - left the pool at stage `refine` iteration 1 of round `run_01M4TX07ME8VWFJGK2PKNNGSEF` by `remove`
  - reason `withdrawn_by_reviser`: Both validator findings are structural and cannot both be satisfied without changing what the item measures. Binding mode is a category, active-conformation ATP-competitive, inactive-conformation back-pocket, allosteric or covalent, and the cited quotes support no ordering among those categories for this objective: they say the conserved ATP pocket is what lets one molecule hit several kinases, that active-conformation binders show broad activity which limits their selectivity, that inactive-conformation binders are often more selective and correspondingly narrower, that allosteric sites are the least conserved, and that covalent engagement sustains inhibition regardless of conformational bias. That is a genuine trade-off with no stated winner, which is why the item was proposed as an exploratory consideration with direction non_directional. The validator requires that an ordering rule be a preference, and that a literature-bound attribute be quantitative with a unit. Forcing a direction onto these categories would assert a preference the claims do not support, and inventing a numeric proxy such as a count of conformational states engaged would manufacture a quantity no cited quote reports. Withdrawn rather than falsified into compliance. The underlying evidence is not lost: the same quotes support the selectivity-margin and panel-fraction attributes, which measure the consequence of binding mode instead of the category itself.
  - definition: The reported binding mode of the compound at the required receptors, classified as active-conformation ATP-competitive, inactive-conformation back-pocket binding, allosteric outside the ATP cleft, or covalent. Recorded as a category, not ranked, because the claims support no single best mode for this objective.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "unknown_no_penalty", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "exploratory_consideration"}`
  - critic findings: —
  - validator problems (2):
    - schema: schema: an ordering rule ranks candidates, so it must be a preference
    - schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - cited claims: `["claim_01M4TX9911YZS36QB50GFE3HAC", "claim_01M4TY6CARS3T1DDQ3Y3J76HPT", "claim_01M4TXF4AS029SX0Y5N1Z3EBX5", "claim_01M4TY6CSFNK1PDW03A2H6ESPQ", "claim_01M4TYRRSCQ3S0TKDN0AQGZRM0", "claim_01M4TY6CV3G0JK5HECMXWZNKBH", "claim_01M4TYRRR9VXCAGFYEP8QQGQ5Q", "claim_01M4TY6CRVHP4PE6T41RY2X1FG"]`
- **Number of resistance variants of the required receptors against which activity is retained** · `cri_01M4V183RCWHMFPK60XJQBHH9R@v4` · dimension `target_coverage` · unit `count of variants` · direction `higher_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: The attribute counts named kinase-domain substitutions of the required receptors, and no cited claim names a variant of any of the five: every cited variant belongs to a receptor outside the required set, so the attribute as defined has no supporting evidence at all. Retained activity against receptor mutants is also a durability property that neither the objective nor the stated constraint names, and as a count of variants tested it would rise with how much resistance profiling a compound has received, scoring an untested agent the same as one tested and found vulnerable.
  - definition: The number of distinct, individually named kinase-domain substitutions of the required receptors (for example gatekeeper, molecular-brake or activation-loop substitutions) against which the compound is reported to retain measured inhibitory activity. A variant counts only if the source names it and reports a measured readout against it; a general statement that a compound is robust to resistance counts for nothing. The system in which retention was demonstrated, enzymatic, cellular or xenograft, is recorded with the count. Higher is better.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (3):
    - `evidence_support` on supporting_claim_ids · severity `blocking` · verdict `fail`: The attribute counts named kinase-domain substitutions 'of the required receptors', but every cited variant belongs to a receptor outside the required set: FGFR2 in claim_01M4TXQPZPC6FWHNEQHPJD3104 ('V565I/L') and claim_01M4TXQR3HR9HHAWYKETM102GF ('V565 in FGFR2'), and FLT3 in claim_01M4TY6CX0ZJXG0BT7FM5TG256, claim_01M4TY6CTBC31H59HMNZ0NT0YJ ('F691') and claim_01M4TY6CSYWYZQZ0ZY9QPHYKC8 ('D835 variants'). No cited claim names a variant of CSF1R, VEGFR1, VEGFR2, VEGFR3 or FGFR1, so the attribute as defined has no supporting evidence at all.
    - `objective_conformance` on attribute.definition · severity `material` · verdict `fail`: The objective asks for concurrent engagement of five named receptors with a profile suitable for clinical development. Retained activity against kinase-domain mutants of those receptors is a durability property that the stated objective and constraints do not mention; claim_01M4TX99FCH8KV8DZN711CH4ZT motivates it only as a general bottleneck in targeted therapy.
    - `candidate_symmetric_scrutiny` on attribute.direction · severity `material` · verdict `fail`: With direction higher_better and aggregation max over a count of named variants, the score rises with how much resistance profiling a compound has received. An agent never tested against variants scores zero, indistinguishable from one tested and found vulnerable.
  - validator problems: —
  - cited claims: `["claim_01M4TXQPZPC6FWHNEQHPJD3104", "claim_01M4TY6CX0ZJXG0BT7FM5TG256", "claim_01M4TY6CTBC31H59HMNZ0NT0YJ", "claim_01M4TXQR3HR9HHAWYKETM102GF", "claim_01M4TX99FCH8KV8DZN711CH4ZT", "claim_01M4TY6CSYWYZQZ0ZY9QPHYKC8"]`
- **Breadth of tumour-microenvironment compartments covered by one molecule** · `cri_01M4V183RS8K2XQT8F5G19DW8S@v2` · dimension `target_coverage` · unit `count of compartments` · direction `higher_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4TX07ME8VWFJGK2PKNNGSEF` by `remove`
  - reason `withdrawn_by_reviser`: Three material findings, and together they leave nothing worth keeping. The decisive one is that the four microenvironment compartments are a deterministic relabelling of the five-receptor count at index 7: every compartment is assigned from receptor identity alone, so scoring both would let one breadth signal count twice on the same leaderboard. The second is that the fibroblast and stromal compartment rested on a quote tying FGFR1 to glioma stem-cell maintenance, invasion and radioresistance, which is tumour-cell-intrinsic biology and not a stromal compartment at all, so one of the four compartments was not evidenced. The third is that aggregation by maximum over a compartment count rewards the molecule with the most generous review rather than the better pharmacology. I could repair the aggregation and drop the mis-cited compartment, but the double-counting objection would survive both repairs, and the instruction at this stage forbids merging the item into index 7. Withdrawn. The microenvironmental reading of the objective that motivated it is preserved in the rationales of the per-receptor engagement attributes, which record why these particular five receptors were named together.
  - definition: The number of distinct microenvironmental compartments that the compound's reported target list reaches: the macrophage and myeloid compartment through the colony-stimulating-factor-1 receptor, the vascular endothelial compartment through the vascular endothelial growth factor receptors, the lymphatic endothelial compartment through the lymphangiogenic receptor, and the fibroblast and stromal compartment through fibroblast growth factor receptor 1.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (3):
    - `evidence_support` on claim_01M4TXF4F1YW5CXVC4K1KKQ43T · severity `material` · verdict `fail`: The fibroblast and stromal compartment rests on this quote, which ties FGFR1 to glioma stem-cell maintenance, invasion and radioresistance - tumour-cell-intrinsic biology, not a fibroblast or stromal compartment.
    - `objective_conformance` on proposal[9].attribute.definition · severity `material` · verdict `fail`: The four compartments are a deterministic relabelling of the five-receptor count in proposal[3]; scoring both lets one breadth signal count twice in the same leaderboard.
    - `candidate_symmetric_scrutiny` on proposal[9].attribute.aggregation · severity `material` · verdict `fail`: aggregation max over a compartment count takes the most generous source, so the score rises with how many reviews describe a molecule rather than with its pharmacology.
  - validator problems: —
  - cited claims: `["claim_01M4TXQPVXFWJBS1GPP1B7QTCX", "claim_01M4TXQQ2QWTWJM3HWNWMHJ27Z", "claim_01M4TXQQ259SAS711B2STZ8NB2", "claim_01M4TXXA8SKD5CQJSCYVNT1BJD", "claim_01M4TXF4F1YW5CXVC4K1KKQ43T", "claim_01M4TXF4FQF24CPE4ZHR2NAJF9"]`
- **Highest development phase reached** · `cri_01M4V183SYFKKC91BMB6W7Z6TW@v2` · dimension `target_coverage` · unit `phase` · direction `higher_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4TX07ME8VWFJGK2PKNNGSEF` by `remove`
  - reason `withdrawn_by_reviser`: Two blocking findings and a material one, and all three are right. The highest development phase attained is a record of how far a molecule has already been taken, not a pharmacological property of it, and with direction higher_better it ranks approved agents at the top by construction, so no investigational candidate could ever equal them however good its profile; that alone makes it a candidate-asymmetric criterion rather than a measurement. Worse, two of the item's own citations are counter-evidence to its direction: one records a phase III trial of an agent with this coverage that failed its primary endpoint with no overall survival difference, and another a phase II trial terminated prematurely for lack of efficacy with 100 percent total adverse events. A high phase therefore coexists with failure, and the rule as written rewards exactly those records. The material finding completes the case: the objective asks for a profile suitable for clinical development, which is a different quantity from development already attained and is not evidenced by it. There is no sharpening that preserves the item's meaning and removes these defects, so it is withdrawn rather than rewritten.
  - definition: The highest clinical development phase on record for the compound, from the molecule record (0 to 4, where 4 denotes approval). Read as evidence that a molecule with this target coverage has been taken into and through clinical development, not as evidence of potency.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "unknown_no_penalty", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (3):
    - `candidate_symmetric_scrutiny` on proposal[10].attribute.definition · severity `blocking` · verdict `fail`: max_phase records how far a molecule's development has already gone, not a pharmacological property. With direction higher_better it ranks approved agents top by construction, and no investigational candidate can ever equal them however good its profile.
    - `counter_evidence_considered` on proposal[10].attribute.direction · severity `blocking` · verdict `fail`: claim_01M4TXF59553HZWC2HK5ZCQR5Q (phase III missing its endpoint) and claim_01M4TXF5AEGGCMQT9W8FN5A5HW (terminated for futility, 100% AEs) are cited and show high phase coexisting with failure, yet higher_better rewards exactly those records.
    - `objective_conformance` on proposal[10].attribute.name · severity `material` · verdict `fail`: The objective asks for a profile SUITABLE for clinical development; development already attained is a different quantity and is not evidence of suitability.
  - validator problems: —
  - cited claims: `["claim_01M4TXXAZ5YEF4MGPT8R1P8XAT", "claim_01M4TY6CGXSG3209BJX443Q304", "claim_01M4TXF57RCRCWFP47TV2S48VJ", "claim_01M4TXQR0PR4DVVF1MCRGNPABN", "claim_01M4TXF59553HZWC2HK5ZCQR5Q", "claim_01M4TXF5AEGGCMQT9W8FN5A5HW"]`
- **Heavy atom count as a proxy for the size cost of multi-receptor pharmacophores** · `cri_01M4V183TB7JX5X51RTWFSD9AX@v2` · dimension `target_coverage` · unit `count` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4TX07ME8VWFJGK2PKNNGSEF` by `remove`
  - reason `withdrawn_by_reviser`: Both material findings are accepted and are fatal in combination. The first is that the item's own citations state multi-receptor pharmacophores are necessarily larger, since structural extensions reaching additional subpockets increase molecular size and rigidity and molecular hybridisation raises size and complexity, so a lower_better direction on size penalises precisely the concurrent five-receptor coverage this objective requires and the coverage attribute rewards; the pool would be scoring one property in both directions. The second is evidential: no cited quote gives a heavy-atom count or any size threshold at all, and the size claim that comes closest is made in the service of central-nervous-system penetration, a compartment this objective does not require. I considered flipping the direction or converting it to a window, but no cited value exists to place a window on, and the molecular-weight attribute already in the pool carries molecular size with an explicitly stated numeric band taken from a quote. Withdrawn as redundant and unevidenced.
  - definition: The number of heavy (non-hydrogen) atoms in the molecule, computed from its structure, used as a size proxy for how much pharmacophore has been added to reach several receptors at once.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "unknown_no_penalty", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (2):
    - `objective_conformance` on proposal[11].attribute.direction · severity `material` · verdict `fail`: claim_01M4TXF562VJSK1YXFMCET5RS7 and claim_01M4TYRS14XFBSD59W2TJQSNEW state that multi-receptor pharmacophores are necessarily larger, so lower_better on size penalises the concurrent five-target coverage the objective requires and proposal[3] rewards.
    - `evidence_support` on proposal[11].attribute.definition · severity `material` · verdict `fail`: No cited quote gives a heavy-atom count or any size threshold, and claim_01M4TXF562VJSK1YXFMCET5RS7 ends at CNS penetration, which the objective does not require.
  - validator problems: —
  - cited claims: `["claim_01M4TXF562VJSK1YXFMCET5RS7", "claim_01M4TYRS14XFBSD59W2TJQSNEW", "claim_01M4TYRRXE8SRA8KRRKWVZ8QJG", "claim_01M4TYRRW4JR1100CWQFH418SC"]`
- **Topological polar surface area** · `cri_01M4V1FPD7WXZMN2DGFFH5GZJ9@v6` · dimension `oral_bioavailability` · unit `Å²` · direction `lower_better`
  - left the pool at stage `refine` iteration 2 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: The descriptor this attribute scores is named in only one cited quote, and that quote's endpoint is central-nervous-system penetration, which this objective does not name: polar surface area below approximately 90 square angstroms together with limited hydrogen bonding correlating with improved brain penetration. The quotes that do carry a membrane-permeability or oral-absorption endpoint name something else, an excess of polar functional groups, particularly hydroxyl and amine moieties, increasing solvation and reducing membrane permeability, and polarity alongside molecular weight, lipophilicity and ionisation state as determinants of passive transcellular diffusion, so the direction for this particular computed descriptor is an inference rather than a quoted relationship. The mechanism those on-endpoint quotes do state is read directly by the hydrogen-bond donor count attribute proposed for this dimension, which counts the hydroxyl and amine hydrogens the quotes name, so withdrawing this one loses no evidenced property and removes a descriptor scored on an extrapolated endpoint.
  - definition: The computed topological polar surface area of the molecule. Lower values are preferred weakly and monotonically, with no threshold. Three limits are part of the definition. The direction rests on the cited quotes whose endpoint is membrane permeability and oral absorption rather than brain penetration: an excess of polar functional groups, particularly hydroxyl and amine moieties, increases solvation and reduces membrane permeability, and polarity is named among the determinants of passive transcellular diffusion and of susceptibility to active efflux transporters. The only numeric figure in the cited evidence, approximately 90 square angstroms, is stated with central-nervous-system penetration as its endpoint, which this objective does not name, so it is recorded but used neither as a cutoff nor as the basis of the direction. And the cited evidence describes a genuine trade-off, since adding polar or ionisable groups improves aqueous solubility while raising polar surface area and reducing passive diffusion; a monotone preference captures only one side of that, so this attribute is subordinate to the measured oral bioavailability attribute and must not outweigh it.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "unknown_no_penalty", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (1):
    - `evidence_support` on attribute.definition · severity `material` · verdict `fail`: The direction is now rested on claim_01M4TXF4S4XVHCR3R6M8T3CTYJ ('hydroxyl and amine moieties (OH, NH), increases solvation and reduces membrane permeability') and claim_01M4TXF4KFBDJF1ASFM4NTQM19 ('molecular weight, lipophilicity, polarity, and ionization state'), neither of which names topological polar surface area. The only quote naming TPSA is claim_01M4TXF4RG4P3S9CV0926P5XV9, whose endpoint the definition correctly sets aside as central-nervous-system penetration. The scored descriptor therefore has no on-endpoint quote naming it, and the direction is an inference from polarity generally.
  - validator problems: —
  - cited claims: `["claim_01M4TXF4S4XVHCR3R6M8T3CTYJ", "claim_01M4TXF4KFBDJF1ASFM4NTQM19", "claim_01M4TXF50Y236KPK5VTCY742X0", "claim_01M4TXF4RG4P3S9CV0926P5XV9", "claim_01M4TXF51XDDHCAZG3WWD6VE4T", "claim_01M4TXF4W21JKF32KEPR8E7MP1"]`
- **Hydrogen-bond acceptor count** · `cri_01M4V1FPE9KRE1559CJWBD43TY@v2` · dimension `oral_bioavailability` · unit `count` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4V43E8GDH8GF8M633VTWDQJ` by `remove`
  - reason `withdrawn_by_reviser`: The blocking finding is correct and I cannot repair it. No cited quote mentions hydrogen-bond acceptors at all: the polarity quote names hydroxyl and amine moieties, which are donors, and the second quote concerns efflux-transporter liability of heterocyclic cores. The definition's assertion that the claims name both donors and acceptors is therefore not borne out by any quote in the request, and the lower_better direction on acceptor count has no cited support, the only polarity figure anywhere in the set being a polar surface area value. The further material finding is also right and reinforces withdrawal: polar surface area, donor count, acceptor count and rotatable bonds all draw on one source passage, so scoring four of them lets a single physicochemical argument outvote the measured bioavailability endpoint. Acceptor count is the weakest of the four and the only one with no quote behind it, so it is the right one to drop. Donors and polar surface area remain, each with its own quoted sentence.
  - definition: Computed number of hydrogen-bond acceptors in the molecule, recorded alongside donor count because the claims name both as components of the polarity that governs absorption.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (3):
    - `evidence_support` on proposal[16].attribute.definition · severity `blocking` · verdict `fail`: No cited quote mentions hydrogen-bond ACCEPTORS: claim_01M4TXF4S4XVHCR3R6M8T3CTYJ names hydroxyl and amine (donor) moieties and claim_01M4TXF4XPX9V4KVAAZFKRK38T concerns P-gp/BCRP liability. The definition's 'the claims name both' is borne out by no quote in the request.
    - `unit_applicability_consistency` on proposal[16].attribute.direction · severity `material` · verdict `fail`: lower_better on acceptor count has no cited support; the only polarity figure anywhere in the supporting set is a TPSA value.
    - `objective_conformance` on proposal[16].rule.rule_kind · severity `material` · verdict `fail`: Proposals 14, 15, 16 and 17 each score a component of the same polarity-and-flexibility construct from one source passage, so a single physicochemical argument is counted four times against the measured endpoint in proposal[18].
  - validator problems: —
  - cited claims: `["claim_01M4TXF4RG4P3S9CV0926P5XV9", "claim_01M4TXF4S4XVHCR3R6M8T3CTYJ", "claim_01M4TXF4XPX9V4KVAAZFKRK38T"]`
- **Rotatable bond count** · `cri_01M4V1FPETHNTHZ8256MAKRVJ5@v4` · dimension `oral_bioavailability` · unit `count` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: The caveat the definition attributed to the evidence, that increased rigidity can reduce aqueous solubility, appears in no cited quote: one quote is only about reduced flexibility improving passive diffusion, one is about the interplay of size, lipophilicity, polarity and ionisation, and one lists permeability, solubility, metabolic stability and efflux without mentioning rigidity. Removing it leaves the preference with no counter-evidence and, more seriously, with no endpoint anchor: the sole flexibility quote states enhanced central-nervous-system exposure as its endpoint and the second states brain unbound concentrations, and this objective names no central-nervous-system compartment, so the attribute would be scored entirely on an extrapolation from a different endpoint with no measured anchor. Unlike polarity, flexibility has no cited quote tying it to oral absorption, so the gap cannot be closed from the evidence given.
  - definition: The computed number of rotatable bonds, used as the measure of conformational flexibility. Fewer is preferred weakly and monotonically, with no threshold. The definition records what the evidence does and does not say: the cited source states that reduced conformational flexibility generally improves passive membrane diffusion and gives more favourable pharmacokinetic profiles with the endpoint stated as central-nervous-system exposure, not oral bioavailability, so applying it to intestinal absorption is an extrapolation from a related permeability setting and is flagged as such. The same evidence notes that increased rigidity can reduce aqueous solubility, so the preference is weak and subordinate to the measured bioavailability and dissolution attributes.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "unknown_no_penalty", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (2):
    - `counter_evidence_considered` on attribute.definition · severity `material` · verdict `fail`: The definition asserts 'The same evidence notes that increased rigidity can reduce aqueous solubility'. No cited claim states this: claim_01M4TXF4V8HZY42HMWHWN84YK6 is only about reduced flexibility improving diffusion, claim_01M4TXF4W21JKF32KEPR8E7MP1 is about the interplay of size, lipophilicity, polarity and ionisation, and claim_01M4TXF4JS64F17N8PVA67M294 lists permeability, solubility, metabolic stability and efflux without mentioning rigidity. The caveat is attributed to evidence that does not contain it.
    - `objective_conformance` on claim_01M4TXF4V8HZY42HMWHWN84YK6 · severity `material` · verdict `fail`: The quote's endpoint is 'improved passive diffusion across biological membranes and more favorable pharmacokinetic profiles, supporting enhanced CNS exposure'. The definition acknowledges that applying this to intestinal absorption is an extrapolation; the attribute is nonetheless scored on that extrapolation with no measured anchor.
  - validator problems: —
  - cited claims: `["claim_01M4TXF4V8HZY42HMWHWN84YK6", "claim_01M4TXF4W21JKF32KEPR8E7MP1", "claim_01M4TXF4JS64F17N8PVA67M294"]`
- **Width of the reported oral bioavailability range** · `cri_01M4V1FPG2SFVRCJV7BCSTQ2XY@v4` · dimension `oral_bioavailability` · unit `percentage points (range width)` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: Only an explicitly reported range qualifies, while a missing range is unknown with no penalty, so the attribute scores a candidate whose source discloses its variability and leaves a candidate reporting a bare point estimate unscored: disclosure is penalised and silence is neutral. That asymmetry is intrinsic to the quantity as defined and cannot be removed from the cited evidence, which contains a single reported range. The variability concern is carried instead by the derivation, prandial-state and formulation qualifiers now attached to the reported oral bioavailability attribute, which conditions values rather than scoring the act of disclosure.
  - definition: The width, in percentage points, of an explicitly reported range of oral bioavailability for the compound, for example a stated 13.5 to 38.9 percent range yielding a width of 25.4 points. Only an explicitly reported range qualifies. A coefficient of variation is a different quantity and is not admitted here, because the two cannot be ordered against each other even though both are written with a percent sign. Narrower is better, independently of the mean. The attribute rests on a single worked example in the cited evidence and is expected to return unknown for most candidates, which carries no penalty.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (1):
    - `candidate_symmetric_scrutiny` on rule.on_missing · severity `material` · verdict `fail`: Only an explicitly reported range qualifies and a missing range is unknown_no_penalty, so a candidate whose source discloses its variability is scored against a candidate whose source reports a bare point estimate and is not scored at all. Disclosure is penalised and silence is neutral, the opposite of the treatment proposal 17 insists on for untested interactions.
  - validator problems: —
  - cited claims: `["claim_01M4TXXAJQY7J3GZ65NVXCF6E2", "claim_01M4TYZ66EJHCHWW87RPZ8WQ39", "claim_01M4TYZ6NHPX2MBM8PE5G7ZAVW", "claim_01M4TX98YYX1FVXEK7AB58N46T"]`
- **Number of absorption properties rated low in the assigned Biopharmaceutics Classification System class** · `cri_01M4V1FPJ1V9SRWMXEMTHHSDEX@v6` · dimension `oral_bioavailability` · unit `count of low-rated absorption properties` · direction `lower_better`
  - left the pool at stage `refine` iteration 2 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: The count depends on a mapping from each Biopharmaceutics Classification System class to which of the two absorption properties it rates as low, and the cited evidence states only part of it: one quote names class 2 and class 4 as the classes in which dissolution rather than permeability limits absorption, while nothing cited says that class 1 is high on both or that class 3 is high in solubility and low in permeability. Two of the four class-to-count assignments are therefore not traceable to the evidence supplied, and supplying them from general pharmaceutical knowledge would be importing a mapping this request does not contain. The property the evidence does state, that many agents of this class are lipophilic poorly soluble compounds whose absorption is dissolution-limited and which depend on formulation engineering, is stated qualitatively and carries no admissible per-candidate number, and the attribute's own falsification test prescribes withdrawal where class assignments cannot be read. The measured food-effect and oral bioavailability attributes carry the absorption consequence directly.
  - definition: The number of the two absorption properties, aqueous solubility and intestinal permeability, that the compound's assigned Biopharmaceutics Classification System class rates as low: zero for class 1 (high solubility, high permeability), one for class 2 (low solubility, high permeability) and one for class 3 (high solubility, low permeability), and two for class 4 (low on both). The quantity is a count because the four classes are categories rather than points on a scale: ordering the class numbers themselves would rank a low-solubility class above a low-permeability class, which the cited evidence does not support, whereas the count ranks only on how many of the two properties are rated low and leaves classes 2 and 3 equal. The class assigned, and therefore which property is the low one, is recorded with the value. Where a source states low aqueous solubility or dissolution-limited absorption without assigning a class, the value is recorded as unknown with that statement noted rather than converted into a class or a count. The cited evidence warns that this classification does not reliably predict the direction or magnitude of a food effect for class 2 compounds, so this attribute never substitutes for the measured food-effect attribute. Fewer low-rated properties is better.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (1):
    - `evidence_support` on claim_01M4TYZ65DFF1FRS4HCR4WBXHN · severity `material` · verdict `fail`: The quote names only 'class II or class IV drugs in which dissolution rather than permeability limits absorption'. The mapping the count depends on for the other two classes, class 1 as high on both and class 3 as high solubility with low permeability, appears in no cited quote, so two of the four class-to-count assignments are not traceable to the evidence.
  - validator problems: —
  - cited claims: `["claim_01M4TYZ65DFF1FRS4HCR4WBXHN", "claim_01M4TYZ664TJTQ36SFFCF9BH11", "claim_01M4TXF4PGYBH8PGC6E4PX2YGE", "claim_01M4TXF51XDDHCAZG3WWD6VE4T", "claim_01M4TXF4JS64F17N8PVA67M294"]`
- **Intestinal efflux ratio** · `cri_01M4V1FPJJ8GTNAN97YNT5KWPV@v4` · dimension `oral_bioavailability` · unit `efflux ratio` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: No cited claim reports a basolateral-to-apical over apical-to-basolateral permeability ratio or any numeric efflux ratio. Every cited quote is a qualitative substrate statement of exactly the kind the definition itself says must be recorded as unknown, and one is a population genotype frequency, a different quantity on a different subject, so the declared ratio axis rests on no cited value and the attribute returns unknown for every candidate. The liability it aimed at is measured directly by the transporter-mediated exposure-change attribute, which is scored on reported exposure changes rather than on an unreported ratio.
  - definition: The efflux ratio of the compound measured in a polarised cell monolayer, that is the basolateral-to-apical permeability divided by the apical-to-basolateral permeability, recorded with the cell system and with which transporter the ratio was attributed to. A ratio near 1 means no net efflux; larger ratios mean net absorption is actively opposed at the intestinal barrier. Lower is better. Where a source states only that the compound is or is not a transporter substrate without a ratio, the value is recorded as unknown with that statement noted, because a qualitative substrate label cannot be ordered against a measured ratio.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (2):
    - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: No cited claim reports a basolateral-to-apical over apical-to-basolateral ratio or any numeric efflux ratio. The cited evidence is qualitative substrate statements (claim_01M4TYZ66TAGFJ47BTQ9CFCDFT, claim_01M4TXF4XPX9V4KVAAZFKRK38T, claim_01M4TZ40Q17HK13ADR41027G89, claim_01M4TXF4Y6W5TZ6XJPEVGW83NS) of exactly the kind the definition says must be recorded as unknown, so the declared unit rests on no cited value.
    - `evidence_support` on claim_01M4TZ40QFJPX42BM6SBAAY369 · severity `material` · verdict `fail`: This quote reports population genotype frequencies, 'ABCB1 variants G2677T/A and C3435T were reported as 64% and 61.6%, respectively, in the South Indian population'. Variant frequency is a different quantity on a different subject from a compound's efflux ratio and supports nothing in this attribute.
  - validator problems: —
  - cited claims: `["claim_01M4TYZ66TAGFJ47BTQ9CFCDFT", "claim_01M4TXF4XPX9V4KVAAZFKRK38T", "claim_01M4TZ40Q17HK13ADR41027G89", "claim_01M4TZ40R0WDGAEM5S2FZKVK4D", "claim_01M4TZ40QFJPX42BM6SBAAY369", "claim_01M4TY1REX3SM4ND6KESQHPZAD", "claim_01M4TXF4Y6W5TZ6XJPEVGW83NS"]`
- **Presystemically extracted fraction of the oral dose** · `cri_01M4V1FPK4A8S2G3AQ6PBWZ64Y@v4` · dimension `oral_bioavailability` · unit `% of dose extracted presystemically` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: The attribute admits only numerically reported presystemically extracted fractions and no cited claim contains one: the quotes state that CYP3A-mediated presystemic extraction is a principal determinant of bioavailability, that first-pass metabolism reduces absorption and bioavailability, and that the mechanism of metabolism and elimination is one of several contributing factors. On its own admission rule the attribute returns unknown for every candidate, and its own falsification test says it should then be withdrawn in favour of the bioavailability and interaction attributes, which measure the consequence directly.
  - definition: The fraction of an absorbed oral dose removed by intestinal and hepatic metabolism before reaching the systemic circulation, as a percentage, taken only from sources reporting that fraction numerically. Lower is better. A qualitative statement that first-pass metabolism substantially limits bioavailability is recorded as unknown with the statement noted, not converted into a percentage, and an absolute bioavailability figure is a different quantity and is not admitted here.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (1):
    - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: The attribute admits only numerically reported extracted fractions, and no cited claim contains one: claim_01M4TYZ674CP0KT2G6277WWTZW states that 'CYP3A-mediated presystemic extraction is a principal determinant of bioavailability', claim_01M4TY1R8T0JFAMCJHM9FNHE45 that 'significant first-pass metabolism reduce absorption and bioavailability', and claim_01M4TX98YYX1FVXEK7AB58N46T is a list of contributing factors. On its own evidence the attribute returns unknown throughout.
  - validator problems: —
  - cited claims: `["claim_01M4TYZ674CP0KT2G6277WWTZW", "claim_01M4TY1R8T0JFAMCJHM9FNHE45", "claim_01M4TX98YYX1FVXEK7AB58N46T"]`
- **Plasma protein binding** · `cri_01M4V1FPMDQ4HGTH3TDPYT7HTC@v2` · dimension `oral_bioavailability` · unit `% bound` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4V43E8GDH8GF8M633VTWDQJ` by `remove`
  - reason `withdrawn_by_reviser`: Two blocking findings, both correct, and together they remove the attribute's foundation. The direction was the problem: the cited quote says only that the unbound fraction is pharmacologically active and available for distribution, metabolism and elimination, which cuts both ways, since lower binding raises free active drug and also raises clearance. It states no preference for lower binding, so lower_better was my inference and not the evidence's. The second finding is worse: one cited quote reads that more than 9.5 percent of the drug is protein-bound, a figure the claim itself flags as stated rather than verified, and under lower_better that self-flagged number would have put its compound first on the attribute. The material finding compounds both, since the remaining values mix binding to albumin specifically with binding to plasma proteins overall, which are different quantities. I could drop the mis-stated quote and restrict the unit, but no surviving quote supplies a direction, and an ordering attribute without a defensible direction is not a criterion. Withdrawn. The useful part of the concern, that only free drug reaches the receptors, survives as the free-concentration margin attribute in the target-coverage pool, where it is measured directly instead of being inferred from a binding percentage.
  - definition: The reported fraction of drug bound to plasma proteins, as a percentage. Lower binding is preferred because the claims state that only the unbound fraction is pharmacologically active and available for distribution, metabolism and elimination.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (3):
    - `evidence_support` on proposal[23].attribute.direction · severity `blocking` · verdict `fail`: lower_better is not supported by claim_01M4TYZ67EZVH1PQV6BX6E0SC1, which says only the unbound fraction is active and available for distribution, metabolism AND elimination. That cuts both ways and states no preference for lower binding.
    - `evidence_support` on claim_01M4TXXANM7JG9P0VYCQVF2VWM · severity `blocking` · verdict `fail`: Quote reads 'More than 9.5 percent of the drug is protein-bound', carried as value 9.5 with a unit the claim itself qualifies '(as stated)'. Under lower_better that self-flagged figure would place its compound first on this attribute.
    - `unit_applicability_consistency` on proposal[23].attribute.unit · severity `material` · verdict `fail`: claim_01M4TY1RCT9CYSV0BB325G7FWC reports 97.8% bound to serum ALBUMIN while claim_01M4TY1RHA15CHFDC6PG25A6ZR reports >97% to plasma proteins overall. Albumin binding is a subset; pooling them under '% bound' mixes two quantities.
  - validator problems: —
  - cited claims: `["claim_01M4TYZ67EZVH1PQV6BX6E0SC1", "claim_01M4TY1RCT9CYSV0BB325G7FWC", "claim_01M4TY1RHA15CHFDC6PG25A6ZR", "claim_01M4TXXAPNGJ14WB68G5ZARXR8", "claim_01M4TXXANM7JG9P0VYCQVF2VWM"]`
- **Number of formulations with divergent administration instructions** · `cri_01M4V1FPN1D1Z2B8DQ2F4CQF7V@v4` · dimension `oral_bioavailability` · unit `count of divergent formulations` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: After removing the two mis-cited quotes, one describing two strengths of a single dosage form under one instruction and one about food-effect study design rather than formulation instructions, nothing cited yields a count of divergent formulations for any candidate. The count is also confounded by commercial history rather than pharmacology: it can only rise with how long and how widely a molecule has been marketed and reformulated, so a mature approved agent is penalised against an investigational agent whose single formulation scores best without having been tested for consistency. The substance of the concern is retained as recorded qualifiers in the food-effect and acid-suppression attributes, both of which now record the formulation studied and forbid transferring a value between products.
  - definition: The number of marketed or studied formulations of the compound whose administration instruction, food requirement or interchangeability differs from the others: zero where one consistent instruction applies to all products, one where a reformulation carries a different instruction, and more where several diverge. Products explicitly stated not to be interchangeable are counted as divergent. Fewer is better, because the cited evidence shows that where the instruction is formulation-dependent the counselling point must be checked against the product actually dispensed, and that an interaction magnitude measured for one formulation does not transfer to another.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (2):
    - `evidence_support` on claim_01M4TY1RA9QF89DW4DP9AH06JW · severity `material` · verdict `fail`: The quote describes two strengths of one dosage form under one instruction, 'available in 100 mg and 150 mg soft capsules ... taken whole with food and fluids'. Two strengths are not two divergent formulations, so this claim cannot raise the count; claim_01M4TYZ6CQD712197RSTQ470ZM is about food-effect study design rather than formulation instructions.
    - `candidate_symmetric_scrutiny` on attribute.direction · severity `material` · verdict `fail`: The count can only rise with how long and how widely a molecule has been marketed and reformulated, so a mature approved agent is penalised against an investigational agent with a single formulation, for reasons unrelated to its pharmacology.
  - validator problems: —
  - cited claims: `["claim_01M4TYZ6B42DA4F3FDKYFB64B4", "claim_01M4TYZ6F30J0KEF9W5FQ4K941", "claim_01M4TYZ6CQD712197RSTQ470ZM", "claim_01M4TY1RA9QF89DW4DP9AH06JW"]`
- **Terminal elimination half-life in humans** · `cri_01M4V1REDATHP5ENWSKDG6DJK2@v2` · dimension `metabolic_stability` · unit `hours` · direction `within_range`
  - left the pool at stage `refine` iteration 1 of round `run_01M4V43E8GDH8GF8M633VTWDQJ` by `remove`
  - reason `withdrawn_by_reviser`: Two blocking findings and two material ones, and after honouring them the attribute has no evidence left to stand on. The blocking structural finding is right: direction within_range with predicate_form ordering and a null cutoff gives no defined sort at all, since a window cannot be evaluated by an ordering and neither bound appeared in the rule. The blocking evidence finding is also right: the two-week half-life quote describes an intravenously administered monoclonal antibody and its structured value is a systemic clearance in millilitres per kilogram per day, so it supports neither an hours-scaled half-life nor an orally administered small molecule, and it was the only citation anchoring the long end of my window. The material findings remove two more: one quote's structured value is a percentage of renal clearance with the half-life only in prose, and another reports time to peak plasma concentration, an absorption parameter rather than a terminal half-life. That leaves two values, 9.5 and 9.7 hours, for a single agent. I could keep a half-life attribute with a direction, but neither lower nor higher is better for a chronic oral agent and I have no cited bound to place a window on, so any direction I chose would be invented. Withdrawn. The practical consequences the item was reaching for are carried by the doses-per-day attribute and the time-to-steady-state attribute, both of which are measured directly and have defensible directions.
  - definition: The reported terminal elimination half-life of the compound in humans, in hours. Scored as a window: long enough that once-daily or twice-daily oral dosing holds exposure above the active concentration, short enough that the drug can be cleared when toxicity requires interruption and does not accumulate several-fold on repeated dosing.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (4):
    - `evidence_support` on claim_01M4TZXYTZNQP0CN6AK06HM84Z · severity `blocking` · verdict `fail`: Quote describes an intravenously administered monoclonal antibody with a two-week terminal half-life, and its structured value is 4.9-6.7 mL/kg/day of systemic CLEARANCE. It supports neither an hours-scaled half-life nor an orally administered small molecule.
    - `unit_applicability_consistency` on proposal[24].rule.predicate_form · severity `blocking` · verdict `fail`: direction within_range with predicate_form ordering and cutoff null gives no defined sort: a window cannot be evaluated by an ordering, and neither bound of the window appears anywhere in the rule.
    - `evidence_support` on claim_01M4V00PDK31CVQAQYRB780F0V · severity `material` · verdict `fail`: Structured value is 75 with unit '% renal clearance'; the half-life appears only in the prose, so the claim's value is not in the attribute's unit of hours.
    - `evidence_support` on claim_01M4TY1R7NHQYK6VY8CP75A5SW · severity `material` · verdict `fail`: Quote reports time to peak plasma concentration (2-4 hours), an absorption parameter, not terminal elimination half-life.
  - validator problems: —
  - cited claims: `["claim_01M4TY1RFZ0BKWJ6CXJCYH4EX3", "claim_01M4TY1RGN8F2NC0WNHSW2PY96", "claim_01M4TZXYTZNQP0CN6AK06HM84Z", "claim_01M4V00PDK31CVQAQYRB780F0V", "claim_01M4TY1R7NHQYK6VY8CP75A5SW"]`
- **Share of total clearance carried by CYP3A** · `cri_01M4V1REE3FCKE5VT9AP705QQ9@v4` · dimension `metabolic_stability` · unit `% of total clearance` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: The definition admits values only against total systemic clearance and every cited number uses another denominator: about 5 percent of the biotransformation for one agent, a 40 to 50 percent contribution with no denominator stated for another, and approximately 10 percent of the drug undergoing hepatic metabolism for a third. The three denominators are not interconvertible without the metabolic fraction, which no quote gives, so by its own admission rule the attribute excludes all of its cited values and returns unknown throughout; keeping it by widening the denominator would put non-interconvertible quantities on one percentage axis. Its own falsification test prescribes the alternative, which survives in this pool: the measured inhibitor and inducer exposure-change attributes capture the same liability as an observed exposure change.
  - definition: The share of the compound's total systemic clearance attributable to CYP3A, as a percentage, admitted only from sources that report it against that denominator. Values reported against a different denominator, such as the share of biotransformation or the share of hepatic metabolism, are recorded with their own denominator and are not converted to this one, because the three are not interchangeable. Lower is better, with no threshold: the cited evidence reports what has been observed for particular molecules and sets no acceptability standard.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (1):
    - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: The definition admits values only against total systemic clearance, yet every cited number uses another denominator: 'about 5% of the biotransformation' (claim_01M4TY1RDR5FBAKFQKDFJZYCDJ), CYP3A4 'has only 40-50% contribution' with no denominator stated (claim_01M4TZM5MPZ1MFCB558G1BRDZ4), and 'Approximately 10% of the drug undergoes hepatic metabolism' (claim_01M4V00PD3AC7N68R3KCCXRC3W). By its own admission rule the attribute excludes all of its cited values.
  - validator problems: —
  - cited claims: `["claim_01M4TZM5MPZ1MFCB558G1BRDZ4", "claim_01M4TY1RDR5FBAKFQKDFJZYCDJ", "claim_01M4V00PD3AC7N68R3KCCXRC3W", "claim_01M4TZM5E18G6E5RACG27FDC91", "claim_01M4TYZ674CP0KT2G6277WWTZW", "claim_01M4TYZ6G0S1XVXQ5VRF898PBS"]`
- **Share of clearance carried by the largest single route** · `cri_01M4V1REEYCRXMBBGEMPWKE52B@v4` · dimension `metabolic_stability` · unit `% of clearance via the largest route` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: No cited claim apportions clearance between routes numerically. All are qualitative route statements, such as being only partially metabolised by one enzyme and also relying on alternative routes, being primarily metabolised by one enzyme, being primarily metabolised by esterase hydrolysis, or being predominantly metabolised by two named enzymes, and the definition rightly forbids inferring a share by counting the routes a source happens to mention. The percentage axis therefore has no cited value and the attribute returns unknown for every candidate; the redundancy it aimed to reward is observable in the measured inhibitor and inducer exposure-change attributes, which are retained.
  - definition: The percentage of the compound's clearance carried by its single largest elimination route, whether that route is oxidative metabolism by one enzyme, conjugation, esterase hydrolysis, unchanged biliary excretion or unchanged renal excretion. A value near 100 means clearance funnels through one perturbable route; a lower value means parallel routes share it. Lower is better. Where no source apportions clearance between routes the value is unknown with the named routes recorded, and is never inferred by counting the routes a source happens to mention, because a compound with three named routes and 90 percent of clearance through one of them behaves as a single-route compound.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (1):
    - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: No cited claim apportions clearance numerically; all are qualitative route statements such as 'only partially metabolized by CYP3A4 and also rely on alternative routes' (claim_01M4TZM5DFVY7SWCTV5KHMZ9HM), 'primarily metabolized by CYP3A4' (claim_01M4TZM5E18G6E5RACG27FDC91), 'primarily metabolized through hydrolytic cleavage by esterases' (claim_01M4TY1RDAYJJ2RAF98TE0DVHW) and 'predominantly metabolized by CYP3A and UGT1A4' (claim_01M4TZRMS3GD07QZC9NKEH97E8). The percentage axis has no cited value.
  - validator problems: —
  - cited claims: `["claim_01M4TZM5DFVY7SWCTV5KHMZ9HM", "claim_01M4TZM5E18G6E5RACG27FDC91", "claim_01M4TY1RDAYJJ2RAF98TE0DVHW", "claim_01M4TZRMS3GD07QZC9NKEH97E8", "claim_01M4TZRMAF7HJ1ZK8TF2CB8X64", "claim_01M4TZM5N79K45R9T9TKBSBC2R"]`
- **Pharmacologically active circulating metabolites** · `cri_01M4V1REM82YS0ATT46XA2PJPA@v2` · dimension `metabolic_stability` · unit — · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: A literature-bound attribute must be quantitative with a unit, and the cited evidence contains no quantified metabolite property to carry one. No cited quote gives an active metabolite's share of total drug-related exposure or its potency relative to the parent: the quotes name one agent's main pharmacologically inactive metabolite, state that another agent's active-metabolite exposure is highest with a low-fat meal, report a 264 percent rise in one metabolite's exposure under an inducer alongside a 50 percent fall in parent exposure, and state that one agent's metabolic pathway is unknown. Those are three different quantities and one absence, and none of them can be put on a single axis without inventing a number. The part of the concern the evidence does support, that the analyte measured differs between studies so published exposure values may not be comparable, is now recorded as a qualifier in the food-effect attribute, which cites that quote.
  - definition: Whether the compound forms circulating metabolites that retain pharmacological activity at the required receptors, the fraction of total systemic exposure they represent, and their potency relative to the parent. Fewer and less potent active metabolites make exposure easier to interpret and control.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings: —
  - validator problems (1):
    - schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - cited claims: `["claim_01M4TYZ6GYVQ0X24MFKYHWRR78", "claim_01M4TZRMS3GD07QZC9NKEH97E8", "claim_01M4TYZ6AGPVG11B7AE0DB26TH", "claim_01M4TYZ6AR0YCKDQVMN1RD4669", "claim_01M4TZXYTGV4T2SGJE9CNG59Y1"]`
- **Sensitivity of clearance to metabolising-enzyme and transporter genotype** · `cri_01M4V1RER0P5FMENTWEYXF0WDK@v3` · dimension `metabolic_stability` · unit `fold difference in exposure between genotypes` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: Only one cited claim supplies a value on the declared fold axis, a 1.5-fold exposure difference for one combined genotype; six others state a direction with no magnitude and one reports a count of genes, so the axis is almost entirely unevidenced. The quantity is also a property of a patient population's genotype distribution rather than of the molecule, as one cited quote makes explicit in noting that prevalence varies across populations and ethnic groups, and no population is specified. Finally, with the largest reported genotype effect scored and an ungenotyped candidate unranked, each additional pharmacogenetic study can only worsen a candidate's score; the attribute's own falsification test names that defect, and nothing in the cited evidence supports the normalisation that would cure it.
  - definition: The reported magnitude of exposure difference between metaboliser or transporter genotypes, as a fold change. Smaller genotype sensitivity is better because it narrows the spread of exposure across a population.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (4):
    - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: Only claim_01M4TZM5JRSMPDKFY6CKF15T8K supplies a fold value, '1.5-fold higher lenvatinib values'. claim_01M4TZM5HZX9DQHJ4A6F3ZEEWV ('an increase in AUC with higher toxicity risks'), claim_01M4TZM5KBFY23AV5F81NFW7TE ('higher plasmatic concentrations'), claim_01M4TZ40JY9SQDWHT50SME4VMW, claim_01M4TZM5HEDCNKYWT7903SRYPR and claim_01M4TZ40G32EP93WAMW10DQY5K state a direction with no magnitude, so six of seven cited claims yield nothing on a fold axis.
    - `evidence_support` on claim_01M4TZ40EJTGBY11WKW2B6DGJG · severity `material` · verdict `fail`: This claim's only number is a count of genes, 'the identification of 57 functional genes, classified into 18 families'. It is a different quantity from a fold difference in exposure between genotypes and cannot support the attribute.
    - `candidate_symmetric_scrutiny` on falsification_test · severity `material` · verdict `fail`: The test states 'a candidate must not be penalised for having been studied more thoroughly than its competitors', but with aggregation max over reported genotype effects and rule.on_missing unknown_no_penalty that is exactly what happens: each additional pharmacogenetic study can only raise a candidate's score, while an ungenotyped candidate is unranked. The defect is named and not remedied.
    - `objective_conformance` on attribute.definition · severity `material` · verdict `fail`: The quantity is a property of patient genotype distribution rather than of the molecule, as claim_01M4TZ40G32EP93WAMW10DQY5K makes explicit ('prevalence varying across different populations and ethnic groups'), yet it is scored as a candidate attribute with no population specified.
  - validator problems: —
  - cited claims: `["claim_01M4TZM5JRSMPDKFY6CKF15T8K", "claim_01M4TZM5HZX9DQHJ4A6F3ZEEWV", "claim_01M4TZM5KBFY23AV5F81NFW7TE", "claim_01M4TZ40JY9SQDWHT50SME4VMW", "claim_01M4TZM5HEDCNKYWT7903SRYPR", "claim_01M4TZ40G32EP93WAMW10DQY5K", "claim_01M4TZ40EJTGBY11WKW2B6DGJG"]`
- **Breadth of the co-medication interaction list** · `cri_01M4V1RERRZTFDSFQGMB2CHPMD@v3` · dimension `metabolic_stability` · unit `count of restricted co-medications` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: The attribute scores two things on one axis, the number of restricted co-medications and their clinical commonness, and the unit admits only the count, so the stated direction cannot order a short list of common drugs against a long list of rare ones. The counts themselves are not available from the evidence: the quote naming ten drugs is explicitly open-ended, so a count taken from it measures the source's verbosity, and the other cited numbers are a patient-level prevalence of potential interactions and a list of foods and herbs rather than co-medications. The count can also only grow with the depth of a candidate's interaction literature, which its own falsification test identifies, while the cited evidence itself grades agents qualitatively as significant, moderate or mild. The same liability is measured directly by the inhibitor, inducer, transporter and perpetrator exposure-change attributes retained in this pool.
  - definition: The number and clinical commonness of co-medications for which the label or literature requires avoidance, dose adjustment or added monitoring. A shorter list of less common drugs is better.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (4):
    - `unit_applicability_consistency` on attribute.definition · severity `material` · verdict `fail`: The definition scores two things, 'The number and clinical commonness of co-medications', and resolves them with 'A shorter list of less common drugs is better'. The unit admits only 'count of restricted co-medications', so commonness has no scale, and the stated direction cannot order a short list of common drugs against a long list of rare ones.
    - `evidence_support` on claim_01M4TY1RJCFBWFFEVA8HT9KXQZ · severity `material` · verdict `fail`: The quote names ten drugs but is explicitly open-ended: 'Some commonly used drugs that may potentially affect nintedanib metabolism include but are not limited to'. A count taken from it is a lower bound set by the source's verbosity, not the number the attribute defines.
    - `evidence_support` on claim_01M4TZM5WY5EE7PR8T993S2DGS · severity `material` · verdict `fail`: This is a patient-level prevalence, 'About 47.4% of patients on TKIs encountered at least one potential TKI-drug interaction, with 30.8% of these classified as major'. It is a percentage of patients, not a count of restricted co-medications, and is not on the declared axis; claim_01M4TZM5TA82RSY7KKETAR4ZNP lists foods and herbs rather than co-medications.
    - `candidate_symmetric_scrutiny` on attribute.direction · severity `material` · verdict `fail`: The count can only grow with the depth of a candidate's interaction literature. The falsification test identifies this ('a well-characterised agent would be punished for its own evidence base') but the definition contains no normalisation, and claim_01M4TZM5QXVFPSAGJBW80RP0F1 shows the evidence itself grades agents qualitatively (significant, moderate, mild) rather than by count.
  - validator problems: —
  - cited claims: `["claim_01M4TZM5WY5EE7PR8T993S2DGS", "claim_01M4TY1RJCFBWFFEVA8HT9KXQZ", "claim_01M4TZRMHDWXXK91FKV9MPCR39", "claim_01M4TZM5QXVFPSAGJBW80RP0F1", "claim_01M4TZM5TA82RSY7KKETAR4ZNP", "claim_01M4TZRMY4F732E1HFVGQ02QBK"]`
- **Number of clinical pharmacology characterisations reported** · `cri_01M4V1RESATG6X4V8AP6CR5XJZ@v4` · dimension `metabolic_stability` · unit `count of characterisations reported` · direction `higher_better`
  - left the pool at stage `refine` iteration 2 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: The quantity measures how fully a candidate's clinical pharmacology dossier has been assembled rather than a property of the molecule, and with a higher-is-better ordering it rises monotonically with development stage, so an approved agent outranks an investigational one of identical pharmacology. That is the mirror image of the bias this pool corrects elsewhere, where a largest-change rule was rejected because it would penalise a compound for the depth of its interaction programme, and nothing in the cited evidence supports a normalisation that would cure it: the quotes establish that an absent interaction finding is untested rather than safe, not that more studies make a molecule better. The caveat that the count can never outrank the measured attributes is a weighting instruction rather than part of the scored quantity, so it cannot do that work either. The substance the quotes do support is retained in the admission rules of the measured interaction attributes, which return unknown for an unstudied substrate and record its substrate status rather than scoring silence as safety.
  - definition: The number of the following three characterisations that the source reports as actually performed for this compound, an integer from 0 to 3: a dedicated clinical interaction study using a strong index perpetrator; an established primary clearance or metabolic pathway, as opposed to one reported as not elucidated or unknown; and an interaction study conducted in patients rather than only in healthy volunteers. Each counts only where the source states it for this compound. An entry recording no interaction in labelling, or an interaction not formally evaluated, counts as nothing: it is the absence of a labelled finding rather than a demonstrated absence of effect, and for a compound known to be a substrate, inhibitor or inducer the mechanistic potential remains. Higher is better. The count measures what is known about a compound's exposure behaviour and never stands in for a measured liability: a candidate with a fully characterised and unfavourable interaction profile is not preferred over one with fewer studies and no liability, which is why this attribute is read alongside the measured interaction and toxicity attributes and can never outrank them.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (2):
    - `objective_conformance` on attribute.direction · severity `material` · verdict `fail`: The quantity measures how fully a candidate's clinical pharmacology dossier has been assembled, not a property of the molecule. With direction higher_better it rises monotonically with development stage, so an approved agent outranks an investigational one of identical pharmacology; the objective asks for a profile suitable for development, under which an unstudied candidate is not thereby worse.
    - `candidate_symmetric_scrutiny` on attribute.definition · severity `material` · verdict `fail`: This is the mirror image of the bias the same pool corrects in proposal 15, which rejects a largest-change rule because it 'would penalise a compound for the depth of its interaction programme'. Here depth of programme is directly rewarded. The caveat that the count 'can never outrank' the measured attributes is a weighting instruction, not part of the scored quantity, so candidates are not treated alike.
  - validator problems: —
  - cited claims: `["claim_01M4TYZ6MVMRJHNEA0V8AJR2SE", "claim_01M4TZRMW718J1MZA8KYSWEEVZ", "claim_01M4TYZ6KKPT6DPJTEA5CB9D5Y", "claim_01M4TYZ6FQW0KQDXEF50J0RRW6", "claim_01M4TZXYTGV4T2SGJE9CNG59Y1", "claim_01M4TZRMHY06A6Q4NV5J8F7TX9", "claim_01M4TYZ6N61H4K84ZQ795M2T9E"]`
- **Need for therapeutic drug monitoring to control exposure** · `cri_01M4V1RET1S008XWXGRESPB9GA@v2` · dimension `metabolic_stability` · unit — · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: A literature-bound attribute must be quantitative with a unit, and the cited evidence supports no number for this property. The quotes say that therapeutic drug monitoring is important for reducing exposure variability in this class, that plasma measurement is recommended when toxicity, non-compliance, interaction or suboptimal response is suspected, and that the exposure-response evidence does not yet support routine use. Those are class-level statements of when monitoring is advisable, not a per-candidate quantity, and converting them into a score would require a number the evidence does not contain.
  - definition: Whether maintaining safe and effective exposure is reported to require plasma concentration measurement or other individualised monitoring, as opposed to fixed dosing. Not needing monitoring is better.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings: —
  - validator problems (1):
    - schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - cited claims: `["claim_01M4TZRMXC6AD4ERZ45YVD86SR", "claim_01M4TZM6CECH44X9YVSZ7H6RX3", "claim_01M4TYZ68S7R7KXB17CSK2M2FG", "claim_01M4TZRMX2G3TTNVVNKX6J52FN", "claim_01M4TYZ68FGES8E8NJH15YAFBA"]`
- **Stability of clearance against disease-state and inflammatory changes** · `cri_01M4V1RETJXJCS0JZW1NX5NTKH@v2` · dimension `metabolic_stability` · unit — · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: A literature-bound attribute must be quantitative with a unit, and no cited quote quantifies this for any compound. The evidence gives a mechanism, that chronic inflammation raises cytokine levels which suppress drug-metabolising enzymes so that treating the inflammation may normalise enzyme activity, and an observation that oncology patients frequently have altered hepatic function, both stated for the class rather than for a candidate; no quote reports a patient-versus-volunteer clearance comparison for any compound. The attribute's own falsification test prescribes the alternative, folding the concern into the hepatic-impairment attribute, which scores the measurable consequence.
  - definition: Whether the compound's clearance is reported to change with disease state, inflammation or treatment of the underlying disease, for example through cytokine-mediated suppression of drug-metabolising enzymes. Less such dependence is better.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings: —
  - validator problems (1):
    - schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - cited claims: `["claim_01M4TZXZ41N6MQ417M3W63T5RY", "claim_01M4TZM5C3RMHZ9QZEGATZ1XXG", "claim_01M4TYZ67EZVH1PQV6BX6E0SC1", "claim_01M4TZRMX2G3TTNVVNKX6J52FN"]`
- **Boxed warning on the molecule record** · `cri_01M4V221Z350TD708JJHBX7DDD@v4` · dimension `toxicological_safety` · unit — · direction `lower_better`
  - left the pool at stage `refine` iteration 2 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: No cited claim mentions a boxed warning or the molecule-record flag this attribute reads; the six quotes are narrative toxicity statements about the class, so the flag's relevance here is asserted rather than evidenced. The flag is also structurally asymmetric for this pool: the field is usually empty before approval, an empty field gives unknown with no penalty, and the flag can therefore only ever penalise approved candidates, which is precisely the failure the attribute's own falsification test describes, separating approved from unapproved candidates rather than safe from unsafe ones. The measured adverse-event and discontinuation rates quantify what a flag only signals.
  - definition: Whether the compound's molecule record carries a boxed warning. Read as a categorical flag and ranked rather than thresholded: a record carrying the flag ranks below a record that does not carry it, and an empty field gives unknown, never a pass, because the field is usually empty before approval. No cited source states the value the flag should take, so the rule carries no cutoff: the ordering is on the flag as recorded, and the attribute is read alongside the measured adverse-event rates, which quantify what a flag only signals.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "unknown_no_penalty", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (2):
    - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: None of the six cited claims mentions a boxed warning or a molecule-record flag; they are narrative toxicity statements such as 'Hypertension Hypotension Congestive heart failure ... QT interval prolongation' (claim_01M4TX994ZSKG804S280SWT2Q1) and claim_01M4TY1RRQ6YXEHXMNMV39Y83F. The attribute's relevance to the flag it reads is asserted rather than evidenced.
    - `candidate_symmetric_scrutiny` on rule.on_missing · severity `material` · verdict `fail`: The definition states that the field 'is usually empty before approval' and an empty field gives unknown, while rule.on_missing is unknown_no_penalty. The flag can therefore only ever penalise approved candidates and never an investigational one, which is the failure its own falsification test describes, that the field 'separates approved from unapproved candidates rather than safe from unsafe ones'. The attribute is retained anyway.
  - validator problems: —
  - cited claims: `["claim_01M4TX9937CKPPPM3WZGXCM35C", "claim_01M4TX9941P0HK8NQZWV2G9D49", "claim_01M4TX994G410JPBMYGA6A9ZPK", "claim_01M4TX994ZSKG804S280SWT2Q1", "claim_01M4TY1RRQ6YXEHXMNMV39Y83F", "claim_01M4TY1RSARR5MJT5F4AV9JZJC"]`
- **Withdrawal flag on the molecule record** · `cri_01M4V221ZQCGF2TK7WYC0B53RE@v3` · dimension `toxicological_safety` · unit — · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: No cited claim mentions a withdrawal or a withdrawn molecule record. The quotes concern one therapy's side-effect profile limiting its clinical utility, treatment cessation with an unrelated inhibitor class, a 10.2 percent discontinuation rate, and post-marketing adverse events; none of them evidences the flag this attribute reads, and a rule that eliminates candidates outright cannot rest on that. The cutoff basis was also mislabelled as a source-stated value when requiring the flag to be false was the proposal's own choice, and the proposal's own falsification test concedes that a withdrawal unrelated to safety, such as failure to complete a confirmatory trial, would make exclusion wrong while the flag carries neither jurisdiction nor reason. The toxicity signal it aimed at is scored directly by the discontinuation-rate and severe-adverse-event-rate attributes.
  - definition: Whether the compound's molecule record is flagged as withdrawn. A categorical flag; an empty field gives unknown.
  - rule: `{"cutoff": {"comparator": "==", "unit": null, "value": false}, "cutoff_basis": "source_stated_value", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "threshold", "rule_kind": "hard_exclusion"}`
  - critic findings (3):
    - `evidence_support` on supporting_claim_ids · severity `blocking` · verdict `fail`: This is the pool's only hard_exclusion, yet no cited claim mentions a withdrawal or a withdrawn molecule record. claim_01M4TZVEE39384V4EVJXMB9113 is about IFN-alpha toxicity limiting clinical utility, claim_01M4TZVE8HEW5KNWCN6KCB2TC9 about Shh-inhibitor treatment cessation, claim_01M4TXQQP6MGMJQ6CG95GTZ8DX about pemigatinib discontinuation in 10.2%, and claim_01M4TY1RRQ6YXEHXMNMV39Y83F about post-marketing events. A rule that eliminates candidates outright rests on no cited evidence for the flag it reads.
    - `evidence_support` on rule.cutoff_basis · severity `material` · verdict `fail`: cutoff_basis is 'source_stated_value', but no source in this request states the value false for a withdrawn flag; requiring the flag be false is the proposal's own choice of admissible record state, so the basis is mislabelled.
    - `counter_evidence_considered` on rule.rule_kind · severity `material` · verdict `fail`: The falsification test concedes that a withdrawal 'for a reason unrelated to safety, for example failure to complete a confirmatory trial' would make exclusion wrong, yet rule_kind remains hard_exclusion on an undifferentiated flag whose jurisdiction and reason are not read. The known counter-case is acknowledged and left in force.
  - validator problems: —
  - cited claims: `["claim_01M4TZVEE39384V4EVJXMB9113", "claim_01M4TZVE8HEW5KNWCN6KCB2TC9", "claim_01M4TXQQP6MGMJQ6CG95GTZ8DX", "claim_01M4TY1RRQ6YXEHXMNMV39Y83F"]`
- **Hepatotoxicity and the hepatic monitoring burden it imposes** · `cri_01M4V2224XFMT6T7Z9ADXWA07K@v3` · dimension `toxicological_safety` · unit `% of patients with transaminase elevation` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: The declared axis, the percentage of patients with transaminase elevation, has no cited value: the quotes describe elevations as commonly seen in patients of low body mass, list symptoms, and say severe events are less frequent but warrant close observation. The other numbers in the evidence are a monitoring interval in months and management thresholds in multiples of the upper limit of normal or in units per litre, which cannot enter a percentage axis, and no cited quote supports the direction the definition asserted for them, since a looser discontinuation threshold reflects labelling judgement rather than less hepatotoxicity. The hepatic liability remains visible in the pool through the hepatic-impairment dose-restriction attribute and through the severe-adverse-event and discontinuation rates.
  - definition: Reported rates of transaminase or bilirubin elevation and of clinically significant liver injury, together with the monitoring schedule and the thresholds at which dose hold or discontinuation is required. Lower rates and looser thresholds are better.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (3):
    - `evidence_support` on supporting_claim_ids · severity `material` · verdict `fail`: The declared unit is '% of patients with transaminase elevation' and no cited claim supplies one. claim_01M4TY1RR6ZCP8S2HAWSR93G25 says elevations were 'commonly seen in patients with low BMI', claim_01M4TX995FN30RYXXDADYY5BNX is a symptom list, and claim_01M4TZVE65NQGA4259K318BS7R says severe events are 'less frequent but warrant close observation'. The percentage axis has no cited value at all.
    - `unit_applicability_consistency` on attribute.definition · severity `material` · verdict `fail`: Three incommensurable scales are bundled under a percentage unit: rates, a monitoring interval in months ('every 6 to 12 months', claim_01M4TY1RXB6BE94FMGSBPYV3SE) and a discontinuation threshold in multiples of normal ('more than 3 to 5 times the normal upper limit', claim_01M4TY1RZYEQYN5DZTRG89QSYX). Neither of the latter two can be entered as a % of patients.
    - `evidence_support` on attribute.definition · severity `material` · verdict `fail`: 'Lower rates and looser thresholds are better' asserts a direction for threshold looseness that no cited claim supports. A looser discontinuation threshold reflects labelling judgement, not less hepatotoxicity, and the cited thresholds are stated as requirements rather than as graded safety signals.
  - validator problems: —
  - cited claims: `["claim_01M4TY1RZYEQYN5DZTRG89QSYX", "claim_01M4TY1RXB6BE94FMGSBPYV3SE", "claim_01M4TY1RR6ZCP8S2HAWSR93G25", "claim_01M4TY1RZEEQ5WVQB593DHSCMV", "claim_01M4TX995FN30RYXXDADYY5BNX", "claim_01M4TZVE65NQGA4259K318BS7R"]`
- **Reversibility of the characteristic toxicities after discontinuation** · `cri_01M4V222DFW65QRXFNJM6GM52C@v2` · dimension `toxicological_safety` · unit — · direction `higher_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: A literature-bound attribute must be quantitative with a unit, and reversibility is reported narratively in the cited evidence. The only time figures belong to different toxicities, improvement within 24 weeks of cessation for one and recovery within six weeks of stopping for another, so they cannot share an axis, and the remaining statements are unquantified: usually reversible with dose reduction or interruption, characteristically reversible on discontinuation, and reversible only in some cases with chronic use. No single quantity with a unit can be formed from that without inventing one. The distinction the attribute was protecting is retained where the evidence states it: the proteinuria attribute now records that the renal changes were only sometimes reversible on withdrawal, and the ocular attribute records the reported reversibility alongside the incidence.
  - definition: Whether the compound's characteristic toxicities resolve after treatment is stopped, and over what interval. More reversible toxicity is better at equal incidence.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings: —
  - validator problems (1):
    - schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - cited claims: `["claim_01M4TZVEAAAXK50W9A283FWF9R", "claim_01M4TXQQK4P73MY29GPGTRA1XW", "claim_01M4TY1RTDSTQBRBNBWRVEJ7YP", "claim_01M4TX9941P0HK8NQZWV2G9D49", "claim_01M4TXQQKR8FM7EN7GQVSPNQ92"]`
- **Impairment of wound healing and the perioperative interruption it requires** · `cri_01M4V222E1W5VYVM9ASEKCSCMV@v3` · dimension `toxicological_safety` · unit `weeks of required perioperative interruption` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: No cited claim reports wound-healing impairment or a perioperative interruption for an agent of this class. The quotes concern the blood-thinning effect of a different inhibitor class before dermatologic surgery, anticoagulants, comorbidity and cardiac evaluation, and thrombosis and haemorrhage from endothelial effects, and the only figure in weeks is a tobacco-cessation window, which cannot be attached to a candidate as a drug interruption. The definition also bundled a boolean with three scales, days, weeks and multiples of the half-life, under a single weeks unit with no conversion and no half-life to convert with.
  - definition: Whether the compound is reported to impair wound healing, and the pre-operative and post-operative interruption it requires, in days or weeks or in multiples of the half-life. Less impairment and shorter interruption are better.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (3):
    - `evidence_support` on supporting_claim_ids · severity `blocking` · verdict `fail`: No cited claim reports wound-healing impairment or a perioperative interruption for an agent of this class. claim_01M4V0N1KFMB388THPBDBBW1RH concerns Bruton tyrosine kinase inhibitors' 'blood thinning effect' before dermatologic surgery, claim_01M4V0N1KTW8DG8VA1ABAVXHF7 anticoagulants, claim_01M4V0N1MSQ0P8BQTN2YY0WQ45 comorbidity and cardiac evaluation, and claim_01M4TX9941P0HK8NQZWV2G9D49 thrombosis and haemorrhage from endothelial effects. The attribute as defined has no supporting evidence.
    - `evidence_support` on claim_01M4V0N1N6BC8WS33ZDM5Q9FNQ · severity `blocking` · verdict `fail`: This is the only cited claim carrying a figure in weeks, and it is about smoking: 'Ideally, patients should discontinue tobacco use 1 to 2 weeks before and after surgery.' Taking the attribute's 'weeks of required perioperative interruption' from a tobacco-cessation window would attach a number to a candidate that the evidence states about a behaviour, not a drug.
    - `unit_applicability_consistency` on attribute.unit · severity `material` · verdict `fail`: The definition admits a boolean ('Whether the compound is reported to impair wound healing') and three scales ('in days or weeks or in multiples of the half-life') under a single 'weeks' unit, with no conversion rule; a multiple of half-life cannot be converted to weeks without a half-life, which this attribute does not carry.
  - validator problems: —
  - cited claims: `["claim_01M4V0N1KFMB388THPBDBBW1RH", "claim_01M4V0N1N6BC8WS33ZDM5Q9FNQ", "claim_01M4V0N1KTW8DG8VA1ABAVXHF7", "claim_01M4V0N1MSQ0P8BQTN2YY0WQ45", "claim_01M4TX9941P0HK8NQZWV2G9D49"]`
- **Reproductive and developmental toxicity** · `cri_01M4V222EKW9JE9ZZ8GQ84QVES@v2` · dimension `toxicological_safety` · unit — · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: A literature-bound attribute must be quantitative with a unit, and the only numbers in the cited evidence are label-imposed contraception durations, which reflect labelling judgement and elimination kinetics rather than the magnitude of reproductive toxicity, so no cited quote supports the direction the definition asserted for them. The evidence otherwise reports the property qualitatively: teratogenic effects from use in pregnancy, co-prescription of effective contraception, a pregnancy category, and embryofetal loss and structural abnormalities that the quotes attribute to inhibition of the very vascular pathway the objective requires, which makes the property common to any candidate with genuine coverage. One cited quote states that for another agent the available data are inadequate to assess the risk at all, so the attribute would separate candidates by whether they have been studied, which its own falsification test names as grounds for withdrawal.
  - definition: Reported teratogenicity, embryofetal toxicity or impairment of fertility, the contraception requirement imposed, and the duration for which it must continue after the last dose. Less reproductive toxicity and shorter post-treatment requirements are better.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings: —
  - validator problems (1):
    - schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - cited claims: `["claim_01M4TX99E56CWK0ASFECQCVNPB", "claim_01M4TX99DJKSHM166Z50XNE52S", "claim_01M4TY1RM1EYSR05AF80C0E49K", "claim_01M4TZVECHJ5QZ22KXFH6GDTRD", "claim_01M4V0QW44XE5QH862XP1K56WX"]`
- **Breadth of organ systems affected by toxicity** · `cri_01M4V222F32HWMFMQH2XPVTQD2@v3` · dimension `toxicological_safety` · unit `count of organ systems` · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: The definition requires the count to be taken from reported adverse-event tables and no cited claim provides one for a candidate: the eight organs named are stated for protein kinase inhibitors as a class, the other cited material is narrative lists, and the comparative quote asserting fewer off-target effects carries no count and cannot calibrate the axis. What is counted is also undefined, since clinically significant toxicity carries no grade or incidence threshold in the evidence, so the count would be set by how exhaustively a source enumerates and would grow with surveillance history, which the proposal's own falsification test identifies without the definition controlling it. The counterweight to breadth of coverage is carried instead by the severe-adverse-event rate, the discontinuation and dose-reduction rates, and the organ-specific rates retained in this pool.
  - definition: The number of distinct organ systems in which the compound produces clinically significant toxicity, counted from reported adverse-event tables. Fewer affected systems is better at equal severity.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (3):
    - `evidence_support` on claim_01M4TX99086ZNX1P5HJ5SPN2PW · severity `material` · verdict `fail`: The eight organs named, 'the heart, lungs, liver, gastrointestinal tract, kidneys, thyroid, blood, and skin', are stated for protein kinase inhibitors as a class, not for any candidate, so the quote cannot yield a per-candidate count; the definition requires counting 'from reported adverse-event tables' while the cited evidence is narrative lists (claim_01M4V0DJ8R57KP0NY5MJ2JAF12, claim_01M4V0DJ31ACEMB5YEN76PT3NN).
    - `unit_applicability_consistency` on attribute.definition · severity `material` · verdict `fail`: 'Clinically significant toxicity' is left undefined, with no grade or incidence threshold, so the count is set by how exhaustively a source enumerates rather than by the toxicity; and 'Fewer affected systems is better at equal severity' states a condition the attribute carries no severity term to verify.
    - `candidate_symmetric_scrutiny` on attribute.direction · severity `material` · verdict `fail`: The restriction that would control the surveillance bias appears only in the falsification test ('must be restricted to controlled trial tables'), not in the definition, so as written a long-marketed agent accumulates organ systems against an agent with one trial report. claim_01M4V0JWCF98R9HQG2519JZH58 is itself an asserted comparative claim of fewer off-target effects with no count, so it cannot calibrate the axis.
  - validator problems: —
  - cited claims: `["claim_01M4TX99086ZNX1P5HJ5SPN2PW", "claim_01M4TX99745ECCBHTQVPHYATZ3", "claim_01M4V0DJ8R57KP0NY5MJ2JAF12", "claim_01M4V0DJ31ACEMB5YEN76PT3NN", "claim_01M4V0JWCF98R9HQG2519JZH58", "claim_01M4TXQQ4WXX1EHJ8YTHG2NCE8"]`
- **Duration of the intensive monitoring window after initiation** · `cri_01M4V222FK6XD2XV1SVCHQ1PDG@v4` · dimension `toxicological_safety` · unit `weeks` · direction `lower_better`
  - left the pool at stage `refine` iteration 2 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: Applied consistently, the programme's own named-subject rule leaves this axis with no admissible value. The only cited quote carrying a window is a table row beginning with an intensive first 8 to 12 weeks of blood pressure, urine protein and weight or electrolyte monitoring, with no molecule named in the quoted text, so the window cannot be attributed to a candidate, and the oral bioavailability attribute in this programme discards a value on exactly that ground. The other cited quote contains no duration at all: it recommends early blood pressure optimisation, anticipatory management of hand-foot skin reaction, routine urinalysis monitoring and individualised assessment of bleeding risk, with minimising interruptions and preserving sustained exposure as its endpoint, which is the benefit of monitoring rather than the length of a window. A recommended surveillance schedule is in any case a practice recommendation about how an agent is used rather than a property of the molecule, and the definition itself conceded that the value is never evidence that a compound is safer. The monitoring burden the evidence does state stays in the record as a qualifier on the toxicity attributes that state it, including the ophthalmological examination recorded with the ocular attribute and the management thresholds recorded with the phosphate attribute.
  - definition: The length, in weeks, of the period after starting treatment during which the source states that intensified safety monitoring is required, for example frequent blood pressure, urine protein and weight or electrolyte checks. Where the source states a range, the upper bound is entered and the full range is recorded, so a stated window of 8 to 12 weeks enters as 12 weeks recorded as a range and no midpoint is invented. Only a stated duration of intensified monitoring after initiation is entered. The composition of the monitoring panel, a periodic interval between tests once the intensive window has passed (a different quantity, on a different scale, whose better direction is the reverse of this one), a specialist examination mandated before starting, and supportive-care measures such as antihypertensive or antidiarrhoeal regimens, hormone replacement or structured patient education are all recorded with the value for a human to weigh and are never entered on this axis, because none of them is a duration in weeks. Shorter is better. A shorter window is a smaller burden only where the monitored toxicities are themselves comparable, so the value is read alongside the measured toxicity rates and is never treated as evidence that a compound is safer.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings (3):
    - `evidence_support` on claim_01M4V09QMFTSERM18AHAWDQQ6G · severity `material` · verdict `fail`: This quote contains no duration. It recommends 'Early blood pressure optimization, anticipatory management of hand-foot skin reaction or palmar-plantar erythrodysesthesia (HFSR/PPE), routine urinalysis monitoring, and individualized assessment of bleeding risk', and its stated endpoint is minimising interruptions and preserving 'sustained exposure to active agents', which is the benefit of monitoring rather than the length of a window. It supplies no value on a weeks axis.
    - `candidate_symmetric_scrutiny` on claim_01M4V0DJ3FH2K33R1W4HR8D70P · severity `material` · verdict `fail`: The quote naming the only window has no subject: it is a table row beginning 'Intensive first 8-12 weeks' with no molecule named in the quoted text. Binding that window to a candidate requires information outside the quote, and unlike the oral-bioavailability attribute in this programme, which discards a value whose quote's subject is a pronoun, this definition states no named-subject admission rule.
    - `objective_conformance` on attribute.definition · severity `material` · verdict `fail`: The objective asks for a single oral agent engaging five named receptors with a pharmacological profile suitable for clinical development. A recommended surveillance schedule is a practice recommendation about how an agent is used rather than a property of the molecule, and the only cited quote carrying one is basis 'asserted'. The connection to the stated objective is indirect and the definition itself concedes the value 'is never treated as evidence that a compound is safer'.
  - validator problems: —
  - cited claims: `["claim_01M4V0DJ3FH2K33R1W4HR8D70P", "claim_01M4V09QMFTSERM18AHAWDQQ6G"]`
- **Relationship between exposure and toxicity on continuous dosing** · `cri_01M4V222G5YAXVEK0KQGK4ABSV@v2` · dimension `toxicological_safety` · unit — · direction `lower_better`
  - left the pool at stage `refine` iteration 1 of round `run_01M4VABCW4TS9P3FJC0K7M8JC9` by `remove`
  - reason `withdrawn_by_reviser`: A literature-bound attribute must be quantitative with a unit, and the cited exposure-response evidence supplies no magnitude to put on one. The quotes state the direction of the relationship and nothing more: that the continuous regimen was associated with an increased probability of any-grade haemorrhage and of grade 3 or higher dermatologic toxicity and proteinuria compared with a three-weeks-on one-week-off regimen, that a higher steady-state peak concentration was associated with an increased probability of grade 3 or higher dermatologic toxicity, that an intermittent schedule reduced toxicity while maintaining pharmacodynamic activity, and that there was no clinically meaningful difference in overall survival over the exposure range. No slope, odds ratio, probability or exposure value accompanies any of those statements, and the only number in the cited quotes is the size of the efficacy analysis population, 368 patients, which is not a property of the compound. Scoring the attribute would therefore require inventing a magnitude for a direction the evidence states qualitatively. The measurable consequence of the same phenomenon, the rate of severe adverse events and the rate of dose reductions and interruptions needed to keep patients on treatment, is reported as a percentage and is scored by the attributes that read those rates.
  - definition: Whether reported exposure-toxicity analyses show that higher exposure or continuous rather than intermittent dosing raises the probability of severe toxicity, and whether efficacy rises with exposure over the same range. A flat exposure-toxicity relationship is better.
  - rule: `{"cutoff": null, "cutoff_basis": "none_evidence_insufficient", "on_conflict": "route_to_human", "on_inapplicable": "unknown_no_penalty", "on_missing": "unknown_no_penalty", "predicate_form": "ordering", "rule_kind": "preference"}`
  - critic findings: —
  - validator problems (1):
    - schema: literature evidence yields numbers with units; a literature-bound attribute must be quantitative with a unit
  - cited claims: `["claim_01M4V0JWQBKEYCHSNFSCA49P8G", "claim_01M4V0JWQYD4PGZZ5HZ87Q7B1C", "claim_01M4TXQQQ24B7XD35RK8JWBBF7", "claim_01M4TX992E32GHA1WJW3PRXXPX", "claim_01M4TX997KMFVKZ4DC3X2P52B9"]`

### Registry versions merged away by a collapse (5)

- **CSF1R affinity on the independent expert curation** · `attr_csf1r-affinity-on-the-independent-expert-curation@v1` with `rule_csf1r-affinity-on-the-independent-expert-curation@v1` → merged into `attr_csf1r-curated-potency@v2`, scored by `rule_csf1r-curated-potency@v2`
  - collapse `clp_01M4WXKPA3MBD055HSNCBV43AA` · approval kind `software_status` · confirmed by a person `False` · withdrawn `False`
  - routes it contributed: `["gtopdb_affinity"]`
  - held out of the latest confirmed rule set: `True`
  - reason: 2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL1844. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_csf1r-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.
- **FGFR1 affinity on the independent expert curation** · `attr_fgfr1-affinity-on-the-independent-expert-curation@v1` with `rule_fgfr1-affinity-on-the-independent-expert-curation@v1` → merged into `attr_fgfr1-curated-potency@v2`, scored by `rule_fgfr1-curated-potency@v2`
  - collapse `clp_01M4WXKPEB4X4X3ZSBETYZ9EXX` · approval kind `software_status` · confirmed by a person `False` · withdrawn `False`
  - routes it contributed: `["gtopdb_affinity"]`
  - held out of the latest confirmed rule set: `True`
  - reason: 2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL3650. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_fgfr1-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.
- **VEGFR1 affinity on the independent expert curation** · `attr_vegfr1-affinity-on-the-independent-expert-curation@v1` with `rule_vegfr1-affinity-on-the-independent-expert-curation@v1` → merged into `attr_vegfr1-curated-potency@v2`, scored by `rule_vegfr1-curated-potency@v2`
  - collapse `clp_01M4WXKPKBRKYT0M0QJ6FP1BJ4` · approval kind `software_status` · confirmed by a person `False` · withdrawn `False`
  - routes it contributed: `["gtopdb_affinity"]`
  - held out of the latest confirmed rule set: `True`
  - reason: 2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL1868. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_vegfr1-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.
- **VEGFR2 affinity on the independent expert curation** · `attr_vegfr2-affinity-on-the-independent-expert-curation@v1` with `rule_vegfr2-affinity-on-the-independent-expert-curation@v1` → merged into `attr_vegfr2-curated-potency@v2`, scored by `rule_vegfr2-curated-potency@v2`
  - collapse `clp_01M4WXKPQ837MK8GF71Y7F5YVH` · approval kind `software_status` · confirmed by a person `False` · withdrawn `False`
  - routes it contributed: `["gtopdb_affinity"]`
  - held out of the latest confirmed rule set: `True`
  - reason: 2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL279. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_vegfr2-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.
- **VEGFR3 affinity on the independent expert curation** · `attr_vegfr3-affinity-on-the-independent-expert-curation@v1` with `rule_vegfr3-affinity-on-the-independent-expert-curation@v1` → merged into `attr_vegfr3-curated-potency@v2`, scored by `rule_vegfr3-curated-potency@v2`
  - collapse `clp_01M4WXKPVCG360VDRWPCXAM2EN` · approval kind `software_status` · confirmed by a person `False` · withdrawn `False`
  - routes it contributed: `["gtopdb_affinity"]`
  - held out of the latest confirmed rule set: `True`
  - reason: 2 promoted attributes ask one question for one quantity: capabilities interaction_evidence_lookup, unit pChEMBL, direction higher_better, subject target_chembl_id=CHEMBL1955. Each was scored separately and each counted once in the coverage denominator. The registry is append-only, so the earliest-promoted attribute attr_vegfr3-curated-potency@v1 is re-versioned declaring every route the group asks (pchembl_values, gtopdb_affinity) and the others are merged away pointing at it. No judgement was added: sharing a quantity key is sharing a capability set, a canonical unit, a direction and the subject parameters. No person confirmed it.

### Superseded registry versions (14)

`["attr_csf1r-curated-potency@v1", "attr_distance-of-computed-lipophilicity-outside-the-stated-band@v1", "attr_fgfr1-curated-potency@v1", "attr_molecular-weight-in-excess-of-the-stated-upper-bound@v1", "attr_vegfr1-curated-potency@v1", "attr_vegfr2-curated-potency@v1", "attr_vegfr3-curated-potency@v1", "rule_csf1r-curated-potency@v1", "rule_distance-of-computed-lipophilicity-outside-the-stated-band@v1", "rule_fgfr1-curated-potency@v1", "rule_molecular-weight-in-excess-of-the-stated-upper-bound@v1", "rule_vegfr1-curated-potency@v1", "rule_vegfr2-curated-potency@v1", "rule_vegfr3-curated-potency@v1"]`


## Withheld from this export

- artifact kinds: `["tool_result", "trace"]`
- private model traces and whole provider responses are not published; quoted spans, locators, source identities and document hashes are

