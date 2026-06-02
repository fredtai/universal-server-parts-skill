"""
USPI Core 模块 - 零件号识别与数据标准化
USPI Core Module - Part Number Recognition and Data Standardization

本模块提供服务器零件号的 OEM/ODM 识别、分类推断、单位转换、
数据抓取、适配器基类以及导出功能。

This module provides server part number OEM/ODM recognition, category
inference, unit conversion, data fetching, adapter base classes, and
export functionality.
"""

from uspi.core.parser import PartParser, ParseResult

__all__ = [
    "PartParser",   # 零件号解析器 / Part number parser
    "ParseResult",  # 解析结果数据类 / Parse result dataclass
]
