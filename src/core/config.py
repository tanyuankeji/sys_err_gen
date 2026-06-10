# -*- coding: utf-8 -*-
"""
配置加载模块

使用 pydantic-settings 从 .env 文件和 YAML 配置文件加载全局配置。
所有配置项通过 Pydantic 模型进行类型校验。

使用示例:
    from src.core.config import load_config
    settings = load_config()
    print(settings.excel_file)
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, model_validator


class ExcelConfig(BaseModel):
    """Excel 输入文件配置"""

    file: str = Field(default="sys_err错误表.xls", description="Excel 文件路径")
    sheet: str = Field(default="错误动作", description="目标 Sheet 名称")
    merge_columns: List[str] = Field(
        default_factory=lambda: ["类型", "模块"],
        description="存在合并单元格需要向前填充的列名",
    )


class MatchColumnConfig(BaseModel):
    """单列匹配规则配置"""

    name: str = Field(description="列名（中文）")
    keyword: str = Field(default="", description="匹配关键词，为空则匹配任意非空值")


class MatchConfig(BaseModel):
    """匹配规则配置"""

    columns: List[MatchColumnConfig] = Field(
        default_factory=list,
        description="匹配列规则列表，行为 ALL 匹配（所有条件需同时满足）",
    )


class TemplateConfig(BaseModel):
    """模板配置"""

    file: str = Field(default="templates/error_handler.j2", description="Jinja2 模板文件路径")
    autoescape: bool = Field(default=False, description="是否启用 HTML 自动转义")


class OutputConfig(BaseModel):
    """输出配置"""

    directory: str = Field(default="output", description="输出目录")
    filename: str = Field(default="sys_err_gen.v", description="输出文件名")
    overwrite: bool = Field(default=True, description="是否覆盖已有文件")


class LoggingConfig(BaseModel):
    """日志配置"""

    level: str = Field(default="DEBUG", description="日志级别")
    dir: str = Field(default="logs", description="日志目录")
    file: Optional[str] = Field(default=None, description="日志文件名")


class AppConfig(BaseModel):
    """应用全局配置"""

    excel: ExcelConfig = Field(default_factory=ExcelConfig)
    match: MatchConfig = Field(default_factory=MatchConfig)
    template: TemplateConfig = Field(default_factory=TemplateConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @model_validator(mode="after")
    def resolve_paths(self) -> "AppConfig":
        """将相对路径转换为基于项目根目录的绝对路径"""
        project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
        self.excel.file = str(Path(project_root) / self.excel.file)
        self.template.file = str(Path(project_root) / self.template.file)
        self.output.directory = str(Path(project_root) / self.output.directory)
        self.logging.dir = str(Path(project_root) / self.logging.dir)
        return self


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    加载应用配置

    优先级: YAML 配置文件 > .env 环境变量 > 默认值

    Args:
        config_path: YAML 配置文件路径，为 None 时从 .env 或默认路径读取

    Returns:
        AppConfig 实例

    Raises:
        FileNotFoundError: 配置文件不存在时抛出
        ValueError: 配置格式错误时抛出
    """
    project_root = os.getcwd()
    os.environ.setdefault("PROJECT_ROOT", project_root)

    # 确定 YAML 配置文件路径
    if config_path is None:
        config_path = os.environ.get(
            "CONFIG_FILE",
            str(Path(project_root) / "config" / "match_config.yaml"),
        )

    yaml_data: Dict[str, Any] = {}
    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}
    else:
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    # 从 .env 文件补充配置
    excel_file = os.environ.get("EXCEL_FILE", "")
    if excel_file and "excel" not in yaml_data:
        yaml_data.setdefault("excel", {})
    if excel_file:
        yaml_data["excel"].setdefault("file", excel_file)

    log_level = os.environ.get("LOG_LEVEL", "")
    if log_level and "logging" not in yaml_data:
        yaml_data.setdefault("logging", {})
    if log_level:
        yaml_data["logging"].setdefault("level", log_level)

    config = AppConfig(**yaml_data)
    return config
