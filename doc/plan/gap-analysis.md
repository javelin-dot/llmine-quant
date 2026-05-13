# LLMine Quant — 前后端差距分析与问题清单

> 分析日期：2026-05-13  
> 分析范围：完整主交易流程（策略生成 → 回测 → 模拟盘 → 审批 → 实盘）

---

## 一、主交易流程概述

```
用户提示词
    ↓
策略生成（LLM）
    ↓
回测验证（IS/OOS + Walk-Forward + 敏感性）
    ↓
模拟盘运行（Paper Trading EOD）
    ↓
交易审批（Execution Approval + Pre-Trade Checks）
    ↓
风控门控（Risk Engine + Circuit Breakers）
    ↓
实盘执行（Order Book + Fill Management）
    ↓
审计追踪（Audit Logs + Explain）
```

---

## 二、P0 — 完全阻断流程（立即修复）

### P0-1：认证系统缺失

**问题**  
- `app/domains/identity/models.py` 定义了 User/Organization/Role/Session 并有迁移文件
- 但**所有 API 路由无鉴权 middleware**
- 无登录端点（`POST /auth/login`）
- `get_actor_id()` 在 `core/tracing.py` 从 HTTP header 读取，但前端 `api.ts` 从未附加任何 token
- 前端无登录页面，无 token 存储/刷新逻辑

**影响**  
任何人可以不验证身份调用任意接口，包括创建策略、审批订单、触发熔断。

**文件**  
- `backend/app/core/security.py` — JWT 工具已写但未挂载
- `backend/app/api/v1/router.py` — 无全局鉴权依赖
- `frontend/src/lib/api.ts` — 无 Authorization header

---

### P0-2：WebSocket 不可用（实时推送断路）

**问题**  
后端 `/ws/events` 和 `/ws/strategy-events` 只回显 pong，从不主动推送事件；策略生成管线写数据库但**不广播到 WS 客户端**；前端**无任何 WebSocket 客户端代码**。

**影响**  
- 策略生成进度无法实时展示（前端只能轮询）
- 风控告警、熔断触发无法实时通知前端
- 执行状态（订单成交/拒绝）无法实时更新

**文件**  
- `backend/app/core/websocket.py` — `manager.broadcast()` 方法存在但从未被服务层调用
- `backend/app/services/strategy_generation.py` — 流程完成后未调用 WS 广播
- `frontend/src/App.tsx` — 无 `useEffect` 建立 WS 连接

---

### P0-3：策略→回测 UI 断链

**问题**  
- App.tsx 支持 `onNavigate('backtest:strategyId=abc')` 跳转并携带 strategyId
- 但 `Backtest` 屏幕的 `initialStrategyId` prop **没有被任何子组件使用**来预填策略选择
- 用户在策略工厂完成生成后，无法直接在回测页面看到该策略并启动回测
- 回测创建 payload 中 `strategyName` 是字符串，未关联到数据库中的 `strategy_id`

**文件**  
- `frontend/src/screens/Backtest/index.tsx`
- `frontend/src/App.tsx:108`

---

## 三、P1 — 关键功能缺失

### P1-1：8 个业务 API 模块返回硬编码假数据

以下模块的 `/overview` 端点全部返回**模块顶部定义的 Python 常量**，与数据库完全解耦：

| 模块 | 文件 | 说明 |
|------|------|------|
| Execution | `api/v1/execution.py` | 审批列表、订单簿、预交易检查、滑点指标全硬编码 |
| Explain | `api/v1/explain.py` | 信号头、归因瀑布、决策链、血缘图全硬编码（固定为贵州茅台） |
| Risk | `api/v1/risk.py` | 风险指标、VaR、熔断器状态、策略流全硬编码 |
| Portfolio | `api/v1/portfolio.py` | NAV、分配、相关矩阵、集中度全硬编码 |
| Audit | `api/v1/audit.py` | 审计日志、Actor统计、工具注册全硬编码 |
| Security | `api/v1/security.py` | Vault密钥、AI权限矩阵、提款规则全硬编码 |
| Collaboration | `api/v1/collaboration.py` | 评审列表、A/B测试、审批流程全硬编码 |
| Dashboard | `api/v1/dashboard.py` | 市场指数、Portfolio指标、Agent状态全硬编码 |

