## Context

`streaming_aggregator.py` holds the chain-level Greeks aggregation. `full_recompute()` sums
GEX/Vanna/Charm over all N contracts from a `GreeksMatrix` (numpy float64 arrays). Wall tracking
calls `_select_walls_by_spot()` which runs argmax over two strike arrays. Both paths are pure
float arithmetic — no branching business logic — ideal for Rust SIMD.

## Goals

- Expose `aggregate_greeks_full` and `select_walls` from `shared_rust_services`
- Replace `full_recompute` inner loop and `_select_walls_by_spot` with Rust calls
- Incremental `update_contract()` path remains in Python (already O(1) scalar, not a bottleneck)

## Non-Goals

- No changes to `AggregateGreeks` dataclass interface (frozen contract)
- No changes to `update_contract()` incremental path
- No changes to `GreeksMatrix` definition in `gpu_greeks_kernel.py`

## Rust API Signatures

```rust
// shared_rust_services/src/aggregation.rs

#[pyfunction]
pub fn aggregate_greeks_full(
    gammas: PyReadonlyArray1<f64>,
    vannas: PyReadonlyArray1<f64>,
    charms: PyReadonlyArray1<f64>,
    ois: PyReadonlyArray1<f64>,
    mults: PyReadonlyArray1<f64>,
    spots: PyReadonlyArray1<f64>,
    strikes: PyReadonlyArray1<f64>,
    is_call: PyReadonlyArray1<bool>,
    spot_ref: f64,
    scale: f64,       // _GEX_SCALE_MILLION = 1_000_000.0
) -> PyResult<PyObject>
// Returns dict: {net_gex, net_vanna, net_charm, total_call_gex, total_put_gex,
//                per_strike_call_gex: ndarray, per_strike_put_gex: ndarray}

#[pyfunction]
pub fn select_walls(
    strikes: PyReadonlyArray1<f64>,
    call_gex: PyReadonlyArray1<f64>,
    put_gex: PyReadonlyArray1<f64>,
    spot_ref: f64,
) -> PyResult<(f64, f64, f64, f64)>
// Returns (call_wall, put_wall, max_call_gex, max_put_gex)
// None → NaN (Python side maps NaN to None)
```

## Python Diff Sketch

```python
# streaming_aggregator.py

try:
    from shared_rust.services import aggregate_greeks_full as _rust_agg
    from shared_rust.services import select_walls as _rust_walls
    _RUST_AGG_AVAILABLE = True
except ImportError:
    _RUST_AGG_AVAILABLE = False

def full_recompute(self, matrix, strikes, is_call, ois, mults, spots):
    if _RUST_AGG_AVAILABLE:
        result = _rust_agg(matrix.gamma, matrix.vanna, matrix.charm,
                           ois, mults, spots, strikes, is_call,
                           spot_ref=self._spot_ref, scale=_GEX_SCALE_MILLION)
        # map result dict + _rust_walls(...) into AggregateGreeks
        ...
        return
    # existing NumPy loop unchanged as fallback

def _select_walls_by_spot(strikes, call_gex, put_gex, spot_ref):
    if _RUST_AGG_AVAILABLE:
        cw, pw, mcg, mpg = _rust_walls(strikes, call_gex, put_gex, spot_ref)
        return (None if math.isnan(cw) else cw), (None if math.isnan(pw) else pw), mcg, mpg
    # existing NumPy path unchanged
```

## Performance Targets

| Path | Current | Target |
|------|---------|--------|
| full_recompute, 300 contracts | ~8ms | <1ms (8×) |
| select_walls, 300 strikes | ~0.5ms | <0.05ms |

## Controls

1. Parity test: synthetic 100-contract chain comparing Rust vs NumPy to 1e-8 relative tolerance.
2. None-to-NaN contract: Python maps `float('nan')` wall values back to `None` for `AggregateGreeks`.
3. `aggregation.rs` ≤ 400 lines.

## Risk

LOW-MEDIUM. Wall selection uses argmax over positive GEX subset — pure comparisons, no float
approximation risk. Aggregation sum order differs from NumPy (Rust processes sequentially by
default); parity test uses absolute tolerance 1e-6 for sum (adequate for GEX in USD millions).
