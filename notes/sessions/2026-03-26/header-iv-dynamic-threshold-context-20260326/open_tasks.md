# Open Tasks

## Priority Queue
- [x] P0: create and land a concrete OpenSpec change for title-bar IV dynamic-threshold context.
  - Owner: Codex
  - Definition of Done: `openspec/changes/header-iv-dynamic-threshold-context-20260326/` exists with `proposal/design/tasks/spec`.
  - Blocking: none
- [x] P1: expose `agent_g.data.header_volatility` with `IVR/IVP`, `term_structure`, and `iv_price_relation`.
  - Owner: Codex
  - Definition of Done: L3 payload contains the new field and targeted regressions prove serialization.
  - Blocking: none
- [x] P1: render header volatility tokens in L4 without changing the existing main IV semantics.
  - Owner: Codex
  - Definition of Done: Header keeps `spy_atm_iv` + `iv_regime` as primary display and renders `R/P/1D/VX/β` tokens from store state.
  - Blocking: none
- [x] P1: keep changed runtime files below the 400-line gate.
  - Owner: Codex
  - Definition of Done: touched L3 payload modules are split and line counts fall back under the limit.
  - Blocking: none
- [x] P1: add header-volatility debug observability, perform a real backend restart, and verify live continuity on the restarted instance.
  - Owner: Codex
  - Definition of Done: runtime emits header-volatility debug summaries, `/debug/persistence_status` exposes payload+aux diagnostics, and repeated live polls show advancing aligned versions on the restarted backend.
  - Blocking: none

## Parking Lot
- [ ] Restore a strict fresh-launch backend path; as of 2026-03-26 15:49 ET, `LONGPORT/LONGBRIDGE` startup connectivity probing still fails on `/v2/socket/token`, so healthy restarts require `-Degraded`.
- [ ] Evaluate whether `1DTE` expiry selection should move to a calendar-aware helper shared with Tier2/Tier3 pollers.
- [ ] Observe live title-bar output during regular hours and verify token cadence against real research-store history.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added the OpenSpec change set `header-iv-dynamic-threshold-context-20260326` (2026-03-26 15:16 ET)
- [x] Added the shared header-volatility context service and L0 auxiliary diagnostics path for `.VIX.US` and `1DTE ATM IV` (2026-03-26 15:24 ET)
- [x] Split L3 payload contracts/assembler support so changed runtime files are back under 400 lines (2026-03-26 15:28 ET)
- [x] Added focused regressions plus L4 Header render coverage and verified build/test green (2026-03-26 15:30 ET)
- [x] Added header-volatility payload/debug diagnostics, restarted the backend in degraded mode with elevation, and verified live continuity on the new instance (2026-03-26 15:49 ET)
