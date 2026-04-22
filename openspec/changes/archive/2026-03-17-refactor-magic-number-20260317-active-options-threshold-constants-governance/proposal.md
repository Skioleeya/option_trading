PARENT_CHANGE_ID: refactor-governance-20260317-active-options-arrow-volume-contract-chain
DEPENDENCY_ORDER: 4
BLOCKED_BY: refactor-bloat-20260317-active-options-runtime-service-module-split

## Why

阈值常量在 Active Options 路径中分散定义，存在可审计性不足与策略漂移风险，需要统一常量治理。

## What Changes

1. 将 `min_volume` 与相关阈值迁移到统一常量与配置入口。
2. 清理裸字面量，建立命名常量与注释语义。
3. 增加阈值变更影响面验证与回滚说明。

## Hard Governance Prohibitions

- 禁止模块耦合
- 禁止复杂嵌套
- 禁止复杂函数
- 禁止垃圾代码

## Scope

- 目标范围：Active Options 路径阈值常量治理。
- 非目标范围：策略参数业务改动、外部 API 合同改动。

## Parent

- `refactor-governance-20260317-active-options-arrow-volume-contract-chain`
