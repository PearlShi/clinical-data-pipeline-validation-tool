"""
主校验器
=======
协调各类校验检查器对临床数据执行全面的质量校验。
"""

import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging

from src.validation.checks.base_check import BaseCheck, CheckResult
from src.validation.checks.completeness_check import CompletenessCheck
from src.validation.checks.type_check import TypeCheck
from src.validation.checks.range_check import RangeCheck
from src.validation.checks.cdisc_check import CDISCCheck
from src.config.settings import config

logger = logging.getLogger(__name__)


@dataclass
class ValidationSummary:
    """校验结果汇总"""
    total_checks: int = 0           # 总检查项数
    passed: int = 0                 # 通过项数
    failed: int = 0                 # 未通过项数
    total_issues: int = 0           # 总问题数
    errors: int = 0                 # 错误级问题数
    warnings: int = 0               # 警告级问题数
    infos: int = 0                  # 信息级问题数
    overall_status: str = "PASSED"  # 整体状态

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_checks": self.total_checks,
            "passed": self.passed,
            "failed": self.failed,
            "total_issues": self.total_issues,
            "errors": self.errors,
            "warnings": self.warnings,
            "infos": self.infos,
            "overall_status": self.overall_status,
        }


class Validator:
    """临床数据校验器，协调所有校验检查器的执行"""

    # 默认启用的检查器
    DEFAULT_CHECKERS = [
        CompletenessCheck,
        TypeCheck,
        RangeCheck,
        CDISCCheck,
    ]

    def __init__(
        self,
        custom_checks: Optional[List[BaseCheck]] = None,
        config_override: Optional[Dict] = None
    ):
        """
        初始化校验器

        Args:
            custom_checks: 自定义检查器列表
            config_override: 配置覆盖项
        """
        self.results: List[CheckResult] = []
        self.checkers: List[BaseCheck] = custom_checks or []
        self._init_checkers(config_override)

    def _init_checkers(self, config_override: Optional[Dict] = None) -> None:
        """初始化默认检查器"""
        if self.checkers:
            return  # 已有自定义检查器

        rules = config.validation_rules
        cfg = config_override or {}

        # 构建各个检查器的配置
        checker_configs = [
            ("variables", rules.get("required_variables", {})),
            ("date_variables", rules.get("date_checks", {}).get("variables", [])),
            ("date_format", rules.get("date_checks", {}).get("format", "%Y-%m-%d")),
            ("value_ranges", rules.get("value_ranges", {})),
            ("category_mappings", rules.get("category_mappings", {})),
            ("sdtm", rules.get("sdtm", {})),
            ("logic_rules", rules.get("logic_checks", {}).get("rules", [])),
        ]

        # 合并配置
        merged_config = dict(cfg)
        for key, value in checker_configs:
            if key not in merged_config:
                merged_config[key] = value

        # 实例化检查器
        self.checkers = [
            CompletenessCheck(merged_config),
            TypeCheck(merged_config),
            RangeCheck(merged_config),
            CDISCCheck(merged_config),
        ]

    def validate(self, df: pd.DataFrame) -> List[CheckResult]:
        """
        对数据执行所有校验检查

        Args:
            df: 待校验的 DataFrame

        Returns:
            校验结果列表
        """
        self.results = []

        if df is None or df.empty:
            logger.warning("校验器收到空 DataFrame")
            return self.results

        for checker in self.checkers:
            try:
                result = checker.check(df)
                self.results.append(result)
                logger.info(
                    f"检查项 '{result.check_name}': "
                    f"{'通过' if result.passed else '未通过'} "
                    f"(发现 {result.issue_count} 个问题)"
                )
            except Exception as e:
                logger.error(f"执行检查项时出错: {e}", exc_info=True)
                self.results.append(CheckResult(
                    check_name=checker.__class__.__name__,
                    status="FAILED",
                    details=f"检查执行异常: {str(e)}"
                ))

        return self.results

    def get_all_issues(self) -> List:
        """获取所有校验问题"""
        issues = []
        for result in self.results:
            issues.extend(result.issues)
        return issues

    def get_summary(self) -> ValidationSummary:
        """获取校验结果汇总"""
        summary = ValidationSummary(
            total_checks=len(self.results),
        )

        for result in self.results:
            if result.passed:
                summary.passed += 1
            else:
                summary.failed += 1

            for issue in result.issues:
                summary.total_issues += 1
                if issue.severity == "ERROR":
                    summary.errors += 1
                elif issue.severity == "WARNING":
                    summary.warnings += 1
                else:
                    summary.infos += 1

        if summary.errors > 0:
            summary.overall_status = "FAILED"
        elif summary.warnings > 0:
            summary.overall_status = "WARNING"
        else:
            summary.overall_status = "PASSED"

        return summary
