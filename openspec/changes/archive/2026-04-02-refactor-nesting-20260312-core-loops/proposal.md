PARENT_CHANGE_ID: refactor-governance-20260312-system-deep-cleanup
DEPENDENCY_ORDER: 2
BLOCKED_BY: refactor-dependency-20260312-layer-decouple

## Why

深层嵌套会增加热路径分支不确定性，放大回归风险并拖慢定位效率。

## What Changes

1. 将目标热路径函数的控制流压平，优先使用 guard clause 和早返回。
2. 将复杂判断拆为可测的小函数，减少嵌套层级。
3. 保持行为不变，仅做结构重构。

## Scope

- `app/loops/compute_loop.py`
- `l1_compute/*`（仅热路径相关函数）
- `l3_assembly/*`（仅与目标函数直接相关代码）

## Parent

- `refactor-governance-20260312-system-deep-cleanup`
