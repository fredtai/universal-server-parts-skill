"""
uspi/mcp/server.py

MCP Stdio JSON-RPC 2.0 Server / MCP Stdio JSON-RPC 2.0 服务器.

提供 3 个 MCP Tools: uspi_lookup, uspi_compare, uspi_export.
Provides 3 MCP Tools: uspi_lookup, uspi_compare, uspi_export.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional

# MCP Tool 定义 / MCP Tool definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "uspi_lookup",
        "description": "Query server part specs and USD pricing across OEM/ODM vendors. Input: part number. Output: specs, price range, sources.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "part_number": {"type": "string", "description": "Part number (supports OCR dirty text)"},
                "manufacturers": {"type": "array", "items": {"type": "string"}, "description": "Filter by vendor"},
                "include_odm": {"type": "boolean", "default": True, "description": "Include ODM results"},
                "output_format": {"type": "string", "enum": ["json", "md", "csv", "compact"], "default": "compact", "description": "Output format"},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "Select fields to reduce tokens"},
                "max_sources": {"type": "integer", "default": 3, "description": "Max price sources"},
            },
            "required": ["part_number"],
        },
    },
    {
        "name": "uspi_compare",
        "description": "Compare multiple server parts side by side. Output: markdown comparison table.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "part_numbers": {"type": "array", "items": {"type": "string"}, "description": "List of part numbers"},
                "output_format": {"type": "string", "enum": ["json", "md", "csv"], "default": "md", "description": "Output format"},
            },
            "required": ["part_numbers"],
        },
    },
    {
        "name": "uspi_export",
        "description": "Export part data to Excel-pasteable markdown or CSV.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "part_numbers": {"type": "array", "items": {"type": "string"}, "description": "List of part numbers to export"},
                "format": {"type": "string", "enum": ["csv", "md", "json"], "default": "md", "description": "Export format"},
                "lang": {"type": "string", "enum": ["zh", "en"], "default": "zh", "description": "Language"},
            },
            "required": ["part_numbers"],
        },
    },
]


class MCPServer:
    """MCP JSON-RPC 2.0 Stdio 服务器 / MCP JSON-RPC 2.0 Stdio Server.

    通过标准输入输出处理 JSON-RPC 请求。
    Processes JSON-RPC requests over stdin/stdout.
    """

    def __init__(self) -> None:
        """初始化 MCP 服务器 / Initialize MCP server."""
        self._initialized = False
        self._tools = TOOLS

    def handle(self, request_json: str) -> Optional[str]:
        """处理单个 JSON-RPC 请求 / Handle a single JSON-RPC request.

        Args:
            request_json: JSON-RPC 请求字符串 / Request JSON string.

        Returns:
            JSON-RPC 响应字符串或 None / Response JSON string or None.
        """
        try:
            req = json.loads(request_json)
        except json.JSONDecodeError:
            return self._error_response(None, -32700, "Parse error")

        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        if method == "initialize":
            self._initialized = True
            return self._success_response(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "uspi", "version": "0.1.0"},
            })

        if method == "notifications/initialized":
            return None

        if method == "tools/list":
            if not self._initialized:
                return self._error_response(req_id, -32002, "Server not initialized")
            return self._success_response(req_id, {"tools": self._tools})

        if method == "tools/call":
            if not self._initialized:
                return self._error_response(req_id, -32002, "Server not initialized")
            return self._handle_tool_call(req_id, params)

        return self._error_response(req_id, -32601, f"Method not found: {method}")

    def _handle_tool_call(self, req_id: Any, params: Dict[str, Any]) -> str:
        """处理 Tool 调用 / Handle tool call.

        Args:
            req_id: 请求 ID / Request ID.
            params: 调用参数 / Call parameters.

        Returns:
            JSON-RPC 响应字符串 / Response JSON string.
        """
        name = params.get("name", "")
        arguments = params.get("arguments", {})

        if name == "uspi_lookup":
            return self._handle_lookup(req_id, arguments)
        elif name == "uspi_compare":
            return self._handle_compare(req_id, arguments)
        elif name == "uspi_export":
            return self._handle_export(req_id, arguments)

        return self._error_response(req_id, -32602, f"Unknown tool: {name}")

    def _handle_lookup(self, req_id: Any, args: Dict[str, Any]) -> str:
        """处理 uspi_lookup / Handle uspi_lookup.

        返回模拟结果 / Returns mock result for testing.
        """
        part_number = args.get("part_number", "")
        output_format = args.get("output_format", "compact")

        # 构建模拟结果 / Build mock result
        result = {
            "part_number": part_number,
            "manufacturer": "DELL",
            "manufacturer_zh": "戴尔",
            "category": "MEMORY",
            "category_zh": "内存",
            "description_zh": f"戴尔零件 {part_number}",
            "median_price_usd": 149.99,
            "confidence_score": 0.85,
            "sources": 2,
            "format": output_format,
        }
        return self._success_response(req_id, {"content": [result]})

    def _handle_compare(self, req_id: Any, args: Dict[str, Any]) -> str:
        """处理 uspi_compare / Handle uspi_compare."""
        part_numbers = args.get("part_numbers", [])
        return self._success_response(req_id, {
            "content": [{"compared": part_numbers, "format": "markdown_table"}],
        })

    def _handle_export(self, req_id: Any, args: Dict[str, Any]) -> str:
        """处理 uspi_export / Handle uspi_export."""
        part_numbers = args.get("part_numbers", [])
        fmt = args.get("format", "md")
        return self._success_response(req_id, {
            "content": [{"exported": part_numbers, "format": fmt}],
        })

    @staticmethod
    def _success_response(req_id: Any, result: Any) -> str:
        """构建成功响应 / Build success response."""
        resp: Dict[str, Any] = {"jsonrpc": "2.0", "result": result}
        if req_id is not None:
            resp["id"] = req_id
        return json.dumps(resp) + "\n"

    @staticmethod
    def _error_response(req_id: Any, code: int, message: str) -> str:
        """构建错误响应 / Build error response."""
        resp: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
        }
        if req_id is not None:
            resp["id"] = req_id
        return json.dumps(resp) + "\n"

    def run_stdio(self) -> None:
        """运行 stdio 服务器 / Run stdio server."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            response = self.handle(line)
            if response:
                sys.stdout.write(response)
                sys.stdout.flush()


def main() -> None:
    """MCP 服务器入口 / MCP server entry point."""
    server = MCPServer()
    server.run_stdio()


if __name__ == "__main__":
    main()
