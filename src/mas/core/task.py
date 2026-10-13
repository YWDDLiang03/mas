"""Task Context Normalizer (C4): explicit, versioned task contexts (design §4.4)."""

from __future__ import annotations

from typing import Any

from . import vocab
from .ids import new_id
from .runtime import Core

DEFAULT_GROUP = "grp_default"


class TaskContextInvalid(ValueError):
    pass


def validate(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Check mandatory fields; return the unknowns that remain (blocking ones stop a run)."""
    for field in ("objective_text", "mode", "evaluation_scope"):
        if not spec.get(field):
            raise TaskContextInvalid(f"{field} is mandatory")
    vocab.require("task_mode", spec["mode"])
    universe = spec.get("candidate_universe") or {}
    seeds = spec.get("seed_candidates") or []
    if not universe.get("members") and not universe.get("access_path") and not seeds:
        raise TaskContextInvalid("a candidate universe or a seed set is mandatory")
    if spec["mode"] == "conditional" and not (spec.get("constraints") or spec.get("scope_entities")):
        raise TaskContextInvalid("conditional mode needs at least one constraint or scope entity")
    return list(spec.get("unknowns") or [])


def record_version(core: Core, spec: dict[str, Any], *, by: dict[str, Any], task_id: str | None = None) -> tuple[str, int]:
    """Create a task (no `task_id`) or a new version of one. Returns (task_id, version)."""
    unknowns = validate(spec)
    if task_id is None:
        task_id, version, supersedes = new_id("task"), 1, None
    else:
        previous = latest_version(core, task_id)
        version, supersedes = previous + 1, f"{task_id}@v{previous}"
    record = dict(spec)
    record.update({
        "task_context_id": task_id, "version": version, "supersedes": supersedes,
        "group_id": spec.get("group_id", DEFAULT_GROUP), "unknowns": unknowns,
        "created_by": by,
    })
    artifact_id = core.artifacts.put("task_context", record)
    core.journal.append(task_id, "task.version_recorded", actor=by,
                        ids={"task_id": task_id}, payload={"version": version, "artifact_id": artifact_id},
                        artifact_links=[{"kind": "task_context", "id": artifact_id, "version": version}],
                        summary=f"task context {task_id}@v{version}")
    return task_id, version


def latest_version(core: Core, task_id: str) -> int:
    versions = [e.payload["version"] for e in core.journal.replay(task_id) if e.event_type == "task.version_recorded"]
    if not versions:
        raise KeyError(f"no such task {task_id}")
    return max(versions)


def get(core: Core, task_id: str, version: int | None = None) -> dict[str, Any]:
    wanted = version or latest_version(core, task_id)
    for event in core.journal.replay(task_id):
        if event.event_type == "task.version_recorded" and event.payload["version"] == wanted:
            return core.artifacts.payload(event.payload["artifact_id"])
    raise KeyError(f"{task_id}@v{wanted}")


def list_tasks(core: Core, group_id: str | None = None) -> list[dict[str, Any]]:
    out = []
    for stream in core.journal.streams("task_"):
        context = get(core, stream)
        if group_id is None or context.get("group_id") == group_id:
            out.append(context)
    return out


def blocking_unknowns(context: dict[str, Any]) -> list[dict[str, Any]]:
    return [u for u in context.get("unknowns", []) if u.get("blocking") and u.get("resolution_state") != "answered"]

