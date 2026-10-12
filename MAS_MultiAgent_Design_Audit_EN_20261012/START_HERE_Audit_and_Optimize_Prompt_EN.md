# Multi-Agent Assignment: Audit and Optimize an Agent-Centered System Architecture

You are the coordinating agent for a research and design audit of an agent-centered, self-improving multi-agent system. The core concerns are task understanding and decomposition, collaboration, tool use, evidence handling, memory, adaptive execution, evaluated strategy improvement, human interaction, and observable, reproducible decision-making. Biomedical drug prioritization is the initial application scenario used to exercise this architecture.

**This is a multi-agent task. Use actual subagents to conduct the audit and optimize the design. The product being designed is also a multi-agent system.** Your deliverable is a coherent, evidence-supported design and implementation plan, not the complete application.

**This is primarily an agent-systems design task. Biology is an application context, not the main research contribution.** Put the main effort into the agent architecture, interaction protocols, runtime and memory design, self-evolution mechanism, evaluation, observability, and UI. Investigate domain details only to the extent needed to specify realistic inputs, outputs, evidence standards, tool boundaries, and expert handoffs. A deep biological mechanism study, new target discovery, clinical argument, or wet-lab program is not required to complete the architecture. Preserve domain uncertainty and source quality rather than treating unverified assumptions as established facts.

**The final purpose remains the manuscript rebuttal and the surufatinib prioritization task.** Agent-system design is the methodological focus; delivering the capabilities and evidence described in the rebuttal is the concrete v1 purpose. The intended case outcome is to substantiate surufatinib as a leading candidate under the stated objective and target configuration. Reusability is valuable, but an abstract general platform that cannot complete this case is not an adequate design. Translate the rebuttal into capabilities, required records, experiments to be conducted later, and acceptance criteria. Actual rankings must come from traceable evidence and evaluation; preserve and investigate any failure to support the intended outcome rather than reporting it as achieved.

**Current phase: detailed architecture design only. Do not write implementation code.** Produce a complete, understandable system blueprint before development. Do not scaffold the application, implement frontend or backend features, modify the reference repositories, write executable adapters or migrations, deploy services, or run scientific experiments. Read-only code inspection and source research are appropriate. Use English prose, tables, diagrams, state-transition descriptions, declarative interface specifications, and non-executable wireframes to make the architecture concrete. This restriction applies to every subagent as well as the coordinator.

Work in English throughout: research notes, subagent assignments, reports, design documents, and the final handoff.

## 1. Establish the current objective

Read the package README, `Project_Brief_EN.md`, `01_Concept_Overview_EN.md`, `02_Agentic_Doping_Reference_EN.md`, and `04_Source_Inventory_EN.md`. Also read `06_Agentic_Doping_Original_Prompt_English_Translation.md` for the original interaction requirements and `07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md` for grounded progress/history reference points. Inspect relevant manuscript sections and source excerpts. Treat the original rebuttal and translated doping request as historical context; the current prompt determines the task, output directory, and no-code phase.

The intended contribution is an evidence-driven MAS that understands a user objective, plans and delegates work, develops task-appropriate decision criteria, uses tools, checks results, and maintains a selective candidate leaderboard with a traceable decision history. Its policies can be revised and evaluated over time. The ovarian-cancer/TME study and surufatinib are one worked case of the reusable architecture and the required first acceptance case. Aim to recover and support surufatinib's high-priority position for this objective and target configuration, with clear evidence for the criteria and candidate comparison. This is a disclosed, known-outcome study, not a claim of blind discovery. Surufatinib must not become the fixed answer for unrelated tasks. Keep competing candidates and contradictory results visible.

Allow flexible entry points: a natural-language objective, desired properties or outcomes, supplied evidence/data, a candidate set, seed candidates, constraints, or combinations of these. In the initial drug scenario, these may be expressed as a disease or phenotype, desired effect, pathway, target set, compound library, or seed compounds. Normalize them into an explicit task context containing the intended outcome, candidate universe, known constraints, unknowns, and evaluation scope. Ask only for missing information necessary to make the task meaningful. Do not hard-code the current five targets, drug, disease, or data modalities. Use a small set of realistic cases to test the design; do not expand this phase into implementing many domains.

