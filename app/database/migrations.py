"""Database migrations for core market, prospecting, and paper-trading tables."""

from __future__ import annotations

import sqlite3


SCHEMA_STATEMENTS = [
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
    ]


def run_migrations(connection: sqlite3.Connection) -> None:
    """Run all idempotent SQLite migrations required by the application."""
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)
    connection.commit()
