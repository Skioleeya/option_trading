PARENT_CHANGE_ID: refactor-governance-20260317-active-options-arrow-volume-contract-chain
DEPENDENCY_ORDER: 1
BLOCKED_BY: none

## Why

当前 Active Options 路径在 `L1 Arrow` 输出中缺少 `current_volume/turnover` 连续性，导致下游归一化无法稳定利用 `current_volume` 回退逻辑，最终放大 `min_volume` 过滤误伤概率。

## What Changes

1. 统一 `volume/current_volume/turnover` 在 L0/L1/app/shared 的合同映射。
2. 修复 L1 Arrow 合同字段缺口，确保 housekeeping 归一化可读取必需字段。
3. 保持现有层级依赖方向，禁止耦合扩散与语义漂移。

## Hard Governance Prohibitions

- 禁止模块耦合
- 禁止复杂嵌套
- 禁止复杂函数
- 禁止垃圾代码

## Scope

- 目标范围：`l1_compute/arrow/*`、`app/loops/housekeeping_loop.py`、`shared/services/active_options/runtime_service.py` 相关合同衔接逻辑。
- 非目标范围：L2 决策策略、L3 组装策略、前端渲染策略。

## Parent

- `refactor-governance-20260317-active-options-arrow-volume-contract-chain`
