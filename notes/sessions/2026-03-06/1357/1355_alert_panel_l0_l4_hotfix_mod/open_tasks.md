# Open Tasks

## Priority Queue
- [x] P0: Hotfix missing `Ctrl/Cmd + D` runtime toggle for DebugOverlay.
  - Owner: Codex
  - Definition of Done: Global key binding dispatches `l4:toggle_debug_overlay` (DEV mode) and verified by tests/build.
  - Blocking: None
- [x] P1: Hotfix DebugOverlay `shm_stats` contract gap (`status/head/tail/lag` not rendered).
  - Owner: Codex
  - Definition of Done: Overlay reads top-level payload `shm_stats`, displays values, and model tests pass.
  - Blocking: None
- [ ] P1: Resolve dead `l4:nav_*` command path.
  - Owner: Next agent
  - Definition of Done: Either add working listeners/scroll behavior, or remove/disable commands with clear UX rationale.
  - Blocking: Requires product decision on intended navigation target behavior.
- [ ] P2: Expand integration test to assert `Ctrl/Cmd + D` toggles overlay via event wiring in `App`.
  - Owner: Next agent
  - Definition of Done: RTL test around `App` verifies event-driven open/close path.
  - Blocking: None

## Parking Lot
- [ ] Assess whether AlertToast should support keyboard dismissal for accessibility parity.
- [ ] Consider moving debug overlay telemetry stream template to formatter utility for easier regression tests.

## Completed (Recent)
- [x] Audited `AlertToast` and confirmed no major L0-L4 contract break found (2026-03-06 14:06 ET)
- [x] Added modular helpers for command palette hotkeys/search and debug overlay model (2026-03-06 14:06 ET)
