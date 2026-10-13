import pytest

from mas.core import identity, ledger, vocab
from mas.core.assessor import usable_claims
from mas.core.broker import Broker, ToolResult
from mas.core.evidence import claims_from_tool_result
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


# --- what a tool returns is recorded with the basis the tool declares ---------------------

MECHANISM_VALUE = {"name": "target_engagement", "value": True, "unit": None, "value_kind": "curated",
                   "determination_basis": "curated", "source_record_ref": "chembl_mechanism_304",
                   "conditions": {"action_type": "INHIBITOR"}}
POTENCY_VALUE = {"name": "pchembl_value", "value": 7.5, "unit": "pChEMBL", "value_kind": "curated",
                 "source_record_ref": "chembl_activity_909963", "conditions": {"standard_type": "IC50"}}
ENGAGEMENT_ATTRIBUTE = {"attribute_id": "attr_engagement", "version": 1, "name": "ABL1 engagement on record",
                        "measurement_kind": "categorical", "unit": None,
                        "acceptable_value_sources": ["database_entry"]}


def tool_result(values, tool_id="tool_drug_chembl_mechanism"):
    return ToolResult(result_id="tres_1", invocation={"tool_id": tool_id}, outcome="ok", values=values, records=[],
                      provenance={"tool_id": tool_id, "invocation_id": "inv_1", "license_id": "CC BY-SA 3.0 (ChEMBL)",
                                  "data_version": "chembl", "upstream_ref": ["chembl:mechanism:CHEMBL941:CHEMBL1862"]})


def db_claims(core, values, tool_id="tool_drug_chembl_mechanism"):
    return claims_from_tool_result(core, "run_x", tool_result(values, tool_id), candidate={"candidate_id": "cand_ik-K1"},
                                   attribute_ref="attr_engagement@v1", evidence_kind="database_entry",
                                   link_basis="exact_identifier_match")


def test_a_tool_declared_basis_is_kept_and_an_undeclared_one_falls_back_to_the_value_kind(core):
    claims = db_claims(core, [MECHANISM_VALUE, POTENCY_VALUE])
    # the mechanism row is a curated assertion and says so; a curated potency record is a
    # measurement a curator carried over, and still maps to `measured` through DB_BASIS
    assert [c["determination_basis"] for c in claims] == ["curated", "measured"]
    assert all(c["admission_state"] == "admitted" for c in claims)


def test_an_attribute_that_does_not_accept_curated_claims_gets_no_evidence(core):
    claims = db_claims(core, [MECHANISM_VALUE])
    # fails closed: an attribute that forgets acceptable_determination_bases ["curated"] sees
    # nothing, rather than counting a categorical assertion as a measurement
    usable, set_aside = usable_claims(claims, ENGAGEMENT_ATTRIBUTE)
    assert usable == [] and [c["set_aside_reason"] for c in set_aside] == ["determination_basis_not_accepted"]
    declared = dict(ENGAGEMENT_ATTRIBUTE, acceptable_determination_bases=["curated"])
    usable, set_aside = usable_claims(claims, declared)
    assert [c["claim_id"] for c in usable] == [claims[0]["claim_id"]] and set_aside == []


def test_an_unregistered_determination_basis_is_refused(core):
    with pytest.raises(vocab.VocabularyViolation):
        db_claims(core, [dict(MECHANISM_VALUE, determination_basis="asserted")])
