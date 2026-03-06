# Project State

## Snapshot
- DateTime (ET): 2026-03-06 15:58:26 -05:00
- Branch: `master`
- Last Commit: `f587b9d`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `PARTIAL` (targeted regression suites pass; full e2e suite not run in this task)

## Current Focus
- Primary Goal: Audit SPY ATM IV real-time dataflow end-to-end and patch major hidden staleness risk.
- Scope In:
  - `l0_ingest/feeds/chain_state_store.py`
  - `l0_ingest/feeds/option_chain_builder.py`
  - `app/loops/compute_loop.py`
  - `l0_ingest/tests/test_chain_state_store.py`
  - `app/loops/tests/test_compute_loop_helpers.py`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/L2_DECISION_ANALYSIS.md`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `AGENTS.md`
  - `scripts/validate_session.ps1`
- Scope Out:
  - IV model calibration logic
  - Frontend DecisionEngine rendering semantics

## What Changed (Latest Session)
- Files:
  - `l0_ingest/feeds/chain_state_store.py`
  - `l0_ingest/feeds/option_chain_builder.py`
  - `app/loops/compute_loop.py`
  - `l0_ingest/tests/test_chain_state_store.py` (new)
  - `app/loops/tests/test_compute_loop_helpers.py` (new)
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/L2_DECISION_ANALYSIS.md`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `AGENTS.md`
  - `scripts/validate_session.ps1`
- Behavior:
  - Fixed major version-propagation gap: compute loop no longer hardcodes `l0_version=0`.
  - `ChainStateStore` now maintains a monotonic `version` and bumps on actual state mutations.
  - `OptionChainBuilder.fetch_chain()` now emits `version`, enabling L1->L2 to invalidate feature TTL cache on fresh snapshots.
  - Modularized snapshot-version parsing in compute loop via `_extract_snapshot_version()` helper.
  - Updated SOP docs with explicit 2026-03-06 version contract: L0 monotonic snapshot version -> L1 passthrough -> L2 cache invalidation -> L3 `spy_atm_iv` bridge constraints.
  - Added mandatory SOP sync contract to `AGENTS.md` (trigger/DoD/exemption/validation gate).
  - Enhanced `scripts/validate_session.ps1` with automatic SOP gate: runtime-layer file changes now require `docs/SOP` updates or `SOP-EXEMPT` in handoff.
- Verification:
  - `./scripts/test/run_pytest.ps1 l0_ingest/tests/test_chain_state_store.py app/loops/tests/test_compute_loop_helpers.py l2_decision/tests/test_feature_store.py::TestFeatureStore::test_cache_invalidated_when_snapshot_version_changes l2_decision/tests/test_feature_store.py::TestFeatureStore::test_atm_iv_updates_immediately_on_version_change -q` (11 passed)
  - `./scripts/validate_session.ps1` (pass, SOP sync gate reports `docs/SOP updated`)

## Risks / Constraints
- Risk 1: Full market-open end-to-end behavior still depends on runtime feed quality and was not validated in this code-only task.
- Risk 2: Existing unrelated dirty worktree files remain and were intentionally not modified/reverted.

## Next Action
- Immediate Next Step: Run an in-session live tick probe (or debug payload capture) to confirm `agent_g.data.spy_atm_iv` changes every snapshot-version advance.
- Owner: Codex / next agent
