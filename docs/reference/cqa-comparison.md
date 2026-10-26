# Original CQAs compared with the latest system output

[中文](../zh/cqa-comparison.md) · [JSON](../../examples/oral-multitarget/cqa-comparison.json) · [CSV](../../examples/oral-multitarget/cqa-comparison.csv)

The latest system names **two of the original eleven endpoints**: human intestinal absorption probability and CYP2C9 inhibition probability. CYP2C9 inhibition is an enabled ranking preference; intestinal absorption is deferred. Thus **one original endpoint appears in the 18 enabled decision rules**. No complete original pass/fail criterion is reproduced: thresholds, decision roles, or endpoint definitions differ. Three original rows have related quantities whose event identity remains unresolved, and six have no matching current endpoint.

This is a **descriptive post-hoc comparison**, completed on 17 October 2026 against fixed outputs. It does not remeasure acceptance endpoint B, establish blind recovery, or change the system criteria. No new model or derivation run was performed for the comparison.

## Which sets are being compared

| Set | Identity and counting basis |
|---|---|
| Original human-selected baseline | The manuscript authors' **11 CQAs** in Figure 1A(d). They are predicted probabilities or a prediction, applied as eleven required pass conditions. “Human-selected” describes who chose the criteria; it does not turn their predicted values into measured clinical outcomes. |
| Earlier system registry | The previously discussed **59 registered criteria** are an older system output. They are not the original authors' eleven-item baseline and are excluded from this comparison's denominator. |
| Latest working set | **53 current items**: 45 registered criteria and 8 unregistered pending proposals. Historical retired or merged proposals are excluded. |
| Latest enabled decision rules | **18 unique rules**: six eligibility requirements and 17 scoring criteria share five target criteria. Admission requires the oral condition and all five direct target observations; target values also contribute to ranking. |
| Latest reference context | **13 contextual observations**. They support interpretation. Together with the decision rules, 31 items enter assessment. |
| Not used in this evaluation | **22 items**: 14 registered but deferred and 8 unregistered proposals. “Present in the working set” does not mean “used in ranking.” |

The latest pin is task `task_01M52CBE5GYPK9F0MCZYBMPH84`, snapshot `lb_task_01M52CBE5GYPK9F0MCZYBMPH84_2`, `rules@v2`, published `2026-10-16T16:24:51.438Z`. Its source records are [cqa.json](../../examples/oral-multitarget/latest/results/cqa.json), [snapshot.json](../../examples/oral-multitarget/latest/results/snapshot.json), and [source-cqa-history.json](../../examples/oral-multitarget/latest/results/source-cqa-history.json). The comparison JSON pins the first two files by SHA-256.

## Original source and provenance

The baseline was checked directly against the user-supplied manuscript *Multi-target TME Reprogramming Awakens TLS driven Immunity in Ovarian Cancer*, PDF page 4, Figure 1A(d). The caption and adjoining text on pages 4–5 describe the eleven-condition conjunction. This repository contains only the factual endpoint/cutoff summary needed for comparison; the manuscript PDF and figure image are not redistributed.

Two local 60-page copies were checked. `CELL1.pdf` has SHA-256 `4332685173c953ddaf7adb855965378da580958fa904fd97ca9017acb34153d2`; `CELL.pdf` has SHA-256 `52bb911590edc7cd543d09e05b35537800380e6a61d5bed7be9099b77d3ed088`. Their embedded page-4 figure images have identical bytes, SHA-256 `a8065740ab23ae00579bf7535571f312b91d2a0f5e0170fd5ffc7dac9691590d`.

The retained local store contains two old comparison artifacts and two case-inheritance snapshots. The snapshots retain intake headers and digests; the standalone original intake payloads and old case streams are absent. Those headers have different intake digests, so their transcripts are not assumed identical. This comparison uses direct visual verification of the manuscript panel. Private intake/mapping content was not exported, and stored visibility was unchanged.

## Item-by-item comparison

“Same endpoint” below means that both descriptions explicitly name the same predicted endpoint. It does not establish that the historical and current predictors produce equivalent probabilities. “Related” preserves a substantive connection while leaving an event-definition gap explicit. Every original row retains its displayed comparison sign.

