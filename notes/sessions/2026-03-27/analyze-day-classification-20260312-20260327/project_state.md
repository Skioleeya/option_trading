# Project State

## Snapshot
- DateTime (ET): 2026-03-27 23:25:15 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6dfd9c5`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Analyze full-day behavior for `20260312` and `20260327` and decide which category each day should belong to beyond the current script output.
- Scope In: Classification thresholds, cold manifests/reports, raw/feature data, ATM decay, MTF IV, wall migration traces.
- Scope Out: Runtime code changes, threshold tuning, backfill regeneration.

## What Changed (Latest Session)
- Files: Session/context notes only; no runtime files changed in this analysis session.
- Behavior: Established that `20260327` is correctly a `gap_trend_day`; `20260312` is behaviorally a bearish `trend_day` with vol-crush overlay even though the script leaves it `unclassified`.
- Verification: Re-read classification logic in `scripts/diagnostics/eod_bucket_archive.py` and `scripts/diagnostics/config/eod_bucket_thresholds.json`; reconciled against cold reports and day-path evidence from feature/ATM/MTF-IV/wall datasets.

## Risks / Constraints
- Risk 1: `data/research/raw/raw_20260312.parquet` is not present in the current workspace, so `20260312` cannot be re-scored from live raw now.
- Risk 2: Both days have `ofi_persistence = 0.0`, which means the current taxonomy lacks a fallback bucket for strong directional sessions without OFI confirmation.

## Next Action
- Immediate Next Step: If classification policy is to be corrected, add a directional fallback or relax the hard OFI gate, then backfill `20260312`.
- Owner: Codex
