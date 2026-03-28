# Project State

## Snapshot
- DateTime (ET): 2026-03-27 23:44:35 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6dfd9c5`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Restore `20260312` raw source into the official data path and complete a formal cold re-archive for that date.
- Scope In: Canonical source search, data recovery into `data/research/raw/`, `20260312` cold reclassification, by-regime cleanup, sync verification.
- Scope Out: Runtime code changes and further classifier logic changes.

## What Changed (Latest Session)
- Files: Restored `data/research/raw/raw_20260312.parquet`; rewrote `data/cold/daily/20260312/manifest.json`, `data/cold/reports/20260312_quality.json`, and `data/cold/by_regime/trend_day/20260312/manifest.json`; removed stale `data/cold/by_regime/unclassified/20260312`.
- Behavior: `20260312` now classifies formally as `trend_day` on the current real source set under `data/`.
- Verification: EOD archive rerun succeeded with `quality=PASS`; manifest sync check returned `ok=true`.

## Risks / Constraints
- Risk 1: The old 2026-03-12 cold manifest referenced an earlier source snapshot that no longer exists on the host; the restored raw is the only surviving local raw candidate, not a byte-identical match to the March 12 manifest.
- Risk 2: `20260312` formal cold outputs now reflect the current recovered source set, so historical hashes/row counts differ from the original stale `unclassified` archive.

## Next Action
- Immediate Next Step: No further recovery is required for `20260312`; future work, if any, is to decide whether any other stale pre-race cold days need the same treatment.
- Owner: Codex
