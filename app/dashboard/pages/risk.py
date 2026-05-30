from __future__ import annotations

import yaml
import streamlit as st

from app.config import load_settings
from app.risk.circuit_breakers import CircuitBreakers


def _load_yaml() -> dict:
    try:
        with open("settings.yaml") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def render() -> None:
    config = load_settings()
    raw = _load_yaml()
    risk = raw.get("risk", {})
    trading = raw.get("trading", {})

    st.header("🛡️ Risk Configuration")
    st.caption("Límites y controles de riesgo del sistema")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Position Sizing")
        st.metric("Máx por operación", f"{risk.get('max_position_size_pct', 3)*100:.2f}%", border=True)
        st.metric("Riesgo por operación", f"{risk.get('max_risk_per_trade_pct', 1)*100:.2f}%", border=True)

        st.subheader("Stop Loss")
        st.metric("Stop Loss por defecto", f"{risk.get('default_stop_loss_pct', 2)*100:.2f}%", border=True)
        st.metric("Stop mínimo", f"{risk.get('min_stop_loss_pct', 0.5)*100:.2f}%", border=True)
        st.metric("Stop máximo", f"{risk.get('max_stop_loss_pct', 10)*100:.2f}%", border=True)

    with col2:
        st.subheader("Exposure Limits")
        st.metric("Máx por activo", f"{risk.get('max_asset_exposure_pct', 35)*100:.2f}%", border=True)
        st.metric("Máx total", f"{risk.get('max_total_exposure_pct', 50) if risk.get('max_total_exposure_pct') else 50:.2f}%", border=True)
        st.metric("Máx altcoins", f"{risk.get('max_altcoin_exposure_pct', 40)*100:.2f}%", border=True)

        st.subheader("Circuit Breakers")
        st.metric("Pérdida diaria máx", f"{risk.get('max_daily_loss_pct', 3)*100:.2f}%", border=True)
        st.metric("Pérdida semanal máx", f"{risk.get('max_weekly_loss_pct', 7)*100:.2f}%", border=True)
        st.metric("Pérdidas consecutivas", str(risk.get('max_consecutive_losses', 5)), border=True)

    st.divider()

    st.subheader("Kill Switch")
    kill_col1, kill_col2 = st.columns([1, 3])
    with kill_col1:
        ks_active = st.checkbox("Activar Kill Switch", value=config.kill_switch)
    with kill_col2:
        if ks_active:
            st.error("⚠️ KILL SWITCH ACTIVO — No se permiten nuevas operaciones")
        else:
            st.success("✅ Kill Switch inactivo — Operaciones permitidas")
    if ks_active != config.kill_switch:
        st.warning("Cambio solo visual. Edita settings.yaml o usa KILL_SWITCH=true/false en .env para persistir.")

    st.divider()

    st.subheader("Modo de Operación")
    st.info(f"Modo actual: **{config.mode}**")
    if config.mode in ("real_manual", "real_auto_limited"):
        st.warning("⚠️ Modo real activo — revisa la configuración de seguridad")

    st.divider()

    st.subheader("Estado Actual del Circuit Breaker")
    cb = CircuitBreakers(
        max_daily_loss_pct=risk.get("max_daily_loss_pct", 3.0),
        max_weekly_loss_pct=risk.get("max_weekly_loss_pct", 7.0),
        max_consecutive_losses=risk.get("max_consecutive_losses", 5),
        max_trades_per_day=risk.get("max_trades_per_day", 10),
        kill_switch=config.kill_switch,
    )
    state = cb.state

    cb_cols = st.columns(4)
    with cb_cols[0]:
        st.metric("Pérdidas consecutivas", str(state.consecutive_losses), border=True)
    with cb_cols[1]:
        st.metric("Trades hoy", str(state.trades_today), border=True)
    with cb_cols[2]:
        st.metric("Pérdida diaria", f"{state.daily_loss_pct:.2f}%", border=True)
    with cb_cols[3]:
        ks_status = "⚠️ Activo" if state.kill_switch_active else "✅ Inactivo"
        st.metric("Kill Switch", ks_status, border=True)

    st.divider()

    st.subheader("Requisitos de Trading")
    tr_cols = st.columns(3)
    with tr_cols[0]:
        st.metric("Requiere Stop Loss", "✅ Sí" if trading.get("require_stop_loss", True) else "❌ No", border=True)
    with tr_cols[1]:
        st.metric("Futuros permitidos", "❌ No" if not trading.get("allow_futures", False) else "✅ Sí", border=True)
    with tr_cols[2]:
        st.metric("Apalancamiento", "❌ No" if not trading.get("allow_leverage", False) else "✅ Sí", border=True)

    st.caption("Estos valores se leen de settings.yaml. Edita ese archivo para cambios permanentes.")
