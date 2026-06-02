"""
uspi/core/adapters/jabil_adapter.py

捷普 (Jabil) ODM 适配器 / Jabil ODM Adapter.

捷普电子是全球领先的电子制造服务厂商，
为 CISCO、HP、JUNIPER 等品牌代工网络及服务器设备。
Jabil is a leading electronic manufacturing services company,
producing networking and server equipment for CISCO, HP, JUNIPER, and others.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

from uspi.core.adapters.base import BaseAdapter, CATEGORIES, PriceSource, ServerPart
from uspi.core.parser import PartParser


# ---------------------------------------------------------------------------
# HTML 解析辅助 / HTML parsing helpers
# ---------------------------------------------------------------------------


class _JabilSpecParser(HTMLParser):
    """轻量级 HTML 规格表提取器 / Lightweight HTML spec table extractor."""

    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.current_tag: Optional[str] = None
        self.specs: Dict[str, str] = {}
        self._current_key: Optional[str] = None
        self._buffer = ""

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self.current_tag = tag
        if tag in ("table", "div"):
            attr_dict = dict(attrs)
            if "spec" in attr_dict.get("class", "").lower():
                self.in_table = True

    def handle_data(self, data: str) -> None:
        if self.in_table and data.strip():
            self._buffer += data.strip()

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th", "div") and self._buffer:
            if self._current_key is None:
                self._current_key = self._buffer
            else:
                self.specs[self._current_key] = self._buffer
                self._current_key = None
            self._buffer = ""


# ---------------------------------------------------------------------------
# 适配器主体 / Adapter class
# ---------------------------------------------------------------------------


class JabilAdapter(BaseAdapter):
    """捷普 ODM 适配器 / Jabil ODM adapter.

    Attributes:
        name: 适配器英文标识 / Adapter English code.
        name_zh: 适配器中文名 / Adapter Chinese name.
        source_url: 捷普官网 / Jabil official website.
        reliability_score: 数据源可信度 (ODM 公开数据较少) / Data reliability.
        oem_brands: 可能代工的品牌列表 / Possible OEM brands.
        part_prefixes: 零件号前缀字典 / Part number prefixes.
    """

    name = "jabil"
    name_zh = "捷普"
    source_url = "https://www.jabil.com"
    reliability_score = 0.60
    oem_brands = ["CISCO", "HP", "JUNIPER"]
    part_prefixes = ["JBL", "J"]

    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询捷普零件信息 / Look up a Jabil part by part number.

        先检查适配器是否启用，再尝试从官网获取数据；
        若失败则返回 mock 推断结果，确保 skill 始终可用。

        Args:
            part_number: 零件号字符串 / Part number string.

        Returns:
            ServerPart 实例或 None / ServerPart instance or None.
        """
        if not self._is_available():
            return self._fallback_disabled()

        try:
            url = f"{self.source_url}/search?q={part_number}"
            html = self._fetch_html(url, timeout=10)
            if html and len(html) > 100:
                return self._parse_lookup_response(part_number, html)
        except Exception:
            pass

        return self._mock_lookup(part_number)

    def _parse_lookup_response(self, part_number: str, html: str) -> Optional[ServerPart]:
        """解析捷普官网 HTML 响应 / Parse Jabil official HTML response.

        Args:
            part_number: 零件号 / Part number.
            html: HTML 文本 / HTML text content.

        Returns:
            ServerPart 或 None / ServerPart or None if parsing fails.
        """
        parser = _JabilSpecParser()
        parser.feed(html)
        if not parser.specs:
            return None

        category = self._infer_category_from_specs(parser.specs)
        return ServerPart(
            part_number=part_number,
            manufacturer="JABIL",
            manufacturer_zh=self.name_zh,
            oem_brand=self.oem_brands[0],
            category=category,
            category_zh=CATEGORIES.get(category, "其他"),
            description=f"Jabil ODM part {part_number}",
            description_zh=f"捷普 ODM 零件 {part_number}",
            specifications={},
            raw_specifications=parser.specs,
            sources=[
                PriceSource(
                    source_name="Jabil_Official",
                    source_name_zh="捷普官网",
                    url=self.source_url,
                    reliability_score=self.reliability_score,
                )
            ],
            confidence_score=0.6,
        )

    def search_by_spec(self, **specs: Any) -> List[ServerPart]:
        """按规格参数搜索捷普零件 / Search Jabil parts by specifications.

        ODM 公开规格搜索能力有限，当前返回 mock 示例列表。

        Args:
            **specs: 规格键值对 / Specification key-value pairs.

        Returns:
            ServerPart 列表 / List of ServerPart instances.
        """
        if not self._is_available():
            return []

        mock_parts = [
            self._mock_lookup("JBL12345678"),
            self._mock_lookup("J87654321"),
        ]
        return [p for p in mock_parts if p is not None]

    def _mock_lookup(self, part_number: str) -> Optional[ServerPart]:
        """生成 Mock 查询结果 / Generate mock lookup result.

        使用 PartParser 基于零件号模式推断厂商和分类。

        Args:
            part_number: 零件号 / Part number.

        Returns:
            ServerPart 实例（mock） / Mock ServerPart instance.
        """
        parser = PartParser()
        parsed = parser.parse(part_number)

        category = parsed.category if parsed.category else "OTHERS"
        category_zh = parsed.category_zh if parsed.category_zh else "其他"
        oem_brand = parsed.oem_brand if parsed.oem_brand else self.oem_brands[0]

        return ServerPart(
            part_number=part_number,
            manufacturer="JABIL",
            manufacturer_zh=self.name_zh,
            oem_brand=oem_brand,
            category=category,
            category_zh=category_zh,
            description="Jabil ODM part (inferred from pattern)",
            description_zh="ODM 零件（公开数据有限，基于零件号模式推断）",
            specifications={},
            raw_specifications={},
            sources=[
                PriceSource(
                    source_name="ODM_Mock",
                    source_name_zh="ODM推断数据源",
                    url=None,
                    reliability_score=0.3,
                )
            ],
            median_price_usd=None,
            price_range_usd=None,
            confidence_score=0.3,
        )

    @staticmethod
    def _infer_category_from_specs(specs: Dict[str, str]) -> str:
        """从规格字典推断零件分类 / Infer part category from specifications.

        Args:
            specs: 原始规格字典 / Raw specification dictionary.

        Returns:
            分类键值 / Category key.
        """
        text = " ".join(f"{k} {v}" for k, v in specs.items()).upper()
        if any(kw in text for kw in ["DDR", "RDIMM", "LRDIMM", "MEMORY"]):
            return "MEMORY"
        if any(kw in text for kw in ["SSD", "SOLID STATE"]):
            return "STORAGE_SSD"
        if any(kw in text for kw in ["HDD", "HARD DRIVE", "SAS"]):
            return "STORAGE_HDD"
        if any(kw in text for kw in ["NVME", "NVMe"]):
            return "STORAGE_NVME"
        if any(kw in text for kw in ["POWER SUPPLY", "PSU", "WATT"]):
            return "PSU"
        if any(kw in text for kw in ["NIC", "ETHERNET", "NETWORK"]):
            return "NIC"
        if any(kw in text for kw in ["ROUTER", "SWITCH", "NETWORKING"]):
            return "NIC"
        if any(kw in text for kw in ["XEON", "EPYC", "PROCESSOR", "CPU"]):
            return "CPU"
        return "OTHERS"
