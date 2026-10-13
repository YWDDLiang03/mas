"""Leaderboard Service (C12; design §4.12, `leaderboard_spec.md`).

Task-scoped, versioned snapshots. Each snapshot reports the result kind: the all-pass
set under hard rules and, when preference rules exist, the ranking under the registered
ordering method (`both_reported`). Precision is never shown without coverage and
abstention. Every state change against the parent snapshot carries a change record.
"""

from __future__ import annotations

from typing import Any

from .canonical import sha256_hex
from .clock import utc_now
from .ids import new_id
from .runtime import Core

STATE_ORDER = {"recommended": 0, "provisional": 1, "unassessed": 2, "rejected": 3}


def leaderboard_record(core: Core, task_context: dict[str, Any]) -> str:
    """The open leaderboard (`lbd_`) for the task's comparability key, opening one if needed."""
    key_fields = {k: task_context.get(k) for k in ("objective_text", "mode", "evaluation_scope")}
    key_fields["required_scope"] = sorted(e.get("identifier", "") for e in task_context.get("scope_entities", [])
                                          if e.get("role") == "required")
    universe = task_context.get("candidate_universe") or {}
    key_fields["universe"] = {k: universe.get(k) for k in ("kind", "source", "as_of")}
    key_fields["hard_constraints"] = sorted(c.get("text", "") for c in task_context.get("constraints", [])
                                            if c.get("hardness") == "hard")
    comparability_key = sha256_hex(key_fields)
    task_id = task_context["task_context_id"]
    existing = [e.payload for e in core.journal.replay(task_id) if e.event_type == "leaderboard.current_set"
                and e.payload.get("opened")]
    for record in existing:
        if record["comparability_key"] == comparability_key:
            return record["leaderboard_id"]
    leaderboard_id = f"lbd_{task_id}_{len(existing) + 1}"
    supersedes = existing[-1]["leaderboard_id"] if existing else None
    core.journal.append(task_id, "leaderboard.current_set", actor={"kind": "system", "id": "C12", "role": "leaderboard"},
                        payload={"opened": True, "leaderboard_id": leaderboard_id, "comparability_key": comparability_key,
                                 "supersedes": supersedes, "current_snapshot_id": None},
                        summary=f"opened {leaderboard_id}")
    return leaderboard_id


def snapshots(core: Core, task_id: str) -> list[dict[str, Any]]:
    out = []
    for stream in core.journal.streams("run_"):
        for event in core.journal.replay(stream):
            if event.event_type == "leaderboard.snapshot_published" and event.payload["task_id"] == task_id:
                out.append(core.artifacts.payload(event.payload["artifact_id"]))
    return sorted(out, key=lambda s: s["published_at"])


