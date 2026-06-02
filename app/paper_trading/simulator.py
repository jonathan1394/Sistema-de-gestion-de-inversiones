"""Paper-trading simulator wiring strategy, risk, and virtual execution."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

from app.paper_trading import storage as pt_storage
from app.paper_trading.virtual_orders import (
    OrderSide,
    VirtualOrderManager,
)
from app.paper_trading.virtual_portfolio import VirtualPortfolio
from app.risk.exposure_limits import PortfolioState
from app.risk.risk_manager import RiskManager, TradeProposal
from app.strategies.base_strategy import BaseStrategy, Signal

logger = logging.getLogger(__name__)


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
    """Execute strategy signals on a virtual portfolio with risk controls."""

    def __init__(
        self,
        strategy: BaseStrategy,
        risk_manager: RiskManager,
        initial_capital: float = 1000.0,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.001,
        symbol: str = "BTCUSDT",
        db_path: str | None = None,
        interval: str = "4h",
    ) -> None:
        self._strategy = strategy
        self._risk_manager = risk_manager
        self._portfolio = VirtualPortfolio(initial_capital)
        self._orders = VirtualOrderManager(slippage_pct=slippage_pct)
        self._commission_pct = commission_pct
        self._slippage_pct = slippage_pct
        self._symbol = symbol
        self._interval = interval
        self._trades_executed = 0
        self._trades_rejected = 0
        self._db_path = db_path
        self._db_conn: sqlite3.Connection | None = None

    def _get_db(self) -> sqlite3.Connection | None:
        if self._db_path is not None and self._db_conn is None:
            self._db_conn = sqlite3.connect(self._db_path)
            self._db_conn.row_factory = sqlite3.Row
            pt_storage.init_portfolio_tables(self._db_conn)
        return self._db_conn

    @property
    def portfolio(self) -> VirtualPortfolio:
        """Return current virtual portfolio state."""
        return self._portfolio

    @property
    def trades_executed(self) -> int:
        """Return number of executed trades."""
        return self._trades_executed

    @property
    def trades_rejected(self) -> int:
        """Return number of rejected trades."""
        return self._trades_rejected

    def process_signal(self, signal: Signal, current_price: float) -> None:
        """Process one signal at current market price."""
        self._portfolio.update_prices({self._symbol: current_price}, timestamp=signal.timestamp)

        if signal.action not in ("BUY", "SELL", "EXIT", "REDUCE"):
            return

        if signal.action == "BUY":
            if signal.direction == "short":
                self._process_short_signal(signal, current_price)
            else:
                self._process_buy_signal(signal, current_price)
        else:
            if self._portfolio.is_short(self._symbol):
                self._process_cover_short_signal(signal, current_price)
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

        buy_quantity = fill.quantity

        success = self._portfolio.buy(
            symbol=self._symbol,
            quantity=buy_quantity,
            price=fill.price,
        )

        if success:
            self._trades_executed += 1
            self._risk_manager.circuit_breakers.record_trade(
                0.0,
                self._portfolio.total_value,
            )
            conn = self._get_db()
            if conn is not None:
                pos = self._portfolio.get_position(self._symbol)
                if pos:
                    pt_storage.upsert_position(
                        conn,
                        symbol=self._symbol,
                        quantity=pos.quantity,
                        entry_price=pos.entry_price,
                        current_price=pos.current_price,
                        entry_time=pos.entry_time.isoformat() if pos.entry_time else None,
                    )
                pt_storage.add_snapshot(
                    conn,
                    total_value=round(self._portfolio.total_value, 2),
                    cash=round(self._portfolio.cash, 2),
                    drawdown_pct=round(self._portfolio.drawdown_pct, 2),
                )

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
            self._portfolio.snapshot(timestamp=signal.timestamp)
            self._risk_manager.circuit_breakers.record_trade(
                realized_pnl / (fill.quantity * fill.price),
                self._portfolio.total_value,
            )
            self._trades_executed += 1

            conn = self._get_db()
            if conn is not None:
                pnl_pct = realized_pnl / (fill.quantity * fill.price)
                pt_storage.record_trade(
                    conn,
                    symbol=self._symbol,
                    action=signal.action,
                    quantity=fill.quantity,
                    price=fill.price,
                    commission=fill.quantity * fill.price * self._commission_pct,
                    pnl=realized_pnl,
                    pnl_pct=pnl_pct,
                    reason=signal.reason,
                    interval=self._interval,
                )
                if not self._portfolio.has_position(self._symbol):
                    pt_storage.remove_position(conn, self._symbol)
                else:
                    pos = self._portfolio.get_position(self._symbol)
                    if pos:
                        pt_storage.upsert_position(
                            conn,
                            symbol=self._symbol,
                            quantity=pos.quantity,
                            entry_price=pos.entry_price,
                            current_price=pos.current_price,
                            entry_time=pos.entry_time.isoformat() if pos.entry_time else None,
                        )
                pt_storage.add_snapshot(
                    conn,
                    total_value=round(self._portfolio.total_value, 2),
                    cash=round(self._portfolio.cash, 2),
                    drawdown_pct=round(self._portfolio.drawdown_pct, 2),
                )

    def _process_short_signal(self, signal: Signal, current_price: float) -> None:
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
            direction="short",
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
            side=OrderSide.SELL,
            quantity=ps.position_size,
        )

        fill = self._orders.attempt_fill(order, current_price)
        if fill is None:
            return

        short_quantity = fill.quantity

        success = self._portfolio.short_sell(
            symbol=self._symbol,
            quantity=short_quantity,
            price=fill.price,
        )

        if success:
            self._trades_executed += 1
            self._risk_manager.circuit_breakers.record_trade(
                0.0,
                self._portfolio.total_value,
            )
            conn = self._get_db()
            if conn is not None:
                pos = self._portfolio.get_position(self._symbol)
                if pos:
                    pt_storage.upsert_position(
                        conn,
                        symbol=self._symbol,
                        quantity=pos.quantity,
                        entry_price=pos.entry_price,
                        current_price=pos.current_price,
                        entry_time=pos.entry_time.isoformat() if pos.entry_time else None,
                    )
                pt_storage.add_snapshot(
                    conn,
                    total_value=round(self._portfolio.total_value, 2),
                    cash=round(self._portfolio.cash, 2),
                    drawdown_pct=round(self._portfolio.drawdown_pct, 2),
                )

    def _process_cover_short_signal(self, signal: Signal, current_price: float) -> None:
        if not self._portfolio.has_position(self._symbol):
            return

        pos = self._portfolio.get_position(self._symbol)
        if pos is None:
            return

        order = self._orders.create_market_order(
            symbol=self._symbol,
            side=OrderSide.BUY,
            quantity=abs(pos.quantity),
        )

        fill = self._orders.attempt_fill(order, current_price)
        if fill is None:
            return

        realized_pnl = self._portfolio.cover_short(
            symbol=self._symbol,
            quantity=fill.quantity,
            price=fill.price,
        )

        if realized_pnl is not None:
            self._portfolio.snapshot(timestamp=signal.timestamp)
            self._risk_manager.circuit_breakers.record_trade(
                realized_pnl / (fill.quantity * fill.price),
                self._portfolio.total_value,
            )
            self._trades_executed += 1

            conn = self._get_db()
            if conn is not None:
                pnl_pct = realized_pnl / (fill.quantity * fill.price)
                pt_storage.record_trade(
                    conn,
                    symbol=self._symbol,
                    action=signal.action,
                    quantity=fill.quantity,
                    price=fill.price,
                    commission=fill.quantity * fill.price * self._commission_pct,
                    pnl=realized_pnl,
                    pnl_pct=pnl_pct,
                    reason=signal.reason,
                    interval=self._interval,
                )
                if not self._portfolio.has_position(self._symbol):
                    pt_storage.remove_position(conn, self._symbol)
                else:
                    pos = self._portfolio.get_position(self._symbol)
                    if pos:
                        pt_storage.upsert_position(
                            conn,
                            symbol=self._symbol,
                            quantity=pos.quantity,
                            entry_price=pos.entry_price,
                            current_price=pos.current_price,
                            entry_time=pos.entry_time.isoformat() if pos.entry_time else None,
                        )
                pt_storage.add_snapshot(
                    conn,
                    total_value=round(self._portfolio.total_value, 2),
                    cash=round(self._portfolio.cash, 2),
                    drawdown_pct=round(self._portfolio.drawdown_pct, 2),
                )

    def get_status(self) -> dict:
        """Return compact simulator status metrics."""
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
