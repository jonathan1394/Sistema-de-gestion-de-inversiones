"""Tests for app/database/migrations.py."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from app.database.connection import get_connection, reset_migration_cache
from app.database.migrations import run_migrations

EXPECTED_TABLES = {
    "candles",
    "prospects",
    "decision_log",
    "paper_trades",
    "paper_portfolio",
    "paper_snapshots",
}

ALEMBIC_HEAD = "7eaf882f9721"


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def test_run_migrations_creates_expected_tables():
    conn = sqlite3.connect(":memory:")

    run_migrations(conn)

    assert EXPECTED_TABLES.issubset(_tables(conn))


def test_run_migrations_is_idempotent():
    conn = sqlite3.connect(":memory:")

    run_migrations(conn)
    run_migrations(conn)

    assert EXPECTED_TABLES.issubset(_tables(conn))


def test_core_tables_have_expected_columns():
    conn = sqlite3.connect(":memory:")
    run_migrations(conn)

    assert {"symbol", "interval", "open_time", "close"}.issubset(_columns(conn, "candles"))
    assert {"symbol", "interval", "score", "metadata"}.issubset(_columns(conn, "prospects"))
    assert {"decision_id", "decision_type", "approved"}.issubset(_columns(conn, "decision_log"))


# ── Alembic real migration path (file-based database) ─────────────────────


def _alembic_version(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    return row[0] if row else None


def test_alembic_migration_creates_version_table():
    """File-based Alembic path creates the alembic_version table."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = sqlite3.connect(str(db_path))
        run_migrations(conn)
        conn.close()

        conn = sqlite3.connect(str(db_path))
        assert "alembic_version" in _tables(conn)
        version = _alembic_version(conn)
        assert version == ALEMBIC_HEAD
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)


def test_alembic_migration_is_idempotent():
    """Running Alembic migrations twice on the same file is safe."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = sqlite3.connect(str(db_path))
        run_migrations(conn)
        conn.close()

        conn = sqlite3.connect(str(db_path))
        run_migrations(conn)
        conn.close()

        conn = sqlite3.connect(str(db_path))
        assert EXPECTED_TABLES.issubset(_tables(conn))
        assert _alembic_version(conn) == ALEMBIC_HEAD
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)


def test_get_connection_auto_migrates():
    """get_connection() runs migrations automatically on file-based DB."""
    reset_migration_cache()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = get_connection(db_path)
        assert EXPECTED_TABLES.issubset(_tables(conn))
        assert _alembic_version(conn) == ALEMBIC_HEAD
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)


def test_get_connection_cache_prevents_duplicate_migrations():
    """Calling get_connection() twice only runs migrations once."""
    reset_migration_cache()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn_a = get_connection(db_path)
        conn_a.close()
        conn_b = get_connection(db_path)
        assert EXPECTED_TABLES.issubset(_tables(conn_b))
        assert _alembic_version(conn_b) == ALEMBIC_HEAD
        conn_b.close()
    finally:
        db_path.unlink(missing_ok=True)


def test_reset_migration_cache_reapplies():
    """After reset_migration_cache(), get_connection() re-runs migrations."""
    reset_migration_cache()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = get_connection(db_path)
        conn.close()
        reset_migration_cache()
        conn = get_connection(db_path)
        assert EXPECTED_TABLES.issubset(_tables(conn))
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)


def test_alembic_downgrade_and_upgrade():
    """Alembic downgrade then upgrade round-trip leaves schema intact."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        from alembic.config import Config

        from alembic import command

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

        command.upgrade(cfg, "head")
        conn = sqlite3.connect(str(db_path))
        assert _alembic_version(conn) == ALEMBIC_HEAD
        assert EXPECTED_TABLES.issubset(_tables(conn))
        conn.close()

        command.downgrade(cfg, "ca52cc9a3084")
        conn = sqlite3.connect(str(db_path))
        assert _alembic_version(conn) == "ca52cc9a3084"
        assert EXPECTED_TABLES.issubset(_tables(conn))
        conn.close()

        command.downgrade(cfg, "base")
        conn = sqlite3.connect(str(db_path))
        assert _alembic_version(conn) is None
        conn.close()

        command.upgrade(cfg, "head")
        conn = sqlite3.connect(str(db_path))
        assert _alembic_version(conn) == ALEMBIC_HEAD
        assert EXPECTED_TABLES.issubset(_tables(conn))
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)
