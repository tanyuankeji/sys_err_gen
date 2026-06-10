# -*- coding: utf-8 -*-
"""
Jinja2 模板渲染引擎模块

负责加载 Jinja2 模板文件，将匹配到的数据渲染为 Verilog 代码。

扩展点:
    - 可添加自定义 Jinja2 过滤器（如信号命名转换）
    - 可添加自定义测试函数
    - 支持模板继承和宏

使用示例:
    from src.core.template_engine import TemplateEngine
    engine = TemplateEngine("templates/error_handler.j2")
    code = engine.render(data_list)
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, Template

from src.core.config import TemplateConfig
from src.core.logger import get_logger

logger = get_logger(__name__)


class TemplateEngine:
    """Jinja2 模板引擎，负责渲染 Verilog 代码"""

    def __init__(self, config: TemplateConfig) -> None:
        """
        初始化模板引擎

        Args:
            config: 模板配置

        Raises:
            FileNotFoundError: 模板文件不存在时抛出
        """
        self.config: TemplateConfig = config
        template_path = config.file

        if not os.path.isfile(template_path):
            raise FileNotFoundError(f"模板文件不存在: {template_path}")

        # 分离模板目录和文件名
        template_dir = str(Path(template_path).parent)
        template_name = os.path.basename(template_path)

        # 创建 Jinja2 环境
        self.env: Environment = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=config.autoescape,
            trim_blocks=True,
            lstrip_blocks=False,
            keep_trailing_newline=True,
        )

        # 注册自定义过滤器
        self._register_filters()

        # 加载模板
        self.template: Template = self.env.get_template(template_name)
        logger.info("模板引擎初始化完成，模板: %s", template_name)

    def _register_filters(self) -> None:
        """注册 Jinja2 自定义过滤器，用于 Verilog 命名转换"""

        def to_upper(value: str) -> str:
            """转为大写"""
            return str(value).upper()

        def to_lower(value: str) -> str:
            """转为小写"""
            return str(value).lower()

        def to_snake_case(value: str) -> str:
            """将含有特殊字符的字符串转为 snake_case"""
            import re
            result = str(value).lower()
            result = re.sub(r"[^a-z0-9]+", "_", result)
            result = result.strip("_")
            return result

        def strip_underscore(value: str) -> str:
            """去除首尾下划线"""
            return str(value).strip("_")

        def verilog_comment(value: str) -> str:
            """将文本转为 Verilog 注释行"""
            lines = str(value).split("\n")
            return "\n".join(f"// {line}" for line in lines)

        self.env.filters["upper"] = to_upper
        self.env.filters["lower"] = to_lower
        self.env.filters["snake"] = to_snake_case
        self.env.filters["strip_us"] = strip_underscore
        self.env.filters["vcomment"] = verilog_comment

    def render(
        self,
        data_list: List[Dict[str, Any]],
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        渲染模板生成代码

        Args:
            data_list: 匹配到的数据行列表，模板中可通过 errors 变量访问
            extra_context: 额外的上下文变量，传入模板

        Returns:
            渲染后的 Verilog 代码字符串
        """
        context: Dict[str, Any] = {
            "errors": data_list,
            "error_count": len(data_list),
        }
        if extra_context:
            context.update(extra_context)

        logger.info("开始渲染模板，数据行数: %d", len(data_list))
        result = self.template.render(**context)
        logger.info("模板渲染完成，输出长度: %d 字符", len(result))
        return result
