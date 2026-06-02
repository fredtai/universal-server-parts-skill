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

from uspi.core.adapters.base import BaseAdapter, CATEGORIES, PriceSource, ServerPart


class AmazonPublicAdapter(BaseAdapter):
    """Amazon 公开商品页适配器 / Amazon public product page adapter.

    通过 Amazon 公开搜索页抓取商品列表，提取价格、标题、配送等信息。
    Crawls Amazon public search results to extract product listings with prices,
    titles, and shipping info.

    Attributes:
        name: 适配器英文标识 / Adapter English identifier.
        name_zh: 适配器中文名称 / Adapter Chinese name.
        source_url: Amazon 搜索页基础 URL / Base Amazon search URL.
        reliability_score: 数据源可信度 0.50 / Data source reliability.
    """

    name = "amazon"
    name_zh = "亚马逊"
    source_url = "https://www.amazon.com/s"
    reliability_score = 0.50

    SEARCH_URL = "https://www.amazon.com/s?k={pn}"

    # Amazon 商品价格正则 / Amazon price patterns
    PRICE_PATTERNS = [
        re.compile(r'\$\s*([0-9,]+\.?\d*)'),
        re.compile(r'([0-9,]+\.?\d*)\s*\$'),
    ]

    # Amazon 搜索页商品区块正则 / Amazon result block patterns
    RESULT_BLOCK_PATTERN = re.compile(
        r'<div[^>]*data-component-type="s-search-result"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        re.IGNORECASE | re.DOTALL,
    )
    TITLE_PATTERN = re.compile(
        r'<h2[^>]*>.*?<a[^>]*>(.*?)</a>.*?</h2>',
        re.IGNORECASE | re.DOTALL,
    )
    LINK_PATTERN = re.compile(
        r'<h2[^>]*>.*?<a[^>]*href="([^"]*)"',
        re.IGNORECASE | re.DOTALL,
    )
    PRICE_BLOCK_PATTERN = re.compile(
        r'<span[^>]*class="[^"]*a-price[^"]*"[^>]*>.*?<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>(.*?)</span>',
        re.IGNORECASE | re.DOTALL,
    )
    IN_STOCK_PATTERN = re.compile(
        r'(In Stock|Available|Delivery|Tomorrow|Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)',
        re.IGNORECASE,
    )

    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询 Amazon 商品信息 / Look up a part on Amazon.

        构造 Amazon 搜索 URL，抓取 HTML 并解析搜索结果。
        若抓取或解析失败，则返回 _mock_lookup() 生成的模拟数据。

        Constructs Amazon search URL, fetches HTML and parses results.
        Falls back to mock data on failure.

        Args:
            part_number: 零件号字符串 / Part number string.

        Returns:
            ServerPart 实例（含 Amazon 价格来源）或 None / ServerPart with Amazon
            price sources, or None.
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
                    condition="new" if item.get("in_stock") else None,
                    in_stock=item.get("in_stock"),
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
            description=f"Amazon search result for {part_number}",
            description_zh=f"Amazon 搜索结果: {part_number}",
            specifications={},
            raw_specifications={},
            sources=sources,
            median_price_usd=median_price,
            price_range_usd=price_range,
            confidence_score=0.35 if sources else 0.0,
        )

    def search_by_spec(self, **specs: Any) -> List[ServerPart]:
        """按规格参数搜索（Amazon 不支持，返回空列表）/ Search by specs.

        Amazon 公开页不支持规格搜索，此方法返回空列表。
        Public Amazon does not support spec-based search.

        Args:
            **specs: 规格键值对 / Specification key-value pairs.

        Returns:
            空列表 / Empty list.
        """
        return []

    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """从 Amazon 搜索结果 HTML 中提取商品列表 / Extract products from HTML.

        使用正则表达式提取商品标题、价格、链接和库存状态。
        Uses regex to extract titles, prices, URLs, and stock status.

        Args:
            html: Amazon 搜索结果页 HTML / Amazon search results HTML.

        Returns:
            商品字典列表 / List of product dicts with title, price, url, in_stock.
        """
        items: List[Dict[str, Any]] = []

        # 按商品区块分割 / Split by result blocks
        blocks = self.RESULT_BLOCK_PATTERN.findall(html)

        if not blocks:
            # 备用：尝试整体匹配 / Fallback: whole-page match
            return self._fallback_parse(html)

        for block in blocks[:10]:  # 最多处理 10 个区块 / Process up to 10
            # 提取标题 / Extract title
            title_match = self.TITLE_PATTERN.search(block)
            title = ""
            if title_match:
                title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()

            # 提取链接 / Extract link
            link_match = self.LINK_PATTERN.search(block)
            url = None
            if link_match:
                href = link_match.group(1)
                if href.startswith("/"):
                    href = f"https://www.amazon.com{href}"
                url = href

            # 提取价格 / Extract price
            price_match = self.PRICE_BLOCK_PATTERN.search(block)
            price: Optional[float] = None
            if price_match:
                price_text = re.sub(r"<[^>]+>", "", price_match.group(1)).strip()
                for pat in self.PRICE_PATTERNS:
                    m = pat.search(price_text)
                    if m:
                        try:
                            price = float(m.group(1).replace(",", ""))
                            break
                        except ValueError:
                            continue

            # 检查库存 / Check stock
            in_stock = bool(self.IN_STOCK_PATTERN.search(block))

            # 过滤无效条目 / Filter invalid entries
            if title and price and price > 0:
                items.append(
                    {
                        "title": title,
                        "price": price,
                        "url": url,
                        "in_stock": in_stock,
                        "original_price": price,
                    }
                )

        return items

    def _fallback_parse(self, html: str) -> List[Dict[str, Any]]:
        """备用解析：从整页 HTML 中提取价格信息 / Fallback: extract prices from full page.

        当区块分割失败时，尝试全局正则匹配价格。
        Tries global regex matching when block parsing fails.

        Args:
            html: Amazon 搜索结果页 HTML / Amazon search results HTML.

        Returns:
            商品字典列表 / List of product dicts.
        """
        items: List[Dict[str, Any]] = []

        # 全局价格匹配 / Global price matching
        for pat in self.PRICE_PATTERNS:
            for match in pat.finditer(html):
                try:
                    price = float(match.group(1).replace(",", ""))
                    if price > 0 and price < 100000:  # 过滤异常值 / Filter outliers
                        items.append(
                            {
                                "title": "Amazon listing",
                                "price": price,
                                "url": None,
                                "in_stock": None,
                                "original_price": price,
                            }
                        )
                except ValueError:
                    continue
            if items:
                break

        return items

    def _mock_lookup(self, part_number: str) -> ServerPart:
        """返回 Amazon 模拟数据 / Return mock Amazon data.

        当 Amazon 反爬或网络故障时，返回标注为模拟数据的 ServerPart。
        Returns a ServerPart marked as mock data when Amazon is blocked.

        Args:
            part_number: 零件号字符串 / Part number string.

        Returns:
            含模拟价格来源的 ServerPart / ServerPart with mock price source.
        """
        import random

        mock_price = round(random.uniform(15.0, 600.0), 2)
        return ServerPart(
            part_number=part_number,
            manufacturer="UNKNOWN",
            manufacturer_zh="未知厂商",
            category="OTHERS",
            category_zh="其他",
            description=f"Amazon mock result for {part_number}",
            description_zh=f"Amazon 模拟数据: {part_number}",
            specifications={},
            raw_specifications={},
            sources=[
                PriceSource(
                    source_name=self.name,
                    source_name_zh=self.name_zh,
                    price_usd=mock_price,
                    original_price=mock_price,
                    original_currency="USD",
                    url=f"https://www.amazon.com/s?k={quote_plus(part_number)}",
                    condition="new",
                    in_stock=True,
                    reliability_score=self.reliability_score,
                )
            ],
            median_price_usd=mock_price,
            price_range_usd=(mock_price, mock_price),
            confidence_score=0.12,
        )
