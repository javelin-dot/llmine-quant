# 执行进度

## 当前阶段

- 当前阶段：Phase 4 — 模拟盘闭环（已完成）→ 即将进入 Phase 5
- 当前目标：Phase 4 全部任务完成；下一阶段为 Phase 5 实盘前安全审批
- 当前状态：Phase 4 全绿（86 backend pytest pass + 前端 build 通过 + live API 验证），等待 Phase 5 启动

## 自动推进规则

后续执行时按以下规则推进：

1. 先读取本文件。
2. 找到 `当前阶段` 对应的阶段文档。
3. 从该阶段文档中选择第一个未完成的任务执行。
4. 每完成一个任务，更新对应阶段文档的勾选状态。
5. 如果阶段验收标准全部满足，更新本文件的 `当前阶段` 到下一阶段。
6. 每次代码变更后运行相关测试或构建；如果无法运行，记录原因。
7. 不跳阶段，除非用户明确要求调整优先级。

## 阶段状态总览

| 阶段 | 名称 | 状态 | 说明 |
|------|------|------|------|
| Phase 0 | 前端高保真壳层与 11 屏重构 | **已完成** | 全部屏幕 war-room 风格重构完毕，构建通过 |
| Phase 1 | 真实 Research MVP | **已完成** | 真实数据导入、日频回测、指标计算、API 落库、测试覆盖 |
| Phase 2 | AI 策略生成接入真实回测 | **已完成** | DSL/校验/未来函数/真实回测/关联/前端/失败路径/E2E 全部完成 |
| Phase 3 | 可靠性与可解释性 | **已完成** | IS/OOS、Walk-forward、敏感性、过拟合、Feature Store、血缘、解释、报告 API、前端类型；后端 79 passed |
| Phase 4 | 模拟盘闭环 | **已完成** | 7 张 paper_* 表 + 引擎 + API + Celery beat；后端 86 passed |
| Phase 5 | 实盘前准备 | 未开始 | Broker 适配、HITL 审批、kill switch、审计 |

## Phase 0 前端里程碑（已完成）

- [x] 11 个功能页面全部完成 war-room 风格深度重构
  - [x] Dashboard、Strategy、Backtest、Explain、Portfolio
  - [x] Execution、Risk、Data、Security、Collaboration、Audit
- [x] App.tsx 纯壳化：仅保留 sidebar + topbar + screen switcher + modals
- [x] 全局设计系统：GlassCard、status-dot、pulseDot、status-tag、dashFade 动画
- [x] 双市场 Mock 数据层：A股 (`mock_ashare.ts`) / Crypto (`mock_crypto.ts`)
- [x] ECharts 多图表模式验证：多 grid、IS/OOS 分离、渐变线、SVG sparkline
- [x] 构建验证：`npm run build` 通过（chunk size 警告为 ECharts 预期行为）

## Phase 1 后端里程碑（已完成）

- [x] 真实行情数据导入（AKShare / 本地 CSV）
- [x] `MarketBarDaily` 导入服务与最小清洗
- [x] 基础 A股交易规则标记（停牌、涨跌停、T+1 预留）
- [x] 最小策略运行接口 + 内置双均线示例策略
- [x] 日频回测循环 + 交易成本（佣金、印花税、滑点）
- [x] 核心指标计算（收益、回撤、Sharpe、胜率、换手）
- [x] `BacktestTask` / `BacktestRun` / `BacktestMetric` / `EquityPoint` 真实落库
- [x] `/api/v1/backtests` 从静态样例改为真实读取
- [x] 后端测试覆盖数据导入、示例策略回测、指标计算、API 端到端

## Phase 2 当前进度详情

### 已完成（前半段）

- [x] 定义策略生成结构化 schema：`StrategyGenerationSpec`（`generation_dsl.py`）
- [x] 将 LLM 输出限制为受控策略 DSL + Pydantic 校验（`build_strategy_metadata_bundle` 桥接落库）
- [x] 增加策略生成结果校验：DSL 语义校验 + 生成代码 AST 接口校验（`generation_validate.py`）
- [x] 增加未来函数检查：`filters.field` 未来名列拒绝 + `ast` 扫描负周期（`future_data_guard`）
- [x] 将 `StrategyGenerationService._mock_backtest()` 替换为真实回测任务（`DailyBacktestEngine.run_and_persist`）

