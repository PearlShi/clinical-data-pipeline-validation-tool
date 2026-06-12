"""
数据输出模块
===========
支持将处理结果输出为 CSV、Excel、Markdown 等格式。
"""

import pandas as pd
from pathlib import Path
from typing import Union, Optional, List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class DataWriter:
    """数据写入器，支持多种输出格式"""

    @staticmethod
    def to_csv(
        df: pd.DataFrame,
        output_path: Union[str, Path],
        index: bool = False,
        encoding: str = "utf-8-sig",
        **kwargs
    ) -> str:
        """
        将 DataFrame 输出为 CSV 文件

        Args:
            df: 要输出的数据
            output_path: 输出文件路径
            index: 是否包含索引列
            encoding: 文件编码（默认 utf-8-sig 兼容 Excel）
            **kwargs: 透传给 pandas.to_csv 的额外参数

        Returns:
            输出文件的绝对路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df.to_csv(
            output_path,
            index=index,
            encoding=encoding,
            **kwargs
        )
        logger.info(f"CSV 文件已输出: {output_path}")
        return str(output_path.resolve())

    @staticmethod
    def to_excel(
        df: pd.DataFrame,
        output_path: Union[str, Path],
        sheet_name: str = "Sheet1",
        index: bool = False,
        **kwargs
    ) -> str:
        """
        将 DataFrame 输出为 Excel 文件

        Args:
            df: 要输出的数据
            output_path: 输出文件路径
            sheet_name: 工作表名称
            index: 是否包含索引列
            **kwargs: 透传给 pandas.to_excel 的额外参数

        Returns:
            输出文件的绝对路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 确保扩展名为 .xlsx
        if output_path.suffix.lower() not in (".xlsx", ".xls"):
            output_path = output_path.with_suffix(".xlsx")

        df.to_excel(
            output_path,
            sheet_name=sheet_name,
            index=index,
            engine="openpyxl",
            **kwargs
        )
        logger.info(f"Excel 文件已输出: {output_path}")
        return str(output_path.resolve())

    @staticmethod
    def to_multi_sheet_excel(
        data_frames: Dict[str, pd.DataFrame],
        output_path: Union[str, Path],
        **kwargs
    ) -> str:
        """
        将多个 DataFrame 输出到同一个 Excel 文件的不同工作表

        Args:
            data_frames: 工作表名到 DataFrame 的字典
            output_path: 输出文件路径
            **kwargs: 透传给 pandas.ExcelWriter 的额外参数

        Returns:
            输出文件的绝对路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix.lower() not in (".xlsx", ".xls"):
            output_path = output_path.with_suffix(".xlsx")

        with pd.ExcelWriter(
            output_path,
            engine="openpyxl",
            **kwargs
        ) as writer:
            for sheet_name, df in data_frames.items():
                # Excel 工作表名最长 31 字符
                safe_name = sheet_name[:31]
                df.to_excel(writer, sheet_name=safe_name, index=False)
                logger.info(f"  写入工作表: {safe_name} ({len(df)} 行)")

        logger.info(f"多工作表 Excel 文件已输出: {output_path}")
        return str(output_path.resolve())

    @staticmethod
    def to_json(
        data: Any,
        output_path: Union[str, Path],
        ensure_ascii: bool = False,
        indent: int = 2,
        **kwargs
    ) -> str:
        """
        将数据输出为 JSON 文件

        Args:
            data: 要输出的数据（dict 或 list）
            output_path: 输出文件路径
            ensure_ascii: 是否确保 ASCII 编码
            indent: JSON 缩进空格数
            **kwargs: 透传给 json.dump 的额外参数

        Returns:
            输出文件的绝对路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent, **kwargs)

        logger.info(f"JSON 文件已输出: {output_path}")
        return str(output_path.resolve())

    @staticmethod
    def to_markdown(
        df: pd.DataFrame,
        output_path: Union[str, Path],
        title: str = "",
        **kwargs
    ) -> str:
        """
        将 DataFrame 输出为 Markdown 表格

        Args:
            df: 要输出的数据
            output_path: 输出文件路径
            title: 表格标题
            **kwargs: 透传给 pandas.to_markdown 的额外参数

        Returns:
            输出文件的绝对路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            if title:
                f.write(f"# {title}\n\n")
            f.write(df.to_markdown(**kwargs))
            f.write("\n")

        logger.info(f"Markdown 文件已输出: {output_path}")
        return str(output_path.resolve())

    @staticmethod
    def save_report(
        markdown_content: str,
        output_dir: Union[str, Path],
        report_name: str = "validation_report",
    ) -> Dict[str, str]:
        """
        保存校验报告（Markdown 格式）

        Args:
            markdown_content: Markdown 报告内容
            output_dir: 输出目录
            report_name: 报告文件名（不含扩展名）

        Returns:
            输出文件路径字典 {"markdown": str}
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        md_path = output_dir / f"{report_name}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        logger.info(f"校验报告已保存: {md_path}")
        return {"markdown": str(md_path.resolve())}
