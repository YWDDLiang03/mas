"""Saved CDES results and the input/output boundary for a future deployed model.

This supplement is linked to a completed evaluation. It never writes assessments
or contributes values to the saved leaderboard.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from xml.etree import ElementTree as ET


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def xlsx_rows(content: bytes) -> list[dict]:
    """Read stored values and formulas without executing workbook content."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(content)) as book:
        strings = []
        if "xl/sharedStrings.xml" in book.namelist():
            strings = ["".join(t.text or "" for t in item.findall(".//m:t", ns))
                       for item in ET.fromstring(book.read("xl/sharedStrings.xml")).findall("m:si", ns)]
        rows = []
        for row in ET.fromstring(book.read("xl/worksheets/sheet1.xml")).findall(".//m:row", ns):
            cells = {}
            for cell in row.findall("m:c", ns):
                value = cell.findtext("m:v", "", ns)
                if cell.get("t") == "s":
                    value = strings[int(value)]
                elif cell.get("t") == "inlineStr":
                    value = "".join(t.text or "" for t in cell.findall(".//m:t", ns))
                column = re.sub(r"\d", "", cell.get("r", ""))
                cells[column] = value
            rows.append({"row": int(row.get("r")), "values": cells})
        return rows


def prepare_dataset(archive: Path, case: Path, universe: Path, structures: Path,
                    targets: dict[str, str]) -> tuple[dict, dict[str, bytes]]:
    summary = read_json(case / "source-data/run-summary.json")
    library = read_json(universe)["universe"]
    smiles = read_json(structures)
    by_id = {row["chembl_id"]: row for row in library}
    by_smiles: dict[str, list[dict]] = {}
    for row in library:
        if smiles.get(row["chembl_id"]):
            by_smiles.setdefault(smiles[row["chembl_id"]], []).append(row)
    outcomes = {row["Candidate"].casefold(): row for row in read_csv(case / "source-data/AI_Data_2_candidate_results.csv")}
    claims: dict[tuple[str, str], list[str]] = {}
    for row in read_csv(case / "source-data/AI_Data_7_target_observations.csv"):
        key = (row["Candidate"].casefold(), row["Target criterion"].split()[0])
        claims.setdefault(key, []).append(row["Claim reference"])
    observations = {}
    score_rules = {row["Criterion"]: row["Rule reference"]
                   for row in read_csv(case / "source-data/AI_Data_4_eligible_candidate_scores.csv")}
    for row in read_json(case / "source-data/source_records/target_observation_records.json")["cell_checks"]:
        target = row["criterion"].split()[0]
        observations[row["candidate"].casefold(), target] = {
            "value": row["stored"], "unit": "pChEMBL", "basis": "measured",
            "observation_count": row["observations"], "endpoint_types": row["endpoint_types"],
            "claim_refs": claims.get((row["candidate"].casefold(), target), []),
            "rule_ref": score_rules.get(row["criterion"]),
        }
    source_files = {}
    candidates: dict[str, dict] = {}
    proteins = {}
    source_index = []
    archive_bytes = archive.read_bytes()
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as source:
        for target, uniprot in targets.items():
            filename = f"{target}_screen_results.csv"
            matches = [name for name in source.namelist() if name.endswith("/" + filename)]
            if len(matches) != 1:
                raise ValueError(f"Expected one {filename}")
            content = source.read(matches[0])
            source_files[filename] = content
            rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
            values = [float(row["y_scores"]) for row in rows]
            if any(not math.isfinite(v) or not 0 <= v <= 1 for v in values):
                raise ValueError(f"Invalid interaction score in {filename}")
            sequences = {row["Protein"] for row in rows}
            if len(sequences) != 1 or any(row["Gene Name"] != target for row in rows):
                raise ValueError(f"Target/sequence mismatch in {filename}")
            sequence = sequences.pop()
            proteins[target] = {"label": target, "uniprot": uniprot, "sequence": sequence,
                                "sequence_sha256": digest(sequence.encode()), "residues": len(sequence)}
            ranks = {}
            for rank, score in enumerate(sorted(values, reverse=True), 1):
                ranks.setdefault(score, rank)
            seen = set()
            for line, row in enumerate(rows, 2):
                identifier, structure = row["Drug ChEMBL ID"], row["SMILES"]
                if identifier in seen:
                    raise ValueError(f"Duplicate compound-target pair in {filename}: {identifier}")
                seen.add(identifier)
                prior = candidates.get(identifier)
                if prior and (prior["smiles"] != structure or prior["name"] != row["Drug Name"]):
                    raise ValueError(f"Inconsistent compound identity: {identifier}")
                item = candidates.setdefault(identifier, {"id": identifier, "name": row["Drug Name"],
                    "smiles": structure, "predictions": {}, "candidate_ref": None, "match_status": "unmatched",
                    "measurements": {}, "evaluation": None, "admet": None})
                value = float(row["y_scores"])
                item["predictions"][target] = {"value": value, "raw_value": row["y_scores"],
                    "class": int(row["y_preds"]), "rank": ranks[value], "population": len(rows),
                    "file": filename, "row": line, "basis": "predicted"}
            source_index.append({"file": filename, "sha256": digest(content), "rows": len(rows)})
        if any(set(row["predictions"]) != set(targets) for row in candidates.values()):
            raise ValueError("The target files contain different candidate sets")
        for item in candidates.values():
            original = by_id.get(item["id"])
            if original and smiles.get(item["id"]) == item["smiles"]:
                item["match_status"] = "identifier_and_structure"
            elif original:
                item["match_status"] = "structure_review"
                item["related_candidate_ref"] = "cand_inchikey-" + original["inchikey"]
                original = None
            else:
                matches = by_smiles.get(item["smiles"], [])
                original = matches[0] if len(matches) == 1 else None
                item["match_status"] = "exact_structure" if original else "ambiguous" if matches else "unmatched"
            if original:
                item["candidate_ref"] = "cand_inchikey-" + original["inchikey"]
                outcome = outcomes.get(original["name"].casefold())
                if outcome:
                    item["evaluation"] = {"label": outcome["Candidate"], "classification": outcome["Classification"],
                        "rank": int(outcome["Rank"]) if outcome["Rank"] else None,
                        "score": float(outcome["Score"]) if outcome["Score"] else None,
                        "requirements_supported": int(outcome["Requirements supported"])}
                item["measurements"] = {target: observations[original["name"].casefold(), target]
                    for target in targets if (original["name"].casefold(), target) in observations}
        # One current candidate must not silently choose between two source structures.
        groups: dict[str, list[dict]] = {}
        for item in candidates.values():
            if item["candidate_ref"]:
                groups.setdefault(item["candidate_ref"], []).append(item)
        for group in groups.values():
            if len(group) > 1:
                exact = [item for item in group if item["match_status"] == "identifier_and_structure"]
                for item in group:
                    if len(exact) == 1 and item is exact[0]:
                        continue
                    item.update(related_candidate_ref=item["candidate_ref"], candidate_ref=None,
                                match_status="duplicate_correspondence", measurements={}, evaluation=None)
        admet_names = [name for name in source.namelist() if name.lower().endswith("/admet_evaluation.xlsx")]
        if len(admet_names) != 1:
            raise ValueError("Expected one ADMET evaluation workbook")
        content = source.read(admet_names[0])
        source_files["ADMET_evaluation.xlsx"] = content
        sheet = xlsx_rows(content)
        header = sheet[0]["values"]
        admet = []
        names: dict[str, list[dict]] = {}
        for item in candidates.values():
            names.setdefault(item["name"].casefold(), []).append(item)
        for row in sheet[1:]:
            cells = row["values"]
            record = {"name": cells["B"], "score": float(cells["A"]), "row": row["row"],
                "file": "ADMET_evaluation.xlsx", "sheet": "admet", "basis": "predicted",
                "provider": "ADMETlab 3.0 (as described in the supplied package)",
                "values": [{"label": label, "value": float(cells[column]), "cell": f"{column}{row['row']}"}
                           for column, label in header.items() if column not in ("A", "B")]}
            matches = names.get(record["name"].casefold(), [])
            record["prediction_compound_id"] = matches[0]["id"] if len(matches) == 1 else None
            record["association_basis"] = "exact_name" if len(matches) == 1 else "unmatched"
            admet.append(record)
        ranks = {}
        for rank, value in enumerate(sorted((row["score"] for row in admet), reverse=True), 1):
            ranks.setdefault(value, rank)
        for record in admet:
            record["rank"] = ranks[record["score"]]
            record["population"] = len(admet)
            if record["prediction_compound_id"]:
                candidates[record["prediction_compound_id"]]["admet"] = record
        source_index.append({"file": "ADMET_evaluation.xlsx", "sha256": digest(content), "rows": len(admet)})
    source_case_files = ["source-data/run-summary.json"] + [
        path.relative_to(case).as_posix() for path in sorted((case / "source-data").glob("AI_Data_*"))
        if path.is_file()] + [path.relative_to(case).as_posix()
                            for path in sorted((case / "source-data/source_records").glob("*.json"))]
    case_index = [{"file": name, "sha256": digest((case / name).read_bytes())} for name in source_case_files]
    identity = digest(json.dumps({"sources": source_index, "case": case_index, "targets": targets,
        "universe": digest(universe.read_bytes()), "structures": digest(structures.read_bytes()),
        "importer_version": 3}, sort_keys=True).encode())
    items = sorted(candidates.values(), key=lambda row: ((row["evaluation"] or {}).get("rank") or 10**9,
                                                        row["name"].casefold(), row["id"]))
    eligible = [row for row in items if (row["evaluation"] or {}).get("classification") == "Eligible"]
    matched_refs = {row["candidate_ref"] for row in items if row["candidate_ref"]}
    original_only = [{"candidate_ref": "cand_inchikey-" + row["inchikey"], "name": row["name"],
                      "chembl_id": row["chembl_id"]} for row in library
                     if "cand_inchikey-" + row["inchikey"] not in matched_refs]
    from collections import Counter
    manifest = {"integration_id": "cdes_" + identity, "schema_version": 1, "source_mode": "saved_results",
        "task_id": summary["task_id"], "run_id": summary["run_id"], "snapshot_id": summary["snapshot_id"],
        "source_archive_sha256": digest(archive_bytes), "source_files": source_index, "case_sources": case_index,
        "model_version": None, "prediction_generated_at": None, "calibration_status": "not_assessed",
        "targets": list(targets), "original_candidate_count": summary["candidate_count"],
        "candidate_count": len(items), "prediction_count": sum(len(r["predictions"]) for r in items),
        "admet_count": len(admet), "matched_candidates": sum(bool(r["candidate_ref"]) for r in items),
        "original_candidates_without_prediction": len(original_only),
        "match_counts": dict(Counter(r["match_status"] for r in items)),
        "eligible_matched": len(eligible), "eligible_target_observations": sum(len(r["measurements"]) for r in eligible),
        "eligible_target_gaps": sum(len(targets) - len(r["measurements"]) for r in eligible),
        "score_contribution": False, "case_summary": summary,
        "admet_association": "Exact supplied drug name; workbook contains no chemical identifiers or structures"}
    return {"manifest": manifest, "targets": proteins, "candidates": items, "admet": admet,
            "original_candidates_without_prediction": original_only}, source_files


