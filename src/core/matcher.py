# -*- coding: utf-8 -*-
"""
列匹配引擎模块

根据配置的匹配规则，从 Excel 数据中筛选出符合条件的行。
支持多列 AND 逻辑匹配，关键词支持精确匹配（空关键词表示匹配任意非空值）。

匹配规则:
    - keyword 为空字符串("")：匹配所有该列有内容的行（非空即匹配）
    - keyword 不为空：精确匹配该列的值是否等于 keyword

使用示例:
    from src.core.matcher import ColumnMatcher
    matcher = ColumnMatcher(match_config)
    matched = matcher.match(records)
"""

from typing import Any, Dict, List

from src.core.config import MatchConfig
from src.core.logger import get_logger

logger = get_logger(__name__)


class ColumnMatcher:
    """列匹配引擎，按规则筛选数据行"""

    def __init__(self, config: MatchConfig) -> None:
        """
        初始化匹配引擎

        Args:
            config: 匹配规则配置
        """
        self.config: MatchConfig = config
        logger.info(
            "ColumnMatcher 初始化完成，匹配规则: %d 列",
            len(config.columns),
        )

    def match(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据配置的匹配规则筛选记录

        匹配逻辑: ALL 模式，即所有指定的列条件必须同时满足，行才被选中。

        Args:
            records: 待筛选的记录列表，每条记录为 {列名: 值} 的字典

        Returns:
            匹配成功的记录列表

        Raises:
            ValueError: 配置的列名在数据中不存在时抛出
        """
        if not self.config.columns:
            logger.info("未配置匹配规则，返回所有 %d 条记录", len(records))
            return records

        # 校验列名是否存在
        if records:
            available_cols = set(records[0].keys())
            for col_cfg in self.config.columns:
                if col_cfg.name not in available_cols:
                    raise ValueError(
                        f"匹配列 '{col_cfg.name}' 不存在于数据中，"
                        f"可用列: {sorted(available_cols)}"
                    )

        # 逐行匹配
        matched: List[Dict[str, Any]] = []
        for idx, record in enumerate(records):
            if self._match_row(record):
                matched.append(record)
                logger.debug(
                    "第 %d 行匹配成功: %s",
                    idx + 1,
                    {c.name: record.get(c.name, "") for c in self.config.columns},
                )

        logger.info(
            "匹配完成: 总行数 %d, 匹配行数 %d",
            len(records),
            len(matched),
        )

        if not matched:
            logger.warning("没有行匹配到规则，请检查配置列和关键词")

        return matched

    def _match_row(self, record: Dict[str, Any]) -> bool:
        """
        判断单行是否匹配所有列规则

        Args:
            record: 单行数据字典

        Returns:
            True 表示匹配所有列规则
        """
        for col_cfg in self.config.columns:
            cell_value = record.get(col_cfg.name, "")

            if col_cfg.keyword == "":
                # 空关键词：匹配任意非空值，排除空字符串和 NaN
                if not cell_value or cell_value == "":
                    return False
            else:
                # 非空关键词：精确匹配
                if str(cell_value).strip() != col_cfg.keyword.strip():
                    return False

        return True
