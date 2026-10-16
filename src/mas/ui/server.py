"""Browser workbench (`ui_ux_spec.md` §15, §15.5): the read surfaces over loopback, in the standard library.

One screen is one dictionary from `views`, served twice: as a page at `/leaderboard` and as its JSON
twin at `/api/leaderboard`, rendered from the same dictionary so the two cannot disagree (§15.2.8).

The store root is opened read-only for the
length of one request, so the workbench reads a root while a service host writes it and cannot
write to the journal itself. By default, methods other than GET and HEAD are refused with 405.
Explicitly enabling local operations adds a token-protected POST endpoint for allowlisted CLI
subprocesses; expert decisions (`hd_`) stay on the terminal (§15.2.7). The listening address is checked
before it is bound: a non-loopback host is refused with its reason, because this surface has no
authentication and is meant for the machine it runs on (§15.1).

Every value reaches the page through `html.escape`, including claim quotes, which are source text
and may hold anything.
"""

from __future__ import annotations

import html
import csv
import io
import ipaddress
import json
import os
import secrets
import socket
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit, urlencode

from mas.core import config as config_mod
from mas.core.config import Config
from mas.core.runtime import Core
from mas.core.store import StoreError
from mas.ui import i18n, presentation, views
from mas.ui.operations import OperationError, OperationManager

PAGES = ("/", "/leaderboard", "/candidate", "/run", "/review", "/pool", "/settings", "/operations")
HTML = "text/html; charset=utf-8"
JSON = "application/json; charset=utf-8"
STYLE = presentation.STYLE


class BadRequest(ValueError):
    """A page was asked for without the parameter it needs."""


@dataclass(frozen=True)
class Response:
    status: int
    content_type: str
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)


# --- rendering --------------------------------------------------------------------------------

def _document(title: str, target: str, body: str, *, refresh_s: int | None = None,
              context: dict[str, Any] | None = None) -> bytes:
    refresh = f'<meta http-equiv="refresh" content="{int(refresh_s)}">' if refresh_s else ""
    return (f'<!doctype html><html lang="{"zh-CN" if i18n.LANGUAGE.get() == "zh" else "en"}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'{refresh}<title>MAS Research — {html.escape(i18n.ui_template(presentation.TITLES.get(title, title)))}</title>'
            f'<style>{STYLE}</style></head><body>'
            f'{presentation.chrome(title, target, body, context)}</body></html>').encode("utf-8")


def _page(target: str, data: dict[str, Any], *, operation_token: str | None = None,
          navigation_task: str | None = None) -> Response:
    """Task-oriented research views; complete fields remain in a collapsed audit record."""
    title = str(data.get("page", target))
    live = 10 if target.split("?")[0].rstrip("/") == "/run" and data.get("state") == "running" else None
    render_data = dict(data, _operation_token=operation_token, _navigation_task=navigation_task)
    return Response(int(HTTPStatus.OK), HTML, _document(title, target, presentation.render(target, render_data),
                                                      refresh_s=live, context=render_data))


def _json(data: dict[str, Any]) -> Response:
    return Response(int(HTTPStatus.OK), JSON, json.dumps(data, indent=1, ensure_ascii=False, default=str).encode("utf-8"))


def _csv_board(data: dict[str, Any]) -> Response:
    output = io.StringIO(newline="")
    rows = data["rows"]
    columns = [key for key in (rows[0] if rows else {}) if key != "candidate"]
    writer = csv.writer(output)
    writer.writerow(["snapshot_id", "rules_ref", *columns])
    for row in rows:
        cells = []
        for key in columns:
            value = row.get(key)
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
                value = "'" + value
            cells.append(value)
        writer.writerow([data["snapshot_id"], data["rules@v"], *cells])
    return Response(200, "text/csv; charset=utf-8", output.getvalue().encode("utf-8-sig"))


