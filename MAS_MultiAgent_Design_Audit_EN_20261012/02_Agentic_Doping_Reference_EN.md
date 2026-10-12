# Agentic Doping: Reusable Workflow Patterns

Read-only source inspection | 12 October 2026

Agentic Doping is the user's existing materials-research project. The inspected code provides concrete examples of evidence handling and iterative agent workflows. It is an engineering reference for the proposed medical MAS; the included excerpts do not implement drug screening or establish biomedical validity.

For the UI and iteration experience, also read the [original project request in English](06_Agentic_Doping_Original_Prompt_English_Translation.md) and the [source-based progress/history note](07_Agentic_Doping_Progress_and_Iteration_Reference_EN.md). The current task is to design the biomedical architecture in detail, with no implementation code. The original request describes intent; the source-based note distinguishes existing mechanisms from additional requirements such as semantic version differences and complete live activity events.

The source snapshot is repository commit `0007ad104755aec56cbc2479db6cf68c0e05b237`, together with the inspected working-tree file contents. The repository contains unrelated local changes. Each selected file and excerpt is independently hashed in the [source manifest](agentic_doping_reference/SOURCE_MANIFEST.json), so the precise material included here does not depend on the commit identifier alone.

## Reusable components

| Pattern | What the inspected code does | Proposed medical adaptation | Included source |
|---|---|---|---|
| Evidence admission | Retains current, access-permitted, source-linked claims for knowledge distillation. | Attach sources and provenance to CQA rationales; keep unverified summaries distinguishable. | [Claim admission](agentic_doping_reference/excerpts/01_claim_admission.py.txt) |
| Gap-directed retrieval | Searches identified gaps, records retrieval failures, and distils newly admitted claims into scoped memory. | Search specifically for missing threshold support, applicability conditions, and counter-evidence. | [Gap discovery](agentic_doping_reference/excerpts/02_gap_discovery.py.txt) |
| Proposal-review-revision | Saves versioned proposals and reviews, bounds the number of rounds, and preserves rejected or exhausted outcomes. | Revise rules and candidate arguments without silently turning unfinished review into acceptance. | [Bounded loop](agentic_doping_reference/excerpts/03_proposal_review_loop.py.txt) |
| Tool feedback | In the inspected Anthropic path, dispatches tool calls and sends their results or errors into subsequent model calls. | Return actual outputs from available tools. CDES is one optional adapter; its absence does not block the core workflow. Provider-specific behavior must be checked. | [Tool feedback](agentic_doping_reference/excerpts/04_tool_feedback.py.txt) |
| Scoped memory | Restricts provisional recall by group and role; ordinary agent verdicts do not automatically become durable lessons. | Keep tentative rule hypotheses, scientific evidence, and reusable procedures separate. | [Recall scope](agentic_doping_reference/excerpts/05_scoped_memory.py.txt), [outcome handling](agentic_doping_reference/excerpts/06_outcome_memory_boundary.py.txt) |
| Methodology reflection | May save one provisional review procedure from recorded run facts; leaves the completed ranking unchanged. | Propose improved evidence-search or review strategies for later evaluation. | [Reflection](agentic_doping_reference/excerpts/07_methodology_reflection.py.txt) |
| Strategy content checks | Rejects candidate identities, observed score thresholds, and scientific conclusions disguised as reusable methods. | Prevent a lesson such as “make surufatinib win” from being treated as general methodological improvement. | [Strategy checks](agentic_doping_reference/excerpts/08_methodology_guardrails.py.txt) |
| Evidence record | Appends typed records and reads them back from a per-run ledger. | Preserve provenance, exclusions, failed evaluations, and rule-version associations. | [Ledger](agentic_doping_reference/excerpts/09_evidence_ledger.py.txt) |

## Limits that matter for this concept

The existing target-property validator draws from a fixed property vocabulary. It provides useful fields for direction, rationale, and computation method, but it is not open-ended CQA derivation. The proposed MAS must add the latter capability. See the [target-contract excerpt](agentic_doping_reference/excerpts/10_fixed_vocabulary_target_contract.py.txt), selected through original line 729 to omit a later multilingual keyword block while preserving the included code unchanged.

The tool-feedback example is provider-specific. The previously inspected Codex bridge path dispatches a returned call list without another local bridge request carrying those results; it should not be assumed to provide the same continuing loop as the included Anthropic example. A medical implementation would need to verify the behavior of its actual tool adapter.

The inspected project has proposal versioning, scoped memory, and provisional strategy refinement. The inspection did not establish a held-out evaluator that promotes improved rule versions, or a scientific result showing that this learning process improves candidate selection. The source explicitly defers active-learning acquisition and model retraining; the [deferred-capability excerpt](agentic_doping_reference/excerpts/11_deferred_learning.py.txt) preserves that limitation. An evaluation and promotion process for CQA/strategy versions would be new work.

An agent-review verdict, a software field named `approved`, and a human scientific approval are different records. The medical MAS must not infer human approval from a programmatically assigned status. Likewise, multiple agent roles can share information and biases; assigning different role names does not establish independent scientific validation.

## Intended transfer

Reuse the workflow pattern: evidence intake, specific gap discovery, proposal, criticism, tool feedback, bounded revision, and carefully scoped memory. Add biomedical evidence rules, genuine human review, and evaluation of proposed strategy changes. Do not transfer materials-specific properties, numerical thresholds, evidence-tier meanings, winning compositions, or performance claims.

These are selected, unmodified source excerpts for reading. They are not standalone programs and omit imports and dependencies outside the selected ranges. No project experiments or test suites were run for this package. The selection excludes live run histories, credentials, service configuration, caches, personal conversations, and large model artifacts.
