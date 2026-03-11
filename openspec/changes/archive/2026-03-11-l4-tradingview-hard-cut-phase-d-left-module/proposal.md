## Why

Left 面板承担微结构和墙体/深度展示，必须独立模块化以支持最终硬切闭环，并避免与 Center/Right 的并发改动耦合。

## What Changes

本子提案（Phase D）仅处理 Left 模块：

1. 收敛 `MicroStats/WallMigration/DepthProfile` 模块边界。
2. 保持 Left 模块仅消费 L3 合同字段，不引入跨层实现依赖。
3. 固化 Left 模块主题映射与导航行为的本地实现边界。
4. 完成 Left 模块切换与回退验证，作为父提案最终子阶段。

## Scope

- 仅 Left 模块代码与测试；不改 Center/Right 功能。

## Parent

- `l4-tradingview-hard-cut-parent-governance`
