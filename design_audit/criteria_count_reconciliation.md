# Criteria count reconciliation

Measured from `task_01M4TWZXZEB1SQPS7H47C8BX01` at journal sequence 516; the same snapshot as `derived_criteria_review.json`. The project has quoted several different criteria counts. They differ because they count different populations at different versions, not because any of them is wrong.

## The numbers, each with its population

| quoted number | value here | what it counts | version and scope |
|---|---|---|---|
| 72 proposals | 72 | pool lineages the `propose` stage created | the whole task, summed over every round |
| 34 promoted | 34 | pool lineages whose final state is `promoted` | end state of the pool at this sequence |
| 40 registered criteria | 40 | distinct attribute ids in the registry, each with one rule id | the registry, all origins |
| 13 scoring rules on the published board | 13 | entries in `rules@v1` | the first confirmed rule set |
| 8 scoring rules in an offline experiment | not a rule set in this store | the 13 minus the five duplicate IUPHAR rules | an offline recomputation; it was never confirmed, so no `rules@v` holds it |
| 9 scoring rules in `rules@v3` | 9 | entries in the latest confirmed set | after the collapse and one machine adjudication |
| 26 deferred literature criteria | 26 | registered rules whose capability `literature_retrieval` was held out of the run | every confirmed set so far |
| 5 collapsed away | 5 | registered rules whose attribute a collapse merged away | `rules@v3` |

## Why 34 and 40 differ

34 of the 40 registered criteria were written by a pool promotion. The other 6 were written directly by the drug adapter's objective templates, which restate task-supplied requirements (the five required receptors and the oral-route constraint) and never enter the pool. So 34 counts the derivation's output and 40 counts the registry, which also holds the task's own mandated criteria.

The registry additionally holds 47 attribute versions and 47 rule versions for those 40 criteria. A second version is a revision of one criterion, not another criterion: five receptor attributes were revised to `@v2` to declare both curations as routes of one quantity, and the molecular-weight and lipophilicity attributes were revised to `@v2` to declare the transform their definitions already described.

## Why the scoring counts differ

Every confirmed set draws on the same 40 registered rules and differs only in how many of them may enter:

| rule set | scoring | pending | deferred | collapsed away | adds up to |
|---|---|---|---|---|---|
| `rules@v1` | 13 | 10 | 26 | 0 | 39 of 40 |
| `rules@v2` | 13 | 10 | 26 | 0 | 39 of 40 |
| `rules@v3` | 9 | 9 | 26 | 5 | 40 of 40 |

`rules@v1`: 13 scoring plus 26 deferred accounts for 39 of 40. The remainder is the oral-route hard exclusion, which the trigger table gates and which had no decision at that point, so it entered neither list.

`rules@v3`: 9 scoring plus 26 deferred plus 5 collapsed away accounts for all 40. Relative to `rules@v1` it loses the five IUPHAR duplicates, whose attributes a collapse merged into the receptor attributes they duplicated, and gains the oral-route hard exclusion, which a machine adjudication resolved by restating the task's own constraint.

The offline 8 sits between the two: it is the 13 with the five duplicates deleted rather than merged, and without the oral-route rule. Deleting an independent curation is not the path the store took; merging it into the quantity it duplicates is.

## What the 9 open disputes are

9 review items are open because a proposer and a critic still disagreed after one revision. They are not counted anywhere above as a criteria count: a disputed rule can still be registered, and five of the nine concern rules whose attributes the collapse later merged away.

## Bounds

Of the 40 registered criteria, 2 carry a numeric bound whose basis is a cited claim, 1 carries a cutoff restating a task constraint, and 39 carry `cutoff_basis: none_evidence_insufficient` and no cutoff at all. The two source-stated bounds are transform parameters, not rule cutoffs, so a reviewer looking only at `rule.cutoff` sees a registry with one bound in it.

