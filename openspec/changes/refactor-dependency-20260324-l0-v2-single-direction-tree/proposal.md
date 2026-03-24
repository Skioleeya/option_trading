PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-data-path-remediation-chain
DEPENDENCY_ORDER: 4
BLOCKED_BY: none

## Why

当前 L0 主入口仍通过旧 `OptionChainBuilder` 混入 `l1_compute` 依赖，导致：

1. L0 运行时边界失真，`fetch_chain()` 同时承担 L0 状态投影与 L1 兼容补值。
2. app 生命周期和 L0 启动修复逻辑过度耦合。
3. `l0_rust/src/lib.rs` 超过 400 行，已违反质量门禁。

## What Changes

1. 在 `l0_ingest/v2/` 内建立新的单向依赖工作树。
2. 将 Arrow 合同与 Rust SHM bridge 迁到 shared 中立模块，移除 L0 对 `l1_compute` 的运行时依赖。
3. app 主路径硬切到新的 L0 facade，L0 只输出原始快照/诊断/Arrow 快路径，不再提供 legacy Greeks/TTM 兜底。
4. 拆分 `l0_rust/src/lib.rs`，保持 Python FFI 入口不变但恢复文件长度合规。

## Scope

- 目标：`l0_ingest/v2/*`、`app/container.py`、`app/lifespan.py`、`app/loops/compute_loop.py`、`shared/contracts/*`、`shared/system/rust_shm_bridge.py`
- 同步：`docs/SOP/L0_DATA_FEED.md`、`docs/SOP/L1_LOCAL_COMPUTATION.md`、`docs/SOP/SYSTEM_OVERVIEW.md`
- 非目标：L1/L2/L3 算法语义重写

## Parent

- `refactor-governance-20260317-l0-l2-data-path-remediation-chain`
