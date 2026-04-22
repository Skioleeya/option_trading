# Project State

## Snapshot
- DateTime (ET): 2026-03-24 13:04:10 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `21b928c`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: Remove flat L0 business structure by absorbing legacy `l0_ingest/feeds/*` and top-level `subscription_manager.py` into a hierarchical `l0_ingest/v2` worktree.
- Scope In: `l0_ingest/v2/*`, `l0_ingest/tests/v2/*`, `l0_ingest/README.md`, `docs/SOP/L0_DATA_FEED.md`, `docs/SOP/SYSTEM_OVERVIEW.md`, OpenSpec/session/context sync.
- Scope Out: L1/L2/L3 algorithm changes and Rust runtime behavior changes beyond path relocation / import rewiring.

## What Changed (Latest Session)
- Files:
  - `l0_ingest/v2/*`
  - `l0_ingest/tests/v2/*`
  - `l0_ingest/README.md`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `openspec/changes/refactor-governance-20260324-l0-ingest-structure-governance/*`
- Behavior:
  - Legacy `l0_ingest/feeds/*` and `l0_ingest/subscription_manager.py` were removed; L0 runtime code now lives under a non-flat `v2` hierarchy.
  - `l0_ingest.v2` no longer depends on old `feeds` paths; package exports were made lazy/lightweight to avoid import-cycle regressions.
  - V2 runtime tests were mirrored into `l0_ingest/tests/v2/` to match the production tree.
  - Tracked `l0_ingest/l0_rust-0.1.0.dist-info/*` was removed from the source tree.
- Verification:
  - `python -m compileall l0_ingest/v2 l0_ingest/tests/v2 app shared` -> PASS
  - `scripts/test/run_pytest.ps1 l0_ingest/tests/v2 app/loops/tests/test_compute_loop_gpu_dedup.py app/loops/tests/test_housekeeping_gpu_dedup.py` -> `77 passed`

## Risks / Constraints
- Risk 1: The worktree is already dirty from prior sessions; this session must not revert unrelated app/shared/Rust changes.
- Risk 2: Historical notes/OpenSpec records still mention `option_chain_builder.py`; those are audit history, not runtime references.

## Next Action
- Immediate Next Step: Run `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`, then update session/context files with final validation evidence.
- Owner: Codex
