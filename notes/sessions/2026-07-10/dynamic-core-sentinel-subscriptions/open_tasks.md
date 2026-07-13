# Open Tasks

## Priority Queue
- [x] P0: Implement dynamic core subscription selection with sentinel retention.
  - Owner: Codex
  - Definition of Done: L0 selector supports initial and dynamic phases, mandatory/underlying symbols are retained, and cap trimming preserves priority.
  - Blocking: None
- [x] P1: Add orchestration timing/snapshot inputs and rebalance hysteresis.
  - Owner: Codex
  - Definition of Done: `FeedOrchestrator` passes first-source timing and chain snapshot; small dynamic shifts do not churn subscriptions.
  - Blocking: None
- [x] P2: Update tests, SOP, and OpenSpec records.
  - Owner: Codex
  - Definition of Done: targeted regressions pass and session validation has required docs/governance records.
  - Blocking: None

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added Rust selector and Python hysteresis tests. (2026-07-10 12:24 ET)
- [x] Updated L0 SOP and OpenSpec change record. (2026-07-10 12:24 ET)
- [x] Added deterministic dynamic side guards and protection-tier cap trimming. (2026-07-10 13:25 ET)
