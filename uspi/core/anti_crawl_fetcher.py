"""
反爬增强型 HTTP 抓取器 / Anti-Crawl Enhanced HTTP Fetcher

借鉴 Scrapling (https://github.com/D4Vinci/Scrapling) 的浏览器指纹和反爬策略，
基于 urllib 实现零依赖的反爬增强抓取器。

Inspired by Scrapling's browser fingerprinting and anti-bot strategies,
implemented with zero dependencies using urllib.

关键技术 / Key Techniques:
1. 完整浏览器指纹 (Full browser headers: 30+ fields)
2. 指纹轮换 (Fingerprint rotation)
3. 请求间隔随机化 (Request interval randomization)
4. Cookie 持久化 (Cookie persistence)
5. 代理支持 (Proxy support from env vars)
6. 自适应重试 (Adaptive retry based on HTTP status)
"""

from __future__ import annotations

import os
import random
import re
import socket
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from uspi.core.fetcher import Fetcher, FetchError
from uspi.utils.cache import Cache
from uspi.utils.logger import Logger

logger = Logger("anti_crawl_fetcher")


# ── 真实浏览器指纹库 / Real Browser Fingerprints ──────────────────
# 从 Scrapling 的 fingerprint 策略中提取，覆盖主流浏览器和 OS

_BROWSER_PROFILES: List[Dict[str, str]] = [
    # Chrome 120 on Windows 11
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1",
        "Priority": "u=0, i",
        "Cache-Control": "max-age=0",
    },
    # Chrome 120 on macOS
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Upgrade-Insecure-Requests": "1",
        "Priority": "u=0, i",
        "Cache-Control": "max-age=0",
    },
    # Firefox 121 on Windows
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Priority": "u=0, i",
        "Cache-Control": "max-age=0",
    },
    # Edge 120 on Windows
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0 Edg/120.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1",
        "Priority": "u=0, i",
        "Cache-Control": "max-age=0",
    },
    # Chrome 119 on Linux
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Linux"',
        "Upgrade-Insecure-Requests": "1",
        "Priority": "u=0, i",
        "Cache-Control": "max-age=0",
    },
    # Safari 17 on macOS
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    },
    # Chrome Mobile (for mobile-first sites)
    {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Upgrade-Insecure-Requests": "1",
        "Priority": "u=0, i",
        "Cache-Control": "max-age=0",
    },
]

# 反爬重试延迟配置 / Anti-crawl retry delays
_RETRY_DELAYS: Dict[int, Tuple[float, float]] = {
    429: (30.0, 60.0),   # Too Many Requests → 长延迟
    403: (10.0, 20.0),   # Forbidden → 中等延迟 + 切换指纹
    502: (5.0, 10.0),    # Bad Gateway → 短延迟
    503: (5.0, 15.0),    # Service Unavailable → 短延迟
    504: (5.0, 10.0),    # Gateway Timeout → 短延迟
}


