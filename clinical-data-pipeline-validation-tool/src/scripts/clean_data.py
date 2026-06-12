"""
通用数据清洗脚本
=============
提供缺失值标记、重复记录去重、格式统一等可复用清洗功能。
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Union, Any, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataCleaner:
    """数据清洗器，提供临床数据常用清洗操作"""

    @staticmethod
    def remove_duplicates(
        df: pd.DataFrame,
        subset: Optional[List[str]] = None,
        keep: str = "first",
        inplace: bool = False
    ) -> pd.DataFrame:
        """
        去除重复记录

        Args:
            df: 数据 DataFrame
            subset: 用于判断重复的列子集（默认所有列）
            keep: 保留方式 (first / last / False)
            inplace: 是否就地修改

        Returns:
            去重后的 DataFrame
        """
        result = df if inplace else df.copy()
        before = len(result)
        result.drop_duplicates(subset=subset, keep=keep, inplace=True)
        after = len(result)
        removed = before - after

        if removed > 0:
            logger.info(f"去重完成: 移除 {removed} 条重复记录 ({before} → {after})")
        else:
            logger.info("未发现重复记录")

        return result

    @staticmethod
    def mark_missing_values(
        df: pd.DataFrame,
        na_values: Optional[List[Any]] = None,
        inplace: bool = False
    ) -> pd.DataFrame:
        """
        标记缺失值，将指定值转换为 NaN

        Args:
            df: 数据 DataFrame
            na_values: 需要视为缺失值的列表（默认包含常见缺失标记）
            inplace: 是否就地修改

        Returns:
            处理后的 DataFrame
        """
        result = df if inplace else df.copy()
        na_marks = na_values or [
            "", "NA", "N/A", "n/a", "na", "NULL", "null", "NaN",
            "nan", ".", "None", "none", "?", "--", "Unknown", "UNKNOWN"
        ]

        for col in result.columns:
            col_na_count = 0
            for val in na_marks:
                if val == "":
                    mask = result[col].astype(str).str.strip().eq("")
                else:
                    mask = result[col].astype(str).str.strip().str.upper() == val.upper()
                result.loc[mask, col] = None
                col_na_count += mask.sum()
            if col_na_count > 0:
                logger.debug(f"列 '{col}': 标记 {col_na_count} 个缺失值")

        logger.info(f"缺失值标记完成，共标记 {result.isnull().sum().sum()} 个缺失值")
        return result

    @staticmethod
    def strip_whitespace(
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        inplace: bool = False
    ) -> pd.DataFrame:
        """
        去除字符串列的前后空白字符

        Args:
            df: 数据 DataFrame
            columns: 要处理的列（默认所有字符串列）
            inplace: 是否就地修改

        Returns:
            处理后的 DataFrame
        """
        result = df if inplace else df.copy()
        target_cols = columns or result.select_dtypes(include=["object", "string"]).columns.tolist()

        for col in target_cols:
            if col in result.columns:
                result[col] = result[col].astype(str).str.strip()
                result.loc[result[col] == "", col] = None

        logger.info(f"空白字符清除完成，处理了 {len(target_cols)} 列")
        return result

    @staticmethod
    def fill_missing_values(
        df: pd.DataFrame,
        strategy: Union[str, Dict[str, Any]] = "auto",
        fill_values: Optional[Dict[str, Any]] = None,
        inplace: bool = False
    ) -> pd.DataFrame:
        """
        填充缺失值

        Args:
            df: 数据 DataFrame
            strategy: 填充策略
                - "auto": 根据列类型自动选择（数值列用中位数，分类列用众数）
                - "mean": 数值列用均值
                - "median": 数值列用中位数
                - "mode": 所有列用众数
                - "drop": 删除含缺失值的行
                - Dict: 每列的字典策略
            fill_values: 指定填充值的字典 {列名: 填充值}
            inplace: 是否就地修改

        Returns:
            处理后的 DataFrame
        """
        result = df if inplace else df.copy()

        if strategy == "drop":
            before = len(result)
            result.dropna(inplace=True)
            after = len(result)
            logger.info(f"删除含缺失值行: {before - after} 行被删除 ({before} → {after})")
            return result

        # 使用指定的填充值
        if fill_values:
            for col, val in fill_values.items():
                if col in result.columns:
                    result[col].fillna(val, inplace=True)
                    logger.debug(f"列 '{col}': 使用指定值 '{val}' 填充")
            return result

        # 自动策略
        for col in result.columns:
            if result[col].isnull().sum() == 0:
                continue

            if isinstance(strategy, dict) and col in strategy:
                strat = strategy[col]
            else:
                strat = strategy

            if strat == "auto":
                if pd.api.types.is_numeric_dtype(result[col]):
                    result[col].fillna(result[col].median(), inplace=True)
                    logger.debug(f"列 '{col}': 使用中位数 {result[col].median():.2f} 填充")
                elif pd.api.types.is_datetime64_dtype(result[col]):
                    result[col].fillna(method="ffill", inplace=True)
                    logger.debug(f"列 '{col}': 使用前向填充")
                else:
                    mode_val = result[col].mode()
                    if not mode_val.empty:
                        result[col].fillna(mode_val[0], inplace=True)
                        logger.debug(f"列 '{col}': 使用众数 '{mode_val[0]}' 填充")
            elif strat == "mean":
                result[col].fillna(result[col].mean(), inplace=True)
            elif strat == "median":
                result[col].fillna(result[col].median(), inplace=True)
            elif strat == "mode":
                mode_val = result[col].mode()
                if not mode_val.empty:
                    result[col].fillna(mode_val[0], inplace=True)

        filled = df.isnull().sum().sum() - result.isnull().sum().sum()
        logger.info(f"缺失值填充完成，共填充 {filled} 个缺失值")
        return result

    @staticmethod
    def standardize_case(
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        case: str = "upper",
        inplace: bool = False
    ) -> pd.DataFrame:
        """
        统一字符串列的大小写

        Args:
            df: 数据 DataFrame
            columns: 要处理的列（默认所有字符串列）
            case: 目标大小写 (upper / lower / title)
            inplace: 是否就地修改

        Returns:
            处理后的 DataFrame
        """
        result = df if inplace else df.copy()
        target_cols = columns or result.select_dtypes(include=["object", "string"]).columns.tolist()

        for col in target_cols:
            if col in result.columns:
                if case == "upper":
                    result[col] = result[col].astype(str).str.upper()
                elif case == "lower":
                    result[col] = result[col].astype(str).str.lower()
                elif case == "title":
                    result[col] = result[col].astype(str).str.title()

        logger.info(f"大小写统一完成: {case.upper()}, 处理了 {len(target_cols)} 列")
        return result

    @staticmethod
    def clean_and_prepare(
        df: pd.DataFrame,
        drop_duplicates: bool = True,
        strip_whitespace: bool = True,
        mark_missing: bool = True,
        standardize_case: bool = True,
        fill_missing: bool = False,
        **kwargs
    ) -> pd.DataFrame:
        """
        一键执行常用的数据清洗操作

        Args:
            df: 数据 DataFrame
            drop_duplicates: 是否去重
            strip_whitespace: 是否去除空白
            mark_missing: 是否标记缺失值
            standardize_case: 是否统一大小写
            fill_missing: 是否填充缺失值
            **kwargs: 其他参数透传

        Returns:
            清洗后的 DataFrame
        """
        result = df.copy()
        logger.info(f"开始一键清洗: {len(result)} 行, {len(result.columns)} 列")

        if strip_whitespace:
            result = DataCleaner.strip_whitespace(result, inplace=True)

        if mark_missing:
            result = DataCleaner.mark_missing_values(result, inplace=True)

        if standardize_case:
            result = DataCleaner.standardize_case(result, case="upper", inplace=True)

        if drop_duplicates:
            result = DataCleaner.remove_duplicates(result, inplace=True)

        if fill_missing:
            result = DataCleaner.fill_missing_values(
                result, strategy=kwargs.get("fill_strategy", "auto"), inplace=True
            )

        logger.info(f"一键清洗完成: {len(result)} 行, {len(result.columns)} 列")
        return result
