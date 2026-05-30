"""Application configuration loading with environment overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class BinanceConfig:
    base_url: str
    request_timeout_seconds: int
    max_retries: int
    retry_delay_seconds: float


@dataclass(frozen=True)
class DatabaseConfig:
    path: Path


@dataclass(frozen=True)
class AppConfig:
    mode: str
    kill_switch: bool
    binance: BinanceConfig
    database: DatabaseConfig


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings(settings_path: str | Path = "settings.yaml") -> AppConfig:
    """Load app settings from YAML and env vars into typed config."""
    settings_file = Path(settings_path)
    if not settings_file.exists():
        raise FileNotFoundError(f"Settings file not found: {settings_file}")

    with settings_file.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    app_raw = raw.get("app", {})
    binance_raw = raw.get("binance", {})
    db_raw = raw.get("database", {})

    mode = os.getenv("APP_MODE", app_raw.get("mode", "analysis"))
    kill_switch = _to_bool(os.getenv("KILL_SWITCH"), app_raw.get("kill_switch", True))

    db_path = Path(os.getenv("DATABASE_PATH", db_raw.get("path", "./data/market.db")))

    return AppConfig(
        mode=mode,
        kill_switch=kill_switch,
        binance=BinanceConfig(
            base_url=binance_raw.get("base_url", "https://api.binance.com"),
            request_timeout_seconds=int(binance_raw.get("request_timeout_seconds", 20)),
            max_retries=int(binance_raw.get("max_retries", 3)),
            retry_delay_seconds=float(binance_raw.get("retry_delay_seconds", 1.5)),
        ),
        database=DatabaseConfig(path=db_path),
    )
