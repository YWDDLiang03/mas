# One-command handoff to another agent

The checkout, Python 3.11+, and the public optional capsule are sufficient. No original private store, manuscript PDF, private account, or operator log is needed. Work in a **new independent workspace**. The commands below work in PowerShell and Linux/macOS shells from the repository root.

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

## Replay and new research answer different questions

`replay` downloads the approximately 168 MB release asset, checks its exact byte count and SHA-256 against the repository manifest, imports public immutable records, and calls production qualification, preference scoring, and snapshot construction. It compares every candidate entry and the relevant aggregate fields against the saved snapshot. It makes **zero new model calls, zero retrieval calls, and no new CQA**. The saved failed history, original run identities, costs, and budget reports remain historical records. Matching the old leaderboard validates deterministic engine replay from saved assessments; it does not rerun the old models or regenerate old criteria.

`plan` prepares complete executable input without a model call. For the original task, it creates a new evidence-only source from the pinned 3,157 claims, 164 sources and 68,886 historical tool facts. Its starting CQA count is zero. `run` creates an independent research task, normalizes the objective, proposes/reviews/refines new criteria, resolves decisions, freezes rules, screens candidates, and publishes actual results. It uses current configured models over the saved factual inputs. This is a counterfactual new trajectory: its criteria, outcome, cost, and winner can differ from the historical result. There is no promise that Surufatinib will pass or rank first.

The defaults for new work are **mid literature/textbook workload, 4 workers, USD 10, staged screening, saved evidence only**. These defaults apply to the new workflow and do not rewrite the original recorded budget. `--workers`, `--budget-usd`, and `--evaluation-mode full` override the new workflow's values. Every resolved workflow uses `<workspace>/cache` as its source cache.

## Credentials and model settings

Copy [the model TOML example](../config/examples/models.deepseek.toml) outside the repository, configure the provider/model and role bindings, and set its named environment variable or point `api_key_file` to an existing key file. A live run requires actual API model bindings for `proposer`, `critic`, and `adjudicator`. A missing binding or missing credential fails before any paid workflow is started. Keys are neither printed nor copied into receipts. `plan` and `replay` need no model configuration.

```powershell
# PowerShell: use the variable named by your models.toml.
$env:DEEPSEEK_API_KEY = '<your-key>'
python scripts/agent_run.py run --workspace var/agent-live --task config/examples/task.original.json --models C:/Users/YOU/.config/mas/models.toml
```

`run` is the explicit instruction to use the configured models; it does not request another confirmation. The command waits in the foreground and writes human-readable progress to stderr and a JSON receipt to stdout. Missing prices/token usage remain unknown or partial in the actual accounting. The budget limit and known recorded cost are distinct fields; absent tariff information is not a zero-dollar model call. An optional `--config /path/mas.toml` supplies other MAS settings. Bootstrap readiness is local; actual provider connectivity is first exercised by the real investigation.

## Your own objective, candidates, and observations

Start from [task.custom.example.json](../config/examples/task.custom.example.json). Its fields are `objective`, a string array of `targets`, text `constraints`, and `entity_type` (`drug`, `carrier`, or `general`), plus `candidates_csv` and `measurements_csv`. Paths are resolved relative to the JSON file, regardless of the shell's working directory. The supplied [candidate](../config/examples/candidates.csv) and [measurement](../config/examples/measurements.csv) files contain headers only: replace them with your actual data before planning. The runner does not generate observations or substitute the original compound library when your files or measurements are missing.

```sh
python scripts/agent_run.py plan --bootstrap --workspace var/my-study --task /path/my-study/task.json
python scripts/agent_run.py run --bootstrap --workspace var/my-study --task /path/my-study/task.json --models /path/models.toml
```

CSV headers are exact and case-sensitive unless the task JSON supplies an explicit field mapping. Candidate fields are `candidate_id` (required), `name`, `smiles`, `inchikey`, `chembl_id`, `description`. Measurement fields are `candidate_id`, `property`, `value`, `basis` (all required), plus `unit`, `conditions`, `source`, `summary`. Numeric values require units (`1` for dimensionless). `basis` must be one of `measured`, `curated`, `predicted`, `simulated`, `derived`. Missing observations are omitted, not supplied as `NaN`, `unknown`, or invented values. Every measurement must reference an exact candidate ID in the selected file. Plain-text conditions are kept; JSON object conditions are also accepted.

