"""Market analysis dashboard page with timeframe confluence."""

from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from app.ai.market_summary import generate_market_summary
from app.config import load_settings
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.prospecting.db import add_prospect, get_prospect

logger = logging.getLogger(__name__)


def analyze_timeframe(conn, symbol: str, interval: str) -> dict | None:
    """Build summary metrics for one timeframe if data is sufficient."""
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


TREND_ORDER = {"strong_up": 5, "up": 4, "sideways": 3, "down": 2, "strong_down": 1}


def compute_confluence(results: list[dict]) -> int:
    """Return number of bullish trends across timeframe results."""
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


def _render_confluence_header(symbol: str, confluence: int) -> None:
    if confluence >= 3:
        label = "FUERTE"
    elif confluence >= 2:
        label = "MODERADA"
    else:
        label = "DEBIL"
    tone = "badge-pos" if confluence >= 3 else "badge-warn" if confluence >= 2 else "badge-neg"
    st.subheader(f"{symbol} - Confluencia: {confluence}/3")
    st.markdown(
        f"<div class='legend-row'>{_badge(label, tone)} {_badge('MOMENTUM', 'badge-neutral')}</div>",
        unsafe_allow_html=True,
    )


def _render_tf_table(results: list[dict]) -> None:
    rows = [
        {
            "Timeframe": r["interval"],
            "Trend": f"{TREND_COLORS.get(r['trend'], '')} {r['trend']}",
            "Return": f"{r['return_pct']:+.2f}%",
            "Volatility": f"{r['volatility']} ({r['volatility_pct']:.2f}%)",
            "RSI": r["rsi"],
            "Volume": r["volume"],
        }
        for r in results
    ]
    st.subheader("Timeframe Comparison")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_key_levels(results: list[dict]) -> None:
    st.divider()
    st.subheader("Key Levels by Timeframe")
    for r in results:
        with st.expander(f"{r['interval']} - {r['summary_text']}", expanded=(r["interval"] == "4h")):
            kl = r["key_levels"]
            kcol1, kcol2, kcol3, kcol4 = st.columns(4)
            kcol1.metric("Soporte", f"${kl.get('support', 0):,.2f}")
            kcol2.metric("Resistencia", f"${kl.get('resistance', 0):,.2f}")
            kcol3.metric("EMA 20", f"${kl.get('ema_20', 0):,.2f}")
            kcol4.metric("EMA 50", f"${kl.get('ema_50', 0):,.2f}")


def render() -> None:
    """Render market analysis inputs, tables, and key levels."""
    st.markdown('<div class="page-title">Market Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Analisis multi-timeframe para detectar tendencia, confluencia y niveles clave.</div>', unsafe_allow_html=True)

    config = load_settings()
    conn = get_connection(config.database.path)

    # Input symbol
    symbol = st.text_input("Symbol", value="BTCUSDT").strip().upper()

    if not symbol:
        st.info("Enter a symbol to begin analysis.")
        return

    # Check if symbol is in prospects and get score
    prospect = get_prospect(conn, symbol) if symbol else None
    if prospect:
        st.caption(f"Este símbolo está en tu lista de prospectos con score {prospect.score:.4f} y estado {prospect.status}.")
    else:
        st.caption("Este símbolo no está en tu lista de prospectos. Puedes agregarlo abajo.")

    # Button to add to prospects
    if st.button("Agregar a Prospectos", use_container_width=True):
        if symbol:
            try:
                add_prospect(conn, symbol)
                st.success(f"Símbolo {symbol} agregado a prospectos.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al agregar a prospectos: {e}")
                logger.exception("Error adding prospect %s", symbol)
        else:
            st.warning("Ingrese un símbolo válido.")

    st.divider()

    # Run analysis
    results = [r for tf in ["1h", "4h", "1d"] if (r := analyze_timeframe(conn, symbol, tf)) is not None]
    if not results:
        st.warning(f"No data available for {symbol}. Download historical data first.")
        return

    confluence = compute_confluence(results)
    _render_confluence_header(symbol, confluence)

    latest = results[0] if results[0]["interval"] == "1h" else results[-1]
    st.metric("Precio Actual", f"${latest['price']:,.2f}", f"{latest['return_pct']:+.2f}%")
    st.divider()
    _render_tf_table(results)
    _render_key_levels(results)
    st.divider()

    st.subheader("Multi-Timeframe Summary")
    summary_parts = [f"**{r['interval']}**: {r['summary_text']}" for r in results]
    st.markdown("  \n".join(summary_parts))

    # Option to run screener for this symbol only
    if st.button("Ejecutar Screener para este símbolo", use_container_width=True):
        with st.spinner(f"Analizando {symbol}..."):
            try:
                from app.data.binance_client import BinanceClient
                from app.prospecting.screener import ProspectScreener
                weights = config.prospecting.get("scoring_weights")
                client = BinanceClient(config.binance)
                screener = ProspectScreener(
                    client=client,
                    connection=conn,
                    weights=weights,
                )
                result = screener.run_on_symbol(symbol)
                if result:
                    st.success(f"Screener completado. Score: {result.score.total:.4f}")
                    st.rerun()
                else:
                    st.warning(f"No se pudo analizar {symbol}. Verifique que haya suficientes datos.")
            except Exception as e:
                st.error(f"Error al ejecutar screener: {e}")
                logger.exception("Error running screener for %s", symbol)

    if st.button("Refresh Analysis", use_container_width=True):
        st.rerun()
