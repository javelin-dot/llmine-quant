# 2026-05-11 — Phase 2：LLM 输出收窄为受控策略 DSL

## 背景

执行计划 `doc/plan/phase-2-ai-to-backtest.md` 第二项：在自由文本代码生成之前，要求模型先产出**可校验的结构化策略意图**，避免不可控 JSON 或随意字段进入落库与后续回测链路。

## 核心数据流（`StrategyGenerationService._generate_code`）

1. **结构化 DSL 优先**  
   - 调用 `LLMProvider.generate_structured`，`output_schema` 使用 `StrategyGenerationSpec.model_json_schema()`（`generation_dsl.strategy_generation_json_schema()`）。  
   - System/User 提示词：`STRATEGY_SPEC_SYSTEM_PROMPT` / `STRATEGY_SPEC_USER_PROMPT`（`app/integrations/llm/prompts.py`），约束 snake_case 键与业务含义（因子、过滤、between/in 形态、调仓频率、仓位与风险块）。

2. **硬校验**  
   - 返回 dict 经 `parse_strategy_generation_spec` → Pydantic `StrategyGenerationSpec`；失败则抛 `LLMException("strategy DSL validation failed: …")`，流水线失败可追踪。  
   - `ConfigDict(extra="forbid")` 在模型层禁止未知字段。

3. **与持久化字段的桥接**  
   - `build_strategy_metadata_bundle(spec, prompt_excerpt=…, display_seed=…)`（`generation_dsl.py`）把 DSL 压成原 `_update_strategy_from_meta` / `StrategyVersion` 使用的扁平键：  
     - `name` / `family` / `description` / `universe` / `frequency`：由首因子、filters 摘要、用户 prompt 片段推导；  
     - `params`：完整 `spec.model_dump()`，写入 `StrategyVersion.params_schema`；  
     - `riskRules`：`risk_rules` dict，写入 `risk_rules` 列。  
   - `expected_sharpe` / `expected_max_dd`：保留占位与风险上界信息，真实指标仍由后续真实回测（Phase 2 后续项）替换 mock。

4. **代码生成**  
   - 在原有 `STRATEGY_GENERATION_*` 用户提示末尾追加 `STRATEGY_SPEC_FOR_CODE_APPEND`，附上**已通过校验**的 `spec_json`，要求生成的 `RuleBasedStrategy` 子类与 DSL 一致（软约束，仍经 `ast.parse`）。

## Mock 与 CI

- `MockLLMProvider.generate_structured`：若 `output_schema.properties` 同时包含 `strategy_kind` 与 `factors`，返回固定的 `_MOCK_STRATEGY_SPEC`（合法 DSL）；否则仍返回旧版 `_MOCK_METADATA`，避免破坏其他潜在调用方。

## 测试

- `tests/domains/test_strategy_generation_dsl.py`：`build_strategy_metadata_bundle`、mock + `strategy_generation_json_schema` 校验闭环。  
- 全量：`cd backend && python -m pytest tests/ -q`。

## 计划文档更新

- `phase-2-ai-to-backtest.md`：第二项勾选完成。  
- `doc/plan/progress.md`：下一步指向「策略生成结果校验」等后续条目。

## 后续（未在本日志实现）

- 将 `_mock_backtest` 换为真实 `BacktestTask` / `DailyBacktestEngine`（同阶段后续任务）。  
- 在 DSL 之上增加语义校验（未来函数、参数范围与内置策略模板对齐等），对应 Phase 2 任务清单第三项及以后。
