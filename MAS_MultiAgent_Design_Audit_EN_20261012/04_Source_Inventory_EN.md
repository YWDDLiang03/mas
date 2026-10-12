# Source Inventory and Intended Uses

Inventory date: 12 October 2026. The archive and local materials were inspected without running a medical screening experiment. Publication descriptions below refer to the supplied PDF versions, not a survey of subsequent publication updates. The primary research focus for the next agent is agent architecture and current agent/RSI/self-evolving methods. Biomedical sources supply the required first case: completing the rebuttal's workflow and substantiating surufatinib prioritization. Reusable interfaces should support other inputs later, without requiring an exhaustive biology review now.

## Manuscript and supplied references

| ID | Included material | Version or publication identity | Role in this package | Use boundary |
|---|---|---|---|---|
| M1 | [Multi-target TME Reprogramming Awakens TLS-driven Immunity in Ovarian Cancer](references/Manuscript_TME_TLS_Ovarian_Cancer.pdf) | Supplied 60-page manuscript. Its original source identity is preserved in the artifact manifest. Submission/publication status is not independently established here. | Defines the research context, historical CDES cascade, and known surufatinib outcome. | Its reported findings do not establish that the newly proposed MAS has been implemented or evaluated; CDES is optional in the new design. |
| R1 | [AI-driven discovery of dual antiaging and anti-AD therapeutics via PROTAC target deconvolution of a super-enhancer–regulated axis](references/Sun_2025_AI_Drug_Discovery_PROTAC.pdf) | Sun et al., *Science Advances* 11, eadz9283; 19 November 2025. [DOI](https://doi.org/10.1126/sciadv.adz9283). | An example of computational candidate screening followed by distinct experimental evidence. | It does not provide CQA thresholds or MAS performance evidence for ovarian cancer. |
| R2 | [Predicting cellular responses to perturbation across diverse contexts with State](references/State_2025_Supplied_Preprint.pdf) | Supplied bioRxiv version posted 10 July 2025. [DOI](https://doi.org/10.1101/2025.06.26.661135). The supplied copy explicitly identifies itself as a preprint. | Context for a possible future perturbation-prediction tool. | No model checkpoint, compatible perturbation dataset, or local evaluation is included; it is optional to the MAS concept. |
| R3 | [scTenifoldKnk: An efficient virtual knockout tool for gene function predictions via single-cell gene regulatory network perturbation](references/Osorio_2022_scTenifoldKnk.pdf) | Osorio et al., *Patterns* 3, 100434; March 2022. [DOI](https://doi.org/10.1016/j.patter.2022.100434). | An example of computational gene perturbation from single-cell expression. | A virtual gene knockout does not directly establish a drug's dose-dependent effect, exposure, or CQA values. |
| R4 | [Dissecting cell identity via network inference and in silico gene perturbation](references/Kamimoto_2023_CellOracle.pdf) | Kamimoto et al., *Nature* 614; online 8 February 2023. [DOI](https://doi.org/10.1038/s41586-022-05688-9). | An example of cell-state analysis using inferred regulatory networks and transcription-factor perturbations. | Applicability to the proposed drug-target setting must be established; the paper is not direct evidence for surufatinib prioritization. |

## Optional datasets

| Included files | Observed structure | Possible future use | Limitations established by this inspection |
|---|---|---|---|
| [P07post matrix](supporting_data/P07post/matrix.mtx.gz), [features](supporting_data/P07post/features.tsv.gz), [barcodes](supporting_data/P07post/barcodes.tsv.gz) | MatrixMarket integer matrix: 38,349 rows, 14,440 columns, 21,037,146 stored entries. Feature and barcode counts match those dimensions. Header reports Cell Ranger 8.0.0. | Optional cell-state or target-expression context after appropriate QC and annotation. | The folder is labelled P07post. No separate metadata or matched pre-treatment sample is supplied in this archive. Barcodes are not treated as an independently verified count of high-quality cells. |
| [Sanger dose-response table](supporting_data/sanger-dose-response.csv) | 387,626 rows and 20 columns; GDSC1: 268,718 rows, GDSC2: 118,908. There are 397 distinct nonmissing drug-name strings and 989 distinct COSMIC IDs. | Optional cell-line response context and comparator coverage checks. | No match for surufatinib, sulfatinib, or HMPL-012-style aliases was found in `DRUG_NAME`. This is not a direct five-target binding or ADMET table. Units, provenance version, and endpoint meanings require the upstream data dictionary before modeling. |

The GDSC table contains names such as AXITINIB, CABOZANTINIB, PAZOPANIB, SORAFENIB, and SUNITINIB. Their presence does not select them as definitive comparators. Missingness differs by column: `ec50`, `auc`, and `R2` are missing in approximately 15.553% of rows, while `log2.ic50` is missing in approximately 74.254%. No missing values were imputed and no response model was fitted.

The supplied archive contains four reference PDFs and four data files. It contains no CDES source code, checkpoint, complete candidate screening output, or executed medical MAS history. CDES is optional. The design audit and core workflow should proceed without it, using available evidence and suitable alternative tools while identifying unresolved numerical questions.

## Original-to-packaged mapping

| Original location | Packaged location |
|---|---|
| M1: local manuscript PDF | `references/Manuscript_TME_TLS_Ovarian_Cancer.pdf` |
| R1: Sun et al. reference PDF in `2lyw.rar` | `references/Sun_2025_AI_Drug_Discovery_PROTAC.pdf` |
| R2: supplied State preprint PDF in `2lyw.rar` | `references/State_2025_Supplied_Preprint.pdf` |
| R3: scTenifoldKnk PDF in `2lyw.rar` | `references/Osorio_2022_scTenifoldKnk.pdf` |
| R4: CellOracle PDF in `2lyw.rar` | `references/Kamimoto_2023_CellOracle.pdf` |
| P07post feature, barcode, and matrix files in `2lyw.rar` | `supporting_data/P07post/` |
| Sanger dose-response CSV in `2lyw.rar` | `supporting_data/sanger-dose-response.csv` |
| User's three-paragraph rebuttal supplied in this task | [Original rebuttal with status annotation](03_Provided_Rebuttal_Draft_EN.md) |
| `D:/codex_work/ai4s/agentic_doping` | [Reference note](02_Agentic_Doping_Reference_EN.md) and [selected-source manifest](agentic_doping_reference/SOURCE_MANIFEST.json) |
| Original Agentic Doping project request supplied by the user | [English translation](06_Agentic_Doping_Original_Prompt_English_Translation.md); historical requirements, not completed functionality |
| Targeted read-only inspection of Agentic Doping progress/history source | [Progress and iteration reference](07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md); implementation observations separated from proposed biomedical requirements |

The original archive and local manuscript are unchanged. Binary files are copied or extracted byte-for-byte. [Artifact manifest](ARTIFACT_MANIFEST.json) records their individual hashes and origin mappings. Original non-English path components use JSON Unicode escapes so the visible package documentation and filenames remain English. Agentic Doping excerpts preserve the selected source lines without reinterpreting project results as medical evidence.
