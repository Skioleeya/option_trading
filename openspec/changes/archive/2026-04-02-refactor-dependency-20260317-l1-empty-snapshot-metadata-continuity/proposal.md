PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 1
BLOCKED_BY: none

## Why

`L1ComputeReactor` 在空快照降级路径直接返回 `_empty_snapshot()`，当前实现会丢失 `extra_metadata`，导致 `rust_active/shm_stats/source_data_timestamp_utc` 连续性中断。

## What Changes

1. 修复 `l1_compute/reactor.py` 的空快照路径，透传 `extra_metadata`。
2. 增加单测覆盖：空链、`spot<=0`、`n_valid=0` 三种降级路径。
3. 保持现有字段语义与接口不变，不引入跨层依赖。

## Hard Governance Prohibitions

- 禁止使用复杂函数
- 禁止使用魔法数字
- 禁止使用复杂嵌套
- 禁止模块耦合

## Scope

- 目标：`l1_compute/reactor.py`、`l1_compute/tests/test_reactor.py`
- 非目标：L2 决策逻辑、L3 组装逻辑

## Parent

- `refactor-governance-20260317-l0-l2-data-path-remediation-chain`
