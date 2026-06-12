"""
转换日志模块
=========
记录转换过程中的关键步骤与修改内容，便于追溯与审计。
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import json
import logging

class NumpyEncoder(json.JSONEncoder):
    """支持 numpy 类型序列化的 JSON 编码器"""
    def default(self, obj):
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        elif isinstance(obj, (np.bool_,)):
            return bool(obj)
        return super().default(obj)

logger = logging.getLogger(__name__)


@dataclass
class ConversionStep:
    """转换步骤记录"""
    step_name: str                      # 步骤名称
    timestamp: str                      # 时间戳
    action: str                         # 操作类型
    details: str                        # 详细描述
    affected_rows: int = 0              # 影响行数
    affected_columns: List[str] = field(default_factory=list)  # 影响列

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "step_name": self.step_name,
            "timestamp": self.timestamp,
            "action": self.action,
            "details": self.details,
            "affected_rows": self.affected_rows,
            "affected_columns": self.affected_columns,
        }


class ConversionLog:
    """转换日志，记录整个转换过程"""

    def __init__(self, study_id: str = "", domain: str = ""):
        """
        初始化转换日志

        Args:
            study_id: 研究编号
            domain: 数据域
        """
        self.study_id = study_id
        self.domain = domain
        self.start_time = datetime.now()
        self.steps: List[ConversionStep] = []
        self.metadata: Dict[str, Any] = {
            "study_id": study_id,
            "domain": domain,
            "start_time": self.start_time.isoformat(),
            "source_file": "",
            "target_file": "",
        }

    def set_source(self, file_path: str) -> None:
        """设置源文件路径"""
        self.metadata["source_file"] = file_path

    def set_target(self, file_path: str) -> None:
        """设置目标文件路径"""
        self.metadata["target_file"] = file_path

    def add_step(
        self,
        step_name: str,
        action: str,
        details: str,
        affected_rows: int = 0,
        affected_columns: Optional[List[str]] = None,
    ) -> None:
        """
        添加转换步骤记录

        Args:
            step_name: 步骤名称
            action: 操作类型（如: 生成、映射、转换、标准化）
            details: 详细描述
            affected_rows: 影响行数
            affected_columns: 影响列
        """
        step = ConversionStep(
            step_name=step_name,
            timestamp=datetime.now().isoformat(),
            action=action,
            details=details,
            affected_rows=affected_rows,
            affected_columns=affected_columns or [],
        )
        self.steps.append(step)
        logger.info(f"[转换日志] {step_name}: {details}")

    def get_summary(self) -> Dict[str, Any]:
        """
        获取日志汇总

        Returns:
            日志汇总字典
        """
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        action_counts: Dict[str, int] = {}
        for step in self.steps:
            action_counts[step.action] = action_counts.get(step.action, 0) + 1

        return {
            "study_id": self.study_id,
            "domain": self.domain,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration, 2),
            "total_steps": len(self.steps),
            "action_summary": action_counts,
        }

    def to_text(self) -> str:
        """
        生成文本格式的转换日志

        Returns:
            格式化的日志文本
        """
        lines = []
        lines.append("=" * 60)
        lines.append("临床数据格式转换日志")
        lines.append("=" * 60)
        lines.append(f"研究编号: {self.study_id}")
        lines.append(f"数据域:   {self.domain}")
        lines.append(f"开始时间: {self.start_time.isoformat()}")
        lines.append(f"源文件:   {self.metadata.get('source_file', '')}")
        lines.append(f"目标文件: {self.metadata.get('target_file', '')}")
        lines.append("-" * 60)
        lines.append("")

        for i, step in enumerate(self.steps, 1):
            lines.append(f"[步骤 {i}] {step.step_name}")
            lines.append(f"  时间:   {step.timestamp}")
            lines.append(f"  操作:   {step.action}")
            lines.append(f"  详情:   {step.details}")
            if step.affected_rows > 0:
                lines.append(f"  影响:   {step.affected_rows} 行")
            if step.affected_columns:
                lines.append(f"  列:     {', '.join(step.affected_columns)}")
            lines.append("")

        # 汇总
        summary = self.get_summary()
        lines.append("-" * 60)
        lines.append(f"转换完成 | 总步骤: {summary['total_steps']} | "
                     f"耗时: {summary['duration_seconds']} 秒")
        lines.append("=" * 60)

        return "\n".join(lines)

    def to_json(self) -> str:
        """
        生成 JSON 格式的转换日志

        Returns:
            JSON 字符串
        """
        output = self.metadata.copy()
        output.update({
            "steps": [step.to_dict() for step in self.steps],
            "summary": self.get_summary(),
        })
        return json.dumps(output, ensure_ascii=False, indent=2, cls=NumpyEncoder)

    def save(self, output_path: str) -> None:
        """
        保存日志到文件

        Args:
            output_path: 输出路径
        """
        from pathlib import Path
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # 保存文本格式
        if output_path.endswith(".json"):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.to_json())
        else:
            with open(output_path.replace(".log", ".txt"), "w", encoding="utf-8") as f:
                f.write(self.to_text())
            with open(output_path.replace(".log", ".json"), "w", encoding="utf-8") as f:
                f.write(self.to_json())

        logger.info(f"转换日志已保存: {output_path}")
