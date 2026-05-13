# LLMine Quant 阶段计划索引

本目录用于承载项目后续执行计划。后续推进时，优先读取 `progress.md`，找到当前阶段第一个未完成任务，然后按对应阶段文档执行。

## 文档结构

- `progress.md`：当前进度、下一步任务、自动推进规则。
- `phase-0-frontend-foundation.md`：（记录在 `progress.md` 中）前端高保真壳层与 11 屏 war-room 重构。
- `phase-1-research-mvp.md`：真实数据层与日频回测 MVP。
- `phase-2-ai-to-backtest.md`：AI 策略生成接入真实回测。
- `phase-3-reliability-explainability.md`：可靠性验证、过拟合检测、数据血缘与解释。
- `phase-4-paper-trading.md`：模拟盘闭环。
- `phase-5-live-readiness.md`：实盘前准备与安全审批。
- `gap-analysis.md`：**2026-05-13 全局差距分析**，从完整主流程出发列出 P0→P3 问题清单与文件定位。
- `roadmap.md`：**对应 gap-analysis 的修复路线图**，按 Sprint 排列，含具体任务、文件和实现方案。

## 总路线

```
Phase 0  前端高保真壳层与 11 屏重构        [已完成]
   ↓
Phase 1  真实数据 + 日频回测 MVP            [已完成]
   ↓
Phase 2  AI 策略生成接入真实回测            [已完成]
   ↓
Phase 3  可靠性、可解释性、数据血缘           [已完成]
   ↓
Phase 4  模拟盘闭环                         [已完成]
   ↓
Phase 5  实盘前安全、审批、券商适配           [下一阶段]
```

## 2026-05-13 全局差距分析

执行了完整的前后端差距扫描，详见 `gap-analysis.md` 和 `roadmap.md`。

关键发现（按严重程度）：
- **P0**：Dashboard 类型合约错误、Backtest 未接 strategyId、WebSocket 无客户端
- **P1**：8 个 API 模块返回硬编码假数据、7 个领域无数据库迁移、操作接口是空壳、Paper Trading 无前端
- **P2**：api.ts 缺 14 个已存在后端端点的调用、Audit 未读 DB、Explain 固定为假信号
- **P3**：Agent 编排断路、LLM 状态无监控

这些问题与 Phase 5 任务存在重叠，建议将 gap-analysis 的 Sprint 1-2 任务与 Phase 5 并行推进。

## 当前状态摘要

- **前端**：11 个功能页面全部完成 war-room 风格深度重构，构建通过，App.tsx 纯壳化。
- **后端 Phase 1**：真实数据导入、日频回测、指标计算、API 落库、测试覆盖 — 全部完成。
- **后端 Phase 2**：DSL 定义、结构化输出、生成校验、未来函数检查、真实回测接入、任务关联、前端展示、失败路径、端到端测试 — 全部完成（后端 pytest 68 passed）。
- **后端 Phase 3**：已完成。IS/OOS 切分、walk-forward、参数/滑点敏感性、过拟合评分、Feature Store、数据血缘、规则解释、统一报告 API 全部交付。后端 pytest 79 passed，live API 验证通过；前端 `api.ts` 已暴露新端点类型，`npx tsc -b --force` 与 `npm run build` 通过。
- **后端 Phase 4**：已完成。7 张 `paper_*` 表 + `PaperTradingEngine`（信号 / pre-check / 当日收盘+动态滑点撮合 / 幂等 NAV / breach）+ `/paper/*` API + Celery beat (`15:30 Mon-Fri`)。后端 86 passed，frontend `npm run build` 通过，live API 跑通。
- **Phase 5**：未开始。下一步进入实盘前安全审批：broker adapter / live order draft / 强制 HITL / 权限分级 / kill switch / 审计扩展 / paper↔live 对账 / 实盘前检查清单。

当前项目已有高保真前端、FastAPI API 骨架、策略任务和 Agent 任务表、真实数据回测链路。核心量化能力已从真实数据、真实回测开始补齐，当前重点是把 AI 策略生成与真实回测彻底闭环。
