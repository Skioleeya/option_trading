PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 6
BLOCKED_BY: none

## Why

`l0_ingest/v2` 已完成单向工作树切换，但仓内仍残留未接入主链路的 runtime-side path 与重复事件处理器，导致：

1. `v2/source/runtime` 目录表面上存在多条实现路径，实际只有 `RustQuoteRuntime` / `PythonQuoteRuntime` 在运行。
2. 遗留模块继续挂在正式 runtime 树内，会误导后续修改把逻辑接回孤立旁路。
3. `normalize/events` 同时保留现役 `StateEventProcessor` 与已退场的 `ChainEventProcessor`，增加语义漂移和来回修补风险。

## What Changes

1. 删除未接入主链路、且仍回连 legacy `l0_ingest.events` / `l0_ingest.sanitize` 的孤立 runtime adapter。
2. 删除仅测试存活、已被 `StateEventProcessor` 取代的重复事件处理器及其专属测试。
3. 拆分超长 L0 runtime 测试文件，恢复 Python 文件长度合规。
4. 更新 L0 README/SOP/OpenSpec/session 记录，明确现役 runtime/provider 与 dead-path 清理结论。

## Scope

- 目标：`l0_ingest/v2/source/runtime/*`, `l0_ingest/v2/normalize/events/*`, `l0_ingest/tests/v2/*`, `l0_ingest/README.md`, `docs/SOP/L0_DATA_FEED.md`
- 同步：`openspec/changes/refactor-governance-20260324-l0-runtime-dead-path-cleanup/*`, `notes/sessions/2026-03-24/l0-static-governance-audit-remediation/*`, `notes/context/*`
- 非目标：L1/L2/L3 运行时行为修改
