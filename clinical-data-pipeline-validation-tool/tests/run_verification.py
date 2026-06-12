#!/usr/bin/env python
"""
项目功能验证脚本
==============
由于网络限制无法安装 pytest，此脚本使用 unittest 验证核心功能。
"""

import sys
import os
import unittest
from pathlib import Path

# 将项目根目录添加到系统路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

os.environ["PYTHONIOENCODING"] = "utf-8"


class TestDataLoader(unittest.TestCase):
    """数据加载模块测试"""

    def setUp(self):
        from src.core.data_loader import DataLoader
        self.DataLoader = DataLoader

    def test_load_csv(self):
        sample_file = project_root / "data" / "sample_dm_data.csv"
        self.assertTrue(sample_file.exists(), f"示例数据文件不存在: {sample_file}")
        loader = self.DataLoader(str(sample_file))
        df = loader.load()
        self.assertGreater(len(df), 0)
        self.assertIn("USUBJID", df.columns)

    def test_load_excel(self):
        sample_file = project_root / "data" / "sample_clinical_data.xlsx"
        self.assertTrue(sample_file.exists())
        loader = self.DataLoader(str(sample_file))
        df = loader.load()
        self.assertGreater(len(df), 0)

    def test_load_with_preview(self):
        sample_file = project_root / "data" / "sample_dm_data.csv"
        loader = self.DataLoader(str(sample_file))
        df, preview = loader.load_with_preview()
        self.assertIn("rows", preview)
        self.assertIn("columns", preview)
        self.assertEqual(preview["rows"], len(df))


class TestValidator(unittest.TestCase):
    """校验器测试"""

    def setUp(self):
        from src.validation.validator import Validator
        from src.core.data_loader import DataLoader
        self.Validator = Validator
        sample_file = project_root / "data" / "sample_dm_data.csv"
        loader = DataLoader(str(sample_file))
        self.df = loader.load()

    def test_validator_runs(self):
        validator = self.Validator()
        results = validator.validate(self.df)
        self.assertGreater(len(results), 0)

    def test_validator_detects_issues(self):
        """示例数据包含故意引入的问题，校验器应发现问题"""
        validator = self.Validator()
        results = validator.validate(self.df)
        all_issues = []
        for r in results:
            all_issues.extend(r.issues)
        # 示例数据中存在日期格式错误、异常值等问题
        self.assertGreater(len(all_issues), 0,
                          "预期能发现数据质量问题")

    def test_validation_summary(self):
        validator = self.Validator()
        validator.validate(self.df)
        summary = validator.get_summary()
        self.assertGreater(summary.total_checks, 0)
        self.assertTrue(summary.failed > 0 or summary.passed > 0)


class TestChecks(unittest.TestCase):
    """单项检查器测试"""

    def setUp(self):
        import pandas as pd
        self.df = pd.DataFrame({
            "USUBJID": ["STUDY001-SITE01-0001", "INVALID-ID"],
            "STUDYID": ["STUDY001", "STUDY001"],
            "DOMAIN": ["DM", "XX"],
            "AGE": [45, 999],
            "SEX": ["M", "Unknown"],
            "RFSTDTC": ["2024-01-15", "2024/13/01"],
            "RFENDTC": ["2024-06-15", "2024-01-01"],
        })

    def test_completeness_check(self):
        from src.validation.checks.completeness_check import CompletenessCheck
        checker = CompletenessCheck()
        result = checker.check(self.df)
        self.assertIsNotNone(result)

    def test_type_check(self):
        from src.validation.checks.type_check import TypeCheck
        checker = TypeCheck()
        result = checker.check(self.df)
        self.assertIsNotNone(result)

    def test_range_check(self):
        from src.validation.checks.range_check import RangeCheck
        checker = RangeCheck({
            "value_ranges": {
                "AGE": {"min": 0, "max": 120, "description": "年龄"},
            }
        })
        result = checker.check(self.df)
        self.assertIsNotNone(result)

    def test_cdisc_check(self):
        from src.validation.checks.cdisc_check import CDISCCheck
        checker = CDISCCheck()
        result = checker.check(self.df)
        self.assertIsNotNone(result)


