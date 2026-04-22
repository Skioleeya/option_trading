PARENT_CHANGE_ID: none
DEPENDENCY_ORDER: 31
BLOCKED_BY: none

## Why

`l1_compute/aggregation/streaming_aggregator.py` runs on every market tick. Its core
`full_recompute()` path iterates over all N contracts with NumPy element-wise arithmetic
(`GreeksMatrix` arrays). Its `update_contract()` incremental path does O(1) scalar Python
arithmetic but triggers GIL-bound dict lookups per contract update.

The incremental aggregation kernel (GEX = gamma × OI × multiplier × spot²/scale, Vanna/Charm
sums) is purely numerical with no branching logic — ideal for Rust SIMD. Wall tracking
(`_select_walls_by_spot`) is an argmax operation on float arrays, also vectorizable.

Replacing both the `full_recompute` NumPy loop and the wall-tracking argmax with a single
Rust call is expected to yield 5–10× speedup per tick on chains ≥ 100 contracts, reducing
per-tick aggregation from ~8ms to <1ms.

## What Changes

1. **Add** `shared_rust_services/src/aggregation.rs`:
   - `aggregate_greeks_full(gammas, vannas, charms, ois, mults, spots, strikes, is_call, scale) -> AggResult`
   - `select_walls(strikes, call_gex, put_gex, spot_ref) -> WallResult`
   Both return Python-friendly named tuples or dicts via PyO3.
2. **Add** `mod aggregation; pub use aggregation::*;` to `shared_rust_services/src/lib.rs`.
3. **Edit** `l1_compute/aggregation/streaming_aggregator.py`:
   - `full_recompute()`: replace NumPy summation + `_select_walls_by_spot()` with
     `shared_rust.services.aggregate_greeks_full(...)`.
   - `_select_walls_by_spot()` helper: delegate to `shared_rust.services.select_walls(...)`.
   - Drift protection counter and state machine remain in Python (control flow, not compute).
4. Rebuild pyd.

## Scope

In:
- `shared_rust_services/src/aggregation.rs` — new Rust module
- `shared_rust_services/src/lib.rs` — `mod aggregation` declaration
- `l1_compute/aggregation/streaming_aggregator.py` — `full_recompute` and wall-tracking delegation

Out:
- `update_contract()` incremental scalar path — out of scope for Phase 1 (already O(1))
- `l1_compute/compute/gpu_greeks_kernel.py` (GreeksMatrix definition) — not touched
- All L2/L3 layers — not touched

## Hard Governance Prohibitions

- No `unwrap()` in Rust; use `?` propagation + PyO3 error mapping
- `aggregation.rs` must stay ≤ 400 lines
- No silent exception swallowing in Python delegation wrapper

## Verification Gate

1. `python -c "from shared_rust.services import aggregate_greeks_full, select_walls; print('agg-ok')"` passes.
2. Numerical parity: `full_recompute()` Rust result must match prior NumPy result to 1e-8 relative tolerance (pytest fixture with 100-contract synthetic chain).
3. `pwsh scripts/test/run_pytest.ps1 l1_compute/tests/` — all tests pass.
4. `pwsh scripts/validate_session.ps1 -Strict` — exits 0.

## Rollback

```
git restore shared_rust_services/src/aggregation.rs shared_rust_services/src/lib.rs \
    l1_compute/aggregation/streaming_aggregator.py
```
Rebuild pyd. Blast radius = aggregation module only; no upstream or downstream contract changes.

## Risk

MEDIUM-LOW. `full_recompute()` is already a calibration path (not the primary incremental path).
Worst case: Rust version produces slightly different float order-of-ops results →
caught by parity test before merge.
