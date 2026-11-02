# Run a study from a task file

[中文](zh/agent-run.md) · [Workflow design](design.md) · [Documentation index](README.md)

Start with the checkout, Python 3.11+ and the optional public capsule. Work in a **new independent workspace**. The commands below work in PowerShell and Linux/macOS shells from the repository root.

```sh
# Verify the saved result with the real qualification/scoring/ranking engine.
python scripts/agent_run.py replay --bootstrap --workspace var/agent-replay

# Inspect the same result in the workbench (builds the UI on first use).
python scripts/agent_run.py serve --bootstrap --workspace var/agent-replay --open

# Prepare the original complete input and a fresh evidence-only source, with zero CQA.
python scripts/agent_run.py plan --bootstrap --workspace var/agent-live --task config/examples/task.original.json

# Explicitly call your configured models and wait for the complete investigation.
python scripts/agent_run.py run --bootstrap --workspace var/agent-live --task config/examples/task.original.json --models /absolute/path/models.toml
```

On Windows, `agent-run.cmd` is an equivalent launcher: `agent-run.cmd replay --workspace var/agent-replay --open`. It automatically adds `--bootstrap`. After first setup, the runner reuses `.venv`; it installs Python dependencies only when the package/runtime is missing. Node.js/npm is needed only for `serve`, `--serve`, or `--open` when `web/client/dist/index.html` has not been built. Existing Python environments and built clients are reused.

## Replay and new research

