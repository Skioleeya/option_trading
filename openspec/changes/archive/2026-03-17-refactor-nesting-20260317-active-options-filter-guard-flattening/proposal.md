PARENT_CHANGE_ID: refactor-governance-20260317-active-options-arrow-volume-contract-chain
DEPENDENCY_ORDER: 2
BLOCKED_BY: refactor-dependency-20260317-active-options-arrow-volume-turnover-continuity

## Why

当前 Active Options 过滤链存在多层条件嵌套，`volume/current_volume` 回退、`min_volume` 判定、占位触发解释路径耦合在同一逻辑块，降低可读性与审计效率。

## What Changes

1. 以 guard clause 重排过滤入口，压平嵌套分支。
2. 维持原有合同语义与行为输出，不扩散到非目标模块。
3. 为关键分支补齐可解释性测试点与日志标记约束。

## Hard Governance Prohibitions

- 禁止模块耦合
- 禁止复杂嵌套
- 禁止复杂函数
- 禁止垃圾代码

## Scope

- 目标范围：`shared/services/active_options/runtime_service.py` 过滤判定与归一化编排结构。
- 非目标范围：L2/L3/L4 策略、Rust 数据通道、前端展示逻辑。

## Parent

- `refactor-governance-20260317-active-options-arrow-volume-contract-chain`
