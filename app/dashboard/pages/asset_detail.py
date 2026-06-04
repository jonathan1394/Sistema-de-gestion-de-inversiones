"""Asset detail dashboard with multi-timeframe and backtest views."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from loguru import logger

from app.ai.market_summary import generate_market_summary
from app.backtesting.comparator import compare_strategies
from app.config import load_settings
from app.dashboard.helpers import candles_to_dataframe, compute_confluence, get_current_price
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.governance.decision_engine import evaluate_investment_decision
from app.paper_trading.storage import record_trade, upsert_position
from app.prospecting.db import get_all_prospects, get_prospect
from app.prospecting.scoring import get_recommendation


def analyze_timeframe(conn, symbol: str, interval: str) -> dict | None:
    """Summarize one timeframe for the selected symbol."""
    candles = get_candles(
        connection=conn,
        symbol=symbol,
        interval=interval,
        limit=200,
        desc=True,
    )
    if not candles or len(candles) < 50:
        return None
    data = pd.DataFrame(
        {
            "timestamp": pd.to_datetime([c.open_time for c in candles], unit="ms", utc=True),
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        }
    )
    try:
        summary = generate_market_summary(data, symbol=symbol, period=interval)
    except (ValueError, KeyError):
        logger.exception("Error generating market summary for %s %s", symbol, interval)
        return None
    return {
        "interval": interval,
        "price": summary.close_price,
        "return_pct": summary.return_pct,
        "trend": summary.condition.trend,
        "volatility": summary.condition.volatility,
        "rsi": summary.condition.rsi_condition,
        "volume": summary.condition.volume_profile,
        "summary_text": summary.condition.summary,
        "key_levels": summary.key_levels,
        "volatility_pct": summary.volatility_pct,
    }


def _rec_badge(label: str) -> str:
    tone = {
        "INVERTIR": "badge-pos",
        "VIGILAR": "badge-warn",
        "NEUTRAL": "badge-neutral",
        "EVITAR": "badge-neg",
    }.get(label, "badge-neutral")
    return f'<span class="badge {tone}">{label}</span>'


def _render_overview(symbol: str, prospect, latest: dict, confluence: int) -> None:
    rec = get_recommendation(prospect.score if prospect else 0, confluence)
    st.subheader(f"{symbol} -- Overview")
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Price", f"${latest['price']:,.2f}", f"{latest['return_pct']:+.2f}%")
    col_b.metric("Score", f"{prospect.score:.4f}" if prospect else "N/A")
    col_c.markdown(
        f"<div style='margin-top:0.7rem'>{_rec_badge(rec.label)}</div>", unsafe_allow_html=True
    )
    col_d.metric("Status", (prospect.status if prospect else "unknown").capitalize())


def _render_confluence(results: list[dict]) -> None:
    confluence = compute_confluence(results)
    st.subheader(f"Multi-Timeframe -- Confluence {confluence}/3")
    label = "ALTA" if confluence >= 3 else "MEDIA" if confluence >= 2 else "BAJA"
    tone = "badge-pos" if confluence >= 3 else "badge-warn" if confluence >= 2 else "badge-neg"
    st.markdown(
        f"<div class='legend-row'><span class='badge {tone}'>CONFLUENCIA {label}</span></div>",
        unsafe_allow_html=True,
    )

    tf_rows = [
        {
            "TF": r["interval"],
            "Trend": r["trend"],
            "Return": f"{r['return_pct']:+.2f}%",
            "RSI": r["rsi"],
            "Volatility": f"{r['volatility']} ({r['volatility_pct']:.2f}%)",
            "Volume": r["volume"],
        }
        for r in results
    ]
    st.dataframe(pd.DataFrame(tf_rows), use_container_width=True, hide_index=True)


def _render_key_levels(results: list[dict]) -> None:
    st.divider()
    st.subheader("Key Levels")
    for r in results:
        with st.expander(
            f"{r['interval']} -- {r['summary_text']}", expanded=(r["interval"] == "4h")
        ):
            kl = r["key_levels"]
            kc1, kc2, kc3, kc4 = st.columns(4)
            kc1.metric("Support", f"${kl.get('support', 0):,.2f}")
            kc2.metric("Resistance", f"${kl.get('resistance', 0):,.2f}")
            kc3.metric("EMA 20", f"${kl.get('ema_20', 0):,.2f}")
            kc4.metric("EMA 50", f"${kl.get('ema_50', 0):,.2f}")


def _render_backtest_comparison(conn, symbol: str) -> None:
    st.divider()
    st.subheader("Backtest Comparison")
    if not st.button("Run Backtest Comparison", type="primary", use_container_width=True):
        return
    with st.spinner("Running backtests on all strategies..."):
        try:
            candles = get_candles(connection=conn, symbol=symbol, interval="4h", limit=500)
            if len(candles) < 50:
                st.warning("Insufficient data.")
                return
            data = candles_to_dataframe(candles)
            bt_result = compare_strategies(data=data, symbol=symbol, interval="4h")
            rows = [
                {
                    "Strategy": sr.strategy_name,
                    "ROI": f"{sr.metrics.roi_pct:+.2f}%",
                    "Sharpe": f"{sr.metrics.sharpe_ratio:.2f}",
                    "Max DD": f"{sr.metrics.max_drawdown_pct:.2f}%",
                    "PF": f"{sr.metrics.profit_factor:.2f}",
                    "Win Rate": f"{sr.metrics.win_rate:.1f}%",
                    "Trades": sr.metrics.total_trades,
                }
                for sr in bt_result.strategy_results
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            best = bt_result.best
            if best:
                st.success(
                    f"Best: **{best.strategy_name}** -- Sharpe {best.metrics.sharpe_ratio:.2f}, ROI {best.metrics.roi_pct:+.2f}%"
                )
        except Exception as e:
            st.error(f"Error: {e}")


def _render_paper_trading(conn, symbol: str, prospect, decision) -> None:
    """Render the paper trading execution section (extracted from render for complexity)."""
    st.divider()
    st.subheader("Operación Paper Trading")
    if prospect:
        st.caption(
            f"Score: {prospect.score:.4f} | Recomendación: {decision.recommendation} | Confluencia: {decision.confluence}/3"
        )
    else:
        st.caption(
            "Este símbolo no está en tu lista de prospectos. Agregarlo primero en la página de Prospectos."
        )

    if decision.action == "PAPER_BUY" and decision.approved:
        st.success("Esta operación está **aprobada** para ejecución paper.")
        amount_input = st.number_input(
            f"Monto a invertir (USDT) para {symbol}",
            min_value=0.0,
            value=decision.suggested_amount_usdt,
            step=1.0,
            help="Ingresa el monto en USDT que deseas invertir en esta operación paper.",
        )
        if st.button("Ejecutar operación paper", type="primary", use_container_width=True):
            if amount_input <= 0:
                st.error("El monto debe ser mayor que cero.")
            else:
                _execute_paper_buy(conn, symbol, prospect, amount_input)
    elif decision.action == "PAPER_BUY" and not decision.approved:
        st.warning(
            f"Esta operación está **rechazada** por gestión de riesgo: {decision.reason} "
            f"(Bloqueo: {decision.blocking_rule})"
        )
    else:
        st.info(
            f"Esta operación no está disponible para paper trading actual. "
            f"Recomendación: {decision.reason}"
        )


def _execute_paper_buy(conn, symbol: str, prospect, amount_input: float) -> None:
    """Execute a paper buy after re-evaluating risk with the user-provided amount."""
    updated_decision = evaluate_investment_decision(
        symbol=symbol,
        interval="1d",
        score=prospect.score if prospect else 0.0,
        suggested_amount_usdt=amount_input,
    )
    if updated_decision.approved and updated_decision.action == "PAPER_BUY":
        try:
            price = get_current_price(conn, symbol)
            if price is None or price <= 0:
                st.error("No se pudo obtener el precio actual para ejecutar la operación.")
                return
            quantity = amount_input / price
            trade = record_trade(
                connection=conn,
                symbol=symbol,
                action="BUY",
                quantity=quantity,
                price=price,
                commission=0.0,
                pnl=0.0,
                pnl_pct=0.0,
                reason=f"Paper trade from asset detail: score {prospect.score:.2f}, confluence {updated_decision.confluence}/3",
                interval="1d",
            )
            upsert_position(
                connection=conn,
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                current_price=price,
                entry_time=trade.created_at,
            )
            st.success(
                f"Operación paper ejecutada: {quantity:.6f} {symbol} a ${price:,.2f} USDT. "
                f"Trade ID: {trade.id}"
            )
            st.rerun()
        except Exception as e:
            st.error(f"Error al ejecutar la operación paper: {e}")
    else:
        st.error(
            f"Operación rechazada por gestión de riesgo: {updated_decision.reason} "
            f"(Bloqueo: {updated_decision.blocking_rule})"
        )


def render() -> None:
    """Render consolidated per-asset analysis and comparison sections."""
    st.markdown('<div class="page-title">Asset Detail</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Vista consolidada de mercado, score, riesgo y backtesting por activo.</div>',
        unsafe_allow_html=True,
    )

    try:
        config = load_settings()
        conn = get_connection(config.database.path)
        prospects = get_all_prospects(conn)
        symbol_list = (
            [p.symbol for p in prospects] if prospects else ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        )
        symbol = st.selectbox("Symbol", list(dict.fromkeys(symbol_list))).upper()

        if not symbol:
            st.info("Select a symbol to begin.")
            return

        prospect = get_prospect(conn, symbol)
        results = [
            r for tf in ["1h", "4h", "1d"] if (r := analyze_timeframe(conn, symbol, tf)) is not None
        ]
        if not results:
            st.warning(f"No data available for {symbol}. Download historical data first.")
            return

        decision = evaluate_investment_decision(
            symbol=symbol,
            interval="1d",
            score=prospect.score if prospect else 0.0,
            suggested_amount_usdt=50.0,
        )

        _render_overview(symbol, prospect, results[0], compute_confluence(results))
        st.divider()
        _render_confluence(results)
        _render_key_levels(results)
        _render_backtest_comparison(conn, symbol)

        _render_paper_trading(conn, symbol, prospect, decision)

        if st.button("Refresh", use_container_width=True):
            st.rerun()
    except Exception:
        logger.exception("Unhandled error in asset_detail render")
        st.error("An unexpected error occurred while rendering this page.")
