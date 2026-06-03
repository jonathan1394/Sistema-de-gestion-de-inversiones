"""System logs dashboard page for inspection and export."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

LOGS_FILE = Path("data/system_logs.jsonl")

logger = logging.getLogger(__name__)


def _append_log(level: str, module: str, message: str) -> None:
    try:
        LOGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "module": module,
            "message": message,
        }
        with LOGS_FILE.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        logger.exception("Error appending log entry")


def _read_logs() -> list[dict]:
    if not LOGS_FILE.exists():
        return []
    entries = []
    try:
        with LOGS_FILE.open("r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.exception("Error decoding JSON line in logs")
                        pass
    except OSError:
        logger.exception("Error reading log file %s", LOGS_FILE)
    return entries


def render() -> None:
    """Render filters, table, export, and manual log entry tools."""
    st.header("📋 System Logs")
    st.caption("Registro de eventos del sistema")

    try:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            level = st.selectbox("Filtrar por nivel", ["ALL", "INFO", "WARNING", "ERROR", "TRADE"])
        with col2:
            if st.button("🔄 Refrescar", use_container_width=True):
                st.rerun()
        with col3:
            if st.button("🗑️ Limpiar Logs", use_container_width=True):
                try:
                    if LOGS_FILE.exists():
                        LOGS_FILE.unlink()
                    st.success("Logs eliminados.")
                except Exception:
                    logger.exception("Error clearing log file")
                    st.error("Error clearing log file.")
                st.rerun()

        logs = _read_logs()

        if level != "ALL":
            logs = [e for e in logs if e.get("level") == level]

        if logs:
            log_df = pd.DataFrame(logs)
            st.dataframe(log_df, use_container_width=True, height=400, hide_index=True)
        else:
            st.info("No hay entradas de log para el filtro seleccionado.")

        st.divider()

        st.subheader("Exportar Logs")
        if logs:
            json_str = json.dumps(logs, indent=2)
            st.download_button(
                "📥 Exportar como JSON",
                data=json_str,
                file_name="system_logs.json",
                mime="application/json",
                use_container_width=True,
            )

        st.divider()
        st.subheader("Generar Evento de Prueba")
        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            test_level = st.selectbox("Nivel", ["INFO", "WARNING", "ERROR", "TRADE"])
        with col_e2:
            test_module = st.text_input("Módulo", "manual")
        with col_e3:
            test_msg = st.text_input("Mensaje", "Evento de prueba")

        if st.button("➕ Agregar Entrada", use_container_width=True):
            _append_log(test_level, test_module, test_msg)
            st.success("Entrada agregada.")
            st.rerun()
    except Exception:
        logger.exception("Unhandled error in logs render")
        st.error("An unexpected error occurred while rendering this page.")
