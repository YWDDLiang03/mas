"""PubChem PUG REST: identity resolution and computed properties (`tools.md` §2.2)."""

from __future__ import annotations

import copy
import threading
from typing import Any
from urllib.parse import quote

from mas.adapters.literature import http
from mas.core.broker import ProviderResponse, ToolContract, ToolError
from mas.core.canonical import sha256_hex

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
IDENTITY_FIELDS = "InChIKey,IUPACName,MolecularFormula"
# PubChem property name → (unit, value kind). Computed descriptors are `derived`, never measured.
PROPERTIES = {
    "MolecularWeight": ("g/mol", float), "XLogP": ("log units", float), "TPSA": ("Å²", float),
    "HBondDonorCount": ("count", int), "HBondAcceptorCount": ("count", int), "RotatableBondCount": ("count", int),
    "HeavyAtomCount": ("count", int), "Complexity": ("score", float),
}


def _properties(path: str, fields: str) -> list[dict[str, Any]]:
    body = http.get(f"{BASE}/compound/{path}/property/{fields}/JSON")
    if body is None or "Fault" in (body or {}):
        return []
    return (body.get("PropertyTable") or {}).get("Properties") or []


class PubChemIdentity:
    contract = ToolContract(
        tool_id="tool_drug_pubchem_identity", capability="identity_resolution", capability_kind="entity_resolution",
        question_kinds=("resolve_name",), contract_version="1", implementation_version="pug-rest-name-1",
        purpose_statement="Resolve a compound name or identifier to PubChem CID and InChIKey with synonyms",
        evidence_kind_produced="database_entry", claim_strength_ceiling="curated", required_inputs=("name",),
        license_id="PubChem data: public domain (NCBI policy)")

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        name = inputs["name"].strip()
        if len(name) == 27 and name[14] == "-" and name[25] == "-":
            records, basis = _properties(f"inchikey/{name}", IDENTITY_FIELDS), "exact_identifier_match"
        else:
            records, basis = _properties(f"name/{quote(name, safe='')}", IDENTITY_FIELDS), "name_match_single_candidate"
        hits = []
        for record in records:
            synonyms_body = http.get(f"{BASE}/compound/cid/{record['CID']}/synonyms/JSON") or {}
            info = ((synonyms_body.get("InformationList") or {}).get("Information") or [{}])[0]
            synonyms = [s for s in info.get("Synonym", []) if len(s) < 40][:12]
            hits.append({
                "preferred_label": synonyms[0] if synonyms else name,
                "identifiers": [{"scheme": "inchikey", "value": record["InChIKey"], "scheme_authority": "IUPAC/PubChem"},
                                {"scheme": "pubchem_cid", "value": str(record["CID"]), "scheme_authority": "PubChem"}],
                "aliases": [{"alias": s, "alias_source": "pubchem_synonyms", "alias_kind": "synonym"} for s in synonyms[1:]],
                "molecular_formula": record.get("MolecularFormula"), "link_basis": basis,
            })
        if len(hits) > 1:
            for hit in hits:
                hit["link_basis"] = "name_match_ambiguous"
        return ProviderResponse(values=[{"name": "identity", "value": h, "value_kind": "curated"} for h in hits],
                                records=[{"cid": h["identifiers"][1]["value"]} for h in hits], data_version="pubchem",
                                upstream_refs=[f"pubchem:cid:{h['identifiers'][1]['value']}" for h in hits])


class PropertyCache:
    """One compound's whole descriptor row, fetched once and served to every property asked of it.

    PUG REST returns any comma-separated field list in one response, while a criterion asks for
    one descriptor at a time. Without this, a sweep over a universe pays a separate round trip per
    (compound, descriptor) -- on the manuscript case three physicochemical criteria over 3,177
    compounds, which is three times the requests and the slowest step of the screen. Keyed by
    InChIKey, so a candidate reached by two rules is fetched once.
    """

    def __init__(self):
        self._rows: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def row(self, inchikey: str) -> list[dict[str, Any]]:
        with self._lock:                      # the sweep may assess cells concurrently
            if inchikey not in self._rows:
                self._rows[inchikey] = _properties(f"inchikey/{inchikey}", ",".join(PROPERTIES))
            return self._rows[inchikey]


