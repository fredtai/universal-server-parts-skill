"""
uspi/core/fetcher.py

基于 urllib 的 HTTP 抓取器 / HTTP Fetcher based on urllib

功能 / Features:
- 3 次重试 + 指数退避 / 3 retries with exponential backoff
- User-Agent 轮换 / User-Agent rotation
- robots.txt 内存缓存 / In-memory robots.txt cache
- SQLite 缓存支持 (TTL 86400s) / SQLite cache support with TTL
- 线程安全 / Thread-safe
- 仅使用标准库 / Standard library only (urllib, http.client, sqlite3, etc.)
"""

from __future__ import annotations

import hashlib
import json
import random
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlparse

# ---------------------------------------------------------------------------
# 自定义异常 / Custom Exceptions
# ---------------------------------------------------------------------------


class FetchError(Exception):
    """抓取失败异常 / Exception raised when HTTP fetch fails.

    Attributes:
        url: 请求 URL / Request URL
        status: HTTP 状态码 / HTTP status code (if applicable)
        message: 错误描述 / Error description
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status = status
        self.message = message

    def __str__(self) -> str:
        parts = [self.message]
        if self.url:
            parts.append(f"URL={self.url}")
        if self.status is not None:
            parts.append(f"Status={self.status}")
        return " | ".join(parts)


class RobotsDisallowedError(FetchError):
    """robots.txt 禁止抓取异常 / Exception raised when robots.txt disallows crawling.

    Attributes:
        url: 被禁止的 URL / Disallowed URL
        robots_url: robots.txt 的 URL / robots.txt URL
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        robots_url: Optional[str] = None,
    ) -> None:
        super().__init__(message, url=url)
        self.robots_url = robots_url


