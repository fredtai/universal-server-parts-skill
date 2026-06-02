"""
uspi/core/adapters/lenovo_adapter.py

Lenovo OEM 适配器 / Lenovo OEM Adapter.

通过 Lenovo Support 查询 Lenovo 服务器零件信息。
Queries Lenovo server part information via Lenovo Support.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from uspi.core.adapters.base import CATEGORIES, BaseAdapter, PriceSource, ServerPart
from uspi.core.adapters._common import (
    clean_html_text,
    extract_normalized_specs,
    extract_price_from_html,
    extract_specs_from_html,
    infer_category_from_text,
    make_mock_part,
    normalize_capacity,
    utc_now,
)
from uspi.core.fetcher import FetchError


class LenovoAdapter(BaseAdapter):
    """Lenovo OEM 零件查询适配器 / Lenovo OEM parts lookup adapter.

    Attributes:
        name: 适配器英文标识 / Adapter English identifier.
        name_zh: 适配器中文名称 / Adapter Chinese name.
        source_url: Lenovo 支持页面 URL / Lenovo support URL.
        reliability_score: 数据源可信度 0.82 / Data source reliability score.
    """

    name = "lenovo"
    name_zh = "\u8054\u60f3"
    source_url = "https://support.lenovo.com/us/en/partslookup/{pn}"
    reliability_score = 0.82

    # Lenovo FRU 前缀分类映射 / Lenovo FRU prefix category map
    FRU_PREFIX_CATEGORIES: Dict[str, str] = {
        "00": "STORAGE_HDD", "01": "MEMORY", "02": "CPU",
        "03": "NIC", "04": "PSU", "05": "FAN",
        "07": "RAID_CONTROLLER", "0A": "MOTHERBOARD",
    }

    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询 Lenovo 零件信息 / Look up a Lenovo part by part number.

        Args:
            part_number: Lenovo 零件号 / Lenovo part number (e.g., "01KN234").

        Returns:
            ServerPart 实例或 mock 数据 / ServerPart or mock data.
        """
        if not part_number or not isinstance(part_number, str):
            return None
        if not self.enabled:
            return self._fallback_disabled()

        cleaned_pn = part_number.strip().upper()
        url = self.source_url.format(pn=cleaned_pn)

        try:
            html = self._fetcher.fetch(url)
            result = self._parse_html(html, cleaned_pn)
            if result is not None:
                return result
        except FetchError:
            pass
        return self._mock_lookup(cleaned_pn)

    def search_by_spec(self, **specs: Any) -> List[ServerPart]:
        """按规格参数搜索 Lenovo 零件 / Search Lenovo parts by specifications.

        Args:
            **specs: 规格键值对 / Specification key-value pairs.

        Returns:
            ServerPart 列表 / List of ServerPart instances.
        """
        return []

    def _parse_html(self, html: str, part_number: str) -> Optional[ServerPart]:
        """从 HTML 中提取 Lenovo 零件规格 / Extract Lenovo part specs from HTML.

        Args:
            html: 抓取的 HTML 内容 / Fetched HTML content.
            part_number: 零件号 / Part number.

        Returns:
            ServerPart 实例，解析失败返回 None / ServerPart or None on parse failure.
        """
        text = clean_html_text(html)
        price = extract_price_from_html(text)
        specs = extract_specs_from_html(html)
        cat, cat_zh, _ = infer_category_from_text(text)

        # Lenovo FRU 前缀推断 / Lenovo FRU prefix inference
        if cat == "OTHERS" and len(part_number) >= 2:
            prefix = part_number[:2]
            if prefix in self.FRU_PREFIX_CATEGORIES:
                cat = self.FRU_PREFIX_CATEGORIES[prefix]
                cat_zh = CATEGORIES.get(cat, "\u5176\u4ed6")

        norm_specs = extract_normalized_specs(text, specs)
        if specs:
            norm_specs.update(specs)

        now = utc_now()
        sources = []
        if price is not None:
            sources.append(PriceSource(
                source_name="Lenovo_Support", source_name_zh="\u8054\u60f3\u652f\u6301",
                price_usd=price, original_price=price, original_currency="USD",
                url=self.source_url.format(pn=part_number),
                in_stock=None, condition="new", last_seen=now,
                reliability_score=self.reliability_score,
            ))

        return ServerPart(
            part_number=part_number, manufacturer="LENOVO", manufacturer_zh="\u8054\u60f3",
            oem_brand="LENOVO", category=cat, category_zh=cat_zh,
            description=text[:200] if text else f"Lenovo Part {part_number}",
            description_zh=f"\u8054\u60f3\u96f6\u4ef6 {part_number}",
            specifications=norm_specs, raw_specifications=specs, sources=sources,
            median_price_usd=price,
            price_range_usd=(price, price) if price else None,
            confidence_score=0.75 if sources else 0.5, last_updated=now,
        )

    def _mock_lookup(self, part_number: str) -> ServerPart:
        """返回 Lenovo 零件的 mock 数据 / Return mock data for a Lenovo part.

        Args:
            part_number: Lenovo 零件号 / Lenovo part number.

        Returns:
            \u5e26 mock \u6807\u5fd7\u7684\u5b8c\u6574 ServerPart / Complete ServerPart with mock flag.
        """
        cat, cat_zh, _ = infer_category_from_text(part_number)

        # Lenovo FRU 前缀推断
        if cat == "OTHERS" and len(part_number) >= 2:
            prefix = part_number[:2]
            if prefix in self.FRU_PREFIX_CATEGORIES:
                cat = self.FRU_PREFIX_CATEGORIES[prefix]
                cat_zh = CATEGORIES.get(cat, "\u5176\u4ed6")

        specs: Dict[str, Any] = {"inferred": True}
        cap_match = re.search(r"(\d+\.?\d*)\s*(GB|TB|MB)", part_number, re.I)
        if cap_match:
            specs["capacity_gb"] = normalize_capacity(cap_match.group(1), cap_match.group(2))

        return make_mock_part(
            part_number=part_number, manufacturer="LENOVO", manufacturer_zh="\u8054\u60f3",
            category=cat, category_zh=cat_zh,
            description=f"Lenovo {cat_zh} FRU Part {part_number}",
            description_zh=f"\u8054\u60f3{cat_zh}FRU\u96f6\u4ef6 {part_number}\uff08\u6a21\u62df\u6570\u636e\uff09",
            oem_brand="LENOVO", specs=specs, url=self.source_url.format(pn=part_number),
        )
