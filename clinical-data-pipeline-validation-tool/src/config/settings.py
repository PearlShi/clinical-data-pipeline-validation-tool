"""
配置管理模块
===========
负责加载环境变量、校验规则、映射规则等配置信息。
支持 .env 文件和 YAML 配置文件。
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv


# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 加载 .env 文件
load_dotenv(PROJECT_ROOT / ".env")


def get_env(key: str, default: Any = None) -> Any:
    """获取环境变量值"""
    return os.getenv(key, default)


def get_path(key: str, default: str = "") -> Path:
    """获取路径类型的环境变量"""
    path_str = get_env(key, default)
    if not path_str:
        return PROJECT_ROOT / "data" / "output"
    path = Path(path_str)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


class Config:
    """全局配置类，管理所有配置项"""

    def __init__(self):
        # 路径配置
        self.output_dir = get_path("OUTPUT_DIR", "./data/output")
        self.report_dir = get_path("REPORT_DIR", "./data/output/reports")
        self.log_dir = get_path("LOG_DIR", "./data/output/logs")

        # 规则配置路径
        self.validation_rules_path = get_env(
            "VALIDATION_RULES",
            str(PROJECT_ROOT / "src" / "config" / "rules" / "validation_rules.yaml")
        )
        self.mapping_rules_path = get_env(
            "MAPPING_RULES",
            str(PROJECT_ROOT / "src" / "config" / "rules" / "mapping_rules.yaml")
        )

        # 日期格式
        self.date_format = get_env("DATE_FORMAT", "%Y-%m-%d")

        # 日志级别
        self.log_level = get_env("LOG_LEVEL", "INFO")

        # 加载规则
        self._validation_rules: Dict = {}
        self._mapping_rules: Dict = {}
        self._load_rules()

    def _load_rules(self) -> None:
        """加载 YAML 规则配置文件"""
        try:
            v_path = Path(self.validation_rules_path)
            if v_path.exists():
                with open(v_path, "r", encoding="utf-8") as f:
                    self._validation_rules = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"警告: 无法加载校验规则文件 {self.validation_rules_path}: {e}")
            self._validation_rules = {}

        try:
            m_path = Path(self.mapping_rules_path)
            if m_path.exists():
                with open(m_path, "r", encoding="utf-8") as f:
                    self._mapping_rules = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"警告: 无法加载映射规则文件 {self.mapping_rules_path}: {e}")
            self._mapping_rules = {}

    @property
    def validation_rules(self) -> Dict:
        """获取校验规则配置"""
        return self._validation_rules

    @property
    def mapping_rules(self) -> Dict:
        """获取映射规则配置"""
        return self._mapping_rules

    def get_required_variables(self) -> List[str]:
        """获取必填变量列表"""
        rules = self._validation_rules.get("required_variables", {})
        return rules.get("variables", ["USUBJID", "STUDYID", "DOMAIN"])

    def get_sdtm_domains(self) -> List[str]:
        """获取 SDTM 标准 domain 列表"""
        return self._validation_rules.get(
            "sdtm", {}
        ).get("standard_domains", [
            "DM", "AE", "VS", "LB", "EX", "MH", "CM", "DS", "SC", "SS"
        ])

    def get_date_variables(self) -> List[str]:
        """获取日期类型变量列表"""
        return self._validation_rules.get(
            "date_checks", {}
        ).get("variables", ["RFSTDTC", "RFENDTC", "AESTDTC", "AEENDTC"])

    def get_value_ranges(self) -> Dict[str, Dict]:
        """获取变量取值范围配置"""
        return self._validation_rules.get("value_ranges", {})

    def get_category_mappings(self) -> Dict[str, Dict]:
        """获取分类变量映射表"""
        return self._validation_rules.get("category_mappings", {})

    def get_mapping_config(self) -> Dict:
        """获取变量映射配置"""
        return self._mapping_rules.get("mapping", {})

    def get_domain_prefixes(self) -> Dict[str, str]:
        """获取 DOMAIN 前缀映射"""
        return self._mapping_rules.get("domain_prefixes", {})

    def get_variable_defaults(self) -> Dict[str, Any]:
        """获取变量默认值配置"""
        return self._mapping_rules.get("variable_defaults", {})

    def ensure_dirs(self) -> None:
        """确保输出目录存在"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


# 全局配置实例
config = Config()
