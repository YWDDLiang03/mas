"""Registered case inheritance and shortlist stages (design §6.6 feasibility, ADR-33).

Full inheritance retains the complete universe and registry for a descriptive assisted reading,
with pinned provenance and a fresh case. It does not make another independent validation.

When a full sweep of every rule is infeasible (for example literature-evaluated rules over
thousands of candidates), the operator registers a shortlist rule: the top K candidates of a
published snapshot, ties at the boundary included. The shortlist becomes a derived task
(`derived_from_task_id`) that carries the source snapshot, the rule, and copies of the
registered criteria with links to their source versions; hard and disputed rules are raised
again for an expert. Nothing about the shortlist rule refers to any particular candidate.
"""

from __future__ import annotations

from typing import Any

from . import criteria, criteria_export, leaderboard, recovery, review, task as task_mod
from .canonical import sha256_hex
from .ids import new_id
from .journal import actor as make_actor
from .runtime import Core


def inherit_task(core: Core, source_task_id: str, *, by: dict[str, Any], reason: str,
                 objective_text: str | None = None, source_at_seq: int | None = None) -> str:
    """Create a descriptive inherited case with the complete source scope and registry.

    Source records and all their versions keep their original identities and provenance. The
    copying actor is recorded separately; no source approval, adjudication or expert decision is
    replayed as a decision on the new task. A new freeze remains the caller's next step. Only
    content-free case headers are read here: the historical list and its mapping stay sealed.
    """
    if not reason.strip():
        raise ValueError("an inherited reading needs a stated reason")
    pinned_core, source_seq = criteria_export.pinned(core, source_task_id, source_at_seq)
    events = list(pinned_core.journal.replay(source_task_id))
    source = task_mod.get(pinned_core, source_task_id)
    registry = criteria_export._registry(pinned_core, source_task_id)
    context_event = next(event for event in reversed(events) if event.event_type == "task.version_recorded")

    def reference(event):
        artifact_id = event.payload["artifact_id"]
        return {"artifact_id": artifact_id,
                "artifact_sha256": criteria_export._artifact_hash(core, artifact_id),
                "seq": event.seq, "recorded_at": event.recorded_at}

    source_case = recovery.case_stream(pinned_core, source_task_id)
    # The public headers retain prior failures and results without opening an evaluator artifact.
    previous_readings = []
    for event in core.journal.replay(source_case):
        if event.event_type == "evaluation.recorded" and event.payload.get("record_kind") == recovery.COMPARISON_KIND:
            previous_readings.append(dict(reference(event), task_id=source_task_id, case_ref=source_case,
                                          comparison_id=event.payload["comparison_id"],
                                          intake_id=event.payload.get("intake_id"),
                                          counts=event.payload.get("counts"), rates=event.payload.get("rates")))
    source_intake = recovery.intake_reference(pinned_core, source_task_id)
    snapshot = {
        "schema_version": 1, "kind": "case_inheritance_snapshot", "source_task_id": source_task_id,
        "source_task_context_ref": f"{source_task_id}@v{source['version']}",
        "source_context": reference(context_event), "source_case_ref": source_case,
        "source_at_seq": source_seq,
        "source_journal_pin": {"seq": events[-1].seq, "event_id": events[-1].event_id,
                               "event_sha256": sha256_hex(events[-1].to_record())},
        "candidate_scope": {key: source.get(key) for key in
                            ("candidate_universe", "seed_candidates", "scope_entities", "evaluation_scope")},
        "criteria": [{key: entry[key] for key in ("ref", "kind", "base_id", "version", "artifact_id", "seq")}
                     | {"artifact_sha256": criteria_export._artifact_hash(core, entry["artifact_id"])}
                     for entry in registry.values()],
        "source_rule_sets": [dict(reference(event), rule_set_ref=event.payload["rule_set_ref"])
                             for event in events if event.event_type == "criterion.version_approved"],
        "source_lifecycle": [{"seq": event.seq, "event_id": event.event_id,
                              "payload_sha256": event.payload_hash, "artifact_id": event.payload.get("artifact_id")}
                             for event in events if event.event_type == "criterion.change_recorded"],
        "source_boards": [dict(reference(event), stream_id=event.stream_id,
                               snapshot_id=event.payload["snapshot_id"])
                          for event in core.journal.of_type("leaderboard.snapshot_published")
                          if event.payload.get("task_id") == source_task_id],
        "source_intake": None if source_intake is None else {
            key: source_intake.get(key) for key in ("intake_id", "item_count", "content_sha256", "recorded_at")},
        "prior_recovery_readings": previous_readings,
    }
    snapshot_id = core.artifacts.put("case_inheritance_snapshot", snapshot)
    latest_attributes = {entry["base_id"]: entry for entry in registry.values() if entry["kind"] == "attribute"}
    latest_rules = {entry["base_id"]: entry for entry in registry.values() if entry["kind"] == "rule"}
    spec = {key: value for key, value in source.items()
            if key not in ("task_context_id", "version", "supersedes", "created_by", "case_ref", "inheritance")}
    if objective_text is not None:
        spec["objective_text"] = objective_text
    spec["case_ref"] = new_id("case")
    spec["derived_from_task_id"] = source_task_id
    spec["inheritance"] = {
        "kind": "full_case", "reading_kind": "descriptive_inherited", "recovery_view": "assisted",
        "is_independent_validation": False, "reason": reason,
        "source_task_id": source_task_id, "source_task_context_ref": snapshot["source_task_context_ref"],
        "source_case_ref": source_case, "source_at_seq": source_seq,
        "source_snapshot_artifact_id": snapshot_id,
        "source_snapshot_sha256": criteria_export._artifact_hash(core, snapshot_id),
        "source_criteria_count": len(latest_attributes), "source_rule_count": len(latest_rules),
        "candidate_scope": "full_source_universe", "prior_recovery_readings": previous_readings,
    }
    new_task_id, _ = task_mod.record_version(core, spec, by=by)
    copier = make_actor("system", "case-inheritance", "criterion_copy")
    for entry in registry.values():
        copied_from = {"task_id": source_task_id, f"{entry['kind']}_ref": entry["ref"],
                       "artifact_id": entry["artifact_id"],
                       "artifact_sha256": criteria_export._artifact_hash(core, entry["artifact_id"]),
                       "source_at_seq": source_seq}
        record = dict(entry["record"], copied_from=copied_from, inherited_by=copier)
        artifact_id = core.artifacts.put(entry["kind"], record)
        core.journal.append(new_task_id, "criterion.version_proposed", actor=copier,
                            ids={"task_id": new_task_id},
                            payload={"kind": entry["kind"], "id": entry["base_id"],
                                     "version": entry["version"], "artifact_id": artifact_id,
                                     "copied_from": copied_from},
                            artifact_links=[{"kind": entry["kind"], "id": artifact_id, "version": entry["version"]}],
                            summary=f"inherited {entry['ref']} from {source_task_id} seq {source_seq}")
    # Pool reductions and software collapses are scientific lineage, not approvals. Carry their
    # recorded status so merged-away criteria cannot quietly become separate scoring quantities.
    for event in events:
        if event.event_type == "criterion.change_recorded":
            core.journal.append(new_task_id, event.event_type, actor=copier, ids={"task_id": new_task_id},
                                payload=dict(event.payload, inherited_from={"task_id": source_task_id,
                                             "seq": event.seq, "event_id": event.event_id,
                                             "payload_sha256": event.payload_hash, "actor": event.actor}),
                                artifact_links=event.artifact_links,
                                summary=f"inherited criterion lifecycle from {source_task_id} seq {event.seq}")
    restore_inherited_reviews(core, new_task_id)
    return new_task_id


