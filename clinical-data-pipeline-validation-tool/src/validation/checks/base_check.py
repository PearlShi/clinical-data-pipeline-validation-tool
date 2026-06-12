"""
校验检查基类
=========
定义所有校验检查器的抽象基类与通用数据结构。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import pandas as pd


@dataclass
class ValidationIssue:
    """校验问题记录"""
    check_name: str              # 检查项名称
    severity: str                # 严重级别: ERROR / WARNING / INFO
    description: str             # 问题描述
    column: Optional[str] = None      # 相关列名
    row_index: Optional[int] = None   # 相关行号（0-based）
    actual_value: Optional[str] = None  # 实际值
    expected: Optional[str] = None      # 期望值
    suggestion: Optional[str] = None    # 修改建议

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "check_name": self.check_name,
            "severity": self.severity,
            "description": self.description,
            "column": self.column or "",
            "row": (self.row_index + 2) if self.row_index is not None else "",  # Excel 行号（+2 含表头和0-base）
            "actual_value": self.actual_value or "",
            "expected": self.expected or "",
            "suggestion": self.suggestion or "",
        }


@dataclass
class CheckResult:
    """单项检查结果"""
    check_name: str                          # 检查项名称
    status: str                              # PASSED / FAILED / SKIPPED
    total_checked: int = 0                   # 检查总数
    issues: List[ValidationIssue] = field(default_factory=list)  # 发现的问题列表
    details: Optional[str] = None            # 补充说明

    @property
    def passed(self) -> bool:
        """是否通过"""
        return self.status == "PASSED"

    @property
    def issue_count(self) -> int:
        """问题数量"""
        return len(self.issues)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "check_name": self.check_name,
            "status": self.status,
            "total_checked": self.total_checked,
            "issue_count": self.issue_count,
            "issues": [issue.to_dict() for issue in self.issues],
            "details": self.details or "",
        }


class BaseCheck(ABC):
    """校验检查器基类"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    @abstractmethod
    def check(self, df: pd.DataFrame) -> CheckResult:
        """
        执行检查

        Args:
            df: 待检查的 DataFrame

        Returns:
            检查结果
        """
        pass

    def _make_issue(
        self,
        check_name: str,
        severity: str,
        description: str,
        column: Optional[str] = None,
        row_index: Optional[int] = None,
        actual_value: Optional[str] = None,
        expected: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> ValidationIssue:
        """创建校验问题记录"""
        return ValidationIssue(
            check_name=check_name,
            severity=severity,
            description=description,
            column=column,
            row_index=row_index,
            actual_value=str(actual_value) if actual_value is not None else None,
            expected=expected,
            suggestion=suggestion,
        )
