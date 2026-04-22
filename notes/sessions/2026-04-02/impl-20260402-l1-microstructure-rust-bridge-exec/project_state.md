# Project State

## Snapshot
- DateTime (ET): 2026-04-02 17:18:20 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `65dbc0f`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 落地 `impl-20260402-l1-microstructure-rust-bridge`，启用 L1 微结构 Rust owner 且禁止 Python fallback 回归。
- Scope In:
  - `shared_rust_services/src/microstructure.rs`
  - `shared_rust_services/src/lib.rs`
  - `l1_compute/microstructure/vpin_v2.py`
  - `l1_compute/microstructure/vol_accel_v2.py`
  - `l1_compute/analysis/entropy_filter.py`
  - `l1_compute/tests/test_microstructure_rust_parity.py`
  - `openspec/changes/impl-20260402-l1-microstructure-rust-bridge/tasks.md`
- Scope Out:
  - `l1_compute/microstructure/bbo_v2.py`
  - `l1_compute/microstructure/depth_engine.py`
  - L2/L3/L4 行为变更

## What Changed (Latest Session)
- Files:
  - `shared_rust_services/src/microstructure.rs` (new)
  - `shared_rust_services/src/lib.rs`
  - `l1_compute/microstructure/vpin_v2.py`
  - `l1_compute/microstructure/vol_accel_v2.py`
  - `l1_compute/analysis/entropy_filter.py`
  - `l1_compute/tests/test_microstructure_rust_parity.py` (new)
  - `openspec/changes/impl-20260402-l1-microstructure-rust-bridge/tasks.md`
- Behavior:
  - 新增 Rust 微结构函数：`compute_vpin_regime` / `compute_vol_accel_entropy` / `compute_entropy_gate`。
  - `vpin_v2.py` 移除 `l1_rust` 旧桥，regime 分类改走 `shared_rust.services.compute_vpin_regime`；Rust 不可用/失败时显式抛错。
  - `vol_accel_v2.py` entropy + EMA 单步更新委托 Rust；Rust 不可用/失败时显式抛错。
  - `entropy_filter.py` Shannon gate 委托 Rust；Rust 不可用/失败时显式抛错。
  - 新增 parity/契约/无-fallback 测试覆盖微结构桥接。
- Verification:
  - `python -c "from shared_rust.services import compute_vpin_regime, compute_vol_accel_entropy, compute_entropy_gate; ..."` -> PASS
  - `scripts/test/run_pytest.ps1 l1_compute/tests/` -> `60 passed, 1 warning`
  - `scripts/policy/check_layer_boundaries.ps1` -> PASS
  - `cargo build --release --target-dir C:\Users\Lenovo\.codex\memories\cargo_target\shared_rust_services` -> PASS

## Risks / Constraints
- Risk 1: `tmp/pytest_cache` 的 `nodeids` 写权限 warning 仍存在（不影响通过）。
- Risk 2: none（strict gate 与 pointer 同步已完成）。

## Next Action
- Immediate Next Step: 进入下一执行波次。
- Owner: Codex
