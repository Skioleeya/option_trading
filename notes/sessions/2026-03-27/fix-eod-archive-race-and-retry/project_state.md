# Project State

## Snapshot
- DateTime (ET): 2026-03-27 23:24:00 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6dfd9c5`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `NOT ASSESSED`
  - L0-L4 Pipeline: `NOT ASSESSED`

## Current Focus
- Primary Goal: eliminate the EOD archive race so `16:01` does not index half-finished source files, and make retry coverage self-heal even if the external `17:00` task does not save the day.
- Scope In:
  - `scripts/ops/run_eod_bucket.ps1`
  - `scripts/ops/register_eod_bucket_task.ps1`
  - `scripts/diagnostics/wait_for_eod_sources_settle.py`
  - `scripts/diagnostics/check_eod_manifest_sync.py`
  - `scripts/test/test_eod_archive_guards.py`
  - `data/cold/daily/20260326/manifest.json`
  - `data/cold/by_regime/unclassified/20260326/manifest.json`
  - `data/cold/reports/20260326_quality.json`
  - `notes/context/*`
  - `notes/sessions/2026-03-27/fix-eod-archive-race-and-retry/*`
- Scope Out:
  - no L0-L4 runtime-layer code changes
  - no SOP or OpenSpec updates
  - no frontend/backend contract changes

## What Changed (Latest Session)
- Files:
  - `scripts/ops/run_eod_bucket.ps1`
  - `scripts/ops/register_eod_bucket_task.ps1`
  - `scripts/diagnostics/wait_for_eod_sources_settle.py`
  - `scripts/diagnostics/check_eod_manifest_sync.py`
  - `scripts/test/test_eod_bucket_guards.py`
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
- Behavior:
  - added a settle guard that waits until required EOD source files stop changing before archive generation
  - added a manifest sync checker so the runner verifies `source_files` still match disk after archive generation
  - upgraded the runner from single-shot execution to guarded multi-attempt execution, which removes dependence on an external `17:00` task for stale-manifest repair
  - re-registered the host scheduled tasks with `StartWhenAvailable=True`, `MultipleInstances=IgnoreNew`, `Primary=16:01`, and `Retry=16:04`
- Verification:
  - `scripts/test/test_eod_archive_guards.py` passed
  - existing `test_eod_bucket_archive.py` regression suite stayed green
  - real-date runner verification for `20260326` passed with settle guard + archive + sync check all green
  - live host task query confirmed both `EODBucketPrimary` and `EODBucketRetry` now point at the guarded runner command line with `StartWhenAvailable=True`
  - live host task query confirmed retry moved from `17:00` to `16:04` without changing settle-guard parameters (`30/900/5`, `MaxAttempts=2`)

## Risks / Constraints
- Risk 1: the exact historical reason why the host `2026-03-26 17:00` retry missed the stale manifest remains unprovable from repo evidence because historical Task Scheduler event data was unavailable.
- Risk 2: correctness no longer depends on that external retry path because the runner now waits for settle, verifies sync, and retries internally.

## Next Action
- Immediate Next Step: sync notes/context and run `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`.
- Owner: Codex
