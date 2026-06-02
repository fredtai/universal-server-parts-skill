"""
MCP Stdio Server — JSON-RPC 2.0 / MCP 标准输入输出服务器
自研解析器，零依赖。仅处理 initialize, tools/list, tools/call。
Custom parser, zero deps. Handles initialize, tools/list, tools/call only.

Token 效率: 默认 compact 输出, 支持 fields 过滤, Tool description < 200 字符。
Token efficiency: default compact, fields filter, tool desc < 200 chars.
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any, Dict, List, Optional

# -- 工具定义 / Tool definitions (<200 char descriptions) -------------------

TOOLS = [
    {
        "name": "uspi_lookup",
        "description": "Query server part specs and USD pricing across OEM/ODM. Supports OCR input.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "part_number": {"type": "string", "description": "Part number (supports OCR dirty text)"},
                "manufacturers": {"type": "array", "items": {"type": "string"}},
                "include_odm": {"type": "boolean", "default": True},
                "output_format": {"type": "string", "enum": ["compact", "json", "md", "csv"], "default": "compact"},
                "fields": {"type": "array", "items": {"type": "string"}},
                "max_sources": {"type": "integer", "default": 3}
            },
            "required": ["part_number"]
        }
    },
    {
        "name": "uspi_compare",
        "description": "Compare multiple parts side by side. Excel-pasteable markdown table output.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "part_numbers": {"type": "array", "items": {"type": "string"}},
                "output_format": {"type": "string", "enum": ["md", "json", "csv", "compact"], "default": "md"}
            },
            "required": ["part_numbers"]
        }
    },
    {
        "name": "uspi_export",
        "description": "Export part data to CSV(Excel) or markdown table.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "part_numbers": {"type": "array", "items": {"type": "string"}},
                "format": {"type": "string", "enum": ["csv", "md", "json"], "default": "md"},
                "lang": {"type": "string", "enum": ["zh", "en"], "default": "zh"}
            },
            "required": ["part_numbers"]
        }
    }
]

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

# -- JSON-RPC 错误码 / Error codes -----------------------------------------

ERR_PARSE = -32700
ERR_INVALID_REQ = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_PARAMS = -32602
ERR_INTERNAL = -32603


class McpServer:
    """MCP JSON-RPC 2.0 Server (Stdio transport).

    从 stdin 读取 JSON-RPC 请求，处理后写入 stdout。
    Reads JSON-RPC from stdin, writes responses to stdout.
    """

    def __init__(self) -> None:
        self._running = True
        self._initialized = False
        self._adapters: Dict[str, Any] = {}

    def _init_adapters(self) -> Dict[str, Any]:
        """延迟初始化适配器实例 / Lazy-init adapter instances."""
        if self._adapters:
            return self._adapters
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
                self._adapters[name] = cls(fetcher, currency)
            except Exception:
                pass
        return self._adapters

    # -- 主循环 / Main loop ------------------------------------------------

    def run(self) -> None:
        """主循环：逐行读取 stdin 的 JSON-RPC 请求。/ Read JSON-RPC lines from stdin."""
        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                req = json.loads(line)
                resp = self._dispatch(req)
                if resp is not None:
                    self._write(resp)
            except json.JSONDecodeError as e:
                self._write(self._err(ERR_PARSE, f"JSON parse error / JSON 解析错误: {e}", None))
            except Exception as e:
                self._write(self._err(ERR_INTERNAL, f"Internal error / 内部错误: {e}", None))

    # -- 分发 / Dispatch ---------------------------------------------------

    def _dispatch(self, req: dict) -> Optional[dict]:
        """路由请求到对应 handler。/ Route request to handler."""
        if not isinstance(req, dict) or req.get("jsonrpc") != "2.0":
            return self._err(ERR_INVALID_REQ, "Invalid JSON-RPC 2.0 request / 无效请求", req.get("id") if isinstance(req, dict) else None)
        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})
        if not method:
            return self._err(ERR_INVALID_PARAMS, "Missing method / 缺少 method", req_id)
        try:
            if method == "initialize":
                return self._ok(self._handle_init(params), req_id)
            elif method == "tools/list":
                return self._ok(self._handle_tools_list(params), req_id)
            elif method == "tools/call":
                return self._ok(self._handle_tools_call(params), req_id)
            elif method == "notifications/initialized":
                self._initialized = True
                return None
            return self._err(ERR_METHOD_NOT_FOUND, f"Method not found / 方法未找到: {method}", req_id)
        except Exception as e:
            tb = traceback.format_exc()
            return self._err(ERR_INTERNAL, f"Handler error / 处理错误: {e}\n{tb}", req_id)

    # -- Handlers ----------------------------------------------------------

    def _handle_init(self, params: dict) -> dict:
        """返回 serverInfo + capabilities。/ Return server info and capabilities."""
        self._initialized = True
        return {
            "protocolVersion": params.get("protocolVersion", "2024-11-05"),
            "serverInfo": {"name": "uspi", "version": "0.1.0"},
            "capabilities": {"tools": {}}
        }

    def _handle_tools_list(self, params: dict) -> dict:
        """返回 TOOLS 列表。/ Return tools list."""
        return {"tools": TOOLS}

    def _handle_tools_call(self, params: dict) -> dict:
        """分发 tool 调用。/ Dispatch tool call."""
        name = params.get("name", "")
        args = params.get("arguments", {})
        adapters = self._init_adapters()
        if name == "uspi_lookup":
            text = self._do_lookup(args, adapters)
        elif name == "uspi_compare":
            text = self._do_compare(args, adapters)
        elif name == "uspi_export":
            text = self._do_export(args, adapters)
        else:
            raise ValueError(f"Unknown tool / 未知工具: {name}")
        return {"content": [{"type": "text", "text": text}], "isError": False}

    # -- Tool 实现 / Tool implementations ----------------------------------

    def _do_lookup(self, args: dict, adapters: Dict[str, Any]) -> str:
        """零件查询。/ Part lookup.

        1. OCR 清洗 / OCR clean
        2. 遍历适配器查询 / Query adapters
        3. 聚合导出 / Aggregate and export
        """
        pn = args.get("part_number", "")
        mfrs = args.get("manufacturers", [])
        include_odm = args.get("include_odm", True)
        fmt = args.get("output_format", "compact")
        fields = args.get("fields", None)
        max_src = args.get("max_sources", 3)
        lang = args.get("lang", "zh")
        if not pn:
            return "[Error / 错误] part_number required / 必须提供零件号"
        # OCR 清洗 / OCR cleaning
        cleaned = self._clean_pn(pn)
        # 查询适配器 / Query adapters
        parts: List[Any] = []
        for name, adapter in adapters.items():
            if mfrs and name not in mfrs:
                continue
            if not include_odm and name not in ("dell", "hp", "lenovo", "supermicro"):
                continue
            try:
                r = adapter.lookup(cleaned) if hasattr(adapter, "lookup") else None
                if r is not None:
                    if max_src > 0 and hasattr(r, "sources") and r.sources:
                        r.sources = r.sources[:max_src]
                    parts.append(r)
            except Exception:
                continue
        if not parts:
            return f"[Not Found / 未找到] {cleaned}\n请检查零件号 / Please verify part number."
        return self._export(parts, fmt, fields, lang)

    def _do_compare(self, args: dict, adapters: Dict[str, Any]) -> str:
        """零件对比。/ Part comparison."""
        pns = args.get("part_numbers", [])
        fmt = args.get("output_format", "md")
        if len(pns) < 2:
            return "[Error / 错误] Need >=2 part numbers / 至少需 2 个零件号"
        parts: List[Any] = []
        for pn in pns:
            pn = pn.strip()
            if not pn:
                continue
            cleaned = self._clean_pn(pn)
            for adapter in adapters.values():
                try:
                    r = adapter.lookup(cleaned) if hasattr(adapter, "lookup") else None
                    if r is not None:
                        parts.append(r)
                        break
                except Exception:
                    continue
        if len(parts) < 2:
            return f"[Error / 错误] Only found {len(parts)} part(s) / 仅找到 {len(parts)} 个零件"
        # 使用 Comparator / Use Comparator
        if Comparator is not None:
            try:
                comp = Comparator()
                result = comp.compare(parts)
                if fmt == "md":
                    return comp.to_markdown_matrix(result)
                elif fmt == "json":
                    return json.dumps(result, ensure_ascii=False, indent=None)
            except Exception:
                pass
        return self._export(parts, fmt if fmt != "md" else "md", None, "zh")

    def _do_export(self, args: dict, adapters: Dict[str, Any]) -> str:
        """数据导出。/ Data export."""
        pns = args.get("part_numbers", [])
        fmt = args.get("format", "md")
        lang = args.get("lang", "zh")
        if not pns:
            return "[Error / 错误] part_numbers required / 必须提供零件号列表"
        parts: List[Any] = []
        for pn in pns:
            pn = pn.strip()
            if not pn:
                continue
            cleaned = self._clean_pn(pn)
            for adapter in adapters.values():
                try:
                    r = adapter.lookup(cleaned) if hasattr(adapter, "lookup") else None
                    if r is not None:
                        parts.append(r)
                        break
                except Exception:
                    continue
        if not parts:
            return "[Not Found / 未找到] No data found / 未找到数据"
        return self._export(parts, fmt, None, lang)

    # -- 辅助 / Helpers ----------------------------------------------------

    @staticmethod
    def _clean_pn(pn: str) -> str:
        """清洗零件号（支持 OCR 脏文本）。/ Clean part number (OCR dirty text supported)."""
        if not pn or OcrInputCleaner is None:
            return pn
        try:
            cleaned = OcrInputCleaner.clean_ocr_text(pn) or pn
            extracted = OcrInputCleaner.extract_part_numbers(pn)
            if extracted:
                return extracted[0].get("cleaned", cleaned)
            return cleaned
        except Exception:
            return pn

    def _export(self, parts: List[Any], fmt: str, fields: Optional[List[str]], lang: str) -> str:
        """按格式导出零件列表。/ Export parts in specified format."""
        if Exporter is not None:
            try:
                exp = Exporter()
                if fmt == "compact":
                    return exp.to_compact_text(parts, lang=lang)
                elif fmt == "json":
                    return exp.to_json(parts, fields=fields)
                elif fmt == "md":
                    return exp.to_markdown(parts, lang=lang, fields=fields)
                elif fmt == "csv":
                    return exp.to_csv(parts, lang=lang)
            except Exception:
                pass
        return self._builtin_export(parts, fmt, lang)

    @staticmethod
    def _builtin_export(parts: List[Any], fmt: str, lang: str) -> str:
        """内建导出（降级）。/ Built-in export fallback."""
        lines: List[str] = []
        if fmt == "compact":
            for p in parts:
                pn = getattr(p, "part_number", "?")
                mfr = getattr(p, "manufacturer", "?")
                cat = getattr(p, "category_zh" if lang == "zh" else "category", "?")
                pr = getattr(p, "median_price_usd", None)
                cf = getattr(p, "confidence_score", 0.0)
                ps = f"${pr:.2f}" if pr else "N/A"
                lines.append(f"{pn} | {mfr} | {cat} | {ps} | conf:{cf:.2f}")
            return "\n".join(lines) if lines else "[No data / 无数据]"
        elif fmt == "csv":
            hdr = "\ufeff零件号,厂商,分类,美元价,可信度" if lang == "zh" else "\ufeffPartNumber,Mfr,Category,USD,Conf"
            lines.append(hdr)
            for p in parts:
                pn, mfr = getattr(p, "part_number", "?"), getattr(p, "manufacturer", "?")
                cat = getattr(p, "category_zh" if lang == "zh" else "category", "?")
                pr = getattr(p, "median_price_usd", None)
                cf = getattr(p, "confidence_score", 0.0)
                lines.append(f"{pn},{mfr},{cat},{pr if pr else ''},{cf:.2f}")
            return "\n".join(lines)
        elif fmt in ("md", "markdown"):
            if lang == "zh":
                lines.extend(["| 零件号 | 厂商 | 分类 | 美元价 | 可信度 |", "|--------|------|------|--------|--------|"])
            else:
                lines.extend(["| Part # | Mfr | Category | USD | Conf |", "|--------|-----|----------|-----|------|"])
            for p in parts:
                pn, mfr = getattr(p, "part_number", "?"), getattr(p, "manufacturer", "?")
                cat = getattr(p, "category_zh" if lang == "zh" else "category", "?")
                pr = getattr(p, "median_price_usd", None)
                cf = getattr(p, "confidence_score", 0.0)
                ps = f"${pr:.2f}" if pr else "N/A"
                lines.append(f"| {pn} | {mfr} | {cat} | {ps} | {cf:.2f} |")
            return "\n".join(lines)
        elif fmt == "json":
            result = []
            for p in parts:
                d = {a: getattr(p, a, None) for a in ["part_number", "manufacturer", "manufacturer_zh",
                     "category", "category_zh", "description_zh", "median_price_usd", "confidence_score"]}
                d = {k: v for k, v in d.items() if v is not None}
                if fields:
                    d = {k: v for k, v in d.items() if k in fields}
                result.append(d)
            return json.dumps(result, ensure_ascii=False, indent=None)
        return f"[Error / 错误] Unknown format / 未知格式: {fmt}"

    # -- JSON-RPC 响应构造 / Response builders -----------------------------

    def _write(self, resp: dict) -> None:
        """写入 stdout。/ Write to stdout."""
        try:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
        except Exception:
            pass

    @staticmethod
    def _ok(result: Any, req_id: Any) -> dict:
        """构造成功响应。/ Build success response."""
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    @staticmethod
    def _err(code: int, msg: str, req_id: Any) -> dict:
        """构造错误响应。/ Build error response."""
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": msg}}


# -- 入口 / Entry point ----------------------------------------------------

def main() -> None:
    """入口: python -m uspi.mcp.server / Entry point."""
    McpServer().run()


if __name__ == "__main__":
    main()
