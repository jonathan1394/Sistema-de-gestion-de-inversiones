"""Application configuration loading with environment overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
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
class CapitalConfig:
    initial_usdt: float = 1000.0


@dataclass(frozen=True)
class RiskConfig:
    max_position_size_pct: float = 0.03
    max_risk_per_trade_pct: float = 0.01
    max_daily_loss_pct: float = 0.03
    max_weekly_loss_pct: float = 0.07
    max_asset_exposure_pct: float = 0.35
    max_total_exposure_pct: float = 0.50
    max_altcoin_exposure_pct: float = 0.40
    max_consecutive_losses: int = 5
    max_trades_per_day: int = 10
    default_stop_loss_pct: float = 0.02
    min_stop_loss_pct: float = 0.005
    max_stop_loss_pct: float = 0.10
    require_stop_loss: bool = True
    altcoin_symbols: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TradingConfig:
    mode: str = "paper"
    allow_real_trading: bool = False
    allow_futures: bool = False
    allow_leverage: bool = False
    require_stop_loss: bool = True
    require_take_profit: bool = False


@dataclass(frozen=True)
class FeesConfig:
    trading_fee_pct: float = 0.001
    slippage_pct: float = 0.001


@dataclass(frozen=True)
class BacktestingConfig:
    default_commission_pct: float = 0.001
    default_slippage_pct: float = 0.001
    min_trades_for_validation: int = 50
    min_profit_factor: float = 1.2
    min_sharpe_ratio: float = 1.0
    max_allowed_drawdown_pct: float = 20.0


@dataclass(frozen=True)
class AppConfig:
    mode: str
    kill_switch: bool
    binance: BinanceConfig
    database: DatabaseConfig
    capital: CapitalConfig = field(default_factory=CapitalConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    fees: FeesConfig = field(default_factory=FeesConfig)
    backtesting: BacktestingConfig = field(default_factory=BacktestingConfig)
    symbols: list[str] = field(default_factory=list)
    timeframes: list[str] = field(default_factory=list)
    alerts: dict = field(default_factory=dict)
    prospecting: dict = field(default_factory=dict)


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
    capital_raw = raw.get("capital", {})
    risk_raw = raw.get("risk", {})
    trading_raw = raw.get("trading", {})
    fees_raw = raw.get("fees", {})
    backtesting_raw = raw.get("backtesting", {})

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
        capital=CapitalConfig(initial_usdt=float(capital_raw.get("initial_usdt", 1000.0))),
        risk=RiskConfig(
            max_position_size_pct=float(risk_raw.get("max_position_size_pct", 0.03)),
            max_risk_per_trade_pct=float(risk_raw.get("max_risk_per_trade_pct", 0.01)),
            max_daily_loss_pct=float(risk_raw.get("max_daily_loss_pct", 0.03)),
            max_weekly_loss_pct=float(risk_raw.get("max_weekly_loss_pct", 0.07)),
            max_asset_exposure_pct=float(risk_raw.get("max_asset_exposure_pct", 0.35)),
            max_total_exposure_pct=float(risk_raw.get("max_total_exposure_pct", 0.50)),
            max_altcoin_exposure_pct=float(risk_raw.get("max_altcoin_exposure_pct", 0.40)),
            max_consecutive_losses=int(risk_raw.get("max_consecutive_losses", 5)),
            max_trades_per_day=int(risk_raw.get("max_trades_per_day", 10)),
            default_stop_loss_pct=float(risk_raw.get("default_stop_loss_pct", 0.02)),
            min_stop_loss_pct=float(risk_raw.get("min_stop_loss_pct", 0.005)),
            max_stop_loss_pct=float(risk_raw.get("max_stop_loss_pct", 0.10)),
            require_stop_loss=_to_bool(
                os.getenv("REQUIRE_STOP_LOSS"), risk_raw.get("require_stop_loss", True)
            ),
            altcoin_symbols=list(risk_raw.get("altcoin_symbols", []) or []),
        ),
        trading=TradingConfig(
            mode=str(trading_raw.get("mode", "paper")),
            allow_real_trading=_to_bool(
                os.getenv("ALLOW_REAL_TRADING"), trading_raw.get("allow_real_trading", False)
            ),
            allow_futures=_to_bool(
                os.getenv("ALLOW_FUTURES"), trading_raw.get("allow_futures", False)
            ),
            allow_leverage=_to_bool(
                os.getenv("ALLOW_LEVERAGE"), trading_raw.get("allow_leverage", False)
            ),
            require_stop_loss=_to_bool(
                os.getenv("TRADING_REQUIRE_STOP_LOSS"), trading_raw.get("require_stop_loss", True)
            ),
            require_take_profit=_to_bool(
                os.getenv("TRADING_REQUIRE_TAKE_PROFIT"), trading_raw.get("require_take_profit", False)
            ),
        ),
        fees=FeesConfig(
            trading_fee_pct=float(fees_raw.get("trading_fee_pct", 0.001)),
            slippage_pct=float(fees_raw.get("slippage_pct", 0.001)),
        ),
        backtesting=BacktestingConfig(
            default_commission_pct=float(backtesting_raw.get("default_commission_pct", 0.001)),
            default_slippage_pct=float(backtesting_raw.get("default_slippage_pct", 0.001)),
            min_trades_for_validation=int(backtesting_raw.get("min_trades_for_validation", 50)),
            min_profit_factor=float(backtesting_raw.get("min_profit_factor", 1.2)),
            min_sharpe_ratio=float(backtesting_raw.get("min_sharpe_ratio", 1.0)),
            max_allowed_drawdown_pct=float(backtesting_raw.get("max_allowed_drawdown_pct", 20.0)),
        ),
        symbols=[str(s) for s in (raw.get("symbols", []) or [])],
        timeframes=[str(t) for t in (raw.get("timeframes", []) or [])],
        alerts=raw.get("alerts", {}) or {},
        prospecting=raw.get("prospecting", {}) or {},
    )
