PARENT_CHANGE_ID: refactor-governance-20260317-active-options-arrow-volume-contract-chain
DEPENDENCY_ORDER: 3
BLOCKED_BY: refactor-nesting-20260317-active-options-filter-guard-flattening

## Why

`ActiveOptionsRuntimeService` 相关逻辑逐步累积后，文件职责边界趋于膨胀，影响维护速度与回归审计效率。

## What Changes

1. 将归一化/过滤/占位输出的辅助逻辑拆入独立 support 模块。
2. runtime service 仅保留 orchestration 主路径。
3. 对外合同与导出接口保持兼容。

## Hard Governance Prohibitions

- 禁止模块耦合
- 禁止复杂嵌套
- 禁止复杂函数
- 禁止垃圾代码

## Scope

- 目标范围：`shared/services/active_options/*` 内部模块拆分与职责收敛。
- 非目标范围：跨层接口、L2 决策与 L3/L4 展示策略。

## Parent

- `refactor-governance-20260317-active-options-arrow-volume-contract-chain`
