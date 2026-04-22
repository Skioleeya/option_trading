# Handoff

## Session Summary
- DateTime (ET): 2026-04-01 09:50:30 -04:00
- Goal: monitor the full Active Options L0-L4 path and eliminate the cause of frontend Top5 VOL rows staying below 100 in sparse live windows.
- Outcome: complete. The root cause was not L0 decode loss; it was the shared Active Options sparse fallback path. When `min_volume=100` left only 0-2 candidates, the runtime skipped real sub-threshold volume rows and filled the panel with turnover/OI synthetic rows, which frequently surfaced as `volume=1` style fake fillers. The fallback path now prefers real positive-volume sub-threshold contracts first, keeping the panel on real VOL-ranked rows while preserving the existing `min_volume=100` primary gate.

## What Changed
- Code / Docs Files:
  - `shared/services/active_options/runtime_service.py`
  - `shared/services/active_options/runtime_service_fallbacks.py`
  - `shared/services/active_options/runtime_service_support.py`
  - `shared/services/active_options/test_runtime_service_sparse_fallback.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `notes/sessions/2026-04-01/active-options-top5-vol-fix/project_state.md`
  - `notes/sessions/2026-04-01/active-options-top5-vol-fix/open_tasks.md`
  - `notes/sessions/2026-04-01/active-options-top5-vol-fix/handoff.md`
  - `notes/sessions/2026-04-01/active-options-top5-vol-fix/meta.yaml`
- Runtime / Infra Changes:
  - real-host strict backend restart was attempted first and failed on quote startup connectivity probe
  - real-host degraded retry was then launched per repo policy and used for final live verification
- Commands Run:
  - `powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId active-options-top5-vol-fix -Title "Fix Active Options TOP5 vol low values" -Scope implementation -UpdatePointer`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service_sparse_fallback.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py -q`
  - `python -m compileall shared/services/active_options/runtime_service.py shared/services/active_options/runtime_service_fallbacks.py shared/services/active_options/runtime_service_support.py shared/services/active_options/test_runtime_service_sparse_fallback.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -Degraded`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/verify_active_options_hotfix.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Verification
- Passed:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service_sparse_fallback.py -q` -> `2 passed`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py -q` -> `23 passed`
  - `python -m compileall ...` completed without compile errors for the changed Active Options files
  - live `/debug/persistence_status` after degraded host restart showed `rows_real_non_synthetic=5`, `rows_synthetic_fallback=0`, `live_rows=5`, `filtered_candidates_count=1`, `last_fallback_mode=subthreshold_volume`
  - live `/debug/active_options_capture` after the fix was version-aligned and showed a sparse window with `filtered_candidates_count=1` while displayed payload remained five real rows, including sub-threshold real-volume contracts tagged `fallback_reason=subthreshold_volume`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/verify_active_options_hotfix.ps1` -> `PASS` with `chain_size=102`, `placeholder=0`, `real=5`, `live_rows=5`, `degraded_rows=0`, `missing_gamma_rows=0`, `missing_turnover_rows=0`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> `Session validation passed.`
- Failed / Not Run:
  - the first strict real-host restart failed quote startup connectivity probing (`QuoteContext init failed: connect timeout`), so verification used the mandated degraded retry path

## Pending
- Must Do Next:
  - none for this Active Options defect
- Nice to Have:
  - stabilize strict startup quote connectivity so future live verification does not need degraded retry

## Debt Record (Mandatory)
- OPENSPEC-EXEMPT: targeted Active Options sparse fallback repair inside existing payload/diagnostic contracts; no schema or interface shape changed
- DEBT-EXEMPT: this session closed the sparse-window synthetic-volume defect without introducing new unchecked runtime debt
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-01
- DEBT-RISK: remaining operational risk is limited to intermittent strict startup broker connectivity, not the Active Options ranking logic fixed here
- DEBT-NEW: 0
- DEBT-CLOSED: 1
- DEBT-DELTA: -1
- DEBT-JUSTIFICATION: none
- RUNTIME-ARTIFACT-EXEMPT: no persisted runtime artifact changes beyond normal logs and temporary diagnostics
- Updated SOP Files:
  - `docs/SOP/L0_DATA_FEED.md`

## How To Continue
- Start Command:
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1`
- Key Logs:
  - `logs/backend_runtime.current.log`
- First File To Read:
  - `notes/sessions/2026-04-01/active-options-top5-vol-fix/handoff.md`
