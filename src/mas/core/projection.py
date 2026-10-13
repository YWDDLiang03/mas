"""Progress Projection (C17; design §11): a pure fold over one run's journal.

No cross-stage percentage: each scope reports its own denominator kind; a percentage
is given only for `enumerated_fixed`; the budget is a separate meter.
"""

from __future__ import annotations

from typing import Any

from . import vocab
from .runtime import Core


def progress(core: Core, run_id: str) -> dict[str, Any]:
    state, termination, last_activity = None, None, None
    scopes: dict[str, dict[str, Any]] = {}
    budget: dict[str, Any] | None = None
    verdicts: dict[str, int] = {}
    snapshot_id = None
    for event in core.journal.replay(run_id):
        last_activity = event.recorded_at
        if event.event_type.startswith("run.") and event.state_to:
            state = event.state_to
            termination = event.termination_reason or termination
        if event.progress:
            scopes[event.progress["scope"]] = dict(event.progress)
        if event.budget:
            budget = event.budget
        if event.event_type == "candidate.assessed":
            verdict = event.payload["verdict"]
            verdicts[verdict] = verdicts.get(verdict, 0) + 1
        if event.event_type == "leaderboard.snapshot_published":
            snapshot_id = event.payload["snapshot_id"]
    rows = []
    for scope, item in scopes.items():
        row = dict(item)
        if item["denominator_kind"] == "enumerated_fixed" and item.get("planned"):
            row["percent"] = round(100 * item["completed"] / item["planned"])
        rows.append(row)
    return {"run_id": run_id, "state": state, "state_label": vocab.label("execution", state) if state else None,
            "termination_reason": termination, "progress": rows, "budget": budget, "verdict_counts": verdicts,
            "last_activity_at": last_activity, "snapshot_id": snapshot_id}
