# Open Tasks

## Priority Queue
- [ ] P1: Clear the unrelated frontend type-test debt that still blocks full `npm run build`.
  - Owner: Codex / frontend maintenance wave
  - Definition of Done: `npm --prefix l4_ui run build` passes without relying on test-file exclusions.
  - Blocking: Pre-existing `smallWindowGuardrails` node typings and tactical-triad test contract drift.
- [ ] P2: Re-sample browser CPU on a headed Windows Chrome session during higher-volatility live flow.
  - Owner: Codex
  - Definition of Done: One 60s headed-browser evidence pack is attached and remains `<5%` avg CPU / `>=50` FPS.
  - Blocking: Requires live market window and Windows-side browser automation evidence.

## Parking Lot
- [ ] Evaluate whether remaining `Header/DepthProfile` render work should be moved behind a lighter animation token set in a future polish wave.
- [ ] Consider a dedicated non-overlay performance HUD if repeated browser sampling becomes routine.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Removed closed-state DebugOverlay/store subscriptions and permanent RUM RAF loop. (2026-04-21 16:33 ET)
- [x] Replaced per-tick `atmHistory` ET trade-date filtering with trade-date keyed O(1) live history maintenance. (2026-04-21 16:33 ET)
- [x] Real-host Chrome CDP sampling confirmed frontend CPU `<5%` avg and FPS `60`. (2026-04-21 16:33 ET)
