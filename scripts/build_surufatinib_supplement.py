"""Read one declared primary paper with the real reader; do not attach any task.

Run with the project virtualenv. Credentials are resolved only by ModelRoster.
This source selection follows a known gap and is recorded as exploratory.
"""

from __future__ import annotations

import json
from pathlib import Path

from mas.adapters.literature.europepmc import EuropePMCReader
from mas.core import reading, task
from mas.core.broker import Broker
from mas.core.canonical import sha256_hex
from mas.core.clock import utc_now
from mas.core.ids import new_id
from mas.core.journal import actor
from mas.core.models import ModelRoster
from mas.core.runtime import Core


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "design_audit/windows_execution_2026-10-16/supplement_source_2024.json"
TARGETS = {"CSF1R": "CHEMBL1844", "VEGFR1": "CHEMBL1868", "VEGFR2": "CHEMBL279",
           "VEGFR3": "CHEMBL1955", "FGFR1": "CHEMBL3650"}
IDENTIFIER = "TTZSNFLLYPYKIL-UHFFFAOYSA-N"


def main() -> None:
    if REPORT.exists():
        raise SystemExit(f"source report already exists: {REPORT}; inspect it before requesting another paid read")
    roster = ModelRoster.from_toml(ROOT / "var/primary/store/models_deepseek.toml")
    adapter = roster.adapter("reader")
    if adapter.record.model_id != "deepseek-v4-flash":
        raise SystemExit("this source read authorizes deepseek-v4-flash only")
    adapter.reasoning_effort = "medium"
    who = actor("agent", "verified-supplement-source-reader", "reader")
    with Core.open(ROOT / "var/primary/store") as core:
        source_task, _ = task.record_version(core, {
            "objective_text": "Extract original Surufatinib measurements from one declared 2024 primary paper.",
            "mode": "conditional", "evaluation_scope": "declared single-source evidence reading",
            "scope_entities": [{"label": name, "identifier_scheme": "chembl_target", "identifier": target,
                                "role": "required"} for name, target in TARGETS.items()],
            "candidate_universe": {"kind": "enumerated_set", "members": [IDENTIFIER]},
            "seed_candidates": [], "unknowns": []}, by=who)
        run_id = new_id("run")
        run_binding = {"run_id": run_id, "task_context_id@v": f"{source_task}@v1",
                       "run_purpose": "verified_supplement_source", "role_bindings": roster.role_bindings(),
                       "research_preset": "standard", "research_level": "mid",
                       "declared_source": "doi:10.1038/s42004-023-01084-0",
                       "selection_kind": "exploratory_known_gap_source",
                       "bound_at": utc_now(), "bound_by": who}
        binding_ref = core.artifacts.put("run_binding", run_binding)
        core.journal.append(run_id, "run.created", actor=who,
                            payload={"binding_artifact_id": binding_ref, "task_id": source_task}, state_to="queued")
        core.journal.append(run_id, "run.started", actor=who, state_from="queued", state_to="running")
        report = {"source_task_id": source_task, "source_run_id": run_id, "binding_ref": binding_ref,
                  "status": "running"}
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        try:
            broker = Broker(core)
            broker.register(EuropePMCReader())
            hit = {"source": "europepmc", "doi": "10.1038/s42004-023-01084-0", "pmid": "38172256",
                   "pmcid": "PMC10764862", "identifiers": [
                       {"scheme": "doi", "value": "10.1038/s42004-023-01084-0"},
                       {"scheme": "pmcid", "value": "PMC10764862"}],
                   "title": "Structural basis and selectivity of sulfatinib binding to FGFR and CSF-1R",
                   "authors": "Lin Q et al.", "journal": "Communications Chemistry", "year": "2024",
                   "first_publication_date": "2024-01-03", "pub_types": ["Journal Article"],
                   "is_preprint": False, "is_review": False}
            document = reading.read(core, broker, run_id, hit, cutoff_date="2026-10-16")
            if document is None or document.get("reading_depth") != "full_text":
                raise RuntimeError("the declared source full text was not available")
            claims = reading.extract_claims(core, roster, run_id, document, {
                "purpose": "candidate_attribute",
                "objective_text": (
                    "Read all original experimental biochemical IC50/Ki/Kd/EC50 measurements in this study for "
                    "Surufatinib (sulfatinib) against the five listed required receptors. Include all eligible "
                    "measurements, never select by favorable value. State wild type or exact mutant in "
                    "system_or_population for every numerical claim. Extract mutant results too so they can be "
                    "explicitly excluded in scope review. Distinguish newly measured results from citations to "
                    "previous studies and from measurements of other compounds. Do not infer numerical values "
                    "from qualitative statements. FGFR1 and CSF1R are separate attributes: the sentence giving "
                    "34 and 5 nM reports them in that order."),
                "candidate": {"candidate_id": f"cand_inchikey-{IDENTIFIER}",
                              "labels": ["Surufatinib", "sulfatinib", "HMPL-012"]},
                "attributes": [{"name": f"{name} curated potency", "ref": f"supplement_{target}@v1",
                                "unit": "pChEMBL",
                                "definition": f"Original biochemical inhibition measurements of sulfatinib "
                                              f"against human {name}; preserve reported unit and mutation condition."}
                               for name, target in TARGETS.items()]}, max_chars=60_000)
            report.update(status="extracted_pending_scope_review", document_ref=document["document_artifact_id"],
                          document_sha256=sha256_hex(core.artifacts.payload(document["document_artifact_id"])),
                          claims=[{"claim_id": c["claim_id"], "attribute_ref": c.get("attribute_ref"),
                                   "value": c.get("value"), "unit": c.get("unit"),
                                   "scope": c.get("scope"), "admission_state": c["admission_state"],
                                   "admission_reasons": c["admission_reasons"]} for c in claims])
            core.journal.append(run_id, "run.completed", actor=who, state_from="running", state_to="completed",
                                payload={"purpose": "verified_supplement_source", "claims_extracted": len(claims)})
        except Exception as error:
            report.update(status="failed", error_class=type(error).__name__)
            core.journal.append(run_id, "run.failed", actor=who, state_from="running", state_to="failed",
                                payload={"error_class": type(error).__name__})
            raise
        finally:
            finished = [e.payload for e in core.journal.replay(run_id) if e.event_type == "agent.finished"]
            report["model_calls"] = [{k: p.get(k) for k in ("model_id", "usage", "cost_usd", "schema_ok")}
                                     for p in finished]
            report["cost_is_estimate"] = True
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
