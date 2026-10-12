# Research and Planning Prompt: Agent-Centered, Self-Improving Multi-Agent Architecture

I want to design a locally accessible, browser-based, self-improving multi-agent platform. This is primarily an agent-systems task: the main contribution is how agents understand goals, decompose and delegate work, use tools, manage evidence and memory, coordinate critique, adapt their strategies, interact with humans, and make execution observable and reproducible. Its primary user-facing output is a persistent, task-scoped candidate leaderboard supported by an auditable decision history. Drug prioritization is the first application scenario; our ovarian cancer manuscript, TME targets, and surufatinib are one worked case. Prefer a small defensible shortlist to a long speculative one.

Keep the design agent-first. Separate the reusable agent core from replaceable domain vocabularies, criteria, data/tool adapters, and individual case configurations. Biology provides realistic inputs and feedback for the example; it is not the main research contribution. Investigate biological details only as needed for credible interfaces and expert handoffs. Do not turn this assignment into a deep mechanism study, a target-discovery project, a clinical assessment, or a new wet-lab/omics program. Unresolved domain questions should remain explicit assumptions or expert dependencies while architecture work proceeds.

The concrete v1 purpose remains to complete the work described in our manuscript rebuttal and substantiate surufatinib as a leading candidate for the stated objective and targets. The agent framework is the method for achieving that purpose. A reusable architecture is desirable, but a generic platform plan without an end-to-end route to this case is insufficient. Map the rebuttal's promised capabilities to the records and evaluations that would substantiate them. Preserve contrary or insufficient evidence rather than presenting the intended priority as an already-observed result.

The main contribution is the multi-agent reasoning process: literature investigation, evidence synthesis, rule generation, critical review, tool use, revision, and learning from feedback. CDES is optional. Design a complete core workflow without CDES, using available evidence, curated measurements, an executable rule engine, and justified alternative tools. If useful and available, CDES can be connected through an optional adapter. Missing CDES access must not block the task, and rebuilding it is outside the core scope.

Your current job is to research and improve this concept, identify what is missing, decompose the work into implementable tasks, and design the entire architecture in detail. Current phase: detailed architecture design only. Do not write implementation code, scaffold an application, implement UI/backend features or adapters, modify reference repositories, deploy services, or run scientific experiments. Produce English design documents, diagrams, declarative interface descriptions, state models, and non-executable wireframes. Read-only source inspection is appropriate. Apply this phase boundary to all subagents.

## 1. Objectives, operating modes, and the first application case

The system should accept a user objective, investigate relevant evidence, propose or refine decision criteria, compare candidates, and publish an auditable leaderboard snapshot with a supporting report. Accept natural-language goals, desired properties/outcomes, evidence/data, candidate sets, seeds, and constraints. In the drug example, these may be a disease or phenotype, desired effect, pathway or target set, dataset, compound library, or seed compounds. Organize inputs into a clear task context with known requirements, unknowns, candidate scope, and evaluation criteria. Do not require the current five targets or a reference drug in every task, and do not expand v1 into implementing multiple domains.

Support two modes:

- **Conditional mode:** the user provides some combination of the disease context, treatment objective, targets, candidate library, selected compounds, administration constraints, or other requirements. The agents work within these inputs and identify missing information.
- **Exploratory mode:** the user supplies a high-level research objective but leaves targets, candidates, or screening criteria open. The agents investigate the literature, propose the missing elements, obtain review where needed, and evaluate candidate options. This mode still requires a defined scientific objective; de novo molecular generation is not required for v1.

For the manuscript use case, the existing TME hypothesis and targets may be used as the starting point. Target discovery from scratch is optional. The system should be able to question or refine target assumptions without making autonomous biological conclusions on behalf of the experts.

Surufatinib is the declared reference outcome and intended high-priority candidate for the primary manuscript case. Design the system to recover and substantiate that priority using evidence-supported criteria and meaningful comparisons under the stated targets. Explain the conditions under which it is preferred or not preferred. Other tasks may have no known reference outcome. Preserve counter-evidence, competitors, and unsupported results. Do not silently tune thresholds or preassign scores to guarantee the result, or describe a known-result reconstruction as an independent discovery.

