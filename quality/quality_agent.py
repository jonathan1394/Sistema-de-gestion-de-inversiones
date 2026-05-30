#!/usr/bin/env python3
"""
CriptoLab Quality Agent
=======================
Main entry point for quality verification.
All agents MUST run this before making commits or merging code.

Usage:
    python -m quality.quality_agent --check-all
    python -m quality.quality_agent --phase phase1
    python -m quality.quality_agent --gate Phase1Gate
    python -m quality.quality_agent --report
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from .gates import (
    Phase1Gate, Phase2Gate, Phase3Gate,
    Phase4Gate, Phase5Gate, Phase6Gate,
)
from .gates.base_gate import GateResult
from .validators import CodeValidator, SecurityValidator, TestValidator, DocValidator
from .agent_report import AgentReport


class QualityAgent:
    def __init__(self, project_path: Optional[str] = None):
        self.project_path = Path(project_path or self._find_project_root())
        self.rules = self._load_rules()
        self.results: list[GateResult] = []
        self.start_time: float = 0.0
        self.report = AgentReport(self.project_path, self.rules)

    def _find_project_root(self) -> str:
        current = Path(__file__).resolve().parent.parent
        markers = ["AGENTS.md", "planing.md", "quality"]
        for parent in [current] + list(current.parents):
            if all((parent / m).exists() for m in markers if m != "quality"):
                return str(parent)
            if (parent / "quality").exists():
                return str(parent)
        return str(current)

    def _load_rules(self) -> dict[str, Any]:
        rules_path = Path(__file__).parent / "rules.yaml"
        if not rules_path.exists():
            print(f"[WARNING] rules.yaml not found at {rules_path}, using defaults")
            return {}
        with open(rules_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def run_all_gates(self) -> list[GateResult]:
        gates = [
            Phase1Gate(self.rules, str(self.project_path)),
            Phase2Gate(self.rules, str(self.project_path)),
            Phase3Gate(self.rules, str(self.project_path)),
            Phase4Gate(self.rules, str(self.project_path)),
            Phase5Gate(self.rules, str(self.project_path)),
            Phase6Gate(self.rules, str(self.project_path)),
        ]
        results = []
        for gate in gates:
            result = gate.run()
            results.append(result)
            print(result.summary)

        self.results.extend(results)
        return results

    def run_phase(self, phase: str) -> Optional[GateResult]:
        gate_map = {
            "phase1": Phase1Gate,
            "phase2": Phase2Gate,
            "phase3": Phase3Gate,
            "phase4": Phase4Gate,
            "phase5": Phase5Gate,
            "phase6": Phase6Gate,
        }
        gate_class = gate_map.get(phase)
        if not gate_class:
            print(f"[ERROR] Unknown phase: {phase}")
            print(f"  Available: {', '.join(gate_map.keys())}")
            return None

        gate = gate_class(self.rules, str(self.project_path))
        result = gate.run()
        print(result.summary)
        self.results.append(result)
        return result

    def run_gate(self, gate_name: str) -> Optional[GateResult]:
        gate_map = {
            "Phase1Gate": Phase1Gate,
            "Phase2Gate": Phase2Gate,
            "Phase3Gate": Phase3Gate,
            "Phase4Gate": Phase4Gate,
            "Phase5Gate": Phase5Gate,
            "Phase6Gate": Phase6Gate,
        }
        gate_class = gate_map.get(gate_name)
        if not gate_class:
            print(f"[ERROR] Unknown gate: {gate_name}")
            print(f"  Available: {', '.join(gate_map.keys())}")
            return None

        gate = gate_class(self.rules, str(self.project_path))
        result = gate.run()
        print(result.summary)
        self.results.append(result)
        return result

    def run_validators(self) -> dict[str, Any]:
        print("\n--- Running Code Validators ---")
        code_val = CodeValidator(self.rules, str(self.project_path))
        code_result = code_val.validate_all()
        print(f"  Code: {'PASS' if code_result.passed else 'FAIL'} "
              f"({len(code_result.errors)} errors, {len(code_result.warnings)} warnings)")
        for e in code_result.errors:
            print(f"    ERROR: {e}")
        for w in code_result.warnings:
            print(f"    WARN:  {w}")

        print("\n--- Running Security Validators ---")
        sec_val = SecurityValidator(self.rules, str(self.project_path))
        sec_result = sec_val.validate_all()
        print(f"  Security: {'PASS' if sec_result.passed else 'FAIL'} "
              f"({len(sec_result.errors)} errors, {len(sec_result.warnings)} warnings)")
        for e in sec_result.errors:
            print(f"    ERROR: {e}")
        for w in sec_result.warnings:
            print(f"    WARN:  {w}")

        print("\n--- Running Test Validators ---")
        test_val = TestValidator(self.rules, str(self.project_path))
        test_result = test_val.validate_all()
        print(f"  Tests: {'PASS' if test_result.passed else 'FAIL'} "
              f"({len(test_result.errors)} errors, {len(test_result.warnings)} warnings)")
        for e in test_result.errors:
            print(f"    ERROR: {e}")
        for w in test_result.warnings:
            print(f"    WARN:  {w}")

        print("\n--- Running Documentation Validators ---")
        doc_val = DocValidator(self.rules, str(self.project_path))
        doc_result = doc_val.validate_all()
        print(f"  Docs: {'PASS' if doc_result.passed else 'FAIL'} "
              f"({len(doc_result.errors)} errors, {len(doc_result.warnings)} warnings)")
        for e in doc_result.errors:
            print(f"    ERROR: {e}")
        for w in doc_result.warnings:
            print(f"    WARN:  {w}")

        return {
            "code": code_result,
            "security": sec_result,
            "tests": test_result,
            "docs": doc_result,
        }

    def check_all(self) -> bool:
        print("=" * 60)
        print(f"CriptoLab Quality Check")
        print(f"Started: {datetime.now(timezone.utc).isoformat()}")
        print(f"Project: {self.project_path}")
        print("=" * 60)

        self.start_time = time.perf_counter()

        gate_results = self.run_all_gates()
        validator_results = self.run_validators()

        elapsed = (time.perf_counter() - self.start_time) * 1000

        all_passed = all(r.passed for r in gate_results)
        val_all_passed = all(
            v.passed for v in validator_results.values()
        )
        overall = all_passed and val_all_passed

        print("\n" + "=" * 60)
        print(f"OVERALL RESULT: {'PASS' if overall else 'FAIL'}")
        print(f"Duration: {elapsed:.1f}ms")
        print()

        self.generate_report()

        if overall:
            print("All quality gates passed. Code is ready for review.")
        else:
            print("Some quality gates failed. Review errors above and fix before committing.")
        print("=" * 60)

        return overall

    def generate_report(self) -> str:
        from .agent_report import AgentReport
        report = AgentReport(self.project_path, self.rules)
        return report.generate(self.results)

    def validate_phase_complete(self, phase: str) -> bool:
        result = self.run_phase(phase)
        if not result:
            return False
        return result.passed


def main():
    parser = argparse.ArgumentParser(
        description="CriptoLab Quality Agent - Verify code quality before commits"
    )
    parser.add_argument(
        "--check-all", action="store_true",
        help="Run all quality gates and validators"
    )
    parser.add_argument(
        "--phase", type=str,
        help="Run specific phase gate (phase1, phase2, ... phase6)"
    )
    parser.add_argument(
        "--gate", type=str,
        help="Run specific gate (Phase1Gate, Phase2Gate, ...)"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Generate agent activity report"
    )
    parser.add_argument(
        "--project-path", type=str, default=None,
        help="Override project root path"
    )

    args = parser.parse_args()

    agent = QualityAgent(project_path=args.project_path)

    if args.check_all:
        success = agent.check_all()
        sys.exit(0 if success else 1)
    elif args.phase:
        agent.run_phase(args.phase)
    elif args.gate:
        agent.run_gate(args.gate)
    elif args.report:
        recent = agent.report.list_recent_reports(5)
        if not recent:
            print("No reports found. Run --check-all first to generate a report.")
        else:
            print("Recent quality reports:")
            print("-" * 60)
            for r in recent:
                status = (
                    "PASS" if r["passed"] is True
                    else "FAIL" if r["passed"] is False
                    else "N/A"
                )
                summary = r.get("summary", {})
                print(f"  [{status}] {r['timestamp']}")
                if summary:
                    print(f"         {summary.get('passed', 0)}/{summary.get('total_gates', 0)} gates, "
                          f"{summary.get('total_errors', 0)} errors, "
                          f"{summary.get('total_warnings', 0)} warnings")
                print(f"         File: {r['path']}")
                print()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
