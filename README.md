# Universal Server Parts Intelligence (USPI)

**Identify, normalize, and compare server component specifications and pricing across OEMs (Dell, HP, Lenovo, etc.) and ODMs (Foxconn, Quanta, Wistron, Compal, Pegatron, Inventec, Flex, Jabil).**

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

### What is USPI?

USPI is a **zero-dependency** Python skill that helps AI agents (Kimi, Claude, GPT, Copilot, etc.) look up server hardware parts — from both OEM brands and ODM manufacturers — without relying on any paid API.

**Key capabilities:**
- **15 Adapters** — 4 OEM (Dell, HP, Lenovo, Supermicro) + 8 ODM (Foxconn, Quanta, Wistron...) + 3 market (eBay, Amazon, AliExpress)
- **OCR Input** — Feed dirty text from photos/scanners; USPI cleans and extracts part numbers automatically
- **Excel Export** — Copy-paste markdown tables or download CSV with UTF-8 BOM
- **Dual Protocol** — MCP (stdio) + HTTP REST API
- **Zero pip dependencies** — Python 3.10+ standard library only
- **Bilingual** — All outputs include both English and Chinese

### Quick Start

```bash
# Clone
git clone https://github.com/fredtai/universal-server-parts-skill.git
cd universal-server-parts-skill

# Verify
python -c "import uspi; print(uspi.__version__)"

# Run MCP Server (stdio mode — for Kimi/Claude Desktop)
python -m uspi.mcp.server

# Run HTTP API Server (port 8787)
python -m uspi.api.http_server 8787
```

### Agent Integration Examples

#### MCP (Model Context Protocol)

Add to your agent's MCP config:

```json
{
  "mcpServers": {
    "uspi": {
      "command": "python",
      "args": ["-m", "uspi.mcp.server"]
    }
  }
}
```

Available tools:

| Tool | Description | Example Query |
|------|-------------|---------------|
| `uspi_lookup` | Query part specs & USD pricing | "What's the spec of 0WX202?" |
| `uspi_compare` | Compare multiple parts side-by-side | "Compare 0WX202 vs SNK-P0070APS4" |
| `uspi_export` | Export to Excel-ready markdown/CSV | "Export results to Excel format" |

#### HTTP REST API

```bash
# Health check
curl http://localhost:8787/health
# → {"status": "ok", "version": "0.1.0", "adapters": 15}

# Look up a part
curl -X POST http://localhost:8787/lookup \
  -H "Content-Type: application/json" \
  -d '{"part_number": "0WX202", "format": "md"}'

# Compare multiple parts
curl -X POST http://localhost:8787/compare \
  -H "Content-Type: application/json" \
  -d '{"part_numbers": ["0WX202", "872736-001"], "format": "md"}'
```

### OCR Workflow

```
User takes photo → OCR text: "FOX12B456 from label"
                              ↓
                    OcrInputCleaner.extract_part_numbers()
                    → [{"cleaned": "FOX12B456", "confidence": 0.9}]
                              ↓
                    PartParser.parse("FOX12B456")
                    → Foxconn (鸿海/富士康), category=MEMORY
                              ↓
                    Return specs + pricing in USD
```

### Excel Export Workflow

**Option A — Copy-Paste Markdown Table:**
```
Agent returns markdown table → User copies → Pastes into Excel/Google Sheets
```

**Option B — CSV Download:**
```bash
curl -X POST http://localhost:8787/lookup \
  -d '{"part_number": "0WX202", "format": "csv"}' \
  > result.csv
# Open in Excel directly — Chinese characters display correctly (UTF-8 BOM)
```

### Supported Vendors

**OEMs:** Dell, HP/HPE, Lenovo, Supermicro

**ODMs:** Foxconn (鸿海/富士康), Quanta (广达), Wistron (纬创), Compal (仁宝), Pegatron (和硕), Inventec (英业达), Flex (伟创力), Jabil (捷普)

**Market:** eBay, Amazon, AliExpress

### Architecture

```
OCR Input → PartParser (OEM/ODM识别) → AdapterRegistry (15 adapters)
                                              ↓
                              Normalizer (SI units + USD pricing)
                                              ↓
                              Exporter (JSON / Markdown / CSV / Compact)
                                              ↓
                              MCP Server ←→ HTTP API
```

### Running Tests

```bash
python -m unittest discover -s tests -v
```

---

<a name="中文"></a>
## 中文

### USPI 是什么？

USPI（Universal Server Parts Intelligence）是一个**零第三方依赖**的 Python Skill，让 AI Agent（Kimi、Claude、GPT、Copilot 等）能够查询服务器硬件零件的规格与价格，覆盖 OEM 品牌厂商和 ODM 代工厂商，**完全基于免费公开数据源**。

**核心能力：**
- **15 个数据源适配器** — 4 个 OEM + 8 个 ODM + 3 个公开市场
- **OCR 输入支持** — 直接输入拍照/扫描的识别结果，自动清洗提取零件号
- **Excel 导出** — Markdown 表格复制粘贴 或 CSV 带 BOM 直接打开
- **双协议接口** — MCP (stdio) + HTTP REST API
- **零 pip 依赖** — 仅 Python 3.10+ 标准库
- **中英双语** — 所有输出同时包含中英文

### 快速开始

