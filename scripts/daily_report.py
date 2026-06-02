#!/usr/bin/env python3
"""Daily report generator for CriptoLab.

Generates a comprehensive daily report including:
- Updated asset rankings
- Multi-timeframe analysis of main assets
- Paper trading portfolio status
- Active signals
- Daily alerts
- Action suggestions
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.config import load_settings
from app.data.binance_client import BinanceClient
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.governance.decision_engine import evaluate_investment_decision
from app.prospecting.db import get_all_prospects
from app.prospecting.ranking import AssetRanking, generate_ranking
from app.prospecting.market_decision import analyze_timeframe, compute_confluence
from app.paper_trading.storage import get_all_positions, get_trades
from app.ai.market_summary import generate_market_summary


def _get_latest_price(conn, symbol: str) -> Optional[float]:
    """Get the latest close price for a symbol."""
    for interval in ("1h", "4h", "1d"):
        candles = get_candles(
            connection=conn,
            symbol=symbol,
            interval=interval,
            limit=1,
            desc=True,
        )
        if candles and len(candles) > 0:
            return float(candles[0].close)
    return None


def _get_portfolio_summary(conn) -> Dict[str, Any]:
    """Get summary of paper trading portfolio."""
    positions = get_all_positions(conn)
    trades = get_trades(conn, limit=100)  # Get recent trades
    
    total_value = 0.0
    total_cost = 0.0
    total_pnl = 0.0
    
    for pos in positions:
        latest_price = _get_latest_price(conn, pos.symbol) or pos.current_price
        market_value = pos.quantity * latest_price
        cost_basis = pos.quantity * pos.entry_price
        pnl = market_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
        
        total_value += market_value
        total_cost += cost_basis
        total_pnl += pnl
    
    # Calculate cash (simplified - in reality this should come from portfolio snapshots)
    settings = load_settings()
    initial_capital = settings.capital.initial_usdt
    cash = initial_capital - total_cost  # This is approximate
    
    return {
        "total_value": total_value,
        "cash": cash,
        "total_cost": total_cost,
        "total_pnl": total_pnl,
        "total_pnl_pct": (total_pnl / total_cost * 100) if total_cost > 0 else 0.0,
        "positions_count": len(positions),
        "recent_trades_count": len(trades),
        "positions": [
            {
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
                "current_price": _get_latest_price(conn, pos.symbol) or pos.current_price,
                "unrealized_pnl": (_get_latest_price(conn, pos.symbol) or pos.current_price - pos.entry_price) * pos.quantity,
                "unrealized_pnl_pct": ((_get_latest_price(conn, pos.symbol) or pos.current_price) / pos.entry_price - 1) * 100 if pos.entry_price > 0 else 0.0,
            }
            for pos in positions
        ]
    }


def _get_top_rankings(limit: int = 10) -> List[AssetRanking]:
    """Get top ranked assets."""
    settings = load_settings()
    conn = get_connection(settings.database.path)
    prospects = get_all_prospects(conn)
    rankings = generate_ranking(prospects)
    return rankings[:limit]


def _get_market_analysis(symbols: List[str]) -> Dict[str, Any]:
    """Get multi-timeframe analysis for a list of symbols."""
    settings = load_settings()
    conn = get_connection(settings.database.path)
    
    analysis = {}
    for symbol in symbols:
        results = []
        for tf in ["1h", "4h", "1d"]:
            result = analyze_timeframe(conn, symbol, tf)
            if result:
                results.append(result)
        
        if results:
            confluence = compute_confluence(results)
            latest = results[0] if results[0]["interval"] == "1h" else results[-1]
            
            analysis[symbol] = {
                "price": latest["price"],
                "return_pct": latest["return_pct"],
                "confluence": confluence,
                "trend_1h": next((r["trend"] for r in results if r["interval"] == "1h"), None),
                "trend_4h": next((r["trend"] for r in results if r["interval"] == "4h"), None),
                "trend_1d": next((r["trend"] for r in results if r["interval"] == "1d"), None),
                "volatility": latest["volatility"],
                "rsi": latest["rsi"],
                "volume": latest["volume"],
                "summary_text": latest["summary_text"],
                "key_levels": latest["key_levels"],
            }
    
    return analysis


def _get_recent_decisions(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent investment decisions."""
    from app.governance.decision_log import get_recent_decisions
    
    decisions = get_recent_decisions(limit=limit)
    return [
        {
            "decision_id": d.decision_id,
            "timestamp": d.timestamp,
            "datetime": datetime.fromtimestamp(int(d.timestamp) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "type": d.decision_type,
            "symbol": d.symbol,
            "strategy": d.strategy_name,
            "mode": d.mode,
            "approved": d.approved,
            "reason": d.reason,
        }
        for d in decisions
    ]


def _get_active_signals() -> List[Dict[str, Any]]:
    """Get active trading signals (simplified)."""
    # This would typically come from a signals table or active strategies
    # For now, we'll return prospects with high scores as "signals"
    settings = load_settings()
    conn = get_connection(settings.database.path)
    prospects = get_all_prospects(conn)
    
    signals = []
    for prospect in prospects:
        if prospect.score >= 0.6:  # High score threshold
            signals.append({
                "symbol": prospect.symbol,
                "score": prospect.score,
                "trend": prospect.trend,
                "volume": prospect.volume_profile,
                "rsi": prospect.rsi_condition,
                "signals_count": prospect.signals_count,
            })
    
    # Sort by score descending
    signals.sort(key=lambda x: x["score"], reverse=True)
    return signals[:10]  # Top 10 signals


def _generate_action_suggestions(
    rankings: List[AssetRanking],
    portfolio: Dict[str, Any],
    signals: List[Dict[str, Any]]
) -> List[str]:
    """Generate action suggestions based on analysis."""
    suggestions = []
    
    # Check for strong buy opportunities
    strong_buys = [r for r in rankings if r.recommendation == "INVERTIR"]
    if strong_buys:
        top_buy = strong_buys[0]
        suggestions.append(
            f"🟢 COMPRAR: {top_buy.symbol} tiene la mejor recomendación "
            f"(Score: {top_buy.score:.2f}, Confluencia: {top_buy.confluence}/3)"
        )
    
    # Check for assets to watch
    watch_list = [r for r in rankings if r.recommendation == "VIGILAR"]
    if watch_list:
        suggestions.append(
            f"🟡 VIGILAR: {len(watch_list)} activos en espera de confirmación"
        )
    
    # Check for assets to avoid
    avoid_list = [r for r in rankings if r.recommendation == "EVITAR"]
    if avoid_list:
        suggestions.append(
            f"🔴 EVITAR: {len(avoid_list)} activos muestran señales débiles"
        )
    
    # Portfolio-based suggestions
    if portfolio["total_pnl_pct"] < -5:
        suggestions.append(
            f"⚠️ CARTERA: Pérdida del {abs(portfolio['total_pnl_pct']):.1f}% "
            f"considera revisar tu estrategia"
        )
    elif portfolio["total_pnl_pct"] > 10:
        suggestions.append(
            f"📈 CARTERA: Ganancia del {portfolio['total_pnl_pct']:.1f}% "
            f"mantén disciplina y considera tomar ganancias parciales"
        )
    
    # Signal-based suggestions
    high_confidence_signals = [s for s in signals if s["score"] >= 0.75]
    if high_confidence_signals:
        top_signal = high_confidence_signals[0]
        suggestions.append(
            f"📊 SEÑAL: {top_signal['symbol']} muestra alta confianza "
            f"(Score: {top_signal['score']:.2f})"
        )
    
    if not suggestions:
        suggestions.append("📊 MANTENER: Condiciones de mercado mixtas, espera mejores oportunidades")
    
    return suggestions


def generate_daily_report() -> Dict[str, Any]:
    """Generate the complete daily report."""
    settings = load_settings()
    conn = get_connection(settings.database.path)
    
    # Get main assets from settings or default to major pairs
    main_assets = getattr(settings.symbols, '__root__', settings.symbols) if hasattr(settings, 'symbols') else ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    # Generate report components
    rankings = _get_top_rankings(limit=20)
    portfolio = _get_portfolio_summary(conn)
    market_analysis = _get_market_analysis(main_assets)
    recent_decisions = _get_recent_decisions(limit=10)
    active_signals = _get_active_signals()
    action_suggestions = _generate_action_suggestions(rankings, portfolio, active_signals)
    
    # Build final report
    report = {
        "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "report_time_utc": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "summary": {
            "total_assets_analyzed": len(get_all_prospects(conn)),
            "paper_trading_enabled": settings.trading.mode == "paper",
            "kill_switch_active": settings.app.kill_switch,
            "market_regime": "unknown",  # TODO: implement market regime detection
        },
        "rankings": [
            {
                "rank": idx + 1,
                "symbol": rank.symbol,
                "score": rank.score,
                "recommendation": rank.recommendation,
                "confluence": rank.confluence,
                "reason": rank.reason,
                "price": rank.price,
                "return_1d": rank.return_pct_1d,
                "trend_1h": rank.trend_1h,
                "trend_4h": rank.trend_4h,
                "trend_1d": rank.trend_1d,
            }
            for idx, rank in enumerate(rankings)
        ],
        "portfolio": portfolio,
        "market_analysis": market_analysis,
        "recent_decisions": recent_decisions,
        "active_signals": active_signals,
        "action_suggestions": action_suggestions,
    }
    
    return report


