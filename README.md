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

### Choosing language models

Every agent role (retriever, reader, summarizer, proposer, critic) is bound to a provider in
`STORE/models.toml`. API keys are read from environment variables at call time and are never
written to any record.

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

    [roles]
    reader = "claude"
    proposer = "claude"
    critic = "mine"                       # a different model family makes the critique more independent
    retriever = "subagents"
    summarizer = "subagents"

With `kind = "exchange"`, the system writes each request to `llm_exchange/requests/` and waits.
An outside agent (for example a Claude subagent) answers with `mas bridge next --dir DIR` and
`mas bridge answer REQUEST_ID --dir DIR` (JSON on standard input).
