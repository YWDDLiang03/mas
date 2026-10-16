"""Schema-repair accounting uses synthetic responses and never calls a real API."""

import json

import pytest

from mas.core import models
from mas.core.budget import Budget
from mas.core.models import CapabilityRecord, ModelError, ModelRequest, ModelResponse, ModelRoster, call_role


class SequenceAdapter:
    record = CapabilityRecord("sequence", "synthetic", "synthetic-model")

    def __init__(self, replies):
        self.replies = iter(replies)
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        return ModelResponse(request.request_id, reply["text"], None, "synthetic-model", "synthetic",
                             usage=reply.get("usage", {}), cost_usd=reply.get("cost_usd"))


def _request():
    return ModelRequest(role="reader", system="schema test", messages=[],
                        response_schema={"type": "object", "required": ["answer"]})


def _reply(text, incoming=10, outgoing=3, cost=0.1):
    return {"text": text, "usage": {"input_tokens": incoming, "output_tokens": outgoing}, "cost_usd": cost}


def _finished(core):
    events = [event for event in core.journal.replay("run_accounting") if event.event_type == "agent.finished"]
    assert len(events) == 1
    return events[0].payload, core.artifacts.payload(events[0].payload["trace_blob"])


def test_repair_aggregates_every_response_and_preserves_each_failed_schema_reply(core):
    adapter = SequenceAdapter([_reply("not json"), _reply('{"answer":"ok"}', incoming=20, outgoing=5, cost=0.2)])
    roster = ModelRoster({"sequence": adapter}, {"reader": "sequence"})
    budget = Budget({"llm_turns": 3})
    response = call_role(core, roster, "run_accounting", _request(), budget=budget)
    finished, trace = _finished(core)
    assert response.usage == finished["usage"] == {"input_tokens": 30, "output_tokens": 8}
    assert response.cost_usd == pytest.approx(0.3)
    assert finished["cost_usd"] == pytest.approx(0.3) and budget.used["usd"] == pytest.approx(0.3)
    assert finished["usage_status"] == "complete" and finished["cost_status"] == "estimated"
    assert finished["attempt_count"] == 2
    assert trace["request"]["request_id"] == adapter.requests[0].request_id
    assert trace["final_text"] == '{"answer":"ok"}'
    assert trace["attempts"][0]["response"]["text"] == "not json"
    assert trace["attempts"][0]["schema_problems"]
    assert trace["attempts"][1]["request_id"] == adapter.requests[1].request_id
    assert trace["attempts"][1]["request"]["response_schema"] == adapter.requests[0].response_schema


@pytest.mark.parametrize("caps", [{"llm_turns": 1}, {"llm_turns": 3, "usd": 0.1}])
def test_repair_respects_turn_and_spend_caps_without_losing_the_first_response(core, caps):
    adapter = SequenceAdapter([_reply("not json"), _reply('{"answer":"must not be called"}')])
    roster = ModelRoster({"sequence": adapter}, {"reader": "sequence"})
    budget = Budget(caps)
    with pytest.raises(ModelError) as refusal:
        call_role(core, roster, "run_accounting", _request(), budget=budget)
    finished, trace = _finished(core)
    assert refusal.value.error_class == "quota_exhausted" and len(adapter.requests) == 1
    assert finished["cost_usd"] == pytest.approx(0.1) and budget.used["usd"] == pytest.approx(0.1)
    assert finished["cost_status"] == "estimated" and finished["outcome"] == "budget_exhausted"
    assert trace["attempts"][-1]["status"] == "not_attempted"


def test_adapter_failure_after_a_paid_bad_reply_keeps_known_cost_and_marks_unknown_remainder(core):
    adapter = SequenceAdapter([_reply("not json"), ModelError("timeout", "synthetic timeout")])
    roster = ModelRoster({"sequence": adapter}, {"reader": "sequence"})
    budget = Budget({"llm_turns": 3})
    with pytest.raises(ModelError) as failure:
        call_role(core, roster, "run_accounting", _request(), budget=budget)
    finished, trace = _finished(core)
    assert failure.value.error_class == "timeout"
    assert finished["usage"] == {"input_tokens": 10, "output_tokens": 3} and finished["usage_status"] == "partial"
    assert finished["cost_usd"] == finished["known_cost_usd"] == pytest.approx(0.1)
    assert finished["cost_status"] == "partial" and budget.used["usd"] == pytest.approx(0.1)
    assert trace["attempts"][1]["cost_usd"] is None and trace["attempts"][1]["status"] == "failed"
    assert failure.value.accounting["trace_blob"] == finished["trace_blob"]


