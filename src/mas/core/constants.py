"""Registered constants (design §8.4): every number affecting a published verdict or a host behaviour."""

from __future__ import annotations

from typing import Any

from .canonical import sha256_hex
from .journal import EVAL_STREAM
from .runtime import Core

SCOPES = ("core_policy", "adapter_policy", "case_configuration")

# Core-policy engineering constants with their defaults (design §8.4, §14.1, §10.5).
CORE_DEFAULTS: dict[str, tuple[Any, str]] = {
    "const_review_claim_lease": (3600, "s"),
    "const_host_suspend_threshold": (120, "s"),
    "const_store_write_retry_limit": (5, "attempts"),
    "const_reflection_item_cap": (3, "items"),
    "const_sweep_tool_failure_share": (0.5, "fraction"),
    "const_tool_retry_limit": (3, "attempts"),
    "const_ranking_coverage_floor": (0.5, "fraction"),
}


def register(core: Core, const_id: str, value: Any, *, unit: str, scope: str, cutoff_basis: str,
             set_by: dict[str, Any], stream_id: str = EVAL_STREAM) -> dict[str, Any]:
    if not const_id.startswith("const_"):
        raise ValueError("constant ids start with const_")
    if scope not in SCOPES:
        raise ValueError(f"unknown constant scope {scope!r}")
    record = {"const_id": const_id, "scope": scope, "value": value, "unit": unit,
              "cutoff_basis": cutoff_basis, "set_by": set_by, "sensitivity_tested": {"yes": False}}
    core.journal.append(stream_id, "constant.registered", actor=set_by, payload=record,
                        summary=f"{const_id} = {value} {unit}")
    return record


def current(core: Core, const_id: str, stream_ids: tuple[str, ...] = (EVAL_STREAM,)) -> dict[str, Any] | None:
    """Latest registration of a constant across the given streams, or None."""
    latest = None
    for stream_id in stream_ids:
        for event in core.journal.replay(stream_id):
            if event.event_type == "constant.registered" and event.payload["const_id"] == const_id:
                latest = event.payload
    return latest


def value(core: Core, const_id: str, stream_ids: tuple[str, ...] = (EVAL_STREAM,)) -> Any:
    record = current(core, const_id, stream_ids)
    if record is not None:
        return record["value"]
    if const_id in CORE_DEFAULTS:
        return CORE_DEFAULTS[const_id][0]
    raise KeyError(f"{const_id} is not registered")


def constants_hash(records: list[dict[str, Any]]) -> str:
    return sha256_hex(sorted(records, key=lambda r: r["const_id"]))
