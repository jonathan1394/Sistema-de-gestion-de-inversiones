"""Orchestrates stop-loss, position sizing, and exposure checks for trades."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.risk.circuit_breakers import CircuitBreakers, CircuitBreakerResult
from app.risk.exposure_limits import (
    ExposureCheckResult,
    PortfolioState,
    check_exposure,
)
from app.risk.position_sizing import PositionSizeResult, calculate_position_size
from app.risk.stop_loss import StopLossResult, fixed_percentage


@dataclass
class TradeProposal:
    symbol: str
    direction: str
    entry_price: float
    capital: float
    reason: str = ""
    confidence: float = 0.5


@dataclass
class RiskDecision:
    approved: bool = False
    rejection_reason: str = ""
    position_size: Optional[PositionSizeResult] = None
    stop_loss: Optional[StopLossResult] = None
    exposure: Optional[ExposureCheckResult] = None
    circuit_breaker: Optional[CircuitBreakerResult] = None
    adjusted_position_value: Optional[float] = None
    warnings: list[str] = field(default_factory=list)


class RiskManager:
    """Apply layered risk controls to approve or reject trade proposals."""

    def __init__(
        self,
        circuit_breakers: CircuitBreakers | None = None,
        max_position_pct: float = 0.03,
        max_risk_per_trade_pct: float = 0.01,
        default_stop_loss_pct: float = 0.02,
        max_asset_pct: float = 0.35,
        max_total_pct: float = 0.50,
        max_altcoin_pct: float = 0.40,
        require_stop_loss: bool = True,
        altcoin_symbols: set[str] | None = None,
    ) -> None:
        self._circuit_breakers = circuit_breakers or CircuitBreakers()
        self._max_position_pct = max_position_pct
        self._max_risk_per_trade_pct = max_risk_per_trade_pct
        self._default_stop_loss_pct = default_stop_loss_pct
        self._max_asset_pct = max_asset_pct
        self._max_total_pct = max_total_pct
        self._max_altcoin_pct = max_altcoin_pct
        self._require_stop_loss = require_stop_loss
        self._altcoin_symbols = altcoin_symbols or set()

    @property
    def circuit_breakers(self) -> CircuitBreakers:
        """Expose circuit-breaker state and controls."""
        return self._circuit_breakers

    def evaluate(
        self,
        proposal: TradeProposal,
        portfolio: PortfolioState,
        stop_loss_price: float | None = None,
        stop_loss_pct: float | None = None,
    ) -> RiskDecision:
        """Evaluate a proposed trade and return approval details or rejection reason."""
        warnings: list[str] = []
        decision = RiskDecision()

        cb_result = self._circuit_breakers.can_open_new_position(proposal.capital)
        decision.circuit_breaker = cb_result
        if not cb_result.trading_allowed:
            decision.rejection_reason = cb_result.reason
            return decision

        sl_result: StopLossResult | None = None
        if stop_loss_price is not None:
            sl_result = StopLossResult(stop_price=stop_loss_price, distance_pct=0, method="provided")
        elif stop_loss_pct is not None:
            sl_result = fixed_percentage(proposal.entry_price, stop_loss_pct, proposal.direction)
        else:
            sl_result = fixed_percentage(proposal.entry_price, self._default_stop_loss_pct, proposal.direction)

        if sl_result is None or sl_result.rejected:
            decision.rejection_reason = sl_result.rejection_reason if sl_result else "Invalid stop-loss"
            return decision

        decision.stop_loss = sl_result

        ps_result = calculate_position_size(
            capital=proposal.capital,
            entry_price=proposal.entry_price,
            stop_loss=sl_result.stop_price,
            risk_per_trade_pct=self._max_risk_per_trade_pct,
            max_position_pct=self._max_position_pct,
            direction=proposal.direction,
        )
        decision.position_size = ps_result

        if ps_result.rejected:
            decision.rejection_reason = ps_result.rejection_reason
            return decision

        exposure = check_exposure(
            portfolio=portfolio,
            symbol=proposal.symbol,
            trade_value=ps_result.position_value,
            max_asset_pct=self._max_asset_pct,
            max_total_pct=self._max_total_pct,
            max_altcoin_pct=self._max_altcoin_pct,
            altcoin_symbols=self._altcoin_symbols,
        )
        decision.exposure = exposure

        if not exposure.approved:
            decision.rejection_reason = exposure.rejection_reason
            return decision

        if ps_result.position_size == 0:
            decision.rejection_reason = "Position size is zero after risk calculation"
            return decision

        decision.approved = True

        if ps_result.position_value < proposal.capital * self._max_position_pct:
            decision.adjusted_position_value = ps_result.position_value

        if proposal.confidence < 0.3:
            warnings.append(f"Low confidence signal ({proposal.confidence:.1f})")

        decision.warnings = warnings
        return decision
