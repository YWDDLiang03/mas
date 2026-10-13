"""Identity from a documented universe file (e.g. one built by scripts/build_universe_chembl.py).

Members are resolved by exact identifier (InChIKey) against the file, with the file's
authority (ChEMBL) recorded; no network call is made.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mas.core.broker import ProviderResponse, ToolContract


class UniverseIdentity:
    contract = ToolContract(
        tool_id="tool_drug_universe_identity", capability="identity_resolution", capability_kind="entity_resolution",
        question_kinds=("resolve_name",), contract_version="1", implementation_version="universe-file-1",
        purpose_statement="Resolve universe members (InChIKey or name) against a documented universe file",
        evidence_kind_produced="database_entry", claim_strength_ceiling="curated", required_inputs=("name",),
        execution_location="in_process", license_id="per universe source (ChEMBL: CC BY-SA 3.0)")

    def __init__(self, path: str | Path):
        record = json.loads(Path(path).read_text(encoding="utf-8"))
        self.source = record["source"]
        self.by_key: dict[str, dict[str, Any]] = {}
        self.by_name: dict[str, list[dict[str, Any]]] = {}
        for member in record["universe"]:
            self.by_key[member["inchikey"]] = member
            for label in [member["name"], *member.get("synonyms", [])]:
                self.by_name.setdefault(label.lower(), []).append(member)

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        name = inputs["name"].strip()
        if name in self.by_key:
            members, basis = [self.by_key[name]], "exact_identifier_match"
        else:
            members = {m["inchikey"]: m for m in self.by_name.get(name.lower(), [])}.values()
            members, basis = list(members), "name_match_single_candidate"
        hits = [{"preferred_label": (m["name"] or "").title() if m["name"] and m["name"].isupper() else m["name"],
                 "identifiers": [{"scheme": "inchikey", "value": m["inchikey"], "scheme_authority": "IUPAC"},
                                 {"scheme": "chembl_id", "value": m["chembl_id"], "scheme_authority": "ChEMBL"}],
                 "aliases": [{"alias": s, "alias_source": "chembl_synonyms", "alias_kind": "synonym"} for s in m.get("synonyms", [])],
                 "max_phase": m.get("max_phase"),
                 "link_basis": basis if len(members) == 1 else "name_match_ambiguous"} for m in members]
        return ProviderResponse(values=[{"name": "identity", "value": h, "value_kind": "curated"} for h in hits],
                                data_version=self.source)