Make three layers explicit: (1) a reusable agent core for orchestration, evidence/provenance, memory, policy revision, progress, human review, and leaderboard lifecycle; (2) a replaceable domain adapter for task-specific vocabularies, criteria, data, tools, and expert validation; and (3) a case configuration defining the actual objective, inputs, constraints, candidates, and available evidence. CQAs are the initial scenario's decision attributes, not a reason to embed pharmacology assumptions throughout the agent runtime.

Derive CQAs from the objective and evidence. Their number is not fixed at eleven. Existing biological hypotheses and targets may provide the starting point; discovering targets from scratch is optional. Scientific human review remains separate from automated review by an LLM.

**CDES is optional. Design a complete core workflow without CDES.** Assess CDES only as one possible adapter if it is useful, available, and compatible with the selected task. A missing CDES implementation must not block this assignment. The no-CDES design can use literature evidence, curated measurements, an executable rule engine, and justified alternative tools. Missing measurements remain unknown; evidence-only comparisons must not be presented as measured affinity or completed numerical validation.

These current requirements supersede assumptions in the historical manuscript or rebuttal.

Create a direct rebuttal-to-design mapping. Cover evidence-supported rule/CQA generation, critic/arbiter revisions, genuine expert review, numerical-tool feedback, candidate-level decisions, sensitivity to alternative configurations, and a conditional statement of the final prioritization. The historical claims of completed work are requirements to substantiate later, not current facts. If the evidence-derived CQA count differs from eleven, or a configuration does not prioritize surufatinib, record the difference and its implications for the eventual reply. Do not impose artificial rounds, undocumented thresholds, or preassigned scores to manufacture those records.

## 2. Organize real multi-agent collaboration

Delegate the following six workstreams to subagents, using parallel execution where dependencies permit. If concurrency is limited, run them in waves. Give each subagent a bounded scope and its own report file. Keep integration and final decisions with the coordinating agent. Multi-agent collaboration and the number of sequential screening rounds are separate design choices: multiple agents can contribute to a single-pass assessment.

| Workstream | Responsibility | Report |
|---|---|---|
| Evidence and decision-policy auditor | Audit source extraction, criterion generation, provenance, uncertainty, counter-evidence, and decision consistency at the agent-system level. Use CQAs as a bounded example and identify the interface for domain expert judgment. | `agent_reports/evidence_and_policy.md` |
| MAS architecture and reuse auditor | Inspect proposer-critic-arbiter interaction, file-based artifacts, tool feedback, memory, versioned round records, and reusable Agentic Doping components; specify the architecture without implementing it. | `agent_reports/mas_architecture.md` |
| Tools and data auditor | Design reusable tool contracts, dispatch, result/error feedback, optional adapters, resource needs, and any justified training requirements. Scope biomedical investigation to exercising these interfaces and the no-CDES case. | `agent_reports/tools_and_data.md` |
| Human-review and UI auditor | Inspect Agentic Doping's progress and iteration views; design detailed progress bars, live activity, per-round evidence and differences, flexible input, the leaderboard, human interventions, and rerun behavior. | `agent_reports/human_review_and_ui.md` |
| Evaluation and self-improvement auditor | Compare single-pass and adaptive multi-round policies; design separated evaluation, precision-first admission, strategy promotion, rollback, and evidence needed for improvement claims. | `agent_reports/evaluation_and_improvement.md` |
| Current agent and self-evolution literature investigator | Independently search and read the latest relevant agent, multi-agent, RSI, self-improving, and self-evolving research; identify supported mechanisms, evaluation weaknesses, and applicable design changes. | `agent_reports/current_agent_literature.md` |

Have subagents critique the existing design and propose concrete improvements, not merely summarize the package. Each report should identify the issue, supporting source or code location, importance, recommended change, tradeoff, and unresolved uncertainty. Subagents should not overwrite one another's reports or the shared final documents.

Arrange a cross-review between relevant workstreams, then assign an independent final reviewer to check the integrated design. Record actual subagent identifiers and assignments when available, reviewed artifacts, disagreements, and resolutions. Do not simulate multiple reviewers by writing role-labelled paragraphs yourself. If the environment provides no subagent capability, disclose that limitation and provide a clearly labelled single-agent fallback; do not claim a multi-agent review occurred.

## 3. Audit the agent's evidence-to-decision process