```bash
# 克隆仓库
git clone https://github.com/fredtai/universal-server-parts-skill.git
cd universal-server-parts-skill

# 验证安装
python -c "import uspi; print(uspi.__version__)"

# 启动 MCP Server（stdio 模式，供 Kimi/Claude Desktop 使用）
python -m uspi.mcp.server

# 启动 HTTP API Server（端口 8787）
python -m uspi.api.http_server 8787
```

### Agent 调用示例

#### MCP (Model Context Protocol) 接入

在 Agent 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "uspi": {
      "command": "python",
      "args": ["-m", "uspi.mcp.server"]
    }
  }
}
```

提供的 3 个 Tools：

| Tool | 功能 | 示例对话 |
|------|------|---------|
| `uspi_lookup` | 查询零件规格与美元价格 | "帮我查一下 0WX202" |
| `uspi_compare` | 并排对比多个零件 | "对比 0WX202 和 SNK-P0070APS4" |
| `uspi_export` | 导出为 Excel 兼容格式 | "导出成 Excel 能打开的格式" |

#### 用户可问的典型问题

- **"查一下 Dell 0WX202 的规格和价格"**
  - Agent → `uspi_lookup(part_number="0WX202")` → 返回规格 + 美元价格区间

- **"我拍了张照片，OCR 识别出 FOX12B456，帮我查一下"**
  - Agent → `uspi_lookup(part_number="FOX12B456")` → OCR 自动清洗 → 识别为 Foxconn 零件

- **"对比这三个内存条哪个更便宜"**
  - Agent → `uspi_compare(part_numbers=["0WX202", "872736-001", "01KN234"], format="md")` → Markdown 对比表格

- **"把结果导出成 Excel"**
  - Agent → `uspi_export(part_numbers=["0WX202"], format="csv")` → CSV 文件

#### HTTP REST API

```bash
# 健康检查
curl http://localhost:8787/health
# → {"status": "ok", "version": "0.1.0", "adapters": 15}

# 查询零件
curl -X POST http://localhost:8787/lookup \
  -H "Content-Type: application/json" \
  -d '{"part_number": "0WX202", "format": "md"}'

# 对比多个零件
curl -X POST http://localhost:8787/compare \
  -H "Content-Type: application/json" \
  -d '{"part_numbers": ["0WX202", "872736-001"], "format": "md"}'
```

### OCR 工作流

```
用户拍照 → OCR 识别: "标签上写着 FOX12B456"
                    ↓
        OcrInputCleaner.extract_part_numbers()
        → [{"cleaned": "FOX12B456", "confidence": 0.9}]
                    ↓
        PartParser.parse("FOX12B456")
        → Foxconn (鸿海/富士康), category=MEMORY
                    ↓
        返回规格 + 美元价格
```

### Excel 导出工作流

**方式 A — 复制粘贴 Markdown 表格：**
```
Agent 返回 Markdown 表格 → 用户复制 → 粘贴到 Excel/WPS/Google Sheets
```

**方式 B — CSV 文件下载：**
```bash
curl -X POST http://localhost:8787/lookup \
  -d '{"part_number": "0WX202", "format": "csv"}' \
  > result.csv
# 直接用 Excel 打开，中文正常显示（UTF-8 BOM）
```

### 支持的厂商

**OEM 品牌厂商：** Dell（戴尔）、HP/HPE（惠普/慧与）、Lenovo（联想）、Supermicro（超微）

**ODM 代工厂商：** Foxconn（鸿海/富士康）、Quanta（广达）、Wistron（纬创）、Compal（仁宝）、Pegatron（和硕）、Inventec（英业达）、Flex（伟创力）、Jabil（捷普）

**公开市场：** eBay、Amazon（亚马逊）、AliExpress（全球速卖通）

### 技术架构

```
OCR 输入 → PartParser（OEM/ODM 识别） → AdapterRegistry（15 个适配器）
                                                   ↓
                                   Normalizer（SI 单位 + USD 定价）
                                                   ↓
                                   Exporter（JSON / Markdown / CSV / 紧凑文本）
                                                   ↓
                                   MCP Server ←→ HTTP API
```

### Token 效率设计

| 输出格式 | 每零件 Token 数 | 适用场景 |
|---------|----------------|---------|
| `compact` | ~50 | 快速查询、对话 |
| `md` | ~150 | 人读、粘贴到 Excel |
| `csv` | ~80 | 数据分析 |
| `json` | ~300 | 程序消费 |

```
Agent: "用最少的字告诉我价格"
→ uspi_lookup(part_number="0WX202", output_format="compact", 
              fields=["part_number", "manufacturer_zh", "median_price_usd"])
→ 仅 4 个字段，Token 消耗最小化
```

### 运行测试

```bash
python -m unittest discover -s tests -v
```

### 技术栈

- **语言：** Python 3.10+（零 pip 依赖，仅标准库）
- **缓存：** SQLite（TTL + SHA256 Key）
- **汇率：** ECB XML + floatrates.com 双源，USD 基准
- **单位：** SI/IEC 标准（11 维度全覆盖）
- **日志：** 四级分级（ERROR/WARN/INFO/DEBUG）
- **CI/CD：** GitHub Actions（Python 3.10/3.11/3.12/3.13 矩阵测试）

### 许可证

MIT License — 自由使用、修改、分发。

---

**Made by fredtai**
