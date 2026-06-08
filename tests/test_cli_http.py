"""
测试 CLI 和 HTTP API / Tests for CLI & HTTP API

替换原 test_mcp.py，覆盖 CLI 命令行工具和 HTTP REST API。
Replaces test_mcp.py, covers CLI tool and HTTP REST API.
"""

import json
import sys
import unittest
from io import StringIO

sys.path.insert(0, ".")

from uspi.cli import main as cli_main
from uspi.api.http_server import UspiHandler, _get_adapters, _clean_pn


class MockRequest:
    """Mock HTTP request for handler testing."""
    def __init__(self, path="/", body=None, method="GET"):
        self.path = path
        self.body = body or {}
        self.method = method
        self.headers = {"Content-Length": str(len(json.dumps(self.body).encode())) if body else "0"}
        self._body_bytes = json.dumps(self.body).encode() if body else b""
        self._pos = 0

    def read(self, n=-1):
        if n == -1:
            result = self._body_bytes[self._pos:]
            self._pos = len(self._body_bytes)
            return result
        result = self._body_bytes[self._pos:self._pos + n]
        self._pos += n
        return result


class MockHandler(UspiHandler):
    """Mock HTTP handler that captures output."""
    def __init__(self, request_body=None, path="/"):
        self.request = MockRequest(path, request_body)
        self._output = b""
        self._status = 200
        self._headers = []

    def send_response(self, code, message=None):
        self._status = code

    def send_header(self, keyword, value):
        self._headers.append((keyword, value))

    def end_headers(self):
        pass

    def rfile(self):
        return self.request

    @property
    def rfile(self):
        return self.request

    def wfile_write(self, data):
        self._output += data

    @property
    def wfile(self):
        class W:
            def __init__(self, handler):
                self.h = handler
            def write(self, data):
                self.h._output += data
        return W(self)

    def get_response(self):
        return json.loads(self._output.decode("utf-8"))


class TestCLI(unittest.TestCase):
    """CLI 工具测试 / CLI tool tests."""

    def _run_cli(self, args):
        """运行 CLI 并返回 (exit_code, stdout, stderr)."""
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout = StringIO()
        stderr = StringIO()
        sys.stdout = stdout
        sys.stderr = stderr
        try:
            code = cli_main(args)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 0
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_health(self):
        """health 子命令."""
        code, out, err = self._run_cli(["health"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "ok")
        self.assertIn("adapters", data)

    def test_cli_lookup_dell(self):
        """lookup Dell 零件号."""
        code, out, err = self._run_cli(["--timeout", "1", "--workers", "1", "lookup", "0WX202"])
        self.assertEqual(code, 0)
        # compact format prints lines
        self.assertIn("0WX202", out)
        self.assertIn("戴尔", out)

    def test_cli_lookup_samsung(self):
        """lookup Samsung 零件号."""
        code, out, err = self._run_cli(["--timeout", "1", "--workers", "1", "lookup", "M393A8G40AB2-CWE", "--format", "json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["found"])
        self.assertIn("results", data)
        # Samsung should be in results
        mfrs = [r.get("manufacturer_zh", "") for r in data["results"]]
        self.assertTrue(any("三星" in m for m in mfrs))

    def test_cli_lookup_not_found(self):
        """lookup 不存在的零件号返回 1."""
        code, out, err = self._run_cli(["--timeout", "1", "--workers", "1", "lookup", "XXXXXXXX"])
        self.assertEqual(code, 1)

    def test_cli_compare(self):
        """compare 子命令."""
        code, out, err = self._run_cli(["--timeout", "1", "--workers", "1", "compare", "0WX202", "M393A8G40AB2-CWE"])
        self.assertEqual(code, 0)
        self.assertIn("0WX202", out)
        self.assertIn("M393A8G40AB2-CWE", out)

    def test_cli_batch(self):
        """batch 子命令."""
        # Use --workers 1 to avoid parallel overhead in tests
        code, out, err = self._run_cli(["--timeout", "1", "--workers", "1", "batch", "0WX202", "M393A8G40AB2-CWE"])
        self.assertEqual(code, 0)
        self.assertIn("0WX202", out)

    def test_cli_batch_json(self):
        """batch JSON 格式."""
        code, out, err = self._run_cli(["--timeout", "1", "--workers", "1", "batch", "0WX202", "--format", "json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIsInstance(data, list)


class TestHTTPAPI(unittest.TestCase):
    """HTTP API 测试 / HTTP API tests."""

    def test_clean_pn(self):
        """零件号清洗."""
        self.assertEqual(_clean_pn("0WX202"), "0WX202")
        self.assertEqual(_clean_pn(""), "")

    def test_handler_part_dict(self):
        """零件转字典."""
        from uspi.core.adapters.base import ServerPart, PriceSource
        p = ServerPart(
            part_number="0WX202", manufacturer="DELL", manufacturer_zh="戴尔",
            oem_brand=None, category="MEMORY", category_zh="内存",
            description="32GB", description_zh="32GB",
            specifications={"capacity": 32.0}, raw_specifications={},
            sources=[PriceSource("Test", "测试", 100.0, 100.0, "USD", "", True, "new", "2024-01-01T00:00:00Z", 0.8)],
            median_price_usd=100.0, price_range_usd=(100.0, 100.0),
            confidence_score=0.8, last_updated="2024-01-01T00:00:00Z",
        )
        d = UspiHandler._to_dicts([p])
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]["part_number"], "0WX202")
        self.assertEqual(d[0]["manufacturer_zh"], "戴尔")
        self.assertIn("prices", d[0])

    def test_adapter_init(self):
        """适配器延迟初始化."""
        adapters = _get_adapters()
        self.assertGreater(len(adapters), 0)
        self.assertIn("dell", adapters)
        self.assertIn("samsung", adapters)

    def test_cors_headers_defined(self):
        """CORS 头已定义."""
        self.assertTrue(len(UspiHandler._CORS_HEADERS) > 0)
        headers_dict = dict(UspiHandler._CORS_HEADERS)
        self.assertIn("Access-Control-Allow-Origin", headers_dict)
        self.assertEqual(headers_dict["Access-Control-Allow-Origin"], "*")


if __name__ == "__main__":
    unittest.main()
