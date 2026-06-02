"""
uspi/core/adapters/amazon_public_adapter.py
Amazon 公开商品页适配器 / Amazon Public Product Page Adapter

基于 Amazon 公开搜索页 HTML 解析（非 API），提取商品价格、标题、评分等信息。
Uses public Amazon search page HTML parsing (not API) to extract product prices,
titles, ratings, and availability.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from uspi.core.adapters.base import BaseAdapter, PriceSource, ServerPart
from uspi.core.adapters._common import clean_html_text, make_market_mock_part, utc_now


class AmazonPublicAdapter(BaseAdapter):
    """Amazon 公开商品页适配器 / Amazon public product page adapter.

    Attributes:
        name: 适配器英文标识 / Adapter English identifier.
        name_zh: 适配器中文名称 / Adapter Chinese name.
        source_url: Amazon 搜索页基础 URL / Base Amazon search URL.
        reliability_score: 数据源可信度 0.50 / Data source reliability.
    """

    name = "amazon"
    name_zh = "\u4e9a\u9a6c\u900a"
    source_url = "https://www.amazon.com"
    reliability_score = 0.50

    SEARCH_URL = "https://www.amazon.com/s?k={pn}"

    # 正则模式 / Regex patterns
    PRICE_PATTERNS = [
        re.compile(r'\$\s*([0-9,]+\.?\d*)'),
        re.compile(r'([0-9,]+\.?\d*)\s*\$'),
    ]
    RESULT_BLOCK_PATTERN = re.compile(
        r'<div[^>]*data-component-type="s-search-result"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        re.IGNORECASE | re.DOTALL,
    )
    TITLE_PATTERN = re.compile(
        r'<h2[^>]*>.*?<a[^>]*>(.*?)</a>.*?</h2>', re.IGNORECASE | re.DOTALL,
    )
    LINK_PATTERN = re.compile(
        r'<h2[^>]*>.*?<a[^>]*href="([^"]*)"', re.IGNORECASE | re.DOTALL,
    )
    PRICE_BLOCK_PATTERN = re.compile(
        r'<span[^>]*class="[^"]*a-price[^"]*"[^>]*>.*?<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>(.*?)</span>',
        re.IGNORECASE | re.DOTALL,
    )
    IN_STOCK_PATTERN = re.compile(r'(In Stock|Available|Delivery)', re.IGNORECASE)

    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询 Amazon 商品信息 / Look up a part on Amazon."""
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
        """按规格参数搜索（Amazon 不支持，返回空列表）/ Search by specs."""
        return []

    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """从 Amazon 搜索结果 HTML 中提取商品列表 / Extract products from HTML."""
        items: List[Dict[str, Any]] = []
        blocks = self.RESULT_BLOCK_PATTERN.findall(html)

        if not blocks:
            return self._fallback_parse(html)

        for block in blocks[:10]:
            title_match = self.TITLE_PATTERN.search(block)
            title = clean_html_text(title_match.group(1)) if title_match else ""

            link_match = self.LINK_PATTERN.search(block)
            url = None
            if link_match:
                href = link_match.group(1)
                url = f"https://www.amazon.com{href}" if href.startswith("/") else href

            price_match = self.PRICE_BLOCK_PATTERN.search(block)
            price: Optional[float] = None
            if price_match:
                price_text = clean_html_text(price_match.group(1))
                for pat in self.PRICE_PATTERNS:
                    m = pat.search(price_text)
                    if m:
                        try:
                            price = float(m.group(1).replace(",", ""))
                            break
                        except ValueError:
                            continue

            if title and price and price > 0:
                items.append({
                    "title": title, "price": price, "url": url,
                    "in_stock": bool(self.IN_STOCK_PATTERN.search(block)),
                    "original_price": price,
                })

        return items

    def _fallback_parse(self, html: str) -> List[Dict[str, Any]]:
        """备用解析：从整页 HTML 中提取价格信息 / Fallback: extract prices from full page."""
        items: List[Dict[str, Any]] = []
        for pat in self.PRICE_PATTERNS:
            for match in pat.finditer(html):
                try:
                    price = float(match.group(1).replace(",", ""))
                    if 0 < price < 100000:
                        items.append({
                            "title": "Amazon listing", "price": price,
                            "url": None, "in_stock": None, "original_price": price,
                        })
                except ValueError:
                    continue
            if items:
                break
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
                price_usd=price, original_price=item.get("original_price"),
                original_currency="USD", url=item.get("url"),
                condition="new" if item.get("in_stock") else None,
                in_stock=item.get("in_stock"), last_seen=now,
                reliability_score=self.reliability_score,
            ))

        median_price, price_range = self._calc_price_stats(prices)
        return ServerPart(
            part_number=part_number, manufacturer="UNKNOWN", manufacturer_zh="\u672a\u77e5\u5382\u5546",
            category="OTHERS", category_zh="\u5176\u4ed6",
            description=f"Amazon search result for {part_number}",
            description_zh=f"Amazon \u641c\u7d22\u7ed3\u679c: {part_number}",
            specifications={}, raw_specifications={}, sources=sources,
            median_price_usd=median_price, price_range_usd=price_range,
            confidence_score=0.35 if sources else 0.0, last_updated=now,
        )

    def _mock_lookup(self, part_number: str) -> ServerPart:
        """返回 Amazon 模拟数据 / Return mock Amazon data."""
        return make_market_mock_part(
            self.name, self.name_zh, part_number, self.reliability_score,
            f"https://www.amazon.com/s?k={quote_plus(part_number)}",
            price_low=15.0, price_high=600.0,
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
