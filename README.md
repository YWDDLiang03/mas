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

## Session handoff — 2026-10-15 (read this first when picking the project up)

| what | where |
|---|---|
| **Start here: handoff recipe** — the goal, the frozen-state inventory, the five-step reproducible path to both readings (inherit the store; no re-derivation, no literature crawl), how to read a board, and every known problem | [`design_audit/HANDOFF_2026-10-15.md`](design_audit/HANDOFF_2026-10-15.md) |
| **System report** — the goal and problem list, where the project stands, the exact next commands, a reference for every module of `src/mas`, process lessons | [`design_audit/system_report_2026-10-15.md`](design_audit/system_report_2026-10-15.md) |
| **Environment** — the service-host pins and the predictor's separate environment | [`requirements.txt`](requirements.txt) |
| **Iteration log** — the bridge stall and account hold, rounds 5–10 on the case chain, every deviation and configuration change, the test log, the development log | [`design_audit/iteration_log_2026-10-15.md`](design_audit/iteration_log_2026-10-15.md) |
| **Run log** — run ids, times, outcomes, and the stage records they wrote | iteration log §1 and §3; live detail in `var/primary/store/store.db` (git-ignored) |
| **Test log** — `pytest tests/ -q` on 2026-10-15: 442 passed, 15 live deselected; `pytest tests/ -m live` for the network suite | iteration log §5 |
| **Development log** — every commit with its WHY in the message | `git log --oneline dbb0394..HEAD` |
| Previous iteration's state | [`design_audit/situation_report.md`](design_audit/situation_report.md) and [`design_audit/improvement_plan.md`](design_audit/improvement_plan.md) |

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
    mas --store var/store review adjudicate TASK     # or: resolve the queue with nobody to ask
    mas --store var/store rules confirm TASK         # add --allow-pending for an exploratory run
    mas --store var/store run start TASK --seed 1
    mas --store var/store board show TASK
    mas --store var/store candidate show TASK NAME
    mas --store var/store candidate explain TASK     # mechanism-of-action notes for the shortlist
    mas --store var/store score show TASK            # how the score was produced

Expert decisions are confirmed on the terminal itself and cannot be scripted.

### Running with nobody to ask

`mas review adjudicate` resolves open queue items without a person, so a run is not blocked by a
queue nobody will answer. It never produces an expert decision: an `hd_` is still written only by a
person confirming at a terminal, and what this writes instead is a *machine adjudication* (`adj_`)
with its own id, its own queue state and `approval_kind: agent_verdict`. It needs
`interaction.autonomous_adjudication`, which is off until `interaction.mode = autonomous` turns it
on and which cannot be on while `interaction.checkpoints` lists a checkpoint.

Which route resolves an item depends on *why* it needed an expert; `mas review list` labels every
open item with the route that would resolve it.

| why the item was raised | what happens | basis recorded |
|---|---|---|
| the cutoff restates a constraint the task context states itself | approved unchanged, citing the task-context field and version; deterministic, no model call | `task_constraint_restated` |
| `cutoff_basis: expert_set` | never approved: the rule becomes an `exploratory_consideration` and stops scoring | `no_authority_available` |
| a hard exclusion the task text does not state | demoted to a preference, so it keeps measuring and stops deleting candidates | `irreversible_without_authority` |
| proposer and critic still disagree after a revision | the `adjudicator` role decides -- blind to the proposer's rationale, on a model family neither the proposer nor the critic used where the roster has one | `dispute_adjudicated` |

