# Phase 3 - 可靠性与可解释性

## 目标

避免策略只在样本内好看，建立过拟合检测、样本外验证、数据血缘和信号解释能力。

## 任务清单

- [x] 增加样本内和样本外切分配置。
  - `DailyBacktestConfig.in_sample_end_date` 可选切分点；`__post_init__` 校验落在 [start, end)
  - `_segment_metrics` 分别计算 IS/OOS 指标，OOS 基线锚定到 IS 末端权益
  - `BacktestMetric` 新增 `segment` 列（all/is/oos），迁移 `c45d1fe90688`
  - `EquityPoint.phase` 按切分日自动标记 is/oos
  - API `BacktestCreateIn.inSampleEndDate`、`BacktestTaskResultOut.inSampleMetrics/outSampleMetrics/inSampleEndDate`、`BacktestEquityPointOut.phase`
  - 测试：`tests/services/test_daily_backtest.py` 新增 splits / invalid split；`tests/api/test_backtests.py` 新增 segment 端到端 + 400 拒绝；后端 72 passed
  - 本地 SQLite alembic upgrade head 已执行；live POST /api/v1/backtests/ + GET 验证 IS/OOS 数据正确返回
- [x] 实现 Walk-forward 回测流程。
  - 新表 `walk_forward_folds`（迁移 65eb0814322d），按 fold_index 索引；记录 train/test 起止与 return/sharpe/max_dd
  - `DailyBacktestEngine.run_walk_forward(folds, train_ratio)`：在单次全量回测的权益曲线上按等长切窗，每折再按 train_ratio 划分；OOS 基线锚定 train 末端
  - API `POST /api/v1/backtests/walk-forward`，返回每折 train/test 指标与父任务 ID
  - 测试：`tests/services/test_daily_backtest.py` 新增 folds 持久化 + 数据不足 400；`tests/api/test_backtests.py` 新增 walk-forward 端到端；后端 75 passed
  - live POST /api/v1/backtests/walk-forward 已跑通，DB walk_forward_folds 写入 4 行
- [x] 实现参数扰动分析。
- [x] 实现滑点敏感性分析。
  - 新表 `sensitivity_runs`（迁移 a00a9a166a85），区分 baseline / param / slippage 三类
  - `app/services/sensitivity.py`：dual_ma short/long ±1/±5 网格、滑点 0/+/-bps 五点；调用 `engine.run()` 不再二次落库 BacktestTask
  - API `POST /api/v1/backtests/sensitivity` 返回所有变体的指标
  - 测试：`tests/services/test_sensitivity.py` 校验 baseline + param + slippage 全部落库；后端 76 passed
  - live 12 个变体跑通（baseline + 8 param + 3 slippage）
- [x] 实现过拟合评分：IS/OOS 收益比、Sharpe 衰减、回撤一致性、参数稳定性。
  - `app/services/overfitting.py`：4 个组件——sharpe_decay / drawdown_consistency / walk_forward_continuity / param_stability；缺失组件自动跳过；平均 → 0-100 → low/medium/high
  - 直接复用 `BacktestMetric.oos_score / overfit_level` 列写回（无需新迁移）
  - API `GET /api/v1/backtests/{task_id}/overfit`
  - 测试：`tests/services/test_overfitting.py` 覆盖全组件 + 仅 baseline 退化路径；后端 78 passed
  - live API 返回 score=53 level=medium，组件 detail 展示比例
- [x] 建立最小 Feature Store：特征名、版本、依赖、计算时间点、是否验证。
  - `data.FeatureSet` 已有，迁移 `61868637158e` 新增 `kind/description/dependencies_json/computation_window` 列与 `feature_usages` 关联表
  - `app/services/feature_lineage.upsert_features_from_spec` 从 DSL 因子写入；`record_feature_usage` 绑定 StrategyVersion
  - API `GET /api/v1/data/features`、`GET /api/v1/data/features/usages`
- [x] 建立数据血缘记录：Raw -> Cleaned -> Feature -> Strategy -> Signal -> BacktestRun。
  - 同迁移建立 `lineage_nodes / lineage_edges`，新增 `ref_table / ref_id / backtest_run_id`
  - `app/services/feature_lineage.write_lineage_for_run` 自动构建链路
  - API `GET /api/v1/data/lineage/runs/{run_id}`
  - 接入策略生成流水线（best-effort，不阻断 pipeline）
- [x] 增加规则策略解释：命中条件、排序贡献、过滤原因。
  - 新表 `backtest_trades`（迁移 `dbab78f9c309`），run_and_persist 写入每笔成交（含 reason、cost、weight）
  - 内置 dual_ma 策略已生成自然语言 reason（`short_ma X above long_ma Y` 等）
  - API `GET /api/v1/backtests/{task_id}/trades`
- [x] 增加报告 API，输出回测摘要、风险摘要、解释摘要。
  - `GET /api/v1/backtests/{task_id}/report` 一次性返回 summary / walk-forward / sensitivity / overfit / trades / feature_usage / lineage 节点边数
  - 同时刷新 overfit 评分
  - live 验证 14 笔成交 + IS/OOS=medium overfit
- [x] 增加测试，覆盖 Walk-forward、过拟合评分和血缘记录。
  - `tests/services/test_daily_backtest.py` (8)、`test_overfitting.py` (2)、`test_sensitivity.py` (1)、`test_strategy_generation_e2e.py` (扩展 features+lineage 断言)
  - `tests/api/test_backtests.py` 新增 trades/report/walk-forward/IS-OOS/sensitivity 7 项；后端 79 passed

## 验收标准

- [x] 每个策略回测都能标记低/中/高过拟合风险。（`/backtests/{task_id}/overfit` 与 BacktestMetric.overfit_level）
- [x] 每个回测结果能追踪到使用的数据和特征版本。（FeatureUsage + LineageEdge/Node 写入并按 run_id 检索）
- [x] 策略报告能说明收益来源和主要风险来源。（`/backtests/{task_id}/report` 聚合 + trades.reason）

