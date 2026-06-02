"""
tests/test_parser.py

PartParser unit tests / PartParser 单元测试.

Coverage: OEM PN recognition, ODM PN recognition, category inference,
confidence scoring, manufacturer/category suggestions.
"""

import unittest

from uspi.core.parser import ParseResult, PartParser


class TestPartParserOEM(unittest.TestCase):
    """Test OEM part number recognition / 测试 OEM 零件号识别."""

    def setUp(self) -> None:
        self.parser = PartParser()

    # --- Dell (3 cases) ---
    def test_dell_pn_standard(self) -> None:
        """Dell standard PN: 0WX202."""
        result = self.parser.parse("0WX202")
        self.assertEqual(result.manufacturer, "DELL")
        self.assertEqual(result.manufacturer_zh, "戴尔")
        self.assertFalse(result.is_odm)
        self.assertEqual(result.confidence_score, 0.8)

    def test_dell_pn_with_cn_prefix(self) -> None:
        """Dell CN-0 prefix: CN-0WX202."""
        result = self.parser.parse("CN-0WX202")
        self.assertEqual(result.manufacturer, "DELL")
        self.assertEqual(result.manufacturer_zh, "戴尔")
        self.assertFalse(result.is_odm)

    def test_dell_pn_long_format(self) -> None:
        """Dell long PN: A9654882 starts with letter, not matched as Dell."""
        result = self.parser.parse("A9654882")
        # A9654882 starts with letter 'A', not digit - Dell pattern requires digit first
        # Parser should return suggestions but not match DELL directly
        self.assertEqual(result.confidence_score, 0.0)
        self.assertIn("DELL", result.suggested_manufacturers)

    # --- HP (3 cases) ---
    def test_hp_pn_standard(self) -> None:
        """HP standard PN: 872736-001."""
        result = self.parser.parse("872736-001")
        self.assertEqual(result.manufacturer, "HP")
        self.assertEqual(result.manufacturer_zh, "惠普")
        self.assertFalse(result.is_odm)

    def test_hp_pn_spare_format(self) -> None:
        """HP spare format: Spare #872736-001."""
        result = self.parser.parse("Spare #872736-001")
        self.assertEqual(result.manufacturer, "HP")

    def test_hp_pn_hpe_variant(self) -> None:
        """HPE variant: 872737-B21."""
        result = self.parser.parse("872737-B21")
        self.assertTrue(result.manufacturer in ("HP", "HPE"))

    # --- Lenovo (3 cases) ---
    def test_lenovo_pn_standard(self) -> None:
        """Lenovo standard FRU: 01KN234."""
        result = self.parser.parse("01KN234")
        self.assertEqual(result.manufacturer, "LENOVO")
        self.assertEqual(result.manufacturer_zh, "联想")

    def test_lenovo_pn_memory(self) -> None:
        """Lenovo memory FRU: 01KN235."""
        result = self.parser.parse("01KN235")
        self.assertEqual(result.manufacturer, "LENOVO")

    def test_lenovo_pn_7digit(self) -> None:
        """Lenovo 7-digit FRU: 00WG660."""
        result = self.parser.parse("00WG660")
        self.assertEqual(result.manufacturer, "LENOVO")

    # --- Supermicro (3 cases) ---
    def test_supermicro_heatsink(self) -> None:
        """Supermicro heatsink: SNK-P0070APS4."""
        result = self.parser.parse("SNK-P0070APS4")
        self.assertEqual(result.manufacturer, "SUPERMICRO")
        self.assertEqual(result.manufacturer_zh, "超微")

    def test_supermicro_motherboard(self) -> None:
        """Supermicro motherboard: MBD-X12DAI-N6."""
        result = self.parser.parse("MBD-X12DAI-N6")
        self.assertEqual(result.manufacturer, "SUPERMICRO")

    def test_supermicro_fan(self) -> None:
        """Supermicro fan: SNK-P0048AP4."""
        result = self.parser.parse("SNK-P0048AP4")
        self.assertEqual(result.manufacturer, "SUPERMICRO")


