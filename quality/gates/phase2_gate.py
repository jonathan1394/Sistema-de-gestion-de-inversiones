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

        self._validate_engine(errors, warnings)

        self._validate_metrics(warnings)

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

    def _validate_engine(self, errors: list[str], warnings: list[str]) -> None:
        engine_code = self.read_file("app/backtesting/engine.py")
        if not engine_code:
            return

        normalized = engine_code.lower()
        if "commission" not in normalized and "fee" not in normalized:
            errors.append("Backtesting engine must include commission modeling")
        if "slippage" not in normalized:
            errors.append("Backtesting engine must include slippage modeling")
        if "position_size" not in normalized:
            warnings.append("Position sizing not explicitly referenced in engine")
        if "stop" not in normalized or "loss" not in normalized:
            warnings.append("Stop-loss not detected in backtesting engine")
        if self._looks_like_bias_check_missing(engine_code, normalized):
            warnings.append("Verify no look-ahead bias in backtesting logic")

    def _validate_metrics(self, warnings: list[str]) -> None:
        metrics_code = self.read_file("app/backtesting/metrics.py")
        if not metrics_code:
            warnings.append("metrics.py not yet implemented")
            return

        normalized = metrics_code.lower()
        for metric in ["sharpe", "drawdown", "profit_factor", "win_rate", "roi"]:
            if metric not in normalized:
                warnings.append(f"Metric '{metric}' not found in metrics.py")

    @staticmethod
    def _looks_like_bias_check_missing(engine_code: str, normalized: str) -> bool:
        if "lookahead" in normalized or "look_ahead" in normalized:
            return False
        if "iloc" in engine_code or "shift" in engine_code:
            return False
        return True
