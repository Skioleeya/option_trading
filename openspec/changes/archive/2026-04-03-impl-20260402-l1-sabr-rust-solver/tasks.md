## Scope

- [x] 确认目标文件：sabr_calibrator.py（calibrate() + interpolate()）
- [x] 确认非目标：mtf_iv_engine.py, iv_velocity_tracker.py 不动；SABRParams dataclass 不变

## Implementation

- [x] 新建 `shared_rust_services/src/sabr.rs`
  - [x] 实现 `sabr_iv(strike, forward, ttm, alpha, beta, rho, nu) -> PyResult<f64>`
    Hagan 2002 公式（仅用 ln/sqrt，无 scipy 依赖）
  - [x] 实现 `calibrate_sabr(strikes, market_ivs, forward, ttm, beta, alpha_init, rho_init, nu_init, max_iter, tol) -> PyResult<(f64, f64, f64, f64)>`
    - 参数边界裁剪保证范围约束
    - 有限差分 Jacobian + Adam-like 梯度下降
    - 返回 (alpha, rho, nu, residual_mse)
  - [x] 确认文件 <= 400 行，无 unwrap()
- [x] 编辑 `shared_rust_services/src/lib.rs`：添加 `mod sabr; pub use sabr::*;`
- [x] 重新编译 pyd
- [x] 编辑 `l1_compute/iv/sabr_calibrator.py`
  - [x] 默认走 `shared_rust.services.calibrate_sabr` / `sabr_iv`
  - [x] runtime 主路径无 `numpy` / `scipy` imports
  - [x] Rust owner 不可用时显式抛 `RuntimeError`
  - [x] `calibrate()` 在数据不足 (<3) 时仅做 lightweight fill 并返回 `False`
  - [x] `interpolate()` 对外签名不变，Rust 结果直接返回
- [x] 新建 `l1_compute/tests/test_sabr_rust_parity.py`
  - [x] `sabr_iv` 公式：50 个 `(K, F, T, params)` fixture，与 Python Hagan 公式误差 < 1e-10
  - [x] `calibrate_sabr`：20 个随机市场观测 fixture，校验 residual / 参数边界
  - [x] 边界条件：`rho` 近 `+-0.999`、极短 `ttm`、`alpha` 近下界
  - [x] Rust owner 不可用时 fail-fast 抛 `RuntimeError`
- [x] 边界扫描：`pwsh scripts/policy/check_layer_boundaries.ps1`

## Tests

- [x] `pwsh scripts/test/run_pytest.ps1 l1_compute/tests/test_sabr_rust_parity.py` 全通过

## Verification

- [x] `python -c "from shared_rust.services import calibrate_sabr, sabr_iv; print('sabr-ok')"` 通过
- [x] `powershell -ExecutionPolicy Bypass -File scripts/policy/check_layer_boundaries.ps1` 通过
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` 通过
- [x] `python scripts/policy/check_openspec_chain.py --meta-file ... --handoff-file ...` 通过

## DoD

- [x] `sabr.rs` <= 400 行，无 unwrap()
- [x] `SABRParams` dataclass 接口不变
- [x] `l1_compute` runtime 源文件无 `numpy` / `scipy` imports
- [x] runtime 路径 Rust-only fail-fast
- [x] Rust owner / rebuilt pyd evidence 完成

## Evidence

- Python bridge/runtime wiring landed in `sabr_calibrator.py`
- Rust smoke: PASS (`python -c "from shared_rust.services import calibrate_sabr, sabr_iv; print('sabr-ok')"` -> import and call verified)
- pytest: PASS (`scripts/test/run_pytest.ps1 l1_compute/tests/` -> `132 passed, 1 warning`)
- boundary: PASS (`scripts/policy/check_layer_boundaries.ps1`)
- openspec gate: PASS (`python scripts/policy/check_openspec_chain.py --meta-file ... --handoff-file ...`)
- strict: PASS (`powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`)

## Notes

OPENSPEC: impl-20260402-l1-sabr-rust-solver
SOP-NOTE: runtime no longer retains a Python fallback branch; Rust-only fail-fast is the active policy in this session.
