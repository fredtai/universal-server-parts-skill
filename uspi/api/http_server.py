"""
HTTP REST API Server / HTTP REST API 服务器
基于 http.server.ThreadingHTTPServer

端点 / Endpoints:
- POST /lookup  -> Part lookup / 零件查询
- POST /compare -> Part comparison / 零件对比
- GET  /health  -> Health check / 健康检查
默认端口 / Default port: 8787
"""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# -- 核心模块导入（优雅降级）/ Core imports (graceful fallback) --------------

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
    from uspi.core.fetcher import Fetcher
except ImportError:
    Fetcher = None  # type: ignore[misc,assignment]
try:
    from uspi.utils.currency import CurrencyConverter
except ImportError:
    CurrencyConverter = None  # type: ignore[misc,assignment]

# -- 线程安全全局状态 / Thread-safe global state ----------------------------

_lock = threading.Lock()
_adapters: Dict[str, Any] = {}
_adapters_ready = False


def _get_adapters() -> Dict[str, Any]:
    """延迟初始化适配器 / Lazy-init adapters (thread-safe)."""
    global _adapters_ready
    with _lock:
        if _adapters_ready:
            return _adapters
        fetcher = None
        currency = None
        if Fetcher is not None:
            try:
                fetcher = Fetcher()
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
    """清洗零件号（支持 OCR）/ Clean part number (OCR supported)."""
    if not pn or OcrInputCleaner is None:
        return pn
    try:
        c = OcrInputCleaner.clean_ocr_text(pn) or pn
        ext = OcrInputCleaner.extract_part_numbers(pn)
        return ext[0].get("cleaned", c) if ext else c
    except Exception:
        return pn


class UspiHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器 / HTTP request handler."""

    def do_POST(self) -> None:  # noqa: N802
        """处理 POST / Handle POST."""
        path = urlparse(self.path).path.rstrip("/") or "/"
        body = self._read_body()
        if body is None:
            self._send_json({"error": "Invalid JSON / 无效 JSON", "code": 400}, 400)
            return
        try:
            if path == "/lookup":
                self._send_json(self._handle_lookup(body))
            elif path == "/compare":
                self._send_json(self._handle_compare(body))
            else:
                self._send_json({"error": f"Not found / 未找到: {path}", "code": 404}, 404)
        except Exception as e:
            self._send_json({"error": f"Handler error / 处理错误: {e}", "code": 500}, 500)

    def do_GET(self) -> None:  # noqa: N802
        """处理 GET / Handle GET."""
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/health":
            adapters = _get_adapters()
            self._send_json({"status": "ok", "version": "0.1.0", "unit_system": "SI", "adapters": len(adapters)})
        else:
            self._send_json({"error": f"Not found / 未找到: {path}", "code": 404}, 404)

    def _read_body(self) -> Optional[Dict[str, Any]]:
        """读取请求体 / Read request body."""
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))  # type: ignore[no-any-return]
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _handle_lookup(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """零件查询 / Part lookup."""
        pn = body.get("part_number", "")
        fmt = body.get("format", "compact")
        lang = body.get("lang", "zh")
        fields = body.get("fields", None)
        max_src = body.get("max_sources", 3)
        if not pn:
            return {"error": "part_number required / 必须提供零件号", "code": 400}
        adapters = _get_adapters()
        cleaned = _clean_pn(pn)
        parts: List[Any] = []
        for adapter in adapters.values():
            try:
                r = adapter.lookup(cleaned) if hasattr(adapter, "lookup") else None
                if r is not None:
                    if max_src > 0 and hasattr(r, "sources") and r.sources:
                        r.sources = r.sources[:max_src]
                    parts.append(r)
            except Exception:
                continue
        if not parts:
            return {"part_number": cleaned, "found": False, "message": "No results / 未找到结果"}
        return {"part_number": cleaned, "found": True, "count": len(parts),
                "results": self._fmt_parts(parts, fmt, fields, lang)}

    def _handle_compare(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """零件对比 / Part comparison."""
        pns = body.get("part_numbers", [])
        fmt = body.get("format", "md")
        lang = body.get("lang", "zh")
        if len(pns) < 2:
            return {"error": "Need >=2 part numbers / 至少需 2 个零件号", "code": 400}
        adapters = _get_adapters()
        found: List[Any] = []
        not_found: List[str] = []
        for pn in pns:
            pn = pn.strip()
            if not pn:
                continue
            r = None
            for a in adapters.values():
                try:
                    r = a.lookup(_clean_pn(pn)) if hasattr(a, "lookup") else None
                    if r:
                        break
                except Exception:
                    continue
            if r:
                found.append(r)
            else:
                not_found.append(pn)
        if len(found) < 2:
            return {"error": f"Only found {len(found)} part(s) / 仅找到 {len(found)} 个", "not_found": not_found, "code": 404}
        if Comparator is not None:
            try:
                comp = Comparator()
                cmp = comp.compare(found)
                if fmt == "md":
                    return {"format": "md", "table": comp.to_markdown_matrix(cmp, lang=lang),
                            "found": len(found), "not_found": not_found}
                return {"format": fmt, "comparison": cmp, "found": len(found), "not_found": not_found}
            except Exception:
                pass
        return {"format": fmt, "parts": self._fmt_parts(found, fmt, None, lang), "not_found": not_found}

    def _fmt_parts(self, parts: List[Any], fmt: str, fields: Optional[List[str]], lang: str) -> Any:
        """格式化零件列表 / Format parts list."""
        if Exporter is not None:
            try:
                exp = Exporter()
                if fmt == "compact":
                    return {"text": exp.to_compact_text(parts, lang=lang)}
                elif fmt == "md":
                    return {"markdown": exp.to_markdown(parts, lang=lang, fields=fields)}
                elif fmt == "csv":
                    return {"csv": exp.to_csv(parts, lang=lang)}
                elif fmt == "json":
                    return {"json": exp.to_json(parts, fields=fields)}
            except Exception:
                pass
        # 内建降级 / Built-in fallback
        return [self._part_dict(p, fields) for p in parts]

    @staticmethod
    def _part_dict(part: Any, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """零件转字典 / Part to dict."""
        attrs = ["part_number", "manufacturer", "manufacturer_zh", "category", "category_zh",
                 "description_zh", "median_price_usd", "price_range_usd", "confidence_score", "unit_system"]
        d = {a: getattr(part, a, None) for a in attrs}
        d = {k: v for k, v in d.items() if v is not None}
        if hasattr(part, "sources") and part.sources:
            d["sources"] = [{"name": getattr(s, "source_name", ""), "price_usd": getattr(s, "price_usd", None),
                             "in_stock": getattr(s, "in_stock", None)} for s in part.sources]
        if fields:
            d = {k: v for k, v in d.items() if k in fields}
        return d

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        """发送 JSON 响应 / Send JSON response."""
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """抑制日志 / Suppress logs."""
        pass


def run_server(host: str = "0.0.0.0", port: int = 8787) -> None:
    """启动服务器 / Start server."""
    server = ThreadingHTTPServer((host, port), UspiHandler)
    print(f"USPI HTTP API on / 服务地址: http://{host}:{port}", file=sys.stderr)
    print("Endpoints / 端点: POST /lookup, POST /compare, GET /health", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutdown / 关闭...", file=sys.stderr)
        server.shutdown()


def main() -> None:
    """入口 / Entry point."""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    run_server(port=port)


if __name__ == "__main__":
    main()