Examine how the system translates a user objective into tasks, evidence requests, decision attributes, and rules. Specify the common criterion contract: definition, rationale, units where applicable, direction, applicability, supporting and conflicting sources, and a justified cutoff or uncertainty range when available. Check how qualitative, missing, conflicting, and inapplicable evidence affects decisions. Domain-specific values and scientific validity should come from authoritative evidence, suitable tools, or expert review; the architecture audit need not establish new biological conclusions.

Evaluate conditional operation with user-supplied constraints and exploratory operation with a high-level objective. Both need a defined candidate universe and traceable scope, but they must not require the current manuscript's targets or a known winning compound. De novo molecule generation and virtual-cell modeling are optional extensions, not v1 prerequisites.

Identify how rules are added, revised, merged, split, or removed; how expert decisions create a confirmed version; and how changed rules affect candidate inclusion or ordering. Keep hard exclusions separate from preferences. A unique all-pass candidate and a highest-ranked candidate are different results and must be described accordingly.

Design checks for arbitrary thresholds, duplicate criteria, selective literature use, weak exclusions, inconsistent units, and dependence on any already-known case-study outcome. Preserve failed proposals and unresolved decisions. Apply a precision-first, evidence-first admission policy: prefer a smaller defensible shortlist to a longer speculative one. An empty recommended set is a valid result when support is insufficient; do not fill a top-K quota. Keep exploratory or unassessed candidates visible in a separate view without presenting them as evidence-qualified recommendations.

## 4. Optimize the agent and application design

Recommend a practical proposer-critic core, with an arbiter or specialized roles where they add value. Define responsibilities and the artifacts passed between agents, tools, and humans. Ensure that tool outputs and errors can influence later decisions. Bound revision loops and define meaningful completion, rejection, and unresolved states. Do not assume that more agents, more debate, or more rounds necessarily improve screening.

Make the reusable agent mechanisms the main design output: planning and delegation, message/artifact contracts, coordination and disagreement resolution, execution state, tool-result feedback, scoped memory, policy/version control, failure recovery, human intervention, and evaluation. Show how the domain adapter supplies specialized evidence and tools without taking ownership of these core mechanisms. Document a clear expert handoff for unresolved biology rather than delaying the agent architecture until the scientific question is settled.

### 4.1 Decide when another round is useful

Define a screening round as one scheduled evidence/evaluation pass that produces an auditable candidate assessment or leaderboard snapshot. It can contain multiple tool calls and contributions from several agents. Distinguish screening rounds from LLM message turns, review exchanges, and updates arriving days or weeks later.

Treat single-pass screening as a legitimate operating mode and evaluation baseline. Compare it with a fixed-round reference configuration and an adaptive multi-round policy. Use the same task definitions, candidate universe, source-access cutoff, available tools, and independent evaluator; make actual time, token, tool, and human-review costs visible. Include matched-budget comparisons so extra computation is not mistaken for a better strategy.

Recommend another round only when there is an actionable opportunity: new external evidence or experiments, an unresolved evidence conflict, a consequential missing measurement, a questionable exclusion, or a targeted computation likely to affect the decision. Rephrasing the same evidence or raising an agent's self-reported confidence is not progress. Design stopping criteria for sufficient support, no actionable next step, diminishing information gain, repeated failures, and budget exhaustion. Reaching a limit should preserve unresolved status rather than force acceptance. Longitudinal leaderboard maintenance does not require every individual run to use multiple rounds.

Keep computational backends replaceable. Demonstrate the no-CDES design first, then explain what the optional CDES adapter would add, what it would require, and how its absence or failure would be handled. Avoid making a particular provider or model a hidden dependency.

For the local browser UI, cover flexible task creation, current and overall progress, rule and target inspection, evidence browsing, candidate comparison, expert decisions, human edits, and affected-result reruns. The default interface should expose concise decisions and sources rather than raw model responses.

### 4.2 Make the leaderboard the primary persistent output

Design a versioned, evidence-backed leaderboard for each comparable task context. Users should be able to enter a new objective, inspect the current qualified shortlist, understand each candidate's position, and follow updates as new evidence becomes available. Do not combine different diseases, endpoints, or constraint sets into an unexplained universal ranking. Keep historical snapshots tied to the objective, rule/strategy versions, evidence cutoff, and scoring or ordering method.

For each candidate, expose its identity, relevance to the objective, evidence provenance and independence, measured versus predicted values, CQA/rule coverage, missing information, counter-evidence, uncertainty, evaluation completeness, review status, and the reason for admission, exclusion, abstention, or rank change. Explicitly distinguish recommended, provisional, unassessed, and rejected entries. Prefer calibrated evidence or uncertainty measures where support exists; an LLM confidence statement is not a reliability estimate.

