"""Configuration endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Body, Request

from app.config import reload_settings

router = APIRouter(prefix="/config", tags=["config"])


def _public_config(settings: Any) -> dict[str, Any]:
    return {
        "mode": settings.mode,
        "kill_switch": settings.kill_switch,
        "database": {"path": str(settings.database.path)},
        "capital": {"initial_usdt": settings.capital.initial_usdt},
        "fees": {
            "trading_fee_pct": settings.fees.trading_fee_pct,
            "slippage_pct": settings.fees.slippage_pct,
        },
        "risk": {
            "max_position_size_pct": settings.risk.max_position_size_pct,
            "max_risk_per_trade_pct": settings.risk.max_risk_per_trade_pct,
            "max_daily_loss_pct": settings.risk.max_daily_loss_pct,
            "max_weekly_loss_pct": settings.risk.max_weekly_loss_pct,
            "max_asset_exposure_pct": settings.risk.max_asset_exposure_pct,
            "max_total_exposure_pct": settings.risk.max_total_exposure_pct,
            "max_altcoin_exposure_pct": settings.risk.max_altcoin_exposure_pct,
            "max_consecutive_losses": settings.risk.max_consecutive_losses,
            "max_trades_per_day": settings.risk.max_trades_per_day,
            "default_stop_loss_pct": settings.risk.default_stop_loss_pct,
            "min_stop_loss_pct": settings.risk.min_stop_loss_pct,
            "max_stop_loss_pct": settings.risk.max_stop_loss_pct,
            "require_stop_loss": settings.risk.require_stop_loss,
            "altcoin_symbols": settings.risk.altcoin_symbols,
        },
        "trading": {
            "mode": settings.trading.mode,
            "allow_real_trading": settings.trading.allow_real_trading,
            "allow_futures": settings.trading.allow_futures,
            "allow_leverage": settings.trading.allow_leverage,
            "require_stop_loss": settings.trading.require_stop_loss,
            "require_take_profit": settings.trading.require_take_profit,
        },
        "backtesting": {
            "default_commission_pct": settings.backtesting.default_commission_pct,
            "default_slippage_pct": settings.backtesting.default_slippage_pct,
            "min_trades_for_validation": settings.backtesting.min_trades_for_validation,
            "min_profit_factor": settings.backtesting.min_profit_factor,
            "min_sharpe_ratio": settings.backtesting.min_sharpe_ratio,
            "max_allowed_drawdown_pct": settings.backtesting.max_allowed_drawdown_pct,
        },
        "symbols": settings.symbols,
        "timeframes": settings.timeframes,
        "alerts": {
            "enabled": (settings.alerts or {}).get("enabled", False),
            "check_interval_seconds": (settings.alerts or {}).get("check_interval_seconds", 300),
        },
        "prospecting": settings.prospecting,
    }


@router.get("")
def get_config(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    return {"status": "ok", "data": _public_config(settings), "error": None, "meta": {}}


@router.post("/universe-symbol")
def add_universe_symbol(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    symbol = str(payload.get("symbol", "")).strip().upper()
    if not symbol:
        return {
            "status": "error",
            "data": None,
            "error": {"message": "symbol is required", "type": "validation_error"},
            "meta": {},
        }

    settings_path = Path("settings.yaml")
    with settings_path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    symbols = [str(item).upper() for item in (raw.get("symbols", []) or [])]
    added = symbol not in symbols
    if added:
        symbols.append(symbol)
        raw["symbols"] = symbols
        with settings_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(raw, handle, sort_keys=False, allow_unicode=False)

    request.app.state.settings = reload_settings(settings_path)
    return {
        "status": "ok",
        "data": {
            "symbol": symbol,
            "added": added,
            "symbols": request.app.state.settings.symbols,
        },
        "error": None,
        "meta": {},
    }


@router.post("/universe-symbol/remove")
def remove_universe_symbol(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    symbol = str(payload.get("symbol", "")).strip().upper()
    if not symbol:
        return {
            "status": "error",
            "data": None,
            "error": {"message": "symbol is required", "type": "validation_error"},
            "meta": {},
        }

    settings_path = Path("settings.yaml")
    with settings_path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    symbols = [str(item).upper() for item in (raw.get("symbols", []) or [])]
    removed = symbol in symbols
    if removed:
        raw["symbols"] = [item for item in symbols if item != symbol]
        with settings_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(raw, handle, sort_keys=False, allow_unicode=False)

    request.app.state.settings = reload_settings(settings_path)
    return {
        "status": "ok",
        "data": {
            "symbol": symbol,
            "removed": removed,
            "symbols": request.app.state.settings.symbols,
        },
        "error": None,
        "meta": {},
    }
