"""Risk dashboard page for configuration and breaker visibility."""

from __future__ import annotations

import streamlit as st
from loguru import logger

from app.config import load_settings
from app.risk.circuit_breakers import CircuitBreakers


def _render_position_sizing(config) -> None:
    st.subheader("Position Sizing")
    st.metric("Max por operacion", f"{config.risk.max_position_size_pct * 100:.2f}%", border=True)
    st.metric(
        "Riesgo por operacion", f"{config.risk.max_risk_per_trade_pct * 100:.2f}%", border=True
    )
    st.subheader("Stop Loss")
    st.metric(
        "Stop Loss por defecto", f"{config.risk.default_stop_loss_pct * 100:.2f}%", border=True
    )
    st.metric("Stop minimo", f"{config.risk.min_stop_loss_pct * 100:.2f}%", border=True)
    st.metric("Stop maximo", f"{config.risk.max_stop_loss_pct * 100:.2f}%", border=True)


def _render_exposure_limits(config) -> None:
    st.subheader("Exposure Limits")
    st.metric("Max por activo", f"{config.risk.max_asset_exposure_pct * 100:.2f}%", border=True)
    st.metric("Max total", f"{config.risk.max_total_exposure_pct * 100:.2f}%", border=True)
    st.metric("Max altcoins", f"{config.risk.max_altcoin_exposure_pct * 100:.2f}%", border=True)
    st.subheader("Circuit Breakers")
    st.metric("Perdida diaria max", f"{config.risk.max_daily_loss_pct * 100:.2f}%", border=True)
    st.metric("Perdida semanal max", f"{config.risk.max_weekly_loss_pct * 100:.2f}%", border=True)
    st.metric("Perdidas consecutivas", str(config.risk.max_consecutive_losses), border=True)


def _render_kill_switch(config) -> None:
    st.subheader("Kill Switch")
    ks_active = st.checkbox("Activar Kill Switch", value=config.kill_switch)
    if ks_active:
        st.error("KILL SWITCH ACTIVO - No se permiten nuevas operaciones")
    else:
        st.success("Kill Switch inactivo - Operaciones permitidas")
    if ks_active != config.kill_switch:
        st.warning(
            "Cambio solo visual. Usa KILL_SWITCH en el entorno o ajusta la configuracion para persistir."
        )


def _render_circuit_breaker_state(config) -> None:
    st.subheader("Estado Actual del Circuit Breaker")
    cb = CircuitBreakers(
        max_daily_loss_pct=config.risk.max_daily_loss_pct,
        max_weekly_loss_pct=config.risk.max_weekly_loss_pct,
        max_consecutive_losses=config.risk.max_consecutive_losses,
        max_trades_per_day=config.risk.max_trades_per_day,
        kill_switch=config.kill_switch,
    )
    state = cb.state
    cb_cols = st.columns(4)
    cb_cols[0].metric("Perdidas consecutivas", str(state.consecutive_losses), border=True)
    cb_cols[1].metric("Trades hoy", str(state.trades_today), border=True)
    cb_cols[2].metric("Perdida diaria", f"{state.daily_loss_pct:.2f}%", border=True)
    ks_status = "Activo" if state.kill_switch_active else "Inactivo"
    cb_cols[3].metric("Kill Switch", ks_status, border=True)


def _render_trading_requirements(config) -> None:
    st.subheader("Requisitos de Trading")
    tr_cols = st.columns(3)
    tr_cols[0].metric(
        "Requiere Stop Loss", "Si" if config.trading.require_stop_loss else "No", border=True
    )
    tr_cols[1].metric(
        "Futuros permitidos", "No" if not config.trading.allow_futures else "Si", border=True
    )
    tr_cols[2].metric(
        "Apalancamiento", "No" if not config.trading.allow_leverage else "Si", border=True
    )


def render() -> None:
    """Render risk settings, kill switch, and circuit breaker state."""
    try:
        config = load_settings()

        st.header("Risk Configuration")
        st.caption("Limites y controles de riesgo del sistema")

        col1, col2 = st.columns(2)
        with col1:
            _render_position_sizing(config)
        with col2:
            _render_exposure_limits(config)

        st.divider()
        _render_kill_switch(config)
        st.divider()

        st.subheader("Modo de Operacion")
        st.info(f"Modo actual: **{config.mode}**")
        if config.mode in ("real_manual", "real_auto_limited"):
            st.warning("Modo real activo - revisa la configuracion de seguridad")

        st.divider()
        _render_circuit_breaker_state(config)
        st.divider()
        _render_trading_requirements(config)
        st.caption(
            "Estos valores usan la configuracion cargada, incluyendo overrides por variables de entorno."
        )
    except Exception:
        logger.exception("Error rendering risk page")
        st.error("Error loading risk page.")
        st.stop()
