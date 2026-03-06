# Open Tasks

## Priority Queue
- [x] P0: Hotfix SPY ATM IV version propagation into L1/L2 decision pipeline.
  - Owner: Codex
  - Definition of Done: `compute_loop` passes real snapshot version (not constant 0), and L0 snapshot includes version field.
  - Blocking: None
- [x] P1: Modularize snapshot version parsing and state-version ownership.
  - Owner: Codex
  - Definition of Done: dedicated version parser helper in `compute_loop`; `ChainStateStore` owns monotonic version lifecycle.
  - Blocking: None
- [ ] P2: Add runtime observability probe for version-vs-spy_atm_iv drift.
  - Owner: Next agent
  - Definition of Done: log/metric confirms `spy_atm_iv` updates coincide with advancing snapshot version during live market ticks.
  - Blocking: Requires running live feed session.

## Parking Lot
- [ ] Consider exposing `snapshot_version` in L4 debug overlay for direct operator validation.
- [ ] Evaluate replacing heuristic state version with MVCC-backed version source where available.

## Completed (Recent)
- [x] Fixed major hidden bug: `l0_version` hardcoded to `0` in `compute_loop` (2026-03-06 15:47 ET)
- [x] Added state-version monotonic contract in `ChainStateStore` and fetch payload (2026-03-06 15:47 ET)
- [x] Added regression tests for version semantics and parser helper (2026-03-06 15:47 ET)
