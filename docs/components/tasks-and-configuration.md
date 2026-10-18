# Tasks, normalization and configuration

[Practical walkthrough](../component-walkthrough.md#task-and-config) · [中文实操](../zh/component-walkthrough.md#task-and-config)

[Components](README.md) · [Architecture](../architecture.md)

A task defines the research question and candidate population before the system judges any candidate. Configuration defines how MAS spends effort and executes that task. Keeping these records explicit prevents a later settings edit from silently changing the meaning of an earlier result. This page covers C4 and the implemented portion of C5.

## Inputs and outputs

| Input | Output |
|---|---|
| Objective, scope entities, constraints, library or seed candidates | Versioned `task_context` artifact and `task.version_recorded` event |
| Workbench original input and optional additional information | Structured English research context plus retained original input; missing-input requests where required |
| Preset, project TOML, profile, workbench settings, environment, CLI overrides | Validated `Config`, source layer for every setting, configuration hash |
| Task version, selected rule set, settings and provider registry | Immutable run binding and fixed plan artifact |

[`task.validate()`](../../src/mas/core/task.py) requires `objective_text`, `mode`, `evaluation_scope`, and either a candidate universe/access path or seed candidates. Conditional mode needs a constraint or scope entity. `record_version()` creates a new ID or increments the version of an existing task; `get()` can read the latest or a specific historical version. `blocking_unknowns()` identifies unresolved inputs that prevent `RunController.start()`.

## Why normalization is separate from scoring

Free text mixes goals, definitions, numeric requirements and preferences. A model can help structure that input, but a parsed instruction must retain its source. [`investigation.py`](../../src/mas/core/investigation.py) prepares task records from the workbench through `_normalize`, `_apply_normalized` and `_record_task`. Uploaded evidence has additional requirement validation in [`uploaded_evidence.py`](../../src/mas/core/uploaded_evidence.py). An unsupported measurement or missing interpretation can lead to a request for more information instead of inventing an executable criterion.

Task-mandated criteria keep task-field provenance. They are reported separately from criteria derived from literature. A model restating a requirement already supplied by the user has performed normalization, not independently discovered that requirement. This distinction is carried into criterion exports and [recovery reports](evaluation-and-recovery.md).

## Layered configuration

[`config.py`](../../src/mas/core/config.py) contains the `SETTINGS` registry: defaults, documentation, allowed values, ranges, units and optional registered constant IDs. `resolve()` composes defaults, preset, project file, profile, optional extra tables, environment and explicit overrides. Later applicable layers win. The standard precedence tested by the project is defaults → preset → project → profile → environment → CLI; the workbench additionally supplies its saved settings as an extra table before final overrides.

`Config.sources` identifies the winning layer for every value. `layer_record()` produces the stored explanation; `hash()` includes resolved values, provider tables and role bindings. `registered_constants()` names numerical settings that can affect a published verdict, and `register_constants()` records them in the bound stream.

Examples of independent controls are literature breadth/depth, read limits, pool stage order, model/tool/spend caps, assessment mode and qualification policy, coverage floors, and optional symbolic scoring. A larger literature volume raises permitted effort; saturation can still stop reading early. An effort ceiling is not a promise that the system will read that many sources.

## Fixed planning in v1.0

[`RunController.execute()`](../../src/mas/core/controller.py) writes a plan containing identity, assessment and snapshot stages, rule-pass steps, and the budget envelope. Derivation has its own recorded stage sequence and continuation. The `planner` role name is available in model configuration, but the screening plan is fixed code. There is no general planner that creates arbitrary dependency graphs, delegates agents or replans after every failure.

`RunController.start()` binds task and rule-set references, adapter/version, model roles, provider availability, seed, evidence cutoff, effective settings, qualification/evaluation/evidence modes and optional measurement profile. These are the inputs to saved interpretation and reuse. Editing current settings affects a new operation; it does not update the binding of a completed run.

## Failure semantics

Unknown configuration keys, wrong types, disallowed values, out-of-range values and cross-field inconsistencies raise `ConfigError`. Role bindings to missing providers are refused. A task missing mandatory context raises `TaskContextInvalid`. A task with blocking unknowns is refused at run start with `rejected_not_permitted_in_state`.

For uploaded workflows, the missing requirement is retained as a structured request and can be answered in the same draft. Candidate/library uploads and measurement uploads have separate validation. The selected evidence source is explicit; `existing_only` does not acquire new literature when a fact is absent.

## Worked example: one task and one configuration change

**Illustrative executable fragment** using a synthetic candidate name:

```python
from tempfile import TemporaryDirectory
from mas.core import config, task
from mas.core.runtime import Core
from mas.core.journal import actor

settings = config.resolve(project_file=None, environ={},
                          overrides={"evaluation.mode": "staged"})
with TemporaryDirectory() as root, Core.open(root) as core:
    task_id, version = task.record_version(core, {
        "objective_text": "Prioritize compounds for a defined target profile",
        "mode": "conditional",
        "evaluation_scope": "synthetic demonstration",
        "candidate_universe": {"members": ["EXAMPLE-A"]},
        "constraints": [{"text": "Use the declared target profile", "hardness": "hard"}],
    }, by=actor("human", "researcher", "operator"))
    assert version == 1
    assert settings.sources["evaluation.mode"] == "override"
```

The candidate still needs identity, executable criteria and evidence before evaluation. The example demonstrates task/configuration records rather than a scientific result.

## Existing verification

[`test_config_and_providers.py`](../../tests/test_config_and_providers.py) verifies precedence, layer records, hashes, invalid settings and role/provider binding. [`test_workbench_normalization.py`](../../tests/test_workbench_normalization.py) checks the workbench normalization path; [`test_required_bindings.py`](../../tests/test_required_bindings.py) checks preservation of task-defined anchors. [Execution and reuse](execution-and-reuse.md) explains how those inputs constrain continuation.
