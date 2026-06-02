"""
uspi/core/adapters/__init__.py

适配器包初始化 / Adapter package initialization.

导出 BaseAdapter 基类及数据模型，供各数据源适配器继承使用 / Exports BaseAdapter
and data models for data source adapters to inherit.
"""

from uspi.core.adapters.base import BaseAdapter, CATEGORIES, PriceSource, ServerPart

__all__ = [
    "BaseAdapter",
    "CATEGORIES",
    "PriceSource",
    "ServerPart",
]
