# Project State

## Snapshot
- DateTime (ET): 2026-04-02 05:01:39 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `7fb0f53`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: retire the remaining root owners under `shared/services`
- Scope In:
  - `shared/services/research_feature_store.py`
  - `shared/services/research_feature_store_io.py`
  - `shared/services/header_volatility_context.py`
  - `shared_rust_services/*`
  - direct consumers in `app/`, `l3_assembly/`, and tests
- Scope Out:
  - `shared/services/active_options/*`
  - `shared/services/l0_runtime/*`
  - unrelated compute / UI migration

## What Changed (Latest Session)
- Files:
  - added `shared_rust_services/src/header_context.rs`
  - added `shared_rust_services/src/research_store.rs`
  - added `shared_rust_services/src/research_store_support.rs`
  - updated `shared_rust_services/src/lib.rs`
  - updated `shared_rust_services/Cargo.toml`
  - updated `app/routes/history.py`
  - updated `l3_assembly/reactor.py`
  - updated `l3_assembly/assembly/ui_state_tracker.py`
  - updated `l3_assembly/tests/test_research_feature_store.py`
  - updated `l3_assembly/tests/test_header_volatility_context.py`
  - deleted `shared/services/research_feature_store.py`
  - deleted `shared/services/research_feature_store_io.py`
  - deleted `shared/services/header_volatility_context.py`
- Behavior:
  - `ResearchFeatureStore`, `cleanup_tier`, and `HeaderVolatilityContextService` now live in `shared_rust.services`
  - `/api/research/features` and `/api/research/exports/*` now call the Rust-backed root service synchronously
  - root shared service consumers no longer depend on the retired Python owners
- Verification:
  - `l3_assembly/tests/test_research_feature_store.py` passed
  - `l3_assembly/tests/test_header_volatility_context.py`, `app/tests/test_history_schema_v2.py`, and `l2_decision/tests/test_feature_store.py` passed

## Risks / Constraints
- Risk 1: `tmp/pytest_cache` remains ACL-restricted for cache writes; pytest passes but warns on cache persistence.
- Risk 2: `shared/services` still contains `active_options` and `l0_runtime` migration waves.

## Next Action
- Immediate Next Step: retire `shared/services/active_options/*`, then continue `shared/services/l0_runtime/*`
- Owner: Codex
