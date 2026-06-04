"""Prospects dashboard page for watchlist and screening workflows."""

from __future__ import annotations

import streamlit as st
from loguru import logger

from app.config import load_settings
from app.dashboard.helpers import get_current_price
from app.data.binance_client import BinanceClient
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.governance.decision_engine import InvestmentDecision, evaluate_investment_decision
from app.paper_trading.storage import record_trade, upsert_position
from app.prospecting.db import (
    add_prospect,
    archive_prospect,
    get_all_prospects,
    get_prospects_by_status,
    remove_prospect,
    update_prospect_status,
)
from app.prospecting.ranking import generate_ranking
from app.prospecting.scoring import get_recommendation
from app.prospecting.screener import ProspectScreener


def _run_screener() -> None:
    with st.spinner("Analyzing all prospects..."):
        try:
            config = load_settings()
            conn = get_connection(config.database.path)
            client = BinanceClient(config.binance)
            weights = config.prospecting.get("scoring_weights")
            screener = ProspectScreener(
                client=client,
                connection=conn,
                weights=weights,
            )
            result = screener.run_on_all()
            st.success(f"Screener completed. {result.count} assets analyzed.")
            st.rerun()
        except Exception as e:
            st.error(f"Screener failed: {e}")
            logger.exception("Screener failed")


def _prospect_rows(prospects: list) -> list[dict[str, str | int]]:
    rec_display = {
        "INVERTIR": "🟢 INVERTIR",
        "VIGILAR": "🟡 VIGILAR",
        "NEUTRAL": "⚪ NEUTRAL",
        "EVITAR": "🔴 EVITAR",
    }
    rows: list[dict[str, str | int]] = []
    for prospect in prospects:
        rec_label = get_recommendation(prospect.score).label
        rows.append(
            {
                "Symbol": prospect.symbol,
                "Interval": prospect.interval,
                "Status": prospect.status,
                "Score": f"{prospect.score:.4f}",
                "Rec": rec_display.get(rec_label, rec_label),
                "Trend": prospect.trend or "-",
                "Volatility": prospect.volatility or "-",
                "Volume": prospect.volume_profile or "-",
                "RSI": prospect.rsi_condition or "-",
                "Signals": prospect.signals_count,
            }
        )
    return rows


def _manage_selected_prospect(conn, selected: str, promote: bool, arch: bool, delete: bool) -> None:
    try:
        symbol, rest = selected.split(" (")
        interval = rest.rstrip(")")
        if promote:
            update_prospect_status(conn, symbol, interval, "active")
            st.rerun()
        if arch:
            archive_prospect(conn, symbol, interval)
            st.rerun()
        if delete:
            remove_prospect(conn, symbol, interval)
            st.rerun()
    except Exception:
        logger.exception("Error managing prospect")
        st.error("Error managing prospect.")


def _render_header() -> None:
    st.markdown('<div class="page-title">🎯 Prospects</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Seguimiento de activos candidatos con score y recomendacion.</div>',
        unsafe_allow_html=True,
    )


def _render_add_form(conn) -> None:
    with st.form("add_prospect", clear_on_submit=True):
        subcol1, subcol2 = st.columns([3, 1])
        with subcol1:
            symbol = st.text_input("Symbol", placeholder="BTCUSDT", label_visibility="collapsed")
        with subcol2:
            submitted = st.form_submit_button("Add", use_container_width=True)
        if submitted and symbol.strip():
            try:
                add_prospect(conn, symbol.strip())
                st.rerun()
            except Exception:
                logger.exception("Error adding prospect")
                st.error("Error adding prospect.")


def _render_screener_controls() -> None:
    run_col1, run_col2 = st.columns([3, 1])
    with run_col1:
        st.caption("Run analysis on all prospects to update scores, trends and signals.")
    with run_col2:
        if st.button("Run Screener", type="primary", use_container_width=True):
            _run_screener()


def _render_metrics(prospects: list) -> None:
    total = len(prospects)
    high_score = sum(1 for p in prospects if p.score >= 0.6)
    mid_score = sum(1 for p in prospects if 0.3 <= p.score < 0.6)
    mcol1, mcol2, mcol3 = st.columns(3)
    mcol1.metric("Total", total)
    mcol2.metric("High Score (>=0.6)", high_score)
    mcol3.metric("Medium Score (0.3-0.6)", mid_score)


