"""Opt-in local operation launcher: a small allowlist, real child processes, durable logs.

The views continue to open SQLite read-only. Mutations go through the same CLI as
terminal operations, with its frozen policy and authority checks intact.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import signal
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from mas.core import config as config_mod, criteria, task
from mas.core.clock import utc_now
from mas.core.runtime import Core
from mas.ui import views


class OperationError(ValueError):
    def __init__(self, message: str, *, run_id: str | None = None):
        super().__init__(message)
        self.run_id = run_id


EDITABLE_SETTINGS = {
    "search.volume": "Literature workload", "textbook.volume": "Textbook workload", "assess.workers": "Concurrent candidates",
    "search.breadth": "Search breadth", "search.depth": "Search rounds", "read.max_papers_full_read": "Full texts per dimension",
    "budget.usd_max": "Cost cap (USD)", "budget.on_exhaust": "When budget is exhausted",
    "interaction.mode": "Interaction mode", "rank.coverage_floor": "Ranking coverage floor",
    "rank.mandated_coverage_floor": "Required-criteria eligibility floor",
}


class OperationManager:
    def __init__(self, store_root: str | os.PathLike, *, cli_options: list[str] | None = None,
                 config_hash: str | None = None, working_directory: str | os.PathLike | None = None,
                 initiator_kind: str = "agent", initiator_name: str = "codex", settings: config_mod.Config | None = None):
        self.store_root = Path(store_root).resolve()
        self.cli_options = list(cli_options or [])
        self.config_hash = config_hash
        self.settings = settings or config_mod.resolve(project_file=None, environ={})
        self.initiator = {"kind": initiator_kind, "id": initiator_name, "surface": "browser"}
        self.working_directory = Path(working_directory or Path.cwd()).resolve()
        self.token = secrets.token_urlsafe(32)
        self.log_root = self.store_root.parent / "workbench-jobs"
        self._jobs: dict[str, dict[str, Any]] = {}
        self._processes: dict[str, subprocess.Popen] = {}
        self._lock = threading.RLock()
        self._task_cache_lock = threading.RLock()
        self._task_cache: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {}
        self.state_path = self.store_root.parent / "workbench-state.json"
        self.current_task: str | None = None
        self.saved_overrides: dict[str, Any] = {}
        if self.state_path.is_file():
            with self.state_path.open(encoding="utf-8") as state_file:
                saved = json.load(state_file)
            self.current_task = saved.get("current_task")
            self.saved_overrides = {key: value for key, value in (saved.get("settings") or {}).items() if key in EDITABLE_SETTINGS}
            if self.saved_overrides:
                self._apply_settings(self.saved_overrides, persist=False)
        history = []
        for metadata in self.log_root.glob("job_*/job.json"):
            try:
                with metadata.open(encoding="utf-8") as saved_job:
                    record = json.load(saved_job)
                if record.get("status") in ("completed", "failed", "cancelled") and record.get("job_id") == metadata.parent.name:
                    history.append(record)
            except (OSError, ValueError):
                continue
        for record in sorted(history, key=lambda row: row.get("started_at") or ""):
            self._jobs[record["job_id"]] = record

    def _save_state(self) -> None:
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"current_task": self.current_task, "preset": self.settings.preset,
                                         "settings": self.saved_overrides}, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.state_path)

    @staticmethod
    def _argument(value: Any) -> str:
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, list):
            return ",".join(str(part) for part in value)
        return str(value)

    def _apply_settings(self, updates: dict[str, Any], *, persist: bool = True) -> dict[str, Any]:
        if not isinstance(updates, dict) or set(updates) - set(EDITABLE_SETTINGS):
            raise OperationError("only the displayed non-secret settings may be edited")
        overrides = {**self.saved_overrides, **updates}
        pairs, project_file, profile = [], None, None
        options = self.cli_options
        for index in range(0, len(options), 2):
            flag, value = options[index:index + 2]
            if flag == "--config":
                project_file = value
            elif flag == "--profile":
                profile = value
            elif flag == "--set":
                pairs.append(value)
        pairs.extend(f"{key}={self._argument(value)}" for key, value in overrides.items())
        resolved = config_mod.resolve(preset="standard", project_file=project_file, profile=profile,
                                      overrides=config_mod.parse_overrides(pairs))
        # Keep model/provider tables from the original service if it was constructed programmatically.
        if not project_file and self.settings.providers:
            resolved.providers, resolved.roles = self.settings.providers, self.settings.roles
        self.settings = resolved
        self.config_hash = resolved.hash()
        self.saved_overrides = {key: resolved[key] for key in overrides}
        if persist:
            self._save_state()
        return self.configuration()

    def save_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            return self._apply_settings(updates)

    def configuration(self) -> dict[str, Any]:
        fields = []
        for key, label in EDITABLE_SETTINGS.items():
            definition = config_mod.SETTINGS[key]
            fields.append({"key": key, "label": label, "value": self.settings[key],
                           "kind": type(definition.default).__name__, "choices": definition.choices,
                           "minimum": definition.minimum, "maximum": definition.maximum,
                           "doc": definition.doc})
        return {"preset": self.settings.preset, "fields": fields, "config_hash": self.config_hash,
                "path": str(self.state_path), "message": "Changes apply to subsequent work. Existing results keep their recorded settings."}

    def select_task(self, task_id: str) -> dict[str, Any]:
        if not isinstance(task_id, str):
            raise OperationError("select an existing task")
        with Core.open(self.store_root, read_only=True) as core:
            try:
                task.get(core, task_id)
            except KeyError:
                raise OperationError("task does not exist in this store") from None
        with self._lock:
            self.current_task = task_id
            self._save_state()
        return {"current_task": task_id, "status": "saved"}

    @staticmethod
    def active_runs(core: Core) -> dict[str, dict[str, Any]]:
        states = views.run_states(core)
        active = {}
        for created in core.journal.of_type("run.created", "run_"):
            row = states.get(created.stream_id) or {}
            if row.get("state") in ("queued", "running", "paused"):
                active[created.payload["task_id"]] = {"run_id": created.stream_id, "state": row["state"],
                    "state_changed_at": row.get("state_changed_at"), "run_url": f"/run?run={created.stream_id}"}
        return active

    def tasks(self) -> list[dict[str, Any]]:
        rows = []
        with self._task_cache_lock, Core.open(self.store_root, read_only=True) as core:
            live = self.active_runs(core)
            bound_runs: dict[str, list[str]] = {}
            for event in core.journal.of_type("run.created", "run_"):
                bound_runs.setdefault(event.payload.get("task_id"), []).append(event.event_id)
            for task_id in core.journal.streams("task_"):
                # A run binds a profile on its own stream, without appending to the task stream.
                # Both journal positions are therefore part of the invalidation key.
                cache_key = (core.journal.last_seq(task_id), tuple(bound_runs.get(task_id, [])))
                cached = self._task_cache.get(task_id)
                if cached and cached[0] == cache_key:
                    rows.append(cached[1])
                    continue
                context = task.get(core, task_id)
                try:
                    frozen = criteria.rule_set(core, task_id)
                except KeyError:
                    frozen = {}
                row = {"task_id": task_id, "objective": context["objective_text"],
                             "rule_set_ref": frozen.get("rule_set_ref"),
                             "scoring_rules": len(frozen.get("entries") or []),
                             "acceptance_label": frozen.get("acceptance_label"),
                             "deferred_capabilities": list(criteria.deferred_capabilities(frozen)),
                             "blocking_unknowns": len(task.blocking_unknowns(context)),
                             "verified_supplement_refs": context.get("verified_supplement_refs") or [],
                             "criteria_summary": views.criteria_summary(core, task_id, include_details=False)}
                self._task_cache[task_id] = (cache_key, row)
                rows.append(row)
        return [dict(row, active_run=live.get(row["task_id"])) for row in rows]

    def supplements(self) -> list[dict[str, Any]]:
        """Only metadata from the explicitly verified artifact kind; never expose paper text or claims."""
        with Core.open(self.store_root, read_only=True) as core:
            return [{"ref": ref, "source_ref": record["source_ref"],
                     "accepted_count": len(record.get("claims") or []),
                     "excluded_count": len(record.get("excluded_claims") or []),
                     "selection": record.get("selection") or {}, "created_at": record.get("created_at")}
                    for ref, record in core.artifacts.of_kind("verified_supplement")]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            jobs = [self._public_job(job_id) for job_id in reversed(self._jobs)]
        return {"page": "local operations", "enabled": True, "tasks": self.tasks(), "jobs": jobs,
                "available_actions": ["run_start", "adjudicate_item", "task_inherit", "freeze_profile", "reduce_registered", "supplement_attach"],
                "verified_supplements": self.supplements(),
                "current_task": self.current_task, "configuration": self.configuration(),
                "config_hash": self.config_hash, "log_root": str(self.log_root), "initiator": self.initiator,
                "authority": "machine adjudication is recorded as agent_verdict; expert decisions remain on the terminal",
                "recovery": "criteria re-derivation and historical recovery are not available here"}

    def _public_job(self, job_id: str) -> dict[str, Any]:
        row = dict(self._jobs[job_id])
        process = self._processes.get(job_id)
        exit_code = process.poll() if process is not None else row.get("exit_code")
        row["exit_code"] = exit_code
        row["can_cancel"] = process is not None and exit_code is None
        if exit_code is not None and row["status"] == "running":
            row["status"] = "completed" if exit_code == 0 else "failed"
        path = Path(row["log_path"])
        try:
            with path.open("rb") as log:
                log.seek(max(0, path.stat().st_size - 24_000))
                tail = log.read().decode("utf-8", errors="replace")
        except OSError:
            tail = ""
        row["log_tail"] = tail
        found = re.search(r"\brun_[0-9A-Z]{26}\b", tail)
        if found:
            row["run_id"] = found.group()
            row["run_url"] = f"/run?run={found.group()}"
        if row["action"] == "reduce_registered" and not self._jobs[job_id].get("run_id"):
            started = datetime.fromisoformat(row["started_at"]).timestamp()
            with Core.open(self.store_root, read_only=True) as core:
                for event in core.journal.of_type("run.created", "run_"):
                    if event.payload.get("task_id") != row["task_id"]:
                        continue
                    if datetime.fromisoformat(event.recorded_at).timestamp() < started - 1:
                        continue
                    binding = core.artifacts.payload(event.payload["binding_artifact_id"])
                    if binding.get("operation") == "registered_reduction":
                        self._jobs[job_id]["run_id"] = row["run_id"] = event.stream_id
                        row["run_url"] = f"/run?run={event.stream_id}"
        elif self._jobs[job_id].get("run_id"):
            row["run_id"] = self._jobs[job_id]["run_id"]
            row["run_url"] = f"/run?run={row['run_id']}"
        try:
            output = json.loads(tail)
            if isinstance(output, dict):
                row["result"] = output
        except ValueError:
            pass
        if row["action"] == "task_inherit" and re.fullmatch(r"task_[0-9A-Z]{26}", tail.strip()):
            row["result"] = {"task_id": tail.strip()}
        if row["status"] == "failed" and row["action"] in ("run_start", "reduce_registered") and row.get("run_id"):
            with Core.open(self.store_root, read_only=True) as core:
                created = core.journal.replay(row["run_id"], 1, 1)
                belongs_to_job = (created and created[0].payload.get("task_id") == row["task_id"]
                                  and datetime.fromisoformat(created[0].recorded_at).timestamp()
                                  >= datetime.fromisoformat(row["started_at"]).timestamp() - 1)
                recorded = views._event_core(core, views.RUN_STATE_KINDS).journal.replay(row["run_id"])
                latest = next((event for event in reversed(recorded) if event.state_to), None)
                if belongs_to_job and latest and latest.state_to == "completed":
                    row["research_run_state"] = "completed"
                    row["research_result_saved"] = True
                    row["research_result_artifact_id"] = latest.payload.get("derivation_record_artifact_id")
        return row

    def _persist(self, job_id: str) -> None:
        destination = self.log_root / job_id / "job.json"
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(self._jobs[job_id], ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(destination)

    def _watch(self, job_id: str, process: subprocess.Popen) -> None:
        code = process.wait()
        with self._lock:
            row = self._jobs[job_id]
            row["exit_code"] = code
            row["finished_at"] = utc_now()
            if row["status"] != "cancelled":
                row["status"] = "completed" if code == 0 else "failed"
            self._persist(job_id)

    def start(self, request: dict[str, Any]) -> dict[str, Any]:
        action, task_id = request.get("action"), request.get("task_id")
        if action not in ("run_start", "adjudicate_item", "task_inherit", "freeze_profile", "reduce_registered", "supplement_attach"):
            raise OperationError("unsupported operation; choose one of the displayed operations")
        if not isinstance(task_id, str) or not task_id.startswith("task_"):
            raise OperationError("choose an existing task")
        with Core.open(self.store_root, read_only=True) as core:
            try:
                context = task.get(core, task_id)
            except KeyError:
                raise OperationError("this task does not exist in the selected store") from None
            if action in ("run_start", "reduce_registered", "freeze_profile", "supplement_attach"):
                live = self.active_runs(core).get(task_id)
                if live:
                    raise OperationError(f"This task already has a {live['state']} run: {live['run_id']}. Open its progress before starting more work.",
                                         run_id=live["run_id"])
            if action == "run_start":
                if task.blocking_unknowns(context):
                    raise OperationError("this task still has blocking unknowns")
                try:
                    frozen = criteria.rule_set(core, task_id, request.get("rule_set_ref"))
                except (KeyError, StopIteration):
                    raise OperationError("this task needs an existing frozen rule set") from None
                if not request.get("rule_set_ref"):
                    raise OperationError("select the frozen rule set shown on this page")
                workers = request.get("workers", 4)
                if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 32:
                    raise OperationError("workers must be an integer from 1 to 32")
                command = ["run", "start", task_id, "--seed", "0", "--workers", str(workers),
                           "--rule-set", frozen["rule_set_ref"]]
                profile_ref = request.get("measurement_profile")
                if profile_ref:
                    if not isinstance(profile_ref, str) or profile_ref.startswith("-") or len(profile_ref) > 240:
                        raise OperationError("measurement profile must be a registered profile reference")
                    command.extend(["--measurement-profile", profile_ref])
            elif action == "adjudicate_item":
                item = request.get("item")
                if not isinstance(item, str) or not item.strip() or item.startswith("-") or len(item) > 240:
                    raise OperationError("enter one review item id or rule reference")
                command = ["review", "adjudicate", task_id, "--item", item]
            elif action == "task_inherit":
                reason = request.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    raise OperationError("state the purpose of the new experiment")
                command = ["task", "inherit", task_id, "--reason", reason]
            elif action == "reduce_registered":
                reason = request.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    raise OperationError("state the purpose of the criteria reduction")
                command = ["criteria", "reduce-registered", task_id, "--reason", reason]
            elif action == "supplement_attach":
                ref = request.get("supplement_ref")
                if not isinstance(ref, str):
                    raise OperationError("choose a verified measurement supplement")
                try:
                    envelope = core.artifacts.get(ref)
                except KeyError:
                    raise OperationError("this supplement is not present in the selected store") from None
                if envelope["kind"] != "verified_supplement":
                    raise OperationError("only previously verified measurement supplements can be attached")
                command = ["supplement", "attach", task_id, "--ref", ref]
            else:
                required = ("primary_board", "rationale", "expected_effect")
                if any(not isinstance(request.get(key), str) or not request[key].strip() for key in required):
                    raise OperationError("name the board, rationale and expected effect before freezing")
                deferred = request.get("defer_capabilities", [])
                if not isinstance(deferred, list) or set(deferred) - {"predicted_property_lookup", "literature_retrieval"}:
                    raise OperationError("choose supported capability deferrals")
                command = ["measurement", "prepare", task_id, "--primary-board", request["primary_board"],
                           "--rationale", request["rationale"], "--expected-effect", request["expected_effect"]]
                for capability in deferred:
                    command.extend(["--defer-capability", capability])
                if not deferred:
                    command.append("--no-deferrals")
                if deferred:
                    reason = request.get("defer_reason")
                    if not isinstance(reason, str) or not reason.strip():
                        raise OperationError("explain the capability deferrals")
                    command.extend(["--defer-reason", reason])
        with self._lock:
            if any(process.poll() is None for process in self._processes.values()):
                raise OperationError("one operation is already running; finish or cancel it first")
            job_id = "job_" + secrets.token_hex(8)
            folder = self.log_root / job_id
            folder.mkdir(parents=True)
            log_path = folder / "output.log"
            environment = dict(os.environ, PYTHONUTF8="1", PYTHONUNBUFFERED="1", MAS_SURFACE="browser",
                               MAS_ACTOR_KIND=self.initiator["kind"], MAS_PERSON=self.initiator["id"])
            source_root = str(Path(__file__).resolve().parents[2])
            environment["PYTHONPATH"] = os.pathsep.join(filter(None, (source_root, environment.get("PYTHONPATH"))))
            options: dict[str, Any] = {"start_new_session": True} if os.name != "nt" else {
                "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
            with log_path.open("wb") as log:
                effective_options = list(self.cli_options)
                if self.saved_overrides:
                    effective_options.extend(["--preset", "standard"])
                    for key, value in self.saved_overrides.items():
                        effective_options.extend(["--set", f"{key}={self._argument(value)}"])
                process = subprocess.Popen([sys.executable, "-m", "mas.cli.main", "--store", str(self.store_root),
                                            *effective_options, *command], cwd=self.working_directory,
                                           env=environment, stdin=subprocess.DEVNULL, stdout=log,
                                           stderr=subprocess.STDOUT, **options)
            self._processes[job_id] = process
            self._jobs[job_id] = {"job_id": job_id, "action": action, "task_id": task_id,
                                  "rule_set_ref": request.get("rule_set_ref") if action == "run_start" else None,
                                  "item": request.get("item") if action == "adjudicate_item" else None,
                                  "config_hash": self.config_hash, "pid": process.pid, "status": "running",
                                  "measurement_profile": request.get("measurement_profile"),
                                  "initiator": self.initiator,
                                  "started_at": utc_now(), "finished_at": None, "exit_code": None,
                                  "log_path": str(log_path)}
            self._persist(job_id)
            threading.Thread(target=self._watch, args=(job_id, process), daemon=True).start()
            return self._public_job(job_id)

    def cancel(self, job_id: str) -> dict[str, Any]:
        if not isinstance(job_id, str):
            raise OperationError("job_id must identify a job started by this server")
        with self._lock:
            process = self._processes.get(job_id)
            if process is None:
                raise OperationError("this server did not start that job")
            if process.poll() is None:
                if os.name == "nt":
                    stopped = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
                                             creationflags=subprocess.CREATE_NO_WINDOW, check=False)
                    if stopped.returncode and process.poll() is None:
                        raise OperationError(f"could not stop owned process {process.pid}; it is still running")
                else:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        if process.poll() is None:
                            raise
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    raise OperationError(f"process {process.pid} did not exit after cancellation") from None
                self._jobs[job_id]["status"] = "cancelled"
                self._jobs[job_id]["cancelled_at"] = utc_now()
                self._persist(job_id)
            return self._public_job(job_id)

    def close(self) -> None:
        """Stop only the processes launched by this server, before it relinquishes ownership."""
        for job_id, process in list(self._processes.items()):
            if process.poll() is None:
                self.cancel(job_id)
