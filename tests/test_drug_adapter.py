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


# --- the mandated receptor criterion's three routes ---------------------------------------------

TASK_WITH_ONE_REQUIRED_RECEPTOR = {
    "task_context_id": "task_t", "version": 1,
    "scope_entities": [{"entity_kind": "target", "identifier": "CHEMBL1844", "label": "CSF1R", "role": "required",
                        "identifier_scheme": "chembl_target"}],
    "constraints": [{"text": "oral administration", "kind": "route", "hardness": "hard"}]}


def _mandated_potency():
    from mas.adapters.drug.registration import objective_templates
    item = next(i for i in objective_templates(TASK_WITH_ONE_REQUIRED_RECEPTOR)
                if i["attribute"]["name"] == "CSF1R curated potency")
    return item


def test_the_mandated_receptor_potency_reads_two_curations_and_the_literature_as_one_quantity():
    """A required receptor's potency is one quantity (the comment above the template), and the
    literature is a third curation of it: a published selectivity table reports exactly this for
    exactly these targets, and it is where the quantity exists for the compounds no curation has
    reached -- 74 of the 3,177 candidates carry any curated potency at the five required receptors.

    One attribute with three routes, pooled by the `median` it already declared, so the quantity is
    not registered twice; and every route's evidence kind is accepted, so none of the three pays for
    a call whose values are then all set aside.
    """
    from mas.core import criteria

    item = _mandated_potency()
    attribute, rule = item["attribute"], item["rule"]
    criteria.check_attribute(attribute)
    criteria.check_rule(rule, attribute)
    routes = criteria.evidence_routes(attribute)
    assert [(r["capability"], r["question_kind"]) for r in routes] == [
        ("interaction_evidence_lookup", "pchembl_values"),
        ("interaction_evidence_lookup", "gtopdb_affinity"),
        ("literature_retrieval", "search")]
    assert attribute["acceptable_value_sources"] == ["curated_measurement", "peer_reviewed"]
    for route in routes:
        entry = next(e for e in EVIDENCE_CATALOG if e["capability"] == route["capability"]
                     and e["question_kind"] == route["question_kind"])
        assert entry["evidence_kind"] in attribute["acceptable_value_sources"], route["question_kind"]
        assert entry["determination_basis"] in ("measured", "derived"), "the default accepted bases"
    # the task's decision, kept as code: no predicted route and no gap-filling on this attribute
    assert "determination_basis_precedence" not in attribute
    assert all(r["capability"] != "predicted_property_lookup" for r in routes)


def test_the_literature_route_asks_for_this_receptors_potency_and_is_read_by_capability():
    """The query is about the receptor's potency for this compound, not about the compound: a
    pharmacokinetics paper naming it does not answer here. And the template is found by capability --
    on a three-route attribute the first route is a database one with no template at all, which
    produced a bare-name query."""
    from mas.core import criteria, evidence

    attribute = dict(_mandated_potency()["attribute"], attribute_id="attr_csf1r", version=1)
    route = criteria.literature_route(attribute)
    assert route["parameters"]["search_limit"] == 10 and "CSF1R" in route["parameters"]["relevance_terms"]
    query = evidence.literature_query(attribute, ["Surufatinib", "HMPL-012"])
    assert query == ('(Surufatinib OR "HMPL-012") AND "CSF1R" AND '
                     '(IC50 OR Ki OR Kd OR EC50 OR potency OR selectivity OR "kinase selectivity")')
    assert "{names}" not in query


def test_the_literature_route_only_pays_off_with_the_molar_conversion():
    """The pairing this route depends on: the attribute is on the pChEMBL scale and a selectivity
    table prints a molar IC50. Without `assessor.UNIT_CONVERSIONS` every claim the route produces is
    set aside `unit_unresolved` and the reading is paid for and discarded."""
    from mas.core import assessor

    attribute = _mandated_potency()["attribute"]
    assert attribute["unit"] == "pChEMBL"
    claim = {"claim_id": "c1", "admission_state": "admitted", "evidence_kind": "peer_reviewed",
             "determination_basis": "measured", "value": 0.004, "unit": "uM"}
    usable, set_aside = assessor.usable_claims([claim], attribute)
    assert set_aside == [] and round(usable[0]["value"], 3) == 8.398


# --- an accepted evidence kind has to be one something produces ---------------------------------

def _oral_literature_companion():
    from mas.adapters.drug.registration import objective_templates
    return next(i for i in objective_templates(TASK_WITH_ONE_REQUIRED_RECEPTOR)
                if i["attribute"]["name"].startswith("Oral administration reported"))


def test_the_oral_route_companion_accepts_the_kind_the_readers_actually_emit():
    """It declared `peer_reviewed_primary`, which no tool produces: the readers stamp the source
    registry's kind on every claim and that registry has no `primary` variant. So every claim this
    criterion ever read was set aside `evidence_kind_not_accepted` and it could never carry a value
    -- the one route meant to answer the oral-route question for the 1,262 of 3,177 candidates
    ChEMBL has no route flag for, because its route flags come from approved-product records."""
    from mas.adapters.literature import registry
    from mas.core import assessor, criteria

    attribute = _oral_literature_companion()["attribute"]
    assert attribute["acceptable_value_sources"] == ["peer_reviewed"]
    assert registry.SOURCES["europepmc"].evidence_kind == "peer_reviewed"
    criteria.check_attribute(attribute)
    read = {"claim_id": "c1", "admission_state": "admitted", "evidence_kind": "peer_reviewed",
            "determination_basis": "asserted", "value": True, "unit": None}
    usable, set_aside = assessor.usable_claims([read], dict(attribute, attribute_id="attr_oral", version=1))
    assert [c["claim_id"] for c in usable] == ["c1"] and set_aside == []
    # the declaration as it was: admitted by the registry, and refused by the assessor on every claim
    was = dict(attribute, acceptable_value_sources=["peer_reviewed_primary"])
    _, refused = assessor.usable_claims([read], dict(was, attribute_id="attr_oral", version=1))
    assert [c["set_aside_reason"] for c in refused] == ["evidence_kind_not_accepted"]


