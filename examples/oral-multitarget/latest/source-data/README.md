# Case source data

[中文](README.zh-CN.md) · [Case tutorial](../../../../docs/tutorial.md) · [Field guide](data-dictionary.md) · [Analysis notes](analysis-notes.md) · [Manifest](manifest.json)

This collection provides the recorded oral multi-target case as tables suitable for research reporting and supplementary data. It connects the task, criterion development, candidate decisions, scores and source observations. The general system is described in the [workflow guide](../../../../docs/design.md); the quantities below belong to this case.

[Download the complete source-data ZIP](https://github.com/YWDDLiang03/mas/releases/download/v1.1.0/TRIAGE-oral-multitarget-source-data-20261028.zip). The [download record](../source-data-download.json) gives its size and SHA-256. The ZIP includes the tables, source records, original public study exports and an offline verification script. Manuscript text and draft figures are maintained separately.

## Recorded run

The objective was to compare a library of 3,177 compounds for a single orally administered agent covering CSF1R, VEGFR1, VEGFR2, VEGFR3 and FGFR1. Criterion generation began from an empty set, incorporated six task requirements, expanded to 1,917 working items and reached 147, 68 and 53 items after three refinement rounds.

The evaluation used six eligibility requirements and 17 scoring criteria, sharing five target criteria. This gives 18 unique evaluation criteria; another 13 observations support interpretation. Thirty-one items were assessed for each candidate, yielding 98,487 records. Twenty-two retained items remained outside this evaluation, with their individual reasons in the criterion table.

The saved workflow ran from **16 October 2026, 20:52 to 17 October, 00:25 (UTC+8)**, lasting 3 h 32 min 42 s. It used saved evidence, mid workload, a configured worker limit of four and a USD 5.50 budget. The 325 recorded model requests used 5,997,812 input tokens and 2,009,003 output tokens, with estimated cost USD 4.2101472. [Run summary](run-summary.json), [model use by stage and role](AI_Data_10_model_usage.csv) and [phase timestamps](workflow-phases.csv) supply the details. The data release date is 28 October 2026.

## Tables and supporting records

| File | Rows | Contents |
|---|---:|---|
| [1. Final criteria](AI_Data_1_final_criteria.csv) | 53 | Definition, unit, direction, threshold, use, parents and reasons for entries outside evaluation |
| [2. Candidate results](AI_Data_2_candidate_results.csv) | 3,177 | Current classification, required-evidence support, rank and score |
| [3. Candidate assessments](AI_Data_3_candidate_assessments.csv.gz) | 98,487 | Candidate–criterion values, evidence bases, assessment states and source references; gzip-compressed CSV |
| [4. Eligible-candidate scores](AI_Data_4_eligible_candidate_scores.csv) | 170 | All 17 scoring entries for each of ten eligible candidates, including missing values, weights and contributions |
| [5. Criterion stages](AI_Data_5_criterion_stages.csv) | 25 | Stage timestamps and working-set counts; includes the two saved evaluations of this task |
| [6. Criterion basis](AI_Data_6_criterion_basis.csv) | 17 | Task-specified versus evidence-derived scoring criteria, rationale, sources and scope of support |
| [7. Target observations](AI_Data_7_target_observations.csv) | 1,348 | Endpoint, organism, assay, source position and pChEMBL value underlying 238 nonmissing target summaries |
| [8. Scores without predictions](AI_Data_8_without_predictions.csv) | 10 | Existing comparison with ADMET prediction contributions removed |
| [9. IC50 comparison](AI_Data_9_IC50_comparison.csv) | 10 | Existing endpoint comparison within the original eligible cohort |
| [10. Model use](AI_Data_10_model_usage.csv) | 18 | Requests, tokens and estimated cost by stage, round and agent role |

The [eligible leaderboard](eligible-leaderboard.csv) gives a compact view of the ten ranked compounds. Their full criterion contributions are in Table 4. The three candidate groups are **10 Eligible, 1,305 Evidence incomplete and 1,862 Excluded**. Surufatinib ranks first, with score 0.7592592593 and direct scoring-evidence coverage 10/17. Fifteen available values contribute to its score.

Source records include the [31 assessed definitions](source_records/final_criterion_definitions.json), [3,157-record evidence collection](source_records/evidence_collection.json), [3,021-record generation subset](source_records/criterion_generation_evidence.json), [criterion rationales and sources](source_records/criterion_basis_records.json), [target claim records](source_records/target_observation_records.json), [study settings](source_records/study_settings_basis.json), [model identifiers](source_records/model_identifiers.json) and [observation review](source_records/review_summary.json).

[The source index](source-index.json) identifies the existing public task, snapshots, complete criterion history, run bindings, model accounting and reproduction records by hash. In the ZIP these are under `study_exports/`; in the repository they remain in their existing locations. The public task copy uses the metadata treatment described in the [public-content policy](../../../../docs/reference/public-content.md).

## Read and reproduce the calculations

From a clone of the current repository, run:

```sh
python scripts/build_case_source_data.py
```

This checks the files, candidate classifications and all assessment links; recomputes all ten eligible scores and 238 target medians; and verifies the two saved score comparisons and model accounting. It uses the Python standard library and the committed data.

To create the complete download locally:

```sh
python scripts/build_case_source_data.py --output var/TRIAGE-oral-multitarget-source-data-20261028.zip
```

After extracting the published ZIP, run `python tools/build_case_source_data.py` in the extracted directory. Table 3 is already decompressed there. For replay through the research engine or a fresh investigation using the saved inputs, follow the separate [agent-run guide](../../../../docs/agent-run.md).

The original candidate classifications and score comparisons have different scopes. [Analysis notes](analysis-notes.md) explain the fixed-cohort comparisons, endpoint mix, duplicate-record review and treatment of missing data.
