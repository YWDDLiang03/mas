# Tools: Researched Packages, Data Sources, and Reference Implementations

Coordinating agent (drafting fork), 12 October 2026. Design-phase document: every entry is described at the interface level (what it does, inputs and outputs, how it registers with the Tool Broker, license, limits, where it enters the workflow). No adapters are implemented and no executable examples are given. All URLs were accessed on 12 October 2026 by Workstream 3 unless stated otherwise; reading depth per URL is recorded in `agent_reports/tools_and_data.md`. Names and vocabularies follow `optimized_design.md` Section 0; the tool contract, invocation, result, and provenance records are those of Section 7.

## 1. Conventions used in this document

**Capability naming (added after independent review).** Capability names used in this document (`identity_resolution`, `interaction_evidence_lookup`, `interaction_estimate`, `property_estimate`, `literature_retrieval`) are the drug adapter's declared bindings of the core's domain-neutral `capability_kind` values (`entity_resolution`, `relationship_evidence_lookup`, `relationship_estimate`, `attribute_estimate`, `source_retrieval`); see `optimized_design.md` §7.1 and ADR-29. The core resolves tools on the kind, never on the adapter label.

- **Capability** is one of the core list consumed by the Tool Broker (C13): `identity_resolution`, `interaction_evidence_lookup`, `interaction_estimate`, `property_estimate`, `literature_retrieval`, `document_reading`, `dataset_context_lookup`, `rule_evaluation`. Resolution is by `(capability, question_kind, required_value_kind)`, never by tool name.
- **Evidence kind produced** is one of the ten Section 0.4 evidence kinds; **claim_strength_ceiling** is the highest value kind a result may carry (`predicted` | `curated` | `measured`); the broker rejects payloads exceeding it.
- **Workflow entry** names the Section 3 stage and the components that consume the result.
- Every v1 evidence tool is `side_effect_class: read`. Every result carries unit, `value_kind`, uncertainty, `data_version`, and the thirteen-field provenance block (Section 7.4); `outcome` uses the merged vocabulary `ok | partial | empty | not_attempted | failed | unknown_outcome`.
- A successful call never validates a claim (Section 7.7). Nothing below sets a threshold; thresholds are criterion-registry decisions with a recorded `cutoff_basis`.
- **Platform.** Every contract also declares `supported_platforms[]` with a `platform_support_basis`, an `execution_location`, and `platform_independent_output` (design §7.1, §14.2). The web services of Section 2 are reached over HTTPS, do not depend on the host platform, and declare `platform_independent_output`; locally installed tools (RDKit, ADMET-AI, Boltz-2, a CDES checkpoint) are `platform_support_basis: unchecked` on both platforms until checked at implementation (Section 9), their results enter fingerprints with `executed_on`, and a tool that cannot run on the host is recorded as absent with `requires_other_environment`.

## 2. Evidence tools and data sources for the no-CDES route

### 2.1 RDKit — structure handling and computed descriptors

- **Primary links.** rdkit.org/docs/index.html (release 2026.09.1 observed); license text raw.githubusercontent.com/rdkit/rdkit/master/license.txt (BSD 3-Clause confirmed).
- **What it does.** Parses structure strings and molecule files, normalizes structures, computes canonical keys and physicochemical descriptors.
- **Why it fits.** Every evidence join needs a resolved identity; descriptors supply computed inputs for oral-bioavailability attributes.
- **Inputs → outputs.** Structure string or molecule file → canonical structure, structure key, computed descriptors with units.
- **Interface.** Capability `identity_resolution` (normalization step) and `property_estimate` (descriptors). `evidence_kind_produced: derived_identity` for identity and `computational_simulation`/`derived` for descriptors; `claim_strength_ceiling: predicted` (a descriptor is a computed property, not a measurement); `uncertainty_model: none`; `determinism: deterministic` with the library version in the reproducibility key; `cost_latency_class: interactive`; local dependency, no network.
- **License and availability.** BSD 3-Clause (attribution, no endorsement). Local installation.
- **Limitations.** Descriptor values are version-sensitive; salt, tautomer, and stereo handling must be declared by the adapter's Identity Rules port.
- **Workflow entry.** Stage 6 identity resolution before any lookup; Stage 3 property inputs. Consumers: Identity Service, C11.

