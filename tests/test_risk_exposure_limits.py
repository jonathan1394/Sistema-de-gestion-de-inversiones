"""Tests for app/risk/exposure_limits.py."""

from app.risk.exposure_limits import PortfolioState, check_exposure


class TestCheckExposure:
    def _make_portfolio(self, total=1000, cash=500, positions=None):
        return PortfolioState(
            total_capital=total,
            cash=cash,
            positions=positions or {},
        )

    def test_approves_small_trade(self):
        p = self._make_portfolio(total=1000, cash=900)
        result = check_exposure(p, "BTCUSDT", trade_value=50.0)
        assert result.approved

    def test_rejects_when_asset_exposure_exceeded(self):
        p = self._make_portfolio(
            total=1000, cash=200, positions={"BTCUSDT": 300.0}
        )
        result = check_exposure(
            p, "BTCUSDT", trade_value=60.0, max_asset_pct=0.35
        )
        assert not result.approved
        assert "exceeds max" in result.rejection_reason.lower()

    def test_rejects_when_total_exposure_exceeded(self):
        p = self._make_portfolio(
            total=1000, cash=100, positions={"BTCUSDT": 400.0, "ETHUSDT": 200.0}
        )
        result = check_exposure(
            p, "SOLUSDT", trade_value=200.0, max_asset_pct=0.60, max_total_pct=0.50
        )
        assert not result.approved
        assert "total exposure" in result.rejection_reason.lower()

    def test_rejects_when_altcoin_exposure_exceeded(self):
        p = self._make_portfolio(
            total=1000,
            cash=540,
            positions={"ETHUSDT": 200.0, "SOLUSDT": 200.0},
        )
        result = check_exposure(
            p, "SOLUSDT", trade_value=60.0,
            max_total_pct=0.60,
            max_altcoin_pct=0.40,
            altcoin_symbols={"ETHUSDT", "SOLUSDT"},
        )
        assert not result.approved
        assert "altcoin" in result.rejection_reason.lower()

    def test_rejects_zero_capital(self):
        p = self._make_portfolio(total=0, cash=0)
        result = check_exposure(p, "BTCUSDT", trade_value=100.0)
        assert not result.approved
        assert "capital" in result.rejection_reason.lower()

    def test_approved_values_are_consistent(self):
        p = self._make_portfolio(total=1000, cash=600, positions={"BTCUSDT": 200.0})
        result = check_exposure(p, "BTCUSDT", trade_value=100.0)
        assert result.approved
        assert abs(result.asset_exposure_after_pct - round(result.asset_exposure_after_pct, 2)) < 0.01
        assert abs(result.total_exposure_after_pct - round(result.total_exposure_after_pct, 2)) < 0.01

    def test_short_position_negative_value(self):
        p = self._make_portfolio(
            total=1000, cash=1500, positions={"BTCUSDT": -500.0}
        )
        result = check_exposure(
            p, "ETHUSDT", trade_value=100.0,
            max_asset_pct=0.50, max_total_pct=0.60,
        )
        assert result.approved
        assert result.current_total_exposure_pct == 50.0

    def test_exposure_with_short_uses_absolute_values(self):
        p = self._make_portfolio(
            total=2000, cash=3000,
            positions={"BTCUSDT": -1000.0, "ETHUSDT": 500.0},
        )
        result = check_exposure(
            p, "SOLUSDT", trade_value=600.0,
            max_asset_pct=0.70, max_total_pct=0.50,
        )
        assert not result.approved
        assert "total exposure" in result.rejection_reason.lower()
