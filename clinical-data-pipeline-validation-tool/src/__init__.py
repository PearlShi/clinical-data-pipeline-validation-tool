"""
临床数据 Pipeline 自动化校验工具
================================
用于临床试验数据的质量校验、SDTM 格式转换与批量处理。

本工具遵循 CDISC 标准，支持 CSV/Excel 格式数据的：
  - 数据格式校验（完整性、类型、异常值、CDISC 合规性）
  - 自动化格式转换（原始数据 → SDTM 标准格式）
  - 可复用清洗与统计校验脚本
  - 命令行工具与 Web 界面双模式操作
"""

__version__ = "1.0.0"
__author__ = "Personal Technical Demo Project"
