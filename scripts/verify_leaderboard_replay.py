"""Rebuild a completed board from frozen cells, with no tools, models, or store writes.

Run once with the project interpreter after the final sweep completes::

    python scripts/verify_leaderboard_replay.py --store var/primary/store \
        --run RUN --snapshot SNAPSHOT --profile ARTIFACT --rules rules@vN \
        --expected-candidates 3177 --out var/verification/replay.json

The old scores are comparison targets only. The scorer, calibration guard, roll-up
and leaderboard builder receive persisted assessments and the frozen rule set.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import mas
from mas.core import assessor, constants, criteria, leaderboard, measurement, supplements, task
from mas.core.canonical import sha256_hex
from mas.core.clock import utc_now
from mas.core.runtime import Core


ENTRY_FIELDS = (
    "identity_labels", "state", "state_reason", "preference_score", "preference_coverage", "coverage", "position",
    "clears_hard_rules", "n_fail_hard", "n_unknown_hard", "gate_blocked_by", "missing",
    "clears_mandated_criteria", "n_mandated", "n_mandated_answered", "mandated_coverage", "mandated_blocked_by",
    "mandated_gates", "mandated_gates_unanswered", "verdicts", "measured_vs_predicted_counts",
    "gap_filled_criteria", "determination_bases", "rank_note",
)
REPORT_FIELDS = (
    "admitted_n", "coverage_fraction", "sweep_completeness", "abstention_n_by_reason", "ranking_coverage_floor",
    "unranked_for_coverage", "mandated_coverage_floor", "rank_requires_mandated_coverage", "mandated_rule_refs",
    "ineligible_for_mandated_coverage", "eligible_on_mandated_criteria", "ranked_with_a_mandated_gate_unanswered",
)


class ReplayError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayError(message)


def events(core: Core, run_id: str, kinds: tuple[str, ...], *, before: int | None = None):
    placeholders = ",".join("?" for _ in kinds)
    query = f"SELECT body FROM events WHERE stream_id=? AND event_type IN ({placeholders})"
    values: list[Any] = [run_id, *kinds]
    if before is not None:
        query += " AND seq < ?"
        values.append(before)
    for (body,) in core.store.db.execute(query + " ORDER BY seq", values):
        yield json.loads(body)


def artifact(core: Core, artifact_id: str, kind: str) -> tuple[dict[str, Any], str]:
    row = core.store.db.execute("SELECT kind,body,sha256 FROM artifacts WHERE artifact_id=?", (artifact_id,)).fetchone()
    require(row is not None and row[0] == kind, f"{artifact_id} is not a {kind} artifact")
    envelope = json.loads(row[1])
    require(sha256_hex(envelope) == row[2], f"artifact hash differs for {artifact_id}")
    return envelope["payload"], row[2]


def source_hash() -> str:
    root = Path(mas.__file__).resolve().parent
    digest = hashlib.sha256()
    for source in sorted(root.rglob("*.py")):
        digest.update(source.relative_to(root).as_posix().encode("utf-8") + b"\0")
        digest.update(source.read_bytes() + b"\0")
    return digest.hexdigest()


def same(expected: Any, rebuilt: Any, tolerance: float) -> bool:
    if type(expected) is not type(rebuilt) and (isinstance(expected, bool) or isinstance(rebuilt, bool)):
        return False
    if isinstance(expected, (int, float)) and isinstance(rebuilt, (int, float)):
        return math.isclose(expected, rebuilt, rel_tol=tolerance, abs_tol=tolerance)
    if isinstance(expected, list) and isinstance(rebuilt, list):
        return len(expected) == len(rebuilt) and all(same(a, b, tolerance) for a, b in zip(expected, rebuilt))
    if isinstance(expected, dict) and isinstance(rebuilt, dict):
        return expected.keys() == rebuilt.keys() and all(same(expected[key], rebuilt[key], tolerance) for key in expected)
    return expected == rebuilt


def replay(core: Core, args) -> dict[str, Any]:
    require(core.read_only, "verification requires a read-only Core")
    lifecycle = list(events(core, args.run, ("run.created", "run.started", "run.resumed", "run.paused",
                                            "run.completed", "run.unresolved", "run.failed", "run.cancelled")))
    require(bool(lifecycle) and lifecycle[0]["event_type"] == "run.created", "the fixed run does not exist")
    require(lifecycle[-1]["event_type"] == "run.completed", "the fixed run is not completed; do not verify a live/partial run")
    require(lifecycle[-1]["payload"].get("snapshot_id") == args.snapshot,
            "the explicit snapshot differs from the run's final completed result")
    created = lifecycle[0]
    binding, binding_hash = artifact(core, created["payload"]["binding_artifact_id"], "run_binding")
    require(binding.get("run_purpose", "sweep") == "sweep", "the fixed run is not a candidate sweep")
    require(binding["rules@v"] == args.rules, "the explicit rule set differs from the run binding")
    require(binding.get("measurement_profile_ref") == args.profile, "the explicit profile differs from the run binding")
    require(binding.get("candidate_limit") is None and binding.get("sweep_scope") == "full_universe",
            "the bound run is not an unlimited full-universe sweep")
    task_id, version = binding["task_context_id@v"].rsplit("@v", 1)
    publications = [event for event in events(core, args.run, ("leaderboard.snapshot_published",))
                    if event["payload"].get("snapshot_id") == args.snapshot]
    require(len(publications) == 1, "the fixed snapshot is not published exactly once by this run")
    published = publications[0]
    saved, saved_hash = artifact(core, published["payload"]["artifact_id"], "leaderboard_snapshot")
    require(saved["run_id"] == args.run and saved["task_id"] == task_id and saved["rules@v"] == args.rules,
            "snapshot identities differ from the explicit run/task/rules")
    context = task.get(core, task_id, int(version))
    frozen = criteria.rule_set(core, task_id, args.rules)
    current_source = source_hash()
    require(bool(binding.get("implementation", {}).get("source_sha256")), "the run has no bound source-tree digest")
    require(current_source == binding["implementation"]["source_sha256"],
            "current source differs from the bound implementation; use the archived source before reproducing")

    settings = {}
    settings_ref = binding.get("settings") or {}
    if settings_ref.get("layers_artifact_id"):
        layers, _ = artifact(core, settings_ref["layers_artifact_id"], "config_layers")
        settings = {entry["key"]: entry["value"] for entry in layers["settings"]}
    profile = measurement.verify(
        core, task_id, args.profile, context=context, rule_set=frozen, sweep_seed=binding["sweep_seed"],
        evidence_cutoff=binding["evidence_cutoff"], candidate_limit=binding.get("candidate_limit"), settings=settings,
        config_hash=settings_ref.get("config_hash"), implementation=binding["implementation"],
        bound_digest=binding.get("measurement_profile_digest"))
    require(saved.get("measurement_profile", {}).get("digest") == profile["digest"], "snapshot profile digest differs")
    require(binding.get("verified_supplements") == supplements.binding(core, context), "bound supplement digest differs")
    require(saved.get("verified_supplements") == binding.get("verified_supplements"), "snapshot supplement binding differs")

    values = {key: value[0] for key, value in constants.CORE_DEFAULTS.items()}
    for stream in ("eval", args.run):
        for event in events(core, stream, ("constant.registered",), before=published["seq"] if stream == args.run else None):
            values[event["payload"]["const_id"]] = event["payload"]["value"]
    scoring_policy = profile["policy"]["scoring_policy"]
    require(values["const_ranking_coverage_floor"] == scoring_policy["ranking_coverage_floor"], "effective ranking floor drifted")
    require(values["const_mandated_coverage_floor"] == scoring_policy["eligibility_mandated_coverage_floor"],
            "effective eligibility floor drifted")

    identities, cells, identity_hashes, cell_hashes = {}, {}, {}, {}
    for event in events(core, args.run, ("identity.resolved", "candidate.assessed"), before=published["seq"]):
        payload = event["payload"]
        if event["event_type"] == "identity.resolved":
            identity, digest = artifact(core, payload["artifact_id"], "identity_record")
            identities[identity["candidate_id"]] = identity
            identity_hashes[identity["candidate_id"]] = digest
        else:
            cell, digest = artifact(core, payload["artifact_id"], "assessment")
            key = (cell["rule_ref"], cell["candidate_ref"])
            cells[key], cell_hashes["|".join(key)] = cell, digest
    require(len(identities) == args.expected_candidates, "frozen identity count differs from the declared full scope")
    saved_entries = {entry["candidate_ref"]: entry for entry in saved["candidate_entries"]}
    require(len(saved_entries) == len(saved["candidate_entries"]), "the saved board contains duplicate candidate identities")
    require(set(identities) == set(saved_entries), "the complete identity set differs from the saved board")
    rule_refs = {entry["rule_ref"] for entry in frozen["entries"]}
    require(set(cells) == {(ref, candidate) for ref in rule_refs for candidate in identities},
            "frozen cells do not cover the full candidate-by-rule Cartesian product")
    for candidate, saved_entry in saved_entries.items():
        require(set(saved_entry["per_criterion_refs"]) == {cells[(ref, candidate)]["assessment_id"] for ref in rule_refs},
                f"the snapshot references different frozen assessments for {candidate}")
    evidence_events = [event for event in events(core, args.run, ("evidence.snapshot_frozen",), before=published["seq"])
                       if event["payload"]["snapshot_id"] == saved["evidence_snapshot_id"]]
    require(len(evidence_events) == 1, "the fixed evidence snapshot is missing or ambiguous")
    evidence, evidence_hash = artifact(core, evidence_events[0]["payload"]["artifact_id"], "evidence_snapshot")
    require(set(evidence["claim_ids"]) == {ref for cell in cells.values() for ref in cell["value_source_claim_refs"]},
            "the frozen claim set differs from the assessments used by this board")
    require(evidence["cutoff_at"] == binding["evidence_cutoff"], "the evidence snapshot cutoff differs")
    require(evidence["tool_availability_snapshot"] == binding["tool_availability_snapshot"],
            "the frozen evidence tool manifest differs from the run binding")

    loaded = [{"entry": entry, "rule": criteria.load(core, entry["rule_ref"], task_id),
               "attribute": criteria.load(core, entry["attribute_ref"], task_id)} for entry in frozen["entries"]]
    info = {item["entry"]["rule_ref"]: {"rule_kind": item["rule"]["rule_kind"],
              "predicate_form": item["rule"].get("predicate_form", "threshold"), "direction": item["attribute"].get("direction")}
            for item in loaded}
    mandated = [item["entry"]["rule_ref"] for item in loaded if criteria.is_task_mandated(item["attribute"])]
    by_candidate = {candidate: [] for candidate in sorted(identities)}
    for (_, candidate), cell in cells.items():
        by_candidate[candidate].append(cell)
    guard = assessor.calibration_guard(by_candidate, info, mandated_rule_refs=mandated,
                                      max_removed_share=settings.get("assess.max_reference_exclusion_share",
                                                                     assessor.DEFAULT_MAX_REFERENCE_EXCLUSION))
    if guard["demoted"]:
        info = {ref: dict(item, rule_kind="preference") if ref in guard["demoted"] else item for ref, item in info.items()}
        by_candidate = {candidate: [dict(cell, rule_kind="preference",
                          demoted_by_calibration_guard=guard["demoted"][cell["rule_ref"]])
                          if cell["rule_ref"] in guard["demoted"] else cell for cell in mine]
                        for candidate, mine in by_candidate.items()}
    pending_hard = [ref for ref in frozen.get("pending", []) if criteria.load(core, ref, task_id)["rule_kind"] == "hard_exclusion"]
    roll_ups = {candidate: assessor.roll_up(
        candidate, mine, coverage_floor=frozen.get("coverage_floor", 1.0),
        recommended_requires_hd=context.get("human_review_requirements", {}).get("recommended_requires_hd", True),
        pending_hard_rules=pending_hard, machine_authority=bool(frozen.get("machine_adjudicated")))
        for candidate, mine in by_candidate.items()}
    ordering = frozen.get("ordering_method") or {}
    if ordering.get("kind") == "symbolic_expression":
        scores = assessor.expression_scores(by_candidate, info, ordering)
    else:
        require(ordering.get("kind", "weighted_preference") == "weighted_preference", "unsupported frozen scorer")
        scores = assessor.preference_scores(by_candidate, info, ordering.get("weight_vector") or {})
    attempted = sum(cell["verdict"] != "not_assessed" or cell.get("not_assessed_reason") in
                    ("identity_unresolved", "identity_pending_review") for cell in cells.values())
    completeness = attempted / len(cells) if cells else 1.0
    rebuilt = leaderboard.build_snapshot(
        task_context=context, leaderboard_id=saved["leaderboard_id"], run_id=args.run, round_id=saved["round_id"],
        rule_set=frozen, evidence_snapshot_id=saved["evidence_snapshot_id"], roll_ups=roll_ups, cells=by_candidate,
        scores=scores, identities=identities, parent=None, sweep_completeness=completeness, budget={},
        ranking_coverage_floor=values["const_ranking_coverage_floor"], mandated_rule_refs=mandated,
        mandated_coverage_floor=values["const_mandated_coverage_floor"], calibration_guard=guard,
        rank_requires_mandated_coverage=scoring_policy["rank_requires_mandated_coverage"])
    require(completeness == 1.0, "the completed run contains unassessed cells")
    rebuilt_entries = {entry["candidate_ref"]: entry for entry in rebuilt["candidate_entries"]}
    differences = []
    for candidate in sorted(identities):
        for field in ENTRY_FIELDS:
            expected, actual = saved_entries[candidate].get(field), rebuilt_entries[candidate].get(field)
            if not same(expected, actual, args.tolerance):
                differences.append({"candidate_ref": candidate, "field": field, "saved": expected, "rebuilt": actual})
    for field in REPORT_FIELDS:
        if not same(saved["reporting_tuple"].get(field), rebuilt["reporting_tuple"].get(field), args.tolerance):
            differences.append({"field": f"reporting_tuple.{field}", "saved": saved["reporting_tuple"].get(field),
                                "rebuilt": rebuilt["reporting_tuple"].get(field)})
    for field in ("result_kind", "no_recommendation", "abstention_reason", "all_pass_count", "calibration_guard"):
        if not same(saved.get(field), rebuilt.get(field), args.tolerance):
            differences.append({"field": field, "saved": saved.get(field), "rebuilt": rebuilt.get(field)})
    canonical_entries = lambda board: [{"candidate_ref": candidate, **{
        field: board[candidate].get(field) for field in ENTRY_FIELDS}} for candidate in sorted(board)]
    return {"status": "pass" if not differences else "fail", "run_id": args.run, "task_id": task_id,
            "snapshot_id": args.snapshot, "rules_ref": args.rules, "profile_ref": args.profile,
            "binding_sha256": binding_hash, "published_snapshot_sha256": saved_hash, "evidence_snapshot_sha256": evidence_hash,
            "source_sha256": current_source, "profile_digest": profile["digest"], "profile_conforms": True,
            "identity_count": len(identities), "scoring_rule_count": len(rule_refs), "frozen_cell_count": len(cells),
            "sweep_completeness": completeness, "identity_set_sha256": sha256_hex(sorted(identities)),
            "identity_artifacts_sha256": sha256_hex(identity_hashes), "cell_artifacts_sha256": sha256_hex(cell_hashes),
            "saved_comparable_entries_sha256": sha256_hex(canonical_entries(saved_entries)),
            "rebuilt_comparable_entries_sha256": sha256_hex(canonical_entries(rebuilt_entries)),
            "comparison_fields": list(ENTRY_FIELDS), "float_tolerance": args.tolerance,
            "difference_count": len(differences), "differences": differences}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("store", "run", "snapshot", "profile", "rules", "out"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--expected-candidates", type=int, default=3177)
    parser.add_argument("--tolerance", type=float, default=1e-12)
    args = parser.parse_args(argv)
    output, store = Path(args.out).resolve(), Path(args.store).resolve()
    if output.is_relative_to(store):
        parser.error("the verification report must be outside the real store root")
    if output.exists():
        parser.error("the verification report already exists; preserve the previous artifact")
    if not math.isfinite(args.tolerance) or args.tolerance < 0 or args.expected_candidates < 1:
        parser.error("tolerance must be a finite nonnegative value and candidate count positive")
    started = utc_now()
    try:
        with Core.open(store, read_only=True) as core:
            result = replay(core, args)
    except Exception as error:
        result = {"status": "blocked", "run_id": args.run, "snapshot_id": args.snapshot,
                  "profile_ref": args.profile, "rules_ref": args.rules,
                  "error_class": type(error).__name__, "message": str(error)}
    result.update(started_at=started, finished_at=utc_now(), store_read_only=True,
                  method="frozen assessments -> calibration -> roll-up -> score -> full leaderboard comparison",
                  claim_scope={"establishes": ["offline aggregation/scoring/ranking reproducibility"] if result["status"] == "pass" else [],
                               "not_reperformed": ["identity resolution", "source retrieval", "claim extraction", "cell assessment"],
                               "does_not_establish": ["biological effectiveness", "expert agreement", "independent validation"]})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"status": result["status"], "report": str(output), "differences": result.get("difference_count")}, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
