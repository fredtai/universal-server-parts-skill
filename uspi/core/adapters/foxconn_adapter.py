"""
uspi/core/adapters/foxconn_adapter.py

鸿海/富士康 (Foxconn) ODM 适配器 / Foxconn ODM Adapter.

Foxconn（鸿海精密工业）是全球最大的电子代工制造商之一，
为 DELL、HP、APPLE 等品牌代工服务器及零部件。
Foxconn is the world's largest electronics contract manufacturer,
producing server parts for DELL, HP, APPLE, and others.
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


class _FoxconnSpecParser(HTMLParser):
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


class FoxconnAdapter(BaseAdapter):
    """鸿海/富士康 ODM 适配器 / Foxconn ODM adapter.

    Attributes:
        name: 适配器英文标识 / Adapter English code.
        name_zh: 适配器中文名 / Adapter Chinese name.
        source_url: 富士康官网 / Foxconn official website.
        reliability_score: 数据源可信度 (ODM 公开数据较少) / Data reliability.
        oem_brands: 可能代工的品牌列表 / Possible OEM brands.
        part_prefixes: 零件号前缀字典 / Part number prefixes.
    """

    name = "foxconn"
    name_zh = "鸿海/富士康"
    source_url = "https://www.foxconn.com"
    reliability_score = 0.65
    oem_brands = ["DELL", "HP", "APPLE"]
    part_prefixes = ["FOX", "HK"]

    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询富士康零件信息 / Look up a Foxconn part by part number.

        先检查适配器是否启用，再尝试从官网获取数据；
        若失败则返回 mock 推断结果，确保 skill 始终可用。

        Args:
            part_number: 零件号字符串 / Part number string.

        Returns:
            ServerPart 实例或 None / ServerPart instance or None.
        """
        if not self._is_available():
            return self._fallback_disabled()

        # 尝试从官网获取 / Try to fetch from official site
        try:
            url = f"{self.source_url}/search?q={part_number}"
            html = self._fetch_html(url, timeout=10)
            if html and len(html) > 100:
                return self._parse_lookup_response(part_number, html)
        except Exception:
            # 抓取失败时优雅降级到 mock / Graceful fallback to mock
            pass

        return self._mock_lookup(part_number)

    def _parse_lookup_response(self, part_number: str, html: str) -> Optional[ServerPart]:
        """解析富士康官网 HTML 响应 / Parse Foxconn official HTML response.

        Args:
            part_number: 零件号 / Part number.
            html: HTML 文本 / HTML text content.

        Returns:
            ServerPart 或 None / ServerPart or None if parsing fails.
        """
        parser = _FoxconnSpecParser()
        parser.feed(html)
        if not parser.specs:
            return None

        # 从解析到的规格构建 ServerPart / Build ServerPart from parsed specs
        category = self._infer_category_from_specs(parser.specs)
        return ServerPart(
            part_number=part_number,
            manufacturer="FOXCONN",
            manufacturer_zh=self.name_zh,
            oem_brand=self.oem_brands[0],
            category=category,
            category_zh=CATEGORIES.get(category, "其他"),
            description=f"Foxconn ODM part {part_number}",
            description_zh=f"鸿海/富士康 ODM 零件 {part_number}",
            specifications={},
            raw_specifications=parser.specs,
            sources=[
                PriceSource(
                    source_name="Foxconn_Official",
                    source_name_zh="富士康官网",
                    url=self.source_url,
                    reliability_score=self.reliability_score,
                )
            ],
            confidence_score=0.6,
        )

    def search_by_spec(self, **specs: Any) -> List[ServerPart]:
        """按规格参数搜索富士康零件 / Search Foxconn parts by specifications.

        ODM 公开规格搜索能力有限，当前返回 mock 示例列表。
        Public ODM spec search is limited; returns mock sample list.

        Args:
            **specs: 规格键值对 / Specification key-value pairs.

        Returns:
            ServerPart 列表 / List of ServerPart instances.
        """
        if not self._is_available():
            return []

        # Mock: 返回几个典型零件 / Return a few representative parts
        mock_parts = [
            self._mock_lookup("FOX12345678"),
            self._mock_lookup("HK87654321"),
        ]
        return [p for p in mock_parts if p is not None]

    def _mock_lookup(self, part_number: str) -> Optional[ServerPart]:
        """生成 Mock 查询结果 / Generate mock lookup result.

        使用 PartParser 基于零件号模式推断厂商和分类，
        用于官网不可用时保证 skill 始终可用。

        Args:
            part_number: 零件号 / Part number.

        Returns:
            ServerPart 实例（mock） / Mock ServerPart instance.
        """
        parser = PartParser()
        parsed = parser.parse(part_number)

        # 确定分类 / Determine category
        category = parsed.category if parsed.category else "OTHERS"
        category_zh = parsed.category_zh if parsed.category_zh else "其他"

        # 确定代工品牌 / Determine OEM brand
        oem_brand = parsed.oem_brand if parsed.oem_brand else self.oem_brands[0]

        return ServerPart(
            part_number=part_number,
            manufacturer="FOXCONN",
            manufacturer_zh=self.name_zh,
            oem_brand=oem_brand,
            category=category,
            category_zh=category_zh,
            description=f"Foxconn ODM part (inferred from pattern)",
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
        return "OTHERS"
