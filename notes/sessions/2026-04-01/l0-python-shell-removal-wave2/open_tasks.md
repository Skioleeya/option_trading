# Open Tasks

## Priority Queue
- [ ] P1: eliminate residual Python runtime owners from L0 runtime path
  - Owner: Codex
  - Definition of Done:
    - `PythonQuoteRuntime` no longer owns live L0 runtime state
    - `QuoteContext` lifecycle and callback fan-in are Rust-owned
    - generated extension import no longer needs Python package shim
  - Blocking: requires a new implementation slice beyond Phase A shell deletion
- [ ] P2: remove dead/stale adapter assumptions around legacy `LongportFeedAdapter`
  - Owner: Codex
  - Definition of Done:
    - legacy adapter either updated to current gateway contract or explicitly retired
  - Blocking: low priority because no live references exist in the current runtime path

## Parking Lot
- [ ] verify whether direct generated-extension import can replace `shared/services/l0_runtime/l0_rust/__init__.py`
- [ ] fold `sdk_bootstrap.py` startup probe into a Rust-native owner when Phase B starts

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Deleted Phase A shell file paths for `openapi_bootstrap.py`, `factory.py`, `quote_runtime.py`, `market_data_gateway.py`, and `l0_rust.py` (2026-04-01 12:53 ET)
