# Project State

## Snapshot
- DateTime (ET): 2026-04-08 11:05:31 -04:00
- Branch: chore/sync-all-local-changes-20260313
- Last Commit: 3d3168f
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Hard-cut ActiveOptions to day cumulative volume policy (`volume`) and remove `current_volume` fallback behavior.
- Scope In: `shared_rust_services/src/active_options/support.rs`, ActiveOptions runtime diagnostics/logging, SOP sync, regression tests.
- Scope Out: L2 strategy logic and frontend rendering style changes.

## What Changed (Latest Session)
- Files:
  - `shared_rust_services/src/active_options/support.rs`
  - `shared/services/active_options_runtime.py`
  - `shared/services/active_options_runtime_metrics.py`
  - `app/loops/housekeeping_loop.py`
  - `app/tests/test_active_options_day_volume_policy.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L4_FRONTEND.md`
- Behavior:
  - ActiveOptions normalize/filter now strictly uses `volume` as day cumulative volume gate; removed `volume<=0 -> current_volume` fallback.
  - Added explicit normalized field `day_volume` for observability while keeping ranking/filter source unified.
  - Runtime diagnostics/logs switched from `volume_or_current_*` to hard-cut `day_volume_ge_min` counters.
- Verification:
  - `cargo build --release` (crate: `shared_rust_services`; actual target dir: `E:\US.market\cargo_target`).
  - `scripts/test/run_pytest.ps1 app/tests/test_active_options_day_volume_policy.py app/loops/tests/test_housekeeping_gpu_dedup.py -q` (7 passed).
  - `/debug/persistence_status` confirms runtime healthy and exposes `input_day_volume_ge_min_last`.

## Risks / Constraints
- Risk 1: strict `flow_active_min_volume=100` remains unchanged; sparse windows can still reduce real rows.
- Risk 2: replacing `shared_rust/services.pyd` requires process lock coordination; wrong artifact path can break imports.

## Next Action
- Immediate Next Step: run strict session validation and keep live watch on `filtered_candidates_count` + `input_day_volume_ge_min_last`.
- Owner: Codex
