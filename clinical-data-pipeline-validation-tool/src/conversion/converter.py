"""
自动化格式转换器
=============
实现 CSV/Excel 原始数据到 SDTM 标准格式的一键转换。
"""

import pandas as pd
from typing import Dict, Optional, Any, List, Tuple
from pathlib import Path
import logging

from src.conversion.variable_mapper import VariableMapper
from src.conversion.variable_generator import VariableGenerator
from src.conversion.conversion_log import ConversionLog
from src.core.data_loader import DataLoader
from src.core.data_writer import DataWriter
from src.config.settings import config

logger = logging.getLogger(__name__)


class DataConverter:
    """数据格式转换器，将原始临床数据转换为 SDTM 标准格式"""

    def __init__(
        self,
        study_id: Optional[str] = None,
        domain: Optional[str] = None,
        custom_mappings: Optional[Dict] = None,
        custom_defaults: Optional[Dict] = None,
    ):
        """
        初始化转换器

        Args:
            study_id: 研究编号
            domain: 目标数据域
            custom_mappings: 自定义变量映射
            custom_defaults: 自定义默认值
        """
        self.study_id = study_id or config.get_variable_defaults().get("STUDYID", "STUDY001")
        self.domain = domain or config.get_variable_defaults().get("DOMAIN", "DM")

        self.mapper = VariableMapper(custom_mappings)
        self.generator = VariableGenerator(custom_defaults)

    def convert(
        self,
        input_path: str,
        output_dir: str,
        generate_usubjid: bool = True,
        generate_studyid: bool = True,
        generate_domain: bool = True,
        normalize_dates: bool = True,
        normalize_categorical: bool = True,
        normalize_numeric: bool = True,
        decimal_places: Optional[int] = None,
        output_format: str = "xlsx",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行数据格式转换

        Args:
            input_path: 输入文件路径
            output_dir: 输出目录
            generate_usubjid: 是否自动生成 USUBJID
            generate_studyid: 是否自动生成 STUDYID
            generate_domain: 是否自动生成 DOMAIN
            normalize_dates: 是否标准化日期格式
            normalize_categorical: 是否标准化分类变量
            normalize_numeric: 是否标准化数值精度
            decimal_places: 数值保留小数位数
            output_format: 输出格式 (csv / xlsx)
            **kwargs: 其他参数

        Returns:
            转换结果字典
        """
        # 初始化日志
        log = ConversionLog(study_id=self.study_id, domain=self.domain)
        log.set_source(input_path)

        # 加载数据
        logger.info(f"开始加载数据: {input_path}")
        loader = DataLoader(input_path)
        df = loader.load(**kwargs)
        log.add_step("数据加载", "加载", f"从 {input_path} 加载数据",
                     affected_rows=len(df))
        logger.info(f"数据加载完成: {len(df)} 行, {len(df.columns)} 列")

        # 变量映射检测
        mapping_summary = self.mapper.get_mapping_summary(list(df.columns))
        log.add_step("变量映射检测", "检测",
                     f"检测到 {mapping_summary['mapped_columns']} 个变量映射, "
                     f"{mapping_summary['unmapped_columns']} 个未映射",
                     affected_columns=list(df.columns))

        # 应用变量映射（重命名列）
        rename_map = {}
        for col in df.columns:
            std_name, confidence = self.mapper.map_variable_name(col)
            if confidence >= 0.5 and std_name != col:
                rename_map[col] = std_name
                logger.debug(f"  映射: {col} → {std_name} (置信度: {confidence:.2f})")

        if rename_map:
            df = df.rename(columns=rename_map)
            log.add_step("变量名映射", "映射",
                         f"映射了 {len(rename_map)} 个变量名: {rename_map}",
                         affected_columns=list(rename_map.keys()))
            logger.info(f"变量映射完成: {len(rename_map)} 个")

        # 生成 USUBJID
        if generate_usubjid and "USUBJID" not in df.columns:
            df["USUBJID"] = self.generator.generate_usubjid(df, studyid=self.study_id)
            log.add_step("生成 USUBJID", "生成",
                         f"自动生成 USUBJID（格式: {self.study_id}-SITEID-SUBJID）",
                         affected_rows=len(df), affected_columns=["USUBJID"])

        # 生成 STUDYID
        if generate_studyid and "STUDYID" not in df.columns:
            df["STUDYID"] = self.generator.generate_studyid(df, studyid=self.study_id)
            log.add_step("生成 STUDYID", "生成",
                         f"自动生成 STUDYID: {self.study_id}",
                         affected_rows=len(df), affected_columns=["STUDYID"])

        # 生成 DOMAIN
        if generate_domain and "DOMAIN" not in df.columns:
            df["DOMAIN"] = self.generator.generate_domain(df, domain=self.domain)
            log.add_step("生成 DOMAIN", "生成",
                         f"自动生成 DOMAIN: {self.domain}",
                         affected_rows=len(df), affected_columns=["DOMAIN"])

        # 标准化日期格式
        if normalize_dates:
            date_columns = [
                col for col in df.columns
                if any(col.endswith(suffix) for suffix in ["DTC", "STDTC", "ENDTC"])
                or col in ["BRTHDTC"]
            ]
            for col in date_columns:
                if col in df.columns:
                    before_count = df[col].notna().sum()
                    df[col] = self.generator.normalize_date(df[col])
                    after_count = df[col].notna().sum()
                    if before_count > 0:
                        log.add_step("日期格式化", "标准化",
                                     f"标准化日期列 '{col}' 为 {config.date_format} 格式",
                                     affected_rows=before_count,
                                     affected_columns=[col])

        # 标准化分类变量
        if normalize_categorical:
            for var, mapping in config.get_category_mappings().items():
                if var in df.columns:
                    valid_values = mapping.get("valid_values", [])
                    if not valid_values:
                        continue
                    # 检查是否需要值映射
                    value_mappings = self.mapper.value_mappings.get(var, {})
                    if value_mappings:
                        unique_before = df[var].dropna().nunique()
                        df[var] = self.generator.normalize_categorical(
                            df[var], value_mappings
                        )
                        log.add_step("分类变量标准化", "标准化",
                                     f"标准化 '{var}' 取值映射",
                                     affected_columns=[var])

        # 标准化数值精度
        if normalize_numeric:
            numeric_cols = df.select_dtypes(include=["float64", "Float64"]).columns
            for col in numeric_cols:
                df[col] = self.generator.normalize_numeric(
                    df[col], decimal_places=decimal_places
                )
            if len(numeric_cols) > 0:
                log.add_step("数值精度标准化", "标准化",
                             f"标准化 {len(numeric_cols)} 个数值列精度",
                             affected_columns=list(numeric_cols))

        # 生成访视变量
        df = self.generator.generate_visit_vars(df)

        # 输出结果
        output_path = Path(output_dir) / f"{self.domain.lower()}_sdtm.{output_format}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.set_target(str(output_path))

        writer = DataWriter()
        if output_format == "csv":
            out_file = writer.to_csv(df, str(output_path), index=False)
        else:
            out_file = writer.to_excel(df, str(output_path), sheet_name=self.domain, index=False)

        log.add_step("结果输出", "输出",
                     f"转换结果已保存至: {out_file}",
                     affected_rows=len(df))

        # 保存日志
        log_path = str(Path(output_dir) / f"{self.domain.lower()}_conversion_log")
        log.save(log_path + ".log")

        return {
            "status": "SUCCESS",
            "output_file": out_file,
            "rows": len(df),
            "columns": len(df.columns),
            "variables_mapped": len(rename_map),
            "log": log,
            "summary": log.get_summary(),
        }
