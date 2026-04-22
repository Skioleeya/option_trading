# Project State

## Snapshot
- DateTime (ET): 2026-04-01 09:50:30 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `790471c`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Repair Active Options sparse-window fallback so the frontend Top5 VOL list stays on real volume-ranked rows instead of collapsing into synthetic `<100` fillers.
- Scope In: `shared/services/active_options/*` sparse fallback behavior, Active Options regression tests, SOP sync, live host verification.
- Scope Out: unrelated dirty worktree files, ATM decay tracker work, frontend rendering refactors.

## What Changed (Latest Session)
- Files:
  - `shared/services/active_options/runtime_service.py`
  - `shared/services/active_options/runtime_service_fallbacks.py`
  - `shared/services/active_options/runtime_service_support.py`
  - `shared/services/active_options/test_runtime_service_sparse_fallback.py`
  - `docs/SOP/L0_DATA_FEED.md`
- Behavior:
  - Sparse Active Options fallback now prefers real sub-threshold positive-volume contracts before turnover/OI synthetic fallback.
  - Real fallback rows are tagged with `fallback_reason=subthreshold_volume` but remain `row_quality=REAL`, so the panel can keep five live volume-ranked rows when only 1-2 contracts clear the hard `min_volume=100` gate.
- Verification:
  - Targeted Active Options pytest suites passed.
  - Real-host `/debug/persistence_status`, `/debug/active_options_capture`, and `scripts/ops/verify_active_options_hotfix.ps1` confirmed `rows_real_non_synthetic=5`, `rows_synthetic_fallback=0`, `live_rows=5` in a live sparse window after restart.
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed.

## Risks / Constraints
- Risk 1: The real-host strict restart still intermittently fails quote startup connectivity; this session had to follow the mandated degraded retry path before live verification.
- Risk 2: The worktree still contains unrelated user changes and generated artifacts outside this session; they were not modified.

## Next Action
- Immediate Next Step: none for this defect; continue from the session handoff if strict startup connectivity needs a separate repair.
- Owner: Codex
