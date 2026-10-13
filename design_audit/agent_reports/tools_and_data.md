# Workstream 3 — Tools and Data Layer Audit

Design-only report. No implementation code. All source access dates are 12 October 2026 unless stated otherwise.

## Summary

1. The preliminary spine names a **Tool Broker** but gives it no provenance obligation, no absence vocabulary, and no versioning duty; as specified it can dispatch a call and return a value that nobody can later reproduce, invalidate, or attribute.
2. The reference implementation confirms the risk concretely: its provenance record carries only `kind`, `ref`, `at` (`evidence_ledger/models.py:23-27`), so a result cannot be tied to a tool version, parameter set, or data release.
3. Tool contracts there are inline dict literals and per-role dispatch closures (`dual_agent/agent_harness.py:62-117, 531, 623, 897`). Nothing can be swapped, versioned, or audited — which makes "CDES as an optional adapter" structurally impossible under that shape.
4. The single worst behaviour to avoid: human-submitted results are written as top-tier evidence with a perfect score purely because the file write succeeded (`feedback/ingest.py`, `ingest_wetlab`: `evidence_level=E4`, `scores=ScoreBreakdown(experiment=1.0)`, `needs_confirmation` set **only** on failure).
5. Three patterns in the same repo are worth lifting wholesale: tool errors fed back into the next turn instead of aborting (`core/llm_client.py:472-479`); a `needs_other_env` / `skipped` tier status distinct from `failed` (`evaluation_cascade/base.py`, `cascade.py:26-33`); and a required-inputs manifest that states what an absent backend would need (`evaluation_cascade/dft_bridge.py`).
6. A no-CDES route is feasible at interface level from ten public sources, but it is **coverage-limited, not quality-limited**: retrieval can give measured values for well-studied pairs and nothing at all for most of a 3,171-compound universe, so `unknown` will be the most common per-criterion verdict and must be a first-class, non-penalising state.
7. The supplied GDSC and P07post data cannot support any criterion value under their own inventory metadata (no candidate alias in `DRUG_NAME`; no matched pre-treatment sample; units and endpoint meanings undocumented). They enter as `context_only` with machine-enforced refusals, not prose warnings.
8. No model training is needed for v1. One optional later model (evidence extraction from full text) is specified with its data, labels, evaluation, and the reviewer-time gain it must demonstrate.

**Most important recommended change:** replace name-based tool dispatch with a **capability-based tool registry** in which every result is a typed value object carrying `unit`, `value_kind`, `uncertainty`, `data_version`, and a full provenance block, and in which `absent` is a first-class status with a typed `absence_reason` and a required-inputs manifest. This one change is what makes CDES optional rather than load-bearing, makes `missing ≠ failed` enforceable instead of aspirational, and is the precondition for honestly reporting what the no-CDES route did and did not establish.

---

## 1. The reusable tool contract

The core owns the *shape* of a tool interaction; the domain adapter owns the *vocabulary* that fills it; the case configuration owns *preference order* among providers. No pharmacology term appears in any core field name below.

### 1.1 Tool contract (declared once per tool, versioned)

- `tool_id` — stable, adapter-namespaced
- `capability` — the question class answered, from a controlled core list (`identity_resolution`, `interaction_evidence_lookup`, `interaction_estimate`, `property_estimate`, `literature_retrieval`, `document_reading`, `dataset_context_lookup`)
- `contract_version`, `implementation_version`, `upstream_version_source`
- `purpose_statement` — one sentence
- `evidence_kind_produced` — `model_prediction` | `computational_simulation` | `curated_measurement` | `database_entry` | `literature_record` | `derived_identity`
- `claim_strength_ceiling` — the highest value kind any result may carry (`predicted` | `curated` | `measured`); the broker rejects a payload exceeding it
- `input_schema` — per field: name, type, unit, required/optional, allowed values, identity precondition (for example, a resolved structure key rather than a free-text name)
- `output_schema` — per field: name, type, **mandatory** unit, `value_kind`, uncertainty block, source-record reference
- `uncertainty_model` — `none` | `interval` | `stated_sd` | `class_probability` | `rank_only` | `qualitative`; a model's own score is a `class_probability`, never a reliability estimate
- `error_schema`, `absence_schema` — the vocabularies in §1.5
- `determinism` — `deterministic` | `seeded_stochastic` | `nondeterministic` | `external_state_dependent`, plus the fields forming a reproducibility key
- `cost_latency_class` — `interactive` | `short` | `batch` | `offline_human`, plus `quota_cost` and `money_cost_class`
- `rate_limit_declaration` — requests/second, requests/minute, concurrency cap, backoff, whether a key raises the limit
- `prerequisites` — credentials, environment, local data, network egress, hardware, license acceptance
- `license_and_redistribution` — license identifier, redistribution permitted, attribution text, commercial restriction
- `side_effects` — must be `read_only` for every v1 evidence tool
- `human_review_required` — boolean plus triggering conditions
- `deprecation` — `active` | `degraded` | `deprecated` | `withdrawn`, with replacement `tool_id`

### 1.2 Invocation record (one per call)

`invocation_id`, `run_id`, `round_id`, `step_id`, `requesting_actor`, `question_id`, resolved `tool_id` + `contract_version` + `implementation_version`, `normalized_input`, `input_hash`, `requested_at`, `started_at`, `finished_at`, `latency_ms`, `attempt_index`, `retry_of`, `budget_charged`, `cache_hit`, `cache_key`, `cache_written_at`.

### 1.3 Result record

- `status` — `ok` | `partial` | `empty` | `absent` | `failed`; `empty` means the source answered and held no record, `absent` means the tool never ran
- `values[]` — each: `name`, `value`, `unit`, `value_kind` (`measured` | `curated` | `predicted` | `simulated` | `derived` | `missing`), `uncertainty`, `n`, `conditions_ref`, `source_record_ref`
- `data_version` — database release label, checkpoint identifier, or library release
- `determinism_record` — seed and parameters actually used
- `evidence_kind`, `claim_strength_ceiling` — echoed from the contract
- `supports_claim` — **always null from the broker**; only the Evidence Ledger and Per-Candidate Assessor may write a criterion verdict
- `warnings[]`, `truncation_record`, `provenance[]`

### 1.4 Provenance block (the gap this fixes)

`kind`, `upstream_ref` (DOI, accession, URL or file hash), `retrieved_at`, `tool_id`, `contract_version`, `implementation_version`, `data_version`, `parameters_hash`, `invocation_id`, `run_id`, `actor`, `license_id`, `independence_key`.

