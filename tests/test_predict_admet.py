"""The predicted-property panel: what it answers, what it refuses, and what the catalog promises.

No test here needs torch, rdkit or chemprop. The predictor is reached by subprocess, so a recorded
worker output replayed by a stub worker exercises everything between the provider and the
predictor's stdout -- the pipe, the JSON lines, the panel check, the cache files -- while the
predictor itself is never started. `tests/test_live_predict.py` is where the real one runs.
"""

import inspect
import json
import sys
from pathlib import Path

import pytest

from mas.adapters.drug.registration import CAPABILITY_BINDINGS, EVIDENCE_CATALOG, EVIDENCE_KINDS, register
from mas.adapters.predict import admet
from mas.core import bound_support, criteria, evidence
from mas.core.broker import Broker, ToolError
from mas.core.journal import actor

FIXTURE = Path(__file__).parent / "fixtures" / "admet_worker_output.jsonl"
WHO = actor("agent", "retriever-1", "evidence_retriever")
ENTRY = next(e for e in EVIDENCE_CATALOG if e["question_kind"] == "admet_prediction")


def recorded() -> list[dict]:
    return [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]


def recorded_rows() -> list[dict]:
    return [record for record in recorded() if record["kind"] == "row"]


def predicted() -> dict:
    return next(row for row in recorded_rows() if row.get("values"))


def refused() -> dict:
    return next(row for row in recorded_rows() if row.get("error"))


def write_universe(tmp_path: Path, members: list[tuple[str, str, str | None]]) -> Path:
    """A universe file and the structure file beside it. `members` are (inchikey, chembl_id, smiles)."""
    universe = tmp_path / "universe_chembl.json"
    universe.write_text(json.dumps({
        "source": "test universe", "retrieved_at": "2026-10-14",
        "universe": [{"name": f"COMPOUND {chembl}", "inchikey": key, "chembl_id": chembl, "max_phase": 4.0,
                      "synonyms": [], "fields": {}} for key, chembl, _ in members]}), encoding="utf-8")
    (tmp_path / "universe_smiles.json").write_text(
        json.dumps({chembl: smiles for _, chembl, smiles in members}), encoding="utf-8")
    return universe


class Replay:
    """A stub worker replaying the recorded output, run by this interpreter."""

    def __init__(self, script: Path, counter: Path):
        self.script, self.counter = script, counter

    def runs(self) -> int:
        return len(self.counter.read_text(encoding="utf-8")) if self.counter.exists() else 0


@pytest.fixture
def replay(tmp_path, monkeypatch) -> Replay:
    script, counter = tmp_path / "stub_worker.py", tmp_path / "worker_runs"
    script.write_text(
        "import pathlib, sys\n"
        "sys.stdin.read()\n"                       # the real worker reads every structure before predicting
        f"pathlib.Path({str(counter)!r}).open('a').write('x')\n"
        # bytes, so the replay is byte-for-byte what the predictor wrote, whatever the locale is
        f"sys.stdout.buffer.write(pathlib.Path({str(FIXTURE)!r}).read_bytes())\n", encoding="utf-8")
    monkeypatch.setattr(admet, "WORKER", script)
    monkeypatch.setattr(admet, "interpreter", lambda python=None: sys.executable)
    return Replay(script, counter)


@pytest.fixture
def provider(tmp_path, replay):
    """The provider over a two-member universe: one structure the fixture holds, one with none."""
    row = predicted()
    universe = write_universe(tmp_path, [("AAAAAAAAAAAAAA-BBBBBBBBBB-N", "CHEMBL1", row["smiles"]),
                                         ("CCCCCCCCCCCCCC-DDDDDDDDDD-N", "CHEMBL2", None),
                                         ("EEEEEEEEEEEEEE-FFFFFFFFFF-N", "CHEMBL3", refused()["smiles"])])
    return admet.AdmetPrediction(admet.StructureIndex(universe), admet.PanelCache(tmp_path / "cache"))


# --- what the route answers -------------------------------------------------------------------

def test_an_endpoint_outside_the_panel_is_refused_before_the_predictor_is_started(provider, replay):
    with pytest.raises(ToolError) as refusal:
        provider.invoke("admet_prediction", {"identifier": "AAAAAAAAAAAAAA-BBBBBBBBBB-N", "endpoint": "Vibes"})
    assert refusal.value.error_class == "input_invalid" and refusal.value.retryable is False
    assert replay.runs() == 0


