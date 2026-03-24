## Design Summary

1. `l0_ingest/v2` 内部按 `source -> services -> state -> projection -> facade` 单向组织。
2. `facade.OptionChainBuilder` 成为 app 唯一入口；旧 `l0_ingest/feeds/option_chain_builder.py` 不再承接主路径。
3. Arrow schema 与 Rust SHM bridge 移入 shared 中立模块，避免 L0 反向依赖 L1。
4. L0 快照合同不再包含 `aggregate_greeks`、`ttm_seconds`。

## Boundary Contract

- 允许：L1 消费 `chain_arrow`、`chain`、`version`、`as_of_utc`、`rust_active`、`shm_stats`
- 禁止：L0 直接 import `l1_compute` 运行时模块
- 保持：startup bootstrap、mandatory symbols、price repair、diagnostics 公开 API 仍可被 app wiring 调用

## Validation Plan

- Python: targeted pytest for Arrow/input-adapter/compute-loop/L0 helpers
- Rust: source-file split under 400 LOC; Python bridge API names unchanged
- Governance: strict validation, OpenSpec chain, SOP sync
