"""
uspi/core/exporter.py

多格式导出引擎 / Multi-format Export Engine

支持: JSON / Markdown 表格 / CSV(Excel 兼容) / 紧凑文本
Supports: JSON / Markdown Table / CSV(Excel-ready) / Compact Text

Excel 工作流 / Excel Workflow:
1. to_csv(include_bom=True) → Excel 直接打开，中文正常
2. to_excel_pasteable() → Markdown 表格 → 复制粘贴到 Excel/Google Sheets
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List, Optional

from uspi.core.adapters.base import ServerPart

# ---------------------------------------------------------------------------
# 模块级常量 / Module-level constants
# ---------------------------------------------------------------------------

# ISO 时间格式字符串 / ISO time format string
_ISO_FMT: str = "%Y-%m-%dT%H:%M:%SZ"

# Markdown 表格分隔符（预构建避免循环内重复创建）
_MD_SEPARATOR: str = "|:---:"

# 表头映射（模块级常量避免每次调用重建）/ Header maps as module-level constants
_ZH_HEADERS: dict[str, str] = {
    "part_number": "零件号",
    "manufacturer": "厂商",
    "manufacturer_zh": "厂商(中)",
    "category": "分类",
    "category_zh": "分类(中)",
    "description": "描述",
    "description_zh": "描述(中)",
    "specifications": "规格",
    "raw_specifications": "原始规格",
    "sources": "货源",
    "median_price_usd": "美元价",
    "price_range_usd": "价格区间",
    "confidence_score": "可信度",
    "last_updated": "更新时间",
    "oem_brand": "OEM品牌",
    "unit_system": "单位体系",
}

_EN_HEADERS: dict[str, str] = {
    "part_number": "Part Number",
    "manufacturer": "Manufacturer",
    "manufacturer_zh": "Mfr (zh)",
    "category": "Category",
    "category_zh": "Category (zh)",
    "description": "Description",
    "description_zh": "Desc (zh)",
    "specifications": "Specifications",
    "raw_specifications": "Raw Specs",
    "sources": "Sources",
    "median_price_usd": "USD Price",
    "price_range_usd": "Price Range",
    "confidence_score": "Confidence",
    "last_updated": "Updated",
    "oem_brand": "OEM Brand",
    "unit_system": "Unit System",
}

# 错误消息常量 / Error message constants
_ERR_PART_NUMBER_REQUIRED: str = "[Error / 错误] part_number required / 必须提供零件号"
_ERR_NEED_2_PARTS: str = "[Error / 错误] Need >=2 part numbers / 至少需 2 个零件号"
_ERR_NOT_FOUND: str = "[Not Found / 未找到]"

# ---------------------------------------------------------------------------
# 预定义字段子集（Token 优化）/ Predefined field subsets (Token optimization)
# ---------------------------------------------------------------------------

COMPACT_FIELDS: list[str] = [
    "part_number",
    "manufacturer",
    "category",
    "median_price_usd",
    "confidence_score",
]
"""最小字段集，Token 消耗最低 / Minimal field set, lowest Token usage."""

STANDARD_FIELDS: list[str] = [
    "part_number",
    "manufacturer",
    "manufacturer_zh",
    "category_zh",
    "description_zh",
    "specifications",
    "median_price_usd",
    "confidence_score",
]
"""标准字段集，平衡信息量与 Token 消耗 / Standard field set, balanced info vs Tokens."""

FULL_FIELDS: Optional[list[str]] = None
"""所有字段 / All fields."""


class Exporter:
    """多格式导出引擎：将 ServerPart 列表导出为多种格式。

    Multi-format export engine: Exports ServerPart lists to multiple formats.

    支持 JSON、Markdown 表格、CSV（带 UTF-8 BOM，Excel 兼容）、
    专为 Excel 粘贴优化的 Markdown，以及超紧凑文本。
    Supports JSON, Markdown tables, CSV (with UTF-8 BOM, Excel-compatible),
    Excel-pasteable Markdown, and ultra-compact text.

    所有方法均为静态方法，无需实例化即可使用。
    All methods are static — no instantiation required.
    """

    # ------------------------------------------------------------------
    # JSON 导出 / JSON Export
    # ------------------------------------------------------------------

    @staticmethod
    def to_json(
        parts: list[ServerPart],
        indent: Optional[int] = None,
        fields: Optional[list[str]] = None,
    ) -> str:
        """导出为 JSON 字符串。

        Export as a JSON string.

        Args:
            parts: ServerPart 列表 / List of ServerPart objects.
            indent: 缩进空格数，None 表示紧凑格式 / Indent spaces, None for compact.
            fields: 字段子集，None 表示全部字段 / Field subset, None for all fields.

        Returns:
            JSON 格式字符串 / JSON formatted string.
        """
        data: list[dict] = []
        for p in parts:
            filtered: dict = Exporter._filter_fields(p, fields)
            data.append(filtered)
        return json.dumps(data, ensure_ascii=False, indent=indent, default=str)

    # ------------------------------------------------------------------
    # Markdown 表格导出 / Markdown Table Export
    # ------------------------------------------------------------------

    @staticmethod
    def to_markdown(
        parts: list[ServerPart],
        lang: str = "zh",
        fields: Optional[list[str]] = None,
    ) -> str:
        """导出为 Markdown 表格（可直接粘贴到 Excel）。

        Export as a Markdown table (directly pasteable into Excel).

        使用标准 Markdown 表格语法，列对齐，UTF-8 编码。
        Uses standard Markdown table syntax with column alignment.

        Args:
            parts: ServerPart 列表 / List of ServerPart objects.
            lang: 语言 "zh" 或 "en" / Language code.
            fields: 字段子集，None 使用默认字段 / Field subset, None for defaults.

        Returns:
            Markdown 表格字符串 / Markdown table string.
        """
        if not parts:
            return "_No data / 无数据_"

        if fields is None:
            fields = STANDARD_FIELDS

        # 确定表头 / Determine headers
        headers: list[str] = Exporter._headers_for_fields(fields, lang)

        # 分隔符行一次性构建（循环外）/ Build separator once (outside loop)
        sep: str = "|" + "|".join([":---" for _ in headers]) + "|"

        lines: list[str] = [
            "| " + " | ".join(headers) + " |",
            sep,
        ]

        for p in parts:
            row: list[str] = Exporter._row_values(p, fields, lang)
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # CSV 导出（Excel 兼容）/ CSV Export (Excel-compatible)
    # ------------------------------------------------------------------

    @staticmethod
    def to_csv(
        parts: list[ServerPart],
        lang: str = "zh",
        include_bom: bool = True,
        fields: Optional[list[str]] = None,
    ) -> str:
        """导出为 CSV 字符串（默认带 UTF-8 BOM，Excel 中文不乱码）。

        Export as a CSV string (default with UTF-8 BOM for Excel Chinese support).

        BOM (Byte Order Mark) \ufeff 放在文件开头，告诉 Excel 使用 UTF-8 编码打开，
        避免中文乱码。
        The BOM prefix tells Excel to open the file with UTF-8 encoding,
        preventing Chinese character garbling.

        Args:
            parts: ServerPart 列表 / List of ServerPart objects.
            lang: 语言 "zh" 或 "en" / Language code.
            include_bom: 是否包含 UTF-8 BOM 前缀 / Whether to include UTF-8 BOM.
            fields: 字段子集 / Field subset.

        Returns:
            CSV 格式字符串 / CSV formatted string.
        """
        if not parts:
            return "\ufeff" if include_bom else ""

        if fields is None:
            fields = STANDARD_FIELDS

        output: io.StringIO = io.StringIO()

        # 写入 BOM（Excel UTF-8 识别标记）/ Write BOM (Excel UTF-8 recognition marker)
        if include_bom:
            output.write("\ufeff")

        writer = csv.writer(output, lineterminator="\n")

        # 表头 / Headers
        headers: list[str] = Exporter._headers_for_fields(fields, lang)
        writer.writerow(headers)

        # 数据行 / Data rows
        for p in parts:
            row: list[str] = Exporter._row_values(p, fields, lang)
            writer.writerow(row)

        return output.getvalue()

    # ------------------------------------------------------------------
    # Excel 粘贴优化导出 / Excel Paste-optimized Export
    # ------------------------------------------------------------------

    @staticmethod
    def to_excel_pasteable(
        parts: list[ServerPart],
        lang: str = "zh",
    ) -> str:
        """专为 Excel 粘贴优化的 Markdown 表格。

        Excel-optimized Markdown table for copy-paste.

        列: 零件号 | 厂商(中) | 分类(中) | 规格摘要 | 美元价 | 货源 | 可信度
        Columns: Part Number | Mfr(zh) | Cat(zh) | Spec Summary | USD | Sources | Confidence

        用户可复制 → 粘贴到 Excel / WPS / Google Sheets。
        User can copy → paste into Excel / WPS / Google Sheets.

        Args:
            parts: ServerPart 列表 / List of ServerPart objects.
            lang: 语言 "zh" 或 "en" / Language code.

        Returns:
            Markdown 表格字符串 / Markdown table string.
        """
        if not parts:
            return "_No data / 无数据_"

        if lang == "zh":
            headers: list[str] = [
                "零件号", "厂商", "分类", "规格摘要", "美元价", "货源", "可信度",
            ]
        else:
            headers = [
                "Part Number", "Manufacturer", "Category",
                "Spec Summary", "USD Price", "Sources", "Confidence",
            ]

        lines: list[str] = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join([":---" for _ in headers]) + "|")

        for p in parts:
            spec_sum: str = Exporter._specs_summary(p.specifications)
            price_str: str = f"${p.median_price_usd:.2f}" if p.median_price_usd is not None else "N/A"
            src_count: str = str(len(p.sources))
            conf_str: str = f"{p.confidence_score:.0%}"
            cat_display: str = p.category_zh if lang == "zh" and p.category_zh else p.category
            mfr_display: str = p.manufacturer_zh if lang == "zh" and p.manufacturer_zh else p.manufacturer

            row: list[str] = [
                p.part_number,
                mfr_display,
                cat_display,
                spec_sum,
                price_str,
                src_count,
                conf_str,
            ]
            lines.append("| " + " | ".join(row) + " |")

        # 添加统计汇总行 / Add summary stats row
        lines.append("")
        valid_prices: list[float] = [
            p.median_price_usd for p in parts if p.median_price_usd is not None
        ]
        if valid_prices:
            avg_price: float = sum(valid_prices) / len(valid_prices)
            total_sources: int = sum(len(p.sources) for p in parts)
            if lang == "zh":
                lines.append(f"_共 {len(parts)} 个零件 | 均价 ${avg_price:.2f} | 总货源 {total_sources}_")
            else:
                lines.append(f"_{len(parts)} parts | Avg ${avg_price:.2f} | {total_sources} total sources_")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 紧凑文本导出 / Compact Text Export
    # ------------------------------------------------------------------

    @staticmethod
    def to_compact_text(
        parts: list[ServerPart],
        lang: str = "zh",
    ) -> str:
        """超紧凑文本（Token 效率最优）。每行一个零件。

        Ultra-compact text (Token-optimal). One part per line.

        格式: 零件号|厂商|分类|价格|规格|货源:数量|可信度:百分比
        Format: part_number|mfr|cat|price|specs|src:N|conf:%

        Args:
            parts: ServerPart 列表 / List of ServerPart objects.
            lang: 语言 "zh" 或 "en" / Language code.

        Returns:
            紧凑文本字符串 / Compact text string.
        """
        if not parts:
            return "N/A"

        lines: list[str] = []
        for p in parts:
            cat: str = p.category_zh if lang == "zh" and p.category_zh else p.category
            price: str = f"${p.median_price_usd:.0f}" if p.median_price_usd else "N/A"
            spec_sum: str = Exporter._specs_summary(p.specifications, max_len=20)
            srcs: str = str(len(p.sources))
            line: str = (
                f"{p.part_number}|{p.manufacturer}|{cat}|{price}|"
                f"{spec_sum}|src:{srcs}|conf:{p.confidence_score:.0%}"
            )
            lines.append(line)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 内部工具方法 / Internal utility methods
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_fields(part: ServerPart, fields: Optional[list[str]] = None) -> dict:
        """按字段子集过滤 ServerPart（Token 优化）。

        Filter ServerPart by field subset (Token optimization).

        将 ServerPart 转为字典后，仅保留指定字段。如果 fields 为 None，
        返回所有字段。
        Converts ServerPart to dict, keeps only specified fields. If fields is None,
        returns all fields.

        Args:
            part: ServerPart 实例 / ServerPart instance.
            fields: 字段名列表，None 表示全部 / Field name list, None for all.

        Returns:
            过滤后的字典 / Filtered dictionary.
        """
        # 将 dataclass 转为字典 / Convert dataclass to dict
        part_dict: dict[str, Any] = {}
        for key in dir(part):
            if key.startswith("_"):
                continue
            val: Any = getattr(part, key)
            if callable(val):
                continue
            part_dict[key] = val

        # 排除 dataclass 内部属性 / Exclude dataclass internals
        part_dict = {k: v for k, v in part_dict.items() if not k.startswith("__")}

        # 使用 dataclasses.fields 更可靠地获取所有字段 / Use dataclasses.fields for reliability
        from dataclasses import fields as dc_fields

        all_field_names: list[str] = [f.name for f in dc_fields(part)]
        full_dict: dict[str, Any] = {k: getattr(part, k) for k in all_field_names}

        if fields is None:
            return full_dict

        # 递归过滤嵌套对象 / Recursively filter nested objects
        result: dict[str, Any] = {}
        for field_name in fields:
            if field_name in full_dict:
                val = full_dict[field_name]
                # 处理 PriceSource 列表 / Handle PriceSource list
                if field_name == "sources" and isinstance(val, list):
                    result[field_name] = [
                        Exporter._source_to_dict(s) for s in val
                    ]
                else:
                    result[field_name] = val
        return result

    @staticmethod
    def _source_to_dict(source: Any) -> dict:
        """将 PriceSource 转为字典。

        Convert a PriceSource to dictionary.

        Args:
            source: PriceSource 实例 / PriceSource instance.

        Returns:
            字典表示 / Dictionary representation.
        """
        from dataclasses import fields as dc_fields

        if hasattr(source, "__dataclass_fields__"):
            return {
                f.name: getattr(source, f.name)
                for f in dc_fields(source)
            }
        return dict(source) if isinstance(source, dict) else {}

    @staticmethod
    def _headers_for_fields(fields: list[str], lang: str) -> list[str]:
        """根据字段列表生成表头。

        Generate headers from a field list.
        使用模块级常量字典（O(1) 查表），避免每次调用重新创建大对象。

        Args:
            fields: 字段名列表 / Field name list.
            lang: 语言代码 / Language code.

        Returns:
            表头字符串列表 / List of header strings.
        """
        header_map: dict[str, str] = _ZH_HEADERS if lang == "zh" else _EN_HEADERS
        return [header_map.get(f, f) for f in fields]

    @staticmethod
    def _row_values(part: ServerPart, fields: list[str], lang: str) -> list[str]:
        """根据字段列表提取零件的行数据。

        Extract row data for a part based on field list.

        Args:
            part: ServerPart 实例 / ServerPart instance.
            fields: 字段名列表 / Field name list.
            lang: 语言代码 / Language code.

        Returns:
            字符串值列表 / List of string values.
        """
        values: list[str] = []
        for field_name in fields:
            val: Any = getattr(part, field_name, None)
            str_val: str = Exporter._format_value(val, field_name, lang)
            values.append(str_val)
        return values

    @staticmethod
    def _format_value(val: Any, field_name: str, lang: str) -> str:
        """将字段值格式化为字符串。

        Format a field value as a string.

        Args:
            val: 字段值 / Field value.
            field_name: 字段名 / Field name.
            lang: 语言代码 / Language code.

        Returns:
            格式化后的字符串 / Formatted string.
        """
        if val is None:
            return "N/A"

        if field_name == "specifications":
            return Exporter._specs_summary(val)

        if field_name == "sources":
            if isinstance(val, list):
                return str(len(val))
            return str(val)

        if field_name == "median_price_usd":
            if isinstance(val, (int, float)):
                return f"${val:.2f}"
            return str(val)

        if field_name == "price_range_usd":
            if isinstance(val, (tuple, list)) and len(val) == 2:
                return f"${val[0]:.2f} - ${val[1]:.2f}"
            return str(val)

        if field_name == "confidence_score":
            if isinstance(val, (int, float)):
                return f"{val:.0%}"
            return str(val)

        if field_name in ("description", "description_zh"):
            s: str = str(val)
            max_desc: int = 50
            if len(s) > max_desc:
                return s[:max_desc - 3] + "..."
            return s

        return str(val)

    @staticmethod
    def _specs_summary(specs: dict, max_len: int = 40) -> str:
        """生成规格摘要字符串。

        Generate a specification summary string.

        将规格字典压缩为简短的可读字符串，如 '32GB DDR4-2933, 1.2V'。
        Compresses spec dict into a short readable string.

        Args:
            specs: 规格字典 / Specification dictionary.
            max_len: 最大长度限制 / Maximum length limit.

        Returns:
            规格摘要字符串 / Spec summary string.
        """
        if not specs:
            return "-"

        parts: list[str] = []
        # 优先显示关键规格 / Prioritize key specs
        priority_keys: list[str] = [
            "capacity", "frequency", "type", "voltage", "power",
            "speed", "interface", "form_factor", "cache",
        ]

        for key in priority_keys:
            if key in specs:
                val: Any = specs[key]
                if isinstance(val, dict):
                    val_str: str = ""
                    v: Any = val.get("value")
                    u: str = val.get("unit", "")
                    if v is not None:
                        # 简化数值显示 / Simplify numeric display
                        try:
                            vf: float = float(v)
                            if vf == int(vf):
                                val_str = f"{int(vf)}{u}"
                            else:
                                val_str = f"{vf:g}{u}"
                        except (ValueError, TypeError):
                            val_str = f"{v}{u}"
                    if val_str:
                        parts.append(val_str)
                else:
                    val_str = str(val)
                    if val_str and val_str.lower() not in ("none", "null", "", "-"):
                        parts.append(val_str)

        # 如果没有优先键匹配，取前3个非空值 / If no priority keys, take first 3 non-empty
        if not parts:
            count: int = 0
            for key in list(specs.keys()):
                if count >= 3:
                    break
                val = specs[key]
                if isinstance(val, dict):
                    v = val.get("value")
                    u = val.get("unit", "")
                    if v is not None:
                        try:
                            vf = float(v)
                            val_str = f"{vf:g}{u}" if vf != int(vf) else f"{int(vf)}{u}"
                        except (ValueError, TypeError):
                            val_str = f"{v}{u}"
                    else:
                        continue
                else:
                    val_str = str(val)
                if val_str and val_str.lower() not in ("none", "null", "", "-"):
                    parts.append(val_str)
                    count += 1

        summary: str = ", ".join(parts)
        if len(summary) > max_len:
            summary = summary[:max_len - 3] + "..."
        return summary if summary else "-"


__all__ = [
    "Exporter",
    "COMPACT_FIELDS",
    "STANDARD_FIELDS",
    "FULL_FIELDS",
]
