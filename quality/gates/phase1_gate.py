from pathlib import Path

from .base_gate import BaseGate, GateResult


class Phase1Gate(BaseGate):
    @property
    def phase(self) -> str:
        return "phase1_data"

    def validate(self) -> GateResult:
        cfg = self.rules.get("phases", {}).get("phase1_data", {})
        required = cfg.get("required_files", [])
        errors: list[str] = []
        warnings: list[str] = []

        missing = self.check_required_files(required)
        if missing:
            errors.append(f"Missing required files: {', '.join(missing)}")

        data_dir = Path(self.project_path) / "app" / "data"
        db_dir = Path(self.project_path) / "app" / "database"

        if data_dir.exists():
            py_files = list(data_dir.glob("*.py"))
            if not py_files:
                warnings.append("data directory exists but contains no Python files")
        else:
            warnings.append("data directory not found yet (Phase 1 not started)")

        if db_dir.exists():
            py_files = list(db_dir.glob("*.py"))
            if not py_files:
                warnings.append("database directory exists but contains no Python files")

        passed = len(errors) == 0
        return GateResult(
            gate_name="Phase1Gate",
            phase=self.phase,
            passed=passed,
            duration_ms=0,
            errors=errors,
            warnings=warnings,
            details={"required_files_checked": required, "missing": missing},
        )
