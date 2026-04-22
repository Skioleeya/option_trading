# Handoff

## Session Summary
- DateTime (ET): 2026-03-27 23:24:00 -04:00
- Goal: fix the EOD archive race that let `16:01` manifests capture half-finished files and make retry coverage deterministic.
- Outcome: the EOD runner now waits for source settle, verifies manifest sync after archive generation, and retries internally when outputs are stale or low quality.

## What Changed
- Code / Docs Files:
  - `scripts/ops/run_eod_bucket.ps1`
  - `scripts/ops/register_eod_bucket_task.ps1`
  - `scripts/diagnostics/wait_for_eod_sources_settle.py`
  - `scripts/diagnostics/check_eod_manifest_sync.py`
  - `scripts/test/test_eod_archive_guards.py`
  - `data/cold/daily/20260326/manifest.json`
  - `data/cold/by_regime/unclassified/20260326/manifest.json`
  - `data/cold/reports/20260326_quality.json`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-03-27/fix-eod-archive-race-and-retry/project_state.md`
  - `notes/sessions/2026-03-27/fix-eod-archive-race-and-retry/open_tasks.md`
  - `notes/sessions/2026-03-27/fix-eod-archive-race-and-retry/handoff.md`
  - `notes/sessions/2026-03-27/fix-eod-archive-race-and-retry/meta.yaml`
- Runtime / Infra Changes:
  - none
- Commands Run:
  - `python -m py_compile scripts/diagnostics/wait_for_eod_sources_settle.py scripts/diagnostics/check_eod_manifest_sync.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 scripts/test/test_eod_archive_guards.py scripts/test/test_eod_bucket_archive.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/run_eod_bucket.ps1 -Date 20260326 -RunLabel Verify -SettleStableWindowSeconds 0 -SettleTimeoutSeconds 1 -SettlePollSeconds 0.1 -MaxAttempts 1`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/register_eod_bucket_task.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/register_eod_bucket_task.ps1 -Apply`
  - `Get-ScheduledTask -TaskName EODBucketPrimary,EODBucketRetry`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Verification
- Passed:
  - `scripts/test/test_eod_archive_guards.py` + `scripts/test/test_eod_bucket_archive.py`: `17 passed`
  - real-data verification for `20260326` runner output: settle guard returned `stable=true`, archive returned `quality=PASS`, and sync check returned `ok=true`
  - host scheduled tasks were re-registered successfully and verified as:
    `StartWhenAvailable=True`, `MultipleInstances=IgnoreNew`, distinct `-RunLabel Primary|Retry`
  - host scheduled tasks now run at `Primary=16:01` and `Retry=16:04`; settle-guard parameters stayed `30/900/5` with `MaxAttempts=2`
- Failed / Not Run:
  - historical Task Scheduler event evidence for `2026-03-26` was not available, so the exact missed-retry mechanism remains external

SOP-EXEMPT: ops tooling only; no runtime-layer behavior in L0-L4 changed.
OPENSPEC-EXEMPT: scripts/data repair only; no runtime-layer contract or product behavior change.

## Pending
- Must Do Next:
  - monitor the next live trading-day `16:01` and `16:04` task executions for one clean cycle of evidence
- Nice to Have:
  - add a persistent task-run status artifact if future ops needs exact proof that the external retry executed

## Debt Record (Mandatory)
- DEBT-EXEMPT: session complete with no unresolved delivery debt; remaining monitoring is operational follow-through only
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-27
- DEBT-RISK: low; runner and host tasks are both updated, leaving only future-run monitoring
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: not required; no net new debt was introduced
- RUNTIME-ARTIFACT-EXEMPT: refreshed `data/cold/*` outputs are intended cold-storage deliverables for verification, not transient runtime artifacts

## How To Continue
- Start Command:
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/register_eod_bucket_task.ps1 -Apply`
- Key Logs:
  - runner output prefixes `[EODBucketRunner]`, `[EODSettle]`, and `[EODSync]`
- First File To Read:
  - `scripts/ops/run_eod_bucket.ps1`
