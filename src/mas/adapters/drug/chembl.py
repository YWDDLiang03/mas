"""ChEMBL web services: curated bioactivity and curated mechanism of a compound against a target (`tools.md` §2.4)."""

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


# Mechanism row fields kept: the engagement statement, its qualifiers, and its references.
MECHANISM_ONLY = ("mec_id,molecule_chembl_id,parent_molecule_chembl_id,target_chembl_id,action_type,mechanism_of_action,"
                  "direct_interaction,molecular_mechanism,binding_site_comment,selectivity_comment,mechanism_refs,max_phase")

# Activity row fields kept: the potency value, the assay it came from, and both molecule ids.
ACTIVITY_ONLY = ("activity_id,molecule_chembl_id,parent_molecule_chembl_id,pchembl_value,standard_type,"
                 "standard_relation,standard_value,standard_units,assay_chembl_id,assay_type,document_chembl_id,"
                 "target_organism")

# The salt/parent trap, in both ChEMBL tables that record a compound against a target: a
# curator records a row against whichever molecule the source named, often a salt (imatinib
# mesylate CHEMBL1642, sunitinib malate CHEMBL1567) with the parent (imatinib CHEMBL941,
# sunitinib CHEMBL535) only in `parent_molecule_chembl_id`. The id a universe holds may be
# either, and a ChEMBL filter matches only the field it names: measured 2026-10-13, imatinib
# at ABL1 (CHEMBL1862) has 106 pChEMBL rows under `molecule_chembl_id=CHEMBL941` and 108
# under `parent_molecule_chembl_id=CHEMBL941`, while the salt CHEMBL1642 has those 2 rows
# under `molecule_chembl_id` and none under the parent field; CHEMBL206034 at the same target
# has 0 and 1. So every per-compound query asks on both fields and keeps the union.
MOLECULE_FIELDS = ("parent_molecule_chembl_id", "molecule_chembl_id")