Plan updates driven by new papers, corrected data, tool outputs, expert decisions, and experimental feedback. Better-supported evidence may raise, lower, remove, or leave a candidate unranked. Preserve the change history and explain why a position changed. More citations, repeated copies of one study, a higher score, or a stable winner do not establish improved accuracy. The goal is improving decision quality and justification while maintaining conservative admission, not monotonically increasing scores or list length.

Human edits should preserve earlier versions and remain attributable. Automated reviewers cannot provide human scientific approval. Explain how expert feedback, uploaded files, local paths, and textual experimental results enter the system without becoming accepted facts solely because they were submitted.

### 4.3 Design detailed live progress and iteration history using Agentic Doping as a reference

Inspect the actual Agentic Doping UI and its source-level progress, event, and versioned-review mechanisms where available. Reuse the interaction ideas that fit this project and identify missing behavior explicitly. The historical generation prompt expresses intended capabilities; it does not prove that all of them exist. Do not assume a feature is implemented merely because it appears in the reference documentation. If the local project is unavailable, use the packaged reference note and state that limit.

Design the interface so a user can see, at any time, what is running, which agent or tool owns it, what it is trying to resolve, what has completed, and what is waiting. Show progress at overall-run, stage/workstream, and current-round levels. Where work has a known denominator, report completed versus planned work; where duration or scope is unknown, show a live status, elapsed time, and an honest indeterminate indicator. A configured maximum number of rounds is a budget, not a measure of how complete the scientific work is. Separate activity or heartbeat from actual completed work. Preserve visible distinctions between queued, running, waiting for a tool, waiting for human review, retrying, paused, failed, cancelled, completed, and unresolved states.

Provide a chronological timeline for every screening round and substantive analysis step, including single-pass tasks. The user should be able to open a round, inspect the evidence considered, compare the proposal and review, see the decision and its concise rationale, and follow the resulting candidate and rule changes. Do not require raw model responses or private internal reasoning to understand the run. Use source-linked decision explanations, material tool inputs/outputs, and recorded review conclusions.

For each round or analysis record, design the necessary identifiers and relationships: task/run/round/step, parent version or checkpoint, agent/tool/human actor, timestamps, question being answered, input and evidence versions, retrieved or corrected sources, relevant tool results or errors, proposed changes, critiques, human decisions, outcomes, unresolved issues, and the reason to continue or stop. Keep an append-only event history or equivalent immutable version history. Corrections should link back to earlier records rather than silently rewriting them.

Make changes between versions directly inspectable: rules and CQAs added, modified, merged, split, or removed; changed thresholds, units, or applicability; candidates admitted, excluded, demoted, or left unranked; and leaderboard rank/score/status changes with the evidence or decision that caused them. Link each material change to its supporting sources and responsible decision. Distinguish a new screening round from a retry of the same tool call, a human edit, and a later evidence-refresh run.

Design human intervention points in these views. A user should be able to inspect a pending proposal, edit or reject it with a reason, approve an appropriate version, request targeted follow-up, pause/resume, and see which previous results become stale and which steps must rerun. Show resume/checkpoint lineage and explain whether a result was reused or newly evaluated. The interface must not imply progress, scientific validation, or expert approval that has not occurred.

Deliver non-executable wireframes and a component/state description for the task-input screen, live run monitor, round timeline, version-difference view, candidate detail, evidence inspector, and human-review queue. Specify the proposed progress/event interface, update mechanism, reconnect and stale-state behavior, and its mapping to persisted records. These are design artifacts only; do not implement the UI or event transport in this phase.

## 5. Make self-improvement evaluable

Separate within-run rule refinement from across-run improvements to retrieval, review, tool selection, and failure handling. Keep scientific evidence, tentative hypotheses, and reusable procedures distinguishable in memory.

Prioritize evaluation of agent capability: task decomposition quality, appropriate delegation, tool-contract correctness, evidence traceability, handling of contradictions and missing information, memory isolation/reuse, reliable stop/resume behavior, human-edit propagation, useful strategy updates, and cost. Define process-level test scenarios separately from domain-outcome validation. A design can specify these mechanisms using bounded examples even when biomedical outcome labels are unavailable; it must not claim biological effectiveness from passing process-level checks.

