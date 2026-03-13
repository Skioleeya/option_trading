# Open Tasks

## Priority Queue
- [x] P0: fetch_chain store snapshot aggregation decouple
  - Owner: Codex
  - Definition of Done:
    - aggregation logic extracted from `OptionChainBuilder.fetch_chain()`
    - builder keeps orchestration role
  - Blocking: None
- [x] P1: legacy greeks audit decouple
  - Owner: Codex
  - Definition of Done:
    - `LegacyGreeksAudit` manages invocation/version/caller counters
    - diagnostics output preserved
  - Blocking: None
- [x] P1: governor/runtime payload assembly decouple
  - Owner: Codex
  - Definition of Done:
    - telemetry/runtime/error payload shaping moved to component helpers
    - boundary scan passes
  - Blocking: None
- [ ] P2: live smoke validation for fetch_chain refactor
  - Owner: Codex
  - Definition of Done:
    - one market-session observation confirms stable callbacks/telemetry cadence
  - Blocking: live window (latest attempt at 2026-03-13 00:31 ET failed by strict market-session gate)
  - Evidence:
    - `tmp/fetch_chain_live_smoke_20260313_003112.json` => `FAIL: market_session_gate_failed`

## Parking Lot
- [ ] Consider extracting `fetch_chain` ttm computation policy into dedicated L0 time-policy helper.
- [ ] Add benchmark harness for fetch_chain payload assembly latency.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] option-chain-builder-fetch-chain-decouple core refactor completed (2026-03-13 00:18 ET)
