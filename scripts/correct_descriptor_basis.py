"""One-time, append-only correction of proven RDKit descriptor provenance.

Default is read-only. No predictions, descriptor recomputation, literature or model
calls occur. --apply consumes an inspected plan and creates fresh versions plus a
narrow software-verification receipt; it never rewrites an old rule or snapshot.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from mas.core import criteria, review, task, vocab
from mas.core.canonical import sha256_hex
from mas.core.clock import utc_now
from mas.core.ids import new_id
from mas.core.journal import actor
from mas.core.runtime import Core

VERSION = "descriptor-basis-correction-1"
ROUTE = "evidence_basis_corrected"
BY = actor("system", "descriptor-basis-correction", "operator")
WHEEL_SHA256 = "fef3527f637abb00d272cf824e8eef0136fe31ebde6c56881f1a8c02c0417806"
SOURCE_SHA256 = {
    "admet_ai/physchem.py": "f2e7cadcc73cfd0d47a4122f9131bdb1ea0f9fc0ba83f0a562bfec6966cec1e6",
    "admet_ai/admet_model.py": "70a0bd4687f0d897485584a4314c6c254dd1d721228002d2c458131d66e5aedd",
}
PROVEN = {
    "logP": {"unit": "log units", "method": "rdkit.Chem.Crippen.MolLogP(mol)", "lines": "physchem.py:5,77-89; admet_model.py:169-187"},
    "PAINS_alert": {"unit": "count", "method": "len(catalog_pains.GetMatches(mol)); FilterCatalogs.PAINS", "lines": "physchem.py:19-21,32-38,86"},
    "BRENK_alert": {"unit": "count", "method": "len(catalog_brenk.GetMatches(mol)); FilterCatalogs.BRENK", "lines": "physchem.py:23-25,41-47,87"},
    "NIH_alert": {"unit": "count", "method": "len(catalog_nih.GetMatches(mol)); FilterCatalogs.NIH", "lines": "physchem.py:27-29,50-56,88"},
}
OLD_ROUTE = {"capability": "predicted_property_lookup", "question_kind": "admet_prediction"}
NEW_ROUTE = {"capability": "property_estimate", "question_kind": "admet_computed_property"}
META = {"version", "status", "supersedes", "proposed_by", "adjudicated_by", "adjudication_id",
        "approval_kind", "confirmed_by", "confirmed_by_a_person", "workbench_revision"}
SOURCE_FIELDS = {"acceptable_value_sources", "acceptable_determination_bases", "evidence_request", "evidence_requests"}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def load_proof(path):
    path = Path(path).resolve()
    proof = json.loads(path.read_text(encoding="utf-8"))
    need(proof.get("package") == "admet-ai" and proof.get("version") == "2.0.1", "Only the independently reviewed package version 2.0.1 is supported")
    need(proof.get("distribution_sha256") == WHEEL_SHA256 and proof.get("verified_against_pypi_sha256"), "Official distribution hash does not match")
    sources = {r["package_path"]: r for r in proof["files"]}
    fixed = []
    for name, digest in SOURCE_SHA256.items():
        row = sources[name]
        need(row["sha256"] == digest and hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() == digest,
             "Reviewed source hash differs: " + name)
        fixed.append(deepcopy(row))
    return {"manifest_path": str(path), "manifest_sha256": sha256_hex(proof), "package": "admet-ai",
            "version": "2.0.1", "wheel_sha256": WHEEL_SHA256, "sources": fixed, "endpoints": PROVEN,
            "release_url": "https://pypi.org/project/admet-ai/2.0.1/",
            "classification": "Deterministic calculations over recorded structures, not experimental measurements.",
            "not_reclassified": "All trained TDC endpoints remain model_prediction/predicted."}


def changes_for(attribute, rule):
    need(rule["rule_kind"] == "preference" and rule.get("predicate_form") == "ordering" and
         rule.get("cutoff") is None and rule.get("cutoff_basis") == "none_evidence_insufficient",
         "Only enabled cutoff-free ordering preferences are eligible")
    need(not attribute.get("value_transform") and not attribute.get("bound_support") and not rule.get("bound_support"),
         "Bound-bearing or transformed criteria need their own review, outside this metadata correction")
    need(attribute.get("acceptable_value_sources") == ["model_prediction"] and
         attribute.get("acceptable_determination_bases") == ["predicted"],
         "The original source and basis must be exactly model_prediction/predicted")
    routes = criteria.evidence_routes(attribute)
    need(bool(routes), "No evidence route")
    new_routes, endpoints = [], []
    for route in routes:
        need(all(route.get(k) == v for k, v in OLD_ROUTE.items()), "Mixed or non-ADMET routes require separate review")
        endpoint = (route.get("parameters") or {}).get("endpoint")
        need(endpoint in PROVEN, "Endpoint not in the independently verified descriptor list")
        need(attribute.get("unit") == PROVEN[endpoint]["unit"], "Declared unit differs from the actual descriptor")
        need(route.get("identifier_scheme") == "inchikey", "Unexpected identifier scheme")
        endpoints.append(endpoint)
        new_routes.append(dict(deepcopy(route), **NEW_ROUTE))
    change = {"acceptable_value_sources": ["database_entry"], "acceptable_determination_bases": ["derived"]}
    if attribute.get("evidence_requests"):
        change["evidence_requests"] = new_routes
        if attribute.get("evidence_request"):
            old_key = criteria.route_key(attribute["evidence_request"])
            position = next(i for i, r in enumerate(routes) if criteria.route_key(r) == old_key)
            change["evidence_request"] = new_routes[position]
    else:
        change["evidence_request"] = new_routes[0]
    return {"attribute": change}, sorted(set(endpoints))


def contract(attribute, rule):
    return {"attribute": {k: v for k, v in attribute.items() if k not in META | SOURCE_FIELDS},
            "rule": {k: v for k, v in rule.items() if k not in META | {"attribute_ref"}}}


def live_runs(core, task_id):
    found = []
    for (body,) in core.store.db.execute("SELECT body FROM events WHERE event_type='run.created' AND "
            "json_extract(body,'$.payload.task_id')=?", (task_id,)):
        event = json.loads(body)
        state = core.store.db.execute("SELECT event_type FROM events WHERE stream_id=? AND event_type IN "
            "('run.created','run.started','run.paused','run.completed','run.failed','run.cancelled','run.unresolved') "
            "ORDER BY seq DESC LIMIT 1", (event["stream_id"],)).fetchone()
        if state and state[0] in ("run.created", "run.started", "run.paused"):
            found.append(event["stream_id"])
    return found


def build_plan(core, task_id, proof, rule_set_ref=None):
    need(core.read_only, "Planning must use a read-only core")
    context = task.get(core, task_id)
    frozen = criteria.rule_set(core, task_id, rule_set_ref)
    ordering = frozen.get("ordering_method") or {}
    need(ordering.get("kind", "weighted_preference") == "weighted_preference" and not ordering.get("weight_vector"),
         "Explicit weights or fitted scoring require a separate prospective version-binding plan")
    proposed, excluded = [], []
    for entry in frozen["entries"]:
        rule = criteria.load(core, entry["rule_ref"], task_id)
        attr = criteria.load(core, entry["attribute_ref"], task_id)
        endpoints = [(r.get("parameters") or {}).get("endpoint") for r in criteria.evidence_routes(attr)
                     if r.get("capability") == OLD_ROUTE["capability"]]
        if not set(endpoints) & set(PROVEN):
            continue
        try:
            need(not entry.get("disputed"), "Disputed criterion needs independent scientific review")
            change, endpoints = changes_for(attr, rule)
        except ValueError as error:
            excluded.append({"rule_ref": entry["rule_ref"], "reason": str(error)})
            continue
        proposed.append({"source_rule_ref": entry["rule_ref"], "source_attribute_ref": entry["attribute_ref"],
            "source_rule_sha256": sha256_hex(rule), "source_attribute_sha256": sha256_hex(attr),
            "source_rule": rule, "source_attribute": attr, "scientific_contract_sha256": sha256_hex(contract(attr, rule)),
            "changes": change, "endpoints": endpoints,
            "methods": [PROVEN[e] for e in endpoints]})
    plan = {"schema": VERSION, "task_id": task_id, "task_context_ref": f"{task_id}@v{context['version']}",
        "migration_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "task_context_sha256": sha256_hex(context), "source_task_seq": core.journal.last_seq(task_id),
        "source_rule_set_ref": frozen["rule_set_ref"], "source_rule_set_sha256": sha256_hex(frozen),
        "ordering_method_sha256": sha256_hex(ordering), "proof": proof, "items": proposed, "excluded": excluded,
        "mode": "dry_run", "primary_modified": False, "candidate_results_used": False,
        "parameters_preserved": ["name", "definition", "direction", "aggregation", "unit", "cutoff", "weights", "source refs"],
        "next_step": "Explicitly apply inspected plan, then create a new freeze/profile and evaluate. Old results remain unchanged."}
    plan["plan_sha256"] = sha256_hex(plan)
    return plan


def apply_plan(core, plan, expected_sha256):
    need(not core.read_only, "Apply needs an explicitly writable core")
    body = {k: v for k, v in plan.items() if k != "plan_sha256"}
    need(plan["schema"] == VERSION and sha256_hex(body) == plan["plan_sha256"] == expected_sha256, "Plan digest differs")
    need(plan["migration_source_sha256"] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         "Migration implementation changed after dry run")
    proof = load_proof(plan["proof"]["manifest_path"])
    need(proof == plan["proof"], "Reviewed implementation proof changed")
    tid = plan["task_id"]
    need(sha256_hex(task.get(core, tid)) == plan["task_context_sha256"], "Task context changed after dry run")
    frozen = criteria.rule_set(core, tid, plan["source_rule_set_ref"])
    need(sha256_hex(frozen) == plan["source_rule_set_sha256"], "The original frozen set differs")
    frozen_refs = {e["rule_ref"]: e["attribute_ref"] for e in frozen["entries"]}
    need(not live_runs(core, tid), "Finish or preserve/stop active task runs before this correction")
    vocab.require("adjudication_route", ROUTE)
    latest = {r["rule_id"]: r for r in criteria.registered_rule_records(core, tid)}
    prior = [e.payload for e in core.journal.replay(tid) if e.event_type == "decision.recorded" and
             e.payload.get("basis_correction_plan_sha256") == expected_sha256]
    receipts = {r["rule_ref_before"]: r for r in prior}
    latest_freeze = criteria.rule_set(core, tid)["rule_set_ref"]
    need(latest_freeze == plan["source_rule_set_ref"] or all(r["source_rule_ref"] in receipts for r in plan["items"]),
         "A different policy was frozen after planning; inspect a new plan before changing active criteria")
    prepared = []
    reason = "Verified deterministic descriptor provenance correction; plan " + expected_sha256
    # Validate every item before writing the first one. A partial interrupted application
    # can resume only its own exactly matching version/review pair.
    for row in plan["items"]:
        old_rule = criteria.load(core, row["source_rule_ref"], tid)
        old_attr = criteria.load(core, row["source_attribute_ref"], tid)
        need(sha256_hex(old_rule) == row["source_rule_sha256"] and sha256_hex(old_attr) == row["source_attribute_sha256"],
             "Original version changed")
        need(old_rule == row["source_rule"] and old_attr == row["source_attribute"] and
             frozen_refs.get(row["source_rule_ref"]) == row["source_attribute_ref"],
             "The plan does not contain exact originally frozen records")
        change, endpoints = changes_for(old_attr, old_rule)
        need(change == row["changes"] and endpoints == row["endpoints"], "Plan contains unauthorized field changes")
        current = latest[old_rule["rule_id"]]
        ref = f"{current['rule_id']}@v{current['version']}"
        receipt = receipts.get(row["source_rule_ref"])
        if receipt:
            need(receipt["rule_ref_after"] == ref, "Already-corrected criterion was subsequently revised")
            prepared.append((row, current, receipt))
        elif ref == row["source_rule_ref"]:
            prepared.append((row, current, None))
        else:
            revision = current.get("workbench_revision") or {}
            need(revision.get("source_rule_ref") == row["source_rule_ref"] and revision.get("reason") == reason,
                 "A different revision already exists")
            prepared.append((row, current, None))
    results = []
    for row, current, receipt in prepared:
        if receipt:
            results.append({"rule_ref": receipt["rule_ref_after"], "adjudication_id": receipt["adjudication_id"], "reused": True})
            continue
        old = row["source_rule_ref"]
        current_ref = f"{current['rule_id']}@v{current['version']}"
        if current_ref == old:
            revision = criteria.revise_for_workbench(core, tid, old, row["changes"], reason=reason, by=BY)
            new_ref = revision["rule_ref"]
        else:
            new_ref = current_ref
        new_rule = criteria.load(core, new_ref, tid)
        new_attr = criteria.load(core, new_rule["attribute_ref"], tid)
        need(contract(new_attr, new_rule) == contract(row["source_attribute"], row["source_rule"]), "Scientific contract changed")
        need(all(new_attr.get(k) == v for k, v in row["changes"]["attribute"].items()), "New route or basis differs")
        queue = [q for q in review.items(core, [tid]).values() if q["subject"].get("id") == new_ref]
        need(len(queue) == 1 and queue[0]["state"] in ("open", "in_review"), "Fresh review item is missing or already decided")
        record = {"adjudication_id": new_id("adj"), "queue_item_ref": queue[0]["item_id"], "subject": queue[0]["subject"],
            "task_id": tid, "task_context_id@v": plan["task_context_ref"], "route": ROUTE, "resolution": "approve",
            "basis": ROUTE, "reason_text": reason, "authority": "machine_adjudication", "approval_kind": "software_status",
            "confirmed_by_a_person": False, "actor": BY, "adjudicated_at": utc_now(),
            "rule_ref_before": old, "rule_ref_after": new_ref, "rule_kind_before": row["source_rule"]["rule_kind"],
            "rule_kind_after": new_rule["rule_kind"], "attribute_ref_before": row["source_attribute_ref"],
            "attribute_ref_after": new_rule["attribute_ref"], "scores_candidates": True, "grants": None,
            "revision": None, "requires_explicit_review": False, "predictor_boundary": None, "requirement_review": None,
            "qualification_policy": "qualification_first_v1", "cites": {"implementation_proof": proof, "endpoints": row["endpoints"]},
            "edits": [{"target": row["source_attribute_ref"], "target_after": new_rule["attribute_ref"],
                       "field": key, "from": row["source_attribute"].get(key), "to": value}
                      for key, value in row["changes"]["attribute"].items()],
            "basis_correction_plan_sha256": expected_sha256, "scientific_contract_sha256": row["scientific_contract_sha256"],
            "migration_source_sha256": plan["migration_source_sha256"],
            "review_scope": "Source-kind, determination-basis and matching route only; no threshold or applicability approval.",
            "model_calls": 0, "candidate_results_used": False}
        ref = core.artifacts.put("machine_adjudication", record)
        core.journal.append(tid, "decision.recorded", actor=BY, ids={"task_id": tid},
            payload=dict(record, artifact_id=ref), artifact_links=[{"kind": "machine_adjudication", "id": ref}],
            summary="Software-verified descriptor basis correction; no person confirmed it")
        results.append({"rule_ref": new_ref, "attribute_ref": new_rule["attribute_ref"],
                        "adjudication_id": record["adjudication_id"], "artifact_id": ref, "reused": False})
    need(sha256_hex(criteria.rule_set(core, tid, plan["source_rule_set_ref"])) == plan["source_rule_set_sha256"],
         "Original frozen rules changed")
    return {"mode": "applied", "plan_sha256": expected_sha256, "results": results,
            "old_freeze_preserved": True, "new_freeze_required": True, "model_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--task")
    parser.add_argument("--rule-set")
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--expect-plan-sha256")
    args = parser.parse_args()
    if args.apply:
        need(args.plan and args.expect_plan_sha256, "Apply requires --plan and --expect-plan-sha256")
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        with Core.open(args.store) as core:
            result = apply_plan(core, plan, args.expect_plan_sha256)
    else:
        need(args.task and args.proof, "Dry run requires --task and --proof")
        with Core.open(args.store, read_only=True) as core:
            result = build_plan(core, args.task, load_proof(args.proof), args.rule_set)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": result["mode"], "items": len(result.get("items", result.get("results", []))),
                      "out": str(args.out.resolve()), "plan_sha256": result.get("plan_sha256")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

