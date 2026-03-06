# Open Tasks

## Priority Queue
- [ ] P0: Add `-NoPointerUpdate` in `new_session.ps1`
  - Owner: Codex
  - Definition of Done: Session folders can be created without modifying `notes/context` active pointers.
  - Blocking: None.
- [ ] P1: Add `-Timezone` option in `new_session.ps1`
  - Owner: Codex
  - Definition of Done: Can pin bucket time and timestamps to a chosen timezone.
  - Blocking: Decide supported timezone identifiers.
- [ ] P2: Extend `validate_session.ps1 -Strict`
  - Owner: Quant Platform
  - Definition of Done: Strict mode enforces non-empty `commands/files_changed/tests_passed` for completed sessions.
  - Blocking: Completion criteria policy.

## Parking Lot
- [ ] Add automatic session ID collision suffix when same HHMM.
- [ ] Add CI pre-merge session validation job.

## Completed (Recent)
- [x] Time-bucket session directory support (`YYYY-MM-DD/HHMM/<task-id>`) (2026-03-06 11:31 ET)