def test_a_compound_with_no_structure_is_unknown_and_never_a_failure(provider, replay):
    """A member the universe has no structure for is the shape `UniverseRecordField` already has for
    a field ChEMBL left empty: no value, so the cell is unknown. The warning says it was the
    structure that was missing, so the absence is readable rather than an empty answer."""
    response = provider.invoke("admet_prediction", {"identifier": "CCCCCCCCCCCCCC-DDDDDDDDDD-N",
                                                    "endpoint": "Bioavailability_Ma"})
    assert response.values == [] and response.outcome == "ok"
    assert "no structure" in response.warnings[0]
    assert replay.runs() == 0            # nothing to predict from, so nothing was started


def test_a_structure_the_predictor_refuses_is_unknown_and_says_which_it_was(provider):
    response = provider.invoke("admet_prediction", {"identifier": "EEEEEEEEEEEEEE-FFFFFFFFFF-N",
                                                    "endpoint": "Bioavailability_Ma"})
    assert response.values == []
    assert refused()["error"] in response.warnings[0]


def test_a_prediction_names_the_predictor_the_endpoint_and_the_dataset_behind_it(provider):
    row = predicted()
    response = provider.invoke("admet_prediction", {"identifier": "AAAAAAAAAAAAAA-BBBBBBBBBB-N",
                                                    "endpoint": "Bioavailability_Ma"})
    value, = response.values
    assert value["value"] == pytest.approx(row["values"]["Bioavailability_Ma"])
    assert (value["value_kind"], value["determination_basis"]) == ("predicted", "predicted")
    assert value["unit"] == "probability" == admet.ENDPOINTS["Bioavailability_Ma"]["unit"]
    # and the claim built from it carries that basis rather than inferring a measurement
    assert evidence.determination_basis(value) == "predicted"
    where = value["conditions"]
    assert where["predictor_package"] == "admet-ai" and where["predictor_version"]
    assert where["endpoint"] == "Bioavailability_Ma" and where["training_dataset"] == "Bioavailability_Ma"
    assert where["task_type"] == "classification" and where["decision_boundary"] == 0.5
    assert where["canonical_smiles"] == row["smiles"] and where["smiles_sha256"] == admet.digest(row["smiles"])
    assert where["reference"].startswith("https://tdcommons.ai/")
    assert where["holdout_metric"]["auroc"] and where["training_rows"] == 640
    assert response.data_version.startswith("admet-ai ")


def test_a_regression_endpoint_carries_the_panel_unit_and_no_decision_boundary(provider):
    value, = provider.invoke("admet_prediction", {"identifier": "AAAAAAAAAAAAAA-BBBBBBBBBB-N",
                                                  "endpoint": "Half_Life_Obach"}).values
    assert value["unit"] == "h" and value["conditions"]["task_type"] == "regression"
    assert value["conditions"]["decision_boundary"] is None


def test_the_panel_is_predicted_once_per_structure_and_read_from_the_cache_after(tmp_path, replay):
    """The expensive thing is starting the predictor, not asking it, and the panel answers every
    endpoint at once -- so a second endpoint of the same compound, and a later run over the same
    cache directory, must not start it again."""
    row = predicted()
    universe = write_universe(tmp_path, [("AAAAAAAAAAAAAA-BBBBBBBBBB-N", "CHEMBL1", row["smiles"])])
    cache = admet.PanelCache(tmp_path / "cache")
    first = admet.AdmetPrediction(admet.StructureIndex(universe), cache)
    inputs = {"identifier": "AAAAAAAAAAAAAA-BBBBBBBBBB-N", "endpoint": "hERG"}
    assert first.invoke("admet_prediction", inputs).values[0]["value"] == pytest.approx(row["values"]["hERG"])
    assert replay.runs() == 1
    first.invoke("admet_prediction", dict(inputs, endpoint="AMES"))
    assert replay.runs() == 1                                   # one row, every endpoint
    assert cache.path(row["smiles"]).exists()
    fresh = admet.AdmetPrediction(admet.StructureIndex(universe), admet.PanelCache(tmp_path / "cache"))
    assert fresh.invoke("admet_prediction", inputs).values[0]["value"] == pytest.approx(row["values"]["hERG"])
    assert replay.runs() == 1                                   # a new process reads the files

    warmed = admet.PanelCache(tmp_path / "cache").warm([row["smiles"]])
    assert (warmed["already_cached"], warmed["computed"]) == (1, 0) and replay.runs() == 1


