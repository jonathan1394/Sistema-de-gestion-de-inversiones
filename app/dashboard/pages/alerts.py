"""Alerts dashboard page for history and configuration visibility."""

from __future__ import annotations

import json
import logging

import pandas as pd
import streamlit as st

from app.alerts import AlertManager
from app.config import load_settings

logger = logging.getLogger(__name__)


def render() -> None:
    """Render alerts history, filters, and notification settings."""
    try:
        st.header("🔔 Alertas y Notificaciones")
        st.caption("Historial de alertas del sistema")

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            level_filter = st.selectbox("Filtrar por nivel", ["ALL", "INFO", "WARNING", "ERROR", "TRADE", "SUMMARY"])
        with col2:
            category_filter = st.selectbox("Filtrar por categoría", ["ALL", "PRICE", "SIGNAL", "RISK", "SUMMARY", "SYSTEM"])
        with col3:
            if st.button("🗑️ Limpiar", use_container_width=True):
                AlertManager().clear_history()
                st.success("Historial limpiado.")
                st.rerun()

        manager = AlertManager()
        entries = manager.get_history(limit=200)

        if level_filter != "ALL":
            entries = [e for e in entries if e.get("level") == level_filter]
        if category_filter != "ALL":
            entries = [e for e in entries if e.get("category") == category_filter]

        if entries:
            df = pd.DataFrame(entries)
            df = df[["timestamp", "level", "category", "title", "message"]]
            df.columns = ["Timestamp", "Nivel", "Categoría", "Título", "Mensaje"]

            def _color_row(row):
                level_colors = {"INFO": "", "WARNING": "background-color: #fff3cd", "ERROR": "background-color: #f8d7da", "TRADE": "background-color: #d4edda"}
                return [level_colors.get(row["Nivel"], "")] * len(row)

            st.dataframe(df, use_container_width=True, height=400, hide_index=True)

            st.download_button(
                "📥 Exportar alertas (JSON)",
                data=json.dumps(entries, indent=2),
                file_name="alert_history.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.info("No hay alertas registradas.")

        st.divider()

        st.subheader("Estado del Sistema de Alertas")
        alerts_config = load_settings().alerts

        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            enabled = alerts_config.get("enabled", False)
            st.metric("Alertas", "✅ Activas" if enabled else "❌ Inactivas", border=True)
        with col_c2:
            interval = alerts_config.get("check_interval_seconds", 300)
            st.metric("Intervalo", f"{interval}s", border=True)
        with col_c3:
            desktop = alerts_config.get("notifications", {}).get("desktop", False)
            st.metric("Desktop", "✅ Sí" if desktop else "❌ No", border=True)

        tg = alerts_config.get("notifications", {}).get("telegram", {})
        if tg.get("enabled") and tg.get("bot_token"):
            st.success("✅ Telegram configurado")
        else:
            st.info("ℹ️ Telegram no configurado. Usa TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en .env")
    except Exception:
        logger.exception("Error rendering alerts page")
        st.error("Error loading alerts page.")
        st.stop()
