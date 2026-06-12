"""
变量完整性校验检查器
=================
检查必填变量缺失、变量名不规范/大小写不一致等问题。
"""

import re
import pandas as pd
from typing import List, Optional, Dict
from src.validation.checks.base_check import BaseCheck, CheckResult, ValidationIssue


class CompletenessCheck(BaseCheck):
    """变量完整性校验检查器"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.required_vars = self.config.get("variables", [
            "USUBJID", "STUDYID", "DOMAIN", "SUBJID", "SITEID",
            "RFSTDTC", "RFENDTC"
        ])
        self.name_pattern = self.config.get("name_pattern", "^[A-Z][A-Z0-9_]*$")

    def check(self, df: pd.DataFrame) -> CheckResult:
        """
        执行完整性检查：
        1. 检查必填变量是否存在
        2. 检查变量名是否符合命名规范
        3. 检查必填变量是否存在缺失值
        4. 检查变量名大小写不一致问题
        """
        result = CheckResult(
            check_name="变量完整性校验",
            status="PASSED",
            total_checked=len(df),
        )

        # 1. 检查必填变量是否存在
        missing_vars = self._check_missing_variables(df, result)

        # 2. 检查变量名命名规范
        self._check_variable_naming(df, result)

        # 3. 检查必填变量缺失值（仅对存在的变量）
        existing_required = [v for v in self.required_vars if v in df.columns]
        if existing_required:
            self._check_missing_values(df, existing_required, result)

        # 4. 检查变量名大小写不一致
        self._check_case_consistency(df, result)

        # 更新最终状态
        if result.issues:
            result.status = "FAILED"

        return result

    def _check_missing_variables(self, df: pd.DataFrame, result: CheckResult) -> List[str]:
        """检查必填变量是否存在于 DataFrame 中"""
        missing_vars = []
        for var in self.required_vars:
            if var not in df.columns:
                missing_vars.append(var)
                issue = self._make_issue(
                    check_name="必填变量缺失",
                    severity="ERROR",
                    description=f"必填变量 '{var}' 不存在于数据集中",
                    column=var,
                    suggestion=f"请添加 '{var}' 列，或检查原始数据中对应的变量名是否正确"
                )
                result.issues.append(issue)

        return missing_vars

    def _check_variable_naming(self, df: pd.DataFrame, result: CheckResult) -> None:
        """检查变量名是否符合命名规范"""
        pattern = re.compile(self.name_pattern)
        for col in df.columns:
            if not pattern.match(str(col)):
                issue = self._make_issue(
                    check_name="变量名不规范",
                    severity="WARNING",
                    description=f"变量名 '{col}' 不符合命名规范（应匹配: {self.name_pattern}）",
                    column=str(col),
                    suggestion=f"建议将 '{col}' 改为全大写字母、数字和下划线的组合（如: {str(col).upper()}）"
                )
                result.issues.append(issue)

    def _check_missing_values(
        self,
        df: pd.DataFrame,
        variables: List[str],
        result: CheckResult
    ) -> None:
        """检查必填变量的缺失值"""
        for var in variables:
            missing_mask = df[var].isnull()
            missing_count = missing_mask.sum()
            if missing_count > 0:
                # 只记录前 N 个缺失值的位置
                max_report = min(missing_count, 50)
                missing_indices = df.index[missing_mask].tolist()[:max_report]

                issue = self._make_issue(
                    check_name="必填变量缺失值",
                    severity="ERROR",
                    description=f"变量 '{var}' 存在 {missing_count} 个缺失值 "
                                f"(显示前{max_report}个)",
                    column=var,
                    suggestion=f"请根据源数据补全 '{var}' 的缺失值"
                )
                result.issues.append(issue)

    def _check_case_consistency(self, df: pd.DataFrame, result: CheckResult) -> None:
        """检查是否存在大小写不一致的相似变量名"""
        col_upper = {}
        for col in df.columns:
            upper_key = str(col).upper().strip()
            if upper_key in col_upper:
                prev = col_upper[upper_key]
                if prev != col:
                    issue = self._make_issue(
                        check_name="变量名大小写不一致",
                        severity="WARNING",
                        description=f"发现相似变量名: '{prev}' 与 '{col}'，"
                                    f"可能存在大小写不一致问题",
                        column=str(col),
                        suggestion="建议统一变量名的大小写"
                    )
                    result.issues.append(issue)
            else:
                col_upper[upper_key] = col
