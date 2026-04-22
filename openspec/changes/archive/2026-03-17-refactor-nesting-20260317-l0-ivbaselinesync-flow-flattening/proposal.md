PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-dechaos-chain
DEPENDENCY_ORDER: 2
BLOCKED_BY: refactor-bloat-20260317-l2-agentg-decision-pipeline-split

## Why

`IVBaselineSync.warm_up/_staggered_sync` 目前存在深嵌套与重复批处理逻辑，导致维护成本高、行为修复容易遗漏。

## What Changes

1. 提取批次调度骨架与 chunk 遍历流程。
2. 提取 IV/OI 解析与 spot_at_sync 写入策略。
3. 提取 cooldown/限流错误处理策略，减少重复分支。
4. 保持外部接口、调用顺序和日志语义等价。

## Guardrails

- 不改变 warm_up dedupe window 语义。
- 不改变 301607 cooldown 行为语义。
- 不改变 chunk 顺序（ATM-first split）。
