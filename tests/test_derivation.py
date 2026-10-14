import pytest

from mas.adapters.drug.registration import EVIDENCE_CATALOG
from mas.core import assessor, criteria, derivation, review, task
from mas.core.broker import Broker, ProviderResponse, ToolContract
from mas.core.journal import actor
from mas.core.models import ModelRoster, ScriptedAdapter
from mas.core.runtime import Core

OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")
SPEC = {
    "objective_text": "Prioritize oral multi-kinase inhibitors for targets T1 and T2", "mode": "conditional",
    "scope_entities": [{"entity_kind": "target", "identifier": "CHEMBL_T1", "label": "T1", "role": "required"}],
    "candidate_universe": {"kind": "enumerated_set", "members": ["a", "b"]},
    "constraints": [{"text": "oral administration", "kind": "route", "hardness": "hard"}],
    "evaluation_scope": {"comparison_basis": "both", "abstention_allowed": True},
    "seed_candidates": [{"candidate_ref": "refotinib", "aliases": ["RF-7"], "is_reference_outcome": True}],
    "case_source_documents": [{"identifiers": [{"scheme": "doi", "value": "10.9/case-source"}], "title": "The case manuscript"}],
}
PAPERS = {
    "10.1/review": "Oral kinase inhibitors with an absolute oral bioavailability above 30% achieved adequate exposure.",
    "10.9/case-source": "Our eleven criteria were applied to 3,171 compounds.",
}


