from typing import Any
from .base_gate import BaseGate, GateResult


class Phase3Gate(BaseGate):
    @property
    def phase(self) -> str:
        return "phase3_risk"

    def validate(self) -> GateResult:
        cfg = self.rules.get("phases", {}).get("phase3_risk", {})
        required = cfg.get("required_files", [])
        errors: list[str] = []
        warnings: list[str] = []

        missing = self.check_required_files(required)
        if missing:
            errors.append(f"Missing required files: {', '.join(missing)}")

        sizing_code = self.read_file("app/risk/position_sizing.py")
        if sizing_code:
            if "0.03" not in sizing_code and "0.01" not in sizing_code:
                warnings.append("Position sizing: expected 1-3% risk constants")
            if "risk" not in sizing_code.lower():
                errors.append("position_sizing.py must calculate based on risk percentage")

        stop_loss_code = self.read_file("app/risk/stop_loss.py")
        if stop_loss_code:
            if "stop" not in stop_loss_code.lower():
                errors.append("stop_loss.py must implement stop-loss logic")
        else:
            errors.append("stop_loss.py is mandatory - stop-loss is required per project rules")

        exposure_code = self.read_file("app/risk/exposure_limits.py")
        if exposure_code:
            if "exposure" not in exposure_code.lower():
                errors.append("exposure_limits.py must enforce exposure limits")

        circuit_code = self.read_file("app/risk/circuit_breakers.py")
        if circuit_code:
            if "kill" not in circuit_code.lower():
                warnings.append("circuit_breakers.py should include kill switch logic")
            if "max_daily_loss" not in circuit_code.lower():
                warnings.append("circuit_breakers.py should check max daily loss")

        passed = len(errors) == 0
        return GateResult(
            gate_name="Phase3Gate",
            phase=self.phase,
            passed=passed,
            duration_ms=0,
            errors=errors,
            warnings=warnings,
            details={
                "required_files_checked": required,
                "missing": missing,
            },
        )
