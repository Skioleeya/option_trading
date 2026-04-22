PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 2
BLOCKED_BY: refactor-dependency-20260317-l1-empty-snapshot-metadata-continuity

## Why

L0 `build_uninitialized_snapshot()` 与 `build_error_snapshot()` 未稳定包含 `rust_active/shm_stats`，导致降级时诊断链路不完整。

## What Changes

1. 在 L0 fallback 快照中补齐 `rust_active`、`rust_shm_path`、`shm_stats` 默认合同。
2. 补充单测，确保未初始化和错误快照字段稳定存在。
3. 保持现有主路径 payload 行为不变。

## Hard Governance Prohibitions

- 禁止使用复杂函数
- 禁止使用魔法数字
- 禁止使用复杂嵌套
- 禁止模块耦合

## Scope

- 目标：`l0_ingest/feeds/fetch_chain_components.py`、`l0_ingest/tests/test_fetch_chain_components.py`
- 非目标：L1/L2 算法逻辑

## Parent

- `refactor-governance-20260317-l0-l2-data-path-remediation-chain`
