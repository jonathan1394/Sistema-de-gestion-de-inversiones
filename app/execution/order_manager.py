"""Local order tracking, validation, and status management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class OrderRequest:
    symbol: str
    side: str
    quantity: float
    order_type: str = "MARKET"
    price: Optional[float] = None
    stop_price: Optional[float] = None


@dataclass
class OrderValidation:
    valid: bool = True
    reason: str = ""
    adjusted_quantity: Optional[float] = None
    adjusted_price: Optional[float] = None


@dataclass
class OrderRecord:
    id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]
    status: str
    created_at: datetime
    filled_quantity: float = 0.0
    avg_fill_price: Optional[float] = None
    fees: float = 0.0
    error: str = ""


class OrderManager:
    """Tracks orders locally with validation and status updates."""

    def __init__(self) -> None:
        self._orders: list[OrderRecord] = []
        self._next_id = 0
        self._log: list[str] = []

    @property
    def orders(self) -> list[OrderRecord]:
        """Return a copy of all tracked orders."""
        return list(self._orders)

    def validate_order(self, request: OrderRequest, capital: float) -> OrderValidation:
        """Validate an order request against basic constraints."""
        if request.quantity <= 0:
            return OrderValidation(valid=False, reason="Quantity must be positive")

        if request.order_type.upper() == "LIMIT":
            if request.price is None or request.price <= 0:
                return OrderValidation(valid=False, reason="Limit price required and must be positive")

        if request.side.upper() not in ("BUY", "SELL"):
            return OrderValidation(valid=False, reason=f"Invalid side: {request.side}")

        return OrderValidation(valid=True)

    def record_order(self, request: OrderRequest, status: str = "pending", error: str = "") -> OrderRecord:
        """Record a new order and return its record."""
        self._next_id += 1
        record = OrderRecord(
            id=f"ord_{self._next_id:06d}",
            symbol=request.symbol.upper(),
            side=request.side.upper(),
            order_type=request.order_type.upper(),
            quantity=request.quantity,
            price=request.price,
            status=status,
            created_at=datetime.now(timezone.utc),
            error=error,
        )
        self._orders.append(record)
        self._log.append(f"ORDER: {record.side} {record.quantity} {record.symbol} ({record.status})")
        return record

    def update_order(self, order_id: str, filled_quantity: float = 0.0, avg_fill_price: Optional[float] = None, fees: float = 0.0, status: str = "filled") -> None:
        """Update fill details for an existing order."""
        for order in self._orders:
            if order.id == order_id:
                order.filled_quantity = filled_quantity
                order.avg_fill_price = avg_fill_price
                order.fees = fees
                order.status = status
                self._log.append(f"FILL: {order.side} {filled_quantity} {order.symbol} @ {avg_fill_price} ({status})")
                break

    def get_pending_orders(self) -> list[OrderRecord]:
        """Return orders that are pending or submitted."""
        return [o for o in self._orders if o.status in ("pending", "submitted")]

    def get_recent_orders(self, limit: int = 20) -> list[OrderRecord]:
        """Return the most recent orders up to limit."""
        return list(reversed(self._orders[-limit:]))