def test_warming_reports_what_it_computed_and_what_the_predictor_refused(tmp_path, replay):
    report = admet.PanelCache(tmp_path / "cache").warm([row["smiles"] for row in recorded_rows()])
    assert report["requested"] == len(recorded_rows()) and replay.runs() == 1
    assert report["computed"] == len([r for r in recorded_rows() if r.get("values")])
    assert report["refused"] == len([r for r in recorded_rows() if r.get("error")])
    assert report["endpoints"] == len(admet.ENDPOINTS) and report["panel_version"] == admet.PANEL_VERSION


# --- what the route refuses when the predictor is not there -----------------------------------

def test_without_an_interpreter_the_route_refuses_deterministically(tmp_path, monkeypatch, core):
    """A missing environment is a fact about this machine, not about the compound. It must not read
    as "no data": the refusal is non-retryable, names what was tried and names the setting that
    fixes it."""
    monkeypatch.setattr(admet, "candidates", lambda python=None: ["/nonexistent/python"])
    monkeypatch.setattr(admet, "_PROBED", {})
    assert admet.available() is False and admet.interpreter() is None

    universe = write_universe(tmp_path, [("AAAAAAAAAAAAAA-BBBBBBBBBB-N", "CHEMBL1", "CCO")])
    provider = admet.AdmetPrediction(admet.StructureIndex(universe), admet.PanelCache(tmp_path / "cache"))
    inputs = {"identifier": "AAAAAAAAAAAAAA-BBBBBBBBBB-N", "endpoint": "hERG"}
    with pytest.raises(ToolError) as refusal:
        provider.invoke("admet_prediction", inputs)
    assert refusal.value.error_class == "environment_missing" and refusal.value.retryable is False
    assert "/nonexistent/python" in str(refusal.value) and "predict.python" in str(refusal.value)

    delays = []
    broker = Broker(core, sleep=delays.append)
    broker.register(provider)
    result = broker.call("run_x", "predicted_property_lookup", "admet_prediction", inputs, requesting_actor=WHO)
    assert result.outcome == "failed" and result.error["class"] == "environment_missing"
    assert delays == []                                         # a missing environment is not a transient one


def test_a_missing_structure_file_refuses_rather_than_reporting_a_universe_of_unknowns(tmp_path):
    universe = write_universe(tmp_path, [("AAAAAAAAAAAAAA-BBBBBBBBBB-N", "CHEMBL1", "CCO")])
    (tmp_path / "universe_smiles.json").unlink()
    index = admet.StructureIndex(universe)
    with pytest.raises(ToolError) as refusal:
        index.smiles_for("AAAAAAAAAAAAAA-BBBBBBBBBB-N")
    assert refusal.value.error_class == "environment_missing" and refusal.value.retryable is False


def test_a_panel_that_is_not_the_recorded_one_is_refused(tmp_path, replay):
    """The recorded table says what each number means. A package that moved an endpoint would have
    its values labelled by the old table, which is the one failure this route must not have."""
    cache = admet.PanelCache(tmp_path / "cache")
    installed = [dict(entry) for entry in next(r for r in recorded() if r["kind"] == "panel")["endpoints"]]
    cache._check_panel(installed)                               # the recorded panel is accepted
    installed[0]["task_type"] = "classification"
    with pytest.raises(ToolError) as refusal:
        cache._check_panel(installed)
    assert refusal.value.error_class == "schema_violation" and refusal.value.retryable is False
    with pytest.raises(ToolError):
        cache._check_panel(installed[1:])                       # an endpoint that disappeared


# --- registration -----------------------------------------------------------------------------

def test_the_panel_is_registered_with_a_universe_and_a_predictor_and_not_otherwise(tmp_path, monkeypatch, core):
    universe = str(write_universe(tmp_path, [("AAAAAAAAAAAAAA-BBBBBBBBBB-N", "CHEMBL1", "CCO")]))

    def capabilities(**kw):
        broker = Broker(core)
        register(broker, literature=False, cache_dir=str(tmp_path / "cache"), **kw)
        return {c.capability for c in broker.contracts()}

    monkeypatch.setattr(admet, "available", lambda python=None: True)
    assert "predicted_property_lookup" in capabilities(universe_file=universe)
    assert "predicted_property_lookup" not in capabilities(universe_file=universe, predict=False)
    assert "predicted_property_lookup" not in capabilities()     # no universe, so no structures
    monkeypatch.setattr(admet, "available", lambda python=None: False)
    assert "predicted_property_lookup" not in capabilities(universe_file=universe)
    # explicitly asked for: registered anyway, so a criterion bound to it refuses loudly per cell
    # instead of being answered by nothing at all
    assert "predicted_property_lookup" in capabilities(universe_file=universe, predict=True)


