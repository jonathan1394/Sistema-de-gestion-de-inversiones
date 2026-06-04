from types import SimpleNamespace

from quality.gates import (
    Phase1Gate,
    Phase2Gate,
    Phase3Gate,
    Phase4Gate,
    Phase5Gate,
    Phase6Gate,
)
from quality.gates.base_gate import GateResult
from quality.quality_agent import QualityAgent


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
        rules["phases"] = {"phase1_data": {"required_files": ["tmp_test_file.py"]}}
        (tmp_path / "tmp_test_file.py").touch()
        gate = Phase1Gate(rules, str(tmp_path))
        missing = gate.check_required_files(["tmp_test_file.py"])
        assert missing == []


class TestQualityAgent:
    def test_run_all_gates_respects_fail_fast(self, tmp_path):
        agent = QualityAgent(str(tmp_path))
        agent.rules = {
            "agent": {"fail_fast": True},
            "phases": {
                "phase1_data": {"required_files": ["missing.py"]},
                "phase2_backtesting": {"required_files": ["also_missing.py"]},
            },
        }

        results = agent.run_all_gates()

        assert len(results) == 1
        assert not results[0].passed

    def test_run_external_tools_skips_missing_tools(self, tmp_path, monkeypatch):
        agent = QualityAgent(str(tmp_path))
        monkeypatch.setattr("quality.quality_agent.shutil.which", lambda _name: None)

        result = agent.run_external_tools()

        assert result.passed
        assert len(result.warnings) == 2
        assert result.metrics["ruff"] == "missing"
        assert result.metrics["mypy"] == "missing"

    def test_run_external_tools_reports_failures(self, tmp_path, monkeypatch):
        agent = QualityAgent(str(tmp_path))
        monkeypatch.setattr("quality.quality_agent.shutil.which", lambda name: f"/bin/{name}")

        def fake_run(*_args, **_kwargs):
            return SimpleNamespace(returncode=1, stdout="tool failed", stderr="")

        monkeypatch.setattr("quality.quality_agent.subprocess.run", fake_run)

        result = agent.run_external_tools()

        assert not result.passed
        assert len(result.errors) == 2
        assert "ruff failed" in result.errors[0]
