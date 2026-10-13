"""Budget and Cost Accountant (C6; design §4.6): caps per class, charged before work is done.

Most classes (tool calls, model turns) are charged before the work and refuse once the
cap is reached. Provider spend is known only after a call returns, so it is *recorded*
afterwards; whether reaching its cap stops the run is a setting (`budget.on_exhaust`):
a soft class keeps going and reports each threshold it crosses, a hard class refuses
further work once exhausted.
"""

from __future__ import annotations

import threading
from typing import Any


class Budget:
    """Caps are optional per class; a class without a cap is unbounded but still counted."""

    def __init__(self, envelope: dict[str, Any] | None = None, *, soft_kinds: tuple[str, ...] = (),
                 warn_at: float | None = None):
        self.caps = {k: v for k, v in (envelope or {}).items()
                     if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0}
        self.used: dict[str, float] = {}
        self.soft_kinds = frozenset(soft_kinds)
        self.warn_at = warn_at
        self._crossed: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    def try_charge(self, kind: str, amount: float = 1) -> bool:
        with self._lock:
            cap = self.caps.get(kind)
            used = self.used.get(kind, 0)
            if cap is not None and used + amount > cap and kind not in self.soft_kinds:
                return False
            self.used[kind] = used + amount
            return True

    def allows(self, kind: str) -> bool:
        """Whether work charged to `kind` may start: soft classes always may."""
        return kind in self.soft_kinds or not self.exhausted(kind)

    def record(self, kind: str, amount: float) -> list[str]:
        """Charge an amount known only after the work; return the thresholds newly crossed."""
        with self._lock:
            used = self.used.get(kind, 0) + amount
            self.used[kind] = used
            cap = self.caps.get(kind)
            if cap is None:
                return []
            levels = []
            if self.warn_at is not None and used >= self.warn_at * cap:
                levels.append("warn")
            if used >= cap:
                levels.append("cap")
            fresh = [level for level in levels if (kind, level) not in self._crossed]
            self._crossed.update((kind, level) for level in fresh)
            return fresh

    def remaining(self, kind: str) -> float | None:
        cap = self.caps.get(kind)
        return None if cap is None else cap - self.used.get(kind, 0)

    def exhausted(self, kind: str) -> bool:
        remaining = self.remaining(kind)
        return remaining is not None and remaining <= 0

    def snapshot(self) -> dict[str, Any]:
        return {"caps": dict(self.caps), "used": dict(self.used), "soft_kinds": sorted(self.soft_kinds),
                "warn_at": self.warn_at}


def from_config(config, *, envelope: dict[str, Any] | None = None) -> Budget:
    """A budget for one run from the resolved settings; an explicit envelope wins per class."""
    caps = {"usd": config["budget.usd_max"], "llm_turns": config["budget.llm_turns"],
            "tool_calls": config["budget.tool_calls"]}
    caps.update(envelope or {})
    soft = ("usd",) if config["budget.on_exhaust"] == "warn_continue" else ()
    return Budget(caps, soft_kinds=soft, warn_at=config["budget.warn_at"])