def test_the_provider_resolves_through_the_core_capability_kind_it_is_bound_to(core, provider):
    assert CAPABILITY_BINDINGS["predicted_property_lookup"] == "attribute_estimate"
    assert provider.contract.capability_kind == CAPABILITY_BINDINGS[provider.contract.capability]
    broker = Broker(core)
    broker.register(provider)
    assert broker.resolve("attribute_estimate", "admet_prediction") == [provider]
    # a route that demands a measurement is not answered by a predictor
    result = broker.call("run_x", "predicted_property_lookup", "admet_prediction",
                         {"identifier": "AAAAAAAAAAAAAA-BBBBBBBBBB-N", "endpoint": "hERG"},
                         requesting_actor=WHO, required_value_kind="measured")
    assert (result.outcome, result.absence_reason) == ("not_attempted", "not_configured")


# --- the catalog and the vocabularies ---------------------------------------------------------

def test_the_catalog_offers_the_whole_panel_and_nothing_it_cannot_answer():
    """The point of the entry is that the deriving agents choose the endpoint, so the entry holds
    every one of them -- curating it here would decide, quietly and in advance, which questions
    about absorption, metabolism and toxicity a screen is allowed to ask."""
    assert set(ENTRY["units"]) == set(ENTRY["endpoints"]) == set(admet.ENDPOINTS)
    assert list(ENTRY["units"]) == list(admet.ENDPOINTS)         # the package's own order, unreordered
    assert len(admet.ENDPOINTS) == len(admet.MODEL_ENDPOINTS) + len(admet.DESCRIPTOR_ENDPOINTS)
    assert all(ENTRY["units"][e] for e in admet.ENDPOINTS)       # every endpoint is bindable: units are required
    for endpoint in admet.CLASSIFIERS:
        spec = admet.ENDPOINTS[endpoint]
        assert spec["unit"] == "probability" and spec["decision_boundary"] == 0.5
        assert "[0,1]" in ENTRY["endpoints"][endpoint]
    for endpoint in admet.DESCRIPTOR_ENDPOINTS:
        assert admet.ENDPOINTS[endpoint]["training_dataset"] is None
        assert "not a trained model" in ENTRY["endpoints"][endpoint]
    assert str(len(admet.ENDPOINTS)) in ENTRY["parameters"]["endpoint"]


def test_the_recorded_panel_is_in_the_package_s_own_order_and_says_what_the_package_says():
    """The order is part of what must not be curated: a panel regrouped by category here would
    offer the deriving agents a different reading order from the one the package publishes, and
    the first version of this table did exactly that (Metabolism ahead of Excretion) -- caught by
    the live check, which is why the recorded worker output is compared here too, where the offline
    suite can see it."""
    installed = next(record for record in recorded() if record["kind"] == "panel")["endpoints"]
    assert [entry["id"] for entry in installed] == list(admet.ENDPOINTS)
    for entry in installed:
        spec = admet.ENDPOINTS[entry["id"]]
        assert [entry[field] for field in admet.PANEL_FIELDS_CHECKED] == \
               [spec[field] for field in admet.PANEL_FIELDS_CHECKED]
        assert spec["training_rows"] == entry["size"]


def test_the_catalog_entry_declares_the_kind_and_the_basis_its_tool_produces(provider):
    assert ENTRY["capability"] == provider.contract.capability
    assert ENTRY["question_kind"] in provider.contract.question_kinds
    assert ENTRY["evidence_kind"] == provider.contract.evidence_kind_produced == "model_prediction"
    assert ENTRY["evidence_kind"] in EVIDENCE_KINDS
    assert ENTRY["determination_basis"] == "predicted" and ENTRY["determination_basis"] in criteria.DETERMINATION_BASES
    assert provider.contract.claim_strength_ceiling == "predicted"
    # the note has to tell the proposer both halves of the gate, or the entry is unusable end to end
    assert '["model_prediction"]' in ENTRY["note"] and '["predicted"]' in ENTRY["note"]
    assert "model_decision_boundary" in ENTRY["note"]


PREDICTED_ATTRIBUTE = {
    "name": "Predicted oral bioavailability", "measurement_kind": "quantitative", "unit": "probability",
    "definition": "The panel's predicted probability that the compound is orally bioavailable",
    "direction": "higher_better", "acceptable_value_sources": ["model_prediction"], "aggregation": "median",
    "acceptable_determination_bases": ["predicted"],
    "evidence_request": {"capability": "predicted_property_lookup", "question_kind": "admet_prediction",
                         "identifier_scheme": "inchikey", "parameters": {"endpoint": "Bioavailability_Ma"}},
    "rationale": "absorption is measured for a few dozen drugs and predictable for all of them"}
