"""Alert channels and manager for multi-destination notifications."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from loguru import logger

HISTORY_FILE = Path("data/alert_history.jsonl")


@dataclass
class Alert:
    level: str
    category: str
    title: str
    message: str
    timestamp: str = ""
    data: Optional[dict] = None

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class AlertChannel(ABC):
    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """Send one alert through the channel."""
        ...


class ConsoleChannel(AlertChannel):
    def send(self, alert: Alert) -> bool:
        """Print formatted alert to stderr."""
        color = {"INFO": "", "WARNING": "\033[93m", "ERROR": "\033[91m", "TRADE": "\033[92m"}.get(
            alert.level, ""
        )
        reset = "\033[0m" if color else ""
        icon = {"INFO": "ℹ", "WARNING": "⚠", "ERROR": "✖", "TRADE": "💰"}.get(alert.level, "○")
        line = f"{color}{icon} [{alert.timestamp}] [{alert.category}] {alert.title}: {alert.message}{reset}"
        logger.info("%s", line)
        return True


class DesktopChannel(AlertChannel):
    def send(self, alert: Alert) -> bool:
        """Send desktop notification on supported platforms."""
        try:
            if sys.platform == "linux":
                subprocess.run(
                    ["notify-send", f"CriptoLab — {alert.title}", alert.message],
                    timeout=5,
                    capture_output=True,
                )
                return True
            elif sys.platform == "darwin":
                subprocess.run(
                    [
                        "osascript",
                        "-e",
                        f'display notification "{alert.message}" with title "CriptoLab — {alert.title}"',
                    ],
                    timeout=5,
                    capture_output=True,
                )
                return True
            return False
        except Exception as e:
            logger.debug("Desktop notification failed: %s", e)
            return False


class TelegramChannel(AlertChannel):
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._token = bot_token
        self._chat_id = chat_id
        self._api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def send(self, alert: Alert) -> bool:
        """Send alert message to configured Telegram chat."""
        try:
            icon = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "TRADE": "💰"}.get(
                alert.level, "🔔"
            )
            text = (
                f"{icon} *CriptoLab Alert*\n*{alert.title}*\n{alert.message}\n`{alert.timestamp}`"
            )
            resp = requests.post(
                self._api_url,
                json={"chat_id": self._chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("Failed to send Telegram alert: %s", e)
            return False

    def send_document(self, document_path: str, caption: str = "") -> bool:
        """Send a document to the configured Telegram chat."""
        try:
            with open(document_path, "rb") as doc:
                url = f"https://api.telegram.org/bot{self._token}/sendDocument"
                resp = requests.post(
                    url,
                    data={"chat_id": self._chat_id, "caption": caption},
                    files={"document": doc},
                    timeout=10,
                )
            return resp.status_code == 200
        except Exception as e:
            logger.error("Failed to send Telegram document: %s", e)
            return False


class AlertManager:
    def __init__(self, channels: Optional[list[AlertChannel]] = None) -> None:
        self._channels = channels or [ConsoleChannel()]

    def add_channel(self, channel: AlertChannel) -> None:
        """Attach an additional delivery channel."""
        self._channels.append(channel)

    def notify(self, alert: Alert) -> bool:
        """Persist and dispatch alert to all channels."""
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY_FILE.open("a") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": alert.timestamp,
                        "level": alert.level,
                        "category": alert.category,
                        "title": alert.title,
                        "message": alert.message,
                        "data": alert.data,
                    }
                )
                + "\n"
            )

        results = [ch.send(alert) for ch in self._channels]
        return any(results)

    def get_history(self, limit: int = 50) -> list[dict]:
        """Read recent alert history entries from storage."""
        if not HISTORY_FILE.exists():
            return []
        entries = []
        with HISTORY_FILE.open("r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries[-limit:]

    def clear_history(self) -> None:
        """Delete persisted alert history file if present."""
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()


def build_alert_manager(config: Optional[dict] = None) -> AlertManager:
    """Build alert manager using config and environment fallbacks."""
    channels: list[AlertChannel] = [ConsoleChannel()]

    if config:
        if config.get("notifications", {}).get("desktop", False):
            channels.append(DesktopChannel())

        tg = config.get("notifications", {}).get("telegram", {})
        token = tg.get("bot_token") or os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = tg.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID")
        if token and chat_id:
            channels.append(TelegramChannel(token, chat_id))

    return AlertManager(channels)
