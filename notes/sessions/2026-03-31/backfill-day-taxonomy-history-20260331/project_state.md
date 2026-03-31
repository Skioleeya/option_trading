# Project State

## Snapshot
- DateTime (ET): 2026-03-31 02:00:55 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6ba6cb2`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `N/A (offline cold-manifest backfill)`
  - L0-L4 Pipeline: `N/A (offline cold-manifest backfill)`

## Current Focus
- Primary Goal: Backfill all backfillable historical cold manifests onto the canonical day-taxonomy contract.
- Scope In: `data/cold/daily/*`, `data/cold/reports/*`, `data/cold/by_regime/*` for dates with complete `research/raw|feature|label` sources, plus session/context evidence.
- Scope Out: Runtime L0-L4 code, live backend loops, and dates lacking `research/raw` source evidence.

## What Changed (Latest Session)
- Files: `data/cold/daily/20260324/manifest.json`, `data/cold/daily/20260325/manifest.json`, `data/cold/daily/20260326/manifest.json`, `data/cold/daily/20260327/manifest.json`, `data/cold/daily/20260330/manifest.json`, matching `data/cold/reports/*` outputs, canonical `data/cold/by_regime/balance_day|trend_day|reversal_day/*` indexes, and stale legacy `by_regime` manifests for `20260325` and `20260327` removed.
- Behavior: All backfillable historical dates now emit canonical `primary_day_type + context_modifiers + close_profile`; affected `by_regime` indexes no longer point to stale flat labels for those dates.
- Verification: Preview rerun succeeded for `20260324/25/26/27/30`; formal backfill wrote production manifests; `check_eod_manifest_sync.py` passed for all five dates; strict session validation passed with quality gate `PASS`, `runtime_changed=0`, and `openspec_changed=0`.

## Risks / Constraints
- Risk 1: `20260311/12/13/17` still have legacy flat manifests because `data/research/raw/raw_<date>.parquet` is absent, so canonical rebuild is not evidence-safe for those dates.
- Risk 2: Historical consumers that scan every `by_regime/*` directory will still encounter legacy top-level regime names for the four blocked dates until raw recovery or retirement is handled in a follow-up session.

## Next Action
- Immediate Next Step: Open a follow-up session only if raw recovery or retirement for `20260311/12/13/17` is approved.
- Owner: Codex
