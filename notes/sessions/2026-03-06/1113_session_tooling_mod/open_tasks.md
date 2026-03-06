# Open Tasks

## Priority Queue
- [ ] P0: Add `-NoPointerUpdate` mode to `new_session.ps1`
  - Owner: Codex
  - Definition of Done: Session files can be created without mutating `notes/context` pointers.
  - Blocking: None.
- [ ] P1: Add richer semantic checks to `validate_session.ps1`
  - Owner: Codex
  - Definition of Done: Optional strict mode validates `commands`, `files_changed`, and `tests_*` non-empty for completed sessions.
  - Blocking: Decide strict criteria for in-progress vs done sessions.
- [ ] P2: Add CI hook for session validation
  - Owner: Quant Platform
  - Definition of Done: PR pipeline runs `scripts/validate_session.ps1` for active session.
  - Blocking: CI PowerShell runner configuration.

## Parking Lot
- [ ] Auto-generate session `<task-id>` from branch + timestamp.
- [ ] Add markdown link rendering for session pointers.

## Completed (Recent)
- [x] Created session tooling scripts + pointer-mode context migration support (2026-03-06 11:18 ET)
