"""Reconstruct a candidate universe from ChEMBL: small molecules at max_phase >= 3, salts collapsed to parents.

Usage: python scripts/build_universe_chembl.py OUT.json [--min-phase 3]
The output records its source, query, date, and counts, so the universe is a documented
`named_library`, never mistaken for an author-supplied list.
"""

import argparse
import json
import time

import requests

BASE = "https://www.ebi.ac.uk/chembl/api/data/molecule"
FIELDS = ("oral", "parenteral", "topical", "black_box_warning", "first_approval", "withdrawn_flag")


def fetch(min_phase: float) -> list[dict]:
    rows, offset, limit = [], 0, 1000
    while True:
        for attempt in range(5):
            try:
                reply = requests.get(BASE, timeout=120, params={
                    "max_phase__gte": min_phase, "molecule_type": "Small molecule", "format": "json", "limit": limit,
                    "offset": offset, "only": "molecule_chembl_id,pref_name,max_phase,molecule_structures,molecule_hierarchy,molecule_synonyms,oral,parenteral,topical,black_box_warning,first_approval,withdrawn_flag"})
                reply.raise_for_status()
                break
            except requests.RequestException:
                time.sleep(2 ** attempt)
        else:
            raise SystemExit(f"ChEMBL unreachable at offset {offset}")
        body = reply.json()
        rows.extend(body["molecules"])
        if not body["page_meta"]["next"]:
            return rows
        offset += limit


def _merge_fields(rows: list[dict]) -> dict:
    """Route and warning flags are true if any salt form has them; dates take the earliest value."""
    merged = {}
    for key in FIELDS:
        values = [r.get(key) for r in rows if r.get(key) is not None]
        if not values:
            merged[key] = None
        elif key == "first_approval":
            merged[key] = min(values)
        else:
            merged[key] = any(bool(v) for v in values)
    return merged


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--min-phase", type=float, default=3)
    args = parser.parse_args()
    rows = fetch(args.min_phase)
    by_parent: dict[str, dict] = {}
    no_structure = 0
    for row in rows:
        structures = row.get("molecule_structures") or {}
        inchikey = structures.get("standard_inchi_key")
        if not inchikey:
            no_structure += 1
            continue
        parent = (row.get("molecule_hierarchy") or {}).get("parent_chembl_id") or row["molecule_chembl_id"]
        entry = by_parent.setdefault(parent, {"parent_chembl_id": parent, "members": []})
        synonyms = [s.get("molecule_synonym") for s in row.get("molecule_synonyms") or [] if s.get("molecule_synonym")]
        entry["members"].append({"chembl_id": row["molecule_chembl_id"], "pref_name": row.get("pref_name"),
                                 "inchikey": inchikey, "max_phase": row.get("max_phase"), "synonyms": synonyms,
                                 "fields": {k: row.get(k) for k in FIELDS}})
    universe = []
    for parent, entry in sorted(by_parent.items()):
        chosen = next((m for m in entry["members"] if m["chembl_id"] == parent), entry["members"][0])
        universe.append({"name": chosen["pref_name"] or chosen["chembl_id"], "inchikey": chosen["inchikey"],
                         "chembl_id": chosen["chembl_id"], "max_phase": max(float(m["max_phase"] or 0) for m in entry["members"]),
                         "salt_forms": [m["chembl_id"] for m in entry["members"] if m["chembl_id"] != chosen["chembl_id"]],
                         "synonyms": sorted({s for m in entry["members"] for s in m["synonyms"]} - {chosen["pref_name"]})[:20],
                         "fields": _merge_fields([m["fields"] for m in entry["members"]])})
    record = {"source": "ChEMBL web services", "query": {"max_phase__gte": args.min_phase, "molecule_type": "Small molecule"},
              "retrieved_at": time.strftime("%Y-%m-%d"), "rows_returned": len(rows), "rows_without_structure": no_structure,
              "parents": len(universe), "note": "Reconstruction; the authors' 3,171-compound list was not available.",
              "universe": universe}
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in record.items() if k != "universe"}, indent=1))


if __name__ == "__main__":
    main()
