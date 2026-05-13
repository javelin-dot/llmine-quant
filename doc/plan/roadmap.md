# LLMine Quant — 开发路线图

> 基于 gap-analysis.md，按优先级排列的后续开发计划  
> 更新日期：2026-05-13

---

## Sprint 1：打通主流程核心（1-2周）

目标：让"策略生成 → 回测 → Paper Trading"完整跑通，所有关键 API 返回真实数据。

### Task 1.1：修复 Dashboard 类型合约

**范围**：前端  
**文件**：`frontend/src/lib/api.ts`

```typescript
// 当前（错误）
type DashboardOverview = MockData['dashboard']

// 修复：定义包含 meta/system/modals 的正确类型
interface DashboardOverview extends MockData['dashboard'] {
  meta: { product: string; subtitle: string }
  system: { healthScore: number; healthStatusLabel: string; healthBarHeights: number[]; autopilot: boolean; riskGateLabel: string }
  modals: Record<string, { title: string; body: string; primary: string }>
}
```

---

### Task 1.2：Backtest 屏幕接收 initialStrategyId

**范围**：前端  
**文件**：`frontend/src/screens/Backtest/index.tsx`

- 读取 `initialStrategyId` prop，用于调用 `api.strategy.detail(id)` 预填策略名称
- 读取 `initialTaskId` prop，加载已有回测结果
- 在 BacktestComparison 中展示历史回测列表（调用 `api.backtest.list()`）

---

### Task 1.3：Paper Trading 前端屏幕

**范围**：前端  
**文件**：新建 `frontend/src/screens/Paper/`

- 在 `App.tsx` Screen 类型中加入 `'paper'`
- 侧边栏 Command 区加入"模拟盘"入口
- 实现 PaperAccountList（账户列表 + 创建按钮）
- 实现 PaperPositions（持仓列表）
- 实现 PaperNavChart（NAV曲线，复用 ECharts 模式）
- 实现 PaperOrderHistory（订单历史）
- 实现 RunEodButton（EOD 触发按钮）
- 创建 `frontend/src/contexts/PaperContext.tsx`

---

### Task 1.4：Audit API 接数据库

**范围**：后端  
**文件**：`backend/app/api/v1/audit.py`

- `GET /audit/overview`：查询 `audit_logs` 表最近 100 条，统计 Actor 分布
- `GET /audit/logs`：支持分页、actorType 过滤、时间范围过滤
- `GET /audit/registry`：查询 `tool_registry` 表
- `GET /audit/hitl-rules`：查询 `hitl_rules` 表（已有迁移）

---

### Task 1.5：扩展 api.ts 暴露已有后端端点

**范围**：前端  
**文件**：`frontend/src/lib/api.ts`

新增以下调用：
```typescript
strategy.templates()         // GET /strategies/templates
strategy.createDraft(...)    // POST /strategies/
strategy.transition(id, ...) // POST /strategies/{id}/transition
strategy.events(id)          // GET /strategies/{id}/events
execution.approve(id)        // POST /execution/approvals/{id}/approve
execution.reject(id, reason) // POST /execution/approvals/{id}/reject
risk.triggerCircuit(level)   // POST /risk/circuit-breakers/{level}/trigger
portfolio.approveRebalance(id)
data.importAkshare(...)      // POST /data/market-bars/import/akshare
data.marketBars(symbol, ...) // GET /data/market-bars
data.features()              // GET /data/features
```

---

## Sprint 2：DB 驱动替换硬编码数据（2-3周）

目标：将所有返回假数据的 API 模块改为从数据库读取真实数据。

### Task 2.1：缺失迁移文件补齐

**优先级排序**：