def test_a_failure_without_returned_usage_has_unknown_cost_and_a_trace(core):
    adapter = SequenceAdapter([ModelError("timeout", "synthetic timeout")])
    roster = ModelRoster({"sequence": adapter}, {"reader": "sequence"})
    with pytest.raises(ModelError):
        call_role(core, roster, "run_accounting", _request())
    finished, trace = _finished(core)
    assert finished["usage"] == {} and finished["usage_status"] == "unknown"
    assert finished["cost_usd"] is None and finished["cost_status"] == "unknown"
    assert trace["attempts"][0]["request"]["response_schema"] == _request().response_schema
    assert trace["outcome"] == "failed"


def test_usage_without_a_configured_tariff_does_not_become_known_zero_cost(core):
    adapter = SequenceAdapter([_reply('{"answer":"ok"}', cost=None)])
    response = call_role(core, ModelRoster({"sequence": adapter}, {"reader": "sequence"}),
                         "run_accounting", _request())
    finished, _ = _finished(core)
    assert response.usage_status == "complete" and response.cost_usd is None and response.cost_status == "unknown"
    assert finished["cost_usd"] is None and finished["cost_status"] == "unknown"


def test_an_internal_empty_reply_then_transport_failure_keeps_the_completed_http_usage(core, monkeypatch):
    class Reply:
        status_code = 200
        text = json.dumps({"choices": [{"message": {"content": ""}, "finish_reason": "length"}],
                           "usage": {"prompt_tokens": 100, "completion_tokens": 10}})

        def json(self):
            return json.loads(self.text)

    replies = iter([Reply(), models.requests.Timeout("synthetic transport failure")])

    def post(*args, **kwargs):
        response = next(replies)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setenv("SYNTHETIC_ACCOUNTING_KEY", "synthetic-test-key")
    monkeypatch.setattr(models.requests, "post", post)
    adapter = models.OpenAICompatibleAdapter(
        "synthetic", "m", base_url="https://example.invalid", api_key_env="SYNTHETIC_ACCOUNTING_KEY",
        price_input_per_mtok=1, price_output_per_mtok=2)
    budget = Budget({"llm_turns": 2})
    with pytest.raises(ModelError) as failure:
        call_role(core, ModelRoster({"synthetic": adapter}, {"reader": "synthetic"}),
                  "run_accounting", _request(), budget=budget)
    finished, trace = _finished(core)
    assert failure.value.error_class == "transient_network"
    assert finished["usage"] == {"input_tokens": 100, "output_tokens": 10}
    assert finished["usage_status"] == finished["cost_status"] == "partial"
    assert finished["cost_usd"] == budget.used["usd"] == pytest.approx(0.00012)
    inner = trace["attempts"][0]["provider_attempts"]
    assert len(inner) == 2 and inner[0]["raw_response"] == Reply.text
    assert inner[1]["cost_usd"] is None and "synthetic-test-key" not in json.dumps(trace)


def _http_reply(text="", finish_reason="stop"):
    class Reply:
        status_code = 200

        def json(self):
            return {"id": "synthetic-response", "model": "synthetic-model",
                    "choices": [{"message": {"content": text}, "finish_reason": finish_reason}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 10}}

    reply = Reply()
    reply.text = json.dumps(reply.json())
    return reply


def _controlled_roster(monkeypatch):
    monkeypatch.setenv("SYNTHETIC_ACCOUNTING_KEY", "synthetic-test-key")
    adapter = models.OpenAICompatibleAdapter(
        "synthetic", "m", base_url="https://example.invalid", api_key_env="SYNTHETIC_ACCOUNTING_KEY",
        price_input_per_mtok=1, price_output_per_mtok=2)
    return ModelRoster({"synthetic": adapter}, {"reader": "synthetic"})


def _provider_progress(core):
    return [event.payload for event in core.journal.replay("run_accounting")
            if event.event_type == "run.annotated" and event.payload.get("annotation") == "model_provider_attempt"]


@pytest.mark.parametrize("finish_reason", ["stop", "length"])
def test_each_internal_http_attempt_is_charged_and_visible_before_the_next(core, monkeypatch, finish_reason):
    roster = _controlled_roster(monkeypatch)
    budget, sent, observed = Budget({"usd": 1, "llm_turns": 3}), [], []
    budget.on_model_attempt = observed.append

    def post(*args, **kwargs):
        if sent:
            assert budget.used["usd"] == pytest.approx(0.00012)
            assert budget.used["llm_turns"] == 2
            assert len(_provider_progress(core)) == 1
            assert not any(event.event_type == "agent.finished" for event in core.journal.replay("run_accounting"))
        sent.append(kwargs["json"]["max_tokens"])
        return _http_reply("", finish_reason) if len(sent) == 1 else _http_reply('{"answer":"ok"}')

    monkeypatch.setattr(models.requests, "post", post)
    response = call_role(core, roster, "run_accounting", _request(), budget=budget)
    finished, trace = _finished(core)
    assert sent == ([4000, 8000] if finish_reason == "length" else [4000, 4000])
    assert budget.used["llm_turns"] == finished["provider_attempt_count"] == 2
    assert response.cost_usd == finished["cost_usd"] == budget.used["usd"] == pytest.approx(0.00024)
    assert len(observed) == 2 and len(trace["attempts"][0]["response"]["provider_attempts"]) == 2
    assert all(row["request_id"] == trace["request"]["request_id"] for row in observed)
    assert all(row["known_cost_usd"] == pytest.approx(0.00012) for row in observed)
    assert all("raw_response" not in row and "text" not in row and "synthetic-test-key" not in json.dumps(row) for row in observed)


