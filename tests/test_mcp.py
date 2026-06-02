"""
tests/test_mcp.py

MCP Server unit tests / MCP 服务器单元测试.

Coverage: JSON-RPC initialize, tools/list, tools/call uspi_lookup,
error handling. Zero external dependencies.
"""

import json
import unittest

from uspi.mcp.server import MCPServer


class TestMCPInitialize(unittest.TestCase):
    """Test MCP initialization / 测试 MCP 初始化."""

    def setUp(self) -> None:
        self.server = MCPServer()

    def test_initialize(self) -> None:
        """initialize returns protocol info / 初始化返回协议信息."""
        req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        resp = self.server.handle(req)
        self.assertIsNotNone(resp)
        data = json.loads(resp)
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["result"]["serverInfo"]["name"], "uspi")
        self.assertEqual(data["result"]["serverInfo"]["version"], "0.1.0")

    def test_initialized_notification(self) -> None:
        """notifications/initialized returns None / 初始化通知返回 None."""
        req = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        resp = self.server.handle(req)
        self.assertIsNone(resp)


class TestMCPToolsList(unittest.TestCase):
    """Test tools/list / 测试工具列表."""

    def setUp(self) -> None:
        self.server = MCPServer()
        # Initialize first / 先初始化
        init_req = json.dumps({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
        self.server.handle(init_req)

    def test_tools_list_returns_three(self) -> None:
        """tools/list returns 3 tools / 返回 3 个工具."""
        req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        resp = self.server.handle(req)
        self.assertIsNotNone(resp)
        data = json.loads(resp)
        self.assertEqual(data["id"], 2)
        tools = data["result"]["tools"]
        self.assertEqual(len(tools), 3)
        names = [t["name"] for t in tools]
        self.assertIn("uspi_lookup", names)
        self.assertIn("uspi_compare", names)
        self.assertIn("uspi_export", names)

    def test_tools_list_before_init_fails(self) -> None:
        """tools/list before initialize fails / 未初始化时失败."""
        fresh_server = MCPServer()
        req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        resp = fresh_server.handle(req)
        data = json.loads(resp)
        self.assertIn("error", data)


class TestMCPToolCall(unittest.TestCase):
    """Test tools/call / 测试工具调用."""

    def setUp(self) -> None:
        self.server = MCPServer()
        init_req = json.dumps({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
        self.server.handle(init_req)

    def test_lookup_uspi_lookup(self) -> None:
        """uspi_lookup returns non-empty result / 返回非空结果."""
        req = json.dumps({
            "jsonrpc": "2.0", "id": 3,
            "method": "tools/call",
            "params": {
                "name": "uspi_lookup",
                "arguments": {"part_number": "0WX202", "output_format": "compact"},
            },
        })
        resp = self.server.handle(req)
        self.assertIsNotNone(resp)
        data = json.loads(resp)
        self.assertIn("result", data)
        content = data["result"]["content"]
        self.assertTrue(len(content) > 0)
        self.assertEqual(content[0]["part_number"], "0WX202")

    def test_lookup_unknown_tool(self) -> None:
        """Unknown tool returns error / 未知工具返回错误."""
        req = json.dumps({
            "jsonrpc": "2.0", "id": 4,
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
        })
        resp = self.server.handle(req)
        data = json.loads(resp)
        self.assertIn("error", data)

    def test_compare_tool(self) -> None:
        """uspi_compare returns result / uspi_compare 返回结果."""
        req = json.dumps({
            "jsonrpc": "2.0", "id": 5,
            "method": "tools/call",
            "params": {
                "name": "uspi_compare",
                "arguments": {"part_numbers": ["0WX202", "872736-001"]},
            },
        })
        resp = self.server.handle(req)
        data = json.loads(resp)
        self.assertIn("result", data)
        self.assertIn("0WX202", data["result"]["content"][0]["compared"])

    def test_export_tool(self) -> None:
        """uspi_export returns result / uspi_export 返回结果."""
        req = json.dumps({
            "jsonrpc": "2.0", "id": 6,
            "method": "tools/call",
            "params": {
                "name": "uspi_export",
                "arguments": {"part_numbers": ["0WX202"], "format": "csv"},
            },
        })
        resp = self.server.handle(req)
        data = json.loads(resp)
        self.assertIn("result", data)
        self.assertEqual(data["result"]["content"][0]["format"], "csv")


class TestMCPErrorHandling(unittest.TestCase):
    """Test MCP error handling / 测试 MCP 错误处理."""

    def test_parse_error(self) -> None:
        """Invalid JSON returns parse error / 无效 JSON 返回解析错误."""
        server = MCPServer()
        resp = server.handle("not valid json")
        data = json.loads(resp)
        self.assertEqual(data["error"]["code"], -32700)

    def test_method_not_found(self) -> None:
        """Unknown method returns error / 未知方法返回错误."""
        server = MCPServer()
        init_req = json.dumps({"jsonrpc": "2.0", "id": 0, "method": "initialize"})
        server.handle(init_req)
        req = json.dumps({"jsonrpc": "2.0", "id": 7, "method": "unknown/method"})
        resp = server.handle(req)
        data = json.loads(resp)
        self.assertEqual(data["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
