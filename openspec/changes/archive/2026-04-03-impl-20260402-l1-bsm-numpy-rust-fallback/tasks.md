## Scope

- [x] 确认目标文件：bsm_fast.py (Tier 3 分支), gpu_greeks_kernel.py (NumPy fallback 分支)
- [x] 确认非目标：GPU/Numba 层不动，greeks_engine.py 不动

## Implementation

- [x] 新建 `shared_rust_services/src/bsm.rs`
  - [x] 实现 `norm_cdf(x: f64) -> f64`（Rust `libm::erf` 路径）
  - [x] 实现 `bsm_batch_numpy_tier` PyO3 函数，返回 dict 含 delta/gamma/vega/vanna/charm/theta
  - [x] 确认文件 ≤ 400 行
  - [x] 无 `unwrap()`，错误路径显式 `PyValueError` / `PyResult` 传播
- [x] 编辑 `shared_rust_services/src/lib.rs`：注册 `bsm` module
- [x] 重新编译 pyd（Cargo target: `C:\Users\Lenovo\.codex\memories\cargo_target\shared_rust_services`）
- [x] 编辑 `l1_compute/analysis/bsm_fast.py`：Tier 3 分支改为 Rust-only（Rust 失败显式抛错）
- [x] 编辑 `l1_compute/compute/gpu_greeks_kernel.py`：CPU NumPy 分支改为 Rust-only（Rust 失败显式抛错）
- [x] 边界扫描：`pwsh scripts/policy/check_layer_boundaries.ps1`

## Tests

- [x] 新建 `l1_compute/tests/test_bsm_rust_parity.py`
  - [x] 50个参数化 fixture（call + put，覆盖典型 0DTE IV/TTM 范围）
  - [x] 相对误差 < 1e-10
  - [x] norm_cdf 对 10,000 点与 scipy.special.ndtr 对齐（环境有 scipy 时校验）
- [x] `pwsh scripts/test/run_pytest.ps1 l1_compute/tests/` 全通过

## Verification

- [x] `python -c "from shared_rust.services import bsm_batch_numpy_tier; print('bsm-ok')"` 通过
- [x] ATM call delta ∈ (0.4, 0.6) 验证
- [x] `pwsh scripts/validate_session.ps1 -Strict` 通过
- [x] OpenSpec 链路 gate 由 strict validation 集成校验

## DoD

- [x] 无行为回归（GPU/Numba 层输出不变）
- [x] 文件长度 bsm.rs ≤ 400 行
- [x] 无 unwrap()
- [x] 变更可回滚（git restore + pyd 重编）

## Evidence

- `python -c` smoke: `bsm-ok ['charm', 'delta', 'gamma', 'theta', 'vanna', 'vega'] ...`
- pytest 通过行数：`132 passed`（`l1_compute/tests/`）
- validate_session：`powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> PASS

## Pending DEBT (Successor Session Required)

- [x] **DEBT-P1 CLOSED (2026-04-02, impl-20260402-claude-audit-fixes-closeout)** `l1_compute/analysis/bsm_aggregation.py` 已删除；`bsm_fast.py` 聚合与 wall 选择改为 Rust owner（`aggregate_from_greeks` / `select_walls`）。
- [x] **DEBT-P2 CLOSED (2026-04-02, impl-20260402-claude-audit-fixes-closeout)** `l1_compute/analysis/bsm_rust_bridge.py` 仅保留 Rust-only 导入与显式抛错，无 `_RUST_AVAILABLE` guard / NumPy fallback。

## Notes

OPENSPEC: impl-20260402-l1-bsm-numpy-rust-fallback
