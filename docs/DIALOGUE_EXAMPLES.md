# USPI Dialogue Examples / USPI 对话示例

> 50+ bilingual dialogue examples covering 8 scenarios.
> 50+ 中英双语对话示例，覆盖 8 个场景。

---

## 场景 1: 基础零件查询 / Basic Part Lookup (8 dialogs)

**对话 1 (中文)**
> **用户**: "查一下 0WX202"
> **Agent**: 调用 `uspi_lookup(part_number="0WX202")` → 返回 Dell 32GB DDR4 RDIMM, $149.99, 置信度 0.85
> **结果**: "0WX202 是戴尔 32GB DDR4 RDIMM 内存条，中位数价格 $149.99，数据来源 Dell Support。"

**Dialog 1 (English)**
> **User**: "Look up 0WX202"
> **Agent**: Calls `uspi_lookup(part_number="0WX202")` → Returns Dell 32GB DDR4 RDIMM, $149.99, confidence 0.85
> **Result**: "0WX202 is a Dell 32GB DDR4 RDIMM memory module, median price $149.99, source: Dell Support."

**对话 2 (中文)**
> **用户**: "What are the specs for Dell 0WX202?"
> **Agent**: 调用 `uspi_lookup(part_number="0WX202", output_format="json")` → 返回完整规格
> **结果**: "{\"part_number\": \"0WX202\", \"manufacturer\": \"DELL\", \"category\": \"MEMORY\", \"specifications\": {\"capacity_gb\": 32, \"speed_mhz\": 2933}, \"median_price_usd\": 149.99}"

**Dialog 2 (English)**
> **User**: "What are the specs for Dell 0WX202?"
> **Agent**: Calls `uspi_lookup(part_number="0WX202", output_format="json")` → Returns full specs
> **Result**: "0WX202: Dell 32GB DDR4 RDIMM 2933MHz, price $149.99."

**对话 3 (中文)**
> **用户**: "0WX202 是什么零件？内存还是硬盘？"
> **Agent**: 调用 `uspi_lookup(part_number="0WX202")` → 从返回的 category 字段判断
> **结果**: "0WX202 是内存（MEMORY）零件，具体为 32GB DDR4 RDIMM。"

**Dialog 3 (English)**
> **User**: "Is 0WX202 a memory module or a hard drive?"
> **Agent**: Calls `uspi_lookup(part_number="0WX202")` → Reads category field
> **Result**: "0WX202 is a memory module (MEMORY), specifically a 32GB DDR4 RDIMM."

**对话 4 (中文)**
> **用户**: "查一下 872736-001"
> **Agent**: 调用 `uspi_lookup(part_number="872736-001")` → 返回 HP 内存
> **结果**: "872736-001 是惠普 32GB DDR4 2933MHz RDIMM，价格约 $129.99。"

**Dialog 4 (English)**
> **User**: "Check part 872736-001"
> **Agent**: Calls `uspi_lookup(part_number="872736-001")` → Returns HP memory
> **Result**: "872736-001 is an HP 32GB DDR4 2933MHz RDIMM, priced around $129.99."

**对话 5 (中文)**
> **用户**: "01KN234 是哪个厂商的？"
> **Agent**: 调用 `uspi_lookup(part_number="01KN234")` → 返回 Lenovo 信息
> **结果**: "01KN234 是联想（Lenovo）的零件。"

**Dialog 5 (English)**
> **User**: "Who makes part 01KN234?"
> **Agent**: Calls `uspi_lookup(part_number="01KN234")` → Returns Lenovo info
> **Result**: "01KN234 is manufactured by Lenovo."

**对话 6 (中文)**
> **用户**: "SNK-P0070APS4 规格是什么？"
> **Agent**: 调用 `uspi_lookup(part_number="SNK-P0070APS4")` → 返回超微散热器
> **结果**: "SNK-P0070APS4 是超微（Supermicro）CPU 散热器。"

**Dialog 6 (English)**
> **User**: "What are the specs for SNK-P0070APS4?"
> **Agent**: Calls `uspi_lookup(part_number="SNK-P0070APS4")` → Returns Supermicro heatsink
> **Result**: "SNK-P0070APS4 is a Supermicro CPU heatsink."

