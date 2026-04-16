# Open Tasks

## Priority Queue
- [x] P0: L0 `trade_type/trade_session` passthrough to Arrow + bridge
  - Owner: Codex
  - Definition of Done: schema/writer/gateway/bridge fields all aligned and readable
  - Blocking: None
- [x] P0: midpoint tick-rule direction path in trade payload
  - Owner: Codex
  - Definition of Done: midpoint uses prev_price + prev_direction continuation and outputs deterministic direction
  - Blocking: None
- [x] P1: Rust MM core functions and MVP integration
  - Owner: Codex
  - Definition of Done: Rust functions importable; MVP contract tests green; CSV fields upgraded
  - Blocking: None
- [ ] P1: Wave2 proposal execution (L1/L2 runtime Rust owner migration)
  - Owner: Codex
  - Definition of Done: Wave2 child proposal implemented and strict gate green
  - Blocking: Parent/child chain order

## Parking Lot
- [x] None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Wave1 OpenSpec parent + child created with field-consistency gate (2026-04-16 16:56 ET)
- [x] Rust artifacts rebuilt and copied (`shared_rust/services.pyd`, `l0_rust.pyd`) (2026-04-16 17:03 ET)
- [x] MVP contract tests passed (`6 passed, 1 skipped`) (2026-04-16 17:04 ET)
