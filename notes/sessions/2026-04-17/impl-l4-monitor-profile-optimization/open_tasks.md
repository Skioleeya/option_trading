# Open Tasks

## Priority Queue
- [x] P0: Add viewport profile detection for main/secondary display classes.
  - Owner: Codex
  - Definition of Done: `useLayoutScale` and layout token generation expose `primary_standard` vs `secondary_compact` based on viewport only.
  - Blocking: None.
- [x] P1: Wire compact tokens into left/right/center layout owners.
  - Owner: Codex
  - Definition of Done: left rail, right cards, Header, GEX bar, and ATM overlay all consume profile-aware tokens instead of fixed density values.
  - Blocking: None.
- [x] P2: Record strict validation evidence and sync context/handoff.
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes and the exact result is recorded.
  - Blocking: None.

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Viewport profile optimization landed (2026-04-17 15:49 ET)
- [x] Strict validation passed and context sync completed (2026-04-17 15:50 ET)