`independence_key` is what lets the ledger notice that three "sources" repeat one underlying experiment. The brief requires independence markers, and no reference-repo field supports that today.

### 1.5 Error and absence vocabularies

Error classes: `input_invalid`, `identity_unresolved`, `out_of_domain`, `auth_missing`, `auth_rejected`, `rate_limited`, `transient_network`, `upstream_server_error`, `timeout`, `quota_exhausted`, `parse_failed`, `schema_violation`, `environment_missing`, `model_unavailable`, `internal_error` — each with `retryable` and `operator_action`.

Absence reasons: `not_configured`, `not_installed`, `requires_other_environment`, `unreachable`, `unauthorized`, `rate_limited_exhausted`, `out_of_domain`, `identity_unresolved`, `no_record_found`, `budget_exceeded`, `declined_by_policy`.

Every `absent` result also carries a `required_inputs_manifest` — the artifacts that would make the call possible — modelled on the reference repo's `required_dft_inputs` / `runs_no_dft` pattern. Absence is therefore informative: the planner converts `not_configured` into an operator task and `no_record_found` into a genuine evidence gap, while `out_of_domain` closes that route.

### 1.6 Registry, dispatch, retry

- **Registry.** Adapters register contracts; the core never imports a tool module. Resolution is by `(capability, question_kind, required_value_kind)`, never by tool name. A criterion demanding a measured value cannot be matched to a prediction-only provider; the assessor then records `unknown`.
- **Dispatch pre-checks,** in order: input validation, identity precondition, license gate, prerequisite probe, budget and rate-limit token. A failed prerequisite yields `absent`, not `failed` — the distinction the reference code loses.
- **Retry.** Only `retryable` error classes; bounded attempts with exponential backoff and jitter; idempotency by `input_hash`; `retry_of` lineage recorded. A retry is never a new screening round. A per-provider **circuit breaker** marks a provider `degraded` after N consecutive failures, journals a `tool_degraded` event, and falls through to the next provider or records absence.
- **Feedback.** Every result, error and absence becomes a typed `tool_observation` entering the next agent turn with question asked, status, values with units and value kinds, uncertainty, absence reason, and `decision_relevance`. This is the one mechanism the reference repo already gets right and it must be preserved.

### 1.7 How "a successful call does not validate a claim" is encoded

Five structural mechanisms, none relying on prompt wording: (1) `tool_status` and `claim_status` are different fields in different records and the broker cannot write the second; (2) `claim_strength_ceiling` makes it impossible to store a predictor's output as a measurement; (3) the assessor compares the criterion's `required_value_kind` against the evidence record's `value_kind`, and a mismatch yields `unknown` — never `pass`, never `fail`; (4) the leaderboard renders each cell as `measured | curated | predicted | missing` with provenance, so a cell filled by a successful prediction call is visibly not a measurement; (5) `human_scientific_approval` is writable only by the Human Review Queue with a named reviewer, so no agent verdict or software status field can produce it.

## 2. CDES as an optional adapter

CDES is described in the manuscript (text extract lines 100–117, 134–153) as a deep-learning drug–target interaction predictor combining pretrained molecular and protein representations with a cross-attention interaction module, retrained on roughly one million curated interaction pairs, used to screen 3,171 compounds against five targets and yield 140 candidates above a 0.9 probability on all five.

**Contract if present.** Capability `interaction_estimate`. Inputs: resolved compound identity (structure key plus canonical structure string plus source identifier) and resolved target identity (protein accession, sequence version, isoform). Outputs: one interaction probability in [0,1] per compound–target pair, plus `model_version`, `checkpoint_id`, `training_data_version`, `calibration_metadata`, and an `applicability` flag stating whether the pair falls inside the training domain. Evidence kind `model_prediction`; `claim_strength_ceiling: predicted`; `uncertainty_model: class_probability`; `determinism: seeded_stochastic`; `cost_latency_class: batch`; prerequisites: code, checkpoint, GPU environment.

**What it would add.** Uniform coverage of the whole candidate universe. No retrieval route can produce a value for every one of ~15,855 compound–target pairs, so only a model can evaluate the five-target conjunction for every candidate rather than only for the well-studied minority. That is the single capability the no-CDES route cannot replace.

**What it requires that the package does not contain.** Per `04_Source_Inventory_EN.md` and `ARTIFACT_MANIFEST.json` (`scientific_models_run: false`): no source code, no checkpoint, no screening output. Beyond those, before any criterion is allowed to depend on it: the training set with its provenance and licensing, the train/test split, an **overlap check against surufatinib and the five targets** (the case outcome is disclosed, so leakage is a live risk and its absence is not evidence of absence), calibration data that gives the 0.9 cut a meaning, and a stated decision-threshold rationale.

**Absence and failure behaviour.** The registry marks the provider `declared_unavailable`; capability resolution falls through to retrieval and property-estimation providers. Each affected per-criterion record carries `value_kind: missing`, the typed absence reason, and a required-inputs manifest. The candidate verdict is `unknown`; the candidate state is `provisional` or `unassessed` and **never** `rejected` for want of a prediction. The run reaches `completed` with a `tool_coverage` summary per dimension, and the snapshot carries a disclosure field (`interaction_estimate_provider: none`) so no later narrative can imply the model ran. If CDES arrives later it enters as an evidence-refresh run against preserved snapshots, with an agreement check against curated measurements recorded before any criterion depends on it alone.

---

## 3. Researched sources for the no-CDES route

Ten sources, interface level only. Access date for every row: 12 October 2026. Reading depth per URL is recorded in the contribution record.

