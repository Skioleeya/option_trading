# Open Tasks

## Priority Queue
- [ ] P0: Verify the patched depth-profile window on the live backend and capture same-version evidence that the flip row is visible.
  - Owner: Codex
  - Definition of Done: Real-host backend restart completed; `/history?view=full&count=1` shows finite `gamma_flip_level` plus at least one `ui_state.depth_profile[*].is_flip=true` row.
  - Blocking: Backend must be restarted outside sandbox per AGENTS runtime rule.
- [ ] P1: Run strict session validation and sync context/handoff files for the gamma-flip fix session.
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes after session-local and `notes/context/*` files are synchronized.
  - Blocking: Final runtime verification and handoff content must be complete first.
- [ ] P2: Assess whether the depth-profile window should later prioritize additional hero strikes when call/put wall and flip cannot all fit in one fixed-width pane.
  - Owner: Codex
  - Definition of Done: Deferred design decision documented only if current session leaves a follow-up.
  - Blocking: None.

## Parking Lot
- [x] None. (2026-03-30 09:57 ET)

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Isolated root cause to L3 depth-profile window selection, not L1 gamma computation or L4 selector wiring. (2026-03-30 09:50 ET)
- [x] Added a presenter regression covering a flip level one strike above the original spot-centered window. (2026-03-30 09:55 ET)
