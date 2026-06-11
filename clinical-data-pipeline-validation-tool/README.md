# 🏥 临床数据 Pipeline 自动化校验工具

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## 📋 项目概述

本工具是**临床数据质量校验与格式转换的自动化解决方案**，专为临床试验数据管理、生物统计分析场景设计。它能够：

- ✅ **自动校验** CSV/Excel 格式临床数据的质量
- 🔄 **一键转换** 原始数据为 SDTM 标准格式
- 📊 **生成报告** 输出 Markdown 与 Excel 双格式校验报告
- ⚡ **批量处理** 同时校验/转换多个数据文件
- 🖥️ **双界面操作** 命令行 + Web 界面，满足不同用户需求

### 适用场景

- 临床试验数据管理中的日常数据质量检查
- 从原始采集数据到 SDTM 标准数据的格式转换
- 多个临床研究项目的批量数据清洗与校验
- 生物统计分析前的数据质量保障

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip 包管理器

### 安装步骤

```bash
# 1. 克隆项目
git clone <项目地址>
cd 临床数据校验工具

# 2. 安装依赖
pip install -r requirements.txt

# 3. （可选）配置环境变量
cp .env.example .env
```

### 验证安装

```bash
# 查看帮助
python -m src.cli.main --help

# 查看版本
python -m src.cli.main --version
```

预期输出：显示 validate、convert、batch、summary 四个命令的说明。

## 💻 使用指南

### 方式一：命令行工具（推荐）

#### 1️⃣ 数据校验

对临床数据文件执行全面的质量校验：

```bash
# 校验单个文件
python -m src.cli.main validate data/sample/sample_dm_data.csv

# 指定输出目录并生成详细日志
python -m src.cli.main validate data/sample/sample_dm_data.csv -o ./my_report -v
```

**校验内容：**
- 变量完整性 — 检查必填变量缺失、变量名不规范
- 数据类型校验 — 检查数值非法字符、日期格式错误、分类变量超范围
- 异常值校验 — 超出合理范围、日期逻辑矛盾、统计离群值
- SDTM/CDISC 合规 — USUBJID/STUDYID/DOMAIN 格式合规检查

**输出：** Markdown 报告（含问题详情与行号定位）+ Excel 报告（含问题列表工作表）

#### 2️⃣ 格式转换（→ SDTM）

将原始数据转换为 SDTM 标准格式：

```bash
# 基本转换
python -m src.cli.main convert data/sample/sample_dm_data.csv \
    --study-id STUDY001 --domain DM

# 指定输出格式
python -m src.cli.main convert data/sample/sample_ae_data.csv \
    --study-id STUDY001 --domain AE --output-format csv
```

**转换功能：**
- 自动映射原始变量名 → SDTM 标准变量名
- 自动生成 USUBJID、STUDYID、DOMAIN 等核心变量
- 日期格式统一为 `YYYY-MM-DD` 标准格式
- 分类变量值标准化（如 "男"→"M", "是"→"Y"）
- 数值精度统一
- 生成详细的转换日志（含每一步的修改记录）

#### 3️⃣ 批量处理

同时对多个数据文件执行校验或转换：

```bash
# 批量校验
python -m src.cli.main batch data/sample/ --mode validate

# 批量转换
python -m src.cli.main batch data/sample/ --mode convert \
    --study-id STUDY001 --domain DM

# 批量校验+转换
python -m src.cli.main batch data/sample/ --mode both \
    --study-id STUDY001
```

#### 4️⃣ 数据概要

快速查看数据集的基本信息：

```bash
python -m src.cli.main summary data/sample/sample_dm_data.csv
```

输出内容：行数、列数、每列数据类型、缺失值统计等。

### 方式二：Web 界面

启动 Streamlit Web 应用，无需命令行操作：

```bash
streamlit run web/app.py
```

浏览器打开 `http://localhost:8501`，即可使用图形界面完成以下操作：

1. **📤 数据上传与预览** — 上传 CSV/Excel 文件，查看数据预览与列信息
2. **🔍 数据质量校验** — 执行全维度校验，在线查看并下载报告
3. **🔄 格式转换** — 配置转换参数，一键转换为 SDTM 格式
4. **🧹 数据清洗** — 去重、去除空白、标记缺失值、统一大小写
5. **📊 统计分析** — 描述统计、分布分析、交叉表与卡方检验
6. **⚠️ 离群值检测** — IQR/Z-Score/MAD/综合投票法识别异常值

## 📁 项目结构

