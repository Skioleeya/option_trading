# Project State

## Snapshot
- DateTime (ET): 2026-03-28 02:22:14 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6dfd9c5`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Commit the current accumulated diagnostics/data-maintenance changes and leave the worktree clean.
- Scope In: EOD archive/classification fixes, research feature store schema hardening, repaired cold outputs, test-path cleanup, and session/context records.
- Scope Out: New feature work beyond packaging the current repository state into a clean commit.

## What Changed (Latest Session)
- Files: Current staged scope spans `scripts/diagnostics/*`, `scripts/ops/*`, `shared/services/research_feature_store*`, `scripts/test/*`, `l3_assembly/tests/test_research_feature_store.py`, `data/cold/*`, `data/research/feature/feature_20260327.parquet`, and session/context notes.
- Behavior: The repo now includes settled EOD archive guards, mutually exclusive day-regime tags, repaired 20260312/20260326/20260327 cold outputs, and canonical-schema writes for the research feature store.
- Verification: `py_compile` passed for diagnostics/research store files, 42 targeted pytest cases passed, and manifest sync is green for `20260312`, `20260326`, and `20260327`.

## Risks / Constraints
- Risk 1: `20260327` post-`09:40 ET` feature rows are repaired from raw plus neutral/default feature-only placeholders because the exact lost decision snapshots are not locally recoverable.
- Risk 2: This commit intentionally bundles multiple already-validated maintenance sessions to clear the worktree in one shot, so the commit scope is broader than a single isolated fix.

## Next Action
- Immediate Next Step: Run strict validation, create one commit for the current repo state, and confirm `git status` is empty.
- Owner: Codex
