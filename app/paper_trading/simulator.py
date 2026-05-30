from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.paper_trading.virtual_orders import (
    FillResult,
    OrderSide,
    VirtualOrderManager,
)
from app.paper_trading.virtual_portfolio import VirtualPortfolio
from app.risk.circuit_breakers import CircuitBreakers
from app.risk.exposure_limits import PortfolioState
from app.risk.risk_manager import RiskDecision, RiskManager, TradeProposal
from app.strategies.base_strategy import BaseStrategy, Signal


@dataclass
class SimulationResult:
    portfolio: VirtualPortfolio
    trades_executed: int
    trades_rejected: int
    final_capital: float
    total_pnl_pct: float
    max_drawdown_pct: float
    snapshots: list


class PaperTradingSimulator:
    def __init__(
        self,
        strategy: BaseStrategy,
        risk_manager: RiskManager,
        initial_capital: float = 1000.0,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.001,
        symbol: str = "BTCUSDT",
    ) -> None:
        self._strategy = strategy
        self._risk_manager = risk_manager
        self._portfolio = VirtualPortfolio(initial_capital)
        self._orders = VirtualOrderManager(slippage_pct=slippage_pct)
        self._commission_pct = commission_pct
        self._slippage_pct = slippage_pct
        self._symbol = symbol
        self._trades_executed = 0
        self._trades_rejected = 0

    @property
    def portfolio(self) -> VirtualPortfolio:
        return self._portfolio

    @property
    def trades_executed(self) -> int:
        return self._trades_executed

    @property
    def trades_rejected(self) -> int:
        return self._trades_rejected

    def process_signal(self, signal: Signal, current_price: float) -> None:
        self._portfolio.update_prices({self._symbol: current_price})

        if signal.action not in ("BUY", "SELL", "EXIT", "REDUCE"):
            return

        if signal.action == "BUY":
            self._process_buy_signal(signal, current_price)
        else:
            self._process_sell_signal(signal, current_price)

    def _process_buy_signal(self, signal: Signal, current_price: float) -> None:
        if self._portfolio.has_position(self._symbol):
            return

        tv = self._portfolio.total_value
        portfolio_state = PortfolioState(
            total_capital=tv,
            cash=self._portfolio.cash,
            positions={
                sym: pos.quantity * pos.current_price
                for sym, pos in self._portfolio.positions.items()
            },
        )

        proposal = TradeProposal(
            symbol=self._symbol,
            direction="long",
            entry_price=current_price,
            capital=tv,
            reason=signal.reason,
            confidence=signal.confidence,
        )

        decision = self._risk_manager.evaluate(
            proposal,
            portfolio_state,
            stop_loss_price=signal.stop_loss,
        )

        if not decision.approved:
            self._trades_rejected += 1
            return

        ps = decision.position_size
        if ps is None:
            self._trades_rejected += 1
            return

        order = self._orders.create_market_order(
            symbol=self._symbol,
            side=OrderSide.BUY,
            quantity=ps.position_size,
        )

        fill = self._orders.attempt_fill(order, current_price)
        if fill is None:
            return

        fee = fill.quantity * fill.price * self._commission_pct
        buy_quantity = fill.quantity

        success = self._portfolio.buy(
            symbol=self._symbol,
            quantity=buy_quantity,
            price=fill.price,
        )

        if success:
            self._trades_executed += 1

    def _process_sell_signal(self, signal: Signal, current_price: float) -> None:
        if not self._portfolio.has_position(self._symbol):
            return

        pos = self._portfolio.get_position(self._symbol)
        if pos is None:
            return

        order = self._orders.create_market_order(
            symbol=self._symbol,
            side=OrderSide.SELL,
            quantity=pos.quantity,
        )

        fill = self._orders.attempt_fill(order, current_price)
        if fill is None:
            return

        realized_pnl = self._portfolio.sell(
            symbol=self._symbol,
            quantity=fill.quantity,
            price=fill.price,
        )

        if realized_pnl is not None:
            self._portfolio.snapshot()
            self._risk_manager.circuit_breakers.record_trade(
                realized_pnl / (fill.quantity * fill.price) * 100,
                self._portfolio.total_value,
            )
            self._trades_executed += 1

    def get_status(self) -> dict:
        return {
            "total_value": round(self._portfolio.total_value, 2),
            "cash": round(self._portfolio.cash, 2),
            "exposure_pct": round(self._portfolio.exposure_pct, 2),
            "total_pnl": round(self._portfolio.total_pnl, 2),
            "total_pnl_pct": round(self._portfolio.total_pnl_pct, 2),
            "drawdown_pct": round(self._portfolio.drawdown_pct, 2),
            "trades_executed": self._trades_executed,
            "trades_rejected": self._trades_rejected,
        }
