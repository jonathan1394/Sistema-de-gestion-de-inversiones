"""Portfolio dashboard page for manual paper-trading simulation."""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
import pandas as pd

from app.config import load_settings
from app.database.connection import get_connection
from app.data.market_data import get_candles
from app.dashboard.portfolio_state import add_snapshot, get_portfolio_value, update_portfolio_prices


def _load_prices(conn) -> dict[str, float]:
    symbols = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    prices: dict[str, float] = {}
    for symbol in symbols:
        candles = get_candles(conn, symbol, "4h", limit=1)
        if candles:
            prices[symbol] = candles[-1].close
    return prices


def _portfolio_metrics(total_value: float) -> tuple[float, float, float, float]:
    exposure = (total_value - st.session_state.portfolio_cash) / total_value * 100 if total_value > 0 else 0
    total_pnl = total_value - 1000.0
    total_pnl_pct = (total_value - 1000.0) / 1000.0 * 100
    if total_value > st.session_state.portfolio_peak:
        st.session_state.portfolio_peak = total_value
    drawdown = (
        (st.session_state.portfolio_peak - total_value) / st.session_state.portfolio_peak * 100
        if st.session_state.portfolio_peak > 0
        else 0
    )
    return exposure, total_pnl, total_pnl_pct, drawdown


def _render_positions() -> None:
    st.subheader("Posiciones Abiertas")
    positions = st.session_state.get("portfolio_positions", {})
    if not positions:
        st.info("No hay posiciones abiertas.")
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


def _buy_position(trade_symbol: str, trade_pct: int, current_price: float) -> None:
    if current_price <= 0:
        st.error("Sin datos de precio. Descarga datos primero.")
        return

    cash = st.session_state.portfolio_cash
    amount = cash * (trade_pct / 100)
    quantity = amount / current_price
    positions = st.session_state.portfolio_positions

    if trade_symbol in positions:
        pos = positions[trade_symbol]
        total_qty = pos["quantity"] + quantity
        total_cost = pos["quantity"] * pos["entry_price"] + amount
        pos["quantity"] = total_qty
        pos["entry_price"] = total_cost / total_qty
    else:
        positions[trade_symbol] = {
            "quantity": quantity,
            "entry_price": current_price,
            "current_price": current_price,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0,
        }

    st.session_state.portfolio_cash -= amount
    st.session_state.executed_trades = st.session_state.get("executed_trades", 0) + 1
    add_snapshot()
    st.success(f"Comprados {quantity:.6f} {trade_symbol} a ${current_price:.2f}")
    st.rerun()


def _sell_position(trade_symbol: str, trade_pct: int, current_price: float) -> None:
    positions = st.session_state.portfolio_positions
    if trade_symbol not in positions:
        st.error("No hay posicion de este simbolo.")
        return

    pos = positions[trade_symbol]
    qty_to_sell = pos["quantity"] * (trade_pct / 100)
    proceeds = qty_to_sell * current_price
    cost_basis = qty_to_sell * pos["entry_price"]
    pnl = proceeds - cost_basis

    st.session_state.portfolio_cash += proceeds
    pos["quantity"] -= qty_to_sell
    if pos["quantity"] <= 0:
        del positions[trade_symbol]

    st.session_state.executed_trades = st.session_state.get("executed_trades", 0) + 1
    add_snapshot()
    st.success(f"Vendidos {qty_to_sell:.6f} {trade_symbol}. PnL: ${pnl:+.2f}")
    st.rerun()


def _render_trade_panel(prices: dict[str, float]) -> None:
    st.subheader("Realizar Trade Manual")
    col_sym, col_qty = st.columns(2)
    with col_sym:
        trade_symbol = st.selectbox("Simbolo", ["BTCUSDT", "ETHUSDT", "SOLUSDT"], key="trade_sym")
    with col_qty:
        trade_pct = st.slider("% del capital", 1, 100, 10, key="trade_pct")

    current_price = prices.get(trade_symbol, 0)
    st.caption(f"Precio actual: ${current_price:,.2f}")

    col_buy, col_sell = st.columns(2)
    with col_buy:
        if st.button("COMPRAR", type="primary", use_container_width=True):
            _buy_position(trade_symbol, trade_pct, current_price)
    with col_sell:
        if st.button("VENDER", use_container_width=True):
            _sell_position(trade_symbol, trade_pct, current_price)


def _reset_portfolio() -> None:
    st.session_state.portfolio_capital = 1000.0
    st.session_state.portfolio_cash = 1000.0
    st.session_state.portfolio_positions = {}
    st.session_state.portfolio_snapshots = []
    st.session_state.portfolio_peak = 1000.0
    st.session_state.executed_trades = 0
    st.session_state.rejected_trades = 0
    st.success("Portfolio reseteado.")
    st.rerun()


def render() -> None:
    """Render portfolio metrics, positions, and manual trade actions."""
    st.header("💰 Portfolio / Paper Trading")
    st.caption("Simulación de cartera virtual")

    config = load_settings()
    conn = get_connection(config.database.path)

    prices = _load_prices(conn)

    update_portfolio_prices(prices)
    tv = get_portfolio_value()
    exp, total_pnl, total_pnl_pct, dd = _portfolio_metrics(tv)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Capital", f"${tv:.2f}", border=True)
    with col2:
        st.metric("Cash Disponible", f"${st.session_state.portfolio_cash:.2f}", border=True)
    with col3:
        st.metric("Exposición", f"{exp:.1f}%", border=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("PnL Total", f"${total_pnl:.2f}", f"{total_pnl_pct:+.2f}%", border=True)
    with col5:
        st.metric("Drawdown", f"{dd:.2f}%", border=True)
    with col6:
        exec_trades = st.session_state.get("executed_trades", 0)
        rej_trades = st.session_state.get("rejected_trades", 0)
        st.metric("Trades", f"{exec_trades} ejecutados, {rej_trades} rechazados", border=True)

    st.divider()

    left, right = st.columns(2)

    with left:
        _render_positions()

    with right:
        _render_trade_panel(prices)

    st.divider()

    col_h1, col_h2, col_h3 = st.columns(3)
    snapshots = st.session_state.get("portfolio_snapshots", [])

    with col_h1:
        st.subheader("Curva de Capital")
        if len(snapshots) >= 2:
            snap_df = pd.DataFrame(snapshots)
            snap_df["timestamp"] = pd.to_datetime(snap_df["timestamp"])
            st.line_chart(snap_df, x="timestamp", y="total_value")
        else:
            st.info("Realiza trades para ver la curva de capital.")

    with col_h2:
        st.subheader("Drawdown")
        if len(snapshots) >= 2:
            snap_df = pd.DataFrame(snapshots)
            snap_df["timestamp"] = pd.to_datetime(snap_df["timestamp"])
            st.line_chart(snap_df, x="timestamp", y="drawdown_pct")
        else:
            st.info("Realiza trades para ver el drawdown.")

    with col_h3:
        st.subheader("Acciones")
        if st.button("🔄 Resetear Portfolio", use_container_width=True):
            _reset_portfolio()
