"""
测试 MCP Server / Tests for MCP Server

测试 JSON-RPC 2.0 接口：initialize, tools/list, tools/call
"""
import unittest
import sys
sys.path.insert(0, '.')

from uspi.mcp.server import McpServer, TOOLS


class TestMcpServer(unittest.TestCase):
    """MCP Server 单元测试"""

    def setUp(self):
        self.server = McpServer()
        # Mock adapters to avoid network calls during tests
        self.server._adapters = {
            "mock": type('MockAd', (), {
                'lookup': lambda self, x: None,
                'name': 'mock'
            })()
        }
        self.server._adapters_initialized = True

    def test_dispatch_initialize(self):
        """Test initialize returns server info"""
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = self.server._dispatch(req)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 1)
        self.assertIn("result", resp)

    def test_dispatch_tools_list(self):
        """Test tools/list returns 3 tools"""
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = self.server._dispatch(req)
        self.assertIn("result", resp)
        tools = resp["result"]["tools"]
        self.assertEqual(len(tools), 3)
        names = [t["name"] for t in tools]
        self.assertIn("uspi_lookup", names)
        self.assertIn("uspi_compare", names)
        self.assertIn("uspi_export", names)

    def test_dispatch_tools_call_lookup(self):
        """Test tools/call uspi_lookup returns result"""
        req = {
            "jsonrpc": "2.0", "id": 3,
            "method": "tools/call",
            "params": {
                "name": "uspi_lookup",
                "arguments": {"part_number": "0WX202"}
            }
        }
        resp = self.server._dispatch(req)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 3)
        self.assertIn("result", resp)
        # Result should contain content array with text
        content = resp["result"]["content"]
        self.assertIsInstance(content, list)

    def test_tools_schema_complete(self):
        """Test TOOLS schema has required fields"""
        for tool in TOOLS:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("inputSchema", tool)

    def test_clean_pn(self):
        """Test OCR part number cleaning"""
        result = McpServer._clean_pn("0WX2O2")
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main()
