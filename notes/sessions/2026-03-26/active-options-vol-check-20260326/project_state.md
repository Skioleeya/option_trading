# Project State

## Snapshot
- DateTime (ET): 2026-03-26 13:36:15 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `fc3103948982fad2ded21d77bdb7a8d1425f2e44`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: verify whether live ActiveOptions `VOL` data is healthy online and separate value/order correctness from fallback-row occupancy.
- Scope In:
  - `/health`
  - `/debug/persistence_status`
  - `ws://127.0.0.1:8001/ws/dashboard`
  - `logs/backend_runtime.current.log`
  - `scripts/ops/verify_active_options_hotfix.ps1`
  - `shared/services/active_options/runtime_service_support.py`
  - `shared/services/active_options/test_runtime_service.py`
- Scope Out:
  - no runtime code changes
  - no threshold tuning or backend restart
  - no frontend contract changes

## What Changed (Latest Session)
- Files:
  - `notes/sessions/2026-03-26/active-options-vol-check-20260326/project_state.md`
  - `notes/sessions/2026-03-26/active-options-vol-check-20260326/open_tasks.md`
  - `notes/sessions/2026-03-26/active-options-vol-check-20260326/handoff.md`
  - `notes/sessions/2026-03-26/active-options-vol-check-20260326/meta.yaml`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
- Behavior:
  - confirmed live ActiveOptions `VOL` values are structurally healthy in the sampled window: all observed rows used bounded non-negative volumes and remained sorted descending by `VOL`
  - confirmed the online hotfix contract is still intact: `/debug/persistence_status.active_options` reported `rows_total=5`, `rows_placeholder=0`, `real=5`, `missing_turnover_rows=0`, and `verify_active_options_hotfix.ps1` passed
  - confirmed the panel is still frequently sustained by synthetic fallback rows rather than five organic min-volume winners; the sampled live window averaged two `FALLBACK_SYNTHETIC` rows per frame
  - root-caused the sparse-window behavior primarily to `flow_active_min_volume=100` being too strict for the live candidate pool in some windows: logs now show both `Partial fallback supplemented sparse filtered candidates=2 ... threshold=100` and repeated `No options above min_volume threshold — using turnover/open_interest fallback candidates=100 threshold=100`
  - identified the 3-tick switch gate as a secondary presentation effect rather than the primary cause: diagnostics can already show `filtered_candidates_count=0` while the displayed payload still retains one older real row until the new signature is confirmed
- Verification:
  - inline Python fetch of `/health` and `/debug/persistence_status`
  - inline Python websocket snapshot and 15-frame merged ActiveOptions audit
  - `python scripts/diag/check_active_options_no_data_cause.py --json`
  - `python scripts/diag/audit_intraday_core_flow.py --json`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/verify_active_options_hotfix.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py -q`

## Risks / Constraints
- Risk 1: the online `VOL` field is healthy, but current regular-hours snapshots still rely on partial fallback; operators could mistake `TOP BY VOL` for five fully organic live winners.
- Risk 2: diagnostics vary tick-to-tick between zero and two filtered winners; the remaining slots are currently being backfilled by `turnover_open_interest` fallback, and the 3-tick gate can briefly leave one older real row visible after the filter has already gone empty.

## Next Action
- Immediate Next Step: capture one raw chain vs displayed-top5 artifact and run a bounded A/B on the `min_volume` threshold to confirm whether the remaining issue is policy strictness or tracked-window coverage.
- Owner: Codex