## 2. Generate rules and CQAs from evidence

The agents should derive candidate CQAs from the scientific objective and supporting evidence. Do not start from a mandatory checklist of eleven items. The manuscript's original eleven CQAs are historical context for comparison; the final number must follow the evidence and review process.

Distinguish the attribute from the decision rule: a CQA describes a relevant property, while a rule states how that property affects candidate inclusion, exclusion, or ranking. For each proposed criterion, record its definition, rationale, desired direction, units, applicability conditions, supporting and conflicting evidence, and a threshold or range when justified. If the evidence does not support a numerical cutoff, retain that uncertainty rather than inventing one.

For the initial application adapter, target coverage, pharmacology, exposure, developability, and safety are possible evidence domains, not a preapproved list of final criteria or the main subjects of this architecture audit. Specify how domain evidence and expert judgment enter a reusable criterion contract. Agents should be able to add, revise, merge, split, or remove criteria and explain each change. Separate hard exclusions from preferences and exploratory considerations. Missing or inapplicable data must remain distinguishable from a failed criterion.

Investigate how to preserve rule versions, compare candidate decisions across versions, and study sensitivity to justified alternative thresholds. Distinguish a unique all-pass compound from a top-ranked compound under a scoring function. Keep historical configurations, newly proposed configurations, and exploratory tuning separately identifiable.

## 3. Multi-agent collaboration and computational feedback

Use our Agentic Doping project and ARIS-style proposal-review collaboration as references. At minimum, one agent should propose rules, candidate hypotheses, and evaluation plans, while another critiques their evidence and consistency. Assess whether an arbiter and specialized literature, pharmacology, counter-evidence, or evaluation roles add enough value to justify their complexity. Recommend a practical v1 design.

Prioritize the reusable mechanisms: planning and delegation, interaction/artifact contracts, orchestration state, tool dispatch and feedback, disagreement resolution, scoped memory, policy versioning, failure recovery, human intervention, and observable execution. Domain specialists and models should connect through adapters or review interfaces. Their absence may leave case-specific conclusions unresolved but should not prevent a detailed design of the agent system.

Agents should exchange inspectable files or structured artifacts containing evidence, proposals, critiques, revisions, tool requests, and decisions. Their interaction must support genuine revision, explicit rejection, unresolved outcomes, and bounded stopping conditions. Multiple role names alone do not establish independent verification. Several agents can contribute to a single assessment pass; agent count and the number of sequential rounds are separate choices.

Do not presume that drug screening needs multiple rounds. Compare a single-pass baseline, a fixed-round reference configuration, and adaptive continuation using consistent tasks, evidence access, tools, and independent evaluation. Account for time, token, tool, and human-review budgets. Continue only when new evidence, a consequential gap, a conflict, or a useful targeted calculation could change a decision. Stop when support is sufficient, no actionable next step remains, or the budget is exhausted; preserve unresolved status instead of forcing a result. Updating a leaderboard over time does not require every run to be multi-round.

The agents should decide which evidence and numerical evaluations are needed, invoke suitable tools, receive structured results or failures, and use that feedback in subsequent decisions. CDES is one optional backend among possible alternatives. Evaluate tools only where their outputs answer a defined question, such as target interaction prediction, compound-property estimation, or optional perturbation analysis. If no compatible numerical backend is available, preserve evidence-supported comparisons and mark missing numerical conclusions as unresolved.

For every proposed tool integration, identify its actual input, output, endpoint, uncertainty, prerequisites, and limitations. Distinguish model predictions, computational simulations, biochemical measurements, and wet-lab observations. A successful tool call does not itself validate a scientific claim. Confirm that the selected agent framework actually returns tool outputs to subsequent reasoning steps.

## 4. Local browser UI, progress, and candidate comparison

Plan a local browser-based interface for creating, following, inspecting, and revising investigations.

