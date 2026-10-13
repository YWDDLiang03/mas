"""Live checks against PubChem and ChEMBL. Run with: pytest -m live"""

import pytest

from mas.adapters.drug.chembl import ChEMBLBioactivity, ChEMBLMechanism
from mas.adapters.drug.pubchem import PubChemIdentity, PubChemProperty

pytestmark = pytest.mark.live
IMATINIB = "KTUFNOKKBVMGRW-UHFFFAOYSA-N"
SUNITINIB = "WINHZLLDWRZWRT-ATVHPVEESA-N"


def test_pubchem_identity_and_property():
    hits = PubChemIdentity().invoke("resolve_name", {"name": "imatinib"}).values
    assert len(hits) == 1 and hits[0]["value"]["identifiers"][0]["value"] == IMATINIB
    by_key = PubChemIdentity().invoke("resolve_name", {"name": IMATINIB}).values
    assert by_key[0]["value"]["link_basis"] == "exact_identifier_match"
    assert PubChemIdentity().invoke("resolve_name", {"name": "notacompoundxyz"}).values == []
    mw = PubChemProperty().invoke("computed_property", {"identifier": IMATINIB, "property": "MolecularWeight"}).values
    assert mw[0]["unit"] == "g/mol" and 490 < mw[0]["value"] < 500 and mw[0]["value_kind"] == "derived"


def test_chembl_bioactivity_against_a_target():
    values = ChEMBLBioactivity().invoke("pchembl_values", {"identifier": IMATINIB, "target_chembl_id": "CHEMBL1862"}).values
    assert values and all(v["unit"] == "pChEMBL" and v["value_kind"] == "curated" for v in values)


def _potency(molecule, target):
    return ChEMBLBioactivity().invoke("pchembl_values", {
        "identifier": "", "identifiers": [{"scheme": "chembl_id", "value": molecule}],
        "target_chembl_id": target}).values


def test_chembl_bioactivity_finds_activities_recorded_against_a_salt_of_the_parent():
    # imatinib's id is the parent CHEMBL941, but some of its ABL1 measurements are recorded
    # against the mesylate CHEMBL1642: 106 rows under molecule_chembl_id=CHEMBL941 against 108
    # under parent_molecule_chembl_id=CHEMBL941 (measured 2026-10-13), and a salt id is the
    # mirror case, reachable only through molecule_chembl_id
    parent, salt = _potency("CHEMBL941", "CHEMBL1862"), _potency("CHEMBL1642", "CHEMBL1862")
    refs = {v["source_record_ref"] for v in parent}
    assert len(refs) == len(parent)                      # de-duplicated by activity id
    assert salt and {v["source_record_ref"] for v in salt} <= refs    # the salt's rows are in the parent's union
    assert any(v["conditions"]["molecule_chembl_id"] != "CHEMBL941" for v in parent)
    assert all(v["conditions"]["parent_molecule_chembl_id"] == "CHEMBL941" for v in parent)


def test_chembl_mechanism_records_curated_engagement_at_a_required_target():
    # sunitinib (parent CHEMBL535) engages CSF1R (CHEMBL1844) by curated mechanism; it is resolved
    # from the InChIKey alone, as a universe candidate is, and its rows are recorded against a salt
    values = ChEMBLMechanism().invoke("mechanism_records", {"identifier": SUNITINIB, "identifiers": [],
                                                           "target_chembl_id": "CHEMBL1844"}).values
    assert values and all(v["name"] == "target_engagement" and v["value"] is True and v["unit"] is None
                          and v["value_kind"] == "curated" for v in values)
    # a curated assertion, declared as such: it can never be read as a measurement
    assert all(v["determination_basis"] == "curated" for v in values)
    assert any(v["conditions"]["action_type"] == "INHIBITOR" and v["conditions"]["references"] for v in values)
    assert all(v["conditions"]["target_chembl_id"] == "CHEMBL1844" for v in values)
    # the same compound has no curated mechanism row at an unrelated target
    assert ChEMBLMechanism().invoke("mechanism_records", {"identifier": SUNITINIB, "identifiers": [],
                                                         "target_chembl_id": "CHEMBL1862"}).values == []
