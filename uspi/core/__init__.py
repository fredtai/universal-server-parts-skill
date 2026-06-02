"""
USPI Core Package — 核心包
USPI Core Module - Part Number Recognition and Data Standardization

本模块提供服务器零件号的 OEM/ODM 识别、分类推断、单位转换、
数据抓取、适配器基类以及导出功能。

This module provides server part number OEM/ODM recognition, category
inference, unit conversion, data fetching, adapter base classes, and
export functionality.
"""

from uspi.core.unit_converter import UnitConverter
from uspi.core.parser import PartParser, ParseResult
from uspi.core.normalizer import Normalizer
from uspi.core.comparator import Comparator
from uspi.core.exporter import Exporter, COMPACT_FIELDS, STANDARD_FIELDS, FULL_FIELDS

__all__ = [
    "UnitConverter",      # 单位转换引擎 / Unit conversion engine
    "PartParser",         # 零件号解析器 / Part number parser
    "ParseResult",        # 解析结果数据类 / Parse result dataclass
    "Normalizer",         # 数据归一化器 / Data normalizer
    "Comparator",         # 零件对比引擎 / Part comparison engine
    "Exporter",           # 多格式导出引擎 / Multi-format export engine
    "COMPACT_FIELDS",     # Token 最小字段集 / Token-minimal field set
    "STANDARD_FIELDS",    # 标准字段集 / Standard field set
    "FULL_FIELDS",        # 完整字段集 / Full field set
]
