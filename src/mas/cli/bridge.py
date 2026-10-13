"""Subagent bridge commands: let an outside agent answer model requests.

    python -m mas.cli.bridge next   --dir DIR [--wait SECONDS]   print the oldest unanswered request
    python -m mas.cli.bridge answer --dir DIR REQUEST_ID [--file PATH]   write a response (JSON on stdin by default)
    python -m mas.cli.bridge status --dir DIR

A response body is either a JSON value matching the request's response_schema, or an
object {"text": "..."} for free-text requests. The bridge adds request_id, model_id,
and answered_by.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


CLAIM_TIMEOUT_S = 1800


def _pending(root: Path) -> list[Path]:
    answered = {p.stem for p in (root / "responses").glob("*.json")}
    requests = sorted((root / "requests").glob("*.json"), key=lambda p: p.stat().st_mtime)
    return [p for p in requests if p.stem not in answered]


def _claim(root: Path, request: Path, agent: str) -> bool:
    """Claim a request atomically; a claim older than CLAIM_TIMEOUT_S may be taken over."""
    claims = root / "claims"
    claims.mkdir(exist_ok=True)
    marker = claims / f"{request.stem}.claim"
    try:
        handle = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if marker.read_text() == agent:
            return True  # re-deliver to the agent that claimed it (for example after a failed answer)
        if time.time() - marker.stat().st_mtime < CLAIM_TIMEOUT_S:
            return False
        marker.unlink(missing_ok=True)
        return _claim(root, request, agent)
    with os.fdopen(handle, "w") as out:
        out.write(agent)
    return True


def cmd_next(root: Path, wait_s: float, agent: str = "agent") -> int:
    deadline = time.monotonic() + wait_s
    while True:
        for request in _pending(root):
            if _claim(root, request, agent):
                print(request.read_text(encoding="utf-8"))
                return 0
        if (root / "DONE").exists() and not _pending(root):
            print(json.dumps({"status": "done"}))
            return 3
        if time.monotonic() > deadline:
            print(json.dumps({"status": "no_pending_request", "waited_s": wait_s}))
            return 2
        time.sleep(1.0)


def cmd_answer(root: Path, request_id: str, source: str | None, model_id: str, answered_by: str) -> int:
    if not (root / "requests" / f"{request_id}.json").exists():
        print(f"no such request {request_id}", file=sys.stderr)
        return 1
    raw = Path(source).read_text(encoding="utf-8") if source else sys.stdin.read()
    body = json.loads(raw)
    response = {"request_id": request_id, "model_id": model_id, "answered_by": answered_by}
    if isinstance(body, dict) and set(body) == {"text"}:
        response["text"] = body["text"]
    else:
        response["data"] = body
    target = root / "responses" / f"{request_id}.json"
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(response, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temp, target)
    print(json.dumps({"answered": request_id}))
    return 0


def cmd_status(root: Path) -> int:
    requests = list((root / "requests").glob("*.json"))
    responses = list((root / "responses").glob("*.json"))
    print(json.dumps({"requests": len(requests), "responses": len(responses), "pending": len(_pending(root)),
                      "done": (root / "DONE").exists()}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mas-bridge")
    parser.add_argument("command", choices=("next", "answer", "status"))
    parser.add_argument("request_id", nargs="?")
    parser.add_argument("--dir", required=True)
    parser.add_argument("--wait", type=float, default=600)
    parser.add_argument("--file")
    parser.add_argument("--model-id", default="claude-opus (subagent)")
    parser.add_argument("--answered-by", default="claude-subagent")
    args = parser.parse_intermixed_args(argv)
    root = Path(args.dir)
    (root / "requests").mkdir(parents=True, exist_ok=True)
    (root / "responses").mkdir(parents=True, exist_ok=True)
    if args.command == "next":
        return cmd_next(root, args.wait, args.answered_by)
    if args.command == "answer":
        if not args.request_id:
            parser.error("answer needs REQUEST_ID")
        return cmd_answer(root, args.request_id, args.file, args.model_id, args.answered_by)
    return cmd_status(root)


if __name__ == "__main__":
    sys.exit(main())
