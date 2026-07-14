# Open Tasks

## Priority Queue
- No open P0/P1/P2 tasks for this session.

## Completed
- [x] P0: Make ATM anchor mandatory subscription independent from housekeeping ActiveOptions failures.
  - Owner: Codex
  - Definition of Done: compute-loop ATM update path sets mandatory symbols, refreshes subscriptions once on anchor change, repairs anchor prices, and targeted tests pass.
  - Completed: 2026-07-14 11:58 ET
- [x] P0: Raise local subscription pool cap to official 500.
  - Owner: Codex
  - Definition of Done: `.env` has `SUBSCRIPTION_MAX=500`; source default already remains 500.
  - Completed: 2026-07-14 11:58 ET
- [x] P1: Add OpenSpec and SOP evidence for the runtime behavior.
  - Owner: Codex
  - Definition of Done: OpenSpec delta and L0/L1 SOP explain compute-loop anchor mandatory ownership.
  - Completed: 2026-07-14 11:58 ET

## Parking Lot
- N/A:no parking-lot work created.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.
