"""Ranking dashboard page for viewing ranked assets and investment recommendations."""

from __future__ import annotations

import streamlit as st
from loguru import logger

from app.config import load_settings
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.prospecting.db import get_all_prospects
from app.prospecting.ranking import AssetRanking, generate_ranking


def _render_header() -> None:
    st.markdown('<div class="page-title">📊 Ranking</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Ranking de activos basado en score, confluencia y recomendación de inversión.</div>',
        unsafe_allow_html=True,
    )


def _render_summary(rankings: list[AssetRanking], total: int) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Activos", total)
    col2.metric("Recomendado (INVERTIR)", sum(1 for r in rankings if r.recommendation == "INVERTIR"))
    col3.metric("En Vigilancia (VIGILAR)", sum(1 for r in rankings if r.recommendation == "VIGILAR"))
    col4.metric("Evitar (EVITAR)", sum(1 for r in rankings if r.recommendation == "EVITAR"))


def _render_ranking_table(rankings: list[AssetRanking]) -> None:
    st.subheader("Ranking de Activos")
    if not rankings:
        st.info("No data available to display in the ranking.")
        return
    rows = []
    for idx, rank in enumerate(rankings, start=1):
        rows.append({
            "Rank": idx,
            "Símbolo": rank.symbol,
            "Score": f"{rank.score:.2f}",
            "Recomendación": rank.recommendation,
            "Confluencia": f"{rank.confluence}/3",
            "Precio": f"${rank.price:,.2f}" if rank.price is not None else "-",
            "Retorno 1d": f"{rank.return_pct_1d:+.2f}%" if rank.return_pct_1d is not None else "-",
            "Tendencia 1h": rank.trend_1h or "-",
            "Tendencia 4h": rank.trend_4h or "-",
            "Tendencia 1d": rank.trend_1d or "-",
            "Motivo": rank.reason,
        })
    st.dataframe(rows, use_container_width=True, hide_index=True, column_config={
        "Rank": st.column_config.NumberColumn("Rank", width="small"),
        "Símbolo": st.column_config.TextColumn("Símbolo", width="small"),
        "Score": st.column_config.TextColumn("Score", width="small"),
        "Recomendación": st.column_config.TextColumn("Recomendación", width="medium"),
        "Confluencia": st.column_config.TextColumn("Confluencia", width="small"),
        "Precio": st.column_config.TextColumn("Precio", width="small"),
        "Retorno 1d": st.column_config.TextColumn("Retorno 1d", width="small"),
        "Tendencia 1h": st.column_config.TextColumn("Tend 1h", width="small"),
        "Tendencia 4h": st.column_config.TextColumn("Tend 4h", width="small"),
        "Tendencia 1d": st.column_config.TextColumn("Tend 1d", width="small"),
        "Motivo": st.column_config.TextColumn("Motivo", width="large"),
    })


def render() -> None:
    """Render the ranking page."""
    try:
        _render_header()
        config = load_settings()
        conn = get_connection(config.database.path)
        run_migrations(conn)

        prospects = get_all_prospects(conn)
        if not prospects:
            st.info("No prospects yet. Add a symbol in the Prospects page to get started.")
            return

        rankings = generate_ranking(prospects)
        _render_summary(rankings, len(prospects))
        st.divider()
        _render_ranking_table(rankings)

        with st.expander("Datos brutos de prospectos (para depuración)"):
            if prospects:
                st.dataframe(
                    [{"Símbolo": p.symbol, "Intervalo": p.interval, "Score": p.score,
                      "Tendencia": p.trend or "-", "Volatilidad": p.volatility or "-",
                      "Volumen": p.volume_profile or "-", "RSI": p.rsi_condition or "-",
                      "Señales": p.signals_count, "Estado": p.status} for p in prospects],
                    use_container_width=True, hide_index=True,
                )

        if st.button("🔄 Actualizar Ranking", use_container_width=True):
            st.rerun()
    except Exception:
        logger.exception("Error rendering ranking page")
        st.error("Error loading ranking page.")
        st.stop()
