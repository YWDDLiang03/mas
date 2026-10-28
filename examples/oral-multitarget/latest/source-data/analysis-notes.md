# Recorded analyses and their scope

[Data index](README.md) · [Field guide](data-dictionary.md) · [Verification manifest](manifest.json)

## Original evaluation

The source tables describe the final saved evaluation of one oral multi-target task. Its 18 unique evaluation criteria serve six eligibility requirements and 17 scoring criteria, with five shared target criteria. Thirteen further observations provide context. The current candidate classification is 10 Eligible, 1,305 Evidence incomplete and 1,862 Excluded. The original numerical observations, scoring rules and final ranks retain their saved values.

The complete task and criterion history remain in the original public exports listed in [source-index.json](source-index.json). The generation collection has 3,157 records from 164 sources; its selected subset contains 3,021 records. The source manifests record the 136 omissions and generation settings. The history includes the earlier unranked evaluation of this same task and the final saved evaluation. Table 3 supplies the final 98,487 assessment cells.

## Target observations

Table 7 contains 1,348 observations underlying 238 nonmissing candidate–target summaries. Recalculation reproduces every saved median. The retained endpoint counts are IC50 991, Kd 231, Ki 77, AC50 42, EC50 5 and ED50 2. Seventy-nine summaries combine more than one endpoint type.

The source records identify 1,262 observations as human (`Homo sapiens` or `human`); organism is unrecorded for 86. Assay identifiers are present for 1,260 observations and assay descriptions for 18. These counts describe retained metadata. The observation table and raw claims preserve endpoint and condition differences for inspection.

Three groups share a candidate, target, assay, endpoint, value and document. They involve Erdafitinib–VEGFR2, Semaxanib–VEGFR2 and Gefitinib–VEGFR3. Collapsing the duplicate records changes the Semaxanib median from 5.61 to 5.75 pChEMBL; the other two medians stay unchanged. All three lie outside the original eligible cohort, and each affected summary retains evidence. The detailed review is in [review_summary.json](source_records/review_summary.json).

The available identifiers do not resolve every underlying experiment across databases. Shared numerical values alone were retained as separate records; the review reports their source and assay information.

## Removing prediction contributions

Table 8 keeps the original ten eligible candidates and their existing criterion points. It removes ADMET prediction contributions from the numerator and available-weight denominator. Surufatinib remains first, with comparison score 0.7833333333 across ten nonprediction values. The table reports changes for every candidate, including Axitinib moving from third to second and Pazopanib from second to third.

## Restricting target summaries to IC50

Table 9 keeps the original eligible cohort, non-target criterion points, equal weights and 50% direct-coverage floor. It recalculates target medians from IC50/pIC50 observations and compares each target among the original cohort members with a retained value. Unavailable target summaries remain missing.

Seven compounds meet the coverage floor in this comparison. Surufatinib retains all five target summaries and remains first, with comparison score 0.7476190476. Entrectinib, Fedratinib and Midostaurin fall below the comparison's coverage floor. This is an endpoint comparison within a fixed cohort; the candidate eligibility assignment is held at the original result.

## Recalculation

`python scripts/build_case_source_data.py` verifies the published table and source-file hashes, every final assessment link, the current classifications, all ten original scores, 238 target medians, the two comparison tables and model-use totals. The [full engine replay](../../../../docs/agent-run.md) remains available for checking the saved result through the system itself. These calculations use saved observations and require no new model requests.
