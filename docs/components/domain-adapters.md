# Domain adapters and source implementations

[Practical walkthrough](../component-walkthrough.md#domain-adapter) · [中文实操](../zh/component-walkthrough.md#domain-adapter)

[Components](README.md) · [Tool contract](tools-and-providers.md) · [Evidence](evidence-and-reading.md)

An adapter supplies domain vocabulary, identity policy, evidence providers and criterion templates while the core keeps record, execution and decision semantics. The release supplies a drug-prioritization adapter, reusable literature sources and an uploaded-data path for drug, carrier and general entities. Uploaded studies use their supplied properties and task requirements.

## Composition contract

[`adapters/drug/registration.py`](../../src/mas/adapters/drug/registration.py) exposes `ADAPTER`, `CAPABILITY_BINDINGS`, `register()` and `objective_templates()`, plus its tool/catalog metadata. The composition root registers providers and passes adapter ID/version/primary identity scheme to the controller. Core modules receive these capabilities through the composition root.

`register()` accepts an optional universe file, cache/upload locations, literature switch and optional prediction environment. With a universe file, local identity/record fields are registered first, followed by public identity, descriptors and curated interaction sources. Prediction registration is conditional on the selected environment policy. The bound tool manifest records what this installation actually had.

## Drug providers

| Provider / source | Question kind | Output and scientific basis |
|---|---|---|
| [`UniverseIdentity`](../../src/mas/adapters/drug/universe.py) | `resolve_name` | Fixed library identifiers/aliases; local source version |
| `UniverseRecordField` | `record_field` | Declared fields in the pinned library, with source-field location |
| [`PubChemIdentity`](../../src/mas/adapters/drug/pubchem.py) | `resolve_name` | PubChem crosswalk/structure identity; ambiguous/missing identity remains explicit |
| `PubChemProperty` | `computed_property` | Computed descriptors from PUG REST; derived descriptor basis and saved row provenance |
| [`ChEMBLBioactivity`](../../src/mas/adapters/drug/chembl.py) | `pchembl_values` | Curated measured bioactivity at the declared target, with source record context |
| `ChEMBLMechanism` | `mechanism_records` | Curated database assertions about target mechanism; distinct from a potency measurement |
| [`GtoPdbAffinity`](../../src/mas/adapters/drug/gtopdb.py) | `gtopdb_affinity` | Curated affinity observations and references from the IUPHAR/BPS data cache |
| [`AdmetPrediction`](../../src/mas/adapters/predict/admet.py) | `admet_prediction` | Optional learned ADMET endpoint predictions, explicitly predicted |
| `AdmetComputedDescriptors` | `admet_computed_property` | Optional deterministic structural descriptors from the predictor environment, separately identified |

[`identity.resolve_universe()`](../../src/mas/core/identity.py) asks registered entity-resolution providers and creates domain-neutral candidate IDs from the declared primary scheme. It retains exact/crosswalk/single-name/ambiguous/unresolved link bases. Ambiguous candidates get a review record; unresolved members retain a row instead of being dropped from the population.

The drug templates bind explicit scope entities and constraints already in the task. Literature discovery uses the selected source providers. Quantities from different curations can be combined in one attribute only through the declared unit, aggregation, basis and subject policy.

## Literature providers

[`adapters/literature/tools.py`](../../src/mas/adapters/literature/tools.py) registers Europe PMC search/reader, PubMed search, Bookshelf search/reader, MediaWiki search/readers for Wikibooks and Wikipedia, and local-upload search/readers. Search uses `source_retrieval`/`search`; reading uses `document_reading`/`read`. PubMed-discovered documents are read through the Europe PMC reader.

[`registry.py`](../../src/mas/adapters/literature/registry.py) keeps source IDs, evidence kinds, access route and LLM-ingestion status. Bookshelf requires synchronized permitted books; upload documents require a readable manifest. MediaWiki passages retain revision identity. Source kinds remain distinct, including peer-reviewed, preprint, reference text, tertiary reference and user-supplied document. The reader retains each source's declared type.

[`jats.py`](../../src/mas/adapters/literature/jats.py) and [`textparse.py`](../../src/mas/adapters/literature/textparse.py) construct located passages from source documents. HTTP/source modules retain fetch and parse failures with their causes.

## Optional ADMET environment

[`admet.py`](../../src/mas/adapters/predict/admet.py) locates the configured interpreter or candidate local environment, builds a structure index, invokes the worker in [`_admet_worker.py`](../../src/mas/adapters/predict/_admet_worker.py), caches panels and exposes endpoint metadata. `ExistingPanelProjection` permits local reuse of saved panel results with pinned dates and derivation information. The model panel and deterministic descriptors have different contracts and basis labels.

With `predict=None`, the drug registration includes prediction tools when an environment is found; `True` requests explicit failure when it is missing; `False` leaves them out. An absent installation yields an unavailable route. Predictions support permitted scoring and interpretation; hard-condition decisions and direct coverage use accepted direct evidence. Legacy predictor-boundary review routes remain identifiable in old run policies.

The [structure-prediction supplement](structure-predictions.md) reads supplied CDES results and links them to a saved evaluation. New studies can select this analysis as an optional step. The pair-scoring interface supports a later deployed model; other interaction predictors can be added through their own adapter contracts.

## Uploaded candidate and observation adapter

[`UploadedEvidence`](../../src/mas/core/uploaded_evidence.py) declares adapter `uploaded_candidates`, primary scheme `uploaded_id`, and a local `uploaded_measurement_lookup` provider. It pins exact properties, units, conditions, candidate IDs and basis declarations with dataset/row hashes. `property_catalog()` exposes metadata for criterion generation without distributing candidate measurements as a cutoff suggestion. Local hooks supply identity and observation claims.

The workbench CSV templates in [`ui/uploads.py`](../../src/mas/ui/uploads.py) accept entity kinds drug/carrier/general. A carrier workflow evaluates properties such as particle size or cell viability under its supplied conditions. Requirements that name an absent property or unresolved measurement method remain clarification findings.

[`drug/clinical_routes.py`](../../src/mas/adapters/drug/clinical_routes.py) is another specialized local projection: a pinned admitted clinical-claim cache can produce a typed documented-administration-route assertion. It derives a traceable Boolean assertion from the pinned clinical claims and retains the source observation. Missing route support is recorded as a gap.

## Extension and failure semantics

A new domain integration needs identity policy, provider contracts/question kinds, an executable catalog of evidence routes, and task-mandated templates where appropriate. Register those at composition; keep database-specific logic in the adapter. Reuse the core's evidence-kind vocabulary and basis labels or extend their writers/validators together.

Missing fields, ambiguous identity, absent environment, unconfigured local sources, upstream errors and license refusal retain their typed outcomes. A returned value must obey its contract ceiling and the criterion's evidence policy. A provider can be installed successfully while a specific criterion remains unanswerable.

## Worked example: a carrier dataset

**Illustrative:** candidate `EXAMPLE-A` has a particle-size observation 120 nm from DLS at 25 °C and a viability observation 92% at 24 h/10 µg mL⁻¹ in a declared assay. The upload hashes those exact observations. A size criterion bound to those DLS conditions can use the first row. A viability criterion requiring another dose or model needs a matching observation or a supported interpretation of the difference.

## Existing verification

[`test_drug_adapter.py`](../../tests/test_drug_adapter.py) checks drug contracts; [`test_predict_admet.py`](../../tests/test_predict_admet.py) and [`test_admet_existing_panel.py`](../../tests/test_admet_existing_panel.py) check optional predictions and saved projections. [`test_sources.py`](../../tests/test_sources.py) checks literature setup/access behavior. [`test_uploaded_evidence.py`](../../tests/test_uploaded_evidence.py), [`test_workbench_uploads.py`](../../tests/test_workbench_uploads.py) and [`test_clinical_routes.py`](../../tests/test_clinical_routes.py) cover local data contracts. `test_live_*` checks exercise the configured external providers separately.
