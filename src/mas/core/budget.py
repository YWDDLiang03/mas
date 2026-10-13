"""Budget and Cost Accountant (C6; design §4.6): caps per class, charged before work is done."""

from __future__ import annotations

from typing import Any


class Budget:
    """Caps are optional per class; a class without a cap is unbounded but still counted."""

    def __init__(self, envelope: dict[str, Any] | None = None):
        self.caps = {k: v for k, v in (envelope or {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        self.used: dict[str, float] = {}

    def try_charge(self, kind: str, amount: float = 1) -> bool:
        cap = self.caps.get(kind)
        used = self.used.get(kind, 0)
        if cap is not None and used + amount > cap:
            return False
        self.used[kind] = used + amount
        return True

    def remaining(self, kind: str) -> float | None:
        cap = self.caps.get(kind)
        return None if cap is None else cap - self.used.get(kind, 0)

    def exhausted(self, kind: str) -> bool:
        remaining = self.remaining(kind)
        return remaining is not None and remaining <= 0

    def snapshot(self) -> dict[str, Any]:
        return {"caps": dict(self.caps), "used": dict(self.used)}
