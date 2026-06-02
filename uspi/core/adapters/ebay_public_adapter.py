"""
uspi/core/adapters/ebay_public_adapter.py
eBay 公开搜索页适配器 / eBay Public Search Page Adapter

基于 eBay 公开搜索页 HTML 解析（非 API），提取商品价格、标题、状态等信息。
Uses public eBay search page HTML parsing (not API) to extract product prices,
titles, conditions, and URLs.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from uspi.core.adapters.base import BaseAdapter, PriceSource, ServerPart
from uspi.core.adapters._common import clean_html_text, make_market_mock_part, utc_now


class EbayPublicAdapter(BaseAdapter):
    """eBay 公开搜索页适配器 / eBay public search page adapter.

    Attributes:
        name: 适配器英文标识 / Adapter English identifier.
        name_zh: 适配器中文名称 / Adapter Chinese name.
        source_url: eBay 搜索页基础 URL / Base eBay search URL.
        reliability_score: 数据源可信度 0.55 / Data source reliability.
    """

    name = "ebay"
    name_zh = "eBay"
    source_url = "https://www.ebay.com"
    reliability_score = 0.55

    SEARCH_URL = "https://www.ebay.com/sch/i.html?_nkw={pn}"

    # 正则模式 / Regex patterns
    PRICE_PATTERNS = [
        re.compile(r'\$\s*([0-9,]+\.?\d*)'),
        re.compile(r'([0-9,]+\.?\d*)\s*USD'),
    ]
    ITEM_PRICE_PATTERN = re.compile(
        r'<span[^>]*class="[^"]*s-item__price[^"]*"[^>]*>(.*?)</span>',
        re.IGNORECASE | re.DOTALL,
    )
    ITEM_TITLE_PATTERN = re.compile(
        r'<div[^>]*class="[^"]*s-item__title[^"]*"[^>]*>(.*?)</div>',
        re.IGNORECASE | re.DOTALL,
    )
    ITEM_LINK_PATTERN = re.compile(
        r'<a[^>]*class="[^"]*s-item__link[^"]*"[^>]*href="([^"]*)"',
        re.IGNORECASE,
    )
    ITEM_CONDITION_PATTERN = re.compile(
        r'<span[^>]*class="[^"]*s-item__subtitle[^"]*"[^>]*>(.*?)</span>',
        re.IGNORECASE | re.DOTALL,
    )

    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询 eBay 商品信息 / Look up a part on eBay."""
        if not part_number or not isinstance(part_number, str):
            return None
        if not self._is_available():
            return self._fallback_disabled()

        try:
            html = self._fetch_html(self.SEARCH_URL.format(pn=quote_plus(part_number)), timeout=30)
            items = self._parse_search_results(html)
        except Exception:
            return self._mock_lookup(part_number)

        if not items:
            return self._mock_lookup(part_number)

        return self._build_server_part(part_number, items)

    def search_by_spec(self, **specs: Any) -> List[ServerPart]:
        """按规格参数搜索（eBay 不支持，返回空列表）/ Search by specs."""
        return []

    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """从 eBay 搜索结果 HTML 中提取商品列表 / Extract product list from HTML."""
        items: List[Dict[str, Any]] = []
        prices_raw = self.ITEM_PRICE_PATTERN.findall(html)
        titles_raw = self.ITEM_TITLE_PATTERN.findall(html)
        links_raw = self.ITEM_LINK_PATTERN.findall(html)
        conditions_raw = self.ITEM_CONDITION_PATTERN.findall(html)

        prices: List[Optional[float]] = []
        for pr in prices_raw:
            clean = clean_html_text(pr)
            matched: Optional[float] = None
            for pat in self.PRICE_PATTERNS:
                m = pat.search(clean)
                if m:
                    try:
                        matched = float(m.group(1).replace(",", ""))
                        break
                    except ValueError:
                        continue
            prices.append(matched)

        titles = [clean_html_text(t) for t in titles_raw]
        conditions = []
        for c in conditions_raw:
            clean = clean_html_text(c).lower()
            conditions.append(
                "new" if "new" in clean else "used" if "used" in clean
                else "refurbished" if "refurbished" in clean else None
            )

        count = min(len(prices), len(titles), len(links_raw))
        for i in range(count):
            title = titles[i] if i < len(titles) else ""
            if not title or "shop on ebay" in title.lower():
                continue
            items.append({
                "title": title,
                "price": prices[i] if i < len(prices) else None,
                "url": links_raw[i] if i < len(links_raw) else None,
                "condition": conditions[i] if i < len(conditions) else None,
            })

        return items

    def _build_server_part(self, part_number: str, items: List[Dict[str, Any]]) -> ServerPart:
        """从解析的商品列表构建 ServerPart / Build ServerPart from parsed items."""
        sources = []
        prices = []
        now = utc_now()
        for item in items[:5]:
            price = item.get("price")
            if price and price > 0:
                prices.append(price)
            sources.append(PriceSource(
                source_name=self.name, source_name_zh=self.name_zh,
                price_usd=price, original_price=item.get("price"),
                original_currency="USD", url=item.get("url"),
                condition=item.get("condition"), last_seen=now,
                reliability_score=self.reliability_score,
            ))

        median_price, price_range = self._calc_price_stats(prices)
        return ServerPart(
            part_number=part_number, manufacturer="UNKNOWN", manufacturer_zh="\u672a\u77e5\u5382\u5546",
            category="OTHERS", category_zh="\u5176\u4ed6",
            description=f"eBay search result for {part_number}",
            description_zh=f"eBay \u641c\u7d22\u7ed3\u679c: {part_number}",
            specifications={}, raw_specifications={}, sources=sources,
            median_price_usd=median_price, price_range_usd=price_range,
            confidence_score=0.4 if sources else 0.0, last_updated=now,
        )

    def _mock_lookup(self, part_number: str) -> ServerPart:
        """返回 eBay 模拟数据 / Return mock eBay data."""
        return make_market_mock_part(
            self.name, self.name_zh, part_number, self.reliability_score,
            f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(part_number)}",
            price_low=10.0, price_high=500.0,
        )

    @staticmethod
    def _calc_price_stats(prices: List[float]) -> tuple:
        """计算价格统计 / Calculate price statistics."""
        if not prices:
            return None, None
        prices_sorted = sorted(prices)
        n = len(prices_sorted)
        median = prices_sorted[n // 2] if n % 2 == 1 else (
            prices_sorted[n // 2 - 1] + prices_sorted[n // 2]) / 2
        return median, (min(prices), max(prices))
