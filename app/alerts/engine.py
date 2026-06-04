"""Alert rule engine for price, signal, and risk notifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from app.alerts.channels import Alert, AlertManager
from app.strategies.base_strategy import Signal


@dataclass
class AlertRule:
    name: str
    check_fn: Callable[[], Optional[Alert]]
    interval_seconds: int = 3600
    last_triggered: float = 0.0


class AlertEngine:
    """Evaluate registered alert rules and dispatch matches."""

    def __init__(self, manager: AlertManager) -> None:
        self._manager = manager
        self._rules: list[AlertRule] = []

    def add_rule(self, rule: AlertRule) -> None:
        """Register one alert rule."""
        self._rules.append(rule)

    def tick(self) -> list[Alert]:
        """Run due rules once and return triggered alerts."""
        now = datetime.now(timezone.utc).timestamp()
        triggered: list[Alert] = []
        for rule in self._rules:
            if now - rule.last_triggered >= rule.interval_seconds:
                alert = rule.check_fn()
                if alert:
                    rule.last_triggered = now
                    self._manager.notify(alert)
                    triggered.append(alert)
        return triggered

    @property
    def manager(self) -> AlertManager:
        """Return bound alert manager."""
        return self._manager


def price_alert_rule(
    symbol: str,
    current_price_fn: Callable[[], float],
    above: Optional[float] = None,
    below: Optional[float] = None,
) -> AlertRule:
    """Create threshold-based price alert rule."""

    def check() -> Optional[Alert]:
        """Evaluate current price against configured thresholds."""
        price = current_price_fn()
        if above is not None and price >= above:
            return Alert(
                level="INFO",
                category="PRICE",
                title=f"{symbol} above ${above:,.2f}",
                message=f"Price is ${price:,.2f}, above target of ${above:,.2f}",
                data={"symbol": symbol, "price": price, "threshold": above, "direction": "above"},
            )
        if below is not None and price <= below:
            return Alert(
                level="WARNING",
                category="PRICE",
                title=f"{symbol} below ${below:,.2f}",
                message=f"Price is ${price:,.2f}, below target of ${below:,.2f}",
                data={"symbol": symbol, "price": price, "threshold": below, "direction": "below"},
            )
        return None

    label = f"{symbol}_{'above' if above else 'below'}_{above or below}"
    return AlertRule(name=f"price_{label}", check_fn=check, interval_seconds=1800)


def signal_alert_rule(
    symbol: str,
    signals_fn: Callable[[], list[Signal]],
) -> AlertRule:
    """Create rule that notifies on new actionable signals."""
    _last_count = 0

    def check() -> Optional[Alert]:
        """Emit alert when new BUY/SELL signal appears."""
        nonlocal _last_count
        signals = signals_fn()
        current_count = len(signals)
        new_signals = signals[_last_count:]
        _last_count = current_count

        for s in new_signals:
            if s.action in ("BUY", "SELL"):
                return Alert(
                    level="TRADE",
                    category="SIGNAL",
                    title=f"{s.action} {symbol}",
                    message=f"{s.reason} at ${s.price:.2f} (confidence: {s.confidence:.0%})",
                    data={
                        "symbol": symbol,
                        "action": s.action,
                        "price": s.price,
                        "reason": s.reason,
                    },
                )
        return None

    return AlertRule(name=f"signal_{symbol}", check_fn=check, interval_seconds=300)


def risk_alert_rule(
    symbol: str,
    drawdown_fn: Callable[[], float],
    max_drawdown: float = 20.0,
) -> AlertRule:
    """Create drawdown risk alert rule with warning and error levels."""

    def check() -> Optional[Alert]:
        """Evaluate current drawdown against warning/error thresholds."""
        dd = drawdown_fn()
        if dd >= max_drawdown:
            return Alert(
                level="ERROR",
                category="RISK",
                title=f"Max drawdown exceeded on {symbol}",
                message=f"Drawdown is {dd:.1f}% (max allowed: {max_drawdown:.1f}%)",
                data={"symbol": symbol, "drawdown": dd, "max_drawdown": max_drawdown},
            )
        if dd >= max_drawdown * 0.8:
            return Alert(
                level="WARNING",
                category="RISK",
                title=f"Drawdown approaching limit on {symbol}",
                message=f"Drawdown is {dd:.1f}% (limit: {max_drawdown:.1f}%)",
                data={"symbol": symbol, "drawdown": dd, "max_drawdown": max_drawdown},
            )
        return None

    return AlertRule(name=f"risk_{symbol}", check_fn=check, interval_seconds=600)
