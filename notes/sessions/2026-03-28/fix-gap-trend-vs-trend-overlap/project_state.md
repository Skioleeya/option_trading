# Project State

## Snapshot
- DateTime (ET): 2026-03-28 00:13:53 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6dfd9c5`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Remove semantic overlap between `gap_trend_day` and `trend_day`, then rerun affected cold buckets.
- Scope In: Diagnostic classifier rule order/guard changes, regression tests, `20260327`/`20260326` reruns, manifest sync verification.
- Scope Out: Reworking the quality-gate policy or backfilling sparse `feature_20260327.parquet`.

## What Changed (Latest Session)
- Files: Updated `scripts/diagnostics/eod_bucket_rules.py`, `scripts/test/test_eod_bucket_classification_fallback.py`, and rewrote `20260327`/`20260326` cold manifests, quality reports, and by-regime manifests during reruns.
- Behavior: `gap_trend_day` now suppresses `trend_day` in `matched_tags`, so gap-trend sessions are classified as a distinct bucket instead of a parent/child overlap.
- Verification: `py_compile` passed, targeted pytest passed (`20 passed`), `20260327` reran to `primary=gap_trend_day matched=gap_trend_day`, `20260326` reran to `primary=trend_day matched=trend_day`, and both manifest sync checks returned `ok=true`.

## Risks / Constraints
- Risk 1: `20260327` still returns `LOW_QUALITY_DAY` under `--strict-quality` because `feature_20260327.parquet` has only `229` rows; this is an existing data-quality issue, not a classification-rule failure.
- Risk 2: Historical outputs that previously carried both tags should be rerun if downstream consumers depended on the old overlapping `matched_tags` behavior.

## Next Action
- Immediate Next Step: Keep the semantic fix; only investigate `20260327` feature sparsity if the user wants to clear the strict quality gate for that date.
- Owner: Codex
