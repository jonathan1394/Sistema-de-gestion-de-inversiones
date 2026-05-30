from pathlib import Path

from quality.validators.code_validator import CodeValidator
from quality.validators.security_validator import SecurityValidator
from quality.validators.test_validator import TestValidator
from quality.validators.doc_validator import DocValidator


class TestCodeValidator:
    def test_validate_complexity_empty_project(self, project_root, sample_rules):
        validator = CodeValidator(sample_rules, str(project_root))
        result = validator.validate_complexity()
        assert result.passed
        assert isinstance(result.metrics["files_checked"], int)

    def test_validate_imports_empty_project(self, project_root, sample_rules):
        validator = CodeValidator(sample_rules, str(project_root))
        result = validator.validate_imports()
        assert result.passed


class TestSecurityValidator:
    def test_no_hardcoded_secrets(self, project_root, sample_rules):
        validator = SecurityValidator(sample_rules, str(project_root))
        result = validator.check_hardcoded_secrets()
        assert result.passed
        assert len(result.errors) == 0

    def test_gitignore_check(self, project_root, sample_rules):
        validator = SecurityValidator(sample_rules, str(project_root))
        result = validator.check_gitignore()
        assert result.passed

    def test_detects_hardcoded_secret(self, project_root, sample_rules, tmp_path):
        risky_file = tmp_path / "risky_script.py"
        risky_file.write_text('api_key = "12345-abcde"\n')
        validator = SecurityValidator(sample_rules, str(tmp_path))
        result = validator.check_hardcoded_secrets()
        assert not result.passed
        assert len(result.errors) > 0


class TestTestValidator:
    def test_no_tests_warns(self, project_root, sample_rules, tmp_path):
        validator = TestValidator(sample_rules, str(tmp_path))
        result = validator.validate_test_existence()
        assert result.passed

    def test_test_quality_no_test_files(self, project_root, sample_rules, tmp_path):
        validator = TestValidator(sample_rules, str(tmp_path))
        result = validator.validate_test_quality()
        assert result.passed


class TestDocValidator:
    def test_docstring_coverage_no_files(self, project_root, sample_rules, tmp_path):
        validator = DocValidator(sample_rules, str(tmp_path))
        result = validator.validate_docstrings()
        assert result.passed

    def test_readme_check(self, project_root, sample_rules, tmp_path):
        validator = DocValidator(sample_rules, str(tmp_path))
        result = validator.validate_readme()
        assert result.passed