```json
{
  "candidates_mapping": {"candidate_id": "Sample ID", "name": "Display name"},
  "measurements_mapping": {"candidate_id": "Sample ID", "property": "Endpoint", "value": "Result", "unit": "Units", "basis": "Evidence basis"}
}
```

Add those optional mappings to the task object, using canonical field names on the left and exact file headers on the right. The runner uses `UploadStore.preview` and `commit`, preserves declared evidence basis/provenance, and rejects invalid rows before any model call. Candidate descriptions alone do not become measurement evidence. You can override JSON values with `--objective "..."`, `--targets target1 target2`, `--constraints "..."`, `--entity-type general`, `--title "..."`, and `--reference-candidate "exact ID or name"`. A reference records an outcome comparison; it is not forced into a winner.

## Resume, inspect, export, and serve

Repeat the **same `run` command** after a stop or restart. A durable request identity is written before submission, and the workflow database enforces that identity. A paused investigation resumes saved checkpoints and accumulated budget. A completed, failed, cancelled, or unresolved investigation is returned as the existing outcome; repeats do not silently start another paid investigation. A changed task or semantic model/settings selection is rejected unless you explicitly add `--new-run`. Keep using the same task JSON and overrides. The runner remembers the last model TOML path if `--models` is omitted on a retry.

```sh
python scripts/agent_run.py inspect --workspace var/agent-live
python scripts/agent_run.py run --workspace var/agent-live --task config/examples/task.original.json --models /path/models.toml --new-run
python scripts/agent_run.py serve --workspace var/agent-live --models /path/models.toml --port 8782 --open
```

`inspect`/`status` read workflow state without taking over the workspace. Other runner commands hold an OS workspace lock, so two runner processes cannot launch the same study concurrently. Use one owner process for a workspace; opening another independently launched workbench against the same store can interfere with checkpoint ownership. Ctrl+C requests a saved boundary and waits for the active work to reach it. A model request already in flight can take until its provider timeout. If essential task details are missing, the receipt contains the actual `questions`; use the workbench to answer them and resume there, or correct the task and explicitly start another investigation.

A completed workflow automatically exports the complete actual snapshot to `<workspace>/exports/<workflow_id>/`: every candidate row in JSON/CSV, CQA history and lineage, stages, task, frozen run bindings, model accounting, validation and report. `--output /new/export/directory` chooses another location. A repeated run reuses a matching export. No final export is claimed for an unfinished workflow; its actual state is saved as `agent-run-incomplete.json`. Completion means the workflow finished; scientific success still requires checking the rules, evidence and results. The receipt reports the declared reference's actual qualification/top-five outcome separately when it can be uniquely matched.

The default UI URL is `http://127.0.0.1:8782/`. Add `--serve` to `replay`/`run` to keep it running after completion, or `--open` to also open a browser. Stop `run` before using the separate `serve` command on that same workspace. A prepared plan appears in `agent-plan.json`, replay verification in `agent-replay-receipt.json`, and a live outcome in `agent-run-receipt.json`. Exit codes: `0` completed/successful command, `2` invalid configuration/input or runtime error, `3` saved live workflow needs attention or did not complete, `4` replay disagrees with the recorded result.

## Local capsule and download cache

```sh
python scripts/agent_run.py replay --workspace var/offline-replay --bundle /path/to/capsule-directory
python scripts/agent_run.py plan --workspace var/offline-live --bundle /path/to/capsule-directory --task config/examples/task.original.json
```

The directory must contain `manifest.json` and the declared capsule file(s). The importer checks all declared hashes. It reuses a completed import of the same capsule, or resumes its own interrupted import using the `.mas-import` ownership record. Unrelated populated workspaces and conflicting files are preserved and rejected. Downloads are cached outside the target workspace, by default under `<repo>/var/downloads/reproduction/<sha256>/`; override with `--download-cache /outside/cache`. An interrupted download leaves no published capsule, and a corrupt cache file is never imported. The optional public asset is [the v1.1.0 capsule](https://github.com/YWDDLiang03/mas/releases/download/v1.1.0/oral-multitarget-latest-v1.jsonl.gz); the [repository manifest](../examples/oral-multitarget/latest/reproduction/manifest.json) is the checksum authority. Allow about 3 GB for a restored workspace and several minutes for the first browser index.

[中文操作说明](zh/agent-run.md)
