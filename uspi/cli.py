"""
USPI 命令行工具 / Command Line Interface

任何 Agent 均可通过子进程调用 CLI 使用 USPI。
Any agent can call USPI via subprocess.

用法 / Usage:
    python -m uspi.cli lookup 0WX202
    python -m uspi.cli lookup M393A8G40AB2-CWE --format json
    python -m uspi.cli compare 0WX202 SNK-P0070APS4
    python -m uspi.cli batch 0WX202 872736-001 01KN234 --format csv
    python -m uspi.cli health

Token 优化 / Token-efficient: compact format default, no MCP overhead.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

try:
    from uspi.core.adapters import ADAPTER_REGISTRY
except ImportError:
    ADAPTER_REGISTRY = {}  # type: ignore[assignment]
try:
    from uspi.core.anti_crawl_fetcher import AntiCrawlFetcher as FetcherCls
except ImportError:
    try:
        from uspi.core.fetcher import Fetcher as FetcherCls  # type: ignore[assignment]
    except ImportError:
        FetcherCls = None  # type: ignore[misc,assignment]
try:
    from uspi.utils.currency import CurrencyConverter
except ImportError:
    CurrencyConverter = None  # type: ignore[misc,assignment]
try:
    from uspi.core.ocr_input import OcrInputCleaner
except ImportError:
    OcrInputCleaner = None  # type: ignore[misc,assignment]

_lock = threading.Lock()
_adapters: Dict[str, Any] = {}
_adapters_ready = False


def _get_adapters() -> Dict[str, Any]:
    """延迟初始化适配器 / Lazy-init adapters."""
    global _adapters_ready
    with _lock:
        if _adapters_ready:
            return _adapters
        fetcher = None
        currency = None
        if FetcherCls is not None:
            try:
                fetcher = FetcherCls()
            except Exception:
                pass
        if CurrencyConverter is not None:
            try:
                currency = CurrencyConverter()
            except Exception:
                pass
        for name, cls in ADAPTER_REGISTRY.items():
            try:
                _adapters[name] = cls(fetcher, currency)
            except Exception:
                pass
        _adapters_ready = True
        return _adapters


def _clean_pn(pn: str) -> str:
    """清洗零件号 / Clean part number."""
    if not pn or OcrInputCleaner is None:
        return pn
    try:
        c = OcrInputCleaner.clean_ocr_text(pn) or pn
        ext = OcrInputCleaner.extract_part_numbers(pn)
        return ext[0].get("cleaned", c) if ext else c
    except Exception:
        return pn


def _safe_lookup(adapter: Any, pn: str) -> Any:
    """带保护的适配器查询 / Safe adapter lookup."""
    try:
        if not getattr(adapter, "enabled", True):
            return None
        return adapter.lookup(pn)
    except Exception:
        return None


def _part_dict(part: Any) -> Dict[str, Any]:
    """零件转字典 / Part to compact dict."""
    d: Dict[str, Any] = {}
    for a in ["part_number", "manufacturer_zh", "category_zh",
              "median_price_usd", "confidence_score"]:
        v = getattr(part, a, None)
        if v is not None:
            d[a] = v
    if hasattr(part, "specifications") and part.specifications:
        d["specs"] = {k: v for k, v in part.specifications.items() if v is not None}
    if hasattr(part, "sources") and part.sources:
        d["prices"] = [{"src": s.source_name, "$": s.price_usd}
                       for s in part.sources[:3]]
    return d


def cmd_lookup(args: argparse.Namespace) -> int:
    """lookup 子命令 / lookup subcommand."""
    pn = _clean_pn(args.part_number)
    adapters = _get_adapters()
    parts: List[Any] = []

    # 并行查询
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(_safe_lookup, a, pn): n
                   for n, a in adapters.items()}
        for future in as_completed(futures, timeout=args.timeout + 5):
            try:
                r = future.result(timeout=args.timeout)
                if r:
                    parts.append(r)
            except Exception:
                pass

    if not parts:
        print(f"Not found: {pn}", file=sys.stderr)
        return 1

    result = {
        "pn": pn,
        "found": True,
        "count": len(parts),
        "results": [_part_dict(p) for p in parts],
    }

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.format == "csv":
        print("part_number,manufacturer,category,price_usd,confidence")
        for p in parts:
            print(f"{p.part_number},{getattr(p,'manufacturer_zh','')},"
                  f"{getattr(p,'category_zh','')},{getattr(p,'median_price_usd','')},"
                  f"{p.confidence_score}")
    else:
        # compact — default, token-efficient
        for p in parts:
            price = getattr(p, "median_price_usd", None)
            price_str = f"${price}" if price else "N/A"
            print(f"{p.part_number} | {getattr(p,'manufacturer_zh','')} | "
                  f"{getattr(p,'category_zh','')} | {price_str} | "
                  f"conf={p.confidence_score}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """compare 子命令 / compare subcommand."""
    adapters = _get_adapters()
    found: List[Any] = []
    for pn in args.part_numbers:
        for adapter in adapters.values():
            try:
                r = adapter.lookup(_clean_pn(pn))
                if r:
                    found.append(r)
                    break
            except Exception:
                continue

    if len(found) < 2:
        print(f"Only found {len(found)} part(s)", file=sys.stderr)
        return 1

    print("part_number | manufacturer | category | price_usd | confidence")
    print("-" * 70)
    for p in found:
        price = getattr(p, "median_price_usd", "N/A")
        print(f"{p.part_number} | {getattr(p,'manufacturer_zh','')} | "
              f"{getattr(p,'category_zh','')} | {price} | {p.confidence_score}")
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """batch 子命令 / batch subcommand."""
    adapters = _get_adapters()
    results: List[Dict[str, Any]] = []
    for pn in args.part_numbers:
        cleaned = _clean_pn(pn)
        parts: List[Any] = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(_safe_lookup, a, cleaned): n
                       for n, a in adapters.items()}
            for f in as_completed(futures, timeout=args.timeout + 5):
                try:
                    r = f.result(timeout=args.timeout)
                    if r:
                        parts.append(r)
                except Exception:
                    pass
        results.append({
            "pn": cleaned,
            "found": len(parts) > 0,
            "count": len(parts),
            "results": [_part_dict(p) for p in parts],
        })

    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            status = "✓" if r["found"] else "✗"
            print(f"{status} {r['pn']} ({r['count']} results)")
    return 0


def cmd_health(_: argparse.Namespace) -> int:
    """health 子命令 / health subcommand."""
    adapters = _get_adapters()
    print(json.dumps({
        "status": "ok",
        "version": "0.1.0",
        "adapters": sorted(adapters.keys()),
        "count": len(adapters),
    }, ensure_ascii=False, indent=2))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 入口 / CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="uspi",
        description="Universal Server Parts Intelligence CLI",
    )
    parser.add_argument("--workers", type=int, default=5,
                        help="Parallel workers (default: 5)")
    parser.add_argument("--timeout", type=int, default=10,
                        help="Timeout per adapter in seconds (default: 10)")
    sub = parser.add_subparsers(dest="command", required=True)

    # lookup
    p_lookup = sub.add_parser("lookup", help="Query a part number")
    p_lookup.add_argument("part_number", help="Part number to query")
    p_lookup.add_argument("--format", choices=["compact", "json", "csv"],
                          default="compact", help="Output format")
    p_lookup.set_defaults(func=cmd_lookup)

    # compare
    p_compare = sub.add_parser("compare", help="Compare multiple parts")
    p_compare.add_argument("part_numbers", nargs="+", help="Part numbers")
    p_compare.set_defaults(func=cmd_compare)

    # batch
    p_batch = sub.add_parser("batch", help="Batch query multiple parts")
    p_batch.add_argument("part_numbers", nargs="+", help="Part numbers")
    p_batch.add_argument("--format", choices=["compact", "json"],
                         default="compact", help="Output format")
    p_batch.set_defaults(func=cmd_batch)

    # health
    p_health = sub.add_parser("health", help="Show system status")
    p_health.set_defaults(func=cmd_health)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