def test_an_attribute_declaring_a_kind_nothing_produces_is_refused_at_registration():
    """The class of bug, closed where the attribute is written. `check_attribute` only checked that
    `acceptable_value_sources` was *present*, so a kind nothing emits read exactly like absent
    evidence: the cell came back `unknown_missing` and nothing said the criterion was unanswerable
    by construction."""
    import pytest

    from mas.core import criteria

    attribute = _oral_literature_companion()["attribute"]
    for refused in ("peer_reviewed_primary", "PEER_REVIEWED", "clinical_trial_registry", ""):
        with pytest.raises(criteria.InvariantViolation, match="no tool of this system produces"):
            criteria.check_attribute(dict(attribute, acceptable_value_sources=[refused]))
    with pytest.raises(criteria.InvariantViolation, match="needs acceptable_value_sources"):
        criteria.check_attribute({k: v for k, v in attribute.items() if k != "acceptable_value_sources"})
    with pytest.raises(criteria.InvariantViolation, match="non-empty list"):
        criteria.check_attribute(dict(attribute, acceptable_value_sources="peer_reviewed"))


def test_a_kind_whose_tool_this_install_has_not_got_is_not_a_schema_defect(tmp_path):
    """The false positive to avoid. `model_prediction` is a legitimate kind, and a machine without
    the ADMET predictor registers no tool that produces one. That is an install gap, reported from
    the live contracts (`evidence.producible_evidence_kinds`), not a defect in the attribute -- so
    the registry's refusal is measured against the closed `evidence_kind` vocabulary, which says
    what kind of thing exists at all, and never against what happens to be installed."""
    from mas.adapters.drug.registration import register
    from mas.core import criteria, evidence, vocab
    from mas.core.broker import Broker
    from mas.core.runtime import Core

    predicted = {"name": "Predicted clearance", "definition": "d", "measurement_kind": "quantitative",
                 "unit": "mL/min/kg", "direction": "lower_better", "aggregation": "median",
                 "acceptable_value_sources": ["model_prediction"],
                 "acceptable_determination_bases": ["predicted"],
                 "evidence_request": {"capability": "predicted_property_lookup",
                                      "question_kind": "admet_prediction", "identifier_scheme": "inchikey",
                                      "parameters": {"endpoint": "Clearance_Hepatocyte_AZ"}}}
    universe = tmp_path / "u.json"
    universe.write_text(json.dumps({"source": "test", "universe": [{"inchikey": "AAA", "name": "x", "smiles": "C"}]}))
    with Core.open(tmp_path / "root") as core:
        installs = {}
        for predict in (True, False):
            broker = Broker(core, sleep=lambda s: None)
            register(broker, universe_file=str(universe), predict=predict, cache_dir=str(tmp_path),
                     upload_dir=str(tmp_path))
            installs[predict] = evidence.producible_evidence_kinds(broker)
    assert "model_prediction" in installs[True] and "model_prediction" not in installs[False]
    criteria.check_attribute(predicted), "the attribute is sound either way"
    # and every kind a full install produces is a registered one, so the refusal above can never
    # reject a kind some tool here emits -- including `preprint`, which `reading.read` stamps on a
    # preprint hit and which therefore no tool contract declares
    assert installs[True] == set(criteria.EVIDENCE_KINDS) == set(vocab.DOMAINS["evidence_kind"])
    assert "preprint" not in {c.evidence_kind_produced for c in Broker(None, sleep=lambda s: None).contracts()}


def test_every_kind_the_adapters_declare_is_one_the_vocabulary_registers():
    """The drift guard the registry needs and cannot run itself: the core may not import an adapter,
    so the closed list in `vocab.DOMAINS["evidence_kind"]` is checked against the adapters here. The
    hand-written tuple it replaces listed five kinds and omitted the three this adapter's own
    literature registration produces, which is why it could not be used to check anything."""
    from mas.adapters.drug.registration import EVIDENCE_KINDS
    from mas.adapters.literature import registry
    from mas.core import criteria, vocab

    assert set(EVIDENCE_KINDS) == set(criteria.EVIDENCE_KINDS)
    assert {"reference_text", "tertiary_reference", "user_supplied_document"} <= set(EVIDENCE_KINDS)
    assert {s.evidence_kind for s in registry.SOURCES.values()} <= set(vocab.DOMAINS["evidence_kind"])
    assert {e["evidence_kind"] for e in EVIDENCE_CATALOG} <= set(vocab.DOMAINS["evidence_kind"])
    # every catalog entry's kind is accepted by at least one of its routes' attributes somewhere, and
    # the reverse direction -- a kind in the vocabulary that nothing produces -- is what is refused
    for kind in criteria.EVIDENCE_KINDS:
        assert vocab.label("evidence_kind", kind)
