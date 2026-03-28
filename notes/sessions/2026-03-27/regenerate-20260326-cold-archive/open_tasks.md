# Open Tasks

## Priority Queue
- [x] P0: regenerate the stale `20260326` cold archive outputs.
  - Owner: Codex
  - Definition of Done: `data/cold/daily|by_regime|reports` for `20260326` are regenerated from current source files and return `quality=PASS`.
  - Blocking: none
- [x] P1: prove the regenerated manifest matches the actual saved files.
  - Owner: Codex
  - Definition of Done: all six `source_files` entries match disk `size_bytes` and `sha256`; parquet row metrics match actual row counts.
  - Blocking: none
- [x] P1: record the repair in session/context notes and close with strict validation.
  - Owner: Codex
  - Definition of Done: session/context notes are synced and `scripts/validate_session.ps1 -Strict` passes.
  - Blocking: none

## Parking Lot
- [x] Root cause confirmed: the prior `20260326` cold manifest/report were generated at `16:01:03 ET`, before `raw/feature/mtf_iv` reached their final on-disk state.
- [ ] Follow-up candidate: investigate whether `EODBucketRetry` at `17:00` is missing or not rerunning when the primary task already succeeded.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Re-ran the `20260326` EOD cold archive and refreshed `daily/by_regime/report` outputs. (2026-03-27 22:48 ET)
- [x] Verified the refreshed manifest now matches all source files by size/hash/row count. (2026-03-27 22:49 ET)
