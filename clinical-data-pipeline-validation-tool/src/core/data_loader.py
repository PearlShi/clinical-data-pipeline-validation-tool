"""
数据加载模块
===========
支持 CSV 和 Excel 格式临床数据的读取，提供统一的数据加载接口。
自动检测文件编码、格式，支持常见的数据预处理操作。
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Union, List, Dict
import logging

logger = logging.getLogger(__name__)


class DataLoadError(Exception):
    """数据加载异常"""
    pass


class DataLoader:
    """数据加载器，支持 CSV 与 Excel 格式的临床数据读取"""

    # 支持的文件格式
    SUPPORTED_FORMATS = {".csv", ".xlsx", ".xls", ".xlsm"}

    def __init__(self, file_path: Union[str, Path]):
        """
        初始化数据加载器

        Args:
            file_path: 数据文件路径
        """
        self.file_path = Path(file_path)
        self._validate_file()

    def _validate_file(self) -> None:
        """验证文件是否存在且格式受支持"""
        if not self.file_path.exists():
            raise DataLoadError(f"文件不存在: {self.file_path}")

        if self.file_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise DataLoadError(
                f"不支持的文件格式: {self.file_path.suffix}。"
                f"支持格式: {', '.join(self.SUPPORTED_FORMATS)}"
            )

    def load(
        self,
        sheet_name: Optional[Union[str, int]] = 0,
        encoding: str = "utf-8",
        dtype_backend: str = "numpy_nullable",
        **kwargs
    ) -> pd.DataFrame:
        """
        加载数据文件为 DataFrame

        Args:
            sheet_name: Excel 工作表名或索引（仅 Excel 有效），默认第一个工作表
            encoding: CSV 文件编码
            dtype_backend: 数据类型后端
            **kwargs: 透传给 pandas.read_csv / pandas.read_excel 的额外参数

        Returns:
            包含数据的 DataFrame

        Raises:
            DataLoadError: 数据加载失败时抛出
        """
        suffix = self.file_path.suffix.lower()

        try:
            if suffix == ".csv":
                return self._load_csv(encoding=encoding, dtype_backend=dtype_backend, **kwargs)
            else:  # .xlsx, .xls, .xlsm
                return self._load_excel(sheet_name=sheet_name, dtype_backend=dtype_backend, **kwargs)
        except Exception as e:
            raise DataLoadError(f"数据加载失败: {e}")

    def _load_csv(
        self,
        encoding: str = "utf-8",
        dtype_backend: str = "numpy_nullable",
        **kwargs
    ) -> pd.DataFrame:
        """加载 CSV 文件，自动检测编码"""
        encodings_to_try = [encoding, "utf-8", "gbk", "gb2312", "latin-1"]

        for enc in encodings_to_try:
            try:
                df = pd.read_csv(
                    self.file_path,
                    encoding=enc,
                    dtype_backend=dtype_backend,
                    engine="c" if enc == "utf-8" else "python",
                    **kwargs
                )
                logger.info(f"成功加载 CSV 文件: {self.file_path} (编码: {enc})")
                return df
            except (UnicodeDecodeError, UnicodeError):
                continue

        # 最后的尝试：使用 latin-1 编码（不会失败）
        df = pd.read_csv(
            self.file_path,
            encoding="latin-1",
            dtype_backend=dtype_backend,
            **kwargs
        )
        logger.warning(f"CSV 文件使用 latin-1 编码加载: {self.file_path}")
        return df

    def _load_excel(
        self,
        sheet_name: Optional[Union[str, int]] = 0,
        dtype_backend: str = "numpy_nullable",
        **kwargs
    ) -> pd.DataFrame:
        """加载 Excel 文件"""
        df = pd.read_excel(
            self.file_path,
            sheet_name=sheet_name,
            dtype_backend=dtype_backend,
            engine="openpyxl" if self.file_path.suffix.lower() in (".xlsx", ".xlsm") else "xlrd",
            **kwargs
        )
        sheet_display = sheet_name if sheet_name is not None else "第一个"
        logger.info(f"成功加载 Excel 文件: {self.file_path} (工作表: {sheet_display})")
        return df

    def load_with_preview(self, **kwargs) -> tuple:
        """
        加载数据并返回预览信息

        Returns:
            (DataFrame, preview_info) 元组
        """
        df = self.load(**kwargs)
        preview = {
            "file_name": self.file_path.name,
            "file_size": self.file_path.stat().st_size,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "dtypes": {col: str(df[col].dtype) for col in df.columns},
            "missing_counts": df.isnull().sum().to_dict(),
            "memory_usage": df.memory_usage(deep=True).sum(),
        }
        return df, preview


class BatchDataLoader:
    """批量数据加载器，支持目录级别的数据加载"""

    def __init__(self, directory: Union[str, Path]):
        """
        初始化批量加载器

        Args:
            directory: 数据文件所在目录
        """
        self.directory = Path(directory)
        if not self.directory.is_dir():
            raise DataLoadError(f"目录不存在: {self.directory}")

    def list_files(self, pattern: str = "*.*") -> List[Path]:
        """列出目录中所有支持的数据文件"""
        files = []
        for ext in DataLoader.SUPPORTED_FORMATS:
            files.extend(self.directory.glob(f"*{ext}"))
            files.extend(self.directory.glob(f"*{ext.upper()}"))
        return sorted(files)

    def load_all(
        self,
        sheet_name: Optional[Union[str, int]] = 0,
        encoding: str = "utf-8",
        **kwargs
    ) -> Dict[str, pd.DataFrame]:
        """
        加载目录下所有支持的数据文件

        Returns:
            文件名到 DataFrame 的字典
        """
        result = {}
        for file_path in self.list_files():
            try:
                loader = DataLoader(file_path)
                df = loader.load(sheet_name=sheet_name, encoding=encoding, **kwargs)
                result[file_path.name] = df
                logger.info(f"批量加载成功: {file_path.name}")
            except DataLoadError as e:
                logger.error(f"加载文件失败 {file_path.name}: {e}")
                continue
        return result