| # | Source | What it does | Primary URL | Inputs → outputs | License / access constraints | Limitations | Dimension informed | Evidence kind | Workflow entry |
|---|---|---|---|---|---|---|---|---|---|
| 1 | RDKit 2026.09.1 | Structure parsing, normalisation, canonical keys, computed descriptors | rdkit.org/docs/index.html; raw.githubusercontent.com/rdkit/rdkit/master/license.txt | Structure strings / mol files → canonical structure, structure key, computed descriptors | BSD 3-Clause (attribution, no endorsement) | Descriptors are computed properties, not measurements; values are version-sensitive | Oral bioavailability (physicochemical inputs only) | `derived_identity` / computed | Identity normalisation before any lookup |
| 2 | PubChem PUG REST | Resolves names, structures and keys to a compound record | pubchem.ncbi.nlm.nih.gov/docs/programmatic-access | Name, structure string, structure key, compound id → identity record, cross-references | No copyright asserted on aggregated data; depositor records may carry own terms. Policy: ≤5 req/s, ≤400/min, ≤300 s running time/min; synchronous, ≤30 s/call | Aggregator — depositor quality varies; name resolution ambiguous for salts, stereoisomers, brand names | All (identity gate) | `database_entry` | Identity resolution, first step |
| 3 | UniChem | Maps a compound identifier across chemistry resources by standard structure hash | chembl.gitbook.io/unichem | Identifier or structure → identifier set across sources | EMBL-EBI terms; open | Strict structure-hash equality, so salt, tautomer and stereo variants do not unify — silent under-matching | All (identity gate) | `database_entry` | Identity reconciliation, duplicate detection |
| 4 | ChEMBL web services (release 37, May 2026) | Bioactivity records abstracted from primary literature | chembl.gitbook.io/chembl-interface-documentation/web-services; /about; /downloads | Compound / target / assay query → activity records with standardised type, value, unit, assay–target confidence level | CC BY-SA 3.0; release DOIs available | Normalisation is best-effort; confidence levels must be carried, not collapsed; values inherit the original assay's conditions | Target coverage; some metabolic endpoints | `curated_measurement` | Retrieval for a named compound–target pair |
| 5 | BindingDB | Curated protein–small-molecule binding measurements | bindingdb.org/rwd/bind/info.jsp | Compound / target query → affinity constants and thermodynamic parameters with assay references | CC BY 3.0 for BindingDB-curated rows, CC BY-SA 3.0 for ChEMBL-imported rows — two licenses in one response | Heterogeneous assay types; provenance overlaps ChEMBL, so independence must be checked | Target coverage | `curated_measurement` | Second provider; cross-source agreement check |
| 6 | IUPHAR/BPS Guide to PHARMACOLOGY web services | Expert-curated target–ligand interactions with species and reference | guidetopharmacology.org/webServices.jsp | Target / ligand / interaction query → records with affinity parameter type, value, species, action type, reference | ODbL database, CC BY-SA 4.0 content; **API key required**, ~60 req/min | High quality, low coverage; absence of a record is not absence of an interaction | Target coverage | `curated_measurement` | Third provider; preferred where present |
| 7 | Europe PMC REST | Literature search and open-access full-text retrieval | ebi.ac.uk/europepmc/webservices/rest/ (live endpoint probed) | Query → results with source, identifiers, title, journal, year, open-access and in-repository flags, citation count, full-text id list | No key required for the REST service; reuse governed by each article's license | Full text only for the open-access subset; flags must set an honest read depth | All four (carrier of claims) | `literature_record` | Title → abstract → full-text escalation |
| 8 | NCBI E-utilities (PubMed) | Indexed literature search and record fetch | ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/ | Database + query → record identifiers and metadata | 3 req/s without a key, 10/s with one; NCBI usage policy | Abstract-level only; complements rather than replaces source 7 | All four | `database_entry` to literature | Parallel provider, de-duplicated by identifier |
| 9 | ADMET-AI (MIT) over Therapeutics Data Commons datasets | Predicts property endpoints from a structure string | github.com/swansonk14/admet_ai; github.com/mims-harvard/TDC; tdcommons.ai/single_pred_tasks/adme/ and /tox/ | Structure string → per-endpoint predicted value or class probability | Code MIT; most datasets CC BY 4.0, at least one CC BY-NC-SA 4.0 — per-dataset license must be carried | v2 predictions differ from v1, the paper and the web server, so the version must be pinned; several endpoints train on only hundreds of compounds; class probabilities are not calibrated risk | Oral bioavailability, metabolic stability, toxicological safety | `model_prediction` | Property estimation after identity resolution |
| 10 | Boltz-2 (MIT) — optional | Structure-based complex and affinity prediction | github.com/jwohlwend/boltz; boltz.bio/boltz2 | File describing sequences and ligand → predicted structure, `affinity_pred_value` (stated as log10 of IC50 in µM) and `affinity_probability_binary` | MIT, weights for academic and commercial use; GPU strongly recommended | The repo gives the two outputs different intended uses (binder/decoy separation versus affinity comparison); conflating them is a misuse. Interpretation conflict per Finding 9 | Target coverage | `model_prediction` (structure-based) | Optional targeted computation when retrieval leaves a consequential gap |

---

## 4. Per-dimension evidence and tool mapping

No thresholds are proposed anywhere in this table. Units are the units in which values must be *carried*, not criteria.

| Dimension | Candidate source types | Measured or predicted | Typical units as reported | Stays an expert dependency |
|---|---|---|---|---|
| **Target coverage** (sources 4, 5, 6, 10, optional CDES) | Curated bioactivity records; expert-curated interaction tables; structure-based prediction; optional interaction predictor | Both, and they must never be merged into one cell: curated records are `measured`/`curated`; model outputs are `predicted` | Affinity constants in nanomolar or micromolar; negative-log parameters (dimensionless); class probability in [0,1]; Boltz-2 value as log10(IC50/µM) | Whether an assay type is comparable across records; species and isoform relevance; whether engagement of all five targets by one agent is the right requirement at all; free versus total concentration |
| **Oral bioavailability** (sources 1, 9; literature via 7, 8) | Computed physicochemical descriptors; permeability and absorption models; published human or animal pharmacokinetic reports | Descriptors `derived`; model endpoints `predicted`; published pharmacokinetic values `measured` | Bioavailable fraction in percent; permeability in 10⁻⁶ cm/s; partition coefficients dimensionless; polar surface area in Å²; solubility in log molar | Formulation and dose dependence; species-to-human extrapolation; whether a classification output is actionable for the stated objective |
| **Metabolic stability** (source 9; literature via 7, 8; some records in 4) | Enzyme inhibition and substrate models; measured intrinsic clearance and half-life from literature or regulatory documents | Model endpoints `predicted`; literature values `measured` | Intrinsic clearance in µL/min/mg protein or mL/min/kg; half-life in hours; fraction remaining in percent; inhibition and substrate endpoints as class probability | Which enzyme interactions matter for the intended regimen; in vitro to in vivo extrapolation; interaction risk in a combination setting |
| **Toxicological safety** (source 9; literature via 7, 8; label documents) | Cardiac channel, mutagenicity, hepatic injury and acute toxicity models; published safety and label data | Model endpoints `predicted`; published and label data `measured`/`observed` | Channel inhibition in µM or class probability; acute toxicity on the source's own dose convention; binary liability endpoints as class probability; clinical event frequency in percent | Severity and reversibility weighting; population relevance; whether a predicted liability is manageable; all risk–benefit judgement |

Two cross-cutting rules: an endpoint whose unit is unknown may not be used as a criterion value under any dimension; and the four dimensions must remain separate ledgers, because a value that is strong evidence under one dimension is often irrelevant under another.