**对话 7 (中文)**
> **用户**: "帮我查这个零件 0WX202 的价格"
> **Agent**: 调用 `uspi_lookup(part_number="0WX202", output_format="compact")` → 紧凑格式
> **结果**: "0WX202 | DELL | MEMORY | $150 | conf:0.85"

**Dialog 7 (English)**
> **User**: "What's the price of 0WX202?"
> **Agent**: Calls `uspi_lookup(part_number="0WX202", output_format="compact")` → Compact format
> **Result**: "0WX202 | DELL | MEMORY | $150 | conf:0.85"

**对话 8 (中文)**
> **用户**: "0WX202 有货吗？"
> **Agent**: 调用 `uspi_lookup(part_number="0WX202")` → 检查 sources 中的 in_stock 字段
> **结果**: "0WX202 在 Dell Support 有库存信息，最新价格 $149.99。"

**Dialog 8 (English)**
> **User**: "Is 0WX202 in stock?"
> **Agent**: Calls `uspi_lookup(part_number="0WX202")` → Checks in_stock field
> **Result**: "0WX202 has stock information from Dell Support, latest price $149.99."

---

## 场景 2: OCR 输入查询 / OCR Input Lookup (7 dialogs)

**对话 1 (中文)**
> **用户**: "我拍了张照片，OCR识别出 FOX12B456，帮我查"
> **Agent**: OCR 文本 "FOX12B456" → 调用 `clean_ocr_text()` → 提取零件号 → `uspi_lookup(part_number="FOX12B456")`
> **结果**: "FOX12B456 是富士康（Foxconn）代工的零件，对应 Dell 内存模块，价格约 $89.99。"

**Dialog 1 (English)**
> **User**: "I took a photo, OCR says FOX12B456, look it up"
> **Agent**: OCR text "FOX12B456" → Calls `clean_ocr_text()` → Extracts PN → `uspi_lookup("FOX12B456")`
> **Result**: "FOX12B456 is a Foxconn ODM part for Dell, memory module, priced around $89.99."

**对话 2 (中文)**
> **用户**: "照片标签是 0WX2O2（可能是0WX202）"
> **Agent**: OCR 文本 "0WX2O2" → 调用 `_apply_confusion_fix()` → "0WX202" → `uspi_lookup("0WX202")`
> **结果**: "已修复 OCR 混淆：0WX2O2 → 0WX202，这是戴尔 32GB DDR4 RDIMM，价格 $149.99。"

**Dialog 2 (English)**
> **User**: "The label in the photo says 0WX2O2 (probably 0WX202)"
> **Agent**: OCR "0WX2O2" → Applies `_apply_confusion_fix()` → "0WX202" → `uspi_lookup("0WX202")`
> **Result**: "OCR confusion fixed: 0WX2O2 → 0WX202. This is a Dell 32GB DDR4 RDIMM, $149.99."

**对话 3 (中文)**
> **用户**: "This image text shows 'QCT-abc-123'"
> **Agent**: OCR 文本 "QCT-abc-123" → 清洗 → 提取 "QCTABC123" → `uspi_lookup("QCTABC123")`
> **结果**: "从图片提取的零件号 QCTABC123 是广达（Quanta）代工零件。"

**Dialog 3 (English)**
> **User**: "This image text shows 'QCT-abc-123'"
> **Agent**: OCR "QCT-abc-123" → Clean → Extract "QCTABC123" → `uspi_lookup("QCTABC123")`
> **Result**: "Extracted part QCTABC123 from image — this is a Quanta ODM part."

**对话 4 (中文)**
> **用户**: "扫描件上写的零件号是 872736-OO1，你看对吗？"
> **Agent**: OCR "872736-OO1" → 混淆修复 → "872736-001" → `uspi_lookup("872736-001")`
> **结果**: "已自动修复：872736-OO1 → 872736-001。这是 HP 32GB DDR4 内存条，价格约 $129.99。"

