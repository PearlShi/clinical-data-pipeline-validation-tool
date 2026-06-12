"""
SDTM/CDISC 标准合规性校验检查器
=============================
检查关键变量的命名与格式是否符合 CDISC 标准规范。
"""

import re
import pandas as pd
from typing import Optional, Dict, List
from src.validation.checks.base_check import BaseCheck, CheckResult


class CDISCCheck(BaseCheck):
    """SDTM/CDISC 标准合规性校验检查器"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.standard_domains = self.config.get("standard_domains", [
            "DM", "AE", "VS", "LB", "EX", "MH", "CM", "DS", "SC", "SS"
        ])
        self.usubjid_pattern = self.config.get(
            "usubjid_pattern",
            r"^[A-Z0-9]{3,20}-[A-Z0-9]{3,10}-[A-Z0-9]{3,10}$"
        )
        self.studyid_pattern = self.config.get(
            "studyid_pattern",
            r"^[A-Z0-9]{3,20}$"
        )
        self.domain_pattern = self.config.get(
            "domain_pattern",
            r"^(DM|AE|VS|LB|EX|MH|CM|DS|SC|SS|MH|EG|IE|TA|TV|SE)$"
        )
        self.time_var_suffixes = self.config.get("time_var_suffixes", ["DTC", "STDTC", "ENDTC"])

    def check(self, df: pd.DataFrame) -> CheckResult:
        """执行 SDTM/CDISC 标准合规性检查"""
        result = CheckResult(
            check_name="SDTM/CDISC 标准合规性校验",
            status="PASSED",
            total_checked=len(df),
        )

        # 1. 检查 USUBJID 格式
        self._check_usubjid(df, result)

        # 2. 检查 STUDYID 格式
        self._check_studyid(df, result)

        # 3. 检查 DOMAIN 标识
        self._check_domain(df, result)

        # 4. 检查 SDTM 标准变量命名
        self._check_variable_naming_convention(df, result)

        if result.issues:
            result.status = "FAILED"

        return result

    def _check_usubjid(self, df: pd.DataFrame, result: CheckResult) -> None:
        """检查 USUBJID 格式是否符合 CDISC 标准"""
        if "USUBJID" not in df.columns:
            issue = self._make_issue(
                check_name="USUBJID 缺失",
                severity="ERROR",
                description="数据集缺少 USUBJID（受试者唯一标识）变量",
                column="USUBJID",
                suggestion="USUBJID 是 SDTM 标准必填变量，请添加该字段。"
                           "格式建议: STUDYID-SITEID-SUBJID"
            )
            result.issues.append(issue)
            return

        pattern = re.compile(self.usubjid_pattern)
        non_null = df["USUBJID"].dropna().astype(str)
        invalid_mask = ~non_null.str.match(pattern)

        if invalid_mask.any():
            invalid_examples = non_null[invalid_mask].unique().tolist()[:10]
            issue = self._make_issue(
                check_name="USUBJID 格式不合规",
                severity="ERROR",
                description=f"存在 {invalid_mask.sum()} 个 USUBJID 不符合 CDISC 规范格式，"
                            f"示例: {invalid_examples}",
                column="USUBJID",
                expected="格式: STUDYID-SITEID-SUBJID（如: STUDY001-SITE01-0001）",
                suggestion="USUBJID 应使用连字符分隔的研究编号-中心编号-受试者编号格式"
            )
            result.issues.append(issue)

    def _check_studyid(self, df: pd.DataFrame, result: CheckResult) -> None:
        """检查 STUDYID 格式"""
        if "STUDYID" not in df.columns:
            issue = self._make_issue(
                check_name="STUDYID 缺失",
                severity="ERROR",
                description="数据集缺少 STUDYID（研究编号）变量",
                column="STUDYID",
                suggestion="STUDYID 是 SDTM 标准必填变量，请添加该字段"
            )
            result.issues.append(issue)
            return

        pattern = re.compile(self.studyid_pattern)
        non_null = df["STUDYID"].dropna().astype(str)
        invalid_mask = ~non_null.str.match(pattern)

        if invalid_mask.any():
            invalid_examples = non_null[invalid_mask].unique().tolist()[:5]
            issue = self._make_issue(
                check_name="STUDYID 格式不合规",
                severity="WARNING",
                description=f"STUDYID 值 '{invalid_examples}' 建议使用大写字母数字组合",
                column="STUDYID",
                expected="格式: 大写字母数字组合（如: STUDY001）",
                suggestion="STUDYID 建议统一为大写字母和数字组合"
            )
            result.issues.append(issue)

    def _check_domain(self, df: pd.DataFrame, result: CheckResult) -> None:
        """检查 DOMAIN 标识是否符合 SDTM 标准"""
        if "DOMAIN" not in df.columns:
            return  # 不是所有数据集都必须有 DOMAIN（如 DM 域本身）

        domains = df["DOMAIN"].dropna().astype(str).str.upper().unique()
        unknown_domains = [d for d in domains if d not in self.standard_domains]

        if unknown_domains:
            issue = self._make_issue(
                check_name="DOMAIN 标识不合规",
                severity="ERROR",
                description=f"检测到非标准 SDTM Domain: {unknown_domains}",
                column="DOMAIN",
                expected=f"标准 Domain: {self.standard_domains}",
                suggestion=f"请将 DOMAIN 映射为 SDTM 标准 Domain 标识: {self.standard_domains}"
            )
            result.issues.append(issue)

    def _check_variable_naming_convention(
        self, df: pd.DataFrame, result: CheckResult
    ) -> None:
        """检查变量命名是否符合 SDTM 命名惯例"""
        for col in df.columns:
            # 检查时间变量后缀
            for suffix in self.time_var_suffixes:
                if col.endswith(suffix) and len(col) > 4:
                    prefix = col[:-len(suffix)]
                    if len(prefix) > 8:
                        issue = self._make_issue(
                            check_name="SDTM 变量命名规范",
                            severity="WARNING",
                            description=f"时间变量 '{col}' 前缀 '{prefix}' 超过 8 个字符，"
                                        f"可能不符合 SDTM 变量命名长度限制",
                            column=col,
                            suggestion="SDTM 变量名建议不超过 8 个字符"
                        )
                        result.issues.append(issue)
                    break
