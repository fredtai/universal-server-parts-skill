"""
tests/test_unit_converter.py

UnitConverter unit tests / UnitConverter 单元测试.

Coverage: capacity, frequency, power, temperature, data_rate conversions
plus unknown/edge case handling.
"""

import unittest

from uspi.core.unit_converter import UnitConverter


class TestCapacityConversion(unittest.TestCase):
    """Test capacity dimension / 测试容量维度."""

    def test_gb_direct(self) -> None:
        """GB -> GB (identity)."""
        result = UnitConverter.normalize_value("32GB", "capacity")
        self.assertAlmostEqual(result["value"], 32.0, places=3)
        self.assertEqual(result["unit"], "GB")
        self.assertEqual(result["confidence"], 1.0)

    def test_tb_to_gb(self) -> None:
        """TB -> GB."""
        result = UnitConverter.normalize_value("1.5TB", "capacity")
        self.assertAlmostEqual(result["value"], 1500.0, places=3)
        self.assertEqual(result["unit"], "GB")

    def test_multiplier_format(self) -> None:
        """2x 32GB -> 64GB."""
        result = UnitConverter.normalize_value("2x 32GB", "capacity")
        self.assertAlmostEqual(result["value"], 64.0, places=3)

    def test_tib_to_gb(self) -> None:
        """TiB -> GB."""
        result = UnitConverter.normalize_value("2TiB", "capacity")
        self.assertAlmostEqual(result["value"], 2199.023, places=1)

    def test_mib_to_gb(self) -> None:
        """MiB -> GB (approx)."""
        result = UnitConverter.normalize_value("1024MiB", "capacity")
        self.assertAlmostEqual(result["value"], 1.074, places=2)


class TestFrequencyConversion(unittest.TestCase):
    """Test frequency dimension / 测试频率维度."""

    def test_mhz_to_ghz(self) -> None:
        """MHz -> GHz."""
        result = UnitConverter.normalize_value("2933MHz", "frequency")
        self.assertAlmostEqual(result["value"], 2.933, places=3)
        self.assertEqual(result["unit"], "GHz")

    def test_ghz_direct(self) -> None:
        """GHz -> GHz (identity)."""
        result = UnitConverter.normalize_value("3.5GHz", "frequency")
        self.assertAlmostEqual(result["value"], 3.5, places=3)

    def test_ghz_whitespace(self) -> None:
        """GHz with whitespace."""
        result = UnitConverter.normalize_value("  3200 MHz  ", "frequency")
        self.assertAlmostEqual(result["value"], 3.2, places=3)


class TestPowerConversion(unittest.TestCase):
    """Test power dimension / 测试功率维度."""

    def test_w_direct(self) -> None:
        """W -> W (identity)."""
        result = UnitConverter.normalize_value("750W", "power")
        self.assertEqual(result["value"], 750.0)
        self.assertEqual(result["unit"], "W")

    def test_btu_hr_to_w(self) -> None:
        """BTU/hr -> W."""
        result = UnitConverter.normalize_value("3412BTU/hr", "power")
        self.assertAlmostEqual(result["value"], 1000.0, places=0)

    def test_kw_to_w(self) -> None:
        """kW -> W."""
        result = UnitConverter.normalize_value("1.2kW", "power")
        self.assertEqual(result["value"], 1200.0)


class TestTemperatureConversion(unittest.TestCase):
    """Test temperature dimension / 测试温度维度."""

    def test_celsius_direct(self) -> None:
        """Celsius identity."""
        result = UnitConverter.normalize_value("45°C", "temperature")
        self.assertEqual(result["value"], 45.0)
        self.assertEqual(result["unit"], "°C")

    def test_fahrenheit_to_celsius(self) -> None:
        """Fahrenheit -> Celsius."""
        result = UnitConverter.normalize_value("212°F", "temperature")
        self.assertAlmostEqual(result["value"], 100.0, places=1)

    def test_kelvin_to_celsius(self) -> None:
        """Kelvin -> Celsius."""
        result = UnitConverter.normalize_value("273.15K", "temperature")
        self.assertAlmostEqual(result["value"], 0.0, places=1)

    def test_freezing_f(self) -> None:
        """32°F -> 0°C."""
        result = UnitConverter.normalize_value("32°F", "temperature")
        self.assertAlmostEqual(result["value"], 0.0, places=1)


class TestDataRateConversion(unittest.TestCase):
    """Test data_rate dimension / 测试数据速率维度."""

    def test_mbps_to_gbps(self) -> None:
        """Mbps -> Gbps."""
        result = UnitConverter.normalize_value("10000Mbps", "data_rate")
        self.assertEqual(result["value"], 10.0)
        self.assertEqual(result["unit"], "Gbps")

    def test_gbps_direct(self) -> None:
        """Gbps identity."""
        result = UnitConverter.normalize_value("25Gbps", "data_rate")
        self.assertEqual(result["value"], 25.0)

    def test_mbps_to_gbps_partial(self) -> None:
        """1000 Mbps -> 1 Gbps."""
        result = UnitConverter.normalize_value("1000Mbps", "data_rate")
        self.assertEqual(result["value"], 1.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases / 测试边界情况."""

    def test_empty_string(self) -> None:
        """Empty string returns None value."""
        result = UnitConverter.normalize_value("", "capacity")
        self.assertIsNone(result["value"])
        self.assertEqual(result["confidence"], 0.0)

    def test_unknown_dimension(self) -> None:
        """Unknown dimension returns zero confidence."""
        result = UnitConverter.normalize_value("10GB", "not_a_dimension")
        self.assertIsNone(result["value"])
        self.assertEqual(result["confidence"], 0.0)

    def test_unknown_unit(self) -> None:
        """Unknown unit returns 0.9 confidence with raw number."""
        result = UnitConverter.normalize_value("10XY", "capacity")
        self.assertEqual(result["value"], 10.0)
        self.assertEqual(result["confidence"], 0.9)

    def test_no_number(self) -> None:
        """String with no number fails parse."""
        result = UnitConverter.normalize_value("N/A", "capacity")
        self.assertIsNone(result["value"])
        self.assertEqual(result["confidence"], 0.0)

    def test_number_only(self) -> None:
        """Number without unit detected."""
        result = UnitConverter.normalize_value("100", "power")
        self.assertEqual(result["value"], 100.0)
        self.assertEqual(result["confidence"], 0.9)


if __name__ == "__main__":
    unittest.main()
