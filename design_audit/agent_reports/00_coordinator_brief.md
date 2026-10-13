# Coordinator Brief for All Workstream Subagents

Prepared by the coordinating agent on 12 October 2026. Read this fully before starting. It is the shared context for the multi-agent architecture audit; the governing instructions are the package's main prompt and project brief, which you must also read (paths below). Where this brief and the main prompt differ, the main prompt wins.

## 1. Phase rules (non-negotiable)

1. **Design only. Write no implementation code of any kind.** No scaffolding, adapters, scripts, migrations, UI code, or executable examples. Declarative material is allowed: tables, Mermaid or ASCII diagrams, state-transition descriptions, JSON/YAML *schema examples*, pseudo-interfaces written as field lists. Do not use fenced code blocks tagged `python`, `ts`, `js`, `bash`, or `sh` in your report.
2. **Do not modify any reference repository, package file, or another agent's report.** You write exactly one file: your own report (path given in your assignment). Scratch notes go under the session scratchpad only.
3. **English throughout.**
4. **Critique and propose; do not summarize the package.** Each finding must identify the issue, the supporting source or code location, importance, recommended change, tradeoff, and unresolved uncertainty.
5. **Distinguish verified from intended.** Implemented code, tests, recorded executions, plans, and scientific claims are different things. Historical "completed-work" wording in the rebuttal is a requirement to substantiate later, not a fact. Do not invent evidence, rankings, thresholds, scores, or experimental results.
6. **Record your work honestly.** End your report with a `## Contribution record` section (see §8). If you could not access a source, say so; do not label an abstract-only read as a full-text review.

## 2. Primary acceptance target (user clarification, 12 Oct 2026)

The method is an agent-centered, self-improving multi-agent system. The concrete v1 purpose, which every design decision must serve, is:

