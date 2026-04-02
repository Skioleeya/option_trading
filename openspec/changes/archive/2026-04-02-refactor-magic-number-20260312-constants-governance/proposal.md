PARENT_CHANGE_ID: refactor-governance-20260312-system-deep-cleanup
DEPENDENCY_ORDER: 4
BLOCKED_BY: refactor-bloat-20260312-service-split

## Why

业务阈值散落为硬编码数字会导致策略漂移、不可追踪和回滚困难。

## What Changes

1. 识别业务魔法数并统一提取为命名常量或配置入口。
2. 保留 `0/1/-1` 等结构常量，聚焦业务语义常量治理。
3. 为常量引入注释和来源说明，确保策略可审计。

## Scope

- `app/loops/*`
- `l1_compute/*`
- `l2_decision/*`
- `shared/config/*`

## Parent

- `refactor-governance-20260312-system-deep-cleanup`
