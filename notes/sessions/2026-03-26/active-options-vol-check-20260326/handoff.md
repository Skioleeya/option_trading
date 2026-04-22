# Handoff

## Session Summary
- DateTime (ET): 2026-03-26 13:36:15 -04:00
- Goal: inspect whether live ActiveOptions `VOL` data is normal online without changing runtime behavior.
- Outcome: completed as an inspection-only session. Live `VOL` data is normal in the sampled window with respect to field presence, bounded values, and descending ordering, but the panel is not fully organic: the observed regular-hours window still relied on synthetic fallback rows to fill the five-slot contract. The strongest current root-cause signal points to `min_volume=100` being too strict for the active candidate pool in sparse windows, while the 3-tick switch gate only explains short-lived row carryover.

## What Changed
- Code / Docs Files:
  - `notes/sessions/2026-03-26/active-options-vol-check-20260326/project_state.md`
  - `notes/sessions/2026-03-26/active-options-vol-check-20260326/open_tasks.md`
  - `notes/sessions/2026-03-26/active-options-vol-check-20260326/handoff.md`
  - `notes/sessions/2026-03-26/active-options-vol-check-20260326/meta.yaml`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
- Runtime / Infra Changes:
  - none; reused the already-running backend and only collected evidence
- Commands Run:
  - `powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId active-options-vol-check-20260326 -Title "ActiveOptions VOL live check" -Scope "feature" -Owner "Codex" -ParentSession "2026-03-26/active-options-partial-fallback-runtime-repair" -UpdatePointer`
  - inline Python fetch of `http://127.0.0.1:8001/health` and `http://127.0.0.1:8001/debug/persistence_status`
  - `Get-Content logs/backend_runtime.current.log -Tail 300`
  - inline Python websocket sampler for one merged ActiveOptions snapshot
  - inline Python websocket sampler for 15 merged ActiveOptions frames
  - inline Python websocket sampler for a fresh sparse-window ActiveOptions snapshot
  - inline Python fetch of `active_options` from `/debug/persistence_status`
  - `python scripts/diag/check_active_options_no_data_cause.py --json`
  - `python scripts/diag/audit_intraday_core_flow.py --json`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/verify_active_options_hotfix.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`
- OPENSPEC-EXEMPT: inspection-only session; no runtime files under governed layers changed
- SOP-EXEMPT: inspection-only session; no behavior or contract change

## Verification
- Passed:
  - `/health` returned `200` and `/debug/persistence_status` returned live advancing diagnostics with:
    - `active_options.rows_total=5`
    - `active_options.rows_placeholder=0`
    - `active_options.rows_real=5`
    - `active_options.rows_real_non_synthetic` varying between `2` and `3`
    - `active_options.partial_fallback_count` actively increasing
    - `active_options.filtered_candidates_count=2` in the sampled sparse window
    - `stores.store.ws_volume_dropped=0`
    - `stores.store.ws_current_volume_dropped=0`
  - one merged websocket snapshot showed five rows with descending `VOL` values `500, 300, 208, 5, 5`; the last two rows were `FALLBACK_SYNTHETIC`
  - 15 merged websocket frames showed:
    - `order_violations=0`
    - `synthetic_frames=15/15`
    - `all_real_frames=0/15`
    - `avg_synthetic_rows=2`
    - representative `VOL` vectors such as `500, 300, 208, 2, 1`
  - a later live sparse snapshot showed the degradation could deepen to `1` real row plus `4` synthetic rows, with current payload rows:
    - `PUT 643.0 volume=300 quality=REAL`
    - `PUT 654.0 volume=10 quality=FALLBACK_SYNTHETIC`
    - `PUT 652.0 volume=2 quality=FALLBACK_SYNTHETIC`
    - `PUT 650.0 volume=1 quality=FALLBACK_SYNTHETIC`
    - `PUT 653.0 volume=1 quality=FALLBACK_SYNTHETIC`
  - the matching `/debug/persistence_status.active_options` sample at that point showed:
    - `rows_real_non_synthetic=1`
    - `rows_synthetic_fallback=4`
    - `live_rows=1`
    - `filtered_candidates_count=0`
    - `last_fallback_mode=turnover_open_interest`
    - `empty_filter_fallback_count` increasing
  - latest backend log tail now shows repeated empty-filter fallback rather than only partial fallback:
    - `[ActiveOptionsRuntimeService] No options above min_volume threshold — using turnover/open_interest fallback candidates=100 threshold=100`
    - followed by `[ActiveOptionsFlow] ... state=DEGRADED`
  - `python scripts/diag/check_active_options_no_data_cause.py --json` classified the live state as `ACTIVE_OPTIONS_DEGRADED` with primary reason: candidates become empty after `min_volume` filtering while runtime/feed health remains OK
  - `python scripts/diag/audit_intraday_core_flow.py --json` still passed the broader flow audit, showing runtime freshness and `rows_real>0`; this means the broad pipeline is healthy even while ActiveOptions quality is degraded
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/verify_active_options_hotfix.ps1` passed with:
    - `chain_size=112`
    - `active_options_total=5`
    - `placeholder=0`
    - `real=5`
    - `live_rows=2`
    - `degraded_rows=3`
    - `missing_turnover_rows=0`
    - final line: `[verify-hotfix] PASS`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py -q` passed: `23 passed in 0.81s`
  - code contract review confirmed:
    - `shared/services/active_options/runtime_service_support.py` falls back from `volume` to `current_volume` before min-volume filtering
    - the same helper clamps implausible volume values above `1_000_000_000` to zero
    - ranking remains `VOL desc -> turnover desc -> impact_index desc -> stable key`
    - `shared/services/active_options/runtime_service.py` applies `min_volume` filtering before both empty-filter and partial fallback handling
    - `shared/services/active_options/runtime_service_mutations.py` shows the switch-confirm gate only delays signature cutover; it does not create sparse filtered candidates
- Failed / Not Run:
  - no raw chain dump was captured for the exact sampled source versions, so this session did not prove whether the sparse winner pool comes from symbol-window coverage or simply from the live `min_volume=100` policy being too strict
  - no frontend browser screenshot was taken; websocket payload evidence was sufficient for this check

## Pending
- Must Do Next:
  - capture one raw chain vs displayed-top5 artifact for a sparse live source version
  - run a bounded A/B on `FLOW_ACTIVE_MIN_VOLUME` to confirm whether lowering the threshold materially increases non-synthetic winners
- Nice to Have:
  - add an ops artifact that prints displayed rows together with `filtered_candidates_count` and top raw candidates for one sampled source version

## Debt Record (Mandatory)
- DEBT-EXEMPT: this session closed the old online VOL verification carry item and classified the sparse-window root cause without introducing runtime mutations
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-27
- DEBT-RISK: operators may read `TOP BY VOL` as five fully organic live winners even though the current sparse window still relied on about two synthetic fallback rows per frame
- DEBT-NEW: 0
- DEBT-CLOSED: 2
- DEBT-DELTA: -2
- DEBT-JUSTIFICATION: closed the outstanding online VOL verification carry item and the first-pass root-cause classification; remaining work is bounded follow-up verification, not a new debt introduced here
- RUNTIME-ARTIFACT-EXEMPT: no new runtime artifacts beyond existing logs and temporary command output

## How To Continue
- Start Command:
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1`
- Key Logs:
  - `logs/backend_runtime.current.log`
- First File To Read:
  - `notes/sessions/2026-03-26/active-options-vol-check-20260326/handoff.md`
