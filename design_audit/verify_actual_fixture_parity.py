"""Bounded mode-consistency check over real saved target facts and the literal oral task gate.

This builds two temporary engineering runs. It is NOT a replay of the original
rank-only instrument or a validation of the fresh GUI generation workflow.
No source leaderboard, case, recovery artifact, network or model is read/called.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
from pathlib import Path
from unittest.mock import patch

from mas.adapters.drug.registration import objective_templates
from mas.adapters.drug.universe import UniverseRecordField
from mas.core import adjudication, assessor, criteria, leaderboard, measurement, task
from mas.core.broker import Broker
from mas.core.canonical import sha256_hex
from mas.core.clock import utc_now
from mas.core.controller import RunController
from mas.core.journal import actor
from mas.core.runtime import Core

IMPORTER = actor("system", "actual-evidence-parity-fixture", "verification_fixture")
TEMPLATE = actor("system", "actual-evidence-task-template", "adapter_template")
ALLOWED = {"run_binding", "task_context", "rule_set", "attribute", "rule", "assessment", "identity_record", "claim"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def artifact(core, ref, kind):
    require(kind in ALLOWED, f"source artifact kind is not allowed: {kind}")
    row = core.store.db.execute("SELECT kind,body,sha256 FROM artifacts WHERE artifact_id=?", (ref,)).fetchone()
    require(row is not None and row[0] == kind, f"{ref} is not {kind}")
    envelope = json.loads(row[1])
    require(sha256_hex(envelope) == row[2], f"source artifact hash failed: {ref}")
    return envelope["payload"], {"artifact_id": ref, "sha256": row[2], "kind": kind}


def context_record(core, ref):
    tid, version = ref.rsplit("@v", 1)
    row = core.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='task.version_recorded' "
        "AND json_extract(body,'$.payload.version')=? ORDER BY seq LIMIT 1", (tid, int(version))).fetchone()
    require(row is not None, f"source task context is absent: {ref}")
    event = json.loads(row[0])
    record, provenance = artifact(core, event["payload"]["artifact_id"], "task_context")
    return record, dict(provenance, stream_id=tid, seq=event["seq"], event_id=event["event_id"])


def criterion(core, tid, ref, kind):
    base, version = ref.rsplit("@v", 1)
    row = core.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='criterion.version_proposed' "
        "AND json_extract(body,'$.payload.kind')=? AND json_extract(body,'$.payload.id')=? "
        "AND json_extract(body,'$.payload.version')=? ORDER BY seq DESC LIMIT 1", (tid, kind, base, int(version))).fetchone()
    require(row is not None, f"source criterion is absent: {ref}")
    event = json.loads(row[0])
    record, provenance = artifact(core, event["payload"]["artifact_id"], kind)
    return record, dict(provenance, ref=ref, stream_id=tid, seq=event["seq"], event_id=event["event_id"])


def cell_records(core, run, candidate, refs):
    marks = ",".join("?" for _ in refs)
    rows = core.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='candidate.assessed' "
        "AND json_extract(body,'$.payload.candidate_ref')=? AND json_extract(body,'$.payload.rule_ref') IN (" + marks + ") ORDER BY seq",
        (run, candidate, *refs))
    result = {}
    for (body,) in rows:
        event = json.loads(body)
        cell, provenance = artifact(core, event["payload"]["artifact_id"], "assessment")
        result[cell["rule_ref"]] = (cell, dict(provenance, event_id=event["event_id"], seq=event["seq"]))
    require(len(result) == len(refs), f"candidate lacks source cells: {candidate}")
    return result


def backend_hashes():
    import mas.core.assessor
    root = Path(mas.core.assessor.__file__).parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in
            ("controller.py", "assessor.py", "criteria.py", "adjudication.py", "leaderboard.py", "measurement.py")}


def verify(source, source_run, universe_path):
    require(source.store.read_only, "source connection is not read-only")
    first = source.journal.replay(source_run, 1, 1)[0]
    binding, binding_prov = artifact(source, first.payload["binding_artifact_id"], "run_binding")
    require(binding.get("run_purpose", "sweep") == "sweep", "source is not a screening run")
    last = source.store.db.execute("SELECT seq,body FROM events WHERE stream_id=? ORDER BY seq DESC LIMIT 1", (source_run,)).fetchone()
    require(json.loads(last[1])["event_type"] == "run.completed", "source must be completed")
    source_seq = last[0]
    context, context_prov = context_record(source, binding["task_context_id@v"])
    tid = context["task_context_id"]
    approved = source.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='criterion.version_approved' "
        "AND json_extract(body,'$.payload.rule_set_ref')=? ORDER BY seq DESC LIMIT 1", (tid, binding["rules@v"])).fetchone()
    require(approved is not None, "source frozen rule set is absent")
    frozen, frozen_prov = artifact(source, json.loads(approved[0])["payload"]["artifact_id"], "rule_set")
    selected_rules = []
    for entry in frozen["entries"]:
        attr, ap = criterion(source, tid, entry["attribute_ref"], "attribute")
        rule, rp = criterion(source, tid, entry["rule_ref"], "rule")
        if criteria.is_required_scope(attr, context) and rule["rule_kind"] == "preference":
            require(rule.get("predicate_form") == "ordering" and rule.get("cutoff") is None, "fixture must not invent target thresholds")
            selected_rules.append((entry, attr, rule, ap, rp))
    require(selected_rules, "source has no task-bound target ordering criteria")
    refs = [e[0]["rule_ref"] for e in selected_rules]
    raw_library = universe_path.read_bytes()
    library_hash = hashlib.sha256(raw_library).hexdigest()
    local = UniverseRecordField(universe_path)
    members = json.loads(raw_library)["universe"]
    marks = ",".join("?" for _ in refs)
    rows = source.store.db.execute("SELECT json_extract(body,'$.payload.candidate_ref'),count(*) FROM events "
        "WHERE stream_id=? AND event_type='candidate.assessed' AND json_extract(body,'$.payload.rule_ref') IN (" + marks + ") "
        "AND json_extract(body,'$.payload.verdict') IN ('pass','fail','available') GROUP BY 1", (source_run, *refs))
    available = dict(rows)
    groups = {"known_oral": [], "known_non_oral": [], "unknown": []}
    for member in members:
        response = local.invoke("record_field", {"identifier": member["inchikey"], "field": "oral"})
        value = response.values[0]["value"] if response.values else None
        group = "known_oral" if value is True else "known_non_oral" if value is False else "unknown"
        candidate = "cand_inchikey-" + member["inchikey"]
        groups[group].append((available.get(candidate, 0), candidate, member, response))
    chosen = []
    for group, needed in (("known_oral", 2), ("known_non_oral", 1), ("unknown", 1)):
        count = 0
        for n, candidate, member, response in sorted(groups[group], key=lambda item: (-item[0], item[1]))[:32]:
            cells = cell_records(source, source_run, candidate, refs)
            if group == "known_oral" and not all(assessor.direct_evidence(cell) for cell, _ in cells.values()):
                continue
            chosen.append({"group": group, "candidate": candidate, "member": member, "oral": response, "cells": cells})
            count += 1
            if count == needed:
                break
        require(count == needed, f"insufficient genuine fixture candidates in {group}")
    all_claim_ids = {ref for row in chosen for cell, _ in row["cells"].values() for ref in cell["value_source_claim_refs"]}
    require(len(all_claim_ids) <= 2000, "fixture claim bound exceeded")
    claims = {}
    ordered_ids = sorted(all_claim_ids)
    for start in range(0, len(ordered_ids), 400):
        ids = ordered_ids[start:start + 400]
        claim_rows = source.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='evidence.admitted' "
            "AND json_extract(body,'$.payload.claim_id') IN (" + ",".join("?" for _ in ids) + ")", (source_run, *ids))
        for (body,) in claim_rows:
            event = json.loads(body)
            value, provenance = artifact(source, event["payload"]["artifact_id"], "claim")
            require(value["admission_state"] == "admitted", "source claim is not admitted")
            claims[value["claim_id"]] = (value, dict(provenance, event_id=event["event_id"], seq=event["seq"]))
    require(set(claims) == all_claim_ids, "source claim references do not fully resolve on the named source run")
    implementations = backend_hashes()
    with tempfile.TemporaryDirectory(prefix="mas_actual_mode_parity_") as folder:
        temp_root = Path(folder) / "store"
        require(not temp_root.resolve().is_relative_to(source.store.root.resolve()), "temporary fixture would enter the primary store")
        with Core.open(temp_root) as temp:
            contexts = {attr.get("derived_from", {}).get("task_context") for _, attr, _, _, _ in selected_rules}
            for ref in sorted(contexts - {None}):
                record, provenance = context_record(source, ref)
                aid = temp.artifacts.put("task_context", record)
                temp.journal.append(record["task_context_id"], "task.version_recorded", actor=IMPORTER,
                    payload={"version": record["version"], "artifact_id": aid, "fixture_source": provenance})
            spec = {k: v for k, v in context.items() if k not in ("task_context_id", "version", "case_ref", "supersedes", "created_by", "unknowns", "verified_supplement_refs")}
            spec.update(candidate_universe={"kind": "enumerated_set", "members": [r["member"]["inchikey"] for r in chosen]},
                        seed_candidates=[], group_id="actual_evidence_engineering_fixture")
            fixture_task, _ = task.record_version(temp, spec, by=IMPORTER)
            for entry, attr, rule, ap, rp in selected_rules:
                for kind, record, provenance in (("attribute", attr, ap), ("rule", rule, rp)):
                    aid = temp.artifacts.put(kind, record)
                    temp.journal.append(fixture_task, "criterion.version_proposed", actor=IMPORTER,
                        payload={"kind": kind, "id": record[kind + "_id"], "version": record["version"], "artifact_id": aid,
                                 "fixture_source": provenance})
            hard = [item for item in objective_templates(task.get(temp, fixture_task)) if item["rule"]["rule_kind"] == "hard_exclusion"
                    and item["attribute"].get("evidence_request", {}).get("parameters", {}).get("field") == "oral"]
            require(len(hard) == 1, "source task must explicitly state one supported oral hard constraint")
            literal = hard[0]
            oral_attr, oral_rule = criteria.propose(temp, fixture_task, dict(literal["attribute"],
                derived_from={"task_context": f"{fixture_task}@v1", "field": literal["source_field"]}), literal["rule"], by=TEMPLATE)
            decisions = adjudication.adjudicate_open(temp, fixture_task, qualification_policy=assessor.QUALIFICATION_POLICY)
            require(any(d.get("rule_ref_after") == oral_rule and d.get("resolution") == "approve" for d in decisions),
                    "literal task constraint was not deterministically confirmed; no model fallback is permitted")
            criteria.confirm_rule_set(temp, fixture_task, by=IMPORTER, allow_pending=True)
            fixture_claims = {}
            identities = []
            for row in chosen:
                candidate = row["candidate"]
                event = source.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='identity.resolved' "
                    "AND json_extract(body,'$.payload.candidate_id')=? ORDER BY seq DESC LIMIT 1", (source_run, candidate)).fetchone()
                require(event is not None, "source candidate identity is absent")
                original_identity, _ = artifact(source, json.loads(event[0])["payload"]["artifact_id"], "identity_record")
                identities.append(original_identity)
                for ref, (cell, _) in row["cells"].items():
                    fixture_claims[candidate, ref] = [claims[c][0] for c in cell["value_source_claim_refs"]]
                values = row["oral"].values
                oral_claims = []
                if values:
                    claim = {"claim_id": "fixture_oral_" + sha256_hex(candidate)[:12], "candidate_ref": candidate,
                        "attribute_ref": oral_attr, "source_ref": "src_fixture_universe_" + library_hash[:12],
                        "evidence_kind": "database_entry", "determination_basis": "measured", "value": values[0]["value"],
                        "unit": None, "admission_state": "admitted", "location": {"location_kind": "database_record",
                        "locator_value": values[0]["source_record_ref"]}, "fixture_origin": {"file_sha256": library_hash,
                        "record_sha256": sha256_hex(row["member"]), "tool_implementation": local.contract.implementation_version}}
                    oral_claims = [claim]
                fixture_claims[candidate, oral_rule] = oral_claims
            for claim in {c["claim_id"]: c for values in fixture_claims.values() for c in values}.values():
                aid = temp.artifacts.put("claim", claim)
                temp.journal.append(fixture_task, "evidence.admitted", actor=IMPORTER,
                    payload={"claim_id": claim["claim_id"], "artifact_id": aid, "admission_state": "admitted"})
            boards, run_ids, call_counts = {}, {}, {}
            for mode in ("full", "staged"):
                calls = []
                def facts(request):
                    calls.append((request["candidate_id"], request["rule"]["rule_id"] + "@v" + str(request["rule"]["version"])))
                    return fixture_claims[calls[-1]], None, ["fixed_actual_fixture"]
                profile = measurement.register(temp, fixture_task, by=IMPORTER, primary_board="Bounded actual-fact mode fixture",
                    rationale="Compare execution modes over the same saved facts and literal task gate",
                    expected_effect="Same qualified-only ordering; deliberate skips remain separately counted", evaluation_mode=mode)
                ctl = RunController(temp, Broker(temp), adapter={"adapter_id": "actual_fact_fixture", "adapter_version": "1", "primary_scheme": "inchikey"},
                    identity_hook=lambda request: identities, evidence_hook=facts,
                    evidence_manifest={"source_run": source_run, "source_seq": source_seq, "library_sha256": library_hash})
                run_ids[mode] = ctl.start(fixture_task, by=IMPORTER, measurement_profile_ref=profile)
                boards[mode] = leaderboard.snapshots(temp, fixture_task)[-1]
                call_counts[mode] = len(calls)
            def eligible(board):
                return [(r["candidate_ref"], r["position"], r["preference_score"]) for r in board["candidate_entries"] if r.get("qualified")]
            require(eligible(boards["full"]) == eligible(boards["staged"]), "full/staged eligible order or scores differ")
            require(len(eligible(boards["full"])) >= 2, "fixture has no nontrivial qualified ordering")
            states = {r["candidate_ref"]: r["qualification_state"] for r in boards["full"]["candidate_entries"]}
            require(states == {r["candidate_ref"]: r["qualification_state"] for r in boards["staged"]["candidate_entries"]},
                    "full/staged qualification states differ")
            require(set(states.values()) >= {"qualified", "rejected", "pending"}, "fixture does not exercise all three required states")
            require(boards["staged"]["reporting_tuple"]["skipped_after_rejection_n"] == len(refs), "unexpected staged skip count")
            expected_qualified = [row for row in chosen if row["group"] == "known_oral"]
            require({r[0] for r in eligible(boards["full"])} == {r["candidate"] for r in expected_qualified}, "unexpected qualified population")
            manual_scores = {r["candidate"]: 0.0 for r in expected_qualified}
            for entry, attr, _, _, _ in selected_rules:
                values = {row["candidate"]: row["cells"][entry["rule_ref"]][0]["value"] for row in expected_qualified}
                for candidate, value in values.items():
                    ordered = sorted(values.values(), reverse=attr["direction"] == "lower_better")
                    positions = [i for i, number in enumerate(ordered) if number == value]
                    percentile = sum(positions) / len(positions) / (len(ordered) - 1)
                    manual_scores[candidate] += percentile / len(selected_rules)
            for candidate, _, score in eligible(boards["full"]):
                require(math.isclose(score, manual_scores[candidate], rel_tol=1e-12, abs_tol=1e-12),
                        "qualified-only score differs from independent pairwise percentile arithmetic")
            require(temp.store.db.execute("SELECT count(*) FROM events WHERE event_type='agent.started'").fetchone()[0] == 0,
                    "fixture attempted a model call")
            checked_values = 0
            for (body,) in temp.store.db.execute("SELECT body FROM events WHERE stream_id=? AND event_type='candidate.assessed'", (run_ids["full"],)):
                event = json.loads(body); cell = temp.artifacts.payload(event["payload"]["artifact_id"])
                original = next((r["cells"][cell["rule_ref"]][0] for r in chosen if r["candidate"] == cell["candidate_ref"] and cell["rule_ref"] in r["cells"]), None)
                if original and isinstance(original.get("value"), (int, float)):
                    require(math.isclose(cell["value"], original["value"], rel_tol=1e-12, abs_tol=1e-12), "saved target value changed on fixture reassessment")
                    checked_values += 1
            report = {"status": "passed", "scope": "bounded actual-evidence execution-mode engineering fixture",
                "fresh_workflow_parity_claimed": False, "source_policy_parity_claimed": False,
                "source_run_id": source_run, "source_run_seq": source_seq, "binding": binding_prov, "task_context": context_prov,
                "frozen_rule_set": frozen_prov, "source_frozen_hard_rules": sum(e["rule_kind"] == "hard_exclusion" for e in frozen["entries"]),
                "universe_file": str(universe_path), "universe_sha256": library_hash, "source_connection": "sqlite_mode_ro_plus_application_write_guard",
                "selection": "two lexicographically first fully observed known-oral candidates; nonoral/unknown ordered by target availability then ID; never source rank",
                "selected": [{"group": r["group"], "candidate_ref": r["candidate"], "label": r["member"].get("pref_name"),
                              "state": states[r["candidate"]], "source_assessments": [p for _, p in r["cells"].values()]} for r in chosen],
                "preference_sources": [p for _, _, _, ap, rp in selected_rules for p in (ap, rp)],
                "source_claims": [p for _, p in claims.values()], "source_target_values_rechecked": checked_values,
                "literal_gate": {"source_field": literal["source_field"], "attribute": literal["attribute"], "rule": literal["rule"],
                                 "authority": "deterministic task_constraint_restated; no human/model approval"},
                "eligible_order": eligible(boards["full"]), "same_eligible_order_and_scores": True,
                "independent_qualified_only_scores": manual_scores,
                "mode_counts": {mode: {**{key: board["reporting_tuple"][key] for key in
                    ("recorded_cell_n", "assessed_cell_n", "skipped_after_rejection_n", "missing_or_conflicted_n", "qualified_n", "assessment_completeness")},
                    "evidence_hook_calls": call_counts[mode]} for mode, board in boards.items()},
                "assumptions": ["Target quantities, units, aggregations and source claim values are unchanged from the pinned historical assessments.",
                    "Source supplemental retrieval bindings are not re-executed; the claims already used by the selected historical cells are retained with their original provenance.",
                    "The temporary hard gate instantiates the source task's explicit oral constraint, not a new data-selected threshold.",
                    "Oral status is the pinned library record flag under the existing adapter policy: false without first_approval remains unknown.",
                    "A recorded route flag is used as an engineering proxy; this does not independently establish every regimen's clinical oral suitability.",
                    "The bounded fixture uses equal-weight means of the unchanged target ordering percentiles; an independent arithmetic check uses only its qualified candidates.",
                    "No literature regeneration, applicability generalization, full-universe ranking or fresh GUI workflow parity is established."],
                "backend_files_sha256": implementations, "network_calls": 0, "model_calls": 0,
                "primary_store_writes": 0, "temporary_store_removed_on_exit": True, "recorded_at": utc_now()}
    require(implementations == backend_hashes(), "backend changed during verification")
    require(source.store.db.execute("SELECT max(seq) FROM events WHERE stream_id=?", (source_run,)).fetchone()[0] == source_seq,
            "completed source run changed during verification")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path("var/primary/store"))
    parser.add_argument("--source-run", default="run_01M50X7EYSBXPDCP0SG859666R")
    parser.add_argument("--universe", type=Path, default=Path("var/primary/universe_chembl.json"))
    parser.add_argument("--out", type=Path, default=Path("design_audit/actual_fixture_parity_2026-10-16.json"))
    args = parser.parse_args()
    require(not args.out.resolve().is_relative_to(args.store.resolve()), "report cannot be written inside the primary store")
    with patch("requests.sessions.Session.request", side_effect=AssertionError("network prohibited")), \
         patch("socket.create_connection", side_effect=AssertionError("network prohibited")), \
         Core.open(args.store.resolve(), read_only=True) as source:
        report = verify(source, args.source_run, args.universe.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "scope": report["scope"], "mode_counts": report["mode_counts"],
                      "out": str(args.out.resolve())}, ensure_ascii=True))


if __name__ == "__main__":
    main()
