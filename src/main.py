# -*- coding: utf-8 -*-
"""
sys_err_gen - 系统错误码 Verilog 代码自动生成工具

根据 Excel 错误表、匹配配置和 Jinja2 模板，自动生成 Verilog RTL 代码。

流程:
    1. 读取 YAML 配置 -> 2. 加载 Excel 数据 -> 3. 列匹配筛选 -> 4. 模板渲染 -> 5. 输出 .v 文件

使用方式:
    python -m src.main                          # 使用默认配置
    python -m src.main -c config/custom.yaml    # 指定配置文件
    python -m src.main -l DEBUG                 # 指定日志级别
    python -m src.main -o output/my_module.v    # 指定输出文件
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from src.core.config import AppConfig, load_config
from src.core.excel_reader import ExcelReader
from src.core.logger import LogManager, get_logger
from src.core.matcher import ColumnMatcher
from src.core.template_engine import TemplateEngine

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="系统错误码 Verilog 代码自动生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m src.main
  python -m src.main -c config/power_match.yaml
  python -m src.main -l INFO
  python -m src.main -o output/power_err.v
        """,
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="YAML 配置文件路径 (默认: config/match_config.yaml)",
    )
    parser.add_argument(
        "-l", "--log-level",
        type=str,
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="日志级别 (默认: 使用配置文件中的设置)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="输出 Verilog 文件路径 (默认: 使用配置文件中的设置)",
    )
    parser.add_argument(
        "-e", "--excel",
        type=str,
        default=None,
        help="Excel 输入文件路径 (默认: 使用配置文件中的设置)",
    )
    return parser.parse_args()


def run(config: AppConfig) -> str:
    """
    执行主流程

    Args:
        config: 应用配置对象

    Returns:
        生成的 Verilog 代码字符串

    Raises:
        FileNotFoundError: 输入文件不存在时抛出
        ValueError: 配置错误或数据为空时抛出
        RuntimeError: 执行过程中发生未知错误时抛出
    """
    # ---- 步骤 1: 读取 Excel ----
    logger.info("=" * 60)
    logger.info("步骤 1/4: 读取 Excel 文件")
    logger.info("=" * 60)

    reader = ExcelReader(config.excel.file)
    df = reader.read_sheet(
        sheet_name=config.excel.sheet,
        merge_columns=config.excel.merge_columns,
    )

    if df.empty:
        raise ValueError(f"Sheet '{config.excel.sheet}' 中没有数据")

    records = reader.to_records(df)
    logger.info("Excel 读取完成，共 %d 行数据", len(records))

    # ---- 步骤 2: 列匹配 ----
    logger.info("=" * 60)
    logger.info("步骤 2/4: 执行列匹配筛选")
    logger.info("=" * 60)

    for col_cfg in config.match.columns:
        kw_info = col_cfg.keyword if col_cfg.keyword else "(任意非空)"
        logger.info("  匹配列: '%s' = '%s'", col_cfg.name, kw_info)

    matcher = ColumnMatcher(config.match)
    matched = matcher.match(records)

    if not matched:
        raise ValueError("没有匹配到任何数据行，请检查匹配配置")

    # ---- 步骤 3: 模板渲染 ----
    logger.info("=" * 60)
    logger.info("步骤 3/4: 渲染 Verilog 代码模板")
    logger.info("=" * 60)

    engine = TemplateEngine(config.template)
    extra_context = {
        "excel_file": config.excel.file,
        "sheet_name": config.excel.sheet,
        "generated_by": "sys_err_gen",
    }
    verilog_code = engine.render(matched, extra_context=extra_context)

    # ---- 步骤 4: 输出文件 ----
    logger.info("=" * 60)
    logger.info("步骤 4/4: 写入 Verilog 文件")
    logger.info("=" * 60)

    output_path = config.output.directory
    output_file = str(Path(output_path) / config.output.filename)
    Path(output_path).mkdir(parents=True, exist_ok=True)

    if Path(output_file).exists() and not config.output.overwrite:
        raise FileExistsError(
            f"输出文件已存在: {output_file} (设置 overwrite=true 可覆盖)"
        )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(verilog_code)

    logger.info("Verilog 代码已写入: %s", output_file)
    logger.info("文件大小: %d 字节", len(verilog_code))
    logger.info("=" * 60)
    logger.info("生成完毕！")
    logger.info("=" * 60)

    return verilog_code


def main() -> None:
    """程序入口"""
    args = parse_args()

    try:
        # 加载配置
        config = load_config(args.config)

        # 命令行参数覆盖配置文件
        if args.log_level:
            config.logging.level = args.log_level
        if args.output:
            config.output.filename = Path(args.output).name
            config.output.directory = str(Path(args.output).parent)
        if args.excel:
            config.excel.file = args.excel

        # 初始化日志系统
        LogManager.init(
            log_level=config.logging.level,
            log_dir=config.logging.dir,
            log_file=config.logging.file,
        )

        logger.info("sys_err_gen 启动")
        logger.debug("配置详情: %s", config.model_dump_json(indent=2))

        # 执行主流程
        run(config)

    except FileNotFoundError as e:
        logger.error("文件未找到: %s", e)
        sys.exit(1)
    except ValueError as e:
        logger.error("数据错误: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.exception("未知错误: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
