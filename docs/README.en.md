# USPI — Universal Server Parts Intelligence

> Zero Dependencies / Bilingual EN-ZH / USD Unified Pricing / SI Standard Units / OCR Input / Excel-Compatible Export

## Introduction

USPI is a server parts intelligence query system supporting OEM (Dell/HP/Lenovo/Supermicro) and ODM (Foxconn/Quanta/Wistron and 5 more) part number recognition, specification lookup, price comparison, and Excel export.

## Core Features

| Feature | Description |
|---|---|
| Zero pip dependencies | Python 3.10+ standard library only |
| USD unified | All prices automatically converted to USD |
| SI standard units | Capacity→GB, Frequency→GHz, Power→W, 11 dimensions |
| Bilingual EN-ZH | All outputs support both English and Chinese |
| OCR input | Full pipeline: Photo → OCR → Query |
| Excel compatible | CSV+BOM / Markdown pasteable table |
| Token efficient | Compact format, optional field filtering |
| 15 adapters | 4 OEM + 8 ODM + 3 Market |

## Quick Start

### Install

```bash
git clone <repo-url>
cd uspi
python -c "import uspi; print(uspi.__version__)"
# Output: 0.1.0
```

### Run MCP Server

```bash
python -m uspi.mcp.server
# Stdio JSON-RPC 2.0 mode
```

### Run HTTP Server

```bash
python -m uspi.api.http_server
# Default port 8000
```

## MCP Tool Usage

USPI provides 3 MCP Tools:

### 1. uspi_lookup — Part Lookup

```json
{
  "part_number": "0WX202",
  "output_format": "compact",
  "fields": ["part_number", "manufacturer", "category", "median_price_usd"]
}
```

Parameters:
- `part_number` (required): Part number, supports OCR dirty text
- `manufacturers`: Filter by vendor
- `include_odm`: Include ODM results (default true)
- `output_format`: Output format `compact|md|csv|json`
- `fields`: Select fields to reduce tokens
- `max_sources`: Max price sources (default 3)

### 2. uspi_compare — Part Comparison

```json
{
  "part_numbers": ["0WX202", "872736-001"],
  "output_format": "md"
}
```

### 3. uspi_export — Data Export

```json
{
  "part_numbers": ["0WX202"],
  "format": "csv",
  "lang": "en"
}
```

## Dialogue Examples

### Example 1: Basic Lookup
> **User**: "Look up 0WX202"
> **Agent**: Returns → 0WX202 | DELL | MEMORY | $149.99

### Example 2: OCR Input
> **User**: "Photo label says 0WX2O2"
> **Agent**: OCR fix → 0WX202 → lookup → result

### Example 3: Excel Export
> **User**: "Export to Excel-compatible format"
> **Agent**: Returns BOM CSV

### Example 4: Part Comparison
> **User**: "Compare 0WX202 and 872736-001"
> **Agent**: Returns Markdown comparison table

### Example 5: ODM Query
> **User**: "What OEM is FOX12B456 for?"
> **Agent**: Returns Foxconn → Dell ODM

### Example 6: Batch Lookup
> **User**: "Check these parts: 0WX202, 872736-001, 01KN234"
> **Agent**: Returns batch results

### Example 7: Spec Interpretation
> **User**: "Can a 750W PSU support 2 A100 GPUs?"
> **Agent**: Calculates power → recommends 1200W PSU

### Example 8: Token Efficiency
> **User**: "Shortest format"
> **Agent**: Compact: 0WX202 | DELL | MEMORY | $150

### Example 9: Field Filtering
> **User**: "Manufacturer and price only"
> **Agent**: Returns {manufacturer, median_price_usd}

### Example 10: CSV Export
> **User**: "Export CSV"
> **Agent**: Returns UTF-8 BOM CSV

## Excel Export Workflow

1. User queries part → Agent calls `uspi_lookup`
2. Agent gets result → calls `to_excel_pasteable()` or `to_csv()`
3. User receives Markdown table → copy-paste into Excel
4. Or user receives CSV file → Excel opens directly (BOM ensures correct Chinese)

## OCR Input Workflow

1. User takes photo/scan → gets OCR text
2. Agent calls `clean_ocr_text()` to clean noise
3. Calls `extract_part_numbers()` to extract candidate PNs
4. Calls `uspi_lookup()` on best candidate
5. Returns structured result

## Output Format Levels

| Format | Use Case | Token Level |
|---|---|---|
| `compact` | Quick lookup/chat | Lowest (~50 tokens/part) |
| `md` | Human read/Excel paste | Medium (~150 tokens/part) |
| `csv` | Data analysis | Low (no repeated field names) |
| `json` | Program consumption | High (full fields) |

## Project Structure

```
uspi/
├── core/              # Core engine
│   ├── parser.py      # Part number recognition
│   ├── fetcher.py     # HTTP fetcher
│   ├── adapters/      # 15 adapters
│   ├── normalizer.py  # Data normalization
│   ├── comparator.py  # Comparison engine
│   ├── unit_converter.py  # Unit conversion
│   ├── ocr_input.py   # OCR preprocessing
│   └── exporter.py    # Multi-format export
├── mcp/server.py      # MCP JSON-RPC server
├── api/http_server.py # HTTP REST API
└── utils/             # Utility modules

docs/
├── README.zh.md       # Chinese README
├── README.en.md       # This document
├── API_SPEC.zh.md     # API spec (Chinese)
├── API_SPEC.en.md     # API spec (English)
├── DIALOGUE_EXAMPLES.md   # 55 dialogue examples
└── UNITS.md           # Unit standardization table

tests/                 # 120 unit tests
```

## License

MIT License
