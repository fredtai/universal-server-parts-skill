"""
tests/test_exporter.py

Exporter unit tests / Exporter 单元测试.

Coverage: to_json(), to_csv(), to_markdown(), to_excel_pasteable(),
to_compact_text(), with/without fields filtering.
"""

import json
import unittest

from uspi.core.adapters.base import PriceSource, ServerPart
from uspi.core.exporter import STANDARD_FIELDS, COMPACT_FIELDS, FULL_FIELDS, Exporter


def _make_test_part(
    pn: str = "0WX202",
    mfr: str = "DELL",
    mfr_zh: str = "戴尔",
    cat: str = "MEMORY",
    cat_zh: str = "内存",
    desc_zh: str = "32GB DDR4 RDIMM",
    price: float = 149.99,
    conf: float = 0.85,
) -> ServerPart:
    """Create a test ServerPart / 创建测试 ServerPart."""
    return ServerPart(
        part_number=pn,
        manufacturer=mfr,
        manufacturer_zh=mfr_zh,
        category=cat,
        category_zh=cat_zh,
        description=f"Dell {pn}",
        description_zh=desc_zh,
        specifications={"capacity_gb": 32, "speed_mhz": 2933},
        raw_specifications={"capacity": "32GB", "speed": "2933MHz"},
        sources=[
            PriceSource("Dell", "戴尔", price_usd=price, reliability_score=0.85),
        ],
        median_price_usd=price,
        price_range_usd=(price, price),
        confidence_score=conf,
    )


class TestExporterJson(unittest.TestCase):
    """Test to_json() / 测试 JSON 导出."""

    def test_json_basic(self) -> None:
        """JSON export basic / 基本 JSON 导出."""
        part = _make_test_part()
        result = Exporter.to_json([part])
        data = json.loads(result)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["part_number"], "0WX202")
        self.assertEqual(data[0]["manufacturer"], "DELL")

    def test_json_indent(self) -> None:
        """JSON with indent / 带缩进 JSON."""
        part = _make_test_part()
        result = Exporter.to_json([part], indent=2)
        self.assertIn("\n", result)

    def test_json_fields_filter(self) -> None:
        """JSON with fields filter / 字段过滤 JSON."""
        part = _make_test_part()
        result = Exporter.to_json([part], fields=["part_number", "median_price_usd"])
        data = json.loads(result)
        self.assertEqual(set(data[0].keys()), {"part_number", "median_price_usd"})

    def test_json_empty(self) -> None:
        """JSON empty list / 空列表 JSON."""
        result = Exporter.to_json([])
        self.assertEqual(json.loads(result), [])


class TestExporterCsv(unittest.TestCase):
    """Test to_csv() / 测试 CSV 导出."""

    def test_csv_with_bom(self) -> None:
        """CSV with BOM / 带 BOM 的 CSV."""
        part = _make_test_part()
        result = Exporter.to_csv([part], include_bom=True)
        self.assertTrue(result.startswith("\ufeff"))
        self.assertIn("0WX202", result)
        self.assertIn("DELL", result)

    def test_csv_without_bom(self) -> None:
        """CSV without BOM / 不带 BOM 的 CSV."""
        part = _make_test_part()
        result = Exporter.to_csv([part], include_bom=False)
        self.assertFalse(result.startswith("\ufeff"))
        self.assertIn("0WX202", result)

    def test_csv_empty(self) -> None:
        """CSV empty list / 空列表 CSV."""
        result = Exporter.to_csv([], include_bom=True)
        self.assertTrue(result.startswith("\ufeff"))


