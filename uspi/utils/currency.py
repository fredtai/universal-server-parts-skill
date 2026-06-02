"""
Currency conversion module for USPI.
USPI 货币转换模块。

Provides USD-based currency conversion with automatic fallback
between multiple exchange rate sources (ECB, floatrates.com)
and hardcoded fallback rates for graceful degradation.
提供基于美元的货币转换,支持多个汇率源 (ECB, floatrates.com) 之间的
自动回退,以及硬编码回退汇率以实现优雅降级。

All exchange rates are USD-based (how many USD 1 unit of foreign currency buys).
所有汇率均以美元为基准 (1 单位外币可兑换多少美元)。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

from uspi.utils.cache import Cache

__all__ = ["CurrencyConverter"]


class CurrencyConverter:
    """
    Currency converter with USD as the base currency.
    以 USD 为基准货币的汇率转换器。

    Fetches live exchange rates from multiple sources with automatic fallback:
    1. Primary: European Central Bank (ECB) XML feed
    2. Secondary: floatrates.com JSON API
    3. Fallback: Hardcoded rates for common currencies

    从多个源获取实时汇率,并自动回退:
    1. 主源: 欧洲央行 (ECB) XML 数据流
    2. 备源: floatrates.com JSON API
    3. 回退: 常见货币的硬编码汇率

    Usage / 用法:
        >>> converter = CurrencyConverter()
        >>> result = converter.convert_to_usd(100.0, "EUR")
        >>> result["usd_amount"]
        108.0
    """

    # ECB XML URL / 欧洲央行 XML 地址
    _ECB_URL: str = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    # floatrates.com JSON URL / floatrates.com JSON 地址
    _FLOATRATES_URL: str = "https://www.floatrates.com/daily/usd.json"

    # Hardcoded fallback rates (USD per 1 unit of foreign currency)
    # 硬编码回退汇率 (1 单位外币兑换的 USD)
    FALLBACK_RATES: dict[str, float] = {
        "EUR": 1.08,
        "CNY": 0.14,
        "JPY": 0.0067,
        "GBP": 1.27,
        "TWD": 0.031,
        "USD": 1.0,
    }

    def __init__(self, cache: Optional[Cache] = None) -> None:
        """
        Initialize the currency converter.
        初始化货币转换器。

        Args / 参数:
            cache: Optional Cache instance for storing fetched rates.
                   If None, no caching is used.
                   可选的 Cache 实例,用于存储获取的汇率。
                   如果为 None,则不使用缓存。
        """
        self._cache: Optional[Cache] = cache

    def convert_to_usd(self, amount: float, from_currency: str) -> dict[str, Any]:
        """
        Convert an amount from the given currency to USD.
        将给定货币的金额转换为 USD。

        Automatically fetches live rates, falls back to alternative sources,
        and finally to hardcoded rates if all sources fail.
        自动获取实时汇率,回退到替代源,如果所有源都失败则使用硬编码汇率。

        Args / 参数:
            amount: The amount to convert.
                    要转换的金额。
            from_currency: The ISO 4217 currency code (e.g., "EUR", "CNY").
                           ISO 4217 货币代码 (例如 "EUR", "CNY")。

        Returns / 返回:
            A dictionary with the following keys:
            - "usd_amount": The converted amount in USD
            - "rate": The exchange rate used
            - "stale": True if a fallback rate was used, False otherwise
            - "source": The source of the rate ("ecb", "floatrates", "fallback")

            包含以下键的字典:
            - "usd_amount": 转换后的 USD 金额
            - "rate": 使用的汇率
            - "stale": 如果使用了回退汇率则为 True,否则为 False
            - "source": 汇率来源 ("ecb", "floatrates", "fallback")
        """
        currency: str = from_currency.upper()

        if currency == "USD":
            return {
                "usd_amount": amount,
                "rate": 1.0,
                "stale": False,
                "source": "fixed",
            }

        # Try cache first / 首先尝试缓存
        if self._cache is not None:
            cache_key: str = f"fx_rate:{currency}"
            cached: Optional[str] = self._cache.get(cache_key)
            if cached is not None:
                try:
                    rate: float = float(cached)
                    return {
                        "usd_amount": amount * rate,
                        "rate": rate,
                        "stale": False,
                        "source": "cache",
                    }
                except ValueError:
                    pass  # Invalid cached value, fetch fresh / 缓存值无效,重新获取

        # Try primary source: ECB / 尝试主源: ECB
        ecb_rates: Optional[dict[str, float]] = self._fetch_ecb_rates()
        if ecb_rates is not None and currency in ecb_rates:
            rate = ecb_rates[currency]
            self._store_in_cache(currency, rate)
            return {
                "usd_amount": amount * rate,
                "rate": rate,
                "stale": False,
                "source": "ecb",
            }

        # Try secondary source: floatrates.com / 尝试备源: floatrates.com
        fr_rates: Optional[dict[str, float]] = self._fetch_floatrates()
        if fr_rates is not None and currency in fr_rates:
            rate = fr_rates[currency]
            self._store_in_cache(currency, rate)
            return {
                "usd_amount": amount * rate,
                "rate": rate,
                "stale": False,
                "source": "floatrates",
            }

        # Fallback to hardcoded rates / 回退到硬编码汇率
        rate = self._get_fallback_rate(currency)
        return {
            "usd_amount": amount * rate,
            "rate": rate,
            "stale": True,
            "source": "fallback",
        }

    def _fetch_ecb_rates(self) -> Optional[dict[str, float]]:
        """
        Fetch exchange rates from the ECB XML feed.
        从 ECB XML 数据流获取汇率。

        Parses EUR-based rates and converts them to USD-based rates
        using the EUR/USD rate from the feed.
        解析基于 EUR 的汇率,并使用数据流中的 EUR/USD 汇率将其转换为基于 USD 的汇率。

        Returns / 返回:
            A dictionary mapping currency codes to USD-based rates,
            or None if the fetch failed.
            货币代码到基于 USD 的汇率的映射字典,如果获取失败则返回 None。
        """
        try:
            req = urllib.request.Request(
                self._ECB_URL,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; USPI/0.1.0; "
                        "+https://github.com/example/uspi)"
                    ),
                },
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                xml_data: str = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError):
            return None

        try:
            root: ET.Element = ET.fromstring(xml_data)
        except ET.ParseError:
            return None

        # ECB XML namespace / ECB XML 命名空间
        ns: dict[str, str] = {
            "": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
            "gesmes": "http://www.gesmes.org/xml/2002-08-01",
        }

        # Find all Cube elements with currency attributes
        # 查找所有带 currency 属性的 Cube 元素
        eur_rates: dict[str, float] = {}
        eur_usd_rate: Optional[float] = None

        for cube in root.iter("{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube"):
            currency_attr: Optional[str] = cube.get("currency")
            rate_attr: Optional[str] = cube.get("rate")
            if currency_attr is not None and rate_attr is not None:
                try:
                    rate_val: float = float(rate_attr)
                    eur_rates[currency_attr] = rate_val
                    if currency_attr == "USD":
                        eur_usd_rate = rate_val
                except ValueError:
                    continue

        if eur_usd_rate is None or eur_usd_rate == 0:
            return None

        # Convert EUR-based rates to USD-based rates
        # Rate in USD = (1 / EUR_USD) * EUR_currency_rate
        # 将基于 EUR 的汇率转换为基于 USD 的汇率
        # USD 汇率 = (1 / EUR_USD) * EUR_货币汇率
        usd_rates: dict[str, float] = {}
        for curr, eur_rate in eur_rates.items():
            if curr != "USD":
                usd_rates[curr] = eur_rate / eur_usd_rate

        # Add USD itself
        usd_rates["USD"] = 1.0
        # EUR rate in USD terms / EUR 以 USD 计价的汇率
        usd_rates["EUR"] = 1.0 / eur_usd_rate

        return usd_rates

    def _fetch_floatrates(self) -> Optional[dict[str, float]]:
        """
        Fetch USD-based exchange rates from floatrates.com.
        从 floatrates.com 获取基于 USD 的汇率。

        Returns / 返回:
            A dictionary mapping currency codes to USD-based rates,
            or None if the fetch failed.
            货币代码到基于 USD 的汇率的映射字典,如果获取失败则返回 None。
        """
        try:
            req = urllib.request.Request(
                self._FLOATRATES_URL,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; USPI/0.1.0; "
                        "+https://github.com/example/uspi)"
                    ),
                },
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                json_data: str = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError):
            return None

        try:
            data: dict[str, Any] = json.loads(json_data)
        except json.JSONDecodeError:
            return None

        usd_rates: dict[str, float] = {"USD": 1.0}

        # floatrates.com returns rates with "rate" field being
        # how many foreign currency units per USD.
        # We need USD per foreign currency unit, so we take the inverse.
        # floatrates.com 返回的 "rate" 字段是 1 USD 兑换多少外币。
        # 我们需要 1 外币兑换多少 USD,所以取倒数。
        for currency_code, info in data.items():
            if isinstance(info, dict) and "rate" in info:
                try:
                    fr_rate: float = float(info["rate"])
                    if fr_rate > 0:
                        # Inverse: USD per 1 unit of foreign currency
                        # 取倒数: 1 单位外币兑换的 USD
                        code_upper: str = currency_code.upper()
                        usd_rates[code_upper] = 1.0 / fr_rate
                except (ValueError, TypeError):
                    continue

        return usd_rates if len(usd_rates) > 1 else None

    def _get_fallback_rate(self, currency: str) -> float:
        """
        Return a hardcoded fallback exchange rate for the given currency.
        返回给定货币的硬编码回退汇率。

        This is used as the last resort when all live rate sources fail.
        当所有实时汇率源都失败时,作为最后手段使用。

        Args / 参数:
            currency: The ISO 4217 currency code (e.g., "EUR").
                      ISO 4217 货币代码 (例如 "EUR")。

        Returns / 返回:
            The hardcoded USD rate for the currency, or 0.0 if unknown.
            该货币的硬编码 USD 汇率,如果未知则返回 0.0。
        """
        return self.FALLBACK_RATES.get(currency.upper(), 0.0)

    def _store_in_cache(self, currency: str, rate: float) -> None:
        """
        Store an exchange rate in the cache.
        将汇率存入缓存。

        Args / 参数:
            currency: The currency code.
                      货币代码。
            rate: The exchange rate to cache.
                  要缓存的汇率。
        """
        if self._cache is not None:
            cache_key: str = f"fx_rate:{currency.upper()}"
            # Cache exchange rates for 6 hours (21600 seconds)
            # 缓存汇率 6 小时 (21600 秒)
            self._cache.set(cache_key, str(rate), ttl=21600)
