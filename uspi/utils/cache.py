"""
SQLite-based cache module with TTL support for USPI.
USPI 基于 SQLite 的带 TTL 支持缓存模块。

Provides a persistent, thread-safe key-value cache backed by SQLite.
All timestamps use time.time() (seconds since epoch).
提供由 SQLite 支持的持久化、线程安全的键值缓存。
所有时间戳使用 time.time() (自纪元以来的秒数)。
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from typing import Optional

__all__ = ["Cache"]


class Cache:
    """
    SQLite-backed cache with TTL (time-to-live) support.
    基于 SQLite 的带 TTL (生存时间) 支持缓存。

    This cache is thread-safe via SQLite's internal locking mechanisms.
    It stores key-value pairs with an expiration timestamp.
    When a key expires, get() returns None and the entry is eventually
    removed by clear_expired().
    此缓存通过 SQLite 的内部锁定机制实现线程安全。
    它存储带过期时间戳的键值对。
    当键过期时, get() 返回 None, 该条目最终由 clear_expired() 清除。

    Usage / 用法:
        >>> cache = Cache(":memory:", default_ttl=3600)
        >>> cache.set("key", "value")
        >>> cache.get("key")
        'value'
        >>> cache._make_key("https://example.com", "param=1")
        'sha256_hash_string'
    """

    def __init__(self, db_path: str = ":memory:", default_ttl: int = 86400) -> None:
        """
        Initialize the cache with a SQLite database.
        使用 SQLite 数据库初始化缓存。

        Args / 参数:
            db_path: Path to the SQLite database file.
                     ":memory:" creates an in-memory database.
                     SQLite 数据库文件路径。":memory:" 创建内存数据库。
            default_ttl: Default time-to-live in seconds. Defaults to 86400 (1 day).
                         默认生存时间,单位为秒。默认为 86400 (1 天)。
        """
        self.db_path: str = db_path
        self.default_ttl: int = default_ttl
        self._conn: sqlite3.Connection = sqlite3.connect(
            db_path,
            check_same_thread=False,
        )
        self._init_table()

    def _init_table(self) -> None:
        """
        Create the cache table if it does not exist.
        如果缓存表不存在则创建。

        Schema / 模式:
            key TEXT PRIMARY KEY      -- cache key / 缓存键
            value TEXT                -- cached value / 缓存值
            expires_at REAL           -- expiration timestamp (time.time()) / 过期时间戳
        """
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    expires_at REAL
                )
                """
            )

    def get(self, key: str) -> Optional[str]:
        """
        Retrieve a value from the cache.
        从缓存中检索值。

        If the key has expired, it is deleted and None is returned.
        如果键已过期,则删除该键并返回 None。

        Args / 参数:
            key: The cache key.
                 缓存键。

        Returns / 返回:
            The cached value, or None if not found or expired.
            缓存的值,如果未找到或已过期则返回 None。
        """
        now: float = time.time()
        cursor: sqlite3.Cursor = self._conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?",
            (key,),
        )
        row: Optional[tuple[str, float]] = cursor.fetchone()
        if row is None:
            return None
        value: str = row[0]
        expires_at: float = row[1]
        if now > expires_at:
            # Expired: delete and return None / 已过期:删除并返回 None
            self.delete(key)
            return None
        return value

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """
        Store a value in the cache with an optional TTL.
        将值存入缓存,可指定 TTL。

        Args / 参数:
            key: The cache key.
                 缓存键。
            value: The value to cache.
                   要缓存的值。
            ttl: Time-to-live in seconds. If None, uses default_ttl.
                 生存时间,单位为秒。如果为 None,使用 default_ttl。
        """
        effective_ttl: int = ttl if ttl is not None else self.default_ttl
        expires_at: float = time.time() + effective_ttl
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO cache (key, value, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    expires_at = excluded.expires_at
                """,
                (key, value, expires_at),
            )

    def delete(self, key: str) -> None:
        """
        Remove a key from the cache.
        从缓存中删除键。

        Args / 参数:
            key: The cache key to delete.
                 要删除的缓存键。
        """
        with self._conn:
            self._conn.execute(
                "DELETE FROM cache WHERE key = ?",
                (key,),
            )

    def clear_expired(self) -> None:
        """
        Remove all expired entries from the cache.
        清除缓存中所有已过期的条目。

        This should be called periodically to reclaim disk space
        when using a file-based database.
        当使用基于文件的数据库时,应定期调用此方法来回收磁盘空间。
        """
        now: float = time.time()
        with self._conn:
            self._conn.execute(
                "DELETE FROM cache WHERE expires_at < ?",
                (now,),
            )

    def _make_key(self, *parts: str) -> str:
        """
        Generate a SHA-256 cache key from the given string parts.
        根据给定的字符串部分生成 SHA-256 缓存键。

        This is typically used to create a unique key from a URL
        and its parameters.
        这通常用于从 URL 及其参数创建唯一键。

        Args / 参数:
            *parts: String parts to concatenate and hash.
                    要连接并哈希的字符串部分。

        Returns / 返回:
            A SHA-256 hex digest string.
            SHA-256 十六进制摘要字符串。
        """
        raw: str = "".join(parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def close(self) -> None:
        """
        Close the SQLite connection.
        关闭 SQLite 连接。

        Call this when the cache is no longer needed to release resources.
        当不再需要缓存时调用此方法以释放资源。
        """
        self._conn.close()

    def __del__(self) -> None:
        """Destructor to ensure connection is closed."""
        try:
            self._conn.close()
        except Exception:
            pass
