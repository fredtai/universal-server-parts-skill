"""
uspi/core/adapters/__init__.py

适配器包初始化 / Adapter package initialization.
导出 BaseAdapter 基类、数据模型以及全部 15 个适配器。
Exports BaseAdapter, data models, and all 15 OEM/ODM/Market adapters.
"""

# 基类和数据模型 / Base classes and data models
from uspi.core.adapters.base import BaseAdapter, CATEGORIES, PriceSource, ServerPart

# OEM 适配器 / OEM adapters
from uspi.core.adapters.dell_adapter import DellAdapter
from uspi.core.adapters.hp_adapter import HpAdapter
from uspi.core.adapters.lenovo_adapter import LenovoAdapter
from uspi.core.adapters.supermicro_adapter import SupermicroAdapter

# ODM 适配器 / ODM adapters
from uspi.core.adapters.foxconn_adapter import FoxconnAdapter
from uspi.core.adapters.quanta_adapter import QuantaAdapter
from uspi.core.adapters.wistron_adapter import WistronAdapter
from uspi.core.adapters.compal_adapter import CompalAdapter
from uspi.core.adapters.pegatron_adapter import PegatronAdapter
from uspi.core.adapters.inventec_adapter import InventecAdapter
from uspi.core.adapters.flex_adapter import FlexAdapter
from uspi.core.adapters.jabil_adapter import JabilAdapter

# 公开市场适配器 / Market adapters
from uspi.core.adapters.ebay_public_adapter import EbayPublicAdapter
from uspi.core.adapters.amazon_public_adapter import AmazonPublicAdapter
from uspi.core.adapters.aliexpress_adapter import AliexpressAdapter

__all__ = [
    # 基类和数据模型 / Base classes and data models
    "BaseAdapter",
    "CATEGORIES",
    "PriceSource",
    "ServerPart",
    # OEM 适配器 / OEM adapters
    "DellAdapter",
    "HpAdapter",
    "LenovoAdapter",
    "SupermicroAdapter",
    # ODM 适配器 / ODM adapters
    "FoxconnAdapter",
    "QuantaAdapter",
    "WistronAdapter",
    "CompalAdapter",
    "PegatronAdapter",
    "InventecAdapter",
    "FlexAdapter",
    "JabilAdapter",
    # 公开市场适配器 / Market adapters
    "EbayPublicAdapter",
    "AmazonPublicAdapter",
    "AliexpressAdapter",
    # 注册表 / Registry
    "ADAPTER_REGISTRY",
]

# 适配器注册表 / Adapter registry
# 统一调度入口 / Unified dispatch entry
ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    # OEM
    "dell": DellAdapter,
    "hp": HpAdapter,
    "lenovo": LenovoAdapter,
    "supermicro": SupermicroAdapter,
    # ODM
    "foxconn": FoxconnAdapter,
    "quanta": QuantaAdapter,
    "wistron": WistronAdapter,
    "compal": CompalAdapter,
    "pegatron": PegatronAdapter,
    "inventec": InventecAdapter,
    "flex": FlexAdapter,
    "jabil": JabilAdapter,
    # Market
    "ebay": EbayPublicAdapter,
    "amazon": AmazonPublicAdapter,
    "aliexpress": AliexpressAdapter,
}
