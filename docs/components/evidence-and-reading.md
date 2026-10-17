# Evidence sources, reading and claim admission

[Components](README.md) · [Tools](tools-and-providers.md) · [Criteria](criteria-and-review.md)

The evidence layer turns provider outputs and source passages into claims that can be inspected and used by a criterion. Its purpose is to preserve the chain from a candidate's verdict back to the observation, document location and retrieval operation. This is C9, with reusable literature reading and uploaded-data paths.

## Inputs and outputs

| Input | Output |
|---|---|
| Search query, permitted sources, date cutoff and budget | Search hits, duplicate handling and coverage records |
| Search hit or uploaded document | Located passages, source metadata, access/reading-depth limits |
| Document, extraction question and model roster | Checked claims, including quarantined extractions with reasons |
| Database tool result, candidate identity and attribute reference | Record-field claims with tool provenance |
| Admitted claim IDs and tool manifest | Immutable evidence snapshot with cutoff and hash |

The stored objects are sources, document/read artifacts, claims, visibility/coverage records and snapshots. An admitted claim is eligible for downstream consideration; the attribute's evidence policy can still set it aside.

## Why location and attribution are explicit

A correct quote can support the wrong compound or endpoint. MAS therefore keeps source access, span matching, entity attribution and value interpretation separate. [`reading.py`](../../src/mas/core/reading.py) offers `quote_found`, `value_in_quote`, `names_entity` and `attribution_problem`. The extraction path checks the cited passage, quote, number and subject/context before admitting a claim. Typography normalization permits quotation matching across harmless formatting differences, while the stored quote remains tied to a real passage.

`select_passages()` bounds the text offered to the model. `summarize()` retains cited points only when their citations pass checks. `extract_claims()` records each extraction's admission reasons. Verified quotation establishes that the words are present; source interpretation and scientific truth require the criterion-specific checks and research judgment that follow.

## Literature workflow

`plan_queries()` uses the configured retriever role. `search()` dispatches through permitted sources, applies cutoff/case-source exclusions, deduplicates hits and records coverage. `read()` records source access and document reading depth. Full text unavailable at a permitted endpoint can leave abstract-depth evidence; it does not become full-text evidence by inference.

The source registry in [`adapters/literature/registry.py`](../../src/mas/adapters/literature/registry.py) owns access/ingestion declarations. Europe PMC and PubMed supply literature discovery; Bookshelf uses synchronized permitted open-access books; Wikipedia/Wikibooks keep revision information; uploaded documents need a manifest declaration. OpenStax is present as a refused source entry and has no registered search/reading path. The registry is executable source-access policy; source-specific terms and provenance stay attached to records.

[`evidence.gather()`](../../src/mas/core/evidence.py) follows the attribute's declared routes. Database routes create claims at source-record fields. Literature routes form candidate queries and share a candidate-level reading cache so one paper can answer several attributes without repeated reading. Multiple routes are combined only under the attribute's accepted evidence/basis and aggregation policy. Deferred capabilities are retained as deliberate limits.

## Ledger implementation

[`ledger.put_source()`](../../src/mas/core/ledger.py) validates source/access states and stores the source. `record_claim()` requires an exact location and valid reading depth, then stores the claim with admission state, reasons, actor and timestamp. `claims()` reads matching admissions from explicit streams with candidate/attribute/ID filters. `freeze_snapshot()` records the sorted claim IDs, cutoff and tool manifest, plus a canonical hash.

Database claims preserve `tool_result_ref`, record-field locator, identity-link basis, value kind and determination basis. These are distinct: a database can carry measured curated bioactivity, a curated assertion or a computed descriptor. [`evidence.determination_basis()`](../../src/mas/core/evidence.py) respects the provider's declared basis and checks it against the accepted basis vocabulary.

## Uploaded evidence and verified supplements

CSV intake is previewed and mapped in [`ui/uploads.py`](../../src/mas/ui/uploads.py). [`UploadedEvidence`](../../src/mas/core/uploaded_evidence.py) pins library identity, dataset hash, unique candidates, unique observations, exact property IDs, units, conditions and declared bases. Its local provider and hooks expose only those recorded observations. An upload records the submitter's declared observation; it does not create peer review, a threshold or candidate suitability.

[`supplements.py`](../../src/mas/core/supplements.py) can create and attach a verified supplemental observation from an existing read document and checked claim. `lookup()` matches the bound supplement; `record_reuse()` retains provenance when reused. This supports targeted source-backed completion while keeping the original measurement and the later supplement distinguishable.

## Failure semantics

Fetch failures, absent source configuration, unlicensed ingestion, metadata-only/abstract-only access, invalid spans, ambiguous attribution and missing values remain explicit. Unsupported extracted claims are quarantined or rejected from use, retaining reasons. Missing direct evidence remains unknown in assessment. `existing_only` uses pinned facts and returns `existing_evidence_unavailable` on a miss; it does not perform a hidden fresh fetch.

## Worked example: same quote, different admission

**Illustrative** source passage: “Compound A inhibited Target X with IC50 20 nM; Compound B required 200 nM.” A model proposes `Compound B / Target X / 20 nM` and quotes the full sentence. Span matching succeeds and the number exists in the quote, but the attribution check can identify the number as belonging to Compound A. That extraction is kept with its refusal reason and supplies no measured value for B. A correctly attributed B claim at 200 nM can be admitted and then converted by an attribute whose unit policy accepts that transformation.

## Existing verification

[`test_models_and_reading.py`](../../tests/test_models_and_reading.py) checks source deduplication, real quoted spans, cited summaries and case-source matching. [`test_evidence.py`](../../tests/test_evidence.py), [`test_uploaded_evidence.py`](../../tests/test_uploaded_evidence.py) and [`test_supplements.py`](../../tests/test_supplements.py) cover the concrete gathering/intake/reuse paths. [`test_evidence_groups.py`](../../tests/test_evidence_groups.py) and [`test_workbench_evidence.py`](../../tests/test_workbench_evidence.py) cover evidence relationships exposed in the workbench.
