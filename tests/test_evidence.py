import pytest

from mas.core import identity, ledger
from mas.core.broker import Broker
from mas.core.journal import actor
from mas.core.runtime import Core
from tests.fakes import AbsentProvider, FakeIdentity, FakeProperty

WHO = actor("agent", "retriever-1", "evidence_retriever")


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c


def hit(key, label):
    return {"preferred_label": label, "identifiers": [{"scheme": "ik", "value": key}], "link_basis": "name_match_single_candidate"}


def test_broker_retries_retryable_errors_then_succeeds(core):
    prop = FakeProperty({("K1", "MW"): 300.0}, failures={"K1": ["transient_network", "rate_limited"]})
    delays = []
    broker = Broker(core, sleep=delays.append)
    broker.register(prop)
    result = broker.call("run_x", "property_estimate", "computed_property", {"identifier": "K1", "property": "MW"},
                         requesting_actor=WHO)
    assert result.outcome == "ok" and result.values[0]["value"] == 300.0
    assert prop.calls == 3 and len(delays) == 2
    kinds = [e.event_type for e in core.journal.replay("run_x")]
    assert kinds == ["tool.requested", "tool.retry_scheduled", "tool.retry_scheduled", "tool.returned"]
    assert result.provenance["executed_on"]["platform"] == "linux"


def test_broker_distinguishes_failed_empty_and_not_attempted(core):
    broker = Broker(core, sleep=lambda s: None)
    broker.register(FakeProperty({}, failures={"K2": ["parse_failed"]}))
    broker.register(AbsentProvider())
    failed = broker.call("run_x", "property_estimate", "computed_property", {"identifier": "K2", "property": "MW"},
                         requesting_actor=WHO)
    empty = broker.call("run_x", "property_estimate", "computed_property", {"identifier": "K3", "property": "MW"},
                        requesting_actor=WHO)
    no_identity = broker.call("run_x", "property_estimate", "computed_property", {"identifier": "", "property": "MW"},
                              requesting_actor=WHO)
    absent = broker.call("run_x", "interaction_estimate", "estimate", {}, requesting_actor=WHO)
    unknown_capability = broker.call("run_x", "literature_retrieval", "search", {}, requesting_actor=WHO)
    assert failed.outcome == "failed" and failed.error["class"] == "parse_failed"
    assert empty.outcome == "empty"
    assert (no_identity.outcome, no_identity.absence_reason) == ("not_attempted", "identity_unresolved")
    assert (absent.outcome, absent.absence_reason) == ("not_attempted", "not_installed")
    assert (unknown_capability.outcome, unknown_capability.absence_reason) == ("not_attempted", "not_configured")


def test_broker_refuses_tools_not_supported_on_the_host_platform(core):
    broker = Broker(core, platform="windows")
    prop = FakeProperty({("K1", "MW"): 1.0})
    prop.contract = type(prop.contract)(**{**prop.contract.__dict__, "supported_platforms": (("linux", "checked"),)})
    broker.register(prop)
    result = broker.call("run_x", "property_estimate", "computed_property", {"identifier": "K1", "property": "MW"},
                         requesting_actor=WHO)
    assert (result.outcome, result.absence_reason) == ("not_attempted", "requires_other_environment")


def test_identity_resolution_records_link_basis_and_queues_ambiguity(core):
    broker = Broker(core)
    broker.register(FakeIdentity({"alpha": [hit("AAA", "Alpha")],
                                  "beta": [hit("B1", "Beta 1"), hit("B2", "Beta 2")]}))
    records = identity.resolve_universe(core, broker, "run_x", ["alpha", "beta", "gamma"], primary_scheme="ik",
                                        capability="identity_resolution")
    by_label = {r["input_label"]: r for r in records}
    assert by_label["alpha"]["candidate_id"] == "cand_ik-AAA" and identity.is_resolved(by_label["alpha"])
    assert by_label["beta"]["identity_link_basis"] == "name_match_ambiguous"
    assert by_label["gamma"]["identity_link_basis"] == "unresolved"
    queued = [e for e in core.journal.replay("run_x") if e.event_type == "human.review_requested"]
    assert len(queued) == 1 and queued[0].payload["subject"]["kind"] == "identity_merge"


def test_claims_need_locations_and_snapshots_freeze_admitted_claims(core):
    source = ledger.put_source(core, {"identifiers": [{"scheme": "db_fake", "value": "K1"}],
                                      "source_status": "database_entry", "access_state": "metadata_only"})
    with pytest.raises(ValueError):
        ledger.record_claim(core, "run_x", {"source_ref": source}, by=WHO, admission_state="admitted", admission_reasons=[])
    claim = {"source_ref": source, "candidate_ref": "cand_ik-K1", "attribute_ref": "attr_mw@v1",
             "location": {"location_kind": "record_field", "locator_value": "MW", "quoted_span": "300.0",
                          "span_checked_against_source": True},
             "normalized_statement": "MW of K1 is 300 g/mol", "value": 300.0, "unit": "g/mol",
             "determination_basis": "derived", "evidence_kind": "database_entry"}
    admitted = ledger.record_claim(core, "run_x", claim, by=WHO, admission_state="admitted",
                                   admission_reasons=["identifier_match", "provenance_complete"])
    ledger.record_claim(core, "run_x", dict(claim, value=999.0), by=WHO, admission_state="quarantined",
                        admission_reasons=["unit_unresolved"])
    found = ledger.claims(core, ["run_x"], candidate_ref="cand_ik-K1", attribute_ref="attr_mw@v1")
    assert [c["claim_id"] for c in found] == [admitted]
    snapshot = ledger.freeze_snapshot(core, "run_x", task_id="task_t", claim_ids=[admitted], cutoff_at="2026-10-13",
                                      tool_manifest=[], by=WHO)
    assert snapshot == "evs_task_t_1"
