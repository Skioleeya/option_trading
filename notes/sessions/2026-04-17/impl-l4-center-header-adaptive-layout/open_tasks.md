# Open Tasks

## Priority Queue
- [x] P0: Rebuild the center header into strict left/middle/right grouped DOM with IV permanently visible.
  - Owner: Codex
  - Definition of Done: grouped DOM lands, small-screen rule hides only the detail badge, targeted tests/build pass.
  - Blocking: none
- [x] P1: Raise IV detail badge readability without sacrificing single-line behavior.
  - Owner: Codex
  - Definition of Done: regime/micro text is legible at the normal viewport and breakpoints absorb width pressure before text becomes tiny.
  - Blocking: none
- [x] P1: Add broker-style SPY tick direction feedback in the header.
  - Owner: Codex
  - Definition of Done: SPY price shows red upticks, green downticks, neutral first paint, and short tick flash with targeted test coverage.
  - Blocking: none
- [x] P1: Remove `SCALE` display from the masthead and rebalance the right utility rail.
  - Owner: Codex
  - Definition of Done: Header no longer renders `SCALE xx%`, `TACTICAL OFFENSIVE` and `RUST` remain grouped with clean breathing, targeted tests/build/strict validation pass.
  - Blocking: none
- [ ] P2: Capture live browser screenshot evidence for the refined masthead on the user viewport.
  - Owner: Next session
  - Definition of Done: refreshed browser evidence confirms grouping, IV readability, SPY tick presentation, and right-rail spacing under the real viewport.
  - Blocking: requires live browser run on the user viewport

## Parking Lot
- [ ] Re-run broader `l4_ui` visual smoke checks if more header or panel compression reports arrive.
- [ ] Consolidate prior header-related note drift once adjacent sessions are archived.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Grouped center-header DOM/CSS refactor implemented (2026-04-17 17:45 ET)
- [x] IV detail readability pass implemented (2026-04-17 18:05 ET)
- [x] SPY tick-direction header pass implemented (2026-04-17 18:16 ET)
- [x] Masthead `SCALE` removal and right-rail spacing pass implemented (2026-04-17 18:35 ET)
- [x] Targeted header/layoutScale tests passed (2026-04-17 18:35 ET)
- [x] `l4_ui` production build passed (2026-04-17 18:35 ET)
- [x] Strict session validation passed (2026-04-17 18:35 ET)
