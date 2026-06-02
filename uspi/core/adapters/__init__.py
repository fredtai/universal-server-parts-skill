"""
uspi/core/adapters/__init__.py

适配器包初始化 / Adapter package initialization.

导出 BaseAdapter 基类及数据模型，注册所有 ODM 适配器到 ADAPTER_REGISTRY。
Exports BaseAdapter and data models, registers all ODM adapters to
ADAPTER_REGISTRY.
"""

from uspi.core.adapters.base import BaseAdapter, CATEGORIES, PriceSource, ServerPart

# ODM 适配器导入 / ODM adapter imports
from uspi.core.adapters.foxconn_adapter import FoxconnAdapter
from uspi.core.adapters.quanta_adapter import QuantaAdapter
from uspi.core.adapters.wistron_adapter import WistronAdapter
from uspi.core.adapters.compal_adapter import CompalAdapter
from uspi.core.adapters.pegatron_adapter import PegatronAdapter
from uspi.core.adapters.inventec_adapter import InventecAdapter
from uspi.core.adapters.flex_adapter import FlexAdapter
from uspi.core.adapters.jabil_adapter import JabilAdapter

__all__ = [
    "BaseAdapter",
    "CATEGORIES",
    "PriceSource",
    "ServerPart",
    "FoxconnAdapter",
    "QuantaAdapter",
    "WistronAdapter",
    "CompalAdapter",
    "PegatronAdapter",
    "InventecAdapter",
    "FlexAdapter",
    "JabilAdapter",
    "ADAPTER_REGISTRY",
]

# 适配器注册表 / Adapter registry
# 所有数据源适配器必须在此注册以便统一调度
ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "foxconn": FoxconnAdapter,
    "quanta": QuantaAdapter,
    "wistron": WistronAdapter,
    "compal": CompalAdapter,
    "pegatron": PegatronAdapter,
    "inventec": InventecAdapter,
    "flex": FlexAdapter,
    "jabil": JabilAdapter,
}