```
├── src/                          # 核心源码
│   ├── __init__.py               # 包入口与版本信息
│   ├── config/                   # 配置管理
│   │   ├── settings.py           # 全局配置类
│   │   └── rules/                # YAML 规则配置
│   │       ├── validation_rules.yaml  # 校验规则（可自定义）
│   │       └── mapping_rules.yaml     # 映射规则（可自定义）
│   ├── core/                     # 核心功能
│   │   ├── data_loader.py        # CSV/Excel 数据加载器
│   │   ├── data_writer.py        # 多格式数据输出器
│   │   └── batch_processor.py    # 批量并行处理器
│   ├── validation/               # 模块1: 校验
│   │   ├── validator.py          # 主校验器（协调所有检查）
│   │   ├── report.py             # 报告生成器（Markdown+Excel）
│   │   └── checks/               # 校验检查器
│   │       ├── base_check.py     # 基类与数据结构
│   │       ├── completeness_check.py  # 完整性检查
│   │       ├── type_check.py     # 类型格式检查
│   │       ├── range_check.py    # 异常值与逻辑检查
│   │       └── cdisc_check.py    # SDTM/CDISC 合规检查
│   ├── conversion/               # 模块2: 格式转换
│   │   ├── converter.py          # 主转换器
│   │   ├── variable_mapper.py    # 变量名映射
│   │   ├── variable_generator.py # 标准变量生成
│   │   └── conversion_log.py     # 转换日志
│   ├── scripts/                  # 模块3: 可复用脚本
│   │   ├── clean_data.py         # 数据清洗
│   │   ├── stats_checks.py       # 统计校验
│   │   └── outlier_detection.py  # 离群值检测
│   └── cli/                      # 模块4: 命令行
│       ├── main.py               # Click CLI 入口
│       └── __main__.py           # python -m 支持
├── web/                          # Streamlit Web 界面
│   └── app.py                    # Web 应用
├── data/                         # 数据文件
│   ├── sample/                   # 示例数据
│   │   ├── sample_dm_data.csv    # 人口学数据（含故意引入的问题）
│   │   ├── sample_ae_data.csv    # 不良事件数据
│   │   ├── sample_vs_data.csv    # 生命体征数据
│   │   ├── sample_clinical_data.csv    # 合并数据集
│   │   └── sample_clinical_data.xlsx   # Excel 示例数据
│   ├── output/                   # 输出目录
│   └── generate_sample_data.py   # 示例数据生成脚本
├── tests/                        # 测试
│   ├── test_data_loader.py
│   ├── test_validator.py
│   ├── test_converter.py
│   ├── test_scripts.py
│   └── run_verification.py       # 一键验证脚本
├── docs/                         # 文档
│   └── user_guide.md             # 用户指南
├── requirements.txt              # 依赖清单
├── .env.example                  # 环境变量模板
└── README.md                     # 本文件
```

## ⚙️ 自定义配置

### 校验规则自定义

编辑 `src/config/rules/validation_rules.yaml`，可自定义：

- **必填变量列表** — 根据项目需要增删必填字段
- **取值范围** — 设置各变量的合理范围（如 AGE: 0-120）
- **分类变量取值** — 定义允许的分类值列表
- **SDTM 标准配置** — 配置标准 Domain 列表、ID 格式规则
- **逻辑校验规则** — 添加自定义的业务逻辑约束

### 映射规则自定义

编辑 `src/config/rules/mapping_rules.yaml`，可自定义：

- **变量名映射** — 配置原始变量名到 SDTM 变量名的映射关系
- **值映射** — 配置分类变量值的标准化映射（如 "男"→"M"）
- **默认值** — 设置 STUDYID、DOMAIN 等变量的默认值

### 环境变量

编辑 `.env` 文件（基于 `.env.example` 复制）：

```
OUTPUT_DIR=./data/output
DATE_FORMAT=%Y-%m-%d
LOG_LEVEL=INFO
```

## 🧪 测试

```bash
# 方式一：pytest（需安装）
pytest tests/ -v

# 方式二：一键验证脚本（无需第三方库）
python tests/run_verification.py
```

## 📊 示例数据说明

示例数据包含 **故意引入的数据质量问题**，用于演示校验功能：

| 问题类型 | 示例 | 检测模块 |
|---------|------|---------|
| 缺失值 | AGE/SEX/RACE 缺失 | 完整性检查 |
| 日期格式错误 | 2024/01/15 而非 2024-01-15 | 类型检查 |
| 数值异常 | AGE=999, WEIGHT=550 | 范围检查 |
| 分类值异常 | SEX="Unknown" | 类型检查 |
| 日期逻辑矛盾 | RFSTDTC > RFENDTC | 逻辑检查 |
| USUBJID 格式错误 | "invalid-usubjid" | CDISC 合规检查 |
| 重复记录 | 完全重复的行 | 清洗脚本 |

## 🔧 技术栈

- **Python** — 核心开发语言
- **pandas** — 数据处理基础
- **openpyxl** — Excel 文件读写
- **click** — CLI 命令行框架
- **streamlit** — Web 交互界面
- **PyYAML** — 规则配置解析
- **python-dotenv** — 环境变量管理

## 📄 许可证

MIT License

Copyright (c) 2026 BeiGene AI Engineering Intern Project

---

*本工具为 BeiGene AI Engineering Intern 面试项目，用于临床研究数据质量的自动化管理。*