def _render_legend() -> None:
    st.markdown(
        """
        <div class='legend-row'>
            <span class='badge badge-pos'>INVERTIR</span>
            <span class='badge badge-warn'>VIGILAR</span>
            <span class='badge badge-neutral'>NEUTRAL</span>
            <span class='badge badge-neg'>EVITAR</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_manage_form(conn, prospects: list) -> None:
    st.subheader("Manage Prospects")
    with st.form("manage_prospect"):
        prospects_list = [f"{p.symbol} ({p.interval})" for p in prospects]
        selected = st.selectbox("Select prospect", prospects_list, label_visibility="collapsed")
        action_col1, action_col2, action_col3 = st.columns(3)
        with action_col1:
            promote = st.form_submit_button("Promote to Active", use_container_width=True)
        with action_col2:
            arch = st.form_submit_button("Archive", use_container_width=True)
        with action_col3:
            delete = st.form_submit_button("Remove", use_container_width=True, type="primary")
        if selected:
            _manage_selected_prospect(conn, selected, promote, arch, delete)


def _render_ranking_table(rankings, prospects) -> None:
    if not rankings:
        st.info("No hay datos para mostrar en el ranking.")
        return
    rows = []
    for idx, rank in enumerate(rankings, start=1):
        prospect = next((p for p in prospects if p.symbol == rank.symbol and p.interval == "1d"), None)
        rows.append({
            "Rank": idx,
            "Symbol": rank.symbol,
            "Score": f"{rank.score:.2f}",
            "Recommendation": rank.recommendation,
            "Reason": rank.reason,
            "Price": f"${rank.price:,.2f}" if rank.price is not None else "-",
            "Retorno 1d": f"{rank.return_pct_1d:+.2f}%" if rank.return_pct_1d is not None else "-",
            "Tendencia 1h": rank.trend_1h or "-",
            "Tendencia 4h": rank.trend_4h or "-",
            "Tendencia 1d": rank.trend_1d or "-",
            "Señales": prospect.signals_count if prospect else 0,
        })
    st.dataframe(
        rows, use_container_width=True, hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "Symbol": st.column_config.TextColumn("Symbol", width="small"),
            "Score": st.column_config.TextColumn("Score", width="small"),
            "Recommendation": st.column_config.TextColumn("Recommendation", width="medium"),
            "Reason": st.column_config.TextColumn("Motivo", width="large"),
            "Price": st.column_config.TextColumn("Precio", width="small"),
            "Retorno 1d": st.column_config.TextColumn("Retorno 1d", width="small"),
            "Tendencia 1h": st.column_config.TextColumn("Tend 1h", width="small"),
            "Tendencia 4h": st.column_config.TextColumn("Tend 4h", width="small"),
            "Tendencia 1d": st.column_config.TextColumn("Tend 1d", width="small"),
            "Señales": st.column_config.NumberColumn("Señales", width="small"),
        },
    )


def _render_paper_execution(conn, prospects) -> None:
    st.divider()
    st.subheader("Ejecutar operación paper")
    decisions: dict[str, InvestmentDecision] = {}
    for prospect in prospects:
        decision = evaluate_investment_decision(
            symbol=prospect.symbol, interval=prospect.interval,
            score=prospect.score, suggested_amount_usdt=50.0,
        )
        decisions[prospect.symbol] = decision

    executable = [p for p in prospects if decisions.get(p.symbol) and decisions[p.symbol].approved and decisions[p.symbol].action == "PAPER_BUY"]
    if not executable:
        st.info("No hay prospectos aprobados para operación paper en este momento.")
        return

    options = {f"{p.symbol} - Score: {p.score:.2f}": p for p in executable}
    selected_label = st.selectbox("Selecciona un prospecto para operar", options=list(options.keys()), label_visibility="collapsed")
    selected = options[selected_label] if selected_label else None
    if not selected:
        return

    d = decisions.get(selected.symbol)
    amount = st.number_input(
        f"Monto a invertir (USDT) para {selected.symbol}",
        min_value=0.0, value=d.suggested_amount_usdt if d else 50.0, step=1.0,
    )
    if st.button("Ejecutar operación paper", type="primary", use_container_width=True):
        if amount <= 0:
            st.error("El monto debe ser mayor que cero.")
            return
        updated = evaluate_investment_decision(
            symbol=selected.symbol, interval=selected.interval,
            score=selected.score, suggested_amount_usdt=amount,
        )
        if not (updated.approved and updated.action == "PAPER_BUY"):
            st.error(f"Operación rechazada: {updated.reason} (Bloqueo: {updated.blocking_rule})")
            return
        try:
            price = get_current_price(conn, selected.symbol)
            if not price or price <= 0:
                st.error("No se pudo obtener el precio actual.")
                return
            quantity = amount / price
            trade = record_trade(
                connection=conn, symbol=selected.symbol, action="BUY", quantity=quantity,
                price=price, commission=0.0, pnl=0.0, pnl_pct=0.0,
                reason=f"Paper trade from prospecting: score {selected.score:.2f}, confluence {updated.confluence}/3",
                interval=selected.interval,
            )
            upsert_position(connection=conn, symbol=selected.symbol, quantity=quantity, entry_price=price, current_price=price, entry_time=trade.created_at)
            st.success(f"Operación ejecutada: {quantity:.6f} {selected.symbol} a ${price:,.2f} USDT. Trade ID: {trade.id}")
            st.rerun()
        except Exception as e:
            logger.exception("Error executing paper trade")
            st.error(f"Error: {e}")


def render() -> None:
    """Render prospect management, metrics, screener controls, ranking, and paper trade execution."""
    try:
        _render_header()
        config = load_settings()
        conn = get_connection(config.database.path)
        run_migrations(conn)

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            _render_add_form(conn)
        with col2:
            status_filter = st.selectbox("Filter", ["all", "watching", "active", "archived", "rejected"], label_visibility="collapsed")
        with col3:
            if st.button("Refresh", use_container_width=True):
                st.rerun()

        st.divider()
        _render_screener_controls()

        prospects = get_all_prospects(conn) if status_filter == "all" else get_prospects_by_status(conn, status_filter)
        if not prospects:
            st.info("No prospects yet. Add a symbol above to get started.")
            return

        rankings = generate_ranking(prospects)
        _render_metrics(prospects)
        _render_legend()

        st.subheader("Ranking de Activos")
        _render_ranking_table(rankings, prospects)

        _render_paper_execution(conn, prospects)
        _render_manage_form(conn, prospects)
    except Exception:
        logger.exception("Error rendering prospects page")
        st.error("Error loading prospects page.")
        st.stop()