BOUNDARY_RULE = {"rule_kind": "preference", "predicate_form": "threshold",
                 "cutoff": {"comparator": ">=", "value": 0.5, "unit": "probability"},
                 "cutoff_basis": "model_decision_boundary", "on_missing": "unknown_no_penalty"}


def test_a_predicted_attribute_declares_the_predicted_basis_alone_and_its_claims_then_count(core):
    """What `assessor.usable_claims` requires, end to end: the claim's `evidence_kind` must be in
    `acceptable_value_sources` and its `determination_basis` in `acceptable_determination_bases`,
    which defaults to (measured, derived) -- so an attribute that does not name `predicted` sees
    every prediction set aside, which reads as no data. `check_attribute` then refuses `predicted`
    beside any other basis, so a predicted quantity is its own attribute."""
    from mas.core.assessor import DEFAULT_DETERMINATION_BASES, usable_claims

    criteria.check_attribute(PREDICTED_ATTRIBUTE)
    criteria.check_rule(BOUNDARY_RULE, PREDICTED_ATTRIBUTE)
    assert "predicted" not in DEFAULT_DETERMINATION_BASES
    with pytest.raises(criteria.InvariantViolation):
        criteria.check_attribute(dict(PREDICTED_ATTRIBUTE, acceptable_determination_bases=["predicted", "measured"]))

    claim = {"claim_id": "claim_1", "admission_state": "admitted", "evidence_kind": "model_prediction",
             "determination_basis": "predicted", "value": 0.94, "unit": "probability"}
    attribute = dict(PREDICTED_ATTRIBUTE, attribute_id="attr_pred", version=1)
    usable, set_aside = usable_claims([claim], attribute)
    assert [c["claim_id"] for c in usable] == ["claim_1"] and set_aside == []
    undeclared = {k: v for k, v in attribute.items() if k != "acceptable_determination_bases"}
    usable, set_aside = usable_claims([claim], undeclared)
    assert usable == [] and [c["set_aside_reason"] for c in set_aside] == ["determination_basis_not_accepted"]
    measured_only = dict(attribute, acceptable_value_sources=["curated_measurement"])
    usable, set_aside = usable_claims([claim], measured_only)
    assert usable == [] and [c["set_aside_reason"] for c in set_aside] == ["evidence_kind_not_accepted"]


def test_the_validator_refuses_a_predicted_route_the_attribute_does_not_accept():
    """The pairing is refused where it can be fixed -- in the pool -- rather than at assessment
    time, where it looks like a compound nobody has data for."""
    from mas.core.derivation import _normalize_proposal, validate_proposal

    claims = {"claim_1": {"claim_id": "claim_1", "determination_basis": "measured", "value": 0.5,
                          "unit": "probability"}}
    undeclared = {k: v for k, v in PREDICTED_ATTRIBUTE.items() if k != "acceptable_determination_bases"}
    item = {"attribute": undeclared, "rule": BOUNDARY_RULE, "supporting_claim_ids": ["claim_1"]}
    problems = validate_proposal(item, claims_by_id=claims, reference_labels=[], catalog=EVIDENCE_CATALOG)
    assert [p for p in problems if "acceptable_determination_bases" in p], problems

    declared = _normalize_proposal(dict(item, attribute=PREDICTED_ATTRIBUTE))
    assert declared["attribute"]["acceptable_determination_bases"] == ["predicted"]   # survives normalisation
    assert not [p for p in validate_proposal(declared, claims_by_id=claims, reference_labels=[],
                                             catalog=EVIDENCE_CATALOG) if "acceptable_determination_bases" in p]


def test_a_classifier_boundary_is_a_registered_basis_that_still_needs_a_decision():
    """0.5 is the model's own line, so no claim in the ledger states it and none is asked for. That
    is not a licence to score: the basis claims an authority of its own, exactly as `expert_set`
    does, so the bound needs a decision before the rule may score. Left unclassified in
    `bound_support` it would come out `unaudited` -- which that module says is not a pass -- and
    would score anyway."""
    assert "model_decision_boundary" in criteria.CUTOFF_BASES
    assert "model_decision_boundary" in bound_support.AUTHORITY_BASES
    report = bound_support.validate(PREDICTED_ATTRIBUTE, BOUNDARY_RULE, claims=[])
    bound, = report["bounds"]
    assert (bound["state"], bound["authority"]) == ("authority_basis", "decision_required")
    assert report["blocking"] == [] and report["unsupported_paths"] == []
    assert criteria.needs_expert(BOUNDARY_RULE, PREDICTED_ATTRIBUTE, support=report) is True
    reasons = [r["reason"] for r in criteria.authority_requirements(BOUNDARY_RULE, PREDICTED_ATTRIBUTE, support=report)]
    assert "cutoff_basis_model_decision_boundary" in reasons


