"""Investment decision engine for paper trading candidates.

Evaluates whether a prospect should be recommended for a paper buy,
considering kill switch, mode, risk limits, and logs the decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import load_settings
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.governance.decision_log import log_decision
from app.prospecting.market_decision import analyze_timeframe, compute_confluence
from app.prospecting.scoring import get_recommendation
from app.risk.exposure_limits import PortfolioState
from app.risk.risk_manager import RiskManager, TradeProposal


@dataclass
class InvestmentDecision:
    """Result of evaluating an investment candidate."""

    approved: bool
    recommendation: str  # from scoring: INVERTIR, VIGILAR, NEUTRAL, EVITAR
    action: Optional[str]  # e.g., "PAPER_BUY" or None
    reason: str
    blocking_rule: Optional[str]  # e.g., "KILL_SWITCH", "MODE_NOT_ALLOWED", "RISK_REJECTED"
    suggested_amount_usdt: float
    score: float
    confluence: int
    current_price: float
    quantity: float  # amount / price


def _is_trading_allowed(settings) -> tuple[bool, Optional[str]]:
    """Check if trading (including paper) is allowed based on kill switch and mode."""
    if settings.kill_switch:
        return False, "KILL_SWITCH"
    if settings.mode not in ("paper", "real_manual", "real_auto_limited"):
        return False, f"MODE_NOT_ALLOWED: {settings.mode}"
    if settings.mode == "paper":
        return True, None
    return False, f"MODE_NOT_ALLOWED_FOR_PAPER_BUY: {settings.mode}"


def _get_current_price(connection, symbol: str) -> Optional[float]:
    """Fetch the latest close price for symbol from candles (any interval)."""
    for interval in ("1h", "4h", "1d"):
        candles = get_candles(connection=connection, symbol=symbol, interval=interval, limit=1, desc=True)
        if candles and len(candles) > 0:
            return float(candles[0].close)
    return None


def _price_and_qty(conn, symbol: str, amount: float) -> tuple[float, float]:
    price = _get_current_price(conn, symbol) or 0.0
    qty = amount / price if price > 0 else 0.0
    return price, qty


def _get_recommendation(score: float, confluence: int, cfg: dict) -> object:
    return get_recommendation(
        score=score,
        confluence=confluence,
        invertir_threshold=cfg.get("invertir_threshold", 0.75),
        vigilat_threshold=cfg.get("vigilar_threshold", 0.60),
        neutral_threshold=cfg.get("neutral_threshold", 0.40),
        min_confluence_invertir=cfg.get("min_confluence_for_invertir", 2),
        min_confluence_vigilat=cfg.get("min_confluence_for_vigilar", 1),
    )


def _decision(
    approved: bool,
    action: str | None,
    reason: str,
    blocking_rule: str | None,
    rec_label: str,
    score: float,
    confluence: int,
    price: float,
    qty: float,
    amount: float,
) -> InvestmentDecision:
    return InvestmentDecision(
        approved=approved,
        recommendation=rec_label,
        action=action,
        reason=reason,
        blocking_rule=blocking_rule,
        suggested_amount_usdt=amount,
        score=score,
        confluence=confluence,
        current_price=price,
        quantity=qty,
    )


def _make_risk_manager(settings) -> RiskManager:
    return RiskManager(
        max_position_pct=settings.risk.max_position_size_pct,
        max_risk_per_trade_pct=settings.risk.max_risk_per_trade_pct,
        default_stop_loss_pct=settings.risk.default_stop_loss_pct,
        max_asset_pct=settings.risk.max_asset_exposure_pct,
        max_total_pct=settings.risk.max_total_exposure_pct,
        max_altcoin_pct=settings.risk.max_altcoin_exposure_pct,
        require_stop_loss=settings.risk.require_stop_loss,
        altcoin_symbols=set(settings.risk.altcoin_symbols),
    )


def compute_confluence_score(conn, symbol: str) -> int:
    """Compute confluence score from 1h, 4h, 1d timeframes."""
    results = []
    for tf in ("1h", "4h", "1d"):
        result = analyze_timeframe(conn, symbol, tf)
        if result is not None:
            results.append(result)
    return compute_confluence(results)


def evaluate_investment_decision(
    *,
    symbol: str,
    interval: str,
    score: float,
    suggested_amount_usdt: float = 50.0,
) -> InvestmentDecision:
    """Evaluate a prospect for a paper buy decision."""
    settings = load_settings()
    conn = get_connection(settings.database.path)

    confluence = compute_confluence_score(conn, symbol)
    rec_cfg = settings.prospecting.get("recommendation", {})

    allowed, blocking_rule = _is_trading_allowed(settings)
    if not allowed:
        rec = _get_recommendation(score, confluence, rec_cfg)
        price, qty = _price_and_qty(conn, symbol, suggested_amount_usdt)
        return _decision(False, None, f"Trading not allowed: {blocking_rule}", blocking_rule, rec.label, score, confluence, price, qty, suggested_amount_usdt)

    rec = _get_recommendation(score, confluence, rec_cfg)
    if rec.label != "INVERTIR":
        price, qty = _price_and_qty(conn, symbol, suggested_amount_usdt)
        return _decision(False, None, f"Recommendation is {rec.label}, not INVERTIR", None, rec.label, score, confluence, price, qty, suggested_amount_usdt)

    price, qty = _price_and_qty(conn, symbol, suggested_amount_usdt)
    if price <= 0:
        return _decision(False, None, "Unable to fetch current price", "PRICE_UNAVAILABLE", rec.label, score, confluence, 0.0, 0.0, suggested_amount_usdt)

    portfolio = PortfolioState(total_capital=settings.capital.initial_usdt, cash=settings.capital.initial_usdt, positions={}, asset_classes={})
    proposal = TradeProposal(symbol=symbol, direction="BUY", entry_price=price, capital=settings.capital.initial_usdt, reason=f"Prospect score {score:.2f}, confluence {confluence}/3", confidence=score)
    risk_decision = _make_risk_manager(settings).evaluate(proposal=proposal, portfolio=portfolio)

    log_decision(
        decision_type="PAPER_BUY_EVALUATION",
        symbol=symbol,
        strategy_name="prospecting",
        timeframe=interval,
        mode=settings.trading.mode,
        approved=risk_decision.approved,
        reason=risk_decision.rejection_reason if not risk_decision.approved else "Approved by risk manager",
        input_data={"symbol": symbol, "score": score, "confluence": confluence, "suggested_amount_usdt": suggested_amount_usdt, "recommendation": rec.label},
        output_data={"approved": risk_decision.approved, "rejection_reason": risk_decision.rejection_reason, "suggested_quantity": qty, "suggested_amount_usdt": suggested_amount_usdt},
        policy_version=settings.policy.version if hasattr(settings, "policy") else None,
        strategy_version="1.0", settings=settings,
    )

    if risk_decision.approved:
        return _decision(True, "PAPER_BUY", "Approved by risk manager", None, rec.label, score, confluence, price, qty, suggested_amount_usdt)
    return _decision(False, None, risk_decision.rejection_reason or "Rejected by risk manager", "RISK_REJECTED", rec.label, score, confluence, price, qty, suggested_amount_usdt)
