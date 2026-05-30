from pathlib import Path

import pytest

from quality.gates import (
    Phase1Gate, Phase2Gate, Phase3Gate,
    Phase4Gate, Phase5Gate, Phase6Gate,
)
from quality.gates.base_gate import GateResult


class TestPhaseGates:
    def test_phase1_gate_has_correct_phase(self, project_root, sample_rules):
        gate = Phase1Gate(sample_rules, str(project_root))
        assert gate.phase == "phase1_data"

    def test_phase2_gate_has_correct_phase(self, project_root, sample_rules):
        gate = Phase2Gate(sample_rules, str(project_root))
        assert gate.phase == "phase2_backtesting"

    def test_phase3_gate_has_correct_phase(self, project_root, sample_rules):
        gate = Phase3Gate(sample_rules, str(project_root))
        assert gate.phase == "phase3_risk"

    def test_phase4_gate_has_correct_phase(self, project_root, sample_rules):
        gate = Phase4Gate(sample_rules, str(project_root))
        assert gate.phase == "phase4_paper_trading"

    def test_phase5_gate_has_correct_phase(self, project_root, sample_rules):
        gate = Phase5Gate(sample_rules, str(project_root))
        assert gate.phase == "phase5_dashboard"

    def test_phase6_gate_has_correct_phase(self, project_root, sample_rules):
        gate = Phase6Gate(sample_rules, str(project_root))
        assert gate.phase == "phase6_binance"

    def test_phase1_gate_runs_without_crash(self, project_root, sample_rules):
        gate = Phase1Gate(sample_rules, str(project_root))
        result = gate.run()
        assert isinstance(result, GateResult)
        assert isinstance(result.passed, bool)

    def test_phase2_gate_runs_without_crash(self, project_root, sample_rules):
        gate = Phase2Gate(sample_rules, str(project_root))
        result = gate.run()
        assert isinstance(result, GateResult)

    def test_gate_result_has_summary(self):
        result = GateResult(
            gate_name="TestGate",
            phase="test",
            passed=True,
            duration_ms=10.5,
            errors=[],
            warnings=["test warning"],
        )
        summary = result.summary
        assert "PASS" in summary
        assert "TestGate" in summary

    def test_gate_result_fail_summary(self):
        result = GateResult(
            gate_name="FailGate",
            phase="test",
            passed=False,
            duration_ms=5.0,
            errors=["something broke"],
        )
        summary = result.summary
        assert "FAIL" in summary


class TestRequiredFilesCheck:
    def test_check_required_files_nonexistent(self, project_root, sample_rules):
        gate = Phase1Gate(sample_rules, str(project_root))
        missing = gate.check_required_files(["nonexistent/file.py"])
        assert "nonexistent/file.py" in missing

    def test_check_required_files_none_missing(self, project_root, sample_rules, tmp_path):
        rules = sample_rules.copy()
        rules["phases"] = {
            "phase1_data": {"required_files": ["tmp_test_file.py"]}
        }
        (tmp_path / "tmp_test_file.py").touch()
        gate = Phase1Gate(rules, str(tmp_path))
        missing = gate.check_required_files(["tmp_test_file.py"])
        assert missing == []
