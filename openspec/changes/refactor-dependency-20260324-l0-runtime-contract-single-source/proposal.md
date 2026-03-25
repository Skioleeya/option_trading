PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 7
BLOCKED_BY: refactor-governance-20260324-l0-runtime-dead-path-cleanup

## Why

`l0_ingest/v2` 的目录结构已基本单向化，但运行契约和数据治理仍未完全收口：

1. Rust runtime 在已启动后对新 symbol 集只做 Python 侧跟踪，没有把目标集合实际 reconcile 到活跃会话。
2. IV/OI 与 metadata 解析分散在 sync / poller / sanitizer 多处，修改一处不足以保证合同一致。
3. `fetch_snapshot()` 仍残留 legacy payload 壳，`as_of/as_of_utc` 绑定的是投影时刻而非 L0 source time。

## What Changes

1. 将 `L0QuoteRuntime.subscribe()` 收敛为“完整 desired set -> 实际 applied session”契约，并把 diagnostics 扩展到 `desired_symbols/applied_symbols`。
2. 把 IV/OI 清洗与 poller metadata 扫描收口到共享实现，移除 duplicated parser / expiry scan / strike fallback。
3. 清理 snapshot projection 中的 legacy `aggregate_greeks/ttm_seconds` 残留，并把 `as_of/as_of_utc` 绑定到最近一次 L0 source update。

## Scope

- 目标：`l0_ingest/v2/source/runtime/*`, `l0_ingest/v2/normalize/pipeline/*`, `l0_ingest/v2/services/subscription/*`, `l0_ingest/v2/services/sync/*`, `l0_ingest/v2/services/pollers/*`, `l0_ingest/v2/projection/snapshot/*`, `l0_ingest/v2/state/runtime/*`
- 同步：`l0_ingest/tests/v2/*`, `docs/SOP/L0_DATA_FEED.md`, `notes/sessions/2026-03-24/l0-governance-remediation-20260324/*`
- 非目标：L1/L2/L3 算法语义变更、UI 行为调整

## Parent

- `refactor-governance-20260317-l0-l2-data-path-remediation-chain`
