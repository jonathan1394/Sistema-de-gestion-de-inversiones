import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CodeValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


class CodeValidator:
    def __init__(self, rules: dict[str, Any], project_path: str):
        self.rules = rules.get("code", {})
        self.project_path = Path(project_path)
        self.all_py_files: list[Path] = []

    def _find_python_files(self) -> list[Path]:
        if self.all_py_files:
            return self.all_py_files
        self.all_py_files = list(self.project_path.rglob("*.py"))
        ignore_dirs = {"__pycache__", ".venv", "venv", ".env", ".git", "node_modules"}
        self.all_py_files = [
            f for f in self.all_py_files
            if not any(part in ignore_dirs for part in f.parts)
        ]
        return self.all_py_files

    def validate_complexity(self) -> CodeValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        max_complexity = self.rules.get("complexity", {}).get(
            "max_cyclomatic_complexity", 15
        )
        max_lines = self.rules.get("complexity", {}).get(
            "max_function_length_lines", 80
        )
        max_file_lines = self.rules.get("complexity", {}).get(
            "max_file_length_lines", 500
        )

        for py_file in self._find_python_files():
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)

                lines = source.splitlines()
                if len(lines) > max_file_lines:
                    warnings.append(
                        f"{py_file}: {len(lines)} lines exceeds max {max_file_lines}"
                    )

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func_lines = node.end_lineno - node.lineno
                        if func_lines > max_lines:
                            warnings.append(
                                f"{py_file}:{node.lineno} "
                                f"Function '{node.name}' has {func_lines} lines "
                                f"(max {max_lines})"
                            )
                        complexity = self._compute_complexity(node)
                        if complexity > max_complexity:
                            warnings.append(
                                f"{py_file}:{node.lineno} "
                                f"Function '{node.name}' has cyclomatic complexity "
                                f"{complexity} (max {max_complexity})"
                            )
            except SyntaxError as e:
                errors.append(f"{py_file}: Syntax error - {e}")

        return CodeValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metrics={"files_checked": len(self._find_python_files())},
        )

    def _compute_complexity(self, node: ast.AST) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        return complexity

    def validate_imports(self) -> CodeValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        forbid_wildcard = self.rules.get("imports", {}).get("forbid_wildcard", True)

        for py_file in self._find_python_files():
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and node.module.startswith("."):
                            depth = len(node.module) - len(node.module.lstrip("."))
                            max_depth = self.rules.get("imports", {}).get(
                                "forbid_relative_deep", 2
                            )
                            if depth > max_depth:
                                warnings.append(
                                    f"{py_file}:{node.lineno} "
                                    f"Deep relative import ({node.module})"
                                )
                        if forbid_wildcard:
                            for alias in node.names:
                                if alias.name == "*":
                                    errors.append(
                                        f"{py_file}:{node.lineno} "
                                        "Wildcard import detected"
                                    )
            except SyntaxError:
                pass

        return CodeValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def validate_unused_imports(self) -> CodeValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        for py_file in self._find_python_files():
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
                imports: dict[str, int] = {}
                names_used: set[str] = set()

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            name = alias.asname or alias.name
                            imports[name] = node.lineno
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            name = alias.asname or alias.name
                            imports[name] = node.lineno
                    elif isinstance(node, ast.Name):
                        names_used.add(node.id)

                for name, lineno in imports.items():
                    base = name.split(".")[0]
                    if base not in names_used:
                        warnings.append(
                            f"{py_file}:{lineno} "
                            f"Possible unused import '{name}'"
                        )
            except SyntaxError:
                pass

        return CodeValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def validate_all(self) -> CodeValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        validators = [
            self.validate_complexity,
            self.validate_imports,
            self.validate_unused_imports,
        ]
        for validator in validators:
            result = validator()
            errors.extend(result.errors)
            warnings.extend(result.warnings)

        return CodeValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
