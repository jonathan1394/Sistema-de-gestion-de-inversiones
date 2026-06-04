"""Property-based tests for risk modules using hypothesis.

These tests enforce invariants that must always hold regardless of
valid input combinations. Each test generates random valid inputs and
checks that the output respects core business rules.
"""

from __future__ import annotations

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.risk.circuit_breakers import CircuitBreakers
from app.risk.exposure_limits import PortfolioState, check_exposure
from app.risk.position_sizing import calculate_position_size
from app.risk.stop_loss import atr_based, fixed_percentage, take_profit_dynamic

# ── Common strategies ─────────────────────────────────────────────────────────

positive_floats = st.floats(min_value=0.001, max_value=1e9, allow_nan=False, allow_infinity=False)
pct_floats = st.floats(min_value=0.001, max_value=0.50, allow_nan=False, allow_infinity=False)
small_pct = st.floats(min_value=0.001, max_value=0.20, allow_nan=False, allow_infinity=False)


# ── 1. Position Sizing ───────────────────────────────────────────────────────


class TestPositionSizingProperties:
    @given(
        capital=positive_floats,
        entry=positive_floats,
        stop_discount=st.floats(min_value=0.001, max_value=0.99),
        risk_pct=small_pct,
        max_pos_pct=small_pct,
    )
    @settings(max_examples=200)
    def test_long_position_value_bounded_by_max_pct(
        self,
        capital: float,
        entry: float,
        stop_discount: float,
        risk_pct: float,
        max_pos_pct: float,
    ):
        """For a valid long entry, position_value never exceeds capital * max_position_pct (after rounding cap)."""
        stop = entry * (1 - stop_discount)
        result = calculate_position_size(
            capital, entry, stop, risk_pct, max_pos_pct, direction="long"
        )
        assume(not result.rejected)
        assert result.position_value <= round(capital * max_pos_pct, 2) * 1.001

    @given(
        capital=positive_floats,
        entry=positive_floats,
        stop_premium=st.floats(min_value=0.001, max_value=0.99),
        risk_pct=small_pct,
        max_pos_pct=small_pct,
    )
    @settings(max_examples=200)
    def test_short_position_value_bounded_by_max_pct(
        self, capital: float, entry: float, stop_premium: float, risk_pct: float, max_pos_pct: float
    ):
        """For a valid short entry, position_value never exceeds capital * max_position_pct (after rounding cap)."""
        stop = entry * (1 + stop_premium)
        result = calculate_position_size(
            capital, entry, stop, risk_pct, max_pos_pct, direction="short"
        )
        assume(not result.rejected)
        assert result.position_value <= round(capital * max_pos_pct, 2) * 1.001

    @given(
        capital=positive_floats,
        entry=positive_floats,
        stop_discount=st.floats(min_value=0.001, max_value=0.99),
        risk_pct=small_pct,
        max_pos_pct=small_pct,
    )
    @settings(max_examples=200)
    def test_risk_amount_equals_capital_times_risk_pct(
        self,
        capital: float,
        entry: float,
        stop_discount: float,
        risk_pct: float,
        max_pos_pct: float,
    ):
        """Risk amount must equal capital * risk_per_trade_pct when accepted."""
        stop = entry * (1 - stop_discount)
        result = calculate_position_size(
            capital, entry, stop, risk_pct, max_pos_pct, direction="long"
        )
        assume(not result.rejected)
        assert abs(result.risk_amount - capital * risk_pct) < 0.02

    @given(
        capital=positive_floats,
        entry=positive_floats,
        stop_discount=st.floats(min_value=0.001, max_value=0.99),
        risk_pct=small_pct,
        max_pos_pct=small_pct,
    )
    @settings(max_examples=200)
    def test_price_times_size_equals_value(
        self,
        capital: float,
        entry: float,
        stop_discount: float,
        risk_pct: float,
        max_pos_pct: float,
    ):
        """position_size * entry_price ≈ position_value (adaptive tolerance for position_size rounding)."""
        stop = entry * (1 - stop_discount)
        result = calculate_position_size(
            capital, entry, stop, risk_pct, max_pos_pct, direction="long"
        )
        assume(not result.rejected)
        expected_value = result.position_size * entry
        # position_size is rounded to 8dp, so max error = 0.5 * 1e-8 * entry + 0.005 (pos_value rounding)
        tol = 0.02 + 5e-9 * entry
        assert abs(result.position_value - expected_value) < tol

    @given(
        capital=st.floats(min_value=-1e6, max_value=0, allow_nan=False, allow_infinity=False),
        entry=positive_floats,
        stop_discount=st.floats(min_value=0.001, max_value=0.99),
    )
    @settings(max_examples=50)
    def test_rejects_non_positive_capital(self, capital: float, entry: float, stop_discount: float):
        """Capital <= 0 must be rejected."""
        stop = entry * (1 - stop_discount)
        result = calculate_position_size(capital, entry, stop)
        assert result.rejected

    @given(
        capital=positive_floats,
        entry=positive_floats,
    )
    @settings(max_examples=50)
    def test_rejects_stop_above_entry_for_long(self, capital: float, entry: float):
        """Long: stop_loss >= entry_price must be rejected."""
        stop = entry * 1.1
        result = calculate_position_size(capital, entry, stop, direction="long")
        assert result.rejected
        assert "Stop-loss must be below entry for long" in result.rejection_reason

    @given(
        capital=positive_floats,
        entry=positive_floats,
    )
    @settings(max_examples=50)
    def test_rejects_stop_below_entry_for_short(self, capital: float, entry: float):
        """Short: stop_loss <= entry_price must be rejected."""
        stop = entry * 0.9
        result = calculate_position_size(capital, entry, stop, direction="short")
        assert result.rejected
        assert "Stop-loss must be above entry for short" in result.rejection_reason

    @given(
        capital=positive_floats,
        entry=st.just(0.0),
        stop_discount=st.floats(min_value=0.001, max_value=0.99),
    )
    @settings(max_examples=10)
    def test_rejects_zero_entry_price(self, capital: float, entry: float, stop_discount: float):
        """entry_price == 0 must be rejected."""
        stop = 0.001  # > 0 but entry is 0
        result = calculate_position_size(capital, entry, stop)
        assert result.rejected
        assert "Prices must be positive" in result.rejection_reason

    @given(
        capital=positive_floats,
        entry=positive_floats,
        stop_discount=st.floats(min_value=0.001, max_value=0.99),
        risk_pct=small_pct,
        max_pos_pct=small_pct,
    )
    @settings(max_examples=200)
    def test_accepted_result_has_non_negative_values(
        self,
        capital: float,
        entry: float,
        stop_discount: float,
        risk_pct: float,
        max_pos_pct: float,
    ):
        """Accepted positions have non-negative size, value, risk."""
        stop = entry * (1 - stop_discount)
        result = calculate_position_size(
            capital, entry, stop, risk_pct, max_pos_pct, direction="long"
        )
        assume(not result.rejected)
        assert result.position_size >= 0
        assert result.position_value >= 0
        assert result.risk_amount >= 0


