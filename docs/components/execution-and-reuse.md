# Execution, checkpoints and evidence reuse

[Practical walkthrough](../component-walkthrough.md#execution-and-reuse) · [中文实操](../zh/component-walkthrough.md#execution-and-reuse)

[Components](README.md) · [Tasks](tasks-and-configuration.md) · [Assessment](assessment-and-qualification.md)

Execution coordinates the scientific components and gives each operation a saved boundary. Reuse avoids repeating paid or slow work when its factual and policy basis is unchanged. This is the implemented fixed-workflow portion of C15 and the concrete reuse mechanisms corresponding to part of C16.

## Inputs and outputs

`RunController.start()` in [`controller.py`](../../src/mas/core/controller.py) consumes a task, frozen rule-set reference, actor, settings, budget, provider registry, modes and optional continuation/reuse/measurement references. It creates a run binding and queued run, then normally executes it. The binding captures the task/rules versions, source cutoff, tool availability/replay, model roles, adapter, seed, settings hash/layers, evidence manifest, policy and implementation identity.

Execution produces identity records, assessments/reasons, checkpoints, an evidence snapshot, leaderboard snapshot, progress/budget events and a terminal run state. Derivation uses its own binding and stages in [`derivation_run.py`](../../src/mas/core/derivation_run.py), because generating criteria and screening candidates have different units of work and recovery needs.

## Fixed execution mechanism

`execute()` refuses a terminal run, opens an attempt, writes the fixed plan/round, restores recorded work and enters `_run()`. The stages are identity, assessment and snapshot. Identity resolution creates a record for each candidate even if identity is unresolved. The controller then chooses the bound qualification path or the legacy full-sweep path.

Current qualification supports `staged` and `full` evaluation. Both evaluate hard conditions before preferences. Staged mode records later cells as skipped after a verified direct hard failure; full mode evaluates those later cells. Unknown evidence continues through the schedule. The legacy path uses rule passes, per-pass budget reservations and shared candidate literature reading. Worker settings affect supported concurrent reading; the qualification schedule itself iterates candidate/rule work.

`_record_cell()` persists the assessment, reason and source lineage. Checkpoints record completed-cell hashes/cursors at the appropriate pass or candidate boundary. `_finish()` constructs the evidence and leaderboard records, accounts for unswept cells and ends the run. A completed sweep can yield no recommendation. A budget-limited sweep can publish partial diagnostics while remaining unresolved; execution completion and scientific success are separate states.

## Resume versus continuation

`resume()` continues the same nonterminal run from its recorded work and starts a new attempt; a previously interrupted attempt is finalized by the controller. `_restore()` reconstructs identities and assessed cells. Restoring does not ask a model to guess the previous state.

A finished run is never re-entered. Continuation starts a new run with `continues_run_id`, `continuation_kind` and chain identity. This lets later evidence/rule versions be compared while preserving the earlier outcome. Workbench `WorkflowManager` also saves phase checkpoints, budget usage and cooperative pause/stop commands in its workflow store. Review and pool stages have their own resumable boundaries so an unresolved model response is not repeatedly purchased on restart.

## Four concrete reuse paths

| Reuse operation | What crosses the boundary | Main implementation |
|---|---|---|
| Resume | Recorded identities/cells within the same run | `RunController._restore()` |
| Compatible assessment continuation | Completed unchanged cells and their reason/source refs | `_reuse_source()`, `_reuse_cells()` |
| Exact tool replay | Original successful/empty provider results with original date/artifact | `Broker.seed_cache_from_runs()` |
| Fresh derivation on existing evidence | Pinned admitted claims/facts; criterion pool starts empty | `existing_research.pin_evidence()`, `derive()` |

Assessment reuse requires a terminal screening source, fixed task version/cutoff/tool manifest/evidence policy and matching retrieval settings. Hook-based reuse requires a fixed evidence manifest. The rule and attribute refs, scoring/deferred routes and assessor version must match. `not_assessed` cells and cells carrying tool errors are not reused as completed decisions. A previously skipped cell is therefore reassessed when later circumstances allow it.

[`existing_research.py`](../../src/mas/core/existing_research.py) pins source streams/sequences and claim hashes. Only selected evidence crosses into fresh generation; old rules, critiques, adjudications, assessments and ranks do not seed the new pool. Evaluation ancestry can contribute completed `ok`/`empty` tool facts from explicitly pinned public terminal runs, even where the overall sweep failed or was cancelled. Failed/partial calls remain failures/partials rather than empty facts.

The `existing_only` broker wrapper permits exact replay, saved provider projections and explicitly allowed in-process facts. A miss returns `existing_evidence_unavailable`; it never invokes an unrecorded remote or prediction provider. Saved PubChem descriptor rows, recorded ADMET panels and typed clinical-route projections preserve their own source/derivation manifests.

[`staging.py`](../../src/mas/core/staging.py) provides a different operation: explicit task/criterion inheritance and shortlist tasks with lineage. This can intentionally carry criteria across tasks and is distinct from starting an empty pool over a fact bank. Supplements are another explicit reuse source, described in [evidence](evidence-and-reading.md).

## Failure semantics and scope

Policy drift rejects assessment reuse instead of treating changed work as already done. Workflow composition can start a recomputation path when compatibility fails. Invalid/active tool-replay sources are refused. Pause/stop preserves committed boundaries and spent budget; cancellation does not retract a paid provider call. Terminal failure and missing facts remain visible in source histories.

C16 is a collection of these explicit mechanisms, not a universal dependency-graph staleness engine. C8's proposed durable open-question/gain register and C14's memory store/recall/procedure trials are not implemented. `memory_mode` and broader `policy_arm` names are saved metadata; current screening uses the fixed algorithm. There is no implemented adaptive P2 continuation policy or strategy self-improvement service.

## Worked example: change one rule after a terminal run

**Illustrative:** a saved run has three completed criteria and two cells skipped after a hard rejection. A new run uses the same task/evidence policy but revises one criterion. Compatible completed cells whose attribute/rule refs and routes still match can retain their original assessment/reason refs. The changed criterion is evaluated again. Previous skipped cells cannot be reused as measurements and are evaluated if the new hard outcome permits it. If retrieval settings or the pinned fact bank changed, the reuse compatibility check rejects the source and the workflow recomputes the affected run.

## Existing verification

[`test_run_end_to_end.py`](../../tests/test_run_end_to_end.py) exercises the recorded pipeline. [`test_qualification_first.py`](../../tests/test_qualification_first.py) covers compatible cell reuse, terminal partial sources, skipped-cell reassessment and pause boundaries. [`test_existing_research_resume.py`](../../tests/test_existing_research_resume.py), [`test_review_attempt_resume.py`](../../tests/test_review_attempt_resume.py) and [`test_terminal_tool_facts.py`](../../tests/test_terminal_tool_facts.py) check the distinct resumable stages. [`test_broker_replay.py`](../../tests/test_broker_replay.py) covers exact fact replay.
