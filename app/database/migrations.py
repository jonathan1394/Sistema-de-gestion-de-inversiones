"""Database migrations via Alembic.

Keeps the ``run_migrations()`` entrypoint so existing callers don't break.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from alembic.config import Config

from alembic import command

logger = logging.getLogger(__name__)

# Keep raw statements as fallback for in-memory databases (tests).
_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS candles (
        symbol TEXT NOT NULL,
        interval TEXT NOT NULL,
        open_time INTEGER NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume REAL NOT NULL,
        close_time INTEGER NOT NULL,
        quote_asset_volume REAL NOT NULL,
        number_of_trades INTEGER NOT NULL,
        taker_buy_base_asset_volume REAL NOT NULL,
        taker_buy_quote_asset_volume REAL NOT NULL,
        PRIMARY KEY (symbol, interval, open_time)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_candles_symbol_interval_time
    ON candles (symbol, interval, open_time)
    """,
    """
    CREATE TABLE IF NOT EXISTS prospects (
        symbol TEXT NOT NULL,
        interval TEXT NOT NULL DEFAULT '1d',
        status TEXT NOT NULL DEFAULT 'watching',
        added_at INTEGER NOT NULL,
        last_analysis_at INTEGER,
        score REAL DEFAULT 0.0,
        trend TEXT,
        volatility TEXT,
        volume_profile TEXT,
        rsi_condition TEXT,
        signals_count INTEGER DEFAULT 0,
        metadata TEXT DEFAULT '{}',
        notes TEXT DEFAULT '',
        PRIMARY KEY (symbol, interval)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_prospects_status_score
    ON prospects (status, score DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS decision_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id TEXT NOT NULL UNIQUE,
        decision_type TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        symbol TEXT,
        strategy_name TEXT,
        timeframe TEXT,
        mode TEXT NOT NULL,
        approved INTEGER NOT NULL,
        reason TEXT NOT NULL,
        input_json TEXT DEFAULT '{}',
        output_json TEXT DEFAULT '{}',
        policy_version TEXT,
        strategy_version TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_decision_log_timestamp
    ON decision_log (timestamp)
    """,
    """
    CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        interval TEXT NOT NULL DEFAULT '4h',
        action TEXT NOT NULL,
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        commission REAL DEFAULT 0.0,
        pnl REAL DEFAULT 0.0,
        pnl_pct REAL DEFAULT 0.0,
        reason TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS paper_portfolio (
        symbol TEXT NOT NULL PRIMARY KEY,
        quantity REAL NOT NULL DEFAULT 0.0,
        entry_price REAL NOT NULL DEFAULT 0.0,
        current_price REAL NOT NULL DEFAULT 0.0,
        unrealized_pnl REAL NOT NULL DEFAULT 0.0,
        entry_time TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS paper_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        total_value REAL NOT NULL,
        cash REAL NOT NULL,
        drawdown_pct REAL NOT NULL DEFAULT 0.0
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_paper_trades_created_at
    ON paper_trades (created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_decision_log_timestamp_desc
    ON decision_log (timestamp DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_prospects_score_desc
    ON prospects (score DESC)
    """,
]

_ALEMBIC_CFG: Optional[Config] = None
_ALEMBIC_LAST_PATH: Optional[str] = None


def _alembic_cfg(db_path: Path) -> Config:
    global _ALEMBIC_CFG, _ALEMBIC_LAST_PATH
    url = f"sqlite:///{db_path}"
    if _ALEMBIC_CFG is None or _ALEMBIC_LAST_PATH != url:
        cfg = Config(str(Path(__file__).parent.parent.parent / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", url)
        _ALEMBIC_CFG = cfg
        _ALEMBIC_LAST_PATH = url
    return _ALEMBIC_CFG


def run_migrations(connection: sqlite3.Connection) -> None:
    """Apply all pending Alembic migrations to the given connection.

    Falls back to raw SQL for in-memory databases (common in tests).
    """
    db_path = _resolve_db_path(connection)
    if db_path is None:
        _run_raw(connection)
        return
    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "head")


def _run_raw(connection: sqlite3.Connection) -> None:
    for statement in _SCHEMA_STATEMENTS:
        connection.execute(statement)
    connection.commit()


def _resolve_db_path(connection: sqlite3.Connection) -> Optional[Path]:
    """Return the file path for the main database, or ``None`` for in-memory."""
    row = connection.execute("PRAGMA database_list").fetchone()
    if row is None:
        return None
    raw: str = row[2] or ""
    if not raw.strip():
        return None
    return Path(raw)
