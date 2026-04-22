# Project State

## Snapshot
- DateTime (ET): 2026-04-01 16:45:00 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `790471c`
- Environment:
  - Market: `OPEN/CLOSED`
  - Data Feed: `OK/DEGRADED/DOWN`
  - L0-L4 Pipeline: `OK/DEGRADED/DOWN`

## Current Focus
- Primary Goal: Migrate the next bounded `shared/services/l0_runtime/services/*` helper cluster to Rust-backed owners.
- Scope In:
  - `shared/services/l0_runtime/services/sync/support.py`
  - `shared/services/l0_runtime/services/repair/price_repair.py`
  - native loader/artifact ordering needed to consume Wave 7
- Scope Out:
  - `iv_baseline_sync.py` orchestration
  - `services/orchestration/*`
  - `services/pollers/*`
  - non-L0 modules

## What Changed (Latest Session)
- Files:
  - `l0_ingest/l0_rust/src/l0_sync_support.rs`
  - `l0_ingest/l0_rust/src/lib.rs`
  - `shared/services/l0_runtime/_native_extension_loader.py`
  - `shared/services/l0_runtime/_native_generated/__init__.py`
  - `shared/services/l0_runtime/services/sync/_native_sync_support.py`
  - `shared/services/l0_runtime/services/sync/support.py`
  - `shared/services/l0_runtime/services/repair/price_repair.py`
  - `tests/l0_runtime/test_iv_baseline_sync_support.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `openspec/changes/refactor-bloat-20260401-rust-shared-l0-migration-boundary/artifacts/shared-l0-boundary-evidence.md`
- Behavior:
  - Rust now owns IV/OI parse, clamp/batch helpers, rate-limit detection, price-repair candidate selection, and price-repair row apply summary.
  - Python sync/repair path now only keeps async runtime calls, limiter acquire, logging, and public facade behavior.
  - Process-wide native extension candidate order now includes `wave7` ahead of `wave6/wave5/wave4`.
- Verification:
  - `cargo test` passed.
  - targeted sync/repair/orchestrator pytest suite passed.
  - native probe confirmed Wave 7 `.pyd` and `l0_sync_*` exports.

## Risks / Constraints
- Risk 1: Versioned native artifact fallback is still required because the default generated extension path remains lock-prone.
- Risk 2: Orchestration and poller owners still remain in Python and must be cut in later bounded slices.

## Next Action
- Immediate Next Step: Enter `services/subscription/manager.py` or `services/orchestration/support.py` as the next bounded L0 services slice.
- Owner: Codex
