# Open Tasks

## Priority Queue
- [x] P0: Make `gap_trend_day` and `trend_day` mutually exclusive and rerun affected buckets.
  - Owner: Codex
  - Definition of Done: `gap_trend_day` no longer coexists with `trend_day` in `matched_tags`, regression tests pass, and `20260327`/`20260326` manifests are rerun and synced.
  - Blocking: None.
- [ ] P1: Decide whether historical `gap_trend_day` outputs before this fix need a bounded replay sweep.
  - Owner: Codex
  - Definition of Done: Candidate dates are enumerated and replay scope is agreed.
  - Blocking: User has only requested the immediate semantic overlap fix.
- [ ] P2: Investigate why `feature_20260327.parquet` only contains `229` rows and whether the strict quality gate should stay red for that dataset.
  - Owner: Codex
  - Definition of Done: Root cause and remediation path are documented.
  - Blocking: Outside the scope of the overlap fix; current classification output is already correct.

## Parking Lot
- [ ] Consider exposing an explicit `exclusive_with` note in diagnostics docs so bucket semantics are obvious to future maintainers.
- [ ] Consider adding a one-shot replay helper for historical by-regime cleanup when taxonomy semantics change.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Suppressed `trend_day` whenever `gap_trend_day` matches, making the taxonomy mutually exclusive. (2026-03-28 00:13 ET)
- [x] Reran `20260327` and `20260326`, confirming synced manifests with non-overlapping tags. (2026-03-28 00:13 ET)
