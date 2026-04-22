PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 3
BLOCKED_BY: refactor-dependency-20260317-l0-fallback-snapshot-diagnostics-continuity

## Why

当前 L0->L1 热路径仍以 `list[dict]` 进入 L1，再在每 tick 执行 dict->Arrow 转换，偏离 zero-copy 优先原则并增加 CPU/内存开销。

## What Changes

1. 设计并实现 L0->L1 Arrow 直通路径（优先直接消费 `RecordBatch`）。
2. 保留兼容回退路径（list[dict]）以便分阶段切换。
3. 增加性能/行为回归验证，确保合同与语义不变。

## Hard Governance Prohibitions

- 禁止使用复杂函数
- 禁止使用魔法数字
- 禁止使用复杂嵌套
- 禁止模块耦合

## Scope

- 目标：L0->L1 传输与转换边界
- 非目标：L2 信号算法重写

## Parent

- `refactor-governance-20260317-l0-l2-data-path-remediation-chain`
