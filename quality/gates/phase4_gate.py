from typing import Any
from .base_gate import BaseGate, GateResult


class Phase4Gate(BaseGate):
    @property
    def phase(self) -> str:
        return "phase4_paper_trading"

    def validate(self) -> GateResult:
        cfg = self.rules.get("phases", {}).get("phase4_paper_trading", {})
        required = cfg.get("required_files", [])
        errors: list[str] = []
        warnings: list[str] = []

        missing = self.check_required_files(required)
        if missing:
            errors.append(f"Missing required files: {', '.join(missing)}")

        simulator = self.read_file("app/paper_trading/simulator.py")
        if simulator:
            if "virtual" not in simulator.lower() and "paper" not in simulator.lower():
                warnings.append("simulator.py should reference virtual/paper trading")
            if "order" not in simulator.lower():
                warnings.append("simulator.py must handle order simulation")
            if "price" not in simulator.lower():
                warnings.append("simulator.py must track prices")
        else:
            warnings.append("simulator.py not yet implemented")

        portfolio = self.read_file("app/paper_trading/virtual_portfolio.py")
        if portfolio:
            if "balance" not in portfolio.lower():
                warnings.append("virtual_portfolio.py must track balance")
        else:
            warnings.append("virtual_portfolio.py not yet implemented")

        passed = len(errors) == 0
        return GateResult(
            gate_name="Phase4Gate",
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