**影响**：前端展示的数据与真实业务状态完全脱钩，系统形似有效却无实际价值。

---

### P1-2：7 个领域的数据库表无迁移文件

以下领域存在完整的 SQLAlchemy 模型但**没有对应的 Alembic 迁移**，表不存在于数据库中：

| 领域 | 模型文件 | 缺失的表 |
|------|---------|---------|
| Portfolio | `domains/portfolio/models.py` | `portfolios`, `accounts`, `positions`, `cash_balances`, `nav_snapshots`, `rebalance_proposals` |
| Risk (live) | `domains/risk/models.py` | `risk_rules`, `risk_checks`, `risk_breaches`, `circuit_breakers`, `var_history` |
| Execution (live) | `domains/execution/models.py` | `approvals`, `orders`, `fills`, `execution_metrics`, `agent_traces` |
| Security | `domains/security/models.py` | 密钥库、安全事件等表 |
| Collaboration | `domains/collaboration/models.py` | 评审、版本差异、A/B测试等表 |
| Explain | `domains/explain/models.py` | 信号历史、归因记录等表 |

**注**：`audit_logs` 表虽有迁移，但 `audit.py` API 返回硬编码而非查询该表。

---

### P1-3：操作型接口是空壳

以下 POST 端点接受请求但**无任何业务逻辑**，仅返回字符串状态：

| 端点 | 文件 | 当前行为 |
|------|------|---------|
| `POST /execution/approvals/{id}/approve` | `execution.py:129` | 返回 `{"status": "approved"}` |
| `POST /execution/approvals/{id}/reject` | `execution.py:135` | 返回 `{"status": "rejected"}` |
| `POST /risk/circuit-breakers/{level}/trigger` | `risk.py:143` | 返回 `{"status": "triggered"}` |
| `POST /risk/circuit-breakers/{level}/recover` | `risk.py:149` | 返回 `{"status": "recovery_requested"}` |
| `POST /portfolio/rebalance/{id}/approve` | `portfolio.py:117` | 返回 `{"status": "approved"}` |

**影响**：所有"审批"、"熔断"等高权限操作实际上什么都不做。

---

### P1-4：Paper Trading 无前端界面

**问题**  
- `api.ts` 中 `api.paper.*` 定义了完整的 8 个调用（createAccount/positions/orders/fills/nav/breaches/runEod）
- 后端 `api/v1/paper.py` 和 `services/paper_trading.py` 是 DB 驱动的完整实现
- 但前端**无 Paper 屏幕**，`Screen` 类型不包含 `'paper'`，侧边栏无入口

**文件**  
- `frontend/src/App.tsx:15` — Screen 类型缺少 `'paper'`
- `frontend/src/screens/` — 无 `Paper/` 目录

---

## 四、P2 — 功能不完整

### P2-1：前端 api.ts 缺少对已存在后端端点的调用

后端已实现但前端 `api.ts` 未暴露：

| 端点 | 后端文件 |
|------|---------|
| `GET /strategies/templates` | `strategies.py:282` |
| `GET /strategies/{id}/events` | `strategies.py:427` |
| `POST /strategies/{id}/transition` | `strategies.py:400` |
| `POST /strategies/` | `strategies.py:560` |
| `GET /data/market-bars` | `data.py:194` |
| `POST /data/market-bars/import/csv` | `data.py:155` |
| `POST /data/market-bars/import/akshare` | `data.py:175` |
| `GET /data/features` | `data.py:252` |
| `GET /data/lineage` | `data.py:220` |
| `GET /data/lineage/runs/{id}` | `data.py:299` |
| `POST /execution/approvals/{id}/approve` | `execution.py:129` |
| `POST /execution/approvals/{id}/reject` | `execution.py:135` |
| `POST /risk/circuit-breakers/{level}/trigger` | `risk.py:143` |
| `POST /portfolio/rebalance/{id}/approve` | `portfolio.py:117` |

---

### P2-2：策略运行时未实现

**问题**  
- `app/domains/strategy/runtime.py` 有抽象基类，核心方法 `execute()` / `generate_signals()` 抛 `NotImplementedError`
- LLM 生成的策略代码（Python 文本）无法被回测引擎直接执行
- `DailyBacktestEngine`（`services/daily_backtest.py`）使用配置驱动逻辑，不执行动态代码