---

## 5. Adapter input contracts for the supplied datasets

Both are declared `role: context_only`. Both contracts are written entirely from inventory metadata.

**GDSC dose-response table.** Inputs: the twenty declared columns, with identity keys `DATASET` (GDSC1 or GDSC2), `COSMIC_ID`, `DRUG_ID`, `DRUG_NAME`, `BROAD_ID`, `ARXSPAN_ID`. Declared shape: 387,626 rows (268,718 GDSC1, 118,908 GDSC2), 397 distinct non-missing drug-name strings, 989 distinct identifiers. Declared limits the adapter must publish as machine-readable refusals: zero matches for the three candidate aliases checked in `DRUG_NAME`; missing fractions of about 0.1555 for three fitted columns and about 0.7425 for the log-transformed concentration column; `data_version: unknown`; concentration and area-under-curve units and normalisation conventions **not stated anywhere in the supplied material**. Permitted outputs: absence statements and per-dataset provenance separation. Forbidden: any criterion value, cross-dataset numeric comparison, imputation, response model, or treatment of the similar-class compounds present in the table as selected comparators. Unmet prerequisite: the upstream data dictionary and release notes, which could not be retrieved (Finding 7).

**P07post expression matrix.** Inputs: a MatrixMarket integer matrix of 38,349 × 14,440 with 21,037,146 stored entries, a feature file of 38,349 rows, a barcode file of 14,440 rows, header metadata naming the processing software release and format version. Limits: the sample is labelled post-treatment only; no matched pre-treatment sample exists in the archive; no sample or cell metadata is supplied; the barcode count is not a verified count of high-quality cells. The adapter emits `comparison_possible: false` for any before-after contrast plus a required-inputs manifest naming the missing matched baseline, quality-control parameters, annotation and feature-identifier convention. Forbidden: any treatment-effect statement, any expression value used as a criterion, any per-candidate value.

---

## 6. Human-supplied result intake

Three intake modes — inline text, local path, uploaded file — converge on one `submission` record. The governing rule: **a submission is stored as a claim with provenance, never as a criterion value.**

- *Identity and storage:* `submission_id`, `submitted_by`, `submitted_at`, `intake_mode`, `original_filename`, `content_hash`, `stored_uri`, `parser_used`, `parser_version`, `asserted_subject` (candidate, criterion, target), `identity_resolution_status` (`resolved`, `ambiguous`, `unresolved` — the same identity rules tools use), `claimed_value_kind`.
- *Required provenance:* who performed the work, when, at which laboratory, protocol or standard-operating-procedure reference, instrument or model identity, data version or batch, and any prior publication or internal report.
- *Required experimental context:* assay name, system (biochemical, cell, animal, human), species, sample size, replicates, controls present (positive, negative, vehicle), concentration or dose range, incubation time, temperature, matrix, readout, normalisation, statistics applied.
- *Units:* mandatory and explicit per value. A submission without a unit is `incomplete` and is never given a default.
- *Negative results are first class:* a `direction` field with values `effect_observed`, `no_effect_observed`, `below_limit_of_detection`, `assay_failed`, `inconclusive`, plus detection or quantification limits and a statement of discriminating power. Negative submissions are accepted, counted and visible in conflict sets — a system that ingests only positives manufactures a biased ledger.

Lifecycle: `received` → `parsed` (or `parse_failed`, retained with `needs_confirmation` rather than dropped) → `identity_resolved` → `review_pending` → one of `accepted_as_evidence`, `accepted_with_reservations`, `rejected`, `withdrawn`. The transition into evidence requires a Human Review Queue decision by a named reviewer **other than the submitter** whenever it would change a candidate's state, and the ledger stores reviewer identity, decision, reason, assigned evidence kind and assigned claim strength. No evidence level is assigned on write. Acceptance marks affected per-criterion records stale and schedules reassessment; it never rewrites an earlier snapshot.

---

## 7. Resources and the no-additional-training baseline

**Compute.** No accelerator in the baseline: retrieval is network-bound and property estimation is CPU-feasible at the scale of a few thousand structures. The optional structure-based predictor is the only GPU dependency, which is part of why it stays optional.

**Storage.** Small and cache-dominated: journal and ledger, cached API responses, retrieved open-access full texts, the supplied data files, the submission artifact store. Every cache entry records `retrieved_at` and a staleness policy, because a cached answer is a claim about a past release.

**API access.** No key: Europe PMC, ChEMBL, BindingDB, PubChem (policy-limited). Key recommended: E-utilities (3/s rising to 10/s). Key required: Guide to PHARMACOLOGY (~60/min). Language-model access stays provider-agnostic through role resolution, which the reference repo already demonstrates.

**Model access.** A pinned ADMET-AI release with its dataset licenses; optionally the structure-based predictor weights (MIT). No interaction-predictor checkpoint exists in the package.

**Expert input** is the scarcest resource and the real rate limiter: criterion relevance, assay comparability, species extrapolation, intake of the authors' historical criterion list, and sign-off on every submission that would change a candidate's state.

**No-additional-training baseline.** All four dimensions are served by retrieval plus published models at fixed, recorded versions. Nothing is trained, fine-tuned or calibrated in v1; evidence strength derives from source kind and provenance, never from a model's own score; missing values stay `unknown`. This is also the comparison arm for any later model.

**One optional later model, in the reference repo's deferred style.** Task: extract `(endpoint, value, unit, conditions, direction)` tuples from retrieved full text, with conflict detection against existing ledger records. Data: paragraphs of already-retrieved open-access full texts. Labels: reviewer-verified extractions from the Human Review Queue, admitted through a ledger gate that accepts only reviewer-accepted records — the same gate the reference repo applies to its training buffer. Method: a calibrated verifier over language-model extractions first; supervised fine-tuning of a small extraction model only if that is insufficient. Compute: modest, single-accelerator. Evaluation: held-out reviewer-verified extractions scored on exact agreement of value **and** unit plus conflict-detection recall, against the untrained baseline at matched budget. Value must be shown as reviewer-minutes per accepted evidence record at equal or better accuracy, not as extraction volume. Gate: a stated minimum of reviewer-verified records must exist first.

---

## Findings

### Finding 1 — The Tool Broker carries no provenance obligation, and the reference provenance record could not carry one

