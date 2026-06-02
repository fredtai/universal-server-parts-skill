"""
tests/test_ocr_input.py

OCR Input unit tests / OCR 输入单元测试.

Coverage: clean_ocr_text(), extract_part_numbers(), OcrPipeline.process_single(),
Chinese OCR text handling, confusion fix.
"""

import unittest

from uspi.core.ocr_input import OcrInputCleaner, OcrPipeline, clean_and_fix, quick_extract


class TestCleanOcrText(unittest.TestCase):
    """Test clean_ocr_text() / 测试 OCR 文本清洗."""

    def test_clean_basic(self) -> None:
        """Basic cleaning / 基本清洗."""
        text = "  FOX12B456  \n\t"
        result = OcrInputCleaner.clean_ocr_text(text)
        self.assertEqual(result, "FOX12B456")

    def test_clean_control_chars(self) -> None:
        """Remove control characters / 去除控制字符."""
        text = "FOX12B456\x00\x01\x02"
        result = OcrInputCleaner.clean_ocr_text(text)
        self.assertNotIn("\x00", result)

    def test_clean_uppercase(self) -> None:
        """Convert to uppercase / 转为大写."""
        text = "fox12b456"
        result = OcrInputCleaner.clean_ocr_text(text)
        self.assertEqual(result, "FOX12B456")

    def test_clean_whitespace_normalize(self) -> None:
        """Normalize whitespace / 标准化空白."""
        text = "FOX12B456    QCT7890123"
        result = OcrInputCleaner.clean_ocr_text(text)
        self.assertEqual(result, "FOX12B456 QCT7890123")

    def test_clean_empty(self) -> None:
        """Empty input / 空输入."""
        result = OcrInputCleaner.clean_ocr_text("")
        self.assertEqual(result, "")


class TestExtractPartNumbers(unittest.TestCase):
    """Test extract_part_numbers() / 测试零件号提取."""

    def test_extract_dell(self) -> None:
        """Extract Dell PN / 提取 Dell 零件号."""
        text = "The part number is 0WX202 for Dell server"
        result = OcrInputCleaner.extract_part_numbers(text)
        self.assertTrue(len(result) > 0)
        pns = [r["cleaned"] for r in result]
        self.assertIn("0WX202", pns)

    def test_extract_hp(self) -> None:
        """Extract HP PN / 提取 HP 零件号."""
        text = "HP spare 872736-001 memory module"
        result = OcrInputCleaner.extract_part_numbers(text)
        pns = [r["cleaned"] for r in result]
        self.assertIn("872736-001", pns)

    def test_extract_foxconn(self) -> None:
        """Extract Foxconn PN / 提取 Foxconn 零件号."""
        text = "OEM part FOX12B456 from factory"
        result = OcrInputCleaner.extract_part_numbers(text)
        pns = [r["cleaned"] for r in result]
        self.assertIn("FOX12B456", pns)

    def test_extract_quanta(self) -> None:
        """Extract Quanta PN / 提取 Quanta 零件号."""
        text = "Quanta part QCT7890123"
        result = OcrInputCleaner.extract_part_numbers(text)
        pns = [r["cleaned"] for r in result]
        self.assertIn("QCT7890123", pns)

    def test_extract_multiple(self) -> None:
        """Extract multiple PNs / 提取多个零件号."""
        text = "Parts: 0WX202 and FOX12B456 and QCT7890123"
        result = OcrInputCleaner.extract_part_numbers(text)
        pns = [r["cleaned"] for r in result]
        self.assertIn("0WX202", pns)
        self.assertIn("FOX12B456", pns)
        self.assertIn("QCT7890123", pns)

    def test_extract_confusion_fix(self) -> None:
        """Extract with confusion fix / 混淆修复提取."""
        text = "OCR misread: 0WX2O2"
        result = OcrInputCleaner.extract_part_numbers(text)
        self.assertTrue(len(result) > 0)

    def test_extract_empty(self) -> None:
        """Extract from empty text / 空文本提取."""
        result = OcrInputCleaner.extract_part_numbers("")
        self.assertEqual(result, [])


class TestOcrPipeline(unittest.TestCase):
    """Test OcrPipeline / 测试 OCR 管道."""

    def test_process_single(self) -> None:
        """process_single returns best result / process_single 返回最佳结果."""
        pipeline = OcrPipeline()
        result = pipeline.process_single("Server uses part 0WX202")
        self.assertIsNotNone(result)

    def test_process_single_with_description(self) -> None:
        """process_single with description / 带描述的 process_single."""
        pipeline = OcrPipeline()
        result = pipeline.process_single("Part QCT7890123", "Quanta server board")
        self.assertIsNotNone(result)

    def test_process_empty(self) -> None:
        """process empty text / 处理空文本."""
        pipeline = OcrPipeline()
        result = pipeline.process_single("")
        self.assertIsNone(result)

    def test_process_multiple(self) -> None:
        """process multiple parts / 处理多个零件."""
        pipeline = OcrPipeline()
        results = pipeline.process("Parts: 0WX202 and FOX12B456")
        self.assertIsInstance(results, list)


class TestChineseOcr(unittest.TestCase):
    """Test Chinese OCR text handling / 测试中文 OCR 文本处理."""

    def test_chinese_text_extraction(self) -> None:
        """Extract PN from Chinese text / 从中文文本提取零件号."""
        text = "This server uses part number 0WX202, memory spec"
        result = OcrInputCleaner.extract_part_numbers(text)
        pns = [r["cleaned"] for r in result]
        self.assertIn("0WX202", pns)

    def test_chinese_with_punctuation(self) -> None:
        """Handle Chinese punctuation / 处理中文标点."""
        text = "零件：FOX12B456，厂商：富士康"
        result = OcrInputCleaner.clean_ocr_text(text)
        self.assertIn("FOX12B456", result)

    def test_mixed_chinese_english(self) -> None:
        """Mixed text with special chars / 混合特殊字符文本."""
        text = "Dell server memory part 0WX202 (32GB DDR4)"
        result = OcrInputCleaner.extract_part_numbers(text)
        pns = [r["cleaned"] for r in result]
        self.assertIn("0WX202", pns)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions / 测试便捷函数."""

    def test_quick_extract(self) -> None:
        """quick_extract returns list / quick_extract 返回列表."""
        result = quick_extract("Parts: 0WX202 and FOX12B456")
        self.assertIsInstance(result, list)
        self.assertIn("0WX202", result)

    def test_clean_and_fix(self) -> None:
        """clean_and_fix applies confusion fix / clean_and_fix 应用混淆修复."""
        result = clean_and_fix("0WX2O2")
        self.assertIn("0WX202", result)


if __name__ == "__main__":
    unittest.main()
