import abc
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GateResult:
    gate_name: str
    phase: str
    passed: bool
    duration_ms: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{status}] {self.gate_name} ({self.duration_ms:.1f}ms) "
            f"- {len(self.errors)} errors, {len(self.warnings)} warnings"
        )


class BaseGate(abc.ABC):
    def __init__(self, rules: dict[str, Any], project_path: str):
        self.rules = rules
        self.project_path = project_path
        self._results: list[GateResult] = []

    @property
    @abc.abstractmethod
    def phase(self) -> str:
        ...

    @abc.abstractmethod
    def validate(self) -> GateResult:
        ...

    def run(self) -> GateResult:
        start = time.perf_counter()
        try:
            result = self.validate()
        except Exception as e:
            result = GateResult(
                gate_name=self.__class__.__name__,
                phase=self.phase,
                passed=False,
                duration_ms=0,
                errors=[f"Gate crashed: {e}"],
            )
        result.duration_ms = (time.perf_counter() - start) * 1000
        self._results.append(result)
        return result

    def check_required_files(self, required: list[str]) -> list[str]:
        from pathlib import Path

        missing = []
        for rel_path in required:
            full = Path(self.project_path) / rel_path
            if not full.exists():
                missing.append(rel_path)
        return missing

    def file_exists(self, rel_path: str) -> bool:
        from pathlib import Path

        return (Path(self.project_path) / rel_path).exists()

    def read_file(self, rel_path: str) -> Optional[str]:
        from pathlib import Path

        full = Path(self.project_path) / rel_path
        if full.exists():
            return full.read_text(encoding="utf-8")
        return None
