"""
uspi/core/adapters/jabil_adapter.py

捷普 (Jabil) ODM 适配器 / Jabil ODM Adapter.

为 DELL、HP、LENOVO 等品牌代工服务器及零部件。
Jabil produces server parts for DELL, HP, LENOVO, and others.
"""
from __future__ import annotations

from typing import Any, List, Optional

from uspi.core.adapters.base import CATEGORIES, BaseAdapter, PriceSource, ServerPart
from uspi.core.adapters._common import (
    extract_specs_from_html, infer_category_from_specs, infer_category_from_text,
    make_mock_part, utc_now,
)


class JabilAdapter(BaseAdapter):
    """捷普 ODM 适配器 / Jabil ODM adapter.

    Attributes:
        name: 适配器英文标识 / Adapter English code.
        name_zh: 适配器中文名 / Adapter Chinese name.
        source_url: 捷普官网 / Jabil official website.
        reliability_score: 数据源可信度 / Data reliability.
        oem_brands: 可能代工的品牌列表 / Possible OEM brands.
        part_prefixes: 零件号前缀 / Part number prefixes.
    """

    name = "jabil"
    name_zh = "\u6377\u666e"
    source_url = "https://www.jabil.com"
    reliability_score = 0.62
    oem_brands = ["DELL", "HP", "LENOVO"]
    part_prefixes = ["JBL", "J"]

    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询捷普零件信息 / Look up a Jabil part by part number.

        Args:
            part_number: 零件号字符串 / Part number string.

        Returns:
            ServerPart 实例或 None / ServerPart instance or None.
        """
        if not part_number or not isinstance(part_number, str):
            return None
        if not self._is_available():
            return self._fallback_disabled()

        try:
            url = f"{self.source_url}/search?q={part_number}"
            html = self._fetch_html(url, timeout=10)
            if html and len(html) > 100:
                result = self._parse_response(part_number, html)
                if result:
                    return result
        except Exception:
            pass
        return self._mock_lookup(part_number)

    def _parse_response(self, part_number: str, html: str) -> Optional[ServerPart]:
        """解析捷普官网 HTML 响应 / Parse Jabil HTML response."""
        specs = extract_specs_from_html(html)
        if not specs:
            return None
        cat = infer_category_from_specs(specs)
        now = utc_now()
        return ServerPart(
            part_number=part_number, manufacturer="JABIL", manufacturer_zh=self.name_zh,
            oem_brand=self.oem_brands[0], category=cat,
            category_zh=CATEGORIES.get(cat, "\u5176\u4ed6"),
            description=f"Jabil ODM part {part_number}",
            description_zh=f"\u6377\u666e ODM \u96f6\u4ef6 {part_number}",
            specifications={}, raw_specifications=specs,
            sources=[PriceSource(
                source_name="Jabil_Official", source_name_zh="\u6377\u666e\u5b98\u7f51",
                url=self.source_url, last_seen=now, reliability_score=self.reliability_score,
            )],
            confidence_score=0.6, last_updated=now,
        )

    def search_by_spec(self, **specs: Any) -> List[ServerPart]:
        """按规格参数搜索捷普零件 / Search Jabil parts by specifications.

        Returns:
            \u7a7a\u5217\u8868 / Empty list.
        """
        return []

    def _mock_lookup(self, part_number: str) -> ServerPart:
        """生成 Mock 查询结果 / Generate mock lookup result.

        Args:
            part_number: 零件号 / Part number.

        Returns:
            Mock ServerPart instance.
        """
        cat, cat_zh, _ = infer_category_from_text(part_number)
        return make_mock_part(
            part_number=part_number, manufacturer="JABIL", manufacturer_zh=self.name_zh,
            category=cat, category_zh=cat_zh, oem_brand=self.oem_brands[0],
            description=f"Jabil ODM part {part_number}",
            description_zh=f"\u6377\u666e ODM \u96f6\u4ef6 {part_number}\uff08\u6a21\u62df\u6570\u636e\uff09",
        )
