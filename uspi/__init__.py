"""
USPI - Universal Server Parts Intelligence
通用服务器零件智能查询系统

任何 Agent 均可通过以下方式调用 / Any agent can use USPI via:

1. Python 模块导入 / Python module import (推荐 / Recommended):
   import uspi
   from uspi.core.parser import PartParser
   from uspi.core.adapters import ADAPTER_REGISTRY
   from uspi.api.http_server import run_server

2. HTTP REST API / HTTP REST API:
   python -m uspi.api.http_server 8787
   POST http://localhost:8787/lookup {"part_number": "0WX202"}

3. 命令行工具 / Command Line:
   python -m uspi.cli lookup 0WX202
   python -m uspi.cli batch PN1 PN2 PN3 --format json

4. 子进程调用 / Subprocess (任何语言):
   result = subprocess.run(["python", "-m", "uspi.cli", "lookup", "0WX202"],
                           capture_output=True, text=True)
   data = json.loads(result.stdout)

零依赖 / Zero dependencies. Python 3.10+.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
