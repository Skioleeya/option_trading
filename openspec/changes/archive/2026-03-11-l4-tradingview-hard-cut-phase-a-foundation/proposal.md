## Why

当前 L4 存在硬编码端点与切换开关缺失问题，且缺少统一图表适配器边界，无法支撑可控硬切和秒级回退。

## What Changes

本子提案（Phase A）仅处理基础层解耦：

1. 将 WS/API 端点改为环境配置驱动，移除硬编码。
2. 引入模块切换开关（Center/Right/Left 与图表引擎键）。
3. 引入 `ChartEngineAdapter` 抽象与 `lightweight` 实现注册边界。
4. 接入消息处理 RUM 打点（received/processed/reconnect）。
5. 清零 L4 TypeScript 基线错误，建立后续阶段可验证基线。

## Scope

- 仅基础设施与边界抽象；不改 Center/Right/Left 业务行为。

## Parent

- `l4-tradingview-hard-cut-parent-governance`
