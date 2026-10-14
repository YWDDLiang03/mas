"""Registering an experiment before it runs, and checking afterwards that it ran as registered.

A one-shot result is only one-shot if the thing being evaluated was fixed before anyone saw the
outcome. `criteria.confirm_rule_set` can label a rule set `prespecified`, but it needs a
registration reference that resolves (F6) -- and nothing in the repository wrote one, so the label
rested on a caller's say-so.

The split follows the review's §12.1: a manifest cannot hash candidate evidence that has not been
retrieved yet, so **policy** is registered prospectively and the **artifacts actually used** are
bound afterwards. Binding may resolve a prospective reference; it may not change a scientific or
ranking decision. A later change is a new registration and a new experiment, never an edit of this
one -- which is why `register` refuses to overwrite and `verify` reports drift rather than
tolerating it.
"""

from __future__ import annotations

from typing import Any

from .canonical import canonical_text
from .ids import new_id
from .journal import actor as make_actor
from .runtime import Core

# WHY these fields and no others: each one, changed after a result is seen, changes what the result
# means. The list is the review's §12.1 prospective set, trimmed to what this implementation can
# actually state at registration time -- a field nobody can fill before the run is a field that
# invites a placeholder, and a placeholder in a registration is worse than an absent one.
POLICY_FIELDS = (
    "task_ref",                  # task context id and version, with its eligibility semantics
    "criteria_ref",              # the rule set being frozen
    "evidence_cutoff",           # the retrospective date boundary
    "candidate_scope",           # universe definition, source version, identity policy
    "permitted_sources",         # which evidence sources may answer, and their licence gate
    "retrieval_policy",          # queries, routing, budgets, deferred capabilities
    "aggregation_policy",        # compatibility strata, experiment dedup, interval handling
    "missingness_policy",        # what an absent value does to a cell and to a candidate
    "scoring_policy",            # estimator, weights, coverage floor, tie rules
    "primary_board",             # which board carries the registered endpoint, and its rank rule
    "rank_endpoint",             # what counts as the result: ranked-only, or eligibility required
    "recovery_rubric",           # how the historical comparison will classify each item
    "planned_arms",              # every provider/configuration arm intended before unsealing
    "code_commit",               # implementation the registration describes
)

REQUIRED = ("task_ref", "criteria_ref", "primary_board", "rank_endpoint", "scoring_policy")


class FreezeError(RuntimeError):
    pass


def register(core: Core, task_id: str, *, by: dict[str, Any], policy: dict[str, Any],
             supersedes: str | None = None) -> str:
    """Record a prospective policy and return its reference, for `confirm_rule_set`.

    Refuses a policy missing a field whose absence would make the endpoint ambiguous, and refuses
    an unknown field rather than storing something no reader will check.
    """
    unknown = sorted(set(policy) - set(POLICY_FIELDS))
    if unknown:
        raise FreezeError(f"unknown policy fields {unknown}; registering a field nothing reads is "
                          f"a claim nobody can check")
    missing = [f for f in REQUIRED if not policy.get(f)]
    if missing:
        raise FreezeError(f"a registration without {missing} does not fix what the result is")
    record = {
        "preregistration_id": new_id("proto"), "task_id": task_id, "registered_by": by,
        "supersedes": supersedes, "policy": {f: policy.get(f) for f in POLICY_FIELDS},
        # The digest covers the policy alone, so re-registering identical policy is detectable and
        # a timestamp cannot make two different policies look like two of the same.
        "policy_digest": canonical_text({f: policy.get(f) for f in POLICY_FIELDS}),
    }
    artifact_id = core.artifacts.put("preregistration", record)
    core.journal.append(task_id, "preregistration.recorded", actor=by, ids={"task_id": task_id},
                        payload=dict(record, artifact_id=artifact_id),
                        artifact_links=[{"kind": "preregistration", "id": artifact_id}],
                        summary=f"registered {record['preregistration_id']} for {policy['rank_endpoint']}")
    return artifact_id


def registrations(core: Core, task_id: str) -> list[dict[str, Any]]:
    """Every registration against one task, oldest first."""
    out = []
    for event in core.journal.replay(task_id):
        if event.event_type == "preregistration.recorded" and event.payload.get("artifact_id"):
            out.append(dict(core.artifacts.payload(event.payload["artifact_id"]),
                            artifact_id=event.payload["artifact_id"]))
    return out


def verify(core: Core, ref: str, *, actual: dict[str, Any]) -> dict[str, Any]:
    """Compare what ran against what was registered.

    Returns the drifted fields rather than raising: a deviation is a result to report, and a run
    that quietly conformed because the checker refused to look is the failure this prevents.
    """
    try:
        record = core.artifacts.payload(ref)
    except KeyError:
        raise FreezeError(f"registration {ref} does not resolve, so nothing was registered")
    registered = record["policy"]
    drift = [{"field": f, "registered": registered.get(f), "actual": actual[f]}
             for f in actual if f in POLICY_FIELDS
             and canonical_text(actual[f]) != canonical_text(registered.get(f))]
    unregistered = sorted(set(actual) - set(POLICY_FIELDS))
    return {"preregistration_ref": ref, "preregistration_id": record["preregistration_id"],
            "conforms": not drift, "drift": drift, "fields_not_registered": unregistered,
            "checked_fields": sorted(f for f in actual if f in POLICY_FIELDS)}


def bind_artifacts(core: Core, task_id: str, ref: str, *, by: dict[str, Any],
                   captured: dict[str, Any]) -> str:
    """Bind the artifacts a registered run actually used, after retrieval and before final scoring.

    Separate from `register` because a manifest cannot hash evidence that does not exist yet. This
    may resolve a prospective reference; it cannot change a registered scientific or ranking policy,
    so it is recorded as its own artifact pointing at the registration rather than amending it.
    """
    if not registrations(core, task_id):
        raise FreezeError(f"no registration on {task_id} to bind artifacts to")
    record = {"binding_id": new_id("bind"), "task_id": task_id, "preregistration_ref": ref,
              "bound_by": by, "captured": captured, "captured_digest": canonical_text(captured)}
    artifact_id = core.artifacts.put("freeze_binding", record)
    core.journal.append(task_id, "preregistration.recorded", actor=by, ids={"task_id": task_id},
                        payload=dict(record, artifact_id=artifact_id, kind="binding"),
                        artifact_links=[{"kind": "freeze_binding", "id": artifact_id}],
                        summary=f"bound captured artifacts to {ref}")
    return artifact_id
