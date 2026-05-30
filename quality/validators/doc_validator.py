import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DocValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    coverage_pct: float = 0.0


class DocValidator:
    def __init__(self, rules: dict[str, Any], project_path: str):
        self.rules = rules.get("documentation", {})
        self.project_path = Path(project_path)

    def _find_python_files(self) -> list[Path]:
        files = list(self.project_path.rglob("*.py"))
        ignore_dirs = {"__pycache__", ".venv", "venv", ".env", ".git", "tests", "scripts"}
        return [
            f for f in files
            if not any(part in ignore_dirs for part in f.parts)
            and "quality" not in f.parts
        ]

    def validate_docstrings(self) -> DocValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        totals = {
            "functions": 0,
            "documented_functions": 0,
            "classes": 0,
            "documented_classes": 0,
            "modules": 0,
            "documented_modules": 0,
        }

        require_module = self.rules.get("require_module_docstrings", True)
        require_function = self.rules.get("require_function_docstrings", True)

        for py_file in self._find_python_files():
            self._validate_file_docstrings(
                py_file=py_file,
                require_module=require_module,
                require_function=require_function,
                warnings=warnings,
                totals=totals,
            )

        total = totals["functions"] + totals["classes"] + totals["modules"]
        documented = (
            totals["documented_functions"]
            + totals["documented_classes"]
            + totals["documented_modules"]
        )
        coverage_pct = (documented / total * 100) if total > 0 else 100

        min_coverage = self.rules.get("min_docstrings_pct", 60)
        if coverage_pct < min_coverage:
            warnings.append(
                f"Docstring coverage: {coverage_pct:.1f}% "
                f"(minimum required: {min_coverage}%)"
            )

        return DocValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            coverage_pct=coverage_pct,
        )

    @staticmethod
    def _has_docstring(body: list[ast.stmt]) -> bool:
        if not body:
            return False
        first = body[0]
        return (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        )

    def _validate_file_docstrings(
        self,
        py_file: Path,
        require_module: bool,
        require_function: bool,
        warnings: list[str],
        totals: dict[str, int],
    ) -> None:
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except SyntaxError:
            return

        totals["modules"] += 1
        if self._has_docstring(tree.body):
            totals["documented_modules"] += 1
        elif require_module and tree.body:
            warnings.append(f"{py_file}: Missing module-level docstring")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._count_function_docstring(node, py_file, require_function, warnings, totals)
            elif isinstance(node, ast.ClassDef):
                totals["classes"] += 1
                if self._has_docstring(node.body):
                    totals["documented_classes"] += 1

    def _count_function_docstring(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        py_file: Path,
        require_function: bool,
        warnings: list[str],
        totals: dict[str, int],
    ) -> None:
        totals["functions"] += 1
        if self._has_docstring(node.body):
            totals["documented_functions"] += 1
            return
        if require_function and not node.name.startswith("_"):
            warnings.append(
                f"{py_file}:{node.lineno} Function '{node.name}' missing docstring"
            )

    def validate_readme(self) -> DocValidationResult:
        warnings: list[str] = []
        readme = self.project_path / "README.md"
        if not readme.exists():
            warnings.append("README.md not found")

        agents_md = self.project_path / "AGENTS.md"
        if not agents_md.exists():
            warnings.append("AGENTS.md not found - this is required for agent guidance")

        return DocValidationResult(
            passed=True,
            warnings=warnings,
        )

    def validate_all(self) -> DocValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        coverage_pct = 0.0

        docstring_result = self.validate_docstrings()
        errors.extend(docstring_result.errors)
        warnings.extend(docstring_result.warnings)
        coverage_pct = docstring_result.coverage_pct

        readme_result = self.validate_readme()
        warnings.extend(readme_result.warnings)

        return DocValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            coverage_pct=coverage_pct,
        )
