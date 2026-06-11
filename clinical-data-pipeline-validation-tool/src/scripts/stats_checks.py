"""
标准化统计校验脚本
===============
提供关键指标范围校验、逻辑一致性检查等统计校验功能。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any, Tuple
from scipy import stats as scipy_stats
import logging

logger = logging.getLogger(__name__)


class StatisticalChecker:
    """统计校验器，对临床数据进行统计分析校验"""

    @staticmethod
    def describe_dataset(df: pd.DataFrame) -> Dict[str, Any]:
        """
        生成数据集描述统计

        Args:
            df: 数据 DataFrame

        Returns:
            描述统计字典
        """
        result = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "missing_summary": df.isnull().sum().to_dict(),
            "missing_percent": (df.isnull().sum() / len(df) * 100).round(2).to_dict(),
            "numeric_summary": {},
            "categorical_summary": {},
        }

        # 数值列统计
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            vals = df[col].dropna()
            if len(vals) > 0:
                result["numeric_summary"][col] = {
                    "count": int(len(vals)),
                    "missing": int(df[col].isnull().sum()),
                    "mean": round(float(vals.mean()), 4),
                    "std": round(float(vals.std()), 4),
                    "min": round(float(vals.min()), 4),
                    "q1": round(float(vals.quantile(0.25)), 4),
                    "median": round(float(vals.median()), 4),
                    "q3": round(float(vals.quantile(0.75)), 4),
                    "max": round(float(vals.max()), 4),
                    "skewness": round(float(vals.skew()), 4),
                    "kurtosis": round(float(vals.kurtosis()), 4),
                }

        # 分类列统计
        cat_cols = df.select_dtypes(include=["object", "category", "string"]).columns
        for col in cat_cols:
            value_counts = df[col].value_counts(dropna=False).head(20)
            result["categorical_summary"][col] = {
                "count": int(df[col].notna().sum()),
                "missing": int(df[col].isnull().sum()),
                "unique_values": int(df[col].nunique()),
                "top_values": value_counts.to_dict(),
            }

        return result

    @staticmethod
    def check_value_distribution(
        df: pd.DataFrame,
        column: str,
        expected_min: Optional[float] = None,
        expected_max: Optional[float] = None,
        bins: int = 10
    ) -> Dict[str, Any]:
        """
        检查数值列的分布情况

        Args:
            df: 数据 DataFrame
            column: 列名
            expected_min: 期望最小值
            expected_max: 期望最大值
            bins: 直方图分组数

        Returns:
            分布检查结果
        """
        if column not in df.columns:
            return {"error": f"列 '{column}' 不存在"}

        vals = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(vals) == 0:
            return {"error": f"列 '{column}' 无有效数值"}

        result = {
            "column": column,
            "count": len(vals),
            "min": float(vals.min()),
            "max": float(vals.max()),
            "mean": float(vals.mean()),
            "median": float(vals.median()),
            "std": float(vals.std()),
            "range_checks": {},
        }

        # 范围检查
        if expected_min is not None:
            below_min = (vals < expected_min).sum()
            if below_min > 0:
                result["range_checks"]["below_min"] = {
                    "count": int(below_min),
                    "percent": round(below_min / len(vals) * 100, 2),
                    "expected_min": expected_min,
                }

        if expected_max is not None:
            above_max = (vals > expected_max).sum()
            if above_max > 0:
                result["range_checks"]["above_max"] = {
                    "count": int(above_max),
                    "percent": round(above_max / len(vals) * 100, 2),
                    "expected_max": expected_max,
                }

        # 正态性检验（样本量 > 5000 时使用 Kolmogorov-Smirnov）
        if len(vals) >= 8:
            try:
                if len(vals) <= 5000:
                    stat, p = scipy_stats.shapiro(vals.sample(min(len(vals), 5000)))
                else:
                    stat, p = scipy_stats.normaltest(vals.sample(5000))
                result["normality_test"] = {
                    "method": "Shapiro-Wilk" if len(vals) <= 5000 else "D'Agostino-Pearson",
                    "statistic": round(float(stat), 4),
                    "p_value": round(float(p), 4),
                    "is_normal": p > 0.05,
                }
            except Exception as e:
                logger.warning(f"正态性检验失败: {e}")

        # 百分位数
        percentiles = [1, 5, 25, 50, 75, 95, 99]
        result["percentiles"] = {
            str(p): round(float(vals.quantile(p / 100)), 4) for p in percentiles
        }

        return result

    @staticmethod
    def check_categorical_balance(
        df: pd.DataFrame,
        column: str,
        expected_proportions: Optional[Dict[str, float]] = None,
        min_count: int = 5
    ) -> Dict[str, Any]:
        """
        检查分类变量各类别的分布均衡性

        Args:
            df: 数据 DataFrame
            column: 列名
            expected_proportions: 期望比例 {类别: 比例}
            min_count: 最小期望频数

        Returns:
            分类平衡性检查结果
        """
        if column not in df.columns:
            return {"error": f"列 '{column}' 不存在"}

        value_counts = df[column].value_counts(dropna=False)
        result = {
            "column": column,
            "total": int(len(df)),
            "categories": value_counts.to_dict(),
            "proportions": (value_counts / len(df) * 100).round(2).to_dict(),
        }

        # 检查稀有类别
        rare_categories = value_counts[value_counts < min_count]
        if not rare_categories.empty:
            result["rare_categories"] = rare_categories.to_dict()

        # 检查类别数量是否过多
        if len(value_counts) > 50:
            result["too_many_categories"] = {
                "count": len(value_counts),
                "suggestion": "类别数量过多，建议检查数据是否有误或分组分析"
            }

        # 期望比例检查
        if expected_proportions:
            discrepancies = {}
            for cat, expected_pct in expected_proportions.items():
                actual_pct = (value_counts.get(cat, 0) / len(df)) * 100
                diff = abs(actual_pct - expected_pct * 100)
                if diff > 5:  # 差异超过 5% 时标记
                    discrepancies[cat] = {
                        "expected_pct": expected_pct * 100,
                        "actual_pct": round(actual_pct, 2),
                        "diff_pct": round(diff, 2),
                    }
            if discrepancies:
                result["proportion_discrepancies"] = discrepancies

        return result

    @staticmethod
    def cross_tabulation(
        df: pd.DataFrame,
        row_var: str,
        col_var: str,
        normalize: str = "all"
    ) -> Dict[str, Any]:
        """
        生成交叉表并做卡方检验

        Args:
            df: 数据 DataFrame
            row_var: 行变量
            col_var: 列变量
            normalize: 标准化方式 (all / index / columns)

        Returns:
            交叉表分析结果
        """
        if row_var not in df.columns or col_var not in df.columns:
            return {"error": "变量不存在"}

        crosstab = pd.crosstab(df[row_var], df[col_var], margins=True)
        crosstab_norm = pd.crosstab(df[row_var], df[col_var],
                                     normalize=normalize, margins=True)

        result = {
            "row_variable": row_var,
            "col_variable": col_var,
            "table": crosstab.to_dict(),
            "normalized_table": crosstab_norm.to_dict(),
        }

        # 卡方检验
        try:
            contingency = pd.crosstab(df[row_var], df[col_var])
            chi2, p, dof, expected = scipy_stats.chi2_contingency(contingency)
            result["chi_square_test"] = {
                "chi2_statistic": round(float(chi2), 4),
                "p_value": round(float(p), 4),
                "degrees_of_freedom": int(dof),
                "significant": p < 0.05,
            }
        except Exception as e:
            logger.warning(f"卡方检验失败: {e}")

        return result
