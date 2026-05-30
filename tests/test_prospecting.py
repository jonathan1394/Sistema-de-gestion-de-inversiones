import json
import time
import sqlite3

import pytest

from app.prospecting.db import (
    add_prospect,
    archive_prospect,
    get_all_prospects,
    get_prospect,
    get_prospects_by_status,
    remove_prospect,
    update_prospect_analysis,
    update_prospect_status,
)
from app.prospecting.scoring import ProspectScore, score_prospect


@pytest.fixture
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
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
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prospects_status_score ON prospects (status, score DESC)")
    conn.commit()
    return conn


class TestProspectDB:
    def test_add_and_get_prospect(self, db: sqlite3.Connection):
        p = add_prospect(db, "BTCUSDT", "1d", notes="test")
        assert p.symbol == "BTCUSDT"
        assert p.interval == "1d"
        assert p.status == "watching"

        retrieved = get_prospect(db, "btcusdt", "1d")
        assert retrieved is not None
        assert retrieved.symbol == "BTCUSDT"

    def test_add_duplicate_is_idempotent(self, db: sqlite3.Connection):
        add_prospect(db, "BTCUSDT", "1d")
        add_prospect(db, "btcusdt", "1d")
        all_p = get_all_prospects(db)
        assert len(all_p) == 1

    def test_get_all_prospects_returns_sorted(self, db: sqlite3.Connection):
        add_prospect(db, "AAVEUSDT", "1d")
        add_prospect(db, "BTCUSDT", "1d")
        all_p = get_all_prospects(db)
        assert len(all_p) == 2

    def test_get_prospects_by_status(self, db: sqlite3.Connection):
        add_prospect(db, "BTCUSDT", "1d")
        add_prospect(db, "ETHUSDT", "1d")
        update_prospect_status(db, "ETHUSDT", "1d", "active")
        watching = get_prospects_by_status(db, "watching")
        active = get_prospects_by_status(db, "active")
        assert len(watching) == 1
        assert len(active) == 1

    def test_update_analysis(self, db: sqlite3.Connection):
        add_prospect(db, "BTCUSDT", "1d")
        update_prospect_analysis(
            db, "BTCUSDT", "1d",
            score=0.85,
            trend="strong_up",
            volatility="moderate",
            volume_profile="high",
            rsi_condition="neutral",
            signals_count=3,
            metadata={"return_pct": 5.2},
        )
        p = get_prospect(db, "BTCUSDT", "1d")
        assert p is not None
        assert p.score == 0.85
        assert p.trend == "strong_up"
        assert p.signals_count == 3
        assert p.last_analysis_at is not None
        assert p.metadata["return_pct"] == 5.2

    def test_archive_prospect(self, db: sqlite3.Connection):
        add_prospect(db, "BTCUSDT", "1d")
        archive_prospect(db, "BTCUSDT", "1d")
        p = get_prospect(db, "BTCUSDT", "1d")
        assert p is not None
        assert p.status == "archived"

    def test_remove_prospect(self, db: sqlite3.Connection):
        add_prospect(db, "BTCUSDT", "1d")
        assert remove_prospect(db, "BTCUSDT", "1d") is True
        assert get_prospect(db, "BTCUSDT", "1d") is None

    def test_remove_nonexistent(self, db: sqlite3.Connection):
        assert remove_prospect(db, "NONEXIST", "1d") is False

    def test_prospect_initially_has_defaults(self, db: sqlite3.Connection):
        add_prospect(db, "SOLUSDT", "1d")
        p = get_prospect(db, "SOLUSDT", "1d")
        assert p is not None
        assert p.score == 0.0
        assert p.signals_count == 0
        assert p.metadata == {}
        assert p.notes == ""


class TestScoring:
    def test_score_prospect_strong_up(self):
        ps = score_prospect("strong_up", "moderate", "high", "neutral", 5.0, 3)
        assert ps.total > 0.5

    def test_score_prospect_strong_down(self):
        ps = score_prospect("strong_down", "high", "normal", "overbought", -10.0, 0)
        assert ps.total < 0.4

    def test_score_is_bounded(self):
        ps = score_prospect("strong_up", "moderate", "high", "neutral", 100.0, 10)
        assert 0.0 <= ps.total <= 1.0

    def test_score_returns_breakdown(self, db: sqlite3.Connection):
        ps = score_prospect("up", "low", "above_average", "oversold", 3.0, 2)
        assert isinstance(ps, ProspectScore)
        assert ps.trend_score > 0
        assert ps.volatility_score > 0
        assert ps.breakdown != ""

    def test_score_prospect_decreasing(self):
        high = score_prospect("strong_up", "moderate", "high", "neutral", 10.0, 5)
        low = score_prospect("strong_down", "high", "normal", "overbought", -15.0, 0)
        assert high.total > low.total
