# Handoff

## Session Summary
- DateTime (ET): 2026-03-26 14:44:54 -04:00
- Goal: unblock the pending ActiveOptions `FLOW_ACTIVE_MIN_VOLUME` A/B by fixing the restart-time crash, restoring a healthy backend, and collecting enough live evidence to judge whether sparse ActiveOptions output is threshold-policy driven.
- Outcome: the startup crash is fixed, the backend was recovered via elevated strict restart, and the bounded live `FLOW_ACTIVE_MIN_VOLUME` A/B was completed under healthy runtime conditions. A debug-only same-version capture endpoint and script now expose raw input chain plus displayed Top5 from the same server version, and aligned artifacts were captured successfully. Lowering the threshold from `100` to `10` materially widened the candidate pool in sampled windows, but both sampled windows still produced `5` real rows and `0` synthetic fallback rows. A further 180-second aligned capture watch still did not hit `sparse_window=true`; the best aligned sample only tightened to `46` filtered candidates versus `5` displayed real rows, so the remaining blocker is market conditions, not missing capture infrastructure.

## What Changed
- Code / Docs Files:
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
- Runtime / Infra Changes:
  - elevated strict restart recovered a healthy backend with Arrow IPC + quote connectivity
  - elevated strict restart with inherited `FLOW_ACTIVE_MIN_VOLUME=10` kept the backend healthy during the bounded A/B window
  - one-off privileged live-reader captures wrote `tmp/active_options_artifact_min10.json` and `tmp/active_options_artifact_min10_warm.json`
  - debug route `/debug/active_options_capture` now returns version-aligned raw ActiveOptions input plus displayed Top5 for diagnostics
  - elevated strict/min10 restart with the new route recovered `:8001` again after the failed non-elevated restart attempt
