"""
数据加载模块测试
=============
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import os

from src.core.data_loader import DataLoader, BatchDataLoader, DataLoadError


class TestDataLoader:
    """DataLoader 测试"""

    @pytest.fixture
    def csv_file(self):
        """创建临时 CSV 文件"""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            f.write("USUBJID,AGE,SEX,RFSTDTC\n")
            f.write("SUBJ-001,45,M,2024-01-15\n")
            f.write("SUBJ-002,32,F,2024-02-20\n")
            f.write("SUBJ-003,28,,2024-03-10\n")
            tmp_path = f.name
        yield tmp_path
        os.unlink(tmp_path)

    @pytest.fixture
    def excel_file(self):
        """创建临时 Excel 文件"""
        df = pd.DataFrame({
            "USUBJID": ["SUBJ-001", "SUBJ-002"],
            "AGE": [45, 32],
            "SEX": ["M", "F"],
        })
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = f.name
        df.to_excel(tmp_path, index=False)
        yield tmp_path
        os.unlink(tmp_path)

    def test_load_csv(self, csv_file):
        loader = DataLoader(csv_file)
        df = loader.load()
        assert len(df) == 3
        assert list(df.columns) == ["USUBJID", "AGE", "SEX", "RFSTDTC"]

    def test_load_excel(self, excel_file):
        loader = DataLoader(excel_file)
        df = loader.load()
        assert len(df) == 2
        assert "USUBJID" in df.columns

    def test_file_not_found(self):
        with pytest.raises(DataLoadError):
            DataLoader("nonexistent_file.csv")

    def test_unsupported_format(self):
        with pytest.raises(DataLoadError):
            DataLoader("data.txt")

    def test_load_with_preview(self, csv_file):
        loader = DataLoader(csv_file)
        df, preview = loader.load_with_preview()
        assert preview["rows"] == 3
        assert preview["columns"] == 4
        assert "USUBJID" in preview["column_names"]

    def test_empty_csv(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            f.write("USUBJID,AGE\n")
            tmp_path = f.name
        try:
            loader = DataLoader(tmp_path)
            df = loader.load()
            assert len(df) == 0
        finally:
            os.unlink(tmp_path)


class TestBatchDataLoader:
    """BatchDataLoader 测试"""

    @pytest.fixture
    def temp_dir_with_files(self):
        """创建包含多个 CSV 文件的临时目录"""
        tmp_dir = Path(tempfile.mkdtemp())
        for i in range(3):
            file_path = tmp_dir / f"data_{i}.csv"
            with open(file_path, "w") as f:
                f.write("USUBJID,AGE\n")
                f.write(f"SUBJ-00{i},{20 + i}\n")
        yield tmp_dir
        import shutil
        shutil.rmtree(tmp_dir)

    def test_list_files(self, temp_dir_with_files):
        loader = BatchDataLoader(temp_dir_with_files)
        files = loader.list_files()
        assert len(files) == 3

    def test_load_all(self, temp_dir_with_files):
        loader = BatchDataLoader(temp_dir_with_files)
        result = loader.load_all()
        assert len(result) == 3
        for name, df in result.items():
            assert len(df) == 1