def _problem(status: HTTPStatus, message: str, *, as_json: bool, target: str = "/") -> Response:
    if as_json:
        body = json.dumps({"status": int(status), "error": status.phrase, "message": message,
                           "surface": views.READ_ONLY}, indent=1).encode("utf-8")
        return Response(int(status), JSON, body)
    body = (f"<h1>{html.escape(status.phrase.lower())}</h1><p>{html.escape(message)}</p>"
            f'<p class="note">{html.escape(views.READ_ONLY)}</p>')
    return Response(int(status), HTML, _document(status.phrase.lower(), target, body))


def _operations_page(manager: OperationManager | None, *, navigation_task: str | None = None,
                     target: str = "/operations") -> Response:
    if manager is None:
        body = i18n.ui_template('<h1>本机操作</h1><p class="notice">当前为只读模式。使用 '
                '<code>mas ui serve --allow-operations</code> 启用本机操作。</p>'
                '<p>任务、榜单、证据与复核队列可从上方导航查看。</p>')
        return Response(200, HTML, _document("本机操作", target, body, context={"_navigation_task": navigation_task}))
    return Response(200, HTML, _document("运行工作区", target, presentation.operations_page(manager.token),
                                       context={"_navigation_task": navigation_task}))


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
                 role_bindings: list[dict[str, Any]] | None = None,
                 operations: OperationManager | None = None, modern: bool = False):
        self.store_root = Path(store_root)
        self.settings = settings if settings is not None else config_mod.resolve(project_file=None, environ={})
        self.role_bindings = role_bindings or []
        self.operations = operations
        self.open().close()
        self.modern = None
        if modern and operations is not None:
            from mas.ui.workbench_api import WorkbenchAPI
            self.modern = WorkbenchAPI(operations)

    def open(self) -> Core:
        return Core.open(self.store_root, read_only=True)

    def navigation_task(self, query: dict[str, list[str]]) -> str | None:
        explicit = _maybe(query, "task")
        if explicit:
            return explicit
        if self.operations and self.operations.current_task:
            return self.operations.current_task
        with self.open() as core:
            tasks = core.journal.streams("task_")
            return tasks[-1] if tasks else None

    def view(self, page: str, query: dict[str, list[str]]) -> dict[str, Any]:
        if page == "/settings":
            data = views.settings(self.operations.settings if self.operations else self.settings,
                                  store_root=str(self.store_root), role_bindings=self.role_bindings)
            if self.operations:
                data["editable_configuration"] = self.operations.configuration()
            return data
        with self.open() as core:
            if page == "/":
                return views.tasks_and_runs(core)
            if page == "/review":
                return views.review_queue(core, include_routes=_maybe(query, "routes") != "0", task_id=_maybe(query, "task"),
                                          current_versions=_maybe(query, "current_versions") == "1")
            selected = self.navigation_task(query)
            if page == "/run":
                if not _maybe(query, "run"):
                    return views.empty_page("run", selected, "Choose a run from the workspace to view its progress.")
                return views.run(core, _one(query, "run"))
            if page == "/pool":
                if not selected:
                    return views.empty_page("criteria pool", None, "Choose a task to review its criteria.")
                try:
                    return views.criteria_pool(core, selected)
                except views.NotFound as missing:
                    if str(missing).startswith("no registered criteria"):
                        return views.empty_page("criteria pool", selected, "No criteria have been registered for this task yet.")
                    raise
            if page == "/candidate":
                if not selected or not _maybe(query, "id"):
                    return views.empty_page("candidate", selected, "Choose a candidate from a ranking to inspect its evidence.")
                return views.candidate(core, selected, _one(query, "id"),
                                       snapshot_id=_maybe(query, "snapshot"))
            asked_page = _maybe(query, "page") or "1"
            if not asked_page.isdigit() or int(asked_page) < 1:
                raise BadRequest("page must be a positive integer")
            if not selected:
                return views.empty_page("leaderboard", None, "Choose a task to view its saved results.")
            try:
                return views.board(core, selected, snapshot_id=_maybe(query, "snapshot"),
                                   top=_rows(query), page=int(asked_page))
            except views.NotFound as missing:
                if str(missing).startswith("no leaderboard snapshot"):
                    return views.empty_page("leaderboard", selected, "No ranking has been published for this task yet. Open its run to follow progress.")
                raise

    def handle(self, method: str, target: str, *, body: bytes = b"",
               headers: dict[str, str] | None = None) -> Response:
        language, explicit = i18n.language_for(target, headers)
        token = i18n.LANGUAGE.set(language)
        try:
            response = self._handle(method, target, body=body, headers=headers)
            if explicit and method in ("GET", "HEAD"):
                response.headers["Set-Cookie"] = f"mas_ui_language={language}; Path=/; Max-Age=31536000; SameSite=Lax; HttpOnly"
            return response
        finally:
            i18n.LANGUAGE.reset(token)

    def _handle(self, method: str, target: str, *, body: bytes = b"",
                headers: dict[str, str] | None = None) -> Response:
        """Answer one request. Anything but GET and HEAD is refused: this surface writes nothing."""
        split = urlsplit(target)
        path = split.path.rstrip("/") or "/"
        as_json = path == "/api" or path.startswith("/api/")
        if self.modern is not None:
            if path == '/workbench' or path.startswith('/workbench/'):
                asset = self.modern.asset(target)
                if asset:
                    mime, content = asset
                    return Response(200, mime, content)
                return _problem(HTTPStatus.NOT_FOUND, 'The workbench build is not available.', as_json=True)
            if path.startswith('/api/workbench/'):
                try:
                    query = parse_qs(split.query)
                    if method in ('GET', 'HEAD'):
                        if path.startswith('/api/workbench/uploads/templates/') and path.endswith('.csv'):
                            from .uploads import template
                            kind = path.rsplit('/', 1)[-1].removesuffix('.csv')
                            return Response(200, 'text/csv; charset=utf-8', template(kind).encode('utf-8-sig'),
                                headers={'Content-Disposition': f'attachment; filename="mas-{kind}-template.csv"'})
                        if path.endswith('/export.csv'):
                            task_id = path.split('/')[4]
                            content = self.modern.read.export_csv(task_id, _maybe(query, 'snapshot'))
                            return Response(200, 'text/csv; charset=utf-8', content.encode('utf-8-sig'),
                                headers={'Content-Disposition': 'attachment; filename="mas-candidates.csv"'})
                        return _json(self.modern.get(path, query))
                    if method == 'POST':
                        supplied = {k.lower(): v for k, v in (headers or {}).items()}
                        if (not secrets.compare_digest(supplied.get('x-mas-operation-token', ''), self.operations.token)
                                or supplied.get('origin') != 'http://' + supplied.get('host', '')):
                            return Response(403, JSON, b'{"error":{"code":"local_origin_required","message":"Open this workbench on its local address."}}')
                        return _json(self.modern.post(path, json.loads(body)))
                    return Response(405, JSON, b'{"error":{"code":"method_not_allowed","message":"This operation is unavailable."}}')
                except KeyError as error:
                    return Response(404, JSON, json.dumps({'error': {'code': 'not_found', 'message': str(error)}}).encode())
                except (ValueError, OSError, StoreError) as error:
                    return Response(400, JSON, json.dumps({'error': {'code': type(error).__name__, 'message': str(error)}}).encode())
                except RuntimeError as error:
                    return Response(503, JSON, json.dumps({'error': {'code': 'preparing_records', 'message': str(error)}}).encode())
            if method in ('GET', 'HEAD') and path in ('/', '/settings', '/pool', '/leaderboard', '/candidate', '/run'):
                query = parse_qs(split.query)
                query['view'] = [{'/' : 'overview', '/settings': 'settings', '/pool': 'criteria',
                                  '/leaderboard': 'candidates', '/candidate': 'candidates', '/run': 'overview'}[path]]
                if path == '/candidate' and query.get('id'):
                    query['candidate'] = query.pop('id')
                return Response(302, HTML, b'', headers={'Location': '/workbench/?' + urlencode(query, doseq=True)})
        if path in ("/operations", "/api/operations") and method in ("GET", "HEAD"):
            if not as_json:
                return _operations_page(self.operations, navigation_task=self.navigation_task(parse_qs(split.query)), target=target)
            return _json(self.operations.snapshot() if self.operations else {
                "page": "local operations", "enabled": False, "message": "start with --allow-operations"})
        if path == "/api/operations" and method == "POST" and self.operations is not None:
            supplied = {key.lower(): value for key, value in (headers or {}).items()}
            origin = supplied.get("origin", "")
            origin_url = urlsplit(origin)
            if (not secrets.compare_digest(supplied.get("x-mas-operation-token", ""), self.operations.token)
                    or origin != "http://" + supplied.get("host", "")
                    or origin_url.scheme != "http" or not origin_url.hostname
                    or non_loopback_reason(origin_url.hostname)):
                return Response(403, JSON, json.dumps({"message": "local operation token and same-origin request required"}).encode())
            try:
                request = json.loads(body)
                if not isinstance(request, dict):
                    raise OperationError("request must be a JSON object")
                if request.get("action") == "cancel":
                    result = self.operations.cancel(request.get("job_id", ""))
                elif request.get("action") == "save_settings":
                    result = self.operations.save_settings(request.get("settings"))
                elif request.get("action") == "select_task":
                    result = self.operations.select_task(request.get("task_id"))
                else:
                    result = self.operations.start(request)
                return _json(result)
            except (OperationError, ValueError, OSError, StoreError) as error:
                problem = {"message": str(error)}
                if getattr(error, "run_id", None):
                    problem.update(run_id=error.run_id, run_url=f"/run?run={error.run_id}")
                return Response(400, JSON, json.dumps(problem, ensure_ascii=False).encode("utf-8"))
        if method not in ("GET", "HEAD"):
            return _problem(HTTPStatus.METHOD_NOT_ALLOWED,
                            f"{method} is refused: the workbench is read-only. A run is started with `mas run start` "
                            f"and an expert decision with `mas review decide`, on the terminal.",
                            as_json=as_json, target=path)
        exporting = path == "/export/leaderboard.csv"
        page = "/leaderboard" if exporting else (path[len("/api"):] or "/") if as_json else path
        if page not in PAGES:
            return _problem(HTTPStatus.NOT_FOUND, f"no page at {path}; this workbench serves {', '.join(PAGES)}",
                            as_json=as_json)
        try:
            query = parse_qs(split.query)
            if page == "/review" and not as_json:
                query.setdefault("routes", ["0"])
                query["current_versions"] = ["1"]
                if not _maybe(query, "task"):
                    current = self.navigation_task(query)
                    if current:
                        query["task"] = [current]
            if exporting:
                query.update(top=["1000000000"], page=["1"])
            data = self.view(page, query)
            if exporting and data.get("empty_state"):
                return _problem(HTTPStatus.CONFLICT, data["message"], as_json=True, target=path)
        except views.NotFound as missing:
            return _problem(HTTPStatus.NOT_FOUND, str(missing), as_json=as_json, target=path)
        except BadRequest as incomplete:
            return _problem(HTTPStatus.BAD_REQUEST, str(incomplete), as_json=as_json, target=path)
        except StoreError as error:
            return _problem(HTTPStatus.SERVICE_UNAVAILABLE, f"the store root cannot be read: {error}",
                            as_json=as_json, target=path)
        return _csv_board(data) if exporting else _json(data) if as_json else _page(target, data, operation_token=self.operations.token if self.operations else None,
                                                                                navigation_task=data.get("task_id") or self.navigation_task(query))