The two routes that would hand an agent an expert's authority are closed, and they compose: an
upheld proposal that is still a hard exclusion is demoted anyway, and a revision may only weaken a
rule. A rule set holding any machine adjudication is `exploratory` whatever else is confirmed, its
acceptance reasons name the count ("N rules were adjudicated by an agent; no person has confirmed
them"), each entry carries its authority, and the board and the browser queue say the same.

A rule set records what entered it and what did not. `entries` are the rules that score the
board, each naming the authority behind it; `pending` are the proposals still awaiting an expert
decision; `machine_adjudicated` are the rules an agent resolved with no person confirming them;
`deferred` are rules kept out of this run on purpose, by capability. A preference rule the trigger
table admits can be in `entries` while its critic finding is still open -- that rule is also listed
in `pending_but_scoring`, and the set's `acceptance_label` is `exploratory` with a reason naming it,
so a board built on unconfirmed rules says so rather than reading as settled.

Deferring a capability is how a large universe is screened honestly. One document read serves
every literature-bound attribute for a compound, so literature cost scales per compound, not per
cell -- but a search, up to two reads and an extraction for each of several thousand compounds is
out of reach in one sitting. Screen the whole universe on the database-bound rules, then run
literature on a registered shortlist as a continuation:

    mas --store var/store rules confirm TASK --allow-pending \
        --defer-capability literature_retrieval --defer-reason "screened on database rules"
    mas --store var/store run start TASK                    # the whole universe
    mas --store var/store task shortlist TASK --top 40      # a new task, members from the snapshot
    mas --store var/store rules confirm SHORTLIST_TASK --allow-pending
    mas --store var/store run start SHORTLIST_TASK          # literature on the shortlist

The two boards are different boards, and the leaderboard's comparability key carries a hash of
the member set so they cannot be mistaken for one another. Report a candidate's rank on each,
with the rankable count beside the universe size: where no source holds a measurement, a cell is
`unknown_missing` and the candidate falls below the coverage floor, which is the honest outcome
rather than a number to fill in.

### The browser workbench

    mas --store var/store ui serve                   # http://127.0.0.1:8765/

The same read surfaces in a browser: tasks and runs, the leaderboard, a candidate's rationale
with its claim quotes and mechanism note, run progress, the review queue, the criteria pool with
lineage, and the resolved settings with the layer each value came from. Every page has a JSON
twin at `/api/...` rendered from the same data.

Three properties it keeps, each covered by a test:

* **Loopback only.** It binds `127.0.0.1` (or `::1`) and refuses any other address, because the
  surface is unauthenticated. To reach it from another machine, forward the port over SSH.
* **Read-only.** It opens the store root with no lock, so it works while a run is writing, and
  every write path is refused before SQLite is reached. Any method but GET or HEAD is 405.
* **No decisions.** A pending expert decision is shown, never made: `mas review decide` on the
  terminal is the only way to answer one. Runs are started the same way.

Keys are never rendered: a setting naming an API key shows where the key is read from, never a
value, and no page opens a key file.

### Settings

Every tunable number — literature breadth and depth, documents read, criteria iterations,
symbolic-regression options, spend cap, interaction mode — is a named setting with a type,
a range and a one-line explanation. Settings come from layers, lowest precedence first:

    built-in defaults → --preset quick|standard|deep → ./mas.toml (or STORE/mas.toml)
      → --profile NAME (~/.config/mas/profiles/NAME.toml) → MAS__SECTION__KEY env → --set KEY=VALUE

    mas config show --explain                 # every value, with the layer it came from
    mas --preset deep --set search.breadth=6 config validate
    mas config estimate --dimensions 5 --candidates 3177   # offline volume/cost estimate
    mas --set read.max_papers_full_read=60 config save mylab         # keep a profile

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

### Deriving criteria: the pool workflow

`mas criteria derive TASK` runs one *round* of an iterative workflow and records it as a
run. It searches and reads (breadth × depth), then:

1. **propose** — every distinct criterion the evidence supports goes into a pool, recall first;
2. **filter** — deterministic checks (already registered, no supporting claim, unbound
   evidence request), then a blind critic on its own model queue;
3. **distill** — each candidate is sharpened into its most precise, measurable form;
4. **merge** — candidates measuring the same quantity (same capability, unit, direction and
   subject parameters; or, where a candidate names no subject, overlapping wording) are
   offered to an adjudicator, which may merge them. Two candidates that are one measurement
   from two databases merge into one attribute declaring a route to each (`evidence_requests`),
   whose values are pooled under its aggregation;
5. **refine** — items with validator problems or critic findings are revised or withdrawn.

Steps 2–5 repeat up to `criteria.inner_iterations` times and stop early once the pool
stops changing for `criteria.stall_rounds` iterations. Survivors are then promoted into the
registry as *proposed* criteria: items with open critic findings go to the review queue as
disputes, and hard exclusions or expert-set cutoffs still need an expert decision.

Every pool change is recorded with its reason and evidence, and items keep their identity
across versions, merges and rounds. Continue in a later round — with new evidence, a
different model, or deeper settings — and the pool picks up where it stopped:

    mas criteria derive TASK                         # round 1
    mas criteria derive TASK --continues RUN_ID      # round 2, same chain
    mas criteria pool TASK [--all]                   # states, versions, merges

### Scoring

By default the leaderboard score is a weighted percentile over the confirmed preference
criteria. With `sr.mode` set, the run also tries to *derive* the score: the proposer chooses
which already-assessed features belong in it, what transformation each deserves, which
direction every term must push, and a prior magnitude where it can cite one; the numerics
stay small enough to check by hand (least squares on standardised columns, shrunk toward the
model's prior instead of toward zero, solved by Gaussian elimination, refusing a constant
column or an ill-conditioned design). Terms come from a fixed grammar — `x`, `log1p(x)`,
`1/(1+x)`, `x²`, `x·y`, `hinge(x, c)`, `z(x)` — at depth 1 and at most `sr.max_terms` of them,
proposed as structured JSON, never as an expression string to evaluate.

    mas --set sr.mode=potency --set rank.method=symbolic_expression run start TASK
    mas score show TASK            # the expression, its fit, and how it did on the holdout
    mas candidate show TASK NAME   # that candidate's terms by contribution, with the claims behind them

Two modes: `potency` regresses the median pChEMBL of a required target on descriptor and
record-field cells, and `leaderboard_score` reproduces the weighted-percentile score from the
confirmed preference values. Nothing new is fetched — the features are cells the sweep already
assessed.

**How missing evidence affects a score, which you need when reading any board.** A cell with no
usable value leaves both the numerator and the denominator: it is never surrogate-filled, and it
never counts as a failure. The score is therefore the mean desirability over the rules a
candidate *was* evaluated on, and completeness is reported beside it as coverage rather than
folded into it. The consequence is worth stating plainly: a compound measured only where it
happens to look good can outrank a thoroughly characterised one, because the coverage floor is a
gate, not a gradient. Compare ranks at similar coverage, and read `coverage` on every row. Where
completeness itself should count, it belongs in a criterion that measures it -- "how many of the
required receptors have a measured rather than a predicted value" is an attribute, and once
confirmed it enters the score like any other.

What the numbers are protected by, and why the default is still the percentile score:

- the candidates are split three ways by hash (**train** fits, **select** compares generations,
  **holdout** is looked at once), so more generations cannot buy a better result;
- every reference outcome is excluded from all three splits and scored only once the
  expression is frozen;
- the proposer sees feature names, definitions, units, directions, coverage counts,
  training-split quartiles and the previous generations' aggregate diagnostics — never a
  per-candidate row, never the target column, never the reference compound;
- anything derived from the target is refused before it is offered, including a prediction of
  the same target and any feature whose fitting-row ranking *is* the target's;
- a fitted coefficient whose sign contradicts the direction the model declared rejects the
  expression, a hinge constant must be a quartile that was shown or a value in a cited claim,
  and a blind critic runs symmetric scrutiny on the terms and priors;
- a term is called `mechanistic` only when the claims it cites exist, were admitted and had
  their spans verified; otherwise it is `associational`. Both are allowed in the score.

The expression is adopted only if it beats the weighted-percentile baseline by
`sr.min_improvement` on the holdout, measured as rank agreement with the target. Otherwise the
baseline keeps the ranking and the attempt is recorded anyway, with every rejected expression
and every generation's diagnostics. An adopted expression is registered as the rule set's
ordering method before any snapshot is published, which makes the rule set *exploratory* —
the ranking rule was chosen after seeing results — and raises a `rule_set_version` item for an
expert to confirm. Where a target has too few usable rows to fit, the model's cited
coefficients are used directly and the expression is recorded as `expert_prior`; it faces the
same holdout gate.

### Mechanism of action

A score says where a compound ranks, not how it acts. The mechanism-of-action note is a separate
artifact per candidate and enters no score, verdict, rank, coverage figure or comparability key —
nothing downstream reads it, and no module in the decision path can even import it.

    mas candidate explain TASK            # the ranked shortlist (rank.top_n, or --top N)
    mas candidate explain TASK NAME       # one candidate
    mas candidate show TASK NAME          # prints the note once it exists; never writes one

It runs **on demand for a shortlist**, not in the sweep: the sweep covers thousands of candidates
and a model call each would be indefensible for a block no decision depends on — and because
nothing depends on it, writing it later costs the run nothing. It is written once per candidate
per run and is idempotent on a second pass: an existing note is returned with no model call.

The `summarizer` is given only this candidate's claims that were *admitted* and had their *spans
verified against the source*, and answers with sentences each carrying the claim ids it rests on.
A deterministic gate then re-checks every sentence and **drops** — never repairs — any it cannot
stand behind:

- each cited claim must exist, be admitted, have a verified span, and tie that span to this
  candidate (the quote names it, or, for a database record field whose quoted value names
  nothing, the identifier the record was found by);
- every mechanism word the sentence uses must appear in the text of a claim it cites;
- a sentence that mentions a score, rank, coefficient or percentile is dropped whatever it cites.

If no sentence survives, the block records `unexplained` rather than an empty or invented
narrative, and every dropped sentence is kept with the reason it fell. Curated ChEMBL
mechanism records ground sentences beside literature claims — their value is the categorical
statement that engagement is documented, their action type and mechanism text come from the
record's `conditions`, and their references (PubMed ids, FDA and EMA labels) are printed with the
sentence so a reader can follow them.

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
