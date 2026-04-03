PARENT_CHANGE_ID: none
DEPENDENCY_ORDER: 33
BLOCKED_BY: none

## Why

`l1_compute/iv/sabr_calibrator.py` uses `scipy.optimize.minimize` (L-BFGS-B) to calibrate
3 SABR parameters (α, ρ, ν) against market IV observations every 120 seconds. This introduces:

1. `scipy` as a hard runtime dependency — large wheel (~30 MB compressed), fragile on CUDA
   environments where scipy's BLAS linkage can conflict with CuPy.
2. `scipy.optimize.minimize` launches a subprocess-like thread pool on some platforms,
   interfering with `asyncio.to_thread` scheduling.
3. The SABR Hagan 2002 formula is a closed-form algebraic expression with no special
   functions beyond `log`, `sqrt`, `atan`. A Rust implementation using Newton-Raphson
   (or the `argmin` crate's L-BFGS-B) eliminates the scipy dependency entirely.

Cadence is 120s — correctness and dependency hygiene outweigh raw throughput here.

## What Changes

1. **Add** `shared_rust_services/src/sabr.rs`:
   - `sabr_iv(strike: f64, forward: f64, ttm: f64, alpha: f64, beta: f64, rho: f64, nu: f64) -> f64`
     Pure Hagan 2002 SABR implied vol formula.
   - `calibrate_sabr(strikes: &[f64], market_ivs: &[f64], forward: f64, ttm: f64, beta: f64) -> (f64, f64, f64, f64)`
     Returns (alpha, rho, nu, residual_mse). Uses internal gradient descent / Newton-Raphson;
     no external crate required beyond `std`.
2. **Add** `mod sabr; pub use sabr::*;` to `shared_rust_services/src/lib.rs`.
3. **Edit** `l1_compute/iv/sabr_calibrator.py`:
   - Add `USE_RUST_SABR = os.environ.get("USE_RUST_SABR", "1") != "0"` feature flag.
   - When `USE_RUST_SABR` is set: call `shared_rust.services.calibrate_sabr(...)` instead of `scipy.optimize.minimize`.
   - `interpolate()` method: when Rust calibration was used, call `shared_rust.services.sabr_iv(...)` for each eval.
   - `_SCIPY_AVAILABLE` fallback path remains for `USE_RUST_SABR=0`.
4. Rebuild pyd.

## Scope

In:
- `shared_rust_services/src/sabr.rs` — SABR formula + solver
- `shared_rust_services/src/lib.rs` — `mod sabr` declaration
- `l1_compute/iv/sabr_calibrator.py` — feature-flagged delegation

Out:
- `l1_compute/iv/` other files — not touched
- `l1_compute/analysis/mtf_iv_engine.py` — calls `sabr_calibrator.interpolate()` unchanged
- `l1_compute/trackers/iv_velocity_tracker.py` — not touched
- All L2/L3 layers — not touched

## Hard Governance Prohibitions

- No `unwrap()` in Rust; all functions return `Result<_, String>` mapped to PyErr at boundary
- `sabr.rs` must stay ≤ 400 lines
- Do not remove the scipy fallback path until `USE_RUST_SABR` has been validated through
  at least one live market session (dual-run evidence)
- `calibrate_sabr` must enforce parameter bounds (_ALPHA_BOUNDS, _RHO_BOUNDS, _NU_BOUNDS)
  identical to the Python implementation

## Verification Gate

1. `python -c "from shared_rust.services import calibrate_sabr, sabr_iv; print('sabr-ok')"` passes.
2. Calibration parity: for 20 random (strikes, market_ivs, forward, ttm) fixtures, Rust result
   must agree with scipy result to residual_mse difference < 1e-8.
3. `interpolate()` parity: Rust `sabr_iv` must match Python Hagan 2002 formula to 1e-10 across
   50 (K, F, T, params) fixtures.
4. `pwsh scripts/test/run_pytest.ps1 l1_compute/tests/` — all tests pass.
5. `pwsh scripts/validate_session.ps1 -Strict` — exits 0.
6. Post-live session: disable `USE_RUST_SABR=0` and confirm no calibration divergence
   vs scipy baseline in session logs before removing scipy conditional.

## Rollback

Set `USE_RUST_SABR=0` environment variable — immediate fallback to scipy path with zero code change.
Hard rollback: `git restore shared_rust_services/src/sabr.rs shared_rust_services/src/lib.rs l1_compute/iv/sabr_calibrator.py`.

## Risk

MEDIUM. SABR calibration convergence depends on solver implementation quality. The Newton-Raphson
approach must handle ill-conditioned cases (near-zero α, ρ near ±1). Mitigation: the `USE_RUST_SABR`
feature flag allows parallel running with scipy comparison during rollout. Parity test suite
covers boundary conditions.
