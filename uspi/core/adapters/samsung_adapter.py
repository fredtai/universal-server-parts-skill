"""
uspi/core/adapters/samsung_adapter.py

Samsung 适配器 / Samsung Adapter

Samsung 是全球最大的服务器内存制造商，零件号编码包含完整的规格信息。
Samsung is the world's largest server memory manufacturer; part numbers encode
complete specification information.

数据来源: Samsung 公开产品页面 / Data source: Samsung public product pages
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from uspi.core.adapters.base import CATEGORIES, BaseAdapter, PriceSource, ServerPart
from uspi.core.adapters._common import (
    infer_category_from_text,
    make_mock_part,
    utc_now,
)


class SamsungAdapter(BaseAdapter):
    """Samsung 服务器零件适配器 / Samsung server parts adapter.

    专注于 Samsung 服务器内存模块（DDR4/DDR5 RDIMM/LRDIMM）的查询与规格推断。
    Focused on Samsung server memory modules (DDR4/DDR5 RDIMM/LRDIMM) lookup
    and specification inference.

    Samsung 零件号编码规则 / Samsung part number encoding rules:
    - M393A8G40AB2-CWE = DDR4-3200 64GB RDIMM 2Rx4
    - M393A4K40CB2-CTD = DDR4-2666 32GB RDIMM 2Rx4
    - M321R8GA0PB0-CWM = DDR5-5600 64GB RDIMM 2Rx4

    编码结构 / Encoding structure:
    - 第1位: M = Memory module
    - 第2-4位: 393=DDR4 RDIMM, 394=DDR4 LRDIMM, 321=DDR5 RDIMM, 322=DDR5 LRDIMM
    - 第5位: A=1.2V(DDR4), B=1.1V(DDR5)
    - 容量段: 8G=64GB, 4G/4K=32GB, 2G/2R=16GB, 16G=128GB
    - 位宽: 40=x4, 80=x8
    - 速度代码: AB=3200, CB=2666, PB=5600

    Attributes:
        name: 适配器英文标识 / Adapter English identifier.
        name_zh: 适配器中文名称 / Adapter Chinese name.
        source_url: Samsung 产品页面 URL / Samsung product page URL.
        reliability_score: 数据源可信度 0.70 / Data source reliability score.
    """

    name = "samsung"
    name_zh = "\u4e09\u661f"
    source_url = "https://semiconductor.samsung.com/dram/module/"
    reliability_score = 0.70

    # Samsung 零件号前缀正则模式 / Samsung part number regex patterns
    SAMSUNG_PATTERNS: List[str] = [
        r"^M\d{3}[A-Z]\d[A-Z0-9]{5,20}",       # 标准 DDR4/5 RDIMM/LRDIMM
        r"^M\d{3}[BR]\d[A-Z0-9]{5,20}",          # 其他 Samsung 内存格式
    ]

    # Samsung 产品类型码映射 / Samsung product type code mapping
    # 第2-4位编码 / Positions 2-4 encoding
    PRODUCT_TYPE_MAP: Dict[str, Dict[str, str]] = {
        "393": {"type": "DDR4", "form": "RDIMM", "desc": "DDR4 RDIMM"},
        "394": {"type": "DDR4", "form": "LRDIMM", "desc": "DDR4 LRDIMM"},
        "395": {"type": "DDR4", "form": "UDIMM", "desc": "DDR4 UDIMM"},
        "321": {"type": "DDR5", "form": "RDIMM", "desc": "DDR5 RDIMM"},
        "322": {"type": "DDR5", "form": "LRDIMM", "desc": "DDR5 LRDIMM"},
        "323": {"type": "DDR5", "form": "UDIMM", "desc": "DDR5 UDIMM"},
        "386": {"type": "DDR4", "form": "SODIMM", "desc": "DDR4 SODIMM"},
        "316": {"type": "DDR5", "form": "SODIMM", "desc": "DDR5 SODIMM"},
    }

    # 速度代码映射 / Speed code mapping (Samsung 编码中的速度位)
    SPEED_HINTS: Dict[str, Dict[str, int]] = {
        # DDR4 速度 / DDR4 speeds
        "DDR4": {
            "AB": 3200, "CB": 2666, "BB": 2933, "DB": 2400,
            "EB": 2133, "FB": 3200, "GB": 2933, "HB": 2666,
        },
        # DDR5 速度 / DDR5 speeds
        "DDR5": {
            "PB": 5600, "QB": 5200, "RB": 4800, "SB": 4400,
            "TB": 4000, "UB": 3600, "VB": 3200, "WB": 6400,
        },
    }

    def lookup(self, part_number: str) -> Optional[ServerPart]:
        """按零件号查询 Samsung 零件信息 / Look up a Samsung part by part number.

        首先尝试从 Samsung 官网获取数据，失败时返回带规格推断的 mock 数据。
        First tries to fetch data from Samsung website, falls back to mock data
        with specification inference on failure.

        Args:
            part_number: Samsung 零件号 / Samsung part number (e.g., "M393A8G40AB2-CWE").

        Returns:
            ServerPart 实例或 None / ServerPart instance or None for invalid input.
        """
        if not part_number or not isinstance(part_number, str):
            return None
        if not self.enabled:
            return self._fallback_disabled()

        pn_upper = part_number.upper().strip()

        # Samsung 零件号快速格式检查 / Quick Samsung PN format check
        if not pn_upper.startswith("M") or len(pn_upper) < 8:
            return self._mock_lookup(part_number)

        # 额外验证：检查是否符合 Samsung 编码模式 / Extra validation against patterns
        if not any(re.match(p, pn_upper) for p in self.SAMSUNG_PATTERNS):
            return self._mock_lookup(part_number)

        try:
            url = f"{self.source_url}{pn_upper}"
            html = self._fetch_html(url, timeout=8)
            if html:
                result = self._parse_html(html, pn_upper)
                if result is not None:
                    return result
        except Exception:
            pass

        return self._mock_lookup(pn_upper)

    def search_by_spec(self, **specs: Any) -> List[ServerPart]:
        """按规格参数搜索 Samsung 零件 / Search Samsung parts by specifications.

        Args:
            **specs: 规格键值对 / Specification key-value pairs.

        Returns:
            ServerPart 列表（当前版本返回空列表）/ List of ServerPart instances.
        """
        return []

    def _parse_html(self, html: str, part_number: str) -> Optional[ServerPart]:
        """解析 Samsung 产品页 HTML / Parse Samsung product page HTML.

        由于 Samsung 网站可能有反爬机制，此解析器做尽力尝试。
        主要数据获取途径仍为 _mock_lookup() 的规格推断。

        Due to potential anti-scraping on Samsung website, this parser makes
        best-effort attempt. Primary data path remains _mock_lookup().

        Args:
            html: 抓取的 HTML 内容 / Fetched HTML content.
            part_number: 零件号 / Part number.

        Returns:
            ServerPart 实例，解析失败或数据不足返回 None / ServerPart or None.
        """
        if not html or len(html) < 100:
            return None

        # 检查页面是否包含产品信息 / Check if page contains product info
        if part_number not in html and part_number.replace("-", "") not in html:
            return None

        # 尝试提取标题 / Try to extract title
        title_match = re.search(r"<title>([^<]+)</title>", html, re.I)
        if title_match:
            title = title_match.group(1).strip()
            if "not found" in title.lower() or "404" in title:
                return None

        return None

    def _mock_lookup(self, part_number: str) -> ServerPart:
        """生成 Samsung mock 数据，带规格推断 / Generate Samsung mock data with spec inference.

        从 Samsung 零件号编码中解码容量、类型、速度等规格信息。
        Decodes capacity, type, speed and other specs from Samsung PN encoding.

        Args:
            part_number: Samsung 零件号 / Samsung part number.

        Returns:
            带完整规格推断的 ServerPart / ServerPart with full spec inference.
        """
        pn = part_number.upper()
        specs: Dict[str, Any] = {"inferred_from_pn": True}
        desc = f"Samsung {part_number}"
        desc_zh = f"\u4e09\u661f {part_number}"
        category = "MEMORY"
        category_zh = "\u5185\u5b58"

        # ── 产品类型解码 (第2-4位) / Product type decoding ──
        product_code = pn[1:4] if len(pn) >= 4 else ""
        product_info = self.PRODUCT_TYPE_MAP.get(product_code)

        if product_info:
            specs["memory_type"] = product_info["type"]
            specs["dimm_type"] = product_info["form"]
            desc += f" {product_info['desc']}"
            desc_zh += f" {product_info['desc']}"
        else:
            # 回退推断 / Fallback inference
            if "321" in pn[:5] or "322" in pn[:5] or "316" in pn[:5]:
                specs["memory_type"] = "DDR5"
                desc += " DDR5"
                desc_zh += " DDR5"
            else:
                specs["memory_type"] = "DDR4"
                desc += " DDR4"
                desc_zh += " DDR4"

        # ── 容量推断 / Capacity inference ──
        capacity = self._infer_capacity(pn)
        if capacity:
            specs["capacity_gb"] = capacity
            desc += f" {int(capacity)}GB"
            desc_zh += f" {int(capacity)}GB"

        # ── 位宽推断 / Data width inference ──
        width = self._infer_width(pn)
        if width:
            specs["data_width"] = width
            desc += f" {width}"
            desc_zh += f" {width}"

        # ── 速度推断 / Speed inference ──
        speed = self._infer_speed(pn)
        if speed:
            specs["speed_mbps"] = speed
            specs["speed_mhz"] = speed // 2  # DDR = 2x MT/s
            desc += f" {speed}Mbps"
            desc_zh += f" {speed}Mbps"

        # ── Rank 推断 / Rank inference ──
        rank = self._infer_rank(pn)
        if rank:
            specs["rank"] = rank
            desc += f" {rank}"
            desc_zh += f" {rank}"

        # ── 电压推断 (第5位) / Voltage inference ──
        voltage_char = pn[4] if len(pn) >= 5 else ""
        voltage_map = {
            "A": "1.2V",  # DDR4
            "B": "1.1V",  # DDR5
        }
        if voltage_char in voltage_map:
            specs["voltage"] = voltage_map[voltage_char]

        return make_mock_part(
            part_number=part_number,
            manufacturer="SAMSUNG",
            manufacturer_zh="\u4e09\u661f",
            category=category,
            category_zh=category_zh,
            description=desc,
            description_zh=desc_zh + "\uff08\u6a21\u62df\u6570\u636e\uff0cSamsung \u539f\u5382\u96f6\u4ef6\uff09",
            specs=specs,
            price_usd=0.0,
            reliability_score=0.55,  # Samsung 原厂比通用 OEM mock 更可信
        )

    # ── 规格推断辅助方法 / Spec inference helpers ──

    def _infer_capacity(self, pn: str) -> Optional[float]:
        """从零件号推断容量 (GB) / Infer capacity from part number.

        Samsung 容量编码规则 / Samsung capacity encoding:
        - 8G = 64GB (8 x 8Gb chips)
        - 4G/4K = 32GB (4 x 8Gb chips)
        - 2G/2R = 16GB (2 x 8Gb chips)
        - 16G = 128GB (16 x 8Gb chips)
        - AG = 128GB, BG = 256GB (DDR5)

        Args:
            pn: 大写的 Samsung 零件号 / Uppercase Samsung part number.

        Returns:
            容量 (GB) 或 None / Capacity in GB or None.
        """
        # 按优先级顺序匹配 / Match in priority order
        if "16G" in pn:
            return 128.0
        if "AG" in pn or "AAG" in pn:
            return 128.0
        if "BG" in pn or "BBG" in pn:
            return 256.0
        if "CG" in pn:
            return 512.0
        # 注意：必须在 4G/2G 之前检查 8G / Must check 8G before 4G/2G
        if "8G" in pn:
            return 64.0
        if "4G" in pn or "4K" in pn or "4KG" in pn:
            return 32.0
        if "2G" in pn or "2R" in pn or "2RG" in pn:
            return 16.0
        if "1G" in pn:
            return 8.0
        return None

    def _infer_width(self, pn: str) -> Optional[str]:
        """从零件号推断位宽 / Infer data width from part number.

        Samsung 位宽编码:
        - 40 = x4
        - 80 = x8

        Args:
            pn: 大写的 Samsung 零件号 / Uppercase Samsung part number.

        Returns:
            位宽字符串或 None / Width string or None.
        """
        # 在零件号中寻找位宽码 / Look for width code in PN
        width_match = re.search(r"\d([48])0[A-Z]", pn)
        if width_match:
            return f"x{width_match.group(1)}"
        return None

    def _infer_speed(self, pn: str) -> Optional[int]:
        """从零件号推断速度 / Infer speed from part number.

        从编码中提取速度代码并匹配到实际 Mbps 值。
        Extracts speed code from PN and maps to actual Mbps value.

        Args:
            pn: 大写的 Samsung 零件号 / Uppercase Samsung part number.

        Returns:
            速度 (Mbps) 或 None / Speed in Mbps or None.
        """
        # 确定内存类型 / Determine memory type
        if "DDR5" in pn or "321" in pn[:5] or "322" in pn[:5]:
            speed_table = self.SPEED_HINTS["DDR5"]
        else:
            speed_table = self.SPEED_HINTS["DDR4"]

        # 尝试匹配速度代码 / Try to match speed code
        body = pn[5:] if len(pn) > 5 else pn
        for code, speed in sorted(speed_table.items(), key=lambda x: -x[1]):
            if code in body:
                return speed

        # 根据后缀中的速度标识回退推断 / Fallback from suffix speed hints
        suffix = pn.split("-")[-1] if "-" in pn else ""
        if suffix:
            speed_map = {
                "CWE": 3200, "CTD": 2666, "CWF": 2933, "CRE": 2400,
                "CWM": 5600, "CWK": 5200, "CWJ": 4800, "CWH": 4400,
            }
            for key, spd in speed_map.items():
                if suffix.startswith(key):
                    return spd

        return None

    def _infer_rank(self, pn: str) -> Optional[str]:
        """从零件号推断 Rank 配置 / Infer rank configuration from part number.

        Samsung Rank 编码:
        - 零件号末尾数字: 2=2Rank, 4=4Rank, 1=1Rank
        通常出现在主代码段最后一位。

        Args:
            pn: 大写的 Samsung 零件号 / Uppercase Samsung part number.

        Returns:
            Rank 字符串或 None / Rank string or None.
        """
        # 提取主代码段（破折号前）/ Extract main code (before dash)
        main_part = pn.split("-")[0] if "-" in pn else pn
        if len(main_part) >= 2:
            last_char = main_part[-1]
            rank_map = {"1": "1Rank", "2": "2Rank", "4": "4Rank", "8": "8Rank"}
            if last_char in rank_map:
                return rank_map[last_char]
        return None
