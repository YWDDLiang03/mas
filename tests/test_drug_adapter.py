import json

from mas.adapters.drug import chembl
from mas.adapters.drug.chembl import ChEMBLBioactivity, TargetCache
from mas.adapters.drug.registration import EVIDENCE_CATALOG
from mas.adapters.drug.universe import UniverseIdentity
from mas.core.evidence import determination_basis, name_like


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


def test_route_flags_without_an_approval_record_are_unknown_not_false(tmp_path):
    from mas.adapters.drug.universe import UniverseRecordField
    path = tmp_path / "u.json"
    path.write_text(json.dumps({"source": "test", "retrieved_at": "2026-10-13", "universe": [
        {"name": "A", "inchikey": "K-APPROVED", "chembl_id": "C1", "max_phase": 4.0,
         "fields": {"oral": False, "parenteral": True, "first_approval": 2001}},
        {"name": "B", "inchikey": "K-PHASE3", "chembl_id": "C2", "max_phase": 3.0,
         "fields": {"oral": False, "parenteral": False, "first_approval": None}}]}))
    provider = UniverseRecordField(path)
    assert provider.invoke("record_field", {"identifier": "K-APPROVED", "field": "oral"}).values[0]["value"] is False
    assert provider.invoke("record_field", {"identifier": "K-PHASE3", "field": "oral"}).values == []
    assert provider.invoke("record_field", {"identifier": "K-PHASE3", "field": "max_phase"}).values[0]["value"] == 3.0


MECHANISM_ROWS = [
    # imatinib at ABL1: the row names the mesylate salt, the parent only in parent_molecule_chembl_id
    {"mec_id": 304, "molecule_chembl_id": "CHEMBL1642", "parent_molecule_chembl_id": "CHEMBL941",
     "target_chembl_id": "CHEMBL1862", "action_type": "INHIBITOR",
     "mechanism_of_action": "Tyrosine-protein kinase ABL inhibitor", "direct_interaction": 1, "molecular_mechanism": 1,
     "binding_site_comment": None, "selectivity_comment": None, "max_phase": 4,
     "mechanism_refs": [{"ref_type": "PubMed", "ref_id": "11290408", "ref_url": "http://pubmed/11290408"},
                        {"ref_type": "DailyMed", "ref_id": "setid=211ef2da#section-13", "ref_url": "http://dailymed/211ef2da"}]},
    # sunitinib at ABL1: one row against the salt, one against the parent itself
    {"mec_id": 236, "molecule_chembl_id": "CHEMBL1567", "parent_molecule_chembl_id": "CHEMBL535",
     "target_chembl_id": "CHEMBL1862", "action_type": "INHIBITOR",
     "mechanism_of_action": "Macrophage colony stimulating factor receptor inhibitor", "direct_interaction": 1,
     "molecular_mechanism": 1, "binding_site_comment": None, "selectivity_comment": None, "max_phase": 4,
     "mechanism_refs": [{"ref_type": "DailyMed", "ref_id": "setid=43a4d7f8#section-14", "ref_url": "http://dailymed/43a4d7f8"}]},
    {"mec_id": 9798, "molecule_chembl_id": "CHEMBL535", "parent_molecule_chembl_id": "CHEMBL535",
     "target_chembl_id": "CHEMBL1862", "action_type": "INHIBITOR", "mechanism_of_action": "Kinase inhibitor",
     "direct_interaction": 1, "molecular_mechanism": 1, "binding_site_comment": None, "selectivity_comment": None,
     "max_phase": 4, "mechanism_refs": [{"ref_type": "EMA", "ref_id": "epar-product-information", "ref_url": "http://ema/epar"}]},
]


def _fake_listing_get(calls, collection, table):
    """A ChEMBL listing: a filter matches only the field it names, as the live API does."""

    def fake_get(url, params=None, timeout_s=60, expect="json"):
        calls.append(dict(params))
        rows = [r for r in table if r["target_chembl_id"] == params["target_chembl_id"]]
        for field in ("molecule_chembl_id", "parent_molecule_chembl_id"):
            if field in params:
                rows = [r for r in rows if r[field] == params[field]]
        return {collection: rows[params.get("offset", 0):], "page_meta": {"next": None}}

    return fake_get


def _fake_mechanism_get(calls):
    return _fake_listing_get(calls, "mechanisms", MECHANISM_ROWS)


def _fake_activity_get(calls):
    return _fake_listing_get(calls, "activities", ACTIVITY_ROWS)


