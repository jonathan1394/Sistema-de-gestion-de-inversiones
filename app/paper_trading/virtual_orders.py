"""Virtual order models and fill simulation logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_quantity: float = 0.0
    avg_fill_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None
    rejection_reason: str = ""


@dataclass
class FillResult:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime
    partial: bool = False


class VirtualOrderManager:
    """Manage in-memory orders and simulate fills."""

    def __init__(self, slippage_pct: float = 0.001) -> None:
        self._orders: dict[str, Order] = {}
        self._id_counter = 0
        self._slippage_pct = slippage_pct

    @property
    def orders(self) -> list[Order]:
        """Return all known orders."""
        return list(self._orders.values())

    def create_market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
    ) -> Order:
        """Create and store a market order."""
        order = Order(
            id=self._next_id(),
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
        )
        self._orders[order.id] = order
        return order

    def create_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
    ) -> Order:
        """Create and store a limit order."""
        order = Order(
            id=self._next_id(),
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
        )
        self._orders[order.id] = order
        return order

    def attempt_fill(
        self,
        order: Order,
        current_price: float,
        timestamp: Optional[datetime] = None,
    ) -> Optional[FillResult]:
        """Attempt to fill market or limit order at current price."""
        if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
            return None

        if order.order_type == OrderType.MARKET:
            return self._fill_market(order, current_price, timestamp)

        fill_price = self._check_limit_fill(order, current_price)
        if fill_price is not None:
            return self._fill_limit(order, fill_price, timestamp)

        return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel pending order by id."""
        order = self._orders.get(order_id)
        if order is None or order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            return False
        order.status = OrderStatus.CANCELLED
        return True

    def _fill_market(
        self,
        order: Order,
        current_price: float,
        timestamp: Optional[datetime],
    ) -> FillResult:
        slippage = current_price * self._slippage_pct
        if order.side == OrderSide.BUY:
            fill_price = current_price + slippage
        else:
            fill_price = current_price - slippage

        fill_price = max(fill_price, 0.01)
        now = timestamp or datetime.now(timezone.utc)

        order.filled_quantity = order.quantity
        order.avg_fill_price = fill_price
        order.status = OrderStatus.FILLED
        order.filled_at = now

        return FillResult(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            timestamp=now,
        )

    def _check_limit_fill(self, order: Order, current_price: float) -> Optional[float]:
        if order.price is None:
            return None
        if order.side == OrderSide.BUY and current_price <= order.price:
            return order.price
        if order.side == OrderSide.SELL and current_price >= order.price:
            return order.price
        return None

    def _fill_limit(
        self,
        order: Order,
        fill_price: float,
        timestamp: Optional[datetime],
    ) -> FillResult:
        now = timestamp or datetime.now(timezone.utc)
        order.filled_quantity = order.quantity
        order.avg_fill_price = fill_price
        order.status = OrderStatus.FILLED
        order.filled_at = now

        return FillResult(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            timestamp=now,
        )

    def _next_id(self) -> str:
        self._id_counter += 1
        return f"ord_{self._id_counter:06d}"
