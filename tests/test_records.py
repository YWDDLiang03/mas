import pytest

from mas.core import constants, criteria, review, task
from mas.core.journal import actor
from mas.core.runtime import Core

OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")
EXPERT = actor("human", "E1", "expert", identity_basis="recorded_attestation")
AGENT = actor("agent", "proposer-1", "proposer")

TASK_SPEC = {
    "objective_text": "Prioritize compounds by two test criteria",
    "mode": "conditional",
    "scope_entities": [{"entity_kind": "target", "identifier": "T1", "identifier_scheme": "test", "role": "required"}],
    "candidate_universe": {"kind": "enumerated_set", "members": ["alpha", "beta"]},
    "constraints": [{"text": "test constraint", "kind": "scope", "hardness": "hard"}],
    "evaluation_scope": {"comparison_basis": "all_pass_set", "abstention_allowed": True},
}

ATTRIBUTE = {
    "name": "Molecular weight",
    "definition": "Molecular weight of the parent compound",
    "measurement_kind": "quantitative", "unit": "g/mol", "direction": "lower_better",
    "acceptable_value_sources": ["database_entry"], "aggregation": "consensus",
    "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                         "parameters": {"property": "MolecularWeight"}},
}
RULE = {"rule_kind": "hard_exclusion", "cutoff": {"comparator": "<=", "value": 600, "unit": "g/mol"},
        "cutoff_basis": "expert_set"}


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c


def test_task_context_versions_supersede(core):
    task_id, v1 = task.record_version(core, TASK_SPEC, by=OPERATOR)
    _, v2 = task.record_version(core, dict(TASK_SPEC, objective_text="edited"), by=OPERATOR, task_id=task_id)
    assert (v1, v2) == (1, 2)
    assert task.get(core, task_id)["objective_text"] == "edited"
    assert task.get(core, task_id, 1)["objective_text"] == TASK_SPEC["objective_text"]
    assert task.get(core, task_id)["supersedes"] == f"{task_id}@v1"


def test_task_context_needs_mandatory_fields(core):
    with pytest.raises(task.TaskContextInvalid):
        task.record_version(core, dict(TASK_SPEC, objective_text=""), by=OPERATOR)
    with pytest.raises(task.TaskContextInvalid):
        task.record_version(core, dict(TASK_SPEC, candidate_universe={}), by=OPERATOR)


def test_constants_have_defaults_and_registrations(core):
    assert constants.value(core, "const_tool_retry_limit") == 3
    constants.register(core, "const_tool_retry_limit", 5, unit="attempts", scope="core_policy",
                       cutoff_basis="expert_set", set_by=OPERATOR)
    assert constants.value(core, "const_tool_retry_limit") == 5
    with pytest.raises(KeyError):
        constants.value(core, "const_unknown")


def test_registry_invariants_refuse_unitless_and_arbitrary_cutoffs():
    with pytest.raises(criteria.InvariantViolation) as err:
        criteria.check_attribute(dict(ATTRIBUTE, unit=None))
    assert err.value.finding_class == "units"
    with pytest.raises(criteria.InvariantViolation) as err:
        criteria.check_rule(dict(RULE, cutoff={"comparator": "<=", "value": 600, "unit": "Da"}), ATTRIBUTE)
    assert err.value.finding_class == "units"
    with pytest.raises(criteria.InvariantViolation) as err:
        criteria.check_rule(dict(RULE, cutoff_basis="none_evidence_insufficient"), ATTRIBUTE)
    assert err.value.finding_class == "arbitrary_cutoff"


def test_rule_set_needs_an_expert_decision_for_every_proposal(core):
    task_id, _ = task.record_version(core, TASK_SPEC, by=OPERATOR)
    attr_ref, rule_ref = criteria.propose(core, task_id, ATTRIBUTE, RULE, by=AGENT)
    assert (attr_ref, rule_ref) == ("attr_molecular-weight@v1", "rule_molecular-weight@v1")
    with pytest.raises(criteria.InvariantViolation):
        criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    (item,) = review.items(core, [task_id]).values()
    assert item["subject"]["id"] == rule_ref and item["state"] == "open"
    decision = review.decide(core, item, decision="approve", actor=EXPERT, reason_text="", entry="interactive",
                             historical_list_exposure="not_exposed")
    ref = criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    rules = criteria.rule_set(core, task_id)
    assert ref == "rules@v1" and rules["confirmed_by"] == [decision["decision_id"]]
    assert criteria.load(core, rule_ref, task_id)["attribute_ref"] == attr_ref


def test_expert_decisions_need_a_person_and_interactive_entry(core):
    task_id, _ = task.record_version(core, TASK_SPEC, by=OPERATOR)
    criteria.propose(core, task_id, ATTRIBUTE, RULE, by=AGENT)
    (item,) = review.items(core, [task_id]).values()
    with pytest.raises(review.ReviewError) as err:
        review.decide(core, item, decision="approve", actor=AGENT, reason_text="", entry="interactive")
    assert err.value.code == "rejected_unauthorized"
    with pytest.raises(review.ReviewError) as err:
        review.decide(core, item, decision="approve", actor=EXPERT, reason_text="", entry="scripted")
    assert err.value.code == "rejected_unauthorized"
    with pytest.raises(review.ReviewError) as err:
        review.decide(core, item, decision="reject", actor=EXPERT, reason_text=" ", entry="interactive")
    assert err.value.code == "rejected_invalid"
    review.decide(core, item, decision="reject", actor=EXPERT, reason_text="cutoff unsupported", entry="interactive")
    (item,) = review.items(core, [task_id]).values()
    with pytest.raises(review.ReviewError) as err:
        review.decide(core, item, decision="approve", actor=EXPERT, reason_text="", entry="interactive")
    assert err.value.code == "rejected_not_permitted_in_state"
    with pytest.raises(criteria.InvariantViolation):
        criteria.confirm_rule_set(core, task_id, by=OPERATOR)