### 已完成（后半段）

- [x] 将策略生成任务与 `BacktestTask`、`BacktestRun` 建立显式关联（外键 + 索引）。
  - `StrategyTask` 增加 `backtest_task_id`、`backtest_run_id` 字段与索引
  - `BacktestTask.strategy_version_id` 在流水线中传入真实 `StrategyVersion.id`
  - Alembic 迁移 `c029ffadba27` 已应用
  - 后端测试 66 passed
- [x] 在策略详情页/Strategy 屏幕展示生成代码、参数、真实回测指标和 pipeline event。
  - 前端 `StrategyDetailModal` 已展示代码、参数模板、风险规则、回测指标、pipeline events
  - 前端 `api.ts` 已更新 `StrategyDetail` 和 `getTask` 类型定义，对齐后端 schema
  - 前端构建通过
- [x] 增加失败路径：生成失败、校验失败、回测失败、风控失败均可追踪并落库。
  - `run_pipeline` except 块根据异常类型自动推断失败阶段（code_gen / static_check / backtest / risk / pipeline）
  - 每种失败都会写入 `PipelineEvent`（含 stage、event、error、exception_type）
  - 失败时 Strategy 状态回退为 `draft`
  - Audit log 记录 `stage={fail_stage}; {error_msg}`
  - WebSocket broadcast 推送带 stage 的失败事件
  - 后端测试 66 passed

### 待完成（后半段）

- [x] 增加端到端测试，覆盖自然语言生成 → 校验 → 真实回测的完整链路。
  - `tests/services/test_strategy_generation_e2e.py`：mock LLM 走完 NL→DSL→校验→真实回测，断言 StrategyTask/Strategy/Version/BacktestTask/Run/Metric/EquityPoint/PipelineEvent 全部落库。
  - 失败路径测试：无市场数据时 task 标记 failed、Strategy 回退 draft、PipelineEvent 含 *.failed。
  - 后端 `pytest` 68 passed。

## 下一步任务

Phase 4 已完成。进入 **Phase 5 实盘前准备**，按 `phase-5-live-readiness.md` 顺序执行：

> **Phase 5-1：抽象 broker adapter（统一下单/撤单/回报/持仓查询）。**
>
> 后续步骤：QMT/PTrade 占位适配 → live order draft 模型 → HITL 强制审批 → 权限分级（Research/Trader/Risk/Admin/Viewer）→ kill switch（global/strategy/account）→ 审计日志扩展 → paper-vs-live 一致性对账 → 实盘前检查清单 API → 测试覆盖审批/权限/熔断/审计。

## 构建与测试命令速查

```bash
# 前端（在 frontend/ 目录下）
npm run lint
npx tsc -b --force
npm run build

# 后端（在 backend/ 目录下，使用虚拟环境）
python -m pytest tests/ -q
```

## 最近记录

- **2026-05-13 Sprint 3**：Task 2.5 Audit 扩展 + Task 3.1 认证系统 + Task 3.2 WebSocket 实时推送。
  - **Audit**：`AuditService.log()` 增加 SHA-256 哈希链（`prev_hash` → `curr_hash`）；新增 `GET /audit/verify`（链完整性验证）、`GET /audit/export`（CSV 下载）、`GET /audit/actor-stats?limit=N`、`GET /audit/logs?action=xx` 支持 action 过滤。
  - **Auth 后端**：新建 `app/api/v1/auth.py`（POST /auth/login OAuth2PasswordRequestForm，POST /auth/refresh，POST /auth/logout，GET /auth/me）；`app/core/auth_deps.py`（`get_current_user` / `get_optional_user` FastAPI Depends）；`python-multipart` 依赖已加入。
  - **Auth 前端**：`api.ts` 新增 `authStore`（localStorage token 管理），`getJson/postJson/putJson/deleteJson` 注入 `Authorization: Bearer`，监听 `llmine:unauthorized` 事件触发退出；新增 `api.auth.{login,logout,refresh,me}` 方法；新建 `src/screens/Login/index.tsx`（登录表单）；`App.tsx` 增加 `currentUser` / `authChecked` 状态，优先显示 Login，顶栏增加用户名与退出按钮；Login screen CSS 写入 `prototype.css`。
  - **WebSocket**：`ws.py` 新增 `/ws/execution-events` 和 `/ws/risk-events` 端点；`execution.py` approve/reject 后 broadcast `execution-events`；`risk.py` trigger/recover 后 broadcast `risk-events`；前端新建 `src/lib/ws.ts`（`createWsClient` + 自动重连 + 事件分发，singleton：`strategyWs/executionWs/riskWs`）；`App.tsx` 登录后 connect，退出/组件卸载时 disconnect。
  - 测试：新增 `TestAuth`（login 成功/错误密码/未知用户）；89 passed。