def _save_report_to_files(report: Dict[str, Any], base_name: str = "daily_report") -> Dict[str, str]:
    """Save report to JSON and Markdown files."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename_base = f"{base_name}_{timestamp}"
    
    # Save JSON
    json_path = Path(f"./reports/daily/{filename_base}.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Save Markdown
    md_path = Path(f"./reports/daily/{filename_base}.md")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    
    md_content = _generate_markdown_report(report)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    return {
        "json": str(json_path),
        "markdown": str(md_path),
        "filename_base": filename_base
    }


def _generate_markdown_report(report: Dict[str, Any]) -> str:
    """Generate a human-readable Markdown report."""
    md = f"""# Reporte Diario de CriptoLab
**Fecha:** {report['report_date']}
**Hora:** {report['report_time_utc']}

## Resumen Ejecutivo
- **Activos analizados:** {report['summary']['total_assets_analyzed']}
- **Modo de trading:** {'Paper Trading' if report['summary']['paper_trading_enabled'] else 'Solo Análisis'}
- **Kill Switch:** {'Activado' if report['summary']['kill_switch_active'] else 'Desactivado'}
- **Régimen de mercado:** {report['summary']['market_regime']}

## Rankings de Activos (Top 10)
| Rank | Símbolo | Recomendación | Score | Confluencia | Precio (USDT) | Retorno 1d |
|------|---------|---------------|-------|-------------|---------------|------------|
"""
    
    for rank in report["rankings"][:10]:
        md += f"| {rank['rank']} | {rank['symbol']} | {rank['recommendation']} | {rank['score']:.2f} | {rank['confluence']}/3 | "
        md += f"{rank['price']:,.2f} | {rank['return_1d']:+.2f}% |\n"
    
    md += "\n## Estado de la Carta Paper\n"
    portfolio = report["portfolio"]
    md += f"""- **Valor total:** ${portfolio['total_value']:,.2f}
