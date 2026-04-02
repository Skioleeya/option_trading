## Context

`bsm_fast.py` Tier 3 (NumPy fallback) and `gpu_greeks_kernel.py` NumPy tier are the active
compute paths on this machine. Both use element-wise NumPy ops (exp, log, erf/ndtr) over
float64 strike arrays. Replacing with Rust SIMD eliminates Python GIL overhead and scipy ndtr.

## Goals

- Expose `bsm_batch_numpy_tier` from `shared_rust_services` via PyO3
- Python bsm_fast.py: delegate Tier 3 to Rust, keep Tier 1+2 untouched
- Numerical precision: max relative error 1e-10 vs NumPy reference

## Non-Goals

- No GPU/CuPy changes
- No Numba JIT changes
- No changes to `greeks_engine.py` (it calls `compute_greeks_batch` which is unchanged)

## Rust API Signatures

```rust
// shared_rust_services/src/bsm.rs

use pyo3::prelude::*;
use numpy::{PyArray1, PyReadonlyArray1};

#[pyfunction]
pub fn bsm_batch_numpy_tier<'py>(
    py: Python<'py>,
    spots: PyReadonlyArray1<f64>,
    strikes: PyReadonlyArray1<f64>,
    ivs: PyReadonlyArray1<f64>,
    ttms: PyReadonlyArray1<f64>,
    is_call: PyReadonlyArray1<bool>,
    r: f64,
    q: f64,
) -> PyResult<PyObject>
// Returns dict: {"delta": ndarray, "gamma": ndarray, "vega": ndarray,
//                "vanna": ndarray, "charm": ndarray, "theta": ndarray}
```

Internal: implement `norm_cdf(x: f64) -> f64` using Abramowitz & Stegun 7-term approximation
(identical to scipy ndtr to 1e-14 relative error).

## Python Diff Sketch

```python
# bsm_fast.py — Tier 3 fallback section (currently ~line 300-380)

# BEFORE:
def _numpy_tier(spots, strikes, ivs, ttms, is_call, r, q):
    # ... numpy exp/log/ndtr operations ...

# AFTER:
try:
    from shared_rust.services import bsm_batch_numpy_tier as _rust_bsm
    _RUST_BSM_AVAILABLE = True
except ImportError:
    _RUST_BSM_AVAILABLE = False

def _numpy_tier(spots, strikes, ivs, ttms, is_call, r, q):
    if _RUST_BSM_AVAILABLE:
        return _rust_bsm(spots, strikes, ivs, ttms, is_call, r, q)
    # ... existing numpy fallback unchanged ...
```

## Performance Targets

| Path | Current | Target |
|------|---------|--------|
| NumPy tier, 300 contracts | ~15ms | <1.5ms (10×) |
| NumPy tier, 100 contracts | ~5ms  | <0.5ms |

## Controls

1. PyO3 error mapping: all `?` propagation, no `unwrap()`.
2. Parity test: `l1_compute/tests/test_bsm_rust_parity.py` — 50 parametrized fixtures,
   both call and put, across typical 0DTE IV/TTM ranges.
3. `bsm.rs` ≤ 400 lines.

## Risk

MEDIUM. `norm_cdf` approximation must be validated against scipy.special.ndtr.
Include a dedicated unit test comparing 10,000 random inputs to 1e-14 relative tolerance.