def test_mechanism_rows_are_found_by_the_parent_or_the_salt_id(monkeypatch):
    calls = []
    monkeypatch.setattr(chembl.http, "get", _fake_mechanism_get(calls))
    provider = chembl.ChEMBLMechanism()                       # no cache: the per-compound path

    def refs(molecule):
        values = provider.invoke("mechanism_records", {
            "identifier": "X", "identifiers": [{"scheme": "chembl_id", "value": molecule}],
            "target_chembl_id": "CHEMBL1862"}).values
        return sorted(v["source_record_ref"] for v in values)

    assert refs("CHEMBL941") == ["chembl_mechanism_304"]      # the parent: only parent_molecule_chembl_id matches
    assert refs("CHEMBL1642") == ["chembl_mechanism_304"]     # the salt: only molecule_chembl_id matches
    assert {f for call in calls for f in call} >= {"molecule_chembl_id", "parent_molecule_chembl_id"}
    assert refs("CHEMBL535") == ["chembl_mechanism_236", "chembl_mechanism_9798"]  # both filters hit 9798: one claim


def test_mechanism_target_cache_fetches_each_target_once(monkeypatch):
    calls = []
    monkeypatch.setattr(chembl.http, "get", _fake_mechanism_get(calls))
    cache = TargetCache()
    provider = chembl.ChEMBLMechanism(cache)
    first = provider.invoke("mechanism_records", {"identifier": "X", "identifiers": [{"scheme": "chembl_id", "value": "CHEMBL941"}],
                                                 "target_chembl_id": "CHEMBL1862"}).values
    second = provider.invoke("mechanism_records", {"identifier": "Y", "identifiers": [{"scheme": "chembl_id", "value": "CHEMBL1567"}],
                                                  "target_chembl_id": "CHEMBL1862"}).values
    assert len(calls) == 1 and "molecule_chembl_id" not in calls[0]   # one bulk page serves the whole universe
    assert [v["source_record_ref"] for v in first] == ["chembl_mechanism_304"]
    assert [v["source_record_ref"] for v in second] == ["chembl_mechanism_236"]  # indexed under the salt too


def test_mechanism_rows_become_one_categorical_claim_each_with_references(monkeypatch):
    monkeypatch.setattr(chembl.http, "get", _fake_mechanism_get([]))
    values = chembl.ChEMBLMechanism(TargetCache()).invoke("mechanism_records", {
        "identifier": "X", "identifiers": [{"scheme": "chembl_id", "value": "CHEMBL535"}],
        "target_chembl_id": "CHEMBL1862"}).values
    assert len(values) == 2                                   # one claim per curated row
    assert all(v["name"] == "target_engagement" and v["value"] is True and v["unit"] is None
               and v["value_kind"] == "curated" for v in values)
    assert [v["conditions"]["action_type"] for v in values] == ["INHIBITOR", "INHIBITOR"]
    assert [r["ref_type"] for v in values for r in v["conditions"]["references"]] == ["DailyMed", "EMA"]
    assert values[0]["conditions"]["references"][0]["ref_id"] == "setid=43a4d7f8#section-14"
    assert values[0]["conditions"]["mechanism_of_action"].endswith("inhibitor")


def test_mechanism_never_produces_a_potency_value(monkeypatch):
    monkeypatch.setattr(chembl.http, "get", _fake_mechanism_get([]))
    contract = chembl.ChEMBLMechanism.contract
    # curation, not measurement: it can never be read as, or stand in for, a pChEMBL potency
    assert contract.claim_strength_ceiling == "curated" and contract.evidence_kind_produced == "database_entry"
    assert contract.question_kinds == ("mechanism_records",)
    values = chembl.ChEMBLMechanism(TargetCache()).invoke("mechanism_records", {
        "identifier": "X", "identifiers": [{"scheme": "chembl_id", "value": "CHEMBL941"}],
        "target_chembl_id": "CHEMBL1862"}).values
    assert values and all(isinstance(v["value"], bool) for v in values)  # a bool is what assess_cell calls non-numeric
    assert all(v["unit"] is None and v.get("value_low") is None and v.get("value_high") is None for v in values)
    assert all("pchembl" not in v["name"] for v in values)


def test_mechanism_is_empty_when_the_compound_has_no_curated_row(monkeypatch):
    monkeypatch.setattr(chembl.http, "get", _fake_mechanism_get([]))
    inputs = {"identifier": "X", "identifiers": [{"scheme": "chembl_id", "value": "CHEMBL404"}],
              "target_chembl_id": "CHEMBL1862"}
    assert chembl.ChEMBLMechanism().invoke("mechanism_records", inputs).values == []
    assert chembl.ChEMBLMechanism(TargetCache()).invoke("mechanism_records", inputs).values == []


