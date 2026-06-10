# -*- coding: utf-8 -*-
"""
Excel 文件读取与解析模块

负责读取指定 Excel 文件的指定 Sheet，处理合并单元格（向前填充 NaN），
将数据转换为结构化的字典列表。

核心功能:
    1. 读取 .xls / .xlsx 文件
    2. 自动识别并 forward-fill 合并单元格产生的 NaN 值
    3. 返回处理后的 DataFrame 和结构化数据

使用示例:
    from src.core.excel_reader import ExcelReader
    reader = ExcelReader("sys_err错误表.xls")
    df = reader.read_sheet("错误动作", merge_columns=["类型", "模块"])
    records = reader.to_records(df)
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.logger import get_logger

logger = get_logger(__name__)


class ExcelReader:
    """Excel 文件读取器，支持合并单元格处理"""

    def __init__(self, file_path: str) -> None:
        """
        初始化 Excel 读取器

        Args:
            file_path: Excel 文件路径，支持 .xls 和 .xlsx 格式

        Raises:
            FileNotFoundError: 文件不存在时抛出
        """
        self.file_path: str = file_path
        self._validate_file()
        logger.info("ExcelReader 初始化完成，文件: %s", file_path)

    def _validate_file(self) -> None:
        """校验文件是否存在且格式正确"""
        import os
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"Excel 文件不存在: {self.file_path}")
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext not in (".xls", ".xlsx"):
            raise ValueError(f"不支持的文件格式: {ext}，仅支持 .xls / .xlsx")

    def read_sheet(
        self,
        sheet_name: str,
        merge_columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        读取指定 Sheet 并处理合并单元格

        合并单元格处理策略:
            对 merge_columns 中指定的列执行向前填充（forward fill），
            即用上一个非空值填充当前行的 NaN，模拟 Excel 合并单元格的视觉效果。

        Args:
            sheet_name: Sheet 名称
            merge_columns: 需要向前填充的列名列表，用于处理合并单元格

        Returns:
            处理后的 pandas DataFrame

        Raises:
            ValueError: Sheet 不存在或列名不存在时抛出
        """
        logger.info("正在读取 Sheet: %s", sheet_name)

        try:
            df = pd.read_excel(self.file_path, sheet_name=sheet_name)
        except ValueError:
            available = pd.ExcelFile(self.file_path).sheet_names
            raise ValueError(
                f"Sheet '{sheet_name}' 不存在，可用的 Sheet: {available}"
            )

        if df.empty:
            logger.warning("Sheet '%s' 为空", sheet_name)
            return df

        logger.debug(
            "Sheet '%s' 读取完成，形状: %s，列: %s",
            sheet_name,
            df.shape,
            list(df.columns),
        )

        # 处理合并单元格：向前填充
        if merge_columns:
            existing_cols = [c for c in merge_columns if c in df.columns]
            missing_cols = [c for c in merge_columns if c not in df.columns]
            if missing_cols:
                logger.warning("以下合并列不存在于数据中: %s", missing_cols)
            if existing_cols:
                df[existing_cols] = df[existing_cols].ffill()
                logger.info("已对 %d 列执行向前填充: %s", len(existing_cols), existing_cols)

        # 将所有 NaN 转换为空字符串，方便后续比较
        df = df.fillna("")

        return df

    @staticmethod
    def to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        将 DataFrame 转换为字典列表

        Args:
            df: pandas DataFrame

        Returns:
            字典列表，每个字典代表一行数据，键为列名，值为单元格内容
        """
        records = df.to_dict(orient="records")
        logger.debug("转换完成，共 %d 条记录", len(records))
        return records
