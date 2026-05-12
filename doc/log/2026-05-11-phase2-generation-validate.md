# 2026-05-11 — Phase 2 第三项：策略生成结果校验

## 目标

在 Pydantic 结构校验之外，补齐计划中的三类校验：

1. **字段 / 业务语义**：DSL 与任务上下文（`risk_profile`、`market`）一致。  
2. **参数范围**：典型因子参数（如 `window` / `lookback`）落在合理区间。  
3. **策略接口**：生成 Python 在 AST 层面满足当前流水线所约定的类形态（兼容旧版 `RuleBasedStrategy` 提示词与新版 `BaseStrategy` 运行时）。

## 实现位置

- **`app/domains/strategy/generation_validate.py`**
  - `validate_spec_semantics(spec, *, risk_profile, market)`  
    - `risk_profile` ∈ {conservative, balanced, aggressive}。  
    - `market` ∈ {A, US, HK, crypto}（空字符串跳过，避免误伤）。  
    - `position_rules.max_single_name_weight` 不得超过该档位的单票上限（与 prompt 中 conservative/balanced/aggressive 一致）。  
    - `risk_rules.max_portfolio_drawdown` 不得超过该档位的回撤上限（与 `_MAX_DD_CAPS` 对齐）。  
    - 因子名：`^[a-zA-Z][a-zA-Z0-9_]{0,63}$`。  
    - 因子 `params` 中 `window` / `lookback` / `days` / `period`：数值且 ∈ [1, 252]。  
  - `validate_generated_strategy_ast(code)`  
    - `ast.parse`；至少一个 `class`。  
    - 若基类名为 `RuleBasedStrategy`：需定义 `generate_signals`、`risk_check`。  
    - 若基类名为 `BaseStrategy`：需定义 `generate_signals`、`rebalance`（与 `runtime.BaseStrategy` 对齐，便于后续接入真实回测）。

## 与流水线的衔接

- **`StrategyGenerationService._generate_code`**  
  - 在 `parse_strategy_generation_spec` 之后立刻调用 `validate_spec_semantics`；失败包装为 `LLMException("strategy DSL semantic validation failed: …")`。  
  - 在代码脱敏（去 markdown fence）之后调用 `validate_generated_strategy_ast`；失败包装为 `LLMException("generated strategy code validation failed: …")`。  
- **`run_pipeline` 静态检查阶段**  
  - 不再重复 `ast.parse`；`static_check` 的 `detail.checks` 更新为 `["ast.parse", "dsl_semantics", "strategy_interface"]`，表示上述校验已在生成阶段完成。

## 测试

- **`tests/domains/test_strategy_generation_validate.py`**：语义拒绝用例（超重、超回撤、非法 window、非法 market）、AST 接受/拒绝用例。  
- 全量：`cd backend && python -m pytest tests/ -q`（当前 **60 passed**）。

## 后续（未实现）

- **未来函数 / 数据泄露**：对应 Phase 2 下一项；需在 DSL 或代码层增加对「禁止引用未来字段」的规则（可结合静态分析或白名单列名）。  
- **与真实回测联动**：生成类仍为提示词中的 `RuleBasedStrategy`，与 `DailyBacktestEngine` 内置 `BaseStrategy` 尚未统一，后续任务将替换 mock 回测并逐步统一接口。
