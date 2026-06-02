"""Tests for app/database/migrations.py."""

from __future__ import annotations

import sqlite3

from app.database.migrations import run_migrations

EXPECTED_TABLES = {
    "candles",
    "prospects",
    "decision_log",
    "paper_trades",
    "paper_portfolio",
    "paper_snapshots",
}


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
