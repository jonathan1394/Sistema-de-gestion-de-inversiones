from __future__ import annotations

import pandas as pd
import streamlit as st

from app.ai.market_summary import generate_market_summary
from app.backtesting.comparator import compare_strategies
from app.config import load_settings
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.prospecting.db import get_all_prospects, get_prospect
from app.prospecting.scoring import get_recommendation


def analyze_timeframe(conn, symbol: str, interval: str) -> dict | None:
    candles = get_candles(
        connection=conn, symbol=symbol, interval=interval, limit=200, desc=True,
    )
    if not candles or len(candles) < 50:
        return None
    data = pd.DataFrame({
        "timestamp": pd.to_datetime([c.open_time for c in candles], unit="ms", utc=True),
        "open": [c.open for c in candles],
        "high": [c.high for c in candles],
        "low": [c.low for c in candles],
        "close": [c.close for c in candles],
        "volume": [c.volume for c in candles],
    })
    try:
        summary = generate_market_summary(data, symbol=symbol, period=interval)
    except (ValueError, KeyError):
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


TREND_ORDER = {"strong_up": 5, "up": 4, "sideways": 3, "down": 2, "strong_down": 1}


def compute_confluence(results: list[dict]) -> int:
    return sum(1 for r in results if TREND_ORDER.get(r.get("trend", "sideways"), 3) >= 4)


def _rec_badge(label: str) -> str:
    tone = {
        "INVERTIR": "badge-pos",
        "VIGILAR": "badge-warn",
        "NEUTRAL": "badge-neutral",
        "EVITAR": "badge-neg",
    }.get(label, "badge-neutral")
    return f'<span class="badge {tone}">{label}</span>'


def render() -> None:
    st.markdown('<div class="page-title">🧾 Asset Detail</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Vista consolidada de mercado, score, riesgo y backtesting por activo.</div>',
        unsafe_allow_html=True,
    )

    config = load_settings()
    conn = get_connection(config.database.path)

    prospects = get_all_prospects(conn)
    symbol_list = [p.symbol for p in prospects] if prospects else ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    unique_symbols = list(dict.fromkeys(symbol_list))

    col1, col2 = st.columns([1, 3])
    with col1:
        symbol = st.selectbox("Symbol", unique_symbols).upper()
    with col2:
        pass

    if not symbol:
        st.info("Select a symbol to begin.")
        return

    prospect = get_prospect(conn, symbol)

    timeframes = ["1h", "4h", "1d"]
    results = []
    for tf in timeframes:
        r = analyze_timeframe(conn, symbol, tf)
        if r is not None:
            results.append(r)

    if not results:
        st.warning(f"No data available for {symbol}. Download historical data first.")
        return

    st.subheader(f"{symbol} — Overview")
    latest = results[0]
    rec = get_recommendation(prospect.score if prospect else 0, compute_confluence(results))

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("Price", f"${latest['price']:,.2f}", f"{latest['return_pct']:+.2f}%")
    with col_b:
        st.metric("Score", f"{prospect.score:.4f}" if prospect else "N/A")
    with col_c:
        st.markdown(f"<div style='margin-top:0.7rem'>{_rec_badge(rec.label)}</div>", unsafe_allow_html=True)
    with col_d:
        status = prospect.status if prospect else "unknown"
        st.metric("Status", status.capitalize())

    st.divider()

    confluence = compute_confluence(results)
    st.subheader(f"Multi-Timeframe — Confluence {confluence}/3")
    conf_label = "ALTA" if confluence >= 3 else "MEDIA" if confluence >= 2 else "BAJA"
    conf_tone = "badge-pos" if confluence >= 3 else "badge-warn" if confluence >= 2 else "badge-neg"
    st.markdown(f"<div class='legend-row'><span class='badge {conf_tone}'>CONFLUENCIA {conf_label}</span></div>", unsafe_allow_html=True)

    tf_rows = []
    for r in results:
        tf_rows.append({
            "TF": r["interval"],
            "Trend": r["trend"],
            "Return": f"{r['return_pct']:+.2f}%",
            "RSI": r["rsi"],
            "Volatility": f"{r['volatility']} ({r['volatility_pct']:.2f}%)",
            "Volume": r["volume"],
        })
    st.dataframe(pd.DataFrame(tf_rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Key Levels")

    for r in results:
        with st.expander(f"{r['interval']} — {r['summary_text']}", expanded=(r["interval"] == "4h")):
            kl = r["key_levels"]
            kc1, kc2, kc3, kc4 = st.columns(4)
            kc1.metric("Support", f"${kl.get('support', 0):,.2f}")
            kc2.metric("Resistance", f"${kl.get('resistance', 0):,.2f}")
            kc3.metric("EMA 20", f"${kl.get('ema_20', 0):,.2f}")
            kc4.metric("EMA 50", f"${kl.get('ema_50', 0):,.2f}")

    st.divider()
    st.subheader("Backtest Comparison")

    if st.button("Run Backtest Comparison", type="primary", use_container_width=True):
        with st.spinner("Running backtests on all strategies..."):
            try:
                candles = get_candles(
                    connection=conn, symbol=symbol, interval="4h", limit=500,
                )
                if len(candles) < 50:
                    st.warning("Insufficient data.")
                    return

                data = pd.DataFrame({
                    "timestamp": pd.to_datetime([c.open_time for c in candles], unit="ms", utc=True),
                    "open": [c.open for c in candles],
                    "high": [c.high for c in candles],
                    "low": [c.low for c in candles],
                    "close": [c.close for c in candles],
                    "volume": [c.volume for c in candles],
                })

                bt_result = compare_strategies(data=data, symbol=symbol, interval="4h")

                rows = []
                for sr in bt_result.strategy_results:
                    m = sr.metrics
                    rows.append({
                        "Strategy": sr.strategy_name,
                        "ROI": f"{m.roi_pct:+.2f}%",
                        "Sharpe": f"{m.sharpe_ratio:.2f}",
                        "Max DD": f"{m.max_drawdown_pct:.2f}%",
                        "PF": f"{m.profit_factor:.2f}",
                        "Win Rate": f"{m.win_rate:.1f}%",
                        "Trades": m.total_trades,
                    })

                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)

                best = bt_result.best
                if best:
                    st.success(
                        f"Best: **{best.strategy_name}** — "
                        f"Sharpe {best.metrics.sharpe_ratio:.2f}, "
                        f"ROI {best.metrics.roi_pct:+.2f}%"
                    )

            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("Refresh", use_container_width=True):
        st.rerun()
