"""Leaderboard Service (C12; design §4.12, `leaderboard_spec.md`).

Task-scoped, versioned snapshots. Each snapshot reports the result kind: the all-pass
set under hard rules and, when preference rules exist, the ranking under the registered
ordering method (`both_reported`). Precision is never shown without coverage and
abstention. Every state change against the parent snapshot carries a change record.
"""

from __future__ import annotations

import json
from typing import Any

from . import assessor, selection, vocab
from .canonical import sha256_hex
from .clock import utc_now
from .ids import new_id
from .runtime import Core

STATE_ORDER = {"recommended": 0, "provisional": 1, "unassessed": 2, "rejected": 3}


def member_set_hash(task_context: dict[str, Any], members: list[str] | None = None) -> str:
    """Hash of the candidates a snapshot compares: the ranked set, else the task's declared universe."""
    if members is None:
        universe = task_context.get("candidate_universe") or {}
        members = list(universe.get("members") or [])
        members += [s["candidate_ref"] for s in task_context.get("seed_candidates", [])]
    return sha256_hex(sorted(set(members)))


def leaderboard_record(core: Core, task_context: dict[str, Any], members: list[str] | None = None) -> str:
    """The open leaderboard (`lbd_`) for the task's comparability key, opening one if needed.

    The key includes a hash of the member set, because a percentile-style score is set-dependent:
    the same candidate's score moves when the set it is compared against changes, so two
    snapshots over different member sets are not comparable and must not share a leaderboard or
    exchange change records. `members` is the set actually ranked (the resolved candidates of a
    run), which is what a run-level candidate limit changes; without it the task's universe is used.
    """
    key_fields = {k: task_context.get(k) for k in ("objective_text", "mode", "evaluation_scope")}
    key_fields["required_scope"] = sorted(e.get("identifier", "") for e in task_context.get("scope_entities", [])
                                          if e.get("role") == "required")
    universe = task_context.get("candidate_universe") or {}
    key_fields["universe"] = {k: universe.get(k) for k in ("kind", "source", "as_of")}
    key_fields["member_set_hash"] = member_set_hash(task_context, members)
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
    rows = core.store.db.execute("SELECT body FROM events WHERE event_type = ? AND stream_id LIKE 'run_%' "
        "AND COALESCE(json_extract(body, '$.payload.task_id'), json_extract(body, '$.ids.task_id')) = ? "
        "ORDER BY stream_id, seq", ("leaderboard.snapshot_published", task_id))
    for (body,) in rows:
        event = json.loads(body)
        out.append(core.artifacts.payload(event["payload"]["artifact_id"]))
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


def _review_summary(rule_set: dict[str, Any]) -> dict[str, Any]:
    """Who stands behind the rules this board was built on.

    A board carries its own answer to "did a person agree to this?", because the rule set is a
    separate record a reader may never open. Rules resolved by a `machine_adjudication` are named,
    not counted away: the count alone would not say which exclusion stopped excluding.
    """
    machine = list(rule_set.get("machine_adjudicated") or [])
    expert = sorted(e["rule_ref"] for e in rule_set.get("entries", [])
                    if e.get("authority") == "human_scientific_approval")
    return {"recommended_requires_hd": True, "expert_confirmed_rules": expert, "expert_confirmed_n": len(expert),
            "machine_adjudicated_rules": machine, "machine_adjudicated_n": len(machine),
            "note": (f"{len(machine)} of this board's rules were adjudicated by an agent; no person has "
                     f"confirmed them" if machine else None)}


