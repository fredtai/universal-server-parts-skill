# ITERATION.md -- USPI Iteration Roadmap / USPI 迭代路线图

## v0.1.0 (Current / 当前版本)

- 15 adapters (4 OEM + 8 ODM + 3 Market) / 15 个适配器（4 OEM + 8 ODM + 3 市场）
- OCR input support / OCR 输入支持
- Excel-compatible export / Excel 兼容导出
- MCP + HTTP dual interface / MCP + HTTP 双接口
- 120 unit tests with 100% pass rate / 120 个单元测试全部通过
- Full bilingual documentation / 完整双语文档

## v0.2.0 (Planned / 计划)

- Adapter accuracy improvement to 80%+ / 适配器准确率提升至 80%+
- Add Mitac ODM adapter / 新增 Mitac ODM 适配器
- eBay/Amazon parsing enhancement / eBay/Amazon 解析增强
- Regression test suite with 100 part numbers / 回归测试集 100 个零件号
- HTTP API full implementation / HTTP API 完整实现

## v0.3.0 (Planned / 计划)

- Token consumption optimization (target: 30% reduction) / Token 消耗优化（目标减少 30%）
- Adapter lifecycle management (experimental -> stable -> deprecated) / 适配器生命周期管理
- Community extensions: Issue submission for new ODM prefixes / 社区扩展：Issue 提交新 ODM 前缀
- Price trend tracking over time / 价格趋势追踪

## v0.4.0 (Future / 未来)

- WebSocket real-time price alerts / WebSocket 实时价格预警
- Multi-language support beyond EN/ZH / 超出中英的多语言支持
- GraphQL API endpoint / GraphQL API 端点
- Plugin system for custom adapters / 自定义适配器插件系统

## SemVer Rules / 语义化版本规则

| Level / 级别 | Rule / 规则 |
|---|---|
| MAJOR | Incompatible schema changes / 不兼容的 Schema 变更 |
| MINOR | New adapters or features / 新增适配器或功能 |
| PATCH | Bug fixes or data updates / Bug 修复或数据更新 |