Propose a fixed baseline and a protocol for evaluating revised strategies on separated material across more than the current case study. Assess precision among admitted candidates, evidence correctness and independent support, unsupported-claim and incorrect-exclusion rates, coverage and abstention, uncertainty calibration where identifiable, reproducibility, and operating cost. Use actual labels or qualified review where needed. Do not claim predictive accuracy when outcome labels are unavailable, and report coverage so returning nothing cannot trivially win the evaluation.

A strategy should earn promotion through measured improvement without silently weakening evidence-admission requirements. Preserve a usable prior version and prevent repeated tuning on the final evaluation material. Separate improvements caused by new external data from improvements caused by a changed agent policy by using fixed evidence snapshots when comparing policies. Neither a more elaborate rationale nor more frequent selection of a known reference compound establishes improvement.

Plan justified sensitivity analyses and record configurations before evaluating them. Label outcome-informed tuning as exploratory. Explain which claims the proposed evaluations would support and which would remain unestablished.

Begin with a no-additional-training baseline. For each optional trained model, specify its task, training data, labels or reward, proposed method, compute, evaluation, and value over the baseline. Distinguish prompt or memory updates from model-weight training. Treat strong RSI claims as requiring further evidence.

## 6. Research sources and inspect reusable work

Use the included papers, the Agentic Doping source manifest, the translated original generation prompt, and the progress/iteration reference note. If available, inspect relevant code in these local projects:

- `D:\codex_work\ai4s\agentic_doping`
- `D:\codex_work\TASTE`
- `D:\codex_work\iDeer`
- `D:\codex_work\self_improving_ai`
- `D:\codex_work\auto_research_project_vGPT`

Read applicable project instructions before inspection. Distinguish implemented code, tests, recorded executions, plans, and scientific evidence. The included Agentic Doping material demonstrates useful patterns but does not establish a validated medical self-improvement system. If the local repositories are unavailable, use the packaged excerpts and state that inspection limit without blocking the rest of the audit.

### Mandatory current literature investigation

Actively search the web for the latest relevant papers on agents, multi-agent systems, recursive self-improvement (RSI), self-improving agents, self-evolving agents, agent evolution, memory/skill acquisition, workflow or tool-use optimization, and agentic scientific discovery. Do not rely only on the packaged references, local projects, or recalled model knowledge. Determine the date of execution, record a search cutoff, and prioritize the preceding 6-12 months plus necessary foundational work. Check preprint revisions and publication status as of that cutoff.

Read primary papers and relevant official implementations. Record exact titles, authors, dates, venue/status, version, primary links, reading depth, claimed mechanism, what is actually changed, feedback source, evaluation setup, baselines, cost, limitations, and applicability to this project. Do not present an abstract-only read as a full-text review. If browsing or full text is unavailable, document the gap and do not label the survey current or comprehensive.

Cover both promising results and critical or negative evidence concerning reflection, multi-agent debate, extra inference rounds, reward or evaluator exploitation, and generalization. Distinguish within-run revision, persistent memory, evaluated strategy evolution, and model-weight training. Explain which mechanisms justify adoption and which add unsupported complexity. Include an explicit evidence-based answer to when single-pass screening is enough and when adaptive continuation is worthwhile. Recent publication alone is not a reason to adopt a method.

The primary literature investigation should concern agent systems, orchestration, memory, tool use, evaluation, and self-evolution. Limit additional drug-prioritization or biomedical research to what is needed to specify one credible application adapter and worked case. Use primary papers, official documentation, and source repositories for recommended tools. Explain actual inputs, outputs, usage, dependencies, and limits. Keep CDES and other backends optional where the task permits. Do not let a broad biology review or a search for a new biological mechanism displace the agent-design deliverables.

The supplied P07post matrix and GDSC table are optional case materials. Inspect their metadata only as needed to understand adapter inputs and limitations; new omics analysis and biological model development are not required in this architecture phase. Do not fabricate missing baseline samples, target measurements, surufatinib response data, or model checkpoints. Record domain gaps and expert dependencies without making them blockers for the reusable agent core.

## 7. Deliver one integrated audit and optimized plan

Create an English `design_audit/` folder in the workspace containing:

