"""
适配器公共工具模块 / Adapter Common Utilities

提取各适配器重复逻辑，减少代码冗余。
Extract shared logic from adapters to reduce duplication.
"""
from __future__ import annotations

import random
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

from uspi.core.adapters.base import CATEGORIES, PriceSource, ServerPart


# ── 时间戳工具 ──────────────────────────────────────────
def utc_now() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串 / Return current UTC time as ISO 8601."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── HTML 解析公共类 ──────────────────────────────────────────
class SpecTableParser(HTMLParser):
    """轻量级规格表 HTML 提取器 / Lightweight spec table HTML extractor."""

    def __init__(self) -> None:
        super().__init__()
        self._in_table = False
        self._in_td = False
        self._current_tag: Optional[str] = None
        self._cells: List[str] = []
        self._current_cell: List[str] = []
        self.specs: Dict[str, str] = {}
        self._last_label: Optional[str] = None
        self.title: str = ""
        self._capture_title = False
        self._in_script = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        tag = tag.lower()
        attrs_dict = dict(attrs)
        css_class = attrs_dict.get("class", "").lower()

        if tag in ("script", "style"):
            self._in_script = True
            return
        if tag == "title":
            self._capture_title = True
        if tag == "table" and any(cls in css_class for cls in ["spec", "detail", "product"]):
            self._in_table = True
        if tag == "td" and self._in_table:
            self._in_td = True
            self._current_cell = []
        if tag in ("div",) and any(cls in css_class for cls in ["spec", "detail", "product"]):
            self._in_table = True
        self._current_tag = tag

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in ("script", "style"):
            self._in_script = False
            return
        if tag == "title":
            self._capture_title = False
        if tag == "td" and self._in_table:
            self._in_td = False
            text = "".join(self._current_cell).strip()
            if text:
                self._cells.append(text)
                if len(self._cells) % 2 == 0 and len(self._cells) >= 2:
                    self.specs[self._cells[-2]] = self._cells[-1]
        if tag in ("table", "div") and self._in_table:
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._in_script:
            return
        cleaned = data.strip()
        if not cleaned:
            return
        if self._capture_title:
            self.title = cleaned
            return
        if self._in_td and self._in_table:
            self._current_cell.append(cleaned)


# ── 公共正则模式库 ──────────────────────────────────────────
PRICE_PATTERN = re.compile(r"[$\u20ac\u00a3\u00a5]\s*([0-9,]+\.?\d*)")
DESCRIPTION_PATTERN = re.compile(
    r"(?:Description|Product\s*Description|Title)\s*[:#]?\s*([^<\n]+)", re.I
)
CATEGORY_PATTERN = re.compile(
    r"(?:Category|Product\s*Type|Item\s*Type)\s*[:#]?\s*([^<\n]+)", re.I
)
CAPACITY_PATTERN = re.compile(r"(\d+\.?\d*)\s*(GB|TB|MB|GiB|TiB)", re.I)
WATTAGE_PATTERN = re.compile(r"(\d+)\s*W(?:att)?", re.I)


# ── HTML 文本清理 ──────────────────────────────────────────
def clean_html_text(html: str) -> str:
    """去除 HTML 标签，返回纯文本 / Strip HTML tags, return plain text."""
    text = re.sub(r"<[^>]+>", " ", html)
    return " ".join(text.split())


def extract_price_from_html(html: str) -> Optional[float]:
    """从 HTML 中提取价格 / Extract price from HTML."""
    match = PRICE_PATTERN.search(html)
    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except (ValueError, AttributeError):
            pass
    return None


def extract_specs_from_html(html: str) -> Dict[str, str]:
    """从 HTML 中提取规格键值对 / Extract specs from HTML."""
    parser = SpecTableParser()
    try:
        parser.feed(html[:50000])  # 限制 50KB 防内存溢出 / Limit 50KB to prevent overflow
    except Exception:
        pass
    return parser.specs


# ── 容量归一化 ──────────────────────────────────────────
def normalize_capacity(value: str, unit: str) -> float:
    """将容量归一化为 GB / Normalize capacity to GB.

    Args:
        value: 容量数值 / Capacity value.
        unit: 容量单位 / Capacity unit (GB, TB, MB).

    Returns:
        以 GB 为单位的容量 / Capacity in GB.
    """
    val = float(value)
    unit_upper = unit.upper()
    if unit_upper in ("TB", "TIB"):
        return val * 1024
    elif unit_upper in ("MB", "MIB"):
        return val / 1024
    return val


