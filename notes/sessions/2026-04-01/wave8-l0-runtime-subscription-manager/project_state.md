# Project State

## Snapshot
- DateTime (ET): 2026-04-01 17:05:00 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `790471c`
- Environment:
  - Market: `OPEN/CLOSED`
  - Data Feed: `OK/DEGRADED/DOWN`
  - L0-L4 Pipeline: `OK/DEGRADED/DOWN`

## Current Focus
- Primary Goal: Cut `services/subscription/manager.py` into a Rust-backed bounded cluster.
- Scope In:
  - subscription cap clamp
  - option-chain row target/strike collect
  - subscription pool cap trim and strike-map filter
- Scope Out:
  - metadata TTL cache migration
  - orchestration/poller migration
  - non-L0 modules

## What Changed (Latest Session)
- Files:
  - `l0_ingest/l0_rust/src/l0_subscription_support.rs`
  - `l0_ingest/l0_rust/src/lib.rs`
  - `shared/services/l0_runtime/_native_generated/__init__.py`
  - `shared/services/l0_runtime/services/subscription/_native_subscription_support.py`
  - `shared/services/l0_runtime/services/subscription/manager.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `openspec/changes/refactor-bloat-20260401-rust-shared-l0-migration-boundary/artifacts/shared-l0-boundary-evidence.md`
- Behavior:
  - Rust now owns subscription cap clamp, target symbol collection from option-chain rows, and pool-trim/mandatory-keep semantics.
  - Python manager still owns metadata cache, async option-chain fetch, runtime subscribe, diagnostics, and public API.
  - Global generated-extension candidate order now prefers `wave8`.
- Verification:
  - `cargo test` passed.
  - subscription manager / cache / orchestrator pytest suite passed.
  - native probe confirmed Wave 8 `.pyd` and `l0_subscription_*` exports.

## Risks / Constraints
- Risk 1: Versioned native artifact fallback is still required because the default generated extension path remains lock-prone.
- Risk 2: metadata cache and orchestration owners remain Python and must be cut later in separate bounded slices.

## Next Action
- Immediate Next Step: Enter `services/orchestration/support.py` or `services/pollers/*` as the next bounded cluster.
- Owner: Codex
