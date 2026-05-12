# 执行进度

## 当前阶段

- 当前阶段：Phase 2 - AI 策略生成接入真实回测
- 当前目标：把自然语言策略生成从 mock 回测接入真实回测任务，使生成结果可验证、可复现、可落库。
- 当前状态：进行中

## 自动推进规则

后续执行时按以下规则推进：

1. 先读取本文件。
2. 找到 `当前阶段` 对应的阶段文档。
3. 从该阶段文档中选择第一个未完成的任务执行。
4. 每完成一个任务，更新对应阶段文档的勾选状态。
5. 如果阶段验收标准全部满足，更新本文件的 `当前阶段` 到下一阶段。
6. 每次代码变更后运行相关测试或构建；如果无法运行，记录原因。
7. 不跳阶段，除非用户明确要求调整优先级。

## 阶段状态

- [x] Phase 1 - 真实 Research MVP：`phase-1-research-mvp.md`
- [ ] Phase 2 - AI 策略生成接入真实回测：`phase-2-ai-to-backtest.md`
- [ ] Phase 3 - 可靠性与可解释性：`phase-3-reliability-explainability.md`
- [ ] Phase 4 - 模拟盘闭环：`phase-4-paper-trading.md`
- [ ] Phase 5 - 实盘前准备：`phase-5-live-readiness.md`

## 下一步任务

从 `phase-2-ai-to-backtest.md` 开始，优先执行（按文档顺序第一个未完成项）：

- [ ] 将策略生成任务与 `BacktestTask`、`BacktestRun` 建立关联。

（Phase 1 已全部完成；后端验证：`python -m pytest tests/ -q`。）

## 最近记录

- 2026-05-11：Phase 2 第五项：策略生成流水线用 `DailyBacktestEngine.run_and_persist` 替代 `_mock_backtest`；`discover_default_research_universe` + `spec_to_dual_ma_params`；`task.result` 含 `backtestTaskId`/`backtestRunId`；日志 `doc/log/2026-05-11-phase2-real-backtest.md`。
- 2026-05-11：Phase 2 第四项：DSL `filters.field` 未来名列拒绝；生成代码 `ast` 扫描负 `shift`/`pct_change`/`diff` 周期与负 `roll`；提示词补充；`future_data_guard`；日志 `doc/log/2026-05-11-phase2-future-leak-guard.md`。
- 2026-05-11：Phase 2 第三项：`generation_validate.py` 增加 DSL 语义校验（风险档位与单票权重/回撤上限、市场枚举、因子 window 等）与生成代码 AST 接口校验（`RuleBasedStrategy`+`generate_signals`/`risk_check` 或 `BaseStrategy`+`generate_signals`/`rebalance`）；接入 `_generate_code`；单测 `tests/domains/test_strategy_generation_validate.py`；工作日志见 `doc/log/2026-05-11-phase2-generation-validate.md`。
- 2026-05-11：Phase 2 第二项：策略生成流水线改为「先 `StrategyGenerationSpec` 结构化输出 + Pydantic 校验，再附加 spec 生成 Python」；`build_strategy_metadata_bundle` 桥接落库；Mock 按 schema 分发；工作日志见 `doc/log/2026-05-11-phase2-llm-dsl.md`。
- 2026-05-11：Phase 2 首项落地：`app/domains/strategy/generation_dsl.py` 定义 `StrategyGenerationSpec`（策略类型、因子、过滤、调仓频率、仓位与风险规则）及 `parse_strategy_generation_spec`；单测 `tests/domains/test_strategy_generation_dsl.py`。
- 2026-05-11：确认 Phase 1 后端测试已覆盖数据导入（`tests/services/test_market_data_import.py`、`tests/api/test_market_data_import.py`）、日频回测与指标（`tests/services/test_daily_backtest.py`）、API 与 CSV 端到端（`tests/api/test_backtests.py`）；`pytest` 全绿；计划文档勾选完毕，当前阶段进入 Phase 2。
- 2026-05-12：根据项目现状完成阶段路线拆解，建立 `doc/plan` 执行计划。
- 2026-05-12：完成真实行情导入路径、`MarketBarDaily` 导入服务、最小清洗与基础 A 股交易规则标记；下一步进入最小策略运行接口。
- 2026-05-12：完成最小策略运行接口，包含初始化、信号生成、调仓目标和 runner；下一步实现内置示例策略。
- 2026-05-12：完成内置双均线示例策略与策略工厂；下一步进入日频回测循环。
- 2026-05-12：完成日频回测循环，支持读取 `MarketBarDaily`、按交易日运行内置策略、撮合目标权重并更新现金、持仓和权益曲线；下一步实现交易成本。
- 2026-05-12：完成交易成本模型，支持双边佣金、最低佣金、卖出印花税和买卖滑点，并在成交记录中保留成本明细；下一步计算核心指标。
- 2026-05-12：完成核心指标计算，回测结果返回累计收益、年化收益、最大回撤、Sharpe、胜率和换手；下一步接入真实落库流程。
- 2026-05-12：完成真实落库流程，`run_and_persist` 会写入 `BacktestTask`、`BacktestRun`、`BacktestMetric` 和 `EquityPoint`，并通过 Alembic 迁移校验；下一步改造回测 API。
- 2026-05-12：完成回测 API 改造，`POST /api/v1/backtests` 会运行并落库，`GET /api/v1/backtests/{task_id}` 从真实表返回运行、指标和权益曲线；下一步补齐阶段后端覆盖和验收。
