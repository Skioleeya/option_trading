# Open Tasks

## Priority Queue
- [x] P0: Complete Header/GexStatusBar L0-L4 audit and root-cause evidence chain.
  - Owner: Codex
  - Definition of Done: Data source, transform, and render contracts traced from L0/L1/L3 payload to L4 component selectors.
  - Blocking: None.
- [x] P1: Hotfix severe Header observability defects (`STALLED` + `rust_active` visibility + ET market gate).
  - Owner: Codex
  - Definition of Done: Header no longer shows false-live status under stall/fallback conditions; market gate aligns to ET 09:30-16:00.
  - Blocking: None.
- [x] P2: Hotfix + modularization for GEX bar invalid level rendering.
  - Owner: Codex
  - Definition of Done: Non-finite/non-positive walls and flip render as unavailable (`—`) and logic extracted to dedicated module with tests.
  - Blocking: None.

## Parking Lot
- [ ] Add component-level integration test for `Header.tsx` rendering under mocked store states.
- [ ] Consider exposing `market_status` from backend payload to avoid front-end-only session calendar assumptions.

## Completed (Recent)
- [x] Header/GEX severe-hotfix + modularization + unit tests (2026-03-06 13:33 ET)
