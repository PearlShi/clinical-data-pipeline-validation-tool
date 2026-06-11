"""
离群值识别脚本
===========
提供多种离群值识别算法，支持 SDTM/ADaM 数据的异常值检测。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class OutlierDetector:
    """离群值检测器，支持多种识别方法"""

    # 需要分组的 SDTM 变量
    GROUP_VARIABLES = ["DOMAIN", "STUDYID", "ARM", "VISIT", "TEST"]

    @staticmethod
    def iqr_method(
        df: pd.DataFrame,
        column: str,
        multiplier: float = 1.5,
        groupby: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        使用 IQR 方法识别离群值

        Args:
            df: 数据 DataFrame
            column: 数值列名
            multiplier: IQR 倍数（1.5 = 温和离群值，3 = 极端离群值）
            groupby: 分组列（按组别分别检测）

        Returns:
            标记离群值的 DataFrame（新增 outlier 列）
        """
        result = df.copy()
        result["_is_outlier"] = False
        result["_outlier_method"] = "IQR"
        result["_outlier_severity"] = ""

        def mark_group(group):
            vals = pd.to_numeric(group[column], errors="coerce")
            q1 = vals.quantile(0.25)
            q3 = vals.quantile(0.75)
            iqr = q3 - q1

            if iqr == 0:
                return group

            lower = q1 - multiplier * iqr
            upper = q3 + multiplier * iqr

            # 温和离群值 (1.5×IQR)
            mild_mult = multiplier
            mild_lower = q1 - mild_mult * iqr
            mild_upper = q3 + mild_mult * iqr

            # 极端离群值 (3×IQR)
            extreme_mult = 3.0
            extreme_lower = q1 - extreme_mult * iqr
            extreme_upper = q3 + extreme_mult * iqr

            mask = (vals.notna()) & ((vals < lower) | (vals > upper))
            group.loc[mask, "_is_outlier"] = True

            # 标记严重程度
            mild_mask = (vals < mild_lower) | (vals > mild_upper)
            extreme_mask = (vals < extreme_lower) | (vals > extreme_upper)
            group.loc[mask & extreme_mask, "_outlier_severity"] = "extreme"
            group.loc[mask & ~extreme_mask & mild_mask, "_outlier_severity"] = "mild"

            return group

        if groupby:
            valid_groups = [g for g in groupby if g in result.columns]
            if valid_groups:
                result = result.groupby(valid_groups, group_keys=False).apply(mark_group)
            else:
                result = mark_group(result)
        else:
            result = mark_group(result)

        outlier_count = result["_is_outlier"].sum()
        logger.info(f"IQR 离群值检测完成: 发现 {outlier_count} 个离群值 (乘数={multiplier})")
        return result[["_is_outlier", "_outlier_method", "_outlier_severity"]]

    @staticmethod
    def zscore_method(
        df: pd.DataFrame,
        column: str,
        threshold: float = 3.0,
        groupby: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        使用 Z-Score 方法识别离群值

        Args:
            df: 数据 DataFrame
            column: 数值列名
            threshold: Z-Score 阈值（默认 3.0）
            groupby: 分组列

        Returns:
            标记离群值的 DataFrame
        """
        result = df.copy()
        result["_is_outlier"] = False
        result["_outlier_method"] = "Z-Score"
        result["_zscore"] = 0.0
        result["_outlier_severity"] = ""

        def mark_group(group):
            vals = pd.to_numeric(group[column], errors="coerce")
            mean = vals.mean()
            std = vals.std()

            if std == 0 or pd.isna(std):
                return group

            z_scores = (vals - mean) / std
            group.loc[vals.notna(), "_zscore"] = z_scores[vals.notna()].abs()
            mask = vals.notna() & (z_scores.abs() > threshold)
            group.loc[mask, "_is_outlier"] = True

            # 标注严重程度
            group.loc[mask & (z_scores.abs() > 4), "_outlier_severity"] = "extreme"
            group.loc[mask & (z_scores.abs() <= 4), "_outlier_severity"] = "mild"

            return group

        if groupby:
            valid_groups = [g for g in groupby if g in result.columns]
            if valid_groups:
                result = result.groupby(valid_groups, group_keys=False).apply(mark_group)
            else:
                result = mark_group(result)
        else:
            result = mark_group(result)

        outlier_count = result["_is_outlier"].sum()
        logger.info(f"Z-Score 离群值检测完成: 发现 {outlier_count} 个离群值 (阈值={threshold})")
        return result[["_is_outlier", "_outlier_method", "_zscore", "_outlier_severity"]]

    @staticmethod
    def mad_method(
        df: pd.DataFrame,
        column: str,
        threshold: float = 3.5,
        groupby: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        使用 MAD（绝对中位差）方法识别离群值，对异常值更稳健

        Args:
            df: 数据 DataFrame
            column: 数值列名
            threshold: MAD 倍数阈值（默认 3.5）
            groupby: 分组列

        Returns:
            标记离群值的 DataFrame
        """
        result = df.copy()
        result["_is_outlier"] = False
        result["_outlier_method"] = "MAD"
        result["_mad_score"] = 0.0
        result["_outlier_severity"] = ""

        def mark_group(group):
            vals = pd.to_numeric(group[column], errors="coerce")
            median = vals.median()
            mad = np.median(np.abs(vals - median))

            if mad == 0 or pd.isna(mad):
                return group

            # Modified Z-Score
            modified_z = 0.6745 * (vals - median) / mad
            group.loc[vals.notna(), "_mad_score"] = modified_z[vals.notna()].abs()
            mask = vals.notna() & (modified_z.abs() > threshold)
            group.loc[mask, "_is_outlier"] = True

            # 严重程度
            group.loc[mask & (modified_z.abs() > 5), "_outlier_severity"] = "extreme"
            group.loc[mask & (modified_z.abs() <= 5), "_outlier_severity"] = "mild"

            return group

        if groupby:
            valid_groups = [g for g in groupby if g in result.columns]
            if valid_groups:
                result = result.groupby(valid_groups, group_keys=False).apply(mark_group)
            else:
                result = mark_group(result)
        else:
            result = mark_group(result)

        outlier_count = result["_is_outlier"].sum()
        logger.info(f"MAD 离群值检测完成: 发现 {outlier_count} 个离群值 (阈值={threshold})")
        return result[["_is_outlier", "_outlier_method", "_mad_score", "_outlier_severity"]]

    @staticmethod
    def detect_outliers(
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        method: str = "iqr",
        threshold: float = 3.0,
        groupby: Optional[List[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        综合离群值检测，对指定列或所有数值列执行检测

        Args:
            df: 数据 DataFrame
            columns: 要检测的列（默认所有数值列）
            method: 方法 (iqr / zscore / mad / all)
            threshold: 阈值
            groupby: 分组列

        Returns:
            列名到离群值标记 DataFrame 的字典
        """
        target_cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
        results = {}

        for col in target_cols:
            if col not in df.columns:
                continue

            try:
                if method == "iqr":
                    result = OutlierDetector.iqr_method(
                        df, col, multiplier=threshold, groupby=groupby
                    )
                elif method == "zscore":
                    result = OutlierDetector.zscore_method(
                        df, col, threshold=threshold, groupby=groupby
                    )
                elif method == "mad":
                    result = OutlierDetector.mad_method(
                        df, col, threshold=threshold, groupby=groupby
                    )
                elif method == "all":
                    # 综合多种方法（投票机制）
                    iqr_result = OutlierDetector.iqr_method(df, col, multiplier=1.5, groupby=groupby)
                    zscore_result = OutlierDetector.zscore_method(df, col, threshold=3, groupby=groupby)
                    mad_result = OutlierDetector.mad_method(df, col, threshold=3.5, groupby=groupby)

                    result = iqr_result.copy()
                    result["_votes"] = (
                        iqr_result["_is_outlier"].astype(int)
                        + zscore_result["_is_outlier"].astype(int)
                        + mad_result["_is_outlier"].astype(int)
                    )
                    # 至少 2 种方法确认
                    result["_is_outlier"] = result["_votes"] >= 2
                    result["_outlier_method"] = "Ensemble(vote>=2/3)"

                outlier_count = result["_is_outlier"].sum()
                if outlier_count > 0:
                    results[col] = result
                    logger.info(f"  列 '{col}': 发现 {outlier_count} 个离群值")

            except Exception as e:
                logger.warning(f"列 '{col}' 离群值检测失败: {e}")
                continue

        logger.info(f"离群值检测完成: 检查了 {len(target_cols)} 列, {len(results)} 列发现离群值")
        return results

    @staticmethod
    def get_outlier_summary(
        outlier_results: Dict[str, pd.DataFrame],
        original_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        汇总所有离群值检测结果

        Args:
            outlier_results: detect_outliers 的输出
            original_df: 原始数据

        Returns:
            离群值汇总表
        """
        summary_rows = []

        for col, result in outlier_results.items():
            outlier_mask = result["_is_outlier"]
            if outlier_mask.sum() == 0:
                continue

            outlier_rows = original_df.loc[outlier_mask.index[outlier_mask]]
            severity = result["_outlier_severity"].value_counts().to_dict() if "_outlier_severity" in result.columns else {}

            summary_rows.append({
                "variable": col,
                "outlier_count": int(outlier_mask.sum()),
                "total_count": len(outlier_mask),
                "outlier_pct": round(float(outlier_mask.mean() * 100), 2),
                "method": result["_outlier_method"].iloc[0] if "_outlier_method" in result.columns else "",
                "mild_count": severity.get("mild", 0),
                "extreme_count": severity.get("extreme", 0),
            })

        if not summary_rows:
            return pd.DataFrame()

        summary_df = pd.DataFrame(summary_rows)
        summary_df = summary_df.sort_values("outlier_count", ascending=False)
        return summary_df
