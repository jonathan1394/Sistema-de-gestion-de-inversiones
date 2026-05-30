"""Trading journal dashboard page for uploads and paper-trade review."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from app.ai.journal_analyzer import generate_journal_report
from app.config import load_settings
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.paper_trading.storage import get_trades, init_portfolio_tables


def _render_upload_tab() -> None:
    st.subheader("Upload Trade History")
    st.caption("Upload a JSON file with trade records")
    uploaded_file = st.file_uploader("Choose a JSON file", type=["json"], label_visibility="collapsed")
    if uploaded_file is None:
        return
    try:
        trades = json.load(uploaded_file)
        if isinstance(trades, dict):
            trades = [trades]
        if not trades:
            st.warning("Empty trade data.")
            return
        _render_analysis(trades)
    except json.JSONDecodeError:
        st.error("Invalid JSON file.")
    except Exception as e:
        st.error(f"Analysis failed: {e}")


def _render_analysis(trades: list) -> None:
    report = generate_journal_report(trades)
    a = report.trade_analysis
    st.success(f"Analyzed {a.total_trades} trades")

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Win Rate", f"{a.win_rate:.1f}%")
    mc2.metric("Profit Factor", f"{a.profit_factor:.2f}")
    mc3.metric("Avg Win", f"{a.avg_win:+.2f}%")
    mc4.metric("Avg Loss", f"{a.avg_loss:+.2f}%")

    mc5, mc6, mc7, mc8 = st.columns(4)
    mc5.metric("Total Trades", a.total_trades)
    mc6.metric("Consec Wins", a.consecutive_wins)
    mc7.metric("Consec Losses", a.consecutive_losses)
    mc8.metric("Avg Hold", f"{a.avg_hold_time:.1f} bars")

    st.divider()
    st.subheader("Trade Analysis")
    trades_df = pd.DataFrame([
        {"PnL%": f"{t.get('pnl_pct', 0):+.2f}%", "Hold": f"{t.get('hold_bars', 0)} bars", "Reason": t.get("reason_exit", t.get("reason", ""))}
        for t in trades
    ])
    if not trades_df.empty:
        st.dataframe(trades_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Behavior Analysis")
    b = report.behavior
    if b.details:
        for detail in b.details:
            st.warning(f"! {detail}")
    else:
        st.info("No behavioral flags detected.")

    st.divider()
    st.subheader("Insights")
    st.markdown(f"**Weakness:** {report.insight.weakness}")
    st.markdown(f"**Suggestion:** {report.insight.suggestion}")
    st.markdown(f"**Summary:** {report.summary}")


def _render_paper_trades_tab(conn) -> None:
    st.subheader("Paper Trading History")
    st.caption("Trades recorded from the Portfolio page")
    stored_trades = get_trades(conn, limit=200)
    if not stored_trades:
        st.info("No paper trades recorded yet. Execute trades from the Portfolio page.")
        return
    data = [
        {
            "Date": t.created_at[:19],
            "Symbol": t.symbol,
            "Action": t.action,
            "Qty": f"{t.quantity:.6f}",
            "Price": f"${t.price:.2f}",
            "PnL": f"${t.pnl:+.2f}",
            "PnL%": f"{t.pnl_pct:+.2f}%",
        }
        for t in stored_trades
    ]
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    pnls = [t.pnl_pct for t in stored_trades if t.action == "SELL"]
    if pnls:
        wins = sum(1 for p in pnls if p > 0)
        st.metric("Closed Trades Win Rate", f"{wins/len(pnls)*100:.1f}%")


def render() -> None:
    """Render journal tabs for uploaded JSON and stored paper trades."""
    st.markdown('<div class="page-title">Trading Journal</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Analisis de historial de trades para detectar patrones y mejorar ejecucion.</div>', unsafe_allow_html=True)
    config = load_settings()
    conn = get_connection(config.database.path)
    run_migrations(conn)
    init_portfolio_tables(conn)

    tab1, tab2 = st.tabs(["Upload JSON", "Paper Trades History"])
    with tab1:
        _render_upload_tab()
    with tab2:
        _render_paper_trades_tab(conn)
