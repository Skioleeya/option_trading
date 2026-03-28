# Open Tasks

## Priority Queue
- [x] P0: Produce a concrete plan for improving day-regime classification accuracy without drifting into runtime changes.
  - Owner: Codex
  - Definition of Done: A recommended design, alternatives, verification path, and execution ordering are documented.
  - Blocking: None.
- [ ] P1: Implement the recommended classifier redesign in a new execution session.
  - Owner: Codex
  - Definition of Done: Classifier logic and tests are updated, replay set passes, and target dates classify as intended.
  - Blocking: User has requested planning only in this session.
- [ ] P2: Recover or reconstruct `raw_20260312.parquet` before final backfill validation.
  - Owner: Codex
  - Definition of Done: `20260312` can be replayed through the exact same archive code path as live data.
  - Blocking: Current raw file missing from workspace.

## Parking Lot
- [ ] Evaluate whether `vol_crush_day` and `pinning_day` should become overlay tags rather than primary winners.
- [ ] Evaluate whether `LOW_QUALITY_DAY` should annotate valid classes instead of sitting at the same semantic layer.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Compared redesign options and selected a price-path directional fallback as the preferred approach. (2026-03-27 23:28 ET)
- [x] Anchored the plan to current classifier code and threshold config. (2026-03-27 23:28 ET)
