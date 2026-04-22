# Project State

## Snapshot
- DateTime (ET): 2026-03-24 12:28:35 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `21b928c`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: Hard-cut the runtime path to a new `l0_ingest/v2` single-direction worktree and remove L0 runtime imports from `l1_compute`.
- Scope In: `l0_ingest/v2/*`, shared Arrow/SHM neutral modules, app wiring, active-options input adapter, Rust `l0_rust` source split, SOP/OpenSpec/session sync.
- Scope Out: L1/L2/L3 algorithm changes and unrelated live ATM/OI bug resolution.

## What Changed (Latest Session)
- Files:
  - `l0_ingest/v2/*`
  - `shared/contracts/option_chain_arrow.py`
  - `shared/system/rust_shm_bridge.py`
  - `app/container.py`
  - `app/lifespan.py`
  - `app/loops/compute_loop.py`
  - `shared/services/active_options/input_adapter.py`
  - `l1_compute/arrow/schema.py`
  - `l1_compute/rust_bridge.py`
  - `l0_ingest/l0_rust/src/*.rs`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `openspec/changes/refactor-dependency-20260324-l0-v2-single-direction-tree/*`
- Behavior:
  - App container now imports `OptionChainBuilder` from `l0_ingest.v2`.
  - L0 main path now uses `fetch_snapshot()` and only projects raw snapshot/diagnostic fields plus optional `chain_arrow`.
  - Arrow schema and Rust SHM bridge are now neutral shared modules rather than `l1_compute` dependencies.
  - Active Options input adapter no longer falls back to L0 `aggregate_greeks` or `ttm_seconds`.
  - Rust `l0_rust/src/lib.rs` was split into focused modules and is now under the 400-line gate.
- Verification:
  - `scripts/test/run_pytest.ps1 ...` targeted Python regressions green.
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> PASS.

## Risks / Constraints
- Risk 1: The old `l0_ingest/feeds/option_chain_builder.py` tree still exists in the repo as non-primary legacy code, so future work must avoid accidentally routing app back to it.
- Risk 2: Rust source split is structure-preserving but not yet compile-checked in this environment; strict validation will be the next gate.

## Next Action
- Immediate Next Step: Follow up in a separate cleanup session to retire or quarantine the legacy `l0_ingest/feeds/option_chain_builder.py` tree.
- Owner: Codex
