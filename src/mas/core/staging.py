"""Registered shortlist stages (design §6.6 feasibility, ADR-33): a smaller universe under a stated rule.

When a full sweep of every rule is infeasible (for example literature-evaluated rules over
thousands of candidates), the operator registers a shortlist rule: the top K candidates of a
published snapshot, ties at the boundary included. The shortlist becomes a derived task
(`derived_from_task_id`) that carries the source snapshot, the rule, and copies of the
registered criteria with links to their source versions; hard and disputed rules are raised
again for an expert. Nothing about the shortlist rule refers to any particular candidate.
"""

from __future__ import annotations

from typing import Any

from . import criteria, leaderboard, review, task as task_mod
from .journal import actor as make_actor
from .runtime import Core


def shortlist_members(snapshot: dict[str, Any], top_k: int) -> list[dict[str, Any]]:
    """Ranked entries in positions 1..K, plus any entry tied with position K."""
    ranked = sorted((e for e in snapshot["candidate_entries"] if e.get("position")), key=lambda e: e["position"])
    if len(ranked) <= top_k:
        return ranked
    boundary = ranked[top_k - 1]["preference_score"]
    return [e for e in ranked if e["position"] <= top_k or e["preference_score"] == boundary]


def shortlist_task(core: Core, source_task_id: str, *, top_k: int, by: dict[str, Any],
                   identities: dict[str, dict[str, Any]] | None = None) -> str:
    snapshot = leaderboard.snapshots(core, source_task_id)[-1]
    chosen = shortlist_members(snapshot, top_k)
    source = task_mod.get(core, source_task_id)
    members = []
    for entry in chosen:
        identifier = entry["candidate_ref"].split("-", 1)[1] if "-" in entry["candidate_ref"] else entry["candidate_ref"]
        members.append(identifier)
    spec = {k: v for k, v in source.items() if k not in ("task_context_id", "version", "supersedes", "unknowns", "created_by")}
    spec["candidate_universe"] = {
        "kind": "enumerated_set", "members": members, "size_if_known": len(members),
        "access_path": source.get("candidate_universe", {}).get("access_path"),
        "source": f"registered shortlist of {snapshot['snapshot_id']}",
        "shortlist_rule": {"kind": "top_k_by_position", "k": top_k, "ties_at_boundary": "included",
                           "source_snapshot_id": snapshot["snapshot_id"], "source_rules": snapshot["rules@v"],
                           "selected": len(members)}}
    spec["derived_from_task_id"] = source_task_id
    new_task_id, _ = task_mod.record_version(core, spec, by=by)
    copier = make_actor("system", "shortlist-stage", "criterion_copy")
    disputes = {item["subject"]["id"]: item for item in review.items(core, [source_task_id]).values()
                if item["subject"]["kind"] == "rule_version" and item["why_expert_required"].startswith("proposer and critic")}
    latest_rules = {}
    for event in core.journal.replay(source_task_id):
        if event.event_type == "criterion.version_proposed" and event.payload["kind"] == "rule":
            latest_rules[event.payload["id"]] = f"{event.payload['id']}@v{event.payload['version']}"
    for rule_ref in sorted(latest_rules.values()):
        rule = criteria.load(core, rule_ref, source_task_id)
        attribute = criteria.load(core, rule["attribute_ref"], source_task_id)
        attribute = {k: v for k, v in attribute.items() if k not in ("attribute_id", "version", "status", "proposed_by")}
        attribute["attribute_id"] = rule["attribute_ref"].rsplit("@v", 1)[0]
        attribute["copied_from"] = {"task_id": source_task_id, "attribute_ref": rule["attribute_ref"]}
        rule_copy = {k: v for k, v in rule.items() if k not in ("rule_id", "version", "status", "proposed_by", "attribute_ref")}
        rule_copy["rule_id"] = rule_ref.rsplit("@v", 1)[0]
        rule_copy["copied_from"] = {"task_id": source_task_id, "rule_ref": rule_ref}
        dispute = disputes.get(rule_ref)
        criteria.propose(core, new_task_id, attribute, rule_copy, by=copier,
                         dispute=dict(dispute["inspection_bundle"], copied_from=rule_ref) if dispute else None)
    return new_task_id
