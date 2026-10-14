# Predicted evidence, the receptor gate, and what each change is worth

Recorded 2026-10-14. Every number here was measured on the manuscript case, not estimated. Where a
change helps the reference compound, that is stated; where a change was refused because its only
justification was that it helps, that is stated too.

## 1. Why `exact 0/11` against the historical list was structural

The 11 historical CQAs are, every one, an **in-silico ADMET classifier output compared with 0.5**
(Tox21 nuclear-receptor panels, human intestinal absorption, oral bioavailability, CYP2C9 inhibition,
skin sensitisation, a predicted maximum tolerated dose). None is a literature-measured quantity.

The derived set was 51 criteria of which 41 were literature-bound clinical endpoints — measured
quantities with sourced cutoffs. A measured clinical endpoint and a classifier probability are not the
same quantity, so no amount of derivation quality could have produced an exact match. The gap was a
**missing capability**, not a derivation failure, and it is recorded as such rather than as a score.

## 2. The capability added, and the limits that came with it

`src/mas/adapters/predict/admet.py`, capability `predicted_property_lookup`, evidence kind
`model_prediction`, every value `determination_basis: predicted`. A local ADMET model panel
(`admet-ai 2.0.1`, Chemprop-RDKit ensembles over Therapeutics Data Commons datasets) in an isolated
interpreter, reached by subprocess so the core keeps its `requests`-only install. **52 base
endpoints**, 31 of them classifier probabilities. All 3,177 candidates cached.

Three limits are recorded in the catalog entry and must survive any later edit:

- **`Half_Life_Obach` (held-out R^2 -2.39) and `VDss_Lombardo` (-1.21) may not carry a criterion.**
  A negative R^2 means the model is worse than predicting the training mean, so the number says
  nothing about a particular compound. Both remain in the panel, labelled, because removing an
  endpoint from the advertised panel would be curating the agent's choices.
- **A predicted quantity is its own attribute.** The registry refuses `predicted` alongside any other
  determination basis, because a predicted value standing in for a measurement is a surrogate inside
  a verdict.
- **The 11 physicochemical endpoints are RDKit calculations, not models**, and are nonetheless
  labelled `predicted`. That is the conservative direction (a calculation trusted less, not more) and
  it avoids a second `derived` route to descriptors PubChem already supplies.

## 3. The receptor affinity models, and the applicability domain that refused to help

Protocol and its one amendment are in the run scratch record; both were fixed **before** any
prediction was inspected.

Classification was withdrawn before fitting: ChEMBL contains only molecules somebody chose to assay,
so CSF1R yields 2,396 actives against 36 inactives (98.5% positive). A classifier on that base rate
calls almost anything a binder, and its PR-AUC of 1.000 measures the base rate, not skill. Assuming
unmeasured compounds inactive would have made the label a property of what has been studied.

Replacement: RandomForestRegressor on median pChEMBL, ECFP4-2048 + 10 descriptors, **Bemis-Murcko
scaffold split** (a random split leaks analogue series). Held-out Spearman 0.672-0.806.

**Applicability domain, Tanimoto 0.40, registered before fitting (OECD principle 3).** Only 2.7-6.3%
of the universe is in domain, because the universe is every approved drug while the training chemistry
is kinase inhibitors. Outside the domain the cell is `unknown`, never a value.

**The predictor does not rescue the reference compound.** Its CSF1R neighbourhood is Tanimoto 0.303 —
out of domain, so no value is offered. IUPHAR/BPS has no CSF1R row for it either. This is reported
because the opposite result would have been the suspicious one.

## 4. A gate on predicted toxicity is miscalibrated for this task, and that is measurable

A predicted general-toxicity gate at the models' own 0.5 boundary removes **100% of the 116
approved/Phase-III kinase inhibitors in the candidate universe**: DILI alone excludes 99.1%, hERG
88.8%, NR-AhR 52.6%, ClinTox 43.1%, AMES 34.5%. A screen that rejects every already-approved drug in
the class the task is about is not selective, it is wrong.

Note that a universe-wide rate would not have caught this (DILI excludes 51% of all 3,177), so the
reference set matters. Hence `assessor.calibration_guard`: a hard exclusion removing more than a
registered share of the candidates that clear the task's **mandated** criteria is demoted to a
preference, so it still ranks and its evidence survives, with the measured share recorded. The guard
is handed cells and rule kinds only -- no task context, no identities, no seed list -- so it is blind
to candidate identity structurally rather than by discipline.

## 5. The sparse-coverage ranking defect

`assessor.preference_scores` averages over *evaluated* rules, so a candidate assessed on few cells is
scored on its best-covered subset. A coverage floor of 0.5 does not protect against it, because 4 of
the 9 criteria are structural descriptors available for every compound.

