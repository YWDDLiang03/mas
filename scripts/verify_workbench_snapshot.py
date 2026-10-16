"""Read-only numerical audit of one completed, already exported snapshot.

Recomputes scores from the exact run's assessment records without calling the
production score/rank functions. No polling, models, cache rebuild or source writes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from urllib.parse import quote

from export_workbench_run import API, ExportError, PROJECT_ROOT, now, payload

sys.dont_write_bytecode = True
from mas.core import criteria
from mas.core.runtime import Core

DIRECT_BASES = {"measured", "derived", "curated", "asserted"}
LOGP_RULES = {"rule_lipophilicity-logp-optimal-band@v2", "rule_lipophilicity-logp@v2"}


def near(left, right):
    if left is None or right is None:
        return left is right
    return math.isclose(float(left), float(right), rel_tol=0, abs_tol=1e-12)


def direct(cell):
    return (cell["verdict"] in ("pass", "fail", "available") and bool(cell["value_source_claim_refs"])
            and not cell.get("tool_error_ref") and cell["determination_basis"] in DIRECT_BASES
            and cell["value_kind"] not in ("predicted", "simulated", "missing")
            and cell.get("direct_evidence", True) is not False)


def independent_scores(cells, rules, qualified, weights):
    """Average tied empirical percentiles, then an available-value weighted mean."""
    selected, suppressed = {}, {}
    for candidate, observations in cells.items():
        observed = {rules[c["rule_ref"]]["quantity_key"] for c in observations
                    if c["rule_kind"] == "preference" and direct(c)}
        chosen, held = [], []
        for cell in observations:
            if (cell["rule_kind"] == "preference" and not direct(cell)
                    and rules[cell["rule_ref"]]["quantity_key"] in observed):
                held.append(cell["rule_ref"])
            else:
                chosen.append(cell)
        selected[candidate], suppressed[candidate] = chosen, held
    percentiles = {}
    for ref, info in rules.items():
        if info["rule_kind"] != "preference" or info["predicate_form"] != "ordering":
            continue
        observations = {candidate: c["value"] for candidate in qualified for c in selected[candidate]
                        if c["rule_ref"] == ref and c["verdict"] in ("pass", "available")
                        and isinstance(c["value"], (int, float)) and not isinstance(c["value"], bool)}
        frequencies = Counter(observations.values())
        count = len(observations)
        ranks = {}
        for candidate, value in observations.items():
            worse = sum(n for other, n in frequencies.items()
                        if (other > value if info["direction"] == "lower_better" else other < value))
            ranks[candidate] = ((worse + (frequencies[value] - 1) / 2) / (count - 1)) if count > 1 else 1.0
        percentiles[ref] = ranks
    results = {}
    for candidate, observations in selected.items():
        preferences = [c for c in observations if c["rule_kind"] == "preference" and c["verdict"] != "inapplicable"]
        total = sum(weights.get(c["rule_ref"], 1.0) for c in preferences)
        direct_weight = sum(weights.get(c["rule_ref"], 1.0) for c in preferences if direct(c))
        numerator = denominator = 0.0
        participating = []
        for cell in preferences:
            ref = cell["rule_ref"]
            if ref in percentiles:
                desirability = percentiles[ref].get(candidate)
            else:
                desirability = float(cell["verdict"] == "pass") if cell["verdict"] in ("pass", "fail") else None
            if desirability is not None:
                weight = weights.get(ref, 1.0)
                numerator += weight * desirability
                denominator += weight
                participating.append(ref)
        results[candidate] = {"score": numerator / denominator if denominator and candidate in qualified else None,
                              "coverage": direct_weight / total if total else 0.0,
                              "selected_preference_entries": len(preferences), "participating_rule_refs": participating,
                              "participating_count": len(participating), "suppressed_rule_refs": suppressed[candidate]}
    return results


def decision_key(attribute, rule):
    return {"quantity": criteria.quantity_identity(attribute), "measurement_kind": attribute.get("measurement_kind"),
            "aggregation": attribute.get("aggregation", "consensus"), "aggregation_scope": attribute.get("aggregation_scope"),
            "rule_kind": rule["rule_kind"], "predicate_form": rule.get("predicate_form", "threshold"),
            "cutoff": rule.get("cutoff"), "direction": attribute.get("direction"),
            **{key: rule.get(key) for key in ("on_missing", "on_conflict", "on_inapplicable")}}


def source_snapshot(core, task_id, run_id, snapshot_id):
    row = core.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='leaderboard.snapshot_published' "
        "AND json_extract(body,'$.payload.snapshot_id')=?", (run_id, snapshot_id)).fetchone()
    if not row:
        raise ExportError("Requested source snapshot is not published by this run")
    event = json.loads(row[0])
    if event.get("visibility", "default") not in ("default", "public") or event["payload"]["task_id"] != task_id:
        raise ExportError("Requested publication is not a public snapshot of this task")
    return payload(core, event["payload"]["artifact_id"], {"leaderboard_snapshot"})


def source_cells(core, run_id):
    fields = ("candidate_ref", "rule_ref", "attribute_ref", "rule_kind", "verdict", "value", "value_kind",
              "determination_basis", "tool_error_ref", "not_assessed_reason", "unit", "assessment_id")
    columns = [f"json_extract(a.body,'$.payload.{field}')" for field in fields]
    columns += ["json_type(a.body,'$.payload.value')", "json_extract(a.body,'$.payload.value_source_claim_refs')",
                "json_extract(a.body,'$.payload.direct_evidence')", "json_extract(a.body,'$.payload.reuse.decision')"]
    query = ("SELECT " + ",".join(columns) + " FROM events e JOIN artifacts a "
             "ON a.artifact_id=json_extract(e.body,'$.payload.artifact_id') WHERE e.stream_id=? "
             "AND e.event_type='candidate.assessed' AND a.kind='assessment' "
             "AND coalesce(json_extract(e.body,'$.visibility'),'default') IN ('default','public') ORDER BY e.seq")
    latest, event_count = {}, 0
    for row in core.store.db.execute(query, (run_id,)):
        event_count += 1
        cell = dict(zip(fields, row))
        if row[len(fields)] in ("true", "false"):
            cell["value"] = bool(cell["value"])
        cell["value_source_claim_refs"] = json.loads(row[len(fields) + 1] or "[]")
        flag = row[len(fields) + 2]
        cell["direct_evidence"] = bool(flag) if flag is not None else None
        cell["reuse_decision"] = row[len(fields) + 3]
        latest[cell["rule_ref"], cell["candidate_ref"]] = cell
    result = defaultdict(list)
    for cell in latest.values():
        result[cell["candidate_ref"]].append(cell)
    return result, event_count


def logp_values(core, task_id, run_id, binding, cells):
    relevant = [c for observations in cells.values() for c in observations if c["rule_ref"] in LOGP_RULES]
    refs = {ref for c in relevant for ref in c["value_source_claim_refs"]}
    raw = {}
    streams = list(dict.fromkeys([task_id, run_id, *([binding["reuse_from_run_id"]] if binding.get("reuse_from_run_id") else [])]))
    query = ("SELECT json_extract(a.body,'$.payload.claim_id'),json_extract(a.body,'$.payload.value'),"
             "json_extract(a.body,'$.payload.value_low'),json_extract(a.body,'$.payload.value_high'),"
             "json_extract(a.body,'$.payload.unit') FROM events e JOIN artifacts a "
             "ON a.artifact_id=json_extract(e.body,'$.payload.artifact_id') WHERE e.stream_id=? "
             "AND e.event_type IN ('evidence.admitted','evidence.quarantined') AND a.kind='claim' "
             "AND json_extract(e.body,'$.payload.admission_state')='admitted' "
             "AND json_extract(e.body,'$.payload.claim_id') IN (SELECT value FROM json_each(?)) ORDER BY e.seq")
    if refs:
        for stream in streams:
            for row in core.store.db.execute(query, (stream, json.dumps(sorted(refs)))):
                value = tuple(row[1:])
                if row[0] in raw and raw[row[0]] != value:
                    raise ExportError("One used claim identity resolves to different original values")
                raw[row[0]] = value
    differences, checked = [], 0
    for cell in relevant:
        if not cell["value_source_claim_refs"]:
            continue
        values = []
        for ref in cell["value_source_claim_refs"]:
            if ref not in raw:
                raise ExportError(f"Used logP claim is not in the permitted task/run streams: {ref}")
            value, low, high, unit = raw[ref]
            if unit not in ("log units", "logP", "log-ratio"):
                raise ExportError(f"Unregistered raw logP coordinate in numerical audit: {unit}")
            values.extend([max(2 - float(v), 0.0, float(v) - 4) for v in ([value] if value is not None else [low, high])])
        expected = statistics.median(values)
        checked += 1
        if not near(cell["value"], expected) or cell["verdict"] != "available":
            differences.append({"candidate_ref": cell["candidate_ref"], "rule_ref": cell["rule_ref"],
                                "actual": cell["value"], "expected": expected, "verdict": cell["verdict"]})
    return {"cells": len(relevant), "value_bearing_cells_checked": checked, "original_claims": len(raw),
            "source_streams": streams, "formula": "median(max(2-x,0,x-4) for each used raw observation)",
            "differences": differences, "passed": not differences}


def verify(args):
    api = API(args.base_url)
    workflow = api.get("/workflows/" + quote(args.workflow, safe=""))
    if (workflow.get("state") != "completed" or workflow.get("snapshot_id") != args.snapshot
            or workflow.get("run_id") != args.run or workflow.get("task_id") != args.task):
        raise ExportError("Numerical audit requires the exact completed workflow/run/snapshot")
    if args.output.exists() or any(args.output.resolve().is_relative_to(p.resolve()) for p in (args.store, PROJECT_ROOT / "src", PROJECT_ROOT / "var/primary")):
        raise ExportError("Choose a new output folder outside source and primary/cache")
    exported = json.loads((args.export_dir / "snapshot.json").read_text(encoding="utf-8"))
    previous = json.loads((args.previous_export / "snapshot.json").read_text(encoding="utf-8"))
    checks = []
    def check(name, match, **detail):
        checks.append({"check": name, "match": bool(match), **detail})
    with Core.open(args.store, read_only=True) as core:
        snapshot = source_snapshot(core, args.task, args.run, args.snapshot)
        check("source_snapshot_equals_complete_export", snapshot == exported)
        original = source_snapshot(core, args.task, previous["run_id"], previous["snapshot_id"])
        check("snapshot1_source_immutable", original == previous)
        created = json.loads(core.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='run.created' ORDER BY seq LIMIT 1", (args.run,)).fetchone()[0])
        binding = payload(core, created["payload"]["binding_artifact_id"], {"run_binding"})
        frozen = criteria.rule_set(core, args.task, binding["rules@v"])
        rules, decision_groups = {}, defaultdict(list)
        for entry in frozen["entries"]:
            rule = criteria.load(core, entry["rule_ref"], args.task)
            attribute = criteria.load(core, entry["attribute_ref"], args.task)
            rules[entry["rule_ref"]] = {"rule_kind": rule["rule_kind"], "predicate_form": rule.get("predicate_form", "threshold"),
                "direction": attribute.get("direction"), "quantity_key": criteria.quantity_identity(attribute),
                "attribute_ref": entry["attribute_ref"]}
            decision_groups[json.dumps(decision_key(attribute, rule), sort_keys=True)].append(entry["rule_ref"])
        check("both_corrected_logp_versions_frozen", LOGP_RULES.issubset(rules))
        check("corrected_logp_quantity_identity_shared", len({rules[ref]["quantity_key"] for ref in LOGP_RULES}) == 1)
        revisions = json.loads((PROJECT_ROOT / "var/workbench-v2-acceptance/logp-coordinate-revisions.json").read_text(encoding="utf-8"))
        retained = []
        for revision in revisions["revisions"]:
            for label in ("old_rule", "old_attribute", "new_rule", "new_attribute"):
                record = revision[label]
                base = record.get("rule_id") or record["attribute_id"]
                ref = f"{base}@v{record['version']}"
                retained.append({"ref":ref,"equal":criteria.load(core, ref, args.task) == record})
        check("logp_v1_and_v2_source_versions_immutable", all(row["equal"] for row in retained), records=retained)
        cells, event_count = source_cells(core, args.run)
        entries = {row["candidate_ref"]: row for row in snapshot["candidate_entries"]}
        check("complete_cell_population", set(cells) == set(entries) and all(len(cs) == len(rules) for cs in cells.values()),
              candidate_count=len(cells), unique_cells=sum(map(len, cells.values())), assessment_events=event_count)
        check("cell_refs_exactly_match_freeze", all(c["rule_ref"] in rules and c["attribute_ref"] == rules[c["rule_ref"]]["attribute_ref"]
              and c["rule_kind"] == rules[c["rule_ref"]]["rule_kind"] for cs in cells.values() for c in cs))
        math_check = logp_values(core, args.task, args.run, binding, cells)
        check("corrected_coordinates_from_original_claim_values", math_check["passed"], **{k:v for k,v in math_check.items() if k != "passed"})
        task_runs = [row[0] for row in core.store.db.execute("SELECT stream_id FROM events WHERE event_type='run.created' "
            "AND json_extract(body,'$.payload.task_id')=?", (args.task,))]
        model_events = []
        for stream in [args.task, *task_runs]:
            for raw, in core.store.db.execute("SELECT body FROM events WHERE stream_id=? "
                    "AND event_type IN ('agent.started','agent.finished') AND recorded_at>=? AND recorded_at<=? ORDER BY seq",
                    (stream, workflow["started_at"], workflow["finished_at"])):
                event = json.loads(raw)
                if event.get("visibility", "default") in ("default", "public"):
                    model_events.append(event)
        source_finished, source_started = {}, set()
        for event in sorted(model_events, key=lambda e:(e["recorded_at"],e["stream_id"],e["seq"])):
            record = event["payload"]
            if event["event_type"] == "agent.started":
                source_started.add(record["request_id"])
            else:
                source_finished.setdefault(record["request_id"], record.get("known_cost_usd",record.get("cost_usd")))
    qualified = {ref for ref, row in entries.items() if row.get("qualified") is True}
    weights = (frozen.get("ordering_method") or {}).get("weight_vector") or {}
    recomputed = independent_scores(cells, rules, qualified, weights)
    score_differences = [{"candidate_ref": ref, "actual": row.get("preference_score"), "expected": recomputed[ref]["score"],
                          "actual_coverage": row.get("preference_coverage"), "expected_coverage": recomputed[ref]["coverage"]}
                         for ref, row in entries.items() if not near(row.get("preference_score"), recomputed[ref]["score"])
                         or not near(row.get("preference_coverage"), recomputed[ref]["coverage"])]
    check("independent_all_scores_and_direct_coverage", not score_differences, differences=score_differences)
    policy = snapshot["reporting_tuple"]
    ranked = [ref for ref, row in entries.items() if row["state"] in ("recommended", "provisional") and ref in qualified
              and recomputed[ref]["score"] is not None and recomputed[ref]["coverage"] >= policy["ranking_coverage_floor"]
              and (not policy.get("rank_requires_mandated_coverage", True) or row.get("clears_mandated_criteria") is not False)]
    state_order = {"recommended":0, "provisional":1, "unassessed":2, "rejected":3}
    ranked.sort(key=lambda ref: (-recomputed[ref]["score"], state_order[entries[ref]["state"]],
        -recomputed[ref]["coverage"], -(entries[ref].get("coverage") or 0), ref))
    positions = {ref:index for index,ref in enumerate(ranked,1)}
    rank_differences = [{"candidate_ref":ref,"actual":row.get("position"),"expected":positions.get(ref)}
                        for ref,row in entries.items() if row.get("position") != positions.get(ref)]
    check("independent_all_rank_positions", not rank_differences, differences=rank_differences)
    old_entries = {row["candidate_ref"]: row for row in previous["candidate_entries"]}
    check("qualification_records_unchanged_by_preference_repair", set(old_entries) == set(entries)
          and all(row.get("qualification") == old_entries[ref].get("qualification") for ref,row in entries.items()))
    api_rows, _ = api.pages("/tasks/" + quote(args.task,safe="") + "/candidates", snapshot=args.snapshot, status="all")
    with (args.export_dir / "candidates.csv").open(encoding="utf-8-sig",newline="") as stream:
        reader = csv.DictReader(stream)
        header, csv_rows = reader.fieldnames, list(reader)
    check("source_api_csv_3177_complete_ids", len(entries) == len(api_rows) == len(csv_rows) == 3177
          and Counter(entries.keys()) == Counter(row["candidate_ref"] for row in api_rows) == Counter(row["candidate_ref"] for row in csv_rows))
    mismatch = []
    for kind, rows in (("API",api_rows),("CSV",csv_rows)):
        for row in rows:
            original = entries[row["candidate_ref"]]
            position = int(row["position"]) if row.get("position") not in (None,"") else None
            score = float(row["score"]) if row.get("score") not in (None,"") else None
            if position != original.get("position") or not near(score,original.get("preference_score")):
                mismatch.append({"kind":kind,"candidate_ref":row["candidate_ref"]})
    check("source_api_csv_scores_and_positions", not mismatch, differences=mismatch)
    check("csv_rank_note_present", "rank_note" in header)
    for label, folder in (("snapshot1",args.previous_export),("snapshot2",args.export_dir)):
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        bad = [name for name,meta in manifest["files"].items() if hashlib.sha256((folder/name).read_bytes()).hexdigest() != meta["sha256"]
               or (folder/name).stat().st_size != meta["bytes"]]
        check(label + "_all_export_hashes_intact", not bad, mismatched_files=bad)
    accounting = json.loads((args.export_dir / "model-accounting.json").read_text(encoding="utf-8"))
    old_accounting = json.loads((args.previous_export / "model-accounting.json").read_text(encoding="utf-8"))
    check("prior_finished_cost_history_retained", {row["request_id"] for row in old_accounting["requests"]}.issubset(
          {row["request_id"] for row in accounting["requests"]}))
    current_cost_rows = {row["request_id"]:row for row in accounting["requests"]}
    check("prior_finished_cost_values_unchanged", all(all(current_cost_rows[row["request_id"]].get(field) == row.get(field)
          for field in ("known_cost_usd","cost_status","usage","usage_status","outcome")) for row in old_accounting["requests"]))
    check("export_costs_equal_exact_public_agent_finished_source", set(source_finished) == set(current_cost_rows)
          and all(near(cost,current_cost_rows[ref]["known_cost_usd"]) for ref,cost in source_finished.items()))
    check("unclosed_request_history_equals_source", source_started - set(source_finished)
          == {row["request_id"] for row in accounting["unfinished_model_requests"]})
    check("cost_finished_aggregates_not_attempts", near(sum(row["known_cost_usd"] or 0 for row in accounting["requests"]),
          accounting["total"]["known_cost_usd"]) and len({row["request_id"] for row in accounting["requests"]}) == len(accounting["requests"]))
    check("cost_budget_record_matches_known_total", near(accounting["total"]["known_cost_usd"],workflow["budget"]["used_usd"]))
    suruf = "cand_inchikey-TTZSNFLLYPYKIL-UHFFFAOYSA-N"
    report = {"created_at":now(),"task_id":args.task,"run_id":args.run,"snapshot_id":args.snapshot,
              "source_implementation":binding["implementation"],"source_read_only":True,"models_called":0,
              "prior_performance_evidence_reused":True,"http_benchmark_or_rebuild_repeated":False,
              "checks":checks,"passed":all(c["match"] for c in checks),
              "counts":{"enabled_execution_entries":len(rules),"independent_decisions":len(decision_groups),
                  "execution_by_role":dict(Counter(r["rule_kind"] for r in rules.values())),
                  "independent_by_role":dict(Counter(json.loads(key)["rule_kind"] for key in decision_groups)),
                  "participating_preference_values_histogram":dict(Counter(r["participating_count"] for r in recomputed.values())),
                  "qualified_participating_preference_values_histogram":dict(Counter(recomputed[ref]["participating_count"] for ref in qualified)),
                  "ranked_participating_preference_values_histogram":dict(Counter(recomputed[ref]["participating_count"] for ref in ranked)),
                  "ranked_participating_rule_ref_union_count":len({ref for candidate in ranked for ref in recomputed[candidate]["participating_rule_refs"]})},
              "decision_groups":[{"key":json.loads(key),"rule_refs":refs} for key,refs in decision_groups.items()],
              "source_qualification_counts":dict(Counter(row["qualification_state"] for row in entries.values())),
              "surufatinib":{"source_entry":entries.get(suruf),"independent_calculation":recomputed.get(suruf)},
              "accounting":{"total":accounting["total"],"previous_total":old_accounting["total"],
                  "unfinished_model_requests":accounting["unfinished_model_requests"],"by_stage_and_role":accounting["by_stage_and_role"]},
              "per_candidate_calculations":recomputed}
    args.output.mkdir(parents=True)
    (args.output / "numerical-check.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return {key:report[key] for key in ("passed","snapshot_id","counts","source_qualification_counts","accounting")}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ("task","workflow","run","snapshot"):
        parser.add_argument("--"+flag,required=True)
    parser.add_argument("--base-url",default="http://127.0.0.1:8770")
    parser.add_argument("--store",type=Path,default=PROJECT_ROOT/"var/primary/store")
    parser.add_argument("--export-dir",type=Path,required=True)
    parser.add_argument("--previous-export",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    try:
        result=verify(args)
    except (ExportError,OSError,ValueError,KeyError) as error:
        print(f"Numerical audit refused: {error}",file=sys.stderr)
        return 2
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