class TestExporterMarkdown(unittest.TestCase):
    """Test to_markdown() / 测试 Markdown 导出."""

    def test_markdown_basic(self) -> None:
        """Markdown table export / Markdown 表格导出."""
        part = _make_test_part()
        result = Exporter.to_markdown([part])
        self.assertIn("| part_number |", result)
        self.assertIn("|---|", result)
        self.assertIn("| 0WX202 |", result)

    def test_markdown_empty(self) -> None:
        """Markdown empty list / 空列表 Markdown."""
        result = Exporter.to_markdown([])
        self.assertEqual(result, "")

    def test_markdown_fields_filter(self) -> None:
        """Markdown with fields filter / 字段过滤 Markdown."""
        part = _make_test_part()
        result = Exporter.to_markdown([part], fields=["part_number", "manufacturer"])
        lines = result.strip().split("\n")
        self.assertIn("part_number", lines[0])
        self.assertIn("manufacturer", lines[0])
        # Only 2 data columns + separator
        self.assertNotIn("category", lines[0])


class TestExporterExcelPasteable(unittest.TestCase):
    """Test to_excel_pasteable() / 测试 Excel 可粘贴格式."""

    def test_excel_pasteable_basic(self) -> None:
        """Excel pasteable basic / 基本可粘贴格式."""
        part = _make_test_part()
        result = Exporter.to_excel_pasteable([part], lang="zh")
        self.assertIn("零件号", result)
        self.assertIn("0WX202", result)
        self.assertIn("戴尔", result)
        self.assertIn("$149.99", result)

    def test_excel_pasteable_en(self) -> None:
        """Excel pasteable English / 英文可粘贴格式."""
        part = _make_test_part()
        result = Exporter.to_excel_pasteable([part], lang="en")
        self.assertIn("Part Number", result)
        self.assertIn("DELL", result)

    def test_excel_pasteable_empty(self) -> None:
        """Excel pasteable empty / 空列表可粘贴格式."""
        result = Exporter.to_excel_pasteable([])
        self.assertEqual(result, "")


class TestExporterCompactText(unittest.TestCase):
    """Test to_compact_text() / 测试紧凑文本格式."""

    def test_compact_basic(self) -> None:
        """Compact text basic / 基本紧凑格式."""
        part = _make_test_part()
        result = Exporter.to_compact_text([part], lang="zh")
        self.assertIn("0WX202", result)
        self.assertIn("戴尔", result)
        self.assertIn("$150", result)

    def test_compact_en(self) -> None:
        """Compact text English / 英文紧凑格式."""
        part = _make_test_part()
        result = Exporter.to_compact_text([part], lang="en")
        self.assertIn("DELL", result)
        self.assertIn("MEMORY", result)

    def test_compact_multiple(self) -> None:
        """Compact text multiple parts / 多零件紧凑格式."""
        parts = [
            _make_test_part("0WX202", "DELL", "戴尔", "MEMORY", "内存"),
            _make_test_part("872736-001", "HP", "惠普", "MEMORY", "内存", price=129.99),
        ]
        result = Exporter.to_compact_text(parts, lang="zh")
        lines = result.strip().split("\n")
        self.assertEqual(len(lines), 2)

    def test_compact_empty(self) -> None:
        """Compact text empty / 空列表紧凑格式."""
        result = Exporter.to_compact_text([])
        self.assertEqual(result, "")


class TestExporterConstants(unittest.TestCase):
    """Test exported constants / 测试导出常量."""

    def test_compact_fields(self) -> None:
        """COMPACT_FIELDS defined / COMPACT_FIELDS 已定义."""
        self.assertIsInstance(COMPACT_FIELDS, list)
        self.assertIn("part_number", COMPACT_FIELDS)
        self.assertIn("median_price_usd", COMPACT_FIELDS)

    def test_standard_fields(self) -> None:
        """STANDARD_FIELDS defined / STANDARD_FIELDS 已定义."""
        self.assertIsInstance(STANDARD_FIELDS, list)
        self.assertIn("description_zh", STANDARD_FIELDS)

    def test_full_fields(self) -> None:
        """FULL_FIELDS is None / FULL_FIELDS 为 None."""
        self.assertIsNone(FULL_FIELDS)


if __name__ == "__main__":
    unittest.main()
