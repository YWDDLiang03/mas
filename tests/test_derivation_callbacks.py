"""Logical model/tool activity checkpoints, using only synthetic providers."""

import pytest

from mas.core import derivation_run
from mas.core.budget import Budget
from mas.core.models import ModelRequest, call_role
from test_criteria_pool import DIMENSIONS, EVIDENCE_CATALOG, OPERATOR, RoundOne, roster_for, setup, unmerged_pool


def test_iterative_callbacks_cover_enumeration_tools_models_and_stage_counts(core):
    task_id, broker = setup(core)
    observed, checkpoints = [], []
    budget = Budget({"llm_turns": 100, "tool_calls": 100})
    result = derivation_run.derive_iterative(core, broker, roster_for(RoundOne()), task_id, dimensions=DIMENSIONS,
        catalog=EVIDENCE_CATALOG, by=OPERATOR, inner_iterations=1, budget=budget,
        observer=lambda kind, detail: observed.append((kind, detail)),
        checkpoint=lambda run_id, stage_boundary=True: checkpoints.append((run_id, stage_boundary)))
    assert observed[0] == ("created", {"run_id": result["run_id"]})
    activities = [detail for kind, detail in observed if kind == "activity"]
    assert {detail["role"] for detail in activities} >= {"retriever", "reader", "tool", "proposer"}
    assert sum(not boundary for _, boundary in checkpoints) == len(activities)
    finished = [detail for kind, detail in observed if kind == "stage_finished"]
    assert all(detail["before_count"] >= 0 and detail["after_count"] >= 0 for detail in finished)
    assert any(detail["phase"] == "evidence" for kind, detail in observed if kind == "stage")
    assert [detail for kind, detail in observed if kind == "usage"][-1]["budget"] == budget.snapshot()


@pytest.mark.parametrize("operation,paused", [("derive", False), ("reduce", True)])
def test_activity_stop_is_cancelled_or_service_paused_and_does_not_charge_unstarted_model(core, operation, paused):
    created = []
    def observer(kind, detail):
        if kind == "created":
            created.append(detail["run_id"])
    def checkpoint(run_id, stage_boundary=True):
        if not stage_boundary:
            error = InterruptedError("synthetic stop")
            error.paused = paused
            raise error
    budget = Budget({"llm_turns": 100})
    if operation == "derive":
        task_id, broker = setup(core)
        execute = lambda: derivation_run.derive_iterative(core, broker, roster_for(RoundOne()), task_id,
            dimensions=DIMENSIONS, catalog=EVIDENCE_CATALOG, by=OPERATOR, budget=budget,
            observer=observer, checkpoint=checkpoint)
    else:
        task_id, source = unmerged_pool(core)
        execute = lambda: derivation_run.reduce_pool(core, roster_for(RoundOne()), task_id, catalog=EVIDENCE_CATALOG,
            by=OPERATOR, continues_run_id=source["run_id"], budget=budget, observer=observer, checkpoint=checkpoint)
    with pytest.raises(InterruptedError):
        execute()
    events = core.journal.replay(created[0])
    assert events[-1].event_type == ("run.paused" if paused else "run.cancelled")
    assert not any(e.event_type in ("run.failed", "run.completed", "agent.started", "tool.requested") for e in events)
    assert budget.used.get("llm_turns", 0) == 0


def test_schema_repair_pause_preserves_prior_attempt_accounting(core):
    budget, observed, attempts = Budget({"llm_turns": 10}), [], []
    stopping = []
    def checkpoint(run_id, stage_boundary=True):
        if stopping:
            raise InterruptedError("stop at the next logical activity")
    def script(request):
        attempts.append(request.request_id)
        stopping.append(True)
        return {} if len(attempts) == 1 else {"answer": "synthetic"}
    observed_core, observed_budget, _ = derivation_run._activity_context(core, "run_synthetic_callbacks", budget,
        lambda kind, detail: observed.append((kind, detail)), checkpoint)
    request = ModelRequest(role="proposer", system="synthetic", messages=[], response_schema={"type": "object",
        "required": ["answer"], "properties": {"answer": {"type": "string"}}})
    with pytest.raises(InterruptedError):
        call_role(observed_core, roster_for(script), "run_synthetic_callbacks", request, budget=observed_budget)
    assert budget.used["llm_turns"] == 1 and len(attempts) == 1
    finished = [e for e in core.journal.replay("run_synthetic_callbacks") if e.event_type == "agent.finished"]
    assert len(finished) == 1 and not finished[0].payload["schema_ok"]
    assert finished[0].payload["error_class"] == "InterruptedError"
    assert finished[0].payload["attempt_count"] == 1
    assert [detail for kind, detail in observed if kind == "usage"][-1]["budget"]["used"]["llm_turns"] == 1
    with pytest.raises(InterruptedError):
        call_role(observed_core, roster_for(script), "run_synthetic_callbacks", request, budget=observed_budget)
    assert budget.used["llm_turns"] == 1
