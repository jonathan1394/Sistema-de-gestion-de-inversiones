import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SecurityValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)


class SecurityValidator:
    def __init__(self, rules: dict[str, Any], project_path: str):
        self.rules = rules.get("security", {})
        self.project_path = Path(project_path)

    def _find_python_files(self) -> list[Path]:
        files = list(self.project_path.rglob("*.py"))
        ignore_dirs = {"__pycache__", ".venv", "venv", ".env", ".git"}
        ignore_prefixes = {"tests"}  # test files may contain intentional secrets
        return [
            f for f in files
            if not any(part in ignore_dirs for part in f.parts)
            and not any(p in f.parts for p in ignore_prefixes)
        ]

    def check_hardcoded_secrets(self) -> SecurityValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        findings: list[dict] = []

        forbidden = self.rules.get("forbidden_patterns", [])
        if not forbidden:
            forbidden = ["api_key", "api_secret", "password", "secret", "private_key"]

        patterns = []
        for pattern in forbidden:
            patterns.append(re.compile(
                rf'(?i){re.escape(pattern)}\s*=\s*["\'][^"\']+["\']'
            ))

        for py_file in self._find_python_files():
            try:
                source = py_file.read_text(encoding="utf-8")
                for i, line in enumerate(source.splitlines(), 1):
                    for p in patterns:
                        match = p.search(line)
                        if match:
                            finding = {
                                "file": str(py_file),
                                "line": i,
                                "pattern": match.group(),
                                "severity": "error",
                            }
                            findings.append(finding)
                            if self.rules.get("fail_on_hardcoded_secrets", True):
                                errors.append(
                                    f"{py_file}:{i} - Hardcoded secret detected: "
                                    f"{match.group()[:60]}"
                                )
                            else:
                                warnings.append(
                                    f"{py_file}:{i} - Possible hardcoded secret"
                                )
            except Exception:
                pass

        return SecurityValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            findings=findings,
        )

    def check_env_usage(self) -> SecurityValidationResult:
        warnings: list[str] = []
        env_file = self.project_path / ".env"
        env_example = self.project_path / "config" / "secrets.example.env"

        if not env_file.exists() and not env_example.exists():
            warnings.append(
                "No .env or config/secrets.example.env found. "
                "Create these before storing any secrets."
            )

        if env_file.exists():
            content = env_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    if "API" in line.upper() or "SECRET" in line.upper():
                        pass

        return SecurityValidationResult(
            passed=True,
            errors=[],
            warnings=warnings,
        )

    def check_gitignore(self) -> SecurityValidationResult:
        warnings: list[str] = []
        gitignore = self.project_path / ".gitignore"

        if not gitignore.exists():
            warnings.append("No .gitignore found. Create one to protect .env and secrets.")
            return SecurityValidationResult(passed=True, warnings=warnings)

        content = gitignore.read_text(encoding="utf-8")
        required_entries = [".env", "*.pyc", "__pycache__/", ".venv/", "venv/"]
        for entry in required_entries:
            if entry not in content:
                warnings.append(f".gitignore missing entry: {entry}")

        return SecurityValidationResult(
            passed=True,
            warnings=warnings,
        )

    def validate_all(self) -> SecurityValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        findings: list[dict] = []

        secrets_result = self.check_hardcoded_secrets()
        errors.extend(secrets_result.errors)
        warnings.extend(secrets_result.warnings)
        findings.extend(secrets_result.findings)

        env_result = self.check_env_usage()
        warnings.extend(env_result.warnings)

        gitignore_result = self.check_gitignore()
        warnings.extend(gitignore_result.warnings)

        return SecurityValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            findings=findings,
        )
