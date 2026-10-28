# Field guide

[Data index](README.md) · [Analysis notes](analysis-notes.md)

All tables use UTF-8 CSV. An empty numeric cell denotes unavailable or inapplicable data, as specified by its assessment state. Numeric zero and `False` are observed values. Values retain their recorded precision; display rounding is applied only in explanatory text.

## Identities and sources

`Candidate` is the recorded display name. Candidate names are unique within this export. `Candidate identifier` is the stable identity used by the engine. `Rule reference`, `Assessment identifier` and `Claim reference` connect criteria, assessments and observations. A version suffix such as `@v2` belongs to a saved definition. JSON arrays inside CSV cells retain all references and parents.

`Source reference` identifies a document or database record. `Source position` identifies the retained location within it. Assay, document and PubMed identifiers are supplied where recorded. `Reported value` and `Reported unit` describe the retained source value; a database may already supply a logarithmic affinity. Original standard values and further conditions are retained in [target observation records](source_records/target_observation_records.json).

## Criteria and decision uses

Table 1 records five overlapping target criteria as `Eligibility and scoring`, the oral criterion as `Eligibility`, 12 additional criteria as `Scoring`, 13 as `Context`, and 22 as `Awaiting definition or review`. These last two stored labels correspond to **Contextual observations** and **Outside this evaluation** in the current explanation.

`Definition`, `Unit`, `Direction` and `Scoring threshold` define the quantity and comparison. `higher_better` and `lower_better` identify the preferred direction. A blank threshold accompanies continuous ordering or an unfinished definition; the rule and use columns identify which. Recorded criterion titles may include an earlier “Predicted” prefix. Evidence basis and the final rule version identify calculated descriptors in the saved evaluation.

Table 6's `Origin` distinguishes five task-specified targets from 12 evidence-guided scoring criteria. The oral requirement is supplied in the [task constraints](run-summary.json) and Table 1. `Recorded rationale`, `Source statements` and `Support scope and study choice` respectively report the saved reasoning, supporting material and the distinction between source support and the study's selected preference.

## Candidate decisions and assessments

Table 2 gives current **Eligible**, **Evidence incomplete** and **Excluded** classifications. `Requirements supported` and `Requirements assessed` count the six compulsory requirements in this case; `Requirements needing evidence` identifies gaps. Table 3 contains the underlying cell states. A cell-level `pass` or `available` describes one assessment and is separate from the candidate classification.

For the recorded case, complete support gives Eligible; partial support gives Evidence incomplete; zero support after completed required assessments gives Excluded. The general system also excludes a candidate after a confirmed required-condition failure. The current case has no such confirmed failures. [System decision definitions](../../../../docs/reference/decision-language.md) describe these rules.

`Evidence basis` retains `measured`, `derived`, `predicted` or the recorded missing state. `Supports direct coverage` in Table 3 identifies whether the assessment has accepted direct support; only applicable scoring criteria enter the scoring-coverage calculation. A direct oral-route assessment establishes eligibility and is outside that scoring denominator.

## Scores and coverage

In Table 4, `Criterion score` is the 0–1 comparison point. `Comparison method` is continuous `ordering` or a threshold check. For continuous ordering among n eligible candidates with a value, the point equals `(number worse + (number tied − 1)/2)/(n − 1)`; a single available value receives 1. A threshold check receives 1 for pass and 0 for fail.

`Weight` is 1 throughout this case. `Included in total score` identifies available contributions. The total is the sum of weighted points divided by the weight of available scoring values. `Contribution to total score` is an individual weighted point divided by that same denominator.

`Direct coverage weight` is supported scoring weight from measurements, accepted curated observations or declared deterministic calculations. `Applicable coverage weight` includes all applicable scoring entries, including those missing a value. For Surufatinib, 15 available values enter the score; ten direct values divided by 17 applicable entries give 58.8% coverage. The saved ranking floor is 50%.

## Development, model use and times

Table 5 counts working entries at recorded stages. Its 25 rows include criterion development and the first and final saved assessments of this task. Blank counts mark identity, assessment or result activities where a criterion count does not apply. A refinement round contains filter, distill, refine and merge stages.

Table 10 groups 325 requests into 18 stage/round/role rows. Token counts and costs sum to [the saved model accounting](../results/model-accounting.json). Costs are recorded estimates in USD. Phase timestamps come from the persisted workflow; phase intervals can overlap across resumed work and should not be added to obtain total elapsed time. Use the overall start and finish in `run-summary.json` for elapsed time.

Raw times use ISO 8601 UTC. The run summary also supplies UTC+8 times. Model configuration names and provider-returned names are preserved separately in `source_records/model_identifiers.json`.

## Comparison tables

Table 8 removes prediction contributions while keeping the original ten candidates and existing criterion points. `Rank change` equals original rank minus comparison rank; a positive value means a move upward.

Table 9 holds the same original cohort and non-target scores, then recalculates each target from IC50/pIC50 observations. `Targets with IC50 data` counts the available restricted summaries. `Direct coverage` and `Meets original 50% coverage threshold` describe this calculation. Empty comparison ranks identify candidates below the coverage floor. Original eligibility decisions remain fixed for this comparison.
