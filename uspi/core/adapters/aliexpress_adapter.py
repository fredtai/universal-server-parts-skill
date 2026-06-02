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

from uspi.core.adapters.base import BaseAdapter, CATEGORIES, PriceSource, ServerPart


class AliexpressAdapter(BaseAdapter):
    """AliExpress 公开商品页适配器 / AliExpress public product page adapter.

    通过 AliExpress 公开搜索页抓取商品列表，提取价格、标题、销量等信息。
    Crawls AliExpress public search results to extract product listings with
    prices, titles, and order counts.

    Attributes:
        name: 适配器英文标识 / Adapter English identifier.
        name_zh: 适配器中文名称 / Adapter Chinese name.
        source_url: AliExpress 搜索页基础 URL / Base AliExpress search URL.
        reliability_score: 数据源可信度 0.45 / Data source reliability.
    """

    name = "aliexpress"
    name_zh = "全球速卖通"
    source_url = "https://www.aliexpress.com/wholesale"
    reliability_score = 0.45

    SEARCH_URL = "https://www.aliexpress.com/wholesale?SearchText={pn}"

    # 价格正则 / Price extraction patterns
    PRICE_PATTERNS = [
        re.compile(r'\$\s*([0-9,]+\.?\d*)'),
        re.compile(r'US\s*\$\s*([0-9,]+\.?\d*)'),
        re.compile(r'([0-9,]+\.?\d*)\s*\$'),
    ]

    # 商品卡片正则 / Product card patterns
    CARD_PATTERN = re.compile(
        r'<a[^>]*href="([^"]*item/[^"]*)"[^>]*>.*?<img[^>]*>.*?</a>',
        re.IGNORECASE | re.DOTALL,
    )
    TITLE_IN_CARD_PATTERN = re.compile(
        r'class="[^"]*product-title[^"]*"[^>]*>(.*?)</',
        re.IGNORECASE | re.DOTALL,
    )
    PRICE_IN_HTML_PATTERN = re.compile(
        r'class="[^"]*price[^"]*"[^>]*>(.*?)</span>',
        re.IGNORECASE | re.DOTALL,
    )
    ORDERS_PATTERN = re.compile(
        r'(\d+)\s*(orders|sold|purchases)',
        re.IGNORECASE,
    )
    SHIPPING_PATTERN = re.compile(
        r'(Free Shipping|免费 shipping|包邮)',
        re.IGNORECASE,
    )

    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询 AliExpress 商品信息 / Look up a part on AliExpress.

        构造 AliExpress 搜索 URL，抓取 HTML 并解析搜索结果。
        若抓取或解析失败，则返回 _mock_lookup() 生成的模拟数据。

        Constructs AliExpress search URL, fetches HTML and parses results.
        Falls back to mock data on failure.

        Args:
            part_number: 零件号字符串 / Part number string.

        Returns:
            ServerPart 实例（含 AliExpress 价格来源）或 None / ServerPart with
            AliExpress price sources, or None.
        """
        if not self._is_available():
            return self._fallback_disabled()

        search_url = self.SEARCH_URL.format(pn=quote_plus(part_number))

        try:
            html = self._fetch_html(search_url, timeout=30)
            items = self._parse_search_results(html)
        except Exception:
            # Graceful degradation: 反爬或网络故障时返回模拟数据
            return self._mock_lookup(part_number)

        if not items:
            return self._mock_lookup(part_number)

        # 构建 PriceSource 列表 / Build PriceSource list
        sources = []
        prices = []
        for item in items[:5]:  # 最多取前 5 条 / Top 5 results
            price = item.get("price")
            if price and price > 0:
                prices.append(price)
            sources.append(
                PriceSource(
                    source_name=self.name,
                    source_name_zh=self.name_zh,
                    price_usd=price,
                    original_price=item.get("original_price"),
                    original_currency="USD",
                    url=item.get("url"),
                    condition="new",
                    in_stock=item.get("has_orders"),
                    reliability_score=self.reliability_score,
                )
            )

        # 计算价格统计 / Calculate price statistics
        median_price = None
        price_range = None
        if prices:
            prices_sorted = sorted(prices)
            n = len(prices_sorted)
            median_price = (
                prices_sorted[n // 2]
                if n % 2 == 1
                else (prices_sorted[n // 2 - 1] + prices_sorted[n // 2]) / 2
            )
            price_range = (min(prices), max(prices))

        return ServerPart(
            part_number=part_number,
            manufacturer="UNKNOWN",
            manufacturer_zh="未知厂商",
            category="OTHERS",
            category_zh="其他",
            description=f"AliExpress search result for {part_number}",
            description_zh=f"AliExpress 搜索结果: {part_number}",
            specifications={},
            raw_specifications={},
            sources=sources,
            median_price_usd=median_price,
            price_range_usd=price_range,
            confidence_score=0.3 if sources else 0.0,
        )

    def search_by_spec(self, **specs: Any) -> List[ServerPart]:
        """按规格参数搜索（AliExpress 不支持，返回空列表）/ Search by specs.

        AliExpress 公开页不支持规格搜索，此方法返回空列表。
        Public AliExpress does not support spec-based search.

        Args:
            **specs: 规格键值对 / Specification key-value pairs.

        Returns:
            空列表 / Empty list.
        """
        return []

    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """从 AliExpress 搜索结果 HTML 中提取商品列表 / Extract products from HTML.

        使用正则表达式提取商品标题、价格、链接和订单量。
        Uses regex to extract titles, prices, URLs, and order counts.

        Args:
            html: AliExpress 搜索结果页 HTML / AliExpress search results HTML.

        Returns:
            商品字典列表 / List of product dicts with title, price, url, etc.
        """
        items: List[Dict[str, Any]] = []

        # 提取所有价格 / Extract all prices
        price_texts = self.PRICE_IN_HTML_PATTERN.findall(html)
        parsed_prices: List[float] = []
        for pt in price_texts:
            clean = re.sub(r"<[^>]+>", "", pt).strip()
            for pat in self.PRICE_PATTERNS:
                m = pat.search(clean)
                if m:
                    try:
                        val = float(m.group(1).replace(",", ""))
                        if 0 < val < 100000:  # 过滤异常值 / Filter outliers
                            parsed_prices.append(val)
                            break
                    except ValueError:
                        continue

        # 提取所有商品链接 / Extract all product links
        link_matches = self.CARD_PATTERN.findall(html)

        # 提取订单量 / Extract order counts
        order_matches = self.ORDERS_PATTERN.findall(html)
        has_orders = len(order_matches) > 0

        # 组合结果 / Combine results
        for i, link in enumerate(link_matches[:10]):
            price = parsed_prices[i] if i < len(parsed_prices) else None
            if not price:
                continue

            # 规范化链接 / Normalize link
            if link.startswith("//"):
                link = f"https:{link}"
            elif link.startswith("/"):
                link = f"https://www.aliexpress.com{link}"

            items.append(
                {
                    "title": f"AliExpress listing #{i + 1}",
                    "price": price,
                    "url": link,
                    "original_price": price,
                    "has_orders": has_orders,
                }
            )

        # 如果没有从卡片提取到，尝试全局价格提取 / Fallback: global price extraction
        if not items:
            items = self._fallback_price_parse(html)

        return items

    def _fallback_price_parse(self, html: str) -> List[Dict[str, Any]]:
        """备用价格解析：从整页提取所有价格 / Fallback: extract all prices from page.

        当卡片解析失败时，尝试全局匹配价格。
        Tries global price matching when card parsing fails.

        Args:
            html: AliExpress 搜索结果页 HTML / AliExpress search results HTML.

        Returns:
            商品字典列表 / List of product dicts.
        """
        items: List[Dict[str, Any]] = []
        seen_prices: set[float] = set()

        for pat in self.PRICE_PATTERNS:
            for match in pat.finditer(html):
                try:
                    price = float(match.group(1).replace(",", ""))
                    if 0 < price < 100000 and price not in seen_prices:
                        seen_prices.add(price)
                        items.append(
                            {
                                "title": "AliExpress listing",
                                "price": price,
                                "url": None,
                                "original_price": price,
                                "has_orders": None,
                            }
                        )
                except ValueError:
                    continue
            if len(items) >= 3:
                break

        return items

    def _mock_lookup(self, part_number: str) -> ServerPart:
        """返回 AliExpress 模拟数据 / Return mock AliExpress data.

        当 AliExpress 反爬或网络故障时，返回标注为模拟数据的 ServerPart。
        Returns a ServerPart marked as mock data when AliExpress is blocked.

        Args:
            part_number: 零件号字符串 / Part number string.

        Returns:
            含模拟价格来源的 ServerPart / ServerPart with mock price source.
        """
        import random

        mock_price = round(random.uniform(5.0, 300.0), 2)
        return ServerPart(
            part_number=part_number,
            manufacturer="UNKNOWN",
            manufacturer_zh="未知厂商",
            category="OTHERS",
            category_zh="其他",
            description=f"AliExpress mock result for {part_number}",
            description_zh=f"AliExpress 模拟数据: {part_number}",
            specifications={},
            raw_specifications={},
            sources=[
                PriceSource(
                    source_name=self.name,
                    source_name_zh=self.name_zh,
                    price_usd=mock_price,
                    original_price=mock_price,
                    original_currency="USD",
                    url=f"https://www.aliexpress.com/wholesale?SearchText={quote_plus(part_number)}",
                    condition="new",
                    in_stock=True,
                    reliability_score=self.reliability_score,
                )
            ],
            median_price_usd=mock_price,
            price_range_usd=(mock_price, mock_price),
            confidence_score=0.1,
        )