def install_dataset(dataset: dict, sources: dict[str, bytes], workspace: Path) -> Path:
    manifest = dataset["manifest"]
    # Keep nested source names within ordinary Windows path lengths. The full
    # content identity and checksum remain in the manifest and pointer.
    directory = manifest["integration_id"][:29]
    root = workspace / "structure-results" / manifest["task_id"] / directory
    payload = json.dumps(dataset, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    root.mkdir(parents=True, exist_ok=True)
    packed = gzip.compress(payload, mtime=0)
    path = root / "dataset.json.gz"
    if path.exists() and path.read_bytes() != packed:
        raise ValueError("An integration with this identity already contains different data")
    path.write_bytes(packed)
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "sources").mkdir(exist_ok=True)
    for name, data in sources.items():
        target = root / "sources" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    pointer = root.parent / "current.json"
    temporary = pointer.with_suffix(".tmp")
    temporary.write_text(json.dumps({"integration_id": manifest["integration_id"], "directory": directory,
                                   "dataset_sha256": digest(packed)}), encoding="utf-8")
    temporary.replace(pointer)
    return root


@dataclass(frozen=True)
class PairRequest:
    candidate_id: str
    smiles: str
    target_uniprot: str
    protein_sequence: str


class InteractionScorer(Protocol):
    """A deployed implementation can replace SavedResultScorer with this contract."""
    def predict_pairs(self, pairs: list[PairRequest]) -> dict: ...


