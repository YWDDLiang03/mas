"""IUPHAR/BPS Guide to Pharmacology: curated ligand–target affinities from the open bulk files.

The GtoPdb web services need a registered API key, but its data files are published
openly (CC BY-SA 4.0) and versioned. They are downloaded once into the cache; a
candidate is matched to GtoPdb ligands by InChIKey, and a target given as a ChEMBL
target id is matched by its UniProt accession(s).

Affinities are p-values (pIC50, pKi, pKd, pEC50: −log10 molar), the same scale as
pChEMBL. A row reported as a range contributes its low and high bounds.
"""

from __future__ import annotations

import csv
import io
import json
import threading
import time
from pathlib import Path
from typing import Any

from mas.adapters.literature import http
from mas.adapters.literature.bookshelf import default_cache_dir
from mas.core.broker import ProviderResponse, ToolContract, ToolError

DATA = "https://www.guidetopharmacology.org/DATA"
FILES = ("ligands.csv", "interactions.csv")
MAX_AGE_S = 30 * 24 * 3600
CHEMBL = "https://www.ebi.ac.uk/chembl/api/data"


def _rows(text: str) -> tuple[str, list[dict[str, str]]]:
    first, _, rest = text.partition("\n")
    version = first.strip().strip('"').lstrip("# ").strip()
    return version, list(csv.DictReader(io.StringIO(rest)))


class GtoPdbData:
    """The bulk files, indexed by ligand InChIKey and target UniProt accession."""

    def __init__(self, cache_dir: str | Path | None = None):
        self.root = Path(cache_dir or default_cache_dir()) / "gtopdb"
        self._lock = threading.Lock()
        self._loaded = False
        self.version = ""
        self.ligands_by_inchikey: dict[str, list[str]] = {}
        self.interactions: dict[tuple[str, str], list[dict[str, str]]] = {}
        self._uniprot: dict[str, list[str]] = {}

    def _file(self, name: str) -> str:
        path = self.root / name
        if not path.exists() or time.time() - path.stat().st_mtime > MAX_AGE_S:
            text = http.get(f"{DATA}/{name}", expect="text", timeout_s=300)
            if not text:
                raise ToolError("upstream_server_error", f"GtoPdb {name} unavailable")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return path.read_text(encoding="utf-8")

    def load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            version, ligands = _rows(self._file("ligands.csv"))
            for row in ligands:
                key = (row.get("InChIKey") or "").strip()
                if key:
                    self.ligands_by_inchikey.setdefault(key, []).append(row["Ligand ID"])
            _, interactions = _rows(self._file("interactions.csv"))
            for row in interactions:
                for accession in (row.get("Target UniProt ID") or "").split("|"):
                    if accession.strip():
                        self.interactions.setdefault((row["Ligand ID"], accession.strip()), []).append(row)
            self.version, self._loaded = version, True

    def uniprot_for(self, target_chembl_id: str) -> list[str]:
        if target_chembl_id not in self._uniprot:
            path = self.root / "chembl_target_uniprot.json"
            known = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            if target_chembl_id not in known:
                body = http.get(f"{CHEMBL}/target/{target_chembl_id}.json")
                if body is None:
                    raise ToolError("input_invalid", f"unknown ChEMBL target {target_chembl_id}", retryable=False)
                known[target_chembl_id] = sorted({c["accession"] for c in body.get("target_components") or []
                                                  if c.get("accession")})
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(known, indent=1), encoding="utf-8")
            self._uniprot[target_chembl_id] = known[target_chembl_id]
        return self._uniprot[target_chembl_id]


def _float(text: str | None) -> float | None:
    try:
        return float(text) if text not in (None, "") else None
    except ValueError:
        return None


class GtoPdbAffinity:
    contract = ToolContract(
        tool_id="tool_drug_gtopdb_affinity", capability="interaction_evidence_lookup",
        capability_kind="relationship_evidence_lookup", question_kinds=("gtopdb_affinity",), contract_version="1",
        implementation_version="gtopdb-bulk-interactions-1",
        purpose_statement="Expert-curated affinities (pIC50/pKi/pKd) of a compound at a named target, with action type",
        evidence_kind_produced="curated_measurement", claim_strength_ceiling="measured",
        identity_inputs=("identifier",), required_inputs=("target_chembl_id",),
        license_id="CC BY-SA 4.0 (IUPHAR/BPS Guide to Pharmacology)")

    def __init__(self, data: GtoPdbData | None = None):
        self.data = data or GtoPdbData()

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        self.data.load()
        ligands = self.data.ligands_by_inchikey.get(inputs.get("identifier") or "", [])
        accessions = self.data.uniprot_for(inputs["target_chembl_id"])
        values = []
        for ligand in ligands:
            for accession in accessions:
                for row in self.data.interactions.get((ligand, accession), []):
                    if (row.get("Target Species") or "Human") != "Human" or row.get("Original Affinity Relation") not in ("", "=", None):
                        continue
                    median, low, high = (_float(row.get(k)) for k in ("Affinity Median", "Affinity Low", "Affinity High"))
                    if median is None and low is None and high is None:
                        continue
                    value = {"name": "affinity", "unit": "pChEMBL", "value_kind": "curated",
                             "source_record_ref": f"gtopdb_interaction_{ligand}_{accession}_{row.get('PubMed ID') or 'nopmid'}",
                             "conditions": {"affinity_type": row.get("Affinity Units"), "action": row.get("Action"),
                                            "type": row.get("Type"), "selectivity": row.get("Selectivity"),
                                            "primary_target": row.get("Primary Target"),
                                            "assay_description": row.get("Assay Description"),
                                            "pubmed_id": row.get("PubMed ID"), "gtopdb_ligand_id": ligand,
                                            "target_uniprot": accession, "gtopdb_version": self.data.version}}
                    if median is not None:
                        value["value"] = median
                    else:
                        value.update({"value": None, "value_low": low, "value_high": high})
                    values.append(value)
        return ProviderResponse(values=values, records=[{"gtopdb_ligand_ids": ligands, "target_uniprot": accessions,
                                                         "n_rows": len(values)}],
                                data_version=f"gtopdb:{self.data.version}",
                                upstream_refs=[f"gtopdb:ligand:{l}" for l in ligands])
