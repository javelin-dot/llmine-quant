# LLMine Quant Backend — 开发路线图

基于 `doc/07-后端项目设计说明书.md` 和 `doc/prd/V1.0.0-产品需求文档.md` 执行。

## 已完成

- [x] Milestone 1: 项目骨架、数据库、Dashboard API、审计基础
- [x] Phase 1 — Data Service、Strategy Service、Backtest Service
- [x] Phase 2 — Risk Service、Portfolio Service、Execution Service
- [x] Phase 3 — Explain Service、Security Service
- [x] Phase 4 — Collaboration Service、Agent Orchestrator、WebSocket 实时推送
- [x] 全部 11 个屏幕 API（Dashboard / Data / Strategy / Backtest / Risk / Portfolio / Execution / Explain / Security / Collaboration / Audit）
- [x] 端到端测试骨架（pytest + httpx AsyncClient 覆盖所有 screen API）

## 执行计划

### Phase 1 — 数据层与策略层
1. **Data Service** — 数据源模型、适配器接口、日线行情表、数据健康检查
2. **Strategy Service** — 策略模型、Pipeline 状态机、版本管理、NL Prompt 任务
3. **Backtest Service** — 回测任务、权益曲线、绩效指标、压力测试

### Phase 2 — 风控与执行层
4. **Risk Service** — 风控规则、Policy Engine、熔断器、VaR 计算
5. **Portfolio Service** — 组合模型、持仓、NAV、再平衡
6. **Execution Service** — 审批流、订单状态机、预交易检查、执行指标

### Phase 3 — 可解释性与安全层
7. **Explain Service** — 信号归因、决策链、血缘查询
8. **Security Service** — Vault 客户端、密钥轮换、AI 工具权限、提现守卫

### Phase 4 — 协作与实时层
9. **Collaboration Service** — 评审、Diff、A/B 测试、审批流
10. **Agent Orchestrator** — Agent 任务状态、消息协议、工具注册表
11. **WebSocket** — 实时推送服务、事件广播

### Phase 5 — 集成与优化
12. ~~剩余屏幕 API~~ ✅ 已完成（所有 11 个屏幕 API 已对齐前端 MockData）
13. ~~端到端测试骨架~~ ✅ 已完成
14. 性能优化（连接池、缓存层、异步任务队列）
