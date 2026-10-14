"""Human Review Queue (C18): queue items and expert decision records `hd_` (design §12).

An `hd_` is created by a person confirming at a terminal and by nothing else; `decide` refuses any
other actor and any non-interactive entry. An item may instead be resolved without a person by a
`machine_adjudication` (`core/adjudication.py`), which is a separate record with a separate id, a
separate queue state and `approval_kind: agent_verdict`; `items` folds it, and this module never
creates one.
"""

from __future__ import annotations

from typing import Any

from . import vocab
from .clock import utc_now
from .ids import new_id
from .runtime import Core


class ReviewError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def request(core: Core, stream_id: str, *, subject: dict[str, Any], why_expert_required: str,
            requested_by: dict[str, Any], blocking: bool = True, priority: str = "normal",
            inspection_bundle: dict[str, Any] | None = None) -> str:
    vocab.require("hd_subject_kind", subject["kind"])
    item_id = new_id("q")
    item = {"item_id": item_id, "priority": priority, "created_at": utc_now(), "subject": subject,
            "why_expert_required": why_expert_required, "blocking": blocking,
            "requested_by": requested_by, "inspection_bundle": inspection_bundle or {}, "state": "open"}
    core.journal.append(stream_id, "human.review_requested", actor=requested_by,
                        ids={"review_request_id": item_id}, payload=item,
                        summary=f"review requested: {subject['kind']} {subject['id']}")
    return item_id


def items(core: Core, stream_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Queue items folded from the given streams, keyed by item id."""
    out: dict[str, dict[str, Any]] = {}
    for stream_id in stream_ids:
        for event in core.journal.replay(stream_id):
            if event.event_type == "human.review_requested":
                out[event.payload["item_id"]] = dict(event.payload, stream_id=stream_id)
            elif event.event_type == "human.review_decided":
                item = out.get(event.payload["queue_item_ref"])
                if item is not None:
                    item.update(state="decided", decision_id=event.payload["decision_id"],
                                decision=event.payload["decision"])
            elif event.event_type == "human.review_withdrawn":
                item = out.get(event.payload["item_id"])
                if item is not None:
                    item["state"] = "withdrawn"
            elif event.event_type == "decision.recorded" and event.payload.get("adjudication_id"):
                # A machine adjudication (core/adjudication.py) resolves an item without a person. It is
                # folded into its own state, never `decided`, so nothing downstream -- the rule set, the
                # board, the queue page -- can read it as an expert having answered. `decide` still
                # refuses the item afterwards, because its state is not open: an `hd_` stays a person's.
                item = out.get(event.payload["queue_item_ref"])
                if item is not None:
                    item.update(state="machine_adjudicated", adjudication_id=event.payload["adjudication_id"],
                                adjudication_route=event.payload["route"],
                                adjudication_resolution=event.payload["resolution"],
                                adjudication_reason=event.payload["reason_text"],
                                authority=event.payload["authority"])
    return out


def decide(core: Core, item: dict[str, Any], *, decision: str, actor: dict[str, Any], reason_text: str,
           entry: str, edits: list[dict[str, Any]] | None = None,
           historical_list_exposure: str = "undeclared", confidence_qualifier: str = "not_stated") -> dict[str, Any]:
    """Record one expert decision. Only interactive entry by a human may create an `hd_` (design §2.4)."""
    vocab.require("hd_decision", decision)
    if actor.get("kind") != "human":
        raise ReviewError("rejected_unauthorized", "expert decisions are made by people, never by agents")
    if entry != "interactive":
        raise ReviewError("rejected_unauthorized", "expert decisions need interactive confirmation")
    if item.get("state") not in ("open", "in_review"):
        raise ReviewError("rejected_not_permitted_in_state", f"item {item['item_id']} is {item.get('state')}")
    if decision != "approve" and not reason_text.strip():
        raise ReviewError("rejected_invalid", "a reason is required except for approving an unedited proposal")
    if decision == "approve_with_edits" and not edits:
        raise ReviewError("rejected_invalid", "approve_with_edits needs edits")
    vocab.require("historical_list_exposure", historical_list_exposure)
    record = {
        "decision_id": new_id("hd"), "queue_item_ref": item["item_id"], "subject": item["subject"],
        "decision": decision, "edits": edits or [], "reason_text": reason_text, "actor": actor,
        "decided_at": utc_now(), "confidence_qualifier": confidence_qualifier,
        "approval_kind": "human_scientific_approval", "historical_list_exposure": historical_list_exposure,
        "entry": entry, "supersedes_decision_id": None, "disputes_decision_id": None,
    }
    artifact_id = core.artifacts.put("expert_decision", record)
    core.journal.append(item["stream_id"], "human.review_decided", actor=actor,
                        ids={"review_request_id": item["item_id"]}, payload=dict(record, artifact_id=artifact_id),
                        artifact_links=[{"kind": "expert_decision", "id": artifact_id}],
                        summary=f"{decision}: {item['subject']['kind']} {item['subject']['id']}")
    return record
