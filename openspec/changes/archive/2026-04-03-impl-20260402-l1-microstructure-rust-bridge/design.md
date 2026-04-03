## Context

VPIN, vol_accel, and entropy_filter all have reserved Rust bridge hooks in `l1_compute/`.
VPIN imports `l1_rust` (nonexistent → ImportError, Python path active). Vol_accel has similar
reservation comments. entropy_filter has no bridge at all. All three compute tight numerical
loops over small arrays (<100 elements per tick). Consolidating into `shared_rust_services`
follows the Wave 18 pattern (tactical, active_options all in `services.pyd`).

## Goals

- Implement 3 Rust functions in `microstructure.rs`
- Activate VPIN and vol_accel bridges; add new bridge to entropy_filter
- Preserve all Python interface signatures (no downstream changes)
- VPINRegime string enum values must not change

## Non-Goals

- `bbo_v2.py` — separate scope (different algorithm)
- `depth_engine.py` — out of scope
- `l1_rust` crate — do NOT create; use `shared_rust_services` only

## Rust API Signatures

```rust
// shared_rust_services/src/microstructure.rs

/// VPIN regime classification
/// Returns 0=NORMAL, 1=ELEVATED, 2=TOXIC
#[pyfunction]
pub fn compute_vpin_regime(
    buy_vols: PyReadonlyArray1<f64>,
    sell_vols: PyReadonlyArray1<f64>,
    threshold_elevated: f64,   // 0.5
    threshold_toxic: f64,      // 0.75
) -> PyResult<u8>

/// Vol acceleration entropy + single EMA update
/// Returns (entropy: f64, ema_next: f64)
#[pyfunction]
pub fn compute_vol_accel_entropy(
    price_buckets: PyReadonlyArray1<f64>,
    ema_prev: f64,
    alpha: f64,
) -> PyResult<(f64, f64)>

/// Shannon entropy gate — returns true if tick passes (entropy ≥ min_entropy)
#[pyfunction]
pub fn compute_entropy_gate(
    features: PyReadonlyArray1<f64>,
    min_entropy: f64,
) -> PyResult<bool>
```

## Python Diff Sketch

```python
# vpin_v2.py — replace l1_rust block

try:
    from shared_rust.services import compute_vpin_regime as _rust_vpin_regime
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False

# In regime classification:
if _RUST_AVAILABLE:
    code = _rust_vpin_regime(buy_arr, sell_arr, 0.5, 0.75)
    regime = [VPINRegime.NORMAL, VPINRegime.ELEVATED, VPINRegime.TOXIC][code]
else:
    # ... existing Python threshold comparisons ...
```

```python
# entropy_filter.py — add bridge

try:
    from shared_rust.services import compute_entropy_gate as _rust_entropy_gate
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False
```

## Performance Targets

| Function | Estimated speedup |
|----------|-------------------|
| compute_vpin_regime (3×30 bucket arrays) | 3–5× |
| compute_vol_accel_entropy (20-bucket window) | 2–3× |
| compute_entropy_gate (8-feature vector) | 2× |

## Controls

1. VPINRegime enum contract test: assert string values "NORMAL"/"ELEVATED"/"TOXIC" unchanged.
2. Entropy parity: Rust `f64::ln` vs Python `math.log` — relative error < 1e-12.
3. `microstructure.rs` ≤ 400 lines.

## Risk

LOW. Regime classification is threshold comparison — no float precision issue. Entropy uses
standard `f64::ln` which matches Python `math.log` exactly. Primary risk: array length
mismatch if buy_vols/sell_vols padding differs — guard with `assert_eq!(buy_vols.len(), sell_vols.len())` → PyValueError.
