# Model roles, provider adapters and budgets

[Practical walkthrough](../component-walkthrough.md#model-and-budget) · [中文实操](../zh/component-walkthrough.md#model-and-budget)

[Components](README.md) · [Tasks](tasks-and-configuration.md) · [Tool contracts](tools-and-providers.md)

MAS uses models to propose structured scientific interpretations and uses code to check their executable consequences. A model role identifies a responsibility; a provider adapter identifies the actual model and transport. Budget accounting records the work those calls consume. This implements C6 and supplies the model boundary used by criterion derivation, review, reading and optional scoring.

## Contract and rationale

[`models.py`](../../src/mas/core/models.py) defines the public boundary:

| Record / interface | Important fields or behavior |
|---|---|
| `CapabilityRecord` | Adapter identity, provider family, model ID and declared capabilities |
| `ModelRequest` | Request ID, role, system instructions, messages, response schema, token limit, metadata |
| `ModelResponse` | Actual model ID, text/parsed data, usage, latency, cost/status, attempts, reasoning and truncation |
| `ModelAdapter.complete(request)` | Returns a `ModelResponse` or raises `ModelError` |
| `ModelRoster` | Validated role → configured adapter mapping; persisted role bindings |
| `Budget` | Caps, used counters, soft classes, remaining amount, threshold notices |

Model output is data delivered to a trusted controller. It does not gain permission to edit the journal or claim a human decision. The caller supplies a response schema and the receiving component performs scientific checks after parsing. Schema-valid JSON alone does not establish correct attribution, a supported threshold or an admissible rule.

## Provider implementations

`AnthropicAdapter` uses the configured Anthropic endpoint. `OpenAICompatibleAdapter` supports a configured compatible endpoint, model, key environment variable/file, JSON response mode, reasoning/thinking options, prices and timeout. These are configurable transports; a compatible URL does not establish equivalence of model capabilities or behavior. `adapter_from_config()` constructs the configured kind.

`ExchangeAdapter` publishes `<exchange_dir>/requests/<request_id>.json` atomically and waits for a matching response file. [`cli/bridge.py`](../../src/mas/cli/bridge.py) supports `next`, `answer` and `status`, with atomic claims for multiple external workers. A response contains `data` or `text` plus the recorded answering identity. The bridge does not automatically launch external agents. `ScriptedAdapter` supplies deterministic responses for tests.

`ModelRoster.adapter()` refuses an unbound role. The registered role vocabulary includes planner, proposer, critic, adjudicator, retriever, reader, summarizer, reflector and evaluator judge. This list describes assignable identities; [architecture status](../architecture.md) identifies the workflows actually implemented. In particular, naming a reflector or planner role does not create a general reflection or planning service.

## Call lifecycle and accounting

`call_role()` resolves the adapter, records `agent.started`, submits the request and validates parsed output. `extract_json()` tolerates common fences/prose; `validate()` implements the supported schema subset. A failed response is returned to the model with schema problems for bounded repair, by default up to two repairs. Trace artifacts preserve requests, responses, schema problems and provider attempt accounting. Default event summaries stay separate from raw prompt/response traces.

Provider retries and schema repairs can cost real money. The OpenAI-compatible controlled-call path invokes callbacks before/after actual provider attempts; `call_role()` charges those attempts and avoids counting the same subtotal again when the logical call finishes. Known spend uses the provider usage and configured prices. Missing usage/prices retain `usage_status` or `cost_status` describing that uncertainty. A missing cost is not recorded as a proven zero.

[`Budget.try_charge()`](../../src/mas/core/budget.py) reserves capped classes such as `llm_turns` before work. `record()` charges amounts learned afterwards, particularly provider spend, and emits each warning/cap threshold once. A soft USD class reports the crossing and permits more work; a hard class refuses further starts after exhaustion. Since cost is known after a paid call, a spend cap can be crossed by the last permitted call. `from_config()` composes settings and explicit caps. Shared workflow budgets can span derivation and screening; rule-pass reservations prevent one part of a legacy full sweep from consuming all planned effort.

## Failures and practical limits

- Missing model roles raise `model_unavailable`; malformed replies eventually raise `parse_failed` after bounded repair.
- Missing/rejected credentials, provider errors and timeouts retain typed errors and sanitized diagnostics.
- Interrupted repair retains the paid response and accounting already obtained.
- A hard budget refusal is explicit; derivation/screening translates it into its recorded unresolved or not-assessed behavior.
- An exchange timeout remains a timeout. The external worker's absence does not become an empty scientific result.

Provider identity is recorded for independence analysis. Distinct role labels using one adapter are shared-model roles, and cross-family criticism is a configuration property. The release does not assume every critic is independent.

## Worked example: no-cost local role call

**Illustrative executable fragment**; the adapter is synthetic and makes no network call:

```python
from tempfile import TemporaryDirectory
from mas.core.models import ModelRequest, ModelRoster, ScriptedAdapter, call_role
from mas.core.runtime import Core
from mas.core.budget import Budget

adapter = ScriptedAdapter("example", lambda request: {"decision": "inspect"})
roster = ModelRoster({"example": adapter}, {"critic": "example"})
schema = {"type": "object", "required": ["decision"],
          "properties": {"decision": {"type": "string"}}}
request = ModelRequest(request_id="example-request", role="critic", system="Return JSON.",
                       messages=[{"role": "user", "content": "Inspect this synthetic item."}],
                       response_schema=schema)
with TemporaryDirectory() as root, Core.open(root) as core:
    budget = Budget({"llm_turns": 1})
    reply = call_role(core, roster, "run_example", request, budget=budget)
    assert reply.data == {"decision": "inspect"}
    assert budget.used["llm_turns"] == 1
```

## Existing verification

[`test_models_and_reading.py`](../../tests/test_models_and_reading.py) covers role validation, schema repair, trace records and exchange round trips. [`test_config_and_providers.py`](../../tests/test_config_and_providers.py) covers key sources, thinking options, truncation recovery, spend thresholds and redaction. [`test_model_accounting.py`](../../tests/test_model_accounting.py) checks paid-attempt accounting. These are contract tests; use a separately recorded live run when validating a specific provider installation.
