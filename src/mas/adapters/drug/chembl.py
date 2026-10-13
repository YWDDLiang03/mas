"""ChEMBL web services: curated bioactivity of a compound against a target (`tools.md` §2.4)."""

from __future__ import annotations

from typing import Any

from mas.adapters.literature import http
from mas.core.broker import ProviderResponse, ToolContract, ToolError

BASE = "https://www.ebi.ac.uk/chembl/api/data"
_molecule_cache: dict[str, str | None] = {}


def chembl_id_for_inchikey(inchikey: str) -> str | None:
    if inchikey not in _molecule_cache:
        body = http.get(f"{BASE}/molecule", params={"molecule_structures__standard_inchi_key": inchikey, "format": "json",
                                                   "only": "molecule_chembl_id"})
        molecules = (body or {}).get("molecules") or []
        _molecule_cache[inchikey] = molecules[0]["molecule_chembl_id"] if molecules else None
    return _molecule_cache[inchikey]


class TargetCache:
    """All pChEMBL activity records of one target, fetched once and indexed by molecule."""

    def __init__(self):
        self.by_target: dict[str, dict[str, list[dict[str, Any]]]] = {}

    def activities(self, target_chembl_id: str) -> dict[str, list[dict[str, Any]]]:
        if target_chembl_id not in self.by_target:
            index: dict[str, list[dict[str, Any]]] = {}
            offset = 0
            while True:
                body = http.get(f"{BASE}/activity", timeout_s=180, params={
                    "target_chembl_id": target_chembl_id, "pchembl_value__isnull": "false", "format": "json",
                    "limit": 1000, "offset": offset,
                    "only": "activity_id,molecule_chembl_id,parent_molecule_chembl_id,pchembl_value,standard_type,"
                            "standard_relation,standard_value,standard_units,assay_chembl_id,assay_type,document_chembl_id,"
                            "target_organism"})
                if body is None:
                    raise ToolError("upstream_server_error", f"activity listing for {target_chembl_id} returned 404")
                for activity in body.get("activities") or []:
                    for key in {activity.get("molecule_chembl_id"), activity.get("parent_molecule_chembl_id")} - {None}:
                        index.setdefault(key, []).append(activity)
                if not (body.get("page_meta") or {}).get("next"):
                    break
                offset += 1000
            self.by_target[target_chembl_id] = index
        return self.by_target[target_chembl_id]


class ChEMBLBioactivity:
    contract = ToolContract(
        tool_id="tool_drug_chembl_bioactivity", capability="interaction_evidence_lookup",
        capability_kind="relationship_evidence_lookup", question_kinds=("pchembl_values",), contract_version="1",
        implementation_version="chembl-ws-activity-1",
        purpose_statement="Curated potency records (pChEMBL) of a compound against a named target",
        evidence_kind_produced="curated_measurement", claim_strength_ceiling="measured",
        identity_inputs=("identifier",), required_inputs=("target_chembl_id",), license_id="CC BY-SA 3.0 (ChEMBL)")

    def __init__(self, cache: TargetCache | None = None):
        self.cache = cache  # with a cache, a target's records are fetched once for the whole universe

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        molecule = next((i["value"] for i in inputs.get("identifiers", []) if i.get("scheme") == "chembl_id"), None) \
            or chembl_id_for_inchikey(inputs["identifier"])
        if molecule is None:
            return ProviderResponse(values=[], data_version="chembl")
        if self.cache is not None:
            activities = self.cache.activities(inputs["target_chembl_id"]).get(molecule, [])
        else:
            body = http.get(f"{BASE}/activity", params={
                "molecule_chembl_id": molecule, "target_chembl_id": inputs["target_chembl_id"], "pchembl_value__isnull": "false",
                "format": "json", "limit": 1000,
                "only": "activity_id,pchembl_value,standard_type,standard_relation,standard_value,standard_units,assay_chembl_id,"
                        "assay_type,document_chembl_id,target_organism"})
            if body is None:
                raise ToolError("upstream_server_error", "activity endpoint returned 404")
            activities = body.get("activities") or []
        values = []
        for activity in activities:
            if activity.get("standard_relation") not in (None, "=", "'='"):
                continue  # censored values (">", "<") are not point measurements
            values.append({"name": "pchembl_value", "value": float(activity["pchembl_value"]), "unit": "pChEMBL",
                           "value_kind": "curated", "source_record_ref": f"chembl_activity_{activity['activity_id']}",
                           "conditions": {k: activity.get(k) for k in ("standard_type", "standard_value", "standard_units",
                                                                        "assay_chembl_id", "assay_type", "document_chembl_id",
                                                                        "target_organism")}})
        return ProviderResponse(values=values, records=[{"molecule_chembl_id": molecule, "n_activities": len(values)}],
                                data_version="chembl", upstream_refs=[f"chembl:{molecule}:{inputs['target_chembl_id']}"])
