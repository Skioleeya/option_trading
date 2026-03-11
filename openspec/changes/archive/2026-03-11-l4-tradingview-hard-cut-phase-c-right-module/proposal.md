## Why

Right 面板承担决策消费与交易解释展示，存在类型收敛与稳定槽位要求。需独立阶段交付，避免与 Center 图表改造相互干扰。

## What Changes

本子提案（Phase C）仅处理 Right 模块：

1. 强化 `payload -> store -> model -> component` 类型链路。
2. 固化 `ActiveOptions` 五槽位稳定渲染与占位协议。
3. 固化 FLOW 方向“数值符号优先”配色语义。
4. 保证 Right 模块切换可独立回退，不依赖 Center/Left 内部实现。

## Scope

- 仅 Right 组件及其 model 层；不改 Center/Left 实现。

## Parent

- `l4-tradingview-hard-cut-parent-governance`
