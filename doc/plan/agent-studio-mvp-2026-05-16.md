# Agent Studio MVP 交付记录

> 日期：2026-05-16  
> 状态：已完成  
> 目标：将原本静态展示的 Agent 模块，升级为前后端真实可用、可配置、可编排、可运行、可发布的 MVP。

---

## 1. 本阶段目标

用户要求：

1. 默认交易链路中的所有 Agent 都必须从静态配置升级为可配置实体。
2. Agent 新增 / 修改时必须保留完整能力，不能为了 MVP 简化字段。
3. 每个 Agent 必须支持：
   - 模型配置
   - 系统提示词
   - 用户提示词模板
   - 原始输入 / 输出
   - 标准化结构化输入 / 输出
   - 映射
   - 工具权限
   - 约束
   - 运行策略
4. Agent 模块必须使用 **LangChain + LangGraph**。
5. 多个 Agent 需要通过类似画布的方式组成交易链路。

本阶段的设计原则不是“先做个简版”，而是直接把后续会成为核心配置资产的字段一次建全，避免后续返工和数据迁移。

---

## 2. 已完成能力

### 2.1 完整 Agent 定义

新增 `AgentDefinition`，支持完整配置：

| 配置域 | 已实现内容 |
|---|---|
| 基础信息 | 名称、角色、头像、描述、目标、下游交接提示、自治等级、状态 |
| 模型 | provider、model、temperature、topP、maxTokens 等模型配置 |
| Prompt | system prompt、user prompt template |
| 原始契约 | input schema、output schema |
| 标准化契约 | normalized input schema、normalized output schema |
| 数据映射 | input mapping、output mapping |
| 治理能力 | tool policy、constraints、runtime policy |

默认交易链路中的 7 个 Agent 已从静态展示升级为数据库定义：

1. Research Agent
2. Strategy Agent
3. Backtest Agent
4. Explain Agent
5. Portfolio Agent
6. Execution Agent
7. Risk Agent

### 2.2 工作流定义与画布编排

新增：

- `WorkflowDefinition`
- `WorkflowNode`
- `WorkflowEdge`

前端 Agent 页面已支持：

- Agent 库
- 节点添加
- 节点删除
- 节点拖拽
- 节点连线
- 边映射编辑
- 节点级 override

默认交易链路已可在画布中真实编排，而不是仅做静态卡片展示。

### 2.3 LangChain + LangGraph 运行时

新增运行时模块：

- `backend/app/services/agents/runtime.py`

已实现：

- 将持久化 `AgentDefinition` 编译为 LangChain runnable
- 将工作流节点 / 边编译为 LangGraph `StateGraph`
- 支持节点级 override 覆盖模型、prompt、schema、mapping
- 支持边映射执行
- 支持输入输出 JSON Schema 校验
- 支持 mock provider 与真实模型 provider 切换

这意味着当前工作流已经不是“看起来像编排”，而是真的可以执行。

### 2.4 契约校验与可视化

前端已支持：

- 查看节点标准化输入 / 输出 Schema
- 编辑边映射
- 校验上游输出字段是否存在
- 校验下游必填字段是否已映射
- 在画布旁展示链路校验结果

后端发布接口也会执行契约校验，避免只依赖前端。

### 2.5 运行调试

前端已支持：

- 输入 JSON payload
- 执行当前工作流
- 查看最终结果
- 查看逐节点执行历史

这为后续调试、回放、运行审计提供了基础。

### 2.6 发布与版本快照

新增：

- `WorkflowVersion`
- `GET /agents/workflows/{workflow_id}/versions`
- `POST /agents/workflows/{workflow_id}/publish`

发布逻辑：

1. 先执行工作流契约校验
2. 校验通过后生成不可变版本快照
3. 快照包含：
   - 工作流结构
   - 节点
   - 边
   - 节点 override
   - 发布时完整 Agent 定义
4. 编辑已发布工作流后，状态自动回到 `draft`
5. 再次发布时自动递增 patch 版本号

这一步把“可编辑草稿”和“可上线配置”真正分开了。

---

## 3. 主要代码范围

### 后端

- `backend/app/domains/agents/models.py`
- `backend/app/domains/agents/schemas.py`
- `backend/app/api/v1/agents.py`
- `backend/app/services/agents/runtime.py`
- `backend/scripts/seed_dev_data.py`
- `backend/app/db/migrations/versions/20260516_000001_workflow_versions.py`

### 前端

- `frontend/src/screens/Agent/index.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/styles/prototype.css`

### 测试

- `backend/tests/services/test_agent_runtime_langgraph.py`
- `backend/tests/services/test_agent_runtime_contracts.py`
- `backend/tests/services/test_agent_runtime_override.py`
- `backend/tests/api/test_agent_workflow_publish.py`

---

## 4. 已完成验证

### 后端验证

- LangGraph 工作流可端到端执行
- 合同校验可拦截错误映射
- 节点 override 可覆盖运行配置
- 发布会生成不可变版本快照
- 编辑后会回到 draft
- 二次发布版本会从 `1.0.0` 升到 `1.0.1`

### 前端验证

- `npm run build` 通过
- 浏览器验证：
  - Agent 页面正常加载
  - 画布、节点、边、校验面板可用
  - 调试运行面板可见
  - 发布按钮可执行
  - 发布后可看到 `v1.0.0`

### 迁移验证

- 当前开发库已执行到最新迁移
- 全新 SQLite 库从 0 到 head 的完整迁移链通过

---

## 5. 当前仍未完成的内容

这些不是遗漏，而是有意留给下一阶段或后续能力阶段：

| 方向 | 说明 |
|---|---|
| UI / 交互易用性 | 当前已可用，但仍偏“工程面板”，对第一次使用者不够友好 |
| Human-in-the-loop | execution / high-risk Agent 尚未实现图内暂停、审批、恢复 |
| 运行记录持久化 | 当前有调试执行，但尚未沉淀正式 run history / replay |
| 多版本运行选择 | 已有版本快照，但还未支持选择指定版本执行 |
| 协作治理 | 暂未加入发布说明、变更对比、审批人、回滚 |

---

## 6. 对下一阶段的判断

当前最重要的不是继续往里塞更多 Agent 能力，而是把已完成能力变得**可理解、可发现、低错误率**。

因此下一阶段应优先进入：

> **Agent Studio UX — 以 UI 交互与用户易用性为核心的设计阶段**

详见：

- `doc/plan/phase-agent-studio-ux.md`
