# English Multi-Agent Design Audit Package

Revision date: 12 October 2026. Current revision: agent-first architecture with the manuscript rebuttal and surufatinib prioritization as the concrete v1 purpose; no implementation code; detailed progress/history; flexible inputs; persistent leaderboards; adaptive continuation; and current agent/RSI research.

This package is ready to give to another agent. Its immediate assignment is an agent-systems architecture audit conducted through actual multi-agent collaboration. Biology is the initial application context. The concrete v1 purpose is to complete the capabilities described in the manuscript rebuttal and support surufatinib as a leading candidate under the stated task and targets. The reusable framework and persistent leaderboards serve that purpose while allowing other inputs later. The current phase produces detailed design, not completed screening results.

Keep three layers distinct: reusable agent core, domain adapter, and case configuration. Prioritize planning/delegation, collaboration, tools, evidence/provenance, memory, self-improvement, observable execution, UI, and evaluation. Investigate biology only as needed for the primary case's interfaces and evidence needs; unresolved domain judgments should have clear expert handoffs rather than blocking the architecture or becoming invented facts.

**No implementation code in the current phase.** The next agent must make the complete architecture detailed and understandable through documents, diagrams, state/interface descriptions, and non-executable UI wireframes. It must not scaffold or implement the application, change the reference projects, deploy a service, or run scientific experiments.

**CDES is optional.** The recommended core workflow must function without CDES. If useful and available, CDES can be added through an optional adapter; its absence must not block the design audit, evidence investigation, rule/CQA development, or candidate comparison supported by other available evidence.

## Give this prompt to the next agent

Copy [START_HERE_Audit_and_Optimize_Prompt_EN.md](START_HERE_Audit_and_Optimize_Prompt_EN.md) into the next agent's task and provide this extracted folder. That prompt explicitly requires actual subagents, six workstreams including current agent/RSI/self-evolving literature research, independent criticism, integration, and a record of collaboration. A multi-agent assessment may still use only one screening pass; extra rounds must have a reason.

Read the supporting files in this order:

1. [Project brief](Project_Brief_EN.md): the full functional and research request, updated so CDES is optional.
2. [Concept overview](01_Concept_Overview_EN.md): the agent-method contribution, concrete rebuttal objective, and proposed reasoning loops.
3. [Agentic Doping reference](02_Agentic_Doping_Reference_EN.md): reusable code patterns and limits of the inspected implementation.
4. [Source inventory](04_Source_Inventory_EN.md): reference papers, optional data, and their intended uses.
5. [Historical rebuttal draft](03_Provided_Rebuttal_Draft_EN.md): background only, with superseded assumptions and uncompleted claims identified.
6. [Original Agentic Doping request in English](06_Agentic_Doping_Original_Prompt_English_Translation.md): the user's historical generation prompt, translated and explicitly scoped as reference material.
7. [Progress and iteration reference](07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md): inspected source mechanisms and the additional behavior the biomedical design must specify.

The current audit prompt and updated project brief take precedence over the historical manuscript and rebuttal when defining the new system. In particular, the original eleven CQAs do not determine the new criterion count, and historical use of CDES does not make it a required dependency.

## Agreed design intent

- Make this an agent-systems task; keep domain assumptions and tools in an application adapter and case configuration.
- Accept flexible goals, evidence/data, candidates, desired properties, and constraints; biomedical inputs are the initial instance.
- Treat the ovarian-cancer/TME targets and surufatinib as the required first acceptance case. Aim to substantiate the drug's high priority and the rebuttal's promised workflow, without hard-coding the answer for unrelated tasks.
- Derive proposed rules and CQAs from the objective and evidence; retain uncertainty and counter-evidence.
- Start from existing TME hypotheses or targets where useful; target discovery from scratch is optional.
- Make a persistent evidence-backed leaderboard the primary output, with versioned snapshots and explanations for admission, abstention, exclusion, and rank changes.
- Prefer a smaller defensible shortlist to weak recommendations; allow an empty recommended set and keep exploratory candidates separate.
- Compare single-pass, fixed-round, and adaptive screening under explicit budgets; continue only for actionable evidence or decision gaps.
- Improve both scientific rules and agent strategies, evaluating accuracy where outcome labels exist and evidence quality, coverage, and cost where appropriate.
- Require live investigation of the latest agent, RSI, self-improving, and self-evolving research, with dates, source versions, and positive and negative findings.
- Keep scientific expert decisions distinct from automated agent review.
- Provide a local browser UI, progress visibility, human editing and review, and auditable candidate comparisons.
- Model the progress and iteration experience on Agentic Doping: detailed overall/stage/round progress, current agent/tool activity, waits and failures, a round timeline, and version differences linked to evidence and recorded decisions.
- Record each substantive analysis and revision with provenance, concise rationale, actor, version, and outcome; preserve history and explain reruns after human edits.

All MAS implementation, the next agent's current literature survey, screening experiments, human approvals, sensitivity studies, and improvement results remain proposed. This package does not contain newly generated drug rankings. The next agent must produce `literature_review.md`, `leaderboard_spec.md`, `evaluation_plan.md`, `ui_ux_spec.md`, `iteration_and_provenance_spec.md`, and `architecture_decisions.md`, plus `rebuttal_alignment.md` and `case_study_protocol.md`, alongside the original audit and planning documents.

## Contents and provenance

The package includes the English prompts and notes, five English reference PDFs, the supplied optional datasets, and selected Agentic Doping source excerpts. All archive entry names are ASCII. The authored documentation is English. Original non-English source identifiers are preserved using JSON Unicode escapes in the [artifact manifest](ARTIFACT_MANIFEST.json), so their identities remain recoverable without Chinese text in the visible documentation.

The [source manifest](agentic_doping_reference/SOURCE_MANIFEST.json) records each source excerpt's original file, line range, and checksums. The excerpt showing fixed-vocabulary target validation ends before its multilingual keyword block; included lines remain unmodified. The [checksum list](MANIFEST.sha256) and [delivery checks](05_Delivery_Checks_EN.md) document package verification.

Original scientific PDFs and datasets are preserved byte-for-byte. The language check covers packaged text, datasets, and extractable PDF text; it is not an exhaustive OCR audit of every embedded figure. Earlier package versions remain separate.
