"""SQLite persistence helpers for paper-trading state and history."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.database.migrations import run_migrations

logger = logging.getLogger(__name__)

@dataclass
class StoredTrade:
    id: int
    symbol: str
    interval: str
    action: str
    quantity: float
    price: float
    commission: float
    pnl: float
    pnl_pct: float
    reason: str
    created_at: str


@dataclass
class StoredPosition:
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    entry_time: str
    updated_at: str


def init_portfolio_tables(connection: sqlite3.Connection) -> None:
    """Create portfolio, trades, and snapshots tables if missing."""
    run_migrations(connection)


def record_trade(
    connection: sqlite3.Connection,
    symbol: str,
    action: str,
    quantity: float,
    price: float,
    commission: float = 0.0,
    pnl: float = 0.0,
    pnl_pct: float = 0.0,
    reason: str = "",
    interval: str = "4h",
) -> StoredTrade:
    """Insert one executed trade and return stored row."""
    now = datetime.now(timezone.utc).isoformat()
    cursor = connection.execute(
        """
        INSERT INTO paper_trades (symbol, interval, action, quantity, price, commission, pnl, pnl_pct, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (symbol.upper(), interval, action, quantity, price, commission, pnl, pnl_pct, reason, now),
    )
    connection.commit()
    row = connection.execute(
        "SELECT * FROM paper_trades WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_trade(row)


def get_trades(
    connection: sqlite3.Connection,
    symbol: str | None = None,
    limit: int = 100,
) -> list[StoredTrade]:
    """Fetch recent trades optionally filtered by symbol."""
    if symbol:
        rows = connection.execute(
            "SELECT * FROM paper_trades WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
            (symbol.upper(), limit),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM paper_trades ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_trade(r) for r in rows]


def _row_to_trade(row: sqlite3.Row) -> StoredTrade:
    return StoredTrade(
        id=row["id"],
        symbol=row["symbol"],
        interval=row["interval"],
        action=row["action"],
        quantity=row["quantity"],
        price=row["price"],
        commission=row["commission"],
        pnl=row["pnl"],
        pnl_pct=row["pnl_pct"],
        reason=row["reason"],
        created_at=row["created_at"],
    )


def upsert_position(
    connection: sqlite3.Connection,
    symbol: str,
    quantity: float,
    entry_price: float,
    current_price: float,
    entry_time: str | None = None,
) -> StoredPosition:
    """Insert or update one portfolio position row."""
    now = datetime.now(timezone.utc).isoformat()
    if entry_time is None:
        entry_time = now
    unrealized_pnl = quantity * (current_price - entry_price)
    connection.execute(
        """
        INSERT INTO paper_portfolio (symbol, quantity, entry_price, current_price, unrealized_pnl, entry_time, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            quantity = excluded.quantity,
            entry_price = excluded.entry_price,
            current_price = excluded.current_price,
            unrealized_pnl = excluded.unrealized_pnl,
            updated_at = excluded.updated_at
        """,
        (symbol.upper(), quantity, entry_price, current_price, unrealized_pnl, entry_time, now),
    )
    connection.commit()
    row = connection.execute(
        "SELECT * FROM paper_portfolio WHERE symbol = ?", (symbol.upper(),)
    ).fetchone()
    return _row_to_position(row)


def remove_position(
    connection: sqlite3.Connection,
    symbol: str,
) -> bool:
    """Delete one position by symbol and return success flag."""
    cursor = connection.execute(
        "DELETE FROM paper_portfolio WHERE symbol = ?", (symbol.upper(),)
    )
    connection.commit()
    return cursor.rowcount > 0


def get_all_positions(connection: sqlite3.Connection) -> list[StoredPosition]:
    """Return all stored portfolio positions."""
    rows = connection.execute("SELECT * FROM paper_portfolio ORDER BY symbol").fetchall()
    return [_row_to_position(r) for r in rows]


def _row_to_position(row: sqlite3.Row) -> StoredPosition:
    return StoredPosition(
        symbol=row["symbol"],
        quantity=row["quantity"],
        entry_price=row["entry_price"],
        current_price=row["current_price"],
        unrealized_pnl=row["unrealized_pnl"],
        entry_time=row["entry_time"],
        updated_at=row["updated_at"],
    )


def add_snapshot(
    connection: sqlite3.Connection,
    total_value: float,
    cash: float,
    drawdown_pct: float = 0.0,
) -> None:
    """Persist one portfolio snapshot row."""
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "INSERT INTO paper_snapshots (timestamp, total_value, cash, drawdown_pct) VALUES (?, ?, ?, ?)",
        (now, total_value, cash, drawdown_pct),
    )
    connection.commit()


def get_snapshots(
    connection: sqlite3.Connection,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Fetch historical snapshots ordered by timestamp."""
    rows = connection.execute(
        "SELECT * FROM paper_snapshots ORDER BY timestamp ASC LIMIT ?", (limit,)
    ).fetchall()
    return [
        {
            "timestamp": r["timestamp"],
            "total_value": r["total_value"],
            "cash": r["cash"],
            "drawdown_pct": r["drawdown_pct"],
        }
        for r in rows
    ]
