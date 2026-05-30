"""Risk dashboard page for configuration and breaker visibility."""

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


def _render_position_sizing(risk: dict) -> None:
    st.subheader("Position Sizing")
    st.metric("Max por operacion", f"{risk.get('max_position_size_pct', 3)*100:.2f}%", border=True)
    st.metric("Riesgo por operacion", f"{risk.get('max_risk_per_trade_pct', 1)*100:.2f}%", border=True)
    st.subheader("Stop Loss")
    st.metric("Stop Loss por defecto", f"{risk.get('default_stop_loss_pct', 2)*100:.2f}%", border=True)
    st.metric("Stop minimo", f"{risk.get('min_stop_loss_pct', 0.5)*100:.2f}%", border=True)
    st.metric("Stop maximo", f"{risk.get('max_stop_loss_pct', 10)*100:.2f}%", border=True)


def _render_exposure_limits(risk: dict) -> None:
    st.subheader("Exposure Limits")
    st.metric("Max por activo", f"{risk.get('max_asset_exposure_pct', 35)*100:.2f}%", border=True)
    total = risk.get('max_total_exposure_pct', 50) or 50
    st.metric("Max total", f"{total:.2f}%", border=True)
    st.metric("Max altcoins", f"{risk.get('max_altcoin_exposure_pct', 40)*100:.2f}%", border=True)
    st.subheader("Circuit Breakers")
    st.metric("Perdida diaria max", f"{risk.get('max_daily_loss_pct', 3)*100:.2f}%", border=True)
    st.metric("Perdida semanal max", f"{risk.get('max_weekly_loss_pct', 7)*100:.2f}%", border=True)
    st.metric("Perdidas consecutivas", str(risk.get('max_consecutive_losses', 5)), border=True)


def _render_kill_switch(config) -> None:
    st.subheader("Kill Switch")
    ks_active = st.checkbox("Activar Kill Switch", value=config.kill_switch)
    if ks_active:
        st.error("KILL SWITCH ACTIVO - No se permiten nuevas operaciones")
    else:
        st.success("Kill Switch inactivo - Operaciones permitidas")
    if ks_active != config.kill_switch:
        st.warning("Cambio solo visual. Edita settings.yaml o usa KILL_SWITCH en .env para persistir.")


def _render_circuit_breaker_state(risk: dict, config) -> None:
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
    cb_cols[0].metric("Perdidas consecutivas", str(state.consecutive_losses), border=True)
    cb_cols[1].metric("Trades hoy", str(state.trades_today), border=True)
    cb_cols[2].metric("Perdida diaria", f"{state.daily_loss_pct:.2f}%", border=True)
    ks_status = "Activo" if state.kill_switch_active else "Inactivo"
    cb_cols[3].metric("Kill Switch", ks_status, border=True)


def _render_trading_requirements(trading: dict) -> None:
    st.subheader("Requisitos de Trading")
    tr_cols = st.columns(3)
    tr_cols[0].metric("Requiere Stop Loss", "Si" if trading.get("require_stop_loss", True) else "No", border=True)
    tr_cols[1].metric("Futuros permitidos", "No" if not trading.get("allow_futures", False) else "Si", border=True)
    tr_cols[2].metric("Apalancamiento", "No" if not trading.get("allow_leverage", False) else "Si", border=True)


def render() -> None:
    """Render risk settings, kill switch, and circuit breaker state."""
    config = load_settings()
    raw = _load_yaml()
    risk = raw.get("risk", {})
    trading = raw.get("trading", {})

    st.header("Risk Configuration")
    st.caption("Limites y controles de riesgo del sistema")

    col1, col2 = st.columns(2)
    with col1:
        _render_position_sizing(risk)
    with col2:
        _render_exposure_limits(risk)

    st.divider()
    _render_kill_switch(config)
    st.divider()

    st.subheader("Modo de Operacion")
    st.info(f"Modo actual: **{config.mode}**")
    if config.mode in ("real_manual", "real_auto_limited"):
        st.warning("Modo real activo - revisa la configuracion de seguridad")

    st.divider()
    _render_circuit_breaker_state(risk, config)
    st.divider()
    _render_trading_requirements(trading)
    st.caption("Estos valores se leen de settings.yaml. Edita ese archivo para cambios permanentes.")
