"""Backtesting dashboard page for single and comparative runs."""

from __future__ import annotations

import json
import logging

import pandas as pd
import streamlit as st

from app.backtesting import BacktestEngine, compute_metrics
from app.backtesting.comparator import compare_strategies
from app.config import load_settings
from app.dashboard.helpers import candles_to_dataframe
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.strategies import (
    DCADynamic,
    MovingAverageCrossover,
    RebalanceStrategy,
    RSIStrategy,
    TrendFollowing,
)

logger = logging.getLogger(__name__)


def _strategy_instance(strategy_name: str, symbol: str, params_override: dict | None = None):
    cls_map = {
        "MA Crossover": MovingAverageCrossover,
        "RSI": RSIStrategy,
        "Trend Following": TrendFollowing,
        "DCA Dinámico": DCADynamic,
        "Rebalanceo": RebalanceStrategy,
    }
    strat_cls = cls_map[strategy_name]

    config = load_settings()
    strategies_cfg = config.strategies or {}

    cfg_key = {
        "MA Crossover": "moving_average_crossover",
        "RSI": "rsi_strategy",
        "Trend Following": "trend_following",
        "DCA Dinámico": "dca_dynamic",
        "Rebalanceo": "rebalance",
    }.get(strategy_name, "")

    params: dict = {"symbol": symbol}
    cfg_section = strategies_cfg.get(cfg_key, {}) if cfg_key else {}
    if isinstance(cfg_section, dict):
        params.update(cfg_section)
    if params_override:
        params.update(params_override)
    return strat_cls(parameters=params)  # type: ignore[abstract]


def _render_metrics(metrics) -> None:
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("ROI", f"{metrics.roi_pct:+.2f}%", border=True)
    with col_m2:
        st.metric("Sharpe", f"{metrics.sharpe_ratio:.2f}", border=True)
    with col_m3:
        st.metric("Max DD", f"{metrics.max_drawdown_pct:.2f}%", border=True)
    with col_m4:
        st.metric("Trades", str(metrics.total_trades), border=True)

    col_n1, col_n2, col_n3, col_n4 = st.columns(4)
    with col_n1:
        st.metric("Win Rate", f"{metrics.win_rate:.1f}%", border=True)
    with col_n2:
        st.metric("Profit Factor", f"{metrics.profit_factor:.2f}", border=True)
    with col_n3:
        st.metric("Capital Final", f"${metrics.final_capital:.2f}", border=True)
    with col_n4:
        st.metric("Sortino", f"{metrics.sortino_ratio:.2f}", border=True)


def _render_trades_table(result) -> None:
    with st.expander("Ver todos los trades", expanded=False):
        if not result.trades:
            st.info("No se realizaron trades.")
            return
        trades_df = pd.DataFrame(
            [
                {
                    "Entry": str(t.entry_time),
                    "Exit": str(t.exit_time) if t.exit_time else "-",
                    "Entry $": round(t.entry_price, 2),
                    "Exit $": round(t.exit_price, 2) if t.exit_price else "-",
                    "PnL": round(t.pnl, 2),
                    "PnL%": round(t.pnl_pct * 100, 2),
                    "Bars": t.hold_bars,
                    "Exit Reason": t.reason_exit or "-",
                }
                for t in result.trades
            ]
        )
        st.dataframe(trades_df, use_container_width=True, hide_index=True)


def _render_export_button(result, strategy: str, symbol: str, interval: str) -> None:
    st.divider()
    st.subheader("Exportar")
    trades_json = [
        {
            "entry_time": str(t.entry_time),
            "exit_time": str(t.exit_time),
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "quantity": t.quantity,
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct * 100,
            "reason_entry": t.reason_entry,
            "reason_exit": t.reason_exit,
            "hold_bars": t.hold_bars,
        }
        for t in result.trades
    ]
    st.download_button(
        "📥 Descargar trades (JSON)",
        data=json.dumps(trades_json, indent=2),
        file_name=f"backtest_{strategy.lower().replace(' ', '_')}_{symbol}_{interval}.json",
        mime="application/json",
        use_container_width=True,
    )


def _run_backtest(conn, symbol: str, interval: str, strategy: str,
                  params_override: dict | None, capital: float) -> None:
    candles = get_candles(connection=conn, symbol=symbol, interval=interval, limit=1000)
    if len(candles) < 50:
        st.warning(f"Solo {len(candles)} velas disponibles. Descarga datos primero.")
        st.stop()

    data = candles_to_dataframe(candles)
    strategy_instance = _strategy_instance(strategy, symbol, params_override)
    engine = BacktestEngine(
        strategy=strategy_instance,
        data=data,
        initial_capital=capital,
        symbol=symbol,
        interval=interval,
    )
    result = engine.run()
    metrics = compute_metrics(result)

    st.success(f"Backtest completado - {metrics.total_trades} trades en {len(data)} velas")
    _render_metrics(metrics)

    st.divider()
    st.subheader("Curva de Capital")
    chart_data = result.equity_curve.reset_index()
    chart_data.columns = ["timestamp", "equity"]
    st.line_chart(chart_data, x="timestamp", y="equity")

    _render_trades_table(result)
    _render_export_button(result, strategy, symbol, interval)