# Activity rows shaped like the live endpoint's (ids and counts checked against ChEMBL on
# 2026-10-13): most of imatinib's ABL1 measurements name the parent CHEMBL941, two name the
# mesylate salt CHEMBL1642 and are invisible to a parent-only filter, and CHEMBL206034's only
# ABL1 measurement is recorded against a salt, so that filter returns nothing at all for it.
ACTIVITY_ROWS = [
    {"activity_id": 909963, "molecule_chembl_id": "CHEMBL941", "parent_molecule_chembl_id": "CHEMBL941",
     "target_chembl_id": "CHEMBL1862", "pchembl_value": "7.4", "standard_relation": "=", "standard_type": "IC50",
     "standard_value": "40.0", "standard_units": "nM", "assay_chembl_id": "CHEMBL662679", "assay_type": "B",
     "document_chembl_id": "CHEMBL1127319", "target_organism": "Homo sapiens"},
    {"activity_id": 1735313, "molecule_chembl_id": "CHEMBL1642", "parent_molecule_chembl_id": "CHEMBL941",
     "target_chembl_id": "CHEMBL1862", "pchembl_value": "6.37", "standard_relation": "=", "standard_type": "IC50",
     "standard_value": "430.0", "standard_units": "nM", "target_organism": "Homo sapiens"},
    {"activity_id": 24788695, "molecule_chembl_id": "CHEMBL1642", "parent_molecule_chembl_id": "CHEMBL941",
     "target_chembl_id": "CHEMBL1862", "pchembl_value": "6.72", "standard_relation": ">", "standard_type": "IC50",
     "standard_value": "190.0", "standard_units": "nM", "target_organism": "Homo sapiens"},
    {"activity_id": 311, "molecule_chembl_id": "CHEMBL206035", "parent_molecule_chembl_id": "CHEMBL206034",
     "target_chembl_id": "CHEMBL1862", "pchembl_value": "8.1", "standard_relation": "=", "standard_type": "Ki",
     "standard_value": "7.9", "standard_units": "nM", "target_organism": "Homo sapiens"},
]
IMATINIB_ABL1 = ["chembl_activity_1735313", "chembl_activity_909963"]   # the censored ">" row is not a measurement


def _activity_refs(provider, molecule, target="CHEMBL1862"):
    values = provider.invoke("pchembl_values", {"identifier": "X", "target_chembl_id": target,
                                                "identifiers": [{"scheme": "chembl_id", "value": molecule}]}).values
    return sorted(v["source_record_ref"] for v in values)


def test_activity_rows_are_found_by_the_parent_or_the_salt_id(monkeypatch):
    calls = []
    monkeypatch.setattr(chembl.http, "get", _fake_activity_get(calls))
    provider = ChEMBLBioactivity()                            # no cache: the per-compound path
    assert _activity_refs(provider, "CHEMBL941") == IMATINIB_ABL1    # the parent, including its salt's rows
    assert _activity_refs(provider, "CHEMBL1642") == ["chembl_activity_1735313"]  # the salt: only molecule_chembl_id
    assert _activity_refs(provider, "CHEMBL206034") == ["chembl_activity_311"]    # a parent with no row of its own
    assert {f for call in calls for f in call} >= {"molecule_chembl_id", "parent_molecule_chembl_id"}


def test_an_activity_row_both_filters_return_stays_one_measurement(monkeypatch):
    monkeypatch.setattr(chembl.http, "get", _fake_activity_get([]))
    values = ChEMBLBioactivity().invoke("pchembl_values", {
        "identifier": "X", "identifiers": [{"scheme": "chembl_id", "value": "CHEMBL941"}],
        "target_chembl_id": "CHEMBL1862"}).values
    # 909963 names CHEMBL941 as both its molecule and its parent, so both queries return it
    assert [r["activity_id"] for r in ACTIVITY_ROWS if r["molecule_chembl_id"] == "CHEMBL941"] == [909963]
    assert 909963 in [r["activity_id"] for r in ACTIVITY_ROWS if r["parent_molecule_chembl_id"] == "CHEMBL941"]
    refs = [v["source_record_ref"] for v in values]
    assert refs.count("chembl_activity_909963") == 1 and len(refs) == len(set(refs))
    assert sorted(v["value"] for v in values) == [6.37, 7.4]   # one measurement each: no aggregation is doubled
    assert all(v["unit"] == "pChEMBL" and v["value_kind"] == "curated" for v in values)