**Dialog 4 (English)**
> **User**: "The scan says part number 872736-OO1, is that right?"
> **Agent**: OCR "872736-OO1" → Confusion fix → "872736-001" → `uspi_lookup("872736-001")`
> **Result**: "Auto-fixed: 872736-OO1 → 872736-001. This is an HP 32GB DDR4 memory module, ~$129.99."

**对话 5 (中文)**
> **用户**: "照片里有两个零件号：0WX202 和 FOX12B456"
> **Agent**: OCR 文本 → `extract_part_numbers()` 提取两个 → 分别 `uspi_lookup()`
> **结果**: "识别到两个零件：0WX202（Dell 内存 $149.99）和 FOX12B456（Foxconn 代工 $89.99）。"

**Dialog 5 (English)**
> **User**: "There are two part numbers in the photo: 0WX202 and FOX12B456"
> **Agent**: OCR → `extract_part_numbers()` extracts two → `uspi_lookup()` each
> **Result**: "Found two parts: 0WX202 (Dell memory $149.99) and FOX12B456 (Foxconn ODM $89.99)."

**对话 6 (中文)**
> **用户**: "OCR结果很乱：F O X 1 2 B 4 5 6"
> **Agent**: 清洗去除空格 → "FOX12B456" → `uspi_lookup("FOX12B456")`
> **结果**: "清洗后零件号：FOX12B456，富士康代工服务器零件。"

**Dialog 6 (English)**
> **User**: "OCR result is messy: F O X 1 2 B 4 5 6"
> **Agent**: Clean spaces → "FOX12B456" → `uspi_lookup("FOX12B456")`
> **Result**: "Cleaned part number: FOX12B456, Foxconn ODM server part."

**对话 7 (中文)**
> **用户**: "手写标签上写的是 'WIS-123-456'"
> **Agent**: OCR 清洗 → "WIS123456" → 提取 → `uspi_lookup("WIS123456")`
> **结果**: "WIS123456 是纬创（Wistron）代工零件。"

**Dialog 7 (English)**
> **User**: "The handwritten label says 'WIS-123-456'"
> **Agent**: OCR clean → "WIS123456" → Extract → `uspi_lookup("WIS123456")`
> **Result**: "WIS123456 is a Wistron ODM part."

---

## 场景 3: Excel 导出 / Excel Export (6 dialogs)

**对话 1 (中文)**
> **用户**: "把结果导出 Excel 能打开的格式"
> **Agent**: `uspi_lookup("0WX202")` → `to_csv(parts, include_bom=True)`
> **结果**: 返回带 UTF-8 BOM 的 CSV，Excel 直接打开中文不乱码。

**Dialog 1 (English)**
> **User**: "Export the results to a format Excel can open"
> **Agent**: `uspi_lookup("0WX202")` → `to_csv(parts, include_bom=True)`
> **Result**: Returns UTF-8 BOM CSV that Excel opens without encoding issues.

**对话 2 (中文)**
> **用户**: "给我能复制到 Excel 的表格"
> **Agent**: `uspi_lookup("0WX202")` → `to_excel_pasteable(parts)`
> **结果**: 返回 Markdown 表格，用户可直接复制粘贴到 Excel。

**Dialog 2 (English)**
> **User**: "Give me a table I can paste into Excel"
> **Agent**: `uspi_lookup("0WX202")` → `to_excel_pasteable(parts)`
> **Result**: Returns Markdown table that can be copied and pasted directly into Excel.

**对话 3 (中文)**
> **用户**: "对比这三个零件并导出 CSV"
> **Agent**: `uspi_compare(["0WX202", "872736-001", "01KN234"])` → `to_csv(parts)`
> **结果**: 返回 CSV 格式的对比表，含三行零件数据。

**Dialog 3 (English)**
> **User**: "Compare these three parts and export to CSV"
> **Agent**: `uspi_compare(["0WX202", "872736-001", "01KN234"])` → `to_csv(parts)`
> **Result**: Returns CSV comparison table with three rows of part data.

**对话 4 (中文)**
> **用户**: "导出 JSON 格式的结果"
> **Agent**: `uspi_lookup("0WX202")` → `to_json(parts, indent=2)`
> **结果**: 返回格式化的 JSON，含完整字段。