| Original ID | Original endpoint and required condition | Latest counterpart and state | Assessment |
|---|---|---|---|
| A.I | Human oral bioavailability, **20% class**, probability **> 0.5** | Generic Bioavailability_Ma probability, deferred; measured human F%, enabled preference | **Related, unresolved.** The generic prediction does not record a 20% class boundary. Measured F% and class probability are different quantities; both latest criteria have no cutoff. |
| A.II | Human intestinal absorption probability **> 0.5** | HIA_Hou probability, proposed **≥ 0.5** preference, deferred | **Same endpoint, changed decision.** Strict `>` differs from `≥` at 0.5. The proposed boundary lacks accepted predictor support and is withheld from evaluation. |
| A.III | Human oral bioavailability, **50% class**, probability **> 0.5** | Generic Bioavailability_Ma probability, deferred; measured human F%, enabled preference | **Related, unresolved.** No frozen definition identifies the 50% class. The generic probability is not counted again as recovery of a second class. |
| B.I | Breast cancer resistance protein probability **> 0.5** | No BCRP/ABCG2 criterion | **Absent.** P-glycoprotein inhibition is a different transporter endpoint. The original panel does not specify whether the BCRP event is substrate status, inhibition, or another event. |
| B.II | CYP2C9 inhibitor probability **< 0.5** | Predicted CYP2C9 inhibition probability, enabled preference, no cutoff | **Same endpoint, changed decision.** Lower values rank better; the original binary pass boundary is absent. |
| C.I | Maximum tolerated dose prediction **< 0** | No MTD criterion | **Absent.** Clinical toxicity, DILI, and hERG concern other outcomes. The original MTD unit and transformation are not stated in the panel. |
| C.II | NR-Aromatase probability **< 0.5** | No corresponding endpoint | **Absent.** General toxicity and required kinase potency do not measure this event. |
| C.III | NR-ER-LBD probability **< 0.5** | No corresponding endpoint | **Absent.** No estrogen-receptor ligand-binding-domain criterion is current. |
| C.IV | NR-GR probability **< 0.5** | No corresponding endpoint | **Absent.** No glucocorticoid-receptor endpoint is current. |
| C.V | NR-TR probability **< 0.5** | No corresponding endpoint | **Absent.** No thyroid-receptor endpoint is current. |
| C.VI | Skin sensitisation probability **< 0.5** | Skin_Reaction probability, enabled exploratory observation, no cutoff | **Related, unresolved.** The frozen definition describes rash/hand-foot skin reaction; it does not establish the historical sensitisation event. It contributes no ranking weight. |

The mutually exclusive descriptive counts are **2 same-named endpoints with changed decisions + 3 related/unresolved rows + 6 absent endpoints = 11**. Full operational criterion equivalence is established for **0** rows. These labels are intentionally separate from the historical evaluator's `exact / near_equivalent / missed` results.

The panel does not provide predictor versions, calibration, full event/assay definitions, applicability populations, or missing-value policy. Those fields are left unknown. In particular, the displayed BCRP `> 0.5` and MTD `< 0` conditions are preserved without inventing a biological direction or unit.

## What the latest core adds

The enabled core reflects a different decision structure: documented oral administration as a hard exclusion, evidence on five required kinase targets, and graded preferences. Its 18 rules comprise:

| Latest core group | Count | Connection to the original eleven |
|---|---:|---|
| Documented oral administration | 1 | A route-of-administration condition, distinct from predicted absorption or bioavailability. |
| CSF1R, FGFR1, VEGFR1, VEGFR2, VEGFR3 curated potency | 5 | Task-required target evidence. In the original manuscript, target prediction preceded the eleven-CQA filter. |
| Molecular weight, RDKit logP, BRENK/NIH/PAINS alert counts | 5 | Structural preferences not named among the original eleven endpoints. |
| BBB penetration; CYP1A2, CYP2C19, CYP2C9 inhibition; CYP2C9 substrate probability | 5 | Only CYP2C9 inhibition names an original CQA endpoint. The other predictions add distinct considerations. |
| Measured human oral F% and reported Tmax | 2 | Pharmacokinetic preferences. Measured F% is related to oral exposure but does not identify either original predicted bioavailability class. |

The machine-readable comparison lists every enabled core rule and every enabled exploratory observation with its exact reference, definition, role, cutoff and evaluation state. A related quantity is not automatically an equivalent original criterion, and an added dimension is not automatically a scientific improvement. Its usefulness depends on evidence and the intended decision.

## Historical recovery results remain separate

Two existing local results are retained in the comparison metadata:

| Historical comparison | Frozen task / rules | Exact | Near-equivalent | Missed |
|---|---|---:|---:|---:|
| `evr_01M50HFTFHPTV58AMBW9GNV5VH`, 15 Oct 2026 19:44 UTC | `task_01M4X892V1EAER2GHWE1RE19ZN`, `rules@v1`, seq 857 | 0 | 4 | 7 |
| `evr_01M50KK1T8CNQHP4YBFYTC4DZT`, 15 Oct 2026 20:20 UTC | `task_01M50JQYYQAMPBQTQ0N8YNQT22`, `rules@v1`, seq 1443; inherited assisted descriptive reading | 0 | 1 | 10 |

They use different frozen sets, intake digests and equivalence judgments. They are preserved as separate historical outcomes; neither is replaced by the latest comparison, and the three readings are not a recovery-performance trend. The full private mappings remain outside the publication.

The original manuscript describes a 3,171-compound library and a 140-candidate target-prediction stage. The latest evaluation contains 3,177 candidates and uses its declared evidence/qualification policy. Surufatinib's latest rank of 1 among 10 qualified candidates is a separate ranking result; it does not establish reproduction of the original eleven-condition screen.
