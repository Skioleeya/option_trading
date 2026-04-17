# Open Tasks

## Priority Queue
- [x] P0: Remove broken whole-app transform scaling path.
  - Owner: Codex
  - Definition of Done: `App` no longer applies `transform: scale(...)` or inverse `width/height` compensation to the full L4 tree.
  - Blocking: None.
- [x] P1: Replace runtime scaling with layout-token scaling.
  - Owner: Codex
  - Definition of Done: viewport scale only drives layout token variables used by rails, GEX bar, and chart overlay positioning; no fallback path remains.
  - Blocking: None.
- [x] P2: Capture strict validation evidence and finalize session/context sync.
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes and the exact result is recorded in session handoff plus context index.
  - Blocking: None.

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Root-cause layout-scale replacement landed (2026-04-17 15:33 ET)
- [x] Strict validation passed and context sync completed (2026-04-17 15:34 ET)
