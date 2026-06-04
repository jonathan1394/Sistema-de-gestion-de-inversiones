"""Journal analysis endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request

from app.ai.journal_analyzer import generate_journal_report
from app.database.connection import get_connection
from app.paper_trading.storage import get_trades, init_portfolio_tables

router = APIRouter(prefix="/journal", tags=["journal"])


@router.get("/trades")
def list_trades(
    request: Request,
    symbol: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    s = request.app.state.settings
    conn = get_connection(s.database.path)
    init_portfolio_tables(conn)
    items = get_trades(conn, symbol=symbol, limit=limit)
    data = [
        {
            "id": t.id,
            "symbol": t.symbol,
            "interval": t.interval,
            "action": t.action,
            "quantity": t.quantity,
            "price": t.price,
            "commission": t.commission,
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct,
            "reason": t.reason,
            "created_at": t.created_at,
        }
        for t in items
    ]
    return {
        "status": "ok",
        "data": data,
        "error": None,
        "meta": {"count": len(data)},
    }


@router.post("/analyze")
def analyze_journal(request: Request, payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    """Analyze trade history and return a journal report with AI insights."""
    trades = payload.get("trades")
    if trades is None:
        s = request.app.state.settings
        conn = get_connection(s.database.path)
        init_portfolio_tables(conn)
        symbol = payload.get("symbol")
        limit = int(payload.get("limit", 500))
        items = get_trades(conn, symbol=symbol if symbol else None, limit=limit)
        trades = [
            {
                "action": t.action,
                "quantity": t.quantity,
                "price": t.price,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "reason": t.reason,
                "created_at": t.created_at,
            }
            for t in items
        ]

    if not trades:
        return {
            "status": "ok",
            "data": {
                "summary": "No trades available for analysis.",
                "trade_analysis": {
                    "total_trades": 0,
                    "win_rate": 0.0,
                    "profit_factor": 0.0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0,
                    "largest_win": 0.0,
                    "largest_loss": 0.0,
                    "avg_hold_time": 0.0,
                    "consecutive_wins": 0,
                    "consecutive_losses": 0,
                },
                "behavior": {"revenge_trading": False, "details": []},
                "insight": {
                    "weakness": "",
                    "suggestion": "Start trading to generate data for analysis.",
                },
            },
            "error": None,
            "meta": {},
        }

    try:
        report = generate_journal_report(trades)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {
        "status": "ok",
        "data": {
            "summary": report.summary,
            "trade_analysis": {
                "total_trades": report.trade_analysis.total_trades,
                "win_rate": round(report.trade_analysis.win_rate, 1),
                "profit_factor": round(report.trade_analysis.profit_factor, 2),
                "avg_win": round(report.trade_analysis.avg_win, 2),
                "avg_loss": round(report.trade_analysis.avg_loss, 2),
                "largest_win": round(report.trade_analysis.largest_win, 2),
                "largest_loss": round(report.trade_analysis.largest_loss, 2),
                "avg_hold_time": round(report.trade_analysis.avg_hold_time, 1),
                "consecutive_wins": report.trade_analysis.consecutive_wins,
                "consecutive_losses": report.trade_analysis.consecutive_losses,
            },
            "behavior": {
                "revenge_trading": report.behavior.revenge_trading,
                "closing_early": report.behavior.closing_early,
                "fomo_entries": report.behavior.fomo_entries,
                "details": report.behavior.details,
            },
            "insight": {
                "weakness": report.insight.weakness,
                "suggestion": report.insight.suggestion,
            },
        },
        "error": None,
        "meta": {},
    }
