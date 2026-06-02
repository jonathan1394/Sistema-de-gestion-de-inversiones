"""Tests for app/paper_trading/virtual_portfolio.py — including short support."""

from datetime import datetime, timezone

import pytest

from app.paper_trading.virtual_portfolio import VirtualPortfolio


def _ts() -> datetime:
    return datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)


class TestVirtualPortfolio:
    def test_initial_state(self):
        p = VirtualPortfolio(1000)
        assert p.cash == 1000
        assert p.total_value == 1000
        assert p.total_pnl == 0.0
        assert p.trade_count == 0

    def test_buy_reduces_cash(self):
        p = VirtualPortfolio(1000)
        assert p.buy("BTCUSDT", 1, 500, _ts())
        assert p.cash == 500
        assert p.total_value == 1000
        assert p.has_position("BTCUSDT")

    def test_sell_restores_cash(self):
        p = VirtualPortfolio(1000)
        p.buy("BTCUSDT", 1, 500, _ts())
        pnl = p.sell("BTCUSDT", 1, 550, _ts())
        assert pnl == 50.0
        assert p.cash == 1050
        assert not p.has_position("BTCUSDT")

    def test_short_sell_increases_cash(self):
        p = VirtualPortfolio(1000)
        assert p.short_sell("BTCUSDT", 2, 500, _ts())
        assert p.cash == 2000
        assert p.total_value == 1000
        assert p.has_position("BTCUSDT")
        assert p.is_short("BTCUSDT")

    def test_cover_short_decreases_cash(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 2, 500, _ts())
        pnl = p.cover_short("BTCUSDT", 2, 450, _ts())
        assert pnl == 100.0
        assert p.cash == 1100
        assert not p.has_position("BTCUSDT")

    def test_short_pnl_loss(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 2, 500, _ts())
        pnl = p.cover_short("BTCUSDT", 2, 550, _ts())
        assert pnl == -100.0
        assert p.cash == 900
        assert not p.has_position("BTCUSDT")

    def test_short_update_prices_unrealized_pnl(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 2, 500, _ts())
        p.update_prices({"BTCUSDT": 450}, _ts())
        pos = p.get_position("BTCUSDT")
        assert pos is not None
        assert pos.unrealized_pnl == 100.0
        assert pos.unrealized_pnl_pct == pytest.approx(10.0)

    def test_short_update_prices_unrealized_loss(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 2, 500, _ts())
        p.update_prices({"BTCUSDT": 550}, _ts())
        pos = p.get_position("BTCUSDT")
        assert pos is not None
        assert pos.unrealized_pnl == -100.0
        assert pos.unrealized_pnl_pct == pytest.approx(-10.0)

    def test_has_position_returns_true_for_short(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 1, 500, _ts())
        assert p.has_position("BTCUSDT")

    def test_is_short_true_when_short(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 1, 500, _ts())
        assert p.is_short("BTCUSDT")

    def test_is_short_false_when_long(self):
        p = VirtualPortfolio(1000)
        p.buy("BTCUSDT", 1, 500, _ts())
        assert not p.is_short("BTCUSDT")

    def test_close_position_for_short(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 2, 500, _ts())
        pnl = p.close_position("BTCUSDT", 450)
        assert pnl == 100.0
        assert not p.has_position("BTCUSDT")

    def test_close_position_for_long(self):
        p = VirtualPortfolio(1000)
        p.buy("BTCUSDT", 1, 500, _ts())
        pnl = p.close_position("BTCUSDT", 550)
        assert pnl == 50.0
        assert not p.has_position("BTCUSDT")

    def test_gross_exposure_with_mixed_positions(self):
        p = VirtualPortfolio(1000)
        p.buy("BTCUSDT", 1, 400, _ts())
        p.short_sell("ETHUSDT", 2, 300, _ts())
        p.update_prices({"BTCUSDT": 400, "ETHUSDT": 300}, _ts())
        assert p.gross_exposure == 1000

    def test_exposure_pct_with_shorts(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 2, 500, _ts())
        assert p.exposure_pct > 0

    def test_partial_cover_short(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 3, 500, _ts())
        pnl = p.cover_short("BTCUSDT", 1, 480, _ts())
        assert pnl == 20.0
        assert p.has_position("BTCUSDT")
        assert p.is_short("BTCUSDT")

    def test_buy_insufficient_cash(self):
        p = VirtualPortfolio(100)
        assert not p.buy("BTCUSDT", 1, 500, _ts())

    def test_short_sell_invalid_quantity(self):
        p = VirtualPortfolio(1000)
        assert not p.short_sell("BTCUSDT", 0, 500, _ts())
        assert not p.short_sell("BTCUSDT", -1, 500, _ts())

    def test_sell_nonexistent_position(self):
        p = VirtualPortfolio(1000)
        assert p.sell("BTCUSDT", 1, 500, _ts()) is None

    def test_cover_nonexistent_short(self):
        p = VirtualPortfolio(1000)
        assert p.cover_short("BTCUSDT", 1, 500, _ts()) is None

    def test_reset_clears_everything(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 2, 500, _ts())
        p.reset()
        assert p.cash == 1000
        assert not p.has_position("BTCUSDT")
        assert p.trade_count == 0

    def test_total_value_with_short_profit(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 2, 500, _ts())
        p.update_prices({"BTCUSDT": 400}, _ts())
        assert p.total_value == 1200

    def test_total_value_with_short_loss(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 2, 500, _ts())
        p.update_prices({"BTCUSDT": 600}, _ts())
        assert p.total_value == 800

    def test_trade_history_includes_short_operations(self):
        p = VirtualPortfolio(1000)
        p.short_sell("BTCUSDT", 2, 500, _ts())
        p.cover_short("BTCUSDT", 2, 450, _ts())
        history = p.get_trade_history()
        assert len(history) == 2
        assert history[0]["type"] == "short_sell"
        assert history[1]["type"] == "cover_short"
