# Project State

## Snapshot
- DateTime (ET): 2026-03-12 22:30:58 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `UNVERIFIED`
  - L0-L4 Pipeline: `UNVERIFIED`

## Current Focus
- Primary Goal: Implement research-only integration of official `historical_volatility_decimal` without adding REST call surfaces.
- Scope In:
  - Reuse existing `FeedOrchestrator` volume-research `option_quote()` responses to aggregate official HV diagnostics.
  - Propagate official HV diagnostics through `fetch_chain` -> `compute_loop` metadata -> research feature store columns.
  - Add targeted tests for orchestrator diagnostics extraction, compute-loop metadata, and research feature persistence.
- Scope Out:
  - No changes to `vol_risk_premium` / `vrp_realized_based` live decision semantics.
  - No schema changes to `CleanQuoteEvent`, `EnrichedSnapshot` core contract, or SHM layout.
  - No additional polling loops or new LongPort REST call types.

## What Changed (Latest Session)
- Files:
  - `l0_ingest/feeds/feed_orchestrator.py`
  - `l0_ingest/feeds/option_chain_builder.py`
  - `app/loops/compute_loop.py`
  - `shared/services/research_feature_store.py`
  - `l0_ingest/tests/test_feed_orchestrator_startup_stagger.py`
  - `app/loops/tests/test_compute_loop_helpers.py`
  - `l3_assembly/tests/test_research_feature_store.py`
  - `docs/SOP/L0_DATA_FEED.md`
- Behavior:
  - FeedOrchestrator now aggregates official HV diagnostics (`official_hv_decimal`, sample count, sync timestamp) from existing research `option_quote()` batches.
  - `fetch_chain()` now carries `official_hv_diagnostics`; compute-loop metadata now emits official HV fields and computed age seconds.
  - Research feature rows now persist official HV diagnostics columns and derived `vrp_official_hv_based` (research-only).
- Verification:
  - `scripts/test/run_pytest.ps1 l0_ingest/tests/test_feed_orchestrator_startup_stagger.py app/loops/tests/test_compute_loop_helpers.py l3_assembly/tests/test_research_feature_store.py`
  - Result: `24 passed`

## Risks / Constraints
- Risk 1: Official HV refresh cadence follows existing volume-research loop (~15 min), so diagnostics may be stale intra-window.
- Risk 2: Existing repository has many unrelated dirty changes; this session intentionally only touched the files above.

## Next Action
- Immediate Next Step: Run strict session validation and sync context indices with this completed session.
- Owner: Codex
