"""
USPI 日志工具 / USPI Logger

编码规范要求：
- ERROR/WARN/INFO/DEBUG 分级
- ERROR 日志必须包含: 时间 + 模块名 + 消息
- 生产环境关闭 DEBUG
- 禁止循环打印海量日志

零依赖实现，基于 print 输出到 stderr。
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional

__all__ = ["LogLevel", "Logger", "debug", "info", "warn", "error"]


class LogLevel(IntEnum):
    """日志级别 / Log levels"""

    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    SILENT = 100  # 完全静默 / completely silent


class Logger:
    """
    简单日志记录器 / Simple logger.

    使用方式 / Usage:
        >>> logger = Logger("module_name", level=LogLevel.INFO)
        >>> logger.error("Failed to fetch: %s", error_msg)
        >>> logger.info("Query completed: %s", part_number)
    """

    _global_level: LogLevel = LogLevel.INFO  # 全局默认级别 / global default level

    def __init__(self, name: str, level: Optional[LogLevel] = None) -> None:
        self.name = name
        self._level = level or self._global_level

    @classmethod
    def set_global_level(cls, level: LogLevel) -> None:
        """设置全局日志级别 / Set global log level"""
        cls._global_level = level

    def _log(self, level: LogLevel, msg: str, *args) -> None:
        """内部日志输出 / Internal log output"""
        if level < self._level:
            return
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        level_name = level.name
        formatted = msg % args if args else msg
        # 输出到 stderr（编码规范: 日志与 stdout 分离）
        # Print to stderr (coding standard: separate logs from stdout)
        print(
            f"[{timestamp}][{level_name}][{self.name}] {formatted}",
            file=sys.stderr,
        )

    def debug(self, msg: str, *args) -> None:
        """DEBUG 级别日志 / DEBUG level log"""
        self._log(LogLevel.DEBUG, msg, *args)

    def info(self, msg: str, *args) -> None:
        """INFO 级别日志 / INFO level log"""
        self._log(LogLevel.INFO, msg, *args)

    def warn(self, msg: str, *args) -> None:
        """WARN 级别日志 / WARN level log"""
        self._log(LogLevel.WARN, msg, *args)

    def error(self, msg: str, *args) -> None:
        """ERROR 级别日志（强制输出）/ ERROR level log (always output)"""
        self._log(LogLevel.ERROR, msg, *args)

    # 便捷工厂方法 / Convenience factory method

    @staticmethod
    def get_logger(name: str) -> Logger:
        """获取 Logger 实例 / Get logger instance"""
        return Logger(name)


# 模块级便捷函数 / Module-level convenience functions
_default_logger = Logger("uspi")


def debug(msg: str, *args) -> None:
    _default_logger.debug(msg, *args)


def info(msg: str, *args) -> None:
    _default_logger.info(msg, *args)


def warn(msg: str, *args) -> None:
    _default_logger.warn(msg, *args)


def error(msg: str, *args) -> None:
    _default_logger.error(msg, *args)
