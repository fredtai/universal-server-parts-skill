"""
uspi/core/comparator.py

零件对比引擎 / Part Comparison Engine

并排比较多个 ServerPart，生成对比矩阵、Markdown 表格（可粘贴到 Excel）、
以及超紧凑对比文本。
Side-by-side comparison of multiple ServerPart objects, generating comparison
matrices, Markdown tables (Excel-pasteable), and ultra-compact text.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from uspi.core.adapters.base import CATEGORIES, PriceSource, ServerPart


class Comparator:
    """零件对比引擎：并排比较多个零件并生成可读的对比结果。

    Part comparison engine: Compares multiple parts side by side and generates
    readable comparison results.

    支持价格、规格、可用性三个维度的对比，可生成 Markdown 表格
    （直接复制粘贴到 Excel）和超紧凑文本（Token 最优）。
    Supports price, specs, and availability dimensions. Can generate Markdown
    tables (copy-paste to Excel) and ultra-compact text (Token-optimal).
    """

    # 对比维度默认集合 / Default comparison dimensions
    _DEFAULT_DIMENSIONS: list[str] = ["price", "specs", "availability"]

    # 价格维度指标 / Price dimension metrics
    _PRICE_METRICS: list[str] = ["median_price_usd", "price_range_usd", "source_count"]

    # 可用性指标 / Availability metrics
    _AVAIL_METRICS: list[str] = ["in_stock_sources", "new_sources", "refurbished_sources", "used_sources"]

    def compare(
        self,
        parts: list[ServerPart],
        dimensions: Optional[list[str]] = None,
    ) -> dict:
        """对比多个 ServerPart，返回对比矩阵。

        Compare multiple ServerPart objects and return a comparison matrix.

        Args:
            parts: 要对比的 ServerPart 列表（至少 2 个）/ List of ServerPart to compare (min 2).
            dimensions: 对比维度列表，可选 ["price", "specs", "availability"]
                        List of dimensions to compare, optional.

        Returns:
            包含以下键的字典 / Dictionary with keys:
            - parts: 原始零件列表 / Original part list
            - price_matrix: 价格对比矩阵 / Price comparison matrix
            - spec_matrix: 规格对比矩阵 / Spec comparison matrix
            - availability_matrix: 可用性矩阵 / Availability matrix
            - summary: 最优推荐摘要 / Best recommendation summary
        """
        if not parts:
            return {"parts": [], "price_matrix": {}, "spec_matrix": {}, "summary": {}}

        if dimensions is None:
            dimensions = self._DEFAULT_DIMENSIONS

        dims: set[str] = set(dim.lower() for dim in dimensions)

        result: dict[str, Any] = {
            "parts": parts,
            "price_matrix": {},
            "spec_matrix": {},
            "availability_matrix": {},
            "summary": {},
        }

        # -- Price comparison / 价格对比 --
        if "price" in dims:
            result["price_matrix"] = self._build_price_matrix(parts)

        # -- Specification comparison / 规格对比 --
        if "specs" in dims:
            result["spec_matrix"] = self._build_spec_matrix(parts)

        # -- Availability comparison / 可用性对比 --
        if "availability" in dims:
            result["availability_matrix"] = self._build_availability_matrix(parts)

        # -- Summary / best recommendation / 摘要与最优推荐 --
        result["summary"] = self._build_summary(parts, result)

        return result

    def to_markdown_matrix(self, comparison: dict, lang: str = "zh") -> str:
        """生成 Markdown 对比表格（可直接复制粘贴到 Excel）。

        Generate a Markdown comparison table (directly copy-pasteable to Excel).

        列：零件号 | 厂商 | 分类 | 美元价 | 规格摘要 | 货源数 | 可信度
        Columns: Part Number | Manufacturer | Category | USD Price | Spec Summary | Sources | Confidence

        Args:
            comparison: compare() 方法返回的对比字典 / Comparison dict from compare().
            lang: 语言代码 "zh" 或 "en" / Language code.

        Returns:
            Markdown 格式字符串 / Markdown formatted string.
        """
        parts: list[ServerPart] = comparison.get("parts", [])
        if not parts:
            return "_No parts to compare / 无零件可对比_"

        # 表头 / Headers
        if lang == "zh":
            headers: list[str] = ["零件号", "厂商", "分类", "美元价", "规格摘要", "货源数", "可信度"]
        else:
            headers = ["Part Number", "Manufacturer", "Category", "USD Price", "Spec Summary", "Sources", "Confidence"]

        lines: list[str] = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join([":---" for _ in headers]) + "|")

        for p in parts:
            price_str: str = f"${p.median_price_usd:.2f}" if p.median_price_usd is not None else "N/A"
            spec_summary: str = self._specs_summary(p.specifications)
            src_count: str = str(len(p.sources))
            conf_str: str = f"{p.confidence_score:.0%}"
            cat_display: str = p.category_zh if lang == "zh" and p.category_zh else p.category
            mfr_display: str = p.manufacturer_zh if lang == "zh" and p.manufacturer_zh else p.manufacturer

            row: list[str] = [
                p.part_number,
                mfr_display,
                cat_display,
                price_str,
                spec_summary,
                src_count,
                conf_str,
            ]
            lines.append("| " + " | ".join(row) + " |")

        # 添加最优推荐行 / Add best recommendation row
        summary: dict = comparison.get("summary", {})
        if summary:
            lines.append("")
            best_pn: Optional[str] = summary.get("best_part_number")
            reason: str = summary.get("reason", "")
            if lang == "zh":
                lines.append(f"**最优推荐 / Best Pick**: `{best_pn}` — {reason}")
            else:
                lines.append(f"**Best Pick**: `{best_pn}` — {reason}")

        return "\n".join(lines)

    def to_compact_comparison(self, comparison: dict, lang: str = "zh") -> str:
        """超紧凑对比文本（Token 效率最优）。

        Ultra-compact comparison text (Token-optimal).

        每行一个零件，仅核心字段，用最少的 Token 表达对比结果。
        One part per line, core fields only, minimal Token usage.

        Args:
            comparison: compare() 方法返回的对比字典 / Comparison dict from compare().
            lang: 语言代码 "zh" 或 "en" / Language code.

        Returns:
            紧凑文本字符串 / Compact text string.
        """
        parts: list[ServerPart] = comparison.get("parts", [])
        summary: dict = comparison.get("summary", {})
        if not parts:
            return "N/A"

        lines: list[str] = []
        for i, p in enumerate(parts, 1):
            price: str = f"${p.median_price_usd:.0f}" if p.median_price_usd else "N/A"
            cat: str = p.category_zh if lang == "zh" and p.category_zh else p.category
            srcs: str = str(len(p.sources))
            spec_sum: str = self._specs_summary(p.specifications, max_len=25)
            lines.append(
                f"{i}.{p.part_number}|{p.manufacturer}|{cat}|{price}|{spec_sum}|src:{srcs}|conf:{p.confidence_score:.0%}"
            )

        # 添加最优标记 / Add best pick marker
        best_pn: Optional[str] = summary.get("best_part_number")
        if best_pn:
            for i, line in enumerate(lines):
                if best_pn in line:
                    lines[i] = line + " ★BEST"
                    break

        return "\n".join(lines)

    def _find_best_value(self, parts: list[ServerPart], spec_key: str) -> tuple:
        """找出某规格维度的最优值。

        Find the best value for a given specification dimension.

        对于数值型规格（如 capacity、frequency），取最大值视为最优；
        对于非数值型规格，取出现频率最高的值。
        For numeric specs (e.g., capacity, frequency), the maximum is considered best.
        For non-numeric specs, the most frequent value is taken.

        Args:
            parts: ServerPart 列表 / List of ServerPart objects.
            spec_key: 规格维度键名 / Spec dimension key.

        Returns:
            (最优零件的 part_number, 最优值) 元组
            Tuple of (best part_number, best value).
        """
        candidates: list[tuple[str, Any]] = []

        for p in parts:
            spec_val: Any = p.specifications.get(spec_key)
            if spec_val is None:
                continue
            # 处理归一化后的规格值 / Handle normalized spec value
            if isinstance(spec_val, dict) and "value" in spec_val:
                actual_val: Any = spec_val["value"]
            else:
                actual_val = spec_val
            candidates.append((p.part_number, actual_val))

        if not candidates:
            return ("", None)

        # 尝试数值比较 / Try numeric comparison
        numeric_candidates: list[tuple[str, float]] = []
        for pn, val in candidates:
            try:
                numeric_candidates.append((pn, float(val)))
            except (ValueError, TypeError):
                continue

        if numeric_candidates:
            # 取最大值 / Take maximum (e.g., larger capacity is better)
            best_pn, best_val = max(numeric_candidates, key=lambda x: x[1])
            return (best_pn, best_val)

        # 非数值型：取频率最高 / Non-numeric: take most frequent
        from collections import Counter

        values: list[Any] = [v for _, v in candidates]
        most_common: Any = Counter(str(v) for v in values).most_common(1)[0][0]
        for pn, val in candidates:
            if str(val) == most_common:
                return (pn, val)

        return candidates[0]

    # ------------------------------------------------------------------
    # 内部构建方法 / Internal build methods
    # ------------------------------------------------------------------

    def _build_price_matrix(self, parts: list[ServerPart]) -> dict:
        """构建价格对比矩阵。

        Build the price comparison matrix.

        Args:
            parts: ServerPart 列表 / List of ServerPart objects.

        Returns:
            价格矩阵字典 / Price matrix dictionary.
        """
        matrix: dict[str, Any] = {
            "parts": [p.part_number for p in parts],
            "median_prices": [],
            "price_ranges": [],
            "source_counts": [],
            "cheapest": None,
            "most_expensive": None,
            "best_value": None,
        }

        valid_prices: list[tuple[str, float]] = []
        for p in parts:
            matrix["median_prices"].append(p.median_price_usd)
            matrix["price_ranges"].append(p.price_range_usd)
            matrix["source_counts"].append(len(p.sources))
            if p.median_price_usd is not None:
                valid_prices.append((p.part_number, p.median_price_usd))

        if valid_prices:
            cheapest = min(valid_prices, key=lambda x: x[1])
            expensive = max(valid_prices, key=lambda x: x[1])
            matrix["cheapest"] = {"part_number": cheapest[0], "price": cheapest[1]}
            matrix["most_expensive"] = {"part_number": expensive[0], "price": expensive[1]}

            # 最佳性价比：价格低且来源多 / Best value: low price with many sources
            max_sources: int = max(len(p.sources) for p in parts)
            min_price: float = min(v for _, v in valid_prices)
            best_score: float = float("inf")
            best_pn: str = ""
            for p in parts:
                if p.median_price_usd is None:
                    continue
                source_bonus: float = 1.0 + (0.1 * len(p.sources) / max(max_sources, 1))
                score: float = p.median_price_usd / source_bonus
                if score < best_score:
                    best_score = score
                    best_pn = p.part_number
            matrix["best_value"] = best_pn

        return matrix

    def _build_spec_matrix(self, parts: list[ServerPart]) -> dict:
        """构建规格对比矩阵。

        Build the specification comparison matrix.

        Args:
            parts: ServerPart 列表 / List of ServerPart objects.

        Returns:
            规格矩阵字典 / Spec matrix dictionary.
        """
        matrix: dict[str, Any] = {
            "parts": [p.part_number for p in parts],
            "common_keys": [],
            "diff_keys": [],
            "all_keys": set(),
            "values": {},  # key -> list of values per part
            "best_in_class": {},  # key -> best part_number
        }

        # 收集所有规格键 / Collect all spec keys
        all_keys: set[str] = set()
        for p in parts:
            all_keys.update(p.specifications.keys())
        matrix["all_keys"] = sorted(all_keys)

        # 对每个键，收集每个零件的值 / For each key, collect each part's value
        for key in all_keys:
            values: list[Any] = []
            for p in parts:
                spec: Any = p.specifications.get(key)
                if isinstance(spec, dict) and "value" in spec:
                    values.append(spec["value"])
                else:
                    values.append(spec)
            matrix["values"][key] = values

            # 检查是否所有零件都相同 / Check if all parts have same value
            non_none: list[Any] = [v for v in values if v is not None]
            if non_none and all(str(v) == str(non_none[0]) for v in non_none):
                matrix["common_keys"].append(key)
            else:
                matrix["diff_keys"].append(key)

            # 找最优值 / Find best value
            if non_none:
                try:
                    best_pn, _ = self._find_best_value(parts, key)
                    if best_pn:
                        matrix["best_in_class"][key] = best_pn
                except Exception:
                    pass

        return matrix

    def _build_availability_matrix(self, parts: list[ServerPart]) -> dict:
        """构建可用性对比矩阵。

        Build the availability comparison matrix.

        Args:
            parts: ServerPart 列表 / List of ServerPart objects.

        Returns:
            可用性矩阵字典 / Availability matrix dictionary.
        """
        matrix: dict[str, Any] = {
            "parts": [p.part_number for p in parts],
            "in_stock_counts": [],
            "condition_breakdown": [],
            "best_availability": None,
        }

        best_stock_count: int = -1
        best_pn: str = ""

        for p in parts:
            in_stock: int = sum(
                1 for s in p.sources if s.in_stock is True
            )
            new_count: int = sum(
                1 for s in p.sources if s.condition == "new"
            )
            ref_count: int = sum(
                1 for s in p.sources if s.condition == "refurbished"
            )
            used_count: int = sum(
                1 for s in p.sources if s.condition == "used"
            )

            matrix["in_stock_counts"].append(in_stock)
            matrix["condition_breakdown"].append({
                "new": new_count,
                "refurbished": ref_count,
                "used": used_count,
            })

            if in_stock > best_stock_count:
                best_stock_count = in_stock
                best_pn = p.part_number

        if best_pn:
            matrix["best_availability"] = {
                "part_number": best_pn,
                "in_stock_count": best_stock_count,
            }

        return matrix

    def _build_summary(self, parts: list[ServerPart], result: dict) -> dict:
        """构建最优推荐摘要。

        Build the best recommendation summary.

        综合价格、规格、可用性三个维度，给出最优推荐。
        Combines price, specs, and availability dimensions to give best recommendation.

        Args:
            parts: ServerPart 列表 / List of ServerPart objects.
            result: 包含各矩阵的对比结果 / Comparison result with matrices.

        Returns:
            摘要字典 / Summary dictionary.
        """
        if not parts:
            return {}

        summary: dict[str, Any] = {
            "total_parts": len(parts),
            "part_numbers": [p.part_number for p in parts],
        }

        # 综合评分 / Composite score
        scores: dict[str, float] = {}
        for p in parts:
            score: float = 0.0

            # 价格分（越低越好，反转）/ Price score (lower is better, invert)
            pm: dict = result.get("price_matrix", {})
            if p.median_price_usd is not None:
                prices: list[float] = [
                    pp.median_price_usd for pp in parts if pp.median_price_usd is not None
                ]
                if prices:
                    max_price: float = max(prices)
                    min_price: float = min(prices)
                    price_range: float = max_price - min_price if max_price > min_price else 1.0
                    price_score: float = (max_price - p.median_price_usd) / price_range
                    score += price_score * 0.3  # 价格权重 30%

            # 来源分（越多越好）/ Source score (more is better)
            max_sources: int = max(len(pp.sources) for pp in parts)
            if max_sources > 0:
                score += (len(p.sources) / max_sources) * 0.3  # 来源权重 30%

            # 可信度分 / Confidence score
            score += p.confidence_score * 0.4  # 可信度权重 40%

            scores[p.part_number] = round(score, 3)

        if scores:
            best_pn: str = max(scores, key=scores.get)
            summary["best_part_number"] = best_pn
            summary["best_score"] = scores[best_pn]
            summary["all_scores"] = scores

            # 生成推荐原因 / Generate recommendation reason
            best_part: Optional[ServerPart] = None
            for p in parts:
                if p.part_number == best_pn:
                    best_part = p
                    break

            if best_part:
                reasons: list[str] = []
                # 价格原因 / Price reason
                pm = result.get("price_matrix", {})
                if pm.get("cheapest") and pm["cheapest"]["part_number"] == best_pn:
                    reasons.append("最低价格 / Lowest price")
                # 来源原因 / Source reason
                max_src: int = max(len(pp.sources) for pp in parts)
                if len(best_part.sources) == max_src and max_src > 0:
                    reasons.append("最多货源 / Most sources")
                # 可信度原因 / Confidence reason
                if best_part.confidence_score >= 0.8:
                    reasons.append("高可信度 / High confidence")

                if not reasons:
                    reasons.append("综合评分最高 / Highest composite score")

                summary["reason"] = "; ".join(reasons)

        return summary

    def _specs_summary(self, specs: dict, max_len: int = 40) -> str:
        """生成规格摘要字符串。

        Generate a specification summary string.

        将规格字典压缩为简短的可读字符串，如 '32GB DDR4-2933, 1.2V'。
        Compresses spec dict into a short readable string.

        Args:
            specs: 规格字典 / Specification dictionary.
            max_len: 最大长度限制 / Maximum length limit.

        Returns:
            规格摘要字符串 / Spec summary string.
        """
        if not specs:
            return "-"

        parts: list[str] = []
        # 优先显示关键规格 / Prioritize key specs
        priority_keys: list[str] = ["capacity", "frequency", "type", "voltage", "power", "speed"]

        for key in priority_keys:
            if key in specs:
                val: Any = specs[key]
                if isinstance(val, dict):
                    val_str: str = f"{val.get('value', '')}{val.get('unit', '')}"
                else:
                    val_str = str(val)
                if val_str:
                    parts.append(val_str)

        # 如果没有优先键匹配，取前3个 / If no priority keys matched, take first 3
        if not parts:
            for key in list(specs.keys())[:3]:
                val = specs[key]
                if isinstance(val, dict):
                    val_str = f"{val.get('value', '')}{val.get('unit', '')}"
                else:
                    val_str = str(val)
                if val_str and val_str.lower() not in ("none", "null", ""):
                    parts.append(val_str)

        summary: str = ", ".join(parts)
        if len(summary) > max_len:
            summary = summary[:max_len - 3] + "..."
        return summary if summary else "-"


__all__ = ["Comparator"]
