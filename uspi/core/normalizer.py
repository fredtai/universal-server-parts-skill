"""
uspi/core/normalizer.py

数据归一化器 / Data Normalizer

将各适配器的原始输出统一转换为标准 ServerPart 对象。
Converts raw adapter outputs into standardized ServerPart objects.

提供规格归一化（SI 标准单位）、价格归一化（USD）、中位数计算、
多适配器结果聚合等功能。
Provides spec normalization (SI units), price normalization (USD), median
price calculation, and multi-adapter result aggregation.
"""

from __future__ import annotations

import re
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from uspi.core.adapters.base import CATEGORIES, PriceSource, ServerPart
from uspi.core.unit_converter import UnitConverter


# 模块级常量 / Module-level constants
_ISO_FMT: str = "%Y-%m-%dT%H:%M:%SZ"
"""ISO 8601 UTC 时间格式字符串（避免重复字面量）。"""


def _utc_now() -> str:
    """Return current UTC time as ISO 8601 string.

    返回当前 UTC 时间的 ISO 8601 字符串。
    """
    return datetime.now(timezone.utc).strftime(_ISO_FMT)


class Normalizer:
    """数据归一化器：将各适配器的原始输出统一转换为标准 ServerPart。

    Data Normalizer: Unifies raw adapter outputs into standard ServerPart objects.

    负责字段映射、规格 SI 标准化、价格 USD 转换、可信度评分、
    以及多源结果聚合。
    Handles field mapping, spec SI standardization, price USD conversion,
    confidence scoring, and multi-source result aggregation.
    """

    # 常见原始字段名到标准字段名的映射 / Mapping of common raw field names to standard fields
    _FIELD_ALIASES: dict[str, list[str]] = {
        "part_number": ["part_number", "partNumber", "pn", "part_no", "dpn", "fru", "model"],
        "manufacturer": ["manufacturer", "vendor", "brand", "mfr", "oem", "supplier"],
        "manufacturer_zh": ["manufacturer_zh", "vendor_zh", "brand_zh"],
        "oem_brand": ["oem_brand", "oem", "original_brand"],
        "category": ["category", "type", "component_type", "product_type"],
        "description": ["description", "desc", "product_name", "title", "name"],
        "description_zh": ["description_zh", "desc_zh", "name_zh", "title_zh"],
        "specifications": ["specifications", "specs", "spec", "technical_specs", "details"],
        "sources": ["sources", "price_sources", "vendors", "listings"],
    }

    # 分类推断关键词 / Category inference keywords
    _CATEGORY_KEYWORDS: dict[str, list[str]] = {
        "CPU": ["processor", "cpu", "xeon", "epyc", "opteron"],
        "MEMORY": ["memory", "ram", "ddr", "dimms", "dimm", "ecc memory"],
        "STORAGE_HDD": ["hdd", "hard drive", "hard disk", "sata hdd"],
        "STORAGE_SSD": ["ssd", "sata ssd", "solid state"],
        "STORAGE_NVME": ["nvme", "pcie ssd", "m.2"],
        "RAID_CONTROLLER": ["raid", "sas controller", "hba"],
        "NIC": ["nic", "network adapter", "ethernet", "lan card", "infiniband"],
        "GPU": ["gpu", "graphics", "accelerator", "tesla", "a100", "h100"],
        "PSU": ["power supply", "psu", "power adapter"],
        "FAN": ["fan", "cooling fan", "blower"],
        "HEATSINK": ["heatsink", "heat sink", "cooler", "radiator"],
        "MOTHERBOARD": ["motherboard", "system board", "mainboard", "planar"],
        "BACKPLANE": ["backplane", "backplane board"],
        "CABLE": ["cable", "cables", "power cable", "data cable"],
        "RAIL_KIT": ["rail", "rail kit", "slide rail", "mounting rail"],
        "BEZEL": ["bezel", "front bezel", "trim"],
        "BATTERY": ["battery", "cmos battery", "raid battery"],
    }

    # 预编译分类推断正则（O(N) 替代 O(N*M)）/ Pre-compiled category regex
    _CATEGORY_PATTERNS: dict[str, re.Pattern] = {
        cat: re.compile("|".join(re.escape(kw) for kw in kws), re.IGNORECASE)
        for cat, kws in _CATEGORY_KEYWORDS.items()
    }

    # 常见键名映射（类级别常量避免每次调用重建）/ Common key map as class constant
    _DIMENSION_KEY_MAP: dict[str, str] = {
        "capacity": "capacity",
        "size": "capacity",
        "mem": "capacity",
        "memory": "capacity",
        "speed": "frequency",
        "clock": "frequency",
        "freq": "frequency",
        "power": "power",
        "wattage": "power",
        "pwr": "power",
        "dimension": "dimension",
        "dimensions": "dimension",
        "weight": "weight",
        "rpm": "rpm",
        "voltage": "voltage",
        "current": "current",
        "temp": "temperature",
        "temperature": "temperature",
        "data_rate": "data_rate",
        "bandwidth": "data_rate",
        "cache": "cache",
    }

    def __init__(
        self,
        unit_converter: type[UnitConverter] = UnitConverter,
        currency_converter: Any = None,
        cache: Any = None,
        parser: Any = None,
    ) -> None:
        """Initialize the Normalizer.

        初始化归一化器。

        Args:
            unit_converter: UnitConverter class or instance for spec normalization.
                用于规格归一化的 UnitConverter 类或实例。
            currency_converter: CurrencyConverter instance for price conversion.
                用于价格转换的 CurrencyConverter 实例。
            cache: Optional cache instance for storing normalized results.
                可选的缓存实例，用于存储归一化结果。
            parser: Optional PartParser instance for category/part number inference.
                可选的零件号解析器实例，用于分类/零件号推断。
        """
        self._unit_converter = unit_converter
        self._currency = currency_converter
        self._cache = cache
        self._parser = parser

    # ------------------------------------------------------------------
    # 公共 API / Public API
    # ------------------------------------------------------------------

    def normalize(self, raw_data: dict, adapter_name: str) -> ServerPart:
        """将适配器的原始字典归一化为标准 ServerPart。

        Convert raw adapter output dictionary into a standard ServerPart.

        Args:
            raw_data: 适配器返回的原始字典 / Raw dictionary from adapter.
            adapter_name: 适配器名称（如 "dell", "ebay"）/ Adapter name (e.g., "dell").

        Returns:
            标准化的 ServerPart 实例 / Standardized ServerPart instance.
        """
        if raw_data is None:
            raw_data = {}

        # 1. 提取基础字段 / Extract base fields
        part_number: str = self._extract_field(raw_data, "part_number") or "UNKNOWN"
        manufacturer: str = self._extract_field(raw_data, "manufacturer") or adapter_name.upper()
        manufacturer_zh: str = self._extract_field(raw_data, "manufacturer_zh") or manufacturer
        oem_brand: Optional[str] = self._extract_field(raw_data, "oem_brand")

        # 2. 推断分类 / Infer category
        category_key, category_zh = self._infer_category(raw_data)

        # 3. 描述 / Descriptions
        description: str = self._extract_field(raw_data, "description") or ""
        description_zh: str = self._extract_field(raw_data, "description_zh") or description

        # 4. 规格归一化 / Normalize specifications
        raw_specs: dict = raw_data.get("raw_specifications") or raw_data.get("specifications") or raw_data.get("specs", {})
        if isinstance(raw_specs, dict):
            specifications = self.normalize_specs(raw_specs)
            raw_specifications = {k: str(v) for k, v in raw_specs.items()}
        else:
            specifications = {}
            raw_specifications = {}

        # 5. 价格来源 / Price sources
        sources: list = raw_data.get("sources") or raw_data.get("price_sources") or []
        price_sources: list[PriceSource] = []
        if isinstance(sources, list):
            for src in sources:
                ps = self._normalize_price_source(src)
                if ps:
                    price_sources.append(ps)

        # 6. 价格统计 / Price statistics
        median_price = self.compute_median_price(price_sources)
        price_range = self.compute_price_range(price_sources)

        # 7. 可信度评分 / Confidence score
        confidence: float = raw_data.get("confidence_score", 0.0)
        if not confidence and price_sources:
            # 基于来源可信度加权计算 / Weighted by source reliability
            confidence = round(
                min(1.0, sum(s.reliability_score for s in price_sources) / len(price_sources)),
                3,
            )
        confidence = max(0.0, min(1.0, confidence))

        # 8. 构建 ServerPart / Build ServerPart
        now: str = _utc_now()
        last_updated: str = raw_data.get("last_updated") or raw_data.get("last_seen") or now

        return ServerPart(
            part_number=part_number,
            manufacturer=manufacturer,
            manufacturer_zh=manufacturer_zh,
            oem_brand=oem_brand,
            category=category_key,
            category_zh=category_zh,
            description=description,
            description_zh=description_zh,
            specifications=specifications,
            raw_specifications=raw_specifications,
            sources=price_sources,
            median_price_usd=median_price,
            price_range_usd=price_range,
            confidence_score=confidence,
            last_updated=last_updated,
            unit_system="SI",
        )

    def normalize_specs(self, raw_specs: dict) -> dict:
        """规格归一化：原始单位 → SI 标准。

        Normalize raw specifications to SI standard units.

        遍历 raw_specs，对每个值调用 UnitConverter.normalize_value()，
        自动识别维度并转换。结果放入归一化字典。
        Iterates raw_specs, calls UnitConverter.normalize_value() on each value,
        auto-detects dimension and converts. Results go into normalized dict.

        Args:
            raw_specs: 原始规格字典（键值对）/ Raw spec dictionary (key-value pairs).

        Returns:
            归一化后的规格字典，每个值包含 {value, unit, raw, confidence}
            Normalized spec dict, each value containing {value, unit, raw, confidence}.
        """
        normalized: dict[str, Any] = {}
        if not raw_specs:
            return normalized

        for key, val in raw_specs.items():
            if val is None:
                continue
            raw_str: str = str(val)
            dimension: Optional[str] = self._detect_dimension(key, raw_str)

            if dimension and self._unit_converter is not None:
                try:
                    result = self._unit_converter.normalize_value(raw_str, dimension)
                except Exception:
                    # 转换失败时保留原始值 / Keep original on failure
                    result = {"value": raw_str, "unit": "", "raw": raw_str, "confidence": 0.0}
            else:
                # 无法识别维度，保留原始字符串 / Unknown dimension, keep raw string
                result = {"value": raw_str, "unit": "", "raw": raw_str, "confidence": 0.0}

            normalized[key] = result

        return normalized

    def normalize_price(self, amount: float, currency: str) -> dict:
        """价格归一化 → USD。

        Normalize price to USD.

        调用 CurrencyConverter.convert_to_usd() 将给定货币金额转换为美元。
        Calls CurrencyConverter.convert_to_usd() to convert amount to USD.

        Args:
            amount: 原始金额 / Original amount.
            currency: 原始货币代码（如 "EUR", "CNY"）/ Original currency code.

        Returns:
            包含 usd_amount, rate, stale, source 的字典
            Dict with usd_amount, rate, stale, source.
            如果 currency_converter 不可用，返回原始金额作为 usd_amount。
            If currency_converter is unavailable, returns original amount as usd_amount.
        """
        if self._currency is None:
            return {
                "usd_amount": amount,
                "rate": 1.0,
                "stale": True,
                "source": "no_converter",
            }
        try:
            return self._currency.convert_to_usd(amount, currency)
        except Exception:
            # 转换失败，返回原始金额 / Return original on failure
            return {
                "usd_amount": amount,
                "rate": 1.0,
                "stale": True,
                "source": "error_fallback",
            }

    def compute_median_price(self, sources: list[PriceSource]) -> Optional[float]:
        """从多个 PriceSource 计算中位数价格。

        Calculate the median price from a list of PriceSource objects.

        过滤掉 price_usd 为 None 的来源，然后计算中位数。
        Filters out sources with None price_usd, then computes median.

        Args:
            sources: PriceSource 列表 / List of PriceSource objects.

        Returns:
            中位数美元价格，四舍五入到小数点后2位；无有效价格时返回 None
            Median USD price rounded to 2 decimals, or None if no valid prices.
        """
        prices: list[float] = [s.price_usd for s in sources if s.price_usd is not None]
        if not prices:
            return None
        median: float = statistics.median(prices)
        return round(median, 2)

    def compute_price_range(self, sources: list[PriceSource]) -> Optional[tuple]:
        """计算价格区间 (min, max)。

        Calculate the price range (min, max) from price sources.

        Args:
            sources: PriceSource 列表 / List of PriceSource objects.

        Returns:
            (最低价, 最高价) 元组，四舍五入到小数点后2位；无有效价格时返回 None
            (lowest, highest) tuple rounded to 2 decimals, or None if no valid prices.
        """
        prices: list[float] = [s.price_usd for s in sources if s.price_usd is not None]
        if not prices:
            return None
        return (round(min(prices), 2), round(max(prices), 2))

    def aggregate_sources(self, parts: list[ServerPart]) -> Optional[ServerPart]:
        """聚合多个适配器的查询结果为一个 ServerPart。

        Aggregate results from multiple adapters into a single ServerPart.

        合并所有 sources 列表，计算中位数价格，取最高 confidence_score，
        保留最详细的描述和规格。
        Merges all source lists, computes median price, takes highest confidence_score,
        keeps the most detailed description and specs.

        Args:
            parts: 多个适配器返回的 ServerPart 列表 / List of ServerPart from multiple adapters.

        Returns:
            聚合后的 ServerPart，如果输入为空则返回 None
            Aggregated ServerPart, or None if input is empty.
        """
        if not parts:
            return None

        # 选择最佳基准零件（confidence_score 最高）
        # Select best base part (highest confidence_score)
        base: ServerPart = max(parts, key=lambda p: p.confidence_score)

        # 合并所有 sources / Merge all sources
        all_sources: list[PriceSource] = []
        seen_urls: set[str] = set()
        for p in parts:
            for s in p.sources:
                # 去重：基于 URL / Deduplicate by URL
                url_key: str = s.url or f"{s.source_name}_{s.original_price}_{s.original_currency}"
                if url_key not in seen_urls:
                    seen_urls.add(url_key)
                    all_sources.append(s)

        # 合并规格（取最详细的）/ Merge specs (take most detailed)
        merged_specs: dict[str, Any] = dict(base.specifications)
        for p in parts:
            if p is base:
                continue
            for key, val in p.specifications.items():
                if key not in merged_specs:
                    merged_specs[key] = val

        # 合并原始规格 / Merge raw specs
        merged_raw_specs: dict[str, str] = dict(base.raw_specifications)
        for p in parts:
            if p is base:
                continue
            for key, val in p.raw_specifications.items():
                if key not in merged_raw_specs:
                    merged_raw_specs[key] = val

        # 重新计算价格统计 / Recompute price stats
        median_price = self.compute_median_price(all_sources)
        price_range = self.compute_price_range(all_sources)

        # 取最高可信度 / Take highest confidence
        best_confidence: float = round(max(p.confidence_score for p in parts), 3)

        # 构建聚合结果 / Build aggregated result
        return ServerPart(
            part_number=base.part_number,
            manufacturer=base.manufacturer,
            manufacturer_zh=base.manufacturer_zh,
            oem_brand=base.oem_brand,
            category=base.category,
            category_zh=base.category_zh,
            description=base.description,
            description_zh=base.description_zh,
            specifications=merged_specs,
            raw_specifications=merged_raw_specs,
            sources=all_sources,
            median_price_usd=median_price,
            price_range_usd=price_range,
            confidence_score=best_confidence,
            last_updated=_utc_now(),
            unit_system="SI",
        )

    # ------------------------------------------------------------------
    # 内部方法 / Internal Methods
    # ------------------------------------------------------------------

    def _extract_field(self, raw_data: dict, standard_field: str) -> Optional[str]:
        """从原始数据中提取标准字段，支持字段别名。

        Extract a standard field from raw data, supporting field aliases.

        Args:
            raw_data: 原始数据字典 / Raw data dictionary.
            standard_field: 标准字段名 / Standard field name.

        Returns:
            字段值字符串，未找到时返回 None / Field value string, or None if not found.
        """
        aliases: list[str] = self._FIELD_ALIASES.get(standard_field, [standard_field])
        for alias in aliases:
            if alias in raw_data and raw_data[alias] is not None:
                return str(raw_data[alias]).strip()
        return None

    def _infer_category(self, raw_data: dict) -> tuple[str, str]:
        """从原始数据中推断分类。

        Infer the category from raw data.

        依次检查显式 category 字段、description、specifications 中的关键词。
        使用预编译正则实现 O(N) 复杂度（N=分类数），替代原有的 O(N*M) 嵌套循环。
        Checks explicit category field, description, then spec keywords.
        Uses pre-compiled regex for O(N) complexity vs original O(N*M) nested loops.

        Args:
            raw_data: 原始数据字典 / Raw data dictionary.

        Returns:
            (分类键, 中文分类名) 元组 / Tuple of (category_key, category_zh_name).
        """
        # 1. 检查显式 category / Check explicit category
        explicit: Optional[str] = (
            raw_data.get("category")
            or raw_data.get("type")
            or raw_data.get("component_type")
        )
        if explicit:
            explicit_upper: str = explicit.upper()
            if explicit_upper in CATEGORIES:
                return (explicit_upper, CATEGORIES[explicit_upper])
            # 模糊匹配 / Fuzzy match — O(C) set lookup
            for key, zh in CATEGORIES.items():
                if key in explicit_upper or zh in explicit:
                    return (key, zh)

        # 2. 从描述推断 / Infer from description
        text_to_check: str = " ".join(
            str(v) for v in [
                raw_data.get("description", ""),
                raw_data.get("title", ""),
                raw_data.get("name", ""),
            ] if v
        )

        if text_to_check.strip():
            # 预编译正则 O(N) 单遍匹配 / Pre-compiled regex O(N) single pass
            for cat_key, pattern in self._CATEGORY_PATTERNS.items():
                if pattern.search(text_to_check):
                    return (cat_key, CATEGORIES.get(cat_key, cat_key))

        # 3. 从规格推断 / Infer from specifications
        specs_text: str = " ".join(
            f"{k} {v}" for k, v in raw_data.get("specifications", {}).items()
        )
        for cat_key, pattern in self._CATEGORY_PATTERNS.items():
            if pattern.search(specs_text):
                return (cat_key, CATEGORIES.get(cat_key, cat_key))

        # 默认：其他 / Default: OTHERS
        return ("OTHERS", CATEGORIES["OTHERS"])

    def _detect_dimension(self, spec_key: str, raw_value: str) -> Optional[str]:
        """根据规格键和原始值检测维度类型。

        Detect the dimension type from spec key and raw value.
        优化版本：使用类级别常量字典 + 预编译正则，消除 O(D*P) 嵌套循环。
        Optimized: class-level dict + pre-compiled regex, eliminates O(D*P) nested loops.

        Args:
            spec_key: 规格键名（如 "capacity", "frequency"）/ Spec key name.
            raw_value: 原始值字符串 / Raw value string.

        Returns:
            维度键（来自 UnitConverter.DIMENSIONS）或 None
            Dimension key (from UnitConverter.DIMENSIONS) or None.
        """
        key_lower: str = spec_key.lower()
        val_lower: str = raw_value.lower()

        # 1. 直接键匹配 / Direct key matching
        for dim in UnitConverter.DIMENSIONS:
            if dim.lower() in key_lower:
                return dim

        # 2. 值内容匹配 — 使用预编译正则 / Value match — use pre-compiled regex
        # 从 unit_converter 导入模块级预编译模式 / Import module-level pre-compiled patterns
        from uspi.core.unit_converter import _UNIT_PATTERNS

        for dim in UnitConverter.DIMENSIONS:
            patterns = _UNIT_PATTERNS.get(dim, [])
            for compiled_pattern, _ in patterns:
                if compiled_pattern.search(raw_value):
                    return dim
            std_unit: str = UnitConverter.STANDARD_UNITS.get(dim, "")
            if std_unit and std_unit.lower() in val_lower:
                return dim

        # 3. 常见键名映射 — O(1) 类常量查表 / Common key map — O(1) class constant lookup
        return self._DIMENSION_KEY_MAP.get(key_lower)

    def _normalize_price_source(self, raw_source: dict) -> Optional[PriceSource]:
        """将原始价格来源字典归一化为 PriceSource。

        Normalize a raw price source dict into a PriceSource object.

        Args:
            raw_source: 原始价格来源字典 / Raw price source dictionary.

        Returns:
            PriceSource 实例，或 None 如果输入无效
            PriceSource instance, or None if input is invalid.
        """
        if not isinstance(raw_source, dict):
            return None

        source_name: str = raw_source.get("source_name", "unknown")
        source_name_zh: str = raw_source.get("source_name_zh", source_name)
        original_price: Optional[float] = raw_source.get("original_price")
        original_currency: Optional[str] = raw_source.get("original_currency", "USD")
        price_usd: Optional[float] = raw_source.get("price_usd")

        # 如有原始价格但无 USD 价格，进行转换
        # If original price exists but no USD price, convert
        if price_usd is None and original_price is not None and self._currency is not None:
            try:
                result: dict = self._currency.convert_to_usd(
                    original_price, original_currency or "USD"
                )
                price_usd = result.get("usd_amount")
            except Exception:
                price_usd = original_price  # 无法转换时使用原始值 / Use original on failure

        return PriceSource(
            source_name=source_name,
            source_name_zh=source_name_zh,
            price_usd=price_usd,
            original_price=original_price,
            original_currency=original_currency,
            url=raw_source.get("url"),
            in_stock=raw_source.get("in_stock"),
            condition=raw_source.get("condition"),
            last_seen=raw_source.get("last_seen") or raw_source.get("last_updated") or _utc_now(),
            reliability_score=float(raw_source.get("reliability_score", 0.5)),
        )


__all__ = ["Normalizer"]
