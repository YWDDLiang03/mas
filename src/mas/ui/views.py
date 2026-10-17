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

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from mas.core import adjudication, criteria, derivation_run, freeze, leaderboard, ledger, mechanism, projection, sr_stage, vocab
from mas.core import collapse as collapse_mod
from mas.core import pool as pool_mod, review as review_mod, task as task_mod
from mas.core.clock import utc_now
from mas.core.journal import Event
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


def empty_page(page: str, task_id: str | None, message: str) -> dict[str, Any]:
    return _frame(page, {"empty_state": True, "task_id": task_id, "message": message,
                         "workspace": link("/operations", task=task_id) if task_id else "/operations",
                         "tasks_url": "/", "leaderboard": link("/leaderboard", task=task_id) if task_id else "/leaderboard"})


def _label(domain: str, value: str | None) -> str | None:
    if not value:
        return None
    try:
        return vocab.label(domain, value)
    except vocab.VocabularyViolation:
        # A readable historical/newer metadata value must not disconnect an entire page.
        # Keep its original value; UI label fallback grants no decision authority.
        return value


def _task(core: Core, task_id: str) -> dict[str, Any]:
    try:
        return task_mod.get(core, task_id)
    except KeyError:
        raise NotFound(f"no task {task_id} in this store root") from None


class _EventView:
    """A read projection for existing core folds, avoiding full replay of unrelated tool events."""

    def __init__(self, journal, kinds: tuple[str, ...], candidate_ref: str | None = None):
        self.journal, self.kinds, self.candidate_ref = journal, kinds, candidate_ref
        self._cache = {}

    def __getattr__(self, name):
        return getattr(self.journal, name)

    def replay(self, stream_id: str, from_seq: int = 1, to_seq: int | None = None) -> list[Event]:
        key = (stream_id, from_seq, to_seq)
        if key not in self._cache:
            placeholders = ",".join("?" for _ in self.kinds)
            sql = f"SELECT body FROM events WHERE stream_id=? AND seq>=? AND event_type IN ({placeholders})"
            parameters = [stream_id, from_seq, *self.kinds]
            if to_seq is not None:
                sql += " AND seq<=?"
                parameters.append(to_seq)
            if self.candidate_ref:
                sql += " AND (json_extract(body,'$.payload.candidate_ref')=? OR (event_type='step.completed' AND json_extract(body,'$.payload.step')='symbolic_regression'))"
                parameters.append(self.candidate_ref)
            sql += " ORDER BY seq"
            self._cache[key] = [Event.from_record(json.loads(body)) for (body,) in self.journal.store.db.execute(sql, parameters)]
        return self._cache[key]


def _event_core(core: Core, kinds: tuple[str, ...], candidate_ref: str | None = None) -> Core:
    return Core(core.store, _EventView(core.journal, kinds, candidate_ref), core.artifacts)


