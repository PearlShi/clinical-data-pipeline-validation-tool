# 用户指南

## 快速导航

- [安装与配置](#安装与配置)
- [命令行使用详解](#命令行使用详解)
- [Web 界面使用](#web-界面使用)
- [数据类型说明](#数据类型说明)
- [规则配置指南](#规则配置指南)
- [常见问题](#常见问题)

---

## 安装与配置

### 第一步：安装 Python 依赖

```bash
pip install -r requirements.txt
```

核心依赖包括：
- `pandas>=2.0.0` — 数据处理核心
- `openpyxl>=3.1.0` — Excel 读写
- `click>=8.1.0` — 命令行框架
- `streamlit>=1.28.0` — Web 界面
- `pyyaml>=6.0` — YAML 配置解析

### 第二步：配置环境变量（可选）

```bash
cp .env.example .env
```

编辑 `.env` 文件可修改：
- `OUTPUT_DIR` — 输出文件目录
- `REPORT_DIR` — 报告文件目录
- `LOG_LEVEL` — 日志级别（DEBUG/INFO/WARNING/ERROR）
- `DATE_FORMAT` — 标准日期格式

### 第三步：生成示例数据

```bash
python data/generate_sample_data.py
```

生成的数据文件位于 `data/sample/` 目录下，包含：人口学数据（DM）、不良事件数据（AE）、生命体征数据（VS）。

---

## 命令行使用详解

### `validate` — 数据质量校验

```bash
python -m src.cli.main validate [OPTIONS] INPUT_FILE

# 示例
python -m src.cli.main validate data/sample/sample_dm_data.csv
python -m src.cli.main validate data/sample/sample_dm_data.csv -o ./reports -v
python -m src.cli.main validate data/sample/sample_dm_data.csv --md-only
```

**参数说明：**
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `INPUT_FILE` | 输入文件路径（CSV/Excel） | 必填 |
| `-o, --output-dir` | 输出目录 | data/output/reports |
| `-r, --rules` | 自定义校验规则文件 | 使用默认规则 |
| `--report-name` | 报告文件名 | validation_report |
| `--md-only` | 仅生成 Markdown 报告 | 生成 MD+Excel |
| `-v, --verbose` | 显示详细日志 | 不显示 |

**输出文件：**
- `validation_report.md` — Markdown 格式报告（含问题详情与行号定位）
- `validation_report.xlsx` — Excel 格式报告（含多个工作表）

### `convert` — 格式转换

```bash
python -m src.cli.main convert [OPTIONS] INPUT_FILE

# 示例
python -m src.cli.main convert data/sample/sample_dm_data.csv \
    --study-id BEIGENE-001 --domain DM
python -m src.cli.main convert data/sample/sample_ae_data.csv \
    --study-id BEIGENE-001 --domain AE --output-format csv
```

**参数说明：**
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `INPUT_FILE` | 输入文件路径 | 必填 |
| `--study-id` | 研究编号 | 从配置读取 |
| `--domain` | 目标数据域 | 从配置读取 |
| `--output-format` | 输出格式（csv/xlsx） | xlsx |
| `--no-date-norm` | 跳过日期标准化 | 标准化 |
| `--no-category-norm` | 跳过分类变量标准化 | 标准化 |
| `-o, --output-dir` | 输出目录 | data/output |

**转换流程：**
1. 加载原始数据
2. 检测变量映射（自动匹配原始变量→SDTM 标准变量）
3. 应用变量名映射
4. 生成 USUBJID/STUDYID/DOMAIN 等标准变量
5. 统一日期格式
6. 标准化分类变量值
7. 统一数值精度
8. 输出 SDTM 格式数据 + 转换日志

### `batch` — 批量处理

```bash
python -m src.cli.main batch [OPTIONS] INPUT_DIR

# 批量校验
python -m src.cli.main batch data/sample/ --mode validate

# 批量转换
python -m src.cli.main batch data/sample/ --mode convert \
    --study-id BEIGENE-001 --domain DM

# 批量校验+转换
python -m src.cli.main batch data/sample/ --mode both
```

### `summary` — 数据概要

```bash
python -m src.cli.main summary INPUT_FILE

# 示例
python -m src.cli.main summary data/sample/sample_dm_data.csv
```

---

## Web 界面使用

### 启动方式

```bash
streamlit run web/app.py
```

浏览器访问 `http://localhost:8501`

### 功能页面

1. **📤 数据上传与预览**
   - 上传 CSV/Excel 数据文件
   - 查看数据预览表（前 100 行）
   - 查看列信息（类型、缺失率、唯一值数）
   - 查看数值列描述统计

2. **🔍 数据质量校验**
   - 一键执行全维度校验
   - 查看每项检查的详细结果
   - 按严重级别筛选问题
   - 下载 Markdown 或 Excel 校验报告

3. **🔄 格式转换（→SDTM）**
   - 设置转换参数（研究编号、数据域）
   - 配置转换选项（日期标准化、分类变量标准化）
   - 查看转换日志
   - 下载转换后的 SDTM 格式数据

4. **🧹 数据清洗**
   - 选择清洗操作（去重、去空白、标记缺失值、统一大小写）
   - 选择缺失值填充策略
   - 查看清洗前后的数据对比
   - 下载清洗后数据

5. **📊 统计分析**
   - 自动生成描述性统计
   - 数值列分布分析（含正态性检验）
   - 分类列频数统计
   - 交叉表与卡方检验

6. **⚠️ 离群值检测**
   - 选择检测方法（IQR/Z-Score/MAD/综合投票）
   - 选择检测列和分组变量
   - 查看离群值汇总与详细列表
   - 标记异常值严重程度

---

## 数据类型说明

### 支持的输入格式

| 格式 | 说明 | 限制 |
|------|------|------|
| CSV | 逗号分隔值 | 自动检测编码（UTF-8/GBK/GB2312） |
| XLSX | Excel Open XML | 支持多工作表，默认读取第一个 |
| XLS | Excel 97-2003 | 兼容旧版格式 |

### 常用 SDTM 变量

| 变量名 | 说明 | 必填 | 格式要求 |
|--------|------|------|----------|
| STUDYID | 研究编号 | ✅ | 大写字母数字组合 |
| DOMAIN | 数据域标识 | ✅ | 2 字母标准 Domain 代码 |
| USUBJID | 受试者唯一标识 | ✅ | STUDYID-SITEID-SUBJID |
| SUBJID | 受试者编号 | ✅ | 数字或字母数字 |
| SITEID | 研究中心编号 | ✅ | 字母数字组合 |
| RFSTDTC | 首次给药/研究日期 | ✅ | ISO 8601 (YYYY-MM-DD) |
| RFENDTC | 末次给药/研究日期 | ✅ | ISO 8601 (YYYY-MM-DD) |
| AGE | 年龄 | 推荐 | 数值，0-120 |
| SEX | 性别 | 推荐 | M/F |
| RACE | 种族 | 推荐 | 标准分类值 |

---

## 规则配置指南

### 校验规则（validation_rules.yaml）

```yaml
# 1. 自定义必填变量
required_variables:
  variables:
    - USUBJID
    - STUDYID
    - SITEID
    # 在此添加项目特有变量

# 2. 自定义取值范围
value_ranges:
  AGE:
    min: 0
    max: 120
  # 添加新变量
  DURATION:
    min: 0
    max: 365

# 3. 自定义分类变量
category_mappings:
  NEW_VARIABLE:
    valid_values:
      - "VALUE1"
      - "VALUE2"
```

### 映射规则（mapping_rules.yaml）

```yaml
# 1. 添加变量映射
mapping:
  direct_mappings:
    SOURCE_VAR: "SDTM_VAR"
    # 在此添加新的映射

# 2. 添加值映射
value_mappings:
  NEW_VAR:
    "原始值": "标准值"
```

---

## 常见问题

### Q: 输出报告中的行号对应 Excel 中的行号吗？
A: 是的。Markdown 报告的"行号"列显示的是 Excel 行号（即 DataFrame 行号 + 2，因为第 1 行为表头，DataFrame 行号从 0 开始）。

### Q: 如何处理大数据文件？
A: 本工具默认一次性加载全部数据到内存。对于超大文件（> 100MB），建议先分割为多个小文件，使用 batch 模式批量处理。

### Q: 如何添加新的校验规则？
A: 两种方式：
1. **配置式** — 编辑 `validation_rules.yaml` 添加取值范围、分类值等
2. **编程式** — 继承 `BaseCheck` 类实现自定义检查器，注册到 `Validator`

### Q: 转换后数据中的 USUBJID 格式是什么？
A: 默认格式为 `STUDYID-SITEID-SUBJID`。例如 `BEIGENE001-SITE01-0001`。

### Q: 如何指定 CSV 文件的编码？
A: DataLoader 自动尝试 UTF-8 → GBK → GB2312 → latin-1。也可在 `.env` 中设置默认编码。

### Q: Windows 下显示乱码怎么办？
A: 执行前设置环境变量 `SET PYTHONIOENCODING=utf-8`。

---

*最后更新: 2026-06-11*
