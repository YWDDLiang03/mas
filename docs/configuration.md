# Configure MAS

Run settings and model bindings are ordinary TOML files. Start with [the portable examples](../config/examples/) and copy editable files into an ignored workspace directory. No private `var/primary` file is required.

## Run settings and precedence

`--config FILE` selects the run configuration. Without it, MAS checks `./mas.toml`, then `STORE/mas.toml`. Values resolve in this order, from lowest to highest priority:

1. Code defaults.
2. `--preset quick|standard|deep` (default: `standard`).
3. Project TOML.
4. A named `--profile` from `~/.config/mas/profiles/NAME.toml`.
5. `MAS__SECTION__KEY` environment variables.
6. Repeated `--set section.key=value` arguments.

For example, both forms change candidate concurrency:

```powershell
$env:MAS__ASSESS__WORKERS = '2'
.\.venv\Scripts\python.exe -m mas.cli.main --config config/examples/mas.toml --set assess.workers=4 config show --explain
Remove-Item Env:MAS__ASSESS__WORKERS
```

Use `config validate` for types/ranges and `config show --explain` for the effective value and source layer. `config estimate` estimates effort from supplied dimensions/candidates without calling a model. Unknown scalar keys are refused; [the settings registry](../src/mas/core/config.py) defines available keys and defaults.

The example uses mid literature/textbook workload, four candidate workers, staged evaluation, existing-only evidence and a USD 10 envelope. Browser Settings changes are saved in `STORE/../workbench-state.json` and affect subsequent work. The workbench's research controller records a resolved workflow configuration, including the submitted workers, evidence/evaluation mode and budget; it runs its workflow autonomously and finalizes a partial result on budget exhaustion. Standalone CLI checkpoint settings therefore do not describe every browser workflow setting. Existing run bindings retain their recorded settings.

## DeepSeek and other model adapters

