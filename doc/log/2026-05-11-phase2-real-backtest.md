# 2026-05-11 — Phase 2 第五项：真实回测替代 mock

## 目标

用 **`DailyBacktestEngine.run_and_persist`** 替代 **`StrategyGenerationService._mock_backtest()`**，使策略生成流水线在通过静态校验后，对**真实落库的日线**跑一次可复现的研究回测，并写入 `BacktestTask` / `BacktestRun` / `BacktestMetric` / `EquityPoint`。

## 设计取舍

- **不执行 LLM 生成的 Python**：研究引擎当前只支持受控内置策略（`dual_ma`）。生成代码仍落 `StrategyVersion`，回测阶段使用 **DSL → `dual_ma` 参数** 的受控映射（`spec_to_dual_ma_params`），从动量类因子的 `window`/`lookback` 等推断短长周期，其它类型采用保守默认。
- **标的与区间**：`discover_default_research_universe(session, min_bars=30)` 在 `MarketBarDaily` 中选 **行数足够** 的一只标的，并取该标的的 **min/max trade_date** 作为 `[start_date, end_date]`。若无数据则 **`LLMException`**，提示先导入行情。
- **资金与成本**：`initial_cash=1e6`，`BacktestCostConfig()` 默认佣金/印花税/滑点（与 API 研究回测一致）。
- **与下游兼容**：`_backtest_result_to_pipeline_dict` 将 `DailyBacktestResult.metrics` 转成原 mock 使用的 **`sharpe` / `maxDd` / `annualReturn` / `oosScore` / `confidence`** 等键，并附加 **`backtestTaskId` / `backtestRunId` / `researchStrategy` / 起止日期**，供风控、`Strategy` 行更新与 `task.result` JSON 使用。`maxDd` 对引擎返回的负向最大回撤取幅度（与 `_check_risk` 阈值比较一致）。

## 代码路径

- **`app/services/strategy_generation_research.py`**：`spec_to_dual_ma_params`、`discover_default_research_universe`。
- **`app/services/strategy_generation.py`**：阶段 4 调用上述逻辑 + `DailyBacktestEngine.run_and_persist`；删除 `_mock_backtest` 与 **`random`** 依赖。

## 测试

- **`tests/services/test_strategy_generation_research.py`**：无数据 / 有数据下的 `discover` + `spec_to_dual_ma_params`。  
- 全量：`python -m pytest tests/ -q`（当前 **66 passed**）。

## 后续（第六项）

- 将 **`StrategyTask`** 与 **`BacktestTask`** 显式关联（外键或 JSON 字段、`strategy_version_id` 指向真实 `StrategyVersion.id` 等），并在 API/前端展示关联回测。
