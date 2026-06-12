"""
变量映射模块
=========
基于预设规则自动匹配原始变量与 SDTM 标准变量。
支持精确匹配、模糊匹配与值映射。
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from difflib import SequenceMatcher

from src.config.settings import config

logger = logging.getLogger(__name__)


class VariableMapper:
    """变量映射器，将原始变量映射为 SDTM 标准变量"""

    def __init__(self, custom_mappings: Optional[Dict] = None):
        """
        初始化映射器

        Args:
            custom_mappings: 自定义映射配置（覆盖默认配置）
        """
        # 加载映射规则
        mapping_config = custom_mappings or config.get_mapping_config()
        self.direct_mappings: Dict[str, str] = mapping_config.get("direct_mappings", {})
        self.date_mappings: Dict[str, str] = mapping_config.get("date_mappings", {})
        self.all_standard_mappings: Dict[str, str] = {}
        self.all_standard_mappings.update(self.direct_mappings)
        self.all_standard_mappings.update(self.date_mappings)

        # 值映射
        self.value_mappings: Dict[str, Dict[str, str]] = \
            custom_mappings.get("value_mappings", {}) if custom_mappings else {}

        # 反向映射（标准 → 原始）
        self.reverse_mappings: Dict[str, str] = {
            std: raw for raw, std in self.all_standard_mappings.items()
        }

    def map_variable_name(self, var_name: str) -> Tuple[str, float]:
        """
        将原始变量名映射为 SDTM 标准变量名

        Args:
            var_name: 原始变量名

        Returns:
            (标准变量名, 匹配置信度) 元组
        """
        # 1. 精确匹配
        if var_name in self.all_standard_mappings:
            return self.all_standard_mappings[var_name], 1.0

        # 2. 大小写不敏感匹配
        upper_name = var_name.upper()
        for raw, std in self.all_standard_mappings.items():
            if raw.upper() == upper_name:
                return std, 1.0

        # 2b. 检查变量名是否已是一个 SDTM 标准变量名
        sdtm_standard_vars = {"STUDYID", "USUBJID", "DOMAIN", "SUBJID", "SITEID",
                              "RFSTDTC", "RFENDTC", "AESTDTC", "AEENDTC",
                              "VISITNUM", "VISIT", "EPOCH", "ARM", "ARMCD",
                              "AGE", "AGEU", "SEX", "RACE", "ETHNIC", "COUNTRY"}
        if upper_name in sdtm_standard_vars:
            return upper_name, 1.0

        # 3. 模糊匹配（仅对非标准变量名）
        best_match = (var_name, 0.0)
        FUZZY_THRESHOLD = 0.75  # 最低匹配阈值
        for raw, std in self.all_standard_mappings.items():
            ratio = SequenceMatcher(None, upper_name, raw.upper()).ratio()
            if ratio > best_match[1] and ratio >= FUZZY_THRESHOLD:
                best_match = (std, ratio)

        return best_match

    def map_value(self, var: str, value: Any) -> Any:
        """
        映射分类变量的值（如 "男" → "M"）

        Args:
            var: 变量名
            value: 原始值

        Returns:
            映射后的值（如果无映射则返回原值）
        """
        if pd.isna(value):
            return value

        var_mappings = self.value_mappings.get(var, {})
        str_value = str(value).strip()

        return var_mappings.get(str_value, value) if var_mappings else value

    def auto_detect_mappings(
        self, source_columns: List[str]
    ) -> Dict[str, Tuple[str, float]]:
        """
        自动检测源数据列到 SDTM 标准变量的映射

        Args:
            source_columns: 源数据列名列表

        Returns:
            源列名到 (标准变量名, 置信度) 的字典
        """
        detected = {}
        for col in source_columns:
            std_var, confidence = self.map_variable_name(col)
            if confidence > 0.0:
                detected[col] = (std_var, confidence)

        return detected

    def get_unmapped_columns(
        self, source_columns: List[str], threshold: float = 0.6
    ) -> List[str]:
        """
        获取无法自动映射的列

        Args:
            source_columns: 源数据列名列表
            threshold: 匹配阈值

        Returns:
            未匹配的列名列表
        """
        unmapped = []
        for col in source_columns:
            _, confidence = self.map_variable_name(col)
            if confidence < threshold:
                unmapped.append(col)
        return unmapped

    def get_mapping_summary(
        self, source_columns: List[str]
    ) -> Dict[str, Any]:
        """
        获取映射汇总信息

        Args:
            source_columns: 源数据列名列表

        Returns:
            映射汇总
        """
        detected = self.auto_detect_mappings(source_columns)
        unmapped = self.get_unmapped_columns(source_columns)

        high_confidence = sum(1 for _, c in detected.values() if c >= 0.8)
        medium_confidence = sum(1 for _, c in detected.values() if 0.6 <= c < 0.8)
        low_confidence = sum(1 for _, c in detected.values() if c < 0.6)

        return {
            "total_columns": len(source_columns),
            "mapped_columns": len(detected) - len(unmapped),
            "unmapped_columns": len(unmapped),
            "high_confidence": high_confidence,
            "medium_confidence": medium_confidence,
            "low_confidence": low_confidence,
            "unmapped_list": unmapped,
        }


# 避免在 import 时出错
import pandas as pd
