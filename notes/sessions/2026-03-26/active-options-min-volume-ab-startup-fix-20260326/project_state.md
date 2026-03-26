# Project State

## Snapshot
- DateTime (ET): 2026-03-26 14:44:54 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `fc3103948982fad2ded21d77bdb7a8d1425f2e44`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: keep the recovered backend healthy under strict `FLOW_ACTIVE_MIN_VOLUME=10`, preserve the new version-aligned capture path, and wait only for a naturally sparse live window.
- Scope In:
  - `app/lifespan.py`
  - `app/tests/test_lifespan_startup.py`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `logs/backend_runtime.elevated_strict.log`
  - `logs/backend_runtime.elevated_min10_strict.log`
  - `logs/backend_runtime.same_version_capture_elevated.log`
  - `tmp/active_options_artifact_min10.json`
  - `tmp/active_options_artifact_min10_warm.json`
  - `tmp/active_options_same_version_capture.json`
  - `tmp/active_options_same_version_sparse_capture.json`
- Scope Out:
  - no new ActiveOptions ranking/min-volume policy change beyond bounded live env override for A/B
  - no L0/L1/L2/L3 contract change
  - no frontend change

## What Changed (Latest Session)
- Files:
  - `app/lifespan.py`
  - `app/routes/health.py`
  - `scripts/diag/capture_same_version_active_options.py`
  - `app/tests/test_lifespan_startup.py`
  - `app/tests/test_health_route_diagnostics.py`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `notes/sessions/2026-03-26/active-options-min-volume-ab-startup-fix-20260326/project_state.md`
  - `notes/sessions/2026-03-26/active-options-min-volume-ab-startup-fix-20260326/open_tasks.md`
  - `notes/sessions/2026-03-26/active-options-min-volume-ab-startup-fix-20260326/handoff.md`
  - `notes/sessions/2026-03-26/active-options-min-volume-ab-startup-fix-20260326/meta.yaml`
- Behavior:
  - normalized `fetch_snapshot().spot` during `lifespan` startup so degraded startup no longer crashes when the initial snapshot returns `spot=None`
  - documented the startup null-normalization rule in the system overview SOP
  - recovered the backend with an elevated strict restart and verified Arrow IPC plus quote connectivity were healthy again
  - completed a bounded live `FLOW_ACTIVE_MIN_VOLUME` A/B: baseline strict threshold `100` versus strict threshold `10`
  - added a debug-only same-version capture endpoint plus `scripts/diag/capture_same_version_active_options.py` so raw chain and displayed Top5 can be sampled from the same server runtime version
  - captured aligned server-side artifacts at `tmp/active_options_same_version_capture.json` and `tmp/active_options_same_version_sparse_capture.json`; the latter is version-aligned but still not a sparse window
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/tests/test_lifespan_startup.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/tests/test_health_route_diagnostics.py -q`
  - `python -m compileall app/lifespan.py app/routes/health.py scripts/diag/capture_same_version_active_options.py app/tests/test_lifespan_startup.py app/tests/test_health_route_diagnostics.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -LogFile logs/backend_runtime.elevated_strict.log`
  - `$env:FLOW_ACTIVE_MIN_VOLUME='10'; powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -LogFile logs/backend_runtime.elevated_min10_strict.log`
  - `$env:FLOW_ACTIVE_MIN_VOLUME='10'; powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -LogFile logs/backend_runtime.same_version_capture_elevated.log`
  - `python scripts/diag/audit_intraday_core_flow.py --json`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/verify_active_options_hotfix.ps1`
  - `python scripts/diag/capture_same_version_active_options.py --json`

## Risks / Constraints
- Risk 1: the bounded A/B is complete and the same-version capture path now exists, but the sampled live windows were not sparse enough to force `sparse_window=true`, so the result is informative but not decisive for the original sparse-window hypothesis.
- Risk 2: `tmp/active_options_same_version_sparse_capture.json` is version-aligned but still reflects a non-sparse window (`46` filtered candidates vs `5` displayed real rows after a 180-second watch), so the strict sparse-window proof is still pending.

## Next Action
- Immediate Next Step: leave the backend healthy, keep polling `/debug/active_options_capture` during thinner live conditions, and replace `tmp/active_options_same_version_sparse_capture.json` with a truly sparse aligned sample once one appears.
- Owner: Codex