def _index_by_molecule(resource: str, collection: str, row_id: str,
                       params: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Page through a target-filtered listing, indexing every row under both its molecule and its parent id.

    A universe may hold either id (see `MOLECULE_FIELDS`), so both are keys to the same row.
    Rows are kept per molecule in a `row_id`-keyed map, so one record cannot enter a
    compound's list twice.
    """
    index: dict[str, dict[Any, dict[str, Any]]] = {}
    offset = 0
    while True:
        body = http.get(f"{BASE}/{resource}", timeout_s=180,
                        params=dict(params, format="json", limit=1000, offset=offset))
        if body is None:
            raise ToolError("upstream_server_error",
                            f"{resource} listing for {params.get('target_chembl_id')} returned 404")
        for row in body.get(collection) or []:
            for key in {row.get("molecule_chembl_id"), row.get("parent_molecule_chembl_id")} - {None}:
                index.setdefault(key, {})[row[row_id]] = row
        if not (body.get("page_meta") or {}).get("next"):
            break
        offset += 1000
    return {molecule: list(rows.values()) for molecule, rows in index.items()}


def _rows_for_molecule(resource: str, collection: str, row_id: str, molecule: str,
                       params: dict[str, Any]) -> list[dict[str, Any]]:
    """One compound's rows of a listing, asked for by its molecule id and by its parent id.

    The no-cache path of `_index_by_molecule`: either field may be the one that names the
    id we hold (see `MOLECULE_FIELDS`), so both are queried and the union is de-duplicated
    by `row_id` — a row that both filters return is one record, not two.
    """
    found: dict[Any, dict[str, Any]] = {}
    for field in MOLECULE_FIELDS:
        body = http.get(f"{BASE}/{resource}",
                        params=dict(params, format="json", limit=1000, **{field: molecule}))
        if body is None:
            raise ToolError("upstream_server_error", f"{resource} endpoint returned 404")
        for row in body.get(collection) or []:
            found[row[row_id]] = row
    return list(found.values())


class TargetCache:
    """All curated records of one target, fetched once and indexed by molecule.

    Two independent ChEMBL tables, each cached per target: pChEMBL activity measurements
    and mechanism-of-action records.
    """

    def __init__(self):
        self.by_target: dict[str, dict[str, list[dict[str, Any]]]] = {}
        self.mechanisms_by_target: dict[str, dict[str, list[dict[str, Any]]]] = {}

    def activities(self, target_chembl_id: str) -> dict[str, list[dict[str, Any]]]:
        if target_chembl_id not in self.by_target:
            self.by_target[target_chembl_id] = _index_by_molecule("activity", "activities", "activity_id", {
                "target_chembl_id": target_chembl_id, "pchembl_value__isnull": "false", "only": ACTIVITY_ONLY})
        return self.by_target[target_chembl_id]

    def mechanisms(self, target_chembl_id: str) -> dict[str, list[dict[str, Any]]]:
        if target_chembl_id not in self.mechanisms_by_target:
            self.mechanisms_by_target[target_chembl_id] = _index_by_molecule(
                "mechanism", "mechanisms", "mec_id", {"target_chembl_id": target_chembl_id, "only": MECHANISM_ONLY})
        return self.mechanisms_by_target[target_chembl_id]


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
            # Both molecule fields, de-duplicated by activity_id: a compound whose id is the
            # parent while its measurements are recorded against a salt (or the reverse) would
            # otherwise return no potency at all, which reads exactly like "no data".
            activities = _rows_for_molecule("activity", "activities", "activity_id", molecule,
                                            {"target_chembl_id": inputs["target_chembl_id"],
                                             "pchembl_value__isnull": "false", "only": ACTIVITY_ONLY})
        values = []
        for activity in activities:
            if activity.get("standard_relation") not in (None, "=", "'='"):
                continue  # censored values (">", "<") are not point measurements
            values.append({"name": "pchembl_value", "value": float(activity["pchembl_value"]), "unit": "pChEMBL",
                           "value_kind": "curated", "source_record_ref": f"chembl_activity_{activity['activity_id']}",
                           "conditions": {k: activity.get(k) for k in ("standard_type", "standard_value", "standard_units",
                                                                        "assay_chembl_id", "assay_type", "document_chembl_id",
                                                                        "target_organism", "molecule_chembl_id",
                                                                        "parent_molecule_chembl_id")}})
        return ProviderResponse(values=values, records=[{"molecule_chembl_id": molecule, "n_activities": len(values)}],
                                data_version="chembl", upstream_refs=[f"chembl:{molecule}:{inputs['target_chembl_id']}"])


class ChEMBLMechanism:
    """Curated mechanism-of-action records: that a compound engages a target, and the references for it.

    An independent curation from the activity table: small (a few dozen rows per target,
    almost all approved or late-stage drugs) but covering compound-target pairs with no
    pChEMBL record at all. A row carries no magnitude, so a value here is the categorical
    statement "engagement is on record" (True, no unit, `curated`), never a potency; the
    action type, the qualifiers and the references travel in `conditions` for a narrative
    to cite.
    """

    contract = ToolContract(
        tool_id="tool_drug_chembl_mechanism", capability="interaction_evidence_lookup",
        capability_kind="relationship_evidence_lookup", question_kinds=("mechanism_records",), contract_version="1",
        implementation_version="chembl-ws-mechanism-1",
        purpose_statement="Curated mechanism-of-action records of a compound engaging a named target, with references",
        evidence_kind_produced="database_entry", claim_strength_ceiling="curated",
        identity_inputs=("identifier",), required_inputs=("target_chembl_id",), license_id="CC BY-SA 3.0 (ChEMBL)")

    def __init__(self, cache: TargetCache | None = None):
        self.cache = cache  # with a cache, a target's mechanism rows are fetched once for the whole universe

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        molecule = next((i["value"] for i in inputs.get("identifiers", []) if i.get("scheme") == "chembl_id"), None) \
            or chembl_id_for_inchikey(inputs["identifier"])
        if molecule is None:
            return ProviderResponse(values=[], data_version="chembl")
        target = inputs["target_chembl_id"]
        if self.cache is not None:
            rows = self.cache.mechanisms(target).get(molecule, [])
        else:
            # Both molecule fields (see `MOLECULE_FIELDS`): in a 1,000-row sample 507 mechanism
            # rows named a salt as their molecule and the parent only in parent_molecule_chembl_id.
            rows = _rows_for_molecule("mechanism", "mechanisms", "mec_id", molecule,
                                      {"target_chembl_id": target, "only": MECHANISM_ONLY})
        values = []
        for row in rows:
            values.append({
                # A curated assertion with references, not a measurement: the basis is declared
                # here rather than mapped from `value_kind`, which would stamp it `measured` and
                # let a categorical record satisfy an attribute that asked for measurements.
                "name": "target_engagement", "value": True, "unit": None, "value_kind": "curated",
                "determination_basis": "curated",
                "source_record_ref": f"chembl_mechanism_{row['mec_id']}",
                "conditions": {
                    "target_chembl_id": target, "action_type": row.get("action_type"),
                    "mechanism_of_action": row.get("mechanism_of_action"),
                    "molecule_chembl_id": row.get("molecule_chembl_id"),
                    "parent_molecule_chembl_id": row.get("parent_molecule_chembl_id"),
                    "direct_interaction": row.get("direct_interaction"),
                    "molecular_mechanism": row.get("molecular_mechanism"),
                    "binding_site_comment": row.get("binding_site_comment"),
                    "selectivity_comment": row.get("selectivity_comment"), "max_phase": row.get("max_phase"),
                    "references": [{k: ref.get(k) for k in ("ref_type", "ref_id", "ref_url")}
                                   for ref in row.get("mechanism_refs") or []]}})
        return ProviderResponse(values=values, records=[{"molecule_chembl_id": molecule, "n_mechanisms": len(values)}],
                                data_version="chembl", upstream_refs=[f"chembl:mechanism:{molecule}:{target}"])
