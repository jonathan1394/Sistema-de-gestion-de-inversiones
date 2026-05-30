from typing import Any
from .base_gate import BaseGate, GateResult


class Phase2Gate(BaseGate):
    @property
    def phase(self) -> str:
        return "phase2_backtesting"

    def validate(self) -> GateResult:
        cfg = self.rules.get("phases", {}).get("phase2_backtesting", {})
        required = cfg.get("required_files", [])
        validations = cfg.get("validations", [])
        errors: list[str] = []
        warnings: list[str] = []

        missing = self.check_required_files(required)
        if missing:
            errors.append(f"Missing required files: {', '.join(missing)}")

        engine_code = self.read_file("app/backtesting/engine.py")
        if engine_code:
            if "commission" not in engine_code.lower() and "fee" not in engine_code.lower():
                errors.append("Backtesting engine must include commission modeling")
            if "slippage" not in engine_code.lower():
                errors.append("Backtesting engine must include slippage modeling")
            if "position_size" not in engine_code.lower():
                warnings.append("Position sizing not explicitly referenced in engine")
            if "stop" in engine_code.lower() and "loss" in engine_code.lower():
                pass
            else:
                warnings.append("Stop-loss not detected in backtesting engine")
            if "lookahead" in engine_code.lower() or "look_ahead" in engine_code.lower():
                pass
            elif "iloc" in engine_code or "shift" in engine_code:
                pass
            else:
                warnings.append("Verify no look-ahead bias in backtesting logic")

        metrics_code = self.read_file("app/backtesting/metrics.py")
        if metrics_code:
            required_metrics = [
                "sharpe", "drawdown", "profit_factor",
                "win_rate", "roi"
            ]
            for metric in required_metrics:
                if metric.lower() not in metrics_code.lower():
                    warnings.append(f"Metric '{metric}' not found in metrics.py")
        else:
            warnings.append("metrics.py not yet implemented")

        passed = len(errors) == 0
        return GateResult(
            gate_name="Phase2Gate",
            phase=self.phase,
            passed=passed,
            duration_ms=0,
            errors=errors,
            warnings=warnings,
            details={
                "required_files_checked": required,
                "missing": missing,
                "validations_checked": validations,
            },
        )
