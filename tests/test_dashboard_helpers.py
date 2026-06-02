"""Tests for dashboard helper functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.dashboard.helpers import (
    add_snapshot,
    candles_to_dataframe,
    get_current_price,
    get_portfolio_value,
    update_portfolio_prices,
)
from app.data.market_data import Candle


def make_candle(open_time: int, open_: float, high: float, low: float, close: float) -> Candle:
    return Candle(
        symbol="BTCUSDT",
        interval="1h",
        open_time=open_time,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=100.0,
        close_time=open_time + 3_600_000,
        quote_asset_volume=0.0,
        number_of_trades=0,
        taker_buy_base_asset_volume=0.0,
        taker_buy_quote_asset_volume=0.0,
    )


class TestCandlesToDataFrame:
    def test_empty_list(self) -> None:
        df = candles_to_dataframe([])
        assert df.empty

    def test_single_candle(self) -> None:
        candles = [make_candle(1_700_000_000_000, 100.0, 110.0, 90.0, 105.0)]
        df = candles_to_dataframe(candles)
        assert isinstance(df, pd.DataFrame)
        assert df.iloc[0]["open"] == 100.0
        assert df.iloc[0]["high"] == 110.0
        assert df.iloc[0]["low"] == 90.0
        assert df.iloc[0]["close"] == 105.0
        assert df.iloc[0]["volume"] == 100.0
        assert df.iloc[0]["timestamp"] == pd.Timestamp("2023-11-14 22:13:20+0000")

    def test_multiple_candles(self) -> None:
        candles = [
            make_candle(1_700_000_000_000, 100.0, 110.0, 90.0, 105.0),
            make_candle(1_700_003_600_000, 105.0, 115.0, 95.0, 110.0),
        ]
        df = candles_to_dataframe(candles)
        assert len(df) == 2
        assert list(df["close"]) == [105.0, 110.0]


class TestGetCurrentPrice:
    def test_returns_close_from_1h(self) -> None:
        conn = MagicMock()
        with patch("app.dashboard.helpers.get_candles") as mock_get:
            mock_get.return_value = [MagicMock(close=50000.0)]
            result = get_current_price(conn, "BTCUSDT")
            assert result == 50000.0
            mock_get.assert_called_once_with(
                connection=conn, symbol="BTCUSDT", interval="1h", limit=1, desc=True
            )

    def test_falls_back_to_4h(self) -> None:
        conn = MagicMock()
        with patch("app.dashboard.helpers.get_candles") as mock_get:
            mock_get.side_effect = [[], [MagicMock(close=49000.0)]]
            result = get_current_price(conn, "BTCUSDT")
            assert result == 49000.0

    def test_falls_back_to_1d(self) -> None:
        conn = MagicMock()
        with patch("app.dashboard.helpers.get_candles") as mock_get:
            mock_get.side_effect = [[], [], [MagicMock(close=48000.0)]]
            result = get_current_price(conn, "BTCUSDT")
            assert result == 48000.0

    def test_returns_none_when_no_data(self) -> None:
        conn = MagicMock()
        with patch("app.dashboard.helpers.get_candles") as mock_get:
            mock_get.return_value = []
            result = get_current_price(conn, "BTCUSDT")
            assert result is None


class TestGetPortfolioValue:
    def test_only_cash(self) -> None:
        state = MagicMock(portfolio_cash=1000.0, portfolio_positions={})
        assert get_portfolio_value(state) == 1000.0

    def test_cash_with_positions(self) -> None:
        state = MagicMock(
            portfolio_cash=500.0,
            portfolio_positions={
                "BTCUSDT": {"quantity": 0.5, "current_price": 60000.0},
                "ETHUSDT": {"quantity": 2.0, "current_price": 3000.0},
            },
        )
        expected = 500.0 + (0.5 * 60000.0) + (2.0 * 3000.0)
        assert get_portfolio_value(state) == expected

    def test_handles_non_numeric_gracefully(self) -> None:
        state = MagicMock(
            portfolio_cash=100.0,
            portfolio_positions={
                "BAD": {"quantity": "abc", "current_price": 10.0},
            },
        )
        assert get_portfolio_value(state) == 100.0

    def test_defaults_when_missing(self) -> None:
        state = MagicMock()
        del state.portfolio_cash
        del state.portfolio_positions
        assert get_portfolio_value(state) == 0.0


class TestUpdatePortfolioPrices:
    def test_updates_existing_positions(self) -> None:
        state = MagicMock(
            portfolio_positions={
                "BTCUSDT": {"entry_price": 50000.0, "quantity": 1.0},
            }
        )
        update_portfolio_prices(state, {"BTCUSDT": 55000.0})
        pos = state.portfolio_positions["BTCUSDT"]
        assert pos["current_price"] == 55000.0
        assert pos["unrealized_pnl"] == 5000.0
        assert pos["unrealized_pnl_pct"] == pytest.approx(10.0)

    def test_skips_unknown_symbols(self) -> None:
        state = MagicMock(portfolio_positions={"BTCUSDT": {}})
        update_portfolio_prices(state, {"ETHUSDT": 2000.0})
        # Should not raise and only update known symbols
        assert "current_price" not in state.portfolio_positions.get("ETHUSDT", {})

    def test_handles_zero_entry(self) -> None:
        state = MagicMock(
            portfolio_positions={
                "BTCUSDT": {"entry_price": 0.0, "quantity": 1.0},
            }
        )
        update_portfolio_prices(state, {"BTCUSDT": 100.0})
        assert state.portfolio_positions["BTCUSDT"]["unrealized_pnl_pct"] == 0.0


class TestAddSnapshot:
    def test_first_snapshot(self) -> None:
        state = MagicMock(
            portfolio_cash=1000.0,
            portfolio_positions={},
            portfolio_peak=0.0,
            portfolio_snapshots=[],
        )
        add_snapshot(state)
        assert len(state.portfolio_snapshots) == 1
        snap = state.portfolio_snapshots[0]
        assert snap["total_value"] == 1000.0
        assert snap["cash"] == 1000.0
        assert snap["drawdown_pct"] == 0.0
        assert "timestamp" in snap

    def test_tracks_peak(self) -> None:
        state = MagicMock(
            portfolio_cash=500.0,
            portfolio_positions={"BTCUSDT": {"quantity": 0.01, "current_price": 60000.0}},
            portfolio_peak=0.0,
            portfolio_snapshots=[],
        )
        add_snapshot(state)
        assert state.portfolio_peak == 500.0 + 0.01 * 60000.0

    def test_drawdown_calculation(self) -> None:
        state = MagicMock(
            portfolio_cash=800.0,
            portfolio_positions={},
            portfolio_peak=1000.0,
            portfolio_snapshots=[],
        )
        add_snapshot(state)
        snap = state.portfolio_snapshots[0]
        assert snap["drawdown_pct"] == pytest.approx(20.0)  # (1000-800)/1000 * 100

    def test_appends_multiple_snapshots(self) -> None:
        state = MagicMock(
            portfolio_cash=1000.0,
            portfolio_positions={},
            portfolio_peak=1000.0,
            portfolio_snapshots=[],
        )
        add_snapshot(state)
        add_snapshot(state)
        assert len(state.portfolio_snapshots) == 2
