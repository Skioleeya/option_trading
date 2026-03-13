# Open Tasks

## Priority Queue
- [x] P0: Research-only official HV integration completed
  - Owner: Codex
  - Definition of Done:
    - Existing `option_quote()` research pull path aggregates official HV diagnostics.
    - `fetch_chain` and `compute_loop` metadata include official HV pass-through fields.
    - Research feature store persists official HV columns and `vrp_official_hv_based`.
  - Blocking: None
- [x] P1: Targeted regressions completed
  - Owner: Codex
  - Definition of Done:
    - Orchestrator tests cover official HV extraction and missing-HV fallback.
    - Compute-loop helper tests cover official HV diagnostics passthrough and age calculation.
    - Research feature store tests cover new official HV columns and derived VRP field.
  - Blocking: None
- [x] P2: SOP sync completed
  - Owner: Codex
  - Definition of Done:
    - `docs/SOP/L0_DATA_FEED.md` reflects official HV diagnostics passthrough rule.
  - Blocking: None

## Parking Lot
- [ ] Add dedicated end-to-end runtime observation on a live session to validate official HV freshness distribution.
- [ ] Evaluate whether official-HV cadence should be decoupled from 15-minute volume-research cadence for faster research labels.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] historical-vol-decimal-research-only-impl completed (2026-03-12 22:30 ET)
