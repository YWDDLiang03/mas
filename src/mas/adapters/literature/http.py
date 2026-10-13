"""Shared HTTP handling: map transport and status failures to the broker's error classes."""

from __future__ import annotations

import threading
import time
from urllib.parse import urlparse

import requests

from mas.core.broker import ToolAbsent, ToolError

USER_AGENT = "mas/0.1 (evidence-driven candidate prioritization; research use)"

# Minimum seconds between requests to one host (polite use of public services).
MIN_INTERVAL_S = {"pubchem.ncbi.nlm.nih.gov": 0.25, "eutils.ncbi.nlm.nih.gov": 0.4, "www.ebi.ac.uk": 0.1}
_last_call: dict[str, float] = {}
_lock = threading.Lock()


def _throttle(url: str) -> None:
    host = urlparse(url).netloc
    interval = MIN_INTERVAL_S.get(host, 0.0)
    with _lock:
        wait = _last_call.get(host, 0.0) + interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.monotonic()


def get(url: str, *, params: dict | None = None, timeout_s: float = 60, expect: str = "json"):
    _throttle(url)
    try:
        reply = requests.get(url, params=params, timeout=timeout_s, headers={"User-Agent": USER_AGENT})
    except requests.Timeout:
        raise ToolError("timeout", url) from None
    except requests.ConnectionError as error:
        raise ToolError("transient_network", str(error)[:200]) from None
    if reply.status_code == 404:
        return None
    if reply.status_code == 429:
        raise ToolError("rate_limited", url)
    if reply.status_code in (401, 403):
        raise ToolAbsent("unauthorized", f"{reply.status_code} from {url}")
    if reply.status_code >= 500:
        raise ToolError("upstream_server_error", f"{reply.status_code} from {url}")
    if reply.status_code >= 400:
        raise ToolError("input_invalid", f"{reply.status_code} from {url}: {reply.text[:200]}", retryable=False)
    if expect == "json":
        try:
            return reply.json()
        except ValueError:
            raise ToolError("parse_failed", f"non-JSON reply from {url}", retryable=False) from None
    return reply.text
