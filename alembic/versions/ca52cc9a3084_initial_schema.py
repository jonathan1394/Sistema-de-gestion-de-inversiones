"""initial_schema

Revision ID: ca52cc9a3084
Revises:
Create Date: 2026-06-02 17:09:22.047773

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ca52cc9a3084'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_candles_symbol_interval_time
        ON candles (symbol, interval, open_time)
    """)
    op.execute("""
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
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_prospects_status_score
        ON prospects (status, score DESC)
    """)
    op.execute("""
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
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_decision_log_timestamp
        ON decision_log (timestamp)
    """)
    op.execute("""
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
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS paper_portfolio (
            symbol TEXT NOT NULL PRIMARY KEY,
            quantity REAL NOT NULL DEFAULT 0.0,
            entry_price REAL NOT NULL DEFAULT 0.0,
            current_price REAL NOT NULL DEFAULT 0.0,
            unrealized_pnl REAL NOT NULL DEFAULT 0.0,
            entry_time TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS paper_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_value REAL NOT NULL,
            cash REAL NOT NULL,
            drawdown_pct REAL NOT NULL DEFAULT 0.0
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS paper_snapshots")
    op.execute("DROP TABLE IF EXISTS paper_portfolio")
    op.execute("DROP TABLE IF EXISTS paper_trades")
    op.execute("DROP TABLE IF EXISTS decision_log")
    op.execute("DROP TABLE IF EXISTS prospects")
    op.execute("DROP TABLE IF EXISTS candles")
