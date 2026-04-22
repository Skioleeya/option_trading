PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-dechaos-chain
DEPENDENCY_ORDER: 1
BLOCKED_BY: none

## Why

`AgentG._decide_impl` 当前承担过多职责（输入整形、微结构聚合、风险闸门、融合信号、结果组装），函数复杂度与变更风险过高。

## What Changes

1. 将决策流程拆为独立 support 模块（输入归一化、微结构聚合、风险闸门、结果组装）。
2. 将硬编码阈值提取为常量/配置读取，清理局部临时 helper。
3. 保持 `AgentG.decide()` 与输出字段契约不变。

## Guardrails

- 禁止引入 L2->L3/L4 依赖。
- 禁止改变 `fused_signal`、`summary`、jump gate 行为语义。
- 禁止新增 silent catch。
