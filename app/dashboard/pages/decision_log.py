"""Decision log dashboard page for audit trail inspection and export."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List

import pandas as pd
import streamlit as st

from app.governance.decision_log import DecisionLogEntry, get_recent_decisions

logger = logging.getLogger(__name__)


def _read_decisions_from_db(limit: int = 1000) -> List[DecisionLogEntry]:
    """Read decisions from the decision_log table."""
    try:
        # Use the existing function from decision_log module
        return get_recent_decisions(limit=limit)
    except Exception as e:
        st.error(f"Error reading decisions from database: {e}")
        logger.exception("Error reading decisions from DB")
        return []


def _decisions_to_dataframe(decisions: List[DecisionLogEntry]) -> pd.DataFrame:
    """Convert a list of DecisionLogEntry to a pandas DataFrame for display."""
    if not decisions:
        return pd.DataFrame()

    data = []
    for d in decisions:
        data.append({
            "ID": d.decision_id,
            "Timestamp": d.timestamp,
            "Datetime": datetime.fromtimestamp(int(d.timestamp) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "Type": d.decision_type,
            "Symbol": d.symbol or "-",
            "Strategy": d.strategy_name or "-",
            "Timeframe": d.timeframe or "-",
            "Mode": d.mode,
            "Approved": "✅" if d.approved else "❌",
            "Reason": d.reason,
            "Policy Version": d.policy_version or "-",
            "Strategy Version": d.strategy_version or "-",
        })
    df = pd.DataFrame(data)
    return df


def render() -> None:
    """Render decision log filters, table, export, and manual entry tools (if needed)."""
    st.header("📋 Decision Log (Audit Trail)")
    st.caption("Registro de decisiones de inversión, aprobaciones y rechazos")

    # Filters
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    with col1:
        decision_type_filter = st.selectbox(
            "Filtrar por tipo de decisión",
            ["ALL", "PAPER_BUY_EVALUATION", "POLICY_CHECK", "RISK_CHECK", "SAFETY_CHECK", "APPROVAL", "EXECUTION", "REJECTION"],
        )
    with col2:
        approved_filter = st.selectbox(
            "Filtrar por aprobación",
            ["ALL", "APPROVED", "REJECTED"],
        )
    with col3:
        limit_options = [100, 500, 1000, 5000]
        limit = st.selectbox(
            "Máximo de registros",
            options=limit_options,
            index=2,  # default 1000
        )
    with col4:
        if st.button("🔄 Refrescar", use_container_width=True):
            st.rerun()

    # Read decisions
    with st.spinner("Cargando decisiones..."):
        decisions = _read_decisions_from_db(limit=int(limit))

    # Apply filters
    if decision_type_filter != "ALL":
        decisions = [d for d in decisions if d.decision_type == decision_type_filter]
    if approved_filter == "APPROVED":
        decisions = [d for d in decisions if d.approved]
    elif approved_filter == "REJECTED":
        decisions = [d for d in decisions if not d.approved]

    # Display
    if decisions:
        df = _decisions_to_dataframe(decisions)
        # Reorder columns for better readability
        column_order = ["Datetime", "Type", "Symbol", "Strategy", "Timeframe", "Mode", "Approved", "Reason", "Policy Version", "Strategy Version", "ID"]
        df = df[column_order] if all(col in df.columns for col in column_order) else df
        st.dataframe(df, use_container_width=True, height=500, hide_index=True)
        st.caption(f"Mostrando {len(decisions)} decisiones")
    else:
        st.info("No hay decisiones de inversión para mostrar con los filtros seleccionados.")

    # Export
    st.divider()
    st.subheader("Exportar Decisiones")
    if decisions:
        # Prepare JSON export
        export_data = []
        for d in decisions:
            export_data.append({
                "decision_id": d.decision_id,
                "decision_type": d.decision_type,
                "timestamp": d.timestamp,
                "datetime": datetime.fromtimestamp(int(d.timestamp) / 1000, tz=timezone.utc).isoformat(),
                "symbol": d.symbol,
                "strategy_name": d.strategy_name,
                "timeframe": d.timeframe,
                "mode": d.mode,
                "approved": d.approved,
                "reason": d.reason,
                "input_json": d.input_json,
                "output_json": d.output_json,
                "policy_version": d.policy_version,
                "strategy_version": d.strategy_version,
            })
        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Exportar como JSON",
            data=json_str,
            file_name=f"decision_log_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.info("No hay datos para exportar.")

    # Optional: Manual decision entry (for testing or admin)
    st.divider()
    st.subheader("Agregar Decisión de Prueba (Solo para pruebas)")
    with st.form("manual_decision_entry"):
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            m_type = st.selectbox("Tipo", ["PAPER_BUY_EVALUATION", "POLICY_CHECK", "RISK_CHECK", "TEST"])
            m_symbol = st.text_input("Símbolo (opcional)", "BTCUSDT")
            m_approved = st.selectbox("Aprobado", [True, False], format_func=lambda x: "Sí" if x else "No")
        with col_e2:
            m_reason = st.text_input("Motivo", "Decisión de prueba")
            m_mode = st.selectbox("Modo", ["paper", "real_manual", "real_auto_limited", "analysis", "backtest"])
        m_input = st.text_area("Entrada JSON", value='{"test": true}')
        m_output = st.text_area("Salida JSON", value='{"result": "ok"}')
        submitted = st.form_submit_button("➕ Agregar Decisión de Prueba", use_container_width=True)
        if submitted:
            try:
                input_json = json.loads(m_input) if m_input.strip() else {}
                output_json = json.loads(m_output) if m_output.strip() else {}
                from app.governance.decision_log import log_decision
                decision_id = log_decision(
                    decision_type=m_type,
                    symbol=m_symbol if m_symbol.strip() else None,
                    strategy_name="test" if m_type == "TEST" else None,
                    timeframe="1d",
                    mode=m_mode,
                    approved=m_approved,
                    reason=m_reason,
                    input_data=input_json,
                    output_data=output_json,
                )
                st.success(f"Decisión de prueba agregada con ID: {decision_id}")
                st.rerun()
            except Exception as e:
                st.error(f"Error al agregar decisión: {e}")
                logger.exception("Error adding decision log entry")
