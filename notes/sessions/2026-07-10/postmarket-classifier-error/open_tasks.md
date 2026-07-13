# Open Tasks

## Priority Queue
- [x] P0: Root-cause scheduled EOD classifier failure.
  - Owner: Codex
  - Definition of Done: reproduce task wrapper failure and identify the exact environment mismatch.
  - Blocking: None.
- [x] P1: Fix wrapper to use repo venv only.
  - Owner: Codex
  - Definition of Done: wrapper no longer resolves PATH/system Python and no fallback remains.
  - Blocking: None.
- [x] P2: Verify EOD task guard and today's publish.
  - Owner: Codex
  - Definition of Done: targeted test passes and `20260710` EOD bucket publishes with sync OK.
  - Blocking: None.

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Fixed scheduled EOD wrapper Python owner and verified `20260710` bucket publish. (2026-07-10 16:11 ET)