1. **Execution（live）**：`approvals`, `orders`, `fills`, `execution_metrics`, `agent_traces`
2. **Risk（live）**：`risk_rules`, `risk_checks`, `risk_breaches`, `circuit_breakers`, `var_history`
3. **Portfolio**：`portfolios`, `accounts`, `positions`, `cash_balances`, `nav_snapshots`, `rebalance_proposals`
4. **Security**：`key_vault`, `key_rotations`, `security_events`
5. **Collaboration**：`strategy_reviews`, `review_comments`, `ab_tests`, `approval_flows`
6. **Explain**：`signal_records`, `attribution_records`

每个领域对应一个迁移文件，参照现有迁移文件风格。

---

### Task 2.2：Execution API 接数据库

**文件**：`backend/app/api/v1/execution.py`

- `GET /overview`：从 `approvals`、`orders`、`execution_metrics` 表查询
- `POST /approvals/{id}/approve`：更新 `approvals.status = 'approved'`，写 `audit_logs`，触发 Paper 模拟执行
- `POST /approvals/{id}/reject`：更新 status，写拒绝原因到 `orders`，写 `audit_logs`
- 预交易检查：按照 `risk_rules` 表中配置的规则实时计算
- 审计：每次审批/拒绝写 `audit_logs`

---

### Task 2.3：Risk API 接数据库

**文件**：`backend/app/api/v1/risk.py`

- `GET /overview`：VaR 从 `var_history` 读取，Circuit Breakers 从 `circuit_breakers` 读取，Breaches 从 `risk_breaches` 读取
- `POST /circuit-breakers/{level}/trigger`：更新 `circuit_breakers.status = 'triggered'`，写 `audit_logs`，广播 WS 事件
- `POST /circuit-breakers/{level}/recover`：更新状态，写 audit
- VaR 历史图：从 Paper Trading NAV 数据计算历史 VaR

---

### Task 2.4：Portfolio API 接数据库

**文件**：`backend/app/api/v1/portfolio.py`

- NAV：汇总 `paper_accounts` 的 `paper_nav_points` 最新值
- 分配：汇总 `paper_positions` 按策略分组
- 再平衡提案：从 `rebalance_proposals` 表读取，`approve` 动作更新状态

---

### Task 2.5：Audit API 全量接数据库（扩展 Task 1.4）

扩展为支持：
- 哈希链完整性验证（对 `audit_logs` 的 `prev_hash` 链式验证）
- Actor 统计分页查询
- 事件导出（CSV）

---

## Sprint 3：认证系统 + WebSocket（2周）

目标：实现基础鉴权体系，打通实时推送。

### Task 3.1：认证系统

**后端**：
- `POST /api/v1/auth/login`：校验 username/password，发放 JWT access + refresh token
- `POST /api/v1/auth/refresh`：刷新 token
- `POST /api/v1/auth/logout`：撤销 refresh token（写 `sessions` 表）
- `app/core/security.py`：`require_auth` FastAPI Depends，挂载到所有非 health 路由

**前端**：
- 新建 `frontend/src/screens/Login/`：用户名/密码表单
- `api.ts`：请求拦截器注入 `Authorization: Bearer <token>`
- `api.ts`：401 响应触发 refresh，失败则跳转 Login
- `localStorage` 存储 token（或 `httpOnly cookie` 后端实现）

---

### Task 3.2：WebSocket 实时推送

**后端**：
- `core/websocket.py`：`broadcast(topic, payload)` 已存在，在以下位置调用：
  - `services/strategy_generation.py`：每个 pipeline 阶段结束时广播 `strategy-events`
  - `api/v1/execution.py`：approve/reject 时广播 `execution-events`
  - `api/v1/risk.py`：circuit breaker 触发时广播 `risk-events`

**前端**：
- `frontend/src/lib/ws.ts`：创建 WebSocket 客户端工具（自动重连，支持 token 鉴权）
- `App.tsx`：建立 WS 连接，分发事件到对应 Context
- Strategy 屏幕：接收 `strategy-events` 更新进度条（替代轮询）
- Risk 屏幕：接收 `risk-events` 实时更新熔断器状态
- Execution 屏幕：接收 `execution-events` 实时更新审批队列

---

## Sprint 4：解释层 + 协作层（1-2周）

