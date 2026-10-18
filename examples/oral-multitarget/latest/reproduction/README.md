# Portable oral multi-target reproduction capsule

This optional capsule restores the recorded latest study into a new workspace and supplies fixed factual inputs for an independent investigation. See the [tutorial](../../../../docs/tutorial.md) and [agent runner](../../../../scripts/agent_run.py) for the workflow. The source private SQLite workspace is not required.

The archive `oral-multitarget-latest-v1.jsonl.gz` is an optional release asset of **168,065,291 bytes**, separate from the Git checkout. [manifest.json](manifest.json) binds the archive to its SHA-256 hash. Put the downloaded archive beside a copy of that manifest; the importer validates it before creating a workspace. It refuses to overwrite an existing populated workspace and recognizes an identical earlier import.

The selected dependency set contains:

- The latest task, criterion development and review records, 53 final working items, and frozen rule sets.
- All 3,177 final candidates and their 98,487 recorded assessment cells across 31 frozen evaluation rules. The 18-rule core and 13 reference observations retain their recorded roles.
- The pinned 3,157 generation facts and 164 source records, plus factual dependencies used by the frozen assessments.
- The exact 68,886 successful or empty historical tool facts, 3,084 PubChem descriptor rows, the recorded candidate library and structures, and all 3,177 cached ADMET panel rows.
- The eight historical candidate-literature claims used by the existing fact-rebinding route and their three measurement descriptions. Their old assessment verdicts and scoring decisions are not inputs to the independent run.
- The final workflow's public progress and cost metadata. Provider configuration, credentials, operator logs, private/evaluator records, recovery artifacts, full-text documents and the original manuscript PDF are excluded.

This is a selected immutable-record capsule, not a complete journal backup. Original event IDs, sequence numbers, source row order and record hashes are retained; omitted sequence positions are expected. Excluded document and model-trace references remain historical audit pointers and are listed in the manifest. Original local paths inside immutable records are provenance. New work uses the imported workspace's own library and cache paths.

The first latest-study snapshot survives in the source as an immutable artifact, while its original publication event was removed during earlier workspace cleanup. The artifact is retained as an available historical reference in the manifest. Import restores only original available event rows, so the workbench shows the final published snapshot. The old artifact's full assessment stream is not supplied. The final snapshot's complete assessment dependencies are supplied.

Two different operations are supported:

1. **Recorded replay:** `mas.core.reproduction.import_bundle(bundle_directory, workspace)` restores the saved study. `verify_replay(store_root)` calls the production qualification, preference scoring and leaderboard functions over the frozen assessments, then compares every final candidate field and the reporting tuple. This reuses the recorded CQA and factual observations. It does not generate CQA or call a model.
2. **Independent live investigation:** `prepare_live(workspace)` creates a new evidence-only source task with an empty criterion pool and registry and returns the input for a new workflow. A configured model develops fresh CQA from the fixed facts. Candidate tools use the imported historical facts and cached predictions through `existing_only`; scientific outcomes, criterion counts and Surufatinib's new rank depend on the actual new run. The original run's saved USD 5.50 budget and USD 4.2101472 estimated cost remain historical records.

[verification.json](verification.json) records a completed fresh import and production engine replay: all 3,177 candidates and 98,487 cells matched, with zero differences. Surufatinib reproduced rank 1, score `0.7592592592592593`, and direct preference coverage `10/17`. Offline dependency checks independently loaded all declared tool facts, descriptor rows, cached panel candidates and pinned generation facts, and confirmed that the independent source starts with zero CQA. The backend workbench projection reached ready, selected final snapshot 2 and reported the completed task with zero synthetic history events. No paid model, network retrieval, new live investigation or browser GUI validation was performed for this verification.

To rebuild the capsule from an authorized local source store:

```bash
python scripts/build_reproduction_bundle.py --store var/primary/store --out var/reproduction-build/new-capsule
```

The builder opens that store read-only and exports only the declared dependencies. A fresh checkout downloads the optional release asset identified by the committed manifest; it does not need to run the builder.