**Dialog 4 (English)**
> **User**: "Export results as JSON"
> **Agent**: `uspi_lookup("0WX202")` → `to_json(parts, indent=2)`
> **Result**: Returns formatted JSON with all fields.

**对话 5 (中文)**
> **用户**: "给我最省 Token 的格式"
> **Agent**: `uspi_lookup("0WX202")` → `to_compact_text(parts)`
> **结果**: "0WX202 | DELL | MEMORY | $150 | conf:0.85"

**Dialog 5 (English)**
> **User**: "Give me the most token-efficient format"
> **Agent**: `uspi_lookup("0WX202")` → `to_compact_text(parts)`
> **Result**: "0WX202 | DELL | MEMORY | $150 | conf:0.85"

**对话 6 (中文)**
> **用户**: "用 Markdown 表格显示"
> **Agent**: `uspi_lookup("0WX202")` → `to_markdown(parts, lang="zh")`
> **结果**: 返回标准 Markdown 表格，可在 GitHub / Notion 中渲染。

**Dialog 6 (English)**
> **User**: "Show as a Markdown table"
> **Agent**: `uspi_lookup("0WX202")` → `to_markdown(parts, lang="en")`
> **Result**: Returns standard Markdown table renderable in GitHub / Notion.

---

## 场景 4: 零件对比 / Part Comparison (7 dialogs)

**对话 1 (中文)**
> **用户**: "对比 0WX202 和 SNK-P0070APS4"
> **Agent**: 调用 `uspi_compare(part_numbers=["0WX202", "SNK-P0070APS4"])`
> **结果**: 返回 Markdown 对比表格：零件号、厂商、分类、规格、价格、可信度。

**Dialog 1 (English)**
> **User**: "Compare 0WX202 and SNK-P0070APS4"
> **Agent**: Calls `uspi_compare(part_numbers=["0WX202", "SNK-P0070APS4"])`
> **Result**: Returns Markdown comparison table: PN, manufacturer, category, specs, price, confidence.

**对话 2 (中文)**
> **用户**: "Dell 和 HP 的同规格内存哪个便宜？"
> **Agent**: 分别查询 0WX202（Dell）和 872736-001（HP）→ 对比 median_price_usd
> **结果**: "Dell 0WX202: $149.99；HP 872736-001: $129.99。HP 更便宜约 $20。"

**Dialog 2 (English)**
> **User**: "Which is cheaper, Dell or HP memory with same specs?"
> **Agent**: Query 0WX202 (Dell) and 872736-001 (HP) → Compare median_price_usd
> **Result**: "Dell 0WX202: $149.99; HP 872736-001: $129.99. HP is ~$20 cheaper."

**对话 3 (中文)**
> **用户**: "0WX202, 872736-001, 01KN234 三个内存条对比"
> **Agent**: `uspi_compare(["0WX202", "872736-001", "01KN234"])` → md 输出
> **结果**: 三列对比表：Dell/HP/Lenovo 的 32GB DDR4 内存价格和规格对比。

**Dialog 3 (English)**
> **User**: "Compare these three memory modules: 0WX202, 872736-001, 01KN234"
> **Agent**: `uspi_compare(["0WX202", "872736-001", "01KN234"])` → md output
> **Result**: Three-column comparison of Dell/HP/Lenovo 32GB DDR4 memory prices and specs.

**对话 4 (中文)**
> **用户**: "对比一下 Foxconn 和 Quanta 的同类产品"
> **Agent**: `uspi_compare(["FOX12B456", "QCT7890123"])`
> **结果**: 富士康 vs 广达代工零件对比表。

**Dialog 4 (English)**
> **User**: "Compare Foxconn and Quanta equivalent parts"
> **Agent**: `uspi_compare(["FOX12B456", "QCT7890123"])`
> **Result**: Foxconn vs Quanta ODM part comparison table.

**对话 5 (中文)**
> **用户**: "导出对比结果为 CSV"
> **Agent**: `uspi_compare(["0WX202", "872736-001"])` → `to_csv()`
> **结果**: 返回 CSV 对比文件。

