# CriptoLab - Code Review Checklist

## Before submitting any code, verify ALL items:

### Security (Critical)
- [ ] No hardcoded API keys, secrets, or passwords
- [ ] All secrets use `.env` or environment variables
- [ ] No withdrawal-enabled API keys referenced
- [ ] `KILL_SWITCH` pattern implemented where applicable
- [ ] Stop-loss is mandatory in all trading logic
- [ ] Logs do not contain sensitive data
- [ ] `.gitignore` includes `.env`, `*.pyc`, `__pycache__/`

### Code Quality
- [ ] No syntax errors (run: `ruff check .`)
- [ ] No unused imports or variables
- [ ] Cyclomatic complexity < 15 per function
- [ ] Functions are < 80 lines
- [ ] Files are < 500 lines
- [ ] No wildcard imports (`from x import *`)
- [ ] Code follows PEP 8 (max line length 100)
- [ ] Type hints used for function signatures

### Testing
- [ ] Tests exist for the module being changed
- [ ] Each test function has at least one `assert`
- [ ] Tests are in `/tests/test_*.py` files
- [ ] Critical modules (risk, execution, backtesting) have test coverage > 85%

### Documentation
- [ ] Module-level docstring exists
- [ ] Public functions have docstrings
- [ ] Strategy logic is explained (not just code)
- [ ] Configuration changes are documented in `settings.yaml`

### Phase-Specific
- [ ] Backtesting includes commissions (0.1%) and slippage (0.1%)
- [ ] Strategies have ≥50 trades, profit factor >1.2, Sharpe >1 before promotion
- [ ] Position sizing based on risk %, not fixed amounts
- [ ] Data validation checks for missing/corrupted candles
- [ ] All API calls have error handling and retry logic
- [ ] Timestamps are in UTC
- [ ] Binance rate limits are respected

### Git
- [ ] No `.env` or secrets committed
- [ ] Commit message is clear and follows conventions
- [ ] Only intended files are staged

---

## Pre-commit command

```bash
python -m quality.quality_agent --check-all
```

If this passes, the code is ready for review.
