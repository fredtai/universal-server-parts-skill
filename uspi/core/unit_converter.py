"""
USPI Unit Converter — SI Normalization Engine
USPI 单位转换器 — SI 标准化引擎

Provides zero-dependency normalization of server hardware specifications
to standard SI units using pure Python dictionaries and regular expressions.

以纯 Python 字典 + 正则表达式实现服务器硬件规格到标准 SI 单位的零依赖归一化。
"""

from __future__ import annotations

import re
from typing import Optional


class UnitConverter:
    """Unit standardization engine for server hardware specifications.
    服务器硬件规格的单位标准化引擎。

    Normalizes raw specification strings (e.g., "1.5TB", "2x 32GB", "3.5GHz")
    into standardized SI unit representations with confidence scores.

    将原始规格字符串（如 "1.5TB", "2x 32GB", "3.5GHz"）归一化为带置信度评分的
    标准 SI 单位表示。
    """

    # ------------------------------------------------------------------
    # 类级别常量 / Class-level constants
    # ------------------------------------------------------------------

    DIMENSIONS: list[str] = [
        "capacity",
        "frequency",
        "power",
        "dimension",
        "weight",
        "rpm",
        "voltage",
        "current",
        "temperature",
        "data_rate",
        "cache",
    ]
    """Supported dimension keys / 支持的维度键列表。"""

    STANDARD_UNITS: dict[str, str] = {
        "capacity": "GB",
        "frequency": "GHz",
        "power": "W",
        "dimension": "mm",
        "weight": "kg",
        "rpm": "RPM",
        "voltage": "V",
        "current": "A",
        "temperature": "°C",
        "data_rate": "Gbps",
        "cache": "MB",
    }
    """Standard (target) unit for each dimension / 每个维度的标准（目标）单位。"""

    # ------------------------------------------------------------------
    # 转换因子 / Conversion factors
    # 格式: {dimension: {unit_symbol: factor_to_standard_unit}}
    # ------------------------------------------------------------------
    CONVERSION_FACTORS: dict[str, dict[str, float]] = {
        "capacity": {
            "MB": 0.001,
            "GB": 1.0,
            "TB": 1000.0,
            "MiB": 1.0 / 953.67431640625,   # ≈ 0.001048576
            "GiB": 1.073741824,
            "TiB": 1099.511627776,
        },
        "frequency": {
            "Hz": 1e-9,
            "KHz": 1e-6,
            "MHz": 0.001,
            "GHz": 1.0,
        },
        "power": {
            "mW": 0.001,
            "W": 1.0,
            "kW": 1000.0,
            "BTU/hr": 0.293071,
            "BTU/h": 0.293071,
        },
        "dimension": {
            "mm": 1.0,
            "cm": 10.0,
            "m": 1000.0,
            "inch": 25.4,
            "in": 25.4,
            "\"": 25.4,
        },
        "weight": {
            "g": 0.001,
            "kg": 1.0,
            "lb": 0.453592,
            "oz": 0.0283495,
        },
        "rpm": {
            "RPM": 1.0,
            "r/min": 1.0,
        },
        "voltage": {
            "mV": 0.001,
            "V": 1.0,
            "kV": 1000.0,
        },
        "current": {
            "mA": 0.001,
            "A": 1.0,
        },
        "temperature": {
            "°C": 1.0,
            "°F": "special_fahrenheit",
            "K": "special_kelvin",
        },
        "data_rate": {
            "KB/s": 0.000008,
            "MB/s": 0.008,
            "Mbps": 0.001,
            "Gbps": 1.0,
        },
        "cache": {
            "MB": 1.0,
            "GB": 1000.0,
        },
    }

    # ------------------------------------------------------------------
    # 单位检测的正则模式 / Regex patterns for unit detection
    # 格式: {dimension: [(regex_pattern, canonical_unit), ...]}
    # 顺序很重要 — 先匹配更具体的模式 / Order matters — more specific first.
    # ------------------------------------------------------------------
    UNIT_PATTERNS: dict[str, list[tuple[str, str]]] = {
        "capacity": [
            (r"TiB\b", "TiB"),
            (r"GiB\b", "GiB"),
            (r"MiB\b", "MiB"),
            (r"TB\b", "TB"),
            (r"GB\b", "GB"),
            (r"MB\b", "MB"),
        ],
        "frequency": [
            (r"GHz\b", "GHz"),
            (r"MHz\b", "MHz"),
            (r"KHz\b", "KHz"),
            (r"Hz\b", "Hz"),
        ],
        "power": [
            (r"kW\b", "kW"),
            (r"mW\b", "mW"),
            (r"BTU/hr\b", "BTU/hr"),
            (r"BTU/h\b", "BTU/h"),
            (r"W\b", "W"),
        ],
        "dimension": [
            (r"inch\b", "inch"),
            (r"in\b", "in"),
            (r'"', '"'),
            (r"cm\b", "cm"),
            (r"mm\b", "mm"),
            (r"m\b", "m"),
        ],
        "weight": [
            (r"kg\b", "kg"),
            (r"lb\b", "lb"),
            (r"oz\b", "oz"),
            (r"g\b", "g"),
        ],
        "rpm": [
            (r"RPM\b", "RPM"),
            (r"r/min\b", "r/min"),
        ],
        "voltage": [
            (r"kV\b", "kV"),
            (r"mV\b", "mV"),
            (r"V\b", "V"),
        ],
        "current": [
            (r"mA\b", "mA"),
            (r"A\b", "A"),
        ],
        "temperature": [
            (r"°F\b", "°F"),
            (r"℉\b", "°F"),
            (r"°C\b", "°C"),
            (r"℃\b", "°C"),
            (r"K\b", "K"),
        ],
        "data_rate": [
            (r"Gbps\b", "Gbps"),
            (r"Mbps\b", "Mbps"),
            (r"MB/s\b", "MB/s"),
            (r"KB/s\b", "KB/s"),
        ],
        "cache": [
            (r"GB\b", "GB"),
            (r"MB\b", "MB"),
        ],
    }

    # ------------------------------------------------------------------
    # 数值提取正则 / Number extraction regex
    # ------------------------------------------------------------------
    # 匹配整数、小数、科学计数法 / Matches integers, decimals, scientific notation
    _NUMBER_RE = re.compile(r"[+-]?\d+\.?\d*([eE][+-]?\d+)?")

    # 匹配乘法格式如 "2x 32GB" 或 "2 x 32GB" / Matches multiplier format
    # 要求被乘数后必须紧跟数字开头的值，避免误匹配 "100 XYZ" 中的 X
    # Requires the multiplicand to start with a digit to avoid false matches like "100 XYZ"
    _MULTIPLIER_RE = re.compile(
        r"^(?P<multiplier>\d+(?:\.\d+)?)\s*[xX×]\s*(?P<value>\d.*)$"
    )

    # ------------------------------------------------------------------
    # 公共 API / Public API
    # ------------------------------------------------------------------

    @classmethod
    def normalize_value(cls, raw_str: str, dimension: str) -> dict:
        """Normalize a raw specification string to a standard SI unit value.
        将原始规格字符串归一化为标准 SI 单位值。

        Args:
            raw_str: The raw specification string, e.g., "1.5TB", "2x 32GB", "3.5GHz"
                     原始规格字符串，例如 "1.5TB", "2x 32GB", "3.5GHz"
            dimension: Dimension key from DIMENSIONS, e.g., "capacity", "frequency"
                       来自 DIMENSIONS 的维度键，例如 "capacity", "frequency"

        Returns:
            dict with keys:
                - value (float | None): Normalized numeric value / 归一化后的数值
                - unit (str): Standard unit symbol / 标准单位符号
                - raw (str): Original input string / 原始输入字符串
                - confidence (float): 1.0 = normal, 0.9 = unknown unit, 0.0 = parse failure
                                    1.0 = 正常, 0.9 = 未知单位, 0.0 = 解析失败
        """
        result: dict = {
            "value": None,
            "unit": cls.STANDARD_UNITS.get(dimension, ""),
            "raw": raw_str,
            "confidence": 0.0,
        }

        # Guard: empty input / 空输入保护
        if not raw_str or not raw_str.strip():
            return result

        # Guard: unsupported dimension / 不支持维度保护
        if dimension not in cls.DIMENSIONS:
            result["confidence"] = 0.0
            return result

        raw = raw_str.strip()
        confidence = 1.0

        # --- Step 1: Handle multiplier format (e.g., "2x 32GB", "2 x 32")
        # 步骤1：处理乘法格式（如 "2x 32GB", "2 x 32"）
        multiplier = 1.0
        multiplier_match = cls._MULTIPLIER_RE.match(raw)
        if multiplier_match:
            multiplier = float(multiplier_match.group("multiplier"))
            raw = multiplier_match.group("value").strip()

        # --- Step 2: Extract numeric value
        # 步骤2：提取数值
        try:
            numeric_value = cls._parse_number(raw)
        except ValueError:
            result["confidence"] = 0.0
            return result

        if numeric_value is None:
            result["confidence"] = 0.0
            return result

        # Apply multiplier / 应用乘数
        numeric_value *= multiplier

        # --- Step 3: Detect unit
        # 步骤3：检测单位
        detected_unit = cls._detect_unit(raw, dimension)

        if detected_unit is None:
            # Unknown unit — apply penalty but still try to return parsed number
            # 未知单位 — 应用惩罚但仍尝试返回已解析数值
            confidence = 0.9
            result["value"] = float(numeric_value)
            result["confidence"] = confidence
            return result

        # --- Step 4: Convert to standard unit
        # 步骤4：转换为标准单位
        conversion_table = cls.CONVERSION_FACTORS.get(dimension, {})
        factor = conversion_table.get(detected_unit)

        if factor is None:
            confidence = 0.9
            result["value"] = float(numeric_value)
            result["confidence"] = confidence
            return result

        # Handle special temperature conversions
        # 处理特殊温度转换
        if factor == "special_fahrenheit":
            # (°F - 32) × 5/9 = °C
            converted = (numeric_value - 32.0) * 5.0 / 9.0
        elif factor == "special_kelvin":
            # K - 273.15 = °C
            converted = numeric_value - 273.15
        else:
            # Standard linear conversion / 标准线性转换
            converted = numeric_value * factor

        result["value"] = float(converted)
        result["confidence"] = confidence
        return result

    @classmethod
    def _parse_number(cls, raw_str: str) -> float:
        """Extract the first numeric value from a string.
        从字符串中提取第一个数值。

        Supports integers, decimals, and scientific notation.
        Handles cases like "1.5TB", ">= 100", "~ 50", "3.5".
        支持整数、小数和科学计数法。
        处理如 "1.5TB", ">= 100", "~ 50", "3.5" 等情形。

        Args:
            raw_str: Input string containing a number / 包含数字的输入字符串

        Returns:
            float: Extracted numeric value / 提取的数值

        Raises:
            ValueError: If no number can be found / 如果找不到任何数字
        """
        raw = raw_str.strip()

        # Direct conversion for pure numeric strings / 纯数字字符串直接转换
        try:
            return float(raw)
        except ValueError:
            pass

        # Remove common prefix characters that may precede numbers
        # 移除可能出现在数字前的常见前缀字符
        cleaned = raw.lstrip("~>=<≈≤≥")

        # Find first number match / 查找第一个数字匹配
        match = cls._NUMBER_RE.search(cleaned)
        if match:
            return float(match.group())

        raise ValueError(f"No numeric value found in '{raw_str}' / 在 '{raw_str}' 中未找到数值")

    @classmethod
    def _detect_unit(cls, raw_str: str, dimension: str) -> Optional[str]:
        """Detect the unit symbol in a raw string for a given dimension.
        检测给定维度下原始字符串中的单位符号。

        Uses dimension-specific regex patterns to identify unit symbols.
        Matching is case-sensitive to avoid false positives.
        使用维度特定的正则表达式模式识别单位符号。
        匹配区分大小写以避免误报。

        Args:
            raw_str: The raw specification string / 原始规格字符串
            dimension: Dimension key from DIMENSIONS / 来自 DIMENSIONS 的维度键

        Returns:
            Canonical unit symbol if detected, None otherwise
            如果检测到则返回标准单位符号，否则返回 None
        """
        patterns = cls.UNIT_PATTERNS.get(dimension, [])
        for pattern, canonical_unit in patterns:
            if re.search(pattern, raw_str):
                return canonical_unit
        return None


# Public API declaration / 公共 API 声明
__all__ = ["UnitConverter"]