### 2.2 PubChem PUG REST — identity resolution and cross-references

- **Primary links.** pubchem.ncbi.nlm.nih.gov/docs/programmatic-access; the PUG REST documentation page itself is client-rendered and returned no body to the fetch tool, so the usage-policy figures below come from search results citing that page (snippet-level).
- **What it does.** Resolves names, structures, and structure keys to a compound record with depositor cross-references.
- **Why it fits.** Aggregator with the widest identity coverage; the first stop for ambiguous names and brand or code aliases.
- **Inputs → outputs.** Name, structure string, structure key, or compound id → identity record, synonyms, cross-references.
- **Interface.** Capability `identity_resolution`; `evidence_kind_produced: database_entry`; `claim_strength_ceiling: curated`; `determinism: external_state_dependent` (data version = retrieval date); `cost_latency_class: short`; `rate_limit_declaration`: at most 5 requests per second, 400 per minute, 300 seconds of running time per minute, synchronous calls under 30 seconds (per policy as cited).
- **License and availability.** No copyright asserted on aggregated data; depositor records may carry their own terms. No key required.
- **Limitations.** Depositor quality varies; name resolution is ambiguous for salts, stereoisomers, brand names; an `identity_link_basis` of `name_match_ambiguous` routes to the Human Review Queue.
- **Workflow entry.** Stage 6 identity gate for the whole candidate universe; consumers: Identity Service, C9 entity typing.

### 2.3 UniChem — identifier crosswalk

- **Primary link.** chembl.gitbook.io/unichem (full page read).
- **What it does.** Maps a compound identifier across chemistry resources by a standard structure hash.
- **Why it fits.** Deterministic crosswalk between PubChem, ChEMBL, BindingDB, and other identifier schemes; the mechanism behind `identity_link_basis: authority_crosswalk`.
- **Inputs → outputs.** Identifier or structure → identifier set across sources.
- **Interface.** Capability `identity_resolution`; `evidence_kind_produced: database_entry`; `claim_strength_ceiling: curated`; `determinism: external_state_dependent`; `cost_latency_class: short`.
- **License and availability.** EMBL-EBI terms; open.
- **Limitations.** Strict structure-hash equality: salt, tautomer, and stereo variants do not unify, producing silent under-matching; the adapter's Identity Rules must declare how variants are treated as aliases.
- **Workflow entry.** Stage 6 identity reconciliation and duplicate detection across sources.

### 2.4 ChEMBL web services — curated bioactivity

- **Primary links.** chembl.gitbook.io/chembl-interface-documentation/web-services (landing), /about (CC BY-SA 3.0; normalization and assay-confidence statements), /downloads (release 37, May 2026; release DOIs).
- **What it does.** Bioactivity records abstracted from primary literature with standardized activity type, value, unit, and an assay-to-target confidence level.
- **Why it fits.** The primary measured-value source for target coverage; release-versioned, so `data_version` is a real field.
- **Inputs → outputs.** Compound, target, or assay query → activity records with standardized type, value, unit, assay–target confidence, source document reference.
- **Interface.** Capability `interaction_evidence_lookup`; `evidence_kind_produced: curated_measurement`; `claim_strength_ceiling: curated` (the measurement was performed elsewhere and curated here; the Claim record carries `determination_basis: measured` with the primary source as location); `uncertainty_model: stated_sd` where present else `none`; `determinism: external_state_dependent` with release label; `cost_latency_class: short`; no key required.
- **License and availability.** CC BY-SA 3.0 with release DOIs.
- **Limitations.** Normalization is best-effort; confidence levels must be carried, not collapsed; values inherit the original assay's conditions, which must populate `scope`; records imported from other databases need independence grouping.
- **Workflow entry.** Stage 3 retrieval for named compound–target pairs; Stage 6 per-candidate assessment of target-coverage attributes. Consumers: C9, C11.

### 2.5 BindingDB — curated binding measurements

