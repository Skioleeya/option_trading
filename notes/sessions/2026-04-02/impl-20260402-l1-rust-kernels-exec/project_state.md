# Project State

## Snapshot
- DateTime (ET): 2026-04-02 16:32:55 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `65dbc0f`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 完整落地 `impl-20260402-l1-bsm-numpy-rust-fallback` 与 `impl-20260402-l1-streaming-aggregator-rust`，并通过 strict gate。
- Scope In:
  - `shared_rust_services` 新增 `bsm.rs` 与 `aggregation.rs`
  - L1 Python 侧 Rust 委托与 fallback 接入
  - `bsm_fast.py`/`streaming_aggregator.py` 行数治理到 `<=400`
  - parity tests、SOP 同步、OpenSpec 任务落地
- Scope Out:
  - L2/L3/L4 逻辑改动
  - CuPy 主路径与 Numba 算法语义重写

## What Changed (Latest Session)
- Files:
  - `l1_compute/analysis/bsm_fast.py`
  - `l1_compute/analysis/bsm_aggregation.py` (new)
  - `l1_compute/analysis/bsm_rust_bridge.py` (new)
  - `l1_compute/compute/gpu_greeks_kernel.py`
  - `l1_compute/aggregation/streaming_aggregator.py`
  - `l1_compute/aggregation/zero_gamma.py` (new)
  - `l1_compute/aggregation/rust_bridge.py` (new)
  - `l1_compute/tests/test_bsm_rust_parity.py` (new)
  - `l1_compute/tests/test_streaming_aggregator_rust_parity.py` (new)
  - `shared_rust_services/src/bsm.rs` (new)
  - `shared_rust_services/src/aggregation.rs` (new)
  - `shared_rust_services/src/lib.rs`
  - `shared_rust_services/Cargo.toml`
  - `shared_rust_services/Cargo.lock`
  - `openspec/changes/impl-20260402-l1-bsm-numpy-rust-fallback/tasks.md`
  - `openspec/changes/impl-20260402-l1-streaming-aggregator-rust/tasks.md`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `notes/sessions/2026-04-02/impl-20260402-l1-rust-kernels-exec/*`
- Behavior:
  - NumPy-tier BSM 优先走 `shared_rust.services.bsm_batch_numpy_tier`，失败显式回退 Python NumPy。
  - `GPUGreeksKernel` NumPy fallback 同步接入 Rust BSM 委托。
  - `StreamingAggregator.full_recompute` 优先走 Rust 聚合；`_recompute_walls` 优先走 Rust 墙位选择并保留 Python fallback。
  - `streaming_aggregator.py` 与 `bsm_fast.py` 都已收敛到 400 行门槛以内。
- Verification:
  - AST parse 通过（7 个 runtime Python 文件 + 2 个测试文件）。
  - Rust extension 编译通过并替换 `shared_rust/services.pyd`。
  - `scripts/policy/check_layer_boundaries.ps1` 通过。
  - `scripts/test/run_pytest.ps1 l1_compute/tests/` -> `54 passed`。
  - `scripts/validate_session.ps1 -Strict` 通过。

## Risks / Constraints
- Risk 1: pytest 缓存目录仍会出现 `nodeids` 写入 warning（不影响通过态）。
- Risk 2: none.

## Next Action
- Immediate Next Step: 进入后续 wave（microstructure/sabr）或继续 shared/services retirement backlog。
- Owner: Codex
