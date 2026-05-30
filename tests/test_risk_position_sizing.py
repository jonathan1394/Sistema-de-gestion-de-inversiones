"""Tests for app/risk/position_sizing.py."""

from app.risk.position_sizing import calculate_position_size


class TestCalculatePositionSize:
    def test_basic_long_position(self):
        result = calculate_position_size(
            capital=1000.0,
            entry_price=50000.0,
            stop_loss=49000.0,
            risk_per_trade_pct=0.01,
            max_position_pct=0.03,
        )
        assert not result.rejected
        assert result.position_size > 0
        assert result.position_value > 0
        assert result.risk_amount == 10.0

    def test_rejects_zero_capital(self):
        result = calculate_position_size(
            capital=0, entry_price=50000, stop_loss=49000
        )
        assert result.rejected
        assert "Capital" in result.rejection_reason

    def test_rejects_negative_capital(self):
        result = calculate_position_size(
            capital=-100, entry_price=50000, stop_loss=49000
        )
        assert result.rejected

    def test_rejects_zero_entry_price(self):
        result = calculate_position_size(
            capital=1000, entry_price=0, stop_loss=49000
        )
        assert result.rejected
        assert "Prices" in result.rejection_reason

    def test_rejects_stop_above_entry_for_long(self):
        result = calculate_position_size(
            capital=1000, entry_price=50000, stop_loss=51000, direction="long"
        )
        assert result.rejected
        assert "below entry" in result.rejection_reason

    def test_rejects_stop_below_entry_for_short(self):
        result = calculate_position_size(
            capital=1000, entry_price=50000, stop_loss=49000, direction="short"
        )
        assert result.rejected
        assert "above entry" in result.rejection_reason

    def test_short_position_calculation(self):
        result = calculate_position_size(
            capital=1000,
            entry_price=50000,
            stop_loss=51000,
            direction="short",
            risk_per_trade_pct=0.01,
        )
        assert not result.rejected
        assert result.position_size > 0

    def test_position_capped_by_max_position_pct(self):
        result = calculate_position_size(
            capital=1000,
            entry_price=100.0,
            stop_loss=99.0,
            risk_per_trade_pct=0.05,
            max_position_pct=0.03,
        )
        assert not result.rejected
        assert result.position_value <= 1000 * 0.03

    def test_result_fields_are_consistent(self):
        result = calculate_position_size(
            capital=1000, entry_price=50000, stop_loss=49000
        )
        assert result.position_value == round(result.position_value, 2)
        assert result.risk_amount == round(result.risk_amount, 2)
