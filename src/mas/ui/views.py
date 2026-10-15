"""Workbench views (`ui_ux_spec.md` §2, §15.2): one dictionary per screen, folded from the journal.

Each view calls the core functions the terminal client calls — `leaderboard.snapshots`,
`projection.progress`, `review.items`, `pool.fold`, `sr_stage.rationale_of`,
`mechanism.narrative_of`, `Config.layer_record` — and arranges the result as the screen map of
§2, labelled through the registered vocabularies, so neither surface carries a label, a state or
a count of its own (parity rule §15.2.1). One dictionary is both the page and its JSON twin, so
the two cannot drift.

Nothing here writes: the store root is opened read-only, and a view that cannot find its record
raises `NotFound` rather than rendering an empty screen that reads like an answer. A page is one
fold taken when it was rendered and says so (`as_of`, `freshness`); it does not follow a
running run (§1.6).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from mas.core import adjudication, criteria, leaderboard, ledger, mechanism, projection, sr_stage, vocab
from mas.core import pool as pool_mod, review as review_mod, task as task_mod
from mas.core.clock import utc_now
from mas.core.config import Config
from mas.core.runtime import Core

READ_ONLY = "read-only: this surface records nothing; runs are started and expert decisions made on the terminal"
FRESHNESS = "static: this page is one fold of the journal, taken when it was rendered; reload to fold again"
TERMINAL_DECISION = "the decision is made on the terminal, not here"
NO_PERSON_CONFIRMED = ("these items were resolved by an agent so the run could proceed; no person confirmed them, "
                       "and every rule set and board they reach says so")
SECRET_MARK = "api_key"
MAX_ROWS = 200
POOL_ORDER = ("promoted", "candidate", "needs_refine", "deferred_next_round", "merged_away", "withdrawn", "filtered_out")
RUN_STATE_KINDS = ("run.created", "run.started", "run.paused", "run.resumed", "run.cancelled", "run.completed",
                   "run.unresolved", "run.failed")


class NotFound(LookupError):
    """A page asked the store root for a record it does not hold."""


def link(path: str, **query: str) -> str:
    return f"{path}?{urlencode(query)}" if query else path


def _frame(page: str, fields: dict[str, Any]) -> dict[str, Any]:
    return {"page": page, "surface": READ_ONLY, "freshness": FRESHNESS, "as_of": utc_now(), **fields}


def _label(domain: str, value: str | None) -> str | None:
    return vocab.label(domain, value) if value else None


def _task(core: Core, task_id: str) -> dict[str, Any]:
    try:
        return task_mod.get(core, task_id)
    except KeyError:
        raise NotFound(f"no task {task_id} in this store root") from None


def _snapshots(core: Core, task_id: str, snapshot_id: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    published = leaderboard.snapshots(core, task_id)
    if not published:
        raise NotFound(f"no leaderboard snapshot has been published for {task_id}")
    if snapshot_id is None:
        return published[-1], published
    chosen = next((s for s in published if s["snapshot_id"] == snapshot_id), None)
    if chosen is None:
        raise NotFound(f"{task_id} has no snapshot {snapshot_id}")
    return chosen, published


def _rule_set(core: Core, task_id: str, ref: str | None) -> dict[str, Any]:
    try:
        return criteria.rule_set(core, task_id, ref)
    except (KeyError, StopIteration):
        return {}


def run_states(core: Core) -> dict[str, dict[str, Any]]:
    """Execution state of every run in the root, from the state-bearing run events alone."""
    latest: dict[str, tuple[int, dict[str, Any]]] = {}
    for kind in RUN_STATE_KINDS:
        for event in core.journal.of_type(kind, "run_"):
            if not event.state_to:
                continue
            seen = latest.get(event.stream_id)
            if seen is None or event.seq > seen[0]:
                latest[event.stream_id] = (event.seq, {
                    "state": event.state_to, "state_label": _label("execution", event.state_to),
                    "termination_reason": event.termination_reason,
                    "termination_reason_label": _label("termination_reason", event.termination_reason),
                    "state_changed_at": event.recorded_at})
    return {run_id: row for run_id, (_seq, row) in latest.items()}


def _binding(core: Core, run_id: str) -> dict[str, Any]:
    created = core.journal.replay(run_id, 1, 1)
    if not created or created[0].event_type != "run.created":
        return {}
    return dict(core.artifacts.payload(created[0].payload["binding_artifact_id"]),
                task_id=created[0].payload["task_id"])


def _run_row(core: Core, run_id: str, states: dict[str, dict[str, Any]]) -> dict[str, Any]:
    binding = _binding(core, run_id)
    purpose = binding.get("run_purpose", "sweep")
    unstated = {"state": None, "state_label": None, "termination_reason": None, "termination_reason_label": None,
                "state_changed_at": None}
    return {"run_id": run_id, "task_id": binding.get("task_id"), "run_purpose": purpose,
            "run_purpose_label": _label("run_purpose", purpose), "chain_id": binding.get("chain_id"),
            "continues_run_id": binding.get("continues_run_id"),
            "continuation_kind": binding.get("continuation_kind"),
            "continuation_kind_label": _label("continuation_kind", binding.get("continuation_kind")),
            "rules@v": binding.get("rules@v"), "bound_at": binding.get("bound_at"),
            **states.get(run_id, unstated), "last_seq": core.journal.last_seq(run_id),
            "run": link("/run", run=run_id)}


def tasks_and_runs(core: Core) -> dict[str, Any]:
    """The task list and the runs over them, grouped into their chains (§2 screen map, §16.1)."""
    published: dict[str, list[str]] = {}
    for event in core.journal.of_type("leaderboard.snapshot_published", "run_"):
        published.setdefault(event.payload["task_id"], []).append(event.payload["snapshot_id"])
    tasks = []
    for context in task_mod.list_tasks(core):
        task_id = context["task_context_id"]
        universe = context.get("candidate_universe") or {}
        tasks.append({"task_id": task_id, "version": context["version"], "group_id": context.get("group_id"),
                      "mode": context["mode"], "objective_text": context["objective_text"],
                      "universe_size": universe.get("size_if_known") or len(universe.get("members") or []),
                      "seed_candidates": len(context.get("seed_candidates") or []),
                      "blocking_unknowns": len(task_mod.blocking_unknowns(context)),
                      "snapshots": len(published.get(task_id, [])),
                      "leaderboard": link("/leaderboard", task=task_id), "pool": link("/pool", task=task_id)})
    states = run_states(core)
    runs = [_run_row(core, run_id, states) for run_id in core.journal.streams("run_")]
    chains: dict[str, dict[str, Any]] = {}
    for row in runs:
        chain = chains.setdefault(row["chain_id"] or row["run_id"],
                                  {"chain_id": row["chain_id"], "task_id": row["task_id"], "rounds": 0, "runs": []})
        chain["rounds"] += 1
        chain["runs"].append({key: row[key] for key in ("run_id", "run_purpose_label", "continuation_kind_label",
                                                        "continues_run_id", "state_label", "run")})
    return _frame("tasks and runs", {
        "store_root": str(core.store.root), "tasks": tasks, "tasks_n": len(tasks), "runs": runs, "runs_n": len(runs),
        "chains": sorted(chains.values(), key=lambda chain: str(chain["chain_id"])),
        "review_queue": link("/review"), "settings": link("/settings")})


def board(core: Core, task_id: str, *, snapshot_id: str | None = None, top: int = MAX_ROWS) -> dict[str, Any]:
    """One leaderboard snapshot: ranks, scores, coverage, its acceptance label, what was rankable (§11)."""
    context = _task(core, task_id)
    snapshot, published = _snapshots(core, task_id, snapshot_id)
    entries = snapshot["candidate_entries"]
    ranked = [entry for entry in entries if entry.get("position")]
    rules = _rule_set(core, task_id, snapshot["rules@v"])
    reported = snapshot["reporting_tuple"]
    method = snapshot.get("ordering_method") or {}
    rows = [{"position": entry["position"], "candidate_ref": entry["candidate_ref"],
             "label": (entry["identity_labels"] or [None])[0], "state": entry["state"],
             "state_label": _label("candidate", entry["state"]), "score": entry["preference_score"],
             "preference_coverage": entry["preference_coverage"], "hard_rule_coverage": entry["coverage"],
             "missing": entry["missing"], "state_reason": entry["state_reason"],
             # Whether the task's own criteria have been answered for this candidate, and which of
             # them have not: a row with no position is either unrankable for want of scoring inputs
             # or ineligible because the task's requirement is unmeasured, and those are different
             # findings about different evidence.
             "clears_mandated_criteria": entry.get("clears_mandated_criteria"),
             "mandated_coverage": entry.get("mandated_coverage"),
             "mandated_blocked_by": entry.get("mandated_blocked_by") or [],
             # The mandated gates the floor does not measure, and those this candidate has no value
             # for: a row may hold a position and still be held off a recommendation by one of them,
             # and the row has to say which rather than leave the two readings of a position open.
             "mandated_gates_unanswered": entry.get("mandated_gates_unanswered") or [],
             "rank_note": entry.get("rank_note"), "review_status": _label("review", entry["review_status"]),
             "candidate": link("/candidate", task=task_id, id=entry["candidate_ref"])}
            for entry in entries[:top]]
    return _frame("leaderboard", {
        "task_id": task_id, "objective_text": context["objective_text"], "snapshot_id": snapshot["snapshot_id"],
        "published_at": snapshot["published_at"], "run_id": snapshot["run_id"],
        "leaderboard_id": snapshot["leaderboard_id"], "parent_snapshot_id": snapshot["parent_snapshot_id"],
        "rules@v": snapshot["rules@v"], "evidence_snapshot_id": snapshot["evidence_snapshot_id"],
        "result_kind": snapshot["result_kind"], "result_kind_label": _label("result_kind", snapshot["result_kind"]),
        "abstention_reason": snapshot["abstention_reason"],
        "abstention_reason_label": _label("abstention_reason", snapshot["abstention_reason"]),
        "acceptance_label": rules.get("acceptance_label"),
        "acceptance_label_shown": _label("acceptance_label", rules.get("acceptance_label")),
        "acceptance_reasons": rules.get("acceptance_reasons") or [],
        "human_review_summary": snapshot.get("human_review_summary") or {},
        "machine_adjudicated_rules": [{"rule_ref": entry["rule_ref"], "rule_kind": entry["rule_kind"],
                                       "authority": _label("decision_authority", entry.get("authority"))}
                                      for entry in rules.get("entries", [])
                                      if entry.get("authority") == "machine_adjudication"],
        "ordering_method": {key: method.get(key) for key in ("kind", "expression_text", "provenance",
                                                             "expression_ref", "tie_break", "fitter_version")},
        "rankable_set_size": len(ranked), "members_compared": len(entries),
        "all_pass_count": snapshot["all_pass_count"], "admitted_n": reported["admitted_n"],
        "precision_among_admitted": reported["precision_among_admitted"],
        "coverage_fraction": reported["coverage_fraction"], "sweep_completeness": reported["sweep_completeness"],
        "ranking_coverage_floor": reported["ranking_coverage_floor"],
        "unranked_for_coverage": reported["unranked_for_coverage"],
        # The floor over the task's own mandated criteria and what it held off the ranking. `.get`,
        # because a board published before this floor existed carries neither number, and an absent
        # one reads as unknown rather than as nothing excluded (§9.2).
        "mandated_coverage_floor": reported.get("mandated_coverage_floor"),
        "mandated_criteria": reported.get("mandated_rule_refs") or [],
        "eligible_on_mandated_criteria": reported.get("eligible_on_mandated_criteria"),
        "ineligible_for_mandated_coverage": reported.get("ineligible_for_mandated_coverage"),
        "ranked_with_a_mandated_gate_unanswered": reported.get("ranked_with_a_mandated_gate_unanswered"),
        "abstention_n_by_reason": reported["abstention_n_by_reason"], "budget": reported["budget"],
        "rows": rows, "rows_shown": len(rows), "rows_not_shown": max(0, len(entries) - len(rows)),
        "snapshots": [{"snapshot_id": s["snapshot_id"], "published_at": s["published_at"],
                       "leaderboard": link("/leaderboard", task=task_id, snapshot=s["snapshot_id"])}
                      for s in published],
        "run": link("/run", run=snapshot["run_id"]), "pool": link("/pool", task=task_id)})


def _claim_row(claim: dict[str, Any]) -> dict[str, Any]:
    location = claim.get("location") or {}
    return {"claim_id": claim["claim_id"], "source_ref": claim.get("source_ref"),
            "attribute_ref": claim.get("attribute_ref"), "location_kind": location.get("location_kind"),
            "locator": location.get("locator_value"), "section_path": location.get("section_path") or [],
            "quote": location.get("quoted_span"), "statement": claim.get("normalized_statement"),
            "value": claim.get("value"), "unit": claim.get("unit"),
            "determination_basis": claim.get("determination_basis"), "evidence_kind": claim.get("evidence_kind"),
            "span_checked_against_source": location.get("span_checked_against_source")}


def _mechanism_block(narrative: dict[str, Any] | None) -> dict[str, Any]:
    """The narrative as it was recorded, or `unexplained` with the reason there is none (design §5.7)."""
    if narrative is None:
        return {"explanation_status": "unexplained", "sentences": [], "dropped_sentences": [],
                "unexplained_reason": "no mechanism note has been written for this candidate; write one with "
                                      "`mas candidate explain TASK CANDIDATE`"}
    return {"explanation_status": narrative["explanation_status"],
            "unexplained_reason": narrative.get("unexplained_reason"),
            "claims_offered": len(narrative["claims_offered"]), "model_id": narrative.get("model_id"),
            "is_evidence": narrative["is_evidence"], "enters_scoring": narrative["enters_scoring"],
            "sentences": [{"text": sentence["text"],
                           "claims": [{"claim_id": claim["claim_id"], "source_ref": claim.get("source_ref"),
                                       "locator": claim.get("locator"), "quote": claim.get("quote"),
                                       "determination_basis": claim.get("determination_basis"),
                                       "conditions": claim.get("conditions") or {},
                                       "references": claim.get("references") or []}
                                      for claim in sentence["claims"]]}
                          for sentence in narrative["sentences"]],
            "dropped_sentences": [{"text": dropped["text"],
                                   "problems": [f"{problem['reason']} {problem['detail']}".strip()
                                                for problem in dropped["problems"]]}
                                  for dropped in narrative["dropped_sentences"]]}


def _rationale_block(rationale: dict[str, Any] | None) -> dict[str, Any]:
    """Why this candidate scored what it scored: each term with its value, coefficient and share."""
    if rationale is None:
        return {"ordering_method": "weighted_preference", "terms": [], "terms_missing": [],
                "note": "no fitted expression was installed for this run, so the score has no per-term rationale"}
    return {"ordering_method": "symbolic_expression", "score": rationale["score"], "coverage": rationale["coverage"],
            "intercept": rationale["intercept"],
            "terms": [{key: term[key] for key in ("term", "features", "feature_values", "value", "coefficient",
                                                  "contribution", "share", "direction", "grounding", "claim_refs")}
                      for term in rationale["terms"]],
            "terms_missing": [{key: term[key] for key in ("term", "features", "missing_features")}
                              for term in rationale["terms_missing"]]}


def _cells(core: Core, run_id: str, candidate_ref: str) -> list[dict[str, Any]]:
    rows = []
    for event in core.journal.replay(run_id):
        if event.event_type != "candidate.assessed" or event.payload["candidate_ref"] != candidate_ref:
            continue
        cell = core.artifacts.payload(event.payload["artifact_id"])
        reason = core.artifacts.payload(event.payload["reason_artifact_id"])
        rows.append({"attribute_ref": cell["attribute_ref"], "rule_ref": cell["rule_ref"],
                     "rule_kind": cell["rule_kind"], "verdict": cell["verdict"],
                     "verdict_label": _label("verdict", cell["verdict"]), "value": cell["value"],
                     "unit": cell["unit"], "value_kind": _label("value_kind", cell["value_kind"]),
                     "determination_basis": cell["determination_basis"], "reason_text": reason["reason_text"],
                     # Whether this value is a gap-fill: the attribute accepts a stronger basis and
                     # this candidate had nothing on it (`determination_basis_precedence`). None on
                     # every cell whose attribute ranks no bases, so a surface can tell the two apart.
                     "basis_precedence": cell.get("determination_basis_precedence"),
                     "evidence": cell["value_source_claim_refs"],
                     "counter_evidence": cell["conflicting_claim_refs"]})
    return rows


def candidate(core: Core, task_id: str, wanted: str, *, snapshot_id: str | None = None) -> dict[str, Any]:
    """One candidate of one snapshot: its score rationale, claims, verdicts and mechanism note (§7, §8)."""
    _task(core, task_id)
    snapshot, _published = _snapshots(core, task_id, snapshot_id)
    entry = next((e for e in snapshot["candidate_entries"]
                  if e["candidate_ref"] == wanted
                  or wanted.lower() in ((e["identity_labels"] or [""])[0] or "").lower()), None)
    if entry is None:
        raise NotFound(f"{wanted} is not in snapshot {snapshot['snapshot_id']}")
    run_id, candidate_ref = snapshot["run_id"], entry["candidate_ref"]
    claims = ledger.claims(core, [run_id, task_id], candidate_ref=candidate_ref)
    return _frame("candidate", {
        "task_id": task_id, "candidate_ref": candidate_ref, "label": (entry["identity_labels"] or [None])[0],
        "snapshot_id": snapshot["snapshot_id"], "run_id": run_id,
        "state": entry["state"], "state_label": _label("candidate", entry["state"]), "position": entry["position"],
        "score": entry["preference_score"], "preference_coverage": entry["preference_coverage"],
        "hard_rule_coverage": entry["coverage"], "missing": entry["missing"],
        "state_reason": entry["state_reason"], "rank_note": entry.get("rank_note"),
        "measured_vs_predicted_counts": entry["measured_vs_predicted_counts"],
        "review_status": _label("review", entry["review_status"]),
        "score_rationale": _rationale_block(sr_stage.rationale_of(core, run_id, candidate_ref)),
        "mechanism_of_action": _mechanism_block(mechanism.narrative_of(core, run_id, candidate_ref)),
        "per_criterion": _cells(core, run_id, candidate_ref),
        "claims": [_claim_row(claim) for claim in claims], "claims_admitted": len(claims),
        "leaderboard": link("/leaderboard", task=task_id), "run": link("/run", run=run_id)})


def run(core: Core, run_id: str) -> dict[str, Any]:
    """One run's progress fold (`projection.progress`): a denominator per scope, the budget apart (§4, §12)."""
    binding = _binding(core, run_id)
    if not binding and core.journal.last_seq(run_id) == 0:
        raise NotFound(f"no run {run_id} in this store root")
    view = projection.progress(core, run_id)
    bound = binding.get("settings") or {}
    purpose = binding.get("run_purpose", "sweep")
    return _frame("run", {
        "run_id": run_id, "task_id": binding.get("task_id"), "state": view["state"],
        "state_label": view["state_label"], "termination_reason": view["termination_reason"],
        "termination_reason_label": _label("termination_reason", view["termination_reason"]),
        "last_activity_at": view["last_activity_at"], "last_seq": core.journal.last_seq(run_id),
        "progress": view["progress"], "budget": view["budget"],
        "verdicts": [{"verdict": verdict, "label": _label("verdict", verdict), "count": count}
                     for verdict, count in sorted(view["verdict_counts"].items())],
        "snapshot_id": view["snapshot_id"],
        "binding": {"run_purpose": _label("run_purpose", purpose), "chain_id": binding.get("chain_id"),
                    "continues_run_id": binding.get("continues_run_id"),
                    "continuation_kind": _label("continuation_kind", binding.get("continuation_kind")),
                    "rules@v": binding.get("rules@v"), "policy_arm": binding.get("policy_arm"),
                    "sweep_seed": binding.get("sweep_seed"), "candidate_limit": binding.get("candidate_limit"),
                    "evidence_cutoff": binding.get("evidence_cutoff"),
                    "budget_envelope": binding.get("budget_envelope") or {}, "config_hash": bound.get("config_hash"),
                    "preset": bound.get("preset"), "profile": bound.get("profile"),
                    "bound_at": binding.get("bound_at")},
        "leaderboard": link("/leaderboard", task=binding["task_id"]) if binding.get("task_id") else None})


