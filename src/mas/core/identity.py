"""Identity Service (design §8.2): candidate identity records driven by adapter identifier schemes.

The core knows no domain identifier: the adapter declares the primary scheme used
in candidate ids, and providers answer `entity_resolution` questions.
"""

from __future__ import annotations

from typing import Any

from . import review
from .ids import slug
from .journal import actor as make_actor
from .runtime import Core

LINK_BASES = ("exact_identifier_match", "authority_crosswalk", "name_match_single_candidate",
              "name_match_ambiguous", "unresolved")


def candidate_id(scheme: str, value: str) -> str:
    return f"cand_{scheme}-{value}"


def resolve_universe(core: Core, broker, stream_id: str, members: list[str], *, primary_scheme: str,
                     capability: str = "entity_resolution", question_kind: str = "resolve_name",
                     ids: dict[str, Any] | None = None, budget: Any = None) -> list[dict[str, Any]]:
    """Resolve every universe member; every member leaves with an identity record."""
    who = make_actor("agent", "identity-service", "identity_service")
    records = []
    for label in members:
        result = broker.call(stream_id, capability, question_kind, {"name": label}, requesting_actor=who,
                             ids=ids, budget=budget)
        hits = [v for v in result.values if v.get("name") == "identity"]
        if result.outcome in ("ok", "partial") and len(hits) == 1:
            hit = hits[0]["value"]
            scheme_value = next((i["value"] for i in hit["identifiers"] if i["scheme"] == primary_scheme), None)
            basis = hit.get("link_basis", "name_match_single_candidate")
            if scheme_value is None:
                basis, cand = "unresolved", candidate_id("name", slug(label))
            else:
                cand = candidate_id(primary_scheme, scheme_value)
            record = {"candidate_id": cand, "preferred_label": hit.get("preferred_label", label), "input_label": label,
                      "identifiers": hit["identifiers"], "aliases": hit.get("aliases", []),
                      "identity_link_basis": basis, "identity_review_state": "not_required",
                      "tool_result_ref": result.result_id}
        else:
            ambiguous = len(hits) > 1
            record = {"candidate_id": candidate_id("name", slug(label)), "preferred_label": label, "input_label": label,
                      "identifiers": [], "aliases": [],
                      "identity_link_basis": "name_match_ambiguous" if ambiguous else "unresolved",
                      "identity_review_state": "pending" if ambiguous else "not_required",
                      "candidates_offered": [h["value"] for h in hits] if ambiguous else [],
                      "tool_result_ref": result.result_id, "tool_outcome": result.outcome}
            if ambiguous:
                review.request(core, stream_id, subject={"kind": "identity_merge", "id": record["candidate_id"]},
                               why_expert_required="name_match_ambiguous identity", requested_by=who, blocking=False)
        artifact_id = core.artifacts.put("identity_record", record)
        core.journal.append(stream_id, "identity.resolved", actor=who, ids=dict(ids or {}),
                            payload={"candidate_id": record["candidate_id"], "input_label": label,
                                     "identity_link_basis": record["identity_link_basis"], "artifact_id": artifact_id},
                            artifact_links=[{"kind": "identity_record", "id": artifact_id}],
                            summary=f"{label}: {record['identity_link_basis']}")
        records.append(record)
    return records


def is_resolved(record: dict[str, Any]) -> bool:
    return record["identity_link_basis"] in ("exact_identifier_match", "authority_crosswalk", "name_match_single_candidate")
