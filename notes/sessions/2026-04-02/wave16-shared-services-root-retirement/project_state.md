# Project State

## Snapshot
- DateTime (ET): 2026-04-02 04:05
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `7fb0f53`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: Consolidate root shared service helpers onto the final `shared_rust.services` namespace and delete dead root Python shells.
- Scope In:
  - `shared_rust_services/*`
  - `app/routes/history.py`
  - `app/tests/test_history_schema_v2.py`
  - `l2_decision/feature_store/extractors_volatility.py`
  - `shared/services/research_feature_store.py`
  - `shared/services/research_feature_store_io.py`
  - `shared/services/__init__.py`
  - `shared/services/_native_service_support.py`
  - SOP/OpenSpec evidence for the root helper namespace
- Scope Out:
  - `shared/services/research_feature_store.py` owner port to Rust
  - `shared/services/header_volatility_context.py` owner port to Rust
  - `active_options`
  - `l0_runtime`

## What Changed (Latest Session)
- Files:
  - Finalized `shared_rust_services` as module `shared_rust.services`
  - Repointed former `shared_rust.services_root` consumers to `shared_rust.services`
  - Deleted dead root shells `shared/services/__init__.py` and `shared/services/_native_service_support.py`
- Behavior:
  - Root helper owners now expose only the final namespace `shared_rust.services`
  - Live `shared_rust.services_root` imports are reduced to zero
- Verification:
  - Rust build/import smoke passed
  - Direct consumer suites for history, feature-store extraction, and header volatility passed
  - Research feature store suite remains blocked by an ACL on `tmp/pytest_cache/research_store_tests`

## Risks / Constraints
- Risk 1: The worktree remains globally dirty from many prior slices; this session must stay scoped to the root-services namespace cutover.
- Risk 2: `tmp/pytest_cache/research_store_tests` denies child directory creation even after recreation, so the research-store suite cannot complete under the current local ACL.

## Next Action
- Immediate Next Step: Port the remaining root Python owners (`ResearchFeatureStore`, `HeaderVolatilityContextService`) into `shared_rust.services` and remove their Python files.
- Owner: Codex
