"""Tests for app/database/dao.py and connection_scope."""

import sqlite3
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Generator

import pytest

from app.database.connection import connection_scope, get_connection
from app.database.dao import CandlesFilter, DataAccessObject, ProspectFilter
from app.database.migrations import run_migrations


@pytest.fixture
def db_path() -> Generator[Path, None, None]:
    with NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    conn = sqlite3.connect(path)
    run_migrations(conn)
    conn.close()
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def dao(db_path: Path) -> DataAccessObject:
    return DataAccessObject(db_path)


class TestConnectionScope:
    def test_commit_on_success(self, db_path: Path):
        with connection_scope(db_path) as conn:
            conn.execute("INSERT INTO paper_snapshots (timestamp, total_value, cash) VALUES ('t', 100, 50)")
        with get_connection(db_path) as conn:
            rows = conn.execute("SELECT COUNT(*) as cnt FROM paper_snapshots").fetchall()
            assert rows[0]["cnt"] == 1

    def test_rollback_on_error(self, db_path: Path):
        try:
            with connection_scope(db_path) as conn:
                conn.execute("INSERT INTO paper_snapshots (timestamp, total_value, cash) VALUES ('t', 100, 50)")
                raise ValueError("simulated error")
        except ValueError:
            pass
        with get_connection(db_path) as conn:
            rows = conn.execute("SELECT COUNT(*) as cnt FROM paper_snapshots").fetchall()
            assert rows[0]["cnt"] == 0

    def test_rollback_on_sql_error(self, db_path: Path):
        with pytest.raises(sqlite3.OperationalError):
            with connection_scope(db_path) as conn:
                conn.execute("INSERT INTO nonexistent VALUES (1)")


class TestDataAccessObject:
    def test_store_and_get_candles(self, dao: DataAccessObject):
        klines = [
            [1609459200000, 100.0, 101.0, 99.0, 100.5, 1000, 1609459260000, 50000, 100, 20000, 25000],
            [1609459260000, 101.0, 102.0, 100.0, 101.5, 1200, 1609459320000, 55000, 110, 22000, 28000],
        ]
        count = dao.store_klines("BTCUSDT", "1m", klines)
        assert count == 2

        candles = dao.get_candles(CandlesFilter(symbol="BTCUSDT", interval="1m"))
        assert len(candles) == 2
        assert candles[0]["symbol"] == "BTCUSDT"
        assert candles[0]["open"] == 100.0

    def test_store_klines_chunked(self, dao: DataAccessObject):
        klines = []
        for i in range(1500):
            base = 1609459200000 + i * 60000
            klines.append([base, 100.0, 101.0, 99.0, 100.5, 1000, base + 60000, 50000, 100, 20000, 25000])
        count = dao.store_klines_chunked("ETHUSDT", "1m", klines, chunk_size=500)
        assert count == 1500

        candles = dao.get_candles(CandlesFilter(symbol="ETHUSDT", interval="1m"))
        assert len(candles) == 1500

    def test_get_candles_with_limit(self, dao: DataAccessObject):
        klines = []
        for i in range(10):
            base = 1609459200000 + i * 60000
            klines.append([base, 100.0 + i, 101.0, 99.0, 100.5, 1000, base + 60000, 50000, 100, 20000, 25000])
        dao.store_klines("BTCUSDT", "1h", klines)

        candles = dao.get_candles(CandlesFilter(symbol="BTCUSDT", interval="1h", limit=3))
        assert len(candles) == 3

    def test_prospect_lifecycle(self, dao: DataAccessObject):
        p = dao.add_prospect("BTCUSDT", interval="1d", notes="test coin")
        assert p["symbol"] == "BTCUSDT"
        assert p["status"] == "watching"

        fetched = dao.get_prospect("BTCUSDT", "1d")
        assert fetched is not None
        assert fetched["symbol"] == "BTCUSDT"

        dao.update_prospect_analysis("BTCUSDT", "1d", score=85.0, trend="bullish")
        updated = dao.get_prospect("BTCUSDT", "1d")
        assert updated is not None
        assert updated["score"] == 85.0
        assert updated["trend"] == "bullish"

        dao.update_prospect_status("BTCUSDT", "1d", "active")
        updated2 = dao.get_prospect("BTCUSDT", "1d")
        assert updated2 is not None
        assert updated2["status"] == "active"

        assert dao.remove_prospect("BTCUSDT", "1d") is True
        assert dao.get_prospect("BTCUSDT", "1d") is None

    def test_get_prospects_filtered(self, dao: DataAccessObject):
        dao.add_prospect("BTCUSDT", "1d")
        dao.add_prospect("ETHUSDT", "1d")
        dao.add_prospect("SOLUSDT", "1d")

        all_p = dao.get_prospects(ProspectFilter(limit=10))
        assert len(all_p) == 3

        dao.update_prospect_status("SOLUSDT", "1d", "archived")
        active = dao.get_prospects(ProspectFilter(status="watching", limit=10))
        assert len(active) == 2

    def test_record_and_get_trades(self, dao: DataAccessObject):
        t1 = dao.record_trade("BTCUSDT", "BUY", 1.0, 50000, reason="entry")
        assert t1["symbol"] == "BTCUSDT"
        assert t1["action"] == "BUY"

        t2 = dao.record_trade("BTCUSDT", "SELL", 1.0, 51000, pnl=1000, reason="exit")
        assert t2["pnl"] == 1000

        trades = dao.get_trades(limit=10)
        assert len(trades) == 2

        btc_trades = dao.get_trades(symbol="BTCUSDT")
        assert len(btc_trades) == 2

    def test_position_upsert_and_remove(self, dao: DataAccessObject):
        pos = dao.upsert_position("BTCUSDT", 1.0, 50000, 51000)
        assert pos["quantity"] == 1.0
        assert pos["unrealized_pnl"] == 1000.0

        all_pos = dao.get_all_positions()
        assert len(all_pos) == 1

        assert dao.remove_position("BTCUSDT") is True
        assert len(dao.get_all_positions()) == 0

    def test_snapshot_lifecycle(self, dao: DataAccessObject):
        dao.add_snapshot(1000, 500)
        snapshots = dao.get_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0]["total_value"] == 1000

    def test_decision_log(self, dao: DataAccessObject):
        did = dao.log_decision(
            decision_type="buy_signal",
            symbol="BTCUSDT",
            mode="paper",
            approved=True,
            reason="Signal detected",
        )
        assert did != ""

        decisions = dao.get_recent_decisions(limit=10)
        assert len(decisions) == 1
        assert decisions[0]["approved"] == 1

        rejected = dao.get_recent_decisions(rejected_only=True)
        assert len(rejected) == 0

        approved = dao.get_recent_decisions(approved_only=True)
        assert len(approved) == 1
