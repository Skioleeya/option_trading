# Project State

## Snapshot
- DateTime (ET): 2026-04-02 18:09:21 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `65dbc0f`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 落地 `impl-20260402-l1-sabr-rust-solver`，以 Rust owner 接管 SABR 求解并清除 `l1_compute/iv/sabr_calibrator.py` 的 scipy/numpy runtime 依赖。
- Scope In:
  - `shared_rust_services/src/sabr.rs`
  - `shared_rust_services/src/lib.rs`
  - `l1_compute/iv/sabr_calibrator.py`
  - `l1_compute/tests/test_sabr_rust_parity.py`
  - `openspec/changes/impl-20260402-l1-sabr-rust-solver/tasks.md`
- Scope Out:
  - `l1_compute/iv/` 其他模块
  - L2/L3/L4 行为
  - 线上 broker 运行态流程

## What Changed (Latest Session)
- Files:
  - `shared_rust_services/src/sabr.rs` (new)
  - `shared_rust_services/src/lib.rs`
  - `l1_compute/iv/sabr_calibrator.py`
  - `l1_compute/tests/test_sabr_rust_parity.py` (new)
  - `openspec/changes/impl-20260402-l1-sabr-rust-solver/tasks.md`
  - `notes/sessions/2026-04-02/impl-20260402-l1-sabr-rust-solver-exec/*`
- Behavior:
  - 新增 Rust SABR API：`sabr_iv` 与 `calibrate_sabr`（参数边界受控，返回 residual_mse）。
  - `SABRCalibrator` 切换为 Rust-first 且 fail-fast：Rust owner 不可用时显式抛错。
  - `sabr_calibrator.py` runtime 主路径移除 `numpy/scipy` import，`calibrate()/interpolate()` 外部签名保持不变。
  - 数据不足（<3 观测点）时保留轻量填充并返回 `False`。
- Verification:
  - `cargo build --release --target-dir C:\Users\Lenovo\.codex\memories\cargo_target\shared_rust_services` -> PASS
  - `python -c "from shared_rust.services import calibrate_sabr, sabr_iv; print('sabr-ok', ...)"` -> PASS
  - `powershell -ExecutionPolicy Bypass -File scripts/policy/check_layer_boundaries.ps1` -> PASS
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/` -> `132 passed, 1 warning`

## Risks / Constraints
- Risk 1: SABR optimizer在病态输入上的收敛行为与历史 scipy 路径可能不完全一致（已用合成 fixture + 残差边界覆盖）。
- Risk 2: `tmp/pytest_cache` ACL 导致 `nodeids` 写 warning（不影响测试通过）。

## Next Action
- Immediate Next Step: 进入下一执行波次。
- Owner: Codex
