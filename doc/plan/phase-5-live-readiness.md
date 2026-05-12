# Phase 5 - 实盘前准备

## 目标

为实盘接入做安全、审批、审计和券商接口准备。默认不开放自动实盘下单。

## 任务清单

- [ ] 抽象 broker adapter：统一下单、撤单、成交回报、持仓查询接口。
- [ ] 增加 QMT 或 PTrade 的最小适配接口，占位实现先不触发真实交易。
- [ ] 增加 live order draft 模型，区分订单草案和真实订单。
- [ ] 所有 live order 必须进入 Human-in-the-loop 审批。
- [ ] 完善权限分级：Research、Trader、Risk、Admin、Viewer。
- [ ] 完善 kill switch：全局暂停、策略暂停、账户冻结。
- [ ] 完善审计日志：actor、action、resource、trace_id、result、metadata。
- [ ] 增加模拟盘和实盘理论订单的一致性对账。
- [ ] 增加实盘前检查清单 API。
- [ ] 增加测试，覆盖审批、权限、熔断和审计。

## 验收标准

- [ ] 系统可以生成实盘订单草案，但不能绕过人工审批。
- [ ] 所有高风险动作都有审计记录。
- [ ] kill switch 可以阻断新订单生成和执行。
- [ ] broker adapter 可替换，不与业务逻辑强耦合。

