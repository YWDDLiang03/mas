"""Summarize selection reasons from a saved result package, without rerunning research."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mas.ui.decision_reading import (
    SELECTION_DECISIONS, SELECTION_POLICY,
    criterion_disposition, eligibility_counts, eligibility_reading, selection_reading,
)


def audit(results: Path, output: Path) -> dict:
    snapshot_path, cqa_path = results / "snapshot.json", results / "cqa.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    cqa = json.loads(cqa_path.read_text(encoding="utf-8"))
    rules = {row["rule_ref"]: row for row in cqa["items"] if row.get("rule_ref")}
    readings = [eligibility_reading(row, rules) for row in snapshot["candidate_entries"]]
    decisions = [selection_reading(reading) for reading in readings]
    withheld = []
    for row in cqa["items"]:
        if not row.get("current"):
            continue
        evaluation = row.get("evaluation") or {}
        if evaluation.get("state") == "enabled":
            continue
        explanation = criterion_disposition(row, evaluation)
        withheld.append({"name": row["name"], "criterion_ref": row.get("detail_ref") or row.get("rule_ref"),
                         **explanation, "recorded_reason": evaluation.get("reason") or row.get("reason")})
    counts = Counter(item["decision"] for item in decisions)
    counts.update({key: 0 for key in SELECTION_DECISIONS})
    report = {"snapshot_id": snapshot["snapshot_id"], "rule_set": snapshot.get("rules@v"),
              "source_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (snapshot_path, cqa_path)},
              "reading_scope": "Saved qualification records and verdicts; no new source retrieval or assessment.",
              "total": len(decisions), "selection_counts": dict(counts),
              "selection_policy": SELECTION_POLICY,
              "confirmed_mandatory_failures": sum(item["confirmed_mandatory_failure"] for item in decisions),
              "evidence_reason_summary": eligibility_counts(readings),
              "evidence_incomplete_summary": eligibility_counts([reading for reading, decision in zip(readings, decisions)
                                                                  if decision["decision"] == "evidence_incomplete"]),
              "exclusion_summary": eligibility_counts([reading for reading, decision in zip(readings, decisions)
                                                        if decision["decision"] == "excluded"]),
              "withheld_counts": dict(Counter(item["code"] for item in withheld)), "withheld_items": withheld}
    output.mkdir(parents=True, exist_ok=True)
    (output / "selection-audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (output / "candidate-selection.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ("candidate", "selection", "reason_code", "mandatory_passed", "mandatory_total",
                  "required_supported", "required_total", "affected_requirements", "rank", "score",
                  "evidence_profile", "selection_policy", "selection_reason_code")
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        for entry, reading, decision in zip(snapshot["candidate_entries"], readings, decisions):
            writer.writerow({"candidate": next(iter(entry.get("identity_labels") or []), entry["candidate_ref"]),
                "selection": decision["decision"], "reason_code": reading["reason_code"], "selection_reason_code": decision["reason_code"],
                "evidence_profile": reading["evidence_profile"]["state"], "selection_policy": decision["policy"],
                **{key: reading.get(key) for key in fields[3:7]},
                "affected_requirements": "; ".join(item["name"] for item in reading["issues"]),
                "rank": entry.get("position"), "score": entry.get("preference_score")})
    with (output / "withheld-criteria.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, ("name", "criterion_ref", "code", "label", "description", "recorded_reason"))
        writer.writeheader()
        writer.writerows(withheld)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.results, args.output)
    print(json.dumps({"total": report["total"], "selection_counts": report["selection_counts"],
                      "withheld_counts": report["withheld_counts"]}, indent=2))
