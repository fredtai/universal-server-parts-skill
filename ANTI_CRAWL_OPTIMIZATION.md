# USPI 反爬优化方案 — 借鉴 Scrapling 技术

## Scrapling 核心技术分析

### 1. 浏览器指纹随机化 (`fingerprints.py`)
Scrapling 使用 browserforge 库生成**完整的浏览器请求头**，不仅仅是 User-Agent，还包括：
- `Accept`, `Accept-Language`, `Accept-Encoding`
- `Sec-Fetch-*` 系列（Sec-Fetch-Dest, Sec-Fetch-Mode, Sec-Fetch-Site, Sec-Fetch-User）
- `Referer` 链
- `Origin`
- 指纹与 OS 匹配（Windows/Mac/Linux 不同）

### 2. 代理轮换 (`proxy_rotation.py`)
- 线程安全的轮询策略
- 支持 HTTP/HTTPS/SOCKS 代理
- 自动错误检测和切换

### 3. 其他反爬技术
- 请求间隔随机化（避免固定频率）
- Cookie 持久化（保持会话状态）
- 自适应重试（根据 HTTP 状态码调整策略）

## USPI 优化实施计划

### 优化 1: AntiCrawlFetcher（完整浏览器指纹）
创建 `uspi/core/anti_crawl_fetcher.py`，继承 Fetcher，添加：
- 30+ 真实浏览器请求头模板
- 随机选择和轮换
- 请求间隔随机化（1-5秒）
- Cookie 持久化
- 代理支持（从环境变量读取）
- 自适应重试（429→增加延迟, 403→切换指纹）

### 优化 2: 适配器使用 AntiCrawlFetcher
所有 adapter 改用 AntiCrawlFetcher 替代 Fetcher

### 优化 3: 缓存策略优化
- 成功响应：缓存 7 天（避免重复请求）
- 失败响应：缓存 1 天（避免重复失败）
- 反爬拦截：缓存 12 小时（尊重站点的 rate limit）

### 优化 4: 请求间隔控制
- 适配器级最小间隔：3 秒
- 域名级最小间隔：5 秒
- 随机抖动：±2 秒
