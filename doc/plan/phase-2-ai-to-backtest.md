# Phase 2 - AI 策略生成接入真实回测

## 目标

把自然语言策略生成从 mock 回测接入真实回测任务，让策略生成结果可验证、可复现、可落库。

## 范围

- 策略生成 DSL 与结构化输出
- 生成结果校验（语义 + AST 接口 + 未来函数）
- 真实回测任务接入
- 生成任务与回测任务的关联与追踪
- 前端 Strategy 屏幕展示真实生成结果与回测指标
- 失败路径处理与端到端测试

## 任务清单

### 前半段（已完成）

- [x] 定义策略生成结构化 schema：策略类型、因子、过滤条件、调仓频率、仓位规则、风险规则。
- [x] 将 LLM 输出限制为受控策略 DSL 或受限模板参数。
- [x] 增加策略生成结果校验：字段校验、参数范围校验、策略接口校验。
- [x] 增加未来函数检查的最小规则：禁止使用当前调仓日之后的数据字段。
- [x] 将 `StrategyGenerationService._mock_backtest()` 替换为真实回测任务。

### 后半段（已完成）

- [x] 将策略生成任务与 `BacktestTask`、`BacktestRun` 建立显式关联（外键或关联表）。
- [x] 在策略详情页/Strategy 屏幕展示生成代码、参数、真实回测指标和 pipeline event。
- [x] 增加失败路径：生成失败、校验失败、回测失败、风控失败均可追踪并落库。
- [x] 增加端到端测试，覆盖自然语言生成到真实回测的完整链路。
  - `tests/services/test_strategy_generation_e2e.py` 覆盖 NL→DSL→校验→真实回测→落库
  - 同时覆盖失败路径：无市场数据时 task 标记 failed、Strategy 回退 draft、PipelineEvent 包含 *.failed
  - 后端测试 68 passed（66 旧 + 2 新）

## 验收标准

- [x] 用户输入自然语言策略后，系统生成受控策略定义。
- [x] 策略定义通过校验后自动创建真实回测任务。
- [x] 策略任务完成后能查看真实回测结果。
- [x] mock LLM 和真实 LLM provider 均可走同一流程。
- [x] 生成失败、校验失败、回测失败均有可查询记录。
- [x] 端到端测试覆盖自然语言输入 → DSL → 校验 → 代码生成 → 真实回测 → 结果返回。

## 风险

- 直接执行 LLM Python 代码风险高，必须优先使用受控 DSL 或模板。
- 生成策略的表达能力会暂时受限，但可以换取安全性和可复现性。
- 前端 Strategy 屏幕目前展示的是 mock 数据，接入真实数据后需要调整数据接口和加载状态。

## 关键文件

- `app/domains/strategy/generation_dsl.py` — `StrategyGenerationSpec` 定义与解析
- `app/domains/strategy/generation_validate.py` — DSL 语义校验与代码 AST 接口校验
- `app/domains/strategy/runtime.py` — 策略生成服务与真实回测接入
- `app/domains/strategy/models.py` — 策略生成任务模型
- `app/domains/backtest/models.py` — 回测任务/运行/指标模型
- `frontend/src/screens/Strategy/` — 前端策略屏幕（待接入真实数据）
