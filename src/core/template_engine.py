# -*- coding: utf-8 -*-
"""
Jinja2 模板渲染引擎模块

负责加载 Jinja2 模板文件，将匹配到的数据渲染为 Verilog 代码。
支持：
    - 代码字符对齐（自动计算最大信号名宽度）
    - 条件生成（RSTB / FuSa / FLT_ERR_CNT 仅在有值时生成对应代码段）
    - 用户代码保护（USER_CODE 区域在重新生成时保留手动修改内容）

使用示例:
    from src.core.template_engine import TemplateEngine, SectionProtector
    engine = TemplateEngine(config)
    code = engine.render(data_list)
    merged = SectionProtector.merge(old_code, code)
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, Template

from src.core.config import TemplateConfig
from src.core.logger import get_logger

logger = get_logger(__name__)

# 代码保护区域标记
_USER_CODE_BEGIN = "// === USER_CODE_BEGIN:"
_USER_CODE_END = "// === USER_CODE_END:"


class SectionProtector:
    """代码保护合并器，在重新生成时保留用户手动修改的代码区域"""

    USER_BEGIN_PATTERN = re.compile(
        r"^\s*//\s*===\s*USER_CODE_BEGIN\s*:\s*(\w+)\s*===\s*$"
    )
    USER_END_PATTERN = re.compile(
        r"^\s*//\s*===\s*USER_CODE_END\s*:\s*(\w+)\s*===\s*$"
    )

    @staticmethod
    def extract_user_sections(old_code: str) -> Dict[str, str]:
        """
        从旧代码中提取所有 USER_CODE 区域的内容

        Args:
            old_code: 已存在的 Verilog 代码

        Returns:
            {section_name: content} 字典，不含标记行本身
        """
        sections: Dict[str, str] = {}
        lines = old_code.split("\n")

        current_section: Optional[str] = None
        current_content: List[str] = []

        for line in lines:
            begin_match = SectionProtector.USER_BEGIN_PATTERN.match(line)
            end_match = SectionProtector.USER_END_PATTERN.match(line)

            if current_section is None and begin_match:
                current_section = begin_match.group(1)
                current_content = []
            elif current_section is not None and end_match:
                if end_match.group(1) == current_section:
                    sections[current_section] = "\n".join(current_content)
                    logger.debug(
                        "提取用户代码区域: %s (%d 行)",
                        current_section,
                        len(current_content),
                    )
                current_section = None
                current_content = []
            elif current_section is not None:
                current_content.append(line)

        return sections

    @staticmethod
    def merge(new_code: str, old_code: Optional[str] = None) -> str:
        """
        将旧代码中的 USER_CODE 区域合并到新生成代码中

        如果旧代码不存在（首次生成），直接返回新代码（USER_CODE 区域为空）。

        Args:
            new_code: 新生成的代码
            old_code: 已存在的旧代码（None 表示首次生成）

        Returns:
            合并后的代码
        """
        if not old_code:
            logger.info("首次生成，无旧代码可合并")
            return new_code

        user_sections = SectionProtector.extract_user_sections(old_code)
        if not user_sections:
            logger.info("旧代码中无用户自定义区域，直接使用新代码")
            return new_code

        logger.info("检测到 %d 个用户代码区域，正在合并...", len(user_sections))

        result_lines: List[str] = []
        lines = new_code.split("\n")

        current_section: Optional[str] = None
        skip_block: bool = False

        for line in lines:
            begin_match = SectionProtector.USER_BEGIN_PATTERN.match(line)
            end_match = SectionProtector.USER_END_PATTERN.match(line)

            if begin_match:
                name = begin_match.group(1)
                current_section = name
                result_lines.append(line)
                if name in user_sections and user_sections[name].strip():
                    # 插入保留的用户代码
                    result_lines.append(user_sections[name])
                    skip_block = True
                    logger.info("  已合并用户区域: %s", name)
                continue

            if current_section is not None and end_match:
                if end_match.group(1) == current_section:
                    current_section = None
                    skip_block = False
                    result_lines.append(line)
                continue

            if skip_block:
                # 跳过新生成代码中的空内容，保留用户代码
                if line.strip() == "":
                    continue
                # 遇到非空行但不在用户区域标记间，结束跳过
                skip_block = False
                result_lines.append(line)
            else:
                result_lines.append(line)

        merged = "\n".join(result_lines)
        logger.info("代码合并完成")
        return merged


def _compute_signal_max_width(errors: List[Dict[str, Any]], suffix: str = "") -> int:
    """
    计算所有信号名的最大字符宽度，用于代码对齐

    Args:
        errors: 错误数据列表
        suffix: 信号名后缀（如 "_imp"）

    Returns:
        最大信号名长度
    """
    if not errors:
        return 16
    return max(
        len(str(err.get("数字信号", ""))) + len(suffix)
        for err in errors
    )


def _build_filtered_lists(errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    根据 RSTB / FuSa / FLT_ERR_CNT 字段构建过滤列表和存在标志

    Args:
        errors: 错误数据列表

    Returns:
        包含 filtered_* 列表和 has_* 标志的字典
    """
    result: Dict[str, Any] = {}

    # RSTB
    rstb_errors = [e for e in errors if e.get("RSTB", "") and str(e.get("RSTB", "")).strip()]
    result["has_rstb"] = len(rstb_errors) > 0
    result["rstb_errors"] = rstb_errors

    # FuSa
    fusa_errors = [e for e in errors if e.get("FuSa", "") and str(e.get("FuSa", "")).strip()]
    result["has_fusa"] = len(fusa_errors) > 0
    result["fusa_errors"] = fusa_errors

    # FLT_ERR_CNT
    fltcnt_errors = [
        e for e in errors
        if e.get("FLT_ERR_CNT", "") and str(e.get("FLT_ERR_CNT", "")).strip()
    ]
    result["has_fltcnt"] = len(fltcnt_errors) > 0
    result["fltcnt_errors"] = fltcnt_errors

    return result


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

        template_dir = str(Path(template_path).parent)
        template_name = os.path.basename(template_path)

        self.env: Environment = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=config.autoescape,
            trim_blocks=True,
            lstrip_blocks=False,
            keep_trailing_newline=True,
        )

        self._register_filters()
        self.template: Template = self.env.get_template(template_name)
        logger.info("模板引擎初始化完成，模板: %s", template_name)

    def _register_filters(self) -> None:
        """注册 Jinja2 自定义过滤器，用于 Verilog 命名转换"""

        def to_upper(value: str) -> str:
            return str(value).upper()

        def to_lower(value: str) -> str:
            return str(value).lower()

        def to_snake_case(value: str) -> str:
            result = str(value).lower()
            result = re.sub(r"[^a-z0-9]+", "_", result)
            return result.strip("_")

        def strip_underscore(value: str) -> str:
            return str(value).strip("_")

        def pad_right(value: str, width: int) -> str:
            """右侧填充空格到指定宽度，用于代码对齐"""
            s = str(value)
            if len(s) >= width:
                return s
            return s + " " * (width - len(s))

        def has_value(value: Any) -> bool:
            """判断值是否为非空（用于模板中判断可选字段）"""
            if value is None:
                return False
            s = str(value).strip()
            return s != "" and s != "nan" and s != "NaN"

        self.env.filters["upper"] = to_upper
        self.env.filters["lower"] = to_lower
        self.env.filters["snake"] = to_snake_case
        self.env.filters["strip_us"] = strip_underscore
        self.env.filters["pad_r"] = pad_right
        self.env.filters["has_val"] = has_value

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
        # 计算信号对齐宽度
        sig_max_width = _compute_signal_max_width(data_list)
        imp_max_width = _compute_signal_max_width(data_list, suffix="_imp")

        # 构建条件过滤列表
        filtered = _build_filtered_lists(data_list)

        context: Dict[str, Any] = {
            "errors": data_list,
            "error_count": len(data_list),
            "sig_max_width": sig_max_width,
            "imp_max_width": imp_max_width,
            **filtered,
        }
        if extra_context:
            context.update(extra_context)

        logger.info("开始渲染模板，数据行数: %d", len(data_list))
        logger.debug(
            "条件标志: has_rstb=%s, has_fusa=%s, has_fltcnt=%s",
            context["has_rstb"],
            context["has_fusa"],
            context["has_fltcnt"],
        )
        result = self.template.render(**context)
        logger.info("模板渲染完成，输出长度: %d 字符", len(result))
        return result
