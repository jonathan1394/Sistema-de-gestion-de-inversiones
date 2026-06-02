"""Tests for app/risk/trailing_stop.py."""

from app.risk.trailing_stop import TrailingStop, TrailingStopConfig


class TestTrailingStop:
    def test_long_not_active_below_activation(self):
        cfg = TrailingStopConfig(activation_pct=0.02, trail_pct=0.03)
        ts = TrailingStop(cfg, entry_price=100, direction="long")
        result = ts.update(current_price=101, high=101)
        assert ts.state.active is False
        assert result == 0.0

    def test_long_activates_when_price_reaches_activation(self):
        cfg = TrailingStopConfig(activation_pct=0.02, trail_pct=0.03)
        ts = TrailingStop(cfg, entry_price=100, direction="long")
        result = ts.update(current_price=102.5, high=102.5)
        assert ts.state.active is True
        assert result > 0

    def test_long_trailing_stop_moves_up(self):
        cfg = TrailingStopConfig(activation_pct=0.01, trail_pct=0.02)
        ts = TrailingStop(cfg, entry_price=100, direction="long")
        ts.update(current_price=101, high=101)
        assert ts.state.active
        stop1 = ts.current_stop
        ts.update(current_price=105, high=105)
        stop2 = ts.current_stop
        assert stop2 >= stop1

    def test_long_stop_never_goes_down(self):
        cfg = TrailingStopConfig(activation_pct=0.01, trail_pct=0.02)
        ts = TrailingStop(cfg, entry_price=100, direction="long")
        ts.update(current_price=105, high=105)
        stop_high = ts.current_stop
        ts.update(current_price=103, high=105)
        assert ts.current_stop == stop_high

    def test_short_not_active_above_activation(self):
        cfg = TrailingStopConfig(activation_pct=0.02, trail_pct=0.03)
        ts = TrailingStop(cfg, entry_price=100, direction="short")
        result = ts.update(current_price=99, low=99)
        assert ts.state.active is False
        assert result == 0.0

    def test_short_activates_when_price_drops(self):
        cfg = TrailingStopConfig(activation_pct=0.02, trail_pct=0.03)
        ts = TrailingStop(cfg, entry_price=100, direction="short")
        result = ts.update(current_price=97.5, low=97.5)
        assert ts.state.active is True
        assert result > 0

    def test_short_trailing_stop_moves_down(self):
        cfg = TrailingStopConfig(activation_pct=0.01, trail_pct=0.02)
        ts = TrailingStop(cfg, entry_price=100, direction="short")
        ts.update(current_price=98, low=98)
        stop1 = ts.current_stop
        ts.update(current_price=95, low=95)
        stop2 = ts.current_stop
        assert stop2 <= stop1

    def test_short_stop_never_goes_up(self):
        cfg = TrailingStopConfig(activation_pct=0.01, trail_pct=0.02)
        ts = TrailingStop(cfg, entry_price=100, direction="short")
        ts.update(current_price=95, low=95)
        stop_low = ts.current_stop
        ts.update(current_price=97, low=95)
        assert ts.current_stop == stop_low

    def test_with_initial_stop(self):
        cfg = TrailingStopConfig(activation_pct=0.01, trail_pct=0.02)
        ts = TrailingStop(cfg, entry_price=100, direction="long", initial_stop=98.0)
        assert ts.current_stop == 98.0
        ts.update(current_price=102, high=102)
        assert ts.state.active
        assert ts.current_stop >= 98.0

    def test_with_atr_based_trailing(self):
        cfg = TrailingStopConfig(
            activation_pct=0.01, trail_pct=0.02,
            use_atr=True, atr_multiplier=2.0,
        )
        ts = TrailingStop(cfg, entry_price=100, direction="long")
        ts.update(current_price=102, high=102, atr_value=1.5)
        assert ts.state.active
        assert ts.current_stop > 0

    def test_zero_trail_pct(self):
        cfg = TrailingStopConfig(activation_pct=0.0, trail_pct=0.0)
        ts = TrailingStop(cfg, entry_price=100, direction="long")
        result = ts.update(current_price=100, high=100)
        assert result >= 0

    def test_high_updates_peak(self):
        cfg = TrailingStopConfig(activation_pct=0.01, trail_pct=0.02)
        ts = TrailingStop(cfg, entry_price=100, direction="long")
        ts.update(current_price=101, high=101)
        ts.update(current_price=103, high=105)
        assert ts.state.peak_price == 105
