# Open Tasks

## Priority Queue
- [x] P0: Root-cause fix for MM flow snapshot size source (depth `bid_volume/ask_volume`) and condition filter source (`trade_type` persisted in chain).
- [x] P1: Rebuild Rust owners (`l0_rust`, `shared_rust_services`) and replace runtime-loaded `.pyd` artifacts.
- [x] P1: Regression tests for L0 state persistence and MM flow no-fallback behavior.
- [x] P2: Keep touched Rust/Python files under 300 lines by splitting `gateway_core.rs` helper logic.

## Parking Lot
- [x] None in this session.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 2026-04-16 ET: P1/P2 root-cause fixes implemented and validated in targeted pytest.