def _snapshots(core: Core, task_id: str, snapshot_id: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    published = leaderboard.snapshots(_event_core(core, ("leaderboard.snapshot_published",)), task_id)
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


def criteria_summary(core: Core, task_id: str, *, include_details: bool = True) -> dict[str, Any]:
    """Registry, pool and scoring are different counts; expose each without reconstructing a policy."""
    reduction = derivation_run.registered_reduction_summary(core, task_id)
    frozen = _rule_set(core, task_id, None)
    registrations = []
    used_profiles = {}
    for created in core.journal.of_type("run.created", "run_"):
        if created.payload.get("task_id") == task_id:
            binding = core.artifacts.payload(created.payload["binding_artifact_id"])
            if binding.get("measurement_profile_ref"):
                used_profiles[binding["measurement_profile_ref"]] = created.stream_id
    for record in freeze.registrations(core, task_id):
        policy = record.get("policy") or {}
        scoring = policy.get("scoring_policy") or {}
        if scoring.get("measurement_profile_version") == 1:
            registrations.append({"ref": record["artifact_id"], "name": policy.get("primary_board"),
                                  "rule_set_ref": policy.get("criteria_ref"),
                                  "rank_endpoint": policy.get("rank_endpoint"),
                                  "used_by_run": used_profiles.get(record["artifact_id"])})
    compact = {"registered_total": reduction["historical_registered_count"],
               "active_registered_count": reduction["active_registered_count"],
               "retired_registered_count": reduction["retired_latest_count"],
               "scoring_count": reduction["scoring_in_latest_frozen_set_count"],
               "rule_set_ref": frozen.get("rule_set_ref"), "pending_count": reduction["pending_review_count"],
               "measurement_profiles": registrations,
               "reduction": {key: reduction[key] for key in ("run_id", "total_active_count", "scope_pool_states",
                                "unresolved_pool_count", "additional_unregistered_active_count", "retired_by_this_run_count")}}
    if not include_details:
        return compact
    registered = criteria.registered_attributes(core, task_id, include_retired=True)
    queue = review_mod.items(core, [task_id])
    folded = pool_mod.fold(core, task_id)
    pool_counts: dict[str, int] = {}
    for row in folded.values():
        pool_counts[row["state"]] = pool_counts.get(row["state"], 0) + 1
    scoring_attrs = {entry["attribute_ref"] for entry in frozen.get("entries", [])}
    retired_attrs = {entry["attribute_ref"] for entry in reduction["retired"]}
    pending_attrs = {entry["attribute_ref"] for entry in reduction["active"] if entry["pending_review"]}
    merged_attrs = collapse_mod.superseded_attributes(core, task_id)
    registry_rows = []
    for attribute in registered:
        ref = f"{attribute['attribute_id']}@v{attribute['version']}"
        registry_rows.append({"attribute_ref": ref, "name": attribute.get("name"),
                              "definition": attribute.get("definition"), "unit": attribute.get("unit"),
                              "state": "retired" if ref in retired_attrs else "scoring" if ref in scoring_attrs else "merged_away" if ref in merged_attrs else "open" if ref in pending_attrs else "registered",
                              "supporting_claims": len(attribute.get("supporting_claim_refs") or [])})
    return {**compact, "reduction": reduction,
            "pending_queue_count": sum(row["state"] in ("open", "in_review") for row in queue.values()),
            "registry_merged_count": len(merged_attrs), "registered_criteria": registry_rows,
            "pool_counts": pool_counts, "measurement_profiles": registrations,
            "note": "Registered criteria, pool history and scoring criteria are counted separately. A smaller scoring set does not mean the registry has been reduced."}


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
                      "leaderboard": link("/leaderboard", task=task_id), "pool": link("/pool", task=task_id),
                      "criteria_summary": criteria_summary(core, task_id)})
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
        "review_queue": link("/review"), "settings": link("/settings"), "published_readings": {}})


