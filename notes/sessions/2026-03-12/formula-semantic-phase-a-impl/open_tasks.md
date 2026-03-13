# Open Tasks

## Priority Queue
- [x] P0: Execute Phase A `VRP + GEX` semantic stopgap
  - Owner: Codex
  - Definition of Done:
    - `vol_risk_premium` emits percent points.
    - GEX/wall/zero-gamma proxy semantics aligned across code and SOP.
    - Targeted L2 regressions pass.
  - Blocking: None
- [ ] P1: Execute Phase B skew/raw-exposure contract convergence
  - Owner: Codex
  - Definition of Done:
    - Decide canonical `RR25` vs current normalized skew field strategy.
    - Rename or hard-label `net_vanna/net_charm` raw sums.
    - Update downstream docs/tests.
  - Blocking: Need downstream consumer scan before renaming.
- [ ] P2: Gate Phase D research upgrades on official field consumption review
  - Owner: Codex
  - Definition of Done:
    - Decide whether L0 `historical_volatility/premium/standard` should be consumed before new derived vol paths.
    - Reflect decision in OpenSpec sequencing.
  - Blocking: Depends on research/data-priority decision.

## Parking Lot
- [ ] Review `VRPVetoGuard` for future percent-point migration once guard consumers are explicitly versioned.
- [ ] Remove deprecated `asyncio.get_event_loop()` usage in `l2_decision/tests/test_reactor_and_guards.py` if warning cleanup becomes necessary.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Phase A implementation and regression pass (2026-03-12 14:36 ET)
