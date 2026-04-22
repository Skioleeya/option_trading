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
- Primary Goal: Implement the minimal day-regime classifier change so strong directional days are no longer wholly dependent on OFI confirmation.
- Scope In: Offline archive classifier, threshold config, regression tests, replay acceptance, session/context sync.
- Scope Out: L0-L4 runtime code, downstream UI/schema rollout, canonical `20260312` raw recovery.

## What Changed (Latest Session)
- Files: Split `eod_bucket_archive.py` into smaller modules, updated threshold config, added fallback-specific tests, and fixed a stale settle guard test clock mock.
- Behavior: `trend_day` now has a directional-path fallback using `directional_efficiency`, `open_side_persistence`, `close_to_extreme`, and `state_switch_rate`, while `gap_trend_day` priority remains unchanged.
- Verification: `22` targeted pytest cases passed; replay acceptance shows `20260327 -> gap_trend_day` on canonical data and `20260312 -> trend_day` on isolated proxy replay data.

## Risks / Constraints
- Risk 1: The workspace still lacks canonical `data/research/raw/raw_20260312.parquet`, so formal backfill for that date still depends on raw recovery.
- Risk 2: `20260327` now matches both `trend_day` and `gap_trend_day`; primary stays correct by priority, but downstream consumers should rely on `primary_tag` if they need a single bucket.

## Next Action
- Immediate Next Step: Recover canonical `20260312` raw parquet and rerun archive on the real source set before touching production cold outputs for that date.
- Owner: Codex