### Task 4.1：Explain 接真实信号

- `GET /explain/{signal_id}`：从 `approval` 记录关联 strategy → version → pipeline_events，重建决策链
- 前端 Explain 屏幕：增加 `onNavigate` 从 Execution 屏幕传入信号 ID
- 归因数据：从 backtest 的 `feature_usages` 表提取因子权重

### Task 4.2：Collaboration 接数据库

- `strategy_reviews` 表：迁移 + 增删改查
- `POST /collaboration/reviews`：创建评审单
- `POST /collaboration/reviews/{id}/approve|reject`：提交评审决定
- A/B Test：从两个 `backtest_runs` 对比指标

### Task 4.3：Security 接数据库

- `key_vault` 表：迁移 + API
- `POST /security/vault/rotate`：触发密钥轮换，写 `security_events`
- 前端 Security 屏幕中的"轮换"按钮接入真实接口

---

## Sprint 5：策略运行时 + Agent 编排（3周）

### Task 5.1：策略代码执行沙箱

- `domains/strategy/runtime.py`：实现 `execute()` 方法
- 方案：在受限的 Python 执行环境中运行 LLM 生成的策略代码
- 输出：信号序列（date → {symbol: weight}）写入 DB
- 安全：禁止网络请求、文件写入，设置 CPU/内存上限

### Task 5.2：策略信号接入 DailyBacktestEngine

- 当策略有代码时，从运行时获取每日信号
- 当策略无代码时（config-based），用现有规则引擎
- 统一接口：`SignalProvider` → `BacktestEngine`

### Task 5.3：Agent Orchestrator 接入流程

- 策略生成后自动触发 Research Agent 评审
- 回测通过后自动触发 Paper Agent 开始模拟
- Paper 稳定后自动生成 Execution 审批提案
- 通过 WS 实时播报每个 Agent 动作到前端 Dashboard

### Task 5.4：LLM 状态监控接口

- `GET /api/v1/llm/status`：返回当前 provider、source、是否 mock 模式
- `GET /api/v1/llm/test`：发送测试提示，验证 LLM 可用性
- 前端 Dashboard 的 Agent Matrix 状态反映 LLM 可用性

---

## Sprint 6：数据层完善（1-2周）

### Task 6.1：Data 屏幕接数据库

- `GET /data/overview`：从 `market_bars_daily` 统计活跃数据源、缺失率、延迟
- 数据源健康度：从 `DataSourceHealth` 表（如需补充迁移）读取
- 事件记录：数据异常写入 `data_incidents` 表

### Task 6.2：Data 屏幕增加导入 UI

- Data 屏幕的 `SourceMatrix` 中增加"导入"按钮
- 表单：选择 AKShare / CSV，输入股票代码列表，日期范围
- 提交后调用 `api.data.importAkshare()` 并展示导入进度

---

## 优先级总结

| Priority | Sprint | 预计工期 | 核心价值 |
|----------|--------|---------|---------|
| P0 | Sprint 1 | 1-2周 | 主流程可运行 |
| P1 | Sprint 2 | 2-3周 | 数据真实可信 |
| P1 | Sprint 3 | 2周 | 安全+实时 |
| P2 | Sprint 4 | 1-2周 | 业务深度 |
| P2 | Sprint 5 | 3周 | 智能自动化 |
| P3 | Sprint 6 | 1-2周 | 数据完善 |

---

## 开发规范提醒

- 所有新 DB 操作用 `AsyncSession` + `async/await`
- 所有新操作写 `audit_logs`（通过 `AuditService`）
- 后端新端点遵循：`router → service → db` 分层
- 前端新屏幕遵循：`index.tsx`（组合） + 子组件 + Context + api.ts 调用
- Mock data 的 `types.ts` 新字段同步更新 `mock_ashare.ts` 和 `mock_crypto.ts`
- 每次迁移后运行 `alembic upgrade head`
- 新端点补充到 `frontend/src/lib/api.ts`
