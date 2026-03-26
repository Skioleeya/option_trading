# Project State

## Snapshot
- DateTime (ET): 2026-03-26 10:17:52 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `c279f84d5c4aa760b05e66192aba5e4875c46d71`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: repair ActiveOptions so a valid shared input snapshot can conservatively supplement sparse min-volume winners instead of falling through to long-lived placeholder rows.
- Scope In:
  - `shared/services/active_options/runtime_service.py`
  - `shared/services/active_options/runtime_service_support.py`
  - new shared fallback/diagnostics helpers
  - targeted runtime and diagnostics tests
- Scope Out:
  - no frontend contract redesign
  - no min-volume threshold relaxation
  - no live backend restart or intraday deployment validation in this session

## What Changed (Latest Session)
- Files:
  - `scripts/diag/replay_active_options_partial_fallback.py`
  - `shared/services/active_options/runtime_service.py`
  - `shared/services/active_options/runtime_service_support.py`
  - `shared/services/active_options/runtime_service_fallbacks.py`
  - `shared/services/active_options/runtime_service_diagnostics.py`
  - `shared/services/active_options/test_runtime_service_partial_fallback.py`
  - `app/tests/test_health_route_diagnostics.py`
  - `notes/sessions/2026-03-26/active-options-partial-fallback-runtime-repair/project_state.md`
  - `notes/sessions/2026-03-26/active-options-partial-fallback-runtime-repair/open_tasks.md`
  - `notes/sessions/2026-03-26/active-options-partial-fallback-runtime-repair/handoff.md`
  - `notes/sessions/2026-03-26/active-options-partial-fallback-runtime-repair/meta.yaml`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
- Behavior:
  - kept `flow_active_min_volume=100` as the primary filter
  - added conservative partial fallback so `0 < filtered < limit` now supplements missing rows from turnover/OI-ranked candidates instead of immediately accepting a sparse set and padding placeholders
  - restored synthetic tagging for both empty-filter fallback and the new partial-fallback rows
  - extended `/debug/persistence_status.active_options` diagnostics with sparse-candidate and partial-fallback counters
  - restarted the backend on the patched workspace and re-sampled live ActiveOptions websocket init payloads after restart
  - added a standalone replay script that drives a sparse `0 < filtered < 5` chain through `ActiveOptionsRuntimeService` and prints the resulting diagnostics/rows
- Verification:
  - `python -m py_compile ...` passed for the edited runtime and test modules
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service_partial_fallback.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/tests/test_health_route_diagnostics.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1`
  - post-restart `/debug/persistence_status` showed `rows_real=5`, `rows_placeholder=0`, `filtered_candidates_count=65`, `partial_fallback_count=0`
  - 12 consecutive websocket `dashboard_init` snapshots all showed `real_rows=5` and a real slot-5 contract (`SPY|PUT|677.0`)
  - `python scripts/diag/replay_active_options_partial_fallback.py` proved the sparse branch independently with `filtered_candidates_count=2`, `supplemented_rows=3`, and `partial_fallback_count=1`

## Risks / Constraints
- Risk 1: the post-restart live window had `filtered_candidates_count=65`, so it verified slot-5 continuity but did not naturally exercise the partial-fallback branch in production cadence.
- Risk 2: partial fallback remains intentionally conservative; if the chain genuinely lacks enough turnover/OI candidates, placeholders can still appear.
- Risk 3: the visible `SYM` field intentionally stays `SPY`; synthetic-row tagging now depends on an internal `contract_symbol` key rather than the display symbol.

## Next Action
- Immediate Next Step: if needed, wait for a naturally sparse live market window and compare its runtime diagnostics against the new replay script baseline; current replay and post-restart live checks are already sufficient to prove the fix path.
- Owner: Codex