def _review_row(item: dict[str, Any]) -> dict[str, Any]:
    subject = item["subject"]
    return {"item_id": item["item_id"], "state": item["state"], "state_label": _label("queue_item_state", item["state"]),
            "priority": item["priority"], "created_at": item["created_at"], "blocking": item["blocking"],
            "stream_id": item["stream_id"], "subject_kind": _label("hd_subject_kind", subject["kind"]),
            "subject_id": subject["id"], "why_expert_required": item["why_expert_required"]}


def review_queue(core: Core) -> dict[str, Any]:
    """The queue as it stands: shown here, decided on the terminal, never from a page (§9, §15.2.7).

    An item a machine adjudication resolved is listed apart from the ones an expert decided, with the
    route that resolved it and the plain statement that no person confirmed it, because the two are
    the same shape of row and only the authority behind them differs.
    """
    items = review_mod.items(core, core.journal.streams("task_") + core.journal.streams("run_"))
    pending, decided, adjudicated, withdrawn = [], [], [], []
    for item in sorted(items.values(), key=lambda item: item["created_at"]):
        row = _review_row(item)
        if item["state"] in ("open", "in_review"):
            pending.append(dict(row, decided_where=TERMINAL_DECISION, **adjudication.route_preview(core, item),
                                decide_with=f"mas review decide {item['item_id']} --decision DECISION "
                                            f"--reason TEXT --exposure DECLARATION"))
        elif item["state"] == "decided":
            decided.append(dict(row, decision=_label("hd_decision", item["decision"]),
                                decision_id=item["decision_id"],
                                authority=_label("decision_authority", "human_scientific_approval")))
        elif item["state"] == "machine_adjudicated":
            adjudicated.append(dict(row, adjudication_id=item["adjudication_id"],
                                    route=item["adjudication_route"],
                                    route_label=_label("adjudication_route", item["adjudication_route"]),
                                    resolution=item["adjudication_resolution"],
                                    reason=item["adjudication_reason"],
                                    authority=_label("decision_authority", item["authority"]),
                                    confirmed_by_a_person=False))
        else:
            withdrawn.append(row)
    return _frame("review queue", {
        "decisions_are_made": TERMINAL_DECISION, "pending": pending, "pending_n": len(pending),
        "blocking_n": sum(1 for row in pending if row["blocking"]), "decided": decided,
        "machine_adjudicated": adjudicated, "machine_adjudicated_n": len(adjudicated),
        "machine_adjudication_note": NO_PERSON_CONFIRMED if adjudicated else None,
        "withdrawn": withdrawn})


