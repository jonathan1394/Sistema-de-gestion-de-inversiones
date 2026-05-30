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

        self._validate_executor(errors, warnings)

        self._validate_safety_checks(errors, warnings)

        self._validate_order_manager(warnings)

        self._validate_secrets_presence(warnings)

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

    def _validate_executor(self, errors: list[str], warnings: list[str]) -> None:
        executor = self.read_file("app/execution/binance_executor.py")
        if not executor:
            return

        normalized = executor.lower()
        if "read" not in normalized or "only" not in normalized:
            warnings.append("First connection should be read-only")
        if "withdrawal" in normalized:
            errors.append(
                "CRITICAL: binance_executor.py references withdrawals - "
                "this is forbidden by project security rules"
            )
        if "retry" not in normalized:
            warnings.append("Missing retry logic for API calls")
        if "error" not in normalized:
            warnings.append("Missing error handling for API calls")

    def _validate_safety_checks(self, errors: list[str], warnings: list[str]) -> None:
        safety = self.read_file("app/execution/safety_checks.py")
        if not safety:
            errors.append("safety_checks.py is mandatory")
            return

        normalized = safety.lower()
        if "kill" not in normalized:
            errors.append("safety_checks.py must include kill switch check")
        if "risk" not in normalized:
            warnings.append("safety_checks.py should validate risk before execution")

    def _validate_order_manager(self, warnings: list[str]) -> None:
        order_mgr = self.read_file("app/execution/order_manager.py")
        if order_mgr and "log" not in order_mgr.lower():
            warnings.append("order_manager.py must log all orders")

    def _validate_secrets_presence(self, warnings: list[str]) -> None:
        env_file = self.read_file(".env")
        if env_file:
            return
        secrets_example = self.read_file("config/secrets.example.env")
        if secrets_example:
            return
        warnings.append(
            "No .env or config/secrets.example.env found. "
            "Secrets management must be configured before Binance connection."
        )
