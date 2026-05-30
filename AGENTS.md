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
python -m scripts.compare_backtests --files ./path/to/metrics.json ...

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