def criteria_pool(core: Core, task_id: str) -> dict[str, Any]:
    """The criteria pool of one task: every lineage with its state, version and parentage (design §5.6)."""
    _task(core, task_id)
    folded = pool_mod.fold(core, task_id)
    if not folded:
        raise NotFound(f"the criteria pool of {task_id} is empty; derive criteria with `mas criteria derive TASK`")
    counts: dict[str, int] = {}
    for entry in folded.values():
        counts[entry["state"]] = counts.get(entry["state"], 0) + 1
    items = []
    for entry in sorted(folded.values(), key=lambda entry: (
            POOL_ORDER.index(entry["state"]) if entry["state"] in POOL_ORDER else len(POOL_ORDER),
            ((entry["item"] or {}).get("attribute") or {}).get("name") or "")):
        item = entry["item"] or {}
        attribute = item.get("attribute") or {}
        last = entry["history"][-1] if entry["history"] else {}
        items.append({"criterion_id": entry["criterion_id"], "version": entry["version"], "state": entry["state"],
                      "state_label": _label("criterion_pool_state", entry["state"]), "name": attribute.get("name"),
                      "unit": attribute.get("unit"), "dimension": item.get("dimension"),
                      "promoted_as": (entry["promoted_as"] or {}).get("rule_ref"), "parents": entry["parents"],
                      "children": entry["children"],
                      "supporting_claims": len(item.get("supporting_claim_ids") or []),
                      "changes": len(entry["history"]),
                      "last_change": {key: last.get(key) for key in ("operation", "stage", "iteration", "reason_kind",
                                                                     "reason_text", "round_run_id")}})
    return _frame("criteria pool", {
        "task_id": task_id, "pool_hash": pool_mod.pool_hash(folded), "items_n": len(items),
        "active": len(pool_mod.active(folded)),
        "counts": [{"state": state, "state_label": _label("criterion_pool_state", state), "items": count}
                   for state, count in sorted(counts.items())],
        "items": items, "leaderboard": link("/leaderboard", task=task_id)})


