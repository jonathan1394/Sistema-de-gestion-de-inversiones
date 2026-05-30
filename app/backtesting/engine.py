"""Backtesting engine that executes strategy signals over historical data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.strategies.base_strategy import BaseStrategy, Signal


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


class BacktestEngine:
    """Run a single-strategy backtest with fees and slippage."""

    def __init__(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        initial_capital: float = 1000.0,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.001,
        symbol: str = "UNKNOWN",
        interval: str = "1h",
    ) -> None:
        self.strategy = strategy
        self.data = data
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.symbol = symbol
        self.interval = interval

    def run(self) -> BacktestResult:
        """Execute backtest loop and return full result object."""
        data = self._prepare_data()
        signal_map = self._build_signal_map(data)

        cash = self.initial_capital
        pos = self._empty_position()
        total_fees = 0.0
        trades: list[TradeRecord] = []
        equity = pd.Series(index=data.index, dtype=float)

        for timestamp, row in data.iterrows():
            price = row["close"]
            sig = signal_map.get(timestamp)
            equity.iloc[data.index.get_loc(timestamp)] = cash + pos["qty"] * price

            if pos["qty"] > 0:
                result = self._check_exit(timestamp, price, sig, pos, cash)
                if result is not None:
                    trades.append(result["trade"])
                    cash = result["cash"]
                    total_fees += result["fees"]
                    pos = self._empty_position()

            if sig is not None and sig.action == "BUY" and pos["qty"] == 0 and cash > 0:
                result = self._enter_position(timestamp, price, sig, cash)
                trades.append(result["trade"])
                pos = result["pos"]
                cash = result["cash"]
                total_fees += result["fees"]

        if pos["qty"] > 0:
            result = self._force_close(data, pos, total_fees)
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
        }

    def _check_exit(
        self, timestamp: pd.Timestamp, price: float, sig: Signal | None,
        pos: dict, cash: float,
    ) -> dict | None:
        pos["hold"] += 1
        stop_hit = pos["stop"] is not None and price <= pos["stop"]
        tp_hit = pos["tp"] is not None and price >= pos["tp"]
        exit_signal = sig is not None and sig.action in ("SELL", "EXIT", "REDUCE")
        if not (exit_signal or stop_hit or tp_hit):
            return None

        exec_px = price * (1 - self.slippage_pct)
        gross = pos["qty"] * exec_px
        fee = gross * self.commission_pct
        net = gross - fee
        pnl = net - (pos["qty"] * pos["entry_px"])
        entry_cost = pos["qty"] * pos["entry_px"]

        if exit_signal:
            reason = sig.reason
        elif stop_hit:
            reason = "Stop-loss hit"
        else:
            reason = "Take-profit hit"

        return {
            "trade": TradeRecord(
                symbol=self.symbol, side="BUY",
                entry_time=pos["entry_time"] or timestamp, exit_time=timestamp,
                entry_price=pos["entry_px"], exit_price=exec_px, quantity=pos["qty"],
                fees=pos["fees"] + fee, pnl=pnl, pnl_pct=pnl / entry_cost if entry_cost > 0 else 0.0,
                reason_entry=pos["reason"], reason_exit=reason, status="closed",
                hold_bars=pos["hold"], stop_loss=pos["stop"], take_profit=pos["tp"],
            ),
            "cash": net, "fees": fee,
        }

    def _enter_position(
        self, timestamp: pd.Timestamp, price: float, sig: Signal, cash: float,
    ) -> dict:
        alloc = min(sig.position_size_pct or 1.0, 1.0)
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
            ),
            "pos": {
                "qty": qty, "entry_px": exec_px, "stop": sig.stop_loss,
                "tp": sig.take_profit, "reason": sig.reason,
                "entry_time": timestamp, "fees": fee, "hold": 0,
            },
            "cash": cash - invest, "fees": fee,
        }

    def _force_close(self, data: pd.DataFrame, pos: dict, total_fees: float) -> dict:
        ts = data.index[-1]
        px = data.iloc[-1]["close"]
        exec_px = px * (1 - self.slippage_pct)
        gross = pos["qty"] * exec_px
        fee = gross * self.commission_pct
        net = gross - fee
        pnl = net - (pos["qty"] * pos["entry_px"])
        entry_cost = pos["qty"] * pos["entry_px"]

        return {
            "trade": TradeRecord(
                symbol=self.symbol, side="BUY",
                entry_time=pos["entry_time"] or ts, exit_time=ts,
                entry_price=pos["entry_px"], exit_price=exec_px, quantity=pos["qty"],
                fees=pos["fees"] + fee, pnl=pnl, pnl_pct=pnl / entry_cost if entry_cost > 0 else 0.0,
                reason_entry=pos["reason"], reason_exit="End of backtest (forced close)",
                status="closed", hold_bars=pos["hold"],
                stop_loss=pos["stop"], take_profit=pos["tp"],
            ),
            "cash": net, "fees": fee,
        }
