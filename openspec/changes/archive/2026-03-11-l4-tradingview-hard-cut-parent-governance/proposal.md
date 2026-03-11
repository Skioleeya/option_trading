## Why

TradingView 前端硬切涉及连接层、中心图表、左右模块三类改动。若不做父子提案治理，容易出现跨模块耦合、反向依赖和并发改动冲突，导致切换窗口不可控。

## What Changes

本父提案定义“分阶段 + 按模块”的治理边界：

1. 采用父提案 + 子提案组合推进，不在父提案内直接实现运行时代码。
2. 子提案强制依赖顺序：`A -> B -> C -> D`。
3. 每个子提案仅允许一个主模块改动，禁止跨模块嵌套实现。
4. 强制架构边界：禁止反向依赖，禁止跨层私有成员访问。
5. 父提案关闭条件：全部子提案完成且 strict 验证证据齐全。

## Scope

- 变更编排、依赖顺序、回滚策略、验收门禁。
- 不直接提交 L4 业务功能实现。

## Child Proposals

- `l4-tradingview-hard-cut-phase-a-foundation`
- `l4-tradingview-hard-cut-phase-b-center-module`
- `l4-tradingview-hard-cut-phase-c-right-module`
- `l4-tradingview-hard-cut-phase-d-left-module`

## Rollback

任一子提案触发 P0 回归（边界违规、广播中断、strict 失败），立即停止后续阶段并回退到上一个已验证子提案。
