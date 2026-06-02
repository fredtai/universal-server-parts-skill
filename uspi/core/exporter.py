"""
uspi/core/exporter.py

多格式导出引擎 / Multi-format Export Engine.

支持 JSON / Markdown / CSV(Excel兼容) / 扁平Markdown / 超紧凑文本。
Supports JSON / Markdown / CSV(Excel-compatible) / flat Markdown / ultra-compact text.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List, Optional

from uspi.core.adapters.base import ServerPart

# 预定义字段子集 / Predefined field subsets
COMPACT_FIELDS = [
    "part_number", "manufacturer", "category", "median_price_usd", "confidence_score",
]
STANDARD_FIELDS = [
    "part_number", "manufacturer", "manufacturer_zh", "category_zh",
    "description_zh", "specifications", "median_price_usd", "confidence_score",
]
FULL_FIELDS: Optional[List[str]] = None  # 所有字段 / All fields


class Exporter:
    """多格式导出引擎 / Multi-format export engine.

    将 ServerPart 列表导出为多种格式，支持字段过滤以优化 Token 消耗。
    Exports list of ServerPart to multiple formats with field filtering for
    Token optimization.
    """

    @staticmethod
    def _filter_fields(
        part: ServerPart, fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """提取指定字段的字典 / Extract dict with specified fields."""
        data: Dict[str, Any] = {
            "part_number": part.part_number,
            "manufacturer": part.manufacturer,
            "manufacturer_zh": part.manufacturer_zh,
            "oem_brand": part.oem_brand,
            "category": part.category,
            "category_zh": part.category_zh,
            "description": part.description,
            "description_zh": part.description_zh,
            "specifications": part.specifications,
            "raw_specifications": part.raw_specifications,
            "sources": [
                {
                    "source_name": s.source_name,
                    "source_name_zh": s.source_name_zh,
                    "price_usd": s.price_usd,
                    "original_price": s.original_price,
                    "original_currency": s.original_currency,
                    "url": s.url,
                    "in_stock": s.in_stock,
                    "condition": s.condition,
                    "reliability_score": s.reliability_score,
                    "last_seen": s.last_seen,
                }
                for s in part.sources
            ],
            "median_price_usd": part.median_price_usd,
            "price_range_usd": part.price_range_usd,
            "confidence_score": part.confidence_score,
            "last_updated": part.last_updated,
            "unit_system": part.unit_system,
        }
        if fields is not None:
            return {k: v for k, v in data.items() if k in fields}
        return data

    @classmethod
    def to_json(
        cls,
        parts: List[ServerPart],
        indent: Optional[int] = None,
        fields: Optional[List[str]] = None,
    ) -> str:
        """JSON 导出 / JSON export.

        Args:
            parts: ServerPart 列表 / List of ServerPart.
            indent: 缩进空格数 / Indentation spaces.
            fields: 指定字段子集 / Field subset.

        Returns:
            JSON 字符串 / JSON string.
        """
        data = [cls._filter_fields(p, fields) for p in parts]
        return json.dumps(data, indent=indent, ensure_ascii=False, default=str)

    @classmethod
    def to_markdown(
        cls,
        parts: List[ServerPart],
        lang: str = "zh",
        fields: Optional[List[str]] = None,
    ) -> str:
        """Markdown 表格导出 / Markdown table export.

        可直接粘贴到 Excel / Google Sheets。
        Can be pasted directly into Excel / Google Sheets.

        Args:
            parts: ServerPart 列表 / List of ServerPart.
            lang: 语言 "zh" 或 "en" / Language.
            fields: 指定字段子集 / Field subset.

        Returns:
            Markdown 表格字符串 / Markdown table string.
        """
        if not parts:
            return ""

        data = [cls._filter_fields(p, fields) for p in parts]
        if not data:
            return ""

        headers = list(data[0].keys())
        lines: List[str] = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join(["---"] * len(headers)) + "|")
        for row in data:
            values = []
            for h in headers:
                v = row.get(h, "")
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False, default=str)
                else:
                    v = str(v) if v is not None else ""
                values.append(v)
            lines.append("| " + " | ".join(values) + " |")

        return "\n".join(lines)

    @classmethod
    def to_csv(
        cls,
        parts: List[ServerPart],
        lang: str = "zh",
        include_bom: bool = True,
    ) -> str:
        """CSV 导出 / CSV export.

        默认带 UTF-8 BOM，Excel 直接打开中文不乱码。
        Default with UTF-8 BOM for Excel compatibility.

        Args:
            parts: ServerPart 列表 / List of ServerPart.
            lang: 语言 / Language.
            include_bom: 是否包含 BOM / Whether to include BOM.

        Returns:
            CSV 字符串 / CSV string.
        """
        if not parts:
            return "\ufeff" if include_bom else ""

        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")

        # 使用标准字段集作为 CSV 列 / Use standard fields as columns
        fieldnames = [
            "part_number", "manufacturer", "manufacturer_zh", "category",
            "category_zh", "description_zh", "median_price_usd",
            "confidence_score", "last_updated",
        ]
        writer.writerow(fieldnames)

        for part in parts:
            row = [
                part.part_number,
                part.manufacturer,
                part.manufacturer_zh,
                part.category,
                part.category_zh,
                part.description_zh,
                str(part.median_price_usd) if part.median_price_usd is not None else "",
                str(part.confidence_score),
                part.last_updated,
            ]
            writer.writerow(row)

        result = output.getvalue()
        if include_bom:
            result = "\ufeff" + result
        return result

    @classmethod
    def to_excel_pasteable(
        cls,
        parts: List[ServerPart],
        lang: str = "zh",
    ) -> str:
        """Excel 可粘贴 Markdown 表格 / Excel-pasteable Markdown table.

        列: 零件号 | 厂商 | 分类 | 规格摘要 | 美元价 | 货源数 | 可信度
        Columns: PN | Mfr | Category | Spec Summary | USD Price | Sources | Confidence

        Args:
            parts: ServerPart 列表 / List of ServerPart.
            lang: 语言 / Language.

        Returns:
            Markdown 表格字符串 / Markdown table string.
        """
        if not parts:
            return ""

        if lang == "zh":
            headers = ["零件号", "厂商", "分类", "规格摘要", "美元价", "货源数", "可信度"]
        else:
            headers = ["Part Number", "Manufacturer", "Category", "Spec Summary",
                       "USD Price", "Sources", "Confidence"]

        lines: List[str] = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for part in parts:
            # 规格摘要 / Spec summary
            specs_summary = ""
            if part.specifications:
                spec_items = []
                for k, v in list(part.specifications.items())[:3]:
                    spec_items.append(f"{k}={v}")
                specs_summary = ", ".join(spec_items)

            price_str = f"${part.median_price_usd:.2f}" if part.median_price_usd else "N/A"
            mfr = part.manufacturer_zh if lang == "zh" and part.manufacturer_zh else part.manufacturer
            cat = part.category_zh if lang == "zh" and part.category_zh else part.category

            row = [
                part.part_number,
                mfr,
                cat,
                specs_summary,
                price_str,
                str(len(part.sources)),
                f"{part.confidence_score:.2f}",
            ]
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    @classmethod
    def to_compact_text(
        cls,
        parts: List[ServerPart],
        lang: str = "zh",
    ) -> str:
        """超紧凑文本格式 / Ultra-compact text format.

        每行一个零件，仅核心字段。Token 效率最优。
        One part per line, core fields only. Optimal Token efficiency.

        Args:
            parts: ServerPart 列表 / List of ServerPart.
            lang: 语言 / Language.

        Returns:
            紧凑文本字符串 / Compact text string.
        """
        if not parts:
            return ""

        lines: List[str] = []
        for part in parts:
            price = f"${part.median_price_usd:.0f}" if part.median_price_usd else "$?"
            mfr = part.manufacturer_zh if lang == "zh" and part.manufacturer_zh else part.manufacturer
            cat = part.category_zh if lang == "zh" and part.category_zh else part.category
            line = f"{part.part_number} | {mfr} | {cat} | {price} | conf:{part.confidence_score:.1f}"
            lines.append(line)

        return "\n".join(lines)


__all__ = ["Exporter", "COMPACT_FIELDS", "STANDARD_FIELDS", "FULL_FIELDS"]