The retained example displays **10 Eligible, 1,305 Evidence incomplete and 1,862 Excluded**. Replay verifies the frozen qualification fields (`qualified: 10`, `pending: 3167`, `rejected: 0`); the workbench derives the current selection groups and specific reasons from the same assessments. See [the version mapping](reference/system-alignment.md#classification-version).

`replay` downloads the approximately 168 MB release asset, checks its exact byte count and SHA-256 against the repository manifest, imports the selected public records and declared metadata projection, and calls production qualification, preference scoring, and snapshot construction. It compares every candidate entry and the relevant aggregate fields against the saved snapshot. Replay calculates from saved assessments. The original criterion history, run identities, costs and budget reports remain attached to those records.

`plan` prepares complete executable input without a model call. For the original task, it creates a new evidence-only source from the pinned 3,157 claims, 164 sources and 68,886 historical tool facts. Its starting CQA count is zero. `run` creates an independent research task, normalizes the objective, proposes/reviews/refines new criteria, resolves decisions, freezes rules, screens candidates, and publishes actual results. It uses current configured models over the saved factual inputs. Each investigation reports its own criteria, outcome, cost and prioritized candidates.

New work defaults to **mid literature/textbook workload, 4 workers, USD 10 and staged screening**. Original-case and uploaded-observation tasks use saved evidence; named drug-library tasks default to new retrieval. `--workers`, `--budget-usd`, and `--evaluation-mode full` override the new workflow's values. Every resolved workflow uses `<workspace>/cache` as its source cache.

## Credentials and model settings

Copy [the model TOML example](../config/examples/models.deepseek.toml) outside the repository, configure the provider/model and role bindings, and set its named environment variable or point `api_key_file` to an existing key file. A live run requires actual API model bindings for `proposer`, `critic`, and `adjudicator`. A missing binding or missing credential fails before any paid workflow is started. Keys are neither printed nor copied into receipts. `plan` and `replay` need no model configuration.

```powershell
# PowerShell: use the variable named by your models.toml.
$env:DEEPSEEK_API_KEY = '<your-key>'
python scripts/agent_run.py run --workspace var/agent-live --task config/examples/task.original.json --models C:/Users/YOU/.config/mas/models.toml
```

`run` starts the configured models, reports progress to stderr and writes a JSON receipt to stdout. Cost records distinguish recorded estimates, partial accounting and unknown charges. The budget applies to the amounts the system can account for. An optional `--config /path/mas.toml` supplies other settings; the investigation uses the configured provider connection.

## Your own drug library

Use [task.library.example.json](../config/examples/task.library.example.json) for a target-led drug study. Set `library_json` to your own library file, relative to the task JSON. Provide targets and requirements; objective text is optional when targets are supplied.

```json
{
  "input_mode": "library",
  "library_json": "drug-library.json",
  "targets": ["EGFR", "MET"],
  "constraints": "Documented oral administration is required.",
  "evidence_mode": "retrieve",
  "cdes_enabled": false,
  "workers": 4,
  "budget_usd": 10
}
```

The drug library is a JSON object with a nonempty `universe` array. Each compound supplies `name`, `inchikey` and `chembl_id`; InChIKeys identify unique members. Preserve the library's `source`, `retrieved_at`, and any recorded product/route `fields`. This is the same named-library format used by the drug adapter. The runner saves a fingerprinted copy in the chosen workspace.

```sh
python scripts/agent_run.py plan --bootstrap --workspace var/target-study --task /path/task.json
python scripts/agent_run.py run --workspace var/target-study --task /path/task.json --models /path/models.toml
```

Library mode uses that population and the supplied targets and requirements. New retrieval begins with this study's sources. Original-case mode remains the route for generating fresh criteria over the public example's recorded evidence.

### Optional CDES selection

A task JSON can set `cdes_enabled` and `cdes_source_id`. With CDES enabled, a single available collection is selected automatically; with multiple collections, choose the source explicitly in the workbench or task file. The source is pinned before the workflow starts. The [CDES guide](components/structure-predictions.md) describes importing a collection into the workspace.

CDES adds a target-profile stage after the main evaluation. Its result records the matched compound–target pairs and any missing coverage. The saved overall ranking retains its own criteria. The initial implementation reads supplied results through the deployment interface.

## Your own objective, candidates, and observations

Start from [task.custom.example.json](../config/examples/task.custom.example.json). Its fields are `objective`, a string array of `targets`, text `constraints`, and `entity_type` (`drug`, `carrier`, or `general`), plus `candidates_csv` and `measurements_csv`. Paths are resolved relative to the JSON file, regardless of the shell's working directory. The supplied [candidate](../config/examples/candidates.csv) and [measurement](../config/examples/measurements.csv) files contain headers only: replace them with your actual data before planning. The runner validates these supplied files before preparing the study.

```sh
python scripts/agent_run.py plan --bootstrap --workspace var/my-study --task /path/my-study/task.json
python scripts/agent_run.py run --bootstrap --workspace var/my-study --task /path/my-study/task.json --models /path/models.toml
```

CSV headers are exact and case-sensitive unless the task JSON supplies an explicit field mapping. Candidate fields are `candidate_id` (required), `name`, `smiles`, `inchikey`, `chembl_id`, `description`. Measurement fields are `candidate_id`, `property`, `value`, `basis` (all required), plus `unit`, `conditions`, `source`, `summary`. Numeric values require units (`1` for dimensionless). `basis` must be one of `measured`, `curated`, `predicted`, `simulated`, `derived`. Represent available observations as rows and leave missing observations absent. Every measurement must reference an exact candidate ID in the selected file. Plain-text conditions are kept; JSON object conditions are also accepted.

```json
{
  "candidates_mapping": {"candidate_id": "Sample ID", "name": "Display name"},
  "measurements_mapping": {"candidate_id": "Sample ID", "property": "Endpoint", "value": "Result", "unit": "Units", "basis": "Evidence basis"}
}
```

Add those optional mappings to the task object, using canonical field names on the left and exact file headers on the right. The runner uses `UploadStore.preview` and `commit`, preserves declared evidence basis/provenance, and rejects invalid rows before any model call. Candidate descriptions and measurement rows have separate roles. You can override JSON values with `--objective "..."`, `--targets target1 target2`, `--constraints "..."`, `--entity-type general`, `--title "..."`, and `--reference-candidate "exact ID or name"`. A reference label records the candidate to inspect in the outcome comparison.

## Resume, inspect, export, and serve

Repeat the **same `run` command** after a stop or restart. A durable request identity is written before submission, and the workflow database enforces that identity. A paused investigation resumes saved checkpoints and accumulated budget. A completed, failed, cancelled, or unresolved investigation is returned as the existing outcome; repeats do not silently start another paid investigation. A changed task or semantic model/settings selection is rejected unless you explicitly add `--new-run`. Keep using the same task JSON and overrides. The runner remembers the last model TOML path if `--models` is omitted on a retry.

```sh
python scripts/agent_run.py inspect --workspace var/agent-live
python scripts/agent_run.py run --workspace var/agent-live --task config/examples/task.original.json --models /path/models.toml --new-run
python scripts/agent_run.py serve --workspace var/agent-live --models /path/models.toml --port 8782 --open
```

`inspect`/`status` read workflow state without taking over the workspace. Other runner commands hold an OS workspace lock, so two runner processes cannot launch the same study concurrently. Use one owner process for a workspace; opening another independently launched workbench against the same store can interfere with checkpoint ownership. Ctrl+C requests a saved boundary and waits for the active work to reach it. A model request already in flight can take until its provider timeout. If essential task details are missing, the receipt contains the actual `questions`; use the workbench to answer them and resume there, or correct the task and explicitly start another investigation.

A completed workflow automatically exports the complete actual snapshot to `<workspace>/exports/<workflow_id>/`: every candidate row in JSON/CSV, CQA history and lineage, stages, task, frozen run bindings, model accounting, validation and report. `--output /new/export/directory` chooses another location. A repeated run reuses a matching export. Unfinished workflows write their state to `agent-run-incomplete.json`. The final report presents the research outcome together with its rules and supporting evidence. The receipt reports the declared reference's actual qualification/top-five outcome separately when it can be uniquely matched.

The default UI URL is `http://127.0.0.1:8782/`. Add `--serve` to `replay`/`run` to keep it running after completion, or `--open` to also open a browser. Stop `run` before using the separate `serve` command on that same workspace. A prepared plan appears in `agent-plan.json`, replay verification in `agent-replay-receipt.json`, and a live outcome in `agent-run-receipt.json`. Exit codes: `0` completed/successful command, `2` invalid configuration/input or runtime error, `3` saved live workflow needs attention or did not complete, `4` replay disagrees with the recorded result.

## Local capsule and download cache

```sh
python scripts/agent_run.py replay --workspace var/offline-replay --bundle /path/to/capsule-directory
python scripts/agent_run.py plan --workspace var/offline-live --bundle /path/to/capsule-directory --task config/examples/task.original.json
```

The directory must contain `manifest.json` and the declared capsule file(s). The importer checks all declared hashes. It reuses a completed import of the same capsule, or resumes its own interrupted import using the `.mas-import` ownership record. Unrelated populated workspaces and conflicting files are preserved and rejected. Downloads are cached outside the target workspace, by default under `<repo>/var/downloads/reproduction/<sha256>/`; override with `--download-cache /outside/cache`. Only a completed, checksum-verified download is imported. The optional public asset is [the v1.1.0 capsule](https://github.com/YWDDLiang03/mas/releases/download/v1.1.0/oral-multitarget-latest-public-20261028.jsonl.gz); the [repository manifest](../examples/oral-multitarget/latest/reproduction/manifest.json) is the checksum authority. Allow about 3 GB for a restored workspace and several minutes for the first browser index.

[中文操作说明](zh/agent-run.md)
