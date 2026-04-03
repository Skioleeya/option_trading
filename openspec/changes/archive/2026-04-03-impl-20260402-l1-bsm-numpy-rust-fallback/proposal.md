PARENT_CHANGE_ID: none
DEPENDENCY_ORDER: 30
BLOCKED_BY: none

## Why

`l1_compute/analysis/bsm_fast.py` operates on a 3-tier compute model:
Tier 1 = CuPy GPU, Tier 2 = Numba JIT, Tier 3 = NumPy pure-Python fallback.
`l1_compute/compute/gpu_greeks_kernel.py` mirrors this with its own NumPy fallback tier.

The NumPy tier (Tier 3) is the active baseline on this machine (no CUDA device confirmed
by `scripts/perf/diag_hardware.py`). It vectorises over strike arrays but remains in
Python GIL-space — each `np.exp`, `np.log`, `scipy.special.ndtr` call crosses Python
overhead boundaries per contract. On a 300-contract SPY chain this is ~15ms/tick.

Replacing the NumPy tier with a Rust SIMD kernel (AVX2/AVX-512 auto-dispatch via the
`std::arch` crate or `packed_simd` if available) is expected to yield 10–20× speedup
for the CPU path and eliminates the scipy ndtr dependency from the hot path.

## What Changes

1. **Add** `shared_rust_services/src/bsm.rs` — vectorized BSM Greeks via PyO3:
   `bsm_batch_numpy_tier(spots, strikes, ivs, ttms, is_call, r, q) -> dict[str, ndarray]`
2. **Add** `mod bsm; pub use bsm::*;` to `shared_rust_services/src/lib.rs`.
3. **Edit** `l1_compute/analysis/bsm_fast.py` — in the NumPy-tier branch (Tier 3),
   delegate to `shared_rust.services.bsm_batch_numpy_tier(...)` when available;
   keep the existing NumPy loop as the ultimate fallback (Rust import guarded by try/except).
4. **Edit** `l1_compute/compute/gpu_greeks_kernel.py` — same delegation in its
   NumPy fallback branch.
5. Rebuild `shared_rust_services` pyd (Codex uses `C:\Users\Lenovo\.codex\memories\cargo_target`).

## Scope

In:
- `shared_rust_services/src/bsm.rs` — new Rust module
- `shared_rust_services/src/lib.rs` — `mod bsm` declaration
- `l1_compute/analysis/bsm_fast.py` — Tier-3 branch delegation
- `l1_compute/compute/gpu_greeks_kernel.py` — NumPy fallback delegation

Out:
- GPU (CuPy) tier — not touched
- Numba JIT tier — not touched
- `l1_compute/analysis/greeks_engine.py` — no changes (calls bsm_fast.compute_greeks_batch, unaffected)
- L2 layers — no changes

## Hard Governance Prohibitions

- No `unwrap()` in Rust PyO3 boundary; use `.map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))?`
- No bare `try-except` swallowing errors without logging in Python bridge
- `l1_compute/` must not import from `l2_decision/` or `l3_assembly/` (layer law)
- New `bsm.rs` must stay ≤ 400 lines

## Verification Gate

1. `python -c "from shared_rust.services import bsm_batch_numpy_tier; print('bsm-ok')"` passes.
2. `python -c "from l1_compute.analysis.bsm_fast import compute_greeks_batch; r = compute_greeks_batch([560.],[560.],[0.2],[0.002],[True]); print('delta:', r['delta'])"` returns plausible delta (0.4–0.6 for ATM call).
3. `pwsh scripts/test/run_pytest.ps1 l1_compute/tests/` — all tests pass.
4. `pwsh scripts/validate_session.ps1 -Strict` — exits 0.
5. `python scripts/policy/check_openspec_chain.py` — exits 0.

## Rollback

```
git restore shared_rust_services/src/bsm.rs shared_rust_services/src/lib.rs \
    l1_compute/analysis/bsm_fast.py l1_compute/compute/gpu_greeks_kernel.py
```
Rebuild pyd from restored lib.rs. GPU and Numba tiers are unaffected; blast radius = Tier 3 only.

## Risk

MEDIUM. Numerical precision must match NumPy to within 1e-10 (relative).
Mitigation: include a pytest parametrized comparison test in `l1_compute/tests/test_bsm_rust_parity.py`
covering delta/gamma/vega/vanna/charm/theta for call and put across 50 random fixtures.
