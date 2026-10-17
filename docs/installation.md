# Install and start MAS

MAS can start with a new, empty local workspace. A source checkout contains frozen result exports, but no restored interactive studies, private API credentials or operational candidate database. You can inspect the published files or import your own candidates and evidence to start a study.

## Windows prerequisites

- Python **3.11 or newer** for the core service. Python 3.11 is a suitable baseline when preparing an optional prediction environment separately.
- Node.js **22 or 24 LTS**, with npm, to build the browser client. The pinned Vite 5.4.21 package accepts `^18.0.0 || >=20.0.0`; use a maintained Node release from the [official release list](https://nodejs.org/en/about/previous-releases).
- Git if you clone the repository, or an extracted source archive. Use a local writable directory for the SQLite workspace.

The Windows launcher uses the repository's `.venv/Scripts/python.exe` when present, otherwise `python` on `PATH`. Pass `-Python <absolute-path>` to select another interpreter. The core server uses Python's standard HTTP/SQLite facilities and the `requests` package; installing an OpenAI SDK, a database server or an ADMET package is unnecessary for first launch.

## 1. Install from the repository root

Open PowerShell in the extracted or cloned repository:

```powershell
python --version
node --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd --prefix web/client ci
npm.cmd --prefix web/client run build
```

`requirements.txt` installs this repository and its development extra from `pyproject.toml`; `pip install -e ".[dev]"` is equivalent. The explicit interpreter avoids an activation or execution-policy step. `npm.cmd` also works when PowerShell blocks the `npm.ps1` shim. The frontend build belongs to this checkout; repeat it after changing frontend code or updating the checkout.

## 2. Start an empty workspace without a model call

```powershell
.\start_workbench.cmd -Store var\workspace\store -InitializeStore -AllowOperations -NoBrowser -ActorKind human -ActorName "$env:USERNAME"
```

Open [http://127.0.0.1:8769/workbench/](http://127.0.0.1:8769/workbench/). An empty task list and empty candidate/evidence selectors are expected. Initialization creates SQLite tables and an example `models.toml`; it creates no task, candidate or scientific result. `-InitializeStore` leaves an existing database intact and is optional on later launches. Stop this process with **Ctrl+C** before changing its model configuration.

The generated model file uses an external-agent exchange example. For ordinary API-backed research, replace it as described below. Opening the empty workbench, viewing Settings and validating configuration do not call a model.

## 3. Configure DeepSeek for new research

Copy the supplied examples into your ignored workspace directory:

```powershell
Copy-Item config\examples\models.deepseek.toml var\workspace\store\models.toml
Copy-Item config\examples\mas.toml var\workspace\store\mas.toml
.\.venv\Scripts\python.exe -m mas.cli.main --store var/workspace/store --config var/workspace/store/mas.toml config validate
.\.venv\Scripts\python.exe -m mas.cli.main --store var/workspace/store models show
```

Set `DEEPSEEK_API_KEY` for this PowerShell session without placing the key in shell history:

```powershell
$masCredential = Get-Credential -UserName 'DeepSeek' -Message 'Enter your DeepSeek API key in the password field'
$env:DEEPSEEK_API_KEY = $masCredential.GetNetworkCredential().Password
Remove-Variable masCredential
.\start_workbench.cmd -Store var\workspace\store -Models var\workspace\store\models.toml -Config var\workspace\store\mas.toml -AllowOperations -ActorKind human -ActorName "$env:USERNAME"
```

The example also shows an external `api_key_file` alternative. See [configuration](configuration.md) for key lookup, paths, cost accounting, source tools and prompts. The example uses `deepseek-flash` through the [official DeepSeek API endpoint](https://api-docs.deepseek.com/). Parsing these files checks their schema and role bindings; API connectivity and account access are checked when a real request is made.

## 4. Import data and start research

Open **Settings** to choose workload, worker count and the cost envelope. Use **Use own data** to import a candidate CSV, review the column mapping, then import its measurement CSV. The [header templates](../config/examples/) contain no sample observations; fill them with your own data before upload. The [CSV input guide](csv-input.md) describes accepted columns, illustrative examples and preview corrections.

Choose the entity type appropriate to your candidates, including carriers or general candidates. Preserve IDs, measurement units, conditions, sources and whether each observation is measured or predicted. Describe the objective, required observations, hard conditions and preferences. A source checkout has no inherited evidence collection: supply evidence for **Use own data**, or explicitly select retrieval for a new literature-based investigation. An existing-only task needs a saved evidence collection or uploaded measurements.

Starting research can make paid model requests; retrieval can also contact evidence services. **AllowOperations** permits local Settings edits, uploads, task creation and workflow control. A submission starts normalization, evidence preparation, CQA derivation/review and evaluation under its recorded settings. Expert decisions recorded as human decisions still require terminal confirmation.

## Viewing and advanced launch options

To open an existing store through the legacy read-only interface, omit the operation switch:

```powershell
.\start_workbench.cmd -Store var\workspace\store -NoBrowser
```

This interface serves the read pages and refuses mutation requests. The modern React workbench currently requires `-AllowOperations`; it is served at `/workbench/`. Both modes listen on loopback. `-Port 8781` selects another port. `-Settings 'assess.workers=2','budget.usd_max=5'` supplies CLI overrides when invoking the PowerShell script directly.

The Windows script resolves relative `-Store`, `-Models`, `-Config` and interpreter file paths from the repository root, and runs there even when called from another directory. `MAS_WORKBENCH_ASSET_DIR` can select a different frontend build. In contrast, direct `python -m mas.cli.main` commands resolve relative paths from the current directory. Keep all workspace siblings (uploads, workflow records, display metadata and read caches) with the store directory when moving a workspace.

For macOS/Linux, run from the source root after installing Python dependencies and building the client:

```sh
python -m mas.cli.main --store var/workspace/store init
python -m mas.cli.main --store var/workspace/store --models config/examples/models.deepseek.toml --config config/examples/mas.toml ui serve --port 8769 --allow-operations --operation-actor-kind human --operation-actor-name operator
```

The commands use the same Python entry point; the release validation below covers Windows.

## Validation and common failures

- **Missing `store.db`**: use `-InitializeStore` for a new workspace or select an existing store. The launcher never restores a retained study automatically.
- **Client build missing**: run the two npm commands above from the repository root.
- **Port occupied**: pass another `-Port`; leave unrelated services running.
- **Model unavailable/auth missing**: check the copied role bindings and set the credential in the process that launches MAS. The default external-agent exchange waits for a responding external agent.
- **Prediction unavailable**: configure and test its separate environment; the core installation does not install predictor packages.

Release installation checks on 2026-10-17 used Windows, core Python 3.14.2 and Node.js 24.13.0. They covered the frontend build, example parsing and a new temporary workspace on an independent port. The optional ADMET environment and paid model/retrieval paths were not exercised in these installation checks. See [configuration](configuration.md) for the optional predictor boundary.
