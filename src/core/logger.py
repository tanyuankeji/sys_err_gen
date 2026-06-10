# -*- coding: utf-8 -*-
"""
多级别日志系统模块

提供统一的日志记录功能，支持 DEBUG / INFO / WARNING / ERROR / CRITICAL 五个级别。
日志同时输出到控制台和文件，文件按日期轮转。

使用示例:
    from src.core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("程序启动")
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class LogManager:
    """日志管理器，负责初始化与获取 logger 实例"""

    _initialized: bool = False
    _log_level: int = logging.DEBUG
    _log_dir: str = "logs"
    _log_format: str = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    )
    _date_format: str = "%Y-%m-%d %H:%M:%S"

    @classmethod
    def init(
        cls,
        log_level: str = "DEBUG",
        log_dir: str = "logs",
        log_file: Optional[str] = None,
    ) -> None:
        """
        初始化日志系统

        Args:
            log_level: 日志级别，可选 DEBUG / INFO / WARNING / ERROR / CRITICAL
            log_dir: 日志文件存放目录
            log_file: 日志文件名，为 None 时按日期自动命名
        """
        if cls._initialized:
            return

        # 解析日志级别
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        cls._log_level = level_map.get(log_level.upper(), logging.DEBUG)
        cls._log_dir = log_dir

        # 确保日志目录存在
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # 生成日志文件名
        if log_file is None:
            date_str = datetime.now().strftime("%Y%m%d")
            log_file = f"sys_err_gen_{date_str}.log"

        log_path = os.path.join(log_dir, log_file)

        # 创建根 logger
        root_logger = logging.getLogger()
        root_logger.setLevel(cls._log_level)

        # 清除已有的 handler，避免重复输出
        root_logger.handlers.clear()

        # 控制台 handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(cls._log_level)
        console_formatter = logging.Formatter(cls._log_format, cls._date_format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # 文件 handler（支持轮转，单文件最大 10MB，保留 5 个备份）
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(cls._log_level)
        file_formatter = logging.Formatter(cls._log_format, cls._date_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        cls._initialized = True
        root_logger.debug("日志系统初始化完成，日志文件: %s", log_path)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 logger 实例

    Args:
        name: logger 名称，建议使用 __name__

    Returns:
        logging.Logger 实例
    """
    return logging.getLogger(name)
