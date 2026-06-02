"""Backtesting engine that executes strategy signals over historical data."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from app.risk.exposure_limits import PortfolioState
from app.risk.risk_manager import RiskDecision, RiskManager, TradeProposal
from app.risk.trailing_stop import TrailingStop, TrailingStopConfig
from app.strategies.base_strategy import BaseStrategy, Signal

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    symbol: str
    side: str
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp] = None
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: float = 0.0
    fees: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    reason_entry: str = ""
    reason_exit: str = ""
    status: str = "open"
    hold_bars: int = 0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    direction: str = "long"


@dataclass
class BacktestResult:
    symbol: str
    interval: str
    initial_capital: float
    final_capital: float
    total_fees: float
    trades: list[TradeRecord]
    equity_curve: pd.Series
    strategy_name: str
    parameters: dict
    rejected_signals: list[dict] = field(default_factory=list)


class BacktestEngine:
    """Run a single-strategy backtest with fees, slippage, and short support."""

    def __init__(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        initial_capital: float = 1000.0,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.001,
        symbol: str = "UNKNOWN",
        interval: str = "1h",
        risk_manager: RiskManager | None = None,
        trailing_stop_config: TrailingStopConfig | None = None,
    ) -> None:
        self.strategy = strategy
        self.data = data
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.symbol = symbol
        self.interval = interval
        self._risk_manager = risk_manager
        self._trailing_stop_config = trailing_stop_config
        self._atr_series: pd.Series | None = None

    def _compute_atr(self, period: int = 14) -> pd.Series:
        """Compute ATR from OHLC data."""
        high = self.data["high"]
        low = self.data["low"]
        close = self.data["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        return tr.ewm(span=period, adjust=False).mean()

    def run(self) -> BacktestResult:
        data = self._prepare_data()
        signal_map = self._build_signal_map(data)

        needs_atr = (
            (self._risk_manager is not None and self._risk_manager.take_profit_atr_multiplier is not None)
            or self._trailing_stop_config is not None
        )
        if needs_atr and "high" in data.columns and "low" in data.columns:
            self._atr_series = self._compute_atr()

        cash = self.initial_capital
        pos = self._empty_position()
        trailing: TrailingStop | None = None
        total_fees = 0.0
        trades: list[TradeRecord] = []
        rejected_signals: list[dict] = []
        equity = pd.Series(index=data.index, dtype=float)

        for timestamp, row in data.iterrows():
            price = row["close"]
            sig = signal_map.get(timestamp)
            equity.iloc[data.index.get_loc(timestamp)] = cash + pos["qty"] * price

            if pos["qty"] != 0:
                self._update_trailing_stop(trailing, row, timestamp)
                if trailing is not None:
                    pos["stop"] = trailing.current_stop
                result = self._check_exit(timestamp, price, sig, pos, cash)
                if result is not None:
                    trades.append(result["trade"])
                    cash = result["cash"]
                    total_fees += result["fees"]
                    pos = self._empty_position()
                    trailing = None

            if sig is not None and pos["qty"] == 0 and cash > 0:
                if sig.action == "BUY":
                    is_short = sig.direction == "short"
                    atr_val = self._get_atr(timestamp)
                    if self._risk_manager is not None:
                        proposal = TradeProposal(
                            symbol=self.symbol,
                            direction="short" if is_short else "long",
                            entry_price=price,
                            capital=cash,
                            reason=sig.reason,
                            confidence=sig.confidence,
                        )
                        portfolio = PortfolioState(
                            total_capital=cash,
                            cash=cash,
                            positions={},
                        )
                        decision = self._risk_manager.evaluate(
                            proposal,
                            portfolio,
                            stop_loss_price=sig.stop_loss,
                            atr_value=atr_val,
                        )
                        if not decision.approved:
                            rejected_signals.append({
                                "timestamp": str(timestamp),
                                "reason": sig.reason,
                                "rejection": decision.rejection_reason,
                            })
                            continue
                        result = self._enter_position_rm(timestamp, price, sig, cash, decision)
                        trailing = self._init_trailing(
                            price, sig, decision, atr_val, is_short,
                        )
                    else:
                        result = self._enter_position(timestamp, price, sig, cash)
                        trailing = self._init_trailing_simple(
                            price, sig, is_short,
                        )
                    trades.append(result["trade"])
                    pos = result["pos"]
                    cash = result["cash"]
                    total_fees += result["fees"]

        if pos["qty"] != 0:
            result = self._force_close(data, pos, total_fees, cash)
            trades.append(result["trade"])
            cash = result["cash"]
            total_fees += result["fees"]
            equity.iloc[data.index.get_loc(data.index[-1])] = cash

        equity = equity.ffill()

        return BacktestResult(
            symbol=self.symbol,
            interval=self.interval,
            initial_capital=self.initial_capital,
            final_capital=cash,
            total_fees=total_fees,
            trades=[t for t in trades if t.status == "closed"],
            equity_curve=equity,
            strategy_name=type(self.strategy).__name__,
            parameters=getattr(self.strategy, "parameters", {}),
            rejected_signals=rejected_signals,
        )

    def _prepare_data(self) -> pd.DataFrame:
        data = self.data.copy()
        if "timestamp" in data.columns:
            data = data.set_index("timestamp")
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        return data.sort_index()

    def _build_signal_map(self, data: pd.DataFrame) -> dict[pd.Timestamp, Signal]:
        strategy_result = self.strategy.generate_signals(data)
        signal_map: dict[pd.Timestamp, Signal] = {}
        for sig in strategy_result.signals:
            if sig.timestamp not in signal_map:
                signal_map[sig.timestamp] = sig
        return signal_map

    def _empty_position(self) -> dict:
        return {
            "qty": 0.0, "entry_px": 0.0, "stop": None, "tp": None,
            "reason": "", "entry_time": None, "fees": 0.0, "hold": 0,
            "direction": "long",
        }

    def _get_atr(self, timestamp: pd.Timestamp) -> float | None:
        if self._atr_series is None:
            return None
        try:
            val = self._atr_series.loc[timestamp]
            return float(val) if not np.isnan(val) else None
        except (KeyError, TypeError):
            return None

    def _init_trailing(
        self, price: float, sig: Signal, decision: RiskDecision,
        atr_val: float | None, is_short: bool,
    ) -> TrailingStop | None:
        if self._trailing_stop_config is None:
            return None
        cfg = self._trailing_stop_config
        if cfg.use_atr and atr_val is not None:
            dist = atr_val * (cfg.atr_multiplier or 2.0)
            initial_stop = price - dist if not is_short else price + dist
        else:
            initial_stop = price * (1 - cfg.trail_pct) if not is_short else price * (1 + cfg.trail_pct)
        if decision.stop_loss is not None:
            initial_stop = decision.stop_loss.stop_price
        return TrailingStop(cfg, price, direction="short" if is_short else "long", initial_stop=initial_stop)

    def _init_trailing_simple(
        self, price: float, sig: Signal, is_short: bool,
    ) -> TrailingStop | None:
        if self._trailing_stop_config is None:
            return None
        cfg = self._trailing_stop_config
        initial_stop = sig.stop_loss
        return TrailingStop(cfg, price, direction="short" if is_short else "long", initial_stop=initial_stop)

    def _update_trailing_stop(
        self, trailing: TrailingStop | None, row: pd.Series, timestamp: pd.Timestamp,
    ) -> None:
        if trailing is None:
            return
        price = row["close"] if "close" in row else 0
        high = row["high"] if "high" in row else price
        low = row["low"] if "low" in row else price
        atr_val = self._get_atr(timestamp)
        trailing.update(price, high=high, low=low, atr_value=atr_val)

    def _check_exit(
        self, timestamp: pd.Timestamp, price: float, sig: Signal | None,
        pos: dict, cash: float,
    ) -> dict | None:
        pos["hold"] += 1
        is_short = pos.get("direction", "long") == "short"

        if is_short:
            stop_hit = pos["stop"] is not None and price >= pos["stop"]
            tp_hit = pos["tp"] is not None and price <= pos["tp"]
        else:
            stop_hit = pos["stop"] is not None and price <= pos["stop"]
            tp_hit = pos["tp"] is not None and price >= pos["tp"]

        exit_signal = sig is not None and sig.action in ("SELL", "EXIT", "REDUCE")
        if not (exit_signal or stop_hit or tp_hit):
            return None

        if is_short:
            exec_px = price * (1 + self.slippage_pct)
            gross = abs(pos["qty"]) * exec_px
            fee = gross * self.commission_pct
            cost = gross + fee
            proceeds_basis = abs(pos["qty"]) * pos["entry_px"]
            pnl = proceeds_basis - cost
            entry_notional = abs(pos["qty"]) * pos["entry_px"]
            net_cash = cash - cost
        else:
            exec_px = price * (1 - self.slippage_pct)
            gross = pos["qty"] * exec_px
            fee = gross * self.commission_pct
            net = gross - fee
            pnl = net - (pos["qty"] * pos["entry_px"])
            entry_notional = pos["qty"] * pos["entry_px"]
            net_cash = net

        if exit_signal and sig is not None:
            reason = sig.reason
        elif stop_hit:
            reason = "Stop-loss hit"
        else:
            reason = "Take-profit hit"

        side = "SELL" if is_short else "BUY"

        return {
            "trade": TradeRecord(
                symbol=self.symbol, side=side,
                entry_time=pos["entry_time"] or timestamp, exit_time=timestamp,
                entry_price=pos["entry_px"], exit_price=exec_px,
                quantity=abs(pos["qty"]),
                fees=pos["fees"] + fee, pnl=pnl,
                pnl_pct=pnl / entry_notional if entry_notional > 0 else 0.0,
                reason_entry=pos["reason"], reason_exit=reason, status="closed",
                hold_bars=pos["hold"], stop_loss=pos["stop"], take_profit=pos["tp"],
                direction=pos.get("direction", "long"),
            ),
            "cash": net_cash, "fees": fee,
        }

    def _enter_position(
        self, timestamp: pd.Timestamp, price: float, sig: Signal, cash: float,
    ) -> dict:
        is_short = sig.direction == "short"
        alloc = min(sig.position_size_pct or 1.0, 1.0)

        if is_short:
            invest = cash * alloc
            exec_px = price * (1 - self.slippage_pct)
            fee = invest * self.commission_pct
            qty_notional = invest + fee
            qty = qty_notional / exec_px
            net_cash = cash + qty_notional

            return {
                "trade": TradeRecord(
                    symbol=self.symbol, side="SELL", entry_time=timestamp,
                    entry_price=exec_px, quantity=qty, fees=fee,
                    reason_entry=sig.reason, status="open",
                    stop_loss=sig.stop_loss, take_profit=sig.take_profit,
                    direction="short",
                ),
                "pos": {
                    "qty": -qty, "entry_px": exec_px, "stop": sig.stop_loss,
                    "tp": sig.take_profit, "reason": sig.reason,
                    "entry_time": timestamp, "fees": fee, "hold": 0,
                    "direction": "short",
                },
                "cash": net_cash, "fees": fee,
            }

        invest = cash * alloc
        exec_px = price * (1 + self.slippage_pct)
        fee = invest * self.commission_pct
        qty = invest / exec_px

        return {
            "trade": TradeRecord(
                symbol=self.symbol, side="BUY", entry_time=timestamp,
                entry_price=exec_px, quantity=qty, fees=fee,
                reason_entry=sig.reason, status="open",
                stop_loss=sig.stop_loss, take_profit=sig.take_profit,
                direction="long",
            ),
            "pos": {
                "qty": qty, "entry_px": exec_px, "stop": sig.stop_loss,
                "tp": sig.take_profit, "reason": sig.reason,
                "entry_time": timestamp, "fees": fee, "hold": 0,
                "direction": "long",
            },
            "cash": cash - invest, "fees": fee,
        }

    def _enter_position_rm(
        self, timestamp: pd.Timestamp, price: float, sig: Signal, cash: float,
        decision: RiskDecision,
    ) -> dict:
        is_short = sig.direction == "short"
        inv = decision.position_size.position_value if decision.position_size else 0
        invest = min(inv, cash)

        if is_short:
            exec_px = price * (1 - self.slippage_pct)
            fee = invest * self.commission_pct
            qty_notional = invest + fee
            qty = qty_notional / exec_px
            stop = decision.stop_loss.stop_price if decision.stop_loss else sig.stop_loss
            net_cash = cash + qty_notional

            return {
                "trade": TradeRecord(
                    symbol=self.symbol, side="SELL", entry_time=timestamp,
                    entry_price=exec_px, quantity=qty, fees=fee,
                    reason_entry=sig.reason, status="open",
                    stop_loss=stop, take_profit=sig.take_profit,
                    direction="short",
                ),
                "pos": {
                    "qty": -qty, "entry_px": exec_px, "stop": stop,
                    "tp": sig.take_profit, "reason": sig.reason,
                    "entry_time": timestamp, "fees": fee, "hold": 0,
                    "direction": "short",
                },
                "cash": net_cash, "fees": fee,
            }

        exec_px = price * (1 + self.slippage_pct)
        fee = invest * self.commission_pct
        qty = invest / exec_px
        stop = decision.stop_loss.stop_price if decision.stop_loss else sig.stop_loss

        return {
            "trade": TradeRecord(
                symbol=self.symbol, side="BUY", entry_time=timestamp,
                entry_price=exec_px, quantity=qty, fees=fee,
                reason_entry=sig.reason, status="open",
                stop_loss=stop, take_profit=sig.take_profit,
                direction="long",
            ),
            "pos": {
                "qty": qty, "entry_px": exec_px, "stop": stop,
                "tp": sig.take_profit, "reason": sig.reason,
                "entry_time": timestamp, "fees": fee, "hold": 0,
                "direction": "long",
            },
            "cash": cash - invest, "fees": fee,
        }

    def _force_close(self, data: pd.DataFrame, pos: dict, total_fees: float, cash: float) -> dict:
        ts = data.index[-1]
        px = data.iloc[-1]["close"]
        is_short = pos.get("direction", "long") == "short"

        if is_short:
            exec_px = px * (1 + self.slippage_pct)
            gross = abs(pos["qty"]) * exec_px
            fee = gross * self.commission_pct
            cost = gross + fee
            pnl = (abs(pos["qty"]) * pos["entry_px"]) - cost
        else:
            exec_px = px * (1 - self.slippage_pct)
            gross = pos["qty"] * exec_px
            fee = gross * self.commission_pct
            net = gross - fee
            pnl = net - (pos["qty"] * pos["entry_px"])
            cost = 0.0

        entry_notional = abs(pos["qty"]) * pos["entry_px"]

        return {
            "trade": TradeRecord(
                symbol=self.symbol, side="SELL" if is_short else "BUY",
                entry_time=pos["entry_time"] or ts, exit_time=ts,
                entry_price=pos["entry_px"], exit_price=exec_px,
                quantity=abs(pos["qty"]),
                fees=pos["fees"] + fee, pnl=pnl,
                pnl_pct=pnl / entry_notional if entry_notional > 0 else 0.0,
                reason_entry=pos["reason"], reason_exit="End of backtest (forced close)",
                status="closed", hold_bars=pos["hold"],
                stop_loss=pos["stop"], take_profit=pos["tp"],
                direction=pos.get("direction", "long"),
            ),
            "cash": cash - cost if is_short else net, "fees": fee,
        }
