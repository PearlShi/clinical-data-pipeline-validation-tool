"""
数据类型与格式校验检查器
=====================
识别数值型变量的非法字符、日期变量格式错误、分类变量取值超出预期范围。
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any
from datetime import datetime
from src.validation.checks.base_check import BaseCheck, CheckResult


class TypeCheck(BaseCheck):
    """数据类型与格式校验检查器"""

    # 常见数值型变量关键词
    NUMERIC_KEYWORDS = [
        "AGE", "WEIGHT", "HEIGHT", "BMI", "DOSE", "VISITNUM",
        "NUM", "CNT", "COUNT", "SCORE", "VALUE", "RESULT",
        "LO", "HI", "RANGE", "PERCENT", "PCT", "DURATION"
    ]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.date_vars = self.config.get("date_variables", [
            "RFSTDTC", "RFENDTC", "AESTDTC", "AEENDTC",
            "LB_DTC", "VS_DTC", "EX_DTC", "MH_STDTC",
            "CM_STDTC", "DS_DTC", "BRTHDTC"
        ])
        self.date_format = self.config.get("date_format", "%Y-%m-%d")
        self.category_mappings = self.config.get("category_mappings", {})

    def check(self, df: pd.DataFrame) -> CheckResult:
        """执行数据类型与格式检查"""
        result = CheckResult(
            check_name="数据类型与格式校验",
            status="PASSED",
            total_checked=len(df),
        )

        # 1. 检查日期变量格式
        self._check_date_formats(df, result)

        # 2. 检查数值型变量非法字符
        self._check_numeric_columns(df, result)

        # 3. 检查分类变量取值
        self._check_category_values(df, result)

        if result.issues:
            result.status = "FAILED"

        return result

    def _check_date_formats(self, df: pd.DataFrame, result: CheckResult) -> None:
        """检查日期变量的格式是否正确"""
        date_format_display = self.date_format.replace("%Y", "YYYY") \
                                              .replace("%m", "MM") \
                                              .replace("%d", "DD")

        for var in self.date_vars:
            if var not in df.columns:
                continue

            non_null = df[var].dropna()
            if len(non_null) == 0:
                continue

            error_count = 0
            error_values = []

            for idx, value in non_null.items():
                if not self._is_valid_date(str(value)):
                    error_count += 1
                    if len(error_values) < 10:  # 最多记录10个示例
                        error_values.append((idx, str(value)))

            if error_count > 0:
                examples = "; ".join(
                    [f"第{idx + 2}行: '{val}'" for idx, val in error_values]
                )
                issue = self._make_issue(
                    check_name="日期格式错误",
                    severity="ERROR",
                    description=f"变量 '{var}' 存在 {error_count} 个日期格式错误 "
                                f"（期望格式: {date_format_display}），"
                                f"示例: {examples}",
                    column=var,
                    suggestion=f"请将 '{var}' 的值统一为 {date_format_display} 格式"
                )
                result.issues.append(issue)

    def _is_valid_date(self, value: str) -> bool:
        """验证日期字符串是否合法"""
        value = value.strip()
        if not value:
            return True  # 空值视为有效

        # 尝试匹配多种日期格式
        date_formats = [
            self.date_format,
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y%m%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
        ]

        for fmt in date_formats:
            try:
                datetime.strptime(value, fmt)
                return True
            except (ValueError, TypeError):
                continue
        return False

    def _check_numeric_columns(self, df: pd.DataFrame, result: CheckResult) -> None:
        """检查数值型变量的非法字符"""
        for col in df.columns:
            if not self._is_likely_numeric(col):
                continue

            non_null = df[col].dropna()
            if len(non_null) == 0:
                continue

            # 尝试转换为数值，捕获非法值
            numeric_mask = pd.to_numeric(non_null, errors="coerce").notna()
            invalid_mask = ~numeric_mask

            if invalid_mask.any():
                invalid_values = non_null[invalid_mask].unique().tolist()
                issue = self._make_issue(
                    check_name="数值变量非数值内容",
                    severity="ERROR",
                    description=f"变量 '{col}' 存在 {invalid_mask.sum()} 个非数值值: "
                                f"{invalid_values[:10]}",
                    column=col,
                    suggestion=f"请清理 '{col}' 中的非数值字符"
                )
                result.issues.append(issue)

    def _is_likely_numeric(self, col_name: str) -> bool:
        """判断变量名是否可能为数值类型"""
        # 检查是否包含数值关键词
        upper_name = str(col_name).upper()
        for keyword in self.NUMERIC_KEYWORDS:
            if keyword in upper_name:
                return True
        return False

    def _check_category_values(self, df: pd.DataFrame, result: CheckResult) -> None:
        """检查分类变量取值是否在预期范围内"""
        for var, mapping in self.category_mappings.items():
            if var not in df.columns:
                continue

            valid_values = mapping.get("valid_values", [])
            if not valid_values:
                continue

            non_null = df[var].dropna().astype(str).str.strip()
            if len(non_null) == 0:
                continue

            invalid_mask = ~non_null.isin(valid_values)
            if invalid_mask.any():
                invalid_examples = non_null[invalid_mask].unique().tolist()
                description = mapping.get("description", var)
                issue = self._make_issue(
                    check_name="分类变量取值超出范围",
                    severity="WARNING",
                    description=f"变量 '{var}' ({description}) 存在 "
                                f"{invalid_mask.sum()} 个超出预期范围的值: "
                                f"{invalid_examples[:15]}",
                    column=var,
                    expected=f"允许值: {valid_values[:10]}",
                    suggestion=f"请将 '{var}' 的值映射为允许范围内的标准取值"
                )
                result.issues.append(issue)
