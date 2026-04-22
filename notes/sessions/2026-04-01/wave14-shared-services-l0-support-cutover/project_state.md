# Project State

## Snapshot
- DateTime (ET): 2026-04-01 18:56:35 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `7fb0f53`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: migrate deterministic `shared/services/l0_support` owners to `shared_rust.services_l0_support` and delete the retired Python files.
- Scope In:
  - `shared/services/l0_support/events/*`
  - `shared/services/l0_support/quality/*`
  - `shared/services/l0_support/sanitize/*`
  - `shared/services/l0_support/store/*`
  - direct consumers in `shared/services/l0_runtime/source/runtime/longport_adapter.py`, `l1_compute/analysis/greeks_engine.py`, and `tests/l0_support/*`
- Scope Out:
  - `shared/services/l0_support/rate_governor/*`
  - `shared/services/l0_support/observability/*`
  - `shared/services/l0_runtime` heavy owners

## What Changed (Latest Session)
- Files:
  - added Rust crate `shared_rust_l0_support/*`
  - added runtime artifact `shared_rust/services_l0_support.pyd`
  - rewired direct consumers to `shared_rust.services_l0_support`
  - deleted 13 retired Python files under `shared/services/l0_support/{events,quality,sanitize,store}`
- Behavior:
  - event models, quality reports, sanitize pipeline, statistical breaker, and MVCC store now resolve from Rust-only namespace `shared_rust.services_l0_support`
  - `LongportFeedAdapter` and L0 support tests no longer import the deleted Python owner files
- Verification:
  - `cargo build --release --target-dir C:\Users\Lenovo\.codex\memories\cargo_target\shared_rust_l0_support`
  - `cargo test --target-dir C:\Users\Lenovo\.codex\memories\cargo_target\shared_rust_l0_support`
  - `scripts/test/run_pytest.ps1 tests/l0_support/test_sanitize_pipeline.py tests/l0_support/test_statistical_breaker.py tests/l0_support/test_data_quality.py tests/l0_support/test_mvcc_store.py tests/l0_support/test_adaptive_governor.py tests/l0_runtime/test_quote_runtime.py`

## Risks / Constraints
- Risk 1: `shared_rust/services.pyd` remains externally locked, so this slice uses a dedicated Rust-only module name `shared_rust.services_l0_support`.
- Risk 2: `rate_governor` and `observability` still live under `shared/services/l0_support/*`; deleting `shared/services/l0_support/__init__.py` is deferred until those owners migrate.

## Next Action
- Immediate Next Step: migrate `shared/services/l0_support/rate_governor/*` and then clear `observability/*`.
- Owner: Codex