- **Issue.** The spine's broker has no duty to emit tool version, parameters, data version or run identity, and the reference provenance record has exactly three fields — so a stored result cannot be reproduced, attributed, or invalidated when a tool version changes.
- **Source / location.** Coordinator brief §5 item 4; `Agentic-Doping-snapshot/src/agentic_doping/evidence_ledger/models.py:23-27` (`Provenance`: `kind`, `ref`, `at`), commit `0007ad10`.
- **Importance.** High — the audit trail the acceptance target depends on cannot be reconstructed, and a tool upgrade silently changes conclusions.
- **Recommended change.** Make the thirteen-field provenance block of §1.4 mandatory on every Evidence Ledger write, with the Tool Broker refusing results whose provenance is incomplete.
- **Tradeoff.** Some services expose no version information, so those fields will sometimes read `unknown` — honest but noisier.
- **Unresolved uncertainty.** Whether a daily snapshot label is an acceptable `data_version` substitute for services with no per-request release identifier.

### Finding 2 — Absence is not a status in the spine, and the reference adapter collapses four distinct absences into one null

- **Issue.** The external-integration adapter returns `None` when disabled, not installed, endpoint-less, or given empty input, while a remote HTTP failure raises instead, so "no result" is indistinguishable from "tool switched off" — which breaks the test for whether another round is useful.
- **Source / location.** `integrations/crysllm_vri.py` (`enabled()`, `available()`, `score_candidate()`, `_score_remote`), commit `0007ad10`; coordinator brief §4 rule semantics.
- **Importance.** High — `missing ≠ failed` is a stated requirement and is unenforceable without a typed absence vocabulary.
- **Recommended change.** Add the `absence_reason` enumeration and `required_inputs_manifest` of §1.5 to the broker result contract, generalising the repo's own `needs_other_env` status and `required_dft_inputs` manifest.
- **Tradeoff.** More states for the planner and the UI to handle.
- **Unresolved uncertainty.** Whether exhausted rate limits are an absence or a run-scoped retryable error — they behave as both depending on budget.

### Finding 3 — A submitted result becomes top-tier evidence because the file write succeeded

- **Issue.** Wet-lab intake writes a ledger record at the highest evidence level with a perfect sub-score on success and flags `needs_confirmation` only on failure, with no units, conditions, reviewer or negative-result fields on that path.
- **Source / location.** `feedback/ingest.py`, `ingest_wetlab` (`evidence_level=EvidenceLevel.E4`, `scores=ScoreBreakdown(experiment=1.0)`, `provenance=[Provenance(kind="wetlab", ref="user_upload", ...)]`), commit `0007ad10`.
- **Importance.** High — it is the shortest path from an unreviewed upload to a changed leaderboard position, and the governing prompt forbids exactly this.
- **Recommended change.** Replace it with the §6 submission lifecycle: no evidence level on write, mandatory units and conditions, promotion only by a named reviewer who is not the submitter.
- **Tradeoff.** Submitting stops being one step and reviewer availability becomes a visible bottleneck — the honest state of affairs.
- **Unresolved uncertainty.** Whether any submission class may auto-promote inside a private working copy that never reaches a shared leaderboard.

### Finding 4 — No tool registry: contracts are literals and dispatch is a closure, so no backend can be optional

- **Issue.** Tool schemas are inline dict literals, dispatch is a per-role closure, and availability is expressed by filtering a list by tool name — nothing is versioned, nothing declares evidence kind or cost class, and no capability indirection exists, so an optional CDES adapter has nowhere to plug in.
- **Source / location.** `dual_agent/agent_harness.py:62-117`, `:531`, `:623`, `:897`, `:593-594`, `:930-931`, `:1039-1040`, commit `0007ad10`.
- **Importance.** High — this is the structural blocker for the optional-backend requirement.
- **Recommended change.** Adopt the capability-based registry of §1.6, resolving by `(capability, question_kind, required_value_kind)` with a case-configured preference order and one declared contract per tool.
- **Tradeoff.** An indirection layer to maintain; adding a small tool costs more.
- **Unresolved uncertainty.** Whether preference order may adapt from observed coverage, which edges toward an unevaluated self-improvement claim.

### Finding 5 — The core/adapter boundary does not say who owns units, identity and value kind

- **Issue.** The spine assigns the core "tool brokering and result feedback" and the adapter "evidence-source and tool adapters" but never assigns ownership of units, identity resolution and measured-versus-predicted marking; in the reference repo domain semantics have already drifted into `core/`.
- **Source / location.** Coordinator brief §3 layer table; `core/property_semantics.py` (13.6 KB of domain property semantics inside `core/`), commit `0007ad10`.
- **Importance.** Medium-high — ambiguous ownership is how layer separation erodes during implementation.
- **Recommended change.** The core owns the *shape* and enforces unit, `value_kind`, uncertainty and provenance on every value; the adapter owns the *vocabulary* of legal units, endpoints and identity rules; the case configuration owns provider preference and required value kinds.
- **Tradeoff.** The core must reject payloads on formal grounds while knowing nothing of their meaning, producing occasional unhelpful refusals.
- **Unresolved uncertainty.** Where unit conversion belongs — adapter-side conversion loses the as-reported value unless both are stored.

### Finding 6 — Tool output re-enters the model context unvalidated and unbounded

- **Issue.** Whatever dispatch returns is serialised straight into the next turn and an exception becomes a free-text type-name-plus-message string, with no output-schema validation, size policy or truncation record.
- **Source / location.** `core/llm_client.py:472-479`; same construct in packaged excerpt `agentic_doping_reference/excerpts/04_tool_feedback.py.txt`.
- **Importance.** Medium — the feedback mechanism is right and worth keeping; the missing validation is what makes it unreliable.
- **Recommended change.** Interpose the `tool_observation` projection of §1.6 with required fields, output-schema validation before feedback, and an explicit `truncation_record`.
- **Tradeoff.** A rejected malformed payload loses information, so the rejection must itself be fed back as an error observation.
- **Unresolved uncertainty.** How much of a large retrieval result to surface before it crowds out reasoning.
- *Revised after cross-review:* my claim that "the feedback mechanism is right" holds only for the Anthropic path — WS2 D1 shows the bridge path dispatches tools without returning results to the model while reporting itself tool-capable, so feedback must be capability-gated before it can be validated.

### Finding 7 — Unit ambiguity is already stored as a comment, and the supplied table would repeat it

