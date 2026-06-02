"""
USPI 零件号识别引擎 (Part Number Parser Engine)

实现对 OEM（Dell/HP/Lenovo/Supermicro）和 ODM（Foxconn/Quanta/Wistron/Compal/
Pegatron/Inventec/Flex/Jabil）零件号的识别与分类推断。

Implementation of part number recognition and category inference for OEMs
(Dell/HP/Lenovo/Supermicro) and ODMs (Foxconn/Quanta/Wistron/Compal/Pegatron/
Inventec/Flex/Jabil).
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ParseResult:
    """
    零件号解析结果 / Part number parse result.

    Attributes:
        part_number: 原始零件号 / Original part number.
        manufacturer: 识别到的厂商代码 (e.g., "DELL", "FOXCONN") / Detected manufacturer code.
        manufacturer_zh: 厂商中文名 / Manufacturer Chinese name.
        is_odm: 是否为 ODM 厂商 / Whether the manufacturer is an ODM.
        oem_brand: 对应 OEM 品牌 (若 ODM 代工) / Associated OEM brand if ODM.
        category: 分类键值 (e.g., "CPU", "MEMORY") / Category key.
        category_zh: 分类中文名 / Category Chinese name.
        confidence_score: 置信度 0.0-1.0 / Confidence score.
        suggested_manufacturers: 建议厂商列表 / Suggested manufacturers.
        suggested_categories: 建议分类及置信度列表 / Suggested categories with confidence.
    """

    part_number: str
    manufacturer: Optional[str] = None
    manufacturer_zh: Optional[str] = None
    is_odm: bool = False
    oem_brand: Optional[str] = None
    category: Optional[str] = None
    category_zh: Optional[str] = None
    confidence_score: float = 0.0
    suggested_manufacturers: List[str] = field(default_factory=list)
    suggested_categories: List[Tuple[str, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Dataclass 初始化后处理 / Post-initialization processing."""
        pass


