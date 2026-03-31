# Project State

## Snapshot
- DateTime (ET): 2026-03-31 02:15:43 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6ba6cb2`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `N/A (offline cold-archive hard cut)`
  - L0-L4 Pipeline: `N/A (offline cold-archive hard cut)`

## Current Focus
- Primary Goal: Complete a no-compatibility hard cut of the day-taxonomy archive contract.
- Scope In: `scripts/diagnostics/eod_bucket_*`, related tests, OpenSpec day-taxonomy docs, and active `data/cold/*` artifacts.
- Scope Out: Runtime L0-L4 code, live backend loops, and recovery of retired historical dates without source evidence.

## What Changed (Latest Session)
- Files: `scripts/diagnostics/eod_bucket_rules.py`, `scripts/diagnostics/eod_bucket_archive.py`, `scripts/test/test_eod_bucket_archive.py`, `scripts/test/test_eod_bucket_classification_fallback.py`, `scripts/README.md`, `openspec/changes/research-day-taxonomy-non-overlap-20260331/*`, active `data/cold/daily|reports|by_regime` artifacts, and session/context evidence.
- Behavior: Classifier and archive outputs now expose only canonical `primary_day_type + context_modifiers + close_profile`; `primary_tag`, `legacy_primary_tag`, and `matched_tags` were removed; active cold archive now contains only canonical regime directories and only backfillable canonical dates.
- Verification: Targeted pytest passed (`19 passed`); active `data/cold` grep for legacy fields returned no matches; manifest sync passed for `20260324/25/26/27/30`; strict session validation passed with quality gate `PASS`, `runtime_changed=0`, and `openspec_changed=4`.

## Risks / Constraints
- Risk 1: This is an intentional breaking cut. Any consumer still reading `primary_tag`, `legacy_primary_tag`, or `matched_tags` will fail until migrated.
- Risk 2: Active cold archive no longer contains `20260311/12/13/17`; restoring those dates requires separate raw-source recovery and canonical rebuild.

## Next Action
- Immediate Next Step: Only open a new session if raw recovery for retired historical dates is explicitly required.
- Owner: Codex
