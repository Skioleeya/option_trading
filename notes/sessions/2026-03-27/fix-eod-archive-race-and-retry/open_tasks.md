# Open Tasks

## Priority Queue
- [x] P0: remove the `16:01` EOD archive race against late source-file writes.
  - Owner: Codex
  - Definition of Done: scheduled runner waits for required source files to settle before generating final manifests.
  - Blocking: none
- [x] P1: make stale manifest metadata self-detecting and self-repairing inside the runner.
  - Owner: Codex
  - Definition of Done: runner verifies post-archive manifest sync and retries internally if archive output is stale or low quality.
  - Blocking: none
- [x] P1: preserve retry intent without relying exclusively on external Task Scheduler behavior.
  - Owner: Codex
  - Definition of Done: scheduler registration emits distinct `Primary/Retry` runner labels and the runner itself is robust enough to heal stale output.
  - Blocking: none
- [x] P1: re-apply host scheduled tasks so the fix is active on this machine.
  - Owner: Codex
  - Definition of Done: `EODBucketPrimary` and `EODBucketRetry` are re-registered with `StartWhenAvailable=True` and the guarded runner arguments.
  - Blocking: none

## Parking Lot
- [x] Root cause confirmed: the original runner was a single-shot call into `eod_bucket_archive.py`, with no source-settle wait and no post-archive sync verification.
- [x] Root cause confirmed: repo-side retry semantics were too weak because the `17:00` task reused the same blind runner and the repo had no internal fallback if that external retry never corrected stale output.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added settle-guard and manifest-sync helper scripts for EOD archive execution. (2026-03-27 22:58 ET)
- [x] Upgraded `run_eod_bucket.ps1` to guarded multi-attempt execution with post-archive verification. (2026-03-27 22:59 ET)
- [x] Verified `scripts/test/test_eod_archive_guards.py` and `scripts/test/test_eod_bucket_archive.py` both pass. (2026-03-27 23:00 ET)
- [x] Re-registered `EODBucketPrimary` and `EODBucketRetry` with `StartWhenAvailable=True` and verified the live task definition. (2026-03-27 23:13 ET)
- [x] Moved `EODBucketRetry` from `17:00` to `16:04` after conflict check; verified live task definition kept the same settle-guard arguments. (2026-03-27 23:23 ET)
