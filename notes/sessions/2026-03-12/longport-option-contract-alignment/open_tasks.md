# Open Tasks

## Priority Queue
- [x] P0: L0 LongPort option runtime contract alignment
  - Owner: Codex
  - Definition of Done: Rust/Python runtimes expose aligned option quote, chain strike, and calc-index contracts with additive raw+normalized fields; L0 tests and Rust compile pass.
  - Blocking: None
- [ ] P1: Observe one live session after deploying rebuilt Rust extension
  - Owner: Codex
  - Definition of Done: Confirm live REST rows carry preserved official fields and normalized IV aliases without breaking Tier1/Tier2/Tier3 updates.
  - Blocking: Requires rebuilt/loaded extension in runtime environment
- [ ] P2: Consider adding preserved `standard` / `trade_status` / `premium` to downstream diagnostics
  - Owner: Codex
  - Definition of Done: Decide whether the new L0-preserved fields need explicit observability in later layers.
  - Blocking: Out of scope for this L0-only session

## Parking Lot
- [ ] Revisit `pyo3` signature deprecation warning in `RustIngestGateway.start`.
- [ ] Clean pre-existing Rust warnings in `ipc.rs` and `threat.rs`.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added shared LongPort option contract builders and normalized IV/date aliases (2026-03-12 13:46 ET)
- [x] Aligned Rust/Python runtime return shapes for option quote / chain / calc indexes (2026-03-12 13:46 ET)
- [x] Updated L0 IV consumers and SOP, and passed L0 test suite plus Rust compile (2026-03-12 13:46 ET)