class PubChemProperty:
    historical_projection_policy = "pubchem_descriptor_row_projection@v1"
    contract = ToolContract(
        tool_id="tool_drug_pubchem_property", capability="property_estimate", capability_kind="attribute_estimate",
        question_kinds=("computed_property",), contract_version="1", implementation_version="pug-rest-property-1",
        purpose_statement="Computed physicochemical descriptors for a compound (derived values, not measurements)",
        evidence_kind_produced="database_entry", claim_strength_ceiling="curated", identity_inputs=("identifier",),
        required_inputs=("property",), license_id="PubChem data: public domain (NCBI policy)")

    def __init__(self, cache: PropertyCache | None = None):
        self.cache = cache
        self._historical_rows: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _row_key(inputs: dict[str, Any]) -> str:
        return sha256_hex({key: value for key, value in inputs.items() if key != "property"})

    def seed_historical_result(self, result: dict[str, Any], source: dict[str, Any]) -> bool:
        """Remember the first original row for otherwise identical descriptor inputs."""
        invocation, provenance = result["invocation"], result["provenance"]
        inputs = invocation["normalized_input"]
        records = result["records"]
        if (invocation["question_kind"] != "computed_property" or inputs.get("property") not in PROPERTIES
                or not records or not isinstance(records[0], dict) or "CID" not in records[0]):
            return False
        key = self._row_key(inputs)
        if key in self._historical_rows:
            return False
        row = copy.deepcopy(records[:1])
        self._historical_rows[key] = {
            "records": row, "data_version": provenance.get("data_version", "pubchem"),
            "retrieved_at": provenance["retrieved_at"],
            "source": {"strategy": self.historical_projection_policy, **source,
                       "source_invocation_id": invocation["invocation_id"],
                       "source_property": inputs["property"], "record_sha256": sha256_hex(row)},
        }
        return True

    def historical_projection_manifest(self) -> dict[str, Any]:
        return {"policy": self.historical_projection_policy, "rows": len(self._historical_rows),
                "matching": "same tool, contract, implementation and all inputs except property",
                "missing_field": "empty_without_retrieval", "entries_digest": sha256_hex([
                    {"input_key": key, "source": self._historical_rows[key]["source"]}
                    for key in sorted(self._historical_rows)])}

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        prop = inputs["property"]
        if prop not in PROPERTIES:
            raise ToolError("input_invalid", f"unsupported property {prop}", retryable=False)
        history = self._historical_rows.get(self._row_key(inputs))
        if history is not None:
            records = copy.deepcopy(history["records"])
        else:
            records = self.cache.row(inputs["identifier"]) if self.cache is not None \
                else _properties(f"inchikey/{inputs['identifier']}", prop)
        unit, cast = PROPERTIES[prop]
        values = [{"name": prop, "value": cast(r[prop]), "unit": unit, "value_kind": "derived",
                   "source_record_ref": f"pubchem_cid_{r['CID']}"} for r in records if r.get(prop) is not None][:1]
        return ProviderResponse(
            values=values, records=records[:1], data_version=history["data_version"] if history is not None else "pubchem",
            outcome="empty" if history is not None and not values else "ok",
            upstream_refs=[f"pubchem:cid:{r['CID']}" for r in records[:1]],
            source_retrieved_at=history["retrieved_at"] if history is not None else None,
            local_derivation=dict(history["source"], selected_property=prop) if history is not None else None,
            warnings=[f"{prop} is absent from the inherited PubChem row; no new retrieval was attempted"]
            if history is not None and not values else [])
