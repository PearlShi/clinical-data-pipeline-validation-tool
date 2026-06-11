"""
可复用脚本模块测试
===============
"""

import pytest
import pandas as pd
import numpy as np

from src.scripts.clean_data import DataCleaner
from src.scripts.stats_checks import StatisticalChecker
from src.scripts.outlier_detection import OutlierDetector


class TestDataCleaner:
    """数据清洗测试"""

    @pytest.fixture
    def dirty_df(self):
        return pd.DataFrame({
            "USUBJID": ["S-001", "S-002", "S-001", "S-003"],
            "AGE": [45, None, 32, 28],
            "SEX": [" M ", "F", "M", None],
            "ARM": ["PLACEBO", "TREATMENT", "PLACEBO", "UNKNOWN"],
        })

    def test_remove_duplicates(self, dirty_df):
        result = DataCleaner.remove_duplicates(dirty_df)
        assert len(result) == 3  # 1 duplicate removed

    def test_remove_duplicates_subset(self, dirty_df):
        result = DataCleaner.remove_duplicates(dirty_df, subset=["USUBJID"])
        assert len(result) == 3

    def test_strip_whitespace(self, dirty_df):
        result = DataCleaner.strip_whitespace(dirty_df)
        assert result.iloc[0]["SEX"] == "M"

    def test_mark_missing_values(self, dirty_df):
        result = DataCleaner.mark_missing_values(dirty_df)
        assert result.isnull().sum().sum() >= 2

    def test_fill_missing_values_auto(self, dirty_df):
        result = DataCleaner.fill_missing_values(dirty_df, strategy="auto")
        assert result.isnull().sum().sum() < dirty_df.isnull().sum().sum()

    def test_standardize_case(self, dirty_df):
        result = DataCleaner.standardize_case(dirty_df, case="upper")
        assert result.iloc[0]["SEX"] == " M "  # strip 不改变大小写
        result2 = DataCleaner.standardize_case(
            DataCleaner.strip_whitespace(dirty_df), case="upper"
        )
        assert result2.iloc[0]["SEX"] == "M"

    def test_clean_and_prepare(self, dirty_df):
        result = DataCleaner.clean_and_prepare(
            dirty_df,
            drop_duplicates=True,
            strip_whitespace=True,
            mark_missing=True,
            standardize_case=True,
        )
        assert len(result) <= len(dirty_df)


class TestStatisticalChecker:
    """统计校验测试"""

    @pytest.fixture
    def sample_df(self):
        np.random.seed(42)
        return pd.DataFrame({
            "AGE": np.random.normal(45, 10, 100),
            "WEIGHT": np.random.normal(70, 12, 100),
            "SEX": np.random.choice(["M", "F"], 100),
            "ARM": np.random.choice(["PLACEBO", "TREATMENT"], 100),
        })

    def test_describe_dataset(self, sample_df):
        desc = StatisticalChecker.describe_dataset(sample_df)
        assert desc["rows"] == 100
        assert "AGE" in desc["numeric_summary"]
        assert "SEX" in desc["categorical_summary"]

    def test_check_value_distribution(self, sample_df):
        dist = StatisticalChecker.check_value_distribution(
            sample_df, "AGE", expected_min=0, expected_max=120
        )
        assert dist["column"] == "AGE"
        assert dist["count"] == 100
        assert "range_checks" in dist

    def test_check_categorical_balance(self, sample_df):
        result = StatisticalChecker.check_categorical_balance(sample_df, "SEX")
        assert result["column"] == "SEX"
        assert result["total"] == 100
        assert "proportions" in result

    def test_cross_tabulation(self, sample_df):
        result = StatisticalChecker.cross_tabulation(sample_df, "SEX", "ARM")
        assert "table" in result
        assert "chi_square_test" in result


class TestOutlierDetector:
    """离群值检测测试"""

    @pytest.fixture
    def df_with_outliers(self):
        np.random.seed(42)
        values = np.random.normal(50, 10, 100)
        values[0] = 999  # 极端离群值
        values[1] = -100  # 极端离群值
        values[2] = 85  # 温和离群值
        return pd.DataFrame({
            "VALUE": values,
            "GROUP": np.random.choice(["A", "B"], 100),
            "DOMAIN": ["DM"] * 100,
        })

    def test_iqr_method(self, df_with_outliers):
        result = OutlierDetector.iqr_method(
            df_with_outliers, "VALUE", multiplier=1.5
        )
        assert result["_is_outlier"].sum() >= 2

    def test_zscore_method(self, df_with_outliers):
        result = OutlierDetector.zscore_method(
            df_with_outliers, "VALUE", threshold=3
        )
        assert result["_is_outlier"].sum() >= 2

    def test_mad_method(self, df_with_outliers):
        result = OutlierDetector.mad_method(
            df_with_outliers, "VALUE", threshold=3.5
        )
        assert result["_is_outlier"].sum() >= 2

    def test_detect_outliers(self, df_with_outliers):
        results = OutlierDetector.detect_outliers(
            df_with_outliers, columns=["VALUE"], method="all"
        )
        assert "VALUE" in results

    def test_get_outlier_summary(self, df_with_outliers):
        results = OutlierDetector.detect_outliers(
            df_with_outliers, columns=["VALUE"], method="iqr"
        )
        summary = OutlierDetector.get_outlier_summary(results, df_with_outliers)
        assert len(summary) > 0
        assert "outlier_count" in summary.columns