# ── 分类推断辅助 ──────────────────────────────────────────
def infer_category_from_text(text: str) -> Tuple[str, str, float]:
    """从文本推断分类 / Infer category from text.

    Returns:
        (category_key, category_zh, confidence_boost)
    """
    text_upper = text.upper()
    scores: Dict[str, int] = {}
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.upper() in text_upper)
        if score > 0:
            scores[cat] = score

    if not scores:
        return "OTHERS", "\u5176\u4ed6", 0.0

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    return best, CATEGORIES.get(best, "\u5176\u4ed6"), min(scores[best] * 0.1, 0.2)


_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "CPU": ["XEON", "EPYC", "PROCESSOR", "\u5904\u7406\u5668"],
    "MEMORY": ["DDR", "RDIMM", "LRDIMM", "UDIMM", "DIMM", "MEMORY", "\u5185\u5b58"],
    "STORAGE_SSD": ["SSD", "\u56fa\u6001"],
    "STORAGE_HDD": ["HDD", "HARD DRIVE", "\u786c\u76d8", "SATA", "SAS"],
    "STORAGE_NVME": ["NVME"],
    "PSU": ["POWER SUPPLY", "PSU", "\u7535\u6e90", "WATT"],
    "FAN": ["FAN", "BLOWER", "\u98ce\u6247"],
    "RAID_CONTROLLER": ["RAID", "HBA", "CONTROLLER", "\u63a7\u5236\u5668"],
    "NIC": ["NIC", "ETHERNET", "\u7f51\u5361", "GBE", "10GBE"],
    "GPU": ["GPU", "NVIDIA", "A100", "H100", "\u52a0\u901f\u5668"],
    "MOTHERBOARD": ["MOTHERBOARD", "BOARD", "\u4e3b\u677f"],
    "HEATSINK": ["HEATSINK", "SNK-P", "\u6563\u70ed\u7247"],
    "BACKPLANE": ["BACKPLANE", "\u80cc\u677f"],
    "CABLE": ["CABLE", "\u7ebf\u7f06"],
    "RAIL_KIT": ["RAIL", "\u5bfc\u8f68"],
    "BEZEL": ["BEZEL", "\u9762\u677f"],
    "BATTERY": ["BATTERY", "\u7535\u6c60", "BBU"],
}


