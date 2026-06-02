from .base_gate import BaseGate, GateResult


class Phase5Gate(BaseGate):
    @property
    def phase(self) -> str:
        return "phase5_dashboard"

    def validate(self) -> GateResult:
        cfg = self.rules.get("phases", {}).get("phase5_dashboard", {})
        required = cfg.get("required_files", [])
        errors: list[str] = []
        warnings: list[str] = []

        missing = self.check_required_files(required)
        if missing:
            errors.append(f"Missing required files: {', '.join(missing)}")

        main_dash = self.read_file("app/dashboard/main.py")
        if main_dash:
            if "streamlit" not in main_dash.lower() and "st." not in main_dash:
                warnings.append("Dashboard should use Streamlit as per project tech stack")
            checks = {
                "capital": "capital" in main_dash.lower(),
                "pnl": "pnl" in main_dash.lower() or "profit" in main_dash.lower(),
                "drawdown": "drawdown" in main_dash.lower(),
                "exposure": "exposure" in main_dash.lower(),
                "signals": "signal" in main_dash.lower(),
                "status": "status" in main_dash.lower(),
            }
            missing_indicators = [k for k, v in checks.items() if not v]
            if missing_indicators:
                warnings.append(
                    f"Dashboard missing indicators: {', '.join(missing_indicators)}"
                )
        else:
            warnings.append("Dashboard not yet implemented")

        from pathlib import Path
        pages_dir_exists = (Path(self.project_path) / "app" / "dashboard" / "pages").exists()
        if not pages_dir_exists:
            warnings.append("dashboard/pages/ directory not yet created")

        passed = len(errors) == 0
        return GateResult(
            gate_name="Phase5Gate",
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