- **Primary link.** bindingdb.org/rwd/bind/info.jsp (full page: measurement types, scale, access, dual licensing).
- **What it does.** Curated protein–small-molecule binding measurements with assay references and thermodynamic parameters.
- **Why it fits.** Second provider for target coverage and a cross-source agreement check.
- **Inputs → outputs.** Compound or target query → affinity constants and parameters with assay references.
- **Interface.** Capability `interaction_evidence_lookup`; `evidence_kind_produced: curated_measurement`; `claim_strength_ceiling: curated`; `determinism: external_state_dependent`; `cost_latency_class: short`; no key required.
- **License and availability.** Two licenses in one response: CC BY 3.0 for BindingDB-curated rows, CC BY-SA 3.0 for rows imported from ChEMBL; the provenance block must carry `license_id` per value.
- **Limitations.** Heterogeneous assay types; provenance overlaps ChEMBL, so the same underlying experiment can appear twice and must share an `independence_group`.
- **Workflow entry.** Stage 3 and Stage 6 as a second `interaction_evidence_lookup` provider in the case-configured preference order.

### 2.6 IUPHAR/BPS Guide to PHARMACOLOGY web services — expert-curated interactions

- **Primary link.** guidetopharmacology.org/webServices.jsp (full page: endpoints, API key, roughly 60 requests per minute, ODbL and CC BY-SA 4.0).
- **What it does.** Expert-curated target–ligand interactions with species, affinity parameter type, action type, and reference.
- **Why it fits.** Highest curation quality for the target-coverage dimension; preferred where a record exists.
- **Inputs → outputs.** Target, ligand, or interaction query → records with parameter type, value, species, action type, reference.
- **Interface.** Capability `interaction_evidence_lookup`; `evidence_kind_produced: curated_measurement`; `claim_strength_ceiling: curated`; `determinism: external_state_dependent`; `cost_latency_class: short`; `rate_limit_declaration` about 60 per minute; `prerequisites`: API key (required as observed on 12 October 2026).
- **License and availability.** Database under ODbL, content under CC BY-SA 4.0.
- **Limitations.** High quality, low coverage: the absence of a record is not evidence of no interaction, so an `empty` outcome must not become a negative claim.
- **Workflow entry.** Stage 3 and Stage 6, first in preference order for target coverage where a record exists.

### 2.7 Europe PMC REST — literature search and open-access full text

