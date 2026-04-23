# Project State

## Snapshot
- DateTime (ET): 2026-04-23 09:54
- Branch: `master`
- Last Commit: `b6ef4ff`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Clear the fresh-backend startup fatal that trips `research_persistence` on the first live compute tick.
- Scope In: Compute-loop/L3 spot continuity, strict startup validation, real-host `start-all` verification.
- Scope Out: Historical backfill, canonical schema redesign, unrelated frontend/runtime changes already present in the worktree.

## What Changed (Latest Session)
- Files:
  - `app/loops/compute_loop.py`
  - `app/loops/snapshot_spot.py`
  - `app/loops/tests/test_compute_loop_gpu_dedup.py`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
- Behavior:
  - Reconciles a valid L0 `spot` onto the L1 snapshot when the first bypassed `EnrichedSnapshot` arrives with `spot<=0`, preventing L3 assembly and research persistence from seeing `0.0`.
- Verification:
  - `python manage.py run-pytest app/loops/tests/test_compute_loop_gpu_dedup.py app/tests/test_health_route_diagnostics.py scripts/test/test_active_options_strict_no_fallback.py` -> `11 passed`
  - `python manage.py validate-session --strict` -> runtime quality/open-spec/SOP gates green; final rerun pending after session/context closeout
  - `python manage.py start-all` -> Redis `6380` / Backend `8001` / Frontend `5173` all ready
  - `GET /health` -> `200`, `fatal_runtime_error=null`, `research_persistence.healthy=true`
  - `GET /debug/persistence_status` -> `failed_computations=0`, `rows_persisted_today=19`, `active_options.halted=false`

## Risks / Constraints
- Risk 1: Worktree is already dirty from prior sessions; edits must remain scoped and must not disturb unrelated user changes.
- Risk 2: Final evidence requires real-host `start-all`; sandbox-local reads alone are not sufficient.

## Next Action
- Immediate Next Step: Finalize session/context sync and rerun `validate-session --strict`.
- Owner: Codex
