"""Circuit breaker rules to stop trading under adverse conditions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class CircuitBreakerState:
    daily_loss_pct: float = 0.0
    weekly_loss_pct: float = 0.0
    consecutive_losses: int = 0
    trades_today: int = 0
    last_trade_date: Optional[str] = None
    last_reset: str = ""
    kill_switch_active: bool = False
    daily_loss_count: int = 0


@dataclass
class CircuitBreakerResult:
    trading_allowed: bool = True
    reason: str = ""
    state: CircuitBreakerState | None = None


class CircuitBreakers:
    """Stateful guardrail checks for daily activity and losing streaks."""

    def __init__(
        self,
        max_daily_loss_pct: float = 0.03,
        max_weekly_loss_pct: float = 0.07,
        max_consecutive_losses: int = 5,
        max_trades_per_day: int = 10,
        kill_switch: bool = True,
        max_daily_loss_count: int = 2,
    ) -> None:
        self._max_daily_loss = max_daily_loss_pct
        self._max_weekly_loss = max_weekly_loss_pct
        self._max_consecutive_losses = max_consecutive_losses
        self._max_trades_per_day = max_trades_per_day
        self._max_daily_loss_count = max_daily_loss_count
        self._state = CircuitBreakerState(kill_switch_active=kill_switch)
        self._peak_capital: float | None = None

    @property
    def state(self) -> CircuitBreakerState:
        """Return current breaker state snapshot."""
        return self._state

    @property
    def kill_switch_active(self) -> bool:
        """Return whether manual kill switch is active."""
        return self._state.kill_switch_active

    def set_kill_switch(self, active: bool) -> None:
        """Enable or disable kill switch state."""
        self._state.kill_switch_active = active

    def _get_today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _get_week_start(self) -> str:
        today = datetime.now(timezone.utc)
        week_start = today - timedelta(days=today.weekday())
        return week_start.strftime("%Y-%m-%d")

    def _reset_if_new_period(self) -> None:
        today = self._get_today()
        week_start = self._get_week_start()

        if self._state.last_reset != week_start:
            self._state.weekly_loss_pct = 0.0
            self._state.last_reset = week_start

        if self._state.last_trade_date != today:
            self._state.trades_today = 0
            self._state.last_trade_date = today

    def record_trade(self, pnl_pct: float, capital: float) -> None:
        """Update breaker counters after a completed trade."""
        self._reset_if_new_period()

        self._state.trades_today += 1

        if pnl_pct < 0:
            self._state.daily_loss_pct += abs(pnl_pct)
            self._state.weekly_loss_pct += abs(pnl_pct)
            self._state.consecutive_losses += 1
        else:
            self._state.consecutive_losses = 0

    def check_trading_allowed(self, capital: float) -> CircuitBreakerResult:
        """Validate whether new trading is currently allowed."""
        self._reset_if_new_period()

        if self._state.kill_switch_active:
            return CircuitBreakerResult(
                trading_allowed=False,
                reason="Kill switch is active",
                state=self._state,
            )

        if self._state.trades_today >= self._max_trades_per_day:
            return CircuitBreakerResult(
                trading_allowed=False,
                reason=f"Max trades per day ({self._max_trades_per_day}) reached",
                state=self._state,
            )

        if self._state.daily_loss_pct >= self._max_daily_loss:
            return CircuitBreakerResult(
                trading_allowed=False,
                reason=f"Daily loss {self._state.daily_loss_pct:.2%} exceeds max ({self._max_daily_loss:.2%})",
                state=self._state,
            )

        if self._state.weekly_loss_pct >= self._max_weekly_loss:
            return CircuitBreakerResult(
                trading_allowed=False,
                reason=f"Weekly loss {self._state.weekly_loss_pct:.2%} exceeds max ({self._max_weekly_loss:.2%})",
                state=self._state,
            )

        if self._state.consecutive_losses >= self._max_consecutive_losses:
            return CircuitBreakerResult(
                trading_allowed=False,
                reason=f"{self._state.consecutive_losses} consecutive losses exceeds max ({self._max_consecutive_losses})",
                state=self._state,
            )

        return CircuitBreakerResult(trading_allowed=True, state=self._state)

    def can_open_new_position(self, capital: float) -> CircuitBreakerResult:
        """Compatibility alias for trading-allowed check."""
        return self.check_trading_allowed(capital)
