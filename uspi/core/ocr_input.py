"""
uspi/core/ocr_input.py
OCR 文本预处理模块 / OCR Text Preprocessing Module

从拍照/扫描/OCR 识别结果中提取并清洗零件号。
支持：手机拍照、扫描仪、任何 OCR 工具的输出。
Extracts and cleans part numbers from photos/scans/OCR output.
Supports: mobile photos, scanners, any OCR tool output.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


class OcrInputCleaner:
    """OCR 文本清洗与零件号提取器 / OCR Text Cleaner & Part Number Extractor.

    提供从 OCR 噪声文本中清洗、修复混淆字符、提取候选零件号的功能。
    Provides text cleaning, confusion character fixing, and candidate part
    number extraction from noisy OCR output.

    Attributes:
        OCR_CONFUSION_MAP: 常见 OCR 混淆字符映射 / OCR confusion char map.
        PART_NUMBER_PATTERNS: 各厂商零件号正则模式 / Vendor part number patterns.
        NOISE_PATTERNS: 噪声清除正则模式 / Noise cleanup patterns.
    """

    # OCR 常见混淆字符映射（O→0, l→1 等）
    # Common OCR confusion character mappings
    OCR_CONFUSION_MAP: Dict[str, str] = {
        "O": "0",
        "o": "0",
        "Q": "0",
        "D": "0",
        "I": "1",
        "l": "1",
        "i": "1",
        "|": "1",
        "!": "1",
        "S": "5",
        "s": "5",
        "B": "8",
        "Z": "2",
        "g": "9",
        "q": "9",
        " ": "",  # 空格有时混入 / Spaces sometimes creep in
    }

    # 各厂商零件号的正则模式 / Vendor-specific part number regex patterns
    # 格式: (pattern, manufacturer_code)
    PART_NUMBER_PATTERNS: List[Tuple[str, Optional[str]]] = [
        # Dell (must start with digit / CN-0 prefix)
        (r"\b(?:CN-0|DP/N\s*)?([0-9][A-Z0-9]{4,19})\b", "DELL"),
        (r"\b(A\d{8})\b", "DELL"),  # Dell alternate format
        # HP
        (r"\b(\d{3}[A-Z0-9]{3,4}-[A-Z0-9]{3})\b", "HP"),
        # Lenovo
        (r"\b(\d{2}[A-Z0-9]{6})\b", "LENOVO"),
        # Supermicro
        (r"\b(SNK-P\d{4}[A-Z0-9]+)\b", "SUPERMICRO"),
        (r"\b(MBD-[A-Z0-9-]+)\b", "SUPERMICRO"),
        # ODM - Foxconn (require at least one digit / 要求至少一个数字)
        (r"\b(FOX[A-Z]*\d+[A-Z0-9]{2,12})\b", "FOXCONN"),
        (r"\b(HK[A-Z]*\d+[A-Z0-9]{2,10})\b", "FOXCONN"),
        # ODM - Quanta
        (r"\b(QCT[A-Z]*\d+[A-Z0-9]{2,12})\b", "QUANTA"),
        # ODM - Wistron
        (r"\b(WIS[A-Z]*\d+[A-Z0-9]{2,12})\b", "WISTRON"),
        # ODM - Compal
        (r"\b(CPA[A-Z]*\d+[A-Z0-9]{2,12})\b", "COMPAL"),
        # ODM - Pegatron
        (r"\b(PEG[A-Z]*\d+[A-Z0-9]{2,12})\b", "PEGATRON"),
        # ODM - Inventec
        (r"\b(INV[A-Z]*\d+[A-Z0-9]{2,12})\b", "INVENTEC"),
        # ODM - Flex
        (r"\b(FLE[A-Z]*\d+[A-Z0-9]{2,12})\b", "FLEX"),
        (r"\b(FLX[A-Z]*\d+[A-Z0-9]{2,12})\b", "FLEX"),
        # ODM - Jabil
        (r"\b(JBL[A-Z]*\d+[A-Z0-9]{2,12})\b", "JABIL"),
        # 通用零件号（最后匹配）/ Generic patterns (matched last)
        # 要求同时包含字母和数字 / Must contain both letters and digits
        (r"\b([A-Z]{2,5}\d{4,12}[A-Z]{0,4})\b", None),
        (r"\b(\d+[A-Z]+[0-9A-Z]{2,12})\b", None),
        (r"\b([A-Z]+\d+[0-9A-Z]{2,12})\b", None),
    ]

    # 噪声清除正则 / Noise removal patterns
    NOISE_PATTERNS: List[re.Pattern] = [
        # 控制字符 / Control characters
        re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"),
        # 非单词字符（保留部分分隔符）/ Non-word chars (keep some delimiters)
        re.compile(r"[^\w\s\-/#$]"),
    ]

    @classmethod
    def clean_ocr_text(cls, ocr_text: str) -> str:
        """清洗 OCR 噪声文本 / Clean OCR noise from text.

        步骤：
        1. 去除控制字符 / Remove control characters
        2. 标准化空白（多空格→单空格）/ Normalize whitespace
        3. 转为大写（零件号通常大写）/ Uppercase (P/N usually uppercase)

        Args:
            ocr_text: OCR 原始文本 / Raw OCR text.

        Returns:
            清洗后的文本 / Cleaned text.
        """
        if not ocr_text:
            return ""

        text = ocr_text

        # 1. 去除控制字符 / Remove control characters
        for pat in cls.NOISE_PATTERNS:
            text = pat.sub(" ", text)

        # 2. 标准化空白 / Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # 3. 转为大写 / Convert to uppercase
        text = text.upper()

        return text

    @classmethod
    def extract_part_numbers(
        cls, ocr_text: str, apply_confusion_fix: bool = True
    ) -> List[Dict[str, Any]]:
        """从 OCR 文本中提取候选零件号 / Extract candidate part numbers.

        按优先级匹配各厂商零件号模式，返回带置信度的候选列表。
        Matches vendor-specific patterns by priority, returns candidates with
        confidence scores.

        Args:
            ocr_text: OCR 原始文本 / Raw OCR text.
            apply_confusion_fix: 是否应用混淆字符修复 / Whether to apply confusion fix.

        Returns:
            候选零件号列表，每项含 raw, cleaned, confidence, suggested_mfr /
            List of candidate dicts sorted by confidence descending.
        """
        if not ocr_text or not ocr_text.strip():
            return []

        cleaned = cls.clean_ocr_text(ocr_text)
        candidates: List[Dict[str, Any]] = []
        seen: set[str] = set()

        # 1. 在原始清洗文本上匹配 / Match on cleaned text
        for pattern_str, mfr in cls.PART_NUMBER_PATTERNS:
            for match in re.finditer(pattern_str, cleaned):
                raw = match.group(1) if match.lastindex else match.group(0)
                if not raw or raw in seen:
                    continue
                seen.add(raw)

                confidence = cls._calculate_confidence(
                    raw=raw, cleaned=raw, has_prefix_match=(mfr is not None)
                )
                candidates.append(
                    {
                        "raw": raw,
                        "cleaned": raw,
                        "confidence": confidence,
                        "suggested_mfr": mfr,
                    }
                )

        # 2. 应用混淆修复后再次匹配 / Match after confusion fix
        if apply_confusion_fix:
            fixed = cls._apply_confusion_fix(cleaned)
            if fixed != cleaned:
                for pattern_str, mfr in cls.PART_NUMBER_PATTERNS:
                    for match in re.finditer(pattern_str, fixed):
                        fixed_raw = (
                            match.group(1) if match.lastindex else match.group(0)
                        )
                        if not fixed_raw or fixed_raw in seen:
                            continue
                        seen.add(fixed_raw)

                        confidence = cls._calculate_confidence(
                            raw=fixed_raw,
                            cleaned=fixed_raw,
                            has_prefix_match=(mfr is not None),
                        )
                        # 混淆修复后降低 0.1 置信度 / Reduce confidence for fixed
                        confidence = max(0.1, confidence - 0.1)
                        candidates.append(
                            {
                                "raw": fixed_raw,
                                "cleaned": fixed_raw,
                                "confidence": confidence,
                                "suggested_mfr": mfr,
                            }
                        )

        # 3. 去重并按置信度降序排序 / Deduplicate and sort by confidence
        candidates = cls._deduplicate_candidates(candidates)
        candidates.sort(key=lambda x: x["confidence"], reverse=True)

        return candidates

    @classmethod
    def _apply_confusion_fix(cls, text: str) -> str:
        """应用混淆字符修复 / Apply confusion character fixes.

        将 OCR 常见混淆字符替换为正确字符。
        Replaces common OCR confusion characters with correct ones.

        Args:
            text: 待修复文本 / Text to fix.

        Returns:
            修复后的文本 / Fixed text.
        """
        result = []
        for ch in text:
            result.append(cls.OCR_CONFUSION_MAP.get(ch, ch))
        return "".join(result)

    @classmethod
    def _calculate_confidence(
        cls, raw: str, cleaned: str, has_prefix_match: bool
    ) -> float:
        """计算提取置信度 / Calculate extraction confidence.

        评分规则 / Scoring rules:
        - 完全匹配厂商前缀: 0.9 / Full vendor prefix match: 0.9
        - 混淆修复后匹配: 0.7 / After confusion fix: 0.7
        - 通用匹配（无前缀）: 0.5 / Generic match (no prefix): 0.5
        - 长度惩罚: 过短(<6) -0.1 / Length penalty: too short (<6): -0.1

        Args:
            raw: 原始匹配文本 / Raw matched text.
            cleaned: 清洗后文本 / Cleaned text.
            has_prefix_match: 是否匹配厂商前缀 / Whether vendor prefix matched.

        Returns:
            置信度分数 0.0-1.0 / Confidence score.
        """
        if has_prefix_match:
            score = 0.9
        else:
            score = 0.5

        # 长度调整 / Length adjustment
        if len(cleaned) < 6:
            score -= 0.1
        if len(cleaned) > 20:
            score -= 0.05

        # 全数字惩罚（零件号通常含字母）/ All-digits penalty
        if cleaned.isdigit():
            score -= 0.2

        return max(0.1, min(1.0, score))

    @classmethod
    def _deduplicate_candidates(
        cls, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """去重候选列表，保留最高置信度 / Deduplicate, keep highest confidence.

        相同 cleaned 值只保留置信度最高的一条。
        For identical cleaned values, keep only the highest confidence entry.

        Args:
            candidates: 候选列表 / Candidate list.

        Returns:
            去重后的候选列表 / Deduplicated list.
        """
        best: Dict[str, Dict[str, Any]] = {}
        for c in candidates:
            key = c["cleaned"]
            if key not in best or c["confidence"] > best[key]["confidence"]:
                best[key] = c
        return list(best.values())


class OcrPipeline:
    """OCR 全链路管道 / OCR Full Pipeline.

    OCR 文本 → 清洗 → 提取零件号 → 解析 → 结果
    OCR Text → Clean → Extract PN → Parse → Results

    使用方式 / Usage:
        pipeline = OcrPipeline()
        results = pipeline.process("照片上的文字: FOX12B456 和 QCT7890123")
        # 返回按置信度排序的解析结果列表 / Returns confidence-sorted results
    """

    def __init__(
        self,
        parser: Any = None,
        cleaner: Optional[OcrInputCleaner] = None,
    ) -> None:
        """初始化 OCR 管道 / Initialize OCR pipeline.

        Args:
            parser: PartParser 实例 / PartParser instance.
            cleaner: OcrInputCleaner 实例 / OcrInputCleaner instance.
        """
        if parser is None:
            try:
                from uspi.core.parser import PartParser

                self.parser = PartParser()
            except ImportError:
                self.parser = None
        else:
            self.parser = parser

        self.cleaner = cleaner or OcrInputCleaner()

    def process(
        self, ocr_text: str, description: str = ""
    ) -> List[Dict[str, Any]]:
        """处理 OCR 文本，返回结构化结果 / Process OCR text.

        完整流程：清洗 → 提取零件号 → 解析每个零件号 → 组合结果。
        Full flow: clean → extract P/Ns → parse each → combine results.

        Args:
            ocr_text: OCR 原始文本 / Raw OCR text.
            description: 可选描述文本 / Optional description text.

        Returns:
            结构化结果列表，每项含 extracted_pn, parse_result, ocr_confidence /
            List of dicts with extracted_pn, parse_result, ocr_confidence.
        """
        if not ocr_text or not ocr_text.strip():
            return []

        # 1. 提取候选零件号 / Extract candidate part numbers
        candidates = self.cleaner.extract_part_numbers(ocr_text)
        if not candidates:
            return []

        results: List[Dict[str, Any]] = []

        for cand in candidates:
            cleaned_pn = cand["cleaned"]

            # 2. 解析零件号 / Parse part number
            parse_result = None
            if self.parser is not None:
                try:
                    parse_result = self.parser.parse(cleaned_pn, description)
                except Exception:
                    parse_result = None

            # 3. 计算综合置信度 / Calculate combined confidence
            ocr_conf = cand["confidence"]
            parse_conf = 0.0
            if parse_result is not None:
                parse_conf = getattr(parse_result, "confidence_score", 0.0)

            # 综合置信度 = OCR 置信度 * 0.4 + 解析置信度 * 0.6
            combined_conf = round(ocr_conf * 0.4 + parse_conf * 0.6, 3)

            results.append(
                {
                    "extracted_pn": {
                        "raw": cand["raw"],
                        "cleaned": cleaned_pn,
                        "confidence": ocr_conf,
                        "suggested_mfr": cand.get("suggested_mfr"),
                    },
                    "parse_result": parse_result,
                    "ocr_confidence": combined_conf,
                }
            )

        # 按综合置信度降序排序 / Sort by combined confidence
        results.sort(key=lambda x: x["ocr_confidence"], reverse=True)
        return results

    def process_single(
        self, ocr_text: str, description: str = ""
    ) -> Optional[Dict[str, Any]]:
        """处理并返回最高置信度的单个结果 / Return best single result.

        适用于单零件场景，返回置信度最高的结果。
        Suitable for single-part scenarios, returns the highest confidence result.

        Args:
            ocr_text: OCR 原始文本 / Raw OCR text.
            description: 可选描述文本 / Optional description text.

        Returns:
            最佳结果字典或 None / Best result dict or None.
        """
        results = self.process(ocr_text, description)
        if not results:
            return None
        return results[0]


# ---------------------------------------------------------------------------
# 便捷函数 / Convenience Functions
# ---------------------------------------------------------------------------


def quick_extract(ocr_text: str) -> List[str]:
    """快速提取零件号（仅返回字符串列表）/ Quick extract part numbers.

    最简接口：输入 OCR 文本，返回零件号字符串列表。
    Minimal interface: input OCR text, output list of part number strings.

    Args:
        ocr_text: OCR 原始文本 / Raw OCR text.

    Returns:
        零件号字符串列表 / List of part number strings.
    """
    cleaner = OcrInputCleaner()
    candidates = cleaner.extract_part_numbers(ocr_text)
    return [c["cleaned"] for c in candidates]


def clean_and_fix(ocr_text: str) -> str:
    """清洗并修复 OCR 文本 / Clean and fix OCR text.

    对 OCR 文本进行清洗并应用混淆字符修复。
    Cleans OCR text and applies confusion character fixes.

    Args:
        ocr_text: OCR 原始文本 / Raw OCR text.

    Returns:
        清洗并修复后的文本 / Cleaned and fixed text.
    """
    cleaned = OcrInputCleaner.clean_ocr_text(ocr_text)
    fixed = OcrInputCleaner._apply_confusion_fix(cleaned)
    return fixed
