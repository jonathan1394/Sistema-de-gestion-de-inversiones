from typing import Any
from .base_gate import BaseGate, GateResult


class Phase6Gate(BaseGate):
    @property
    def phase(self) -> str:
        return "phase6_binance"

    def validate(self) -> GateResult:
        cfg = self.rules.get("phases", {}).get("phase6_binance", {})
        required = cfg.get("required_files", [])
        errors: list[str] = []
        warnings: list[str] = []

        missing = self.check_required_files(required)
        if missing:
            errors.append(f"Missing required files: {', '.join(missing)}")

        executor = self.read_file("app/execution/binance_executor.py")
        if executor:
            if "read" in executor.lower() and "only" in executor.lower():
                pass
            else:
                warnings.append("First connection should be read-only")
            if "withdrawal" in executor.lower():
                errors.append(
                    "CRITICAL: binance_executor.py references withdrawals - "
                    "this is forbidden by project security rules"
                )
            if "retry" not in executor.lower():
                warnings.append("Missing retry logic for API calls")
            if "error" not in executor.lower():
                warnings.append("Missing error handling for API calls")

        safety = self.read_file("app/execution/safety_checks.py")
        if safety:
            if "kill" not in safety.lower():
                errors.append("safety_checks.py must include kill switch check")
            if "risk" not in safety.lower():
                warnings.append("safety_checks.py should validate risk before execution")
        else:
            errors.append("safety_checks.py is mandatory")

        order_mgr = self.read_file("app/execution/order_manager.py")
        if order_mgr:
            if "log" not in order_mgr.lower():
                warnings.append("order_manager.py must log all orders")

        env_file = self.read_file(".env")
        if not env_file:
            secrets_example = self.read_file("config/secrets.example.env")
            if not secrets_example:
                warnings.append(
                    "No .env or config/secrets.example.env found. "
                    "Secrets management must be configured before Binance connection."
                )

        passed = len(errors) == 0
        return GateResult(
            gate_name="Phase6Gate",
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
