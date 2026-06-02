"""
uspi/core/adapters/aliexpress_adapter.py
AliExpress 公开商品页适配器 / AliExpress Public Product Page Adapter

基于 AliExpress 公开搜索页 HTML 解析（非 API），提取商品价格、标题、销量等信息。
Uses public AliExpress search page HTML parsing (not API) to extract product
prices, titles, order counts, and store ratings.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from uspi.core.adapters.base import BaseAdapter, PriceSource, ServerPart
from uspi.core.adapters._common import clean_html_text, make_market_mock_part, utc_now


class AliexpressAdapter(BaseAdapter):
    """AliExpress 公开商品页适配器 / AliExpress public product page adapter.

    Attributes:
        name: 适配器英文标识 / Adapter English identifier.
        name_zh: 适配器中文名称 / Adapter Chinese name.
        source_url: AliExpress 搜索页基础 URL / Base AliExpress search URL.
        reliability_score: 数据源可信度 0.45 / Data source reliability.
    """

    name = "aliexpress"
    name_zh = "\u5168\u7403\u901f\u5356\u901a"
    source_url = "https://www.aliexpress.com"
    reliability_score = 0.45

    SEARCH_URL = "https://www.aliexpress.com/wholesale?SearchText={pn}"

    # 正则模式 / Regex patterns
    PRICE_PATTERNS = [
        re.compile(r'\$\s*([0-9,]+\.?\d*)'),
        re.compile(r'US\s*\$\s*([0-9,]+\.?\d*)'),
        re.compile(r'([0-9,]+\.?\d*)\s*\$'),
    ]
    CARD_PATTERN = re.compile(
        r'<a[^>]*href="([^"]*item/[^"]*)"[^>]*>.*?<img[^>]*>.*?</a>',
        re.IGNORECASE | re.DOTALL,
    )
    PRICE_IN_HTML_PATTERN = re.compile(
        r'class="[^"]*price[^"]*"[^>]*>(.*?)</span>', re.IGNORECASE | re.DOTALL,
    )
    ORDERS_PATTERN = re.compile(r'(\d+)\s*(orders|sold)', re.IGNORECASE)

    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询 AliExpress 商品信息 / Look up a part on AliExpress."""
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
        """按规格参数搜索（AliExpress 不支持，返回空列表）/ Search by specs."""
        return []

    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """从 AliExpress 搜索结果 HTML 中提取商品列表 / Extract products from HTML."""
        items: List[Dict[str, Any]] = []
        price_texts = self.PRICE_IN_HTML_PATTERN.findall(html)
        parsed_prices: List[float] = []
        for pt in price_texts:
            clean = clean_html_text(pt)
            for pat in self.PRICE_PATTERNS:
                m = pat.search(clean)
                if m:
                    try:
                        val = float(m.group(1).replace(",", ""))
                        if 0 < val < 100000:
                            parsed_prices.append(val)
                            break
                    except ValueError:
                        continue

        link_matches = self.CARD_PATTERN.findall(html)
        has_orders = bool(self.ORDERS_PATTERN.search(html))

        for i, link in enumerate(link_matches[:10]):
            price = parsed_prices[i] if i < len(parsed_prices) else None
            if not price:
                continue
            if link.startswith("//"):
                link = f"https:{link}"
            elif link.startswith("/"):
                link = f"https://www.aliexpress.com{link}"
            items.append({
                "title": f"AliExpress listing #{i + 1}", "price": price,
                "url": link, "original_price": price, "has_orders": has_orders,
            })

        return items if items else self._fallback_price_parse(html)

    def _fallback_price_parse(self, html: str) -> List[Dict[str, Any]]:
        """备用价格解析：从整页提取所有价格 / Fallback: extract all prices from page."""
        items: List[Dict[str, Any]] = []
        seen: set[float] = set()
        for pat in self.PRICE_PATTERNS:
            for match in pat.finditer(html):
                try:
                    price = float(match.group(1).replace(",", ""))
                    if 0 < price < 100000 and price not in seen:
                        seen.add(price)
                        items.append({
                            "title": "AliExpress listing", "price": price,
                            "url": None, "original_price": price, "has_orders": None,
                        })
                except ValueError:
                    continue
            if len(items) >= 3:
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
                condition="new", in_stock=item.get("has_orders"),
                last_seen=now, reliability_score=self.reliability_score,
            ))

        median_price, price_range = self._calc_price_stats(prices)
        return ServerPart(
            part_number=part_number, manufacturer="UNKNOWN", manufacturer_zh="\u672a\u77e5\u5382\u5546",
            category="OTHERS", category_zh="\u5176\u4ed6",
            description=f"AliExpress search result for {part_number}",
            description_zh=f"AliExpress \u641c\u7d22\u7ed3\u679c: {part_number}",
            specifications={}, raw_specifications={}, sources=sources,
            median_price_usd=median_price, price_range_usd=price_range,
            confidence_score=0.3 if sources else 0.0, last_updated=now,
        )

    def _mock_lookup(self, part_number: str) -> ServerPart:
        """返回 AliExpress 模拟数据 / Return mock AliExpress data."""
        return make_market_mock_part(
            self.name, self.name_zh, part_number, self.reliability_score,
            f"https://www.aliexpress.com/wholesale?SearchText={quote_plus(part_number)}",
            price_low=5.0, price_high=300.0,
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