def render_compare_section(conn, symbol: str, interval: str, capital: float) -> None:
    """Render and execute the all-strategies comparison block."""
    st.divider()
    st.subheader("Compare All Strategies")
    st.caption("Ejecuta todas las estrategias sobre el mismo activo y timeframe")

    if st.button("Compare All Strategies", type="primary", use_container_width=True):
        with st.spinner("Running all strategies..."):
            try:
                candles = get_candles(
                    connection=conn,
                    symbol=symbol,
                    interval=interval,
                    limit=1000,
                )
                if len(candles) < 50:
                    st.warning(f"Insufficient data ({len(candles)} candles).")
                    return

                data = candles_to_dataframe(candles)

                result = compare_strategies(
                    data=data,
                    symbol=symbol,
                    interval=interval,
                    initial_capital=capital,
                    min_trades=0,
                )

                if not result.strategy_results:
                    st.warning("No strategies produced results.")
                    return

                rows = []
                for sr in result.strategy_results:
                    m = sr.metrics
                    roi_mark = "🟢" if m.roi_pct > 0 else "🔴" if m.roi_pct < 0 else "⚪"
                    rows.append({
                        "Strategy": sr.strategy_name,
                        "ROI%": f"{roi_mark} {m.roi_pct:+.2f}%",
                        "Sharpe": f"{m.sharpe_ratio:.2f}",
                        "Max DD": f"{m.max_drawdown_pct:.2f}%",
                        "PF": f"{m.profit_factor:.2f}",
                        "Win Rate": f"{m.win_rate:.1f}%",
                        "Trades": m.total_trades,
                        "Final Cap": f"${m.final_capital:.2f}",
                        "Valid": "✅" if sr.passed_validation else "⚪",
                    })

                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption("ROI con semaforo visual y validacion por estrategia.")

                best = result.best
                if best:
                    st.success(
                        f"Best strategy: **{best.strategy_name}** "
                        f"(Sharpe {best.metrics.sharpe_ratio:.2f}, "
                        f"ROI {best.metrics.roi_pct:+.2f}%)"
                    )

            except Exception as e:
                st.error(f"Comparison failed: {e}")
                logger.exception("Error in backtest comparison")


def render() -> None:
    """Render backtesting controls, outputs, and strategy comparison."""
    st.markdown('<div class="page-title">🔬 Backtesting</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Compara estrategias con datos historicos y valida robustez antes de operar.</div>',
        unsafe_allow_html=True,
    )

    config = load_settings()
    conn = get_connection(config.database.path)

    col1, col2, col3 = st.columns(3)

    with col1:
        symbol = st.selectbox("Símbolo", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])

    with col2:
        interval = st.selectbox("Intervalo", ["4h", "1h", "1d"])

    with col3:
        strategy = st.selectbox(
            "Estrategia",
            ["MA Crossover", "RSI", "Trend Following", "DCA Dinámico", "Rebalanceo"],
        )

    strategies_cfg = (config.strategies or {}) if hasattr(config, "strategies") else {}

    params_override: dict = {}
    cfg_key = {
        "MA Crossover": "moving_average_crossover",
        "RSI": "rsi_strategy",
        "Trend Following": "trend_following",
        "DCA Dinámico": "dca_dynamic",
        "Rebalanceo": "rebalance",
    }.get(strategy, "")
    strat_cfg = strategies_cfg.get(cfg_key, {}) if isinstance(strategies_cfg, dict) else {}

    if strategy == "MA Crossover":
        col_a, col_b = st.columns(2)
        with col_a:
            fast_default = strat_cfg.get("fast_period", 20)
            fast = st.number_input("Periodo rápido", min_value=5, max_value=100, value=int(fast_default))
            params_override["fast_period"] = fast
        with col_b:
            slow_default = strat_cfg.get("slow_period", 50)
            slow = st.number_input("Periodo lento", min_value=10, max_value=200, value=int(slow_default))
            params_override["slow_period"] = slow
    elif strategy == "RSI":
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            rsi_def = strat_cfg.get("rsi_period", 14)
            params_override["rsi_period"] = st.number_input("RSI Period", min_value=5, max_value=50, value=int(rsi_def))
        with col_b:
            os_def = strat_cfg.get("oversold", 30)
            params_override["oversold"] = st.number_input("Oversold", min_value=10, max_value=50, value=int(os_def))
        with col_c:
            ob_def = strat_cfg.get("overbought", 70)
            params_override["overbought"] = st.number_input("Overbought", min_value=50, max_value=90, value=int(ob_def))
    elif strategy in ("Trend Following", "DCA Dinámico", "Rebalanceo"):
        st.caption(f"Parámetros cargados desde settings.yaml → strategies → {cfg_key}")

    default_capital = int(load_settings().capital.initial_usdt)
    capital = st.number_input("Capital inicial", min_value=100, max_value=100000, value=default_capital, step=100)

    if st.button("🚀 Ejecutar Backtest", type="primary", use_container_width=True):
        with st.spinner("Ejecutando backtest..."):
            try:
                _run_backtest(conn, symbol, interval, strategy, params_override or None, capital)

            except Exception as e:
                st.error(f"Error ejecutando backtest: {e}")
                logger.exception("Error running backtest")
                import traceback
                st.code(traceback.format_exc())

    render_compare_section(conn, symbol, interval, capital)
