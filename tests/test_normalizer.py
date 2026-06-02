"""
tests/test_normalizer.py

Normalizer unit tests / Normalizer 单元测试.

Coverage: normalize(), normalize_specs(), aggregate_sources(), median_price().
"""

import unittest

from uspi.core.adapters.base import PriceSource, ServerPart
from uspi.core.normalizer import Normalizer


class TestNormalizerBasic(unittest.TestCase):
    """Test normalize() / 测试 normalize()."""

    def setUp(self) -> None:
        self.norm = Normalizer()

    def test_normalize_basic(self) -> None:
        """Normalize basic raw data / 基本归一化."""
        raw = {
            "part_number": "0WX202",
            "manufacturer": "DELL",
            "manufacturer_zh": "戴尔",
            "category": "MEMORY",
            "description": "32GB DDR4 RDIMM",
            "description_zh": "32GB DDR4 RDIMM内存",
            "confidence_score": 0.85,
        }
        result = self.norm.normalize(raw, "dell")
        self.assertIsInstance(result, ServerPart)
        self.assertEqual(result.part_number, "0WX202")
        self.assertEqual(result.manufacturer, "DELL")
        self.assertEqual(result.category, "MEMORY")
        self.assertEqual(result.category_zh, "内存")

    def test_normalize_with_specs(self) -> None:
        """Normalize with raw specifications / 带规格归一化."""
        raw = {
            "part_number": "0WX202",
            "manufacturer": "DELL",
            "manufacturer_zh": "戴尔",
            "category": "MEMORY",
            "raw_specifications": {"capacity": "32GB", "frequency": "2933MHz"},
            "confidence_score": 0.9,
        }
        result = self.norm.normalize(raw)
        self.assertEqual(result.raw_specifications["capacity"], "32GB")
        self.assertIn("capacity_normalized", result.specifications)

    def test_normalize_with_sources(self) -> None:
        """Normalize with price sources / 带价格来源归一化."""
        raw = {
            "part_number": "0WX202",
            "manufacturer": "DELL",
            "manufacturer_zh": "戴尔",
            "category": "MEMORY",
            "sources": [
                {"source_name": "Dell", "source_name_zh": "戴尔", "price_usd": 150.0},
            ],
            "confidence_score": 0.8,
        }
        result = self.norm.normalize(raw)
        self.assertEqual(len(result.sources), 1)
        self.assertEqual(result.sources[0].price_usd, 150.0)


class TestNormalizeSpecs(unittest.TestCase):
    """Test normalize_specs() / 测试规格归一化."""

    def setUp(self) -> None:
        self.norm = Normalizer()

    def test_capacity_gb(self) -> None:
        """Normalize capacity GB / 容量 GB 归一化."""
        specs = {"capacity": "32GB"}
        result = self.norm.normalize_specs(specs)
        self.assertIn("capacity_normalized", result)
        self.assertAlmostEqual(result["capacity_normalized"]["value"], 32.0)

    def test_frequency_mhz(self) -> None:
        """Normalize frequency MHz / 频率 MHz 归一化."""
        specs = {"frequency": "3200MHz"}
        result = self.norm.normalize_specs(specs)
        self.assertIn("frequency_normalized", result)
        self.assertAlmostEqual(result["frequency_normalized"]["value"], 3.2, places=3)

    def test_power_watt(self) -> None:
        """Normalize power W / 功率 W 归一化."""
        specs = {"wattage": "750W"}
        result = self.norm.normalize_specs(specs)
        self.assertIn("wattage_normalized", result)
        self.assertEqual(result["wattage_normalized"]["value"], 750.0)

    def test_empty_specs(self) -> None:
        """Empty specs returns empty dict / 空规格返回空字典."""
        result = self.norm.normalize_specs({})
        self.assertEqual(result, {})

    def test_unknown_spec_key(self) -> None:
        """Unknown spec key preserved as-is / 未知规格键保留原样."""
        specs = {"custom_field": "custom_value"}
        result = self.norm.normalize_specs(specs)
        self.assertEqual(result["custom_field"], "custom_value")


class TestAggregateSources(unittest.TestCase):
    """Test aggregate_sources() / 测试多源聚合."""

    def setUp(self) -> None:
        self.norm = Normalizer()

    def test_single_source(self) -> None:
        """Aggregate single source / 单源聚合."""
        sources = [PriceSource("Test", "测试", price_usd=100.0, reliability_score=0.8)]
        result = self.norm.aggregate_sources(sources)
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["median_price_usd"], 100.0)
        self.assertEqual(result["min_price_usd"], 100.0)

    def test_multiple_sources(self) -> None:
        """Aggregate multiple sources / 多源聚合."""
        sources = [
            PriceSource("A", "A", price_usd=100.0, reliability_score=0.8),
            PriceSource("B", "B", price_usd=200.0, reliability_score=0.7),
            PriceSource("C", "C", price_usd=150.0, reliability_score=0.9),
        ]
        result = self.norm.aggregate_sources(sources)
        self.assertEqual(result["source_count"], 3)
        self.assertEqual(result["median_price_usd"], 150.0)
        self.assertEqual(result["min_price_usd"], 100.0)
        self.assertEqual(result["max_price_usd"], 200.0)

    def test_no_prices(self) -> None:
        """Sources with no prices / 无价格来源."""
        sources = [PriceSource("A", "A", price_usd=None)]
        result = self.norm.aggregate_sources(sources)
        self.assertIsNone(result["median_price_usd"])

    def test_empty_sources(self) -> None:
        """Empty sources / 空来源列表."""
        result = self.norm.aggregate_sources([])
        self.assertEqual(result["source_count"], 0)
        self.assertEqual(result["avg_reliability"], 0.0)


class TestMedianPrice(unittest.TestCase):
    """Test median_price() / 测试中位数价格."""

    def setUp(self) -> None:
        self.norm = Normalizer()

    def test_median_odd(self) -> None:
        """Median of odd count / 奇数个元素中位数."""
        sources = [
            PriceSource("A", "A", price_usd=100.0),
            PriceSource("B", "B", price_usd=200.0),
            PriceSource("C", "C", price_usd=150.0),
        ]
        result = self.norm.median_price(sources)
        self.assertEqual(result, 150.0)

    def test_median_even(self) -> None:
        """Median of even count / 偶数个元素中位数."""
        sources = [
            PriceSource("A", "A", price_usd=100.0),
            PriceSource("B", "B", price_usd=200.0),
        ]
        result = self.norm.median_price(sources)
        self.assertEqual(result, 150.0)

    def test_median_empty(self) -> None:
        """Median of empty list / 空列表中位数."""
        result = self.norm.median_price([])
        self.assertIsNone(result)

    def test_median_none_prices(self) -> None:
        """Median with None prices / None 价格中位数."""
        sources = [PriceSource("A", "A", price_usd=None)]
        result = self.norm.median_price(sources)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