**Dialog 5 (English)**
> **User**: "Export comparison as CSV"
> **Agent**: `uspi_compare(["0WX202", "872736-001"])` → `to_csv()`
> **Result**: Returns CSV comparison file.

**对话 6 (中文)**
> **用户**: "哪个零件可信度更高？"
> **Agent**: 对比两个零件的 confidence_score 字段
> **结果**: "0WX202 可信度 0.85，高于 FOX12B456 的 0.65。"

**Dialog 6 (English)**
> **User**: "Which part has higher confidence?"
> **Agent**: Compare confidence_score fields
> **Result**: "0WX202 has confidence 0.85, higher than FOX12B456 at 0.65."

**对话 7 (中文)**
> **用户**: "Dell 0WX202 和 HP 872736-001 的规格差异在哪？"
> **Agent**: `uspi_compare()` → 提取 specifications 字段差异
> **结果**: "两者均为 32GB DDR4 2933MHz RDIMM，规格一致。价格差异：Dell $149.99 vs HP $129.99。"

**Dialog 7 (English)**
> **User**: "What are the spec differences between Dell 0WX202 and HP 872736-001?"
> **Agent**: `uspi_compare()` → Extract specification differences
> **Result**: "Both are 32GB DDR4 2933MHz RDIMM, specs match. Price diff: Dell $149.99 vs HP $129.99."

---

## 场景 5: ODM 查询 / ODM Query (6 dialogs)

**对话 1 (中文)**
> **用户**: "富士康代工的 Dell 零件怎么查？"
> **Agent**: `uspi_lookup(part_number="FOX12B456", include_odm=True)` → 返回 oem_brand 字段
> **结果**: "FOX12B456 是富士康代工的 Dell 零件，OEM 品牌：DELL。"

**Dialog 1 (English)**
> **User**: "How do I look up Dell parts made by Foxconn?"
> **Agent**: `uspi_lookup("FOX12B456", include_odm=True)` → Returns oem_brand field
> **Result**: "FOX12B456 is a Foxconn ODM part for Dell. OEM brand: DELL."

**对话 2 (中文)**
> **用户**: "Quanta QCT7890123 对应什么 OEM 零件？"
> **Agent**: `uspi_lookup("QCT7890123")` → 返回 oem_brand 映射
> **结果**: "QCT7890123 是广达（Quanta）代工，对应 OEM：DELL / HP / AWS。"

**Dialog 2 (English)**
> **User**: "What OEM part does Quanta QCT7890123 correspond to?"
> **Agent**: `uspi_lookup("QCT7890123")` → Returns oem_brand mapping
> **Result**: "QCT7890123 is Quanta ODM, corresponds to OEM brands: DELL / HP / AWS."

**对话 3 (中文)**
> **用户**: "纬创代工的零件有哪些 OEM 品牌？"
> **Agent**: 查询 ODM_OEM_MAP → WISTRON 对应 DELL, HP, LENOVO
> **结果**: "纬创（Wistron）代工零件对应 OEM 品牌：Dell、HP、Lenovo。"

**Dialog 3 (English)**
> **User**: "Which OEM brands does Wistron manufacture for?"
> **Agent**: Query ODM_OEM_MAP → WISTRON maps to DELL, HP, LENOVO
> **Result**: "Wistron ODM parts correspond to OEM brands: Dell, HP, Lenovo."

**对话 4 (中文)**
> **用户**: "和硕 PEG123456 是哪个品牌的零件？"
> **Agent**: `uspi_lookup("PEG123456")` → 返回 PEGATRON 及 oem_brand
> **结果**: "PEG123456 是和硕（Pegatron）代工，对应 OEM：ASUS / APPLE / MSI。"

**Dialog 4 (English)**
> **User**: "Which brand is Pegatron PEG123456 for?"
> **Agent**: `uspi_lookup("PEG123456")` → Returns PEGATRON and oem_brand
> **Result**: "PEG123456 is Pegatron ODM for OEM brands: ASUS / APPLE / MSI."

