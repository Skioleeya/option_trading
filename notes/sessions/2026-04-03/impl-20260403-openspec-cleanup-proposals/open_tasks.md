# Open Tasks

## Priority Queue
- [x] P0: Create the cleanup proposal set
  - Owner: Codex
  - Definition of Done: Four new change folders exist with `proposal.md`, `design.md`, `tasks.md`, and at least one delta `spec.md` each.
  - Blocking: None.
- [x] P1: Validate proposal structure and cross-proposal dependencies
  - Owner: Codex
  - Definition of Done: `openspec.cmd list` shows the new changes; delta spec structure passes; dependency headers are consistent across the proposal set.
  - Blocking: None.
- [x] P2: Complete strict validation and sync final session/context evidence
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes and the resulting evidence is written into session/context handoff.
  - Blocking: None.

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Authored four cleanup-targeted OpenSpec change folders (2026-04-03 08:32 ET)
- [x] Completed OpenSpec structure and dependency header scans (2026-04-03 08:33 ET)
- [x] Closed the strict validation loop after fixing missing command evidence in `meta.yaml` (2026-04-03 08:36 ET)