def build_snapshot(*, task_context: dict[str, Any], leaderboard_id: str, run_id: str, round_id: str, rule_set: dict[str, Any],
                   evidence_snapshot_id: str | None, roll_ups: dict[str, dict[str, Any]],
                   cells: dict[str, list[dict[str, Any]]], scores: dict[str, tuple[float | None, float]],
                   identities: dict[str, dict[str, Any]], parent: dict[str, Any] | None, sweep_completeness: float,
                   budget: dict[str, Any], strategy: str = "strat@v1", tool_coverage: dict[str, Any] | None = None,
                   ranking_coverage_floor: float = 0.5,
                   mandated_rule_refs: list[str] | tuple[str, ...] = (),
                   mandated_coverage_floor: float = assessor.DEFAULT_MANDATED_COVERAGE_FLOOR,
                   calibration_guard: dict[str, Any] | None = None,
                   rank_requires_mandated_coverage: bool = True, qualification_policy: str = "legacy",
                   qualifications: dict[str, dict[str, Any]] | None = None, evaluation_mode: str = "full") -> dict[str, Any]:
    # WHY the demoted kinds come from the cells rather than from the rule set's entries: the
    # calibration guard demotes a hard exclusion for this run (`controller._calibration_guard`), the
    # registry's rule is untouched, and the cells are what carry the kind this board was computed
    # with. Reading `entries[].rule_kind` here would report an all-pass set this board never applied.
    demoted = set((calibration_guard or {}).get("demoted") or {})
    kinds = ["preference" if e.get("rule_ref") in demoted else e["rule_kind"] for e in rule_set["entries"]]
    has_preferences = any(kind == "preference" for kind in kinds)
    has_hard = any(kind == "hard_exclusion" for kind in kinds)
    result_kind = vocab.require("result_kind", "both_reported" if (has_hard and has_preferences)
                               else "ranked_under_score" if has_preferences else "all_pass_set")
    entries = []
    for candidate_id, summary in roll_ups.items():
        candidate_cells = cells.get(candidate_id, [])
        score, pref_coverage = scores.get(candidate_id, (None, 0.0))
        identity = identities.get(candidate_id, {})
        # What this candidate answers of the criteria the task itself mandates
        # (`assessor.mandated_coverage`), and which of them it does not.
        own = assessor.mandated_coverage(candidate_cells, mandated_rule_refs)
        if qualification_policy == assessor.QUALIFICATION_POLICY:
            mine = [c for c in candidate_cells if c["rule_ref"] in mandated_rule_refs and c["rule_kind"] != "hard_exclusion"]
            own.update(answered_n=sum(assessor.direct_evidence(c) for c in mine),
                       coverage=sum(assessor.direct_evidence(c) for c in mine) / len(mine) if mine else None,
                       unanswered=sorted(c["attribute_ref"] for c in mine if not assessor.direct_evidence(c)))
        entries.append({
            "candidate_ref": candidate_id, "identity_labels": [identity.get("preferred_label") or identity.get("input_label")],
            "state": summary["state"], "state_reason": summary["state_reason"], "preference_score": score,
            "preference_coverage": pref_coverage, "position": None,
            "per_criterion_refs": [c["assessment_id"] for c in candidate_cells],
            "coverage": summary["hard_rule_coverage"], "missing": summary["blocking_unknowns"],
            # WHY the gate outcome is carried per candidate: the selection is two steps -- the hard
            # rules choose which candidates are eligible at all, and the preferences rank the ones
            # that are. `roll_up` computes both halves and only the state survived into the snapshot,
            # and `state` collapses them: a candidate failing a hard rule, one blocked on an absent
            # record, and one that clears every gate but carries no human signature all read
            # `provisional`. Measured on the 14 October board: 9 candidates cleared every hard rule
            # and 1,262 were blocked on an unknown oral-route record, and nothing in the entries told
            # them apart, so the pass set could not be reported at all. `clears_hard_rules` is the
            # gate's own answer; `gate_blocked_by` names what is missing when it is false.
            # Absent counts read unknown, never pass: defaulting them to zero would make a summary
            # that never reported them look like a candidate that cleared every gate (§9.2).
            "clears_hard_rules": (None if summary.get("n_fail_hard") is None
                                        or summary.get("n_unknown_hard") is None
                                  else not summary["n_fail_hard"] and not summary["n_unknown_hard"]),
            "n_fail_hard": summary.get("n_fail_hard"), "n_unknown_hard": summary.get("n_unknown_hard"),
            "gate_blocked_by": summary.get("blocking_unknowns") or [],
            # The same three things about the task's *own* criteria, in the same vocabulary: the
            # answer, the count behind it and what is missing when it is false. A candidate below the
            # floor keeps its entry, its state and its cells and is reported as ineligible for a
            # position with the criteria it is missing named -- it is not dropped, because "nobody has
            # measured this compound at four of the five required receptors" is a finding about the
            # evidence and the one thing a silent drop would hide. None where the task mandates
            # nothing or this candidate has no mandated cell: unknown, never a pass.
            "clears_mandated_criteria": (None if own["coverage"] is None
                                         else own["coverage"] >= mandated_coverage_floor),
            "n_mandated": own["n"], "n_mandated_answered": own["answered_n"],
            "mandated_coverage": own["coverage"], "mandated_blocked_by": own["unanswered"],
            # The mandated criteria the floor does not measure because they gate rather than rank
            # (`assessor.mandated_coverage`), and which of them this candidate has no value for.
            # On the entry so that the gate's effect stays visible where its position is decided: a
            # candidate ranked with `mandated_gates_unanswered` non-empty is one the gate is holding
            # off a recommendation, not one that answered everything the task asked.
            "mandated_gates": own["gates"], "mandated_gates_unanswered": own["gates_unanswered"],
            "counter_evidence_refs": sorted({r for c in candidate_cells for r in c["conflicting_claim_refs"]}),
            "measured_vs_predicted_counts": {kind: sum(c["value_kind"] == kind for c in candidate_cells)
                                             for kind in ("measured", "curated", "derived", "predicted")},
            # Which of this candidate's values stand in for a measurement it has none of
            # (`determination_basis_precedence`). Beside the counts above rather than inside them:
            # the counts say what kind of value each cell carried, this says which cells carried the
            # weaker of the two bases their attribute accepts because the stronger one was silent.
            "gap_filled_criteria": summary.get("gap_filled_criteria") or [],
            "determination_bases": summary.get("determination_bases") or {},
            "review_status": "none", "verdicts": {c["attribute_ref"]: c["verdict"] for c in candidate_cells},
        })
    for entry in entries:
        notes = []
        if qualification_policy == assessor.QUALIFICATION_POLICY:
            q = (qualifications or {}).get(entry["candidate_ref"], {"state": "not_ready", "qualified": False})
            entry.update(qualification=q, qualification_state=q["state"], qualified=q["qualified"],
                         direct_preference_coverage=entry["preference_coverage"],
                         cell_availability={c["attribute_ref"]: c.get("availability", "unavailable")
                                            for c in cells.get(entry["candidate_ref"], [])})
            entry["clears_hard_rules"] = (q.get("applicable_hard_count", 0) > 0 and
                not q.get("blocking_hard_rule_refs") and not q.get("failed_hard_rule_refs"))
            entry["gate_blocked_by"] = q.get("blocking_hard_rule_refs", []) + q.get("failed_hard_rule_refs", [])
            if not q["qualified"]:
                entry["preference_score"] = None
                notes.append(f"qualification: {q['state']}")
        if entry["clears_mandated_criteria"] is False:
            notes.append(f"{entry['n_mandated'] - entry['n_mandated_answered']} of the {entry['n_mandated']} criteria "
                         f"the task itself requires are unanswered ({', '.join(entry['mandated_blocked_by'])}); "
                         f"{entry['mandated_coverage']:.2f} answered, floor {mandated_coverage_floor:.2f}")
        if entry["preference_score"] is not None and entry["preference_coverage"] < ranking_coverage_floor:
            notes.append(f"too little preference evidence to rank (coverage {entry['preference_coverage']:.2f} "
                         f"below {ranking_coverage_floor:.2f})")
        if notes:
            entry["rank_note"] = "; ".join(notes)
    # A legacy board gates positions on mandated coverage. A profile may register rank separately
    # from that eligibility reading; the coverage, qualification and blocking unknowns remain.
    # `is not False` keeps an absent mandated population from reading as a failure.
    ranked = [e for e in entries if e["state"] in ("recommended", "provisional") and e["preference_score"] is not None
              and (qualification_policy != assessor.QUALIFICATION_POLICY or e.get("qualified") is True)
              and e["preference_coverage"] >= ranking_coverage_floor
              and (not rank_requires_mandated_coverage or e["clears_mandated_criteria"] is not False)]
    ranked.sort(key=lambda e: (-e["preference_score"], STATE_ORDER[e["state"]], -e["preference_coverage"], -(e["coverage"] or 0),
                               e["candidate_ref"]))
    if has_preferences:
        for position, entry in enumerate(ranked, 1):
            entry["position"] = position
    entries.sort(key=lambda e: (e["position"] is None, e["position"] or 0, STATE_ORDER[e["state"]], e["candidate_ref"]))
    admitted = [e for e in entries if e["state"] == "recommended"]
    all_cells = [c for cs in cells.values() for c in cs]
    applicable = [c for c in all_cells if c["verdict"] != "inapplicable"]
    value_bearing = [c for c in applicable if c["verdict"] in ("pass", "fail", "available")]
    abstentions: dict[str, int] = {}
    for e in entries:
        if e["state"] in ("provisional", "unassessed"):
            key = e["state_reason"].split(":")[0]
            abstentions[key] = abstentions.get(key, 0) + 1
    abstention_reason = None
    if not ranked and not admitted:
        # Nothing to recommend and nothing rankable: the snapshot says so with a reason, rather
        # than reporting an empty ranking that reads like a result (design §4.12).
        if entries and all(e["state"] == "rejected" for e in entries):
            abstention_reason = "all_candidates_excluded"
        elif not value_bearing:
            abstention_reason = "evidence_unavailable"
        elif any(c["verdict"] == "unknown_conflicted" for c in applicable):
            abstention_reason = "unresolved_conflicts"
        else:
            abstention_reason = "insufficient_coverage"
        result_kind = vocab.require("result_kind", "no_recommendation")
        vocab.require("abstention_reason", abstention_reason)
    snapshot = {
        "snapshot_id": None, "task_id": task_context["task_context_id"],
        "task_context_id@v": f"{task_context['task_context_id']}@v{task_context['version']}",
        "run_id": run_id, "round_id": round_id, "rules@v": rule_set["rule_set_ref"], "strat@v": strategy,
        "evidence_snapshot_id": evidence_snapshot_id, "result_kind": result_kind,
        "no_recommendation": result_kind == "no_recommendation", "abstention_reason": abstention_reason,
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
                            # Counted from the condition and not from the presence of a `rank_note`,
                            # which now also carries the mandated floor's reason: the two numbers
                            # answer different questions and a reader comparing boards needs each of
                            # them to go on meaning what it meant.
                            "unranked_for_coverage": sum(1 for e in entries if e["preference_score"] is not None
                                                         and e["preference_coverage"] < ranking_coverage_floor),
                            # The floor over the task's own criteria, and how many candidates it
                            # holds off the ranking. Recorded whether or not it excluded anybody, so
                            # the number the board was built with is reproducible from the board.
                            "mandated_coverage_floor": mandated_coverage_floor,
                            "rank_requires_mandated_coverage": rank_requires_mandated_coverage,
                            "mandated_rule_refs": sorted(mandated_rule_refs),
                            "ineligible_for_mandated_coverage": sum(1 for e in entries
                                                                    if e["clears_mandated_criteria"] is False),
                            "eligible_on_mandated_criteria": sum(1 for e in entries
                                                                 if e["clears_mandated_criteria"] is True),
                            # How many ranked candidates hold a position while a mandated *gate* is
                            # unanswered for them. The floor does not measure gates
                            # (`assessor.mandated_coverage`), which is a deliberate decision; this
                            # is the number that decision costs, stated on every board rather than
                            # left to be recomputed from the entries.
                            "ranked_with_a_mandated_gate_unanswered": sum(
                                1 for e in entries if e["position"] and e.get("mandated_gates_unanswered")),
                            "budget": budget},
        "interaction_estimate_provider": "none", "human_review_summary": _review_summary(rule_set),
        # What the calibration guard measured for this board, whether or not it demoted anything: the
        # share of the task's mandated population each hard exclusion removed. Always present when
        # the run computed it, because "every gate was checked and none was over the limit" is a
        # finding a reader needs as much as a demotion is (§9.2: an absent number reads as unknown).
        "calibration_guard": calibration_guard,
        "published_at": utc_now(),
    }
    if qualification_policy == assessor.QUALIFICATION_POLICY:
        skipped = [c for c in all_cells if c.get("not_assessed_reason") == "skipped_after_rejection"]
        missing = [c for c in all_cells if c["verdict"] in ("unknown_missing", "unknown_conflicted")]
        readiness = "ready" if any(q.get("applicable_hard_count", 0) and q.get("verified_hard_count", 0)
                                    for q in (qualifications or {}).values()) else "not_ready"
        snapshot.update(qualification_policy=qualification_policy, evaluation_mode=evaluation_mode, readiness=readiness,
                        qualified_count=sum(e.get("qualified", False) for e in entries),
                        all_pass_count=sum(e.get("qualified", False) for e in entries))
        snapshot["reporting_tuple"].update(qualification_policy=qualification_policy, evaluation_mode=evaluation_mode,
            normalization_population="qualified_only", readiness=readiness, skipped_after_rejection_n=len(skipped),
            missing_or_conflicted_n=len(missing), error_n=sum(bool(c.get("tool_error_ref")) for c in all_cells),
            assessed_cell_n=sum(c["verdict"] != "not_assessed" for c in all_cells),
            recorded_cell_n=len(all_cells), qualified_n=snapshot["qualified_count"],
            assessment_completeness=sum(c["verdict"] != "not_assessed" for c in all_cells) / len(all_cells) if all_cells else 0.0,
            direct_coverage_fraction=sum(assessor.direct_evidence(c) for c in applicable) / len(applicable) if applicable else 0.0)
        if readiness == "not_ready":
            snapshot["result_kind"] = "no_recommendation"
            snapshot["abstention_reason"] = "qualification_not_ready"
        selection_counts = dict.fromkeys(selection.SELECTION_DECISIONS, 0)
        for entry in entries:
            assessments = {c["rule_ref"]: c for c in cells.get(entry["candidate_ref"], [])}
            rules = {ref: {"attribute_ref": cell.get("attribute_ref"),
                           "name": cell.get("criterion_name") or ref} for ref, cell in assessments.items()}
            reading = selection.eligibility_reading(entry, rules, rule_assessments=assessments)
            entry["selection"] = selection.selection_reading(reading)
            selection_counts[entry["selection"]["decision"]] += 1
        snapshot.update(selection_policy=selection.SELECTION_POLICY,
                        selection_counts={**selection_counts, "total": len(entries)})
    return snapshot
