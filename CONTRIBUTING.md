# Contributing

Start with the [architecture](docs/architecture.md) and the component page for the code you intend to change. The repository keeps scientific records separate from UI projections and explanations.

## Development setup

Follow [installation](docs/installation.md). `requirements.txt` installs the project with its `dev` extra. Build the React client with `npm.cmd --prefix web/client ci` and `npm.cmd --prefix web/client run build`.

Run the smallest relevant existing tests while working. Before a release, run the offline suite, client build and publication checks:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix web/client run build
.\.venv\Scripts\python.exe scripts/check_publication.py
```

Tests marked `live` require external services or a configured prediction environment and are excluded by default. Do not describe offline checks as provider or browser validation. Use a separate temporary workspace and port when testing startup; leave existing research services alone.

## Scientific records

- Preserve identities, versions, measurement units, evidence basis, source positions and actual cost status.
- Keep hard failures, missing observations, conflicts, unavailable interpretation and skipped evaluations distinct.
- Record corrections as new versions and results. Do not edit frozen example files to match new code or a desired rank.
- Historical reference criteria belong to evaluation, not derivation prompts. A published descriptive comparison does not become a recovery claim.
- Leave credentials, manuscripts without redistribution permission, local databases and temporary builds outside Git.

The two directories under `examples/oral-multitarget/*/results/` are frozen exports. Their original manifests record file hashes. Add a new case/version for new results, and document its input scope and comparison basis.

## Documentation

`README.md` is the English entry point; `README.zh-CN.md` links to its Chinese counterpart. Keep their navigation aligned. General usage, installation and the retained tutorial have Chinese versions. Technical component references are English.

Document implemented behavior using real functions and records. Mark partial or planned features explicitly. Include a concrete example when a component's design choice would otherwise remain abstract. Avoid copying development conversations or temporary acceptance logs into user guides.

## Releases

Use the same version in `pyproject.toml`, `src/mas/__init__.py`, and the client package/lock metadata. Bind a release tag to the verified commit and write its actual validation in `docs/releases/`. Release assets may package the frozen examples and presentation without modifying their bytes. Source availability alone does not select a software license; the repository currently has no license grant file.
