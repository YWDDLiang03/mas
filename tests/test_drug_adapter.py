import json

from mas.adapters.drug import chembl
from mas.adapters.drug.chembl import ChEMBLBioactivity, TargetCache
from mas.adapters.drug.universe import UniverseIdentity
from mas.core.evidence import name_like


def test_universe_identity_resolves_by_key_and_name(tmp_path):
    path = tmp_path / "u.json"
    path.write_text(json.dumps({"source": "test", "retrieved_at": "2026-10-13", "universe": [
        {"name": "ALPHATINIB", "inchikey": "AAAAAAAAAAAAAA-BBBBBBBBBB-N", "chembl_id": "CHEMBL1", "synonyms": ["AT-1"]},
        {"name": "BETATINIB", "inchikey": "CCCCCCCCCCCCCC-DDDDDDDDDD-N", "chembl_id": "CHEMBL2", "synonyms": ["AT-1"]}]}))
    provider = UniverseIdentity(path)
    by_key = provider.invoke("resolve_name", {"name": "AAAAAAAAAAAAAA-BBBBBBBBBB-N"}).values
    assert by_key[0]["value"]["link_basis"] == "exact_identifier_match"
    assert by_key[0]["value"]["preferred_label"] == "Alphatinib"
    shared = provider.invoke("resolve_name", {"name": "at-1"}).values
    assert len(shared) == 2 and {h["value"]["link_basis"] for h in shared} == {"name_match_ambiguous"}
    assert provider.invoke("resolve_name", {"name": "unknown"}).values == []


def test_target_cache_fetches_each_target_once(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout_s=60, expect="json"):
        calls.append(params["offset"])
        if params["offset"] == 0:
            return {"activities": [{"activity_id": 1, "molecule_chembl_id": "CHEMBL1", "parent_molecule_chembl_id": "CHEMBL1",
                                    "pchembl_value": "7.5", "standard_relation": "="}], "page_meta": {"next": "more"}}
        return {"activities": [{"activity_id": 2, "molecule_chembl_id": "CHEMBL9", "parent_molecule_chembl_id": "CHEMBL1",
                                "pchembl_value": "6.0", "standard_relation": ">"}], "page_meta": {"next": None}}

    monkeypatch.setattr(chembl.http, "get", fake_get)
    provider = ChEMBLBioactivity(TargetCache())
    inputs = {"identifier": "X", "identifiers": [{"scheme": "chembl_id", "value": "CHEMBL1"}], "target_chembl_id": "T"}
    first = provider.invoke("pchembl_values", inputs).values
    again = provider.invoke("pchembl_values", inputs).values
    assert calls == [0, 1000]                       # two pages, fetched once
    assert [v["value"] for v in first] == [7.5]      # the censored ">" record is not a point measurement
    assert first == again


def test_name_like_filters_search_labels():
    assert [a for a in ["Gleevec", "152459-95-5", "STI-571", "a very long chemical name with many words"] if name_like(a)] \
        == ["Gleevec", "STI-571"]