def test_a_prediction_is_recorded_as_a_model_prediction_and_not_as_a_database_entry(core, provider):
    """The source table says what each claim rests on. A prediction recorded as a database entry
    would tell every reader of it that somebody looked up what a model computed."""
    from mas.core.broker import ToolResult

    value, = provider.invoke("admet_prediction", {"identifier": "AAAAAAAAAAAAAA-BBBBBBBBBB-N",
                                                  "endpoint": "hERG"}).values
    result = ToolResult(result_id="tres_1", invocation={"tool_id": "tool_predict_admet_panel"}, outcome="ok",
                        values=[value], records=[],
                        provenance={"tool_id": "tool_predict_admet_panel", "invocation_id": "inv_1",
                                    "license_id": "ADMET-AI: MIT", "data_version": "admet-ai 2.0.1",
                                    "upstream_ref": ["admet-ai:hERG"]})
    claim, = evidence.claims_from_tool_result(core, "run_x", result, candidate={"candidate_id": "cand_1"},
                                              attribute_ref="attr_pred@v1", evidence_kind="model_prediction",
                                              link_basis="exact_identifier_match")
    assert claim["evidence_kind"] == "model_prediction" and claim["determination_basis"] == "predicted"
    assert claim["admission_state"] == "admitted"
    statuses = {payload["source_id"]: payload["source_status"] for _, payload in core.artifacts.of_kind("source")}
    assert statuses[claim["source_ref"]] == "model_prediction_record"


# --- gap-filling: one attribute, two bases, never pooled ----------------------------------------

GAP_FILLED = {
    "attribute_id": "attr_csf1r-potency", "version": 1,
    "name": "CSF1R potency", "measurement_kind": "quantitative", "unit": "pChEMBL",
    "definition": "Median pChEMBL against CSF1R (CHEMBL1844) over curated point measurements; where no "
                  "curation exists, the affinity model's predicted pChEMBL for the same target",
    "direction": "higher_better", "aggregation": "median",
    "acceptable_value_sources": ["curated_measurement", "model_prediction"],
    "acceptable_determination_bases": ["measured", "predicted"],
    "determination_basis_precedence": ["measured", "predicted"],
    "evidence_requests": [{"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values",
                           "identifier_scheme": "inchikey", "parameters": {"target_chembl_id": "CHEMBL1844"}},
                          {"capability": "predicted_property_lookup", "question_kind": "admet_prediction",
                           "identifier_scheme": "inchikey", "parameters": {"endpoint": "CSF1R_affinity"}}],
    "rationale": "74 of 3,177 candidates carry any curated potency at the five required receptors"}
GAP_FILLED_RULE = {"rule_id": "rule_csf1r-potency", "version": 1, "rule_kind": "preference",
                   "predicate_form": "ordering", "cutoff": None,
                   "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty"}


def _claim(claim_id: str, basis: str, kind: str, value: float) -> dict:
    return {"claim_id": claim_id, "admission_state": "admitted", "evidence_kind": kind,
            "determination_basis": basis, "value": value, "unit": "pChEMBL", "source_ref": f"src_{claim_id}",
            "location": {"location_kind": "record_field", "locator_value": claim_id,
                         "quoted_span": str(value), "span_checked_against_source": True}}


def _cell(claims: list[dict], attribute: dict | None = None):
    from mas.core.assessor import assess_cell
    return assess_cell(candidate={"candidate_id": "cand_1"}, attribute=attribute or GAP_FILLED,
                       rule=GAP_FILLED_RULE, rule_set_ref="rules@v1", claims=claims, resolved=True)


