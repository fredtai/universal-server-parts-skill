"""
uspi/core/adapters/lenovo_adapter.py

Lenovo OEM 适配器 / Lenovo OEM Adapter.

通过 Lenovo Support 查询 Lenovo 服务器零件信息。
Queries Lenovo server part information via Lenovo Support.

支持零件号格式 / Supported part number formats:
- 01KN234 (FRU 号，7 位字母数字)
- 00WK892 (Lenovo 标准件号)
- 2 位数字 + 5 位字母数字
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

from uspi.core.adapters.base import CATEGORIES, BaseAdapter, PriceSource, ServerPart
from uspi.core.fetcher import FetchError
from uspi.core.parser import PartParser


# ---------------------------------------------------------------------------
# HTML 规格解析器 / HTML Specification Parser
# ---------------------------------------------------------------------------


class _LenovoHtmlParser(HTMLParser):
    """轻量级 Lenovo HTML 规格提取器 / Lightweight Lenovo HTML spec extractor.

    从 Lenovo Support 页面中提取零件描述、规格表和价格信息。
    Extracts part description, specification tables, and price info from
    Lenovo Support pages.
    """

    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_script = False
        self.current_tag: Optional[str] = None
        self.current_data: List[str] = []
        self.specs: Dict[str, str] = {}
        self.description: str = ""
        self.title: str = ""
        self._capture_title = False
        self._last_label: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self.current_tag = tag
        attrs_dict = dict(attrs)
        css_class = attrs_dict.get("class", "")

        if tag in ("script", "style"):
            self.in_script = True
            return

        if tag == "title":
            self._capture_title = True

        # 检测规格表格 / Detect spec table
        if tag == "table" and any(
            cls in css_class.lower()
            for cls in ["spec", "detail", "fru-info", "product-detail"]
        ):
            self.in_table = True

        if tag == "div" and any(
            cls in css_class.lower()
            for cls in ["spec", "detail", "part-info", "product-detail"]
        ):
            self.in_table = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self.in_script = False
            return

        if tag == "title":
            self._capture_title = False

        if tag in ("td", "div", "span") and self._last_label and self.current_data:
            value = " ".join("".join(self.current_data).split())
            if value:
                self.specs[self._last_label] = value
            self._last_label = None
            self.current_data = []

        if tag in ("table", "div") and self.in_table:
            self.in_table = False

        self.current_tag = None

    def handle_data(self, data: str) -> None:
        if self.in_script:
            return

        cleaned = data.strip()
        if not cleaned:
            return

        if self._capture_title:
            self.title = cleaned
            return

        # 检测标签 / Detect labels
        if cleaned.endswith(":") or cleaned.endswith(""):
            potential_label = cleaned.rstrip(":").strip()
            label_keywords = [
                "description", "fru", "part", "category", "type",
                "product", "model", "specification", "subsystem",
            ]
            if any(kw in potential_label.lower() for kw in label_keywords):
                self._last_label = potential_label
                return

        if self._last_label:
            self.current_data.append(cleaned)
        else:
            self.current_data.append(cleaned)


# ---------------------------------------------------------------------------
# LenovoAdapter 类 / LenovoAdapter Class
# ---------------------------------------------------------------------------


class LenovoAdapter(BaseAdapter):
    """Lenovo OEM 零件查询适配器 / Lenovo OEM parts lookup adapter.

    通过 Lenovo Support 查询 Lenovo 服务器零件的规格和价格。
    Queries Lenovo server part specifications and pricing via Lenovo Support.

    Attributes:
        name: 适配器英文标识 / Adapter English identifier.
        name_zh: 适配器中文名称 / Adapter Chinese name.
        source_url: Lenovo 支持页面 URL / Lenovo support URL.
        reliability_score: 数据源可信度 0.0-1.0 / Data source reliability score.
    """

    name = "lenovo"
    name_zh = "联想"
    source_url = "https://support.lenovo.com"
    reliability_score = 0.82

    # Lenovo Support URL / Lenovo Support URL
    BASE_URL = "https://support.lenovo.com/us/en/partslookup/{pn}"

    # 规格提取正则模式 / Specification extraction regex patterns
    SPEC_PATTERNS = {
        "part_number": re.compile(
            r"(?:FRU|Part Number|P/N)\s*[:#]?\s*([A-Z0-9]+)", re.I
        ),
        "description": re.compile(
            r"(?:Description|Product Description|Item Description)\s*[:#]?\s*([^<\n]+)",
            re.I,
        ),
        "category": re.compile(
            r"(?:Category|Product Type|SubSystem|Component)\s*[:#]?\s*([^<\n]+)", re.I
        ),
        "price": re.compile(r"\$([0-9,]+\.?\d*)", re.I),
        "capacity": re.compile(r"(\d+\.?\d*)\s*(GB|TB|MB)", re.I),
        "wattage": re.compile(r"(\d+)\s*W(?:att)?", re.I),
        "fru_number": re.compile(r"([0-9]{2}[A-Z0-9]{5,6})", re.I),
    }

    def __init__(self, fetcher: Any, currency_converter: Any) -> None:
        """初始化 Lenovo 适配器 / Initialize Lenovo adapter.

        Args:
            fetcher: Fetcher 实例 / Fetcher instance for HTTP requests.
            currency_converter: CurrencyConverter 实例 / CurrencyConverter instance.
        """
        super().__init__(fetcher, currency_converter)
        self._parser = PartParser()

    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询 Lenovo 零件信息 / Look up a Lenovo part by part number.

        执行流程 / Execution flow:
        1. 检查适配器是否启用 / Check if adapter is enabled.
        2. 构造 Lenovo Support URL / Construct Lenovo Support URL.
        3. 尝试抓取 HTML / Attempt to fetch HTML.
        4. 解析 HTML 提取规格 / Parse HTML to extract specifications.
        5. 抓取失败返回 mock 数据 / Return mock data on fetch failure.

        Args:
            part_number: Lenovo 零件号 / Lenovo part number (e.g., "01KN234").

        Returns:
            ServerPart 实例或 mock 数据 / ServerPart instance or mock data.
        """
        if not self.enabled:
            return self._fallback_disabled()

        cleaned_pn = part_number.strip().upper()
        url = self.BASE_URL.format(pn=cleaned_pn)

        try:
            html = self._fetcher.fetch(url)
            result = self._parse_html(html, cleaned_pn)
            if result is not None:
                return result
            return self._mock_lookup(cleaned_pn)
        except FetchError:
            return self._mock_lookup(cleaned_pn)

    def search_by_spec(self, **specs: Any) -> List[ServerPart]:
        """按规格参数搜索 Lenovo 零件 / Search Lenovo parts by specifications.

        当前为 mock 实现，返回空列表或基于规格的静态匹配。
        Current mock implementation returns empty list or static matches.

        Args:
            **specs: 规格键值对 / Specification key-value pairs.

        Returns:
            ServerPart 列表 / List of ServerPart instances.
        """
        results: List[ServerPart] = []
        category = specs.get("category", "").upper()

        if category in CATEGORIES:
            mock_pn = specs.get("part_number", "LENOVO-MOCK-001")
            part = self._mock_lookup(mock_pn)
            part.category = category
            part.category_zh = CATEGORIES.get(category, "其他")
            results.append(part)

        return results

    def _parse_html(self, html: str, part_number: str) -> Optional[ServerPart]:
        """从 HTML 中提取 Lenovo 零件规格 / Extract Lenovo part specs from HTML.

        Args:
            html: 抓取的 HTML 内容 / Fetched HTML content.
            part_number: 零件号 / Part number.

        Returns:
            ServerPart 实例，解析失败返回 None / ServerPart or None on parse failure.
        """
        raw_specs: Dict[str, str] = {}

        # 提取描述 / Extract description
        desc_match = self.SPEC_PATTERNS["description"].search(html)
        description = ""
        if desc_match:
            description = self._clean_html_text(desc_match.group(1))
            raw_specs["description"] = description

        # 提取类别 / Extract category
        cat_match = self.SPEC_PATTERNS["category"].search(html)
        category_hint = ""
        if cat_match:
            category_hint = self._clean_html_text(cat_match.group(1))
            raw_specs["category"] = category_hint

        # 提取 FRU 号 / Extract FRU number
        fru_match = self.SPEC_PATTERNS["fru_number"].search(html)
        fru_number = ""
        if fru_match:
            fru_number = fru_match.group(1).upper()
            raw_specs["fru_number"] = fru_number

        # 提取价格 / Extract price
        price_match = self.SPEC_PATTERNS["price"].search(html)
        price_usd: Optional[float] = None
        if price_match:
            try:
                price_usd = float(price_match.group(1).replace(",", ""))
                raw_specs["price"] = f"${price_match.group(1)}"
            except ValueError:
                pass

        # 提取容量 / Extract capacity
        cap_match = self.SPEC_PATTERNS["capacity"].search(html)
        if cap_match:
            raw_specs["capacity"] = f"{cap_match.group(1)} {cap_match.group(2)}"

        # 提取功耗 / Extract wattage
        watt_match = self.SPEC_PATTERNS["wattage"].search(html)
        if watt_match:
            raw_specs["wattage"] = f"{watt_match.group(1)}W"

        # 使用 PartParser 解析 / Use PartParser
        parse_result = self._parser.parse(part_number, description)

        # 确定分类 / Determine category
        category = parse_result.category or "OTHERS"
        category_zh = parse_result.category_zh or CATEGORIES.get(category, "其他")

        if category == "OTHERS" and description:
            categories = self._parser.infer_category(description)
            if categories:
                category = categories[0][0]
                category_zh = CATEGORIES.get(category, "其他")

        norm_specs = self._extract_normalized_specs(description, raw_specs)

        # 构建 sources / Build sources
        sources: List[PriceSource] = []
        if price_usd is not None:
            sources.append(
                PriceSource(
                    source_name="Lenovo Support",
                    source_name_zh="联想支持",
                    price_usd=price_usd,
                    original_price=price_usd,
                    original_currency="USD",
                    url=self.BASE_URL.format(pn=part_number),
                    in_stock=None,
                    condition="new",
                    reliability_score=self.reliability_score,
                )
            )

        now = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        return ServerPart(
            part_number=part_number,
            manufacturer="LENOVO",
            manufacturer_zh="联想",
            oem_brand="LENOVO",
            category=category,
            category_zh=category_zh,
            description=description or f"Lenovo Part {part_number}",
            description_zh=f"联想零件 {part_number}",
            specifications=norm_specs,
            raw_specifications=raw_specs,
            sources=sources,
            median_price_usd=price_usd,
            price_range_usd=(price_usd, price_usd) if price_usd else None,
            confidence_score=0.75 if sources else 0.5,
            last_updated=now,
        )

    def _mock_lookup(self, part_number: str) -> ServerPart:
        """返回 Lenovo 零件的 mock 数据 / Return mock data for a Lenovo part.

        当网站抓取失败时使用，基于零件号特征推断分类。
        Used when website fetch fails; infers category from part number features.

        Args:
            part_number: Lenovo 零件号 / Lenovo part number.

        Returns:
            带 mock 标志的完整 ServerPart / Complete ServerPart with mock flag.
        """
        parse_result = self._parser.parse(part_number)

        category = parse_result.category or "OTHERS"
        category_zh = parse_result.category_zh or CATEGORIES.get(category, "其他")

        # Lenovo FRU 号基于前缀推断 / Lenovo FRU prefix-based inference
        if category == "OTHERS" and len(part_number) >= 2:
            prefix_map = {
                "00": "STORAGE_HDD",
                "01": "MEMORY",
                "02": "CPU",
                "03": "NIC",
                "04": "PSU",
                "05": "FAN",
                "07": "RAID_CONTROLLER",
                "0A": "MOTHERBOARD",
            }
            prefix = part_number[:2]
            if prefix in prefix_map:
                category = prefix_map[prefix]
                category_zh = CATEGORIES.get(category, "其他")

        description = f"Lenovo {category_zh} FRU Part {part_number}"
        description_zh = f"联想{category_zh}FRU零件 {part_number}"

        raw_specs: Dict[str, str] = {"note": "Mock data - website fetch failed"}
        norm_specs: Dict[str, Any] = {"inferred": True}

        # 尝试提取容量 / Try to extract capacity
        cap_match = self.SPEC_PATTERNS["capacity"].search(part_number)
        if cap_match:
            raw_specs["capacity"] = f"{cap_match.group(1)} {cap_match.group(2)}"
            norm_specs["capacity_gb"] = self._normalize_capacity(
                cap_match.group(1), cap_match.group(2)
            )

        now = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        mock_source = PriceSource(
            source_name="Lenovo Support (Mock)",
            source_name_zh="联想支持 (模拟数据)",
            price_usd=None,
            url=self.BASE_URL.format(pn=part_number),
            in_stock=None,
            condition="new",
            reliability_score=0.3,
        )

        return ServerPart(
            part_number=part_number,
            manufacturer="LENOVO",
            manufacturer_zh="联想",
            oem_brand="LENOVO",
            category=category,
            category_zh=category_zh,
            description=description,
            description_zh=description_zh,
            specifications=norm_specs,
            raw_specifications=raw_specs,
            sources=[mock_source],
            median_price_usd=None,
            price_range_usd=None,
            confidence_score=0.3,
            last_updated=now,
        )

    def _extract_normalized_specs(
        self, description: str, raw_specs: Dict[str, str]
    ) -> Dict[str, Any]:
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
            if "RDIMM" in desc_upper:
                specs["dimm_type"] = "RDIMM"
            elif "LRDIMM" in desc_upper:
                specs["dimm_type"] = "LRDIMM"
            elif "UDIMM" in desc_upper:
                specs["dimm_type"] = "UDIMM"

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

        # 硬盘类型 / Storage type
        if "SAS" in desc_upper and "HDD" in desc_upper:
            specs["interface"] = "SAS"
        elif "SATA" in desc_upper and "SSD" in desc_upper:
            specs["interface"] = "SATA"
        elif "NVMe" in desc_upper or "NVME" in desc_upper:
            specs["interface"] = "NVMe"

        # RAID 控制器 / RAID controller
        if "RAID" in desc_upper:
            raid_match = re.search(r"(RAID-\d+)", desc_upper)
            if raid_match:
                specs["raid_level"] = raid_match.group(1)

        # 显卡 / GPU
        if "NVIDIA" in desc_upper or "GPU" in desc_upper:
            gpu_match = re.search(r"(Tesla|A100|H100|A40|V100)", desc_upper)
            if gpu_match:
                specs["gpu_model"] = gpu_match.group(1)

        return specs

    @staticmethod
    def _clean_html_text(text: str) -> str:
        """清理 HTML 文本 / Clean HTML text.

        Args:
            text: 原始 HTML 文本 / Raw HTML text.

        Returns:
            清理后的纯文本 / Cleaned plain text.
        """
        cleaned = re.sub(r"<[^>]+>", "", text)
        cleaned = " ".join(cleaned.split())
        return cleaned

    @staticmethod
    def _normalize_capacity(value: str, unit: str) -> float:
        """将容量归一化为 GB / Normalize capacity to GB.

        Args:
            value: 容量数值 / Capacity value.
            unit: 容量单位 / Capacity unit.

        Returns:
            以 GB 为单位的容量 / Capacity in GB.
        """
        val = float(value)
        unit_upper = unit.upper()
        if unit_upper == "TB":
            return val * 1024
        elif unit_upper == "MB":
            return val / 1024
        return val