# ── 2. Stop Loss (Fixed Percentage) ──────────────────────────────────────────


class TestStopLossFixedProperties:
    @given(
        entry=positive_floats,
        sl_pct=small_pct,
        min_pct=st.floats(min_value=0.001, max_value=0.005),
        max_pct=st.floats(min_value=0.10, max_value=0.20),
    )
    @settings(max_examples=100)
    def test_long_stop_below_entry(
        self, entry: float, sl_pct: float, min_pct: float, max_pct: float
    ):
        """Long: stop_price is always below entry_price."""
        result = fixed_percentage(
            entry, sl_pct, direction="long", min_stop_pct=min_pct, max_stop_pct=max_pct
        )
        assume(not result.rejected)
        assert result.stop_price < entry

    @given(
        entry=positive_floats,
        sl_pct=small_pct,
        min_pct=st.floats(min_value=0.001, max_value=0.005),
        max_pct=st.floats(min_value=0.10, max_value=0.20),
    )
    @settings(max_examples=100)
    def test_short_stop_above_entry(
        self, entry: float, sl_pct: float, min_pct: float, max_pct: float
    ):
        """Short: stop_price is always above entry_price."""
        result = fixed_percentage(
            entry, sl_pct, direction="short", min_stop_pct=min_pct, max_stop_pct=max_pct
        )
        assume(not result.rejected)
        assert result.stop_price > entry

    @given(
        entry=positive_floats,
        sl_pct=st.floats(min_value=0.001, max_value=0.009, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_rejects_below_min(self, entry: float, sl_pct: float):
        """stop_loss_pct < min_stop_pct must be rejected."""
        result = fixed_percentage(entry, sl_pct, min_stop_pct=0.01)
        assert result.rejected
        assert "below minimum" in result.rejection_reason

    @given(
        entry=positive_floats,
        sl_pct=st.floats(min_value=0.21, max_value=0.50, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_rejects_above_max(self, entry: float, sl_pct: float):
        """stop_loss_pct > max_stop_pct must be rejected."""
        result = fixed_percentage(entry, sl_pct, max_stop_pct=0.20)
        assert result.rejected
        assert "exceeds maximum" in result.rejection_reason

    @given(
        entry=positive_floats,
        sl_pct=small_pct,
        min_pct=st.floats(min_value=0.001, max_value=0.005),
        max_pct=st.floats(min_value=0.10, max_value=0.20),
    )
    @settings(max_examples=100)
    def test_distance_pct_matches_input(
        self, entry: float, sl_pct: float, min_pct: float, max_pct: float
    ):
        """When accepted, distance_pct equals the input stop_loss_pct."""
        result = fixed_percentage(
            entry, sl_pct, direction="long", min_stop_pct=min_pct, max_stop_pct=max_pct
        )
        assume(not result.rejected)
        assert abs(result.distance_pct - sl_pct) < 0.001


# ── 3. Stop Loss (ATR-based) ────────────────────────────────────────────────


class TestStopLossAtrProperties:
    @given(
        entry=positive_floats,
        atr=st.floats(min_value=0.001, max_value=1000, allow_nan=False, allow_infinity=False),
        mult=st.floats(min_value=0.5, max_value=5.0, allow_nan=False),
        min_pct=st.floats(min_value=0.001, max_value=0.005),
        max_pct=st.floats(min_value=0.10, max_value=0.20),
    )
    @settings(max_examples=200)
    def test_distance_pct_within_bounds(
        self, entry: float, atr: float, mult: float, min_pct: float, max_pct: float
    ):
        """ATR stop distance_pct is always within [min_stop_pct, max_stop_pct]."""
        result = atr_based(
            entry, atr, mult, direction="long", min_stop_pct=min_pct, max_stop_pct=max_pct
        )
        assume(not result.rejected)
        assert min_pct - 0.001 <= result.distance_pct <= max_pct + 0.001

    @given(
        entry=positive_floats,
        atr=st.floats(min_value=-1000, max_value=0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_rejects_non_positive_atr(self, entry: float, atr: float):
        """atr_value <= 0 must be rejected."""
        result = atr_based(entry, atr)
        assert result.rejected
        assert "ATR must be positive" in result.rejection_reason

    @given(
        entry=positive_floats,
        atr=positive_floats,
        mult=st.floats(min_value=0.5, max_value=5.0, allow_nan=False),
        min_pct=st.floats(min_value=0.001, max_value=0.005),
        max_pct=st.floats(min_value=0.10, max_value=0.20),
    )
    @settings(max_examples=100)
    def test_long_stop_below_entry(
        self, entry: float, atr: float, mult: float, min_pct: float, max_pct: float
    ):
        """ATR long: stop_price is always below entry_price."""
        result = atr_based(
            entry, atr, mult, direction="long", min_stop_pct=min_pct, max_stop_pct=max_pct
        )
        assume(not result.rejected)
        assert result.stop_price < entry

    @given(
        entry=positive_floats,
        atr=positive_floats,
        mult=st.floats(min_value=0.5, max_value=5.0, allow_nan=False),
        min_pct=st.floats(min_value=0.001, max_value=0.005),
        max_pct=st.floats(min_value=0.10, max_value=0.20),
    )
    @settings(max_examples=100)
    def test_short_stop_above_entry(
        self, entry: float, atr: float, mult: float, min_pct: float, max_pct: float
    ):
        """ATR short: stop_price is always above entry_price."""
        result = atr_based(
            entry, atr, mult, direction="short", min_stop_pct=min_pct, max_stop_pct=max_pct
        )
        assume(not result.rejected)
        assert result.stop_price > entry


# ── 4. Take Profit Dynamic ──────────────────────────────────────────────────


class TestTakeProfitDynamicProperties:
    @given(
        entry=positive_floats,
        atr=st.floats(min_value=0.001, max_value=1000, allow_nan=False),
        mult=st.floats(min_value=1.0, max_value=6.0, allow_nan=False),
        min_tp=st.floats(min_value=0.005, max_value=0.01),
        max_tp=st.floats(min_value=0.15, max_value=0.25),
    )
    @settings(max_examples=200)
    def test_distance_pct_within_bounds(
        self, entry: float, atr: float, mult: float, min_tp: float, max_tp: float
    ):
        """TP distance_pct is always within [min_tp_pct, max_tp_pct]."""
        result = take_profit_dynamic(
            entry, atr, mult, direction="long", min_tp_pct=min_tp, max_tp_pct=max_tp
        )
        assume(not result.rejected)
        assert min_tp - 0.001 <= result.distance_pct <= max_tp + 0.001

    @given(
        entry=positive_floats,
        atr=st.floats(min_value=-1000, max_value=0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_rejects_non_positive_atr(self, entry: float, atr: float):
        """atr_value <= 0 must be rejected."""
        result = take_profit_dynamic(entry, atr)
        assert result.rejected
        assert "ATR must be positive" in result.rejection_reason

    @given(
        entry=positive_floats,
        atr=positive_floats,
        mult=st.floats(min_value=1.0, max_value=6.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_long_tp_above_entry(self, entry: float, atr: float, mult: float):
        """Long TP: stop_price is always above entry_price."""
        result = take_profit_dynamic(entry, atr, mult, direction="long")
        assume(not result.rejected)
        assert result.stop_price > entry

    @given(
        entry=positive_floats,
        atr=positive_floats,
        mult=st.floats(min_value=1.0, max_value=6.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_short_tp_below_entry(self, entry: float, atr: float, mult: float):
        """Short TP: stop_price is always below entry_price."""
        result = take_profit_dynamic(entry, atr, mult, direction="short")
        assume(not result.rejected)
        assert result.stop_price < entry


# ── 5. Exposure Limits ──────────────────────────────────────────────────────


class TestExposureLimitsProperties:
    @given(
        capital=positive_floats,
        trade_value=st.floats(min_value=0.001, max_value=1e6, allow_nan=False),
        max_asset=st.floats(min_value=0.05, max_value=0.50, allow_nan=False),
        max_total=st.floats(min_value=0.10, max_value=0.70, allow_nan=False),
    )
    @settings(max_examples=200)
    def test_approved_exposure_stays_within_limits(
        self, capital: float, trade_value: float, max_asset: float, max_total: float
    ):
        """When approved, exposure after trade never exceeds limits."""
        portfolio = PortfolioState(total_capital=capital, cash=capital)
        result = check_exposure(
            portfolio=portfolio,
            symbol="BTCUSDT",
            trade_value=trade_value,
            max_asset_pct=max_asset,
            max_total_pct=max_total,
        )
        assume(result.approved)
        assert result.asset_exposure_after_pct <= max_asset * 100 * 1.01
        assert result.total_exposure_after_pct <= max_total * 100 * 1.01

    @given(
        capital=st.floats(min_value=-1e6, max_value=0, allow_nan=False, allow_infinity=False),
        trade_value=positive_floats,
    )
    @settings(max_examples=50)
    def test_rejects_non_positive_capital(self, capital: float, trade_value: float):
        """total_capital <= 0 must be rejected."""
        portfolio = PortfolioState(total_capital=capital)
        result = check_exposure(portfolio, "BTCUSDT", trade_value)
        assert not result.approved
        assert "positive" in result.rejection_reason.lower()

    @given(
        capital=st.floats(min_value=100, max_value=1e6, allow_nan=False),
        existing_pct=st.floats(min_value=0.05, max_value=0.20, allow_nan=False),
        trade_pct=st.floats(min_value=0.05, max_value=0.20, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_rejects_when_asset_exposure_exceeded(
        self, capital: float, existing_pct: float, trade_pct: float
    ):
        """If asset_after > max_asset_pct, must be rejected."""
        max_asset = 0.10
        # With both >= 5% and min sum = 10%, but using assume to guarantee > 10%
        assume(existing_pct + trade_pct > max_asset)
        existing_value = capital * existing_pct
        trade_value = capital * trade_pct
        portfolio = PortfolioState(total_capital=capital, positions={"SYM": existing_value})
        result = check_exposure(portfolio, "SYM", trade_value, max_asset_pct=max_asset)
        assert not result.approved

    @given(
        capital=st.floats(min_value=100, max_value=1e6, allow_nan=False),
        existing_pct=st.floats(min_value=0.05, max_value=0.20, allow_nan=False),
        trade_pct=st.floats(min_value=0.05, max_value=0.20, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_rejects_when_total_exposure_exceeded(
        self, capital: float, existing_pct: float, trade_pct: float
    ):
        """If total_after > max_total_pct, must be rejected."""
        max_total = 0.20
        assume(existing_pct + trade_pct > max_total)
        existing_value = capital * existing_pct
        trade_value = capital * trade_pct
        portfolio = PortfolioState(total_capital=capital, positions={"SYM": existing_value})
        result = check_exposure(portfolio, "SYM", trade_value, max_total_pct=max_total)
        assert not result.approved

    @given(
        capital=positive_floats,
        trade_value=st.floats(min_value=0.001, max_value=1e6, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_proposed_pct_is_non_negative(self, capital: float, trade_value: float):
        """proposed_additional_pct is always >= 0."""
        result = check_exposure(PortfolioState(total_capital=capital), "SYM", trade_value)
        assert result.proposed_additional_pct >= 0

    @given(
        capital=positive_floats,
        existing_value=st.floats(min_value=0.001, max_value=1e6, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_short_negative_value_uses_absolute(self, capital: float, existing_value: float):
        """Short positions (negative value) use absolute value for exposure."""
        portfolio = PortfolioState(total_capital=capital, positions={"SYM": -existing_value})
        result = check_exposure(portfolio, "SYM2", 1.0)
        assert result.current_total_exposure_pct > 0


# ── 6. Circuit Breakers ─────────────────────────────────────────────────────


class TestCircuitBreakersProperties:
    @given(
        capital=positive_floats,
    )
    @settings(max_examples=50)
    def test_kill_switch_blocks_trading(self, capital: float):
        """When kill switch is active, trading is never allowed."""
        cb = CircuitBreakers(kill_switch=True)
        result = cb.check_trading_allowed(capital)
        assert not result.trading_allowed
        assert "Kill switch" in result.reason

    @given(
        capital=positive_floats,
        max_losses=st.integers(min_value=2, max_value=6),
    )
    @settings(max_examples=50)
    def test_consecutive_losses_eventually_block(self, capital: float, max_losses: int):
        """After max_consecutive_losses, trading is blocked."""
        tiny_loss = 0.001
        cb = CircuitBreakers(
            max_consecutive_losses=max_losses,
            max_daily_loss_pct=1.0,
            max_weekly_loss_pct=1.0,
            kill_switch=False,
        )
        for i in range(max_losses):
            result = cb.check_trading_allowed(capital)
            assert result.trading_allowed or i == max_losses - 1
            if result.trading_allowed:
                cb.record_trade(pnl_pct=-tiny_loss, capital=capital)
        result = cb.check_trading_allowed(capital)
        assert not result.trading_allowed
        assert "consecutive losses" in result.reason

    @given(
        capital=positive_floats,
    )
    @settings(max_examples=50)
    def test_win_resets_consecutive_losses(self, capital: float):
        """A winning trade resets the consecutive loss counter."""
        tiny_loss = 0.001
        cb = CircuitBreakers(
            max_consecutive_losses=3,
            max_daily_loss_pct=1.0,
            max_weekly_loss_pct=1.0,
            kill_switch=False,
        )
        for _ in range(2):
            cb.record_trade(pnl_pct=-tiny_loss, capital=capital)
        cb.record_trade(pnl_pct=tiny_loss, capital=capital)  # win
        cb.record_trade(pnl_pct=-tiny_loss, capital=capital)  # loss
        result = cb.check_trading_allowed(capital)
        assert result.trading_allowed  # only 1 consecutive loss after win

    @given(
        capital=positive_floats,
        max_daily=st.floats(min_value=0.01, max_value=0.10, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_daily_loss_limit_blocks(self, capital: float, max_daily: float):
        """When daily_loss_pct >= max_daily_loss_pct, trading is blocked."""
        cb = CircuitBreakers(max_daily_loss_pct=max_daily, kill_switch=False)
        cb.record_trade(pnl_pct=-max_daily * 0.6, capital=capital)
        result = cb.check_trading_allowed(capital)
        assert result.trading_allowed
        cb.record_trade(pnl_pct=-max_daily * 0.6, capital=capital)
        result = cb.check_trading_allowed(capital)
        assert not result.trading_allowed
        assert "Daily loss" in result.reason

    @given(
        capital=positive_floats,
    )
    @settings(max_examples=50)
    def test_kill_switch_can_be_disabled(self, capital: float):
        """Disabling kill switch re-allows trading."""
        cb = CircuitBreakers(kill_switch=True)
        assert not cb.check_trading_allowed(capital).trading_allowed
        cb.set_kill_switch(False)
        assert cb.check_trading_allowed(capital).trading_allowed

    @given(
        capital=positive_floats,
    )
    @settings(max_examples=50)
    def test_state_is_returned_on_check(self, capital: float):
        """check_trading_allowed always includes the current state."""
        cb = CircuitBreakers(kill_switch=False)
        result = cb.check_trading_allowed(capital)
        assert result.state is not None
        assert hasattr(result.state, "consecutive_losses")

    @given(
        capital=positive_floats,
        num_losses=st.integers(min_value=1, max_value=4),
    )
    @settings(max_examples=50)
    def test_consecutive_losses_increments_on_loss(self, capital: float, num_losses: int):
        """Each losing trade increments consecutive_losses."""
        tiny_loss = 0.001
        cb = CircuitBreakers(
            max_consecutive_losses=num_losses + 1,
            max_daily_loss_pct=1.0,
            max_weekly_loss_pct=1.0,
            kill_switch=False,
        )
        for _ in range(num_losses):
            cb.record_trade(pnl_pct=-tiny_loss, capital=capital)
        assert cb.state.consecutive_losses == num_losses
