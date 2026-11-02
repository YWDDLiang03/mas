# Target-driven studies and optional CDES analysis

2 November 2026 · [English home](../../README.md) · [中文主页](../../README.zh-CN.md)

TRIAGE now starts drug-selection studies from a target profile, requirements and a selected library. The agents develop criteria from the chosen evidence strategy, assess admission and compare eligible candidates. CDES is an optional target-profile module.

## System update

- The task form foregrounds targets and requirements. Additional context is optional; the form previews the generated objective when targets are supplied alone.
- A new retrieval study can start with its own library. Saved-evidence studies select a fixed collection. Task-specific administration requirements guide criterion development.
- Settings supplies a CDES default, and each drug study selects its own setting and result collection. Enabled studies add a target-profile stage after screening.
- Profiles link compound structures and protein sequences to the task's own activity observations, eligibility and ranking. A completed study can toggle its analysis view while retaining its attached results.
- The current CDES adapter reads supplied results. Its pair-scoring interface is ready for a later deployed implementation.
- The agent runner accepts a separate drug-library task mode and forwards evidence and CDES choices. This mode prepares the supplied library in an independent workspace.

## Documentation

The bilingual READMEs, installation and task guides, case tutorial, component explanations, architecture and terminology now describe this workflow. Start with [target-driven studies](../target-workflow.md), [the CDES component](../components/structure-predictions.md) or [one-command operation](../agent-run.md).

[Current screenshots and measurements](../current-status.md) identify the source version and capture date. The presentation remains the dated 28 October system-and-case deck. Saved research tables retain their original study identity and numerical results.

## Verification

The system source update `d81dd77` passed 731 tests locally and its GitHub Actions checks. Focused checks covered task-defined routes, retrieval without an earlier collection, optional CDES binding, snapshot isolation, prediction source identity and export. The subsequent library-runner addition passed its 20 affected tests. Frontend type checking and the production build passed.

This publication update checks documentation links, example commands, screenshot identities, frozen case tables and current read APIs. Browser inspection uses Microsoft Edge on Windows. The retained example has 3,177 candidates, 10 Eligible, 1,305 Evidence incomplete and 1,862 Excluded; Surufatinib ranks first among the ten eligible compounds. These checks inspect the saved study and the updated workflow controls.
