from __future__ import annotations

import pandas as pd
import streamlit as st

from app.ai.market_summary import generate_market_summary
from app.config import load_settings
from app.data.market_data import get_candles
from app.database.connection import get_connection


def analyze_timeframe(conn, symbol: str, interval: str) -> dict | None:
    candles = get_candles(
        connection=conn,
        symbol=symbol,
        interval=interval,
        limit=200,
        desc=True,
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
    bullish = 0
    for r in results:
        t = r.get("trend", "sideways")
        if TREND_ORDER.get(t, 3) >= 4:
            bullish += 1
    return bullish


TREND_COLORS = {
    "strong_up": "🟢",
    "up": "📗",
    "sideways": "🟡",
    "down": "📕",
    "strong_down": "🔴",
}


def _badge(label: str, tone: str) -> str:
    return f'<span class="badge {tone}">{label}</span>'


def render() -> None:
    st.markdown('<div class="page-title">📈 Market Analysis</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Analisis multi-timeframe para detectar tendencia, confluencia y niveles clave.</div>',
        unsafe_allow_html=True,
    )

    config = load_settings()
    conn = get_connection(config.database.path)

    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("Symbol", value="BTCUSDT").strip().upper()
    with col2:
        pass

    if not symbol:
        st.info("Enter a symbol to begin analysis.")
        return

    timeframes = ["1h", "4h", "1d"]
    results = []
    for tf in timeframes:
        r = analyze_timeframe(conn, symbol, tf)
        if r is not None:
            results.append(r)

    if not results:
        st.warning(f"No data available for {symbol}. Download historical data first.")
        return

    confluence = compute_confluence(results)
    if confluence >= 3:
        confidence_label = "FUERTE"
    elif confluence >= 2:
        confidence_label = "MODERADA"
    else:
        confidence_label = "DEBIL"

    tone = "badge-pos" if confluence >= 3 else "badge-warn" if confluence >= 2 else "badge-neg"
    st.subheader(f"{symbol} — Confluencia: {confluence}/3")
    st.markdown(
        f"<div class='legend-row'>{_badge(confidence_label, tone)} {_badge('MOMENTUM', 'badge-neutral')}</div>",
        unsafe_allow_html=True,
    )

    if results:
        latest = results[0] if results[0]["interval"] == "1h" else results[-1]
        st.metric(
            "Precio Actual",
            f"${latest['price']:,.2f}",
            f"{latest['return_pct']:+.2f}%",
        )

    st.divider()

    rows = []
    for r in results:
        icon = TREND_COLORS.get(r["trend"], "➖")
        rows.append({
            "Timeframe": r["interval"],
            "Trend": f"{icon} {r['trend']}",
            "Return": f"{r['return_pct']:+.2f}%",
            "Volatility": f"{r['volatility']} ({r['volatility_pct']:.2f}%)",
            "RSI": r["rsi"],
            "Volume": r["volume"],
        })

    st.subheader("Timeframe Comparison")
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Key Levels by Timeframe")

    for r in results:
        with st.expander(f"{r['interval']} — {r['summary_text']}", expanded=(r["interval"] == "4h")):
            kl = r["key_levels"]
            kcol1, kcol2, kcol3, kcol4 = st.columns(4)
            kcol1.metric("Soporte", f"${kl.get('support', 0):,.2f}")
            kcol2.metric("Resistencia", f"${kl.get('resistance', 0):,.2f}")
            kcol3.metric("EMA 20", f"${kl.get('ema_20', 0):,.2f}")
            kcol4.metric("EMA 50", f"${kl.get('ema_50', 0):,.2f}")

    st.divider()

    st.subheader("Multi-Timeframe Summary")
    if results:
        summary_parts = []
        for r in results:
            summary_parts.append(f"**{r['interval']}**: {r['summary_text']}")
        st.markdown("  \n".join(summary_parts))

    if st.button("Refresh Analysis", use_container_width=True):
        st.rerun()
