# Open Tasks

## Priority Queue
- [x] P0: Audit GEX L0-L4 formula, unit scale, sign convention, field propagation, and display path.
  - Owner: Codex
  - Definition of Done: Formula source and L2-L4 mappings reviewed; live payload sampled; targeted tests run.
  - Blocking: none.

## Parking Lot
- Observation: L3 GEX regime fail-fast masking should be fixed in a separate implementation session if accepted; unknown `gex_regime` should not be silently converted to `MicroStatsState.zero_state()`.
- Observation: MicroStats GEX comments/display prose should be aligned with OI-based proxy semantics if cleanup is accepted.
- Observation: Install Playwright in the project environment only if browser-level GEX UI reconciliation is needed again.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Read context and SOP fast-load pack. (2026-07-16 09:34 ET)
- [x] Audited L1 Rust/Python GEX formula and unit scale. (2026-07-16 09:38 ET)
- [x] Audited L2-L4 field mapping and display path. (2026-07-16 09:42 ET)
- [x] Captured live WS GEX payload sample. (2026-07-16 09:46 ET)
- [x] Ran targeted backend and L4 tests. (2026-07-16 09:48 ET)
