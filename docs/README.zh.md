# USPI — Universal Server Parts Intelligence

> 零依赖 / 中英双语 / USD 统一价格 / SI 标准单位 / OCR 输入 / Excel 兼容导出

## 简介

USPI 是一个服务器零件智能查询系统，支持 OEM（Dell/HP/Lenovo/Supermicro）和 ODM（Foxconn/Quanta/Wistron 等 8 家）零件号识别、规格查询、价格对比和 Excel 导出。

## 核心特性

| 特性 | 说明 |
|---|---|
| 零 pip 依赖 | 仅 Python 3.10+ 标准库 |
| USD 统一 | 所有价格自动转换为美元 |
| SI 标准单位 | 容量→GB, 频率→GHz, 功率→W 等 11 维度 |
| 中英双语 | 所有输出同时支持中文和英文 |
| OCR 输入 | 支持拍照 → OCR → 查询全链路 |
| Excel 兼容 | CSV+BOM / Markdown 可粘贴表格 |
| Token 效率 | compact 格式，可选字段过滤 |
| 15 个适配器 | 4 OEM + 8 ODM + 3 Market |

## 快速开始

### 安装

```bash
git clone <repo-url>
cd uspi
python -c "import uspi; print(uspi.__version__)"
# 输出: 0.1.0
```

### 运行 MCP Server

```bash
python -m uspi.mcp.server
# Stdio JSON-RPC 2.0 模式
```

### 运行 HTTP Server

```bash
python -m uspi.api.http_server
# 默认端口 8000
```

## MCP Tool 使用说明

USPI 提供 3 个 MCP Tools：

### 1. uspi_lookup — 零件查询

```json
{
  "part_number": "0WX202",
  "output_format": "compact",
  "fields": ["part_number", "manufacturer_zh", "category_zh", "median_price_usd"]
}
```

支持参数：
- `part_number` (必填): 零件号，支持 OCR 脏文本
- `manufacturers`: 按厂商过滤
- `include_odm`: 是否包含 ODM 结果（默认 true）
- `output_format`: 输出格式 `compact|md|csv|json`
- `fields`: 选择字段减少 Token
- `max_sources`: 最大价格来源数（默认 3）

### 2. uspi_compare — 零件对比

```json
{
  "part_numbers": ["0WX202", "872736-001"],
  "output_format": "md"
}
```

### 3. uspi_export — 数据导出

```json
{
  "part_numbers": ["0WX202"],
  "format": "csv",
  "lang": "zh"
}
```

## 对话示例

### 示例 1: 基础查询
> **用户**: "查一下 0WX202"
> **Agent**: 返回 → 0WX202 | DELL | 内存 | $149.99

### 示例 2: OCR 输入
> **用户**: "照片标签是 0WX2O2"
> **Agent**: OCR 修复 → 0WX202 → 查询 → 结果

### 示例 3: Excel 导出
> **用户**: "导出 Excel 能打开的格式"
> **Agent**: 返回带 BOM 的 CSV

### 示例 4: 零件对比
> **用户**: "对比 0WX202 和 872736-001"
> **Agent**: 返回 Markdown 对比表

### 示例 5: ODM 查询
> **用户**: "FOX12B456 是哪个 OEM 的？"
> **Agent**: 返回 Foxconn → Dell 代工

### 示例 6: 批量查询
> **用户**: "查这批零件：0WX202, 872736-001, 01KN234"
> **Agent**: 批量返回结果

### 示例 7: 规格解读
> **用户**: "750W PSU 能支持 2 块 A100 吗？"
> **Agent**: 计算功耗 → 建议 1200W 电源

### 示例 8: Token 效率
> **用户**: "用最短格式"
> **Agent**: compact 格式：0WX202 | DELL | MEMORY | $150

### 示例 9: 字段过滤
> **用户**: "只要厂商和价格"
> **Agent**: 返回 {manufacturer_zh, median_price_usd}

### 示例 10: CSV 导出
> **用户**: "导出 CSV"
> **Agent**: 返回 UTF-8 BOM CSV

## Excel 导出工作流

1. 用户查询零件 → Agent 调用 `uspi_lookup`
2. Agent 获取结果 → 调用 `to_excel_pasteable()` 或 `to_csv()`
3. 用户收到 Markdown 表格 → 直接复制粘贴到 Excel
4. 或用户收到 CSV 文件 → Excel 直接打开（BOM 保障中文正常）

## OCR 输入工作流

1. 用户拍照/扫描 → 获得 OCR 文本
2. Agent 调用 `clean_ocr_text()` 清洗噪声
3. 调用 `extract_part_numbers()` 提取候选零件号
4. 对最佳候选调用 `uspi_lookup()` 查询
5. 返回结构化结果

## 输出格式层级

| 格式 | 用途 | Token 级别 |
|---|---|---|
| `compact` | 快速查询/对话 | 最低（每零件 ~50 tokens） |
| `md` | 人读/Excel 粘贴 | 中（每零件 ~150 tokens） |
| `csv` | 数据分析 | 低（无字段名重复） |
| `json` | 程序消费 | 高（完整字段） |

## 项目结构

```
uspi/
├── core/              # 核心引擎
│   ├── parser.py      # 零件号识别
│   ├── fetcher.py     # HTTP 抓取
│   ├── adapters/      # 15 个适配器
│   ├── normalizer.py  # 数据归一化
│   ├── comparator.py  # 对比引擎
│   ├── unit_converter.py  # 单位转换
│   ├── ocr_input.py   # OCR 预处理
│   └── exporter.py    # 多格式导出
├── mcp/server.py      # MCP JSON-RPC 服务
├── api/http_server.py # HTTP REST API
└── utils/             # 工具模块

docs/
├── README.zh.md       # 本文档
├── README.en.md       # English README
├── API_SPEC.zh.md     # API 规范（中文）
├── API_SPEC.en.md     # API Spec (English)
├── DIALOGUE_EXAMPLES.md   # 55 组对话示例
└── UNITS.md           # 单位标准化对照表

tests/                 # 120 个单元测试
```

## License

MIT License
