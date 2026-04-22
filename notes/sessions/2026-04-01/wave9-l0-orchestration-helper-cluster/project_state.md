# Project State

## Snapshot
- DateTime (ET): 2026-04-01 17:28:00 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `790471c`
- Environment:
  - Market: `OPEN/CLOSED`
  - Data Feed: `OK/DEGRADED/DOWN`
  - L0-L4 Pipeline: `OK/DEGRADED/DOWN`

## Current Focus
- Primary Goal: Cut the bounded orchestration helper cluster into Rust-backed owners.
- Scope In:
  - `services/orchestration/support.py`
  - `services/orchestration/header_volatility_support.py`
  - generated-extension candidate order needed to consume Wave 9
- Scope Out:
  - `orchestrator.py` main loop
  - `pollers/*`
  - non-L0 modules

## What Changed (Latest Session)
- Files:
  - `l0_ingest/l0_rust/src/l0_orchestration_support.rs`
  - `l0_ingest/l0_rust/src/lib.rs`
  - `shared/services/l0_runtime/_native_generated/__init__.py`
  - `shared/services/l0_runtime/services/orchestration/_native_orchestration_support.py`
  - `shared/services/l0_runtime/services/orchestration/support.py`
  - `shared/services/l0_runtime/services/orchestration/header_volatility_support.py`
  - `tests/l0_runtime/test_header_volatility_support.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `openspec/changes/refactor-bloat-20260401-rust-shared-l0-migration-boundary/artifacts/shared-l0-boundary-evidence.md`
- Behavior:
  - Rust now owns symbol->strike fallback parse, SHM u64 read, next-trading-day, ratio normalization, valid-average, nearest-chain selection, and option IV decimal extraction.
  - Python helper layer still owns `CleanQuoteEvent` construction, store mutation, async quote fetch, limiter acquire, logging, and public helper APIs.
  - Global generated-extension candidate order now prefers `wave9`.
- Verification:
  - `cargo test` passed.
  - targeted orchestration helper and `FeedOrchestrator` pytest suite passed.
  - native probe confirmed Wave 9 `.pyd` and `l0_orch_*` exports.

## Risks / Constraints
- Risk 1: Versioned native artifact fallback is still required because the default generated extension path remains lock-prone.
- Risk 2: `orchestrator.py` main loop and poller owners remain Python and must be handled in later bounded slices.

## Next Action
- Immediate Next Step: Enter `services/orchestration/orchestrator.py` split-first planning or the poller helper cluster, whichever yields the smaller bounded slice.
- Owner: Codex