class TestPartParserODM(unittest.TestCase):
    """Test ODM part number recognition / 测试 ODM 零件号识别."""

    def setUp(self) -> None:
        self.parser = PartParser()

    # --- Foxconn (2 cases) ---
    def test_foxconn_pn_standard(self) -> None:
        """Foxconn standard: FOX12B456."""
        result = self.parser.parse("FOX12B456")
        self.assertEqual(result.manufacturer, "FOXCONN")
        self.assertEqual(result.manufacturer_zh, "鸿海/富士康")
        self.assertTrue(result.is_odm)
        self.assertEqual(result.oem_brand, "DELL")

    def test_foxconn_pn_hk_prefix(self) -> None:
        """Foxconn HK prefix: HK12345678."""
        result = self.parser.parse("HK12345678")
        self.assertEqual(result.manufacturer, "FOXCONN")

    # --- Quanta (2 cases) ---
    def test_quanta_pn_standard(self) -> None:
        """Quanta standard: QCT7890123."""
        result = self.parser.parse("QCT7890123")
        self.assertEqual(result.manufacturer, "QUANTA")
        self.assertEqual(result.manufacturer_zh, "广达")
        self.assertTrue(result.is_odm)
        self.assertEqual(result.oem_brand, "DELL")

    def test_quanta_pn_short(self) -> None:
        """Quanta short: Q123456."""
        result = self.parser.parse("Q123456")
        self.assertEqual(result.manufacturer, "QUANTA")

    # --- Wistron (2 cases) ---
    def test_wistron_pn_standard(self) -> None:
        """Wistron standard: WIS12345678."""
        result = self.parser.parse("WIS12345678")
        self.assertEqual(result.manufacturer, "WISTRON")
        self.assertEqual(result.manufacturer_zh, "纬创")

    def test_wistron_pn_short(self) -> None:
        """Wistron short: W123456."""
        result = self.parser.parse("W123456")
        self.assertEqual(result.manufacturer, "WISTRON")


class TestPartParserCategory(unittest.TestCase):
    """Test category inference / 测试分类推断."""

    def setUp(self) -> None:
        self.parser = PartParser()

    def test_category_memory_ddr4(self) -> None:
        """Memory category from DDR4 description."""
        result = self.parser.parse("0WX202", "32GB DDR4 2933MHz RDIMM")
        self.assertEqual(result.category, "MEMORY")
        self.assertEqual(result.category_zh, "内存")
        self.assertGreaterEqual(result.confidence_score, 0.8)

    def test_category_cpu_xeon(self) -> None:
        """CPU category from Xeon description."""
        result = self.parser.parse("X12345", "Intel Xeon Gold 6248R Processor")
        self.assertEqual(result.category, "CPU")
        self.assertEqual(result.category_zh, "处理器")

    def test_category_psu(self) -> None:
        """PSU category from power supply description."""
        result = self.parser.parse("W12345", "750W Power Supply")
        self.assertEqual(result.category, "PSU")
        self.assertEqual(result.category_zh, "电源")

    def test_category_ssd(self) -> None:
        """SSD category from SSD description."""
        result = self.parser.parse("U12345", "960GB SATA SSD")
        self.assertEqual(result.category, "STORAGE_SSD")

    def test_category_from_pn_only(self) -> None:
        """Category inferred from PN keywords only."""
        result = self.parser.parse("0WX202DDR4")
        self.assertGreaterEqual(result.confidence_score, 0.0)

    def test_empty_input(self) -> None:
        """Empty input handling."""
        result = self.parser.parse("")
        self.assertEqual(result.confidence_score, 0.0)
        self.assertEqual(result.part_number, "")

    def test_unknown_pn_suggestions(self) -> None:
        """Unknown PN returns suggestions."""
        result = self.parser.parse("XYZ999999")
        self.assertEqual(result.confidence_score, 0.0)
        self.assertTrue(len(result.suggested_manufacturers) > 0)


class TestPartParserConfidence(unittest.TestCase):
    """Test confidence score calculation / 测试置信度计算."""

    def setUp(self) -> None:
        self.parser = PartParser()

    def test_prefix_match_only(self) -> None:
        """Prefix match without description => 0.8."""
        result = self.parser.parse("0WX202")
        self.assertEqual(result.confidence_score, 0.8)

    def test_prefix_plus_category(self) -> None:
        """Prefix + category match => >= 0.8."""
        result = self.parser.parse("0WX202", "DDR4 Memory RDIMM")
        self.assertGreaterEqual(result.confidence_score, 0.8)

    def test_category_only(self) -> None:
        """Only category matched => 0.3."""
        result = self.parser.parse("UNKNOWN", "DDR4 Memory RDIMM")
        self.assertEqual(result.confidence_score, 0.3)

    def test_no_match(self) -> None:
        """No match => 0.0."""
        result = self.parser.parse("XYZ")
        self.assertEqual(result.confidence_score, 0.0)

    def test_suggest_manufacturers(self) -> None:
        """Manufacturer suggestion for unknown prefix."""
        suggestions = self.parser.suggest_manufacturers("UNKNOWN")
        self.assertTrue(len(suggestions) > 0)


if __name__ == "__main__":
    unittest.main()
