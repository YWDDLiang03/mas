"""Live checks of the predicted-property panel. Run with: pytest -m live

Unlike the other live tests these need no network. They need the predictor's own interpreter
(torch, chemprop and rdkit, installed where `mas` cannot see them), which is why they cannot run
in the offline suite: every one of them loads the model ensembles, about fifteen seconds each.
"""

from pathlib import Path

import pytest

from mas.adapters.predict import admet

pytestmark = pytest.mark.live

SURUFATINIB = "TTZSNFLLYPYKIL-UHFFFAOYSA-N"
UNIVERSE = Path("var/primary/universe_chembl.json")
ETHANOL = "CCO"
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
CAFFEINE = "Cn1c(=O)c2c(ncn2C)n(C)c1=O"


@pytest.fixture(autouse=True)
def predictor_present():
    if not admet.available():
        pytest.skip(f"no interpreter with the predictor: tried {admet.candidates()}")


def test_the_recorded_panel_is_the_panel_the_package_reports(tmp_path):
    """The recorded table is what labels every value -- its unit, whether it is a probability,
    which dataset stands behind it -- so it is checked against the installed package rather than
    trusted. `PanelCache._check_panel` makes the same comparison on every batch; this is the test
    that says the recorded table was right in the first place."""
    reported: list[dict] = []
    cache = admet.PanelCache(tmp_path / "cache")
    original = cache._check_panel

    def capture(endpoints):
        reported.extend(endpoints)
        original(endpoints)

    cache._check_panel = capture
    cache._run([ETHANOL])
    assert [entry["id"] for entry in reported] == list(admet.ENDPOINTS)
    for entry in reported:
        spec = admet.ENDPOINTS[entry["id"]]
        assert [entry[field] for field in admet.PANEL_FIELDS_CHECKED] == \
               [spec[field] for field in admet.PANEL_FIELDS_CHECKED]
    assert len(reported) == 52 and len(admet.CLASSIFIERS) == 31 and len(admet.DESCRIPTOR_ENDPOINTS) == 11
    row = cache.row(ETHANOL)
    assert set(row["values"]) == set(admet.ENDPOINTS) and row["predictor"]["version"]
    assert all(0.0 <= row["values"][e] <= 1.0 for e in admet.CLASSIFIERS)


def test_the_panel_answers_a_real_universe_compound_through_the_provider(tmp_path):
    if not UNIVERSE.exists():
        pytest.skip(f"no universe at {UNIVERSE}")
    provider = admet.AdmetPrediction(admet.StructureIndex(UNIVERSE), admet.PanelCache(tmp_path / "cache"))
    bioavailability, = provider.invoke("admet_prediction", {"identifier": SURUFATINIB,
                                                            "endpoint": "Bioavailability_Ma"}).values
    assert 0.0 <= bioavailability["value"] <= 1.0 and bioavailability["unit"] == "probability"
    assert bioavailability["value_kind"] == "predicted"
    where = bioavailability["conditions"]
    assert where["predictor_package"] == "admet-ai" and where["predictor_version"]
    assert where["training_dataset"] == "Bioavailability_Ma" and where["decision_boundary"] == 0.5
    # the whole panel came from one model run, so a second endpoint costs nothing and is consistent
    weight, = provider.invoke("admet_prediction", {"identifier": SURUFATINIB, "endpoint": "molecular_weight"}).values
    assert 300 < weight["value"] < 600 and weight["unit"] == "g/mol"


def test_a_prediction_barely_moves_with_the_batch_it_was_scored_in(tmp_path):
    """The cache is keyed by the structure alone, which is only sound if the batch a structure
    happened to be scored in cannot meaningfully move its values.

    It moves them in the fifth or sixth significant figure and no further: the ensembles sample
    nothing, but float32 partial sums are accumulated in an order that depends on how the batch
    was assembled. The assertion is a tolerance rather than equality because the measured
    behaviour is a tolerance -- the first version of this test asserted equality, failed, and that
    is how the size of it came to be measured (`PanelCache`). 1e-4 is two orders of magnitude
    above the worst deviation measured and still far below any decision taken on one of these
    numbers; a classifier crossing 0.5 by this much would be a different finding."""
    alone = admet.PanelCache(tmp_path / "alone")
    alone.warm([ASPIRIN])
    batched = admet.PanelCache(tmp_path / "batched")
    batched.warm([ETHANOL, CAFFEINE, ASPIRIN, "CCCCCCCC", "c1ccccc1"])
    one, other = alone.row(ASPIRIN)["values"], batched.row(ASPIRIN)["values"]
    assert set(one) == set(other)
    for endpoint, value in one.items():
        assert value == pytest.approx(other[endpoint], rel=1e-4, abs=1e-4), endpoint
    for endpoint in admet.CLASSIFIERS:
        assert (one[endpoint] >= admet.DECISION_BOUNDARY) == (other[endpoint] >= admet.DECISION_BOUNDARY), endpoint


def test_a_structure_the_predictor_cannot_read_is_refused_per_structure(tmp_path):
    cache = admet.PanelCache(tmp_path / "cache")
    report = cache.warm([ETHANOL, "this is not a SMILES"])
    assert (report["computed"], report["refused"]) == (1, 1)
    assert cache.row(ETHANOL)["values"]["molecular_weight"] == pytest.approx(46.069, abs=0.01)
    assert cache.row("this is not a SMILES")["error"]