`--models FILE` selects model providers and role bindings. Without that option, providers/roles in `--config` take precedence when present, otherwise `STORE/models.toml` is used. [models.deepseek.toml](../config/examples/models.deepseek.toml) binds retriever, reader, summarizer, proposer, critic and adjudicator to an OpenAI-compatible DeepSeek adapter. The API model name and base URL follow [DeepSeek's API guide](https://api-docs.deepseek.com/); verify available models and prices for your account before a paid run.

This example is for new research. The latest retained study records the historical model ID `deepseek-v4-flash` in its run metadata. Keep that stored identity when interpreting or exporting its results; selecting a current API model for a new task does not update a saved run or establish a rerun result.

Credentials are read at call time:

```toml
[providers.deepseek]
kind = "openai_compatible"
provider_family = "deepseek"
base_url = "https://api.deepseek.com"
model = "deepseek-flash"
api_key_env = "DEEPSEEK_API_KEY"
# Optional fallback. Replace the placeholder and store only the key in this file.
# api_key_file = 'C:/Users/YOUR_USERNAME/.config/mas/deepseek.key'
thinking = false
```

The named environment variable wins when nonempty; otherwise MAS reads `api_key_file`. A key-file path supports `~` expansion. It does **not** substitute `${ENV_VAR}`, `%ENV_VAR%` or `$env:...` text inside TOML. Use a literal absolute path or the actual `api_key_env` field. Relative key-file paths resolve from the running process's directory, so an external absolute path is easier to move and inspect. Never commit key files or inline keys. The installation guide shows an interactive session credential prompt that avoids putting the key in command history.

`models show` constructs adapters and prints role bindings without reading the credential or calling the provider. `thinking = false` selects the structured extraction/judging configuration in this example. All roles share one provider/model in this simple setup; their role names do not imply provider independence. Recovery measurement requires an appropriately isolated `evaluator_judge` configuration, which the first-use example does not claim to provide.

Optional `price_input_per_mtok` and `price_output_per_mtok` values are USD per million tokens. Set them from the applicable current tariff to enable a token-based cost estimate. Without prices or provider-reported cost, spend can remain unknown; a USD envelope cannot ensure a monetary ceiling for unknown-cost requests. Read the recorded budget/cost status and provider billing before scaling a run. Provider tariffs, cache discounts and billing can differ from a configured estimate.

Supported provider kinds are `openai_compatible`, `anthropic` and `exchange`; the actual parser is in [models.py](../src/mas/core/models.py). An exchange provider writes requests to a directory for an external agent and waits for answers; it is the generic example created by `mas init`. Choose an API adapter for a self-contained API-backed deployment.

## Sources, tools and domain data

Source configuration uses `search.sources`, `sources.cache_dir`, `sources.upload_dir`, `sources.replay_run_ids` and `evidence.mode` in `mas.toml`. Empty `sources.cache_dir` uses `MAS_CACHE` or `~/.cache/mas`. Empty `sources.upload_dir` uses `STORE/uploads`. That document-source directory is separate from candidate/measurement CSV imports, which are stored as content-addressed files in `STORE/../workbench-uploads`.

`evidence.mode = "existing_only"` reuses admitted facts or uploaded measurements. It does not import an evidence collection into a clean store. Select retrieval when a new task needs evidence services; sources lacking setup are reported as unavailable/skipped. To inspect availability without research model calls:

```powershell
.\.venv\Scripts\python.exe -m mas.cli.main --config config/examples/mas.toml sources list
```

`sources check` reports the locally synced books and upload manifest. `sources sync bookshelf --book NBK...` downloads reference material from the upstream service. `sources template` writes a literature-upload manifest under the configured document directory. A document entry declares its source, license and whether LLM ingestion is permitted; PDF text extraction additionally needs `pdftotext`. No PDF reader is required for CSV-only first use.

For drug libraries, recorded `universe*.json` files are discovered beside the store. A new workspace contains none. For carriers and general domains, use **Use own data**, select the entity type, import a real candidate CSV and its measurements, then describe the objective and conditions. [Header-only CSV files](../config/examples/) are provided as starting points. The [CSV input guide](csv-input.md) includes illustrative examples and preview corrections; the [upload implementation](../src/mas/ui/uploads.py) defines the accepted mapping and validation:

| CSV | Fields | Meaning |
| --- | --- | --- |
| Candidates | `candidate_id` (required), `name` (optional) | One row per candidate; IDs must be unique and remain text, so `001` and `1` differ. |
| Measurements | `candidate_id`, `property`, `value`, `basis` (required) | One row per observation; the ID must match the selected library exactly. |
| Measurements | `unit` | Required for numeric observations; use `1` for dimensionless quantities. Boolean/category values can have an empty unit. |
| Measurements | `conditions`, `source`, `summary` (optional) | Supply experiment/population/dose/time context, a DOI/URL/notebook/dataset source and an observation summary. Conditions can be text or a JSON object. |

Declare `basis` explicitly as `measured`, `curated`, `predicted`, `simulated` or `derived`; preserve the actual observation type. Omit missing observations rather than filling blank numbers or NaN. Zero and `false` are valid values. The preview locates duplicate IDs, unknown observation IDs, invalid values and missing units before saving a version. Modified datasets receive a new immutable identity. Upload validation covers structure and declared metadata; scientific assessment follows in the research workflow. The current importer accepts UTF-8 CSV up to 8 MB, 50,000 data rows and 64 columns per file.

MAS v1 registers source tools and domain capabilities in Python. There is no runtime `tools.toml`, `adapters.toml` or arbitrary plug-in import setting. Use the [drug registration module](../src/mas/adapters/drug/registration.py), [literature tools](../src/mas/adapters/literature/tools.py) and [uploaded-evidence adapter](../src/mas/core/uploaded_evidence.py) when extending capabilities; declarations and executable tool behavior must agree. The built-in drug adapter supplies drug identifiers and reference services; the upload path supplies generic candidate identifiers and observation properties.

## Prompts and task instructions

The browser saves the original research input and normalizes task/criterion records into English. English / 中文 changes interface display. Supply the scientific objective and constraints in the task form; the model should preserve your stated conditions and ask for essential missing information. A useful structure is:

```text
Objective: [the decision this study should support]
Candidate set: [the uploaded library selected in the workbench]
Required observations: [properties, units and conditions that must be available]
Hard conditions: [explicit conditions that determine qualification]
Preferences: [directions used to compare qualified candidates]
Evidence: [the selected collection or uploaded measurements and their sources]
```

Replace bracketed instructions with the actual research specification. This is a task-writing template, not data or a preset scientific claim.

System prompts are versioned Python source, not a separately loaded prompt TOML. Their main locations are [task normalization/investigation](../src/mas/core/investigation.py), [literature reading](../src/mas/core/reading.py), [criterion derivation stages](../src/mas/core/derivation_stages.py), and [adjudication](../src/mas/core/adjudication.py). Change them in source when developing the method and record the code/configuration identity of resulting runs. The immutable run records keep the actual model requests, role bindings and provenance needed to interpret a result.

## Optional ADMET prediction

The ADMET worker runs in a separate interpreter selected by `predict.python`, falling back to `MAS_ADMET_PYTHON` when no interpreter is configured. The core never needs to import its chemistry/ML dependency tree. Example:

```toml
[predict]
python = 'C:/Users/YOUR_USERNAME/envs/mas-admet/Scripts/python.exe'
```

Or set a process variable before launch:

```powershell
$env:MAS_ADMET_PYTHON = 'C:/Users/YOUR_USERNAME/envs/mas-admet/Scripts/python.exe'
.\.venv\Scripts\python.exe -m mas.cli.main --store var/workspace/store predict check
```

`predict check` inspects the selected environment and endpoint panel without warming a candidate library or calling a paid language model. Preparing the predictor, its weights and structure files is a separate step. The historical predictor environment recorded for the research was Python 3.11.17 with `admet_ai` 2.0.1; that record does not establish that a fresh Windows installation, Python 3.14, or every upstream predictor version is supported. The release's first-use checks validate the core on Python 3.14.2; they do not validate a freshly installed prediction environment. Prepare a separate Python 3.11 environment compatible with the chosen predictor, run its checks on the target machine and retain its actual package/endpoint metadata.