class PartParser:
    """
    零件号识别与分类推断器 / Part number parser and category inferrer.

    维护完整的前缀正则字典和分类关键词字典，支持 OEM 和 ODM 零件号识别。
    Maintains comprehensive prefix regex dictionaries and category keyword
    dictionaries for OEM and ODM part number recognition.
    """

    # ------------------------------------------------------------------
    # OEM 前缀正则 / OEM prefix regex patterns
    # ------------------------------------------------------------------
    OEM_PATTERNS: Dict[str, List[str]] = {
        "DELL": [
            r"^[0-9][A-Z0-9]{4,19}$",
            r"^CN-0[A-Z0-9]+",
            r"^DP/N\s*[0-9A-Z]+",
        ],
        "HP": [
            r"^[0-9]{3}[A-Z0-9]{3,4}-[0-9A-Z]{3}$",
            r"^Spare\s*#\s*[0-9A-Z-]+",
        ],
        "HPE": [
            r"^[0-9]{3}[A-Z0-9]{3,4}-[0-9A-Z]{3}$",
            r"^Spare\s*#\s*[0-9A-Z-]+",
        ],
        "LENOVO": [
            r"^[0-9]{2}[A-Z0-9]{5,6}$",
        ],
        "SUPERMICRO": [
            r"^SNK-P[0-9]{4}[A-Z0-9]+",
            r"^MBD-[A-Z0-9-]+",
        ],
    }

    # ------------------------------------------------------------------
    # ODM 前缀正则 / ODM prefix regex patterns
    # ------------------------------------------------------------------
    ODM_PATTERNS: Dict[str, List[str]] = {
        "FOXCONN": [
            r"^FOX[A-Z0-9]{5,15}$",
            r"^HK[A-Z0-9]{5,12}$",
        ],
        "QUANTA": [
            r"^QCT[A-Z0-9]{5,15}$",
            r"^Q[A-Z0-9]{6,12}$",
        ],
        "WISTRON": [
            r"^WIS[A-Z0-9]{5,15}$",
            r"^W[A-Z0-9]{6,12}$",
            r"^60[0-9A-Z]{6}$",
        ],
        "COMPAL": [
            r"^CPA[A-Z0-9]{5,15}$",
            r"^C[A-Z0-9]{6,12}$",
        ],
        "PEGATRON": [
            r"^PEG[A-Z0-9]{5,15}$",
            r"^P[A-Z0-9]{6,12}$",
        ],
        "INVENTEC": [
            r"^INV[A-Z0-9]{5,15}$",
            r"^I[A-Z0-9]{6,12}$",
        ],
        "FLEX": [
            r"^FLE[A-Z0-9]{5,15}$",
            r"^FLX[A-Z0-9]{5,15}$",
        ],
        "JABIL": [
            r"^JBL[A-Z0-9]{5,15}$",
            r"^J[A-Z0-9]{6,12}$",
        ],
    }

    # ------------------------------------------------------------------
    # ODM -> 可能代工的 OEM 品牌 / ODM -> possible OEM brands map
    # ------------------------------------------------------------------
    ODM_OEM_MAP: Dict[str, List[str]] = {
        "FOXCONN": ["DELL", "HP", "APPLE"],
        "QUANTA": ["DELL", "HP", "AWS"],
        "WISTRON": ["DELL", "HP", "LENOVO"],
        "COMPAL": ["DELL", "HP", "LENOVO"],
        "PEGATRON": ["ASUS", "APPLE", "MSI"],
        "INVENTEC": ["DELL", "HP", "LENOVO"],
        "FLEX": ["CISCO", "JUNIPER", "NOKIA"],
        "JABIL": ["CISCO", "HP", "JUNIPER"],
    }

    # ------------------------------------------------------------------
    # 厂商中文名 / Manufacturer Chinese names
    # ------------------------------------------------------------------
    MANUFACTURER_ZH: Dict[str, str] = {
        "DELL": "戴尔",
        "HP": "惠普",
        "HPE": "慧与",
        "LENOVO": "联想",
        "SUPERMICRO": "超微",
        "IBM": "IBM",
        "CISCO": "思科",
        "FOXCONN": "鸿海/富士康",
        "QUANTA": "广达",
        "WISTRON": "纬创",
        "COMPAL": "仁宝",
        "PEGATRON": "和硕",
        "INVENTEC": "英业达",
        "FLEX": "伟创力",
        "JABIL": "捷普",
        "MITAC": "神达",
    }

    # ------------------------------------------------------------------
    # 分类推断关键词 / Category inference keywords
    # ------------------------------------------------------------------
    CATEGORY_KEYWORDS: Dict[str, List[str]] = {
        "CPU": ["Xeon", "EPYC", "Core", "Processor", "处理器", "CPU"],
        "MEMORY": ["DDR", "RDIMM", "LRDIMM", "UDIMM", "Memory", "内存", "DIMM"],
        "STORAGE_SSD": ["SSD", "固态硬盘", "SATA SSD", "SAS SSD"],
        "STORAGE_HDD": ["HDD", "SAS", "SATA", "硬盘", "Hard Drive", "机械硬盘"],
        "STORAGE_NVME": ["NVMe", "NVME", "PCIe SSD"],
        "PSU": ["Power Supply", "Watt", "PSU", "电源", "W "],
        "FAN": ["Fan", "Blower", "Cooling", "风扇"],
        "HEATSINK": ["Heatsink", "Heat Sink", "散热片"],
        "RAID_CONTROLLER": ["RAID", "HBA", "SAS Controller", "控制器", "RAID卡"],
        "NIC": ["NIC", "Ethernet", "网卡", "网络", "GbE", "10GbE", "25GbE"],
        "GPU": ["GPU", "NVIDIA", "Accelerator", "显卡", "加速卡", "A100", "H100"],
        "MOTHERBOARD": ["Motherboard", "System Board", "主板"],
        "BACKPLANE": ["Backplane", "背板"],
        "CABLE": ["Cable", "线缆", "SAS Cable", "Power Cable"],
        "RAIL_KIT": ["Rail", "导轨", "Slide Rail"],
        "BEZEL": ["Bezel", "Faceplate", "面板"],
        "BATTERY": ["Battery", "电池", "RAID Battery", "BBU"],
    }

    # ------------------------------------------------------------------
    # 分类中文名 / Category Chinese names
    # ------------------------------------------------------------------
    CATEGORIES: Dict[str, str] = {
        "CPU": "处理器",
        "MEMORY": "内存",
        "STORAGE_HDD": "机械硬盘",
        "STORAGE_SSD": "固态硬盘",
        "STORAGE_NVME": "NVMe 硬盘",
        "RAID_CONTROLLER": "RAID 控制器",
        "NIC": "网卡",
        "GPU": "显卡/加速卡",
        "PSU": "电源",
        "FAN": "风扇",
        "HEATSINK": "散热片",
        "MOTHERBOARD": "主板",
        "BACKPLANE": "背板",
        "CABLE": "线缆",
        "RAIL_KIT": "导轨",
        "BEZEL": "面板",
        "BATTERY": "电池",
        "OTHERS": "其他",
    }

    # ------------------------------------------------------------------
    # 编译后的正则缓存 / Compiled regex cache
    # ------------------------------------------------------------------
    _compiled_oem: Dict[str, List[re.Pattern]] = {}
    _compiled_odm: Dict[str, List[re.Pattern]] = {}
    _compiled_categories: Dict[str, List[re.Pattern]] = {}

    def __init__(self) -> None:
        """
        初始化解析器，编译所有正则表达式。
        Initialize the parser and compile all regex patterns.
        """
        self._compiled_oem = {
            brand: [re.compile(p, re.IGNORECASE) for p in patterns]
            for brand, patterns in self.OEM_PATTERNS.items()
        }
        self._compiled_odm = {
            brand: [re.compile(p, re.IGNORECASE) for p in patterns]
            for brand, patterns in self.ODM_PATTERNS.items()
        }
        self._compiled_categories = {
            cat: [re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE) for kw in kws]
            for cat, kws in self.CATEGORY_KEYWORDS.items()
        }

    def parse(
        self, part_number: str, description: Optional[str] = None
    ) -> ParseResult:
        """
        解析零件号，识别厂商和分类。
        Parse a part number to identify manufacturer and category.

        识别逻辑 / Recognition logic:
        1. 先遍历 OEM_PATTERNS 尝试正则匹配 / Try OEM pattern matching first.
        2. 再遍历 ODM_PATTERNS 尝试正则匹配 / Then try ODM pattern matching.
        3. 匹配成功 confidence_score = 0.8 / Match success => score = 0.8.
        4. 若同时匹配 description 分类关键词，score += 0.1 / Category match => +0.1.
        5. 未匹配前缀但匹配分类关键词，score = 0.3 / Only category => score = 0.3.
        6. 完全未匹配，score = 0.0，填充建议列表 / No match => score = 0.0 with suggestions.

        Args:
            part_number: 零件号字符串 / Part number string.
            description: 可选描述文本 / Optional description text.

        Returns:
            ParseResult: 解析结果对象 / Parse result object.
        """
        result = ParseResult(part_number=part_number)

        # 空输入处理 / Handle empty input
        if not part_number or not part_number.strip():
            result.confidence_score = 0.0
            result.suggested_manufacturers = []
            result.suggested_categories = []
            return result

        cleaned_pn = part_number.strip().upper()

        # --------------------------------------------------------------
        # Step 1&2: 同时匹配 OEM 和 ODM，选特异性最高的 / Match both, pick best
        # --------------------------------------------------------------
        matched_oem, oem_spec = self._match_manufacturer_with_score(
            cleaned_pn, self._compiled_oem
        )
        matched_odm, odm_spec = self._match_manufacturer_with_score(
            cleaned_pn, self._compiled_odm
        )

        # 选择特异性更高的匹配 / Choose match with higher specificity
        if matched_oem and matched_odm:
            if oem_spec >= odm_spec:
                self._apply_oem_result(result, matched_oem)
            else:
                self._apply_odm_result(result, matched_odm)
        elif matched_oem:
            self._apply_oem_result(result, matched_oem)
        elif matched_odm:
            self._apply_odm_result(result, matched_odm)

        # --------------------------------------------------------------
        # Step 3: 分类推断 / Category inference from description
        # --------------------------------------------------------------
        if description and description.strip():
            categories = self.infer_category(description)
            result.suggested_categories = categories
            if categories:
                best_cat, best_score = categories[0]
                result.category = best_cat
                result.category_zh = self.CATEGORIES.get(best_cat)
                # 调整置信度 / Adjust confidence score
                if result.confidence_score >= 0.8:
                    # 已匹配前缀 + 分类 / Prefix + category
                    result.confidence_score = min(0.9, 0.8 + best_score * 0.1)
                elif result.confidence_score == 0.0:
                    # 仅匹配分类 / Only category matched
                    result.confidence_score = 0.3
        else:
            # 无描述时，基于零件号特征做简单分类推断 / Simple inference from PN
            categories = self.infer_category(cleaned_pn)
            result.suggested_categories = categories
            if categories and result.confidence_score >= 0.8:
                best_cat, best_score = categories[0]
                if best_score > 0.0:
                    result.category = best_cat
                    result.category_zh = self.CATEGORIES.get(best_cat)
                    result.confidence_score = min(0.9, 0.8 + best_score * 0.1)

        # --------------------------------------------------------------
        # Step 4: 完全未匹配处理 / No match handling
        # --------------------------------------------------------------
        if result.confidence_score == 0.0:
            result.suggested_manufacturers = self.suggest_manufacturers(
                cleaned_pn
            )
            if not result.suggested_categories:
                result.suggested_categories = self.infer_category(cleaned_pn)

        return result

    def _apply_oem_result(self, result: ParseResult, brand: str) -> None:
        """
        将 OEM 匹配结果填充到 ParseResult。
        Fill OEM match result into ParseResult.

        Args:
            result: ParseResult 对象 / ParseResult object.
            brand: 匹配到的 OEM 品牌代码 / Matched OEM brand code.
        """
        result.manufacturer = brand
        result.manufacturer_zh = self.MANUFACTURER_ZH.get(brand)
        result.is_odm = False
        result.confidence_score = 0.8
        result.oem_brand = brand

    def _apply_odm_result(self, result: ParseResult, brand: str) -> None:
        """
        将 ODM 匹配结果填充到 ParseResult。
        Fill ODM match result into ParseResult.

        Args:
            result: ParseResult 对象 / ParseResult object.
            brand: 匹配到的 ODM 品牌代码 / Matched ODM brand code.
        """
        result.manufacturer = brand
        result.manufacturer_zh = self.MANUFACTURER_ZH.get(brand)
        result.is_odm = True
        result.confidence_score = 0.8
        oem_brands = self.ODM_OEM_MAP.get(brand, [])
        result.oem_brand = oem_brands[0] if oem_brands else None

    @staticmethod
    def _pattern_specificity(pattern_str: str) -> int:
        """
        计算正则模式的特异性分数（越高越具体）。
        Calculate regex pattern specificity score (higher = more specific).

        评分规则 / Scoring rules:
        - 字面字符数（非正则元字符）+3 分 each literal char
        - 字符类数量 [0-9], [A-Z] 等 +1 分 each character class
        - 锚点 ^, $ +1 分 each anchor
        - 宽泛范围如 {5,20} -2 分 wide quantifier penalty
        - 纯宽泛字母数字模式（无字面字符）额外 -3 分
          Pure alphanum catch-all (no literals) extra -3 penalty

        Args:
            pattern_str: 正则模式字符串 / Regex pattern string.

        Returns:
            特异性分数 / Specificity score.
        """
        score = 0
        i = 0
        in_char_class = False
        has_literal_outside_class = False

        while i < len(pattern_str):
            ch = pattern_str[i]

            if ch == "[":
                in_char_class = True
                score += 1  # 字符类加分
                i += 1
                continue
            elif ch == "]":
                in_char_class = False
                i += 1
                continue
            elif ch in ("^", "$"):
                score += 1
                i += 1
                continue
            elif ch == "\\":
                # 转义序列按字面字符处理 / Escaped char as literal
                score += 3
                has_literal_outside_class = True
                i += 2
                continue
            elif ch == "{" and not in_char_class:
                # 检查是否为大范围限定符 / Check for wide quantifier
                j = i + 1
                while j < len(pattern_str) and pattern_str[j] != "}":
                    j += 1
                inner = pattern_str[i + 1 : j]
                if "," in inner:
                    parts = inner.split(",")
                    if len(parts) == 2:
                        try:
                            hi = int(parts[1]) if parts[1] else 999
                            lo = int(parts[0])
                            if hi - lo > 10:
                                score -= 2  # 宽泛范围惩罚
                        except ValueError:
                            pass
                i = j + 1
                continue
            elif ch in ("*", "+", "?", "|", ".", "(", ")"):
                # 正则元字符不计分 / Regex metachar no score
                i += 1
                continue
            elif not in_char_class:
                # 字面字符 / Literal character
                score += 3
                has_literal_outside_class = True
                i += 1
                continue
            else:
                i += 1
                continue

        # 纯宽泛字母数字模式惩罚 / Penalty for pure catch-all patterns
        if not has_literal_outside_class:
            score -= 3

        return score

    def _match_manufacturer_with_score(
        self,
        part_number: str,
        compiled_patterns: Dict[str, List[re.Pattern]],
    ) -> Tuple[Optional[str], int]:
        """
        内部方法：遍历编译后的正则匹配厂商，返回最佳匹配及特异性分数。
        Internal: iterate compiled patterns, return best match with specificity.

        Args:
            part_number: 清理后的零件号 / Cleaned part number.
            compiled_patterns: 编译后的厂商正则字典 / Compiled pattern dict.

        Returns:
            (厂商代码, 特异性分数) 或 (None, 0) / (Brand code, specificity) or (None, 0).
        """
        matches: List[Tuple[str, int]] = []

        for brand, patterns in compiled_patterns.items():
            for pattern in patterns:
                if pattern.match(part_number):
                    spec = self._pattern_specificity(pattern.pattern)
                    matches.append((brand, spec))

        if not matches:
            return None, 0

        # 按特异性降序排序，取最具体的 / Sort by specificity desc, pick best
        matches.sort(key=lambda x: x[1], reverse=True)
        best_brand, best_spec = matches[0]

        # 特异性低于阈值视为无效匹配 / Treat low-specificity matches as invalid
        if best_spec < -1:
            return None, 0

        return best_brand, best_spec

    def _match_manufacturer(
        self,
        part_number: str,
        compiled_patterns: Dict[str, List[re.Pattern]],
    ) -> Optional[str]:
        """
        内部方法：遍历编译后的正则匹配厂商，优先返回最具体的匹配。
        Internal: iterate compiled patterns, prefer the most specific match.

        特异性通过 _pattern_specificity 计算，确保具体前缀模式优先于
        宽泛通用模式。
        Specificity via _pattern_specificity ensures specific prefix patterns
        are preferred over broad catch-all patterns.

        Args:
            part_number: 清理后的零件号 / Cleaned part number.
            compiled_patterns: 编译后的厂商正则字典 / Compiled pattern dict.

        Returns:
            匹配到的厂商代码或 None / Matched manufacturer code or None.
        """
        brand, _ = self._match_manufacturer_with_score(
            part_number, compiled_patterns
        )
        return brand

    def infer_category(self, text: str) -> List[Tuple[str, float]]:
        """
        根据文本推断分类，返回按置信度排序的分类列表。
        Infer category from text, return sorted list by confidence.

        优化版本：使用预编译正则，O(N) 而非 O(N*M)。
        Optimized: uses pre-compiled regex, O(N) instead of O(N*M).

        置信度计算：匹配关键词数 / 该分类总关键词数。
        Confidence = matched_keywords / total_keywords_for_category.

        Args:
            text: 描述文本 / Description text.

        Returns:
            [(category_key, confidence), ...] 按置信度降序 / Sorted by confidence desc.
        """
        if not text:
            return []

        text_upper = text.upper()
        scores: Dict[str, float] = {}
        category_keywords = self.CATEGORY_KEYWORDS

        for cat, patterns in self._compiled_categories.items():
            count = sum(1 for p in patterns if p.search(text_upper))
            if count > 0:
                total_kw = len(category_keywords[cat])
                scores[cat] = min(count / total_kw, 1.0)

        if not scores:
            return []

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def suggest_manufacturers(self, part_number: str) -> List[str]:
        """
        当无法识别时，基于零件号前缀特征推荐可能的厂商。
        When unrecognized, suggest possible manufacturers based on PN prefix.

        Args:
            part_number: 零件号字符串 / Part number string.

        Returns:
            建议厂商代码列表 / List of suggested manufacturer codes.
        """
        if not part_number:
            return list(self.OEM_PATTERNS.keys()) + list(
                self.ODM_PATTERNS.keys()
            )

        pn = part_number.strip().upper()
        suggestions: List[str] = []

        # 基于前缀字母进行启发式推荐 / Heuristic based on prefix letters
        prefix_hints = {
            "FOX": ["FOXCONN"],
            "HK": ["FOXCONN"],
            "QCT": ["QUANTA"],
            "Q": ["QUANTA"],
            "WIS": ["WISTRON"],
            "W": ["WISTRON"],
            "CPA": ["COMPAL"],
            "C": ["COMPAL"],
            "PEG": ["PEGATRON"],
            "P": ["PEGATRON"],
            "INV": ["INVENTEC"],
            "I": ["INVENTEC"],
            "FLE": ["FLEX"],
            "FLX": ["FLEX"],
            "JBL": ["JABIL"],
            "J": ["JABIL"],
            "SNK": ["SUPERMICRO"],
            "MBD": ["SUPERMICRO"],
            "CN-0": ["DELL"],
            "DP/N": ["DELL"],
            "SPARE": ["HP", "HPE"],
        }

        for hint_prefix, manufacturers in prefix_hints.items():
            if pn.startswith(hint_prefix):
                for mfr in manufacturers:
                    if mfr not in suggestions:
                        suggestions.append(mfr)

        # 如果没有任何前缀匹配，返回所有厂商 / Return all if no prefix matched
        if not suggestions:
            suggestions = list(self.OEM_PATTERNS.keys()) + list(
                self.ODM_PATTERNS.keys()
            )

        return suggestions