**对话 5 (中文)**
> **用户**: "英业达 INV123456 对应 Dell 的哪个零件号？"
> **Agent**: `uspi_lookup("INV123456")` → 解析 ODM-OEM 关系
> **结果**: "INV123456 是英业达（Inventec）代工零件，可能对应 Dell/HP/Lenovo 产品。"

**Dialog 5 (English)**
> **User**: "What Dell part number corresponds to Inventec INV123456?"
> **Agent**: `uspi_lookup("INV123456")` → Parses ODM-OEM relationship
> **Result**: "INV123456 is an Inventec ODM part, may correspond to Dell/HP/Lenovo products."

**对话 6 (中文)**
> **用户**: "捷普 JBL123456 的 OEM 品牌是什么？"
> **Agent**: `uspi_lookup("JBL123456")` → 返回 JABIL 及 oem_brand
> **结果**: "JBL123456 是捷普（Jabil）代工，对应 OEM：CISCO / HP / JUNIPER。"

**Dialog 6 (English)**
> **User**: "What OEM brand is Jabil JBL123456 for?"
> **Agent**: `uspi_lookup("JBL123456")` → Returns JABIL and oem_brand
> **Result**: "JBL123456 is Jabil ODM for OEM brands: CISCO / HP / JUNIPER."

---

## 场景 6: 批量查询 / Batch Query (6 dialogs)

**对话 1 (中文)**
> **用户**: "查这批零件：0WX202, 872736-001, 01KN234"
> **Agent**: 分别调用 3 次 `uspi_lookup()` → 汇总结果
> **结果**: 返回三行紧凑格式结果，每零件一行。

**Dialog 1 (English)**
> **User**: "Check these parts: 0WX202, 872736-001, 01KN234"
> **Agent**: Call `uspi_lookup()` 3 times → Aggregate results
> **Result**: Returns three lines of compact format, one per part.

**对话 2 (中文)**
> **用户**: "查列表 [0WX202, FOX12B456, QCT7890123] 并给出价格对比表"
> **Agent**: 批量查询 → `uspi_compare()` → Markdown 表格
> **结果**: 三列对比表，含零件号、厂商、分类、美元价。

**Dialog 2 (English)**
> **User**: "Check list [0WX202, FOX12B456, QCT7890123] and give price comparison table"
> **Agent**: Batch query → `uspi_compare()` → Markdown table
> **Result**: Three-column comparison with PN, manufacturer, category, USD price.

**对话 3 (中文)**
> **用户**: "查 5 个零件并导出 CSV"
> **Agent**: 批量查询 → `uspi_export(part_numbers=[...], format="csv")`
> **结果**: 返回 CSV 文件，含 5 行零件数据。

**Dialog 3 (English)**
> **User**: "Look up 5 parts and export CSV"
> **Agent**: Batch query → `uspi_export(part_numbers=[...], format="csv")`
> **Result**: Returns CSV file with 5 rows of part data.

**对话 4 (中文)**
> **用户**: "查 SNK-P0070APS4, SNK-P0048AP4 并对比"
> **Agent**: `uspi_compare(["SNK-P0070APS4", "SNK-P0048AP4"])` → md 输出
> **结果**: 超微两款散热器的对比表格。

**Dialog 4 (English)**
> **User**: "Look up SNK-P0070APS4, SNK-P0048AP4 and compare"
> **Agent**: `uspi_compare(["SNK-P0070APS4", "SNK-P0048AP4"])` → md output
> **Result**: Comparison table of two Supermicro heatsinks.

**对话 5 (中文)**
> **用户**: "查这批 Dell 零件：0WX202, A9654882"
> **Agent**: 批量查询 → 汇总
> **结果**: "0WX202：内存 $149.99；A9654882：未识别，建议检查零件号。"

**Dialog 5 (English)**
> **User**: "Check these Dell parts: 0WX202, A9654882"
> **Agent**: Batch query → Aggregate
> **Result**: "0WX202: memory $149.99; A9654882: not recognized, please verify part number."

**对话 6 (中文)**
> **用户**: "把这批零件导出到 Excel：0WX202, 872736-001, FOX12B456"
> **Agent**: 批量查询 → `to_excel_pasteable()`
> **结果**: 返回可粘贴 Excel 的 Markdown 表格。

