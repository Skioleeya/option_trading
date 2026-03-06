# Open Tasks

## Priority Queue
- [ ] P0: Backend intraday cutoff parity for ATM decay
  - Owner: Quant Backend
  - Definition of Done: `AtmDecayTracker.update()` enforces post-market cutoff and corresponding unit test added.
  - Blocking: Confirm expected close boundary (`16:00:00` hard stop vs configurable calendar/session close).
- [ ] P1: L0-L4 timestamp contract hardening
  - Owner: Quant Platform
  - Definition of Done: Timestamp format contract documented; parser tolerant strategy defined for non-ISO inputs.
  - Blocking: Cross-team agreement on canonical timestamp schema.
- [ ] P2: Frontend ATM chart incremental update optimization
  - Owner: L4 Frontend
  - Definition of Done: Avoid full-series `setData` on every tick for 5k history scenario; benchmark added.
  - Blocking: None.

## Parking Lot
- [ ] Add visual session separators (open/noon/close) to ATM chart.
- [ ] Explore binary payload for ATM substream when protobuf rollout starts.

## Completed (Recent)
- [x] Hotfix + modularization: L3 aggregate extraction resilience and L4 ATM market-hours gate + tests (2026-03-06 11:06 ET)
