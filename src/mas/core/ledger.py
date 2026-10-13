"""Evidence Ledger (C9): sources, claims with exact locations, admission, snapshots (design §4.9, §8.5)."""

from __future__ import annotations

from typing import Any

from .canonical import sha256_hex
from .clock import utc_now
from .ids import new_id
from .runtime import Core

ADMISSION_STATES = ("pending", "admitted", "quarantined", "rejected", "superseded")
SOURCE_STATUSES = ("peer_reviewed_paper", "preprint", "database_entry", "technical_report", "curated_measurement",
                   "model_prediction_record", "experiment_record", "expert_statement",
                   "reference_text",          # edited textbook or reference-work chapter
                   "tertiary_reference",      # encyclopedia or wiki article, revision-pinned
                   "user_supplied_document")  # uploaded by the user with a rights declaration
ACCESS_STATES = ("full_text_available", "abstract_only", "metadata_only", "paywalled", "fetch_failed")
READING_DEPTHS = ("title_only", "title_abstract", "full_text", "supplementary", "not_read")


def put_source(core: Core, source: dict[str, Any]) -> str:
    """Store a source record; the same identifiers and version give the same source id."""
    if source.get("source_status") not in SOURCE_STATUSES:
        raise ValueError(f"bad source_status {source.get('source_status')!r}")
    if source.get("access_state", "metadata_only") not in ACCESS_STATES:
        raise ValueError(f"bad access_state {source.get('access_state')!r}")
    if not source.get("source_id"):
        first = source["identifiers"][0]
        source = dict(source, source_id=f"src_{first['scheme']}_{first['value']}")
    core.artifacts.put("source", source)
    return source["source_id"]


def record_claim(core: Core, stream_id: str, claim: dict[str, Any], *, by: dict[str, Any],
                 admission_state: str, admission_reasons: list[str], ids: dict[str, Any] | None = None) -> str:
    """Store a claim and journal its admission decision; returns the claim id."""
    if admission_state not in ADMISSION_STATES:
        raise ValueError(f"bad admission_state {admission_state!r}")
    location = claim.get("location") or {}
    if not location.get("location_kind") or "locator_value" not in location:
        raise ValueError("a claim needs a location with location_kind and locator_value")
    if claim.get("reading_depth", "not_read") not in READING_DEPTHS:
        raise ValueError(f"bad reading_depth {claim.get('reading_depth')!r}")
    record = dict(claim, claim_id=claim.get("claim_id") or new_id("claim"), admission_state=admission_state,
                  admission_reasons=admission_reasons, recorded_at=utc_now(), extraction_actor=by)
    artifact_id = core.artifacts.put("claim", record)
    event = "evidence.admitted" if admission_state == "admitted" else "evidence.quarantined"
    core.journal.append(stream_id, event, actor=by, ids=ids or {},
                        payload={"claim_id": record["claim_id"], "artifact_id": artifact_id,
                                 "admission_state": admission_state, "reasons": admission_reasons,
                                 "candidate_ref": claim.get("candidate_ref"),
                                 "attribute_ref": claim.get("attribute_ref"),
                                 "source_ref": claim.get("source_ref")},
                        artifact_links=[{"kind": "claim", "id": artifact_id}],
                        summary=f"claim {admission_state}: {claim.get('normalized_statement', '')[:80]}")
    return record["claim_id"]


def claims(core: Core, stream_ids: list[str], *, candidate_ref: str | None = None, attribute_ref: str | None = None,
           admitted_only: bool = True) -> list[dict[str, Any]]:
    out = []
    for stream_id in stream_ids:
        for event in core.journal.replay(stream_id):
            if event.event_type not in ("evidence.admitted", "evidence.quarantined"):
                continue
            if admitted_only and event.payload["admission_state"] != "admitted":
                continue
            if candidate_ref and event.payload.get("candidate_ref") != candidate_ref:
                continue
            if attribute_ref and event.payload.get("attribute_ref") != attribute_ref:
                continue
            out.append(core.artifacts.payload(event.payload["artifact_id"]))
    return out


def freeze_snapshot(core: Core, stream_id: str, *, task_id: str, claim_ids: list[str], cutoff_at: str,
                    tool_manifest: list[dict[str, Any]], by: dict[str, Any]) -> str:
    """Freeze an evidence snapshot `evs_<task>_<n>` over admitted claim ids."""
    existing = [e for e in core.journal.of_type("evidence.snapshot_frozen")
                if e.payload.get("task_id") == task_id]
    snapshot_id = f"evs_{task_id}_{len(existing) + 1}"
    record = {"snapshot_id": snapshot_id, "task_id": task_id, "claim_ids": sorted(claim_ids),
              "cutoff_at": cutoff_at, "tool_availability_snapshot": tool_manifest}
    record["hash"] = sha256_hex(record)
    artifact_id = core.artifacts.put("evidence_snapshot", record)
    core.journal.append(stream_id, "evidence.snapshot_frozen", actor=by,
                        payload={"snapshot_id": snapshot_id, "task_id": task_id, "artifact_id": artifact_id,
                                 "n_claims": len(claim_ids), "hash": record["hash"]},
                        artifact_links=[{"kind": "evidence_snapshot", "id": artifact_id}],
                        summary=f"{snapshot_id} frozen with {len(claim_ids)} claims")
    return snapshot_id
