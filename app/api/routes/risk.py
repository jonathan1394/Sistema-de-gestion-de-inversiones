"""Risk endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Request

from app.risk.exposure_limits import PortfolioState
from app.risk.risk_manager import RiskManager, TradeProposal

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/limits")
def limits(request: Request) -> dict[str, Any]:
    """Return current risk limits from settings."""
    s = request.app.state.settings
    data = {
        "max_position_size_pct": s.risk.max_position_size_pct,
        "max_risk_per_trade_pct": s.risk.max_risk_per_trade_pct,
        "max_daily_loss_pct": s.risk.max_daily_loss_pct,
        "max_weekly_loss_pct": s.risk.max_weekly_loss_pct,
        "max_asset_exposure_pct": s.risk.max_asset_exposure_pct,
        "max_total_exposure_pct": s.risk.max_total_exposure_pct,
        "max_altcoin_exposure_pct": s.risk.max_altcoin_exposure_pct,
        "max_consecutive_losses": s.risk.max_consecutive_losses,
        "max_trades_per_day": s.risk.max_trades_per_day,
        "default_stop_loss_pct": s.risk.default_stop_loss_pct,
        "min_stop_loss_pct": s.risk.min_stop_loss_pct,
        "max_stop_loss_pct": s.risk.max_stop_loss_pct,
        "require_stop_loss": s.risk.require_stop_loss,
        "altcoin_symbols": s.risk.altcoin_symbols,
    }
    return {"status": "ok", "data": data, "error": None, "meta": {}}


@router.get("/status")
def status(request: Request) -> dict[str, Any]:
    """Return basic risk status for UI."""
    s = request.app.state.settings
    return {
        "status": "ok",
        "data": {"mode": s.mode, "kill_switch": s.kill_switch},
        "error": None,
        "meta": {},
    }


@router.get("/circuit-breakers")
def circuit_breakers(request: Request) -> dict[str, Any]:
    """Expose circuit-breaker state (MVP: defaults only)."""
    # CircuitBreakers currently tracks state in-memory; API is stateless.
    return {"status": "ok", "data": {"state": "stateless"}, "error": None, "meta": {}}


@router.post("/evaluate")
def evaluate(
    request: Request,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Evaluate one trade proposal through the risk manager."""
    s = request.app.state.settings

    proposal = TradeProposal(
        symbol=str(payload.get("symbol", "")),
        direction=str(payload.get("direction", "BUY")),
        entry_price=float(payload.get("entry_price", 0.0)),
        capital=float(payload.get("capital", s.capital.initial_usdt)),
        reason=str(payload.get("reason", "")),
        confidence=float(payload.get("confidence", 0.5)),
    )

    portfolio_in = payload.get("portfolio") or {}
    portfolio = PortfolioState(
        total_capital=float(portfolio_in.get("total_capital", proposal.capital)),
        cash=float(portfolio_in.get("cash", proposal.capital)),
        positions=dict(portfolio_in.get("positions", {}) or {}),
        asset_classes=dict(portfolio_in.get("asset_classes", {}) or {}),
    )

    rm = RiskManager(
        max_position_pct=s.risk.max_position_size_pct,
        max_risk_per_trade_pct=s.risk.max_risk_per_trade_pct,
        default_stop_loss_pct=s.risk.default_stop_loss_pct,
        max_asset_pct=s.risk.max_asset_exposure_pct,
        max_total_pct=s.risk.max_total_exposure_pct,
        max_altcoin_pct=s.risk.max_altcoin_exposure_pct,
        require_stop_loss=s.risk.require_stop_loss,
        altcoin_symbols=set(s.risk.altcoin_symbols),
    )

    decision = rm.evaluate(
        proposal=proposal,
        portfolio=portfolio,
        stop_loss_price=payload.get("stop_loss_price"),
        stop_loss_pct=payload.get("stop_loss_pct"),
    )

    data: dict[str, Any] = {
        "approved": decision.approved,
        "rejection_reason": decision.rejection_reason,
        "warnings": decision.warnings,
        "adjusted_position_value": decision.adjusted_position_value,
    }
    if decision.position_size is not None:
        data["position_size"] = {
            "position_value": decision.position_size.position_value,
            "position_size": decision.position_size.position_size,
            "risk_amount": decision.position_size.risk_amount,
            "rejected": decision.position_size.rejected,
            "rejection_reason": decision.position_size.rejection_reason,
        }
    if decision.stop_loss is not None:
        data["stop_loss"] = {
            "stop_price": decision.stop_loss.stop_price,
            "distance_pct": decision.stop_loss.distance_pct,
            "method": decision.stop_loss.method,
            "rejected": decision.stop_loss.rejected,
            "rejection_reason": decision.stop_loss.rejection_reason,
        }
    if decision.exposure is not None:
        data["exposure"] = {
            "approved": decision.exposure.approved,
            "rejection_reason": decision.exposure.rejection_reason,
            "current_asset_exposure_pct": decision.exposure.current_asset_exposure_pct,
            "current_total_exposure_pct": decision.exposure.current_total_exposure_pct,
            "proposed_additional_pct": decision.exposure.proposed_additional_pct,
            "asset_exposure_after_pct": decision.exposure.asset_exposure_after_pct,
            "total_exposure_after_pct": decision.exposure.total_exposure_after_pct,
            "max_asset_pct": decision.exposure.max_asset_pct,
            "max_total_pct": decision.exposure.max_total_pct,
            "max_altcoin_pct": decision.exposure.max_altcoin_pct,
        }
    if decision.circuit_breaker is not None:
        data["circuit_breaker"] = {
            "trading_allowed": decision.circuit_breaker.trading_allowed,
            "reason": decision.circuit_breaker.reason,
        }

    return {"status": "ok", "data": data, "error": None, "meta": {}}