**Correction, recorded rather than quietly fixed.** An earlier draft of this section said "the top four
were compounds with 1 of 5 required receptors measured, including mebendazole at rank 4". Those figures
came from an offline re-score over freshly fetched ChEMBL activity tables and RDKit descriptors, not
from any published snapshot in the store, and they were stated as though they were the board. On the
published board `lb_task_01M4TD4MNYWDDVH3KWAE4Y1Q7R_4` mebendazole is at **rank 39**, not 4.

The defect is nonetheless real and visible on that published board: **Pemigatinib (rank 6)** and
**Crenolanib (rank 7)** each carry **1 of 5 required receptors**, placed above **Ponatinib (4 of 5)**,
**Tivozanib (4 of 5)** and **Cediranib (5 of 5)**, with **Axitinib (5 of 5)** at rank 5. The
answered-count distribution over that board's 6 mandated criteria is
`{0: 1220, 1: 1877, 2: 33, 3: 13, 4: 9, 5: 16, 6: 9}`. Every one of the sparse-coverage candidates
named is excluded once the floor below is applied.

The fix is not to reinterpret anyone's criterion. An unknown on a *preference* is absence of
information, not failure, and the mandated receptor criteria are `ordering` preferences precisely
because no potency threshold is evidence-supported. What is wrong is ranking a candidate on the task's
objective while the task's own required criteria are unanswered. That is a **mandated-coverage floor**,
separate from the overall coverage floor.

## 6. Literature could never supply a potency, and why

`VALUE_TRANSFORMS` offers `excess_above`, `shortfall_below`, `distance_outside_band`; `UNIT_SYNONYMS`
carries no conversion from a molar concentration to the pChEMBL scale. A literature claim reporting an
IC50 in uM therefore cannot resolve against an attribute whose unit is pChEMBL, and is set aside as
`unit_unresolved`. This is why all 26 literature-bound criteria were clinical endpoints and not one was
a potency, although published selectivity tables are exactly where multi-target potency lives.

pChEMBL = -log10(IC50 in mol/L) is exact and is how ChEMBL computes its own column. Validated against
the reference compound's published selectivity table (PMC5522050, CC BY, Table 1): VEGFR3 0.001 uM
-> 9.000 against a ChEMBL median of 9.00, FGFR1 0.015 uM -> 7.824 against 7.82 -- two exact
reproductions, which both validate the conversion and indicate ChEMBL curated those rows from that
table. The same table reports VEGFR2 at 7.620 where ChEMBL's median is 8.31, i.e. pooling the
literature **lowers** that cell; the conversion is not uniformly favourable and is not applied
selectively.

## 7. Ranks measured, equal weights, nothing tuned

`ordering_method.weight_vector` can weight the mandated receptors above derived preferences. It was
left at equal weights: changing it now, knowing which direction helps, would be tuning.

**Provenance of the table below, stated because it is not all the same.** These rows are **offline
re-scores**, not published snapshots: they mirror `assessor.preference_scores` exactly (percentile over
candidates with a value, in the attribute's direction, ties shared; threshold rules 1 for pass and 0
for fail) over values fetched fresh from the ChEMBL activity tables, with RDKit standing in for
PubChem's descriptors -- molecular weight is identical, logP and TPSA differ slightly. The harness
reproduces the published board exactly on the baseline row, which is why it is trusted at all, but a
re-score is not the system's own output and is not reported as one. The pipeline run that produces
these numbers from the system is outstanding.

| instrument | rankable | reference compound |
|---|---|---|
| measured potency alone, >=1 receptor | 33 | **2** |
| full 9-criterion board, coverage floor 0.5 | 74 | **9** (beaten by 1-of-5 compounds, S5) |
| full 9-criterion board, mandated coverage complete | 17 | **tied 1st** (0.732639, with axitinib) |
| five-receptor profile ranked by worst receptor | 17 | **1** |
| five-receptor profile ranked by mean | 17 | **2** (axitinib 8.72 vs 8.48) |

The tie is informative: axitinib buys its score with peak VEGFR potency while sitting 36x weaker at
FGFR1 (6.57 against 7.82). The criterion that separates them is balance across the five required
receptors -- which the derivation proposed on its own, with the historical list firewalled, and which
is currently deferred because it is literature-bound.

**Outstanding and not yet done:** the mandated-coverage floor, the molar-to-pChEMBL conversion, a
literature route on the mandated receptor attributes, a re-derivation so ADMET criteria exist, and the
isolated-evaluator recovery measurement on the new set. The receptor comparison above uses ChEMBL
medians for the comparators and the literature table for one cell of the reference compound; a fair
literature pass must run over every shortlisted candidate, and its result is to be reported as it falls.