- **Primary links.** ebi.ac.uk/europepmc/webservices/rest/ (documentation root returned HTTP 404; the public search endpoint was probed live for response-schema fields only); europepmc.org/RestfulWebService and /Help returned HTTP 403 to the fetch tool.
- **What it does.** Literature search with source, identifiers, title, journal, year, open-access and repository flags, citation count, and full-text identifiers for the open-access subset.
- **Why it fits.** Carrier of claims for all four dimensions; its open-access flags set an honest `access_state` and `reading_depth`.
- **Inputs → outputs.** Query → result list with identifiers and flags → full-text retrieval for open-access items.
- **Interface.** Capabilities `literature_retrieval` and `document_reading`; `evidence_kind_produced: peer_reviewed` or `preprint` as flagged (the source record's `source_status` is set from the response, never assumed); `claim_strength_ceiling` for extracted claims depends on the claim's `determination_basis`, not the tool; `determinism: external_state_dependent`; `cost_latency_class: short`; the "no key required" statement comes from a search snippet and must be re-verified before implementation.
- **License and availability.** Reuse governed by each article's license; the REST service itself was usable without a key in the probe.
- **Limitations.** Full text only for the open-access subset; everything else yields `access_state: abstract_only` and a `limitation_kind: full_text_unavailable` on dependent assessments.
- **Workflow entry.** Stage 3 title screening → title-and-abstract screening → full-text reading; Evidence Retriever with search coverage records.

### 2.8 NCBI E-utilities (PubMed) — indexed literature search

- **Primary link.** ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/ (rate limits and key policy); the reference chapter at ncbi.nlm.nih.gov/books/NBK25501/ returned a reCAPTCHA interstitial.
- **What it does.** Database plus query → record identifiers and metadata.
- **Why it fits.** Parallel literature provider, de-duplicated against Europe PMC by identifier.
- **Inputs → outputs.** Query → identifiers and abstract-level metadata.
- **Interface.** Capability `literature_retrieval`; `evidence_kind_produced` as flagged by the record; `determinism: external_state_dependent`; `cost_latency_class: short`; `rate_limit_declaration`: 3 requests per second without a key, 10 with one.
- **License and availability.** NCBI usage policy; key recommended.
- **Limitations.** Abstract-level only; complements rather than replaces Europe PMC.
- **Workflow entry.** Stage 3 as a second `literature_retrieval` provider.

### 2.9 ADMET-AI over Therapeutics Data Commons datasets — property prediction

- **Primary links.** github.com/swansonk14/admet_ai (README: purpose, TDC basis, MIT license, v1/v2 divergence caveat); github.com/mims-harvard/TDC (README: MIT code, per-dataset licenses); tdcommons.ai/single_pred_tasks/adme/ and /tox/ (endpoint listings with units, sizes, licenses).
- **What it does.** Predicts property endpoints from a structure string across absorption, distribution, metabolism, excretion, and toxicity tasks.
- **Why it fits.** The only no-CDES route to a value for property attributes on candidates with no published measurement; outputs are explicitly predictions.
- **Inputs → outputs.** Structure string → per-endpoint predicted value or class probability.
- **Interface.** Capability `property_estimate`; `evidence_kind_produced: model_prediction`; `claim_strength_ceiling: predicted`; `uncertainty_model: class_probability` for classification endpoints and `none` for regression unless the release documents otherwise (a class probability is never a reliability estimate); `determinism: deterministic` given a pinned release; `cost_latency_class: short` on CPU at the scale of a few thousand structures; `data_version` = pinned package release plus dataset versions.
- **License and availability.** Code MIT; most TDC datasets CC BY 4.0, at least one CC BY-NC-SA 4.0, so the per-dataset license travels in `license_id` per value.
- **Limitations.** v2 predictions differ from v1, the paper, and the web server, so the version must be pinned and recorded; several endpoints train on only hundreds of compounds; predicted liabilities are not calibrated risk; a criterion whose `acceptable_value_sources` excludes `model_prediction` will see these results as `unknown`.
- **Workflow entry.** Stage 6 after identity resolution, for oral bioavailability, metabolic stability, and toxicological safety attributes that admit predicted values.

### 2.10 Boltz-2 (optional) — structure-based complex and affinity prediction

- **Primary links.** github.com/jwohlwend/boltz (README: MIT license, input form, the two affinity outputs and their stated distinct uses, hardware notes); boltz.bio/boltz2 (not fetched directly; cited via search snippets).
- **What it does.** Predicts a protein–ligand complex structure and two affinity-related outputs: a value stated as log10 of IC50 in micromolar and a binary binder probability.
- **Why it fits.** The best-documented open structure-based affinity predictor for the optional `interaction_estimate` slot when retrieval leaves a consequential gap.
- **Inputs → outputs.** Sequence and ligand description → predicted structure, affinity value, binder probability.
- **Interface.** Capability `interaction_estimate`; `evidence_kind_produced: model_prediction`; `claim_strength_ceiling: predicted`; `uncertainty_model: class_probability` for the binary output and `none` for the value; `determinism: seeded_stochastic`; `cost_latency_class: batch`; `prerequisites`: GPU strongly recommended, weights download.
- **License and availability.** MIT; weights for academic and commercial use.
- **Limitations.** The repository assigns the two outputs different intended uses (binder/decoy separation versus affinity comparison); conflating them is a misuse. The manuscript names this model as the comparator CDES outperformed; the case configuration records the collision and prohibits any inference about CDES's relative merit from its use.
- **Workflow entry.** Stage 9 only, as a `decision_relevant_computation` trigger in the Open-Question Register for consequential gaps; never a default stage.

## 3. The CDES adapter (optional)

**Contract if present.** `tool_id: drug_v1.cdes`; capability `interaction_estimate`; inputs: resolved compound identity (structure key plus canonical structure string plus source identifier) and resolved target identity (protein accession, sequence version, isoform); outputs: one interaction probability in [0, 1] per compound–target pair plus `model_version`, `checkpoint_id`, `training_data_version`, `calibration_metadata`, `applicability` flag; `evidence_kind_produced: model_prediction`; `claim_strength_ceiling: predicted`; `uncertainty_model: class_probability`; `determinism: seeded_stochastic`; `cost_latency_class: batch`; `prerequisites`: code, checkpoint, GPU environment.

**What it adds.** Uniform coverage of all candidate–target pairs (for the primary case roughly 15,855 pairs); no retrieval route can do that.

**What it requires before any criterion may depend on it.** The package contains no code, checkpoint, training data, or screening output (`ARTIFACT_MANIFEST.json`: `scientific_models_run: false`). Beyond those: training-set provenance and license; train/test split; an overlap check against the reference candidate and the five targets (leakage is a live risk because the outcome is disclosed); calibration data giving any probability cut a meaning; a stated threshold rationale registered as a `const_` with `cutoff_basis`.

**Absence and failure.** Provider not registered (`not_configured`); resolution falls through to retrieval and property providers; affected cells `unknown_missing` with `absence_reason: not_installed` or `not_configured` and a `required_inputs_manifest`; candidates `provisional` or `unassessed`, never `rejected` for want of a prediction; the snapshot carries `interaction_estimate_provider: none`. A later arrival enters as an evidence-refresh run with an agreement check against curated measurements recorded first.

## 4. Supplied datasets as `context_only` adapters

Both register under `dataset_context_lookup` with `role: context_only`; both publish machine-readable refusals rather than prose warnings. Contracts are written from the package inventory only.

**GDSC dose-response table (`supporting_data/sanger-dose-response.csv`).** Twenty declared columns with identity keys `DATASET`, `COSMIC_ID`, `DRUG_ID`, `DRUG_NAME`, `BROAD_ID`, `ARXSPAN_ID`; 387,626 rows (268,718 GDSC1, 118,908 GDSC2); 397 distinct drug-name strings; 989 distinct cell-line identifiers. Published refusals: zero matches for the three reference-candidate aliases checked in `DRUG_NAME`; missing fractions about 0.1555 for three fitted columns and about 0.7425 for the log-transformed concentration column; `data_version: unknown`; concentration and area-under-curve units and normalization conventions not stated in the supplied material. Permitted outputs: absence statements, per-dataset provenance separation. Forbidden: any criterion value, cross-dataset numeric comparison, imputation, response modelling, or treating similar-class compounds present in the table as selected comparators. Unmet prerequisite: the upstream data dictionary and release notes (project download and help pages returned HTTP 410 on 12 October 2026).

**P07post expression matrix (`supporting_data/P07post/`).** MatrixMarket integer matrix 38,349 × 14,440 with 21,037,146 stored entries; feature file 38,349 rows; barcode file 14,440 rows; header names the processing software release and format version. Limits: labelled post-treatment only; no matched pre-treatment sample; no sample or cell metadata; barcode count not a verified count of high-quality cells. The adapter emits `comparison_possible: false` for any before-after contrast plus a `required_inputs_manifest` (matched baseline, quality-control parameters, annotation, feature-identifier convention). Forbidden: any treatment-effect statement, any expression value as a criterion value, any per-candidate value.

## 5. Per-dimension evidence and tool mapping (interface level; no thresholds)

| Dimension | Capabilities and providers | Measured or predicted | Units carried as reported | Stays an expert dependency |
|---|---|---|---|---|
| Target coverage (five targets) | `interaction_evidence_lookup`: Guide to PHARMACOLOGY, ChEMBL, BindingDB; optional `interaction_estimate`: Boltz-2, CDES | curated measurements and model predictions are never merged into one cell | affinity constants in nanomolar or micromolar; negative-log parameters (dimensionless); class probability in [0, 1]; Boltz-2 value as log10(IC50 in micromolar) | assay comparability across records; species and isoform relevance; whether engagement of all five targets by one agent is the right requirement; free versus total concentration |
| Oral bioavailability | `property_estimate`: RDKit descriptors, ADMET-AI endpoints; `literature_retrieval`/`document_reading`: Europe PMC, E-utilities for published pharmacokinetics | descriptors `derived`; model endpoints `predicted`; published values `measured` | bioavailable fraction in percent; permeability in 10⁻⁶ cm/s; partition coefficients dimensionless; polar surface area in Å²; solubility in log molar | formulation and dose dependence; species-to-human extrapolation; whether a classification output is actionable |
| Metabolic stability | `property_estimate`: ADMET-AI enzyme interaction endpoints; literature tools; some ChEMBL records | model endpoints `predicted`; literature values `measured` | intrinsic clearance in µL/min/mg protein or mL/min/kg; half-life in hours; fraction remaining in percent; inhibition and substrate endpoints as class probability | which enzyme interactions matter for the intended regimen; in vitro to in vivo extrapolation; interaction risk in combination |
| Toxicological safety | `property_estimate`: ADMET-AI cardiac, mutagenicity, hepatic, acute endpoints; literature and label documents via literature tools | model endpoints `predicted`; published and label data `measured` or observed | channel inhibition in micromolar or class probability; acute toxicity on the source's dose convention; binary liability endpoints as class probability; clinical event frequency in percent | severity and reversibility weighting; population relevance; manageability of a predicted liability; all risk–benefit judgement |

Cross-cutting rules: a value whose unit is `unknown` may be stored and displayed but never consumed by the Per-Candidate Assessor; the four dimensions remain separate ledgers; a criterion's `acceptable_value_sources` decides whether a predicted value can ever satisfy it, and a mismatch yields `unknown`.

## 6. Core-provided capabilities

- **`rule_evaluation`.** The Per-Candidate Assessor (C11) applies confirmed rule versions deterministically; it is a core capability, not an external tool, and its "tool contract" is the rule record itself. Its outputs are assessment and reason records, never ledger claims.
- **Identity Service.** Core record driven by adapter schemes (design Section 8.2), backed by the `identity_resolution` providers above; `identity_link_basis` and `identity_review_state` on every join.

## 7. Agent-infrastructure references (patterns, not dependencies)

These repositories were cloned read-only and inspected by Workstream 7 (`agent_reports/reference_harness_inspection.md`); none is a runtime dependency of the design.

| Reference | Repository, commit, license | Pattern contributed | Verdict |
|---|---|---|---|
| Agentic Doping | github.com/YWDDLiang/Agentic-Doping, snapshot `0007ad10` (tip of `cloud_deployment`, 2026-08-12); `main` `7cdf6591` | bounded proposal/review loop with `completed/killed/exhausted`; deterministic critic plus gate; citation cross-check with downgrade-only calibration; append-only ledger; scoped memory; post-run reflection with honest skip; Anthropic tool loop; prompt-inclusion audit | reuse as pattern / adapt per `audit_report.md` §4; avoid the disposition remap, the one-shot bridge, count-based skills, upload-as-top-evidence, and ETA over changing denominators |
| DeepSeek Harness | github.com/deepseek-ai/deepseek-harness, `d7432673`, MIT, developer preview | typed event taxonomy `{type, seq, time, data}`; durable `tool/call`–`tool/result` with synthetic results for unanswered calls; crashed turn closed not truncated; pure-fold projections; tool contract with output schema, cancellation, timeout; goal `blocked` with typed reason | adopt the patterns for C1, C13, C15; avoid its two-value agent status as user-facing vocabulary |
| ARIS | github.com/wanshuiyin/Auto-claude-code-research-in-sleep, `26b95cfa`, MIT; paper arXiv 2605.03042 | file-paths-only reviewer input and cross-family rule; Type-A execution gates versus Type-B quality gates; `done` versus `accepted` requiring a verdict id and non-same-family reviewer; deterministic evidence pre-check ("verified is not correct"); verdicts computed by code; stall ladder on zero new findings | adopt for C7, C15, C18; adapt the stall ladder as `no_actionable_step`; avoid treating a single AI-score trajectory as improvement evidence |
| Darwin Gödel Machine | github.com/jennyzzt/dgm, `a565fd2d`, Apache-2.0; arXiv 2505.22954, ICLR 2026 | never-delete archive; staged evaluation budgets; explicit noise leeway; failure-class-directed proposals | adopt and adapt for C19/C20; avoid selection and reporting on the same sets and the hidden-detector bypass it documents |
| hsi (Hierarchical Self-Improvement) | github.com/TailinZhou/hsi, `97a022b9`; README states "MIT", no license file or header found; arXiv 2608.08466 | frozen, non-copied final selector outside the evolvable surface; lower-confidence-bound reward; stratified dev/val/test with fixed seeds and test touched only post-run; per-call usage log by scope; hypothesis with falsification criteria | adopt for C19/C20 and C7 (`falsification_test`); adapt max-of-evaluations ranking to LCB across repeats; avoid in-place overwrite of lessons |
| ACE (Agentic Context Engineering) | github.com/ace-agent/ace, `82709de0`, Apache-2.0; arXiv 2510.04618, ICLR 2026 | identified delta items with helpful/harmful counters; append-only ADD operations; no whole-text regeneration | adopt the operation discipline for C14; adapt grouping deterministic and merge human-reviewed; avoid prompt-text-only token budgets and label-driven branching inside a "no ground truth" mode |
| HGM (Huxley-Gödel Machine) | github.com/metauto-ai/HGM, `013872d9`, Apache-2.0; arXiv 2510.21614, ICLR 2026 oral | clade-level selection over descendant outcomes; incremental one-task measurement; separate post-run evaluation on a different split | adopt separate post-run evaluation; adapt clade selection as a warning for C20 lineage metrics; avoid its absence of cost accounting |
| GEPA | github.com/gepa-ai/gepa, MIT; arXiv 2507.19457, ICLR 2026 oral | reflective prompt mutation driven by a scalar metric plus textual feedback; validation-dominated budget | adopt as a candidate offline optimizer for C19/C20 under the held-out gate; never run inside a screening run; the historical-criteria artifact must be invisible to it |
| ReasoningBank | github.com/google-research/reasoning-bank, Apache-2.0 ("demonstration purposes only"); arXiv 2509.25140, ICLR 2026 | failure-derived lessons as memory items | reference only; its self-judged success labels are the pattern C14 displays as `signal_provenance: model_judgment` |

## 8. Language-model access

Language-model access is provider-agnostic through role resolution: each role (Planner, Proposer, Blind Critic, Escalated Adjudicator, Evidence Retriever, Evaluator judge for process metrics) is bound at run start to a model adapter whose **Model Adapter Capability Record** (design Section 7.6) states `accepts_tool_schemas`, `returns_tool_results_to_model`, `max_tool_iterations`, `structured_output_mode`, `error_feedback_supported`, `verified_by`, `verified_at`, and `verification_state`. The core refuses feedback-dependent protocols unless the record says yes and degrades explicitly otherwise. Interface-level contract tests (echo, error recovery, two-step dependency, iteration cap, idempotency, provenance, conformance) verify each adapter; they do not establish outcome quality. Every exchange records `provider_path` and the model family of each actor so the independence marker can be computed. Cross-family critics are a declared, replaceable dependency; where unavailable the record says `false`.

## 9. What could not be verified

- GDSC primary documentation and data dictionary: every project download and help page tried returned HTTP 410; the Sanger overview page has no column dictionary or explicit license. The dataset contract rests on package inventory metadata; `data_version` is `unknown`.
- Europe PMC REST documentation pages returned HTTP 403 and the REST root 404; endpoint and field facts come from a live schema probe plus search snippets; the "no key required" statement is snippet-level.
- NCBI E-utilities reference chapters returned a reCAPTCHA interstitial; rate limits come from NCBI's own announcement post.
- PubChem PUG REST documentation is client-rendered and returned no body; policy figures are from search results citing it.
- hsi license: README says "MIT" with no license text anywhere in the repository at `97a022b9`.
- CDES: no code, checkpoint, training data, or screening output exists in the package; Section 3 is a contract and prerequisite list, not an assessment of a real backend.
- The manuscript's candidate list and the authors' individual eleven criteria are not in the supplied material.
- Windows support of the locally installed tools (RDKit, ADMET-AI, Boltz-2) was not checked in this phase; nothing was installed or run on Windows. The design records platform support per contract and treats a tool that cannot run on the host as absent (ADR-36, U-14).

## 10. Sources

`agent_reports/tools_and_data.md` (sections 1–7, Findings 1–10, cross-review, contribution record with the URL/fetch table); `agent_reports/reference_harness_inspection.md` (sections 3–5, 6, 8); `agent_reports/mas_architecture.md` (G1, H1, cross-reviews); `agent_reports/current_agent_literature_a.md` (Table A rows S7, S8, S15); `optimized_design.md` Sections 0, 2, 7, 16; coordinator clone records (commit SHAs, licenses, 12 October 2026).