- **2026-05-13 Sprint 2**：Task 2.1 缺失迁移补齐（+26 表）+ Task 2.2 Execution DB 化 + Task 2.3 Risk DB 化 + Task 2.4 Portfolio DB 化。
  - 新增 2 个 Alembic 迁移：`20260513_000001`（execution/risk/portfolio，17 张表）+ `20260513_000002`（security/collaboration/explain，13 张表），数据库共 70 张表。
  - `execution.py`：approve/reject 写 `approvals` 表 + `audit_logs`，overview 从 DB 读 approvals/orders/agent_traces；新增 `GET /execution/approvals`。
  - `risk.py`：header/budgets/var/circuits/policy/breaches 全部从 DB 读；trigger/recover 写 `circuit_breakers` 表 + `audit_logs`。
  - `portfolio.py`：NAV 从 `nav_snapshots` 读，rebalance 从 `rebalance_proposals` 读；approve 写 `rebalance_proposals` 表 + `audit_logs`；新增 `GET /portfolio/rebalance`。
  - `scripts/seed_dev_data.py`：补充 `_seed_circuit_breakers` / `_seed_risk_budgets`，4 条 L1-L4 熔断 + 5 条风险预算已植入 dev DB。
  - 测试：测试文件更新为 DB 感知（seeded_circuit_l2、seeded_approval、seeded_rebalance fixtures）；86 passed。

- **2026-05-13**：执行全局差距分析（gap-analysis.md + roadmap.md）。扫描范围：所有 11 个后端 API 模块、13 个前端 Context、完整数据库迁移链、前后端 API 合约对比。核心发现：8 个 API 模块返回硬编码数据、7 个领域表无迁移、Paper Trading 前端缺失、Dashboard 类型合约错误、WebSocket 无客户端、Backtest 未接 strategyId、14 个后端端点未在 api.ts 暴露。详见 `doc/plan/gap-analysis.md`（问题清单）和 `doc/plan/roadmap.md`（分 Sprint 修复计划）。

- **2026-05-13**：Phase 4 完成。新增 7 张 paper_* 表（迁移 49c0724c647e）；`PaperTradingEngine` 覆盖 mark / signal / pre-check / match / nav / breach；当日收盘 + 动态滑点撮合（同回测 cost）；幂等 last_processed_date；API `/paper/accounts/*`；Celery + Redis beat (`paper-trading-eod` cron `15:30 Mon-Fri`)；前端 `api.paper.*` 客户端方法；后端测试 86 passed（+7）；frontend `tsc -b --force` + `npm run build` 通过；live API 验证账户创建与 EOD 写入 NAV/positions/orders 全链路。

- **2026-05-13**：Phase 3 全部完成。
  - Phase 3-1：IS/OOS 切分（migration c45d1fe90688，`BacktestMetric.segment`、`EquityPoint.phase` 自动标记）。
  - Phase 3-2：Walk-forward（migration 65eb0814322d，`walk_forward_folds` 表，`run_walk_forward` 引擎方法，POST `/backtests/walk-forward`）。
  - Phase 3-3：参数扰动 + 滑点敏感性（migration a00a9a166a85，`sensitivity_runs` 表，dual_ma 网格扰动 + 滑点 5 点，POST `/backtests/sensitivity`）。
  - Phase 3-4：过拟合评分（4 组件加权 → 0-100，写回 `BacktestMetric.oos_score / overfit_level`，GET `/backtests/{task}/overfit`）。
  - Phase 3-5+6：Feature Store + 数据血缘（migration 61868637158e，`feature_sets / feature_usages / lineage_nodes / lineage_edges`；策略生成流水线自动写入；GET `/data/features`、`/data/features/usages`、`/data/lineage/runs/{run}`）。
  - Phase 3-7：规则解释 — 新表 `backtest_trades`（migration dbab78f9c309），run_and_persist 写入含 reason 的成交；GET `/backtests/{task}/trades`。
  - Phase 3-8：统一报告 API — GET `/backtests/{task}/report` 一次性返回 summary + walk-forward + sensitivity + overfit + trades + featureUsage + 血缘节点/边数。
  - 前端：`frontend/src/lib/api.ts` 暴露所有新端点的 TS 类型与方法；`npx tsc -b --force` + `npm run build` 通过。
  - 测试：后端 79 passed（66+2+4+2+2+1+2 = +13 over Phase 2）；live API 全链路验证。
