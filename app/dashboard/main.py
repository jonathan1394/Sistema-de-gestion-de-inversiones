"""Main Streamlit entrypoint for the CriptoLab operational dashboard."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Ensure the app module can be found when running via streamlit
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.logging_setup import setup_logging  # noqa: E402

setup_logging()

import streamlit as st  # noqa: E402

from app.config import load_settings  # noqa: E402
from app.dashboard.portfolio_state import get_portfolio_value, update_portfolio_prices  # noqa: E402
from app.data.market_data import get_candles  # noqa: E402
from app.database.connection import get_connection  # noqa: E402

THEME_CSS = """
        <style>
        :root {
            --brand-bg: #0b0f19;
            --brand-surface: #121a2a;
            --brand-surface-2: #0f1523;
            --brand-border: #263248;
            --brand-text: #e8edf7;
            --brand-muted: #93a0b8;
            --brand-accent: #f0c419;
            --brand-accent-soft: #2a2410;
        }

        .stApp {
            background: radial-gradient(circle at 20% 0%, #141d31 0%, #0b0f19 45%), var(--brand-bg);
            color: var(--brand-text);
            font-family: "DM Sans", "Segoe UI", sans-serif;
        }

        [data-testid="stSidebar"] {
            background: #0b101a;
            border-right: 1px solid #1a2436;
        }

        [data-testid="stSidebar"] * {
            color: #dbe5f6;
        }

        [data-testid="stSidebar"] .stButton > button {
            border-radius: 10px;
            border: 1px solid #24314a;
            background: #10182a;
            font-weight: 600;
            letter-spacing: 0.2px;
            transition: all 0.2s ease;
        }

        [data-testid="stSidebar"] .stButton > button:hover {
            border-color: #3a4d70;
            transform: translateY(-1px);
        }

        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: linear-gradient(90deg, #f0c419, #ffdc56);
            border-color: #f0c419;
            color: #111827;
        }

        [data-testid="stMetric"] {
            background: var(--brand-surface);
            border: 1px solid var(--brand-border);
            border-radius: 12px;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.25);
            padding: 0.4rem 0.6rem;
        }

        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"],
        [data-testid="stMetricDelta"] {
            color: var(--brand-text) !important;
        }

        .stDataFrame, .stTable {
            background: var(--brand-surface);
            border: 1px solid var(--brand-border);
            border-radius: 12px;
        }

        .stTextInput input,
        .stNumberInput input,
        .stSelectbox [data-baseweb="select"] > div {
            background: var(--brand-surface-2) !important;
            border: 1px solid var(--brand-border) !important;
            color: var(--brand-text) !important;
            border-radius: 10px !important;
        }

        .stButton > button {
            border-radius: 10px;
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(90deg, #f0c419, #ffdc56);
            color: #111827;
            border: none;
            font-weight: 700;
        }

        [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] .stAlert {
            border-radius: 12px;
            border: 1px solid var(--brand-border);
            background: var(--brand-surface);
        }

        .page-title {
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--brand-text);
            margin-bottom: 0.2rem;
        }

        .page-subtitle {
            color: var(--brand-muted);
            margin-bottom: 0.7rem;
        }

        .top-strip {
            background: var(--brand-surface);
            border: 1px solid var(--brand-border);
            border-radius: 12px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.9rem;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.22);
        }

        .panel {
            background: var(--brand-surface);
            border: 1px solid var(--brand-border);
            border-radius: 14px;
            padding: 0.7rem 0.9rem;
            margin: 0.4rem 0 0.9rem 0;
            box-shadow: 0 6px 14px rgba(15, 23, 42, 0.04);
        }

        .badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.16rem 0.65rem;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.3px;
            border: 1px solid transparent;
        }

        .badge-pos { background: #112c20; color: #77e0a3; border-color: #275c43; }
        .badge-warn { background: #3a2e0d; color: #ffd56a; border-color: #675324; }
        .badge-neg { background: #37191b; color: #ff9c9c; border-color: #6d2f33; }
        .badge-neutral { background: #1a2539; color: #b6c5df; border-color: #2f4365; }

        .legend-row {
            display: flex;
            gap: 0.45rem;
            flex-wrap: wrap;
            margin: 0.2rem 0 0.7rem 0;
        }

        @media (max-width: 980px) {
            .page-title { font-size: 1.22rem; }
            .top-strip { padding: 0.65rem 0.75rem; }
        }

        .block-container {
            padding-top: 1.2rem;
        }
        </style>
"""


def inject_theme() -> None:
    """Inject global CSS theme and UI component styling."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


st.set_page_config(
    page_title="CriptoLab",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "page" not in st.session_state:
    st.session_state.page = "Overview"
if "portfolio_initialized" not in st.session_state:
    st.session_state.portfolio_initialized = False
if "portfolio_capital" not in st.session_state:
    ini = load_settings().capital.initial_usdt
    st.session_state.portfolio_capital = ini
if "portfolio_cash" not in st.session_state:
    st.session_state.portfolio_cash = st.session_state.portfolio_capital
if "portfolio_positions" not in st.session_state:
    st.session_state.portfolio_positions = {}
if "portfolio_snapshots" not in st.session_state:
    st.session_state.portfolio_snapshots = []
if "portfolio_peak" not in st.session_state:
    st.session_state.portfolio_peak = st.session_state.portfolio_capital
if "active_signals" not in st.session_state:
    st.session_state.active_signals = []

PAGES = {
    "Overview": "app.dashboard.pages.overview",
    "Market Analysis": "app.dashboard.pages.market_analysis",
    "Asset Detail": "app.dashboard.pages.asset_detail",
    "Prospects": "app.dashboard.pages.prospects",
    "Backtesting": "app.dashboard.pages.backtest",
    "Portfolio": "app.dashboard.pages.portfolio",
    "Journal": "app.dashboard.pages.journal",
    "Risk": "app.dashboard.pages.risk",
    "Alerts": "app.dashboard.pages.alerts",
    "Logs": "app.dashboard.pages.logs",
    "Decision Log": "app.dashboard.pages.decision_log",
    "Ranking": "app.dashboard.pages.ranking",
}

_PAGE_MODULES: dict[str, object] = {}


def _load_page_module(page_name: str) -> object | None:
    if page_name in _PAGE_MODULES:
        return _PAGE_MODULES[page_name]
    try:
        if page_name == "Overview":
            from app.dashboard.pages import overview as mod
        elif page_name == "Market Analysis":
            from app.dashboard.pages import market_analysis as mod
        elif page_name == "Asset Detail":
            from app.dashboard.pages import asset_detail as mod
        elif page_name == "Prospects":
            from app.dashboard.pages import prospects as mod
        elif page_name == "Backtesting":
            from app.dashboard.pages import backtest as mod
        elif page_name == "Portfolio":
            from app.dashboard.pages import portfolio as mod
        elif page_name == "Journal":
            from app.dashboard.pages import journal as mod
        elif page_name == "Risk":
            from app.dashboard.pages import risk as mod
        elif page_name == "Alerts":
            from app.dashboard.pages import alerts as mod
        elif page_name == "Logs":
            from app.dashboard.pages import logs as mod
        elif page_name == "Decision Log":
            from app.dashboard.pages import decision_log as mod
        elif page_name == "Ranking":
            from app.dashboard.pages import ranking as mod
        else:
            return None
        _PAGE_MODULES[page_name] = mod
        return mod
    except Exception as exc:
        st.error(f"Error cargando página '{page_name}': {exc}")
        logger.exception("Error importing page module %s", page_name)
        return None


def render_overview_indicators() -> None:
    """Render top-level metrics for capital, PnL, market, and risk state."""
    try:
        config = load_settings()
        conn = get_connection(config.database.path)

        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        prices: dict[str, float] = {}
        for symbol in symbols:
            symbol_candles = get_candles(conn, symbol, "4h", limit=1, desc=True)
            prices[symbol] = symbol_candles[-1].close if symbol_candles else 0.0
        update_portfolio_prices(prices)

        candles = get_candles(conn, "BTCUSDT", "4h", limit=5, desc=True)
        latest_price = candles[-1].close if candles else 0.0

        if candles and len(candles) > 1:
            price_change = (candles[-1].close - candles[0].close) / candles[0].close * 100
        else:
            price_change = 0.0

        tv = get_portfolio_value()
        cap = st.session_state.portfolio_capital
        total_pnl = tv - cap
        total_pnl_pct = (tv - cap) / cap * 100 if cap > 0 else 0.0
        if tv > st.session_state.portfolio_peak:
            st.session_state.portfolio_peak = tv
        dd = (st.session_state.portfolio_peak - tv) / st.session_state.portfolio_peak * 100 if st.session_state.portfolio_peak > 0 else 0
        exposure = (tv - st.session_state.portfolio_cash) / tv * 100 if tv > 0 else 0

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Capital", f"${tv:.2f}", border=True)

        with col2:
            st.metric("PnL", f"${total_pnl:.2f}", f"{total_pnl_pct:+.2f}%", border=True)

        with col3:
            st.metric("BTC/USDT", f"${latest_price:,.2f}", f"{price_change:+.2f}%", border=True)

        with col4:
            status = "⚠️ ON" if config.kill_switch else "✅ OFF"
            st.metric("Kill Switch", status, border=True)

        st.markdown(
            """
            <div class="legend-row">
                <span class="badge badge-neutral">DRAWDOWN</span>
                <span class="badge badge-neutral">EXPOSURE</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"Drawdown: {dd:.2f}%  |  Exposure: {exposure:.1f}%")
    except Exception:
        logger.exception("Error rendering overview indicators")
        st.error("Error loading overview indicators.")


def main() -> None:
    """Render sidebar navigation and selected dashboard page content."""
    try:
        inject_theme()

        with st.sidebar:
            st.title("🧪 CriptoLab")
            st.caption("Private Crypto Investment System")
            st.divider()

            page_icons = {
                "Overview": "🏠",
                "Market Analysis": "📈",
                "Asset Detail": "🧾",
                "Prospects": "🎯",
                "Backtesting": "🔬",
                "Portfolio": "💼",
                "Journal": "📓",
                "Risk": "🛡️",
                "Alerts": "🔔",
                "Logs": "📚",
            }

            for page_name in PAGES:
                if st.button(
                    f"{page_icons.get(page_name, '•')}  {page_name}",
                    use_container_width=True,
                    type="primary" if st.session_state.page == page_name else "secondary",
                ):
                    st.session_state.page = page_name

            st.divider()
            config = load_settings()
            st.caption(f"Mode: **{config.mode}**")
            ks = "⚠️ ACTIVE" if config.kill_switch else "✅ Inactive"
            st.caption(f"Kill Switch: {ks}")

            tv = get_portfolio_value()
            st.caption(f"Portfolio: **${tv:.2f}**")

        st.markdown(
            """
            <div class="top-strip">
                <div class="page-title">CriptoLab</div>
                <div class="page-subtitle">Panel operativo minimalista para mercado, cartera y riesgo.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_overview_indicators()

        page_module = _load_page_module(st.session_state.page)
        if page_module and hasattr(page_module, "render"):
            page_module.render()
    except Exception:
        logger.exception("Error in main dashboard")
        st.error("Error loading dashboard.")


if __name__ == "__main__":
    main()
