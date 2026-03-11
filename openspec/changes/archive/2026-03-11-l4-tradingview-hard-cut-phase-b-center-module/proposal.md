## Why

Center 模块承担 TradingView 主图交互，是硬切风险最高区域。需要单独阶段完成图表适配、增量更新与降级连续性，避免影响右/左模块交付节奏。

## What Changes

本子提案（Phase B）仅处理 Center 模块：

1. `AtmDecayChart` 切换到 `ChartEngineAdapter` 驱动。
2. 维持并强化严格命中 hover 语义（无命中即清焦点）。
3. 优化增量数据路径，保留全量回退路径。
4. 保障异常降级时 L4 广播消费连续，不阻断页面更新。

## Scope

- 仅 Center 范围（图表 + Overlay 相关模型/工具）；不改 Right/Left 组件逻辑。

## Parent

- `l4-tradingview-hard-cut-parent-governance`
