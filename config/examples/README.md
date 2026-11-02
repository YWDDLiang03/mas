# Portable configuration examples

These files provide task/configuration templates and CSV headers for your own inputs.

Use these examples for a new workspace. The recorded study retains its `deepseek-v4-flash` request identifier; the provider example uses `deepseek-flash` for new work.

- `task.library.example.json`: targets and requirements over your own named drug-library JSON, with retrieval and optional CDES choices.
- `task.original.json`: new criterion development over the public example’s saved factual inputs.
- `task.custom.example.json`: candidate and observation CSV input.
- `models.deepseek.toml`: working provider/role schema for DeepSeek. Set `DEEPSEEK_API_KEY` in the service process or enable the commented `api_key_file` after replacing its external path.
- `mas.toml`: mid workload, four candidate workers and a USD 10 run envelope. The workbench records its own resolved workflow settings when research starts.
- `candidates.csv` and `measurements.csv`: add your own rows before importing through **Use own data**. Headers alone do not form a dataset. Preserve candidate IDs, observation units, conditions, source and actual evidence basis. The [CSV input guide](../../docs/csv-input.md) ([中文](../../docs/zh/csv-input.md)) covers all accepted fields and types, illustrative examples and preview corrections.

From the repository root after installation, validate without making model requests:

```powershell
.\.venv\Scripts\python.exe -m mas.cli.main --config config/examples/mas.toml config validate
.\.venv\Scripts\python.exe -m mas.cli.main --models config/examples/models.deepseek.toml models show
```

For setup, credential handling, tool registration and the source locations of model prompts, see [installation](../../docs/installation.md) and [configuration](../../docs/configuration.md).
