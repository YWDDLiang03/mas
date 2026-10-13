"""Canonical serialization and hashing (design §4.3, §14.2).

Every hashed record is serialized in one canonical form: UTF-8 without a byte-order
mark, Unicode NFC, LF line endings inside strings, keys sorted, no insignificant
whitespace, and shortest round-trip float formatting. Record hashes, payload hashes,
fingerprints, and projection hashes are computed on these bytes, never on
platform-native text. Files people supply are hashed on their raw bytes instead.
"""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from typing import Any

CANONICAL_FORM_VERSION = "canon-1"


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical form has no representation for NaN or infinity")
        return value
    if isinstance(value, str):
        text = value.replace("\r\n", "\n").replace("\r", "\n")
        return unicodedata.normalize("NFC", text)
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"canonical form needs string keys, got {type(key).__name__}")
            norm_key = unicodedata.normalize("NFC", key)
            if norm_key in out:
                raise ValueError(f"keys collide after normalization: {key!r}")
            out[norm_key] = _normalize(item)
        return out
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    raise TypeError(f"no canonical form for {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    """The canonical byte form of a JSON-compatible value."""
    return json.dumps(
        _normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_text(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8")


def sha256_hex(value: Any) -> str:
    """Hash of a record in canonical form."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def raw_sha256(data: bytes) -> str:
    """Hash of supplied file bytes, unaltered (`content_hash`, design §12.4)."""
    return hashlib.sha256(data).hexdigest()


def text_sha256(text: str) -> str:
    """Duplicate-detection hash of a text file's canonical text (`text_hash`, design §14.2)."""
    return hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()
