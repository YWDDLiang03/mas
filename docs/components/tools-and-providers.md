# Tool broker and provider contracts

[Components](README.md) · [Domain adapters](domain-adapters.md) · [Evidence](evidence-and-reading.md)

The broker is the boundary between a scientific question and an installed tool. It answers two distinct questions: whether this installation can attempt the operation, and what happened when a provider attempted it. This is C13. Evidence admission remains the responsibility of the evidence layer.

## Inputs, outputs and design rationale

`Broker.call(stream_id, capability, question_kind, inputs, ...)` takes normalized inputs, requesting actor, optional IDs, budget, required value strength and an ordered tool restriction. It returns a `ToolResult` containing invocation, outcome, values, records, provenance, optional error/absence and the saved artifact ID.

Tools are resolved by either the adapter capability label or the domain-neutral `capability_kind`, plus `question_kind`. [`broker.py`](../../src/mas/core/broker.py) recognizes entity resolution, relationship evidence/estimation, attribute estimation, source retrieval, document reading, dataset context and rule evaluation. An installed provider must still implement the requested question kind; a matching name is insufficient.

This boundary lets the core stay reusable. A drug adapter can label an operation `interaction_evidence_lookup`, while its core kind is `relationship_evidence_lookup`. The selected provider still supplies exact tool, contract and implementation versions. A successful transport call is an observation, not a verdict on the candidate.

## Provider contract

`ToolContract` declares `tool_id`, adapter capability, core capability kind, question kinds, contract and implementation versions, purpose, evidence kind produced and claim-strength ceiling. It also records determinism, latency class, timeout, license, side effects, execution location, supported platforms, required inputs and identity inputs.

A provider exposes `contract` and `invoke(question_kind, inputs) -> ProviderResponse`. The response separates `values` from other `records` and may supply outcome, data version, upstream references, warnings, source retrieval time and a local derivation record. Use `ToolAbsent` for an unavailable precondition and `ToolError` for a runtime failure after an attempt.

`register()` adds a provider; `contracts()` exposes the registry; `manifest()` supplies the versioned availability snapshot bound into a run. Resolution preserves registration order unless `tool_ids` explicitly orders the allowed providers. The broker returns the first provider result whose outcome is not `not_attempted`; it does not automatically aggregate all sources. Criteria with multiple evidence routes ask for those sources explicitly.

## Outcomes and their meaning

| Outcome | Meaning downstream |
|---|---|
| `ok` | Provider returned usable observations/records; scientific checks still apply |
| `partial` | Provider returned a partial response; limitations remain attached |
| `empty` | An attempted completed lookup produced no values/records |
| `not_attempted` | No eligible provider or a declared precondition prevented the operation |
| `failed` | Attempted operation failed; typed error retained |
| `unknown_outcome` | Registered vocabulary for an unknown result; its presence does not imply automatic synthetic closure of every interrupted tool request |

Examples of absence are `not_configured`, `identity_unresolved`, `requires_other_environment`, `budget_exceeded` and `existing_evidence_unavailable`. An absent tool and a completed empty query have different implications for missingness and reproducibility.

## Dispatch, retries and provenance

Before invoking, the broker checks cache/replay, required identity/input fields, declared platform support and tool-call budget. Required-value filtering excludes a contract whose strength ceiling cannot answer the requested kind. A returned value above its contract ceiling raises a contract violation; predictions cannot be relabeled as measurements by the provider.

`ToolError` classes for rate limits, transient networking, upstream server errors and timeouts are retryable by default. `_call_one()` uses bounded exponential backoff with jitter and journals scheduled retries. Other typed failures are retained without those retries. Unexpected provider exceptions are recorded as `internal_error`. Transport-specific enforcement such as an HTTP timeout is performed by the provider; the broker contract records the timeout rather than sandboxing arbitrary Python execution.

`_record()` stores the normalized input hash, tool/contract/implementation version, retrieval date, platform, data version, upstream references, license, attempts and outcome. `tool.requested` and terminal events connect the invocation to its result artifact. The evidence layer uses that provenance when creating located claims.

## Cache and exact historical replay

The cache key includes tool ID, contract version, implementation version, question kind and normalized input. Ordinary in-process caching accepts successful/partial/empty results. Historical replay is stricter: `seed_cache_from_runs()` indexes only recorded `ok`/`empty` results from explicitly selected completed runs, or explicitly permitted terminated/pinned sources. Partial and failed attempts stay excluded. Original artifacts and retrieval dates are retained, along with a replay manifest.

Replay must be configured before dispatch. It does not establish that an observation is current under external database changes. [Execution and reuse](execution-and-reuse.md) explains the additional compatibility checks for assessment reuse.

## Worked example: a local provider

**Illustrative implementation**, showing the minimal provider shape:

```python
from mas.core.broker import ProviderResponse, ToolContract

class ExampleSizeProvider:
    contract = ToolContract(
        tool_id="example_size", capability="example_property",
        capability_kind="attribute_estimate", question_kinds=("size",),
        contract_version="1", implementation_version="synthetic-1",
        purpose_statement="Return a synthetic example observation",
        evidence_kind_produced="database_entry", claim_strength_ceiling="measured",
        required_inputs=("candidate_id",), execution_location="in_process",
    )

    def invoke(self, question_kind, inputs):
        return ProviderResponse(values=[{
            "name": "size", "value": 120, "unit": "nm",
            "value_kind": "measured", "determination_basis": "measured",
            "source_record_ref": "synthetic-observation-1",
        }], data_version="example-1")
```

Registering this provider enables a broker call; a real integration also needs identity, an attribute route, evidence-source policy and the applicable scientific rule. The synthetic value is not real evidence.

## Existing verification

[`test_broker_replay.py`](../../tests/test_broker_replay.py) checks all matching fields, source order, preservation of original date/artifact, exclusion of failed/partial results and saved PubChem-row projection. [`test_terminal_tool_facts.py`](../../tests/test_terminal_tool_facts.py) checks facts from interrupted runs. [`test_drug_adapter.py`](../../tests/test_drug_adapter.py) and [`test_predict_admet.py`](../../tests/test_predict_admet.py) cover concrete provider contracts and strengths.
