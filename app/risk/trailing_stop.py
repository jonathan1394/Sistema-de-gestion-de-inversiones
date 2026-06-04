"""Trailing stop-loss that adjusts as price moves in favour of the position."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TrailingStopConfig:
    """Configuration for a trailing stop."""

    activation_pct: float = 0.01
    trail_pct: float = 0.02
    atr_multiplier: Optional[float] = None
    use_atr: bool = False


@dataclass
class TrailingStopState:
    """Mutable state of a trailing stop during a position's lifetime."""

    active: bool = False
    peak_price: float = 0.0
    current_stop: float = 0.0
    initial_stop: float = 0.0


class TrailingStop:
    """Manages a trailing stop for a single position."""

    def __init__(
        self,
        config: TrailingStopConfig,
        entry_price: float,
        direction: str = "long",
        initial_stop: Optional[float] = None,
    ) -> None:
        self.config = config
        self.entry_price = entry_price
        self.direction = direction
        self.state = TrailingStopState()

        if initial_stop is not None:
            self.state.current_stop = initial_stop
            self.state.initial_stop = initial_stop

    @property
    def current_stop(self) -> float:
        return self.state.current_stop

    def update(
        self,
        current_price: float,
        high: Optional[float] = None,
        low: Optional[float] = None,
        atr_value: Optional[float] = None,
    ) -> float:
        """Update the trailing stop based on current price action."""
        if self.direction == "long":
            return self._update_long(current_price, high or current_price, atr_value)
        return self._update_short(current_price, low or current_price, atr_value)

    def _update_long(
        self,
        price: float,
        high: float,
        atr_value: Optional[float] = None,
    ) -> float:
        entry = self.entry_price
        activation = self.config.activation_pct
        trail = self.config.trail_pct
        state = self.state
        state.peak_price = max(state.peak_price, high)

        if not state.active:
            if price >= entry * (1 + activation):
                state.active = True
                if self.config.use_atr and atr_value and atr_value > 0:
                    distance = atr_value * (self.config.atr_multiplier or 2.0)
                else:
                    distance = state.peak_price * trail
                state.current_stop = max(state.current_stop, state.peak_price - distance)
            return state.current_stop

        if self.config.use_atr and atr_value and atr_value > 0:
            distance = atr_value * (self.config.atr_multiplier or 2.0)
        else:
            distance = state.peak_price * trail

        candidate = state.peak_price - distance
        state.current_stop = max(state.current_stop, candidate)
        return state.current_stop

    def _update_short(
        self,
        price: float,
        low: float,
        atr_value: Optional[float] = None,
    ) -> float:
        entry = self.entry_price
        activation = self.config.activation_pct
        trail = self.config.trail_pct
        state = self.state
        trough = state.peak_price
        new_trough = min(trough, low) if trough != 0 else low
        state.peak_price = new_trough

        if not state.active:
            if price <= entry * (1 - activation):
                state.active = True
                if self.config.use_atr and atr_value and atr_value > 0:
                    distance = atr_value * (self.config.atr_multiplier or 2.0)
                else:
                    distance = state.peak_price * trail if state.peak_price > 0 else entry * trail
                candidate = (
                    state.peak_price + distance if state.peak_price > 0 else entry + distance
                )
                state.current_stop = (
                    min(state.current_stop, candidate) if state.current_stop != 0 else candidate
                )
            return state.current_stop

        if self.config.use_atr and atr_value and atr_value > 0:
            distance = atr_value * (self.config.atr_multiplier or 2.0)
        else:
            distance = state.peak_price * trail if state.peak_price > 0 else entry * trail

        candidate = new_trough + distance
        state.current_stop = (
            min(state.current_stop, candidate) if state.current_stop != 0 else candidate
        )
        return state.current_stop