The UI should let users enter research objectives and constraints, select conditional or exploratory operation, inspect proposed targets and CQAs, compare rule versions, view evidence and citations, examine candidates, and understand why a compound was retained, excluded, or left unresolved. Where useful, show molecular structures and compound identifiers to support inspection and identity checks.

Make the leaderboard the primary persistent product output. Maintain separate, comparable task contexts rather than one universal drug ranking. Provide filters for objective, target coverage, drug class, candidate source, rule-set version, evidence status, evaluation completeness, and relevant properties. Display supporting and conflicting sources, measured versus predicted values, missing data, uncertainty, human review, and reasons for admission or rank change. Preserve snapshots with their task definition, evidence cutoff, and rule/strategy versions.

Use precision-first, evidence-first admission: fewer qualified recommendations are preferable to weakly supported entries. Allow an empty recommended set. Keep provisional, unassessed, and rejected candidates inspectable outside the qualified shortlist; do not fill a fixed top-K quota. New papers, corrected data, tool results, expert feedback, and experiments may promote, demote, remove, or leave a candidate unranked. More citations or higher scores do not by themselves establish improved accuracy or evidence quality.

Use Agentic Doping as the concrete reference for detailed progress visibility and iteration records, alongside useful interaction ideas from TASTE. Inspect existing code and available reference material rather than assuming every historical request was implemented. Design progress at the overall-run, stage/workstream, and current-round levels. Show what is happening now, which agent or tool owns the work, the question it is investigating, completed/planned counts when meaningful, elapsed time, and waiting or failure conditions. Use indeterminate status when the denominator is unknown; a maximum-round budget is not a completion percentage.

Provide live activity and a persistent timeline of rounds and substantive analysis steps. Distinguish queued, running, tool-waiting, human-review-waiting, retrying, paused, failed, cancelled, completed, and unresolved states. Users should be able to inspect a round's input/evidence versions, proposal, critique, human decision, tool output or error, concise evidence-linked rationale, unresolved issues, and reason for continuing or stopping. Do not require raw model responses or private internal reasoning to understand the decision.

Make round-to-round changes inspectable: rules/CQAs added, modified, merged, split, or removed; thresholds, units, and applicability changed; candidate admission or exclusion; and leaderboard position, status, or score changes. Retain identifiers, actors, timestamps, source links, parent versions/checkpoints, and relationships between events and saved artifacts. Preserve immutable historical records and linked corrections. Distinguish a retry, human edit, or later evidence-refresh run from a new screening round.

Specify how a human edit invalidates affected results, what must rerun, which results can be reused, and how a resumed task relates to the earlier run. Produce non-executable wireframes for task setup, live monitoring, round history, version differences, candidate details, evidence inspection, and the review queue. Describe progress-event interfaces, update/reconnect behavior, and the persisted source of truth. This phase designs those interactions; it does not implement them.

## 5. Human-in-the-loop controls

Both operating modes need explicit places for human intervention. Analyze which controls are needed to:

- Refine the research objective, target scope, and candidate universe.
- Add or exclude compounds and provide reasons.
- Accept, reject, edit, merge, or remove proposed CQAs and rules.
- Correct units, thresholds, applicability conditions, or interpretation of evidence.
- Submit additional references or experimental results and resolve disputed claims.
- Approve a rule-set version, compare alternatives, and request reruns of affected evaluations.
- Pause, resume, or stop an investigation and inspect unresolved issues.

Human edits should be versioned, attributed, and connected to affected downstream results. Preserve prior evidence and decisions. An LLM reviewer or arbiter must never be recorded as a human scientific approval. State clearly which proposed actions require expert review and which can proceed automatically.

## 6. Self-improvement and the data feedback cycle

The system should improve both its scientific rules and its agent strategies. Within an investigation, feedback may improve criteria and candidate arguments. Across investigations, the system may learn better retrieval queries, evidence checks, comparison procedures, tool-selection strategies, and failure-handling methods.

