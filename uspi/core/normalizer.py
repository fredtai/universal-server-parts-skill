"""
uspi/core/normalizer.py

数据归一化模块 / Data Normalization Module.

将适配器原始输出归一化为标准 ServerPart 格式。
Normalizes adapter raw output to standard ServerPart format.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from uspi.core.adapters.base import CATEGORIES, PriceSource, ServerPart
from uspi.core.unit_converter import UnitConverter


class Normalizer:
    """数据归一化器 / Data normalizer.

    将适配器的原始字典输出转换为标准 ServerPart 对象。
    Converts adapter raw dict output to standard ServerPart objects.
    """

    def __init__(
        self,
        unit_converter: Optional[UnitConverter] = None,
        currency_converter: Any = None,
    ) -> None:
        """初始化归一化器 / Initialize normalizer.

        Args:
            unit_converter: UnitConverter 实例 / UnitConverter instance.
            currency_converter: 货币转换器实例 / Currency converter instance.
        """
        self._uc = unit_converter or UnitConverter()
        self._currency = currency_converter

    def normalize(self, raw_data: Dict[str, Any], adapter_name: str = "") -> ServerPart:
        """将原始数据归一化为 ServerPart / Normalize raw data to ServerPart.

        Args:
            raw_data: 适配器原始输出字典 / Adapter raw output dict.
            adapter_name: 适配器名称 / Adapter name.

        Returns:
            ServerPart 实例 / ServerPart instance.
        """
        part_number = raw_data.get("part_number", "UNKNOWN")
        manufacturer = raw_data.get("manufacturer", "UNKNOWN")
        manufacturer_zh = raw_data.get("manufacturer_zh", "")
        category = raw_data.get("category", "OTHERS")
        category_zh = CATEGORIES.get(category, "其他")
        description = raw_data.get("description", "")
        description_zh = raw_data.get("description_zh", "")
        oem_brand = raw_data.get("oem_brand")

        raw_specs = raw_data.get("raw_specifications", {})
        if not raw_specs:
            raw_specs = raw_data.get("specifications", {})

        normalized_specs = self.normalize_specs(raw_specs)

        sources_raw = raw_data.get("sources", [])
        sources = self._build_sources(sources_raw)

        median_price = raw_data.get("median_price_usd")
        price_range = raw_data.get("price_range_usd")
        confidence = raw_data.get("confidence_score", 0.0)
        last_updated = raw_data.get("last_updated", "")

        return ServerPart(
            part_number=part_number,
            manufacturer=manufacturer,
            manufacturer_zh=manufacturer_zh,
            oem_brand=oem_brand,
            category=category,
            category_zh=category_zh,
            description=description,
            description_zh=description_zh,
            specifications=normalized_specs,
            raw_specifications=raw_specs if isinstance(raw_specs, dict) else {},
            sources=sources,
            median_price_usd=median_price,
            price_range_usd=price_range,
            confidence_score=confidence,
            last_updated=last_updated,
        )

    def normalize_specs(self, raw_specs: Dict[str, str]) -> Dict[str, Any]:
        """规格归一化 / Normalize specifications.

        将原始规格（含原始单位）转换为 SI 标准单位。
        Converts raw specs (with original units) to SI standard units.

        Args:
            raw_specs: 原始规格字典 / Raw specifications dict.

        Returns:
            标准化规格字典 / Normalized specifications dict.
        """
        result: Dict[str, Any] = {}
        if not raw_specs:
            return result

        # 维度映射 / Dimension mapping
        dimension_map = {
            "capacity": "capacity",
            "capacity_gb": "capacity",
            "memory": "capacity",
            "storage": "capacity",
            "frequency": "frequency",
            "speed": "frequency",
            "clock": "frequency",
            "power": "power",
            "wattage": "power",
            "dimension": "dimension",
            "size": "dimension",
            "weight": "weight",
            "rpm": "rpm",
            "voltage": "voltage",
            "current": "current",
            "temperature": "temperature",
            "data_rate": "data_rate",
            "bandwidth": "data_rate",
            "cache": "cache",
        }

        for key, raw_value in raw_specs.items():
            if not isinstance(raw_value, str):
                result[key] = raw_value
                continue

            dim = dimension_map.get(key.lower())
            if dim:
                converted = self._uc.normalize_value(raw_value, dim)
                if converted.get("value") is not None and converted["confidence"] > 0.0:
                    result[f"{key}_normalized"] = {
                        "value": converted["value"],
                        "unit": converted["unit"],
                    }
                    result[key] = raw_value
                else:
                    result[key] = raw_value
            else:
                result[key] = raw_value

        return result

    def normalize_price(self, amount: float, currency: str) -> Dict[str, Any]:
        """价格归一化为 USD / Normalize price to USD.

        Args:
            amount: 原始金额 / Original amount.
            currency: 原始货币 / Original currency.

        Returns:
            归一化结果字典 / Normalized price dict.
        """
        if currency.upper() == "USD":
            return {"price_usd": amount, "original_price": amount,
                    "original_currency": "USD", "stale": False}

        if self._currency is not None:
            try:
                conv = self._currency.convert_to_usd(amount, currency)
                return {
                    "price_usd": conv.get("usd_amount"),
                    "original_price": amount,
                    "original_currency": currency,
                    "stale": conv.get("stale", False),
                    "source": conv.get("source", "unknown"),
                }
            except Exception:
                pass

        return {"price_usd": None, "original_price": amount,
                "original_currency": currency, "stale": True}

    @staticmethod
    def aggregate_sources(sources: List[PriceSource]) -> Dict[str, Any]:
        """聚合多源价格信息 / Aggregate multi-source price info.

        Args:
            sources: PriceSource 列表 / List of PriceSource.

        Returns:
            聚合结果字典 / Aggregated result dict.
        """
        prices: List[float] = []
        reliability_sum = 0.0
        in_stock_count = 0

        for s in sources:
            if s.price_usd is not None:
                prices.append(s.price_usd)
            reliability_sum += s.reliability_score
            if s.in_stock:
                in_stock_count += 1

        result: Dict[str, Any] = {
            "source_count": len(sources),
            "avg_reliability": reliability_sum / len(sources) if sources else 0.0,
            "in_stock_count": in_stock_count,
        }

        if prices:
            prices_sorted = sorted(prices)
            n = len(prices_sorted)
            result["min_price_usd"] = prices_sorted[0]
            result["max_price_usd"] = prices_sorted[-1]
            # median / 中位数
            if n % 2 == 1:
                result["median_price_usd"] = prices_sorted[n // 2]
            else:
                result["median_price_usd"] = (prices_sorted[n // 2 - 1] + prices_sorted[n // 2]) / 2
        else:
            result["min_price_usd"] = None
            result["max_price_usd"] = None
            result["median_price_usd"] = None

        return result

    @staticmethod
    def median_price(sources: List[PriceSource]) -> Optional[float]:
        """计算中位数价格 / Calculate median price.

        Args:
            sources: PriceSource 列表 / List of PriceSource.

        Returns:
            中位数 USD 价格或 None / Median USD price or None.
        """
        prices = [s.price_usd for s in sources if s.price_usd is not None]
        if not prices:
            return None
        prices_sorted = sorted(prices)
        n = len(prices_sorted)
        if n % 2 == 1:
            return prices_sorted[n // 2]
        return (prices_sorted[n // 2 - 1] + prices_sorted[n // 2]) / 2

    def _build_sources(self, sources_raw: List[Any]) -> List[PriceSource]:
        """构建 PriceSource 列表 / Build PriceSource list.

        Args:
            sources_raw: 原始来源数据列表 / Raw source data list.

        Returns:
            PriceSource 列表 / List of PriceSource.
        """
        sources: List[PriceSource] = []
        for s in sources_raw:
            if isinstance(s, dict):
                sources.append(PriceSource(
                    source_name=s.get("source_name", ""),
                    source_name_zh=s.get("source_name_zh", ""),
                    price_usd=s.get("price_usd"),
                    original_price=s.get("original_price"),
                    original_currency=s.get("original_currency"),
                    url=s.get("url"),
                    in_stock=s.get("in_stock"),
                    condition=s.get("condition"),
                    reliability_score=s.get("reliability_score", 0.5),
                    last_seen=s.get("last_seen", ""),
                ))
            elif isinstance(s, PriceSource):
                sources.append(s)
        return sources


__all__ = ["Normalizer"]
