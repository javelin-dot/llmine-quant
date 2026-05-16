# 2026-05-16 — Agent Studio UX Slice 3：Workflow Builder 交互增强

## 目标

将工作流页面从“画布 + 顶部按钮组”进一步整理为更接近编排工具的布局：

- 左侧节点库
- 中间画布
- 右侧 Inspector
- 顶部常驻校验反馈

## 设计取舍

- **节点添加入口下沉到左侧 palette**：让“可添加对象”和“当前画布对象”语义分离。
- **校验结果常驻**：不再依赖“什么都没选中”时才显示。
- **暂不做复杂画布能力**：本轮不加入缩放、对齐、mini-map，先把信息层级和动作入口理顺。

## 代码改动

### 前端

- `frontend/src/screens/Agent/index.tsx`
  - 新增 `workflow-palette`
  - 新增 `WorkflowValidationStrip`
  - 取消顶部一排“+ Agent”按钮，把节点入口移到左侧
- `frontend/src/styles/prototype.css`
  - 工作流布局改为三栏
  - 新增节点库样式
  - 新增常驻校验条样式

## 验证

### 构建

- `frontend/` 下执行 `npm run build`
- 结果：通过

### 浏览器验证

验证了：

1. `Workflows` 工作区可见 `节点库`
2. 默认链路可见常驻校验条
3. 发布区域仍正常保留

结果：通过。

## 结果

工作流页面的主结构已经初步稳定：

- 节点从哪里来
- 当前链路是否健康
- 具体节点 / 边如何编辑

这三件事现在已经被视觉上拆开。

## 下一步

进入 **Slice 4：Runs 体验增强**。

重点：

1. 让一次运行的阶段过程更可读
2. 把最终结果和节点历史从“JSON 堆叠”整理成时间线
3. 为后续接 run history / failure replay 预留结构
