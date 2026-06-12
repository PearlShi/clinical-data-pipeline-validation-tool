"""
异常值与逻辑校验检查器
===================
识别超出合理范围的数值、不符合业务逻辑的变量组合。
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from src.validation.checks.base_check import BaseCheck, CheckResult


class RangeCheck(BaseCheck):
    """异常值与逻辑校验检查器"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.value_ranges = self.config.get("value_ranges", {})
        self.logic_rules = self.config.get("logic_rules", [])

    def check(self, df: pd.DataFrame) -> CheckResult:
        """执行异常值与逻辑校验"""
        result = CheckResult(
            check_name="异常值与逻辑校验",
            status="PASSED",
            total_checked=len(df),
        )

        # 1. 数值范围检查
        self._check_value_ranges(df, result)

        # 2. 日期逻辑一致性检查
        self._check_date_logic(df, result)

        # 3. 异常值统计识别 (IQR 方法)
        self._check_outliers_iqr(df, result)

        # 4. 自定义逻辑规则检查
        self._check_custom_logic_rules(df, result)

        if result.issues:
            result.status = "FAILED"

        return result

    def _check_value_ranges(self, df: pd.DataFrame, result: CheckResult) -> None:
        """检查数值是否在合理范围内"""
        for var, range_config in self.value_ranges.items():
            if var not in df.columns:
                continue

            min_val = range_config.get("min")
            max_val = range_config.get("max")
            description = range_config.get("description", var)

            numeric_vals = pd.to_numeric(df[var], errors="coerce")
            invalid_mask = pd.Series(False, index=df.index)

            if min_val is not None:
                invalid_mask = invalid_mask | (numeric_vals < min_val)
            if max_val is not None:
                invalid_mask = invalid_mask | (numeric_vals > max_val)

            if invalid_mask.any():
                invalid_rows = df.index[invalid_mask].tolist()[:20]
                invalid_values = df.loc[invalid_mask, var].head(20).tolist()

                range_str = ""
                if min_val is not None and max_val is not None:
                    range_str = f"[{min_val}, {max_val}]"
                elif min_val is not None:
                    range_str = f"≥ {min_val}"
                else:
                    range_str = f"≤ {max_val}"

                issue = self._make_issue(
                    check_name="数值超出合理范围",
                    severity="ERROR",
                    description=f"变量 '{var}' ({description}) 存在 "
                                f"{invalid_mask.sum()} 个值超出合理范围 {range_str}，"
                                f"如第{invalid_rows[0] + 2}行: {invalid_values[0]}",
                    column=var,
                    expected=range_str,
                    suggestion=f"请核实 '{var}' 的异常值并进行修正或标注"
                )
                result.issues.append(issue)

    def _check_date_logic(self, df: pd.DataFrame, result: CheckResult) -> None:
        """检查日期逻辑一致性"""
        # 检查 RFSTDTC <= RFENDTC
        self._compare_date_pair(
            df, "RFSTDTC", "RFENDTC",
            "入组/首次给药日期应早于或等于末次给药日期",
            result
        )

        # 检查 AESTDTC <= AEENDTC
        self._compare_date_pair(
            df, "AESTDTC", "AEENDTC",
            "不良事件开始日期应早于或等于结束日期",
            result
        )

        # 检查 BRTHDTC 早于所有日期
        if "BRTHDTC" in df.columns:
            birth_dates = pd.to_datetime(df["BRTHDTC"], errors="coerce")
            date_vars = [v for v in ["RFSTDTC", "AESTDTC", "LB_DTC", "VS_DTC", "EX_DTC"]
                        if v in df.columns]

            for date_var in date_vars:
                other_dates = pd.to_datetime(df[date_var], errors="coerce")
                mask = birth_dates.notna() & other_dates.notna()
                if mask.any():
                    later_birth = (birth_dates[mask] > other_dates[mask])
                    if later_birth.any():
                        for idx in df.index[mask][later_birth][:10]:
                            issue = self._make_issue(
                                check_name="日期逻辑矛盾",
                                severity="ERROR",
                                description=f"第{idx + 2}行: 出生日期 (BRTHDTC={df.at[idx, 'BRTHDTC']}) "
                                            f"晚于 {date_var}={df.at[idx, date_var]}",
                                column="BRTHDTC",
                                row_index=idx,
                                suggestion="出生日期应早于所有其他记录日期，请核查数据"
                            )
                            result.issues.append(issue)

    def _compare_date_pair(
        self,
        df: pd.DataFrame,
        var1: str,
        var2: str,
        description: str,
        result: CheckResult
    ) -> None:
        """比较一对日期变量的先后关系"""
        if var1 not in df.columns or var2 not in df.columns:
            return

        date1 = pd.to_datetime(df[var1], errors="coerce")
        date2 = pd.to_datetime(df[var2], errors="coerce")

        mask = date1.notna() & date2.notna()
        if not mask.any():
            return

        invalid_mask = date1[mask] > date2[mask]
        if invalid_mask.any():
            invalid_indices = df.index[mask][invalid_mask]
            for idx in invalid_indices[:15]:
                issue = self._make_issue(
                    check_name="日期逻辑检查",
                    severity="ERROR",
                    description=f"第{idx + 2}行: {var1}({df.at[idx, var1]}) 晚于 "
                                f"{var2}({df.at[idx, var2]})，不符合: {description}",
                    row_index=idx,
                    expected=f"{var1} <= {var2}",
                    suggestion=f"请核查第{idx + 2}行的 {var1} 和 {var2} 值是否正确"
                )
                result.issues.append(issue)

    def _check_outliers_iqr(self, df: pd.DataFrame, result: CheckResult) -> None:
        """使用 IQR 方法识别统计异常值"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            vals = df[col].dropna()
            if len(vals) < 10:  # 样本量太小时跳过
                continue

            q1 = vals.quantile(0.25)
            q3 = vals.quantile(0.75)
            iqr = q3 - q1

            if iqr == 0:
                continue

            lower_bound = q1 - 3 * iqr  # 使用 3×IQR 更严格
            upper_bound = q3 + 3 * iqr

            outlier_mask = (vals < lower_bound) | (vals > upper_bound)
            if outlier_mask.any():
                outlier_indices = vals.index[outlier_mask]
                outlier_values = vals[outlier_mask].tolist()

                if len(outlier_values) <= 3:
                    detail = f"异常值: {list(zip([i + 2 for i in outlier_indices], outlier_values))}"
                else:
                    detail = f"共 {len(outlier_values)} 个异常值，示例: {outlier_values[:5]}"

                issue = self._make_issue(
                    check_name="统计异常值识别",
                    severity="WARNING",
                    description=f"变量 '{col}' 检测到 {len(outlier_values)} 个统计异常值 "
                                f"(基于 3×IQR 方法)。{detail}",
                    column=col,
                    expected=f"正常范围: ({lower_bound:.2f}, {upper_bound:.2f})",
                    suggestion=f"请核实 '{col}' 的异常值是否为录入错误或临床特殊情况"
                )
                result.issues.append(issue)

    def _check_custom_logic_rules(self, df: pd.DataFrame, result: CheckResult) -> None:
        """检查自定义逻辑规则"""
        rules = self.config.get("rules", [])
        for rule in rules:
            rule_name = rule.get("name", "")
            rule_type = rule.get("type", "")
            rule_desc = rule.get("description", "")
            rule_var = rule.get("var", "")
            rule_min = rule.get("min")
            rule_max = rule.get("max")

            if rule_type == "range" and rule_var in df.columns:
                vals = pd.to_numeric(df[rule_var], errors="coerce")
                if rule_min is not None:
                    invalid = vals < rule_min
                    if invalid.any():
                        issue = self._make_issue(
                            check_name="逻辑规则检查",
                            severity="WARNING",
                            description=f"'{rule_name}': {rule_desc}. "
                                        f"{invalid.sum()} 行不符合",
                            column=rule_var,
                            expected=f"{rule_var} >= {rule_min}",
                            suggestion="请核查数据"
                        )
                        result.issues.append(issue)
