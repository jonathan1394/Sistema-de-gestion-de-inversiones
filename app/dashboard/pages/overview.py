"""Overview dashboard page summarizing market and system status."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import yaml

from app.config import load_settings
from app.dashboard.main import get_portfolio_value
from app.data.market_data import get_candles
from app.database.connection import get_connection


def _render_market_header(candles_4h: list, candles_1d: list) -> None:
    latest_price = candles_4h[-1].close if candles_4h else 0
    prev_price = candles_4h[-2].close if len(candles_4h) > 1 else latest_price
    change_24h = (latest_price - prev_price) / prev_price * 100 if prev_price else 0
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("BTC/USDT", f"${latest_price:,.2f}", f"{change_24h:+.2f}%", border=True)
    if candles_1d:
        vol_avg = sum(c.volume for c in candles_1d[-7:]) / 7 if len(candles_1d) >= 7 else 0
        col2.metric("Vol 7d (avg)", f"{vol_avg:,.0f}", border=True)
    else:
        col2.metric("Vol 7d (avg)", "--", border=True)
    high_30d = max(c.high for c in candles_1d) if candles_1d else 0
    low_30d = min(c.low for c in candles_1d) if candles_1d else 0
    range_pct = (high_30d - low_30d) / low_30d * 100 if low_30d else 0
    col3.metric("Rango 30d", f"${low_30d:,.0f} - ${high_30d:,.0f}", f"{range_pct:.1f}%", border=True)
    col4.metric("Valor Cartera", f"${get_portfolio_value():.2f}", border=True)


def _render_open_positions() -> None:
    st.subheader("Posiciones Abiertas")
    positions = st.session_state.get("portfolio_positions", {})
    if not positions:
        st.info("No hay posiciones abiertas actualmente.")
        return
    pos_data = [
        {
            "Symbol": sym,
            "Qty": f"{pos['quantity']:.6f}",
            "Entry": f"${pos['entry_price']:.2f}",
            "Price": f"${pos['current_price']:.2f}",
            "PnL": f"{pos['unrealized_pnl']:+.2f}",
            "PnL%": f"{pos['unrealized_pnl_pct']:+.2f}%",
        }
        for sym, pos in positions.items()
    ]
    st.dataframe(pd.DataFrame(pos_data), use_container_width=True, hide_index=True)


def _render_market_chart(candles_4h: list) -> None:
    st.subheader("Datos de Mercado (BTC/USDT)")
    if not candles_4h:
        st.info("Descarga datos con scripts/download_historical.py")
        return
    df = pd.DataFrame({
        "timestamp": pd.to_datetime([c.open_time for c in candles_4h], unit="ms", utc=True),
        "close": [c.close for c in candles_4h],
    })
    st.line_chart(df, x="timestamp", y="close")


def _render_system_status(config, candles_4h: list) -> None:
    st.subheader("Estado del Sistema")
    status_data = {
        "Modo": config.mode,
        "Kill Switch": "Activo" if config.kill_switch else "Inactivo",
        "Data DB": f"{len(candles_4h)} velas BTC 4h",
        "Ultima vela": str(candles_4h[-1].open_time) if candles_4h else "--",
        "Precio BTC": f"${candles_4h[-1].close:,.2f}" if candles_4h else "--",
    }
    for k, v in status_data.items():
        st.text(f"{k}: {v}")


def _render_risk_summary() -> None:
    st.subheader("Limites de Riesgo")
    try:
        with open("settings.yaml") as f:
            raw = yaml.safe_load(f) or {}
        risk = raw.get("risk", {})
        risk_data = {
            "Max por trade": f"{risk.get('max_position_size_pct', 0.03)*100:.1f}%",
            "Riesgo por trade": f"{risk.get('max_risk_per_trade_pct', 0.01)*100:.1f}%",
            "Stop loss por defecto": f"{risk.get('default_stop_loss_pct', 0.02)*100:.1f}%",
        }
    except Exception:
        risk_data = {"Max por trade": "3.0%", "Riesgo por trade": "1.0%", "Stop loss": "2.0%"}
    for k, v in risk_data.items():
        st.text(f"{k}: {v}")


def render() -> None:
    """Render high-level market, portfolio, and system overview panels."""
    st.markdown('<div class="page-title">Dashboard Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Resumen del estado del sistema y cartera.</div>', unsafe_allow_html=True)

    config = load_settings()
    conn = get_connection(config.database.path)
    candles_4h = get_candles(conn, "BTCUSDT", "4h", limit=100, desc=True)
    candles_1d = get_candles(conn, "BTCUSDT", "1d", limit=30, desc=True)

    _render_market_header(candles_4h, candles_1d)
    st.divider()

    left, right = st.columns(2)
    with left:
        _render_open_positions()
    with right:
        _render_market_chart(candles_4h)

    st.divider()
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        _render_system_status(config, candles_4h)
    with col_b:
        _render_risk_summary()
    with col_c:
        st.subheader("Resumen de Estrategias")
        st.info("Ejecuta backtests en la seccion Backtesting.")
        if st.button("Ir a Backtesting", use_container_width=True):
            st.session_state.page = "Backtesting"
            st.rerun()
