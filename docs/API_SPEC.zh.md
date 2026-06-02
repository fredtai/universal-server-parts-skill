# USPI API 规范 / API Specification (中文)

## MCP Tool Schema

USPI MCP Server 提供 3 个 Tool，通过 JSON-RPC 2.0 over stdio 通信。

### Tool 1: uspi_lookup

**描述**: 查询服务器零件规格与美元价格，支持 OEM/ODM 厂商。

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "part_number": {
      "type": "string",
      "description": "零件号（支持 OCR 脏文本）"
    },
    "manufacturers": {
      "type": "array",
      "items": {"type": "string"},
      "description": "按厂商过滤"
    },
    "include_odm": {
      "type": "boolean",
      "default": true,
      "description": "包含 ODM 结果"
    },
    "output_format": {
      "type": "string",
      "enum": ["json", "md", "csv", "compact"],
      "default": "compact",
      "description": "输出格式"
    },
    "fields": {
      "type": "array",
      "items": {"type": "string"},
      "description": "选择字段以减少 Token"
    },
    "max_sources": {
      "type": "integer",
      "default": 3,
      "description": "最大价格来源数"
    }
  },
  "required": ["part_number"]
}
```

### Tool 2: uspi_compare

**描述**: 并排对比多个服务器零件，输出 Markdown 对比表格。

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "part_numbers": {
      "type": "array",
      "items": {"type": "string"},
      "description": "零件号列表"
    },
    "output_format": {
      "type": "string",
      "enum": ["json", "md", "csv"],
      "default": "md",
      "description": "输出格式"
    }
  },
  "required": ["part_numbers"]
}
```

### Tool 3: uspi_export

**描述**: 导出零件数据为可粘贴 Excel 的 Markdown 或 CSV。

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "part_numbers": {
      "type": "array",
      "items": {"type": "string"},
      "description": "要导出的零件号列表"
    },
    "format": {
      "type": "string",
      "enum": ["csv", "md", "json"],
      "default": "md",
      "description": "导出格式"
    },
    "lang": {
      "type": "string",
      "enum": ["zh", "en"],
      "default": "zh",
      "description": "语言"
    }
  },
  "required": ["part_numbers"]
}
```

---

## HTTP API 端点

### POST /lookup — 零件查询

请求:
```json
{
  "part_number": "0WX202",
  "output_format": "compact",
  "fields": ["part_number", "manufacturer_zh", "median_price_usd"]
}
```

响应:
```json
{
  "part_number": "0WX202",
  "manufacturer": "DELL",
  "manufacturer_zh": "戴尔",
  "category": "MEMORY",
  "category_zh": "内存",
  "median_price_usd": 149.99,
  "confidence_score": 0.85
}
```

### POST /compare — 零件对比

请求:
```json
{
  "part_numbers": ["0WX202", "872736-001"],
  "output_format": "md"
}
```

响应:
```json
{
  "format": "markdown_table",
  "content": "| 零件号 | 厂商 | 分类 | 价格 |..."
}
```

### GET /health — 健康检查

响应:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "adapters": 15,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

## 数据模型

### ServerPart

| 字段 | 类型 | 说明 |
|---|---|---|
| `part_number` | str | 原始零件号 |
| `manufacturer` | str | 厂商代码 (DELL/FOXCONN/...) |
| `manufacturer_zh` | str | 厂商中文名 |
| `oem_brand` | Optional[str] | 对应 OEM 品牌 |
| `category` | str | 标准化分类 key |
| `category_zh` | str | 中文分类 |
| `description` | str | 英文描述 |
| `description_zh` | str | 中文描述 |
| `specifications` | Dict[str, Any] | 标准化规格 (SI units) |
| `raw_specifications` | Dict[str, str] | 原始规格 |
| `sources` | List[PriceSource] | 价格来源 |
| `median_price_usd` | Optional[float] | 中位数美元价 |
| `price_range_usd` | Optional[tuple] | (min, max) 价格区间 |
| `confidence_score` | float | 数据置信度 0.0-1.0 |
| `last_updated` | str | ISO 8601 UTC |
| `unit_system` | str | 单位体系 (默认 SI) |

### PriceSource

| 字段 | 类型 | 说明 |
|---|---|---|
| `source_name` | str | 来源名称（英文） |
| `source_name_zh` | str | 中文来源名 |
| `price_usd` | Optional[float] | 美元价 |
| `original_price` | Optional[float] | 原始价格 |
| `original_currency` | Optional[str] | 原始货币 |
| `url` | Optional[str] | 来源 URL |
| `in_stock` | Optional[bool] | 是否有货 |
| `condition` | Optional[str] | 新旧状态 |
| `last_seen` | str | ISO 8601 UTC |
| `reliability_score` | float | 来源可信度 0.0-1.0 |

---

## 输出格式说明

### compact 格式

```
0WX202 | DELL | MEMORY | $150 | conf:0.85
```

每行一个零件，仅核心字段，Token 消耗最低。

### md (Markdown) 格式

```markdown
| part_number | manufacturer | category | median_price_usd |
|---|---|---|---|
| 0WX202 | DELL | MEMORY | 149.99 |
```

可直接粘贴到 Excel / Google Sheets / GitHub。

### csv 格式

默认带 UTF-8 BOM (`\ufeff`)，Excel 直接打开中文不乱码。

### json 格式

完整字段，含嵌套的 specifications 和 sources 数组。

---

## 18 个分类 (CATEGORIES)

CPU, MEMORY, STORAGE_HDD, STORAGE_SSD, STORAGE_NVME, RAID_CONTROLLER, NIC, GPU, PSU, FAN, HEATSINK, MOTHERBOARD, BACKPLANE, CABLE, RAIL_KIT, BEZEL, BATTERY, OTHERS