class SavedResultScorer:
    def __init__(self, dataset: dict):
        self.dataset = dataset
        self.rows = {row["id"]: row for row in dataset["candidates"]}
        self.rows.update({row["candidate_ref"]: row for row in dataset["candidates"] if row["candidate_ref"]})
        self.targets = {row["uniprot"]: key for key, row in dataset["targets"].items()}

    def predict_pairs(self, pairs: list[PairRequest]) -> dict:
        results, errors = [], []
        for pair in pairs:
            row, target = self.rows.get(pair.candidate_id), self.targets.get(pair.target_uniprot)
            code = None
            if row is None or target is None:
                code = "saved_result_missing"
            elif row["smiles"] != pair.smiles:
                code = "structure_mismatch"
            elif self.dataset["targets"][target]["sequence"] != pair.protein_sequence:
                code = "sequence_mismatch"
            if code:
                errors.append({"candidate_id": pair.candidate_id, "target_uniprot": pair.target_uniprot,
                               "error_code": code, "retryable": False})
                continue
            value = row["predictions"][target]
            results.append({"candidate_id": pair.candidate_id, "target_uniprot": pair.target_uniprot,
                "value": value["value"], "value_scale": "classification_score_0_1", "basis": "predicted",
                "source_mode": "saved_results", "source": value,
                "integration_id": self.dataset["manifest"]["integration_id"], "model_version": None})
        return {"results": results, "errors": errors}