**Dialog 6 (English)**
> **User**: "Export these parts to Excel: 0WX202, 872736-001, FOX12B456"
> **Agent**: Batch query → `to_excel_pasteable()`
> **Result**: Returns Excel-pasteable Markdown table.

---

## 场景 7: 规格解读 / Spec Interpretation (6 dialogs)

**对话 1 (中文)**
> **用户**: "32GB DDR4 2933MHz 和 3200MHz 有什么区别？"
> **Agent**: 分别查询两个规格 → 对比 frequency 字段
> **结果**: "2933MHz vs 3200MHz：后者频率高约 9.1%，理论带宽更高。实际性能差异约 3-5%。"

**Dialog 1 (English)**
> **User**: "What's the difference between 32GB DDR4 2933MHz and 3200MHz?"
> **Agent**: Query both specs → Compare frequency field
> **Result**: "2933MHz vs 3200MHz:后者 is ~9.1% higher frequency, higher theoretical bandwidth. Real-world diff ~3-5%."

**对话 2 (中文)**
> **用户**: "750W PSU 能支持 2 块 A100 吗？"
> **Agent**: 查询 PSU 规格 + A100 功耗（400W each）→ 计算总功耗
> **结果**: "2x A100 = ~800W 峰值。750W PSU 不足，建议 1200W 以上电源。"

**Dialog 2 (English)**
> **User**: "Can a 750W PSU support 2 A100 GPUs?"
> **Agent**: Query PSU spec + A100 power (400W each) → Calculate total
> **Result**: "2x A100 = ~800W peak. 750W PSU insufficient, recommend 1200W+."

**对话 3 (中文)**
> **用户**: "RDIMM 和 LRDIMM 有什么区别？"
> **Agent**: 从分类数据中提取 spec 差异
> **结果**: "RDIMM：Registered DIMM，支持单条 32GB；LRDIMM：Load-Reduced，支持单条 64GB+，适合大容量配置。"

**Dialog 3 (English)**
> **User**: "What's the difference between RDIMM and LRDIMM?"
> **Agent**: Extract spec differences from category data
> **Result**: "RDIMM: Registered, up to 32GB per stick; LRDIMM: Load-Reduced, 64GB+ per stick, for high-capacity configs."

**对话 4 (中文)**
> **用户**: "SATA SSD 和 NVMe SSD 速度差多少？"
> **Agent**: 对比 data_rate 字段
> **结果**: "SATA SSD: ~0.5Gbps；NVMe SSD: ~3.5-7Gbps。NVMe 快 7-14 倍。"

**Dialog 4 (English)**
> **User**: "How much faster is NVMe SSD vs SATA SSD?"
> **Agent**: Compare data_rate fields
> **Result**: "SATA SSD: ~0.5Gbps; NVMe SSD: ~3.5-7Gbps. NVMe is 7-14x faster."

**对话 5 (中文)**
> **用户**: "25GbE 网卡需要什么样的交换机？"
> **Agent**: 查询 NIC 规格 → 匹配交换机要求
> **结果**: "25GbE 网卡需要支持 25Gbps 的 SFP28 端口交换机。"

**Dialog 5 (English)**
> **User**: "What switch do I need for a 25GbE NIC?"
> **Agent**: Query NIC spec → Match switch requirements
> **Result**: "25GbE NIC requires a switch with SFP28 ports supporting 25Gbps."

**对话 6 (中文)**
> **用户**: "1TB HDD 和 1TB SSD 的功耗差多少？"
> **Agent**: 查询 PSU/power 规格对比
> **结果**: "1TB HDD: active ~7W, idle ~3W；1TB SSD: active ~3W, idle ~0.5W。SSD 省电约 50-80%。"

**Dialog 6 (English)**
> **User**: "What's the power difference between 1TB HDD and 1TB SSD?"
> **Agent**: Compare power specs
> **Result**: "1TB HDD: active ~7W, idle ~3W; 1TB SSD: active ~3W, idle ~0.5W. SSD saves ~50-80% power."

---

## 场景 8: Token 效率 / Token Efficiency (8 dialogs)

