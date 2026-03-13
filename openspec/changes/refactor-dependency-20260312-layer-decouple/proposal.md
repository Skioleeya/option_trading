PARENT_CHANGE_ID: refactor-governance-20260312-system-deep-cleanup
DEPENDENCY_ORDER: 1
BLOCKED_BY: none

## Why

跨层依赖与隐式耦合会直接破坏 L0-L4 单向架构，属于 P0 级风险，必须作为首个子提案先清理。

## What Changes

1. 扫描并清理目标范围内的跨层违规 import 风险。
2. 将可复用逻辑迁移到中立边界（`shared/services/*` 或合同模块）。
3. 建立依赖图，确保后续子提案在干净边界上实施。

## Scope

- `app/loops/*`
- `l2_decision/*`
- `l3_assembly/*`
- `shared/services/*`

## Parent

- `refactor-governance-20260312-system-deep-cleanup`