def redact(key: str, value: Any) -> Any:
    """A setting that names a key shows the name of the variable or file, never a key (design §14.1)."""
    if SECRET_MARK not in key:
        return value
    if key.endswith("_env"):
        return f"read at call time from the environment variable {value}"
    if key.endswith("_file"):
        return f"read at call time from a key file named {Path(str(value)).name}"
    return "redacted"


def settings(config: Config, *, store_root: str, role_bindings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """The resolved settings with the layer each value came from (design §14.1), key settings redacted.

    `role_bindings` comes from the model roster, which may be a separate models file rather than a
    configuration table, so the page states which model answers for each role either way (ADR-40:
    the binding names the model, never the credential).
    """
    record = config.layer_record()
    return _frame("settings", {
        "store_root": store_root, "preset": record["preset"], "profile": record["profile"],
        "config_hash": record["config_hash"],
        "layers": "code defaults → preset → ./mas.toml → profile → MAS__SECTION__KEY → --set KEY=VALUE",
        "settings": [{"key": row["key"], "value": redact(row["key"], row["value"]), "unit": row["unit"],
                      "layer": row["layer"], "doc": row["doc"]} for row in record["settings"]],
        "providers": [{"provider": name, **{key: redact(key, value) for key, value in sorted(spec.items())}}
                      for name, spec in sorted(config.providers.items())],
        "roles": config.roles,
        "role_bindings": [{key: redact(key, value) for key, value in sorted(binding.items())}
                          for binding in (role_bindings or [])],
        "secrets": "a key is read at call time from the environment variable or key file a provider names; "
                   "no page reads one and none is stored"})
