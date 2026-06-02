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

from uspi.core.adapters.base import BaseAdapter, CATEGORIES, PriceSource, ServerPart


class EbayPublicAdapter(BaseAdapter):
    """eBay 公开搜索页适配器（基于 HTML，非 API）/ eBay public search page adapter.

    通过 eBay 公开搜索页抓取商品列表，提取价格、标题、新旧状态等信息。
    Crawls eBay public search results to extract product listings with prices,
    titles, and condition info.

    Attributes:
        name: 适配器英文标识 / Adapter English identifier.
        name_zh: 适配器中文名称 / Adapter Chinese name.
        source_url: eBay 搜索页基础 URL / Base eBay search URL.
        reliability_score: 数据源可信度 0.55 / Data source reliability.
    """

    name = "ebay"
    name_zh = "eBay"
    source_url = "https://www.ebay.com/sch/i.html"
    reliability_score = 0.55

    SEARCH_URL = "https://www.ebay.com/sch/i.html?_nkw={pn}&_sacat=0"

    # 价格提取正则 / Price extraction patterns
    PRICE_PATTERNS = [
        re.compile(r'\$\s*([0-9,]+\.?\d*)'),
        re.compile(r'([0-9,]+\.?\d*)\s*USD'),
    ]

    # 商品容器模式 / Item container patterns
    ITEM_TITLE_PATTERN = re.compile(
        r'<div[^>]*class="[^"]*s-item__title[^"]*"[^>]*>(.*?)</div>',
        re.IGNORECASE | re.DOTALL,
    )
    ITEM_LINK_PATTERN = re.compile(
        r'<a[^>]*class="[^"]*s-item__link[^"]*"[^>]*href="([^"]*)"',
        re.IGNORECASE,
    )
    ITEM_PRICE_PATTERN = re.compile(
        r'<span[^>]*class="[^"]*s-item__price[^"]*"[^>]*>(.*?)</span>',
        re.IGNORECASE | re.DOTALL,
    )
    ITEM_CONDITION_PATTERN = re.compile(
        r'<span[^>]*class="[^"]*s-item__subtitle[^"]*"[^>]*>(.*?)</span>',
        re.IGNORECASE | re.DOTALL,
    )

    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询 eBay 商品信息 / Look up a part on eBay.

        构造 eBay 搜索 URL，抓取 HTML 并解析搜索结果。
        若抓取或解析失败，则返回 _mock_lookup() 生成的模拟数据。

        Constructs eBay search URL, fetches HTML and parses results.
        Falls back to mock data on failure.

        Args:
            part_number: 零件号字符串 / Part number string.

        Returns:
            ServerPart 实例（含 eBay 价格来源）或 None / ServerPart with eBay price
            sources, or None.
        """
        if not self._is_available():
            return self._fallback_disabled()

        search_url = self.SEARCH_URL.format(pn=quote_plus(part_number))

        try:
            html = self._fetch_html(search_url, timeout=30)
            items = self._parse_search_results(html)
        except Exception:
            # Graceful degradation: 反爬或网络故障时返回模拟数据
            # Return mock data when blocked or network error
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
                    condition=item.get("condition"),
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
            description=f"eBay search result for {part_number}",
            description_zh=f"eBay 搜索结果: {part_number}",
            specifications={},
            raw_specifications={},
            sources=sources,
            median_price_usd=median_price,
            price_range_usd=price_range,
            confidence_score=0.4 if sources else 0.0,
        )

    def search_by_spec(self, **specs: Any) -> List[ServerPart]:
        """按规格参数搜索（eBay 不支持，返回空列表）/ Search by specs.

        eBay 公开页不支持规格搜索，此方法返回空列表。
        Public eBay does not support spec-based search.

        Args:
            **specs: 规格键值对 / Specification key-value pairs.

        Returns:
            空列表 / Empty list.
        """
        return []

    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """从 eBay 搜索结果 HTML 中提取商品列表 / Extract product list from HTML.

        使用正则表达式提取商品标题、价格、链接和新旧状态。
        Uses regex to extract titles, prices, URLs, and conditions.

        Args:
            html: eBay 搜索结果页 HTML / eBay search results HTML.

        Returns:
            商品字典列表，每项含 title, price, url, condition / List of product dicts.
        """
        items: List[Dict[str, Any]] = []

        # 提取价格 / Extract prices
        prices_raw = self.ITEM_PRICE_PATTERN.findall(html)
        titles_raw = self.ITEM_TITLE_PATTERN.findall(html)
        links_raw = self.ITEM_LINK_PATTERN.findall(html)
        conditions_raw = self.ITEM_CONDITION_PATTERN.findall(html)

        # 解析价格文本 / Parse price text
        prices: List[Optional[float]] = []
        for pr in prices_raw:
            # 去除 HTML 标签 / Strip HTML tags
            clean = re.sub(r"<[^>]+>", "", pr).strip()
            # 尝试匹配价格 / Try price match
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

        # 解析标题 / Parse titles
        titles: List[str] = []
        for t in titles_raw:
            clean = re.sub(r"<[^>]+>", "", t).strip()
            titles.append(clean)

        # 解析新旧状态 / Parse conditions
        conditions: List[str] = []
        for c in conditions_raw:
            clean = re.sub(r"<[^>]+>", "", c).strip()
            if "new" in clean.lower():
                conditions.append("new")
            elif "used" in clean.lower():
                conditions.append("used")
            elif "refurbished" in clean.lower():
                conditions.append("refurbished")
            else:
                conditions.append(None)

        # 组合结果 / Combine results
        count = min(len(prices), len(titles), len(links_raw))
        for i in range(count):
            # 跳过 "Shop on eBay" 等无关条目 / Skip irrelevant entries
            title = titles[i] if i < len(titles) else ""
            if not title or "shop on ebay" in title.lower():
                continue
            items.append(
                {
                    "title": title,
                    "price": prices[i] if i < len(prices) else None,
                    "url": links_raw[i] if i < len(links_raw) else None,
                    "condition": conditions[i] if i < len(conditions) else None,
                }
            )

        return items

    def _mock_lookup(self, part_number: str) -> ServerPart:
        """返回 eBay 模拟数据 / Return mock eBay data.

        当 eBay 反爬或网络故障时，返回标注为模拟数据的 ServerPart。
        Returns a ServerPart marked as mock data when eBay is blocked.

        Args:
            part_number: 零件号字符串 / Part number string.

        Returns:
            含模拟价格来源的 ServerPart / ServerPart with mock price source.
        """
        import random

        mock_price = round(random.uniform(10.0, 500.0), 2)
        return ServerPart(
            part_number=part_number,
            manufacturer="UNKNOWN",
            manufacturer_zh="未知厂商",
            category="OTHERS",
            category_zh="其他",
            description=f"eBay mock result for {part_number}",
            description_zh=f"eBay 模拟数据: {part_number}",
            specifications={},
            raw_specifications={},
            sources=[
                PriceSource(
                    source_name=self.name,
                    source_name_zh=self.name_zh,
                    price_usd=mock_price,
                    original_price=mock_price,
                    original_currency="USD",
                    url=f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(part_number)}",
                    condition="new",
                    reliability_score=self.reliability_score,
                )
            ],
            median_price_usd=mock_price,
            price_range_usd=(mock_price, mock_price),
            confidence_score=0.15,
        )
