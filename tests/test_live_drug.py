"""Live checks against PubChem and ChEMBL. Run with: pytest -m live"""

import pytest

from mas.adapters.drug.chembl import ChEMBLBioactivity
from mas.adapters.drug.pubchem import PubChemIdentity, PubChemProperty

pytestmark = pytest.mark.live
IMATINIB = "KTUFNOKKBVMGRW-UHFFFAOYSA-N"


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
