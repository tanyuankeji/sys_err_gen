# sys_err_gen - 系统错误码 Verilog 代码自动生成工具

## 概述

`sys_err_gen` 是一个 Python 命令行工具，根据 Excel 错误表的输入需求、YAML 匹配配置和 Jinja2 代码模板，自动生成 Verilog RTL 代码。适用于 IC 设计中系统级错误监控模块的批量生成。

### 工作流程

```
Excel 错误表 ──> 列匹配筛选 ──> Jinja2 模板渲染 ──> Verilog 代码文件
  (.xls/.xlsx)     (YAML 配置)      (.j2 模板)           (.v 输出)
```

---

## 项目结构

```
sys_err_gen/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # 配置加载（YAML + .env，pydantic 校验）
│   │   ├── excel_reader.py       # Excel 读取 + 合并单元格 forward-fill 处理
│   │   ├── logger.py             # 多级别日志系统（控制台 + 文件轮转）
│   │   ├── matcher.py            # 列匹配引擎（中文列名，AND 逻辑）
│   │   └── template_engine.py    # Jinja2 模板引擎（含 Verilog 自定义滤波器）
│   ├── __init__.py
│   └── main.py                   # 主入口，4 步编排流水线
├── config/
│   ├── match_config.yaml         # 默认匹配配置（供电类错误）
│   └── match_config_bg.yaml      # 示例配置（BG 类错误）
├── templates/
│   └── error_handler.j2          # Verilog 错误监控模块模板
├── output/                       # 生成代码输出目录
├── logs/                         # 日志输出目录
├── .env                          # 环境变量
├── requirements.txt              # Python 依赖
└── README.md                     # 本文档
```

---

## 快速开始

### 环境要求

- Python 3.10+
- 依赖包见 `requirements.txt`

### 安装

```bash
pip install -r requirements.txt
```

### 核心特性

| 特性| 实现方式 |
|-------|----------|
| Excel 解析|ExcelReader 读取指定 Sheet，merge_columns 配置对合并单元格执行 ffill()|
|列匹配|ColumnMatcher 按 YAML 配置的列名(中文) + 关键词 AND 匹配，空关键词匹配任意非空值|
|模板渲染|	Jinja2 模板引擎，注册了 upper/lower/snake/vcomment 等自定义 Verilog 命名滤波器|
|Verilog 输出|	生成完整 RTL 模块，含错误标志检测、优先级编码器、故障计数器
|多级日志|	DEBUG/INFO/WARNING/ERROR/CRITICAL 五级，同时输出控制台 + 按 10MB 轮转的文件|

### 基本用法

```bash
# 使用默认配置（匹配 Excel 中"类型"列为"供电"的行）
python -m src.main

# 指定配置文件
python -m src.main -c config/match_config_bg.yaml

# 指定日志级别
python -m src.main -l DEBUG

# 指定输出文件路径
python -m src.main -o output/my_error_module.v

# 同时使用多个选项
python -m src.main -c config/custom.yaml -l WARNING -o output/custom.v
```


### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-c, --config` | YAML 配置文件路径 | `config/match_config.yaml` |
| `-l, --log-level` | 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL） | 配置文件中的设置 |
| `-o, --output` | 输出 Verilog 文件路径 | 配置文件中的设置 |
| `-e, --excel` | Excel 输入文件路径 | 配置文件中的设置 |

---

## 配置说明

配置文件使用 YAML 格式，分为五个配置段，完整示例：

```yaml
# ===== Excel 输入配置 =====
excel:
  file: "sys_err错误表.xls"       # Excel 文件路径（支持 .xls / .xlsx）
  sheet: "错误动作"                # 目标 Sheet 名称
  merge_columns:                  # 存在合并单元格的列，执行向前填充（ffill）
    - "类型"
    - "模块"

# ===== 列匹配规则 =====
match:
  columns:                        # 匹配列列表，所有条件为 AND 关系
    - name: "类型"                 # 列名（必须与 Excel 中的中文列名一致）
      keyword: "供电"              # 匹配关键词，空字符串 "" 表示匹配任意非空值

# ===== 模板配置 =====
template:
  file: "templates/error_handler.j2"  # Jinja2 模板文件路径
  autoescape: false                   # Verilog 代码不需要 HTML 转义

# ===== 输出配置 =====
output:
  directory: "output"             # 输出目录
  filename: "sys_err_gen.v"       # 输出文件名
  overwrite: true                 # 是否覆盖已有文件

# ===== 日志配置 =====
logging:
  level: "DEBUG"                  # 日志级别
  dir: "logs"                     # 日志目录
  file: null                      # null 表示按日期自动命名
```