class Search:
    contract = ToolContract(tool_id="tool_s", capability="literature_retrieval", capability_kind="source_retrieval",
                            question_kinds=("search",), contract_version="1", implementation_version="f", purpose_statement="s",
                            evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def invoke(self, q, inputs):
        hits = [{"doi": doi, "pmcid": f"PMC{i}", "title": f"Paper {i}", "is_review": True,
                 "identifiers": [{"scheme": "doi", "value": doi}]} for i, doi in enumerate(PAPERS)]
        return ProviderResponse(values=[{"name": "search_hit", "value": h, "value_kind": "curated"} for h in hits])


class Reader:
    contract = ToolContract(tool_id="tool_r", capability="document_reading", capability_kind="document_reading",
                            question_kinds=("read",), contract_version="1", implementation_version="f", purpose_statement="r",
                            evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")

    def invoke(self, q, inputs):
        doi = inputs["hit"]["doi"]
        doc = {"title": inputs["hit"]["title"], "access_state": "full_text_available", "reading_depth": "full_text",
               "source_hit": {"is_preprint": False},
               "passages": [{"passage_id": "sec1.p1", "kind": "paragraph", "section_path": ["Results"], "text": PAPERS[doi]}]}
        return ProviderResponse(values=[{"name": "document", "value": doc, "value_kind": "curated"}])


GOOD = {"attribute": {"name": "Oral bioavailability", "definition": "Fraction of an oral dose reaching circulation",
                      "measurement_kind": "quantitative", "unit": "%", "direction": "higher_better",
                      "acceptable_value_sources": ["peer_reviewed"], "aggregation": "max",
                      "evidence_request": {"capability": "literature_retrieval", "question_kind": "search",
                                           "parameters": {"query_template": "({names}) AND bioavailability"}},
                      "rationale": "oral route constraint"},
        "rule": {"rule_kind": "preference", "predicate_form": "threshold", "cutoff": {"comparator": ">=", "value": 30, "unit": "%"},
                 "cutoff_basis": "source_stated_value"},
        "expected_change": "ranks orally exposed compounds higher", "falsification_test": "no difference in ranking"}


def script(request):
    if request.role == "retriever":
        return {"queries": [{"query": "oral kinase inhibitor criteria", "rationale": "recall"}]}
    if request.role == "reader":
        if "eleven criteria" in request.messages[0]["content"]:
            raise AssertionError("the case-source document reached the reader")
        return {"claims": [{"passage_id": "sec1.p1", "quoted_span": "absolute oral bioavailability above 30% achieved adequate exposure",
                            "statement": "F above 30% gave adequate exposure", "determination_basis": "measured",
                            "polarity": "supports", "value": 30, "unit": "%", "attribute_hint": "oral bioavailability"}]}
    if request.role == "proposer" and "revising proposals" in request.system:
        claim_id = request.messages[0]["content"].split('"claim_id": "')[1].split('"')[0]
        revised = dict(GOOD, supporting_claim_ids=[claim_id],
                       attribute=dict(GOOD["attribute"], name="Exposure margin", definition="Oral bioavailability as exposure"))
        return {"revisions": [{"index": 1, "action": "withdraw", "reason": "named a compound"},
                              {"index": 2, "action": "withdraw", "reason": "citation did not exist"},
                              {"index": 3, "action": "revise", "proposal": revised, "reason": "claim now matches"}]}
    if request.role == "proposer":
        claim_id = request.messages[0]["content"].split('"claim_id": "')[1].split('"')[0]
        good = dict(GOOD, supporting_claim_ids=[claim_id])
        names_reference = dict(GOOD, supporting_claim_ids=[claim_id],
                               attribute=dict(GOOD["attribute"], name="Similarity to refotinib", rationale="like refotinib"))
        invented = dict(GOOD, supporting_claim_ids=["claim_nonexistent"])
        blocked = dict(GOOD, supporting_claim_ids=[claim_id], attribute=dict(GOOD["attribute"], name="Exposure margin"))
        return {"proposals": [good, names_reference, invented, blocked], "considered_and_rejected": [
            {"name": "Color", "reason": "not measurable from sources"}]}
    if request.role == "critic" and "revision check" in request.messages[0]["content"]:
        assert "quote is about bioavailability" in request.messages[0]["content"]   # the critic sees its earlier findings
        return {"findings": [{"proposal_index": 3, "check": "evidence_support", "verdict": "pass", "severity": "minor",
                              "referent": "supporting_claim_ids", "finding": "now supported"}]}
    if request.role == "critic":
        return {"findings": [{"proposal_index": 3, "check": "evidence_support", "verdict": "fail", "severity": "blocking",
                              "referent": "supporting_claim_ids", "finding": "quote is about bioavailability, not exposure margin"},
                             {"proposal_index": 0, "check": "objective_conformance", "verdict": "pass", "severity": "minor",
                              "referent": "rule.cutoff", "finding": "serves the oral constraint"},
                             {"proposal_index": 0, "check": "evidence_support", "verdict": "fail", "severity": "blocking",
                              "referent": "", "finding": "no referent, must be ignored"}]}
    raise AssertionError(request.role)


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c


def test_derivation_screens_proposals_and_queues_the_rest(core):
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    broker = Broker(core)
    broker.register(Search())
    broker.register(Reader())
    adapter = ScriptedAdapter("s", script, model="scripted-opus")
    roster = ModelRoster({"s": adapter}, {r: "s" for r in ("retriever", "reader", "proposer", "critic")})
    record = derivation.derive(core, broker, roster, task_id, dimensions=[{"dimension": "oral", "focus": "bioavailability"}],
                               catalog=EVIDENCE_CATALOG, by=OPERATOR)
    assert sorted(a["name"] for a in record["accepted"]) == ["Exposure margin", "Oral bioavailability"]
    reasons = {r.get("attribute"): r for r in record["considered_and_rejected"] if "rejection_reason" in r}
    assert any("reference_candidate_scan" in p for p in reasons["Similarity to refotinib"]["validator"])
    assert reasons["Similarity to refotinib"]["rejection_reason"] == "withdrawn"
    assert reasons["Oral bioavailability"]["rejection_reason"] == "withdrawn"          # the invented-citation copy
    assert [r["action"] for r in record["revisions"]] == ["withdraw", "withdraw", "revise"]
    manifest = core.artifacts.payload(record["dimensions"][0]["manifest_id"])
    omitted = {e["omitted_reason"] for e in manifest["excluded"]}
    assert omitted == {"case_source_document", "evaluator_only_artifact"}
    assert review.items(core, [task_id]) == {}          # an evidence-sourced preference needs no expert (trigger table)
    criteria.confirm_rule_set(core, task_id, by=OPERATOR)
    rules = criteria.rule_set(core, task_id)
    assert [(e["rule_ref"], e["confirmed_by"]) for e in rules["entries"]] == [
        ("rule_exposure-margin@v1", "auto:trigger_table"), ("rule_oral-bioavailability@v1", "auto:trigger_table")]
    assert rules["acceptance_label"] == "prespecified" and rules["pending"] == []
    proposer_request = next(r for r in adapter.requests if r.role == "proposer")
    critic_request = next(r for r in adapter.requests if r.role == "critic")
    assert "expected_change" not in critic_request.messages[0]["content"]       # blind critic: no proposer rationale
    assert "Evidence catalog" in proposer_request.messages[0]["content"]


def test_ordering_preferences_score_by_percentile_and_skip_missing():
    def cell(candidate, value, verdict="pass"):
        return {"candidate_ref": candidate, "rule_ref": "rule_f@v1", "rule_kind": "preference", "verdict": verdict, "value": value}
    cells = {"a": [cell("a", 10.0)], "b": [cell("b", 50.0)], "c": [cell("c", 90.0)], "d": [cell("d", None, "unknown_missing")]}
    rules = {"rule_f@v1": {"rule_kind": "preference", "predicate_form": "ordering", "direction": "higher_better"}}
    scores = assessor.preference_scores(cells, rules, {})
    assert scores["c"] == (1.0, 1.0) and scores["a"] == (0.0, 1.0) and scores["b"] == (0.5, 1.0)
    assert scores["d"] == (None, 0.0)
    rules["rule_f@v1"]["direction"] = "lower_better"
    assert assessor.preference_scores(cells, rules, {})["a"] == (1.0, 1.0)


def test_an_attribute_about_a_derived_quantity_declares_the_transformation_and_it_is_applied():
    """A proposer can define a one-sided quantity correctly in prose -- "the excess above 500 g/mol,
    zero for a molecule at or below it" -- while the bound source returns the raw descriptor. Nothing
    applied the difference, so the cell carried the raw weight under the derived quantity's name and
    `lower_better` direction: every molecule inside the band was ranked by how small it was instead of
    tying at zero. The transformation is declared, checked, and applied before aggregation."""
    attribute = {"attribute_id": "attr_mw", "version": 1, "name": "Molecular weight in excess of the upper bound",
                 "definition": "the excess in g/mol above 500, zero at or below it", "unit": "g/mol",
                 "measurement_kind": "quantitative", "direction": "lower_better", "aggregation": "median",
                 "acceptable_value_sources": ["database_entry"], "acceptable_determination_bases": ["derived"],
                 "value_transform": {"kind": "excess_above", "bound": 500, "basis": "source_stated_value",
                                     "source_refs": ["claim_bound"]},
                 "evidence_request": {"capability": "property_estimate", "question_kind": "computed_property",
                                      "parameters": {"property": "MolecularWeight"}}}
    rule = {"rule_id": "rule_mw", "version": 1, "rule_kind": "preference", "predicate_form": "ordering",
            "cutoff": None, "cutoff_basis": "none_evidence_insufficient"}
    criteria.check_attribute(attribute)

    def value_for(weight):
        claims = [{"claim_id": "c1", "admission_state": "admitted", "evidence_kind": "database_entry",
                   "determination_basis": "derived", "value": weight, "unit": "g/mol"}]
        cell, _ = assessor.assess_cell(candidate={"candidate_id": "x"}, attribute=attribute, rule=rule,
                                       rule_set_ref="rules@v1", claims=claims, resolved=True)
        return cell["value"]

    assert value_for(480.6) == 0.0 and value_for(397.0) == 0.0   # inside the bound: tied, not ranked by size
    assert value_for(612.0) == 112.0                              # outside: the excess itself

    banded = dict(attribute, attribute_id="attr_lp", unit="log units", name="Distance outside the band",
                  value_transform={"kind": "distance_outside_band", "low": 2, "high": 4,
                                   "basis": "source_stated_value", "source_refs": ["claim_band"]})
    criteria.check_attribute(banded)
    assert criteria.apply_value_transform(3.4, banded["value_transform"]) == 0.0
    assert criteria.apply_value_transform(1.2, banded["value_transform"]) == pytest.approx(0.8)
    assert criteria.apply_value_transform(5.1, banded["value_transform"]) == pytest.approx(1.1)

    # a bound no source states is the arbitrary cutoff the registry refuses elsewhere
    with pytest.raises(criteria.InvariantViolation, match="arbitrary_cutoff"):
        criteria.check_attribute(dict(attribute, value_transform={"kind": "excess_above", "bound": 500,
                                                                  "basis": "source_stated_value"}))
    with pytest.raises(criteria.InvariantViolation, match="value_transform kind"):
        criteria.check_attribute(dict(attribute, value_transform={"kind": "log", "bound": 1,
                                                                  "basis": "task_constraint"}))
    with pytest.raises(criteria.InvariantViolation, match="numeric bound"):
        criteria.check_attribute(dict(attribute, value_transform={"kind": "excess_above", "bound": "500",
                                                                  "basis": "task_constraint"}))
    with pytest.raises(criteria.InvariantViolation, match="is not below"):
        criteria.check_attribute(dict(banded, value_transform={"kind": "distance_outside_band", "low": 4,
                                                               "high": 2, "basis": "task_constraint"}))
    # and the declaration must survive the normaliser the pipeline runs before validating (ADR-48)
    from mas.core.derivation import _normalize_proposal
    kept = _normalize_proposal({"attribute": attribute, "rule": rule})["attribute"]
    assert kept["value_transform"] == attribute["value_transform"]


def test_an_ordering_rule_uses_the_aggregation_the_attribute_declares(core=None):
    """The cutoff-less ordering path took the best of the usable values whatever the attribute asked
    for. A maximum rises with the number of assays, so the board rewarded having been studied often:
    on the manuscript case sorafenib carried 125 curated VEGFR2 measurements and ranked on their
    maximum against two for the reference compound. The evidence catalog warns of this and every
    target attribute declared `median`."""
    attribute = {"attribute_id": "attr_p", "version": 1, "name": "Curated potency", "definition": "d",
                 "measurement_kind": "quantitative", "unit": "pChEMBL", "direction": "higher_better",
                 "acceptable_value_sources": ["curated_measurement"], "aggregation": "median",
                 "evidence_request": {"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values"}}
    rule = {"rule_id": "rule_p", "version": 1, "rule_kind": "preference", "predicate_form": "ordering",
            "cutoff": None, "cutoff_basis": "none_evidence_insufficient"}

    def claim(value, i):
        return {"claim_id": f"c{i}", "admission_state": "admitted", "evidence_kind": "curated_measurement",
                "determination_basis": "measured", "value": value, "unit": "pChEMBL"}

    # one heavily assayed compound: a single outlying assay must not become its score
    many = [claim(v, i) for i, v in enumerate([7.0, 7.1, 7.2, 7.3, 10.7])]
    cell, _ = assessor.assess_cell(candidate={"candidate_id": "heavy"}, attribute=attribute, rule=rule,
                                   rule_set_ref="rules@v1", claims=many, resolved=True)
    assert cell["verdict"] == "pass" and cell["value"] == 7.2        # the median, not the 10.7 maximum

    few = [claim(9.0, 0), claim(9.0, 1)]
    cell, _ = assessor.assess_cell(candidate={"candidate_id": "light"}, attribute=attribute, rule=rule,
                                   rule_set_ref="rules@v1", claims=few, resolved=True)
    assert cell["value"] == 9.0      # two consistent measurements rank above the heavily assayed compound

    for declared, expected in (("max", 10.7), ("min", 7.0)):
        cell, _ = assessor.assess_cell(candidate={"candidate_id": "heavy"}, rule=rule, rule_set_ref="rules@v1",
                                       attribute=dict(attribute, aggregation=declared), claims=many, resolved=True)
        assert cell["value"] == expected, declared


def test_task_mandated_criteria_come_from_scope_and_constraints_without_duplicates(core):
    from mas.adapters.drug.registration import objective_templates
    spec = dict(SPEC, scope_entities=[
        {"entity_kind": "target", "identifier": "CHEMBL1", "identifier_scheme": "chembl_target", "label": "T1", "role": "required"},
        {"entity_kind": "target", "identifier": "CHEMBL2", "identifier_scheme": "chembl_target", "label": "T2", "role": "optional"}])
    task_id, _ = task.record_version(core, spec, by=OPERATOR)
    added = derivation.objective_criteria(core, task_id, templates=objective_templates, by=OPERATOR)
    # The route constraint yields two criteria: the hard gate on a recorded oral route, and a
    # contextual companion the literature can answer for a Phase III compound, whose route no
    # approval register records. The gate no longer says "approved", because the task admits a
    # Phase III compound and an approved-product criterion can never be satisfied by one.
    assert [a["name"] for a in added] == ["T1 curated potency", "Oral route on record",
                                          "Oral administration reported in the clinical literature"]
    assert derivation.objective_criteria(core, task_id, templates=objective_templates, by=OPERATOR) == []
    (item,) = review.items(core, [task_id]).values()                    # only the hard gate needs an expert
    assert item["subject"]["id"].startswith("rule_oral-route-on-record")
    ref = criteria.confirm_rule_set(core, task_id, by=OPERATOR, allow_pending=True)
    entries = criteria.rule_set(core, task_id, ref)["entries"]
    # the hard gate is held out pending its decision; the companion enters the set but is
    # contextual, so `preference_scores` passes over it and one requirement is not scored twice
    assert sorted(e["rule_ref"] for e in entries) == [
        "rule_oral-administration-reported-in-the-clinical-literature@v1", "rule_t1-curated-potency@v1"]
    kinds = {e["rule_ref"]: e["rule_kind"] for e in entries}
    assert kinds["rule_oral-administration-reported-in-the-clinical-literature@v1"] == "exploratory_consideration"
    assert [r for r, k in kinds.items() if k == "preference"] == ["rule_t1-curated-potency@v1"]


def test_a_disputed_preference_scores_the_board_and_the_rule_set_says_so(core):
    """The trigger table admits a preference rule without an expert, and it does so whether or not a
    critic finding against that rule is still open. Such a rule both scores candidates and sits in
    `pending[]` -- a list that on its own reads as "did not enter the set". The entry has to say which."""
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    attribute = {"name": "Affinity on an independent curation", "definition": "curated affinity at the required target",
                 "measurement_kind": "quantitative", "unit": "pChEMBL", "direction": "higher_better",
                 "acceptable_value_sources": ["curated_measurement"], "aggregation": "consensus",
                 "evidence_request": {"capability": "interaction_evidence_lookup", "question_kind": "gtopdb_affinity",
                                      "parameters": {"target_chembl_id": "CHEMBL_T1"}}}
    rule = {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
            "cutoff_basis": "none_evidence_insufficient"}
    _, rule_ref = criteria.propose(core, task_id, attribute, rule, by=OPERATOR,
                                   dispute={"finding": "the identifier mapping could not be checked"})
    # the trigger table lets it through, and it is read from the rule, the attribute and its bounds together
    assert not criteria.needs_expert(dict(rule, rule_kind="preference"), attribute)

    with pytest.raises(criteria.InvariantViolation, match="unconfirmed"):
        criteria.confirm_rule_set(core, task_id, by=OPERATOR)                 # blocked without allow_pending

    ref = criteria.confirm_rule_set(core, task_id, by=OPERATOR, allow_pending=True)
    record = criteria.rule_set(core, task_id, ref)
    entry = next(e for e in record["entries"] if e["rule_ref"] == rule_ref)
    assert entry["disputed"] is True and entry["confirmed_by"] == "auto:trigger_table"
    assert rule_ref in record["pending"] and record["pending_but_scoring"] == [rule_ref]
    assert record["acceptance_label"] == "exploratory"
    assert any("score candidates while disputed" in r for r in record["acceptance_reasons"])


def test_range_claims_straddling_a_cutoff_are_conflicts_not_passes():
    attribute = {"attribute_id": "attr_f", "version": 1, "name": "F", "definition": "d", "measurement_kind": "quantitative",
                 "unit": "%", "direction": "higher_better", "acceptable_value_sources": ["peer_reviewed"], "aggregation": "consensus",
                 "evidence_request": {"capability": "literature_retrieval", "question_kind": "search"}}
    rule = {"rule_id": "rule_f", "version": 1, "rule_kind": "preference", "cutoff": {"comparator": ">=", "value": 30, "unit": "%"},
            "cutoff_basis": "source_stated_value"}
    def claim(low, high):
        return {"claim_id": f"c{low}", "admission_state": "admitted", "evidence_kind": "peer_reviewed",
                "determination_basis": "measured", "value": None, "value_low": low, "value_high": high, "unit": "%"}
    straddling, _ = assessor.assess_cell(candidate={"candidate_id": "x"}, attribute=attribute, rule=rule, rule_set_ref="rules@v1",
                                         claims=[claim(20, 40)], resolved=True)
    above, _ = assessor.assess_cell(candidate={"candidate_id": "x"}, attribute=attribute, rule=rule, rule_set_ref="rules@v1",
                                    claims=[claim(35, 45)], resolved=True)
    assert straddling["verdict"] == "unknown_conflicted" and above["verdict"] == "pass"


def test_counter_evidence_is_attributed_from_the_values_the_verdict_was_computed_from():
    """F8. Conflict attribution re-derived sides from the raw observation against a cutoff that lives
    on the transformed scale, and skipped range claims because their `value` is None. Reproduced from
    the handoff fixture: raw 20 and 50, excess above 30, assessed 0 and 20, median 10, pass if `>= 10`.
    The cell correctly passed while the claim that transformed to 0 was reported as no conflict at all,
    so the score was right and its own audit trail denied the counter-evidence."""
    attribute = {"attribute_id": "attr_x", "version": 1, "name": "Excess above the stated bound",
                 "definition": "the excess above 30", "measurement_kind": "quantitative", "unit": "u",
                 "direction": "lower_better", "acceptable_value_sources": ["curated_measurement"],
                 "aggregation": "median",
                 "value_transform": {"kind": "excess_above", "bound": 30.0, "basis": "source_stated_value",
                                     "source_refs": ["c0"]},
                 "evidence_request": {"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values"}}
    rule = {"rule_id": "rule_x", "version": 1, "rule_kind": "preference", "predicate_form": "threshold",
            "cutoff": {"comparator": ">=", "value": 10.0, "unit": "u"}, "cutoff_basis": "source_stated_value"}

    def claim(i, value=None, low=None, high=None):
        return {"claim_id": f"c{i}", "admission_state": "admitted", "evidence_kind": "curated_measurement",
                "determination_basis": "measured", "value": value, "value_low": low, "value_high": high, "unit": "u"}

    cell, _ = assessor.assess_cell(candidate={"candidate_id": "x"}, attribute=attribute, rule=rule,
                                   rule_set_ref="rules@v1", claims=[claim(0, 20.0), claim(1, 50.0)], resolved=True)
    assert cell["verdict"] == "pass" and cell["value"] == 10.0          # median of the transformed 0 and 20
    assert cell["conflicting_claim_refs"] == ["c0"], "the claim transformed to 0 is the counter-evidence"

    # a reported range contributes both ends, so it is attributable too -- it was skipped entirely before
    cell, _ = assessor.assess_cell(candidate={"candidate_id": "y"}, attribute=attribute, rule=rule,
                                   rule_set_ref="rules@v1",
                                   claims=[claim(0, low=20.0, high=50.0), claim(1, 60.0)], resolved=True)
    assert "c0" in cell["conflicting_claim_refs"], "a range straddling the cutoff is counter-evidence"

    # without a transform the raw and evaluated values coincide, so behaviour is unchanged
    plain = dict(attribute); plain.pop("value_transform")
    cell, _ = assessor.assess_cell(candidate={"candidate_id": "z"}, attribute=plain, rule=rule,
                                   rule_set_ref="rules@v1", claims=[claim(0, 2.0), claim(1, 50.0)], resolved=True)
    assert cell["verdict"] == "pass" and cell["conflicting_claim_refs"] == ["c0"]


def test_an_attribute_may_accept_a_stated_claim_because_the_reader_writes_that_basis():
    """F9. `reading.extract_claims` offers `asserted` in its extraction enum and the reader uses it,
    but it was absent from `criteria.DETERMINATION_BASES`, so `check_attribute` refused any attribute
    naming it and `usable_claims` set every such claim aside. Measured on the manuscript task: 60 of
    the 127 claims behind registered criteria carry it, and no attribute could legally accept one.
    It stays out of the defaults, so an attribute that does not ask for it still sees none."""
    assert "asserted" in criteria.DETERMINATION_BASES
    assert "asserted" not in assessor.DEFAULT_DETERMINATION_BASES

    attribute = {"attribute_id": "attr_t", "version": 1, "name": "Reported tolerability", "definition": "d",
                 "measurement_kind": "quantitative", "unit": "% of patients", "direction": "lower_better",
                 "acceptable_value_sources": ["peer_reviewed_primary"], "aggregation": "median",
                 "acceptable_determination_bases": ["asserted"],
                 "evidence_request": {"capability": "literature_retrieval", "question_kind": "search",
                                      "parameters": {"query_template": "({names}) AND tolerability",
                                                     "relevance_terms": ["tolerability"], "search_limit": 10}}}
    assert not criteria.check_attribute(attribute), "an attribute may now ask for a stated basis"

    stated = {"claim_id": "c1", "admission_state": "admitted", "evidence_kind": "peer_reviewed_primary",
              "determination_basis": "asserted", "value": 12.0, "unit": "% of patients"}
    usable, set_aside = assessor.usable_claims([stated], attribute)
    assert [c["claim_id"] for c in usable] == ["c1"], "the claim the reader wrote is now usable"

    # an attribute that does not name it still sees nothing, so an assertion is never counted by omission
    silent = dict(attribute); silent.pop("acceptable_determination_bases")
    usable, set_aside = assessor.usable_claims([stated], silent)
    assert usable == [] and [c["claim_id"] for c in set_aside] == ["c1"]


def test_a_rule_set_cannot_call_itself_prespecified_on_a_registration_that_does_not_resolve(core):
    """F6. `acceptance_label` was `prespecified` whenever nothing else had gone wrong, and
    `preregistration_ref` was an unvalidated parameter: a confirmation produced
    `prespecified` with `preregistration_ref: null`. The label asserts *when* the set was fixed, so
    it cannot rest on a field nobody checks."""
    task_id, _ = task.record_version(core, SPEC, by=OPERATOR)
    attribute = {"attribute_id": "attr_q", "version": 1, "name": "Quantity", "definition": "d",
                 "measurement_kind": "quantitative", "unit": "u", "direction": "higher_better",
                 "acceptable_value_sources": ["curated_measurement"], "aggregation": "median",
                 "evidence_request": {"capability": "interaction_evidence_lookup",
                                      "question_kind": "pchembl_values", "parameters": {"target_chembl_id": "C1"}}}
    rule = {"rule_id": "rule_q", "version": 1, "rule_kind": "preference", "predicate_form": "ordering",
            "cutoff": None, "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty",
            "on_inapplicable": "unknown_no_penalty", "on_conflict": "unknown_no_penalty"}
    criteria.propose(core, task_id, attribute, rule, by=OPERATOR)

    # a reference to an artifact that does not exist cannot buy the label
    ref = criteria.confirm_rule_set(core, task_id, by=OPERATOR, coverage_floor=0.5,
                                    preregistration_ref="pre_does_not_exist")
    rs = criteria.rule_set(core, task_id, ref)
    assert rs["acceptance_label"] == "exploratory"
    assert rs["preregistration_ref"] is None
    assert any("does not resolve" in r for r in rs["acceptance_reasons"])

    # a registration that does resolve is honoured
    real = core.artifacts.put("preregistration", {"task_id": task_id, "note": "fixed before results"})
    ref = criteria.confirm_rule_set(core, task_id, by=OPERATOR, coverage_floor=0.5, preregistration_ref=real)
    rs = criteria.rule_set(core, task_id, ref)
    assert rs["preregistration_ref"] == real and rs["acceptance_label"] == "prespecified"


def test_one_observation_counted_once_however_many_times_the_reader_emitted_it():
    """Measured on the clean derivation of 14 October 2026: 388 claims came from 15 distinct
    documents, and 18 (document, quoted span) pairs had been extracted more than once -- one table
    row about a marketed inhibitor seven times from a single paper. Nothing collapsed them, so each
    copy entered the aggregate as an independent value. A median over seven copies of one number is
    that number, so this biases the aggregate, not just the reading cost."""
    attribute = {"attribute_id": "attr_p", "version": 1, "name": "Curated potency", "definition": "d",
                 "measurement_kind": "quantitative", "unit": "pChEMBL", "direction": "higher_better",
                 "acceptable_value_sources": ["curated_measurement"], "aggregation": "median",
                 "evidence_request": {"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values"}}
    rule = {"rule_id": "rule_p", "version": 1, "rule_kind": "preference", "predicate_form": "ordering",
            "cutoff": None, "cutoff_basis": "none_evidence_insufficient"}

    def claim(cid, value, span, source="src_doi_10.1/a"):
        return {"claim_id": cid, "admission_state": "admitted", "evidence_kind": "curated_measurement",
                "determination_basis": "measured", "value": value, "unit": "pChEMBL",
                "source_ref": source, "location": {"quoted_span": span}}

    # the real shape: one span repeated, plus two genuinely different observations
    claims = [claim(f"c{i}", 9.5, "Sunitinib | VEGFR1-3, KIT, CSF1R") for i in range(7)]
    claims += [claim("d1", 7.0, "a different sentence reporting 7.0"),
               claim("d2", 7.2, "another paper's figure", source="src_doi_10.1/b")]

    usable, set_aside = assessor.usable_claims(claims, attribute)
    assert [c["claim_id"] for c in usable] == ["c0", "d1", "d2"], "the repeat is one observation"
    dupes = [c for c in set_aside if c.get("set_aside_reason") == "duplicate_observation"]
    assert len(dupes) == 6 and all(c["duplicate_of"] == "c0" for c in dupes)

    cell, _ = assessor.assess_cell(candidate={"candidate_id": "x"}, attribute=attribute, rule=rule,
                                   rule_set_ref="rules@v1", claims=claims, resolved=True)
    assert cell["value"] == 7.2, "median of 9.5, 7.0, 7.2 -- not of seven 9.5s"

    # a table and a sentence reporting the same figure separately are still two reports
    two_reports = [claim("e1", 8.0, "table row: 8.0"), claim("e2", 8.0, "the text says 8.0")]
    usable, set_aside = assessor.usable_claims(two_reports, attribute)
    assert len(usable) == 2 and not [c for c in set_aside if c.get("set_aside_reason") == "duplicate_observation"]
