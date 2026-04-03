# Open Tasks

## Priority Queue
- [x] P0: Fix review gaps in the four cleanup proposals
  - Owner: Codex
  - Definition of Done: All four review findings are addressed in proposal/design/tasks/spec text.
  - Blocking: None.
- [x] P1: Re-scan the proposal set for structure and cross-proposal consistency
  - Owner: Codex
  - Definition of Done: Targeted grep confirms the new constraints; spec structure scan and `openspec.cmd list` remain green.
  - Blocking: None.
- [x] P2: Pass strict validation and sync session/context evidence
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes and the PASS evidence is written into handoff/context.
  - Blocking: None.

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Tightened proposal completion semantics to block false closure over Python runtime owners (2026-04-03 08:56 ET)
- [x] Added `fusion_weights` preservation and `RecordBatch` Arrow-first requirements to the relevant cutover proposals (2026-04-03 08:57 ET)
- [x] Closed the strict validation loop after adding missing command evidence to `meta.yaml` (2026-04-03 08:53 ET)