def test_a_precedence_keeps_one_basis_per_candidate_and_never_pools_two():
    """The core invariant of the field, asserted directly: whatever evidence a candidate has, the
    claims that reach an aggregate all carry one basis. A candidate with two curated measurements and
    a prediction is scored on the two measurements; the prediction is set aside with a named reason
    and stays in the ledger, so a reader can see the cell had one and declined it."""
    from mas.core.assessor import SET_ASIDE_REASONS, usable_claims

    measured = [_claim("claim_m1", "measured", "curated_measurement", 7.5),
                _claim("claim_m2", "measured", "curated_measurement", 8.1)]
    predicted = [_claim("claim_p1", "predicted", "model_prediction", 6.2)]
    usable, set_aside = usable_claims(measured + predicted, GAP_FILLED)
    assert {c["determination_basis"] for c in usable} == {"measured"}, "no aggregate spans two bases"
    assert [c["claim_id"] for c in usable] == ["claim_m1", "claim_m2"]
    assert [(c["claim_id"], c["set_aside_reason"], c["outranked_by"]) for c in set_aside] == \
        [("claim_p1", "lower_precedence_basis", "measured")]
    assert "lower_precedence_basis" in SET_ASIDE_REASONS, "the reason a cell publishes is a registered one"

    # the gap: the same attribute, a candidate with nothing curated, and the prediction is used alone
    only_predicted, nothing_aside = usable_claims(predicted, GAP_FILLED)
    assert [c["claim_id"] for c in only_predicted] == ["claim_p1"] and nothing_aside == []
    # and the order the claims arrive in cannot change any of it
    reversed_usable, _ = usable_claims(list(reversed(measured + predicted)), GAP_FILLED)
    assert {c["determination_basis"] for c in reversed_usable} == {"measured"}


def test_the_cell_reports_the_basis_it_actually_used():
    """A gap-filled cell reads `predicted` and a measured cell reads `measured`, with the aggregate
    computed over that basis alone. This is what keeps the double counting out: the quantity is
    scored once, and what it rests on is on the cell rather than inferred from the attribute."""
    measured = [_claim("claim_m1", "measured", "curated_measurement", 7.5),
                _claim("claim_m2", "measured", "curated_measurement", 8.1)]
    predicted = [_claim("claim_p1", "predicted", "model_prediction", 6.2)]

    both, both_reason = _cell(measured + predicted)
    assert both["value"] == pytest.approx(7.8) and both["determination_basis"] == "measured"
    assert both["value_kind"] == "curated" and both["value_source_claim_refs"] == ["claim_m1", "claim_m2"]
    assert both["determination_basis_precedence"] == {
        "order": ["measured", "predicted"], "basis_used": "measured", "gap_filled": False,
        "outranked_claims": [{"claim_id": "claim_p1", "basis": "predicted"}]}
    assert "basis precedence measured > predicted" in both_reason["reason_text"]

    gap, gap_reason = _cell(predicted)
    assert gap["value"] == pytest.approx(6.2) and gap["determination_basis"] == "predicted"
    assert gap["value_kind"] == "predicted" and gap["determination_basis_precedence"]["gap_filled"] is True
    assert "standing in for measured evidence this candidate has none of" in gap_reason["reason_text"]
    assert gap_reason["determination_basis_precedence"] == gap["determination_basis_precedence"]

    # a cell with nothing to score says so rather than claiming a basis
    empty, _ = _cell([])
    assert empty["verdict"] == "unknown_missing" and empty["determination_basis"] == "absent"
    assert empty["determination_basis_precedence"]["basis_used"] is None
    assert empty["determination_basis_precedence"]["gap_filled"] is None


def test_an_attribute_with_no_precedence_still_cannot_accept_predicted_beside_a_measurement():
    """The invariant is relaxed for exactly one declaration and not otherwise. Without a precedence
    the refusal stands word for word -- the claims would be pooled, which is the surrogate §4.11
    refuses -- and a malformed precedence is no declaration at all."""
    criteria.check_attribute(GAP_FILLED)
    assert criteria.basis_precedence(GAP_FILLED) == ["measured", "predicted"]

    undeclared = {k: v for k, v in GAP_FILLED.items() if k != criteria.PRECEDENCE_FIELD}
    with pytest.raises(criteria.InvariantViolation, match="their own attribute"):
        criteria.check_attribute(undeclared)
    assert criteria.basis_precedence(undeclared) is None

    for bad, message in ((["predicted", "measured"], "predicted first"),
                         (["measured"], "exactly once"),
                         (["measured", "predicted", "derived"], "exactly once"),
                         (["measured", "measured", "predicted"], "ranks a basis twice"),
                         (["measured", "guessed"], "must be one of"),
                         ([], "non-empty list")):
        with pytest.raises(criteria.InvariantViolation, match=message):
            criteria.check_attribute(dict(GAP_FILLED, determination_basis_precedence=bad))
    # a precedence needs an explicit accepted set to order: the assessor's implicit default is not one
    implicit = {k: v for k, v in GAP_FILLED.items() if k != "acceptable_determination_bases"}
    with pytest.raises(criteria.InvariantViolation, match="explicit acceptable_determination_bases"):
        criteria.check_attribute(implicit)
    # and a malformed declaration reads as absent to the assessor rather than crashing a cell
    from mas.core.assessor import usable_claims
    broken = dict(GAP_FILLED, determination_basis_precedence=["predicted"])
    usable, _ = usable_claims([_claim("claim_m1", "measured", "curated_measurement", 7.5),
                               _claim("claim_p1", "predicted", "model_prediction", 6.2)], broken)
    assert len(usable) == 2, "an unchecked declaration grants nothing; `check_attribute` is where it is refused"


