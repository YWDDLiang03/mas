"""Historical replay uses exact tool artifacts, without network or evaluator content."""

from dataclasses import replace

import pytest

from mas.core import broker as broker_mod
from mas.core.broker import Broker
from mas.core.budget import Budget
from mas.core.controller import RunError
from mas.core.journal import actor
from tests.fakes import FakeProperty
from tests.test_run_end_to_end import OPERATOR, make_controller, setup_task

WHO = actor("agent", "replay-test", "retriever")
INPUTS = {"identifier": "K1", "property": "MW"}


def _call(broker, run="run_source", inputs=None, question="computed_property", budget=None):
    return broker.call(run, "property_estimate", question, INPUTS if inputs is None else inputs,
                       requesting_actor=WHO, budget=budget)


def _source(core, run="run_source", value=300, outcome="ok", completed=True):
    class OutcomeProperty(FakeProperty):
        def invoke(self, question_kind, inputs):
            response = super().invoke(question_kind, inputs)
            response.outcome = outcome
            return response

    core.journal.append(run, "run.created", actor=WHO, payload={"task_id": "task_source"}, state_to="queued")
    broker = Broker(core, platform="linux", sleep=lambda _: None)
    broker.register(OutcomeProperty({("K1", "MW"): value} if value is not None else {}))
    result = _call(broker, run=run)
    if completed:
        core.journal.append(run, "run.completed", actor=WHO, state_to="completed")
    return result


@pytest.mark.parametrize("value", [300, None])
def test_exact_historical_success_and_empty_keep_the_original_artifact_and_date(core, value):
    original = _source(core, value=value)
    provider = FakeProperty({("K1", "MW"): 999})
    broker = Broker(core, platform="windows")
    broker.register(provider)
    manifest = broker.seed_cache_from_runs(["run_source"])
    replayed = _call(broker, run="run_replay", budget=Budget({"tool_calls": 0}))
    assert provider.calls == 0
    assert replayed == original
    assert replayed.provenance["executed_on"]["platform"] == "linux"
    assert replayed.provenance["retrieved_at"] == original.provenance["retrieved_at"]
    (event,) = core.journal.replay("run_replay")
    assert event.event_type == "tool.returned" and event.payload["historical_replay"] is True
    assert event.payload["source_artifact_id"] == original.artifact_id
    assert event.payload["source_request_seq"] == 2
    assert event.payload["fresh_tool_call"] is False and event.payload["charged_tool_calls"] == 0
    assert event.payload["replay_manifest_digest"] == manifest["manifest_digest"]
    manifest["source_run_ids"].clear()
    assert broker.replay_manifest()["source_run_ids"] == ["run_source"]


@pytest.mark.parametrize("change", ["tool_id", "contract_version", "implementation_version", "question", "inputs"])
def test_every_exact_match_component_is_required(core, change):
    _source(core)
    provider = FakeProperty({("K1", "MW"): 999, ("K2", "MW"): 888})
    if change in ("tool_id", "contract_version", "implementation_version"):
        provider.contract = replace(provider.contract, **{change: "different"})
    if change == "question":
        provider.contract = replace(provider.contract, question_kinds=("computed_property", "other_property"))
    broker = Broker(core)
    broker.register(provider)
    broker.seed_cache_from_runs(["run_source"])
    result = _call(broker, run="run_live", inputs={"identifier": "K2", "property": "MW"} if change == "inputs" else None,
                   question="other_property" if change == "question" else "computed_property")
    assert provider.calls == 1 and result.values[0]["value"] in (999, 888)
    assert not any(event.payload.get("historical_replay") for event in core.journal.replay("run_live"))


@pytest.mark.parametrize("outcome", ["partial", "failed"])
def test_partial_and_failed_results_are_not_replayed_or_converted_to_empty(core, outcome):
    original = _source(core, value=None, outcome=outcome)
    assert original.outcome == outcome
    provider = FakeProperty({("K1", "MW"): 999})
    broker = Broker(core)
    broker.register(provider)
    manifest = broker.seed_cache_from_runs(["run_source"])
    assert manifest["cache_entries"] == 0
    assert _call(broker, run="run_live").values[0]["value"] == 999 and provider.calls == 1


def test_only_explicit_completed_sources_are_accepted_before_dispatch(core):
    _source(core, completed=False)
    broker = Broker(core)
    with pytest.raises(ValueError, match="not a completed run"):
        broker.seed_cache_from_runs(["run_source"])
    assert broker.replay_manifest() is None
    with pytest.raises(ValueError, match="explicit run_"):
        broker.seed_cache_from_runs(["case_sealed"])
    broker.register(FakeProperty({("K1", "MW"): 999}))
    _call(broker, run="run_live")
    with pytest.raises(ValueError, match="before any tool call"):
        broker.seed_cache_from_runs(["run_source"])


