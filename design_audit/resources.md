# Resources: Data, Services, Compute, Expert Input, Reference Material, and Optional Training

Coordinating agent (drafting fork), 12 October 2026. Design-phase inventory of what the architecture in `optimized_design.md` needs, what the package supplies, what is missing, and what the design deliberately does not require. Names and vocabularies follow `optimized_design.md` Section 0. Nothing here was executed; all limits on supplied data come from the package inventory and read-only inspection.

## 1. Summary

The reusable core needs no accelerator, no trained model, and no specific language-model provider. The primary case needs four inputs the package does not contain (the candidate identity list, the authors' eleven CQAs, endpoint and unit conventions, the historical 140-binder stage) and a quantity of expert review that is the real rate limiter. Evidence tools are public, mostly keyless, and rate-limited; the only GPU dependency is optional (structure-based or CDES prediction). The no-additional-training baseline is the v1 system; two optional later efforts are specified as evaluated candidates.

## 2. Data

### 2.1 Case inputs and their owners

| Input | Needed by | Owner | Status | Record it populates |
|---|---|---|---|---|
| Identity list of the 3,171 FDA-approved or Phase III compounds (identifiers, structures, aliases) or an access path to it | Stage 6 identity resolution; the candidate universe | manuscript authors | not in the package | case configuration `candidate_universe {kind: named_library, access_path, as_of}`; Identity Service records |
| The authors' eleven historical CQAs with definitions, dimensions, thresholds, units, directions, and a completeness attestation | Stage 8 recovery comparison | manuscript authors (main text does not enumerate them) | not in the package | `historical_criteria_intake` with `visibility: evaluator_only` |
| Assay-endpoint and unit conventions for CSF1R, VEGFR1, VEGFR2, VEGFR3, FGFR1 | Stage 3 retrieval; criterion applicability | authors or domain experts | not in the package | adapter Vocabulary port; registry attributes' `unit`, `applicability_conditions` |
| The historical 140-binder stage (CDES probability > 0.9 on all five targets) as a comparison artifact | Stage 8 comparison only | authors | described in the manuscript text, list not supplied | `historical_stage_artifacts[]`, comparison-only |
| Evidence cutoff date and tool availability snapshot | Run Binding | operator | decision needed | `evidence_cutoff_at`, `tool_availability_snapshot` |
| Coverage floor for `recommended` and every cutoff basis | admission; registry | domain experts | expert dependency | `registered_constants[]` with `cutoff_basis` |

### 2.2 Supplied datasets (optional, `context_only`)

| Dataset | What it is | Established limits | Permitted use |
|---|---|---|---|
| `supporting_data/sanger-dose-response.csv` | GDSC1 and GDSC2 dose-response table, 387,626 rows, 20 columns, 397 drug-name strings, 989 cell-line identifiers | no match for surufatinib, sulfatinib, or HMPL-012-style aliases in `DRUG_NAME`; units and endpoint meanings undocumented in the package; `data_version` unknown; upstream dictionary pages returned HTTP 410 on 12 October 2026; missingness 15.55% for fitted columns and 74.25% for the log-transformed concentration column | absence statements and per-dataset provenance; never a criterion value; similar-class compounds present are not comparators by that fact |
| `supporting_data/P07post/` | Cell Ranger 8.0.0 MatrixMarket matrix 38,349 × 14,440, 21,037,146 entries, with feature and barcode files | post-treatment only; no matched pre-treatment sample; no sample or cell metadata; barcodes not a verified cell count | `comparison_possible: false` for any before–after contrast; a `required_inputs_manifest` names the missing baseline, QC parameters, annotation; never a criterion value |

### 2.3 Evidence sources (public, interface level)

Detailed in `tools.md` Section 2. Summary of access needs: PubChem PUG REST (keyless, policy-limited), UniChem (open), ChEMBL web services (keyless, CC BY-SA 3.0, release 37), BindingDB (keyless, dual CC BY 3.0 / CC BY-SA 3.0), Guide to PHARMACOLOGY (API key required, about 60 requests per minute, ODbL and CC BY-SA 4.0), Europe PMC REST (probed keyless; documentation not accessible), NCBI E-utilities (3 requests per second without a key, 10 with), ADMET-AI with TDC datasets (local, MIT code, per-dataset licenses including one CC BY-NC-SA 4.0), RDKit (local, BSD 3-Clause), Boltz-2 (optional, MIT, GPU).

## 3. External services and API access

| Service | Key | Rate limit as observed or cited | Failure handling in the design |
|---|---|---|---|
| PubChem PUG REST | none | ≤ 5 requests per second, ≤ 400 per minute, ≤ 300 s running time per minute, synchronous ≤ 30 s | broker `rate_limited` error class, bounded retry, circuit breaker → `degraded` |
| UniChem | none | not stated | same |
| ChEMBL web services | none | not stated; release-versioned | `data_version` = release label |
| BindingDB | none | not stated | per-value `license_id` |
| Guide to PHARMACOLOGY | required | about 60 per minute | `absence_reason: unauthorized` when the key is missing → `not_attempted` |
| Europe PMC REST | none observed (re-verify) | not stated | `access_state` per article |
| NCBI E-utilities | recommended | 3/s without key, 10/s with | same as PubChem |
| ADMET-AI, RDKit | none (local) | none | pinned release in `data_version` |
| Boltz-2 (optional) | none; weights download | none (local GPU) | `requires_other_environment` absence when no GPU |
| CDES (optional) | n/a | n/a | `not_installed` / `not_configured` absence with manifest |
| Language-model providers | per provider | per provider | Model Adapter Capability Record; `model_unavailable` error class; degradation record |

Every cache entry records `retrieved_at` and a staleness policy; a cached answer is a claim about a past release.

## 4. Compute

- **Baseline (no-CDES):** no accelerator. Retrieval is network-bound; descriptor and property prediction are CPU-feasible at the scale of a few thousand structures; rule evaluation is deterministic and cheap; language-model calls dominate cost and are budgeted per role and loop class by C6.
- **Optional:** one GPU for Boltz-2 or for a CDES checkpoint; both are `cost_latency_class: batch` providers behind the capability registry and are never required for a run to reach `completed`.
- **Evaluation:** policy-arm comparisons multiply run cost roughly by the number of arms times `n_repeats` (floor three); the design requires variance-estimation pilots before any promotion claim, so the first evaluation budget is a pilot budget.
- **Hosts and surfaces:** the service host runs on Linux or Windows (design §14.1, ADR-36); the browser workbench targets current stable Chrome; the terminal client targets Linux. GPU-backed optional tools may be unavailable on a given Windows machine and are then recorded as absent (U-14).
- **Design-phase host used:** a single Linux node; no model was trained or run.

## 5. Storage

Local-first, single-node stores as in `optimized_design.md` Section 14: append-only journals per stream; content-addressed artifact store; Claim Ledger; Criterion Registry; Assessment Ledger; leaderboard snapshots; memory store with operations log; review queue and decisions; evaluation store; submission store; role-gated trace store; tool cache. Volume is cache- and journal-dominated: for the primary case, per-candidate per-criterion rows for a 3,171-compound universe and roughly a dozen criteria are tens of thousands of sparse rows per snapshot; retrieved open-access full texts and cached API responses are the largest items. Retention: completion events, artifacts, ledgers, snapshots, decisions, and evaluation records indefinitely; heartbeats in a bounded window; caches by policy.

## 6. Model access

- Provider-agnostic role resolution; each role bound at run start to a model adapter with a Model Adapter Capability Record and interface-level contract-test results.
- **Cross-family critic availability is a dependency** of the independence design (ADR-06): consequential decisions require a cross-family or human check; if only one model family is available the independence marker records `same_family` and the design never claims independence.
- No model weights are trained, fine-tuned, or calibrated in v1; evidence strength derives from source kind and provenance, never from a model's own score.
- Raw model I/O is stored in the role-gated trace store; the default UI never shows it.

## 7. Expert input (the scarcest resource)

Expert review is the real rate limiter of the primary case. Each item below is a Human Review Queue trigger (design Section 12.1) or a registered constant; none is resolved by the architecture and none is a blocker for implementing it.

| Expert dependency (from WS1 §10 and the trigger table) | Enters the system as |
|---|---|
| Which attributes may carry hard exclusions at all | `rule_kind` confirmation per rule, `hd_` record |
| Every cutoff and its `cutoff_basis`, including whether evidence supports a number or only a range, and whether a qualitative determination may exclude | `cutoff`, `uncertainty_range`, `cutoff_basis` on rule versions; `const_` records |
| Applicability conditions per attribute and the meaning of `inapplicable` for the objective | `applicability_conditions[]` |
| Relative standing of source statuses and what makes conflicting claims comparable | conflict-resolution `hd_` records; `on_conflict` policy |
| Independence grouping where shared experiments or datasets are suspected | `independence_group.determined_by` |
| Candidate identity equivalence across salt forms, formulations, codes, ambiguous names | `identity_merge` decisions |
| Unit and endpoint normalization across heterogeneous measurement contexts | `unit_correction` decisions |
| The hard-rule coverage floor for `recommended`, and whether predicted values may ever satisfy a hard rule | `const_coverage_floor`; `acceptable_value_sources` |
| Equivalence judgments in the recovery comparison | `recovery_mapping` decisions with `match_basis: expert_judged_equivalent` |
| Whether the five-target configuration is a constraint or a questioned hypothesis | case configuration `scope_entities[].role` |
| Admission of every human submission that would change a candidate state (reviewer other than the submitter) | `submission_admission` decisions |
| Approval of every `recommended` publication where the case requires it | `candidate_state` decisions |

Load estimate: Workstream 1 judged "plausibly dozens of decisions for the primary case"; no number is registered here. The queue batches items, precomputes stale/rerun consequences, and separates blocking from non-blocking items to limit expert minutes; human-review minutes are a budgeted quantity in C6 and reported beside every metric.

## 8. Reference repositories (cloned read-only; none modified; none a runtime dependency)

Location: `/home/yiwei3_duke/anny/reference_repos/` on the design host, outside the project repository.

| Repository | URL | Commit (date) | License as found | Informs |
|---|---|---|---|---|
| Agentic Doping, packaged snapshot (primary) | github.com/YWDDLiang/Agentic-Doping | `0007ad10` (2026-08-12), tip of `cloud_deployment` | repository license not restated here; excerpts packaged by the user | C1, C7, C9, C14, C15, C17; reuse verdicts in `audit_report.md` §4; packaged excerpt hashes verified 11/11 |
| Agentic Doping, `main` | same | `7cdf6591` (2026-07-09), 53 commits behind the snapshot | same | what changed between `main` and the snapshot |
| DeepSeek Harness | github.com/deepseek-ai/deepseek-harness | `d7432673` (2026-10-09), shallow clone | MIT; developer preview | C1 event taxonomy and projections; C13 durable tool call/result; C15 crash closure |
| ARIS | github.com/wanshuiyin/Auto-claude-code-research-in-sleep | `26b95cfa` (2026-10-07), shallow clone | MIT | C7 independence rules and code-computed verdicts; C15 stall ladder; C18 done-versus-accepted |
| Darwin Gödel Machine | github.com/jennyzzt/dgm | `a565fd2d` (2025-08-13) | Apache-2.0 | C19/C20 archive, staged budgets, noise leeway; the same-set selection hazard |
| hsi | github.com/TailinZhou/hsi | `97a022b9` (2026-08-23) | README states "MIT"; no LICENSE file or header text found | C19/C20 frozen selector, LCB reward, split discipline; C7 falsification test |
| ACE | github.com/ace-agent/ace | `82709de0` (2026-08-24) | Apache-2.0 (`LICENSE.txt`) | C14 delta-item memory and operation discipline |
| HGM | github.com/metauto-ai/HGM | `013872d9` (2026-02-08) | Apache-2.0 | C20 lineage metrics warning; separate post-run evaluation |

Not cloned: facebookresearch/Hyperagents (CC BY-NC-SA 4.0, non-commercial); Group-Evolving Agents (no official repository located); AIDE² outer loop (not released). The five Windows-path local projects named in the historical prompts were not available on this host; per the user, four were treated as outdated and replaced by the references above.

## 9. Design-phase tooling used

Conda environment `mas-audit` (conda-forge only): Python 3.11, pypdf, pdfplumber, requests, pyyaml, jsonschema, pandas, tabulate, GitHub CLI 2.102.0; system `pdftotext` for read-only extraction of the five reference PDFs to the session scratchpad. Used for PDF text extraction, repository metadata lookups, hash verification of packaged excerpts, and consistency checks of the deliverables. None of this is part of the designed system.

## 10. Missing resources (recorded, not blocking the architecture)

1. Candidate identity list for the 3,171-compound library (authors).
2. The authors' eleven CQAs with a completeness attestation (authors).
3. Endpoint and unit conventions for the five targets (authors or experts).
4. CDES code, checkpoint, training data, and screening outputs (not in the package; optional).
5. GDSC data dictionary and release notes (upstream pages returned HTTP 410).
6. Outcome labels for criterion derivation; none exist, so domain-outcome validation rests on qualified expert review and the historical list used at most once per strategy version.
7. Variance estimates for agent-policy comparisons; pilots must come first.
8. A second case for held-out strategy evaluation across more than the primary case.
9. Cross-family model access for consequential decisions (declared dependency).
10. Expert availability and identity attestation for `hd_` records.

## 11. Optional model adaptation or training (none necessary for v1)

**No-additional-training baseline (the v1 system).** All four dimensions are served by retrieval plus published models at fixed, recorded versions; prompts, procedures, retrieval rules, and tool contracts are the only adjustable strategy components; nothing is trained, fine-tuned, or calibrated; missing values stay `unknown`; this is the comparison arm for any later model and for every strategy version.

| Effort | Purpose | Technical approach | Data and labels | Evaluation | Cost | Necessary for v1 |
|---|---|---|---|---|---|---|
| Evidence-extraction model (later, optional; WS3 §7) | extract `(endpoint, value, unit, conditions, direction)` tuples from retrieved full text with conflict detection against existing ledger records | first a calibrated verifier over language-model extractions; supervised fine-tuning of a small extraction model only if that is insufficient | paragraphs of already-retrieved open-access full texts; labels = reviewer-verified extractions admitted through the Human Review Queue (ledger-gated, as the reference project gates its training buffer) | held-out reviewer-verified extractions scored on exact agreement of value and unit plus conflict-detection recall, against the untrained baseline at matched budget; value shown as reviewer-minutes per accepted evidence record at equal or better accuracy | modest, single accelerator | no; gated on a stated minimum of reviewer-verified records existing first |
| GEPA-style offline prompt optimizer (candidate for C19/C20) | revise role prompts and delegation or retrieval rules as strategy versions | reflective prompt mutation driven by the harness metric and the textual feedback already produced by critiques and verification failures; run offline on a fixed evidence snapshot; promote only on held-out criteria under the C19 conjunction; rollback kept | development pool tasks; textual feedback from critiques; no labels beyond the process metrics; the historical-criteria artifact invisible to the optimizer | matched-budget comparison against the fixed baseline on held-out tasks across more than one case, lower confidence bound over repeats | validation-dominated token budget (the method's own reports) | no; a `change_class: prompt_text` strategy change, not training |
| Model-weight training of any kind | — | excluded for v1 by the governing prompt; would require a stated task and label source, a held-out set disjoint from training, the no-additional-training baseline under the same protocol, cost accounting, and a gain over the prompt/memory baseline | — | — | — | no |

Prompt or memory updates and model-weight training are distinguished by `change_class` on every strategy version; reflection-authored prompt text is a memory update, never training.

## 12. Sources

`agent_reports/tools_and_data.md` (§3 source table, §5 dataset contracts, §7 resources and training, contribution record); `agent_reports/evidence_and_policy.md` §10 (expert dependencies); `agent_reports/reference_harness_inspection.md` (§3–§5, §8 licenses and commits); `agent_reports/current_agent_literature_b.md` §7 (repository recommendations); `MAS_MultiAgent_Design_Audit_EN_20261012/04_Source_Inventory_EN.md` and `ARTIFACT_MANIFEST.json` (dataset limits); coordinator clone and environment records (12 October 2026); `optimized_design.md` Sections 2, 12, 14, 16.
