"""Store root (design §14, §14.1): one service host per local, unsynchronized store root.

The store root holds one SQLite database. Journal events and artifacts are
append-only, enforced by triggers, so no code path can rewrite or delete them.
The host holds an operating-system lock on the root for as long as it is open;
the operating system releases it when the process ends, so a crash never leaves
a stale lock.

A root may also be opened read-only (`read_only=True`). Such a reader takes no
lock, so it works while a service host holds the root, and every write path is
refused with `StoreError("read_only", ...)` before SQLite is reached. This is
what a second surface over a running store gets: the browser workbench
(`ui_ux_spec.md` §15) reads one store while a run writes it.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import threading
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    stream_id   TEXT NOT NULL,
    seq         INTEGER NOT NULL,
    event_id    TEXT NOT NULL UNIQUE,
    event_type  TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    body        TEXT NOT NULL,
    body_hash   TEXT NOT NULL,
    PRIMARY KEY (stream_id, seq)
);
CREATE INDEX IF NOT EXISTS events_by_type ON events (event_type);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    kind        TEXT NOT NULL,
    sha256      TEXT NOT NULL UNIQUE,
    body        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS artifacts_by_kind ON artifacts (kind);

CREATE TABLE IF NOT EXISTS operator_log (
    entry_no    INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_kind  TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    body        TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'journal is append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'journal is append-only'); END;
CREATE TRIGGER IF NOT EXISTS artifacts_no_update BEFORE UPDATE ON artifacts
BEGIN SELECT RAISE(ABORT, 'artifacts are write-once'); END;
CREATE TRIGGER IF NOT EXISTS artifacts_no_delete BEFORE DELETE ON artifacts
BEGIN SELECT RAISE(ABORT, 'artifacts are write-once'); END;
CREATE TRIGGER IF NOT EXISTS operator_log_no_update BEFORE UPDATE ON operator_log
BEGIN SELECT RAISE(ABORT, 'operator log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS operator_log_no_delete BEFORE DELETE ON operator_log
BEGIN SELECT RAISE(ABORT, 'operator log is append-only'); END;
"""

# Folder names of common synchronization clients; a root inside one is refused.
_SYNC_MARKERS = ("dropbox", "onedrive", "google drive", "googledrive", "icloud", "box sync", "nextcloud", "owncloud")
_NETWORK_FILESYSTEMS = frozenset({"nfs", "nfs4", "cifs", "smbfs", "smb3", "fuse.sshfs", "9p", "afs", "glusterfs", "lustre"})


class StoreError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _mount_fstype(path: Path) -> str | None:
    """File-system type of the mount holding `path` (Linux only; None elsewhere)."""
    mounts = Path("/proc/mounts")
    if not mounts.exists():
        return None
    best, fstype = "", None
    resolved = str(path.resolve())
    for line in mounts.read_text().splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mount_point = parts[1].replace("\\040", " ")
        if (resolved == mount_point or resolved.startswith(mount_point.rstrip("/") + "/")) and len(mount_point) > len(best):
            best, fstype = mount_point, parts[2]
    return fstype


def unsupported_root_reason(path: Path) -> str | None:
    """Why a store root is unsupported (`store_root_unsupported`), or None."""
    lowered = str(path.resolve()).lower()
    for marker in _SYNC_MARKERS:
        if marker in lowered:
            return f"store root lies inside a synchronized folder ({marker})"
    fstype = _mount_fstype(path)
    if fstype in _NETWORK_FILESYSTEMS:
        return f"store root lies on a network file system ({fstype})"
    return None


class _RootLock:
    """Exclusive operating-system lock on `<root>/store.lock`."""

    def __init__(self, root: Path):
        self.path = root / "store.lock"
        self._handle = None

    def acquire(self) -> None:
        handle = open(self.path, "a+b")
        try:
            if sys.platform == "win32":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise StoreError("store_locked", f"another service host holds {self.path}") from None
        self._handle = handle

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt
                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None


class _ReadOnlyConnection:
    """A connection that answers reads and refuses every write, naming the reason."""

    READING = ("select", "explain", "with")

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def execute(self, sql: str, parameters: Any = ()) -> sqlite3.Cursor:
        head = sql.strip().split(" ", 1)[0].lower()
        if head not in self.READING and not (head == "pragma" and "=" not in sql):
            raise StoreError("read_only", f"this store root is open read-only; {sql.strip()[:40]!r} would write")
        return self.connection.execute(sql, parameters)

    def executescript(self, sql: str) -> None:
        raise StoreError("read_only", "this store root is open read-only; a script would write")

    def executemany(self, sql: str, parameters: Any) -> None:
        raise StoreError("read_only", f"this store root is open read-only; {sql.strip()[:40]!r} would write")

    def close(self) -> None:
        self.connection.close()


class Store:
    """An open store root. Use `Store.open(path)`; close it, or use it as a context manager."""

    def __init__(self, root: Path, connection: "sqlite3.Connection | _ReadOnlyConnection", lock: _RootLock,
                 read_only: bool = False):
        self.root = root
        self.db = connection
        self.read_only = read_only
        self._lock = lock
        self.write_lock = threading.RLock()  # one writer at a time inside this host

    @classmethod
    def open(cls, root: str | os.PathLike, *, create: bool = True, allow_unsupported_root: bool = False,
             read_only: bool = False) -> "Store":
        """Open a store root. `read_only=True` creates nothing, takes no lock, and refuses every write."""
        path = Path(root)
        if create and not read_only:
            path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            raise StoreError("store_root_missing", f"{path} is not a directory")
        reason = unsupported_root_reason(path)
        if reason and not allow_unsupported_root:
            raise StoreError("store_root_unsupported", reason)
        if read_only:
            return cls._open_read_only(path)
        lock = _RootLock(path)
        lock.acquire()
        try:
            # Workers share this connection. CPython's statement cache can return
            # inconsistent rows for concurrent cursors (python/cpython#118172).
            # Writes remain serialized by write_lock; reads use distinct statements.
            connection = sqlite3.connect(path / "store.db", isolation_level=None, check_same_thread=False,
                                         cached_statements=0)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.executescript(SCHEMA)
        except Exception:
            lock.release()
            raise
        return cls(path, connection, lock)

    @classmethod
    def _open_read_only(cls, path: Path) -> "Store":
        """A reader of an existing root: no lock, so another host may hold the root and keep writing."""
        database = path / "store.db"
        if not database.is_file():
            raise StoreError("store_root_missing", f"{database} does not exist")
        connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True,
                                     check_same_thread=False, cached_statements=0)
        return cls(path, _ReadOnlyConnection(connection), _RootLock(path), read_only=True)

    def close(self) -> None:
        try:
            self.db.close()
        finally:
            self._lock.release()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
