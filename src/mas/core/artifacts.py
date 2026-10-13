"""Artifact store (C3): content-addressed, write-once envelopes (design §4.3, §14)."""

from __future__ import annotations

import json
from typing import Any

from . import vocab
from .canonical import canonical_text, sha256_hex
from .clock import utc_now
from .store import Store


class ArtifactStore:
    def __init__(self, store: Store):
        self.store = store

    def put(self, kind: str, payload: dict[str, Any], *, schema_version: int = 1) -> str:
        """Store an artifact and return its id; storing identical content again returns the same id."""
        envelope = {
            "kind": kind,
            "schema_version": schema_version,
            "vocabulary_version": vocab.VOCABULARY_VERSION,
            "payload": payload,
        }
        digest = sha256_hex(envelope)
        artifact_id = f"art_{digest[:12]}"
        with self.store.write_lock:
            return self._put_locked(artifact_id, digest, kind, envelope)

    def _put_locked(self, artifact_id: str, digest: str, kind: str, envelope: dict[str, Any]) -> str:
        db = self.store.db
        existing = db.execute("SELECT sha256 FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
        if existing:
            if existing[0] != digest:
                raise ValueError(f"artifact id collision on {artifact_id}")
            return artifact_id
        db.execute(
            "INSERT INTO artifacts (artifact_id, kind, sha256, body, created_at) VALUES (?, ?, ?, ?, ?)",
            (artifact_id, kind, digest, canonical_text(envelope), utc_now()),
        )
        return artifact_id

    def get(self, artifact_id: str) -> dict[str, Any]:
        row = self.store.db.execute("SELECT body FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
        if row is None:
            raise KeyError(artifact_id)
        return json.loads(row[0])

    def payload(self, artifact_id: str) -> dict[str, Any]:
        return self.get(artifact_id)["payload"]

    def of_kind(self, kind: str) -> list[tuple[str, dict[str, Any]]]:
        rows = self.store.db.execute("SELECT artifact_id, body FROM artifacts WHERE kind = ? ORDER BY created_at", (kind,))
        return [(artifact_id, json.loads(body)["payload"]) for artifact_id, body in rows]
