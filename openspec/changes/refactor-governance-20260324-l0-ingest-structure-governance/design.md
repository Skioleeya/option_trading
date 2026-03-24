PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 5
BLOCKED_BY: none

## Design

1. `l0_ingest/v2` 维持单向依赖：`source -> normalize -> state -> services -> projection -> facade`。
2. 旧 `feeds` 内模块按职责进入下列子树：
   - `v2/source/runtime/*`
   - `v2/normalize/{pipeline,bridges,events}/*`
   - `v2/state/runtime/*`
   - `v2/services/{subscription,orchestration,sync,repair,pollers,runtime}/*`
   - `v2/projection/snapshot/*`
3. app 对 L0 的公开入口继续固定为 `from l0_ingest.v2 import OptionChainBuilder`，不引入新的顶层兼容壳。
4. L0 测试按运行树镜像到 `l0_ingest/tests/v2/*`，其余中立基础模块测试保留在 `l0_ingest/tests/*`。
5. 被跟踪的 `dist-info` 目录移出源码树；Rust 本地构建产物不作为仓内结构的一部分。

## Safety

- 不改变 `fetch_snapshot()` 合同和 `rust_active/shm_stats/as_of_utc/version` 语义。
- 不恢复 L0 对 `l1_compute` 的运行时依赖。
- 任何新/改 Python、Rust 运行时文件都必须满足 400 LOC 门禁。