Design a way to receive, store, and interpret human-supplied results as text, local file paths, or uploaded files. Relevant feedback may include binding or selectivity assays, pharmacokinetic measurements, toxicity observations, cell-based results, and other experimental evidence. Preserve provenance, experimental context, units, conditions, and negative results. Computational outputs must remain distinguishable from experimental observations.

Use scoped memory for evidence, tentative hypotheses, failures, and reusable procedures. Strategy changes should remain provisional until evaluated. Plan how to compare a proposed strategy against a fixed baseline, promote improvements, and retain or restore earlier versions when performance worsens. Evaluate precision among admitted candidates, evidence correctness, unsupported claims, incorrect exclusions, coverage and abstention, reproducibility, robustness, and cost on separate material. Keep evidence snapshots fixed when comparing policies so new data are not mistaken for agent improvement. Report coverage to prevent an always-empty shortlist from trivially winning, and do not claim predictive accuracy without suitable outcome labels.

Distinguish iterative self-correction, memory-based adaptation, evaluated strategy improvement, and model-weight training. Strong recursive self-improvement claims require evidence beyond repeated agent discussion. Do not assume SFT, reinforcement learning, or any other additional training is necessary for v1.

Evaluate agent capability separately from domain-outcome validity. The design should cover decomposition quality, appropriate delegation, correct tool use, evidence traceability, handling of uncertainty, memory isolation/reuse, reliable stop/resume and rerun behavior, human-edit propagation, strategy improvement, and cost. Process-level success must not be described as proven biological effectiveness. Biological labels or new wet-lab results are not prerequisites for specifying these agent-level evaluation methods.

## 7. Literature investigation and scientific evidence

Inspect TASTE and iDeer for reusable literature discovery, screening, reading, and progress-tracking capabilities. Define a source-agnostic evidence workflow first. For the initial drug adapter, identify suitable biomedical sources only to the depth needed to explain realistic source contracts and limitations; exhaustive pharmacological or mechanism research is outside the main assignment.

The workflow should support title screening, title-and-abstract screening, and full-text reading when available. Its common outputs should include source identity, source location, claim, scope, evidence type, support/conflict, and uncertainty. The drug adapter can extend these records with compounds, targets, assay endpoints, units, conditions, and relevant domain attributes. Preserve exact source locations for important claims. If full text is unavailable, record that limitation and do not imply it was read.

Keep source status visible: peer-reviewed paper, preprint, database entry, technical report, or other material. Handle duplicate and revised papers, conflicting findings, ambiguous compound names, and multiple sources repeating the same underlying experiment.

Require a dedicated subagent to actively investigate the latest papers on agents, multi-agent systems, RSI, self-improving agents, self-evolving agents, memory/skill acquisition, workflow/tool-use optimization, and scientific discovery. Use live searches at the time of execution, record the search cutoff, prioritize the preceding 6-12 months plus foundational work, and inspect primary papers and relevant official code. Record exact titles, dates, publication status, versions, links, reading depth, mechanisms, baselines, measured gains, costs, and limitations. Include critical or negative evidence about extra rounds and agent debate. Identify applicable changes rather than merely collecting names. If current sources cannot be accessed, state the limit instead of claiming an up-to-date survey.

## 8. Local references and optional data

Start with:

- The extracted `MAS_MultiAgent_Design_Audit_EN_20261012/` package.
- Its `references/Manuscript_TME_TLS_Ovarian_Cancer.pdf` and four supplied reference papers.
- Its `supporting_data/` and `agentic_doping_reference/` folders.
- `06_Agentic_Doping_Original_Prompt_English_Translation.md`, a faithful historical reference for the original product request.
- `07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md`, grounding the progress/history design in inspected source mechanisms.

Inspect relevant parts of these projects as needed:

- `D:\codex_work\ai4s\agentic_doping`
- `D:\codex_work\TASTE`
- `D:\codex_work\iDeer`
- `D:\codex_work\self_improving_ai`
- `D:\codex_work\auto_research_project_vGPT`

