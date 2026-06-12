"""
批量处理模块
===========
支持对目录下的多个数据文件批量执行校验与转换流程。
"""

import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from src.core.data_loader import DataLoader, BatchDataLoader

logger = logging.getLogger(__name__)


class BatchProcessor:
    """批量处理器，对多个文件并行执行处理流程"""

    def __init__(self, max_workers: int = 4):
        """
        初始化批量处理器

        Args:
            max_workers: 最大并行工作线程数
        """
        self.max_workers = max_workers

    def process_directory(
        self,
        input_dir: Union[str, Path],
        process_func: Callable[[str, str], Any],
        output_dir: Optional[Union[str, Path]] = None,
        file_pattern: str = "*.*",
        **kwargs
    ) -> Dict[str, Any]:
        """
        批量处理目录下的所有数据文件

        Args:
            input_dir: 输入目录
            process_func: 处理函数，接收 (input_path, output_path) 返回结果
            output_dir: 输出目录（可选）
            file_pattern: 文件匹配模式
            **kwargs: 额外参数

        Returns:
            文件名到处理结果的字典
        """
        input_dir = Path(input_dir)
        loader = BatchDataLoader(input_dir)
        files = loader.list_files(file_pattern)

        if not files:
            logger.warning(f"目录中没有找到支持的数据文件: {input_dir}")
            return {}

        results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {}

            for file_path in files:
                if output_dir:
                    out_path = Path(output_dir) / file_path.name
                else:
                    out_path = file_path.parent / f"{file_path.stem}_processed{file_path.suffix}"

                future = executor.submit(
                    self._safe_process,
                    process_func,
                    str(file_path),
                    str(out_path),
                    **kwargs
                )
                future_to_file[future] = file_path.name

            for future in as_completed(future_to_file):
                fname = future_to_file[future]
                try:
                    results[fname] = future.result()
                    logger.info(f"处理完成: {fname}")
                except Exception as e:
                    results[fname] = {"error": str(e)}
                    logger.error(f"处理失败 {fname}: {e}")

        return results

    def process_file_list(
        self,
        file_paths: List[Union[str, Path]],
        process_func: Callable,
        output_dir: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        批量处理指定的文件列表

        Args:
            file_paths: 文件路径列表
            process_func: 处理函数
            output_dir: 输出目录
            **kwargs: 额外参数

        Returns:
            文件名到处理结果的字典
        """
        results = {}
        for file_path in file_paths:
            file_path = Path(file_path)
            if output_dir:
                out_path = Path(output_dir) / file_path.name
            else:
                out_path = file_path.parent / f"{file_path.stem}_processed{file_path.suffix}"

            try:
                result = process_func(str(file_path), str(out_path), **kwargs)
                results[file_path.name] = result
                logger.info(f"处理完成: {file_path.name}")
            except Exception as e:
                results[file_path.name] = {"error": str(e)}
                logger.error(f"处理失败 {file_path.name}: {e}")

        return results

    @staticmethod
    def _safe_process(func, *args, **kwargs) -> Any:
        """安全执行处理函数，捕获并包装异常"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"处理过程出错: {e}")
            raise
