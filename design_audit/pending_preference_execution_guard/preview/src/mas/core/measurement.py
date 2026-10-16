"""Prospective measurement profiles, using the existing immutable freeze records.

A profile fixes the scoring set and ranking gate before its run. Eligibility keeps
its own coverage floor even when the registered rank endpoint does not gate on it.
Legacy runs without a profile retain their original semantics.
"""

from __future__ import annotations

import math
from typing import Any

from . import criteria, freeze, supplements, task as task_mod
from .canonical import sha256_hex
from .clock import utc_now
from .runtime import Core


class MeasurementError(RuntimeError):
    pass


def _fraction(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise MeasurementError(f"{name} must be a finite fraction from 0 to 1")
    return float(value)


def _scope(context: dict[str, Any]) -> dict[str, Any]:
    return {"candidate_universe": context.get("candidate_universe") or {},
            "seed_candidates": context.get("seed_candidates") or [], "candidate_limit": None}


def check_required_anchors(core: Core, task_id: str, *, rule_set: dict[str, Any] | None = None,
                           defer_capabilities: tuple[str, ...] = ()) -> dict[str, Any]:
    """Validate the task-defined population before a new freeze/profile, without changing old profiles."""
    from . import derivation_run

    audit = derivation_run.required_binding_audit(core, task_id)
    if not audit["preserves_original_bindings"]:
        raise MeasurementError("required anchors changed or were retired; audit/restore the original task bindings "
                               "before preparing a new measurement")
    if not audit["task_scope_fully_bound"]:
        raise MeasurementError("required scope lacks verified task-bound anchors: "
                               + ", ".join(audit["unbound_required_scope_identifiers"]))
    scope_bindings = [row for row in audit["bindings"] if row["required_scope_identifier"]]
    selected = {entry["rule_ref"]: entry for entry in rule_set["entries"]} if rule_set is not None else None
    non_scope = []
    for binding in audit["bindings"]:
        if binding["required_scope_identifier"]:
            continue
        ref = binding["active_rule_ref"]
        attribute = criteria.load(core, binding["active_attribute_ref"], task_id)
        routes = criteria.evidence_routes(attribute)
        if rule_set is not None:
            deferred = [row for row in rule_set.get("deferred") or [] if row["rule_ref"] == ref]
            state = "included" if ref in selected else "deferred" if deferred else "withheld"
        else:
            deferred = [criteria.route_summary(route) for route in routes
                        if route.get("capability") in defer_capabilities]
            state = "deferred" if routes and len(deferred) == len(routes) else "awaiting_freeze"
        non_scope.append({"attribute_ref": binding["active_attribute_ref"], "rule_ref": ref,
                          "source_attribute_ref": binding["source_attribute_ref"],
                          "source_rule_ref": binding["source_rule_ref"],
                          "source_attribute_sha256": binding["source_attribute_sha256"],
                          "source_rule_sha256": binding["source_rule_sha256"],
                          "task_field": binding["task_field"], "rule_kind": binding["source_rule_kind"],
                          "freeze_state": state, "deferred": deferred})
    rows = []
    for binding in scope_bindings:
        rule_ref = binding["active_rule_ref"]
        attribute = criteria.load(core, binding["active_attribute_ref"], task_id)
        if selected is not None:
            entry = selected.get(rule_ref)
            if entry is None or entry["attribute_ref"] != binding["active_attribute_ref"]:
                raise MeasurementError(f"required denominator would shrink: {binding['required_scope_identifier']} "
                                       f"({rule_ref}) is absent from the selected frozen scoring set")
            rule_kind = entry["rule_kind"]
            if rule_kind != binding["source_rule_kind"]:
                raise MeasurementError(f"required binding changed decision kind: {rule_ref}")
        else:
            routes = criteria.evidence_routes(attribute)
            if routes and all(route.get("capability") in defer_capabilities for route in routes):
                raise MeasurementError(f"required denominator would shrink: every route for "
                                       f"{binding['required_scope_identifier']} is deferred")
            rule_kind = binding["source_rule_kind"]
        rows.append({"scope_identifier": binding["required_scope_identifier"],
                     "attribute_ref": binding["active_attribute_ref"], "rule_ref": rule_ref,
                     "source_attribute_sha256": binding["source_attribute_sha256"],
                     "source_rule_sha256": binding["source_rule_sha256"], "rule_kind": rule_kind})
    return {"version": 1, "task_pinned_seq": audit["task_pinned_seq"],
            "required_scope_count": audit["required_scope_count"], "scope_bindings": rows,
            "scope_preference_count": sum(row["rule_kind"] != "hard_exclusion" for row in rows),
            "scope_gate_count": sum(row["rule_kind"] == "hard_exclusion" for row in rows),
            "non_scope_required_anchors": non_scope,
            "selected_rule_set_ref": rule_set["rule_set_ref"] if rule_set is not None else None,
            "audit_digest": sha256_hex(audit)}


def prepare(core: Core, task_id: str, *, by: dict[str, Any], primary_board: str, rationale: str,
            expected_effect: str, coverage_floor: float = 0.0,
            defer_capabilities: tuple[str, ...] = ("predicted_property_lookup", "literature_retrieval"),
            defer_reason: str | None = None, **profile_options: Any) -> dict[str, Any]:
    """Check required bindings before confirming rules, then register the exact validated profile."""
    if not all(isinstance(value, str) and value.strip() for value in (primary_board, rationale, expected_effect)):
        raise MeasurementError("primary_board, rationale and expected_effect must each be stated")
    check_required_anchors(core, task_id, defer_capabilities=defer_capabilities)
    selected = criteria.confirm_rule_set(core, task_id, by=by, allow_pending=True,
                                         coverage_floor=coverage_floor, defer_capabilities=defer_capabilities,
                                         defer_reason=defer_reason or expected_effect)
    ref = register(core, task_id, by=by, primary_board=primary_board, rationale=rationale,
                    expected_effect=expected_effect, rule_set_ref=selected, **profile_options)
    frozen = criteria.rule_set(core, task_id, selected)
    return {"task_id": task_id, "rule_set_ref": selected, "measurement_profile_ref": ref,
            "scoring_rules": len(frozen["entries"]), "acceptance_label": frozen["acceptance_label"],
            "required_binding_check": load(core, task_id, ref)["policy"]["scoring_policy"]["required_binding_check"]}


def register(core: Core, task_id: str, *, by: dict[str, Any], primary_board: str,
             rationale: str, expected_effect: str, rule_set_ref: str | None = None,
             ranking_coverage_floor: float = 0.5, eligibility_mandated_coverage_floor: float = 1.0,
             rank_requires_mandated_coverage: bool = False, implementation: dict[str, Any] | None = None,
             settings: Any = None, evaluation_mode: str | None = None,
             qualification_policy: str | None = None, evidence_mode: str | None = None) -> str:
    """Freeze a new profile; an existing profile is never edited or selected implicitly.

    This records a prospective continuation, not a retrospective claim that an
    earlier board conformed. Prior outcomes and the recovery case remain intact.
    """
    if not all(isinstance(value, str) and value.strip() for value in (primary_board, rationale, expected_effect)):
        raise MeasurementError("primary_board, rationale and expected_effect must each be stated")
    if not isinstance(rank_requires_mandated_coverage, bool):
        raise MeasurementError("rank_requires_mandated_coverage must be an explicit boolean")
    context = task_mod.get(core, task_id)
    rule_set = criteria.rule_set(core, task_id, rule_set_ref)
    execution_findings = criteria.preference_execution_findings(core, task_id, rule_set=rule_set)
    if execution_findings:
        raise MeasurementError("selected scoring set contains non-executable preferences; confirm a new "
                               "rule set to defer them before registering a new measurement: " + "; ".join(
                                   f"{row['rule_ref']}: {row['reason']}" for row in execution_findings))
    required_binding_check = check_required_anchors(core, task_id, rule_set=rule_set)
    evaluation_mode = evaluation_mode or (settings["evaluation.mode"] if settings is not None else "staged")
    qualification_policy = qualification_policy or (settings["qualification.policy"] if settings is not None else "qualification_first_v1")
    evidence_mode = evidence_mode or (settings["evidence.mode"] if settings is not None else "existing_only")
    if evaluation_mode not in ("staged", "full") or qualification_policy not in ("legacy", "qualification_first_v1") \
            or evidence_mode not in ("existing_only", "retrieve"):
        raise MeasurementError("invalid evaluation_mode, qualification_policy or evidence_mode")
    if qualification_policy == "qualification_first_v1" and (rule_set.get("ordering_method") or {}).get("kind") == "symbolic_expression":
        raise MeasurementError("qualification_first_v1 currently requires weighted preference scoring")
    scoring = {
        "measurement_profile_version": 1,
        "rule_set_digest": sha256_hex(rule_set),
        "scoring_rule_refs": sorted(entry["rule_ref"] for entry in rule_set["entries"]),
        "ranking_coverage_floor": _fraction(ranking_coverage_floor, "ranking_coverage_floor"),
        "eligibility_mandated_coverage_floor": _fraction(eligibility_mandated_coverage_floor,
                                                        "eligibility_mandated_coverage_floor"),
        "rank_requires_mandated_coverage": rank_requires_mandated_coverage,
        "config_hash": settings.hash() if settings is not None else None,
        "sweep_seed": settings["run.seed"] if settings is not None else 0,
        "required_binding_check": required_binding_check,
        "evaluation_mode": evaluation_mode, "qualification_policy": qualification_policy, "evidence_mode": evidence_mode,
        "scoring_method": "weighted_preference_qualified_v1" if qualification_policy == "qualification_first_v1" else "legacy",
    }
    policy = {
        "task_ref": f"{task_id}@v{context['version']}", "criteria_ref": rule_set["rule_set_ref"],
        "candidate_scope": _scope(context),
        "evidence_cutoff": (settings["search.date_to"] if settings is not None else "") or utc_now()[:10],
        "retrieval_policy": {"deferred_capabilities": rule_set.get("deferred_capabilities") or [],
                             "replay_source_run_ids": settings["sources.replay_run_ids"] if settings is not None else [],
                             "pubchem_record_projection": settings["sources.pubchem_record_projection"] if settings is not None else False,
                             "defer_reason": rule_set.get("defer_reason"),
                             "verified_supplements": supplements.binding(core, context),
                             "rationale": rationale, "expected_effect": expected_effect},
        "scoring_policy": scoring, "primary_board": primary_board,
        "rank_endpoint": "qualified_only" if qualification_policy == "qualification_first_v1" else
                         "eligibility_required" if rank_requires_mandated_coverage else "ranked_only",
        "missingness_policy": {"unknown_values": "remain_unknown", "eligibility_reported_separately": True},
        "code_commit": implementation or None,
    }
    if settings is not None:
        _settings_check(scoring, settings.values if hasattr(settings, "values") else {}, settings.hash())
    return freeze.register(core, task_id, by=by, policy=policy)


def load(core: Core, task_id: str, ref: str) -> dict[str, Any]:
    """Resolve a registered profile on this task, without opening evaluator content."""
    events = core.journal.replay(task_id)
    if not any(event.event_type == "preregistration.recorded" and event.payload.get("artifact_id") == ref
               for event in events):
        raise MeasurementError(f"measurement profile {ref} is not registered on {task_id}")
    record = core.artifacts.payload(ref)
    if (record.get("policy", {}).get("scoring_policy") or {}).get("measurement_profile_version") != 1:
        raise MeasurementError(f"{ref} is not a measurement profile")
    if "sweep_seed" not in record["policy"]["scoring_policy"] or not record["policy"].get("evidence_cutoff"):
        raise MeasurementError(f"{ref} did not freeze the seed and cutoff; register a new measurement profile")
    return record


def digest(record: dict[str, Any]) -> str:
    return sha256_hex(record["policy"])


def ensure_unused(core: Core, task_id: str, ref: str) -> None:
    """One profile names one run; an interrupted run is resumed, not selected again."""
    for run_id in core.journal.streams("run_"):
        events = core.journal.replay(run_id, 1, 1)
        if not events or events[0].event_type != "run.created" or events[0].payload.get("task_id") != task_id:
            continue
        binding = core.artifacts.payload(events[0].payload["binding_artifact_id"])
        if binding.get("measurement_profile_ref") == ref:
            raise MeasurementError(f"measurement profile {ref} is already bound to {run_id}; resume that run "
                                   "or register a separately labelled new reading")


def _settings_check(scoring: dict[str, Any], settings: dict[str, Any], config_hash: str | None) -> None:
    for key, field in (("rank.coverage_floor", "ranking_coverage_floor"),
                       ("rank.mandated_coverage_floor", "eligibility_mandated_coverage_floor")):
        if key in settings and settings[key] != scoring[field]:
            raise MeasurementError(f"measurement profile drift: {key} differs from {field}")
    for key, field in (("evaluation.mode", "evaluation_mode"), ("qualification.policy", "qualification_policy"),
                       ("evidence.mode", "evidence_mode")):
        if field in scoring and key in settings and settings[key] != scoring[field]:
            raise MeasurementError(f"measurement profile drift: {key} differs from {field}")
    if scoring.get("config_hash") is not None and config_hash != scoring["config_hash"]:
        raise MeasurementError("measurement profile drift: resolved settings changed")
    if settings.get("sr.mode", "off") != "off":
        raise MeasurementError("a frozen measurement profile cannot fit a new scoring rule during its run")


def verify(core: Core, task_id: str, ref: str, *, context: dict[str, Any], rule_set: dict[str, Any],
           sweep_seed: int, evidence_cutoff: str,
           candidate_limit: int | None = None, settings: dict[str, Any] | None = None,
           config_hash: str | None = None, implementation: dict[str, Any] | None = None,
           bound_digest: str | None = None) -> dict[str, Any]:
    """Refuse policy drift before executing, resuming, or publishing a run."""
    record = load(core, task_id, ref)
    policy, scoring = record["policy"], record["policy"]["scoring_policy"]
    checks = {
        "task_ref": f"{task_id}@v{context['version']}" == policy["task_ref"],
        "criteria_ref": rule_set["rule_set_ref"] == policy["criteria_ref"],
        "rule_set_digest": sha256_hex(rule_set) == scoring["rule_set_digest"],
        "candidate_scope": _scope(context) == policy["candidate_scope"] and candidate_limit is None,
        "implementation": not policy.get("code_commit") or policy["code_commit"] == implementation,
        "bound_digest": bound_digest is None or bound_digest == digest(record),
        "sweep_seed": sweep_seed == scoring["sweep_seed"],
        "evidence_cutoff": evidence_cutoff == policy["evidence_cutoff"],
        "verified_supplements": (policy.get("retrieval_policy", {}).get("verified_supplements")
                                 or supplements.binding(core, {})) == supplements.binding(core, context),
    }
    failed = [key for key, passed in checks.items() if not passed]
    if failed:
        raise MeasurementError(f"measurement profile drift: {', '.join(failed)}")
    _settings_check(scoring, settings or {}, config_hash)
    return {"ref": ref, "digest": digest(record), "policy": policy,
            "verification": {"conforms": True, "checked_fields": sorted(checks)}}
