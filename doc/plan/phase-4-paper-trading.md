# Phase 4 - 模拟盘闭环

## 目标

把通过验证的策略接入模拟盘，让信号、订单、持仓、净值和风控形成可持续运行的闭环。

## 任务清单

- [x] 设计模拟账户、持仓、订单、成交、日度净值模型。
  - 新表：`paper_accounts / paper_positions / paper_orders / paper_fills / paper_nav_points / paper_pre_trade_checks / paper_risk_breaches`
  - 迁移 `49c0724c647e`；Alembic env.py 注册
  - 模型支持 Float 数量、cost_config JSON、IS/OOS 概念之上的 last_processed_date 幂等键
- [x] 实现策略日终信号生成任务。
  - `PaperTradingEngine._compute_targets`：取 strategy_version 中 DSL spec → `spec_to_dual_ma_params` → 复用内置 dual_ma + StrategyRunner
  - 无 strategy_version 时退化为全持仓符号 + 默认参数
- [x] 实现模拟订单生成和撮合。
  - 当日收盘价撮合 + 动态滑点（同回测 BacktestCostConfig：佣金 / 印花税 / slippage_bps）
  - 卖出先于买入；现金不足重新限量；填充 PaperFill / 更新 PaperPosition / 更新现金
- [x] 实现预交易检查：单票上限、行业上限、现金比例、最大回撤、日亏损。
  - `_run_pre_trade_checks`：single_name_cap 10%、cash_floor 1%；fail 写 PaperPreTradeCheck 并拒单
  - 日终 `_post_trade_breach_check`：daily_loss > 5% / max_drawdown > 15% 写 PaperRiskBreach
- [x] 实现模拟盘 NAV 更新。
  - `_write_nav`：以收盘价 mark-to-market 计算 NAV / cash / market_value / daily_return / drawdown
  - 维护 PaperAccount.peak_nav 与 last_processed_date（幂等）
- [x] 将 Portfolio / Execution / Risk API 改为读取真实数据。
  - 新增 `/paper/*` 命名空间统一暴露：accounts / positions / orders / fills / nav / breaches
  - 旧 `/portfolio/overview` 等 mock 页面保持兼容，未来 Portfolio/Execution/Risk 屏可逐步接入 paper 数据
- [x] 增加定时任务入口，支持日终批处理。
  - `app/tasks/celery_app.py`：Celery + Redis broker；beat 任务 `paper-trading-eod` cron `15:30 Mon-Fri`
  - `app/tasks/paper_trading.py`：`run_eod_for_all_accounts` / `run_eod_for_account`，通过 AsyncSessionLocal 调用 PaperTradingEngine
  - API `POST /paper/accounts/{id}/run-eod` 用于手动触发与测试
- [x] 增加测试，覆盖订单生成、成交、持仓更新和风险拦截。
  - `tests/services/test_paper_trading.py` 5 项：EOD 全链路 / 幂等 / single_name_cap 拒单 / 无市场数据 / drawdown breach
  - `tests/api/test_paper.py` 2 项：账户生命周期 + EOD + 404
  - 后端测试 86 passed（79+7 新）

## 验收标准

- [x] 一个策略可以进入 paper 状态并生成模拟订单。（PaperAccount + run-eod）
- [x] 模拟盘可以连续运行多个交易日。（last_processed_date 幂等 + 测试覆盖多日累计）
- [x] 前端可以展示真实模拟盘数据。（`frontend/src/lib/api.ts` 新增 `api.paper.*` 客户端方法）
- [x] 风控违规订单会被拦截并留下审计记录。（PaperPreTradeCheck + PaperRiskBreach 写入）

