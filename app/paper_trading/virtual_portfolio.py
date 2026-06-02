"""Virtual portfolio model used by paper-trading workflows."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_Direction = str  # "long" | "short"


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    direction: str = "long"


@dataclass
class PortfolioSnapshot:
    timestamp: datetime
    total_value: float
    cash: float
    exposure_pct: float
    daily_pnl: float
    total_pnl: float
    drawdown_pct: float


class VirtualPortfolio:
    """Track cash, positions, PnL, and snapshots for simulation.

    Supports both long (positive quantity) and short (negative quantity)
    positions.
    """

    def __init__(self, initial_capital: float = 1000.0) -> None:
        self._initial_capital = initial_capital
        self._cash = initial_capital
        self._positions: dict[str, Position] = {}
        self._trade_history: list[dict] = []
        self._snapshots: list[PortfolioSnapshot] = []
        self._peak_value = initial_capital
        self._daily_start_value = initial_capital
        self._current_date: str = ""
        self._total_pnl = 0.0
        self._daily_pnl = 0.0

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def positions(self) -> dict[str, Position]:
        return dict(self._positions)

    @property
    def total_value(self) -> float:
        tv = self._cash + sum(
            p.quantity * p.current_price for p in self._positions.values()
        )
        return tv

    @property
    def gross_exposure(self) -> float:
        return sum(
            abs(p.quantity * p.current_price) for p in self._positions.values()
        )

    @property
    def exposure_pct(self) -> float:
        tv = self.total_value
        if tv <= 0:
            return 0.0
        gross = self.gross_exposure
        return gross / tv * 100

    @property
    def total_pnl(self) -> float:
        return self.total_value - self._initial_capital

    @property
    def total_pnl_pct(self) -> float:
        if self._initial_capital <= 0:
            return 0.0
        return (self.total_value - self._initial_capital) / self._initial_capital * 100

    @property
    def drawdown_pct(self) -> float:
        tv = self.total_value
        if tv > self._peak_value:
            self._peak_value = tv
        if self._peak_value <= 0:
            return 0.0
        return (self._peak_value - tv) / self._peak_value * 100

    @property
    def trade_count(self) -> int:
        return len(self._trade_history)

    @property
    def initial_capital(self) -> float:
        return self._initial_capital

    def update_prices(self, prices: dict[str, float], timestamp: Optional[datetime] = None) -> None:
        now = timestamp or datetime.now(timezone.utc)
        date_key = now.strftime("%Y-%m-%d")

        if date_key != self._current_date:
            self._daily_start_value = self.total_value
            self._daily_pnl = 0.0
            self._current_date = date_key

        for symbol, price in prices.items():
            if symbol in self._positions:
                pos = self._positions[symbol]
                pos.current_price = price
                pos.unrealized_pnl = pos.quantity * (price - pos.entry_price)
                if pos.entry_price > 0:
                    if pos.direction == "long":
                        pos.unrealized_pnl_pct = (price / pos.entry_price - 1) * 100
                    else:
                        pos.unrealized_pnl_pct = (1 - price / pos.entry_price) * 100
                else:
                    pos.unrealized_pnl_pct = 0.0

        self._daily_pnl = self.total_value - self._daily_start_value

    def buy(self, symbol: str, quantity: float, price: float, timestamp: Optional[datetime] = None) -> bool:
        cost = quantity * price
        if cost > self._cash:
            return False

        now = timestamp or datetime.now(timezone.utc)
        self._cash -= cost

        if symbol in self._positions:
            existing = self._positions[symbol]
            existing.direction = "long"
            total_qty = existing.quantity + quantity
            total_cost = existing.quantity * existing.entry_price + cost
            existing.quantity = total_qty
            existing.entry_price = total_cost / total_qty
            existing.current_price = price
        else:
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                entry_time=now,
                current_price=price,
                direction="long",
            )

        self._trade_history.append({
            "type": "buy",
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "cost": cost,
            "timestamp": now.isoformat(),
        })
        return True

    def sell(self, symbol: str, quantity: float, price: float, timestamp: Optional[datetime] = None) -> Optional[float]:
        if symbol not in self._positions:
            return None

        pos = self._positions[symbol]
        sell_qty = min(quantity, pos.quantity)
        proceeds = sell_qty * price
        cost_basis = sell_qty * pos.entry_price
        realized_pnl = proceeds - cost_basis

        now = timestamp or datetime.now(timezone.utc)
        self._cash += proceeds

        pos.quantity -= sell_qty
        if pos.quantity <= 0:
            del self._positions[symbol]

        self._trade_history.append({
            "type": "sell",
            "symbol": symbol,
            "quantity": sell_qty,
            "price": price,
            "proceeds": proceeds,
            "realized_pnl": realized_pnl,
            "timestamp": now.isoformat(),
        })
        return realized_pnl

    def short_sell(self, symbol: str, quantity: float, price: float, timestamp: Optional[datetime] = None) -> bool:
        """Open a short position. ``quantity`` is the number of units sold short (positive)."""
        if quantity <= 0:
            return False
        proceeds = quantity * price

        now = timestamp or datetime.now(timezone.utc)
        self._cash += proceeds

        if symbol in self._positions:
            existing = self._positions[symbol]
            existing.direction = "short"
            total_qty = existing.quantity - quantity
            total_cost_basis = existing.quantity * existing.entry_price
            existing.quantity = total_qty
            existing.entry_price = total_cost_basis / (total_qty + quantity) if total_qty != 0 else price
            existing.current_price = price
            if total_qty == 0:
                del self._positions[symbol]
        else:
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=-quantity,
                entry_price=price,
                entry_time=now,
                current_price=price,
                direction="short",
            )

        self._trade_history.append({
            "type": "short_sell",
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "proceeds": proceeds,
            "timestamp": now.isoformat(),
        })
        return True

    def cover_short(self, symbol: str, quantity: float, price: float, timestamp: Optional[datetime] = None) -> Optional[float]:
        """Cover (buy back) ``quantity`` units of a short position. Returns realized PnL."""
        if symbol not in self._positions:
            return None

        pos = self._positions[symbol]
        cover_qty = min(quantity, abs(pos.quantity))
        cost = cover_qty * price
        proceeds_basis = cover_qty * pos.entry_price
        realized_pnl = proceeds_basis - cost

        now = timestamp or datetime.now(timezone.utc)
        self._cash -= cost

        pos.quantity += cover_qty
        if pos.quantity >= 0:
            del self._positions[symbol]

        self._trade_history.append({
            "type": "cover_short",
            "symbol": symbol,
            "quantity": cover_qty,
            "price": price,
            "cost": cost,
            "realized_pnl": realized_pnl,
            "timestamp": now.isoformat(),
        })
        return realized_pnl

    def close_position(self, symbol: str, price: float) -> Optional[float]:
        if symbol not in self._positions:
            return None
        pos = self._positions[symbol]
        qty = abs(pos.quantity)
        if pos.direction == "long":
            return self.sell(symbol, qty, price)
        return self.cover_short(symbol, qty, price)

    def snapshot(self, timestamp: Optional[datetime] = None) -> PortfolioSnapshot:
        now = timestamp or datetime.now(timezone.utc)
        snap = PortfolioSnapshot(
            timestamp=now,
            total_value=round(self.total_value, 2),
            cash=round(self._cash, 2),
            exposure_pct=round(self.exposure_pct, 2),
            daily_pnl=round(self._daily_pnl, 2),
            total_pnl=round(self.total_pnl, 2),
            drawdown_pct=round(self.drawdown_pct, 2),
        )
        self._snapshots.append(snap)
        return snap

    def get_snapshots(self) -> list[PortfolioSnapshot]:
        return list(self._snapshots)

    def get_trade_history(self) -> list[dict]:
        return list(self._trade_history)

    def has_position(self, symbol: str) -> bool:
        return symbol in self._positions and self._positions[symbol].quantity != 0

    def is_short(self, symbol: str) -> bool:
        return symbol in self._positions and self._positions[symbol].quantity < 0

    def get_position(self, symbol: str) -> Optional[Position]:
        return self._positions.get(symbol)

    def reset(self) -> None:
        self._cash = self._initial_capital
        self._positions.clear()
        self._trade_history.clear()
        self._snapshots.clear()
        self._peak_value = self._initial_capital
        self._daily_start_value = self._initial_capital
        self._total_pnl = 0.0
        self._daily_pnl = 0.0
