# Component reference

[Practical walkthrough](../component-walkthrough.md#read-records) · [中文实操](../zh/component-walkthrough.md#read-records)

[Project home](../../README.md) · [Architecture and C1–C20 status](../architecture.md)

This reference describes the shipped implementation. Every page explains the problem a component solves, why its boundary exists, the concrete Python entry points, its records and failure semantics, and a worked example. Examples marked **illustrative** explain behavior using synthetic data; they are not reported research measurements. Test links identify existing verification of the contract and do not imply a fresh test run or live provider validation.

| Component | Read this to understand |
|---|---|
| [Foundation: records and storage](foundation.md) | C1–C3, identities of records, canonical hashes, writer lock and replay |
| [Tasks and configuration](tasks-and-configuration.md) | C4–C5, research scope, normalization, layered settings and bound plans |
| [Models and budgets](models-and-budgets.md) | C6, role/provider contracts, JSON repair, real spend and unknown costs |
| [Tools and providers](tools-and-providers.md) | C13, registration, capability resolution, outcomes, retries and provenance |
| [Evidence and reading](evidence-and-reading.md) | C9, source access, located claims, extraction checks, uploads and evidence snapshots |
| [Criteria and review](criteria-and-review.md) | C7/C10/C18, attributes versus rules, pool evolution, consolidation and authority |
| [Assessment and qualification](assessment-and-qualification.md) | C11, executable measurements, direct evidence, hard conditions and missingness |
| [Ranking and explanations](ranking-and-explanations.md) | C12, scores, comparability, symbolic regression and separately grounded narratives |
| [Execution and reuse](execution-and-reuse.md) | C15/C16, fixed workflows, checkpoints, continuation and existing-evidence runs; C8/C14 limits |
| [Evaluation and recovery](evaluation-and-recovery.md) | C19, prospective measurement, CQA recovery, exposure accounting and C20 limits |
| [Domain adapters](domain-adapters.md) | Drug providers, literature sources, ADMET, uploaded carrier/general data and extension points |
| [Workbench and CLI](workbench-and-cli.md) | C17, application routes, workflows, read projections, UI language and file exchange |

For a first technical reading, follow tasks → evidence → criteria → assessment → ranking. For integration work, start with tools/providers and models/budgets. For result interpretation, read assessment, ranking, and evaluation together.
