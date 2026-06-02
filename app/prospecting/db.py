"""Database helpers for prospect lifecycle and analysis storage."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class Prospect:
    symbol: str
    interval: str
    status: str
    added_at: int
    last_analysis_at: Optional[int]
    score: float
    trend: Optional[str]
    volatility: Optional[str]
    volume_profile: Optional[str]
    rsi_condition: Optional[str]
    signals_count: int
    metadata: dict[str, Any]
    notes: str


def _row_to_prospect(row: sqlite3.Row) -> Prospect:
    return Prospect(
        symbol=row["symbol"],
        interval=row["interval"],
        status=row["status"],
        added_at=row["added_at"],
        last_analysis_at=row["last_analysis_at"],
        score=row["score"],
        trend=row["trend"],
        volatility=row["volatility"],
        volume_profile=row["volume_profile"],
        rsi_condition=row["rsi_condition"],
        signals_count=row["signals_count"],
        metadata=json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {}),
        notes=row["notes"] or "",
    )


def add_prospect(
    connection: sqlite3.Connection,
    symbol: str,
    interval: str = "1d",
    notes: str = "",
) -> Prospect:
    """Insert a prospect if missing and return stored record."""
    now = int(time.time() * 1000)
    connection.execute(
        """
        INSERT OR IGNORE INTO prospects (symbol, interval, status, added_at, notes)
        VALUES (?, ?, 'watching', ?, ?)
        """,
        (symbol.upper(), interval, now, notes),
    )
    connection.commit()
    p = get_prospect(connection, symbol, interval)
    if p is None:
        raise RuntimeError(f"Failed to retrieve prospect {symbol} after insertion")
    return p


def get_prospect(
    connection: sqlite3.Connection,
    symbol: str,
    interval: str = "1d",
) -> Optional[Prospect]:
    """Fetch one prospect by symbol and interval."""
    row = connection.execute(
        "SELECT * FROM prospects WHERE symbol = ? AND interval = ?",
        (symbol.upper(), interval),
    ).fetchone()
    return _row_to_prospect(row) if row else None


def get_all_prospects(connection: sqlite3.Connection) -> list[Prospect]:
    """Fetch all prospects sorted by score and symbol."""
    rows = connection.execute(
        "SELECT * FROM prospects ORDER BY score DESC, symbol ASC"
    ).fetchall()
    return [_row_to_prospect(r) for r in rows]


def get_prospects_by_status(
    connection: sqlite3.Connection,
    status: str,
) -> list[Prospect]:
    """Fetch prospects filtered by lifecycle status."""
    rows = connection.execute(
        "SELECT * FROM prospects WHERE status = ? ORDER BY score DESC",
        (status,),
    ).fetchall()
    return [_row_to_prospect(r) for r in rows]


def update_prospect_analysis(
    connection: sqlite3.Connection,
    symbol: str,
    interval: str,
    score: float,
    trend: Optional[str],
    volatility: Optional[str],
    volume_profile: Optional[str],
    rsi_condition: Optional[str],
    signals_count: int,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Persist latest analysis metrics and metadata for a prospect."""
    now = int(time.time() * 1000)
    meta_json = json.dumps(metadata) if metadata else "{}"
    connection.execute(
        """
        UPDATE prospects
        SET last_analysis_at = ?,
            score = ?,
            trend = ?,
            volatility = ?,
            volume_profile = ?,
            rsi_condition = ?,
            signals_count = ?,
            metadata = ?
        WHERE symbol = ? AND interval = ?
        """,
        (now, score, trend, volatility, volume_profile, rsi_condition, signals_count, meta_json, symbol.upper(), interval),
    )
    connection.commit()


def update_prospect_status(
    connection: sqlite3.Connection,
    symbol: str,
    interval: str,
    status: str,
) -> None:
    """Change prospect status value for a symbol and interval."""
    connection.execute(
        "UPDATE prospects SET status = ? WHERE symbol = ? AND interval = ?",
        (status, symbol.upper(), interval),
    )
    connection.commit()


def archive_prospect(
    connection: sqlite3.Connection,
    symbol: str,
    interval: str,
) -> None:
    """Mark a prospect as archived."""
    update_prospect_status(connection, symbol, interval, "archived")


def remove_prospect(
    connection: sqlite3.Connection,
    symbol: str,
    interval: str,
) -> bool:
    """Delete a prospect and return whether a row was removed."""
    cursor = connection.execute(
        "DELETE FROM prospects WHERE symbol = ? AND interval = ?",
        (symbol.upper(), interval),
    )
    connection.commit()
    return cursor.rowcount > 0
