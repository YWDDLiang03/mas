"""Prediction worker, executed by the ADMET predictor's own interpreter (never by `mas`).

It is run as a script by another Python (`python -m` is not used: the `mas` package is not
importable there), so it imports only the standard library and `admet_ai`. Importing anything
from `mas` here would make the core's dependency set the predictor env's as well, which is the
one thing the subprocess boundary exists to prevent.

Protocol, one JSON value per line:

    stdin   a SMILES string, or {"smiles": "..."}; blank lines are ignored
    stdout  {"kind": "meta", ...}                 once, before any row
            {"kind": "panel", "endpoints": [...]} once: the package's own endpoint metadata
            {"kind": "row", "smiles": s, "values": {endpoint: float, ...}}
            {"kind": "row", "smiles": s, "error": "..."}   a structure the predictor refused
            {"kind": "done", "rows": n}           once, last

WHY the rows are written to a duplicate of the real stdout while the library gets stderr:
`admet_ai` prints an RDKit warning for every molecule it drops and `lightning` draws a `rich`
progress bar, both on stdout, so a reader parsing stdout as JSON lines reads a progress bar as
a prediction. The redirection happens before `admet_ai` is imported, so nothing it prints at
import time lands in the protocol either.
"""

import json
import os
import sys

DRUGBANK_SUFFIX = "_drugbank_approved_percentile"


def _open_protocol():
    """The real stdout, with the library's stdout pointed at stderr."""
    duplicate = os.dup(1)
    os.dup2(2, 1)   # fd 1 is now stderr, so `print` and `rich` leave the protocol alone
    return os.fdopen(duplicate, "w", buffering=1, encoding="utf-8")


def _smiles_from(line: str) -> str | None:
    value = json.loads(line)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("smiles")
    return None


def main(argv: list[str]) -> int:
    chunk_size = int(argv[1]) if len(argv) > 1 else 256
    out = _open_protocol()

    def emit(record: dict) -> None:
        out.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")

    requested: list[str] = []
    seen: set[str] = set()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        smiles = _smiles_from(line)
        if smiles and smiles not in seen:
            seen.add(smiles)
            requested.append(smiles)

    import importlib.metadata

    from admet_ai import ADMETModel
    from admet_ai.admet_info import get_admet_info

    version = importlib.metadata.version("admet-ai")
    info = get_admet_info()

    def text(value):
        return None if value is None or value != value else str(value)

    panel = [{"id": text(row["id"]), "name": text(row["name"]), "category": text(row["category"]),
              "task_type": text(row["task_type"]), "package_units": text(row["units"]),
              "species": text(row["species"]), "url": text(row["url"]),
              "size": None if row["size"] != row["size"] else int(row["size"])}
             for row in info.to_dict(orient="records")]
    model = ADMETModel()
    emit({"kind": "meta", "package": "admet-ai", "version": version, "requested": len(requested),
          "num_ensembles": model.num_ensembles,
          "tasks": [task for tasks in model.task_lists for task in tasks],
          "physchem": model.include_physchem, "device": model.device})
    emit({"kind": "panel", "endpoints": panel})

    written = 0
    for start in range(0, len(requested), chunk_size):
        chunk = requested[start:start + chunk_size]
        frame = model.predict(smiles=list(chunk))
        rows = {} if frame is None else frame.to_dict(orient="index")
        for smiles in chunk:
            row = rows.get(smiles)
            if row is None:
                # `ADMETModel.predict` drops a SMILES RDKit cannot parse, so a missing row is a
                # refused structure and is reported as one: a silently absent row would reach the
                # caller as "no prediction" and from there as "no data".
                emit({"kind": "row", "smiles": smiles, "error": "the predictor could not build a molecule from this SMILES"})
            else:
                values = {key: (None if value != value else float(value))
                          for key, value in row.items() if not key.endswith(DRUGBANK_SUFFIX)}
                percentiles = {key[:-len(DRUGBANK_SUFFIX)]: (None if value != value else float(value))
                               for key, value in row.items() if key.endswith(DRUGBANK_SUFFIX)}
                emit({"kind": "row", "smiles": smiles, "values": values, "percentiles": percentiles})
            written += 1
    emit({"kind": "done", "rows": written})
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
