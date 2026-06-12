"""
标准变量自动生成模块
=================
自动生成 USUBJID、DOMAIN、STUDYID 等核心标识变量。
支持自定义规则配置。
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Any, List, Union
import logging

logger = logging.getLogger(__name__)


class VariableGenerator:
    """标准变量生成器，自动生成 SDTM 核心标识变量"""

    def __init__(self, defaults: Optional[Dict] = None):
        """
        初始化生成器

        Args:
            defaults: 默认值配置
        """
        from src.config.settings import config as app_config
        self.defaults = defaults or app_config.get_variable_defaults()

    def generate_usubjid(
        self,
        df: pd.DataFrame,
        studyid: Optional[str] = None,
        siteid_col: str = "SITEID",
        subjid_col: str = "SUBJID",
        sep: str = "-"
    ) -> pd.Series:
        """
        生成 USUBJID（受试者唯一标识）
        格式: STUDYID-SITEID-SUBJID

        Args:
            df: 数据 DataFrame
            studyid: 研究编号（若为空则使用默认值）
            siteid_col: 中心编号列名
            subjid_col: 受试者编号列名
            sep: 分隔符

        Returns:
            USUBJID 列
        """
        study = studyid or self.defaults.get("STUDYID", "STUDY001")

        if siteid_col in df.columns and subjid_col in df.columns:
            # 拼接字段
            site = df[siteid_col].astype(str).str.strip()
            subj = df[subjid_col].astype(str).str.strip()
            return study + sep + site + sep + subj
        elif subjid_col in df.columns:
            # 仅有受试者编号
            return study + sep + df[subjid_col].astype(str).str.strip()
        else:
            # 使用行号生成
            logger.warning(f"缺少 {subjid_col} 列，使用行号生成 USUBJID")
            return study + sep + "SITE" + sep + (df.index + 1).astype(str).str.zfill(4)

    def generate_studyid(
        self, df: pd.DataFrame, studyid: Optional[str] = None
    ) -> pd.Series:
        """
        生成 STUDYID（研究编号）

        Args:
            df: 数据 DataFrame
            studyid: 研究编号（若为空则使用配置默认值）

        Returns:
            包含 STUDYID 的 Series
        """
        study = studyid or self.defaults.get("STUDYID", "STUDY001")
        return pd.Series([study] * len(df))

    def generate_domain(
        self, df: pd.DataFrame, domain: Optional[str] = None
    ) -> pd.Series:
        """
        生成 DOMAIN（数据域标识）

        Args:
            df: 数据 DataFrame
            domain: 数据域（若为空则使用配置默认值）

        Returns:
            包含 DOMAIN 的 Series
        """
        dm = domain or self.defaults.get("DOMAIN", "DM")
        return pd.Series([dm] * len(df))

    def normalize_date(
        self,
        series: pd.Series,
        output_format: str = "%Y-%m-%d"
    ) -> pd.Series:
        """
        统一日期格式为 SDTM 标准格式

        Args:
            series: 包含日期值的 Series
            output_format: 输出日期格式

        Returns:
            标准化后的日期 Series
        """
        # 尝试多种常见格式
        date_formats = [
            "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d",
            "%d-%m-%Y", "%d/%m/%Y",
            "%m/%d/%Y", "%d.%m.%Y",
            "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
        ]

        def parse_date(val):
            if pd.isna(val):
                return None
            val = str(val).strip()
            for fmt in date_formats:
                try:
                    from datetime import datetime
                    dt = datetime.strptime(val, fmt)
                    return dt.strftime(output_format)
                except (ValueError, TypeError):
                    continue
            return val  # 无法解析时返回原值

        return series.apply(parse_date)

    def normalize_numeric(
        self, series: pd.Series, decimal_places: Optional[int] = None
    ) -> pd.Series:
        """
        标准化数值精度

        Args:
            series: 数值 Series
            decimal_places: 保留小数位数

        Returns:
            标准化后的 Series
        """
        numeric_vals = pd.to_numeric(series, errors="coerce")
        if decimal_places is not None:
            return numeric_vals.round(decimal_places)
        return numeric_vals

    def normalize_categorical(
        self,
        series: pd.Series,
        value_mapping: Dict[str, str]
    ) -> pd.Series:
        """
        标准化分类变量取值

        Args:
            series: 原始分类变量
            value_mapping: 值映射字典

        Returns:
            映射后的 Series
        """
        def map_val(val):
            if pd.isna(val):
                return None
            str_val = str(val).strip()
            return value_mapping.get(str_val, str_val)

        return series.apply(map_val)

    def generate_visit_vars(
        self, df: pd.DataFrame, visitnum_col: Optional[str] = None
    ) -> pd.DataFrame:
        """
        生成访视相关变量（VISITNUM, VISIT, EPOCH）

        Args:
            df: 数据 DataFrame
            visitnum_col: 访视编号列名（可选）

        Returns:
            添加了访视变量的 DataFrame
        """
        result = df.copy()

        # VISITNUM
        if "VISITNUM" not in result.columns:
            if visitnum_col and visitnum_col in result.columns:
                result["VISITNUM"] = pd.to_numeric(
                    result[visitnum_col], errors="coerce"
                ).fillna(self.defaults.get("VISITNUM", 1)).astype(int)
            else:
                result["VISITNUM"] = self.defaults.get("VISITNUM", 1)

        # VISIT
        if "VISIT" not in result.columns:
            result["VISIT"] = self.defaults.get("VISIT", "SCREENING")

        # EPOCH
        if "EPOCH" not in result.columns:
            result["EPOCH"] = self.defaults.get("EPOCH", "SCREENING")

        return result