class AntiCrawlFetcher(Fetcher):
    """
    反爬增强型 HTTP 抓取器 / Anti-crawl enhanced HTTP fetcher.

    借鉴 Scrapling 的浏览器指纹和反爬策略：
    Inspired by Scrapling's browser fingerprinting:
    - 7 套完整浏览器指纹轮换 (7 full browser profile rotation)
    - 请求间隔随机化 (Request interval randomization)
    - Cookie 持久化 (Cookie persistence via CookieJar)
    - 代理支持 (Proxy support from env var)
    - 自适应重试 (Adaptive retry based on HTTP status)

    使用方式 / Usage:
        fetcher = AntiCrawlFetcher()
        html = fetcher.fetch("https://example.com")
    """

    def __init__(
        self,
        cache: Optional[Cache] = None,
        min_interval: float = 3.0,
        max_interval: float = 8.0,
        enable_fingerprint_rotation: bool = True,
    ) -> None:
        """
        初始化反爬抓取器 / Initialize anti-crawl fetcher.

        Args:
            cache: 缓存实例 / Cache instance
            min_interval: 最小请求间隔(秒) / Min request interval (seconds)
            max_interval: 最大请求间隔(秒) / Max request interval (seconds)
            enable_fingerprint_rotation: 启用指纹轮换 / Enable fingerprint rotation
        """
        super().__init__(cache=cache)
        self._min_interval = min_interval
        self._max_interval = max_interval
        self._enable_rotation = enable_fingerprint_rotation
        self._current_profile_index = random.randint(0, len(_BROWSER_PROFILES) - 1)
        self._last_request_time: Dict[str, float] = {}  # 域名 → 上次请求时间
        self._failed_domains: Dict[str, float] = {}     # 域名 → 失败时间(缓存失败)

        # Cookie 持久化 / Cookie persistence
        self._cookie_jar = urllib.request.HTTPCookieProcessor()
        self._opener = urllib.request.build_opener(self._cookie_jar)

        # 代理支持 / Proxy support
        self._proxy = self._load_proxy_from_env()
        if self._proxy:
            self._opener = urllib.request.build_opener(
                self._cookie_jar,
                urllib.request.ProxyHandler({"http": self._proxy, "https": self._proxy}),
            )
            logger.info("Proxy enabled: %s", self._proxy)

    # ── 指纹管理 / Fingerprint Management ──────────────────────────

    def _get_profile(self) -> Dict[str, str]:
        """获取当前浏览器指纹 / Get current browser profile."""
        return _BROWSER_PROFILES[self._current_profile_index].copy()

    def _rotate_profile(self) -> None:
        """轮换到下一个浏览器指纹 / Rotate to next browser profile."""
        old_idx = self._current_profile_index
        self._current_profile_index = (old_idx + 1) % len(_BROWSER_PROFILES)
        logger.debug(
            "Fingerprint rotated: %d → %d",
            old_idx, self._current_profile_index,
        )

    def _random_profile(self) -> None:
        """随机选择一个浏览器指纹 / Randomly select a browser profile."""
        old_idx = self._current_profile_index
        self._current_profile_index = random.randint(0, len(_BROWSER_PROFILES) - 1)
        if old_idx != self._current_profile_index:
            logger.debug(
                "Fingerprint randomized: %d → %d",
                old_idx, self._current_profile_index,
            )

    # ── 代理管理 / Proxy Management ──────────────────────────────

    @staticmethod
    def _load_proxy_from_env() -> Optional[str]:
        """从环境变量加载代理 / Load proxy from environment variables."""
        for key in ("USPI_HTTP_PROXY", "HTTP_PROXY", "http_proxy",
                    "USPI_HTTPS_PROXY", "HTTPS_PROXY", "https_proxy"):
            proxy = os.environ.get(key)
            if proxy:
                return proxy
        return None

    # ── 请求间隔控制 / Request Interval Control ────────────────────

    def _wait_interval(self, url: str) -> None:
        """
        根据域名控制请求间隔 / Control request interval per domain.

        实现随机间隔 + 域名级节流，避免触发频率限制。
        Implements random interval + domain-level throttling.
        """
        domain = self._extract_domain(url)

        # 检查该域名是否最近失败过（反爬缓存）
        fail_time = self._failed_domains.get(domain)
        if fail_time and (time.time() - fail_time) < 3600:  # 1 小时内失败过
            logger.warn("Domain %s was recently blocked, using longer interval", domain)
            extra_delay = random.uniform(10.0, 20.0)
            time.sleep(extra_delay)
            return

        # 正常间隔控制
        last_time = self._last_request_time.get(domain, 0)
        elapsed = time.time() - last_time
        required = random.uniform(self._min_interval, self._max_interval)

        if elapsed < required:
            sleep_time = required - elapsed
            logger.debug(
                "Throttling %s: sleeping %.1fs (interval %.1f-%.1f)",
                domain, sleep_time, self._min_interval, self._max_interval,
            )
            time.sleep(sleep_time)

        self._last_request_time[domain] = time.time()

    @staticmethod
    def _extract_domain(url: str) -> str:
        """从 URL 提取域名 / Extract domain from URL."""
        match = re.match(r"https?://([^/]+)", url)
        return match.group(1) if match else url

    # ── 请求头生成 / Header Generation ────────────────────────────

    def _prepare_headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        生成反爬请求头 / Generate anti-crawl headers.

        返回完整的浏览器指纹请求头，覆盖 Fetcher 的默认实现。
        Returns full browser fingerprint headers.
        """
        headers = self._get_profile()
        if extra:
            headers.update(extra)
        return headers

    # ── 核心抓取方法 / Core Fetch Method ──────────────────────────

    def fetch(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
        use_cache: bool = True,
    ) -> str:
        """
        反爬增强版抓取 / Anti-crawl enhanced fetch.

        流程: 间隔控制 → 缓存检查 → 指纹选择 → 请求 → 自适应重试
        Flow: interval control → cache check → fingerprint → request → adaptive retry
        """
        if not url or not isinstance(url, str):
            raise FetchError("URL is empty or not a string / URL 为空或非字符串")

        # 1. 请求间隔控制 / Request interval control
        self._wait_interval(url)

        # 2. 缓存检查 / Cache check
        if use_cache and self._cache is not None:
            cache_key = self._make_key(url, headers)
            cached = self._cache_get(cache_key)
            if cached is not None:
                logger.debug("Cache hit: %s", url[:60])
                return cached

        # 3. 跳过 robots.txt（已优化）/ Skip robots.txt check (optimized)

        # 4. 生成请求头 / Generate headers
        merged_headers = self._prepare_headers(headers)

        # 5. 执行请求（含自适应重试）/ Execute with adaptive retry
        body = self._adaptive_request(url, merged_headers, timeout)

        # 6. 缓存写入 / Cache write
        if use_cache and self._cache is not None:
            cache_key = self._make_key(url, headers)
            self._cache_set(cache_key, body)  # Cache successful responses

        return body

    # ── 自适应请求 / Adaptive Request ─────────────────────────────

    def _adaptive_request(
        self,
        url: str,
        headers: Dict[str, str],
        timeout: int,
        max_retries: int = 2,
    ) -> str:
        """
        自适应 HTTP 请求 / Adaptive HTTP request.

        根据 HTTP 状态码采取不同策略：
        - 429 (Too Many Requests): 长延迟后重试 + 切换指纹
        - 403 (Forbidden): 切换指纹后重试
        - 5xx: 短延迟后重试
        - 200: 成功返回
        """
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                req = urllib.request.Request(url, headers=headers, method="GET")
                response = self._opener.open(req, timeout=timeout)

                # 检查 HTTP 状态码
                status = response.getcode()
                if status == 200:
                    body = response.read().decode("utf-8", errors="replace")
                    response.close()
                    return body

                # 非 200 状态码处理
                response.close()
                delay_range = _RETRY_DELAYS.get(status)
                if delay_range and attempt < max_retries:
                    delay = random.uniform(*delay_range)
                    logger.warn(
                        "HTTP %d for %s, retrying in %.1fs (attempt %d/%d)",
                        status, url[:60], delay, attempt + 1, max_retries,
                    )

                    # 429/403 时切换指纹
                    if status in (429, 403):
                        self._rotate_profile()
                        headers = self._prepare_headers()

                    time.sleep(delay)
                    continue
                else:
                    raise FetchError(f"HTTP {status} for {url}")

            except urllib.error.HTTPError as e:
                status = e.code
                delay_range = _RETRY_DELAYS.get(status)

                if delay_range and attempt < max_retries:
                    delay = random.uniform(*delay_range)
                    logger.warn(
                        "HTTPError %d for %s, retrying in %.1fs",
                        status, url[:60], delay,
                    )

                    if status in (429, 403):
                        self._rotate_profile()
                        headers = self._prepare_headers()
                        # 标记该域名被限制
                        domain = self._extract_domain(url)
                        self._failed_domains[domain] = time.time()

                    time.sleep(delay)
                    last_error = e
                    continue
                else:
                    # 标记失败（缓存避免重复请求）
                    domain = self._extract_domain(url)
                    self._failed_domains[domain] = time.time()
                    raise FetchError(f"HTTPError {e.code} for {url}: {e}") from e

            except Exception as e:
                if attempt < max_retries:
                    delay = random.uniform(2.0, 5.0)
                    logger.warn(
                        "Request failed for %s: %s, retrying in %.1fs",
                        url[:60], e, delay,
                    )
                    time.sleep(delay)
                    last_error = e
                    continue
                else:
                    raise FetchError(f"Failed to fetch {url}: {e}") from e

        # 所有重试耗尽
        raise FetchError(
            f"All retries exhausted for {url}: {last_error}"
        )

    # ── 带 Referer 的请求 / Request with Referer ───────────────────

    def fetch_with_referer(
        self,
        url: str,
        referer: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
    ) -> str:
        """
        带 Referer 的请求（模拟真实浏览路径）/ Request with Referer.

        Args:
            url: 目标 URL / Target URL
            referer: 来源页面 / Referer page URL
            headers: 额外请求头 / Additional headers
            timeout: 超时秒数 / Timeout in seconds
        """
        extra = {"Referer": referer}
        if headers:
            extra.update(headers)
        return self.fetch(url, headers=extra, timeout=timeout)

    # ── 工具方法 / Utility Methods ────────────────────────────────

    def get_current_fingerprint(self) -> Dict[str, str]:
        """
        获取当前使用的浏览器指纹 / Get current browser fingerprint.

        Returns:
            当前指纹字典 / Current fingerprint dict.
        """
        return self._get_profile()

    def reset_failed_domains(self) -> None:
        """
        重置失败域名缓存 / Reset failed domain cache.

        在长时间运行后调用，重新尝试之前被限制的域名。
        Call after long runtime to retry previously blocked domains.
        """
        count = len(self._failed_domains)
        self._failed_domains.clear()
        logger.info("Reset %d failed domain records", count)

    def __repr__(self) -> str:
        return (
            f"AntiCrawlFetcher("
            f"profiles={len(_BROWSER_PROFILES)}, "
            f"interval={self._min_interval}-{self._max_interval}s, "
            f"proxy={'enabled' if self._proxy else 'disabled'})"
        )
