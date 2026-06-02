"""
测试数据归一化器 / Tests for Normalizer

测试 Normalizer 的核心功能：数据归一化、规格转换、价格统计、多源聚合。
"""
import unittest
import sys
sys.path.insert(0, '.')

from uspi.core.normalizer import Normalizer
from uspi.core.adapters.base import PriceSource, ServerPart, CATEGORIES


class TestNormalizerBasic(unittest.TestCase):
    """基本归一化测试 / Basic normalization tests"""

    def setUp(self):
        self.norm = Normalizer()

    def test_normalize_basic(self):
        """Normalize basic raw data / 基本归一化"""
        raw = {
            "part_number": "0WX202",
            "manufacturer": "DELL",
            "description": "32GB DDR4 RDIMM",
        }
        result = self.norm.normalize(raw, "dell")
        self.assertIsInstance(result, ServerPart)
        self.assertEqual(result.part_number, "0WX202")
        self.assertEqual(result.manufacturer, "DELL")

    def test_normalize_with_specs(self):
        """Normalize with raw specifications / 带规格归一化"""
        raw = {
            "part_number": "TEST123",
            "manufacturer": "DELL",
            "raw_specifications": {"capacity": "32GB", "speed": "2933MHz"},
        }
        result = self.norm.normalize(raw, "dell")
        self.assertIn("capacity", result.raw_specifications)

    def test_normalize_with_sources(self):
        """Normalize with price sources / 带价格来源归一化"""
        raw = {
            "part_number": "TEST123",
            "manufacturer": "HP",
            "sources": [{"source_name": "Test", "price_usd": 100.0}],
        }
        result = self.norm.normalize(raw, "hp")
        self.assertEqual(len(result.sources), 1)


class TestMedianPrice(unittest.TestCase):
    """中位数价格计算测试 / Median price calculation tests"""

    def setUp(self):
        self.norm = Normalizer()

    def _make_sources(self, prices):
        return [PriceSource(
            source_name=f"s{i}", source_name_zh=f"源{i}",
            price_usd=p, original_price=p, original_currency="USD",
            url="", in_stock=True, condition="new",
            last_seen="2024-01-01T00:00:00Z", reliability_score=0.8
        ) for i, p in enumerate(prices)]

    def test_median_odd(self):
        """Median of odd count / 奇数个元素中位数"""
        sources = self._make_sources([100.0, 200.0, 300.0])
        result = self.norm.compute_median_price(sources)
        self.assertEqual(result, 200.0)

    def test_median_even(self):
        """Median of even count / 偶数个元素中位数"""
        sources = self._make_sources([100.0, 200.0, 300.0, 400.0])
        result = self.norm.compute_median_price(sources)
        self.assertEqual(result, 250.0)

    def test_median_empty(self):
        """Median of empty list / 空列表中位数"""
        result = self.norm.compute_median_price([])
        self.assertIsNone(result)

    def test_median_none_prices(self):
        """Median with None prices / None 价格中位数"""
        sources = [PriceSource(
            source_name="s", source_name_zh="源", price_usd=None,
            original_price=None, original_currency="USD", url="",
            in_stock=None, condition="new", last_seen="2024-01-01T00:00:00Z",
            reliability_score=0.5
        )]
        result = self.norm.compute_median_price(sources)
        self.assertIsNone(result)


class TestNormalizeSpecs(unittest.TestCase):
    """规格归一化测试 / Spec normalization tests"""

    def setUp(self):
        self.norm = Normalizer()

    def test_empty_specs(self):
        """Empty specs returns empty dict / 空规格返回空字典"""
        result = self.norm.normalize_specs({})
        self.assertEqual(result, {})

    def test_capacity_gb(self):
        """Normalize capacity GB / 容量 GB 归一化"""
        result = self.norm.normalize_specs({"capacity": "32GB"})
        self.assertIn("capacity", result)
        self.assertEqual(result["capacity"]["unit"], "GB")

    def test_frequency_mhz(self):
        """Normalize frequency MHz / 频率 MHz 归一化"""
        result = self.norm.normalize_specs({"speed": "3200MHz"})
        self.assertIn("speed", result)

    def test_power_watt(self):
        """Normalize power W / 功率 W 归一化"""
        result = self.norm.normalize_specs({"power": "750W"})
        self.assertIn("power", result)

    def test_unknown_spec_key(self):
        """Unknown spec key processed / 未知规格键处理"""
        result = self.norm.normalize_specs({"custom_field": "custom_value"})
        self.assertIn("custom_field", result)


if __name__ == "__main__":
    unittest.main()
