# USPI Unit Standardization Table / USPI 单位标准化对照表

> This document lists all 11 supported dimensions, their original units, standard SI units, and conversion formulas.
> 本文档列出所有 11 个支持维度，包含原始单位、标准 SI 单位和转换公式。

---

## 1. Capacity / 容量

| Raw Unit / 原始单位 | Standard Unit / 标准单位 | Conversion Formula / 转换公式 |
|---|---|---|
| MB | GB | value x 0.001 |
| GB | GB | value x 1.0 (identity) |
| TB | GB | value x 1000.0 |
| MiB | GB | value x (1/953.67) ≈ value x 0.001048576 |
| GiB | GB | value x 1.073741824 |
| TiB | GB | value x 1099.511627776 |

**Multiplier format / 乘法格式**: `2x 32GB` → 64 GB

---

## 2. Frequency / 频率

| Raw Unit / 原始单位 | Standard Unit / 标准单位 | Conversion Formula / 转换公式 |
|---|---|---|
| Hz | GHz | value x 1e-9 |
| KHz | GHz | value x 1e-6 |
| MHz | GHz | value x 0.001 |
| GHz | GHz | value x 1.0 (identity) |

---

## 3. Power / 功率

| Raw Unit / 原始单位 | Standard Unit / 标准单位 | Conversion Formula / 转换公式 |
|---|---|---|
| mW | W | value x 0.001 |
| W | W | value x 1.0 (identity) |
| kW | W | value x 1000.0 |
| BTU/hr | W | value x 0.293071 |
| BTU/h | W | value x 0.293071 |

---

## 4. Dimension / 尺寸

| Raw Unit / 原始单位 | Standard Unit / 标准单位 | Conversion Formula / 转换公式 |
|---|---|---|
| mm | mm | value x 1.0 (identity) |
| cm | mm | value x 10.0 |
| m | mm | value x 1000.0 |
| inch / in / " | mm | value x 25.4 |

---

## 5. Weight / 重量

| Raw Unit / 原始单位 | Standard Unit / 标准单位 | Conversion Formula / 转换公式 |
|---|---|---|
| g | kg | value x 0.001 |
| kg | kg | value x 1.0 (identity) |
| lb | kg | value x 0.453592 |
| oz | kg | value x 0.0283495 |

---

## 6. RPM / 转速

| Raw Unit / 原始单位 | Standard Unit / 标准单位 | Conversion Formula / 转换公式 |
|---|---|---|
| RPM | RPM | value x 1.0 (identity) |
| r/min | RPM | value x 1.0 (identity) |

---

## 7. Voltage / 电压

| Raw Unit / 原始单位 | Standard Unit / 标准单位 | Conversion Formula / 转换公式 |
|---|---|---|
| mV | V | value x 0.001 |
| V | V | value x 1.0 (identity) |
| kV | V | value x 1000.0 |

---

## 8. Current / 电流

| Raw Unit / 原始单位 | Standard Unit / 标准单位 | Conversion Formula / 转换公式 |
|---|---|---|
| mA | A | value x 0.001 |
| A | A | value x 1.0 (identity) |

---

## 9. Temperature / 温度

| Raw Unit / 原始单位 | Standard Unit / 标准单位 | Conversion Formula / 转换公式 |
|---|---|---|
| °C / ℃ | °C | value x 1.0 (identity) |
| °F / ℉ | °C | (value - 32) x 5/9 |
| K | °C | value - 273.15 |

---

## 10. Data Rate / 数据速率

| Raw Unit / 原始单位 | Standard Unit / 标准单位 | Conversion Formula / 转换公式 |
|---|---|---|
| KB/s | Gbps | value x 0.000008 |
| MB/s | Gbps | value x 0.008 |
| Mbps | Gbps | value x 0.001 |
| Gbps | Gbps | value x 1.0 (identity) |

---

## 11. Cache / 缓存

| Raw Unit / 原始单位 | Standard Unit / 标准单位 | Conversion Formula / 转换公式 |
|---|---|---|
| MB | MB | value x 1.0 (identity) |
| GB | MB | value x 1000.0 |

---

## Confidence Scores / 置信度评分

| Scenario / 场景 | Confidence / 置信度 |
|---|---|
| Normal conversion / 正常转换 | 1.0 |
| Unknown unit (number extracted) / 未知单位（提取到数值） | 0.9 |
| Parse failure / 解析失败 | 0.0 |