**影响**：LLM 生成的策略代码永远不会真正运行，只是文本存储。

---

### P2-3：前端 Context 无状态管理

**问题**  
11 个 Context 文件（`DashboardContext.tsx` 等）全部是 12 行的 pass-through：

```typescript
const DashboardContext = createContext<MockData['dashboard'] | null>(null)
export const DashboardProvider = DashboardContext.Provider
```

无加载状态、无错误处理、无自动刷新、无乐观更新。

**影响**：任何网络错误导致数据 null，屏幕永远显示 "Loading..."。

---

### P2-4：Dashboard 类型合约不一致

**问题**  
- `api.ts:334` 定义 `type DashboardOverview = MockData['dashboard']`
- 但 `MockData['dashboard']` 不包含 `meta`、`system`、`modals` 字段
- App.tsx 读取 `d.meta`、`d.system`、`d.modals` — 在 mock fallback 时这些字段为 `undefined`
- 后端 `DashboardOverview` schema 包含 `meta + system + modals + 业务字段`，是一个超集

**文件**  
- `frontend/src/lib/api.ts:334`
- `backend/app/schemas/dashboard.py`

---

### P2-5：Explain 屏幕无法查看真实信号决策链

- `explain.py` 信号固定写死为贵州茅台 (`600519`)，与真实策略信号完全无关
- 无 `GET /explain/{signal_id}` 端点支持按信号查询
- 前端 Explain 屏幕无法从 Execution/Strategy 页面跳入并查看特定信号的解释

---

### P2-6：Audit 日志未从数据库读取

- `audit_logs` 表有迁移，`AuditService` 会写入记录（如策略更新/删除时）
- 但 `audit.py` API 返回硬编码的 5 条日志，从不查询 `audit_logs` 表
- 实际发生的操作永远不会反映在 Audit 屏幕

---

## 五、P3 — 提升项

### P3-1：Agent Orchestration 断路

- `services/agent_orchestrator.py` 实现了多 Agent 协作框架
- `api/v1/agents.py` 提供 `/overview` 和 `/tasks` 端点
- 但 Orchestrator 未被任何业务流程调用，Agent 任务状态是孤立数据

### P3-2：LLM 状态无监控接口

- 后端 `config.py` 有 `llm_source`（explicit/claude_code/mock）
- 无 `GET /api/v1/llm/status` 端点
- 前端无法感知 LLM 是否可用，用户不知道是否在 mock 模式运行

### P3-3：策略生成进度只能轮询

- 前端 Strategy 屏幕通过 `setInterval` 轮询 `GET /strategies/tasks/{id}`
- 后端策略生成管线写 PipelineEvent 到 DB，但不通过 WS 推送
- 建议：管线完成各阶段时 `manager.broadcast(topic="strategy-events", ...)`

### P3-4：回测历史列表无 UI

- `GET /backtests/` 返回完整的历史回测列表（`BacktestTaskListPayload[]`）
- `api.backtest.list()` 已定义
- 但 Backtest 屏幕无历史列表组件，无法选择历史回测对比

### P3-5：数据导入无 UI

- `POST /data/market-bars/import/akshare` 支持按股票代码批量拉取行情
- `POST /data/market-bars/import/csv` 支持 CSV 导入
- Data 屏幕无导入按钮/表单，行情数据无法从 UI 管理

---

## 六、已完整实现的模块（勿动）

以下模块前后端均已完整实现，不在此次修复范围：

| 模块 | 状态 |
|------|------|
| 策略生成（LLM pipeline） | 后端完整，前端 AIForge 界面完整 |
| 回测执行（DailyBacktest） | 后端完整，前端 Backtest 屏幕完整 |
| Walk-Forward / 敏感性分析 | 后端完整，前端已集成 |
| Paper Trading 后端 | 后端完整（DB驱动），前端缺失 |
| 市场数据导入（AKShare） | 后端完整，前端缺入口 |
| Feature Store + Lineage | 后端完整，前端只展示静态 DAG |
| 所有前端屏幕 UI 组件 | 11 个屏幕全部完成深度重构 |
