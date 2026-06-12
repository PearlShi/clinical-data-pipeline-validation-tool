"""
校验器测试
=========
"""

import pytest
import pandas as pd
import numpy as np

from src.validation.validator import Validator
from src.validation.checks.base_check import ValidationIssue, CheckResult
from src.validation.checks.completeness_check import CompletenessCheck
from src.validation.checks.type_check import TypeCheck
from src.validation.checks.range_check import RangeCheck
from src.validation.checks.cdisc_check import CDISCCheck
from src.validation.report import ReportGenerator


class TestValidationIssues:
    """校验问题记录测试"""

    def test_issue_creation(self):
        issue = ValidationIssue(
            check_name="测试检查",
            severity="ERROR",
            description="测试问题",
            column="AGE",
            row_index=0,
            actual_value="999",
            expected="0-120",
            suggestion="请检查",
        )
        assert issue.severity == "ERROR"
        assert issue.column == "AGE"

    def test_issue_to_dict(self):
        issue = ValidationIssue("测试", "WARNING", "描述", column="SEX")
        d = issue.to_dict()
        assert d["check_name"] == "测试"
        assert d["severity"] == "WARNING"

    def test_check_result_status(self):
        result = CheckResult(check_name="测试", status="PASSED")
        assert result.passed
        assert result.issue_count == 0

        result = CheckResult(check_name="测试", status="FAILED")
        assert not result.passed


class TestCompletenessCheck:
    """完整性检查测试"""

    @pytest.fixture
    def complete_df(self):
        return pd.DataFrame({
            "USUBJID": ["S-001", "S-002"],
            "STUDYID": ["STDY01", "STDY01"],
            "DOMAIN": ["DM", "DM"],
            "AGE": [45, 32],
        })

    @pytest.fixture
    def incomplete_df(self):
        return pd.DataFrame({
            "USUBJID": ["S-001", None],
            "STUDYID": [None, "STDY01"],
            "AGE": [45, None],
            "SEX": ["M", "F"],
        })

    def test_check_passes_on_complete_data(self, complete_df):
        checker = CompletenessCheck({
            "variables": ["USUBJID", "STUDYID", "DOMAIN"],
        })
        result = checker.check(complete_df)
        assert result.passed

    def test_check_fails_on_missing(self, incomplete_df):
        checker = CompletenessCheck({
            "variables": ["USUBJID", "STUDYID", "AGE", "DOMAIN"],
        })
        result = checker.check(incomplete_df)
        assert not result.passed
        assert result.issue_count > 0


class TestTypeCheck:
    """类型检查测试"""

    @pytest.fixture
    def df_with_date_issues(self):
        return pd.DataFrame({
            "RFSTDTC": ["2024-01-15", "invalid-date", "2024/03/01", None],
            "AGE": [45, 32, "not_a_number", 28],
        })

    def test_date_format_errors(self, df_with_date_issues):
        checker = TypeCheck({
            "date_variables": ["RFSTDTC"],
            "date_format": "%Y-%m-%d",
        })
        result = checker.check(df_with_date_issues)
        issues = [i for i in result.issues if "日期" in i.description]
        assert len(issues) > 0


class TestRangeCheck:
    """范围检查测试"""

    @pytest.fixture
    def df_with_outliers(self):
        return pd.DataFrame({
            "AGE": [45, 32, 999, 28, -5, 65],
            "WEIGHT": [68.0, 55.0, 550.0, 72.0, 60.0, 80.0],
        })

    def test_out_of_range_detected(self, df_with_outliers):
        checker = RangeCheck({
            "value_ranges": {
                "AGE": {"min": 0, "max": 120},
                "WEIGHT": {"min": 1.0, "max": 300.0},
            }
        })
        result = checker.check(df_with_outliers)
        assert not result.passed
        age_issues = [i for i in result.issues if i.column == "AGE"]
        weight_issues = [i for i in result.issues if i.column == "WEIGHT"]
        assert len(age_issues) > 0
        assert len(weight_issues) > 0


class TestCDISCCheck:
    """CDISC 合规性检查测试"""

    @pytest.fixture
    def valid_df(self):
        return pd.DataFrame({
            "USUBJID": ["STUDY001-SITE01-0001", "STUDY001-SITE01-0002"],
            "STUDYID": ["STUDY001", "STUDY001"],
            "DOMAIN": ["DM", "DM"],
        })

    @pytest.fixture
    def invalid_df(self):
        return pd.DataFrame({
            "USUBJID": ["invalid", "also_bad"],
            "STUDYID": ["study 001", "study 001"],
            "DOMAIN": ["XX", "YY"],
        })

    def test_valid_data_passes(self, valid_df):
        checker = CDISCCheck()
        result = checker.check(valid_df)
        assert result.passed

    def test_invalid_data_fails(self, invalid_df):
        checker = CDISCCheck()
        result = checker.check(invalid_df)
        assert not result.passed


class TestValidator:
    """Validator 集成测试"""

    @pytest.fixture
    def test_df(self):
        return pd.DataFrame({
            "USUBJID": ["STUDY001-SITE01-0001", "STUDY001-SITE01-0002"],
            "STUDYID": ["STUDY001", "STUDY001"],
            "DOMAIN": ["DM", "DM"],
            "AGE": [45, 32],
            "SEX": ["M", "F"],
            "RFSTDTC": ["2024-01-15", "2024-02-20"],
            "RFENDTC": ["2024-06-15", "2024-08-20"],
        })

    def test_validator_runs(self, test_df):
        validator = Validator()
        results = validator.validate(test_df)
        assert len(results) > 0

    def test_validator_summary(self, test_df):
        validator = Validator()
        validator.validate(test_df)
        summary = validator.get_summary()
        assert summary.total_checks > 0
        assert summary.total_checks == summary.passed + summary.failed


class TestReportGenerator:
    """报告生成测试"""

    @pytest.fixture
    def sample_results(self):
        return [
            CheckResult(
                check_name="完整性检查",
                status="PASSED",
                total_checked=10,
                issues=[],
            ),
            CheckResult(
                check_name="类型检查",
                status="FAILED",
                total_checked=10,
                issues=[
                    ValidationIssue("类型检查", "ERROR", "日期格式错误",
                                    column="RFSTDTC", row_index=0),
                ],
            ),
        ]

    def test_markdown_report(self, sample_results):
        from src.validation.validator import ValidationSummary
        summary = ValidationSummary(
            total_checks=2, passed=1, failed=1,
            total_issues=1, errors=1, warnings=0, infos=0,
        )
        gen = ReportGenerator("测试报告")
        md = gen.generate_markdown(sample_results, summary)
        assert len(md) > 0
        assert "测试报告" in md
        assert "完整性检查" in md
        assert "类型检查" in md
