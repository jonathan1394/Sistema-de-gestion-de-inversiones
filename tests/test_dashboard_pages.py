"""Tests for dashboard page-level pure functions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.dashboard.helpers import compute_confluence
from app.dashboard.pages.asset_detail import _rec_badge
from app.dashboard.pages.decision_log import _decisions_to_dataframe
from app.dashboard.pages.logs import _append_log, _read_logs
from app.dashboard.pages.market_analysis import _badge
from app.dashboard.pages.prospects import _prospect_rows
from app.governance.decision_log import DecisionLogEntry
from app.prospecting.db import Prospect

# ── compute_confluence ─────────────────────────────────────────────────────


class TestComputeConfluence:
    """Extracted to app/dashboard/helpers.py."""

    def test_all_bullish(self):
        results = [
            {"trend": "strong_up"},
            {"trend": "up"},
            {"trend": "strong_up"},
        ]
        assert compute_confluence(results) == 3

    def test_all_bearish(self):
        results = [
            {"trend": "strong_down"},
            {"trend": "down"},
            {"trend": "sideways"},
        ]
        assert compute_confluence(results) == 0

    def test_mixed(self):
        results = [
            {"trend": "up"},
            {"trend": "sideways"},
            {"trend": "down"},
        ]
        assert compute_confluence(results) == 1

    def test_edge_trends(self):
        results = [
            {"trend": "strong_up"},
            {"trend": "strong_down"},
        ]
        assert compute_confluence(results) == 1

    def test_missing_trend_key(self):
        results = [
            {},
            {"trend": "up"},
        ]
        assert compute_confluence(results) == 1

    def test_empty(self):
        assert compute_confluence([]) == 0

    def test_unknown_trend_value(self):
        results = [
            {"trend": "unknown_value"},
            {"trend": "up"},
        ]
        assert compute_confluence(results) == 1


# ── _badge / _rec_badge ────────────────────────────────────────────────────


class TestBadge:
    def test_badge_renders(self):
        html = _badge("ALTA", "badge-pos")
        assert html == '<span class="badge badge-pos">ALTA</span>'

    def test_badge_empty_label(self):
        html = _badge("", "badge-neutral")
        assert html == '<span class="badge badge-neutral"></span>'


class TestRecBadge:
    def test_invertir(self):
        html = _rec_badge("INVERTIR")
        assert "badge-pos" in html
        assert "INVERTIR" in html

    def test_vigilar(self):
        html = _rec_badge("VIGILAR")
        assert "badge-warn" in html

    def test_neutral(self):
        html = _rec_badge("NEUTRAL")
        assert "badge-neutral" in html

    def test_evitar(self):
        html = _rec_badge("EVITAR")
        assert "badge-neg" in html

    def test_unknown_label_falls_back_to_neutral(self):
        html = _rec_badge("UNKNOWN")
        assert "badge-neutral" in html
        assert "UNKNOWN" in html


# ── _prospect_rows ─────────────────────────────────────────────────────────


class TestProspectRows:
    def test_single_prospect(self):
        prospects = [
            Prospect(
                symbol="BTCUSDT",
                interval="1d",
                status="active",
                added_at=1000,
                last_analysis_at=2000,
                score=0.85,
                trend="up",
                volatility="medium",
                volume_profile="high",
                rsi_condition="neutral",
                signals_count=5,
                metadata={},
                notes="",
            )
        ]
        rows = _prospect_rows(prospects)
        assert len(rows) == 1
        row = rows[0]
        assert row["Symbol"] == "BTCUSDT"
        assert row["Status"] == "active"
        assert row["Score"] == "0.8500"
        # score 0.85 needs confluence >= 2 for INVERTIR;
        # _prospect_rows calls get_recommendation(score) with default confluence=0 → VIGILAR
        assert "VIGILAR" in row["Rec"]
        assert row["Trend"] == "up"
        assert row["Signals"] == 5

    def test_multiple_prospects(self):
        prospects = [
            Prospect(
                symbol="BTCUSDT",
                interval="1d",
                status="active",
                added_at=1000,
                last_analysis_at=None,
                score=0.9,
                trend="strong_up",
                volatility="low",
                volume_profile=None,
                rsi_condition=None,
                signals_count=3,
                metadata={},
                notes="",
            ),
            Prospect(
                symbol="ETHUSDT",
                interval="1d",
                status="watching",
                added_at=2000,
                last_analysis_at=None,
                score=0.3,
                trend="down",
                volatility="high",
                volume_profile="low",
                rsi_condition="oversold",
                signals_count=0,
                metadata={},
                notes="",
            ),
        ]
        rows = _prospect_rows(prospects)
        assert len(rows) == 2
        assert rows[0]["Symbol"] == "BTCUSDT"
        # score 0.9, confluence=0 → VIGILAR (needs confluence >= 2 for INVERTIR)
        assert "VIGILAR" in rows[0]["Rec"]
        assert "EVITAR" in rows[1]["Rec"]

    def test_empty(self):
        assert _prospect_rows([]) == []

    def test_missing_optional_fields(self):
        prospects = [
            Prospect(
                symbol="SOLUSDT",
                interval="1d",
                status="active",
                added_at=1000,
                last_analysis_at=None,
                score=0.55,
                trend=None,
                volatility=None,
                volume_profile=None,
                rsi_condition=None,
                signals_count=0,
                metadata={},
                notes="",
            )
        ]
        rows = _prospect_rows(prospects)
        row = rows[0]
        assert row["Trend"] == "-"
        assert row["Volatility"] == "-"


# ── _decisions_to_dataframe ────────────────────────────────────────────────


class TestDecisionsToDataframe:
    def test_single_decision(self):
        decisions = [
            DecisionLogEntry(
                decision_id="abc123",
                decision_type="PAPER_BUY",
                timestamp="1700000000000",
                symbol="BTCUSDT",
                strategy_name="ma_crossover",
                timeframe="1h",
                mode="paper",
                approved=True,
                reason="Score OK",
                input_json={},
                output_json={},
                policy_version="1.0",
                strategy_version="1.0",
            )
        ]
        df = _decisions_to_dataframe(decisions)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]["ID"] == "abc123"
        assert df.iloc[0]["Approved"] == "✅"
        assert df.iloc[0]["Symbol"] == "BTCUSDT"

    def test_empty(self):
        df = _decisions_to_dataframe([])
        assert df.empty
        assert len(df) == 0

    def test_rejected_decision(self):
        decisions = [
            DecisionLogEntry(
                decision_id="def456",
                decision_type="RISK_CHECK",
                timestamp="1700000000001",
                symbol="ETHUSDT",
                strategy_name=None,
                timeframe="4h",
                mode="paper",
                approved=False,
                reason="Risk limit exceeded",
                input_json={},
                output_json={"risk_score": 0.9},
                policy_version=None,
                strategy_version=None,
            )
        ]
        df = _decisions_to_dataframe(decisions)
        assert df.iloc[0]["Approved"] == "❌"
        assert df.iloc[0]["Strategy"] == "-"
        assert df.iloc[0]["Policy Version"] == "-"

    def test_timestamp_zero(self):
        decisions = [
            DecisionLogEntry(
                decision_id="ts0",
                decision_type="TEST",
                timestamp="0",
                symbol=None,
                strategy_name=None,
                timeframe=None,
                mode="backtest",
                approved=True,
                reason="test",
                input_json={},
                output_json={},
            )
        ]
        df = _decisions_to_dataframe(decisions)
        assert df.iloc[0]["Datetime"] == "-"


# ── _read_logs / _append_log ────────────────────────────────────────────────


class TestLogs:
    def test_append_read_roundtrip(self, tmp_path: Path):
        log_file = tmp_path / "system_logs.jsonl"
        import app.dashboard.pages.logs as logs_mod

        original = logs_mod.LOGS_FILE
        logs_mod.LOGS_FILE = log_file
        try:
            _append_log("INFO", "core", "startup complete")
            _append_log("WARNING", "risk", "position limit near")
            _append_log("ERROR", "execution", "order failed")
            entries = _read_logs()
            assert len(entries) == 3
            assert entries[0]["level"] == "INFO"
            assert entries[0]["module"] == "core"
            assert entries[0]["message"] == "startup complete"
            assert entries[1]["level"] == "WARNING"
            assert entries[2]["level"] == "ERROR"
        finally:
            logs_mod.LOGS_FILE = original

    def test_read_empty_file(self, tmp_path: Path):
        log_file = tmp_path / "nonexistent.jsonl"
        import app.dashboard.pages.logs as logs_mod

        original = logs_mod.LOGS_FILE
        logs_mod.LOGS_FILE = log_file
        try:
            assert _read_logs() == []
        finally:
            logs_mod.LOGS_FILE = original

    def test_append_creates_parent_directory(self, tmp_path: Path):
        log_file = tmp_path / "subdir" / "deep" / "logs.jsonl"
        import app.dashboard.pages.logs as logs_mod

        original = logs_mod.LOGS_FILE
        logs_mod.LOGS_FILE = log_file
        try:
            _append_log("TRADE", "test", "trade executed")
            assert log_file.exists()
            entries = _read_logs()
            assert len(entries) == 1
        finally:
            logs_mod.LOGS_FILE = original

    def test_invalid_json_line_skipped(self, tmp_path: Path):
        import app.dashboard.pages.logs as logs_mod

        original = logs_mod.LOGS_FILE
        log_file = tmp_path / "system_logs.jsonl"
        logs_mod.LOGS_FILE = log_file
        try:
            log_file.write_text('{"valid": true}\ninvalid json line\n{"also_valid": false}\n')
            entries = _read_logs()
            assert len(entries) == 2
        finally:
            logs_mod.LOGS_FILE = original
