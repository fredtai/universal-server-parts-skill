# USPI API Specification (English)

## MCP Tool Schema

The USPI MCP Server provides 3 Tools via JSON-RPC 2.0 over stdio.

### Tool 1: uspi_lookup

**Description**: Query server part specs and USD pricing across OEM/ODM vendors.

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "part_number": {
      "type": "string",
      "description": "Part number (supports OCR dirty text)"
    },
    "manufacturers": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Filter by vendor"
    },
    "include_odm": {
      "type": "boolean",
      "default": true,
      "description": "Include ODM results"
    },
    "output_format": {
      "type": "string",
      "enum": ["json", "md", "csv", "compact"],
      "default": "compact",
      "description": "Output format"
    },
    "fields": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Select fields to reduce tokens"
    },
    "max_sources": {
      "type": "integer",
      "default": 3,
      "description": "Max price sources"
    }
  },
  "required": ["part_number"]
}
```

### Tool 2: uspi_compare

**Description**: Compare multiple server parts side by side.

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "part_numbers": {
      "type": "array",
      "items": {"type": "string"},
      "description": "List of part numbers"
    },
    "output_format": {
      "type": "string",
      "enum": ["json", "md", "csv"],
      "default": "md",
      "description": "Output format"
    }
  },
  "required": ["part_numbers"]
}
```

### Tool 3: uspi_export

**Description**: Export part data to Excel-pasteable Markdown or CSV.

**inputSchema**:
```json
{
  "type": "object",
  "properties": {
    "part_numbers": {
      "type": "array",
      "items": {"type": "string"},
      "description": "List of part numbers to export"
    },
    "format": {
      "type": "string",
      "enum": ["csv", "md", "json"],
      "default": "md",
      "description": "Export format"
    },
    "lang": {
      "type": "string",
      "enum": ["zh", "en"],
      "default": "en",
      "description": "Language"
    }
  },
  "required": ["part_numbers"]
}
```

---

## HTTP API Endpoints

### POST /lookup — Part Lookup

Request:
```json
{
  "part_number": "0WX202",
  "output_format": "compact",
  "fields": ["part_number", "manufacturer", "median_price_usd"]
}
```

Response:
```json
{
  "part_number": "0WX202",
  "manufacturer": "DELL",
  "category": "MEMORY",
  "median_price_usd": 149.99,
  "confidence_score": 0.85
}
```

### POST /compare — Part Comparison

Request:
```json
{
  "part_numbers": ["0WX202", "872736-001"],
  "output_format": "md"
}
```

Response:
```json
{
  "format": "markdown_table",
  "content": "| Part Number | Manufacturer | Category | Price |..."
}
```

### GET /health — Health Check

Response:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "adapters": 15,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

## Data Models

### ServerPart

| Field | Type | Description |
|---|---|---|
| `part_number` | str | Original part number |
| `manufacturer` | str | Manufacturer code (DELL/FOXCONN/...) |
| `manufacturer_zh` | str | Manufacturer Chinese name |
| `oem_brand` | Optional[str] | Associated OEM brand |
| `category` | str | Standardized category key |
| `category_zh` | str | Chinese category name |
| `description` | str | English description |
| `description_zh` | str | Chinese description |
| `specifications` | Dict[str, Any] | Normalized specs (SI units) |
| `raw_specifications` | Dict[str, str] | Raw specifications |
| `sources` | List[PriceSource] | Price sources |
| `median_price_usd` | Optional[float] | Median price in USD |
| `price_range_usd` | Optional[tuple] | (min, max) price range |
| `confidence_score` | float | Data confidence 0.0-1.0 |
| `last_updated` | str | ISO 8601 UTC |
| `unit_system` | str | Unit system (default SI) |

### PriceSource

| Field | Type | Description |
|---|---|---|
| `source_name` | str | Source name (English) |
| `source_name_zh` | str | Chinese source name |
| `price_usd` | Optional[float] | Price in USD |
| `original_price` | Optional[float] | Original price |
| `original_currency` | Optional[str] | Original currency code |
| `url` | Optional[str] | Source URL |
| `in_stock` | Optional[bool] | In stock flag |
| `condition` | Optional[str] | new/refurbished/used |
| `last_seen` | str | ISO 8601 UTC |
| `reliability_score` | float | Source reliability 0.0-1.0 |

---

## Output Format Reference

### compact format

```
0WX202 | DELL | MEMORY | $150 | conf:0.85
```

One line per part, core fields only. Minimal token consumption.

### md (Markdown) format

```markdown
| part_number | manufacturer | category | median_price_usd |
|---|---|---|---|
| 0WX202 | DELL | MEMORY | 149.99 |
```

Pasteable into Excel / Google Sheets / GitHub.

### csv format

UTF-8 BOM (`\ufeff`) by default. Excel opens with correct Chinese characters.

### json format

Full fields with nested specifications and sources arrays.

---

## 18 Categories (CATEGORIES)

CPU, MEMORY, STORAGE_HDD, STORAGE_SSD, STORAGE_NVME, RAID_CONTROLLER, NIC, GPU, PSU, FAN, HEATSINK, MOTHERBOARD, BACKPLANE, CABLE, RAIL_KIT, BEZEL, BATTERY, OTHERS
