"""
Agent Report
============
Genera reportes de actividad para auditoría de agentes.
Cada agente que trabaje en CriptoLab debe generar un reporte
que quede registrado en /reports/agent_logs/
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .gates.base_gate import GateResult


class AgentReport:
    def __init__(self, project_path: Path, rules: dict[str, Any]):
        self.project_path = project_path
        self.rules = rules
        self.reports_dir = project_path / "reports" / "agent_logs"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, gate_results: list[GateResult]) -> str:
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": self.rules.get("project", {}).get("name", "CriptoLab"),
            "overall_pass": all(r.passed for r in gate_results) if gate_results else None,
            "gates": [
                {
                    "gate": r.gate_name,
                    "phase": r.phase,
                    "passed": r.passed,
                    "duration_ms": round(r.duration_ms, 1),
                    "error_count": len(r.errors),
                    "warning_count": len(r.warnings),
                    "errors": r.errors[:10],  # limit to first 10
                    "warnings": r.warnings[:10],
                }
                for r in gate_results
            ],
            "summary": {
                "total_gates": len(gate_results),
                "passed": sum(1 for r in gate_results if r.passed),
                "failed": sum(1 for r in gate_results if not r.passed),
                "total_errors": sum(len(r.errors) for r in gate_results),
                "total_warnings": sum(len(r.warnings) for r in gate_results),
            },
        }

        report_path = self.reports_dir / f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return self._format_report(report, report_path)

    def _format_report(self, report: dict, path: Path) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append(f"CriptoLab Agent Report")
        lines.append(f"Timestamp: {report['timestamp']}")
        lines.append(f"Saved to: {path}")
        lines.append("=" * 60)

        for gate in report["gates"]:
            status = "PASS" if gate["passed"] else "FAIL"
            lines.append(
                f"  [{status}] {gate['gate']} ({gate['phase']}) "
                f"- {gate['duration_ms']}ms"
            )
            for e in gate["errors"]:
                lines.append(f"    ERROR: {e}")
            for w in gate["warnings"]:
                lines.append(f"    WARN:  {w}")

        lines.append("-" * 60)
        s = report["summary"]
        lines.append(
            f"Summary: {s['passed']}/{s['total_gates']} gates passed, "
            f"{s['total_errors']} errors, {s['total_warnings']} warnings"
        )
        lines.append("=" * 60)

        return "\n".join(lines)

    def list_recent_reports(self, n: int = 5) -> list[dict]:
        reports = sorted(self.reports_dir.glob("report_*.json"), reverse=True)
        results = []
        for rp in reports[:n]:
            try:
                with open(rp) as f:
                    data = json.load(f)
                results.append({
                    "path": str(rp),
                    "timestamp": data.get("timestamp"),
                    "passed": data.get("overall_pass"),
                    "summary": data.get("summary"),
                })
            except Exception:
                pass
        return results
