# Open Tasks

## Priority Queue
- [x] P0: Analyze `20260312` and `20260327` full-day metrics and decide script-external best-fit categories.
  - Owner: Codex
  - Definition of Done: Classification logic, cold metrics, and intraday path evidence are reconciled into a written judgment for both dates.
  - Blocking: None.
- [ ] P1: If user wants classification corrected in data, design the smallest policy change that reclassifies `20260312` without degrading genuine range/whipsaw days.
  - Owner: Codex
  - Definition of Done: A threshold/logic proposal exists with replay candidates and expected impact.
  - Blocking: User has asked for analysis only so far.
- [ ] P2: Recover or regenerate `raw_20260312.parquet` to enable exact recomputation and post-change backfill.
  - Owner: Codex
  - Definition of Done: Raw parquet exists and matches the cold-day window.
  - Blocking: Source file missing from current workspace snapshot.

## Parking Lot
- [ ] Review whether `LOW_QUALITY_DAY` should suppress or only annotate otherwise valid regime tags.
- [ ] Review whether `ofi_persistence` should be computed from a broader or less brittle signal basis.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Classified `20260327` as correctly tagged `gap_trend_day` by existing rules and actual day path. (2026-03-27 23:25 ET)
- [x] Determined `20260312` is behaviorally a bearish `trend_day` with strong vol-crush overlay, not a true `unclassified` session. (2026-03-27 23:25 ET)
