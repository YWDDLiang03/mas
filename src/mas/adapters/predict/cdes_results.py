"""Collections, task bindings and exports for optional interaction analysis."""
from __future__ import annotations

import csv
import gzip
import io
import json
import re
import threading
import zipfile
from pathlib import Path

from mas.adapters.predict.cdes import digest, read_json


class StructureResults:
    def __init__(self, workspace: Path):
        self.root = workspace / "structure-results"
        self._cache = {}
        self._lock = threading.Lock()

    def _task_root(self, task_id: str) -> Path:
        if not re.fullmatch(r"task_[A-Za-z0-9_-]+", task_id):
            raise ValueError("Choose a valid research task")
        return self.root / task_id

    def enabled(self, task_id: str) -> bool:
        root = self._task_root(task_id)
        state = root / "module.json"
        return read_json(state).get("enabled") is True if state.exists() else (root / "current.json").exists()

    def set_enabled(self, task_id: str, enabled: bool) -> dict:
        if type(enabled) is not bool:
            raise ValueError("CDES must be on or off")
        from mas.core.clock import utc_now
        root = self._task_root(task_id)
        root.mkdir(parents=True, exist_ok=True)
        with self._lock:
            temporary = root / "module.tmp"
            temporary.write_text(json.dumps({"enabled": enabled, "updated_at": utc_now()}), encoding="utf-8")
            temporary.replace(root / "module.json")
        return {"enabled": enabled}

    def collections(self) -> list[dict]:
        collections = []
        for path in sorted(self.root.glob("task_*/cdes_*/manifest.json")):
            manifest = read_json(path)
            identity = manifest.get("integration_id", "")
            directory = path.parent.name
            if not re.fullmatch(r"cdes_[a-f0-9]{64}", identity) or directory not in (identity, identity[:29]):
                continue
            if manifest.get("origin") == "optional_module":
                continue
            collections.append({"id": path.parent.parent.name + ":" + identity,
                "label": "CDES · " + ", ".join(manifest.get("targets", [])),
                "targets": manifest.get("targets", []), "candidate_count": manifest["candidate_count"],
                "source_mode": "saved_results"})
        return collections

    def pin(self, source_id: str) -> dict:
        if source_id not in {row["id"] for row in self.collections()}:
            raise ValueError("Choose an available CDES result collection")
        task_id, identity = source_id.split(":", 1)
        root = self._task_root(task_id) / identity[:29]
        if not root.is_dir():
            root = self._task_root(task_id) / identity
        return {"source_task_id": task_id, "integration_id": identity,
                "dataset_sha256": digest((root / 'dataset.json.gz').read_bytes()), "source_mode": "saved_results"}

    def load_pinned(self, pin: dict) -> tuple[dict, Path]:
        identity = pin.get("integration_id", "")
        if not re.fullmatch(r"cdes_[a-f0-9]{64}", identity):
            raise ValueError("Invalid pinned CDES collection")
        parent = self._task_root(pin.get("source_task_id", ""))
        root = parent / identity[:29]
        if not root.is_dir():
            root = parent / identity
        packed = (root / "dataset.json.gz").read_bytes()
        if digest(packed) != pin.get("dataset_sha256"):
            raise ValueError("The selected CDES collection changed")
        return json.loads(gzip.decompress(packed)), root

    def load(self, task_id: str) -> tuple[dict | None, Path | None]:
        pointer = self._task_root(task_id) / "current.json"
        if not pointer.exists():
            return None, None
        reference = read_json(pointer)
        identity = reference["integration_id"]
        if not re.fullmatch(r"cdes_[a-f0-9]{64}", identity):
            raise ValueError("Invalid structure-result reference")
        directory = reference.get("directory", identity)
        if directory not in (identity, identity[:29]):
            raise ValueError("Invalid structure-result directory")
        root = pointer.parent / directory
        with self._lock:
            if identity not in self._cache:
                packed = (root / "dataset.json.gz").read_bytes()
                if digest(packed) != reference["dataset_sha256"]:
                    raise ValueError("Structure-result contents do not match their recorded checksum")
                value = json.loads(gzip.decompress(packed))
                if value["manifest"]["task_id"] != task_id:
                    raise ValueError("Structure results belong to a different task")
                self._cache[identity] = value
            return self._cache[identity], root

    def get(self, task_id: str, *, snapshot: str | None = None, wanted: str | None = None,
            cohort: str = "eligible", q: str = "", page: int = 1, page_size: int = 50) -> dict:
        data, _ = self.load(task_id)
        if data is None:
            return {"available": False, "module_enabled": self.enabled(task_id),
                    "reason": "not_imported", "task_id": task_id}
        manifest = data["manifest"]
        if not self.enabled(task_id):
            return {"available": False, "module_enabled": False, "reason": "module_disabled", "task_id": task_id,
                    "snapshot_id": manifest["snapshot_id"]}
        if snapshot and snapshot != manifest["snapshot_id"]:
            return {"available": False, "module_enabled": True, "reason": "different_evaluation", "task_id": task_id,
                    "snapshot_id": manifest["snapshot_id"]}
        if cohort not in ("eligible", "matched", "all", "unmatched", "admet"):
            raise ValueError("Unknown comparison population")
        items = data["candidates"]
        base = {"available": True, "module_enabled": True, "manifest": manifest,
                "targets": [{k: v for k, v in value.items() if k != "sequence"} for value in data["targets"].values()]}
        if wanted:
            row = next((row for row in items if wanted in (row["id"], row["candidate_ref"])), None)
            return dict(base, item=row, proteins=data["targets"] if row else {})
        if cohort == "admet":
            items = sorted(data["admet"], key=lambda row: (row["rank"], row["name"]))
        elif cohort == "eligible":
            items = [row for row in items if (row["evaluation"] or {}).get("classification") == "Eligible"]
        elif cohort == "matched":
            items = [row for row in items if row["candidate_ref"]]
        elif cohort == "unmatched":
            items = [row for row in items if not row["candidate_ref"]]
        if q.strip():
            term = q.strip().casefold()
            items = [row for row in items if term in row["name"].casefold() or term in row.get("id", "").casefold()
                     or term in (row.get("candidate_ref") or "").casefold()]
        page_size = max(1, min(200, page_size))
        total = len(items)
        page = max(1, min(page, max(1, (total + page_size - 1) // page_size)))
        start = (page - 1) * page_size
        return dict(base, items=items[start:start + page_size], cohort=cohort, total=total, page=page,
                    page_size=page_size, has_more=start + page_size < total)

    @staticmethod
    def csv(data: dict, kind: str) -> str:
        rows = []
        manifest = data["manifest"]
        if kind == "mapping":
            rows = [{"prediction_compound_id": item["id"], "name": item["name"],
                     "candidate_ref": item["candidate_ref"], "match_status": item["match_status"],
                     "related_candidate_ref": item.get("related_candidate_ref"), "smiles": item["smiles"]}
                    for item in data["candidates"]]
        elif kind == "original-only":
            rows = data.get("original_candidates_without_prediction", [])
        elif kind == "admet":
            for item in data["admet"]:
                rows.append({"name": item["name"], "prediction_compound_id": item["prediction_compound_id"],
                    "association_basis": item["association_basis"], "score": item["score"], "rank": item["rank"],
                    "population": item["population"], "file": item["file"], "sheet": item["sheet"], "row": item["row"],
                    **{value["label"]: value["value"] for value in item["values"]}})
        elif kind == "predictions":
            for item in data["candidates"]:
                for target, prediction in item["predictions"].items():
                    measured = item["measurements"].get(target, {})
                    rows.append({"prediction_compound_id": item["id"], "name": item["name"],
                        "candidate_ref": item["candidate_ref"], "match_status": item["match_status"],
                        "target": target, "target_uniprot": data["targets"][target]["uniprot"],
                        "sequence_sha256": data["targets"][target]["sequence_sha256"],
                        "interaction_score": prediction["raw_value"], "target_rank": prediction["rank"],
                        "prediction_population": prediction["population"], "file": prediction["file"], "row": prediction["row"],
                        "measured_value": measured.get("value"), "measured_unit": measured.get("unit"),
                        "claim_refs": json.dumps(measured.get("claim_refs", [])),
                        "saved_rank": (item["evaluation"] or {}).get("rank"),
                        "saved_score": (item["evaluation"] or {}).get("score"),
                        "snapshot_id": manifest["snapshot_id"], "integration_id": manifest["integration_id"]})
        else:
            raise ValueError("Choose predictions, mapping, original-only or admet")
        stream = io.StringIO(newline="")
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return stream.getvalue()

    def export(self, task_id: str, format: str, *, kind: str = "predictions", snapshot: str | None = None) -> tuple[str, bytes]:
        data, root = self.load(task_id)
        if data is None or root is None:
            raise KeyError("No structure results are attached to this research")
        if snapshot and snapshot != data["manifest"]["snapshot_id"]:
            raise ValueError("Choose the evaluation associated with these structure results")
        if format == "csv":
            return "text/csv; charset=utf-8", self.csv(data, kind).encode("utf-8-sig")
        if format == "json":
            return "application/json; charset=utf-8", json.dumps(data, ensure_ascii=False).encode()
        if format != "zip":
            raise ValueError("Choose CSV, JSON or ZIP")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("results.json", json.dumps(data, ensure_ascii=False, indent=2))
            archive.writestr("manifest.json", json.dumps(data["manifest"], ensure_ascii=False, indent=2))
            for name in ("predictions", "mapping", "original-only", "admet"):
                archive.writestr(name + ".csv", self.csv(data, name).encode("utf-8-sig"))
            for record in data["manifest"]["source_files"]:
                source = root / "sources" / record["file"]
                content = source.read_bytes()
                if digest(content) != record["sha256"]:
                    raise ValueError("A supplied source file has changed")
                archive.writestr("sources/" + record["file"], content)
            for record in data["manifest"].get("case_sources", []):
                content = (root / "sources/case" / record["file"]).read_bytes()
                if digest(content) != record["sha256"]:
                    raise ValueError("A linked case source has changed")
                archive.writestr("case/" + record["file"], content)
            archive.writestr("README.md", "# TRIAGE structure-prediction supplement\n\n"
                "results.json links imported CDES results to the saved TRIAGE evaluation.\n"
                "predictions.csv contains all supplied compound-target scores and source positions.\n"
                "mapping.csv records accepted and unresolved candidate correspondences.\n"
                "original-only.csv lists study candidates without a confirmed prediction correspondence.\n"
                "admet.csv preserves the supplied ADMETlab workbook scores and endpoint labels.\n"
                "sources/ contains the unchanged supplied result files; case/ contains linked case data.\n\n"
                "CDES values are classification scores (0–1); measured target values use pChEMBL.\n"
                "The original eligibility, composite scores and ranks are preserved.\n"
                "ADMET associations use exact supplied names; structural identity is not present in that workbook.\n"
                "Model weights, training records and a calibration result were not included in the input package.\n")
        return "application/zip", output.getvalue()
