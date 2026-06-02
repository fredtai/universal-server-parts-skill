"""
uspi/core/adapters/__init__.py

适配器包初始化 / Adapter package initialization.

导出 BaseAdapter 基类及数据模型，供各数据源适配器继承使用 / Exports BaseAdapter
and data models for data source adapters to inherit. Also exports and registers
the three public market adapters (eBay, Amazon, AliExpress).
"""

from uspi.core.adapters.base import BaseAdapter, CATEGORIES, PriceSource, ServerPart
from uspi.core.adapters.ebay_public_adapter import EbayPublicAdapter
from uspi.core.adapters.amazon_public_adapter import AmazonPublicAdapter
from uspi.core.adapters.aliexpress_adapter import AliexpressAdapter

# 适配器注册表 / Adapter registry
ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "ebay": EbayPublicAdapter,
    "amazon": AmazonPublicAdapter,
    "aliexpress": AliexpressAdapter,
}

__all__ = [
    "BaseAdapter",
    "CATEGORIES",
    "PriceSource",
    "ServerPart",
    "EbayPublicAdapter",
    "AmazonPublicAdapter",
    "AliexpressAdapter",
    "ADAPTER_REGISTRY",
]
