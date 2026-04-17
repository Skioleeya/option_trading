# Open Tasks

## Priority Queue
- [x] P0: Replace first-frame baseline with fixed design baseline (`1920x1080`) in adaptive scale pipeline.
  - Owner: Codex
  - Definition of Done: first render computes from fixed baseline; resize + browser zoom synced; no first-load mismatch.
  - Blocking: None.
- [x] P1: Lower adaptive minimum scale to `50%` while retaining upper clamp `125%`.
  - Owner: Codex
  - Definition of Done: small windows render within layout without clipping; tests assert new clamp behavior.
  - Blocking: None.
- [x] P2: Add tests + SOP sync + strict validation evidence.
  - Owner: Codex
  - Definition of Done: hook tests and header render tests green; `docs/SOP/L4_FRONTEND.md` reflects fixed baseline + new range; strict validator passes.
  - Blocking: None.

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Fixed-baseline adaptive scale revision completed (2026-04-17 15:19 ET)