- **Issue.** A stored numeric field is documented as being in the source's own convention while the method field that would disambiguate it is marked reserved and unused — the same failure the supplied dose-response table pre-loads, its concentration units, area-under-curve normalisation and endpoint meanings being undocumented in the package.
- **Source / location.** `dft_data/store.py:110-135`; `04_Source_Inventory_EN.md` optional-datasets table; `ARTIFACT_MANIFEST.json` `read_only_data_inspection`.
- **Importance.** High — a unit-ambiguous number reaching a criterion produces a confident wrong verdict.
- **Recommended change.** A machine-enforced unit gate: a value whose `unit` is `unknown` may be stored and displayed but never consumed by the assessor, and the dataset adapter stays `role: context_only` until the upstream dictionary arrives.
- **Tradeoff.** Usable-looking data sits idle until documentation arrives.
- **Unresolved uncertainty.** The dictionary could not be retrieved (HTTP 410 on the project's download pages, 12 October 2026), so whether it is publicly available elsewhere is unestablished.

### Finding 8 — The no-CDES route is coverage-limited, and the design must say so numerically

- **Issue.** Retrieval yields values for well-studied pairs and nothing for the rest, so at the manuscript's stated scale `unknown` will be the dominant per-criterion verdict, and a design that does not report coverage will look like a screen when it is a lookup over a small annotated subset.
- **Source / location.** Manuscript text extract lines 134-146; source table rows 4, 5, 6 above.
- **Importance.** High — it determines whether the eventual case report can be stated honestly.
- **Recommended change.** Give every leaderboard snapshot a per-dimension `tool_coverage` block (candidates with a measured value, with prediction only, with nothing, and the provider behind each), keeping abstention and an empty recommended set valid.
- **Tradeoff.** The coverage block will make the no-CDES route look weak beside a model that scores everything — accurately.
- **Unresolved uncertainty.** Whether the candidate universe can be reconstructed from public sources at all, since the package contains no compound list.

### Finding 9 — The obvious optional affinity predictor is the one the manuscript names as its comparator

- **Issue.** Boltz-2 is the best-documented open structure-based affinity predictor for the optional slot, and the manuscript cites Boltz-2 as the model CDES produced better discrimination than — putting a claim and its own counter-evidence inside one pipeline.
- **Source / location.** Manuscript text extract lines 114-117; github.com/jwohlwend/boltz and boltz.bio/boltz2, accessed 12 October 2026.
- **Importance.** Medium — it does not block the design, but an unremarked collision would damage the rebuttal.
- **Recommended change.** Admit it as one optional `interaction_estimate` provider, keep its two outputs distinct per its own documentation, record the collision in the case configuration, and prohibit any inference from it about CDES's relative merit.
- **Tradeoff.** Declaring the collision invites the question of why the comparator is now in use; silence would be worse.
- **Unresolved uncertainty.** Whether the manuscript's comparison can be re-examined at all without the CDES checkpoint — on this package it cannot.

### Finding 10 — Retry, round and provider health are conflated

- **Issue.** Retry sits inside the model call with a fixed attempt count plus a separate truncation re-loop, and no per-provider health state exists, so a persistently failing tool is retried indefinitely across steps while the shared vocabulary requires retry to stay distinct from a round.
- **Source / location.** `core/llm_client.py:226-246`, `:167-193`, `:451-455`; coordinator brief §4 "Units of work".
- **Importance.** Medium — it distorts cost accounting and the repeated-failure stopping criterion.
- **Recommended change.** Move retry into the Tool Broker, bound it by error class, add a per-provider circuit breaker with a `degraded` state and a journalled `tool_degraded` event, and record `retry_of` lineage.
- **Tradeoff.** A breaker may trip during a transient outage and reduce coverage for that run; the event record makes that visible and re-runnable.
- **Unresolved uncertainty.** Breaker thresholds cannot be set without observed failure rates.
- *Revised after cross-review:* I placed the whole retry budget in the Tool Broker; I now hold that the broker owns retry *policy* while the retry *allowance* belongs to WS2's Plan step budget (B1) and Cost Accountant, per cross-review conflict (v).

---

## Cross-review of mas_architecture.md

### 1. Agreements

- **A1/A2** — deterministic adjudication as default with the LLM arbiter as configuration only, and independence declared as enforced mechanisms (their `check_kind` list consumes my `independence_key`, §1.4).
- **C2** — every bounded loop returns a `LoopOutcome`; `budget_exhausted` never maps to acceptance.
- **D1** — the one-shot bridge path dispatches tools without returning results while advertising itself tool-capable.
- **D2** — step-level failure isolation; no candidate leaves a round without a decision state and a per-criterion row.
- **F1** — `support_basis` and `review_state` as independent axes, `approved` only via a human action record.
- **H1/H2/G1/I1** — redesign the E0–E4 ladder; a State Registry so no label implies unearned admission; enforced import direction; an explicit statement of what the core must never own.

### 2. Objections

**Objection 1 (A3, Tool result payload).** It has no `data_version`, `implementation_version`, `parameters_hash` or determinism record, so a result cannot be reproduced or invalidated; and one payload-level `units` field fails when a call returns several values in different units. Evidence: ADMET-AI's maintainers state v2 predictions do not match v1; ChEMBL ships numbered releases (37, May 2026) with release DOIs; the reference repo's three-field `Provenance` (`models.py:23-27`) is this gap already realised. **Alternative:** use my §1.3 `values[]` plus the §1.4 provenance block as the Tool result payload, leaving their envelope untouched.

**Objection 2 (A3 states, D2).** Tool request states omit `empty` and `absent`. Evidence: the reference external adapter returns `None` for four distinct causes (`integrations/crysllm_vri.py`), and six of my ten sources answer "no record" while healthy. Their own C3 rule cannot be applied if "asked, no record exists" is indistinguishable from "never asked, provider unconfigured". **Alternative:** add both as terminal states carrying my `absence_reason` enumeration and `required_inputs_manifest` (§1.5).

**Objection 3 (D1, contract tests as the gate).** `verified_by`/`verified_at` is a one-time attestation about a *model adapter*; no equivalent exists for *tool providers*, which change underneath a running system — on 12 October 2026 Guide to PHARMACOLOGY now required an API key and the dose-response portal returned HTTP 410. **Alternative:** keep their record for model adapters; add broker-owned provider health (`active | degraded | unavailable`) driven by the breaker, and let a stale `verified_at` downgrade `returns_tool_results_to_model` to `unknown`.

### 3. Interface conflicts and resolutions

**(i) Artifact Envelope (A3) versus my call records (§1.1–1.4).** Theirs is per artifact, mine per call. Resolution: the envelope wins on identity and lineage; my §1.2 becomes the Tool request payload (their `idempotency_key` = my `input_hash`) and §1.3–1.4 the Tool result payload, both held in their Artifact Contract Registry (I1 ii). I drop a separate `invocation_id` where `artifact_id` identifies the call, keeping `request_id` + `attempt_no` as retry lineage. My §1.1 contract is adapter-registered configuration, not an artifact.

**(ii) Capability Record (D1) versus my pre-checks and breaker (§1.6, Finding 10).** Two objects at different layers: the Capability Record governs LLM providers and gates feedback-dependent protocols; Tool Provider Health governs evidence tools and is observed at dispatch. Dispatch reads both. My prerequisite probe moves from test time to pre-dispatch, because its result is `absent`, not a test failure.

**(iii) Run Binding and ports (G1) versus ownership of units, identity, value kind (Finding 5).** Compatible; mine refines theirs. The adapter *declares* the vocabulary through the Tool Contracts port; the core *enforces* structural presence, rejecting payloads lacking `unit` or `value_kind`; the Run Binding gains `provider_preference[]` and `required_value_kind_by_criterion`. Their identity uncertainty resolves their way — a core identity service on adapter-supplied schemes — with `identity_resolution_status` on every evidence join, since my sources disagree on salt, tautomer and stereo forms.

**(iv) `run_degradation[]` (D2) versus my absence vocabulary.** Layering, not conflict: absence records are call-scoped automatic evidence; a degradation entry is the run-level roll-up emitted when a declared capability is unavailable for a whole run, and only those carry `approved_by`, so nobody approves each missing lookup. Their cell reason `measurement_unavailable` should be the typed `absence_reason`.

**(v) Where the tool retry budget lives.** Split allowance from policy: the Plan step budget owns the allowance (`tool_retries` is already in their B1 list) and their Cost Accountant charges it; the broker owns retryable error classes, backoff, idempotency and the breaker, requesting a retry token per attempt. Exhaustion surfaces as a step-level `LoopOutcome` with `termination_reason = budget_exhausted`, and retries stay out of the round count.

### 4. Dependencies

My schemas need their Artifact Contract Registry and State Registry as a home. Their C3 register needs my `absence_reason` to classify a gap; their D2 cells need my `unit`/`value_kind` gate; their E2 fingerprint must include `data_version` and `implementation_version`, or reuse will serve results from a superseded release; their Budget Accountant needs my `cost_latency_class` and `quota_cost`.

### 5. Resolution summary

| Topic | My position | WS2 position | Proposed resolution | Confidence |
|---|---|---|---|---|
| Result schema | Per-value units, 13-field provenance | Payload-level `units`, no version fields | My payload inside their envelope | High |
| Absence | Typed reason + required-inputs manifest | No `absent`/`empty` state | Add both states with my enumeration | High |
| Capability gating | Observed provider health + breaker | Declared record, contract-tested | Two objects, both read at dispatch | High |
| Tool contract as artifact | Registered configuration | Implied artifact kind | Registry configuration, not run artifact | Medium |
| Units / identity / value kind | Core enforces shape | Adapter ports declare all | Both, plus two Run Binding fields | High |
| Degradation record | Call-scoped, automatic | Run-scoped, human-approved | Absence as evidence, degradation as roll-up | Medium-high |
| Retry budget | Tool Broker | Plan step budget | Allowance in plan, policy in broker | High |

---

## Contribution record

**Agent identity.** Workstream 3, Tools and Data Auditor — a subagent of the coordinating agent for the MAS architecture audit, running as Claude Fable 5.1 in Claude Code on the audit host. Sole output file: `/home/yiwei3_duke/anny/mas/design_audit/agent_reports/tools_and_data.md`. Scratch directory used only for timestamps.

**Start and end.** Main report: started 2026-10-12T13:06:12Z, first complete draft 13:24Z, length trimming to 13:52Z. Cross-review wave: 2026-10-12T17:00Z to 17:20Z. Total two working sessions on one assignment.

**Cross-review wave.** Assigned by the coordinator after the main report was accepted at its then-current length (the coordinator confirmed the 5,000-word figure was a soft bound and instructed no further trimming). Peer report read: `/home/yiwei3_duke/anny/mas/design_audit/agent_reports/mas_architecture.md` (Workstream 2, MAS Architecture and Reuse), 6,028 words, dated 2026-10-12T13:27Z — **read in full**, all sections A1 through I1 plus its contribution record. No other peer report was read, and the peer file was not modified. The cross-review section raises three objections (WS2 A3 result-payload provenance, A3/D2 missing absence states, D1 one-time capability attestation) and proposes five interface resolutions. Two of my own findings carry a `Revised after cross-review:` line (Finding 6 on which provider paths actually return tool results, Finding 10 on splitting retry allowance from retry policy); no other earlier text was altered during this wave.

**Note on interrupted attempts.** Two separate automated safety-classifier interruptions occurred during this assignment: one at the very start, before any file was written or repository inspection completed, and one during the cross-review wave before the peer report had been read. In both cases no withheld content was reused and the work was redone from the beginning. A third interruption of the earlier session was a usage limit during length trimming, not a classifier event. No content from that attempt was reused. The work recorded below was performed from the beginning in a second pass, and no reference repository or package file was modified at any point.

**Files read (absolute paths).**

- `/home/yiwei3_duke/anny/mas/design_audit/agent_reports/00_coordinator_brief.md` — full text
- `/home/yiwei3_duke/anny/mas/MAS_MultiAgent_Design_Audit_EN_20261012/START_HERE_Audit_and_Optimize_Prompt_EN.md` — preamble and sections 1, 4 (with 4.1–4.3), 6 (including the mandatory-literature subsection) and the head of 7; sections 2, 3, 5 not read
- `/home/yiwei3_duke/anny/mas/MAS_MultiAgent_Design_Audit_EN_20261012/Project_Brief_EN.md` — sections 3, 7, 8, 9 (full, including the deliverables table rows for `tools.md` and `resources.md`)
- `/home/yiwei3_duke/anny/mas/MAS_MultiAgent_Design_Audit_EN_20261012/04_Source_Inventory_EN.md` — full text
- `/home/yiwei3_duke/anny/mas/MAS_MultiAgent_Design_Audit_EN_20261012/ARTIFACT_MANIFEST.json` — key list and the complete `read_only_data_inspection` block
- `/home/yiwei3_duke/anny/mas/MAS_MultiAgent_Design_Audit_EN_20261012/agentic_doping_reference/excerpts/04_tool_feedback.py.txt` — full text
- `/home/yiwei3_duke/anny/mas/MAS_MultiAgent_Design_Audit_EN_20261012/agentic_doping_reference/excerpts/11_deferred_learning.py.txt` — full text
- `/tmp/claude-1010/-home-yiwei3-duke-anny-mas/0ea0f6b6-dad0-4a42-b565-31a249e2401a/scratchpad/pdf_text/Manuscript_TME_TLS_Ovarian_Cancer.txt` — lines 100-175 (the predictor description and the three criterion dimensions) and lines 213-338, which the assigned 220-345 window resolved to; the biology beyond the screening description was not analysed and no biological conclusion is drawn in this report

**Repository inspected (read-only, no modifications).** `/home/yiwei3_duke/anny/reference_repos/Agentic-Doping-snapshot/`, commit `0007ad10`, under `src/agentic_doping/`:

- `core/llm_client.py` — structure mapped by symbol grep; lines 139-200, 226-250, 342-412, 413-489 read in full
- `core/` — directory listing; `property_semantics.py` noted by name and size only, not read
- `dual_agent/agent_harness.py` — tool-schema and dispatch sites located by grep (lines 62-117, 531, 593-594, 623, 795, 897, 927-931, 1036-1040); file not read in full
- `evaluation_cascade/base.py` — full text; `cascade.py` — control-flow grep only; `dft_bridge.py` — full text
- `feedback/ingest.py` — full text
- `evidence_ledger/enums.py` — full text; `models.py` — lines 1-120
- `dft_data/__init__.py` — full text; `match.py` — lines 1-45; `store.py` — lines 110-155 plus symbol grep; `analyze.py` — symbol grep only; `parse.py`, `report.py`, `leaderboard.py`, `structure_cache.py`, `structure_worker.py` — not read
- `integrations/crysllm_vri.py` — full text

No commits were made and no git state was changed by this workstream.

**Web searches run (all 12 October 2026).**

1. "PubChem PUG REST usage policy request throttling five requests per second documentation"
2. "Boltz-2 binding affinity prediction open source repository license MIT"
3. "Europe PMC RESTful Web Service documentation search fullTextXML endpoint parameters terms of use"
4. "PubChem data license 'free to use' depositor-supplied license statement site policies"
5. "GDSC Genomics of Drug Sensitivity in Cancer current release downloads portal 2026 dose response fitted data"

**URLs fetched, with reading depth (all 12 October 2026).**

| URL | Depth / outcome |
|---|---|
| https://www.rdkit.org/docs/index.html | Index page only; gave release 2026.09.1, no license text |
| https://raw.githubusercontent.com/rdkit/rdkit/master/license.txt | Full text — BSD 3-Clause confirmed |
| https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest | **Failed** — page returned title only (client-rendered); policy facts taken from search 1 instead |
| https://chembl.gitbook.io/chembl-interface-documentation/web-services | Landing page only; pointed to sub-pages |
| https://chembl.gitbook.io/chembl-interface-documentation/downloads | Full page — release 37 (May 2026), formats |
| https://chembl.gitbook.io/chembl-interface-documentation/about | Full page — CC BY-SA 3.0, normalisation and assay-confidence statements |
| https://chembl.gitbook.io/unichem | Full page — scope, access, structure-hash matching |
| https://europepmc.org/RestfulWebService | **Failed** — HTTP 403 |
| https://europepmc.org/Help | **Failed** — HTTP 403 |
| https://www.ebi.ac.uk/europepmc/webservices/rest/ | **Failed** — HTTP 404 |
| https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=…&format=json&pageSize=1 | Live endpoint probed for **response-schema fields only**; article content deliberately not summarised |
| https://www.ncbi.nlm.nih.gov/books/NBK25501/ | **Failed** — reCAPTCHA interstitial |
| https://ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/ | Full page — 3/s versus 10/s rate limits and key policy |
| https://www.bindingdb.org/rwd/bind/info.jsp | Full page — measurement types, scale, access, dual licensing |
| https://www.guidetopharmacology.org/webServices.jsp | Full page — endpoints, API key, ~60/min, ODbL and CC BY-SA 4.0 |
| https://github.com/swansonk14/admet_ai | README — purpose, TDC basis, MIT license, v1/v2 divergence caveat |
| https://github.com/mims-harvard/TDC | README — scope, MIT code license, per-dataset licenses, Dataverse hosting |
| https://tdcommons.ai/single_pred_tasks/adme/ | Full listing — endpoints, task types, units, sizes, licenses |
| https://tdcommons.ai/single_pred_tasks/tox/ | Full listing — endpoints, task types, labels, sizes, licenses |
| https://github.com/jwohlwend/boltz | README — license, input form, the two affinity outputs and their stated distinct uses, hardware notes |
| https://www.cancerrxgene.org/downloads/bulk_download | **Failed** — HTTP 410 |
| https://www.cancerrxgene.org/downloads | **Failed** — HTTP 410 |
| https://www.cancerrxgene.org/help | **Failed** — HTTP 410 |
| https://cancerrxgene.org/downloads/bulk_download | **Failed** — HTTP 410 |
| https://www.sanger.ac.uk/tool/gdsc-genomics-drug-sensitivity-cancer/ | Full page — resource scope and open-access statement; no column dictionary or explicit license |
| https://boltz.bio/boltz2 | Not fetched directly; cited via search 2 result snippets (title/claim level only) |

**Tools used.** Bash (read-only file and repository inspection plus section assembly: `cat`, `sed`, `grep`, `awk`, `ls`, `wc`, a one-line JSON key dump, `date`, `mkdir`, quoted heredocs for scratch parts), ToolSearch, WebSearch, WebFetch, Read (the peer report), Write and Edit (the single output file). Scratch parts under the session scratchpad at `scratchpad/ws3/`; no other project file was created or modified, and no commits were made.

**Could not access, and the consequence.**

- **GDSC primary documentation and data dictionary** — every project download and help page tried returned HTTP 410; the Sanger overview page carries no column dictionary and no explicit license. Consequently the dataset contract in §5 rests entirely on the package's own inventory metadata, the table's declared `data_version` is `unknown`, and the dictionary is recorded as an unmet prerequisite (Finding 7).
- **Europe PMC REST documentation** — HTTP 403 on both documentation pages. Endpoint and field facts come from a live schema probe of the public search endpoint plus search snippets; the "no key required" statement is from a search snippet, not from a page I read, and should be re-verified before implementation.
- **NCBI E-utilities reference chapters** — reCAPTCHA interstitial. Rate-limit and key facts come from NCBI's own announcement post; the full parameter reference was not read.
- **PubChem PUG REST documentation page** — client-rendered and returned no body; the usage-policy figures come from search results citing that page, reading depth snippet-level.
- **CDES** — no code, checkpoint, training data, or screening output exists in the package (`ARTIFACT_MANIFEST.json`: `scientific_models_run: false`), so §2 is an interface specification and a prerequisite list, not an assessment of a real backend.
- The manuscript's candidate list, the authors' individual eleven criteria, and any threshold values are not in the supplied material; none were invented, and no threshold is proposed anywhere in this report.
