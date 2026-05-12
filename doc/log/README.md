# 工作日志（doc/log）

按日期记录实现要点、核心数据流与设计决策，便于回溯与 onboarding。

| 日期 | 文件 | 摘要 |
|------|------|------|
| 2026-05-11 | [phase2-real-backtest.md](./2026-05-11-phase2-real-backtest.md) | Phase 2：策略生成接入 `DailyBacktestEngine` 真实落库回测 |
| 2026-05-11 | [phase2-future-leak-guard.md](./2026-05-11-phase2-future-leak-guard.md) | Phase 2：DSL 字段名 + 生成代码 AST 前视最小规则 |
| 2026-05-11 | [phase2-generation-validate.md](./2026-05-11-phase2-generation-validate.md) | Phase 2：策略生成语义校验 + 生成代码 AST 接口校验 |
| 2026-05-11 | [phase2-llm-dsl.md](./2026-05-11-phase2-llm-dsl.md) | Phase 2：LLM 结构化输出收窄为 `StrategyGenerationSpec`，再生成策略代码 |
