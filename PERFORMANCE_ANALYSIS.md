# USPI 性能问题分析与优化方案

## 测试环境
- WorkBuddy + MCP stdio 模式
- Windows + Python 3.13
- 测试零件: Samsung M393A8G40AB2-CWE (64GB DDR4-3200 RDIMM)

## 根因分析

### 问题 1: 串行适配器查询（最严重）
**现象**: 每次 lookup 按顺序遍历 15 个适配器，一个超时后才下一个。
**影响**: 15 个适配器 × 30s 超时 = 最坏 450 秒 = 7.5 分钟
**代码位置**: `mcp/server.py:_do_lookup()` 中 for 循环

### 问题 2: 超时过长
**现象**: fetcher 默认 timeout=30s，3 次重试。
**影响**: 单个不适配请求最长 90 秒
**代码位置**: `fetcher.py:fetch(timeout=30)` + `_retry_with_backoff(max_retries=3)`

### 问题 3: 三星型号不匹配 OEM 适配器
**现象**: M393A8G40AB2-CWE 是 Samsung 原厂号，不是 Dell/HP/Lenovo 的 OEM FRU。这些适配器浪费时间搜索官网后才 fallback。
**影响**: 4 个 OEM 适配器 × 超时时间 = 浪费
**根因**: 缺少 Samsung 适配器

### 问题 4: robots.txt 检查阻塞
**现象**: 每次 HTTP 请求前都阻塞检查 robots.txt
**影响**: 额外的网络往返延迟
**代码位置**: `fetcher.py:_check_robots_txt()`

### 问题 5: MCP 子进程模式
**现象**: 每次 tool call 启动新 Python 子进程
**影响**: 进程启动开销 + 适配器重新初始化
**缓解**: 已通过 `_ensure_adapters()` 懒加载部分缓解

## 优化方案

### P0: 立即修复

| # | 优化 | 预期收益 |
|---|------|---------|
| 1 | **并行适配器查询** (ThreadPoolExecutor, max_workers=5) | 从 450s → 30s (15x) |
| 2 | **缩短超时** (30s→10s, 重试3→1) | 从 90s/适配器 → 10s/适配器 (9x) |
| 3 | **智能路由** (按零件号前缀选择适配器) | 从查15个 → 查3-5个 (3-5x) |
| 4 | **新增 Samsung 适配器** | 内存查询准确率提升 |
| 5 | **跳过 robots.txt** | 减少 1 RTT/请求 |
| 6 | **快速 mock fallback** (不匹配直接 mock) | 减少无效 HTTP 请求 |

### P1: 后续优化

| # | 优化 | 预期收益 |
|---|------|---------|
| 7 | **连接池** (urllib 连接复用) | 减少 TCP 握手 |
| 8 | **缓存预热** | 常见零件首查加速 |
| 9 | **Windows 编码兼容** | 解决中文乱码 |
