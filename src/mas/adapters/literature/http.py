"""Shared HTTP handling: map transport and status failures to the broker's error classes."""

from __future__ import annotations

import requests

from mas.core.broker import ToolAbsent, ToolError

USER_AGENT = "mas-literature/0.1 (evidence-driven candidate prioritization; research use)"


def get(url: str, *, params: dict | None = None, timeout_s: float = 60, expect: str = "json"):
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
