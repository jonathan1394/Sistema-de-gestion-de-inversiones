"""SQLite connection helpers for the application database."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Generator

from app.database.migrations import run_migrations

_migrated: set[str] = set()
_lock: Lock = Lock()


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Create a SQLite connection ensuring parent directory exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _migrate_once(db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def reset_migration_cache() -> None:
    """Clear the cache so the next get_connection() re-runs migrations."""
    global _migrated
    _migrated = set()


def _migrate_once(db_path: Path) -> None:
    key = str(db_path.resolve())
    if key in _migrated:
        return
    with _lock:
        if key in _migrated:
            return
        conn = sqlite3.connect(str(db_path))
        try:
            run_migrations(conn)
        finally:
            conn.close()
        _migrated.add(key)


@contextmanager
def connection_scope(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Context manager that handles commit/rollback/close lifecycle."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