**对话 1 (中文)**
> **用户**: "用最少字数告诉我 0WX202 的价格"
> **Agent**: `uspi_lookup("0WX202", output_format="compact")` → compact 格式
> **结果**: "0WX202 | DELL | MEMORY | $150 | conf:0.85"

**Dialog 1 (English)**
> **User**: "Tell me the price of 0WX202 in the fewest words"
> **Agent**: `uspi_lookup("0WX202", output_format="compact")` → compact
> **Result**: "0WX202 | DELL | MEMORY | $150 | conf:0.85"

**对话 2 (中文)**
> **用户**: "Quick price check for Dell memory"
> **Agent**: `uspi_lookup("0WX202", output_format="compact", fields=["part_number","median_price_usd"])`
> **结果**: "0WX202: $149.99"

**Dialog 2 (English)**
> **User**: "Quick price check for Dell memory"
> **Agent**: `uspi_lookup("0WX202", output_format="compact", fields=["part_number","median_price_usd"])`
> **Result**: "0WX202: $149.99"

**对话 3 (中文)**
> **用户**: "只告诉我厂商和价格"
> **Agent**: `uspi_lookup("0WX202", fields=["manufacturer_zh","median_price_usd"])`
> **结果**: "厂商：戴尔，价格：$149.99"

**Dialog 3 (English)**
> **User**: "Just tell me the manufacturer and price"
> **Agent**: `uspi_lookup("0WX202", fields=["manufacturer","median_price_usd"])`
> **Result**: "Manufacturer: Dell, Price: $149.99"

**对话 4 (中文)**
> **用户**: "0WX202 用最短的格式"
> **Agent**: `uspi_lookup("0WX202", output_format="compact")`
> **结果**: "0WX202 | 戴尔 | 内存 | $150 | 0.85"

**Dialog 4 (English)**
> **User**: "Shortest format for 0WX202"
> **Agent**: `uspi_lookup("0WX202", output_format="compact")`
> **Result**: "0WX202 | Dell | MEMORY | $150 | 0.85"

**对话 5 (中文)**
> **用户**: "批量查零件， compact 格式"
> **Agent**: 批量 `uspi_lookup()` → `to_compact_text()`
> **结果**: 多行紧凑文本，每零件一行。

**Dialog 5 (English)**
> **User**: "Batch lookup parts, compact format"
> **Agent**: Batch `uspi_lookup()` → `to_compact_text()`
> **Result**: Multi-line compact text, one line per part.

**对话 6 (中文)**
> **用户**: "对比 0WX202 和 872736-001，用最省 Token 的格式"
> **Agent**: `uspi_compare(["0WX202","872736-001"])` → compact 格式
> **结果**: "0WX202 DELL $150 | 872736-001 HP $130"

**Dialog 6 (English)**
> **User**: "Compare 0WX202 and 872736-001 in most token-efficient format"
> **Agent**: `uspi_compare(["0WX202","872736-001"])` → compact
> **Result**: "0WX202 DELL $150 | 872736-001 HP $130"

**对话 7 (中文)**
> **用户**: "CSV 格式导出，只要零件号和价格"
> **Agent**: `uspi_export(["0WX202"], format="csv")` → 精简字段
> **结果**: CSV 含两列：part_number, median_price_usd

**Dialog 7 (English)**
> **User**: "Export CSV with just part number and price"
> **Agent**: `uspi_export(["0WX202"], format="csv")` → Minimal fields
> **Result**: CSV with two columns: part_number, median_price_usd.

**对话 8 (中文)**
> **用户**: "md 格式，只要关键字段"
> **Agent**: `to_markdown(parts, fields=["part_number","manufacturer","median_price_usd"])`
> **结果**: Markdown 表格，仅 3 列。

**Dialog 8 (English)**
> **User**: "Markdown format, key fields only"
> **Agent**: `to_markdown(parts, fields=["part_number","manufacturer","median_price_usd"])`
> **Result**: Markdown table with only 3 columns.

---

*Total: 55 dialogue examples across 8 scenarios / 总计 55 组对话示例，覆盖 8 个场景。*