def restore_inherited_reviews(core: Core, task_id: str, *, rule_refs: list[str] | None = None) -> list[str]:
    """Restore missing inherited review requests without importing source decision authority.

    Also repairs cases created before resolved source requests were re-raised. Exact latest rule
    versions must still match the inherited version: a source revision withdrawing a cutoff does
    not inherit the old cutoff's request. Any existing local request or decision is left in place.
    Returns only the ids of newly created requests.
    """
    context = task_mod.get(core, task_id)
    inheritance = context.get("inheritance") or {}
    if inheritance.get("kind") != "full_case":
        raise ValueError("review restoration requires a full inherited case")
    source_task_id = inheritance["source_task_id"]
    pinned_core, _ = criteria_export.pinned(core, source_task_id, inheritance["source_at_seq"])
    registry = criteria_export._registry(pinned_core, source_task_id)
    latest_rules = {entry["base_id"]: entry for entry in registry.values() if entry["kind"] == "rule"}
    local_rules = {entry["base_id"]: entry for entry in criteria_export._registry(core, task_id).values()
                   if entry["kind"] == "rule"}
    source_queue = review.items(pinned_core, [source_task_id])
    local_queue = review.items(core, [task_id])
    copier = make_actor("system", "case-inheritance", "criterion_copy")
    created = []
    for base_id, entry in latest_rules.items():
        if rule_refs is not None and entry["ref"] not in rule_refs:
            continue
        local_rule = local_rules.get(base_id)
        if not local_rule or local_rule["ref"] != entry["ref"]:
            continue
        if any(item["subject"].get("id") == entry["ref"] for item in local_queue.values()):
            continue
        rule = entry["record"]
        attribute = registry[rule["attribute_ref"]]["record"]
        # A same-version interpretation grant leaves a resolved queue item rather than an
        # intrinsic expert_set field. Its source authority still has to be granted on this case.
        disputes = [item for item in source_queue.values()
                    if item["subject"].get("id") == entry["ref"] and item["state"] in
                    ("open", "in_review", "machine_adjudicated", "decided")]
        owed = criteria.authority_requirements(rule, attribute)
        if not disputes and not owed:
            continue
        for item in disputes or [None]:
            created.append(review.request(core, task_id,
                           subject={"kind": "rule_version", "id": entry["ref"], "version": entry["version"],
                                    "attribute_ref": rule["attribute_ref"]},
                           why_expert_required=item["why_expert_required"] if item else
                           "; ".join(requirement["detail"] for requirement in owed), requested_by=copier,
                           inspection_bundle=dict((item or {}).get("inspection_bundle") or {},
                                                  inherited_from_task_id=source_task_id,
                                                  source_rule_ref=entry["ref"],
                                                  source_review_item_id=(item or {}).get("item_id"),
                                                  source_review_state=(item or {}).get("state"),
                                                  source_adjudication_id=(item or {}).get("adjudication_id"),
                                                  source_decision_id=(item or {}).get("decision_id"),
                                                  source_authority_carried=False)))
    return created


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
    spec = {k: v for k, v in source.items() if k not in
            ("task_context_id", "version", "supersedes", "unknowns", "created_by", "case_ref", "inheritance")}
    spec["candidate_universe"] = {
        "kind": "enumerated_set", "members": members, "size_if_known": len(members),
        "access_path": source.get("candidate_universe", {}).get("access_path"),
        "source": f"registered shortlist of {snapshot['snapshot_id']}",
        "shortlist_rule": {"kind": "top_k_by_position", "k": top_k, "ties_at_boundary": "included",
                           "source_snapshot_id": snapshot["snapshot_id"], "source_rules": snapshot["rules@v"],
                           "selected": len(members)}}
    spec["derived_from_task_id"] = source_task_id
    spec["case_ref"] = new_id("case")
    spec["inheritance"] = {
        "kind": "shortlist", "reading_kind": "descriptive_inherited", "recovery_view": "assisted",
        "is_independent_validation": False, "source_task_id": source_task_id,
        "source_at_seq": core.journal.last_seq(source_task_id),
        "source_case_ref": recovery.case_stream(core, source_task_id),
        "source_board_snapshot_id": snapshot["snapshot_id"],
        "candidate_scope": "registered_shortlist",
    }
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
