# Project State

## Snapshot
- DateTime (ET): 2026-03-24 22:36:00 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `724efb3`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: Close the remaining L0 runtime governance gap by reconciling runtime subscribe semantics, centralizing normalization/metadata handling, and cleaning snapshot projection semantics.
- Scope In: `l0_ingest/v2/source/runtime/*`, `l0_ingest/v2/normalize/pipeline/*`, `l0_ingest/v2/services/subscription/*`, `l0_ingest/v2/services/sync/*`, `l0_ingest/v2/services/pollers/*`, `l0_ingest/v2/projection/snapshot/*`, `l0_ingest/v2/state/runtime/*`, `l0_ingest/tests/v2/*`, `docs/SOP/L0_DATA_FEED.md`, `openspec/changes/refactor-dependency-20260324-l0-runtime-contract-single-source/*`
- Scope Out: L1/L2/L3 behavior changes, app wiring changes, and frontend/UI work.

## What Changed (Latest Session)
- Files:
  - `l0_ingest/v2/source/runtime/quote_runtime.py`
  - `l0_ingest/v2/normalize/pipeline/sanitization.py`
  - `l0_ingest/v2/services/subscription/manager.py`
  - `l0_ingest/v2/services/subscription/metadata.py`
  - `l0_ingest/v2/services/sync/iv_baseline_sync.py`
  - `l0_ingest/v2/services/sync/support.py`
  - `l0_ingest/v2/services/pollers/tier2_poller.py`
  - `l0_ingest/v2/services/pollers/tier3_poller.py`
  - `l0_ingest/v2/services/orchestration/support.py`
  - `l0_ingest/v2/state/runtime/chain_state_store.py`
  - `l0_ingest/v2/projection/snapshot/components.py`
  - `l0_ingest/v2/projection/snapshot/payload.py`
  - `l0_ingest/tests/v2/test_quote_runtime_rust.py`
  - `l0_ingest/tests/v2/test_fetch_chain_components.py`
  - `l0_ingest/tests/v2/quote_runtime_support.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `openspec/changes/refactor-dependency-20260324-l0-runtime-contract-single-source/*`
- Behavior:
  - Rust runtime subscribe now reconciles the active session to the full desired symbol set instead of only tracking updates in Python.
  - IV/OI normalization is delegated to shared sanitizer helpers, and Tier2/Tier3 plus subscription selection now share a metadata resolver.
  - Snapshot projection no longer emits legacy `aggregate_greeks/ttm_seconds`, and `as_of/as_of_utc` now bind to the latest L0 source update timestamp.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/v2/test_quote_runtime_rust.py l0_ingest/tests/v2/test_quote_runtime_failover.py l0_ingest/tests/v2/test_fetch_chain_components.py l0_ingest/tests/v2/test_subscription_metadata_cache.py l0_ingest/tests/v2/test_iv_baseline_sync_support.py l0_ingest/tests/v2/test_feed_orchestrator_startup_stagger.py` -> `20 passed`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/v2` -> `71 passed`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> `PASS`

## Risks / Constraints
- Risk 1: Worktree contains unrelated pre-existing modifications and temp artifacts; this session must not revert unrelated changes.
- Risk 2: Strict validation still needs to be rerun after OpenSpec/session synchronization; any first failing gate must be fixed before handoff.

## Next Action
- Immediate Next Step: None. Session is ready for handoff.
- Owner: Codex
