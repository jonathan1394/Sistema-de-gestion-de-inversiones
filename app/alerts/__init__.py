"""Alerts package exports for rules, channels, and manager."""

from app.alerts.channels import (
    HISTORY_FILE,
    Alert,
    AlertChannel,
    AlertManager,
    ConsoleChannel,
    DesktopChannel,
    TelegramChannel,
    build_alert_manager,
)
from app.alerts.engine import (
    AlertEngine,
    AlertRule,
    price_alert_rule,
    risk_alert_rule,
    signal_alert_rule,
)

__all__ = [
    "Alert",
    "AlertChannel",
    "AlertManager",
    "ConsoleChannel",
    "DesktopChannel",
    "TelegramChannel",
    "build_alert_manager",
    "AlertEngine",
    "AlertRule",
    "price_alert_rule",
    "signal_alert_rule",
    "risk_alert_rule",
    "HISTORY_FILE",
]
