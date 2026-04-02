PARENT_CHANGE_ID: refactor-governance-20260312-system-deep-cleanup
DEPENDENCY_ORDER: 3
BLOCKED_BY: refactor-nesting-20260312-core-loops

## Why

超长函数与超大类会隐藏多重职责，降低可测试性和审计可读性。

## What Changes

1. 将超长函数拆分为职责单一的 helper/service。
2. 将超大类中可复用逻辑提取到中立服务模块。
3. 维持原合同与行为，避免接口突变。

## Scope

- `app/loops/compute_loop.py`
- `shared/services/*`
- `l3_assembly/*`（若仅为本次拆分落地）

## Parent

- `refactor-governance-20260312-system-deep-cleanup`
