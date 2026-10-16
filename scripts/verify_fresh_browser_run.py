"""Audit a newly completed browser study, without models, polling or source writes.

Uses this workflow's exact published snapshot and assessment cells. The independent
score calculation does not call the production scoring/ranking functions. Old
snapshots and fixed criterion IDs are not used as expected scientific results.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
from urllib.parse import quote

from export_workbench_run import API, ExportError, PROJECT_ROOT, accounting, now, selected_source
from verify_workbench_snapshot import decision_key, direct, independent_scores, near, source_cells
from mas.core import criteria
from mas.core.canonical import sha256_hex
from mas.core.runtime import Core

sys.dont_write_bytecode = True
SURUF = "cand_inchikey-TTZSNFLLYPYKIL-UHFFFAOYSA-N"
AUDIT_KINDS = {"preregistration", "config_layers", "existing_evidence_manifest", "existing_fact_manifest", "assessment", "claim"}


def payload(core, artifact_id, allowed):
    """Read only the exact additional public proof kinds used by this audit."""
    row=core.store.db.execute("SELECT kind FROM artifacts WHERE artifact_id=?",(artifact_id,)).fetchone()
    if row is None or row[0] not in allowed or row[0] not in AUDIT_KINDS:
        raise ExportError(f"Artifact is outside the numerical proof allowlist: {artifact_id}")
    envelope=core.artifacts.get(artifact_id)
    record=envelope.get("payload") or {}
    if envelope.get("visibility","default") not in ("default","public") or record.get("visibility","default") not in ("default","public"):
        raise ExportError(f"Artifact is outside public numerical proof: {artifact_id}")
    return record


def qualification_from_cells(cells, hard, required, verified, pending):
    by_ref = {cell["rule_ref"]: cell for cell in cells}
    applicable = {ref for ref in hard if by_ref.get(ref, {}).get("verdict") != "inapplicable"}
    observed = {ref for ref in applicable & verified if ref in by_ref and direct(by_ref[ref])}
    failed = {ref for ref in observed if by_ref[ref]["verdict"] == "fail"}
    passed = {ref for ref in observed if by_ref[ref]["verdict"] == "pass"}
    blocked = (applicable - passed - failed) | pending
    missing = {ref for ref in required if ref not in by_ref or not direct(by_ref[ref])}
    state = ("rejected" if failed else "not_ready" if not applicable or not applicable & verified
             else "pending" if blocked or missing else "qualified")
    return {"state": state, "qualified": state == "qualified", "failed_hard_rule_refs": sorted(failed),
            "blocking_hard_rule_refs": sorted(blocked), "missing_direct_required_rule_refs": sorted(missing),
            "applicable_hard_count": len(applicable), "verified_hard_count": len(applicable & verified),
            "hard_total": len(hard), "hard_passed": len(passed), "hard_failed": len(failed),
            "hard_blocked": len(blocked), "required_total": len(required),
            "required_direct_answered": len(required) - len(missing),
            "hard_direct_coverage": len(passed | failed) / len(applicable) if applicable else None,
            "required_direct_coverage": (len(required) - len(missing)) / len(required) if required else None}


def verify(args):
    if not math.isfinite(args.prior_known_usd) or args.prior_known_usd < 0:
        raise ExportError("prior-known-usd must be a finite nonnegative recorded amount")
    api = API(args.base_url)
    workflow = api.get("/workflows/" + quote(args.workflow, safe=""))
    if workflow.get("state") != "completed" or not workflow.get("snapshot_id") or not workflow.get("task_id"):
        raise ExportError("Audit requires a completed workflow with its own published snapshot; nothing was written")
    if args.output.exists() or any(args.output.resolve().is_relative_to(path.resolve())
                                 for path in (args.store, PROJECT_ROOT / "src", PROJECT_ROOT / "var/primary")):
        raise ExportError("Choose a new audit folder outside source and primary/cache")
    task_id, run_id, snapshot_id = (workflow[key] for key in ("task_id", "run_id", "snapshot_id"))
    source = selected_source(args.store, workflow)
    snapshot, context = source["snapshot"], source["task"]
    checks = []
    def check(name, match, **details):
        checks.append({"check": name, "match": bool(match), **details})
    exported = json.loads((args.export_dir / "snapshot.json").read_text(encoding="utf-8"))
    check("new_task_run_snapshot_identity", snapshot["task_id"] == task_id and snapshot["run_id"] == run_id
          and snapshot["snapshot_id"] == snapshot_id)
    check("source_snapshot_equals_export", snapshot == exported)
    binding = source["run_bindings"][run_id]
    check("qualification_policy", snapshot.get("qualification_policy") == "qualification_first_v1"
          and binding.get("qualification_policy") == "qualification_first_v1")
    check("saved_evidence_staged_mode", binding.get("evidence_mode") == "existing_only"
          and binding.get("evaluation_mode") == "staged")
    rules, decisions, hard, verified, mandated = {}, defaultdict(list), set(), set(), set()
    descriptor_rules, source_proofs = {}, {}
    execution_problems = []
    with Core.open(args.store, read_only=True) as core:
        frozen = criteria.rule_set(core, task_id, binding["rules@v"])
        for entry in frozen["entries"]:
            rule, attribute = (criteria.load(core, entry[key], task_id) for key in ("rule_ref", "attribute_ref"))
            ref = entry["rule_ref"]
            rules[ref] = {"attribute_ref": entry["attribute_ref"], "rule_kind": rule["rule_kind"],
                          "predicate_form": rule.get("predicate_form", "threshold"),
                          "direction": attribute.get("direction"), "quantity_key": criteria.quantity_identity(attribute),
                          "unit":attribute.get("unit"),"routes":criteria.evidence_routes(attribute),
                          "acceptable_value_sources":attribute.get("acceptable_value_sources"),
                          "acceptable_determination_bases":attribute.get("acceptable_determination_bases")}
            for route in criteria.evidence_routes(attribute):
                if route.get("capability") == "property_estimate" and route.get("question_kind") == "admet_computed_property":
                    descriptor_rules[ref] = (route.get("parameters") or {}).get("endpoint")
            problems=criteria.preference_execution_problems(attribute,rule)
            if problems:
                execution_problems.append({"rule_ref":ref,"attribute_ref":entry["attribute_ref"],"problems":problems})
            decisions[json.dumps(decision_key(attribute, rule), sort_keys=True)].append(ref)
            if rule["rule_kind"] == "hard_exclusion":
                hard.add(ref)
                if not entry.get("disputed") and entry.get("authority") in ("machine_adjudication", "human_scientific_approval"):
                    verified.add(ref)
            if criteria.is_task_mandated(attribute) and rule["rule_kind"] != "hard_exclusion":
                mandated.add(ref)
        profile = payload(core, binding["measurement_profile_ref"], {"preregistration"})
        check("all_frozen_preferences_meet_execution_contract",not execution_problems,findings=execution_problems)
        scoring = profile["policy"]["scoring_policy"]
        proof = scoring.get("required_binding_check") or {}
        if not proof:
            raise ExportError("This audit requires the new profile's explicit required-scope binding proof")
        required = {row["rule_ref"] for row in proof.get("scope_bindings", [])}
        pending = {ref for ref in frozen.get("pending", []) if criteria.load(core, ref, task_id)["rule_kind"] == "hard_exclusion"}
        cells, cell_events = source_cells(core, run_id)
        if args.verify_saved_fact_projection:
            evidence_manifest=binding.get("evidence_manifest") or {}
            closure=evidence_manifest.get("tool_fact_source_manifest") or {}
            closure_body=dict(closure)
            closure_hash=closure_body.pop("sha256",None)
            check("terminal_tool_source_manifest_hash",bool(closure_hash) and sha256_hex(closure_body)==closure_hash)
            source_rows=closure.get("source_runs") or []
            source_pins={row["run_id"]:row["pinned_seq"] for row in source_rows}
            replay=binding.get("tool_replay") or {}
            replay_body=dict(replay)
            replay_hash=replay_body.pop("manifest_digest",None)
            check("terminal_tool_replay_manifest_and_pins",bool(source_rows) and replay.get("policy_version")==3
                  and replay.get("allow_terminal_sources") is True and replay.get("reuses_decisions") is False
                  and replay.get("source_pins")==source_pins and sha256_hex(replay_body)==replay_hash)
            invalid_sources=[]
            for row in source_rows:
                artifact=core.store.db.execute("SELECT kind,body FROM artifacts WHERE artifact_id=?",
                                               (row["binding_artifact_id"],)).fetchone()
                terminal=core.store.db.execute("SELECT body FROM events WHERE stream_id=? AND seq=?",
                                               (row["run_id"],row["terminal_seq"])).fetchone()
                record=json.loads(terminal[0]) if terminal else {}
                if (not artifact or artifact[0]!="run_binding"
                        or sha256_hex(json.loads(artifact[1])["payload"])!=row["binding_sha256"]
                        or record.get("event_id")!=row["terminal_event_id"]
                        or record.get("state_to") not in ("completed","cancelled","failed","unresolved")
                        or row["terminal_seq"]>row["pinned_seq"]):
                    invalid_sources.append(row["run_id"])
            check("all_bound_tool_sources_are_exact_public_terminal_pins",not invalid_sources,differences=invalid_sources)
            projections=evidence_manifest.get("cached_tool_projections") or []
            invalid_projections=[]
            for projection in projections:
                saved=projection.get("manifest") or {}
                content=dict(saved)
                digest=content.pop("manifest_digest",None)
                if (not digest or sha256_hex(content)!=digest
                        or sha256_hex(saved.get("entries") or [])!=saved.get("entries_digest")
                        or saved.get("universe_sha256")!=evidence_manifest.get("library_sha256")
                        or saved.get("covered_candidates")!=3177 or saved.get("fresh_prediction") is not False):
                    invalid_projections.append(projection.get("tool_id"))
            check("saved_panel_projection_manifests_are_pinned_and_complete",len(projections)==2 and not invalid_projections,
                  differences=invalid_projections)
            expected_endpoints={"logP","BRENK_alert","NIH_alert","PAINS_alert"}
            check("exact_four_descriptor_preferences_have_correct_new_contract",len(descriptor_rules)==4
                  and set(descriptor_rules.values())==expected_endpoints
                  and all(rules[ref]["rule_kind"]=="preference"
                          and rules[ref]["acceptable_value_sources"]==["database_entry"]
                          and rules[ref]["acceptable_determination_bases"]==["derived"] for ref in descriptor_rules))
            wrong_basis=[]
            basis_counts=defaultdict(Counter)
            for observations in cells.values():
                for cell in observations:
                    if cell["rule_ref"] in descriptor_rules:
                        endpoint=descriptor_rules[cell["rule_ref"]]
                        basis_counts[endpoint][str(cell.get("determination_basis"))]+=1
                        if not direct(cell) or cell.get("value_kind")!="derived" or cell.get("determination_basis")!="derived":
                            wrong_basis.append((cell["candidate_ref"],cell["rule_ref"]))
            check("all_four_saved_descriptors_are_derived_direct_cells",not wrong_basis
                  and all(sum(basis_counts[endpoint].values())==3177 for endpoint in expected_endpoints),
                  differences=wrong_basis)
            check("five_task_target_anchors_preserved",len(mandated)==len(required)==5 and mandated==required)
            source_proofs={"tool_fact_source_manifest":closure,"tool_replay":replay,
                           "cached_projection_manifests":projections,"descriptor_rules":descriptor_rules,
                           "descriptor_cell_basis_counts":{key:dict(value) for key,value in basis_counts.items()}}
        if args.prior_snapshot_baseline:
            baseline=json.loads(args.prior_snapshot_baseline.read_text(encoding="utf-8"))
            old=core.store.db.execute("SELECT kind,body,sha256 FROM artifacts WHERE artifact_id=?",
                                      (baseline["snapshot_artifact_id"],)).fetchone()
            check("previous_snapshot1_source_and_exports_unchanged",baseline["task_id"]==task_id
                  and baseline["snapshot_id"]!=snapshot_id and old is not None and old[0]=="leaderboard_snapshot"
                  and old[2]==baseline["snapshot_envelope_sha256"] and sha256_hex(json.loads(old[1]))==old[2]
                  and all(hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest()==row["sha256"]
                          for row in baseline["files"].values()))
            source_proofs["previous_snapshot1_preservation_baseline"]=baseline
        generations, generation_settings = [], []
        for source_run, source_binding in source["run_bindings"].items():
            if source_binding.get("operation") != "derive_existing_evidence":
                continue
            manifest = payload(core, source_binding["evidence_manifest_ref"], {"existing_evidence_manifest"})
            layers = payload(core, source_binding["settings"]["layers_artifact_id"], {"config_layers"})
            values = {row["key"]:row["value"] for row in layers["settings"] if row["key"] in (
                "search.volume","textbook.volume","assess.workers","criteria.inner_iterations","budget.usd_max","rank.coverage_floor")}
            generation_settings.append({"run_id":source_run,"values":values,"roles":source_binding.get("role_bindings")})
            generations.append({"run_id": source_run, "initial_registry_count": source_binding.get("initial_registry_count"),
                "initial_pool_count": source_binding.get("initial_pool_count"),
                "bound_at":source_binding.get("bound_at"),"task_context_ref":source_binding.get("task_context_id@v"),
                "copies_existing_criteria": source_binding.get("copies_existing_criteria"),
                "source_task_id": source_binding.get("source_task_id"), "inner_iterations": source_binding.get("inner_iterations"),
                "implementation":source_binding.get("implementation"),"continues_run_id":source_binding.get("continues_run_id"),
                "inherited_stage_refs":source_binding.get("inherited_stage_refs"),
                "inherited_proposal_slice_refs":source_binding.get("inherited_proposal_slice_refs"),
                "proposal_claim_count": len(manifest["claims"]), "manifest_ref": source_binding["evidence_manifest_ref"],
                "claim_rows_hash": sha256_hex(manifest["claims"]), "omissions": dict(Counter(row["reason"] for row in manifest["omitted"]))})
        generations.sort(key=lambda row:(row.get("bound_at") or "",row["run_id"]))
        roots=[row for row in generations if row.get("continues_run_id") is None]
        generation_ids={row["run_id"] for row in generations}
        check("fresh_zero_criteria_start", len(roots) == 1 and roots[0]["initial_registry_count"] == 0
              and roots[0]["initial_pool_count"] == 0 and all(g["copies_existing_criteria"] is False for g in generations))
        check("versioned_generation_continuations_stay_in_this_new_task", all(
            g.get("task_context_ref","").split("@v")[0] == task_id
            and (g.get("continues_run_id") is None or g["continues_run_id"] in generation_ids)
            for g in generations))
        check("versioned_generations_keep_fixed_proposal_claims", bool(roots) and all(
            g["claim_rows_hash"] == roots[0]["claim_rows_hash"] for g in generations))
        check("recorded_mid_profile", bool(generation_settings) and all(row["values"].get("search.volume") == "mid"
              and row["values"].get("textbook.volume") == "mid" and row["values"].get("assess.workers") == 4
              and row["values"].get("criteria.inner_iterations") == 3 for row in generation_settings))
        fact = payload(core, context["evidence_fact_manifest_ref"], {"existing_fact_manifest"})
        check("library_matches_pinned_factbank", fact["candidate_library_sha256"] == binding["evidence_manifest"]["library_sha256"])
        suruf_cells = {}
        for raw, in core.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='candidate.assessed' "
                "AND json_extract(body,'$.payload.candidate_ref')=? ORDER BY seq", (run_id,SURUF)):
            event=json.loads(raw)
            if event.get("visibility","default") in ("default","public"):
                cell=payload(core,event["payload"]["artifact_id"],{"assessment"})
                suruf_cells[cell["rule_ref"]]=cell
        used_refs={ref for cell in suruf_cells.values() for ref in cell.get("value_source_claim_refs") or []}
        claim_provenance={}
        for stream in (task_id,run_id):
            for raw, in core.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='evidence.admitted' "
                    "AND json_extract(body,'$.payload.claim_id') IN (SELECT value FROM json_each(?)) ORDER BY seq",
                    (stream,json.dumps(sorted(used_refs)))):
                event=json.loads(raw)
                if event.get("visibility","default") in ("default","public"):
                    artifact=event["payload"]["artifact_id"]
                    claim=payload(core,artifact,{"claim"})
                    claim_provenance[claim["claim_id"]]={"artifact_id":artifact,"payload_sha256":sha256_hex(claim),"claim":claim}
        check("suruf_used_claims_present_in_public_new_task_or_run", used_refs <= set(claim_provenance),
              missing_refs=sorted(used_refs-set(claim_provenance)))
    entries = {row["candidate_ref"]: row for row in snapshot["candidate_entries"]}
    check("complete_3177_candidate_population", len(entries) == 3177 and len(entries) == len(snapshot["candidate_entries"]))
    check("all_frozen_cells_recorded", set(cells) == set(entries) and all(len(observations) == len(rules) for observations in cells.values()),
          unique_cells=sum(map(len, cells.values())), source_assessment_events=cell_events)
    check("all_cell_refs_match_exact_freeze", all(c["rule_ref"] in rules and c["attribute_ref"] == rules[c["rule_ref"]]["attribute_ref"]
          and c["rule_kind"] == rules[c["rule_ref"]]["rule_kind"] for observations in cells.values() for c in observations))
    qualifications = {ref: qualification_from_cells(observations, hard, required, verified, pending) for ref, observations in cells.items()}
    q_differences = [{"candidate_ref": ref, "actual": row.get("qualification"), "expected": qualifications[ref]}
                     for ref, row in entries.items() if row.get("qualification") != qualifications[ref]]
    check("independent_all_qualification_records", not q_differences, differences=q_differences)
    qualified = {ref for ref, value in qualifications.items() if value["qualified"]}
    calculated = independent_scores(cells, rules, qualified, (frozen.get("ordering_method") or {}).get("weight_vector") or {})
    mismatches = [{"candidate_ref": ref, "actual_score": row.get("preference_score"), "calculated": calculated[ref]}
                  for ref, row in entries.items() if not near(row.get("preference_score"), calculated[ref]["score"])
                  or not near(row.get("preference_coverage"), calculated[ref]["coverage"])]
    check("independent_all_scores_and_direct_coverage", not mismatches, differences=mismatches)
    own = {ref: sum(direct(cell) for cell in observations if cell["rule_ref"] in mandated) / len(mandated)
           if mandated else None for ref, observations in cells.items()}
    check("independent_task_anchor_direct_coverage", all(near(row.get("mandated_coverage"), own[ref]) for ref, row in entries.items()))
    ranked = [ref for ref, row in entries.items() if ref in qualified and row["state"] in ("recommended", "provisional")
              and calculated[ref]["score"] is not None and calculated[ref]["coverage"] >= scoring["ranking_coverage_floor"]
              and (not scoring["rank_requires_mandated_coverage"] or own[ref] is None
                   or own[ref] >= scoring["eligibility_mandated_coverage_floor"])]
    states = {"recommended": 0, "provisional": 1, "unassessed": 2, "rejected": 3}
    ranked.sort(key=lambda ref: (-calculated[ref]["score"], states[entries[ref]["state"]],
                                -calculated[ref]["coverage"], -(entries[ref].get("coverage") or 0), ref))
    positions = {ref: index for index, ref in enumerate(ranked, 1)}
    check("independent_all_rank_positions", all(row.get("position") == positions.get(ref) for ref, row in entries.items()))
    api_rows, _ = api.pages("/tasks/" + quote(task_id, safe="") + "/candidates", snapshot=snapshot_id, status="all")
    with (args.export_dir / "candidates.csv").open(encoding="utf-8-sig", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    expected = Counter(entries.keys())
    check("source_api_csv_all_3177_ids", len(api_rows) == len(csv_rows) == 3177
          and Counter(row["candidate_ref"] for row in api_rows) == expected == Counter(row["candidate_ref"] for row in csv_rows))
    for label, rows in (("api", api_rows), ("csv", csv_rows)):
        bad = []
        for row in rows:
            entry = entries.get(row["candidate_ref"])
            position = int(row["position"]) if row.get("position") not in (None, "") else None
            score = float(row["score"]) if row.get("score") not in (None, "") else None
            coverage = float(row["preference_coverage"]) if row.get("preference_coverage") not in (None, "") else None
            raw_qualification = entry.get("qualification_state") if entry else None
            expected_qualification = ("pending" if raw_qualification in ("not_ready","insufficient_evidence","unknown")
                                      else raw_qualification)
            if (entry is None or position != entry.get("position") or not near(score, entry.get("preference_score"))
                    or not near(coverage,entry.get("preference_coverage")) or row.get("qualification") != expected_qualification):
                bad.append(row["candidate_ref"])
        check("source_" + label + "_scores_positions_qualification_coverage", not bad, differences=bad)
    manifest = json.loads((args.export_dir / "manifest.json").read_text(encoding="utf-8"))
    check("export_file_hashes", all(hashlib.sha256((args.export_dir / name).read_bytes()).hexdigest() == meta["sha256"]
          for name, meta in manifest["files"].items()))
    costs = accounting(workflow, source["model_events"])
    exported_costs = json.loads((args.export_dir / "model-accounting.json").read_text(encoding="utf-8"))
    check("source_finished_costs_equal_export", costs == exported_costs)
    check("source_finished_costs_equal_workflow", near(costs["total"]["known_cost_usd"], workflow["budget"]["used_usd"]))
    check("no_unfinished_model_requests", not costs["unfinished_model_requests"])
    known = costs["total"]["known_cost_usd"]
    check("cumulative_known_cost_within_10_usd", known is not None and args.prior_known_usd + known <= 10.0)
    result = {"created_at": now(), "workflow_id": args.workflow, "task_id": task_id, "run_id": run_id,
              "snapshot_id": snapshot_id, "source_open_mode": "read_only", "models_called": 0,
              "source_implementation": binding.get("implementation"), "checks": checks,
              "engineering_passed": all(row["match"] for row in checks),
              "scientific_target_met": SURUF in qualified and positions.get(SURUF) is not None and positions[SURUF] <= 5,
              "counts": {"candidates": len(entries), "qualified": len(qualified), "ranked": len(ranked),
                         "execution_entries": len(rules), "independent_decisions": len(decisions),
                         "independent_core_decisions":sum(json.loads(key)["rule_kind"]!="exploratory_consideration" for key in decisions),
                         "independent_context_decisions":sum(json.loads(key)["rule_kind"]=="exploratory_consideration" for key in decisions),
                         "ranking_preference_entries":sum(row["rule_kind"]=="preference" for row in rules.values()),
                         "derived_descriptor_entries":len(descriptor_rules),
                         "qualification_states": dict(Counter(row["state"] for row in qualifications.values()))},
              "surufatinib": {"source_entry": entries.get(SURUF), "independent_calculation": calculated.get(SURUF),
                              "independent_qualification": qualifications.get(SURUF), "independent_rank": positions.get(SURUF),
                              "source_assessments":list(suruf_cells.values()),"used_claim_provenance":claim_provenance},
              "generations": generations,"generation_settings":generation_settings,
              "factbank": {"claims": len(fact["claims"]), "sources": len(fact["source_records"]),
                  "claim_rows_hash": sha256_hex(fact["claims"]), "source_records_hash": sha256_hex(fact["source_records"]),
                  "library_sha256": fact["candidate_library_sha256"]},
              "reference_disclosure": context.get("seed_candidates"), "accounting": costs,
              "cumulative_known_usd": args.prior_known_usd + known if known is not None else None,
              "prior_known_usd": args.prior_known_usd,
              "decision_groups": [{"key": json.loads(key), "rule_refs": refs} for key, refs in decisions.items()],
              "saved_fact_projection_proofs":source_proofs,
              "per_candidate_calculations": calculated}
    args.output.mkdir(parents=True)
    (args.output / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {key: result[key] for key in ("engineering_passed", "scientific_target_met", "task_id", "snapshot_id", "counts", "cumulative_known_usd")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8769")
    parser.add_argument("--store", type=Path, default=PROJECT_ROOT / "var/primary/store")
    parser.add_argument("--export-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prior-known-usd", type=float, required=True)
    parser.add_argument("--verify-saved-fact-projection", action="store_true",
                        help="Verify fixed terminal-tool sources, complete saved panel and four corrected derived descriptors")
    parser.add_argument("--prior-snapshot-baseline", type=Path,
                        help="Verify the prior snapshot source artifact and exported files remain unchanged")
    args = parser.parse_args()
    try:
        result = verify(args)
    except (ExportError, OSError, ValueError, KeyError) as error:
        print(f"Audit refused: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["engineering_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