- `audit_report.md`: prioritized findings, evidence, recommended changes, and unresolved issues.
- `optimized_design.md`: the detailed recommended agent-first architecture, explicitly separating the reusable agent core, domain adapter, and case configuration. Cover planning/delegation, collaboration, tools, memory, adaptive execution, strategy improvement, observable progress, human review, and the leaderboard lifecycle. Specify interfaces, states, persistence, failure handling, no-CDES operation, and evaluation sufficiently for later implementation. Include an end-to-end path that would complete the required surufatinib case and produce the records needed by the rebuttal; keep unrelated biological investigation out of scope.
- `rebuttal_alignment.md`: map every material rebuttal claim to the required system capability, source/tool/expert evidence, future evaluation, output record, and acceptance condition. Mark current versus planned work and identify wording that cannot yet be substantiated.
- `case_study_protocol.md`: define the primary objective and target configuration, candidate comparison scope, criteria derivation/review, baseline and alternative configurations, intended high-priority surufatinib outcome, and how unsupported or contrary results will be recorded. Specify the protocol and required inputs without executing the screening or inventing a ranked result.
- `literature_review.md`: the current agent/RSI/self-evolving literature investigation, search cutoff and method, source/version table, positive and negative findings, and resulting design decisions.
- `leaderboard_spec.md`: task-scoped ranking, evidence-admission policy, candidate states, provenance, versioned updates, rank-change explanations, and precision/coverage tradeoffs.
- `evaluation_plan.md`: agent-capability evaluations, single-pass versus fixed/adaptive-round comparisons, matched-budget checks, separated evidence snapshots, precision/abstention/coverage, and strategy promotion criteria. Distinguish process correctness from optional domain-outcome validation.
- `ui_ux_spec.md`: Agentic Doping-inspired detailed progress views, real-time activity, round timeline, comparison screens, evidence inspection, human controls, and non-executable wireframes with observable states.
- `iteration_and_provenance_spec.md`: run/round/analysis records, immutable event and version history, evidence-to-decision links, rule/candidate/leaderboard differences, checkpoints, retries, human edits, and stale-result/rerun behavior.
- `architecture_decisions.md`: consequential design choices, alternatives, supporting evidence, tradeoffs, and unresolved decisions, including the progress-update approach and source of truth for UI state.
- `suggestions.md`: actionable improvements separated into v1 essentials and later extensions.
- `task.md`: implementable tasks with dependencies, inputs, outputs, acceptance criteria, and a sensible sequence.
- `module.md`: module responsibilities, interfaces, stored artifacts, reuse choices, and failure behavior.
- `resources.md`: data, services, compute, expert input, access needs, and optional training requirements.
- `tools.md`: researched tools and packages with primary links, inputs/outputs, usage descriptions, limitations, and recommended roles. Describe integration at the interface/design level; do not implement adapters or executable examples now.
- `collaboration_log.md`: actual subagent assignments, contribution paths, cross-review, disputed decisions, and their resolution.
- `agent_reports/`: the bounded workstream reports and final integrated-design review.

Choose a coherent recommended approach. Resolve disagreements explicitly and keep shared documents consistent. The goal is to make the entire agent architecture detailed, understandable, and ready for a later implementation phase, with an explicit route to completing the rebuttal's work and supporting surufatinib's priority in the primary case. Most analysis should concern the agent system; domain-specific work should supply the concrete interfaces, evidence needs, and case protocol. Do not drift into an abstract platform design or an unrelated biology project. Do not stop at a high-level feature list, and do not cross into implementation to compensate for missing design. Ask only about missing decisions that materially change the scope and cannot be resolved from the supplied material. Proceed with discoverable work while waiting.

Before handoff, have the final reviewer check that the method remains agent-centered while the concrete v1 purpose is completing the rebuttal and supporting surufatinib's high-priority position in the stated case; the rebuttal-to-design mapping and end-to-end case protocol are complete; the reusable core, domain adapter, and case configuration are separated; no implementation code was written; the architecture is sufficiently detailed; live progress and evidence-linked round/version histories are specified; the core works without CDES; actual multi-agent work and current agent/RSI literature research are documented; flexible inputs and task-scoped leaderboards are preserved; surufatinib is not a fixed answer for unrelated tasks; CQAs are not forced to eleven; target discovery remains optional; additional rounds have justified triggers and stopping criteria; and intended rankings or future experiments are not reported as completed results. Conclude with the recommended architecture, how it serves the rebuttal, material limits, and clickable output paths.
