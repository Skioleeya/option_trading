# Open Tasks

## Priority Queue
- [x] P0: retire tactical wrapper runtime surface
  - Owner: Codex
  - Definition of Done: `shared/system/tactical_triad_logic.py` deleted and no runtime references remain.
  - Blocking: none.
- [x] P1: retarget L2/L3 consumers to `shared_rust.services`
  - Owner: Codex
  - Definition of Done: five consumer modules import tactical symbols from `shared_rust.services` with unchanged call sites.
  - Blocking: none.
- [x] P2: satisfy runtime file-length gate for changed files
  - Owner: Codex
  - Definition of Done: all changed runtime Python files are `<=400` lines.
  - Blocking: none.

## Parking Lot
- [x] Item: none

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] P3 tactical-triad wrapper retirement implementation complete (2026-04-02 15:44 ET)