### 匹配规则详解

- **关键词匹配**：`keyword` 非空时进行精确匹配（`str.strip()` 比较）
- **通配匹配**：`keyword` 为空字符串 `""` 时，匹配该列值为任意非空内容的行
- **AND 逻辑**：`columns` 列表中所有列条件必须同时满足
- **中文列名**：通过 Excel 中的中文列名进行定位，不依赖列顺序

---

## Excel 数据要求

### 支持格式

- `.xls`（Excel 97-2003）
- `.xlsx`（Excel 2007+）

### 合并单元格处理

工具不会直接读取 Excel 的合并单元格元数据，而是通过配置 `merge_columns` 指定哪些列可能存在合并单元格，然后对这些列的 `NaN` 值执行 **向前填充（forward fill）**。

**示例**：下表中"类型"和"模块"列的合并单元格经过 ffill 后，每一行都会获得其所属分组的值。

| 类型 | 模块 | 数字信号 | 错误 |
|------|------|----------|------|
| 供电 | VSupr | vsup0_ov | 错误10 |
| (合并) | (合并) | vsup1_ov | 错误11 |
| (合并) | Vsense | vsense_ov | 错误15 |

处理后：

| 类型 | 模块 | 数字信号 | 错误 |
|------|------|----------|------|
| 供电 | VSupr | vsup0_ov | 错误10 |
| 供电 | VSupr | vsup1_ov | 错误11 |
| 供电 | Vsense | vsense_ov | 错误15 |

---

## 模板说明

