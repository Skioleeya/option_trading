# Project State

## Snapshot
- DateTime (ET): 2026-03-12 15:13:45 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `UNVERIFIED`
  - L0-L4 Pipeline: `UNVERIFIED`

## Current Focus
- Primary Goal: Integrate zero-additional-call-cost LongPort official option diagnostics into research metadata.
- Scope In:
  - Extend Tier2/Tier3 caches with official `premium` and `standard`.
  - Summarize those fields in `compute_loop` metadata and persist them as research feature columns.
  - Update SOP and session records to reflect that `historical_volatility_decimal` is still deferred from main research path.
- Scope Out:
  - No new `option_quote()` expansion for official `historical_volatility`.
  - No L1 live-compute schema changes.
  - No changes to live decision logic or L3/L4 presentation contracts.

## What Changed (Latest Session)
- Files:
  - `l0_ingest/feeds/tier2_poller.py`
  - `l0_ingest/feeds/tier3_poller.py`
  - `app/loops/compute_loop.py`
  - `app/loops/tests/test_compute_loop_helpers.py`
  - `shared/services/research_feature_store.py`
  - `l3_assembly/tests/test_research_feature_store.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/IV_METRICS_MAP.md`
- Behavior:
  - Tier2/Tier3 caches now retain official `premium` and `standard` without adding new REST calls.
  - L0 snapshot metadata now carries summarized LongPort option diagnostics into L1 extra metadata.
  - Research feature store now persists explicit LongPort diagnostics columns for Tier2/Tier3 contract counts, standard ratios, and average premium.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/loops/tests/test_compute_loop_helpers.py l3_assembly/tests/test_research_feature_store.py l2_decision/tests/test_feature_store.py shared/tests/test_realized_volatility.py`
  - Result: `69 passed`

## Risks / Constraints
- Risk 1: Official `historical_volatility_decimal` still remains only in L0 contract preservation; using it in research/runtime would require extra `option_quote()` adoption and quota review.
- Risk 2: Tier2/Tier3 cache changes are covered indirectly via helper/research tests, but there is still no dedicated poller unit test for `premium/standard` rows.

## Next Action
- Immediate Next Step: Decide whether to pay the extra L0 contract complexity needed to move official `historical_volatility_decimal` into main research/runtime features.
- Owner: Codex / next implementing agent
