"""
Internationalization (i18n) support module for USPI.
USPI 国际化 (i18n) 支持模块。

Provides bilingual error messages in English (en) and Chinese (zh)
for all public API error scenarios.
为所有公共 API 错误场景提供英文 (en) 和中文 (zh) 双语错误消息。
"""

from __future__ import annotations

__all__ = ["I18nMessage"]


class I18nMessage:
    """
    Bilingual message provider for USPI error messages.
    USPI 错误消息的双语消息提供者。

    All error messages, docstrings, and schema descriptions simultaneously
    contain both English (en) and Chinese (zh) translations.
    所有错误消息、文档字符串和模式描述同时包含英文 (en) 和中文 (zh) 翻译。

    Usage / 用法:
        >>> I18nMessage.get("part_not_found", "en")
        'Part number not recognized'
        >>> I18nMessage.get("part_not_found", "zh")
        '零件号无法识别'
    """

    MESSAGES: dict[str, dict[str, str]] = {
        "part_not_found": {
            "en": "Part number not recognized",
            "zh": "零件号无法识别",
        },
        "fetch_failed": {
            "en": "Failed to fetch data",
            "zh": "获取数据失败",
        },
        "cache_miss": {
            "en": "Cache miss",
            "zh": "缓存未命中",
        },
        "rate_limited": {
            "en": "Rate limited",
            "zh": "请求频率受限",
        },
        "unknown_unit": {
            "en": "Unknown unit",
            "zh": "未知单位",
        },
        "currency_fetch_failed": {
            "en": "Currency fetch failed",
            "zh": "汇率获取失败",
        },
        "parser_no_match": {
            "en": "No pattern matched for part number",
            "zh": "零件号无匹配模式",
        },
        "adapter_disabled": {
            "en": "Adapter disabled due to fetch failure",
            "zh": "适配器因获取失败已禁用",
        },
    }

    @classmethod
    def get(cls, key: str, lang: str = "en") -> str:
        """
        Retrieve a bilingual message by key and language.
        根据键和语言检索双语消息。

        Args / 参数:
            key: The message key (e.g., "part_not_found").
                 消息键 (例如 "part_not_found")。
            lang: The language code, either "en" or "zh". Defaults to "en".
                  语言代码, "en" 或 "zh"。默认为 "en"。

        Returns / 返回:
            The translated message string. If the key is not found,
            returns the key itself. If the language is not found,
            falls back to English.
            翻译后的消息字符串。如果键未找到,返回键本身。
            如果语言未找到,回退到英文。
        """
        entry: dict[str, str] | None = cls.MESSAGES.get(key)
        if entry is None:
            return key
        return entry.get(lang, entry.get("en", key))