def board(core: Core, task_id: str, *, snapshot_id: str | None = None, top: int = MAX_ROWS,
          page: int = 1) -> dict[str, Any]:
    """One leaderboard snapshot: ranks, scores, coverage, its acceptance label, what was rankable (§11)."""
    context = _task(core, task_id)
    snapshot, published = _snapshots(core, task_id, snapshot_id)
    entries = snapshot["candidate_entries"]
    ranked = [entry for entry in entries if entry.get("position")]
    rules = _rule_set(core, task_id, snapshot["rules@v"])
    reported = snapshot["reporting_tuple"]
    method = snapshot.get("ordering_method") or {}
    page_count = max(1, (len(entries) + top - 1) // top)
    page = min(max(1, page), page_count)
    offset = (page - 1) * top
    rows = [{"position": entry["position"], "candidate_ref": entry["candidate_ref"],
             "label": (entry["identity_labels"] or [None])[0], "state": entry["state"],
             "state_label": _label("candidate", entry["state"]), "score": entry["preference_score"],
             "preference_coverage": entry["preference_coverage"], "hard_rule_coverage": entry["coverage"],
             "clears_hard_rules": entry.get("clears_hard_rules"),
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
             "candidate": link("/candidate", task=task_id, id=entry["candidate_ref"], snapshot=snapshot["snapshot_id"])}
            for entry in entries[offset:offset + top]]
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
        "measurement_profile": snapshot.get("measurement_profile"),
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
        "rank_requires_mandated_coverage": reported.get("rank_requires_mandated_coverage", True),
        "mandated_coverage_note": ("Eligibility is reported separately; candidates missing required coverage may still be ranked."
                                   if reported.get("rank_requires_mandated_coverage") is False else
                                   "This result requires required-criteria coverage for ranking."),
        "ranked_with_a_mandated_gate_unanswered": reported.get("ranked_with_a_mandated_gate_unanswered"),
        "abstention_n_by_reason": reported["abstention_n_by_reason"], "budget": reported["budget"],
        "rows": rows, "rows_shown": len(rows), "rows_not_shown": max(0, len(entries) - len(rows)),
        "pagination": {"page": page, "pages": page_count, "page_size": top,
                       "first_row": offset + 1 if rows else 0, "last_row": offset + len(rows)},
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
    focused = _event_core(core, ("evidence.admitted", "evidence.quarantined", "candidate.assessed", "step.completed"), candidate_ref)
    claims = ledger.claims(focused, [run_id, task_id], candidate_ref=candidate_ref)
    cells = _cells(focused, run_id, candidate_ref)
    attribute_refs = {cell["attribute_ref"] for cell in cells}
    attribute_names = {}
    for event in _event_core(core, ("criterion.version_proposed",)).journal.replay(task_id):
        proposed = event.payload
        ref = f"{proposed['id']}@v{proposed['version']}"
        if proposed["kind"] == "attribute" and ref in attribute_refs:
            attribute_names[ref] = core.artifacts.payload(proposed["artifact_id"]).get("name")
    for cell in cells:
        cell["attribute_name"] = attribute_names.get(cell["attribute_ref"])
    return _frame("candidate", {
        "task_id": task_id, "candidate_ref": candidate_ref, "label": (entry["identity_labels"] or [None])[0],
        "snapshot_id": snapshot["snapshot_id"], "run_id": run_id,
        "state": entry["state"], "state_label": _label("candidate", entry["state"]), "position": entry["position"],
        "score": entry["preference_score"], "preference_coverage": entry["preference_coverage"],
        "hard_rule_coverage": entry["coverage"], "missing": entry["missing"],
        "state_reason": entry["state_reason"], "rank_note": entry.get("rank_note"),
        "measured_vs_predicted_counts": entry["measured_vs_predicted_counts"],
        "review_status": _label("review", entry["review_status"]),
        "score_rationale": _rationale_block(sr_stage.rationale_of(focused, run_id, candidate_ref)),
        "mechanism_of_action": _mechanism_block(mechanism.narrative_of(focused, run_id, candidate_ref)),
        "per_criterion": cells,
        "claims": [_claim_row(claim) for claim in claims], "claims_admitted": len(claims),
        "leaderboard": link("/leaderboard", task=task_id, snapshot=snapshot["snapshot_id"]), "run": link("/run", run=run_id)})


def _derivation_activity(core: Core, run_id: str, binding: dict[str, Any], state: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recorded stage/model events only; iterative work has no fixed overall denominator."""
    stages, started, finished, activity, roles = {}, {}, set(), [], {}
    known_cost, unknown_cost, known_cost_count = 0.0, 0, 0
    input_tokens, output_tokens, input_known, output_known = 0, 0, 0, 0
    cost_states, usage_states = [], []
    for event in core.journal.replay(run_id):
        payload = event.payload
        if event.event_type in ("stage.opened", "stage.closed"):
            key = payload.get("stage_key") or (payload.get("stage"), payload.get("iteration"))
            row = stages.setdefault(key, {"scope": f"stage:{payload.get('stage')}:{payload.get('iteration')}",
                                         "stage": payload.get("stage"), "iteration": payload.get("iteration"),
                                         "denominator_kind": "open_ended", "opened_at": None, "closed_at": None})
            if event.event_type == "stage.opened":
                row.update(state="running", opened_at=event.recorded_at)
            else:
                row.update(state="completed", closed_at=event.recorded_at,
                           result_counts={key: value for key, value in (payload.get("result") or {}).items()
                                          if isinstance(value, (int, float, bool))})
        elif event.event_type in ("agent.started", "agent.finished"):
            request_id, role = payload.get("request_id"), payload.get("role")
            item = {"request_id": request_id, "role": role, "model_id": payload.get("model_id") or event.actor.get("version"),
                    "state": "started" if event.event_type == "agent.started" else "completed", "at": event.recorded_at}
            if event.event_type == "agent.started":
                started[request_id] = item
            else:
                finished.add(request_id)
                usage = payload.get("usage") or {}
                incoming = usage.get("input_tokens", usage.get("prompt_tokens"))
                outgoing = usage.get("output_tokens", usage.get("completion_tokens"))
                cost = payload.get("cost_usd")
                cost_known = isinstance(cost, (int, float))
                cost_state = payload.get("cost_status") or ("recorded" if cost_known else "unknown")
                usage_state = payload.get("usage_status") or ("recorded" if usage else "unknown")
                known_cost += cost if cost_known else 0
                known_cost_count += cost_known
                unknown_cost += not cost_known
                input_tokens += incoming or 0
                output_tokens += outgoing or 0
                input_known += incoming is not None
                output_known += outgoing is not None
                cost_states.append(cost_state)
                usage_states.append(usage_state)
                item.update(usage={"input_tokens": incoming, "output_tokens": outgoing},
                            usage_status=usage_state, cost_status=cost_state,
                            estimated_cost_usd=cost, schema_ok=payload.get("schema_ok"))
                aggregate = roles.setdefault(role, {"role": role, "finished_requests": 0, "input_tokens": 0,
                                                    "output_tokens": 0, "estimated_cost_usd": None,
                                                    "_input_known": 0, "_output_known": 0, "_cost_states": [], "_usage_states": []})
                aggregate["finished_requests"] += 1
                aggregate["input_tokens"] += incoming or 0
                aggregate["output_tokens"] += outgoing or 0
                aggregate["_input_known"] += incoming is not None
                aggregate["_output_known"] += outgoing is not None
                aggregate["_cost_states"].append(cost_state)
                aggregate["_usage_states"].append(usage_state)
                if cost_known:
                    aggregate["estimated_cost_usd"] = round((aggregate["estimated_cost_usd"] or 0) + cost, 6)
            activity.append(item)
    stage_rows = list(stages.values())
    for row in stage_rows:
        if row.get("state") == "running" and state not in ("queued", "running"):
            row["state"] = "unresolved"
    current = next((row for row in reversed(stage_rows) if row.get("state") == "running"), None)
    envelope = dict(binding.get("budget_envelope") or {})
    settings_ref = (binding.get("settings") or {}).get("layers_artifact_id")
    if settings_ref:
        layers = core.artifacts.payload(settings_ref)
        cap = next((row["value"] for row in layers.get("settings", []) if row["key"] == "budget.usd_max"), None)
        if cap is not None:
            envelope["usd"] = cap
    note = "Only recorded usage and cost estimates from finished requests are included. In-flight requests and unknown charges are excluded."
    def accounting_status(states, known: bool, complete: str) -> str:
        if not known:
            return "unknown"
        if any(value in ("unknown", "partial") for value in states):
            return "partial"
        return "recorded" if "recorded" in states else complete

    for aggregate in roles.values():
        aggregate["cost_status"] = accounting_status(aggregate.pop("_cost_states"), aggregate["estimated_cost_usd"] is not None, "estimated")
        aggregate["usage_status"] = accounting_status(aggregate.pop("_usage_states"), bool(aggregate["_input_known"] or aggregate["_output_known"]), "complete")
        if not aggregate.pop("_input_known"):
            aggregate["input_tokens"] = None
        if not aggregate.pop("_output_known"):
            aggregate["output_tokens"] = None
    budget = {"used": {"usd": round(known_cost, 6) if known_cost_count else None,
                       "input_tokens": input_tokens if input_known else None, "output_tokens": output_tokens if output_known else None,
                       "model_requests_started": len(started), "model_requests_finished": len(finished)},
              "envelope": envelope, "basis": "recorded_agent_finished", "note": note,
              "cost_status": accounting_status(cost_states, bool(known_cost_count), "estimated"),
              "usage_status": accounting_status(usage_states, bool(input_known or output_known), "complete"),
              "usage_note": "Historical usage may include only the final repair attempt and is shown as recorded.",
              "finished_requests_without_cost": unknown_cost}
    detail = {"stages": stage_rows, "current_stage": current,
              "iteration": max((row.get("iteration") or 0 for row in stage_rows), default=0),
              "iteration_limit": binding.get("inner_iterations"), "recent_model_activity": activity[-8:],
              "active_models": [row for key, row in started.items() if key not in finished],
              "model_usage_by_role": list(roles.values()), "overall_percent": None,
              "progress_note": "Iterations may stop early. Stages and model activity show recorded events without an overall percentage."}
    return detail, budget


def run(core: Core, run_id: str) -> dict[str, Any]:
    """One run's progress fold (`projection.progress`): a denominator per scope, the budget apart (§4, §12)."""
    binding = _binding(core, run_id)
    if not binding and core.journal.last_seq(run_id) == 0:
        raise NotFound(f"no run {run_id} in this store root")
    bound = binding.get("settings") or {}
    purpose = binding.get("run_purpose", "sweep")
    focused = _event_core(core, (*RUN_STATE_KINDS, "stage.opened", "stage.closed", "agent.started", "agent.finished", "run.annotated")) if purpose == "criteria_derivation" else core
    view = projection.progress(focused, run_id)
    derivation = None
    if purpose == "criteria_derivation":
        derivation, recorded_budget = _derivation_activity(focused, run_id, binding, view["state"])
        view["progress"] = derivation["stages"]
        view["budget"] = view["budget"] or recorded_budget
        latest = core.journal.replay(run_id, core.journal.last_seq(run_id))
        if latest:
            view["last_activity_at"] = latest[-1].recorded_at
    return _frame("run", {
        "run_id": run_id, "task_id": binding.get("task_id"), "state": view["state"],
        "state_label": view["state_label"], "termination_reason": view["termination_reason"],
        "termination_reason_label": _label("termination_reason", view["termination_reason"]),
        "last_activity_at": view["last_activity_at"], "last_seq": core.journal.last_seq(run_id),
        "progress": view["progress"], "budget": view["budget"],
        "derivation": derivation,
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


def review_queue(core: Core, *, include_routes: bool = True, task_id: str | None = None,
                 current_versions: bool = False) -> dict[str, Any]:
    """The queue as it stands: shown here, decided on the terminal, never from a page (§9, §15.2.7).

    An item a machine adjudication resolved is listed apart from the ones an expert decided, with the
    route that resolved it and the plain statement that no person confirmed it, because the two are
    the same shape of row and only the authority behind them differs.
    """
    queue_core = _event_core(core, ("human.review_requested", "human.review_decided", "human.review_withdrawn", "decision.recorded"))
    if task_id:
        _task(core, task_id)
        streams = [task_id] + [created.stream_id for created in core.journal.of_type("run.created", "run_")
                              if created.payload.get("task_id") == task_id]
    else:
        streams = core.journal.streams("task_") + core.journal.streams("run_")
    items = review_mod.items(queue_core, streams)
    pending, decided, adjudicated, withdrawn, historical = [], [], [], [], []
    active_versions = {}
    if current_versions and task_id:
        rules = criteria.registered_rule_records(core, task_id)
        active_versions = {
            "rule_version": {f"{rule['rule_id']}@v{rule['version']}" for rule in rules},
            "attribute_version": {f"{attr['attribute_id']}@v{attr['version']}"
                                  for attr in criteria.registered_attributes(core, task_id)}
                                 | {rule["attribute_ref"] for rule in rules},
        }
    for item in sorted(items.values(), key=lambda item: item["created_at"]):
        row = _review_row(item)
        subject = item["subject"]
        earlier_version = (subject["kind"] in active_versions
                           and subject["id"] not in active_versions[subject["kind"]])
        if earlier_version:
            row["historical_reason"] = "superseded_or_retired_version"
        if item["state"] in ("open", "in_review"):
            if earlier_version:
                historical.append(row)
                continue
            route = adjudication.route_preview(core, item) if include_routes else {"route": None, "route_label": None,
                       "would": None, "why_not": "Route details are loaded on request."}
            pending.append(dict(row, decided_where=TERMINAL_DECISION, **route,
                                decide_with=f"mas review decide {item['item_id']} --decision DECISION "
                                            f"--reason TEXT --exposure DECLARATION"))
        elif item["state"] == "decided":
            (historical if earlier_version else decided).append(dict(row, decision=_label("hd_decision", item["decision"]),
                                decision_id=item["decision_id"],
                                authority=_label("decision_authority", "human_scientific_approval")))
        elif item["state"] == "machine_adjudicated":
            (historical if earlier_version else adjudicated).append(dict(row, adjudication_id=item["adjudication_id"],
                                    route=item["adjudication_route"],
                                    route_label=_label("adjudication_route", item["adjudication_route"]),
                                    resolution=item["adjudication_resolution"],
                                    reason=item["adjudication_reason"],
                                    authority=_label("decision_authority", item["authority"]),
                                    confirmed_by_a_person=False))
        else:
            (historical if earlier_version else withdrawn).append(row)
    return _frame("review queue", {
        "decisions_are_made": TERMINAL_DECISION, "pending": pending, "pending_n": len(pending),
        "blocking_n": sum(1 for row in pending if row["blocking"]), "decided": decided,
        "machine_adjudicated": adjudicated, "machine_adjudicated_n": len(adjudicated),
        "machine_adjudication_note": NO_PERSON_CONFIRMED if adjudicated else None,
        "withdrawn": withdrawn, "routes_included": include_routes,
        "historical": historical, "historical_n": len(historical),
        "historical_pending_n": sum(row["state"] in ("open", "in_review") for row in historical),
        "current_versions_only": bool(active_versions),
        "scope": "task" if task_id else "workspace", "task_id": task_id})


def criteria_pool(core: Core, task_id: str) -> dict[str, Any]:
    """The criteria pool of one task: every lineage with its state, version and parentage (design §5.6)."""
    _task(core, task_id)
    folded = pool_mod.fold(core, task_id)
    summary = criteria_summary(core, task_id)
    if not folded and not summary["registered_total"]:
        raise NotFound(f"no registered criteria or pool lineage exists for {task_id}")
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
        "registry_summary": summary,
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
