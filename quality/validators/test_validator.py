import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TestValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)


class TestValidator:
    __test__ = False

    def __init__(self, rules: dict[str, Any], project_path: str):
        self.rules = rules.get("testing", {})
        self.project_path = Path(project_path)

    def _get_module_files(self, module: str) -> list[Path]:
        return list((self.project_path / module).rglob("*.py"))

    def _get_test_files(self) -> list[Path]:
        test_dir = self.project_path / "tests"
        if not test_dir.exists():
            return []
        return list(test_dir.rglob("test_*.py"))

    def validate_test_existence(self) -> TestValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        must_have = self.rules.get("must_have_tests_for", [])

        test_files = self._get_test_files()
        if not test_files:
            warnings.append("No test files found (tests/test_*.py)")
            return TestValidationResult(passed=True, warnings=warnings)

        test_names = {t.stem for t in test_files}
        for required in must_have:
            candidates = self._test_name_candidates(required)
            if not any(candidate in test_names for candidate in candidates):
                errors.append(
                    f"No test file found for required module: {required}. "
                    f"Expected one of: {', '.join(f'tests/{c}.py' for c in candidates)}"
                )

        return TestValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            coverage={"test_files_found": len(test_files)},
        )

    def _test_name_candidates(self, required: str) -> set[str]:
        path = Path(required).with_suffix("")
        parts = list(path.parts)
        if parts and parts[0] == "app":
            parts = parts[1:]
        if not parts:
            return set()

        module_name = "_".join(parts)
        package = parts[0]
        leaf = parts[-1]
        return {
            f"test_{module_name}",
            f"test_{package}",
            f"test_{leaf}",
            f"test_{package}_{leaf}",
        }

    def validate_test_quality(self) -> TestValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        for test_file in self._get_test_files():
            try:
                source = test_file.read_text(encoding="utf-8")
                tree = ast.parse(source)

                test_functions = [
                    node.name for node in ast.walk(tree)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name.startswith("test_")
                ]

                if not test_functions:
                    warnings.append(
                        f"{test_file}: No test functions found "
                        f"(functions starting with 'test_')"
                    )
                    continue

                for func_node in ast.walk(tree):
                    if isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not func_node.name.startswith("test_"):
                            continue
                        has_assert = any(
                            isinstance(n, ast.Assert)
                            for n in ast.walk(func_node)
                        )
                        if not has_assert:
                            warnings.append(
                                f"{test_file}:{func_node.lineno} "
                                f"Test '{func_node.name}' has no assert statements"
                            )

            except SyntaxError as e:
                errors.append(f"{test_file}: Syntax error - {e}")

        return TestValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def validate_all(self) -> TestValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        for validator in [self.validate_test_existence, self.validate_test_quality]:
            result = validator()
            errors.extend(result.errors)
            warnings.extend(result.warnings)

        return TestValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
