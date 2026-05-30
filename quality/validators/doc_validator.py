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
        total_functions = 0
        documented_functions = 0
        total_classes = 0
        documented_classes = 0
        total_modules = 0
        documented_modules = 0

        require_module = self.rules.get("require_module_docstrings", True)
        require_function = self.rules.get("require_function_docstrings", True)

        for py_file in self._find_python_files():
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)

                total_modules += 1
                if tree.body and (
                    isinstance(tree.body[0], ast.Expr)
                    and isinstance(tree.body[0].value, ast.Constant)
                    and isinstance(tree.body[0].value.value, str)
                ):
                    documented_modules += 1
                elif require_module and tree.body:
                    warnings.append(
                        f"{py_file}: Missing module-level docstring"
                    )

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        total_functions += 1
                        if (
                            isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)
                            and isinstance(node.body[0].value.value, str)
                        ):
                            documented_functions += 1
                        elif (
                            require_function
                            and not node.name.startswith("_")
                        ):
                            warnings.append(
                                f"{py_file}:{node.lineno} "
                                f"Function '{node.name}' missing docstring"
                            )

                    elif isinstance(node, ast.ClassDef):
                        total_classes += 1
                        if (
                            isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)
                            and isinstance(node.body[0].value.value, str)
                        ):
                            documented_classes += 1

            except SyntaxError:
                pass

        total = total_functions + total_classes + total_modules
        documented = documented_functions + documented_classes + documented_modules
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