class TestConverter(unittest.TestCase):
    """格式转换模块测试"""

    def setUp(self):
        import pandas as pd
        from src.conversion.variable_mapper import VariableMapper
        self.VariableMapper = VariableMapper
        self.sample_df = pd.DataFrame({
            "SUBJID": ["0001", "0002"],
            "SITEID": ["SITE01", "SITE01"],
            "AGE": [45, 32],
            "SEX": ["M", "F"],
            "RFSTDTC": ["2024-01-15", "2024-02-20"],
        })

    def test_variable_mapper(self):
        mapper = self.VariableMapper()
        std, conf = mapper.map_variable_name("AGE")
        self.assertEqual(std, "AGE")
        self.assertGreater(conf, 0)

    def test_variable_generator(self):
        from src.conversion.variable_generator import VariableGenerator
        gen = VariableGenerator()
        usubjid = gen.generate_usubjid(self.sample_df)
        self.assertEqual(len(usubjid), 2)
        self.assertIn("STUDY001", usubjid.iloc[0])

    def test_conversion_log(self):
        from src.conversion.conversion_log import ConversionLog
        log = ConversionLog(study_id="TEST", domain="DM")
        log.add_step("Test Step", "生成", "Test details", affected_rows=10)
        summary = log.get_summary()
        self.assertEqual(summary["total_steps"], 1)


class TestScripts(unittest.TestCase):
    """可复用脚本测试"""

    def setUp(self):
        import pandas as pd
        self.df = pd.DataFrame({
            "USUBJID": ["S-001", "S-002", "S-001"],
            "AGE": [45.0, None, 45.0],
            "SEX": ["M", "F", "M"],
        })

    def test_data_cleaner(self):
        from src.scripts.clean_data import DataCleaner
        result = DataCleaner.remove_duplicates(self.df)
        self.assertEqual(len(result), 2)  # 去重后应为 2 行

        result = DataCleaner.strip_whitespace(self.df)
        self.assertEqual(result.iloc[0]["SEX"], "M")

    def test_statistical_checker(self):
        from src.scripts.stats_checks import StatisticalChecker
        import numpy as np
        import pandas as pd

        test_df = pd.DataFrame({
            "AGE": np.random.normal(45, 10, 50),
            "SEX": np.random.choice(["M", "F"], 50),
        })
        desc = StatisticalChecker.describe_dataset(test_df)
        self.assertIn("AGE", desc["numeric_summary"])

    def test_outlier_detection(self):
        from src.scripts.outlier_detection import OutlierDetector
        import numpy as np
        import pandas as pd

        vals = np.random.normal(50, 10, 100)
        vals[0] = 999
        test_df = pd.DataFrame({"VALUE": vals})
        result = OutlierDetector.iqr_method(test_df, "VALUE")
        self.assertGreater(result["_is_outlier"].sum(), 0)


class TestReport(unittest.TestCase):
    """报告生成测试"""

    def test_markdown_report(self):
        from src.validation.report import ReportGenerator
        from src.validation.checks.base_check import CheckResult, ValidationIssue
        from src.validation.validator import ValidationSummary

        results = [
            CheckResult(check_name="Test Check", status="PASSED", total_checked=5),
            CheckResult(
                check_name="Failed Check", status="FAILED", total_checked=5,
                issues=[ValidationIssue("Test", "ERROR", "Error desc", column="AGE")]
            ),
        ]
        summary = ValidationSummary(
            total_checks=2, passed=1, failed=1,
            total_issues=1, errors=1, warnings=0, infos=0,
        )
        gen = ReportGenerator("Test Report")
        md = gen.generate_markdown(results, summary)
        self.assertIn("Test Report", md)
        self.assertIn("Test Check", md)
        self.assertIn("Failed Check", md)


def main():
    """运行所有测试"""

    # 设置 PYTHONIOENCODING
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加所有测试
    test_cases = [
        TestDataLoader,
        TestValidator,
        TestChecks,
        TestConverter,
        TestScripts,
        TestReport,
    ]

    for test_case in test_cases:
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(test_case))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出摘要
    print(f"\n{'='*50}")
    print(f"测试结果摘要:")
    print(f"  运行: {result.testsRun}")
    print(f"  通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败: {len(result.failures)}")
    print(f"  错误: {len(result.errors)}")
    print(f"{'='*50}")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