def _changes(previous: dict[str, Any] | None, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if previous is None:
        return [{"change_id": new_id("chg"), "object_kind": "leaderboard_entry", "object_id": e["candidate_ref"],
                 "operation": "admit" if e["state"] in ("recommended", "provisional") else "status_changed",
                 "fields_changed": [{"field": "state", "before": None, "after": e["state"]}],
                 "cause": {"assessment_refs": e["per_criterion_refs"]}, "explanation_status": "evidence_linked"}
                for e in entries]
    before = {e["candidate_ref"]: e for e in previous["candidate_entries"]}
    changes = []
    for entry in entries:
        old = before.get(entry["candidate_ref"])
        if old is None or old["state"] != entry["state"] or old.get("position") != entry.get("position"):
            operation = ("admit" if old is None else
                         "exclude" if entry["state"] == "rejected" else
                         "promote" if STATE_ORDER[entry["state"]] < STATE_ORDER[old["state"]] else
                         "demote" if STATE_ORDER[entry["state"]] > STATE_ORDER[old["state"]] else "rank_changed")
            changes.append({"change_id": new_id("chg"), "object_kind": "leaderboard_entry", "object_id": entry["candidate_ref"],
                            "operation": operation,
                            "fields_changed": [{"field": "state", "before": old and old["state"], "after": entry["state"]},
                                               {"field": "position", "before": old and old.get("position"),
                                                "after": entry.get("position")}],
                            "cause": {"assessment_refs": entry["per_criterion_refs"]},
                            "explanation_status": "evidence_linked" if entry["per_criterion_refs"] else "unexplained"})
    return changes


def build_snapshot(*, task_context: dict[str, Any], leaderboard_id: str, run_id: str, round_id: str, rule_set: dict[str, Any],
                   evidence_snapshot_id: str | None, roll_ups: dict[str, dict[str, Any]],
                   cells: dict[str, list[dict[str, Any]]], scores: dict[str, tuple[float | None, float]],
                   identities: dict[str, dict[str, Any]], parent: dict[str, Any] | None, sweep_completeness: float,
                   budget: dict[str, Any], strategy: str = "strat@v1", tool_coverage: dict[str, Any] | None = None,
                   ranking_coverage_floor: float = 0.5) -> dict[str, Any]:
    has_preferences = any(e["rule_kind"] == "preference" for e in rule_set["entries"])
    has_hard = any(e["rule_kind"] == "hard_exclusion" for e in rule_set["entries"])
    result_kind = "both_reported" if (has_hard and has_preferences) else "ranked_under_score" if has_preferences else "all_pass_set"
    entries = []
    for candidate_id, summary in roll_ups.items():
        candidate_cells = cells.get(candidate_id, [])
        score, pref_coverage = scores.get(candidate_id, (None, 0.0))
        identity = identities.get(candidate_id, {})
        entries.append({
            "candidate_ref": candidate_id, "identity_labels": [identity.get("preferred_label") or identity.get("input_label")],
            "state": summary["state"], "state_reason": summary["state_reason"], "preference_score": score,
            "preference_coverage": pref_coverage, "position": None,
            "per_criterion_refs": [c["assessment_id"] for c in candidate_cells],
            "coverage": summary["hard_rule_coverage"], "missing": summary["blocking_unknowns"],
            "counter_evidence_refs": sorted({r for c in candidate_cells for r in c["conflicting_claim_refs"]}),
            "measured_vs_predicted_counts": {kind: sum(c["value_kind"] == kind for c in candidate_cells)
                                             for kind in ("measured", "curated", "derived", "predicted")},
            "review_status": "none", "verdicts": {c["attribute_ref"]: c["verdict"] for c in candidate_cells},
        })
    for entry in entries:
        if entry["preference_score"] is not None and entry["preference_coverage"] < ranking_coverage_floor:
            entry["rank_note"] = (f"too little preference evidence to rank (coverage {entry['preference_coverage']:.2f} "
                                  f"below {ranking_coverage_floor:.2f})")
    ranked = [e for e in entries if e["state"] in ("recommended", "provisional") and e["preference_score"] is not None
              and e["preference_coverage"] >= ranking_coverage_floor]
    ranked.sort(key=lambda e: (-e["preference_score"], STATE_ORDER[e["state"]], -e["preference_coverage"], -(e["coverage"] or 0),
                               e["candidate_ref"]))
    if has_preferences:
        for position, entry in enumerate(ranked, 1):
            entry["position"] = position
    entries.sort(key=lambda e: (e["position"] is None, e["position"] or 0, STATE_ORDER[e["state"]], e["candidate_ref"]))
    admitted = [e for e in entries if e["state"] == "recommended"]
    all_cells = [c for cs in cells.values() for c in cs]
    applicable = [c for c in all_cells if c["verdict"] != "inapplicable"]
    value_bearing = [c for c in applicable if c["verdict"] in ("pass", "fail")]
    abstentions: dict[str, int] = {}
    for e in entries:
        if e["state"] in ("provisional", "unassessed"):
            key = e["state_reason"].split(":")[0]
            abstentions[key] = abstentions.get(key, 0) + 1
    snapshot = {
        "snapshot_id": None, "task_id": task_context["task_context_id"],
        "task_context_id@v": f"{task_context['task_context_id']}@v{task_context['version']}",
        "run_id": run_id, "round_id": round_id, "rules@v": rule_set["rule_set_ref"], "strat@v": strategy,
        "evidence_snapshot_id": evidence_snapshot_id, "result_kind": result_kind,
        "ordering_method": rule_set.get("ordering_method"),
        "all_pass_count": sum(e["state"] in ("recommended", "provisional") and (e["coverage"] or 0) == 1.0
                              and all(v == "pass" for k, v in e["verdicts"].items()) for e in entries) if has_hard else None,
        "candidate_entries": entries, "leaderboard_id": leaderboard_id,
        "parent_snapshot_id": parent["snapshot_id"] if parent else None,
        "change_records": _changes(parent, entries), "tool_coverage": tool_coverage or {},
        "reporting_tuple": {"admitted_n": len(admitted), "precision_among_admitted": None,
                            "coverage_fraction": (len(value_bearing) / len(applicable)) if applicable else 0.0,
                            "sweep_completeness": sweep_completeness, "abstention_n_by_reason": abstentions,
                            "ranking_coverage_floor": ranking_coverage_floor,
                            "unranked_for_coverage": sum(1 for e in entries if "rank_note" in e),
                            "budget": budget},
        "interaction_estimate_provider": "none", "human_review_summary": {"recommended_requires_hd": True},
        "published_at": utc_now(),
    }
    return snapshot
