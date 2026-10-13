"""Event Journal (C1): append-only journals, one contiguous `seq` space per stream.

The journal is the only source of truth (ADR-01). Every other view is a fold over
committed events. Streams are run, task, group, case, and the store-level
evaluation stream (design §2.4). `seq` is assigned by the store at write time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator

from . import vocab
from .canonical import canonical_text, sha256_hex
from .clock import utc_now
from .ids import new_id
from .store import Store

STREAM_PREFIXES = ("run_", "task_", "grp_", "case_", "eval")
EVAL_STREAM = "eval"


@dataclass(frozen=True)
class Event:
    stream_id: str
    seq: int
    event_id: str
    event_type: str
    emitted_at: str
    recorded_at: str
    actor: dict[str, Any]
    ids: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    payload_hash: str = ""
    parent_seq: int | None = None
    cause_seq: int | None = None
    state_from: str | None = None
    state_to: str | None = None
    termination_reason: str | None = None
    question: str | None = None
    summary: str | None = None
    progress: dict[str, Any] | None = None
    budget: dict[str, Any] | None = None
    artifact_links: tuple[dict[str, Any], ...] = ()
    visibility: str = "default"
    vocabulary_version: str = vocab.VOCABULARY_VERSION

    def to_record(self) -> dict[str, Any]:
        record = {k: v for k, v in self.__dict__.items()}
        record["artifact_links"] = list(self.artifact_links)
        return record

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "Event":
        record = dict(record)
        record["artifact_links"] = tuple(record.get("artifact_links") or ())
        return cls(**record)


def actor(kind: str, actor_id: str, role: str | None = None, **extra: Any) -> dict[str, Any]:
    """An event actor record (`actor {kind, id, role, version, model_family?, via?}`)."""
    vocab.require("actor_kind", kind)
    record = {"kind": kind, "id": actor_id, "role": role}
    record.update({k: v for k, v in extra.items() if v is not None})
    return record


def _check_stream(stream_id: str) -> None:
    if not (stream_id == EVAL_STREAM or stream_id.startswith(STREAM_PREFIXES[:-1])):
        raise ValueError(f"not a stream id: {stream_id!r} (run_, task_, grp_, case_, or eval)")


class Journal:
    def __init__(self, store: Store):
        self.store = store

    def append(
        self,
        stream_id: str,
        event_type: str,
        *,
        actor: dict[str, Any],
        ids: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        parent_seq: int | None = None,
        cause_seq: int | None = None,
        state_from: str | None = None,
        state_to: str | None = None,
        termination_reason: str | None = None,
        question: str | None = None,
        summary: str | None = None,
        progress: dict[str, Any] | None = None,
        budget: dict[str, Any] | None = None,
        artifact_links: Iterable[dict[str, Any]] = (),
        visibility: str = "default",
        emitted_at: str | None = None,
    ) -> Event:
        _check_stream(stream_id)
        vocab.require_event_kind(event_type)
        vocab.require("actor_kind", actor.get("kind", ""))
        vocab.require("visibility", visibility)
        for state in (state_from, state_to):
            if state is not None:
                vocab.require("execution", state)
        if termination_reason is not None:
            vocab.require("termination_reason", termination_reason)
        payload = payload or {}
        with self.store.write_lock:
            return self._append_locked(stream_id, event_type, actor=actor, ids=ids, payload=payload, parent_seq=parent_seq,
                                       cause_seq=cause_seq, state_from=state_from, state_to=state_to,
                                       termination_reason=termination_reason, question=question, summary=summary,
                                       progress=progress, budget=budget, artifact_links=artifact_links,
                                       visibility=visibility, emitted_at=emitted_at)

    def _append_locked(self, stream_id, event_type, *, actor, ids, payload, parent_seq, cause_seq, state_from, state_to,
                       termination_reason, question, summary, progress, budget, artifact_links, visibility, emitted_at) -> Event:
        db = self.store.db
        db.execute("BEGIN IMMEDIATE")
        try:
            row = db.execute("SELECT COALESCE(MAX(seq), 0) FROM events WHERE stream_id = ?", (stream_id,)).fetchone()
            recorded_at = utc_now()
            event = Event(
                stream_id=stream_id,
                seq=row[0] + 1,
                event_id=new_id("evt"),
                event_type=event_type,
                emitted_at=emitted_at or recorded_at,
                recorded_at=recorded_at,
                actor=actor,
                ids=ids or {},
                payload=payload,
                payload_hash=sha256_hex(payload),
                parent_seq=parent_seq,
                cause_seq=cause_seq,
                state_from=state_from,
                state_to=state_to,
                termination_reason=termination_reason,
                question=question,
                summary=summary,
                progress=progress,
                budget=budget,
                artifact_links=tuple(artifact_links),
                visibility=visibility,
            )
            record = event.to_record()
            db.execute(
                "INSERT INTO events (stream_id, seq, event_id, event_type, recorded_at, body, body_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (stream_id, event.seq, event.event_id, event_type, recorded_at, canonical_text(record), sha256_hex(record)),
            )
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
        return event

    def replay(self, stream_id: str, from_seq: int = 1, to_seq: int | None = None) -> list[Event]:
        """Events of one stream in `seq` order, from `from_seq` through `to_seq` inclusive."""
        query = "SELECT body FROM events WHERE stream_id = ? AND seq >= ?"
        params: list[Any] = [stream_id, from_seq]
        if to_seq is not None:
            query += " AND seq <= ?"
            params.append(to_seq)
        query += " ORDER BY seq"
        return [Event.from_record(json.loads(body)) for (body,) in self.store.db.execute(query, params)]

    def last_seq(self, stream_id: str) -> int:
        row = self.store.db.execute("SELECT COALESCE(MAX(seq), 0) FROM events WHERE stream_id = ?", (stream_id,)).fetchone()
        return row[0]

    def streams(self, prefix: str = "") -> list[str]:
        rows = self.store.db.execute(
            "SELECT DISTINCT stream_id FROM events WHERE stream_id LIKE ? ORDER BY stream_id", (prefix + "%",)
        )
        return [stream for (stream,) in rows]

    def of_type(self, event_type: str, stream_prefix: str = "") -> Iterator[Event]:
        """Events of one kind across streams, in (stream, seq) order."""
        vocab.require_event_kind(event_type)
        rows = self.store.db.execute(
            "SELECT body FROM events WHERE event_type = ? AND stream_id LIKE ? ORDER BY stream_id, seq",
            (event_type, stream_prefix + "%"),
        )
        for (body,) in rows:
            yield Event.from_record(json.loads(body))

    def verify(self, stream_id: str) -> None:
        """Check contiguity and record hashes of one stream; raise on any inconsistency."""
        expected = 1
        for seq, body, body_hash in self.store.db.execute(
            "SELECT seq, body, body_hash FROM events WHERE stream_id = ? ORDER BY seq", (stream_id,)
        ):
            if seq != expected:
                raise ValueError(f"{stream_id}: seq gap at {expected}")
            if sha256_hex(json.loads(body)) != body_hash:
                raise ValueError(f"{stream_id}: record hash mismatch at seq {seq}")
            expected += 1
