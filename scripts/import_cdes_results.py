"""Attach a supplied CDES result archive to one completed local study."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mas.adapters.predict.cdes import install_dataset, prepare_dataset
from mas.ui.structure_results import StructureResults


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--case", type=Path, required=True, help="Saved case export directory")
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--structures", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True, help="Directory containing store/")
    parser.add_argument("--target", action="append", required=True, help="Target label=UniProt accession")
    parser.add_argument("--export", type=Path, help="Write a portable ZIP alongside the installed dataset")
    args = parser.parse_args()
    targets = dict(value.split("=", 1) for value in args.target)
    data, sources = prepare_dataset(args.archive, args.case, args.universe, args.structures, targets)
    for record in data["manifest"]["case_sources"]:
        sources["case/" + record["file"]] = (args.case / record["file"]).read_bytes()
    root = install_dataset(data, sources, args.workspace)
    if args.export:
        service = StructureResults(args.workspace)
        _, content = service.export(data["manifest"]["task_id"], "zip")
        args.export.parent.mkdir(parents=True, exist_ok=True)
        args.export.write_bytes(content)
    print(json.dumps({"installed": str(root), "manifest": data["manifest"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
