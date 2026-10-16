"""Local display choices for the workbench; scientific records are never edited."""
from __future__ import annotations

import copy
import json
from pathlib import Path


class WorkspaceDisplay:
    def __init__(self, path: Path):
        self.path = Path(path)

    def settings(self) -> dict:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version", 1) != 1:
            raise ValueError("Unsupported workspace display settings")
        return data

    def task_visible(self, task_id: str | None) -> bool:
        return not task_id or task_id not in self.settings().get("archived_task_ids", [])

    def task(self, record: dict) -> dict:
        result = copy.deepcopy(record)
        custom = self.settings().get("task_labels", {}).get(record["task_id"])
        if custom:
            result.update(recorded_title=record.get("title"), title=custom)
        return result

    def tasks(self, records: list[dict]) -> list[dict]:
        return [self.task(row) for row in records if self.task_visible(row["task_id"])]

    def workflow(self, record: dict) -> dict:
        result = copy.deepcopy(record)
        custom = self.settings().get("task_labels", {}).get(record.get("task_id"))
        if custom:
            result.update(recorded_title=record.get("title"), title=custom)
        return result

    def workflow_visible(self, record: dict) -> bool:
        data = self.settings()
        return (self.task_visible(record.get("task_id"))
                and record.get("workflow_id") not in data.get("archived_workflow_ids", []))

    def workflows(self, records: list[dict]) -> list[dict]:
        return [self.workflow(row) for row in records if self.workflow_visible(row)]

    def drafts(self, records: list[dict]) -> list[dict]:
        hidden = self.settings().get("archived_draft_ids", [])
        return [row for row in records if row["draft_id"] not in hidden]

    def libraries(self, records: list[dict]) -> list[dict]:
        hidden = self.settings().get("archived_library_ids", [])
        return [row for row in records if row["id"] not in hidden]

    def snapshots(self, records: list[dict]) -> list[dict]:
        data = self.settings()
        hidden, labels = data.get("archived_snapshot_ids", []), data.get("snapshot_labels", {})
        return [dict(row, label=labels.get(row["snapshot_id"]) or row.get("label"))
                for row in records if row["snapshot_id"] not in hidden]
