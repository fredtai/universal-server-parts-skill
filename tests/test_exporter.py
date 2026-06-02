"""
测试导出引擎 / Tests for Exporter

测试 JSON / Markdown / CSV(Excel) / 紧凑文本 导出格式。
"""
import unittest
import sys
sys.path.insert(0, '.')

from uspi.core.exporter import Exporter, COMPACT_FIELDS, STANDARD_FIELDS
from uspi.core.adapters.base import ServerPart, PriceSource


def _make_part(pn="0WX202", mfr="DELL", mfr_zh="戴尔", cat="MEMORY",
               cat_zh="内存", price=100.0):
    return ServerPart(
        part_number=pn, manufacturer=mfr, manufacturer_zh=mfr_zh,
        oem_brand=None, category=cat, category_zh=cat_zh,
        description="32GB DDR4 RDIMM", description_zh="32GB DDR4 RDIMM 内存",
        specifications={"capacity": 32.0}, raw_specifications={"capacity": "32GB"},
        sources=[PriceSource("Test", "测试源", price, price, "USD", "",
                            True, "new", "2024-01-01T00:00:00Z", 0.8)],
        median_price_usd=price, price_range_usd=(price, price),
        confidence_score=0.8, last_updated="2024-01-01T00:00:00Z"
    )


class TestExporterJson(unittest.TestCase):
    def test_json_basic(self):
        result = Exporter.to_json([_make_part()])
        self.assertIn("0WX202", result)
        self.assertIn("DELL", result)

    def test_json_empty(self):
        result = Exporter.to_json([])
        self.assertEqual(result, "[]")

    def test_json_fields_filter(self):
        result = Exporter.to_json([_make_part()], fields=["part_number", "manufacturer"])
        data = __import__('json').loads(result)
        self.assertEqual(list(data[0].keys()), ["part_number", "manufacturer"])


class TestExporterCsv(unittest.TestCase):
    def test_csv_with_bom(self):
        result = Exporter.to_csv([_make_part()])
        self.assertTrue(result.startswith("\ufeff"))
        self.assertIn("0WX202", result)

    def test_csv_without_bom(self):
        result = Exporter.to_csv([_make_part()], include_bom=False)
        self.assertFalse(result.startswith("\ufeff"))

    def test_csv_empty(self):
        result = Exporter.to_csv([])
        self.assertIn("\ufeff", result)


class TestExporterMarkdown(unittest.TestCase):
    def test_markdown_basic(self):
        result = Exporter.to_markdown([_make_part()])
        self.assertIn("|", result)
        self.assertIn("0WX202", result)
        self.assertIn("---", result)  # has separator

    def test_markdown_fields_filter(self):
        result = Exporter.to_markdown([_make_part()], fields=["part_number", "manufacturer"])
        self.assertIn("0WX202", result)


class TestExporterExcelPasteable(unittest.TestCase):
    def test_excel_pasteable_basic(self):
        result = Exporter.to_excel_pasteable([_make_part()])
        self.assertIn("|", result)
        self.assertIn("0WX202", result)

    def test_excel_pasteable_en(self):
        result = Exporter.to_excel_pasteable([_make_part()], lang="en")
        self.assertIn("Part Number", result)


class TestExporterCompactText(unittest.TestCase):
    def test_compact_basic(self):
        result = Exporter.to_compact_text([_make_part()])
        self.assertIn("0WX202", result)

    def test_compact_en(self):
        result = Exporter.to_compact_text([_make_part()], lang="en")
        self.assertIn("0WX202", result)


class TestExporterConstants(unittest.TestCase):
    def test_compact_fields(self):
        self.assertIsInstance(COMPACT_FIELDS, list)
        self.assertIn("part_number", COMPACT_FIELDS)

    def test_standard_fields(self):
        self.assertIsInstance(STANDARD_FIELDS, list)


if __name__ == "__main__":
    unittest.main()
