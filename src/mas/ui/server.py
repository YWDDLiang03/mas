"""Browser workbench (`ui_ux_spec.md` §15, §15.5): the read surfaces over loopback, in the standard library.

One screen is one dictionary from `views`, served twice: as a page at `/leaderboard` and as its JSON
twin at `/api/leaderboard`, rendered from the same dictionary so the two cannot disagree (§15.2.8).

Three properties are structural rather than promised. The store root is opened read-only for the
length of one request, so the workbench reads a root while a service host writes it and cannot
write a byte itself. Every method but GET and HEAD is refused with 405, so no page is a surface
for a command: a run is started and an expert decision (`hd_`) is recorded on the terminal, which
reads the confirmation from the terminal itself (§15.2.7). And the listening address is checked
before it is bound: a non-loopback host is refused with its reason, because this surface has no
authentication and is meant for the machine it runs on (§15.1).

Every value reaches the page through `html.escape`, including claim quotes, which are source text
and may hold anything.
"""

from __future__ import annotations

import html
import ipaddress
import json
import os
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from mas.core import config as config_mod
from mas.core.config import Config
from mas.core.runtime import Core
from mas.core.store import StoreError
from mas.ui import views

PAGES = ("/", "/leaderboard", "/candidate", "/run", "/review", "/pool", "/settings")
HTML = "text/html; charset=utf-8"
JSON = "application/json; charset=utf-8"
STYLE = """
body { font: 15px/1.5 system-ui, sans-serif; margin: 0 auto; max-width: 70rem; padding: 1.5rem; color: #111; }
h1 { font-size: 1.4rem; } h2 { font-size: 1.05rem; margin-top: 1.8rem; text-transform: lowercase; }
nav { border-bottom: 1px solid #ccc; padding-bottom: .6rem; margin-bottom: 1.2rem; font-size: .9rem; }
nav a { margin-right: 1rem; }
table { border-collapse: collapse; width: 100%; font-size: .9rem; margin: .3rem 0; }
th, td { border: 1px solid #ddd; padding: .25rem .4rem; text-align: left; vertical-align: top; }
th { background: #f4f4f4; font-weight: 600; }
table.fields > tbody > tr > th { width: 16rem; }
.none { color: #888; } .note { color: #555; font-size: .9rem; }
"""


class BadRequest(ValueError):
    """A page was asked for without the parameter it needs."""


@dataclass(frozen=True)
class Response:
    status: int
    content_type: str
    body: bytes


# --- rendering --------------------------------------------------------------------------------

def _text(value: Any) -> str:
    if value is None:
        return '<span class="none">—</span>'
    if isinstance(value, bool):
        return "yes" if value else "no"
    shown = html.escape(str(value))
    if isinstance(value, str) and value.split("?", 1)[0] in PAGES and value.startswith("/"):
        return f'<a href="{html.escape(value, quote=True)}">{shown}</a>'
    return shown


def _cell(value: Any) -> str:
    if isinstance(value, dict):
        return _fields(value)
    if isinstance(value, list):
        return _items(value)
    return _text(value)


def _items(values: list[Any]) -> str:
    if not values:
        return '<span class="none">none</span>'
    if all(isinstance(item, dict) for item in values):
        columns = list(dict.fromkeys(key for item in values for key in item))
        head = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
        rows = "".join("<tr>" + "".join(f"<td>{_cell(item.get(column))}</td>" for column in columns) + "</tr>"
                       for item in values)
        return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"
    return "<ul>" + "".join(f"<li>{_cell(item)}</li>" for item in values) + "</ul>"


def _fields(data: dict[str, Any]) -> str:
    rows = "".join(f"<tr><th>{html.escape(str(key))}</th><td>{_cell(value)}</td></tr>" for key, value in data.items())
    return f'<table class="fields"><tbody>{rows}</tbody></table>'


def _nav(target: str) -> str:
    twin = "/api" + ("" if target in ("/", "") else target)
    links = [f'<a href="{html.escape(path, quote=True)}">{html.escape(path)}</a>' for path in PAGES]
    return f'<nav>{"".join(links)}<a href="{html.escape(twin, quote=True)}">this page as JSON</a></nav>'


def _document(title: str, target: str, body: str) -> bytes:
    return (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>mas workbench — {html.escape(title)}</title><style>{STYLE}</style></head>"
            f"<body>{_nav(target)}{body}</body></html>").encode("utf-8")


def _page(target: str, data: dict[str, Any]) -> Response:
    """The page: scalar fields first, then one section per nested block, every value escaped."""
    title = str(data.get("page", target))
    scalars = {key: value for key, value in data.items() if not isinstance(value, (dict, list))}
    body = [f"<h1>{html.escape(title)}</h1>", _fields(scalars)]
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            body.append(f"<h2>{html.escape(str(key))}</h2>{_cell(value)}")
    return Response(int(HTTPStatus.OK), HTML, _document(title, target, "".join(body)))


def _json(data: dict[str, Any]) -> Response:
    return Response(int(HTTPStatus.OK), JSON, json.dumps(data, indent=1, ensure_ascii=False, default=str).encode("utf-8"))


def _problem(status: HTTPStatus, message: str, *, as_json: bool, target: str = "/") -> Response:
    if as_json:
        body = json.dumps({"status": int(status), "error": status.phrase, "message": message,
                           "surface": views.READ_ONLY}, indent=1).encode("utf-8")
        return Response(int(status), JSON, body)
    body = (f"<h1>{html.escape(status.phrase.lower())}</h1><p>{html.escape(message)}</p>"
            f'<p class="note">{html.escape(views.READ_ONLY)}</p>')
    return Response(int(status), HTML, _document(status.phrase.lower(), target, body))


