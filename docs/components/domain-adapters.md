# Domain adapters and source implementations

[Practical walkthrough](../component-walkthrough.md#domain-adapter) · [中文实操](../zh/component-walkthrough.md#domain-adapter)

[Components](README.md) · [Tool contract](tools-and-providers.md) · [Evidence](evidence-and-reading.md)

An adapter supplies domain vocabulary, identity policy, evidence providers and criterion templates while the core keeps record, execution and decision semantics. The release supplies a drug-prioritization adapter, reusable literature sources and an uploaded-data path for drug, carrier and general entities. The uploaded path does not assume receptors or administration routes.

## Composition contract

[`adapters/drug/registration.py`](../../src/mas/adapters/drug/registration.py) exposes `ADAPTER`, `CAPABILITY_BINDINGS`, `register()` and `objective_templates()`, plus its tool/catalog metadata. The composition root registers providers and passes adapter ID/version/primary identity scheme to the controller. Core modules do not import the drug registration module.

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

The drug templates bind explicit scope entities and constraints already in the task. They do not constitute independent literature discovery. Quantities from different curations can be combined in one attribute only through the declared unit, aggregation, basis and subject policy.

## Literature providers

[`adapters/literature/tools.py`](../../src/mas/adapters/literature/tools.py) registers Europe PMC search/reader, PubMed search, Bookshelf search/reader, MediaWiki search/readers for Wikibooks and Wikipedia, and local-upload search/readers. Search uses `source_retrieval`/`search`; reading uses `document_reading`/`read`. PubMed-discovered documents are read through the Europe PMC reader.

[`registry.py`](../../src/mas/adapters/literature/registry.py) keeps source IDs, evidence kinds, access route and LLM-ingestion status. Bookshelf requires synchronized permitted books; upload documents require a readable manifest. MediaWiki passages retain revision identity. Source kinds remain distinct, including peer-reviewed, preprint, reference text, tertiary reference and user-supplied document. The reader does not promote a tertiary or supplied source to peer-reviewed evidence.

[`jats.py`](../../src/mas/adapters/literature/jats.py) and [`textparse.py`](../../src/mas/adapters/literature/textparse.py) construct located passages from source documents. HTTP/source modules retain fetch/parse failures rather than returning fabricated empty papers.

## Optional ADMET environment

[`admet.py`](../../src/mas/adapters/predict/admet.py) locates the configured interpreter or candidate local environment, builds a structure index, invokes the worker in [`_admet_worker.py`](../../src/mas/adapters/predict/_admet_worker.py), caches panels and exposes endpoint metadata. `ExistingPanelProjection` permits local reuse of saved panel results with pinned dates and derivation information. The model panel and deterministic descriptors have different contracts and basis labels.

With `predict=None`, the drug registration includes prediction tools when an environment is found; `True` requests explicit failure when it is missing; `False` leaves them out. An absent installation yields an unavailable route, not an observed absence of the property. Under current qualification, predictions remain auxiliary: they cannot directly fail a hard condition or increase direct evidence coverage. Legacy predictor-boundary review routes remain identifiable in old run policies.

Boltz-2, CDES, general docking and molecular simulation providers are not implemented by this adapter. The `interaction_estimate` capability label is an extension contract, not evidence of an installed interaction predictor.

## Uploaded candidate and observation adapter

[`UploadedEvidence`](../../src/mas/core/uploaded_evidence.py) declares adapter `uploaded_candidates`, primary scheme `uploaded_id`, and a local `uploaded_measurement_lookup` provider. It pins exact properties, units, conditions, candidate IDs and basis declarations with dataset/row hashes. `property_catalog()` exposes metadata for criterion generation without distributing candidate measurements as a cutoff suggestion. Local hooks supply identity and observation claims.

The workbench CSV templates in [`ui/uploads.py`](../../src/mas/ui/uploads.py) accept entity kinds drug/carrier/general. A carrier workflow can evaluate particle size or cell viability under explicitly supplied conditions; it does not inherit the drug adapter's target/route assumptions. Requirements that name an absent property or unresolved measurement method remain clarification findings.

[`drug/clinical_routes.py`](../../src/mas/adapters/drug/clinical_routes.py) is another specialized local projection: a pinned admitted clinical-claim cache can produce a typed documented-administration-route assertion. It preserves the numeric source claim and adds a separate traceable Boolean projection; it does not perform new retrieval or treat a database's missing flag as proof of a route's absence.

## Extension and failure semantics

A new domain integration needs identity policy, provider contracts/question kinds, an executable catalog of evidence routes, and task-mandated templates where appropriate. Register those at composition; keep database-specific logic in the adapter. Reuse the core's evidence-kind vocabulary and basis labels or extend their writers/validators together.

Missing fields, ambiguous identity, absent environment, unconfigured local sources, upstream errors and license refusal retain their typed outcomes. A returned value must obey its contract ceiling and the criterion's evidence policy. A provider can be installed successfully while a specific criterion remains unanswerable.

## Worked example: a carrier dataset

**Illustrative:** candidate `EXAMPLE-A` has a particle-size observation 120 nm from DLS at 25 °C and a viability observation 92% at 24 h/10 µg mL⁻¹ in a declared assay. The upload hashes those exact observations. A size criterion bound to those DLS conditions can use the first row. A viability criterion requiring another dose/model cannot silently use the second row as a direct match. The system needs the appropriate observation or an explicit supported interpretation.

## Existing verification

[`test_drug_adapter.py`](../../tests/test_drug_adapter.py) checks drug contracts; [`test_predict_admet.py`](../../tests/test_predict_admet.py) and [`test_admet_existing_panel.py`](../../tests/test_admet_existing_panel.py) check optional predictions and saved projections. [`test_sources.py`](../../tests/test_sources.py) checks literature setup/access behavior. [`test_uploaded_evidence.py`](../../tests/test_uploaded_evidence.py), [`test_workbench_uploads.py`](../../tests/test_workbench_uploads.py) and [`test_clinical_routes.py`](../../tests/test_clinical_routes.py) cover local data contracts. `test_live_*` files are separate provider-dependent checks, not a requirement to contact external services when reading this reference.