class _Handler(BaseHTTPRequestHandler):
    server_version = "mas-workbench"
    protocol_version = "HTTP/1.1"

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            self.close_connection = True

    def _answer(self, with_body: bool = True) -> None:
        if self.command == 'GET' and urlsplit(self.path).path == '/api/workbench/events' and self.server.workbench.modern is not None:
            return self._events()
        body = b""
        if self.command == "POST":
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(400, "invalid Content-Length")
                self.close_connection = True
                return
            limit = (20 * 1024 * 1024 if urlsplit(self.path).path == '/api/workbench/uploads/preview'
                     else 131072 if self.path.startswith('/api/workbench/') else 8192)
            if not 0 <= length <= limit:
                self.send_error(413, "operation request is too large")
                self.close_connection = True
                return
            body = self.rfile.read(length)
        response = self.server.workbench.handle(self.command, self.path, body=body, headers=dict(self.headers))
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        for name, value in response.headers.items():
            self.send_header(name, value)
        if response.content_type.startswith("text/csv") and not any(
                name.lower() == 'content-disposition' for name in response.headers):
            self.send_header("Content-Disposition", 'attachment; filename="mas-leaderboard.csv"')
        if response.status == int(HTTPStatus.METHOD_NOT_ALLOWED):
            self.send_header("Allow", "GET, HEAD")
        self.end_headers()
        if with_body:
            self.wfile.write(response.body)

    def _events(self):
        api = self.server.workbench.modern
        query = parse_qs(urlsplit(self.path).query)
        try:
            cursor = int(self.headers.get('Last-Event-ID') or _maybe(query, 'after') or 0)
        except ValueError:
            cursor = 0
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        seen, projection, heartbeat = {}, None, 0.0
        def emit(data, event_id=None):
            prefix = f'id: {event_id}\n' if event_id is not None else ''
            self.wfile.write((prefix + 'data: ' + json.dumps(data, ensure_ascii=False) + '\n\n').encode('utf-8'))
            self.wfile.flush()
        try:
            while not api._closing.is_set():
                for event in api.workflows.events(cursor):
                    cursor = event['cursor']
                    emit(event, cursor)
                for workflow in api.workflows.list():
                    encoded = json.dumps(workflow, sort_keys=True)
                    if seen.get(workflow['workflow_id']) != encoded:
                        emit({'kind': 'workflow', 'workflow': workflow, 'task_id': workflow.get('task_id'), 'cursor': cursor})
                        seen[workflow['workflow_id']] = encoded
                current = api.model.status().get('source_cursor')
                if current != projection:
                    emit({'kind': 'projection', 'cursor': cursor})
                    projection = current
                if time.monotonic() - heartbeat >= 15:
                    emit({'kind': 'heartbeat', 'cursor': cursor})
                    heartbeat = time.monotonic()
                api._closing.wait(.7)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        self.close_connection = True

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
                role_bindings: list[dict[str, Any]] | None = None,
                operations: OperationManager | None = None, modern: bool = False) -> ThreadingHTTPServer:
    """The workbench on a loopback address, bound but not yet serving. Drive it with `handle`, or `serve` it."""
    reason = non_loopback_reason(host)
    if reason:
        raise ValueError(reason)
    workbench = Workbench(store_root, settings=settings, role_bindings=role_bindings, operations=operations, modern=modern)
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    server_type = type("LoopbackHTTPServer", (ThreadingHTTPServer,), {"address_family": family})
    server = server_type((host, port), _Handler)
    server.workbench = workbench
    return server


def address(server: ThreadingHTTPServer) -> str:
    host, port = server.server_address[:2]
    if ":" in host:
        host = f"[{host}]"
    return f"http://{host}:{port}/"


def serve(server: ThreadingHTTPServer) -> None:
    """Serve until interrupted, then close the socket."""
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if server.workbench.modern is not None:
                server.workbench.modern.close()
            if server.workbench.operations is not None:
                server.workbench.operations.close()
        finally:
            server.server_close()
