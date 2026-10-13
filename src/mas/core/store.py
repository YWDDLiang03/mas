"""Store root (design §14, §14.1): one service host per local, unsynchronized store root.

The store root holds one SQLite database. Journal events and artifacts are
append-only, enforced by triggers, so no code path can rewrite or delete them.
The host holds an operating-system lock on the root for as long as it is open;
the operating system releases it when the process ends, so a crash never leaves
a stale lock.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

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


class Store:
    """An open store root. Use `Store.open(path)`; close it, or use it as a context manager."""

    def __init__(self, root: Path, connection: sqlite3.Connection, lock: _RootLock):
        self.root = root
        self.db = connection
        self._lock = lock

    @classmethod
    def open(cls, root: str | os.PathLike, *, create: bool = True, allow_unsupported_root: bool = False) -> "Store":
        path = Path(root)
        if create:
            path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            raise StoreError("store_root_missing", f"{path} is not a directory")
        reason = unsupported_root_reason(path)
        if reason and not allow_unsupported_root:
            raise StoreError("store_root_unsupported", reason)
        lock = _RootLock(path)
        lock.acquire()
        try:
            connection = sqlite3.connect(path / "store.db", isolation_level=None, check_same_thread=False)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.executescript(SCHEMA)
        except Exception:
            lock.release()
            raise
        return cls(path, connection, lock)

    def close(self) -> None:
        try:
            self.db.close()
        finally:
            self._lock.release()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