@pytest.mark.parametrize("caps", [{"llm_turns": 1}, {"usd": 0.00012}])
def test_internal_http_retry_respects_caps_before_another_request(core, monkeypatch, caps):
    roster = _controlled_roster(monkeypatch)
    budget, sent = Budget(caps), []
    def post(*args, **kwargs):
        sent.append(kwargs["json"]["max_tokens"])
        return _http_reply("", "length")
    monkeypatch.setattr(models.requests, "post", post)
    with pytest.raises(ModelError) as failure:
        call_role(core, roster, "run_accounting", _request(), budget=budget)
    finished, trace = _finished(core)
    assert failure.value.error_class == "quota_exhausted" and len(sent) == 1
    assert budget.used["llm_turns"] == finished["provider_attempt_count"] == 1
    assert budget.used["usd"] == finished["cost_usd"] == pytest.approx(0.00012)
    assert finished["cost_status"] == "estimated" and finished["outcome"] == "budget_exhausted"
    assert trace["attempts"][0]["provider_attempts"][-1]["status"] == "not_attempted"


@pytest.mark.parametrize("boundary", ["before_retry", "in_http", "on_attempt"])
def test_controlled_interrupt_preserves_original_exception_paid_attempts_and_trace(core, monkeypatch, boundary):
    roster = _controlled_roster(monkeypatch)
    stopped = InterruptedError("synthetic operator stop")
    class ControlledBudget(Budget):
        def try_charge(self, kind, amount=1):
            if boundary == "before_retry" and kind == "llm_turns" and self.used.get(kind):
                raise stopped
            return super().try_charge(kind, amount)
    budget, sent = ControlledBudget({"usd": 1, "llm_turns": 4}), []
    if boundary == "on_attempt":
        def stop_after_paid(summary):
            assert budget.used["usd"] == pytest.approx(0.00012)
            raise stopped
        budget.on_model_attempt = stop_after_paid
    def post(*args, **kwargs):
        sent.append(kwargs["json"]["max_tokens"])
        if boundary == "in_http" and len(sent) == 2:
            raise stopped
        return _http_reply("", "length")
    monkeypatch.setattr(models.requests, "post", post)
    with pytest.raises(InterruptedError) as failure:
        call_role(core, roster, "run_accounting", _request(), budget=budget)
    finished, trace = _finished(core)
    assert failure.value is stopped
    assert len(sent) == finished["provider_attempt_count"] == (2 if boundary == "in_http" else 1)
    assert budget.used["usd"] == finished["cost_usd"] == pytest.approx(0.00012)
    assert finished["cost_status"] == ("partial" if boundary == "in_http" else "estimated")
    assert finished["outcome"] == "interrupted" and stopped.accounting["trace_blob"] == finished["trace_blob"]
    assert stopped.accounting["provider_attempts"][0]["raw_response"] == _http_reply("", "length").text
    assert trace["attempts"][0]["provider_attempts"][0]["usage"] == {"input_tokens": 100, "output_tokens": 10}


def test_schema_repair_and_internal_retry_have_one_debit_per_http_and_one_logical_identity(core, monkeypatch):
    roster = _controlled_roster(monkeypatch)
    replies = iter([_http_reply("", "length"), _http_reply("not json"), _http_reply('{"answer":"ok"}')])
    monkeypatch.setattr(models.requests, "post", lambda *args, **kwargs: next(replies))
    budget = Budget({"usd": 1, "llm_turns": 3})
    response = call_role(core, roster, "run_accounting", _request(), budget=budget)
    finished, _ = _finished(core)
    progress = _provider_progress(core)
    assert response.data == {"answer": "ok"}
    assert response.cost_usd == budget.used["usd"] == finished["cost_usd"] == pytest.approx(0.00036)
    assert budget.used["llm_turns"] == finished["provider_attempt_count"] == 3
    assert finished["attempt_count"] == 2
    assert len({row["request_id"] for row in progress}) == 1
    assert progress[0]["attempt_request_id"] == progress[1]["attempt_request_id"] != progress[2]["attempt_request_id"]
    assert [row["logical_attempt_index"] for row in progress] == [1, 1, 2]
    assert [row["provider_attempt_index"] for row in progress] == [1, 2, 1]
