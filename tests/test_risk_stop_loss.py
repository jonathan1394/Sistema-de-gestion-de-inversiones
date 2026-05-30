"""Tests for app/risk/stop_loss.py."""

from app.risk.stop_loss import fixed_percentage, atr_based


class TestFixedPercentage:
    def test_long_stop_below_entry(self):
        result = fixed_percentage(entry_price=100.0, stop_loss_pct=0.02, direction="long")
        assert not result.rejected
        assert result.stop_price < 100.0
        assert result.distance_pct == 2.0
        assert result.method == "fixed_pct"

    def test_short_stop_above_entry(self):
        result = fixed_percentage(entry_price=100.0, stop_loss_pct=0.02, direction="short")
        assert not result.rejected
        assert result.stop_price > 100.0

    def test_rejects_below_min(self):
        result = fixed_percentage(
            entry_price=100.0, stop_loss_pct=0.001, min_stop_pct=0.005
        )
        assert result.rejected
        assert "minimum" in result.rejection_reason.lower()

    def test_rejects_above_max(self):
        result = fixed_percentage(
            entry_price=100.0, stop_loss_pct=0.15, max_stop_pct=0.10
        )
        assert result.rejected
        assert "maximum" in result.rejection_reason.lower()

    def test_stop_price_is_rounded(self):
        result = fixed_percentage(entry_price=33333.33, stop_loss_pct=0.03)
        assert result.stop_price == round(result.stop_price, 2)


class TestAtrBased:
    def test_long_stop(self):
        result = atr_based(entry_price=100.0, atr_value=2.0, atr_multiplier=2.0, direction="long")
        assert not result.rejected
        assert result.stop_price < 100.0
        assert result.method == "atr"

    def test_short_stop(self):
        result = atr_based(entry_price=100.0, atr_value=2.0, direction="short")
        assert not result.rejected
        assert result.stop_price > 100.0

    def test_rejects_zero_atr(self):
        result = atr_based(entry_price=100.0, atr_value=0)
        assert result.rejected
        assert "ATR" in result.rejection_reason

    def test_clamps_to_min_stop(self):
        result = atr_based(
            entry_price=100.0, atr_value=0.01, atr_multiplier=1.0,
            min_stop_pct=0.005, max_stop_pct=0.10,
        )
        assert not result.rejected
        assert result.distance_pct >= 0.5

    def test_clamps_to_max_stop(self):
        result = atr_based(
            entry_price=100.0, atr_value=50.0, atr_multiplier=1.0,
            min_stop_pct=0.005, max_stop_pct=0.10,
        )
        assert not result.rejected
        assert result.distance_pct <= 10.0
