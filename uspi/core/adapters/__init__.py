"""
uspi/core/adapters/__init__.py

适配器包初始化 / Adapter package initialization.

导出 BaseAdapter 基类、数据模型以及所有 OEM/ODM 适配器 / Exports BaseAdapter,
data models, and all OEM/ODM adapters.
"""

from uspi.core.adapters.base import BaseAdapter, CATEGORIES, PriceSource, ServerPart
from uspi.core.adapters.dell_adapter import DellAdapter
from uspi.core.adapters.hp_adapter import HpAdapter
from uspi.core.adapters.lenovo_adapter import LenovoAdapter
from uspi.core.adapters.supermicro_adapter import SupermicroAdapter

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
]

# 适配器注册表 / Adapter registry
# 完整注册表将在所有适配器合并后统一维护
# Full registry will be maintained after all adapters are merged
ADAPTER_REGISTRY: dict[str, type] = {
    "dell": DellAdapter,
    "hp": HpAdapter,
    "lenovo": LenovoAdapter,
    "supermicro": SupermicroAdapter,
}
