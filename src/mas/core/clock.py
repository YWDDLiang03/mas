"""Time (design §14.2): UTC timestamps; durations from a monotonic clock."""

from __future__ import annotations

import time
from datetime import datetime, timezone


def utc_now() -> str:
    """UTC timestamp with millisecond precision, e.g. 2026-10-13T08:41:02.123Z."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def monotonic_s() -> float:
    return time.monotonic()
