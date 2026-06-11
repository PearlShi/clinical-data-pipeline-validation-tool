"""
校验报告生成器
===========
支持 Markdown 与 Excel 两种格式的校验报告输出。
"""

import pandas as pd
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import logging

from src.validation.checks.base_check import CheckResult, ValidationIssue
from src.validation.validator import ValidationSummary
from src.core.data_writer import DataWriter

logger = logging.getLogger(__name__)


class ReportGenerator:
    """校验报告生成器，支持 Markdown 和 Excel 格式"""

    def __init__(self, title: str = "临床数据校验报告"):
        self.title = title
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate_markdown(
        self,
        results: List[CheckResult],
        summary: ValidationSummary
    ) -> str:
        """
        生成 Markdown 格式校验报告

        Args:
            results: 校验结果列表
            summary: 校验汇总信息

        Returns:
            Markdown 格式报告字符串
        """
        lines = []

        # 标题
        lines.append(f"# {self.title}\n")
        lines.append(f"- **生成时间**: {self.timestamp}")
        lines.append(f"- **整体状态**: {self._status_badge(summary.overall_status)}\n")

        # 汇总摘要
        lines.append("## 校验摘要\n")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 检查项总数 | {summary.total_checks} |")
        lines.append(f"| 通过 | {summary.passed} |")
        lines.append(f"| 未通过 | {summary.failed} |")
        lines.append(f"| 发现问题总数 | {summary.total_issues} |")
        lines.append(f"| 🔴 错误 | {summary.errors} |")
        lines.append(f"| 🟡 警告 | {summary.warnings} |")
        lines.append(f"| 🔵 信息 | {summary.infos} |")
        lines.append("")

        # 各检查项详情
        lines.append("## 检查项详情\n")
        for i, result in enumerate(results, 1):
            status_icon = "✅" if result.passed else "❌"
            lines.append(
                f"### {i}. {status_icon} {result.check_name}"
            )
            lines.append(f"- **状态**: {self._status_badge(result.status)}")
            lines.append(f"- **检查记录数**: {result.total_checked}")
            lines.append(f"- **发现问题**: {result.issue_count}")
            if result.details:
                lines.append(f"- **补充说明**: {result.details}")
            lines.append("")

            if result.issues:
                # 问题列表
                lines.append("#### 问题明细\n")
                lines.append(
                    "| # | 严重级别 | 描述 | 变量 | 行号 | 实际值 | 期望值 | 修改建议 |"
                )
                lines.append(
                    "|---|----------|------|------|------|--------|--------|----------|"
                )

                for j, issue in enumerate(result.issues[:100], 1):  # 最多显示100条
                    row = issue.row_index if issue.row_index else ""
                    lines.append(
                        f"| {j} | {issue.severity} | {issue.description} "
                        f"| {issue.column or ''} | {row} "
                        f"| {issue.actual_value or ''} | {issue.expected or ''} "
                        f"| {issue.suggestion or ''} |"
                    )

                if len(result.issues) > 100:
                    lines.append(
                        f"\n> ⚠️ 仅显示前 100 条问题，共 {len(result.issues)} 条\n"
                    )
                lines.append("")

        # 附录
        lines.append("---\n")
        lines.append(f"*报告由临床数据 Pipeline 自动化校验工具生成*  \n")
        lines.append(f"*生成时间: {self.timestamp}*")

        return "\n".join(lines)

    def generate_excel(
        self,
        results: List[CheckResult],
        summary: ValidationSummary,
        output_path: str
    ) -> str:
        """
        生成 Excel 格式校验报告

        Args:
            results: 校验结果列表
            summary: 校验汇总信息
            output_path: 输出文件路径

        Returns:
            输出文件的绝对路径
        """
        # 1. 摘要表
        summary_data = {
            "指标": ["检查项总数", "通过", "未通过", "问题总数", "错误", "警告", "信息", "整体状态"],
            "数值": [
                summary.total_checks, summary.passed, summary.failed,
                summary.total_issues, summary.errors, summary.warnings,
                summary.infos, summary.overall_status
            ],
        }
        df_summary = pd.DataFrame(summary_data)

        # 2. 问题明细表（所有问题合并）
        all_issues = []
        for result in results:
            for issue in result.issues:
                all_issues.append(issue.to_dict())

        df_issues = pd.DataFrame(all_issues) if all_issues else pd.DataFrame(
            columns=["check_name", "severity", "description", "column",
                     "row", "actual_value", "expected", "suggestion"]
        )

        # 3. 按检查项分类的问题表
        dfs = {"校验摘要": df_summary, "问题明细": df_issues}
        for result in results:
            if result.issues:
                safe_name = result.check_name[:20].replace("/", "_").replace(":", "")
                issues_dict = [issue.to_dict() for issue in result.issues]
                dfs[f"问题-{safe_name}"] = pd.DataFrame(issues_dict)

        # 使用 DataWriter 输出
        writer = DataWriter()
        return writer.to_multi_sheet_excel(dfs, output_path)

    def generate_all(
        self,
        results: List[CheckResult],
        summary: ValidationSummary,
        output_dir: str,
        report_name: str = "validation_report"
    ) -> Dict[str, str]:
        """
        生成所有格式的报告

        Args:
            results: 校验结果列表
            summary: 校验汇总信息
            output_dir: 输出目录
            report_name: 报告文件名（不含扩展名）

        Returns:
            各格式报告路径字典 {"markdown": str, "excel": str}
        """
        # Markdown 报告
        md_content = self.generate_markdown(results, summary)
        writer = DataWriter()
        paths = writer.save_report(md_content, output_dir, report_name)

        # Excel 报告
        excel_path = self.generate_excel(
            results, summary,
            str(Path(output_dir) / f"{report_name}.xlsx")
        )
        paths["excel"] = excel_path

        logger.info(f"报告已生成: Markdown={paths['markdown']}, Excel={paths['excel']}")
        return paths

    @staticmethod
    def _status_badge(status: str) -> str:
        """格式化状态标签"""
        status_map = {
            "PASSED": "✅ 通过",
            "FAILED": "❌ 未通过",
            "WARNING": "⚠️ 警告",
            "SKIPPED": "⏭️ 跳过",
        }
        return status_map.get(status, status)