- **2026-05-13**：Phase 2 收尾完成。新增 `tests/services/test_strategy_generation_e2e.py` 覆盖完整 NL→DSL→校验→真实回测→落库链路与失败路径；后端测试 68 passed。Phase 2 全部勾选，当前阶段切换为 Phase 3。
- **2026-05-12**：前端 11 屏全部完成 war-room 深度重构；构建通过；App.tsx 纯壳化。当前计划文档重写以反映前端里程碑与 Phase 2 前后半段分界。
- 2026-05-11：Phase 2 第五项：策略生成流水线用 `DailyBacktestEngine.run_and_persist` 替代 `_mock_backtest`；`discover_default_research_universe` + `spec_to_dual_ma_params`；`task.result` 含 `backtestTaskId`/`backtestRunId`；日志 `doc/log/2026-05-11-phase2-real-backtest.md`。
- 2026-05-11：Phase 2 第四项：DSL `filters.field` 未来名列拒绝；生成代码 `ast` 扫描负 `shift`/`pct_change`/`diff` 周期与负 `roll`；提示词补充；`future_data_guard`；日志 `doc/log/2026-05-11-phase2-future-leak-guard.md`。
- 2026-05-11：Phase 2 第三项：`generation_validate.py` 增加 DSL 语义校验与生成代码 AST 接口校验；接入 `_generate_code`；单测 `tests/domains/test_strategy_generation_validate.py`；工作日志见 `doc/log/2026-05-11-phase2-generation-validate.md`。
- 2026-05-11：Phase 2 第二项：策略生成流水线改为「先 `StrategyGenerationSpec` 结构化输出 + Pydantic 校验，再附加 spec 生成 Python」；`build_strategy_metadata_bundle` 桥接落库；工作日志见 `doc/log/2026-05-11-phase2-llm-dsl.md`。
- 2026-05-11：Phase 2 首项落地：`app/domains/strategy/generation_dsl.py` 定义 `StrategyGenerationSpec` 及 `parse_strategy_generation_spec`；单测 `tests/domains/test_strategy_generation_dsl.py`。
- 2026-05-11：确认 Phase 1 后端测试已覆盖数据导入、日频回测与指标、API 与 CSV 端到端；`pytest` 全绿；计划文档勾选完毕，当前阶段进入 Phase 2。
- 2026-05-12：根据项目现状完成阶段路线拆解，建立 `doc/plan` 执行计划。
- 2026-05-12：完成真实行情导入路径、`MarketBarDaily` 导入服务、最小清洗与基础 A 股交易规则标记。
- 2026-05-12：完成最小策略运行接口，包含初始化、信号生成、调仓目标和 runner。
- 2026-05-12：完成内置双均线示例策略与策略工厂。
- 2026-05-12：完成日频回测循环，支持读取 `MarketBarDaily`、按交易日运行内置策略、撮合目标权重并更新现金、持仓和权益曲线。
- 2026-05-12：完成交易成本模型，支持双边佣金、最低佣金、卖出印花税和买卖滑点。
- 2026-05-12：完成核心指标计算，回测结果返回累计收益、年化收益、最大回撤、Sharpe、胜率和换手。
- 2026-05-12：完成真实落库流程，`run_and_persist` 会写入 `BacktestTask`、`BacktestRun`、`BacktestMetric` 和 `EquityPoint`。
- 2026-05-12：完成回测 API 改造，`POST /api/v1/backtests` 会运行并落库，`GET /api/v1/backtests/{task_id}` 从真实表返回运行、指标和权益曲线。