- Commands Run:
  - `powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId active-options-min-volume-ab-startup-fix-20260326 -Title "ActiveOptions min-volume A/B startup fix" -Scope "feature" -Owner "Codex" -ParentSession "2026-03-26/active-options-vol-check-20260326" -UpdatePointer`
  - `python scripts/diag/check_active_options_no_data_cause.py --json`
  - `python scripts/diag/audit_intraday_core_flow.py --json`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -HotfixActiveOptions -HotfixMinVolume 10 -LogFile logs/backend_runtime.ab_min10.log`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -LogFile logs/backend_runtime.elevated_strict.log`
  - `$env:FLOW_ACTIVE_MIN_VOLUME='10'; powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -LogFile logs/backend_runtime.elevated_min10_strict.log`
  - `python scripts/diag/audit_intraday_core_flow.py --json`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/verify_active_options_hotfix.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/tests/test_lifespan_startup.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/tests/test_health_route_diagnostics.py -q`
  - `python -m compileall app/lifespan.py app/routes/health.py scripts/diag/capture_same_version_active_options.py app/tests/test_lifespan_startup.py app/tests/test_health_route_diagnostics.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`
  - privileged one-off raw-chain artifact captures written to `tmp/active_options_artifact_min10.json` and `tmp/active_options_artifact_min10_warm.json`
  - `$env:FLOW_ACTIVE_MIN_VOLUME='10'; powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -LogFile logs/backend_runtime.same_version_capture_elevated.log`
  - `python scripts/diag/capture_same_version_active_options.py --json`
  - 180-second polling watch against `/debug/active_options_capture` with aligned best-sample persistence to `tmp/active_options_same_version_sparse_capture.json`

## Verification
- Passed:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/tests/test_lifespan_startup.py -q` -> `1 passed in 6.04s`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/tests/test_health_route_diagnostics.py -q` -> `2 passed in 0.94s`
  - `python -m compileall app/lifespan.py app/routes/health.py scripts/diag/capture_same_version_active_options.py app/tests/test_lifespan_startup.py app/tests/test_health_route_diagnostics.py` completed without compile errors
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -LogFile logs/backend_runtime.elevated_strict.log` restored a healthy backend; `/debug/persistence_status` showed `transport.status=OK`, `gateway.connected=true`, `chain_size=102`, `rows_real_non_synthetic=5`, `rows_synthetic_fallback=0`, `min_volume_threshold=100`
  - `$env:FLOW_ACTIVE_MIN_VOLUME='10'; powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -LogFile logs/backend_runtime.elevated_min10_strict.log` kept the backend healthy with strict startup; sampled `/debug/persistence_status` windows showed `min_volume_threshold=10`, `rows_real_non_synthetic=5`, `rows_synthetic_fallback=0`, candidate counts between `45` and `88`, and current healthy state `live_rows=5`
  - `$env:FLOW_ACTIVE_MIN_VOLUME='10'; powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -LogFile logs/backend_runtime.same_version_capture_elevated.log` recovered `:8001` with the new debug route loaded; `/health` returned `200`, `/debug/persistence_status` showed `transport.status=OK`, `gateway.connected=true`, `min_volume_threshold=10`, and `/debug/active_options_capture` returned `input_source_version=306`, `payload_source_version=306`, `aligned=true`
  - `python scripts/diag/capture_same_version_active_options.py --json` produced `tmp/active_options_same_version_capture.json` with `aligned=true`, `chain_size=100`, `filtered_candidates_count=86`, `displayed_real_rows=5`
  - the 180-second aligned watch persisted `tmp/active_options_same_version_sparse_capture.json`; it stayed `aligned=true` and reached a best live sample of `46` filtered candidates versus `5` displayed real rows
  - `python scripts/diag/audit_intraday_core_flow.py --json` passed under both healthy baseline and healthy min10 runtime
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/verify_active_options_hotfix.ps1` passed under healthy min10 runtime
  - `tmp/active_options_artifact_min10_warm.json` preserved a directional snapshot: server payload stayed `5` real / `0` synthetic with `min_volume_threshold=10`, while the independent live reader warmed to `chain_size=83`
  - reproduction evidence showed the pre-fix failure was real and specific:
    - `logs/backend_runtime.ab_min10.log` contained `TypeError: '>' not supported between instances of 'NoneType' and 'int'`
    - the stack pointed at `app/lifespan.py` during initial spot/bootstrap handling
- Failed / Not Run:
  - no aligned `sparse_window=true` artifact was captured yet; the capture path is now present, but current live conditions never tightened below `46` filtered candidates in the 180-second watch
  - the non-elevated restart attempted during route bring-up failed strict startup connectivity and temporarily dropped `:8001`; `logs/backend_runtime.same_version_capture.log` records that failure, and `logs/backend_runtime.same_version_capture_elevated.log` records the successful recovery

## Pending
- Must Do Next:
  - keep polling `/debug/active_options_capture` until a genuine aligned `sparse_window=true` window appears, then refresh `tmp/active_options_same_version_sparse_capture.json`
  - decide whether to keep the live backend at `FLOW_ACTIVE_MIN_VOLUME=10` or revert to the default threshold after artifact capture
- Nice to Have:
  - add a strict-hotfix start path that does not implicitly force degraded startup
  - make the A/B diagnostic output report the server-side `min_volume_threshold` directly instead of reading local settings only

## Debt Record (Mandatory)
- DEBT-EXEMPT: the session fixed the startup bug and completed the bounded live restart/A-B work without introducing new runtime contract debt; the only remaining delivery risk is capture timing for a same-version sparse-window proof artifact
- DEBT-EXEMPT: the session fixed the startup bug, completed the bounded live restart/A-B work, and added a debug-only aligned capture surface without changing runtime contracts; the only remaining delivery risk is waiting for a naturally sparse live window
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-27
- DEBT-RISK: an aligned sparse-window proof artifact is still missing, but the remaining risk is now market-timing only because the capture path and aligned artifacts are already in place
- DEBT-NEW: 0
- DEBT-CLOSED: 4
- DEBT-DELTA: -4
- RUNTIME-ARTIFACT-EXEMPT: no new persisted runtime artifacts beyond existing log files and temporary command output
- OPENSPEC-EXEMPT: targeted startup null-guard repair plus debug-only ActiveOptions capture diagnostics; no runtime contract/schema/interface change
- Updated SOP Files:
  - `docs/SOP/SYSTEM_OVERVIEW.md`

## How To Continue
- Start Command:
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1`
- Key Logs:
  - `logs/backend_runtime.elevated_strict.log`
  - `logs/backend_runtime.elevated_min10_strict.log`
  - `logs/backend_runtime.ab_min10.log`
  - `logs/backend_runtime.same_version_capture.log`
  - `logs/backend_runtime.same_version_capture_elevated.log`
- First File To Read:
  - `notes/sessions/2026-03-26/active-options-min-volume-ab-startup-fix-20260326/handoff.md`
