"""Investment decision engine for paper trading candidates.

Evaluates whether a prospect should be recommended for a paper buy,
considering kill switch, mode, risk limits, and logs the decision.
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

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
    # For now, we only allow paper buy recommendations.
    if settings.mode == "paper":
        return True, None
    # In real modes, we would require additional checks (not implemented yet).
    # For safety, we treat them as not allowed for automatic paper buy proposals.
    return False, f"MODE_NOT_ALLOWED_FOR_PAPER_BUY: {settings.mode}"


def _get_current_price(connection, symbol: str) -> Optional[float]:
    """Fetch the latest close price for symbol from candles (any interval)."""
    # Try 1h, 4h, 1d in that order.
    for interval in ("1h", "4h", "1d"):
        candles = get_candles(connection=connection, symbol=symbol, interval=interval, limit=1, desc=True)
        if candles and len(candles) > 0:
            return float(candles[0].close)
    return None


def evaluate_investment_decision(
    *,
    symbol: str,
    interval: str,
    score: float,
    suggested_amount_usdt: float = 50.0,
) -> InvestmentDecision:
    """Evaluate a prospect for a paper buy decision.

    Parameters
    ----------
    symbol: str
        Trading symbol (e.g., BTCUSDT).
    interval: str
        Timeframe used for scoring (e.g., 1d). This parameter is kept for compatibility
        but is not used for confluence; confluence is computed from 1h,4h,1d.
    score: float
        Prospect score from 0.0 to 1.0.
    suggested_amount_usdt: float
        Default amount to suggest for paper trade.

    Returns
    -------
    InvestmentDecision
    """
    settings = load_settings()
    conn = get_connection(settings.database.path)

    # Compute confluence from multiple timeframes (1h, 4h, 1d)
    timeframes = ["1h", "4h", "1d"]
    tf_results = []
    for tf in timeframes:
        result = analyze_timeframe(conn, symbol, tf)
        if result is not None:
            tf_results.append(result)
    confluence = compute_confluence(tf_results)
    recommendation_cfg = settings.prospecting.get("recommendation", {})

    # 1. Check if trading is allowed at all (kill switch, mode)
    allowed, blocking_rule = _is_trading_allowed(settings)
    if not allowed:
        # Still compute recommendation and price for informational purposes.
        recommendation_obj = get_recommendation(
            score=score,
            confluence=confluence,
            invertir_threshold=recommendation_cfg.get("invertir_threshold", 0.75),
            vigilat_threshold=recommendation_cfg.get("vigilar_threshold", 0.60),
            neutral_threshold=recommendation_cfg.get("neutral_threshold", 0.40),
            min_confluence_invertir=recommendation_cfg.get("min_confluence_for_invertir", 2),
            min_confluence_vigilat=recommendation_cfg.get("min_confluence_for_vigilar", 1),
        )
        current_price = _get_current_price(conn, symbol) or 0.0
        quantity = suggested_amount_usdt / current_price if current_price > 0 else 0.0
        return InvestmentDecision(
            approved=False,
            recommendation=recommendation_obj.label,
            action=None,
            reason=f"Trading not allowed: {blocking_rule}",
            blocking_rule=blocking_rule,
            suggested_amount_usdt=suggested_amount_usdt,
            score=score,
            confluence=confluence,
            current_price=current_price,
            quantity=quantity,
        )

    # 2. Get recommendation from scoring (uses thresholds from settings)
    recommendation_obj = get_recommendation(
        score=score,
        confluence=confluence,
        invertir_threshold=recommendation_cfg.get("invertir_threshold", 0.75),
        vigilat_threshold=recommendation_cfg.get("vigilar_threshold", 0.60),
        neutral_threshold=recommendation_cfg.get("neutral_threshold", 0.40),
        min_confluence_invertir=recommendation_cfg.get("min_confluence_for_invertir", 2),
        min_confluence_vigilat=recommendation_cfg.get("min_confluence_for_vigilar", 1),
    )

    # 3. If not INVERTIR, we do not proceed to risk check; just log and return.
    if recommendation_obj.label != "INVERTIR":
        current_price = _get_current_price(conn, symbol) or 0.0
        quantity = suggested_amount_usdt / current_price if current_price > 0 else 0.0
        return InvestmentDecision(
            approved=False,
            recommendation=recommendation_obj.label,
            action=None,
            reason=f"Recommendation is {recommendation_obj.label}, not INVERTIR",
            blocking_rule=None,
            suggested_amount_usdt=suggested_amount_usdt,
            score=score,
            confluence=confluence,
            current_price=current_price,
            quantity=quantity,
        )

    # 4. For INVERTIR, we attempt to create a paper buy proposal and run risk checks.
    current_price = _get_current_price(conn, symbol) or 0.0
    if current_price <= 0:
        return InvestmentDecision(
            approved=False,
            recommendation=recommendation_obj.label,
            action=None,
            reason="Unable to fetch current price",
            blocking_rule="PRICE_UNAVAILABLE",
            suggested_amount_usdt=suggested_amount_usdt,
            score=score,
            confluence=confluence,
            current_price=0.0,
            quantity=0.0,
        )

    quantity = suggested_amount_usdt / current_price

    # Build a minimal portfolio state for risk checks (we could improve this).
    # For now, we assume no existing positions and full capital available.
    portfolio_state = PortfolioState(
        total_capital=settings.capital.initial_usdt,
        cash=settings.capital.initial_usdt,
        positions={},
        asset_classes={},
    )

    # Build trade proposal: we assume direction BUY.
    proposal = TradeProposal(
        symbol=symbol,
        direction="BUY",
        entry_price=current_price,
        capital=settings.capital.initial_usdt,  # risk manager uses capital to size position
        reason=f"Prospect score {score:.2f}, confluence {confluence}/3",
        confidence=score,  # use score as confidence proxy
    )

    # Initialize risk manager with settings from config.
    risk_manager = RiskManager(
        max_position_pct=settings.risk.max_position_size_pct,
        max_risk_per_trade_pct=settings.risk.max_risk_per_trade_pct,
        default_stop_loss_pct=settings.risk.default_stop_loss_pct,
        max_asset_pct=settings.risk.max_asset_exposure_pct,
        max_total_pct=settings.risk.max_total_exposure_pct,
        max_altcoin_pct=settings.risk.max_altcoin_exposure_pct,
        require_stop_loss=settings.risk.require_stop_loss,
        altcoin_symbols=set(settings.risk.altcoin_symbols),
    )

    # Evaluate the trade proposal.
    risk_decision = risk_manager.evaluate(proposal=proposal, portfolio=portfolio_state)

    # Log the decision regardless of outcome.
    log_decision(
        decision_type="PAPER_BUY_EVALUATION",
        symbol=symbol,
        strategy_name="prospecting",
        timeframe=interval,  # keep the original interval for logging
        mode=settings.trading.mode,
        approved=risk_decision.approved,
        reason=risk_decision.rejection_reason if not risk_decision.approved else "Approved by risk manager",
        input_data={
            "symbol": symbol,
            "score": score,
            "confluence": confluence,
            "suggested_amount_usdt": suggested_amount_usdt,
            "recommendation": recommendation_obj.label,
        },
        output_data={
            "approved": risk_decision.approved,
            "rejection_reason": risk_decision.rejection_reason,
            "suggested_quantity": quantity,
            "suggested_amount_usdt": suggested_amount_usdt,
        },
        policy_version=settings.policy.version if hasattr(settings, "policy") else None,
        strategy_version="1.0",  # placeholder
        settings=settings,
    )

    if risk_decision.approved:
        return InvestmentDecision(
            approved=True,
            recommendation=recommendation_obj.label,
            action="PAPER_BUY",
            reason="Approved by risk manager",
            blocking_rule=None,
            suggested_amount_usdt=suggested_amount_usdt,
            score=score,
            confluence=confluence,
            current_price=current_price,
            quantity=quantity,
        )
    else:
        return InvestmentDecision(
            approved=False,
            recommendation=recommendation_obj.label,
            action=None,
            reason=risk_decision.rejection_reason or "Rejected by risk manager",
            blocking_rule="RISK_REJECTED",
            suggested_amount_usdt=suggested_amount_usdt,
            score=score,
            confluence=confluence,
            current_price=current_price,
            quantity=quantity,
        )
