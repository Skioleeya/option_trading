## Context

`sabr_calibrator.py` runs scipy L-BFGS-B every 120s to calibrate 3 SABR parameters
(α, ρ, ν) against market IV observations. Hagan 2002 SABR formula is algebraic —
no special functions beyond log/sqrt/atan — making a self-contained Rust solver feasible
without any external optimization crate.

## Goals

- Implement SABR Hagan 2002 formula and simple gradient-descent solver in Rust (std only)
- Feature-flag Python delegation; scipy fallback retained for `USE_RUST_SABR=0`
- Calibration output must match scipy to residual_mse difference < 1e-8

## Non-Goals

- No removal of scipy path in this proposal (gated by live session dual-run evidence)
- No changes to `mtf_iv_engine.py`, `iv_velocity_tracker.py`
- No change to `SABRParams` dataclass

## Rust API Signatures

```rust
// shared_rust_services/src/sabr.rs

/// Hagan 2002 SABR implied vol for a single (K, F, T, params) combination
#[pyfunction]
pub fn sabr_iv(
    strike: f64,
    forward: f64,
    ttm: f64,
    alpha: f64,
    beta: f64,
    rho: f64,
    nu: f64,
) -> PyResult<f64>

/// Calibrate SABR parameters from market observations
/// Returns (alpha, rho, nu, residual_mse)
#[pyfunction]
pub fn calibrate_sabr(
    strikes: PyReadonlyArray1<f64>,
    market_ivs: PyReadonlyArray1<f64>,
    forward: f64,
    ttm: f64,
    beta: f64,
    alpha_init: f64,
    rho_init: f64,
    nu_init: f64,
    max_iter: usize,    // default 1000
    tol: f64,           // default 1e-8
) -> PyResult<(f64, f64, f64, f64)>
```

Solver strategy: Adam-like gradient descent with finite-difference Jacobian.
Parameter bounds enforced by sigmoid re-parameterization (avoids box constraints).

## Python Diff Sketch

```python
# sabr_calibrator.py

USE_RUST_SABR = os.environ.get("USE_RUST_SABR", "1") != "0"

try:
    from shared_rust.services import calibrate_sabr as _rust_calibrate
    from shared_rust.services import sabr_iv as _rust_sabr_iv
    _RUST_SABR_AVAILABLE = True
except ImportError:
    _RUST_SABR_AVAILABLE = False

# In calibrate():
if USE_RUST_SABR and _RUST_SABR_AVAILABLE:
    alpha, rho, nu, mse = _rust_calibrate(
        strikes_arr, market_ivs_arr, forward, ttm, self.beta,
        alpha_init, rho_init, nu_init
    )
    self._params = SABRParams(alpha=alpha, beta=self.beta, rho=rho, nu=nu)
    return
# ... existing scipy path ...

# In interpolate():
if USE_RUST_SABR and _RUST_SABR_AVAILABLE and self._params:
    return _rust_sabr_iv(strike, forward, ttm, p.alpha, p.beta, p.rho, p.nu)
# ... existing Python formula ...
```

## Performance Targets

| Path | Current | Target |
|------|---------|--------|
| calibrate() 120s cadence | ~50ms (scipy) | <10ms (Rust gradient descent) |
| interpolate() per strike | ~0.2ms | <0.02ms |

## Controls

1. Parity test: 20 random (strikes, ivs, F, T) fixtures — Rust calibration residual_mse
   within 1e-8 of scipy result.
2. Boundary enforcement: assert α ∈ (0.001, 5.0), ρ ∈ (-0.999, 0.999), ν ∈ (0.001, 5.0).
3. `sabr.rs` ≤ 400 lines.
4. Live dual-run: run USE_RUST_SABR=0 (scipy) and USE_RUST_SABR=1 (Rust) in parallel for one
   market session; compare logged calibration results before removing scipy conditional.

## Risk

MEDIUM. Optimizer convergence on ill-conditioned inputs (ρ near ±1, very short TTM) needs
explicit test coverage. Sigmoid re-parameterization ensures parameters stay in bounds but
may slow convergence near boundaries — set `max_iter=2000` for boundary-proximal inputs.
