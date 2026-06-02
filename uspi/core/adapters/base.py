"""
uspi/core/adapters/base.py

适配器抽象基类 / Adapter Abstract Base Class

提供统一的数据模型 (ServerPart, PriceSource) 和适配器接口 / Provides unified data
models and adapter interface.

所有数据源适配器必须继承 BaseAdapter 并实现抽象方法 / All data source adapters
must inherit from BaseAdapter and implement abstract methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 数据模型 / Data Models
# ---------------------------------------------------------------------------


@dataclass
class PriceSource:
    """价格来源数据模型 / Price source data model.

    Attributes:
        source_name: 来源名称 (英文) / Source name in English
        source_name_zh: 中文来源名 / Source name in Chinese
        price_usd: 美元价 / Price in USD
        original_price: 原始价格 / Original price value
        original_currency: 原始货币代码 / Original currency code (e.g., "EUR")
        url: 来源 URL / Source URL
        in_stock: 是否有货 / Whether the item is in stock
        condition: 新旧状态 / Condition: "new", "refurbished", or "used"
        last_seen: 最后看到时间 (ISO 8601 UTC) / Last seen timestamp
        reliability_score: 来源可信度 0.0-1.0 / Source reliability score
    """

    source_name: str
    source_name_zh: str
    price_usd: Optional[float] = None
    original_price: Optional[float] = None
    original_currency: Optional[str] = None
    url: Optional[str] = None
    in_stock: Optional[bool] = None
    condition: Optional[str] = None  # new / refurbished / used
    last_seen: str = field(default_factory=lambda: _utc_now())
    reliability_score: float = 0.5


@dataclass
class ServerPart:
    """服务器零件统一数据模型 / Unified server part data model.

    这是 USPI 的核心数据结构，所有适配器返回的数据必须符合此格式 / This is the core
    data structure of USPI; all adapter output must conform to this schema.

    Attributes:
        part_number: 原始零件号 / Original part number
        manufacturer: 厂商代码 / Manufacturer code (e.g., "DELL", "FOXCONN")
        manufacturer_zh: 厂商中文名 / Manufacturer Chinese name
        oem_brand: 对应 OEM 品牌 (若 ODM 代工) / Associated OEM brand if ODM
        category: 标准化分类 key / Standardized category key
        category_zh: 中文分类 / Chinese category
        description: 英文描述 / English description
        description_zh: 中文描述 / Chinese description
        specifications: 标准化规格 (SI units) / Normalized specifications
        raw_specifications: 原始规格 / Raw specifications with original units
        sources: 价格来源列表 / List of price sources
        median_price_usd: 中位数美元价 / Median price in USD
        price_range_usd: 价格区间 (min, max) / Price range tuple
        confidence_score: 数据置信度 0.0-1.0 / Data confidence score
        last_updated: 最后更新时间 (ISO 8601 UTC) / Last updated timestamp
        unit_system: 单位体系标识 / Unit system identifier (default: "SI")
    """

    part_number: str
    manufacturer: str
    manufacturer_zh: str
    category: str
    category_zh: str
    description: str
    description_zh: str
    specifications: Dict[str, Any] = field(default_factory=dict)
    raw_specifications: Dict[str, str] = field(default_factory=dict)
    sources: List[PriceSource] = field(default_factory=list)
    oem_brand: Optional[str] = None
    median_price_usd: Optional[float] = None
    price_range_usd: Optional[tuple] = None
    confidence_score: float = 0.0
    last_updated: str = field(default_factory=lambda: _utc_now())
    unit_system: str = "SI"


# ---------------------------------------------------------------------------
# 分类枚举 / Category Enumeration
# ---------------------------------------------------------------------------

CATEGORIES: dict[str, str] = {
    "CPU": "处理器",
    "MEMORY": "内存",
    "STORAGE_HDD": "机械硬盘",
    "STORAGE_SSD": "固态硬盘",
    "STORAGE_NVME": "NVMe 硬盘",
    "RAID_CONTROLLER": "RAID 控制器",
    "NIC": "网卡",
    "GPU": "显卡/加速卡",
    "PSU": "电源",
    "FAN": "风扇",
    "HEATSINK": "散热片",
    "MOTHERBOARD": "主板",
    "BACKPLANE": "背板",
    "CABLE": "线缆",
    "RAIL_KIT": "导轨",
    "BEZEL": "面板",
    "BATTERY": "电池",
    "OTHERS": "其他",
}

# ---------------------------------------------------------------------------
# 工具函数 / Utility Functions
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串 / Return current UTC time as ISO 8601.

    Returns:
        ISO 8601 格式的时间字符串 / ISO 8601 formatted timestamp string
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# BaseAdapter 抽象基类 / BaseAdapter Abstract Base Class
# ---------------------------------------------------------------------------


class BaseAdapter(ABC):
    """所有数据源适配器的抽象基类 / Abstract base class for all data source adapters.

    子类必须实现以下方法 / Subclasses must implement:
    - lookup(part_number): 按零件号查询 / Query by part number
    - search_by_spec(**specs): 按规格搜索 / Search by specifications

    属性 / Attributes:
        name: 英文名称 / English name
        name_zh: 中文名称 / Chinese name
        source_url: 数据源 URL / Data source URL
        reliability_score: 数据源可信度 0.0-1.0 / Data source reliability score
        enabled: 是否启用 / Whether the adapter is enabled
        disabled_reason: 禁用原因 (若被禁用) / Reason for being disabled
    """

    # -- class attributes (must be overridden by subclasses) --------------

    name: str = "base"
    """适配器英文名称 / Adapter English name."""

    name_zh: str = "基类"
    """适配器中文名称 / Adapter Chinese name."""

    source_url: str = ""
    """数据源 URL / Data source URL."""

    reliability_score: float = 0.5
    """数据源可信度 (0.0-1.0) / Data source reliability score."""

    enabled: bool = True
    """是否启用 / Whether the adapter is enabled."""

    disabled_reason: Optional[str] = None
    """禁用原因 / Reason for disabling the adapter."""

    # -- lifecycle --------------------------------------------------------

    def __init__(self, fetcher: Any, currency_converter: Any) -> None:
        """初始化适配器 / Initialize the adapter.

        Args:
            fetcher: Fetcher 实例，用于 HTTP 请求 / Fetcher instance for HTTP requests
            currency_converter: CurrencyConverter 实例，用于汇率转换 /
                CurrencyConverter instance for currency conversion
        """
        self._fetcher = fetcher
        self._currency = currency_converter

    # -- abstract methods (must be implemented by subclasses) ---------------

    @abstractmethod
    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询零件信息 / Look up a part by its part number.

        Args:
            part_number: 零件号 / Part number string

        Returns:
            ServerPart 实例，未找到时返回 None / ServerPart instance or None if not found
        """
        ...

    @abstractmethod
    def search_by_spec(self, **specs: Any) -> List[ServerPart]:
        """按规格参数搜索零件 / Search parts by specification parameters.

        Args:
            **specs: 规格键值对 / Specification key-value pairs

        Returns:
            ServerPart 列表 / List of matching ServerPart instances
        """
        ...

    # -- graceful degradation ----------------------------------------------

    def disable(self, reason: str) -> None:
        """优雅降级：禁用当前适配器并记录原因 / Graceful degradation: disable self.

        当某个数据源出现反爬或故障时调用，避免影响整体查询 / Called when a data
        source is blocked or failing, to avoid affecting overall queries.

        Args:
            reason: 禁用原因 / Reason for disabling
        """
        self.enabled = False
        self.disabled_reason = reason

    def _fallback_disabled(self) -> Optional[ServerPart]:
        """适配器被禁用时返回带提示的空结果 / Return None with a disabled hint.

        Returns:
            None (表示适配器当前不可用) / None indicating adapter is unavailable
        """
        return None

    # -- helper methods for subclasses -------------------------------------

    def _fetch_html(self, url: str, **kwargs: Any) -> str:
        """使用 Fetcher 获取 HTML 的便捷方法 / Convenience method to fetch HTML.

        Args:
            url: 目标 URL / Target URL
            **kwargs: 传递给 Fetcher.fetch 的额外参数 / Extra args for Fetcher.fetch

        Returns:
            HTML 文本 / HTML text content

        Raises:
            FetchError: 抓取失败时抛出 / Raised when fetch fails
        """
        return self._fetcher.fetch(url, **kwargs)

    def _convert_to_usd(
        self,
        amount: float,
        currency: str,
    ) -> Optional[float]:
        """将金额转换为美元 / Convert an amount to USD.

        Args:
            amount: 原始金额 / Original amount
            currency: 原始货币代码 / Original currency code

        Returns:
            美元金额，或转换失败时返回 None / USD amount or None on failure
        """
        try:
            result = self._currency.convert_to_usd(amount, currency)
            return result.get("usd_amount")
        except Exception:
            # Graceful degradation: 汇率转换失败返回 None / Return None on failure
            return None

    def _is_available(self) -> bool:
        """检查适配器是否可用 / Check if the adapter is available.

        Returns:
            True 如果适配器已启用 / True if the adapter is enabled
        """
        return self.enabled

    def __repr__(self) -> str:
        """返回适配器的字符串表示 / Return string representation of the adapter.

        Returns:
            格式: <BaseAdapter(name='...', enabled=True)> / Formatted string
        """
        status = "enabled" if self.enabled else f"disabled({self.disabled_reason})"
        return f"<{self.__class__.__name__}(name='{self.name}', {status})>"