# --- the surface ------------------------------------------------------------------------------

def _one(query: dict[str, list[str]], name: str) -> str:
    values = [value for value in query.get(name, []) if value]
    if not values:
        raise BadRequest(f"this page needs a ?{name}= parameter")
    return values[0]


def _maybe(query: dict[str, list[str]], name: str) -> str | None:
    values = [value for value in query.get(name, []) if value]
    return values[0] if values else None


def _rows(query: dict[str, list[str]]) -> int:
    asked = _maybe(query, "top")
    if asked is None:
        return views.MAX_ROWS
    if not asked.isdigit() or int(asked) < 1:
        raise BadRequest(f"top={asked!r} is not a row count")
    return int(asked)


class Workbench:
    """The read surfaces of one store root; each request opens the root read-only and closes it again."""

    def __init__(self, store_root: str | os.PathLike, *, settings: Config | None = None,
                 role_bindings: list[dict[str, Any]] | None = None):
        self.store_root = Path(store_root)
        self.settings = settings if settings is not None else config_mod.resolve(project_file=None, environ={})
        self.role_bindings = role_bindings or []
        self.open().close()

    def open(self) -> Core:
        return Core.open(self.store_root, read_only=True)

    def view(self, page: str, query: dict[str, list[str]]) -> dict[str, Any]:
        if page == "/settings":
            return views.settings(self.settings, store_root=str(self.store_root),
                                  role_bindings=self.role_bindings)
        with self.open() as core:
            if page == "/":
                return views.tasks_and_runs(core)
            if page == "/review":
                return views.review_queue(core)
            if page == "/run":
                return views.run(core, _one(query, "run"))
            if page == "/pool":
                return views.criteria_pool(core, _one(query, "task"))
            if page == "/candidate":
                return views.candidate(core, _one(query, "task"), _one(query, "id"),
                                       snapshot_id=_maybe(query, "snapshot"))
            return views.board(core, _one(query, "task"), snapshot_id=_maybe(query, "snapshot"), top=_rows(query))

    def handle(self, method: str, target: str) -> Response:
        """Answer one request. Anything but GET and HEAD is refused: this surface writes nothing."""
        split = urlsplit(target)
        path = split.path.rstrip("/") or "/"
        as_json = path == "/api" or path.startswith("/api/")
        if method not in ("GET", "HEAD"):
            return _problem(HTTPStatus.METHOD_NOT_ALLOWED,
                            f"{method} is refused: the workbench is read-only. A run is started with `mas run start` "
                            f"and an expert decision with `mas review decide`, on the terminal.",
                            as_json=as_json, target=path)
        page = (path[len("/api"):] or "/") if as_json else path
        if page not in PAGES:
            return _problem(HTTPStatus.NOT_FOUND, f"no page at {path}; this workbench serves {', '.join(PAGES)}",
                            as_json=as_json)
        try:
            data = self.view(page, parse_qs(split.query))
        except views.NotFound as missing:
            return _problem(HTTPStatus.NOT_FOUND, str(missing), as_json=as_json, target=path)
        except BadRequest as incomplete:
            return _problem(HTTPStatus.BAD_REQUEST, str(incomplete), as_json=as_json, target=path)
        except StoreError as error:
            return _problem(HTTPStatus.SERVICE_UNAVAILABLE, f"the store root cannot be read: {error}",
                            as_json=as_json, target=path)
        return _json(data) if as_json else _page(target, data)


class _Handler(BaseHTTPRequestHandler):
    server_version = "mas-workbench"
    protocol_version = "HTTP/1.1"

    def _answer(self, with_body: bool = True) -> None:
        response = self.server.workbench.handle(self.command, self.path)
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        if response.status == int(HTTPStatus.METHOD_NOT_ALLOWED):
            self.send_header("Allow", "GET, HEAD")
        self.end_headers()
        if with_body:
            self.wfile.write(response.body)

    def do_GET(self) -> None:
        self._answer()

    def do_HEAD(self) -> None:
        self._answer(with_body=False)

    do_POST = do_PUT = do_DELETE = do_PATCH = _answer

    def log_message(self, fmt: str, *args: Any) -> None:
        """The journal records what happened; a request log would record only who looked."""


def non_loopback_reason(host: str) -> str | None:
    """Why `host` may not be bound, or None. The workbench has no authentication (§15.1, §15.5)."""
    if host == "localhost":
        return None
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return (f"{host!r} is not a loopback address; the workbench is read-only but unauthenticated, "
                f"so it binds 127.0.0.1, ::1 or localhost only")
    if not address.is_loopback:
        return (f"{host} is not a loopback address; the workbench is read-only but unauthenticated, "
                f"so it would be readable by anyone who can reach this machine")
    return None


def make_server(store_root: str | os.PathLike, *, port: int, host: str = "127.0.0.1",
                settings: Config | None = None,
                role_bindings: list[dict[str, Any]] | None = None) -> ThreadingHTTPServer:
    """The workbench on a loopback address, bound but not yet serving. Drive it with `handle`, or `serve` it."""
    reason = non_loopback_reason(host)
    if reason:
        raise ValueError(reason)
    workbench = Workbench(store_root, settings=settings, role_bindings=role_bindings)
    server = ThreadingHTTPServer((host, port), _Handler)
    server.workbench = workbench
    return server


def address(server: ThreadingHTTPServer) -> str:
    host, port = server.server_address[:2]
    return f"http://{host}:{port}/"


def serve(server: ThreadingHTTPServer) -> None:
    """Serve until interrupted, then close the socket."""
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
