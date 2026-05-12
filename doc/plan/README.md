# LLMine Quant 阶段计划索引

本目录用于承载项目后续执行计划。后续推进时，优先读取 `progress.md`，找到当前阶段第一个未完成任务，然后按对应阶段文档执行。

## 文档结构

- `progress.md`：当前进度、下一步任务、自动推进规则。
- `phase-1-research-mvp.md`：真实数据层与日频回测 MVP。
- `phase-2-ai-to-backtest.md`：AI 策略生成接入真实回测。
- `phase-3-reliability-explainability.md`：可靠性验证、过拟合检测、数据血缘与解释。
- `phase-4-paper-trading.md`：模拟盘闭环。
- `phase-5-live-readiness.md`：实盘前准备与安全审批。

## 总路线

1. 先补真实数据和真实回测。
2. 再把 AI 生成策略接入真实验证链路。
3. 再补可靠性、解释性和血缘追踪。
4. 然后进入模拟盘闭环。
5. 最后做实盘前的安全、审批和券商适配准备。

当前项目已有高保真前端、FastAPI API 骨架、策略任务和 Agent 任务表，但核心量化能力仍需要从真实数据、真实回测开始补齐。

