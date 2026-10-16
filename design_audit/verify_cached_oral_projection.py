"""Read-only validation of the fixed admitted clinical facts; no documents or models are read/called."""
import argparse
import json
from pathlib import Path

from mas.adapters.drug.clinical_routes import ClinicalRouteCache, load_source_records
from mas.adapters.drug.registration import objective_templates
from mas.core import assessor
from mas.core.canonical import sha256_hex
from mas.core.runtime import Core

SOURCE_RUNS = ["run_01M4X89HR1T8BNAVBK250W324X", "run_01M4XNVDGEMHPP74KJG43FCF6J",
    "run_01M4XPSN5YPJ3EJ84X10HMTERH", "run_01M4XXVMW87SVY7MWXWCAG4X7X", "run_01M4YGC2D1W2EN53WEM1VANR0Z",
    "run_01M4ZH2XBWXFK5G5MEJYP87SN2", "run_01M4ZJ0M0SCXNQVDKESHXYFC55", "run_01M4ZJFG0NWX64771NVHYV0BFH",
    "run_01M4ZJWXHPXZRTDHFM6SW3XVTM", "run_01M4ZJZJM6NADXR9MPJN479F43"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path("var/primary/store"))
    parser.add_argument("--universe", type=Path, default=Path("var/primary/universe_chembl.json"))
    parser.add_argument("--out", type=Path, default=Path("design_audit/cached_oral_projection_2026-10-16.json"))
    args = parser.parse_args()
    assert not args.out.resolve().is_relative_to(args.store.resolve())
    library = json.loads(args.universe.read_text(encoding="utf-8"))
    claims, provenance = {}, {}
    with Core.open(args.store, read_only=True) as core:
        for run_id in SOURCE_RUNS:
            for (body,) in core.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='evidence.admitted' ORDER BY seq", (run_id,)):
                event = json.loads(body)
                envelope = core.artifacts.get(event["payload"]["artifact_id"])
                assert envelope["kind"] == "claim"
                claim = envelope["payload"]
                claims[claim["claim_id"]] = claim
                provenance[claim["claim_id"]] = {"artifact_id": event["payload"]["artifact_id"], "sha256": sha256_hex(claim),
                    "run_id": run_id, "seq": event["seq"], "event_id": event["event_id"]}
        sources = load_source_records(core, {c["source_ref"] for c in claims.values()})
        cache = ClinicalRouteCache(list(claims.values()), {ref: row["source"] for ref, row in sources.items()},
            library["universe"], source_provenance=provenance, cutoff_date="2026-10-16")
        identity = "cand_inchikey-TTZSNFLLYPYKIL-UHFFFAOYSA-N"
        facts = cache.claims_for(identity, attribute_ref="attr_fixture_documented_oral@v1")
        assert facts and all(f["value"] is True and f["evidence_kind"] == "peer_reviewed" and f["unit"] is None for f in facts)
        context = {"qualification_policy": "qualification_first_v1", "constraints": [
            {"kind": "route", "hardness": "hard", "text": "oral administration"}]}
        (template,) = objective_templates(context)
        attr = dict(template["attribute"], attribute_id="attr_fixture_documented_oral", version=1)
        rule = dict(template["rule"], rule_id="rule_fixture_documented_oral", version=1)
        database = {"claim_id": "fixture_database_absence", "source_ref": "pinned_library", "admission_state": "admitted",
            "evidence_kind": "database_entry", "determination_basis": "measured", "value": False, "unit": None}
        def assess(items):
            return assessor.assess_cell(candidate={"candidate_id": identity}, attribute=attr, rule=rule, rule_set_ref="fixture_rules@v1",
                claims=items, resolved=True, qualification_policy=assessor.QUALIFICATION_POLICY)[0]
        missing, resolved = assess([database]), assess([database, *facts])
        assert missing["verdict"] == "unknown_missing" and resolved["verdict"] == "pass"
        report = {"status": "passed", "scope": "existing clinical route Boolean projection only; no whole-candidate qualification or ranking claim",
            "cache_manifest": cache.manifest(), "source_runs": SOURCE_RUNS, "source_connection": "mode=ro with application write guard",
            "candidate": identity, "database_only_verdict": missing["verdict"], "with_cached_clinical_verdict": resolved["verdict"],
            "derived_facts": facts, "sources": {f["source_ref"]: {"artifact_id": sources[f["source_ref"]]["artifact_id"],
                "sha256": sources[f["source_ref"]]["sha256"], "identifiers": sources[f["source_ref"]]["source"]["identifiers"]} for f in facts},
            "primary_store_writes": 0, "network_calls": 0, "model_calls": 0}
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "passed", "input_claims": len(claims), "projected_candidates": report["cache_manifest"]["projected_candidate_count"],
        "projected_facts": report["cache_manifest"]["projected_fact_count"], "candidate_facts": len(facts),
        "database_only": missing["verdict"], "with_cached_clinical": resolved["verdict"], "out": str(args.out.resolve())}))


if __name__ == "__main__":
    main()
