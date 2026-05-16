# 2026-05-16 — Agent Studio UX Slice 4：Runs 体验增强

## 目标

让 Runs 工作区从“输入 JSON / 输出 JSON”向“能看懂一次运行过程”迈进一步。

## 本轮交付

### 前端

- `frontend/src/screens/Agent/index.tsx`
  - 新增 `RunSummary`
  - 新增 `RunTimeline`
  - 将运行结果从纯 JSON 历史列表整理为：
    - trace id
    - 节点数
    - 最终状态
    - 按顺序排列的节点时间线
- `frontend/src/styles/prototype.css`
  - 新增 run summary 样式
  - 新增 run timeline 样式

### 后端顺手修复

在验证 Runs 时发现一个真实运行时缺陷：

- 默认链路首节点配置了 `payload -> payload`
- 但 root node 的输入在运行时被直接视为裸对象
- 导致默认工作流执行时出现：`映射源字段不存在: payload`

修复：

- `backend/app/services/agents/runtime.py`
  - root node 若收到裸 payload，会自动包成 `{ traceId, payload }`
- 新增测试：
  - `backend/tests/services/test_agent_runtime_root_mapping.py`

## 验证

### 前端

- `frontend/` 下执行 `npm run build`
- 结果：通过

### 后端

- 执行：
  - `test_agent_runtime_root_mapping.py`
  - `test_agent_runtime_override.py`
  - `test_agent_runtime_contracts.py`
  - `test_agent_runtime_langgraph.py`
- 结果：5 passed

### 运行时手工验证

对默认工作流执行：

- 输入：`{"symbol":"600519.SH"}`
- 结果：
  - 7 个节点顺序执行
  - 最终 `current = {"traceId":"t-ui","status":"ok","payload":{"agent":"risk"}}`

## 结果

Runs 页面现在已经有了继续演进的骨架：

- 上层是一次运行的摘要
- 下层是按节点顺序展开的时间线

后续接入正式 run history、失败回放、节点耗时、错误定位时，可以直接沿这个结构扩展。

## 下一步

进入 **Slice 5：Agent 编辑器组件化增强**。

建议先做：

1. `PromptEditor`：变量提示 + 模板预览
2. `SchemaEditor`：字段表 / JSON 双视图
3. 继续把“可用”向“好配置”推进
