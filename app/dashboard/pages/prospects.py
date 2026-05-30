from __future__ import annotations

import streamlit as st

from app.config import load_settings
from app.data.binance_client import BinanceClient
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.prospecting.db import (
    add_prospect,
    archive_prospect,
    get_all_prospects,
    get_prospects_by_status,
    remove_prospect,
    update_prospect_status,
)
from app.prospecting.scoring import get_recommendation
from app.prospecting.screener import ProspectScreener


def render() -> None:
    st.markdown('<div class="page-title">🎯 Prospects</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Seguimiento de activos candidatos con score y recomendacion.</div>',
        unsafe_allow_html=True,
    )

    config = load_settings()
    conn = get_connection(config.database.path)
    run_migrations(conn)

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        with st.form("add_prospect", clear_on_submit=True):
            subcol1, subcol2 = st.columns([3, 1])
            with subcol1:
                symbol = st.text_input("Symbol", placeholder="BTCUSDT", label_visibility="collapsed")
            with subcol2:
                submitted = st.form_submit_button("Add", use_container_width=True)
            if submitted and symbol.strip():
                add_prospect(conn, symbol.strip())
                st.rerun()

    with col2:
        status_filter = st.selectbox(
            "Filter", ["all", "watching", "active", "archived", "rejected"],
            label_visibility="collapsed",
        )

    with col3:
        if st.button("Refresh", use_container_width=True):
            st.rerun()

    st.divider()

    run_col1, run_col2 = st.columns([3, 1])
    with run_col1:
        st.caption("Run analysis on all prospects to update scores, trends and signals.")
    with run_col2:
        if st.button("Run Screener", type="primary", use_container_width=True):
            with st.spinner("Analyzing all prospects..."):
                try:
                    config = load_settings()
                    conn = get_connection(config.database.path)
                    client = BinanceClient(config.binance)
                    weights = None
                    try:
                        from pathlib import Path

                        import yaml
                        raw = yaml.safe_load(Path("settings.yaml").open()) or {}
                        weights = raw.get("prospecting", {}).get("scoring_weights")
                    except Exception:
                        pass
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

    if status_filter == "all":
        prospects = get_all_prospects(conn)
    else:
        prospects = get_prospects_by_status(conn, status_filter)

    if not prospects:
        st.info("No prospects yet. Add a symbol above to get started.")
        return

    total = len(prospects)
    high_score = sum(1 for p in prospects if p.score >= 0.6)
    mid_score = sum(1 for p in prospects if 0.3 <= p.score < 0.6)

    mcol1, mcol2, mcol3 = st.columns(3)
    mcol1.metric("Total", total)
    mcol2.metric("High Score (>=0.6)", high_score)
    mcol3.metric("Medium Score (0.3-0.6)", mid_score)

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

    data = []
    for p in prospects:
        rec = get_recommendation(p.score)
        rec_label = rec.label
        rec_mark = {
            "INVERTIR": "🟢 INVERTIR",
            "VIGILAR": "🟡 VIGILAR",
            "NEUTRAL": "⚪ NEUTRAL",
            "EVITAR": "🔴 EVITAR",
        }.get(rec_label, rec_label)

        data.append({
            "Symbol": p.symbol,
            "Interval": p.interval,
            "Status": p.status,
            "Score": f"{p.score:.4f}",
            "Rec": rec_mark,
            "Trend": p.trend or "-",
            "Volatility": p.volatility or "-",
            "Volume": p.volume_profile or "-",
            "RSI": p.rsi_condition or "-",
            "Signals": p.signals_count,
        })

    st.dataframe(data, use_container_width=True, hide_index=True)

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
            symbol, rest = selected.split(" (")
            interval = rest.rstrip(")")
            if promote:
                update_prospect_status(conn, symbol, interval, "active")
                st.rerun()
            elif arch:
                archive_prospect(conn, symbol, interval)
                st.rerun()
            elif delete:
                remove_prospect(conn, symbol, interval)
                st.rerun()