模板使用 [Jinja2](https://jinja.palletsprojects.com/) 语法，内置以下变量和滤波器：

### 模板变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `errors` | `List[Dict]` | 匹配到的数据行列表，每行是一个字典，键为中文列名 |
| `error_count` | `int` | 匹配到的数据行数量 |
| `excel_file` | `str` | Excel 文件路径 |
| `sheet_name` | `str` | Sheet 名称 |
| `generated_by` | `str` | 生成工具标识 |

### Jinja2 循环变量

在 `{% for err in errors %}` 循环中，可使用：

| 变量 | 说明 |
|------|------|
| `loop.index` | 当前迭代索引（从 1 开始） |
| `loop.index0` | 当前迭代索引（从 0 开始） |
| `loop.first` | 是否为第一次迭代 |
| `loop.last` | 是否为最后一次迭代 |

### 自定义滤波器

| 滤波器 | 示例 | 输出 |
|--------|------|------|
| `upper` | `{{ "signal" \| upper }}` | `SIGNAL` |
| `lower` | `{{ "SIGNAL" \| lower }}` | `signal` |
| `snake` | `{{ "My-Sig!" \| snake }}` | `my_sig` |
| `strip_us` | `{{ "_sig_" \| strip_us }}` | `sig` |
| `vcomment` | `{{ text \| vcomment }}` | `// line1\n// line2` |

### 自定义模板

创建新的 `.j2` 模板文件，在配置中指定路径即可：

```verilog
// 模板中使用数据
module my_module (
{% for err in errors %}
    input  wire  {{ err["数字信号"] }},  // {{ err["模块"] }} - {{ err["错误"] }}
{% endfor %}
    output wire  err_detected
);
    // error codes
{% for err in errors %}
    localparam ERR_{{ err["数字信号"] | upper }} = 8'h{{ "%02X" % loop.index }};
{% endfor %}
endmodule
```

---

## 日志系统

工具提供五级日志，同时输出到控制台和文件：

| 级别 | 说明 | 使用场景 |
|------|------|----------|
| `DEBUG` | 详细调试信息（行级匹配日志等） | 开发调试、问题排查 |
| `INFO` | 流程步骤信息 | 正常使用 |
| `WARNING` | 警告信息（无匹配行等） | 关注潜在问题 |
| `ERROR` | 错误信息 | 定位失败原因 |
| `CRITICAL` | 严重错误 | 系统级故障 |

日志文件存放在 `logs/` 目录，按日期自动命名（如 `sys_err_gen_20260609.log`），单个文件最大 10MB，保留 5 个历史备份。

---

## 生成的 Verilog 模块说明

默认模板生成的 Verilog 模块 `sys_err_gen` 包含以下功能：

| 功能模块 | 说明 |
|----------|------|
| **输入信号端口** | 自动生成所有匹配错误对应的监控信号输入端口 |
| **错误码定义** | 每个错误信号分配唯一的 localparam 错误码 |
| **错误标志寄存器** | 时序逻辑，检测信号异常时置位，支持 err_rstb 复位 |
| **优先级编码器** | 组合逻辑，按索引优先级输出最高优先级的错误码 |
| **故障计数器** | FLT_ERR_CNT 不为空的错误触发时递增计数器 |

### 代码规范

生成的 Verilog 代码遵循以下规范：

- 模块名/信号名使用小写 + 下划线（snake_case）
- 参数名全大写 + 下划线
- 寄存器以 `_reg` 结尾，组合逻辑以 `_next` 结尾
- 统一上升沿触发，低电平异步复位
- 关键参数使用 parameter 定义（可配置）
- 端口按功能分组，每组带注释说明

---

## 常见问题

### Q: 匹配不到任何行怎么办？

检查以下几点：
1. 配置的 `sheet` 名称是否与 Excel 中的 Sheet 名称完全一致
2. `match.columns[].name` 列名是否与 Excel 中的列名完全一致（包括空格）
3. `keyword` 是否与实际值精确匹配（区分大小写）
4. 如果 Excel 有合并单元格，是否在 `merge_columns` 中配置了对应的列

### Q: 如何匹配多个 Sheet？

建议为每个 Sheet 创建独立的配置文件，多次运行工具。

### Q: 如何在模板中使用条件判断？

Jinja2 支持标准的 `{% if %} / {% elif %} / {% else %} / {% endif %}` 语法：

```jinja2
{% for err in errors %}
{% if err["FLT_ERR_CNT"] and err["FLT_ERR_CNT"] != "" %}
    // handle counter for {{ err["数字信号"] }}
{% endif %}
{% endfor %}
```

### Q: 日志文件太大怎么办？

日志使用 `RotatingFileHandler`，单个文件最大 10MB，自动轮转。可在 `src/core/logger.py` 中调整 `maxBytes` 和 `backupCount` 参数。

---

## 扩展指南

### 添加新的匹配逻辑

修改 `src/core/matcher.py` 中的 `_match_row` 方法，可扩展为正则匹配、模糊匹配等：

```python
def _match_row(self, record: Dict[str, Any]) -> bool:
    for col_cfg in self.config.columns:
        cell_value = str(record.get(col_cfg.name, ""))
        if col_cfg.keyword:
            # 扩展：支持正则
            # import re
            # if not re.search(col_cfg.keyword, cell_value):
            #     return False
            if cell_value.strip() != col_cfg.keyword.strip():
                return False
    return True
```

### 添加自定义 Jinja2 滤波器

在 `src/core/template_engine.py` 的 `_register_filters` 方法中注册：

```python
def verilog_bus(width: int) -> str:
    return f"[{width}-1:0]"

self.env.filters["bus"] = verilog_bus
```

模板中使用：`{{ 8 | bus }}` → `[8-1:0]`

---

## 依赖版本

| 包名 | 最低版本 | 说明 |
|------|----------|------|
| pandas | 1.5.0 | Excel 数据读取 |
| openpyxl | 3.0.0 | .xlsx 格式支持 |
| xlrd | 2.0.0 | .xls 格式支持 |
| pyyaml | 6.0 | YAML 配置文件解析 |
| jinja2 | 3.0.0 | 代码模板渲染 |
| pydantic | 2.0.0 | 配置模型校验 |
| pydantic-settings | 2.0.0 | .env 环境变量加载 |

---

## 许可

内部工具，按需使用。
