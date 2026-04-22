# Open Tasks

## Priority Queue
- [x] P0: Recover a usable `raw_20260312.parquet` into the official data path and complete formal cold re-archive for `20260312`.
  - Owner: Codex
  - Definition of Done: Official `data/research/raw/raw_20260312.parquet` exists, daily/by-regime/reports are rewritten, and manifest sync passes.
  - Blocking: None.
- [ ] P1: Audit whether any other pre-race archived days still point at vanished source snapshots.
  - Owner: Codex
  - Definition of Done: Remaining stale historical manifests, if any, are enumerated with dates and evidence.
  - Blocking: User has not requested a broader audit yet.
- [ ] P2: If stricter provenance is required later, locate an external backup/source-of-truth for the original March 12 raw snapshot.
  - Owner: Codex
  - Definition of Done: Either the exact old snapshot is found, or it is declared unrecoverable with evidence.
  - Blocking: No matching copy exists anywhere under `E:\US.market`.

## Parking Lot
- [ ] Consider adding a manifest note field when a day has been re-archived from recovered rather than original source files.
- [ ] Consider a one-shot stale-manifest audit across the cold archive tree.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Restored `raw_20260312.parquet` into the official research raw path from the only surviving local raw copy. (2026-03-27 23:50 ET)
- [x] Re-archived `20260312` so formal cold state now points to `trend_day` and fully synced source hashes. (2026-03-27 23:50 ET)