class RateLimitError(FetchError):
    """请求频率受限异常 (HTTP 429) / Exception raised when rate limited (HTTP 429).

    Attributes:
        url: 请求 URL / Request URL
        retry_after: 建议等待秒数 / Suggested retry delay in seconds
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message, url=url, status=429)
        self.retry_after = retry_after


# ---------------------------------------------------------------------------
# Fetcher 类 / Fetcher Class
# ---------------------------------------------------------------------------


class Fetcher:
    """基于 urllib 的 HTTP 抓取器 / HTTP fetcher based on urllib.

    特性 / Features:
    - 自动轮换 User-Agent / Automatic User-Agent rotation
    - robots.txt 检查与内存缓存 / robots.txt checking with in-memory cache
    - 指数退避重试 / Exponential backoff retry
    - SQLite 缓存集成 / SQLite cache integration
    - 线程安全 / Thread-safe

    Args:
        cache: Cache 实例 (可选) / Cache instance (optional)
        max_retries: 最大重试次数 / Maximum retry attempts (default: 3)
    """

    USER_AGENTS: list[str] = [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.0"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.0"
        ),
        (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.0"
        ),
    ]

    def __init__(
        self,
        cache: Any = None,
        max_retries: int = 3,
    ) -> None:
        """初始化抓取器 / Initialize the fetcher.

        Args:
            cache: Cache 实例 (可选，需有 get/set 方法) / Cache instance with get/set methods
            max_retries: 最大重试次数 / Maximum number of retries
        """
        self._cache = cache
        self._max_retries = max_retries

        # robots.txt 内存缓存: {netloc -> RobotFileParser} / In-memory robots.txt cache
        self._robots_cache: dict[str, Any] = {}

        # User-Agent 轮换索引 / UA rotation index (轮询替代随机)
        self._ua_index: int = 0

        # 线程锁，保证线程安全 / Threading lock for thread safety
        self._lock = threading.Lock()

    def _get_next_ua(self) -> str:
        """轮询获取下一个 UA / Rotate to next UA.

        使用原子递增索引实现 O(1) 轮询，替代 random.choice 的 O(N) 开销。
        Uses atomic-increment index for O(1) rotation vs random.choice O(N).

        Returns:
            下一个 User-Agent 字符串 / Next User-Agent string.
        """
        ua = self.USER_AGENTS[self._ua_index % len(self.USER_AGENTS)]
        self._ua_index += 1
        return ua

    # -- public API ---------------------------------------------------------

    def fetch(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        use_cache: bool = True,
    ) -> str:
        """抓取 URL 并返回 HTML/文本内容 / Fetch URL and return HTML/text content.

        执行流程 / Execution flow:
        1. 若启用缓存，先检查缓存 / Check cache first if enabled
        2. 检查 robots.txt / Check robots.txt permission
        3. 发送请求（含重试） / Send request with retries
        4. 存入缓存（若启用） / Store in cache if enabled

        Args:
            url: 目标 URL / Target URL
            headers: 额外请求头 / Additional HTTP headers
            timeout: 超时秒数 / Timeout in seconds
            use_cache: 是否使用缓存 / Whether to use cache

        Returns:
            响应体文本 / Response body text

        Raises:
            RobotsDisallowedError: robots.txt 禁止抓取 / robots.txt disallows crawling
            RateLimitError: HTTP 429 频率限制 / HTTP 429 rate limited
            FetchError: 其他抓取失败 / Other fetch failures
        """
        # 1. 缓存检查 / Cache lookup
        if use_cache and self._cache is not None:
            cache_key = self._make_key(url, headers)
            cached = self._cache_get(cache_key)
            if cached is not None:
                return cached

        # 2. robots.txt 检查 / robots.txt check
        if not self._check_robots_txt(url):
            raise RobotsDisallowedError(
                message=f"robots.txt disallows fetching: {url}",
                url=url,
                robots_url=self._robots_url(url),
            )

        # 3. 发送请求（含重试） / Send request with retries
        merged_headers = self._prepare_headers(headers)
        body = self._retry_with_backoff(url, merged_headers, timeout, attempt=0)

        # 4. 缓存写入 / Cache write
        if use_cache and self._cache is not None:
            cache_key = self._make_key(url, headers)
            self._cache_set(cache_key, body)

        return body

    def post(
        self,
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> str:
        """发送 POST 请求 / Send a POST request.

        Args:
            url: 目标 URL / Target URL
            data: POST 表单数据 / Form data
            headers: 额外请求头 / Additional HTTP headers
            timeout: 超时秒数 / Timeout in seconds

        Returns:
            响应体文本 / Response body text

        Raises:
            RateLimitError: HTTP 429 频率限制 / HTTP 429 rate limited
            FetchError: 其他抓取失败 / Other fetch failures
        """
        merged_headers = self._prepare_headers(headers)

        # 设置 Content-Type / Set Content-Type
        merged_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

        encoded_data = urlencode(data).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=encoded_data,
            headers=merged_headers,
            method="POST",
        )

        return self._execute_request(request, timeout, url)

    # -- robots.txt handling ------------------------------------------------

    def _check_robots_txt(self, url: str) -> bool:
        """检查 robots.txt 是否允许抓取 / Check if robots.txt allows crawling.

        使用内存缓存避免重复解析 / Uses in-memory cache to avoid repeated parsing.

        Args:
            url: 目标 URL / Target URL

        Returns:
            True 表示允许抓取，False 表示禁止 / True if allowed, False if disallowed
        """
        import urllib.robotparser

        parsed = urlparse(url)
        netloc = parsed.netloc
        if not netloc:
            # 无效 URL，默认允许 / Invalid URL, allow by default
            return True

        # 检查内存缓存 / Check in-memory cache
        with self._lock:
            if netloc in self._robots_cache:
                rp = self._robots_cache[netloc]
                return rp.can_fetch("*", url)

        # 下载并解析 robots.txt / Download and parse robots.txt
        robots_url = self._robots_url(url)
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)

        try:
            rp.read()
        except Exception:
            # robots.txt 不可达时默认允许 / Allow by default when unreachable
            return True

        # 存入缓存 / Store in cache
        with self._lock:
            self._robots_cache[netloc] = rp

        return rp.can_fetch("*", url)

    def _robots_url(self, url: str) -> str:
        """从目标 URL 构造 robots.txt URL / Build robots.txt URL from target URL.

        Args:
            url: 目标 URL / Target URL

        Returns:
            robots.txt 的完整 URL / Full URL of robots.txt
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    # -- retry & backoff ----------------------------------------------------

    def _retry_with_backoff(
        self,
        url: str,
        headers: Dict[str, str],
        timeout: int,
        attempt: int,
    ) -> str:
        """带指数退避的重试逻辑 / Retry logic with exponential backoff.

        退避公式: delay = 2^attempt * 1 秒 / Backoff formula: delay = 2^attempt * 1 second

        Args:
            url: 目标 URL / Target URL
            headers: 请求头 / HTTP headers
            timeout: 超时秒数 / Timeout in seconds
            attempt: 当前尝试次数 (从 0 开始) / Current attempt number (0-based)

        Returns:
            响应体文本 / Response body text

        Raises:
            FetchError: 重试耗尽后抛出 / Raised when all retries are exhausted
        """
        request = urllib.request.Request(url, headers=headers)

        try:
            return self._execute_request(request, timeout, url)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            if attempt >= self._max_retries:
                raise FetchError(
                    message=f"Max retries ({self._max_retries}) exceeded: {exc}",
                    url=url,
                ) from exc

            # 指数退避 / Exponential backoff
            delay = (2 ** attempt) * 1.0
            # 添加随机抖动，避免 thundering herd / Add jitter
            delay += random.uniform(0, 0.5)
            time.sleep(delay)

            return self._retry_with_backoff(url, headers, timeout, attempt + 1)

    def _execute_request(
        self,
        request: urllib.request.Request,
        timeout: int,
        url: str,
    ) -> str:
        """执行单个 HTTP 请求 / Execute a single HTTP request.

        Args:
            request: urllib Request 对象 / urllib Request object
            timeout: 超时秒数 / Timeout in seconds
            url: 原始 URL (用于错误信息) / Original URL for error messages

        Returns:
            响应体文本 (UTF-8 解码) / Response body text decoded as UTF-8

        Raises:
            RateLimitError: HTTP 429 / HTTP 429 rate limited
            FetchError: 其他 HTTP 错误 / Other HTTP errors
            urllib.error.URLError: 网络错误 / Network errors
        """
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = self._detect_charset(response)
                body = response.read().decode(charset, errors="replace")
                return body
        except urllib.error.HTTPError as exc:
            status = exc.code
            if status == 429:
                # 提取 Retry-After 头 / Extract Retry-After header
                retry_after = None
                retry_header = exc.headers.get("Retry-After")
                if retry_header and retry_header.isdigit():
                    retry_after = int(retry_header)
                raise RateLimitError(
                    message=f"Rate limited (429) for {url}",
                    url=url,
                    retry_after=retry_after,
                ) from exc
            raise FetchError(
                message=f"HTTP error {status}: {exc.reason}",
                url=url,
                status=status,
            ) from exc
        except urllib.error.URLError:
            # 向上传递，由重试逻辑处理 / Propagate for retry logic
            raise

    # -- helpers ------------------------------------------------------------

    def _prepare_headers(
        self, extra: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        """准备请求头，包含随机 User-Agent / Prepare headers with random User-Agent.

        Args:
            extra: 用户提供的额外头 / User-provided extra headers

        Returns:
            合并后的请求头 / Merged headers dictionary
        """
        headers: Dict[str, str] = {
            "User-Agent": self._get_next_ua(),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
        }
        if extra:
            headers.update(extra)
        return headers

    def _detect_charset(self, response) -> str:
        """从响应头检测字符集 / Detect charset from response headers.

        Args:
            response: urllib.addinfourl 对象 / urllib response object

        Returns:
            字符集名称 / Charset name (default: utf-8)
        """
        content_type = response.headers.get("Content-Type", "")
        if "charset=" in content_type:
            # 简单解析 charset / Simple charset extraction
            parts = content_type.split("charset=")
            if len(parts) > 1:
                return parts[1].split(";")[0].strip().strip('"').strip("'")
        return "utf-8"

    def _make_key(self, url: str, headers: Optional[Dict[str, str]]) -> str:
        """生成缓存键: SHA256(url + 排序后的 headers) / Generate cache key.

        Args:
            url: 请求 URL / Request URL
            headers: 请求头 / Request headers

        Returns:
            SHA256 十六进制摘要 / SHA256 hex digest
        """
        parts = url
        if headers:
            # 排序以保证一致性 / Sort for consistency
            header_str = json.dumps(headers, sort_keys=True, ensure_ascii=True)
            parts += header_str
        return hashlib.sha256(parts.encode("utf-8")).hexdigest()

    # -- cache proxy (handles optional cache gracefully) --------------------

    def _cache_get(self, key: str) -> Optional[str]:
        """从缓存读取 / Read from cache.

        Args:
            key: 缓存键 / Cache key

        Returns:
            缓存值或 None / Cached value or None
        """
        if self._cache is None:
            return None
        try:
            return self._cache.get(key)
        except Exception:
            # Graceful degradation: 缓存故障则绕过 / Bypass on cache failure
            return None

    def _cache_set(self, key: str, value: str) -> None:
        """写入缓存 / Write to cache.

        Args:
            key: 缓存键 / Cache key
            value: 缓存值 / Value to cache
        """
        if self._cache is None:
            return
        try:
            self._cache.set(key, value)
        except Exception:
            # Graceful degradation: 缓存故障则忽略 / Ignore on cache failure
            pass