def test_source_order_is_explicit_and_the_manifest_is_reproducible(core):
    _source(core, run="run_first", value=300)
    _source(core, run="run_second", value=700)
    manifests = []
    for stream in ("run_replay1", "run_replay2"):
        broker = Broker(core)
        broker.register(FakeProperty({}))
        manifests.append(broker.seed_cache_from_runs(["run_second", "run_first"]))
        assert _call(broker, run=stream).values[0]["value"] == 700
    assert manifests[0] == manifests[1]


def test_bound_replay_sources_cannot_be_changed_when_resuming(core):
    _source(core)
    task_id = setup_task(core)
    controller = make_controller(core)
    controller.broker.seed_cache_from_runs(["run_source"])
    run_id = controller.start(task_id, by=OPERATOR, execute=False)
    binding = controller._load(run_id).binding
    assert binding["tool_replay"] == controller.broker.replay_manifest()
    with pytest.raises(RunError, match="tool_replay_policy_drift"):
        make_controller(core).resume(run_id)


@pytest.mark.parametrize(("raw", "expected"), [("win32", "windows"), ("linux", "linux"), ("darwin", "darwin")])
def test_default_platform_tracks_the_host_and_an_explicit_override_wins(core, monkeypatch, raw, expected):
    monkeypatch.setattr(broker_mod.sys, "platform", raw)
    assert Broker(core).platform == expected
    assert make_controller(core).host_platform == expected
    assert Broker(core, platform="linux").platform == "linux"


@pytest.mark.parametrize("has_tpsa", [True, False])
def test_pubchem_projects_a_saved_whole_row_locally_and_a_missing_field_stays_unknown(core, monkeypatch, has_tpsa):
    from mas.adapters.drug import pubchem
    from mas.core.assessor import assess_cell
    from mas.core.evidence import claims_from_tool_result

    row = {"CID": 123, "RotatableBondCount": 4, **({"TPSA": "86.3"} if has_tpsa else {})}
    monkeypatch.setattr(pubchem, "_properties", lambda *args: [row])
    monkeypatch.setattr(broker_mod, "utc_now", lambda: "2026-10-15T00:00:00Z")
    core.journal.append("run_source", "run.created", actor=WHO, state_to="queued")
    source_broker = Broker(core, platform="linux")
    source_broker.register(pubchem.PubChemProperty(pubchem.PropertyCache()))
    source = source_broker.call("run_source", "property_estimate", "computed_property",
                                {"identifier": "KEY", "property": "RotatableBondCount"}, requesting_actor=WHO)
    core.journal.append("run_source", "run.completed", actor=WHO, state_to="completed")

    def no_new_retrieval(*args, **kwargs):
        raise AssertionError("a recorded row must not be fetched again")

    monkeypatch.setattr(pubchem, "_properties", no_new_retrieval)
    monkeypatch.setattr(broker_mod, "utc_now", lambda: "2026-10-16T00:00:00Z")
    broker = Broker(core, platform="windows")
    broker.register(pubchem.PubChemProperty(pubchem.PropertyCache()))
    manifest = broker.seed_cache_from_runs(["run_source"], pubchem_record_projection=True)
    result = broker.call("run_projection", "property_estimate", "computed_property",
                         {"identifier": "KEY", "property": "TPSA"}, requesting_actor=WHO)
    assert manifest["policy_version"] == 2 and manifest["parameter_projections"][0]["rows"] == 1
    assert result.artifact_id != source.artifact_id
    assert result.invocation["invocation_id"] != source.invocation["invocation_id"]
    assert result.invocation["normalized_input"]["property"] == "TPSA"
    provenance = result.provenance
    assert provenance["operation_kind"] == "local_historical_projection"
    assert provenance["retrieved_at"] == source.provenance["retrieved_at"] == "2026-10-15T00:00:00Z"
    assert provenance["processed_at"] == "2026-10-16T00:00:00Z"
    assert provenance["executed_on"] == {"platform": "windows", "execution_location": "in_process"}
    assert provenance["derived_from"]["source_artifact_id"] == source.artifact_id
    assert len(provenance["derived_from"]["source_artifact_sha256"]) == 64
    if has_tpsa:
        assert result.values[0]["value"] == 86.3 and result.values[0]["value_kind"] == "derived"
    else:
        assert result.outcome == "empty" and result.values == []
        claims = claims_from_tool_result(core, "run_projection", result, candidate={"candidate_id": "test"},
                                         attribute_ref="attr_tpsa@v1", evidence_kind="database_entry",
                                         link_basis="exact_identifier_match")
        assert claims == []
        cell, _ = assess_cell(
            candidate={"candidate_id": "test"},
            attribute={"attribute_id": "attr_tpsa", "version": 1, "name": "TPSA", "unit": "Å²",
                       "measurement_kind": "quantitative", "acceptable_value_sources": ["database_entry"]},
            rule={"rule_id": "rule_tpsa", "version": 1, "rule_kind": "preference", "cutoff_basis": "source_stated"},
            rule_set_ref="rules@v1", claims=claims, resolved=True)
        assert cell["verdict"] == "unknown_missing" and cell["value"] is None
