"""Data Access Object — typed interface over SQLite for common operations."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.database.connection import connection_scope

logger = logging.getLogger(__name__)


@dataclass
class CandlesFilter:
    symbol: str
    interval: str
    start_time_ms: int | None = None
    end_time_ms: int | None = None
    limit: int | None = None
    desc: bool = False


@dataclass
class ProspectFilter:
    symbol: str | None = None
    interval: str | None = None
    status: str | None = None
    limit: int = 100


class DataAccessObject:
    """Typed data-access layer over the application SQLite database."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    # ── Candles ──────────────────────────────────────────────

    def store_klines(self, symbol: str, interval: str, klines: list[list]) -> int:
        """Store raw Binance kline data, returns rows inserted."""
        rows = [
            (
                symbol.upper(), interval,
                int(k[0]), float(k[1]), float(k[2]), float(k[3]),
                float(k[4]), float(k[5]), int(k[6]), float(k[7]),
                int(k[8]), float(k[9]), float(k[10]),
            )
            for k in klines
        ]
        with connection_scope(self._db_path) as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO candles (
                    symbol, interval, open_time, open, high, low,
                    close, volume, close_time, quote_asset_volume,
                    number_of_trades, taker_buy_base_asset_volume,
                    taker_buy_quote_asset_volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
        return len(rows)

    def store_klines_chunked(self, symbol: str, interval: str,
                             klines: list[list], chunk_size: int = 1000) -> int:
        """Store klines in chunks to avoid large transactions."""
        total = 0
        for i in range(0, len(klines), chunk_size):
            total += self.store_klines(symbol, interval, klines[i:i + chunk_size])
        return total

    def get_candles(self, filter_: CandlesFilter) -> list[dict[str, Any]]:
        """Retrieve candles matching the given filter."""
        query = """SELECT * FROM candles
                   WHERE symbol = ? AND interval = ?"""
        params: list[object] = [filter_.symbol.upper(), filter_.interval]
        if filter_.start_time_ms is not None:
            query += " AND open_time >= ?"
            params.append(filter_.start_time_ms)
        if filter_.end_time_ms is not None:
            query += " AND open_time <= ?"
            params.append(filter_.end_time_ms)
        if filter_.desc and filter_.limit is not None:
            query += " ORDER BY open_time DESC LIMIT ?"
            params.append(filter_.limit)
        else:
            query += " ORDER BY open_time ASC"
            if filter_.limit is not None:
                query += " LIMIT ?"
                params.append(filter_.limit)

        with connection_scope(self._db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        if filter_.desc and filter_.limit:
            rows = list(reversed(rows))
        return [dict(r) for r in rows]

    # ── Prospects ────────────────────────────────────────────

    def add_prospect(self, symbol: str, interval: str = "1d",
                     notes: str = "") -> dict[str, Any]:
        """Insert a prospect if missing and return stored record."""
        now = int(time.time() * 1000)
        with connection_scope(self._db_path) as conn:
            conn.execute(
                """INSERT OR IGNORE INTO prospects
                   (symbol, interval, status, added_at, notes)
                   VALUES (?, ?, 'watching', ?, ?)""",
                (symbol.upper(), interval, now, notes),
            )
        result = self.get_prospect(symbol, interval)
        assert result is not None, f"Failed to retrieve prospect {symbol} after insertion"
        return result

    def get_prospect(self, symbol: str, interval: str = "1d") -> dict[str, Any] | None:
        """Fetch one prospect by symbol and interval."""
        with connection_scope(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM prospects WHERE symbol = ? AND interval = ?",
                (symbol.upper(), interval),
            ).fetchone()
        return dict(row) if row else None

    def get_prospects(self, filter_: ProspectFilter) -> list[dict[str, Any]]:
        """Fetch prospects with optional filtering."""
        query = "SELECT * FROM prospects"
        params: list[object] = []
        conditions: list[str] = []
        if filter_.symbol:
            conditions.append("symbol = ?")
            params.append(filter_.symbol.upper())
        if filter_.interval:
            conditions.append("interval = ?")
            params.append(filter_.interval)
        if filter_.status:
            conditions.append("status = ?")
            params.append(filter_.status)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY score DESC, symbol ASC LIMIT ?"
        params.append(filter_.limit)

        with connection_scope(self._db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def update_prospect_analysis(
        self, symbol: str, interval: str, *,
        score: float, trend: str | None = None,
        volatility: str | None = None,
        volume_profile: str | None = None,
        rsi_condition: str | None = None,
        signals_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = int(time.time() * 1000)
        meta_json = json.dumps(metadata) if metadata else "{}"
        with connection_scope(self._db_path) as conn:
            conn.execute(
                """UPDATE prospects SET last_analysis_at=?, score=?, trend=?,
                   volatility=?, volume_profile=?, rsi_condition=?,
                   signals_count=?, metadata=?
                   WHERE symbol=? AND interval=?""",
                (now, score, trend, volatility, volume_profile,
                 rsi_condition, signals_count, meta_json,
                 symbol.upper(), interval),
            )

    def update_prospect_status(self, symbol: str, interval: str,
                               status: str) -> None:
        with connection_scope(self._db_path) as conn:
            conn.execute(
                "UPDATE prospects SET status=? WHERE symbol=? AND interval=?",
                (status, symbol.upper(), interval),
            )

    def remove_prospect(self, symbol: str, interval: str = "1d") -> bool:
        with connection_scope(self._db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM prospects WHERE symbol=? AND interval=?",
                (symbol.upper(), interval),
            )
        return cursor.rowcount > 0

    # ── Paper Trades ─────────────────────────────────────────

    def record_trade(self, symbol: str, action: str, quantity: float,
                     price: float, commission: float = 0.0,
                     pnl: float = 0.0, pnl_pct: float = 0.0,
                     reason: str = "", interval: str = "4h") -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with connection_scope(self._db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO paper_trades
                   (symbol, interval, action, quantity, price,
                    commission, pnl, pnl_pct, reason, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (symbol.upper(), interval, action, quantity, price,
                 commission, pnl, pnl_pct, reason, now),
            )
            row = conn.execute(
                "SELECT * FROM paper_trades WHERE id=?",
                (cursor.lastrowid,),
            ).fetchone()
        return dict(row) if row else {}

    def get_trades(self, symbol: str | None = None,
                   limit: int = 100) -> list[dict[str, Any]]:
        with connection_scope(self._db_path) as conn:
            if symbol:
                rows = conn.execute(
                    """SELECT * FROM paper_trades
                       WHERE symbol=? ORDER BY created_at DESC LIMIT ?""",
                    (symbol.upper(), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM paper_trades ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(r) for r in rows]

    # ── Portfolio Positions ──────────────────────────────────

    def upsert_position(self, symbol: str, quantity: float,
                        entry_price: float, current_price: float,
                        entry_time: str | None = None) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        if entry_time is None:
            entry_time = now
        unrealized_pnl = quantity * (current_price - entry_price)
        with connection_scope(self._db_path) as conn:
            conn.execute(
                """INSERT INTO paper_portfolio
                   (symbol, quantity, entry_price, current_price,
                    unrealized_pnl, entry_time, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(symbol) DO UPDATE SET
                       quantity=excluded.quantity,
                       entry_price=excluded.entry_price,
                       current_price=excluded.current_price,
                       unrealized_pnl=excluded.unrealized_pnl,
                       updated_at=excluded.updated_at""",
                (symbol.upper(), quantity, entry_price, current_price,
                 unrealized_pnl, entry_time, now),
            )
            row = conn.execute(
                "SELECT * FROM paper_portfolio WHERE symbol=?",
                (symbol.upper(),),
            ).fetchone()
        return dict(row) if row else {}

    def remove_position(self, symbol: str) -> bool:
        with connection_scope(self._db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM paper_portfolio WHERE symbol=?",
                (symbol.upper(),),
            )
        return cursor.rowcount > 0

    def get_all_positions(self) -> list[dict[str, Any]]:
        with connection_scope(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM paper_portfolio ORDER BY symbol",
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Snapshots ────────────────────────────────────────────

    def add_snapshot(self, total_value: float, cash: float,
                     drawdown_pct: float = 0.0) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with connection_scope(self._db_path) as conn:
            conn.execute(
                """INSERT INTO paper_snapshots
                   (timestamp, total_value, cash, drawdown_pct)
                   VALUES (?, ?, ?, ?)""",
                (now, total_value, cash, drawdown_pct),
            )

    def get_snapshots(self, limit: int = 500) -> list[dict[str, Any]]:
        with connection_scope(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM paper_snapshots ORDER BY timestamp ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Decision Log ─────────────────────────────────────────

    def log_decision(self, *, decision_type: str,
                     symbol: str | None = None,
                     strategy_name: str | None = None,
                     timeframe: str | None = None,
                     mode: str, approved: bool, reason: str,
                     input_data: dict[str, Any] | None = None,
                     output_data: dict[str, Any] | None = None,
                     policy_version: str | None = None,
                     strategy_version: str | None = None) -> str:
        decision_id = str(uuid.uuid4())
        timestamp = str(int(time.time() * 1000))
        input_json = json.dumps(input_data or {})
        output_json = json.dumps(output_data or {})
        with connection_scope(self._db_path) as conn:
            conn.execute(
                """INSERT INTO decision_log
                   (decision_id, decision_type, timestamp, symbol,
                    strategy_name, timeframe, mode, approved, reason,
                    input_json, output_json, policy_version, strategy_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (decision_id, decision_type, timestamp, symbol,
                 strategy_name, timeframe, mode, 1 if approved else 0,
                 reason, input_json, output_json, policy_version,
                 strategy_version),
            )
        return decision_id

    def get_recent_decisions(self, limit: int = 50,
                             symbol: str | None = None,
                             approved_only: bool = False,
                             rejected_only: bool = False,
                             ) -> list[dict[str, Any]]:
        query = "SELECT * FROM decision_log"
        params: list[object] = []
        conditions: list[str] = []
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if approved_only:
            conditions.append("approved = 1")
        if rejected_only:
            conditions.append("approved = 0")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with connection_scope(self._db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
