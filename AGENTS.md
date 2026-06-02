# CriptoLab Agent Guidelines

## Project
Private crypto investment app focused on disciplined trading. All source under `app/`. Python 3.10+, Pandas, SQLite, Streamlit. Entry points are `scripts/*.py` (run as `python -m scripts.<name>`).

## Critical Architecture
- **Config**: `load_settings("settings.yaml")` in `app/config.py`. Env var overrides: `APP_MODE`, `KILL_SWITCH`, `DATABASE_PATH`. `secrets.example.env` shows required vars.
- **Database**: SQLite via `app/database/connection.py`. Migrations auto-run in download script (`app/database/migrations.py`).
- **Risk execution order**: Strategy → Risk Check (circuit breakers → stop loss → position sizing → exposure limits) → Safety Checks (mode, kill switch, binance perms) → Execution
- **Modes**: `analysis`, `backtest`, `paper`, `real_manual`, `real_auto_limited` (last two blocked by default)

## Essential Commands
```bash
# Run from project root
python -m scripts.download_historical --symbol BTCUSDT --interval 1h --start-ms <ms> --end-ms <ms> [--paginate]
python -m scripts.run_backtest_ma --symbol BTCUSDT --interval 1h --fast 20 --slow 50 --capital 1000
python -m scripts.run_backtest --symbol BTCUSDT --interval 1h --strategy ma --fast 10 --slow 30 --capital 1000
python -m scripts.run_paper_trading --symbol BTCUSDT --interval 1h --strategy ma --fast 20 --slow 50
python -m scripts.run_prospecting --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1d
python -m scripts.compare_backtests --files ./path/to/metrics.json ...
python -m scripts.compare_strategies --symbols BTCUSDT,ETHUSDT --intervals 1h,4h --strategies ma,rsi,trend

# Quality gate (MANDATORY before any commit)
python -m quality.quality_agent --check-all

# Lint / typecheck / test
ruff check app/ tests/
mypy app/
pytest
```

## Toolchain Details
- **Line length**: 100 (ruff + black). **Target**: py310.
- **Lint**: ruff with E, F, W, I, N rules (E501 excluded). Format: ruff with double quotes.
- **Mypy**: `strict=false`, `ignore_missing_imports=true`.
- **Pre-commit** hooks: ruff (--fix), ruff-format, trailing-whitespace, end-of-file-fixer, check-yaml, detect-private-key, quality agent.
- **pytest**: conftest adds project root to `sys.path`. Test files: `tests/test_*.py`.
- **Config files**: `settings.yaml` at root or `config/settings.yaml`; secrets in `.env` (not committed).

## Quality System
Comprehensive gate/validator system at `quality/`. Gates (Phase1–Phase6) verify data pipeline, backtesting, risk, paper trading, dashboard, binance connectivity. Validators check code complexity, security (hardcoded secrets), test coverage, docstrings. Config at `quality/rules.yaml`. Reports at `reports/agent_logs/report_*.json`.

## Repo-Specific Conventions
- All timestamps in UTC milliseconds
- Backtests must model commissions (0.1%) and slippage (0.1%)
- Strategies need ≥50 trades, profit factor >1.2, Sharpe >1 for promotion
- Position sizing based on risk %, not fixed amounts
- No futures/leverage in initial version
- Never commit `.env`, `config/secrets.env`, `*.db`, or `reports/agent_logs/`

## Session Summary — Fase 2 (2026-06-02)
### Completed
- **2.1 Strategy Registry**: Auto-discovery via entry_points, fallback import, lazy loading.
- **2.2 Short Positions**: VirtualPortfolio sell/short/buy/cover, BacktestEngine short entries/exits, trailing stop for shorts (`is_short` param), config `allow_shorts`, metrics track short trades separately.
- **2.3 Trailing Stop + TP Dinámico**: `TrailingStop` class, `take_profit_dynamic()` based on ATR, integrated into RiskManager and BacktestEngine.
- **2.4 Data Layer**: `connection_scope()` context manager, `DataAccessObject` class, Alembic migration for indexes, batch store_klines with chunking.
- **2.5 Dashboard Refactor**: Helpers (`candles_to_dataframe`, `get_current_price`, `get_portfolio_value`, `update_portfolio_prices`, `add_snapshot`), `portfolio_state.py` cleanup, `main.py` explicit imports, `asset_detail.py` deduplication, strategies loaded from config.
### Test Count: 211 (was 129)
### Known Issues
- `asset_detail.py:render()` has high cyclomatic complexity (20) and length (122 lines) — pre-existing
- `docker-compose.yml` references `app/main.py` which doesn't exist yet
- `_render_backtest_comparison` calls `compare_strategies` — may not handle empty backtest results gracefully