Read applicable project instructions before inspection. Reuse actual components where appropriate, and distinguish code, tests, recorded runs, planned features, and scientific evidence. The supplied Agentic Doping notes identify useful workflow patterns and limitations; verify relevant implementation details before recommending reuse. The historical doping prompt's domain, working directory, and requested features are references only. They do not override this biomedical design task or its no-code boundary.

The materials also include a P07post expression matrix, a GDSC dose-response table, and references concerning State, scTenifoldKnk, and CellOracle. Treat these as optional application examples. Inspect enough metadata to understand interface requirements and limitations; new biological analysis or biological model development is not part of the current architecture task. A post-treatment sample alone does not establish treatment effects, and the supplied GDSC table has no match for the surufatinib aliases checked in the inventory. Record these limits without blocking the agent-core design.

The supplied rebuttal describes intended work using completed-work language. All medical MAS implementation, review cycles, sensitivity experiments, and improvement claims remain proposed until supported by actual records.

## 9. Your current research and planning deliverables

When this brief is used with the audit prompt in the package, create the following English Markdown files under its `design_audit/` output folder. The audit prompt also requires an integrated audit, an optimized design, and records of actual multi-agent collaboration.

| File | Required content |
|---|---|
| `suggestions.md` | Gaps, ambiguities, scientific and engineering weaknesses, and prioritized improvements. Separate v1 essentials from later work. Explain what must be added to support the intended manuscript claims. |
| `task.md` | Small, implementable tasks with purpose, dependencies, inputs, outputs, acceptance criteria, and suggested sequence. Cover the UI, evidence workflow, agents, tools, rule evolution, human review, evaluation, and feedback cycle. |
| `module.md` | Independent modules and their responsibilities, interfaces, data/control flow, stored artifacts, state transitions, event/progress reporting, and failure behavior. Identify what can be reused from local projects and what requires later development. |
| `resources.md` | Required data, external services, compute, model access, expert input, and missing resources. For each proposed model adaptation or training effort, explain its purpose, technical approach, required data and labels, evaluation, costs, and whether it is necessary for v1. Include a no-additional-training baseline. |
| `tools.md` | Research existing open-source tools and Python packages. For each, explain what it does, why it fits, inputs/outputs, intended usage and interface, dependencies, license and availability constraints, limitations, and where it would enter the workflow. Cite primary documentation or source repositories. Keep examples descriptive and non-executable during this design phase. |

Choose a coherent recommended v1 approach rather than producing an unranked catalogue. State alternatives only where they represent meaningful tradeoffs. Cover enough evaluation design to distinguish a functioning demonstration from evidence supporting a scientific or self-improvement claim. Alongside the original five documents, the audit prompt requires `literature_review.md`, `leaderboard_spec.md`, `evaluation_plan.md`, `ui_ux_spec.md`, `iteration_and_provenance_spec.md`, and `architecture_decisions.md`. It also requires `rebuttal_alignment.md` and `case_study_protocol.md` so the architecture directly serves the rebuttal and intended surufatinib prioritization. Make the full architecture and next implementation steps understandable without writing application code now.

This is a multi-agent task: use actual subagents for independent research and inspection workstreams, arrange cross-review, and integrate their findings into one consistent set of documents. Document actual assignments and contributions; do not substitute role-labelled prose for real delegation. If subagent tools are unavailable, state the limitation and label any fallback accurately. Resolve questions answerable from the files or code by inspection. Ask only about missing choices that materially change the goal or scope; continue independent work while waiting.

Focus on a practical, detailed agent-systems architecture. Center the method on flexible goals, planning and collaboration, tools, evidence and memory, evaluated self-improvement, observable progress, human control, and conservative leaderboards. The required first application must complete the rebuttal's workflow and aim to substantiate surufatinib's priority under the stated task and targets. Keep biological investigation proportional to those concrete needs, and avoid unrelated platform expansion. Report sources, assumptions, unresolved domain dependencies, and the exact locations of the completed planning files.