- **Efectivo disponible:** ${portfolio['cash']:,.2f}
- **Costo total:** ${portfolio['total_cost']:,.2f}
- **PnL total:** ${portfolio['total_pnl']:,.2f} ({portfolio['total_pnl_pct']:+.2f}%)
- **Posiciones activas:** {portfolio['positions_count']}
- **Operaciones recientes:** {portfolio['recent_trades_count']}

### Posiciones Actuales
"""
    
    if portfolio["positions"]:
        md += "| Símbolo | Cantidad | Precio Entrada | Precio Actual | PnL No Realizado | PnL % |\n"
        md += "|---------|----------|----------------|---------------|------------------|--------|\n"
        for pos in portfolio["positions"]:
            md += f"| {pos['symbol']} | {pos['quantity']:.6f} | ${pos['entry_price']:,.2f} | ${pos['current_price']:,.2f} | ${pos['unrealized_pnl']:,.2f} | {pos['unrealized_pnl_pct']:+.2f}% |\n"
    else:
        md += "*No hay posiciones activas*\n"
    
    md += "\n## Análisis de Mercado\n"
    for symbol, analysis in report["market_analysis"].items():
        md += f"### {symbol}\n"
        md += f"- **Precio:** ${analysis['price']:,.2f} ({analysis['return_pct']:+.2f}%)\n"
        md += f"- **Confluencia:** {analysis['confluence']}/3\n"
        md += f"- **Tendencia:** 1h={analysis['trend_1h'] or '-'}, 4h={analysis['trend_4h'] or '-'}, 1d={analysis['trend_1d'] or '-'}\n"
        md += f"- **RSI:** {analysis['rsi'] or '-'}\n"
        md += f"- **Volatilidad:** {analysis['volatility'] or '-'}\n"
        md += f"- **Volumen:** {analysis['volume'] or '-'}\n"
        if analysis.get("key_levels"):
            kl = analysis["key_levels"]
            md += f"- **Niveles clave:** Soporte ${kl.get('support', 0):,.2f}, Resistencia ${kl.get('resistance', 0):,.2f}\n"
        md += "\n"
    
    md += "## Señales Activas\n"
    if report["active_signals"]:
        for signal in report["active_signals"][:5]:  # Top 5
            md += f"- **{signal['symbol']}:** Score {signal['score']:.2f}, "
            md += f"Tendencia {signal['trend'] or '-'}, "
            md += f"RSI {signal['rsi'] or '-'}\n"
    else:
        md += "*No hay señales activas*\n"
    
    md += "\n## Decisiones Recientes\n"
    if report["recent_decisions"]:
        for decision in report["recent_decisions"][:5]:  # Last 5
            status = "✅ APROBADA" if decision["approved"] else "❌ RECHAZADA"
            md += f"- **{decision['datetime']}** {decision['symbol']} "
            md += f"({decision['type']}): {status} - {decision['reason']}\n"
    else:
        md += "*No hay decisiones recientes*\n"
    
    md += "\n## Sugerencias de Acción\n"
    for suggestion in report["action_suggestions"]:
        md += f"- {suggestion}\n"
    
    md += f"\n---\n*Reporte generado automáticamente por CriptoLab*\n"
    
    return md


def main():
    """Main function to generate and save the daily report."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate daily CriptoLab report")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./reports/daily",
        help="Directory to save the report files"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Only print report to stdout, do not save files"
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "both"],
        default="both",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    print("Generando reporte diario...")
    report = generate_daily_report()
    
    if args.no_save:
        if args.format in ["json", "both"]:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        if args.format in ["markdown", "both"]:
            print(_generate_markdown_report(report))
        return
    
    # Save files
    saved_files = _save_report_to_files(report)
    
    print(f"Reporte diario generado:")
    print(f"  JSON: {saved_files['json']}")
    print(f"  Markdown: {saved_files['markdown']}")
    
    # Send via Telegram if configured
    try:
        settings = load_settings()
        telegram_cfg = settings.get("alerts", {}).get("notifications", {}).get("telegram", {})
        if telegram_cfg.get("enabled", False):
            bot_token = telegram_cfg.get("bot_token", "")
            chat_id = telegram_cfg.get("chat_id", "")
            if bot_token and chat_id:
                from app.alerts.channels import TelegramChannel
                telegram = TelegramChannel(bot_token, chat_id)
                # Send JSON report
                if saved_files.get("json"):
                    caption = f"Reporte diario de CriptoLab - {report['report_date']}"
                    telegram.send_document(saved_files["json"], caption)
                # Also send markdown as fallback if JSON fails
                if saved_files.get("markdown"):
                    caption = f"Reporte diario de CriptoLab (Markdown) - {report['report_date']}"
                    telegram.send_document(saved_files["markdown"], caption)
    except Exception as e:
        print(f"Warning: Could not send Telegram report: {e}")


if __name__ == "__main__":
    main()