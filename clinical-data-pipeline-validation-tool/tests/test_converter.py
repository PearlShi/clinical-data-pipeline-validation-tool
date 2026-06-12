"""
转换模块测试
===========
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import os

from src.conversion.variable_mapper import VariableMapper
from src.conversion.variable_generator import VariableGenerator
from src.conversion.conversion_log import ConversionLog


class TestVariableMapper:
    """变量映射测试"""

    @pytest.fixture
    def mapper(self):
        return VariableMapper({
            "direct_mappings": {
                "SUBJID": "SUBJID",
                "AGE": "AGE",
                "SEX": "SEX",
            },
            "date_mappings": {
                "RFSTDTC": "RFSTDTC",
            },
            "value_mappings": {
                "SEX": {"男": "M", "女": "F", "Male": "M", "Female": "F"},
            }
        })

    def test_exact_match(self, mapper):
        std, conf = mapper.map_variable_name("AGE")
        assert std == "AGE"
        assert conf == 1.0

    def test_case_insensitive(self, mapper):
        std, conf = mapper.map_variable_name("age")
        assert std == "AGE"

    def test_no_match(self, mapper):
        std, conf = mapper.map_variable_name("NONEXISTENT_VAR")
        assert conf < 1.0

    def test_value_mapping(self, mapper):
        assert mapper.map_value("SEX", "男") == "M"
        assert mapper.map_value("SEX", "Female") == "F"
        assert mapper.map_value("SEX", "M") == "M"  # 已映射

    def test_auto_detect(self, mapper):
        cols = ["SUBJID", "age", "SEX", "UNKNOWN"]
        detected = mapper.auto_detect_mappings(cols)
        assert len(detected) >= 3


class TestVariableGenerator:
    """变量生成测试"""

    @pytest.fixture
    def generator(self):
        return VariableGenerator({
            "STUDYID": "TEST001",
            "DOMAIN": "DM",
            "AGEU": "YEARS",
        })

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            "SUBJID": ["0001", "0002", "0003"],
            "SITEID": ["SITE01", "SITE01", "SITE02"],
        })

    def test_generate_usubjid(self, generator, sample_df):
        result = generator.generate_usubjid(sample_df)
        assert len(result) == 3
        assert result.iloc[0] == "TEST001-SITE01-0001"
        assert result.iloc[2] == "TEST001-SITE02-0003"

    def test_generate_studyid(self, generator, sample_df):
        result = generator.generate_studyid(sample_df)
        assert all(result == "TEST001")

    def test_generate_domain(self, generator, sample_df):
        result = generator.generate_domain(sample_df, domain="AE")
        assert all(result == "AE")

    def test_date_normalization(self, generator):
        dates = pd.Series(["2024-01-15", "2024/03/20", "15-06-2024", None])
        result = generator.normalize_date(dates, output_format="%Y-%m-%d")
        assert result.iloc[0] == "2024-01-15"
        assert result.iloc[1] == "2024-03-20"
        assert result.iloc[2] == "2024-06-15"
        assert pd.isna(result.iloc[3])

    def test_normalize_numeric(self, generator):
        series = pd.Series([1.23456, 2.78901, 3.14159])
        result = generator.normalize_numeric(series, decimal_places=2)
        assert result.iloc[0] == 1.23
        assert result.iloc[2] == 3.14


class TestConversionLog:
    """转换日志测试"""

    def test_log_creation(self):
        log = ConversionLog(study_id="TEST001", domain="DM")
        assert log.study_id == "TEST001"
        assert log.domain == "DM"
        assert len(log.steps) == 0

    def test_add_step(self):
        log = ConversionLog()
        log.add_step("测试步骤", "生成", "生成了 USUBJID", affected_rows=10)
        assert len(log.steps) == 1
        assert log.steps[0].step_name == "测试步骤"

    def test_get_summary(self):
        log = ConversionLog(study_id="TEST001")
        log.add_step("步骤1", "加载", "加载数据")
        log.add_step("步骤2", "转换", "转换格式")
        summary = log.get_summary()
        assert summary["total_steps"] == 2
        assert summary["duration_seconds"] >= 0