# ── 规格标准化提取 ──────────────────────────────────────────
def extract_normalized_specs(description: str, raw_specs: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """从描述和原始规格中提取标准化规格 / Extract normalized specifications.

    Args:
        description: 零件描述 / Part description.
        raw_specs: 原始规格字典 / Raw specifications dict.

    Returns:
        标准化规格字典 / Normalized specifications dict.
    """
    specs: Dict[str, Any] = {}
    if not description:
        return specs

    desc_upper = description.upper()

    # 内存相关 / Memory related
    if "DDR" in desc_upper:
        ddr_match = re.search(r"DDR(\d+)", desc_upper)
        if ddr_match:
            specs["memory_type"] = f"DDR{ddr_match.group(1)}"
        speed_match = re.search(r"(\d+)\s*MHz", desc_upper)
        if speed_match:
            specs["speed_mhz"] = int(speed_match.group(1))
        for dimm_type in ("RDIMM", "LRDIMM", "UDIMM", "SODIMM"):
            if dimm_type in desc_upper:
                specs["dimm_type"] = dimm_type
                break

    # 容量 / Capacity
    cap_match = re.search(r"(\d+\.?\d*)\s*(GB|TB|MB)", desc_upper)
    if cap_match:
        val = float(cap_match.group(1))
        unit = cap_match.group(2)
        if unit == "GB":
            specs["capacity_gb"] = val
        elif unit == "TB":
            specs["capacity_gb"] = val * 1024
        elif unit == "MB":
            specs["capacity_gb"] = val / 1024

    # 电源相关 / PSU related
    watt_match = re.search(r"(\d+)\s*W", desc_upper)
    if watt_match:
        specs["wattage"] = int(watt_match.group(1))

    # 网卡相关 / NIC related
    if "GBE" in desc_upper or "ETHERNET" in desc_upper:
        nic_match = re.search(r"(\d+)\s*GbE", desc_upper)
        if nic_match:
            specs["speed_gbps"] = int(nic_match.group(1))
        if "SFP" in desc_upper:
            specs["interface"] = "SFP+"

    # 硬盘类型 / Storage type
    if "SAS" in desc_upper and "HDD" in desc_upper:
        specs["interface"] = "SAS"
        specs["form_factor"] = "2.5" if "2.5" in desc_upper else "3.5"
    elif "SATA" in desc_upper and "SSD" in desc_upper:
        specs["interface"] = "SATA"
        specs["form_factor"] = "2.5"
    elif "NVME" in desc_upper:
        specs["interface"] = "NVMe"
        specs["form_factor"] = "2.5"

    # RAID 控制器 / RAID controller
    if "RAID" in desc_upper:
        raid_match = re.search(r"(RAID-\d+)", desc_upper)
        if raid_match:
            specs["raid_level"] = raid_match.group(1)

    # 显卡 / GPU
    if "NVIDIA" in desc_upper or "GPU" in desc_upper:
        for gpu_model in ("TESLA", "A100", "H100", "A40", "V100"):
            if gpu_model in desc_upper:
                specs["gpu_model"] = gpu_model
                break

    # 主板相关 / Motherboard related
    if "MOTHERBOARD" in desc_upper or "SERVERBOARD" in desc_upper:
        socket_match = re.search(r"LGA\s*(\d+)", desc_upper)
        if socket_match:
            specs["socket"] = f"LGA-{socket_match.group(1)}"

    # 散热器 / Heatsink
    if "HEATSINK" in desc_upper or "SNK-P" in desc_upper:
        socket_match = re.search(r"LGA\s*(\d+)", desc_upper)
        if socket_match:
            specs["socket"] = f"LGA-{socket_match.group(1)}"
        form_match = re.search(r"(\d+)U", desc_upper)
        if form_match:
            specs["form_factor_u"] = int(form_match.group(1))

    return specs


# ── 从规格字典推断分类 ──────────────────────────────────────────
def infer_category_from_specs(specs: Dict[str, str]) -> str:
    """从规格字典推断零件分类 / Infer part category from specifications.

    Args:
        specs: 原始规格字典 / Raw specification dictionary.

    Returns:
        分类键值 / Category key.
    """
    text = " ".join(f"{k} {v}" for k, v in specs.items()).upper()
    if any(kw in text for kw in ["DDR", "RDIMM", "LRDIMM", "MEMORY"]):
        return "MEMORY"
    if any(kw in text for kw in ["SSD", "SOLID STATE"]):
        return "STORAGE_SSD"
    if any(kw in text for kw in ["HDD", "HARD DRIVE", "SAS"]):
        return "STORAGE_HDD"
    if "NVME" in text:
        return "STORAGE_NVME"
    if any(kw in text for kw in ["POWER SUPPLY", "PSU", "WATT"]):
        return "PSU"
    if any(kw in text for kw in ["NIC", "ETHERNET", "NETWORK"]):
        return "NIC"
    if any(kw in text for kw in ["XEON", "EPYC", "PROCESSOR", "CPU"]):
        return "CPU"
    return "OTHERS"


# ── 零件号厂商匹配检查 ───────────────────────────────────
_PN_OEM_PATTERNS: Dict[str, Any] = {
    # Dell: 5-20位字母数字 或 CN-0 前缀 / Dell: 5-20 alphanumeric or CN-0 prefix
    "DELL": re.compile(r"^[0-9A-Z]{5,20}$|^CN-0[0-9A-Z]+$"),
    # HP/HPE: 6位字母数字 + - + 2-3位字母数字 / HP/HPE: 6 alphanum + dash + 2-3 alphanum
    "HP": re.compile(r"^[0-9A-Z]{6}-[0-9A-Z]{2,3}$"),
    "HPE": re.compile(r"^[0-9A-Z]{6}-[0-9A-Z]{2,3}$"),
    # Lenovo: 2位数字+6位字母数字 或 7-10位字母数字 / Lenovo: 2 digits + 6 alphanum or 7-10 alphanum
    "LENOVO": re.compile(r"^\d{2}[A-Z0-9]{6}$|^[A-Z0-9]{7,10}$"),
    # Supermicro: SNK-P 前缀或 6-15位字母数字 / Supermicro: SNK-P prefix or 6-15 alphanum
    "SUPERMICRO": re.compile(r"^SNK-P[A-Z0-9-]+$|^[A-Z0-9]{6,15}$"),
}

# Samsung 原厂号特征：M 开头 + 2位数字 / Samsung native PN: M prefix + 2 digits
_SAMSUNG_MEMORY_PATTERN = re.compile(r"^M\d{2}[A-Z0-9]{5,20}$")


def should_mock_for_manufacturer(part_number: str, manufacturer: str) -> bool:
    """根据零件号特征判断是否适合该厂商 / Check if PN matches manufacturer.

    不匹配则直接返回 mock，避免无效 HTTP 请求。
    Returns True if the part number does NOT match the manufacturer's
    expected format, suggesting we should skip the HTTP request and
    return mock data directly.

    Args:
        part_number: 零件号 / Part number string.
        manufacturer: 厂商名称 / Manufacturer name (e.g., "DELL", "HP").

    Returns:
        True 表示应直接返回 mock / True if should return mock directly.
    """
    if not part_number or not manufacturer:
        return False

    pn = part_number.upper().strip()
    mfr = manufacturer.upper().strip()

    # Samsung 原厂号 → 不匹配 OEM / Samsung native PN → not OEM compatible
    # 例如 Samsung M393A8G40AB2-CWE 是原厂内存号 / e.g., Samsung M393A8G40AB2-CWE is native memory PN
    if _SAMSUNG_MEMORY_PATTERN.match(pn):
        if mfr in ("DELL", "HP", "HPE", "LENOVO", "SUPERMICRO"):
            return True

    # 检查厂商专用格式 / Check manufacturer-specific format
    pattern = _PN_OEM_PATTERNS.get(mfr)
    if pattern is not None:
        if not pattern.match(pn):
            return True  # 格式不匹配 → 直接 mock / Format mismatch → mock directly

    return False  # 可能匹配 → 允许 HTTP 请求 / Potentially matching → allow HTTP request


# ── Mock 数据生成公共函数 ───────────────────────────────────
def make_mock_part(
    part_number: str,
    manufacturer: str,
    manufacturer_zh: str,
    category: str = "",
    category_zh: str = "",
    description: str = "",
    description_zh: str = "",
    oem_brand: Optional[str] = None,
    specs: Optional[Dict[str, Any]] = None,
    price_usd: float = 0.0,
    reliability_score: float = 0.3,
    source_name: str = "",
    source_name_zh: str = "",
    url: Optional[str] = None,
) -> ServerPart:
    """创建标准 mock ServerPart / Create standardized mock ServerPart.

    所有 adapter 的 _mock_lookup() 统一调用此函数。
    Unified mock data generator for all adapters.
    """
    if not category:
        category, category_zh, _ = infer_category_from_text(part_number)
    if not description:
        description = f"{manufacturer} {category_zh} Part {part_number}"
    if not description_zh:
        description_zh = f"{manufacturer_zh}{category_zh}\u96f6\u4ef6 {part_number}"
    if not source_name:
        source_name = f"{manufacturer}_Mock"
    if not source_name_zh:
        source_name_zh = f"{manufacturer_zh}\u6a21\u62df\u6570\u636e\u6e90"

    now = utc_now()
    sources = [PriceSource(
        source_name=source_name,
        source_name_zh=source_name_zh,
        price_usd=price_usd if price_usd > 0 else None,
        original_price=price_usd if price_usd > 0 else None,
        original_currency="USD" if price_usd > 0 else None,
        url=url,
        in_stock=None,
        condition=None,
        last_seen=now,
        reliability_score=reliability_score,
    )]

    return ServerPart(
        part_number=part_number,
        manufacturer=manufacturer,
        manufacturer_zh=manufacturer_zh,
        oem_brand=oem_brand,
        category=category,
        category_zh=category_zh or CATEGORIES.get(category, "\u5176\u4ed6"),
        description=description,
        description_zh=description_zh,
        specifications=specs or {"inferred": True},
        raw_specifications={"note": "Mock data - website fetch failed"},
        sources=sources,
        median_price_usd=price_usd if price_usd > 0 else None,
        price_range_usd=(price_usd, price_usd) if price_usd > 0 else None,
        confidence_score=reliability_score,
        last_updated=now,
    )


def make_market_mock_part(
    adapter_name: str,
    adapter_name_zh: str,
    part_number: str,
    reliability_score: float,
    search_url: str,
    price_low: float = 10.0,
    price_high: float = 500.0,
) -> ServerPart:
    """创建市场适配器 mock ServerPart / Create market adapter mock ServerPart.

    用于 eBay/Amazon/AliExpress 等市场适配器的 _mock_lookup()。
    Used for market adapters' _mock_lookup() method.
    """
    mock_price = round(random.uniform(price_low, price_high), 2)
    now = utc_now()
    return ServerPart(
        part_number=part_number,
        manufacturer="UNKNOWN",
        manufacturer_zh="\u672a\u77e5\u5382\u5546",
        category="OTHERS",
        category_zh="\u5176\u4ed6",
        description=f"{adapter_name} mock result for {part_number}",
        description_zh=f"{adapter_name_zh}\u6a21\u62df\u6570\u636e: {part_number}",
        specifications={},
        raw_specifications={},
        sources=[PriceSource(
            source_name=adapter_name,
            source_name_zh=adapter_name_zh,
            price_usd=mock_price,
            original_price=mock_price,
            original_currency="USD",
            url=search_url,
            condition="new",
            in_stock=True,
            last_seen=now,
            reliability_score=reliability_score,
        )],
        median_price_usd=mock_price,
        price_range_usd=(mock_price, mock_price),
        confidence_score=reliability_score * 0.3,
        last_updated=now,
    )