def test_one_request_serves_every_descriptor_asked_of_a_compound(monkeypatch):
    """PUG REST returns a whole comma-separated field list in one response, while a criterion asks
    for one descriptor at a time. Without a per-compound row the screen pays a round trip per
    (compound, descriptor) -- the slowest step of a universe sweep, and three times the requests."""
    from mas.adapters.drug.pubchem import PROPERTIES, PropertyCache, PubChemProperty
    urls = []

    def fake_get(url, params=None, timeout_s=60, expect="json"):
        urls.append(url)
        return {"PropertyTable": {"Properties": [{"CID": 5291, "MolecularWeight": "493.6", "XLogP": "3.5",
                                                  "HBondDonorCount": 2, "TPSA": "86.3", "HBondAcceptorCount": 7,
                                                  "RotatableBondCount": 7, "HeavyAtomCount": 37,
                                                  "Complexity": "706"}]}}

    monkeypatch.setattr(chembl.http, "get", fake_get)
    monkeypatch.setattr("mas.adapters.drug.pubchem.http.get", fake_get)
    provider = PubChemProperty(PropertyCache())
    asked = ("MolecularWeight", "XLogP", "HBondDonorCount")
    values = [provider.invoke("computed_property", {"identifier": "KEY", "property": p}).values[0] for p in asked]
    assert [v["name"] for v in values] == list(asked)
    assert [v["value"] for v in values] == [493.6, 3.5, 2]      # cast per property, not all floats
    assert all(v["value_kind"] == "derived" for v in values)    # computed descriptors are never measurements
    assert len(urls) == 1, f"one row per compound, got {len(urls)} requests"
    assert all(name in urls[0] for name in PROPERTIES), "the one request asks for the whole field list"

    uncached = PubChemProperty()
    urls.clear()
    for p in asked:
        uncached.invoke("computed_property", {"identifier": "KEY", "property": p})
    assert len(urls) == 3        # without a cache each descriptor is still its own request


def test_a_compound_with_more_rows_than_one_page_is_paged_on_the_no_cache_path(monkeypatch):
    """The per-compound path asked for one page of 1000 and never looked at `page_meta.next`.
    A well-studied compound exceeds that, and the rows beyond the first page would vanish
    silently -- biasing the median the potency criteria aggregate, not merely losing records."""
    pages = []

    def paging_get(url, params=None, timeout_s=60, expect="json"):
        pages.append(params.get("offset", 0))
        rows = [r for r in ACTIVITY_ROWS if r["target_chembl_id"] == params["target_chembl_id"]]
        for field in ("molecule_chembl_id", "parent_molecule_chembl_id"):
            if field in params:
                rows = [r for r in rows if r[field] == params[field]]
        offset = params.get("offset", 0)
        page = rows[offset // 1000:offset // 1000 + 1]          # one row per page, so every row needs its own request
        has_next = offset // 1000 + 1 < len(rows)
        return {"activities": page, "page_meta": {"next": "/next" if has_next else None}}

    monkeypatch.setattr(chembl.http, "get", paging_get)
    assert _activity_refs(ChEMBLBioactivity(), "CHEMBL941") == IMATINIB_ABL1
    assert max(pages) >= 1000, "the second page was never requested"


def test_target_cache_indexes_activities_under_both_the_salt_and_the_parent_id(monkeypatch):
    calls = []
    monkeypatch.setattr(chembl.http, "get", _fake_activity_get(calls))
    provider = ChEMBLBioactivity(TargetCache())
    assert _activity_refs(provider, "CHEMBL941") == IMATINIB_ABL1
    assert _activity_refs(provider, "CHEMBL1642") == ["chembl_activity_1735313"]
    assert _activity_refs(provider, "CHEMBL206034") == ["chembl_activity_311"]
    assert len(calls) == 1 and "molecule_chembl_id" not in calls[0]   # one bulk page serves the whole universe
    assert _activity_refs(provider, "CHEMBL404") == []                # a compound with no record at the target


def test_mechanism_claims_declare_a_curated_basis_while_potency_claims_keep_measured(monkeypatch):
    monkeypatch.setattr(chembl.http, "get", _fake_mechanism_get([]))
    mechanism = chembl.ChEMBLMechanism().invoke("mechanism_records", {
        "identifier": "X", "identifiers": [{"scheme": "chembl_id", "value": "CHEMBL941"}],
        "target_chembl_id": "CHEMBL1862"}).values
    # an expert assertion with references is recorded as `curated`, never as a measurement
    assert mechanism and all(v["determination_basis"] == "curated" and determination_basis(v) == "curated"
                             for v in mechanism)
    monkeypatch.setattr(chembl.http, "get", _fake_activity_get([]))
    potency = ChEMBLBioactivity().invoke("pchembl_values", {
        "identifier": "X", "identifiers": [{"scheme": "chembl_id", "value": "CHEMBL941"}],
        "target_chembl_id": "CHEMBL1862"}).values
    # a pChEMBL record declares nothing and keeps the DB_BASIS mapping: a curated measurement
    assert potency and all("determination_basis" not in v and determination_basis(v) == "measured" for v in potency)
    entry = next(e for e in EVIDENCE_CATALOG if e["question_kind"] == "mechanism_records")
    assert entry["determination_basis"] == "curated"
    assert 'acceptable_determination_bases: ["curated"]' in entry["note"]
