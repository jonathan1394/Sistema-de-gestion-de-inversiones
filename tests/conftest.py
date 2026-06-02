import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def sample_rules() -> dict:
    return {
        "project": {"name": "CriptoLab", "min_python_version": "3.10"},
        "code": {
            "complexity": {
                "max_cyclomatic_complexity": 15,
                "max_function_length_lines": 80,
                "max_file_length_lines": 500,
            },
            "imports": {
                "forbid_wildcard": True,
                "forbid_relative_deep": 2,
            },
        },
        "testing": {
            "min_coverage_pct": 70,
            "critical_modules_coverage_pct": 85,
            "must_have_tests_for": [
                "risk/position_sizing.py",
                "backtesting/engine.py",
            ],
        },
        "security": {
            "forbidden_patterns": ["api_key", "api_secret"],
            "fail_on_hardcoded_secrets": True,
        },
        "documentation": {
            "min_docstrings_pct": 60,
            "require_module_docstrings": True,
        },
        "phases": {
            "phase1_data": {
                "required_files": [
                    "data/binance_client.py",
                    "database/models.py",
                ],
            },
            "phase2_backtesting": {
                "required_files": ["backtesting/engine.py"],
                "validations": ["includes_commissions"],
            },
        },
    }
