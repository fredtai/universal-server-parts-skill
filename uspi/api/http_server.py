"""
USPI HTTP REST API Server — 通用 Agent 调用接口
Universal Agent-Callable HTTP API

任何 Agent（Kimi、Claude、GPT、自研 Agent）均可通过 HTTP 调用。
Any agent can call via HTTP POST/GET.

启动 / Start:  python -m uspi.api.http_server [port]
默认端口 / Default: 8787

端点 / Endpoints:
  POST /lookup  — 零件查询（支持 OCR、批量、并行）
  POST /compare — 零件对比
  POST /batch   — 批量查询（多个零件号一次性返回）
  GET  /health  — 健康检查 + 可用适配器列表
"""

from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# -- 核心导入（优雅降级）/ Core imports ----------------------------
try:
    from uspi.core.ocr_input import OcrInputCleaner
except ImportError:
    OcrInputCleaner = None  # type: ignore[misc,assignment]
try:
    from uspi.core.adapters import ADAPTER_REGISTRY
except ImportError:
    ADAPTER_REGISTRY = {}  # type: ignore[assignment]
try:
    from uspi.core.exporter import Exporter
except ImportError:
    Exporter = None  # type: ignore[misc,assignment]
try:
    from uspi.core.comparator import Comparator
except ImportError:
    Comparator = None  # type: ignore[misc,assignment]
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

# -- 线程安全全局状态 / Thread-safe state --------------------------
_lock = threading.Lock()
_adapters: Dict[str, Any] = {}
_adapters_ready = False


def _get_adapters() -> Dict[str, Any]:
    """延迟初始化适配器（线程安全）/ Lazy-init adapters."""
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
    """清洗零件号（支持 OCR）/ Clean part number."""
    if not pn or OcrInputCleaner is None:
        return pn
    try:
        c = OcrInputCleaner.clean_ocr_text(pn) or pn
        ext = OcrInputCleaner.extract_part_numbers(pn)
        return ext[0].get("cleaned", c) if ext else c
    except Exception:
        return pn


class UspiHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器 — CORS 支持 / CORS-enabled HTTP handler."""

    # CORS 头 / CORS headers（允许浏览器前端直接调用）
    _CORS_HEADERS = [
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
        ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
        ("Access-Control-Max-Age", "86400"),
    ]

    def do_OPTIONS(self) -> None:  # noqa: N802
        """处理 CORS 预检 / Handle CORS preflight."""
        self.send_response(204)
        for k, v in self._CORS_HEADERS:
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        body = self._read_body()
        if body is None:
            self._send_json({"error": "Invalid JSON", "code": 400}, 400)
            return
        try:
            if path == "/lookup":
                self._send_json(self._handle_lookup(body))
            elif path == "/compare":
                self._send_json(self._handle_compare(body))
            elif path == "/batch":
                self._send_json(self._handle_batch(body))
            else:
                self._send_json({"error": f"Not found: {path}", "code": 404}, 404)
        except Exception as e:
            self._send_json({"error": str(e), "code": 500}, 500)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/health":
            adapters = _get_adapters()
            self._send_json({
                "status": "ok",
                "version": "0.1.0",
                "unit_system": "SI",
                "currency": "USD",
                "adapters_count": len(adapters),
                "adapters": sorted(adapters.keys()),
                "endpoints": ["POST /lookup", "POST /compare", "POST /batch", "GET /health"],
            })
        else:
            self._send_json({"error": f"Not found: {path}", "code": 404}, 404)

    def _read_body(self) -> Optional[Dict[str, Any]]:
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))  # type: ignore[no-any-return]
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    # ── /lookup ──────────────────────────────────────────────────
    def _handle_lookup(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """单个零件查询 — 并行所有适配器。"""
        pn = body.get("part_number", "")
        if not pn:
            return {"error": "part_number required", "code": 400}

        cleaned = _clean_pn(pn)
        adapters = _get_adapters()
        max_workers = body.get("max_workers", 5)
        timeout = body.get("timeout", 12)

        # 并行查询所有适配器
        parts = self._parallel_lookup(cleaned, adapters, max_workers, timeout)

        # 截断来源
        max_src = body.get("max_sources", 3)
        for p in parts:
            if hasattr(p, "sources") and p.sources:
                p.sources = p.sources[:max_src]

        if not parts:
            return {"part_number": cleaned, "found": False}

        return {
            "part_number": cleaned,
            "found": True,
            "count": len(parts),
            "results": self._to_dicts(parts, body.get("fields")),
        }

    # ── /compare ─────────────────────────────────────────────────
    def _handle_compare(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """零件对比 — 查第一个成功即停。"""
        pns = body.get("part_numbers", [])
        if len(pns) < 2:
            return {"error": "Need >=2 part numbers", "code": 400}

        adapters = _get_adapters()
        found: List[Any] = []
        not_found: List[str] = []

        for pn in pns:
            pn = pn.strip()
            if not pn:
                continue
            r = self._first_hit(_clean_pn(pn), adapters)
            if r:
                found.append(r)
            else:
                not_found.append(pn)

        return {
            "found_count": len(found),
            "not_found": not_found,
            "parts": self._to_dicts(found, body.get("fields")),
        }

    # ── /batch ───────────────────────────────────────────────────
    def _handle_batch(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """批量查询 — 多个零件号一次性并行返回。"""
        pns = body.get("part_numbers", [])
        if not pns:
            return {"error": "part_numbers required", "code": 400}

        adapters = _get_adapters()
        max_workers = body.get("max_workers", 5)
        per_pn_timeout = body.get("timeout", 10)
        results: List[Dict[str, Any]] = []

        for pn in pns:
            cleaned = _clean_pn(pn)
            parts = self._parallel_lookup(cleaned, adapters, max_workers, per_pn_timeout)
            results.append({
                "part_number": cleaned,
                "found": len(parts) > 0,
                "count": len(parts),
                "results": self._to_dicts(parts, body.get("fields")),
            })

        return {"batch_size": len(pns), "results": results}

    # ── 并行查询 / Parallel lookup ───────────────────────────────
    @staticmethod
    def _parallel_lookup(pn: str, adapters: Dict[str, Any], max_workers: int, timeout: int) -> List[Any]:
        """使用 ThreadPoolExecutor 并行查询所有适配器。"""
        parts: List[Any] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(UspiHandler._safe_lookup, adapter, pn, timeout): name
                for name, adapter in adapters.items()
            }
            for future in as_completed(futures, timeout=timeout + 5):
                try:
                    result = future.result(timeout=timeout)
                    if result is not None:
                        parts.append(result)
                except Exception:
                    pass
        return parts

    @staticmethod
    def _safe_lookup(adapter: Any, pn: str, timeout: int) -> Any:
        """带异常保护的适配器查询。"""
        try:
            if not getattr(adapter, "enabled", True):
                return None
            return adapter.lookup(pn)
        except Exception:
            return None

    @staticmethod
    def _first_hit(pn: str, adapters: Dict[str, Any]) -> Any:
        """串行查询，第一个成功即返回。"""
        for adapter in adapters.values():
            try:
                r = adapter.lookup(pn) if hasattr(adapter, "lookup") else None
                if r is not None:
                    return r
            except Exception:
                continue
        return None

    # ── 格式化 / Formatting ──────────────────────────────────────
    @staticmethod
    def _to_dicts(parts: List[Any], fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """零件列表转字典（简洁格式，省 Token）。"""
        attrs = ["part_number", "manufacturer", "manufacturer_zh",
                 "category", "category_zh", "description_zh",
                 "median_price_usd", "confidence_score"]
        result = []
        for part in parts:
            d: Dict[str, Any] = {}
            for a in attrs:
                v = getattr(part, a, None)
                if v is not None:
                    d[a] = v
            # 来源摘要
            if hasattr(part, "sources") and part.sources:
                d["prices"] = [
                    {"src": getattr(s, "source_name", ""), "$": getattr(s, "price_usd", None)}
                    for s in part.sources[:3]
                ]
            # 规格摘要
            if hasattr(part, "specifications") and part.specifications:
                specs = part.specifications
                d["specs"] = {k: v for k, v in specs.items() if v is not None}
            if fields:
                d = {k: v for k, v in d.items() if k in fields}
            result.append(d)
        return result

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        """发送 JSON 响应（紧凑格式 / compact separators）。"""
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in self._CORS_HEADERS:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


def run_server(host: str = "0.0.0.0", port: int = 8787) -> None:
    """启动 HTTP 服务器 / Start HTTP server."""
    server = ThreadingHTTPServer((host, port), UspiHandler)
    print(f"USPI HTTP API: http://{host}:{port}", file=sys.stderr)
    print("Endpoints: POST /lookup | POST /compare | POST /batch | GET /health", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
        server.shutdown()


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    run_server(port=port)


if __name__ == "__main__":
    main()
