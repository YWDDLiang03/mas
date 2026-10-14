"""Identifiers (design §0.3): opaque strings with a type prefix around a ULID."""

from __future__ import annotations

import os
import re
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Prefixes registered in design §0.3; an identifier with any other prefix is refused.
PREFIXES = frozenset({
    "task", "run", "att", "round", "stage", "step", "xchg", "evt", "art", "src", "claim", "loc",
    "ig", "attr", "rule", "rules", "chg", "cand", "asm", "rsn", "lb", "lbd", "evs", "tool", "inv",
    "res", "mem", "hd", "q", "oq", "plan", "brief", "ret", "ckpt", "strat", "proto", "evr", "sub",
    "const", "bind", "ops", "ses", "cmd", "chain", "grp", "case",
    "cri",   # criterion lineage in the derivation pool (iteration 2)
    "expr",  # registered scoring expression (iteration 2)
    "adj",   # machine adjudication of a review queue item (core/adjudication.py); never an `hd_`
    "clp",   # collapse of several registrations of one quantity (core/collapse.py); never an `hd_`
    "hci",   # historical-criteria intake: the sealed comparison list (core/recovery.py, design §8.6)
})


def ulid(timestamp_ms: int | None = None) -> str:
    """A 26-character, time-sortable unique id (48-bit milliseconds, 80 random bits)."""
    ms = int(time.time() * 1000) if timestamp_ms is None else timestamp_ms
    value = (ms << 80) | int.from_bytes(os.urandom(10), "big")
    chars = []
    for _ in range(26):
        chars.append(_CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def new_id(prefix: str) -> str:
    if prefix not in PREFIXES:
        raise ValueError(f"unregistered identifier prefix: {prefix!r}")
    return f"{prefix}_{ulid()}"


def prefix_of(identifier: str) -> str:
    return identifier.split("_", 1)[0]


def versioned(base: str, version: int) -> str:
    """`attr_<slug>@v<n>` style reference."""
    if version < 0:
        raise ValueError("versions start at 0")
    return f"{base}@v{version}"


_VERSIONED = re.compile(r"^(?P<base>.+)@v(?P<version>\d+)$")


def split_version(ref: str) -> tuple[str, int]:
    match = _VERSIONED.match(ref)
    if not match:
        raise ValueError(f"not a versioned reference: {ref!r}")
    return match["base"], int(match["version"])


def slug(text: str) -> str:
    """Lowercase ASCII slug for slug-based identifiers (`attr_<slug>`, `grp_<slug>`)."""
    out = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    if not out:
        raise ValueError(f"cannot make a slug from {text!r}")
    return out