def test_the_precedence_travels_to_every_surface_that_reports_provenance():
    """A gap-filled value is only honest if a reader can see it was one, so the declaration and the
    basis actually used are carried through the roll-up, the board entry, the criterion card and the
    cell view -- not left on the attribute record for someone to look up."""
    from mas.core import criteria_export, leaderboard
    from mas.core.assessor import roll_up
    from mas.ui import views

    gap, _ = _cell([_claim("claim_p1", "predicted", "model_prediction", 6.2)])
    measured, _ = _cell([_claim("claim_m1", "measured", "curated_measurement", 7.5)])
    summary = roll_up("cand_1", [gap, measured], coverage_floor=0.0, recommended_requires_hd=False)
    assert summary["gap_filled_criteria"] == ["attr_csf1r-potency@v1"]
    assert summary["determination_bases"] == {"measured": 1, "predicted": 1}

    snapshot = leaderboard.build_snapshot(
        task_context={"task_context_id": "task_1", "version": 1}, leaderboard_id="lbd_1", run_id="run_1",
        round_id="round_1", rule_set={"rule_set_ref": "rules@v1", "entries": [
            {"rule_ref": "rule_csf1r-potency@v1", "rule_kind": "preference", "attribute_ref": "attr_csf1r-potency@v1"}]},
        evidence_snapshot_id=None, roll_ups={"cand_1": summary}, cells={"cand_1": [gap, measured]},
        scores={"cand_1": (0.5, 1.0)}, identities={}, parent=None, sweep_completeness=1.0, budget={})
    (entry,) = snapshot["candidate_entries"]
    assert entry["gap_filled_criteria"] == ["attr_csf1r-potency@v1"]
    assert entry["determination_bases"] == {"measured": 1, "predicted": 1}
    assert entry["measured_vs_predicted_counts"]["predicted"] == 1

    facets = criteria_export._matching_facets(GAP_FILLED, GAP_FILLED_RULE, [])
    assert facets["operational_quantity"]["determination_basis_precedence"] == ["measured", "predicted"]
    # ... and it is part of the measurement identity, so a gap-filling criterion and a measured-only
    # one are not reported as the same quantity by a comparison that reads fields alone
    measured_only = {k: v for k, v in GAP_FILLED.items() if k != criteria.PRECEDENCE_FIELD}
    measured_only.update(acceptable_determination_bases=["measured"],
                         acceptable_value_sources=["curated_measurement"])
    assert criteria_export._matching_facets(measured_only, GAP_FILLED_RULE, [])["measurement_identity_sha256"] \
        != facets["measurement_identity_sha256"]
    # the cell view a surface renders says which basis the value rests on (`ui.views._cell`)
    assert "determination_basis_precedence" in inspect.getsource(views._cells)


def test_a_pooled_cell_cannot_be_labelled_by_whichever_route_answered_first():
    """Without a precedence an attribute may still accept two bases -- `measured` and `derived` are
    the assessor's own default pair -- and the cell used to report `usable[0]`'s basis, so the same
    evidence read in another order labelled the same value differently. The label is now the weakest
    basis the aggregate rests on, which is what an aggregate of a measurement and a derivation is."""
    from mas.core.assessor import basis_used

    pooled = dict(GAP_FILLED, acceptable_determination_bases=["measured", "derived"],
                  acceptable_value_sources=["curated_measurement", "database_entry"])
    pooled.pop(criteria.PRECEDENCE_FIELD)
    criteria.check_attribute(pooled)
    both = [_claim("claim_d1", "derived", "database_entry", 7.0),
            _claim("claim_m1", "measured", "curated_measurement", 8.0)]
    first, _ = _cell(both, pooled)
    second, _ = _cell(list(reversed(both)), pooled)
    assert first["determination_basis"] == second["determination_basis"] == "derived"
    assert first["value"] == second["value"] == pytest.approx(7.5)
    assert first["determination_basis_precedence"] is None, "nothing was ranked, so nothing is reported as ranked"
    assert basis_used([{"determination_basis": "measured"}]) == "measured"
