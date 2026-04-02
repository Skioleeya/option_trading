PARENT_CHANGE_ID: impl-20260402-l1-bsm-numpy-rust-fallback
DEPENDENCY_ORDER: 32
BLOCKED_BY: impl-20260402-l1-bsm-numpy-rust-fallback (PyO3 array pattern reference)

## Why

Three microstructure modules in `l1_compute/` have explicit `rust_kernel` bridge hooks
reserved but inactive:

- `vpin_v2.py` (268L): `try: import l1_rust as _rust` — bridge stub exists, Python path active.
  Regime classification loop (`|buy_vol - sell_vol| / total_vol` per bucket × 3 timeframes)
  runs in Python on every trade tick.
- `vol_accel_v2.py` (204L): similar `rust_kernel` reservation; Shannon entropy
  `H = -Σ(p_i × log(p_i))` computed in Python.
- `entropy_filter.py` (143L): no bridge hook yet; pure Python Shannon gate run before BSM
  to reject low-information ticks.

These three functions share a common pattern: small float-array inputs, tight numerical
loops, no branching business logic. They are ideal for a single `microstructure.rs` module
in `shared_rust_services`, avoiding the need for a separate `l1_rust` crate.

Consolidating into `shared_rust_services` keeps the single-crate deployment model
established by Wave 18 (tactical, active_options, realized all live in `services.pyd`).

## What Changes

1. **Add** `shared_rust_services/src/microstructure.rs`:
   - `compute_vpin_regime(buy_vols: &[f64], sell_vols: &[f64], threshold_elevated: f64, threshold_toxic: f64) -> u8`
     Returns regime code: 0=NORMAL, 1=ELEVATED, 2=TOXIC.
   - `compute_vol_accel_entropy(price_buckets: &[f64]) -> (f64, f64)`
     Returns (entropy, ema_update).
   - `compute_entropy_gate(features: &[f64], min_entropy: f64) -> bool`
     Returns true = tick passes (sufficient information).
2. **Add** `mod microstructure; pub use microstructure::*;` to `lib.rs`.
3. **Edit** `l1_compute/microstructure/vpin_v2.py`:
   - Remove `import l1_rust` block; replace with `from shared_rust.services import compute_vpin_regime`.
   - In regime classification: delegate to `compute_vpin_regime(...)`, map u8 back to `VPINRegime` enum.
4. **Edit** `l1_compute/microstructure/vol_accel_v2.py`:
   - Replace entropy + EMA loop with `compute_vol_accel_entropy(...)`.
5. **Edit** `l1_compute/analysis/entropy_filter.py`:
   - Add Rust delegation in the entropy computation path.
6. Rebuild pyd.

## Scope

In:
- `shared_rust_services/src/microstructure.rs` — new Rust module
- `shared_rust_services/src/lib.rs` — `mod microstructure` declaration
- `l1_compute/microstructure/vpin_v2.py` — bridge activation
- `l1_compute/microstructure/vol_accel_v2.py` — bridge activation
- `l1_compute/analysis/entropy_filter.py` — new bridge

Out:
- `l1_compute/microstructure/bbo_v2.py` — out of scope (different algorithm, separate proposal if needed)
- `l1_compute/microstructure/depth_engine.py` — out of scope
- All L2/L3 layers — not touched

## Hard Governance Prohibitions

- No `unwrap()` in Rust; all PyO3 boundary functions use `?`
- `microstructure.rs` must stay ≤ 400 lines
- `l1_compute/` must not import `l2_decision/` or `l3_assembly/`
- `VPINRegime` Python enum values (str: "NORMAL"/"ELEVATED"/"TOXIC") must not change — downstream consumers depend on string identity

## Verification Gate

1. `python -c "from shared_rust.services import compute_vpin_regime, compute_vol_accel_entropy, compute_entropy_gate; print('micro-ok')"` passes.
2. VPIN regime parity: compute_vpin_regime result matches Python regime classification for 50 random bucket fixtures.
3. Entropy parity: compute_vol_accel_entropy entropy matches `H = -sum(p*log(p))` Python to 1e-12.
4. `pwsh scripts/test/run_pytest.ps1 l1_compute/tests/` — all tests pass.
5. `pwsh scripts/validate_session.ps1 -Strict` — exits 0.

## Rollback

```
git restore shared_rust_services/src/microstructure.rs shared_rust_services/src/lib.rs \
    l1_compute/microstructure/vpin_v2.py l1_compute/microstructure/vol_accel_v2.py \
    l1_compute/analysis/entropy_filter.py
```
Rebuild pyd. Python fallback remains in each file; regime string interface is unchanged.

## Risk

LOW-MEDIUM. Regime classification is threshold-based (no float precision issue). Entropy
computation must match Python `math.log` to 1e-12 (Rust `f64::ln` is identical precision).
Primary risk: VPINRegime enum string values must not change — guarded by contract test.