- When later implemented and run on the manuscript case, the MAS must **(a) derive a set of decision criteria (CQAs) that recovers most of the manuscript's historical CQAs, each with an evidence-linked, reasonable rationale**, and **(b) admit surufatinib onto the task-scoped leaderboard for the stated objective and five-target configuration, with a per-criterion reason for each compound**.
- The MAS assesses **each compound individually**: every candidate receives a per-criterion record (evidence, measured/predicted/missing value, pass/fail/unknown, concise reason) that rolls up into its leaderboard position and status.
- The mechanism stays general. Surufatinib is a disclosed, known reference outcome for this case, not a hard-coded answer for other tasks. The historical eleven CQAs enter as a **comparison reference artifact** (they are not enumerated in the manuscript main text, so an intake step for the authors' list is part of the design). Criteria are derived from objective and evidence; their count is whatever the evidence supports.
- Shortfalls are findings, not failures to hide: if a configuration does not recover a CQA or does not admit surufatinib, the design records that with its implications for the rebuttal wording.

Judge your recommendations by whether they make this route more credible, more traceable, and more honest.

## 3. The three layers (keep them separate in everything you write)

| Layer | Owns | Must not own |
|---|---|---|
| **Reusable agent core** | planning/delegation, proposer–critic protocol, tool brokering and result feedback, evidence ledger and provenance, criterion registry and versioning, per-candidate assessment, leaderboard lifecycle, scoped memory, run control and stopping policy, event journal and progress projection, human review queue, strategy versioning and evaluation | any pharmacology vocabulary, thresholds, target names, or a specific backend such as CDES |
| **Domain adapter** (drug prioritization v1) | vocabularies (compound identity, targets, assay endpoints, units), evidence-source and tool adapters, criterion templates, expert-validation requirements; CDES as an *optional* adapter with defined absence/failure behavior | orchestration, memory, provenance, leaderboard mechanics |
| **Case configuration** | the actual objective, candidate universe, constraints, evidence cutoff, known reference outcome disclosure, prespecified baseline and alternative configurations | anything reusable |

## 4. Shared vocabulary (use these terms exactly)

**Units of work**
- *Screening round*: one scheduled evidence/evaluation pass that produces an auditable candidate assessment or leaderboard snapshot. May include many tool calls and several agents.
- *LLM turn*: one model call. Never a round.
- *Review exchange*: one proposal→critique(→arbitration) cycle inside a round.
- *Tool retry*: re-execution of the same tool call; not a new round.
- *Human edit*: an attributed change by a person; creates a new version, may mark results stale.
- *Evidence-refresh run*: a later run triggered by new sources, data, tool outputs, or experiments, against the same task context.
- *Report revision*: a new version of a narrative report; separate from rounds and rule versions.

**Candidate states** (leaderboard): `recommended`, `provisional`, `unassessed`, `rejected`. A unique all-pass candidate under hard rules and a top-ranked candidate under a score are different results and must be named as such. An empty recommended set is valid.

**Execution states** (run/stage/step): `queued`, `running`, `waiting_tool`, `waiting_human`, `retrying`, `paused`, `failed`, `cancelled`, `completed`, `unresolved`. Reaching a budget limit yields `unresolved`, never acceptance.

**Rule semantics**: *attribute/CQA* = a property; *rule* = how that property affects inclusion, exclusion, or ordering. *Hard exclusion* ≠ *preference* ≠ *exploratory consideration*. *Missing* and *inapplicable* are distinct from *failed*.

**Evidence kinds**: peer-reviewed paper, preprint, database entry, technical report, curated measurement, model prediction, computational simulation, biochemical measurement, wet-lab observation, expert statement. A successful tool call does not validate a scientific claim. An LLM confidence statement is not a reliability estimate.

**Approval kinds**: *agent verdict* (proposer/critic/arbiter output), *software status field*, and *human scientific approval* are three different records. Never infer the third from the first two.

**Memory kinds**: *evidence* (source-linked), *tentative hypothesis*, *reusable procedure*; each is *provisional* until evaluated/approved. Agent verdicts do not become durable lessons automatically.

## 5. Preliminary architecture spine (critique it; it is not decided)

Reusable core components and one-line responsibilities:

1. **Task Context Normalizer**: flexible inputs (objective text, desired properties, evidence/data, candidate set, seeds, constraints) → explicit task context (intended outcome, candidate universe, constraints, unknowns, evaluation scope); asks only for what makes the task meaningful.
2. **Planner/Delegator**: decomposes into steps with owners (agent/tool/human), budgets, and completion criteria.
3. **Proposer–Critic protocol**: typed artifacts (evidence request, proposal, critique, revision, tool request, decision); arbiter only on persistent disagreement; bounded loops with `completed` / `rejected` / `unresolved` outcomes.
4. **Tool Broker**: declarative tool contracts, dispatch, structured results and errors returned into the next reasoning step; provider-agnostic.
5. **Evidence Ledger**: append-only, source-located claims with support/conflict, uncertainty, status, and independence markers.
6. **Criterion Registry**: versioned attributes and rules; add/revise/merge/split/remove with reasons and sources; hard exclusions separate from preferences; historical criteria stored as a comparison reference.
7. **Per-Candidate Assessor**: applies an approved rule version to each compound producing per-criterion records (evidence, value provenance, pass/fail/unknown, reason); missing ≠ failed.
8. **Leaderboard Service**: task-scoped, versioned snapshots tied to objective, rule/strategy version, evidence cutoff, ordering method; four candidate states; rank-change explanations; abstention allowed.
9. **Scoped Memory**: evidence / hypotheses / procedures, provisional vs approved, group and role scoping, content guardrails against candidate-specific "lessons".
10. **Run Controller**: execution states; distinguishes rounds, retries, human edits, refresh runs; actionable-trigger continuation; stopping criteria (sufficient support, no actionable step, diminishing gain, repeated failure, budget); checkpoints; stale/rerun propagation.
11. **Event Journal + Progress Projection**: append-only events are the source of truth; UI state is a projection; resume by replaying from a sequence number; honest indeterminate progress when denominators are unknown.
12. **Human Review Queue**: expert decisions as first-class attributed, versioned records; defines which actions need expert review and which proceed automatically.
13. **Strategy Versioning + Evaluation Harness**: policy versions, fixed evidence snapshots, held-out material, matched-budget comparisons, promotion and rollback.

## 6. Established facts (do not re-derive; cite if used)

**Case facts from the manuscript** (`references/Manuscript_TME_TLS_Ovarian_Cancer.pdf`; text extract in the scratchpad): five targets (CSF1R, VEGFR1, VEGFR2, VEGFR3, FGFR1); library of 3,171 FDA-approved or Phase III compounds; 140 predicted multi-target binders (probability > 0.9 on all five); a binary pass/fail funnel of 11 CQAs across three dimensions (oral bioavailability, metabolic stability, toxicological safety); surufatinib reported as the only all-pass compound. The individual 11 CQAs are **not listed in the main text**. Biology beyond this is out of scope; record expert dependencies instead of researching mechanisms.

**Supplied data limits** (already established in `04_Source_Inventory_EN.md`): the GDSC table has no surufatinib alias; P07post has no matched pre-treatment sample; no CDES code, checkpoints, or screening outputs are included.

**Reference-repo situation**: the five Windows-path local projects named in the prompts are not on this host. Per the user, Agentic Doping is inspected from its GitHub repository; TASTE, iDeer, self_improving_ai, and auto_research_project_vGPT are treated as outdated and replaced by newer open-source references. Clones (read-only, do not modify) in `/home/yiwei3_duke/anny/reference_repos/`:

| Repo | Path | Commit | Notes |
|---|---|---|---|
| Agentic Doping (packaged snapshot, **primary**) | `Agentic-Doping-snapshot/` | `0007ad10` (tip of `origin/cloud_deployment`, 2026-08-12) | the exact revision the package excerpts came from and the **newest** code; coordinator verified 11/11 excerpt source files and 11/11 excerpt line ranges match; 7/8 progress files match, `web/server.py` differs because it carried uncommitted local edits when packaged |
| Agentic Doping (`main`) | `Agentic-Doping/` | `7cdf6591` (2026-07-09) | default branch, 53 commits **behind** the snapshot; use only to see what changed |
| DeepSeek Harness | `deepseek-harness/` | `d7432673` (shallow) | TypeScript, "everything is a plugin", MIT, developer preview |
| ARIS | `ARIS/` | `26b95cfa` (shallow) | Markdown-skill-based cross-model proposer/reviewer loop; paper arXiv 2605.03042 |
| Darwin Gödel Machine | `dgm/` | `a565fd2d` | self-modifying coding agent with archive; ICLR 2026, arXiv 2505.22954 |

**Agentic Doping patterns already identified from the packaged excerpts** (`agentic_doping_reference/excerpts/`): source-linked claim admission (01); gap-directed retrieval (02); bounded proposal/review loop preserving `completed` / `killed` / `exhausted` (03); Anthropic-path tool-result feedback (04); provisional scoped memory (05) and outcome ≠ durable lesson (06); post-run methodology reflection (07) with content guardrails (08); append-only ledger (09); fixed-vocabulary target contract (10); explicitly deferred retraining (11). Known gaps from `07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md`: no explicit live activity events; stage-dependent progress denominators; no semantic field-level diff; `exhausted` mapped to `sent_after_revision_limit` in the trace API; rationale views lack direct evidence navigation.

## 7. Reading list (absolute paths)

Package root: `/home/yiwei3_duke/anny/mas/MAS_MultiAgent_Design_Audit_EN_20261012/`

- `START_HERE_Audit_and_Optimize_Prompt_EN.md` (governing prompt; read fully)
- `Project_Brief_EN.md` (full functional request)
- `01_Concept_Overview_EN.md`, `02_Agentic_Doping_Reference_EN.md`, `03_Provided_Rebuttal_Draft_EN.md`, `04_Source_Inventory_EN.md`, `06_Agentic_Doping_Original_Prompt_English_Translation.md`, `07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md`
- `agentic_doping_reference/excerpts/*.py.txt`, `agentic_doping_reference/SOURCE_MANIFEST.json`, `agentic_doping_reference/PROGRESS_SOURCE_MANIFEST.json`
- PDF text extracts (read-only copies): `/tmp/claude-1010/-home-yiwei3-duke-anny-mas/0ea0f6b6-dad0-4a42-b565-31a249e2401a/scratchpad/pdf_text/*.txt`

Your assignment names which of these are primary for you; skim the rest as needed.

## 8. Report format and bounds

- Length 2,000–5,000 words. Prefer tables for inventories and comparisons.
- Open with a 5–10 line summary of your top findings and the single most important recommended change.
- Findings use this template (one `###` per finding):
  - **Issue**
  - **Source / location** (file path and lines, URL with access date, or repo path and commit)
  - **Importance** (high / medium / low, with one sentence why)
  - **Recommended change** (concrete; name the component or interface it affects)
  - **Tradeoff**
  - **Unresolved uncertainty**
- Where you propose an interface, state, or record, give the field list and allowed values, not code.
- Literature reports additionally require the per-source table described in your assignment.
- End with `## Contribution record`: your agent identity as you know it, start/end time, files read (paths), repos and commits inspected, web searches run (query, date) and URLs fetched with reading depth (title-only / abstract / full text), tools used, and anything you could not access.

## 9. Coordination

The coordinator integrates all reports into the final `design_audit/` documents and owns final decisions. A cross-review wave follows: you will be asked to read one peer report and append a `## Cross-review of <report>` section to your own report (agreements, objections, proposed resolution). An independent final reviewer checks the integrated design against the main prompt's pre-handoff checklist.
