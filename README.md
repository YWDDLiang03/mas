# mas

Agent-centered, self-improving multi-agent system: architecture-design handoff and reference materials.

## Start here

- [Main multi-agent audit and architecture-design prompt](MAS_MultiAgent_Design_Audit_EN_20261012/START_HERE_Audit_and_Optimize_Prompt_EN.md)
- [Package guide and reading order](MAS_MultiAgent_Design_Audit_EN_20261012/README.md)
- [Complete project brief](MAS_MultiAgent_Design_Audit_EN_20261012/Project_Brief_EN.md)
- [Concept overview](MAS_MultiAgent_Design_Audit_EN_20261012/01_Concept_Overview_EN.md)
- [Original Agentic Doping request, translated into English](MAS_MultiAgent_Design_Audit_EN_20261012/06_Agentic_Doping_Original_Prompt_English_Translation.md)

The architecture design is in [`design_audit/`](design_audit/) (canonical: [`optimized_design.md`](design_audit/optimized_design.md); build order: [`v1_scope.md`](design_audit/v1_scope.md)). The implementation of v1 is under way in `src/mas/`; see [Running the system](#running-the-system). CDES is optional.

The concrete first use case is completing the manuscript rebuttal workflow and supporting evidence-based surufatinib prioritization under the stated task and targets. The package describes proposed work and does not claim completed screening experiments or verified drug rankings.

## Included materials

The dated package directory contains the English prompts and notes, five reference PDFs, optional supplied datasets, selected Agentic Doping source excerpts, and provenance/checksum manifests. It was extracted from the validated local release without altering packaged file contents.

See the [source inventory](MAS_MultiAgent_Design_Audit_EN_20261012/04_Source_Inventory_EN.md) and [SHA-256 manifest](MAS_MultiAgent_Design_Audit_EN_20261012/MANIFEST.sha256) for origins and verification. The repository attributes preserve the package's exact file bytes across Git checkouts.

## Running the system

Requires Python 3.11+. Install in a virtual or conda environment:

    pip install -e ".[dev]"
    pytest                      # offline tests
    pytest -m live              # also checks PubChem, ChEMBL, Europe PMC, and PubMed

Create a store and a model configuration, then work through a task:

    mas --store var/store init                       # writes var/store/models.toml
    mas --store var/store task new --from task.json
    mas --store var/store criteria derive TASK       # literature → criteria (LLM roles)
    mas --store var/store review list                # hard exclusions need an expert decision
    mas --store var/store review decide ITEM --decision approve --reason "..." --exposure not_exposed
    mas --store var/store rules confirm TASK         # add --allow-pending for an exploratory run
    mas --store var/store run start TASK --seed 1
    mas --store var/store board show TASK
    mas --store var/store candidate show TASK NAME

Expert decisions are confirmed on the terminal itself and cannot be scripted.

### Settings

Every tunable number — literature breadth and depth, documents read, criteria iterations,
symbolic-regression options, spend cap, interaction mode — is a named setting with a type,
a range and a one-line explanation. Settings come from layers, lowest precedence first:

    built-in defaults → --preset quick|standard|deep → ./mas.toml (or STORE/mas.toml)
      → --profile NAME (~/.config/mas/profiles/NAME.toml) → MAS__SECTION__KEY env → --set KEY=VALUE

    mas config show --explain                 # every value, with the layer it came from
    mas --preset deep --set search.breadth=6 config validate
    mas config estimate --dimensions 5 --candidates 3177   # offline volume/cost estimate
    mas --set read.evidence_k=12 config save mylab         # keep a profile

A `mas.toml` uses the same sections, for example:

    [search]
    breadth = 6
    depth = 3
    [read]
    max_papers_full_read = 60
    [budget]
    usd_max = 20.0
    on_exhaust = "warn_continue"   # or finalize_partial | ask | abort

Each run binds the hash of its resolved settings and a record of where every value came
from; verdict-affecting values are registered as run constants. `mas run resume` refuses
if the settings changed since the run was bound, unless `--allow-config-drift` is given.

### Evidence sources

Literature is searched across every source in `search.sources`, and each query goes to
each source. A source is used only if its licence permits a language model to read its
text; that rule is checked for every task, so a refused source (OpenStax, whose books
forbid model ingestion) cannot be switched on by a setting.

    mas sources list            # sources, licences, and whether each is set up
    mas sources sync bookshelf --book NBK430685 --book NBK53196   # StatPearls, Assay Guidance Manual
    mas sources template        # start STORE/uploads/manifest.toml for your own documents
    mas sources check           # synced books; which uploads are readable and why others are not

| source | what it adds | set-up |
|---|---|---|
| Europe PMC, PubMed | peer-reviewed papers; open-access full text | none |
| NCBI Bookshelf | open-access textbooks (e.g. StatPearls); text from the NLM LitArch FTP | sync a book once |
| Wikibooks, Wikipedia | open textbooks and reference articles, read at the revision in force at the evidence cutoff | none |
| your uploads | any document you have the right to use, declared in `manifest.toml` | add files + manifest |

Research breadth and depth are settings: `search.breadth` queries in the first round,
`search.depth` rounds in all, each later round planned from what was already searched and
learned, with breadth multiplied by `search.breadth_decay`. Reading stops at
`read.max_papers_full_read` documents per dimension, or when the share of documents that
add a new topic falls below `search.saturation_stop`. Each round's numbers are recorded.

The IUPHAR/BPS Guide to Pharmacology's curated affinities (open bulk files, CC BY-SA) are
an evidence catalog entry the criteria proposer can bind a potency attribute to, alongside
ChEMBL.

### Choosing language models

Every agent role (retriever, reader, summarizer, proposer, critic) is bound to a provider in
`mas.toml` (or the older `STORE/models.toml`). API keys are read from an environment variable
or a key file at call time and are never written to any record, trace or error message.

    [providers.mine]
    kind = "openai_compatible"            # any OpenAI-compatible endpoint
    base_url = "https://api.example.com/v1"
    api_key_env = "MY_PROVIDER_API_KEY"
    model = "my-model"

    [providers.claude]
    kind = "anthropic"
    model = "claude-opus-5-5"
    api_key_env = "ANTHROPIC_API_KEY"

    [providers.subagents]
    kind = "exchange"                     # requests are answered by an outside agent
    exchange_dir = "llm_exchange"

    [providers.deepseek]                  # DeepSeek V4.1 Flash, 1M context
    kind = "openai_compatible"
    base_url = "https://api.deepseek.com"
    model = "deepseek-flash"
    api_key_file = "~/deepseek-key"       # or api_key_env; read at call time, never recorded
    thinking = false                      # extraction roles: deterministic, temperature honoured
    price_input_per_mtok = 0.30           # lets the run account its spend against budget.usd_max
    price_output_per_mtok = 1.20

    [roles]
    reader = "claude"
    proposer = "claude"
    critic = "mine"                       # a different model family makes the critique more independent
    retriever = "subagents"
    summarizer = "subagents"

With `kind = "exchange"`, the system writes each request to `llm_exchange/requests/` and waits.
An outside agent (for example a Claude subagent) answers with `mas bridge next --dir DIR` and
`mas bridge answer REQUEST_ID --dir DIR` (JSON on standard input).
