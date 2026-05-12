# 2026-05-11 — Phase 2 第四项：未来函数 / 前视最小规则

## 目标

在「结构化 DSL + 接口 AST」之外，增加**最小**未来数据与前视检测，对应计划：禁止依赖「当前调仓日之后才可知」的典型写法与字段命名。

## DSL 层（`validate_spec_semantics`）

- 对 **`filters[].field`** 做小写子串扫描，命中即拒绝，例如：`_t+`、`t+1`、`next_`、`forward_`、`_fwd`、`future_`、`lead_`、`tomorrow`。  
- 意图：拦截显式「下一期收益」「次日收盘价」等列名进入受控 spec（与 `STRATEGY_SPEC_SYSTEM_PROMPT` 中新增文案一致）。

## 生成代码层（`validate_generated_strategy_ast` 前置）

在类接口校验之前，对整棵 **`ast`** 做 `walk`，拦截常见前视模式（仅常量/一元负号可判定，避免误伤动态表达式）：

| 模式 | 规则 |
|------|------|
| `.shift(...)` | 首位置参数为严格负数，或 `periods` / `n` / `period` 关键字为严格负数 → **拒绝** |
| `.pct_change(...)` / `.diff(...)` | 同上（首参或 `periods`/`n`/`period` 为负）→ **拒绝** |
| `np.roll(..., -k)` / `roll(..., -k)` | 第二位置参为严格负数 → **拒绝** |

正数 `shift(1)`、`pct_change(20)`（mock 模板中的动量）等仍允许。

## 提示词

- **`STRATEGY_GENERATION_SYSTEM_PROMPT`**：新增第 6 条，明确禁止负 `shift` / 负周期 `pct_change`/`diff` / 负 `np.roll`。  
- **`STRATEGY_SPEC_SYSTEM_PROMPT`**：补充「勿用未来才可观测的 filter 字段名」与 position_rules 段落恢复并存。

## 流水线

- `static_check` 的 `detail.checks` 增加 **`future_data_guard`**（与 `ast.parse` 等并列，表示本项已在 `_generate_code` 内执行）。

## 测试

- `tests/domains/test_strategy_generation_validate.py`：`next_close` filter、负 `shift`、负 `pct_change`、正 `shift` 通过等用例。  
- 手工确认 **`_MOCK_STRATEGY_TEMPLATE`** 仍通过 `validate_generated_strategy_ast`。  
- 全量：`python -m pytest tests/ -q`（当前 **64 passed**）。

## 局限（刻意保持「最小」）

- 不分析动态下标、不扫字符串内代码、不覆盖所有 pandas 前视 API（如 `bfill` 误用等）。  
- 更严的未来函数与数据血缘在 Phase 3 / 后续任务扩展。
