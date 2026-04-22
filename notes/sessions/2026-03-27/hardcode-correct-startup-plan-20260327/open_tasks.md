# Open Tasks

## Priority Queue
- [x] P0: hardcode the correct live system startup procedure into `AGENTS.md` in 1-3 lines.
  - Owner: Codex
  - Definition of Done: `AGENTS.md` contains a minimal hard rule that requires real-host startup and strict-first ordering.
  - Blocking: none
- [x] P1: make sandbox-local broker health evidence explicitly invalid in AGENTS governance.
  - Owner: Codex
  - Definition of Done: `AGENTS.md` explicitly forbids using sandbox-local backend launches as evidence for live broker/runtime health.
  - Blocking: none
- [x] P1: record the change in session/context and validate green.
  - Owner: Codex
  - Definition of Done: session notes are synced and `scripts/validate_session.ps1 -Strict` passes.
  - Blocking: none

## Parking Lot
- [x] Rule was compressed to 2 lines to satisfy the requested size constraint.
- [x] No runtime behavior or contracts were changed in this session.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added the 2-line hard startup rule to `AGENTS.md`. (2026-03-27 09:41 ET)
